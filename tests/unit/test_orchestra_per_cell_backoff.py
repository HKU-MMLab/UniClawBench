"""Round 17 — per-cell retry backoff (supersedes per-priority wave isolation)
and per-task attempt pruning.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from scripts.orchestra import dispatch as D
from scripts.orchestra.dispatch import DispatchState, WorkerState, _prune_task_attempts


def _make_state(tmp_path: Path, **cfg_over):
    cfg = SimpleNamespace(
        model_caps={}, default_model_cap=None, wave_isolation=True,
        retry_backoff_base_seconds=0, retry_backoff_cap_seconds=900,
        max_attempts_per_task=3, controller=SimpleNamespace(data_root=tmp_path),
    )
    for k, v in cfg_over.items():
        setattr(cfg, k, v)
    worker = WorkerState(cfg=SimpleNamespace(name="w1", ssh="w1", parallel=8, skip=False))
    state = DispatchState(cfg=cfg, workers=[worker])
    state.inflight_file = tmp_path / "inflight.jsonl"
    state.done_file = tmp_path / "done.jsonl"
    return state, worker


def _task(name="A"):
    return {"backend": "openclaw", "model_dir": "m", "suite": "101", "task": name}


# ── per-cell backoff ────────────────────────────────────────────────────────

def test_attempted_cell_blocked_within_backoff_then_allowed(tmp_path, monkeypatch):
    state, worker = _make_state(tmp_path, retry_backoff_base_seconds=30, wave_isolation=False)
    t = _task(); key = state.task_key(t)
    clock = [1000.0]
    monkeypatch.setattr(D.time, "time", lambda: clock[0])
    state.session_attempts[key] = 1          # one attempt already drained
    state.last_release_ts[key] = 1000.0
    clock[0] = 1010.0                         # 10s < 30s backoff
    assert state.can_start(t, worker) is False
    clock[0] = 1031.0                         # 31s > 30s
    assert state.can_start(t, worker) is True


def test_backoff_doubles_with_attempts(tmp_path, monkeypatch):
    state, worker = _make_state(tmp_path, retry_backoff_base_seconds=30, wave_isolation=False)
    t = _task(); key = state.task_key(t)
    clock = [1000.0]
    monkeypatch.setattr(D.time, "time", lambda: clock[0])
    state.session_attempts[key] = 2          # backoff = 30 * 2**1 = 60
    state.last_release_ts[key] = 1000.0
    clock[0] = 1050.0
    assert state.can_start(t, worker) is False
    clock[0] = 1061.0
    assert state.can_start(t, worker) is True


def test_backoff_capped(tmp_path, monkeypatch):
    # attempts=2 stays under the P100 graveyard ceiling (GLOBAL_MAX_ATTEMPTS=3)
    # so can_start exercises the backoff, not the graveyard gate.  Raw backoff
    # would be 30*2**1=60, but the cap clamps it to 50.
    state, worker = _make_state(tmp_path, retry_backoff_base_seconds=30,
                                retry_backoff_cap_seconds=50, wave_isolation=False)
    t = _task(); key = state.task_key(t)
    clock = [1000.0]
    monkeypatch.setattr(D.time, "time", lambda: clock[0])
    state.session_attempts[key] = 2
    state.last_release_ts[key] = 1000.0
    clock[0] = 1049.0                        # 49s < cap 50 -> still blocked
    assert state.can_start(t, worker) is False
    clock[0] = 1051.0                        # 51s > cap 50 (not the raw 60)
    assert state.can_start(t, worker) is True


def test_fresh_cell_never_delayed(tmp_path, monkeypatch):
    state, worker = _make_state(tmp_path, retry_backoff_base_seconds=30, wave_isolation=False)
    t = _task()
    monkeypatch.setattr(D.time, "time", lambda: 1000.0)
    # never attempted (no session_attempts / last_release_ts) -> always allowed
    assert state.can_start(t, worker) is True


def test_backoff_does_not_block_other_cells(tmp_path, monkeypatch):
    """The whole point: a backing-off cell never blocks an unrelated cell."""
    state, worker = _make_state(tmp_path, retry_backoff_base_seconds=30, wave_isolation=False)
    a, b = _task("A"), _task("B")
    monkeypatch.setattr(D.time, "time", lambda: 1000.0)
    state.session_attempts[state.task_key(a)] = 1
    state.last_release_ts[state.task_key(a)] = 1000.0
    assert state.can_start(a, worker) is False   # A is backing off
    assert state.can_start(b, worker) is True     # B unaffected


def test_wave_isolation_bypassed_when_backoff_on(tmp_path, monkeypatch):
    state, worker = _make_state(tmp_path, retry_backoff_base_seconds=30, wave_isolation=True)
    t = _task(); key = state.task_key(t)
    monkeypatch.setattr(D.time, "time", lambda: 1000.0)
    # put the cell in a "wave" — under legacy wave_isolation this would block,
    # but per-cell backoff supersedes it and the (never-attempted) cell starts.
    state.dispatched_this_round.setdefault("T1", set()).add(key)
    assert state.can_start(t, worker) is True


# ── per-task attempt pruning ────────────────────────────────────────────────

def _mk_attempts(task_dir: Path, n: int):
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "summary.json").write_text("{}")     # rollup file must survive
    for i in range(n):
        d = task_dir / ("p1-worker1-%03d" % i)
        d.mkdir()
        (d / "score.json").write_text("{}")
        os.utime(d, (1000 + i, 1000 + i))            # mtime increases with i


def test_prune_keeps_newest_n(tmp_path):
    td = tmp_path / "task"
    _mk_attempts(td, 5)
    assert _prune_task_attempts(td, 3) == 2
    kept = sorted(d.name for d in td.iterdir() if d.is_dir())
    assert kept == ["p1-worker1-002", "p1-worker1-003", "p1-worker1-004"]   # newest 3 by mtime
    assert (td / "summary.json").exists()                        # file untouched


def test_prune_noop_when_at_or_under_limit(tmp_path):
    td = tmp_path / "task"
    _mk_attempts(td, 3)
    assert _prune_task_attempts(td, 3) == 0
    assert len([d for d in td.iterdir() if d.is_dir()]) == 3


def test_prune_missing_dir_is_safe(tmp_path):
    assert _prune_task_attempts(tmp_path / "nope", 3) == 0
