"""Regression tests for the tool_call pairing invariant when a single
assistant turn emits multiple parallel tool_calls and more than one of
the resulting ``function_call_output`` items carries an image.

Stress test wave-1 reproduced this on provider_primary/aws.claude-opus-4.6
and provider_pool/gemini-3.1-pro-preview: the supervisor (Codex) sent
payloads where the 5 parallel view_image tool_calls produced 5
``function_call_output`` items, 4 of them with image-list output. The
earlier adapter emitted each image's follow-up ``role: "user"`` message
**immediately after** that tool's response, interleaving tool and user
messages inside a single tool_calls batch. The provider then rejected
the request with::

    An assistant message with 'tool_calls' must be followed by tool
    messages responding to each 'tool_call_id'. The following
    tool_call_ids did not have response messages: <N-1 ids>

because the validator stopped counting tool responses at the first
non-tool role. The supervisor reconnected 5 times, gave up, and the run
ended as ``infra_error / grader_transport_error``.

The fix defers image follow-up user messages until the current tool
batch is fully responded, then emits them in order at the next turn
boundary. These tests pin the invariant.
"""
from __future__ import annotations

from lib.proxy import responses_to_chat_payload


def _fc(call_id: str, name: str = "view_image") -> dict:
    return {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": "{}",
    }


def _fc_out_image(call_id: str, tag: str) -> dict:
    return {
        "type": "function_call_output",
        "call_id": call_id,
        "output": [
            {
                "type": "input_image",
                "image_url": {"url": f"data:image/jpeg;base64,AAAA#{tag}"},
            }
        ],
    }


def _fc_out_text(call_id: str, text: str) -> dict:
    return {
        "type": "function_call_output",
        "call_id": call_id,
        "output": text,
    }


def _assistant_idx(messages):
    for i, m in enumerate(messages):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            return i
    raise AssertionError("no assistant tool_calls message")


def test_batch_with_all_image_outputs_preserves_pairing() -> None:
    """5 parallel fcs + 5 image fc_outs — the exact opus/gemini shape."""
    ids = [f"call_{k}" for k in "ABCDE"]
    payload = {
        "model": "gpt-5.4",
        "input": [
            *(_fc(cid) for cid in ids),
            *(_fc_out_image(cid, f"img_{cid}") for cid in ids),
        ],
    }
    messages = responses_to_chat_payload(payload)["messages"]
    a = _assistant_idx(messages)
    # Every tool_call id in the assistant message must map to one of the
    # N consecutive tool messages that follow it. No user/assistant
    # message is allowed in between.
    assert [tc["id"] for tc in messages[a]["tool_calls"]] == ids
    for j, cid in enumerate(ids, start=1):
        m = messages[a + j]
        assert m.get("role") == "tool", (
            f"message [{a+j}] must be tool, got role={m.get('role')} "
            f"(a user msg here is the exact bug that 400'd the supervisor)"
        )
        assert m.get("tool_call_id") == cid
    # All 5 image follow-ups should come AFTER the tool batch, still
    # in original order.
    followups = [m for m in messages[a + 1 + len(ids):] if m.get("role") == "user"]
    assert len(followups) == len(ids)
    for u, cid in zip(followups, ids):
        # Each follow-up should carry at least one image_url block and
        # reference the matching image url tag.
        parts = u.get("content") or []
        assert any(isinstance(p, dict) and p.get("type") == "image_url" for p in parts)
        url = next(p["image_url"]["url"] for p in parts if p.get("type") == "image_url")
        assert cid in url


def test_batch_mixing_text_and_image_outputs_preserves_pairing() -> None:
    """First fc_out is text (str), remaining four are images — mirrors
    the opus rollout exactly ([42] str; [43-46] images)."""
    ids = ["call_FCc", "call_2JG", "call_GWB", "call_ZDF", "call_aYp"]
    inputs = [_fc(cid) for cid in ids]
    inputs.append(_fc_out_text(ids[0], "plain text result"))
    inputs.extend(_fc_out_image(cid, cid) for cid in ids[1:])

    messages = responses_to_chat_payload({"model": "gpt-5.4", "input": inputs})["messages"]
    a = _assistant_idx(messages)
    # All 5 tool messages must come back-to-back, in request order,
    # with NO user message between them.
    for j, cid in enumerate(ids, start=1):
        m = messages[a + j]
        assert m.get("role") == "tool" and m.get("tool_call_id") == cid, (
            f"[{a+j}] broke pairing: {m}"
        )
    # The 4 image follow-ups land after tool[5].
    followups = messages[a + 1 + len(ids):]
    user_count = sum(1 for u in followups if u.get("role") == "user")
    assert user_count == 4


