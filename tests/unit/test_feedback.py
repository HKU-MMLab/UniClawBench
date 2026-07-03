from __future__ import annotations

from types import SimpleNamespace

from lib.constants import SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY, SAFE_USER_FEEDBACK_MODE_COMPOSED
from lib.supervision.feedback_rewriter import fallback_feedback, rewrite_feedback


def test_rewrite_feedback_continue_with_candidate() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(public_task="Search YouTube for earbuds."),
        attempt=SimpleNamespace(turn=1),
    )
    user_handoff = {"verdict": "continue", "attempt_state": "incomplete", "recoverable": True}
    public_user = {"candidate_feedback": "Please check the video again and save a screenshot."}
    result = rewrite_feedback(context, user_handoff, public_user)
    assert result["safe_user_feedback"] == "Please check the video again and save a screenshot."
    assert result["used_candidate_feedback"] is True
    assert result["feedback_mode"] == SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY


def test_rewrite_feedback_default_mode_uses_candidate_only() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(public_task="Please finish the Outlook login check."),
        attempt=SimpleNamespace(turn=1),
    )
    user_handoff = {"verdict": "continue", "attempt_state": "incomplete", "recoverable": True}
    public_user = {
        "candidate_feedback": "Please keep going.",
        "public_feedback_points": ["Save a screenshot once you reach the inbox."],
    }
    result = rewrite_feedback(
        context,
        user_handoff,
        public_user,
        guidance_tags=["credential_hygiene"],
    )
    assert result["safe_user_feedback"] == "Please keep going."
    assert result["used_candidate_feedback"] is True
    assert result["used_public_feedback_points"] is False
    assert result["applied_guidance_tags"] == []
    assert result["feedback_mode"] == SAFE_USER_FEEDBACK_MODE_CANDIDATE_ONLY


def test_rewrite_feedback_composed_mode_uses_public_points_and_guidance_after_candidate() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(public_task="Please finish the Outlook login check."),
        attempt=SimpleNamespace(turn=1),
    )
    user_handoff = {"verdict": "continue", "attempt_state": "incomplete", "recoverable": True}
    public_user = {
        "candidate_feedback": "Please keep going.",
        "public_feedback_points": ["Save a screenshot once you reach the inbox."],
    }
    result = rewrite_feedback(
        context,
        user_handoff,
        public_user,
        guidance_tags=["credential_hygiene"],
        mode=SAFE_USER_FEEDBACK_MODE_COMPOSED,
    )
    lines = result["safe_user_feedback"].splitlines()
    assert lines[0] == "Please keep going."
    assert lines[1] == "Save a screenshot once you reach the inbox."
    assert "credential hygiene" in lines[2].lower()
    assert result["used_public_feedback_points"] is True
    assert result["applied_guidance_tags"] == ["credential_hygiene"]
    assert result["feedback_mode"] == SAFE_USER_FEEDBACK_MODE_COMPOSED


def test_rewrite_feedback_candidate_only_mode_falls_back_when_candidate_missing() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(public_task="Please finish the Outlook login check."),
        attempt=SimpleNamespace(turn=1),
    )
    user_handoff = {"verdict": "continue", "attempt_state": "incomplete", "recoverable": True}
    public_user = {
        "candidate_feedback": "",
        "public_feedback_points": ["Save a screenshot once you reach the inbox."],
    }
    result = rewrite_feedback(
        context,
        user_handoff,
        public_user,
        guidance_tags=["credential_hygiene"],
    )
    assert result["safe_user_feedback"] == fallback_feedback(user_handoff, zh=False)
    assert result["used_candidate_feedback"] is False
    assert result["used_public_feedback_points"] is False
    assert result["applied_guidance_tags"] == []


def test_rewrite_feedback_non_continue_returns_empty() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(public_task="Search YouTube for earbuds."),
        attempt=SimpleNamespace(turn=1),
    )
    user_handoff = {"verdict": "pass", "attempt_state": "complete_and_passed"}
    result = rewrite_feedback(context, user_handoff, None)
    assert result["safe_user_feedback"] == ""
    assert result["used_candidate_feedback"] is False


def test_fallback_feedback_zh_and_en() -> None:
    # Chinese incomplete
    fb = fallback_feedback({"attempt_state": "incomplete", "verdict": "continue"}, zh=True)
    assert "\u7ee7\u7eed" in fb

    # Chinese complete_but_failed
    fb = fallback_feedback({"attempt_state": "complete_but_failed", "verdict": "continue"}, zh=True)
    assert "\u6838\u5bf9" in fb

    # English incomplete
    fb = fallback_feedback({"attempt_state": "incomplete", "verdict": "continue"}, zh=False)
    assert "missing" in fb.lower()

    # English complete_but_failed
    fb = fallback_feedback({"attempt_state": "complete_but_failed", "verdict": "continue"}, zh=False)
    assert "re-check" in fb.lower()
