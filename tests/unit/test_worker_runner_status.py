"""Fix 2 — worker_runner must NOT label a run_eval watchdog rc=124 as global_timeout.

rc=124 reaching worker_runner is the ``run_eval`` watchdog (``os._exit(124)``)
force-killing a WEDGED eval process (a hung supervisor/grader call, an un-joined
thread, a rate-limit retry storm). The executor did NOT exceed its own budget —
the whole eval wedged — so this is ``executor_incomplete`` (bounded rerun), not
``global_timeout``. ``global_timeout`` is reserved for the in-loop cumulative
executor-budget terminal, which writes its own terminal ``summary.json`` and
therefore never reaches this stale-running rewrite path.
"""
from __future__ import annotations

from lib.status import normalize_final_status
from scripts.orchestra.worker_runner import _terminalize_stale_nonterminal


def test_watchdog_rc124_on_stale_running_is_not_global_timeout():
    raw = _terminalize_stale_nonterminal("running", 124)
    # rc=124 maps to FAIL_rc=124 -> executor_incomplete, NOT global_timeout.
    assert normalize_final_status(raw) == "executor_incomplete"
    assert normalize_final_status(raw) != "global_timeout"


def test_watchdog_rc124_on_missing_is_executor_incomplete():
    assert normalize_final_status(_terminalize_stale_nonterminal("missing", 124)) == "executor_incomplete"


def test_other_nonzero_rc_stays_executor_incomplete():
    assert normalize_final_status(_terminalize_stale_nonterminal("running", 137)) == "executor_incomplete"


def test_in_loop_global_timeout_summary_is_passed_through():
    # The legit in-loop cumulative timeout writes finalStatus=global_timeout
    # itself; raw_status is already 'global_timeout' (not running/missing) so it
    # must pass through untouched even with rc=124.
    assert _terminalize_stale_nonterminal("global_timeout", 124) == "global_timeout"


def test_clean_terminal_passthrough():
    assert _terminalize_stale_nonterminal("pass", 0) == "pass"
    assert _terminalize_stale_nonterminal("budget_exhausted", 0) == "budget_exhausted"


def test_running_with_zero_or_none_rc_untouched():
    # A still-running attempt that exited 0 / no rc is NOT terminalized here.
    assert _terminalize_stale_nonterminal("running", 0) == "running"
    assert _terminalize_stale_nonterminal("running", None) == "running"
