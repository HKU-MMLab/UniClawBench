#!/usr/bin/env python3
"""Export a backend-free WebUI bundle.

The static export keeps Home, Leaderboard, Tasks, and Trace usable without a
Python backend.  It writes a compact Trace run list for fast first paint, then
ships selected-attempt detail JSON and referenced task assets so selecting a run
exercises the same timeline/transcript/results UI as the live WebUI.  A heavier
``all-attempts`` mode is available for archival mirrors.

Usage (run on the host that owns the populated ``runs/`` tree)::

    python3 webui/export_static.py --runs-root ./runs --out ./static-site

Then publish the ``./static-site`` directory with a static HTTP host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote


# webui/export_static.py → repo root is one level up. Add it to sys.path so
# ``from webui import aggregate`` resolves regardless of cwd (mirrors the
# convention in scripts/orchestra/*.py and webui/aggregate.py itself).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.util.model_naming import display_model_name

STATIC_SRC = ROOT / "webui" / "static"
ASSETS_SRC = ROOT / "assets"
STATIC_EXPORT_SCHEMA = "clawbench.static.v2"
EXPORT_MARKER = ".clawbench_static_export"
ASSET_MODES = ("full", "lite")
TRACE_DETAIL_POLICIES = ("selected", "all-attempts")
LITE_RUN_ASSET_REASON = "Run artifact omitted from lite static export."
_PUBLIC_ASSET_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_public_asset_name(name: str) -> str:
    raw = unquote(str(name or "")).strip()
    cleaned = _PUBLIC_ASSET_NAME_RE.sub("_", raw).strip("._")
    if not cleaned:
        return "artifact"
    if len(cleaned) <= 120:
        return cleaned
    suffix = "".join(Path(cleaned).suffixes)
    stem = cleaned[: max(1, 120 - len(suffix))]
    return f"{stem}{suffix}" if suffix else stem


def _asset_url(base_url: str | None, rel: str) -> str:
    rel = str(rel or "").lstrip("/")
    if not base_url:
        return rel
    return f"{base_url.rstrip('/')}/{rel}"


def _build_index_html(*, attempts_base: str = "attempts", injection_base: str = "injection") -> str:
    """Return the static-export entry page.

    The entry page mirrors the live shell but points each route at exported
    JSON files through ``window.CLAWBENCH_STATIC_*`` globals.
    """
    attempts_base_json = json.dumps(attempts_base)
    injection_base_json = json.dumps(injection_base)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>UniClawBench</title>
    <link rel="stylesheet" href="static/style.css?v=static_7" />
  </head>
  <body>
    <nav class="topnav">
      <a href="#/home" class="brand">
        <span class="brand-name">UniClawBench</span>
        <span class="brand-tag">Capability-driven agent evaluation</span>
      </a>
      <div class="topnav-links">
        <a class="topnav-link active" data-page="home" href="#/home">Home</a>
        <a class="topnav-link" data-page="leaderboard" href="#/leaderboard/model">Leaderboard</a>
        <a class="topnav-link" data-page="tasks" href="#/tasks">Tasks</a>
        <a class="topnav-link" data-page="trace" href="#/trace">Trace</a>
      </div>
    </nav>
    <div id="page-root" class="page-root"></div>
    <button id="refresh-fab" class="refresh-fab" type="button" aria-label="Refresh current data" title="Refresh current data">
      <svg class="refresh-fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 12a9 9 0 1 1-2.64-6.36" />
        <polyline points="21 3 21 9 15 9" />
      </svg>
    </button>
    <script>
      window.CLAWBENCH_STATIC_DATA = "results.json";
      window.CLAWBENCH_STATIC_TASKS = "tasks.json";
      window.CLAWBENCH_STATIC_TASK_DETAIL_BASE = "task-details";
      window.CLAWBENCH_STATIC_RUNS = "runs.json";
      window.CLAWBENCH_STATIC_ATTEMPTS_BASE = {attempts_base_json};
      window.CLAWBENCH_STATIC_INJECTION_BASE = {injection_base_json};
    </script>
    <div id="image-lightbox" class="lightbox hidden" aria-hidden="true">
      <div id="lightbox-backdrop" class="lightbox-backdrop"></div>
      <div class="lightbox-dialog" role="dialog" aria-modal="true" aria-label="Image preview">
        <button id="lightbox-close" class="lightbox-close" type="button" aria-label="Close image preview">×</button>
        <img id="lightbox-image" class="lightbox-image" alt="" />
        <div id="lightbox-caption" class="lightbox-caption"></div>
      </div>
    </div>
    <div id="file-modal" class="file-modal hidden" aria-hidden="true">
      <div id="file-modal-backdrop" class="file-modal-backdrop"></div>
      <div class="file-modal-dialog" role="dialog" aria-modal="true" aria-label="File preview">
        <header class="file-modal-head">
          <span id="file-modal-title" class="file-modal-title"></span>
          <a id="file-modal-open" class="file-modal-open" target="_blank" rel="noopener" title="Open raw">↗</a>
          <button id="file-modal-close" class="file-modal-close" type="button" aria-label="Close preview">×</button>
        </header>
        <div id="file-modal-body" class="file-modal-body"></div>
      </div>
    </div>
    <script type="module" src="static/main.js?v=static_7"></script>
  </body>
</html>
"""


