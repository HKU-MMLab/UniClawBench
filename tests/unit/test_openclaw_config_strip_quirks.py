"""Round 9 / Phase D regression: openclaw config validator rejects
unknown keys, and Clawbench's ``models.local.json`` carries a
``quirks`` field on individual model specs (used host-side by
``task_config.model_quirks`` to set nanobot's per-model temperature
etc.).

Before the fix, the container-injected ``/root/.openclaw/openclaw.json``
still carried ``quirks`` and ``openclaw doctor`` failed validation:

  × models.providers.dashscope-coding.models.2: Unrecognized key: "quirks"

This test pins that ``_containerize_models_fragment`` (the for-container
normalizer) strips ``quirks`` from every model spec so the gateway can
boot.  The host-side ``model_quirks`` lookup must still see the field
in the original payload — only the container copy is stripped.
"""
from __future__ import annotations

from lib.runner.openclaw import (
    _containerize_models_fragment,
    normalize_openclaw_config_fragment,
)


def test_containerize_strips_quirks_from_every_model_spec() -> None:
    payload = {
        "models": {
            "mode": "merge",
            "providers": {
                "provider_pool": {
                    "baseUrl": "https://example/openai/v1",
                    "models": [
                        {"id": "kimi-k2.6", "input": ["text"], "quirks": {"temperature": 1.0}},
                        {"id": "gpt-5.4", "input": ["text", "image"]},
                    ],
                },
                "dashscope-coding": {
                    "baseUrl": "https://example/dashscope/v1",
                    "models": [
                        {"id": "qwen3-coder-plus", "input": ["text"], "quirks": {"reasoning": "high"}},
                    ],
                },
            },
        },
    }
    out = _containerize_models_fragment(payload, attempt_id="abc")
    providers = ((out.get("models") or {}).get("providers")) or {}
    for provider_cfg in providers.values():
        for spec in (provider_cfg.get("models") or []):
            assert "quirks" not in spec, (
                f"containerized fragment leaked 'quirks' in spec={spec!r}; "
                "openclaw runtime would reject this with Unrecognized key"
            )


def test_normalize_for_container_strips_quirks() -> None:
    """End-to-end pin through the public ``normalize_..._fragment`` API
    with ``for_container=True`` — that's what
    ``inject_openclaw_config`` calls."""
    payload = {
        "models": {
            "mode": "merge",
            "providers": {
                "provider_pool": {
                    "baseUrl": "https://example/openai/v1",
                    "models": [
                        {"id": "kimi-k2.6", "quirks": {"temperature": 1.0}},
                    ],
                },
            },
        },
    }
    out = normalize_openclaw_config_fragment(payload, for_container=True, attempt_id="t1")
    providers = ((out.get("models") or {}).get("providers")) or {}
    assert "kimi-k2.6" == providers["provider_pool"]["models"][0]["id"]
    assert "quirks" not in providers["provider_pool"]["models"][0]


def test_normalize_for_host_preserves_quirks() -> None:
    """Host-side normalization (``for_container=False``, used by
    ``model_quirks`` lookup) MUST keep the quirks field — only the
    container copy is stripped."""
    payload = {
        "models": {
            "mode": "merge",
            "providers": {
                "provider_pool": {
                    "baseUrl": "https://example/openai/v1",
                    "models": [
                        {"id": "kimi-k2.6", "quirks": {"temperature": 1.0}},
                    ],
                },
            },
        },
    }
    out = normalize_openclaw_config_fragment(payload, for_container=False)
    providers = ((out.get("models") or {}).get("providers")) or {}
    assert providers["provider_pool"]["models"][0].get("quirks") == {"temperature": 1.0}
