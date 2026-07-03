"""Idempotently provision a worker node so it can run any Clawbench task.

This module is invoked from the controller: it SSHes into a worker and:

  1. Installs the apt packages every task setup script collectively needs
     (ffmpeg, libreoffice, pandoc, imagemagick, tesseract-ocr, …).  See
     ``WORKER_APT_PACKAGES`` for the full list.  Skips any package already
     present.
  2. Creates / refreshes the Python venv used by ``worker_python`` (default:
     ``/opt/clawbench-venv``) from ``requirements.txt`` so workers don't
     pollute the global interpreter.
  3. Verifies that the Clawbench docker tags referenced by the orchestra
     config are present, loading them from a shared tarball directory if
     missing.
  4. Optionally verifies local proxy/adapter ports when ``--check-ports`` is
     passed. Fresh workers commonly run this preparation step before those
     services are listening.

The list lives next to the orchestrator so it can evolve alongside the
task suite — add a new dependency once tasks/ requires it, and every
re-run of ``prepare_node`` will fix it across the cluster.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import config as cfg_mod

# --------------------------------------------------------------------------
# Curated install lists — pulled from a tasks/ + injection/ scan
# (see refactor docs).  Keep alphabetical for diff hygiene.
# --------------------------------------------------------------------------
WORKER_APT_PACKAGES: tuple[str, ...] = (
    "calibre",
    "chromium-browser",
    "chromium-browser-l10n",
    "dbus-x11",
    "ffmpeg",
    "fonts-dejavu-core",
    "fonts-liberation",
    "fonts-noto-cjk",
    "fonts-noto-color-emoji",
    "fonts-wqy-zenhei",
    "gh",
    "git",
    "git-lfs",
    "gnome-screenshot",
    "gnupg",
    "imagemagick",
    "inkscape",
    "jq",
    "libreoffice",
    "libreoffice-core",
    "libreoffice-gtk3",
    "libreoffice-script-provider-python",
    "neovim",
    "novnc",
    "pandoc",
    "poppler-utils",
    "ripgrep",
    "scrot",
    "socat",
    "sqlite3",
    "tesseract-ocr",
    "tesseract-ocr-chi-sim",
    "tesseract-ocr-deu",
    "tesseract-ocr-eng",
    "tmux",
    "websockify",
    "wmctrl",
    "x11vnc",
    "xauth",
    "xdotool",
    "xvfb",
    "yt-dlp",
    "zsh",
)

WORKER_PIP_PACKAGES: tuple[str, ...] = (
    "duckduckgo-search",
    "opencv-python-headless",
    "openpyxl",
    "pikepdf",
    "pillow",
    "pyautogui",
    "pyexcel-ods3",
    "pygetwindow",
    "pypdf",
    "PyYAML",
)

# Default required docker tags when no orchestra config is supplied.
# This MUST stay in sync with ``preflight.REQUIRED_IMAGES`` and
# ``preflight._backend_to_image_tag``.  The Round 11+12 edict bug ran
# silently for two rounds because ``REQUIRED_DOCKER_TAGS`` here omitted
# ``clawbench-openclaw-edict:latest`` while preflight + dispatch.py
# both expected it.  Round 14 surfaces the same drift class: keep the
# full canonical list here and prefer ``required_docker_tags_for_cfg``
# (below) when a config is available so the two sources can't drift.
REQUIRED_DOCKER_TAGS: tuple[str, ...] = (
    "clawbench-runtime-base:latest",
    "clawbench-openclaw:latest",
    "clawbench-nanobot:latest",
    "clawbench-codex:latest",
    "clawbench-openclaw-edict:latest",
)


def required_docker_tags_for_cfg(cfg: cfg_mod.OrchestraConfig) -> tuple[str, ...]:
    """Derive the docker tags this worker needs from the orchestra config.

    Delegates to ``preflight.expected_images_for_config`` so prepare_node
    and preflight agree on naming.  Use this in place of the static
    ``REQUIRED_DOCKER_TAGS`` whenever a config is at hand — the Round 11+12
    edict bug (silent drift between hardcoded lists) cannot recur if both
    callsites read from the same generator."""
    # Local import to avoid a hard cycle at module load time
    # (preflight imports prepare_node for the apt/pip helpers).
    from . import preflight as _preflight
    return _preflight.expected_images_for_config(cfg)

REQUIRED_LISTEN_PORTS: tuple[int, ...] = (9000, 9001, 9002)

WORKER_VENV_PATH = "/opt/clawbench-venv"
DEFAULT_REMOTE_REPO = cfg_mod.DEFAULT_WORKER_REPO


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


def _ssh(host: str, cmd: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", host, cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _scp(local: Path, host: str, remote: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["scp", "-o", "ConnectTimeout=15", str(local), f"{host}:{remote}"],
        capture_output=True,
        text=True,
    )


def _step_apt(host: str) -> StepResult:
    pkgs = " ".join(shlex.quote(p) for p in WORKER_APT_PACKAGES)
    cmd = (
        "set -e; export DEBIAN_FRONTEND=noninteractive; "
        "apt-get update -qq; "
        f"apt-get install -yqq --no-install-recommends {pkgs} 2>&1 | tail -5"
    )
    r = _ssh(host, cmd, timeout=1800)
    return StepResult("apt", r.returncode == 0, r.stdout.strip()[-200:])


def _venv_path_from_worker_python(worker_python: str) -> str | None:
    """Return the venv root managed by prepare_node for a worker python path.

    The orchestrator's default worker python is ``<venv>/bin/python``.  Custom
    configs can point at another venv, and prepare/preflight should follow that
    same path.  If an operator points at a non-venv interpreter, require them
    to manage it externally and run prepare_node with ``--skip venv``.
    """
    py = PurePosixPath(worker_python)
    if py.parent.name != "bin" or not py.name.startswith("python"):
        return None
    return str(py.parent.parent)


def _step_venv(host: str, requirements_remote: str, *, worker_python: str | None = None) -> StepResult:
    worker_python = worker_python or f"{WORKER_VENV_PATH}/bin/python"
    venv_path = _venv_path_from_worker_python(worker_python)
    if venv_path is None:
        return StepResult(
            "venv",
            False,
            f"worker_python {worker_python!r} is not a managed <venv>/bin/python path; use --skip venv",
        )
    q_venv = shlex.quote(venv_path)
    q_python = shlex.quote(worker_python)
    cmd = (
        f"python3 -m venv --upgrade-deps {q_venv} 2>&1 | tail -2 && "
        f"{q_python} -m pip install --quiet --upgrade pip wheel 2>&1 | tail -2 && "
        f"{q_python} -m pip install --quiet -r {shlex.quote(requirements_remote)} 2>&1 | tail -5 && "
        f"{q_python} -m pip install --quiet "
        + " ".join(shlex.quote(p) for p in WORKER_PIP_PACKAGES)
        + " 2>&1 | tail -5"
    )
    r = _ssh(host, cmd, timeout=1800)
    return StepResult("venv", r.returncode == 0, r.stdout.strip()[-200:])


def _step_docker_tags(
    host: str,
    image_dir: Path | None,
    required_tags: tuple[str, ...] = REQUIRED_DOCKER_TAGS,
) -> StepResult:
    cmd = (
        "for tag in "
        + " ".join(shlex.quote(t) for t in required_tags)
        + r'; do docker image inspect "$tag" >/dev/null 2>&1 || echo "MISSING $tag"; done'
    )
    r = _ssh(host, cmd)
    missing = [
        line.split(" ", 1)[1]
        for line in r.stdout.splitlines()
        if line.startswith("MISSING ")
    ]
    if not missing:
        return StepResult("docker", True, f"all {len(required_tags)} images present")
    if image_dir is None:
        return StepResult(
            "docker",
            False,
            f"missing: {', '.join(missing)} (no --image-dir to load from; "
            f"run scripts/orchestra/build_images.sh on a build host first)",
        )
    # Push each missing tag's tar.gz from the controller via stdin → docker load.
    failed: list[str] = []
    for tag in missing:
        name = tag.split(":", 1)[0]
        tar = image_dir / f"{name}.tar.gz"
        if not tar.exists():
            failed.append(f"{tag} (no tar)")
            continue
        load_cmd = ["ssh", host, "gunzip | docker load"]
        with tar.open("rb") as fh:
            r2 = subprocess.run(load_cmd, stdin=fh, capture_output=True, text=True)
        if r2.returncode != 0:
            failed.append(f"{tag} (load rc={r2.returncode})")
    if failed:
        return StepResult("docker", False, "; ".join(failed))
    return StepResult("docker", True, f"loaded {len(missing)} images")


def _step_ports(host: str) -> StepResult:
    cmd = "ss -tlnp 2>/dev/null | awk '{print $4}' | grep -E ':(9000|9001|9002)$' | sort -u"
    r = _ssh(host, cmd)
    listening = {line.split(":")[-1] for line in r.stdout.splitlines() if line}
    missing = [str(p) for p in REQUIRED_LISTEN_PORTS if str(p) not in listening]
    if not missing:
        return StepResult("ports", True, "9000-9002 OK")
    return StepResult("ports", False, f"not listening: {', '.join(missing)}")


def _step_sync_repo(host: str, local_repo: Path, remote_repo: str) -> StepResult:
    """rsync only the slice of the repo a worker actually needs to run a task.

    We use an explicit allow-list (``--include=<dir>/***`` + ``--exclude=*``)
    rather than a deny-list with ``--exclude='.git'``.  The deny-list pattern
    is a foot-gun: rsync ``--exclude='.git'`` (no leading slash) recursively
    matches **every** ``.git`` directory in the tree, which silently strips
    the nested ``.git`` inside submodules like ``build/libsignal-node/.git``.
    Round 14's ad-hoc rsync hit exactly this; the openclaw image build then
    failed with "/tmp/libsignal-node does not appear to be a git repository".
    The fix is either:
      - allow-list (this function): no chance of accidentally stripping
        nested ``.git`` because we only include the dirs we name; OR
      - if you ever switch to a deny-list pattern, use the anchored form
        ``--exclude='/.git'`` (leading slash) so only the **root** ``.git``
        is excluded and submodules' ``.git`` is preserved.
    """
    cmd = [
        "rsync",
        "-az",
        "--delete",
        "--include=lib/***",
        "--include=scripts/***",
        "--include=tasks/***",
        "--include=injection/***",
        "--include=configs/***",
        "--include=docker/***",
        "--include=requirements.txt",
        "--include=pyproject.toml",
        "--include=README.md",
        "--exclude=*",
        f"{local_repo}/",
        f"{host}:{remote_repo}/",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    return StepResult("repo-sync", r.returncode == 0, r.stderr.strip()[-200:])


def prepare(
    host: str,
    *,
    local_repo: Path,
    remote_repo: str,
    image_dir: Path | None,
    skip: tuple[str, ...] = (),
    required_tags: tuple[str, ...] = REQUIRED_DOCKER_TAGS,
    worker_python: str | None = None,
) -> list[StepResult]:
    results: list[StepResult] = []

    if "repo-sync" not in skip:
        results.append(_step_sync_repo(host, local_repo, remote_repo))

    if "apt" not in skip:
        results.append(_step_apt(host))

    if "venv" not in skip:
        # Push requirements.txt (in case it changed) and run the venv step.
        req_local = local_repo / "requirements.txt"
        if req_local.exists():
            _scp(req_local, host, f"{remote_repo}/requirements.txt")
            results.append(_step_venv(host, f"{remote_repo}/requirements.txt", worker_python=worker_python))
        else:
            results.append(StepResult("venv", False, "requirements.txt missing"))

    if "docker" not in skip:
        results.append(_step_docker_tags(host, image_dir, required_tags=required_tags))

    if "ports" not in skip:
        results.append(_step_ports(host))

    return results


def remote_repo_for_worker(
    worker: cfg_mod.WorkerCfg,
    cfg: cfg_mod.OrchestraConfig,
    *,
    override: str | None = None,
) -> str:
    """Resolve the checkout path used on a worker.

    The orchestra config is the source of truth for worker checkout paths:
    per-worker ``repo`` wins, then global ``worker_repo``.  ``--remote-repo``
    stays as an explicit operator override for one-off migrations.
    """
    return cfg_mod.worker_repo_for(worker, cfg, override=override)


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a Clawbench worker node")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--node", help="single worker name; if omitted, prepare all")
    parser.add_argument("--local-repo", required=True, type=Path)
    parser.add_argument(
        "--remote-repo",
        default=None,
        help="override worker checkout path; default resolves from worker.repo, "
        "then global worker_repo, then /opt/clawbench/Clawbench",
    )
    parser.add_argument(
        "--image-dir", type=Path, default=None,
        help="dir on controller containing <image>.tar.gz to seed missing tags",
    )
    parser.add_argument(
        "--skip", action="append", default=[],
        help="repeatable; skip one of: repo-sync, apt, venv, docker, ports",
    )
    parser.add_argument(
        "--check-ports", action="store_true",
        help="also require local proxy/adapter ports 9000-9002 to be listening "
             "(off by default because fresh workers are usually prepared before "
             "adapter prewarm starts)",
    )
    args = parser.parse_args()

    cfg = cfg_mod.load(args.config)
    targets = (
        [w for w in cfg.workers if not w.skip]
        if not args.node
        else [w for w in cfg.workers if w.name == args.node]
    )
    if not targets:
        print(f"no worker matched node={args.node!r}", file=sys.stderr)
        return 2

    required_tags = required_docker_tags_for_cfg(cfg)
    skip = set(args.skip)
    if not args.check_ports:
        skip.add("ports")
    overall_ok = True
    for w in targets:
        print(f"\n=== {w.name} ({w.ssh}) ===")
        results = prepare(
            w.ssh,
            local_repo=args.local_repo,
            remote_repo=remote_repo_for_worker(w, cfg, override=args.remote_repo),
            image_dir=args.image_dir,
            skip=tuple(skip),
            required_tags=required_tags,
            worker_python=cfg_mod.worker_python_for(w, cfg),
        )
        for r in results:
            badge = "OK " if r.ok else "FAIL"
            print(f"  [{badge}] {r.name:<10} {r.detail}")
            overall_ok = overall_ok and r.ok
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
