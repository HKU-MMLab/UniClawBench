"""Pin the recording-mode getattr fallback to "none".

Round 15 (P3 in the code review) noticed that two call sites defensively
fall back to ``"high"`` when an input object lacks the ``recording``
attribute:

  - ``lib/runner/container_lifecycle.py:start_container`` (the docker
    run wrapper) — ``"high"`` would silently set ``AGENT_BROWSER_HEADED=1``
    even though real ``TaskSpec`` objects default to ``"none"``.
  - ``lib/runner/media.py:recording_session`` (the ffmpeg context manager)
    — ``"high"`` would silently start a recording.

Both fallbacks are reached only by synthetic/test-double tasks (real
``TaskSpec`` objects always carry the attribute), so the bug is latent.
But the latent default contradicts the production-default policy
("recording=none + headless").  This test pins the new ``"none"``
fallback so a future refactor cannot silently re-introduce the
high-fidelity-headed default.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def _make_taskish_without_recording() -> SimpleNamespace:
    """Build a minimal task-like object that has every attribute the
    code paths under test look up — EXCEPT ``recording``.  The
    ``recording`` lookup must therefore exercise the ``getattr(.., "none")``
    fallback we want to pin."""
    return SimpleNamespace(
        task_id="task_synthetic_recording_fallback",
        privacy={},
        injection_root=Path("/nonexistent"),
        services=(),
        skills=(),
        agent_sys="openclaw",
        # Intentionally NO `recording` attribute.
    )


def test_container_lifecycle_fallback_recording_forces_headless(monkeypatch) -> None:
    """``start_container`` with a recording-less task must export
    ``AGENT_BROWSER_HEADED=0`` (not =1) — i.e. the fallback is "none"."""
    from lib.runner import container_lifecycle

    # Capture the argv passed to docker_mod.docker(...).  That's the
    # `docker run ...` invocation we want to inspect.
    captured_argv: list[list[str]] = []

    class _FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_docker(argv, *args, **kwargs):
        captured_argv.append(list(argv))
        return _FakeResult()

    def fake_docker_rm(*args, **kwargs):
        return _FakeResult()

    def fake_resolve_privacy_env(privacy):
        return {}

    monkeypatch.setattr(container_lifecycle.docker_mod, "docker", fake_docker)
    monkeypatch.setattr(container_lifecycle.docker_mod, "docker_rm", fake_docker_rm)
    monkeypatch.setattr(container_lifecycle, "resolve_privacy_env", fake_resolve_privacy_env)

    task = _make_taskish_without_recording()
    container_name = container_lifecycle.start_container(
        image="clawbench-openclaw:latest",
        task=task,
        attempt_id="abc123",
    )
    assert container_name.startswith("clawbench-task_synthetic")
    assert captured_argv, "docker_mod.docker was never called"
    flat = " ".join(captured_argv[-1])
    assert "AGENT_BROWSER_HEADED=0" in flat, (
        "fallback recording mode must be 'none' (headless).  Found argv: "
        + flat
    )
    assert "AGENT_BROWSER_HEADED=1" not in flat, (
        "Pre-Round-15 the fallback was 'high' which would set HEADED=1.  "
        "If this assertion fires, the fallback regressed."
    )


def test_media_recording_session_fallback_skips_ffmpeg(monkeypatch) -> None:
    """``recording_session`` with a recording-less task must enter the
    skip-ffmpeg branch (``yield False`` without calling start_recording)."""
    from lib.runner import media

    # If the fallback regresses to "high", recording_session will call
    # start_recording.  Track invocations to detect that.
    start_calls: list[tuple] = []

    def fake_start_recording(*args, **kwargs):
        start_calls.append((args, kwargs))
        return False

    monkeypatch.setattr(media, "start_recording", fake_start_recording)

    task = _make_taskish_without_recording()
    out_dir = Path("/tmp/clawbench_test_recording_fallback")
    with media.recording_session("dummy-container", task, out_dir) as recording_started:
        # With "none" fallback, this should be False AND start_recording
        # must NOT have been called.
        assert recording_started is False, (
            "fallback must yield False (skip-ffmpeg).  Pre-Round-15 it would "
            "yield whatever start_recording returned."
        )
    assert start_calls == [], (
        "Pre-Round-15 fallback was 'high' which would call start_recording.  "
        "If this assertion fires, the fallback regressed."
    )
