#!/usr/bin/env python3
"""Run every YAML task in a directory and summarise pass/fail/infra counts.

Used for ad-hoc batch evaluation — the orchestra dispatcher is the
production entrypoint.  Reads a directory of ``*.yaml`` task specs and
invokes ``lib.runner.batch_run`` for each.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.runner import batch_run  # noqa: E402
from scripts.orchestra.ensure_adapter import (  # noqa: E402
    _gather_specs_from_tasks,
    run_local as ensure_adapter_run_local,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch_eval.py",
        description="Run every YAML task under a directory and summarise pass/fail/infra counts.",
    )
    parser.add_argument(
        "task_dir",
        type=Path,
        help="Directory containing *.yaml task specs to evaluate.",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of tasks to run concurrently (default: 1).",
    )
    parser.add_argument(
        "--image",
        default="clawbench-openclaw:latest",
        help="Docker image tag to use for the runner container.",
    )
    parser.add_argument(
        "--agent-sys",
        dest="agent_sys",
        help="Backend: openclaw / openclaw_edict / nanobot.",
    )
    parser.add_argument(
        "--model",
        help="Model identifier (e.g. proxy-example/gpt-5.4).",
    )
    parser.add_argument(
        "--keep-container",
        action="store_true",
        help=(
            "Keep the runner container alive after each task finishes. "
            "Default behaviour is to remove the container via docker rm."
        ),
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        raise SystemExit(f"task_dir is not a directory: {task_dir}")

    # V7: explicit ensure_adapter step.  ``batch_run`` already calls
    # ``acquire_shared_proxy_tunnel`` per task, but that path doesn't
    # reap orphans from a prior killed batch.  Calling ensure here means
    # a stale 9001 listener from yesterday's interrupted run gets
    # SIGTERMed before the first task tries to bind it.  Adapter-less
    # task dirs return an empty spec list and this no-ops.
    specs = _gather_specs_from_tasks(
        task_dir,
        agent_sys=args.agent_sys,
        model=args.model,
    )
    if specs:
        ensure_rc = ensure_adapter_run_local(specs)
        if ensure_rc != 0:
            raise SystemExit(f"ensure_adapter failed (rc={ensure_rc})")

    payload = batch_run(
        task_dir,
        parallel=args.parallel,
        image=args.image,
        keep_container=args.keep_container,
        agent_sys=args.agent_sys,
        model=args.model,
    )
    from lib.status import build_status_counts

    results = payload.get("results") or []
    status_counts = build_status_counts(results)
    # Strict-equality counts for the legacy top-level fields, plus the
    # full FINAL_STATUS_ORDER breakdown under statusCounts.  Round 6
    # fixes the historical fail-count inflation: prior code counted
    # any non-pass status as fail via ``passed is False``.
    summary = {
        "agentSys": payload.get("agentSys"),
        "model": payload.get("model"),
        "parallel": payload.get("parallel"),
        "taskCount": payload.get("taskCount"),
        "pass": status_counts["pass"],
        "infra_error": status_counts["infra_error"],
        "fail": status_counts["fail"],
        "statusCounts": status_counts,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
