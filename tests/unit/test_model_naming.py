"""Tests for the lib.util.model_naming utility.

Covers:
- forward (encode_model_dir) is deterministic
- reverse (decode_model_full) round-trips every model the orchestra
  currently encounters
- ambiguous and unknown inputs raise ValueError
- load_registry walks the models.local.json shape correctly
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.util.model_naming import (  # noqa: E402
    decode_model_full,
    default_models_json_path,
    display_model_name,
    encode_model_dir,
    include_in_public_webui,
    load_registry,
)


# Every model the orchestra has encoded in the runs tree to date.  Each
# pair must survive a round-trip through encode + decode.
ORCHESTRA_MODELS = [
    ("provider-all/kimi-k2.6",                  "provider-all-kimi-k2-6"),
    ("provider-all/qwen3.5-plus",               "provider-all-qwen3-5-plus"),
    ("provider-all/gemini-3-flash-preview",     "provider-all-gemini-3-flash-preview"),
    ("provider-all-new/aws.claude-sonnet-4.6",  "provider-all-new-aws-claude-sonnet-4-6"),
    ("provider-all-new/gemini-3.1-pro-preview", "provider-all-new-gemini-3-1-pro-preview"),
    ("provider-all-new/gpt-5.4-controller",           "provider-all-new-gpt-5-4-controller"),
    ("proxy-example/aws.claude-opus-4.6",       "proxy-example-aws-claude-opus-4-6"),
    ("proxy-example/gpt-5.4",                   "proxy-example-gpt-5-4"),
    ("proxy-usage/gpt-4.1",                     "proxy-usage-gpt-4-1"),
]


@pytest.mark.parametrize("model_full,expected_dir", ORCHESTRA_MODELS)
def test_encode_model_dir_is_deterministic(model_full: str, expected_dir: str) -> None:
    assert encode_model_dir(model_full) == expected_dir


@pytest.mark.parametrize("model_full,model_dir", ORCHESTRA_MODELS)
def test_decode_model_full_round_trips_via_registry(model_full: str, model_dir: str) -> None:
    registry = [m for (m, _) in ORCHESTRA_MODELS]
    assert decode_model_full(model_dir, registry) == model_full


def test_decode_unknown_dir_raises() -> None:
    registry = [m for (m, _) in ORCHESTRA_MODELS]
    with pytest.raises(ValueError) as exc:
        decode_model_full("totally-not-a-real-model", registry)
    assert "unknown model_dir" in str(exc.value)


def test_decode_ambiguous_dir_raises() -> None:
    # Construct a registry where two entries encode to the same dir.
    # ``foo/bar.baz`` and ``foo/bar-baz`` both → ``foo-bar-baz``.
    registry = ["foo/bar.baz", "foo/bar-baz"]
    with pytest.raises(ValueError) as exc:
        decode_model_full("foo-bar-baz", registry)
    assert "ambiguous model_dir" in str(exc.value)


def test_decode_empty_registry_raises_unknown() -> None:
    with pytest.raises(ValueError) as exc:
        decode_model_full("proxy-example-gpt-5-4", [])
    assert "unknown model_dir" in str(exc.value)


def test_load_registry_walks_models_json(tmp_path: Path) -> None:
    payload = {
        "providers": {
            "provider_a": {
                "models": [
                    {"id": "model.one", "name": "model.one"},
                    {"id": "model-two", "name": "model-two"},
                ],
            },
            "provider_b": {
                "models": [
                    {"id": "only-id"},  # falls back to id when name missing
                ],
            },
            "provider_with_no_models": {},
            "provider_with_bad_shape": [],  # ignored
        },
    }
    target = tmp_path / "models.local.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    registry = load_registry(target)
    assert sorted(registry) == sorted([
        "provider_a/model.one",
        "provider_a/model-two",
        "provider_b/only-id",
    ])


def test_load_registry_handles_string_entries(tmp_path: Path) -> None:
    payload = {"providers": {"p": {"models": ["plain-string-model"]}}}
    target = tmp_path / "models.local.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    assert load_registry(target) == ["p/plain-string-model"]


def test_default_models_json_path_points_into_configs_dir() -> None:
    # The helper should resolve relative to the repo root, regardless of
    # the cwd from which pytest is invoked.
    p = default_models_json_path(REPO_ROOT)
    assert p == REPO_ROOT / "configs" / "models.local.json"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("provider-primary/vendor-claude-opus-4.8-private", "claude-opus-4.8"),
        ("provider-primary-vendor-claude-opus-4-8-private", "claude-opus-4.8"),
        ("provider-primary/aws.claude-sonnet-4.6", "claude-sonnet-4.6"),
        ("provider-primary-aws-claude-sonnet-4-6", "claude-sonnet-4.6"),
        ("proxy-example/aws.claude-opus-4.6", "claude-opus-4.6"),
        ("private-route-claude-opus-4.8-extra", "claude-opus-4.8"),
        ("provider-primary-claude-opus-4-8-extra", "claude-opus-4.8"),
        ("pool-a-gemini-3-1-pro-preview", "gemini-3.1-pro-preview"),
        ("provider-all-new/kimi-k2.6", "kimi-k2.6"),
        ("provider-all-new-qwen3-5-plus", "qwen3.5-plus"),
        ("proxy-usage/gpt-4.1", "gpt-4.1"),
        ("provider-all-new/gpt-5.4-mini", "gpt-5.4-mini"),
        ("private-route/vendor-claude-opus-4.8-daily", "claude-opus-4.8"),
        ("private-route-MiniMax-M2-7", "MiniMax-M2.7"),
        ("aws.claude-sonnet-4.6", "claude-sonnet-4.6"),
    ],
)
def test_display_model_name_strips_provider_and_keypool(raw: str, expected: str) -> None:
    assert display_model_name(raw) == expected


def test_public_webui_excludes_non_openclaw_gemini_pro() -> None:
    assert include_in_public_webui("openclaw", "provider-all-new/gemini-3.1-pro-preview")
    assert not include_in_public_webui("nanobot", "provider-all-new/gemini-3.1-pro-preview")
    assert not include_in_public_webui("openclaw_edict", "provider-all-new-gemini-3-1-pro-preview")
    assert include_in_public_webui("nanobot", "provider-all-new/gemini-3-flash-preview")
    assert include_in_public_webui("nanobot", "kimi-k2.6")


def test_public_webui_excludes_smoke_test_rows() -> None:
    assert not include_in_public_webui("openclaw", "gpt-4.1", "001_smoketest")
    assert not include_in_public_webui("openclaw", "gpt-4.1", "000_sanity")
    assert include_in_public_webui("openclaw", "gpt-4.1", "101_skill_usage")


def test_orchestra_models_against_real_registry() -> None:
    """If configs/models.local.json exists on disk, every encoded dir we
    use today must round-trip via the live registry (catches regressions
    where someone deletes a model from models.local.json without first
    backfilling the runs tree)."""
    registry_path = default_models_json_path(REPO_ROOT)
    if not registry_path.exists():
        pytest.skip("configs/models.local.json not present; nothing to verify")
    registry = load_registry(registry_path)
    for model_full, model_dir in ORCHESTRA_MODELS:
        if model_full not in registry:
            pytest.skip(f"{model_full} not in real registry; skipping live check")
        assert decode_model_full(model_dir, registry) == model_full
