"""Compute per-task best-known status and bin tasks into priority buckets.

Pipeline:
  1. ``refresh_summary.refresh_all_tasks`` ensures every task dir has an
     up-to-date ``summary.json`` summarising all its ``p*-*`` attempts.
  2. We walk the canonical task list (from ``tasks/<suite>/task_*.yaml``)
     plus the backend × model_dir combinations declared in the orchestra
     config.  For each (backend, model_dir, suite, task) we read the local
     ``summary.json`` to derive the best-known ``finalStatus``.
  3. We drop anything currently in ``runtime/inflight.jsonl`` so locked
     tasks never re-enter a priority queue.
  4. Remaining incomplete tasks are bucketed against the priority list in
     order; the first matching bucket wins.

Output: ``runtime/priorities.jsonl`` — one JSON line per priority bucket:
``{"priority_id": "...", "label": "...", "tasks": [{...}, ...]}``
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import sys
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from . import config as cfg_mod
from . import refresh_summary
from lib.status import TERMINAL_RESULT_STATUSES, normalize_final_status  # noqa: E402

LOG = logging.getLogger("orchestra.stats")

# Statuses that mean "we have a real terminal result for this task" — these
# tasks are excluded from any priority bucket.  Round-6: source from
# lib.status (single source of truth) instead of a local copy.
TERMINAL_STATUSES = TERMINAL_RESULT_STATUSES

# Round-19: ``global_timeout`` stays a TERMINAL outcome everywhere it matters
# for accounting (stats counts, the TOTAL line, the webui results page, the
# reset tool) — it IS a real result. Operators may choose to re-dispatch it via
# an explicit low-priority tier with ``status_in: [global_timeout]``. Wildcard
# catch-all tiers must not pick it up accidentally; see the bucket matching
# guard below.
DISPATCH_INELIGIBLE_STATUSES = TERMINAL_RESULT_STATUSES - frozenset({"global_timeout"})


@dataclass(frozen=True)
class TaskKey:
    backend: str
    model_dir: str
    suite: str
    task: str

    def as_dict(self) -> dict:
        return {
            "backend": self.backend,
            "model_dir": self.model_dir,
            "suite": self.suite,
            "task": self.task,
        }


def _canonical_tasks(
    tasks_root: Path, suites: tuple[str, ...] = ()
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not tasks_root.is_dir():
        return out
    allow = set(suites)
    for suite_dir in tasks_root.iterdir():
        if not suite_dir.is_dir():
            continue
        if not suite_dir.name[:3].isdigit():
            continue  # only suite directories like 101_..., 102_...
        # Skip the 000_template / 001_smoketest scaffolding suites — they
        # ship example task definitions, not anything we want the
        # dispatcher to enqueue.
        if suite_dir.name.startswith(("000_", "001_")):
            continue
        # Optional allowlist from config ``suites:`` — empty means every
        # suite (minus the 000/001 scaffolding skipped above).
        if allow and suite_dir.name not in allow:
            continue
        out[suite_dir.name] = sorted(p.stem for p in suite_dir.glob("task_*.yaml"))
    return out


def _expected_combos(cfg: cfg_mod.OrchestraConfig) -> list[tuple[str, str]]:
    """Return every (backend, model_dir) pair we should be tracking.

    Two sources, unioned:

    1. The cartesian product of ``backend_in × model_in`` from every
       priority that pins both axes.  Lets the YAML declare "I expect
       these combos to exist" even if no run has produced data yet.
    2. Whatever (backend, model_dir) directories already exist under
       ``runs/``.  Catches data we already have but didn't bother
       enumerating in the YAML — common for fallback ``T_others``
       buckets that pin neither backend nor model.
    """
    combos: set[tuple[str, str]] = set()

    # Source 1: explicit priority pins
    for prio in cfg.priorities:
        if not prio.backend_in or not prio.model_in:
            continue
        for b in prio.backend_in:
            for m in prio.model_in:
                combos.add((b, m))

    # Source 2: anything currently on disk
    runs = cfg_mod.runs_root(cfg)
    if runs.is_dir():
        for backend_dir in runs.iterdir():
            if not backend_dir.is_dir():
                continue
            for model_dir in backend_dir.iterdir():
                if model_dir.is_dir():
                    combos.add((backend_dir.name, model_dir.name))

    return sorted(combos)


def _read_status(runs_root: Path, key: TaskKey) -> str:
    """Return the task's canonical finalStatus from its rolled-up summary.

    All return values are canonical ``FINAL_STATUS_ORDER`` members — the
    file-state sentinels (``no_summary``, ``broken_json``) and any
    legacy on-disk values (pre-Round-6 ``continue`` / ``stopped`` /
    ``FAIL_rc=N``) go through ``normalize_final_status`` so the
    priority-bucket config and the dashboards see the same vocabulary
    regardless of which generation wrote the summary.
    """
    sj = runs_root / key.backend / key.model_dir / key.suite / key.task / "summary.json"
    if not sj.exists():
        return normalize_final_status("no_summary")  # → "missing"
    try:
        d = json.loads(sj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return normalize_final_status("broken_json")  # → "missing"
    raw = d.get("finalStatus") or d.get("final_status") or "missing"
    return normalize_final_status(raw)


def _load_inflight(
    runtime_dir: Path,
    *,
    max_age_seconds: int | None = None,
) -> tuple[set[tuple[str, str, str, str]], set[tuple[str, str, str, str]]]:
    """Read inflight.jsonl into (survivors, expired) sets of task keys.

    Round 16 / P0-3: returns a tuple ``(survivors, expired)``.  Both are
    sets keyed on ``(backend, model_dir, suite, task)``.  ``expired``
    holds the keys this call dropped because their ``ts_start`` is older
    than ``now - max_age_seconds``.  Callers can use ``expired`` to keep
    the dispatcher's in-memory accounting (``DispatchState.inflight_by_task``,
    ``model_inflight``, ``worker.inflight``) in sync with the on-disk file.

    When ``max_age_seconds`` is set, expired rows are dropped from BOTH
    the returned ``survivors`` set AND the persisted file.  Rows without
    ``ts_start`` (legacy rows from a pre-Phase-3 dispatcher) are treated
    as "just started" — they keep their inflight slot until the next
    dispatcher invocation re-reserves them with a fresh ts_start.
    """
    f = runtime_dir / "inflight.jsonl"
    expired_keys: set[tuple[str, str, str, str]] = set()
    if not f.exists():
        return set(), expired_keys
    rows: list[dict] = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(d)

    survivors: list[dict] = []
    if max_age_seconds is not None and max_age_seconds > 0:
        cutoff = time.time() - max_age_seconds
        for d in rows:
            ts_start = d.get("ts_start")
            if isinstance(ts_start, (int, float)) and ts_start < cutoff:
                LOG.warning(
                    "inflight: expiring stale row %s/%s/%s/%s (ts_start=%s, age=%.0fs)",
                    d.get("backend"), d.get("model_dir"), d.get("suite"), d.get("task"),
                    ts_start, time.time() - ts_start,
                )
                key = (
                    d.get("backend"),
                    d.get("model_dir"),
                    d.get("suite"),
                    d.get("task"),
                )
                if None not in key:
                    expired_keys.add(key)  # type: ignore[arg-type]
                continue
            survivors.append(d)
        if expired_keys:
            # Rewrite the file atomically with only the survivors so the
            # dispatcher / stats / webui agree on which tasks are still
            # claimed.
            tmp = f.with_suffix(".jsonl.tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                for d in survivors:
                    fh.write(json.dumps(d) + "\n")
            tmp.replace(f)
    else:
        survivors = rows

    survivor_keys = {
        (d["backend"], d["model_dir"], d["suite"], d["task"])
        for d in survivors
        if "backend" in d and "model_dir" in d and "suite" in d and "task" in d
    }
    return survivor_keys, expired_keys


def _count_attempts_from_done_history(
    runtime_dir: Path,
) -> dict[tuple[str, str, str, str], int]:
    """Legacy (Round 12) lifetime-attempts counter — NO LONGER used by
    ``recompute_priorities`` after Round 16.

    Round 16 / P0-1: P200 routing is now session-only (driven by
    ``DispatchState.session_attempts``), so the dispatcher no longer
    reads this function or ``attempts_resets.jsonl`` to decide which
    tasks to suspend.  Dispatcher restart releases P200 automatically.

    Retained because ``release_p200.py`` still uses it to drain legacy
    ``attempts_resets.jsonl`` records (and to print the historical
    lifetime view in ``--list``) for runtimes that carry forward state
    from a pre-Round-16 dispatcher.  Once those runtimes are reset the
    function and its callers can be deleted.

    Reads ``runtime/done_history/done_*.jsonl`` + current
    ``runtime/done.jsonl``, subtracts ``runtime/attempts_resets.jsonl``
    decrements, and clamps the per-task count at zero.  O(N) over total
    DONE archive lines.
    """
    counts: dict[tuple[str, str, str, str], int] = {}
    archive_dir = runtime_dir / "done_history"
    files = []
    if archive_dir.is_dir():
        files.extend(sorted(archive_dir.glob("done_*.jsonl")))
    current = runtime_dir / "done.jsonl"
    if current.is_file():
        files.append(current)
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (
                d.get("backend"),
                d.get("model_dir"),
                d.get("suite"),
                d.get("task"),
            )
            if None in key:
                continue
            counts[key] = counts.get(key, 0) + 1

    # Apply operator resets (Round 12 release_p200.py).  Each reset
    # subtracts ``reset_count`` from the raw counter for one task.
    resets_path = runtime_dir / "attempts_resets.jsonl"
    if resets_path.is_file():
        try:
            text = resets_path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (
                d.get("backend"),
                d.get("model_dir"),
                d.get("suite"),
                d.get("task"),
            )
            if None in key:
                continue
            try:
                decrement = int(d.get("reset_count") or 0)
            except (TypeError, ValueError):
                continue
            if decrement <= 0:
                continue
            current_count = counts.get(key, 0)
            counts[key] = max(0, current_count - decrement)
    return counts


# Round 16 / P0-1: BOTH P100 and P200 are dispatcher-session-only.
#
# GLOBAL_MAX_ATTEMPTS (=3) — first session ceiling.  When
# ``DispatchState.session_attempts[key] >= 3`` the task is routed to the
# synthetic P100 graveyard, which dispatches only after every user
# bucket drains.
#
# SESSION_P200_THRESHOLD (=6) — second session ceiling.  When
# ``session_attempts[key] >= 6`` the task is routed to the synthetic
# P200 suspended bucket and the dispatcher refuses to dispatch it for
# the rest of this process's lifetime.
#
# Both thresholds reset on dispatcher restart (session_attempts is
# default_factory=dict on a fresh DispatchState).  The persistent
# done_history counter and ``release_p200.py`` are kept as legacy
# tooling for runtimes still carrying pre-Round-16 state.
#
# LIFETIME_MAX_ATTEMPTS (=10) is retained for back-compat with the
# legacy release_p200 CLI display only; ``recompute_priorities`` no
# longer reads it.
GLOBAL_MAX_ATTEMPTS = 3
SESSION_P200_THRESHOLD = GLOBAL_MAX_ATTEMPTS * 2  # = 6
LIFETIME_MAX_ATTEMPTS = 10  # legacy

# Synthetic bucket ids — NOT declared in config.  recompute_priorities
# appends them at the end of the bucket list in this order:
#   user buckets (P1..Pn) → P100 (in-process graveyard) → P200 (suspended)
# Dispatcher iterates buckets in order, so P200 is strictly lower
# priority than P100 which is strictly lower than user buckets.  The
# dispatcher refuses to pick from P200 entirely (it's a holding pen,
# not a slow lane).
P100_BUCKET_ID = "P100_session_exhausted"
P200_BUCKET_ID = "P200_suspended"


def recompute_priorities(
    cfg: cfg_mod.OrchestraConfig,
    *,
    tasks_root: Path,
    runs_root: Path | None = None,
    runtime_dir: Path | None = None,
    do_refresh: bool = True,
    session_attempts: dict[tuple[str, str, str, str], int] | None = None,
    expired_inflight_out: set[tuple[str, str, str, str]] | None = None,
) -> list[dict]:
    """Recompute incomplete tasks per priority bucket.

    Side effect: writes ``runtime/priorities.jsonl``.  Returns the list of
    bucket dicts (same content).

    Round 16 / P0-1 routing rules:
    - orphan ``running`` status (summary says ``running`` but task is NOT
      in ``inflight.jsonl``): treat as ``missing`` so P1/P3 reclaim it
      instead of leaving it as an unreachable zombie.
    - ``session_attempts[key] >= SESSION_P200_THRESHOLD`` (in-memory,
      default 6, resets on restart): route to the synthetic
      ``P200_suspended`` bucket.  P200 is NEVER dispatched within this
      dispatcher process.  Restart clears session_attempts → P200 tasks
      rejoin their normal buckets.
    - ``session_attempts[key] >= GLOBAL_MAX_ATTEMPTS`` (in-memory,
      default 3, resets on restart): route to the synthetic
      ``P100_session_exhausted`` bucket.  P100 dispatches only after
      every user bucket drains.
    - Within each bucket: sort by ``attempts`` ASC so fresh tasks
      (attempts=0) dispatch before retries (attempts=1+).
    """
    if runs_root is None:
        runs_root = cfg_mod.runs_root(cfg)
    if runtime_dir is None:
        runtime_dir = cfg_mod.runtime_dir()
    session_attempts = session_attempts or {}

    if do_refresh:
        refresh_summary.refresh_all_tasks(runs_root)

    canonical = _canonical_tasks(tasks_root, cfg.suites)
    combos = _expected_combos(cfg)
    inflight, expired = _load_inflight(
        runtime_dir,
        max_age_seconds=cfg.max_inflight_age_seconds,
    )
    if expired_inflight_out is not None:
        expired_inflight_out.update(expired)

    # Walk every canonical task and tag with its best status.
    incomplete: list[tuple[TaskKey, str]] = []
    for backend, model_dir in combos:
        for suite, tasks in canonical.items():
            for task_id in tasks:
                key = TaskKey(backend, model_dir, suite, task_id)
                status = _read_status(runs_root, key)
                # Round-19: global_timeout is excluded from INELIGIBLE so it can
                # re-dispatch via an explicit "timeout" tier.  It must not fall
                # through into wildcard catch-all priorities.
                if status in DISPATCH_INELIGIBLE_STATUSES:
                    continue
                if (backend, model_dir, suite, task_id) in inflight:
                    continue
                # Round 12 / E2: a summary stuck at ``running`` without a
                # corresponding inflight row is by definition stale — the
                # container died after writing the heartbeat but before
                # the final status update.  Demote to ``missing`` so P1
                # (status_in=[missing]) picks it back up.
                if status == "running":
                    status = "missing"
                incomplete.append((key, status))

    # Bucket against priorities in order.  First match wins.  Append the
    # synthetic P100 graveyard + P200 suspended buckets at the end so
    # P200 is strictly lowest, P100 is the catch-all retry pool, and
    # user buckets are above both.
    buckets: list[dict] = [
        {"priority_id": p.id, "label": p.label, "tasks": []} for p in cfg.priorities
    ]
    p100_bucket: dict = {
        "priority_id": P100_BUCKET_ID,
        "label": f"session attempts >= {GLOBAL_MAX_ATTEMPTS} — graveyard",
        "tasks": [],
    }
    p200_bucket: dict = {
        "priority_id": P200_BUCKET_ID,
        "label": (
            f"session attempts >= {SESSION_P200_THRESHOLD} — suspended "
            "(dispatcher-session only; restart to release)"
        ),
        "tasks": [],
    }

    for key, status in incomplete:
        key_tuple = (key.backend, key.model_dir, key.suite, key.task)
        session = session_attempts.get(key_tuple, 0)
        # P200 outranks P100 (and the user buckets) when both thresholds
        # are crossed — suspended tasks do not retry until restart.
        if session >= SESSION_P200_THRESHOLD:
            p200_bucket["tasks"].append({
                **key.as_dict(),
                "status": status,
                "attempts": session,
            })
            continue
        if session >= GLOBAL_MAX_ATTEMPTS:
            p100_bucket["tasks"].append({
                **key.as_dict(),
                "status": status,
                "attempts": session,
            })
            continue
        for prio, bucket in zip(cfg.priorities, buckets):
            if status in TERMINAL_STATUSES and not prio.status_in:
                # Allow only explicit terminal retry tiers such as
                # status_in=[global_timeout].  The appended "others" bucket and
                # any user catch-all priority are for non-terminal work.
                continue
            if not prio.matches(key.backend, key.model_dir, key.suite, status):
                continue
            bucket["tasks"].append({
                **key.as_dict(),
                "status": status,
                "attempts": session,
            })
            break

    buckets.append(p100_bucket)
    buckets.append(p200_bucket)

    # Round 12 / E1: within each bucket, ASC sort by attempts so
    # attempts=0 tasks dispatch before retries.  ``sort`` is stable so
    # the ``_spread_order`` round-robin in dispatch.py keeps its
    # model_dir interleave within each attempts tier.
    for b in buckets:
        b["tasks"].sort(key=lambda t: t.get("attempts", 0))

    runtime_dir.mkdir(parents=True, exist_ok=True)
    with (runtime_dir / "priorities.jsonl").open("w", encoding="utf-8") as fh:
        for b in buckets:
            fh.write(json.dumps(b) + "\n")
    return buckets


SESSION_ATTEMPTS_SNAPSHOT_FILENAME = "session_attempts.json"


def write_session_attempts_snapshot(
    runtime_dir: Path,
    session_attempts: Mapping[tuple[str, str, str, str], int],
) -> Path:
    """Persist the dispatcher's in-memory ``session_attempts`` to disk so
    monitoring tools that compute priorities outside the dispatcher
    process (``top.py --tasks-root``) can see the same P100/P200 routing
    the live dispatcher applies.

    Why: ``DispatchState.session_attempts`` lives only in the dispatcher
    process; ``stats.recompute_priorities`` defaults the parameter to
    ``{}`` when nothing is passed.  Without this snapshot, an external
    recompute would report P100/P200 as empty even when the dispatcher
    has already pushed several tasks past the session cap.

    Atomic via ``os.replace`` so a partial write is never observable.
    An empty ``session_attempts`` still writes a file (with empty
    ``entries``) so consumers can distinguish "dispatcher up, no
    attempts yet" from "no dispatcher running" (file missing).
    """
    runtime_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": time.time(),
        "entries": [
            {
                "backend": k[0],
                "model_dir": k[1],
                "suite": k[2],
                "task": k[3],
                "count": int(v),
            }
            for k, v in sorted(session_attempts.items())
        ],
    }
    target = runtime_dir / SESSION_ATTEMPTS_SNAPSHOT_FILENAME
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, target)
    return target


def read_session_attempts_snapshot(
    runtime_dir: Path,
) -> dict[tuple[str, str, str, str], int] | None:
    """Read the dispatcher's session_attempts snapshot, returning the
    in-memory shape ``recompute_priorities`` expects.

    Returns ``None`` when the file is missing or unparseable so callers
    can distinguish "no snapshot available" from "snapshot exists and
    is empty".  Callers that prefer best-effort behavior can coerce
    ``None`` to ``{}`` themselves.
    """
    path = runtime_dir / SESSION_ATTEMPTS_SNAPSHOT_FILENAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return None
    out: dict[tuple[str, str, str, str], int] = {}
    for row in entries:
        if not isinstance(row, dict):
            return None
        try:
            key = (
                str(row["backend"]),
                str(row["model_dir"]),
                str(row["suite"]),
                str(row["task"]),
            )
            out[key] = int(row["count"])
        except (KeyError, TypeError, ValueError):
            return None
    return out


def summarise_priorities(buckets: Iterable[dict]) -> str:
    lines = []
    total = 0
    for b in buckets:
        n = len(b["tasks"])
        total += n
        lines.append(f"  {b['priority_id']:<24} {n:>5}  {b['label']}")
    lines.append(f"  {'TOTAL':<24} {total:>5}")
    return "\n".join(lines)


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Recompute orchestra priority queues")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--tasks-root", required=True, type=Path)
    parser.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()

    cfg = cfg_mod.load(args.config)
    buckets = recompute_priorities(
        cfg,
        tasks_root=args.tasks_root,
        do_refresh=not args.no_refresh,
    )
    print(summarise_priorities(buckets))


if __name__ == "__main__":
    _cli()
