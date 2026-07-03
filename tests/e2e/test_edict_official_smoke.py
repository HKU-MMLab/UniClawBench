"""Round 9 / B5: structural smoke test for the EDICT image-build path.

The actual docker-running smoke happens on worker3 in Phase D — this file
pins the wiring so the smoke can succeed.  Tests here validate that
the moving parts (fetch script → Dockerfile COPY entries → orchestrator
state-machine + final-report path) connect correctly.

A failure here means the worker3 smoke would fail for a structural reason
(missing COPY, missing fallback path, missing dispatch state) that we
can catch on the host without spinning up the image.

Marked under ``tests/e2e/`` because the worker3 docker-run companion lives
in the same area and our test runner already understands the layout.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "docker" / "openclaw-edict.Dockerfile"
ORCHESTRATOR = ROOT / "docker" / "edict_orchestrator.py"
FETCH_SCRIPT = ROOT / "scripts" / "fetch_edict.sh"
BUILD_SCRIPT = ROOT / "scripts" / "build_image.sh"
DOWNLOADS_EDICT = ROOT / "downloads" / "edict"


pytestmark = pytest.mark.skipif(
    not DOWNLOADS_EDICT.is_dir(),
    reason="downloads/edict/ missing (offline test env)",
)


def test_dockerfile_copy_paths_exist_in_downloads() -> None:
    """Every ``COPY downloads/edict/<x> ...`` in the openclaw-edict
    Dockerfile must point at a real file or directory under
    downloads/edict.  If fetch_edict.sh ever drops one of these out of
    the extraction, the docker build fails late + opaquely on worker3."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    copy_lines = [line for line in text.splitlines() if line.strip().startswith("COPY downloads/edict/")]
    assert copy_lines, "Dockerfile lost its downloads/edict COPY lines"
    for line in copy_lines:
        # COPY <src> <dest>  — take src (second token)
        parts = line.split()
        assert len(parts) >= 3, f"unexpected COPY shape: {line!r}"
        rel = parts[1]
        assert rel.startswith("downloads/edict/"), rel
        target = ROOT / rel
        assert target.exists(), (
            f"Dockerfile COPYs {rel!r} but {target} doesn't exist; "
            "re-run scripts/fetch_edict.sh to repopulate"
        )


def test_orchestrator_state_machine_wires_final_report() -> None:
    """``docker/edict_orchestrator.py`` must always invoke taizi for
    the final report — both on terminal-state detection and on
    wall-clock timeout — or the attempt collects no executor conclusion
    and the supervisor sees an empty transcript."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    # Final report function must exist
    assert "def invoke_taizi_final_report" in text, (
        "edict_orchestrator.py lost invoke_taizi_final_report definition"
    )
    # And it must be invoked from BOTH the terminal-state branch and
    # the wall-clock timeout branch.  Two distinct call sites.
    call_sites = text.count("invoke_taizi_final_report(")
    # The def itself is 1 occurrence; we want at least 2 call sites + the def = 3.
    assert call_sites >= 3, (
        f"invoke_taizi_final_report referenced only {call_sites} times — "
        "should be definition + 1 terminal-state call + 1 timeout call"
    )


def test_orchestrator_terminal_states_cover_done_and_cancelled() -> None:
    """The orchestrator's TERMINAL_STATES must include Done + Cancelled.
    Parity test in tests/integration/test_edict_adapter_parity.py
    verifies these match upstream — here we additionally confirm the
    in-script branch that uses them is wired."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    # Find the TERMINAL_STATES literal
    match = re.search(r"TERMINAL_STATES\s*:\s*set\[str\]\s*=\s*(\{[^}]+\})", text)
    assert match, "TERMINAL_STATES annotation missing"
    states = ast.literal_eval(match.group(1))
    assert states == {"Done", "Cancelled"}, states


def test_fetch_script_marked_executable() -> None:
    """The fetch script must be marked executable; otherwise the
    build_image.sh::ensure_edict_assets dispatch line fails on a
    cold-clone."""
    import os, stat
    mode = os.stat(FETCH_SCRIPT).st_mode
    assert mode & stat.S_IXUSR, (
        f"scripts/fetch_edict.sh missing user-execute bit: {oct(mode)}"
    )


def test_build_script_routes_openclaw_edict_through_ensure_edict_assets() -> None:
    """scripts/build_image.sh must call ensure_edict_assets in the
    openclaw_edict branch, AND ensure_edict_assets must invoke
    fetch_edict.sh when files are missing.  Without this wiring a
    user who clones the repo fresh + runs build_image.sh openclaw_edict
    hits an opaque docker build failure."""
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    # Branch
    assert "openclaw_edict)" in text
    # Calls ensure_edict_assets in that branch
    assert re.search(r"openclaw_edict\)[^)]*ensure_edict_assets", text, re.DOTALL), (
        "openclaw_edict branch should call ensure_edict_assets"
    )
    # ensure_edict_assets falls back to fetch_edict.sh
    assert "fetch_edict.sh" in text


def test_edict_metadata_files_present_after_fetch() -> None:
    """B1's fetch script writes EDICT_COMMIT + EDICT_VERSION; the
    Dockerfile COPYs them.  If either side drops the metadata, the
    summary edict block reads 'unknown' / the badge disappears."""
    commit_file = DOWNLOADS_EDICT / "EDICT_COMMIT"
    version_file = DOWNLOADS_EDICT / "EDICT_VERSION"
    assert commit_file.is_file(), (
        f"{commit_file} missing — fetch_edict.sh failed to seed metadata"
    )
    assert version_file.is_file(), (
        f"{version_file} missing — fetch_edict.sh failed to seed metadata"
    )
    assert commit_file.read_text().strip(), "EDICT_COMMIT empty"
    assert version_file.read_text().strip(), "EDICT_VERSION empty"


def test_orchestrator_polls_known_kanban_file_path() -> None:
    """``CLAWBENCH_EDICT_KANBAN_FILE`` defaults to
    ``/tmp_workspace/edict/data/tasks_source.json`` — this path is
    what edict's in-container scripts write/read.  A rename here
    silently breaks dispatch (orchestrator reads stale state)."""
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "/tmp_workspace/edict/data/tasks_source.json" in text, (
        "orchestrator default kanban path drifted from upstream layout"
    )
