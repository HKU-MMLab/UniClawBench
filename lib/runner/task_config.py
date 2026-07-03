"""Task spec resolution + model registry helpers.

This module is the "task-config bucket" of the runner package: pure-data
helpers that turn a task YAML + CLI overrides into a fully-resolved
:class:`lib.task.TaskSpec`, and the registry helpers that look model
names up in ``configs/models.local.json``.

Everything here is side-effect-free except:

* :func:`reset_task_run_root` (deletes the run directory)
* :func:`managed_task_proxy_tunnels` (spawns SSH tunnels via ``lib.proxy``)

Kept deliberately small and self-contained — no runtime docker state is
touched — so the unit tests (``tests/test_task_loading.py`` etc.) can
exercise these helpers without any containers.
"""
from __future__ import annotations

import json
import os
import shutil
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..config_stack import load_json_config, merged_env, resolve_config_path
from ..defaults import (
    AGENT_SESSION_ID,
    DEFAULT_IMAGE,
    DEFAULT_IMAGE_BY_AGENT_SYS,
    DEFAULT_MODELS_CONFIG,
    DEFAULT_SHARED_ENV_FILE,
    ROOT,
)
from ..proxy import (
    _ensure_no_adapter_conflict,
    _proxy_spec_key,
    acquire_shared_proxy_tunnel,
    provider_proxy_spec,
    stop_proxy_tunnel,
)
from ..supervision.codex import load_codex_base_config, resolve_codex_provider
from ..task import TaskSpec, load_task, validate_agent_sys
from ..util.model_naming import encode_model_dir


RUNS = ROOT / "runs"

# The nanobot runtime writes its session transcript to a small, fixed list of
# paths inside the container. Kept here (not in ``defaults.py``) because the
# list is only ever consumed by :func:`transcript_targets_for_task`.
NANOBOT_TRANSCRIPT_TARGETS = [
    f"/tmp_workspace/sessions/{AGENT_SESSION_ID}.jsonl",
    "/root/.nanobot/logs/nanobot.log",
    "/tmp_workspace/clawbench/logs/agent.log",
]


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")[:48]


def normalize_agent_sys(value: str) -> str:
    """Path-safe non-strict normaliser for ``agent_sys``.

    Thin wrapper over ``lib.task.canonical_agent_sys(strict=False)``. Most
    callers that build runtime artifact paths from a validated TaskSpec
    can keep using this. Code paths that accept *user* input (CLI flags,
    HTTP query params, etc.) should call
    ``canonical_agent_sys(value, strict=True)`` directly so deprecated
    aliases and unknown backends surface a clear error rather than
    silently producing an unmatchable path.
    """
    from ..task import canonical_agent_sys

    return canonical_agent_sys(value, strict=False)


def default_agent_id_for_agent_sys(agent_sys: str) -> str:
    normalized = normalize_agent_sys(agent_sys)
    if normalized == "openclaw_edict":
        return "taizi"
    if normalized == "nanobot":
        return "nanobot"
    return "main"


def default_image_for_agent_sys(agent_sys: str) -> str:
    return DEFAULT_IMAGE_BY_AGENT_SYS.get(normalize_agent_sys(agent_sys), DEFAULT_IMAGE)


def effective_agent_id_for_task(task: TaskSpec) -> str:
    agent_sys = normalize_agent_sys(task.agent_sys)
    agent_id = (task.agent_id or "").strip()
    if agent_sys == "openclaw_edict" and agent_id in {"", "clawbench-openclaw", "main"}:
        return "taizi"
    if agent_sys == "openclaw" and agent_id in {"", "clawbench-openclaw"}:
        return "main"
    if agent_id:
        return agent_id
    return default_agent_id_for_agent_sys(agent_sys)


def model_slug(model: str) -> str:
    return encode_model_dir(model or "unknown-model")


def strip_model_provider(model: str) -> str:
    raw = str(model or "").strip()
    return raw.partition("/")[2] or raw


def compose_model_ref(model: str, provider: str = "") -> str:
    raw_model = str(model or "").strip()
    raw_provider = str(provider or "").strip()
    if not raw_provider:
        return raw_model
    return f"{raw_provider}/{strip_model_provider(raw_model)}"


def setting_root(agent_sys: str, model: str) -> Path:
    return RUNS / normalize_agent_sys(agent_sys) / model_slug(model)


def task_run_root(task: TaskSpec) -> Path:
    return setting_root(task.agent_sys, task.model) / task.category / task.task_id


def reset_task_run_root(task: TaskSpec) -> Path:
    run_root = task_run_root(task)
    if run_root.exists():
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    return run_root


