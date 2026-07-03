"""Atomic adapter pre-warm: reap orphans + start-if-missing.

Single source of truth for "this worker has a healthy adapter listening on
:9001 (and any other configured adapter port)" before the dispatcher fires
its first SSH wave.  Without this step, a worker killed during adapter
startup can leave an orphan process bound to the port:

  - The dispatcher fires many SSH dispatches in a short burst.
  - sshd hits MaxStartups, and a few connections die with
    "kex_exchange_identification: Connection reset by peer".
  - A worker_runner that just managed to start adapter_server gets
    SIGKILLed mid-handshake; the adapter PID is now orphan and not
    in the proxy_registry.
  - The next task on that worker calls acquire_shared_proxy_tunnel,
    sees no registry entry, tries to bind 9001 — boom, EADDRINUSE.

This script's two modes both end in
``lib.proxy.tunnel.ensure_shared_proxy_with_reap(spec)``, which atomically
(under the spec's flock):

  1. Reads the on-disk registry; if state is stale, drop it.
  2. ``pgrep -af lib.proxy.adapter_server`` and SIGTERM every PID whose
     argv matches our target listen port but isn't recorded in the
     registry.
  3. Delegate to ``acquire_shared_proxy_tunnel`` — its existing
     check-then-start logic refcounts the adapter for this caller, or
     spawns a fresh one if no healthy adapter remains.

Usage
=====

Controller-side (one-shot pre-warm across the whole cluster, called
automatically by ``scripts/orchestra/dispatch.py`` main() before the
first dispatch wave):

    python3 -m scripts.orchestra.ensure_adapter \
        --all --config configs/orchestra.local.yaml

Worker-side (invoked by the controller's --all over SSH; do not call
manually unless debugging):

    python3 -m scripts.orchestra.ensure_adapter \
        --local --specs-b64 <base64-of-spec-list-json>

Single-host smoke / batch-eval pre-warm (no SSH; reads local configs
and walks --tasks-root to enumerate every spec any task might use):

    python3 -m scripts.orchestra.ensure_adapter --local \
        --tasks-root tasks/

The local mode always emits a JSON array to stdout — one entry per
spec — so callers can grep for failures.  Exit code is 0 iff every
spec succeeded.
"""
from __future__ import annotations

import argparse
import base64
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.proxy.tunnel import (  # noqa: E402
    _proxy_spec_key,
    ensure_shared_proxy_with_reap,
)
from lib.runner.task_config import build_runtime_task_spec, collect_task_proxy_specs  # noqa: E402
from lib.task import discover_task_files, load_task  # noqa: E402
from scripts.orchestra import config as cfg_mod  # noqa: E402


# --------------------------------------------------------------------------
# Spec gathering
# --------------------------------------------------------------------------

def _model_refs_from_cfg(cfg: cfg_mod.OrchestraConfig | None) -> list[str]:
    if cfg is None:
        return []
    model_dirs = sorted(
        {
            model_dir
            for priority in cfg.priorities
            for model_dir in priority.model_in
            if model_dir
        }
    )
    model_refs: list[str] = []
    for model_dir in model_dirs:
        model_refs.append(cfg_mod.model_full_for(model_dir))
    return model_refs


def _codex_role_overrides_from_cfg(
    cfg: cfg_mod.OrchestraConfig | None,
) -> dict[str, dict[str, str | None]] | None:
    if cfg is None:
        return None
    return {
        "supervisor": {
            "provider": cfg.supervision.supervisor.provider,
            "model": cfg.supervision.supervisor.model,
        },
        "user_simulator": {
            "provider": cfg.supervision.user_simulator.provider,
            "model": cfg.supervision.user_simulator.model,
        },
    }


def _runtime_tasks_for_prewarm(
    path: Path,
    *,
    cfg: cfg_mod.OrchestraConfig | None,
    agent_sys: str | None = None,
    model: str | None = None,
) -> list[Any]:
    role_overrides = _codex_role_overrides_from_cfg(cfg)
    model_refs = _model_refs_from_cfg(cfg)
    if not model_refs:
        if cfg is not None or agent_sys or model:
            return [
                build_runtime_task_spec(
                    path,
                    agent_sys=agent_sys,
                    model=model,
                    codex_role_overrides=role_overrides,
                )
            ]
        return [load_task(path, _REPO_ROOT)]
    return [
        build_runtime_task_spec(
            path,
            model=model_ref,
            codex_role_overrides=role_overrides,
        )
        for model_ref in model_refs
    ]


def _gather_specs_from_tasks(
    tasks_root: Path,
    *,
    cfg: cfg_mod.OrchestraConfig | None = None,
    agent_sys: str | None = None,
    model: str | None = None,
) -> list[dict[str, Any]]:
    """Walk every task YAML under ``tasks_root`` and collect every proxy
    spec they reference.  Deduplicated via ``_proxy_spec_key`` — multiple
    tasks sharing the same provider produce one entry.

    With an orchestra config, build the same runtime task specs the dispatcher
    will hand to workers: matrix executor models and supervision role overrides
    are applied before proxy collection.  Without a config, local smoke mode
    falls back to raw task YAML defaults.
    """
    seen: dict[str, dict[str, Any]] = {}
    yamls = discover_task_files(tasks_root)
    for path in yamls:
        try:
            tasks = _runtime_tasks_for_prewarm(
                path,
                cfg=cfg,
                agent_sys=agent_sys,
                model=model,
            )
        except Exception:  # noqa: BLE001
            # Skip malformed/incomplete YAMLs; preflight will surface them.
            continue
        for task in tasks:
            for spec in collect_task_proxy_specs(task):
                # Adapter-less proxies still need their SSH tunnel but
                # don't ship with a 9001 adapter — skip them here, the
                # tunnel itself is per-provider and managed_task_proxy_tunnels
                # will pick it up at task start.
                if not spec.get("adapter"):
                    continue
                key = _proxy_spec_key(spec)
                seen.setdefault(key, spec)
    return list(seen.values())


