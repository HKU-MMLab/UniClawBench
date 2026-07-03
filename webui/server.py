#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from webui import aggregate

from lib.runtime_metrics import attempt_runtime_ms
from lib.util.model_naming import display_model_name, include_in_public_webui


ROOT = Path(__file__).resolve().parents[1]
# CLAWBENCH_RUNS_DIR lets the orchestrator point the webui at a runs tree
# that lives outside the repo (for example, a controller data volume).
# Falls back to <repo>/runs/ for the in-tree single-host development case.
RUNS = Path(os.environ.get("CLAWBENCH_RUNS_DIR", str(ROOT / "runs"))).expanduser()
TASKS = ROOT / "tasks"
INJECTION = ROOT / "injection"
ASSETS = ROOT / "assets"
STATIC = ROOT / "webui" / "static"
OPENCLAW_LIVE_TRANSCRIPT_TARGETS = [
    "/root/.openclaw/agents/*/sessions/*.jsonl",
    "/root/.openclaw/agents/*/sessions/chat.jsonl",
    "/tmp/openclaw/chat.jsonl",
    "/tmp/openclaw/sessions/chat.jsonl",
]
NANOBOT_LIVE_TRANSCRIPT_TARGETS = [
    "/tmp_workspace/sessions/chat.jsonl",
    "/root/.nanobot/logs/nanobot.log",
    "/tmp_workspace/clawbench/logs/agent.log",
]
EDICT_AGENT_ORDER = [
    "taizi",
    "zhongshu",
    "menxia",
    "shangshu",
    "libu",
    "hubu",
    "bingbu",
    "xingbu",
    "gongbu",
    "libu_hr",
    "zaochao",
]
EDICT_AGENT_META = {
    "taizi": {"label": "太子", "emoji": "🤴", "role": "储君"},
    "zhongshu": {"label": "中书省", "emoji": "📜", "role": "规划"},
    "menxia": {"label": "门下省", "emoji": "🔍", "role": "审议"},
    "shangshu": {"label": "尚书省", "emoji": "📮", "role": "派发"},
    "libu": {"label": "礼部", "emoji": "📝", "role": "文档/UI"},
    "hubu": {"label": "户部", "emoji": "💰", "role": "数据"},
    "bingbu": {"label": "兵部", "emoji": "⚔️", "role": "工程"},
    "xingbu": {"label": "刑部", "emoji": "⚖️", "role": "测试/审计"},
    "gongbu": {"label": "工部", "emoji": "🔧", "role": "运维"},
    "libu_hr": {"label": "吏部", "emoji": "👔", "role": "人事/培训"},
    "zaochao": {"label": "钦天监", "emoji": "📰", "role": "朝报"},
}


def _display_model(raw: object) -> str:
    return display_model_name(str(raw)) if raw else ""


_PUBLIC_DROP_KEYS = {"config", "outDir", "settingRoot", "taskFile"}
_PUBLIC_MODEL_KEYS = {"model", "imageModel", "modelSlug"}
_PUBLIC_DEBUG_DROP_KEYS = {
    "desktopProbe",
    "logs",
    "prompt",
    "input_readme",
    "input_workspace",
    "response",
    "raw_response",
    "supervisionLog",
}
_PUBLIC_DEBUG_ARTIFACT_SUFFIXES = (
    "_prompt.txt",
    "_input_readme.md",
    "_input_workspace.json",
    "_response.txt",
)
_PUBLIC_DEBUG_ARTIFACT_NAMES = {
    "stdout.log",
    "stderr.log",
    "agent.log",
    "desktop_probe.log",
    "supervision.log",
    "window_grab_raw.json",
    "window_grab_raw.txt",
}
_PUBLIC_RUN_METADATA_NAMES = {
    "agent_sessions_manifest.json",
    "meta.json",
    "runtime_probe.json",
    "score.json",
    "summary.json",
    "supervision_context.json",
    "supervision_trace.jsonl",
    "timeline.json",
    "tool_usage.json",
    "transcript.jsonl",
    "usage.json",
}
_PUBLIC_MCP_ARTIFACT_SUFFIXES = {
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".mp4",
    ".pdf",
    ".png",
    ".svg",
    ".webm",
    ".webp",
}
_PUBLIC_DEBUG_ARTIFACT_NAME_FRAGMENTS = (
    "desktop_grab_raw",
    "raw_screenshot",
    "raw_window",
    "window_grab_raw",
)
_PUBLIC_RAW_ERROR_KEYS = {
    "rawError",
    "raw_error",
    "rawErrorPreview",
    "rawErrorHash",
    "raw_error_preview",
    "raw_error_hash",
}
_PUBLIC_INTERNAL_STRING_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"), "[secret-value]"),
    (re.compile(r"\b(?!missing_brave_api_key\b)[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*(?:_API_KEY|_TOKEN|_SECRET|_KEY)\b", re.IGNORECASE), "[secret-name]"),
    (re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[-_/][A-Za-z0-9]+){0,10}[-_/](?=(?:claude-|gpt-\d|gemini-\d|qwen\d|kimi-k\d|minimax-m\d))", re.IGNORECASE), ""),
    (re.compile(r"/Users/[^/\s\"']+/[^\s\"']*"), "[local-path]"),
    (re.compile(r"/Volumes/[^/\s\"']+/[^\s\"']*"), "[controller-path]"),
    (re.compile(r"/root/clawbench(?:_[A-Za-z0-9_.-]+)?/[^\s\"']*"), "[worker-path]"),
    (re.compile(r"/tmp_workspace/[^\s\"']*"), "[workspace-path]"),
    (re.compile(r"\b(?:localhost|127\.0\.0\.1):\d+\b"), "[local-endpoint]"),
    (re.compile(r"ws://\[[^\]]+\]:\d+"), "ws://[local-gateway]"),
    (re.compile(r"ws://[^\s\"']+:\d+"), "ws://[local-gateway]"),
    (re.compile(r"\bcodex\.local\.toml\b"), "local-config.toml"),
)
_PUBLIC_ROUTE_PATH_KEYS = {
    "relPath",
    "summaryPath",
    "selectedAttemptPath",
    "attemptPath",
}
_PUBLIC_WEBUI_URL_PREFIXES = (
    "/runs/",
    "/runs-public/",
    "/injection/",
    "/tasks/",
    "artifacts/",
    "assets/",
    "injection/",
    "tasks/",
    "static/",
)


def _public_error_payload(value: object) -> object:
    if not isinstance(value, dict):
        return {}
    kind = str(value.get("type") or "runtime_error")
    source = str(value.get("source") or value.get("rate_limit_source") or "")
    payload: dict[str, object] = {"type": sanitize_public_payload(kind)}
    if source:
        payload["source"] = sanitize_public_payload(source)
    if value.get("rate_limit") is not None:
        payload["rate_limit"] = bool(value.get("rate_limit"))
    if value.get("retries_attempted") is not None:
        payload["retries_attempted"] = value.get("retries_attempted")
    if value.get("timed_out_while_throttled") is not None:
        payload["timed_out_while_throttled"] = bool(value.get("timed_out_while_throttled"))
    payload["message"] = "Provider rate limit detected." if "rate_limit" in kind else "Runtime error detected."
    return payload


