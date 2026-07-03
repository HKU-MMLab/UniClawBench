"""Token + request accounting for one attempt.

Extracted from ``lib/runner/artifacts.py``.  The ledger writes
``<attempt>/usage_ledger.jsonl`` (one line per API response observed at
the proxy adapter) and ``<attempt>/usage.json`` (rolled-up totals by
role/turn), and uses two adapter kinds —
``drop_max_tokens`` for the executor side and ``responses_via_chat``
for the Codex (supervisor / user_simulator) side — to attribute each
event to a role without cross-contamination even when wall-clock
windows briefly overlap.

A transcript-based fallback (``compute_executor_token_usage``) covers
the executor bucket when the proxy adapter log is unavailable (e.g. an
out-of-band adapter started from a different checkout).  Supervisor /
user_simulator totals are adapter-only — their transcripts live in
separate Codex workspaces and aren't merged into the attempt tree.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..proxy import (
    read_proxy_request_events,
    read_proxy_request_events_across_all_logs,
    read_proxy_usage_events,
    read_proxy_usage_events_across_all_logs,
)
from ..task import TaskSpec
from .task_config import normalize_agent_sys


# ── Per-adapter role attribution ─────────────────────────────────────
# Our two adapter kinds today are:
#   ``drop_max_tokens``   → executor-side (openclaw / nanobot going
#                           through a chat-completions-compatible provider).
#   ``responses_via_chat`` → Codex-side, i.e. answer_supervisor AND
#                           public_user_simulator on port 9002 (they
#                           run in separate Codex containers but share
#                           the adapter).
# The two-codex-roles case is disambiguated *by time window*, not by
# the adapter field — ``run_answer_supervisor`` and
# ``run_public_user_simulator`` run strictly sequentially so a
# [start_ts, end_ts) slice belongs to exactly one of them.
_EXECUTOR_ADAPTER_KINDS = {"drop_max_tokens"}
_CODEX_ADAPTER_KINDS = {"responses_via_chat"}


def attempt_task_id(out_dir: Path) -> str:
    """The stable per-attempt identifier the proxy adapter sees in the
    URL prefix and tags into every usage / interaction event.

    Today this is the attempt's stage directory name (e.g. ``p1-abc123``)
    which already has a UUID-derived suffix and is unique across all
    parallel attempts of the same task on the same host. Centralising it
    here means callers can switch the underlying scheme later (e.g. to a
    salted hash for cross-host deduping) without touching every config-
    injection or ledger call site.
    """
    return Path(out_dir).name


def _request_event_dedup_key(event: dict[str, Any]) -> tuple:
    return (
        float(event.get("ts_request") or 0.0),
        float(event.get("ts_response") or 0.0),
        str(event.get("endpoint") or ""),
        str(event.get("task_id") or ""),
        int(event.get("status_code") or 0),
    )


def _is_executor_adapter_event(event: dict[str, Any]) -> bool:
    kind = str(event.get("adapter") or "").strip().lower()
    # Fallback: if the event pre-dates the adapter field being
    # included (shouldn't happen in current releases but we keep
    # compat), don't blindly count it — safer to drop than to mix
    # roles.
    if not kind:
        return False
    return kind in _EXECUTOR_ADAPTER_KINDS


def _is_codex_adapter_event(event: dict[str, Any]) -> bool:
    kind = str(event.get("adapter") or "").strip().lower()
    if not kind:
        return False
    return kind in _CODEX_ADAPTER_KINDS


def _filter_events_by_task_id(events: list[dict[str, Any]], task_id: str) -> list[dict[str, Any]]:
    """Per-task isolation filter for cross-attempt parallel safety.

    Behavior:
    - If ``task_id`` is empty (caller doesn't know its task_id, or this
      is a legacy call site that hasn't been migrated yet), return
      ``events`` unchanged. The pre-existing time-window + adapter-kind
      filters remain the only attribution.
    - If ``task_id`` is set: keep events whose ``task_id`` field equals
      the given id, AND keep events that have NO ``task_id`` field at
      all (legacy adapters that pre-date the per-task URL prefix). The
      latter is the migration-window safety: an unrouted client doesn't
      lose its tokens just because we already upgraded the runner. Once
      the matching attempt has any prefix-routed events of its own, the
      legacy fallthrough doesn't matter — we'd still pick those up too,
      but realistically a single attempt is either entirely prefixed or
      entirely legacy because the client config is set once at start.
    """
    needle = (task_id or "").strip()
    if not needle:
        return events
    filtered: list[dict[str, Any]] = []
    for event in events:
        event_task_id = str(event.get("task_id") or "").strip()
        if not event_task_id or event_task_id == needle:
            filtered.append(event)
    return filtered


def append_attempt_request_log(
    out_dir: Path,
    *,
    task_id: str,
    start_ts: float,
    end_ts: float,
    log_path: Path | None = None,
) -> int:
    """Slice the proxy adapter request-transcript log for events
    belonging to ``task_id`` and append them to
    ``<out_dir>/requests.jsonl``. One line per HTTP call.

    Filtering order:
    1. ``event == "interaction"`` (only these carry full payloads)
    2. ``ts_response`` (or ``ts_request`` when ``ts_response`` is
       missing) within the half-open ``[start_ts, end_ts)`` window
    3. ``task_id`` matches the provided value, OR the event has no
       ``task_id`` field at all (legacy adapter that pre-dates the
       per-task URL prefix). Mirrors the ledger's backward-compat
       posture so a partial upgrade doesn't drop transcripts.

    Returns the number of events appended.
    """
    if log_path is not None:
        events = read_proxy_request_events(log_path, start_ts=start_ts, end_ts=end_ts)
    else:
        events = read_proxy_request_events_across_all_logs(start_ts=start_ts, end_ts=end_ts)
    needle = (task_id or "").strip()
    if needle:
        kept: list[dict[str, Any]] = []
        for event in events:
            event_task_id = str(event.get("task_id") or "").strip()
            if not event_task_id or event_task_id == needle:
                kept.append(event)
        events = kept
    if not events:
        return 0
    out_path = Path(out_dir) / "requests.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Defensive in-file dedup: if the slicer is invoked twice for an
    # overlapping time window (e.g. two cycles whose end_ts/start_ts
    # touch and we add 1ms safety on either side) we'd otherwise rewrite
    # the same row. Hash on the few stable identifying fields.
    seen: set[tuple] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                existing = json.loads(line)
            except Exception:
                continue
            seen.add(_request_event_dedup_key(existing))
    appended = 0
    with out_path.open("a", encoding="utf-8") as fh:
        for event in events:
            key = _request_event_dedup_key(event)
            if key in seen:
                continue
            seen.add(key)
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
            appended += 1
    return appended


def append_executor_usage_ledger(
    out_dir: Path,
    *,
    turn: int,
    start_ts: float,
    end_ts: float,
    task_id: str = "",
    log_path: Path | None = None,
    retry_kind: str = "",
    retry_index: int = 0,
) -> int:
    """Slice the proxy adapter logs for **executor-window** usage events
    and append them to ``<out_dir>/usage_ledger.jsonl`` tagged
    ``category="executor"`` with the cycle's ``turn``.

    Three things make the attribution correct without hard-coding paths:

    1. We discover ALL currently-active adapter log files (via
       ``discover_active_proxy_adapter_log_paths``) — the registry
       stores each adapter's real log path, so a different Clawbench
       checkout that happens to share the same shared adapter still
       finds the right file to read. The only-fall-back-to-my-own-ROOT
       hardcode is gone.

    2. Within the merged events we filter by the adapter KIND. In
       Clawbench the executor-side adapter is ``drop_max_tokens`` and
       the Codex-side (supervisor + user_simulator) is
       ``responses_via_chat`` — they're distinct OS processes on
       distinct ports and every event carries an ``adapter`` field
       identifying which one served it. Keeping only
       ``drop_max_tokens`` events here guarantees that even if a
       Codex call leaked into the executor's wall-clock window (e.g.
       a stray retry after the turn actually ended), it cannot
       contaminate the executor's token count.

    3. When ``task_id`` is provided AND the discovered events carry a
       ``task_id`` field (adapter ≥ this release), we additionally
       filter to events whose ``task_id`` matches. This is what stops
       parallel attempts of the same role from stealing each other's
       events when their wall-clock windows overlap on the same shared
       adapter. Events without a ``task_id`` field (legacy adapters or
       legacy clients that did not route via the per-task URL prefix)
       fall through unchanged so older runs keep working — the
       time-window + adapter-kind filters that came before still apply.

    Returns the number of events appended.
    """
    if log_path is not None:
        events = read_proxy_usage_events(log_path, start_ts=start_ts, end_ts=end_ts)
    else:
        events = read_proxy_usage_events_across_all_logs(start_ts=start_ts, end_ts=end_ts)
    # Keep only executor-side adapter events. See the docstring: this
    # is the role-attribution step that ``read_proxy_usage_events``
    # alone can't do.
    events = [ev for ev in events if _is_executor_adapter_event(ev)]
    events = _filter_events_by_task_id(events, task_id)
    if not events:
        return 0
    ledger_path = out_dir / "usage_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        for event in events:
            entry = {
                "category": "executor",
                "turn": int(turn),
                "ts": event.get("ts"),
                "model": str(event.get("model") or ""),
                "endpoint": str(event.get("endpoint") or ""),
                "adapter": str(event.get("adapter") or ""),
                # Round-trip the adapter's task_id into the ledger row for
                # audit. The filter above already guarantees events match
                # the caller's ``task_id`` — propagating it makes per-row
                # provenance grep-able after the fact.
                "task_id": str(event.get("task_id") or ""),
                "prompt_tokens": int(event.get("prompt_tokens") or 0),
                "completion_tokens": int(event.get("completion_tokens") or 0),
                "total_tokens": int(event.get("total_tokens") or 0),
                "estimated_cost": 0.0,
                "call_count": 1,
            }
            # Round 8 / A4: if this ledger append is from an executor
            # rate-limit retry window, tag it so downstream consumers can
            # distinguish retry tokens from initial-turn tokens without
            # losing them in the cycle total.  Default args keep the
            # initial-turn behavior unchanged.
            if retry_kind:
                entry["retry_kind"] = retry_kind
                entry["retry_index"] = int(retry_index)
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(events)


def append_role_usage_ledger(
    out_dir: Path,
    *,
    role: str,
    turn: int,
    start_ts: float,
    end_ts: float,
    task_id: str = "",
    log_path: Path | None = None,
) -> int:
    """Slice proxy adapter logs for a SINGLE codex role
    (``answer_supervisor`` or ``public_user_simulator``) and append to
    ``<out_dir>/usage_ledger.jsonl`` tagged with ``category=role``.

    The caller must invoke this AFTER the role's Codex run has
    returned so ``end_ts = time.time()`` captures everything the role
    produced. Only events coming out of the codex-side adapter
    (``responses_via_chat``) are counted — executor events on the
    other adapter cannot sneak in even if they happened during the
    same wall-clock window.

    See ``append_executor_usage_ledger`` for the per-task ``task_id``
    filter — same semantics here so that two parallel attempts whose
    supervisor windows overlap on the same Codex adapter don't
    cross-attribute.

    Returns the number of events appended.
    """
    if role not in {"answer_supervisor", "public_user_simulator", "supervisor", "user_simulator"}:
        raise ValueError(f"unsupported role for usage ledger: {role!r}")
    # Canonicalize the ledger category name. Keep the ``answer_`` /
    # ``public_`` prefixes out of the ledger so the WebUI rollup can
    # group on a stable short name.
    category = "supervisor" if role in {"answer_supervisor", "supervisor"} else "user_simulator"
    if log_path is not None:
        events = read_proxy_usage_events(log_path, start_ts=start_ts, end_ts=end_ts)
    else:
        events = read_proxy_usage_events_across_all_logs(start_ts=start_ts, end_ts=end_ts)
    events = [ev for ev in events if _is_codex_adapter_event(ev)]
    events = _filter_events_by_task_id(events, task_id)
    if not events:
        return 0
    ledger_path = out_dir / "usage_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        for event in events:
            entry = {
                "category": category,
                "turn": int(turn),
                "ts": event.get("ts"),
                "model": str(event.get("model") or ""),
                "endpoint": str(event.get("endpoint") or ""),
                "adapter": str(event.get("adapter") or ""),
                "task_id": str(event.get("task_id") or ""),
                "prompt_tokens": int(event.get("prompt_tokens") or 0),
                "completion_tokens": int(event.get("completion_tokens") or 0),
                "total_tokens": int(event.get("total_tokens") or 0),
                "estimated_cost": 0.0,
                "call_count": 1,
            }
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(events)


def build_attempt_usage_payload(out_dir: Path, task: TaskSpec) -> dict[str, Any]:
    """Build ``<attempt>/usage.json`` combining every source we have.

    Primary source — ``<attempt>/usage_ledger.jsonl`` written by
    ``append_executor_usage_ledger`` and ``append_role_usage_ledger``.
    Each line is one API response (from the proxy adapter log,
    filtered by adapter kind + time window), tagged with its role —
    this is the ground truth the user asked for: "through the API
    gateway, record real usage, and separate executor from supervisor
    and user_simulator". The ledger is the most trustworthy source
    because it's filtered server-side by adapter identity (so codex
    events can't sneak into executor totals even if wall-clock windows
    briefly overlap).

    Fallback for executor — if the adapter ledger is empty for the
    executor bucket (can happen when the shared proxy adapter's log
    path discovery fails, e.g. an out-of-band adapter started from a
    different checkout without persisting log_path in its registry
    entry AND the pid already exited so ``/proc`` recovery is gone),
    derive executor tokens from ``message.usage`` inside the agent
    transcript via ``compute_executor_token_usage``. This covers
    openclaw/openclaw_edict but not nanobot; nanobot without adapter
    coverage legitimately has no source, in which case the payload
    marks ``available=False`` so the WebUI shows ``n/a``.

    Supervisor / user_simulator totals are adapter-only — Codex
    transcripts live in separate workspaces and aren't merged into
    the attempt tree, so there's nothing to fall back to. If the
    adapter ledger misses them, they just stay empty.
    """
    ledger_path = out_dir / "usage_ledger.jsonl"
    by_category: dict[str, dict[str, int]] = {}
    by_turn_executor: dict[int, dict[str, int]] = {}
    calls: list[dict[str, Any]] = []

    def _bucket(cat: str) -> dict[str, int]:
        return by_category.setdefault(
            cat,
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0,
                "call_count": 0,
            },
        )

    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            category = str(entry.get("category") or "").strip() or "unknown"
            bucket = _bucket(category)
            bucket["prompt_tokens"] += int(entry.get("prompt_tokens") or 0)
            bucket["completion_tokens"] += int(entry.get("completion_tokens") or 0)
            bucket["total_tokens"] += int(entry.get("total_tokens") or 0)
            bucket["call_count"] += 1
            calls.append(entry)
            if category == "executor":
                try:
                    turn_key = int(entry.get("turn"))
                except (TypeError, ValueError):
                    turn_key = 0
                turn_bucket = by_turn_executor.setdefault(
                    turn_key,
                    {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "call_count": 0},
                )
                turn_bucket["prompt_tokens"] += int(entry.get("prompt_tokens") or 0)
                turn_bucket["completion_tokens"] += int(entry.get("completion_tokens") or 0)
                turn_bucket["total_tokens"] += int(entry.get("total_tokens") or 0)
                turn_bucket["call_count"] += 1

    # Fallback for executor only: derive from transcript if adapter
    # ledger has nothing. Keep the bucket marked with its source so we
    # can audit later which path produced the numbers.
    executor_source = "proxy_adapter_log"
    if "executor" not in by_category or by_category["executor"]["call_count"] == 0:
        fallback = compute_executor_token_usage(out_dir, task)
        if fallback.get("available"):
            exec_fallback = dict(((fallback.get("summary") or {}).get("executor") or {}))
            if exec_fallback.get("call_count"):
                _bucket("executor").update(
                    {
                        "prompt_tokens": int(exec_fallback.get("prompt_tokens") or 0),
                        "completion_tokens": int(exec_fallback.get("completion_tokens") or 0),
                        "total_tokens": int(exec_fallback.get("total_tokens") or 0),
                        "call_count": int(exec_fallback.get("call_count") or 0),
                        "estimated_cost": 0,
                    }
                )
                executor_source = "agent_transcript_fallback"

    executor_bucket = by_category.get("executor", {})
    supervisor_bucket = by_category.get("supervisor", {})
    user_simulator_bucket = by_category.get("user_simulator", {})
    available = bool(calls) or bool(executor_bucket.get("call_count"))

    reason = ""
    if not available:
        reason = (
            "nanobot-and-adapter-unavailable"
            if normalize_agent_sys(task.agent_sys) == "nanobot"
            else "no-usage-source"
        )

    return {
        "available": available,
        "reason": reason,
        "source": {
            "executor": executor_source,
            "supervisor": "proxy_adapter_log" if supervisor_bucket.get("call_count") else "unavailable",
            "user_simulator": "proxy_adapter_log" if user_simulator_bucket.get("call_count") else "unavailable",
        },
        "summary": {
            "executor": executor_bucket,
            "supervisor": supervisor_bucket,
            "user_simulator": user_simulator_bucket,
        },
        "executorByTurn": {str(k): v for k, v in by_turn_executor.items()},
        "calls": calls,
    }


def compute_executor_token_usage(out_dir: Path, task: TaskSpec) -> dict[str, Any]:
    """Walk executor transcripts and sum token usage per API response.

    The source of truth is the ``message.usage`` block each LLM
    response carries inside its session JSONL event — openclaw emits
    ``{input, output, cacheRead, cacheWrite, totalTokens}`` for every
    assistant message. Walking the per-attempt ``transcript.jsonl``
    covers every backend uniformly:

    - ``openclaw`` / ``nanobot``: single-agent transcript.
    - ``openclaw_edict``: the merged transcript produced by
      ``collect_edict_agent_session_artifacts`` already interleaves
      events from every sub-ministry AND from nested
      ``sessions_spawn`` subagents (since ``Fix 4`` in the edict
      post-mortem started walking all session files under each agent
      dir). So summing once here gives the true cumulative executor
      spend for the whole three-省/六部 chain.

    ``nanobot`` currently does NOT write ``message.usage`` back into
    its session JSONL; for that backend this function returns
    ``{available: False, reason:
    "agent-transcript-has-no-usage"}`` instead of silently reporting
    zero — the WebUI can then render "n/a" honestly rather than "0".

    The returned payload is designed to plug straight into
    ``webui.server.usage_payload`` (which looks for
    ``summary.executor``) without further transformation. Deliberately
    NOT included in ``_copy_visible_workspace_files``: the supervisor
    and user_simulator must never see these numbers or their judgment
    could drift on cost/efficiency signals that have nothing to do
    with the task itself.
    """
    transcript_path = out_dir / "transcript.jsonl"
    if not transcript_path.exists():
        return {
            "available": False,
            "reason": "transcript-not-collected",
            "source": "agent_transcript",
            "summary": {},
            "calls": [],
        }

    prompt_tokens = 0
    completion_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0
    total_tokens = 0
    call_count = 0
    calls: list[dict[str, Any]] = []

    # Walk the merged transcript in order, pulling any ``message.usage``
    # block. We're forgiving about key names (openclaw uses
    # ``input``/``output``, native OpenAI uses ``prompt_tokens``/
    # ``completion_tokens``) so a future backend change doesn't silently
    # zero out the numbers.
    def _extract(usage_obj: dict) -> dict[str, int]:
        pt = int(
            usage_obj.get("input")
            or usage_obj.get("prompt_tokens")
            or usage_obj.get("input_tokens")
            or usage_obj.get("inputTokens")
            or 0
        )
        ct = int(
            usage_obj.get("output")
            or usage_obj.get("completion_tokens")
            or usage_obj.get("output_tokens")
            or usage_obj.get("outputTokens")
            or 0
        )
        cr = int(usage_obj.get("cacheRead") or usage_obj.get("cache_read") or 0)
        cw = int(usage_obj.get("cacheWrite") or usage_obj.get("cache_write") or 0)
        tt = int(usage_obj.get("totalTokens") or usage_obj.get("total_tokens") or (pt + ct))
        return {"pt": pt, "ct": ct, "cr": cr, "cw": cw, "tt": tt}

    with transcript_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = event.get("message") if isinstance(event, dict) else None
            if not isinstance(message, dict):
                continue
            usage_obj = message.get("usage")
            if not isinstance(usage_obj, dict):
                continue
            parts = _extract(usage_obj)
            prompt_tokens += parts["pt"]
            completion_tokens += parts["ct"]
            cache_read_tokens += parts["cr"]
            cache_write_tokens += parts["cw"]
            total_tokens += parts["tt"]
            call_count += 1
            calls.append(
                {
                    "agentId": event.get("agentId") or "",
                    "timestamp": event.get("timestamp") or "",
                    "prompt_tokens": parts["pt"],
                    "completion_tokens": parts["ct"],
                    "cache_read_tokens": parts["cr"],
                    "cache_write_tokens": parts["cw"],
                    "total_tokens": parts["tt"],
                }
            )

    if call_count == 0:
        agent_sys = normalize_agent_sys(task.agent_sys)
        reason = (
            "nanobot-transcript-has-no-usage"
            if agent_sys == "nanobot"
            else "agent-transcript-has-no-usage"
        )
        return {
            "available": False,
            "reason": reason,
            "source": "agent_transcript",
            "summary": {},
            "calls": [],
        }

    # Optional per-agent breakdown — only meaningful for edict where the
    # merged transcript carries ``agentId`` annotations. For single-agent
    # backends every call has ``agentId == ""`` so we skip the breakdown.
    per_agent: dict[str, dict[str, int]] = {}
    for entry in calls:
        agent_id = str(entry.get("agentId") or "").strip()
        if not agent_id:
            continue
        bucket = per_agent.setdefault(
            agent_id,
            {"prompt_tokens": 0, "completion_tokens": 0, "cache_read_tokens": 0, "total_tokens": 0, "call_count": 0},
        )
        bucket["prompt_tokens"] += entry["prompt_tokens"]
        bucket["completion_tokens"] += entry["completion_tokens"]
        bucket["cache_read_tokens"] += entry["cache_read_tokens"]
        bucket["total_tokens"] += entry["total_tokens"]
        bucket["call_count"] += 1

    executor_bucket = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "total_tokens": total_tokens,
        "call_count": call_count,
    }
    return {
        "available": True,
        "source": "agent_transcript",
        "summary": {"executor": executor_bucket},
        "perAgent": per_agent or None,
        "calls": calls,
    }
