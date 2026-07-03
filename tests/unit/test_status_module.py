"""Round-6 Phase 1 — pin the new lib/status.py single source of truth.

Covers:
  - FINAL_STATUS_ORDER ordering + rank
  - normalize_final_status: canonical, ops-layer, legacy, unknown
  - normalize_supervisor_verdict: passthrough + legacy translation
  - classify_attempt_outcome: all 8 priority branches
  - build_status_counts: complete-keys contract

These tests run as pure unit tests (no IO, no subprocess).
"""
from __future__ import annotations

import pytest

from lib.status import (
    ALL_FINAL_STATUSES,
    FINAL_STATUS_ORDER,
    INCOMPLETE_STATUSES,
    INFRA_STATUSES,
    SUPERVISOR_ATTEMPT_STATES,
    SUPERVISOR_VERDICT_STATES,
    TERMINAL_RESULT_STATUSES,
    apply_score_based_promotion,
    build_status_counts,
    classify_attempt_outcome,
    normalize_final_status,
    normalize_supervisor_attempt_state,
    normalize_supervisor_verdict,
    status_rank,
)


# ── ordering contracts ────────────────────────────────────────────────


def test_final_status_order_has_ten_entries():
    """If a status is ever added/removed, force a deliberate update."""
    assert len(FINAL_STATUS_ORDER) == 10


def test_final_status_order_first_is_pass_last_is_missing():
    assert FINAL_STATUS_ORDER[0] == "pass"
    assert FINAL_STATUS_ORDER[-1] == "missing"


def test_status_rank_pass_beats_missing():
    assert status_rank("pass") > status_rank("missing")


def test_status_rank_canonical_descends_in_order():
    """Sorting by rank descending should reproduce FINAL_STATUS_ORDER."""
    shuffled = list(reversed(FINAL_STATUS_ORDER))
    resorted = sorted(shuffled, key=status_rank, reverse=True)
    assert resorted == list(FINAL_STATUS_ORDER)


def test_status_rank_unknown_returns_zero():
    """Unknown statuses get the worst rank (0) so a typo / legacy value
    never accidentally beats a real one in a max() reduction."""
    assert status_rank("nonsense") == 0
    assert status_rank("") == 0
    assert status_rank(None) == 0


# ── subset categorization ─────────────────────────────────────────────


def test_terminal_result_statuses_excludes_executor_incomplete():
    """Regression: executor_incomplete is NOT in the dispatcher's "done"
    set; the dispatcher should re-run it.  This was the Round-5 design."""
    assert "executor_incomplete" not in TERMINAL_RESULT_STATUSES


def test_terminal_result_statuses_excludes_infra():
    assert "infra_error" not in TERMINAL_RESULT_STATUSES
    assert "rate_limit" not in TERMINAL_RESULT_STATUSES
    assert "pre_exec_failed" not in TERMINAL_RESULT_STATUSES


def test_subsets_cover_all_final_statuses():
    """Every FINAL_STATUS_ORDER entry must fall into at least one of:
    terminal_result / infra / incomplete.  This makes "is this attempt
    worth re-running?" a single boolean check."""
    covered = TERMINAL_RESULT_STATUSES | INFRA_STATUSES | INCOMPLETE_STATUSES
    missing = ALL_FINAL_STATUSES - covered
    assert missing == set(), f"uncovered final statuses: {missing}"


def test_supervisor_verdict_states_is_narrowed():
    """Round 6 narrows the supervisor's verdict to task-semantic states
    only: infra_error / rate_limit must NOT be in the new set."""
    assert SUPERVISOR_VERDICT_STATES == frozenset({"pass", "continue", "fail"})


def test_supervisor_attempt_states_is_narrowed():
    assert "infra_error" not in SUPERVISOR_ATTEMPT_STATES
    assert "rate_limit" not in SUPERVISOR_ATTEMPT_STATES


# ── normalize_final_status ────────────────────────────────────────────


