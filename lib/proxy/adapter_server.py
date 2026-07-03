#!/usr/bin/env python3
'''HTTP compatibility adapter for Clawbench's proxy layer.

Spawned by ``lib.proxy.adapter.start_proxy_adapter`` as
``python3 -m lib.proxy.adapter_server <listen_host> <listen_port>
<upstream_base> <adapter_kind> <log_path> <request_log_path>``.

Listens on a loopback port, accepts Codex-shaped JSON requests, and
forwards them upstream — optionally after:
- ``drop_max_tokens``: removing the ``max_completion_tokens`` field
  some legacy gateways reject;
- ``responses_via_chat``: converting between OpenAI ``/responses`` and
  ``/chat/completions`` envelopes for upstreams that only speak the
  latter.

Round 10 / P2: this module replaces a 1179-line ``python3 -c <script>``
inline string previously held inside ``adapter.start_proxy_adapter``.
The inline form meant production code was never importable, and
``lib.proxy.transform`` had to keep a hand-copied mirror of 4 transform
functions in sync.  As a real module, every helper here is testable
via ordinary ``import`` (see ``tests/unit/test_responses_adapter_*.py``
and ``tests/unit/test_proxy_adapter_server_smoke.py``), and
``lib.proxy.transform`` re-exports the pure transform functions so
existing tests continue to work unchanged.

The module is designed to be run as a script (``python3 -m
lib.proxy.adapter_server``) — importing it is safe and exposes every
top-level definition, but the ``ThreadingHTTPServer`` only binds when
``main()`` is invoked from ``if __name__ == "__main__":``.
'''
from __future__ import annotations

import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


# --------------------------------------------------------------------------
# Argv-dependent globals — set inside main() so importing the module
# (e.g. for unit testing) does not require argv / cannot fail with
# IndexError.  Sentinel values; the runtime entrypoint reassigns them.
# --------------------------------------------------------------------------
LISTEN_HOST = ""
LISTEN_PORT = 0
UPSTREAM_BASE = ""
ADAPTER = ""
LOG_PATH = ""
# Optional: full request/response transcript log (one JSON-Lines entry per
# request). Empty disables capture. Sliced into ``<attempt>/requests.jsonl``
# by ``lib/runner/artifacts.py:append_attempt_request_log``.
REQUEST_LOG_PATH = ""


# Per-message size cap for request_log payloads to bound disk growth on
# long-context tasks.
REQUEST_LOG_MAX_BYTES = int(os.environ.get("CLAWBENCH_RECORD_REQUEST_MAX_BYTES", "200000"))
# Regex for the per-task URL prefix injected by the runner's config
# helpers (see ``lib/runner/task_config.py:adapter_base_url_for_attempt``).
# Format: ``/_t/<attempt_id>/<rest>`` — attempt_id is the unique stage dir
# name (e.g. ``p1-abc123``). When present we strip it from the path before
# matching/forwarding upstream and tag every usage event with task_id, so
# parallel tasks sharing one adapter cannot steal each other's events even
# when their wall-clock windows overlap on the same adapter kind.
TASK_ID_PREFIX_RE = re.compile(r"^/+_t/([A-Za-z0-9_-]+)(/.*)?$")
try:
    import certifi  # type: ignore
except Exception:
    certifi = None
if certifi is not None:
    TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
else:
    TLS_CONTEXT = ssl.create_default_context()

TOOL_CALL_EXTRA_CACHE = {}


# --------------------------------------------------------------------------
# Optional upstream key rotation for selected /chat/completions models.
#
# Some hosted model gateways expose several equivalent API keys but enforce a
# low per-key request-per-minute limit. When explicitly enabled via
# ``CLAWBENCH_ROTATE_KEY_ENVS`` and ``CLAWBENCH_ROTATE_MODELS``, the
# ``drop_max_tokens`` adapter can rotate the upstream Authorization header
# across those key env vars and fail over on HTTP 429. Every non-matching model,
# method, path, adapter, or empty key pool is forwarded verbatim with the
# inbound Authorization header.
#
# Key VALUES are never logged; only counts / env-var names are written.
# --------------------------------------------------------------------------
ROTATOR = None
ROTATE_KEY_ENV_VARS: tuple[str, ...] = ()


class KeyRotator:
    """Thread-safe round-robin pool of key values with per-key 429 cooldown."""

    def __init__(self, keys, *, cooldown_s: float = 20.0):
        self._keys = [str(k) for k in (keys or []) if str(k or "").strip()]
        self._cursor = 0
        self._hot = {}  # key -> ts when it last got a 429
        self._cooldown_s = float(cooldown_s)
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._keys)

    def order(self) -> list:
        """Advance the round-robin cursor and return ALL keys ordered from the
        new cursor position, with not-currently-cooling keys first and cooling
        (recently-429'd) keys appended last. Empty pool -> ``[]``."""
        with self._lock:
            n = len(self._keys)
            if n == 0:
                return []
            self._cursor = (self._cursor + 1) % n
            start = self._cursor
            rotated = [self._keys[(start + i) % n] for i in range(n)]
            now = time.time()
            fresh = []
            cooling = []
            for key in rotated:
                ts_hot = self._hot.get(key)
                if ts_hot is not None and (now - ts_hot) < self._cooldown_s:
                    cooling.append(key)
                else:
                    fresh.append(key)
            return fresh + cooling

    def mark_hot(self, key) -> None:
        """Record that ``key`` just received a 429 (starts its cooldown)."""
        with self._lock:
            self._hot[str(key)] = time.time()


def _api_env_file_path() -> Path:
    """Locate ``configs/api.local.env``. Honors ``CLAWBENCH_API_ENV_FILE``
    override, else derives from this module's location (repo root is two
    parents up from ``lib/proxy/``)."""
    override = str(os.environ.get("CLAWBENCH_API_ENV_FILE", "")).strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "configs" / "api.local.env"


