"""Round 16 / P0-1: P200 is now a dispatcher-session counter, not a
persistent done_history counter.

The intent of the change is that a fresh ``DispatchState`` after a
restart sees an empty ``session_attempts`` dict, so any task previously
parked in P200 is naturally re-routed to its normal user bucket on
the next ``recompute_priorities`` pass.  No operator action (no
``release_p200``, no rotation of ``done_history``) is required.

This file covers the two end-to-end shapes of that contract:

1. ``DispatchState`` lifecycle: bumping ``session_attempts`` past
   ``SESSION_P200_THRESHOLD`` and then constructing a brand-new
   ``DispatchState`` (the "restart" simulation) wipes the counter.

2. ``recompute_priorities`` correctly re-routes a task between P200 and
   P1 as the in-memory counter crosses / no longer crosses the
   threshold — even when ``runtime/done_history`` is non-empty (i.e.
   legacy lifetime accounting is decoupled from live routing).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestra import config as cfg_mod
from scripts.orchestra import dispatch as dispatch_mod
from scripts.orchestra import stats as stats_mod
from scripts.orchestra.stats import (
    GLOBAL_MAX_ATTEMPTS,
    P100_BUCKET_ID,
    P200_BUCKET_ID,
    SESSION_P200_THRESHOLD,
)


def _write_cfg(tmp_path: Path) -> cfg_mod.OrchestraConfig:
    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text(
        "controller:\n"
        "  host: controller\n"
        f"  data_root: {tmp_path}\n"
        "  webui_port: 9999\n"
        "workers:\n"
        "  - name: w1\n"
        "    ssh: w1\n"
        "    parallel: 1\n"
        "supervision:\n"
        "  supervisor:\n"
        "    provider: provider-a\n"
        "    model: model-a\n"
        "  user_simulator:\n"
        "    provider: provider-a\n"
        "    model: model-a\n"
        "priorities:\n"
        "  - id: P1_first_pass\n"
        "    label: first pass\n"
        "    match:\n"
        "      backend_in: [\"openclaw\"]\n"
        "      model_in: [\"test-model\"]\n"
        "      status_in: [\"missing\"]\n",
        encoding="utf-8",
    )
    return cfg_mod.load(cfg_path)


def _seed_task(tasks_root: Path) -> None:
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")


def _seed_done_history(runtime_dir: Path, key: tuple[str, str, str, str], n: int) -> None:
    archive_dir = runtime_dir / "done_history"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "done_seed.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "backend": key[0],
                    "model_dir": key[1],
                    "suite": key[2],
                    "task": key[3],
                    "status": "rate_limit",
                }
            )
            for _ in range(n)
        )
        + "\n",
        encoding="utf-8",
    )


def test_dispatch_state_session_attempts_default_empty_on_restart(tmp_path: Path) -> None:
    """Fresh ``DispatchState`` instances always start with an empty
    ``session_attempts`` dict.  Building a new instance is exactly what
    a dispatcher restart looks like, so this is the contract that lets
    P100/P200 release without operator intervention."""
    cfg = _write_cfg(tmp_path)

    # Simulate a long-lived dispatcher that bumped a key past P200.
    state_a = dispatch_mod.DispatchState(
        cfg=cfg, workers=[dispatch_mod.WorkerState(cfg=cfg.workers[0])]
    )
    key = ("openclaw", "test-model", "101_test_suite", "task_demo")
    state_a.session_attempts[key] = SESSION_P200_THRESHOLD + 4
    assert state_a.session_attempts[key] >= SESSION_P200_THRESHOLD

    # Restart == new DispatchState.
    state_b = dispatch_mod.DispatchState(
        cfg=cfg, workers=[dispatch_mod.WorkerState(cfg=cfg.workers[0])]
    )
    assert state_b.session_attempts == {}, (
        "fresh DispatchState must have empty session_attempts; otherwise "
        "P100/P200 cannot self-release on restart"
    )


def test_session_p200_reroutes_to_user_bucket_after_restart(tmp_path: Path) -> None:
    """End-to-end: a task suspended in P200 (session counter past the
    threshold) is back in its user bucket after a simulated restart
    (recompute with empty session_attempts).  Done_history rows do NOT
    keep it suspended."""
    cfg = _write_cfg(tmp_path)
    _seed_task(tmp_path / "tasks")
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    key = ("openclaw", "test-model", "101_test_suite", "task_demo")

    # Legacy done_history rows on disk — must not affect routing.
    _seed_done_history(runtime_dir, key, 20)

    # Round 1: in-memory counter past SESSION_P200_THRESHOLD → P200.
    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tmp_path / "tasks",
        runs_root=tmp_path,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={key: SESSION_P200_THRESHOLD + 1},
    )
    by_id = {b["priority_id"]: b for b in buckets}
    assert len(by_id[P200_BUCKET_ID]["tasks"]) == 1
    assert by_id[P200_BUCKET_ID]["tasks"][0]["task"] == "task_demo"
    assert len(by_id["P1_first_pass"]["tasks"]) == 0

    # Round 2: simulate restart — empty session_attempts.  The
    # done_history rows on disk should NOT keep the task in P200.
    buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tmp_path / "tasks",
        runs_root=tmp_path,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts={},
    )
    by_id = {b["priority_id"]: b for b in buckets}
    assert len(by_id[P200_BUCKET_ID]["tasks"]) == 0, (
        "restart must release P200; done_history must not keep tasks suspended"
    )
    assert len(by_id[P100_BUCKET_ID]["tasks"]) == 0
    assert len(by_id["P1_first_pass"]["tasks"]) == 1
    assert by_id["P1_first_pass"]["tasks"][0]["task"] == "task_demo"


def test_session_p100_dispatcher_state_gate_still_refuses_user_bucket(tmp_path: Path) -> None:
    """The session_attempts gate on ``DispatchState.can_start`` still
    refuses a user-bucket task at GLOBAL_MAX_ATTEMPTS, and the new
    P200 threshold does NOT break that contract.  Sanity-check that
    SESSION_P200_THRESHOLD is strictly greater than
    GLOBAL_MAX_ATTEMPTS so P100 still has a meaningful in-between
    range."""
    assert SESSION_P200_THRESHOLD > GLOBAL_MAX_ATTEMPTS

    cfg = _write_cfg(tmp_path)
    state = dispatch_mod.DispatchState(
        cfg=cfg, workers=[dispatch_mod.WorkerState(cfg=cfg.workers[0])]
    )
    worker = state.workers[0]
    task = {
        "backend": "openclaw",
        "model_dir": "test-model",
        "suite": "101_test_suite",
        "task": "task_demo",
        "priority_id": "P1_first_pass",
    }
    key = (task["backend"], task["model_dir"], task["suite"], task["task"])

    # Below GLOBAL_MAX_ATTEMPTS → still dispatchable
    state.session_attempts[key] = GLOBAL_MAX_ATTEMPTS - 1
    assert state.can_start(task, worker) is True

    # At GLOBAL_MAX_ATTEMPTS but priority_id=P1 → gate refuses
    state.session_attempts[key] = GLOBAL_MAX_ATTEMPTS
    assert state.can_start(task, worker) is False

    # P100-tagged task at GLOBAL_MAX_ATTEMPTS → graveyard, still dispatchable
    p100_task = {**task, "priority_id": P100_BUCKET_ID}
    assert state.can_start(p100_task, worker) is True

    # P200-tagged task is never dispatchable regardless of counter value
    p200_task = {**task, "priority_id": P200_BUCKET_ID}
    state.session_attempts[key] = SESSION_P200_THRESHOLD
    assert state.can_start(p200_task, worker) is False
