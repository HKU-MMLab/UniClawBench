"""Round 8 / A2 regression: codex rate-limit retry is bounded.

From 2026-05-14 code review:

> ``lib/supervision/codex.py:run_codex_prompt`` uses ``while True`` +
> ``rate_limit_retry_count`` with no upper bound. If the upstream
> provider stays throttled, the supervisor / user-simulator call can
> hang forever, leaving the attempt stuck in ``running`` rather than
> falling to ``rate_limit``.

Round 8 / A2 introduces ``DEFAULT_CODEX_RATE_LIMIT_RETRIES`` (default
10, env-override ``CLAWBENCH_CODEX_RATE_LIMIT_RETRIES``) and raises
``CodexRateLimitExhausted`` when the budget is spent.  The exhausted
exception's message embeds ``rate_limit`` so the needle-based
``detect_supervisor_infra_error`` recognises it as a rate-limit
outcome (final_status ``rate_limit``) rather than a generic infra
error.
"""
from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

import pytest

from lib.supervision import codex
from lib.runner.errors import detect_supervisor_infra_error


def test_retry_bound_default_is_ten():
    """Default cap mirrors the executor's DEFAULT_EXECUTOR_RATE_LIMIT_RETRIES.

    Operators wanting longer tolerance set CLAWBENCH_CODEX_RATE_LIMIT_RETRIES,
    but the default keeps both halves of the runtime in sync."""
    # Reload module-level constant after clearing the env to verify the
    # default branch.
    assert codex.DEFAULT_CODEX_RATE_LIMIT_RETRIES == 10


def test_retry_bound_env_override(monkeypatch):
    """``CLAWBENCH_CODEX_RATE_LIMIT_RETRIES`` overrides the default at
    module load time.  Re-import the module to pick up the new value."""
    import importlib

    monkeypatch.setenv("CLAWBENCH_CODEX_RATE_LIMIT_RETRIES", "3")
    reloaded = importlib.reload(codex)
    try:
        assert reloaded.DEFAULT_CODEX_RATE_LIMIT_RETRIES == 3
    finally:
        # Restore default for other tests in the session.
        monkeypatch.delenv("CLAWBENCH_CODEX_RATE_LIMIT_RETRIES", raising=False)
        importlib.reload(codex)


def test_codex_rate_limit_exhausted_is_runtime_error():
    """The exhausted exception must be a RuntimeError subclass so existing
    ``except RuntimeError`` handlers (e.g. evaluate_attempt's supervisor
    fallback) catch it without code change."""
    assert issubclass(codex.CodexRateLimitExhausted, RuntimeError)


def test_exhausted_exception_message_recognised_as_rate_limit():
    """The exhausted exception's message must contain ``rate_limit`` so
    ``detect_supervisor_infra_error`` (which scans error messages with a
    needle list including ``rate_limit``) routes it to the rate_limit
    final status, not infra_error."""
    exc = codex.CodexRateLimitExhausted(
        "codex rate_limit retries exhausted after 10 attempts: 429 Too Many Requests"
    )
    detected = detect_supervisor_infra_error(str(exc))
    assert detected is not None
    assert detected.get("rate_limit") is True
    assert detected.get("type") == "grader_rate_limited"


def test_retry_exhausted_raises_after_n_attempts(monkeypatch, tmp_path):
    """Drive run_codex_prompt with a mocked transport that always 429s.
    After DEFAULT_CODEX_RATE_LIMIT_RETRIES failures, the next call must
    raise CodexRateLimitExhausted instead of looping forever.

    We monkey-patch the inner ``run_codex_via_container`` to return a
    fake result with a 429-looking stderr, and intercept ``time.sleep``
    so the test stays fast.
    """
    # Use a small cap so the test stays bounded.
    monkeypatch.setattr(codex, "DEFAULT_CODEX_RATE_LIMIT_RETRIES", 2)

    # run_codex_prompt gates on runtime credentials before entering the retry
    # loop (required_codex_env_keys → PROXY_EXAMPLE_API_KEY for the default codex
    # config).  Real callers satisfy this via configs/api.local.env; provide a
    # dummy value so the test reaches the rate-limit retry logic it pins.
    monkeypatch.setenv("PROXY_EXAMPLE_API_KEY", "test-key")

    fake_result = subprocess.CompletedProcess(
        args=["codex"],
        returncode=1,
        stdout="",
        stderr="rate_limit_error: 429 too many requests",
    )

    def _fake_run_codex_via_container(**_kw):
        return fake_result

    monkeypatch.setattr(codex, "run_codex_via_container", _fake_run_codex_via_container)
    monkeypatch.setattr(codex.time, "sleep", lambda _s: None)
    # codex_rollout_summary reads from codex_home; give it a benign default
    monkeypatch.setattr(
        codex,
        "codex_rollout_summary",
        lambda _home: {"path": "", "excerpt": ""},
    )

    # Provide a no-op render of build_codex_execution_prompt so the loop
    # doesn't blow up on missing templates.
    monkeypatch.setattr(
        codex,
        "build_codex_execution_prompt",
        lambda prompt, retry_error="", force_toolless=False: prompt,
    )

    session_root = tmp_path / "session"
    workspace_root = tmp_path / "workspace"
    codex_home = tmp_path / "home"
    for d in (session_root, workspace_root, codex_home):
        d.mkdir()

    output_path = tmp_path / "out.json"
    base_config_path = tmp_path / "codex.toml"
    base_config_path.write_text(
        """
model_provider = "proxy-example"
model = "gpt-5.4"

[model_providers.proxy-example]
name = "proxy-example"
base_url = "http://127.0.0.1:9001/v1/openai/native"
env_key = "PROXY_EXAMPLE_API_KEY"
wire_api = "responses"
supports_websockets = false
models = ["gpt-5.4"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(codex.CodexRateLimitExhausted) as exc_info:
        codex.run_codex_prompt(
            prompt="hello",
            model="gpt-5.4",
            provider="proxy-example",
            base_config_path=base_config_path,
            session_root=session_root,
            workspace_root=workspace_root,
            codex_home=codex_home,
            reasoning_effort="medium",
            images=[],
        )
    # The exception message embeds rate_limit so detect_supervisor_infra_error
    # recognises it.
    assert "rate_limit" in str(exc_info.value).lower()
