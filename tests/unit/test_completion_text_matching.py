"""Regression: assistant_signaled_completion must preserve CJK AND
avoid substring false positives.

Two real bugs from the 2026-05-13 code review:

1. The function strips everything except ``[a-z\\s]`` before matching,
   so CJK completion markers in ``CONTINUATION_DONE_VARIANTS``
   (``已完成``, ``已经完成``, ``任务完成``) can NEVER match — Chinese
   runs that signal completion get blocked.

2. The substring check (``variant in normalized``) is too permissive
   on English text: ``"not completed"`` / ``"not done yet"`` contain
   the completion tokens ``completed`` / ``done`` and get classified
   as finished.  These false positives flip the completion_gate, and
   from there propagate into ``executor_completed`` and the attempt's
   final status.
"""
from __future__ import annotations

import json

from lib.runner.evaluation import assistant_signaled_completion


def _assistant_text_transcript(text: str) -> str:
    event = {
        "type": "message",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }
    return json.dumps(event) + "\n"


# ── Finding 1a: CJK markers must match ────────────────────────────────


def test_chinese_yiwancheng_signals_completion():
    transcript = _assistant_text_transcript("好的，我已完成。")
    assert assistant_signaled_completion(transcript) is True


def test_chinese_yijing_wancheng_signals_completion():
    transcript = _assistant_text_transcript("已经完成所有步骤。")
    assert assistant_signaled_completion(transcript) is True


def test_chinese_renwu_wancheng_signals_completion():
    transcript = _assistant_text_transcript("任务完成")
    assert assistant_signaled_completion(transcript) is True


# ── Finding 1b: English negation must NOT count as completion ─────────


def test_english_not_completed_does_not_signal():
    """``not completed`` contains the substring ``completed`` — the old
    permissive matcher classified this as done.  Fixed matcher must
    not."""
    transcript = _assistant_text_transcript(
        "I have NOT completed the task yet — still working on the deliverables."
    )
    assert assistant_signaled_completion(transcript) is False


def test_english_not_done_does_not_signal():
    transcript = _assistant_text_transcript(
        "Not done yet, more refactoring required before this is ready."
    )
    assert assistant_signaled_completion(transcript) is False


def test_chinese_negation_does_not_signal():
    """Symmetric to the English negation case: Chinese 还没完成 / 未完成
    contains 完成 but should not signal completion."""
    transcript = _assistant_text_transcript("还没完成，需要继续。")
    assert assistant_signaled_completion(transcript) is False


# ── Positive English cases (must still work after the fix) ────────────


def test_english_done_marker_signals_completion():
    transcript = _assistant_text_transcript("Done.")
    assert assistant_signaled_completion(transcript) is True


def test_english_task_complete_signals_completion():
    transcript = _assistant_text_transcript("Task complete.")
    assert assistant_signaled_completion(transcript) is True


def test_english_canonical_marker_signals_completion():
    transcript = _assistant_text_transcript("I have finished the request.")
    assert assistant_signaled_completion(transcript) is True
