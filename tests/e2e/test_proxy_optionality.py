"""End-to-end pin of the proxy-is-per-provider-optional contract.

Some upstream APIs need a local adapter (the proxy_* fixtures route
through ``drop_max_tokens`` on 9001 and ``responses_via_chat`` on 9002).
Others — straight OpenAI / Anthropic / generic gateways — speak the
wire protocol directly and would be slowed down or broken by an
adapter in the path.

The runtime makes that decision per-provider:
``lib.proxy.spec.provider_proxy_spec`` returns ``None`` when the
provider config has neither an inline ``proxy:`` block nor a
``proxyRef:``, and ``lib.runner.task_config`` only calls
``acquire_shared_proxy_tunnel`` when the spec is non-None.

These tests pin both halves so a future refactor that "regularises"
the call site (e.g. by always invoking the tunnel manager) doesn't
silently force a proxy on providers that don't need one.
"""
from __future__ import annotations

from typing import Any

import pytest

from lib.proxy.tunnel import provider_proxy_spec  # spec.py merged into tunnel.py in Phase 4


# ── provider_proxy_spec itself ───────────────────────────────────────


def test_no_proxy_block_returns_none() -> None:
    """A provider with no ``proxy:`` field and no ``proxyRef:`` opts
    out entirely — the runtime must call the API directly."""
    cfg = {"baseUrl": "https://api.openai.com/v1", "apiKey": "sk-xxx"}
    assert provider_proxy_spec(cfg) is None


def test_inline_proxy_block_returns_spec() -> None:
    """A provider with an inline ``proxy:`` block opts IN: tunnel
    spec must come back populated."""
    cfg = {
        "baseUrl": "http://127.0.0.1:9001/v1",
        "apiKey": "fake",
        "proxy": {
            "kind": "adapter",
            "upstreamBase": "http://127.0.0.1:9000",
            "adapter": "drop_max_tokens",
            "adapterPort": 9001,
            "localPort": 9001,
        },
    }
    spec = provider_proxy_spec(cfg)
    assert spec is not None
    assert spec.get("kind") == "adapter"
    assert spec.get("adapter") == "drop_max_tokens"


def test_proxy_ref_resolved_via_definitions() -> None:
    """A provider can also opt-in via ``proxyRef:`` pointing at a
    named definition in the shared ``proxies:`` table."""
    cfg = {"baseUrl": "http://127.0.0.1:9001/v1", "proxyRef": "local-adapter-chat"}
    defs = {
        "local-adapter-chat": {
            "type": "adapter",
            "upstreamBase": "http://127.0.0.1:9000",
            "adapter": "drop_max_tokens",
            "adapterPort": 9001,
            "localPort": 9001,
        }
    }
    spec = provider_proxy_spec(cfg, proxy_definitions=defs)
    assert spec is not None
    assert spec.get("adapter") == "drop_max_tokens"


def test_unknown_proxy_ref_falls_back_to_none() -> None:
    """A ``proxyRef`` that doesn't match any definition must NOT
    crash and must NOT silently fabricate a default — it returns
    None so the runtime calls the API directly (and the operator
    notices because the typo will surface in API errors)."""
    cfg = {"proxyRef": "no-such-name"}
    assert provider_proxy_spec(cfg, proxy_definitions={"other": {}}) is None


def test_empty_provider_config_returns_none() -> None:
    """Defensive: degenerate inputs return None rather than raising."""
    assert provider_proxy_spec({}) is None
    assert provider_proxy_spec(None) is None  # type: ignore[arg-type]


# ── collect_task_proxy_specs — the integration with TaskSpec ─────────


