"""Tests for ``lib.runner.compute_executor_token_usage``.

The function is the single source of truth for executor-only token
counting. It walks the per-attempt merged transcript, sums each LLM
response's ``message.usage`` block, and writes the result to
``<attempt>/usage.json`` where the WebUI picks it up.

Critical invariants these tests lock:

- Counts the openclaw ``{input, output, cacheRead, cacheWrite,
  totalTokens}`` key shape (the shape we actually see in real runs).
- Counts the native OpenAI ``{prompt_tokens, completion_tokens,
  total_tokens}`` key shape as a second source so a provider swap
  doesn't silently zero out the numbers.
- For edict runs the per-agent breakdown respects ``agentId``
  annotations on each event — the merged transcript produced by
  ``merge_agent_transcripts`` preserves those.
- Nanobot-style transcripts (no ``usage`` block anywhere) return
  ``available=False`` with a provider-specific reason instead of
  silently reporting zero tokens.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from lib.runner import compute_executor_token_usage


def _write_transcript(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _task(agent_sys: str) -> SimpleNamespace:
    return SimpleNamespace(agent_sys=agent_sys)


def test_openclaw_style_usage_keys_aggregate_correctly(tmp_path: Path) -> None:
    events = [
        {
            "type": "message",
            "timestamp": "2026-04-16T11:38:07.344Z",
            "message": {
                "role": "assistant",
                "usage": {
                    "input": 100,
                    "output": 20,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 120,
                },
            },
        },
        {
            "type": "message",
            "timestamp": "2026-04-16T11:38:17.344Z",
            "message": {
                "role": "assistant",
                "usage": {
                    "input": 50,
                    "output": 10,
                    "cacheRead": 100,  # should roll up separately
                    "cacheWrite": 0,
                    "totalTokens": 160,
                },
            },
        },
    ]
    _write_transcript(tmp_path / "transcript.jsonl", events)
    payload = compute_executor_token_usage(tmp_path, _task("openclaw"))

    assert payload["available"] is True
    executor = payload["summary"]["executor"]
    assert executor["prompt_tokens"] == 150
    assert executor["completion_tokens"] == 30
    assert executor["cache_read_tokens"] == 100
    assert executor["total_tokens"] == 280
    assert executor["call_count"] == 2


def test_openai_style_usage_keys_are_also_recognized(tmp_path: Path) -> None:
    """Forward-compat: if a future provider returns the native OpenAI
    key shape (``prompt_tokens``/``completion_tokens``) instead of the
    openclaw one, the function must still count it correctly so we
    don't silently report zero."""
    events = [
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "usage": {"prompt_tokens": 80, "completion_tokens": 40, "total_tokens": 120},
            },
        }
    ]
    _write_transcript(tmp_path / "transcript.jsonl", events)
    payload = compute_executor_token_usage(tmp_path, _task("openclaw"))

    assert payload["available"] is True
    executor = payload["summary"]["executor"]
    assert executor["prompt_tokens"] == 80
    assert executor["completion_tokens"] == 40
    assert executor["total_tokens"] == 120
    assert executor["call_count"] == 1


def test_edict_per_agent_breakdown_respects_agentId_annotations(tmp_path: Path) -> None:
    """For ``openclaw_edict`` the merged transcript carries
    ``agentId`` on every event (added by ``annotate_transcript_with_
    agent``). The function must return a per-agent breakdown that
    reproduces those counts so the WebUI can render the three-省 /
    六部 split without re-walking individual session files."""
    events = [
        {
            "type": "message",
            "agentId": "taizi",
            "message": {"role": "assistant", "usage": {"input": 500, "output": 50, "totalTokens": 550}},
        },
        {
            "type": "message",
            "agentId": "zhongshu",
            "message": {"role": "assistant", "usage": {"input": 200, "output": 30, "totalTokens": 230}},
        },
        {
            "type": "message",
            "agentId": "shangshu",
            "message": {"role": "assistant", "usage": {"input": 1000, "output": 80, "totalTokens": 1080}},
        },
        {
            "type": "message",
            "agentId": "shangshu",  # the nested subagent event merges under the same agentId
            "message": {"role": "assistant", "usage": {"input": 300, "output": 20, "totalTokens": 320}},
        },
    ]
    _write_transcript(tmp_path / "transcript.jsonl", events)
    payload = compute_executor_token_usage(tmp_path, _task("openclaw_edict"))

    executor = payload["summary"]["executor"]
    # Totals: 500+200+1000+300 = 2000 / 50+30+80+20 = 180
    assert executor["prompt_tokens"] == 2000
    assert executor["completion_tokens"] == 180
    assert executor["call_count"] == 4

    per_agent = payload["perAgent"]
    assert per_agent["taizi"]["prompt_tokens"] == 500
    assert per_agent["zhongshu"]["prompt_tokens"] == 200
    assert per_agent["shangshu"]["prompt_tokens"] == 1300
    assert per_agent["shangshu"]["call_count"] == 2


