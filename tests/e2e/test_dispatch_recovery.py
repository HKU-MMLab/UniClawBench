"""Phase-3 recovery tests for the orchestra dispatcher.

These pin four failure modes the dispatcher used to handle silently:

1. **Dispatcher crash → inflight memory loss** — inflight.jsonl rows
   persisted to disk, but the in-memory dict + worker counters started
   at 0 on restart; ``restore_inflight_from_disk`` now rebuilds them.

2. **done.jsonl truncated, not archived** — a crash between read and
   processing-complete lost DONE rows; ``_drain_done_file`` now renames
   to ``done_history/done_<ts>.jsonl`` so the rows survive.

3. **rsync-failure releases inflight slot** — a worker that ran but
   couldn't transfer results back used to be marked DONE on the
   controller while leaving an orphan on the worker; the controller
   now leaves the slot held so TTL can decide.

4. **Stuck inflight rows never expire** — a row whose worker crashed
   silently would block its model's slot forever; ``_load_inflight``
   now expires rows past ``max_inflight_age_seconds``.

The tests drive ``DispatchState`` and ``stats._load_inflight`` directly
(no real SSH) — that's enough to pin the contract.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import scripts.orchestra.dispatch as dispatch_mod
import scripts.orchestra.stats as stats_mod


# ── helpers ──────────────────────────────────────────────────────────


def _stub_config(tmp_path: Path) -> "dispatch_mod.cfg_mod.OrchestraConfig":
    """Build a minimal OrchestraConfig that doesn't need a yaml file."""
    from scripts.orchestra.config import (
        ControllerCfg,
        CodexRoleCfg,
        OrchestraConfig,
        SupervisionCfg,
        WorkerCfg,
    )
    return OrchestraConfig(
        controller=ControllerCfg(
            host="controller",
            data_root=tmp_path,
            webui_port=9005,
        ),
        workers=(
            WorkerCfg(name="w1", ssh="w1", parallel=2),
            WorkerCfg(name="w2", ssh="w2", parallel=2),
        ),
        priorities=(),
        model_caps={"fake-model": 1},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
    )


def _make_state(tmp_path: Path) -> "dispatch_mod.DispatchState":
    cfg = _stub_config(tmp_path)
    workers = [dispatch_mod.WorkerState(cfg=w) for w in cfg.workers]
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return dispatch_mod.DispatchState(
        cfg=cfg,
        workers=workers,
        done_file=runtime_dir / "done.jsonl",
        inflight_file=runtime_dir / "inflight.jsonl",
    )


# ── 1. inflight restore on startup ──────────────────────────────────


