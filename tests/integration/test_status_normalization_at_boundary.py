"""Regression: legacy / non-canonical finalStatus values from per-attempt
summary.json must be normalised before ranking and bucketing.

From the 2026-05-13 code review:

> Both aggregation paths read ``finalStatus`` as raw text and rank or
> bucket it directly. ``refresh_summary.refresh_one_task()`` then
> compares those raw values with ``status_rank()``, which only knows
> canonical values.  A legacy status like ``continue`` therefore gets
> rank ``0`` and can lose to ``missing``, so the rolled-up task summary
> can become ``missing`` instead of ``executor_incomplete``.

This file pins:

- A per-attempt summary.json carrying the legacy ``continue`` value is
  rolled up to ``executor_incomplete`` (the canonicalisation of
  ``continue``), not ``missing``.
- ``scripts/orchestra/stats._read_status`` returns canonical names so
  the priority bucketing config and the dashboard see the same
  vocabulary regardless of which generation wrote the summary.
"""
from __future__ import annotations

import json
from pathlib import Path


def _write_attempt_summary(p_dir: Path, *, final_status: str, passed: bool = False) -> None:
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "summary.json").write_text(
        json.dumps({"finalStatus": final_status, "passed": passed}),
        encoding="utf-8",
    )


def test_refresh_summary_normalises_legacy_continue_status(tmp_path: Path) -> None:
    """A per-attempt summary.json with legacy ``finalStatus="continue"``
    must be rolled up to ``executor_incomplete``.  Pre-fix, ``continue``
    got ``status_rank == 0`` (unknown) and lost to ``missing``, so the
    task-level summary.json reported ``missing`` instead of the correct
    ``executor_incomplete``."""
    from scripts.orchestra.refresh_summary import refresh_one_task

    task_dir = tmp_path / "task_001"
    p_dir = task_dir / "p1-host-aaa"
    _write_attempt_summary(p_dir, final_status="continue", passed=False)

    summary = refresh_one_task(task_dir)
    assert summary is not None
    assert summary["finalStatus"] == "executor_incomplete", summary["finalStatus"]


def test_refresh_summary_prefers_executor_incomplete_over_missing(tmp_path: Path) -> None:
    """When multiple attempts carry legacy statuses, the rollup must
    canonicalise both and then pick the higher-ranked outcome."""
    from scripts.orchestra.refresh_summary import refresh_one_task

    task_dir = tmp_path / "task_002"
    # Attempt 1: a legacy ``continue`` that should canonicalise to
    # ``executor_incomplete``.
    _write_attempt_summary(task_dir / "p1-host-aaa", final_status="continue")
    # Attempt 2: a canonical ``missing`` (lowest meaningful rank).
    _write_attempt_summary(task_dir / "p2-host-bbb", final_status="missing")

    summary = refresh_one_task(task_dir)
    assert summary is not None
    # executor_incomplete (rank 6) must beat missing (rank 1).
    assert summary["finalStatus"] == "executor_incomplete", summary["finalStatus"]


def test_stats_read_status_normalises_legacy_continue(tmp_path: Path) -> None:
    """``stats._read_status`` reads the task-level rolled-up summary.json
    and feeds the value into the priority-bucket matcher.  After
    Round-6 the read path must canonicalise, so legacy summaries that
    still carry ``continue`` are routed into the ``executor_incomplete``
    bucket (the same place the runtime classifier would have produced)."""
    from scripts.orchestra.stats import TaskKey, _read_status

    runs_root = tmp_path / "runs"
    backend = "openclaw"
    model_dir = "fake-model-1-0"
    suite = "101_a"
    task = "task_007"
    task_dir = runs_root / backend / model_dir / suite / task
    task_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text(
        json.dumps({"finalStatus": "continue"}),
        encoding="utf-8",
    )

    status = _read_status(runs_root, TaskKey(backend, model_dir, suite, task))
    assert status == "executor_incomplete", status


def test_stats_read_status_canonicalises_no_summary_to_missing(tmp_path: Path) -> None:
    """The file-state sentinels ``no_summary`` / ``broken_json`` must
    also leave ``_read_status`` as canonical values so the priority
    config sees a uniform vocabulary."""
    from scripts.orchestra.stats import TaskKey, _read_status

    runs_root = tmp_path / "runs"
    key = TaskKey("openclaw", "fake-model", "101_a", "task_001")
    # No summary.json on disk.
    status = _read_status(runs_root, key)
    assert status == "missing", status


def test_stats_read_status_canonicalises_broken_json_to_missing(tmp_path: Path) -> None:
    from scripts.orchestra.stats import TaskKey, _read_status

    runs_root = tmp_path / "runs"
    backend = "openclaw"
    model_dir = "fake-model"
    suite = "101_a"
    task = "task_002"
    task_dir = runs_root / backend / model_dir / suite / task
    task_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text("{NOT VALID JSON", encoding="utf-8")

    status = _read_status(runs_root, TaskKey(backend, model_dir, suite, task))
    assert status == "missing", status


def test_synth_record_runtimeMs_no_wallclock_fallback(tmp_path: Path) -> None:
    """Round 8 / A5 regression: ``runtimeMs`` is the EXECUTOR-only elapsed
    time; if meta lacks it, the synth record must leave it absent (so the
    aggregator skips this row's runtime contribution) instead of using
    ``wallClockMs`` as a proxy.

    Pre-fix code did ``meta.get("runtimeMs") or meta.get("wallClockMs")``
    which silently polluted Results-page avg-runtime with grader +
    user-simulator time."""
    import json
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts

    p_dir = tmp_path / "p1-test"
    p_dir.mkdir()
    (p_dir / "score.json").write_text(
        json.dumps({"verdict": "pass", "passed": True}),
        encoding="utf-8",
    )
    (p_dir / "meta.json").write_text(
        # Only wallClockMs is present; runtimeMs is intentionally absent.
        json.dumps({"wallClockMs": 9000, "everExecutorCompleted": True}),
        encoding="utf-8",
    )

    record = _derive_status_from_artifacts(p_dir)
    assert record is not None
    # runtimeMs must NOT be filled from wallClockMs.
    assert record.get("runtimeMs") is None, (
        f"runtimeMs leaked from wallClockMs: {record.get('runtimeMs')}"
    )
    # wallClockMs stays as a separate diagnostic field.
    assert record.get("wallClockMs") == 9000


def test_synth_record_keeps_runtimeMs_when_present(tmp_path: Path) -> None:
    """If meta has runtimeMs, use it (executor-only)."""
    import json
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts

    p_dir = tmp_path / "p1-test"
    p_dir.mkdir()
    (p_dir / "score.json").write_text(json.dumps({"verdict": "fail"}), encoding="utf-8")
    (p_dir / "meta.json").write_text(
        json.dumps({"runtimeMs": 5500, "wallClockMs": 9000, "everExecutorCompleted": True}),
        encoding="utf-8",
    )

    record = _derive_status_from_artifacts(p_dir)
    assert record is not None
    assert record["runtimeMs"] == 5500
    assert record["wallClockMs"] == 9000
