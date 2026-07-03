# `scripts/orchestra/` — distributed task dispatcher

All orchestrator-side logic lives here as a single Python package.  Run
it from a **controller host** that sits between the developer and the
worker pool.  The controller maintains `runs/` (the canonical results
tree) and the WebUI; workers receive tasks over SSH, run containers,
and rsync attempt directories back.

```
scripts/orchestra/
├── __init__.py
├── config.py             # YAML loader / dataclasses
├── stats.py              # walk runs/, bin incomplete tasks into priority buckets
├── refresh_summary.py    # rebuild task-level summary.json from p*-* attempts
├── dispatch.py           # the main loop (priority → ssh worker → drain done)
├── worker_runner.py      # tiny CLI invoked over ssh on each worker
├── top.py                # 1s-refresh terminal monitor
├── prepare_node.py       # one-shot worker provisioning (apt, venv, docker)
├── distribute_images.sh  # peer-to-peer docker tag distribution
└── runtime/              # gitignored — local state
    ├── priorities.jsonl
    ├── inflight.jsonl
    ├── done.jsonl
    └── done_history/     # archived done.jsonl rotations
```

## Conventions used in this doc

Examples below use environment variables for paths and hostnames that
differ by deployment.  Set them once in your shell and the examples
become copy-pasteable:

```sh
# Controller (dispatcher + webui + runs/)
export CONTROLLER_HOST=controller             # SSH alias in ~/.ssh/config
export CLAWBENCH_REPO=/srv/uniclawbench/UniClawBench
export CLAWBENCH_VENV=/srv/clawbench/venv
export CLAWBENCH_RUNS_DIR=/srv/clawbench/runs
export CLAWBENCH_IMAGE_DIR=/srv/clawbench/images
export CLAWBENCH_LOG_DIR=/srv/clawbench/logs

# Worker pool (SSH aliases configured on the controller)
export WORKER_HOSTS="worker1 worker2 worker3 worker4"
```

The orchestra config (`configs/orchestra.local.yaml`) is the source of
truth for the actual hostnames and worker_repo paths; the env vars
above only make the doc examples readable.

## Helper scripts

| Script | When to run |
|--------|-------------|
| `build_images.sh` | Build the required Docker images on a worker or seed host. Use `--distribute-to` when that seed can SSH to the rest of the pool. |
| `distribute_images.sh` | Copy image tags from an explicit seed host to explicit worker hosts via `docker save | docker load`. |
| `prepare_node.py` | Idempotently prepare each worker: packages, Python venv, image checks, and runtime directories. |
| `dispatch.py` | Long-lived controller-side scheduler. |
| `top.py` | Terminal progress monitor for the controller-side queue and worker state. |

## End-to-end run flow

1. **Clone and configure hosts** — clone the same repository on the
   controller and every worker, then configure passwordless SSH:
   controller -> workers, and workers -> controller for result callbacks.
   Set `worker_repo` in `configs/orchestra.local.yaml` to the checkout path
   used on the workers. `worker_python` defaults to the venv that
   `prepare_node.py` creates (`/opt/clawbench-venv/bin/python`); change it
   if your worker dependencies live elsewhere.
   Create the controller-side virtualenv before running controller commands:
   ```sh
   python3 -m venv "$CLAWBENCH_VENV"
   "$CLAWBENCH_VENV/bin/pip" install -e "$CLAWBENCH_REPO"
   ```
2. **Edit config** — copy `configs/orchestra.example.yaml` to
   `configs/orchestra.local.yaml` and fill in:
   * worker SSH aliases (per-host `parallel` + `skip` flags)
   * **`suites:`** — which task suites to dispatch. Empty / omitted = every
     suite (101–105 + 201–205); the `000_template` / `001_smoketest`
     scaffolding is always excluded. List a subset to narrow a run, e.g.
     `[101_skill_usage, 201_skill_usage_zh]`.
   * **`matrix:`** — the backend x model set to run. A list can give each
     backend its own model set; `{backends, models}` is accepted as a
     cross-product shorthand.
   * **`priorities:`** — optional status-tier ordering. When `matrix:` is
     present, priorities define order only with `{id, status_in}` entries.
   * model concurrency caps (`model_caps` per `model_dir` + `default_model_cap`)
   * **`supervision:` block** — provider + model for both the supervisor
     and the user_simulator.  These are required; missing them raises at
     dispatcher startup so a misconfigured deploy is caught immediately.
     These Codex role providers are resolved from `configs/codex.local.toml`;
     the executor matrix models are resolved from `configs/models.local.json`.
     The example config files are templates only; runtime code refuses to use
     them unless `CLAWBENCH_ALLOW_EXAMPLE_CONFIG=1` is explicitly set for a
     documentation or test run.
