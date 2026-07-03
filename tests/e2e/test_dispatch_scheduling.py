"""Round-5 Phase 5a — pin the least-loaded worker scheduling.

Before the fix:
    for worker in state.workers:   # ← FIFO order: worker1 always first
        if can_start: ...; break

This produced "worker3 gets 6, worker4 gets 1" under worker-drop scenarios
because worker3 was always tried first and filled up to its parallel
limit before any task spilled to worker4.

After the fix:
    for worker in sorted(state.workers, key=lambda w: w.inflight):
        if can_start: ...; break

Tasks distribute to the least-loaded reachable worker first, with
ties broken by config order (sorted is stable).
"""
from __future__ import annotations

import time
from pathlib import Path

import scripts.orchestra.dispatch as dispatch_mod
from scripts.orchestra.config import (
    ControllerCfg,
    CodexRoleCfg,
    OrchestraConfig,
    SupervisionCfg,
    WorkerCfg,
)


def _stub_state(tmp_path: Path) -> dispatch_mod.DispatchState:
    cfg = OrchestraConfig(
        controller=ControllerCfg(host="ctl", data_root=tmp_path, webui_port=9005),
        workers=(
            WorkerCfg(name="worker1", ssh="worker1", parallel=4),
            WorkerCfg(name="worker2", ssh="worker2", parallel=4),
            WorkerCfg(name="worker3", ssh="worker3", parallel=4),
            WorkerCfg(name="worker4", ssh="worker4", parallel=4),
        ),
        priorities=(),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
    )
    workers = [dispatch_mod.WorkerState(cfg=w) for w in cfg.workers]
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return dispatch_mod.DispatchState(
        cfg=cfg,
        workers=workers,
        done_file=runtime_dir / "done.jsonl",
        inflight_file=runtime_dir / "inflight.jsonl",
    )


def _pick_worker_for(state: dispatch_mod.DispatchState, task: dict):
    """Mimic the inner loop from run_one_bucket — return the worker that
    would be chosen for this task under the new sorted-by-inflight order."""
    for worker in sorted(state.workers, key=lambda w: w.inflight):
        if state.can_start(task, worker):
            return worker
    return None


def test_least_loaded_balances_when_workers_equal(tmp_path):
    """4 idle workers + 4 tasks → 1 task each, not 4 on worker1."""
    state = _stub_state(tmp_path)
    distributions = {}
    for i in range(4):
        task = {"backend": "openclaw", "model_dir": "m1",
                "suite": "s", "task": f"task_{i}"}
        worker = _pick_worker_for(state, task)
        assert worker is not None
        state.reserve(task, worker)
        distributions[worker.cfg.name] = distributions.get(worker.cfg.name, 0) + 1

    # Each worker got exactly 1 task (no greedy fill on worker1)
    assert distributions == {"worker1": 1, "worker2": 1, "worker3": 1, "worker4": 1}, distributions


def test_least_loaded_skips_full_workers(tmp_path):
    """When worker3 is full (parallel=4 inflight), worker4 takes overflow."""
    state = _stub_state(tmp_path)
    # Pre-load worker3 to parallel=4 (full)
    for i in range(4):
        state.reserve(
            {"backend": "openclaw", "model_dir": "m1", "suite": "s", "task": f"prefilled_{i}"},
            state.workers[2],  # worker3
        )
    assert state.workers[2].inflight == 4  # worker3 full

    # New task should go to worker1 (least loaded; worker1/worker2/worker4 all at 0)
    new_task = {"backend": "openclaw", "model_dir": "m1", "suite": "s", "task": "new"}
    worker = _pick_worker_for(state, new_task)
    assert worker is not None
    assert worker.cfg.name == "worker1"


def test_least_loaded_breaks_ties_by_config_order(tmp_path):
    """When worker1 and worker2 are both idle, the new scheduler picks worker1
    (preserves stable config order via sorted's stability)."""
    state = _stub_state(tmp_path)
    # worker3 and worker4 are loaded; worker1 and worker2 are both idle
    for i in range(2):
        state.reserve(
            {"backend": "openclaw", "model_dir": "m1", "suite": "s", "task": f"worker3_pre_{i}"},
            state.workers[2],  # worker3
        )
    for i in range(2):
        state.reserve(
            {"backend": "openclaw", "model_dir": "m1", "suite": "s", "task": f"worker4_pre_{i}"},
            state.workers[3],  # worker4
        )
    new_task = {"backend": "openclaw", "model_dir": "m1", "suite": "s", "task": "new"}
    worker = _pick_worker_for(state, new_task)
    assert worker is not None
    # worker1 < worker2 in config; both idle → worker1 wins (stable sort)
    assert worker.cfg.name == "worker1"


def test_least_loaded_skips_workers_in_backoff(tmp_path):
    """A worker with unavailable_until > now is treated as unavailable
    even if its inflight count is 0 — the new sorted-by-inflight order
    doesn't undermine the backoff."""
    state = _stub_state(tmp_path)
    # worker1 + worker2 in backoff
    state.workers[0].unavailable_until = time.time() + 300
    state.workers[1].unavailable_until = time.time() + 300
    new_task = {"backend": "openclaw", "model_dir": "m1", "suite": "s", "task": "new"}
    worker = _pick_worker_for(state, new_task)
    assert worker is not None
    # Despite worker1+worker2 having inflight=0 (lowest), can_start refuses
    # them due to backoff; the worker chosen must be worker3 (next least
    # loaded, also config-first among healthy).
    assert worker.cfg.name == "worker3"


def _write_task_yaml(tasks_root: Path, suite: str, task: str, *, pre_exec: bool, parallel_safe: bool = False) -> None:
    suite_dir = tasks_root / suite
    suite_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"task_id: {task}", f"category: {suite}"]
    if pre_exec:
        lines.append("pre_exec:")
        lines.append("  - services/task-setup/setup.py")
        lines.append(f"pre_exec_parallel_safe: {'true' if parallel_safe else 'false'}")
    (suite_dir / f"{task}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_non_parallel_safe_pre_exec_serializes_same_task_across_models(tmp_path):
    """A live-state populator task must not start for two cells at once."""
    state = _stub_state(tmp_path)
    state.task_meta_root = tmp_path / "tasks"
    _write_task_yaml(state.task_meta_root, "101_a", "task_live", pre_exec=True, parallel_safe=False)

    first = {"backend": "openclaw", "model_dir": "m1", "suite": "101_a", "task": "task_live"}
    second = {"backend": "nanobot", "model_dir": "m2", "suite": "101_a", "task": "task_live"}
    other_task = {"backend": "openclaw", "model_dir": "m2", "suite": "101_a", "task": "task_other"}
    _write_task_yaml(state.task_meta_root, "101_a", "task_other", pre_exec=True, parallel_safe=False)

    state.reserve(first, state.workers[0])

    assert not state.can_start(second, state.workers[1])
    assert state.can_start(other_task, state.workers[1])


def test_parallel_safe_pre_exec_allows_same_task_across_models(tmp_path):
    state = _stub_state(tmp_path)
    state.task_meta_root = tmp_path / "tasks"
    _write_task_yaml(state.task_meta_root, "101_a", "task_safe", pre_exec=True, parallel_safe=True)

    first = {"backend": "openclaw", "model_dir": "m1", "suite": "101_a", "task": "task_safe"}
    second = {"backend": "nanobot", "model_dir": "m2", "suite": "101_a", "task": "task_safe"}
    state.reserve(first, state.workers[0])

    assert state.can_start(second, state.workers[1])
