"""Round 9 / Phase D fix: orchestrator idle-after-dispatch detection.

The worker3 validation showed openclaw_edict taking 20m vs openclaw 4m
on the same task.  Investigation found that after the last meaningful
agent invocation, the orchestrator polled the kanban every 3s for
~16 minutes waiting for a ``state=Done`` transition that the model
(gpt-5.4) never explicitly wrote — it used ``kanban_update.py progress``
for status text updates and emitted a substantive final answer to the
conversation, but skipped the explicit terminal-state transition.

The orchestrator now detects this stall: after a dispatched agent's
subprocess returns cleanly AND the kanban state stays unchanged for
``IDLE_AFTER_DISPATCH_SECONDS``, it triggers ``invoke_taizi_final_report``
and exits the polling loop.

This module pins the new logic by parsing the orchestrator source +
verifying:

1. The ``IDLE_AFTER_DISPATCH_SECONDS`` constant exists with a sane
   default (30s).
2. The polling loop tracks ``last_dispatch_at`` after each dispatch.
3. The else-branch (state unchanged) checks the idle threshold before
   sleeping again.
4. The idle branch invokes ``invoke_taizi_final_report`` with a reason
   that includes ``idle-after-dispatch``.
"""
from __future__ import annotations

import re
from pathlib import Path


ORCHESTRATOR = Path(__file__).resolve().parents[2] / "docker" / "edict_orchestrator.py"


def test_idle_after_dispatch_constant_exists() -> None:
    """Round 9 / Phase D fix: the env-tunable constant + sane default."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "IDLE_AFTER_DISPATCH_SECONDS" in text, (
        "IDLE_AFTER_DISPATCH_SECONDS constant missing"
    )
    # Default should be a small-but-not-trivial value
    m = re.search(
        r'IDLE_AFTER_DISPATCH_SECONDS\s*=\s*int\(\s*os\.environ\.get\([^,]+,\s*"(\d+)"\)\s*\)',
        text,
    )
    assert m, "IDLE_AFTER_DISPATCH_SECONDS default value not parseable"
    default = int(m.group(1))
    assert 10 <= default <= 120, (
        f"IDLE_AFTER_DISPATCH_SECONDS default {default}s outside reasonable "
        "range — too short = false-positive on slow dispatches, too long = "
        "wastes wall-clock on stalled chains"
    )


def test_env_var_is_clawbench_namespaced() -> None:
    """Env-var name must be discoverable + consistent with the other
    CLAWBENCH_EDICT_ORCH_* knobs."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "CLAWBENCH_EDICT_ORCH_IDLE_AFTER_DISPATCH" in text


def test_polling_loop_tracks_last_dispatch_at() -> None:
    """The dispatch branch must stamp ``last_dispatch_at = time.time()``
    after invoke_agent(); without this the idle check has no anchor.
    The variable type annotation + a non-None initializer must be
    present (see ``test_last_dispatch_at_anchored_to_initial_taizi``
    for the specific anchoring requirement)."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "last_dispatch_at = time.time()" in text, (
        "polling loop must stamp last_dispatch_at after dispatch"
    )
    # Type annotation must be present (initial value is asserted by a
    # separate test that requires time.time() seeding)
    assert "last_dispatch_at: float | None" in text, (
        "last_dispatch_at must be declared with its float|None type "
        "annotation before the dispatch loop"
    )


def test_idle_branch_triggers_final_report() -> None:
    """The else-branch (state unchanged) must check the idle threshold
    and invoke ``invoke_taizi_final_report`` when exceeded, with a
    reason string that includes ``idle-after-dispatch`` so post-run
    logs identify why the orchestrator exited."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "IDLE_AFTER_DISPATCH_SECONDS" in text
    # Final-report call from the idle branch with the right reason
    assert "idle-after-dispatch" in text, (
        "idle-branch final report reason must include 'idle-after-dispatch'"
    )
    # And it must actually invoke the final-report function
    assert text.count("invoke_taizi_final_report(") >= 3, (
        "idle branch must add a 3rd invoke_taizi_final_report call site "
        "(in addition to terminal-state branch + timeout branch)"
    )