def test_inflight_restored_on_restart(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    state.inflight_file.write_text(
        "\n".join([
            json.dumps({
                "backend": "openclaw",
                "model_dir": "fake-model",
                "suite": "101_multimodal",
                "task": "task_001",
                "worker": "w1",
                "ts_start": time.time(),
            }),
            json.dumps({
                "backend": "openclaw",
                "model_dir": "other-model",
                "suite": "101_multimodal",
                "task": "task_002",
                "worker": "w2",
                "ts_start": time.time(),
            }),
            "",  # blank line tolerance
            "not-json",  # malformed line tolerance
        ]),
        encoding="utf-8",
    )

    restored = state.restore_inflight_from_disk()

    assert restored == 2
    assert len(state.inflight_by_task) == 2
    # Counters reflect restored rows so future can_start() respects model_caps:
    assert state.model_inflight["fake-model"] == 1
    assert state.model_inflight["other-model"] == 1
    w1 = next(w for w in state.workers if w.cfg.name == "w1")
    w2 = next(w for w in state.workers if w.cfg.name == "w2")
    assert w1.inflight == 1
    assert w2.inflight == 1


def test_inflight_restore_on_empty_file_is_noop(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    state.inflight_file.touch()
    assert state.restore_inflight_from_disk() == 0
    assert state.inflight_by_task == {}


def test_can_start_respects_restored_inflight(tmp_path: Path) -> None:
    """After restore, the dispatcher must not double-dispatch a task
    that was already in flight on the previous instance."""
    state = _make_state(tmp_path)
    state.inflight_file.write_text(json.dumps({
        "backend": "openclaw",
        "model_dir": "fake-model",
        "suite": "101_multimodal",
        "task": "task_001",
        "worker": "w1",
        "ts_start": time.time(),
    }), encoding="utf-8")
    state.restore_inflight_from_disk()

    w1 = state.workers[0]
    duplicate = {
        "backend": "openclaw",
        "model_dir": "fake-model",
        "suite": "101_multimodal",
        "task": "task_001",
    }
    assert state.can_start(duplicate, w1) is False  # already inflight

    # And model_cap of 1 still bars OTHER tasks on the same model:
    other_task_same_model = {
        "backend": "openclaw",
        "model_dir": "fake-model",
        "suite": "101_multimodal",
        "task": "task_999",
    }
    assert state.can_start(other_task_same_model, w1) is False


# ── 2. done.jsonl archived, not truncated ───────────────────────────


def test_done_jsonl_archived_not_truncated(tmp_path: Path, monkeypatch) -> None:
    state = _make_state(tmp_path)
    # Workers must have these tasks reserved so release() does something
    # observable, but the archive-on-drain happens before release so even
    # without reservations the file moves.  We reserve one to also confirm
    # release fires for "real" DONE rows.
    state.reserve(
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "101_multimodal", "task": "task_001"},
        state.workers[0],
    )
    rows = [
        # rsync-succeeded → should be released
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "101_multimodal", "task": "task_001",
         "status": "pass", "rc": 0, "transferred": True},
        # rsync-failed → should NOT be released (covered by next test)
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "101_multimodal", "task": "task_002",
         "status": "pass", "rc": 0, "transferred": False,
         "transferred_reason": "rsync_failed_after_3_retries_rc=23"},
    ]
    state.done_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                encoding="utf-8")

    # Stub refresh_one_task_with_index so we don't need a real runs tree.
    monkeypatch.setattr(
        dispatch_mod.refresh_summary,
        "refresh_one_task_with_index",
        lambda *a, **k: None,
    )

    n = dispatch_mod._drain_done_file(state)

    # The archive directory now contains exactly one rotated file:
    archive_dir = state.done_file.parent / "done_history"
    archives = sorted(archive_dir.glob("done_*.jsonl"))
    assert len(archives) == 1
    archive_content = archives[0].read_text(encoding="utf-8")
    assert "task_001" in archive_content
    assert "task_002" in archive_content
    # The live done.jsonl is fresh (touched, empty):
    assert state.done_file.exists()
    assert state.done_file.read_text(encoding="utf-8") == ""
    # n_done counts only the transferred=True row:
    assert n == 1


# ── 3. rsync-failed DONE keeps inflight slot ────────────────────────


def test_rsync_failed_keeps_inflight(tmp_path: Path, monkeypatch) -> None:
    state = _make_state(tmp_path)
    task = {"backend": "openclaw", "model_dir": "m1",
            "suite": "101_multimodal", "task": "task_003"}
    state.reserve(task, state.workers[0])
    assert state.task_key(task) in state.inflight_by_task

    # Worker says it ran but couldn't transfer:
    state.done_file.write_text(json.dumps({
        **task,
        "status": "pass",
        "rc": 0,
        "transferred": False,
        "transferred_reason": "rsync_failed_after_3_retries_rc=23",
    }) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        dispatch_mod.refresh_summary,
        "refresh_one_task_with_index",
        lambda *a, **k: None,
    )

    dispatch_mod._drain_done_file(state)

    # The inflight slot is STILL held — TTL will eventually expire it.
    assert state.task_key(task) in state.inflight_by_task
    # Worker counter not decremented either:
    assert state.workers[0].inflight == 1
    assert state.model_inflight["m1"] == 1


# ── 4. inflight TTL expiry ─────────────────────────────────────────


def test_inflight_ttl_releases_stale_rows(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    f = runtime_dir / "inflight.jsonl"

    now = time.time()
    rows = [
        # Fresh: started 1 minute ago, should survive
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "101_multimodal", "task": "task_fresh",
         "worker": "w1", "ts_start": now - 60},
        # Stale: started 2 days ago, should expire (cutoff = 1h)
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "101_multimodal", "task": "task_stale",
         "worker": "w1", "ts_start": now - 2 * 86400},
        # Legacy: no ts_start → treated as just-started (survives)
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "101_multimodal", "task": "task_legacy",
         "worker": "w1"},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    survivors, expired = stats_mod._load_inflight(runtime_dir, max_age_seconds=3600)

    keys = {(b, m, s, t) for (b, m, s, t) in survivors}
    assert ("openclaw", "m1", "101_multimodal", "task_fresh") in keys
    assert ("openclaw", "m1", "101_multimodal", "task_legacy") in keys
    assert ("openclaw", "m1", "101_multimodal", "task_stale") not in keys

    # Round 16 / P0-3: expired keys are reported back so the dispatcher
    # can release in-memory inflight state in sync with the disk file.
    assert ("openclaw", "m1", "101_multimodal", "task_stale") in expired
    assert ("openclaw", "m1", "101_multimodal", "task_fresh") not in expired
    assert ("openclaw", "m1", "101_multimodal", "task_legacy") not in expired

    # And the on-disk file no longer contains the expired row:
    persisted = f.read_text(encoding="utf-8")
    assert "task_fresh" in persisted
    assert "task_legacy" in persisted
    assert "task_stale" not in persisted


