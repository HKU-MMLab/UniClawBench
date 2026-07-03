"""Legacy P200 release tool — kept for runtimes that still hold a
pre-Round-16 ``attempts_resets.jsonl`` ledger.

Round 16 / P0-1 changed P200 semantics: both P100 and P200 are now
session-only counters in ``DispatchState.session_attempts``, so the
standard release path is now simply **restart the dispatcher**.
``recompute_priorities`` no longer reads ``done_history`` or
``attempts_resets.jsonl`` when routing tasks to P100/P200.

This script is retained because operators may still have legacy
``attempts_resets.jsonl`` files that were written by older dispatcher
generations.  ``--list`` continues to print the P200 view from the most
recent ``priorities.jsonl`` snapshot, and ``--execute`` continues to
append reset records (so ``_count_attempts_from_done_history`` returns
zero for the affected tasks) — useful when archiving a runtime or
sanity-checking the legacy lifetime view.  Neither operation affects
live P200 routing under the Round 16+ dispatcher.

Round 12 historical context (kept for traceability):

  * ``GLOBAL_MAX_ATTEMPTS`` (=3) — session-scoped, in-memory.  Tasks at
    this cap drop to the P100 graveyard.  Dispatcher restart clears
    ``session_attempts`` so P100 releases automatically.

  * ``LIFETIME_MAX_ATTEMPTS`` (=10) — persistent, counted from
    ``runtime/done_history/done_*.jsonl`` files.  Tasks at this cap
    used to drop to the P200 suspended bucket; Round 16 removed this
    behavior so P200 no longer depends on disk state.

This script writes a "reset" record to
``runtime/attempts_resets.jsonl`` that ``_count_attempts_from_done_history``
subtracts from the on-disk count.  The original ``done_*.jsonl`` files
are never modified — the audit trail stays intact.

Usage
-----

List current P200 contents (from the last ``priorities.jsonl``)::

    python3 -m scripts.orchestra.release_p200 \\
        --runtime-dir <data_root>/Clawbench/scripts/orchestra/runtime \\
        --list

Release every task currently in P200 (after a dry-run preview)::

    python3 -m scripts.orchestra.release_p200 \\
        --runtime-dir <data_root>/Clawbench/scripts/orchestra/runtime \\
        --all --execute

Release one specific task (always dry-run by default; use --execute)::

    python3 -m scripts.orchestra.release_p200 \\
        --runtime-dir <data_root>/Clawbench/scripts/orchestra/runtime \\
        --task openclaw/proxy-example-gpt-5-4/103_long_context/task_103_08_hk_jpop_calendar_ticketing \\
        --execute

``--list`` prints the live P200 view from the most recent
``priorities.jsonl`` snapshot; ``--execute`` only updates the legacy
lifetime view used by old reporting tools.  To release a task from
the **live** Round 16+ P200 bucket, restart the dispatcher process —
``DispatchState.session_attempts`` lives only in memory and clears on
a fresh state.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import stats as stats_mod


def _list_p200_tasks(runtime_dir: Path) -> list[dict]:
    """Read the last bucket snapshot from priorities.jsonl and return
    the P200 entries.  Returns [] if priorities.jsonl is missing or
    P200 is empty.

    priorities.jsonl is rewritten on every recompute (~every 5s while
    the dispatcher runs).  Reading the last N lines is sufficient to
    get the current bucket layout — earlier lines are older snapshots.
    """
    pjsonl = runtime_dir / "priorities.jsonl"
    if not pjsonl.is_file():
        return []
    lines = pjsonl.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    # Each "snapshot" is one line per bucket; the last snapshot ends
    # at EOF.  Walk backward to find the P200 entry for the last
    # snapshot.
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("priority_id") == stats_mod.P200_BUCKET_ID:
            return list(d.get("tasks") or [])
    return []


def _resolve_releases(
    runtime_dir: Path,
    task_keys: list[tuple[str, str, str, str]] | None,
    release_all: bool,
) -> list[dict]:
    """Cross-reference the requested task keys against the current
    P200 contents.  Returns the subset of P200 tasks the user asked
    to release (or all of them if ``--all``).
    """
    p200_tasks = _list_p200_tasks(runtime_dir)
    if release_all:
        return p200_tasks
    if not task_keys:
        return []
    wanted = set(task_keys)
    return [
        t for t in p200_tasks
        if (t["backend"], t["model_dir"], t["suite"], t["task"]) in wanted
    ]


def _record_resets(runtime_dir: Path, tasks: list[dict]) -> Path:
    """Append one reset record per task to ``attempts_resets.jsonl``.

    For each task, ``reset_count`` is the **current** legacy lifetime
    count computed from ``runtime/done_history`` minus prior resets
    (via ``stats._count_attempts_from_done_history``).  Subtracting that
    value zeroes out the legacy lifetime counter for the task, leaving
    ``done_history`` itself untouched so the audit trail stays intact.

    Round 16+: this only updates the legacy lifetime view used by
    pre-Round-16 tooling and ``--list``.  Live P200 routing is
    session-only (``DispatchState.session_attempts``) and is unaffected
    by this file — restart the dispatcher to release a live P200 task.

    Earlier revisions read ``lifetime_attempts`` off each task entry,
    but Round 16's ``recompute_priorities`` no longer populates that
    field on P200 task rows, so the value was always ``None`` and the
    resulting ``reset_count`` was 0 (a no-op).
    """
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lifetime_counts = stats_mod._count_attempts_from_done_history(runtime_dir)
    resets_path = runtime_dir / "attempts_resets.jsonl"
    now = time.time()
    with resets_path.open("a", encoding="utf-8") as fh:
        for t in tasks:
            key = (t["backend"], t["model_dir"], t["suite"], t["task"])
            record = {
                "backend": t["backend"],
                "model_dir": t["model_dir"],
                "suite": t["suite"],
                "task": t["task"],
                "reset_count": int(lifetime_counts.get(key, 0)),
                "reset_at": now,
            }
            fh.write(json.dumps(record) + "\n")
    return resets_path


def _format_task(t: dict) -> str:
    return (
        f"{t['backend']}/{t['model_dir']}/{t['suite']}/{t['task']}"
        f"  attempts={t.get('attempts', '?')}"
        f"  lifetime={t.get('lifetime_attempts', '?')}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Release tasks from the P200 suspended bucket "
                    "(Round 12 / E1 lifetime-attempts cap)",
    )
    parser.add_argument(
        "--runtime-dir",
        required=True,
        type=Path,
        help="Path to runtime/ directory (contains priorities.jsonl + "
             "done_history/ + attempts_resets.jsonl).",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--list",
        action="store_true",
        help="Print P200 contents and exit (no changes).",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="Release every task currently in P200.",
    )
    mode.add_argument(
        "--task",
        action="append",
        default=[],
        help="Release a specific task (backend/model_dir/suite/task). "
             "May be repeated to release multiple tasks.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Without this flag, --all and --task only show what WOULD "
             "be released (dry-run).  Pass --execute to actually write "
             "the reset records.",
    )
    args = parser.parse_args(argv)

    if args.list:
        tasks = _list_p200_tasks(args.runtime_dir)
        if not tasks:
            print(f"P200 is empty (or {args.runtime_dir}/priorities.jsonl missing).")
            return 0
        print(f"P200 contents ({len(tasks)} task(s)):")
        for t in tasks:
            print("  " + _format_task(t))
        return 0

    requested_keys: list[tuple[str, str, str, str]] = []
    for raw in args.task:
        parts = raw.strip("/").split("/")
        if len(parts) != 4:
            print(f"error: --task must be backend/model_dir/suite/task, got {raw!r}", file=sys.stderr)
            return 2
        requested_keys.append((parts[0], parts[1], parts[2], parts[3]))

    to_release = _resolve_releases(args.runtime_dir, requested_keys, args.all)
    if not to_release:
        if args.all:
            print("P200 is empty — nothing to release.")
        else:
            print("None of the requested tasks are in P200.")
        return 0

    print(f"Would release {len(to_release)} task(s) from P200:")
    for t in to_release:
        print("  " + _format_task(t))

    if not args.execute:
        print()
        print("Dry-run only.  Re-run with --execute to write resets to attempts_resets.jsonl.")
        return 0

    resets_path = _record_resets(args.runtime_dir, to_release)
    print()
    print(f"Wrote {len(to_release)} reset record(s) to {resets_path}.")
    print("NOTE (Round 16+): live P200 routing is session-only, so this")
    print("reset only affects the legacy lifetime view used by _list/--list")
    print("and any pre-Round-16 tooling.  To actually release P200 under the")
    print("current dispatcher, restart the dispatcher process — session_attempts")
    print("is in-memory and clears automatically on a fresh DispatchState.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
