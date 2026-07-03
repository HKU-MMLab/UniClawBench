#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

from ..constants import (
    SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY,
    is_completion_text,
    normalize_safe_user_feedback_mode,
)
from ..i18n import fallback_feedback_text, guidance_tag_public_hint
from .common import SupervisorContext
from ..i18n import contains_cjk


def split_candidate_lines(text: str) -> list[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    chunks = [part.strip(" \t-•") for part in re.split(r"[\r\n]+", raw) if part.strip()]
    if len(chunks) <= 1:
        chunks = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s+", raw) if part.strip()]
    return [part for part in chunks if part]


def is_completion_line(text: str) -> bool:
    """Return True if ``text`` is a pure completion acknowledgment line.

    Delegates to ``lib.constants.is_completion_text`` so that the canonical
    list of completion phrases lives in one place.
    """
    return is_completion_text(text)


# Re-exported under the original public name for backwards compat.
# New callers should import ``fuzzy_dedupe_lines`` from ``lib.util.dedup``
# directly — the renamed form is what makes the substring-aware
# semantics legible at the call site.
from ..util.dedup import fuzzy_dedupe_lines as dedupe_lines  # noqa: E402,F401


def fallback_feedback(user_handoff: dict[str, Any], *, zh: bool) -> str:
    """Thin wrapper around lib.i18n.fallback_feedback_text.

    Kept here for internal call-site stability; delegates to the
    centralized i18n table in ``lib/i18n.py``.
    """
    return fallback_feedback_text(user_handoff, zh=zh)


def rewrite_feedback(
    context: SupervisorContext,
    user_handoff: dict[str, Any],
    public_user: dict[str, Any] | None,
    *,
    guidance_tags: list[str] | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    verdict = str(user_handoff.get("verdict") or "")
    zh = contains_cjk(context.task.public_task)
    feedback_mode = normalize_safe_user_feedback_mode(mode)
    if verdict != "continue":
        payload = {
            "safe_user_feedback": "",
            "template_lines": [],
            "applied_guidance_tags": [],
            "used_candidate_feedback": False,
            "used_public_feedback_points": False,
            "feedback_mode": feedback_mode,
            "language": "zh" if zh else "en",
        }
        payload["_debug"] = dict(payload)
        return payload

    candidate_lines = [
        line
        for line in split_candidate_lines(str((public_user or {}).get("candidate_feedback") or ""))
        if not is_completion_line(line)
    ]
    public_points = [
        str(item or "").strip()
        for item in (public_user or {}).get("public_feedback_points") or []
        if str(item or "").strip()
    ]
    guidance_entries: list[tuple[str, str]] = []
    for tag in guidance_tags or []:
        hint = guidance_tag_public_hint(tag, zh=zh)
        if not hint:
            continue
        guidance_entries.append((str(tag), hint))
    guidance_lines = [hint for _, hint in guidance_entries]

    if feedback_mode == SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY:
        lines = dedupe_lines(candidate_lines)
    else:
        lines = dedupe_lines([*candidate_lines, *public_points, *guidance_lines])
    # Round 9 / A3 — fallback source classification.
    # Track whether we hit the i18n generic fallback (no real model
    # signal made it through) so the supervision trace can surface
    # this to operators.  Order of preference for source attribution:
    #   - candidate_feedback present → user_simulator (real model output)
    #   - public_feedback_points present → missing_artifacts
    #   - guidance_lines present → guidance_tags
    #   - none of the above → generic
    fallback_feedback_used = False
    if not lines:
        lines = [fallback_feedback(user_handoff, zh=zh)]
        fallback_feedback_used = True
        fallback_source = "generic"
    else:
        # We have real lines; figure out which signal kept us off the
        # fallback path.  Used for trace-level transparency.
        if candidate_lines:
            fallback_source = "user_simulator"
        elif public_points:
            fallback_source = "missing_artifacts"
        elif guidance_lines:
            fallback_source = "guidance_tags"
        else:
            fallback_source = "generic"

    template_lines = lines[:3]
    safe_user_feedback = "\n".join(template_lines).strip()
    used_candidate_feedback = any(line in template_lines for line in candidate_lines)
    used_public_feedback_points = feedback_mode != SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY and any(
        line in template_lines for line in public_points
    )
    applied_guidance_tags = (
        [tag for tag, hint in guidance_entries if hint in template_lines]
        if feedback_mode != SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY
        else []
    )
    payload = {
        "safe_user_feedback": safe_user_feedback,
        "template_lines": template_lines,
        "applied_guidance_tags": applied_guidance_tags,
        "used_candidate_feedback": used_candidate_feedback,
        "used_public_feedback_points": used_public_feedback_points,
        "feedback_mode": feedback_mode,
        "language": "zh" if zh else "en",
        "fallback_feedback_used": fallback_feedback_used,
        "fallback_source": fallback_source,
    }
    payload["_debug"] = dict(payload)
    return payload
