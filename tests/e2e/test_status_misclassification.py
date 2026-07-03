"""Regression test for the worker_runner status-classification bug.

Smoke run #2 surfaced this: when run_eval exited with rc=1 and never
managed to write summary.json, worker_runner reported
``status=no_attempt_dir`` even though run_eval HAD created a p<n>-*
directory containing partial artefacts.  The dispatcher then logged a
misleading status string and refresh_summary couldn't classify the
attempt because the synth fallback hadn't yet been written.

Phase 1 (commit 482bc84a) and Phase 3 (f559ffef) together fixed it:
worker_runner now reports ``no_summary`` when an attempt dir exists
but lacks a per-attempt summary.json, falling back to
``FAIL_rc=<N>`` when run_eval also exited non-zero.

These tests pin that behaviour by driving ``worker_runner.main()``
with a mocked ``_run_one`` so the real run_eval / docker / rsync paths
are never exercised.
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

import scripts.orchestra.worker_runner as wr


# ── fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A minimal Clawbench-shaped repo: tasks/<suite>/<task>.yaml +
    runs/ root.  worker_runner builds run_eval's argv assuming this
    layout exists."""
    repo = tmp_path / "repo"
    (repo / "tasks" / "101_a").mkdir(parents=True)
    (repo / "tasks" / "101_a" / "task_001.yaml").write_text("task_id: task_001\n", encoding="utf-8")
    (repo / "runs").mkdir()
    return repo


@pytest.fixture
def captured_done(tmp_path: Path) -> Path:
    """A file the test pretends is controller's runtime/done.jsonl —
    monkeypatched ``_report_done`` appends payload here instead of
    SSHing to controller."""
    p = tmp_path / "done.jsonl"
    p.touch()
    return p


def _patch_externals(monkeypatch: pytest.MonkeyPatch, captured_done: Path) -> None:
    """Replace SSH / rsync side effects so the test stays local."""

    def _fake_rsync(attempt_dir: Path, controller_ssh: str, controller_runs_dir: Path, key: dict, lightweight: bool = False) -> tuple[bool, str]:
        return True, "ok"  # pretend rsync succeeded

    def _fake_report_done(controller_ssh: str, done_path: Path, payload: dict) -> None:
        with captured_done.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

    monkeypatch.setattr(wr, "_rsync_to_controller", _fake_rsync)
    monkeypatch.setattr(wr, "_report_done", _fake_report_done)


def _run_main(monkeypatch: pytest.MonkeyPatch, fake_repo: Path, captured_done: Path) -> int:
    argv = [
        "worker_runner",
        "--repo", str(fake_repo),
        "--backend", "openclaw",
        "--model-dir", "fake_a-model-1-0",
        "--model-full", "fake_a/model-1.0",
        "--suite", "101_a",
        "--task", "task_001",
        "--image", "clawbench-openclaw:latest",
        "--controller-ssh", "controller",
        "--controller-runs-dir", str(fake_repo / "runs"),
        "--controller-done-path", str(captured_done),
        "--host-tag", "testhost",
        "--supervisor-provider", "fake",
        "--supervisor-model", "m",
        "--user-simulator-provider", "fake",
        "--user-simulator-model", "m",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    return wr.main()


def _read_payload(captured_done: Path) -> dict:
    lines = [l for l in captured_done.read_text().splitlines() if l.strip()]
    assert len(lines) == 1, f"expected exactly one done-payload, got {len(lines)}"
    return json.loads(lines[0])


# ── tests ──────────────────────────────────────────────────────────────


def test_rc_zero_with_summary_reports_finalStatus(
    monkeypatch: pytest.MonkeyPatch, fake_repo: Path, captured_done: Path
) -> None:
    """Happy path: run_eval succeeded, summary.json got written →
    worker reports the summary's finalStatus."""

    def _fake_run(*, repo, task_yaml, image, backend, model_full,
                  supervisor_provider, supervisor_model,
                  user_simulator_provider, user_simulator_model,
                  timeout_sec, extra_env):
        # Simulate run_eval creating a stage dir + per-task summary
        task_dir = repo / "runs" / "openclaw" / "fake_a-model-1-0" / "101_a" / "task_001"
        p_dir = task_dir / f"p1-testhost-{uuid.uuid4().hex[:6]}"
        p_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "summary.json").write_text(
            json.dumps({"finalStatus": "pass", "passed": True}),
            encoding="utf-8",
        )
        return 0, "", ""

    monkeypatch.setattr(wr, "_run_one", _fake_run)
    _patch_externals(monkeypatch, captured_done)
    assert _run_main(monkeypatch, fake_repo, captured_done) == 0

    payload = _read_payload(captured_done)
    assert payload["rc"] == 0
    assert payload["status"] == "pass"


