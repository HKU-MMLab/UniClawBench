"""Tests for the ``rate_limit`` attempt state — peer of ``infra_error``.

Rate-limit (HTTP 429 / upstream-provider quota exceeded) is split out
from the generic ``infra_error`` bucket so the WebUI and operator-side
reports can distinguish "provider throttled us" from runtime / sandbox
/ transport bugs.

The pieces under test:

  - ``lib.runner.detect_openclaw_rate_limit`` — scans the openclaw
    agent log on disk for structured 429 markers (``failoverReason=
    rate_limit`` JSON entries that never surface as assistant text).
  - ``lib.runner.detect_infra_error`` — still returns rate-limit hits
    but tags them with ``rate_limit=True`` so callers can route them
    to the new bucket.
  - ``lib.runner.detect_supervisor_infra_error`` — tags 429 / quota
    errors in supervisor-side exceptions with ``rate_limit=True`` so
    the ``run_supervisor`` fallback path can flip the attempt verdict
    to ``rate_limit`` instead of ``infra_error``.
  - ``lib.runner.structured_rate_limit_score`` — the synthetic score
    payload produced for rate-limited attempts (verdict=rate_limit,
    attempt_state=rate_limit, final_score=0.0).
  - ``lib.runner.resolve_attempt_outcome`` — now emits
    ``final_status="rate_limit"`` when the score has the rate_limit
    marker, and must not pass the success threshold regardless of
    raw_score.
  - ``lib.answer_supervisor.validate_answer_supervisor_payload`` —
    accepts ``rate_limit`` as a verdict and snaps to the matching
    attempt_state + recoverable=False.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.supervision.answer_supervisor import validate_answer_supervisor_payload
from lib.runner import (
    build_runtime_task_spec,
    detect_infra_error,
    detect_openclaw_rate_limit,
    detect_supervisor_infra_error,
    resolve_attempt_outcome,
    structured_rate_limit_score,
)


ROOT = Path(__file__).resolve().parents[2]


def _task():
    return build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")


# ── detect_openclaw_rate_limit ───────────────────────────────────────


def test_detect_openclaw_rate_limit_finds_structured_failover_reason(tmp_path: Path) -> None:
    """The real-world 429 signal: openclaw records a structured JSON log
    entry with failoverReason=rate_limit. The scanner must find this in
    any ``*.log`` under ``<attempt>/openclaw/``."""
    openclaw_dir = tmp_path / "openclaw"
    openclaw_dir.mkdir()
    log_path = openclaw_dir / "openclaw-20260417-0000.log"
    entry = {
        "ts": "2026-04-17T00:00:00Z",
        "level": "warn",
        "event": "provider_failover",
        "failoverReason": "rate_limit",
        "rawErrorPreview": "429 status code (no body)",
    }
    log_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    hit = detect_openclaw_rate_limit(tmp_path)
    assert hit is not None
    assert hit["type"] == "provider_rate_limited"
    assert hit["rate_limit"] is True
    assert hit["noToolProgress"] is True
    # Source should point at the actual log file so operators can jump to it.
    assert str(log_path) in hit["source"]
    assert "429 status code" in hit["message"] or "rate_limit" in hit["message"]


def test_detect_openclaw_rate_limit_returns_none_when_no_markers(tmp_path: Path) -> None:
    openclaw_dir = tmp_path / "openclaw"
    openclaw_dir.mkdir()
    (openclaw_dir / "openclaw-clean.log").write_text(
        '{"ts":"2026-04-17","event":"tool_call","tool":"bash"}\n',
        encoding="utf-8",
    )
    assert detect_openclaw_rate_limit(tmp_path) is None


def test_detect_openclaw_rate_limit_returns_none_when_dir_missing(tmp_path: Path) -> None:
    # Non-openclaw backends (nanobot etc.) don't produce this log dir —
    # the scanner must no-op gracefully instead of blowing up.
    assert detect_openclaw_rate_limit(tmp_path) is None


def test_detect_openclaw_rate_limit_falls_through_to_agent_log(tmp_path: Path) -> None:
    """If the openclaw/ dir is empty but runner logs/agent.log contains the
    429 markers, the scanner should still catch it."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "agent.log").write_text(
        "[stderr] HTTP 429 Too Many Requests from provider\n",
        encoding="utf-8",
    )
    hit = detect_openclaw_rate_limit(tmp_path)
    assert hit is not None
    assert hit["rate_limit"] is True


