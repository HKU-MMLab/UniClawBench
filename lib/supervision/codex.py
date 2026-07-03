"""Codex runtime: container invocation, provider resolution, prompt helpers.

Extracted from ``supervision/common.py`` so the codex-specific pieces
(provider selection, isolated ``CODEX_HOME`` rendering, container-side
``docker run`` invocation, JSON-response parsing retry loop, template
caching) can be read on their own. Non-codex supervision helpers stay in
``common.py`` and this module imports the couple it needs
(``sanitize_codex_context_text``, ``parse_first_json_object``,
``reset_dir``, ``_role_workspace_prompt_files``) lazily inside function
bodies — that lets ``common.py`` re-export the codex names at module top
without a circular import.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ..config_stack import container_visible_value, load_toml_config, parse_env_file
from ..defaults import DEFAULT_CODEX_CONFIG_PATH


ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
_template_cache: dict[str, str] = {}
CONTAINER_SESSION_ROOT = Path("/session")
CONTAINER_WORKDIR = CONTAINER_SESSION_ROOT / "workspace"
CONTAINER_CODEX_HOME = CONTAINER_SESSION_ROOT / "home"
CONTAINER_RUNTIME_DIR = CONTAINER_SESSION_ROOT / "runtime"
DEFAULT_CODEX_IMAGE = os.environ.get("CLAWBENCH_CODEX_IMAGE", "clawbench-codex:latest")
DEFAULT_CODEX_CONFIG = ROOT / DEFAULT_CODEX_CONFIG_PATH
LEGACY_CODEX_BIN = Path("/usr/local/bin/codex")
DEFAULT_CODEX_TIMEOUT_SECONDS = int(os.environ.get("CLAWBENCH_CODEX_TIMEOUT_SECONDS", "300"))
DEFAULT_CODEX_MAX_ATTEMPTS = max(1, int(os.environ.get("CLAWBENCH_CODEX_MAX_ATTEMPTS", "3")))
DEFAULT_CODEX_RETRY_BACKOFF_SECONDS = max(0.0, float(os.environ.get("CLAWBENCH_CODEX_RETRY_BACKOFF_SECONDS", "3")))
# Supervisor / user-simulator 429 retries are bounded but generous: a
# throttled grader should still wait it out rather than crash the
# attempt (rerunning the executor is far more expensive than letting
# the supervisor sleep a minute), but **unbounded** retry can leave a
# task stuck in ``running`` forever when the upstream stays throttled.
# Round 8 / A2 (2026-05-14 review) introduces a hard cap so the
# attempt eventually falls to ``rate_limit`` instead of hanging.
#
# Default ``DEFAULT_CODEX_RATE_LIMIT_RETRIES=10`` mirrors the executor's
# ``DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES`` so the two policies stay
# coherent.  The backoff still grows 1, 2, 4, 8, 16, 32, 60, 60, …
# (capped at ``DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP``), so 10 retries
# roughly bound total wait at ~300s; operators wanting longer
# tolerance set ``CLAWBENCH_CODEX_RATE_LIMIT_RETRIES`` higher.  Setting
# it to 0 makes a single 429 fail immediately (useful in CI).
DEFAULT_CODEX_RATE_LIMIT_RETRIES = max(0, int(os.environ.get("CLAWBENCH_CODEX_RATE_LIMIT_RETRIES", "10")))
DEFAULT_CODEX_RATE_LIMIT_BACKOFF_BASE = max(0.0, float(os.environ.get("CLAWBENCH_CODEX_RATE_LIMIT_BACKOFF_BASE", "1")))
DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP = max(1.0, float(os.environ.get("CLAWBENCH_CODEX_RATE_LIMIT_BACKOFF_CAP", "60")))

# Wall-clock cap on a SINGLE ``run_codex_prompt`` call (incl. all retries).
# Without it, a 429 / timeout retry storm can burn up to
# ``DEFAULT_CODEX_RATE_LIMIT_RETRIES`` * ``DEFAULT_CODEX_TIMEOUT_SECONDS``
# (~10*300=3000s) PLUS backoff — exceeding the ``run_eval`` watchdog grace
# (``max_total_seconds`` + 1800s). That wedges the whole eval process until
# ``os._exit(124)``, which ``worker_runner`` then mislabels ``global_timeout``
# (and discards the executor's already-produced answer). With this cap the
# retry loop surrenders well before the watchdog and raises
# ``CodexRateLimitExhausted`` so ``evaluate_attempt`` records a CLEAN
# ``rate_limit`` terminal (with score.json) instead of wedging. Default 900s
# (~3 per-call timeouts) ≈ the transient ``DEFAULT_CODEX_MAX_ATTEMPTS`` budget;
# set ``CLAWBENCH_CODEX_TOTAL_BUDGET_SECONDS=0`` to restore the old
# count-only behaviour.
DEFAULT_CODEX_TOTAL_BUDGET_SECONDS = max(0, int(os.environ.get("CLAWBENCH_CODEX_TOTAL_BUDGET_SECONDS", "900")))


def codex_call_budget_exceeded(
    started_at: float,
    *,
    rate_limit_retries: int,
    transient_retries: int,
    now: float,
    budget_seconds: int | None = None,
) -> bool:
    """True when a single ``run_codex_prompt`` call has consumed its wall-clock
    budget across retries and must surrender so the caller can record a clean
    terminal BEFORE the ``run_eval`` watchdog force-kills the wedged process.

    Never trips before the first real attempt completes (``rate_limit_retries``
    and ``transient_retries`` both 0) — we always allow one full call. A
    ``budget_seconds`` of 0 disables the guard (legacy count-only behaviour).
    """
    budget = DEFAULT_CODEX_TOTAL_BUDGET_SECONDS if budget_seconds is None else budget_seconds
    if budget <= 0:
        return False
    if rate_limit_retries <= 0 and transient_retries <= 0:
        return False
    return (now - started_at) >= budget


class CodexRateLimitExhausted(RuntimeError):
    """Raised when ``run_codex_prompt`` exhausts its rate-limit retry budget.

    Carries the original 429 detail string so callers
    (``evaluate_attempt`` → ``detect_supervisor_infra_error``) recognise
    it as a ``rate_limit`` outcome rather than a generic infra error.
    The message intentionally embeds the word ``rate_limit`` so the
    needle-based detector matches.
    """
TRANSIENT_CODEX_ERROR_NEEDLES = (
    "stream disconnected before completion",
    "stream closed",
    "connection reset",
    "connection aborted",
    "server disconnected",
    "remoteprotocolerror",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "bad gateway",
    "service unavailable",
    "internal server error",
    "connection refused",
    "eof occurred in violation of protocol",
    "ssl",
    "urlopen error",
    "gateway closed",
)
# HTTP 429 / rate-limit markers a supervisor or user-simulator codex call
# emits when the upstream provider throttles. Kept tight — each needle must
# be specific enough that innocuous content (e.g. a skill doc describing 429
# handling) cannot false-positive. When a match fires the retry loop takes
# the UNBOUNDED rate-limit branch instead of consuming the 3-attempt
# transient budget.
RATE_LIMIT_CODEX_ERROR_NEEDLES = (
    "429",
    "rate limit",
    "rate_limited",
    "rate-limited",
    "rate_limit_error",
    "rate_limit_exceeded",
    "too many requests",
)
TOOLLESS_RETRY_NEEDLES = (
    # Keep these tight: each needle must be specific enough that it cannot
    # accidentally match innocuous content in the error body (e.g. a JSON
    # dump of runtime_probe.json contains "bash -lc python3" and shell=True,
    # which previously tripped "bash" / "sh:" and wasted retries on toolless
    # mode when the actual failure was a network / upstream issue).
    "landlock sandbox",
    "seccomp",
    "operation not permitted",
    "failed to spawn",
    "permission denied",
)


def is_transient_codex_error(*texts: str) -> bool:
    haystack = " | ".join(str(text or "").strip().lower() for text in texts if str(text or "").strip())
    if not haystack:
        return False
    return any(needle in haystack for needle in TRANSIENT_CODEX_ERROR_NEEDLES)
def should_force_toolless_retry(*texts: str) -> bool:
    haystack = " | ".join(str(text or "").strip().lower() for text in texts if str(text or "").strip())
    if not haystack:
        return False
    return any(needle in haystack for needle in TOOLLESS_RETRY_NEEDLES)


def is_rate_limit_codex_error(*texts: str) -> bool:
    """True if any of ``texts`` contains an HTTP 429 / rate-limit marker.

    Used by ``run_codex_prompt``'s retry loop to route 429 failures into
    the unbounded-retry branch instead of consuming the 3-attempt
    transient budget (supervisor / user-simulator policy: retry until the
    upstream clears).
    """
    haystack = " | ".join(str(text or "").strip().lower() for text in texts if str(text or "").strip())
    if not haystack:
        return False
    return any(needle in haystack for needle in RATE_LIMIT_CODEX_ERROR_NEEDLES)


def codex_retry_backoff_seconds(attempt_index: int) -> float:
    if DEFAULT_CODEX_RETRY_BACKOFF_SECONDS <= 0:
        return 0.0
    return min(20.0, DEFAULT_CODEX_RETRY_BACKOFF_SECONDS * (2**max(0, attempt_index)))


def codex_rate_limit_backoff_seconds(retry_index: int) -> float:
    """Exponential backoff for supervisor / user-simulator 429 retries.

    Returns 1, 2, 4, 8, 16, 32, 60, 60, ... capped at
    ``DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP`` (default 60s). Unlike
    ``codex_retry_backoff_seconds`` this series is meant to be driven by
    an unbounded counter — the caller decides when to stop.
    """
    if DEFAULT_CODEX_RATE_LIMIT_BACKOFF_BASE <= 0:
        return 0.0
    return min(
        DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP,
        DEFAULT_CODEX_RATE_LIMIT_BACKOFF_BASE * (2 ** max(0, retry_index)),
    )


def build_codex_execution_prompt(
    prompt: str,
    *,
    retry_error: str = "",
    force_toolless: bool = False,
) -> str:
    from .common import sanitize_codex_context_text

    instructions: list[str] = []
    if force_toolless:
        instructions.append(
            "CRITICAL: respond with exactly one JSON object and no prose outside the JSON object."
        )
        instructions.append(
            "Do not use bash, exec, file inspection, or network tools. Answer only from the workspace files and attached images."
        )
    else:
        instructions.append(
            "Read the workspace files first, then respond with exactly one JSON object and no prose outside the JSON object."
        )
    if retry_error:
        instructions.append(f"Previous attempt failed due to runtime instability: {sanitize_codex_context_text(retry_error)[:600]}")
    parts = ["\n".join(instructions), prompt]
    return "\n\n".join(part for part in parts if part.strip())


def load_codex_base_config(config_path: Path) -> dict[str, Any]:
    loaded = load_toml_config(config_path, base_dir=ROOT)
    if loaded:
        return loaded
    if config_path.resolve() != DEFAULT_CODEX_CONFIG.resolve():
        loaded = load_toml_config(DEFAULT_CODEX_CONFIG, base_dir=ROOT)
        if loaded:
            return loaded
    if os.environ.get("CLAWBENCH_ALLOW_EXAMPLE_CONFIG", "").strip().lower() in {"1", "true", "yes", "on"}:
        example = load_toml_config(ROOT / "configs" / "codex.example.toml", base_dir=ROOT)
        if example:
            return example
    raise FileNotFoundError(
        f"{config_path} is required. Copy configs/codex.example.toml to configs/codex.local.toml "
        "and replace the placeholder provider settings. Set CLAWBENCH_ALLOW_EXAMPLE_CONFIG=1 "
        "only for docs/tests that intentionally exercise the template config."
    )


def codex_env_keys(base_config: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    providers = base_config.get("model_providers") or {}
    if isinstance(providers, dict):
        for provider in providers.values():
            env_key = str((provider or {}).get("env_key") or "").strip()
            if env_key and env_key not in keys:
                keys.append(env_key)
    for key in ("OPENAI_API_KEY", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if key not in keys:
            keys.append(key)
    return keys

def codex_env_file_candidates(base_config_path: Path) -> list[Path]:
    candidates: list[Path] = []
    direct = base_config_path.with_suffix(".env")
    default_local = ROOT / "configs" / "api.local.env"
    paths = [direct, default_local]
    for path in paths:
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def resolve_codex_env_vars(base_config: dict[str, Any], base_config_path: Path) -> dict[str, str]:
    resolved: dict[str, str] = {}
    file_values: dict[str, str] = {}
    for path in codex_env_file_candidates(base_config_path):
        file_values.update(parse_env_file(path))
    for key in codex_env_keys(base_config):
        value = os.environ.get(key)
        if value:
            resolved[key] = value
            continue
        file_value = file_values.get(key)
        if file_value:
            resolved[key] = file_value
    return resolved


def required_codex_env_keys(base_config: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    providers = base_config.get("model_providers") or {}
    if isinstance(providers, dict):
        for provider in providers.values():
            env_key = str((provider or {}).get("env_key") or "").strip()
            if env_key and env_key not in keys:
                keys.append(env_key)
    return keys


def _codex_provider_matches(name: str, provider_name: str, provider_cfg: dict[str, Any]) -> bool:
    candidate = str(name or "").strip()
    if not candidate:
        return False
    if candidate == provider_name:
        return True
    return candidate == str(provider_cfg.get("name") or "").strip()


def _codex_provider_models(provider_cfg: dict[str, Any]) -> list[str]:
    values = provider_cfg.get("models") or []
    result: list[str] = []
    if not isinstance(values, list):
        return result
    for item in values:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            for key in ("id", "name", "model"):
                value = str(item.get(key) or "").strip()
                if value:
                    result.append(value)
    return result


def _validate_codex_provider_model(provider_name: str, provider_cfg: dict[str, Any], model: str) -> str:
    raw_model = str(model or "").strip()
    declared = _codex_provider_models(provider_cfg)
    if not declared:
        return raw_model
    lookup = {item.lower(): item for item in declared}
    canonical = lookup.get(raw_model.lower())
    if canonical:
        return canonical
    hint = ", ".join(declared[:12])
    raise ValueError(
        f"unknown codex model {raw_model!r} for provider {provider_name!r}; "
        f"available models include: {hint or '(none declared)'}"
    )


def resolve_codex_provider(base: dict[str, Any], *, model: str, provider: str = "") -> tuple[str, str]:
    providers = dict(base.get("model_providers") or {})
    raw_model = str(model or "").strip()
    raw_provider = str(provider or "").strip()
    if not providers:
        raise ValueError("no codex model providers configured")
    if not raw_model:
        raise ValueError("empty codex model; set `model` for the role")
    if raw_provider:
        for provider_name, provider_cfg in providers.items():
            cfg = dict(provider_cfg or {})
            if _codex_provider_matches(raw_provider, provider_name, cfg):
                return provider_name, _validate_codex_provider_model(
                    provider_name,
                    cfg,
                    raw_model.partition("/")[2] or raw_model,
                )
        raise ValueError(f"unknown codex model provider {raw_provider!r}")
    if "/" in raw_model:
        prefix, _, stripped = raw_model.partition("/")
        for provider_name, provider_cfg in providers.items():
            cfg = dict(provider_cfg or {})
            if _codex_provider_matches(prefix, provider_name, cfg):
                return provider_name, _validate_codex_provider_model(provider_name, cfg, stripped)
        raise ValueError(f"unknown codex model provider {prefix!r} for model {raw_model!r}")
    for provider_name, provider_cfg in providers.items():
        cfg = dict(provider_cfg or {})
        canonical = {item.lower(): item for item in _codex_provider_models(cfg)}.get(raw_model.lower())
        if canonical:
            return provider_name, canonical
    fallback = str(base.get("model_provider") or "").strip()
    if fallback and fallback in providers:
        provider_cfg = dict(providers.get(fallback) or {})
        return fallback, _validate_codex_provider_model(fallback, provider_cfg, raw_model)
    hint = ", ".join(str(name) for name in providers.keys())
    raise ValueError(
        f"unknown codex model {raw_model!r}; configure it under one of the model_providers"
        + (f": {hint}" if hint else "")
    )


def render_codex_config(base: dict[str, Any], *, model: str, provider: str = "", workspace_root: str | Path) -> str:
    provider_name, resolved_model = resolve_codex_provider(base, model=model, provider=provider)
    providers = dict(base.get("model_providers") or {})
    provider = dict(providers.get(provider_name) or {})
    provider.setdefault("name", provider_name)
    provider.setdefault("base_url", "http://127.0.0.1:9001/v1/openai/native")
    provider.setdefault("env_key", "PROXY_EXAMPLE_API_KEY")
    provider.setdefault("wire_api", "responses")
    provider["base_url"] = container_visible_value(str(provider.get("base_url") or ""))
    supports_ws = "true" if provider.get("supports_websockets") else "false"
    workspace_value = str(workspace_root)
    # Codex supports two top-level keys that drive its built-in conversation
    # compaction loop:
    #   model_context_window          — model's actual max input token capacity
    #   model_auto_compact_token_limit — threshold at which Codex preemptively
    #                                    rewrites the conversation with a
    #                                    summarized "compact_prompt" before the
    #                                    next API request
    # Without these set, Codex doesn't know when to compact and will just let
    # the conversation grow until the provider returns 422
    # context_length_exceeded (observed: supervisor runs hitting
    # "Input tokens exceed the configured limit of 272000 tokens" at 387-611K
    # after 4-5 view_image tool calls). 272000 is a conservative default for
    # large-context providers; override via env if your provider is
    # different. The compaction threshold defaults to ~80% of the window so
    # there's headroom for the compaction request itself.
    default_window = int(os.environ.get("CLAWBENCH_CODEX_MODEL_CONTEXT_WINDOW", "272000"))
    default_compact = int(os.environ.get(
        "CLAWBENCH_CODEX_MODEL_AUTO_COMPACT_TOKEN_LIMIT",
        str(int(default_window * 0.8)),
    ))
    return (
        f'model_provider = "{provider_name}"\n'
        f'model = "{resolved_model}"\n'
        f'model_context_window = {default_window}\n'
        f'model_auto_compact_token_limit = {default_compact}\n'
        f'[model_providers.{json.dumps(provider_name)}]\n'
        f'name = "{provider["name"]}"\n'
        f'base_url = "{provider["base_url"]}"\n'
        f'env_key = "{provider["env_key"]}"\n'
        f'wire_api = "{provider["wire_api"]}"\n'
        f'supports_websockets = {supports_ws}\n\n'
        f'[projects."{workspace_value}"]\n'
        'trust_level = "trusted"\n'
    )


def ensure_isolated_codex_home(
    *,
    base_config_path: Path,
    target: Path,
    model: str,
    provider: str = "",
    workspace_root: str | Path,
) -> Path:
    codex_home = target.resolve()
    codex_home.mkdir(parents=True, exist_ok=True)
    base = load_codex_base_config(base_config_path)
    config = render_codex_config(base, model=model, provider=provider, workspace_root=workspace_root)
    config_path = codex_home / "config.toml"
    if not config_path.exists() or config_path.read_text(encoding="utf-8") != config:
        config_path.write_text(config, encoding="utf-8")
    return codex_home


def session_path_to_container(session_root: Path, path: Path) -> str:
    resolved_session = session_root.resolve()
    resolved_path = path.resolve()
    return str(CONTAINER_SESSION_ROOT / resolved_path.relative_to(resolved_session))


def render_template(name: str, variables: dict[str, str]) -> str:
    """Load a prompt template and render with variables.

    Prefers Python module (lib/templates/<name>.py exporting TEMPLATE),
    falls back to plain text file (lib/templates/<name>.txt).
    """
    if name not in _template_cache:
        try:
            import importlib
            mod = importlib.import_module(f".templates.{name}", package="lib")
            _template_cache[name] = mod.TEMPLATE
        except (ImportError, AttributeError):
            _template_cache[name] = (_TEMPLATE_DIR / f"{name}.txt").read_text(encoding="utf-8")
    return _template_cache[name].format_map(variables)


def build_session_prompt(
    *,
    role_name: str,
    role_instructions: str,
    workspace_manifest: dict[str, Any],
) -> str:
    from .common import _role_workspace_prompt_files

    # Round 16 / P2-2: thread privacy_available so the answer_supervisor
    # wrapper prompt mentions ``privacy/`` whenever the workspace
    # manifest actually carries privacy assets.  Without this the
    # ``Start Here`` list in build_role_workspace_readme included
    # ``privacy/`` but the session prompt wrapper did not — supervisors
    # had to discover the privacy directory by reading the README.
    has_privacy = bool(workspace_manifest.get("privacy_available"))
    # Cap is large enough to hold every entry returned by
    # ``_role_workspace_prompt_files`` for any role (answer_supervisor
    # with privacy hits 13 entries).  Keep the slice as a defensive guard
    # against future role additions, but match the worst-case length so
    # ``privacy/`` is never the entry that falls off the end.
    key_files = [
        str(item)
        for item in _role_workspace_prompt_files(role_name, has_privacy=has_privacy)
    ][:16]
    return render_template("session_wrapper", {
        "role_name": role_name,
        "role_instructions": role_instructions.strip(),
        "key_files_list": "\n".join(f"- `{path}`" for path in key_files),
    })


def run_codex_via_container(
    *,
    prompt: str,
    session_root: Path,
    workspace_root: Path,
    codex_home: Path,
    reasoning_effort: str,
    output_path: Path,
    output_schema_path: Path | None,
    images: list[Path],
    env_vars: dict[str, str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    resolved_session_root = session_root.resolve()
    command = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--privileged",
        "--add-host",
        f"host.docker.internal:{os.environ.get('CLAWBENCH_HOST_GATEWAY', 'host-gateway').strip()}",
        "-e",
        f"CODEX_HOME={session_path_to_container(resolved_session_root, codex_home)}",
        "-v",
        f"{resolved_session_root}:{CONTAINER_SESSION_ROOT}",
        "-w",
        str(CONTAINER_WORKDIR),
    ]
    for key, value in env_vars.items():
        if value:
            command.extend(["-e", f"{key}={value}"])
    command.extend(
        [
            DEFAULT_CODEX_IMAGE,
            str(LEGACY_CODEX_BIN),
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "-C",
            session_path_to_container(resolved_session_root, workspace_root),
            "--output-last-message",
            session_path_to_container(resolved_session_root, output_path),
            "--color",
            "never",
            "-c",
            f'model_reasoning_effort="{reasoning_effort}"',
        ]
    )
    if output_schema_path is not None:
        command.extend(["--output-schema", session_path_to_container(resolved_session_root, output_schema_path)])
    # Pre-attach every workspace image as a codex ``--image`` flag only when the
    # operator opts in via env flag. Default is OFF: the role's prompt instead
    # directs it to inspect images on demand with the built-in ``view_image``
    # tool, which drastically shrinks the request payload and avoids 180s
    # codex timeouts on image-heavy runs. Set
    #   CLAWBENCH_CODEX_ATTACH_IMAGES=1
    # to restore the legacy pre-attach behavior.
    if os.environ.get("CLAWBENCH_CODEX_ATTACH_IMAGES", "0").strip() not in {"", "0", "false", "False", "no", "off"}:
        for image in images:
            command.extend(["--image", session_path_to_container(resolved_session_root, image)])
    command.append("-")
    return subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
        cwd=ROOT,
        env=dict(os.environ),
        timeout=max(30, int(timeout_seconds)),
    )


def latest_codex_rollout_log(codex_home: Path) -> Path | None:
    sessions_root = codex_home / "sessions"
    if not sessions_root.exists():
        return None
    logs = sorted((path for path in sessions_root.rglob("rollout-*.jsonl") if path.is_file()), key=lambda path: path.stat().st_mtime)
    return logs[-1] if logs else None


def codex_rollout_summary(codex_home: Path) -> dict[str, Any]:
    log_path = latest_codex_rollout_log(codex_home)
    if not log_path or not log_path.exists():
        return {}
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    # ``view_image`` used to be treated as a tool-misuse signal because, with
    # pre-attached images, a role calling view_image meant it was fighting the
    # attached context. Now that we deliberately ship workspace files and ask
    # the role to inspect images on demand, view_image is the EXPECTED path.
    # Only real failure signatures remain here.
    tool_needles = ["failed to parse function arguments"]
    return {
        "path": str(log_path),
        "tool_misuse_detected": any(needle in text for needle in tool_needles),
        "excerpt": text[-4000:],
    }


def run_codex_prompt(
    *,
    prompt: str,
    model: str,
    provider: str,
    base_config_path: Path,
    session_root: Path,
    workspace_root: Path,
    codex_home: Path,
    reasoning_effort: str,
    images: list[Path],
    workspace_manifest: dict[str, Any] | None = None,
    workspace_readme: str = "",
    output_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .common import parse_first_json_object, reset_dir

    tmp_dir = reset_dir(session_root / "runtime")
    output_path = tmp_dir / "result.json"
    output_schema_path: Path | None = None
    started_at = time.time()
    try:
        base = load_codex_base_config(base_config_path)
        provider_name, _ = resolve_codex_provider(base, model=model, provider=provider)
        provider_cfg = dict((base.get("model_providers") or {}).get(provider_name) or {})
        wire_api = str(provider_cfg.get("wire_api") or "responses").strip().lower()
        if output_schema and wire_api == "responses":
            output_schema_path = tmp_dir / "output_schema.json"
            output_schema_path.write_text(json.dumps(output_schema, ensure_ascii=False, indent=2), encoding="utf-8")
        env_vars = resolve_codex_env_vars(base, base_config_path)
        missing_required = [key for key in required_codex_env_keys(base) if not env_vars.get(key)]
        if missing_required:
            env_hint = ", ".join(str(path) for path in codex_env_file_candidates(base_config_path))
            raise RuntimeError(
                "missing codex runtime credentials: "
                + ", ".join(missing_required)
                + f". Set them in the current environment or one of: {env_hint}"
            )
        ensure_isolated_codex_home(
            base_config_path=base_config_path,
            target=codex_home,
            model=model,
            provider=provider,
            workspace_root=CONTAINER_WORKDIR,
        )
        toolless_mode = False
        active_prompt = build_codex_execution_prompt(prompt)
        last_error = "codex execution failed"
        # Two independent retry counters:
        #   attempt_index: consumed by transient transport errors, malformed
        #     JSON, and toolless-mode retries. Capped at
        #     DEFAULT_CODEX_MAX_ATTEMPTS — once exhausted we raise.
        #   rate_limit_retry_count: consumed only by HTTP 429 / rate-limit
        #     responses from the upstream provider. Round 8 / A2: bounded
        #     at DEFAULT_CODEX_RATE_LIMIT_RETRIES (default 10) so a
        #     throttled grader eventually falls to ``rate_limit`` final
        #     status instead of hanging in ``running`` forever. Mirrors
        #     the executor-side ``DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES``.
        attempt_index = 0
        rate_limit_retry_count = 0
        while True:
            # Wall-clock guard: surrender a wedged grader BEFORE the run_eval
            # watchdog (max_total+1800s) force-kills the process. Raising
            # CodexRateLimitExhausted here (message carries a "rate limit"
            # needle) lands in evaluate_attempt's handler -> clean rate_limit
            # terminal with score.json, instead of an os._exit(124) wedge that
            # worker_runner would mislabel as global_timeout.
            if codex_call_budget_exceeded(
                started_at,
                rate_limit_retries=rate_limit_retry_count,
                transient_retries=attempt_index,
                now=time.time(),
            ):
                raise CodexRateLimitExhausted(
                    f"codex wall-clock budget {DEFAULT_CODEX_TOTAL_BUDGET_SECONDS}s "
                    f"exceeded — rate limit / timeout retry storm "
                    f"({rate_limit_retry_count} rate-limit + {attempt_index} transient "
                    f"retries); surrendering before run_eval watchdog"
                )
            output_path.unlink(missing_ok=True)
            try:
                result = run_codex_via_container(
                    prompt=active_prompt,
                    session_root=session_root,
                    workspace_root=workspace_root,
                    codex_home=codex_home,
                    reasoning_effort=reasoning_effort,
                    output_path=output_path,
                    output_schema_path=output_schema_path,
                    images=images,
                    env_vars=env_vars,
                    timeout_seconds=DEFAULT_CODEX_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                rollout = codex_rollout_summary(codex_home)
                last_error = f"codex execution timeout after {DEFAULT_CODEX_TIMEOUT_SECONDS}s"
                detail = rollout.get("excerpt") or str(exc)
                # A timeout can itself be a symptom of upstream throttling
                # (provider stalls the stream on 429). If the rollout log
                # carries 429 markers, take the rate-limit branch so we
                # keep retrying instead of burning the transient budget.
                if is_rate_limit_codex_error(detail, last_error):
                    if rate_limit_retry_count >= DEFAULT_CODEX_RATE_LIMIT_RETRIES:
                        raise CodexRateLimitExhausted(
                            f"codex rate_limit retries exhausted after "
                            f"{rate_limit_retry_count} attempts (timeout path): {detail}"
                        ) from exc
                    sleep_for = codex_rate_limit_backoff_seconds(rate_limit_retry_count)
                    print(
                        f"[codex] rate_limit retry #{rate_limit_retry_count + 1}"
                        f"/{DEFAULT_CODEX_RATE_LIMIT_RETRIES} (timeout) — sleeping {sleep_for:.1f}s",
                        flush=True,
                    )
                    time.sleep(sleep_for)
                    rate_limit_retry_count += 1
                    active_prompt = build_codex_execution_prompt(
                        prompt, retry_error=detail, force_toolless=toolless_mode,
                    )
                    continue
                if attempt_index + 1 < DEFAULT_CODEX_MAX_ATTEMPTS:
                    time.sleep(codex_retry_backoff_seconds(attempt_index))
                    toolless_mode = toolless_mode or should_force_toolless_retry(detail, last_error)
                    active_prompt = build_codex_execution_prompt(
                        prompt,
                        retry_error=detail or last_error,
                        force_toolless=toolless_mode,
                    )
                    attempt_index += 1
                    continue
                raise RuntimeError(f"{last_error}. rollout={rollout.get('path','')} detail={detail}") from exc
            if result.returncode == 0 and output_path.exists():
                raw_response = output_path.read_text(encoding="utf-8")
                try:
                    parsed = parse_first_json_object(raw_response)
                except Exception as exc:
                    rollout = codex_rollout_summary(codex_home)
                    last_error = f"failed to parse codex JSON response: {exc}"
                    if attempt_index + 1 < DEFAULT_CODEX_MAX_ATTEMPTS:
                        time.sleep(codex_retry_backoff_seconds(attempt_index))
                        retry_detail = rollout.get("excerpt") or last_error
                        toolless_mode = toolless_mode or should_force_toolless_retry(retry_detail, last_error)
                        active_prompt = build_codex_execution_prompt(
                            prompt,
                            retry_error=retry_detail,
                            force_toolless=toolless_mode,
                        )
                        attempt_index += 1
                        continue
                    raise RuntimeError(f"{last_error}. rollout={rollout.get('path','')} detail={rollout.get('excerpt','')}") from exc
                return {
                    "parsed": parsed,
                    "transport": "codex_container",
                    "elapsed_ms": int((time.time() - started_at) * 1000),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "raw_response": raw_response,
                    "prompt": active_prompt,
                    "image_inputs": [str(path) for path in images],
                    "workspace_manifest": workspace_manifest or {},
                    "workspace_readme": workspace_readme,
                    "workspace_root": str(workspace_root),
                }
            rollout = codex_rollout_summary(codex_home)
            last_error = result.stderr.strip() or result.stdout.strip() or "codex execution failed"
            retry_detail = rollout.get("excerpt") or last_error
            # Rate-limit branch FIRST — 429 retries don't consume attempt_index
            # so a genuine provider throttle can't deadlock with a separate
            # transient error by starving the other's budget.
            if is_rate_limit_codex_error(last_error, retry_detail):
                if rate_limit_retry_count >= DEFAULT_CODEX_RATE_LIMIT_RETRIES:
                    raise CodexRateLimitExhausted(
                        f"codex rate_limit retries exhausted after "
                        f"{rate_limit_retry_count} attempts: {retry_detail}"
                    )
                sleep_for = codex_rate_limit_backoff_seconds(rate_limit_retry_count)
                print(
                    f"[codex] rate_limit retry #{rate_limit_retry_count + 1}"
                    f"/{DEFAULT_CODEX_RATE_LIMIT_RETRIES} — sleeping {sleep_for:.1f}s",
                    flush=True,
                )
                time.sleep(sleep_for)
                rate_limit_retry_count += 1
                active_prompt = build_codex_execution_prompt(
                    prompt,
                    retry_error=retry_detail,
                    force_toolless=toolless_mode,
                )
                continue
            if attempt_index + 1 < DEFAULT_CODEX_MAX_ATTEMPTS:
                toolless_mode = toolless_mode or should_force_toolless_retry(last_error, retry_detail) or bool(rollout.get("tool_misuse_detected"))
                if is_transient_codex_error(last_error, retry_detail) or toolless_mode:
                    time.sleep(codex_retry_backoff_seconds(attempt_index))
                active_prompt = build_codex_execution_prompt(
                    prompt,
                    retry_error=retry_detail,
                    force_toolless=toolless_mode,
                )
                attempt_index += 1
                continue
            if not output_path.exists():
                last_error = f"{last_error}. rollout={rollout.get('path','')} detail={rollout.get('excerpt','')}"
            raise RuntimeError(last_error)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
