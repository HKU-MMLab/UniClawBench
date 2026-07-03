from __future__ import annotations

from types import SimpleNamespace

from lib.supervision.user_simulator import build_user_simulator_prompt, validate_user_simulator_payload


def test_user_simulator_string_fields_do_not_split_into_characters() -> None:
    payload = validate_user_simulator_payload(
        {
            "mode": "nudge",
            "tone": "neutral",
            "candidate_feedback": "\u8bf7\u7ee7\u7eed\u6838\u5bf9\u89c6\u9891\u91cc\u7684\u660e\u786e\u63a8\u8350\u3002",
            "public_feedback_points": "\u8bf7\u76f4\u63a5\u57fa\u4e8e\u89c6\u9891\u5185\u5bb9\u7ee7\u7eed\u6838\u5bf9",
        }
    )
    assert payload["public_feedback_points"] == ["\u8bf7\u76f4\u63a5\u57fa\u4e8e\u89c6\u9891\u5185\u5bb9\u7ee7\u7eed\u6838\u5bf9"]


def test_user_simulator_prompt_repeats_authoritative_public_task_near_output_instructions() -> None:
    context = SimpleNamespace(
        task=SimpleNamespace(
            public_task="\u8bf7\u6253\u5f00\u64ad\u653e\u6700\u591a\u7684\u89c6\u9891\uff0c\u5e76\u4f9d\u636e\u89c6\u9891\u672c\u8eab\u5185\u5bb9\u5224\u65ad\u3002",
            user_simulator=SimpleNamespace(
                policy="",
                instructions="",
            ),
        )
    )
    prompt = build_user_simulator_prompt(context, {"role": "public_user_simulator"})
    assert "<<<ORIGINAL_PUBLIC_TASK>>>" in prompt
    assert "\u8bf7\u6253\u5f00\u64ad\u653e\u6700\u591a\u7684\u89c6\u9891\uff0c\u5e76\u4f9d\u636e\u89c6\u9891\u672c\u8eab\u5185\u5bb9\u5224\u65ad\u3002" in prompt
    assert "original public task is authoritative" in prompt.lower()


def test_user_simulator_prompt_ignores_role_cfg_instructions() -> None:
    """``codex.user_simulator.instructions`` MUST NOT leak into the rendered prompt.

    Task YAMLs sometimes still set this field; the public user simulator's only
    task-level customization channel is ``policy``. Leaking grading-style intent
    or supervisor language via ``instructions`` would blur the public/hidden
    boundary, so the builder silently drops it.
    """
    sentinel = "SHOULD_NOT_APPEAR_IN_USER_SIMULATOR_PROMPT"
    context = SimpleNamespace(
        task=SimpleNamespace(
            public_task="Original public task body.",
            user_simulator=SimpleNamespace(
                policy="real policy text here",
                instructions=sentinel,
            ),
        )
    )
    prompt = build_user_simulator_prompt(context, {"role": "public_user_simulator"})
    assert sentinel not in prompt
    assert "Task-Specific Instructions" not in prompt
    assert "real policy text here" in prompt