def test_collect_task_proxy_specs_skips_provider_without_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the model_provider_cfg has no proxy and codex roles also
    have no proxy, ``collect_task_proxy_specs`` returns an empty
    list — the dispatcher's ``managed_task_proxy_tunnels`` context
    manager will then start zero tunnels."""
    from lib.runner import task_config

    # Sentinel TaskSpec — we don't need to populate it, the test
    # mocks resolve_models_provider_entry to return a no-proxy config
    # regardless.
    class _FakeRole:
        config = "ignored"
        model = "fake-model"
        provider = "fake_provider"

    class _FakeCodex:
        supervisor = _FakeRole()
        user_simulator = _FakeRole()

    class _FakeTask:
        model = "fake_provider/fake-model"
        image_model = "fake_provider/fake-model"
        codex = _FakeCodex()

    # All proxy-resolution helpers return "no proxy" for every input.
    monkeypatch.setattr(task_config, "load_models_payload", lambda: {"proxies": {}})
    monkeypatch.setattr(
        task_config,
        "resolve_models_provider_entry",
        lambda model_ref, payload: ("fake_provider", {"baseUrl": "https://api.example/v1"}),
    )
    monkeypatch.setattr(task_config, "_resolve_role_config_path", lambda p: p)
    monkeypatch.setattr(task_config, "load_codex_base_config", lambda p: {"proxies": {}, "model_providers": {"fake_provider": {}}})
    monkeypatch.setattr(
        task_config,
        "resolve_codex_provider",
        lambda base, *, model, provider: ("fake_provider", {}),
    )
    monkeypatch.setattr(task_config, "provider_proxy_spec", lambda cfg, *, proxy_definitions=None: None)

    specs = task_config.collect_task_proxy_specs(_FakeTask())  # type: ignore[arg-type]
    assert specs == []


def test_collect_task_proxy_specs_includes_provider_with_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inverse: when the executor model's provider DOES declare a
    proxy, ``collect_task_proxy_specs`` includes one entry tagged
    with that source — the tunnel manager will then start a tunnel
    for it."""
    from lib.runner import task_config

    proxy_spec: dict[str, Any] = {
        "kind": "adapter",
        "adapter": "drop_max_tokens",
        "adapter_port": 9001,
        "local_host": "127.0.0.1",
        "local_port": 9001,
    }

    class _FakeRole:
        config = "ignored"
        model = "fake-model"
        provider = "fake_provider"

    class _FakeCodex:
        supervisor = _FakeRole()
        user_simulator = _FakeRole()

    class _FakeTask:
        model = "fake_provider/fake-model"
        image_model = "fake_provider/fake-model"
        codex = _FakeCodex()

    monkeypatch.setattr(task_config, "load_models_payload", lambda: {"proxies": {}})
    monkeypatch.setattr(
        task_config,
        "resolve_models_provider_entry",
        lambda model_ref, payload: ("fake_provider", {"baseUrl": "http://127.0.0.1:9001/v1", "proxy": proxy_spec}),
    )
    monkeypatch.setattr(task_config, "_resolve_role_config_path", lambda p: p)
    monkeypatch.setattr(task_config, "load_codex_base_config", lambda p: {"proxies": {}, "model_providers": {"fake_provider": {}}})
    monkeypatch.setattr(
        task_config,
        "resolve_codex_provider",
        lambda base, *, model, provider: ("fake_provider", {}),
    )

    def _fake_provider_proxy_spec(provider_cfg, *, proxy_definitions=None):
        if provider_cfg.get("proxy"):
            return proxy_spec
        return None

    monkeypatch.setattr(task_config, "provider_proxy_spec", _fake_provider_proxy_spec)

    specs = task_config.collect_task_proxy_specs(_FakeTask())  # type: ignore[arg-type]
    # Two role-paths (executor + executor_image_model) plus two codex roles
    # — only the executor side declared a proxy, so we expect exactly 2
    # entries (executor + executor_image_model), all tagged with the
    # same upstream.
    assert len(specs) == 2
    assert {s["source"] for s in specs} == {"executor", "executor_image_model"}
    for s in specs:
        assert s.get("adapter") == "drop_max_tokens"
