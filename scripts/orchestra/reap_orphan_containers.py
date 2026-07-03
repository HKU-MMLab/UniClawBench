#!/usr/bin/env python3
"""Reap RUNNING orphan containers — a container whose task is NOT in its
worker's current inflight claims.  Orphans are killed/timed-out cells whose GUI
container outlived the per-task cleanup (`_wait_for_containers_gone` only reaps
the current task on a clean worker_runner exit; a SIGKILL'd / watchdog-killed /
wsl--shutdown-rescued cell leaks its container).  They hold memory and drive the
WSL freezes.

Two safety rails:
  * **case-INSENSITIVE** task match — `slugify` lowercases the container name
    (clawbench-task_203_19_rl_blog-...) while the inflight claim keeps the
    original task_id case (task_203_19_RL_blog).  Comparing case-sensitively
    would falsely flag an ACTIVE cell as an orphan and kill it.
  * **age guard** — skip containers younger than the dispatch race window
    (RunningFor still measured in "seconds"); their claim row may not be written
    yet.

Dry-run by default; pass --apply to docker rm -f the identified orphans.
Run on the controller; the script SSHes to each non-skipped worker from
``configs/orchestra.local.yaml``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Import the orchestra config loader the same way the other scripts/orchestra
# tools do (they run as ``python3 scripts/orchestra/<tool>.py`` from the repo
# root). Add the repo root to sys.path so ``scripts.orchestra.config`` resolves
# regardless of CWD.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.orchestra import config as cfg_mod  # noqa: E402

# Default config path, mirroring scripts/orchestra/__init__.py's loader
# convention (configs/orchestra.local.yaml is the gitignored per-instance file).
DEFAULT_CONFIG = _REPO_ROOT / "configs" / "orchestra.local.yaml"

_NAME_RE = re.compile(r"clawbench-(task_[0-9]+_[0-9]+[a-z0-9_]*)-session")


def claims_by_worker(inflight: Path) -> dict[str, set[str]]:
    d: dict[str, set[str]] = defaultdict(set)
    if not Path(inflight).exists():
        return d
    for line in Path(inflight).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        w = r.get("worker")
        t = (r.get("task") or "").lower()
        if w and t:
            d[w].add(t)
    return d


def worker_containers(w: str):
    """Return [(id, running_for, task_lower)] or None if unreachable."""
    try:
        r = subprocess.run(
            ["ssh", "-n", "-o", "ConnectTimeout=12", w,
             "docker ps --filter name=clawbench --format '{{.ID}}|{{.RunningFor}}|{{.Names}}'"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        cid, rf, name = parts[0], parts[1], parts[2]
        m = _NAME_RE.search(name.lower())
        out.append((cid, rf, m.group(1) if m else None))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help=f"orchestra config YAML (default: {DEFAULT_CONFIG})",
    )
    args = ap.parse_args(argv)

    cfg = cfg_mod.load(args.config)
    workers = [w for w in cfg.workers if not w.skip]
    # inflight.jsonl lives in the controller's in-tree runtime/ dir, the same
    # path dispatch.py / stats.py use (cfg_mod.runtime_dir() ->
    # scripts/orchestra/runtime/).
    INFLIGHT = cfg_mod.runtime_dir() / "inflight.jsonl"

    claims = claims_by_worker(INFLIGHT)
    total_orphans = 0
    for worker in workers:
        cs = worker_containers(worker.ssh)
        label = worker.name if worker.name == worker.ssh else f"{worker.name} ({worker.ssh})"
        if cs is None:
            print(f"  {label}: UNREACHABLE (skip)")
            continue
        # Inflight rows store the logical worker name, not necessarily the SSH
        # alias.  Configs often use a stable name with a different SSH target;
        # mixing the two would make active tasks look orphaned.
        cl = claims.get(worker.name, set())
        # orphan: task parsed, NOT in claims (case-insensitive), and not brand-new
        orphans = [
            (cid, rf, t) for (cid, rf, t) in cs
            if t and t not in cl and "second" not in rf.lower()
        ]
        total_orphans += len(orphans)
        print(f"  {label}: containers={len(cs)} claims={len(cl)} orphans={len(orphans)}")
        for cid, rf, t in orphans:
            print(f"      orphan {cid} | {rf} | {t}")
        if args.apply and orphans:
            ids = [cid for cid, _, _ in orphans]
            subprocess.run(
                ["ssh", "-n", "-o", "ConnectTimeout=15", worker.ssh, f"docker rm -f {' '.join(ids)}"],
                capture_output=True, text=True, timeout=40,
            )
            print(f"      -> reaped {len(ids)} on {label}")
    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] total orphans={total_orphans}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
