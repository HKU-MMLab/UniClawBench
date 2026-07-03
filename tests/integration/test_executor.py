from __future__ import annotations

import json
from pathlib import Path

from lib.runner import (
    CONTINUATION_DONE_MARKER,
    apply_executor_completion_gate,
    build_runtime_task_spec,
    executor_completion_state,
    prompt_prefix,
    resolve_attempt_outcome,
    transcript_targets_for_task,
)
from lib.supervision.feedback_rewriter import is_completion_line


ROOT = Path(__file__).resolve().parents[2]


def test_apply_executor_completion_gate_requires_executor_completion_for_pass() -> None:
    """When supervisor claims ``pass`` but executor never wrote a
    completion signal AND no followup budget remains, the gate flips
    to ``fail`` (the original strict behavior).  Round 10 / P1 added
    a budget-aware branch — see test_completion_gate_budget_aware.py
    for the ``budget > 0 → continue`` case."""
    transcript = json.dumps(
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I am still checking the video."}],
            },
        },
        ensure_ascii=False,
    )
    payload = apply_executor_completion_gate(
        {
            "overall_score": 1.0,
            "score_cap": 1.0,
            "capped_score": 1.0,
            "verdict": "pass",
            "attempt_state": "complete_and_passed",
            "recoverable": False,
        },
        transcript,
        1,
        followup_budget_remaining=0,  # No budget — strict fail behavior
    )
    assert payload["verdict"] == "fail"
    assert payload["overall_score"] == 1.0
    assert payload["final_completion_score"] == 0.0
    assert payload["supervisor_verdict_raw"] == "pass"
    assert payload["executor_completed"] is False
    assert payload["completion_gate_failed"] is True
    assert payload["completion_gate_deferred"] is False


def test_apply_executor_completion_gate_preserves_supervisor_score_for_completed_continue() -> None:
    transcript = json.dumps(
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I have finished the request"}],
            },
        },
        ensure_ascii=False,
    )
    payload = apply_executor_completion_gate(
        {
            "overall_score": 0.35,
            "score_cap": 1.0,
            "capped_score": 0.35,
            "verdict": "continue",
            "attempt_state": "incomplete",
            "recoverable": True,
        },
        transcript,
        0,
    )
    assert payload["executor_completed"] is True
    assert payload["final_completion_score"] == 0.35
    assert payload["completion_gate_failed"] is False


def test_resolve_attempt_outcome_uses_last_supervisor_score_when_budget_exhausted() -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    outcome = resolve_attempt_outcome(
        task,
        {
            "overall_score": 0.15,
            "capped_score": 0.15,
            "final_completion_score": 0.15,
            "final_completion_capped_score": 0.15,
            "verdict": "continue",
            "executor_completed": True,
        },
        terminal_reason="followup-limit-reached",
    )
    assert outcome["final_status"] == "budget_exhausted"
    assert outcome["final_score"] == 0.15
    assert outcome["passed"] is False


def test_resolve_attempt_outcome_uses_best_completion_score_when_executor_incomplete() -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    # best_supervisor_score tracks max(overall_score) across rounds (updated
    # from the old behaviour that tracked final_completion_score).
    # If executor never completed in any round, best_supervisor_score stays 0.
    #
    # Round-7 (lib.status.classify_attempt_outcome): an EXPLICIT cumulative
    # budget terminal (terminal_reason="followup-limit-reached") classifies as
    # ``budget_exhausted`` even when the executor never cleanly completed a
    # turn — the run genuinely exhausted its follow-up budget, so it is a
    # terminal failure (bounded retry) rather than ``executor_incomplete``
    # (which the dispatcher would re-dispatch forever).  Mirrors the
    # global-timeout precedence pinned by
    # tests/unit/test_status_module.py::test_classify_timeout_precedes_incomplete_round7.
    # The score selection is unchanged: best_supervisor_score=0 → final_score 0.
    outcome = resolve_attempt_outcome(
        task,
        {
            "overall_score": 0.6,
            "best_supervisor_score": 0.0,
            "final_completion_score": 0.0,
            "verdict": "continue",
            "executor_completed": False,
        },
        terminal_reason="followup-limit-reached",
    )
    assert outcome["final_status"] == "budget_exhausted"
    assert outcome["final_score"] == 0.0
    assert outcome["passed"] is False

    # If executor completed in an earlier round with score 0.4
    outcome2 = resolve_attempt_outcome(
        task,
        {
            "overall_score": 0.1,
            "best_supervisor_score": 0.4,
            "final_completion_score": 0.0,
            "verdict": "continue",
            "executor_completed": False,
            "executor_completed_ever": True,
        },
        terminal_reason="followup-limit-reached",
    )
    assert outcome2["final_status"] == "budget_exhausted"
    assert outcome2["final_score"] == 0.4


