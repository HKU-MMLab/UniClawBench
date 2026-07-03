"""Round 10 / P3: Path A (runtime) and Path B (refresh synth) parity.

Path A = ``lib.runner.orchestration.resolve_attempt_outcome`` — builds
finalStatus from an in-memory ``score`` dict during a live run.

Path B = ``scripts.orchestra.refresh_summary._derive_status_from_artifacts``
— rebuilds finalStatus from on-disk ``score.json`` + ``meta.json``
when the per-attempt summary.json is missing.

Both delegate to ``lib.status.classify_attempt_outcome``.  Pre-fix,
Path B passed ``passed_flag=bool(score.get("passed"))`` but Path A
omitted that kwarg, so for a hypothetical ``score={"passed": true}``
with no verdict the two paths returned different finalStatus values.

Runtime never writes bare ``passed=true`` without a verdict today, so
the gap was theoretical — but if any future caller does, both paths
should now agree.  This test pins that contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.runner.orchestration import resolve_attempt_outcome
from scripts.orchestra.refresh_summary import _derive_status_from_artifacts


def _make_task(threshold: float = 0.5):
    """Minimal TaskSpec.  resolve_attempt_outcome only consumes
    ``task.success_threshold`` for promotion + nothing else."""
    from types import SimpleNamespace

    return SimpleNamespace(success_threshold=threshold)


def _write_synth_inputs(tmp_path: Path, *, score: dict, meta: dict) -> Path:
    """Write ``score.json`` + ``meta.json`` into a tmp attempt dir so
    Path B can read them.  Returns the attempt dir."""
    p = tmp_path / "p1-abc123"
    p.mkdir()
    (p / "score.json").write_text(json.dumps(score), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return p


def _path_a_status(score: dict, threshold: float = 0.5) -> str:
    """Path A returns snake_case ``final_status``."""
    task = _make_task(threshold=threshold)
    return resolve_attempt_outcome(task, score)["final_status"]


def _path_b_status(tmp_path: Path, *, score: dict, meta: dict) -> str:
    """Path B returns camelCase ``finalStatus`` (matches summary.json schema)."""
    p = _write_synth_inputs(tmp_path, score=score, meta=meta)
    out = _derive_status_from_artifacts(p)
    assert out is not None
    return out["finalStatus"]


# --------------------------------------------------------------------------
# Parity matrix
# --------------------------------------------------------------------------


def test_parity_passed_true_no_verdict(tmp_path: Path) -> None:
    """The trigger case: ``score.passed=true`` with no verdict.  Pre-fix
    Path A returned ``executor_incomplete`` (priority-6 default),
    Path B returned ``pass`` (priority-3 via passed_flag).  Post-fix
    both return ``pass``."""
    score = {"passed": True, "overall_score": 1.0}
    meta = {"everExecutorCompleted": True}
    a = _path_a_status(score)
    b = _path_b_status(tmp_path, score=score, meta=meta)
    assert a == b == "pass", f"A={a}, B={b}"


def test_parity_verdict_pass(tmp_path: Path) -> None:
    """Verdict pass: both paths should agree — pass."""
    score = {"verdict": "pass", "overall_score": 0.95}
    meta = {"everExecutorCompleted": True, "agentExitCode": 0}
    a = _path_a_status(score)
    b = _path_b_status(tmp_path, score=score, meta=meta)
    assert a == b == "pass"


def test_parity_verdict_fail(tmp_path: Path) -> None:
    """Verdict fail with executor completion: both paths agree on fail."""
    score = {"verdict": "fail", "overall_score": 0.0}
    meta = {"everExecutorCompleted": True, "agentExitCode": 0}
    a = _path_a_status(score)
    b = _path_b_status(tmp_path, score=score, meta=meta)
    assert a == b == "fail"


def test_parity_completion_gate_failed_demotes_pass(tmp_path: Path) -> None:
    """gate failed beats a supervisor-claimed pass: both paths agree on fail."""
    score = {"verdict": "pass", "completion_gate_failed": True}
    meta = {"everExecutorCompleted": True, "agentExitCode": 0}
    a = _path_a_status(score)
    b = _path_b_status(tmp_path, score=score, meta=meta)
    assert a == b == "fail"


def test_parity_passed_flag_loses_to_completion_gate(tmp_path: Path) -> None:
    """If both ``passed=true`` and ``completion_gate_failed=true`` are
    set, completion_gate wins on both paths.  This pins the priority
    order between the two newly-aligned signals."""
    score = {"passed": True, "completion_gate_failed": True}
    meta = {"everExecutorCompleted": True}
    a = _path_a_status(score)
    b = _path_b_status(tmp_path, score=score, meta=meta)
    assert a == b == "fail"
