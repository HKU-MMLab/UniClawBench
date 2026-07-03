"""Round-5 Phase 4 — pin the new ``resolve_attempt_outcome`` priority order.

Key principle: when the supervisor renders an authoritative terminal
verdict (``attempt_state`` ∈ {``terminal_failure``, ``complete_and_passed``}),
it MUST win over the "executor process didn't sign off" tally. Path A
used to do the opposite, which made any task where the executor was
SIGKILL'd at the wall-clock budget look like ``executor_incomplete``
even though supervisor had judged it ``terminal_failure``.

Bonus pin: a parallel cross-check that ``refresh_summary._derive_status_from_artifacts``
(Path B, the synth fallback used when per-attempt summary.json is
absent) returns the same finalStatus for the same input as Path A.
"""
from __future__ import annotations

import pytest

from lib.runner.orchestration import resolve_attempt_outcome
from lib.task import CodexSpec, TaskSpec
from pathlib import Path


def _stub_task(*, success_threshold: float = 1.0) -> TaskSpec:
    """A TaskSpec with only the fields resolve_attempt_outcome consults."""
    return TaskSpec(
        task_id="t",
        category="cat",
        agent_sys="openclaw",
        agent_id="main",
        model="m",
        image_model="m",
        timeout_seconds=1200,
        max_total_seconds=1800,
        success_threshold=success_threshold,
        task="t",
        task_snapshot="",
        references=[],
        sources=[],
        skills=[],
        services=[],
        pre_exec=[],
        privacy=[],
        file_path=Path("/tmp/fake.yaml"),
        injection_root=Path("/tmp/fake"),
        codex=CodexSpec(),
        pre_exec_parallel_safe=False,
    )


# ── pass / fail / infra / rate_limit (don't regress the easy cases) ────


def test_pass_via_verdict():
    task = _stub_task()
    score = {"verdict": "pass", "attempt_state": "complete_and_passed",
             "executor_completed_ever": True, "best_supervisor_score": 1.0}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "pass"
    assert out["passed"] is True


def test_pass_via_attempt_state_complete_and_passed():
    """Even without verdict=pass, attempt_state=complete_and_passed wins."""
    task = _stub_task()
    score = {"verdict": "continue", "attempt_state": "complete_and_passed",
             "executor_completed_ever": True, "best_supervisor_score": 0.95}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "pass"


def test_rate_limit_via_verdict():
    task = _stub_task()
    score = {"verdict": "rate_limit", "rate_limit": True}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "rate_limit"
    assert out["final_score"] == 0.0


def test_infra_error_via_verdict():
    task = _stub_task()
    score = {"verdict": "infra_error", "infra_error": True}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "infra_error"


def test_pre_exec_failed_specialised():
    task = _stub_task()
    score = {"verdict": "infra_error", "infra_error": True,
             "infra_error_type": "pre_exec_failed"}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "pre_exec_failed"


# ── the Round-5 fix targets ────────────────────────────────────────────


def test_supervisor_terminal_failure_beats_executor_incomplete():
    """Regression: when supervisor explicitly says terminal_failure AFTER
    seeing evidence, that MUST win over executor-process-not-completed.

    Production samples that surfaced this:
      task_038, task_034, task_102_33: executor SIGKILL'd at budget,
      supervisor saw 49-237 tool calls + result files, said
      verdict=fail attempt_state=terminal_failure. OLD path A:
      → executor_incomplete (wrong). NEW path A: → fail.
    """
    task = _stub_task()
    score = {
        "verdict": "fail",
        "attempt_state": "terminal_failure",
        "executor_completed": False,
        "executor_completed_ever": False,
        "executor_exit_code": 1,           # process crash
        "best_supervisor_score": 0.0,
    }
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "fail"  # NOT executor_incomplete


def test_completion_gate_failed_maps_to_fail():
    """Supervisor wanted pass but executor didn't sign off → supervisor-override fail."""
    task = _stub_task()
    score = {
        "verdict": "pass",
        "completion_gate_failed": True,
        "executor_completed_ever": True,
        "best_supervisor_score": 0.8,
    }
    out = resolve_attempt_outcome(task, score)
    # NB: attempt_state=complete_and_passed is NOT set here, so we hit the
    # completion_gate_failed branch.  If verdict=pass + attempt_state were both
    # set, pass would win (legitimate).
    assert out["final_status"] == "fail"


