"""Round 16 / P0-3: when ``stats._load_inflight`` expires a stale
inflight row, ``DispatchState.inflight_by_task`` / ``model_inflight`` /
``worker.inflight`` must drop the row from memory too.

Before the fix, expiration only rewrote ``inflight.jsonl`` on disk; the
dispatcher's in-memory counters silently kept the slot held, so the
worker / model_cap budget never recovered and the affected task could
not be re-dispatched until the dispatcher restarted.

Now ``recompute_priorities`` exposes the set of expired keys via the
``expired_inflight_out`` parameter, and the dispatcher calls
``state.release(key)`` for each one.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from scripts.orchestra import config as cfg_mod
from scripts.orchestra import dispatch as dispatch_mod
from scripts.orchestra import stats as stats_mod
from scripts.orchestra.config import (
    CodexRoleCfg,
    ControllerCfg,
    OrchestraConfig,
    PriorityCfg,
    SupervisionCfg,
    WorkerCfg,
)


def _make_state_with_short_ttl(tmp_path: Path) -> dispatch_mod.DispatchState:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    cfg = OrchestraConfig(
        controller=ControllerCfg(host="controller", data_root=tmp_path, webui_port=9005),
        workers=(
            WorkerCfg(name="w1", ssh="w1", parallel=4),
            WorkerCfg(name="w2", ssh="w2", parallel=4),
        ),
        priorities=(
            PriorityCfg(id="P1", label="missing-only", status_in=("missing",)),
        ),
        model_caps={"m1": 4},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
        max_inflight_age_seconds=60,  # 1 minute → easy to expire stale rows
    )
    workers = [dispatch_mod.WorkerState(cfg=w) for w in cfg.workers]
    return dispatch_mod.DispatchState(
        cfg=cfg,
        workers=workers,
        done_file=runtime_dir / "done.jsonl",
        inflight_file=runtime_dir / "inflight.jsonl",
    )


def test_load_inflight_returns_expired_keys_tuple(tmp_path: Path) -> None:
    """Sanity check on the new tuple return contract."""
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    (runtime_dir / "inflight.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "backend": "openclaw",
                    "model_dir": "m1",
                    "suite": "101",
                    "task": "fresh",
                    "worker": "w1",
                    "ts_start": now - 10,
                },
                {
                    "backend": "openclaw",
                    "model_dir": "m1",
                    "suite": "101",
                    "task": "stale",
                    "worker": "w1",
                    "ts_start": now - 3600,
                },
            ]
        ),
        encoding="utf-8",
    )

    survivors, expired = stats_mod._load_inflight(runtime_dir, max_age_seconds=60)
    assert ("openclaw", "m1", "101", "fresh") in survivors
    assert ("openclaw", "m1", "101", "stale") not in survivors
    assert ("openclaw", "m1", "101", "stale") in expired
    assert ("openclaw", "m1", "101", "fresh") not in expired


def test_recompute_priorities_emits_expired_keys(tmp_path: Path) -> None:
    """``recompute_priorities(..., expired_inflight_out=set)`` populates
    the provided set with expired keys so the dispatcher can release
    them from in-memory state."""
    state = _make_state_with_short_ttl(tmp_path)
    runtime_dir = state.inflight_file.parent
    tasks_root = tmp_path / "tasks"
    suite = tasks_root / "101_test"
    suite.mkdir(parents=True)
    (suite / "task_stale.yaml").write_text("task_id: task_stale\n", encoding="utf-8")

    state.inflight_file.write_text(
        json.dumps(
            {
                "backend": "openclaw",
                "model_dir": "m1",
                "suite": "101_test",
                "task": "task_stale",
                "worker": "w1",
                "ts_start": time.time() - 3600,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    expired: set[tuple[str, str, str, str]] = set()
    stats_mod.recompute_priorities(
        state.cfg,
        tasks_root=tasks_root,
        runs_root=tmp_path,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={},
        expired_inflight_out=expired,
    )
    assert ("openclaw", "m1", "101_test", "task_stale") in expired


def test_dispatch_state_release_clears_all_counters(tmp_path: Path) -> None:
    """``DispatchState.release`` zeroes worker.inflight, model_inflight,
    and removes the entry from inflight_by_task.  This is the contract
    that the dispatcher relies on to roll back a TTL-expired row."""
    state = _make_state_with_short_ttl(tmp_path)
    task = {
        "backend": "openclaw",
        "model_dir": "m1",
        "suite": "101_test",
        "task": "t1",
    }
    state.reserve(task, state.workers[0])
    assert state.workers[0].inflight == 1
    assert state.model_inflight["m1"] == 1
    assert state.task_key(task) in state.inflight_by_task

    released = state.release(state.task_key(task))
    assert released is not None
    assert state.workers[0].inflight == 0
    assert state.model_inflight["m1"] == 0
    assert state.task_key(task) not in state.inflight_by_task


def test_dispatcher_loop_releases_ttl_expired_inflight_from_memory(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: simulate one tick of ``run_unified_dispatch`` after
    restoring a stale inflight row from disk.  The recompute pass must
    flag the row as expired, and the dispatcher must call
    ``state.release`` so worker.inflight + model_inflight + inflight_by_task
    all drop to zero."""
    state = _make_state_with_short_ttl(tmp_path)
    runtime_dir = state.inflight_file.parent
    tasks_root = tmp_path / "tasks"
    suite = tasks_root / "101_test"
    suite.mkdir(parents=True)
    (suite / "task_stale.yaml").write_text("task_id: task_stale\n", encoding="utf-8")

    # Plant a stale row + restore so the dispatcher's in-memory state
    # also shows the row as held.
    state.inflight_file.write_text(
        json.dumps(
            {
                "backend": "openclaw",
                "model_dir": "m1",
                "suite": "101_test",
                "task": "task_stale",
                "worker": "w1",
                "ts_start": time.time() - 3600,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state.restore_inflight_from_disk()
    assert state.workers[0].inflight == 1
    assert state.model_inflight["m1"] == 1
    assert state.task_key(
        {"backend": "openclaw", "model_dir": "m1", "suite": "101_test", "task": "task_stale"}
    ) in state.inflight_by_task

    # Simulate one recompute pass.
    expired: set[tuple[str, str, str, str]] = set()
    stats_mod.recompute_priorities(
        state.cfg,
        tasks_root=tasks_root,
        runs_root=tmp_path,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts=state.session_attempts,
        expired_inflight_out=expired,
    )
    # Then the dispatcher releases each expired key, exactly as
    # run_unified_dispatch does after recompute.
    for key in expired:
        state.release(key)

    assert state.workers[0].inflight == 0
    assert state.model_inflight["m1"] == 0
    assert not state.inflight_by_task
