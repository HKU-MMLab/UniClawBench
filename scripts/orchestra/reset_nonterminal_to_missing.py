#!/usr/bin/env python3
"""Reset non-terminal cells to ``missing`` so the dispatcher re-runs them.

A cell is reset iff its rolled-up ``summary.json`` finalStatus is NOT terminal
(``pass`` / ``budget_exhausted`` / ``fail`` / ``global_timeout``).  Terminal
cells are NEVER touched.

Reset, per cell, is two steps that MUST go together:

  1. Rename each ``p<n>-<worker>-<hash>`` attempt dir -> ``_reset-<origname>``.
     ``refresh_summary.refresh_one_task`` rebuilds ``summary.json`` from the
     ``p*-`` siblings on every full refresh (``recompute_priorities(do_refresh=
     True)`` -> ``refresh_all_tasks``).  If we only rewrote finalStatus the next
     refresh would recompute the cell straight back to its old non-terminal
     status.  Renaming the dirs out of the ``startswith("p") and "-"`` glob
     makes ``refresh_one_task`` see zero attempts -> it returns None and leaves
     our ``missing`` summary alone.  The artifacts are KEPT (just renamed); the
     normal ``max_attempts_per_task`` prune (which globs *all* subdirs by mtime)
     still bounds them as fresh ``p*-`` attempts accrue.

  2. Rewrite ``summary.json`` finalStatus -> ``missing`` (+ a reset marker),
     preserving every other field, so ``stats._read_status`` routes the cell to
     the fresh ``new`` (missing) tier.

Cells currently claimed in ``runtime/inflight.jsonl`` are SKIPPED: a worker may
still be writing into their ``p*-`` dir and renaming it mid-write would break
the run.  Those finish on their own.

Dry-run by default; pass ``--apply`` to write.  Idempotent and re-runnable.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

TERMINAL = {"pass", "budget_exhausted", "fail", "global_timeout"}
RESET_MARKER = "reset-to-missing"


def _load_inflight(runtime_dir: Path) -> set[tuple[str, str, str, str]]:
    f = runtime_dir / "inflight.jsonl"
    claimed: set[tuple[str, str, str, str]] = set()
    if not f.is_file():
        return claimed
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = (d.get("backend"), d.get("model_dir"), d.get("suite"), d.get("task"))
        if None not in key:
            claimed.add(key)
    return claimed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--runtime-dir", required=True)
    ap.add_argument("--stamp", required=True, help="reset stamp, e.g. 2026-06-25 (env can't get the date)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    runs = Path(args.runs_root)
    runtime = Path(args.runtime_dir)
    inflight = _load_inflight(runtime)

    cells = sorted(runs.glob("*/*/*/*"))
    reset_by_status: Counter = Counter()
    archived = 0
    skipped_terminal = 0
    skipped_missing = 0
    skipped_inflight = 0
    no_summary = 0
    examples: list = []

    for cell in cells:
        if not cell.is_dir():
            continue
        sp = cell / "summary.json"
        if not sp.is_file():
            no_summary += 1
            continue
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        fs = (d.get("finalStatus") or d.get("final_status") or "").strip()
        if fs in TERMINAL:
            skipped_terminal += 1
            continue
        if fs == "missing":
            skipped_missing += 1
            continue
        # key = backend/model_dir/suite/task (cell path relative to runs)
        rel = cell.relative_to(runs).parts
        key = (rel[0], rel[1], rel[2], rel[3]) if len(rel) == 4 else None
        if key in inflight:
            skipped_inflight += 1
            continue

        reset_by_status[fs or "<empty>"] += 1
        p_dirs = [
            c for c in cell.iterdir()
            if c.is_dir() and c.name.startswith("p") and "-" in c.name
        ]
        if len(examples) < 6:
            examples.append((str(cell.relative_to(runs)), fs, len(p_dirs)))

        if args.apply:
            for pd in p_dirs:
                target = pd.with_name("_reset-" + pd.name)
                if target.exists():
                    continue
                pd.rename(target)
                archived += 1
            d["finalStatus"] = "missing"
            d["finalStatusReason"] = f"{RESET_MARKER}-{args.stamp}"
            d["_resetFromStatus"] = fs
            tmp = sp.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(sp)
        else:
            archived += len(p_dirs)

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] cells scanned={len(cells)}  inflight-claimed={len(inflight)}")
    print(f"  RESET (non-terminal -> missing): {sum(reset_by_status.values())}  by status={dict(reset_by_status)}")
    print(f"  p*- dirs archived as _reset-: {archived}")
    print(f"  KEPT terminal (untouched): {skipped_terminal}")
    print(f"  skipped already-missing: {skipped_missing}")
    print(f"  skipped inflight (worker still writing): {skipped_inflight}")
    print(f"  cells without summary (already missing): {no_summary}")
    for e in examples:
        print("   eg:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
