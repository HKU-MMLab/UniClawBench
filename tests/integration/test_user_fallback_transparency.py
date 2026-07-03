"""Round 9 / A3 regression: user-simulator failure must be visible in trace.

The supervision orchestrator catches any exception from
``run_public_user_simulator`` and falls back to the i18n feedback
template so the cycle can continue.  Pre-fix, that fallback was
silent — the trace just showed empty user_simulator fields and a
boilerplate ``safe_user_feedback``, and operators couldn't tell
whether the model failed or simply produced no output.

Round 9 / A3 surfaces the failure to operators:
- ``user_simulator_failed`` (bool)
- ``user_simulator_error_type``: timeout / rate_limit / runtime / unknown
- ``user_simulator_error_message_sanitized``: redacted error text
- ``fallback_feedback_used`` (bool): True when safe_user_feedback came
  from the i18n generic template (no real signal)
- ``fallback_source``: user_simulator / missing_artifacts / guidance_tags
  / generic

These tests pin the classification + redaction + payload wiring.
Heavy supervisor IO is stubbed; we drive ``run_supervisor`` directly.
"""
from __future__ import annotations

from lib.supervision import orchestrator


# ── error classification ──────────────────────────────────────────────


def test_classify_timeout_messages():
    for msg in ("Codex timeout after 300s", "deadline exceeded", "subprocess.TimeoutExpired"):
        # timeout takes priority over runtime since "TimeoutExpired" also
        # contains "Expired" but we check timeout needles first.
        assert orchestrator._classify_user_simulator_error(msg) == "timeout", msg


def test_classify_rate_limit_messages():
    for msg in (
        "rate_limit_exceeded",
        "HTTP 429 Too Many Requests",
        "provider throttled the request",
        "rate-limited by upstream",
        "quota exceeded for this minute",
    ):
        assert orchestrator._classify_user_simulator_error(msg) == "rate_limit", msg


def test_classify_runtime_messages():
    for msg in (
        "ValueError: bad json",
        "TypeError in render",
        "Traceback (most recent call last):",
        "subprocess.SubprocessError",
    ):
        assert orchestrator._classify_user_simulator_error(msg) == "runtime", msg


def test_classify_empty_or_unknown():
    assert orchestrator._classify_user_simulator_error("") == "unknown"
    assert orchestrator._classify_user_simulator_error(None) == "unknown"
    assert orchestrator._classify_user_simulator_error("uhm") == "unknown"


# ── error sanitization ───────────────────────────────────────────────


def test_sanitize_strips_paths_and_clamps():
    """The sanitizer reuses content.sanitize_codex_context_text which
    strips host paths + long base64; here we just sanity-check it
    doesn't leak the host path and clamps to 600 chars.

    Uses the current repo's ROOT so the test is portable across hosts
    (Mac dev box vs. worker3 worker) — the sanitizer only redacts paths
    that match the *current* repo root, not a hard-coded one.
    """
    from lib.defaults import ROOT

    repo_path = str(ROOT)
    long_msg = (
        f"Traceback at {repo_path}/lib/supervision/...\n"
        + "x" * 1200
    )
    cleaned = orchestrator._sanitize_user_simulator_error(long_msg)
    assert len(cleaned) <= 600
    # Repo root rewrites to [repo]
    assert repo_path not in cleaned


def test_sanitize_empty():
    assert orchestrator._sanitize_user_simulator_error("") == ""
    assert orchestrator._sanitize_user_simulator_error(None) == ""


# ── feedback_rewriter fallback_source classification ─────────────────


def test_feedback_rewriter_marks_generic_fallback_when_empty():
    """No candidate, no public points, no guidance → generic fallback."""
    from lib.supervision.feedback_rewriter import rewrite_feedback
    from types import SimpleNamespace

    task = SimpleNamespace(
        public_task="please write a hello world",
        safe_user_feedback_mode="composed",
    )
    context = SimpleNamespace(task=task)
    user_handoff = {"verdict": "continue", "attempt_state": "in_progress"}
    public_user = {
        "candidate_feedback": "",
        "public_feedback_points": [],
    }
    out = rewrite_feedback(context, user_handoff, public_user, guidance_tags=[])
    debug = out["_debug"]
    assert debug["fallback_feedback_used"] is True
    assert debug["fallback_source"] == "generic"


def test_feedback_rewriter_marks_user_simulator_source():
    """Non-empty candidate_feedback → fallback_source=user_simulator
    (no fallback boilerplate)."""
    from lib.supervision.feedback_rewriter import rewrite_feedback
    from types import SimpleNamespace

    task = SimpleNamespace(public_task="t", safe_user_feedback_mode="candidate_only")
    context = SimpleNamespace(task=task)
    public_user = {
        "candidate_feedback": "Please try again with a clearer plan.",
        "public_feedback_points": [],
    }
    out = rewrite_feedback(context, {"verdict": "continue"}, public_user, guidance_tags=[])
    debug = out["_debug"]
    assert debug["fallback_feedback_used"] is False
    assert debug["fallback_source"] == "user_simulator"


def test_feedback_rewriter_marks_guidance_tags_source():
    """Empty candidate + public, guidance present → fallback_source=guidance_tags.

    Note: feedback_mode is read from the ``mode`` kwarg (not from
    task), defaults to candidate_only.  Use composed mode here so the
    rewriter actually consults guidance hints."""
    from lib.supervision.feedback_rewriter import rewrite_feedback
    from lib.constants import SAFE_USER_FEEDBACK_MODE_COMPOSED
    from types import SimpleNamespace

    task = SimpleNamespace(public_task="t")
    context = SimpleNamespace(task=task)
    public_user = {
        "candidate_feedback": "",
        "public_feedback_points": [],
    }
    out = rewrite_feedback(
        context, {"verdict": "continue"}, public_user,
        # Use a real guidance_tag that exists in lib/i18n.py
        guidance_tags=["save_visible_evidence"],
        mode=SAFE_USER_FEEDBACK_MODE_COMPOSED,
    )
    debug = out["_debug"]
    assert debug["fallback_feedback_used"] is False
    assert debug["fallback_source"] == "guidance_tags"


def test_feedback_rewriter_marks_missing_artifacts_source():
    """Empty candidate + non-empty public_feedback_points → fallback_source=missing_artifacts."""
    from lib.supervision.feedback_rewriter import rewrite_feedback
    from lib.constants import SAFE_USER_FEEDBACK_MODE_COMPOSED
    from types import SimpleNamespace

    task = SimpleNamespace(public_task="t")
    context = SimpleNamespace(task=task)
    public_user = {
        "candidate_feedback": "",
        "public_feedback_points": ["save the result to result/output.json"],
    }
    out = rewrite_feedback(
        context, {"verdict": "continue"}, public_user,
        guidance_tags=[],
        mode=SAFE_USER_FEEDBACK_MODE_COMPOSED,
    )
    debug = out["_debug"]
    assert debug["fallback_feedback_used"] is False
    assert debug["fallback_source"] == "missing_artifacts"