# ── detect_infra_error now tags rate_limit ───────────────────────────


def test_detect_infra_error_tags_429_hits_as_rate_limit() -> None:
    transcript = json.dumps({
        "type": "message",
        "message": {
            "role": "assistant",
            "stopReason": "error",
            "errorMessage": "Provider returned HTTP 429: rate limit exceeded",
        },
    }) + "\n"
    hit = detect_infra_error(transcript)
    assert hit is not None
    assert hit["type"] == "provider_rate_limited"
    assert hit.get("rate_limit") is True


def test_detect_infra_error_tags_quota_hits_as_rate_limit() -> None:
    transcript = json.dumps({
        "type": "message",
        "message": {
            "role": "assistant",
            "stopReason": "error",
            "errorMessage": "Hour allocated quota exceeded for this account",
        },
    }) + "\n"
    hit = detect_infra_error(transcript)
    assert hit is not None
    assert hit["type"] == "provider_quota_exceeded"
    assert hit.get("rate_limit") is True


def test_detect_infra_error_ignores_429_in_tool_result_skill_docs() -> None:
    """Regression: skills injected into /root/skills/ sometimes ship
    SKILL.md files whose example code references HTTP 429 (e.g. a
    Next.js ``NextResponse.json({ error: 'Too many requests' },
    { status: 429 })`` snippet). When the executor uses the ``read``
    tool on that file, the content lands in a ``toolResult`` block
    in the transcript. Before the fix, the fallback text scan matched
    `` 429 `` there and spuriously tagged the attempt as rate_limited
    even though the provider was healthy. The fallback must only look
    at assistant-authored text."""
    transcript_lines = [
        json.dumps({
            "type": "message",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "please audit this release"}],
            },
        }),
        json.dumps({
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'll start by reading the security-auditor skill doc."}],
            },
        }),
        json.dumps({
            "type": "message",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "toolResult",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "## Rate Limiting example\n\n"
                                    "```ts\n"
                                    "return NextResponse.json({ error: 'Too many requests' }, { status: 429 });\n"
                                    "```\n"
                                ),
                            }
                        ],
                    }
                ],
            },
        }),
        json.dumps({
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Audit complete. Conclusion: only build in an isolated environment."}],
                "stopReason": "end_turn",
            },
        }),
    ]
    transcript = "\n".join(transcript_lines) + "\n"
    assert detect_infra_error(transcript) is None


def test_detect_infra_error_still_catches_real_rate_limit_shape_in_assistant_text() -> None:
    """Sanity check: a realistic provider-error shape inside assistant
    text (``status code: 429`` / ``rate_limit_exceeded``) must still
    trip the fallback. This guards against over-tightening the needle
    set."""
    transcript = json.dumps({
        "type": "message",
        "message": {
            "role": "assistant",
            "content": [{
                "type": "text",
                "text": "Anthropic API error: rate_limit_exceeded (status code: 429).",
            }],
        },
    }) + "\n"
    hit = detect_infra_error(transcript)
    assert hit is not None
    assert hit["type"] == "provider_rate_limited"
    assert hit.get("rate_limit") is True


# ── detect_supervisor_infra_error tags 429 as rate_limit ─────────────


def test_detect_supervisor_infra_error_flags_429_as_rate_limit() -> None:
    hit = detect_supervisor_infra_error("POST /v1/chat returned 429 Too Many Requests")
    assert hit is not None
    assert hit["type"] == "grader_rate_limited"
    assert hit.get("rate_limit") is True


