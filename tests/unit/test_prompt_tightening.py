"""Round 9 / A7 regression: supervisor/user prompts treat summaries as
navigation indices, not as evidence.

The combined 2026-05-14 code review observed that supervisor /
user_simulator prompt language said "most judging passes need nothing
more" + "OCR/text summary can be enough" — which let models treat
summaries as ground truth.  Round 9 / A7 rewrites those passages to:

- Treat summary as a navigation index, NOT evidence.
- When the rubric depends on visual content (image content, page
  state, layout, text-in-image, colors, visual correctness), MUST
  call view_image.
- When transcript shows failure / timeout / rate_limit / fallback /
  infra_error signals, MUST read the corresponding transcript_full
  chunk before scoring.
- user_simulator MUST call view_image when its next instruction
  depends on what a screenshot actually shows.

These tests rebuild the prompts as strings and pin the key sentences.
Cosmetic edits stay free; semantic loosening (re-adding "summary is
enough") will break the tests so we revisit the decision.
"""
from __future__ import annotations

from lib.templates.answer_supervisor import TEMPLATE as SUPERVISOR_TEMPLATE
from lib.templates.answer_supervisor import TRANSCRIPT_CHUNKING_NOTE
from lib.templates.user_simulator import TEMPLATE as USER_SIMULATOR_TEMPLATE


def test_supervisor_treats_summary_as_navigation_index():
    """Pre-fix: prompt said 'Most judging passes need nothing more'.
    Post-fix: 'navigation index, not evidence' framing."""
    text = SUPERVISOR_TEMPLATE
    assert "navigation index" in text.lower(), (
        "supervisor prompt should describe summary as a navigation index "
        "to discourage summary-only reasoning"
    )


def test_supervisor_requires_view_image_for_visual_rubric():
    """When rubric depends on image content / page state / visual
    correctness, the supervisor MUST inspect the original artifact."""
    text = SUPERVISOR_TEMPLATE.lower()
    assert "you must" in text and "view_image" in text, (
        "supervisor prompt must mandate view_image for visual checkpoints"
    )
    # The specific list of visual concerns
    for concern in ("image content", "page state", "layout"):
        assert concern in text, f"missing concern: {concern}"


def test_transcript_chunking_note_directs_to_full_chunks_on_failure():
    """When transcript signals failure/timeout/rate_limit/fallback,
    supervisor must read the relevant transcript_full chunk."""
    text = TRANSCRIPT_CHUNKING_NOTE.lower()
    assert "must read" in text or "must" in text
    assert "transcript_full" in text
    for signal in ("failure", "timeout", "rate_limit", "fallback"):
        assert signal in text, f"missing failure signal: {signal}"


def test_transcript_chunking_note_mentions_omitted_marker_navigation():
    """Operators write omitted markers with structured fields
    (omitted_block_range, transcript_full_chunk_hint).  The prompt
    should tell the supervisor how to use those for navigation."""
    text = TRANSCRIPT_CHUNKING_NOTE.lower()
    assert "omitted" in text and "transcript_full_chunk_hint" in text


def test_user_simulator_requires_view_image_for_visual_state():
    """user_simulator prompt: when next instruction depends on what a
    screenshot actually shows, MUST call view_image rather than infer
    from OCR / filename / transcript."""
    text = USER_SIMULATOR_TEMPLATE.lower()
    assert "you must" in text or "must call" in text
    assert "view_image" in text
    # The discouragement of OCR / filename / transcript text alone
    assert "ocr" in text and "transcript" in text