def test_executor_crashed_maps_to_executor_incomplete():
    """Process exited non-zero, supervisor didn't reach a terminal verdict
    → executor_incomplete (NOT infra_error). The executor failed to do
    its job; infra_error is reserved for actual infra/host failures
    (supervisor crash, container failed to start, etc., flagged via
    verdict=infra_error or current.infra_error)."""
    task = _stub_task()
    score = {
        "verdict": "continue",       # supervisor wanted more
        "attempt_state": "in_progress",  # not terminal
        "executor_completed_ever": False,
        "executor_exit_code": 1,     # crashed
    }
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "executor_incomplete"


def test_executor_stuck_no_completion_no_crash_still_maps_to_executor_incomplete():
    """The "stuck on a huge file at deadline" case (user's prototypical
    intent for executor_incomplete): supervisor verdict=continue, no
    exit code, executor simply didn't cleanly complete."""
    task = _stub_task()
    score = {
        "verdict": "continue",
        "executor_completed": False,
        "executor_completed_ever": False,
        "executor_exit_code": None,
        "followup_budget_exhausted": False,
    }
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "executor_incomplete"


def test_global_timeout_terminalizes_even_when_executor_never_completed():
    """Round-7 (reversed from Round-5, commit 98211b35): an explicit
    CUMULATIVE global-timeout terminal classifies as ``global_timeout`` EVEN
    WHEN the executor never cleanly completed a turn
    (``executor_completed_ever=False``).

    ``terminal_reason="global-timeout-executor"`` is set only when
    ``executor_elapsed_seconds >= max_total_seconds`` — i.e. the run consumed
    its full executor budget.  That IS a terminal budget exhaustion, so it
    must leave the queue as a bounded-retry ``global_timeout`` (Round-19
    re-dispatches it via the lowest-priority "timeout" tier) rather than the
    non-terminal ``executor_incomplete`` catch-all, which the dispatcher would
    re-dispatch forever — the exact churn the Round-7 terminalization fixed.

    Contrast: a PER-TURN deadline kill on the first turn (agent_exit_code=124,
    ever=False, no cumulative ``terminal_reason``) stays ``executor_incomplete``
    (see ``test_executor_crashed_maps_to_executor_incomplete``).  The classifier
    layer pins this same case in
    ``tests/unit/test_status_module.py::test_classify_timeout_precedes_incomplete_round7``.
    """
    task = _stub_task()
    score = {
        "verdict": "continue",
        "executor_completed_ever": False,   # never cleanly completed a turn
        "executor_exit_code": 1,
        "best_supervisor_score": 0.55,
    }
    out = resolve_attempt_outcome(task, score, terminal_reason="global-timeout-executor")
    # global_timeout wins: the cumulative executor budget was exhausted, so the
    # attempt is terminal (bounded retry) — NOT a non-terminal executor_incomplete.
    assert out["final_status"] == "global_timeout"


def test_global_timeout_wins_when_executor_did_complete():
    """If executor DID complete at least one turn (executor_completed_ever=True),
    a global timeout terminates the run as global_timeout."""
    task = _stub_task()
    score = {
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.55,
    }
    out = resolve_attempt_outcome(task, score, terminal_reason="global-timeout-executor")
    assert out["final_status"] == "global_timeout"


def test_budget_exhausted_when_executor_completed():
    """budget_exhausted applies when executor cleanly completed cycles
    AND the followup budget limit was reached."""
    task = _stub_task()
    score = {
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.7,
    }
    out = resolve_attempt_outcome(task, score, terminal_reason="followup-limit-reached")
    assert out["final_status"] == "budget_exhausted"


def test_high_score_budget_exhausted_flips_to_pass():
    """Score-based promotion: budget_exhausted + score >= threshold → pass.

    Rationale: the agent met the success bar; it just used the full
    max_user_followups budget. That's a successful completion, not a
    failure-flavour terminal status.
    """
    task = _stub_task(success_threshold=0.5)
    score = {
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.9,    # well above 0.5 threshold
    }
    out = resolve_attempt_outcome(task, score, terminal_reason="followup-limit-reached")
    # The score-based promotion at the bottom of resolve_attempt_outcome
    # flips budget_exhausted → pass when score >= threshold.
    assert out["final_status"] == "pass"
    assert out["passed"] is True


