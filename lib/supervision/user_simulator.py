#!/usr/bin/env python3
from __future__ import annotations
from typing import Any

from ..templates.user_simulator import DEFAULT_USER_SIMULATOR_POLICY
from .common import (
    SupervisorContext,
    append_role_history,
    build_session_prompt,
    coerce_text_list,
    prepare_role_workspace,
    role_home_dir,
    role_session_dir,
    role_workspace_dir,
    run_codex_prompt,
)


USER_SIMULATOR_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["mode", "tone", "candidate_feedback", "public_feedback_points"],
    "properties": {
        "mode": {"type": "string", "enum": ["silent", "nudge", "instruction"]},
        "tone": {"type": "string", "enum": ["neutral", "firm", "urgent"]},
        "candidate_feedback": {"type": "string"},
        "public_feedback_points": {"type": "array", "items": {"type": "string"}},
    },
}


def build_user_simulator_prompt(context: SupervisorContext, workspace_manifest: dict[str, Any]) -> str:
    from .common import render_template
    role_cfg = context.task.user_simulator
    # NOTE: role_cfg.instructions intentionally NOT used here. The user simulator's
    # task-level customization entry point is `policy`. Any task-specific scoring
    # intent belongs to the supervisor (codex.supervisor.instructions), not to the
    # public user simulator, which must read like a real user follow-up.
    role_instructions = render_template("user_simulator", {
        "policy": role_cfg.policy or DEFAULT_USER_SIMULATOR_POLICY,
        "public_task": context.task.public_task.strip(),
    })
    return build_session_prompt(
        role_name="public_user_simulator",
        role_instructions=role_instructions,
        workspace_manifest=workspace_manifest,
    )


def validate_user_simulator_payload(payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "nudge").strip().lower()
    if mode not in {"silent", "nudge", "instruction"}:
        mode = "nudge"
    tone = str(payload.get("tone") or "neutral").strip().lower()
    if tone not in {"neutral", "firm", "urgent"}:
        tone = "neutral"
    return {
        "mode": mode,
        "tone": tone,
        "candidate_feedback": str(payload.get("candidate_feedback") or "").strip()[:1200],
        "public_feedback_points": coerce_text_list(payload.get("public_feedback_points"), limit=12, item_max_chars=400),
    }


def run_public_user_simulator(context: SupervisorContext, user_handoff: dict[str, Any]) -> dict[str, Any]:
    supervisor_feedback = {
        "verdict": str(user_handoff.get("verdict") or ""),
        "attempt_state": str(user_handoff.get("attempt_state") or ""),
        "recoverable": bool(user_handoff.get("recoverable")),
        "score": user_handoff.get("score"),
    }
    workspace = prepare_role_workspace(
        context,
        "public_user_simulator",
        include_hidden_references=False,
        supervisor_feedback=supervisor_feedback,
    )
    prompt = build_user_simulator_prompt(context, workspace["manifest"])
    role_cfg = context.task.user_simulator
    response = run_codex_prompt(
        prompt=prompt,
        model=role_cfg.model,
        provider=role_cfg.provider,
        base_config_path=role_cfg.config_path,
        session_root=role_session_dir(context, "public_user_simulator"),
        workspace_root=role_workspace_dir(context, "public_user_simulator"),
        codex_home=role_home_dir(context, "public_user_simulator"),
        reasoning_effort=role_cfg.reasoning_effort,
        images=workspace["images"],
        workspace_manifest=workspace["manifest"],
        workspace_readme=workspace["readme"],
        output_schema=USER_SIMULATOR_OUTPUT_SCHEMA,
    )
    payload = validate_user_simulator_payload(dict(response["parsed"]))
    append_role_history(
        context,
        "public_user_simulator",
        {
            "turn": context.attempt.turn,
            "mode": payload["mode"],
            "tone": payload["tone"],
            "candidate_feedback": payload["candidate_feedback"],
            "public_feedback_points": payload["public_feedback_points"],
        },
    )
    payload["_debug"] = {
        "transport": response.get("transport"),
        "elapsed_ms": response.get("elapsed_ms"),
        "stdout": response.get("stdout"),
        "stderr": response.get("stderr"),
        "raw_response": response.get("raw_response"),
        "prompt": response.get("prompt"),
        "image_inputs": response.get("image_inputs"),
        "input_workspace": response.get("workspace_manifest"),
        "input_readme": response.get("workspace_readme"),
        "workspace_root": response.get("workspace_root"),
    }
    return payload
