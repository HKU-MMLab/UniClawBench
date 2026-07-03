"""Cover the priority-bucketing logic that decides what dispatcher
should pick next.

We exercise both layers:

* ``PriorityCfg.matches()`` — the AND-of-non-empty-list semantics that
  declares whether a single task qualifies for a single bucket.
* ``recompute_priorities()`` — the top-down walk that produces the
  ordered queue the dispatcher consumes, including inflight exclusion
  and the wildcard-fallback bucket.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestra import stats as stats_mod
from scripts.orchestra.config import (
    ControllerCfg,
    OrchestraConfig,
    PriorityCfg,
    SupervisionCfg,
    CodexRoleCfg,
    WorkerCfg,
)


# ── PriorityCfg.matches() ────────────────────────────────────────────


def test_match_all_when_filters_empty() -> None:
    p = PriorityCfg(id="any", label="wildcard")
    assert p.matches("openclaw", "provider_primary-gpt-5-4", "101_a", "running") is True
    assert p.matches("nanobot", "fake_a-model.1", "201_a_zh", "infra_error") is True


def test_backend_filter_only() -> None:
    p = PriorityCfg(id="oc", label="oc-only", backend_in=("openclaw",))
    assert p.matches("openclaw", "anything", "101_a", "any") is True
    assert p.matches("nanobot", "anything", "101_a", "any") is False


def test_model_filter_only() -> None:
    p = PriorityCfg(id="sota", label="sota", model_in=("provider_primary-gpt-5-4",))
    assert p.matches("openclaw", "provider_primary-gpt-5-4", "101_a", "fail") is True
    assert p.matches("openclaw", "other-model", "101_a", "fail") is False


def test_status_filter_only() -> None:
    p = PriorityCfg(id="rate", label="rate", status_in=("rate_limit", "infra_error"))
    assert p.matches("openclaw", "x", "101_a", "rate_limit") is True
    assert p.matches("openclaw", "x", "101_a", "infra_error") is True
    assert p.matches("openclaw", "x", "101_a", "pass") is False


def test_suite_filter_only() -> None:
    # The locale axis: a bucket pinned to EN suites must reject ZH cells.
    p = PriorityCfg(id="en", label="en-only", suite_in=("101_a", "102_b"))
    assert p.matches("openclaw", "x", "101_a", "missing") is True
    assert p.matches("openclaw", "x", "102_b", "running") is True
    assert p.matches("openclaw", "x", "201_a_zh", "missing") is False


def test_all_four_filters_are_anded() -> None:
    p = PriorityCfg(
        id="strict",
        label="strict",
        backend_in=("nanobot",),
        model_in=("provider_primary-gpt-5-4",),
        suite_in=("201_a_zh",),
        status_in=("running",),
    )
    assert p.matches("nanobot", "provider_primary-gpt-5-4", "201_a_zh", "running") is True
    assert p.matches("openclaw", "provider_primary-gpt-5-4", "201_a_zh", "running") is False  # backend
    assert p.matches("nanobot", "other-model", "201_a_zh", "running") is False             # model
    assert p.matches("nanobot", "provider_primary-gpt-5-4", "101_a", "running") is False       # suite
    assert p.matches("nanobot", "provider_primary-gpt-5-4", "201_a_zh", "rate_limit") is False # status


# ── recompute_priorities() end-to-end (with mocked tree) ──────────────


def _make_cfg(runs_root: Path) -> OrchestraConfig:
    return OrchestraConfig(
        controller=ControllerCfg(
            host="controller",
            data_root=runs_root.parent,
            webui_port=9005,
        ),
        workers=(WorkerCfg(name="worker1", ssh="worker1", parallel=1, skip=False),),
        priorities=(
            PriorityCfg(
                id="T1_oc_running",
                label="openclaw running",
                backend_in=("openclaw",),
                status_in=("running",),
            ),
            PriorityCfg(
                id="T2_rate",
                label="any rate_limit",
                status_in=("rate_limit",),
            ),
            PriorityCfg(id="T3_wildcard", label="everything else"),
        ),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="fake", model="m"),
            user_simulator=CodexRoleCfg(provider="fake", model="m"),
        ),
        raw={},
    )


def _make_task_yaml(tasks_root: Path, suite: str, task_id: str) -> None:
    (tasks_root / suite).mkdir(parents=True, exist_ok=True)
    (tasks_root / suite / f"{task_id}.yaml").write_text("task_id: " + task_id + "\n", encoding="utf-8")


def _make_summary(runs_root: Path, backend: str, model_dir: str, suite: str, task_id: str, status: str) -> None:
    """Write a minimal task-level summary.json so _read_status returns
    the requested finalStatus."""
    task_dir = runs_root / backend / model_dir / suite / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "summary.json").write_text(
        json.dumps({"finalStatus": status, "attempts": [{"attempt": 1}]}),
        encoding="utf-8",
    )


def test_recompute_priorities_buckets_match_top_down(tmp_path: Path) -> None:
    """Round 12 / E2 changed orphan-running semantics: a summary stuck
    at ``running`` without an inflight row is promoted to ``missing``
    before bucket matching.  So a bucket targeting ``status_in=running``
    no longer captures orphan-running tasks — they fall through to
    whatever bucket matches ``missing`` (or the wildcard).
    """
    runs_root = tmp_path / "runs"
    tasks_root = tmp_path / "tasks"
    runtime_dir = tmp_path / "runtime"
    runs_root.mkdir()
    runtime_dir.mkdir()

    _make_task_yaml(tasks_root, "101_a", "task_001_x")
    _make_task_yaml(tasks_root, "101_a", "task_002_y")
    _make_task_yaml(tasks_root, "101_a", "task_003_z")

    # task_001 → orphan running on openclaw → promoted to missing by E2 → T3 (wildcard)
    _make_summary(runs_root, "openclaw", "provider_primary-gpt-5-4", "101_a", "task_001_x", "running")
    # task_002 → rate_limit on nanobot → T2
    _make_summary(runs_root, "nanobot", "provider_primary-gpt-5-4", "101_a", "task_002_y", "rate_limit")
    # task_003 → no summary → missing → T3 (wildcard)

    cfg = _make_cfg(runs_root)
    buckets = stats_mod.recompute_priorities(
        cfg, tasks_root=tasks_root, runs_root=runs_root, runtime_dir=runtime_dir, do_refresh=False
    )

    by_id = {b["priority_id"]: b for b in buckets}
    t1_keys = {(t["backend"], t["task"]) for t in by_id["T1_oc_running"]["tasks"]}
    t2_keys = {(t["backend"], t["task"]) for t in by_id["T2_rate"]["tasks"]}
    t3_keys = {(t["task"]) for t in by_id["T3_wildcard"]["tasks"]}

    # E2: orphan-running task is promoted to missing → does NOT land in
    # T1 (status_in=running) anymore; falls through to T3 (wildcard).
    assert ("openclaw", "task_001_x") not in t1_keys
    assert "task_001_x" in t3_keys
    # T2 (rate_limit) unaffected
    assert ("nanobot", "task_002_y") in t2_keys
    # task_003 has no summary → status=missing → wildcard
    assert "task_003_z" in t3_keys


def test_global_timeout_requires_explicit_retry_tier(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    tasks_root = tmp_path / "tasks"
    runtime_dir = tmp_path / "runtime"
    runs_root.mkdir()
    runtime_dir.mkdir()

    _make_task_yaml(tasks_root, "101_a", "task_001_x")
    _make_summary(
        runs_root,
        "openclaw",
        "provider_primary-gpt-5-4",
        "101_a",
        "task_001_x",
        "global_timeout",
    )

    wildcard_cfg = _make_cfg(runs_root)
    buckets = stats_mod.recompute_priorities(
        wildcard_cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
    )
    assert all(not bucket["tasks"] for bucket in buckets), (
        "global_timeout is terminal and must not fall into wildcard catch-all buckets"
    )

    explicit_cfg = OrchestraConfig(
        controller=wildcard_cfg.controller,
        workers=wildcard_cfg.workers,
        priorities=(
            PriorityCfg(id="T_timeout", label="explicit timeout retry", status_in=("global_timeout",)),
        ),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=wildcard_cfg.supervision,
        raw={},
    )
    buckets = stats_mod.recompute_priorities(
        explicit_cfg,
        tasks_root=tasks_root,
        runs_root=runs_root,
        runtime_dir=runtime_dir,
        do_refresh=False,
    )
    assert len(buckets[0]["tasks"]) == 1
    assert buckets[0]["tasks"][0]["status"] == "global_timeout"


def test_recompute_priorities_excludes_inflight(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    tasks_root = tmp_path / "tasks"
    runtime_dir = tmp_path / "runtime"
    runs_root.mkdir()
    runtime_dir.mkdir()

    _make_task_yaml(tasks_root, "101_a", "task_001_x")
    _make_summary(runs_root, "openclaw", "provider_primary-gpt-5-4", "101_a", "task_001_x", "running")

    # Mark the task as currently inflight on a worker
    (runtime_dir / "inflight.jsonl").write_text(
        json.dumps(
            {
                "backend": "openclaw",
                "model_dir": "provider_primary-gpt-5-4",
                "suite": "101_a",
                "task": "task_001_x",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    cfg = _make_cfg(runs_root)
    buckets = stats_mod.recompute_priorities(
        cfg, tasks_root=tasks_root, runs_root=runs_root, runtime_dir=runtime_dir, do_refresh=False
    )
    # Inflight task must not appear in any bucket
    for b in buckets:
        for t in b["tasks"]:
            assert not (
                t["backend"] == "openclaw"
                and t["model_dir"] == "provider_primary-gpt-5-4"
                and t["task"] == "task_001_x"
            )


def test_recompute_priorities_writes_jsonl(tmp_path: Path) -> None:
    """Round 12 / E1: recompute always appends the synthetic P100
    graveyard bucket after the user-defined ones.  priorities.jsonl
    snapshot includes it."""
    runs_root = tmp_path / "runs"
    tasks_root = tmp_path / "tasks"
    runtime_dir = tmp_path / "runtime"
    runs_root.mkdir()
    runtime_dir.mkdir()

    _make_task_yaml(tasks_root, "101_a", "task_001_x")

    cfg = _make_cfg(runs_root)
    stats_mod.recompute_priorities(
        cfg, tasks_root=tasks_root, runs_root=runs_root, runtime_dir=runtime_dir, do_refresh=False
    )
    prio_file = runtime_dir / "priorities.jsonl"
    assert prio_file.exists()
    lines = [json.loads(l) for l in prio_file.read_text().splitlines() if l.strip()]
    ids = [l["priority_id"] for l in lines]
    assert ids == [
        "T1_oc_running",
        "T2_rate",
        "T3_wildcard",
        "P100_session_exhausted",
        "P200_suspended",
    ]
