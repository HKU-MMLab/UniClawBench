"""run_eval.py arms a last-resort self-timeout so a hung grader call can't leave
a zombie process lingering for hours on the worker.  Test the deadline logic
(the os._exit watchdog thread itself is not unit-testable in-process)."""
from __future__ import annotations

import importlib

re_mod = importlib.import_module("scripts.run_eval")


def test_override_wins(tmp_path):
    assert re_mod._watchdog_deadline(tmp_path / "x.yaml", 555) == 555


def test_zero_override_disables(tmp_path):
    # 0 means "no watchdog"; _arm_watchdog returns early on <= 0.
    assert re_mod._watchdog_deadline(tmp_path / "x.yaml", 0) == 0


def test_default_on_unreadable_task(tmp_path):
    assert re_mod._watchdog_deadline(tmp_path / "nope.yaml", None) == 1800 + re_mod._WATCHDOG_GRACE_SECONDS


def test_derives_from_real_task_max_total():
    y = re_mod.ROOT_DIR / "tasks/101_skill_usage/task_101_03_access_log_regex.yaml"
    # that task pins max_total_seconds: 1800
    assert re_mod._watchdog_deadline(y, None) == 1800 + re_mod._WATCHDOG_GRACE_SECONDS


def test_arm_watchdog_noop_on_zero():
    # Should not spawn a thread / raise.
    re_mod._arm_watchdog(0)
    re_mod._arm_watchdog(-5)
