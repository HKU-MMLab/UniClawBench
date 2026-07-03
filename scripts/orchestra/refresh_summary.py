"""Rebuild task-level ``summary.json`` from individual ``p*-*`` attempt subdirs,
plus a flat ``.runs_index.json`` cache the webui consumes.

The orchestra preserves every historical attempt as its own ``p1-<host>-<id>``
subdirectory under the task directory.  The webui (and ``stats``) want a
single task-level ``summary.json`` summarising all attempts.  This module
walks the per-attempt summaries, picks the best by status priority (passing
runs win over budget-exhausted, etc.), and atomically writes the rolled-up
summary.

It also maintains a single ``<runs_root>/.runs_index.json`` so the webui's
``/api/runs`` endpoint can answer in O(1 file read) instead of walking all
3 000 task trees on every page load.  See ``write_runs_index`` for the on-
disk shape; ``webui/server.py`` reads it when present and falls back to the
slow path when the index is missing or stale.

It is invoked by ``dispatch`` at three points:
  - on startup (full scan)
  - after each worker reports done (incremental, single task)
  - after each priority bucket drains (full scan, belt-and-braces)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

LOG = logging.getLogger(__name__)

# Pull the lib.status single source of truth.  refresh_summary.py is
# invoked as a module (python -m scripts.orchestra.refresh_summary) where
# the repo root is already on sys.path, but also imported by stats.py
# where we need the absolute import to work.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.status import (  # noqa: E402
    SUMMARY_SCHEMA_VERSION,
    apply_score_based_promotion,
    classify_attempt_outcome,
    normalize_final_status,
    status_rank,
)
from lib.runtime_metrics import attempt_runtime_ms  # noqa: E402

# Status priority ordering: see ``lib/status.py:FINAL_STATUS_ORDER`` and
# ``status_rank``.  Round-6 Phase 2: this module no longer maintains a
# local copy; ``status_rank(s)`` is used directly below.


def _safe_load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _first_not_none(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _derive_status_from_artifacts(p_dir: Path) -> dict | None:
    """Synthesise an attempt summary when per-attempt ``summary.json`` is absent.

    A run_eval invocation only writes ``summary.json`` (at the task level)
    if it makes it through to ``write_task_run_state``.  Attempts that get
    killed mid-flight by a global timeout, a SIGKILL, or an OOM never get
    that far — yet they still leave ``score.json``, ``meta.json``, and
    ``supervision.log`` behind.  Reconstruct a minimal record from those
    so the attempt is visible in the rolled-up summary instead of being
    silently dropped.
    """
    score = _safe_load_json(p_dir / "score.json")
    meta = _safe_load_json(p_dir / "meta.json")
    if not score and not meta:
        return None

    # Round-6 Phase 2: delegate to lib.status.classify_attempt_outcome so
    # Path B (synth) and Path A (runtime: resolve_attempt_outcome) classify
    # the same underlying state identically.  All field mapping happens
    # here at the boundary; the classifier itself is field-name agnostic.
    #
    # Round 9 / A6: extend pre_exec_failed detection beyond meta's
    # ``preExecFailed`` flag.  Also read:
    #   - ``score.infra_error_type == 'pre_exec_failed'`` (set by
    #     structured_runtime_error_score on bootstrap fail)
    #   - ``meta.bootstrapError.type == 'pre_exec_failed'`` (set by
    #     build_bootstrap_infra_summary for the host-side pre_exec
    #     script crashing).
    # Pre-fix, if the score had ``verdict=infra_error`` but the meta
    # didn't have the legacy ``preExecFailed=True`` field, Path B
    # collapsed to ``infra_error`` and lost the pre_exec_failed
    # distinction — which the dispatcher uses to route into a
    # separate priority bucket.  Path A wrote the right type but
    # Path B's synth roll-up flattened it.
    infra_error = meta.get("infraError")
    rate_limit = meta.get("rateLimit")
    bootstrap_error = meta.get("bootstrapError") if isinstance(meta.get("bootstrapError"), dict) else {}
    pre_exec_failed_flag = bool(
        meta.get("preExecFailed")
        or meta.get("pre_exec_failed")
        or (bootstrap_error.get("type") == "pre_exec_failed")
        or (score.get("infra_error_type") == "pre_exec_failed")
    )
    final_status = classify_attempt_outcome(
        verdict=score.get("verdict") or "",
        attempt_state=score.get("attempt_state") or "",
        rate_limit=bool(rate_limit),
        infra_error=bool(infra_error) or pre_exec_failed_flag,
        infra_error_type="pre_exec_failed" if pre_exec_failed_flag else "",
        completion_gate_failed=bool(score.get("completion_gate_failed")),
        executor_completed_ever=bool(meta.get("everExecutorCompleted")),
        agent_exit_code=meta.get("agentExitCode"),
        completion_reason=meta.get("executorCompletionReason") or "",
        followup_budget_exhausted=bool(score.get("followup_budget_exhausted")),
        passed_flag=bool(score.get("passed")),
    )

    # Phase 2: score-based pass promotion now also runs on Path B, gated on
    # ``success_threshold`` having been persisted into ``score.json``. Older
    # artifacts predate this field and skip promotion (legacy attempts keep
    # their classifier-only status).
    score_promotion_skipped = ""
    if "success_threshold" in score:
        try:
            threshold_val = float(score["success_threshold"])
        except (TypeError, ValueError):
            threshold_val = None
        if threshold_val is not None:
            best = score.get("best_supervisor_score")
            raw_score = (
                best
                if best is not None
                else score.get("overall_score", 0.0) or 0.0
            )
            try:
                raw_score_val = float(raw_score)
            except (TypeError, ValueError):
                raw_score_val = 0.0
            final_status, _promoted = apply_score_based_promotion(
                final_status, raw_score_val, threshold_val
            )
        else:
            score_promotion_skipped = "invalid_success_threshold"
    else:
        score_promotion_skipped = "missing_success_threshold"

    record: dict = {
        "outDir": str(p_dir),
        # Round 8 / A5: ``runtimeMs`` is the EXECUTOR-only elapsed time
        # (sum of executor turns + retries).  Pre-fix we fell back to
        # ``wallClockMs`` when meta lacked runtimeMs, but wallClockMs
        # is total wall-clock (executor + supervisor + user_simulator
        # + sync overhead).  Using it as a runtime proxy silently
        # polluted Results-page avg-runtime with grader / simulator
        # time.  Drop the fallback: if executor runtime is missing,
        # leave runtimeMs absent so the aggregator skips this row's
        # runtime contribution rather than averaging in a wall-clock
        # imposter.  The ``wallClockMs`` field is still surfaced
        # separately for diagnostic / debug profiles.
        "runtimeMs": meta.get("runtimeMs"),
        "wallClockMs": meta.get("wallClockMs"),
        "score": _first_not_none(score.get("overall_score"), score.get("capped_score")),
        "rawFinalScore": score.get("overall_score"),
        "finalScore": score.get("capped_score"),
        "passed": final_status == "pass",
        "finalStatus": final_status,
        "infraError": infra_error,
        "rateLimit": rate_limit,
        # Identifiers only the synthesised path knows where to find — used
        # by ``refresh_one_task`` to fill in the rolled-up summary when the
        # chosen attempt has no per-attempt summary.json.
        "_synthetic": True,
        "_meta": meta,
    }
    if score_promotion_skipped:
        record["_scorePromotionSkipped"] = score_promotion_skipped
    return record


def _read_attempt_summary(p_dir: Path) -> dict | None:
    sj = p_dir / "summary.json"
    if not sj.exists():
        return None
    try:
        return json.loads(sj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".summary.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


# ---------------------------------------------------------------------------
# runs index — flat cache the webui consumes instead of walking the tree
# ---------------------------------------------------------------------------

#: Filename of the cache, written into ``<runs_root>/``.  The leading dot
#: keeps it out of normal listings and out of any ``runs_root.glob("*")``
#: pattern that would mistake it for a backend directory.
INDEX_FILENAME = ".runs_index.json"

#: Bump when the index schema changes incompatibly.  Readers compare
#: ``payload["version"]`` and fall back to a full scan on mismatch.
INDEX_SCHEMA_VERSION = 3


def index_path(runs_root: Path) -> Path:
    return Path(runs_root) / INDEX_FILENAME


def _count_continuations(task_dir: Path) -> int:
    """Sum ``len(meta.continuations)`` across all ``p*-*`` attempts.

    Reading per-attempt meta.json is what made the original ``/api/runs``
    so expensive; doing it once at refresh time and caching the total in
    the index trades ~5 reads-per-task at refresh time for **zero** reads-
    per-task at request time.
    """
    total = 0
    try:
        children = list(task_dir.iterdir())
    except OSError:
        return 0
    for pd in children:
        if not pd.is_dir() or not pd.name.startswith("p") or "-" not in pd.name:
            continue
        meta = _safe_load_json(pd / "meta.json")
        cont = meta.get("continuations") if isinstance(meta, dict) else None
        if isinstance(cont, list):
            total += len(cont)
    return total


def _build_index_row(task_dir: Path, summary: dict, *, runs_root: Path) -> dict:
    """Reduce a per-task summary to the flat shape ``/api/runs`` returns.

    Only the 9 fields the webui actually consumes; the rest of ``summary``
    is left on disk for ``/api/attempt`` to read on demand.
    """
    attempts = summary.get("attempts") or []
    # Sum runtime across attempts — that's the metric the trace UI averages.
    # Keep this in sync with webui.server and webui.aggregate via the shared
    # runtime helper so the index fast path cannot bypass runtime fallbacks.
    total_runtime = 0
    for a in attempts:
        attempt_dir = task_dir / Path(a.get("outDir") or "").name
        total_runtime += attempt_runtime_ms(a, attempt_dir, default=0) or 0
    final_status = summary.get("finalStatus")
    if not final_status:
        final_status = "pass" if summary.get("passed") else "fail"
    final_status = normalize_final_status(final_status)
    passed = summary.get("passed")
    if not isinstance(passed, bool):
        passed = final_status == "pass"
    return {
        "taskId": summary.get("taskId") or task_dir.name,
        "category": task_dir.parent.name,
        "backend": summary.get("backend") or task_dir.parents[2].name,
        "model": summary.get("model"),
        "summaryPath": str(task_dir.relative_to(runs_root)),
        "finalStatus": final_status,
        "passed": passed,
        "finalScore": summary.get("finalScore"),
        "runtimeMs": total_runtime,
        "continuationCount": _count_continuations(task_dir),
    }


def _read_index(runs_root: Path) -> dict | None:
    """Load the cached index payload; return ``None`` if absent/unreadable."""
    p = index_path(runs_root)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("version") != INDEX_SCHEMA_VERSION:
        return None
    return data


def write_runs_index(runs_root: Path, rows: list[dict]) -> Path:
    """Persist the full index atomically.  Returns the written path."""
    runs_root = Path(runs_root)
    payload = {
        "version": INDEX_SCHEMA_VERSION,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rowCount": len(rows),
        "rows": rows,
    }
    target = index_path(runs_root)
    _atomic_write_json(target, payload)
    return target


def upsert_index_row(runs_root: Path, task_dir: Path, summary: dict | None) -> bool:
    """Update or insert a single row in the index in place.

    Used by ``refresh_one_task`` so that per-task callbacks (one per worker
    completion) keep the index current without re-walking every task.  If
    the index doesn't exist yet, this is a no-op — ``refresh_all_tasks``
    will materialise it on the next full pass.

    Returns ``True`` if the index was modified.
    """
    runs_root = Path(runs_root)
    cached = _read_index(runs_root)
    if cached is None:
        return False
    rows = list(cached.get("rows") or [])
    rel = str(Path(task_dir).resolve().relative_to(Path(runs_root).resolve()))
    if summary is None:
        # Task was deleted / has no attempts → drop any stale row.
        new_rows = [r for r in rows if r.get("summaryPath") != rel]
        if len(new_rows) == len(rows):
            return False
        cached["rows"] = new_rows
        cached["rowCount"] = len(new_rows)
        cached["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _atomic_write_json(index_path(runs_root), cached)
        return True
    new_row = _build_index_row(task_dir, summary, runs_root=runs_root)
    replaced = False
    for i, r in enumerate(rows):
        if r.get("summaryPath") == rel:
            rows[i] = new_row
            replaced = True
            break
    if not replaced:
        rows.append(new_row)
    cached["rows"] = rows
    cached["rowCount"] = len(rows)
    cached["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _atomic_write_json(index_path(runs_root), cached)
    return True


def refresh_one_task(task_dir: Path) -> dict | None:
    """Recompute ``task_dir/summary.json`` from its ``p*-*`` siblings.

    Returns the new summary dict if anything was written, else ``None``.
    """
    if not task_dir.is_dir():
        return None

    p_dirs = sorted(
        d
        for d in task_dir.iterdir()
        if d.is_dir() and d.name.startswith("p") and "-" in d.name
    )
    attempts: list[dict] = []
    for idx, pd in enumerate(p_dirs, start=1):
        sub = _read_attempt_summary(pd)
        if sub:
            # Carry forward whatever the per-attempt summary already contains,
            # normalising the fields the webui depends on.  The
            # ``normalize_final_status`` call is the boundary translation:
            # legacy values (``continue`` / ``stopped`` / ``FAIL_rc=N`` /
            # ``no_summary`` / ``broken_json`` from pre-Round-6 attempts on
            # disk) become canonical FINAL_STATUS_ORDER members before
            # being passed to ``status_rank`` — without this, an unknown
            # value collapses to rank 0 and a stale ``continue`` attempt
            # gets buried behind a fresh ``missing`` one.
            raw_status = (sub.get("finalStatus") or sub.get("final_status") or "missing")
            status = normalize_final_status(raw_status)
            attempts.append(
                {
                    "attempt": idx,
                    "outDir": str(pd),
                    "runtimeMs": _first_not_none(sub.get("runtimeMs"), sub.get("runtime_ms")),
                    "score": _first_not_none(sub.get("score"), sub.get("rawFinalScore"), sub.get("finalScore")),
                    "rawFinalScore": sub.get("rawFinalScore"),
                    "finalScore": sub.get("finalScore"),
                    "passed": bool(sub.get("passed", False)),
                    "finalStatus": status,
                    "infraError": sub.get("infraError"),
                    "rateLimit": sub.get("rateLimit"),
                }
            )
            continue
        # Fallback: per-attempt summary.json is missing (run_eval was killed
        # before write_task_run_state).  Derive a minimal record from the
        # artefacts that are still on disk.
        synth = _derive_status_from_artifacts(pd)
        if synth is None:
            continue
        synth_attempt = {"attempt": idx, **synth}
        attempts.append(synth_attempt)

    if not attempts:
        return None

    def _attempt_mtime(attempt: dict) -> float:
        """File-system mtime of the attempt directory, 0 on error.

        Used as the "newer wins" tie-breaker once the higher-priority
        keys (status rank, finalScore, non-synthetic) have all tied.
        """
        out = attempt.get("outDir")
        if not out:
            return 0.0
        try:
            return Path(out).stat().st_mtime
        except OSError:
            return 0.0

    def _attempt_sort_key(i: int) -> tuple:
        """Round 8 / A6: tie-breaker priority (higher wins for each
        component, lexicographic across the tuple):

          1. ``status_rank`` — the canonical status ordering from
             ``lib.status.FINAL_STATUS_ORDER`` (pass > budget_exhausted
             > fail > global_timeout > executor_incomplete > …).
          2. ``finalScore`` — within the same status, higher score is
             obviously a better representative.  ``None`` / missing
             coerces to 0.0.
          3. **non-synthetic preferred** — a real ``summary.json`` is
             stronger evidence than a synth fallback record built from
             score.json + meta.json.  Encoded as ``0/1`` where 1 means
             non-synthetic so the max picks it.
          4. ``mtime`` — newer attempt wins (operator re-runs typically
             carry the more recent schema, fixed bugs, fresher
             artefacts).
          5. ``i`` — final stable order for full determinism.

        Pre-fix this was ``(status_rank, -i)``, which buried newer
        attempts behind older ones at the same status, and ignored
        score / synthetic / mtime entirely.
        """
        a = attempts[i]
        score = a.get("finalScore")
        try:
            score_val = float(score) if score is not None else 0.0
        except (TypeError, ValueError):
            score_val = 0.0
        non_synthetic = 0 if a.get("_synthetic") else 1
        return (
            status_rank(a["finalStatus"]),
            score_val,
            non_synthetic,
            _attempt_mtime(a),
            i,
        )

    best_idx = max(range(len(attempts)), key=_attempt_sort_key)
    best = attempts[best_idx]

    # Inherit identifiers from the chosen attempt: prefer its per-attempt
    # summary.json, fall back to its meta.json (synthesised path).
    chosen_pd = Path(best["outDir"])
    chosen_sub = _read_attempt_summary(chosen_pd) or {}
    chosen_meta = best.get("_meta") if best.get("_synthetic") else _safe_load_json(chosen_pd / "meta.json")
    chosen_meta = chosen_meta if isinstance(chosen_meta, dict) else {}

    def _ident(*keys):
        for src in (chosen_sub, chosen_meta):
            for k in keys:
                v = src.get(k) if isinstance(src, dict) else None
                if v:
                    return v
        return None

    # Strip private fields (_synthetic, _meta) before persisting.
    public_attempts = [{k: v for k, v in a.items() if not k.startswith("_")} for a in attempts]
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "taskId": _ident("taskId") or task_dir.name,
        "taskFile": _ident("taskFile"),
        "backend": _ident("backend"),
        "model": _ident("model"),
        "imageModel": _ident("imageModel"),
        "evaluationMode": _ident("evaluationMode") or "codex_supervised",
        "modelSlug": _ident("modelSlug"),
        "settingRoot": _ident("settingRoot"),
        "attempts": public_attempts,
        "resolvedAttempt": best["attempt"],
        "rawFinalScore": _first_not_none(best.get("rawFinalScore"), best.get("score")),
        "finalScore": _first_not_none(best.get("finalScore"), best.get("score")),
        "passed": best.get("passed", False),
        "finalStatus": best["finalStatus"],
        "infraError": best.get("infraError"),
        "rateLimit": best.get("rateLimit"),
        "stopReason": chosen_sub.get("stopReason") or "",
    }

    _atomic_write_json(task_dir / "summary.json", summary)
    return summary


def refresh_one_task_with_index(task_dir: Path, runs_root: Path) -> dict | None:
    """``refresh_one_task`` + best-effort index upsert.

    Use this from callers that have a stable ``runs_root`` handy (the
    dispatcher does).  ``refresh_one_task`` itself stays pure so existing
    callers that only know about the task directory keep working.
    """
    summary = refresh_one_task(task_dir)
    try:
        upsert_index_row(runs_root, task_dir, summary)
    except Exception as e:  # noqa: BLE001 — must not break refresh, but log so operators see staleness
        # Round-5 Phase 2 (M2): the index is a cache; webui falls back to a
        # slow scan when it's stale.  Don't crash the refresh, but DO log so
        # operators notice when index writes are failing en masse.
        LOG.error("upsert_index_row failed for %s: %s", task_dir.name, e)
    return summary


def refresh_all_tasks(runs_root: Path) -> int:
    """Walk every task dir under ``runs_root``, refresh its summary, and
    rewrite the flat ``runs_index.json`` cache.

    Returns the number of summaries successfully (re)written.
    """
    runs_root = Path(runs_root)
    if not runs_root.is_dir():
        return 0
    n = 0
    index_rows: list[dict] = []
    # layout: <runs_root>/<backend>/<model_dir>/<suite>/<task>/
    for backend_dir in sorted(runs_root.iterdir()):
        if not backend_dir.is_dir() or backend_dir.name.startswith("."):
            continue
        for model_dir in sorted(backend_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            for suite_dir in sorted(model_dir.iterdir()):
                if not suite_dir.is_dir():
                    continue
                for task_dir in sorted(suite_dir.iterdir()):
                    if not task_dir.is_dir():
                        continue
                    summary = refresh_one_task(task_dir)
                    if summary is None:
                        continue
                    n += 1
                    try:
                        index_rows.append(_build_index_row(task_dir, summary, runs_root=runs_root))
                    except Exception as e:  # noqa: BLE001
                        # Round-5 Phase 2 (M2): an index-row glitch must not
                        # block summary writes, but log so corrupted rows
                        # surface in operator logs instead of silently
                        # dropping out of the cache.
                        LOG.error("_build_index_row failed for %s: %s", task_dir.name, e)
                        continue
    try:
        write_runs_index(runs_root, index_rows)
    except Exception as e:  # noqa: BLE001
        # Round-5 Phase 2 (M2): index file write failure is recoverable
        # (webui falls back to scan) but log it so operators know.
        LOG.error("write_runs_index failed: %s", e)
    return n


def rebuild_index_only(runs_root: Path) -> int:
    """Walk task summaries and rewrite ``.runs_index.json`` from them.

    Cheaper than ``refresh_all_tasks`` — does **not** rebuild per-task
    summaries; only refreshes the flat cache.  Use this when the on-disk
    summaries are known to be correct (e.g. after an external rsync of
    fresh attempt directories) but the cache is stale.
    """
    runs_root = Path(runs_root)
    if not runs_root.is_dir():
        return 0
    rows: list[dict] = []
    for sj in sorted(runs_root.glob("*/*/*/*/summary.json")):
        if sj.parent.name.startswith("."):
            continue
        summary = _safe_load_json(sj)
        if not summary.get("attempts"):
            continue
        try:
            rows.append(_build_index_row(sj.parent, summary, runs_root=runs_root))
        except Exception:  # noqa: BLE001
            continue
    write_runs_index(runs_root, rows)
    return len(rows)


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Rebuild task-level summary.json files and/or the flat runs_index.json cache",
    )
    parser.add_argument("--runs-root", required=True, type=Path)
    parser.add_argument("--task", type=Path, help="single task_dir; if omitted, full scan")
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="just rebuild .runs_index.json from existing summary.json files (cheap)",
    )
    args = parser.parse_args()

    if args.index_only:
        n = rebuild_index_only(args.runs_root)
        print(f"rebuilt index with {n} rows → {index_path(args.runs_root)}")
        return
    if args.task:
        out = refresh_one_task_with_index(args.task, args.runs_root)
        print("rewrote" if out else "no-op")
    else:
        n = refresh_all_tasks(args.runs_root)
        print(f"refreshed {n} task summaries (+ rewrote .runs_index.json)")


if __name__ == "__main__":
    _cli()
