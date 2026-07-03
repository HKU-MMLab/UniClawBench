"""Phase 4 — pin backend-specific completion relaxation strategies.

``executor_completion_state`` delegates the per-backend special cases
(``openclaw_edict`` taizi-final-answer-despite-orch-exit, ``nanobot`` nonzero-
exit relaxation and clean-exit fallback) to
``lib/runner/completion_strategies.py``. These tests lock the dispatch table
so future refactors can't silently change which backend gets which behaviour.
"""
from __future__ import annotations

from lib.runner.completion_strategies import (
    SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS,
    TranscriptSnapshot,
    fallback_zero_exit,
    relax_nonzero_exit,
)


# ── nonzero-exit relaxation ────────────────────────────────────────────────


def test_relax_nonzero_exit_returns_none_for_unknown_backend():
    # codex / any backend without an explicit strategy keeps the strict
    # signal contract (completed=False, reason="nonzero-exit" upstream).
    snapshot = TranscriptSnapshot(has_last_message=True, final_text="x" * 400)
    assert relax_nonzero_exit("codex", snapshot) is None
    assert relax_nonzero_exit("some_unknown_backend", snapshot) is None


# ── openclaw nonzero-exit relaxation ───────────────────────────────────────
# openclaw exits nonzero when a trailing, non-contract command (e.g. a stray
# ``git commit`` returning "Author identity unknown" → rc=1) runs AFTER the
# agent already wrote a clean final answer. Mirror the edict/nanobot relaxation:
# a text-only last message with no pending tool call and no positively-
# incomplete API stop reason is a completion, regardless of the process rc.


def test_relax_nonzero_exit_openclaw_accepts_clean_final():
    # openclaw often does not surface an api_stop_reason at all ("").
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="here is the reconciled k8s manifest ...",
        api_stop_reason="",
    )
    decision = relax_nonzero_exit("openclaw", snapshot)
    assert decision is not None
    assert decision.completed is True
    assert decision.reason == "openclaw-final-answer-despite-nonzero-exit"


def test_relax_nonzero_exit_openclaw_accepts_explicit_complete_stop():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="done, results saved.",
        api_stop_reason="end_turn",
    )
    decision = relax_nonzero_exit("openclaw", snapshot)
    assert decision is not None and decision.completed is True


def test_relax_nonzero_exit_openclaw_rejects_pending_tool_call():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=True,
        final_text="running the tests now",
        api_stop_reason="",
    )
    assert relax_nonzero_exit("openclaw", snapshot) is None


def test_relax_nonzero_exit_openclaw_rejects_incomplete_stop_reason():
    # api said the model was truncated mid-answer (length) or still calling a
    # tool (toolUse) — a genuine incompleteness, keep strict.
    for sr in ("length", "max_tokens", "toolUse", "tool_use"):
        snapshot = TranscriptSnapshot(
            has_last_message=True,
            last_message_has_tool_call=False,
            final_text="partial answer ...",
            api_stop_reason=sr,
        )
        assert relax_nonzero_exit("openclaw", snapshot) is None, sr


def test_relax_nonzero_exit_openclaw_rejects_empty_text():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="   ",
        api_stop_reason="",
    )
    assert relax_nonzero_exit("openclaw", snapshot) is None


def test_relax_nonzero_exit_returns_none_when_no_last_message():
    snapshot = TranscriptSnapshot(has_last_message=False)
    assert relax_nonzero_exit("nanobot", snapshot) is None
    assert relax_nonzero_exit("openclaw_edict", snapshot) is None


def test_relax_nonzero_exit_edict_accepts_substantive_text_only_final():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="x" * SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS,
        still_routing=False,
    )
    decision = relax_nonzero_exit("openclaw_edict", snapshot)
    assert decision is not None
    assert decision.completed is True
    assert decision.reason == "edict-taizi-final-answer-despite-orch-exit"


def test_relax_nonzero_exit_edict_rejects_below_threshold():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="x" * (SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS - 1),
        still_routing=False,
    )
    assert relax_nonzero_exit("openclaw_edict", snapshot) is None