@pytest.mark.parametrize("canonical", list(FINAL_STATUS_ORDER))
def test_normalize_final_status_canonical_passthrough(canonical):
    """Canonical values must round-trip unchanged."""
    assert normalize_final_status(canonical) == canonical
    # Idempotent
    assert normalize_final_status(normalize_final_status(canonical)) == canonical


def test_normalize_final_status_uppercase_passthrough():
    """Case-insensitive on input, lowercase canonical on output."""
    assert normalize_final_status("PASS") == "pass"
    assert normalize_final_status("Budget_Exhausted") == "budget_exhausted"


def test_normalize_final_status_ops_layer_no_summary():
    assert normalize_final_status("no_summary") == "missing"
    assert normalize_final_status("NO_SUMMARY") == "missing"


def test_normalize_final_status_ops_layer_broken_json():
    assert normalize_final_status("broken_json") == "missing"


def test_normalize_final_status_ops_layer_fail_rc():
    """The worker_runner's FAIL_rc=<rc> pattern → executor_incomplete."""
    assert normalize_final_status("FAIL_rc=1") == "executor_incomplete"
    assert normalize_final_status("FAIL_rc=247") == "executor_incomplete"
    assert normalize_final_status("FAIL_rc=-1") == "executor_incomplete"


def test_normalize_final_status_legacy_continue_to_executor_incomplete():
    """``continue`` was a supervisor verdict that occasionally leaked
    into finalStatus; it should normalize to executor_incomplete (the
    run was interrupted before reaching a terminal verdict)."""
    assert normalize_final_status("continue") == "executor_incomplete"


def test_normalize_final_status_legacy_stopped_to_executor_incomplete():
    """Pre-Round-6 resolve_attempt_outcome's catch-all was 'stopped'."""
    assert normalize_final_status("stopped") == "executor_incomplete"


def test_normalize_final_status_empty_to_missing():
    assert normalize_final_status("") == "missing"
    assert normalize_final_status(None) == "missing"
    assert normalize_final_status("   ") == "missing"


def test_normalize_final_status_unknown_to_missing():
    """Unknown values default to missing (rather than raising) so the
    caller's loop doesn't crash on a typo in an old summary.json."""
    assert normalize_final_status("totally_made_up") == "missing"


# ── normalize_supervisor_verdict ──────────────────────────────────────


def test_normalize_supervisor_verdict_canonical_passthrough():
    assert normalize_supervisor_verdict("pass") == "pass"
    assert normalize_supervisor_verdict("continue") == "continue"
    assert normalize_supervisor_verdict("fail") == "fail"


def test_normalize_supervisor_verdict_uppercase_passthrough():
    assert normalize_supervisor_verdict("PASS") == "pass"


def test_normalize_supervisor_verdict_legacy_infra_error_to_fail():
    """The historic ``verdict=infra_error`` shape must translate to
    ``fail`` (semantically the run didn't reach pass).  Infra flavour
    is preserved separately via score.infra_error=True."""
    assert normalize_supervisor_verdict("infra_error") == "fail"


def test_normalize_supervisor_verdict_legacy_rate_limit_to_fail():
    assert normalize_supervisor_verdict("rate_limit") == "fail"


def test_normalize_supervisor_verdict_empty_returns_empty():
    """Blank / unknown returns "" so callers can branch on presence."""
    assert normalize_supervisor_verdict("") == ""
    assert normalize_supervisor_verdict(None) == ""
    assert normalize_supervisor_verdict("nonsense") == ""


def test_normalize_supervisor_attempt_state_legacy_infra_to_terminal_failure():
    assert normalize_supervisor_attempt_state("infra_error") == "terminal_failure"
    assert normalize_supervisor_attempt_state("rate_limit") == "terminal_failure"


def test_normalize_supervisor_attempt_state_canonical_passthrough():
    for s in SUPERVISOR_ATTEMPT_STATES:
        assert normalize_supervisor_attempt_state(s) == s


# ── classify_attempt_outcome: priority order ───────────────────────


def test_classify_pass_via_attempt_state():
    assert classify_attempt_outcome(attempt_state="complete_and_passed") == "pass"


def test_classify_pass_via_verdict():
    assert classify_attempt_outcome(verdict="pass") == "pass"


