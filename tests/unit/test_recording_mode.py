"""Round 11 / B1: 3-tier ``recording`` task field + headless coupling.

Tests verify:
- TaskSpec.recording defaults to "low".
- `load_task` parses ``recording: none/low/high`` from yaml.
- Invalid values raise at load time.
- ``recording_session`` skips ffmpeg entirely for ``none``.
- ``recording_session`` passes the tier into start/stop_recording.
- ``_recording_params`` returns the correct (input_fps, output_fps,
  resolution) per tier.
- ``container_lifecycle`` couples HEADED env to the recording tier.
"""
from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


# --------------------------------------------------------------------------
# TaskSpec field + load_task parsing
# --------------------------------------------------------------------------


def test_taskspec_recording_defaults_to_none() -> None:
    """Round 12 / E4: existing task yamls (no ``recording:`` field) get
    the cheapest ``none`` tier — the throughput win that Round 11 E5
    measured at 39.4 runs/hr.  GUI-fidelity tasks opt back in per-yaml
    with ``recording: high``."""
    from lib.task import TaskSpec, CodexSpec

    task = TaskSpec(
        task_id="t",
        category="c",
        agent_sys="openclaw",
        agent_id="main",
        model="m",
        image_model="m",
        timeout_seconds=120,
        max_total_seconds=240,
        success_threshold=0.5,
        task="x",
        task_snapshot="",
        references=[],
        sources=[],
        skills=[],
        services=[],
        pre_exec=[],
        privacy=[],
        file_path=Path("."),
        injection_root=Path("."),
        codex=CodexSpec(),
    )
    assert task.recording == "none"


def _setup_min_task_assets(tmp_path: Path) -> None:
    """Create the minimum assets that `load_task._validate_task_assets`
    requires: an eval_rule.md reference inside the task's injection dir."""
    inj = tmp_path / "injection" / "101_test" / "task_demo"
    refs = inj / "references"
    refs.mkdir(parents=True)
    (refs / "eval_rule.md").write_text("eval rule", encoding="utf-8")


def test_load_task_accepts_recording_field(tmp_path: Path) -> None:
    """``recording: high`` in yaml → TaskSpec.recording == "high"."""
    from lib.task import load_task

    _setup_min_task_assets(tmp_path)
    yaml_path = tmp_path / "task_demo.yaml"
    yaml_path.write_text("""\
task_id: task_demo
category: 101_test
agent_sys: openclaw
model: test-model
task: |
  do a thing
references:
  - references/eval_rule.md
recording: high
""", encoding="utf-8")
    task = load_task(yaml_path, tmp_path)
    assert task.recording == "high"


def test_load_task_accepts_none_recording(tmp_path: Path) -> None:
    from lib.task import load_task

    _setup_min_task_assets(tmp_path)
    yaml_path = tmp_path / "task_demo.yaml"
    yaml_path.write_text("""\
task_id: task_demo
category: 101_test
agent_sys: openclaw
model: m
task: x
references:
  - references/eval_rule.md
recording: none
""", encoding="utf-8")
    task = load_task(yaml_path, tmp_path)
    assert task.recording == "none"


def test_load_task_missing_recording_defaults_to_none(tmp_path: Path) -> None:
    """Round 12 / E4: existing task yamls (with no recording field) get
    the cheapest ``none`` tier — Round 11 E5 measured 39.4 runs/hr
    with this config (3x Round 10 baseline)."""
    from lib.task import load_task

    _setup_min_task_assets(tmp_path)
    yaml_path = tmp_path / "task_demo.yaml"
    yaml_path.write_text("""\
task_id: task_demo
category: 101_test
agent_sys: openclaw
model: m
task: x
references:
  - references/eval_rule.md
""", encoding="utf-8")
    task = load_task(yaml_path, tmp_path)
    assert task.recording == "none"


