from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from lib.supervision.answer_supervisor import validate_answer_supervisor_payload
from lib.supervision.codex import render_template
from lib.supervision.orchestrator import _normalize_answer_decision, build_public_feedback
from lib.supervision.content import _strip_edict_routing_note
from lib.supervision.transcripts import semantic_transcript_blocks


ROOT = Path(__file__).resolve().parents[2]


def test_answer_supervisor_validates_current_schema() -> None:
    payload = validate_answer_supervisor_payload(
        {
            "verdict": "continue",
            "attempt_state": "incomplete",
            "recoverable": True,
            "score": 0.4,
            "rationale": "partial evidence only \u2014 missing clear screenshot",
            "confidence": "high",
            "missing_artifacts": ["clear supporting screenshot"],
            "guidance_tags": "save_supporting_screenshot",
        }
    )
    assert payload["verdict"] == "continue"
    assert payload["attempt_state"] == "incomplete"
    assert payload["score"] == 0.4
    assert payload["confidence"] == "high"
    assert payload["rationale"] == "partial evidence only \u2014 missing clear screenshot"
    assert payload["missing_artifacts"] == ["clear supporting screenshot"]
    assert payload["guidance_tags"] == ["save_supporting_screenshot"]
    assert "reference_understanding" not in payload
    assert "failure_reasons" not in payload
    assert "focus_points" not in payload
    assert "leakage_risk" not in payload


def test_validate_answer_supervisor_coerces_invalid_attempt_state() -> None:
    # Invalid attempt_state with verdict=pass should be coerced to complete_and_passed
    payload = validate_answer_supervisor_payload({
        "verdict": "pass",
        "attempt_state": "bogus_state",
        "recoverable": True,
        "score": 1.0,
        "rationale": "Looks good.",
        "confidence": "high",
        "missing_artifacts": [],
        "guidance_tags": [],
    })
    assert payload["attempt_state"] == "complete_and_passed"
    assert payload["recoverable"] is False

    # Invalid attempt_state with verdict=fail should become terminal_failure
    payload2 = validate_answer_supervisor_payload({
        "verdict": "fail",
        "attempt_state": "",
        "recoverable": False,
        "score": 0.0,
        "rationale": "Failed.",
        "confidence": "low",
        "missing_artifacts": [],
        "guidance_tags": [],
    })
    assert payload2["attempt_state"] == "terminal_failure"


def test_build_public_feedback_uses_generic_guidance_tags() -> None:
    payload = build_public_feedback(
        "Search YouTube for best earbuds review, find the top pick.",
        {
            "verdict": "continue",
            "attempt_state": "complete_but_failed",
            "guidance_tags": [
                "save_supporting_screenshot",
                "verify_evidence_matches_conclusion",
            ],
        },
    )
    joined = "\n".join([payload["public_summary"], *payload["public_feedback_points"]])
    assert "screenshot" in joined.lower() or "evidence" in joined.lower()
    assert payload["verdict"] == "continue"


def test_normalize_answer_decision_pass_sets_complete_and_passed() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=2),
        attempt=SimpleNamespace(turn=1),
    )
    answer = {"verdict": "pass", "attempt_state": "incomplete", "recoverable": True, "score": 0.9}
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "pass"
    assert result["attempt_state"] == "complete_and_passed"
    assert result["recoverable"] is False


def test_normalize_answer_decision_upgrades_fail_to_continue() -> None:
    # Low score + fail with budget + guidance → flip to continue so the
    # user simulator gets another turn.
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=2, success_threshold=0.9),
        attempt=SimpleNamespace(turn=1),
    )
    answer = {
        "verdict": "fail",
        "attempt_state": "complete_but_failed",
        "recoverable": False,
        "score": 0.3,
        "guidance_tags": ["save_visible_evidence"],
        "rationale": "Evidence is weak.",
    }
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "continue"
    assert result["attempt_state"] == "complete_but_failed"
    assert result["recoverable"] is True


def test_normalize_answer_decision_no_budget_keeps_fail() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=1, success_threshold=0.9),
        attempt=SimpleNamespace(turn=2),  # turn 2 means 1 followup already used
    )
    answer = {
        "verdict": "fail",
        "attempt_state": "terminal_failure",
        "recoverable": False,
        "score": 0.1,
        "guidance_tags": [],
        "rationale": "",
    }
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "fail"
    assert result["recoverable"] is False


