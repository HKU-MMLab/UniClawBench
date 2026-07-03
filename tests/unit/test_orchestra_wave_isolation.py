"""Round 15 / P1 — wave-isolated dispatch.

Pins the behaviour of ``DispatchState.dispatched_this_round`` +
``maybe_advance_round()`` so a future refactor cannot reopen the
Round-14 rate_limit / infra_error retry-storm window.

The original bug (Round-14 sonnet rate-limit symptom):
  1. Task A reserved at T+0s, runs on worker1.
  2. A fast-fails at T+5s with status=rate_limit.  worker_runner writes
     done.jsonl; _drain_done_file (separate 2s-poll thread) releases
     A from inflight_by_task.
  3. At T≈5s the main loop reaches its 5s recompute window.  Disk-state
     re-read by recompute_priorities → A's summary.json says
     rate_limit → A lands in the P2_recoverable bucket.
  4. Old can_start() saw A NOT-in-inflight ✓, session_attempts[A]=1 ✓,
     model_cap not full ✓ → True.  A gets reserved AGAIN, almost
     immediately, while the API is still throttled.

The fix (this module under test): keep a ``dispatched_this_round`` set
of task keys.  ``reserve()`` adds; ``can_start()`` refuses members; the
set is only cleared by ``maybe_advance_round()`` once **every** task it
contains has finished (drained out of inflight).  Retries are then
naturally paced by wave duration instead of the 5s recompute window.

All tests construct ``DispatchState`` directly with a minimal fake cfg
+ workers — no disk, no ssh, no threads.  Each test < 100ms.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path

import pytest


# --------------------------------------------------------------------------
# Fixture helpers — minimal cfg / state builders
# --------------------------------------------------------------------------

def _make_cfg(*, wave_isolation: bool = True) -> SimpleNamespace:
    """Build the smallest cfg object that DispatchState.can_start /
    reserve / maybe_advance_round inspect.  We use SimpleNamespace
    instead of OrchestraConfig (frozen dataclass) so toggling fields
    in tests is trivial."""
    return SimpleNamespace(
        model_caps={},
        default_model_cap=None,
        wave_isolation=wave_isolation,
        # per-cell backoff OFF here so these tests exercise the legacy
        # per-priority wave-isolation path.
        retry_backoff_base_seconds=0,
        retry_backoff_cap_seconds=900,
        max_attempts_per_task=3,
    )


def _make_state(tmp_path: Path, *, wave_isolation: bool = True):
    """Build a DispatchState with one fake worker pointing inflight_file
    at a writable tmp path (the atomic-rename ``_persist_inflight_locked``
    needs a real filesystem location)."""
    from scripts.orchestra.dispatch import DispatchState, WorkerState

    cfg = _make_cfg(wave_isolation=wave_isolation)
    worker_cfg = SimpleNamespace(name="w1", ssh="w1", parallel=4, skip=False)
    worker = WorkerState(cfg=worker_cfg)
    state = DispatchState(cfg=cfg, workers=[worker])
    state.inflight_file = tmp_path / "inflight.jsonl"
    state.done_file = tmp_path / "done.jsonl"
    return state, worker


def _task(suite: str, name: str, *, model_dir: str = "model-x", backend: str = "openclaw") -> dict:
    """Build a minimal task dict — keys mirror what dispatch.py reads."""
    return {
        "backend": backend,
        "model_dir": model_dir,
        "suite": suite,
        "task": name,
    }


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_dispatched_this_round_blocks_redispatch(tmp_path: Path) -> None:
    """Reserve A, release A (simulating a fast-fail drain), then check
    can_start(A) — must refuse because A is still in
    ``dispatched_this_round`` even though it's no longer in inflight."""
    state, worker = _make_state(tmp_path, wave_isolation=True)
    A = _task("s1", "A")
    assert state.can_start(A, worker) is True
    state.reserve(A, worker)
    # Now A is inflight; can_start would refuse anyway (inflight gate).
    # Simulate fast-fail drain: worker frees up, inflight clears for A.
    state.release(state.task_key(A))
    # Inflight count for the worker is 0 again, BUT A must still be
    # blocked because it's in dispatched_this_round.
    assert worker.inflight == 0
    assert state.can_start(A, worker) is False, (
        "wave isolation must block re-dispatch of a task that was reserved "
        "this round, even after release.  Without this gate the Round 14 "
        "rate_limit retry storm reopens."
    )


