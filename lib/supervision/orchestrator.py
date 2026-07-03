#!/usr/bin/env python3
from __future__ import annotations

import time
import uuid
from typing import Any

from .answer_supervisor import run_answer_supervisor
from .feedback_rewriter import rewrite_feedback
from ..i18n import (
    KEEP_GOING_FOR_MORE_EVIDENCE,
    guidance_tag_public_hint,
    public_feedback_summary,
)
from .common import (
    AttemptSupervisorContext,
    SupervisorContext,
    TaskSupervisorContext,
    clamp_score,
    redacted_supervision_context,
)
from ..constants import SUPERVISION_DECISION_SCHEMA
from ..i18n import contains_cjk as _contains_cjk
from ..util.dedup import dedupe_lines as _dedupe_text_items
from .user_simulator import run_public_user_simulator


# ── Round 9 / A3 — user simulator failure classification ─────────────


def _classify_user_simulator_error(message: str) -> str:
    """Categorize a user-simulator exception message into one of
    timeout / rate_limit / runtime / unknown so the trace + summary
    can surface "what broke" without dumping the raw error.

    Mirrors the categorization in lib.runner.errors.detect_supervisor_infra_error
    but kept simple here since user-simulator failures are non-fatal
    (we always have the fallback feedback path)."""
    needle = (message or "").lower()
    if not needle:
        return "unknown"
    if any(t in needle for t in (
        "rate_limit", "rate limit", "rate-limited", "rate_limited",
        "429", "too many requests", "throttl",
        "quota exceeded", "insufficient_quota",
    )):
        return "rate_limit"
    if any(t in needle for t in (
        "timeout", "timed out", "deadline exceeded",
    )):
        return "timeout"
    if any(t in needle for t in (
        "runtime", "exception", "traceback", "valueerror",
        "typeerror", "keyerror", "subprocess",
    )):
        return "runtime"
    return "unknown"


def _sanitize_user_simulator_error(message: str) -> str:
    """Strip absolute paths + long base64 blobs + privacy-shaped values
    from a user-simulator exception message before persisting it to the
    supervision trace.  Reuses content.sanitize_codex_context_text for
    the path/blob redaction, then clamps the result so a runaway stack
    trace doesn't bloat the trace row."""
    from .content import sanitize_codex_context_text
    cleaned = sanitize_codex_context_text(str(message or ""))
    return cleaned[:600]


def build_public_feedback(public_task: str, answer: dict[str, Any]) -> dict[str, Any]:
    zh = _contains_cjk(public_task)
    verdict = str(answer.get("verdict") or "fail")
    attempt_state = str(answer.get("attempt_state") or "terminal_failure")
    requested_reason = _supervisor_reason(verdict, attempt_state)
    summary = public_feedback_summary(requested_reason, zh=zh)

    points: list[str] = []
    for tag in list(answer.get("guidance_tags") or []):
        hint = guidance_tag_public_hint(str(tag or ""), zh=zh)
        if hint:
            points.append(hint)
    if verdict == "continue" and attempt_state == "in_progress":
        points.append(KEEP_GOING_FOR_MORE_EVIDENCE["zh" if zh else "en"])
    points = _dedupe_text_items(points)[:4]
    return {
        "verdict": verdict,
        "attempt_state": attempt_state,
        "requested_reason": requested_reason,
        "public_summary": summary,
        "public_feedback_points": points,
    }


