"""Tests for the ``tool_choice``/``tools`` coupling invariant in the
``responses_via_chat`` adapter and the shared ``sanitize_chat_payload``
helper.

Why it matters: Codex's auto-compact turn sends a request that strips
``tools`` but keeps ``tool_choice`` in the /responses payload. Several
OpenAI-compatible providers then reject the forwarded /chat/completions
request with:

    ``'tool_choice' is only allowed when 'tools' are specified``.

Codex re-tries 5 times, gives up, and the run fails with
``grader_transport_error`` — which we observed in the stress test at
``CLAWBENCH_CODEX_MODEL_AUTO_COMPACT_TOKEN_LIMIT=15000``.

The adapter now drops ``tool_choice`` whenever the outgoing /chat
payload has no tools. Regular calls (tools present) are unaffected.
"""
from __future__ import annotations

from lib.proxy import responses_to_chat_payload, sanitize_chat_payload


def test_tool_choice_dropped_when_tools_missing_in_responses_payload() -> None:
    payload = {
        "model": "gpt-5.4",
        "input": [
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "summarize"}]},
        ],
        "tool_choice": "auto",
        # no ``tools`` key at all — Codex auto-compact shape
    }
    chat = responses_to_chat_payload(payload)
    assert "tool_choice" not in chat, (
        "tool_choice must NOT be forwarded when tools are absent — upstream "
        "providers reject that combination"
    )


def test_tool_choice_dropped_when_tools_empty_list_in_responses_payload() -> None:
    payload = {
        "model": "gpt-5.4",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]}],
        "tool_choice": "none",
        "tools": [],
    }
    chat = responses_to_chat_payload(payload)
    assert "tool_choice" not in chat
    # Empty tools list should not be forwarded either — keeps the chat
    # payload minimal and aligned with what providers accept.
    assert "tools" not in chat or chat.get("tools")


def test_tool_choice_preserved_when_tools_present_in_responses_payload() -> None:
    payload = {
        "model": "gpt-5.4",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]}],
        "tool_choice": "auto",
        "tools": [
            {"type": "function", "name": "view_image", "parameters": {"type": "object", "properties": {}}},
        ],
    }
    chat = responses_to_chat_payload(payload)
    assert chat.get("tool_choice") == "auto"
    assert isinstance(chat.get("tools"), list) and chat["tools"]


def test_sanitize_chat_payload_strips_orphan_tool_choice() -> None:
    """The /chat/completions path (drop_max_tokens adapter, openclaw
    side) gets the same guard so the executor is protected too."""
    payload = {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "hi"}],
        "tool_choice": "auto",
    }
    sanitized, event = sanitize_chat_payload(payload)
    assert "tool_choice" not in sanitized
    # The fix is observable in the adapter event log so operators can
    # audit that the guard fired.
    assert "tool_choice" in (event.get("rewrote") or {})


def test_sanitize_chat_payload_keeps_tool_choice_with_tools() -> None:
    payload = {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "hi"}],
        "tool_choice": "auto",
        "tools": [{"type": "function", "function": {"name": "f", "parameters": {"type": "object"}}}],
    }
    sanitized, event = sanitize_chat_payload(payload)
    assert sanitized.get("tool_choice") == "auto"
    assert "tool_choice" not in (event.get("rewrote") or {})


def test_sanitize_chat_payload_ignores_empty_string_tool_choice() -> None:
    """Empty-string ``tool_choice`` is a no-op in the event log today;
    the guard must still not crash and must not inject ``tool_choice``
    into the outgoing payload."""
    payload = {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "hi"}],
        "tool_choice": "",
    }
    sanitized, event = sanitize_chat_payload(payload)
    # ``tool_choice`` was neither adopted (no tools) nor promoted — the
    # guard path leaves the original empty-string key alone. Providers
    # that reject empty strings can further sanitize; this adapter's
    # only job is to avoid injecting an orphan.
    assert sanitized.get("tool_choice", None) in (None, "")


def test_parallel_tool_calls_dropped_when_tools_missing() -> None:
    """Sibling of the ``tool_choice`` guard: Codex's auto-compact turn
    also keeps ``parallel_tool_calls`` after stripping ``tools``, and
    the upstream rejects the combo with the same shape of 400 error."""
    payload = {
        "model": "gpt-5.4",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]}],
        "parallel_tool_calls": False,
        # no ``tools`` key — auto-compact shape
    }
    chat = responses_to_chat_payload(payload)
    assert "parallel_tool_calls" not in chat


def test_parallel_tool_calls_preserved_when_tools_present() -> None:
    payload = {
        "model": "gpt-5.4",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]}],
        "parallel_tool_calls": False,
        "tools": [
            {"type": "function", "name": "f", "parameters": {"type": "object", "properties": {}}},
        ],
    }
    chat = responses_to_chat_payload(payload)
    assert chat.get("parallel_tool_calls") is False


def test_sanitize_chat_payload_strips_orphan_parallel_tool_calls() -> None:
    payload = {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "hi"}],
        "parallel_tool_calls": True,
    }
    sanitized, event = sanitize_chat_payload(payload)
    assert "parallel_tool_calls" not in sanitized
    assert "parallel_tool_calls" in (event.get("rewrote") or {})