def override_codex_role_runtime(
    spec,
    *,
    model: str | None = None,
    provider: str | None = None,
    config: str | None = None,
    reasoning_effort: str | None = None,
):
    next_model = spec.model
    next_provider = spec.provider
    if model is not None:
        raw_model = str(model or "").strip()
        if "/" in raw_model and provider is None:
            next_provider, _, next_model = raw_model.partition("/")
        else:
            next_model = strip_model_provider(raw_model)
    if provider is not None:
        next_provider = str(provider or "").strip()
    return replace(
        spec,
        model=next_model,
        provider=next_provider,
        config=str(config or spec.config).strip() if config is not None else spec.config,
        reasoning_effort=str(reasoning_effort or spec.reasoning_effort).strip()
        if reasoning_effort is not None
        else spec.reasoning_effort,
    )


def override_task_runtime(
    task: TaskSpec,
    agent_sys: str | None = None,
    model: str | None = None,
    image_model: str | None = None,
    agent_provider: str | None = None,
    codex_role_overrides: dict[str, dict[str, str | None]] | None = None,
) -> TaskSpec:
    normalized = validate_agent_sys(agent_sys or task.agent_sys, field_name="agent_sys")
    resolved_model = resolve_model_ref(
        compose_model_ref((model or task.model).strip(), agent_provider or ""),
        strict=True,
    )
    explicit_image_model = str(image_model or "").strip()
    if explicit_image_model:
        resolved_image_model = resolve_model_ref(
            compose_model_ref(explicit_image_model, agent_provider or ""),
            strict=True,
        )
    elif model is not None and (not str(task.image_model or "").strip() or strip_model_provider(task.image_model) == strip_model_provider(task.model)):
        resolved_image_model = resolved_model
    else:
        resolved_image_model = resolve_model_ref(str(task.image_model or "").strip(), strict=True)
    codex = task.codex
    if codex_role_overrides:
        next_user_simulator = codex.user_simulator
        next_supervisor = codex.supervisor
        for role, overrides in codex_role_overrides.items():
            if role not in {"user_simulator", "supervisor"}:
                continue
            updated = override_codex_role_runtime(getattr(codex, role), **{key: overrides.get(key) for key in overrides})
            if role == "user_simulator":
                next_user_simulator = updated
            else:
                next_supervisor = updated
        codex = replace(codex, user_simulator=next_user_simulator, supervisor=next_supervisor)
    updated = replace(
        task,
        agent_sys=normalized,
        agent_id=task.agent_id if normalized == normalize_agent_sys(task.agent_sys) else default_agent_id_for_agent_sys(normalized),
        model=resolved_model,
        image_model=resolved_image_model,
        codex=codex,
    )
    return updated


def build_runtime_task_spec(
    task_file: Path,
    *,
    agent_sys: str | None = None,
    model: str | None = None,
    image_model: str | None = None,
    agent_provider: str | None = None,
    codex_role_overrides: dict[str, dict[str, str | None]] | None = None,
) -> TaskSpec:
    return override_task_runtime(
        load_task(task_file.resolve(), ROOT),
        agent_sys=agent_sys,
        model=model,
        image_model=image_model,
        agent_provider=agent_provider,
        codex_role_overrides=codex_role_overrides,
    )


def model_id_for_backend(model: str, agent_sys: str) -> str:
    resolved = resolve_model_ref(model)
    if normalize_agent_sys(agent_sys) == "nanobot" and "/" in resolved:
        return resolved.rsplit("/", 1)[-1]
    return resolved


def _model_registry_hint(providers: dict[str, Any], *, limit: int = 12) -> str:
    names: list[str] = []
    for provider_name, provider_cfg in providers.items():
        for name in _provider_model_names(dict(provider_cfg or {})):
            names.append(f"{provider_name}/{name}")
            if len(names) >= limit:
                break
        if len(names) >= limit:
            break
    return ", ".join(names)


def resolve_model_ref(model: str, payload: dict | None = None, *, strict: bool = False) -> str:
    raw = (model or "").strip()
    if not raw:
        if strict:
            raise ValueError("empty executor model; set `model` in the task or CLI override")
        return raw
    providers = providers_from_models_payload(payload or load_models_payload())
    if "/" in raw:
        provider_name, _, stripped = raw.partition("/")
        provider_cfg = providers.get(provider_name)
        if not isinstance(provider_cfg, dict):
            if strict:
                raise ValueError(f"unknown executor model provider {provider_name!r} for model {raw!r}")
            return raw
        known_names = _provider_model_names(provider_cfg)
        if stripped and known_names:
            lookup = {name.lower(): name for name in known_names}
            canonical = lookup.get(stripped.lower())
            if canonical:
                return f"{provider_name}/{canonical}"
            if strict:
                hint = ", ".join(known_names[:12])
                raise ValueError(
                    f"unknown executor model {stripped!r} for provider {provider_name!r}; "
                    f"available models include: {hint or '(none declared)'}"
                )
        return raw
    needle = raw.lower()
    for provider_name, provider_cfg in providers.items():
        for spec in provider_cfg.get("models") or []:
            model_id = str(spec.get("id") or "").strip()
            model_name = str(spec.get("name") or "").strip()
            if needle in {model_id.lower(), model_name.lower()}:
                return f"{provider_name}/{model_id}"
    if strict:
        hint = _model_registry_hint(providers)
        suffix = f"; available models include: {hint}" if hint else ""
        raise ValueError(
            f"unknown executor model {raw!r}; configure it in configs/models.local.json "
            f"or pass an explicit provider/model ref{suffix}"
        )
    return raw


