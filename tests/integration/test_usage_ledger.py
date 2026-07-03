"""Tests for role-attributed token usage ledger writing and aggregation.

Ground-truth capture happens at the proxy adapter layer: the adapter
writes a JSON-Lines event per API response with an ``adapter`` field
identifying which adapter kind served the call. Clawbench slices that
log by [start_ts, end_ts) per role and appends to
``<attempt_dir>/usage_ledger.jsonl`` with ``category={executor,
supervisor, user_simulator}`` so roles never cross-contaminate in the
WebUI's per-attempt display. These tests lock both behaviours.
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.runner import append_executor_usage_ledger, append_role_usage_ledger
from webui.server import usage_payload, usage_summary


def _write_log(log_path: Path, entries: list[dict]) -> None:
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def test_append_executor_usage_ledger_tags_category_and_turn(tmp_path) -> None:
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            # Executor-side event (adapter: drop_max_tokens) inside the window.
            {"event": "usage", "ts": 100.5, "model": "gpt-5.4", "endpoint": "/responses",
             "adapter": "drop_max_tokens",
             "prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
            # Executor-side but outside cycle 1's window — must be dropped.
            {"event": "usage", "ts": 200.0, "model": "gpt-5.4", "endpoint": "/chat/completions",
             "adapter": "drop_max_tokens",
             "prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_executor_usage_ledger(
        attempt_dir,
        turn=1,
        start_ts=90.0,
        end_ts=150.0,
        log_path=log_path,
    )
    assert appended == 1
    ledger = attempt_dir / "usage_ledger.jsonl"
    assert ledger.exists()
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    assert len(rows) == 1
    row = rows[0]
    assert row["category"] == "executor"
    assert row["turn"] == 1
    assert row["prompt_tokens"] == 12
    assert row["completion_tokens"] == 4
    assert row["total_tokens"] == 16
    assert row["endpoint"] == "/responses"
    assert row["model"] == "gpt-5.4"
    assert row["adapter"] == "drop_max_tokens"


def test_append_executor_usage_ledger_appends_across_cycles(tmp_path) -> None:
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            {"event": "usage", "ts": 100.0, "adapter": "drop_max_tokens",
             "prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            {"event": "usage", "ts": 300.0, "adapter": "drop_max_tokens",
             "prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    append_executor_usage_ledger(attempt_dir, turn=1, start_ts=90.0, end_ts=200.0, log_path=log_path)
    append_executor_usage_ledger(attempt_dir, turn=2, start_ts=250.0, end_ts=350.0, log_path=log_path)

    ledger = attempt_dir / "usage_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    assert [r["turn"] for r in rows] == [1, 2]
    assert [r["prompt_tokens"] for r in rows] == [1, 5]


def test_append_executor_usage_ledger_no_events_writes_nothing(tmp_path) -> None:
    log_path = tmp_path / "proxy.log"
    _write_log(log_path, [{"event": "usage", "ts": 5.0, "adapter": "drop_max_tokens",
                           "prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}])
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_executor_usage_ledger(
        attempt_dir,
        turn=1,
        start_ts=100.0,
        end_ts=200.0,
        log_path=log_path,
    )
    assert appended == 0
    assert not (attempt_dir / "usage_ledger.jsonl").exists()


def test_executor_ledger_drops_codex_adapter_events_in_same_window(tmp_path) -> None:
    """Role attribution by adapter kind: even if a Codex adapter event
    lands inside the executor's wall-clock window (e.g. a stray
    supervisor retry, or two runs sharing a single adapter log),
    ``append_executor_usage_ledger`` must NOT count it."""
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            {"event": "usage", "ts": 100.0, "adapter": "drop_max_tokens",
             "prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
            # Codex-side event inside the SAME window — must be rejected.
            {"event": "usage", "ts": 120.0, "adapter": "responses_via_chat",
             "prompt_tokens": 500, "completion_tokens": 30, "total_tokens": 530},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_executor_usage_ledger(
        attempt_dir, turn=1, start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    assert appended == 1
    row = json.loads((attempt_dir / "usage_ledger.jsonl").read_text().strip())
    assert row["category"] == "executor"
    assert row["prompt_tokens"] == 100  # only the drop_max_tokens event
    assert row["adapter"] == "drop_max_tokens"


def test_role_ledger_drops_executor_adapter_events_in_same_window(tmp_path) -> None:
    """The mirror-image check: ``append_role_usage_ledger`` for a
    codex role must ignore executor-side adapter events even when the
    time window overlaps."""
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            {"event": "usage", "ts": 100.0, "adapter": "responses_via_chat",
             "prompt_tokens": 800, "completion_tokens": 40, "total_tokens": 840},
            {"event": "usage", "ts": 110.0, "adapter": "drop_max_tokens",
             "prompt_tokens": 900, "completion_tokens": 50, "total_tokens": 950},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_role_usage_ledger(
        attempt_dir, role="answer_supervisor", turn=1,
        start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    assert appended == 1
    row = json.loads((attempt_dir / "usage_ledger.jsonl").read_text().strip())
    assert row["category"] == "supervisor"
    assert row["prompt_tokens"] == 800
    assert row["adapter"] == "responses_via_chat"


def test_role_ledger_time_window_separates_supervisor_from_user_simulator(tmp_path) -> None:
    """Both Codex roles share the same adapter kind
    (``responses_via_chat``). Separation between them relies purely on
    the wall-clock window handed to ``append_role_usage_ledger`` — the
    runner invokes the supervisor first, then (optionally) the user
    simulator, so two disjoint [start_ts, end_ts) windows fully
    partition the events."""
    log_path = tmp_path / "proxy.log"
    _write_log(
        log_path,
        [
            {"event": "usage", "ts": 100.0, "adapter": "responses_via_chat",
             "prompt_tokens": 200, "completion_tokens": 10, "total_tokens": 210},
            {"event": "usage", "ts": 250.0, "adapter": "responses_via_chat",
             "prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55},
        ],
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    append_role_usage_ledger(attempt_dir, role="answer_supervisor", turn=1,
                             start_ts=90.0, end_ts=200.0, log_path=log_path)
    append_role_usage_ledger(attempt_dir, role="public_user_simulator", turn=1,
                             start_ts=200.0, end_ts=300.0, log_path=log_path)
    rows = [json.loads(line) for line in (attempt_dir / "usage_ledger.jsonl").read_text().splitlines() if line]
    by_cat = {r["category"]: r for r in rows}
    assert by_cat["supervisor"]["prompt_tokens"] == 200
    assert by_cat["user_simulator"]["prompt_tokens"] == 50
    # Cross-contamination check: each role has exactly one entry.
    assert len([r for r in rows if r["category"] == "supervisor"]) == 1
    assert len([r for r in rows if r["category"] == "user_simulator"]) == 1


def test_executor_ledger_rejects_events_without_adapter_field(tmp_path) -> None:
    """Safety default: pre-adapter-field events (legacy / malformed)
    are DROPPED from the executor bucket rather than being counted as
    executor-by-default. Mixing is the worse failure mode; missing a
    count is recoverable by the transcript fallback."""
    log_path = tmp_path / "proxy.log"
    _write_log(log_path, [{"event": "usage", "ts": 100.0,
                           "prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11}])
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    appended = append_executor_usage_ledger(
        attempt_dir, turn=1, start_ts=90.0, end_ts=200.0, log_path=log_path,
    )
    assert appended == 0
    assert not (attempt_dir / "usage_ledger.jsonl").exists()


def test_usage_payload_aggregates_executor_by_turn(tmp_path) -> None:
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    ledger = attempt_dir / "usage_ledger.jsonl"
    with ledger.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"category": "executor", "turn": 1, "prompt_tokens": 10,
                             "completion_tokens": 3, "total_tokens": 13,
                             "estimated_cost": 0.0, "call_count": 1}) + "\n")
        fh.write(json.dumps({"category": "executor", "turn": 1, "prompt_tokens": 20,
                             "completion_tokens": 5, "total_tokens": 25,
                             "estimated_cost": 0.0, "call_count": 1}) + "\n")
        fh.write(json.dumps({"category": "executor", "turn": 2, "prompt_tokens": 7,
                             "completion_tokens": 2, "total_tokens": 9,
                             "estimated_cost": 0.0, "call_count": 1}) + "\n")

    payload = usage_payload(attempt_dir)
    assert payload["available"] is True
    assert payload["summary"]["executor"]["total_tokens"] == 13 + 25 + 9
    assert payload["summary"]["executor"]["call_count"] == 3
    by_turn = payload["executorByTurn"]
    assert by_turn[1]["prompt_tokens"] == 30
    assert by_turn[1]["completion_tokens"] == 8
    assert by_turn[1]["call_count"] == 2
    assert by_turn[2]["total_tokens"] == 9


def test_usage_summary_exposes_executor_fields(tmp_path) -> None:
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    ledger = attempt_dir / "usage_ledger.jsonl"
    with ledger.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"category": "executor", "turn": 1, "prompt_tokens": 100,
                             "completion_tokens": 25, "total_tokens": 125,
                             "estimated_cost": 0.0, "call_count": 1}) + "\n")
        fh.write(json.dumps({"category": "executor", "turn": 2, "prompt_tokens": 50,
                             "completion_tokens": 10, "total_tokens": 60,
                             "estimated_cost": 0.0, "call_count": 1}) + "\n")

    summary = usage_summary(attempt_dir)
    assert summary["executorUsageAvailable"] is True
    assert summary["executorInputTokens"] == 150
    assert summary["executorOutputTokens"] == 35
    assert summary["executorTotalTokens"] == 185
    assert summary["executorCallCount"] == 2
    # per-cycle keys are stringified so the JSON payload is JSON-friendly.
    assert summary["executorByTurn"]["1"]["inputTokens"] == 100
    assert summary["executorByTurn"]["2"]["outputTokens"] == 10


def test_usage_summary_when_only_agent_bucket_exists(tmp_path) -> None:
    """Back-compat: if a run predates executor-only tracking (only agent bucket),
    executorUsageAvailable stays False and the fields are absent/None."""
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    ledger = attempt_dir / "usage_ledger.jsonl"
    ledger.write_text(
        json.dumps({"category": "agent", "prompt_tokens": 5,
                    "completion_tokens": 1, "total_tokens": 6,
                    "estimated_cost": 0.0, "call_count": 1}) + "\n",
        encoding="utf-8",
    )
    summary = usage_summary(attempt_dir)
    assert summary["executorUsageAvailable"] is False
    assert summary["executorInputTokens"] is None
    assert summary["executorOutputTokens"] is None
    assert summary["executorByTurn"] == {}
    # agent bucket still populated
    assert summary["agentTotalTokens"] == 6
