"""Round 9 / B1: ``scripts/fetch_edict.sh`` formalizes EDICT asset
acquisition + records upstream commit/version metadata.

These tests pin the script's contract:

- When ``downloads/edict/`` already exists with required files + a
  matching ``EDICT_COMMIT`` file, fast-path skip extraction.
- After a real extraction, the ``EDICT_COMMIT`` + ``EDICT_VERSION``
  metadata files exist and are non-empty.
- The docker build (``openclaw-edict.Dockerfile``) copies the metadata
  files so the image carries the official-revision marker into
  ``/opt/edict``.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "fetch_edict.sh"
DOWNLOADS = ROOT / "downloads"
EDICT_DIR = DOWNLOADS / "edict"


pytestmark = pytest.mark.skipif(
    not (DOWNLOADS / "edict-main.tar.gz").is_file(),
    reason="downloads/edict-main.tar.gz not present (offline test env)",
)


def _run_script(env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_fetch_edict_writes_commit_and_version_metadata() -> None:
    """After (re-)extraction, EDICT_COMMIT + EDICT_VERSION are present
    and non-empty.  This is what the Dockerfile COPY hooks into."""
    proc = _run_script({"EDICT_FORCE": "1"})
    assert proc.returncode == 0, (
        f"fetch_edict.sh failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    commit_file = EDICT_DIR / "EDICT_COMMIT"
    version_file = EDICT_DIR / "EDICT_VERSION"
    assert commit_file.is_file(), "EDICT_COMMIT metadata file missing after fetch"
    assert version_file.is_file(), "EDICT_VERSION metadata file missing after fetch"
    assert commit_file.read_text(encoding="utf-8").strip(), "EDICT_COMMIT is empty"
    assert version_file.read_text(encoding="utf-8").strip(), "EDICT_VERSION is empty"


def test_fetch_edict_idempotent_fast_path() -> None:
    """Second invocation skips re-extraction when EDICT_COMMIT matches +
    required files are present.  Repeated build_image.sh runs MUST be
    cheap or CI/parallel-worker builds will thrash."""
    # First run to seed state
    seed = _run_script({"EDICT_FORCE": "1"})
    assert seed.returncode == 0
    # Second run without EDICT_FORCE — fast path
    repeat = _run_script({})
    assert repeat.returncode == 0
    combined = repeat.stdout + repeat.stderr
    assert "skipping fetch" in combined, (
        "second invocation should hit fast path; instead got:\n" + combined
    )


def test_fetch_edict_required_files_intact() -> None:
    """build_image.sh::ensure_edict_assets() depends on this exact set
    of files; the fetch script's --strip-components=1 must land them at
    the expected relative paths.  Drift here would silently break the
    image build."""
    proc = _run_script({"EDICT_FORCE": "1"})
    assert proc.returncode == 0
    required = (
        "agents",
        "agents/GLOBAL.md",
        "agents/groups/sansheng.md",
        "dashboard",
        "scripts/kanban_update.py",
        "data/schema.json",
        "edict/backend/app/models/task.py",
        "docker/demo_data/openclaw.json",
        "docker/demo_data/tasks_source.json",
        "agents.json",
    )
    missing = [rel for rel in required if not (EDICT_DIR / rel).exists()]
    assert not missing, f"missing required EDICT files after fetch: {missing}"


def test_dockerfile_copies_metadata() -> None:
    """Source-level check: the openclaw_edict Dockerfile must COPY the
    EDICT_COMMIT + EDICT_VERSION files written by fetch_edict.sh.
    Without these COPY lines the in-container metadata is unavailable
    and Round 9 / B3 summary fields are silently empty."""
    dockerfile = ROOT / "docker" / "openclaw-edict.Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    assert "downloads/edict/EDICT_COMMIT" in text, (
        "Dockerfile must COPY downloads/edict/EDICT_COMMIT into the image"
    )
    assert "downloads/edict/EDICT_VERSION" in text, (
        "Dockerfile must COPY downloads/edict/EDICT_VERSION into the image"
    )


def test_build_image_ensure_edict_assets_calls_fetch_script() -> None:
    """build_image.sh's ensure_edict_assets() must shell out to
    scripts/fetch_edict.sh (not duplicate the curl logic inline) so the
    metadata write happens consistently."""
    build_script = ROOT / "scripts" / "build_image.sh"
    text = build_script.read_text(encoding="utf-8")
    assert "scripts/fetch_edict.sh" in text, (
        "scripts/build_image.sh must dispatch to scripts/fetch_edict.sh"
    )