def test_resolve_attempt_outcome_preserves_last_score_when_executor_completed_earlier() -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    outcome = resolve_attempt_outcome(
        task,
        {
            "overall_score": 0.6,
            "capped_score": 0.6,
            "final_completion_score": 0.0,
            "final_completion_capped_score": 0.0,
            "verdict": "continue",
            "executor_completed": False,
            "executor_completed_ever": True,
        },
        terminal_reason="followup-limit-reached",
    )
    assert outcome["final_status"] == "budget_exhausted"
    assert outcome["final_score"] == 0.6
    assert outcome["passed"] is False


def test_resolve_attempt_outcome_takes_max_across_cycles_via_best_supervisor_score() -> None:
    """Trajectory 0.29 -> 0.76 -> 0.66 must yield finalScore = 0.76, not 0.66.

    Regression: previously best_supervisor_score tracked final_completion_score
    (which the completion gate could zero out), so test-1-like runs got the
    last cycle's score instead of the true peak. Now it tracks overall_score.
    """
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    # Simulate the state handed to resolve_attempt_outcome at the end of cycle 3:
    # the running max across all three cycles has already been tallied.
    outcome = resolve_attempt_outcome(
        task,
        {
            "overall_score": 0.66,              # the LAST cycle's score
            "capped_score": 0.66,
            "best_supervisor_score": 0.76,      # the MAX across cycles (cycle 2)
            "final_completion_score": 0.66,
            "final_completion_capped_score": 0.66,
            "verdict": "continue",
            "executor_completed": True,
            "executor_completed_ever": True,
        },
        terminal_reason="followup-limit-reached",
    )
    assert outcome["final_status"] == "budget_exhausted"
    # Must pick the peak (0.76), not the last cycle's 0.66.
    assert outcome["final_score"] == 0.76
    assert outcome["passed"] is False


def test_resolve_attempt_outcome_maps_global_timeout_to_new_status() -> None:
    """Terminal reason 'global-timeout-reached' must surface as a distinct
    finalStatus value, not get swallowed into 'stopped' or 'budget_exhausted'.
    (cycle-timeout was removed — a cycle from the executor's perspective is
    just one agent turn, which timeout_seconds already caps.)"""
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    base = {
        "overall_score": 0.5,
        "best_supervisor_score": 0.5,
        "final_completion_score": 0.5,
        "verdict": "continue",
        "executor_completed": True,
        "executor_completed_ever": True,
    }

    out_global = resolve_attempt_outcome(task, base, terminal_reason="global-timeout-reached")
    assert out_global["final_status"] == "global_timeout"
    assert out_global["final_score"] == 0.5


def test_best_supervisor_score_update_rule_reflects_max_overall_score() -> None:
    """Pure unit test of the update rule we now use in run_primary_attempt's
    main while-loop: best = max(best, overall_score), NOT gated on completion."""
    best = 0.0
    for overall_score, executor_completed in [
        (0.29, True),
        (0.76, False),   # cycle was cut off mid-tool-call — previously would
                         # have contributed 0.0 to best; now contributes 0.76
        (0.66, True),
    ]:
        if overall_score > best:
            best = overall_score
    assert best == 0.76


def test_is_completion_line_only_matches_pure_completion_claims() -> None:
    assert is_completion_line("\u5df2\u7ecf\u5b8c\u6210")
    assert is_completion_line("task is complete.")
    assert not is_completion_line("\u4f60\u521a\u624d\u8bf4\u5df2\u7ecf\u5b8c\u6210\u4e86\uff0c\u4f46\u6211\u8fd9\u91cc\u8fd8\u6ca1\u770b\u5230\u7ed3\u679c\u6587\u4ef6\u3002")


