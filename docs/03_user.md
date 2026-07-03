# Public User Simulator Role

The public user simulator plays the next user follow-up in the benchmark loop.

## 1. Input Workspace

The runner usually prepares a workspace shaped like:

```text
workspace/
  README.md
  workspace_manifest.json
  public_task.md
  turn_state.json
  role_history.jsonl
  supervisor_feedback.json
  visible/
    executor_prompt.md
    transcript.jsonl
    tool_usage.json
    runtime_probe.json
    runtime_probe_desktop.png
    visible_summary.json
    result/
    agent_sessions/
```

There is no `references/` directory and no `privacy/` directory. `include_hidden_references=False` is the core workspace difference between the user simulator and the answer supervisor.

Like the supervisor, the user simulator does not receive images pre-attached to the Codex conversation by default. `CLAWBENCH_CODEX_ATTACH_IMAGES` controls that behavior and defaults to `"0"`. If the simulator truly needs an image to write a sensible public follow-up, it can call `view_image(path="visible/result/...")`.

`supervisor_feedback.json` contains only four fields:

```json
{
  "verdict": "continue",
  "attempt_state": "incomplete",
  "recoverable": true,
  "score": 0.35
}
```

## 2. Boundary

The user simulator cannot see:

- `references/`.
- The hidden answer.
- The supervisor's `rationale`.
- The supervisor's `missing_artifacts`.

It can only use:

- The original public task.
- The visible execution trajectory.
- The four-field handoff above.

`candidate_feedback` should be a complete standalone instruction that can drive the next executor step. Do not put essential information only in `public_feedback_points`.

## 3. Output Schema

Current schema:

```json
{
  "mode": "instruction",
  "tone": "firm",
  "candidate_feedback": "Please keep checking the video itself and save clearer evidence.",
  "public_feedback_points": [
    "Keep using the video itself as evidence."
  ]
}
```

The runner then sends the payload through the feedback rewriter:

- Pure completion announcements are filtered out.
- `SAFE_USER_FEEDBACK_MODE` in `lib/defaults.py` controls continuation assembly.
- Default `candidate_only` mode uses only `candidate_feedback`, falling back to a generic message if it is empty.
- Optional `composed` mode combines `candidate_feedback`, `public_feedback_points`, public guidance-tag hints, and a generic fallback, then deduplicates and truncates to at most three lines.
- `public_feedback_points` remain in run artifacts even when they are not used for the executor continuation.

## 4. Design Goal

The user simulator should not explain the hidden rubric or reveal benchmark internals. Its job is to act like a plausible user who nudges the agent forward using only public information.
