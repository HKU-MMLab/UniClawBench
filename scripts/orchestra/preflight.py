"""Pre-dispatch worker readiness check.

The dispatcher runs this only when ``CLAWBENCH_RUN_PREFLIGHT=1`` is set
(or when an operator calls the module directly).  For every reachable worker,
it verifies:

  - All required docker image tags exist locally
    (clawbench-{runtime-base, openclaw, nanobot, codex, openclaw-edict}:latest)
  - Docker image IDs match the controller — best-effort, skipped if
    the controller doesn't have a docker daemon / images locally
  - All ``WORKER_APT_PACKAGES`` are installed
  - All ``WORKER_PIP_PACKAGES`` are installed in the configured worker python
  - Ports 9000, 9001, 9002 are listening

Behavior:
  - Unreachable workers (ssh probe fail / timeout) are LOGGED at WARNING and
    do NOT block dispatch — the dispatcher will simply route tasks elsewhere.
  - Reachable workers missing ANY required item raise ``PreflightError`` —
    the dispatcher exits with rc=1, printing a per-worker breakdown.

Rationale: silently dispatching to a worker that lacks the codex image (or
any other required dependency) results in every supervisor invocation
failing and the harness fabricating fake terminal verdicts.  Preflight makes
that class of cluster-wide misconfiguration fail before dispatch starts.
"""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field

from . import config as cfg_mod
from . import prepare_node

LOG = logging.getLogger("orchestra.preflight")

# Always-required worker docker tags (regardless of which backends are
# configured).  Runtime base + codex are used for the supervisor /
# user-simulator path.
_ALWAYS_REQUIRED_IMAGES: tuple[str, ...] = (
    "clawbench-runtime-base:latest",
    "clawbench-codex:latest",
)

# Backend-derived image tags (Round 12 follow-up): preflight used to
# hardcode the full list, which silently diverged from
# ``dispatch._ssh_worker_run``'s auto-generated image name.  The Round
# 11 + 12 edict bug ran for 2 rounds because dispatch.py constructed
# ``clawbench-openclaw_edict:latest`` (underscore from the backend key)
# while preflight only validated ``clawbench-openclaw-edict:latest``
# (hyphen, hardcoded).  Now we derive expected images from
# ``cfg.priorities[*].match.backend_in`` using the SAME hyphen-mapping
# dispatch.py uses, so the two sources of truth can never drift.

def _backend_to_image_tag(backend: str) -> str:
    """Mirror of dispatch.py's image-name generator.  Must stay in sync
    with ``_ssh_worker_run`` in ``dispatch.py``."""
    return f"clawbench-{backend.replace('_', '-')}:latest"


def expected_images_for_config(cfg: cfg_mod.OrchestraConfig) -> tuple[str, ...]:
    """Return the docker image tags that every reachable worker must have,
    derived from the configured backends + the always-required base set.

    Used both by ``preflight_check`` and (transitively) any test that
    wants to assert dispatch.py + preflight.py agree on image naming.
    """
    backends: set[str] = set()
    for prio in cfg.priorities:
        for backend in (prio.backend_in or ()):
            backends.add(backend)
    backend_images = {_backend_to_image_tag(b) for b in backends}
    configured_images = {
        img if ":" in img else f"{img}:latest"
        for img in getattr(cfg, "images", ())
    }
    return tuple(sorted(set(_ALWAYS_REQUIRED_IMAGES) | backend_images | configured_images))


# Legacy alias for callers that referenced ``REQUIRED_IMAGES`` before
# Round 12.  New code should use ``expected_images_for_config(cfg)``.
REQUIRED_IMAGES: tuple[str, ...] = (
    "clawbench-runtime-base:latest",
    "clawbench-openclaw:latest",
    "clawbench-nanobot:latest",
    "clawbench-codex:latest",
    "clawbench-openclaw-edict:latest",
)

# Short ssh timeout for the initial reachability probe; full checks use
# prepare_node._ssh's default (15s connect, ~60s total).
REACHABILITY_TIMEOUT_SECONDS = 8