3. **Build Docker images** — build on each worker, or build once on a seed
   worker and distribute to the others. The controller only schedules work;
   every worker that may run tasks needs the images locally:
   ```sh
   scripts/orchestra/build_images.sh --host worker1 --remote-root $CLAWBENCH_REPO
   scripts/orchestra/build_images.sh --host worker1 --remote-root $CLAWBENCH_REPO \
     --distribute-to "worker2,worker3,worker4"
   ```
4. **One-time per worker** (idempotent):
   ```sh
   ssh $CONTROLLER_HOST
   cd $CLAWBENCH_REPO
   $CLAWBENCH_VENV/bin/python -m scripts.orchestra.prepare_node \
     --config configs/orchestra.local.yaml \
     --local-repo $CLAWBENCH_REPO \
     --image-dir $CLAWBENCH_IMAGE_DIR
   ```
   Add `--check-ports` only after proxy/adapter services are expected to be
   listening on each worker; fresh workers usually pass through this step
   before those ports exist.
   The SSH account used for each worker must be able to run Docker and write
   to `worker_repo`; if you keep the default `/opt/clawbench-venv`, it also
   needs permission to create or update that venv during preparation.
5. **Start the dispatcher** (long-lived):
   ```sh
   nohup $CLAWBENCH_VENV/bin/python -m scripts.orchestra.dispatch \
     --config configs/orchestra.local.yaml \
     --tasks-root $CLAWBENCH_REPO/tasks \
     > $CLAWBENCH_LOG_DIR/dispatch.log 2>&1 &
   ```
6. **Watch progress**:
   ```sh
   $CLAWBENCH_VENV/bin/python -m scripts.orchestra.top \
     --config configs/orchestra.local.yaml
   ```

## How tasks are picked

The task universe is `suites:` (or every suite if empty) x the
`(backend, model)` combos declared by `matrix:`.  A `priorities:` block is
optional and defines status-tier order.  When both are present, the config
loader combines them status-major: for each status tier, one bucket per
matrix group.

`stats.recompute_priorities` produces an ordered list of priority buckets
based on the YAML.  Each task in `runs/` is bucketed against the priorities
*top-down*; the first matching priority wins.  A task qualifies for a
priority bucket if its current best status (across all `p*-*` attempts)
matches every non-empty filter list (`backend_in`, `model_in`,
`status_in`).  Suites not in `suites:` are never enumerated, so they never
enter any bucket.

After every recompute, the dispatcher also appends two synthetic
buckets at the END of the priority list:

* `P100_session_exhausted` — tasks whose in-memory
  ``DispatchState.session_attempts`` has reached
  ``GLOBAL_MAX_ATTEMPTS`` (default 3).  Strictly lower priority than
  every user-defined bucket; only dispatches when every user bucket
  drains.  Restarting the dispatcher clears the counter so these
  tasks rejoin their normal buckets.

* `P200_suspended` — tasks whose ``session_attempts`` crossed the
  higher ``SESSION_P200_THRESHOLD`` (default 6).  Never dispatches
  while this dispatcher process is alive.  Restarting the dispatcher
  is the documented release path; ``release_p200.py`` is retained as
  a legacy CLI only — it does not affect Round 16+ routing.

Both ceilings are session-only (in-memory).  They never read
``runtime/done_history/``, so historical attempts from prior
dispatcher generations cannot keep a task suspended in the current
process.

### Main scheduling loop — unified dispatch (default)

The main loop is ``run_unified_dispatch``: it flattens every bucket's
tasks into a single priority-ordered list, then tries to fill every
idle worker with the highest-priority task that ``can_start`` accepts.
There is **no T1→T2 barrier** — a P2 task can occupy an idle worker
while P1 still has stuck inflight, eliminating the Round-10 stall
where a single slow P1 task froze the cluster.

Inside this loop a *wave* is the set of tasks ``reserve()`` has
handed out since the last ``maybe_advance_round()`` cleared the
priority's subset.  Round 16's wave isolation is **per-priority**:
each priority_id keeps its own wave subset in
``DispatchState.dispatched_this_round``.  The moment a priority's
subset has no remaining intersection with ``inflight_by_task`` (every
task that priority dispatched has finished), that subset clears and
``recompute_priorities`` can re-route the survivors into the next
priority — without waiting for unrelated priorities that may still
be running.