# ── Phase 8: score-based promotion lives ONLY in lib.status.apply_score_based_promotion ──
#
# Earlier code in ``_normalize_answer_decision`` rewrote any non-pass /
# non-infra / non-rate verdict into ``pass`` whenever ``score >= success_threshold``.
# That override bypassed the user-simulator loop when the supervisor still
# wanted another turn (verdict=continue). Promotion now lives in
# ``lib.status.apply_score_based_promotion`` and is gated by the runtime
# final-status (``budget_exhausted``/``global_timeout``/``running``), not by
# the supervisor's verdict.


def test_normalize_answer_decision_does_not_promote_continue_at_threshold() -> None:
    """High score must NOT silently convert ``continue`` into ``pass``."""
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=3, success_threshold=0.9),
        attempt=SimpleNamespace(turn=1),
    )
    answer = {
        "verdict": "continue",
        "attempt_state": "incomplete",
        "recoverable": True,
        "score": 0.9,  # exactly at threshold
        "guidance_tags": ["follow_up_for_evidence"],
        "rationale": "Score is high but still want one more confirmation.",
    }
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "continue"
    assert result["attempt_state"] == "incomplete"
    assert result["recoverable"] is True


def test_normalize_answer_decision_does_not_promote_continue_above_threshold() -> None:
    """Even a perfect score must keep ``continue`` if the supervisor said so."""
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=3, success_threshold=0.9),
        attempt=SimpleNamespace(turn=1),
    )
    answer = {
        "verdict": "continue",
        "attempt_state": "in_progress",
        "recoverable": True,
        "score": 1.0,
        "guidance_tags": [],
        "rationale": "Still exploring.",
    }
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "continue"
    assert result["attempt_state"] == "in_progress"


def test_normalize_answer_decision_does_not_promote_fail_at_threshold() -> None:
    """High score with verdict=fail must NOT be promoted to pass.

    Without remaining follow-ups the verdict stays ``fail``; score-based
    promotion (if any) is decided later by
    ``lib.status.apply_score_based_promotion`` against the runtime final
    status, never here by overriding the supervisor.
    """
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=1, success_threshold=0.9),
        attempt=SimpleNamespace(turn=2),  # all follow-ups already used
    )
    answer = {
        "verdict": "fail",
        "attempt_state": "terminal_failure",
        "recoverable": False,
        "score": 0.95,  # above threshold
        "guidance_tags": [],
        "rationale": "Numeric score high but answer is misleading.",
    }
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "fail"
    assert result["attempt_state"] == "terminal_failure"
    assert result["recoverable"] is False


def test_normalize_answer_decision_pass_with_low_score_stays_pass() -> None:
    """Symmetric check: an explicit ``pass`` is honoured regardless of score."""
    context = SimpleNamespace(
        task=SimpleNamespace(max_user_followups=2, success_threshold=0.9),
        attempt=SimpleNamespace(turn=1),
    )
    answer = {
        "verdict": "pass",
        "attempt_state": "complete_and_passed",
        "recoverable": False,
        "score": 0.1,  # supervisor judged pass despite low numeric score
    }
    result = _normalize_answer_decision(context, answer)
    assert result["verdict"] == "pass"
    assert result["attempt_state"] == "complete_and_passed"
    assert result["recoverable"] is False


def test_strip_edict_routing_note_removes_identity_block() -> None:
    prompt = (
        "Runtime context:\n"
        "- Task workspace: /tmp_workspace\n\n"
        "EDICT routing note:\n"
        "- \u4f60\u5f53\u524d\u5904\u5728\u4e09\u7701\u516d\u90e8\u591a agent \u4f53\u7cfb\u4e2d\u3002\n"
        "- \u628a\u4e0b\u9762\u539f\u59cb\u4efb\u52a1\u5f53\u4f5c\u201c\u7687\u4e0a\u539f\u8bdd\u201d\u5904\u7406\uff0c\u800c\u4e0d\u662f\u666e\u901a\u5355 agent \u6d4f\u89c8\u5668\u4efb\u52a1\u3002\n"
        "\n"
        "\u7687\u4e0a\u539f\u8bdd\uff1a\n\n"
        "\u8bf7\u5728 Bilibili \u641c\u7d22\u201c\u6d17\u9762\u5976\u6d4b\u8bc4\u201d\u3002\n"
    )
    cleaned = _strip_edict_routing_note(prompt)
    assert "EDICT routing note" not in cleaned
    assert "\u7687\u4e0a\u539f\u8bdd" not in cleaned
    assert "\u592a\u5b50" not in cleaned
    assert "\u4e09\u7701\u516d\u90e8" not in cleaned
    assert "Runtime context" in cleaned
    assert "Bilibili" in cleaned