def test_low_score_budget_exhausted_stays_budget_exhausted():
    """Conversely, budget_exhausted + low score stays budget_exhausted."""
    task = _stub_task(success_threshold=0.9)
    score = {
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.55,   # below 0.9 threshold
    }
    out = resolve_attempt_outcome(task, score, terminal_reason="followup-limit-reached")
    assert out["final_status"] == "budget_exhausted"
    assert out["passed"] is False


def test_fail_status_does_not_flip_to_pass_via_score():
    """Even with score >= threshold (synthetic case), an explicit fail
    terminal verdict stays fail — fail is NOT promotable."""
    task = _stub_task(success_threshold=0.5)
    score = {
        "verdict": "fail",
        "attempt_state": "terminal_failure",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.95,
    }
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "fail"
    assert out["passed"] is False


def test_executor_incomplete_high_score_stays_executor_incomplete():
    """``executor_incomplete`` is on the score-promotion blocklist.

    Even with a high supervisor score, an executor that never cleanly
    completed must stay ``executor_incomplete`` — the supervision score
    can't be trusted to cover a run where the executor never finished
    producing evidence.
    """
    task = _stub_task(success_threshold=0.5)
    score = {
        "verdict": "continue",
        "executor_completed_ever": False,
        "executor_exit_code": 1,
        "best_supervisor_score": 0.95,
    }
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "executor_incomplete"
    assert out["passed"] is False


def test_global_timeout_high_score_promotes_to_pass():
    """Score-based promotion applies to ``global_timeout`` too: if the
    executor did cleanly complete at least one cycle, and the supervisor
    score is above the threshold, a final wall-clock timeout should be
    classified as ``pass`` rather than ``global_timeout``."""
    task = _stub_task(success_threshold=0.5)
    score = {
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.92,
    }
    out = resolve_attempt_outcome(task, score, terminal_reason="global-timeout-executor")
    assert out["final_status"] == "pass"
    assert out["passed"] is True


def test_empty_score_classifies_as_executor_incomplete():
    """Empty score (no verdict, no infra, no executor completion) → the
    new design treats this as executor_incomplete because the executor
    failed to produce any signal at all.  In the old code this fell
    through to ``stopped`` which was less informative."""
    task = _stub_task()
    score = {}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "executor_incomplete"


def test_only_executor_completed_no_verdict_falls_through_to_executor_incomplete():
    """Round-6: when executor cleanly completed but supervisor produced no
    verdict AND there's no terminal_reason, fall through to
    ``executor_incomplete`` (the unified rerun-pool bucket).  Prior to
    Round 6 this fell through to the bespoke ``stopped`` label, which
    no downstream code knew how to handle uniformly."""
    task = _stub_task()
    score = {"executor_completed_ever": True, "executor_completed": True}
    out = resolve_attempt_outcome(task, score)
    assert out["final_status"] == "executor_incomplete"


# ── cross-path consistency: Path A and Path B agree ─────────────────────


def test_path_a_and_path_b_agree_on_terminal_failure(tmp_path):
    """Same input → same finalStatus from Path A and Path B."""
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts
    import json

    # Path B inputs: score.json + meta.json
    p_dir = tmp_path / "p1-test"
    p_dir.mkdir()
    (p_dir / "score.json").write_text(json.dumps({
        "verdict": "fail",
        "attempt_state": "terminal_failure",
        "executor_completed": False,
        "executor_completed_ever": False,
        "executor_exit_code": 1,
        "capped_score": 0.0,
    }))
    (p_dir / "meta.json").write_text(json.dumps({
        "everExecutorCompleted": False,
        "agentExitCode": 1,
        "executorCompletionReason": "nonzero-exit",
    }))

    # Path B
    b_out = _derive_status_from_artifacts(p_dir)
    assert b_out is not None
    assert b_out["finalStatus"] == "fail", b_out

    # Path A on the same logical state
    task = _stub_task()
    a_score = {
        "verdict": "fail",
        "attempt_state": "terminal_failure",
        "executor_completed": False,
        "executor_completed_ever": False,
        "executor_exit_code": 1,
        "best_supervisor_score": 0.0,
    }
    a_out = resolve_attempt_outcome(task, a_score)
    assert a_out["final_status"] == "fail"

    # Cross-path consistency
    assert b_out["finalStatus"] == a_out["final_status"]


