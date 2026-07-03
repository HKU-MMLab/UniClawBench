"""Round 9 / B3: surface EDICT upstream commit/version/mode in the
attempt summary + agent_sessions_manifest.

These tests pin:
- ``read_edict_runtime_metadata()`` reports the contents of the
  downloads/edict/EDICT_COMMIT + EDICT_VERSION files written by
  scripts/fetch_edict.sh, plus a stable ``mode`` tag.
- Missing metadata files fall back to "unknown" rather than crashing.
- ``task_summary_base()`` includes the ``edict`` block when (and ONLY
  when) backend == openclaw_edict.  Other backends omit it.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def test_read_edict_runtime_metadata_from_downloads(tmp_path: Path) -> None:
    """When the downloads/edict/ files exist, their contents are
    surfaced verbatim."""
    from lib.runner import edict as edict_mod

    commit = tmp_path / "EDICT_COMMIT"
    version = tmp_path / "EDICT_VERSION"
    commit.write_text("main\n", encoding="utf-8")
    version.write_text("main-20260514\n", encoding="utf-8")
    with patch.object(edict_mod, "EDICT_COMMIT_FILE", commit), \
         patch.object(edict_mod, "EDICT_VERSION_FILE", version):
        meta = edict_mod.read_edict_runtime_metadata()
    assert meta["mode"] == "official_specs_local_adapter"
    assert meta["commit"] == "main"
    assert meta["version"] == "main-20260514"


def test_read_edict_runtime_metadata_missing_files(tmp_path: Path) -> None:
    """When the metadata files are absent (older snapshot built before
    Round 9 / B1), the resolver returns 'unknown' rather than crashing."""
    from lib.runner import edict as edict_mod

    with patch.object(edict_mod, "EDICT_COMMIT_FILE", tmp_path / "does-not-exist-commit"), \
         patch.object(edict_mod, "EDICT_VERSION_FILE", tmp_path / "does-not-exist-version"):
        meta = edict_mod.read_edict_runtime_metadata()
    assert meta == {
        "mode": "official_specs_local_adapter",
        "commit": "unknown",
        "version": "unknown",
    }


def test_read_edict_runtime_metadata_empty_files(tmp_path: Path) -> None:
    """An empty file ('') is treated the same as missing — the metadata
    is unknown but no exception."""
    from lib.runner import edict as edict_mod

    commit = tmp_path / "EDICT_COMMIT"
    version = tmp_path / "EDICT_VERSION"
    commit.write_text("", encoding="utf-8")
    version.write_text("   \n", encoding="utf-8")
    with patch.object(edict_mod, "EDICT_COMMIT_FILE", commit), \
         patch.object(edict_mod, "EDICT_VERSION_FILE", version):
        meta = edict_mod.read_edict_runtime_metadata()
    assert meta["commit"] == "unknown"
    assert meta["version"] == "unknown"


def _make_task(tmp_path: Path, backend: str):
    """Minimal TaskSpec for summary tests.  Borrowed from
    test_artifact_schema_version.py — kept inline so the test file
    doesn't depend on a shared fixture module."""
    from lib.task import CodexSpec, TaskSpec

    return TaskSpec(
        task_id=f"t-{backend}",
        category="cat",
        agent_sys=backend,
        agent_id="main",
        model="provider_primary-gpt-5-4",
        image_model="provider_primary-gpt-5-4",
        timeout_seconds=1200,
        max_total_seconds=1800,
        success_threshold=0.5,
        task="task body",
        task_snapshot="",
        references=[],
        sources=[],
        skills=[],
        services=[],
        pre_exec=[],
        privacy=[],
        file_path=tmp_path / "fake.yaml",
        injection_root=tmp_path / "inj",
        codex=CodexSpec(),
        pre_exec_parallel_safe=False,
    )


def test_task_summary_base_includes_edict_block_for_openclaw_edict(tmp_path: Path) -> None:
    """task_summary_base() must include the ``edict`` sub-object when
    backend == openclaw_edict.  WebUI's badge renderer reads this."""
    from lib.runner.orchestration import task_summary_base
    from lib.runner import edict as edict_mod

    task = _make_task(tmp_path, "openclaw_edict")
    with patch.object(
        edict_mod,
        "read_edict_runtime_metadata",
        return_value={"mode": "official_specs_local_adapter", "commit": "deadbeef", "version": "deadbee"},
    ):
        summary = task_summary_base(task)
    assert "edict" in summary
    assert summary["edict"]["mode"] == "official_specs_local_adapter"
    assert summary["edict"]["commit"] == "deadbeef"
    assert summary["edict"]["version"] == "deadbee"


def test_task_summary_base_omits_edict_block_for_other_backends(tmp_path: Path) -> None:
    """openclaw / nanobot / codex runs must NOT carry the edict block —
    it would clutter the summary and break filters that key on its
    presence."""
    from lib.runner.orchestration import task_summary_base

    for backend in ("openclaw", "nanobot", "codex"):
        task = _make_task(tmp_path, backend)
        summary = task_summary_base(task)
        assert "edict" not in summary, (
            f"non-edict backend {backend} should not carry edict metadata; "
            f"got: {summary.get('edict')}"
        )


def test_edict_mode_constant_is_official_specs_local_adapter() -> None:
    """Lock the mode string — the WebUI badge text + dashboard filters
    key on this exact value.  A rename is a coordinated change across
    the renderer + tests."""
    from lib.runner.edict import EDICT_MODE

    assert EDICT_MODE == "official_specs_local_adapter"


def test_collect_edict_metadata_manifest_fields_documented_in_code() -> None:
    """Source-level guard: agent_sessions_manifest.json must carry the
    three edict fields.  Without this, the WebUI legacy.js renderer
    can't show the badge."""
    from lib.runner import artifacts as artifacts_mod

    src_path = Path(artifacts_mod.__file__)
    text = src_path.read_text(encoding="utf-8")
    for field in ("edictMode", "edictCommit", "edictVersion"):
        assert field in text, (
            f"collect_edict_agent_session_artifacts must emit {field!r} "
            "into agent_sessions_manifest.json"
        )
