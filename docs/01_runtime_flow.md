# UniClawBench Runtime Flow

This document describes the current implementation in this repository. It intentionally omits old schema variants and historical task examples.

## 1. Main Path

A single evaluation usually enters through `scripts/run_eval.py` and then calls `lib/runner/orchestration.py:run_task()`. The `lib.runner` package re-exports `run_task` and `batch_run` from `__init__.py`, so historical imports such as `from lib.runner import run_task` still work.

High-level flow:

1. Load the task YAML.
2. Validate task config and injected resources.
3. Create the run directory.
4. Start proxy tunnels and adapters when needed.
5. Start the executor container.
6. Run the executor inside the container.
7. Collect visible artifacts.
8. Invoke the answer supervisor in a Codex container.
9. If the verdict is `continue` and the attempt is recoverable, invoke the public user simulator.
10. Feed the continuation back to the executor.
11. Stop on `pass`, `fail`, `infra_error`, `global_timeout`, `budget_exhausted`, `executor_incomplete`, or `stopped`.

### Executor-to-Supervisor Timing

The runner does not wait for `timeout_seconds` to expire after the executor process has already exited. Once the process exits, either because it returned `stopReason=stop` or because the watchdog terminated it, `run_monitored_agent` returns after at most one poll interval. `run_primary_attempt` then waits a fixed two seconds for transcript and result-file settling before `collect_attempt_artifacts`, `collect_runtime_probe`, and `evaluate_attempt`.

This should be understood as a fixed two-second settle period plus artifact/probe sync overhead, not as a hard four-second SLA.

## 2. Role Visibility

### Executor

Visible:

- The public `task` field from the task YAML.
- Continuations from previous cycles.
- Current websites, tool outputs, and container-visible files.

Not visible:

- `references/`.
- The supervisor's private reasoning.

### Answer Supervisor

Visible:

- `public_task.md`.
- `visible/` files: transcript, tool usage, runtime probe, saved result files, and summaries.
- `references/`: hidden evaluation rule and reference materials.
- `privacy/env.env` when the task declares privacy env vars and `configs/privacy.local.env` provides real values.

### Public User Simulator

Visible:

- `public_task.md`.
- `visible/` files.
- `supervisor_feedback.json`.

Not visible:

- `references/`.
- Supervisor `rationale`, `missing_artifacts`, or other hidden analysis fields.

## 3. Answer-Supervisor Schema

The current answer supervisor returns these fields:

```json
{
  "verdict": "continue",
  "attempt_state": "incomplete",
  "recoverable": true,
  "score": 0.35,
  "confidence": "medium",
  "rationale": "Current evidence is still incomplete.",
  "missing_artifacts": ["clear video evidence", "matching Amazon page"],
  "guidance_tags": ["save_supporting_screenshot"]
}
```

`confidence` and `missing_artifacts` are retained in run artifacts and the WebUI. Historical rich-schema fields such as `reference_understanding`, `failure_reasons`, `focus_points`, and `leakage_risk` are no longer part of the current implementation.

## 4. Public User Handoff

The user simulator receives only this four-field handoff:

```json
{
  "verdict": "continue",
  "attempt_state": "incomplete",
  "recoverable": true,
  "score": 0.35
}
```

That means it can only use the original public task, the visible trajectory, and coarse progress state to generate the next public follow-up.

By default, the continuation sent back to the executor uses only `candidate_feedback`. `public_feedback_points` and `guidance_tags` remain in run artifacts, but they only contribute to continuation text when `SAFE_USER_FEEDBACK_MODE` in `lib/defaults.py` is changed to `composed`.

## 5. Key Artifacts

### Task Run Root

- `summary.json`.
- `session_meta.json`.

### Attempt Directory

- `p1-xxxxxx/score.json`.
- `p1-xxxxxx/meta.json`.
- `p1-xxxxxx/transcript.jsonl`: normalized transcript with large base64 images stripped.
- `p1-xxxxxx/transcript_raw.jsonl`: raw transcript, written only when stripping was needed.
- `p1-xxxxxx/tool_usage.json`.
- `p1-xxxxxx/runtime_probe.json`.
- `p1-xxxxxx/timeline.json`: source data for the WebUI execution-timeline Gantt view.
- `p1-xxxxxx/result/`: executor-saved artifacts mirrored into supervisor/user-simulator workspaces.
- `p1-xxxxxx/inline_images/`: base64 images extracted from transcripts for WebUI rendering; not copied into the supervisor workspace.
- `p1-xxxxxx/mcp_artifacts/`: historical MCP side artifacts; not copied into the supervisor workspace.
- `p1-xxxxxx/agent_sessions/<agent>/`: per-subagent transcripts and usage for `openclaw_edict`.
- `p1-xxxxxx/supervision/cycle_XX/recording.mp4`: accelerated desktop recording when task recording is enabled.