def _slim_aggregate(data: dict) -> dict:
    """Return a leaner copy of the aggregate for the static results.json.

    The static page can derive model/backend aggregates from ``rows`` in the
    browser, so the file only needs raw rows, model-label hydration data,
    backend names, and a task count for the coverage banner.
    """
    rows = data.get("rows") or []
    model_labels: dict[str, str] = {}
    slim_rows = []
    for row in rows:
        slug = row.get("model_slug")
        label = row.get("model_label")
        backend = row.get("backend")
        public_model = display_model_name(str(label or slug or row.get("model") or ""))
        if slug is not None and label is not None:
            key = f"{backend or ''}::{public_model}"
            if key not in model_labels:
                model_labels[key] = public_model
        slim_row = {k: v for k, v in row.items() if k != "model_label"}
        if "model_slug" in slim_row:
            slim_row["model_slug"] = public_model
        if "model" in slim_row:
            slim_row["model"] = display_model_name(str(slim_row["model"]))
        slim_rows.append(slim_row)

    task_backends = data.get("task_backends")
    if isinstance(task_backends, dict):
        task_count = len(task_backends)
    else:
        task_count = len(
            {
                f"{row.get('category')}::{row.get('task_id')}"
                for row in rows
                if row.get("category") and row.get("task_id")
            }
        )

    return {
        "schema": STATIC_EXPORT_SCHEMA,
        "kind": "results",
        "rows": slim_rows,
        "model_labels": model_labels,
        "all_backends": data.get("all_backends")
        or sorted({row.get("backend") for row in rows if row.get("backend")}),
        "categories": data.get("categories")
        or _categories_from_aggregate(data)
        or sorted({row.get("category") for row in rows if row.get("category")}),
        "task_count": task_count,
    }


def _categories_from_aggregate(data: dict) -> list[str]:
    categories: set[str] = set()
    for group_name in ("models", "backends", "model_backend_pairs"):
        for entry in data.get(group_name) or []:
            by_category = entry.get("byCategory") if isinstance(entry, dict) else None
            if isinstance(by_category, dict):
                categories.update(str(key) for key in by_category.keys() if key)
    return sorted(categories)


def _copy_static_assets(out: Path) -> None:
    static_dst = out / "static"
    if static_dst.exists():
        shutil.rmtree(static_dst)
    shutil.copytree(STATIC_SRC, static_dst)
    assets_dst = out / "assets"
    if assets_dst.exists():
        shutil.rmtree(assets_dst)
    if ASSETS_SRC.exists():
        shutil.copytree(ASSETS_SRC, assets_dst)


def _write_json(path: Path, payload: object) -> int:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8", errors="replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)


def _write_json_compact(path: Path, payload: object) -> int:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8", errors="replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)


def _packed_runs_payload(rows: list[dict]) -> dict:
    fields = [
        "category",
        "taskId",
        "backend",
        "model",
        "modelSlug",
        "summaryPath",
        "settingKey",
        "selectedAttemptPath",
        "finalScore",
        "rawFinalScore",
        "passed",
        "finalStatus",
        "runtimeMs",
        "continuationCount",
        "supervisionCycleCount",
        "supervisionVerdict",
        "checkpointCounts",
        "createdAt",
    ]
    return {
        "schema": STATIC_EXPORT_SCHEMA,
        "kind": "runs_packed",
        "fields": fields,
        "runs": [[row.get(field) for field in fields] for row in rows],
    }


