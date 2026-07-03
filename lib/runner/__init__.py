#!/usr/bin/env python3
"""Public-API facade for ``lib.runner``.

This package is the runner's *external* surface. ``__all__`` curates the
stable names that external callers (scripts, third-party consumers, the
test suite's surface pin) are expected to import. Symbols that don't
appear in ``__all__`` — in particular underscore-prefixed helpers and
backend-specific constants — are not part of the public contract: they
remain reachable via deep imports (``from lib.runner.evaluation import
_assistant_text``) but should not be picked up by
``from lib.runner import *`` or by anyone building a long-term plugin.

When adding a new public name, place its import in the body below AND
add it to ``__all__`` at the bottom. When removing or renaming a public
name, also update ``docs/deprecations.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..constants import CONTINUATION_DONE_MARKER
from ..defaults import (
    AGENT_SESSION_ID,
    BROWSER_HEADED,
    DEFAULT_IMAGE,
    DEFAULT_IMAGE_BY_AGENT_SYS,
    DEFAULT_MODELS_CONFIG,
    DEFAULT_SHARED_ENV_FILE,
    EXECUTOR_CONTEXT_WINDOW_TOKENS,
    RECORDING_DISPLAY,
    RECORDING_FINAL,
    RECORDING_INPUT_FPS,
    RECORDING_LOG,
    RECORDING_OUTPUT_FPS,
    RECORDING_PID_FILE,
    RECORDING_RAW,
    RECORDING_SPEEDUP,
    RECORDING_STOP_WAIT_STEPS,
    RECORDING_SUPPORTED_AGENT_SYSTEMS,
    RECORDING_VIDEO_SIZE,
    RESULTS_ROOT,
)
from ..proxy import (
    acquire_shared_proxy_tunnel,
    build_proxy_tunnel_command,
    discover_active_proxy_adapter_log_paths,
    normalize_provider_proxy_spec,
    provider_proxy_spec,
    read_proxy_usage_events,
    read_proxy_usage_events_across_all_logs,
    release_shared_proxy_tunnel,
    start_proxy_adapter,
    start_proxy_tunnel,
    stop_proxy_tunnel,
    DEFAULT_PROXY_KIND,
    DEFAULT_PROXY_WAIT_SECONDS,
    PROXY_ADAPTER_LOG_PATH,
    PROXY_REGISTRY_ROOT,
)
from ..supervision.codex import load_codex_base_config, resolve_codex_provider
from ..supervision.common import (
    AttemptSupervisorContext,
    CodexRoleRuntimeContext,
    SupervisorContext,
    TaskSupervisorContext,
)
from ..supervision.content import clamp_score
from ..supervision.orchestrator import run_supervisor
from ..supervision.content import redacted_supervision_context
from ..supervision.transcripts import EDICT_AGENT_LABELS
from ..templates.executor_runtime import EDICT_ROUTING_NOTE, EXECUTOR_RUNTIME_PREFIX_LINES
from ..task import TaskSpec, canonical_agent_sys, discover_task_files, load_task, validate_agent_sys


# ROOT is the repo root (parents[2] = lib/runner/__init__.py → lib/runner → lib → repo).
# It is also defined in ``lib/defaults.py`` and re-exported from ``task_config.py``
# — kept here for legacy consumers that do ``from lib.runner import ROOT``.
ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------
# Media pipeline (consolidated from the old ``recording`` + ``images``
# modules in the third-round refactor).  Three concerns live there:
#  * Timeline recorder + ffmpeg desktop-video session
#  * Inline-image salvage (base64 → ``inline_images/<hash>.<ext>``)
#  * Base64-as-text image file rewriter
# --------------------------------------------------------------------------


from .media import (  # noqa: E402  (timeline + recording + inline-image salvage)
    TimelineRecorder,
    active_inline_images_dir,
    active_timeline_recorder,
    attach_inline_images_dir,
    recording_session,
    start_recording,
    stop_recording,
    timeline_span,
)




# NANOBOT_TRANSCRIPT_TARGETS now lives in ``task_config`` (consumed by
# ``transcript_targets_for_task``) and is re-exported via the import above.

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------
# Task spec + model registry helpers — extracted to ``task_config.py``.
# --------------------------------------------------------------------------


from .task_config import (  # noqa: E402  (task spec + model registry helpers)
    NANOBOT_TRANSCRIPT_TARGETS,
    RUNS,
    build_runtime_task_spec,
    collect_task_proxy_specs,
    compose_model_ref,
    default_agent_id_for_agent_sys,
    default_image_for_agent_sys,
    effective_agent_id_for_task,
    load_models_payload,
    managed_task_proxy_tunnels,
    model_id_for_backend,
    model_slug,
    normalize_agent_sys,
    override_codex_role_runtime,
    override_task_runtime,
    providers_from_models_payload,
    reset_task_run_root,
    resolve_model_ref,
    resolve_models_provider_entry,
    setting_root,
    slugify,
    strip_model_provider,
    task_run_root,
    transcript_targets_for_task,
)


# --------------------------------------------------------------------------
# EDICT (三省六部) runtime assets + AGENTS.md / TOOLS.md renderers
# — extracted to ``edict.py``.
# --------------------------------------------------------------------------


from .edict import (  # noqa: E402  (edict multi-agent assets + renderers)
    EDICT_AGENTS_ROOT,
    EDICT_ASSETS_ROOT,
    EDICT_BACKEND_MODELS_ROOT,
    EDICT_DATA_ROOT,
    EDICT_DEMO_CONFIG,
    EDICT_DEMO_DATA_ROOT,
    EDICT_DEMO_SEED_FILES,
    EDICT_GLOBAL_MD,
    EDICT_GROUPS_ROOT,
    EDICT_RUNTIME_ROOT,
    EDICT_SCRIPTS_ROOT,
    build_edict_agents_md,
    build_edict_tools_md,
    edict_agent_group,
    edict_agent_ids,
    edict_agent_specs,
    edict_repo_dir_for_task,
    read_text_if_exists,
    render_edict_soul,
)


# --------------------------------------------------------------------------
# openclaw session/transcript path discovery — extracted to ``sessions.py``.
# --------------------------------------------------------------------------


from .sessions import (  # noqa: E402  (openclaw agent transcript path resolution)
    resolve_openclaw_agent_all_session_paths,
    resolve_openclaw_agent_transcript_paths,
    resolve_openclaw_transcript_path,
)


# --------------------------------------------------------------------------
# openclaw config-fragment helpers + per-container config injection
# — extracted to ``openclaw.py``.
# --------------------------------------------------------------------------


from .openclaw import (  # noqa: E402  (openclaw config fragment + injection helpers)
    OPENCLAW_CONFIG_VALIDATE_STRICT,
    OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS,
    build_openclaw_config_script,
    configured_openclaw_image_model,
    normalize_openclaw_config_fragment,
    openclaw_agent_models_registry,
    openclaw_model_supports_image,
    select_openclaw_image_model,
    validate_openclaw_config,
)


# --------------------------------------------------------------------------
# Infra-error classifiers (provider quota / supervisor transport /
# container boot + runtime) — extracted to ``errors.py``.
# --------------------------------------------------------------------------


from .errors import (  # noqa: E402  (provider / supervisor / container error classifiers)
    RETRYABLE_CONTAINER_BOOT_PATTERNS,
    RETRYABLE_CONTAINER_RUNTIME_PATTERNS,
    detect_infra_error,
    detect_openclaw_rate_limit,
    detect_retryable_container_boot_error,
    detect_retryable_container_runtime_error,
    detect_supervisor_infra_error,
    should_retry_transient_followup,
)


from .container_lifecycle import (  # noqa: E402  (pre_exec + container boot + services — merged in Phase 2.3)
    BROWSER_GATEWAY_LOG,
    CONTAINER_HOST_ALIASES,
    PreExecError,
    browser_profile_running,
    browser_service_ready,
    build_proxy_env_script,
    ensure_gateway_ready,
    ensure_openclaw_runtime_ready,
    gateway_ready,
    inject_edict_config,
    inject_nanobot_config,
    inject_openclaw_config,
    prepare_runtime,
    run_pre_exec_scripts,
    runtime_base_skill_fallbacks,
    runtime_base_skills,
    start_container,
    start_desktop,
    start_gateway,
    start_openclaw_browser_profile,
    start_services,
    task_likely_uses_browser,
)


from .agents import (  # noqa: E402  (executor agent dispatch + prompt rendering)
    AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS,
    build_continuation_prompt,
    build_initial_prompt,
    prompt_prefix,
    run_agent,
    run_monitored_agent,
    run_nanobot_agent,
    run_openclaw_agent,
)



from .docker import (  # noqa: E402  (extracted docker/subprocess primitives)
    container_exists,
    copy_tree_contents_to_container,
    docker_cp_from_container,
    docker_cp_to_container,
    docker_exec,
    docker_rm,
    docker_write_text_file,
    run,
)
# NOTE: we intentionally do NOT re-export ``docker`` (the CLI wrapper
# function) at the package level. That name would shadow the
# ``lib.runner.docker`` submodule and break ``monkeypatch.setattr(
# "lib.runner.docker.<name>", fake)`` string paths. Callers that need the
# helper should import it directly from ``lib.runner.docker``.


# --------------------------------------------------------------------------
# Per-attempt artifact collection + usage ledger bookkeeping
# — extracted to ``artifacts.py``.
# --------------------------------------------------------------------------


from .artifacts import (  # noqa: E402  (attempt artifacts entry + edict fan-out)
    AGENT_SESSION_ARTIFACTS_DIR,
    PRIVATE_SERVICE_ROOT,
    append_jsonl,
    append_text,
    collect_attempt_artifacts,
    collect_edict_agent_session_artifacts,
    collect_runtime_probe,
    normalize_proxy_value,
    private_service_dir,
    supervision_component_summary,
    write_supervision_component_artifacts,
)
from .usage_ledger import (  # noqa: E402  (token accounting)
    append_attempt_request_log,
    append_executor_usage_ledger,
    append_role_usage_ledger,
    attempt_task_id,
    build_attempt_usage_payload,
    compute_executor_token_usage,
)


from .evaluation import (  # noqa: E402  (supervisor-side evaluation + continuation)
    apply_executor_completion_gate,
    apply_privacy_cap_to_supervision_decision,
    apply_privacy_leakage_cap,
    assistant_signaled_completion,
    codex_role_context,
    continuation_decision,
    edict_primary_still_routing,
    evaluate_attempt,
    executor_completion_state,
    last_message_payload,
    scan_visible_artifacts_for_privacy_leaks,
)


from .transcripts import (  # noqa: E402  (transcript parsing / normalization / merge)
    annotate_transcript_with_agent,
    build_tool_usage_summary,
    load_tool_usage_file,
    merge_agent_transcripts,
    normalize_nanobot_session_transcript,
    normalize_transcript_text,
    parse_json_lines,
    reconstruct_tool_spans,
    summarize_transcript_tools,
    transcript_event_timestamp,
    transcript_is_event_stream,
)


# --------------------------------------------------------------------------
# Top-level task / attempt / batch orchestration — extracted to
# ``orchestration.py``. Re-exported so existing imports of
# ``from lib.runner import run_task / batch_run / run_primary_attempt / ...``
# keep working.
# --------------------------------------------------------------------------


from .orchestration import (  # noqa: E402
    DEFAULT_CONTAINER_RUNTIME_RETRY_ATTEMPTS,
    attempt_meta_base,
    batch_run,
    build_bootstrap_infra_attempt,
    build_bootstrap_infra_summary,
    initialize_session_container,
    resolve_attempt_outcome,
    run_primary_attempt,
    run_task,
    stage_dir_name,
    structured_rate_limit_score,
    structured_runtime_error_score,
    task_summary_base,
    write_task_run_state,
)


# --------------------------------------------------------------------------
# Stable public-API surface — used by ``from lib.runner import *`` and the
# pinning test ``tests/unit/test_runner_public_api.py``.
#
# Underscore-prefixed symbols and backend-specific helpers are intentionally
# omitted from ``__all__``: deep imports (``from lib.runner.evaluation import
# _api_stop_reason``) remain available, but the package surface stays small
# so future refactors don't accidentally lock in private names as API.
#
# Recent additions: ``apply_score_based_promotion`` (Phase 2 — Path A/B
# shared promotion), ``ArtifactProfile*`` + ``current_artifact_profile``
# (Phase 3 — public/debug artifact gating), ``model_quirks`` /
# ``resolve_model_entry`` / ``write_score_json`` (Phase 4 — model config
# quirks + Path B threshold persistence), backend completion strategies
# (Phase 4).
# --------------------------------------------------------------------------

# Re-export the canonical status helpers / new Phase 2 promotion gate so the
# package surface owns them rather than every caller deep-importing ``lib.status``.
from ..status import (  # noqa: E402
    apply_score_based_promotion,
    classify_attempt_outcome,
    status_rank,
)


# Re-export the Phase 3 artifact-profile constants alongside the existing
# artifact entry points so external scripts can opt into the public/debug
# split without deep-importing the writer module.
from .artifacts import (  # noqa: E402
    ARTIFACT_PROFILE_DEBUG,
    ARTIFACT_PROFILE_PUBLIC,
    DEFAULT_ARTIFACT_PROFILE,
    current_artifact_profile,
    write_score_json,
)


# Re-export the Phase 4 model-config quirks helpers.
from .task_config import (  # noqa: E402
    model_quirks,
    resolve_model_entry,
)


__all__ = [
    # Orchestration entry points
    "run_task",
    "batch_run",
    "run_primary_attempt",
    "initialize_session_container",
    "resolve_attempt_outcome",
    "build_bootstrap_infra_attempt",
    "build_bootstrap_infra_summary",
    "task_summary_base",
    "write_task_run_state",
    "stage_dir_name",
    "attempt_meta_base",
    "structured_rate_limit_score",
    "structured_runtime_error_score",
    "DEFAULT_CONTAINER_RUNTIME_RETRY_ATTEMPTS",

    # Task spec + model registry
    "build_runtime_task_spec",
    "override_task_runtime",
    "override_codex_role_runtime",
    "task_run_root",
    "reset_task_run_root",
    "resolve_models_provider_entry",
    "providers_from_models_payload",
    "load_models_payload",
    "resolve_model_ref",
    "resolve_model_entry",
    "model_quirks",
    "model_id_for_backend",
    "model_slug",
    "normalize_agent_sys",
    "compose_model_ref",
    "strip_model_provider",
    "default_agent_id_for_agent_sys",
    "default_image_for_agent_sys",
    "effective_agent_id_for_task",
    "transcript_targets_for_task",
    "collect_task_proxy_specs",
    "managed_task_proxy_tunnels",
    "setting_root",
    "slugify",
    "RUNS",
    "NANOBOT_TRANSCRIPT_TARGETS",

    # Status convergence (Phase 2 shared helpers)
    "apply_score_based_promotion",
    "classify_attempt_outcome",
    "status_rank",

    # Artifact profile (Phase 3)
    "ARTIFACT_PROFILE_PUBLIC",
    "ARTIFACT_PROFILE_DEBUG",
    "DEFAULT_ARTIFACT_PROFILE",
    "current_artifact_profile",
    "write_score_json",

    # Artifact collection
    "collect_attempt_artifacts",
    "collect_runtime_probe",
    "collect_edict_agent_session_artifacts",
    "supervision_component_summary",
    "write_supervision_component_artifacts",
    "append_jsonl",
    "append_text",
    "AGENT_SESSION_ARTIFACTS_DIR",
    "PRIVATE_SERVICE_ROOT",
    "private_service_dir",
    "normalize_proxy_value",

    # Usage ledger
    "build_attempt_usage_payload",
    "compute_executor_token_usage",
    "append_executor_usage_ledger",
    "append_role_usage_ledger",
    "append_attempt_request_log",
    "attempt_task_id",

    # Evaluation + continuation
    "evaluate_attempt",
    "continuation_decision",
    "executor_completion_state",
    "apply_executor_completion_gate",
    "assistant_signaled_completion",
    "edict_primary_still_routing",
    "last_message_payload",
    "codex_role_context",
    "apply_privacy_leakage_cap",
    "apply_privacy_cap_to_supervision_decision",
    "scan_visible_artifacts_for_privacy_leaks",

    # Transcript pipeline
    "annotate_transcript_with_agent",
    "build_tool_usage_summary",
    "load_tool_usage_file",
    "merge_agent_transcripts",
    "normalize_nanobot_session_transcript",
    "normalize_transcript_text",
    "parse_json_lines",
    "reconstruct_tool_spans",
    "summarize_transcript_tools",
    "transcript_event_timestamp",
    "transcript_is_event_stream",

    # EDICT runtime assets
    "build_edict_agents_md",
    "build_edict_tools_md",
    "edict_agent_group",
    "edict_agent_ids",
    "edict_agent_specs",
    "edict_repo_dir_for_task",
    "render_edict_soul",
    "read_text_if_exists",
    "EDICT_AGENTS_ROOT",
    "EDICT_ASSETS_ROOT",
    "EDICT_BACKEND_MODELS_ROOT",
    "EDICT_DATA_ROOT",
    "EDICT_DEMO_CONFIG",
    "EDICT_DEMO_DATA_ROOT",
    "EDICT_DEMO_SEED_FILES",
    "EDICT_GLOBAL_MD",
    "EDICT_GROUPS_ROOT",
    "EDICT_RUNTIME_ROOT",
    "EDICT_SCRIPTS_ROOT",

    # Container / runtime services
    "prepare_runtime",
    "ensure_openclaw_runtime_ready",
    "start_container",
    "start_desktop",
    "start_gateway",
    "start_services",
    "start_openclaw_browser_profile",
    "browser_service_ready",
    "browser_profile_running",
    "ensure_gateway_ready",
    "gateway_ready",
    "task_likely_uses_browser",
    "inject_nanobot_config",
    "inject_openclaw_config",
    "inject_edict_config",
    "run_pre_exec_scripts",
    "build_proxy_env_script",
    "runtime_base_skills",
    "runtime_base_skill_fallbacks",
    "PreExecError",
    "BROWSER_GATEWAY_LOG",
    "CONTAINER_HOST_ALIASES",

    # Agent dispatch
    "build_initial_prompt",
    "build_continuation_prompt",
    "prompt_prefix",
    "run_agent",
    "run_monitored_agent",
    "run_nanobot_agent",
    "run_openclaw_agent",
    "AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS",

    # Docker primitives
    "container_exists",
    "copy_tree_contents_to_container",
    "docker_cp_from_container",
    "docker_cp_to_container",
    "docker_exec",
    "docker_rm",
    "docker_write_text_file",
    "run",

    # Media / recording
    "TimelineRecorder",
    "active_inline_images_dir",
    "active_timeline_recorder",
    "attach_inline_images_dir",
    "recording_session",
    "start_recording",
    "stop_recording",
    "timeline_span",

    # openclaw config helpers
    "OPENCLAW_CONFIG_VALIDATE_STRICT",
    "OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS",
    "build_openclaw_config_script",
    "configured_openclaw_image_model",
    "normalize_openclaw_config_fragment",
    "openclaw_agent_models_registry",
    "openclaw_model_supports_image",
    "select_openclaw_image_model",
    "validate_openclaw_config",

    # Sessions / transcript paths
    "resolve_openclaw_agent_all_session_paths",
    "resolve_openclaw_agent_transcript_paths",
    "resolve_openclaw_transcript_path",

    # Error classifiers
    "RETRYABLE_CONTAINER_BOOT_PATTERNS",
    "RETRYABLE_CONTAINER_RUNTIME_PATTERNS",
    "detect_infra_error",
    "detect_openclaw_rate_limit",
    "detect_retryable_container_boot_error",
    "detect_retryable_container_runtime_error",
    "detect_supervisor_infra_error",
    "should_retry_transient_followup",

    # Supervision context types + runner entry
    "AttemptSupervisorContext",
    "CodexRoleRuntimeContext",
    "SupervisorContext",
    "TaskSupervisorContext",
    "run_supervisor",

    # Templates
    "EDICT_ROUTING_NOTE",
    "EXECUTOR_RUNTIME_PREFIX_LINES",

    # Proxy shared infra
    "acquire_shared_proxy_tunnel",
    "release_shared_proxy_tunnel",
    "build_proxy_tunnel_command",
    "discover_active_proxy_adapter_log_paths",
    "normalize_provider_proxy_spec",
    "provider_proxy_spec",
    "read_proxy_usage_events",
    "read_proxy_usage_events_across_all_logs",
    "start_proxy_adapter",
    "start_proxy_tunnel",
    "stop_proxy_tunnel",
    "DEFAULT_PROXY_KIND",
    "DEFAULT_PROXY_WAIT_SECONDS",
    "PROXY_ADAPTER_LOG_PATH",
    "PROXY_REGISTRY_ROOT",

    # Task loading
    "TaskSpec",
    "canonical_agent_sys",
    "discover_task_files",
    "load_task",
    "validate_agent_sys",

    # Module-level constants
    "AGENT_SESSION_ID",
    "CONTINUATION_DONE_MARKER",
    "ROOT",
    "RESULTS_ROOT",
    "DEFAULT_IMAGE",
    "DEFAULT_IMAGE_BY_AGENT_SYS",
    "DEFAULT_MODELS_CONFIG",
    "DEFAULT_SHARED_ENV_FILE",
    "BROWSER_HEADED",
    "EXECUTOR_CONTEXT_WINDOW_TOKENS",
    "RECORDING_DISPLAY",
    "RECORDING_FINAL",
    "RECORDING_INPUT_FPS",
    "RECORDING_LOG",
    "RECORDING_OUTPUT_FPS",
    "RECORDING_PID_FILE",
    "RECORDING_RAW",
    "RECORDING_SPEEDUP",
    "RECORDING_STOP_WAIT_STEPS",
    "RECORDING_SUPPORTED_AGENT_SYSTEMS",
    "RECORDING_VIDEO_SIZE",
]