### Supervision Directory

- `p1-xxxxxx/supervision/cycle_XX/decision.json`.
- `p1-xxxxxx/supervision/cycle_XX/answer_supervisor_decision.json`.
- `p1-xxxxxx/supervision/cycle_XX/public_user_simulator_decision.json`.
- `p1-xxxxxx/supervision/cycle_XX/feedback_rewriter_decision.json`.

## 6. Execution Timeline

`lib/runner/media.py:TimelineRecorder` writes five phase families into `timeline.json`:

- `container_lifecycle`: `start_container`, `prepare_runtime`, config injection, desktop startup, service startup, and similar phases.
- `artifact`: artifact and runtime-probe collection.
- `executor`: `cycle_NN_executor` phases with reconstructed tool-call spans.
- `supervisor`: `cycle_NN_answer_supervisor`.
- `user_simulator`: `cycle_NN_user_simulator`.

The recorder flushes incrementally at cycle boundaries, so partial timeline data survives many abnormal exits. The WebUI positions phases by wall-clock offset and duration; for `openclaw_edict`, tool-call spans are also grouped by `agent_id`.

## 7. Codex Container and API Adapter

The answer supervisor and user simulator run through Codex CLI v0.120.0 in a separate Docker image (`clawbench-codex`).

Typical adapter path:

```text
Codex CLI inside the container, using Responses API
  -> host.docker.internal:9001, responses_via_chat adapter
    -> 127.0.0.1:9000, SSH tunnel
      -> remote provider API, usually /chat/completions
```

Codex v0.120.0 requires `wire_api = "responses"`. If the upstream provider only supports `/chat/completions`, configure the `responses_via_chat` adapter. If the upstream provider supports `/responses` natively, the adapter is not required.

The adapter translates tool declarations, tool calls, tool outputs, image-bearing tool outputs, and streaming events between the two API shapes.

## 8. Task Resource Injection

Current runner behavior:

- `references/`: copied only to the answer supervisor.
- `sources/`: copied wholesale into the executor container, with the `SNAPSHOT_MODE` exception below.
- `skills/`: only task-declared skills are copied.
- `services/`: only task-declared services are copied and launched. Service files are copied under `/opt/clawbench/.harness/services/<task_id>/...` and made harness-private with `chmod 0700`.

Important notes:

- The `sources:` list is declarative metadata, not a whitelist copy switch.
- It helps EDICT infer a default repo directory when a task has exactly one source entry.
- If a task declares `SNAPSHOT_MODE` in `.privacy` and the injected value is not `1`, `lib/runner/container_lifecycle.py` skips `*_snapshot.json` files so the task must use real APIs.
- `SNAPSHOT_MODE=1`, or no `SNAPSHOT_MODE` declaration, preserves the normal behavior of copying the full `sources/` tree.

## 9. Backend Names

`agent_sys` accepts only these canonical values:

- `openclaw`
- `openclaw_edict`
- `nanobot`

Legacy aliases such as `edict` or `openclaw+edict` are rejected by the task loader.

## 10. Desktop Recording

Default tasks use `recording: none` and `headed: auto`, which usually means headless execution with no recording. When a task YAML sets `recording: low` or `recording: high`, the runner records the container desktop (`:99`) during executor turns with `ffmpeg x11grab`.

Recording details:

- Managed by `lib/runner/media.py:recording_session()`.
- Supported for `openclaw`, `openclaw_edict`, and `nanobot`.
- `recording: high` causes `headed: auto` to resolve to headed mode.
- Stop sequence is `SIGINT`, wait up to ten seconds, then `SIGKILL` if needed.
- Output is accelerated with `setpts=PTS/16` and written to `supervision/cycle_NN/recording.mp4`.
- Recording failures are warnings only and never block scoring.