def test_prompt_prefix_guides_native_browser_typing() -> None:
    """The prompt must steer web/browser work through the agent-browser
    CLI (and its SKILL.md), not a fallback network fetch. The exact
    typing verbs ``kind=type`` / ``kind=fill`` live inside the SKILL
    markdown; the prefix itself only needs to point there reliably.
    """
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    prompt = prompt_prefix(task)
    assert "agent-browser" in prompt
    assert "agent-browser-control/SKILL.md" in prompt
    # The prompt should still differentiate browser work from web_fetch /
    # web_search so the agent does not treat web_fetch as a search tool.
    assert "snapshot" in prompt


def test_prompt_prefix_does_not_include_task_strategy_hints() -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    prompt = prompt_prefix(task)
    assert "preserve its intent" not in prompt
    assert "primary source" not in prompt
    assert "ranked result" not in prompt


def test_prompt_prefix_does_not_force_magic_completion_phrase() -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    prompt = prompt_prefix(task)
    # Completion is detected via API stopReason / message structure, so the prompt
    # should NOT mandate any specific sentence. Guidance about ending with a text
    # message (no tool calls) is still fine.
    assert CONTINUATION_DONE_MARKER not in prompt
    assert "exact sentence" not in prompt
    assert "final text message" in prompt.lower() or "end your turn" in prompt.lower()


# ── executor_completion_state: stopReason-based signals ─────────────


def _make_transcript(message: dict) -> str:
    return json.dumps({"type": "message", "message": message}, ensure_ascii=False)


def test_completion_state_api_stop_reason_stop_marks_completed_without_marker() -> None:
    """openclaw/edict expose stopReason='stop' when the model ends its turn naturally.
    This should be enough to mark completion, even if the prose lacks the explicit marker."""
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Final answer: Soundcore Sleep A30 at $199."}],
            "stopReason": "stop",
        }
    )
    state = executor_completion_state(transcript, 0)
    assert state["completed"] is True
    assert state["api_stop_reason"] == "stop"
    assert state["last_message_has_tool_call"] is False
    assert state["reason"] == "api-stop-stop"


def test_completion_state_api_stop_reason_tooluse_marks_incomplete() -> None:
    """When the backend cut off the turn mid-tool-call, the API reports stopReason='toolUse'.
    This must override any text-marker heuristic — the executor was still working."""
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I have finished the request"},
                {"type": "toolCall", "name": "screenshot", "arguments": {}},
            ],
            "stopReason": "toolUse",
        }
    )
    state = executor_completion_state(transcript, 0)
    assert state["completed"] is False
    assert state["api_stop_reason"] == "toolUse"
    assert state["reason"] == "api-stop-toolUse"


def test_completion_state_structural_tool_call_check_without_stop_reason() -> None:
    """nanobot's transcript omits stopReason. If the last message still contains a toolCall,
    the structural check must still flag it as incomplete."""
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Saving screenshot..."},
                {"type": "toolCall", "name": "take_screenshot", "arguments": {}},
            ],
        }
    )
    state = executor_completion_state(transcript, 0)
    assert state["completed"] is False
    assert state["last_message_has_tool_call"] is True
    assert state["reason"] == "last-message-still-calling-tool"


def test_completion_state_text_marker_fallback_when_no_stop_reason() -> None:
    """For backends without stopReason, a pure-text last message with the marker still counts."""
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Done. I have finished the request"}],
        }
    )
    state = executor_completion_state(transcript, 0)
    assert state["completed"] is True
    assert state["reason"] == "assistant-signaled-completion"


def test_completion_state_no_signals_is_incomplete() -> None:
    """Pure-text last message without stopReason and without the marker is missing-completion-signal."""
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Let me keep looking."}],
        }
    )
    state = executor_completion_state(transcript, 0)
    assert state["completed"] is False
    assert state["reason"] == "missing-completion-signal"


def test_completion_state_nonzero_exit_is_incomplete() -> None:
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Done."}],
            "stopReason": "stop",
        }
    )
    state = executor_completion_state(transcript, 1)
    assert state["completed"] is False
    assert state["reason"] == "nonzero-exit"