def test_rc_nonzero_no_summary_reports_executor_incomplete(
    monkeypatch: pytest.MonkeyPatch, fake_repo: Path, captured_done: Path
) -> None:
    """Round-6: run_eval exited with rc=1 before writing summary.json.
    Worker created an attempt dir for stdout/stderr capture but no
    summary.json.  worker_runner used to write the operations-layer
    string ``FAIL_rc=1`` straight into the DONE payload; Phase 2
    normalises that to the canonical ``executor_incomplete``
    (FINAL_STATUS_ORDER member) before reporting."""

    def _fake_run(*, repo, task_yaml, image, backend, model_full,
                  supervisor_provider, supervisor_model,
                  user_simulator_provider, user_simulator_model,
                  timeout_sec, extra_env):
        task_dir = repo / "runs" / "openclaw" / "fake_a-model-1-0" / "101_a" / "task_001"
        p_dir = task_dir / f"p1-testhost-{uuid.uuid4().hex[:6]}"
        p_dir.mkdir(parents=True, exist_ok=True)
        # NO summary.json written
        return 1, "stdout-fragment", "ImportError: oops"

    monkeypatch.setattr(wr, "_run_one", _fake_run)
    _patch_externals(monkeypatch, captured_done)
    assert _run_main(monkeypatch, fake_repo, captured_done) == 0

    payload = _read_payload(captured_done)
    assert payload["rc"] == 1
    assert payload["status"] == "executor_incomplete", payload["status"]
    # The status must never contain the buggy pre-fix or operations-layer values
    assert payload["status"] != "no_attempt_dir"
    assert payload["status"] != "FAIL_rc=1"
    assert payload["status"] != "no_summary"


def test_rc_nonzero_no_attempt_dir_manufactures_one(
    monkeypatch: pytest.MonkeyPatch, fake_repo: Path, captured_done: Path
) -> None:
    """When run_eval dies before any stage_dir exists, worker manufactures
    a p1-* directory so stdout/stderr still travel back to controller."""

    written: dict = {}

    def _fake_run(*, repo, task_yaml, image, backend, model_full,
                  supervisor_provider, supervisor_model,
                  user_simulator_provider, user_simulator_model,
                  timeout_sec, extra_env):
        return 2, "", "container failed to boot"

    def _fake_rsync_capture(attempt_dir, controller_ssh, controller_runs_dir, key, lightweight=False):
        written["attempt_dir"] = attempt_dir
        # Don't delete the dir even after this call so the test can inspect it.
        return False, "rsync_failed_test"  # pretend rsync failed → worker keeps the dir locally

    monkeypatch.setattr(wr, "_run_one", _fake_run)
    monkeypatch.setattr(wr, "_rsync_to_controller", _fake_rsync_capture)

    def _fake_report_done(controller_ssh, done_path, payload):
        with captured_done.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

    monkeypatch.setattr(wr, "_report_done", _fake_report_done)
    assert _run_main(monkeypatch, fake_repo, captured_done) == 0

    payload = _read_payload(captured_done)
    assert payload["rc"] == 2
    # A manufactured attempt dir gets a sentinel file
    attempt_dir = Path(payload["attempt_dir"])
    assert attempt_dir.exists()
    assert (attempt_dir / "WORKER_RUNNER_NO_ATTEMPT_DIR").exists()
    # And the captured stderr is on disk for post-mortem
    stderr_log = attempt_dir / "worker_runner_stderr.log"
    assert stderr_log.exists()
    assert "container failed to boot" in stderr_log.read_text()


def test_summary_copied_into_attempt_before_rsync(
    monkeypatch: pytest.MonkeyPatch, fake_repo: Path, captured_done: Path
) -> None:
    """Phase 3 fix: worker copies task-level summary.json into the
    attempt dir so refresh_summary on controller can rebuild the rolled-up
    view from p*-* siblings even when run_eval wrote only at the
    task level."""

    captured_attempt: dict[str, Path] = {}

    def _fake_run(*, repo, task_yaml, image, backend, model_full,
                  supervisor_provider, supervisor_model,
                  user_simulator_provider, user_simulator_model,
                  timeout_sec, extra_env):
        task_dir = repo / "runs" / "openclaw" / "fake_a-model-1-0" / "101_a" / "task_001"
        p_dir = task_dir / f"p1-testhost-{uuid.uuid4().hex[:6]}"
        p_dir.mkdir(parents=True, exist_ok=True)
        # Only the task-level summary exists.
        (task_dir / "summary.json").write_text(
            json.dumps({"finalStatus": "fail", "passed": False}),
            encoding="utf-8",
        )
        return 0, "", ""

    def _fake_rsync(attempt_dir, controller_ssh, controller_runs_dir, key, lightweight=False):
        captured_attempt["dir"] = attempt_dir
        return False, "rsync_failed_test"  # keep the dir on disk so we can inspect

    monkeypatch.setattr(wr, "_run_one", _fake_run)
    monkeypatch.setattr(wr, "_rsync_to_controller", _fake_rsync)
    monkeypatch.setattr(
        wr,
        "_report_done",
        lambda *a, **k: captured_done.write_text(json.dumps(k.get("payload") or a[-1]) + "\n"),
    )

    _run_main(monkeypatch, fake_repo, captured_done)
    attempt_dir = captured_attempt["dir"]
    assert (attempt_dir / "summary.json").exists()
    data = json.loads((attempt_dir / "summary.json").read_text())
    assert data["finalStatus"] == "fail"