def test_strip_edict_routing_note_noop_for_non_edict() -> None:
    prompt = "Runtime context:\n- Task workspace: /tmp_workspace\n\n\u8bf7\u5728 Bilibili \u641c\u7d22\u3002\n"
    assert _strip_edict_routing_note(prompt) == prompt


def test_build_initial_prompt_strip_pipeline_hides_edict_routing_from_supervisor() -> None:
    """End-to-end pin: executor prompt -> supervisor-visible text -> no leak.

    For ``openclaw_edict`` the executor's initial prompt prepends a Chinese
    routing note so \u592a\u5b50 understands it is the entry agent of \u4e09\u7701\u516d\u90e8.
    Supervisor / user-simulator must NEVER see that note (it is executor-only
    framing about internal multi-agent coordination \u2014 leaking it would make
    the supervisor / user-simulator mimic the imperial-court register and
    blur the public/hidden boundary).

    This test wires the two real pieces together (``build_initial_prompt`` ->
    ``_strip_edict_routing_note``) and asserts the supervisor-visible result
    contains no routing markers.
    """
    from types import SimpleNamespace

    from lib.runner.agents import build_initial_prompt

    real_body = "\u8bf7\u5728 Bilibili \u641c\u7d22\u201c\u6d17\u9762\u5976\u6d4b\u8bc4\u201d\uff0c\u5e76\u4fdd\u5b58\u622a\u56fe\u3002"
    task = SimpleNamespace(
        agent_sys="openclaw_edict",
        task=real_body,
        task_snapshot="",
        task_id="t",
        privacy=[],
        injection_root=Path("/tmp/fake"),
        skills=[],
        model="kimi-k2.6",
    )
    initial_prompt = build_initial_prompt(task)
    # The executor sees the routing note.
    assert "EDICT routing note" in initial_prompt
    assert "\u7687\u4e0a\u539f\u8bdd" in initial_prompt
    assert "\u4e09\u7701\u516d\u90e8" in initial_prompt
    assert real_body in initial_prompt

    # Now the supervisor / user-simulator side: strip then verify the
    # routing markers are gone but the real task body survives.
    visible = _strip_edict_routing_note(initial_prompt)
    for forbidden in (
        "EDICT routing note:",
        "\u7687\u4e0a\u539f\u8bdd",
        "\u4e09\u7701\u516d\u90e8",
        "\u592a\u5b50\u5206\u62e3",
        "\u4e2d\u4e66\u7701",
        "\u95e8\u4e0b\u7701",
        "\u5c1a\u4e66\u7701",
    ):
        assert forbidden not in visible, (
            f"routing marker {forbidden!r} leaked into supervisor-visible prompt"
        )
    assert real_body in visible
    assert "Runtime context" in visible


def test_build_initial_prompt_no_routing_note_for_non_edict_backend() -> None:
    """openclaw / nanobot must NOT receive the EDICT routing note."""
    from types import SimpleNamespace

    from lib.runner.agents import build_initial_prompt

    for agent_sys in ("openclaw", "nanobot"):
        task = SimpleNamespace(
            agent_sys=agent_sys,
            task="Just a plain task body.",
            task_snapshot="",
            task_id="t",
            privacy=[],
            injection_root=Path("/tmp/fake"),
            skills=[],
            model="gpt-5.4",
        )
        prompt = build_initial_prompt(task)
        assert "EDICT routing note" not in prompt
        assert "\u7687\u4e0a\u539f\u8bdd" not in prompt
        assert "\u4e09\u7701\u516d\u90e8" not in prompt


