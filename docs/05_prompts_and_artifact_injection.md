# Prompts and Artifact Injection

This document describes how the current repository assembles Codex role prompts and role workspaces.

## 1. Template Sources

Prompt templates live under `lib/templates/`:

- `lib/templates/session_wrapper.py`: shared workspace/environment wrapper for Codex roles.
- `lib/templates/answer_supervisor.py`: answer-supervisor role prompt.
- `lib/templates/user_simulator.py`: public-user-simulator role prompt and `DEFAULT_USER_SIMULATOR_POLICY`.
- `lib/templates/supervisor_default.py`: default answer-supervisor task instructions.
- `lib/templates/executor_runtime.py`: executor runtime-context prefix and EDICT routing-note text.

`render_template()` loads the `TEMPLATE` variable from `lib/templates/<name>.py` for the first three files. The last two are imported directly by runner/supervisor code as text modules.

Text tables for English/Chinese public feedback, guidance hints, and fallbacks live in `lib/i18n.py`. Enumerations and schema-version constants live in `lib/constants.py`. Runtime defaults such as model names, reasoning effort, follow-up limits, and paths live in `lib/defaults.py`.

## 2. Prompt Shape

Each Codex role prompt has two layers:

1. A role-specific template.
2. The shared session wrapper.

The session wrapper declares:

- The current role.
- That the workspace is isolated and should be treated as read-only.
- Key files to inspect.
- Network/file-modification restrictions.

In tool-using mode, the prompt tells Codex to inspect workspace files before returning JSON:

```text
Read the workspace files first, then respond with exactly one JSON object
and no prose outside the JSON object.
```

In toolless retry mode, used after sandbox/tool failures, the prompt forbids tool use:

```text
CRITICAL: respond with exactly one JSON object and no prose outside the JSON object.
Do not use bash, exec, file inspection, or network tools.
```

## 3. Role Workspaces

`prepare_role_workspace()` creates an independent directory for each Codex role.

### Shared by Supervisor and User Simulator

- `README.md`: generated "Start Here" file with key files, available images, and `view_image` examples.
- `workspace_manifest.json`: structured index; `available_images` lists all workspace images that `view_image` can inspect.
- `public_task.md`.
- `turn_state.json`.
- `role_history.jsonl`.
- `visible/executor_prompt.md`.
- `visible/transcript.jsonl`: normalized transcript with large base64 images stripped.
- `visible/tool_usage.json`.
- `visible/runtime_probe.json`.
- `visible/runtime_probe_desktop.png`.
- `visible/result/`.
- `visible/visible_summary.json`.
- `visible/agent_sessions/`: present for `openclaw_edict` per-subagent transcripts.

### Supervisor Only

- `references/`: hidden evaluation rule and reference materials.
- `references/hidden_summary.json`: includes the first 12 KB of the primary `eval_rule.md`.
- `privacy/env.env`: present only when the task declares privacy env vars and `configs/privacy.local.env` provides real values.

### User Simulator Only

- `supervisor_feedback.json`: the four-field public handoff.

## 4. Images and Base64 Stripping

By default, images are not pre-attached to Codex conversations. This is controlled by `CLAWBENCH_CODEX_ATTACH_IMAGES`, which defaults to `"0"`.

The generated workspace README and prompts explicitly state that no images are pre-attached and show `view_image` examples. Codex decides whether an image is relevant and which images to inspect. The `available_images` manifest is an optional image pool, not a mandatory read list.

Large inline transcript images are stripped by `lib/runner/transcripts.py:normalize_transcript_text`. A block such as:

```json
{"type": "image", "data": "<multi-KB base64>", "mimeType": "image/png"}
```

is replaced with:

```json
{"type": "text", "text": "[image: inline_images/ab12cd34...png]"}
```

The binary content is written to `<attempt>/inline_images/<sha256>.<ext>`. The WebUI can render those images through a separate allowlist, but the supervisor workspace does not receive `inline_images/`.

Normalization paths:

- Legacy Nanobot role-based format: `normalize_nanobot_session_transcript` plus `_normalize_content_blocks`.
- OpenClaw, OpenClaw EDICT, and event-stream formats: `_strip_image_blocks_from_event_records`.
- OpenClaw EDICT per-subagent `agent_sessions/<agent>/transcript.jsonl` files are stripped in place, with `transcript_raw.jsonl` kept as evidence when needed.

## 4.1 Adapter Image Handling

The stripping above happens on the host side. Codex role requests may also pass through the `responses_via_chat` adapter.

The authoritative adapter implementation is the subprocess script embedded in `lib/proxy/adapter.py`. Unit tests use the synchronized mirror in `lib/proxy/transform.py`.

When a `function_call_output.output` list contains an `input_image` block, the adapter does not stuff that list into a chat-completions `tool` message. Instead:

- The tool message keeps a placeholder such as `[image]` or `[tool result attached in the next turn]` so `tool_call_id` pairing remains valid.
- The actual image is emitted as a separate `role: "user"` message with an `image_url` block.
- Image follow-ups from parallel tool calls are queued and flushed after the whole tool batch is complete, avoiding provider errors about unanswered assistant tool calls.

