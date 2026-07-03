"""Unit tests for ``lib.runner.continuation_decision``.

continuation_decision is the pure function that decides whether a run
continues into another executor turn or stops. Its branches encode the
benchmark's architecture-critical invariants:

  - a pass verdict always stops the run
  - an infra error always stops
  - an unrecoverable fail stops
  - if the supervisor wants to continue but the follow-up budget is
    exhausted, we stop (``followup-limit-reached``)
  - if the supervisor wants to continue but the rewriter produced no
    safe user feedback, we stop (``empty-safe-feedback``)
  - if the executor never emitted a completion signal, we stop with
    ``completion_gate_failed`` regardless of score

Covering these in pure unit tests gives the refactor a cheap safety net
without spinning up containers.
"""
from __future__ import annotations

from pathlib import Path

from lib.runner import continuation_decision, build_runtime_task_spec


ROOT = Path(__file__).resolve().parents[2]


def _task():
    return build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")


def _base_score(**overrides):
    """Minimal supervisor-score-ish payload that continuation_decision reads."""
    score = {
        "verdict": "continue",
        "attempt_state": "incomplete",
        "recoverable": True,
        "safe_user_feedback": "please keep checking the page",
        "executor_completed": True,
        "completion_gate_failed": False,
    }
    score.update(overrides)
    return score


def _transcript():
    """A transcript with an assistant completion signal — shared across tests."""
    return (
        '{"type":"message","message":{"role":"assistant",'
        '"content":[{"type":"text","text":"I have finished the request"}]}}'
    )


def test_pass_verdict_stops_with_supervisor_pass_reason() -> None:
    task = _task()
    decision = continuation_decision(task, _base_score(verdict="pass"), _transcript(), 0)
    assert decision["action"] == "stop"
    assert decision["reason"] == "supervisor-pass"


def test_infra_error_stops() -> None:
    task = _task()
    decision = continuation_decision(
        task,
        _base_score(verdict="infra_error", infra_error=True, infra_error_type="provider_down"),
        _transcript(),
        0,
    )
    assert decision["action"] == "stop"
    assert decision["reason"] == "provider_down"


def test_rate_limit_stops() -> None:
    """rate_limit is a peer of infra_error: the upstream provider returned
    HTTP 429 before the model could reason. Must stop, and the reason
    should surface the rate_limit_type so operators can see it was a
    quota/throttle problem, not a runtime bug."""
    task = _task()
    decision = continuation_decision(
        task,
        _base_score(
            verdict="rate_limit",
            rate_limit=True,
            rate_limit_type="provider_rate_limited",
        ),
        _transcript(),
        0,
    )
    assert decision["action"] == "stop"
    assert decision["reason"] == "provider_rate_limited"


def test_rate_limit_without_verdict_field_still_stops() -> None:
    """Even if the score happens to carry only the ``rate_limit=True``
    flag (no verdict override — e.g. supervisor payload derived from a
    transcript hit that slipped past the verdict normalizer), the
    decision should still stop. This mirrors the existing
    ``infra_error`` fallback in continuation_decision."""
    task = _task()
    decision = continuation_decision(
        task,
        _base_score(
            verdict="continue",  # supervisor thought we could continue
            rate_limit=True,      # but the transcript says otherwise
            rate_limit_type="provider_rate_limited",
            safe_user_feedback="please keep checking",
        ),
        _transcript(),
        0,
    )
    assert decision["action"] == "stop"
    assert decision["reason"] == "provider_rate_limited"


def test_unrecoverable_fail_stops() -> None:
    task = _task()
    decision = continuation_decision(
        task,
        _base_score(verdict="fail", recoverable=False),
        _transcript(),
        0,
    )
    assert decision["action"] == "stop"


def test_continue_with_feedback_triggers_followup() -> None:
    task = _task()
    # continuation_index=0 → 0 follow-ups used → plenty of budget remaining
    decision = continuation_decision(task, _base_score(), _transcript(), 0)
    assert decision["action"] == "continue"
    # Reason should reflect the supervisor asking for another turn
    assert "followup" in decision["reason"]


def test_continue_without_feedback_stops_with_empty_safe_feedback_reason() -> None:
    """If the rewriter collapses to an empty safe_user_feedback, the runner
    must NOT forward an empty continuation to the executor."""
    task = _task()
    decision = continuation_decision(task, _base_score(safe_user_feedback="   "), _transcript(), 0)
    assert decision["action"] == "stop"
    assert decision["reason"] == "empty-safe-feedback"


def test_continue_with_budget_exhausted_stops() -> None:
    task = _task()
    # Push continuation_index beyond max_user_followups from the task YAML
    exhausted_index = int(task.codex.max_user_followups) + 1
    decision = continuation_decision(task, _base_score(), _transcript(), exhausted_index)
    assert decision["action"] == "stop"
    assert decision["reason"] == "followup-limit-reached"


def test_completion_gate_failure_short_circuits_all_other_decisions() -> None:
    """Even a supervisor pass must lose to a failed completion gate, because
    the executor never actually signaled completion and the pass claim is
    therefore unsupported."""
    task = _task()
    decision = continuation_decision(
        task,
        _base_score(
            verdict="pass",
            completion_gate_failed=True,
            completion_gate_reason="executor-did-not-finish",
        ),
        _transcript(),
        0,
    )
    assert decision["action"] == "stop"
    assert decision["reason"] == "executor-did-not-finish"
