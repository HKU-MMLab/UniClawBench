"""Executor agent dispatch + initial / continuation prompt rendering.

These helpers are the "inside the container" handoff: once the runtime
+ services are up (see ``container.py``, ``services.py``), the
orchestrator calls :func:`run_agent` with a rendered prompt. The agent
backend (openclaw / openclaw_edict / nanobot) is selected from
``task.agent_sys`` and its CLI is launched under the monitored-process
watchdog that kills the process if no progress is observed within
``AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS``.

The module is deliberately thin: no scoring, no supervisor calls, no
artefact collection — those live in ``evaluation.py`` and
``artifacts.py``. Only prompt rendering + agent invocation.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ..defaults import AGENT_SESSION_ID, RESULTS_ROOT
from ..privacy import resolve_privacy_env
from ..task import TaskSpec
from ..templates.executor_runtime import EDICT_ROUTING_NOTE, EXECUTOR_RUNTIME_PREFIX_LINES
from . import container_lifecycle as container_mod, docker as docker_mod, task_config


AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS = max(
    0,
    int(os.environ.get("CLAWBENCH_AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS", "180")),
)

# Rolling inactivity watchdog: if the agent produced output earlier but then
# goes silent (no growth in agent.log / results / transcript) for this many
# seconds, the in-container monitor force-terminates it instead of idling until
# the per-turn deadline.  This is what catches the dead-but-not-exited-agent
# case (executor process inside the container wedges into a stuck parent;
# ``proc.poll()`` never returns; host ``docker exec`` keeps waiting), which used
# to freeze a dispatch slot until the run_eval watchdog (~60 min).  Default 600s
# (10 min) matches the operator's diagnostic threshold; 0 disables.  Set BELOW
# the per-turn budget (timeout_seconds, typically 1200s) so it can fire within a
# turn.  Openclaw streams model output to agent.log during healthy work, so a
# multi-minute zero-byte gap is a strong dead-agent signal — but the threshold
# is deliberately generous to avoid killing legitimately-slow GUI turns.
AGENT_STALL_TIMEOUT_SECONDS = max(
    0,
    int(os.environ.get("CLAWBENCH_AGENT_STALL_TIMEOUT_SECONDS", "600")),
)


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# ── Semantic-progress stall (OPT-IN, default OFF) ─────────────────────────
# The byte-level stall guard (AGENT_STALL_TIMEOUT_SECONDS) resets its clock on
# ANY growth of agent.log / results / transcript bytes.  A dead-but-writing
# agent defeats it: openclaw re-injects runtime-context ``user`` lines, and
# pdftocairo / screenshots / ``process poll`` keep touching files, so bytes keep
# growing while the model has actually stopped working.  Those runs then burn
# the full per-attempt budget and only die at the outer watchdog (rc=124).
#
# When CLAWBENCH_AGENT_SEMANTIC_PROGRESS is enabled, the monitor additionally
# watches the transcript .jsonl for *semantic* progress — a NEW assistant reply
# or a NEW tool call/result — and trips ``semantic-stall`` (rc=247) if none
# appears for CLAWBENCH_AGENT_SEMANTIC_STALL_TIMEOUT_SECONDS.  Re-injected
# ``user`` lines (the spoof vector) and pure byte growth are NOT counted.
#
# Deliberately conservative by default:
#   * flag defaults OFF — non-opted-in workers behave EXACTLY as today;
#   * the timeout defaults to 0 (also disabling it) so even flipping the flag
#     alone is inert until an explicit, generous window is set;
#   * a recommended canary window is ~900s (> the 600s byte stall), so it only
#     ever bites strictly-later, dead-but-writing agents, never a slow GUI turn
#     that is still emitting tool calls.
AGENT_SEMANTIC_PROGRESS_ENABLED = _truthy(
    os.environ.get("CLAWBENCH_AGENT_SEMANTIC_PROGRESS", "0")
)
AGENT_SEMANTIC_STALL_TIMEOUT_SECONDS = max(
    0,
    int(os.environ.get("CLAWBENCH_AGENT_SEMANTIC_STALL_TIMEOUT_SECONDS", "0")),
)


def prompt_prefix(task: TaskSpec) -> str:
    declared_skill_lines = [f"- /root/skills/{name}/SKILL.md" for name in task.skills]
    runtime_skill_lines = [f"- /root/skills/{name}/SKILL.md" for name in container_mod.runtime_base_skills()]
    skill_lines = "\n".join(dict.fromkeys([*runtime_skill_lines, *declared_skill_lines])) or "- none"
    lines = [
        line.format(results_root=RESULTS_ROOT, skill_lines=skill_lines)
        for line in EXECUTOR_RUNTIME_PREFIX_LINES
    ]
    return "\n".join(lines) + "\n"


def _select_task_body(task: TaskSpec) -> str:
    """Pick the executor-visible prompt body. Executors never see
    SNAPSHOT_MODE itself — the runner reads the privacy env and substitutes
    ``task_snapshot`` only when the task opts in via SNAPSHOT_MODE=1.
    """
    if task.task_snapshot:
        try:
            env = resolve_privacy_env(task.privacy) if task.privacy else {}
        except Exception:
            env = {}
        if str(env.get("SNAPSHOT_MODE", "")).strip() == "1":
            return task.task_snapshot.strip()
    return task.task.strip()


def build_initial_prompt(task: TaskSpec) -> str:
    # For the ``openclaw_edict`` backend we prepend EDICT_ROUTING_NOTE so the
    # executor understands it is operating inside the 三省六部 multi-agent
    # pipeline and routes via 太子 → 中书省 → 门下省 → 尚书省 → 六部 rather
    # than answering the task as a single-agent. (Removing it in fe30f3c led
    # to the edict root agent treating the task like a normal single-agent
    # flow and never triggering the kanban / sub-agent routing.) The note +
    # ``_strip_edict_routing_note`` helper live in
    # ``lib/templates/executor_runtime.py`` and ``lib/supervision_common.py``
    # respectively; the supervisor / user_simulator workspace sees the
    # stripped version.
    sections = [prompt_prefix(task).rstrip()]
    if task_config.normalize_agent_sys(task.agent_sys) == "openclaw_edict":
        sections.append(EDICT_ROUTING_NOTE)
    sections.append(_select_task_body(task))
    return "\n\n".join(part for part in sections if part).strip() + "\n"


def build_continuation_prompt(feedback: str) -> str:
    body = str(feedback or "").strip() or "Please continue from your current state."
    return body.strip() + "\n"


def run_monitored_agent(
    container: str,
    command: list[str],
    timeout_seconds: int,
    *,
    progress_paths: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    # Inline the host-side liveness logic (decide / run_monitor) into the
    # in-container script.  The task container has no access to the repo, so we
    # splice agent_monitor.py's source verbatim — keeping ONE source of truth
    # that is also unit-tested host-side (see tests/unit/test_agent_monitor_*).
    # agent_monitor.py is intentionally stdlib-only with no ``from __future__``
    # so it can be injected anywhere in the script body.  It's substituted as a
    # runtime f-string VALUE (``{monitor_src}``), so braces / quotes inside it
    # are inserted literally and cannot break this f-string.
    monitor_src = (Path(__file__).resolve().with_name("agent_monitor.py")).read_text(encoding="utf-8")
    script = f"""
