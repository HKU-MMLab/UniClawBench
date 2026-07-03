"""Round 10 / P1: ``apply_executor_completion_gate`` is now budget-aware.

When the supervisor claims ``pass`` but the executor never wrote a
completion signal (final assistant message + stop reason + no pending
tool call):

- ``followup_budget_remaining > 0`` → flip to ``continue`` with
  ``recoverable=True``, leaving ``completion_gate_failed=False`` so
  ``continuation_decision`` can route to the user simulator for one
  more turn (the strict pre-fix behavior was to terminate hard).
- ``followup_budget_remaining == 0`` → preserve original strict
  behavior: ``verdict=fail, recoverable=False, completion_gate_failed=True``.

The invariant "supervisor cannot self-declare pass without executor
signal" is preserved either way — we flip ``pass → continue``, not
``pass → pass``.  The original strict-fail test in
``tests/integration/test_executor.py`` still covers the budget=0 case.
"""
from __future__ import annotations

import json

from lib.runner.evaluation import apply_executor_completion_gate


_INCOMPLETE_TRANSCRIPT = json.dumps(
    {
        "type": "message",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Still working on it..."}],
        },
    },
    ensure_ascii=False,
)


# Text known to trigger the completion-marker regex AND agent_exit_code=0
# is what existing test_apply_executor_completion_gate_preserves_supervisor_
# score_for_completed_continue uses for the executor_completed=True path.
_COMPLETED_TRANSCRIPT = json.dumps(
    {
        "type": "message",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "I have finished the request"}],
        },
    },
    ensure_ascii=False,
)


def test_pass_without_signal_with_budget_flips_to_continue() -> None:
    """Budget > 0 → defer judgment to user simulator.  Round 10 / P1
    new behavior."""
    payload = apply_executor_completion_gate(
        {"verdict": "pass", "attempt_state": "complete_and_passed",
         "overall_score": 1.0, "capped_score": 1.0, "recoverable": False},
        _INCOMPLETE_TRANSCRIPT,
        1,
        followup_budget_remaining=2,
    )
    assert payload["verdict"] == "continue"
    assert payload["attempt_state"] == "incomplete"
    assert payload["recoverable"] is True
    assert payload["completion_gate_failed"] is False, (
        "completion_gate_failed must stay False when budget remains so "
        "continuation_decision can route to the user simulator"
    )
    assert payload["completion_gate_deferred"] is True
    # Supervisor's raw verdict still preserved for audit
    assert payload["supervisor_verdict_raw"] == "pass"
    # ``final_completion_score`` should be 0.0 since executor did not complete
    # (the score only counts when both gate passes AND verdict is not infra/rate)
    assert payload["final_completion_score"] == 0.0


def test_pass_without_signal_with_budget_one_still_continues() -> None:
    """Edge case: budget=1 (exactly one followup left) → still continue."""
    payload = apply_executor_completion_gate(
        {"verdict": "pass", "overall_score": 1.0, "capped_score": 1.0},
        _INCOMPLETE_TRANSCRIPT,
        1,
        followup_budget_remaining=1,
    )
    assert payload["verdict"] == "continue"
    assert payload["completion_gate_failed"] is False


def test_pass_without_signal_with_zero_budget_fails_hard() -> None:
    """Budget = 0 → strict pre-fix behavior: fail + recoverable=False."""
    payload = apply_executor_completion_gate(
        {"verdict": "pass", "overall_score": 1.0, "capped_score": 1.0},
        _INCOMPLETE_TRANSCRIPT,
        1,
        followup_budget_remaining=0,
    )
    assert payload["verdict"] == "fail"
    assert payload["recoverable"] is False
    assert payload["completion_gate_failed"] is True
    assert payload["completion_gate_deferred"] is False


def test_pass_without_signal_default_budget_fails_hard() -> None:
    """Default ``followup_budget_remaining=0`` preserves backward
    compatibility for any caller that doesn't pass the kwarg.  The
    only legitimate live caller is ``run_primary_attempt`` (passes
    the real budget), but a stray test or external script using the
    public function without the kwarg should land on the strict
    behavior, not silently weaken the gate."""
    payload = apply_executor_completion_gate(
        {"verdict": "pass", "overall_score": 1.0, "capped_score": 1.0},
        _INCOMPLETE_TRANSCRIPT,
        1,
    )
    assert payload["verdict"] == "fail"
    assert payload["completion_gate_failed"] is True


def test_pass_with_signal_unchanged_by_budget() -> None:
    """When executor DID complete cleanly, the gate doesn't trigger
    regardless of budget — supervisor's pass stays.  Regression
    guard against accidentally weakening the gate the other way."""
    for budget in (0, 1, 99):
        payload = apply_executor_completion_gate(
            {"verdict": "pass", "attempt_state": "complete_and_passed",
             "overall_score": 1.0, "capped_score": 1.0},
            _COMPLETED_TRANSCRIPT,
            0,
            followup_budget_remaining=budget,
        )
        assert payload["verdict"] == "pass", (
            f"completed executor should keep pass at budget={budget}"
        )
        assert payload["completion_gate_failed"] is False
        assert payload["final_completion_score"] == 1.0


def test_non_pass_verdict_unchanged_by_budget() -> None:
    """``verdict != pass`` paths (continue / fail / infra_error /
    rate_limit) are unaffected by budget — only the ``pass without
    signal`` branch was retargeted."""
    for verdict in ("continue", "fail", "infra_error", "rate_limit"):
        payload = apply_executor_completion_gate(
            {"verdict": verdict, "overall_score": 0.5, "capped_score": 0.5},
            _INCOMPLETE_TRANSCRIPT,
            0,
            followup_budget_remaining=5,
        )
        assert payload["verdict"] == verdict, f"verdict={verdict} mutated"
        assert payload["completion_gate_failed"] is False, (
            f"completion_gate should not fire on verdict={verdict}"
        )