def transcript_targets_for_task(task: TaskSpec) -> list[str]:
    agent_sys = normalize_agent_sys(task.agent_sys)
    if agent_sys == "nanobot":
        return list(NANOBOT_TRANSCRIPT_TARGETS)
    agent_id = effective_agent_id_for_task(task)
    targets: list[str] = []
    if agent_id:
        targets.append(f"/root/.openclaw/agents/{agent_id}/sessions/{AGENT_SESSION_ID}.jsonl")
    # For EDICT multi-agent runs, the primary agent (太子) frequently delegates
    # work to sub-省 agents via sessions_send/sessions_spawn and then stays idle
    # while they do the real work. The startup-silence monitor must watch *every*
    # EDICT agent's transcript, not just the primary, otherwise legitimate
    # delegation looks like a hung agent and gets SIGTERM-killed.
    if agent_sys == "openclaw_edict":
        # Lazy import: edict_agent_ids still lives in the package __init__
        # until the edict bucket extraction in a later phase.
        from . import edict_agent_ids

        for edict_id in edict_agent_ids():
            targets.append(
                f"/root/.openclaw/agents/{edict_id}/sessions/{AGENT_SESSION_ID}.jsonl"
            )
    targets.extend(
        [
            f"/root/.openclaw/agents/main/sessions/{AGENT_SESSION_ID}.jsonl",
            f"/tmp/openclaw/{AGENT_SESSION_ID}.jsonl",
            f"/tmp/openclaw/sessions/{AGENT_SESSION_ID}.jsonl",
        ]
    )
    deduped: list[str] = []
    for target in targets:
        if target not in deduped:
            deduped.append(target)
    return deduped


def load_models_payload() -> dict:
    env = merged_env(files=[DEFAULT_SHARED_ENV_FILE])
    target = resolve_config_path(DEFAULT_MODELS_CONFIG, env_var="CLAWBENCH_MODELS_CONFIG", base_dir=ROOT)
    if target.exists():
        payload = load_json_config(target, env=env)
        if providers_from_models_payload(payload):
            return payload
        raise ValueError(f"model registry {target} does not declare any providers")
    if _allow_example_config():
        return load_json_config(
            ROOT / "configs" / "models.example.json",
            base_dir=ROOT,
            env=env,
        )
    hint = (
        f"{target} is required. Copy configs/models.example.json to configs/models.local.json "
        "and replace the placeholder providers, or set CLAWBENCH_MODELS_CONFIG to an explicit "
        "registry. Set CLAWBENCH_ALLOW_EXAMPLE_CONFIG=1 only for docs/tests that intentionally "
        "exercise the template config."
    )
    raise FileNotFoundError(hint)


