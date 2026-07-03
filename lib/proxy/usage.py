"""Proxy-adapter usage/log discovery and reader helpers.

These helpers inspect the JSON-Lines logs written by the adapter
subprocess spawned in ``adapter.py`` / ``core.start_proxy_adapter``.
They are consumed by the runner's per-cycle token accounting (see
``lib/runner/artifacts.py``) to slice per-call ``event == "usage"``
records into attempt-local ledgers.

The discovery helpers cross-reference the proxy registry under
``PROXY_REGISTRY_ROOT`` (written by ``acquire_shared_proxy_tunnel``)
and, as a fallback, ``/proc/<pid>/cmdline`` of each registered adapter
pid — the registry may predate our log-path persistence, or the
adapter may have been started by a different Clawbench checkout that
happens to share this tunnel.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Deliberately module-qualified: tests patch the constants via string
# path (e.g. ``monkeypatch.setattr("lib.proxy.core.PROXY_REGISTRY_ROOT",
# tmp)``), so ``core.PROXY_REGISTRY_ROOT`` must resolve through the
# module each call. A ``from .core import PROXY_REGISTRY_ROOT`` would
# snapshot the value at import time and silently defeat those tests.
from . import core, tunnel


def _log_path_from_pid_cmdline(pid: int) -> str:
    """Best-effort Linux-only recovery of an adapter's log path by
    reading ``/proc/<pid>/cmdline``. The adapter was launched with its
    log path as the last argv. We return the empty string on any
    failure (pid dead, non-Linux, unparseable cmdline).
    """
    if not pid or int(pid) <= 0:
        return ""
    try:
        raw = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return ""
    except OSError:
        return ""
    parts = [p.decode("utf-8", errors="ignore") for p in raw.split(b"\x00") if p]
    if not parts:
        return ""
    # The adapter's command is ``python3 -c <script> listen_host
    # listen_port upstream_base adapter log_path`` — log_path is the
    # final argv. But only trust it if it actually looks like a path
    # (contains '/' or '\\' and isn't just the python script).
    candidate = parts[-1]
    if "/" in candidate or "\\" in candidate:
        if "proxy_adapter" in candidate or candidate.endswith(".log"):
            return candidate
    return ""


def discover_active_proxy_adapter_log_paths() -> list[Path]:
    """Return the log paths of every currently-active proxy adapter.

    Resolution order for each registry entry (most trusted first):
    1. ``adapter.log_path`` in the registry JSON (set by
       ``acquire_shared_proxy_tunnel`` on adapters started after this
       release).
    2. ``/proc/<pid>/cmdline`` of the registered adapter pid — falls
       back to this for registries written by earlier code that didn't
       persist the log_path, including across a different Clawbench
       checkout that happens to share this adapter.
    3. This process's own ``PROXY_ADAPTER_LOG_PATH`` — last-resort
       guess for when nothing else worked.

    Deduplicates and preserves the order of discovery.
    """
    return _discover_log_paths(
        registry_key="log_path",
        default_path=core.PROXY_ADAPTER_LOG_PATH,
    )


def discover_active_proxy_adapter_request_log_paths() -> list[Path]:
    """Companion of ``discover_active_proxy_adapter_log_paths`` for the
    request-transcript log (full request+response payloads, one JSON-
    Lines entry per HTTP call). Returns an empty list when no adapter
    has been recorded with a ``request_log_path`` and no default file
    exists yet — callers should treat that as "no transcript captured"
    rather than an error.
    """
    return _discover_log_paths(
        registry_key="request_log_path",
        default_path=core.PROXY_ADAPTER_REQUEST_LOG_PATH,
    )


def _discover_log_paths(*, registry_key: str, default_path: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        raw = str(raw or "").strip()
        if not raw or raw in seen:
            return
        seen.add(raw)
        found.append(Path(raw))

    if core.PROXY_REGISTRY_ROOT.exists():
        for entry in sorted(core.PROXY_REGISTRY_ROOT.glob("*.json")):
            payload = tunnel._read_proxy_registry_state(entry)
            adapter = payload.get("adapter") if isinstance(payload, dict) else None
            if not isinstance(adapter, dict):
                continue
            stored = str(adapter.get(registry_key) or "").strip()
            if stored:
                _add(stored)
                continue
            # Registry pre-dates this column being persisted: only the
            # primary usage log can be recovered from ``/proc`` (the
            # adapter cmdline historically only carried argv[5]).
            if registry_key == "log_path":
                pid = int(adapter.get("pid") or 0)
                recovered = _log_path_from_pid_cmdline(pid)
                if recovered:
                    _add(recovered)
    _add(str(default_path.resolve()))
    return found


def read_proxy_usage_events(
    log_path: Path | str | None,
    *,
    start_ts: float,
    end_ts: float,
) -> list[dict[str, Any]]:
    """Read per-call usage events from a SINGLE proxy-adapter log file.

    The adapter writes JSON-Lines events to a log file it was given on
    launch. This helper filters for ``event == "usage"`` entries whose
    ``ts`` falls in the half-open interval ``[start_ts, end_ts)`` and
    returns them in order. The half-open interval makes back-to-back
    cycle slices disjoint — consecutive cycles never double-count.

    Callers that want events across all currently-active adapters (the
    common case, since a shared adapter may have been started by a
    different checkout and logs elsewhere) should use
    ``read_proxy_usage_events_across_all_logs`` instead.

    Malformed lines and missing files are silently skipped so that a
    dirty log never aborts an attempt.
    """
    if log_path is None:
        return []
    path = Path(log_path)
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("event") != "usage":
            continue
        ts = event.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        if ts < start_ts or ts >= end_ts:
            continue
        events.append(event)
    return events


def read_proxy_request_events(
    log_path: Path | str | None,
    *,
    start_ts: float,
    end_ts: float,
) -> list[dict[str, Any]]:
    """Read full-transcript ``event == "interaction"`` entries from a
    SINGLE request-log file. Same time-window semantics as
    ``read_proxy_usage_events`` so callers can use one helper across both
    logs. Filters by ``ts_response`` (falling back to ``ts_request`` so
    early-emitted events from a future adapter version still match).
    """
    if log_path is None:
        return []
    path = Path(log_path)
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("event") != "interaction":
            continue
        ts_value = event.get("ts_response") or event.get("ts_request")
        if not isinstance(ts_value, (int, float)):
            continue
        if ts_value < start_ts or ts_value >= end_ts:
            continue
        events.append(event)
    return events


def read_proxy_request_events_across_all_logs(
    *,
    start_ts: float,
    end_ts: float,
    extra_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Cross-log version of ``read_proxy_request_events``. Mirrors the
    discovery + dedup story of
    ``read_proxy_usage_events_across_all_logs`` but for the request
    transcript log. Dedupes on ``(ts_request, endpoint, task_id)`` so a
    log surfaced twice via symlinks doesn't inflate the per-attempt
    transcript.
    """
    paths: list[Path] = []
    seen_paths: set[str] = set()
    for path in discover_active_proxy_adapter_request_log_paths():
        resolved = str(path.resolve()) if path else ""
        if resolved and resolved not in seen_paths:
            seen_paths.add(resolved)
            paths.append(path)
    for extra in extra_paths or []:
        resolved = str(Path(extra).resolve())
        if resolved and resolved not in seen_paths:
            seen_paths.add(resolved)
            paths.append(Path(extra))

    merged: list[dict[str, Any]] = []
    seen_events: set[tuple] = set()
    for path in paths:
        for event in read_proxy_request_events(path, start_ts=start_ts, end_ts=end_ts):
            key = (
                float(event.get("ts_request") or 0.0),
                str(event.get("endpoint") or ""),
                str(event.get("task_id") or ""),
                int(event.get("status_code") or 0),
            )
            if key in seen_events:
                continue
            seen_events.add(key)
            merged.append(event)
    merged.sort(key=lambda e: float(e.get("ts_response") or e.get("ts_request") or 0.0))
    return merged