@dataclass
class WorkerMissing:
    """What a single worker is missing.  Empty fields = OK on that axis."""
    worker_name: str
    ssh: str
    reachable: bool = True
    missing_images: list[str] = field(default_factory=list)
    image_id_mismatches: list[tuple[str, str, str]] = field(default_factory=list)
    """List of (tag, controller_image_id, worker_image_id) — only populated when both sides have the image."""
    missing_apt: list[str] = field(default_factory=list)
    missing_pip: list[str] = field(default_factory=list)
    missing_ports: list[int] = field(default_factory=list)

    def is_clean(self) -> bool:
        """True if no deps are missing.  Unreachable workers also report 'clean' —
        they're skipped, not failed."""
        if not self.reachable:
            return True
        return not (
            self.missing_images
            or self.image_id_mismatches
            or self.missing_apt
            or self.missing_pip
            or self.missing_ports
        )

    def summary_line(self) -> str:
        if not self.reachable:
            return f"  {self.worker_name} ({self.ssh}): UNREACHABLE (skipped, will not receive tasks)"
        if self.is_clean():
            return f"  {self.worker_name} ({self.ssh}): OK"
        parts: list[str] = []
        if self.missing_images:
            parts.append(f"missing images: {self.missing_images}")
        if self.image_id_mismatches:
            mm = ", ".join(
                f"{tag} (controller={mid[:19]} worker={wid[:19]})"
                for tag, mid, wid in self.image_id_mismatches
            )
            parts.append(f"image-ID mismatch: {mm}")
        if self.missing_apt:
            parts.append(f"missing apt: {self.missing_apt}")
        if self.missing_pip:
            parts.append(f"missing pip: {self.missing_pip}")
        if self.missing_ports:
            parts.append(f"ports not listening: {self.missing_ports}")
        return f"  {self.worker_name} ({self.ssh}): " + "; ".join(parts)


class PreflightError(RuntimeError):
    """Raised when one or more reachable workers are missing required deps."""

    def __init__(self, problems: list[WorkerMissing]):
        self.problems = problems
        lines = ["Preflight failed — fix before dispatching:"]
        lines.extend(p.summary_line() for p in problems)
        super().__init__("\n".join(lines))


# --------------------------------------------------------------------------
# Single-worker checks (each returns the missing items as a list).
# --------------------------------------------------------------------------

