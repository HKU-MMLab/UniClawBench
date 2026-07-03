#!/usr/bin/env python3
"""One-off migration: reset WATCHDOG-MISLABELED ``global_timeout`` cells to ``missing``.

Background (Round-20 status audit): ~60% of on-disk ``global_timeout`` attempts
were NOT executor timeouts.  They are the ``run_eval`` last-resort watchdog
(``os._exit(124)`` at ``max_total_seconds`` + 1800s) force-killing a WEDGED eval
process — a hung supervisor/grader codex call or a 429/timeout retry storm — and
``worker_runner`` then mapping ``rc==124`` -> ``global_timeout`` unconditionally.
Those attempts carry ``finalStatusReason == "run_eval-watchdog-rc124"`` in their
per-attempt ``summary.json`` and usually already produced a real answer in
``result/`` that was never scored.

``worker_runner`` is now fixed (rc==124 -> ``executor_incomplete``), and the
grader call is bounded (``CLAWBENCH_CODEX_TOTAL_BUDGET_SECONDS``) so future
wedges terminate cleanly as ``rate_limit`` instead of being killed by the
watchdog.  This script repairs the EXISTING mislabeled cells so the dispatcher
re-runs them: a cell whose rolled-up finalStatus is ``global_timeout`` AND whose
RESOLVED attempt is a ``run_eval-watchdog-rc124`` kill is reset to ``missing``.
Legitimate in-loop cumulative-budget ``global_timeout`` cells (resolved attempt
has NO watchdog reason, i.e. it wrote its own terminal summary with a score) are
LEFT UNTOUCHED.

Reset mechanics mirror ``reset_nonterminal_to_missing.py`` EXACTLY (so the next
``refresh_summary`` full refresh can't recompute the cell back):

  1. Rename each ``p<n>-...`` attempt dir -> ``_reset-<origname>`` (out of the
     ``startswith("p") and "-"`` glob so ``refresh_one_task`` sees zero attempts
     and leaves our ``missing`` summary alone). Artifacts are KEPT.
  2. Rewrite cell ``summary.json`` finalStatus -> ``missing`` (+ a reset marker),
     preserving every other field, so ``stats._read_status`` routes it to ``new``.

Cells claimed in ``runtime/inflight.jsonl`` are SKIPPED (a worker may still be
writing).  Dry-run by default; pass ``--apply`` to write.  Idempotent.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

WATCHDOG_REASON = "run_eval-watchdog-rc124"
RESET_MARKER = "reset-watchdog-mislabeled"


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


def _resolved_attempt_dir(cell: Path, summary: dict) -> Path | None:
    """Best-effort path to the RESOLVED attempt's dir under ``cell``."""
    attempts = summary.get("attempts") or []
    if not attempts:
        return None
    resolved_no = summary.get("resolvedAttempt")
    chosen = None
    if resolved_no is not None:
        for att in attempts:
            if att.get("attempt") == resolved_no:
                chosen = att
                break
    if chosen is None:
        # Fall back to the last attempt record (or any) when resolvedAttempt is
        # null/absent — we still verify its reason below before resetting.
        chosen = attempts[-1]
    out_dir = chosen.get("outDir") or ""
    base = out_dir.rstrip("/").rsplit("/", 1)[-1]
    cand = cell / base if base else None
    if cand and cand.is_dir():
        return cand
    return None


def _is_watchdog_mislabeled(cell: Path, summary: dict) -> bool:
    """A cell rolled up to global_timeout whose resolved attempt is a watchdog
    rc=124 kill (i.e. NOT a legit in-loop cumulative executor timeout)."""
    fs = (summary.get("finalStatus") or summary.get("final_status") or "").strip().lower()
    if fs != "global_timeout":
        return False
    adir = _resolved_attempt_dir(cell, summary)
    if adir is None:
        return False
    asp = adir / "summary.json"
    if not asp.is_file():
        return False
    try:
        ad = json.loads(asp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (ad.get("finalStatusReason") or "") == WATCHDOG_REASON


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--runtime-dir", required=True)
    ap.add_argument("--stamp", required=True, help="reset stamp, e.g. 2026-06-26 (env can't get the date)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    runs = Path(args.runs_root)
    runtime = Path(args.runtime_dir)
    inflight = _load_inflight(runtime)

    cells = sorted(runs.glob("*/*/*/*"))
    reset = 0
    archived = 0
    skipped_inflight = 0
    skipped_legit_global_timeout = 0
    examples: list = []

    for cell in cells:
        if not cell.is_dir():
            continue
        sp = cell / "summary.json"
        if not sp.is_file():
            continue
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        fs = (d.get("finalStatus") or d.get("final_status") or "").strip().lower()
        if fs != "global_timeout":
            continue
        if not _is_watchdog_mislabeled(cell, d):
            skipped_legit_global_timeout += 1
            continue
        rel = cell.relative_to(runs).parts
        key = (rel[0], rel[1], rel[2], rel[3]) if len(rel) == 4 else None
        if key in inflight:
            skipped_inflight += 1
            continue

        reset += 1
        p_dirs = [
            c for c in cell.iterdir()
            if c.is_dir() and c.name.startswith("p") and "-" in c.name
        ]
        if len(examples) < 8:
            examples.append((str(cell.relative_to(runs)), len(p_dirs)))

        if args.apply:
            for pd in p_dirs:
                target = pd.with_name("_reset-" + pd.name)
                if target.exists():
                    continue
                pd.rename(target)
                archived += 1
            d["finalStatus"] = "missing"
            d["finalStatusReason"] = f"{RESET_MARKER}-{args.stamp}"
            d["_resetFromStatus"] = "global_timeout"
            tmp = sp.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(sp)
        else:
            archived += len(p_dirs)

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] cells scanned={len(cells)}  inflight-claimed={len(inflight)}")
    print(f"  RESET (watchdog-mislabeled global_timeout -> missing): {reset}")
    print(f"  p*- dirs archived as _reset-: {archived}")
    print(f"  KEPT legit in-loop global_timeout (untouched): {skipped_legit_global_timeout}")
    print(f"  skipped inflight (worker still writing): {skipped_inflight}")
    for e in examples:
        print("   eg:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
