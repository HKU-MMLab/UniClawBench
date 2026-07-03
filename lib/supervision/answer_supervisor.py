#!/usr/bin/env python3
from __future__ import annotations
import base64
import json
from typing import Any

from ..constants import ATTEMPT_STATES, CONFIDENCE_LEVELS, VERDICTS
from ..i18n import GUIDANCE_TAGS
from ..status import normalize_supervisor_attempt_state, normalize_supervisor_verdict
from ..templates.supervisor_default import DEFAULT_SUPERVISOR_INSTRUCTIONS
from .common import (
    SupervisorContext,
    append_role_history,
    build_session_prompt,
    clamp_score,
    coerce_text_list,
    prepare_role_workspace,
    role_home_dir,
    role_session_dir,
    role_workspace_dir,
    run_codex_prompt,
)


ANSWER_SUPERVISOR_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "verdict",
        "attempt_state",
        "recoverable",
        "score",
        "confidence",
        "rationale",
        "missing_artifacts",
        "guidance_tags",
    ],
    "properties": {
        "verdict": {"type": "string", "enum": sorted(VERDICTS)},
        "attempt_state": {"type": "string", "enum": sorted(ATTEMPT_STATES)},
        "recoverable": {"type": "boolean"},
        "score": {"type": "number"},
        "confidence": {"type": "string", "enum": sorted(CONFIDENCE_LEVELS)},
        "rationale": {"type": "string"},
        "missing_artifacts": {"type": "array", "items": {"type": "string"}},
        "guidance_tags": {"type": "array", "items": {"type": "string", "enum": sorted(GUIDANCE_TAGS)}},
    },
}


_IMAGE_POLICY_ERROR_NEEDLES = (
    "content_policy_violation",
    "input image may contain content that is not allowed",
    "invalid_request_error",
)

# 1x1 transparent PNG. Used only inside a role-scoped supervisor retry
# workspace after the model provider rejects an image inspection request.
_SAFE_IMAGE_PLACEHOLDER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _is_image_policy_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(needle in text for needle in _IMAGE_POLICY_ERROR_NEEDLES)


def _disable_image_inspection_for_retry(workspace: dict[str, Any]) -> dict[str, Any]:
    """Replace copied images in the supervisor workspace with safe placeholders.

    The original attempt artifacts live outside this role workspace and remain
    untouched. This fallback lets the supervisor grade from text, file names,
    transcript evidence, and result summaries when a provider-side image safety
    filter rejects one specific screenshot.
    """
    workspace_root = workspace["workspace_root"]
    manifest = dict(workspace.get("manifest") or {})
    image_rels = [str(rel) for rel in manifest.get("available_images") or []]
    redacted: list[str] = []
    for rel in image_rels:
        path = workspace_root / rel
        if not path.exists() or not path.is_file():
            continue
        try:
            path.write_bytes(_SAFE_IMAGE_PLACEHOLDER)
            redacted.append(rel)
        except OSError:
            continue

    note = (
        "# Image Inspection Disabled\n\n"
        "A previous supervisor attempt was rejected by the model provider while "
        "viewing one of the copied screenshots. The original run artifacts are "
        "unchanged outside this role workspace, but image pixels in this retry "
        "workspace have been replaced with safe placeholders. Grade from "
        "visible text artifacts, transcript/tool evidence, file paths, file "
        "presence, OCR/text summaries, and hidden references. Do not call "
        "`view_image`; do not treat placeholder pixels as evidence.\n"
    )
    note_path = workspace_root / "IMAGE_INSPECTION_DISABLED.md"
    note_path.write_text(note, encoding="utf-8")

    manifest["image_inspection_disabled"] = True
    manifest["image_inspection_disabled_reason"] = "provider image safety rejection during supervisor evaluation"
    manifest["redacted_image_placeholders"] = redacted
    manifest["available_images"] = []
    manifest["attached_images"] = []
    manifest_path = workspace_root / "workspace_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = str(workspace.get("readme") or "")
    readme += "\n## Image Inspection Disabled\n" + note.split("\n\n", 1)[1]
    readme_path = workspace_root / "README.md"
    readme_path.write_text(readme, encoding="utf-8")

    retry_workspace = dict(workspace)
    retry_workspace["manifest"] = manifest
    retry_workspace["images"] = []
    retry_workspace["readme"] = readme
    return retry_workspace


def build_answer_supervisor_prompt(context: SupervisorContext, workspace_manifest: dict[str, Any]) -> str:
    from .common import render_template
    from ..templates.answer_supervisor import TRANSCRIPT_CHUNKING_NOTE
    task_instructions = context.task.supervisor.instructions or DEFAULT_SUPERVISOR_INSTRUCTIONS
    # Only include the transcript_full/ usage guidance when the workspace
    # actually contains chunked transcripts. Tune the wording in
    # ``lib/templates/answer_supervisor.py::TRANSCRIPT_CHUNKING_NOTE``.
    chunked = workspace_manifest.get("chunked_transcripts") or []
    any_full_chunks = any(not entry.get("capped_only") for entry in chunked)
    transcript_chunking_note = TRANSCRIPT_CHUNKING_NOTE if any_full_chunks else ""
    role_instructions = render_template("answer_supervisor", {
        "task_instructions": task_instructions,
        "guidance_tags": ", ".join(sorted(GUIDANCE_TAGS)),
        "verdicts": ", ".join(sorted(VERDICTS)),
        "attempt_states": ", ".join(sorted(ATTEMPT_STATES)),
        "transcript_chunking_note": transcript_chunking_note,
    })
    return build_session_prompt(
        role_name="answer_supervisor",
        role_instructions=role_instructions,
        workspace_manifest=workspace_manifest,
    )


def validate_answer_supervisor_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalise a supervisor model output.

    Round-6 narrowing: the supervisor model's ``verdict`` is restricted
    to the task-semantic set ``{pass, continue, fail}``.  Legacy / mis-trained
    model outputs that still emit ``verdict=infra_error`` / ``rate_limit``
    (a pre-Round-6 schema variant) are translated to ``verdict=fail`` via
    ``lib.status.normalize_supervisor_verdict`` — semantically, "the run
    did not reach pass".  The framework-runtime flavour (rate_limit vs
    generic infra) is preserved separately by the framework's own
    ``structured_*_score`` synth path, which writes score.json directly
    and bypasses this validator.

    Unknown or empty verdicts still raise — they indicate a model output
    we cannot interpret as any of the three canonical task-semantic
    states.
    """
    raw_verdict = str(payload.get("verdict") or "").strip().lower()
    legacy_verdict_seen = raw_verdict in {"infra_error", "rate_limit"}
    verdict = normalize_supervisor_verdict(raw_verdict)
    if verdict not in VERDICTS:
        raise ValueError(f"invalid verdict: {raw_verdict!r}")

    raw_attempt_state = str(payload.get("attempt_state") or "").strip().lower()
    attempt_state = normalize_supervisor_attempt_state(raw_attempt_state)
    if attempt_state not in ATTEMPT_STATES:
        if verdict == "pass":
            attempt_state = "complete_and_passed"
        elif verdict == "fail":
            attempt_state = "terminal_failure"
        else:
            attempt_state = "in_progress"

    recoverable = bool(payload.get("recoverable"))
    if verdict == "pass":
        recoverable = False
    elif verdict == "continue":
        recoverable = True
    # ``verdict == "fail"`` keeps whatever the model said about
    # recoverability — supervisor may or may not think a retry would
    # succeed.  Framework-synth infra/rate paths set recoverable=False
    # themselves in structured_*_score.

    guidance_tags = coerce_text_list(payload.get("guidance_tags"), limit=10, item_max_chars=80)
    guidance_tags = [tag for tag in guidance_tags if tag in GUIDANCE_TAGS]
    confidence = str(payload.get("confidence") or "medium").strip().lower()
    if confidence not in CONFIDENCE_LEVELS:
        confidence = "medium"

    out = {
        "verdict": verdict,
        "attempt_state": attempt_state,
        "recoverable": recoverable,
        "score": clamp_score(float(payload.get("score", 0.0) or 0.0)),
        "confidence": confidence,
        "rationale": str(payload.get("rationale") or "").strip()[:2000],
        "missing_artifacts": coerce_text_list(payload.get("missing_artifacts"), limit=10, item_max_chars=200),
        "guidance_tags": guidance_tags,
    }
    if legacy_verdict_seen:
        # Leave a breadcrumb so operators can watch for models that keep
        # outputting the narrowed-away values.  Cheaper than logging on
        # every call.
        out["legacy_verdict_seen"] = raw_verdict
    return out


def run_answer_supervisor(context: SupervisorContext) -> dict[str, Any]:
    workspace = prepare_role_workspace(
        context,
        "answer_supervisor",
        include_hidden_references=True,
        include_privacy=True,
    )
    prompt = build_answer_supervisor_prompt(context, workspace["manifest"])
    role_cfg = context.task.supervisor
    try:
        response = run_codex_prompt(
            prompt=prompt,
            model=role_cfg.model,
            provider=role_cfg.provider,
            base_config_path=role_cfg.config_path,
            session_root=role_session_dir(context, "answer_supervisor"),
            workspace_root=role_workspace_dir(context, "answer_supervisor"),
            codex_home=role_home_dir(context, "answer_supervisor"),
            reasoning_effort=role_cfg.reasoning_effort,
            images=workspace["images"],
            workspace_manifest=workspace["manifest"],
            workspace_readme=workspace["readme"],
            output_schema=ANSWER_SUPERVISOR_OUTPUT_SCHEMA,
        )
    except RuntimeError as exc:
        if not _is_image_policy_error(exc):
            raise
        workspace = _disable_image_inspection_for_retry(workspace)
        prompt = (
            build_answer_supervisor_prompt(context, workspace["manifest"])
            + "\n\n# Provider Image Safety Fallback\n"
            + "A previous grading attempt failed while inspecting a screenshot. "
            + "For this retry, do not call `view_image`. The image files in this "
            + "role workspace are placeholders; use visible text artifacts, "
            + "transcripts, file presence, screenshot filenames, and hidden "
            + "reference text to assign the best supported score instead of "
            + "returning an infrastructure error.\n"
        )
        response = run_codex_prompt(
            prompt=prompt,
            model=role_cfg.model,
            provider=role_cfg.provider,
            base_config_path=role_cfg.config_path,
            session_root=role_session_dir(context, "answer_supervisor"),
            workspace_root=role_workspace_dir(context, "answer_supervisor"),
            codex_home=role_home_dir(context, "answer_supervisor"),
            reasoning_effort=role_cfg.reasoning_effort,
            images=[],
            workspace_manifest=workspace["manifest"],
            workspace_readme=workspace["readme"],
            output_schema=ANSWER_SUPERVISOR_OUTPUT_SCHEMA,
        )
    payload = validate_answer_supervisor_payload(dict(response["parsed"]))
    append_role_history(
        context,
        "answer_supervisor",
        {
            "turn": context.attempt.turn,
            "verdict": payload["verdict"],
            "attempt_state": payload["attempt_state"],
            "recoverable": payload["recoverable"],
            "score": payload["score"],
            "confidence": payload["confidence"],
            "rationale": payload["rationale"],
            "missing_artifacts": payload["missing_artifacts"],
            "guidance_tags": payload["guidance_tags"],
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
