"""Round 16 / P1-4 + P1-5 + P2-1: ``scripts/orchestra/top.py`` must
expose a canonical unique-task view, render synthetic P100/P200
buckets, and route all status strings through
``lib.status.normalize_final_status``.

Before this commit ``top.py`` counted every DONE callback line
(inflating completion when retries existed), ``zip(cfg.priorities,
priorities)`` silently dropped synthetic buckets, and raw status
strings like ``no_summary`` or ``FAIL_rc=137`` bypassed normalization
(fragmenting the per-worker status breakdown).
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from scripts.orchestra import top as top_mod
from scripts.orchestra.config import (
    CodexRoleCfg,
    ControllerCfg,
    OrchestraConfig,
    PriorityCfg,
    SupervisionCfg,
    WorkerCfg,
)


def _seed_index(runs_root: Path, rows: list[dict]) -> Path:
    runs_root.mkdir(parents=True, exist_ok=True)
    idx = runs_root / ".runs_index.json"
    idx.write_text(
        json.dumps({"version": 1, "rows": rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    return idx


def _seed_summary(
    runs_root: Path,
    backend: str,
    model_dir: str,
    suite: str,
    task: str,
    *,
    final_status: str,
) -> None:
    task_dir = runs_root / backend / model_dir / suite / task
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "summary.json").write_text(
        json.dumps({"finalStatus": final_status, "taskId": task}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_compute_unique_task_view_reads_index(tmp_path: Path) -> None:
    """The view should prefer ``.runs_index.json`` when available; one
    row per ``(backend, model_dir, suite, task)`` key, regardless of
    how many DONE attempts each task accumulated."""
    runs_root = tmp_path / "runs"
    _seed_index(
        runs_root,
        [
            {
                "summaryPath": "openclaw/m-opus/101_a/task_demo",
                "finalStatus": "pass",
            },
            {
                "summaryPath": "openclaw/m-opus/101_a/task_two",
                "finalStatus": "fail",
            },
            {
                "summaryPath": "nanobot/m-gpt/102_b/task_three",
                "finalStatus": "running",
            },
        ],
    )

    view = top_mod.compute_unique_task_view(runs_root)
    assert view.total == 3
    assert view.completed == 2  # pass + fail are terminal
    assert view.pending == 1  # running is non-terminal
    assert view.status_counts["pass"] == 1
    assert view.status_counts["fail"] == 1
    assert view.status_counts["running"] == 1
    assert ("openclaw", "m-opus", "101_a", "task_demo") in view.by_key
    assert view.by_key[("openclaw", "m-opus", "101_a", "task_demo")] == "pass"


def test_compute_unique_task_view_normalizes_legacy_statuses(tmp_path: Path) -> None:
    """Legacy status strings (``no_summary``, ``FAIL_rc=137``) must map
    to canonical FINAL_STATUS_ORDER members via
    ``normalize_final_status``.  Without normalization they would
    accumulate as their own buckets and the breakdown becomes noisy."""
    runs_root = tmp_path / "runs"
    _seed_index(
        runs_root,
        [
            {"summaryPath": "openclaw/m-opus/101_a/t1", "finalStatus": "no_summary"},
            {"summaryPath": "openclaw/m-opus/101_a/t2", "finalStatus": "FAIL_rc=137"},
            {"summaryPath": "openclaw/m-opus/101_a/t3", "finalStatus": "pass"},
        ],
    )

    view = top_mod.compute_unique_task_view(runs_root)
    # no_summary normalizes to "missing" (canonical for unseen).
    # FAIL_rc=N normalizes to a known status (fail or executor_incomplete).
    keys = {
        ("openclaw", "m-opus", "101_a", "t1"),
        ("openclaw", "m-opus", "101_a", "t2"),
        ("openclaw", "m-opus", "101_a", "t3"),
    }
    assert set(view.by_key.keys()) == keys
    # The legacy "no_summary" string must NOT survive as a literal bucket.
    assert "no_summary" not in view.status_counts
    assert "FAIL_rc=137" not in view.status_counts


def test_compute_unique_task_view_falls_back_to_summary_walk(tmp_path: Path) -> None:
    """When the index is missing, the view walks summary.json files
    under the runs tree."""
    runs_root = tmp_path / "runs"
    _seed_summary(runs_root, "openclaw", "m-opus", "101_a", "t1", final_status="pass")
    _seed_summary(runs_root, "nanobot", "m-gpt", "102_b", "t2", final_status="rate_limit")

    view = top_mod.compute_unique_task_view(runs_root)
    assert view.total == 2
    assert view.completed == 1  # pass is terminal; rate_limit is non-terminal
    assert ("openclaw", "m-opus", "101_a", "t1") in view.by_key
    assert view.by_key[("openclaw", "m-opus", "101_a", "t1")] == "pass"
    assert ("nanobot", "m-gpt", "102_b", "t2") in view.by_key


def test_compute_unique_task_view_handles_empty_runs(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    view = top_mod.compute_unique_task_view(runs_root)
    assert view.total == 0
    assert view.completed == 0
    assert view.pending == 0
    assert view.by_key == {}


def test_read_runtime_progress_normalizes_legacy_status(tmp_path: Path) -> None:
    """The per-worker throughput counters must collapse legacy status
    strings via ``normalize_final_status`` so the breakdown matches the
    canonical vocabulary."""
    runtime_dir = tmp_path / "runtime"
    archive_dir = runtime_dir / "done_history"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "done_seed.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "backend": "openclaw",
                    "model_dir": "m-opus",
                    "suite": "101_a",
                    "task": "t1",
                    "host_tag": "worker1",
                    "status": "no_summary",
                },
                {
                    "backend": "openclaw",
                    "model_dir": "m-opus",
                    "suite": "101_a",
                    "task": "t2",
                    "host_tag": "worker1",
                    "status": "pass",
                },
            ]
        ),
        encoding="utf-8",
    )

    progress = top_mod.read_runtime_progress(runtime_dir)
    assert "worker1" in progress
    counts = progress["worker1"].status_counts
    assert counts is not None
    # Both rows normalize to canonical statuses; raw "no_summary" must
    # not survive as its own bucket.
    assert "no_summary" not in counts
    assert counts.get("pass", 0) == 1


def test_render_iterates_all_priority_buckets_including_synthetic(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The renderer must show synthetic P100/P200 buckets, not just the
    user-defined ones from ``cfg.priorities``.  Before P1-5 the
    ``zip(cfg.priorities, priorities)`` truncated the iteration."""
    cfg = OrchestraConfig(
        controller=ControllerCfg(host="controller", data_root=tmp_path, webui_port=9999),
        workers=(WorkerCfg(name="worker1", ssh="worker1", parallel=1),),
        priorities=(
            PriorityCfg(id="P1_first", label="first pass"),
        ),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
    )

    snaps = [top_mod.WorkerSnapshot(name="worker1", reachable=True, inflight=0)]
    progress = {"worker1": top_mod.WorkerProgress(status_counts=collections.Counter())}
    priorities = [
        {"priority_id": "P1_first", "label": "first pass", "tasks": [{"x": 1}]},
        {
            "priority_id": "P100_session_exhausted",
            "label": "session-3 graveyard",
            "tasks": [{"x": 2}, {"x": 3}],
        },
        {
            "priority_id": "P200_suspended",
            "label": "session-6 suspended",
            "tasks": [{"x": 4}],
        },
    ]
    unique_view = top_mod.UniqueTaskView(
        by_key={}, status_counts=collections.Counter(),
        total=0, completed=0, pending=0,
    )

    top_mod.render(cfg, snaps, progress, priorities, [], unique_view)
    captured = capsys.readouterr().out

    assert "P1_first" in captured
    assert "P100_session_exhausted" in captured, (
        "render must surface synthetic P100 bucket"
    )
    assert "P200_suspended" in captured, (
        "render must surface synthetic P200 bucket"
    )
    # remaining counts must match the buckets' task counts.
    assert "remaining=1" in captured
    assert "remaining=2" in captured
    assert "remaining=2" in captured