python3 - <<'PY'
import json
import os
import signal
import subprocess
import time

# ── injected: lib/runner/agent_monitor.py (decide / run_monitor) ──
{monitor_src}
# ── end injected ──

command = json.loads({json.dumps(json.dumps(command, ensure_ascii=False))})
timeout_seconds = int({int(timeout_seconds)})
startup_silence_timeout_seconds = int({int(AGENT_STARTUP_SILENCE_TIMEOUT_SECONDS)})
stall_timeout_seconds = int({int(AGENT_STALL_TIMEOUT_SECONDS)})
semantic_progress_enabled = bool({1 if AGENT_SEMANTIC_PROGRESS_ENABLED else 0})
semantic_stall_timeout_seconds = int({int(AGENT_SEMANTIC_STALL_TIMEOUT_SECONDS)})
log_path = "/tmp_workspace/clawbench/logs/agent.log"
results_root = "/tmp_workspace/results"
progress_paths = json.loads({json.dumps(json.dumps(list(progress_paths or []), ensure_ascii=False))})
log = open(log_path, "a", encoding="utf-8", buffering=1)
started_at = time.time()
deadline = started_at + timeout_seconds
proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)

def file_size(path):
    try:
        return int(os.path.getsize(path))
    except OSError:
        return 0

def result_file_count(root):
    try:
        with os.scandir(root) as entries:
            return sum(1 for _ in entries)
    except OSError:
        return 0

# Rolling baselines: refreshed whenever a signal grows, so observed_progress()
# measures growth since the LAST check (not just since startup).  A healthy
# streaming agent keeps resetting the stall clock; a dead one never does.
baseline = {{
    "log": file_size(log_path),
    "results": result_file_count(results_root),
    "progress": {{path: file_size(path) for path in progress_paths}},
}}

def observed_progress():
    progressed = False
    cur = file_size(log_path)
    if cur > baseline["log"]:
        baseline["log"] = cur
        progressed = True
    cur = result_file_count(results_root)
    if cur > baseline["results"]:
        baseline["results"] = cur
        progressed = True
    for path in progress_paths:
        cur = file_size(path)
        if cur > baseline["progress"].get(path, 0):
            baseline["progress"][path] = cur
            progressed = True
    return progressed

# ── semantic progress (opt-in) ──────────────────────────────────────────
# Counts NEW assistant replies / tool calls / tool results in the transcript
# .jsonl files (same schema as lib/supervision/transcripts.py).  Re-injected
# runtime-context ``user`` lines and pure byte growth are NOT semantic progress,
# so a dead-but-writing agent stops resetting the semantic clock while a healthy
# one keeps emitting assistant/tool events.  Reads only the appended tail since
# the last check (rolling byte offset per file) to stay cheap.  Any read/parse
# error is swallowed and treated as "no new semantic event" for that file — the
# caller (run_monitor) additionally treats an *exception* as inconclusive, but
# routine empty/partial reads here simply contribute nothing.
semantic_offsets = {{path: file_size(path) for path in progress_paths}}