def _rotation_key_env_vars() -> tuple[str, ...]:
    raw = str(os.environ.get("CLAWBENCH_ROTATE_KEY_ENVS", "")).strip()
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _load_rotation_keys(env_vars: tuple[str, ...] | None = None) -> list:
    """Read configured key env vars from ``configs/api.local.env``.

    Returns only non-empty values, in the order declared by
    ``CLAWBENCH_ROTATE_KEY_ENVS``. Empty/missing config means no rotation.
    """
    names = tuple(env_vars or _rotation_key_env_vars())
    if not names:
        return []
    try:
        from lib import config_stack
        env_file = _api_env_file_path()
        files = [env_file] if env_file.exists() else []
        env = config_stack.merged_env(files=files)
        keys = []
        for var in names:
            value = str(env.get(var) or "").strip()
            if value:
                keys.append(value)
        return keys
    except Exception:
        return []


def _is_rotated_model(model) -> bool:
    """True when ``model`` matches ``CLAWBENCH_ROTATE_MODELS``.

    The env var is a comma-separated substring allowlist. It is intentionally
    empty by default, so key rotation is opt-in and provider/model agnostic.
    """
    text = str(model or "").lower()
    if not text:
        return False
    raw = str(os.environ.get("CLAWBENCH_ROTATE_MODELS", "")).strip()
    needles = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not needles:
        return False
    return any(needle in text for needle in needles)