def _component_debug(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return dict(payload.get("_debug", {}) or {})


def _normalize_answer_decision(context: SupervisorContext, answer: dict[str, Any]) -> dict[str, Any]:
    """Normalise an answer-supervisor payload into the run-loop's contract.

    Supervisor verdict back-compat note (Phase 7):
        The current supervisor prompt narrows the model's allowed verdicts to
        ``pass / continue / fail`` (see ``lib/templates/answer_supervisor.py``
        and ``lib/status.py:SUPERVISOR_VERDICT_STATES``). The ``infra_error``
        and ``rate_limit`` branches below are kept ONLY for two compatibility
        reasons:
          1. Reading legacy artifacts that pre-date Round 6.
          2. Internal synth paths in ``lib/runner/orchestration.py``
             (``structured_rate_limit_score`` / ``structured_runtime_error_score``)
             that write a synthesised score payload carrying ``verdict``
             values of ``"rate_limit"`` / ``"infra_error"`` so downstream
             code can still distinguish framework infra states without a
             special schema.
        Do NOT re-introduce these verdicts into the supervisor prompt — the
        framework owns infra signalling. Adding them back here for the
        *model* would silently break the Round-6 narrowing.
    """
    normalized = dict(answer)
    verdict = str(normalized.get("verdict") or "fail")
    attempt_state = str(normalized.get("attempt_state") or "").strip().lower()
    followups_used = max(0, context.attempt.turn - 1)
    remaining_followups = max(0, int(context.task.max_user_followups) - followups_used)

    # Score-based promotion lives in ``lib/status.apply_score_based_promotion``
    # alone (the runtime-status path, invoked on terminal states like
    # ``budget_exhausted``/``global_timeout``). Do NOT override an explicit
    # supervisor verdict here: a high score with ``verdict=continue`` means
    # the supervisor wants the user simulator to issue another instruction,
    # not that the run should terminate as ``pass``.

    if verdict == "pass":
        normalized["attempt_state"] = "complete_and_passed"
        normalized["recoverable"] = False
        return normalized
    if verdict == "infra_error":
        normalized["attempt_state"] = "infra_error"
        normalized["recoverable"] = False
        return normalized
    if verdict == "rate_limit":
        normalized["attempt_state"] = "rate_limit"
        normalized["recoverable"] = False
        return normalized

    has_recovery_targets = bool(normalized.get("guidance_tags") or str(normalized.get("rationale") or "").strip())
    if verdict == "fail" and remaining_followups > 0 and (attempt_state == "complete_but_failed" or has_recovery_targets):
        normalized["verdict"] = "continue"
        normalized["attempt_state"] = attempt_state if attempt_state in {"in_progress", "incomplete", "complete_but_failed"} else "complete_but_failed"
        normalized["recoverable"] = True
        return normalized

    if verdict == "continue":
        normalized["attempt_state"] = attempt_state if attempt_state in {"in_progress", "incomplete", "complete_but_failed"} else "incomplete"
        normalized["recoverable"] = remaining_followups > 0
        return normalized

    normalized["attempt_state"] = attempt_state if attempt_state in {"complete_but_failed", "terminal_failure"} else "terminal_failure"
    normalized["recoverable"] = False
    return normalized


def _supervisor_reason(verdict: str, attempt_state: str) -> str:
    if verdict == "pass":
        return "evidence_sufficient"
    if verdict == "infra_error":
        return "infra_error"
    if verdict == "rate_limit":
        return "rate_limited"
    if verdict == "continue":
        if attempt_state == "in_progress":
            return "still_exploring"
        if attempt_state == "incomplete":
            return "missing_visible_evidence"
        if attempt_state == "complete_but_failed":
            return "answer_needs_repair"
        return "needs_more_work"
    if attempt_state == "complete_but_failed":
        return "completed_answer_not_supported"
    return "terminal_failure"


def _completion_class(attempt_state: str) -> str:
    if attempt_state == "in_progress":
        return "exploring"
    if attempt_state == "incomplete":
        return "partial"
    if attempt_state in {"complete_but_failed", "complete_and_passed"}:
        return "complete"
    if attempt_state == "infra_error":
        return "infra"
    if attempt_state == "rate_limit":
        return "rate_limit"
    return "terminal"


def _build_supervision_decision(
    context: SupervisorContext,
    payload: dict[str, Any],
    answer_component: dict[str, Any],
    user_component: dict[str, Any],
    feedback_component: dict[str, Any],
    *,
    user_error: str,
    elapsed_ms: int,
    transport: str,
    image_inputs: list[str],
) -> dict[str, Any]:
    verdict = str(payload.get("verdict") or "fail")
    attempt_state = str(payload.get("attempt_state") or "terminal_failure")
    recoverable = bool(payload.get("recoverable"))
    requested_action = "continue" if verdict == "continue" and recoverable else "stop"
    requested_reason = _supervisor_reason(verdict, attempt_state)
    followups_used = int(payload.get("followups_used") or 0)
    remaining_followups = int(payload.get("remaining_followups") or 0)
    budget_exhausted = bool(payload.get("followup_budget_exhausted"))
    return {
        "schema_version": SUPERVISION_DECISION_SCHEMA,
        "decision_id": f"sd-{context.attempt.turn:02d}-{uuid.uuid4().hex[:8]}",
        "task_id": context.task.task_id,
        "stage_id": "primary",
        "evaluation_index": context.attempt.turn,
        "attempt": {
            "turn": context.attempt.turn,
            "completion_class": _completion_class(attempt_state),
            "attempt_state": attempt_state,
            "followups_used": followups_used,
            "remaining_followups": remaining_followups,
            "max_user_followups": int(context.task.max_user_followups),
            "followup_budget_exhausted": budget_exhausted,
        },
        "decision": {
            "verdict": verdict,
            "requested_action": requested_action,
            "requested_reason": requested_reason,
            "recoverable": recoverable,
        },
        "scoring": {
            "raw_score": clamp_score(float(payload.get("score", 0.0) or 0.0)),
            "capped_score": 1.0 if verdict == "pass" else clamp_score(float(payload.get("score", 0.0) or 0.0)),
            "success_threshold": float(context.task.success_threshold),
        },
        "analysis": {
            "confidence": str(payload.get("confidence") or "medium"),
            "rationale": str(payload.get("rationale") or ""),
            "missing_artifacts": list(payload.get("missing_artifacts") or []),
            "guidance_tags": list(payload.get("guidance_tags") or []),
        },
        "interaction": {
            "safe_user_feedback": str(payload.get("safe_user_feedback") or ""),
            "public_feedback_summary": str(payload.get("public_feedback_summary") or ""),
            "public_feedback_points": list(payload.get("public_feedback_points") or []),
            "user_simulator": {
                "mode": str(payload.get("user_simulator_mode") or "silent"),
                "tone": str(payload.get("user_simulator_tone") or "neutral"),
                "skip_reason": str(payload.get("user_simulator_skip_reason") or ""),
                "error": user_error,
            },
        },
        "components": {
            "answer_supervisor": dict(answer_component.get("decision") or {}),
            "public_user_simulator": dict(user_component.get("decision") or {}),
            "feedback_rewriter": dict(feedback_component.get("decision") or {}),
        },
        "runtime": {
            "transport": transport,
            "elapsed_ms": elapsed_ms,
            "image_inputs": list(image_inputs or []),
        },
    }


def run_supervisor(context: SupervisorContext) -> dict[str, Any]:
    # Per-role wall-clock windows, used later by runner.py to time-slice
    # the proxy adapter log and attribute codex-side token usage to the
    # right role (supervisor vs user_simulator). Since the two roles run
    # strictly sequentially here, a half-open [start_ts, end_ts) window
    # around each call uniquely identifies its usage events.
    supervisor_window = {"start_ts": time.time()}
    answer = _normalize_answer_decision(context, run_answer_supervisor(context))
    supervisor_window["end_ts"] = time.time()
    answer_debug = _component_debug(answer)
    public_feedback = build_public_feedback(context.task.public_task, answer)
    user_handoff = {
        "verdict": str(answer.get("verdict") or "fail"),
        "attempt_state": str(answer.get("attempt_state") or "terminal_failure"),
        "recoverable": bool(answer.get("recoverable")),
        "score": clamp_score(float(answer.get("score", 0.0) or 0.0)),
    }

    public_user: dict[str, Any] = {
        "mode": "silent",
        "tone": "neutral",
        "candidate_feedback": "",
        "public_feedback_points": [],
        "skip_reason": "",
    }
    user_error = ""
    user_simulator_window: dict[str, Any] = {}
    # Round 9 / A3: track whether the user_simulator raised so the
    # supervision trace can surface fallback transparency to operators.
    user_simulator_failed = False
    user_simulator_error_type = ""
    user_simulator_error_message_sanitized = ""
    verdict = str(answer.get("verdict") or "")
    recoverable = bool(answer.get("recoverable"))
    if verdict == "continue" and recoverable:
        try:
            user_simulator_window["start_ts"] = time.time()
            public_user = run_public_user_simulator(context, user_handoff)
            user_simulator_window["end_ts"] = time.time()
        except Exception as exc:
            user_error = str(exc)
            user_simulator_window["end_ts"] = time.time()
            user_simulator_window["error"] = str(exc)
            user_simulator_failed = True
            user_simulator_error_type = _classify_user_simulator_error(user_error)
            user_simulator_error_message_sanitized = _sanitize_user_simulator_error(user_error)
    else:
        if verdict:
            public_user["skip_reason"] = f"verdict={verdict}"
        else:
            public_user["skip_reason"] = "no-verdict"
    user_debug = _component_debug(public_user)

    rewritten = rewrite_feedback(
        context,
        user_handoff,
        public_user,
        guidance_tags=list(answer.get("guidance_tags") or []),
    )
    feedback_debug = dict(rewritten.get("_debug", {}) or {})
    # Round 9 / A3: feedback_rewriter publishes fallback_feedback_used
    # / fallback_source flags in _debug so the trace can record whether
    # the safe_user_feedback came from real model output or the i18n
    # fallback template.
    fallback_feedback_used = bool(feedback_debug.get("fallback_feedback_used"))
    fallback_source = str(feedback_debug.get("fallback_source") or "")

    verdict = str(answer.get("verdict") or "fail")
    safe_user_feedback = str(rewritten.get("safe_user_feedback") or "")

    total_elapsed_ms = int(answer_debug.get("elapsed_ms") or 0) + int(user_debug.get("elapsed_ms") or 0)
    followups_used = max(0, context.attempt.turn - 1)
    remaining_followups = max(0, int(context.task.max_user_followups) - followups_used)
    payload = {
        "verdict": verdict,
        "attempt_state": str(answer.get("attempt_state") or "terminal_failure"),
        "recoverable": recoverable,
        "score": clamp_score(float(answer.get("score", 0.0) or 0.0)),
        "confidence": str(answer.get("confidence") or "medium"),
        "rationale": str(answer.get("rationale") or ""),
        "missing_artifacts": list(answer.get("missing_artifacts") or []),
        "guidance_tags": list(answer.get("guidance_tags") or []),
        "public_feedback_summary": str(public_feedback.get("public_summary") or ""),
        "safe_user_feedback": safe_user_feedback,
        "safe_user_feedback_mode": str(feedback_debug.get("feedback_mode") or ""),
        "user_simulator_mode": str(public_user.get("mode") or "silent"),
        "user_simulator_tone": str(public_user.get("tone") or "neutral"),
        "user_simulator_skip_reason": str(public_user.get("skip_reason") or ""),
        # Round 9 / A3 — fallback transparency.  These four fields let
        # operators see WHY the user_simulator didn't run (raised /
        # was skipped) and whether the resulting safe_user_feedback
        # came from real model output or the i18n boilerplate fallback.
        "user_simulator_failed": user_simulator_failed,
        "user_simulator_error_type": user_simulator_error_type,
        "user_simulator_error_message_sanitized": user_simulator_error_message_sanitized,
        "fallback_feedback_used": fallback_feedback_used,
        "fallback_source": fallback_source,
        "public_feedback_points": list(public_feedback.get("public_feedback_points") or []),
        "followups_used": followups_used,
        "remaining_followups": remaining_followups,
        "followup_budget_exhausted": remaining_followups <= 0,
    }
    payload["_debug"] = {
        "transport": str(answer_debug.get("transport") or ""),
        "elapsed_ms": total_elapsed_ms,
        "answer_supervisor": {
            **answer_debug,
            "decision": {
                "verdict": payload["verdict"],
                "attempt_state": payload["attempt_state"],
                "recoverable": payload["recoverable"],
                "score": payload["score"],
                "confidence": payload["confidence"],
                "rationale": payload["rationale"],
                "missing_artifacts": payload["missing_artifacts"],
                "guidance_tags": payload["guidance_tags"],
            },
        },
        "public_user_simulator": {
            **user_debug,
            "decision": {
                "mode": payload["user_simulator_mode"],
                "tone": payload["user_simulator_tone"],
                "candidate_feedback": str(public_user.get("candidate_feedback") or ""),
                "public_feedback_points": list(public_user.get("public_feedback_points") or []),
                "skip_reason": str(public_user.get("skip_reason") or ""),
                "error": user_error,
            },
        },
        "feedback_rewriter": {
            **feedback_debug,
            "decision": {
                "safe_user_feedback": safe_user_feedback,
                "feedback_mode": str(feedback_debug.get("feedback_mode") or ""),
                "applied_guidance_tags": list(feedback_debug.get("applied_guidance_tags") or []),
                "template_lines": list(feedback_debug.get("template_lines") or []),
                "used_candidate_feedback": bool(feedback_debug.get("used_candidate_feedback")),
                "used_public_feedback_points": bool(feedback_debug.get("used_public_feedback_points")),
                "language": str(feedback_debug.get("language") or ""),
            },
        },
        "image_inputs": list(answer_debug.get("image_inputs") or []),
        # Surface the per-role wall-clock windows so the caller
        # (``runner.evaluate_attempt``) can slice the proxy adapter log
        # for each role's token usage without having to time the calls
        # from outside (which would force the timing to span the whole
        # ``run_supervisor`` call, lumping supervisor + user_simulator
        # events together).
        "usage_windows": {
            "supervisor": dict(supervisor_window),
            "user_simulator": dict(user_simulator_window),
        },
    }
    payload["supervision_decision"] = _build_supervision_decision(
        context,
        payload,
        answer_component=dict(payload["_debug"].get("answer_supervisor") or {}),
        user_component=dict(payload["_debug"].get("public_user_simulator") or {}),
        feedback_component=dict(payload["_debug"].get("feedback_rewriter") or {}),
        user_error=user_error,
        elapsed_ms=total_elapsed_ms,
        transport=str(answer_debug.get("transport") or ""),
        image_inputs=list(answer_debug.get("image_inputs") or []),
    )
    return payload


__all__ = [
    "AttemptSupervisorContext",
    "SupervisorContext",
    "TaskSupervisorContext",
    "clamp_score",
    "redacted_supervision_context",
    "run_supervisor",
]