Concrete consequence: a fail-fast P1 task that hits ``rate_limit``,
``infra_error``, or ``executor_incomplete`` is normally re-routed to
P2_recoverable by the next recompute.  Under per-priority wave it
joins the new P2 wave subset immediately once P1 drains, even if P3
still has slow inflight.  Cross-bucket dedup in ``can_start`` walks
every priority's subset, so the same task cannot be dispatched under
two priorities simultaneously.

``run_one_bucket`` is kept as a `--once` / smoke-test helper that
walks a single bucket to completion and exits — useful for fixture
tests, not for production scheduling.

### Inflight, restart, and TTL

A task is *locked* in `runtime/inflight.jsonl` from the moment
dispatch starts an SSH command for it until the worker reports back
via `runtime/done.jsonl`.  Stats reads inflight when bucketing, so a
task already executing never re-enters a queue.

On startup, ``restore_inflight_from_disk()`` rebuilds the in-memory
inflight dict + worker / model_cap counters from
``inflight.jsonl``.  The unified dispatch loop's exit guard requires
``state.inflight_by_task`` to be empty alongside the bucket / future
checks, so a freshly-restarted dispatcher does NOT bail out while it
still has restored-from-disk inflight to drain.

When a row's ``ts_start`` is older than
``cfg.max_inflight_age_seconds``, ``stats._load_inflight`` drops it
from the on-disk file AND reports the key back to the dispatcher,
which calls ``state.release()`` to keep its in-memory accounting in
sync.  The expired key's worker / model_cap slot becomes available
on the next ``can_start`` pass.

## How results flow

Each `worker_runner` invocation:

1. Sets `CLAWBENCH_HOST_TAG` (e.g. `worker1`) so the per-attempt directory
   name becomes `p1-<host>-<rand>` — globally unique.
2. Runs `scripts/run_eval.py` exactly as a single-task command.
3. `rsync`s the resulting `p1-<host>-<rand>/` directory back to the
   controller's `runs/<backend>/<model>/<suite>/<task>/` (NOT the
   task-level `summary.json`).
4. SSH-appends a JSON line to `$CONTROLLER_HOST:runtime/done.jsonl`.
5. Removes its local copy of the attempt dir, leaving the worker disk
   clean.

The controller's drain loop reads `done.jsonl`, releases the inflight
lock, and calls `refresh_summary.refresh_one_task_with_index(task_dir,
runs_root)` so the task-level `summary.json` AND the flat
`runs/.runs_index.json` cache immediately reflect the new attempt.

If a worker is configured with `lightweight_sync: true`, step 3 sends a
small diagnostics allowlist instead of the full attempt tree. This is useful
for storage-constrained overnight runs, but rich Trace artifacts such as large
screenshots, recordings, and full Codex session workspaces remain on the
worker unless you copy them manually before cleanup. Leave lightweight sync
disabled when preparing public demos or a complete static WebUI export.

## Proxy is per-provider optional

The orchestra runtime does NOT force every API call through a local
proxy.  Each provider in `configs/models.local.json` chooses opt-in:

* A `proxy:` inline block or a `proxyRef:` pointing at a named entry
  under top-level `proxies:` → the runtime starts a shared tunnel +
  adapter when a task using this provider begins, and tears it down
  when the last task using it ends.
* No `proxy:` / `proxyRef:` → the runtime calls the API directly.

Adapters are only for providers that need request-shape compatibility
patches, such as translating Codex Responses API traffic to a
chat-completions-only upstream.  Generic OpenAI-compatible endpoints, or
any custom gateway that already speaks the wire protocol you configure,
should omit the `proxy:` block; the adapter is overhead they do not need.

To verify what proxies are started for a task, run:

```sh
python -m scripts.orchestra.dispatch --config configs/orchestra.local.yaml \
    --tasks-root tasks --once --max-tasks 1
```

and watch for `proxy tunnel started …` log lines.  If a provider
opted out, you'll see zero of those for it.

## Graceful shutdown

The dispatcher installs SIGINT + SIGTERM handlers.  When Ctrl+C or
`pkill -TERM` lands:

1. The shutdown event is set.
2. ``run_unified_dispatch`` (or the legacy ``run_one_bucket`` under
   ``--once``) stops submitting NEW tasks and waits on the already-
   inflight futures to finish so their `done.jsonl` callbacks
   complete.
3. The main loop exits its idle poll immediately.
4. A final `_drain_done_file` pass catches any rows that landed
   during teardown so `inflight.jsonl` is consistent on next start.
5. Restarting the dispatcher clears ``session_attempts``, so any
   tasks previously parked in P100/P200 automatically rejoin their
   user buckets on the next ``recompute_priorities`` pass.

