# Reproducibility

This doc covers how to reproduce the experimental results reported in
the UniClawBench paper.  Three things to know up front:

1. The **production dispatcher path runs a single supervisor per
   attempt**.  The paper's 92% inter-rater agreement (and the
   r=0.71 / ρ=0.68 score correlations) were measured by re-running
   every attempt under a *second* independent supervisor in a separate
   off-repo evaluation script — that infrastructure is not part of the
   default codebase.  Sketch in §3 below if you want to reproduce.

2. The OSS drop ships the **full 400-task corpus** across the 5
   capability dimensions — 200 EN tasks (suites `101`–`105`, 40 each)
   plus their 200 ZH mirrors (suites `201`–`205`, 40 each), all present
   in `injection/` and `tasks/`.  This matches the paper's headline
   400-task figure, so numbers reported against the current task set
   cover the complete benchmark.

3. There are **no error bars** on the reported scores.  Each
   (model × task × backend) combination was run once in the paper's
   experiments due to compute cost.  This repository does not include a
   built-in "repeat each cell N times" mode.  If you want confidence
   intervals, run the same matrix into separate fresh runs roots or
   intentionally reset the cells you want to rerun before merging
   results; every additional run is just another attempt directory under
   `runs/<backend>/<model_dir>/<suite>/<task>/p*-*/`.

---

## 1. Models & backends evaluated

The paper benchmarks a broad SOTA model set against the OpenClaw backend plus a
3-framework cross-evaluation (OpenClaw / EDICT / Nanobot).  The
model registry lives in `configs/models.local.json`; the dispatch
config picks which (backend, model_dir) combinations to evaluate via
the `matrix:` block.  `matrix` and `priorities` are **orthogonal**:
`matrix` declares the experiment set (backend × model), `priorities`
declares status-tier ORDER only.  Declaring `backend_in` / `model_in`
under `priorities[]` is rejected (`config.py` raises `ValueError`);
backend × model selection lives exclusively in `matrix:`.

To reproduce the paper's main table, configure
`configs/orchestra.local.yaml` with:

* For the headline table, one `matrix` group pinning the OpenClaw
  backend and the full model id set you are reproducing:

  ```yaml
  matrix:
    - backend: openclaw
      models: [<model-1>, <model-2>, ...]   # model_dir names
  ```

* For the cross-framework comparison, add groups for the other two
  backends (they can share a model set):

  ```yaml
  matrix:
    - backend: openclaw
      models: [<model-1>, ...]
    - backends: [openclaw_edict, nanobot]   # share one model set
      models: [<model-1>, ...]
  ```

* `priorities:` carries only status tiers (`{id, status_in}`) — no
  `backend_in` / `model_in`; omit it to use the default order.

See `configs/orchestra.example.yaml` for the full field layout.

---

## 2. Supervisor / user-simulator configuration

Both Codex roles must run on the paper's grader configuration to make
results comparable:

```yaml
supervision:
  supervisor:
    provider: <your-codex-provider>
    model: gpt-5.4              # paper used gpt-5.4 with reasoning_effort=high
  user_simulator:
    provider: <your-codex-provider>
    model: gpt-5.4
```

`reasoning_effort=high` is the default (set in `lib/defaults.py:DEFAULT_REASONING_EFFORT`).
Tasks may override the per-role model via the `codex:` block in their
YAML — see [`docs/TASK_SCHEMA.md`](TASK_SCHEMA.md) §4.

---

## 3. Inter-rater agreement (paper §reliability)

The 92% pass/fail agreement and 0.71 / 0.68 correlation figures come
from running each attempt through **two** independent supervisor
instances and comparing decisions.  This is not automated in the
default dispatcher loop — adding a second supervisor pass would double
grader cost on every production run, which is rarely what you want.

To reproduce the measurement off-line, the rough recipe is:

```python
# pseudo-code, not committed
from lib.supervision import run_answer_supervisor, AttemptSupervisorContext
from lib.supervision.workspace import prepare_role_workspace

# for each completed attempt under runs/.../p*-*/:
for attempt_dir in sorted(runs_root.rglob("p*-*")):
    ctx = AttemptSupervisorContext(...)             # rebuild context from disk
    decision_a = run_answer_supervisor(ctx, prompt=..., seed=1)
    decision_b = run_answer_supervisor(ctx, prompt=..., seed=2)
    record(attempt_dir, decision_a, decision_b)

# then compute:
#   pass/fail agreement = mean(verdict_a == verdict_b)
#   score correlation   = pearson_r(score_a, score_b)
#   score correlation   = spearman_ρ(score_a, score_b)
```

