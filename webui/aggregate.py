"""Aggregation helpers for the WebUI Leaderboard & Tasks pages.

Kept out of ``webui/server.py`` so the request handler stays focused on
HTTP. All public functions are pure-ish: they read disk on demand and
``aggregate_runs`` memoizes by an mtime+count fingerprint over
``runs/**/summary.json`` (cheap to compute, invalidates whenever
summaries are added or rewritten).
"""

from __future__ import annotations

import json
import os
import sys
import threading
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
# webui/aggregate.py is invoked both as ``from webui import aggregate`` (when
# the cwd is the repo) and via ``python3 webui/server.py`` from the repo
# root, but the repo root may not be on sys.path in either case.  Add it
# defensively so the ``lib.status`` import works in both.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.status import TERMINAL_RESULT_STATUSES, normalize_final_status  # noqa: E402
from lib.runtime_metrics import attempt_runtime_ms  # noqa: E402
from lib.util.model_naming import display_model_name, include_in_public_webui  # noqa: E402

# Mirror webui/server.py: allow runs/ to live outside the repo via env var.
RUNS = Path(os.environ.get("CLAWBENCH_RUNS_DIR", str(ROOT / "runs"))).expanduser()
TASKS = ROOT / "tasks"
INJECTION = ROOT / "injection"


def _expose_hidden_references() -> bool:
    """Allow local debugging to opt into private reference/eval-rule display."""

    return os.environ.get("CLAWBENCH_WEBUI_EXPOSE_HIDDEN_REFERENCES") == "1"


def _public_task_yaml(doc: dict, *, expose_hidden: bool) -> dict:
    payload = deepcopy(doc)
    if not expose_hidden:
        payload.pop("references", None)
    return payload

# Category order surfaced in the UI, discovered dynamically from tasks/ so
# renamed suites and the 2xx_zh mirrors appear without a hardcoded list.
# Mirrors scripts/orchestra/stats.py:_canonical_tasks — 3-digit suite dirs,
# excluding the 000_template / 001_smoketest scaffolding. Sorted for a
# stable order; empty categories still render as "—" rather than missing rows.
def _discover_categories() -> tuple[str, ...]:
    if not TASKS.is_dir():
        return ()
    return tuple(
        d.name
        for d in sorted(TASKS.iterdir())
        if d.is_dir() and d.name[:3].isdigit() and not d.name.startswith(("000_", "001_"))
    )


KNOWN_CATEGORIES = _discover_categories()


def _summary_passed(payload: dict, canonical_status: str) -> bool:
    passed = payload.get("passed")
    if isinstance(passed, bool):
        return passed
    return canonical_status == "pass"


# ─── Aggregate ────────────────────────────────────────────────────────

_AGG_LOCK = threading.Lock()
_AGG_CACHE: dict | None = None
_AGG_KEY: tuple | None = None


def _fingerprint() -> tuple:
    if not RUNS.exists():
        return (0.0, 0)
    latest = 0.0
    count = 0
    for pattern in (
        "*/*/*/*/summary.json",
        "*/*/*/*/p*-*/meta.json",
        "*/*/*/*/p*-*/usage.json",
    ):
        for path in RUNS.glob(pattern):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > latest:
                latest = mtime
            count += 1
    return (latest, count)