def test_inflight_ttl_disabled_keeps_all_rows(tmp_path: Path) -> None:
    """When max_age_seconds is None or 0, the loader is non-destructive
    even for very old rows.  Confirms we don't accidentally garbage-
    collect during ad-hoc CLI calls that pass no TTL."""
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    f = runtime_dir / "inflight.jsonl"
    rows = [
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "s", "task": "ancient",
         "worker": "w1", "ts_start": time.time() - 10 * 365 * 86400},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    survivors, expired = stats_mod._load_inflight(runtime_dir, max_age_seconds=None)
    assert ("openclaw", "m1", "s", "ancient") in survivors
    assert not expired
    # File untouched:
    assert "ancient" in f.read_text(encoding="utf-8")


# ── 5. reserve() stamps ts_start ───────────────────────────────────


def test_reserve_stamps_ts_start(tmp_path: Path) -> None:
    """The TTL guard above only works if reserve() actually writes a
    ts_start in the persisted row.  Pin that."""
    state = _make_state(tmp_path)
    before = time.time()
    state.reserve(
        {"backend": "openclaw", "model_dir": "m1",
         "suite": "s", "task": "task_a"},
        state.workers[0],
    )
    after = time.time()

    persisted = state.inflight_file.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in persisted.splitlines() if line.strip()]
    assert len(rows) == 1
    ts = rows[0].get("ts_start")
    assert isinstance(ts, (int, float))
    assert before <= ts <= after


def test_ssh_backoff_seconds_curve() -> None:
    """Backoff curve: 10s → 30s → 90s → 300s (cap)."""
    from scripts.orchestra.dispatch import _ssh_backoff_seconds
    assert _ssh_backoff_seconds(0) == 0.0  # no failures = no backoff
    assert _ssh_backoff_seconds(1) == 10.0
    assert _ssh_backoff_seconds(2) == 30.0
    assert _ssh_backoff_seconds(3) == 90.0
    assert _ssh_backoff_seconds(4) == 300.0
    assert _ssh_backoff_seconds(10) == 300.0  # caps


def test_worker_in_backoff_refused_by_can_start(tmp_path: Path) -> None:
    """Regression: when a worker has ``unavailable_until > now`` (post ssh
    failure), can_start must return False so the dispatcher doesn't
    hot-loop trying to re-dispatch to a downed host.

    Before this fix, a worker with port 2222 refused (Connection refused
    returns ssh rc=255 in milliseconds) would get the same 7 tasks
    re-tried every 3 seconds, producing 161 ssh failures in 21 seconds
    while worker3/worker4 (healthy) never received any work.
    """
    state = _make_state(tmp_path)
    w1 = state.workers[0]
    w2 = state.workers[1]

    # Simulate w1 just failed ssh:
    w1.consecutive_ssh_failures = 1
    w1.unavailable_until = time.time() + 60  # 1 minute in future

    task = {"backend": "openclaw", "model_dir": "m1",
            "suite": "s", "task": "t1"}
    assert state.can_start(task, w1) is False, "downed worker must be refused"
    assert state.can_start(task, w2) is True, "healthy worker still accepts"

    # After the backoff expires, w1 should accept again:
    w1.unavailable_until = time.time() - 1  # already passed
    assert state.can_start(task, w1) is True