def test_detect_supervisor_infra_error_still_flags_transport_without_rate_limit() -> None:
    hit = detect_supervisor_infra_error("stream disconnected before completion")
    assert hit is not None
    assert hit["type"] == "grader_transport_error"
    assert not hit.get("rate_limit")


# ── structured_rate_limit_score shape ────────────────────────────────


def test_structured_rate_limit_score_emits_rate_limit_verdict() -> None:
    score = structured_rate_limit_score(
        {"type": "provider_rate_limited", "message": "429", "source": "/tmp/openclaw/x.log"},
        turn=3,
    )
    assert score["verdict"] == "rate_limit"
    assert score["attempt_state"] == "rate_limit"
    assert score["rate_limit"] is True
    assert score["rate_limit_type"] == "provider_rate_limited"
    assert score["recoverable"] is False
    assert score["overall_score"] == 0.0
    assert score["evaluation_index"] == 3


# ── resolve_attempt_outcome routing ──────────────────────────────────


def test_resolve_attempt_outcome_rate_limit_becomes_final_status() -> None:
    task = _task()
    outcome = resolve_attempt_outcome(
        task,
        {"verdict": "rate_limit", "rate_limit": True, "overall_score": 0.0, "executor_completed": False},
    )
    assert outcome["final_status"] == "rate_limit"
    assert outcome["final_score"] == 0.0
    assert outcome["passed"] is False


def test_resolve_attempt_outcome_rate_limit_does_not_promote_to_pass() -> None:
    """Even with a high raw_score, a rate_limit attempt must not flip to
    pass — a 429 means the model never got to reason, so any score
    fragment sitting around is meaningless."""
    task = _task()
    outcome = resolve_attempt_outcome(
        task,
        {
            "verdict": "rate_limit",
            "rate_limit": True,
            "overall_score": 0.99,
            "best_supervisor_score": 0.99,
            "executor_completed": True,
        },
    )
    assert outcome["final_status"] == "rate_limit"
    assert outcome["passed"] is False


# ── answer_supervisor payload validation ─────────────────────────────


def test_validate_answer_supervisor_payload_translates_legacy_rate_limit_to_fail() -> None:
    """Round-6 narrowing: ``verdict=rate_limit`` is no longer in the
    supervisor's allowed enum.  Legacy / mis-trained model outputs that
    still produce it are translated to ``verdict=fail`` (semantically:
    the run did not reach pass).  The framework's rate_limit detection
    path (``structured_rate_limit_score``) writes score.json directly
    and bypasses this validator, so the rate_limit final_status remains
    available to downstream consumers via that path."""
    payload = validate_answer_supervisor_payload(
        {
            "verdict": "rate_limit",
            "attempt_state": "rate_limit",
            "recoverable": True,  # not auto-flipped for verdict=fail
            "score": 0.5,
            "confidence": "medium",
            "rationale": "provider threw 429",
            "missing_artifacts": [],
            "guidance_tags": [],
        }
    )
    assert payload["verdict"] == "fail"
    assert payload["attempt_state"] == "terminal_failure"
    # The breadcrumb lets operators monitor models that still emit the
    # narrowed-away values.
    assert payload.get("legacy_verdict_seen") == "rate_limit"


def test_validate_answer_supervisor_payload_legacy_rate_limit_snaps_invalid_attempt_state() -> None:
    """When a legacy rate_limit verdict arrives with an unknown
    attempt_state, the normalised attempt_state must snap to
    ``terminal_failure`` (consistent with the translated verdict=fail)."""
    payload = validate_answer_supervisor_payload(
        {
            "verdict": "rate_limit",
            "attempt_state": "some_invalid_state",  # not in ATTEMPT_STATES
            "recoverable": False,
            "score": 0.0,
            "confidence": "medium",
            "rationale": "",
            "missing_artifacts": [],
            "guidance_tags": [],
        }
    )
    assert payload["verdict"] == "fail"
    assert payload["attempt_state"] == "terminal_failure"


