"""Cover the synthetic-status fallback in refresh_summary.

When run_eval is killed before it writes a per-attempt ``summary.json``
(e.g. global timeout / OOM / SIGKILL), ``refresh_summary`` derives a
status from the artefacts that DID land on disk: ``score.json`` and
``meta.json``.  These tests pin the classifier against the matrix of
inputs we've seen in production so a regression here would surface
immediately.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestra.refresh_summary import _derive_status_from_artifacts


def _write_attempt(p_dir: Path, *, score: dict | None = None, meta: dict | None = None) -> None:
    p_dir.mkdir(parents=True, exist_ok=True)
    if score is not None:
        (p_dir / "score.json").write_text(json.dumps(score), encoding="utf-8")
    if meta is not None:
        (p_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def test_no_artefacts_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-abc123"
    p.mkdir()
    assert _derive_status_from_artifacts(p) is None


def test_pass_from_passed_flag(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-passed"
    _write_attempt(p, score={"passed": True, "overall_score": 1.0}, meta={})
    out = _derive_status_from_artifacts(p)
    assert out is not None
    assert out["finalStatus"] == "pass"
    assert out["passed"] is True


def test_pass_from_verdict_pass(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-verdict"
    _write_attempt(p, score={"verdict": "pass", "overall_score": 0.95}, meta={})
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "pass"


def test_infra_error_takes_priority(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-infra"
    _write_attempt(
        p,
        score={"passed": True, "overall_score": 1.0},
        meta={"infraError": {"type": "container_boot"}, "agentExitCode": 0},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None
    assert out["finalStatus"] == "infra_error"
    assert out["passed"] is False


def test_rate_limit_takes_priority_over_pass(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-rate"
    _write_attempt(
        p,
        score={"verdict": "pass"},
        meta={"rateLimit": {"provider": "provider_primary"}},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "rate_limit"


def test_pre_exec_failed_detected(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-preexec"
    _write_attempt(p, score={}, meta={"preExecFailed": True})
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "pre_exec_failed"


def test_pre_exec_failed_via_bootstrap_error_type(tmp_path: Path) -> None:
    """Round 9 / A6: bootstrap_error.type='pre_exec_failed' (set by
    build_bootstrap_infra_summary for host-side pre_exec script
    failures) must yield pre_exec_failed in the synth path even when
    meta.preExecFailed is absent."""
    p = tmp_path / "p1-host-bootstrap-preexec"
    _write_attempt(
        p,
        score={"verdict": "infra_error", "infra_error": True},
        meta={
            "bootstrapError": {"type": "pre_exec_failed", "message": "boom"},
            "infraError": {"type": "pre_exec_failed", "message": "boom"},
        },
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "pre_exec_failed"


def test_pre_exec_failed_via_score_infra_error_type(tmp_path: Path) -> None:
    """Round 9 / A6: when ``score.infra_error_type='pre_exec_failed'``
    (set by structured_runtime_error_score), Path B must reflect that
    specialization instead of collapsing to infra_error."""
    p = tmp_path / "p1-host-score-preexec"
    _write_attempt(
        p,
        score={
            "verdict": "infra_error",
            "infra_error": True,
            "infra_error_type": "pre_exec_failed",
        },
        meta={"infraError": {"type": "pre_exec_failed"}},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "pre_exec_failed"


def test_generic_infra_error_does_not_become_pre_exec(tmp_path: Path) -> None:
    """Negative: a real infra_error WITHOUT any pre_exec_failed signal
    must stay ``infra_error`` (not promoted to pre_exec_failed)."""
    p = tmp_path / "p1-host-real-infra"
    _write_attempt(
        p,
        score={"verdict": "infra_error", "infra_error": True},
        meta={"infraError": {"type": "container_died"}},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "infra_error"


def test_global_timeout_from_exit_124(tmp_path: Path) -> None:
    """agent_exit=124 (SIGTERM by timeout) AFTER at least one clean executor
    turn → global_timeout.  Round-5 Phase 4 narrowed this: when executor
    NEVER cleanly completed, agent_exit=124 maps to executor_incomplete
    instead (see test_executor_incomplete_from_exit_124_first_turn below)."""
    p = tmp_path / "p1-host-timeout"
    _write_attempt(
        p,
        score={"verdict": "continue", "overall_score": 0.4},
        meta={"agentExitCode": 124, "everExecutorCompleted": True},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "global_timeout"


def test_global_timeout_from_completion_reason(tmp_path: Path) -> None:
    """completionReason=timeout AFTER executor cleanly completed → global_timeout."""
    p = tmp_path / "p1-host-timeout2"
    _write_attempt(
        p,
        score={"verdict": "continue"},
        meta={"executorCompletionReason": "timeout", "everExecutorCompleted": True},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "global_timeout"


def test_executor_incomplete_from_exit_124_first_turn(tmp_path: Path) -> None:
    """Round-5 Phase 4: agent_exit=124 with everExecutorCompleted=False is
    the prototypical executor_incomplete scenario — executor was killed by
    per-turn timeout on its first turn, never wrote a clean completion.
    'Stuck on a huge file at deadline' semantics.  Previously path B
    classified this as global_timeout, conflating per-turn first-turn kills
    with cumulative wall-clock budget timeouts."""
    p = tmp_path / "p1-host-first-turn-stuck"
    _write_attempt(
        p,
        score={"verdict": "continue", "overall_score": 0.0},
        meta={"agentExitCode": 124, "everExecutorCompleted": False},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "executor_incomplete"


def test_executor_incomplete_from_nonzero_exit_without_verdict(tmp_path: Path) -> None:
    """When the supervisor didn't emit a verdict at all (no score.json
    or an empty one) and the runner exited non-zero before completing,
    the synth path should classify as executor_incomplete — distinct
    from ``fail``, which is reserved for a real supervisor fail
    verdict."""
    p = tmp_path / "p1-host-ei"
    _write_attempt(
        p,
        score={},  # no verdict — supervisor never weighed in
        meta={"agentExitCode": 1, "everExecutorCompleted": False, "executorCompletionReason": "nonzero-exit"},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "executor_incomplete"


def test_fail_verdict_trumps_nonzero_exit(tmp_path: Path) -> None:
    """If the supervisor scored the attempt as ``fail`` we trust that
    over the executor's non-zero exit — the attempt completed enough
    for the grader to read its output."""
    p = tmp_path / "p1-host-fail-after-exit"
    _write_attempt(
        p,
        score={"verdict": "fail", "overall_score": 0.0},
        meta={"agentExitCode": 1, "everExecutorCompleted": False, "executorCompletionReason": "nonzero-exit"},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "fail"


def test_continue_verdict_with_no_completion_treated_as_incomplete(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-continue"
    _write_attempt(p, score={"verdict": "continue", "overall_score": 0.5}, meta={})
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "executor_incomplete"


def test_fail_when_executor_completed_with_fail_verdict(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-fail"
    _write_attempt(
        p,
        score={"verdict": "fail", "overall_score": 0.0},
        meta={"agentExitCode": 0, "everExecutorCompleted": True},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None and out["finalStatus"] == "fail"


def test_synthetic_marker_present(tmp_path: Path) -> None:
    """Refresh_summary uses the ``_synthetic`` marker to know it should
    pull identifiers from meta.json instead of summary.json; missing
    the flag would silently degrade summary metadata."""
    p = tmp_path / "p1-host-marker"
    _write_attempt(p, score={"verdict": "fail"}, meta={"agentExitCode": 1})
    out = _derive_status_from_artifacts(p)
    assert out is not None
    assert out.get("_synthetic") is True
    assert "_meta" in out


def test_score_field_population(tmp_path: Path) -> None:
    p = tmp_path / "p1-host-score"
    _write_attempt(
        p,
        score={"overall_score": 0.72, "capped_score": 0.5, "verdict": "fail"},
        meta={"agentExitCode": 0, "everExecutorCompleted": True},
    )
    out = _derive_status_from_artifacts(p)
    assert out is not None
    assert out["rawFinalScore"] == pytest.approx(0.72)
    assert out["finalScore"] == pytest.approx(0.5)
    # score is "best available" fallback for the rolled-up view
    assert out["score"] in {0.72, 0.5}
