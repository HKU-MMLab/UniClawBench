"""V7 — session_attempts is bumped on DONE, not on reserve; SSH failures
have their own ceiling that force-promotes to P100 at 5 consecutive
failures.

The original bug (V6 root-cause for the "10 task ghost-missed" symptom):
  1. Dispatcher main() submits 30 SSH calls within one second; worker sshd
     hits MaxStartups and ~10 connections die with
     "kex_exchange_identification: Connection reset by peer".
  2. ``reserve()`` had already bumped ``session_attempts[key] += 1`` for
     each of those 10 dispatches before SSH was even attempted.
  3. ``_ssh_worker_run`` saw rc!=0, called ``state.release(key)`` to free
     the inflight slot, but **never decremented session_attempts**.  After
     3 retries the task's session_attempts hit ``GLOBAL_MAX_ATTEMPTS=3``
     and ``can_start`` blocked it forever via the P100 graveyard.
  4. Result: 10 tasks dispatched-but-never-ran disappeared from the queue
     for 3 hours until manual ``rm inflight.jsonl`` rescue.

V7 fix (this module under test):
  - reserve() no longer touches session_attempts
  - _drain_done_file bumps session_attempts ONLY on a DONE row we
    successfully release (i.e. a real round-trip from a worker)
  - SSH failures are counted separately in ssh_fail_attempts; at
    SSH_FAIL_CEILING=5 we force session_attempts to GLOBAL_MAX_ATTEMPTS
    so a genuinely unreachable target gets pulled from circulation
  - A successful SSH ``rc==0`` clears ssh_fail_attempts for that key
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def _make_cfg(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        model_caps={},
        default_model_cap=None,
        wave_isolation=False,
        retry_backoff_base_seconds=0,
        retry_backoff_cap_seconds=900,
        max_attempts_per_task=3,
        # _drain_done_file calls cfg_mod.runs_root(cfg) which dereferences
        # cfg.controller.data_root — give it a tmp dir so the function
        # builds a path it can stat without exploding.
        controller=SimpleNamespace(data_root=tmp_path),
    )


def _make_state(tmp_path: Path):
    """Minimal DispatchState with one fake worker, tmp inflight + done files."""
    from scripts.orchestra.dispatch import DispatchState, WorkerState

    cfg = _make_cfg(tmp_path)
    worker_cfg = SimpleNamespace(name="w1", ssh="w1", parallel=4, skip=False)
    worker = WorkerState(cfg=worker_cfg)
    state = DispatchState(cfg=cfg, workers=[worker])
    state.inflight_file = tmp_path / "inflight.jsonl"
    state.done_file = tmp_path / "done.jsonl"
    state.done_file.touch()
    return state, worker


def _task(name: str, *, model_dir: str = "model-x", suite: str = "s1") -> dict:
    return {
        "backend": "openclaw",
        "model_dir": model_dir,
        "suite": suite,
        "task": name,
    }


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_session_attempts_not_bumped_on_reserve(tmp_path: Path) -> None:
    """V6 bug: reserve() bumped session_attempts before SSH dispatch.
    V7 fix: reserve() leaves session_attempts untouched."""
    state, worker = _make_state(tmp_path)
    t = _task("alpha")
    key = state.task_key(t)

    state.reserve(t, worker)

    assert state.session_attempts.get(key, 0) == 0
    # Inflight bookkeeping still works
    assert key in state.inflight_by_task
    assert worker.inflight == 1


def test_session_attempts_bumped_on_drained_done(tmp_path: Path) -> None:
    """V7: session_attempts is incremented when _drain_done_file processes
    a DONE row and successfully releases the inflight slot."""
    from scripts.orchestra.dispatch import _drain_done_file

    state, worker = _make_state(tmp_path)
    t = _task("beta")
    key = state.task_key(t)

    state.reserve(t, worker)
    # Worker reports back via done.jsonl (transferred=True = result rsynced)
    payload = {
        **t,
        "host_tag": "w1",
        "status": "pass",
        "rc": 0,
        "transferred": True,
        "transferred_reason": "ok",
        "duration_sec": 1,
        "started_at": "2026-05-20T00:00:00",
        "ended_at": "2026-05-20T00:00:01",
        "attempt_id": "w1-abc",
        "attempt_dir": str(tmp_path / "ignored"),
    }
    state.done_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    _drain_done_file(state)

    assert state.session_attempts[key] == 1
    assert key not in state.inflight_by_task


def test_session_attempts_not_bumped_on_transferred_false(tmp_path: Path) -> None:
    """V7: DONE rows with transferred=False keep inflight held (TTL path)
    and do NOT count toward session_attempts (we never got the result)."""
    from scripts.orchestra.dispatch import _drain_done_file

    state, worker = _make_state(tmp_path)
    t = _task("gamma")
    key = state.task_key(t)

    state.reserve(t, worker)
    payload = {
        **t,
        "host_tag": "w1",
        "status": "missing",
        "rc": 0,
        "transferred": False,
        "transferred_reason": "rsync_failed",
        "duration_sec": 1,
        "started_at": "2026-05-20T00:00:00",
        "ended_at": "2026-05-20T00:00:01",
        "attempt_id": "w1-xyz",
        "attempt_dir": str(tmp_path / "ignored"),
    }
    state.done_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    _drain_done_file(state)

    # transferred=False → continue → don't bump
    assert state.session_attempts.get(key, 0) == 0
    # And inflight stays held; TTL pass handles it later
    assert key in state.inflight_by_task


def test_ssh_fail_threshold_force_promotes_to_p100(tmp_path: Path) -> None:
    """V7: a task hitting SSH_FAIL_CEILING failures gets its
    session_attempts forced to GLOBAL_MAX_ATTEMPTS so recompute moves it
    to P100 (graveyard) and stops burning slots on an unreachable target.
    """
    from scripts.orchestra import stats as stats_mod
    from scripts.orchestra.dispatch import (
        SSH_FAIL_CEILING, _bump_ssh_fail_attempts,
    )

    state, worker = _make_state(tmp_path)
    t = _task("delta")
    key = state.task_key(t)

    for _ in range(SSH_FAIL_CEILING - 1):
        _bump_ssh_fail_attempts(state, key)
    assert state.session_attempts.get(key, 0) < stats_mod.GLOBAL_MAX_ATTEMPTS

    # The ceiling-hit call should promote
    _bump_ssh_fail_attempts(state, key)
    assert state.ssh_fail_attempts[key] == SSH_FAIL_CEILING
    assert state.session_attempts[key] >= stats_mod.GLOBAL_MAX_ATTEMPTS


def test_ssh_fail_attempts_cleared_on_successful_dispatch(tmp_path: Path) -> None:
    """V7: when a task's SSH dispatch finally lands (rc==0), the counter
    is cleared so flapping connectivity doesn't slowly accumulate to
    the P100 ceiling across hours."""
    from scripts.orchestra.dispatch import (
        _bump_ssh_fail_attempts, _reset_ssh_fail_attempts,
    )

    state, _ = _make_state(tmp_path)
    t = _task("epsilon")
    key = state.task_key(t)

    _bump_ssh_fail_attempts(state, key)
    _bump_ssh_fail_attempts(state, key)
    assert state.ssh_fail_attempts[key] == 2

    _reset_ssh_fail_attempts(state, key)
    assert key not in state.ssh_fail_attempts


def test_drained_done_clears_ssh_fail_attempts(tmp_path: Path) -> None:
    """V7: a DONE row implies the worker round-tripped, so any SSH-level
    failure accumulation for this key is stale — clear it.
    """
    from scripts.orchestra.dispatch import _drain_done_file, _bump_ssh_fail_attempts

    state, worker = _make_state(tmp_path)
    t = _task("zeta")
    key = state.task_key(t)

    state.reserve(t, worker)
    _bump_ssh_fail_attempts(state, key)
    _bump_ssh_fail_attempts(state, key)
    assert state.ssh_fail_attempts[key] == 2

    payload = {
        **t,
        "host_tag": "w1",
        "status": "pass",
        "rc": 0,
        "transferred": True,
        "transferred_reason": "ok",
        "duration_sec": 1,
        "started_at": "2026-05-20T00:00:00",
        "ended_at": "2026-05-20T00:00:01",
        "attempt_id": "w1-zzz",
        "attempt_dir": str(tmp_path / "ignored"),
    }
    state.done_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    _drain_done_file(state)

    assert state.session_attempts[key] == 1
    assert key not in state.ssh_fail_attempts
