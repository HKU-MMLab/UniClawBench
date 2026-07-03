"""Tests for desktop recording lifecycle (start/stop/session wrapper).

Recording is an environment-dependent side effect (requires ffmpeg + X11 inside
the executor container) so these tests only exercise the orchestration contract:

  - recording is gated on agent_sys;
  - failures in start/stop must never raise or block the surrounding task;
  - the session context manager always attempts to stop what it started.

They deliberately do not spin up a real container or ffmpeg.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import lib.runner as runner
from lib.runner import media as recording_module  # ``recording`` was merged into ``media`` in the Phase 2 refactor


def _task(agent_sys: str, *, recording: str = "high") -> SimpleNamespace:
    """Build a minimal task-like for recording_session tests.

    Defaults ``recording="high"`` because every test in this module
    that drives recording_session through start/stop wants the recording
    branch to fire — the lifecycle is what's being tested, not the
    default-mode fallback (which lives in
    ``tests/unit/test_recording_fallback_none.py``).
    """
    return SimpleNamespace(agent_sys=agent_sys, recording=recording)


# ── recording_session: gating by agent_sys ────────────────────────────


def test_recording_session_noop_for_unsupported_agent_sys(monkeypatch, tmp_path) -> None:
    """recording_session must be a pure no-op when the agent_sys is not in the
    supported set — no ffmpeg invocation, no side effects."""
    calls: list[str] = []

    def fake_start(container: str) -> bool:
        calls.append("start")
        return True

    def fake_stop(container: str, out_dir: Path) -> bool:
        calls.append("stop")
        return True

    monkeypatch.setattr(recording_module, "start_recording", fake_start)
    monkeypatch.setattr(recording_module, "stop_recording", fake_stop)

    # Pick an agent_sys that is definitely not in RECORDING_SUPPORTED_AGENT_SYSTEMS
    fake_task = _task("no-such-backend")
    with runner.recording_session("fake-container", fake_task, tmp_path) as started:
        assert started is False, "recording_session must report False when gated off"

    assert calls == [], "start/stop must not be called for unsupported agent_sys"


def test_recording_session_supported_agent_sys_runs_start_and_stop(
    monkeypatch, tmp_path
) -> None:
    """For a supported backend, start_recording should be called exactly once
    on enter and stop_recording exactly once on exit."""
    order: list[str] = []

    def fake_start(container: str, **kwargs) -> bool:
        order.append(f"start:{container}")
        return True

    def fake_stop(container: str, out_dir: Path, **kwargs) -> bool:
        order.append(f"stop:{container}:{out_dir}")
        return True

    monkeypatch.setattr(recording_module, "start_recording", fake_start)
    monkeypatch.setattr(recording_module, "stop_recording", fake_stop)

    fake_task = _task("openclaw")
    assert "openclaw" in runner.RECORDING_SUPPORTED_AGENT_SYSTEMS

    with runner.recording_session("c1", fake_task, tmp_path) as started:
        assert started is True
        order.append("body")

    assert order == ["start:c1", "body", f"stop:c1:{tmp_path}"]


def test_recording_session_start_failure_does_not_call_stop(
    monkeypatch, tmp_path
) -> None:
    """If start_recording returns False, stop_recording must NOT be called —
    there's nothing to stop, and calling stop against a non-running recorder
    could race with a later container shutdown."""
    calls: list[str] = []

    def fake_start(container: str, **kwargs) -> bool:
        calls.append("start")
        return False  # ffmpeg failed to launch

    def fake_stop(container: str, out_dir: Path, **kwargs) -> bool:
        calls.append("stop")
        return True

    monkeypatch.setattr(recording_module, "start_recording", fake_start)
    monkeypatch.setattr(recording_module, "stop_recording", fake_stop)

    fake_task = _task("nanobot")
    with runner.recording_session("c2", fake_task, tmp_path) as started:
        assert started is False

    assert calls == ["start"], "stop must not run when start failed"


def test_recording_session_body_exception_still_calls_stop(
    monkeypatch, tmp_path
) -> None:
    """If the wrapped task raises, we must still run stop_recording to avoid
    leaving an ffmpeg PID inside the container. The exception then re-propagates."""
    calls: list[str] = []

    monkeypatch.setattr(recording_module, "start_recording", lambda c, **kw: calls.append("start") or True)
    monkeypatch.setattr(
        recording_module,
        "stop_recording",
        lambda c, d, **kw: calls.append("stop") or True,
    )

    fake_task = _task("openclaw_edict")
    raised = False
    try:
        with runner.recording_session("c3", fake_task, tmp_path):
            raise RuntimeError("boom")
    except RuntimeError:
        raised = True

    assert raised, "body exception must propagate"
    assert calls == ["start", "stop"], "stop must run even after body raised"


# ── start_recording: never raises ────────────────────────────────────


def test_start_recording_returns_false_on_docker_timeout(monkeypatch) -> None:
    """Docker subprocess TimeoutExpired must be swallowed into a False return."""
    def fake_docker_exec(container: str, script: str, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["docker"], timeout=20)

    monkeypatch.setattr(recording_module, "docker_exec", fake_docker_exec)
    assert runner.start_recording("c") is False


def test_start_recording_returns_false_on_nonzero_exit(monkeypatch) -> None:
    """ffmpeg non-zero exit must be reported as a False start, not raise."""
    def fake_docker_exec(container: str, script: str, **kwargs):
        return subprocess.CompletedProcess(
            args=["docker"], returncode=1, stdout="", stderr="ffmpeg: X server missing"
        )

    monkeypatch.setattr(recording_module, "docker_exec", fake_docker_exec)
    assert runner.start_recording("c") is False


def test_start_recording_returns_true_on_success(monkeypatch) -> None:
    def fake_docker_exec(container: str, script: str, **kwargs):
        return subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(recording_module, "docker_exec", fake_docker_exec)
    assert runner.start_recording("c") is True


# ── supported agent_sys set ───────────────────────────────────────────


def test_recording_supported_agent_sys_set_covers_all_runtime_backends() -> None:
    """Recording must at minimum cover the three runtime backends. If someone
    narrows the set without meaning to, this test flags it."""
    assert runner.RECORDING_SUPPORTED_AGENT_SYSTEMS == {
        "openclaw",
        "nanobot",
        "openclaw_edict",
    }


def test_recording_session_routes_output_to_cycle_subdir(monkeypatch, tmp_path) -> None:
    """per-cycle recording: stop_recording must receive the supervision/cycle_NN
    sub-directory, not the attempt root."""
    captured_out_dirs: list[Path] = []

    monkeypatch.setattr(recording_module, "start_recording", lambda c, **kw: True)
    monkeypatch.setattr(
        recording_module,
        "stop_recording",
        lambda c, out_dir, **kw: captured_out_dirs.append(Path(out_dir)) or True,
    )

    attempt_dir = tmp_path / "p1-abcdef"
    cycle_dir = attempt_dir / "supervision" / "cycle_01"
    cycle_dir.mkdir(parents=True)

    fake_task = _task("openclaw")
    with runner.recording_session("c", fake_task, cycle_dir):
        pass

    # recording.mp4 should be written into the cycle subdirectory, not the
    # attempt root — this keeps multi-cycle runs from overwriting each other.
    assert captured_out_dirs == [cycle_dir]
    assert captured_out_dirs[0].name == "cycle_01"
    assert captured_out_dirs[0].parent.name == "supervision"


def test_recordings_by_cycle_webui_helper_scans_cycle_dirs(tmp_path, monkeypatch) -> None:
    """The webui helper returns {cycle_index: payload} for each non-empty
    supervision/cycle_NN/recording.mp4, ignoring empties / malformed dirs."""
    import webui.server as server

    # We need rec.relative_to(RUNS) to not raise — point RUNS at tmp_path.
    monkeypatch.setattr(server, "RUNS", tmp_path)

    attempt_dir = tmp_path / "p1-xyz"
    (attempt_dir / "supervision").mkdir(parents=True)

    # cycle_01 with valid recording
    c1 = attempt_dir / "supervision" / "cycle_01"
    c1.mkdir()
    (c1 / "recording.mp4").write_bytes(b"fake mp4 content")

    # cycle_02 with empty file → should be skipped
    c2 = attempt_dir / "supervision" / "cycle_02"
    c2.mkdir()
    (c2 / "recording.mp4").write_bytes(b"")

    # cycle_03 with no file → absent from result
    (attempt_dir / "supervision" / "cycle_03").mkdir()

    # non-cycle directory — ignored
    (attempt_dir / "supervision" / "notes").mkdir()

    result = server.recordings_by_cycle(attempt_dir)
    assert set(result.keys()) == {1}, f"only cycle_01 should be present, got {result!r}"
    assert result[1]["url"].endswith("/supervision/cycle_01/recording.mp4")
    assert result[1]["sizeBytes"] > 0
    assert result[1]["speedup"] == 16


def test_recordings_by_cycle_recording_none_returns_empty(tmp_path, monkeypatch) -> None:
    """Round 12 / E5: recording=none runs have supervision/cycle_NN
    directories with score.json / trace transcript / screenshots but NO
    recording.mp4.  The helper must return an empty dict so the frontend
    falls through to rendering trace + score panels without a video
    placeholder."""
    import webui.server as server

    monkeypatch.setattr(server, "RUNS", tmp_path)

    attempt_dir = tmp_path / "p1-recording-none"
    (attempt_dir / "supervision").mkdir(parents=True)

    # Two cycles, both with score.json (mimicking recording=none output)
    for n in (1, 2):
        c = attempt_dir / "supervision" / f"cycle_{n:02d}"
        c.mkdir()
        (c / "score.json").write_text("{}", encoding="utf-8")
        # NO recording.mp4 — recording=none was set

    result = server.recordings_by_cycle(attempt_dir)
    assert result == {}, (
        "recording=none runs must produce an empty {cycle: payload} map; "
        "frontend treats missing key as 'no video panel' and renders trace + score"
    )
