#!/usr/bin/env python3
'''Module-level mirror of the adapter's payload-transform helpers.

The adapter itself runs as a ``python3 -c <script>`` subprocess and
cannot ``import lib.proxy`` — the authoritative copies embedded inside
the ``script = r""" ... """`` string in ``adapter.start_proxy_adapter``
are what executes in production. The copies here exist purely so unit
tests can exercise ``responses_to_chat_payload`` / ``sanitize_chat_payload``
/ ``normalize_content`` / ``item_text`` without spinning up the
subprocess. Any fix applied here MUST be mirrored in the subprocess
script (and vice versa) — drift would silently reintroduce bugs like
the ``str(output)`` image-stringification one that motivated the split.
'''
from __future__ import annotations


def item_text(item) -> str:
    if not isinstance(item, dict):
        return ""
    for key in ("text", "input_text", "output_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    image_url = item.get("image_url")
    if isinstance(image_url, dict):
        url = str(image_url.get("url") or "").strip()
        if url:
            return url
    if isinstance(image_url, str) and image_url.strip():
        return image_url
    return ""


def normalize_content(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        text = str(content or "").strip()
        return text
    parts = []
    text_only = True
    for item in content:
        if not isinstance(item, dict):
            text = str(item or "").strip()
            if text:
                parts.append({"type": "text", "text": text})
            continue
        item_type = str(item.get("type") or "").strip()
        if item_type in {"text", "input_text", "output_text"}:
            text = item_text(item)
            if text:
                parts.append({"type": "text", "text": text})
        elif item_type in {"input_image", "image_url", "image"}:
            text_only = False
            image_url = item.get("image_url")
            if isinstance(image_url, dict):
                url = str(image_url.get("url") or "").strip()
            else:
                url = str(item.get("url") or image_url or "").strip()
            if url:
                parts.append({"type": "image_url", "image_url": {"url": url}})
        else:
            text = item_text(item)
            if text:
                parts.append({"type": "text", "text": text})
    if not parts:
        return ""
    if text_only:
        text = "\n".join(part.get("text") or "" for part in parts if isinstance(part, dict) and str(part.get("text") or "").strip()).strip()
        return text
    return parts


def responses_to_chat_payload(payload):
    chat_payload = {
        "model": payload.get("model"),
        "messages": [],
        "stream": False,
    }
    instructions = str(payload.get("instructions") or "").strip()
    if instructions:
        chat_payload["messages"].append({"role": "system", "content": instructions})
    input_items = payload.get("input")
    if isinstance(input_items, str):
        text = input_items.strip()
        if text:
            chat_payload["messages"].append({"role": "user", "content": text})
    elif isinstance(input_items, list):
        pending_tool_calls: list[dict] = []
        # Defer image follow-up user messages until the tool-response
        # batch for the current assistant turn is fully emitted — see
        # the detailed note in the subprocess-script copy above.
        pending_followups: list[dict] = []

        def _flush_followups():
            nonlocal pending_followups
            for u in pending_followups:
                chat_payload["messages"].append(u)
            pending_followups = []

        for item in input_items:
            if not isinstance(item, dict):
                text = str(item or "").strip()
                if text:
                    _flush_followups()
                    chat_payload["messages"].append({"role": "user", "content": text})
                continue
            item_type = str(item.get("type") or "").strip()
            role = str(item.get("role") or "user").strip() or "user"
            if role == "developer":
                role = "system"
            if item_type == "function_call":
                _flush_followups()
                pending_tool_calls.append({
                    "id": str(item.get("call_id") or item.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(item.get("name") or ""),
                        "arguments": str(item.get("arguments") or "{}"),
                    },
                })
            elif item_type == "function_call_output":
                if pending_tool_calls:
                    chat_payload["messages"].append({"role": "assistant", "content": None, "tool_calls": pending_tool_calls})
                    pending_tool_calls = []
                output = item.get("output")
                call_id = str(item.get("call_id") or "")
                if isinstance(output, str):
                    chat_payload["messages"].append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": output,
                    })
                elif isinstance(output, list):
                    followup_content: list[dict] = []
                    placeholder_parts: list[str] = []
                    for block in output:
                        if not isinstance(block, dict):
                            text = str(block or "").strip()
                            if text:
                                placeholder_parts.append(text)
                                followup_content.append({"type": "text", "text": text})
                            continue
                        block_type = str(block.get("type") or "").strip()
                        if block_type in {"input_image", "image_url", "image"}:
                            image_url_field = block.get("image_url")
                            if isinstance(image_url_field, dict):
                                url = str(image_url_field.get("url") or "").strip()
                                detail = image_url_field.get("detail")
                            else:
                                url = str(block.get("url") or image_url_field or "").strip()
                                detail = None
                            if url:
                                image_block = {"type": "image_url", "image_url": {"url": url}}
                                if isinstance(detail, str) and detail:
                                    image_block["image_url"]["detail"] = detail
                                followup_content.append(image_block)
                                placeholder_parts.append("[image]")
                        elif block_type in {"input_text", "output_text", "text"}:
                            text = item_text(block)
                            if text:
                                placeholder_parts.append(text)
                                followup_content.append({"type": "text", "text": text})
                        else:
                            text = item_text(block)
                            if text:
                                placeholder_parts.append(text)
                                followup_content.append({"type": "text", "text": text})
                    chat_payload["messages"].append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": (" ".join(placeholder_parts).strip()
                                    or "[tool result attached in the next turn]"),
                    })
                    if followup_content:
                        pending_followups.append({
                            "role": "user",
                            "content": followup_content,
                        })
                else:
                    chat_payload["messages"].append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": "",
                    })
            elif item_type in {"message", ""} or "content" in item:
                if pending_tool_calls:
                    chat_payload["messages"].append({"role": "assistant", "content": None, "tool_calls": pending_tool_calls})
                    pending_tool_calls = []
                _flush_followups()
                content = normalize_content(item.get("content"))
                if content:
                    chat_payload["messages"].append({"role": role, "content": content})
            elif item_type in {"input_text", "text"}:
                text = item_text(item).strip()
                if text:
                    _flush_followups()
                    chat_payload["messages"].append({"role": role, "content": text})
        if pending_tool_calls:
            chat_payload["messages"].append({"role": "assistant", "content": None, "tool_calls": pending_tool_calls})
        _flush_followups()
    max_output_tokens = payload.get("max_output_tokens")
    if max_output_tokens not in {None, ""}:
        chat_payload["max_tokens"] = max_output_tokens
    text_cfg = payload.get("text") if isinstance(payload.get("text"), dict) else {}
    format_cfg = text_cfg.get("format") if isinstance(text_cfg.get("format"), dict) else {}
    format_type = str(format_cfg.get("type") or "").strip()
    if format_type == "json_object":
        chat_payload["response_format"] = {"type": "json_object"}
    elif format_type == "json_schema":
        schema = format_cfg.get("schema") if isinstance(format_cfg.get("schema"), dict) else {}
        if schema:
            chat_payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": str(format_cfg.get("name") or "codex_response"),
                    "schema": schema,
                    "strict": bool(format_cfg.get("strict", True)),
                },
            }
    tools = payload.get("tools")
    if isinstance(tools, list) and tools:
        chat_tools = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            if "function" in tool and isinstance(tool["function"], dict):
                chat_tools.append(tool)
            elif "name" in tool:
                chat_tools.append({
                    "type": "function",
                    "function": {k: v for k, v in tool.items() if k in {"name", "description", "parameters", "strict"}},
                })
        if chat_tools:
            chat_payload["tools"] = chat_tools
    tool_choice = payload.get("tool_choice")
    # Mirror the ``tool_choice``/``parallel_tool_calls`` guards from
    # the /responses path: some providers reject these keys when
    # ``tools`` is absent/empty.
    if tool_choice is not None and chat_payload.get("tools"):
        chat_payload["tool_choice"] = tool_choice
    parallel_tool_calls = payload.get("parallel_tool_calls")
    if parallel_tool_calls is not None and chat_payload.get("tools"):
        chat_payload["parallel_tool_calls"] = parallel_tool_calls
    return chat_payload


