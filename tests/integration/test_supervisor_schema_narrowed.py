"""Round-6 Phase 4 regression: supervisor verdict + attempt_state schema.

Round-6 narrows the supervisor model's allowed outputs to TASK SEMANTICS
only — pass / continue / fail for verdict, and the 5 in_progress …
terminal_failure states for attempt_state.  Framework-runtime flavours
(infra_error, rate_limit) are detected externally and written to
score.json directly via ``lib/runner/orchestration.py``'s
``structured_*_score`` synth functions, which bypass this validator.

These tests pin:

- The schema and validator only accept the narrowed set on fresh model
  outputs.
- Legacy outputs that still emit ``verdict=infra_error`` /
  ``verdict=rate_limit`` are translated to ``verdict=fail`` with a
  ``legacy_verdict_seen`` breadcrumb so operators can monitor models
  that need re-prompting.
- The framework's structured_*_score paths still write the
  framework-flavoured verdicts (infra_error / rate_limit) — they're
  outside the validator's scope.
- The prompt template enumerates only the narrowed verdicts.
"""
from __future__ import annotations

import pytest

from lib.constants import ATTEMPT_STATES, LEGACY_ATTEMPT_STATES, LEGACY_VERDICTS, VERDICTS
from lib.runner.orchestration import (
    structured_rate_limit_score,
    structured_runtime_error_score,
)
from lib.supervision.answer_supervisor import (
    ANSWER_SUPERVISOR_OUTPUT_SCHEMA,
    validate_answer_supervisor_payload,
)


def test_verdicts_narrowed_to_three_values():
    assert VERDICTS == frozenset({"pass", "continue", "fail"})
    # Legacy superset still around so readers can recognise old values.
    assert "infra_error" in LEGACY_VERDICTS
    assert "rate_limit" in LEGACY_VERDICTS


def test_attempt_states_drops_framework_flavours():
    assert "infra_error" not in ATTEMPT_STATES
    assert "rate_limit" not in ATTEMPT_STATES
    assert "in_progress" in ATTEMPT_STATES
    assert "terminal_failure" in ATTEMPT_STATES
    # Legacy superset still recognises the dropped values.
    assert "infra_error" in LEGACY_ATTEMPT_STATES
    assert "rate_limit" in LEGACY_ATTEMPT_STATES


def test_output_schema_enum_uses_narrowed_verdicts():
    enum_values = ANSWER_SUPERVISOR_OUTPUT_SCHEMA["properties"]["verdict"]["enum"]
    assert set(enum_values) == VERDICTS
    assert "infra_error" not in enum_values
    assert "rate_limit" not in enum_values


def test_validator_translates_legacy_infra_error_to_fail():
    """Symmetric with the rate_limit case: legacy ``verdict=infra_error``
    must be translated to ``verdict=fail`` with the breadcrumb so the
    framework's separate infra-detection path still owns that label."""
    payload = validate_answer_supervisor_payload({
        "verdict": "infra_error",
        "attempt_state": "infra_error",
        "recoverable": False,
        "score": 0.0,
        "confidence": "medium",
        "rationale": "container died",
        "missing_artifacts": [],
        "guidance_tags": [],
    })
    assert payload["verdict"] == "fail"
    assert payload["attempt_state"] == "terminal_failure"
    assert payload.get("legacy_verdict_seen") == "infra_error"


def test_validator_accepts_canonical_narrowed_verdicts():
    """Sanity check that pass/continue/fail still validate cleanly and
    don't carry a legacy breadcrumb."""
    for verdict in ("pass", "continue", "fail"):
        payload = validate_answer_supervisor_payload({
            "verdict": verdict,
            "attempt_state": "complete_and_passed" if verdict == "pass" else "in_progress",
            "recoverable": False,
            "score": 0.5,
            "confidence": "medium",
            "rationale": "x",
            "missing_artifacts": [],
            "guidance_tags": [],
        })
        assert payload["verdict"] == verdict
        assert "legacy_verdict_seen" not in payload, (
            f"canonical verdict {verdict!r} must NOT carry the legacy breadcrumb"
        )


def test_validator_rejects_unknown_verdict():
    with pytest.raises(ValueError):
        validate_answer_supervisor_payload({
            "verdict": "what",
            "attempt_state": "in_progress",
            "recoverable": False,
            "score": 0.0,
            "confidence": "medium",
            "rationale": "",
            "missing_artifacts": [],
            "guidance_tags": [],
        })


def test_framework_synth_score_keeps_infra_error_verdict():
    """The framework synth path bypasses the validator and continues to
    write ``verdict=infra_error`` / ``attempt_state=infra_error`` to
    score.json — this is how downstream classification detects the
    runtime flavour.  Narrowing the validator must not break this."""
    score = structured_runtime_error_score(
        {"type": "container_died", "message": "boom"},
        turn=1,
    )
    assert score["verdict"] == "infra_error"
    assert score["attempt_state"] == "infra_error"
    assert score["infra_error"] is True


def test_framework_synth_rate_limit_score_keeps_rate_limit_verdict():
    score = structured_rate_limit_score(
        {"type": "provider_rate_limited", "message": "429", "source": "upstream"},
        turn=2,
    )
    assert score["verdict"] == "rate_limit"
    assert score["attempt_state"] == "rate_limit"
    assert score["rate_limit"] is True


def test_prompt_template_lists_only_narrowed_verdicts():
    """The rendered supervisor prompt must enumerate the narrowed
    verdict set — not the legacy 5-value superset — so the model is
    told what's actually allowed."""
    from lib.supervision.codex import render_template

    rendered = render_template("answer_supervisor", {
        "task_instructions": "T",
        "guidance_tags": "g",
        "verdicts": ", ".join(sorted(VERDICTS)),
        "attempt_states": ", ".join(sorted(ATTEMPT_STATES)),
        "transcript_chunking_note": "",
    })
    # The verdict line must list the three narrowed values.
    assert "pass, continue, fail".count(",") == 2  # sanity on test setup
    # The narrowed alphabetical order: continue, fail, pass.
    assert "continue, fail, pass" in rendered
    # Legacy framework flavours must NOT appear in the verdict enum line.
    # (They may appear elsewhere in prose; the assertion below is
    # scoped to the verdict line.)
    verdict_line = next(
        (line for line in rendered.splitlines() if line.startswith("- `verdict`")),
        "",
    )
    assert verdict_line, "verdict line missing from rendered prompt"
    assert "infra_error" not in verdict_line
    assert "rate_limit" not in verdict_line