Coverage lives in `tests/test_responses_adapter_image.py` and `tests/test_responses_adapter_parallel_tool_pairing.py`.

## 4.2 Historical MCP Artifacts

`mcp_artifacts/` is a compatibility channel for old attempts that used Playwright MCP auto screenshots, DOM snapshots, and console logs.

Current backends use the `agent-browser` CLI skill. New runs usually have an empty `mcp_artifacts/` directory. The directory is not inside `result/`, so `_copy_visible_workspace_files` does not copy it into the supervisor workspace. The WebUI receives it through a dedicated `mcpArtifacts` API field for historical trace rendering.

## 4.3 Structured Summaries

The runner also writes structured summaries:

- `visible/visible_summary.json`.
- `references/hidden_summary.json` for the supervisor.
- `supervisor_feedback.json` for the user simulator.

## 5. Artifact Profile

`CLAWBENCH_ARTIFACT_PROFILE` controls how much supervision debug data is written.

| File or field | `public` default | `debug` |
| --- | :---: | :---: |
| `supervision/cycle_XX/{name}_decision.json` | yes | yes |
| `supervision/cycle_XX/{name}_prompt.txt` | no | yes |
| `supervision/cycle_XX/{name}_response.txt` | no | yes |
| `supervision/cycle_XX/{name}_stdout.log` | no | yes |
| `supervision/cycle_XX/{name}_stderr.log` | no | yes |
| `supervision/cycle_XX/{name}_input_workspace.json` | no | yes |
| `supervision/cycle_XX/{name}_input_readme.md` | no | yes |
| `supervision_trace.jsonl` `components.*` | transport, elapsed time, image inputs, decision | public fields plus prompt, input workspace, input README, workspace root |

Public fields such as `score.json`, `meta.json`, `transcript.jsonl`, `tool_usage.json`, `timeline.json`, `result/`, `inline_images/`, and recordings are always generated.

The default `public` profile is intended for open-source release, reproducibility, and archiving. Use `debug` only for local troubleshooting.

## 6. Sources, Skills, and Services

### Sources

The runner copies the entire `injection/.../sources/` directory to:

```text
/tmp_workspace/clawbench/sources/
```

The `sources:` list in task YAML is metadata, not a copy whitelist.

`SNAPSHOT_MODE` exception: when a task declares `SNAPSHOT_MODE` in `.privacy`, `lib/runner/container_lifecycle.py` reads the injected env value. Only `SNAPSHOT_MODE=1` copies `*_snapshot.json` files. Any other non-empty value skips snapshot files and forces real API usage. Tasks without `SNAPSHOT_MODE` keep the normal full-source copy behavior.

### Skills

- Task-declared skills are copied from `injection/.../skills/`.
- Runtime built-in skills are always available.
- `desktop-control` is the current default GUI skill.
- `linux-gui-control` remains only as historical compatibility source.

### Services

Task-declared service directories are copied into the harness-private path:

```text
/opt/clawbench/.harness/services/<task_id>/<service_path>/
```

`lib/runner/container_lifecycle.py:prepare_runtime` immediately makes `/opt/clawbench/.harness` and each task subdirectory `0700`. The executor cannot normally list or enter these paths. Service processes still run as root and can read their own files.

Task authors must follow the isolation contract in [`TASK_SCHEMA.md`](TASK_SCHEMA.md): public task text, sources, and any executor-visible files must not mention `.harness/services/...` paths. Services should write executor-visible outputs to `/tmp_workspace/results/` or `/tmp_workspace/clawbench/service_state/`.

One-shot services are valid. `start_services` uses `nohup bash -lc {start} &` and checks only the `nohup` exit code, so setup scripts can install dependencies and exit. Service scripts should locate their own directory with a pattern such as:

```bash
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

Do not hard-code `/opt/clawbench/.harness/services/<task_id>/...`; task IDs and paths may change.

## 7. Privacy Env Injection

Each task can include:

```text
injection/{category}/{task_id}/.privacy
```

The file is one env-var name per line. Empty lines and `# ...` comments are ignored. This file is safe to commit because it contains names only, not values.

Real values live in `configs/privacy.local.env`, which is ignored by git. At runtime:

- The runner passes each declared key into the executor container with `docker run -e KEY=VALUE`.
- The answer supervisor receives the same values in `privacy/env.env` for scoring and leakage checks.
- The public user simulator never receives the values.
- `load_task` fails early when a declared key is missing, empty, or still a placeholder.

Task YAML no longer declares a `privacy:` list. The `.privacy` file is the single declaration source.

## 8. Isolation Boundary

| Content | Executor | Supervisor | User Simulator |
| --- | :---: | :---: | :---: |
| Public `task` | yes | yes | yes |
| Visible trajectory and results | yes | yes | yes |
| `references/` | no | yes | no |
| `.privacy` env values | container env | `privacy/env.env` | no |
| Full supervisor reasoning | no | yes | no |
| Four-field handoff | no | n/a | yes |