def normalize_tool_call_id(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def append_log(event):
    if not LOG_PATH:
        return
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def append_request_log(event):
    if not REQUEST_LOG_PATH:
        return
    try:
        with open(REQUEST_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def _truncate_for_log(value):
    # Bounds the size of a single field in the request_log so a runaway
    # long-context payload can't blow disk. We serialize once and replace
    # with a marker if too big — callers pass dicts so the original object
    # is not mutated.
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except Exception:
        encoded = repr(value)
    if len(encoded.encode("utf-8")) <= REQUEST_LOG_MAX_BYTES:
        return value
    truncated = encoded[: REQUEST_LOG_MAX_BYTES // 2]
    return {"__truncated__": True,
            "encoded_bytes": len(encoded.encode("utf-8")),
            "preview": truncated}


def extract_task_id(path):
    # Splits ``/_t/<id>/<rest>`` off the front of ``path``. Returns
    # ``(task_id, rest_path)`` where ``rest_path`` always begins with ``/``.
    # If the prefix is absent, returns ``("", path)`` so callers can treat
    # legacy/unprefixed clients without branching.
    match = TASK_ID_PREFIX_RE.match(path or "/")
    if not match:
        return "", path or "/"
    rest = match.group(2) or "/"
    if not rest.startswith("/"):
        rest = "/" + rest
    return match.group(1), rest


def dump_debug_payload(filename, payload):
    if not LOG_PATH:
        return
    try:
        path = os.path.join(os.path.dirname(LOG_PATH), filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception:
        return


def sanitize_chat_payload(payload):
    event = {"dropped": []}
    if not isinstance(payload, dict):
        return payload, event
    try:
        event["payload_bytes"] = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    except Exception:
        pass
    event["json_keys"] = sorted(payload.keys())
    if "max_tokens" in payload:
        event["max_tokens"] = payload.get("max_tokens")
    if "max_completion_tokens" in payload:
        event["max_completion_tokens"] = payload.get("max_completion_tokens")
    if "max_completion_tokens" in payload:
        if "max_tokens" not in payload:
            payload["max_tokens"] = payload.get("max_completion_tokens")
            event["rewrote"] = {"max_completion_tokens": "max_tokens"}
        payload.pop("max_completion_tokens", None)
        event["dropped"].append("max_completion_tokens")
    # When the client asked for SSE streaming, ensure the upstream
    # emits a final ``usage`` chunk so the adapter can log token
    # counts. Without ``stream_options.include_usage=true`` an OpenAI-
    # compatible upstream returns an SSE stream that terminates with
    # ``data: [DONE]`` and NO usage — the adapter then sees no
    # parseable usage anywhere and the ledger comes out empty. This
    # is a no-op on providers that ignore the field.
    if bool(payload.get("stream")):
        existing_options = payload.get("stream_options")
        if isinstance(existing_options, dict):
            if not existing_options.get("include_usage"):
                existing_options["include_usage"] = True
                event.setdefault("rewrote", {})["stream_options.include_usage"] = "true"
        else:
            payload["stream_options"] = {"include_usage": True}
            event.setdefault("rewrote", {})["stream_options"] = '{"include_usage": true}'
    messages = payload.get("messages")
    if isinstance(messages, list):
        summary = []
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                summary.append({"index": index, "type": type(message).__name__})
                continue
            content = message.get("content")
            if isinstance(content, str):
                content_kind = "text"
                content_size = len(content)
            elif isinstance(content, list):
                content_kind = ",".join(
                    str(item.get("type") or type(item).__name__)
                    for item in content
                    if isinstance(item, dict)
                ) or "list"
                content_size = len(content)
            elif content is None:
                content_kind = "none"
                content_size = 0
            else:
                content_kind = type(content).__name__
                content_size = 1
            entry = {
                "index": index,
                "role": str(message.get("role") or ""),
                "content_kind": content_kind,
                "content_size": content_size,
            }
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list):
                entry["tool_call_count"] = len(tool_calls)
                names = []
                for tool_call in tool_calls[:5]:
                    if not isinstance(tool_call, dict):
                        continue
                    function = tool_call.get("function")
                    if isinstance(function, dict):
                        name = str(function.get("name") or "").strip()
                        if name:
                            names.append(name)
                if names:
                    entry["tool_call_names"] = names
            tool_call_id = str(message.get("tool_call_id") or "").strip()
            if tool_call_id:
                entry["tool_call_id"] = tool_call_id
            summary.append(entry)
        event["message_summary"] = summary
    tools = payload.get("tools")
    if isinstance(tools, list):
        event["tool_count"] = len(tools)
        tool_names = []
        for tool in tools[:10]:
            if not isinstance(tool, dict):
                continue
            function = tool.get("function")
            if isinstance(function, dict):
                name = str(function.get("name") or "").strip()
                if name:
                    tool_names.append(name)
        if tool_names:
            event["tool_names"] = tool_names
    tool_choice = payload.get("tool_choice")
    if tool_choice not in {None, ""}:
        event["tool_choice"] = tool_choice
    # Guard: ``tool_choice`` and ``parallel_tool_calls`` are rejected by
    # several OpenAI-compatible providers when ``tools`` is absent or
    # empty. Drop the orphan keys silently rather than letting the
    # upstream 400 out — Codex's auto-compact hits both cases.
    has_tools = isinstance(payload.get("tools"), list) and bool(payload.get("tools"))
    if tool_choice is not None and not has_tools:
        payload.pop("tool_choice", None)
        event.setdefault("rewrote", {})["tool_choice"] = "dropped (no tools)"
    if "parallel_tool_calls" in payload and not has_tools:
        payload.pop("parallel_tool_calls", None)
        event.setdefault("rewrote", {})["parallel_tool_calls"] = "dropped (no tools)"
    return payload, event


def cache_tool_call_extras(chat_payload):
    if not isinstance(chat_payload, dict):
        return
    choices = chat_payload.get("choices")
    if not isinstance(choices, list):
        return
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_id = str(tool_call.get("id") or "").strip()
            extra = tool_call.get("extra_content")
            if tool_id and isinstance(extra, dict) and extra:
                TOOL_CALL_EXTRA_CACHE[tool_id] = extra
                normalized = normalize_tool_call_id(tool_id)
                if normalized:
                    TOOL_CALL_EXTRA_CACHE[normalized] = extra
                append_log({"adapter": ADAPTER, "cached_tool_call_extra_id": tool_id, "cached_tool_call_extra_normalized": normalized})


def cache_tool_call_extras_from_chunk(chunk):
    if not isinstance(chunk, dict):
        return
    choices = chunk.get("choices")
    if not isinstance(choices, list):
        return
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        for container_key in ("message", "delta"):
            container = choice.get(container_key)
            if not isinstance(container, dict):
                continue
            tool_calls = container.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                tool_id = str(tool_call.get("id") or "").strip()
                extra = tool_call.get("extra_content")
                if tool_id and isinstance(extra, dict) and extra:
                    TOOL_CALL_EXTRA_CACHE[tool_id] = extra
                    normalized = normalize_tool_call_id(tool_id)
                    if normalized:
                        TOOL_CALL_EXTRA_CACHE[normalized] = extra
                    append_log({"adapter": ADAPTER, "cached_tool_call_extra_id": tool_id, "cached_tool_call_extra_normalized": normalized})


def cache_tool_call_extras_from_bytes(data):
    if not data:
        return
    text = data.decode("utf-8", errors="ignore")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            cache_tool_call_extras(payload)
        elif isinstance(payload, list):
            for item in payload:
                cache_tool_call_extras(item)
        return
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload_text = line[5:].strip()
        if not payload_text or payload_text == "[DONE]":
            continue
        try:
            chunk = json.loads(payload_text)
        except Exception:
            continue
        cache_tool_call_extras_from_chunk(chunk)


def inject_cached_tool_call_extras(payload):
    if not isinstance(payload, dict):
        return False
    injected = False
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return injected
    for message in messages:
        if not isinstance(message, dict) or str(message.get("role") or "") != "assistant":
            continue
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            if isinstance(tool_call.get("extra_content"), dict) and tool_call.get("extra_content"):
                continue
            tool_id = str(tool_call.get("id") or "").strip()
            normalized = normalize_tool_call_id(tool_id)
            cached = TOOL_CALL_EXTRA_CACHE.get(tool_id) or (TOOL_CALL_EXTRA_CACHE.get(normalized) if normalized else None)
            if not cached and normalized:
                for cached_id, cached_extra in TOOL_CALL_EXTRA_CACHE.items():
                    if not isinstance(cached_extra, dict) or not cached_extra:
                        continue
                    if str(cached_id).startswith(normalized) or normalized.startswith(str(cached_id)):
                        cached = cached_extra
                        break
            if cached:
                tool_call["extra_content"] = cached
                injected = True
                append_log({"adapter": ADAPTER, "injected_tool_call_extra_id": tool_id, "injected_tool_call_extra_normalized": normalized})
    return injected


def request_url(path):
    parsed_base = urllib.parse.urlsplit(UPSTREAM_BASE)
    base_prefix = parsed_base.path.rstrip("/")
    parsed_path = urllib.parse.urlsplit(path)
    request_path = parsed_path.path or "/"
    relative_path = request_path
    if base_prefix and request_path.startswith(base_prefix + "/"):
        relative_path = request_path[len(base_prefix):]
    elif request_path == base_prefix:
        relative_path = "/"
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    final_path = (base_prefix + relative_path).replace("//", "/")
    return urllib.parse.urlunsplit(
        (
            parsed_base.scheme,
            parsed_base.netloc,
            final_path,
            parsed_path.query,
            parsed_path.fragment,
        )
    )


def upstream_chat_url(path):
    parsed_base = urllib.parse.urlsplit(UPSTREAM_BASE)
    base_prefix = parsed_base.path.rstrip("/")
    parsed_path = urllib.parse.urlsplit(path)
    request_path = parsed_path.path or "/responses"
    relative_path = request_path
    if base_prefix and request_path.startswith(base_prefix + "/"):
        relative_path = request_path[len(base_prefix):]
    elif request_path == base_prefix:
        relative_path = "/responses"
    if relative_path.endswith("/responses"):
        relative_path = relative_path[: -len("/responses")] + "/chat/completions"
    elif relative_path == "/responses":
        relative_path = "/chat/completions"
    else:
        relative_path = "/chat/completions"
    final_path = (base_prefix + relative_path).replace("//", "/")
    return urllib.parse.urlunsplit(
        (
            parsed_base.scheme,
            parsed_base.netloc,
            final_path,
            parsed_path.query,
            parsed_path.fragment,
        )
    )


def item_text(item):
    if not isinstance(item, dict):
        return ""
    for key in ("text", "input_text", "output_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    image_url = item.get("image_url")
    if isinstance(image_url, dict):
        url = str(image_url.get("url") or "").strip()
        if url:
            return url
    if isinstance(image_url, str) and image_url.strip():
        return image_url
    return ""


def normalize_content(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        text = str(content or "").strip()
        return text
    parts = []
    text_only = True
    for item in content:
        if not isinstance(item, dict):
            text = str(item or "").strip()
            if text:
                parts.append({"type": "text", "text": text})
            continue
        item_type = str(item.get("type") or "").strip()
        if item_type in {"text", "input_text", "output_text"}:
            text = item_text(item)
            if text:
                parts.append({"type": "text", "text": text})
        elif item_type in {"input_image", "image_url", "image"}:
            text_only = False
            image_url = item.get("image_url")
            if isinstance(image_url, dict):
                url = str(image_url.get("url") or "").strip()
            else:
                url = str(item.get("url") or image_url or "").strip()
            if url:
                parts.append({"type": "image_url", "image_url": {"url": url}})
        else:
            text = item_text(item)
            if text:
                parts.append({"type": "text", "text": text})
    if not parts:
        return ""
    if text_only:
        text = "\n".join(part.get("text") or "" for part in parts if isinstance(part, dict) and str(part.get("text") or "").strip()).strip()
        return text
    return parts


def responses_to_chat_payload(payload):
    chat_payload = {
        "model": payload.get("model"),
        "messages": [],
        "stream": False,
    }
    instructions = str(payload.get("instructions") or "").strip()
    if instructions:
        chat_payload["messages"].append({"role": "system", "content": instructions})
    input_items = payload.get("input")
    if isinstance(input_items, str):
        text = input_items.strip()
        if text:
            chat_payload["messages"].append({"role": "user", "content": text})
    elif isinstance(input_items, list):
        pending_tool_calls: list[dict] = []
        # Image-bearing tool outputs get a follow-up ``role: "user"``
        # message so the provider's vision tokenizer can see them (the
        # tool message itself cannot carry multimodal arrays). Those
        # follow-ups MUST come AFTER every tool response that answers
        # the currently-open assistant ``tool_calls`` batch — inserting
        # them in the middle breaks OpenAI's "assistant tool_calls must
        # be followed by tool messages for each tool_call_id" invariant
        # and the provider 400s the request. We therefore queue them
        # here and flush only at turn boundaries.
        pending_followups: list[dict] = []

        def _flush_followups():
            nonlocal pending_followups
            for u in pending_followups:
                chat_payload["messages"].append(u)
            pending_followups = []

        for item in input_items:
            if not isinstance(item, dict):
                text = str(item or "").strip()
                if text:
                    _flush_followups()
                    chat_payload["messages"].append({"role": "user", "content": text})
                continue
            item_type = str(item.get("type") or "").strip()
            role = str(item.get("role") or "user").strip() or "user"
            if role == "developer":
                role = "system"
            if item_type == "function_call":
                # New assistant turn: close out any in-flight image
                # follow-ups from the previous tool batch first.
                _flush_followups()
                pending_tool_calls.append({
                    "id": str(item.get("call_id") or item.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(item.get("name") or ""),
                        "arguments": str(item.get("arguments") or "{}"),
                    },
                })
            elif item_type == "function_call_output":
                if pending_tool_calls:
                    chat_payload["messages"].append({"role": "assistant", "content": None, "tool_calls": pending_tool_calls})
                    pending_tool_calls = []
                output = item.get("output")
                call_id = str(item.get("call_id") or "")
                if isinstance(output, str):
                    # Plain text (exec_command, read_file, ...). Tool message
                    # takes the string content directly.
                    chat_payload["messages"].append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": output,
                    })
                elif isinstance(output, list):
                    # Codex passes back richer tool results as a list of
                    # content items — in practice that's ``input_image``
                    # for view_image (data URL) but can also be input_text
                    # chunks. ``role: "tool"`` messages on OpenAI chat/
                    # completions DO NOT accept multimodal array content
                    # on most providers today — stringifying the list via
                    # ``str(output)`` (the previous behavior) dumps the raw
                    # base64 data URL into the prompt, which the provider
                    # then bills at ~bytes/4 text tokens. A 150 KB JPEG
                    # data URL becomes ~40K prompt tokens per image; six
                    # of them blow past the 272 K context window.
                    #
                    # Fix: put a short placeholder into the tool message
                    # so the call/response pairing stays intact, then
                    # append a follow-up ``role: "user"`` message whose
                    # content uses the proper ``[{type: "image_url", ...},
                    # {type: "text", ...}]`` blocks. The provider's native
                    # vision tokenizer kicks in for each ``image_url`` and
                    # counts per-image (tens to low-hundreds of tokens),
                    # NOT per-byte.
                    followup_content: list[dict] = []
                    placeholder_parts: list[str] = []
                    for block in output:
                        if not isinstance(block, dict):
                            text = str(block or "").strip()
                            if text:
                                placeholder_parts.append(text)
                                followup_content.append({"type": "text", "text": text})
                            continue
                        block_type = str(block.get("type") or "").strip()
                        if block_type in {"input_image", "image_url", "image"}:
                            image_url_field = block.get("image_url")
                            if isinstance(image_url_field, dict):
                                url = str(image_url_field.get("url") or "").strip()
                                detail = image_url_field.get("detail")
                            else:
                                url = str(block.get("url") or image_url_field or "").strip()
                                detail = None
                            if url:
                                image_block = {"type": "image_url", "image_url": {"url": url}}
                                if isinstance(detail, str) and detail:
                                    image_block["image_url"]["detail"] = detail
                                followup_content.append(image_block)
                                placeholder_parts.append("[image]")
                        elif block_type in {"input_text", "output_text", "text"}:
                            text = item_text(block)
                            if text:
                                placeholder_parts.append(text)
                                followup_content.append({"type": "text", "text": text})
                        else:
                            text = item_text(block)
                            if text:
                                placeholder_parts.append(text)
                                followup_content.append({"type": "text", "text": text})
                    chat_payload["messages"].append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": (" ".join(placeholder_parts).strip()
                                    or "[tool result attached in the next turn]"),
                    })
                    if followup_content:
                        # Queue — do NOT emit between tool messages of
                        # the same tool_calls batch. Flushed by the
                        # next turn boundary (new function_call, new
                        # message, end of loop).
                        pending_followups.append({
                            "role": "user",
                            "content": followup_content,
                        })
                else:
                    # ``None`` or unexpected non-string, non-list — coerce to
                    # empty placeholder to keep the tool_call_id pairing
                    # valid. Should never happen in practice.
                    chat_payload["messages"].append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": "",
                    })
            elif item_type in {"message", ""} or "content" in item:
                if pending_tool_calls:
                    chat_payload["messages"].append({"role": "assistant", "content": None, "tool_calls": pending_tool_calls})
                    pending_tool_calls = []
                _flush_followups()
                content = normalize_content(item.get("content"))
                if content:
                    chat_payload["messages"].append({"role": role, "content": content})
            elif item_type in {"input_text", "text"}:
                text = item_text(item).strip()
                if text:
                    _flush_followups()
                    chat_payload["messages"].append({"role": role, "content": text})
        if pending_tool_calls:
            chat_payload["messages"].append({"role": "assistant", "content": None, "tool_calls": pending_tool_calls})
            pending_tool_calls = []
        _flush_followups()
    max_output_tokens = payload.get("max_output_tokens")
    if max_output_tokens not in {None, ""}:
        chat_payload["max_tokens"] = max_output_tokens
    text_cfg = payload.get("text") if isinstance(payload.get("text"), dict) else {}
    format_cfg = text_cfg.get("format") if isinstance(text_cfg.get("format"), dict) else {}
    format_type = str(format_cfg.get("type") or "").strip()
    if format_type == "json_object":
        chat_payload["response_format"] = {"type": "json_object"}
    elif format_type == "json_schema":
        schema = format_cfg.get("schema") if isinstance(format_cfg.get("schema"), dict) else {}
        if schema:
            chat_payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": str(format_cfg.get("name") or "codex_response"),
                    "schema": schema,
                    "strict": bool(format_cfg.get("strict", True)),
                },
            }
    tools = payload.get("tools")
    if isinstance(tools, list) and tools:
        chat_tools = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            if "function" in tool and isinstance(tool["function"], dict):
                chat_tools.append(tool)
            elif "name" in tool:
                chat_tools.append({
                    "type": "function",
                    "function": {k: v for k, v in tool.items() if k in {"name", "description", "parameters", "strict"}},
                })
        if chat_tools:
            chat_payload["tools"] = chat_tools
    tool_choice = payload.get("tool_choice")
    # Some providers reject ``tool_choice`` and ``parallel_tool_calls``
    # when ``tools`` is absent or empty (error: "'X' is only allowed
    # when 'tools' are specified"). Codex's auto-compact prompt hits
    # exactly this case because the compact turn strips tools but keeps
    # these companion fields. Only forward them when the chat payload
    # actually carries tools.
    if tool_choice is not None and chat_payload.get("tools"):
        chat_payload["tool_choice"] = tool_choice
    parallel_tool_calls = payload.get("parallel_tool_calls")
    if parallel_tool_calls is not None and chat_payload.get("tools"):
        chat_payload["parallel_tool_calls"] = parallel_tool_calls
    if "max_tokens" not in chat_payload:
        chat_payload["max_tokens"] = 4096
    return sanitize_chat_payload(chat_payload)[0]


