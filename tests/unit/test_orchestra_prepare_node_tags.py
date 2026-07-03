"""Round 14 follow-up: prepare_node.REQUIRED_DOCKER_TAGS must include
clawbench-openclaw-edict:latest and stay aligned with preflight.

Before R14 this list was missing the openclaw-edict tag, which meant a
worker provisioned via ``python -m scripts.orchestra.prepare_node`` and
then asked to run an edict task would silently fail with a missing
image, just like the Round 11+12 edict-image drift.  This test pins the
two sources of truth together.
"""
from __future__ import annotations

from pathlib import Path


def test_prepare_node_required_docker_tags_includes_edict() -> None:
    """The static fallback list must include all 5 canonical images."""
    from scripts.orchestra.prepare_node import REQUIRED_DOCKER_TAGS

    expected = {
        "clawbench-runtime-base:latest",
        "clawbench-openclaw:latest",
        "clawbench-nanobot:latest",
        "clawbench-codex:latest",
        "clawbench-openclaw-edict:latest",
    }
    missing = expected - set(REQUIRED_DOCKER_TAGS)
    assert not missing, (
        f"prepare_node.REQUIRED_DOCKER_TAGS is missing {missing!r}.  "
        "This is the same class of bug as the Round 11+12 edict drift: "
        "preflight expects the tag, dispatch.py expects the tag, but "
        "prepare_node would skip installing it.  Keep the canonical "
        "5-image set listed here and in preflight.REQUIRED_IMAGES."
    )


def test_prepare_node_required_tags_match_preflight() -> None:
    """The fallback list in prepare_node must equal preflight's canonical
    list, so a worker provisioned manually has the same image set the
    runtime preflight would require."""
    from scripts.orchestra.prepare_node import REQUIRED_DOCKER_TAGS
    from scripts.orchestra.preflight import REQUIRED_IMAGES

    assert set(REQUIRED_DOCKER_TAGS) == set(REQUIRED_IMAGES), (
        "prepare_node.REQUIRED_DOCKER_TAGS and preflight.REQUIRED_IMAGES "
        "must be the same canonical set.  If you add a new image, update "
        "both lists in the same commit."
    )


def test_required_docker_tags_for_cfg_uses_preflight_generator(tmp_path: Path) -> None:
    """Config-driven entry point (``required_docker_tags_for_cfg``) must
    delegate to ``preflight.expected_images_for_config`` so the two
    callsites never diverge."""
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra.prepare_node import required_docker_tags_for_cfg
    from scripts.orchestra.preflight import expected_images_for_config

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
      backend_in: ["openclaw", "openclaw_edict"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(p)
    tags_via_prepare = required_docker_tags_for_cfg(cfg)
    tags_via_preflight = expected_images_for_config(cfg)
    assert tags_via_prepare == tags_via_preflight


def test_prepare_node_remote_repo_resolves_from_config(tmp_path: Path) -> None:
    """prepare_node must sync to the same worker checkout path dispatch uses."""
    from scripts.orchestra import config as cfg_mod
    from scripts.orchestra.prepare_node import DEFAULT_REMOTE_REPO, remote_repo_for_worker

    p = tmp_path / "orchestra.yaml"
    p.write_text(f"""
controller:
  host: controller
  data_root: {tmp_path}
  webui_port: 9999
worker_repo: /srv/clawbench/shared
workers:
  - name: w1
    ssh: w1
    parallel: 1
  - name: w2
    ssh: w2
    repo: /srv/clawbench/custom
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
      backend_in: ["openclaw"]
      status_in: ["missing"]
""", encoding="utf-8")
    cfg = cfg_mod.load(p)

    assert remote_repo_for_worker(cfg.workers[0], cfg) == "/srv/clawbench/shared"
    assert remote_repo_for_worker(cfg.workers[1], cfg) == "/srv/clawbench/custom"
    assert remote_repo_for_worker(cfg.workers[1], cfg, override="/tmp/override") == "/tmp/override"

    cfg_without_default = cfg_mod.OrchestraConfig(
        controller=cfg.controller,
        workers=cfg.workers,
        priorities=cfg.priorities,
        model_caps=cfg.model_caps,
        default_model_cap=cfg.default_model_cap,
        images=cfg.images,
        supervision=cfg.supervision,
        raw={},
    )
    assert remote_repo_for_worker(cfg.workers[0], cfg_without_default) == DEFAULT_REMOTE_REPO


def test_sync_repo_uses_allowlist_not_dotgit_denylist() -> None:
    """The ``_step_sync_repo`` rsync command MUST use an include-allow-list,
    never an unanchored ``--exclude=.git`` deny-list.

    Round 14 hit this bug operationally: an ad-hoc rsync used
    ``--exclude='.git'`` (no leading slash), which recursively matches
    every ``.git`` in the tree.  That stripped the nested ``.git`` from
    ``build/libsignal-node/`` and broke openclaw image builds with
    "/tmp/libsignal-node does not appear to be a git repository".

    The fix is permanent in this codepath because we never named ``.git``
    in the deny clause — but pinning the contract here prevents a future
    "simplify" refactor from accidentally switching to a deny-list.
    """
    from scripts.orchestra import prepare_node
    import inspect

    src = inspect.getsource(prepare_node._step_sync_repo)
    # Must use include-style allow-list pattern.
    assert "--include=tasks/***" in src

    # Inspect only the body of the function (after the docstring) so the
    # foot-gun mentioned in the docstring as a warning doesn't falsely
    # trip these checks.  We split on the closing triple-quote.
    body = src.split('"""', 2)[-1] if '"""' in src else src

    # The actual rsync command body must NEVER use the unanchored deny pattern.
    assert "--exclude='.git'" not in body
    assert '--exclude=".git"' not in body
    assert "--exclude=.git" not in body

    # If a deny pattern is ever added in the future, it MUST be anchored
    # (leading slash so only the repo-root .git is excluded).  We pin the
    # docstring (which is the only place the unanchored pattern legitimately
    # appears, as a warning) still documents the anchored form.
    doc = prepare_node._step_sync_repo.__doc__ or ""
    assert "/.git" in doc, (
        "_step_sync_repo docstring should still document the anchored "
        "--exclude='/.git' pattern as the only safe deny-list form, "
        "and warn about the unanchored '.git' foot-gun.  Round 14's "
        "rsync .git bug hides here."
    )
