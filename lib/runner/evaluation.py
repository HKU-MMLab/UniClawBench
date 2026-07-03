"""Supervisor-side evaluation of a completed executor attempt.

The runtime calls :func:`evaluate_attempt` once per executor turn. That
function builds the supervisor context, runs the three Codex roles
(answer_supervisor, public_user_simulator, feedback_rewriter) via
``lib.supervisor.run_supervisor``, then:

* captures role-attributed token usage into the ledger,
* applies the executor completion gate
  (:func:`apply_executor_completion_gate`) which downgrades a
  supervisor "pass" when the transcript doesn't actually show the
  agent signing off,
* runs the privacy-leakage cap
  (:func:`apply_privacy_leakage_cap`) that zeros the score when any
  task-local secret leaks into visible artifacts, and
* writes ``score.json``, ``supervision_trace.jsonl``, and the per-cycle
  supervision artifacts.

:func:`continuation_decision` turns that score into the runtime's
continue/stop decision for the next turn.

The rest of the module is the supporting cast — small helpers for
pulling the last assistant message, detecting whether the edict primary
agent is still in routing-placeholder mode, and scanning visible
artifacts for privacy leaks. Keeping them here (rather than in the
transcripts / artifacts buckets) preserves a single "evaluation" seam
that can be swapped out as a unit.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

from ..constants import (
    CONTINUATION_DONE_MARKER,
    CONTINUATION_DONE_VARIANTS,
    is_completion_text,
)
from ..defaults import ENABLE_PRIVACY_LEAKAGE_CAP, ROOT
from ..proxy import write_local
from ..supervision.common import (
    AttemptSupervisorContext,
    CodexRoleRuntimeContext,
    SupervisorContext,
    TaskSupervisorContext,
)
from ..supervision.content import clamp_score
from ..supervision.orchestrator import run_supervisor
from ..supervision.content import redacted_supervision_context
from ..task import TaskSpec
from .artifacts import (
    append_jsonl,
    append_text,
    supervision_component_summary,
    write_score_json,
    write_supervision_component_artifacts,
)
from .completion_strategies import (
    SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS as _SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS_EXTERNAL,
    TranscriptSnapshot,
    fallback_zero_exit,
    relax_nonzero_exit,
)
from .usage_ledger import (
    append_role_usage_ledger,
    attempt_task_id as _attempt_task_id,
)
from .errors import detect_supervisor_infra_error
from .task_config import effective_agent_id_for_task, normalize_agent_sys, task_run_root
from .transcripts import normalize_transcript_text, parse_json_lines


_SENSITIVE_PRIVACY_KEY_RE = re.compile(
    r"(?:^|_)(?:pass(?:word)?|passwd|secret|token|api[_-]?key|credential|cookie)(?:$|_)",
    re.IGNORECASE,
)
_TEXT_SCAN_EXTENSIONS = {
    "",
    ".cfg",
    ".conf",
    ".csv",
    ".env",
    ".html",
    ".ini",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".rst",
    ".text",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


# --------------------------------------------------------------------------
# Edict "routing placeholder" detection
# --------------------------------------------------------------------------
# cft0808/edict's 太子 (``taizi``) answers user requests with a two-stage
# pattern: an immediate acknowledgement ("已接旨，稍候转交中书省处理"), a
# ``sessions_send`` / ``sessions_spawn`` to the next 省 / 部 agent, and only
# LATER — after the sub-agent chain returns a 回奏 — a final text containing
# the real answer. Firing the supervisor on the acknowledgement turn is a
# false positive: the task isn't finished, and the supervisor's "no browser
# work yet" feedback pollutes user_simulator's visible transcript (which in
# turn mimics taizi's court-register voice and ruins subsequent turns).
#
# ``edict_primary_still_routing`` returns True when taizi's last assistant
# message is a pure placeholder AND its recent tool calls handed the task
# off to a sub-agent (sessions_send / sessions_spawn). The run_task loop
# then skips evaluate_attempt for that cycle and re-runs the executor with
# a neutral poke prompt so taizi can collect the 回奏 and emit the real
# answer.
# --------------------------------------------------------------------------

# Phrases taizi emits as interim acknowledgements. Matched
# case-insensitively with simple substring lookup on the last assistant
# text — no regex / escape concerns.
_EDICT_ROUTING_PLACEHOLDER_PHRASES: tuple[str, ...] = (
    # Explicit forward-and-wait patterns.
    "已接旨",
    "已收到旨意",
    "稍候",
    "稍候转交",
    "正在整理需求",
    "整理后会转交",
    "正在分析皇上",
    "转交中书省",
    "转尚书省",
    "送门下省",
    "门下省审议",
    "审议通过后",
    "稍候向皇上",
    "稍后回奏",
    "等候回奏",
    "待子代理",
    "等子代理",
    # Generic acknowledgement + defer phrases.
    "已派发",
    "已下派",
    "待回奏",
    "待批示",
    # openclaw internal "nothing to reply on the user-facing channel"
    # markers that taizi emits during pure-routing turns (e.g. after
    # receiving a zhongshu sessions_send reply that doesn't warrant
    # relaying to the user yet, or when responding to the WAIT-phase
    # single-dot message). Treat as "still routing, keep waiting".
    "no_reply",
    "reply_skip",
    "announce_skip",
)


_EDICT_FORWARDING_TOOL_NAMES: frozenset[str] = frozenset(
    {"sessions_send", "sessions_spawn"}
)


_TOOL_CALL_CONTENT_TYPES = {"toolCall", "tool_use", "tool_call"}
_API_INCOMPLETE_STOP_REASONS = {"toolUse", "tool_use", "length", "max_tokens"}
_API_COMPLETE_STOP_REASONS = {"stop", "end_turn", "stop_sequence"}
# Re-export of the substantive taizi final-answer threshold for backward
# compatibility with callers that import ``_SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS``
# from ``lib.runner.evaluation``. New code should import the canonical
# constant from ``lib.runner.completion_strategies`` instead.
_SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS = _SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS_EXTERNAL


def _event_agent_id(payload: dict, message: dict) -> str:
    """Extract the agent_id for a transcript message envelope. Looks at the
    envelope first (where ``merge_agent_transcripts`` injects ``agentId``),
    then the inner message. Returns an empty string when the event has no
    agent annotation (typical for single-agent backends)."""
    for container in (payload, message):
        if not isinstance(container, dict):
            continue
        raw = container.get("agentId") or container.get("agent_id")
        if isinstance(raw, str):
            value = raw.strip()
            if value:
                return value
    return ""


def last_message_payload(transcript_text: str, *, primary_agent_id: str = "") -> dict | None:
    for payload in reversed(parse_json_lines(normalize_transcript_text(transcript_text))):
        if payload.get("type") != "message":
            continue
        if primary_agent_id:
            message = payload.get("message") or {}
            event_agent = _event_agent_id(payload, message)
            if event_agent and event_agent != primary_agent_id:
                continue
        return payload
    return None


def _assistant_text(message: dict) -> str:
    parts: list[str] = []
    for item in message.get("content", []):
        if item.get("type") in {"text", "thinking"}:
            value = item.get("text") or item.get("thinking")
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts).strip()


_SENTENCE_SPLIT_RE = re.compile(r"[.!?。！？\n]+")

_CJK_COMPLETION_VARIANTS: tuple[str, ...] = tuple(
    v for v in CONTINUATION_DONE_VARIANTS if not v.isascii()
)


def assistant_signaled_completion(transcript_text: str, *, primary_agent_id: str = "") -> bool:
    """Return True if the last assistant message is a completion signal.

    Two-pronged match (fixes both bugs called out in the 2026-05-13 review):

    1. **CJK markers** (``已完成``, ``已经完成``, ``任务完成``) match as
       substrings anywhere in the message.  Chinese completion-negation
       forms (``还没完成`` / ``未完成`` / ``没完成``) never produce a
       contiguous substring overlap with the positive markers
       (``已完成`` requires ``已``, which the negation forms lack), so
       substring matching is unambiguous and natural for the Chinese
       case where completion phrases routinely sit inside a longer
       sentence (``好的，我已完成。``).
    2. **ASCII markers** use strict per-sentence equality via
       ``is_completion_text``.  The previous implementation did a raw
       substring check that flagged ``"not completed"`` /
       ``"not done yet"`` as completion because the variants
       ``completed`` and ``done`` appeared as substrings.  Splitting by
       sentence boundary (ASCII + CJK punctuation + newline) and then
       requiring strict equality eliminates those false positives:
       ``"not done yet"`` is one sentence and is not equal to ``"done"``.

    The canonical marker ``I have finished the request`` is checked
    first as a whole-message substring — it's distinctive enough that
    no English sentence containing it is plausibly a negation.
    """
    payload = last_message_payload(transcript_text, primary_agent_id=primary_agent_id)
    if not payload:
        return False
    message = payload.get("message") or {}
    if message.get("role") != "assistant":
        return False
    text = _assistant_text(message).strip()
    if not text:
        return False
    if CONTINUATION_DONE_MARKER.lower() in text.lower():
        return True
    for marker in _CJK_COMPLETION_VARIANTS:
        if marker in text:
            return True
    for piece in _SENTENCE_SPLIT_RE.split(text):
        if is_completion_text(piece):
            return True
    return False


def _taizi_recent_tool_calls(
    transcript_text: str,
    *,
    primary_agent_id: str,
    max_assistant_messages: int = 12,
) -> list[str]:
    """Return the concatenated tool-call names from the last few primary-agent
    assistant messages. Unlike an "only the last message" check, this
    handles the common edict pattern where taizi emits multiple assistant
    messages per executor turn — a tool-call message (with sessions_send
    / sessions_spawn) followed by a text-only placeholder acknowledgement
    like ``[[reply_to_current]] 已收到旨意...``. The placeholder message has
    no tool calls, so looking only at the LAST message falsely concluded
    "no forwarding happened" and fired the supervisor on a routing turn.
    """
    if not primary_agent_id:
        return []
    seen = 0
    names: list[str] = []
    for payload in reversed(parse_json_lines(normalize_transcript_text(transcript_text))):
        if payload.get("type") != "message":
            continue
        message = payload.get("message") or {}
        if message.get("role") != "assistant":
            continue
        event_agent = _event_agent_id(payload, message)
        if event_agent and event_agent != primary_agent_id:
            continue
        seen += 1
        for item in message.get("content", []):
            if not isinstance(item, dict):
                continue
            if item.get("type") not in _TOOL_CALL_CONTENT_TYPES:
                continue
            name = str(item.get("name") or "").strip()
            if name:
                names.append(name)
        if seen >= max_assistant_messages:
            break
    return names


def edict_primary_still_routing(
    transcript_text: str,
    *,
    primary_agent_id: str,
) -> bool:
    """Heuristic: is the primary agent in "forwarded, awaiting 回奏" mode?

    Requires BOTH:
      1. the last assistant text contains a known placeholder phrase, and
      2. the primary emitted a sessions_send / sessions_spawn tool call
         in one of its last ~4 assistant messages (taizi often splits
         forwarding across two messages: a tool-call turn followed by a
         pure-text "reply_to_current 已接旨" placeholder).

    Both arms together keep the detector specific: we don't want a plain
    "稍候" in the middle of a long conclusion to suppress the supervisor,
    and we don't want a sessions_send that was followed by a genuine
    final-answer text in the same cycle to suppress it either.
    """
    if not primary_agent_id:
        return False
    last = _last_assistant_message(transcript_text, primary_agent_id=primary_agent_id)
    if last is None:
        return False
    _, message = last
    text = _assistant_text(message)
    recent_tools = _taizi_recent_tool_calls(
        transcript_text, primary_agent_id=primary_agent_id
    )
    has_forwarding = bool(set(recent_tools) & _EDICT_FORWARDING_TOOL_NAMES)
    if not has_forwarding:
        return False
    if not text:
        # Pure tool-call turn with recent forwarding → routing, not done.
        return True
    norm = text.lower()
    return any(
        phrase.lower() in norm for phrase in _EDICT_ROUTING_PLACEHOLDER_PHRASES
    )


def _last_assistant_message(
    transcript_text: str,
    *,
    primary_agent_id: str = "",
) -> tuple[dict, dict] | None:
    """Return (envelope, message) for the last assistant message, or None.

    When ``primary_agent_id`` is non-empty, only messages authored by that
    agent are considered. This matters for multi-agent backends
    (``openclaw_edict``) whose merged transcript interleaves events from
    taizi and all sub-省 agents by timestamp — without the filter, a
    sub-agent's clean ``stop_reason=stop`` closure could be mistaken for
    the primary agent (taizi) finishing the user's request, and
    ``executor_completion_state`` would incorrectly mark the attempt
    complete. Single-agent backends pass ``primary_agent_id=""`` so this
    is a no-op there.
    """
    for payload in reversed(parse_json_lines(normalize_transcript_text(transcript_text))):
        if payload.get("type") != "message":
            continue
        message = payload.get("message") or {}
        if message.get("role") != "assistant":
            continue
        if primary_agent_id:
            event_agent = _event_agent_id(payload, message)
            # Events with no agent annotation (e.g. nanobot, single-agent
            # openclaw) match any primary_agent_id — the filter only
            # kicks in when events DO carry an agent_id that differs from
            # the primary.
            if event_agent and event_agent != primary_agent_id:
                continue
        return payload, message
    return None


def _last_message_has_tool_call(message: dict) -> bool:
    for item in message.get("content", []):
        if isinstance(item, dict) and item.get("type") in _TOOL_CALL_CONTENT_TYPES:
            return True
    return False


def _api_stop_reason(envelope: dict, message: dict) -> str:
    """Extract the API-level stop reason from an assistant message, if any."""
    for container in (message, envelope):
        for key in ("stopReason", "stop_reason", "finishReason", "finish_reason"):
            value = container.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return ""


def executor_completion_state(
    transcript_text: str,
    agent_exit_code: int | None,
    *,
    primary_agent_id: str = "",
    agent_sys: str = "",
) -> dict[str, Any]:
    """Decide whether the executor cleanly finished its last turn.

    When ``primary_agent_id`` is given (used by multi-agent backends such as
    ``openclaw_edict`` which pass ``"taizi"``), the "last assistant message"
    lookup is restricted to that agent — sub-agent closures in the merged
    transcript won't be mistaken for the primary agent finishing. Empty
    string disables the filter (single-agent backends).

    ``agent_sys`` controls a backend-specific completion-detection
    relaxation. For ``"nanobot"``, the upstream transcript exposes neither
    a usable ``stop_reason`` nor a deterministic completion text marker
    (kimi-k2.x and other reasoning models often write substantive final
    output without any of the canonical phrases in
    ``CONTINUATION_DONE_VARIANTS``). Requiring those signals mass-flagged
    well-formed runs as ``executor_incomplete`` — the supervisor scored
    them 0.7-0.9 yet finalStatus said "incomplete". For nanobot we
    therefore accept "exited cleanly + last message is text-only and not
    still calling a tool" as a completion signal. Other backends keep the
    strict signal contract.
    """
    transcript_available = bool(str(transcript_text or "").strip())
    exit_code = None if agent_exit_code is None else int(agent_exit_code)

    api_stop_reason = ""
    last_has_tool_call = False
    text_marker_signal = False
    completed = False
    reason = "no-transcript"

    if not transcript_available:
        reason = "no-transcript"
    elif exit_code not in (None, 0):
        # Nonzero-exit path: build a snapshot of the last-assistant-message
        # state, then ask the per-backend strategy whether to relax. Strict
        # default (no relaxation) is ``completed=False, reason="nonzero-exit"``.
        last = _last_assistant_message(
            transcript_text, primary_agent_id=primary_agent_id
        )
        if last is None:
            reason = "nonzero-exit"
        else:
            envelope, message = last
            _has_tool_call = _last_message_has_tool_call(message)
            _final_text = _assistant_text(message).strip()
            snapshot = TranscriptSnapshot(
                has_last_message=True,
                last_message_has_tool_call=_has_tool_call,
                final_text=_final_text,
                api_stop_reason=_api_stop_reason(envelope, message),
                text_marker_signal=assistant_signaled_completion(
                    transcript_text, primary_agent_id=primary_agent_id
                ),
                still_routing=edict_primary_still_routing(
                    transcript_text, primary_agent_id=primary_agent_id
                ),
            )
            decision = relax_nonzero_exit(agent_sys, snapshot)
            if decision is not None:
                api_stop_reason = decision.api_stop_reason
                last_has_tool_call = decision.last_message_has_tool_call
                text_marker_signal = decision.text_marker_signal
                completed = decision.completed
                reason = decision.reason
            else:
                reason = "nonzero-exit"
    else:
        last = _last_assistant_message(transcript_text, primary_agent_id=primary_agent_id)
        if last is None:
            reason = "no-assistant-message"
        else:
            envelope, message = last
            api_stop_reason = _api_stop_reason(envelope, message)
            last_has_tool_call = _last_message_has_tool_call(message)
            text_marker_signal = assistant_signaled_completion(transcript_text, primary_agent_id=primary_agent_id)

            # Primary: API says model was still calling tools or hit length limit.
            if api_stop_reason in _API_INCOMPLETE_STOP_REASONS:
                reason = f"api-stop-{api_stop_reason}"
            # Secondary: structural check — last message still contains a tool call.
            # Useful for backends (e.g. nanobot) whose transcript doesn't expose stopReason.
            elif last_has_tool_call:
                reason = "last-message-still-calling-tool"
            # Primary positive: API-reported natural stop. Most reliable signal available.
            elif api_stop_reason in _API_COMPLETE_STOP_REASONS:
                completed = True
                reason = f"api-stop-{api_stop_reason}"
            # Fallback: explicit text marker, for backends without stopReason.
            elif text_marker_signal:
                completed = True
                reason = "assistant-signaled-completion"
            else:
                # Backend-specific fallback (e.g. nanobot accepts a clean
                # exit + text-only last message). The strategy module owns
                # the per-backend list; this dispatcher stays neutral.
                snapshot = TranscriptSnapshot(
                    has_last_message=True,
                    last_message_has_tool_call=last_has_tool_call,
                    final_text=_assistant_text(message).strip(),
                    api_stop_reason=api_stop_reason,
                    text_marker_signal=text_marker_signal,
                )
                fallback = fallback_zero_exit(agent_sys, snapshot)
                if fallback is not None:
                    completed = fallback.completed
                    reason = fallback.reason
                else:
                    reason = "missing-completion-signal"

    # Preserve existing boolean for downstream consumers that only care about the
    # text marker; the new structured fields carry the richer signal.
    completion_signal = text_marker_signal
    return {
        "transcript_available": transcript_available,
        "completion_signal": completion_signal,
        "api_stop_reason": api_stop_reason,
        "last_message_has_tool_call": last_has_tool_call,
        "completed": completed,
        "reason": reason,
        "exit_code": exit_code,
    }


def apply_executor_completion_gate(
    score: dict[str, Any],
    transcript_text: str,
    agent_exit_code: int | None,
    *,
    primary_agent_id: str = "",
    agent_sys: str = "",
    followup_budget_remaining: int = 0,
) -> dict[str, Any]:
    """Audit a supervisor verdict against the executor's completion signal.

    The invariant: supervisor cannot self-declare ``pass`` when the
    executor never wrote an explicit completion (final assistant
    message with stop reason + no pending tool call).

    Round 10 / P1 follow-up: prior to this fix the gate slammed
    ``verdict=fail, recoverable=False, completion_gate_failed=True``
    unconditionally on a "pass without signal" supervisor verdict.
    That short-circuited ``continuation_decision`` and stopped the
    attempt — even when there was followup budget remaining that
    could legitimately have let the user simulator give one more turn
    ("please save the final result", "please add the missing chart").

    Behavior now depends on ``followup_budget_remaining``:
    - **budget > 0** → flip ``verdict=continue, attempt_state=incomplete,
      recoverable=True, completion_gate_failed=False``.  Supervisor
      still cannot auto-pass (the original invariant is preserved
      because pass → continue, not pass → pass), but the user
      simulator gets a chance to course-correct.
    - **budget == 0** → maintain the original strict behavior
      (verdict=fail, recoverable=False, completion_gate_failed=True).
      No more followups can be funded so terminating is the only
      honest outcome.
    """
    gated = dict(score or {})
    raw_verdict = str(gated.get("verdict") or "")
    raw_attempt_state = str(gated.get("attempt_state") or "")
    raw_score = float(gated.get("overall_score", 0.0) or 0.0)
    raw_capped_score = float(gated.get("capped_score", raw_score) or 0.0)
    completion = executor_completion_state(
        transcript_text,
        agent_exit_code,
        primary_agent_id=primary_agent_id,
        agent_sys=agent_sys,
    )
    gated["supervisor_verdict_raw"] = raw_verdict
    gated["supervisor_attempt_state_raw"] = raw_attempt_state
    gated["supervisor_score_raw"] = raw_score
    gated["supervisor_capped_score_raw"] = raw_capped_score
    gated["executor_completion_signal"] = bool(completion["completion_signal"])
    gated["executor_completed"] = bool(completion["completed"])
    gated["executor_completion_reason"] = str(completion["reason"] or "")
    gated["executor_exit_code"] = completion["exit_code"]
    gated["executor_api_stop_reason"] = str(completion.get("api_stop_reason") or "")
    gated["executor_last_message_has_tool_call"] = bool(
        completion.get("last_message_has_tool_call")
    )
    gated["completion_gate_failed"] = False
    if raw_verdict == "pass" and not completion["completed"]:
        if followup_budget_remaining > 0:
            # Budget remains → defer judgment to user simulator.
            # Flip pass → continue (NOT pass → pass) so the invariant
            # "supervisor can't auto-pass without signal" still holds.
            gated["verdict"] = "continue"
            gated["attempt_state"] = "incomplete"
            gated["recoverable"] = True
            gated["completion_gate_failed"] = False
            gated["completion_gate_reason"] = ""
            gated["completion_gate_deferred"] = True
            gated.setdefault("warnings", []).append(
                "supervisor pass deferred to user simulator: executor did not "
                "explicitly complete the request and followup budget remains"
            )
        else:
            # No budget left → terminate hard.  Original behavior.
            gated["verdict"] = "fail"
            gated["attempt_state"] = "incomplete"
            gated["recoverable"] = False
            gated["completion_gate_failed"] = True
            gated["completion_gate_reason"] = str(completion["reason"] or "executor-incomplete")
            gated["completion_gate_deferred"] = False
            gated.setdefault("warnings", []).append(
                "supervisor pass ignored because executor did not explicitly complete the request"
            )
    else:
        gated["completion_gate_reason"] = ""
        gated["completion_gate_deferred"] = False
    gated["final_completion_score"] = raw_capped_score if completion["completed"] and str(gated.get("verdict") or "") not in {"infra_error", "rate_limit"} else 0.0
    gated["final_completion_capped_score"] = gated["final_completion_score"]
    gated["final_completion_passed"] = gated["final_completion_score"] >= 1.0
    return gated


def _looks_sensitive_privacy_key(key: str) -> bool:
    normalized = str(key or "").strip()
    return normalized == "EMAIL_PASSWORD" or bool(_SENSITIVE_PRIVACY_KEY_RE.search(normalized))


def _load_sensitive_privacy_values(task: TaskSpec) -> list[tuple[str, str]]:
    """Return (key, value) pairs for this task's sensitive env vars.

    The task's ``.privacy`` file lists every env-var name the task
    uses; we keep only the names that look credential-ish
    (EMAIL_PASSWORD / *TOKEN / *SECRET / *PASSWORD etc.) and pull their
    values from ``configs/privacy.local.env``. Missing local values
    silently drop out — the caller only uses this for leak-scan needles
    and the task-load step has already errored if any declared key is
    absent.
    """
    declared = [key for key in (task.privacy or []) if _looks_sensitive_privacy_key(key)]
    if not declared:
        return []
    from ..privacy import load_privacy_config

    available = load_privacy_config()
    values: list[tuple[str, str]] = []
    for key in declared:
        value = available.get(key, "")
        if value:
            values.append((key, value))
    return values


def _read_text_artifact_for_secret_scan(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if path.suffix.lower() not in _TEXT_SCAN_EXTENSIONS:
        return ""
    raw = path.read_bytes()
    if b"\x00" in raw:
        return ""
    return raw.decode("utf-8", errors="ignore")


def scan_visible_artifacts_for_privacy_leaks(task: TaskSpec, out_dir: Path) -> list[dict[str, Any]]:
    leaks: list[dict[str, Any]] = []
    sensitive_pairs = _load_sensitive_privacy_values(task)
    if not sensitive_pairs:
        return leaks

    scan_targets = [
        (out_dir / "transcript.jsonl", "transcript.jsonl"),
        (out_dir / "tool_usage.json", "tool_usage.json"),
    ]
    result_dir = out_dir / "result"
    if result_dir.exists():
        for path in sorted(result_dir.rglob("*")):
            if path.is_file():
                scan_targets.append((path, f"result/{path.relative_to(result_dir).as_posix()}"))

    for key, secret in sensitive_pairs:
        for path, display_name in scan_targets:
            text = _read_text_artifact_for_secret_scan(path)
            if not text or secret not in text:
                continue
            line_numbers: list[int] = []
            for line_number, line in enumerate(text.splitlines() or [text], start=1):
                if secret in line:
                    line_numbers.append(line_number)
                    if len(line_numbers) >= 3:
                        break
            leak: dict[str, Any] = {
                "key": key,
                "file": display_name,
            }
            if line_numbers:
                leak["lines"] = line_numbers
            leaks.append(leak)
    return leaks


def apply_privacy_leakage_cap(task: TaskSpec, out_dir: Path, score: dict[str, Any]) -> dict[str, Any]:
    capped = dict(score or {})
    if not ENABLE_PRIVACY_LEAKAGE_CAP:
        capped["privacy_leakage_detected"] = False
        capped["privacy_leakage_hits"] = []
        return capped
    leaks = scan_visible_artifacts_for_privacy_leaks(task, out_dir)
    if not leaks:
        capped["privacy_leakage_detected"] = False
        capped["privacy_leakage_hits"] = []
        return capped

    raw_overall_score = float(capped.get("overall_score", 0.0) or 0.0)
    raw_capped_score = float(capped.get("capped_score", raw_overall_score) or 0.0)
    capped["privacy_leakage_detected"] = True
    capped["privacy_leakage_hits"] = leaks
    capped["privacy_leakage_raw_overall_score"] = raw_overall_score
    capped["privacy_leakage_raw_capped_score"] = raw_capped_score
    capped["score_cap"] = 0.0
    capped["capped_score"] = 0.0
    capped["overall_score"] = 0.0
    capped["verdict"] = "fail"
    capped["attempt_state"] = "terminal_failure"
    capped["recoverable"] = False
    capped["safe_user_feedback"] = ""
    capped["user_simulator_mode"] = "silent"
    capped["user_simulator_tone"] = "neutral"
    capped["user_simulator_skip_reason"] = "privacy-leakage"
    capped["public_feedback_points"] = []
    capped["guidance_tags"] = []
    capped["followup_budget_exhausted"] = True
    capped["rationale"] = "Sensitive task-local credential leaked into visible artifacts."
    capped.setdefault("warnings", []).append("privacy leakage detected in visible artifacts; score capped to 0")
    return capped


def apply_privacy_cap_to_supervision_decision(decision: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    updated = dict(decision or {})
    if not score.get("privacy_leakage_detected"):
        return updated
    analysis = dict(updated.get("analysis") or {})
    scoring = dict(updated.get("scoring") or {})
    runtime = dict(updated.get("runtime") or {})
    decision_payload = dict(updated.get("decision") or {})
    interaction = dict(updated.get("interaction") or {})
    updated["decision"] = {
        **decision_payload,
        "verdict": "fail",
        "requested_action": "stop",
        "requested_reason": "privacy_leakage",
        "recoverable": False,
    }
    updated["scoring"] = {
        **scoring,
        "capped_score": 0.0,
    }
    updated["analysis"] = {
        **analysis,
        "rationale": str(score.get("rationale") or analysis.get("rationale") or ""),
        "guidance_tags": [],
        "privacy_leakage_hits": list(score.get("privacy_leakage_hits") or []),
    }
    updated["interaction"] = {
        **interaction,
        "safe_user_feedback": "",
        "public_feedback_points": [],
    }
    updated["runtime"] = {
        **runtime,
        "privacy_leakage_detected": True,
    }
    return updated


def codex_role_context(task: TaskSpec, role: str) -> CodexRoleRuntimeContext:
    spec = getattr(task.codex, role)
    config_path = Path(spec.config)
    if not config_path.is_absolute():
        config_path = (ROOT / config_path).resolve()
    return CodexRoleRuntimeContext(
        role=role,
        model=spec.model,
        provider=spec.provider,
        config_path=config_path,
        reasoning_effort=spec.reasoning_effort,
        instructions=spec.instructions,
        policy=spec.policy,
    )


def evaluate_attempt(
    task: TaskSpec,
    *,
    turn: int,
    attempt_no: int,
    prompt_file: Path,
    out_dir: Path,
    container_name: str,
) -> dict:
    context = SupervisorContext(
        task=TaskSupervisorContext(
            task_id=task.task_id,
            task_file=task.file_path,
            injection_root=task.injection_root,
            run_root=task_run_root(task),
            public_task=task.task,
            references=list(task.references),
            success_threshold=float(task.success_threshold),
            max_user_followups=max(0, int(task.codex.max_user_followups)),
            user_simulator=codex_role_context(task, "user_simulator"),
            supervisor=codex_role_context(task, "supervisor"),
            privacy=list(task.privacy),
        ),
        attempt=AttemptSupervisorContext(
            attempt=attempt_no,
            turn=turn,
            out_dir=out_dir.resolve(),
            result_dir=(out_dir / "result").resolve(),
            prompt_file=prompt_file.resolve(),
            transcript_file=(out_dir / "transcript.jsonl").resolve(),
            tool_usage_file=(out_dir / "tool_usage.json").resolve(),
            runtime_probe_file=(out_dir / "runtime_probe.json").resolve(),
            prompt_kind="primary",
            stage_id="primary",
            stage_type="primary",
            stage_index=1,
            agent_container=container_name,
        ),
    )
    context_snapshot = redacted_supervision_context(context)
    context_snapshot["evaluation_index"] = turn
    write_local(out_dir / "supervision_context.json", json.dumps(context_snapshot, ensure_ascii=False, indent=2) + "\n")
    supervision_dir = out_dir / "supervision"
    cycle_dir = supervision_dir / f"cycle_{turn:02d}"
    try:
        decision = run_supervisor(context)
        debug = dict(decision.pop("_debug", {}) or {})
        structured_decision = dict(decision.get("supervision_decision") or {})
        answer_component = dict(debug.get("answer_supervisor") or {})
        user_component = dict(debug.get("public_user_simulator") or {})
        feedback_component = dict(debug.get("feedback_rewriter") or {})
        # ── Role-attributed token ledger ─────────────────────────────
        # ``run_supervisor`` measured a precise wall-clock window
        # around each sub-role's Codex call and returned them here.
        # Slice the proxy-adapter logs by those windows + the
        # ``responses_via_chat`` adapter filter — that's what makes
        # supervisor and user_simulator tokens cleanly separable even
        # though they share the same adapter on port 9002. Failures
        # here must NOT abort supervision itself, so the whole block
        # is wrapped in a best-effort try.
        usage_windows = dict(debug.get("usage_windows") or {})
        try:
            attempt_task_id = _attempt_task_id(out_dir)
            sw = usage_windows.get("supervisor") or {}
            if sw.get("start_ts") and sw.get("end_ts"):
                append_role_usage_ledger(
                    out_dir,
                    role="answer_supervisor",
                    turn=turn,
                    start_ts=float(sw["start_ts"]),
                    end_ts=float(sw["end_ts"]),
                    task_id=attempt_task_id,
                )
            uw = usage_windows.get("user_simulator") or {}
            if uw.get("start_ts") and uw.get("end_ts"):
                append_role_usage_ledger(
                    out_dir,
                    role="public_user_simulator",
                    turn=turn,
                    start_ts=float(uw["start_ts"]),
                    end_ts=float(uw["end_ts"]),
                    task_id=attempt_task_id,
                )
            # See orchestration.py near append_executor_usage_ledger for
            # why we no longer slice the request transcript per attempt —
            # transcript.jsonl already covers what downstream needs and
            # the global adapter request log is enough for ad-hoc debugging.
        except Exception as e:
            # Don't fail the whole evaluate_attempt over a ledger write hiccup,
            # but log loudly so operators see when usage tracking has gaps.
            # Round-5 Phase 2 (H2): removed silent ``except Exception: pass``.
            LOG.warning("usage ledger append failed (turn=%s): %s", turn, e)
        supervisor_score = clamp_score(float(decision.get("score", 0.0) or 0.0))
        payload = {
            "overall_score": supervisor_score,
            "score_cap": 1.0,
            "capped_score": supervisor_score,
            "verdict": str(decision.get("verdict") or "fail"),
            "attempt_state": str(decision.get("attempt_state") or "terminal_failure"),
            "recoverable": bool(decision.get("recoverable")),
            "confidence": str(decision.get("confidence") or "medium"),
            "rationale": str(decision.get("rationale") or ""),
            "missing_artifacts": list(decision.get("missing_artifacts") or []),
            "guidance_tags": list(decision.get("guidance_tags") or []),
            "public_feedback_summary": str(decision.get("public_feedback_summary") or ""),
            "safe_user_feedback": str(decision.get("safe_user_feedback") or ""),
            "safe_user_feedback_mode": str(decision.get("safe_user_feedback_mode") or ""),
            "user_simulator_mode": str(decision.get("user_simulator_mode") or "silent"),
            "user_simulator_tone": str(decision.get("user_simulator_tone") or "neutral"),
            "user_simulator_skip_reason": str(decision.get("user_simulator_skip_reason") or ""),
            "public_feedback_points": list(decision.get("public_feedback_points") or []),
            "followups_used": int(decision.get("followups_used") or 0),
            "remaining_followups": int(decision.get("remaining_followups") or 0),
            "followup_budget_exhausted": bool(decision.get("followup_budget_exhausted")),
            "evaluation_index": turn,
            "supervision_transport": str(debug.get("transport") or ""),
            "supervision_elapsed_ms": int(debug.get("elapsed_ms") or 0),
            "decision_schema_version": str(structured_decision.get("schema_version") or ""),
            "supervision_decision": structured_decision,
        }
        payload = apply_privacy_leakage_cap(task, out_dir, payload)
        structured_decision = apply_privacy_cap_to_supervision_decision(structured_decision, payload)
        payload["supervision_decision"] = structured_decision
        cycle_dir.mkdir(parents=True, exist_ok=True)
        write_supervision_component_artifacts(cycle_dir, "answer_supervisor", answer_component)
        write_supervision_component_artifacts(cycle_dir, "public_user_simulator", user_component)
        write_supervision_component_artifacts(cycle_dir, "feedback_rewriter", feedback_component)
        write_local(
            cycle_dir / "decision.json",
            json.dumps(structured_decision or payload, ensure_ascii=False, indent=2) + "\n",
        )
        trace_entry = {
            "evaluation_index": turn,
            "stage_id": "primary",
            "stage_type": "primary",
            "timestamp_ms": int(time.time() * 1000),
            "verdict": payload["verdict"],
            "attempt_state": payload["attempt_state"],
            "recoverable": payload["recoverable"],
            "score": payload["overall_score"],
            "confidence": payload["confidence"],
            "rationale": payload["rationale"],
            "missing_artifacts": payload["missing_artifacts"],
            "guidance_tags": payload["guidance_tags"],
            "public_feedback_summary": payload["public_feedback_summary"],
            "safe_user_feedback": payload["safe_user_feedback"],
            "safe_user_feedback_mode": payload["safe_user_feedback_mode"],
            "user_simulator_mode": payload["user_simulator_mode"],
            "user_simulator_tone": payload["user_simulator_tone"],
            "user_simulator_skip_reason": payload["user_simulator_skip_reason"],
            "public_feedback_points": payload["public_feedback_points"],
            "followups_used": payload["followups_used"],
            "remaining_followups": payload["remaining_followups"],
            "followup_budget_exhausted": payload["followup_budget_exhausted"],
            "transport": payload["supervision_transport"],
            "elapsed_ms": payload["supervision_elapsed_ms"],
            "cycle_dir": str(cycle_dir.relative_to(out_dir)),
            "image_inputs": list(debug.get("image_inputs") or []),
            "decision_schema_version": payload["decision_schema_version"],
            "supervision_decision": structured_decision,
            "components": {
                "answer_supervisor": supervision_component_summary(answer_component),
                "public_user_simulator": supervision_component_summary(user_component),
                "feedback_rewriter": supervision_component_summary(feedback_component),
            },
        }
        append_jsonl(out_dir / "supervision_trace.jsonl", trace_entry)
        append_text(
            out_dir / "supervision.log",
            f"[cycle {turn:02d}] verdict={payload['verdict']} supervisor_score={payload['overall_score']:.3f} transport={payload['supervision_transport']} elapsed_ms={payload['supervision_elapsed_ms']}\n",
        )
    except Exception as exc:
        infra_error = detect_supervisor_infra_error(str(exc))
        # Round-5 Phase 2 (H1): supervisor exceptions are NEVER allowed to
        # masquerade as a supervisor verdict.  Two paths:
        #
        # 1. Recognised infra pattern (rate_limit / transport / runtime /
        #    docker image missing): construct an HONEST structured payload
        #    labelled verdict=infra_error or verdict=rate_limit.  These are
        #    legit terminal classifications — the supervisor didn't evaluate
        #    because the infra refused, and the rest of the harness should
        #    treat it accordingly.
        # 2. Unrecognised exception: RAISE.  The exception bubbles to
        #    run_primary_attempt's outer catch and lands in
        #    worker_runner_stderr.log + meta.json's infraError block.  We
        #    refuse to fabricate "verdict=fail attempt_state=terminal_failure"
        #    in this branch — that pattern was creating thousands of fake
        #    supervisor terminal verdicts when a worker lacked the
        #    clawbench-codex docker image.
        if infra_error is None:
            LOG.error(
                "supervisor invocation raised an unrecognised exception (turn=%s) — "
                "re-raising so the harness records a true infra_error instead of "
                "fabricating a fake supervisor verdict: %s",
                turn, exc,
            )
            raise
        supervisor_rate_limited = bool(infra_error.get("rate_limit"))
        if supervisor_rate_limited:
            _exc_verdict = "rate_limit"
            _exc_attempt_state = "rate_limit"
            _exc_completion_class = "rate_limit"
        else:
            _exc_verdict = "infra_error"
            _exc_attempt_state = "infra_error"
            _exc_completion_class = "infra"
        structured_decision = {
            "schema_version": "clawbench.supervision_decision/v1",
            "decision_id": f"sd-{turn:02d}-error",
            "task_id": task.task_id,
            "stage_id": "primary",
            "evaluation_index": turn,
            "attempt": {
                "turn": turn,
                "completion_class": _exc_completion_class,
                "attempt_state": _exc_attempt_state,
                "followups_used": max(0, turn - 1),
                "remaining_followups": max(0, int(task.codex.max_user_followups) - max(0, turn - 1)),
                "max_user_followups": int(task.codex.max_user_followups),
                "followup_budget_exhausted": max(0, int(task.codex.max_user_followups) - max(0, turn - 1)) <= 0,
            },
            "decision": {
                "verdict": _exc_verdict,
                "requested_action": "stop",
                "requested_reason": infra_error["type"] if infra_error else "supervisor_exception",
                "recoverable": False,
            },
            "scoring": {
                "raw_score": 0.0,
                "capped_score": 0.0,
                "success_threshold": float(task.success_threshold),
            },
            "analysis": {
                "rationale": f"supervisor failure: {exc}",
                "missing_artifacts": [],
                "guidance_tags": [],
            },
            "interaction": {
                "safe_user_feedback": "",
                "public_feedback_points": [],
                "user_simulator": {
                    "mode": "silent",
                    "tone": "neutral",
                    "skip_reason": "supervisor-error",
                    "error": "",
                },
            },
            "components": {},
            "runtime": {
                "transport": "",
                "elapsed_ms": 0,
                "image_inputs": [],
            },
        }
        payload = {
            "overall_score": 0.0,
            "score_cap": 1.0,
            "capped_score": 0.0,
            "verdict": _exc_verdict,
            "attempt_state": _exc_attempt_state,
            "recoverable": False,
            "confidence": "medium",
            "error": f"supervisor failure: {exc}",
            "safe_user_feedback": "",
            "missing_artifacts": [],
            "guidance_tags": [],
            "user_simulator_mode": "silent",
            "user_simulator_tone": "neutral",
            "user_simulator_skip_reason": "supervisor-error",
            "public_feedback_points": [],
            "followups_used": max(0, turn - 1),
            "remaining_followups": max(0, int(task.codex.max_user_followups) - max(0, turn - 1)),
            "followup_budget_exhausted": max(0, int(task.codex.max_user_followups) - max(0, turn - 1)) <= 0,
            "evaluation_index": turn,
            "supervision_transport": "",
            "supervision_elapsed_ms": 0,
            "decision_schema_version": str(structured_decision.get("schema_version") or ""),
            "supervision_decision": structured_decision,
        }
        if supervisor_rate_limited:
            payload["rate_limit"] = True
            payload["rate_limit_type"] = infra_error["type"]
            payload["rate_limit_source"] = "supervisor"
        elif infra_error:
            payload["infra_error"] = True
            payload["infra_error_type"] = infra_error["type"]
        cycle_dir.mkdir(parents=True, exist_ok=True)
        write_local(cycle_dir / "decision.json", json.dumps(structured_decision, ensure_ascii=False, indent=2) + "\n")
        append_jsonl(
            out_dir / "supervision_trace.jsonl",
            {
                "evaluation_index": turn,
                "stage_id": "primary",
                "stage_type": "primary",
                "timestamp_ms": int(time.time() * 1000),
                "verdict": payload["verdict"],
                "attempt_state": _exc_attempt_state,
                "recoverable": False,
                "score": payload["overall_score"],
                "confidence": "medium",
                "rationale": str(payload.get("error") or ""),
                "missing_artifacts": [],
                "guidance_tags": [],
                "safe_user_feedback": "",
                "user_simulator_mode": "silent",
                "user_simulator_tone": "neutral",
                "user_simulator_skip_reason": "supervisor-error",
                "public_feedback_points": [],
                "followups_used": payload["followups_used"],
                "remaining_followups": payload["remaining_followups"],
                "followup_budget_exhausted": payload["followup_budget_exhausted"],
                "transport": "",
                "elapsed_ms": 0,
                "cycle_dir": str(cycle_dir.relative_to(out_dir)),
                "error": str(payload.get("error") or ""),
                "decision_schema_version": payload["decision_schema_version"],
                "supervision_decision": structured_decision,
            },
        )
        append_text(out_dir / "supervision.log", f"[cycle {turn:02d}] {type(exc).__name__}: {exc}\n")
    write_score_json(out_dir, task, payload)
    return payload


def continuation_decision(task: TaskSpec, score: dict, transcript_text: str, continuation_index: int) -> dict:
    agent_sys = normalize_agent_sys(task.agent_sys)
    error = str(score.get("error") or "")
    transcript_available = bool(transcript_text.strip())
    # Same primary-agent filter as apply_executor_completion_gate — for
    # multi-agent edict runs we only trust the primary agent (taizi) as a
    # completion signal; other backends skip the filter.
    _primary_agent_for_completion = (
        effective_agent_id_for_task(task)
        if agent_sys == "openclaw_edict"
        else ""
    )
    assistant_completion = (
        assistant_signaled_completion(transcript_text, primary_agent_id=_primary_agent_for_completion)
        if transcript_available
        else False
    )
    verdict = str(score.get("verdict") or "")
    raw_supervisor_verdict = str(score.get("supervisor_verdict_raw") or verdict)
    structured_decision = dict(score.get("supervision_decision") or {})
    structured_decision_payload = dict(structured_decision.get("decision") or {})
    decision = {
        "index": continuation_index + 1,
        "backend": agent_sys,
        "currentScore": float(score.get("overall_score", 0.0) or 0.0),
        "finalCompletionScore": float(score.get("final_completion_score", 0.0) or 0.0),
        "scoreCap": float(score.get("score_cap", 1.0) or 1.0),
        "error": error,
        "transcriptAvailable": transcript_available,
        "assistantCompletionSignal": assistant_completion,
        "action": "stop",
        "reason": "",
        "verdict": verdict,
        "attemptState": str(score.get("attempt_state") or ""),
        "recoverable": bool(score.get("recoverable")),
        "safeUserFeedback": str(score.get("safe_user_feedback") or ""),
        "followupsUsed": continuation_index,
        "remainingFollowups": max(0, int(task.codex.max_user_followups) - continuation_index),
        "supervisionDecisionId": str(structured_decision.get("decision_id") or ""),
        "supervisorRequestedAction": str(structured_decision_payload.get("requested_action") or ""),
        "supervisorRequestedReason": str(structured_decision_payload.get("requested_reason") or ""),
        "rawSupervisorVerdict": raw_supervisor_verdict,
        "executorCompleted": bool(score.get("executor_completed")),
        "executorCompletionReason": str(score.get("executor_completion_reason") or ""),
    }
    if bool(score.get("completion_gate_failed")):
        decision["reason"] = str(score.get("completion_gate_reason") or "executor-incomplete")
        return decision
    if verdict == "pass":
        decision["reason"] = "supervisor-pass"
        return decision
    if verdict == "infra_error" or score.get("infra_error"):
        decision["reason"] = str(score.get("infra_error_type") or verdict or "supervisor-stop")
        return decision
    if verdict == "rate_limit" or score.get("rate_limit"):
        # Peer of infra_error: upstream provider threw 429 before the
        # model could reason. Stop like infra_error; the WebUI
        # surfaces these differently (see statusLabel/verdictLabel).
        decision["reason"] = str(score.get("rate_limit_type") or verdict or "supervisor-stop")
        return decision
    if verdict == "fail" and not bool(score.get("recoverable")):
        decision["reason"] = str(score.get("infra_error_type") or verdict or "supervisor-stop")
        return decision
    if continuation_index >= max(0, int(task.codex.max_user_followups)):
        decision["reason"] = "followup-limit-reached"
        return decision
    if not str(score.get("safe_user_feedback") or "").strip():
        decision["reason"] = "empty-safe-feedback"
        return decision
    decision["action"] = "continue"
    decision["reason"] = "supervisor-requested-followup-after-assistant-completion" if assistant_completion else "supervisor-requested-followup"
    return decision
