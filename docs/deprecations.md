# Deprecations and Compatibility Notes

This file tracks compatibility shims, deprecated public symbols, and historical artifact paths that remain in the repository for old runs or downstream imports.

When adding a deprecated item, add a `# DEPRECATED:` comment at the source definition and link back to this file.

## Removed

- `lib/supervision/orchestrator.py:_contains_any`
  - Removed after static scan found no external callers.

## Deprecated but Still Present

- `lib/runner/media.py:attach_timeline_recorder`
  - Current code assigns `recording._ACTIVE_RECORDER` directly.
  - The function remains as a historical deep-import compatibility entry.
  - It is no longer re-exported from `lib/runner/__init__.py`.
  - Planned removal: next minor release.

- `lib/runner/container_lifecycle.py:wait_for_browser_service_ready`
  - Current code uses `ensure_gateway_ready` and `start_services`.
  - It is no longer re-exported from `lib/runner/__init__.py`.
  - Planned removal: next minor release.

- `lib/supervision/content.py:copy_tree_into`
  - Single call site remains in `lib/supervision/common.py`.
  - Planned migration: inline into `common.py` or rename as an internal helper.

## Kept Intentionally

- `lib/runner/usage_ledger.py:append_attempt_request_log`
  - Used by `tests/integration/test_per_task_token_attribution.py`.
  - Not called by the main runtime path, but retained for debugging and compatibility.

- `lib/runner/evaluation.py:_SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS`
  - Canonical constant lives in `lib/runner/completion_strategies.py:SUBSTANTIVE_TAIZI_FINAL_MIN_CHARS`.
  - `evaluation.py` keeps an equal alias for historical deep imports.

## Planned Larger Refactors

These are useful follow-up tasks but are intentionally not part of the release cleanup because they carry import-path risk:

- Split `lib/runner/container_lifecycle.py` into `container/pre_exec.py`, `container/boot.py`, and `container/services.py` plus a facade.
- Split remaining large sections of `lib/runner/evaluation.py`; backend completion strategy has already been extracted.
- Split `lib/proxy/adapter.py` into service lifecycle, request transformation, and streaming pieces.
- Split `lib/runner/orchestration.py` into summary, attempt outcome, container retry, and usage-rollup internals.

## Governance Changes from Phase 8

- Supervisor verdict normalization no longer promotes `continue` or `fail` to `pass` based on score alone.
  - Score-based promotion is centralized in `lib.status.apply_score_based_promotion` and applies to runtime `final_status` handling, not supervisor semantic verdicts.
  - Tests live in `tests/unit/test_supervision.py`.

- Nanobot zero-exit completion fallback now requires non-empty final text.
  - Empty or whitespace-only final text becomes `missing-completion-signal` and ultimately `executor_incomplete`.
  - Tests live in `tests/unit/test_completion_strategy.py`.

- `canonical_agent_sys(value, *, strict=True)` is the single backend-name normalization entry point.
  - `validate_agent_sys` is a strict wrapper.
  - `lib.runner.task_config.normalize_agent_sys` is a non-strict wrapper.
  - `scripts/run_eval.py:_prune_prior` uses strict validation.

- Top-level JSON artifacts include schema-version fields.
  - Affected artifacts: `summary.json`, `score.json`, `meta.json`, `session_meta.json`, and `batch_summary.json`.
  - Version constants live in `lib/status.py`.
  - Readers treat missing fields as v1-compatible.

- `pyproject.toml` includes a minimal Ruff configuration.
  - Enabled checks: `F401`, `F841`, `F541`, and `E9`.
  - Re-export facade files use targeted `per-file-ignores`.

## Historical Artifact Paths

- `<attempt>/mcp_artifacts/`
  - Historical output directory for Playwright MCP automatic screenshots, DOM snapshots, and console logs.
  - Current backends use the `agent-browser` CLI skill. New runs usually leave this directory empty.
  - The directory is not copied into supervisor workspaces. WebUI and static export keep compatibility readers for old attempts.
  - See [`README.md`](../README.md), [`docs/04_supervisor.md`](04_supervisor.md), and [`docs/05_prompts_and_artifact_injection.md`](05_prompts_and_artifact_injection.md).

- Historical supervisor verdicts `infra_error` and `rate_limit`
  - Current supervisor output is limited to `pass`, `continue`, and `fail`.
  - `lib/supervision/orchestrator.py` still normalizes old artifacts that contain runtime-style verdicts.

- `codex.user_simulator.instructions`
  - The field remains in the dataclass for shared-structure compatibility.
  - Current code reads `codex.user_simulator.policy`; `instructions` is ignored.
  - [`docs/TASK_SCHEMA.md`](TASK_SCHEMA.md) marks the field as ignored.