def sanitize_chat_payload(payload):
    """Module-level mirror of the subprocess-side ``sanitize_chat_payload``.

    This exists only so unit tests can exercise the guard without
    starting the adapter subprocess. The authoritative copy lives
    inside the adapter script string above; any fix applied here MUST
    be mirrored there (and vice versa) — drift silently reintroduces
    the bugs each copy was added to prevent.
    """

    event = {"dropped": []}
    if not isinstance(payload, dict):
        return payload, event
    event["json_keys"] = sorted(payload.keys())
    if "max_tokens" in payload:
        event["max_tokens"] = payload.get("max_tokens")
    if "max_completion_tokens" in payload:
        event["max_completion_tokens"] = payload.get("max_completion_tokens")
    if "max_completion_tokens" in payload:
        if "max_tokens" not in payload:
            payload["max_tokens"] = payload.get("max_completion_tokens")
            event["rewrote"] = {"max_completion_tokens": "max_tokens"}
        payload.pop("max_completion_tokens", None)
        event["dropped"].append("max_completion_tokens")
    if bool(payload.get("stream")):
        existing_options = payload.get("stream_options")
        if isinstance(existing_options, dict):
            if not existing_options.get("include_usage"):
                existing_options["include_usage"] = True
                event.setdefault("rewrote", {})["stream_options.include_usage"] = "true"
        else:
            payload["stream_options"] = {"include_usage": True}
            event.setdefault("rewrote", {})["stream_options"] = '{"include_usage": true}'
    tool_choice = payload.get("tool_choice")
    if tool_choice not in {None, ""}:
        event["tool_choice"] = tool_choice
    # Guard: ``tool_choice`` and ``parallel_tool_calls`` are rejected
    # by several OpenAI-compatible providers when ``tools`` is absent
    # or empty. Drop the orphan keys silently rather than letting the
    # upstream 400 out — Codex's auto-compact hits both cases.
    has_tools = isinstance(payload.get("tools"), list) and bool(payload.get("tools"))
    if tool_choice is not None and not has_tools:
        payload.pop("tool_choice", None)
        event.setdefault("rewrote", {})["tool_choice"] = "dropped (no tools)"
    if "parallel_tool_calls" in payload and not has_tools:
        payload.pop("parallel_tool_calls", None)
        event.setdefault("rewrote", {})["parallel_tool_calls"] = "dropped (no tools)"
    return payload, event
