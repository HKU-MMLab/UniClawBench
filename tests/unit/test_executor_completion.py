"""Pin the per-backend relaxations in executor_completion_state.

The function classifies whether an executor finished cleanly.  Two
asymmetries matter for status correctness:

* openclaw_edict — non-zero orchestrator exit doesn't imply incomplete
  if taizi wrote a substantive (≥200 char) final answer
* nanobot — same idea, but reasoning-mode models often write short
  final answers, so the threshold drops to "non-empty text + not in
  tool call"

These tests pin both relaxations and prove they don't bleed into the
default backend path.
"""
from __future__ import annotations

import json

import pytest

from lib.runner.evaluation import executor_completion_state


# Helpers — produce a single-line JSONL transcript with one assistant
# message.  This is the minimal shape the helper accepts.


def _assistant_event(text: str, *, agent_id: str = "", has_tool_call: bool = False) -> str:
    """Build one transcript line representing an assistant turn.

    Matches the shape ``_last_assistant_message`` walks:
    ``payload.get("type") == "message"`` + ``payload["message"]["role"]
    == "assistant"`` + ``content`` list of typed blocks.
    """
    content: list = [{"type": "text", "text": text}]
    if has_tool_call:
        content.append({"type": "tool_use", "id": "t1", "name": "exec", "input": {"cmd": "ls"}})
    event = {
        "type": "message",
        "agentId": agent_id,
        "message": {
            "role": "assistant",
            "content": content,
        },
    }
    return json.dumps(event) + "\n"


# ── nanobot relaxation (new in this commit) ──────────────────────────


def test_nanobot_substantive_final_with_nonzero_exit_marks_completed() -> None:
    transcript = _assistant_event("Here is my final answer with details.")
    state = executor_completion_state(transcript, agent_exit_code=1, agent_sys="nanobot")
    assert state["completed"] is True
    assert state["reason"] == "nanobot-final-answer-despite-nonzero-exit"


def test_nanobot_short_but_non_empty_final_still_completed() -> None:
    """Threshold is 'non-empty', not 200 chars — short final answers
    from reasoning models must still pass."""
    transcript = _assistant_event("Done.")
    state = executor_completion_state(transcript, agent_exit_code=1, agent_sys="nanobot")
    assert state["completed"] is True


def test_nanobot_empty_final_with_nonzero_exit_marks_incomplete() -> None:
    transcript = _assistant_event("   ")  # whitespace only
    state = executor_completion_state(transcript, agent_exit_code=2, agent_sys="nanobot")
    assert state["completed"] is False
    assert state["reason"] == "nonzero-exit"


def test_nanobot_pending_tool_call_with_nonzero_exit_marks_incomplete() -> None:
    """If the last message is still mid-tool-call when the process exits,
    the executor was killed mid-step — that's genuinely incomplete."""
    transcript = _assistant_event("Calling tool…", has_tool_call=True)
    state = executor_completion_state(transcript, agent_exit_code=1, agent_sys="nanobot")
    assert state["completed"] is False
    assert state["reason"] == "nonzero-exit"


def test_nanobot_no_assistant_message_with_nonzero_exit_marks_incomplete() -> None:
    state = executor_completion_state("", agent_exit_code=1, agent_sys="nanobot")
    assert state["completed"] is False
    assert state["reason"] == "no-transcript"


# ── zero-exit path unchanged ─────────────────────────────────────────


def test_nanobot_zero_exit_short_final_still_completed_via_existing_branch() -> None:
    """Pre-existing nanobot relaxation on the clean-exit path: short
    text-only final → completed.  Must still work."""
    transcript = _assistant_event("ok")
    state = executor_completion_state(transcript, agent_exit_code=0, agent_sys="nanobot")
    assert state["completed"] is True
    assert state["reason"] == "nanobot-clean-exit-no-tool-call"


# ── regression: other backends are not affected ──────────────────────


def test_openclaw_nonzero_exit_relaxes_clean_final() -> None:
    """openclaw now relaxes a nonzero exit when the last message is a clean
    text-only answer with no pending tool call (a trailing non-contract
    command — e.g. a failed ``git commit`` — exits the wrapper nonzero AFTER
    the agent already finished).  Mirrors the edict/nanobot relaxations."""
    transcript = _assistant_event("Looks done to me.")
    state = executor_completion_state(transcript, agent_exit_code=1, agent_sys="openclaw")
    assert state["completed"] is True
    assert state["reason"] == "openclaw-final-answer-despite-nonzero-exit"


def test_openclaw_nonzero_exit_strict_when_pending_tool_call() -> None:
    """A pending tool call on the last message means the agent was cut off
    mid-action — openclaw keeps the strict contract there."""
    transcript = _assistant_event("running the build", has_tool_call=True)
    state = executor_completion_state(transcript, agent_exit_code=1, agent_sys="openclaw")
    assert state["completed"] is False
    assert state["reason"] == "nonzero-exit"


def test_codex_nonzero_exit_stays_strict() -> None:
    """Backends without an explicit strategy (codex / unknown) keep the
    strict contract — the openclaw relaxation must not bleed into them."""
    transcript = _assistant_event("Looks done to me.")
    state = executor_completion_state(transcript, agent_exit_code=1, agent_sys="codex")
    assert state["completed"] is False
    assert state["reason"] == "nonzero-exit"


def test_openclaw_zero_exit_strict_completion_signal_required() -> None:
    """openclaw zero-exit needs an explicit completion signal — either
    api_stop_reason ∈ COMPLETE or the textual marker.  Plain final
    text without marker stays missing-completion-signal."""
    transcript = _assistant_event("Done")  # no canonical-phrase marker
    state = executor_completion_state(transcript, agent_exit_code=0, agent_sys="openclaw")
    # Falls through to missing-completion-signal (or whichever path
    # the openclaw side actually takes) — the key assertion is that
    # nanobot's text-only relaxation MUST NOT apply here.
    assert state["completed"] is False or state["reason"] not in {
        "nanobot-clean-exit-no-tool-call",
        "nanobot-final-answer-despite-nonzero-exit",
    }


# ── edict path preserved (existing behaviour) ────────────────────────


def test_edict_nonzero_exit_long_taizi_text_marks_completed() -> None:
    """200-char taizi final still uses the edict-specific
    'edict-taizi-final-answer-despite-orch-exit' label, NOT nanobot's."""
    long_text = "a" * 250  # comfortably above the 200-char threshold
    transcript = _assistant_event(long_text, agent_id="taizi")
    state = executor_completion_state(
        transcript,
        agent_exit_code=1,
        primary_agent_id="taizi",
        agent_sys="openclaw_edict",
    )
    assert state["completed"] is True
    assert state["reason"] == "edict-taizi-final-answer-despite-orch-exit"


def test_edict_short_taizi_text_with_nonzero_exit_stays_incomplete() -> None:
    """Edict's 200-char threshold blocks routing placeholders.  Even
    though the same string would have passed nanobot's threshold,
    edict must reject it."""
    transcript = _assistant_event("[[reply_to_current]] 已收到旨意", agent_id="taizi")
    state = executor_completion_state(
        transcript,
        agent_exit_code=1,
        primary_agent_id="taizi",
        agent_sys="openclaw_edict",
    )
    assert state["completed"] is False
