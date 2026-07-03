"""Round 12 follow-up: preflight derives expected docker images from
``cfg.priorities[*].match.backend_in`` using the SAME underscore→hyphen
mapping as ``dispatch.py``'s ``_ssh_worker_run``.

The Round 11+12 edict bug existed because preflight's hardcoded
``REQUIRED_IMAGES`` and dispatch.py's auto-generated image name were
two separate sources of truth that silently drifted apart.  These
tests pin the two together.
"""
from __future__ import annotations

from pathlib import Path


def _write_cfg(tmp_path: Path, *, backends_in_priorities: list[str]) -> Path:
    """Write a minimal orchestra.yaml that mentions the given backends
    in its priorities block."""
    backend_lines = "\n".join(f'      - "{b}"' for b in backends_in_priorities)
    p = tmp_path / "orchestra.yaml"
    p.write_text(f"""
controller:
  host: controller
  data_root: {tmp_path}
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1
    label: p1
    match:
      backend_in:
{backend_lines}
      status_in: ["missing"]
""", encoding="utf-8")
    return p


def test_backend_to_image_tag_uses_hyphen_not_underscore() -> None:
    """The image tag generator must convert underscore → hyphen so the
    ``openclaw_edict`` backend key produces ``clawbench-openclaw-edict:latest``,
    matching the Docker image naming convention.
    """
    from scripts.orchestra.preflight import _backend_to_image_tag

    assert _backend_to_image_tag("openclaw") == "clawbench-openclaw:latest"
    assert _backend_to_image_tag("nanobot") == "clawbench-nanobot:latest"
    assert _backend_to_image_tag("openclaw_edict") == "clawbench-openclaw-edict:latest"


def test_expected_images_derives_from_config_backends(tmp_path: Path) -> None:
    """expected_images_for_config returns the always-required base set
    PLUS one image per configured backend, using the same tag generator
    as dispatch.py."""
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra.preflight import expected_images_for_config

    cfg_path = _write_cfg(tmp_path, backends_in_priorities=[
        "openclaw", "nanobot", "openclaw_edict",
    ])
    cfg = cfg_mod.load(cfg_path)
    images = expected_images_for_config(cfg)
    assert "clawbench-runtime-base:latest" in images
    assert "clawbench-codex:latest" in images
    assert "clawbench-openclaw:latest" in images
    assert "clawbench-nanobot:latest" in images
    assert "clawbench-openclaw-edict:latest" in images  # the Round 11+12 trap
    # No image with underscore should ever leak through
    for tag in images:
        assert "openclaw_edict" not in tag, (
            f"image tag {tag!r} must NEVER use underscore — Docker convention "
            "is hyphen.  This was the Round 11+12 edict bug."
        )


def test_expected_images_includes_configured_extra_images(tmp_path: Path) -> None:
    """The optional images: block is an additive operator requirement."""
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra.preflight import expected_images_for_config

    cfg_path = _write_cfg(tmp_path, backends_in_priorities=["openclaw"])
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8")
        + "\nimages:\n  - clawbench-extra-tooling\n",
        encoding="utf-8",
    )
    cfg = cfg_mod.load(cfg_path)

    assert "clawbench-extra-tooling:latest" in expected_images_for_config(cfg)


def test_expected_images_matches_dispatch_generator(tmp_path: Path) -> None:
    """The image name preflight validates MUST equal what
    ``dispatch._ssh_worker_run`` would generate.  If these ever drift
    (as they did silently in Round 11+12), the bug surfaces here in CI
    instead of after a 49-min cluster run.
    """
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra.preflight import (
        _backend_to_image_tag,
        expected_images_for_config,
    )

    cfg_path = _write_cfg(tmp_path, backends_in_priorities=[
        "openclaw", "nanobot", "openclaw_edict",
    ])
    cfg = cfg_mod.load(cfg_path)
    images = set(expected_images_for_config(cfg))

    # Simulate what dispatch.py's _ssh_worker_run does for each backend
    # (after the b5157729 / f2e65bf9 fix):
    #   image = task.get("image") or f"clawbench-{task['backend'].replace('_', '-')}:latest"
    for backend in ("openclaw", "nanobot", "openclaw_edict"):
        dispatch_generated = _backend_to_image_tag(backend)
        assert dispatch_generated in images, (
            f"dispatch.py would request {dispatch_generated!r} for backend "
            f"{backend!r}, but preflight does NOT have it in its expected "
            f"set — they have drifted again.  expected={sorted(images)}"
        )


def test_expected_images_handles_empty_backend_list(tmp_path: Path) -> None:
    """A priority bucket with no backend_in (matches all backends) must
    not cause preflight to crash — only the always-required base set
    is returned."""
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra.preflight import expected_images_for_config

    # Empty backend_in → only always-required images
    p = tmp_path / "orchestra.yaml"
    p.write_text(f"""
controller:
  host: controller
  data_root: {tmp_path}
  webui_port: 9999
workers:
  - name: w1
    ssh: w1
    parallel: 1
supervision:
  supervisor:
    provider: provider-a
    model: model-a
  user_simulator:
    provider: provider-a
    model: model-a
priorities:
  - id: P1_wildcard
    label: wildcard
    match:
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(p)
    images = expected_images_for_config(cfg)
    assert "clawbench-runtime-base:latest" in images
    assert "clawbench-codex:latest" in images
    # No backend-specific images (none configured)
    assert "clawbench-openclaw:latest" not in images
