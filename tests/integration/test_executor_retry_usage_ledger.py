"""Round 8 / A4 regression: executor rate-limit retry tokens land in usage ledger.

From 2026-05-14 code review:

> Normal executor turn end appends usage_ledger.  But entering the
> 429 retry loop, the code only records ``_retry_started_at`` /
> ``_retry_ended_at`` for elapsed-time accounting; no second ledger
> append.  Result: every retry's provider tokens vanish from
> ``usage.json.summary.executor`` and from the Results-page averages.

Round 8 / A4:
- Calls ``append_executor_usage_ledger`` after each retry window.
- Tags retry rows with ``retry_kind="rate_limit"`` + ``retry_index=N``
  so consumers can split retry cost from initial-turn cost.

Bonus fix: the orchestration.py call sites used to access the helpers
as ``artifacts.append_executor_usage_ledger`` / ``artifacts.attempt_task_id``,
but artifacts.py never exported those symbols (they live in
``lib.runner.usage_ledger``).  The attribute lookup raised
AttributeError, caught by the surrounding ``try / except Exception``.
This means the **initial-turn** ledger write has been silently failing
since the April-17 refactor (e579f116).  Switching the import to a
direct symbol import fixes both call sites — the initial turn and the
retry windows.
"""
from __future__ import annotations

import json
from pathlib import Path

from lib.runner.usage_ledger import append_executor_usage_ledger


def test_retry_kind_and_index_propagate_to_ledger_rows(tmp_path, monkeypatch):
    """Drive append_executor_usage_ledger with retry kwargs.  The ledger
    rows must carry retry_kind / retry_index so downstream consumers
    can distinguish initial-turn cost from retry cost.

    We don't have a live proxy adapter in the test, so we monkey-patch
    ``read_proxy_usage_events_across_all_logs`` to return a synthetic
    executor-adapter event.
    """
    from lib.runner import usage_ledger as ul

    # Round-trip event that ul._is_executor_adapter_event will accept.
    fake_event = {
        "ts": 100.0,
        "model": "gpt-test",
        "endpoint": "/chat/completions",
        "adapter": "drop_max_tokens",
        "task_id": "test_task",
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
    }

    monkeypatch.setattr(
        ul,
        "read_proxy_usage_events_across_all_logs",
        lambda *, start_ts, end_ts: [fake_event],
    )

    out_dir = tmp_path / "p1-test"
    out_dir.mkdir()

    # Initial-turn append (no retry tags).
    append_executor_usage_ledger(
        out_dir,
        turn=1,
        start_ts=99.0,
        end_ts=101.0,
        task_id="test_task",
    )

    # Retry append (retry_kind/index tagged).
    append_executor_usage_ledger(
        out_dir,
        turn=1,
        start_ts=200.0,
        end_ts=201.0,
        task_id="test_task",
        retry_kind="rate_limit",
        retry_index=2,
    )

    rows = [
        json.loads(line)
        for line in (out_dir / "usage_ledger.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 2

    # First row: initial turn — no retry tags.
    assert "retry_kind" not in rows[0]
    assert "retry_index" not in rows[0]
    assert rows[0]["category"] == "executor"
    assert rows[0]["turn"] == 1

    # Second row: retry — has both tags.
    assert rows[1]["retry_kind"] == "rate_limit"
    assert rows[1]["retry_index"] == 2
    assert rows[1]["category"] == "executor"
    assert rows[1]["turn"] == 1  # same turn as initial


def test_initial_turn_ledger_writes_without_retry_tags(tmp_path, monkeypatch):
    """Default (no retry kwargs) keeps the ledger row shape exactly as
    pre-Round-8.  Important for backward compatibility — downstream
    aggregators (build_attempt_usage_payload, WebUI) read these rows."""
    from lib.runner import usage_ledger as ul

    fake_event = {
        "ts": 50.0,
        "model": "gpt-test",
        "endpoint": "/chat/completions",
        "adapter": "drop_max_tokens",
        "task_id": "test_task",
        "prompt_tokens": 999,
        "completion_tokens": 11,
        "total_tokens": 1010,
    }
    monkeypatch.setattr(
        ul,
        "read_proxy_usage_events_across_all_logs",
        lambda *, start_ts, end_ts: [fake_event],
    )

    out_dir = tmp_path / "p1-test2"
    out_dir.mkdir()

    append_executor_usage_ledger(
        out_dir, turn=2, start_ts=49.0, end_ts=51.0, task_id="test_task",
    )
    rows = [
        json.loads(line)
        for line in (out_dir / "usage_ledger.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert "retry_kind" not in rows[0]
    assert "retry_index" not in rows[0]
    # Required fields unchanged.
    assert rows[0]["category"] == "executor"
    assert rows[0]["turn"] == 2
    assert rows[0]["prompt_tokens"] == 999


def test_orchestration_imports_ledger_helpers_directly():
    """Pre-fix orchestration.py accessed the helpers via
    ``artifacts.append_executor_usage_ledger`` — but artifacts.py never
    exported those symbols, so the attribute lookup raised
    AttributeError (silently caught).  Round 8 / A4 imports them
    directly from usage_ledger.  Pin that the symbols are now in
    orchestration's module namespace."""
    from lib.runner import orchestration

    assert hasattr(orchestration, "append_executor_usage_ledger")
    assert hasattr(orchestration, "attempt_task_id")
    assert hasattr(orchestration, "build_attempt_usage_payload")
