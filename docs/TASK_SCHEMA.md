# Task Schema

This doc is the single source of truth for what a Clawbench task looks
like on disk: the YAML fields, the hidden `eval_rule.md`, the
`.privacy` env-var manifest, and the supporting directory layout under
`injection/<category>/<task_id>/`.

For a working example, copy [`tasks/000_template/task_000_example.yaml`](../tasks/000_template/task_000_example.yaml)
and its [`injection/000_template/task_000_example/`](../injection/000_template/task_000_example/)
folder (which already has the `eval_rule.md`, `sources/`, `.privacy`
sub-structure populated as a reference).

---

## 1. Directory layout

```
tasks/
  <category>/
    task_<id>_<slug>.yaml         ← this file (the public spec)

injection/
  <category>/
    task_<id>_<slug>/
      references/                  ← supervisor-only
        eval_rule.md               ← REQUIRED. 9-section structured spec.
        *.json / *.png / ...       ← optional hidden reference assets
      sources/                     ← entirely copied into the executor container
      skills/                      ← per-task skill packages (whitelisted via YAML)
      services/                    ← background services (whitelisted via YAML);
                                     harness-private inside the container
                                     (see §3 isolation contract)
      .privacy                     ← optional plain-text env-var name list
```

`task_id` and `category` must match `^[A-Za-z0-9][A-Za-z0-9._-]*$`
(validated by `lib/task.py:_validate_safe_name`). The YAML filename's
`task_<id>_<slug>` part is informal; the authoritative ID is the
`task_id:` field, and that ID determines where `injection/` resources
live.

---

## 2. Top-level YAML fields

| Field | Type | Default | Required | Description |
|---|---|---|---|---|
| `task_id` | string | — | yes | Unique task identifier; must match the directory under `injection/<category>/`. |
| `category` | string | — | yes | One of the 5 capability buckets: `101_skill_usage` / `102_exploration` / `103_long_context` / `104_multimodal` / `105_cross_platform`, or the corresponding Chinese mirror bucket `201_*_zh` through `205_*_zh`. |
| `agent_sys` | enum | `openclaw` | no | `openclaw` / `openclaw_edict` / `nanobot`. Normalized and validated by `lib.task.canonical_agent_sys` during `load_task`. |
| `agent_id` | string | `main` | no | Use `taizi` only when `agent_sys: openclaw_edict`. |
| `model` | string | `lib/defaults.py:DEFAULT_EXECUTOR_MODEL` | no | Executor model. Provider is resolved from `configs/models.local.json` by default. |
| `image_model` | string | falls back to `model` | no | Override for multimodal tasks where the executor model isn't vision-capable. |
| `timeout_seconds` | int | `1200` (20 min) | no | Per-turn executor-only budget. Supervisor / user-simulator time is **not** counted. |
| `max_total_seconds` | int | `1800` (30 min) | no | Cumulative executor budget across all turns. |
| `success_threshold` | float | `1.0` | no | Score threshold (0..1) above which the attempt is `pass`. |
| `recording` | enum | `none` | no | ffmpeg desktop-capture tier inside the container — `none` (no recording, default), `low` (5 fps / 1280x720, debug captures), `high` (10 fps / 1440x900, needed for GUI-fidelity grading). See `lib/runner/media.py`. |
| `headed` | enum | `auto` | no | Executor browser mode. `auto` couples to `recording`: `high` → headed, anything else → headless. `true` forces visible Chromium. `false` forces headless. Resolution lives in `lib/runner/container_lifecycle.py:prepare_runtime`. |
| `task` | string (YAML block scalar) | — | yes | The public end-user request. Shown verbatim to executor + user simulator. Never include hidden references or the answer. |
| `task_snapshot` | string (block) | falls back to `task` | no | Alternative public task text used when `SNAPSHOT_MODE=1` is injected (offline-snapshot variant of the task). |
| `references` | list[string] | `[]` | yes-ish | Relative paths under `injection/<category>/<task_id>/`. Must include at least `references/eval_rule.md`. |
| `sources` | list[string] | `[]` | no | Declarative metadata; the runner copies the entire `sources/` directory regardless. The list is used to hint EDICT's repo-dir picker when exactly one source entry is declared. |
| `skills` | list[string] | `[]` | no | Subdirectories under `injection/<category>/<task_id>/skills/` that get installed to `/root/skills/` in the container. Whitelist — only listed skills are copied. |
| `services` | list[ServiceSpec] | `[]` | no | Background services started before the executor (see §3). |
| `pre_exec` | list[string] | `[]` | no | Scripts under `injection/<category>/<task_id>/` to run on the host **before** the container starts (e.g., to provision sources from a remote). |
| `pre_exec_parallel_safe` | bool | `false` | no | If true, identical task cells may run concurrently and reuse a fresh pre-exec fingerprint/TTL. If false, the dispatcher avoids starting the same task concurrently across model/backend cells while the worker lock serializes host-side provisioning. |
| `codex` | CodexSpec | `CodexSpec()` defaults | no | Supervisor / user-simulator runtime overrides (see §4). |