def test_run_unified_dispatch_keeps_running_with_restored_inflight(
    tmp_path: Path, monkeypatch
) -> None:
    """Round 16 / P0-2: a freshly-restarted dispatcher with restored
    inflight rows from disk but no new tasks in any priority bucket
    must NOT exit on the first tick of ``run_unified_dispatch``.

    Before the fix, the queue-drained guard only checked ``flat_tasks``
    and ``futures``.  Restored inflight rows have neither, so the
    dispatcher exited immediately, stopped draining ``done.jsonl``, and
    left the in-memory state to rot.  After the fix it keeps polling
    until the inflight is genuinely empty (via TTL cleanup, a real DONE
    callback, or operator shutdown)."""
    from concurrent.futures import ThreadPoolExecutor
    import threading

    state = _make_state(tmp_path)
    # Plant a restored ghost row.
    state.inflight_file.write_text(
        json.dumps(
            {
                "backend": "openclaw",
                "model_dir": "ghost-model",
                "suite": "101_multimodal",
                "task": "ghost_task",
                "worker": "w1",
                "ts_start": time.time() - 60,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state.restore_inflight_from_disk()
    assert state.inflight_by_task, "precondition: ghost row in memory"

    # Recompute always returns empty user buckets + the synthetic
    # P100/P200 placeholders.  No new tasks → nothing dispatchable.
    empty_buckets = [
        {"priority_id": "P1", "label": "p1", "tasks": []},
        {"priority_id": stats_mod.P100_BUCKET_ID, "label": "p100", "tasks": []},
        {"priority_id": stats_mod.P200_BUCKET_ID, "label": "p200", "tasks": []},
    ]
    monkeypatch.setattr(
        dispatch_mod.stats_mod,
        "recompute_priorities",
        lambda *a, **k: empty_buckets,
    )

    shutdown = threading.Event()
    # Trip shutdown after a short window — long enough to take 1+
    # iterations of the loop (poll_interval_seconds=0.2) but short
    # enough to keep the test fast.
    def _trigger():
        time.sleep(1.0)
        shutdown.set()

    threading.Thread(target=_trigger, daemon=True).start()

    started_at = time.time()
    with ThreadPoolExecutor(max_workers=2) as ex:
        dispatched = dispatch_mod.run_unified_dispatch(
            state,
            ex,
            state.cfg,
            tasks_root=tmp_path / "tasks",
            runtime_dir=tmp_path / "runtime",
            shutdown_event=shutdown,
            poll_interval_seconds=0.2,
            recompute_interval_seconds=0.2,
            full_refresh_interval_seconds=0.5,
        )
    elapsed = time.time() - started_at

    # The dispatcher must have actually polled (not exited the moment it
    # saw empty buckets).  If it bailed early the shutdown wouldn't have
    # had time to fire and elapsed would be ~0.0s.
    assert elapsed >= 1.0, (
        f"dispatcher exited too early (elapsed={elapsed:.2f}s); the "
        "queue-drained guard fired despite restored inflight"
    )
    assert dispatched == 0
    # The ghost row stays in inflight_by_task — only P0-3 TTL handling
    # is responsible for clearing it from memory, which is covered
    # separately.
    assert state.inflight_by_task, "ghost row should remain pending"


def test_run_one_bucket_does_not_wait_for_restored_ghost_rows(tmp_path: Path, monkeypatch) -> None:
    """Regression: a restored-but-orphan inflight row (Phase 3.1 case where
    the previous dispatcher died and its worker died with it) MUST NOT
    deadlock ``run_one_bucket``'s drain loop.

    Symptom before fix: dispatcher B starts, restores 1 ghost row from
    disk → worker.inflight=1.  Dispatches 6 fresh tasks, they all DONE.
    Bucket has no more pending.  But the loop condition
    ``while any(w.inflight for w in state.workers)`` is still True because
    the GHOST row's worker counter never decrements (no live process to
    DONE it).  Result: dispatcher hangs for 39+ minutes producing nothing.

    Fix: loop waits on ``futures`` (tasks dispatched in THIS bucket call),
    not on overall ``w.inflight`` which contains restored rows.
    """
    from concurrent.futures import ThreadPoolExecutor
    state = _make_state(tmp_path)
    # Plant an orphan inflight row (simulating restored-from-disk ghost
    # whose worker died with the previous dispatcher instance):
    state.inflight_file.write_text(
        json.dumps({
            "backend": "openclaw", "model_dir": "ghost-model",
            "suite": "101_multimodal", "task": "ghost_task",
            "worker": "w1", "ts_start": time.time() - 3600,
        }) + "\n",
        encoding="utf-8",
    )
    state.restore_inflight_from_disk()
    assert state.workers[0].inflight == 1, "precondition: ghost row inflated worker counter"

    # Empty bucket — nothing to dispatch.  Before the fix, run_one_bucket
    # would loop forever waiting for the ghost's inflight to drain.
    started_at = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        n = dispatch_mod.run_one_bucket(state, ex, {"priority_id": "T_test", "tasks": []})
    elapsed = time.time() - started_at

    assert n == 0
    # Must NOT have hung — empty bucket + ghost-only inflight should
    # return in well under a second.
    assert elapsed < 5.0, f"run_one_bucket hung {elapsed:.1f}s on a ghost-only inflight"
    # Ghost row stays in inflight_by_task (it's an unreleased reservation);
    # TTL pass on next stats.recompute_priorities will expire it.
    assert ("openclaw", "ghost-model", "101_multimodal", "ghost_task") in state.inflight_by_task
