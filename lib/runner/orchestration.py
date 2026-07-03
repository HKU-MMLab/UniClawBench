"""Top-level attempt / task / batch orchestration.

This is the entry-point layer for ``scripts/run_eval.py`` and
``scripts/batch_eval.py``. ``run_task`` bootstraps provider proxy
tunnels, resolves the task spec, and delegates to
``_run_resolved_task``; that function owns the container lifecycle,
retry loop, and the timeline recorder installation; it hands off to
``run_primary_attempt`` for the per-turn supervisor loop.

Intra-package calls go through qualified module imports so pytest
``monkeypatch.setattr("lib.runner.<submodule>.<name>", ...)`` resolves
to the real source module instead of a stale rebind.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from ..defaults import AGENT_SESSION_ID, DEFAULT_IMAGE, RESULTS_ROOT
from ..proxy import write_local
from ..status import (
    BATCH_SUMMARY_SCHEMA_VERSION,
    META_SCHEMA_VERSION,
    SESSION_META_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
    apply_score_based_promotion,
    classify_attempt_outcome,
)
from ..task import TaskSpec, discover_task_files, load_task
from . import (
    agents,
    artifacts,
    container_lifecycle as container_mod,
    docker as docker_mod,
    edict as edict_mod,
    errors,
    evaluation,
    media as recording,
    task_config,
    transcripts,
)
# Round 8 / A4: import token-ledger helpers directly from usage_ledger.
# Earlier code accessed them as ``artifacts.append_executor_usage_ledger``
# but artifacts.py never exported those symbols — the attribute lookup
# raised AttributeError, caught silently by the surrounding ``try:
# except Exception: pass``.  Production usage_ledger.jsonl files written
# after the April-17 split (e579f116) carry zero executor entries; only
# pre-split runs have them.  Importing the symbol directly fixes both
# the initial-turn ledger write and the retry-window ledger write.
from .usage_ledger import (
    append_executor_usage_ledger,
    attempt_task_id,
    build_attempt_usage_payload,
)
# ``container_lifecycle`` exposes pre_exec helpers + service-startup helpers
# previously in three sibling modules.  Alias the section names to preserve
# the orchestration call-site naming (``services.start_desktop`` etc.)
# without churn.
from . import container_lifecycle as services  # noqa: E402  pre-Phase-2.3 alias
from . import container_lifecycle as pre_exec_mod  # noqa: E402  pre-Phase-2.3 alias
from .container_lifecycle import PreExecError

# Re-exported from ``lib.runner`` for legacy consumers; also defined here at
# module level so ``lib.runner.orchestration.ROOT`` resolves identically to
# ``lib.defaults.ROOT``.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_CONTAINER_RUNTIME_RETRY_ATTEMPTS = max(
    0,
    int(os.environ.get("CLAWBENCH_CONTAINER_RUNTIME_RETRY_ATTEMPTS", "2")),
)
# Executor HTTP 429 retry budget. When the openclaw agent (or any backend
# that mirrors a structured rate-limit log) reports a provider throttle,
# the orchestrator sleeps 2**retry_count seconds (1, 2, 4, 8, 16, ..., 512)
# between attempts up to this cap. Past the cap the attempt is marked
# ``rate_limit`` as before. Supervisor / user-simulator 429s have a
# SEPARATE policy — they retry indefinitely (see ``codex.py``) because
# re-running the executor is far more expensive than waiting out a grader
# throttle.
DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES = max(
    0,
    int(os.environ.get("CLAWBENCH_EXECUTOR_RATE_LIMIT_RETRIES", "10")),
)
DEFAULT_EXECUTOR_RATE_LIMIT_BACKOFF_CAP = max(
    1.0,
    float(os.environ.get("CLAWBENCH_EXECUTOR_RATE_LIMIT_BACKOFF_CAP", "3600")),
)


def _clear_openclaw_logs_for_retry(container_name: str, out_dir: Path) -> None:
    """Zero out openclaw log files inside the container + host mirror.

    ``errors.detect_openclaw_rate_limit`` tail-scans the append-only
    openclaw agent log for 429 markers. Without this reset, a rate-limit
    detected in turn N would keep firing on every subsequent retry
    because the stale needle is still in the file tail. Truncating
    (rather than deleting) preserves the agent's open file handle so the
    in-flight process keeps writing to the same inode — a new 429 will
    be added to an otherwise empty file, which the next detect call
    correctly classifies as a fresh throttle.

    The host-side mirror is cleared too because ``docker cp`` does not
    remove host files whose container source vanished — without this
    step the mirror could carry zombie ``*.log`` entries from before
    the retry and poison detection.
    """
    if not container_name:
        return
    try:
        subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "sh",
                "-c",
                # Truncate *.log and *.jsonl under /tmp/openclaw (structured
                # agent logs) plus the clawbench runtime log that is mirrored
                # to <out_dir>/logs/agent.log. ``|| true`` so missing files
                # don't flip the exit code.
                "find /tmp/openclaw -type f \\( -name '*.log' -o -name '*.jsonl' \\) "
                "-exec truncate -s 0 {} + 2>/dev/null; "
                "truncate -s 0 /tmp_workspace/clawbench/logs/agent.log 2>/dev/null; "
                "true",
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
    openclaw_mirror = out_dir / "openclaw"
    if openclaw_mirror.is_dir():
        for path in list(openclaw_mirror.rglob("*")):
            if path.is_file() and path.suffix in {".log", ".jsonl"}:
                try:
                    path.unlink()
                except Exception:
                    pass
    host_agent_log = out_dir / "logs" / "agent.log"
    if host_agent_log.exists():
        try:
            host_agent_log.unlink()
        except Exception:
            pass


# The currently-installed attempt timeline recorder lives in
# ``recording._ACTIVE_RECORDER`` — ``recording.active_timeline_recorder()``
# is the only reader. ``_run_resolved_task`` installs / restores it via
# direct module-attribute writes in a try/finally.


def initialize_session_container(
    image: str,
    task: TaskSpec,
    attempt_id: str = "",
    *,
    host_out_dir: Path | None = None,
) -> tuple[str, list[dict]]:
    agent_sys = task_config.normalize_agent_sys(task.agent_sys)
    # Pre-executor hooks run BEFORE the container is created — they touch the
    # live API from the host (never the container) so populator source code
    # cannot leak into the executor's view. If any script fails we raise, and
    # the outer retry loop records it as a container-boot infra_error.
    if task.pre_exec:
        with recording.timeline_span("container_lifecycle", "pre_exec_hooks"):
            pre_exec_mod.run_pre_exec_scripts(task)
    with recording.timeline_span("container_lifecycle", "start_container"):
        container_name = container_mod.start_container(image, task, f"session-{uuid.uuid4().hex[:6]}")
    with recording.timeline_span("container_lifecycle", "prepare_runtime"):
        container_mod.prepare_runtime(container_name, task)
    if agent_sys == "openclaw":
        with recording.timeline_span("container_lifecycle", "inject_openclaw_config"):
            container_mod.inject_openclaw_config(container_name, task, attempt_id=attempt_id)
    elif agent_sys == "openclaw_edict":
        with recording.timeline_span("container_lifecycle", "inject_edict_config"):
            container_mod.inject_edict_config(container_name, task, attempt_id=attempt_id)
    elif agent_sys == "nanobot":
        with recording.timeline_span("container_lifecycle", "inject_nanobot_config"):
            container_mod.inject_nanobot_config(container_name, task, attempt_id=attempt_id)
    with recording.timeline_span("container_lifecycle", "start_desktop"):
        services.start_desktop(container_name)
    with recording.timeline_span("container_lifecycle", "start_services"):
        # ``host_out_dir`` lets services salvage container-side install logs
        # to ``<attempt>/logs/container/`` before raising on failure, so the
        # transcript travels back to the controller via rsync.
        started_services = services.start_services(container_name, task, host_out_dir=host_out_dir)
    if agent_sys in {"openclaw", "openclaw_edict"}:
        with recording.timeline_span("container_lifecycle", "start_gateway"):
            services.start_gateway(container_name)
        with recording.timeline_span("container_lifecycle", "ensure_openclaw_runtime_ready"):
            services.ensure_openclaw_runtime_ready(container_name, task)
    return container_name, started_services


def stage_dir_name(attempt_no: int) -> str:
    """Return the per-attempt directory name.

    By default we use a short uuid suffix (``p1-abc123``).  When running
    under the orchestra dispatcher the worker exports
    ``CLAWBENCH_HOST_TAG`` (e.g. ``worker1``) so that attempts produced on
    different workers can coexist in the same task directory without
    risking a collision (``p1-worker1-abc123`` vs ``p1-worker2-def456``).

    The webui resolves attempt dirs by basename, so the extra middle
    segment is transparent to it.
    """
    suffix = uuid.uuid4().hex[:6]
    host_tag = os.environ.get("CLAWBENCH_HOST_TAG", "").strip().lower()
    if host_tag:
        return f"p{attempt_no}-{host_tag}-{suffix}"
    return f"p{attempt_no}-{suffix}"


def attempt_meta_base(task: TaskSpec, container_name: str) -> dict[str, Any]:
    return {
        "schema_version": META_SCHEMA_VERSION,
        "taskId": task.task_id,
        "backend": task_config.normalize_agent_sys(task.agent_sys),
        "model": task.model,
        "imageModel": task.image_model,
        "stageType": "primary",
        "stageId": "primary",
        "stageIndex": 1,
        "promptKind": "primary",
        "outputs": [],
        "process": {"resultsRoot": RESULTS_ROOT},
        "checkpoints": [],
        "supervision": {
            "evaluationMode": "codex_supervised",
            "maxUserFollowups": int(task.codex.max_user_followups),
            "userSimulator": {
                "model": task.codex.user_simulator.model,
                "provider": task.codex.user_simulator.provider,
                "config": task.codex.user_simulator.config,
                "reasoning_effort": task.codex.user_simulator.reasoning_effort,
            },
            "supervisor": {
                "model": task.codex.supervisor.model,
                "provider": task.codex.supervisor.provider,
                "config": task.codex.supervisor.config,
                "reasoning_effort": task.codex.supervisor.reasoning_effort,
            },
        },
        "agentContainer": container_name,
        "continuations": [],
        "continuationTrace": [],
        "supervisionDecisions": [],
        "runtimeMs": 0,
        "agentExitCode": None,
        "everExecutorCompleted": False,
        "latestCompletedEvaluation": None,
        "latestCompletedSupervisorScore": 0.0,
    }


def build_bootstrap_infra_attempt(
    task: TaskSpec,
    *,
    attempt_no: int,
    error: dict[str, Any],
    out_dir: Path | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir) if out_dir is not None else task_config.task_run_root(task) / stage_dir_name(attempt_no)
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    score = {
        "overall_score": 0.0,
        "score_cap": 1.0,
        "capped_score": 0.0,
        "verdict": "infra_error",
        "attempt_state": "infra_error",
        "recoverable": False,
        "confidence": "medium",
        "error": str(error.get("message") or "container bootstrap failed"),
        "infra_error": True,
        "infra_error_type": str(error.get("type") or "container_bootstrap_failed"),
        "safe_user_feedback": "",
        "missing_artifacts": [],
        "guidance_tags": [],
        "evaluation_index": 1,
    }
    meta = attempt_meta_base(task, "")
    meta["outDir"] = str(out_dir)
    meta["runtimeMs"] = 0
    meta["agentExitCode"] = None
    meta["bootstrapError"] = error
    artifacts.write_score_json(out_dir, task, score)
    write_local(out_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    write_local(out_dir / "bootstrap_error.log", str(error.get("message") or "") + "\n")
    # PreExecError supplies extra context — pass it through so the summary
    # carries enough detail for operator triage without re-opening the log.
    score["infra_error_type"] = str(error.get("type") or "container_bootstrap_failed")
    infra_error = {
        "type": str(error.get("type") or "container_bootstrap_failed"),
        "message": str(error.get("message") or ""),
        "retryScheduled": False,
    }
    if error.get("type") == "pre_exec_failed":
        infra_error["script"] = str(error.get("script") or "")
        infra_error["returncode"] = error.get("returncode")
        tail_text = error.get("tail")
        if tail_text:
            infra_error["tail"] = str(tail_text)[-4000:]
            write_local(out_dir / "pre_exec_tail.log", str(tail_text) + "\n")
    return {
        "attempt": attempt_no,
        "promptKind": "primary",
        "stageType": "primary",
        "stageId": "primary",
        "stageIndex": 1,
        "outDir": str(out_dir),
        "runtimeMs": 0,
        "score": score,
        "infraError": infra_error,
    }


def build_bootstrap_infra_summary(
    task: TaskSpec,
    *,
    image: str,
    keep_container: bool,
    error: dict[str, Any],
) -> dict[str, Any]:
    task_config.reset_task_run_root(task)
    attempt = build_bootstrap_infra_attempt(task, attempt_no=1, error=error)
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "taskId": task.task_id,
        "taskFile": str(task.file_path),
        "backend": task_config.normalize_agent_sys(task.agent_sys),
        "model": task.model,
        "imageModel": task.image_model,
        "evaluationMode": "codex_supervised",
        "modelSlug": task_config.model_slug(task.model),
        "settingRoot": str(task_config.setting_root(task.agent_sys, task.model)),
        "attempts": [attempt],
        "resolvedAttempt": None,
        "rawFinalScore": 0.0,
        "finalScore": 0.0,
        "passed": False,
        "finalStatus": "infra_error",
        "infraError": attempt.get("infraError"),
    }
    session_meta = {
        "schema_version": SESSION_META_SCHEMA_VERSION,
        "taskId": task.task_id,
        "backend": task_config.normalize_agent_sys(task.agent_sys),
        "model": task.model,
        "imageModel": task.image_model,
        "evaluationMode": "codex_supervised",
        "image": image,
        "keepContainer": keep_container,
        "containerRetryLimit": 0,
        "containerRetries": [],
        "sessions": {},
        "proxyBootstrapError": error,
    }
    write_local(task_config.task_run_root(task) / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    write_local(task_config.task_run_root(task) / "session_meta.json", json.dumps(session_meta, ensure_ascii=False, indent=2) + "\n")
    return summary


def task_summary_base(
    task: TaskSpec,
    *,
    attempts: list[dict] | None = None,
    resolved_attempt: int | None = None,
    raw_final_score: float = 0.0,
    final_score: float = 0.0,
    final_status: str = "running",
    infra_error: dict[str, Any] | None = None,
    rate_limit: dict[str, Any] | None = None,
    passed: bool | None = None,
    stop_reason: str = "",
) -> dict[str, Any]:
    final_status = str(final_status or "running")
    if passed is None:
        passed = final_status == "pass"
    backend = task_config.normalize_agent_sys(task.agent_sys)
    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "taskId": task.task_id,
        "taskFile": str(task.file_path),
        "backend": backend,
        "model": task.model,
        "imageModel": task.image_model,
        "evaluationMode": "codex_supervised",
        "modelSlug": task_config.model_slug(task.model),
        "settingRoot": str(task_config.setting_root(task.agent_sys, task.model)),
        "attempts": list(attempts or []),
        "resolvedAttempt": resolved_attempt,
        "rawFinalScore": float(raw_final_score or 0.0),
        "finalScore": float(final_score or 0.0),
        "passed": bool(passed),
        "finalStatus": final_status,
        "infraError": infra_error,
        "rateLimit": rate_limit,
        "stopReason": str(stop_reason or ""),
    }
    # Round 9 / B3: tag edict runs with the upstream-revision metadata
    # baked into the image (see scripts/fetch_edict.sh +
    # docker/openclaw-edict.Dockerfile).  Lets the WebUI render the
    # "EDICT @ <commit>" badge and lets human reviewers know which
    # cft0808/edict snapshot the executor actually ran against.
    if backend == "openclaw_edict":
        summary["edict"] = edict_mod.read_edict_runtime_metadata()
    return summary


def write_task_run_state(task: TaskSpec, *, summary: dict[str, Any], session_meta: dict[str, Any]) -> None:
    write_local(task_config.task_run_root(task) / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    write_local(task_config.task_run_root(task) / "session_meta.json", json.dumps(session_meta, ensure_ascii=False, indent=2) + "\n")


def structured_runtime_error_score(error: dict[str, Any], *, turn: int) -> dict[str, Any]:
    message = str(error.get("message") or error.get("type") or "runtime error")
    return {
        "overall_score": 0.0,
        "score_cap": 1.0,
        "capped_score": 0.0,
        "verdict": "infra_error",
        "attempt_state": "infra_error",
        "recoverable": False,
        "confidence": "medium",
        "error": message,
        "infra_error": True,
        "infra_error_type": str(error.get("type") or "runtime_error"),
        "safe_user_feedback": "",
        "missing_artifacts": [],
        "guidance_tags": [],
        "evaluation_index": turn,
    }


def structured_rate_limit_score(error: dict[str, Any], *, turn: int) -> dict[str, Any]:
    """Build a synthetic score payload for an attempt where the upstream
    provider returned HTTP 429 / rate-limit / quota-exceeded before the
    model could reason. Parallel to ``structured_runtime_error_score``
    but tagged as a ``rate_limit`` attempt state (peer of ``infra_error``).
    """
    message = str(error.get("message") or error.get("type") or "rate limit")
    return {
        "overall_score": 0.0,
        "score_cap": 1.0,
        "capped_score": 0.0,
        "verdict": "rate_limit",
        "attempt_state": "rate_limit",
        "recoverable": False,
        "confidence": "medium",
        "error": message,
        "rate_limit": True,
        "rate_limit_type": str(error.get("type") or "provider_rate_limited"),
        "rate_limit_source": str(error.get("source") or ""),
        "safe_user_feedback": "",
        "missing_artifacts": [],
        "guidance_tags": [],
        "evaluation_index": turn,
    }


def resolve_attempt_outcome(task: TaskSpec, score: dict[str, Any], *, terminal_reason: str = "") -> dict[str, Any]:
    """Derive the per-attempt ``finalStatus`` + ``finalScore`` from a supervisor score dict.

    Delegates to ``lib.status.classify_attempt_outcome`` (the single source
    of classification logic shared with ``refresh_summary._derive_status_from_artifacts``).
    See that function's docstring for the full 6-priority order.

    After classification, applies score-based pass promotion: a final_score
    that meets ``task.success_threshold`` flips a budget_exhausted /
    global_timeout / running classification up to pass (the agent met the
    bar even if it used the full budget).  Does NOT promote explicit
    failure paths (fail / executor_incomplete / infra_error / rate_limit /
    pre_exec_failed) where the supervisor or runtime has rendered a
    definitive not-pass classification.
    """
    current = dict(score or {})
    best = current.get("best_supervisor_score")
    raw_score = float(best if best is not None else current.get("overall_score", 0.0) or 0.0)
    final_score = raw_score

    # Resolve agent exit code from either field name.
    agent_exit_code = current.get("executor_exit_code")
    if agent_exit_code is None:
        agent_exit_code = current.get("agent_exit_code")

    final_status = classify_attempt_outcome(
        verdict=current.get("verdict") or "",
        attempt_state=current.get("attempt_state") or "",
        rate_limit=bool(current.get("rate_limit")),
        infra_error=bool(current.get("infra_error")),
        infra_error_type=current.get("infra_error_type") or "",
        completion_gate_failed=bool(current.get("completion_gate_failed")),
        executor_completed_ever=(
            bool(current.get("executor_completed"))
            or bool(current.get("executor_completed_ever"))
        ),
        agent_exit_code=agent_exit_code if isinstance(agent_exit_code, int) else None,
        completion_reason="",
        followup_budget_exhausted=bool(current.get("followup_budget_exhausted")),
        # Round 10 / P3: parity with Path B (refresh_summary).  Path B
        # threads ``passed_flag=bool(score.get("passed"))`` through
        # ``classify_attempt_outcome`` since Round-5; Path A has been
        # missing it.  Current runtime score.json never carries bare
        # ``passed=true`` without a verdict so the gap was theoretical,
        # but pass the flag here so a future caller that DOES write
        # ``score["passed"]`` directly gets identical classification on
        # both paths.
        passed_flag=bool(current.get("passed")),
        terminal_reason=terminal_reason or "",
    )

    # Score-based pass promotion: only on "completed-normally" terminal states.
    # Shared with refresh_summary._derive_status_from_artifacts via
    # ``apply_score_based_promotion`` so Path A and Path B never diverge.
    final_status, passed = apply_score_based_promotion(
        final_status, final_score, task.success_threshold
    )
    stop_reason = str(terminal_reason or "")

    return {
        "final_status": final_status,
        "final_score": final_score,
        "raw_final_score": raw_score,
        "passed": passed,
        "stop_reason": stop_reason,
    }


def run_primary_attempt(
    container_name: str,
    task: TaskSpec,
    *,
    attempt_no: int,
    out_dir: Path | None = None,
) -> dict:
    out_dir = Path(out_dir) if out_dir is not None else task_config.task_run_root(task) / stage_dir_name(attempt_no)
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    result_dir = out_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    meta = attempt_meta_base(task, container_name)
    meta["outDir"] = str(out_dir)
    prompt_text = agents.build_initial_prompt(task)
    prompt_file = out_dir / "prompt.md"
    write_local(prompt_file, prompt_text)

    started_at = time.time()
    run_start_ts = started_at
    # Cumulative wall-clock time spent inside executor cycles. Supervisor and
    # user-simulator time is not counted against max_total_seconds.
    executor_elapsed_seconds: float = 0.0
    turn = 1
    last_score: dict[str, Any] = {}
    best_supervisor_score: float = 0.0
    infra_error: dict[str, Any] | None = None
    # Track provider-side rate-limit / 429 separately from generic infra
    # errors so the run's final_status can report ``rate_limit`` and the
    # WebUI can surface the operator's quota issue distinctly. Populated
    # by ``detect_openclaw_rate_limit`` (openclaw agent log scan) and by
    # ``detect_infra_error`` when its transcript match has ``rate_limit=True``.
    rate_limit: dict[str, Any] | None = None
    terminal_decision: dict[str, Any] = {}
    while True:
        wall_elapsed_seconds = time.time() - run_start_ts
        if task.max_total_seconds > 0 and executor_elapsed_seconds >= task.max_total_seconds:
            terminal_decision = {
                "action": "stop",
                "reason": "global-timeout-executor",
                "executorElapsedSeconds": executor_elapsed_seconds,
                "wallElapsedSeconds": wall_elapsed_seconds,
                "budgetSeconds": task.max_total_seconds,
            }
            break
        timeout_seconds = task.timeout_seconds
        if task.max_total_seconds > 0:
            remaining_executor_budget = task.max_total_seconds - executor_elapsed_seconds
            if remaining_executor_budget <= 0:
                terminal_decision = {
                    "action": "stop",
                    "reason": "global-timeout-executor",
                    "executorElapsedSeconds": executor_elapsed_seconds,
                    "wallElapsedSeconds": wall_elapsed_seconds,
                    "budgetSeconds": task.max_total_seconds,
                }
                break
            timeout_seconds = max(1, min(task.timeout_seconds, int(remaining_executor_budget)))
        # Record this cycle's executor turn into supervision/cycle_NN/recording.mp4
        # — one video per cycle, not one per attempt, so the WebUI can show each
        # cycle's desktop action alongside that cycle's supervisor decision.
        cycle_recording_dir = out_dir / "supervision" / f"cycle_{turn:02d}"
        cycle_recording_dir.mkdir(parents=True, exist_ok=True)
        if task_config.normalize_agent_sys(task.agent_sys) in {"openclaw", "openclaw_edict"}:
            services.ensure_openclaw_runtime_ready(container_name, task)
        executor_turn_started_at = time.time()
        _is_edict = task_config.normalize_agent_sys(task.agent_sys) == "openclaw_edict"
        _primary_agent_id = task_config.effective_agent_id_for_task(task) if _is_edict else ""
        with recording.timeline_span("executor", f"cycle_{turn:02d}_executor", cycle=turn):
            with recording.recording_session(container_name, task, cycle_recording_dir):
                agent_result = agents.run_agent(
                    container_name, task, prompt_text, timeout_seconds
                )
                time.sleep(2)
                with recording.timeline_span("artifact", "collect_attempt_artifacts", cycle=turn):
                    artifacts.collect_attempt_artifacts(container_name, out_dir, task)
                with recording.timeline_span("artifact", "collect_runtime_probe", cycle=turn):
                    artifacts.collect_runtime_probe(container_name, out_dir)
                if errors.should_retry_transient_followup(task, turn, agent_result, out_dir):
                    services.ensure_openclaw_runtime_ready(container_name, task)
                    agent_result = agents.run_agent(
                        container_name, task, prompt_text, timeout_seconds
                    )
                    time.sleep(2)
                    with recording.timeline_span("artifact", "collect_attempt_artifacts_retry", cycle=turn):
                        artifacts.collect_attempt_artifacts(container_name, out_dir, task)
                    with recording.timeline_span("artifact", "collect_runtime_probe_retry", cycle=turn):
                        artifacts.collect_runtime_probe(container_name, out_dir)
                # Edict's multi-agent dance is now orchestrated inside
                # the container (see docker/edict_orchestrator.py +
                # run_edict_agent below). The orchestrator handles:
                #   - initial taizi dispatch
                #   - state-driven sub-agent dispatches based on kanban
                #   - final taizi "report to 皇上" when state reaches
                #     Done (or timeout) — giving us a real conclusion
                #     in the transcript before supervisor fires.
                # So the outer wrapper here is once again the same for
                # all three backends: one ``run_agent`` call, then
                # supervisor. No extra wait/re-invoke steps needed.
                pass
        # End of this cycle's executor activity. Accumulate the time we spent
        # in/around run_agent (incl. the 2s grace for transcript settle +
        # artifact collection, because those also happen while the container
        # is still hot and are part of "evaluating this turn"). Supervisor
        # and user-simulator Codex calls below this line are NOT added.
        executor_turn_ended_at = time.time()
        executor_elapsed_seconds += executor_turn_ended_at - executor_turn_started_at
        # Slice the shared proxy adapter log for usage events that fell inside
        # this executor window and record them into the per-attempt ledger.
        # The window is strictly before any supervisor/user-simulator work
        # begins, so anything logged here can only be an executor call.
        try:
            append_executor_usage_ledger(
                out_dir,
                turn=turn,
                start_ts=executor_turn_started_at,
                end_ts=executor_turn_ended_at,
                task_id=attempt_task_id(out_dir),
            )
            # Note: per-attempt full request transcript (``requests.jsonl``)
            # is intentionally NOT sliced into the attempt directory anymore.
            # ``transcript.jsonl`` already records the application-level
            # conversation (user/assistant/toolResult), which is what
            # downstream replay/audit actually consumes; ``requests.jsonl``
            # was 40-100× larger and held mostly redundant SSE-stream
            # raw text. The adapter still writes the full transcript to the
            # GLOBAL ``.runtime/proxy_adapter_requests.log`` for adapter-
            # level debugging (failed requests, latency, status codes); use
            # ``artifacts.append_attempt_request_log`` directly when an
            # attempt-scoped slice is genuinely needed.
        except Exception:
            pass
        transcript_text = (out_dir / "transcript.jsonl").read_text(encoding="utf-8", errors="ignore") if (out_dir / "transcript.jsonl").exists() else ""
        tool_usage = transcripts.load_tool_usage_file(out_dir)

        # Reconstruct per tool-call timing for the cycle we just finished and
        # annotate the containing executor span so the Gantt panel can render
        # a drill-down under each cycle. Tolerant to malformed transcripts.
        _recorder_for_spans = recording.active_timeline_recorder()
        if _recorder_for_spans is not None and transcript_text:
            try:
                _tool_spans = transcripts.reconstruct_tool_spans(
                    transcript_text,
                    window=(executor_turn_started_at, executor_turn_ended_at),
                )
                if _tool_spans:
                    _recorder_for_spans.annotate_last(
                        lambda entry: entry.get("kind") == "executor"
                        and entry.get("cycle") == turn
                        and "tool_calls" not in entry,
                        {"tool_calls": _tool_spans},
                    )
            except Exception:
                pass

        # ── rate_limit detection ──────────────────────────────────
        # Openclaw's embedded agent records HTTP 429 as structured
        # JSON log entries (``failoverReason=rate_limit``,
        # ``rawErrorPreview=429 status code``) that NEVER surface as
        # assistant message text in the transcript — the transcript
        # only contains empty ``stopReason=error`` envelopes. So we
        # scan the agent-log mirror on disk FIRST and, if that misses,
        # fall back to the transcript-level detector which can still
        # catch rate-limit text when it bleeds through.
        def _detect_rate_limit_signals() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
            rl: dict[str, Any] | None = None
            if task_config.normalize_agent_sys(task.agent_sys) in {"openclaw", "openclaw_edict"}:
                rl = errors.detect_openclaw_rate_limit(out_dir)
            infra = errors.detect_infra_error(transcript_text, tool_usage)
            if rl is None and infra and infra.get("rate_limit"):
                rl = dict(infra)
            return rl, infra

        rate_limit_this_turn, transcript_signal = _detect_rate_limit_signals()

        # Executor-side 429 retry: if the initial scan found a rate-limit
        # marker, wait out the throttle with exponential backoff (1, 2, 4,
        # 8, 16, ... seconds) and rerun the executor up to
        # DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES times before giving up. Each
        # retry clears the append-only openclaw log so the next detect
        # pass only sees fresh text — otherwise the stale 429 from this
        # turn would force every retry to trip the same detector.
        rate_limit_retry_count = 0
        while (
            rate_limit_this_turn is not None
            and rate_limit_retry_count < DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES
        ):
            # Round 16 / P1-3: re-check the executor wall-clock budget
            # BEFORE sleeping.  Previous code applied the budget only at
            # the top of the outer turn loop, so a sticky throttle could
            # burn 10+ minutes of sleep + retry beyond ``max_total_seconds``
            # and still hand off to the supervisor.
            if task.max_total_seconds > 0:
                remaining = task.max_total_seconds - executor_elapsed_seconds
                if remaining <= 0:
                    terminal_decision = {
                        "action": "stop",
                        "reason": "global-timeout-executor",
                        "executorElapsedSeconds": executor_elapsed_seconds,
                        "wallElapsedSeconds": time.time() - run_start_ts,
                        "budgetSeconds": task.max_total_seconds,
                    }
                    break
            sleep_for = min(
                DEFAULT_EXECUTOR_RATE_LIMIT_BACKOFF_CAP,
                float(2 ** rate_limit_retry_count),
            )
            # Clip the sleep so we never wait past the budget.
            if task.max_total_seconds > 0:
                sleep_for = min(
                    sleep_for,
                    max(0.0, task.max_total_seconds - executor_elapsed_seconds),
                )
            print(
                f"[rate_limit] executor turn={turn} retry={rate_limit_retry_count + 1}"
                f"/{DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES} sleeping {sleep_for:.0f}s",
                flush=True,
            )
            _sleep_started_at = time.time()
            time.sleep(sleep_for)
            # Sleep counts toward the executor wall-clock budget — without
            # this the budget could be silently exceeded by a long backoff
            # that ate the remaining seconds.
            executor_elapsed_seconds += time.time() - _sleep_started_at

            # Re-check after sleep — if the sleep itself blew the budget,
            # don't even start the retry.
            retry_timeout_seconds = task.timeout_seconds
            if task.max_total_seconds > 0:
                remaining = task.max_total_seconds - executor_elapsed_seconds
                if remaining <= 0:
                    terminal_decision = {
                        "action": "stop",
                        "reason": "global-timeout-executor",
                        "executorElapsedSeconds": executor_elapsed_seconds,
                        "wallElapsedSeconds": time.time() - run_start_ts,
                        "budgetSeconds": task.max_total_seconds,
                    }
                    break
                retry_timeout_seconds = max(
                    1, min(task.timeout_seconds, int(remaining))
                )

            _clear_openclaw_logs_for_retry(container_name, out_dir)

            if task_config.normalize_agent_sys(task.agent_sys) in {"openclaw", "openclaw_edict"}:
                services.ensure_openclaw_runtime_ready(container_name, task)
            _retry_started_at = time.time()
            with recording.timeline_span(
                "executor",
                f"cycle_{turn:02d}_rate_limit_retry_{rate_limit_retry_count + 1:02d}",
                cycle=turn,
            ):
                with recording.recording_session(container_name, task, cycle_recording_dir):
                    agent_result = agents.run_agent(
                        container_name, task, prompt_text, retry_timeout_seconds
                    )
                    time.sleep(2)
                    with recording.timeline_span(
                        "artifact",
                        f"collect_attempt_artifacts_rl_retry_{rate_limit_retry_count + 1:02d}",
                        cycle=turn,
                    ):
                        artifacts.collect_attempt_artifacts(container_name, out_dir, task)
                    with recording.timeline_span(
                        "artifact",
                        f"collect_runtime_probe_rl_retry_{rate_limit_retry_count + 1:02d}",
                        cycle=turn,
                    ):
                        artifacts.collect_runtime_probe(container_name, out_dir)
            _retry_ended_at = time.time()
            # Retries are part of the executor's wall-clock budget — same
            # accounting rule as the initial turn's run.
            executor_elapsed_seconds += _retry_ended_at - _retry_started_at

            # Round 8 / A4: append usage ledger for this retry window.  The
            # initial-turn call at the top of the cycle (line ~626) captured
            # the first window; without this call here, every token the
            # provider charged us during the retry window vanishes from
            # usage.json / executorByTurn / Results-page averages.  Tag with
            # retry_kind / retry_index so consumers can split retry cost
            # from initial-turn cost if needed (defaults keep the existing
            # initial-turn ledger row unchanged).
            try:
                append_executor_usage_ledger(
                    out_dir,
                    turn=turn,
                    start_ts=_retry_started_at,
                    end_ts=_retry_ended_at,
                    task_id=attempt_task_id(out_dir),
                    retry_kind="rate_limit",
                    retry_index=rate_limit_retry_count + 1,
                )
            except Exception:
                # Match the initial-turn append's swallow-and-continue
                # posture: a ledger write must not break the retry loop.
                pass

            # Re-read transcript + tool_usage now that the retry wrote fresh
            # content, then re-scan for rate-limit / infra signals.
            transcript_text = (out_dir / "transcript.jsonl").read_text(encoding="utf-8", errors="ignore") if (out_dir / "transcript.jsonl").exists() else ""
            tool_usage = transcripts.load_tool_usage_file(out_dir)
            rate_limit_this_turn, transcript_signal = _detect_rate_limit_signals()
            rate_limit_retry_count += 1

        # Round 16 / P1-3: if the retry loop exhausted the executor budget,
        # terminate this attempt with global_timeout WITHOUT handing off
        # to the supervisor.  Same posture as the top-of-loop budget
        # check: stop, don't evaluate, don't continue.
        # Round-7: but if we were STILL rate-limited when the budget ran out,
        # the run wasn't slow at the task — it was throttled into the wall.
        # Attribute it to rate_limit (write a rate_limit score so
        # classify_attempt_outcome routes it to priority-1 rate_limit) so the
        # provider-quota issue is surfaced and it gets the right retry posture,
        # instead of being buried as a generic global_timeout.
        if (
            terminal_decision.get("reason") == "global-timeout-executor"
            and rate_limit_this_turn is not None
        ):
            rate_limit_this_turn.setdefault("retries_attempted", rate_limit_retry_count)
            rate_limit_this_turn["timed_out_while_throttled"] = True
            if rate_limit is None:
                rate_limit = dict(rate_limit_this_turn)
            last_score = structured_rate_limit_score(rate_limit_this_turn, turn=turn)
            artifacts.write_score_json(out_dir, task, last_score)
            break
        if terminal_decision.get("reason") == "global-timeout-executor":
            break

        if rate_limit_this_turn is not None:
            # Annotate so the summary / WebUI can surface how many retries
            # we burned before giving up. Helpful for distinguishing a
            # sticky provider block (10/10 retries still 429) from a brief
            # spike that would have cleared with a larger retry budget.
            rate_limit_this_turn.setdefault("retries_attempted", rate_limit_retry_count)
            # Capture the run-level rate_limit for the attempt record
            # / summary. Only overwrite the earlier turn's record if
            # the new hit is more informative (currently first-wins).
            if rate_limit is None:
                rate_limit = dict(rate_limit_this_turn)
            else:
                # Keep first-wins semantics but make sure the final
                # retry count is reflected on the attempt record.
                rate_limit["retries_attempted"] = rate_limit_retry_count
            infra_error = None  # rate_limit supersedes infra for this turn
        else:
            # Only care about non-rate-limit infra errors here; a
            # transcript hit with ``rate_limit=True`` was already
            # claimed above.
            infra_error = None if (transcript_signal and transcript_signal.get("rate_limit")) else transcript_signal
        runtime_candidate = errors._match_retryable_container_error(
            agent_result.stdout,
            agent_result.stderr,
            errors._attempt_agent_log_tail(out_dir),
            pattern_set=errors.RETRYABLE_CONTAINER_RUNTIME_PATTERNS,
        )
        if runtime_candidate and not transcript_text.strip() and rate_limit_this_turn is None:
            infra_error = {
                "type": runtime_candidate["type"],
                "message": runtime_candidate["message"],
                "noToolProgress": True,
            }
        if rate_limit_this_turn is not None:
            last_score = structured_rate_limit_score(rate_limit_this_turn, turn=turn)
            artifacts.write_score_json(out_dir, task, last_score)
        elif infra_error and infra_error.get("noToolProgress"):
            last_score = structured_runtime_error_score(infra_error, turn=turn)
            artifacts.write_score_json(out_dir, task, last_score)
        else:
            # Routing pump for edict now lives INSIDE the executor
            # span (see the inner ``while True:`` loop above). By the
            # time we get here either:
            #   - taizi produced a non-routing reply → evaluate normally
            #   - task.timeout_seconds was exhausted while still routing
            #     → evaluate normally; the supervisor's own "continue"
            #       feedback acts as the escalate
            _evaluate_start_ts = time.time()
            last_score = evaluation.evaluate_attempt(
                task,
                turn=turn,
                attempt_no=attempt_no,
                prompt_file=prompt_file,
                out_dir=out_dir,
                container_name=container_name,
            )
            _evaluate_end_ts = time.time()
            # Reconstruct per-role timing by replaying elapsed_ms from each
            # component debug payload. Supervisor runs first, then
            # user_simulator (only if verdict=continue + recoverable), then
            # the deterministic feedback rewriter. We emit supervisor and
            # user_simulator as top-level phases; the rewriter is
            # deterministic/short and folded into the supervisor span.
            _recorder_for_phases = recording.active_timeline_recorder()
            if _recorder_for_phases is not None:
                try:
                    _evaluate_start_ms = int(_evaluate_start_ts * 1000)
                    _evaluate_end_ms = int(_evaluate_end_ts * 1000)
                    _evaluate_total_ms = max(0, _evaluate_end_ms - _evaluate_start_ms)

                    # Pull elapsed_ms from the answer_supervisor component
                    # debug first; fall back to the supervision_trace row for
                    # the current cycle; fall back to 0. Same pattern for
                    # user_simulator. For supervisor failures (infra_error /
                    # user_simulator_skip_reason=supervisor-error) elapsed_ms
                    # is often 0 because evaluate_attempt bails before the
                    # debug block is written — in that case we attribute the
                    # whole evaluate window to the supervisor.
                    _answer_component = dict(last_score.get("answer_supervisor") or {})
                    _user_component = dict(last_score.get("public_user_simulator") or {})
                    if not _answer_component or not _user_component:
                        _trace_path = out_dir / "supervision_trace.jsonl"
                        if _trace_path.exists():
                            _trace_lines = _trace_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                            for _line in reversed(_trace_lines):
                                try:
                                    _trace_entry = json.loads(_line)
                                except Exception:
                                    continue
                                if _trace_entry.get("evaluation_index") == turn:
                                    if not _answer_component:
                                        _answer_component = {"elapsed_ms": _trace_entry.get("elapsed_ms") or 0}
                                    break
                    _supervisor_elapsed = int(_answer_component.get("elapsed_ms") or 0)
                    _user_elapsed = int(_user_component.get("elapsed_ms") or 0)

                    _verdict = str(last_score.get("verdict") or "").lower()
                    _us_skip_reason = str(last_score.get("user_simulator_skip_reason") or "")
                    _us_mode = str(last_score.get("user_simulator_mode") or "")
                    _us_skipped = bool(_us_skip_reason) or _us_mode == "silent"

                    _supervisor_errored = _verdict in {"infra_error", "rate_limit"} or _us_skip_reason == "supervisor-error"
                    # When the supervisor errored it consumed the whole window
                    # (e.g. three 180s timeouts). When elapsed_ms signals are
                    # missing but everything succeeded, share the window
                    # proportionally: if user_simulator was skipped, it gets
                    # zero and supervisor gets the full window; otherwise use
                    # the reported elapsed_ms values (clamped).
                    if _supervisor_errored or (_supervisor_elapsed <= 0 and _us_skipped):
                        _supervisor_end_ms = _evaluate_end_ms
                        _us_start_ms = _evaluate_end_ms
                        _us_end_ms = _evaluate_end_ms
                    else:
                        _supervisor_end_ms = min(
                            _evaluate_start_ms + max(0, _supervisor_elapsed),
                            _evaluate_end_ms,
                        )
                        _us_start_ms = _supervisor_end_ms
                        if _us_skipped:
                            _us_end_ms = _us_start_ms
                        elif _user_elapsed > 0:
                            _us_end_ms = min(_us_start_ms + _user_elapsed, _evaluate_end_ms)
                        else:
                            _us_end_ms = _evaluate_end_ms

                    _recorder_for_phases.append_phase(
                        "supervisor",
                        f"cycle_{turn:02d}_answer_supervisor",
                        start_ms=_evaluate_start_ms,
                        end_ms=_supervisor_end_ms,
                        cycle=turn,
                        extra={
                            "verdict": _verdict,
                            "score": float(last_score.get("overall_score") or 0.0),
                            "errored": _supervisor_errored,
                        },
                    )
                    _recorder_for_phases.append_phase(
                        "user_simulator",
                        f"cycle_{turn:02d}_user_simulator",
                        start_ms=_us_start_ms,
                        end_ms=_us_end_ms,
                        cycle=turn,
                        extra={
                            "skipped": _us_skipped,
                            "skip_reason": _us_skip_reason,
                            "mode": _us_mode,
                        },
                    )
                except Exception:
                    pass
            if infra_error:
                last_score.setdefault("warnings", []).append(infra_error["message"])
        # For multi-agent backends (openclaw_edict), restrict the
        # "last assistant message" lookup to the primary agent (taizi) so
        # sub-agent closures in the merged transcript don't spuriously mark
        # the attempt complete. Single-agent backends pass "" and skip the
        # filter. See ``_last_assistant_message`` for the full rationale.
        _primary_agent_for_completion = (
            task_config.effective_agent_id_for_task(task)
            if task_config.normalize_agent_sys(task.agent_sys) == "openclaw_edict"
            else ""
        )
        # Round 10 / P1: thread followup budget into the gate so
        # ``pass without completion signal`` flips to ``continue`` (not
        # ``fail``) when the user simulator can still legitimately give
        # the executor one more turn.  The budget at this point mirrors
        # what ``continuation_decision`` will see at line 1015 below:
        # ``max_user_followups - len(meta["continuations"])`` — each
        # completed cycle has appended exactly one continuation entry.
        _followup_budget_remaining = max(
            0,
            int(task.codex.max_user_followups) - len(meta["continuations"]),
        )
        last_score = evaluation.apply_executor_completion_gate(
            last_score,
            transcript_text,
            agent_result.returncode,
            primary_agent_id=_primary_agent_for_completion,
            agent_sys=task_config.normalize_agent_sys(task.agent_sys),
            followup_budget_remaining=_followup_budget_remaining,
        )
        current_supervisor_score = float(last_score.get("overall_score", 0.0) or 0.0)
        # best_supervisor_score tracks the MAX of the supervisor's raw verdict
        # score (overall_score) across all cycles — not the completion-gated
        # final_completion_score. This gives the final payload a stable "best
        # the supervisor ever said about this run" number, even if the last
        # cycle happened to regress or if the executor was cut off mid-tool-call.
        # The completion gate still controls pass/fail via final_completion_score.
        if current_supervisor_score > best_supervisor_score:
            best_supervisor_score = current_supervisor_score
        last_score["best_supervisor_score"] = best_supervisor_score
        if bool(last_score.get("executor_completed")):
            meta["everExecutorCompleted"] = True
            meta["latestCompletedEvaluation"] = turn
            meta["latestCompletedSupervisorScore"] = float(last_score.get("overall_score", 0.0) or 0.0)
        last_score["executor_completed_ever"] = bool(meta.get("everExecutorCompleted"))
        last_score["latest_completed_evaluation"] = meta.get("latestCompletedEvaluation")
        last_score["latest_completed_supervisor_score"] = float(meta.get("latestCompletedSupervisorScore", 0.0) or 0.0)
        artifacts.write_score_json(out_dir, task, last_score)

        # runtimeMs is "executor runtime" — supervisor / user-simulator time
        # is infrastructure and excluded. wallClockMs keeps the raw wall clock
        # for diagnostics (container startup, supervision latency, etc.).
        meta["runtimeMs"] = int(executor_elapsed_seconds * 1000)
        meta["wallClockMs"] = int((time.time() - started_at) * 1000)
        meta["agentExitCode"] = agent_result.returncode
        meta["executorCompletionSignal"] = bool(last_score.get("executor_completion_signal"))
        meta["executorCompleted"] = bool(last_score.get("executor_completed"))
        meta["executorCompletionReason"] = str(last_score.get("executor_completion_reason") or "")
        meta["supervisionDecisions"].append(
            {
                "evaluationIndex": turn,
                "verdict": last_score.get("verdict"),
                "score": last_score.get("overall_score"),
                "finalCompletionScore": last_score.get("final_completion_score"),
                "safeUserFeedback": last_score.get("safe_user_feedback"),
                "rawSupervisorVerdict": last_score.get("supervisor_verdict_raw"),
                "executorCompleted": last_score.get("executor_completed"),
            }
        )

        decision = evaluation.continuation_decision(task, last_score, transcript_text, len(meta["continuations"]))
        decision["evaluationIndex"] = turn
        decision["followupAgentExitCode"] = agent_result.returncode
        meta["continuationTrace"].append(decision)
        write_local(out_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")

        # Roll up the per-attempt ``usage.json`` now that this cycle's
        # executor + supervisor + user_simulator ledger entries are all
        # written. The payload is cumulative (every row in
        # ``usage_ledger.jsonl`` gets aggregated), so repeating the
        # write each cycle keeps the WebUI current across a multi-
        # cycle run. We must do this AFTER
        # ``append_executor_usage_ledger`` + ``append_role_usage_ledger``
        # — rolling up inside ``collect_attempt_artifacts`` would run
        # before those append calls and miss the cycle's own rows.
        try:
            _usage_payload = build_attempt_usage_payload(out_dir, task)
        except Exception as exc:
            _usage_payload = {
                "available": False,
                "reason": f"compute-failed:{type(exc).__name__}",
                "source": {"executor": "error", "supervisor": "error", "user_simulator": "error"},
                "summary": {},
                "calls": [],
            }
        write_local(
            out_dir / "usage.json",
            json.dumps(_usage_payload, ensure_ascii=False, indent=2) + "\n",
        )

        if decision["action"] != "continue":
            terminal_decision = dict(decision)
            break

        prompt_text = agents.build_continuation_prompt(decision["safeUserFeedback"])
        prompt_file = out_dir / f"continuation_{turn:02d}.md"
        write_local(prompt_file, prompt_text)
        meta["continuations"].append(
            {
                "index": turn,
                "file": prompt_file.name,
                "safeUserFeedback": decision["safeUserFeedback"],
            }
        )
        write_local(out_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
        turn += 1

    attempt_record = {
        "attempt": attempt_no,
        "promptKind": "primary",
        "stageType": "primary",
        "stageId": "primary",
        "stageIndex": 1,
        "outDir": str(out_dir),
        "runtimeMs": meta["runtimeMs"],
        "score": last_score,
        "infraError": infra_error if last_score.get("verdict") == "infra_error" else None,
        "rateLimit": rate_limit if last_score.get("verdict") == "rate_limit" else None,
        "terminalDecision": terminal_decision,
    }
    write_local(out_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return attempt_record


def _run_resolved_task(task: TaskSpec, *, image: str = DEFAULT_IMAGE, keep_container: bool = False) -> dict:
    agent_sys = task_config.normalize_agent_sys(task.agent_sys)
    if image == DEFAULT_IMAGE:
        image = task_config.default_image_for_agent_sys(agent_sys)
    task_config.reset_task_run_root(task)

    active_containers: list[str] = []
    max_container_attempts = 1 + DEFAULT_CONTAINER_RUNTIME_RETRY_ATTEMPTS
    logical_attempt_no = 1
    logical_attempt_dir = task_config.task_run_root(task) / stage_dir_name(logical_attempt_no)
    # Create the attempt's timeline recorder NOW — before initialize_session
    # _container so its container-lifecycle phases (start_container,
    # prepare_runtime, inject_*_config, start_desktop, start_gateway, ...)
    # can be captured by ``timeline_span`` via the module-global active
    # recorder. Bind the attempt dir at construction time so every closed
    # span triggers an incremental flush — the WebUI can watch the file
    # grow while the attempt is still in flight. The finally block still
    # writes the authoritative end-of-attempt timeline.json.
    _timeline_recorder = recording.TimelineRecorder(
        attempt_started_ms=int(time.time() * 1000),
        out_dir=logical_attempt_dir,
    )
    placeholder_attempt = {
        "attempt": logical_attempt_no,
        "promptKind": "primary",
        "stageType": "primary",
        "stageId": "primary",
        "stageIndex": 1,
        "outDir": str(logical_attempt_dir),
        "runtimeMs": 0,
        "score": {},
    }
    session_meta: dict[str, Any] = {
        "schema_version": SESSION_META_SCHEMA_VERSION,
        "taskId": task.task_id,
        "backend": agent_sys,
        "model": task.model,
        "imageModel": task.image_model,
        "evaluationMode": "codex_supervised",
        "image": image,
        "keepContainer": keep_container,
        "codex": {
            "maxUserFollowups": int(task.codex.max_user_followups),
            "userSimulator": {
                "model": task.codex.user_simulator.model,
                "provider": task.codex.user_simulator.provider,
                "config": task.codex.user_simulator.config,
                "reasoning_effort": task.codex.user_simulator.reasoning_effort,
            },
            "supervisor": {
                "model": task.codex.supervisor.model,
                "provider": task.codex.supervisor.provider,
                "config": task.codex.supervisor.config,
                "reasoning_effort": task.codex.supervisor.reasoning_effort,
            },
        },
        "containerRetryLimit": max(0, max_container_attempts - 1),
        "containerRetries": [],
        "sessions": {},
    }
    current_summary = task_summary_base(
        task,
        attempts=[placeholder_attempt],
        resolved_attempt=None,
        raw_final_score=0.0,
        final_score=0.0,
        final_status="running",
        infra_error=None,
        stop_reason="",
    )
    write_task_run_state(task, summary=current_summary, session_meta=session_meta)

    # Install the attempt's timeline recorder as the module-global active one
    # via plain assignment (``with attach_timeline_recorder(...)`` would
    # require re-indenting the ~250-line body that follows). Must write to
    # ``recording._ACTIVE_RECORDER`` directly — that's the global that
    # ``recording.active_timeline_recorder()`` reads. Writing to a local
    # ``orchestration._ACTIVE_RECORDER`` leaves the recording-side global
    # at None and every ``timeline_span`` silently no-ops.
    _prev_active_recorder = recording._ACTIVE_RECORDER
    recording._ACTIVE_RECORDER = _timeline_recorder
    try:
        final_attempt: dict[str, Any] | None = None
        last_boot_error: dict[str, Any] | None = None
        for container_attempt_index in range(max_container_attempts):
            container_name = ""
            try:
                container_name, started_services = initialize_session_container(
                    image,
                    task,
                    attempt_id=logical_attempt_dir.name,
                    host_out_dir=logical_attempt_dir,
                )
                active_containers.append(container_name)
                session_key = "primary" if container_attempt_index == 0 else f"retry_{container_attempt_index + 1:02d}"
                session_meta["sessions"][session_key] = {
                    "containerName": container_name,
                    "sessionId": AGENT_SESSION_ID,
                    "services": started_services,
                }
                write_task_run_state(task, summary=current_summary, session_meta=session_meta)
                attempt = run_primary_attempt(
                    container_name,
                    task,
                    attempt_no=logical_attempt_no,
                    out_dir=logical_attempt_dir,
                )
                score = dict(attempt.get("score") or {})
                out_dir = Path(str(attempt.get("outDir") or ""))
                transcript_text = ""
                if out_dir and (out_dir / "transcript.jsonl").exists():
                    transcript_text = (out_dir / "transcript.jsonl").read_text(encoding="utf-8", errors="ignore")
                agent_exit_code = None
                meta_path = out_dir / "meta.json" if out_dir else None
                if meta_path and meta_path.exists():
                    try:
                        agent_exit_code = json.loads(meta_path.read_text(encoding="utf-8")).get("agentExitCode")
                    except json.JSONDecodeError:
                        agent_exit_code = None
                agent_result = subprocess.CompletedProcess(
                    args=["openclaw-agent"],
                    returncode=int(agent_exit_code or 0),
                    stdout="",
                    stderr="",
                )
                retry_error = errors.detect_retryable_container_runtime_error(
                    task,
                    turn=1,
                    agent_result=agent_result,
                    out_dir=out_dir,
                    transcript_text=transcript_text,
                    score=score,
                )
                if retry_error and container_attempt_index + 1 < max_container_attempts:
                    session_meta["containerRetries"].append(
                        {
                            "attempt": logical_attempt_no,
                            "retryIndex": container_attempt_index + 1,
                            "type": retry_error["type"],
                            "message": retry_error["message"],
                            "containerName": container_name,
                            "outDir": str(out_dir),
                        }
                    )
                    current_summary = task_summary_base(
                        task,
                        attempts=[placeholder_attempt],
                        resolved_attempt=None,
                        raw_final_score=0.0,
                        final_score=0.0,
                        final_status="running",
                        infra_error=None,
                        stop_reason="",
                    )
                    write_task_run_state(task, summary=current_summary, session_meta=session_meta)
                    if not keep_container:
                        docker_mod.docker_rm(container_name)
                        active_containers = [name for name in active_containers if name != container_name]
                    continue
                final_attempt = attempt
                break
            except PreExecError as exc:
                # A pre_exec script failed (live-API populator). Don't keep
                # looping — a bad board id / missing scope / dead token won't
                # self-heal between container attempts, and blowing the retry
                # budget just multiplies the 429 surface. Stash the full tail
                # so the post-loop bootstrap summary can surface it to the
                # operator, then break to build a pre_exec_failed summary.
                last_boot_error = {
                    "type": "pre_exec_failed",
                    "message": f"pre_exec {exc.script} exit={exc.returncode}: {str(exc.tail or '')[-400:]}",
                    "script": exc.script,
                    "returncode": int(exc.returncode),
                    "tail": exc.tail,
                }
                session_meta["containerRetries"].append(
                    {
                        "attempt": logical_attempt_no,
                        "retryIndex": container_attempt_index + 1,
                        "type": "pre_exec_failed",
                        "message": last_boot_error["message"],
                        "containerName": container_name,
                    }
                )
                if container_name and not keep_container:
                    docker_mod.docker_rm(container_name)
                    active_containers = [name for name in active_containers if name != container_name]
                break
            except Exception as exc:
                retry_error = errors.detect_retryable_container_boot_error(task, exc)
                if retry_error and container_attempt_index + 1 < max_container_attempts:
                    last_boot_error = retry_error
                    session_meta["containerRetries"].append(
                        {
                            "attempt": logical_attempt_no,
                            "retryIndex": container_attempt_index + 1,
                            "type": retry_error["type"],
                            "message": retry_error["message"],
                            "containerName": container_name,
                        }
                    )
                    write_task_run_state(task, summary=current_summary, session_meta=session_meta)
                    if container_name and not keep_container:
                        docker_mod.docker_rm(container_name)
                        active_containers = [name for name in active_containers if name != container_name]
                    continue
                raise
        if final_attempt is None and last_boot_error is not None:
            final_attempt = build_bootstrap_infra_attempt(
                task,
                attempt_no=logical_attempt_no,
                error=last_boot_error,
                out_dir=logical_attempt_dir,
            )
        if final_attempt is None:
            raise RuntimeError("task finished without a final attempt record")
        score = dict((final_attempt or {}).get("score") or {})
        terminal_decision = dict((final_attempt or {}).get("terminalDecision") or {})
        outcome = resolve_attempt_outcome(
            task,
            score,
            terminal_reason=str(terminal_decision.get("reason") or ""),
        )
        final_status = str(outcome["final_status"] or "fail")
        final_score = float(outcome["final_score"] or 0.0)
        resolved_attempt = int((final_attempt or {}).get("attempt") or 0) or None
        if not bool(outcome["passed"]):
            resolved_attempt = None
        current_summary = task_summary_base(
            task,
            attempts=[final_attempt],
            resolved_attempt=resolved_attempt,
            raw_final_score=float(outcome["raw_final_score"] or 0.0),
            final_score=final_score,
            final_status=final_status,
            infra_error=(final_attempt or {}).get("infraError"),
            rate_limit=(final_attempt or {}).get("rateLimit"),
            passed=bool(outcome["passed"]),
            stop_reason=str(outcome["stop_reason"] or ""),
        )
        write_task_run_state(task, summary=current_summary, session_meta=session_meta)
        return current_summary
    finally:
        write_task_run_state(task, summary=current_summary, session_meta=session_meta)
        if not keep_container:
            for container_name in reversed(active_containers):
                docker_mod.docker_rm(container_name)
        # Persist the Execution Timeline Gantt data for the webui. Dump to
        # whichever attempt dir exists on disk (the logical one for the
        # successful path; the latest retry dir if the logical one was
        # replaced). We tolerate any IO error — timeline is advisory.
        try:
            dump_target = logical_attempt_dir
            if not dump_target.exists():
                candidates = list(task_config.task_run_root(task).glob("p*-*"))
                if candidates:
                    dump_target = max(candidates, key=lambda p: p.stat().st_mtime)
            if dump_target.exists():
                _timeline_recorder.dump(dump_target)
        except Exception:
            pass
        recording._ACTIVE_RECORDER = _prev_active_recorder


def run_task(
    task_file: Path,
    image: str = DEFAULT_IMAGE,
    keep_container: bool = False,
    agent_sys: str | None = None,
    model: str | None = None,
    image_model: str | None = None,
    agent_provider: str | None = None,
    codex_role_overrides: dict[str, dict[str, str | None]] | None = None,
    manage_provider_proxies: bool = True,
) -> dict:
    task = task_config.build_runtime_task_spec(
        task_file,
        agent_sys=agent_sys,
        model=model,
        image_model=image_model,
        agent_provider=agent_provider,
        codex_role_overrides=codex_role_overrides,
    )
    if manage_provider_proxies:
        stack = ExitStack()
        try:
            stack.enter_context(task_config.managed_task_proxy_tunnels([task]))
        except Exception as exc:
            stack.close()
            return build_bootstrap_infra_summary(
                task,
                image=image,
                keep_container=keep_container,
                error={
                    "type": "provider_proxy_bootstrap_failed",
                    "message": str(exc),
                },
            )
        try:
            return _run_resolved_task(task, image=image, keep_container=keep_container)
        except Exception as exc:
            return build_bootstrap_infra_summary(
                task,
                image=image,
                keep_container=keep_container,
                error={
                    "type": "run_task_exception",
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
        finally:
            stack.close()
    try:
        return _run_resolved_task(task, image=image, keep_container=keep_container)
    except Exception as exc:
        return build_bootstrap_infra_summary(
            task,
            image=image,
            keep_container=keep_container,
            error={
                "type": "run_task_exception",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )


def batch_run(task_root: Path, parallel: int, image: str = DEFAULT_IMAGE, keep_container: bool = False, agent_sys: str | None = None, model: str | None = None) -> dict:
    if task_root.is_file():
        task_files = [task_root.resolve()]
    else:
        task_files = [path for path in discover_task_files(task_root.resolve()) if "template" not in path.name.lower()]

    runtime_tasks = [
        task_config.build_runtime_task_spec(
            task_file,
            agent_sys=agent_sys,
            model=model,
        )
        for task_file in task_files
    ]

    results = []
    with task_config.managed_task_proxy_tunnels(runtime_tasks):
        if parallel <= 1:
            for task in runtime_tasks:
                results.append(_run_resolved_task(task, image=image, keep_container=keep_container))
        else:
            with ThreadPoolExecutor(max_workers=parallel) as pool:
                futures = {
                    pool.submit(_run_resolved_task, task, image=image, keep_container=keep_container): task.file_path
                    for task in runtime_tasks
                }
                for future in as_completed(futures):
                    task_file = futures[future]
                    try:
                        results.append(future.result())
                    except Exception as exc:
                        # Round-5 Phase 2 (H3): an exception escaping
                        # _run_resolved_task is a harness-level failure
                        # (subprocess crash, OOM, unhandled exception in
                        # the runner itself) — it is NOT a "task fail"
                        # verdict.  Surface it as infra_error so reliability
                        # metrics aren't poisoned by harness bugs.
                        import traceback as _tb
                        results.append({
                            "taskFile": str(task_file),
                            "passed": False,
                            "finalStatus": "infra_error",
                            "infraError": {
                                "type": "batch_run_exception",
                                "message": str(exc),
                                "traceback": _tb.format_exc(),
                            },
                        })

    resolved_agent_sys = task_config.normalize_agent_sys(agent_sys or (load_task(task_files[0], ROOT).agent_sys if task_files else "openclaw"))
    resolved_model = task_config.resolve_model_ref(model or (results[0].get("model") if results else "mixed-model"))
    batch_root = task_config.setting_root(resolved_agent_sys, resolved_model) if results else task_config.RUNS / resolved_agent_sys / "empty"

    from ..status import build_status_counts

    status_counts = build_status_counts(results)
    # Top-level summary fields preserve their pre-Round-6 keys for
    # downstream WebUI / dashboard compatibility, but each one is now a
    # strict equality count against the canonical status name — the old
    # ``fail`` field used ``finalStatus == "fail" or passed is False``,
    # which silently included every non-pass status (infra_error,
    # executor_incomplete, missing) in the fail count.  The full
    # FINAL_STATUS_ORDER breakdown lives under ``statusCounts`` so
    # consumers can read whichever slice they need.
    pass_count = status_counts["pass"]
    infra_error_count = status_counts["infra_error"]
    rate_limit_count = status_counts["rate_limit"]
    fail_count = status_counts["fail"]

    summary = {
        "schema_version": BATCH_SUMMARY_SCHEMA_VERSION,
        "runMode": "local",
        "image": image,
        "agentSys": resolved_agent_sys,
        "model": resolved_model,
        "modelSlug": task_config.model_slug(resolved_model),
        "parallel": parallel,
        "taskCount": len(task_files),
        "pass": pass_count,
        "infra_error": infra_error_count,
        "rate_limit": rate_limit_count,
        "fail": fail_count,
        "statusCounts": status_counts,
        "results": results,
    }
    write_local(batch_root / "batch_summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary
