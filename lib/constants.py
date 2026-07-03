"""Centralized constants and enumerations for Clawbench.

This module is the single home for every enum-like value set, completion
marker, schema version, and feedback-mode knob. Prompt text lives in
``lib/templates/*.py`` and translatable strings live in ``lib/i18n.py``.

Keep this module a leaf — it should not import from any other ``lib.*``
module so downstream modules can depend on it without cycle risk.
"""

from __future__ import annotations

import re


# ── Verdicts ──────────────────────────────────────────────────────
# Round-6 narrowing: the supervisor model only judges TASK SEMANTICS
# (did the agent succeed, should the user say more, is it terminally
# wrong).  Framework-runtime states like ``rate_limit`` and
# ``infra_error`` are detected by the framework from external signals
# (HTTP 429 from the upstream provider, container lifecycle errors,
# supervisor-invocation crashes) and written to score.json directly by
# ``structured_runtime_error_score`` / ``structured_rate_limit_score``
# in ``lib/runner/orchestration.py`` — not by the supervisor model.
#
# ``LEGACY_VERDICTS`` keeps the pre-Round-6 superset so the validator
# can RECOGNISE old supervisor outputs and normalise them to the
# narrowed set via ``lib.status.normalize_supervisor_verdict`` (which
# maps ``infra_error`` / ``rate_limit`` → ``fail``: semantically the
# attempt did not reach pass).  Reading old score.json files works
# unchanged thanks to that normaliser.
VERDICTS = frozenset({"pass", "continue", "fail"})
LEGACY_VERDICTS = frozenset({"pass", "continue", "fail", "infra_error", "rate_limit"})

# ── Attempt states ────────────────────────────────────────────────
# Same narrowing applies: ``infra_error`` / ``rate_limit`` removed from
# the supervisor's allowed attempt_state values.  The framework synth
# scores still write ``attempt_state=infra_error`` / ``rate_limit``
# directly to score.json (they bypass the validator), so readers must
# tolerate those legacy values — ``LEGACY_ATTEMPT_STATES`` is the
# tolerant superset, ``ATTEMPT_STATES`` is the strict supervisor-model
# enum.
ATTEMPT_STATES = frozenset({
    "in_progress",
    "incomplete",
    "complete_but_failed",
    "complete_and_passed",
    "terminal_failure",
})
LEGACY_ATTEMPT_STATES = frozenset({
    "in_progress",
    "incomplete",
    "complete_but_failed",
    "complete_and_passed",
    "terminal_failure",
    "infra_error",
    "rate_limit",
})

# ── Supervisor confidence levels ──────────────────────────────────
CONFIDENCE_LEVELS = {"low", "medium", "high"}

# ── User simulator modes and tones ───────────────────────────────
USER_SIMULATOR_MODES = {"silent", "nudge", "instruction"}
USER_SIMULATOR_TONES = {"neutral", "firm", "urgent"}

# ── Executor completion markers ──────────────────────────────────
# Canonical list of normalized completion phrases. Used for both
# ``is_completion_text()`` strict-equality checks (feedback_rewriter)
# and ``variant in normalized`` substring checks (runner).
CONTINUATION_DONE_MARKER = "I have finished the request"
CONTINUATION_DONE_VARIANTS: tuple[str, ...] = (
    "i have finished the request",
    "i finished the request",
    "i have completed the request",
    "i completed the request",
    "the request is finished",
    "the request is complete",
    "the task is complete",
    "task complete",
    "task is complete",
    "task is done",
    "done",
    "completed",
    "already complete",
    "appears complete",
    "all required files have been created",
    "已完成",
    "已经完成",
    "任务完成",
)

_COMPLETION_TEXT_WHITESPACE_RE = re.compile(r"\s+")


def is_completion_text(text: str) -> bool:
    """Return True if ``text`` is equal to one of the completion variants.

    Normalizes by lowercasing, collapsing whitespace, and stripping
    boundary punctuation (English + CJK) before comparing.
    """
    value = _COMPLETION_TEXT_WHITESPACE_RE.sub(" ", str(text or "").strip().lower())
    value = value.strip(" .!?:;。！？")
    return value in CONTINUATION_DONE_VARIANTS


# ── Supervision decision schema version ──────────────────────────
SUPERVISION_DECISION_SCHEMA = "clawbench.supervision_decision/v1"


# ── safe_user_feedback mode enum and default ─────────────────────
# The feedback rewriter can compose ``safe_user_feedback`` in two ways:
#   CANDIDATE_ONLY — only the user-simulator's candidate_feedback is used
#   COMPOSED       — candidate + public_feedback_points + guidance_tag hints
# ``SAFE_USER_FEEDBACK_MODE`` is the run-wide default; flipping it here
# changes the default mode for every task that does not override it.
SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY = "candidate_only"
SAFE_USER_FEEDBACK_MODE_COMPOSED = "composed"
SAFE_USER_FEEDBACK_MODES = frozenset(
    {
        SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY,
        SAFE_USER_FEEDBACK_MODE_COMPOSED,
    }
)
SAFE_USER_FEEDBACK_MODE = SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY


def normalize_safe_user_feedback_mode(mode: str | None = None) -> str:
    """Normalize any incoming mode string to a valid enum member.

    Unknown values fall through to ``SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY``.
    """
    value = str(mode or SAFE_USER_FEEDBACK_MODE).strip().lower()
    if value not in SAFE_USER_FEEDBACK_MODES:
        return SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY
    return value


__all__ = [
    "VERDICTS",
    "LEGACY_VERDICTS",
    "ATTEMPT_STATES",
    "LEGACY_ATTEMPT_STATES",
    "CONFIDENCE_LEVELS",
    "USER_SIMULATOR_MODES",
    "USER_SIMULATOR_TONES",
    "CONTINUATION_DONE_MARKER",
    "CONTINUATION_DONE_VARIANTS",
    "is_completion_text",
    "SUPERVISION_DECISION_SCHEMA",
    "SAFE_USER_FEEDBACK_MODE",
    "SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY",
    "SAFE_USER_FEEDBACK_MODE_COMPOSED",
    "SAFE_USER_FEEDBACK_MODES",
    "normalize_safe_user_feedback_mode",
]