def test_idle_branch_sets_final_report_invoked_flag() -> None:
    """When the idle branch fires final-report, it must mark
    ``final_report_invoked = True`` so the timeout-tail path doesn't
    fire the final report twice (taizi would receive two terminal
    nudges back-to-back)."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    # The idle branch should set the flag before break
    # We do a less-strict check: 2+ occurrences of final_report_invoked = True
    # (once in terminal-state branch, once in idle branch)
    assigns = text.count("final_report_invoked = True")
    assert assigns >= 2, (
        f"final_report_invoked = True assigned only {assigns} times; idle "
        "branch must also set it to prevent double-fire of the final report"
    )


def test_idle_threshold_check_uses_last_dispatch_at() -> None:
    """Sanity: the idle check must reference ``last_dispatch_at`` AND
    handle the ``None`` case (no dispatch yet) so we don't trigger
    final-report when taizi hasn't even started."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "last_dispatch_at is not None" in text, (
        "idle check must guard against last_dispatch_at being None "
        "(no dispatch yet — would prematurely fire final report)"
    )


def test_last_dispatch_at_anchored_to_initial_taizi() -> None:
    """Round 9 / Phase D follow-up: ``last_dispatch_at`` must be
    seeded with ``time.time()`` at the dispatch-loop start, not
    ``None``.  Without this, cycle 2+ runs where taizi returns and
    the kanban state lands in an unmappable combo (e.g. ``state=Doing
    org=皇上``) would never set last_dispatch_at — the idle check
    falls through to ``last_dispatch_at is not None`` being False
    and the orchestrator polls until wall-clock timeout.

    This is the exact bug we hit on the worker3 validation re-run:
    cycle 1 worked because dispatchable state transitions happened;
    cycle 2 stalled because the model emitted a final answer + put
    the kanban into ``Doing org=皇上`` with no follow-up dispatch.
    """
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    # Must initialize to time.time(), not None
    assert "last_dispatch_at: float | None = time.time()" in text, (
        "last_dispatch_at must be initialized to time.time() (the moment "
        "the initial taizi dispatch returned), not None — otherwise the "
        "first iteration's idle check is permanently disabled"
    )


def test_no_agent_mapping_branch_resets_idle_clock() -> None:
    """When the orchestrator observes a state change it can't dispatch
    on (no agent mapping), ``last_dispatch_at`` must still be updated
    so the idle clock measures "time since last sign of life on the
    kanban".  Without this, a sequence of "no agent mapping" skips
    followed by a stuck state never fires the idle check.
    """
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    # The state-change branch (whether dispatchable or not) must always
    # update last_dispatch_at.  We look for a single assignment AFTER
    # both the if/else arms, OR two assignments — either satisfies.
    # The simplest pin is that the assignment isn't ONLY inside the
    # `if agent:` arm.
    # Find the assignment lines and verify there's at least one outside
    # the `if agent:` block.
    lines = text.splitlines()
    in_if_agent = False
    in_changed = False
    found_outside = False
    indent_changed = None
    indent_if_agent = None
    for line in lines:
        stripped = line.lstrip()
        cur_indent = len(line) - len(stripped)
        if stripped.startswith("if changed:"):
            in_changed = True
            indent_changed = cur_indent
            continue
        if in_changed:
            if cur_indent <= indent_changed and stripped:
                in_changed = False
                continue
            if stripped.startswith("if agent:"):
                in_if_agent = True
                indent_if_agent = cur_indent
                continue
            if in_if_agent and cur_indent <= indent_if_agent and stripped:
                in_if_agent = False
            if "last_dispatch_at = time.time()" in stripped and not in_if_agent:
                found_outside = True
                break
    assert found_outside, (
        "last_dispatch_at = time.time() must appear OUTSIDE the `if agent:` "
        "arm so 'no agent mapping' state changes also reset the idle clock"
    )
