"""Round 8 / A3 regression: /api/aggregate filters to terminal-result statuses.

From 2026-05-14 code review:

> ``webui/aggregate.py:aggregate_runs`` only filters by
> ``finalScore is None``.  rate_limit / infra_error / pre_exec_failed
> / executor_incomplete attempts can carry ``finalScore=0.0`` (not
> None), so they get included in the Results-page token / runtime /
> pass-rate averages and corrupt the benchmark numbers with
> executor-never-ran data.

Round 8 / A3 adds a filter through ``lib.status.normalize_final_status``
+ ``TERMINAL_RESULT_STATUSES``: only ``{pass, budget_exhausted, fail,
global_timeout}`` reach Results aggregation.  Non-terminal rows are
still shown on per-task detail and operator dashboards via the slow
path; they just don't bias the benchmark averages.
"""
from __future__ import annotations

import json
from pathlib import Path


def _write_summary(
    runs_root: Path,
    backend: str,
    model_dir: str,
    suite: str,
    task: str,
    *,
    final_status: str,
    final_score: float | None = 0.5,
    model_slug: str | None = None,
):
    task_dir = runs_root / backend / model_dir / suite / task
    task_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "taskId": task,
        "backend": backend,
        "model": model_slug or model_dir,
        "modelSlug": model_slug or model_dir,
        "finalStatus": final_status,
        "finalScore": final_score,
        "rawFinalScore": final_score,
        "passed": final_status == "pass",
        "resolvedAttempt": 1,
    }
    (task_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def test_aggregate_filters_to_terminal_statuses(tmp_path, monkeypatch):
    """Construct 6 summaries: 4 terminal-status types + 1 rate_limit +
    1 infra_error.  Aggregate must surface only the 4 terminal rows."""
    runs = tmp_path / "runs"

    # 4 terminal rows that SHOULD be in aggregate
    _write_summary(runs, "openclaw", "m", "101_a", "task_001", final_status="pass", final_score=0.9)
    _write_summary(runs, "openclaw", "m", "101_a", "task_002", final_status="fail", final_score=0.1)
    _write_summary(runs, "openclaw", "m", "101_a", "task_003", final_status="budget_exhausted", final_score=0.4)
    _write_summary(runs, "openclaw", "m", "101_a", "task_004", final_status="global_timeout", final_score=0.0)

    # 2 non-terminal rows that MUST NOT be in aggregate
    _write_summary(runs, "openclaw", "m", "101_a", "task_005", final_status="rate_limit", final_score=0.0)
    _write_summary(runs, "openclaw", "m", "101_a", "task_006", final_status="infra_error", final_score=0.0)

    # Point aggregate at our test runs dir.  aggregate.RUNS is bound at
    # import time, so we need to both reload the module and patch its
    # cache, OR just patch the module attribute and bypass the cache.
    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    result = aggregate.aggregate_runs(force=True)

    # Find the (openclaw, m) row.
    backends = result.get("backends") or []
    by_model = result.get("models") or []
    # Models view: should have one entry with n=4 (only terminal rows count)
    for entry in by_model:
        if entry.get("model_slug") == "m" or entry.get("key") == "m":
            total = entry.get("total") or {}
            assert total.get("n") == 4, f"expected n=4, got {total.get('n')}: {entry}"
            return
    # Either field name absent — fall back to direct check via internal helper
    # by inspecting the raw rows that aggregate_runs collected. Use scoping
    # via the categories breakdown.
    assert False, f"openclaw/m entry not found in models view: {by_model}"


def test_aggregate_excludes_executor_incomplete_and_missing(tmp_path, monkeypatch):
    """Non-terminal states like executor_incomplete / missing must be
    excluded — these are runs that never reached a real evaluation."""
    runs = tmp_path / "runs"

    _write_summary(runs, "openclaw", "m", "101_a", "task_001", final_status="pass", final_score=1.0)
    _write_summary(runs, "openclaw", "m", "101_a", "task_002", final_status="executor_incomplete", final_score=0.0)
    _write_summary(runs, "openclaw", "m", "101_a", "task_003", final_status="missing", final_score=0.0)

    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    result = aggregate.aggregate_runs(force=True)
    by_model = result.get("models") or []
    for entry in by_model:
        if entry.get("model_slug") == "m" or entry.get("key") == "m":
            assert (entry.get("total") or {}).get("n") == 1
            return
    assert False, f"openclaw/m entry not found: {by_model}"


def test_aggregate_normalizes_legacy_status_strings(tmp_path, monkeypatch):
    """Legacy on-disk values (``continue``, ``stopped``) get normalised by
    ``lib.status.normalize_final_status`` to ``executor_incomplete``,
    which is NOT a terminal status — they must be excluded too."""
    runs = tmp_path / "runs"

    _write_summary(runs, "openclaw", "m", "101_a", "task_001", final_status="pass", final_score=1.0)
    _write_summary(runs, "openclaw", "m", "101_a", "task_002", final_status="continue", final_score=0.3)
    _write_summary(runs, "openclaw", "m", "101_a", "task_003", final_status="stopped", final_score=0.4)

    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    result = aggregate.aggregate_runs(force=True)
    by_model = result.get("models") or []
    for entry in by_model:
        if entry.get("model_slug") == "m" or entry.get("key") == "m":
            assert (entry.get("total") or {}).get("n") == 1
            return
    assert False, f"openclaw/m entry not found: {by_model}"