def _gather_specs_from_specs_b64(b64: str) -> list[dict[str, Any]]:
    raw = base64.b64decode(b64.encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--specs-b64 must decode to a JSON list")
    return list(payload)


# --------------------------------------------------------------------------
# Local mode — directly call ensure_shared_proxy_with_reap per spec
# --------------------------------------------------------------------------

def _summary_entry(spec: dict[str, Any], state: dict[str, Any] | None,
                   error: str | None) -> dict[str, Any]:
    adapter = (state or {}).get("adapter_state") or {}
    return {
        "spec_key": _proxy_spec_key(spec),
        "provider_name": spec.get("provider_name"),
        "source": spec.get("source"),
        "adapter_kind": str(spec.get("adapter") or ""),
        "listen_port": int(adapter.get("listen_port") or 0),
        "pid": int(adapter.get("pid") or 0),
        "reused": bool(adapter.get("reused")),
        "ok": error is None,
        "error": error,
    }


def run_local(specs: list[dict[str, Any]]) -> int:
    """Ensure every spec is listening.  Emits a JSON array to stdout."""
    summary: list[dict[str, Any]] = []
    for spec in specs:
        try:
            state = ensure_shared_proxy_with_reap(spec)
            summary.append(_summary_entry(spec, state, None))
        except Exception as exc:  # noqa: BLE001
            summary.append(_summary_entry(spec, None, str(exc)))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all(s["ok"] for s in summary) else 1


# --------------------------------------------------------------------------
# Cluster mode — SSH every worker in the config, pass specs_b64
# --------------------------------------------------------------------------

def run_all(cfg: cfg_mod.OrchestraConfig, *, tasks_root: Path | None = None) -> int:
    """Gather specs once on the controller, then ssh each worker with
    --local --specs-b64 so workers see the controller's view of configs.

    Returns 0 iff every worker reported success on every spec.
    """
    if tasks_root is None:
        tasks_root = _REPO_ROOT / "tasks"
    specs = _gather_specs_from_tasks(tasks_root, cfg=cfg)
    if not specs:
        # No proxy-adapter specs — every task talks to its provider
        # directly.  Nothing to do, but say so clearly so the dispatcher
        # log doesn't make it look like we silently skipped.
        print("[ensure_adapter] no adapter-bearing proxy specs found "
              f"under {tasks_root}; nothing to pre-warm", file=sys.stderr)
        return 0
    specs_b64 = base64.b64encode(
        json.dumps(specs, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    overall_ok = True
    for w in cfg.workers:
        if w.skip:
            print(f"[{w.name}] skipped (cfg.skip=True)")
            continue
        worker_repo = cfg_mod.worker_repo_for(w, cfg)
        worker_python = cfg_mod.worker_python_cmd(w, cfg)
        remote_cmd = (
            f"cd {shlex.quote(worker_repo)} && "
            f"{worker_python} -m scripts.orchestra.ensure_adapter "
            f"--local --specs-b64 {shlex.quote(specs_b64)}"
        )
        ssh_cmd = [
            "ssh", "-o", "ConnectTimeout=15", w.ssh, remote_cmd,
        ]
        try:
            result = subprocess.run(
                ssh_cmd, capture_output=True, text=True, timeout=180,
            )
        except subprocess.TimeoutExpired:
            print(f"[{w.name}] ssh timeout (180s) — skipped", file=sys.stderr)
            overall_ok = False
            continue
        worker_ok = result.returncode == 0
        overall_ok = overall_ok and worker_ok
        # stdout from the remote is the JSON summary; tee it out.
        print(f"[{w.name}] rc={result.returncode}")
        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.stderr.strip():
            print(f"[{w.name}] stderr:\n{result.stderr.rstrip()}",
                  file=sys.stderr)
    return 0 if overall_ok else 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Atomically reap orphan adapter_server processes "
                    "and ensure every proxy spec is listening.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--local", action="store_true",
        help="Operate on the current host only.  With --specs-b64 the "
             "controller's pre-encoded spec list drives; otherwise walks "
             "--tasks-root to enumerate specs from local configs.",
    )
    mode.add_argument(
        "--all", action="store_true",
        help="Controller-side: gather specs once locally, then ssh each "
             "worker in --config with --local --specs-b64.",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="orchestra config yaml (required with --all)",
    )
    parser.add_argument(
        "--tasks-root", type=Path, default=_REPO_ROOT / "tasks",
        help="root of suite/<id>/task_*.yaml (used to enumerate specs)",
    )
    parser.add_argument(
        "--specs-b64", type=str, default=None,
        help="base64 of a JSON list[spec dict]; preferred in --local "
             "mode when invoked by --all so worker uses controller's view",
    )
    args = parser.parse_args(argv)

    if args.local:
        if args.specs_b64:
            specs = _gather_specs_from_specs_b64(args.specs_b64)
        else:
            specs = _gather_specs_from_tasks(args.tasks_root)
        return run_local(specs)

    if args.all:
        if args.config is None:
            parser.error("--all requires --config")
        cfg = cfg_mod.load(args.config)
        return run_all(cfg, tasks_root=args.tasks_root)

    parser.error("must pick --local or --all")
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
