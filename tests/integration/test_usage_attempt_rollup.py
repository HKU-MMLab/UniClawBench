"""Tests for:

- ``discover_active_proxy_adapter_log_paths`` — how Clawbench picks up
  the REAL adapter log path at runtime (registry first, then
  ``/proc`` cmdline, then its own default), which fixes the failure
  mode we hit on worker2 where a pre-existing adapter was launched by a
  different checkout and our reader was looking at an empty file.

- ``build_attempt_usage_payload`` — the roll-up that turns
  ``<attempt>/usage_ledger.jsonl`` into the ``usage.json`` schema the
  WebUI consumes, with per-role isolation.

Both behaviours are architectural invariants of the proxy-adapter-
based accounting approach, so regressions here silently turn the
WebUI pills back into ``n/a``.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from lib.proxy import discover_active_proxy_adapter_log_paths
from lib.runner import build_attempt_usage_payload


# ── Registry discovery ──────────────────────────────────────────────


def test_registry_with_log_path_is_discovered(monkeypatch, tmp_path) -> None:
    registry_root = tmp_path / "proxy_registry"
    registry_root.mkdir()
    adapter_log = tmp_path / "external_adapter.log"
    adapter_log.write_text("", encoding="utf-8")

    entry = registry_root / "spec-abc.json"
    entry.write_text(
        json.dumps(
            {
                "refcount": 1,
                "adapter": {
                    "kind": "drop_max_tokens",
                    "listen_port": 9001,
                    "pid": 0,
                    "log_path": str(adapter_log),
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("lib.proxy.core.PROXY_REGISTRY_ROOT", registry_root)

    paths = discover_active_proxy_adapter_log_paths()
    assert any(str(p) == str(adapter_log) for p in paths), (
        "discovery missed the log_path stored in the registry entry"
    )


def test_registry_without_log_path_falls_back_to_default(monkeypatch, tmp_path) -> None:
    """A registry written by older Clawbench doesn't carry
    ``log_path`` and the registered pid isn't present (test env — no
    /proc entry). Discovery must still return something, which on the
    fallback path is the current ROOT/.runtime/proxy_adapter.log."""
    registry_root = tmp_path / "proxy_registry"
    registry_root.mkdir()
    entry = registry_root / "spec-legacy.json"
    entry.write_text(
        json.dumps({"refcount": 1, "adapter": {"kind": "drop_max_tokens", "pid": 999999}}),
        encoding="utf-8",
    )
    default_log = tmp_path / "default.log"
    monkeypatch.setattr("lib.proxy.core.PROXY_REGISTRY_ROOT", registry_root)
    monkeypatch.setattr("lib.proxy.core.PROXY_ADAPTER_LOG_PATH", default_log)

    paths = discover_active_proxy_adapter_log_paths()
    assert paths, "discovery must always yield at least one candidate path"
    # The last-resort fallback (our own default path) appears even when
    # registry + /proc yielded nothing.
    assert any(str(default_log.resolve()) == str(p) for p in paths)


def test_registry_discovery_dedupes(monkeypatch, tmp_path) -> None:
    """Two registry entries both pointing at the same log path must
    yield a single discovery candidate so the merge-across-logs step
    doesn't double-count events."""
    registry_root = tmp_path / "proxy_registry"
    registry_root.mkdir()
    shared_log = tmp_path / "shared.log"
    for n in range(2):
        entry = registry_root / f"spec-{n}.json"
        entry.write_text(
            json.dumps(
                {"refcount": 1, "adapter": {"log_path": str(shared_log)}}
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr("lib.proxy.core.PROXY_REGISTRY_ROOT", registry_root)

    paths = discover_active_proxy_adapter_log_paths()
    matching = [p for p in paths if str(p) == str(shared_log)]
    assert len(matching) == 1


# ── Attempt roll-up ─────────────────────────────────────────────────


def _task(agent_sys: str = "openclaw") -> SimpleNamespace:
    return SimpleNamespace(agent_sys=agent_sys)


def _write_ledger(attempt_dir: Path, entries: list[dict]) -> None:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    with (attempt_dir / "usage_ledger.jsonl").open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def test_rollup_separates_three_roles(tmp_path) -> None:
    """Executor / supervisor / user_simulator buckets must stay
    disjoint in the final ``usage.json``. A single adapter log with
    mixed events, when the ledger was correctly populated by role-
    scoped slicing, produces a clean three-way split."""
    _write_ledger(
        tmp_path,
        [
            {"category": "executor", "turn": 1, "prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110, "adapter": "drop_max_tokens"},
            {"category": "executor", "turn": 1, "prompt_tokens": 200, "completion_tokens": 20, "total_tokens": 220, "adapter": "drop_max_tokens"},
            {"category": "supervisor", "turn": 1, "prompt_tokens": 500, "completion_tokens": 40, "total_tokens": 540, "adapter": "responses_via_chat"},
            {"category": "user_simulator", "turn": 1, "prompt_tokens": 80, "completion_tokens": 7, "total_tokens": 87, "adapter": "responses_via_chat"},
        ],
    )
    payload = build_attempt_usage_payload(tmp_path, _task("openclaw"))
    assert payload["available"] is True

    executor = payload["summary"]["executor"]
    assert executor["prompt_tokens"] == 300
    assert executor["completion_tokens"] == 30
    assert executor["call_count"] == 2

    supervisor = payload["summary"]["supervisor"]
    assert supervisor["prompt_tokens"] == 500
    assert supervisor["completion_tokens"] == 40
    assert supervisor["call_count"] == 1

    user_simulator = payload["summary"]["user_simulator"]
    assert user_simulator["prompt_tokens"] == 80
    assert user_simulator["call_count"] == 1

    # Executor totals MUST NOT include any supervisor or user_simulator
    # numbers — the whole point of role attribution.
    assert executor["prompt_tokens"] + supervisor["prompt_tokens"] + user_simulator["prompt_tokens"] == 880


def test_rollup_executor_by_turn_is_per_cycle(tmp_path) -> None:
    _write_ledger(
        tmp_path,
        [
            {"category": "executor", "turn": 1, "prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110, "adapter": "drop_max_tokens"},
            {"category": "executor", "turn": 2, "prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55, "adapter": "drop_max_tokens"},
            {"category": "executor", "turn": 2, "prompt_tokens": 30, "completion_tokens": 3, "total_tokens": 33, "adapter": "drop_max_tokens"},
        ],
    )
    payload = build_attempt_usage_payload(tmp_path, _task("openclaw"))
    by_turn = payload["executorByTurn"]
    assert by_turn["1"]["prompt_tokens"] == 100
    assert by_turn["1"]["call_count"] == 1
    assert by_turn["2"]["prompt_tokens"] == 80  # 50 + 30
    assert by_turn["2"]["call_count"] == 2


def test_rollup_source_marks_proxy_adapter_when_ledger_has_events(tmp_path) -> None:
    """The ``source.executor`` field lets the WebUI show provenance.
    When the ledger has real events, the source must be
    ``proxy_adapter_log`` (the ground-truth path), not the transcript
    fallback."""
    _write_ledger(
        tmp_path,
        [
            {"category": "executor", "turn": 1, "prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11, "adapter": "drop_max_tokens"},
        ],
    )
    payload = build_attempt_usage_payload(tmp_path, _task("openclaw"))
    assert payload["source"]["executor"] == "proxy_adapter_log"


def test_rollup_falls_back_to_transcript_when_ledger_empty_for_openclaw(tmp_path) -> None:
    """If the proxy adapter ledger didn't capture anything (e.g. the
    two-checkouts bug we hit on worker2), fall back to openclaw's own
    ``message.usage`` blocks in the transcript so the WebUI still
    shows real numbers."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"type": "message", "message": {"usage": {"input": 250, "output": 30, "totalTokens": 280}}}) + "\n",
        encoding="utf-8",
    )
    payload = build_attempt_usage_payload(tmp_path, _task("openclaw"))
    assert payload["available"] is True
    executor = payload["summary"]["executor"]
    assert executor["prompt_tokens"] == 250
    assert executor["completion_tokens"] == 30
    assert executor["call_count"] == 1
    # Source annotation makes the fallback path auditable.
    assert payload["source"]["executor"] == "agent_transcript_fallback"


def test_rollup_marks_unavailable_for_nanobot_without_any_source(tmp_path) -> None:
    """Nanobot neither emits ``message.usage`` nor (in this scenario)
    has adapter events recorded — the payload must be honest about
    that so the WebUI renders ``n/a`` instead of a bogus 0."""
    payload = build_attempt_usage_payload(tmp_path, _task("nanobot"))
    assert payload["available"] is False
    assert payload["reason"] == "nanobot-and-adapter-unavailable"
    assert payload["summary"]["executor"] == {}
    assert payload["summary"]["supervisor"] == {}
    assert payload["summary"]["user_simulator"] == {}


def test_rollup_does_not_copy_usage_into_result_dir(tmp_path) -> None:
    """``result/`` is the ONLY bucket we mirror into supervisor and
    user_simulator workspaces. The per-attempt ``usage.json`` must
    sit OUTSIDE it so those two roles never see token numbers in
    their workspace and drift their judgment on cost signals."""
    _write_ledger(
        tmp_path,
        [
            {"category": "executor", "turn": 1, "prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11, "adapter": "drop_max_tokens"},
        ],
    )
    build_attempt_usage_payload(tmp_path, _task("openclaw"))
    # The function itself doesn't write usage.json (caller does); but
    # the ledger + any future writes MUST stay at attempt root, never
    # inside result/.
    result_dir = tmp_path / "result"
    result_dir.mkdir(exist_ok=True)
    for path in result_dir.rglob("usage*"):
        raise AssertionError(f"usage artifact leaked into result/: {path}")
