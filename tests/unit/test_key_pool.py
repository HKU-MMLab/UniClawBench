"""Unit tests for per-model executor key pool resolution (lib/runner/key_pool.py)."""
from __future__ import annotations

import json

from lib.runner import key_pool


def _fixture(tmp_path):
    mj = tmp_path / "models.local.json"
    mj.write_text(json.dumps({
        "providers": {
            "proxy_pool": {"apiKey": "${PROXY_POOL_API_KEY}", "models": [{"id": "gemini-3.1-pro-preview"}]},
            "literal": {"apiKey": "sk-hardcoded", "models": [{"id": "x"}]},
        },
        "keyPools": {
            "proxy_pool-gemini-3-1-pro-preview": {
                "primary": "${POOL_K1}",
                "aux1": "${POOL_K2}",
                "aux2": "${POOL_K3}",
            },
            "literal-x": {"primary": "${LIT_K1}"},
        },
    }), encoding="utf-8")
    env = tmp_path / "api.local.env"
    env.write_text("PROXY_POOL_API_KEY=defaultkey\nPOOL_K1=poolkey1\nPOOL_K2=poolkey2\nPOOL_K3=poolkey3\nLIT_K1=lk\n", encoding="utf-8")
    return mj, env


M = "proxy_pool-gemini-3-1-pro-preview"


def test_pool_labels_ordered(tmp_path):
    mj, _ = _fixture(tmp_path)
    assert key_pool.pool_labels(mj, M) == ["primary", "aux1", "aux2"]  # insertion order = priority


def test_pool_labels_absent(tmp_path):
    mj, _ = _fixture(tmp_path)
    assert key_pool.pool_labels(mj, "not-a-pooled-model") == []
    assert key_pool.pool_labels(tmp_path / "nope.json", M) == []  # missing file


def test_resolve_each_label_to_provider_env_override(tmp_path):
    mj, env = _fixture(tmp_path)
    assert key_pool.resolve_pool_env_override(mj, env, M, "primary", "proxy_pool") == {"PROXY_POOL_API_KEY": "poolkey1"}
    assert key_pool.resolve_pool_env_override(mj, env, M, "aux1", "proxy_pool") == {"PROXY_POOL_API_KEY": "poolkey2"}
    assert key_pool.resolve_pool_env_override(mj, env, M, "aux2", "proxy_pool") == {"PROXY_POOL_API_KEY": "poolkey3"}


def test_resolve_falls_back_to_legacy(tmp_path):
    mj, env = _fixture(tmp_path)
    # no label / unknown label / non-pooled model -> {} (legacy provider key)
    assert key_pool.resolve_pool_env_override(mj, env, M, "", "proxy_pool") == {}
    assert key_pool.resolve_pool_env_override(mj, env, M, "nope", "proxy_pool") == {}
    assert key_pool.resolve_pool_env_override(mj, env, "other-model", "primary", "proxy_pool") == {}
    # provider apiKey is a literal (not ${ENV}) -> can't override -> {}
    assert key_pool.resolve_pool_env_override(mj, env, "literal-x", "primary", "literal") == {}


def test_resolve_unresolved_placeholder(tmp_path):
    mj, _ = _fixture(tmp_path)
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("PROXY_POOL_API_KEY=x\n", encoding="utf-8")  # POOL_K1 undefined
    # placeholder can't expand -> {} (legacy), never leaks the literal "${POOL_K1}"
    assert key_pool.resolve_pool_env_override(mj, empty_env, M, "primary", "proxy_pool") == {}


def test_resolve_rejects_embedded_unresolved_placeholder(tmp_path):
    mj, env = _fixture(tmp_path)
    data = json.loads(mj.read_text(encoding="utf-8"))
    data["keyPools"][M]["primary"] = "sk-${MISSING_VAR}"
    mj.write_text(json.dumps(data), encoding="utf-8")

    assert key_pool.resolve_pool_env_override(mj, env, M, "primary", "proxy_pool") == {}