def _ssh_probe(host: str) -> bool:
    """Lightweight reachability check.  True if ssh succeeds, False otherwise."""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", f"ConnectTimeout={REACHABILITY_TIMEOUT_SECONDS}",
                "-o", "BatchMode=yes",
                host,
                "true",
            ],
            capture_output=True,
            timeout=REACHABILITY_TIMEOUT_SECONDS + 2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _local_image_ids(images: tuple[str, ...]) -> dict[str, str]:
    """Query the controller's local docker daemon for each tag's image ID.

    Returns ``{tag: "sha256:..."}`` for tags present locally.  Tags missing
    locally are simply absent from the returned dict (digest comparison is
    skipped for those tags — only tag-presence is enforced on workers).
    """
    out: dict[str, str] = {}
    for tag in images:
        try:
            r = subprocess.run(
                ["docker", "image", "inspect", tag, "--format", "{{.Id}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
        if r.returncode == 0 and r.stdout.strip().startswith("sha256:"):
            out[tag] = r.stdout.strip()
    return out


def _worker_image_ids(host: str, images: tuple[str, ...]) -> dict[str, str | None]:
    """Query a worker for each tag's image ID over SSH.

    Returns ``{tag: "sha256:..." or None}`` — None means the tag is not
    present on the worker.
    """
    out: dict[str, str | None] = {}
    cmd_lines = []
    for tag in images:
        cmd_lines.append(f"echo {shlex.quote(tag)}")
        cmd_lines.append(
            f"docker image inspect {shlex.quote(tag)} --format '{{{{.Id}}}}' 2>/dev/null"
            " || echo MISSING"
        )
    cmd = "; ".join(cmd_lines)
    r = prepare_node._ssh(host, cmd, timeout=60)
    lines = r.stdout.splitlines()
    i = 0
    while i + 1 < len(lines):
        tag = lines[i].strip()
        value = lines[i + 1].strip()
        if value == "MISSING" or not value.startswith("sha256:"):
            out[tag] = None
        else:
            out[tag] = value
        i += 2
    return out


def _check_apt(host: str) -> list[str]:
    """Return the apt packages that are NOT installed on the worker."""
    pkgs = " ".join(shlex.quote(p) for p in prepare_node.WORKER_APT_PACKAGES)
    cmd = (
        "for p in " + pkgs + "; do "
        r'  dpkg-query -W -f="${db:Status-Status}\n" "$p" 2>/dev/null '
        r'    | grep -q "^installed$" || echo "$p"; '
        "done"
    )
    r = prepare_node._ssh(host, cmd, timeout=120)
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def _check_pip(host: str, *, worker_python: str | None = None) -> list[str]:
    """Return the pip packages that are NOT installed in the worker venv.

    If the worker python itself is missing, ALL packages are returned as missing
    (the worker fundamentally cannot run anything until prepare_node fixes it).
    """
    pkgs = list(prepare_node.WORKER_PIP_PACKAGES)
    worker_python = worker_python or f"{prepare_node.WORKER_VENV_PATH}/bin/python"
    q_python = shlex.quote(worker_python)
    cmd = (
        f"if [ ! -x {q_python} ]; then echo VENV_MISSING; exit 0; fi; "
        f"{q_python} -m pip list --format=freeze 2>/dev/null | cut -d= -f1 | tr A-Z a-z"
    )
    r = prepare_node._ssh(host, cmd, timeout=60)
    if "VENV_MISSING" in r.stdout:
        return pkgs  # all of them; venv itself is missing
    installed = {line.strip().lower() for line in r.stdout.splitlines() if line.strip()}
    return [p for p in pkgs if p.lower() not in installed]


def _check_ports(host: str) -> list[int]:
    """Return the required listening ports that are NOT listening on the worker."""
    cmd = (
        "ss -tlnp 2>/dev/null | awk '{print $4}'"
        " | grep -E ':(9000|9001|9002)$' | sort -u"
    )
    r = prepare_node._ssh(host, cmd, timeout=15)
    listening: set[int] = set()
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            listening.add(int(line.rsplit(":", 1)[-1]))
        except ValueError:
            continue
    return [p for p in prepare_node.REQUIRED_LISTEN_PORTS if p not in listening]


def check_one_worker(
    worker: cfg_mod.WorkerCfg,
    *,
    controller_image_ids: dict[str, str],
    required_images: tuple[str, ...] | None = None,
    worker_python: str | None = None,
) -> WorkerMissing:
    """Probe a single worker; return what (if anything) is missing.

    Round 12 follow-up: ``required_images`` is now an explicit argument
    (derived from cfg.backends via ``expected_images_for_config``) so
    preflight and ``dispatch._ssh_worker_run`` use the same image-naming
    logic.  Falls back to the legacy hardcoded list if omitted (for
    backwards compatibility with callers that haven't been updated).
    """
    if required_images is None:
        required_images = REQUIRED_IMAGES
    result = WorkerMissing(worker_name=worker.name, ssh=worker.ssh)
    if not _ssh_probe(worker.ssh):
        result.reachable = False
        return result

    # Images: missing tags + digest mismatches
    worker_ids = _worker_image_ids(worker.ssh, required_images)
    for tag in required_images:
        wid = worker_ids.get(tag)
        if wid is None:
            result.missing_images.append(tag)
            continue
        # Only flag mismatch when BOTH sides have a valid id; the controller
        # may not have docker, in which case digest check is
        # best-effort and we only enforce tag presence.
        mid = controller_image_ids.get(tag)
        if mid and wid != mid:
            result.image_id_mismatches.append((tag, mid, wid))

    # Apt / pip / ports
    result.missing_apt = _check_apt(worker.ssh)
    result.missing_pip = _check_pip(worker.ssh, worker_python=worker_python)
    result.missing_ports = _check_ports(worker.ssh)

    return result


# --------------------------------------------------------------------------
# Top-level entry point used by dispatch.py
# --------------------------------------------------------------------------

def preflight_check(cfg: cfg_mod.OrchestraConfig) -> list[WorkerMissing]:
    """Run preflight on every non-skip worker in the config.

    Raises ``PreflightError`` if any reachable worker is missing required
    dependencies.  Returns the list of per-worker results (including
    unreachable ones, which are marked but do NOT block) so callers can
    inspect / log details.

    Round 12 follow-up: image list is derived from ``cfg.priorities[*]
    .match.backend_in`` (via ``expected_images_for_config``) using the
    same underscore→hyphen mapping as ``dispatch.py``'s
    ``_ssh_worker_run``.  If the dispatcher would request an image at
    runtime, preflight validates the SAME name, eliminating the kind of
    silent drift that hid the Round 11+12 edict image bug.
    """
    required_images = expected_images_for_config(cfg)
    LOG.info(
        "preflight: validating %d required image(s) on each worker: %s",
        len(required_images), list(required_images),
    )

    controller_image_ids = _local_image_ids(required_images)
    if not controller_image_ids:
        LOG.warning(
            "preflight: controller has no clawbench-* docker images locally — "
            "image-ID digest comparison will be skipped (workers checked only "
            "for tag presence)."
        )

    all_results: list[WorkerMissing] = []
    problems: list[WorkerMissing] = []

    for worker in cfg.workers:
        if worker.skip:
            LOG.info("preflight: %s skipped (config skip=true)", worker.name)
            continue
        LOG.info("preflight: checking %s (%s) ...", worker.name, worker.ssh)
        result = check_one_worker(
            worker, controller_image_ids=controller_image_ids,
            required_images=required_images,
            worker_python=cfg_mod.worker_python_for(worker, cfg),
        )
        all_results.append(result)
        if not result.reachable:
            LOG.warning(
                "preflight: %s UNREACHABLE — dispatcher will skip; "
                "if you expect to dispatch to %s, fix ssh access first",
                worker.name, worker.name,
            )
            continue
        if result.is_clean():
            LOG.info("preflight: %s OK", worker.name)
        else:
            problems.append(result)
            LOG.error("preflight: %s has problems: %s", worker.name, result.summary_line())

    if problems:
        raise PreflightError(problems)
    return all_results


if __name__ == "__main__":
    # CLI for manual preflight invocation (without starting the dispatcher).
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Clawbench worker preflight check")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    cfg = cfg_mod.load(args.config)
    try:
        results = preflight_check(cfg)
    except PreflightError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    print("Preflight passed.  Worker status:")
    for r in results:
        print(r.summary_line())
    sys.exit(0)
