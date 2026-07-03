"""Tests for ``lib.i18n`` — the centralized zh/en text module.

This module owns three translatable surfaces:

  - ``GUIDANCE_TAG_PUBLIC_HINTS`` + ``guidance_tag_public_hint`` — one
    hint string per guidance tag, keyed by language
  - ``PUBLIC_FEEDBACK_SUMMARY`` + ``public_feedback_summary`` — one
    summary per supervisor ``requested_reason`` key
  - ``FALLBACK_FEEDBACK`` + ``fallback_feedback_text`` — per-branch
    fallback lines for feedback_rewriter

These tests lock the lookup contracts and verify that zh and en are
aligned (every key has both languages), so a future contributor can add
a new entry without dropping half the translation.
"""
from __future__ import annotations

import pytest

from lib.i18n import (
    FALLBACK_FEEDBACK,
    GUIDANCE_TAG_PUBLIC_HINTS,
    GUIDANCE_TAGS,
    KEEP_GOING_FOR_MORE_EVIDENCE,
    PUBLIC_FEEDBACK_SUMMARY,
    fallback_feedback_text,
    guidance_tag_public_hint,
    public_feedback_summary,
)


# ── Language coverage invariants ───────────────────────────────────


def test_every_guidance_hint_has_both_languages() -> None:
    for tag, entry in GUIDANCE_TAG_PUBLIC_HINTS.items():
        assert set(entry.keys()) == {"zh", "en"}, f"tag {tag!r} missing a language"
        assert entry["zh"].strip(), f"tag {tag!r} has empty zh"
        assert entry["en"].strip(), f"tag {tag!r} has empty en"


def test_every_public_feedback_reason_has_both_languages() -> None:
    for reason, entry in PUBLIC_FEEDBACK_SUMMARY.items():
        assert set(entry.keys()) == {"zh", "en"}, f"reason {reason!r} missing a language"
        assert entry["zh"].strip(), f"reason {reason!r} has empty zh"
        assert entry["en"].strip(), f"reason {reason!r} has empty en"


def test_every_fallback_branch_has_both_languages() -> None:
    expected_branches = {"complete_but_failed", "incomplete", "verdict_continue", "default"}
    assert set(FALLBACK_FEEDBACK.keys()) == {"zh", "en"}
    for lang, table in FALLBACK_FEEDBACK.items():
        assert set(table.keys()) == expected_branches, (
            f"{lang!r} fallback table is missing branches: "
            f"{expected_branches - set(table.keys())}"
        )


def test_keep_going_has_both_languages() -> None:
    assert set(KEEP_GOING_FOR_MORE_EVIDENCE.keys()) == {"zh", "en"}
    assert KEEP_GOING_FOR_MORE_EVIDENCE["zh"].strip()
    assert KEEP_GOING_FOR_MORE_EVIDENCE["en"].strip()


def test_guidance_tags_frozenset_mirrors_hints_dict() -> None:
    assert GUIDANCE_TAGS == frozenset(GUIDANCE_TAG_PUBLIC_HINTS)


# ── Accessor behavior ──────────────────────────────────────────────


@pytest.mark.parametrize("zh,expected_prefix", [(True, "请继续"), (False, "Keep following")])
def test_guidance_tag_public_hint_returns_correct_language(zh, expected_prefix) -> None:
    hint = guidance_tag_public_hint("follow_public_task", zh=zh)
    assert hint.startswith(expected_prefix)


def test_guidance_tag_public_hint_unknown_tag_returns_empty() -> None:
    assert guidance_tag_public_hint("not_a_real_tag", zh=True) == ""
    assert guidance_tag_public_hint("", zh=False) == ""


@pytest.mark.parametrize(
    "reason,zh,expected_substring",
    [
        ("still_exploring", True, "执行中"),
        ("still_exploring", False, "in progress"),
        ("evidence_sufficient", True, "足够"),
        ("evidence_sufficient", False, "sufficient"),
    ],
)
def test_public_feedback_summary_returns_correct_entry(reason, zh, expected_substring) -> None:
    assert expected_substring in public_feedback_summary(reason, zh=zh)


def test_public_feedback_summary_unknown_reason_falls_back_to_needs_more_work() -> None:
    zh_default = public_feedback_summary("bogus_reason_not_in_table", zh=True)
    en_default = public_feedback_summary("bogus_reason_not_in_table", zh=False)
    assert zh_default == PUBLIC_FEEDBACK_SUMMARY["needs_more_work"]["zh"]
    assert en_default == PUBLIC_FEEDBACK_SUMMARY["needs_more_work"]["en"]


def test_fallback_feedback_text_selects_correct_branch() -> None:
    # Branch 1: attempt_state == "complete_but_failed"
    out = fallback_feedback_text({"attempt_state": "complete_but_failed"}, zh=False)
    assert out == FALLBACK_FEEDBACK["en"]["complete_but_failed"]

    # Branch 2: attempt_state == "incomplete"
    out = fallback_feedback_text({"attempt_state": "incomplete"}, zh=True)
    assert out == FALLBACK_FEEDBACK["zh"]["incomplete"]

    # Branch 3: verdict == "continue" (no matching attempt_state)
    out = fallback_feedback_text({"verdict": "continue"}, zh=False)
    assert out == FALLBACK_FEEDBACK["en"]["verdict_continue"]

    # Branch 4: neither branch matches → default
    out = fallback_feedback_text({}, zh=True)
    assert out == FALLBACK_FEEDBACK["zh"]["default"]


def test_fallback_feedback_text_attempt_state_wins_over_verdict() -> None:
    """If both attempt_state and verdict would match branches, attempt_state
    wins (this preserves the original if/elif chain semantics)."""
    out = fallback_feedback_text(
        {"attempt_state": "incomplete", "verdict": "continue"},
        zh=True,
    )
    assert out == FALLBACK_FEEDBACK["zh"]["incomplete"]