def test_wave_advances_when_all_dispatched_drain(tmp_path: Path) -> None:
    """Reserve A,B.  Release A — wave still active (B still inflight).
    Release B — maybe_advance_round must return True and clear the
    priority's wave subset."""
    state, worker = _make_state(tmp_path, wave_isolation=True)
    A = _task("s1", "A")
    B = _task("s1", "B")
    state.reserve(A, worker)
    state.reserve(B, worker)

    # A finishes first.
    state.release(state.task_key(A))
    # A is still in dispatched_this_round AND B is still inflight.
    advanced = state.maybe_advance_round()
    assert advanced is False, "wave must NOT advance while B is inflight"
    assert state.can_start(A, worker) is False, "A still locked by wave"

    # B finishes — wave can advance.
    state.release(state.task_key(B))
    advanced = state.maybe_advance_round()
    assert advanced is True, "wave should advance once both members drained"
    assert state.dispatched_this_round == {}
    # A is now eligible again (session_attempts gate is separate).
    assert state.can_start(A, worker) is True


def test_new_tasks_dispatchable_during_wave(tmp_path: Path) -> None:
    """Wave isolation only blocks REPEAT dispatch.  Brand-new tasks
    that have never been seen this wave must dispatch normally to any
    idle slot, even while older wave members are still running."""
    state, worker = _make_state(tmp_path, wave_isolation=True)
    A = _task("s1", "A")
    B = _task("s1", "B")
    C = _task("s1", "C")  # never reserved before

    state.reserve(A, worker)
    state.reserve(B, worker)
    # A fast-fails, freeing a worker slot.
    state.release(state.task_key(A))
    # A locked by wave; C is fresh → must be dispatchable.
    assert state.can_start(A, worker) is False
    assert state.can_start(C, worker) is True, (
        "fresh task C (not in dispatched_this_round) must be dispatchable "
        "even while wave members A/B are still tracked."
    )
    state.reserve(C, worker)
    # And C joins the wave going forward (under its bucket, default None
    # here because the test task has no priority_id).
    assert any(
        state.task_key(C) in members
        for members in state.dispatched_this_round.values()
    )


def test_wave_isolation_off_falls_back_to_old_behavior(tmp_path: Path) -> None:
    """With cfg.wave_isolation=False, the gate disappears: a released
    task can be immediately re-dispatched (subject to session_attempts).
    This is the legacy/opt-out path; we pin it so the config flag is
    real, not cosmetic."""
    state, worker = _make_state(tmp_path, wave_isolation=False)
    A = _task("s1", "A")
    state.reserve(A, worker)
    state.release(state.task_key(A))
    # With wave isolation off, A is immediately re-dispatchable.
    assert state.can_start(A, worker) is True
    # And dispatched_this_round must stay empty (reserve is a no-op for
    # the dict when the flag is off).
    assert state.dispatched_this_round == {}
    assert state.maybe_advance_round() is False  # no-op


# --------------------------------------------------------------------------
# Round 16 / P1-1 — per-priority wave (P1 drains while P3 still running)
# --------------------------------------------------------------------------


def _task_with_priority(suite: str, name: str, pid: str, **kw) -> dict:
    return {**_task(suite, name, **kw), "priority_id": pid}


def test_per_priority_wave_advances_p1_while_p3_running(tmp_path: Path) -> None:
    """P1's subset drains → maybe_advance_round releases the P1 wave
    even if P3 still has live inflight.  This is the new per-priority
    contract: a fail-fast P1 task no longer blocks behind a slow P3."""
    state, worker = _make_state(tmp_path, wave_isolation=True)
    p1a = _task_with_priority("s1", "p1a", "P1_first")
    p1b = _task_with_priority("s1", "p1b", "P1_first")
    p3a = _task_with_priority("s1", "p3a", "P3_other", model_dir="model-y")

    state.reserve(p1a, worker)
    state.reserve(p1b, worker)
    state.reserve(p3a, worker)

    # P1 finishes both members; P3 still inflight.
    state.release(state.task_key(p1a))
    state.release(state.task_key(p1b))
    advanced = state.maybe_advance_round()
    assert advanced is True, "P1 wave must advance even while P3 has inflight"
    # P1 entry is gone, P3 entry still present.
    assert "P1_first" not in state.dispatched_this_round
    assert "P3_other" in state.dispatched_this_round
    assert state.task_key(p3a) in state.dispatched_this_round["P3_other"]


def test_per_priority_wave_lets_failed_p1_retry_via_p2(tmp_path: Path) -> None:
    """A task originally dispatched in the P1 wave can be re-dispatched
    in the next wave under a different priority (e.g. P2_recoverable
    after recompute reclassifies its status) once its P1 wave drains —
    without waiting for unrelated priorities (P3/P4) to finish."""
    state, worker = _make_state(tmp_path, wave_isolation=True)
    failer = _task_with_priority("s1", "failer", "P1_first")
    slow_p3 = _task_with_priority("s1", "slow", "P3_other", model_dir="model-y")

    state.reserve(failer, worker)
    state.reserve(slow_p3, worker)
    # P1 fails fast; P3 is still grinding.
    state.release(state.task_key(failer))
    state.maybe_advance_round()
    # Recompute would have moved ``failer`` from P1 to P2_recoverable.
    failer_retry = {**failer, "priority_id": "P2_recoverable"}
    # The wave-isolation gate must now allow the retry.
    assert state.can_start(failer_retry, worker) is True, (
        "P2 retry must be allowed once the original P1 wave drained, "
        "regardless of P3 still running"
    )
    state.reserve(failer_retry, worker)
    # Joins the new P2 wave subset.
    assert state.task_key(failer_retry) in state.dispatched_this_round["P2_recoverable"]
    # The P3 subset is untouched.
    assert "P3_other" in state.dispatched_this_round


