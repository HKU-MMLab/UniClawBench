#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.runner import run_task  # noqa: E402
from lib.runner.task_config import model_slug  # noqa: E402
from lib.task import canonical_agent_sys, load_task  # noqa: E402
import shutil  # noqa: E402


ROOT_DIR = Path(__file__).resolve().parents[1]

# Grace added on top of the task's executor budget (max_total_seconds) for
# supervisor + user-simulator grading and container teardown — neither of which
# counts toward max_total_seconds.  The watchdog below is a LAST-RESORT guard:
# if a grader API call hangs or a non-daemon thread never joins, run_eval.py
# would otherwise sit as a zombie for hours (worker_runner's own subprocess
# timeout is 20000s+), leaking processes/memory on the worker.
_WATCHDOG_GRACE_SECONDS = 1800


def _watchdog_deadline(task_yaml: Path, override: int | None) -> int:
    """Hard wall-clock budget for the whole run_eval.py process."""
    if override is not None:
        return override
    try:
        budget = load_task(task_yaml, ROOT_DIR).max_total_seconds
    except Exception:
        budget = 1800
    return int(budget) + _WATCHDOG_GRACE_SECONDS


def _arm_watchdog(deadline_seconds: int) -> None:
    """Force-exit the process if it hasn't finished within ``deadline_seconds``.

    Uses a daemon thread + ``os._exit`` (not sys.exit) so it fires even when the
    main thread is blocked in a hung C call / network read and bypasses
    atexit/thread-join that an un-joined non-daemon thread would otherwise hang
    on.  ``os._exit(124)`` mirrors the conventional timeout exit code.
    """
    if deadline_seconds <= 0:
        return

    def _kill() -> None:
        time.sleep(deadline_seconds)
        sys.stderr.write(
            f"[run_eval] watchdog: exceeded {deadline_seconds}s — force-exiting "
            "(suspected hung grader call / un-joined thread).\n"
        )
        sys.stderr.flush()
        os._exit(124)

    threading.Thread(target=_kill, daemon=True, name="run_eval-watchdog").start()


def _prune_prior(task_yaml: Path, agent_sys_override: str | None, model_override: str | None) -> None:
    task = load_task(task_yaml, ROOT_DIR)
    # strict=True: a typo or removed alias in --agent-sys must error here
    # rather than silently pointing at a path that never matched any run.
    backend = canonical_agent_sys(agent_sys_override or task.agent_sys, strict=True)
    model = model_override or task.model
    target = ROOT_DIR / "runs" / backend / model_slug(model) / task.category / task.task_id
    if target.exists():
        shutil.rmtree(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_yaml")
    parser.add_argument("image", nargs="?", default="clawbench-openclaw:latest")
    parser.add_argument(
        "--keep-container",
        action="store_true",
        help=(
            "Keep the runner container alive after the task finishes. "
            "Default behaviour is to remove the container via docker rm."
        ),
    )
    parser.add_argument("--fresh", action="store_true",
                        help="Delete prior attempts for this (backend, model, category, task_id) before running.")
    parser.add_argument("--agent-sys")
    parser.add_argument("--model")
    parser.add_argument("--image-model")
    parser.add_argument("--agent-provider")
    parser.add_argument("--user-simulator-model")
    parser.add_argument("--user-simulator-provider")
    parser.add_argument("--user-simulator-config")
    parser.add_argument("--user-simulator-reasoning-effort")
    parser.add_argument("--supervisor-model")
    parser.add_argument("--supervisor-provider")
    parser.add_argument("--supervisor-config")
    parser.add_argument("--supervisor-reasoning-effort")
    parser.add_argument(
        "--hard-timeout-seconds", type=int, default=None,
        help="Force-exit the whole run_eval process after this many seconds "
             "(default: task max_total_seconds + grace). 0 disables the watchdog.",
    )
    args = parser.parse_args()

    task_yaml = Path(args.task_yaml).resolve()
    # Arm the last-resort self-timeout before doing any real work.
    _arm_watchdog(_watchdog_deadline(task_yaml, args.hard_timeout_seconds))
    if args.fresh:
        _prune_prior(task_yaml, args.agent_sys, args.model)
    role_overrides = {
        "user_simulator": {
            "model": args.user_simulator_model,
            "provider": args.user_simulator_provider,
            "config": args.user_simulator_config,
            "reasoning_effort": args.user_simulator_reasoning_effort,
        },
        "supervisor": {
            "model": args.supervisor_model,
            "provider": args.supervisor_provider,
            "config": args.supervisor_config,
            "reasoning_effort": args.supervisor_reasoning_effort,
        },
    }
    payload = run_task(
        task_yaml,
        image=args.image,
        keep_container=args.keep_container,
        agent_sys=args.agent_sys,
        model=args.model,
        image_model=args.image_model,
        agent_provider=args.agent_provider,
        codex_role_overrides=role_overrides,
    )
    summary = {
        "taskId": payload.get("taskId"),
        "backend": payload.get("backend"),
        "model": payload.get("model"),
        "imageModel": payload.get("imageModel"),
        "finalStatus": payload.get("finalStatus"),
        "finalScore": payload.get("finalScore"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