def test_load_task_invalid_recording_raises(tmp_path: Path) -> None:
    """Typos / wrong tier names must raise at load time, not silently
    default."""
    from lib.task import load_task

    _setup_min_task_assets(tmp_path)
    yaml_path = tmp_path / "task_demo.yaml"
    yaml_path.write_text("""\
task_id: task_demo
category: 101_test
agent_sys: openclaw
model: m
task: x
references:
  - references/eval_rule.md
recording: medium
""", encoding="utf-8")
    with pytest.raises(ValueError, match="recording"):
        load_task(yaml_path, tmp_path)


# --------------------------------------------------------------------------
# recording_session gating
# --------------------------------------------------------------------------


def _fake_task(agent_sys: str = "openclaw", recording: str = "high"):
    return SimpleNamespace(agent_sys=agent_sys, recording=recording)


def test_recording_session_none_skips_ffmpeg(monkeypatch, tmp_path) -> None:
    """``recording=none`` → no start_recording call, yields False."""
    from lib.runner import media as media_mod

    called: list[str] = []
    monkeypatch.setattr(media_mod, "start_recording", lambda c, **kw: called.append("start") or True)
    monkeypatch.setattr(media_mod, "stop_recording", lambda c, d, **kw: called.append("stop") or True)

    task = _fake_task(recording="none")
    with media_mod.recording_session("c", task, tmp_path) as started:
        assert started is False

    assert called == [], "none mode must NOT call start_recording or stop_recording"


def test_recording_session_passes_mode_to_start(monkeypatch, tmp_path) -> None:
    """``recording=low`` → start_recording(container, mode="low")."""
    from lib.runner import media as media_mod

    captured: dict[str, str] = {}
    def fake_start(container, *, mode="high"):
        captured["start_mode"] = mode
        return True
    def fake_stop(container, out_dir, *, mode="high"):
        captured["stop_mode"] = mode
        return True
    monkeypatch.setattr(media_mod, "start_recording", fake_start)
    monkeypatch.setattr(media_mod, "stop_recording", fake_stop)

    task = _fake_task(recording="low")
    with media_mod.recording_session("c", task, tmp_path):
        pass

    assert captured == {"start_mode": "low", "stop_mode": "low"}


def test_recording_session_passes_high_mode(monkeypatch, tmp_path) -> None:
    from lib.runner import media as media_mod

    captured: dict[str, str] = {}
    monkeypatch.setattr(media_mod, "start_recording", lambda c, *, mode="high": captured.setdefault("start_mode", mode) or True)
    monkeypatch.setattr(media_mod, "stop_recording", lambda c, d, *, mode="high": captured.setdefault("stop_mode", mode) or True)

    task = _fake_task(recording="high")
    with media_mod.recording_session("c", task, tmp_path):
        pass
    assert captured == {"start_mode": "high", "stop_mode": "high"}


# --------------------------------------------------------------------------
# _recording_params tier resolution
# --------------------------------------------------------------------------


def test_recording_params_high() -> None:
    from lib.runner.media import _recording_params
    assert _recording_params("high") == (10, 24, "1440x900")


def test_recording_params_low() -> None:
    from lib.runner.media import _recording_params
    assert _recording_params("low") == (5, 12, "1280x720")


def test_recording_params_unknown_falls_back_to_high() -> None:
    """Defensive: unexpected mode values reach high-tier defaults
    rather than crashing (``recording_session`` short-circuits ``none``
    before this function is called)."""
    from lib.runner.media import _recording_params
    assert _recording_params("bogus") == (10, 24, "1440x900")


# --------------------------------------------------------------------------
# Container lifecycle: HEADED env coupling
# --------------------------------------------------------------------------