def aggregate_runs(force: bool = False) -> dict:
    """Group every summary.json by model and by backend.

    Each entry: ``{ key, label, backend, total: {pass_rate, avg_score, n},
    byCategory: { "<cat>": {pass_rate, avg_score, n} } }``.

    ``force=True`` bypasses the mtime cache (used by the FAB refresh).
    """
    global _AGG_CACHE, _AGG_KEY
    if not force:
        with _AGG_LOCK:
            current = _fingerprint()
            if _AGG_CACHE is not None and _AGG_KEY == current:
                return _AGG_CACHE

    rows: list[dict] = []
    if RUNS.exists():
        for summary_path in RUNS.glob("*/*/*/*/summary.json"):
            try:
                payload = json.loads(summary_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            # Round 8 / A3: only the four terminal-result statuses
            # ({pass, budget_exhausted, fail, global_timeout}) belong in
            # Results-page averages.  Pre-fix this filter only checked
            # ``finalScore is None`` — rate_limit / infra_error / pre_exec_failed
            # attempts can carry finalScore=0.0, which is not None, so they
            # silently corrupted Results-page token / runtime / pass_rate
            # means with executor-never-ran data.
            canonical_status = normalize_final_status(payload.get("finalStatus") or "")
            if canonical_status not in TERMINAL_RESULT_STATUSES:
                continue
            score = payload.get("finalScore")
            if score is None:
                continue
            backend = (payload.get("backend") or summary_path.parents[3].name).strip().lower()
            model_slug = payload.get("modelSlug") or summary_path.parents[2].name
            model_label = display_model_name(payload.get("model") or model_slug)
            public_model_key = display_model_name(model_slug)
            category = summary_path.parent.parent.name
            if not include_in_public_webui(backend, payload.get("model") or model_slug, category):
                continue
            task_id = payload.get("taskId") or summary_path.parent.name
            prompt_tokens, completion_tokens, runtime_ms = _extract_stats(payload, summary_path)
            rows.append(
                {
                    "backend": backend,
                    "model_slug": public_model_key,
                    "model_label": model_label,
                    "category": category,
                    "task_id": task_id,
                    "score": float(score),
                    "passed": _summary_passed(payload, canonical_status),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "runtime_ms": runtime_ms,
                    "_summary_mtime": summary_path.stat().st_mtime,
                }
            )

    rows = _dedupe_public_result_rows(rows)

    # ── Model tab: filter to openclaw rows only so each model is one row.
    # Cross-backend mixing on the Model tab masked per-backend differences
    # and made same-model multi-backend runs collapse onto one row keyed
    # by whichever backend got loaded first. Restricting to openclaw keeps
    # Model tab as the canonical "model leaderboard".
    openclaw_rows = [r for r in rows if r["backend"] == "openclaw"]

    # ── Backend tab → Show models: each (backend, model) pair is a row.
    # The previous design grouped by model_slug only, so a model that ran
    # on multiple backends (e.g. gpt-5.4 on openclaw + nanobot + edict)
    # collapsed to a single entry whose ``backend`` was whichever appeared
    # first. Backend tab filtering by ``m.backend === 'openclaw'`` then
    # silently dropped that model. Composite key fixes that.
    pair_rows = [
        {**r, "_pair_key": f"{r['backend']}::{r['model_slug']}"}
        for r in rows
    ]

    # ── Task coverage map: which backends ran each (category, task_id)?
    # Used by the Backend tab "all-backend coverage" toggle to filter to
    # tasks present in every backend before re-aggregating.
    task_backends: dict[str, list[str]] = {}
    for row in rows:
        ck = f"{row['category']}::{row['task_id']}"
        if ck not in task_backends:
            task_backends[ck] = []
        if row["backend"] not in task_backends[ck]:
            task_backends[ck].append(row["backend"])
    for ck in task_backends:
        task_backends[ck].sort()

    result = {
        "models": _group(openclaw_rows, key_field="model_slug", label_field="model_label", carry_backend=True),
        "backends": _group(rows, key_field="backend", label_field="backend", carry_backend=False),
        "model_backend_pairs": _group(
            pair_rows, key_field="_pair_key", label_field="model_label", carry_backend=True
        ),
        "rows": rows,
        "task_backends": task_backends,
        "all_backends": sorted({r["backend"] for r in rows}),
        "categories": list(KNOWN_CATEGORIES),
    }

    with _AGG_LOCK:
        _AGG_CACHE = result
        _AGG_KEY = _fingerprint()
    return result


def _dedupe_public_result_rows(rows: list[dict]) -> list[dict]:
    """Collapse provider/keypool aliases after public model-name normalization."""

    by_key: dict[tuple[str, str, str, str], dict] = {}
    for row in rows:
        key = (
            str(row.get("backend") or ""),
            str(row.get("model_slug") or row.get("model_label") or ""),
            str(row.get("category") or ""),
            str(row.get("task_id") or ""),
        )
        current = by_key.get(key)
        if current is None or float(row.get("_summary_mtime") or 0) >= float(current.get("_summary_mtime") or 0):
            by_key[key] = row
    out: list[dict] = []
    for row in by_key.values():
        row = dict(row)
        row.pop("_summary_mtime", None)
        out.append(row)
    out.sort(key=lambda r: (r.get("backend") or "", r.get("model_slug") or "", r.get("category") or "", r.get("task_id") or ""))
    return out


def _group(rows: list[dict], *, key_field: str, label_field: str, carry_backend: bool) -> list[dict]:
    bucket: dict[str, dict] = {}
    for row in rows:
        key = row[key_field]
        slot = bucket.setdefault(key, {"key": key, "label": row[label_field], "rows": []})
        if carry_backend and "backend" not in slot:
            slot["backend"] = row["backend"]
        slot["rows"].append(row)

    grouped: list[dict] = []
    for slot in bucket.values():
        slot_rows = slot.pop("rows")
        slot["total"] = _summarize(slot_rows)
        slot["byCategory"] = {
            cat: _summarize([r for r in slot_rows if r["category"] == cat]) for cat in KNOWN_CATEGORIES
        }
        grouped.append(slot)
    grouped.sort(key=lambda s: s["label"].lower())
    return grouped


def _summarize(rows: list[dict]) -> dict:
    if not rows:
        return {
            "pass_rate": None,
            "avg_score": None,
            "n": 0,
            "avg_input_tokens": None,
            "avg_output_tokens": None,
            "avg_runtime_ms": None,
        }
    n = len(rows)

    def _mean(field: str) -> float | None:
        vals = [r[field] for r in rows if r.get(field) is not None]
        return (sum(vals) / len(vals)) if vals else None

    return {
        "pass_rate": sum(1 for r in rows if r["passed"]) / n,
        "avg_score": sum(r["score"] for r in rows) / n,
        "n": n,
        "avg_input_tokens": _mean("prompt_tokens"),
        "avg_output_tokens": _mean("completion_tokens"),
        "avg_runtime_ms": _mean("runtime_ms"),
    }


def _extract_stats(payload: dict, summary_path: Path) -> tuple[int | None, int | None, int | None]:
    """Return ``(prompt_tokens, completion_tokens, runtime_ms)`` for the resolved attempt.

    Reads ``usage.json`` (executor token roll-up) and the attempt's
    ``runtimeMs`` from ``summary.json``. Missing files return ``None``.
    """
    attempts = payload.get("attempts") or []
    if not attempts:
        return None, None, None

    chosen = None
    resolved = payload.get("resolvedAttempt")
    if isinstance(resolved, int):
        for attempt in attempts:
            if attempt.get("attempt") == resolved:
                chosen = attempt
                break
    if chosen is None:
        chosen = attempts[-1]

    out_dir_str = chosen.get("outDir")
    if not out_dir_str:
        return None, None, attempt_runtime_ms(chosen, None)
    # Always resolve attempt dir locally relative to summary.json (the absolute
    # outDir written by the worker may point to a remote-host path that does
    # not exist locally — we want the basename in OUR task_dir instead).
    out_dir = summary_path.parent / Path(out_dir_str).name

    runtime_ms = attempt_runtime_ms(chosen, out_dir)

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    usage_path = out_dir / "usage.json"
    if usage_path.exists():
        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            exec_sum = (usage.get("summary") or {}).get("executor") or {}
            prompt_tokens = exec_sum.get("prompt_tokens")
            completion_tokens = exec_sum.get("completion_tokens")
        except (OSError, json.JSONDecodeError):
            pass

    return prompt_tokens, completion_tokens, runtime_ms


# ─── Tasks ────────────────────────────────────────────────────────────


def _load_task_yaml(path: Path) -> dict | None:
    try:
        with path.open(encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None
    return doc if isinstance(doc, dict) else None


def _asset_flags(category: str, task_id: str) -> dict:
    base = INJECTION / category / task_id
    return {
        "has_privacy": (base / ".privacy").exists(),
        "has_sources": (base / "sources").is_dir(),
        "has_references": (base / "references").is_dir(),
        "has_skills": (base / "skills").is_dir(),
    }


def _list_injected_skills(category: str, task_id: str) -> list[str] | None:
    """Return skill slugs under ``injection/<cat>/<task>/skills/``.

    Each skill is a sub-directory (name = slug) containing SKILL.md plus
    optional metadata. We surface only the slug — the aside card is a
    simple list, not a full descriptor.
    """
    skills_dir = INJECTION / category / task_id / "skills"
    if not skills_dir.is_dir():
        return None
    names: list[str] = []
    try:
        for entry in sorted(skills_dir.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                names.append(entry.name)
    except OSError:
        return []
    return names


def list_task_yamls() -> list[dict]:
    """Enumerate every task YAML under ``tasks/<cat>/`` for the Tasks list."""
    out: list[dict] = []
    if not TASKS.exists():
        return out
    # The Tasks browser shows EVERY suite dir (3-digit prefix), including the
    # 000_template / 001_smoketest scaffolding so they appear under the
    # Smoketest group. Results aggregation still uses KNOWN_CATEGORIES, which
    # excludes them.
    for cat_dir in sorted(TASKS.iterdir()):
        if not cat_dir.is_dir() or not cat_dir.name[:3].isdigit():
            continue
        category = cat_dir.name
        for yaml_path in sorted(cat_dir.glob("*.yaml")):
            doc = _load_task_yaml(yaml_path)
            if not doc:
                continue
            task_id = doc.get("task_id") or yaml_path.stem
            prompt = (doc.get("task") or "").strip()
            preview = prompt[:200] + ("…" if len(prompt) > 200 else "")
            out.append(
                {
                    "task_id": task_id,
                    "category": category,
                    "model": doc.get("model"),
                    "skills": doc.get("skills") or [],
                    "prompt_preview": preview,
                    "timeout_seconds": doc.get("timeout_seconds"),
                    "success_threshold": doc.get("success_threshold"),
                    **_asset_flags(category, task_id),
                }
            )
    return out


def task_detail(task_id: str, *, expose_hidden: bool | None = None) -> dict | None:
    """Full task payload for the detail page."""
    yaml_path: Path | None = None
    category: str | None = None
    # Search every suite dir (incl. 000/001) so Smoketest task pages resolve.
    for cat_dir in sorted(TASKS.iterdir()):
        if not cat_dir.is_dir() or not cat_dir.name[:3].isdigit():
            continue
        candidate = cat_dir / f"{task_id}.yaml"
        if candidate.exists():
            yaml_path, category = candidate, cat_dir.name
            break
    if yaml_path is None or category is None:
        return None
    doc = _load_task_yaml(yaml_path)
    if doc is None:
        return None

    base = INJECTION / category / task_id
    privacy_count: int | None = None
    privacy_path = base / ".privacy"
    if privacy_path.exists():
        privacy_count = 0
        for line in privacy_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                privacy_count += 1

    expose_hidden = _expose_hidden_references() if expose_hidden is None else bool(expose_hidden)
    eval_rule_md = ""
    eval_rule_path = base / "references" / "eval_rule.md"
    if expose_hidden and eval_rule_path.exists():
        eval_rule_md = eval_rule_path.read_text(encoding="utf-8", errors="ignore")

    sources_root = base / "sources"
    references_root = base / "references"
    skills_list = _list_injected_skills(category, task_id)
    return {
        "task_id": task_id,
        "category": category,
        "task_yaml": _public_task_yaml(doc, expose_hidden=expose_hidden),
        "prompt": doc.get("task") or "",
        "eval_rule_md": eval_rule_md,
        "assets": {
            "privacy": (
                {"present": True, "count": privacy_count or 0}
                if privacy_count is not None
                else None
            ),
            "skills": skills_list,
            "sources": (
                walk_tree(sources_root, category=category, task_id=task_id, asset_type="sources")
                if sources_root.is_dir()
                else None
            ),
            "references": (
                walk_tree(references_root, category=category, task_id=task_id, asset_type="references")
                if expose_hidden and references_root.is_dir()
                else None
            ),
        },
    }


def walk_tree(
    root: Path,
    *,
    category: str,
    task_id: str,
    asset_type: str,
    max_depth: int | None = None,
) -> list[dict]:
    """Return ``[ { name, path, is_dir, size?, url?, children? } ]``.

    ``url`` for files points at the static ``/injection/...`` path so the
    front-end can fetch / preview / download via the existing static
    handler — no separate ``/api/asset`` endpoint needed.
    """
    if not root.exists():
        return []
    base_url = f"/injection/{category}/{task_id}/{asset_type}"

    def descend(directory: Path, depth: int) -> list[dict]:
        if max_depth is not None and depth > max_depth:
            return []
        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return []
        nodes: list[dict] = []
        for path in entries:
            if path.name.startswith("."):
                continue
            rel = path.relative_to(root).as_posix()
            parts = rel.split("/")
            if "privacy" in parts or rel.endswith("/env.env") or path.name == "env.env":
                continue
            node: dict = {"name": path.name, "path": rel}
            if path.is_dir():
                node["is_dir"] = True
                node["children"] = descend(path, depth + 1)
            else:
                node["is_dir"] = False
                try:
                    node["size"] = path.stat().st_size
                except OSError:
                    node["size"] = 0
                node["url"] = f"{base_url}/{rel}"
            nodes.append(node)
        return nodes

    return descend(root, 1)