def test_validate_answer_supervisor_payload_rejects_unknown_verdict() -> None:
    with pytest.raises(ValueError):
        validate_answer_supervisor_payload(
            {
                "verdict": "not_a_real_verdict",
                "attempt_state": "in_progress",
                "recoverable": False,
                "score": 0.0,
                "confidence": "medium",
                "rationale": "",
                "missing_artifacts": [],
                "guidance_tags": [],
            }
        )


# ── _clear_openclaw_logs_for_retry ──────────────────────────────────
# The executor-side 429 retry loop re-runs the executor and re-scans
# the openclaw log for rate-limit markers. Because the log is
# append-only across cycles, we need to clear BOTH the container's
# log files and the host-side mirror before each retry — otherwise
# the first turn's 429 would poison detection on every subsequent
# attempt. The docker-exec half is integration-tested by the smoke
# matrix; here we verify the host-side cleanup is correct.


def test_clear_openclaw_logs_for_retry_truncates_host_mirror(tmp_path: Path, monkeypatch) -> None:
    from lib.runner import orchestration

    # Pretend the docker exec succeeded without spinning up a real container.
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class _Result:
            returncode = 0
            stdout = b""
            stderr = b""
        return _Result()

    monkeypatch.setattr(orchestration.subprocess, "run", fake_run)

    # Populate the host-side mirror with files that look like a mid-run
    # state: openclaw/*.log, openclaw/**/*.jsonl, logs/agent.log.
    openclaw_dir = tmp_path / "openclaw"
    openclaw_dir.mkdir()
    (openclaw_dir / "openclaw-0.log").write_text(
        '{"failoverReason":"rate_limit","rawErrorPreview":"429"}\n', encoding="utf-8",
    )
    (openclaw_dir / "openclaw-1.log").write_text("tail\n", encoding="utf-8")
    nested = openclaw_dir / "session"
    nested.mkdir()
    (nested / "rollout.jsonl").write_text('{"evt":"turn_end"}\n', encoding="utf-8")
    # Non-log file under openclaw/ should survive — only *.log / *.jsonl clear.
    (openclaw_dir / "README.md").write_text("keep me", encoding="utf-8")
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "agent.log").write_text("old 429 tail\n", encoding="utf-8")

    orchestration._clear_openclaw_logs_for_retry("fake-container", tmp_path)

    # Container-side truncate command fired exactly once.
    assert len(calls) == 1
    assert calls[0][:3] == ["docker", "exec", "fake-container"]
    # Must target both openclaw and the clawbench runtime log path.
    joined = " ".join(calls[0])
    assert "/tmp/openclaw" in joined
    assert "/tmp_workspace/clawbench/logs/agent.log" in joined

    # Host-side mirror: log + jsonl files are gone, non-log kept, logs/agent.log removed.
    assert not (openclaw_dir / "openclaw-0.log").exists()
    assert not (openclaw_dir / "openclaw-1.log").exists()
    assert not (nested / "rollout.jsonl").exists()
    assert (openclaw_dir / "README.md").exists()
    assert not (logs_dir / "agent.log").exists()


def test_clear_openclaw_logs_for_retry_is_noop_without_container_name(tmp_path: Path, monkeypatch) -> None:
    from lib.runner import orchestration

    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("docker exec must not fire when container_name is empty")

    monkeypatch.setattr(orchestration.subprocess, "run", fake_run)

    # Host mirror should still remain untouched — no container means no run.
    openclaw_dir = tmp_path / "openclaw"
    openclaw_dir.mkdir()
    (openclaw_dir / "openclaw.log").write_text("keep", encoding="utf-8")

    orchestration._clear_openclaw_logs_for_retry("", tmp_path)

    assert not called
    # Bug-guard: the host cleanup IS allowed to fire even without a
    # container, but we currently gate the whole helper. Either behavior
    # is fine — just keep them consistent. Today: nothing happens.
    assert (openclaw_dir / "openclaw.log").exists()
