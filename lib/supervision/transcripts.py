"""Transcript parsing, handoff summarisation, tool-call trace rollup.

Each supervisor role sees a compact digest of the executor's transcript
— semantic blocks (user/assistant/tool-result), a recent tool-call
history, and (for multi-agent EDICT runs) per-agent session summaries.
The helpers here produce those digests from the on-disk
``transcript.jsonl`` / ``tool_usage.json`` artifacts.

Dependencies are kept leaf-ward: stdlib + ``.contexts`` (dataclasses) +
``.files`` (read_text / read_json / _trim_middle /
sanitize_codex_context_text). Nothing in this module imports from
``.payloads`` / ``.images`` / ``.workspace``.

``EDICT_AGENT_LABELS`` lives here because the two agent-summary builders
are its only supervision-side consumer; ``common.py`` re-exports it for
the shim path used by ``lib.runner.edict`` / ``lib.runner.artifacts``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import SupervisorContext
from .content import (
    _trim_middle,
    read_json,
    read_text,
    sanitize_codex_context_text,
)


EDICT_AGENT_LABELS = {
    "taizi": "太子",
    "zhongshu": "中书省",
    "menxia": "门下省",
    "shangshu": "尚书省",
    "libu": "礼部",
    "hubu": "户部",
    "bingbu": "兵部",
    "xingbu": "刑部",
    "gongbu": "工部",
    "libu_hr": "吏部",
    "zaochao": "钦天监",
}


def _clip_block_list_middle(items: list[dict[str, Any]], max_total_chars: int) -> list[dict[str, Any]]:
    if max_total_chars <= 0:
        return []
    serialized = [json.dumps(item, ensure_ascii=False) for item in items]
    if sum(len(item) for item in serialized) <= max_total_chars:
        return items
    head: list[dict[str, Any]] = []
    tail: list[dict[str, Any]] = []
    budget = max_total_chars
    left = 0
    right = len(items) - 1
    take_head = True
    while left <= right and budget > 0:
        index = left if take_head else right
        item = items[index]
        item_len = len(serialized[index])
        if item_len > budget and (head or tail):
            break
        if take_head:
            head.append(item)
            left += 1
        else:
            tail.append(item)
            right -= 1
        budget -= item_len
        take_head = not take_head
    omitted = max(0, len(items) - len(head) - len(tail))
    clipped = list(head)
    if omitted:
        clipped.append(
            {
                "kind": "omitted",
                "text": f"... omitted {omitted} transcript blocks ...",
            }
        )
    clipped.extend(reversed(tail))
    return clipped


def _timestamp_label(raw: Any) -> str:
    value = str(raw or "").strip()
    if "T" in value:
        value = value.split("T", 1)[1]
    value = value.replace("Z", "")
    return value[:8] if len(value) >= 8 else value


def _content_text(items: Any, *, max_chars: int = 2400) -> str:
    if not isinstance(items, list):
        return _trim_middle(sanitize_codex_context_text(str(items or "").strip()), max_chars)
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "").strip()
        if item_type in {"text", "input_text"}:
            text = sanitize_codex_context_text(str(item.get("text") or item.get("input_text") or "").strip())
            if text:
                parts.append(text)
        elif item_type in {"input_image", "image_url", "image"}:
            parts.append("[image]")
    return _trim_middle("\n\n".join(parts).strip(), max_chars)


def _jsonish_text_preview(text: str) -> str:
    value = sanitize_codex_context_text(str(text or "").strip())
    if not value:
        return ""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, dict):
        status = str(parsed.get("status") or "").strip()
        error = sanitize_codex_context_text(str(parsed.get("error") or "").strip())
        text_value = sanitize_codex_context_text(str(parsed.get("text") or "").strip())
        if error:
            return error
        if text_value:
            return text_value
        if status:
            return f"status={status}"
    return value


def _is_noisy_tool_name(name: str) -> bool:
    return name in {
        "browser",
        "gateway",
        "sessions_send",
        "sessions_spawn",
        "subagents",
    }


def semantic_transcript_blocks(path: Path, *, max_blocks: int = 18, max_chars: int = 12000, max_block_chars: int = 2400) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for raw_line in read_text(path).splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if str(event.get("type") or "").strip() != "message":
            continue
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        role = str(message.get("role") or "").strip()
        timestamp = _timestamp_label(event.get("timestamp") or message.get("timestamp"))
        agent_id = str(event.get("agentId") or message.get("agentId") or "").strip()
        if role == "user":
            text = _content_text(message.get("content"), max_chars=max_block_chars)
            if not text:
                continue
            block: dict[str, str] = {"kind": "user_message", "timestamp": timestamp, "text": text}
            if agent_id:
                block["agent_id"] = agent_id
            blocks.append(block)
            continue
        if role == "assistant":
            error_message = sanitize_codex_context_text(str(message.get("errorMessage") or event.get("errorMessage") or "").strip())
            if error_message:
                block = {"kind": "assistant_error", "timestamp": timestamp, "text": _trim_middle(error_message, max_block_chars)}
                if agent_id:
                    block["agent_id"] = agent_id
                blocks.append(block)
                continue
            stop_reason = str(message.get("stopReason") or event.get("stopReason") or "").strip()
            if stop_reason == "toolUse":
                continue
            text = _content_text(message.get("content"), max_chars=max_block_chars)
            if not text:
                continue
            block = {"kind": "assistant_text", "timestamp": timestamp, "text": text}
            if agent_id:
                block["agent_id"] = agent_id
            blocks.append(block)
            continue
        if role == "toolResult":
            tool_name = str(message.get("toolName") or "").strip()
            details = message.get("details") if isinstance(message.get("details"), dict) else {}
            error_text = sanitize_codex_context_text(str(details.get("error") or "").strip())
            if error_text:
                block = {
                    "kind": "tool_error",
                    "timestamp": timestamp,
                    "tool": tool_name,
                    "text": _trim_middle(error_text, max_block_chars),
                }
                if agent_id:
                    block["agent_id"] = agent_id
                blocks.append(block)
                continue
            raw_text = _content_text(message.get("content"), max_chars=max_block_chars * 2)
            text = _trim_middle(_jsonish_text_preview(raw_text), max_block_chars)
            if not text or _is_noisy_tool_name(tool_name):
                continue
            block = {
                "kind": "tool_text",
                "timestamp": timestamp,
                "tool": tool_name,
                "text": text,
            }
            if agent_id:
                block["agent_id"] = agent_id
            blocks.append(block)
    # Round 9 / A5 — error-priority retention.
    #
    # Pre-fix this kept a fixed head (~6 blocks) + tail (~11 blocks)
    # and dropped the middle.  Mid-run failures (tool_error, fallback,
    # rate_limit, infra_error) often sit in the middle and were
    # silently dropped — supervisor saw an empty plan + final "all
    # done" summary and graded freely without knowing the run crashed
    # in the middle.
    #
    # Round 9 always preserves:
    #   - every ``assistant_error`` / ``tool_error`` block
    #   - every block whose text contains a failure keyword (fail,
    #     error, timeout, rate limit, infra, pre_exec, fallback,
    #     exception, traceback)
    #   - the last 5 blocks (executor's final conclusion + supervisor
    #     handoff context)
    # The remaining budget is filled head→tail in time order.  When
    # budget is exhausted, the omitted marker carries structured info
    # (omitted_count, omitted_block_range, omitted_event_range,
    # transcript_full_chunk_hint) so the supervisor can navigate to the
    # full chunk on disk.
    total_blocks = len(blocks)
    if total_blocks > max_blocks:
        blocks = _retain_error_priority(blocks, max_blocks=max_blocks)
    return _clip_block_list_middle(blocks, max_chars)


_FAILURE_KEYWORDS = (
    "fail", "failed", "error", "timeout", "rate limit", "rate_limit",
    "infra", "pre_exec", "pre-exec", "fallback", "exception", "traceback",
)


def _block_has_failure_signal(block: dict[str, str]) -> bool:
    """True if the block's kind or text suggests a mid-run failure
    that supervisor must not miss when scoring."""
    kind = (block.get("kind") or "").lower()
    if kind in ("assistant_error", "tool_error"):
        return True
    text = (block.get("text") or "").lower()
    return any(needle in text for needle in _FAILURE_KEYWORDS)


def _retain_error_priority(
    blocks: list[dict[str, str]], *, max_blocks: int,
) -> list[dict[str, str]]:
    """Reduce ``blocks`` to ≤ ``max_blocks`` rows while ALWAYS keeping
    failure-signal blocks and the final tail.

    Strategy:
      1. Identify the set of must-keep indices: every failure block
         AND the last 5 blocks.
      2. If must-keep already exceeds budget, return the must-keep set
         in time order (no head/tail filler).
      3. Otherwise budget the remainder (max_blocks - len(must_keep))
         to extra leading blocks for "what was the plan / setup".
      4. Insert a structured omitted marker wherever a contiguous
         range of original-indices got dropped.
    """
    total = len(blocks)
    tail_window = min(5, total)
    error_indices = {
        i for i, b in enumerate(blocks) if _block_has_failure_signal(b)
    }
    tail_indices = {i for i in range(total - tail_window, total) if i >= 0}
    must_keep = error_indices | tail_indices

    if len(must_keep) >= max_blocks:
        # Budget tight.  Failure-signal blocks dominate; if we still
        # need to drop something, drop OLDEST tail (not errors): the
        # operator told us errors matter most, and the most-recent
        # tail entries (executor's final conclusion) are usually more
        # diagnostic than the supervisor handoff lines.
        kept_idx = sorted(error_indices)
        budget_left = max_blocks - len(kept_idx)
        if budget_left > 0:
            # Add the latest tail_indices that aren't already errors.
            tail_only = sorted(tail_indices - error_indices, reverse=True)
            extra = sorted(tail_only[:budget_left])
            kept_idx = sorted(set(kept_idx) | set(extra))
        elif budget_left < 0:
            # Even errors alone exceed budget — keep the latest errors.
            kept_idx = sorted(error_indices)[-max_blocks:]
    else:
        remaining = max_blocks - len(must_keep)
        # Fill the leading slots with the earliest non-must-keep
        # blocks (plan / first user prompts / opening assistant text).
        head_candidates = [
            i for i in range(total) if i not in must_keep
        ][:remaining]
        kept_idx = sorted(set(head_candidates) | must_keep)

    # Build the kept list, inserting omitted markers for gaps.
    out: list[dict[str, str]] = []
    prev = -1
    for idx in kept_idx:
        if idx - prev > 1:
            gap_start = prev + 1
            gap_end = idx - 1
            omitted_count = gap_end - gap_start + 1
            omitted_block = {
                "kind": "omitted",
                "omitted_count": str(omitted_count),
                "omitted_block_range": f"[{gap_start},{gap_end}]",
                # event_range is the same as block_range here; if a
                # future revision splits semantic blocks across events
                # this distinction matters.  Kept structured so the
                # supervisor prompt's navigation hint stays stable.
                "omitted_event_range": f"[{gap_start},{gap_end}]",
                "transcript_full_chunk_hint": "transcript_full/manifest.json",
                "text": (
                    f"... omitted {omitted_count} semantic transcript blocks "
                    f"(orig idx {gap_start}-{gap_end}); see "
                    "transcript_full/manifest.json for full chunks"
                ),
            }
            out.append(omitted_block)
        out.append(blocks[idx])
        prev = idx
    # If the very last kept idx is before the end, add a final omitted
    # marker for the post-tail gap (rare — tail window covers last 5).
    if prev < total - 1:
        gap_start = prev + 1
        gap_end = total - 1
        omitted_count = gap_end - gap_start + 1
        out.append({
            "kind": "omitted",
            "omitted_count": str(omitted_count),
            "omitted_block_range": f"[{gap_start},{gap_end}]",
            "omitted_event_range": f"[{gap_start},{gap_end}]",
            "transcript_full_chunk_hint": "transcript_full/manifest.json",
            "text": (
                f"... omitted {omitted_count} trailing semantic blocks "
                f"(orig idx {gap_start}-{gap_end})"
            ),
        })
    return out


def operation_trace_summary(path: Path, max_chars: int = 4000) -> str:
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        return _trim_middle(sanitize_codex_context_text(read_text(path)), max_chars)
    lines: list[str] = []
    tool_counts = payload.get("tool_counts") or {}
    if isinstance(tool_counts, dict) and tool_counts:
        parts = [f"{name}={count}" for name, count in sorted(tool_counts.items())]
        lines.append("tool_counts: " + ", ".join(parts))
    browser_counts = payload.get("browser_action_counts") or {}
    if isinstance(browser_counts, dict) and browser_counts:
        parts = [f"{name}={count}" for name, count in sorted(browser_counts.items())]
        lines.append("browser_actions: " + ", ".join(parts))
    recent_calls = summarize_recent_tool_calls(payload, max_items=8)
    if recent_calls:
        lines.append("recent_tool_calls:")
        for item in recent_calls:
            agent_prefix = f"{item['agent_id']} · " if item.get("agent_id") else ""
            timestamp = _timestamp_label(item.get("timestamp"))
            lines.append(f"- {timestamp} {agent_prefix}{item.get('name')}: {item.get('summary')}")
    text = "\n".join(lines).strip()
    if not text:
        text = sanitize_codex_context_text(read_text(path))
    return _trim_middle(text, max_chars)


def _tool_arguments_summary(name: str, arguments: dict[str, Any]) -> str:
    args = arguments if isinstance(arguments, dict) else {}
    if name == "browser":
        action = str(args.get("action") or "").strip()
        target = str(args.get("url") or args.get("ref") or args.get("selector") or "").strip()
        summary = action or "browser"
        if target:
            summary += f" · {sanitize_codex_context_text(target)}"
        return summary
    if name == "exec":
        command = str(args.get("command") or args.get("cmd") or args.get("script") or "").strip()
        return sanitize_codex_context_text(command)[:320]
    if name == "sessions_send":
        target = str(args.get("sessionKey") or "").strip()
        message = str(args.get("message") or "").strip()
        preview = sanitize_codex_context_text(message.replace("\n", " "))[:220]
        if target and preview:
            return f"{target} · {preview}"
        return sanitize_codex_context_text(target or preview)[:320]
    if name == "sessions_spawn":
        target = str(args.get("agentId") or args.get("agent") or args.get("targetAgent") or "").strip()
        task = str(args.get("task") or "").strip()
        preview = sanitize_codex_context_text(task.replace("\n", " "))[:220]
        if target and preview:
            return f"{target} · {preview}"
        return sanitize_codex_context_text(target or preview)[:320]
    return sanitize_codex_context_text(json.dumps(args, ensure_ascii=False))[:320]


def summarize_recent_tool_calls(tool_usage: dict[str, Any], max_items: int = 6) -> list[dict[str, Any]]:
    calls = tool_usage.get("tool_calls") or []
    if not isinstance(calls, list):
        return []
    items: list[dict[str, Any]] = []
    for call in calls[-max_items:]:
        if not isinstance(call, dict):
            continue
        name = str(call.get("name") or "").strip()
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        items.append(
            {
                "agent_id": str(call.get("agentId") or "").strip(),
                "name": name,
                "timestamp": str(call.get("timestamp") or "").strip(),
                "summary": _tool_arguments_summary(name, arguments),
            }
        )
    return items


def load_agent_manifest(path: Path) -> dict[str, Any]:
    payload = read_json(path, {})
    return payload if isinstance(payload, dict) else {}


def parse_agent_session_target(session_key: str) -> str:
    value = str(session_key or "").strip()
    if not value:
        return ""
    if value.startswith("agent:"):
        parts = value.split(":")
        if len(parts) >= 2:
            return parts[1].strip()
    return value


def build_handoff_trace(tool_usage: dict[str, Any], max_items: int = 12) -> list[dict[str, Any]]:
    calls = tool_usage.get("tool_calls") or []
    if not isinstance(calls, list):
        return []
    events: list[dict[str, Any]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        name = str(call.get("name") or "").strip()
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        source_agent = str(call.get("agentId") or "").strip()
        if name == "sessions_send":
            target_agent = parse_agent_session_target(arguments.get("sessionKey") or "")
            events.append(
                {
                    "from_agent": source_agent,
                    "to_agent": target_agent,
                    "via": "sessions_send",
                    "timestamp": str(call.get("timestamp") or "").strip(),
                    "summary": _tool_arguments_summary(name, arguments),
                }
            )
            continue
        if name == "subagents":
            target_agent = str(arguments.get("agentId") or arguments.get("agent") or arguments.get("targetAgent") or "").strip()
            action = str(arguments.get("action") or "").strip()
            if target_agent or action:
                events.append(
                    {
                        "from_agent": source_agent,
                        "to_agent": target_agent,
                        "via": "subagents",
                        "timestamp": str(call.get("timestamp") or "").strip(),
                        "summary": _tool_arguments_summary(name, arguments),
                    }
                )
            continue
        if name == "sessions_spawn":
            target_agent = str(arguments.get("agentId") or arguments.get("agent") or arguments.get("targetAgent") or "").strip()
            events.append(
                {
                    "from_agent": source_agent,
                    "to_agent": target_agent,
                    "via": "sessions_spawn",
                    "timestamp": str(call.get("timestamp") or "").strip(),
                    "summary": _tool_arguments_summary(name, arguments),
                }
            )
    return events[-max_items:]


def build_agent_session_summaries(context: SupervisorContext, max_agents: int = 8) -> list[dict[str, Any]]:
    manifest = load_agent_manifest(context.attempt.out_dir / "agent_sessions_manifest.json")
    manifest_agents = manifest.get("agents") or []
    if not isinstance(manifest_agents, list) or not manifest_agents:
        return []
    session_root = context.attempt.out_dir / "agent_sessions"
    summaries: list[dict[str, Any]] = []
    for item in manifest_agents[:max_agents]:
        if not isinstance(item, dict):
            continue
        agent_id = str(item.get("agentId") or "").strip()
        if not agent_id:
            continue
        agent_dir = session_root / agent_id
        transcript_path = agent_dir / "transcript.jsonl"
        tool_usage_path = agent_dir / "tool_usage.json"
        tool_usage = read_json(tool_usage_path, {})
        if not isinstance(tool_usage, dict):
            tool_usage = {}
        summaries.append(
            {
                "agent_id": agent_id,
                "label": str(item.get("label") or EDICT_AGENT_LABELS.get(agent_id, agent_id)),
                "group": str(item.get("group") or "").strip(),
                "event_count": int(item.get("eventCount") or 0),
                "tool_call_count": int(item.get("toolCallCount") or 0),
                "tool_counts": tool_usage.get("tool_counts") or item.get("toolCounts") or {},
                "browser_action_counts": tool_usage.get("browser_action_counts") or {},
                "recent_tool_calls": summarize_recent_tool_calls(tool_usage, max_items=4),
                "semantic_transcript_blocks": semantic_transcript_blocks(transcript_path, max_chars=2200, max_blocks=6) if transcript_path.exists() else [],
                "operation_trace_summary": operation_trace_summary(tool_usage_path, max_chars=1200) if tool_usage_path.exists() else "",
            }
        )
    return summaries


def build_multi_agent_visible_payload(context: SupervisorContext) -> dict[str, Any]:
    manifest = load_agent_manifest(context.attempt.out_dir / "agent_sessions_manifest.json")
    tool_usage = read_json(context.attempt.tool_usage_file, {})
    if not isinstance(tool_usage, dict):
        tool_usage = {}
    agent_summaries = build_agent_session_summaries(context)
    if not manifest and not agent_summaries:
        return {}
    return {
        "primary_agent_id": str(manifest.get("primaryAgentId") or ""),
        "active_agents": [
            {
                "agent_id": str(item.get("agentId") or ""),
                "label": str(item.get("label") or EDICT_AGENT_LABELS.get(str(item.get("agentId") or ""), str(item.get("agentId") or ""))),
                "group": str(item.get("group") or "").strip(),
                "event_count": int(item.get("eventCount") or 0),
                "tool_call_count": int(item.get("toolCallCount") or 0),
                "tool_counts": item.get("toolCounts") or {},
            }
            for item in (manifest.get("agents") or [])
            if isinstance(item, dict) and str(item.get("agentId") or "").strip()
        ],
        "handoff_trace": build_handoff_trace(tool_usage),
        "agent_summaries": agent_summaries,
    }


def runtime_probe_payload(path: Path) -> dict[str, Any]:
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        return {}
    processes = payload.get("processes") if isinstance(payload.get("processes"), dict) else {}
    summarized_processes: dict[str, Any] = {}
    for name, values in processes.items():
        if not isinstance(values, list):
            continue
        summarized_processes[str(name)] = {
            "count": len(values),
            "sample": [_trim_middle(sanitize_codex_context_text(str(item)), 180) for item in values[:3]],
        }
    windows = payload.get("windows") if isinstance(payload.get("windows"), list) else []
    result_files = payload.get("result_files") if isinstance(payload.get("result_files"), list) else []
    return {
        "windows": [_trim_middle(sanitize_codex_context_text(str(item)), 180) for item in windows[:6]],
        "processes": summarized_processes,
        "result_files": [sanitize_codex_context_text(str(item)) for item in result_files[:20]],
    }
