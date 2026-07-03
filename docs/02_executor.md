# Executor Role

The executor is the agent that actually performs the public task.

## 1. Input

The first turn comes from the task YAML `task` field. Later turns receive a runner-generated continuation when the answer supervisor asks the benchmark to continue.

The executor cannot see:

- Hidden references.
- The supervisor's private analysis.

## 2. Container Environment

The executor runs in the primary task container. Common images:

- `clawbench-openclaw:latest`
- `clawbench-openclaw-edict:latest`
- `clawbench-nanobot:latest`

Important public paths inside the container:

- `/tmp_workspace/results/`
- `/tmp_workspace/clawbench/sources/`
- `/tmp_workspace/clawbench/logs/`

## 3. Runtime Constraints

The runner appends a shared runtime prefix to the executor prompt. The most important constraints are:

- Save useful evidence and conclusions under `/tmp_workspace/results/`.
- Finish with one plain-text assistant message and no additional tool call.
- Use the browser for website discovery tasks; do not use `web_fetch` as a search engine.
- Preserve query words and ordering clues from the task unless a small wording adjustment keeps the same intent.
- When the task asks for evidence from primary content, prefer direct page/video/application state over nearby secondary text.

## 4. Time Budgets

All timeouts apply to executor time. The answer supervisor and public user simulator are evaluation infrastructure and do not count against executor budgets.

| Field | Default | Meaning |
| --- | ---: | --- |
| `timeout_seconds` | 1200 | Upper bound for one executor agent process. The container watchdog monitors this and passes it to OpenClaw when applicable. |
| `max_total_seconds` | 1800 | Cumulative executor wall-clock time across all turns in the attempt. Supervisor and user-simulator calls are excluded. |

`AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS` defaults to 180 seconds and protects against agents that start without visible progress.

Attempt `meta.json` records:

- `runtimeMs`: executor time only; same budget basis as `max_total_seconds`.
- `wallClockMs`: full attempt wall clock including supervision, artifact collection, and simulator calls.

## 5. Built-in Skills

Runtime skills that are always available:

- `apt-package-manager`
- `agent-browser-control`
- `web-search`
- `duckduckgo-search`
- `desktop-control`

Task-declared `skills:` entries are copied into `/root/skills/` in addition to the runtime skills.

## 6. Output Artifacts

Important intermediate and final artifacts:

- `transcript.jsonl`
- `tool_usage.json`
- `runtime_probe.json`
- Files under `result/`, including screenshots, text files, spreadsheets, links, and other saved evidence.

The supervisor does not require fixed filenames. It checks whether the public task was completed, whether evidence matches conclusions, and whether results were derived from visible/public content.

`apply_executor_completion_gate` determines completion in this order:

1. API `stopReason`: `stop` or `end_turn` means complete; `toolUse` or `length` means incomplete.
2. Last assistant message containing a tool call means incomplete.
3. Fallback text markers such as `I have finished the request` and compatible variants.

## 7. Supervisor Trigger

As soon as the executor process exits, the runner proceeds to scoring:

1. `run_monitored_agent` polls the executor process every two seconds.
2. After process exit, `run_primary_attempt` waits two seconds for transcript and result-file settling.
3. The runner collects artifacts and invokes the answer supervisor.

There is no idle wait until `timeout_seconds` after an executor has already completed. This avoids wasting runtime on tasks that have already produced a final answer.
