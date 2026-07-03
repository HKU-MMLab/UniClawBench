"""Tests for per-task token attribution and full request transcript log.

Locks behavior introduced by ``feat/per-task-token-tracking``:

1. ``append_{executor,role}_usage_ledger`` filter by ``task_id`` so two
   parallel attempts sharing one shared adapter cannot steal each
   other's events when their wall-clock windows overlap on the same
   adapter kind.
2. ``append_attempt_request_log`` slices the companion request-log by
   ``task_id`` into per-attempt ``requests.jsonl``.
3. ``openclaw.inject_attempt_url_prefix`` produces the canonical
   ``/_t/<id>`` prefix the adapter knows how to strip.
4. ``openclaw.normalize_openclaw_config_fragment`` rewrites adapter-
   routed providers' ``baseUrl`` to carry the per-attempt prefix and
   leaves direct-upstream providers alone.
5. ``container.inject_nanobot_config`` sets ``providers.custom.apiBase``
   to the prefixed adapter URL when the resolved provider is adapter-
   routed (this is what finally makes nanobot token usage observable).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.runner import (
    append_attempt_request_log,
    append_executor_usage_ledger,
    append_role_usage_ledger,
    attempt_task_id,
)
from lib.runner import openclaw, container_lifecycle as container_mod


def _write_log(log_path: Path, entries: list[dict]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


# ── B.4: per-task ledger filtering ───────────────────────────────────


def test_executor_ledger_filters_events_by_task_id_when_present(tmp_path) -> None:
    """When two parallel attempts of the same role share the adapter,
    each task's slice must include only its own events even though the
    time windows overlap and adapter kind matches."""
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            # Attempt A's executor call inside window [90, 200)
            {"event": "usage", "ts": 100.0, "adapter": "drop_max_tokens",
             "task_id": "p1-aaaaaa",
             "prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
            # Attempt B's executor call inside the SAME window — same
            # adapter kind. Pre-fix this was double-counted into A.
            {"event": "usage", "ts": 110.0, "adapter": "drop_max_tokens",
             "task_id": "p1-bbbbbb",
             "prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55},
        ],
    )
    attempt_dir = tmp_path / "attempt-A"
    attempt_dir.mkdir()
    appended = append_executor_usage_ledger(
        attempt_dir,
        turn=1,
        start_ts=90.0,
        end_ts=200.0,
        task_id="p1-aaaaaa",
        log_path=log_path,
    )
    assert appended == 1
    rows = [json.loads(line) for line in (attempt_dir / "usage_ledger.jsonl").read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["prompt_tokens"] == 10
    assert rows[0]["adapter"] == "drop_max_tokens"


def test_executor_ledger_falls_back_to_window_when_task_id_absent(tmp_path) -> None:
    """Backward compat: legacy adapter (no ``task_id`` field on events)
    must still be sliced by the time-window+adapter-kind path. Also
    covers the migration window where the runner is upgraded but the
    adapter subprocess still in flight is the old build."""
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            # No task_id field — pre-this-release adapter event.
            {"event": "usage", "ts": 100.0, "adapter": "drop_max_tokens",
             "prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_executor_usage_ledger(
        attempt_dir, turn=1, start_ts=90.0, end_ts=200.0,
        task_id="p1-aaaaaa", log_path=log_path,
    )
    assert appended == 1
    row = json.loads((attempt_dir / "usage_ledger.jsonl").read_text().strip())
    assert row["prompt_tokens"] == 7


def test_role_ledger_filters_by_task_id_under_parallel_supervisor_overlap(tmp_path) -> None:
    """Same isolation guarantee for the supervisor/user_simulator
    Codex-side adapter when two attempts' supervision phases overlap
    on the shared ``responses_via_chat`` adapter."""
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            {"event": "usage", "ts": 100.0, "adapter": "responses_via_chat",
             "task_id": "p1-aaaaaa",
             "prompt_tokens": 200, "completion_tokens": 20, "total_tokens": 220},
            {"event": "usage", "ts": 120.0, "adapter": "responses_via_chat",
             "task_id": "p1-bbbbbb",
             "prompt_tokens": 999, "completion_tokens": 99, "total_tokens": 1098},
        ],
    )
    attempt_dir = tmp_path / "attempt-A"
    attempt_dir.mkdir()
    appended = append_role_usage_ledger(
        attempt_dir, role="answer_supervisor", turn=1,
        start_ts=90.0, end_ts=200.0,
        task_id="p1-aaaaaa", log_path=log_path,
    )
    assert appended == 1
    row = json.loads((attempt_dir / "usage_ledger.jsonl").read_text().strip())
    assert row["category"] == "supervisor"
    assert row["prompt_tokens"] == 200


def test_attempt_task_id_helper_returns_stage_dir_name(tmp_path) -> None:
    out_dir = tmp_path / "runs" / "openclaw" / "model" / "cat" / "task" / "p1-abc123"
    out_dir.mkdir(parents=True)
    assert attempt_task_id(out_dir) == "p1-abc123"


# ── C.2: per-attempt request transcript slicer ───────────────────────


def test_append_attempt_request_log_slices_by_task_id_and_window(tmp_path) -> None:
    log_path = tmp_path / "proxy_requests.log"
    _write_log(
        log_path,
        [
            # Attempt A inside window
            {"event": "interaction", "ts_request": 100.0, "ts_response": 100.5,
             "task_id": "p1-aaaaaa", "endpoint": "/v1/chat/completions",
             "status_code": 200, "request": {"messages": []},
             "response": {"choices": []}},
            # Attempt B inside same window — must be filtered out
            {"event": "interaction", "ts_request": 105.0, "ts_response": 105.6,
             "task_id": "p1-bbbbbb", "endpoint": "/v1/chat/completions",
             "status_code": 200, "request": {}, "response": {}},
            # Attempt A but outside window — must be filtered out
            {"event": "interaction", "ts_request": 250.0, "ts_response": 251.0,
             "task_id": "p1-aaaaaa", "endpoint": "/v1/chat/completions",
             "status_code": 200, "request": {}, "response": {}},
            # Wrong event type — must be skipped
            {"event": "usage", "ts": 110.0, "task_id": "p1-aaaaaa",
             "adapter": "drop_max_tokens", "prompt_tokens": 1,
             "completion_tokens": 1, "total_tokens": 2},
        ],
    )
    attempt_dir = tmp_path / "attempt-A"
    attempt_dir.mkdir()
    appended = append_attempt_request_log(
        attempt_dir, task_id="p1-aaaaaa",
        start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    assert appended == 1
    rows = [json.loads(line) for line in (attempt_dir / "requests.jsonl").read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["task_id"] == "p1-aaaaaa"
    assert rows[0]["ts_request"] == 100.0


def test_append_attempt_request_log_dedups_on_repeat_invocation(tmp_path) -> None:
    """Cycle slicing windows can touch (end_ts of cycle N == start_ts
    of cycle N+1 by half-open semantics, but a defensive caller might
    add a tiny grace). Re-emitting the same event into the per-attempt
    transcript is a recoverable confusion source — assert dedup."""
    log_path = tmp_path / "proxy_requests.log"
    _write_log(
        log_path,
        [
            {"event": "interaction", "ts_request": 100.0, "ts_response": 100.5,
             "task_id": "p1-aaaaaa", "endpoint": "/v1/chat/completions",
             "status_code": 200, "request": {}, "response": {}},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    append_attempt_request_log(
        attempt_dir, task_id="p1-aaaaaa",
        start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    # Second call — overlapping window, identical event.
    append_attempt_request_log(
        attempt_dir, task_id="p1-aaaaaa",
        start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    rows = [
        line for line in (attempt_dir / "requests.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 1


def test_runner_does_not_call_attempt_request_log_anywhere() -> None:
    """``transcript.jsonl`` already records the application-level
    conversation, so per-attempt ``requests.jsonl`` slicing was found
    to be ~40× redundant with ~50GB+ disk cost on a full sweep. The
    function ``append_attempt_request_log`` is intentionally kept
    (callable for ad-hoc debugging) but should NOT be invoked by the
    runner code path. This regression test pins that decision so a
    future refactor doesn't silently re-enable the per-attempt slice.
    """
    import lib.runner.orchestration as _orch
    import lib.runner.evaluation as _eval
    import inspect
    for module in (_orch, _eval):
        src = inspect.getsource(module)
        # Comments / docstrings are allowed to mention the function name;
        # only flag actual call sites.
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            assert "append_attempt_request_log(" not in stripped, (
                f"{module.__name__} still calls append_attempt_request_log: {line!r}"
            )


def test_append_attempt_request_log_falls_back_when_task_id_absent(tmp_path) -> None:
    """Migration window: adapter event has no task_id (legacy build),
    runner already passes task_id. The slicer should still capture the
    event so transcripts don't silently disappear during rollout."""
    log_path = tmp_path / "proxy_requests.log"
    _write_log(
        log_path,
        [
            {"event": "interaction", "ts_request": 100.0, "ts_response": 100.5,
             "endpoint": "/v1/chat/completions",
             "status_code": 200, "request": {}, "response": {}},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_attempt_request_log(
        attempt_dir, task_id="p1-aaaaaa",
        start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    assert appended == 1


# ── B.2 / Part A: URL prefix injection in config helpers ─────────────


def test_inject_attempt_url_prefix_prepends_to_path() -> None:
    assert (
        openclaw.inject_attempt_url_prefix(
            "http://127.0.0.1:9001/v1/openai/native", "p1-abc123"
        )
        == "http://127.0.0.1:9001/_t/p1-abc123/v1/openai/native"
    )


def test_inject_attempt_url_prefix_no_op_when_attempt_id_empty() -> None:
    base = "http://example.com/v1"
    assert openclaw.inject_attempt_url_prefix(base, "") == base


def test_inject_attempt_url_prefix_preserves_query_string() -> None:
    out = openclaw.inject_attempt_url_prefix(
        "http://host:9001/v1?a=1&b=2", "p1-abc123"
    )
    assert out == "http://host:9001/_t/p1-abc123/v1?a=1&b=2"


def test_normalize_fragment_prefixes_adapter_routed_baseurls(tmp_path) -> None:
    """Adapter-routed providers (proxyRef pointing at an adapter
    definition) get the per-attempt prefix; direct-upstream providers
    do NOT — otherwise the upstream would 404 on ``/_t/<id>/...``."""
    payload = {
        "proxies": {
            "local-adapter-chat": {
                "type": "adapter",
                "upstreamBase": "http://127.0.0.1:9000",
                "adapter": "drop_max_tokens",
                "adapterPort": 9001,
                "localPort": 9001,
            },
        },
        "providers": {
            "via_adapter": {
                "baseUrl": "http://127.0.0.1:9001/v1/openai/native",
                "proxyRef": "local-adapter-chat",
                "models": [{"id": "x"}],
            },
            "direct_upstream": {
                "baseUrl": "https://upstream.example.com/v1",
                "models": [{"id": "y"}],
            },
        },
    }
    fragment = openclaw.normalize_openclaw_config_fragment(
        payload, for_container=True, attempt_id="p1-abc123"
    )
    providers = fragment["models"]["providers"]
    assert providers["via_adapter"]["baseUrl"].endswith("/_t/p1-abc123/v1/openai/native")
    assert providers["direct_upstream"]["baseUrl"] == "https://upstream.example.com/v1"


def test_normalize_fragment_no_op_when_attempt_id_empty() -> None:
    """Smoke-test path / older callers that don't supply an attempt_id
    must not break — baseUrl stays canonical."""
    payload = {
        "proxies": {
            "ref": {"type": "adapter", "adapter": "drop_max_tokens",
                    "upstreamBase": "http://up", "adapterPort": 1, "localPort": 1},
        },
        "providers": {
            "p": {"baseUrl": "http://127.0.0.1:9001/v1", "proxyRef": "ref",
                  "models": [{"id": "x"}]},
        },
    }
    fragment = openclaw.normalize_openclaw_config_fragment(
        payload, for_container=True
    )
    base_url = fragment["models"]["providers"]["p"]["baseUrl"]
    # ``container_visible_value`` may rewrite ``127.0.0.1`` →
    # ``host.docker.internal``; accept either form. The point of this
    # test is the absence of ``/_t/`` prefix, not the host substitution.
    assert "/_t/" not in base_url
    assert base_url.endswith(":9001/v1")


# ── Part A: nanobot routes via adapter when provider is adapter-routed


def test_inject_nanobot_config_uses_prefixed_adapter_url(monkeypatch, tmp_path) -> None:
    """The historical bug: nanobot's apiBase pointed at the upstream
    URL, bypassing the adapter, so usage.json was always empty. After
    this fix, when the resolved provider is adapter-routed, nanobot's
    apiBase becomes the adapter URL with a per-attempt prefix — so the
    adapter sees nanobot calls AND can attribute them to this attempt.
    """
    captured: dict = {}

    def fake_load_models_payload():
        return {
            "proxies": {
                "local-adapter-chat": {
                    "type": "adapter",
                    "upstreamBase": "http://127.0.0.1:9000",
                    "adapter": "drop_max_tokens",
                    "adapterPort": 9001,
                    "localPort": 9001,
                },
            },
            "providers": {
                "provider_primary": {
                    "baseUrl": "http://127.0.0.1:9001/v1/openai/native",
                    "apiKey": "test-key",
                    "proxyRef": "local-adapter-chat",
                    "models": [{"id": "claude-opus-4-7"}],
                },
            },
        }

    def fake_resolve_models_provider_entry(model, payload=None):
        return "provider_primary", payload["providers"]["provider_primary"]

    def fake_docker_exec(container, script, **kwargs):
        captured["container"] = container
        captured["script"] = script
        # The script is python with an embedded JSON. Extract it.
        import re
        m = re.search(r"cfg = json\.loads\(([^)]+)\)", script)
        assert m, "expected cfg = json.loads(...) in injected script"
        # The argument to json.loads is itself a json-encoded JSON
        # string of the cfg dict.
        cfg_json_str = json.loads(m.group(1))
        captured["cfg"] = json.loads(cfg_json_str)
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()

    monkeypatch.setattr(container_mod.task_config, "load_models_payload",
                        fake_load_models_payload)
    monkeypatch.setattr(container_mod.task_config, "resolve_models_provider_entry",
                        fake_resolve_models_provider_entry)
    monkeypatch.setattr(container_mod.docker_mod, "docker_exec", fake_docker_exec)

    # Build a minimal TaskSpec stub — only the fields nanobot config
    # touches (model, agent_sys, model normalization).
    class _CodexRole:
        model = ""
        provider = ""
    class _Codex:
        user_simulator = _CodexRole()
        supervisor = _CodexRole()
    class _Task:
        task_id = "task_x"
        category = "cat"
        agent_sys = "nanobot"
        model = "provider_primary/claude-opus-4-7"
        image_model = ""
        codex = _Codex()
    task = _Task()

    container_mod.inject_nanobot_config("c", task, attempt_id="p1-abc123")

    cfg = captured["cfg"]
    api_base = cfg["providers"]["custom"]["apiBase"]
    # The adapter URL got the per-attempt prefix prepended at the FRONT
    # of the path (so client-appended ``/chat/completions`` lands behind it).
    assert "/_t/p1-abc123/" in api_base
    assert api_base.endswith("/v1/openai/native")
    # API key flowed through.
    assert cfg["providers"]["custom"]["apiKey"] == "test-key"


def test_inject_nanobot_config_keeps_upstream_baseurl_when_not_adapter_routed(
    monkeypatch, tmp_path
) -> None:
    """If the resolved provider is direct-upstream (no proxyRef), the
    nanobot apiBase must NOT carry the prefix — there's no adapter to
    strip it and upstream would 404."""
    captured: dict = {}

    def fake_load_models_payload():
        return {
            "providers": {
                "dashscope-coding": {
                    "baseUrl": "https://coding.dashscope.aliyuncs.com/v1",
                    "apiKey": "k",
                    "models": [{"id": "qwen3-max"}],
                },
            },
        }

    def fake_resolve_models_provider_entry(model, payload=None):
        return "dashscope-coding", payload["providers"]["dashscope-coding"]

    def fake_docker_exec(container, script, **kwargs):
        import re
        m = re.search(r"cfg = json\.loads\(([^)]+)\)", script)
        cfg_json_str = json.loads(m.group(1))
        captured["cfg"] = json.loads(cfg_json_str)
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()

    monkeypatch.setattr(container_mod.task_config, "load_models_payload",
                        fake_load_models_payload)
    monkeypatch.setattr(container_mod.task_config, "resolve_models_provider_entry",
                        fake_resolve_models_provider_entry)
    monkeypatch.setattr(container_mod.docker_mod, "docker_exec", fake_docker_exec)

    class _CodexRole:
        model = ""
        provider = ""
    class _Codex:
        user_simulator = _CodexRole()
        supervisor = _CodexRole()
    class _Task:
        task_id = "task_y"
        category = "cat"
        agent_sys = "nanobot"
        model = "dashscope-coding/qwen3-max"
        image_model = ""
        codex = _Codex()

    container_mod.inject_nanobot_config("c", _Task(), attempt_id="p1-abc123")

    api_base = captured["cfg"]["providers"]["custom"]["apiBase"]
    assert "/_t/" not in api_base
    assert api_base.startswith("https://coding.dashscope.aliyuncs.com")


def test_inject_nanobot_config_requires_baseurl(monkeypatch) -> None:
    def fake_load_models_payload():
        return {
            "providers": {
                "custom_provider": {
                    "apiKey": "k",
                    "models": [{"id": "model-x"}],
                },
            },
        }

    def fake_resolve_models_provider_entry(model, payload=None):
        return "custom_provider", payload["providers"]["custom_provider"]

    monkeypatch.delenv("CLAWBENCH_EVAL_BASE_URL", raising=False)
    monkeypatch.setattr(container_mod.task_config, "load_models_payload", fake_load_models_payload)
    monkeypatch.setattr(container_mod.task_config, "resolve_models_provider_entry", fake_resolve_models_provider_entry)

    class _CodexRole:
        model = ""
        provider = ""
    class _Codex:
        user_simulator = _CodexRole()
        supervisor = _CodexRole()
    class _Task:
        task_id = "task_missing_base"
        category = "cat"
        agent_sys = "nanobot"
        model = "custom_provider/model-x"
        image_model = ""
        codex = _Codex()

    with pytest.raises(ValueError, match="missing baseUrl"):
        container_mod.inject_nanobot_config("c", _Task(), attempt_id="p1-abc123")
