"""Centralized zh/en text tables and accessors used by supervisor / feedback_rewriter.

This module owns every user-facing string that needs a zh+en pair:

- ``GUIDANCE_TAG_PUBLIC_HINTS`` — per-guidance-tag public hint lines
- ``PUBLIC_FEEDBACK_SUMMARY`` — supervisor public-feedback summary keyed by
  ``requested_reason``
- ``FALLBACK_FEEDBACK`` — feedback_rewriter fallback lines keyed by attempt
  state / verdict
- ``KEEP_GOING_FOR_MORE_EVIDENCE`` — the single "keep going" line appended
  when the supervisor verdict is ``continue`` and the attempt_state is
  ``in_progress``

Also hosts the tiny ``contains_cjk`` predicate (formerly in
``lib/text_utils.py``, folded in here in Phase 5) — i18n is the only
caller domain and a one-function file added clutter.

Keep all translatable strings here so a future contributor can add a new
language by extending one file only.
"""

from __future__ import annotations

import re
from typing import Any


def contains_cjk(text: str) -> bool:
    """Return True if *text* contains any CJK Unified Ideograph.

    Used by feedback_rewriter / orchestrator to decide whether to render
    zh or en strings from the tables below.
    """
    return bool(re.search(r"[㐀-鿿]", text or ""))


# ── Guidance-tag public hints ─────────────────────────────────────────
GUIDANCE_TAG_PUBLIC_HINTS: dict[str, dict[str, str]] = {
    "follow_public_task": {
        "zh": "请继续按原始任务要求核对，不要偏离当前目标。",
        "en": "Keep following the original public request without drifting.",
    },
    "keep_query_literal": {
        "zh": "请继续沿用原始搜索词，不要改写问题。",
        "en": "Keep using the original search query.",
    },
    "open_ranked_first_result": {
        "zh": "请继续沿着当前排序规则核对目标结果。",
        "en": "Keep following the requested ranking when checking the target result.",
    },
    "save_visible_evidence": {
        "zh": "请把关键证据及时保存下来。",
        "en": "Save the key visible evidence as you go.",
    },
    "save_supporting_screenshot": {
        "zh": "请保存一张能直接支撑结论的清晰截图。",
        "en": "Save a clear screenshot that directly supports the conclusion.",
    },
    "use_only_visible_evidence": {
        "zh": "请只根据页面上现在能直接看到的内容来判断。",
        "en": "Base the answer only on what is directly visible on the page.",
    },
    "verify_evidence_matches_conclusion": {
        "zh": "请确认保存的证据和最终结论是匹配一致的。",
        "en": "Make sure the saved evidence actually matches and supports the conclusion.",
    },
    "check_correct_source_page": {
        "zh": "请确认你当前打开的是正确的来源页面。",
        "en": "Check that you are on the correct source page for this task.",
    },
    "record_observable_conclusion": {
        "zh": "请把最后能确认的结论整理清楚并保存下来。",
        "en": "Write down the final conclusion once it is supported by visible evidence.",
    },
    "do_not_claim_completion": {
        "zh": "如果证据还不够，请先继续核对，不要过早结束。",
        "en": "If the evidence is still incomplete, keep checking instead of ending early.",
    },
    "credential_hygiene": {
        "zh": "请继续注意隐私，不要把密码或其他敏感值写进结果、命令行或截图里。",
        "en": "Keep credential hygiene: do not place passwords or other secrets into results, command lines, or screenshots.",
    },
}

# Enum-style frozenset derived from the hints table. Importing from here
# avoids an import cycle through lib.constants.
GUIDANCE_TAGS = frozenset(GUIDANCE_TAG_PUBLIC_HINTS)


def guidance_tag_public_hint(tag: str, *, zh: bool) -> str:
    """Return the localized public hint for a guidance tag, or "" if unknown."""
    entry = GUIDANCE_TAG_PUBLIC_HINTS.get(str(tag or "").strip())
    if not entry:
        return ""
    return str(entry["zh" if zh else "en"])


