# Answer Supervisor Role

The answer supervisor is the hidden evaluator.

## 1. Input Workspace

Each cycle receives an independent workspace:

```text
workspace/
  README.md
  workspace_manifest.json
  public_task.md
  turn_state.json
  role_history.jsonl
  visible/
    executor_prompt.md
    transcript.jsonl
    tool_usage.json
    runtime_probe.json
    runtime_probe_desktop.png
    visible_summary.json
    result/
    agent_sessions/
  references/
    eval_rule.md
    references/*.png
    hidden_summary.json
  privacy/
    env.env
```

`privacy/env.env` appears only when the task declares `.privacy` env vars and local privacy config provides real values.

The supervisor is the only role that sees both the visible evidence and hidden references.

## 1.1 Clean Transcript

Before `transcript.jsonl` is copied into the workspace, it is normalized by `normalize_transcript_text`:

- Legacy role-based format: `normalize_nanobot_session_transcript` plus `_normalize_content_blocks`.
- Event-stream format: `_strip_image_blocks_from_event_records`.

Both paths replace large image blocks such as `{type: "image", data: "<b64>"}` with text references like `[image: inline_images/<hash>.<ext>]`. The raw transcript is saved as `transcript_raw.jsonl` when stripping was needed, but raw transcript content is not copied into the supervisor workspace.

All current backends drive browsers through the `agent-browser` CLI skill. Historical `playwright-mcp` output under `<attempt>/mcp_artifacts/` remains readable for old attempts, but that directory is not copied into the supervisor workspace.

## 1.2 Images Are Not Pre-Attached by Default

By default, `CLAWBENCH_CODEX_ATTACH_IMAGES="0"` and the Codex command does not pass any `--image` arguments.

The generated README and supervisor prompt state:

```text
No images are pre-attached to this conversation. Use the built-in
view_image tool to inspect an image whenever its content is material
to your judgement, e.g.:

    view_image(path="visible/result/screenshots/amazon_product.png")
    view_image(path="references/references/reference_frame.png")

Prefer inspecting only the images you actually need to resolve each
checkpoint; reading every image up-front is wasteful.
```

Reasons:

1. Context control. Attaching many high-resolution screenshots can exceed the model context window.
2. Evaluation discipline. The supervisor should decide which images matter for each checkpoint.

Set `CLAWBENCH_CODEX_ATTACH_IMAGES=1` only when reproducing the old "pre-attach every image" behavior.

## 2. Output Schema

Current schema:

```json
{
  "verdict": "continue",
  "attempt_state": "incomplete",
  "recoverable": true,
  "score": 0.35,
  "confidence": "medium",
  "rationale": "The saved evidence is still incomplete.",
  "missing_artifacts": [
    "clear screenshot from the video",
    "matching Amazon product page"
  ],
  "guidance_tags": [
    "save_supporting_screenshot",
    "verify_evidence_matches_conclusion"
  ]
}
```

Field meanings:

- `verdict`: `pass`, `continue`, or `fail`.
- `attempt_state`: `in_progress`, `incomplete`, `complete_but_failed`, `complete_and_passed`, or `terminal_failure`.
- `recoverable`: whether another executor turn is worth trying.
- `score`: continuous score from 0 to 1.
- `confidence`: `low`, `medium`, or `high`.
- `rationale`: hidden analysis, not exposed to the executor or public user simulator.
- `missing_artifacts`: visible evidence still missing.
- `guidance_tags`: task-agnostic guidance labels from a central allowlist.

`infra_error`, `rate_limit`, and `pre_exec_failed` are runtime statuses, not current supervisor verdicts. Historical artifacts may contain older values and are normalized for compatibility when read.

## 3. Guidance Tags

`guidance_tags` are not task YAML text injected into the executor. They are selected by the answer supervisor from a central allowlist using hidden references and visible evidence.

Current chain:

- The answer-supervisor prompt lists allowed tags derived from `lib/i18n.py`.
- `validate_answer_supervisor_payload()` filters out disallowed tags.
- The runner and WebUI save tags into `score.json`, `supervision_trace.jsonl`, and `supervision/cycle_XX/decision.json`.
- `build_public_feedback()` maps tags to generic public hints.
- Only `SAFE_USER_FEEDBACK_MODE = "composed"` can include those hints in executor continuation text.

In default `candidate_only` mode, guidance tags are recorded and displayed but do not directly enter the next executor prompt.

## 4. Public Handoff

The full supervisor output is not passed to the user simulator. The runner passes only:

```json
{
  "verdict": "continue",
  "attempt_state": "incomplete",
  "recoverable": true,
  "score": 0.35
}
```

This gives the user simulator enough state to decide whether and how to nudge the executor without leaking hidden rubric reasoning.

## 5. WebUI and Run Artifacts

`confidence` and `missing_artifacts` are retained in:

- `score.json`.
- `supervision_trace.jsonl`.
- `supervision/cycle_XX/decision.json`.
- WebUI Trace views.

Historical rich-schema fields are deprecated and should be ignored when reading old `decision.json` or `supervision_trace.jsonl` files:

- `reference_understanding`.
- `failure_reasons`.
- `focus_points`.
- `leakage_risk`.