`privacy:` as a YAML field is **rejected at load time**. Use the
`.privacy` plain-text file instead (see §6).

---

## 3. Service spec

```yaml
services:
  - name: fixture-bootstrap        # used in log filenames; shell-safe (A-Za-z0-9._-)
    path: loc-bootstrap            # relative path under injection/<...>/services/
    start: bash install.sh         # command to spawn the service
    oneshot: false                 # if true, runner awaits exit; else service runs in background
```

Source: `lib/task.py:ServiceSpec` (lines ~280-290).

### Isolation contract

Services declared above are copied into the container at
`/opt/clawbench/.harness/services/<task_id>/<service_path>/` (path
constant: `lib/runner/artifacts.py:PRIVATE_SERVICE_ROOT`).  The parent
`.harness` directory and the per-task service root are chmod `0700`
right after the copy step in
`lib/runner/container_lifecycle.py:prepare_runtime`, so the executor's
default `ls /opt/clawbench/` does not surface them and any `ls` inside
the path returns `EACCES`.

The contract for task authors is:

- **Do not** mention `/opt/clawbench/.harness/services/...` in the
  public `task:` block, in `sources/`, or in any executor-visible
  file.
- Background services must publish their executor-visible output to
  `/tmp_workspace/results/` or `/tmp_workspace/clawbench/service_state/`
  (e.g. a JSON status file or a ready-flag).  The executor reads from
  there, never from the private services path.
- The executor process still runs as `root` inside the container.  Soft
  isolation is sufficient to suppress accidental discovery and to make
  any deliberate `chmod` from the executor an unambiguous escalation
  signal in the transcript; a future PR may add a non-root executor
  user for hard isolation.

---

## 4. CodexSpec

```yaml
codex:
  max_user_followups: 2          # int, default DEFAULT_MAX_USER_FOLLOWUPS
  user_simulator:                # CodexRoleSpec (optional override)
    model: gpt-5.4
    provider: ""                  # blank → use codex.local.toml default
    config: configs/codex.local.toml
    reasoning_effort: high        # low / medium / high
    policy: |                     # body of user-simulator behaviour policy
      <multi-line policy text>
  supervisor:                    # CodexRoleSpec (optional override)
    model: gpt-5.4
    provider: ""
    config: configs/codex.local.toml
    reasoning_effort: high
    instructions: |               # body of supervisor task-specific instructions
      <multi-line instructions>
```

When `user_simulator.policy` is omitted, the runner falls back to
`lib/templates/user_simulator.py:DEFAULT_USER_SIMULATOR_POLICY`. When
`supervisor.instructions` is omitted, the runner falls back to
`lib/templates/supervisor_default.py:DEFAULT_SUPERVISOR_INSTRUCTIONS`.
Both defaults match the paper's Appendix C verbatim; reproduce them
in [`docs/PROMPTS.md`](PROMPTS.md).

