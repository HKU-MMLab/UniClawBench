from __future__ import annotations

import subprocess
from pathlib import Path

from lib.runner import (
    build_runtime_task_spec,
    detect_retryable_container_boot_error,
    detect_retryable_container_runtime_error,
)


ROOT = Path(__file__).resolve().parents[2]


def test_detect_retryable_container_boot_error_matches_browser_bootstrap_failure() -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    error = detect_retryable_container_boot_error(
        task,
        TimeoutError("openclaw browser service did not become ready: Failed to start Chrome CDP on port 18800"),
    )
    assert error is not None
    assert error["type"] == "browser_bootstrap_failed"


def test_detect_retryable_container_runtime_error_matches_turn_one_browser_failure(tmp_path) -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    out_dir = tmp_path / "attempt"
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    (out_dir / "logs/agent.log").write_text(
        "Error: Failed to start Chrome CDP on port 18800 for profile \"openclaw\"\n",
        encoding="utf-8",
    )
    error = detect_retryable_container_runtime_error(
        task,
        turn=1,
        agent_result=subprocess.CompletedProcess(args=["openclaw"], returncode=1, stdout="", stderr=""),
        out_dir=out_dir,
        transcript_text="",
        score={"verdict": "fail"},
    )
    assert error is not None
    assert error["type"] == "browser_runtime_failed"


def test_detect_retryable_container_runtime_error_skips_when_flow_already_continuable(tmp_path) -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    out_dir = tmp_path / "attempt"
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    (out_dir / "logs/agent.log").write_text("tab not found\n", encoding="utf-8")
    error = detect_retryable_container_runtime_error(
        task,
        turn=1,
        agent_result=subprocess.CompletedProcess(args=["openclaw"], returncode=1, stdout="", stderr=""),
        out_dir=out_dir,
        transcript_text="",
        score={"verdict": "continue"},
    )
    assert error is None


def test_detect_retryable_container_runtime_error_ignores_startup_string_from_transcript(tmp_path) -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    out_dir = tmp_path / "attempt"
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    (out_dir / "logs/agent.log").write_text("", encoding="utf-8")
    transcript_text = (
        "ps output: python3 - <<'PY' ... "
        "log.write(\"[clawbench-monitor] agent produced no observable progress within startup silence timeout; terminating\\n\")\n"
        "[clawbench-monitor] agent produced no observable progress within startup silence timeout; terminating\n"
    )
    error = detect_retryable_container_runtime_error(
        task,
        turn=1,
        agent_result=subprocess.CompletedProcess(args=["openclaw"], returncode=0, stdout="", stderr=""),
        out_dir=out_dir,
        transcript_text=transcript_text,
        score={"verdict": "fail"},
    )
    assert error is None


def test_detect_retryable_container_runtime_error_matches_real_startup_monitor_line(tmp_path) -> None:
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    out_dir = tmp_path / "attempt"
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    (out_dir / "logs/agent.log").write_text(
        "[clawbench-monitor] agent produced no observable progress within startup silence timeout; terminating\n",
        encoding="utf-8",
    )
    error = detect_retryable_container_runtime_error(
        task,
        turn=1,
        agent_result=subprocess.CompletedProcess(args=["openclaw"], returncode=245, stdout="", stderr=""),
        out_dir=out_dir,
        transcript_text="",
        score={"verdict": "fail"},
    )
    assert error is not None
    assert error["type"] == "agent_startup_stalled"