# ── Public-feedback summary (supervisor → public_feedback_summary) ────
# Key = requested_reason produced by supervisor._supervisor_reason().
PUBLIC_FEEDBACK_SUMMARY: dict[str, dict[str, str]] = {
    "still_exploring": {
        "zh": "当前还在执行中，还没有形成可以结束的最终结论。",
        "en": "The run is still in progress and has not reached a final conclusion yet.",
    },
    "missing_visible_evidence": {
        "zh": "当前还缺少能直接支撑结论的可见证据。",
        "en": "There is still not enough visible evidence to support the current conclusion.",
    },
    "answer_needs_repair": {
        "zh": "当前结论和现有可见证据还没有完全对上，需要重新核对。",
        "en": "The current conclusion still does not line up with the visible evidence.",
    },
    "completed_answer_not_supported": {
        "zh": "当前给出的结论仍然缺少足够的可见支撑。",
        "en": "The current conclusion still lacks enough visible support.",
    },
    "terminal_failure": {
        "zh": "当前这轮已经不能支持正确完成任务。",
        "en": "This run can no longer support a correct completion.",
    },
    "infra_error": {
        "zh": "这轮监督或运行过程中出现了系统错误。",
        "en": "A system error happened during execution or supervision.",
    },
    "rate_limited": {
        "zh": "这轮被上游模型服务商限流（429），调用未能完成。",
        "en": "The upstream model provider rate-limited this run (HTTP 429) before the call could complete.",
    },
    "evidence_sufficient": {
        "zh": "当前可见证据已经足够支持结论。",
        "en": "The visible evidence is sufficient to support the conclusion.",
    },
    "needs_more_work": {
        "zh": "当前还需要继续核对。",
        "en": "More checking is still needed.",
    },
}


def public_feedback_summary(reason: str, *, zh: bool) -> str:
    """Return the localized public-feedback summary for a supervisor reason.

    Unknown reasons fall back to the ``needs_more_work`` entry to match the
    original supervisor.build_public_feedback() default.
    """
    entry = PUBLIC_FEEDBACK_SUMMARY.get(str(reason or "")) or PUBLIC_FEEDBACK_SUMMARY["needs_more_work"]
    return str(entry["zh" if zh else "en"])


# Extra "keep going" line appended by build_public_feedback() when the
# supervisor verdict is continue and attempt_state is in_progress.
KEEP_GOING_FOR_MORE_EVIDENCE: dict[str, str] = {
    "zh": "请继续当前流程，等看到更直接的证据后再下最终结论。",
    "en": "Keep going and wait for more direct evidence before making the final conclusion.",
}


# ── Feedback-rewriter fallback lines ──────────────────────────────────
# Keyed (lang, branch) where branch follows the original if-chain:
#   attempt_state == "complete_but_failed"  → "complete_but_failed"
#   attempt_state == "incomplete"           → "incomplete"
#   verdict == "continue"                   → "verdict_continue"
#   otherwise                               → "default"
FALLBACK_FEEDBACK: dict[str, dict[str, str]] = {
    "zh": {
        "complete_but_failed": "继续完成当前任务，并根据你已经看到的页面和截图重新核对当前结论。",
        "incomplete": "继续完成当前任务，并补齐还缺的可见证据后再下结论。",
        "verdict_continue": "继续完成当前任务，并根据当前页面和截图继续核对。",
        "default": "继续完成当前任务，并根据当前可见证据再检查一遍你的选择。",
    },
    "en": {
        "complete_but_failed": "Continue the current task and re-check your current conclusion against the visible evidence you already have.",
        "incomplete": "Continue the current task and fill in the missing visible evidence before making the final conclusion.",
        "verdict_continue": "Continue the current task and keep checking it against the current page state and saved evidence.",
        "default": "Continue the current task and re-check your current choice against the visible evidence.",
    },
}


def fallback_feedback_text(user_handoff: dict[str, Any], *, zh: bool) -> str:
    """Return the localized fallback feedback line for a supervisor handoff.

    Preserves the exact branch order of the original
    feedback_rewriter.fallback_feedback() function so the output is
    byte-identical.
    """
    lang = "zh" if zh else "en"
    table = FALLBACK_FEEDBACK[lang]
    attempt_state = str(user_handoff.get("attempt_state") or "")
    verdict = str(user_handoff.get("verdict") or "")
    if attempt_state == "complete_but_failed":
        return table["complete_but_failed"]
    if attempt_state == "incomplete":
        return table["incomplete"]
    if verdict == "continue":
        return table["verdict_continue"]
    return table["default"]


__all__ = [
    "GUIDANCE_TAG_PUBLIC_HINTS",
    "GUIDANCE_TAGS",
    "guidance_tag_public_hint",
    "PUBLIC_FEEDBACK_SUMMARY",
    "public_feedback_summary",
    "KEEP_GOING_FOR_MORE_EVIDENCE",
    "FALLBACK_FEEDBACK",
    "fallback_feedback_text",
]
