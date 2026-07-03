"""Infra-error classification for attempts, supervisors, and container boots.

Three distinct families are handled here:

1. **Provider-level errors** observed in the agent transcript
   (:func:`detect_infra_error`) — quota, rate limiting, auth — that
   should demote an attempt into "infra failed, not graded" rather than
   counting as a task loss.

2. **Supervisor transport/runtime errors** (:func:`detect_supervisor_infra_error`)
   — SSL, timeouts, landlock/seccomp — raised by the codex sandbox while
   running the grader.

3. **Retryable container errors**
   (:func:`detect_retryable_container_boot_error`,
   :func:`detect_retryable_container_runtime_error`) — known-flaky
   container bootstrap / browser failures that get a second chance before
   the orchestration surfaces a hard failure.

All three families are pure text classifiers: they take transcript
strings / exception messages and return small dicts or ``None``. No
docker or network calls happen here.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..task import TaskSpec
from .task_config import normalize_agent_sys
from .transcripts import normalize_transcript_text, parse_json_lines


RETRYABLE_CONTAINER_BOOT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "browser_bootstrap_failed",
        (
            "openclaw browser service did not become ready",
            "failed to start chrome cdp",
            "portinuseerror",
            "devtoolsactiveport",
            "failed to connect to the bus",
            "dbus/bus.cc",
            "gateway closed (1012): service restart",
        ),
    ),
    (
        "gateway_bootstrap_failed",
        (
            "gateway service did not become ready",
            "service restart",
        ),
    ),
)
RETRYABLE_CONTAINER_RUNTIME_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "agent_startup_stalled",
        (
            "agent produced no observable progress within startup silence timeout",
        ),
    ),
    (
        "browser_runtime_failed",
        (
            # Chrome CDP startup failures — typically port conflict or
            # Chromium process failure that actually prevents any browser work.
            "failed to start chrome cdp",
            "portinuseerror",
            "devtoolsactiveport",
            # Chromium session drops mid-run — same as above.
            "tab not found",
            "browser has disconnected",
            "target closed",
            "page has been closed",
            # openclaw's native browser control-service restart signal (fatal
            # for openclaw's MCP browser path). agent-browser does not use
            # this gateway, so the error never fires there — safe to keep.
            "gateway closed (1012): service restart",
            # NOTE: DBus socket-connect warnings from Chromium
            # (``failed to connect to the bus`` / ``dbus/bus.cc``) used to
            # live here, but they are NOT fatal: Chromium prints them on
            # every startup when /run/dbus/system_bus_socket is missing
            # (no desktop session), yet continues to run. agent-browser's
            # Chromium exhibits them on every invocation — keeping them
            # in this set triggered a full container-boot retry for every
            # edict screenshot and broke the sub-agent pipeline. Removed.
        ),
    ),
)

_AGENT_STARTUP_STALLED_TYPE = "agent_startup_stalled"
_AGENT_STARTUP_STALLED_NEEDLE = "agent produced no observable progress within startup silence timeout"
_AGENT_STARTUP_MONITOR_PREFIX = "[clawbench-monitor]"


def detect_infra_error(transcript_text: str, tool_usage: dict | None = None) -> dict | None:
    """Detect infra / quota / rate-limit errors from the executor transcript.

    Historically this returned both generic ``provider_rate_limited`` and
    ``provider_quota_exceeded`` types as infra_error. We now mark these with
    ``rate_limit=True`` so the caller can route them to the dedicated
    ``rate_limit`` attempt status (peer of ``infra_error``) instead of
    conflating them with transport/sandbox bugs.

    The fallback text scan deliberately ignores ``toolResult`` payloads:
    skills injected into the workspace often ship documentation that
    *describes* HTTP 429 handling as example code (e.g. Next.js rate-limit
    snippets), and scanning those would produce false positives. Only
    assistant-authored message text is inspected, and the generic-needle
    set is limited to provider error shapes a real rate-limit event would
    actually emit.
    """
    if not transcript_text.strip():
        return None
    normalized_transcript = normalize_transcript_text(transcript_text)
    error_messages: list[str] = []
    assistant_text_segments: list[str] = []
    for payload in parse_json_lines(normalized_transcript):
        if payload.get("type") != "message":
            continue
        message = payload.get("message") or {}
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    seg = str(item.get("text") or "").strip()
                    if seg:
                        assistant_text_segments.append(seg)
        elif isinstance(content, str) and content.strip():
            assistant_text_segments.append(content)
        if str(message.get("stopReason") or "").lower() != "error":
            continue
        error = str(message.get("errorMessage") or "").strip()
        if error:
            error_messages.append(error)
    assistant_only_text = " ".join(assistant_text_segments).lower()
    normalized = " | ".join(error_messages).lower()
    if not normalized:
        quota_needles = (
            "allocated quota exceeded",
            "insufficient_quota",
            "quota exceeded",
            '"code":"throttling"',
            "hour allocated quota exceeded",
        )
        rate_limit_needles = (
            "rate_limit_exceeded",
            "rate_limit_error",
            "status code: 429",
            "status code 429",
            "http 429",
            "http/1.1 429",
            '"code": 429',
            '"status": 429',
            "error code 429",
        )
        if any(needle in assistant_only_text for needle in quota_needles):
            normalized = assistant_only_text
            error_messages.append("provider quota exceeded")
        elif any(needle in assistant_only_text for needle in rate_limit_needles):
            normalized = assistant_only_text
            error_messages.append("provider rate limited")
    if not normalized:
        return None
    tool_counts = ((tool_usage or {}).get("tool_counts") or {}) if isinstance(tool_usage, dict) else {}
    no_tool_progress = sum(int(value or 0) for value in tool_counts.values()) == 0
    if any(needle in normalized for needle in ["allocated quota exceeded", "insufficient_quota", "quota exceeded"]):
        return {
            "type": "provider_quota_exceeded",
            "message": error_messages[-1],
            "noToolProgress": no_tool_progress,
            "rate_limit": True,
        }
    if any(needle in normalized for needle in ["rate limit", "too many requests", "429"]):
        return {
            "type": "provider_rate_limited",
            "message": error_messages[-1],
            "noToolProgress": no_tool_progress,
            "rate_limit": True,
        }
    return None


# Patterns shipped by the openclaw agent (the embedded Claude-style loop)
# when a provider returns HTTP 429. The agent emits structured JSON log
# entries like:
#   {"...","failoverReason":"rate_limit","rawErrorPreview":"429 status code (no body)"}
# These never surface as assistant message text (the transcript only
# records an empty ``stopReason=error`` envelope), so ``detect_infra_error``
# cannot see them — we scan the raw agent-side logs instead.
_OPENCLAW_RATE_LIMIT_NEEDLES: tuple[str, ...] = (
    '"failoverreason":"rate_limit"',
    '"failoverreason": "rate_limit"',
    "failoverreason=rate_limit",
    "failoverreason: rate_limit",
    '"rawerrorpreview":"429 status code',
    '"rawerrorpreview": "429 status code',
    "429 status code",
    "http 429",
    "status code 429",
    "rate_limit_exceeded",
)


def _iter_openclaw_log_candidates(out_dir: Path):
    """Yield host-side paths likely to contain openclaw agent logs.

    ``collect_attempt_artifacts`` mirrors ``/tmp/openclaw/`` into
    ``<attempt>/openclaw/`` (see that function for details). The 429
    structured entries can land in any of that dir's ``*.log`` or
    session jsonl files, plus the runner's own ``logs/agent.log``.
    """
    try:
        base = Path(out_dir)
    except Exception:
        return
    openclaw_dir = base / "openclaw"
    if openclaw_dir.is_dir():
        for ext in ("*.log", "*.jsonl", "**/*.log", "**/*.jsonl"):
            for candidate in openclaw_dir.glob(ext):
                if candidate.is_file():
                    yield candidate
    agent_log = base / "logs" / "agent.log"
    if agent_log.is_file():
        yield agent_log


def detect_openclaw_rate_limit(out_dir: Path, *, max_chars_per_file: int = 64000) -> dict | None:
    """Scan the openclaw agent log on disk for structured 429 / rate-limit markers.

    Returns a dict compatible with ``detect_infra_error`` (``type`` +
    ``message`` + ``noToolProgress`` + ``rate_limit``) or ``None``.
    Only used for backends that write the openclaw embedded agent log
    (openclaw / openclaw_edict); no-op otherwise because the log dir
    won't exist.
    """
    seen: set[Path] = set()
    for path in _iter_openclaw_log_candidates(out_dir):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not raw:
            continue
        # Only scan the tail; rate-limit bursts are recent events and
        # scanning multi-MB log heads would be wasted work.
        tail = raw[-max_chars_per_file:] if len(raw) > max_chars_per_file else raw
        normalized = tail.lower()
        if not any(needle in normalized for needle in _OPENCLAW_RATE_LIMIT_NEEDLES):
            continue
        # Best-effort excerpt: pull a window around the first hit for the
        # operator log / WebUI display.
        first_hit_idx = min(
            (normalized.find(needle) for needle in _OPENCLAW_RATE_LIMIT_NEEDLES if needle in normalized),
            default=-1,
        )
        if first_hit_idx >= 0:
            start = max(0, first_hit_idx - 240)
            end = min(len(tail), first_hit_idx + 720)
            excerpt = tail[start:end].strip()
        else:
            excerpt = tail[-1200:].strip()
        return {
            "type": "provider_rate_limited",
            "message": excerpt or "openclaw agent log reports HTTP 429 / rate_limit",
            "noToolProgress": True,
            "rate_limit": True,
            "source": str(path),
        }
    return None


def detect_supervisor_infra_error(message: str) -> dict | None:
    normalized = (message or "").strip().lower()
    if not normalized:
        return None
    # Rate-limit comes first so "429"/"too many requests" does not get
    # swallowed by the timeout / transport needles below. When the
    # grader Codex call returns 429, treat it as a rate_limit peer of
    # infra_error so the WebUI can surface it distinctly (the operator's
    # quota problem is not a sandbox bug).
    rate_limit_needles = [
        "429",
        "too many requests",
        "rate limit",
        "rate_limited",
        "rate-limited",
        "throttl",
        "quota exceeded",
        "insufficient_quota",
        "allocated quota",
    ]
    if any(needle in normalized for needle in rate_limit_needles):
        return {
            "type": "grader_rate_limited",
            "message": message,
            "noToolProgress": False,
            "rate_limit": True,
        }
    transport_needles = [
        "stream disconnected before completion",
        "stream closed",
        "urlopen error",
        "eof occurred in violation of protocol",
        "_ssl.c",
        "ssl",
        "connection reset",
        "connection aborted",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "bad gateway",
        "service unavailable",
    ]
    if any(needle in normalized for needle in transport_needles):
        return {
            "type": "grader_transport_error",
            "message": message,
            "noToolProgress": False,
        }
    runtime_needles = [
        "landlock",
        "seccomp",
        "sandbox install error",
        "sandbox",
        "operation not permitted",
    ]
    if any(needle in normalized for needle in runtime_needles):
        return {
            "type": "grader_runtime_error",
            "message": message,
            "noToolProgress": False,
        }
    # Docker-side infra failures (missing image, registry unreachable, etc.).
    # Added after a worker-drop test where a worker lacked the clawbench-codex
    # image: every supervisor invocation died with "Unable to find image" but
    # went unrecognised, so the harness fabricated fake
    # terminal_failure verdicts.  Recognising it as infra lets the harness
    # write an honest verdict=infra_error and preflight (Phase 1) catches the
    # whole class of problem before dispatching.
    docker_needles = [
        "unable to find image",
        "pull access denied",
        "repository does not exist",
        "manifest unknown",
        "no such image",
        "image not found",
        "docker: error response from daemon",
        "cannot connect to the docker daemon",
    ]
    if any(needle in normalized for needle in docker_needles):
        return {
            "type": "docker_image_missing",
            "message": message,
            "noToolProgress": True,
        }
    return None


def should_retry_transient_followup(task: TaskSpec, turn: int, agent_result: subprocess.CompletedProcess[str], out_dir: Path) -> bool:
    if turn <= 1:
        return False
    if normalize_agent_sys(task.agent_sys) not in {"openclaw", "openclaw_edict"}:
        return False
    if agent_result.returncode != 247:
        return False
    agent_log = out_dir / "logs" / "agent.log"
    tail = agent_log.read_text(encoding="utf-8", errors="ignore")[-4000:] if agent_log.exists() else ""
    return "gateway closed (1012): service restart" in tail or "service restart" in tail


def _attempt_agent_log_tail(out_dir: Path, *, max_chars: int = 4000) -> str:
    log_path = out_dir / "logs" / "agent.log"
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="ignore")[-max_chars:]


def _matching_error_excerpt(text: str, needles: tuple[str, ...], *, max_chars: int = 1200) -> str:
    raw = str(text or "")
    normalized = raw.lower()
    for needle in needles:
        index = normalized.find(needle)
        if index < 0:
            continue
        start = max(0, index - 240)
        end = min(len(raw), index + 720)
        return raw[start:end].strip()
    return raw[-max_chars:].strip()


def _match_retryable_container_error(*texts: str, pattern_set: tuple[tuple[str, tuple[str, ...]], ...]) -> dict[str, Any] | None:
    for error_type, needles in pattern_set:
        for text in texts:
            raw = str(text or "")
            if not raw.strip():
                continue
            normalized = raw.lower()
            if any(needle in normalized for needle in needles):
                return {
                    "type": error_type,
                    "message": _matching_error_excerpt(raw, needles),
                }
    return None


def _match_real_agent_startup_stalled(*texts: str) -> dict[str, Any] | None:
    """Match only the watchdog's own startup-stalled log line.

    The executor can legitimately print process command lines while
    debugging. Those command lines include the embedded watchdog Python
    source, including the startup-stalled string literal. Treating that
    transcript text as a real watchdog event causes false container retries.
    """
    for text in texts:
        raw = str(text or "")
        if not raw.strip():
            continue
        for line in raw.splitlines():
            stripped = line.strip()
            normalized = stripped.lower()
            if (
                stripped.startswith(_AGENT_STARTUP_MONITOR_PREFIX)
                and _AGENT_STARTUP_STALLED_NEEDLE in normalized
            ):
                return {
                    "type": _AGENT_STARTUP_STALLED_TYPE,
                    "message": stripped,
                }
    return None


def _runtime_patterns_without_startup_stalled() -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (error_type, needles)
        for error_type, needles in RETRYABLE_CONTAINER_RUNTIME_PATTERNS
        if error_type != _AGENT_STARTUP_STALLED_TYPE
    )


def detect_retryable_container_boot_error(task: TaskSpec, exc: BaseException) -> dict[str, Any] | None:
    # Pre-exec script failures (live-API refresh before container start)
    # get a retry budget regardless of agent_sys — transient API blips are
    # the common failure mode and a single retry usually recovers.
    from .container_lifecycle import PreExecError
    if isinstance(exc, PreExecError):
        return {
            "type": "pre_exec_failed",
            "message": f"pre_exec {exc.script} exit={exc.returncode}: {exc.tail[-400:]}",
        }
    if normalize_agent_sys(task.agent_sys) not in {"openclaw", "openclaw_edict"}:
        return None
    return _match_retryable_container_error(str(exc), pattern_set=RETRYABLE_CONTAINER_BOOT_PATTERNS)


def detect_retryable_container_runtime_error(
    task: TaskSpec,
    *,
    turn: int,
    agent_result: subprocess.CompletedProcess[str],
    out_dir: Path,
    transcript_text: str,
    score: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if normalize_agent_sys(task.agent_sys) not in {"openclaw", "openclaw_edict"}:
        return None
    if turn != 1:
        return None
    decision = dict(score or {})
    if str(decision.get("verdict") or "").strip().lower() == "continue":
        return None
    agent_log_tail = _attempt_agent_log_tail(out_dir)
    startup_candidate = _match_real_agent_startup_stalled(
        agent_result.stdout,
        agent_result.stderr,
        agent_log_tail,
    )
    if startup_candidate:
        startup_candidate["turn"] = turn
        startup_candidate["noToolProgress"] = False
        return startup_candidate
    candidate = _match_retryable_container_error(
        agent_result.stdout,
        agent_result.stderr,
        transcript_text,
        agent_log_tail,
        pattern_set=_runtime_patterns_without_startup_stalled(),
    )
    if not candidate:
        return None
    candidate["turn"] = turn
    candidate["noToolProgress"] = False
    return candidate
