#!/usr/bin/env python3
"""Umbrella re-exporter + context dataclasses for ``lib.supervision``.

Two things live here:

1. **The four supervision context dataclasses** (formerly in
   ``contexts.py``, folded in by the third-round merge).  They live at
   the top of this file with no inter-supervision imports so any
   helper sub-module can ``from .common import SupervisorContext``
   without risking a circular import.

2. **The umbrella re-export table** that flattens every public symbol
   from ``.codex`` / ``.files`` / ``.transcripts`` / ``.images`` /
   ``.payloads`` / ``.workspace`` into ``lib.supervision.common`` so
   the test suite + the few callers that import from this namespace
   keep working.  Lazy imports inside ``codex.py`` and ``payloads.py``
   functions prevent circular issues with the bottom-level helpers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ── Supervision context dataclasses ──────────────────────────────────
# The four dataclasses here are the shape of every argument the
# ``answer_supervisor`` / ``user_simulator`` / ``feedback_rewriter`` /
# ``orchestrator`` roles receive.  They capture the task, the attempt,
# and each Codex role's runtime (model, provider, config, reasoning
# effort) without dragging the rest of common.py's transitive imports
# into callers that only need the types.


@dataclass
class CodexRoleRuntimeContext:
    role: str
    model: str
    provider: str
    config_path: Path
    reasoning_effort: str
    instructions: str = ""
    policy: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["config_path"] = str(self.config_path)
        return payload


@dataclass
class TaskSupervisorContext:
    task_id: str
    task_file: Path
    injection_root: Path
    run_root: Path
    public_task: str
    references: list[str]
    success_threshold: float
    max_user_followups: int
    user_simulator: CodexRoleRuntimeContext
    supervisor: CodexRoleRuntimeContext
    privacy: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["task_file"] = str(self.task_file)
        payload["injection_root"] = str(self.injection_root)
        payload["run_root"] = str(self.run_root)
        payload["user_simulator"]["config_path"] = str(self.user_simulator.config_path)
        payload["supervisor"]["config_path"] = str(self.supervisor.config_path)
        return payload


@dataclass
class AttemptSupervisorContext:
    attempt: int
    turn: int
    out_dir: Path
    result_dir: Path
    prompt_file: Path
    transcript_file: Path
    tool_usage_file: Path
    runtime_probe_file: Path
    prompt_kind: str = "primary"
    stage_id: str = "primary"
    stage_type: str = "primary"
    stage_index: int = 1
    agent_container: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("out_dir", "result_dir", "prompt_file", "transcript_file", "tool_usage_file", "runtime_probe_file"):
            payload[key] = str(payload[key])
        return payload


@dataclass
class SupervisorContext:
    task: TaskSupervisorContext
    attempt: AttemptSupervisorContext

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.to_dict(),
            "attempt": self.attempt.to_dict(),
        }
# ``ROOT`` (repo root path) is defined once in ``.content`` and re-exported
# so ``lib.supervision_common.ROOT`` and ``lib.supervision.ROOT`` keep
# resolving for older callers.
from .content import ROOT  # noqa: E402,F401
# Codex runtime helpers live in ``.codex`` now — re-exported here so legacy
# ``from lib.supervision.common import run_codex_prompt`` (and similar) keep
# working. ``codex.py`` imports the non-codex helpers it needs
# (``sanitize_codex_context_text`` / ``parse_first_json_object`` /
# ``reset_dir`` / ``_role_workspace_prompt_files``) lazily inside function
# bodies, which is what lets this top-level re-export be non-circular.
from .codex import (  # noqa: E402,F401
    CONTAINER_CODEX_HOME,
    CONTAINER_RUNTIME_DIR,
    CONTAINER_SESSION_ROOT,
    CONTAINER_WORKDIR,
    DEFAULT_CODEX_CONFIG,
    DEFAULT_CODEX_IMAGE,
    DEFAULT_CODEX_MAX_ATTEMPTS,
    DEFAULT_CODEX_RETRY_BACKOFF_SECONDS,
    DEFAULT_CODEX_TIMEOUT_SECONDS,
    LEGACY_CODEX_BIN,
    TOOLLESS_RETRY_NEEDLES,
    TRANSIENT_CODEX_ERROR_NEEDLES,
    _codex_provider_matches,
    _codex_provider_models,
    build_codex_execution_prompt,
    build_session_prompt,
    codex_env_file_candidates,
    codex_env_keys,
    codex_retry_backoff_seconds,
    codex_rollout_summary,
    ensure_isolated_codex_home,
    is_transient_codex_error,
    latest_codex_rollout_log,
    load_codex_base_config,
    render_codex_config,
    render_template,
    required_codex_env_keys,
    resolve_codex_env_vars,
    resolve_codex_provider,
    run_codex_prompt,
    run_codex_via_container,
    session_path_to_container,
    should_force_toolless_retry,
)
# Low-level file / text helpers (formerly files.py) now live in
# ``.content`` Section 1 — re-export here so legacy ``from
# lib.supervision.common import read_text`` (and similar) keep working.
from .content import (  # noqa: E402,F401
    _split_text_list_candidate,
    _trim_middle,
    clamp_score,
    coerce_text_list,
    copy_file_into,
    copy_tree_into,
    file_kind,
    read_json,
    read_text,
    reset_dir,
    sanitize_codex_context_text,
    summarize_file,
    summarize_result_dir,
    write_json,
)
# Transcript parsing / handoff / multi-agent summaries live in ``.transcripts``
# now — re-exported here so legacy ``from lib.supervision.common import
# semantic_transcript_blocks`` (and similar) keep working. ``transcripts.py``
# depends only on ``.contexts`` + ``.files`` (both leaf-ward), so this
# top-level re-export is non-circular.
from .transcripts import (  # noqa: E402,F401
    EDICT_AGENT_LABELS,
    _clip_block_list_middle,
    _content_text,
    _is_noisy_tool_name,
    _jsonish_text_preview,
    _timestamp_label,
    _tool_arguments_summary,
    build_agent_session_summaries,
    build_handoff_trace,
    build_multi_agent_visible_payload,
    load_agent_manifest,
    operation_trace_summary,
    parse_agent_session_target,
    runtime_probe_payload,
    semantic_transcript_blocks,
    summarize_recent_tool_calls,
)
# Image + reference discovery / OCR cache (formerly images.py) now in
# ``.content`` Section 2 — re-export here so legacy callers keep
# resolving.
from .content import (  # noqa: E402,F401
    _IMAGE_SUFFIXES,
    _SUPERVISOR_IMAGE_JPEG_QUALITY,
    _SUPERVISOR_IMAGE_MAX_BYTES,
    _SUPERVISOR_IMAGE_MAX_SIDE_PX,
    _downscale_image_via_convert,
    collect_image_ocr_blocks,
    collect_reference_images,
    collect_reference_text_blocks,
    collect_visible_images,
    copy_supervisor_asset,
    extract_image_ocr_text,
    image_ocr_cache_path,
    primary_eval_rule_block,
    resolve_reference_path,
)
# Supervisor payload builders + response parser (formerly payloads.py)
# now in ``.content`` Section 3.
from .content import (  # noqa: E402,F401
    _strip_edict_routing_note,
    build_hidden_payload,
    build_visible_payload,
    parse_first_json_object,
    prompt_context_text,
    redacted_supervision_context,
)


from .workspace import (  # noqa: E402,F401
    _TRANSCRIPT_CAPPED_HEAD_BYTES,
    _TRANSCRIPT_CAPPED_TAIL_BYTES,
    _TRANSCRIPT_CHUNK_MAX_BYTES,
    _build_transcript_capped_view,
    _copy_privacy_workspace_files,
    _copy_reference_workspace_files,
    _copy_transcript_with_optional_chunking,
    _copy_visible_workspace_files,
    _role_workspace_prompt_files,
    _transcript_line_chunks,
    _workspace_file_entry,
    append_role_history,
    build_role_workspace_readme,
    load_role_history,
    prepare_role_workspace,
    role_history_path,
    role_home_dir,
    role_runtime_dir,
    role_session_dir,
    role_workspace_dir,
)
