"""Round-5 Phase 5b — pin top.py done_history reader.

Round-4 Phase 3.4 changed done.jsonl drain from "truncate-in-place" to
"rename to done_history/done_<utc-ts>.jsonl directory rotation".  But
``top.py:read_runtime_progress`` was reading the legacy
``done_history.jsonl`` single file, missed the rotated directory,
returned empty progress, and showed all 0s in the ``top`` panel.

This test pins:
  - directory format (rotated) → progress correctly aggregated
  - legacy single-file format → still read (back-compat)
  - directory preferred when both exist
  - empty / missing → empty progress dict
"""
from __future__ import annotations

import json
from pathlib import Path

import scripts.orchestra.top as top_mod


def _write_row(host: str, status: str) -> str:
    return json.dumps({
        "backend": "openclaw",
        "model_dir": "m1",
        "suite": "s",
        "task": f"task_for_{host}_{status}",
        "host_tag": host,
        "status": status,
        "rc": 0,
    })


def test_reads_rotated_directory(tmp_path):
    """3 rotated archive files → aggregated progress across all."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    archive_dir = runtime / "done_history"
    archive_dir.mkdir()
    # 3 archives, each with a different row
    (archive_dir / "done_20260513_120000_000001.jsonl").write_text(
        _write_row("worker3", "pass") + "\n"
    )
    (archive_dir / "done_20260513_120100_000002.jsonl").write_text(
        _write_row("worker3", "fail") + "\n"
        + _write_row("worker4", "executor_incomplete") + "\n"
    )
    (archive_dir / "done_20260513_120200_000003.jsonl").write_text(
        _write_row("worker4", "pass") + "\n"
    )

    out = top_mod.read_runtime_progress(runtime)
    assert "worker3" in out
    assert "worker4" in out
    assert out["worker3"].done == 2
    assert out["worker3"].pass_ == 1
    assert out["worker3"].completed == 2  # pass + fail both in TERMINAL set
    assert out["worker4"].done == 2
    assert out["worker4"].pass_ == 1
    assert out["worker4"].incomplete == 1  # executor_incomplete


def test_reads_legacy_single_file(tmp_path):
    """Back-compat: pre-Round-4 single-file format still works."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    legacy = runtime / "done_history.jsonl"
    legacy.write_text(
        _write_row("worker1", "pass") + "\n"
        + _write_row("worker1", "fail") + "\n"
    )

    out = top_mod.read_runtime_progress(runtime)
    assert "worker1" in out
    assert out["worker1"].done == 2
    assert out["worker1"].pass_ == 1
    assert out["worker1"].completed == 2


def test_directory_preferred_over_legacy(tmp_path):
    """If BOTH formats exist, the rotated directory wins (newer, post-Round-4)."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    legacy = runtime / "done_history.jsonl"
    legacy.write_text(_write_row("ol_legacy", "pass") + "\n")
    archive_dir = runtime / "done_history"
    archive_dir.mkdir()
    (archive_dir / "done_20260513_120000_000001.jsonl").write_text(
        _write_row("ol_directory", "pass") + "\n"
    )

    out = top_mod.read_runtime_progress(runtime)
    assert "ol_directory" in out
    assert "ol_legacy" not in out  # legacy ignored when directory present


def test_neither_exists_returns_empty(tmp_path):
    """No history at all → empty dict, not error."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    out = top_mod.read_runtime_progress(runtime)
    assert out == {}
