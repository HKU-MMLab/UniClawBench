"""openclaw runtime config injection + model-registry fragment helpers.

The host renders a small JSON fragment (``models/providers``, per-agent
defaults, agent-to-agent allow lists, browser enablement) and installs it
into ``/root/.openclaw/openclaw.json`` inside the container. The config
fragment is deterministic, pure-data, and derived from
``configs/models.local.json`` — extracted here so the unit tests can
exercise the fragment shape without touching docker at all.

Runtime-facing entry points (``_copy_openclaw_models_fragment``,
``validate_openclaw_config``) do touch docker, but only via
:mod:`lib.runner.docker`; they are kept in the same module because they
form a single unit of "project config → container filesystem → openclaw
validate".
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from ..config_stack import container_visible_value
from ..defaults import EXECUTOR_CONTEXT_WINDOW_TOKENS
from ..proxy import write_local
from .docker import docker_cp_to_container, docker_exec
from .task_config import _json_clone, providers_from_models_payload


def _proxy_definitions_from_payload(payload: dict) -> dict:
    """Where ``proxies: {...}`` may live in a models payload — top-level
    or nested under ``models.proxies`` (both shapes are accepted by
    ``configs/models.local.json``). Returns the merged dict; nested
    definitions take precedence on collision because that's what the
    ``deep_merge`` in ``build_openclaw_config_script`` would produce.
    """
    merged: dict = {}
    if isinstance(payload, dict):
        top = payload.get("proxies")
        if isinstance(top, dict):
            merged.update(top)
        nested = (payload.get("models") or {}).get("proxies") if isinstance(payload.get("models"), dict) else None
        if isinstance(nested, dict):
            merged.update(nested)
    return merged


_ADAPTER_PROXY_KINDS = {"adapter", "http_adapter", "compat", "compatibility"}


def _is_adapter_routed_provider(provider_cfg: dict, proxy_defs: dict) -> bool:
    """True iff ``provider_cfg`` resolves to one of our compat adapters
    (``drop_max_tokens`` / ``responses_via_chat``). A provider is
    adapter-routed when its inline ``proxy`` block (or the ``proxyRef``
    referenced definition) has ``type == "adapter"`` OR a non-empty
    ``adapter`` field. Direct-upstream providers (no proxy, or SSH-only
    proxy with no adapter) return False so we don't poison their
    ``baseUrl`` with a per-task URL prefix the upstream wouldn't strip.
    """
    inline = provider_cfg.get("proxy")
    if isinstance(inline, dict):
        return _proxy_def_is_adapter(inline)
    ref = str(provider_cfg.get("proxyRef") or provider_cfg.get("proxy_ref") or "").strip()
    if not ref or not isinstance(proxy_defs, dict):
        return False
    definition = proxy_defs.get(ref)
    if not isinstance(definition, dict):
        return False
    return _proxy_def_is_adapter(definition)


def _proxy_def_is_adapter(definition: dict) -> bool:
    kind = str(definition.get("type") or definition.get("kind") or "").strip().lower().replace("-", "_")
    if kind in _ADAPTER_PROXY_KINDS:
        return True
    adapter = str(definition.get("adapter") or definition.get("compat") or "").strip()
    return bool(adapter)


def inject_attempt_url_prefix(base_url: str, attempt_id: str) -> str:
    """Prepend ``/_t/<attempt_id>`` to the path portion of ``base_url``
    so the proxy adapter can attribute every request to the originating
    attempt (and parallel attempts sharing one adapter port don't
    cross-contribute to each other's token ledger).

    The prefix goes at the FRONT of the path because clients append
    ``/chat/completions`` / ``/responses`` to the configured baseUrl
    when constructing the request URL — putting the marker at the front
    keeps the per-task token isolation work even when the adapter is
    fronted by a non-trivial path (``/v1/openai/native``). The adapter
    matches ``^/+_t/<id>(/.*)`` and strips the marker before any path-
    based routing, so upstream sees the canonical API path.

    Returns ``base_url`` unchanged if ``attempt_id`` is empty (callers
    that don't have an attempt yet — config validation, smoke tests).
    """
    if not attempt_id:
        return base_url
    parts = urlsplit(base_url or "")
    if not parts.netloc:
        return base_url
    new_path = f"/_t/{attempt_id}" + (parts.path or "")
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS = max(
    0,
    int(os.environ.get("CLAWBENCH_OPENCLAW_VALIDATE_TIMEOUT_SECONDS", "20")),
)
OPENCLAW_CONFIG_VALIDATE_STRICT = os.environ.get("CLAWBENCH_OPENCLAW_VALIDATE_STRICT", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _containerize_models_fragment(fragment: dict, *, attempt_id: str = "") -> dict:
    cloned = _json_clone(fragment)
    # Snapshot proxy definitions BEFORE we strip them — we still need to
    # know which providers are adapter-routed so we know which baseUrls
    # should carry the per-task ``/_t/<attempt_id>`` prefix.
    proxy_defs = _proxy_definitions_from_payload(cloned)
    if isinstance(cloned.get("models"), dict):
        cloned["models"].pop("proxies", None)
    cloned.pop("proxies", None)
    providers = (((cloned.get("models") or {}).get("providers")) or {})
    for provider_cfg in providers.values():
        if not isinstance(provider_cfg, dict):
            continue
        adapter_routed = _is_adapter_routed_provider(provider_cfg, proxy_defs)
        provider_cfg.pop("proxy", None)
        provider_cfg.pop("proxyRef", None)
        provider_cfg.pop("proxy_ref", None)
        base_url = str(provider_cfg.get("baseUrl") or "").strip()
        if base_url:
            base_url = container_visible_value(base_url)
            if adapter_routed and attempt_id:
                base_url = inject_attempt_url_prefix(base_url, attempt_id)
            provider_cfg["baseUrl"] = base_url
        # ``configs/models.local.json`` commonly stores API keys as
        # ``${ENV_KEY}``. ``load_models_payload`` expands those when the env or
        # ``configs/api.local.env`` provides a value; otherwise the literal
        # placeholder survives into the container. Recent openclaw validates
        # every provider at gateway startup, not just the selected one, and
        # refuses to boot if any provider references a missing env var. Keep the
        # gateway startable in partially configured local environments while
        # preserving real keys when they were actually resolved.
        api_key = str(provider_cfg.get("apiKey") or "").strip()
        if api_key.startswith("${") and api_key.endswith("}"):
            provider_cfg["apiKey"] = "missing-api-key"
        # Round 9 / Phase D fix: ``quirks`` is a Clawbench-side metadata
        # field (``task_config.model_quirks`` reads it to set nanobot's
        # temperature for kimi etc.) that openclaw's runtime config
        # validator does not recognize.  Recent openclaw rejects
        # unknown keys instead of ignoring them, so leaving ``quirks``
        # in the container-injected config breaks gateway startup with
        # ``Unrecognized key: "quirks"``.  Strip it here — the host
        # side has already consumed the metadata before this point.
        for model_spec in (provider_cfg.get("models") or []):
            if isinstance(model_spec, dict):
                model_spec.pop("quirks", None)
    return cloned


def normalize_openclaw_config_fragment(
    payload: dict,
    *,
    for_container: bool = False,
    attempt_id: str = "",
) -> dict:
    if not isinstance(payload, dict):
        return {}
    # Forward proxy definitions into the cloned fragment when missing so
    # ``_containerize_models_fragment`` can still tell adapter-routed
    # providers from direct-upstream ones (the prefix-injection decision
    # depends on it). Without this, payloads that pass top-level
    # ``proxies`` but only ``models.providers`` (no ``models.proxies``)
    # would lose the routing signal during normalization.
    proxy_defs = _proxy_definitions_from_payload(payload)
    if any(key in payload for key in {"models", "agents", "gateway", "browser", "commands"}):
        fragment = _json_clone(payload)
        if "models" not in fragment:
            providers = providers_from_models_payload(payload)
            if providers:
                fragment["models"] = {
                    "mode": str(payload.get("mode") or "merge"),
                    "providers": _json_clone(providers),
                }
        if proxy_defs and "proxies" not in fragment and "proxies" not in (fragment.get("models") or {}):
            fragment.setdefault("proxies", _json_clone(proxy_defs))
        fragment.pop("providers", None)
        return _containerize_models_fragment(fragment, attempt_id=attempt_id) if for_container else fragment
    providers = providers_from_models_payload(payload)
    if not providers:
        return {}
    fragment = {
        "models": {
            "mode": str(payload.get("mode") or "merge"),
            "providers": _json_clone(providers),
        }
    }
    if proxy_defs:
        fragment["proxies"] = _json_clone(proxy_defs)
    return _containerize_models_fragment(fragment, attempt_id=attempt_id) if for_container else fragment


def openclaw_agent_models_registry(config_fragment: dict) -> dict[str, dict]:
    registry: dict[str, dict] = {}
    providers = (((config_fragment.get("models") or {}).get("providers")) or {})
    for provider_name, provider_cfg in providers.items():
        for spec in provider_cfg.get("models") or []:
            model_id = str(spec.get("id") or "").strip()
            if model_id:
                registry[f"{provider_name}/{model_id}"] = {}
    return registry


def openclaw_model_supports_image(config_fragment: dict, model_ref: str) -> bool:
    provider_name, _, model_id = str(model_ref or "").partition("/")
    if not provider_name or not model_id:
        return False
    providers = (((config_fragment.get("models") or {}).get("providers")) or {})
    for spec in ((providers.get(provider_name) or {}).get("models") or []):
        if str(spec.get("id") or "").strip() != model_id:
            continue
        return "image" in [str(item).strip().lower() for item in (spec.get("input") or [])]
    return False


def configured_openclaw_image_model(config_fragment: dict) -> str:
    return str(
        ((((config_fragment.get("agents") or {}).get("defaults") or {}).get("imageModel")) or {}).get("primary")
        or ""
    ).strip()


def select_openclaw_image_model(config_fragment: dict, model_ref: str) -> str:
    if openclaw_model_supports_image(config_fragment, model_ref):
        return model_ref
    configured = configured_openclaw_image_model(config_fragment)
    if configured:
        return configured
    providers = (((config_fragment.get("models") or {}).get("providers")) or {})
    for provider_name, provider_cfg in providers.items():
        for spec in provider_cfg.get("models") or []:
            spec_id = str(spec.get("id") or "").strip()
            inputs = [str(item).strip().lower() for item in (spec.get("input") or [])]
            if spec_id and "image" in inputs:
                return f"{provider_name}/{spec_id}"
    return model_ref


def _copy_openclaw_models_fragment(container: str, config_fragment: dict) -> None:
    if not config_fragment:
        return
    temp_models = Path(tempfile.mkstemp(prefix="clawbench-models-", suffix=".json")[1])
    try:
        write_local(temp_models, json.dumps(config_fragment, ensure_ascii=False, indent=2) + "\n")
        docker_cp_to_container(temp_models, container, "/tmp/clawbench-models.json")
    finally:
        temp_models.unlink(missing_ok=True)


def build_openclaw_config_script(
    *,
    model_ref: str,
    image_model_ref: str,
    model_registry: dict[str, dict],
    workspace: str,
    agents_list: list[dict] | None = None,
    sessions_visibility: str | None = None,
    sandbox_session_visibility: str | None = None,
    agent_to_agent_allow: list[str] | None = None,
) -> str:
    agents_list_line = ""
    if agents_list is not None:
        agents_list_line = f"cfg['agents']['list'] = json.loads({json.dumps(json.dumps(agents_list, ensure_ascii=False))})\n"
    sessions_visibility_line = ""
    if sessions_visibility:
        sessions_visibility_line = (
            "cfg.setdefault('tools', {}).setdefault('sessions', {})['visibility'] = "
            + json.dumps(sessions_visibility)
            + "\n"
        )
    sandbox_session_visibility_line = ""
    if sandbox_session_visibility:
        sandbox_session_visibility_line = (
            "cfg['agents']['defaults'].setdefault('sandbox', {})['sessionToolsVisibility'] = "
            + json.dumps(sandbox_session_visibility)
            + "\n"
        )
    agent_to_agent_line = ""
    if agent_to_agent_allow is not None:
        agent_to_agent_line = (
            "cfg.setdefault('tools', {}).setdefault('agentToAgent', {})['enabled'] = True\n"
            + "cfg.setdefault('tools', {}).setdefault('agentToAgent', {})['allow'] = "
            + json.dumps(agent_to_agent_allow, ensure_ascii=False)
            + "\n"
        )
    return f"""python3 - <<'PY'
import json
from pathlib import Path

cfg_path = Path('/root/.openclaw/openclaw.json')
cfg = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {{}}

def deep_merge(dst, src):
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            deep_merge(dst[key], value)
        else:
            dst[key] = value

models_file = Path('/tmp/clawbench-models.json')
if models_file.exists():
    deep_merge(cfg, json.loads(models_file.read_text(encoding='utf-8')))

cfg.setdefault('agents', {{}}).setdefault('defaults', {{}})
cfg['agents']['defaults']['workspace'] = {json.dumps(workspace)}
cfg['agents']['defaults'].setdefault('model', {{}})['primary'] = {json.dumps(model_ref)}
cfg['agents']['defaults'].setdefault('imageModel', {{}})['primary'] = {json.dumps(image_model_ref)}
cfg['agents']['defaults'].setdefault('models', json.loads({json.dumps(json.dumps(model_registry, ensure_ascii=False))}))
# Unified cross-backend executor context window (see lib/defaults.py:
# EXECUTOR_CONTEXT_WINDOW_TOKENS). openclaw accepts this via the top-level
# agents.defaults.contextTokens key; it would otherwise default to 200_000
# internally. Overriding makes the value consistent with the nanobot-side
# ``agents.defaults.context_window_tokens`` so both backends hit the same
# provider ceiling.
cfg['agents']['defaults']['contextTokens'] = {EXECUTOR_CONTEXT_WINDOW_TOKENS}
{agents_list_line}{sessions_visibility_line}{sandbox_session_visibility_line}{agent_to_agent_line}cfg.setdefault('commands', {{}})['nativeSkills'] = 'auto'
# Disable openclaw's built-in `browser` MCP tool so the agent falls back to
# the `agent-browser` CLI skill (docker/base_skills/agent-browser-control/
# SKILL.md), which is auto-loaded by ``commands.nativeSkills='auto'``. The
# agent-browser CLI (vercel-labs/agent-browser) fixes three openclaw-upstream
# bugs observed in runs before 2026-04-16:
#   1. ``{{path: ...}}`` on browser.screenshot is silently dropped (schema
#      doesn't declare `path`), so the agent never gets the screenshot at the
#      requested location and then hallucinates a tiny base64 PNG via write.
#   2. ``captureBeyondViewport: true`` is hardcoded in the CDP path
#      (extensions/browser/src/browser/cdp.ts), so ``fullPage: false`` is
#      ignored and every screenshot is full-page.
#   3. ``normalizeBrowserScreenshot`` silently converts PNG → JPEG whenever
#      any resize fires, breaking ``type: "png"``.
# agent-browser honours path/fullPage/type correctly, has a persistent
# daemon, and the SKILL.md already teaches the agent the right commands.
# The skill's trigger line — "Use the `agent-browser` CLI when you need
# browser automation in environments that do not expose a native browser
# tool" — activates precisely when we flip this flag.
#
# ``cfg.browser.enabled = False`` stops the built-in browser control
# service from booting (no port 18791) and makes the tool's handler at
# src/browser-tool.ts:347-350 return ``Browser control is disabled``
# for any call that slipped through. ``browser`` is a bundled extension
# in openclaw, NOT a config-registered plugin, so touching
# ``cfg.plugins.entries.browser`` only produces a "plugin not found"
# warning and has no actual effect — keep that branch out.
cfg.setdefault('browser', {{}})['enabled'] = False
cfg['browser']['evaluateEnabled'] = False
cfg['browser']['executablePath'] = '/usr/local/bin/chromium'
cfg['browser']['noSandbox'] = True
cfg['browser']['ssrfPolicy'] = {{
    'dangerouslyAllowPrivateNetwork': True,
    'allowedHostnames': ['localhost', '127.0.0.1'],
}}

cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
PY"""


def validate_openclaw_config(container: str, *, label: str) -> None:
    command = "openclaw config validate"
    if OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS > 0:
        command = f"timeout {OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS} {command}"
    result = docker_exec(container, command)
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip()
    timed_out = result.returncode == 124 and OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS > 0
    if timed_out and not OPENCLAW_CONFIG_VALIDATE_STRICT:
        return
    if timed_out:
        raise RuntimeError(
            detail
            or f"timed out validating {label} config after {OPENCLAW_CONFIG_VALIDATE_TIMEOUT_SECONDS}s"
        )
    raise RuntimeError(detail or f"failed to validate {label} config")