def _allow_example_config() -> bool:
    raw = os.environ.get("CLAWBENCH_ALLOW_EXAMPLE_CONFIG", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def providers_from_models_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    direct = payload.get("providers")
    if isinstance(direct, dict):
        return direct
    nested_models = payload.get("models")
    if isinstance(nested_models, dict):
        nested_providers = nested_models.get("providers")
        if isinstance(nested_providers, dict):
            return nested_providers
    return {}


def _provider_model_names(provider_cfg: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for spec in provider_cfg.get("models") or []:
        if not isinstance(spec, dict):
            continue
        for key in ("id", "name", "model"):
            value = str(spec.get(key) or "").strip()
            if value and value not in names:
                names.append(value)
    return names


def resolve_models_provider_entry(model: str, payload: dict | None = None, *, strict: bool = True) -> tuple[str, dict[str, Any]]:
    providers = providers_from_models_payload(payload or load_models_payload())
    resolved_model = resolve_model_ref(model, payload, strict=strict)
    if "/" in resolved_model:
        provider_name, _, _ = resolved_model.partition("/")
        provider_cfg = providers.get(provider_name)
        if isinstance(provider_cfg, dict):
            return provider_name, dict(provider_cfg)
    stripped = strip_model_provider(resolved_model).lower()
    for provider_name, provider_cfg in providers.items():
        cfg = dict(provider_cfg or {})
        if stripped and stripped in {item.lower() for item in _provider_model_names(cfg)}:
            return provider_name, cfg
    if strict:
        hint = _model_registry_hint(providers)
        suffix = f"; available models include: {hint}" if hint else ""
        raise ValueError(
            f"unknown executor model {model!r}; configure it in configs/models.local.json "
            f"or pass an explicit provider/model ref{suffix}"
        )
    return "", {}


def resolve_model_entry(model: str, payload: dict | None = None) -> dict[str, Any]:
    """Return the per-model entry dict from ``configs/models*.json``.

    Falls back to ``{}`` when the model is unknown. Used by runtime code that
    needs model-specific metadata (e.g. ``quirks`` for backend config injection)
    without coupling to ``substring`` matches in task.model.
    """
    providers = providers_from_models_payload(payload or load_models_payload())
    resolved_model = resolve_model_ref(model, payload, strict=False)
    provider_cfg: dict[str, Any] = {}
    if "/" in resolved_model:
        provider_name, _, _ = resolved_model.partition("/")
        cfg = providers.get(provider_name)
        if isinstance(cfg, dict):
            provider_cfg = dict(cfg)
    if not provider_cfg:
        stripped = strip_model_provider(resolved_model).lower()
        for cfg in providers.values():
            if not isinstance(cfg, dict):
                continue
            names = {item.lower() for item in _provider_model_names(cfg)}
            if stripped and stripped in names:
                provider_cfg = dict(cfg)
                break
    target = strip_model_provider(resolved_model).lower()
    for spec in provider_cfg.get("models") or []:
        if not isinstance(spec, dict):
            continue
        for key in ("id", "name", "model"):
            value = str(spec.get(key) or "").strip().lower()
            if value and value == target:
                return dict(spec)
    return {}


def model_quirks(model: str, payload: dict | None = None) -> dict[str, Any]:
    """Return the ``quirks`` dict for a model entry (or ``{}`` when absent).

    Quirks are provider-specific overrides applied at backend config-injection
    time. Examples:
      - ``{"temperature": 1.0}`` for Moonshot ``kimi-k2.x`` which rejects the
        default 0.1 with ``invalid temperature: only 1 is allowed for this model``.

    Returning ``{}`` when no quirks are declared keeps the call sites a
    one-line ``spread = model_quirks(task.model)`` without branching.
    """
    entry = resolve_model_entry(model, payload)
    quirks = entry.get("quirks") if isinstance(entry, dict) else None
    return dict(quirks) if isinstance(quirks, dict) else {}


def _resolve_role_config_path(path_value: str) -> Path:
    path = Path(str(path_value or "").strip() or "configs/codex.local.toml")
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def collect_task_proxy_specs(task: TaskSpec) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    models_payload = load_models_payload()
    models_proxy_defs = models_payload.get("proxies") or {}
    for source_name, model_ref in (("executor", task.model), ("executor_image_model", task.image_model)):
        model_provider_name, model_provider_cfg = resolve_models_provider_entry(model_ref, models_payload)
        proxy = provider_proxy_spec(model_provider_cfg, proxy_definitions=models_proxy_defs)
        if proxy:
            specs.append(
                {
                    **proxy,
                    "provider_name": model_provider_name,
                    "source": source_name,
                    "model": model_ref,
                }
            )
    for role_name, role_spec in (
        ("user_simulator", task.codex.user_simulator),
        ("supervisor", task.codex.supervisor),
    ):
        config_path = _resolve_role_config_path(role_spec.config)
        base = load_codex_base_config(config_path)
        codex_proxy_defs = base.get("proxies") or {}
        provider_name, _ = resolve_codex_provider(base, model=role_spec.model, provider=role_spec.provider)
        provider_cfg = dict((base.get("model_providers") or {}).get(provider_name) or {})
        proxy = provider_proxy_spec(provider_cfg, proxy_definitions=codex_proxy_defs)
        if proxy:
            specs.append(
                {
                    **proxy,
                    "provider_name": provider_name,
                    "source": role_name,
                    "model": role_spec.model,
                }
            )
    return specs


@contextmanager
def managed_task_proxy_tunnels(tasks: list[TaskSpec]):
    states: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        for task in tasks:
            for spec in collect_task_proxy_specs(task):
                key = _proxy_spec_key(spec)
                if key in seen:
                    continue
                seen.add(key)
                _ensure_no_adapter_conflict(spec, states)
                state = acquire_shared_proxy_tunnel(spec)
                states.append(state)
        yield states
    finally:
        for state in reversed(states):
            stop_proxy_tunnel(state)


def _json_clone(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))
