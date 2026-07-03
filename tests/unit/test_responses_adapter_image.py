"""Tests for the ``responses_to_chat_payload`` conversion of Codex
/responses function_call_output items that carry multimodal content
(image tool results).

The upstream bug: when Codex returns a ``function_call_output`` whose
``output`` is a list like
``[{"type": "input_image", "image_url": "data:image/jpeg;base64,..."}]``,
the prior adapter stringified the list via ``str(output)`` and shoved
the result into a ``role: "tool"`` chat message. Providers that map
``role: "tool"`` content to plain text then bill the entire base64
data URL as text tokens — ~40K tokens per 150 KB image. Six of them
overflowed the 272 K context window and crashed the supervisor.

Fix: detect the list case, put a short placeholder in the tool
message (so the tool_call_id pairing stays valid), and append a
follow-up ``role: "user"`` message whose content array uses proper
``image_url`` blocks. The provider's vision tokenizer then charges
per-image (a few tens to low-hundreds of tokens) instead of per-byte.
"""
from __future__ import annotations

import json

from lib.proxy import responses_to_chat_payload


def _tool_call(call_id: str) -> dict:
    return {
        "type": "function_call",
        "call_id": call_id,
        "name": "view_image",
        "arguments": json.dumps({"path": "x.jpg"}),
    }


def test_image_tool_result_is_not_stringified(dummy_data_url="data:image/jpeg;base64,ABCD") -> None:
    payload = {
        "model": "gpt-5.4",
        "input": [
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]},
            _tool_call("call_1"),
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": [{"type": "input_image", "image_url": dummy_data_url}],
            },
        ],
    }
    chat = responses_to_chat_payload(payload)
    messages = chat["messages"]
    # The tool message must not contain the raw data URL — otherwise the
    # provider will count the whole base64 string as text tokens.
    tool_messages = [m for m in messages if m.get("role") == "tool"]
    assert tool_messages, "function_call_output must produce a tool message"
    for tm in tool_messages:
        content = tm.get("content")
        assert isinstance(content, str)
        assert dummy_data_url not in content, (
            "tool message content must NOT include the raw data URL — that "
            "triggers per-byte text token billing"
        )


def test_image_tool_result_is_attached_via_user_turn(dummy_data_url="data:image/jpeg;base64,ABCD") -> None:
    """The image itself must end up in a role=user message as an
    ``image_url`` block so the provider's vision tokenizer handles it."""
    payload = {
        "model": "gpt-5.4",
        "input": [
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]},
            _tool_call("call_1"),
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": [{"type": "input_image", "image_url": dummy_data_url}],
            },
        ],
    }
    chat = responses_to_chat_payload(payload)
    messages = chat["messages"]
    # Find the user message that came AFTER the tool message and carries
    # the image_url block.
    tool_index = next(i for i, m in enumerate(messages) if m.get("role") == "tool")
    trailing = messages[tool_index + 1:]
    user_with_image = None
    for m in trailing:
        if m.get("role") == "user":
            content = m.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image_url":
                        if block.get("image_url", {}).get("url") == dummy_data_url:
                            user_with_image = m
                            break
        if user_with_image:
            break
    assert user_with_image is not None, (
        "image_url must be attached in a subsequent role=user message, not "
        "inlined into the tool message"
    )


def test_tool_call_id_pairing_survives_fix(dummy_data_url="data:image/jpeg;base64,ABCD") -> None:
    """The tool_call_id pairing (assistant.tool_calls[].id → tool.tool_call_id)
    must stay intact; otherwise /chat/completions rejects the request with
    ``invalid_tool_call_id``."""
    payload = {
        "model": "gpt-5.4",
        "input": [
            _tool_call("call_abc"),
            {
                "type": "function_call_output",
                "call_id": "call_abc",
                "output": [{"type": "input_image", "image_url": dummy_data_url}],
            },
        ],
    }
    chat = responses_to_chat_payload(payload)
    messages = chat["messages"]
    assistant = next(m for m in messages if m.get("role") == "assistant" and m.get("tool_calls"))
    tool = next(m for m in messages if m.get("role") == "tool")
    assert assistant["tool_calls"][0]["id"] == "call_abc"
    assert tool["tool_call_id"] == "call_abc"


def test_string_tool_output_is_unchanged() -> None:
    """Plain text tool outputs (exec_command, read, etc.) must still go
    straight into the tool message with no transformation. That path
    carried the majority of tool traffic before this fix and must keep
    working byte-identically."""
    payload = {
        "model": "gpt-5.4",
        "input": [
            _tool_call("call_1"),
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": "hello world",
            },
        ],
    }
    chat = responses_to_chat_payload(payload)
    tool = next(m for m in chat["messages"] if m.get("role") == "tool")
    assert tool["content"] == "hello world"
    # No stray user-role image-attachment message after the tool turn.
    tool_index = chat["messages"].index(tool)
    assert all(
        not isinstance(m.get("content"), list)
        or not any(
            isinstance(b, dict) and b.get("type") == "image_url"
            for b in m.get("content") or []
        )
        for m in chat["messages"][tool_index + 1:]
    )


def test_mixed_text_and_image_blocks_preserved() -> None:
    """If a tool result mixes text and image blocks, both end up in the
    follow-up user message and are not dropped."""
    payload = {
        "model": "gpt-5.4",
        "input": [
            _tool_call("call_1"),
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": [
                    {"type": "input_text", "text": "caption"},
                    {"type": "input_image", "image_url": "data:image/jpeg;base64,ABC"},
                ],
            },
        ],
    }
    chat = responses_to_chat_payload(payload)
    tool_index = next(i for i, m in enumerate(chat["messages"]) if m.get("role") == "tool")
    user_attached = chat["messages"][tool_index + 1]
    assert user_attached.get("role") == "user"
    content = user_attached["content"]
    assert isinstance(content, list)
    types = [b.get("type") for b in content if isinstance(b, dict)]
    assert "text" in types and "image_url" in types


def test_image_url_dict_form_is_accepted_too() -> None:
    """Codex also emits ``image_url`` as a dict ``{"url": ..., "detail": ...}``
    (native Responses shape). Both forms must route through correctly."""
    payload = {
        "model": "gpt-5.4",
        "input": [
            _tool_call("call_1"),
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": [{"type": "input_image", "image_url": {"url": "data:image/jpeg;base64,XX", "detail": "low"}}],
            },
        ],
    }
    chat = responses_to_chat_payload(payload)
    tool_index = next(i for i, m in enumerate(chat["messages"]) if m.get("role") == "tool")
    user_attached = chat["messages"][tool_index + 1]
    content = user_attached["content"]
    image_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "image_url"]
    assert image_blocks, "image_url dict form must still produce an image_url block"
    assert image_blocks[0]["image_url"]["url"] == "data:image/jpeg;base64,XX"
    # ``detail`` hint is preserved so callers can opt into cheap-token mode.
    assert image_blocks[0]["image_url"].get("detail") == "low"
