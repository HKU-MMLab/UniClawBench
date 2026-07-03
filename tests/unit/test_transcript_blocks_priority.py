"""Round 9 / A5 regression: semantic_transcript_blocks preserves
failure-signal blocks under truncation.

Pre-fix, ``semantic_transcript_blocks`` truncated middle blocks
unconditionally (head ~6 + tail ~11).  When a tool_error or
assistant_error sat in the middle, supervisor's truncated view showed
empty plan + final "all done" — supervisor scored freely without
knowing the run crashed mid-way.

Round 9 / A5 always keeps:
- every assistant_error / tool_error block
- every block whose text contains failure keywords (fail, error,
  timeout, rate limit, infra, pre_exec, fallback, exception, traceback)
- the last 5 blocks (executor final conclusion + supervisor context)

When omitted ranges remain, the marker carries structured fields so
the supervisor prompt can navigate to ``transcript_full/manifest.json``
for the dropped chunk.

These tests drive ``_retain_error_priority`` directly with synthetic
block lists and pin the must-keep + omitted-marker shape.
"""
from __future__ import annotations

from lib.supervision.transcripts import (
    _block_has_failure_signal,
    _retain_error_priority,
)


def _b(kind: str, text: str = "", **extra) -> dict:
    return {"kind": kind, "text": text, **extra}


# ── _block_has_failure_signal ────────────────────────────────────────


def test_failure_signal_via_kind():
    assert _block_has_failure_signal(_b("assistant_error", "no detail"))
    assert _block_has_failure_signal(_b("tool_error", "boom"))


def test_failure_signal_via_text_keywords():
    for kw in ("failed to do X", "timeout reached", "rate_limit hit",
               "infra_error noted", "fallback used",
               "Exception raised", "Traceback (most recent",
               "pre_exec failed bootstrap"):
        block = _b("tool_text", kw)
        assert _block_has_failure_signal(block), kw


def test_failure_signal_negative():
    assert not _block_has_failure_signal(_b("user_message", "please help"))
    assert not _block_has_failure_signal(_b("assistant_text", "I'll proceed"))
    assert not _block_has_failure_signal(_b("tool_text", "ran ok"))


# ── _retain_error_priority ───────────────────────────────────────────


def test_priority_preserves_tool_error_in_middle():
    """30 blocks; the 15th is a tool_error.  After truncation to 10
    blocks, the tool_error must still be present."""
    blocks = []
    for i in range(30):
        if i == 14:
            blocks.append(_b("tool_error", f"boom at step {i}", tool="exec"))
        else:
            blocks.append(_b("assistant_text", f"plan step {i}"))
    out = _retain_error_priority(blocks, max_blocks=10)
    error_blocks = [b for b in out if b["kind"] == "tool_error"]
    assert len(error_blocks) == 1
    assert "boom at step 14" in error_blocks[0]["text"]


def test_priority_preserves_assistant_error_in_middle():
    blocks = []
    for i in range(30):
        if i == 7:
            blocks.append(_b("assistant_error", "exception during draft"))
        else:
            blocks.append(_b("user_message", f"msg {i}"))
    out = _retain_error_priority(blocks, max_blocks=10)
    err = [b for b in out if b["kind"] == "assistant_error"]
    assert len(err) == 1


def test_priority_keeps_failure_keyword_in_text():
    blocks = []
    for i in range(30):
        if i == 12:
            blocks.append(_b("tool_text", "rate_limit on upstream"))
        elif i == 20:
            blocks.append(_b("assistant_text", "fallback to safe template"))
        else:
            blocks.append(_b("user_message", f"please continue step {i}"))
    out = _retain_error_priority(blocks, max_blocks=10)
    texts = " | ".join(b.get("text", "") for b in out)
    assert "rate_limit on upstream" in texts
    assert "fallback to safe template" in texts


def test_priority_keeps_last_5_blocks_always():
    blocks = [_b("user_message", f"step {i}") for i in range(30)]
    out = _retain_error_priority(blocks, max_blocks=10)
    # Last 5 of the original must be in the output (in order)
    last_texts = [b["text"] for b in out if b.get("kind") == "user_message"]
    for tail_text in ["step 25", "step 26", "step 27", "step 28", "step 29"]:
        assert tail_text in last_texts, f"missing tail block: {tail_text}"


def test_priority_omitted_marker_structured():
    """When budget forces dropping a middle range, the omitted marker
    carries omitted_count, omitted_block_range, omitted_event_range,
    transcript_full_chunk_hint."""
    blocks = [_b("user_message", f"step {i}") for i in range(30)]
    out = _retain_error_priority(blocks, max_blocks=10)
    omitted = [b for b in out if b.get("kind") == "omitted"]
    assert len(omitted) >= 1, "expected at least one omitted marker"
    marker = omitted[0]
    assert "omitted_count" in marker
    assert "omitted_block_range" in marker
    assert "omitted_event_range" in marker
    assert marker.get("transcript_full_chunk_hint") == "transcript_full/manifest.json"


def test_priority_no_truncation_when_under_budget():
    """If the input is already ≤ max_blocks, no work needed — but the
    function still works correctly (returns blocks as-is)."""
    blocks = [_b("user_message", f"x{i}") for i in range(5)]
    out = _retain_error_priority(blocks, max_blocks=10)
    # No filler, no omitted marker
    assert len(out) == 5
    assert all(b["kind"] == "user_message" for b in out)


def test_priority_keeps_all_errors_even_when_budget_tight():
    """6 errors + 24 plain blocks, budget=10.  All 6 errors are
    must-keep; tail must-keep is 5.  Total 11 > 10, so tail drops the
    OLDEST tail entry — the design choice is "errors win over old
    tail" because operator declared errors are highest priority."""
    blocks = []
    error_indices = [3, 8, 11, 16, 18, 22]
    for i in range(30):
        if i in error_indices:
            blocks.append(_b("tool_error", f"err at {i}"))
        else:
            blocks.append(_b("user_message", f"msg {i}"))
    out = _retain_error_priority(blocks, max_blocks=10)
    err_kept = [b for b in out if b["kind"] == "tool_error"]
    assert len(err_kept) == 6  # ALL errors retained
    # 4 most-recent tail entries retained (oldest tail dropped to fit)
    tail_texts = [b.get("text", "") for b in out if b.get("kind") == "user_message"]
    for ttl in ["msg 26", "msg 27", "msg 28", "msg 29"]:
        assert ttl in tail_texts, f"recent tail missing: {ttl}"
    # And the oldest tail entry is dropped (or relegated to omitted)
    assert "msg 25" not in tail_texts
