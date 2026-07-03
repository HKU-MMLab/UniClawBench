"""Regression: ``_drain_done_file`` must not lose a DONE row that a worker
appends *during* the drain.

The original order (read snapshot → rename → process the snapshot) lost any
row appended in the read→rename window: it was carried into the archive but
never parsed, so its inflight slot was never released — pinned forever, and
under ``wave_isolation`` its priority's wave never drained (global stall).
The fix rotates first, then reads the rotated file.  See
``scripts/orchestra/dispatch.py:_drain_done_file``.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.orchestra.dispatch import DispatchState, WorkerState, _drain_done_file


def _make_state(tmp_path: Path):
    cfg = SimpleNamespace(
        model_caps={},
        default_model_cap=None,
        wave_isolation=True,
        retry_backoff_base_seconds=0,
        retry_backoff_cap_seconds=900,
        max_attempts_per_task=3,
        controller=SimpleNamespace(data_root=tmp_path),
    )
    worker = WorkerState(cfg=SimpleNamespace(name="w1", ssh="w1", parallel=8, skip=False))
    state = DispatchState(cfg=cfg, workers=[worker])
    state.inflight_file = tmp_path / "inflight.jsonl"
    state.done_file = tmp_path / "done.jsonl"
    return state, worker


def _task(name: str) -> dict:
    return {"backend": "openclaw", "model_dir": "m", "suite": "101", "task": name}


def _done_row(name: str) -> str:
    return (
        json.dumps(
            {"backend": "openclaw", "model_dir": "m", "suite": "101",
             "task": name, "transferred": True}
        )
        + "\n"
    )


def test_drain_processes_row_appended_in_read_rename_window(tmp_path, monkeypatch):
    state, worker = _make_state(tmp_path)
    for n in ("A", "B", "C"):
        state.reserve(_task(n), worker)
    assert len(state.inflight_by_task) == 3

    # done.jsonl already names A and B when the drain starts.
    state.done_file.write_text(_done_row("A") + _done_row("B"))

    # Simulate a worker SSH append for C that lands *between* the (old) read
    # and the rename: wrap Path.replace so C is appended to done.jsonl right
    # before the rename of done.jsonl actually happens.
    real_replace = Path.replace

    def racey_replace(self, target):
        if Path(self) == state.done_file:
            with open(self, "a", encoding="utf-8") as fh:
                fh.write(_done_row("C"))
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", racey_replace)

    released = _drain_done_file(state)

    # All three — including the racing C — must be released. With the old
    # read-then-rename order, C would be lost and stay pinned in inflight.
    assert released == 3, released
    assert state.inflight_by_task == {}


def test_drain_empty_file_is_noop(tmp_path):
    state, _ = _make_state(tmp_path)
    state.done_file.write_text("")
    assert _drain_done_file(state) == 0
    assert not (tmp_path / "done_history").exists()


def test_drain_releases_plain_rows(tmp_path):
    state, worker = _make_state(tmp_path)
    state.reserve(_task("X"), worker)
    state.done_file.write_text(_done_row("X"))
    assert _drain_done_file(state) == 1
    assert state.inflight_by_task == {}