`codex.user_simulator.instructions` is **ignored**. The public user
simulator's only task-level customization entry is `policy`. The
dataclass field is kept for shared structure with the supervisor, but
task YAMLs should not set it; setting it has no effect on the rendered
user simulator prompt.

`supervisor.instructions` is composed with the framework prompt's
hard schema: the supervisor model's `verdict` must be one of `pass`,
`continue`, `fail` (the narrowed Round-6 set — task-semantic only)
and `attempt_state` one of the 5 in_progress / incomplete /
complete_but_failed / complete_and_passed / terminal_failure
values.  Framework-runtime states (`infra_error`, `rate_limit`,
`pre_exec_failed`) are detected externally by the framework and
NOT producible by per-task instructions.  See
[`lib/status.py`](../lib/status.py) for the canonical vocabulary.

#### Author rule — `supervisor.instructions` is a posture supplement only

`codex.supervisor.instructions` (and the framework default
`DEFAULT_SUPERVISOR_INSTRUCTIONS`) must stay a *task-specific scoring focus*
supplement. The hard contract — schema fields, `verdict` enum,
`attempt_state` enum, public/hidden boundary, framework-handles-infra
rule — lives once in
[`lib/templates/answer_supervisor.py:TEMPLATE`](../lib/templates/answer_supervisor.py)
and is composed automatically. Authors **must not**:

- redeclare the `verdict` / `attempt_state` enum (would silently drift
  away from `lib/status.py` if either side changes);
- mention `infra_error` / `rate_limit` / `pre_exec_failed` as if the
  model produces them (those are framework synth final statuses);
- copy hidden-reference contents, passwords, or other internal-only
  detail into the supervisor's published fields.

Task-level overrides should only add things like "focus on whether the
PDF was actually downloaded versus URL-only" or "treat partial answers
as continue when X is present". Keep them short.

---

## 5. `eval_rule.md` — 9-section structure

`references/eval_rule.md` is the hidden judging spec. The supervisor
reads it verbatim each cycle and grades the visible evidence against
it. The recommended 9-section skeleton (matches the paper's Appendix
A.3):

| § | Section | What it does |
|---|---|---|
| 1 | Grading Philosophy | What the supervisor should care about most (satisfied checkpoints + supported result). |
| 2 | Task Contract | Restate the public task in supervisor terms. |
| 3 | Source-Selection / Target-Resolution Rules | Disambiguation rules when source choice matters. |
| 4 | Ground-Truth Snapshot | Hidden ground-truth captured at a date — concrete values, URLs, IDs. |
| 5 | Checkpoint Rubric | Weighted checkpoints totalling 1.0; each names observable state + min visible evidence + hidden anchor. |
| 6 | Scoring Policy / Score Caps | Score caps for failure modes; partial credit comes from checkpoints. |
| 7 | Continue vs Fail Guidance | When to prefer `continue` vs `fail`. |
| 8 | Hidden Reference Assets | List of hidden files the supervisor cross-checks. |
| 9 | Dynamic Content Note | How to handle values that may change between snapshot and run. |

The skeleton template lives at
[`injection/000_template/task_000_example/references/eval_rule.md`](../injection/000_template/task_000_example/references/eval_rule.md).

> **Known schema drift.** A small subset of existing tasks in this
> drop number §5 as "Figure Quality Requirements" or similar
> task-specific titles instead of "Checkpoint Rubric" — the section
> still contains the rubric, just under a different label. The
> supervisor reads content, not headings, so grading is unaffected.
> The next round of task cleanup will normalize the titles.

---

## 6. `.privacy` — env-var manifest

Plain-text file at `injection/<category>/<task_id>/.privacy`, one env
var name per line. Blank lines and `# ...` comments are skipped.

```
# Tasks that need an authenticated session
GITHUB_TOKEN
SLACK_BOT_TOKEN
```