def chat_message_text(message):
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item_text(item)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def chat_to_response_payload(chat_payload, *, requested_model):
    choices = chat_payload.get("choices") or []
    choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    output_text = chat_message_text(message)
    message_id = "msg_" + os.urandom(8).hex()
    response_id = "resp_" + os.urandom(8).hex()
    usage = chat_payload.get("usage") if isinstance(chat_payload.get("usage"), dict) else {}
    output_items: list[dict] = []
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            func = tc.get("function") if isinstance(tc.get("function"), dict) else {}
            call_id = str(tc.get("id") or "call_" + os.urandom(6).hex())
            output_items.append({
                "id": "fc_" + os.urandom(8).hex(),
                "call_id": call_id,
                "type": "function_call",
                "name": str(func.get("name") or ""),
                "arguments": str(func.get("arguments") or "{}"),
                "status": "completed",
            })
    if output_text or not output_items:
        output_items.insert(0, {
            "id": message_id,
            "type": "message",
            "status": "completed",
            "role": "assistant",
            "content": [{"type": "output_text", "text": output_text}],
        })
    status = "completed"
    finish_reason = str(choice.get("finish_reason") or "").strip()
    if finish_reason == "tool_calls":
        status = "incomplete"
    response = {
        "id": response_id,
        "object": "response",
        "created_at": int(time.time()),
        "model": str(chat_payload.get("model") or requested_model or ""),
        "status": status,
        "output": output_items,
        "usage": {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        },
    }
    return response, message_id, output_text


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def _send_json(self, status_code, payload, *, headers=None):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_sse_event(self, payload):
        data = ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")
        self.wfile.write(data)
        self.wfile.flush()

    def _handle_responses_via_chat(self, body):
        ts_request = getattr(self, "_ts_request", None) or time.time()
        payload = json.loads(body.decode("utf-8")) if body else {}
        event = {
            "path": self.path,
            "method": self.command,
            "content_type": self.headers.get("Content-Type", ""),
            "adapter": ADAPTER,
            "task_id": getattr(self, "task_id", "") or "",
            "mode": "responses_via_chat",
            "json_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        }
        append_log(event)
        upstream_payload = responses_to_chat_payload(payload if isinstance(payload, dict) else {})
        upstream_body = json.dumps(upstream_payload, ensure_ascii=False).encode("utf-8")
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection", "accept", "content-type"}
        }
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            upstream_chat_url(self.path),
            data=upstream_body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600, context=TLS_CONTEXT) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            raw = err.read()
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = {"error": {"message": raw.decode("utf-8", errors="ignore")}}
            self._send_json(err.code, payload)
            return
        chat_payload = json.loads(raw.decode("utf-8"))
        response_payload, message_id, output_text = chat_to_response_payload(
            chat_payload if isinstance(chat_payload, dict) else {},
            requested_model=(payload.get("model") if isinstance(payload, dict) else ""),
        )
        try:
            usage_obj = response_payload.get("usage") if isinstance(response_payload, dict) else None
            if isinstance(usage_obj, dict) and (usage_obj.get("total_tokens") or usage_obj.get("input_tokens") or usage_obj.get("output_tokens")):
                append_log({
                    "event": "usage",
                    "ts": time.time(),
                    # The adapter KIND is what downstream role
                    # attribution keys on (``drop_max_tokens`` =
                    # executor-side, ``responses_via_chat`` =
                    # codex-side). Emitting it alongside every usage
                    # event is what lets the per-attempt ledger
                    # separate executor from supervisor/user_simulator
                    # without having to also track the listen port.
                    "adapter": ADAPTER,
                    "task_id": getattr(self, "task_id", "") or "",
                    "endpoint": "/responses",
                    "model": str(response_payload.get("model") or ""),
                    "prompt_tokens": int(usage_obj.get("input_tokens") or 0),
                    "completion_tokens": int(usage_obj.get("output_tokens") or 0),
                    "total_tokens": int(usage_obj.get("total_tokens") or 0),
                })
        except Exception:
            pass
        ts_response = time.time()
        try:
            append_request_log({
                "event": "interaction",
                "ts_request": ts_request,
                "ts_response": ts_response,
                "latency_ms": int((ts_response - ts_request) * 1000),
                "task_id": getattr(self, "task_id", "") or "",
                "adapter": ADAPTER,
                "endpoint": "/responses",
                "status_code": 200,
                "model": str((response_payload or {}).get("model") or "") if isinstance(response_payload, dict) else "",
                "request": {
                    "client": _truncate_for_log(payload),
                    "upstream": _truncate_for_log(upstream_payload),
                },
                "response": {
                    "upstream": _truncate_for_log(chat_payload),
                    "client": _truncate_for_log(response_payload),
                },
                "usage": usage_obj if isinstance(usage_obj, dict) else {},
            })
        except Exception:
            pass
        if bool(payload.get("stream", True)):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self._send_sse_event({"type": "response.created", "response": {**response_payload, "status": "in_progress", "output": []}})
            for output_index, output_item in enumerate(response_payload.get("output") or []):
                item_type = output_item.get("type", "message")
                item_id = output_item.get("id") or output_item.get("call_id") or message_id
                if item_type == "function_call":
                    self._send_sse_event({
                        "type": "response.output_item.added",
                        "output_index": output_index,
                        "item": {**output_item, "status": "in_progress"},
                    })
                    self._send_sse_event({
                        "type": "response.function_call_arguments.delta",
                        "output_index": output_index,
                        "item_id": item_id,
                        "delta": output_item.get("arguments", "{}"),
                    })
                    self._send_sse_event({
                        "type": "response.function_call_arguments.done",
                        "output_index": output_index,
                        "item_id": item_id,
                        "arguments": output_item.get("arguments", "{}"),
                    })
                    self._send_sse_event({
                        "type": "response.output_item.done",
                        "output_index": output_index,
                        "item": output_item,
                    })
                else:
                    self._send_sse_event({
                        "type": "response.output_item.added",
                        "output_index": output_index,
                        "item": {"id": item_id, "type": "message", "status": "in_progress", "role": "assistant", "content": []},
                    })
                    content_items = output_item.get("content") or [{"type": "output_text", "text": output_text}]
                    for ci, part in enumerate(content_items):
                        part_text = part.get("text", "")
                        self._send_sse_event({"type": "response.content_part.added", "output_index": output_index, "item_id": item_id, "content_index": ci, "part": {"type": "output_text", "text": ""}})
                        self._send_sse_event({"type": "response.output_text.delta", "output_index": output_index, "item_id": item_id, "content_index": ci, "delta": part_text})
                        self._send_sse_event({"type": "response.output_text.done", "output_index": output_index, "item_id": item_id, "content_index": ci, "text": part_text})
                        self._send_sse_event({"type": "response.content_part.done", "output_index": output_index, "item_id": item_id, "content_index": ci, "part": {"type": "output_text", "text": part_text}})
                    self._send_sse_event({"type": "response.output_item.done", "output_index": output_index, "item": output_item})
            self._send_sse_event({"type": "response.completed", "response": response_payload})
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            self.close_connection = True
            return
        self._send_json(200, response_payload)

    def _forward(self):
        # Strip the per-task ``/_t/<id>`` prefix BEFORE any other processing
        # so every downstream helper (path matchers, request_url,
        # upstream_chat_url, debug logging) sees the canonical API path.
        # ``self.task_id`` is then propagated into every usage/interaction
        # event for per-task ledger filtering.
        self.task_id, self.path = extract_task_id(self.path)
        ts_request = time.time()
        # Stash the request-side timestamp on the handler so
        # ``_handle_responses_via_chat`` can compute latency_ms from the
        # same instant the client connected, not just the moment the
        # responses_via_chat bridge took over the body.
        self._ts_request = ts_request
        body = b""
        length = int(self.headers.get("Content-Length") or 0)
        if length > 0:
            body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        event = {
            "path": self.path,
            "method": self.command,
            "content_type": content_type,
            "adapter": ADAPTER,
            "task_id": self.task_id,
            "dropped": [],
        }
        path_without_query = urllib.parse.urlsplit(self.path).path.rstrip("/")
        # Captured from the parsed JSON body (when present) so the optional
        # key-rotation gate below can decide whether to rotate. Defaults to
        # "" when the body is missing / not JSON / not a dict.
        request_model = ""
        if ADAPTER == "responses_via_chat" and self.command == "POST" and path_without_query.endswith("/responses"):
            try:
                self._handle_responses_via_chat(body)
                return
            except Exception as exc:
                append_log({**event, "responses_via_chat_error": str(exc)})
                self._send_json(500, {"error": {"message": str(exc)}})
                return
        if ADAPTER in {"drop_max_tokens", "responses_via_chat"} and body and "json" in content_type.lower():
            try:
                payload = json.loads(body.decode("utf-8"))
                if isinstance(payload, dict):
                    request_model = str(payload.get("model") or "")
                    if inject_cached_tool_call_extras(payload):
                        event["injected_cached_tool_call_extras"] = True
                    payload, rewrite_event = sanitize_chat_payload(payload)
                    event.update({key: value for key, value in rewrite_event.items() if key not in {"dropped"}})
                    event["dropped"] = rewrite_event.get("dropped") or []
                    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                append_log(event)
            except Exception:
                append_log({**event, "json_error": True})
                pass
        else:
            append_log(event)
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection"}
        }
        # Optional key rotation gate. ONLY when: drop_max_tokens adapter, a
        # rotator was successfully built, this is a POST to /chat/completions,
        # and the parsed model matches CLAWBENCH_ROTATE_MODELS. Everything else
        # takes the verbatim single-attempt path with inbound Authorization.
        rotate = (
            ADAPTER == "drop_max_tokens"
            and ROTATOR is not None
            and self.command == "POST"
            and path_without_query.endswith("/chat/completions")
            and _is_rotated_model(request_model)
        )
        pool = ROTATOR.order() if rotate else []
        if pool:
            base = {k: v for k, v in headers.items() if k.lower() != "authorization"}
            n = len(pool)
            for i, key in enumerate(pool):
                attempt_headers = dict(base)
                attempt_headers["Authorization"] = "Bearer " + key
                result = self._attempt_upstream(
                    attempt_headers, body, ts_request, path_without_query, event,
                    allow_retry=(i < n - 1),
                )
                if result == "done":
                    return
                # got a 429 with retries remaining: cool this key, try next
                ROTATOR.mark_hot(key)
            return
        self._attempt_upstream(headers, body, ts_request, path_without_query, event, allow_retry=False)
        return

    def _attempt_upstream(self, headers, body, ts_request, path_without_query, event, *, allow_retry):
        """Single upstream attempt with the given ``headers``.

        Builds the request, calls upstream, and relays the response to the
        client (success or error) using the exact relay logic that previously
        lived inline in ``_forward``. Returns:

        - ``"done"``  — the response was relayed to the client (success, OR an
          error that we are NOT retrying); the caller must stop.
        - ``"retry"`` — got a 429 AND ``allow_retry`` is True; the error body
          was drained and NOT relayed so the caller can retry with another key.
        """
        req = urllib.request.Request(
            request_url(self.path),
            data=body if self.command not in {"GET", "HEAD"} else None,
            headers=headers,
            method=self.command,
        )
        try:
            with urllib.request.urlopen(req, timeout=600, context=TLS_CONTEXT) as resp:
                data = resp.read()
                if self.command == "POST" and path_without_query.endswith("/chat/completions"):
                    try:
                        cache_tool_call_extras_from_bytes(data)
                    except Exception:
                        pass
                    usage_logged = False
                    # Fast path: non-streaming response. Whole body is
                    # one JSON object with an optional ``usage`` key.
                    try:
                        chat_resp = json.loads(data.decode("utf-8")) if data else None
                        if isinstance(chat_resp, dict):
                            usage_obj = chat_resp.get("usage")
                            if isinstance(usage_obj, dict) and (usage_obj.get("total_tokens") or usage_obj.get("prompt_tokens") or usage_obj.get("completion_tokens")):
                                append_log({
                                    "event": "usage",
                                    "ts": time.time(),
                                    # See the ``/responses`` branch above for
                                    # why the adapter kind must appear on
                                    # every usage event — role attribution
                                    # in ``append_{executor,role}_usage_
                                    # ledger`` filters on exactly this field.
                                    "adapter": ADAPTER,
                                    "task_id": getattr(self, "task_id", "") or "",
                                    "endpoint": "/chat/completions",
                                    "model": str(chat_resp.get("model") or ""),
                                    "prompt_tokens": int(usage_obj.get("prompt_tokens") or 0),
                                    "completion_tokens": int(usage_obj.get("completion_tokens") or 0),
                                    "total_tokens": int(usage_obj.get("total_tokens") or 0),
                                })
                                usage_logged = True
                    except Exception:
                        pass
                    # Slow path: SSE-streamed response (``stream:
                    # true``). Body is a sequence of ``data: <json>\n\n``
                    # lines terminating with ``data: [DONE]``. When
                    # ``sanitize_chat_payload`` injected
                    # ``stream_options.include_usage=true`` the upstream
                    # emits a chunk whose ``usage`` field has the final
                    # token counts — we scan for the LAST such chunk.
                    if not usage_logged:
                        try:
                            text = data.decode("utf-8") if data else ""
                            if "data:" in text:
                                final_usage = None
                                final_model = ""
                                for raw_line in text.split("\n"):
                                    raw_line = raw_line.strip()
                                    if not raw_line.startswith("data:"):
                                        continue
                                    payload_str = raw_line[len("data:"):].strip()
                                    if not payload_str or payload_str == "[DONE]":
                                        continue
                                    try:
                                        chunk = json.loads(payload_str)
                                    except Exception:
                                        continue
                                    if not isinstance(chunk, dict):
                                        continue
                                    # ``include_usage`` chunks have a
                                    # top-level ``usage`` AND usually
                                    # empty choices. Keep the last
                                    # non-empty one — streaming impls
                                    # sometimes emit usage in multiple
                                    # chunks and the final is the
                                    # authoritative total.
                                    usage_obj = chunk.get("usage")
                                    if isinstance(usage_obj, dict) and (usage_obj.get("total_tokens") or usage_obj.get("prompt_tokens") or usage_obj.get("completion_tokens")):
                                        final_usage = usage_obj
                                        final_model = str(chunk.get("model") or final_model)
                                if final_usage:
                                    append_log({
                                        "event": "usage",
                                        "ts": time.time(),
                                        "adapter": ADAPTER,
                                        "task_id": getattr(self, "task_id", "") or "",
                                        "endpoint": "/chat/completions",
                                        "transport": "sse",
                                        "model": final_model,
                                        "prompt_tokens": int(final_usage.get("prompt_tokens") or 0),
                                        "completion_tokens": int(final_usage.get("completion_tokens") or 0),
                                        "total_tokens": int(final_usage.get("total_tokens") or 0),
                                    })
                                    usage_logged = True
                        except Exception:
                            pass
                # Best-effort full-transcript event: captures the request
                # body (parsed JSON when possible) and response body
                # (parsed JSON for non-streaming, raw text for SSE — the
                # streaming reassembler can recover the assistant message
                # from there) so downstream tooling has a replayable record
                # per call. Disabled when REQUEST_LOG_PATH is empty.
                try:
                    request_payload_for_log = None
                    response_payload_for_log = None
                    response_text_for_log = None
                    request_usage_obj = None
                    if body:
                        try:
                            request_payload_for_log = json.loads(body.decode("utf-8"))
                        except Exception:
                            request_payload_for_log = {"raw": body.decode("utf-8", errors="ignore")}
                    if data:
                        decoded = data.decode("utf-8", errors="ignore")
                        try:
                            response_payload_for_log = json.loads(decoded)
                            if isinstance(response_payload_for_log, dict):
                                request_usage_obj = response_payload_for_log.get("usage")
                        except Exception:
                            response_text_for_log = decoded
                    append_request_log({
                        "event": "interaction",
                        "ts_request": ts_request,
                        "ts_response": time.time(),
                        "latency_ms": int((time.time() - ts_request) * 1000),
                        "task_id": getattr(self, "task_id", "") or "",
                        "adapter": ADAPTER,
                        "endpoint": path_without_query or self.path,
                        "method": self.command,
                        "status_code": resp.status,
                        "request": _truncate_for_log(request_payload_for_log),
                        "response": _truncate_for_log(response_payload_for_log)
                            if response_payload_for_log is not None
                            else _truncate_for_log({"raw_text": response_text_for_log or ""}),
                        "usage": request_usage_obj if isinstance(request_usage_obj, dict) else {},
                    })
                except Exception:
                    pass
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() in {"transfer-encoding", "connection", "content-length"}:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(data)
            return "done"
        except urllib.error.HTTPError as err:
            data = err.read()
            # Key-rotation failover: a retryable 429 is NOT relayed —
            # we drain the body and signal the caller to try the next key.
            if allow_retry and err.code == 429:
                return "retry"
            append_log({**event, "http_error_status": err.code, "response_bytes": len(data or b"")})
            if self.command == "POST" and path_without_query.endswith("/chat/completions"):
                try:
                    request_payload = json.loads(body.decode("utf-8")) if body else {}
                except Exception:
                    request_payload = {"raw": body.decode("utf-8", errors="ignore")}
                dump_debug_payload("proxy_adapter_failed_request.json", request_payload)
                if data:
                    try:
                        response_payload = json.loads(data.decode("utf-8"))
                    except Exception:
                        response_payload = {"raw": data.decode("utf-8", errors="ignore")}
                    dump_debug_payload("proxy_adapter_failed_response.json", response_payload)
            try:
                err_request_payload = None
                err_response_payload = None
                if body:
                    try:
                        err_request_payload = json.loads(body.decode("utf-8"))
                    except Exception:
                        err_request_payload = {"raw": body.decode("utf-8", errors="ignore")}
                if data:
                    try:
                        err_response_payload = json.loads(data.decode("utf-8"))
                    except Exception:
                        err_response_payload = {"raw": data.decode("utf-8", errors="ignore")}
                append_request_log({
                    "event": "interaction",
                    "ts_request": ts_request,
                    "ts_response": time.time(),
                    "latency_ms": int((time.time() - ts_request) * 1000),
                    "task_id": getattr(self, "task_id", "") or "",
                    "adapter": ADAPTER,
                    "endpoint": path_without_query or self.path,
                    "method": self.command,
                    "status_code": err.code,
                    "request": _truncate_for_log(err_request_payload) if err_request_payload is not None else None,
                    "response": _truncate_for_log(err_response_payload) if err_response_payload is not None else None,
                    "error": True,
                })
            except Exception:
                pass
            self.send_response(err.code)
            for key, value in err.headers.items():
                if key.lower() in {"transfer-encoding", "connection", "content-length"}:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            return "done"

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_PATCH = _forward
    do_DELETE = _forward
    do_HEAD = _forward
    do_OPTIONS = _forward