# ── Phase 4.5 bug fixes — status synthesis priorities ────────────────


def test_verdict_continue_with_exhausted_budget_is_budget_exhausted(tmp_path: Path) -> None:
    """Bug 1 regression: when supervisor's last verdict is ``continue`` AND
    the score.json carries ``followup_budget_exhausted: true``, the synth
    path must classify the attempt as ``budget_exhausted`` (a legitimate
    terminal state), NOT ``executor_incomplete``.

    Prior to the fix, refresh_summary's _derive_status_from_artifacts
    mass-mislabelled 1304/1611 production attempts as executor_incomplete
    because it ignored the followup_budget_exhausted flag.  Real path-A
    runs (orchestration.py:476) classify the same state as
    ``budget_exhausted`` via ``stop_reason == "followup-limit-reached"``.
    """
    p = tmp_path / "p1-test"
    p.mkdir()
    (p / "score.json").write_text(
        json.dumps({
            "verdict": "continue",
            "capped_score": 0.78,
            "followup_budget_exhausted": True,
            "followups_used": 2,
            "remaining_followups": 0,
        }),
        encoding="utf-8",
    )
    (p / "meta.json").write_text(
        json.dumps({
            "everExecutorCompleted": True,
            "agentExitCode": 0,
            "executorCompletionReason": "api-stop-stop",
        }),
        encoding="utf-8",
    )
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts

    out = _derive_status_from_artifacts(p)
    assert out is not None
    assert out["finalStatus"] == "budget_exhausted", out


def test_verdict_continue_without_exhausted_budget_is_executor_incomplete(tmp_path: Path) -> None:
    """Negative-direction pin for bug 1: when supervisor said continue but
    no followup_budget_exhausted flag is set, the run really was
    interrupted mid-flight.  Must still classify as
    ``executor_incomplete``."""
    p = tmp_path / "p1-test"
    p.mkdir()
    (p / "score.json").write_text(
        json.dumps({
            "verdict": "continue",
            "capped_score": 0.78,
            # NO followup_budget_exhausted field — runner stopped for some
            # other reason (operator pkill, container crash mid-turn, ...).
        }),
        encoding="utf-8",
    )
    (p / "meta.json").write_text(
        json.dumps({
            "everExecutorCompleted": True,
            "agentExitCode": 0,
        }),
        encoding="utf-8",
    )
    from scripts.orchestra.refresh_summary import _derive_status_from_artifacts

    out = _derive_status_from_artifacts(p)
    assert out is not None
    assert out["finalStatus"] == "executor_incomplete", out


def test_status_priority_executor_incomplete_beats_rate_limit() -> None:
    """Bug 2 regression (Round-6 single-source variant): ``executor_incomplete``
    must rank above ``rate_limit`` — when a task has both an
    executor_incomplete attempt (agent tried, supervisor saw
    something) and a rate_limit attempt (upstream API refused, zero
    progress), the executor_incomplete attempt should be selected as
    the task's representative.  Round-6 moved the ranking table from
    refresh_summary.STATUS_PRIORITY into lib.status.FINAL_STATUS_ORDER
    / status_rank — this test now pins that single source of truth."""
    from lib.status import status_rank

    assert status_rank("executor_incomplete") > status_rank("rate_limit"), (
        "executor_incomplete must rank above rate_limit"
    )
    # The documented top-down ordering for terminal vs interrupted vs
    # zero-progress states must hold end-to-end:
    expected_order = [
        "pass",
        "budget_exhausted",
        "fail",
        "global_timeout",
        "executor_incomplete",
        "rate_limit",
        "infra_error",
    ]
    for higher, lower in zip(expected_order, expected_order[1:]):
        assert status_rank(higher) > status_rank(lower), (
            f"status_rank({higher!r}) must be > status_rank({lower!r})"
        )