def test_render_includes_unique_task_summary_line(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """When a non-empty UniqueTaskView is provided, the renderer prints
    the ``Tasks (unique-by-task)`` block with total/completed/pending."""
    cfg = OrchestraConfig(
        controller=ControllerCfg(host="controller", data_root=tmp_path, webui_port=9999),
        workers=(WorkerCfg(name="worker1", ssh="worker1", parallel=1),),
        priorities=(),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
    )
    snaps = [top_mod.WorkerSnapshot(name="worker1", reachable=True, inflight=0)]
    progress = {"worker1": top_mod.WorkerProgress(status_counts=collections.Counter())}
    priorities = [{"priority_id": "P1", "label": "p1", "tasks": []}]
    unique_view = top_mod.UniqueTaskView(
        by_key={
            ("openclaw", "m1", "101", "t1"): "pass",
            ("openclaw", "m1", "101", "t2"): "fail",
            ("openclaw", "m1", "101", "t3"): "missing",
        },
        status_counts=collections.Counter({"pass": 1, "fail": 1, "missing": 1}),
        total=3,
        completed=2,
        pending=1,
    )

    top_mod.render(cfg, snaps, progress, priorities, [], unique_view)
    captured = capsys.readouterr().out

    assert "Tasks (unique-by-task)" in captured
    assert "total=3" in captured
    assert "completed=2" in captured
    assert "pending=1" in captured
