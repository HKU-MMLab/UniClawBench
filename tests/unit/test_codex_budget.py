"""Fix 1 — bound the supervisor/grader codex call by wall-clock.

A single ``run_codex_prompt`` call may retry up to ``DEFAULT_CODEX_RATE_LIMIT_RETRIES``
(10) times with a per-call timeout of ``DEFAULT_CODEX_TIMEOUT_SECONDS`` (300s).
That ~3600s worst case exceeds the ``run_eval`` watchdog grace (max_total+1800s),
so a grader rate-limit/timeout storm wedges the whole eval process until
``os._exit(124)`` — which ``worker_runner`` then mislabels ``global_timeout``.

``codex_call_budget_exceeded`` lets the retry loop surrender on a wall-clock
budget (well under the watchdog) so the caller can record a clean ``rate_limit``
terminal instead of wedging.
"""
from __future__ import annotations

from lib.supervision.codex import codex_call_budget_exceeded


def test_budget_zero_disables_guard():
    # budget<=0 means "no wall-clock cap" — never trips no matter how long.
    assert codex_call_budget_exceeded(
        0.0, rate_limit_retries=5, transient_retries=2, now=1e9, budget_seconds=0
    ) is False


def test_first_attempt_never_trips_even_when_over_budget():
    # Before any retry, always allow the first real call to complete — we never
    # give up before trying once.
    assert codex_call_budget_exceeded(
        0.0, rate_limit_retries=0, transient_retries=0, now=1e9, budget_seconds=900
    ) is False


def test_trips_after_rate_limit_retry_over_budget():
    assert codex_call_budget_exceeded(
        0.0, rate_limit_retries=1, transient_retries=0, now=901.0, budget_seconds=900
    ) is True


def test_trips_after_transient_retry_at_budget_boundary():
    # >= boundary trips.
    assert codex_call_budget_exceeded(
        0.0, rate_limit_retries=0, transient_retries=1, now=900.0, budget_seconds=900
    ) is True


def test_does_not_trip_under_budget():
    assert codex_call_budget_exceeded(
        0.0, rate_limit_retries=2, transient_retries=0, now=500.0, budget_seconds=900
    ) is False