def test_relax_nonzero_exit_edict_rejects_when_still_routing():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="x" * 500,
        still_routing=True,
    )
    assert relax_nonzero_exit("openclaw_edict", snapshot) is None


def test_relax_nonzero_exit_edict_rejects_when_pending_tool_call():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=True,
        final_text="x" * 500,
        still_routing=False,
    )
    assert relax_nonzero_exit("openclaw_edict", snapshot) is None


def test_relax_nonzero_exit_nanobot_accepts_any_nonempty_text():
    """Nanobot has no 200-char threshold — final answers vary from one line to KBs."""
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="done.",
    )
    decision = relax_nonzero_exit("nanobot", snapshot)
    assert decision is not None
    assert decision.completed is True
    assert decision.reason == "nanobot-final-answer-despite-nonzero-exit"


def test_relax_nonzero_exit_nanobot_rejects_empty_text():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="",
    )
    assert relax_nonzero_exit("nanobot", snapshot) is None


def test_relax_nonzero_exit_nanobot_rejects_pending_tool_call():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=True,
        final_text="final answer",
    )
    assert relax_nonzero_exit("nanobot", snapshot) is None


# ── zero-exit fallback ─────────────────────────────────────────────────────


def test_fallback_zero_exit_nanobot_requires_non_empty_final_text():
    """Once the standard checks fall through to this fallback, nanobot
    opts into completion ONLY when the last message carries non-empty text."""
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="ok",
    )
    decision = fallback_zero_exit("nanobot", snapshot)
    assert decision is not None
    assert decision.completed is True
    assert decision.reason == "nanobot-clean-exit-no-tool-call"


def test_fallback_zero_exit_nanobot_rejects_empty_final_text():
    """Empty final_text on a clean exit is not a completion signal —
    must fall through to ``missing-completion-signal`` so the run can
    land on ``executor_incomplete`` rather than a spurious pass/budget."""
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="",
    )
    assert fallback_zero_exit("nanobot", snapshot) is None


def test_fallback_zero_exit_nanobot_rejects_whitespace_only_final_text():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="   \n\t  ",
    )
    assert fallback_zero_exit("nanobot", snapshot) is None


def test_fallback_zero_exit_nanobot_rejects_pending_tool_call():
    """Even with text, a pending tool call should not be treated as completion."""
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=True,
        final_text="ok",
    )
    assert fallback_zero_exit("nanobot", snapshot) is None


def test_fallback_zero_exit_openclaw_accepts_clean_text_only():
    """Round-7: openclaw zero-exit with a clean text-only final message (no
    pending tool call, no positively-incomplete stop reason) IS a completion —
    symmetric with relax_nonzero_exit's openclaw branch.  Only consulted on a
    supervisor verdict=pass turn, so it rescues correct runs previously demoted
    to executor_incomplete (supervisor 1.0, finalStatus incomplete)."""
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=False,
        final_text="ok",
    )
    decision = fallback_zero_exit("openclaw", snapshot)
    assert decision is not None
    assert decision.completed is True
    assert decision.reason == "openclaw-clean-exit-text-only"


def test_fallback_zero_exit_openclaw_rejects_pending_tool_call():
    snapshot = TranscriptSnapshot(
        has_last_message=True,
        last_message_has_tool_call=True,
        final_text="ok",
    )
    assert fallback_zero_exit("openclaw", snapshot) is None


def test_fallback_zero_exit_openclaw_rejects_incomplete_stop_reason():
    # api said the model was truncated mid-answer (length) or still calling a
    # tool (toolUse) — a genuine incompleteness, keep strict even at zero exit.
    for sr in ("length", "max_tokens", "toolUse", "tool_use"):
        snapshot = TranscriptSnapshot(
            has_last_message=True,
            last_message_has_tool_call=False,
            final_text="partial answer ...",
            api_stop_reason=sr,
        )
        assert fallback_zero_exit("openclaw", snapshot) is None


def test_fallback_zero_exit_strict_for_edict():
    snapshot = TranscriptSnapshot(has_last_message=True, final_text="ok")
    assert fallback_zero_exit("openclaw_edict", snapshot) is None