The two supervisor instances must each use their own isolated Codex
workspace (`lib.supervision.workspace.prepare_role_workspace` already
does this — pass a distinct `workspace_root` per run) and must see
the same `references/eval_rule.md` and `visible/` evidence.

The pseudocode above is the current public contract for reproducing
the inter-rater check.  The exact paper-time batch harness depended on
the archived experiment storage layout, so it is intentionally not part
of the default runtime path; a future release may add a convenience
`scripts/eval_inter_rater.py` wrapper around the public supervision APIs.

---

## 4. Time budgets

Standard tasks use `timeout_seconds=1200` (20 min per turn) and
`max_total_seconds=1800` (30 min global).  Long-context tasks
(`category: 103_long_context`) **must explicitly override** to:

```yaml
timeout_seconds: 1800            # 30 min per turn
max_total_seconds: 2700          # 45 min global
```

The loader does not auto-default these per category — see
[`docs/TASK_SCHEMA.md`](TASK_SCHEMA.md) §7 for the rationale and a grep
command to audit which long-context tasks are missing the override.

Reproducing the paper's reported scores requires running each task
with the same time budgets used in the paper experiments; mismatch
here can shift `incomplete` vs `complete_but_failed` ratios noticeably.

---

## 5. Metrics

Pass rate (PR) and average score (AS) are computed by
`webui/aggregate.py:aggregate_runs`, which groups every
`runs/**/summary.json` by model and by backend and reduces each group
with `_summarize(rows)`:

* **PR** (`pass_rate`) = (# rows where task-level `summary.json`
  has `passed: true`) / n
* **AS** (`avg_score`) = mean of `finalScore` across the group's n rows

Only the terminal-result statuses contribute to these means
(`rate_limit` / `infra_error` / `pre_exec_failed` rows are filtered out).

Per-attempt scores come from the supervisor's `score` field in
`supervision_trace.jsonl` (latest cycle).  `passed` is computed against
`task.success_threshold` (default 1.0; some tasks set lower bounds).
The terminal `finalStatus` label is retained for trace review, but PR uses
the rolled-up `passed` boolean so a supervisor verdict of `pass` below the
success threshold is not counted as a benchmark pass.

To recompute PR/AS from a runs tree without the WebUI, call
`aggregate_runs()` (it reads `$CLAWBENCH_RUNS_DIR`, defaulting to
`./runs`) and summarise its flat `rows` list — or read a specific
model's / backend's `total` block:

```sh
python -c "
from webui.aggregate import aggregate_runs, _summarize
agg = aggregate_runs(force=True)

# Overall (every terminal-result row across all backends & models):
overall = _summarize(agg['rows'])
print('PR:', overall['pass_rate'])
print('AS:', overall['avg_score'])
print('N rows:', overall['n'])

# Per model (each entry has a 'total' = {pass_rate, avg_score, n, ...}):
for m in agg['models']:
    t = m['total']
    print(m['label'], t['pass_rate'], t['avg_score'], t['n'])
"
```

---

## 6. Determinism — there is none

The paper's scores are not reproducible bit-for-bit because:

* Codex / OpenClaw / Nanobot use non-zero sampling temperature by
  default.
* Live tasks (web search, GUI navigation) depend on time-of-day state
  of the public web.
* Task fixtures that reference offline snapshots (`SNAPSHOT_MODE=1`)
  are deterministic in isolation but the executor's path through them
  still varies.

What *should* reproduce within ~5% is the **distribution** of pass
rates across models and categories.  If your reproduction shows
order-of-magnitude divergence, check first:

1. Are you using `gpt-5.4` (or equivalent) for both Codex roles?
2. Are long-context tasks getting their 30/45 min budgets?
3. Are all expected `(backend, model_dir)` combos actually declared in
   your `matrix:` block?
4. Did every worker report completed attempts back into the controller's
   `runs/` tree? A silent rsync-failed batch will show up as missing
   summary rows in the WebUI or `runs/.runs_index.json`.

This repository does not ship a built-in "repeat each cell N times" mode.
For repeated estimates, run the same matrix into separate fresh runs roots
or intentionally reset the cells you want to rerun before merging results.
