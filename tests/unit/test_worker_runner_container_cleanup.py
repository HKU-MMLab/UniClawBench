"""Round 12 follow-up: ``worker_runner._wait_for_containers_gone``
must hold SSH return until any containers started by this task are
actually gone, so the dispatcher doesn't release the slot before the
container dies (the over-spawn cascade observed at parallel >=17 in
Round 12 probe2).

These tests pin the behavior contract:

  * Polls docker ps using the ``clawbench-<task_id>-`` prefix filter
  * Returns as soon as no matching containers exist
  * Force-removes stragglers after the timeout
  * No-op when docker is unavailable (test envs)
  * Best-effort: never raises
"""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest


def _make_proc(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["docker"], returncode=returncode, stdout=stdout, stderr=""
    )


def test_returns_immediately_when_no_containers_match(monkeypatch) -> None:
    """If ``docker ps -q --filter name=clawbench-task-...`` returns
    nothing on the first poll, the function exits in <100ms (no wait).
    """
    from scripts.orchestra import worker_runner as wr

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _make_proc(stdout="")  # no containers

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(wr, "subprocess", subprocess)

    wr._wait_for_containers_gone("task_demo")
    assert len(calls) == 1, "should exit after the first empty poll"
    assert "docker" in calls[0]
    assert "name=clawbench-task_demo-" in " ".join(calls[0])


def test_force_kills_after_timeout(monkeypatch) -> None:
    """Container persists past the timeout → ``docker rm -f`` fires
    with the stuck container IDs."""
    from scripts.orchestra import worker_runner as wr

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == "ps":
            return _make_proc(stdout="abc123\ndef456\n")  # 2 stuck
        return _make_proc(stdout="")  # docker rm -f succeeded

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(wr, "subprocess", subprocess)
    # Shrink the timeout so the test runs fast
    monkeypatch.setattr(wr, "_CONTAINER_DEATH_MAX_WAIT_SEC", 0.5)
    monkeypatch.setattr(wr, "_CONTAINER_DEATH_POLL_INTERVAL", 0.1)

    wr._wait_for_containers_gone("task_demo")
    # Must have at least one ps poll and one final rm -f
    rm_calls = [c for c in calls if "rm" in c]
    assert len(rm_calls) == 1, f"expected one docker rm -f call; got {rm_calls}"
    assert rm_calls[0][:3] == ["docker", "rm", "-f"]
    assert "abc123" in rm_calls[0]
    assert "def456" in rm_calls[0]


def test_swallows_docker_missing(monkeypatch) -> None:
    """If docker binary is absent (test env or worker outside cluster),
    return cleanly without raising."""
    from scripts.orchestra import worker_runner as wr

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("docker not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(wr, "subprocess", subprocess)

    # Must not raise
    wr._wait_for_containers_gone("task_demo")


def test_swallows_docker_timeout(monkeypatch) -> None:
    """docker daemon hung → poll times out → function returns cleanly."""
    from scripts.orchestra import worker_runner as wr

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(wr, "subprocess", subprocess)

    wr._wait_for_containers_gone("task_demo")


def test_gc_docker_resources_calls_three_prune_commands(monkeypatch) -> None:
    """The daily GC sweep runs container, image, and build-cache prune.

    0625 (commit 2c3fc650): stopped *containers* now prune at ``until=2h``
    (short-lived cell containers piled up to 119/57GB on worker2 under a 14d
    window), while dangling *images* and the *build cache* stay at
    ``until=336h`` (14d) so base images aren't re-pulled between runs."""
    from scripts.orchestra import worker_runner as wr

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _make_proc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(wr, "subprocess", subprocess)

    wr._gc_stale_docker_resources()
    assert len(calls) == 3
    by_subcommand = {c[1]: c for c in calls}  # docker SUBCOMMAND ...
    assert set(by_subcommand) == {"container", "image", "builder"}
    for c in calls:
        joined = " ".join(c)
        assert "prune" in joined
        assert "-f" in c
    # Containers prune at the tight 2h window; images/build-cache at 14d.
    assert "until=2h" in " ".join(by_subcommand["container"])
    assert "until=336h" in " ".join(by_subcommand["image"])
    assert "until=336h" in " ".join(by_subcommand["builder"])