def test_classify_pass_via_passed_flag():
    assert classify_attempt_outcome(passed_flag=True) == "pass"


def test_classify_fail_via_attempt_state():
    assert classify_attempt_outcome(attempt_state="terminal_failure") == "fail"


def test_classify_rate_limit_wins_over_verdict_pass():
    """Infra checks come before supervisor pass — rate_limit on the
    upstream provider trumps any later signal."""
    out = classify_attempt_outcome(verdict="pass", rate_limit=True)
    assert out == "rate_limit"


def test_classify_infra_error_via_flag():
    assert classify_attempt_outcome(infra_error=True) == "infra_error"


def test_classify_pre_exec_failed_via_infra_type():
    assert classify_attempt_outcome(
        infra_error=True, infra_error_type="pre_exec_failed",
    ) == "pre_exec_failed"


def test_classify_completion_gate_failed_demotes_pass_to_fail():
    """Supervisor wanted to call pass but executor didn't sign off →
    demote to fail.  Must beat the verdict=pass branch."""
    out = classify_attempt_outcome(verdict="pass", completion_gate_failed=True)
    assert out == "fail"


def test_classify_executor_never_completed_to_executor_incomplete():
    """Round-7: executor_incomplete is the strong-sense catch-all — reached
    only when there is NO explicit terminal signal AND the executor never
    completed a turn (crash / killed-with-no-reason)."""
    out = classify_attempt_outcome(
        verdict="continue",
        executor_completed_ever=False,
        # no terminal_reason / timeout / budget signal at all
    )
    assert out == "executor_incomplete"


def test_classify_timeout_precedes_incomplete_round7():
    """Round-7 (reversed from Round-5): an explicit global-timeout terminal
    classifies as global_timeout EVEN IF the executor never cleanly completed
    a turn — the run did exhaust its budget, so it is terminal (bounded retry),
    not incomplete (which the dispatcher would re-dispatch forever)."""
    out = classify_attempt_outcome(
        verdict="continue",
        executor_completed_ever=False,
        terminal_reason="global-timeout-executor",
    )
    assert out == "global_timeout"


def test_classify_global_timeout_when_executor_did_complete():
    """If executor cleanly completed at least one turn AND wall-clock
    cap hit, classify as global_timeout."""
    out = classify_attempt_outcome(
        verdict="continue",
        executor_completed_ever=True,
        terminal_reason="global-timeout-executor",
    )
    assert out == "global_timeout"


def test_classify_global_timeout_via_exit_124():
    """agent_exit_code=124 is the SIGTERM-from-timeout indicator."""
    out = classify_attempt_outcome(
        verdict="continue",
        executor_completed_ever=True,
        agent_exit_code=124,
    )
    assert out == "global_timeout"


def test_classify_budget_exhausted_when_executor_completed():
    out = classify_attempt_outcome(
        verdict="continue",
        executor_completed_ever=True,
        terminal_reason="followup-limit-reached",
    )
    assert out == "budget_exhausted"


def test_classify_budget_exhausted_via_flag():
    out = classify_attempt_outcome(
        verdict="continue",
        executor_completed_ever=True,
        followup_budget_exhausted=True,
    )
    assert out == "budget_exhausted"


def test_classify_verdict_fail_catchall():
    """verdict=fail without attempt_state=terminal_failure is a rare
    schema variant — still classify as fail."""
    out = classify_attempt_outcome(
        verdict="fail",
        executor_completed_ever=True,
    )
    assert out == "fail"


def test_classify_verdict_fail_beats_executor_completed_false():
    """Symmetric with verdict=pass: an explicit supervisor verdict=fail
    trumps executor_completed_ever=False.  The presence of the verdict
    in score.json proves at least one supervisor cycle ran, which is
    stronger evidence than the framework's completion flag."""
    out = classify_attempt_outcome(
        verdict="fail",
        executor_completed_ever=False,
        agent_exit_code=1,
    )
    assert out == "fail"