def test_completion_gate_exposes_new_structured_fields() -> None:
    transcript = _make_transcript(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Final conclusion."}],
            "stopReason": "stop",
        }
    )
    payload = apply_executor_completion_gate(
        {
            "overall_score": 0.8,
            "capped_score": 0.8,
            "verdict": "continue",
            "attempt_state": "incomplete",
            "recoverable": True,
        },
        transcript,
        0,
    )
    assert payload["executor_completed"] is True
    assert payload["executor_api_stop_reason"] == "stop"
    assert payload["executor_last_message_has_tool_call"] is False
    assert payload["completion_gate_failed"] is False


# ── transcript_targets_for_task: EDICT silence-monitor coverage ─────


def _make_task_spec(agent_sys: str, agent_id: str = "main"):
    """Create a minimal TaskSpec-like object for transcript_targets_for_task."""
    from lib.task import CodexSpec, TaskSpec
    return TaskSpec(
        task_id="x",
        category="x",
        agent_sys=agent_sys,
        agent_id=agent_id,
        model="p/m",
        image_model="p/m",
        timeout_seconds=1200,
        max_total_seconds=1800,
        success_threshold=1.0,
        task="t",
        task_snapshot="",
        references=[],
        sources=[],
        skills=[],
        services=[],
        pre_exec=[],
        privacy=[],
        file_path=Path("/tmp/nonexistent.yaml"),
        injection_root=Path("/tmp"),
        codex=CodexSpec(),
    )


def test_transcript_targets_openclaw_only_primary_agent() -> None:
    """Single-agent openclaw run only needs the primary agent's transcript."""
    task = _make_task_spec("openclaw", "main")
    targets = transcript_targets_for_task(task)
    # Should include main/chat.jsonl plus the /tmp/openclaw fallbacks
    assert any("/root/.openclaw/agents/main/sessions/" in t for t in targets)
    # Should NOT include any EDICT-specific sub-agent paths
    edict_ids = ["taizi", "zhongshu", "menxia", "shangshu", "libu", "hubu",
                 "bingbu", "xingbu", "gongbu", "libu_hr", "zaochao"]
    for eid in edict_ids:
        if eid == "main":
            continue
        assert not any(
            f"/root/.openclaw/agents/{eid}/sessions/" in t for t in targets
        ), f"openclaw shouldn't watch {eid}"


def test_transcript_targets_edict_covers_all_sub_agents(monkeypatch) -> None:
    """Regression for EDICT silence-monitor bug: when 太子 delegates to
    中书省/尚书省 etc. via sessions_send/spawn, the silence monitor must watch
    every EDICT agent's transcript, not just the primary (太子). Otherwise
    legitimate delegation looks like a hung agent and gets SIGTERM-killed."""
    import lib.runner as runner

    # Mock the edict_agent_ids helper so the test doesn't need downloads/edict/.
    sample_ids = [
        "taizi", "zhongshu", "menxia", "shangshu",
        "libu", "hubu", "bingbu", "xingbu", "gongbu",
    ]
    monkeypatch.setattr(runner, "edict_agent_ids", lambda: sample_ids)

    task = _make_task_spec("openclaw_edict", "taizi")
    targets = transcript_targets_for_task(task)

    for eid in sample_ids:
        expected = f"/root/.openclaw/agents/{eid}/sessions/chat.jsonl"
        assert expected in targets, (
            f"EDICT silence monitor must watch {eid}'s transcript, "
            f"otherwise 太子 delegating to it will be mistaken for a hang. "
            f"Missing: {expected}"
        )

    # Deduplication: taizi appears both as primary and as one of the agents;
    # the final list must not contain duplicates.
    assert len(targets) == len(set(targets)), "duplicate transcript paths"


def test_transcript_targets_nanobot_uses_nanobot_targets() -> None:
    """nanobot has its own transcript layout; shouldn't pull openclaw paths."""
    task = _make_task_spec("nanobot", "main")
    targets = transcript_targets_for_task(task)
    assert any("/tmp_workspace/sessions/" in t for t in targets)
    assert any("/root/.nanobot/logs/" in t for t in targets)
    assert not any("/root/.openclaw/agents/" in t for t in targets)
