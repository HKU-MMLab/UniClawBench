"""Pin the top-level public JSON artifact schemas.

Every artefact the runner emits at the top level (``summary.json``,
``score.json``, ``meta.json``, ``session_meta.json``, ``batch_summary.json``)
must carry an explicit ``schema_version`` so third-party consumers can
branch on it. Bump the constant in ``lib.status`` only on a *breaking*
change to a previously-stable field; adding a new optional field is NOT
a bump.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from lib.runner.artifacts import write_score_json
from lib.runner.orchestration import (
    attempt_meta_base,
    build_bootstrap_infra_summary,
    task_summary_base,
)
from lib.status import (
    BATCH_SUMMARY_SCHEMA_VERSION,
    META_SCHEMA_VERSION,
    SCORE_SCHEMA_VERSION,
    SESSION_META_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
)
from lib.task import CodexSpec, TaskSpec


def _stub_task(tmp_path: Path) -> TaskSpec:
    return TaskSpec(
        task_id="t",
        category="cat",
        agent_sys="openclaw",
        agent_id="main",
        model="m",
        image_model="m",
        timeout_seconds=1200,
        max_total_seconds=1800,
        success_threshold=0.5,
        task="t",
        task_snapshot="",
        references=[],
        sources=[],
        skills=[],
        services=[],
        pre_exec=[],
        privacy=[],
        file_path=tmp_path / "task.yaml",
        injection_root=tmp_path / "inj",
        codex=CodexSpec(),
        pre_exec_parallel_safe=False,
    )


def test_schema_version_constants_are_v1_strings():
    """Initial release pins everything at v1.

    A bump to v2 (or anywhere else) must be a deliberate decision — this
    test exists so the bump cannot happen by accident as part of an
    unrelated refactor.
    """
    assert SUMMARY_SCHEMA_VERSION == "clawbench.summary/v1"
    assert SCORE_SCHEMA_VERSION == "clawbench.score/v1"
    assert META_SCHEMA_VERSION == "clawbench.meta/v1"
    assert SESSION_META_SCHEMA_VERSION == "clawbench.session_meta/v1"
    assert BATCH_SUMMARY_SCHEMA_VERSION == "clawbench.batch_summary/v1"


def test_attempt_meta_base_carries_schema_version(tmp_path):
    task = _stub_task(tmp_path)
    meta = attempt_meta_base(task, container_name="cb_test")
    assert meta["schema_version"] == META_SCHEMA_VERSION


def test_task_summary_base_carries_schema_version(tmp_path):
    task = _stub_task(tmp_path)
    summary = task_summary_base(task)
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION


def test_write_score_json_writes_schema_version(tmp_path):
    task = _stub_task(tmp_path)
    out_dir = tmp_path / "p1-test"
    out_dir.mkdir()
    write_score_json(out_dir, task, {"verdict": "pass", "capped_score": 0.9})

    import json

    payload = json.loads((out_dir / "score.json").read_text())
    assert payload["schema_version"] == SCORE_SCHEMA_VERSION
    # Original fields survive.
    assert payload["verdict"] == "pass"
    assert payload["capped_score"] == 0.9
    assert payload["success_threshold"] == pytest.approx(0.5)


def test_refresh_one_task_includes_schema_version(tmp_path):
    """``refresh_summary.refresh_one_task`` rebuilds the task-level
    summary.json from per-attempt ``p*-*`` siblings.  The rebuilt
    summary must carry ``schema_version`` so it stays consistent with
    the runtime-produced one (``task_summary_base``).  Without this,
    a refreshed summary lacks the version field and downstream
    consumers cannot branch on it."""
    import json

    from scripts.orchestra.refresh_summary import refresh_one_task

    task_dir = tmp_path / "task_001"
    p_dir = task_dir / "p1-host-aaa"
    p_dir.mkdir(parents=True)
    (p_dir / "summary.json").write_text(
        json.dumps({"finalStatus": "pass", "passed": True}),
        encoding="utf-8",
    )

    summary = refresh_one_task(task_dir)
    assert summary is not None
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION


def test_bootstrap_infra_summary_carries_schema_version(tmp_path, monkeypatch):
    """The bootstrap-failure code path also writes summary + session_meta;
    both must carry their schema versions."""
    # build_bootstrap_infra_summary writes to ``task_config.task_run_root(task)`` —
    # redirect that to a temp tree to avoid touching the repo.
    from lib.runner import task_config

    monkeypatch.setattr(task_config, "RUNS", tmp_path / "runs")

    task = _stub_task(tmp_path)
    summary = build_bootstrap_infra_summary(
        task,
        image="img",
        keep_container=False,
        error={"type": "container_bootstrap_failed", "message": "boom"},
    )
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION

    import json

    session_meta_path = tmp_path / "runs" / "openclaw" / "m" / "cat" / "t" / "session_meta.json"
    assert session_meta_path.exists()
    session_meta = json.loads(session_meta_path.read_text())
    assert session_meta["schema_version"] == SESSION_META_SCHEMA_VERSION