def test_nanobot_transcript_without_usage_returns_unavailable(tmp_path: Path) -> None:
    """Nanobot does NOT write ``message.usage`` blocks into its
    session jsonl. Returning zero for the WebUI would be a silent lie
    (the run clearly consumed tokens) — the honest answer is
    ``available: False`` with a provider-specific reason so the UI
    can render ``n/a``."""
    events = [
        {
            "type": "message",
            "message": {"role": "user", "content": [{"type": "text", "text": "hello"}]},
        },
        {
            "type": "message",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
        },
    ]
    _write_transcript(tmp_path / "transcript.jsonl", events)
    payload = compute_executor_token_usage(tmp_path, _task("nanobot"))

    assert payload["available"] is False
    assert payload["reason"] == "nanobot-transcript-has-no-usage"
    assert payload["summary"] == {}
    assert payload["calls"] == []


def test_missing_transcript_returns_unavailable(tmp_path: Path) -> None:
    """If the attempt never got a transcript (container crashed
    before artifacts sync), we should report unavailable rather than
    crashing."""
    payload = compute_executor_token_usage(tmp_path, _task("openclaw"))
    assert payload["available"] is False
    assert payload["reason"] == "transcript-not-collected"


def test_malformed_jsonl_lines_are_skipped_silently(tmp_path: Path) -> None:
    """Robustness: a mid-file parse error must not stop the sum."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    with transcript.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "message", "message": {"usage": {"input": 10, "output": 2, "totalTokens": 12}}}) + "\n")
        handle.write("{not-json-at-all\n")
        handle.write(json.dumps({"type": "message", "message": {"usage": {"input": 5, "output": 1, "totalTokens": 6}}}) + "\n")
    payload = compute_executor_token_usage(tmp_path, _task("openclaw"))
    assert payload["available"] is True
    executor = payload["summary"]["executor"]
    assert executor["prompt_tokens"] == 15
    assert executor["call_count"] == 2


def test_usage_json_is_not_copied_to_role_workspaces(tmp_path: Path) -> None:
    """Isolation invariant: the per-attempt ``usage.json`` must stay
    out of the supervisor and user_simulator Codex workspaces. If
    those roles saw per-attempt token counts they'd have an extra
    (and irrelevant) signal — e.g. "this agent used lots of tokens
    therefore it's failing" — that could bias their judgment away
    from task outcome. Lock this by checking the role workspace
    prompt-file manifest never references the file.
    """
    from lib.supervision.workspace import _role_workspace_prompt_files

    forbidden_names = {"usage.json", "visible/usage.json"}
    for role in ("answer_supervisor", "public_user_simulator"):
        files = _role_workspace_prompt_files(role, has_privacy=True)
        for entry in files:
            # Match on the trailing path component, not a raw substring,
            # so ``visible/tool_usage.json`` (a legitimate supervisor
            # input) doesn't false-positive trip the leak check.
            leaf = entry.rstrip("/").rsplit("/", 1)[-1]
            assert leaf != "usage.json", (
                f"role {role!r} workspace listing contains {entry!r} — "
                "per-attempt executor token counts must never be shown "
                "to supervisor or user_simulator"
            )
            assert entry not in forbidden_names, (
                f"role {role!r} workspace listing contains {entry!r} — "
                "per-attempt executor token counts must stay at the "
                "attempt-root, not under visible/"
            )


def test_usage_summary_shape_matches_webui_expectations(tmp_path: Path) -> None:
    """Lock the ``summary.executor`` schema the WebUI consumes: keys
    are ``prompt_tokens``, ``completion_tokens``, ``total_tokens``,
    ``call_count``. If the key names ever drift, the WebUI silently
    shows n/a again — this test catches that at the unit level."""
    events = [
        {"type": "message", "message": {"role": "assistant", "usage": {"input": 1, "output": 1, "totalTokens": 2}}},
    ]
    _write_transcript(tmp_path / "transcript.jsonl", events)
    payload = compute_executor_token_usage(tmp_path, _task("openclaw"))
    executor = payload["summary"]["executor"]
    for required_key in ("prompt_tokens", "completion_tokens", "total_tokens", "call_count"):
        assert required_key in executor, f"missing {required_key} key needed by WebUI usage_summary"