def _line_is_semantic(line):
    line = line.strip()
    if not line:
        return False
    try:
        event = json.loads(line)
    except (ValueError, TypeError):
        return False
    if not isinstance(event, dict):
        return False
    if str(event.get("type") or "").strip() != "message":
        return False
    message = event.get("message")
    if not isinstance(message, dict):
        message = {{}}
    role = str(message.get("role") or "").strip()
    # New assistant turn (text OR a toolUse stop) and tool results are real
    # model/tool activity.  ``user`` (incl. re-injected runtime-context) and
    # anything else is explicitly NOT counted.
    if role == "assistant":
        return True
    if role == "toolResult":
        return True
    return False

def semantic_progress():
    progressed = False
    for path in progress_paths:
        try:
            size = file_size(path)
            start = semantic_offsets.get(path, 0)
            if size < start:
                # File shrank/rotated — reset and recount from the top.
                start = 0
            if size <= start:
                semantic_offsets[path] = size
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(start)
                chunk = fh.read()
            semantic_offsets[path] = size
            for raw in chunk.splitlines():
                if _line_is_semantic(raw):
                    progressed = True
                    break
        except OSError:
            continue
    return progressed

def terminate_process_tree(sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass

def terminate(reason):
    log.write("[clawbench-monitor] terminating agent (%s): no observable progress; failing fast\\n" % reason)
    terminate_process_tree(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        terminate_process_tree(signal.SIGKILL)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    # Preserve the old ``proc.returncode or <reason-code>`` semantics: a killed
    # process that reported 0 / None must NOT look like success.
    return proc.returncode if proc.returncode else None

exit_code = run_monitor(
    poll=proc.poll,
    observed_progress=observed_progress,
    terminate=terminate,
    now=time.time,
    sleep=time.sleep,
    started_at=started_at,
    deadline=deadline,
    startup_silence_timeout=startup_silence_timeout_seconds,
    stall_timeout=stall_timeout_seconds,
    semantic_progress=(semantic_progress if semantic_progress_enabled else None),
    semantic_stall_timeout=(semantic_stall_timeout_seconds if semantic_progress_enabled else 0),
)
raise SystemExit(exit_code)
PY
"""
    return docker_mod.docker_exec(container, script)


def run_openclaw_agent(container: str, task: TaskSpec, prompt: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    agent_sys = task_config.normalize_agent_sys(task.agent_sys)
    # Edict runs go through the in-container orchestrator
    # (/usr/local/bin/edict_orchestrator.py) which handles initial
    # taizi dispatch, state-driven sub-agent dispatches via kanban,
    # and a final taizi "report to 皇上" invocation. That matches
    # cft0808/edict's native Orchestrator + Dispatcher roles without
    # requiring Redis / Postgres infrastructure here.
    if agent_sys == "openclaw_edict":
        command = [
            "python3",
            "/usr/local/bin/edict_orchestrator.py",
            "--timeout",
            str(timeout_seconds),
            "--message",
            prompt,
        ]
        return run_monitored_agent(
            container,
            command,
            timeout_seconds,
            progress_paths=task_config.transcript_targets_for_task(task),
        )

    agent_flag = ""
    agent_id = task_config.effective_agent_id_for_task(task)
    if agent_id and agent_id not in {"clawbench-openclaw", "main"}:
        agent_flag = f" --agent {json.dumps(agent_id)}"
    command = [
        "openclaw",
        "agent",
        "--session-id",
        AGENT_SESSION_ID,
        "--timeout",
        str(timeout_seconds),
    ]
    if agent_flag:
        command.extend(["--agent", agent_id])
    command.extend(["--message", prompt])
    return run_monitored_agent(container, command, timeout_seconds, progress_paths=task_config.transcript_targets_for_task(task))


def run_nanobot_agent(container: str, task: TaskSpec, prompt: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    command = [
        "nanobot",
        "agent",
        "-c",
        "/root/.nanobot/config.json",
        "--session",
        AGENT_SESSION_ID,
        "-w",
        "/tmp_workspace",
        "--no-markdown",
        "-m",
        prompt,
    ]
    return run_monitored_agent(container, command, timeout_seconds, progress_paths=task_config.transcript_targets_for_task(task))


def run_agent(container: str, task: TaskSpec, prompt: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    agent_sys = task_config.normalize_agent_sys(task.agent_sys)
    if agent_sys in {"openclaw", "openclaw_edict"}:
        return run_openclaw_agent(container, task, prompt, timeout_seconds)
    if agent_sys == "nanobot":
        return run_nanobot_agent(container, task, prompt, timeout_seconds)
    raise NotImplementedError(f"agent_sys={task.agent_sys} is not implemented")
