"""Phase 3 — pin artifact-profile gating for supervisor / user-simulator files.

Default profile is ``public``: only ``{name}_decision.json`` is persisted from
``write_supervision_component_artifacts``, and ``supervision_component_summary``
keeps prompts / workspace manifests out of ``supervision_trace.jsonl``.
``CLAWBENCH_ARTIFACT_PROFILE=debug`` restores the legacy full-artefact set.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.runner.artifacts import (
    ARTIFACT_PROFILE_DEBUG,
    ARTIFACT_PROFILE_PUBLIC,
    DEFAULT_ARTIFACT_PROFILE,
    current_artifact_profile,
    supervision_component_summary,
    write_supervision_component_artifacts,
)


@pytest.fixture
def cycle_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cycle_01"
    d.mkdir()
    return d


@pytest.fixture
def loaded_component() -> dict:
    return {
        "prompt": "FULL_SUPERVISOR_PROMPT_BODY",
        "raw_response": "RAW_MODEL_RESPONSE",
        "stdout": "stdout-bytes",
        "stderr": "stderr-bytes",
        "decision": {"verdict": "continue", "score": 0.4},
        "input_workspace": {"manifest": "x"},
        "input_readme": "WORKSPACE_README_CONTENTS",
        "workspace_root": "/tmp/ws",
        "transport": "codex",
        "elapsed_ms": 1234,
        "image_inputs": ["a.png"],
    }


def test_default_profile_is_public():
    assert DEFAULT_ARTIFACT_PROFILE == ARTIFACT_PROFILE_PUBLIC


def test_current_artifact_profile_defaults_to_public(monkeypatch):
    monkeypatch.delenv("CLAWBENCH_ARTIFACT_PROFILE", raising=False)
    assert current_artifact_profile() == ARTIFACT_PROFILE_PUBLIC


def test_current_artifact_profile_invalid_value_falls_back_to_public(monkeypatch):
    monkeypatch.setenv("CLAWBENCH_ARTIFACT_PROFILE", "nonsense")
    assert current_artifact_profile() == ARTIFACT_PROFILE_PUBLIC


def test_current_artifact_profile_explicit_debug(monkeypatch):
    monkeypatch.setenv("CLAWBENCH_ARTIFACT_PROFILE", "debug")
    assert current_artifact_profile() == ARTIFACT_PROFILE_DEBUG


def test_public_profile_writes_only_decision_json(cycle_dir, loaded_component):
    write_supervision_component_artifacts(
        cycle_dir,
        "answer_supervisor",
        loaded_component,
        profile=ARTIFACT_PROFILE_PUBLIC,
    )
    files = sorted(p.name for p in cycle_dir.iterdir())
    assert files == ["answer_supervisor_decision.json"]
    body = json.loads((cycle_dir / "answer_supervisor_decision.json").read_text())
    assert body == {"verdict": "continue", "score": 0.4}


def test_debug_profile_writes_full_artifact_set(cycle_dir, loaded_component):
    write_supervision_component_artifacts(
        cycle_dir,
        "answer_supervisor",
        loaded_component,
        profile=ARTIFACT_PROFILE_DEBUG,
    )
    expected = {
        "answer_supervisor_decision.json",
        "answer_supervisor_prompt.txt",
        "answer_supervisor_response.txt",
        "answer_supervisor_stdout.log",
        "answer_supervisor_stderr.log",
        "answer_supervisor_input_workspace.json",
        "answer_supervisor_input_readme.md",
    }
    assert {p.name for p in cycle_dir.iterdir()} == expected
    prompt_text = (cycle_dir / "answer_supervisor_prompt.txt").read_text()
    assert "FULL_SUPERVISOR_PROMPT_BODY" in prompt_text


def test_public_summary_omits_prompt_and_workspace(loaded_component):
    summary = supervision_component_summary(loaded_component, profile=ARTIFACT_PROFILE_PUBLIC)
    assert summary["transport"] == "codex"
    assert summary["elapsed_ms"] == 1234
    assert summary["image_inputs"] == ["a.png"]
    assert summary["decision"] == {"verdict": "continue", "score": 0.4}
    for forbidden in ("prompt", "input_workspace", "input_readme", "workspace_root"):
        assert forbidden not in summary, f"{forbidden} leaked into public summary"


def test_debug_summary_includes_prompt_and_workspace(loaded_component):
    summary = supervision_component_summary(loaded_component, profile=ARTIFACT_PROFILE_DEBUG)
    assert summary["prompt"] == "FULL_SUPERVISOR_PROMPT_BODY"
    assert summary["input_workspace"] == {"manifest": "x"}
    assert summary["input_readme"] == "WORKSPACE_README_CONTENTS"
    assert summary["workspace_root"] == "/tmp/ws"


def test_env_var_drives_default_in_writer(monkeypatch, cycle_dir, loaded_component):
    """When ``profile`` is not passed, the writer reads the env var."""
    monkeypatch.setenv("CLAWBENCH_ARTIFACT_PROFILE", "public")
    write_supervision_component_artifacts(cycle_dir, "answer_supervisor", loaded_component)
    assert {p.name for p in cycle_dir.iterdir()} == {"answer_supervisor_decision.json"}


def test_env_var_drives_default_in_summary(monkeypatch, loaded_component):
    monkeypatch.setenv("CLAWBENCH_ARTIFACT_PROFILE", "debug")
    summary = supervision_component_summary(loaded_component)
    assert "prompt" in summary
