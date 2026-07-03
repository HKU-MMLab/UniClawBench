"""Backend-specific executor-completion relaxation strategies.

``executor_completion_state`` (in ``lib/runner/evaluation.py``) classifies an
executor turn as completed/incomplete from the transcript. Most of that logic
is backend-agnostic — API stop reason, lingering tool calls, text completion
markers. Two pieces, however, are inherently backend-specific:

  - **Nonzero exit relaxation.** Some backends exit with a non-zero status
    even after writing a substantive final answer:
      * ``openclaw_edict`` orchestrator exits non-zero whenever ANY of its
        sub-省 agents (中书 / 门下 / 尚书 / 六部) crashes, even when taizi
        (the primary) has already produced a complete final reply.
      * ``nanobot`` reasoning-mode models (kimi-k2.x, gpt-5.4) routinely end
        with rc!=0 after stdio close-on-flush or outer-timeout SIGTERM.

  - **Zero-exit fallback.** ``nanobot`` doesn't expose ``stop_reason`` and its
    reasoning-mode models rarely emit canonical completion phrases. A clean
    exit + text-only-last-message must be treated as completed.

Each strategy decides whether the relaxation applies and returns a
:class:`BackendCompletionDecision` describing how to flip ``completed`` /
``reason``. The evaluator's main flow stays a single dispatcher and never
sees ``if agent_sys == "openclaw_edict"`` / ``"nanobot"`` again.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptSnapshot:
    """Pre-computed view of the last-assistant-message state.

    Built by the evaluator's transcript helpers and handed to each strategy
    so the strategies stay free of transcript-walking machinery and free of
    cross-module dependencies. All fields default to "no completion signal".
    """
    has_last_message: bool = False
    last_message_has_tool_call: bool = False
    final_text: str = ""
    api_stop_reason: str = ""
    text_marker_signal: bool = False
    still_routing: bool = False


@dataclass(frozen=True)
class BackendCompletionDecision:
    """Outcome of a strategy decision when it fires.

    ``api_stop_reason`` / ``last_message_has_tool_call`` / ``text_marker_signal``
    overlay the evaluator's running values; ``reason`` becomes the new reason
    label and ``completed`` flips the completion flag.
    """
    completed: bool
    reason: str
    api_stop_reason: str
    last_message_has_tool_call: bool
    text_marker_signal: bool


# ``_SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS`` separates a real taizi final answer
# from a one-line routing placeholder (e.g. ``[[reply_to_current]] 已收到旨意``).
# 200 chars is long enough that no routing acknowledgement reaches it. Kept
# in this module so the strategy and its calibration live together; the
# evaluator no longer hosts the constant.
SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS = 200


_OPENCLAW_EDICT = "openclaw_edict"
_NANOBOT = "nanobot"
_OPENCLAW = "openclaw"

# API stop reasons that positively indicate the model was cut off mid-answer
# (truncated by length, or still calling a tool).  Mirrors
# ``evaluation._API_INCOMPLETE_STOP_REASONS``; kept local to avoid importing
# the evaluator (which imports this module).  An *empty* stop reason is NOT
# in this set — openclaw frequently does not surface one even on a clean
# finish, so empty must remain eligible for relaxation.
_INCOMPLETE_API_STOP_REASONS: frozenset[str] = frozenset(
    {"toolUse", "tool_use", "length", "max_tokens"}
)


def _canonical_agent_sys(agent_sys: str) -> str:
    return (agent_sys or "").strip().lower()


def relax_nonzero_exit(
    agent_sys: str,
    snapshot: TranscriptSnapshot,
) -> BackendCompletionDecision | None:
    """Decide whether a nonzero-exit can be accepted as completed for this backend.

    Returns ``None`` when the strict rule should hold (``completed=False``,
    ``reason="nonzero-exit"``).
    """
    sys_name = _canonical_agent_sys(agent_sys)
    if not snapshot.has_last_message:
        return None

    if sys_name == _OPENCLAW_EDICT:
        # taizi's final answer must be substantive AND not a routing placeholder
        # AND no pending tool call. ``still_routing`` reflects the routing-note
        # placeholder + recent sessions_send/sessions_spawn detector.
        if (
            not snapshot.last_message_has_tool_call
            and len(snapshot.final_text) >= SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS
            and not snapshot.still_routing
        ):
            return BackendCompletionDecision(
                completed=True,
                reason="edict-taizi-final-answer-despite-orch-exit",
                api_stop_reason=snapshot.api_stop_reason,
                last_message_has_tool_call=False,
                text_marker_signal=snapshot.text_marker_signal,
            )
        return None

    if sys_name == _NANOBOT:
        # The 200-char threshold from edict does not apply to nanobot:
        # well-formed final answers range from one line to several KB. The
        # only reliable signal here is "non-empty text + not still mid-tool-call".
        if not snapshot.last_message_has_tool_call and snapshot.final_text:
            return BackendCompletionDecision(
                completed=True,
                reason="nanobot-final-answer-despite-nonzero-exit",
                api_stop_reason=snapshot.api_stop_reason,
                last_message_has_tool_call=False,
                text_marker_signal=snapshot.text_marker_signal,
            )
        return None

    if sys_name == _OPENCLAW:
        # openclaw exits nonzero when a trailing, non-contract command runs
        # AFTER the agent already produced its final answer — e.g. a stray
        # ``git commit`` that fails with "Author identity unknown" → rc=1.
        # The supervisor had already scored the work (the completion gate
        # only consults this relaxation on a ``verdict=pass`` turn), so a
        # clean text-only last message with no pending tool call and no
        # positively-incomplete API stop reason IS a completion. This mirrors
        # the edict/nanobot relaxations; without it correct runs were
        # demoted to ``executor_incomplete`` (supervisor 1.0, finalStatus
        # incomplete).  An empty api_stop_reason is allowed (openclaw often
        # omits one); only an explicit length/tool-use stop blocks it.
        if (
            not snapshot.last_message_has_tool_call
            and snapshot.final_text.strip()
            and snapshot.api_stop_reason not in _INCOMPLETE_API_STOP_REASONS
        ):
            return BackendCompletionDecision(
                completed=True,
                reason="openclaw-final-answer-despite-nonzero-exit",
                api_stop_reason=snapshot.api_stop_reason,
                last_message_has_tool_call=False,
                text_marker_signal=snapshot.text_marker_signal,
            )
        return None

    # unknown backends keep the strict signal contract.
    return None


def fallback_zero_exit(
    agent_sys: str,
    snapshot: TranscriptSnapshot,
) -> BackendCompletionDecision | None:
    """Decide whether a clean exit + ambiguous last-message can be accepted.

    Called only AFTER the evaluator's standard signal checks (API stop
    reason / text marker / tool call) have all said "missing completion
    signal". Returns ``None`` when no backend-specific fallback applies.
    """
    sys_name = _canonical_agent_sys(agent_sys)
    if sys_name == _NANOBOT:
        # nanobot lacks ``stop_reason`` and reasoning models rarely emit a
        # CONTINUATION_DONE_VARIANTS phrase. A clean exit alone is NOT
        # sufficient — we also need a non-empty text-only last message,
        # mirroring relax_nonzero_exit's nanobot branch. An empty / pure
        # tool-call last message must be classified as incomplete so the
        # final state can land on ``executor_incomplete`` rather than
        # ``budget_exhausted`` or a spurious ``pass``.
        if snapshot.final_text.strip() and not snapshot.last_message_has_tool_call:
            return BackendCompletionDecision(
                completed=True,
                reason="nanobot-clean-exit-no-tool-call",
                api_stop_reason=snapshot.api_stop_reason,
                last_message_has_tool_call=snapshot.last_message_has_tool_call,
                text_marker_signal=snapshot.text_marker_signal,
            )
        return None
    if sys_name == _OPENCLAW:
        # Round-7: symmetric with relax_nonzero_exit's openclaw branch, but for
        # the CLEAN (zero) exit case.  openclaw often exits 0 with a final
        # text-only answer and no explicit stop_reason / completion sentinel.
        # This fallback is only consulted on a ``verdict=pass`` turn (the
        # supervisor already scored the work), so a clean text-only last
        # message with no pending tool call and no positively-incomplete API
        # stop reason IS a completion.  Without it, correct zero-exit openclaw
        # runs were demoted to executor_incomplete (supervisor 1.0, finalStatus
        # incomplete) — the exact demotion the nonzero-exit branch already
        # prevents for rc!=0.
        if (
            snapshot.final_text.strip()
            and not snapshot.last_message_has_tool_call
            and snapshot.api_stop_reason not in _INCOMPLETE_API_STOP_REASONS
        ):
            return BackendCompletionDecision(
                completed=True,
                reason="openclaw-clean-exit-text-only",
                api_stop_reason=snapshot.api_stop_reason,
                last_message_has_tool_call=False,
                text_marker_signal=snapshot.text_marker_signal,
            )
        return None
    return None


__all__ = [
    "BackendCompletionDecision",
    "SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS",
    "TranscriptSnapshot",
    "fallback_zero_exit",
    "relax_nonzero_exit",
]
