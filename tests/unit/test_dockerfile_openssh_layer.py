"""Pin the openssh-client layer position: it MUST be in runtime-base, not
openclaw.

Round 14 originally added openssh-client to openclaw.Dockerfile because
openclaw's npm install pulls a libsignal-node submodule whose
package-lock.json points at ``ssh://git@github.com/...`` URLs.  This
caused the symptom (ssh-not-found at openclaw build time) to disappear,
but the fix lived in the wrong layer: every derived image (openclaw,
nanobot, openclaw-edict) needs ssh for the same reason, and the obvious
home is the shared base — clawbench-runtime-base.

Moving the install to runtime-base means:
  - One apt-get layer, not three (smaller derived images).
  - Future Dockerfiles that FROM clawbench-runtime-base automatically
    inherit the working ssh binary.
  - The fix is documented in one place.

These tests pin the layer position so a future "tidy this up" refactor
doesn't accidentally yank ssh back out of the base.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKER_DIR = REPO_ROOT / "docker"


def test_runtime_base_installs_openssh_client() -> None:
    """clawbench-runtime-base must apt-install openssh-client so all
    derived images inherit ssh."""
    text = (DOCKER_DIR / "runtime-base.Dockerfile").read_text()
    # Look for openssh-client in any apt-get install line.
    install_lines = [
        ln for ln in text.splitlines()
        if "apt-get install" in ln or "openssh-client" in ln
    ]
    assert install_lines, "runtime-base.Dockerfile has no apt-get install lines"
    joined = "\n".join(install_lines)
    assert "openssh-client" in joined, (
        "runtime-base.Dockerfile must install openssh-client; Round 14 "
        "moved the install here so every derived image inherits ssh."
    )


def test_openclaw_dockerfile_does_not_reinstall_openssh_client() -> None:
    """openclaw.Dockerfile no longer needs its own openssh-client apt-install
    because the package is inherited from clawbench-runtime-base."""
    text = (DOCKER_DIR / "openclaw.Dockerfile").read_text()
    # Find every apt-get install line and check none of them re-installs
    # openssh-client.  Comments mentioning openssh-client are fine.
    for ln in text.splitlines():
        stripped = ln.lstrip()
        if stripped.startswith("#"):
            continue
        if "apt-get install" not in ln:
            continue
        assert "openssh-client" not in ln, (
            "openclaw.Dockerfile should not re-install openssh-client — "
            "it is inherited from clawbench-runtime-base.  Round 14 moved "
            "this install to the base image to avoid duplicating the "
            "layer across openclaw / nanobot / openclaw-edict."
        )
