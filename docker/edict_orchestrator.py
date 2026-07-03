#!/usr/bin/env python3
"""Edict in-container orchestrator.

Approximates cft0808/edict's Orchestrator + Dispatcher for the
single-task-per-container benchmark case, WITHOUT the Redis Streams /
Postgres infrastructure of the native system.

Flow
----
1. Invoke taizi with the user's initial prompt (single
   ``openclaw agent --agent taizi --message <prompt>`` subprocess).
2. After taizi exits, poll the kanban file
   ``/tmp_workspace/edict/data/tasks_source.json`` for the latest
   task's state. Each time the state transitions to a new agent-bound
   state (Zhongshu / Menxia / Assigned / Review / PendingConfirm) or
   to Assigned with a new 六部 ``org`` assignee, invoke the matching
   agent via ``openclaw agent --agent <id>``.
3. When state enters a terminal value (Done / Cancelled), invoke
   taizi ONCE more so it can read any pending inter_session 回奏 from
   中书省 / 尚书省 / 六部 and emit the final conclusion to 皇上.
4. On wall-clock timeout, give taizi one final wake-up so it can
   report whatever it has.

The orchestrator exits with code 0 when it reaches either (a) a
terminal state + taizi final report, or (b) the wall-clock timeout.

This script is designed to be the single entrypoint that clawbench's
``run_edict_agent`` invokes — from its perspective, a single
``openclaw agent`` call has been replaced by a single orchestrator
call, so the surrounding framework (transcript collection, timeline
span, recording session, etc.) doesn't change.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


STATE_AGENT_MAP: dict[str, str] = {
    "Taizi": "taizi",
    "Zhongshu": "zhongshu",
    "Menxia": "menxia",
    "Assigned": "shangshu",
    "Review": "shangshu",
    "PendingConfirm": "shangshu",
    "Pending": "zhongshu",
}

ORG_AGENT_MAP: dict[str, str] = {
    "户部": "hubu",
    "礼部": "libu",
    "兵部": "bingbu",
    "刑部": "xingbu",
    "工部": "gongbu",
    "吏部": "libu_hr",
}

TERMINAL_STATES: set[str] = {"Done", "Cancelled"}

# Kanban JSON path inside the container — matches the edict scripts
# taizi / zhongshu / ... use to read and mutate task state.
KANBAN_FILE = Path(
    os.environ.get(
        "CLAWBENCH_EDICT_KANBAN_FILE",
        "/tmp_workspace/edict/data/tasks_source.json",
    )
)

# Polling cadence between state-change checks. Small enough that we
# react quickly, large enough that we don't pummel the file system.
POLL_INTERVAL_SECONDS = float(
    os.environ.get("CLAWBENCH_EDICT_ORCH_POLL", "3")
)

# Minimum budget each dispatched agent invocation gets. Prevents us
# from firing a 2-second timeout right before the wall-clock deadline.
MIN_AGENT_TIMEOUT_SECONDS = int(
    os.environ.get("CLAWBENCH_EDICT_ORCH_MIN_AGENT_TIMEOUT", "45")
)

# Budget reserved for the final taizi "report to 皇上" invocation when
# the chain reaches a terminal state. Carved out of the total timeout
# so we never run out of time for the final report.
FINAL_REPORT_RESERVE_SECONDS = int(
    os.environ.get("CLAWBENCH_EDICT_ORCH_FINAL_RESERVE", "120")
)

# Round 9 / Phase D fix: idle-after-dispatch detection.  When the last
# dispatched agent's subprocess returns cleanly but the kanban state
# stays unchanged for this many seconds, exit the polling loop early
# and trigger the final taizi report.  Without this, an agent that
# emits a substantive final answer but forgets to flip the kanban
# state to Done burns the entire wall-clock budget in a 3s poll loop.
#
# 30s is large enough to allow taizi → zhongshu → menxia → shangshu →
# 六部 → review → ... legitimate handoffs (each agent invocation
# itself takes seconds to start, run its first turn, and write back to
# the kanban).  An idle gap larger than this means the chain has
# effectively stopped.
IDLE_AFTER_DISPATCH_SECONDS = int(
    os.environ.get("CLAWBENCH_EDICT_ORCH_IDLE_AFTER_DISPATCH", "30")
)

SESSION_ID = os.environ.get("CLAWBENCH_EDICT_SESSION_ID", "chat")


# --------------------------------------------------------------------------
# Logging helper
# --------------------------------------------------------------------------


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[edict-orch {ts}] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------
# Kanban state inspection
# --------------------------------------------------------------------------


def load_latest_task() -> dict[str, Any] | None:
    """Return the most-recently-updated task in the kanban file, or
    None if the file is missing / empty / malformed. Callers treat
    ``None`` as "state unknown, keep waiting"."""
    try:
        data = json.loads(KANBAN_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:
        log(f"kanban read failed: {exc!r}")
        return None
    if not isinstance(data, list) or not data:
        return None
    # Tasks may lack ``updatedAt``; fall back to ``archivedAt`` then id.
    def sort_key(task: dict[str, Any]) -> tuple[str, str]:
        return (
            str(task.get("updatedAt") or task.get("archivedAt") or ""),
            str(task.get("id") or ""),
        )
    return max(data, key=sort_key)


def describe_task(task: dict[str, Any]) -> str:
    parts = [
        f"id={task.get('id', '?')}",
        f"state={task.get('state', '?')}",
    ]
    org = task.get("org")
    if org:
        parts.append(f"org={org}")
    return " ".join(parts)


def pick_agent_for_state(state: str, org: str) -> str | None:
    """Map a kanban state (+ optional 六部 org) to the agent id we
    should dispatch. Returns None for states that don't correspond to
    a single agent (e.g. terminal or pure-data states)."""
    if state == "Assigned" and org:
        mapped = ORG_AGENT_MAP.get(org)
        if mapped:
            return mapped
    return STATE_AGENT_MAP.get(state)


# --------------------------------------------------------------------------
# Agent invocation
# --------------------------------------------------------------------------


def invoke_agent(agent_id: str, message: str, remaining_seconds: int) -> int:
    """Run ``openclaw agent --agent <id> --message <msg>`` as a
    subprocess. Budget the inner --timeout flag against the caller's
    ``remaining_seconds``. Returns the subprocess exit code."""
    timeout = max(MIN_AGENT_TIMEOUT_SECONDS, remaining_seconds)
    cmd = [
        "openclaw",
        "agent",
        "--session-id",
        SESSION_ID,
        "--agent",
        agent_id,
        "--timeout",
        str(timeout),
        "--message",
        message,
    ]
    log(f"dispatch {agent_id} (--timeout={timeout}s)")
    try:
        # Give subprocess.run a slightly larger wall-clock ceiling
        # so a genuinely-hung CLI has time to raise the inner timeout
        # before Python kills it from outside.
        result = subprocess.run(cmd, timeout=timeout + 30)
        return int(result.returncode or 0)
    except subprocess.TimeoutExpired:
        log(f"{agent_id} invocation hit the outer python timeout")
        return 124
    except Exception as exc:
        log(f"{agent_id} invocation raised {exc!r}")
        return 1


def invoke_taizi_final_report(remaining_seconds: int, reason: str) -> None:
    """Invoke taizi one last time so it can integrate any pending
    inter_session 回奏 from the chain and emit the final conclusion
    to 皇上. ``reason`` goes into the prompt for traceability."""
    if remaining_seconds < 20:
        log(f"skip final taizi report ({reason}): only {remaining_seconds}s left")
        return
    prompt = (
        "[system] 子代理链路应已完成或接近完成。"
        "请检查收件箱，整理来自中书省/门下省/尚书省/六部的回奏，"
        "在原对话中向皇上给出最终结论（含产物路径、关键链接与截图）。"
        "如仍有未到位的部门，你可直接在本回合自行推进并给出结论。"
        f"\n(orchestrator trigger: {reason})"
    )
    invoke_agent("taizi", prompt, remaining_seconds)


# --------------------------------------------------------------------------
# Main orchestrator loop
# --------------------------------------------------------------------------


def run(initial_prompt: str, total_timeout: int) -> int:
    deadline = time.time() + total_timeout

    # 1. Initial taizi invocation — carries the 皇上's original prompt.
    remaining = int(deadline - time.time())
    if remaining <= 0:
        log("out of time before initial taizi call")
        return 0
    invoke_agent("taizi", initial_prompt, remaining)

    # 2. State-driven dispatch loop
    last_state: str | None = None
    last_org: str | None = None
    final_report_invoked = False
    # Round 9 / Phase D fix: track the wall-clock time of the most
    # recent dispatch.  When the last dispatched agent's subprocess
    # has returned and no kanban state change has happened within
    # ``IDLE_AFTER_DISPATCH_SECONDS``, exit the polling loop early
    # and trigger the final taizi report.  Without this, an agent
    # that emits a substantive final answer but forgets to flip the
    # kanban state to Done burns the rest of the wall-clock budget
    # in a 3s poll loop.
    #
    # Anchor on the initial taizi dispatch above so the idle window is
    # active from cycle start.  Without this, a cycle 2+ run where
    # taizi returns and the kanban state lands in an unmappable
    # state/org combo (e.g. ``state=Doing org=皇上`` from a model
    # that uses 皇上 as an org placeholder) would never set
    # last_dispatch_at and the orchestrator would poll until
    # wall-clock timeout — exactly the bug Phase D was meant to fix.
    last_dispatch_at: float | None = time.time()

    while time.time() < deadline:
        task = load_latest_task()
        if task is None:
            # Kanban not written yet — taizi is still setting it up
            # or the task is genuinely undefined. Sleep and retry.
            time.sleep(POLL_INTERVAL_SECONDS)
            continue
        state = str(task.get("state") or "")
        org = str(task.get("org") or "")

        if state in TERMINAL_STATES:
            log(f"terminal state reached: {describe_task(task)}")
            remaining = int(deadline - time.time())
            invoke_taizi_final_report(remaining, reason=f"state={state}")
            final_report_invoked = True
            break

        changed = (state != last_state) or (
            state == "Assigned" and org != last_org
        )
        if changed:
            agent = pick_agent_for_state(state, org)
            if agent:
                remaining = int(deadline - time.time() - FINAL_REPORT_RESERVE_SECONDS)
                if remaining < MIN_AGENT_TIMEOUT_SECONDS:
                    log(
                        f"skip dispatch to {agent}: only {remaining}s "
                        "remaining after final-report reserve"
                    )
                    break
                msg = (
                    f"[system] 任务 {task.get('id', '?')} 进入 {state} 状态，"
                    f"{'部门=' + org + '，' if org else ''}请按职责处理。"
                )
                invoke_agent(agent, msg, remaining)
            else:
                log(f"no agent mapping for state={state} org={org}; skip")
            # Round 9 / Phase D fix: reset the idle clock whenever we
            # observe a state change, even when we can't dispatch on
            # it.  The state-change itself is "sign of life" — some
            # agent wrote to the kanban.  Only when 30s pass with NO
            # further state change do we treat as terminal.
            last_dispatch_at = time.time()
            last_state = state
            last_org = org
        else:
            # Round 9 / Phase D fix: early-exit when the chain has
            # stalled.  If we've dispatched at least once and the
            # kanban state hasn't moved for IDLE_AFTER_DISPATCH_SECONDS,
            # the agent emitted its final answer to the conversation
            # but never wrote ``state=Done`` to the kanban (a common
            # gpt-5.4 oversight — it uses `kanban_update.py progress`
            # for status updates but forgets the explicit state
            # transition).  Treat as terminal and let taizi wrap up.
            if (
                last_dispatch_at is not None
                and time.time() - last_dispatch_at >= IDLE_AFTER_DISPATCH_SECONDS
            ):
                log(
                    f"idle for {IDLE_AFTER_DISPATCH_SECONDS}s after last "
                    f"dispatch (state={state}); treating as terminal"
                )
                remaining = int(deadline - time.time())
                invoke_taizi_final_report(
                    remaining, reason=f"idle-after-dispatch state={state}"
                )
                final_report_invoked = True
                break
            time.sleep(POLL_INTERVAL_SECONDS)

    # 3. If we exit the loop without reaching a terminal state (i.e.
    # we hit timeout mid-chain), still fire taizi's final report so
    # the transcript ends with a best-effort conclusion rather than
    # a routing placeholder.
    if not final_report_invoked:
        log("wall-clock timeout before terminal state; trigger final report")
        # Small grace window — we intentionally run slightly past the
        # deadline for this one invocation because it's the last thing
        # we do and produces the user-visible conclusion.
        invoke_taizi_final_report(
            FINAL_REPORT_RESERVE_SECONDS, reason="wall-clock timeout"
        )

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Edict in-container orchestrator")
    ap.add_argument("--message", required=True, help="initial 皇上 prompt")
    ap.add_argument(
        "--timeout",
        type=int,
        required=True,
        help="total wall-clock budget in seconds for the whole chain",
    )
    args = ap.parse_args()

    total_timeout = max(60, int(args.timeout))
    log(f"starting; timeout={total_timeout}s; kanban={KANBAN_FILE}")
    rc = run(args.message, total_timeout)
    log(f"exit rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