def test_per_priority_wave_cross_bucket_dedup_blocks_double_dispatch(
    tmp_path: Path,
) -> None:
    """If a task is somehow tagged under TWO priorities simultaneously
    (stale flat_tasks cache after recompute), the cross-bucket
    ``any(key in s ...)`` check must still refuse the second
    dispatch.  Without this guard a fail-fast task could ride two
    waves at once and exceed worker / model_cap budgets."""
    state, worker = _make_state(tmp_path, wave_isolation=True)
    t_p1 = _task_with_priority("s1", "dup", "P1_first")
    t_p2 = {**t_p1, "priority_id": "P2_recoverable"}

    state.reserve(t_p1, worker)
    # Same task key under a different priority id — must be refused.
    assert state.can_start(t_p2, worker) is False, (
        "cross-bucket dedup must block re-dispatch of the same task "
        "key even when offered under a different priority"
    )


def test_per_priority_wave_session_attempts_still_caps_route_to_p100(
    tmp_path: Path,
) -> None:
    """The session-attempts gate still routes a task past
    GLOBAL_MAX_ATTEMPTS to P100, even when wave isolation cleared the
    earlier subset.  The gate (priority_id-aware) and the wave subset
    compose: wave paces retries, session_attempts caps total.

    V7: session_attempts is now bumped in _drain_done_file (not reserve);
    this test simulates the post-DONE state by setting the counter
    directly, since the bump mechanism is covered separately in
    test_orchestra_session_attempts_v7.py.
    """
    from scripts.orchestra import stats as stats_mod

    state, worker = _make_state(tmp_path, wave_isolation=True)
    t_p1 = _task_with_priority("s1", "looper", "P1_first")

    # Simulate 3 successful round-trips under P1: each DONE bumps
    # session_attempts; wave advance + release happen between waves.
    for _ in range(stats_mod.GLOBAL_MAX_ATTEMPTS):
        state.reserve(t_p1, worker)
        state.release(state.task_key(t_p1))
        # _drain_done_file's bump simulated:
        state.session_attempts[state.task_key(t_p1)] = (
            state.session_attempts.get(state.task_key(t_p1), 0) + 1
        )
        state.maybe_advance_round()
    assert state.session_attempts[state.task_key(t_p1)] == stats_mod.GLOBAL_MAX_ATTEMPTS

    # Next attempt under any user bucket: session gate refuses.
    assert state.can_start(t_p1, worker) is False
    # But if the dispatcher routes it as P100 (graveyard), the
    # priority_id-aware gate allows it through.
    p100_task = {**t_p1, "priority_id": stats_mod.P100_BUCKET_ID}
    assert state.can_start(p100_task, worker) is True


def test_session_attempts_still_caps_within_wave_isolation(tmp_path: Path) -> None:
    """Wave isolation does NOT replace the GLOBAL_MAX_ATTEMPTS=3 ceiling.
    Across 3 waves a task's session_attempts grows to 3 and can_start
    must refuse — the two gates compose.

    V7: session_attempts is now bumped in _drain_done_file (not reserve);
    bump simulated here so the test focuses on can_start gate composition.
    """
    from scripts.orchestra import stats as stats_mod

    state, worker = _make_state(tmp_path, wave_isolation=True)
    A = _task("s1", "A")

    def _simulate_done_roundtrip(t: dict) -> None:
        state.reserve(t, worker)
        state.release(state.task_key(t))
        # _drain_done_file's bump simulated:
        state.session_attempts[state.task_key(t)] = (
            state.session_attempts.get(state.task_key(t), 0) + 1
        )
        state.maybe_advance_round()

    _simulate_done_roundtrip(A)  # Wave 1
    _simulate_done_roundtrip(A)  # Wave 2
    _simulate_done_roundtrip(A)  # Wave 3
    # session_attempts[A] now equals GLOBAL_MAX_ATTEMPTS (3 by default).
    assert state.session_attempts[state.task_key(A)] == stats_mod.GLOBAL_MAX_ATTEMPTS
    # Wave 4 attempt: blocked by session_attempts gate (not by wave gate
    # — that one just cleared).  Confirms the two gates compose: wave
    # isolation paces retries; session_attempts caps total retries.
    assert state.can_start(A, worker) is False