def _is_private_rel(rel: str) -> bool:
    parts = [part for part in Path(rel).parts if part not in ("", ".")]
    if ".privacy" in parts:
        return True
    joined = "/".join(parts)
    return "/privacy/" in f"/{joined}/" or joined.endswith("/env.env")


def _iter_urls(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            if isinstance(item, str) and item.startswith(("/runs/", "/injection/", "/tasks/")):
                yield item
            yield from _iter_urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_urls(item)
    elif isinstance(value, str) and value.startswith(("/runs/", "/injection/", "/tasks/")):
        yield value


def _stable_public_id(prefix: str, value: str, length: int = 16) -> str:
    digest = hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def _is_attempt_rel_path(rel_path: str) -> bool:
    name = Path(str(rel_path or "")).name
    if not name.startswith("p") or "-" not in name:
        return False
    return name[1:].split("-", 1)[0].isdigit()


def _trace_parent_run_path(rel_path: str) -> str:
    rel = str(rel_path or "").strip("/")
    if not _is_attempt_rel_path(rel):
        return rel
    parts = [part for part in Path(rel).parts if part not in ("", ".", "..")]
    return "/".join(parts[:-1])


def _public_run_path(rel_path: str) -> str:
    return f"r/{_stable_public_id('run', _trace_parent_run_path(rel_path))}"


def _public_trace_path(rel_path: str) -> str:
    rel = str(rel_path or "").strip("/")
    parent = _trace_parent_run_path(rel)
    run_path = _public_run_path(parent)
    if rel == parent:
        return run_path
    return f"{run_path}/a/{_stable_public_id('attempt', rel)}"


def _static_asset_rel_for_url(url: str) -> str:
    clean = str(url or "").split("?", 1)[0].split("#", 1)[0]
    if clean.startswith("/runs/"):
        rel = unquote(clean.removeprefix("/runs/"))
        digest = hashlib.sha1(rel.encode("utf-8", errors="ignore")).hexdigest()[:20]
        name = _safe_public_asset_name(Path(rel).name or "artifact")
        return str(Path("artifacts", digest, name))
    for prefix in ("/injection/", "/tasks/"):
        if clean.startswith(prefix):
            return clean[1:]
    return clean.lstrip("/")


def _rewrite_static_urls(value: object, *, asset_base_url: str | None = None, asset_mode: str = "full") -> object:
    if isinstance(value, dict):
        return {key: _rewrite_static_urls(item, asset_base_url=asset_base_url, asset_mode=asset_mode) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite_static_urls(item, asset_base_url=asset_base_url, asset_mode=asset_mode) for item in value]
    if isinstance(value, str):
        if value.startswith("/runs/"):
            rel = _static_asset_rel_for_url(value)
            return rel if asset_mode == "lite" else _asset_url(asset_base_url, rel)
        if value.startswith("/injection/"):
            return _asset_url(asset_base_url, value[1:])
        if value.startswith("/tasks/"):
            return value[1:]
    return value


def _is_run_url(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("/runs/", "artifacts/"))


def _mark_lite_run_asset_urls(value: object) -> None:
    """Remove run artifact URLs from a static payload in lite mode.

    Lite exports still ship task/injection assets plus all trace metadata and
    inline text previews, but they intentionally omit per-run binary artifacts
    such as saved videos, screenshots, PDFs, and large result files.  Mark the
    affected objects instead of leaving broken links in the frontend.
    """

    if isinstance(value, dict):
        removed = False
        for key in ("url", "poster"):
            if _is_run_url(value.get(key)):
                value.pop(key, None)
                removed = True
        if removed:
            value["assetSkipped"] = True
            value.setdefault("assetUnavailableReason", LITE_RUN_ASSET_REASON)
        for item in value.values():
            _mark_lite_run_asset_urls(item)
    elif isinstance(value, list):
        for item in value:
            _mark_lite_run_asset_urls(item)


def _copy_file(src: Path, dst: Path) -> int:
    try:
        if not src.is_file():
            return 0
        size = src.stat().st_size
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Static exports are commonly generated beside the source runs tree on
        # the same controller volume.  Prefer hardlinks so full Trace exports
        # (recordings, screenshots, result files) stay fast and space-efficient;
        # fall back to copy2 when crossing filesystems or publishing from a
        # filesystem that does not support links.  A hardlinked export is still
        # a normal file tree: moving it with rsync/git/GitHub Pages materializes
        # file contents just like copied files.
        try:
            if dst.exists():
                dst.unlink()
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        return size
    except OSError:
        return 0


def _copy_asset_for_url(url: str, *, runs_root: Path, out: Path, asset_mode: str = "full") -> int:
    clean = str(url).split("?", 1)[0].split("#", 1)[0]
    if clean.startswith("/runs/"):
        if asset_mode == "lite":
            return 0
        rel = unquote(clean.removeprefix("/runs/"))
        if _is_private_rel(rel):
            return 0
        from webui import server  # late import; export() retargets server.RUNS

        if not server._is_public_run_artifact_rel(rel):
            return 0
        target = server.safe_rel_path(rel, runs_root)
        if target is None:
            return 0
        return _copy_file(target, out / _static_asset_rel_for_url(clean))
    if clean.startswith("/injection/"):
        rel = unquote(clean.removeprefix("/injection/"))
        if _is_private_rel(rel):
            return 0
        return _copy_file(ROOT / "injection" / rel, out / "injection" / rel)
    if clean.startswith("/tasks/"):
        rel = unquote(clean.removeprefix("/tasks/"))
        if _is_private_rel(rel):
            return 0
        return _copy_file(ROOT / "tasks" / rel, out / "tasks" / rel)
    return 0


def _copy_payload_assets(
    payload: object,
    *,
    runs_root: Path,
    out: Path,
    asset_mode: str = "full",
    seen_urls: set[str] | None = None,
    asset_sizes: list[dict] | None = None,
) -> tuple[int, int]:
    copied = 0
    copied_bytes = 0
    for url in sorted(set(_iter_urls(payload))):
        if seen_urls is not None and url in seen_urls:
            continue
        if seen_urls is not None:
            seen_urls.add(url)
        size = _copy_asset_for_url(url, runs_root=runs_root, out=out, asset_mode=asset_mode)
        if size:
            copied += 1
            copied_bytes += size
            if asset_sizes is not None:
                asset_sizes.append(
                    {
                        "staticPath": _static_asset_rel_for_url(url),
                        "sourceHash": hashlib.sha1(str(url).encode("utf-8", errors="ignore")).hexdigest(),
                        "bytes": size,
                    }
                )
    return copied, copied_bytes


def _strip_result_file_text(payload: dict) -> None:
    for file_info in payload.get("resultFiles") or []:
        if isinstance(file_info, dict):
            file_info.pop("text", None)


def _compact_static_attempt_payload(payload: dict, rel_path: str, *, asset_mode: str = "full") -> dict:
    """Trim fields that are redundant once artifacts are exported as files.

    The dynamic endpoint can afford to inline log/result text because it only
    serves one request at a time. A static bundle writes thousands of detail
    JSON files, so duplicated transcript/log/result payloads quickly dominate
    disk use. Keep the timeline-critical attemptDetails transcript data, but
    remove unused top-level duplicates and let result previews fetch text from
    the exported ``runs/...`` file URLs.
    """

    if asset_mode != "lite":
        _strip_result_file_text(payload)
    for key in ("transcript", "logs", "agentSessions", "toolUsage", "usage", "desktopProbe"):
        payload.pop(key, None)

    details = [item for item in payload.get("attemptDetails") or [] if isinstance(item, dict)]
    for detail in details:
        if asset_mode != "lite":
            _strip_result_file_text(detail)
        logs = detail.get("logs")
        if isinstance(logs, dict):
            detail["logs"] = {name: "" for name in logs}

    if Path(rel_path).name.startswith("p") and details:
        selected = str(payload.get("selectedAttemptPath") or rel_path)
        selected_details = [item for item in details if str(item.get("attemptPath") or "") == selected]
        payload["attemptDetails"] = selected_details or details[-1:]
    return payload


def _selected_attempt_path(payload: dict, fallback: str = "") -> str:
    selected = str(payload.get("selectedAttemptPath") or "").strip()
    if selected:
        return selected
    cards = [item for item in payload.get("attemptCards") or [] if isinstance(item, dict)]
    if cards:
        path = str(cards[-1].get("attemptPath") or "").strip()
        if path:
            return path
    details = [item for item in payload.get("attemptDetails") or [] if isinstance(item, dict)]
    if details:
        path = str(details[-1].get("attemptPath") or "").strip()
        if path:
            return path
    return str(fallback or "").strip()


def _filter_payload_to_selected_attempt(payload: dict, selected_path: str | None = None) -> None:
    """Keep only the resolved attempt in a static trace payload.

    The dynamic WebUI benefits from exposing every retry/attempt, but a public
    GitHub Pages export should stay focused on the result selected by the
    benchmark resolver.  Filtering before copying payload assets avoids writing
    unreferenced retry artifacts, and filtering ``attemptCards`` prevents the
    static attempt selector from linking to details that were intentionally not
    exported.
    """

    selected = str(selected_path or "").strip() or _selected_attempt_path(payload, "")
    if not selected:
        return
    payload["selectedAttemptPath"] = selected

    cards = [item for item in payload.get("attemptCards") or [] if isinstance(item, dict)]
    if cards:
        selected_cards = [item for item in cards if str(item.get("attemptPath") or "").strip() == selected]
        payload["attemptCards"] = selected_cards or cards[-1:]
        omitted = max(0, len(cards) - len(payload["attemptCards"]))
        if omitted:
            payload["omittedAttemptCount"] = omitted
            payload["staticTracePolicy"] = "selected"

    details = [item for item in payload.get("attemptDetails") or [] if isinstance(item, dict)]
    if details:
        selected_details = [item for item in details if str(item.get("attemptPath") or "").strip() == selected]
        payload["attemptDetails"] = selected_details or details[-1:]


def _task_detail_filename(task_id: str) -> str:
    return f"{task_id}.json"


def _attempt_detail_path(rel_path: str) -> Path:
    parts = [part for part in Path(_public_trace_path(rel_path)).parts if part not in ("", ".", "..")]
    return Path("attempts", *parts).with_suffix(".json")


def _publicize_trace_payload_paths(payload: dict) -> None:
    rel_path = str(payload.get("relPath") or "")
    if rel_path:
        payload["relPath"] = _public_run_path(rel_path)

    selected = str(payload.get("selectedAttemptPath") or "")
    if selected:
        payload["selectedAttemptPath"] = _public_trace_path(selected)

    for card in payload.get("attemptCards") or []:
        if isinstance(card, dict) and card.get("attemptPath"):
            card["attemptPath"] = _public_trace_path(str(card["attemptPath"]))

    for detail in payload.get("attemptDetails") or []:
        if isinstance(detail, dict) and detail.get("attemptPath"):
            detail["attemptPath"] = _public_trace_path(str(detail["attemptPath"]))


def _prepare_output_dir(runs_root: Path, out: Path, *, resume: bool = False) -> None:
    out_resolved = out.resolve()
    dangerous = {
        ROOT.resolve(),
        (ROOT / "webui").resolve(),
        STATIC_SRC.resolve(),
        runs_root.resolve(),
    }
    if out_resolved in dangerous or out_resolved.parent == out_resolved:
        raise ValueError(f"refusing to export into dangerous output path: {out}")

    marker = out / EXPORT_MARKER
    if out.exists():
        try:
            non_empty = any(out.iterdir())
        except OSError as exc:
            raise ValueError(f"cannot inspect output directory {out}: {exc}") from exc
        if non_empty and not marker.exists():
            raise ValueError(
                f"refusing to delete non-export directory {out}; remove it manually "
                f"or choose an empty/{EXPORT_MARKER}-marked export directory"
            )
        if resume:
            marker.write_text("clawbench static export\n", encoding="utf-8")
            return
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    marker.write_text("clawbench static export\n", encoding="utf-8")


def _remove_lite_run_artifact_tree(out: Path) -> None:
    artifacts = out / "artifacts"
    try:
        resolved = artifacts.resolve(strict=False)
        out_resolved = out.resolve(strict=False)
        if resolved != out_resolved and out_resolved not in resolved.parents:
            raise ValueError(f"refusing to remove artifact path outside export directory: {artifacts}")
    except OSError:
        return
    if artifacts.is_symlink() or artifacts.is_file():
        artifacts.unlink()
    elif artifacts.exists():
        shutil.rmtree(artifacts)


def export(
    runs_root: Path,
    out: Path,
    *,
    resume: bool = False,
    asset_mode: str = "full",
    trace_detail_policy: str = "selected",
    asset_out: Path | None = None,
    asset_base_url: str | None = None,
) -> dict:
    """Aggregate ``runs_root`` and write the static bundle to ``out``.

    Returns a small summary dict ``{rows, models, backends, bytes, out}``.
    """
    if asset_mode not in ASSET_MODES:
        raise ValueError(f"asset_mode must be one of {', '.join(ASSET_MODES)}")
    if trace_detail_policy not in TRACE_DETAIL_POLICIES:
        raise ValueError(f"trace_detail_policy must be one of {', '.join(TRACE_DETAIL_POLICIES)}")
    # aggregate.py reads CLAWBENCH_RUNS_DIR at import time, so point it at the
    # requested runs tree BEFORE importing the module.
    os.environ["CLAWBENCH_RUNS_DIR"] = str(runs_root)
    from webui import aggregate  # noqa: E402  (deliberately late)
    aggregate.RUNS = runs_root
    aggregate._AGG_CACHE = None
    aggregate._AGG_KEY = None

    # force=True bypasses the mtime cache so a freshly populated runs/ tree is
    # always re-read (same flag the FAB refresh uses via ?refresh=1).
    data = aggregate.aggregate_runs(force=True)

    from webui import server  # noqa: E402  (late so CLAWBENCH_RUNS_DIR wins)
    server.RUNS = runs_root

    _prepare_output_dir(runs_root, out, resume=resume)
    if asset_out is not None:
        asset_out = asset_out.expanduser().resolve()
        if asset_out == out:
            asset_out = None
        else:
            _prepare_output_dir(runs_root, asset_out, resume=resume)
    asset_root = asset_out or out
    if asset_mode == "lite":
        # A resumed lite export over an older full export must not keep stale
        # run artifacts around; otherwise GitHub Pages would still publish the
        # videos/screenshots even though lite JSON no longer links to them.
        _remove_lite_run_artifact_tree(asset_root)

    # Make the site shell available before the long run-detail export starts.
    # This keeps interrupted/long-running exports inspectable and avoids a
    # half-populated directory that lacks index.html or the SPA assets.
    _copy_static_assets(out)
    attempts_base = _asset_url(asset_base_url, "attempts") if asset_base_url else "attempts"
    injection_base = _asset_url(asset_base_url, "injection") if asset_base_url else "injection"
    index_html = _build_index_html(attempts_base=attempts_base, injection_base=injection_base)
    (out / "index.html").write_text(index_html, encoding="utf-8")
    # GitHub Pages serves 404.html for deep links such as /trace or
    # /tasks/<task_id>; keep it byte-identical to the SPA shell.
    (out / "404.html").write_text(index_html, encoding="utf-8")

    # 1) results.json: a slim results-only schema. The live endpoint stays
    #    full; the static page hydrates labels and derives the aggregate arrays
    #    from rows in-browser.
    slim = _slim_aggregate(data)
    results_path = out / "results.json"
    results_len = _write_json(results_path, slim)

    asset_count = 0
    asset_bytes = 0
    asset_sizes: list[dict] = []
    copied_asset_urls: set[str] = set()

    # 2) Tasks catalog and per-task details. These are task-definition data,
    #    not run artifacts, so they are small enough to ship with static
    #    exports and make the Tasks route genuinely usable offline.
    tasks = aggregate.list_task_yamls()
    tasks_len = _write_json(out / "tasks.json", {"schema": STATIC_EXPORT_SCHEMA, "kind": "tasks", "tasks": tasks})
    task_detail_bytes = 0
    for task in tasks:
        task_id = task.get("task_id")
        if not task_id:
            continue
        detail = aggregate.task_detail(task_id, expose_hidden=False)
        if detail is None:
            continue
        copied, copied_bytes = _copy_payload_assets(
            detail,
            runs_root=runs_root,
            out=asset_root,
            asset_mode=asset_mode,
            seen_urls=copied_asset_urls,
            asset_sizes=asset_sizes,
        )
        asset_count += copied
        asset_bytes += copied_bytes
        static_detail = _rewrite_static_urls(detail, asset_base_url=asset_base_url, asset_mode=asset_mode)
        task_detail_bytes += _write_json(out / "task-details" / _task_detail_filename(task_id), static_detail)

    # 3) Trace sidebar index plus lazy trace payloads. The default selected
    #    policy writes one detail payload per result row and filters it to the
    #    resolver-selected attempt. The heavier all-attempts policy preserves
    #    every retry attempt for archival mirrors.
    full_run_rows = server.list_task_runs()
    run_rows = server.slim_task_runs(full_run_rows)
    public_run_rows = []
    for row in run_rows:
        public_row = dict(row)
        if public_row.get("model"):
            public_row["model"] = display_model_name(str(public_row["model"]))
        if public_row.get("modelSlug"):
            public_row["modelSlug"] = display_model_name(str(public_row["modelSlug"]))
        if public_row.get("summaryPath"):
            public_row["summaryPath"] = _public_run_path(str(public_row["summaryPath"]))
        if public_row.get("selectedAttemptPath"):
            public_row["selectedAttemptPath"] = _public_trace_path(str(public_row["selectedAttemptPath"]))
        public_run_rows.append(public_row)
    runs_len = _write_json_compact(out / "runs.json", _packed_runs_payload(public_run_rows))
    attempt_bytes = 0
    written_attempt_details: set[str] = set()

    def write_attempt_detail(rel_path: str, *, selected_path: str | None = None) -> dict:
        nonlocal asset_count, asset_bytes, attempt_bytes
        if not rel_path or rel_path in written_attempt_details:
            return {}
        detail_path = asset_root / _attempt_detail_path(rel_path)
        payload = server.attempt_payload(rel_path, include_attempt_files=False)
        if trace_detail_policy == "selected":
            _filter_payload_to_selected_attempt(payload, selected_path)
        copied, copied_bytes = _copy_payload_assets(
            payload,
            runs_root=runs_root,
            out=asset_root,
            asset_mode=asset_mode,
            seen_urls=copied_asset_urls,
            asset_sizes=asset_sizes,
        )
        asset_count += copied
        asset_bytes += copied_bytes
        static_payload = _rewrite_static_urls(payload, asset_base_url=asset_base_url, asset_mode=asset_mode)
        if asset_mode == "lite":
            _mark_lite_run_asset_urls(static_payload)
            static_payload["staticAssetMode"] = "lite"
        _compact_static_attempt_payload(static_payload, rel_path, asset_mode=asset_mode)
        # Avoid publishing absolute controller/worker filesystem paths. The UI
        # uses attemptPath/selectedAttemptPath for navigation, not outDir.
        for detail in static_payload.get("attemptDetails") or []:
            if isinstance(detail, dict):
                detail.pop("outDir", None)
        _publicize_trace_payload_paths(static_payload)
        static_payload = server.sanitize_public_payload(static_payload)
        attempt_bytes += _write_json(detail_path, static_payload)
        written_attempt_details.add(rel_path)
        return payload

    for row in run_rows:
        rel_path = row.get("summaryPath")
        if not rel_path:
            continue
        # Trace cards load ``summaryPath`` in both the dynamic and static UI.
        # Let ``server.attempt_payload(summaryPath)`` apply the same
        # resolved-attempt selection that the dynamic endpoint uses; row-level
        # ``selectedAttemptPath`` can refer to an intermediate retry and would
        # make selected static exports diverge from the live trace page.
        task_payload = write_attempt_detail(rel_path)
        if trace_detail_policy == "selected":
            continue
        cards = task_payload.get("attemptCards") or []
        # The task-level payload already includes ``attemptDetails`` for all
        # attempts and is enough for single-attempt runs.  Only multi-attempt
        # runs need explicit attempt JSON because the Trace attempt selector
        # fetches those paths when the user switches away from the resolved
        # attempt.
        if len(cards) <= 1:
            continue
        for card in cards:
            if isinstance(card, dict):
                write_attempt_detail(str(card.get("attemptPath") or ""))

    # Do not walk the entire export tree for a final size.  Full static Trace
    # bundles can contain tens of thousands of hardlinked screenshots/videos,
    # and a recursive stat pass on network/attached volumes is often slower
    # than the export itself.  Report generated JSON bytes plus copied asset
    # count instead; filesystem tools can compute exact disk usage on demand.
    total_bytes = results_len + tasks_len + task_detail_bytes + runs_len + attempt_bytes
    largest_assets = sorted(asset_sizes, key=lambda item: int(item.get("bytes") or 0), reverse=True)[:100]
    asset_manifest_bytes = _write_json(
        out / "asset-manifest.json",
        {
            "schema": STATIC_EXPORT_SCHEMA,
            "kind": "asset_manifest",
            "asset_mode": asset_mode,
            "trace_detail_policy": trace_detail_policy,
            "asset_base_url": asset_base_url or "",
            "asset_split": asset_out is not None,
            "asset_count": asset_count,
            "asset_bytes": asset_bytes,
            "largest_assets": largest_assets,
        },
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")
    if asset_out is not None:
        (asset_out / ".nojekyll").write_text("", encoding="utf-8")
    return {
        "rows": len(data.get("rows") or []),
        "models": len(data.get("models") or []),
        "backends": len(data.get("backends") or []),
        "results_bytes": results_len,
        "tasks_bytes": tasks_len + task_detail_bytes,
        "runs_bytes": runs_len + attempt_bytes,
        "asset_count": asset_count,
        "asset_bytes": asset_bytes,
        "asset_manifest_bytes": asset_manifest_bytes,
        "asset_mode": asset_mode,
        "trace_detail_policy": trace_detail_policy,
        "asset_out": asset_root,
        "asset_base_url": asset_base_url or "",
        "total_bytes": total_bytes,
        "out": out,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the UniClawBench WebUI as a static, server-free site bundle.",
    )
    parser.add_argument(
        "--runs-root",
        default="./runs",
        help="Path to the runs/ tree to aggregate (default: ./runs).",
    )
    parser.add_argument(
        "--out",
        default="./static-site",
        help="Output directory for the static bundle (default: ./static-site).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume into an existing static export directory instead of deleting it first. "
            "Existing assets are reused, but attempt detail JSON is rewritten so public "
            "redaction and schema fixes are always applied."
        ),
    )
    parser.add_argument(
        "--asset-mode",
        choices=ASSET_MODES,
        default="full",
        help=(
            "Asset export policy. 'full' preserves run result artifacts; 'lite' "
            "keeps task/injection assets and trace JSON but omits per-run binary artifacts."
        ),
    )
    parser.add_argument(
        "--trace-detail-policy",
        choices=TRACE_DETAIL_POLICIES,
        default="selected",
        help=(
            "Trace payload policy. 'selected' exports only the resolved attempt "
            "for each result row; 'all-attempts' mirrors every retry attempt."
        ),
    )
    parser.add_argument(
        "--asset-out",
        default=None,
        help=(
            "Optional separate output directory for large static assets such as "
            "attempt detail JSON and injection resources. Use this for R2/S3-backed "
            "deployments where the GitHub Pages artifact should stay small."
        ),
    )
    parser.add_argument(
        "--asset-base-url",
        default=None,
        help=(
            "Public base URL corresponding to --asset-out. When set, static HTML "
            "loads attempts and injection assets from this URL."
        ),
    )
    args = parser.parse_args(argv)

    runs_root = Path(args.runs_root).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()

    summary = export(
        runs_root,
        out,
        resume=args.resume,
        asset_mode=args.asset_mode,
        trace_detail_policy=args.trace_detail_policy,
        asset_out=Path(args.asset_out).expanduser().resolve() if args.asset_out else None,
        asset_base_url=args.asset_base_url,
    )

    print(f"runs-root : {runs_root}")
    print(f"output    : {summary['out']}")
    print(
        f"exported  : {summary['rows']} attempt rows · "
        f"{summary['models']} models · {summary['backends']} harnesses"
    )
    print(f"asset mode  : {summary['asset_mode']}")
    print(f"trace policy: {summary['trace_detail_policy']}")
    print(f"asset out   : {summary['asset_out']}")
    if summary["asset_base_url"]:
        print(f"asset base  : {summary['asset_base_url']}")
    print(f"results.json : {summary['results_bytes']:,} bytes")
    print(f"tasks data   : {summary['tasks_bytes']:,} bytes")
    print(f"runs data    : {summary['runs_bytes']:,} bytes")
    print(f"assets copied: {summary['asset_count']:,} files · {summary['asset_bytes']:,} bytes")
    print(f"asset manifest: {summary['asset_manifest_bytes']:,} bytes")
    print(f"data bytes   : {summary['total_bytes']:,} bytes (JSON only; assets counted above)")
    if summary["rows"] == 0:
        print(
            "NOTE: 0 rows exported — runs-root has no terminal summary.json "
            "data. Run this on the host with a populated runs/ tree to get "
            "real leaderboard data.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
