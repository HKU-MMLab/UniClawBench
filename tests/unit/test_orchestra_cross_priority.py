"""Round 11 / A1: cross-priority unified dispatch source-level guard.

The full ``run_unified_dispatch`` exercises real ThreadPoolExecutor +
``recompute_priorities`` (which talks to disk via ``refresh_summary``).
Setting that up cleanly in a unit test would be a large fixture; for
now we pin the **contract** at source level:

- ``dispatch.py`` defines ``run_unified_dispatch`` at module scope.
- ``main()`` uses ``run_unified_dispatch`` (not the legacy bucket
  barrier ``for bucket: run_one_bucket(); break``).
- Inside ``run_unified_dispatch``, tasks are flattened across all
  buckets in priority order BEFORE being assigned to workers — i.e.
  no per-bucket loop with an early ``break``.

The actual cross-priority filling behavior is then validated end-to-
end in the Round 11 / Phase D parallel-ceiling experiments on worker1-4.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


DISPATCH_PY = Path(__file__).resolve().parents[2] / "scripts" / "orchestra" / "dispatch.py"


@pytest.fixture(scope="module")
def dispatch_src() -> str:
    return DISPATCH_PY.read_text(encoding="utf-8")


def test_run_unified_dispatch_defined(dispatch_src: str) -> None:
    """The new entrypoint must exist at module scope."""
    tree = ast.parse(dispatch_src)
    fn_names = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    assert "run_unified_dispatch" in fn_names


def test_run_one_bucket_still_defined(dispatch_src: str) -> None:
    """``run_one_bucket`` kept for ``--once`` / smoke tests."""
    tree = ast.parse(dispatch_src)
    fn_names = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    assert "run_one_bucket" in fn_names


def test_main_uses_unified_dispatch(dispatch_src: str) -> None:
    """The main loop must call ``run_unified_dispatch`` for the
    long-running path.  Catches a regression where someone reverts
    to the bucket-barrier ``for bucket: run_one_bucket(); break``."""
    # Locate main() body and confirm it references run_unified_dispatch.
    tree = ast.parse(dispatch_src)
    main_fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "main"),
        None,
    )
    assert main_fn is not None
    main_text = ast.get_source_segment(dispatch_src, main_fn) or ""
    assert "run_unified_dispatch" in main_text, (
        "main() must call run_unified_dispatch (Round 11 / A1)"
    )


def test_unified_dispatch_flattens_across_buckets(dispatch_src: str) -> None:
    """The unified dispatcher must build a flat task list across ALL
    buckets BEFORE the worker-fill loop.  This is the core property
    that breaks the bucket barrier."""
    # Read run_unified_dispatch body
    tree = ast.parse(dispatch_src)
    udf = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "run_unified_dispatch"),
        None,
    )
    assert udf is not None
    body_text = ast.get_source_segment(dispatch_src, udf) or ""
    assert "flat_tasks" in body_text, (
        "run_unified_dispatch must build a flat_tasks list across buckets"
    )
    # And the flattening should happen before the worker loop
    flat_idx = body_text.find("flat_tasks.append")
    worker_idx = body_text.find("for worker in sorted(state.workers")
    assert flat_idx != -1 and worker_idx != -1
    assert flat_idx < worker_idx, (
        "flat_tasks must be built BEFORE the worker-fill loop "
        "(otherwise workers can only see one bucket at a time)"
    )
    # Round 12 bugfix: each flattened task must carry its source
    # priority_id so DispatchState.can_start can apply the
    # session-attempts gate selectively (skip the gate for P100/P200
    # graveyard + suspended dispatches).
    assert "priority_id" in body_text, (
        "flat_tasks entries must be tagged with their source bucket's "
        "priority_id (Round 12 bugfix)"
    )


def test_unified_dispatch_walks_workers_least_loaded_first(dispatch_src: str) -> None:
    """Preserve Round-5/Phase-5 least-loaded scheduling."""
    tree = ast.parse(dispatch_src)
    udf = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "run_unified_dispatch"),
        None,
    )
    body_text = ast.get_source_segment(dispatch_src, udf) or ""
    assert "sorted(state.workers, key=lambda w: w.inflight)" in body_text


def test_unified_dispatch_respects_can_start(dispatch_src: str) -> None:
    """``state.can_start(task, worker)`` is the single source of
    truth for model_caps + worker.parallel + skip checks; unified
    dispatch must use it (not reinvent the logic)."""
    tree = ast.parse(dispatch_src)
    udf = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "run_unified_dispatch"),
        None,
    )
    body_text = ast.get_source_segment(dispatch_src, udf) or ""
    assert "state.can_start(" in body_text


def test_recompute_priorities_routes_to_p100_on_session_exhaustion(tmp_path: Path) -> None:
    """Round 12 / E1: a task with session_attempts >= GLOBAL_MAX_ATTEMPTS
    is routed to the synthetic P100 graveyard bucket, NOT to the
    user-defined buckets that would otherwise match its status.

    P100 is appended after every user bucket, so it's strictly lowest
    priority and only dispatches when every other bucket is empty.
    """
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import stats as stats_mod
    from scripts.orchestra.stats import GLOBAL_MAX_ATTEMPTS, P100_BUCKET_ID

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_first_pass
    label: first pass
    match:
      backend_in: ["openclaw"]
      model_in: ["test-model"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")

    runs_root = tmp_path
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    task_key = ("openclaw", "test-model", "101_test_suite", "task_demo")

    # Round 1: no session attempts → task goes to P1
    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={},
    )
    # buckets = [P1, P100, P200]; P100 + P200 are always appended
    assert len(buckets) == 3
    assert buckets[0]["priority_id"] == "P1_first_pass"
    assert buckets[1]["priority_id"] == P100_BUCKET_ID
    assert buckets[2]["priority_id"] == "P200_suspended"
    assert len(buckets[0]["tasks"]) == 1, "Round 1: task should be in P1"
    assert len(buckets[1]["tasks"]) == 0, "Round 1: P100 should be empty"
    assert len(buckets[2]["tasks"]) == 0, "Round 1: P200 should be empty"

    # Round 2: session_attempts at exactly GLOBAL_MAX_ATTEMPTS → P100
    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={task_key: GLOBAL_MAX_ATTEMPTS},
    )
    assert len(buckets[0]["tasks"]) == 0, (
        f"Round 2: task with {GLOBAL_MAX_ATTEMPTS} session attempts must "
        "NOT be in P1"
    )
    assert len(buckets[1]["tasks"]) == 1, "Round 2: task must be in P100"
    assert buckets[1]["tasks"][0]["task"] == "task_demo"
    assert buckets[1]["tasks"][0]["attempts"] == GLOBAL_MAX_ATTEMPTS

    # Round 3: simulate dispatcher restart (session_attempts cleared) →
    # task returns to P1.  This is the documented "release" path.
    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={},
    )
    assert len(buckets[0]["tasks"]) == 1, (
        "Round 3: restart cleared session_attempts → task back in P1"
    )
    assert len(buckets[1]["tasks"]) == 0


def test_recompute_priorities_sorts_bucket_by_attempts_asc(tmp_path: Path) -> None:
    """Round 12 / E1: within a single bucket, tasks are sorted by
    session attempts ASC so fresh tasks (attempts=0) dispatch before
    retries (attempts=1+).  This is how we get the "T3 first wave drains
    before retries" semantic without an explicit wave mechanism.
    """
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import stats as stats_mod

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_first_pass
    label: first pass
    match:
      backend_in: ["openclaw"]
      model_in: ["m1"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True)
    for n in ("a", "b", "c"):
        (suite_dir / f"task_{n}.yaml").write_text(
            f"task_id: task_{n}\n", encoding="utf-8"
        )

    runs_root = tmp_path
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    # Mix of attempts: task_a=2, task_b=0, task_c=1
    session_attempts = {
        ("openclaw", "m1", "101_test_suite", "task_a"): 2,
        ("openclaw", "m1", "101_test_suite", "task_c"): 1,
    }
    # task_b has no entry → defaults to 0

    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts=session_attempts,
    )
    bucket_tasks = buckets[0]["tasks"]
    attempts_in_order = [t["attempts"] for t in bucket_tasks]
    # Must be ASC sorted
    assert attempts_in_order == [0, 1, 2], (
        f"Expected ASC sort by attempts [0, 1, 2]; got {attempts_in_order}"
    )
    # And task_b (attempts=0) comes first
    assert bucket_tasks[0]["task"] == "task_b"


def test_recompute_priorities_orphan_running_treated_as_missing(tmp_path: Path) -> None:
    """Round 12 / E2: a summary.json with finalStatus=running, whose
    task is NOT in inflight.jsonl, must be treated as ``missing`` so
    P1 (status_in=[missing]) can re-claim it.  Without this, the task
    would be a zombie — not in any bucket's status_in.

    This is the fix for Round 11's worker3 18-edict pattern (containers
    crashed after writing the ``running`` heartbeat but before the
    final status write).
    """
    import json
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import stats as stats_mod

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_first_pass
    label: first pass
    match:
      backend_in: ["openclaw"]
      model_in: ["test-model"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")

    runs_root = tmp_path
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    # Write an orphan summary.json with finalStatus=running.
    task_dir = runs_root / "openclaw" / "test-model" / "101_test_suite" / "task_demo"
    task_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text(
        json.dumps({"finalStatus": "running"}),
        encoding="utf-8",
    )

    # No inflight.jsonl entry for this task → it's an orphan.

    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={},
    )
    # E2: orphan-running should be promoted to "missing", landing in P1
    assert len(buckets[0]["tasks"]) == 1, (
        "orphan finalStatus=running should be reclaimed by P1 (status_in=missing)"
    )
    assert buckets[0]["tasks"][0]["task"] == "task_demo"
    # The recompute should record the demoted status as "missing" so
    # bucket-matching reasons stay legible in the priorities.jsonl
    # snapshot.
    assert buckets[0]["tasks"][0]["status"] == "missing"


def test_recompute_priorities_routes_to_p200_on_session_overflow(tmp_path: Path) -> None:
    """Round 16 / P0-1: P200 is now session-only.  A task whose
    ``DispatchState.session_attempts`` has crossed
    ``SESSION_P200_THRESHOLD`` is routed to the synthetic P200 bucket
    regardless of any historical done_history rows on disk.

    Restart releases P200 automatically because session_attempts is
    per-process (verified separately in
    ``test_session_p200_resets_on_restart.py``).
    """
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import stats as stats_mod
    from scripts.orchestra.stats import (
        P100_BUCKET_ID,
        P200_BUCKET_ID,
        SESSION_P200_THRESHOLD,
    )

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_first_pass
    label: first pass
    match:
      backend_in: ["openclaw"]
      model_in: ["test-model"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")

    runs_root = tmp_path
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    task_key = ("openclaw", "test-model", "101_test_suite", "task_demo")

    # session_attempts at SESSION_P200_THRESHOLD → P200, even though
    # done_history is empty on disk.
    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={task_key: SESSION_P200_THRESHOLD},
    )
    by_id = {b["priority_id"]: b for b in buckets}
    assert len(by_id["P1_first_pass"]["tasks"]) == 0
    assert len(by_id[P100_BUCKET_ID]["tasks"]) == 0
    assert len(by_id[P200_BUCKET_ID]["tasks"]) == 1
    assert by_id[P200_BUCKET_ID]["tasks"][0]["task"] == "task_demo"
    assert by_id[P200_BUCKET_ID]["tasks"][0]["attempts"] == SESSION_P200_THRESHOLD


def test_recompute_priorities_session_p200_takes_precedence_over_p100(tmp_path: Path) -> None:
    """When ``session_attempts >= SESSION_P200_THRESHOLD`` (which is
    also >= GLOBAL_MAX_ATTEMPTS), the task lands in P200, not P100 —
    the P200 check fires before P100 in the routing chain.
    """
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import stats as stats_mod
    from scripts.orchestra.stats import (
        P100_BUCKET_ID,
        P200_BUCKET_ID,
        SESSION_P200_THRESHOLD,
    )

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_first_pass
    label: first pass
    match:
      backend_in: ["openclaw"]
      model_in: ["test-model"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")

    runs_root = tmp_path
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    task_key = ("openclaw", "test-model", "101_test_suite", "task_demo")

    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={task_key: SESSION_P200_THRESHOLD + 2},
    )
    by_id = {b["priority_id"]: b for b in buckets}
    assert len(by_id[P100_BUCKET_ID]["tasks"]) == 0, (
        "P200 must outrank P100 when session crosses the higher threshold"
    )
    assert len(by_id[P200_BUCKET_ID]["tasks"]) == 1


def test_dispatch_state_can_start_gates_session_attempts(tmp_path: Path) -> None:
    """Round 12 bugfix: ``DispatchState.can_start`` must refuse a task
    whose session_attempts has hit GLOBAL_MAX_ATTEMPTS for any task NOT
    tagged with priority_id=P100/P200.  Without this gate the stale
    flat_tasks cache (between recomputes) keeps re-dispatching the same
    failing task dozens of times before the next recompute can route it
    to P100.
    """
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import dispatch as dispatch_mod
    from scripts.orchestra.stats import (
        GLOBAL_MAX_ATTEMPTS,
        P100_BUCKET_ID,
        P200_BUCKET_ID,
    )

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 8
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1
    label: p1
    match:
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    state = dispatch_mod.DispatchState(
        cfg=cfg,
        workers=[dispatch_mod.WorkerState(cfg=cfg.workers[0])],
    )
    worker = state.workers[0]

    task = {
        "backend": "openclaw",
        "model_dir": "m1",
        "suite": "101",
        "task": "t1",
        "priority_id": "P1",
    }
    # session=0 → can dispatch
    assert state.can_start(task, worker) is True

    # Simulate dispatcher reserve() bumps that hit the cap
    state.session_attempts[("openclaw", "m1", "101", "t1")] = GLOBAL_MAX_ATTEMPTS
    assert state.can_start(task, worker) is False, (
        "User-bucket task at the cap must NOT be re-dispatched until "
        "recompute routes it to P100"
    )

    # P100-tagged task (graveyard pass) bypasses the gate — graveyard
    # dispatches are allowed even at the cap.
    p100_task = {**task, "priority_id": P100_BUCKET_ID}
    assert state.can_start(p100_task, worker) is True

    # P200-tagged task (suspended) is NEVER dispatched, regardless of
    # the cap state.
    p200_task = {**task, "priority_id": P200_BUCKET_ID}
    assert state.can_start(p200_task, worker) is False, (
        "P200 suspended tasks must never dispatch (holding pen, not slow lane)"
    )


def test_ssh_worker_image_name_uses_hyphens(dispatch_src: str) -> None:
    """Round 12 follow-up: the dispatcher generates docker image names
    from the task's ``backend`` key.  Backend keys use underscores
    (``openclaw_edict``) but Docker image names use hyphens
    (``clawbench-openclaw-edict``).  Without ``.replace('_', '-')`` the
    edict worker hits ``pull access denied for clawbench-openclaw_edict``
    on every dispatch and run_eval crashes before doing any work.

    Round 11 + Round 12 (pre-fix) silently misclassified all 20 edict
    runs as status=running rc=1 zombies, which Round 12's lifetime
    counter then routed to P200 (18 false positives out of 26 P200
    tasks).
    """
    # Just grep the source — we don't need to spawn a real SSH process.
    assert "task['backend'].replace('_', '-')" in dispatch_src or \
           'task["backend"].replace(\'_\', \'-\')' in dispatch_src, (
        "dispatch.py must map backend underscores → hyphens when auto-"
        "generating the docker image name, otherwise edict tasks fail "
        "with 'pull access denied'."
    )


def test_recompute_priorities_running_in_inflight_is_not_orphan(tmp_path: Path) -> None:
    """The orphan-running rule must NOT touch tasks that are legitimately
    inflight — those are still being worked by a dispatcher SSH worker
    and the ``running`` summary is the live heartbeat, not stale."""
    import json
    import time
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra import stats as stats_mod

    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text("""
controller:
  host: controller
  data_root: """ + str(tmp_path) + """
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_first_pass
    label: first pass
    match:
      backend_in: ["openclaw"]
      model_in: ["test-model"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(cfg_path)

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")

    runs_root = tmp_path
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)

    task_dir = runs_root / "openclaw" / "test-model" / "101_test_suite" / "task_demo"
    task_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text(
        json.dumps({"finalStatus": "running"}),
        encoding="utf-8",
    )

    # And an inflight.jsonl entry: this task IS legitimately running.
    (runtime_dir / "inflight.jsonl").write_text(
        json.dumps({
            "backend": "openclaw",
            "model_dir": "test-model",
            "suite": "101_test_suite",
            "task": "task_demo",
            "worker": "w1",
            "ts_start": time.time(),
        }) + "\n",
        encoding="utf-8",
    )

    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={},
    )
    # Inflight tasks are excluded from buckets entirely (regardless of
    # status).  P1 must be empty.
    assert len(buckets[0]["tasks"]) == 0, (
        "task with active inflight entry must not appear in any bucket "
        "(it's being worked on)"
    )
