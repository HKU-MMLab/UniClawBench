"""Round-6 Phase 3 regression: batch_run / batch_eval status counts.

Pre-Round-6, ``lib/runner/orchestration.py:batch_run`` and
``scripts/batch_eval.py`` both computed ``fail`` as
``finalStatus == "fail" or passed is False``.  That silently absorbed
every non-pass status (infra_error, executor_incomplete, missing) into
the fail count, badly distorting any "fail rate" derived from the
summary.

Phase 3 swaps that to ``lib.status.build_status_counts`` — strict
equality against canonical names, plus a full ``statusCounts``
breakdown under FINAL_STATUS_ORDER.  These tests pin both properties.
"""
from __future__ import annotations

from lib.status import FINAL_STATUS_ORDER, build_status_counts


def test_build_status_counts_complete_breakdown():
    """statusCounts must include every FINAL_STATUS_ORDER key,
    zero-padded for any not present in the input batch."""
    results = [
        {"finalStatus": "pass", "passed": True},
        {"finalStatus": "fail", "passed": False},
    ]
    counts = build_status_counts(results)
    for key in FINAL_STATUS_ORDER:
        assert key in counts, f"missing FINAL_STATUS_ORDER key: {key}"
    assert counts["pass"] == 1
    assert counts["fail"] == 1
    assert counts["budget_exhausted"] == 0


def test_fail_count_excludes_non_fail():
    """Regression: the old code counted infra_error / executor_incomplete /
    missing into ``fail`` via ``passed is False``.  Round-6's strict
    equality must NOT count any of those."""
    results = [
        {"finalStatus": "pass", "passed": True},
        {"finalStatus": "fail", "passed": False},
        {"finalStatus": "infra_error", "passed": False},
        {"finalStatus": "executor_incomplete", "passed": False},
        {"finalStatus": "missing", "passed": False},
        {"finalStatus": "rate_limit", "passed": False},
    ]
    counts = build_status_counts(results)
    assert counts["fail"] == 1, (
        f"fail must only count finalStatus==fail, got {counts['fail']}"
    )
    assert counts["infra_error"] == 1
    assert counts["executor_incomplete"] == 1
    assert counts["missing"] == 1
    assert counts["rate_limit"] == 1
    # And the sum of buckets matches input length (no result lost).
    assert sum(counts.values()) == len(results)


def test_infra_error_count_excludes_executor_incomplete():
    """Round-5/6 design distinction: executor_incomplete is an executor-side
    state (process crashed), NOT an infra failure.  The infra_error
    count must not absorb it."""
    results = [
        {"finalStatus": "infra_error"},
        {"finalStatus": "executor_incomplete"},
        {"finalStatus": "executor_incomplete"},
        {"finalStatus": "pre_exec_failed"},
    ]
    counts = build_status_counts(results)
    assert counts["infra_error"] == 1
    assert counts["pre_exec_failed"] == 1
    assert counts["executor_incomplete"] == 2


def test_normalizes_ops_layer_status_strings():
    """build_status_counts goes through normalize_final_status first, so
    any leaked ops-layer strings (FAIL_rc=1, no_summary, broken_json)
    end up in the right bucket instead of silently dropped."""
    results = [
        {"finalStatus": "FAIL_rc=1"},     # → executor_incomplete
        {"finalStatus": "no_summary"},    # → missing
        {"finalStatus": "broken_json"},   # → missing
        {"finalStatus": "stopped"},       # → executor_incomplete (legacy)
        {"finalStatus": "continue"},      # → executor_incomplete (legacy verdict)
    ]
    counts = build_status_counts(results)
    assert counts["executor_incomplete"] == 3, counts
    assert counts["missing"] == 2, counts
    # Total stays consistent with input length.
    assert sum(counts.values()) == len(results)