At runtime, `lib/privacy.py:load_task_privacy_keys` reads this file and
the runner injects values from the gitignored
`configs/privacy.local.env` into the executor container. Fresh clones
must copy `configs/privacy.example.env` to `configs/privacy.local.env`
and fill real values, or `load_task` will raise a loud missing/empty/
placeholder privacy-key error.

A special key `SNAPSHOT_MODE` controls whether `sources/*_snapshot.json`
files get copied into the container (so the executor can read offline
snapshots instead of hitting live APIs). See `lib/runner/container_lifecycle.py`.

---

## 7. Time budget — long-context category note

The defaults `timeout_seconds=1200` (20 min per turn) and
`max_total_seconds=1800` (30 min global) cover the standard categories.
The paper specifies that long-context tasks (`103_long_context`) should
use 30 min per turn / 45 min global instead. **`lib/task.py` has no
category-level auto-defaulting**; long-context yamls must explicitly
declare:

```yaml
timeout_seconds: 1800
max_total_seconds: 2700
```

To audit which long-context tasks are missing the extended budgets:

```sh
grep -L 'timeout_seconds: 1800' tasks/103_long_context/task_*.yaml
```

A future cleanup will add category-level defaults in `lib/task.py`
`_apply_defaults` so this manual override stops being required.

---

## 8. Start from the template

```sh
cp tasks/000_template/task_000_example.yaml tasks/<category>/task_<id>_<slug>.yaml
mkdir -p injection/<category>/task_<id>_<slug>/{references,sources,skills,services}
cp injection/000_template/task_000_example/references/eval_rule.md \
   injection/<category>/task_<id>_<slug>/references/
# (optional, only if your task needs credentials)
cp injection/000_template/task_000_example/.privacy \
   injection/<category>/task_<id>_<slug>/.privacy
```

Then edit:

1. `task_id` + `category` to match the new directory.
2. The `task:` block — the public end-user request.
3. `injection/<...>/references/eval_rule.md` — fill in all 9 sections.
4. `injection/<...>/sources/` — drop in any input files the executor
   needs.
5. (If applicable) `services:` block + `injection/<...>/services/<svc>/`.
6. (If applicable) `skills:` block + `injection/<...>/skills/<skill>/`.
7. (If credentialed) the `.privacy` file with env-var names.

Verify the task loads:

```sh
python -c "from pathlib import Path; from lib.task import load_task; load_task(Path('tasks/<category>/task_<id>_<slug>.yaml'), Path('.'))"
```

A clean exit means the schema is valid and all referenced injection
assets exist. A loud error names the missing field / file.

---

## 9. Field references

The authoritative parser is [`lib/task.py`](../lib/task.py); read
`_parse_codex` / `_parse_codex_role` / `load_task` for the exact
behaviour, including validation rules and what happens when fields
are omitted.

Default constants used by the parser:

| Constant | Defined in | Used for |
|---|---|---|
| `DEFAULT_EXECUTOR_MODEL` | `lib/defaults.py` | `model` when omitted |
| `DEFAULT_CODEX_MODEL` (`gpt-5.4`) | `lib/defaults.py` | `codex.user_simulator.model` / `codex.supervisor.model` |
| `DEFAULT_REASONING_EFFORT` (`high`) | `lib/defaults.py` | `codex.*.reasoning_effort` |
| `DEFAULT_CODEX_CONFIG_PATH` | `lib/defaults.py` | `codex.*.config` |
| `DEFAULT_MAX_USER_FOLLOWUPS` (`2`) | `lib/defaults.py` | `codex.max_user_followups` |
| `DEFAULT_USER_SIMULATOR_POLICY` | `lib/templates/user_simulator.py` | `codex.user_simulator.policy` (fallback) |
| `DEFAULT_SUPERVISOR_INSTRUCTIONS` | `lib/templates/supervisor_default.py` | `codex.supervisor.instructions` (fallback) |
