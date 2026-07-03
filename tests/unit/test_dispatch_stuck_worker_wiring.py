"""Wiring for the dispatcher stuck-worker detector:

  * the drain records each worker's most-recent DONE time, and
  * ``_flag_stuck_workers`` emits a deduped STUCK warning and clears on recovery.

The pure detection logic is covered in test_dispatch_stuck_worker.py; this file
pins the integration glue that feeds it live state.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

from scripts.orchestra.dispatch import (
    DispatchState,
    WorkerState,
    _drain_done_file,
    _flag_stuck_workers,
)


def _make_state(tmp_path: Path, *, stuck_cell_age_seconds: int = 2700):
    cfg = SimpleNamespace(
        model_caps={},
        default_model_cap=None,
        wave_isolation=True,
        retry_backoff_base_seconds=0,
        retry_backoff_cap_seconds=900,
        max_attempts_per_task=3,
        stuck_cell_age_seconds=stuck_cell_age_seconds,
        controller=SimpleNamespace(data_root=tmp_path),
    )
    worker = WorkerState(cfg=SimpleNamespace(name="worker1", ssh="worker1", parallel=8, skip=False))
    state = DispatchState(cfg=cfg, workers=[worker])
    state.inflight_file = tmp_path / "inflight.jsonl"
    state.done_file = tmp_path / "done.jsonl"
    return state, worker


def _task(name: str) -> dict:
    return {"backend": "openclaw", "model_dir": "m", "suite": "101", "task": name}


def _done_row(name: str) -> str:
    return json.dumps(
        {"backend": "openclaw", "model_dir": "m", "suite": "101",
         "task": name, "transferred": True, "host_tag": "worker1"}
    ) + "\n"


def test_drain_records_last_done_per_worker(tmp_path):
    state, worker = _make_state(tmp_path)
    state.reserve(_task("X"), worker)
    state.done_file.write_text(_done_row("X"))

    assert _drain_done_file(state) == 1
    # The worker that round-tripped is recorded so the stall detector can tell
    # "produced a DONE recently" from "silent".
    assert "worker1" in state.last_done_ts_by_worker
    assert state.last_done_ts_by_worker["worker1"] > 0


def test_flag_stuck_workers_warns_once_then_dedupes(tmp_path, caplog):
    state, worker = _make_state(tmp_path, stuck_cell_age_seconds=2700)
    now = 100_000.0
    # An inflight cell aged 50 min, worker never produced a DONE.
    key = ("openclaw", "m", "101", "A")
    state.inflight_by_task[key] = {
        "backend": "openclaw", "model_dir": "m", "suite": "101", "task": "A",
        "worker": "worker1", "ts_start": now - 3000,
    }

    with caplog.at_level(logging.WARNING, logger="orchestra.dispatch"):
        findings = _flag_stuck_workers(state, now)
        assert [f["worker"] for f in findings] == ["worker1"]
        assert "worker1" in state.stuck_flagged_workers
        stuck_warnings = [r for r in caplog.records if "STUCK worker=worker1" in r.getMessage()]
        assert len(stuck_warnings) == 1

        # Second pass while still stuck: no duplicate warning.
        _flag_stuck_workers(state, now + 5)
        stuck_warnings = [r for r in caplog.records if "STUCK worker=worker1" in r.getMessage()]
        assert len(stuck_warnings) == 1


def test_flag_stuck_workers_clears_on_recovery(tmp_path, caplog):
    state, worker = _make_state(tmp_path, stuck_cell_age_seconds=2700)
    now = 100_000.0
    key = ("openclaw", "m", "101", "A")
    state.inflight_by_task[key] = {
        "backend": "openclaw", "model_dir": "m", "suite": "101", "task": "A",
        "worker": "worker1", "ts_start": now - 3000,
    }
    _flag_stuck_workers(state, now)
    assert "worker1" in state.stuck_flagged_workers

    # Worker recovers: reports a DONE (recorded) so it is no longer silent.
    state.last_done_ts_by_worker["worker1"] = now + 1
    with caplog.at_level(logging.INFO, logger="orchestra.dispatch"):
        findings = _flag_stuck_workers(state, now + 2)
    assert findings == []
    assert "worker1" not in state.stuck_flagged_workers
    assert any("STUCK cleared worker=worker1" in r.getMessage() for r in caplog.records)


def test_detector_disabled_when_age_zero(tmp_path):
    state, worker = _make_state(tmp_path, stuck_cell_age_seconds=0)
    now = 100_000.0
    key = ("openclaw", "m", "101", "A")
    state.inflight_by_task[key] = {
        "backend": "openclaw", "model_dir": "m", "suite": "101", "task": "A",
        "worker": "worker1", "ts_start": now - 99_999,
    }
    assert _flag_stuck_workers(state, now) == []
    assert state.stuck_flagged_workers == set()