def main() -> None:
    """Entrypoint when invoked as ``python3 -m lib.proxy.adapter_server ...``.

    Reads argv into module-level globals so the existing function /
    Handler bodies continue to reference them as before, then starts a
    ``ThreadingHTTPServer`` bound to ``LISTEN_HOST:LISTEN_PORT`` with
    ``Handler`` as the request handler.  Does not return.
    """
    global LISTEN_HOST, LISTEN_PORT, UPSTREAM_BASE, ADAPTER, LOG_PATH, REQUEST_LOG_PATH, ROTATOR, ROTATE_KEY_ENV_VARS
    LISTEN_HOST = sys.argv[1]
    LISTEN_PORT = int(sys.argv[2])
    UPSTREAM_BASE = sys.argv[3].rstrip("/")
    ADAPTER = sys.argv[4]
    LOG_PATH = sys.argv[5]
    REQUEST_LOG_PATH = sys.argv[6] if len(sys.argv) > 6 else ""
    # Build the optional key rotator for the executor-side adapter ONLY. The
    # :9002 responses_via_chat process must never build one. Fail-safe: any
    # error -> ROTATOR stays None -> no rotation, verbatim forwarding.
    if ADAPTER == "drop_max_tokens":
        try:
            ROTATE_KEY_ENV_VARS = _rotation_key_env_vars()
            keys = _load_rotation_keys(ROTATE_KEY_ENV_VARS)
            cooldown = float(os.environ.get("CLAWBENCH_ROTATE_KEY_COOLDOWN_S", "20.0"))
            ROTATOR = KeyRotator(keys, cooldown_s=cooldown)
            append_log({
                "event": "key_rotator_init",
                "adapter": ADAPTER,
                "key_count": len(ROTATOR),
                "env_vars": list(ROTATE_KEY_ENV_VARS),
            })
        except Exception as exc:
            ROTATOR = None
            ROTATE_KEY_ENV_VARS = ()
            append_log({"event": "key_rotator_init_failed", "adapter": ADAPTER, "error": str(exc)})
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