def test_classify_verdict_pass_beats_executor_completed_false():
    """Companion pin for the symmetric branch: verdict=pass also trumps
    executor_completed_ever=False (already the case pre-Round-6, just
    making the symmetry explicit)."""
    out = classify_attempt_outcome(
        verdict="pass",
        executor_completed_ever=False,
    )
    assert out == "pass"


def test_classify_default_is_executor_incomplete_not_stopped():
    """Round-6 change: default catch-all is executor_incomplete (not
    the legacy 'stopped' value)."""
    out = classify_attempt_outcome(
        # supervisor reached no terminal verdict, executor completed cleanly,
        # no terminal_reason — what was the run doing?  Treat as incomplete.
        verdict="",
        attempt_state="",
        executor_completed_ever=True,
    )
    assert out == "executor_incomplete"


# ── build_status_counts ───────────────────────────────────────────────


def test_build_status_counts_complete_keys():
    """Every FINAL_STATUS_ORDER entry must be a key in the output,
    zero-padded if no result has it."""
    counts = build_status_counts([])
    assert set(counts.keys()) == set(FINAL_STATUS_ORDER)
    assert all(v == 0 for v in counts.values())


def test_build_status_counts_counts_canonical_values():
    results = [
        {"finalStatus": "pass"},
        {"finalStatus": "pass"},
        {"finalStatus": "fail"},
        {"finalStatus": "budget_exhausted"},
    ]
    counts = build_status_counts(results)
    assert counts["pass"] == 2
    assert counts["fail"] == 1
    assert counts["budget_exhausted"] == 1
    # Other keys still present with 0
    assert counts["executor_incomplete"] == 0


def test_build_status_counts_normalizes_ops_layer():
    """ops-layer values get normalised before counting — no 'broken_json'
    leaks into the output."""
    results = [
        {"finalStatus": "no_summary"},
        {"finalStatus": "broken_json"},
        {"finalStatus": "FAIL_rc=247"},
    ]
    counts = build_status_counts(results)
    assert counts["missing"] == 2  # no_summary + broken_json
    assert counts["executor_incomplete"] == 1  # FAIL_rc=247


def test_build_status_counts_handles_underscore_alias_key():
    """Some legacy code wrote 'final_status' (snake_case) instead of
    'finalStatus'.  build_status_counts must read both."""
    results = [
        {"final_status": "pass"},
        {"finalStatus": "pass"},
    ]
    counts = build_status_counts(results)
    assert counts["pass"] == 2


# ── score-based pass promotion (Path A / Path B shared gate) ────────────


@pytest.mark.parametrize(
    "blocking",
    sorted(["fail", "executor_incomplete", "infra_error", "rate_limit", "pre_exec_failed"]),
)
def test_apply_score_based_promotion_never_overrides_blocking_status(blocking):
    """Definitive not-pass classifications must survive a high score.

    Supervisor or runtime has already rendered a not-pass verdict; the score
    field alone is not strong enough evidence to flip that to pass.
    """
    status, passed = apply_score_based_promotion(blocking, 0.95, 0.5)
    assert status == blocking
    assert passed is False


def test_apply_score_based_promotion_promotes_budget_exhausted_at_threshold():
    """Budget exhausted is a completed-normally state — score >= threshold
    means the agent met the bar even though it used the full budget."""
    status, passed = apply_score_based_promotion("budget_exhausted", 0.7, 0.7)
    assert status == "pass"
    assert passed is True


def test_apply_score_based_promotion_promotes_global_timeout_above_threshold():
    status, passed = apply_score_based_promotion("global_timeout", 0.81, 0.8)
    assert status == "pass"
    assert passed is True


def test_apply_score_based_promotion_below_threshold_returns_input():
    status, passed = apply_score_based_promotion("budget_exhausted", 0.49, 0.5)
    assert status == "budget_exhausted"
    assert passed is False


def test_apply_score_based_promotion_threshold_is_inclusive():
    """``final_score >= success_threshold`` — equality counts as a pass."""
    status, passed = apply_score_based_promotion("budget_exhausted", 0.5, 0.5)
    assert status == "pass"
    assert passed is True
