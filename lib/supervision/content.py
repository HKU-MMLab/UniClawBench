"""Content marshalling for supervisor / user_simulator roles.

Merged from ``files.py`` + ``images.py`` + ``payloads.py`` in the
third-round refactor.  All three modules were answering the same
question — "how do we package task context, attempt artefacts, and
images into the JSON payload Codex sees?" — and the call graph
followed the obvious leaf-to-root chain:

* ``files`` (leaf, stdlib only) — low-level read/write/clamp/coerce
* ``images``  — depends on ``files`` — reference-image discovery,
  downscale-on-copy, OCR cache
* ``payloads`` — depends on ``files`` + ``images`` + ``transcripts``
  — visible / hidden payload assembly + Codex response parsing

Three sections live here, in dependency order:

* **Section 1 — File / text helpers** (was ``files.py``).
  Stdlib-only utilities: read_text, write_json, summarize_result_dir,
  clamp_score, sanitize_codex_context_text, etc.  Importable by every
  other supervision module without risk of cycles.

* **Section 2 — Image discovery, downscale, OCR cache** (was
  ``images.py``).  copy_supervisor_asset re-encodes oversized PNGs as
  JPEG to keep the Codex view_image base64 footprint within budget;
  collect_*_images walks reference / result trees;
  extract_image_ocr_text caches tesseract output under
  ``.runtime/ocr_cache/``.

* **Section 3 — Visible / hidden payload assembly + JSON parsing**
  (was ``payloads.py``).  build_visible_payload + build_hidden_payload
  produce the two JSON blobs the supervisor + user_simulator prompts
  embed; parse_first_json_object is the inverse — extract the best
  JSON object from a Codex response.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .common import SupervisorContext


ROOT = Path(__file__).resolve().parents[2]


# ─────────────────────────────────────────────────────────────────────
# Round 9 / A2 — supervision summary mode hyperparameter
# ─────────────────────────────────────────────────────────────────────
#
# The 2026-05-14 combined code review pointed out that
# ``build_visible_payload`` / ``build_hidden_payload`` produce a thick
# bundle of OCR blocks + result-file text previews + semantic
# transcript blocks + hidden eval_rule excerpts.  Supervisor / user
# simulator prompts say "summary is navigation only, open the original
# for evidence" — but with the whole summary always written, models
# treat the summary as ground truth and stop loading artefacts.
#
# This hyperparameter lets the operator dial summary depth.  Image
# downsampling is ALWAYS on regardless of mode (it's a token-budget
# control, not an evidence shortcut).
#
# Levels (ordered NOT strictly additive — each profile picks which
# auxiliary blocks to include):
#
#   off       file index + image downsampling ONLY.  No OCR, no
#             previews, no semantic blocks.  Forces the model to load
#             original artefacts for any non-trivial check.
#   wocr      off + OCR blocks (visible + reference image OCR).
#             Useful when the rubric depends on text-in-image and the
#             model otherwise wouldn't call view_image.
#   wpreview  off + result-file text previews (summarize_result_dir
#             text).  Useful when result/ contains many small text
#             files the model would skip reading.
#   wsummary  off + semantic_transcript_blocks (DEFAULT).  Recreates
#             pre-Round-9 behavior MINUS OCR + preview noise.  Most
#             runs only need the transcript trace to navigate to
#             evidence.
#   full      everything.  Pre-Round-9 default.  Use only when you
#             know the rubric does not depend on first-hand artefact
#             inspection.

SUMMARY_MODE_ENV = "CLAWBENCH_SUPERVISION_SUMMARY_MODE"
SUMMARY_MODES = ("off", "wocr", "wpreview", "wsummary", "full")
DEFAULT_SUMMARY_MODE = "wsummary"


def supervision_summary_mode() -> str:
    """Return the validated summary mode for the current process.

    Reads ``CLAWBENCH_SUPERVISION_SUMMARY_MODE`` from the environment.
    Falls back to ``wsummary`` (default) when unset; logs a warning and
    falls back to default when the value is unknown."""
    raw = (os.environ.get(SUMMARY_MODE_ENV) or "").strip().lower()
    if not raw:
        return DEFAULT_SUMMARY_MODE
    if raw not in SUMMARY_MODES:
        import logging
        logging.getLogger(__name__).warning(
            "unknown %s=%r; falling back to %r (valid: %s)",
            SUMMARY_MODE_ENV, raw, DEFAULT_SUMMARY_MODE, SUMMARY_MODES,
        )
        return DEFAULT_SUMMARY_MODE
    return raw


def _summary_mode_includes_ocr(mode: str) -> bool:
    """OCR blocks visible to supervisor / user simulator?"""
    return mode in ("wocr", "full")


def _summary_mode_includes_preview(mode: str) -> bool:
    """Result-file text preview included in summarize_result_dir?"""
    return mode in ("wpreview", "full")


def _summary_mode_includes_semantic(mode: str) -> bool:
    """``semantic_transcript_blocks`` / ``operation_trace_summary``
    included in visible payload?"""
    return mode in ("wsummary", "full")


def _summary_mode_includes_hidden_extras(mode: str) -> bool:
    """``primary_eval_rule`` preview text + ``text_reference_blocks``
    included in hidden payload?  Off otherwise (still surfaces the
    reference file list so the supervisor knows what to open)."""
    return mode == "full"


# ─────────────────────────────────────────────────────────────────────
# Section 1 — File / text helpers (was lib/supervision/files.py)
# ─────────────────────────────────────────────────────────────────────


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def file_kind(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return "image"
    if path.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".log", ".jsonl"}:
        return "text"
    return "binary"


def summarize_file(
    path: Path,
    *,
    base: Path,
    include_text_preview: bool = True,
) -> dict[str, Any]:
    """Single-file summary.

    ``include_text_preview=False`` drops the 5 KB ``preview`` blob for
    text files, leaving only the structural index (path/kind/bytes).
    Used by Round 9 / A2 summary-mode gating: ``off`` / ``wocr`` /
    ``wsummary`` produce a path-only catalogue, ``wpreview`` / ``full``
    keep the preview snippet.
    """
    payload: dict[str, Any] = {
        "path": str(path.relative_to(base)),
        "kind": file_kind(path),
        "bytes": path.stat().st_size,
    }
    if payload["kind"] == "text" and include_text_preview:
        payload["preview"] = read_text(path)[:5000]
    return payload


def summarize_result_dir(
    result_dir: Path,
    *,
    include_text_preview: bool = True,
) -> list[dict[str, Any]]:
    """Directory-level result summary.

    Always returns a catalogue (path/kind/bytes) for up to 80 files.
    ``include_text_preview=False`` (Round 9 / A2 ``off``/``wocr``/
    ``wsummary`` modes) omits the per-file ``preview`` snippet so the
    supervisor must open the file to read content instead of treating
    the summary as ground truth.
    """
    if not result_dir.exists():
        return []
    files = [path for path in sorted(result_dir.rglob("*")) if path.is_file()]
    return [
        summarize_file(path, base=result_dir, include_text_preview=include_text_preview)
        for path in files[:80]
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reset_dir(path: Path) -> Path:
    resolved = path.resolve()
    shutil.rmtree(resolved, ignore_errors=True)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def copy_file_into(src: Path, dest: Path) -> Path | None:
    if not src.exists() or not src.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


# DEPRECATED: single call site in ``lib/supervision/common.py``. Will be
# inlined into the caller in the next minor — see ``docs/deprecations.md``.
def copy_tree_into(src: Path, dest: Path) -> Path | None:
    if not src.exists() or not src.is_dir():
        return None
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def _trim_middle(text: str, max_chars: int) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    head_chars = max_chars // 2
    tail_chars = max_chars - head_chars
    omitted = max(0, len(value) - max_chars)
    return value[:head_chars] + f"\n... [truncated {omitted} chars] ...\n" + value[-tail_chars:]


def _split_text_list_candidate(value: str) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    lines = []
    for raw_line in text.split("\n"):
        line = re.sub(r"^\s*(?:[-*•]+|\d+[\.\)])\s*", "", raw_line).strip()
        if line:
            lines.append(line)
    if len(lines) >= 2:
        return lines
    return [text]


def coerce_text_list(value: Any, *, limit: int, item_max_chars: int = 800) -> list[str]:
    if limit <= 0:
        return []
    raw_items = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for raw_item in raw_items:
        if raw_item is None:
            continue
        if isinstance(raw_item, str):
            candidates = _split_text_list_candidate(raw_item)
        else:
            candidate = str(raw_item).strip()
            candidates = [candidate] if candidate else []
        for candidate in candidates:
            item = str(candidate).strip()
            if not item:
                continue
            item = item[:item_max_chars]
            if item not in result:
                result.append(item)
            if len(result) >= limit:
                return result
    return result


def sanitize_codex_context_text(text: str) -> str:
    value = str(text or "")
    # 1. Redact absolute paths so containerised paths don't leak.
    value = re.sub(r"/tmp_workspace/results/([^\s\"')]+)", r"[results/\1]", value)
    value = re.sub(r"/tmp_workspace/clawbench/([^\s\"')]+)", r"[clawbench/\1]", value)
    value = value.replace("/tmp_workspace/results", "[results]")
    value = value.replace("/tmp_workspace/clawbench", "[clawbench]")
    value = value.replace("/tmp_workspace", "[workspace]")
    value = value.replace(str(ROOT), "[repo]")
    # 2. Collapse long base64-looking runs (>=80 chars of [A-Za-z0-9+/=]).
    #    This catches image base64 / raw binary that leaked into a failed
    #    upstream response body (e.g. 5xx HTML pages, chunked-transfer
    #    remnants) without touching ordinary English / CJK error messages.
    value = re.sub(r"[A-Za-z0-9+/=]{80,}", "[binary-blob-elided]", value)
    # 3. Strip non-printable bytes while keeping ASCII printable, common
    #    CJK ranges (ideographs + radicals + symbols + punctuation +
    #    fullwidth forms) and whitespace we care about. This guards against
    #    control characters / raw binary slipping past #2.
    value = re.sub(
        r"[^\x20-\x7E"              # ASCII printable
        r"⺀-鿿"            # CJK radicals + ideographs (A + BMP)
        r"　-〿"            # CJK symbols and punctuation
        r"＀-￯"            # halfwidth / fullwidth forms
        r"\r\n\t]",
        "?",
        value,
    )
    return value


# ─────────────────────────────────────────────────────────────────────
# Section 2 — Image discovery / downscale / OCR (was images.py)
# ─────────────────────────────────────────────────────────────────────


# Supervisor workspace image budget. Codex's ``view_image`` returns the
# full file bytes as base64 inside the function_call_output — a 1 MB PNG
# turns into ~1.4 MB of base64 text which is then replayed in every
# subsequent turn's conversation history. With 4 reference images at
# ~500 KB-1 MB each, a single supervisor evaluation can accumulate
# >400K input tokens and blow past the 272K provider ceiling. Downscale
# anything larger than a reasonable viewport screenshot when we copy it
# into a role workspace.
_SUPERVISOR_IMAGE_MAX_SIDE_PX = int(
    os.environ.get("CLAWBENCH_SUPERVISOR_IMAGE_MAX_SIDE", "1200")
)
_SUPERVISOR_IMAGE_MAX_BYTES = int(
    os.environ.get("CLAWBENCH_SUPERVISOR_IMAGE_MAX_BYTES", "200000")
)
_SUPERVISOR_IMAGE_JPEG_QUALITY = int(
    os.environ.get("CLAWBENCH_SUPERVISOR_IMAGE_JPEG_QUALITY", "82")
)
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"}


def _downscale_image_via_convert(src: Path, dest: Path) -> bool:
    """Resize ``src`` to a supervisor-friendly JPEG using the host's
    ``convert`` (ImageMagick). Returns True on success; callers fall
    back to a plain copy otherwise. ``dest`` should already have a
    ``.jpg`` suffix when we want the re-encode, but this helper keeps
    whatever extension was passed and writes JPEG bytes regardless.

    ``src`` is never modified — ImageMagick reads it and writes new
    bytes to ``dest``. The defensive guard below refuses to run when
    src and dest resolve to the same path (which would corrupt the
    executor's canonical artifact).
    """
    try:
        if src.resolve() == dest.resolve():
            return False
    except Exception:
        pass
    try:
        cmd = [
            "convert",
            str(src),
            "-auto-orient",
            "-resize",
            f"{_SUPERVISOR_IMAGE_MAX_SIDE_PX}x{_SUPERVISOR_IMAGE_MAX_SIDE_PX}>",
            "-quality",
            str(_SUPERVISOR_IMAGE_JPEG_QUALITY),
            "-strip",
            f"jpeg:{dest}",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
    except FileNotFoundError:
        return False
    except Exception:
        return False
    if proc.returncode != 0:
        return False
    return dest.exists() and dest.stat().st_size > 0


def copy_supervisor_asset(src: Path, dest: Path) -> Path | None:
    """Variant of ``copy_file_into`` that downscales large images before
    placing them in a role (supervisor / user_simulator) workspace.

    Small files (< ``_SUPERVISOR_IMAGE_MAX_BYTES``) and non-image files
    pass through unchanged. Larger images are re-encoded as JPEG whose
    long side is capped at ``_SUPERVISOR_IMAGE_MAX_SIDE_PX``. The
    destination filename is rewritten to ``.jpg`` in that case so the
    supervisor / workspace_manifest sees the correct content type.
    Returns the final on-disk path written, or ``None`` on failure.

    **Source is read-only.** This function never modifies ``src``. The
    canonical executor artifact at ``attempt.result_dir`` (e.g.
    ``out_dir/result/foo.png``) is preserved bit-for-bit; this helper
    only writes to ``dest`` (or the suffix-swapped JPEG variant of
    ``dest``), which always lives under the supervisor's role workspace
    at ``out_dir/codex_sessions/<role>/workspace/``.
    """
    if not src.exists() or not src.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.resolve() == dest.resolve():
            return None
    except Exception:
        pass
    try:
        src_size = src.stat().st_size
    except OSError:
        src_size = 0
    if (
        src.suffix.lower() not in _IMAGE_SUFFIXES
        or src_size <= _SUPERVISOR_IMAGE_MAX_BYTES
    ):
        shutil.copy2(src, dest)
        return dest
    jpeg_dest = dest.with_suffix(".jpg") if dest.suffix.lower() != ".jpg" else dest
    if _downscale_image_via_convert(src, jpeg_dest):
        return jpeg_dest
    shutil.copy2(src, dest)
    return dest


def resolve_reference_path(context: SupervisorContext, raw: str) -> Path:
    return (context.task.injection_root / str(raw)).resolve()


def collect_reference_images(context: SupervisorContext) -> list[Path]:
    images: list[Path] = []
    seen: set[Path] = set()
    for raw in context.task.references:
        path = resolve_reference_path(context, raw)
        if path.exists() and path.is_file() and file_kind(path) == "image" and path not in seen:
            images.append(path)
            seen.add(path)
    return images


def collect_visible_images(context: SupervisorContext) -> list[Path]:
    images: list[Path] = []
    seen: set[Path] = set()
    candidates = [path for path in context.attempt.result_dir.rglob("*") if path.is_file() and file_kind(path) == "image"]
    candidates.sort(key=lambda path: path.stat().st_mtime_ns)
    for path in candidates[-20:]:
        if path in seen:
            continue
        images.append(path)
        seen.add(path)
    desktop = context.attempt.out_dir / "runtime_probe_desktop.png"
    if desktop.exists() and desktop not in seen:
        images.append(desktop)
    return images


def collect_reference_text_blocks(context: SupervisorContext) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for raw in context.task.references:
        path = resolve_reference_path(context, raw)
        if not path.exists() or not path.is_file() or file_kind(path) == "image":
            continue
        if path.name.lower() == "eval_rule.md":
            continue
        blocks.append({"path": raw, "content": _trim_middle(sanitize_codex_context_text(read_text(path)), 8000)})
    return blocks


def primary_eval_rule_block(context: SupervisorContext) -> dict[str, str]:
    for raw in context.task.references:
        path = resolve_reference_path(context, raw)
        if not path.exists() or not path.is_file() or file_kind(path) == "image":
            continue
        if path.name.lower() == "eval_rule.md":
            return {"path": raw, "content": _trim_middle(sanitize_codex_context_text(read_text(path)), 12000)}
    return {}


def image_ocr_cache_path(path: Path) -> Path:
    runtime_dir = ROOT / ".runtime" / "ocr_cache"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    cache_key = f"{path.resolve()}::{int(stat.st_mtime_ns)}::{stat.st_size}"
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return runtime_dir / f"{digest}.json"


def extract_image_ocr_text(path: Path, max_chars: int = 2400) -> str:
    if not path.exists() or not path.is_file():
        return ""
    cache_path = image_ocr_cache_path(path)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            text = str(cached.get("text") or "")
            return text[:max_chars]
        except Exception:
            pass
    languages = ["eng", "osd"]
    text = ""
    for language in languages:
        try:
            result = subprocess.run(
                ["tesseract", str(path), "stdout", "-l", language, "--psm", "6"],
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )
        except Exception:
            continue
        candidate = sanitize_codex_context_text((result.stdout or "").strip())
        if candidate:
            text = candidate
            break
    cache_payload = {"path": str(path), "text": text}
    cache_path.write_text(json.dumps(cache_payload, ensure_ascii=False), encoding="utf-8")
    return text[:max_chars]


def collect_image_ocr_blocks(paths: list[Path], *, base: Path | None = None) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for path in paths:
        try:
            relative = str(path.relative_to(base)) if base else path.name
        except Exception:
            relative = path.name
        text = extract_image_ocr_text(path)
        blocks.append(
            {
                "path": relative,
                "ocr_text": text,
            }
        )
    blocks = [item for item in blocks if str(item.get("ocr_text") or "").strip()]
    return blocks


# ─────────────────────────────────────────────────────────────────────
# Section 3 — Payload assembly + JSON response parsing (was payloads.py)
# ─────────────────────────────────────────────────────────────────────


# NOTE on import order: ``transcripts.py`` (in the same package) needs
# the file/text helpers in Section 1 above.  To avoid a circular import
# (transcripts → content → transcripts), the few transcript-side
# helpers used in Section 3 are imported lazily inside the functions
# that need them, NOT at module top.  This mirrors the lazy pattern
# ``codex.py`` already uses for its content-side imports.


def prompt_context_text(path: Path, *, max_chars: int = 8000) -> str:
    return _trim_middle(sanitize_codex_context_text(read_text(path)), max_chars)


def _strip_edict_routing_note(text: str) -> str:
    """Remove EDICT routing note block so supervision roles see only the public task."""
    start_marker = "EDICT routing note:"
    idx = text.find(start_marker)
    if idx < 0:
        return text
    end_marker = "皇上原话："
    end_idx = text.find(end_marker, idx)
    if end_idx >= 0:
        end_idx += len(end_marker)
    else:
        end_idx = idx
        for line in text[idx:].splitlines(True):
            end_idx += len(line)
            if not line.strip():
                break
    return (text[:idx].rstrip() + "\n\n" + text[end_idx:].lstrip()).strip()


def build_visible_payload(context: SupervisorContext) -> dict[str, Any]:
    # Lazy import to break the content ↔ transcripts circular at load time
    # (transcripts.py needs the file/text helpers in Section 1).
    from .transcripts import (
        build_multi_agent_visible_payload,
        operation_trace_summary,
        runtime_probe_payload,
        semantic_transcript_blocks,
    )

    mode = supervision_summary_mode()
    # ``result_files`` always present as a directory index (path, kind,
    # bytes, mtime, hash).  Whether each file carries a text-preview
    # snippet is controlled by ``_summary_mode_includes_preview``;
    # ``summarize_result_dir`` does the snippet trimming honestly when
    # asked to drop previews.
    payload: dict[str, Any] = {
        "task": context.task.public_task,
        "agent_prompt_text": _strip_edict_routing_note(prompt_context_text(context.attempt.prompt_file, max_chars=8000)),
        "result_files": summarize_result_dir(
            context.attempt.result_dir,
            include_text_preview=_summary_mode_includes_preview(mode),
        ),
        "runtime_probe": runtime_probe_payload(context.attempt.runtime_probe_file),
        "supervision_summary_mode": mode,
    }
    if _summary_mode_includes_semantic(mode):
        payload["semantic_transcript_blocks"] = semantic_transcript_blocks(
            context.attempt.transcript_file, max_chars=12000,
        )
        payload["operation_trace_summary"] = operation_trace_summary(
            context.attempt.tool_usage_file, max_chars=4000,
        )
    if _summary_mode_includes_ocr(mode):
        visible_images = collect_visible_images(context)
        payload["visible_image_ocr_blocks"] = collect_image_ocr_blocks(
            visible_images, base=context.attempt.out_dir,
        )
    multi_agent = build_multi_agent_visible_payload(context)
    if multi_agent:
        payload["multi_agent"] = multi_agent
    return payload


def build_hidden_payload(context: SupervisorContext) -> dict[str, Any]:
    """Hidden references the supervisor sees.

    ``reference_files`` (the path list) is always emitted — the
    supervisor must know what to open even when summary mode is ``off``.
    The eval_rule preview, text-reference snippets, and reference-image
    OCR blocks only appear under ``full`` mode (see
    ``_summary_mode_includes_hidden_extras``).  In other modes, the
    supervisor must explicitly read ``references/eval_rule.md`` from
    disk — which encourages first-hand rubric consultation rather than
    summarised reasoning."""
    mode = supervision_summary_mode()
    payload: dict[str, Any] = {
        "reference_files": list(context.task.references),
        "supervision_summary_mode": mode,
    }
    if _summary_mode_includes_hidden_extras(mode):
        payload["primary_eval_rule"] = primary_eval_rule_block(context)
        payload["text_reference_blocks"] = collect_reference_text_blocks(context)
    if _summary_mode_includes_ocr(mode):
        reference_images = collect_reference_images(context)
        payload["reference_image_ocr_blocks"] = collect_image_ocr_blocks(
            reference_images, base=context.task.injection_root,
        )
    return payload


def redacted_supervision_context(context: SupervisorContext) -> dict[str, Any]:
    visible_payload = build_visible_payload(context)
    return {
        "task": {
            "task_id": context.task.task_id,
            "task_file": str(context.task.task_file),
            "run_root": str(context.task.run_root),
            "max_user_followups": context.task.max_user_followups,
            "user_simulator": context.task.user_simulator.to_dict(),
            "supervisor": context.task.supervisor.to_dict(),
        },
        "attempt": context.attempt.to_dict(),
        "public_task": context.task.public_task,
        "result_files": summarize_result_dir(context.attempt.result_dir),
        "references": list(context.task.references),
        "semantic_transcript_blocks": visible_payload.get("semantic_transcript_blocks"),
        "operation_trace_summary": visible_payload.get("operation_trace_summary"),
        "multi_agent": visible_payload.get("multi_agent") or {},
    }


def parse_first_json_object(text: str) -> dict[str, Any]:
    value = (text or "").strip()
    if not value:
        raise ValueError("empty codex response")
    candidates: list[dict[str, Any]] = []

    def record(candidate_text: str) -> None:
        candidate_text = (candidate_text or "").strip()
        if not candidate_text:
            return
        try:
            parsed = json.loads(candidate_text)
        except json.JSONDecodeError:
            return
        if isinstance(parsed, dict):
            candidates.append(parsed)

    record(value)

    fence_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
    for match in fence_pattern.finditer(value):
        record(match.group(1))

    decoder = json.JSONDecoder()
    for index, char in enumerate(value):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            candidates.append(parsed)

    if not candidates:
        raise ValueError("no JSON object found in codex response")

    def score_candidate(payload: dict[str, Any]) -> tuple[int, int]:
        keys = set(payload.keys())
        score = 0
        strong_markers = {
            "verdict": 600,
            "candidate_feedback": 600,
            "public_feedback_points": 250,
            "requested_action": 250,
            "guidance_tags": 200,
            "missing_artifacts": 200,
            "confidence": 180,
            "attempt_state": 150,
        }
        for key, weight in strong_markers.items():
            if key in keys:
                score += weight
        if "mode" in keys and ("candidate_feedback" in keys or "public_feedback_points" in keys):
            score += 150
        if "tone" in keys and ("candidate_feedback" in keys or "public_feedback_points" in keys):
            score += 100
        if not any(key in keys for key in ("verdict", "candidate_feedback", "missing_artifacts", "public_feedback_points")):
            score -= 1000
        score += min(len(keys), 20)
        return score, len(keys)

    candidates.sort(key=score_candidate)
    return candidates[-1]
