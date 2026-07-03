"""Phase 4 — pin ``configs/models*.json:quirks`` resolution.

Model-specific decode overrides (temperature, max_tokens, ...) live in the
models config under each entry's ``quirks`` field. ``model_quirks(model)``
returns the dict for one model — empty when the model is unknown or has no
overrides. The nanobot config injector spreads this dict into its agent
``defaults`` so the runner no longer needs ``"kimi" in task.model.lower()``
substring checks.
"""
from __future__ import annotations

import pytest

from lib.runner.task_config import model_quirks, resolve_model_entry, resolve_models_provider_entry


_PAYLOAD = {
    "providers": {
        "provider-a": {
            "baseUrl": "http://example",
            "models": [
                {"id": "kimi-k2.6", "name": "kimi-k2.6", "quirks": {"temperature": 1.0}},
                {"id": "gpt-5.4", "name": "gpt-5.4"},
                {"id": "fancy-model", "name": "fancy-model", "quirks": {"temperature": 0.7, "max_tokens": 4096}},
            ],
        }
    }
}


def test_model_quirks_returns_temperature_for_kimi():
    quirks = model_quirks("kimi-k2.6", _PAYLOAD)
    assert quirks == {"temperature": 1.0}


def test_model_quirks_returns_empty_dict_when_absent():
    quirks = model_quirks("gpt-5.4", _PAYLOAD)
    assert quirks == {}


def test_model_quirks_returns_empty_for_unknown_model():
    """Unknown model must not raise — the helper is called once per attempt
    and a typo / new model must never crash the container injector."""
    assert model_quirks("nonexistent-model", _PAYLOAD) == {}


def test_model_quirks_returns_copy_so_callers_can_mutate():
    quirks = model_quirks("kimi-k2.6", _PAYLOAD)
    quirks["max_tokens"] = 8192
    # Re-fetching must not see the local mutation.
    fresh = model_quirks("kimi-k2.6", _PAYLOAD)
    assert "max_tokens" not in fresh


def test_resolve_model_entry_returns_full_record():
    entry = resolve_model_entry("fancy-model", _PAYLOAD)
    assert entry["id"] == "fancy-model"
    assert entry["quirks"]["max_tokens"] == 4096


def test_runtime_provider_resolution_rejects_unknown_model():
    with pytest.raises(ValueError, match="unknown executor model"):
        resolve_models_provider_entry("nonexistent-model", _PAYLOAD)


def test_runtime_provider_resolution_rejects_unknown_explicit_provider():
    with pytest.raises(ValueError, match="unknown executor model provider"):
        resolve_models_provider_entry("missing-provider/fancy-model", _PAYLOAD)