def test_multiple_batches_in_one_input_keep_pairing_each() -> None:
    """Batch 1: 2 fcs / 2 images. Then a second assistant turn: 3 fcs / 3 images."""
    b1 = ["call_1a", "call_1b"]
    b2 = ["call_2a", "call_2b", "call_2c"]

    inputs = []
    inputs.extend(_fc(cid) for cid in b1)
    inputs.extend(_fc_out_image(cid, cid) for cid in b1)
    inputs.extend(_fc(cid) for cid in b2)
    inputs.extend(_fc_out_image(cid, cid) for cid in b2)

    messages = responses_to_chat_payload({"model": "gpt-5.4", "input": inputs})["messages"]

    # Find both assistant+tool_calls messages.
    assistant_positions = [i for i, m in enumerate(messages)
                           if m.get("role") == "assistant" and m.get("tool_calls")]
    assert len(assistant_positions) == 2

    # Verify pairing for each batch.
    for a, ids in zip(assistant_positions, (b1, b2)):
        for j, cid in enumerate(ids, start=1):
            m = messages[a + j]
            assert m.get("role") == "tool" and m.get("tool_call_id") == cid


def test_final_batch_followups_emitted_at_end_of_input() -> None:
    """When input ends with an image-bearing tool output and there's no
    further turn, the follow-up user msg must still be flushed (not
    lost)."""
    ids = ["call_only_a", "call_only_b"]
    inputs = [_fc(cid) for cid in ids]
    inputs.extend(_fc_out_image(cid, cid) for cid in ids)

    messages = responses_to_chat_payload({"model": "gpt-5.4", "input": inputs})["messages"]
    a = _assistant_idx(messages)
    # Both tool msgs must be consecutive after the assistant.
    assert messages[a + 1]["role"] == "tool"
    assert messages[a + 2]["role"] == "tool"
    # Followups come after, in order. Neither should be dropped.
    tail = messages[a + 3:]
    user_tail = [m for m in tail if m.get("role") == "user"]
    assert len(user_tail) == 2
    # Order preserved.
    for u, cid in zip(user_tail, ids):
        url = next(p["image_url"]["url"] for p in u["content"] if p.get("type") == "image_url")
        assert cid in url


def test_followup_flushed_before_next_user_message_item() -> None:
    """If the /responses input ends a tool batch and then includes a
    plain user ``message`` item, the queued image follow-ups must be
    emitted BEFORE the new user message to keep transcript order."""
    ids = ["call_x", "call_y"]
    inputs = [_fc(cid) for cid in ids]
    inputs.extend(_fc_out_image(cid, cid) for cid in ids)
    inputs.append({
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "please continue"}],
    })

    messages = responses_to_chat_payload({"model": "gpt-5.4", "input": inputs})["messages"]
    # Expected tail: assistant tc, tool, tool, user(img_x), user(img_y), user("please continue")
    roles = [m.get("role") for m in messages[-6:]]
    assert roles == ["assistant", "tool", "tool", "user", "user", "user"]
    # The "please continue" user message is LAST, after the image follow-ups.
    last_user = messages[-1]
    if isinstance(last_user.get("content"), list):
        assert any(p.get("type") == "text" and "please continue" in (p.get("text") or "")
                   for p in last_user["content"])
    else:
        assert "please continue" in (last_user.get("content") or "")


def test_tool_message_content_carries_placeholder_not_base64() -> None:
    """Sanity: the tool message content stays short (doesn't inline the
    base64 blob that the vision tokenizer would otherwise bill at
    bytes/4 text tokens)."""
    ids = ["call_p"]
    messages = responses_to_chat_payload({
        "model": "gpt-5.4",
        "input": [_fc(ids[0]), _fc_out_image(ids[0], "PPP")],
    })["messages"]
    tool_msg = next(m for m in messages if m.get("role") == "tool")
    assert "AAAA" not in (tool_msg.get("content") or "")
    assert tool_msg.get("content") in {"[image]", "[tool result attached in the next turn]"}