What this means for operators: Ctrl+C is safe.  Already-running tasks
finish normally and report back; pending bucket entries roll back to
the next dispatcher startup automatically.  No SSH subprocesses are
killed — that would leak inflight rows.

If you genuinely need to abort an in-flight task (e.g. a stuck
worker), Ctrl+C the dispatcher first, then SSH into the worker and
`docker kill` / `pkill -f run_eval.py` there.

## `runs/.runs_index.json` — the webui fast-path cache

`refresh_summary` writes one extra file at the top of the runs tree:

```
<runs_root>/.runs_index.json     # JSON; one row per task; 9 fields each
```

It is the **only** source the webui's `/api/runs` reads when present,
and it's why the trace page loads in ~50 ms instead of ~20 s.  The
cache stores the nine fields the trace UI actually consumes:

```
taskId  category  backend  model  summaryPath  finalStatus
finalScore  runtimeMs  continuationCount
```

Heavy detail data (score, usage, supervision trace, etc.) is **not**
in the index — the webui still reads those on demand via
`/api/attempt?path=…` when the user clicks a card.

### Index lifecycle — who writes it, when

| Trigger | Updated by | Scope |
|---|---|---|
| Dispatcher startup | `refresh_all_tasks()` | full rebuild |
| Each worker DONE callback | `refresh_one_task_with_index()` | single row upsert |
| Dispatcher full-refresh timer | `refresh_all_tasks()` | periodic belt-and-braces rebuild |
| Operator runs `--index-only` CLI | `rebuild_index_only()` | full rebuild, no summaries touched |

So **as long as task results arrive via the orchestra pipeline, the
cache stays consistent automatically**.  Nothing operator-facing.

### Webui fallback (the safety net)

The webui never trusts the cache blindly.  Before serving from it,
`webui/server.py::_load_runs_index` checks:

1. File exists and parses as JSON
2. `version` matches the schema the webui knows how to read
3. `mtime(index)` is at least as new as every `summary.json` under
   `runs_root` (with 1 s clock-skew slack)

If any check fails, `/api/runs` falls back to the original tree-walking
implementation and serves correct (slower) data.  The fallback returns
the exact same JSON shape, so the trace page is functionally identical
either way — only the latency differs.

### When you must refresh manually

The cache only goes stale if a `summary.json` is created or modified
**outside** the orchestra pipeline.  Examples:

* You ran `scripts/run_eval.py` directly on the controller (not via dispatcher)
* You manually `rsync`-ed a new attempt directory into `runs/`
* You hand-edited a `summary.json` to fix a bad finalStatus
* You restored a runs subtree from backup

In any of those cases the webui will detect staleness and **silently
fall back to the slow scan path** — so you don't *have* to refresh,
but the trace page will be ~20 s slow until you do.  To restore the
fast path, rebuild the cache:

```sh
ssh $CONTROLLER_HOST
cd $CLAWBENCH_REPO
$CLAWBENCH_VENV/bin/python -m scripts.orchestra.refresh_summary \
  --runs-root $CLAWBENCH_RUNS_DIR --index-only
# rebuilt index with N rows → $CLAWBENCH_RUNS_DIR/.runs_index.json
```

`--index-only` is the cheap form: it walks existing `summary.json`
files and rewrites `.runs_index.json` from them, **without** re-deriving
attempt statuses.  Takes <1 s for ~3 000 tasks.

If you also need to re-derive task-level summaries from their `p*-*`
attempts (e.g. a stray attempt directory landed without an updated
parent summary), use the full form:

```sh
$CLAWBENCH_VENV/bin/python -m scripts.orchestra.refresh_summary \
  --runs-root $CLAWBENCH_RUNS_DIR
# refreshed N task summaries (+ rewrote .runs_index.json)
```

Takes ~3 s and is safe to run any time.  Both forms write atomically
(tmp + rename), so the webui never reads a half-written file.

### Resetting / deleting the index

`$CLAWBENCH_RUNS_DIR/.runs_index.json` is a pure cache —
deleting it is always safe.  The webui falls back to the slow scan,
and the next time `refresh_summary` runs (dispatcher will do this
automatically) the cache rematerializes.

## Why no aggregator?

The old aggregator hardlinked the "best" attempt per task into a
separate aggregate `runs/` tree, which (a) lost historical attempts
whenever a new better one arrived and (b) added an extra moving part on
the critical path.  In the orchestra layout, every attempt is a real
directory under its task; the task-level `summary.json` is rebuilt from
those directories on every relevant event, so the webui always sees the
cluster's best result *and* can drill into any specific historical
attempt.