def test_semantic_transcript_blocks_include_agent_id(tmp_path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    events = [
        {"type": "message", "agentId": "taizi", "message": {"role": "user", "content": [{"type": "text", "text": "\u8bf7\u641c\u7d22"}]}},
        {"type": "message", "agentId": "zhongshu", "message": {"role": "assistant", "content": [{"type": "text", "text": "\u5df2\u6253\u5f00\u6d4f\u89c8\u5668"}]}},
        {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "\u5355 agent \u56de\u590d"}]}},
    ]
    transcript.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8")
    blocks = semantic_transcript_blocks(transcript)
    assert blocks[0]["kind"] == "user_message"
    assert blocks[0]["agent_id"] == "taizi"
    assert blocks[1]["kind"] == "assistant_text"
    assert blocks[1]["agent_id"] == "zhongshu"
    assert "agent_id" not in blocks[2]


def test_templates_load_and_render() -> None:
    # session_wrapper
    result = render_template("session_wrapper", {
        "role_name": "test_role",
        "role_instructions": "Test instructions.",
        "key_files_list": "- `file.txt`",
    })
    assert "You are Codex session role: test_role." in result
    assert "Test instructions." in result
    assert "- `file.txt`" in result

    # answer_supervisor — all placeholders must be provided; leave
    # transcript_chunking_note blank for the non-chunked case (matches
    # build_answer_supervisor_prompt's default path in the real runner).
    # Round-6 adds {verdicts} alongside {attempt_states} so the prompt
    # enum stays in sync with constants.VERDICTS.
    result = render_template("answer_supervisor", {
        "task_instructions": "Judge strictly.",
        "guidance_tags": "tag_a, tag_b",
        "verdicts": "pass, continue, fail",
        "attempt_states": "in_progress, incomplete",
        "transcript_chunking_note": "",
    })
    assert "hidden answer supervisor" in result
    assert "Judge strictly." in result
    assert "tag_a, tag_b" in result
    assert "rationale" in result
    assert "pass, continue, fail" in result

    # user_simulator
    result = render_template("user_simulator", {
        "task_instructions": "",
        "policy": "Be a real user.",
        "public_task": "Do something.",
    })
    # Identity line is "You are the **original end-user (the human)**" —
    # match the current wording.
    assert "original end-user" in result
    assert "Be a real user." in result
    assert "<<<ORIGINAL_PUBLIC_TASK>>>" in result
    assert "Do something." in result
    assert "candidate_feedback" in result


# ── Phase 5: TEMPLATE carries the contract, not DEFAULT_SUPERVISOR_INSTRUCTIONS ──


def test_default_supervisor_instructions_does_not_redeclare_template_contract() -> None:
    """Phase 5 slim: the default instructions string is a posture supplement.

    The hard contract — attempt-state enum, verdict enum, schema list — lives
    in ``answer_supervisor.py:TEMPLATE``. Keeping it out of the default
    instructions removes the drift risk where two sources would have to be
    kept aligned by hand.
    """
    from lib.templates.supervisor_default import DEFAULT_SUPERVISOR_INSTRUCTIONS

    blob = DEFAULT_SUPERVISOR_INSTRUCTIONS.lower()
    # The enum names live in TEMPLATE; default instructions must not list them.
    for absent in (
        "in_progress",
        "incomplete",
        "complete_but_failed",
        "complete_and_passed",
        "terminal_failure",
        "prefer `continue`",
    ):
        assert absent.lower() not in blob, f"{absent!r} leaked into default instructions"


def test_supervisor_template_still_carries_schema_when_default_instructions_used() -> None:
    """Even with the slimmed default, the rendered supervisor prompt must
    still expose the verdict enum and attempt-state list (because TEMPLATE
    contributes them). This test would fail if a future refactor moved them
    out of TEMPLATE without restoring them somewhere.
    """
    from lib.templates.supervisor_default import DEFAULT_SUPERVISOR_INSTRUCTIONS

    rendered = render_template(
        "answer_supervisor",
        {
            "task_instructions": DEFAULT_SUPERVISOR_INSTRUCTIONS,
            "guidance_tags": "tag_a, tag_b",
            "verdicts": "pass, continue, fail",
            "attempt_states": "in_progress, incomplete, complete_but_failed, complete_and_passed, terminal_failure",
            "transcript_chunking_note": "",
        },
    )
    assert "pass, continue, fail" in rendered
    assert "in_progress" in rendered
    assert "terminal_failure" in rendered
    # And the default's posture text is present too (posture supplement, not contract).
    assert "missing_artifacts" in rendered
