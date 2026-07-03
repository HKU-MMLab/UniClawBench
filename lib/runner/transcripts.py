"""Transcript parsing, normalization, and cross-agent merging.

Every backend (openclaw / nanobot / openclaw_edict) emits its own raw
transcript shape; this module converts them to a unified event-stream
form, strips embedded image base64 into ``inline_images/`` references,
and provides helpers to derive per-tool-call timing for the WebUI Gantt
view and to merge multiple per-agent transcripts into a single
wall-clock-ordered stream.

Pure data-in / data-out — no container access, no side effects other
than (optionally) writing ``tool_usage.json`` next to an attempt.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..proxy import write_local
from .media import (
    _data_from_image_url,
    _persist_inline_image,
    _strip_inline_image_base64,
    active_inline_images_dir,
)


def parse_json_lines(text: str) -> list[dict]:
    items = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def transcript_is_event_stream(items: list[dict]) -> bool:
    return any(isinstance(item, dict) and isinstance(item.get("type"), str) for item in items)


def _stable_transcript_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:06d}"


def _stringify_transcript_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _normalize_content_blocks(value: Any) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if isinstance(value, str):
        text = value.strip()
        if text:
            text = _strip_inline_image_base64(text)
            blocks.append({"type": "text", "text": text})
        return blocks
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                item_type = str(item.get("type") or "").strip().lower()
                if item_type in {"text", "input_text"}:
                    text = _stringify_transcript_value(item.get("text") or item.get("value")).strip()
                    if text:
                        # Some MCP servers (e.g. playwright-mcp) emit image
                        # payloads as Python-repr strings inside a text
                        # block instead of a proper image content block —
                        # extract those base64 blobs to inline_images/ so
                        # supervisor / user-simulator never read the raw
                        # base64 (just like real image blocks below).
                        text = _strip_inline_image_base64(text)
                        blocks.append({"type": "text", "text": text})
                    continue
                if item_type in {"image", "image_url", "input_image"}:
                    image_meta = item.get("_meta") or {}
                    label = (
                        image_meta.get("path")
                        or item.get("alt")
                        or item.get("label")
                        or item.get("name")
                        or "image"
                    )
                    # Try to persist embedded base64 payload to the
                    # attempt's ``inline_images/`` directory so the WebUI
                    # can render it. Fall back to the bare ``[image:
                    # <label>]`` text if there's no payload or no active
                    # output directory (e.g. normalization outside a
                    # ``collect_attempt_artifacts`` context).
                    data_b64 = item.get("data") or item.get("b64_json") or item.get("base64")
                    mime = (
                        item.get("mimeType")
                        or item.get("mime_type")
                        or item.get("media_type")
                        or "image/png"
                    )
                    if not data_b64:
                        embedded, embedded_mime = _data_from_image_url(item.get("image_url"))
                        if embedded:
                            data_b64 = embedded
                            mime = embedded_mime or mime
                    rel_path = _persist_inline_image(data_b64, mime, label=label)
                    text_label = rel_path if rel_path else label
                    blocks.append({"type": "text", "text": f"[image: {text_label}]"})
                    continue
            text = _stringify_transcript_value(item).strip()
            if text:
                text = _strip_inline_image_base64(text)
                blocks.append({"type": "text", "text": text})
        return blocks
    text = _stringify_transcript_value(value).strip()
    if text:
        text = _strip_inline_image_base64(text)
        blocks.append({"type": "text", "text": text})
    return blocks


def _normalize_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text}
        return parsed if isinstance(parsed, dict) else {"_raw": text}
    return {"_raw": _stringify_transcript_value(raw)}


def normalize_nanobot_session_transcript(text: str) -> str:
    records = parse_json_lines(text)
    if not records or transcript_is_event_stream(records):
        return text
    if not any(record.get("_type") == "metadata" or "role" in record for record in records):
        return text
    normalized: list[dict[str, Any]] = []
    event_index = 0
    for record in records:
        if not isinstance(record, dict) or record.get("_type") == "metadata":
            continue
        role = str(record.get("role") or "").strip()
        timestamp = str(record.get("timestamp") or "").strip()
        content = _normalize_content_blocks(record.get("content"))
        if role == "assistant":
            for call_index, raw_call in enumerate(record.get("tool_calls") or []):
                if not isinstance(raw_call, dict):
                    continue
                function = raw_call.get("function") if isinstance(raw_call.get("function"), dict) else {}
                name = str(raw_call.get("name") or function.get("name") or "").strip()
                if not name:
                    continue
                content.append(
                    {
                        "type": "toolCall",
                        "id": str(raw_call.get("id") or f"nanobot-call-{event_index:06d}-{call_index:02d}"),
                        "name": name,
                        "arguments": _normalize_tool_arguments(raw_call.get("arguments", function.get("arguments"))),
                    }
                )
            if not content:
                continue
            normalized.append(
                {
                    "type": "message",
                    "id": _stable_transcript_id("nanobot", event_index),
                    "timestamp": timestamp,
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "timestamp": timestamp,
                    },
                }
            )
            event_index += 1
            continue
        if role == "user":
            if not content:
                continue
            normalized.append(
                {
                    "type": "message",
                    "id": _stable_transcript_id("nanobot", event_index),
                    "timestamp": timestamp,
                    "message": {
                        "role": "user",
                        "content": content,
                        "timestamp": timestamp,
                    },
                }
            )
            event_index += 1
            continue
        if role == "tool":
            if not content:
                continue
            normalized.append(
                {
                    "type": "message",
                    "id": _stable_transcript_id("nanobot", event_index),
                    "timestamp": timestamp,
                    "message": {
                        "role": "toolResult",
                        "toolCallId": str(record.get("tool_call_id") or ""),
                        "toolName": str(record.get("name") or ""),
                        "content": content,
                        "timestamp": timestamp,
                    },
                }
            )
            event_index += 1
            continue
    if not normalized:
        return text
    return "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in normalized)


def _strip_image_blocks_from_event_records(records: list) -> tuple[list, int]:
    """Walk event-stream transcript records and replace any embedded image
    content block (``{"type": "image", "data": "<b64>", ...}``) with a text
    block referencing the persisted file under ``inline_images/``.

    Returns ``(new_records, replaced_count)``. When ``replaced_count == 0``
    the caller should leave the on-disk transcript alone — preserving any
    existing byte-for-byte shape (whitespace, key order) rather than
    round-tripping through json.dumps for a no-op.

    Used for openclaw / openclaw_edict / future backends whose raw
    transcript already arrives in event-stream form — unlike nanobot's
    legacy role-based transcript which goes through
    ``_normalize_content_blocks`` as part of the full role→event reshape.
    """
    counter = [0]

    def _is_image_block(node: dict) -> bool:
        t = str(node.get("type") or "").strip().lower()
        if t not in {"image", "image_url", "input_image"}:
            return False
        if node.get("data") or node.get("b64_json") or node.get("base64"):
            return True
        embedded, _ = _data_from_image_url(node.get("image_url"))
        return bool(embedded)

    def _rewrite(node: Any) -> Any:
        if isinstance(node, dict):
            if _is_image_block(node):
                data_b64 = node.get("data") or node.get("b64_json") or node.get("base64")
                default_mime = None
                if not data_b64:
                    embedded, embedded_mime = _data_from_image_url(node.get("image_url"))
                    data_b64 = embedded or ""
                    default_mime = embedded_mime
                mime = (
                    node.get("mimeType")
                    or node.get("mime_type")
                    or node.get("media_type")
                    or default_mime
                    or "image/png"
                )
                image_meta = node.get("_meta") or {}
                label = (
                    image_meta.get("path")
                    or node.get("alt")
                    or node.get("label")
                    or node.get("name")
                    or "image"
                )
                rel = _persist_inline_image(data_b64, mime, label=label) if data_b64 else None
                text_label = rel if rel else label
                counter[0] += 1
                return {"type": "text", "text": f"[image: {text_label}]"}
            return {k: _rewrite(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_rewrite(v) for v in node]
        return node

    new_records = [_rewrite(r) for r in records]
    return new_records, counter[0]


def normalize_transcript_text(text: str) -> str:
    records = parse_json_lines(text)
    if not records:
        return text
    if transcript_is_event_stream(records):
        # Preserve the event-stream shape, but still replace any embedded
        # image content blocks with inline_images/ references so the
        # supervisor / user-simulator ``visible/transcript.jsonl`` copies
        # stay slim. nanobot's playwright-mcp path already produces stripped
        # transcripts upstream (base64 arrives truncated in text form) —
        # this branch is mainly for openclaw / openclaw_edict whose native
        # browser tool returns proper ``{"type":"image","data":"<b64>"}``
        # blocks.
        if active_inline_images_dir() is None:
            return text
        rewritten, replaced = _strip_image_blocks_from_event_records(records)
        if replaced == 0:
            return text
        return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rewritten)
    if any(record.get("_type") == "metadata" or "role" in record for record in records):
        return normalize_nanobot_session_transcript(text)
    return text


def build_tool_usage_summary(transcript_text: str) -> dict[str, Any]:
    transcript_text = normalize_transcript_text(transcript_text)
    tool_names: list[str] = []
    tool_calls: list[dict] = []
    browser_actions: list[str] = []
    for payload in parse_json_lines(transcript_text):
        if payload.get("type") != "message":
            continue
        message = payload.get("message") or {}
        if message.get("role") != "assistant":
            continue
        for item in message.get("content", []):
            if item.get("type") != "toolCall":
                continue
            name = str(item.get("name", ""))
            tool_names.append(name)
            if name == "browser" and isinstance(item.get("arguments"), dict):
                action = item["arguments"].get("action")
                if isinstance(action, str):
                    browser_actions.append(action)
            tool_calls.append(
                {
                    "agentId": str(payload.get("agentId") or ""),
                    "name": name,
                    "arguments": item.get("arguments", {}),
                    "timestamp": payload.get("timestamp"),
                }
            )
    return {
        "tool_names": tool_names,
        "tool_counts": {name: tool_names.count(name) for name in sorted(set(tool_names))},
        "browser_actions": browser_actions,
        "browser_action_counts": {name: browser_actions.count(name) for name in sorted(set(browser_actions))},
        "browser_used": "browser" in tool_names,
        "exec_used": "exec" in tool_names,
        "tool_calls": tool_calls,
    }


def summarize_transcript_tools(transcript_text: str, out_dir: Path) -> None:
    summary = build_tool_usage_summary(transcript_text)
    write_local(out_dir / "tool_usage.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


def reconstruct_tool_spans(
    transcript_text: str,
    window: tuple[float, float],
) -> list[dict[str, Any]]:
    """Derive per tool-call timing from a (possibly multi-agent-merged)
    transcript.

    The underlying agent CLIs (openclaw / nanobot / openclaw_edict) only
    emit a single ``timestamp`` per event, pinned at message-complete time.
    So we approximate each tool-call's wall-clock span as ``(prev_ts, ts)``
    where ``ts`` is the toolCall's completion stamp and ``prev_ts`` is the
    previous event timestamp in the same cycle (falls back to the cycle's
    own start). The first span inside each cycle gets ``approximate=True``
    because its ``prev_ts`` includes LLM thinking + tool wall-time.

    ``window`` is ``(cycle_started_s, cycle_ended_s)`` — events outside it
    (e.g. from a previous cycle that landed in the same transcript) are
    ignored.
    """
    start_s, end_s = float(window[0]), float(window[1])
    events: list[tuple[float, dict]] = []
    for payload in parse_json_lines(normalize_transcript_text(transcript_text)):
        if not isinstance(payload, dict):
            continue
        ts = transcript_event_timestamp(payload)
        if not ts:
            continue
        if ts < start_s or ts > end_s + 0.5:
            continue
        events.append((ts, payload))
    events.sort(key=lambda x: x[0])
    spans: list[dict[str, Any]] = []
    prev_ts = start_s
    is_first = True
    for ts, payload in events:
        if payload.get("type") != "message":
            prev_ts = ts
            continue
        message = payload.get("message") or {}
        agent_id = str(payload.get("agentId") or message.get("agentId") or "main")
        for item in (message.get("content") or []):
            if not isinstance(item, dict):
                continue
            if item.get("type") == "toolCall":
                spans.append({
                    "kind": "tool_call",
                    "name": str(item.get("name") or "unknown"),
                    "agent_id": agent_id,
                    "start_ms": int(prev_ts * 1000),
                    "end_ms": int(ts * 1000),
                    "approximate": is_first,
                })
                is_first = False
        prev_ts = ts
    return spans


def _parse_iso_to_epoch(text: str) -> float:
    """Parse an ISO-8601 timestamp into epoch seconds.

    Handles ``...Z`` suffixes (converts to ``+00:00``) and — importantly —
    treats timestamps that parse to a naive datetime as **UTC** rather than
    local time. Nanobot writes timestamps like ``2026-04-15T12:33:50.945111``
    (no timezone marker, but they're UTC); ``datetime.fromisoformat`` returns
    a naive datetime in that case, and ``.timestamp()`` would otherwise
    default to local time, offsetting every nanobot event by the host's UTC
    offset (+8h on Asia/Shanghai). That broke ``reconstruct_tool_spans``'s
    window filter — all events were rejected as "outside the cycle window",
    leading to empty ``tool_calls`` on the Gantt panel.
    """
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def transcript_event_timestamp(payload: dict) -> float:
    raw = payload.get("timestamp")
    if isinstance(raw, (int, float)):
        numeric = float(raw)
        return numeric / 1000.0 if numeric > 10**12 else numeric
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        return _parse_iso_to_epoch(text)
    message = payload.get("message") or {}
    raw_message = message.get("timestamp")
    if isinstance(raw_message, str):
        return _parse_iso_to_epoch(raw_message.strip())
    return 0.0


def annotate_transcript_with_agent(text: str, agent_id: str) -> str:
    lines: list[str] = []
    for payload in parse_json_lines(text):
        if not isinstance(payload, dict):
            continue
        enriched = json.loads(json.dumps(payload, ensure_ascii=False))
        enriched.setdefault("agentId", agent_id)
        lines.append(json.dumps(enriched, ensure_ascii=False))
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def merge_agent_transcripts(transcripts: list[tuple[str, str]]) -> str:
    merged: list[tuple[float, int, int, str]] = []
    for agent_order, (agent_id, text) in enumerate(transcripts):
        annotated = annotate_transcript_with_agent(text, agent_id)
        if not annotated.strip():
            continue
        for line_index, payload in enumerate(parse_json_lines(annotated)):
            if not isinstance(payload, dict):
                continue
            merged.append(
                (
                    transcript_event_timestamp(payload),
                    agent_order,
                    line_index,
                    json.dumps(payload, ensure_ascii=False),
                )
            )
    if not merged:
        return ""
    merged.sort(key=lambda item: (item[0], item[1], item[2]))
    return "\n".join(item[3] for item in merged) + "\n"


def load_tool_usage_file(out_dir: Path) -> dict:
    tool_path = out_dir / "tool_usage.json"
    if not tool_path.exists():
        return {}
    try:
        return json.loads(tool_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