def test_container_lifecycle_couples_headed_to_recording_mode() -> None:
    """Source-level guard: container_lifecycle.py must read
    ``task.recording`` and emit ``AGENT_BROWSER_HEADED=0/1`` accordingly.
    """
    path = Path(__file__).resolve().parents[2] / "lib" / "runner" / "container_lifecycle.py"
    text = path.read_text(encoding="utf-8")
    # Confirm the coupling: high → HEADED=1, none/low → HEADED=0
    assert 'task.recording' in text or 'task_recording_mode' in text, (
        "container_lifecycle must read the task's recording mode"
    )
    assert 'AGENT_BROWSER_HEADED=0' in text, (
        "container_lifecycle must emit HEADED=0 for headless tiers"
    )
    assert 'AGENT_BROWSER_HEADED=1' in text, (
        "container_lifecycle must emit HEADED=1 for headed (high) tier"
    )


# --------------------------------------------------------------------------
# Explicit ``headed`` task field (decouples from recording tier)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, "auto"),
        ("", "auto"),
        ("auto", "auto"),
        ("AUTO", "auto"),
        ("true", "true"),
        ("headed", "true"),
        ("1", "true"),
        ("yes", "true"),
        (1, "true"),
        ("false", "false"),
        ("headless", "false"),
        ("0", "false"),
        ("no", "false"),
        (0, "false"),
    ],
)
def test_parse_headed_mode_normalizes(raw, expected) -> None:
    """All accepted aliases collapse onto auto/true/false."""
    from lib.task import _parse_headed_mode
    assert _parse_headed_mode(raw) == expected


def test_parse_headed_mode_invalid_raises() -> None:
    from lib.task import _parse_headed_mode
    with pytest.raises(ValueError, match="headed"):
        _parse_headed_mode("on-demand")


def test_load_task_accepts_headed_field(tmp_path: Path) -> None:
    """``headed: true`` in yaml threads through to TaskSpec.headed."""
    from lib.task import load_task
    _setup_min_task_assets(tmp_path)
    yaml_path = tmp_path / "task_demo.yaml"
    yaml_path.write_text(
        "task_id: task_demo\n"
        "category: 101_test\n"
        "agent_sys: openclaw\n"
        "model: m\n"
        "task: x\n"
        "references:\n  - references/eval_rule.md\n"
        "recording: none\n"
        "headed: true\n",
        encoding="utf-8",
    )
    task = load_task(yaml_path, tmp_path)
    assert task.headed == "true"
    assert task.recording == "none"  # explicit headed does not override recording


def test_load_task_missing_headed_defaults_to_auto(tmp_path: Path) -> None:
    """Existing yamls (no ``headed`` field) keep the recording-coupled
    default."""
    from lib.task import load_task
    _setup_min_task_assets(tmp_path)
    yaml_path = tmp_path / "task_demo.yaml"
    yaml_path.write_text(
        "task_id: task_demo\n"
        "category: 101_test\n"
        "agent_sys: openclaw\n"
        "model: m\n"
        "task: x\n"
        "references:\n  - references/eval_rule.md\n",
        encoding="utf-8",
    )
    task = load_task(yaml_path, tmp_path)
    assert task.headed == "auto"


def test_container_lifecycle_explicit_headed_overrides_recording() -> None:
    """Source-level guard: container_lifecycle must consult the explicit
    ``headed`` field before falling back to the recording-tier coupling
    so the two knobs can be set independently."""
    path = Path(__file__).resolve().parents[2] / "lib" / "runner" / "container_lifecycle.py"
    text = path.read_text(encoding="utf-8")
    assert "task_headed_mode" in text, (
        "container_lifecycle must read task.headed into a local variable"
    )
    # The explicit branch must precede the recording-tier branch in the
    # source so explicit settings win.  Compare the indices of the first
    # mention of each branch's literal token.
    headed_branch = text.find('if task_headed_mode == "true"')
    recording_branch = text.find('elif task_recording_mode == "high"')
    assert headed_branch != -1 and recording_branch != -1, (
        "expected both task_headed_mode and task_recording_mode branches"
    )
    assert headed_branch < recording_branch, (
        "explicit headed branch must precede the recording-tier fallback"
    )
