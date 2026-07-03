"""Round 16 / P1-3: the executor rate-limit retry loop must re-check
``task.max_total_seconds`` budget on every iteration — before sleep,
before re-running the executor, and accumulate sleep time into
``executor_elapsed_seconds``.

A full end-to-end test of ``run_one_attempt`` requires mocking
container + agents + supervisor + recording + artifacts + transcripts,
which is heavier than this commit warrants.  Instead we pin the
contract at the source / AST level so a future refactor can't silently
drop the budget gate.

These tests are paired with a behavioral test that will run inside the
isolated Round 16 orchestra run (where a real rate-limited model will
exercise the retry loop with a finite budget).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


ORCH_PY = Path(__file__).resolve().parents[2] / "lib" / "runner" / "orchestration.py"


@pytest.fixture(scope="module")
def orch_src() -> str:
    return ORCH_PY.read_text(encoding="utf-8")


def _retry_loop_body(orch_src: str) -> str:
    """Return the source text of the executor rate-limit retry while-loop.

    The loop is the one gated on ``rate_limit_this_turn is not None and
    rate_limit_retry_count < DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES``.
    """
    tree = ast.parse(orch_src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        if not isinstance(node.test, ast.BoolOp):
            continue
        # We're looking for the retry loop specifically — it's a
        # BoolOp(And, [Compare("rate_limit_this_turn", IsNot, None),
        #              Compare("rate_limit_retry_count", Lt,
        #                      "DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES")]).
        bool_op_src = ast.get_source_segment(orch_src, node.test) or ""
        if (
            "rate_limit_this_turn" in bool_op_src
            and "DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES" in bool_op_src
        ):
            return ast.get_source_segment(orch_src, node) or ""
    raise AssertionError("Could not locate executor rate-limit retry loop")


def test_retry_loop_rechecks_budget_before_sleep(orch_src: str) -> None:
    body = _retry_loop_body(orch_src)
    # We require an explicit ``remaining = task.max_total_seconds - executor_elapsed_seconds``
    # appearing BEFORE the ``time.sleep(sleep_for)`` call.
    assert "task.max_total_seconds - executor_elapsed_seconds" in body, (
        "retry loop must recompute remaining budget against "
        "executor_elapsed_seconds; missing the subtraction"
    )
    remaining_idx = body.find("task.max_total_seconds - executor_elapsed_seconds")
    sleep_idx = body.find("time.sleep(sleep_for)")
    assert remaining_idx != -1 and sleep_idx != -1
    assert remaining_idx < sleep_idx, (
        "remaining-budget recompute must happen BEFORE the sleep so an "
        "exhausted budget breaks out of the loop instead of waiting"
    )


def test_retry_loop_clips_sleep_to_remaining_budget(orch_src: str) -> None:
    body = _retry_loop_body(orch_src)
    # The sleep_for clip must guard against waiting past the budget.
    assert "sleep_for = min(" in body, "sleep_for must be clipped via min(...)"
    assert (
        "max(0.0, task.max_total_seconds - executor_elapsed_seconds)" in body
        or "max(0, task.max_total_seconds - executor_elapsed_seconds)" in body
    ), (
        "sleep_for clip must use max(0, remaining) so we never sleep "
        "past the budget"
    )


def test_retry_loop_accounts_sleep_against_executor_budget(orch_src: str) -> None:
    body = _retry_loop_body(orch_src)
    # After sleep we must add the elapsed wall-clock back into
    # executor_elapsed_seconds so subsequent iterations see the real
    # remaining budget.
    assert (
        "executor_elapsed_seconds += time.time() - _sleep_started_at" in body
        or "executor_elapsed_seconds += (time.time() - _sleep_started_at)" in body
    ), (
        "sleep duration must be added to executor_elapsed_seconds so "
        "the wall-clock budget is enforced consistently"
    )


def test_retry_loop_recomputes_timeout_per_retry(orch_src: str) -> None:
    body = _retry_loop_body(orch_src)
    # The retry executor call must use a fresh ``retry_timeout_seconds``
    # derived from the current remaining budget, not the initial-turn
    # ``timeout_seconds`` value.
    assert "retry_timeout_seconds" in body, (
        "retry must recompute its own timeout (retry_timeout_seconds) "
        "from current remaining budget"
    )
    assert "agents.run_agent(\n" in body or "agents.run_agent(" in body
    assert "retry_timeout_seconds" in body
    # And the run_agent call inside the retry should reference the new
    # variable, not the stale ``timeout_seconds``.
    run_agent_block = body[body.find("agents.run_agent("):]
    assert "retry_timeout_seconds" in run_agent_block[:400], (
        "agents.run_agent inside the retry loop must pass "
        "retry_timeout_seconds (the budget-aware value)"
    )


def test_post_retry_loop_breaks_on_global_timeout_executor(orch_src: str) -> None:
    """After the retry loop ends, the function must short-circuit on
    ``terminal_decision.reason == 'global-timeout-executor'`` so the
    supervisor / completion gate / continuation logic doesn't run for
    an attempt that already crossed its budget."""
    # The break must be lexically positioned after the retry while-loop
    # but before the rate-limit annotation block downstream.
    retry_idx = orch_src.find("rate_limit_retry_count < DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES")
    assert retry_idx != -1
    # Find where the retry while ends — look for the early-break check
    # in the trailing section.
    expected = (
        "if terminal_decision.get(\"reason\") == \"global-timeout-executor\":"
    )
    break_idx = orch_src.find(expected, retry_idx)
    assert break_idx != -1, (
        "missing post-retry-loop early-break that skips supervisor for "
        "budget-exhausted attempts"
    )


def test_budget_check_emits_canonical_terminal_decision(orch_src: str) -> None:
    body = _retry_loop_body(orch_src)
    # The two budget-exhaustion paths inside the retry loop must both
    # set the same terminal_decision shape that the top-of-loop check
    # uses — including ``reason: global-timeout-executor``.
    assert body.count("\"reason\": \"global-timeout-executor\"") >= 2, (
        "retry loop should set terminal_decision in BOTH the pre-sleep "
        "and pre-run_agent budget exhaustion paths"
    )