def test_path_a_and_path_b_agree_on_executor_crash_to_executor_incomplete(tmp_path):
    """Executor process crashed, supervisor in_progress → both paths say executor_incomplete."""
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts
    import json

    p_dir = tmp_path / "p1-test"
    p_dir.mkdir()
    (p_dir / "score.json").write_text(json.dumps({
        "verdict": "continue",
        "attempt_state": "in_progress",
        "executor_completed_ever": False,
        "executor_exit_code": 1,
    }))
    (p_dir / "meta.json").write_text(json.dumps({
        "everExecutorCompleted": False,
        "agentExitCode": 1,
        "executorCompletionReason": "nonzero-exit",
    }))

    b_out = _derive_status_from_artifacts(p_dir)
    assert b_out["finalStatus"] == "executor_incomplete"

    task = _stub_task()
    a_score = {
        "verdict": "continue",
        "attempt_state": "in_progress",
        "executor_completed_ever": False,
        "executor_exit_code": 1,
    }
    a_out = resolve_attempt_outcome(task, a_score)
    assert a_out["final_status"] == "executor_incomplete"


# ── Phase 2: Path B applies the SAME score-based pass-promotion as Path A ──


def test_path_a_and_path_b_agree_on_budget_exhausted_promoting_to_pass(tmp_path):
    """Score promotion must agree across paths.

    Setup: high-score attempt cut off by max_user_followups budget. Path A
    flips ``budget_exhausted`` -> ``pass`` via ``apply_score_based_promotion``.
    Path B reads ``success_threshold`` from ``score.json`` and applies the
    same gate.
    """
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts
    import json

    p_dir = tmp_path / "p1-test"
    p_dir.mkdir()
    # score.json now persists success_threshold (Phase 2). Use a value such
    # that overall_score >= threshold so Path B can promote.
    (p_dir / "score.json").write_text(json.dumps({
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "executor_exit_code": 0,
        "followup_budget_exhausted": True,
        "overall_score": 0.92,
        "best_supervisor_score": 0.92,
        "capped_score": 0.92,
        "success_threshold": 0.5,
    }))
    (p_dir / "meta.json").write_text(json.dumps({
        "everExecutorCompleted": True,
        "agentExitCode": 0,
        "executorCompletionReason": "completed",
    }))

    b_out = _derive_status_from_artifacts(p_dir)
    assert b_out is not None
    assert b_out["finalStatus"] == "pass", b_out
    assert b_out.get("_scorePromotionSkipped") in (None, ""), b_out

    task = _stub_task(success_threshold=0.5)
    a_score = {
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "best_supervisor_score": 0.92,
        "followup_budget_exhausted": True,
    }
    a_out = resolve_attempt_outcome(task, a_score, terminal_reason="followup-limit-reached")
    assert a_out["final_status"] == "pass"

    assert b_out["finalStatus"] == a_out["final_status"]


def test_path_b_without_success_threshold_skips_promotion(tmp_path):
    """Legacy ``score.json`` without ``success_threshold`` must skip promotion.

    Old artifacts predate Phase 2's schema extension. Path B must not crash
    and must not invent a threshold; it falls back to the classifier-only
    outcome and tags the record so summary readers can distinguish.
    """
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts
    import json

    p_dir = tmp_path / "p1-legacy"
    p_dir.mkdir()
    # NOTE: no success_threshold key in this legacy score.json.
    (p_dir / "score.json").write_text(json.dumps({
        "verdict": "continue",
        "attempt_state": "complete_but_failed",
        "executor_completed_ever": True,
        "executor_exit_code": 0,
        "followup_budget_exhausted": True,
        "overall_score": 0.92,
        "best_supervisor_score": 0.92,
        "capped_score": 0.92,
    }))
    (p_dir / "meta.json").write_text(json.dumps({
        "everExecutorCompleted": True,
        "agentExitCode": 0,
        "executorCompletionReason": "completed",
    }))

    b_out = _derive_status_from_artifacts(p_dir)
    assert b_out is not None
    # Without the threshold, Path B keeps the classifier outcome.
    assert b_out["finalStatus"] == "budget_exhausted"
    assert b_out.get("_scorePromotionSkipped") == "missing_success_threshold"
