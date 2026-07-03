"""Round 9 / B4: source-level guards on the WebUI EDICT badge +
failure-cycle highlight.

The WebUI is a static JS bundle so we can't unit-test it from Python
proper, but we can pin the source-level contract — the renderer must
read the right fields from the payload and emit the right CSS hooks,
otherwise the badge / highlight silently disappear after a refactor.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEGACY_JS = ROOT / "webui" / "static" / "pages" / "trace" / "legacy.js"
STYLE_CSS = ROOT / "webui" / "static" / "style.css"


def test_runmetrics_extracts_edict_block_from_summary() -> None:
    """``runMetrics()`` must pull the edict block from either
    ``taskSummary.edict`` (preferred — emitted by Round 9 / B3) or
    fall back to the agent_sessions_manifest fields.  Lock both
    sources because rsync-only attempts can drop the per-task summary
    while leaving the manifest in place."""
    text = LEGACY_JS.read_text(encoding="utf-8")
    assert "taskSummary.edict" in text, (
        "runMetrics must read taskSummary.edict (Round 9 / B3 emit point)"
    )
    assert "manifest.edictMode" in text, (
        "runMetrics must fall back to agentSessionManifest.edictMode"
    )


def test_edict_badge_function_exists_and_renders_short_commit() -> None:
    """``edictBadgeHtml()`` is the badge renderer; the function must
    exist + slice the commit to a short display value (full commit
    sha is too wide for the header pill row)."""
    text = LEGACY_JS.read_text(encoding="utf-8")
    assert "function edictBadgeHtml" in text, (
        "edictBadgeHtml renderer missing from trace legacy.js"
    )
    assert "commit).slice(0," in text, (
        "edictBadgeHtml must shorten the commit string for display"
    )


def test_edict_badge_invoked_in_summary_header() -> None:
    """The header summary must invoke ``edictBadgeHtml(metrics.edict)``;
    without the call the badge never makes it into the DOM."""
    text = LEGACY_JS.read_text(encoding="utf-8")
    assert "edictBadgeHtml(metrics.edict)" in text, (
        "renderSummary must invoke edictBadgeHtml(metrics.edict)"
    )


def test_failure_cycle_class_applied_when_verdict_or_state_signals_failure() -> None:
    """``renderSupervisorCycle`` must flag failure cycles so reviewers
    don't have to click every fold open to find the broken one."""
    text = LEGACY_JS.read_text(encoding="utf-8")
    assert "check-fold-failure" in text, (
        "failure-cycle CSS hook missing — supervisor trace highlight broken"
    )
    # The verdict + state sets we treat as failure signals
    for signal in ("fail", "infra_error", "rate_limit", "executor_incomplete"):
        assert f'"{signal}"' in text, (
            f"failure-signal classifier missing verdict/state {signal!r}"
        )


def test_css_defines_failure_and_edict_badge_classes() -> None:
    """The CSS rules backing the JS hooks must exist; otherwise the
    JS happily emits classes that produce no visual change."""
    text = STYLE_CSS.read_text(encoding="utf-8")
    assert ".check-fold.check-fold-failure" in text, (
        "style.css missing .check-fold-failure rule for failure-cycle highlight"
    )
    assert ".summary-pill.edict-badge" in text, (
        "style.css missing .edict-badge rule for EDICT header pill"
    )


def test_edict_badge_uses_mode_official_specs_local_adapter() -> None:
    """The badge tooltip / fallback mode label must match the constant
    we emit in lib/runner/edict.py::EDICT_MODE; otherwise a rename in
    one place would silently desync the UI."""
    text = LEGACY_JS.read_text(encoding="utf-8")
    assert "official_specs_local_adapter" in text, (
        "WebUI badge mode label out of sync with lib.runner.edict.EDICT_MODE"
    )
