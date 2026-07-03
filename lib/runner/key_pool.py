"""Per-model executor key pool: primary + auxiliary keys.

The dispatcher reads only the ordered label list (``pool_labels``) and rotates
across it (rate-limit-aware). The real key is resolved on the worker
(``resolve_pool_env_override``) by overriding the executor provider's env var, so
both nanobot and openclaw pick it up through the normal ``${ENV}`` expansion —
and no secret ever crosses a command line or SSH string.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from lib import config_stack

# A provider apiKey we can override must be exactly one ``${ENV_VAR}`` placeholder.
_ENV_VAR_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def _load(models_json_path) -> dict:
    try:
        return json.loads(Path(models_json_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def pool_labels(models_json_path, model_dir: str) -> list[str]:
    """Ordered key-pool labels for ``model_dir`` (primary first); [] if no pool."""
    pools = _load(models_json_path).get("keyPools")
    pool = pools.get(model_dir) if isinstance(pools, dict) else None
    return list(pool.keys()) if isinstance(pool, dict) else []


def resolve_pool_env_override(
    models_json_path, env_file, model_dir: str, label: str, provider: str
) -> dict[str, str]:
    """Worker-side: resolve ``label`` to ``{PROVIDER_ENV_VAR: real_key}`` so the
    run_eval subprocess uses the pooled key for the executor provider.

    Returns ``{}`` — i.e. caller keeps the legacy provider-default key — when:
    no label; no pool for this model; unknown label; the provider's ``apiKey``
    is not a single ``${ENV}`` placeholder; or the pool placeholder doesn't
    resolve to a concrete value. Every branch fails safe to legacy behavior.
    """
    if not label:
        return {}
    data = _load(models_json_path)
    pool = (data.get("keyPools") or {}).get(model_dir)
    placeholder = pool.get(label) if isinstance(pool, dict) else None
    if not isinstance(placeholder, str) or not placeholder:
        return {}
    prov_cfg = (data.get("providers") or {}).get(provider) or {}
    m = _ENV_VAR_RE.match(str(prov_cfg.get("apiKey") or "").strip())
    if not m:
        return {}
    provider_var = m.group(1)
    files = [Path(env_file)] if env_file and Path(env_file).exists() else []
    env = config_stack.merged_env(files=files)
    real_key = config_stack.expand_env_placeholders(placeholder, env=env)
    if not isinstance(real_key, str) or not real_key or "${" in real_key:
        return {}
    return {provider_var: real_key}