def _sanitize_public_string(value: str) -> str:
    out = value
    for pattern, replacement in _PUBLIC_INTERNAL_STRING_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def sanitize_public_payload(value: object) -> object:
    """Return a public WebUI payload with local/provider metadata removed.

    Trace payloads are intentionally rich enough to drive the dynamic and static
    UIs from the same data, but archived summaries/meta files contain controller
    paths and provider/key-pool identifiers.  Keep navigation/artifact fields
    such as ``relPath`` and ``attemptPath`` intact, while normalizing model
    labels and dropping local config/path metadata that is not needed by the UI.
    """

    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            if key in _PUBLIC_DROP_KEYS or key in _PUBLIC_DEBUG_DROP_KEYS or key == "provider" or key in _PUBLIC_RAW_ERROR_KEYS:
                continue
            if key in _PUBLIC_ROUTE_PATH_KEYS and isinstance(item, str):
                out[key] = item
                continue
            if key == "url" and isinstance(item, str) and item.startswith(_PUBLIC_WEBUI_URL_PREFIXES):
                out[key] = item
                continue
            if key in {"rateLimit", "infraError"}:
                out[key] = _public_error_payload(item)
                continue
            if key in _PUBLIC_MODEL_KEYS and item is not None:
                out[key] = _display_model(item)
                continue
            out[key] = sanitize_public_payload(item)
        return out
    if isinstance(value, list):
        return [sanitize_public_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_public_string(value)
    return value


def _normalized_rel_parts(rel: str | Path) -> list[str]:
    return [part for part in Path(str(rel or "")).parts if part not in {"", "."}]


def _is_privacy_rel_parts(parts: list[str]) -> bool:
    if ".privacy" in parts:
        return True
    normalized = "/".join(parts)
    return "/privacy/" in f"/{normalized}/" or normalized.endswith("/env.env")


def _is_public_debug_artifact_name(name: str) -> bool:
    lowered = name.lower()
    if lowered in _PUBLIC_DEBUG_ARTIFACT_NAMES:
        return True
    if any(fragment in lowered for fragment in _PUBLIC_DEBUG_ARTIFACT_NAME_FRAGMENTS):
        return True
    return any(lowered.endswith(suffix) for suffix in _PUBLIC_DEBUG_ARTIFACT_SUFFIXES)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _first_symlink_anchor(path: Path, root: Path) -> Path | None:
    """Return the trusted directory symlink target anchoring ``path``.

    Production dashboards sometimes expose a filtered ``runs/`` tree where a
    controller-owned prefix such as ``runs/openclaw/<model>`` is a symlink to a
    larger historical runs directory.  The symlink prefix is trusted; files
    below it are not automatically trusted, so callers still check that the
    final resolved path remains inside this anchor.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None

    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                target = cursor.resolve(strict=True)
                return target if target.is_dir() else None
        except OSError:
            return None
    return None


def _path_allowed_under_root(path: Path, root: Path) -> bool:
    try:
        root_resolved = root.resolve()
        path_resolved = path.resolve(strict=False)
    except OSError:
        return False

    if _is_relative_to(path_resolved, root_resolved):
        return True

    try:
        is_runs_root = root_resolved == RUNS.resolve()
    except OSError:
        is_runs_root = False
    if not is_runs_root:
        return False

    anchor = _first_symlink_anchor(path, root)
    if anchor is None:
        return False
    return _is_relative_to(path_resolved, anchor)


def _safe_runs_file(path: Path) -> bool:
    """Return True for regular run files that do not resolve outside runs."""
    try:
        return path.is_file() and _path_allowed_under_root(path, RUNS)
    except OSError:
        return False


def safe_rel_path(raw: str, root: Path | None = None) -> Path | None:
    """Return a lexical path under ``root`` while rejecting traversal escapes.

    ``root`` defaults to the current ``RUNS`` value at call time.  This matters
    for static export/tests, which may retarget ``webui.server.RUNS`` after the
    module has already been imported.  Static handlers pass ``TASKS``,
    ``INJECTION``, or ``STATIC`` explicitly.
    """
    root = root or RUNS
    rel = Path(raw)
    if rel.is_absolute() or any(part == ".." for part in rel.parts):
        return None
    path = root / rel
    if not _path_allowed_under_root(path, root):
        return None
    return path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


TEXT_RESULT_SUFFIXES = {
    ".csv",
    ".css",
    ".env",
    ".htm",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".log",
    ".markdown",
    ".md",
    ".ndjson",
    ".py",
    ".toml",
    ".ts",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
BULK_ARTIFACT_DIR_NAMES = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "env",
    "node_modules",
    "site-packages",
    "venv",
}


def _is_bulk_artifact_part(part: str) -> bool:
    lowered = part.lower()
    return lowered in BULK_ARTIFACT_DIR_NAMES or lowered.startswith("venv_") or lowered.startswith(".venv_")


def _is_bulk_artifact_path(path: Path) -> bool:
    """Return True for dependency/cache trees that should not be WebUI results."""
    return any(_is_bulk_artifact_part(part) for part in path.parts)


def _is_public_run_artifact_rel(rel: str | Path) -> bool:
    """Return True when a run-local file is safe to expose as a public asset."""
    parts = _normalized_rel_parts(rel)
    if not parts or _is_privacy_rel_parts(parts):
        return False
    path = Path(*parts)
    if _is_bulk_artifact_path(path):
        return False
    name = parts[-1]
    lowered = name.lower()
    if _is_public_debug_artifact_name(lowered):
        return False
    if "codex_sessions" in parts:
        # Raw Codex home/session trees can contain supervisor-only context and
        # privacy material. Public Trace uses sanitized ``agent_sessions/`` and
        # supervision JSON instead, so never expose this raw subtree.
        return False
    if "mcp_artifacts" in parts:
        return Path(lowered).suffix in _PUBLIC_MCP_ARTIFACT_SUFFIXES
    if "supervision" in parts:
        # The structured API exposes sanitized supervision trace data. Do not
        # serve raw supervisor/evaluator text or JSON, because historical
        # payloads may quote hidden references, controller paths, or provider
        # identifiers. Binary screenshots/videos remain eligible below.
        if Path(lowered).suffix in {".json", ".jsonl", ".md", ".txt", ".log"}:
            return False
    if "result" not in parts and "inline_images" not in parts and lowered in _PUBLIC_RUN_METADATA_NAMES:
        return False
    return True


def _iter_result_artifact_files(result_dir: Path):
    """Yield result files while pruning dependency/cache directories early."""
    for dirpath, dirnames, filenames in os.walk(result_dir):
        dirnames[:] = sorted(name for name in dirnames if not _is_bulk_artifact_part(name))
        base = Path(dirpath)
        for filename in sorted(filenames):
            path = base / filename
            rel = path.relative_to(result_dir)
            if _is_bulk_artifact_path(rel) or _is_public_debug_artifact_name(path.name):
                continue
            yield path, rel


def run_url(path: Path) -> str:
    rel = path.relative_to(RUNS)
    return "/runs/" + "/".join(quote(part) for part in rel.parts)


def _collect_inline_images(attempt_dir: Path) -> list[dict]:
    """Enumerate ``<attempt>/inline_images/*`` files as {path, url}.

    These are transient screenshots extracted from base64 image blocks
    by ``lib.runner._persist_inline_image``. Used by the flow timeline
    renderer as a whitelist alongside ``result/``.
    """
    out: list[dict] = []
    inline_dir = attempt_dir / "inline_images"
    if not inline_dir.exists():
        return out
    for path in sorted(inline_dir.rglob("*")):
        if _safe_runs_file(path) and _is_public_run_artifact_rel(path.relative_to(attempt_dir)):
            out.append(
                {
                    "path": f"inline_images/{path.relative_to(inline_dir)}",
                    "url": run_url(path),
                }
            )
    return out


def _collect_mcp_artifacts(attempt_dir: Path) -> list[dict]:
    """Enumerate ``<attempt>/mcp_artifacts/**/*`` files as {path, url}.

    These are MCP tool-side-effect files (e.g. playwright-mcp's
    auto-saved screenshots, DOM snapshots, console logs) mirrored out of
    ``/tmp_workspace/.mcp_artifacts/`` inside the container. Kept
    deliberately outside ``result/`` so the supervisor / user_simulator
    workspace does NOT see them as ``available_images`` — which caused
    Codex to view_image dozens of auto screenshots and blow its context
    limit. The WebUI uses this list as an extra whitelist alongside
    ``resultFiles`` and ``inlineImages`` when rendering Execution Flow
    image thumbnails.
    """
    out: list[dict] = []
    artifacts_dir = attempt_dir / "mcp_artifacts"
    if not artifacts_dir.exists():
        return out
    for path in sorted(artifacts_dir.rglob("*")):
        rel = path.relative_to(attempt_dir)
        if _safe_runs_file(path) and _is_public_run_artifact_rel(rel):
            out.append(
                {
                    "path": f"mcp_artifacts/{path.relative_to(artifacts_dir)}",
                    "url": run_url(path),
                }
            )
    return out


def infer_backend(meta: dict) -> str:
    explicit = str(meta.get("backend") or "").strip().lower()
    if explicit:
        return explicit
    image = str(meta.get("image") or "").lower()
    if "nanobot" in image:
        return "nanobot"
    if "edict" in image:
        return "openclaw_edict"
    if "openclaw" in image:
        return "openclaw"
    return "unknown"


def parse_jsonl(path: Path) -> list[dict]:
    return parse_jsonl_text(read_text(path))


def parse_jsonl_text(text: str) -> list[dict]:
    items: list[dict] = []
    if not text:
        return items
    for line in str(text).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if items and not any(isinstance(item, dict) and isinstance(item.get("type"), str) for item in items):
        if any(isinstance(item, dict) and (item.get("_type") == "metadata" or "role" in item) for item in items):
            return normalize_nanobot_session_items(items)
    return items


def _content_blocks_from_value(value):
    blocks = []
    if isinstance(value, str):
        text = value.strip()
        if text:
            blocks.append({"type": "text", "text": text})
        return blocks
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                item_type = str(item.get("type") or "").strip().lower()
                if item_type in {"text", "input_text"}:
                    text = str(item.get("text") or item.get("value") or "").strip()
                    if text:
                        blocks.append({"type": "text", "text": text})
                    continue
                if item_type in {"image", "image_url", "input_image"}:
                    meta = item.get("_meta") or {}
                    label = meta.get("path") or item.get("alt") or item.get("label") or item.get("name") or "image"
                    blocks.append({"type": "text", "text": f"[image: {label}]"})
                    continue
            text = str(item).strip()
            if text:
                blocks.append({"type": "text", "text": text})
        return blocks
    if value is None:
        return blocks
    text = str(value).strip()
    if text:
        blocks.append({"type": "text", "text": text})
    return blocks


def _tool_arguments_from_value(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text}
        return parsed if isinstance(parsed, dict) else {"_raw": text}
    return {"_raw": str(value)}


def normalize_nanobot_session_items(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("_type") == "metadata":
            continue
        role = str(item.get("role") or "").strip()
        timestamp = str(item.get("timestamp") or "").strip()
        content = _content_blocks_from_value(item.get("content"))
        if role == "assistant":
            for call_index, raw_call in enumerate(item.get("tool_calls") or []):
                if not isinstance(raw_call, dict):
                    continue
                function = raw_call.get("function") if isinstance(raw_call.get("function"), dict) else {}
                name = str(raw_call.get("name") or function.get("name") or "").strip()
                if not name:
                    continue
                content.append(
                    {
                        "type": "toolCall",
                        "id": str(raw_call.get("id") or f"nanobot-call-{index:06d}-{call_index:02d}"),
                        "name": name,
                        "arguments": _tool_arguments_from_value(raw_call.get("arguments", function.get("arguments"))),
                    }
                )
            if not content:
                continue
            normalized.append(
                {
                    "type": "message",
                    "id": f"nanobot-{index:06d}",
                    "timestamp": timestamp,
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "timestamp": timestamp,
                    },
                }
            )
            continue
        if role == "user":
            if not content:
                continue
            normalized.append(
                {
                    "type": "message",
                    "id": f"nanobot-{index:06d}",
                    "timestamp": timestamp,
                    "message": {
                        "role": "user",
                        "content": content,
                        "timestamp": timestamp,
                    },
                }
            )
            continue
        if role == "tool":
            if not content:
                continue
            normalized.append(
                {
                    "type": "message",
                    "id": f"nanobot-{index:06d}",
                    "timestamp": timestamp,
                    "message": {
                        "role": "toolResult",
                        "toolCallId": str(item.get("tool_call_id") or ""),
                        "toolName": str(item.get("name") or ""),
                        "content": content,
                        "timestamp": timestamp,
                    },
                }
            )
    return normalized


def parse_plain_transcript(path: Path) -> list[dict]:
    return parse_plain_transcript_text(read_text(path))


def parse_plain_transcript_text(text: str) -> list[dict]:
    if not text:
        return []
    events: list[dict] = []
    blocks: list[str] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("🐈 nanobot"):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        if line.startswith("Using config:") or line.startswith("Created "):
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    for block in blocks:
        if not block:
            continue
        events.append({"type": "plain_message", "role": "assistant", "text": block})
    return events


def parse_attempt_transcript(path: Path, agent_log: Path | None = None, live_text: str = "") -> list[dict]:
    payload = parse_jsonl(path)
    if payload:
        return payload
    payload = parse_plain_transcript(path)
    if payload:
        return payload
    payload = parse_jsonl_text(live_text)
    if payload:
        return payload
    payload = parse_plain_transcript_text(live_text)
    if payload:
        return payload
    if agent_log:
        return parse_plain_transcript(agent_log)
    return []


def agent_sort_key(agent_id: str) -> tuple[int, str]:
    try:
        return (EDICT_AGENT_ORDER.index(agent_id), agent_id)
    except ValueError:
        return (len(EDICT_AGENT_ORDER), agent_id)


def agent_display_payload(agent_id: str) -> dict:
    meta = dict(EDICT_AGENT_META.get(agent_id) or {})
    meta.setdefault("label", agent_id or "agent")
    meta.setdefault("emoji", "🧩")
    meta.setdefault("role", "")
    meta["id"] = agent_id
    return meta


def agent_sessions_payload(attempt_dir: Path) -> list[dict]:
    root = attempt_dir / "agent_sessions"
    if not root.exists():
        return []
    payloads: list[dict] = []
    for agent_dir in sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: agent_sort_key(path.name)):
        transcript_path = agent_dir / "transcript.jsonl"
        transcript = parse_attempt_transcript(transcript_path)
        tool_usage = read_json(agent_dir / "tool_usage.json")
        display = agent_display_payload(agent_dir.name)
        payloads.append(
            {
                **display,
                "transcript": transcript,
                "toolUsage": tool_usage,
                "eventCount": len(transcript),
                "toolCallCount": len((tool_usage.get("tool_calls") or [])) if isinstance(tool_usage, dict) else 0,
            }
        )
    return payloads


def _docker_available() -> bool:
    """Cheap one-shot check — does this host have a docker CLI?

    A controller host may serve the WebUI without a local docker daemon
    because containers live on worker hosts.  Without this guard, every
    ``/api/attempt`` request raises FileNotFoundError on the docker
    subprocess and the connection just hangs.
    """
    return shutil.which("docker") is not None


def docker_exec_text(container: str, script: str) -> str:
    if not _docker_available():
        return ""
    result = subprocess.run(
        ["docker", "exec", container, "sh", "-lc", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def live_transcript_text(container: str, backend: str) -> str:
    targets = NANOBOT_LIVE_TRANSCRIPT_TARGETS if backend == "nanobot" else OPENCLAW_LIVE_TRANSCRIPT_TARGETS
    lines = ["set -e"]
    for target in targets:
        lines.extend(
            [
                f"for f in {target}; do",
                "  if [ -f \"$f\" ]; then",
                "    tail -n 2000 \"$f\"",
                "    exit 0",
                "  fi",
                "done",
            ]
        )
    lines.append("exit 0")
    script = "\n".join(lines) + "\n"
    return docker_exec_text(container, script)


def live_attempt_context(task_dir: Path, backend: str) -> dict:
    """Return live-transcript info if a docker container is currently running
    this attempt on the same host as the webui.

    The "live tail" feature is only meaningful when the WebUI shares a
    docker daemon with the in-flight container.  In distributed orchestra
    deployments, the controller often has no docker daemon; bail early so
    we never invoke docker subprocesses there.
    """
    if not _docker_available():
        return {}
    session_meta = read_json(task_dir / "session_meta.json")
    primary = ((session_meta.get("sessions") or {}).get("primary") or {})
    container = str(primary.get("containerName") or "").strip()
    if not container:
        prefix = f"clawbench-{task_dir.name}-session-"
        ps = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
        if ps.returncode == 0:
            for line in ps.stdout.splitlines():
                name = line.strip()
                if name.startswith(prefix):
                    container = name
                    break
    if not container:
        return {}
    inspect = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container], capture_output=True, text=True)
    if inspect.returncode != 0 or inspect.stdout.strip().lower() != "true":
        return {}
    payload = {
        "container": container,
        "transcript": live_transcript_text(container, backend),
    }
    return sanitize_public_payload(payload)


def _build_recording_payload(rec: Path, attempt_dir: Path) -> dict | None:
    """Shape a recording.mp4 into the JSON payload the WebUI expects."""
    try:
        if not _safe_runs_file(rec) or rec.stat().st_size == 0:
            return None
    except OSError:
        return None
    try:
        rel_url = run_url(rec)
    except ValueError:
        return None
    # Poster image lives at the attempt root (desktop screenshot), shared by
    # every cycle recording.
    poster = attempt_dir / "runtime_probe_desktop.png"
    poster_url: str | None = None
    if _safe_runs_file(poster):
        try:
            poster_url = run_url(poster)
        except ValueError:
            poster_url = None
    return {
        "url": rel_url,
        "poster": poster_url,
        "sizeBytes": rec.stat().st_size,
        "speedup": 16,
    }


def recording_info(attempt_dir: Path) -> dict | None:
    """Attempt-level recording — kept for back-compat with older runs that
    recorded the whole attempt into one MP4 at the attempt root."""
    return _build_recording_payload(attempt_dir / "recording.mp4", attempt_dir)


def recordings_by_cycle(attempt_dir: Path) -> dict[int, dict]:
    """Per-cycle recordings live at supervision/cycle_NN/recording.mp4.
    Return a {cycle_index: payload} map suitable for the WebUI timeline."""
    supervision_dir = attempt_dir / "supervision"
    if not supervision_dir.exists() or not supervision_dir.is_dir():
        return {}
    by_cycle: dict[int, dict] = {}
    for cycle_dir in sorted(supervision_dir.iterdir()):
        if not cycle_dir.is_dir():
            continue
        name = cycle_dir.name
        if not name.startswith("cycle_"):
            continue
        try:
            idx = int(name.split("_", 1)[1])
        except (ValueError, IndexError):
            continue
        payload = _build_recording_payload(cycle_dir / "recording.mp4", attempt_dir)
        if payload is not None:
            by_cycle[idx] = payload
    return by_cycle


def usage_payload(attempt_dir: Path) -> dict:
    usage_file = attempt_dir / "usage.json"
    if usage_file.exists():
        payload = read_json(usage_file)
        if payload:
            payload.setdefault("available", True)
            return payload

    ledger_file = attempt_dir / "usage_ledger.jsonl"
    if ledger_file.exists():
        calls = parse_jsonl(ledger_file)
        summary: dict[str, dict] = {}
        executor_by_turn: dict[int, dict] = {}
        for call in calls:
            category = str(call.get("category") or "agent")
            bucket = summary.setdefault(
                category,
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost": 0.0, "call_count": 0},
            )
            bucket["prompt_tokens"] += int(call.get("prompt_tokens") or 0)
            bucket["completion_tokens"] += int(call.get("completion_tokens") or 0)
            bucket["total_tokens"] += int(call.get("total_tokens") or 0)
            bucket["estimated_cost"] += float(call.get("estimated_cost") or 0)
            bucket["call_count"] += 1
            if category == "executor":
                turn_raw = call.get("turn")
                try:
                    turn_key = int(turn_raw)
                except (TypeError, ValueError):
                    continue
                turn_bucket = executor_by_turn.setdefault(
                    turn_key,
                    {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost": 0.0, "call_count": 0},
                )
                turn_bucket["prompt_tokens"] += int(call.get("prompt_tokens") or 0)
                turn_bucket["completion_tokens"] += int(call.get("completion_tokens") or 0)
                turn_bucket["total_tokens"] += int(call.get("total_tokens") or 0)
                turn_bucket["estimated_cost"] += float(call.get("estimated_cost") or 0)
                turn_bucket["call_count"] += 1
        return {
            "summary": summary,
            "calls": calls,
            "available": True,
            "executorByTurn": executor_by_turn,
        }

    transcript = attempt_dir / "transcript.jsonl"
    agent_summary = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost": None, "call_count": 0}
    for item in parse_jsonl(transcript):
        message = item.get("message") or {}
        usage = message.get("usage") or {}
        total = usage.get("totalTokens")
        if not isinstance(total, (int, float)) or not total:
            continue
        agent_summary["total_tokens"] += int(total)
        agent_summary["prompt_tokens"] += int(usage.get("input") or 0)
        agent_summary["completion_tokens"] += int(usage.get("output") or 0)
        agent_summary["call_count"] += 1
    if agent_summary["call_count"] > 0:
        return {"summary": {"agent": agent_summary}, "calls": [], "available": True}
    return {
        "summary": {},
        "calls": [],
        "available": False,
        "reason": "provider-usage-unavailable",
    }


def usage_summary(attempt_dir: Path) -> dict:
    payload = usage_payload(attempt_dir)
    summary = payload.get("summary") or {}
    agent = summary.get("agent") or {}
    executor = summary.get("executor") or {}
    # Supervisor and user_simulator buckets come from the proxy-adapter
    # ledger (``responses_via_chat`` events, time-window-sliced per
    # role). They are NOT surfaced alongside executor counts in the UI
    # pills — the top-line "Input Tokens / Output Tokens" pair must stay
    # executor-only per the ownership rule — but we expose them under
    # their own keys so a future cost panel can render the split.
    supervisor_bucket = summary.get("supervisor") or {}
    user_simulator_bucket = summary.get("user_simulator") or {}
    source = payload.get("source") or {}
    supervision = enrich_supervision_trace(attempt_dir, supervision_trace(attempt_dir))
    executor_by_turn_raw = payload.get("executorByTurn") or {}
    executor_by_turn: dict[str, dict] = {}
    for key, value in executor_by_turn_raw.items():
        if not isinstance(value, dict):
            continue
        executor_by_turn[str(key)] = {
            "inputTokens": value.get("prompt_tokens"),
            "outputTokens": value.get("completion_tokens"),
            "totalTokens": value.get("total_tokens"),
            "callCount": value.get("call_count"),
        }
    return {
        "agentUsageAvailable": bool(payload.get("available")),
        "agentUsageReason": payload.get("reason"),
        "agentTotalTokens": agent.get("total_tokens"),
        "agentCost": agent.get("estimated_cost"),
        "agentCalls": agent.get("call_count"),
        "executorUsageAvailable": bool(payload.get("available")) and bool(executor),
        "executorInputTokens": executor.get("prompt_tokens"),
        "executorOutputTokens": executor.get("completion_tokens"),
        "executorTotalTokens": executor.get("total_tokens"),
        "executorCallCount": executor.get("call_count"),
        "executorUsageSource": str(source.get("executor") or "") if isinstance(source, dict) else "",
        "executorByTurn": executor_by_turn,
        "supervisorInputTokens": supervisor_bucket.get("prompt_tokens"),
        "supervisorOutputTokens": supervisor_bucket.get("completion_tokens"),
        "supervisorTotalTokens": supervisor_bucket.get("total_tokens"),
        "supervisorCallCount": supervisor_bucket.get("call_count"),
        "userSimulatorInputTokens": user_simulator_bucket.get("prompt_tokens"),
        "userSimulatorOutputTokens": user_simulator_bucket.get("completion_tokens"),
        "userSimulatorTotalTokens": user_simulator_bucket.get("total_tokens"),
        "userSimulatorCallCount": user_simulator_bucket.get("call_count"),
        "supervisionCalls": len(supervision),
        "latestSupervisorVerdict": (supervision[-1].get("verdict") if supervision else None),
    }


def checkpoint_counts(score: dict) -> dict:
    checkpoints = score.get("checkpoints") or []
    passed = sum(1 for item in checkpoints if item.get("passed"))
    failed = sum(1 for item in checkpoints if item.get("passed") is False)
    return {"passed": passed, "failed": failed, "total": len(checkpoints)}


def supervision_trace(attempt_dir: Path) -> list[dict]:
    return parse_jsonl(attempt_dir / "supervision_trace.jsonl")


def enrich_supervision_trace(attempt_dir: Path, trace: list[dict]) -> list[dict]:
    return trace


def _is_public_supervision_artifact(rel_path: str) -> bool:
    name = Path(rel_path).name
    lowered = name.lower()
    if _is_public_debug_artifact_name(lowered):
        return False
    if Path(lowered).suffix in {".json", ".jsonl", ".md", ".txt", ".log"}:
        return False
    return True


def supervision_artifacts(attempt_dir: Path) -> list[dict]:
    items: list[dict] = []
    supervision_dir = attempt_dir / "supervision"
    if supervision_dir.exists():
        for path in sorted(supervision_dir.rglob("*")):
            if not path.is_file():
                continue
            rel_path = str(path.relative_to(attempt_dir))
            if not _is_public_supervision_artifact(rel_path):
                continue
            item = {
                "path": rel_path,
                "text": read_text(path) if path.name in {"decision.json", "summary.json"} else "",
            }
            if _is_public_run_artifact_rel(rel_path):
                item["url"] = run_url(path)
            items.append(item)
    for path in sorted(attempt_dir.glob("continuation_*.md")):
        items.append(
            {
                "path": str(path.relative_to(attempt_dir)),
                "url": run_url(path),
                "text": read_text(path),
            }
        )
    return items


def parse_openclaw_key_nodes(path: Path) -> list[dict]:
    nodes: list[dict] = []
    if not path.exists():
        return nodes

    titles = {
        "listening on ws://": "Gateway Ready",
        "Browser control service ready": "Browser Ready",
        "openclaw browser started": "Browser Launched",
        "Task completed successfully": "Task Completed",
    }
    seen: set[tuple[str, str]] = set()
    for payload in parse_jsonl(path):
        text_parts: list[str] = []
        for key in ("0", "1", "2", "3"):
            value = payload.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                text_parts.append(value)
            else:
                text_parts.append(json.dumps(value, ensure_ascii=False))
        message = " ".join(part.strip() for part in text_parts if str(part).strip())
        if not message:
            continue
        for needle, title in titles.items():
            if needle in message:
                key = (title, message)
                if key in seen:
                    break
                seen.add(key)
                nodes.append(
                    {
                        "title": title,
                        "body": message,
                        "timestamp": payload.get("time") or payload.get("timestamp"),
                    }
                )
                break
    return nodes


def task_sort_key(task_id: str) -> tuple[int, str]:
    import re
    match = re.search(r"task_(\d+)", task_id or "")
    return (int(match.group(1)) if match else 10**9, task_id or "")


def task_attempt_dirs(task_dir: Path) -> list[Path]:
    items = [path for path in sorted(task_dir.iterdir()) if path.is_dir() and path.name.startswith("p")]
    return items


def attempt_number_from_dir(name: str) -> int:
    import re
    match = re.match(r"p(\d+)-", name or "")
    return int(match.group(1)) if match else 1


def synthetic_attempts(task_dir: Path) -> list[dict]:
    attempts: list[dict] = []
    dirs = task_attempt_dirs(task_dir)
    multi = len(dirs) > 1
    for item_dir in dirs:
        attempt_no = attempt_number_from_dir(item_dir.name)
        attempts.append(
            {
                "attempt": attempt_no,
                "promptKind": "primary",
                "stageType": "primary",
                "stageId": f"p{attempt_no}" if multi else "primary",
                "stageIndex": attempt_no,
                "outDir": str(item_dir),
            }
        )
    return attempts


def _local_attempt_dir(task_dir: Path, raw: str) -> Path:
    # summary.json may carry an absolute outDir written on a remote host
    # (the runner uses abs paths). Always resolve against the local task_dir
    # using just the p*-* basename so the WebUI stays host-agnostic.
    name = Path(raw or "").name
    return task_dir / name if name else Path("")


#: Cache filename produced by ``scripts/orchestra/refresh_summary``.
#: Kept in sync there — see ``refresh_summary.INDEX_FILENAME``.
_RUNS_INDEX_FILENAME = ".runs_index.json"
_RUNS_INDEX_SCHEMA_VERSION = 3
_SLIM_RUNS_CACHE_TTL_SECONDS = float(os.environ.get("CLAWBENCH_WEBUI_SLIM_CACHE_SECONDS", "120"))
_SLIM_RUNS_CACHE: tuple[float, list[dict]] | None = None
_PUBLIC_TRACE_MAP_CACHE: tuple[float, dict[str, str]] | None = None
_PUBLIC_TRACE_MAP_TTL_SECONDS = 30.0


def _summary_passed(payload: dict, final_status: str | None = None) -> bool:
    passed = payload.get("passed")
    if isinstance(passed, bool):
        return passed
    return str(final_status if final_status is not None else payload.get("finalStatus") or "").lower() == "pass"


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
    rel = str(rel_path or "").strip("/")
    if rel.startswith("r/run-"):
        return rel
    return f"r/{_stable_public_id('run', _trace_parent_run_path(rel))}"


def _public_trace_path(rel_path: str) -> str:
    rel = str(rel_path or "").strip("/")
    if rel.startswith("r/run-"):
        return rel
    parent = _trace_parent_run_path(rel)
    run_path = _public_run_path(parent)
    if rel == parent:
        return run_path
    return f"{run_path}/a/{_stable_public_id('attempt', rel)}"


def _public_trace_path_map() -> dict[str, str]:
    global _PUBLIC_TRACE_MAP_CACHE
    now = time.monotonic()
    if _PUBLIC_TRACE_MAP_CACHE and now - _PUBLIC_TRACE_MAP_CACHE[0] <= _PUBLIC_TRACE_MAP_TTL_SECONDS:
        return _PUBLIC_TRACE_MAP_CACHE[1]
    mapping: dict[str, str] = {}
    for task_dir in sorted(RUNS.glob("*/*/*/*")):
        if not task_dir.is_dir():
            continue
        try:
            rel = str(task_dir.relative_to(RUNS))
        except ValueError:
            continue
        mapping[_public_run_path(rel)] = rel
        for attempt_dir in task_dir.glob("p*-*"):
            if not attempt_dir.is_dir():
                continue
            try:
                attempt_rel = str(attempt_dir.relative_to(RUNS))
            except ValueError:
                continue
            mapping[_public_trace_path(attempt_rel)] = attempt_rel
    _PUBLIC_TRACE_MAP_CACHE = (now, mapping)
    return mapping


def _resolve_public_trace_path(rel_path: str) -> str:
    rel = str(rel_path or "").strip("/")
    if rel.startswith("r/run-"):
        return _public_trace_path_map().get(rel, "")
    return rel


def _resolve_public_artifact_rel(rel_path: str) -> str:
    rel = str(rel_path or "").strip("/")
    parts = [part for part in Path(rel).parts if part not in ("", ".", "..")]
    if len(parts) >= 2 and parts[0] == "r" and parts[1].startswith("run-"):
        public_run = "/".join(parts[:2])
        real_run = _public_trace_path_map().get(public_run, "")
        if not real_run:
            return ""
        return "/".join([real_run, *parts[2:]])
    return rel


def _public_artifact_url(url: str) -> str:
    text = str(url or "")
    prefix = "/runs/"
    if not text.startswith(prefix):
        return text
    rel = text.removeprefix(prefix)
    path_part, sep, suffix = rel.partition("?")
    path_part, hash_sep, hash_tail = path_part.partition("#")
    parent = _trace_parent_run_path(path_part)
    public = _public_run_path(parent)
    remainder = path_part[len(parent):].lstrip("/")
    public_rel = "/".join(part for part in [public, remainder] if part)
    return "/runs-public/" + public_rel + (hash_sep + hash_tail if hash_sep else "") + (sep + suffix if sep else "")


def _publicize_run_route_fields(row: dict) -> None:
    if row.get("summaryPath"):
        row["summaryPath"] = _public_run_path(str(row["summaryPath"]))
    if row.get("selectedAttemptPath"):
        row["selectedAttemptPath"] = _public_trace_path(str(row["selectedAttemptPath"]))


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


def _publicize_run_urls(value: object) -> object:
    if isinstance(value, dict):
        return {key: (_public_artifact_url(item) if key == "url" and isinstance(item, str) else _publicize_run_urls(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_publicize_run_urls(item) for item in value]
    if isinstance(value, str) and value.startswith("/runs/"):
        return _public_artifact_url(value)
    return value


def _load_runs_index(runs_root: Path) -> list[dict] | None:
    """Return cached rows from ``<runs_root>/.runs_index.json`` if usable.

    Three conditions must hold for the cache to be authoritative:
      1. The file exists and parses as JSON
      2. Its ``version`` matches what we know how to read
      3. Its mtime is at least as new as the newest task ``summary.json`` or
         per-attempt ``meta.json`` under ``runs_root``
    On any miss we return ``None`` so the caller falls back to the slow
    walk-the-tree path.  The slow path is the source of truth; the index
    is purely an accelerator.
    """
    index_path = runs_root / _RUNS_INDEX_FILENAME
    if not index_path.exists():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("version") != _RUNS_INDEX_SCHEMA_VERSION:
        return None
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None
    # Staleness check: if any task summary or attempt meta is newer than the
    # index, treat it as stale and fall back.  The index includes runtime and
    # continuation data derived from meta.json, so a late/fixed meta file must
    # invalidate the fast path even when summary.json itself did not change.
    try:
        index_mtime = index_path.stat().st_mtime
    except OSError:
        return None
    for pattern in ("*/*/*/*/summary.json", "*/*/*/*/p*-*/meta.json"):
        for dep in runs_root.glob(pattern):
            try:
                if dep.stat().st_mtime > index_mtime + 1:  # 1 s slack for clock skew
                    return None
            except OSError:
                continue
    return rows


def list_task_runs() -> list[dict]:
    # Fast path: serve from .runs_index.json when it exists and is fresh.
    cached = _load_runs_index(RUNS)
    if cached is not None:
        return public_task_runs(cached)
    rows: list[dict] = []
    seen_task_dirs: set[Path] = set()
    for summary_path in sorted(RUNS.glob("*/*/*/*/summary.json")):
        task_dir = summary_path.parent
        seen_task_dirs.add(task_dir.resolve())
        summary_payload = read_json(summary_path)
        attempts = summary_payload.get("attempts") or []
        if not attempts:
            continue
        resolved_attempt = summary_payload.get("resolvedAttempt")
        selected = attempts[-1]
        if isinstance(resolved_attempt, int):
            for item in attempts:
                if item.get("attempt") == resolved_attempt:
                    selected = item
                    break
        attempt_dir = _local_attempt_dir(task_dir, selected.get("outDir", ""))
        meta = read_json(attempt_dir / "meta.json") if attempt_dir.exists() else {}
        score = read_json(attempt_dir / "score.json") if attempt_dir.exists() else {}
        supervision = supervision_trace(attempt_dir) if attempt_dir.exists() else []
        total_runtime = 0
        total_continuations = 0
        for item in attempts:
            item_dir = _local_attempt_dir(task_dir, item.get("outDir", ""))
            item_meta = read_json(item_dir / "meta.json") if item_dir.exists() else {}
            total_continuations += len(item_meta.get("continuations") or [])
            # The summary's per-attempt ``runtimeMs`` is frequently null (the
            # worker often never wrote it), which made every run report
            # ``runtimeMs: 0`` and the UI's Runtime / Setting-Avg-Runtime read
            # 0s. Recover executor elapsed time the same way the Results
            # aggregate does (webui/aggregate.py:_extract_stats): summary
            # value -> attempt meta.runtimeMs. Do not use timeline wall-clock
            # spans here; they include supervisor/user-simulator overhead.
            total_runtime += attempt_runtime_ms(item, item_dir, item_meta, default=0) or 0
        final_status = summary_payload.get("finalStatus") or ("pass" if summary_payload.get("passed") else "fail")
        rows.append(
            {
                "category": task_dir.parent.name,
                "taskId": summary_payload.get("taskId") or task_dir.name,
                "backend": infer_backend(summary_payload),
                "model": _display_model(summary_payload.get("model") or meta.get("model") or summary_payload.get("modelSlug") or meta.get("modelSlug")),
                "modelSlug": _display_model(summary_payload.get("modelSlug") or meta.get("modelSlug")),
                "settingKey": "/".join(
                    part
                    for part in [
                        infer_backend(summary_payload),
                        _display_model(summary_payload.get("modelSlug") or meta.get("modelSlug")),
                    ]
                    if part
                ),
                "summaryPath": str(task_dir.relative_to(RUNS)),
                "selectedAttemptPath": str(attempt_dir.relative_to(RUNS)) if attempt_dir.exists() else "",
                "finalScore": summary_payload.get("finalScore"),
                "rawFinalScore": summary_payload.get("rawFinalScore"),
                "passed": _summary_passed(summary_payload, final_status),
                "finalStatus": final_status,
                "resolvedAttempt": summary_payload.get("resolvedAttempt"),
                "checkpointCounts": checkpoint_counts(score),
                "usage": usage_summary(attempt_dir) if attempt_dir.exists() else {},
                "continuationCount": total_continuations,
                "supervisionCycleCount": len(supervision),
                "supervisionVerdict": score.get("verdict"),
                "createdAt": task_dir.stat().st_mtime,
                "runtimeMs": total_runtime,
                "score": score,
            }
        )
    for task_dir in sorted(RUNS.glob("*/*/*/*")):
        if not task_dir.is_dir() or task_dir.resolve() in seen_task_dirs:
            continue
        attempts = synthetic_attempts(task_dir)
        if not attempts:
            continue
        selected = attempts[-1]
        attempt_dir = _local_attempt_dir(task_dir, selected.get("outDir", ""))
        meta = read_json(attempt_dir / "meta.json") if attempt_dir.exists() else {}
        score = read_json(attempt_dir / "score.json") if attempt_dir.exists() else {}
        supervision = supervision_trace(attempt_dir) if attempt_dir.exists() else []
        rows.append(
            {
                "category": task_dir.parent.name,
                "taskId": task_dir.name,
                "backend": task_dir.parents[2].name,
                "model": _display_model(meta.get("model") or task_dir.parents[1].name),
                "modelSlug": task_dir.parents[1].name,
                "settingKey": "/".join(part for part in [task_dir.parents[2].name, task_dir.parents[1].name] if part),
                "summaryPath": str(task_dir.relative_to(RUNS)),
                "selectedAttemptPath": str(attempt_dir.relative_to(RUNS)) if attempt_dir.exists() else "",
                "finalScore": score.get("final_completion_score", score.get("capped_score", score.get("overall_score"))),
                "rawFinalScore": score.get("overall_score"),
                "passed": False,
                "finalStatus": "running",
                "resolvedAttempt": None,
                "checkpointCounts": checkpoint_counts(score),
                "usage": usage_summary(attempt_dir) if attempt_dir.exists() else {},
                "continuationCount": len(meta.get("continuations") or []),
                "supervisionCycleCount": len(supervision),
                "supervisionVerdict": score.get("verdict"),
                "createdAt": task_dir.stat().st_mtime,
                "runtimeMs": int(meta.get("runtimeMs") or 0),
                "score": score,
            }
        )
    rows.sort(key=lambda item: (item.get("backend") or "", item.get("model") or "", *task_sort_key(item.get("taskId") or "")))
    return public_task_runs(rows)


def list_task_runs_slim(*, force: bool = False, public_paths: bool = False) -> list[dict]:
    """Return the Trace sidebar run list without loading heavy artifacts.

    The fallback ``list_task_runs`` path reads usage ledgers and supervision
    traces so Results/Trace detail views have everything they need.  The Trace
    sidebar only needs routing, status, score, continuation and runtime fields;
    selected attempt details are fetched lazily once a run card is opened.
    """

    global _SLIM_RUNS_CACHE
    now = time.monotonic()
    if public_paths and not force and _SLIM_RUNS_CACHE_TTL_SECONDS > 0 and _SLIM_RUNS_CACHE is not None:
        cached_at, cached_rows = _SLIM_RUNS_CACHE
        if now - cached_at <= _SLIM_RUNS_CACHE_TTL_SECONDS:
            return cached_rows

    cached = _load_runs_index(RUNS)
    if cached is not None:
        rows = slim_task_runs(cached, public_paths=public_paths)
        if public_paths and _SLIM_RUNS_CACHE_TTL_SECONDS > 0:
            _SLIM_RUNS_CACHE = (now, rows)
        return rows

    rows: list[dict] = []
    seen_task_dirs: set[Path] = set()
    for summary_path in sorted(RUNS.glob("*/*/*/*/summary.json")):
        task_dir = summary_path.parent
        seen_task_dirs.add(task_dir.resolve())
        summary_payload = read_json(summary_path)
        attempts = summary_payload.get("attempts") or []
        if not attempts:
            continue
        resolved_attempt = summary_payload.get("resolvedAttempt")
        selected = attempts[-1]
        if isinstance(resolved_attempt, int):
            for item in attempts:
                if item.get("attempt") == resolved_attempt:
                    selected = item
                    break
        attempt_dir = _local_attempt_dir(task_dir, selected.get("outDir", ""))
        meta = read_json(attempt_dir / "meta.json") if attempt_dir.exists() else {}
        score = read_json(attempt_dir / "score.json") if attempt_dir.exists() else {}
        total_runtime = 0
        total_continuations = 0
        for item in attempts:
            item_dir = _local_attempt_dir(task_dir, item.get("outDir", ""))
            item_meta = read_json(item_dir / "meta.json") if item_dir.exists() else {}
            total_continuations += len(item_meta.get("continuations") or [])
            total_runtime += attempt_runtime_ms(item, item_dir, item_meta, default=0) or 0
        backend = infer_backend(summary_payload)
        model_slug = summary_payload.get("modelSlug") or meta.get("modelSlug")
        final_status = summary_payload.get("finalStatus") or ("pass" if summary_payload.get("passed") else "fail")
        rows.append(
            {
                "category": task_dir.parent.name,
                "taskId": summary_payload.get("taskId") or task_dir.name,
                "backend": backend,
                "model": _display_model(summary_payload.get("model") or meta.get("model") or summary_payload.get("modelSlug") or meta.get("modelSlug")),
                "modelSlug": model_slug,
                "settingKey": "/".join(part for part in [backend, model_slug] if part),
                "summaryPath": str(task_dir.relative_to(RUNS)),
                "selectedAttemptPath": str(attempt_dir.relative_to(RUNS)) if attempt_dir.exists() else "",
                "finalScore": summary_payload.get("finalScore"),
                "rawFinalScore": summary_payload.get("rawFinalScore"),
                "passed": _summary_passed(summary_payload, final_status),
                "finalStatus": final_status,
                "resolvedAttempt": summary_payload.get("resolvedAttempt"),
                "checkpointCounts": checkpoint_counts(score),
                "continuationCount": total_continuations,
                "supervisionVerdict": score.get("verdict"),
                "createdAt": task_dir.stat().st_mtime,
                "runtimeMs": total_runtime,
            }
        )
    for task_dir in sorted(RUNS.glob("*/*/*/*")):
        if not task_dir.is_dir() or task_dir.resolve() in seen_task_dirs:
            continue
        attempts = synthetic_attempts(task_dir)
        if not attempts:
            continue
        selected = attempts[-1]
        attempt_dir = _local_attempt_dir(task_dir, selected.get("outDir", ""))
        meta = read_json(attempt_dir / "meta.json") if attempt_dir.exists() else {}
        score = read_json(attempt_dir / "score.json") if attempt_dir.exists() else {}
        rows.append(
            {
                "category": task_dir.parent.name,
                "taskId": task_dir.name,
                "backend": task_dir.parents[2].name,
                "model": _display_model(meta.get("model") or task_dir.parents[1].name),
                "modelSlug": task_dir.parents[1].name,
                "settingKey": "/".join(part for part in [task_dir.parents[2].name, task_dir.parents[1].name] if part),
                "summaryPath": str(task_dir.relative_to(RUNS)),
                "selectedAttemptPath": str(attempt_dir.relative_to(RUNS)) if attempt_dir.exists() else "",
                "finalScore": score.get("final_completion_score", score.get("capped_score", score.get("overall_score"))),
                "rawFinalScore": score.get("overall_score"),
                "passed": False,
                "finalStatus": "running",
                "resolvedAttempt": None,
                "checkpointCounts": checkpoint_counts(score),
                "continuationCount": len(meta.get("continuations") or []),
                "supervisionVerdict": score.get("verdict"),
                "createdAt": task_dir.stat().st_mtime,
                "runtimeMs": int(meta.get("runtimeMs") or 0),
            }
        )
    rows.sort(key=lambda item: (item.get("backend") or "", item.get("model") or "", *task_sort_key(item.get("taskId") or "")))
    rows = slim_task_runs(rows, public_paths=public_paths)
    if public_paths and _SLIM_RUNS_CACHE_TTL_SECONDS > 0:
        _SLIM_RUNS_CACHE = (time.monotonic(), rows)
    return rows


def slim_task_run(row: dict, *, public_paths: bool = False) -> dict:
    """Return the small run-list shape needed by the Trace sidebar.

    The full ``/api/runs`` payload intentionally carries score details and
    usage blocks for legacy consumers, but the Trace sidebar only needs filter
    fields plus a few setting metrics.  Serving this compact shape keeps the
    first Trace render usable on large result sets; the heavy attempt payload
    is still fetched lazily from ``/api/attempt`` when a card is selected.
    """

    keys = (
        "category",
        "taskId",
        "backend",
        "model",
        "modelSlug",
        "settingKey",
        "summaryPath",
        "selectedAttemptPath",
        "finalScore",
        "rawFinalScore",
        "passed",
        "finalStatus",
        "resolvedAttempt",
        "checkpointCounts",
        "continuationCount",
        "supervisionCycleCount",
        "supervisionVerdict",
        "createdAt",
        "runtimeMs",
    )
    out = {key: row.get(key) for key in keys if key in row}
    public_model = _display_model(out.get("model") or out.get("modelSlug"))
    if public_model:
        out["model"] = public_model
        out["modelSlug"] = public_model
        if out.get("backend"):
            out["settingKey"] = f"{out['backend']}::{public_model}"
    if public_paths:
        _publicize_run_route_fields(out)
    return out


def slim_task_runs(rows: list[dict] | None = None, *, public_paths: bool = False) -> list[dict]:
    public_rows = [
        slim_task_run(row, public_paths=public_paths)
        for row in (rows if rows is not None else list_task_runs())
        if include_in_public_webui(
            row.get("backend"),
            row.get("model") or row.get("modelSlug"),
            row.get("category"),
        )
    ]
    return _dedupe_public_run_rows(public_rows)


def public_task_run(row: dict, *, public_paths: bool = False) -> dict:
    """Return a run row with public-facing model identity fields.

    The full ``/api/runs`` response still keeps the high-level score fields that
    the UI needs (``finalScore``, ``rawFinalScore``, checkpoint counts, usage),
    but raw ``score.json`` payloads can carry local paths or provider metadata.
    Keep filesystem paths intact for trace lookup, normalize display identity
    fields, and drop the raw score dict from the public list payload.
    """

    out = dict(row)
    out.pop("score", None)
    public_model = _display_model(out.get("model") or out.get("modelSlug"))
    if public_model:
        out["model"] = public_model
        out["modelSlug"] = public_model
        if out.get("imageModel"):
            out["imageModel"] = _display_model(out.get("imageModel")) or public_model
        if out.get("backend"):
            out["settingKey"] = f"{out['backend']}::{public_model}"
    if public_paths:
        _publicize_run_route_fields(out)
    return out


def public_task_runs(rows: list[dict], *, public_paths: bool = False) -> list[dict]:
    public_rows = [
        public_task_run(row, public_paths=public_paths)
        for row in rows
        if include_in_public_webui(
            row.get("backend"),
            row.get("model") or row.get("modelSlug"),
            row.get("category"),
        )
    ]
    return _dedupe_public_run_rows(public_rows)


def _dedupe_public_run_rows(rows: list[dict]) -> list[dict]:
    """Collapse aliases after public model-name normalization.

    Internal provider/keypool labels can map to the same public model name. The
    public benchmark matrix should still show one run per
    (backend, model, category, task). Prefer terminal rows over in-flight rows,
    then the newest summary/attempt mtime.
    """

    terminal = {"pass", "fail", "budget_exhausted", "global_timeout"}

    def key(row: dict) -> tuple[str, str, str, str]:
        return (
            str(row.get("backend") or ""),
            str(row.get("model") or row.get("modelSlug") or ""),
            str(row.get("category") or ""),
            str(row.get("taskId") or ""),
        )

    def rank(row: dict) -> tuple[int, float, float]:
        status = str(row.get("finalStatus") or "").lower()
        return (
            1 if status in terminal else 0,
            float(row.get("createdAt") or 0),
            float(row.get("finalScore") or -1),
        )

    by_key: dict[tuple[str, str, str, str], dict] = {}
    for row in rows:
        row_key = key(row)
        current = by_key.get(row_key)
        if current is None or rank(row) >= rank(current):
            by_key[row_key] = row
    deduped = list(by_key.values())
    deduped.sort(key=lambda item: (item.get("backend") or "", item.get("model") or "", *task_sort_key(item.get("taskId") or "")))
    return deduped


def attempt_payload(rel: str, *, public_paths: bool = False, include_attempt_files: bool = True) -> dict:
    raw_rel = _resolve_public_trace_path(rel)
    raw_path = safe_rel_path(raw_rel)
    if not raw_path or not raw_path.exists():
        return {"error": "run path not found"}
    task_dir = raw_path
    selected_attempt_dir: Path | None = None
    if raw_path.name.startswith("p") and raw_path.parent.exists():
        selected_attempt_dir = raw_path
        task_dir = raw_path.parent
    try:
        rel_parts = task_dir.relative_to(RUNS).parts
    except ValueError:
        return {"error": "run path not found"}
    if len(rel_parts) < 4 or not include_in_public_webui(rel_parts[0], rel_parts[1], rel_parts[2]):
        return {"error": "run path not found"}
    task_summary = read_json(task_dir / "summary.json")
    attempts = task_summary.get("attempts") or synthetic_attempts(task_dir)
    if not attempts:
        return {"error": "summary has no attempts"}
    resolved_attempt = task_summary.get("resolvedAttempt")
    selected_attempt = attempts[-1]
    if selected_attempt_dir is not None:
        for item in attempts:
            if _local_attempt_dir(task_dir, item.get("outDir", "")) == selected_attempt_dir:
                selected_attempt = item
                break
    if selected_attempt_dir is None and isinstance(resolved_attempt, int):
        for item in attempts:
            if item.get("attempt") == resolved_attempt:
                selected_attempt = item
                break
    attempt_dir = _local_attempt_dir(task_dir, selected_attempt.get("outDir", ""))
    if not attempt_dir.exists():
        return {"error": "selected attempt not found"}
    score = read_json(attempt_dir / "score.json")
    meta = read_json(attempt_dir / "meta.json")
    backend = infer_backend(task_summary or meta)
    live_ctx = live_attempt_context(task_dir, backend)
    if not task_summary:
        task_summary = {
            "taskId": task_dir.name,
            "backend": task_dir.parents[2].name,
            "model": _display_model(meta.get("model") or task_dir.parents[1].name),
            "modelSlug": task_dir.parents[1].name,
            "finalStatus": "running",
            "finalScore": score.get("final_completion_score", score.get("capped_score", score.get("overall_score"))),
            "attempts": attempts,
            "resolvedAttempt": None,
        }

    logs = {}
    log_dir = attempt_dir / "logs"
    if log_dir.exists():
        for path in sorted(log_dir.glob("*")):
            if _safe_runs_file(path):
                logs[path.name] = read_text(path)

    openclaw_logs = [path for path in sorted((attempt_dir / "openclaw").glob("*.log")) if _safe_runs_file(path)]
    openclaw_log = openclaw_logs[-1] if openclaw_logs else None
    usage = usage_payload(attempt_dir)
    selected_supervision_trace = enrich_supervision_trace(attempt_dir, supervision_trace(attempt_dir))
    selected_supervision_context = read_json(attempt_dir / "supervision_context.json")
    selected_agent_sessions = agent_sessions_payload(attempt_dir)
    selected_agent_manifest = read_json(attempt_dir / "agent_sessions_manifest.json")
    result_files = []
    result_dir = attempt_dir / "result"
    if result_dir.exists():
        for path, rel_result in _iter_result_artifact_files(result_dir):
            if _safe_runs_file(path):
                result_files.append(
                    {
                        "path": str(rel_result),
                        "url": run_url(path),
                        "size": path.stat().st_size,
                        "text": read_text(path) if path.suffix.lower() in TEXT_RESULT_SUFFIXES and path.stat().st_size <= 512_000 else "",
                    }
                )
    # ``inline_images/`` holds binary payloads extracted from base64 image
    # blocks in tool results (written by lib.runner._persist_inline_image).
    # Kept separate from ``result/`` so Saved Results stays focused on
    # artifacts the agent explicitly saved, and so
    # ``_copy_visible_workspace_files`` (supervision_common.py) keeps the
    # supervisor / user-simulator workspaces clean.
    inline_images = _collect_inline_images(attempt_dir)
    # ``mcp_artifacts/`` holds MCP tool-side-effect files
    # (playwright-mcp auto-saved screenshots, DOM snapshots, console
    # logs), also outside ``result/`` so they are not mirrored into
    # supervisor workspace. Enumerated separately for WebUI rendering.
    mcp_artifacts = _collect_mcp_artifacts(attempt_dir)
    attempt_files = []
    if include_attempt_files:
        for path in sorted(attempt_dir.rglob("*")):
            if not path.is_file():
                continue
            rel_attempt_file = str(path.relative_to(attempt_dir))
            if _is_private_attempt_file_rel(rel_attempt_file):
                continue
            if not _is_public_run_artifact_rel(rel_attempt_file):
                continue
            if rel_attempt_file.startswith("supervision/") and not _is_public_supervision_artifact(rel_attempt_file):
                continue
            attempt_files.append(rel_attempt_file)

    transcript_path = attempt_dir / "transcript.jsonl"
    agent_log = log_dir / "agent.log" if (log_dir / "agent.log").exists() else None
    live_transcript = str(live_ctx.get("transcript") or "")
    attempt_cards = []
    attempt_details = []
    for item in attempts:
        item_dir = _local_attempt_dir(task_dir, item.get("outDir", ""))
        if not item_dir.exists():
            continue
        item_score = read_json(item_dir / "score.json")
        item_meta = read_json(item_dir / "meta.json")
        item_log_dir = item_dir / "logs"
        item_agent_log = item_log_dir / "agent.log" if (item_log_dir / "agent.log").exists() else None
        item_logs = {}
        if item_log_dir.exists():
            for path in sorted(item_log_dir.glob("*")):
                if _safe_runs_file(path):
                    item_logs[path.name] = read_text(path)
        item_openclaw_logs = [path for path in sorted((item_dir / "openclaw").glob("*.log")) if _safe_runs_file(path)]
        item_openclaw_log = item_openclaw_logs[-1] if item_openclaw_logs else None
        attempt_cards.append(
            {
                "attempt": item.get("attempt"),
                "promptKind": item.get("promptKind"),
                "stageType": item_meta.get("stageType") or item.get("stageType"),
                "stageId": item_meta.get("stageId") or item.get("stageId"),
                "stageIndex": item_meta.get("stageIndex") or item.get("stageIndex"),
                "attemptPath": str(item_dir.relative_to(RUNS)),
                "supervision": item_meta.get("supervision") or {},
                "score": item_score.get("final_completion_score", item_score.get("capped_score", item_score.get("overall_score"))),
                "rawScore": item_score.get("overall_score"),
                "supervisorScore": item_score.get("overall_score"),
                "verdict": item_score.get("verdict"),
                "status": "resolved" if task_summary.get("resolvedAttempt") == item.get("attempt") else "primary",
                "continuationCount": len(item_meta.get("continuations") or []),
                "outputs": item_meta.get("outputs") or [],
                "process": item_meta.get("process") or {},
                "checkpoints": item_meta.get("checkpoints") or [],
                "supervisionCycleCount": len(enrich_supervision_trace(item_dir, supervision_trace(item_dir))),
            }
        )
        attempt_details.append(
            {
                "attempt": item.get("attempt"),
                "promptKind": item.get("promptKind"),
                "stageType": item_meta.get("stageType") or item.get("stageType"),
                "stageId": item_meta.get("stageId") or item.get("stageId"),
                "stageIndex": item_meta.get("stageIndex") or item.get("stageIndex"),
                "attemptPath": str(item_dir.relative_to(RUNS)),
                "supervision": item_meta.get("supervision") or {},
                "outDir": str(item_dir),
                "meta": item_meta,
                "score": item_score,
                "transcript": parse_attempt_transcript(
                    item_dir / "transcript.jsonl",
                    agent_log=item_agent_log,
                    live_text=live_transcript if item_dir == attempt_dir else "",
                ),
                "agentSessions": agent_sessions_payload(item_dir),
                "agentSessionManifest": read_json(item_dir / "agent_sessions_manifest.json"),
                "continuationTrace": item_meta.get("continuationTrace") or [],
                "continuations": item_meta.get("continuations") or [],
                "supervisionTrace": enrich_supervision_trace(item_dir, supervision_trace(item_dir)),
                "supervisionContext": read_json(item_dir / "supervision_context.json"),
                "toolUsage": read_json(item_dir / "tool_usage.json"),
                "usage": usage_payload(item_dir),
                "runtimeProbe": read_json(item_dir / "runtime_probe.json"),
                "recording": recording_info(item_dir),
                "recordingsByCycle": recordings_by_cycle(item_dir),
                "logs": item_logs,
                "keyNodes": parse_openclaw_key_nodes(item_openclaw_log) if item_openclaw_log else [],
                # Per-attempt Execution Timeline data for the Gantt panel.
                # Empty dict when the attempt predates the feature (webui
                # frontend treats ``{phases: []}`` / missing as "no panel").
                "timeline": read_json(item_dir / "timeline.json"),
                # Per-attempt inline_images (transient screenshots extracted
                # from base64 payloads in tool results). Renders inline in the
                # flow timeline alongside result/ files.
                "inlineImages": _collect_inline_images(item_dir),
                # Per-attempt mcp_artifacts (playwright-mcp auto-saved
                # screenshots, snapshots, console logs). Kept outside
                # result/ so supervisor workspace stays minimal.
                "mcpArtifacts": _collect_mcp_artifacts(item_dir),
            }
        )

    empty_reason = ""
    if not result_files and not read_text(transcript_path) and not score and not logs and not selected_supervision_trace:
        if live_ctx.get("container"):
            empty_reason = "This attempt is still running, but the first transcript chunk, supervision output, and saved artifacts have not been synced to the host yet."
        else:
            empty_reason = "This attempt directory currently only contains initialization files, which means the run stopped before the first transcript, supervision output, or saved artifacts were synced."

    payload = {
        "relPath": str(task_dir.relative_to(RUNS)),
        "selectedAttemptPath": str(attempt_dir.relative_to(RUNS)),
        "taskSummary": task_summary,
        "attemptCards": attempt_cards,
        "attemptDetails": attempt_details,
        "meta": meta,
        "backend": backend,
        "score": score,
        "toolUsage": read_json(attempt_dir / "tool_usage.json"),
        "usage": usage,
        "usageSummary": usage_summary(attempt_dir),
        "checkpointCounts": checkpoint_counts(score),
        "continuationCount": len(meta.get("continuations") or []),
        "continuationTrace": meta.get("continuationTrace") or [],
        "outputs": meta.get("outputs") or [],
        "process": meta.get("process") or {},
        "checkpoints": meta.get("checkpoints") or [],
        "transcript": parse_attempt_transcript(transcript_path, agent_log=agent_log, live_text=live_transcript),
        "agentSessions": selected_agent_sessions,
        "agentSessionManifest": selected_agent_manifest,
        "supervision": meta.get("supervision") or {},
        "supervisionDecisions": meta.get("supervisionDecisions") or [],
        "supervisionTrace": selected_supervision_trace,
        "supervisionContext": selected_supervision_context,
        "supervisionArtifacts": supervision_artifacts(attempt_dir),
        "keyNodes": parse_openclaw_key_nodes(openclaw_log) if openclaw_log else [],
        "logs": logs,
        "resultFiles": result_files,
        "inlineImages": inline_images,
        "mcpArtifacts": mcp_artifacts,
        "attemptFiles": attempt_files,
        "emptyReason": empty_reason,
        "supervisionLog": read_text(attempt_dir / "supervision.log"),
        "desktopProbe": read_text(attempt_dir / "desktop_probe.log"),
        "runtimeProbe": read_json(attempt_dir / "runtime_probe.json"),
        "recording": recording_info(attempt_dir),
        "recordingsByCycle": recordings_by_cycle(attempt_dir),
        "liveContainer": live_ctx.get("container"),
        # Raw timeline.json for the Execution Timeline Gantt panel. Missing
        # file (runs from before this feature) renders as an empty dict, which
        # the frontend treats as "hide the panel entirely".
        "timeline": read_json(attempt_dir / "timeline.json"),
    }
    if public_paths:
        _publicize_trace_payload_paths(payload)
        payload = _publicize_run_urls(payload)
    return sanitize_public_payload(payload)


def _with_public_route_fields(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        _publicize_run_route_fields(item)
        out.append(item)
    return out


_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")

# Round 9 / A1: never serve raw ``privacy/env.env`` contents through
# the webui.  Even though privacy/ is excluded from the worker-side
# rsync (worker_runner.py:_rsync_to_controller), defense-in-depth:
# reject any path that looks like
# ``codex_sessions/<role>/workspace/privacy/*`` so a stray privacy
# file checked into runs/ cannot leak via the WebUI.
_PRIVACY_REL_RE = re.compile(r"codex_sessions/[^/]+/workspace/privacy/")


def _is_privacy_path(rel: str) -> bool:
    """Return True if the request path matches the role-private
    privacy env subtree.  Used to short-circuit both /runs/ static
    file serving and any API that takes a path query parameter."""
    return bool(_PRIVACY_REL_RE.search(rel or ""))


def _is_private_attempt_file_rel(rel: str) -> bool:
    """Return True when an attempt-local file listing entry should stay
    server-internal rather than being exposed through structured APIs."""
    parts = _normalized_rel_parts(rel)
    normalized = "/".join(parts)
    return _is_privacy_path(normalized) or _is_privacy_rel_parts(parts)


def _is_private_static_asset_rel(rel: str) -> bool:
    parts = _normalized_rel_parts(rel)
    if _is_privacy_rel_parts(parts):
        return True
    return any(part.startswith(".") for part in parts)


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urlparse(path).path
        if (
            parsed == "/" or parsed == ""
            or parsed.startswith("/leaderboard")
            or parsed.startswith("/trace")
            or parsed == "/tasks"
            or parsed == "/tasks/"
            or parsed.startswith("/tasks/task_")
        ):
            return str(STATIC / "index.html")
        if parsed.startswith("/runs/"):
            rel = parsed.removeprefix("/runs/")
            if _is_privacy_path(rel) or not _is_public_run_artifact_rel(rel):
                # Return a non-existent path so SimpleHTTPRequestHandler
                # renders 404.  Don't expose the real reason to the caller.
                return str(RUNS / "__nonexistent_privacy_blocked__")
            target = safe_rel_path(rel, RUNS)
            return str(target or RUNS)
        if parsed.startswith("/runs-public/"):
            rel = _resolve_public_artifact_rel(parsed.removeprefix("/runs-public/"))
            if not rel or _is_privacy_path(rel) or not _is_public_run_artifact_rel(rel):
                return str(RUNS / "__nonexistent_privacy_blocked__")
            target = safe_rel_path(rel, RUNS)
            return str(target or RUNS)
        # Static asset trees for the Tasks page. Range-request support and
        # mimetype handling come for free from SimpleHTTPRequestHandler, so
        # large source PDFs / videos / images stream and seek correctly.
        if parsed.startswith("/tasks/"):
            rel = parsed.removeprefix("/tasks/")
            if _is_private_static_asset_rel(rel):
                return str(TASKS / "__nonexistent_privacy_blocked__")
            target = safe_rel_path(rel, TASKS)
            return str(target or TASKS)
        if parsed.startswith("/injection/"):
            rel = parsed.removeprefix("/injection/")
            if _is_private_static_asset_rel(rel):
                return str(INJECTION / "__nonexistent_privacy_blocked__")
            target = safe_rel_path(rel, INJECTION)
            return str(target or INJECTION)
        if parsed.startswith("/assets/"):
            target = safe_rel_path(parsed.removeprefix("/assets/"), ASSETS)
            return str(target or (ASSETS / "__nonexistent_assets_blocked__"))
        if parsed.startswith("/static/"):
            target = safe_rel_path(parsed.removeprefix("/static/"), STATIC)
            return str(target or (STATIC / "__nonexistent_static_blocked__"))
        target = safe_rel_path(parsed.lstrip("/"), STATIC)
        return str(target or (STATIC / "__nonexistent_static_blocked__"))

    def list_directory(self, path: str):  # noqa: ANN001
        self.send_error(HTTPStatus.NOT_FOUND, "directory listing disabled")
        return None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/runs":
            query = parse_qs(parsed.query)
            force = (query.get("refresh") or ["0"])[0] == "1"
            if (query.get("slim") or ["0"])[0] == "1":
                self.respond_json({"runs": list_task_runs_slim(force=force, public_paths=True)})
            else:
                self.respond_json({"runs": _with_public_route_fields(list_task_runs())})
            return
        if parsed.path == "/api/attempt":
            rel = (parse_qs(parsed.query).get("path") or [""])[0]
            self.respond_json(attempt_payload(rel, public_paths=True))
            return
        if parsed.path == "/api/aggregate":
            # ``?refresh=1`` bypasses the mtime cache (FAB refresh button).
            force = (parse_qs(parsed.query).get("refresh") or ["0"])[0] == "1"
            self.respond_json(aggregate.aggregate_runs(force=force))
            return
        if parsed.path == "/api/tasks":
            self.respond_json({"tasks": aggregate.list_task_yamls()})
            return
        if parsed.path.startswith("/api/task/"):
            task_id = unquote(parsed.path.removeprefix("/api/task/")).strip("/")
            if not task_id or "/" in task_id:
                self.respond_json({"error": "invalid task id"}, status=HTTPStatus.BAD_REQUEST)
                return
            payload = aggregate.task_detail(task_id)
            if payload is None:
                self.respond_json({"error": "task not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self.respond_json(payload)
            return
        # Honour HTTP Range requests for static files so <video> elements can
        # seek and pause. stdlib SimpleHTTPRequestHandler streams the whole
        # body with status 200 regardless of Range header, which is why
        # scrubbing on the per-cycle recording.mp4 did not work.
        if self.headers.get("Range"):
            if self._try_send_ranged_file():
                return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        # Some browsers probe seekability via HEAD; advertise range support so
        # they then request a specific byte range via GET.
        super().do_HEAD()

    def end_headers(self) -> None:
        # Advertise range support on every static response so video elements
        # know scrubbing is allowed.
        self.send_header("Accept-Ranges", "bytes")
        # Never let browsers serve a stale dashboard: the SPA assets
        # (.js/.css/.html), the index route, and every /api/ response must
        # always be revalidated, otherwise a deploy leaves users staring at
        # cached JS (e.g. the in/out token row not showing up). Large media
        # (.mp4/.png/…) is left cacheable so video scrubbing stays cheap.
        path = (self.path or "/").split("?", 1)[0]
        if (
            path == "/"
            or path.startswith("/api/")
            or path.endswith((".js", ".css", ".html", ".json"))
        ):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def _try_send_ranged_file(self) -> bool:
        """Best-effort Range handler. Returns True on a 206 response."""
        raw = self.headers.get("Range", "")
        match = _RANGE_RE.match(raw.strip())
        if not match:
            return False
        try:
            abs_path = Path(self.translate_path(self.path))
        except Exception:
            return False
        if not abs_path.is_file():
            return False
        size = abs_path.stat().st_size
        start_s, end_s = match.group(1), match.group(2)
        if start_s:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        elif end_s:
            # ``bytes=-N`` → last N bytes
            suffix = int(end_s)
            if suffix <= 0:
                return False
            start = max(0, size - suffix)
            end = size - 1
        else:
            return False
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return True
        length = end - start + 1
        ctype, _ = mimetypes.guess_type(str(abs_path))
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        with abs_path.open("rb") as fh:
            fh.seek(start)
            remaining = length
            # 64 KB chunks are plenty for seeking; avoids loading whole file.
            while remaining > 0:
                chunk = fh.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except BrokenPipeError:
                    return True
                remaining -= len(chunk)
        return True

    def respond_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("CLAWBENCH_WEBUI_QUIET") == "1":
            return
        super().log_message(fmt, *args)


def _prewarm_server_cache() -> None:
    """Warm expensive disk-derived payloads before the first browser visit."""
    try:
        started = time.monotonic()
        aggregate.aggregate_runs()
        aggregate.list_task_yamls()
        elapsed = time.monotonic() - started
        print(f"Clawbench Web UI cache prewarmed in {elapsed:.1f}s", flush=True)
    except Exception as exc:  # pragma: no cover - startup resilience only.
        print(f"Clawbench Web UI cache prewarm failed: {exc}", flush=True)


def main() -> None:
    # Default to 0.0.0.0 so an isolated WebUI started on the controller
    # is reachable from the local network without requiring
    # CLAWBENCH_WEBUI_HOST to be set on every launch. Override with
    # CLAWBENCH_WEBUI_HOST=127.0.0.1 to bind localhost-only.
    host = os.environ.get("CLAWBENCH_WEBUI_HOST", "0.0.0.0")
    port = int(os.environ.get("CLAWBENCH_WEBUI_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Clawbench Web UI listening on http://{host}:{port}", flush=True)
    if os.environ.get("CLAWBENCH_WEBUI_PREWARM") == "1":
        threading.Thread(target=_prewarm_server_cache, name="webui-prewarm", daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