def read_proxy_usage_events_across_all_logs(
    *,
    start_ts: float,
    end_ts: float,
    extra_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Read usage events from every proxy-adapter log Clawbench can
    discover right now, across all currently-active adapters (picked up
    from the registry and ``/proc``).

    This is the right entry point for role-scoped token accounting — a
    single adapter log is only reliable when the reader is the same
    checkout that launched the adapter. In shared-adapter scenarios (a
    different Clawbench checkout already owned the adapter, or the
    executor and the codex roles are served by distinct adapter ports
    that happened to be launched with distinct log paths), merging all
    discovered logs is the only way to not drop events.

    De-duplicates events by ``(ts, endpoint, prompt_tokens,
    completion_tokens)`` so that a file that is actually the same log
    surfaced under two different discovery paths (identical paths after
    symlink resolution, etc.) doesn't inflate the numbers.
    """
    paths: list[Path] = []
    seen_paths: set[str] = set()
    for path in discover_active_proxy_adapter_log_paths():
        resolved = str(path.resolve()) if path else ""
        if resolved and resolved not in seen_paths:
            seen_paths.add(resolved)
            paths.append(path)
    for extra in extra_paths or []:
        resolved = str(Path(extra).resolve())
        if resolved and resolved not in seen_paths:
            seen_paths.add(resolved)
            paths.append(Path(extra))

    merged: list[dict[str, Any]] = []
    seen_events: set[tuple] = set()
    for path in paths:
        for event in read_proxy_usage_events(path, start_ts=start_ts, end_ts=end_ts):
            key = (
                float(event.get("ts") or 0.0),
                str(event.get("endpoint") or ""),
                int(event.get("prompt_tokens") or 0),
                int(event.get("completion_tokens") or 0),
                int(event.get("total_tokens") or 0),
            )
            if key in seen_events:
                continue
            seen_events.add(key)
            merged.append(event)
    merged.sort(key=lambda e: float(e.get("ts") or 0.0))
    return merged
