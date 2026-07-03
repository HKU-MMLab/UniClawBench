"""Architectural invariant tests for the supervisor → user_simulator boundary.

The benchmark's core promise is that the public user simulator roleplays
as a *naive user* who cannot see the supervisor's internal analysis and
cannot see hidden references. The implementation enforces this through
two code paths:

  1. ``run_public_user_simulator`` in ``lib/user_simulator.py`` builds
     its ``supervisor_feedback`` dict from EXACTLY four handoff fields
     (verdict, attempt_state, recoverable, score) — not from the full
     supervisor payload.
  2. It calls ``prepare_role_workspace(..., include_hidden_references=False)``
     which deliberately hides ``references/`` from the role's workspace.

If either invariant drifts (for example, someone adds ``rationale`` to
the handoff, or flips ``include_hidden_references`` to True), these
tests fail loudly. The tests use mock surgery, so they never spin up
Docker or call a real LLM.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from lib.supervision import user_simulator as user_simulator_module
from lib.supervision.user_simulator import run_public_user_simulator


def _make_context(tmp_path: Path):
    """Minimal SupervisorContext-like object with just what the role needs.

    ``role_session_dir`` / ``role_workspace_dir`` / ``role_home_dir`` in
    supervision_common derive paths from ``context.attempt.out_dir``,
    so a real directory is needed.
    """
    role_cfg = SimpleNamespace(
        model="native-openai-proxy/gpt-4.1",
        provider="native-openai-proxy",
        config_path="configs/codex.local.toml",
        reasoning_effort="medium",
        instructions="",
        policy="",
    )
    task = SimpleNamespace(
        public_task="Do something.",
        user_simulator=role_cfg,
    )
    out_dir = tmp_path / "attempt"
    out_dir.mkdir(parents=True, exist_ok=True)
    attempt = SimpleNamespace(turn=1, out_dir=out_dir)
    return SimpleNamespace(task=task, attempt=attempt)


def _fake_codex_response():
    return {
        "parsed": {
            "mode": "nudge",
            "tone": "neutral",
            "candidate_feedback": "Please continue.",
            "public_feedback_points": [],
        },
        "transport": "test-mock",
        "elapsed_ms": 0,
        "stdout": "",
        "stderr": "",
        "raw_response": None,
        "prompt": "",
        "image_inputs": [],
        "workspace_manifest": {},
        "workspace_readme": "",
        "workspace_root": "",
    }


def test_user_simulator_never_sees_hidden_references(tmp_path, monkeypatch) -> None:
    """The user_simulator workspace must always be prepared with
    ``include_hidden_references=False`` — otherwise the naive-user role
    would leak knowledge from the judging references."""
    captured: dict = {}

    def fake_prepare(context, role_name, *, include_hidden_references=True, supervisor_feedback=None, **kwargs):
        captured["role_name"] = role_name
        captured["include_hidden_references"] = include_hidden_references
        return {"manifest": {"role": role_name}, "images": [], "readme": ""}

    monkeypatch.setattr(user_simulator_module, "prepare_role_workspace", fake_prepare)
    monkeypatch.setattr(user_simulator_module, "run_codex_prompt", lambda **kw: _fake_codex_response())
    monkeypatch.setattr(user_simulator_module, "append_role_history", lambda *a, **kw: None)

    run_public_user_simulator(
        _make_context(tmp_path),
        user_handoff={"verdict": "continue", "attempt_state": "incomplete", "recoverable": True, "score": 0.35},
    )

    assert captured["role_name"] == "public_user_simulator"
    assert captured["include_hidden_references"] is False, (
        "user_simulator must NEVER be given hidden references — this flag is "
        "the red line between the naive-user role and the supervisor role."
    )


def test_user_simulator_sees_exactly_four_handoff_fields(tmp_path, monkeypatch) -> None:
    """The supervisor_feedback.json written to the user_simulator workspace
    must contain exactly {verdict, attempt_state, recoverable, score} —
    no rationale, no confidence, no missing_artifacts, no guidance_tags.

    This locks the 4-field handoff documented in README §角色边界 and
    docs/01_runtime_flow.md §4.
    """
    captured: dict = {}

    def fake_prepare(context, role_name, *, include_hidden_references=True, supervisor_feedback=None, **kwargs):
        captured["supervisor_feedback"] = dict(supervisor_feedback or {})
        return {"manifest": {"role": role_name}, "images": [], "readme": ""}

    monkeypatch.setattr(user_simulator_module, "prepare_role_workspace", fake_prepare)
    monkeypatch.setattr(user_simulator_module, "run_codex_prompt", lambda **kw: _fake_codex_response())
    monkeypatch.setattr(user_simulator_module, "append_role_history", lambda *a, **kw: None)

    # Try to pass a handoff with *extra* fields — they must not leak through.
    run_public_user_simulator(
        _make_context(tmp_path),
        user_handoff={
            "verdict": "continue",
            "attempt_state": "incomplete",
            "recoverable": True,
            "score": 0.35,
            # Fields below are supervisor-internal and MUST NOT propagate.
            "rationale": "hidden: the executor missed checkpoint 2",
            "missing_artifacts": ["hidden: screenshot of video 3"],
            "confidence": "high",
            "guidance_tags": ["save_supporting_screenshot"],
        },
    )

    fb = captured["supervisor_feedback"]
    assert set(fb.keys()) == {"verdict", "attempt_state", "recoverable", "score"}, (
        f"user_simulator supervisor_feedback must be exactly 4 fields; got keys {sorted(fb.keys())}"
    )
    # Explicitly verify none of the hidden-analysis fields leaked.
    for leaked in ("rationale", "missing_artifacts", "confidence", "guidance_tags"):
        assert leaked not in fb, f"{leaked!r} leaked into user_simulator supervisor_feedback"


def test_user_simulator_passes_handoff_values_through_unchanged(tmp_path, monkeypatch) -> None:
    """The 4 handoff values themselves must round-trip faithfully — the
    simulator role is supposed to act on them."""
    captured: dict = {}

    def fake_prepare(context, role_name, *, include_hidden_references=True, supervisor_feedback=None, **kwargs):
        captured["supervisor_feedback"] = dict(supervisor_feedback or {})
        return {"manifest": {"role": role_name}, "images": [], "readme": ""}

    monkeypatch.setattr(user_simulator_module, "prepare_role_workspace", fake_prepare)
    monkeypatch.setattr(user_simulator_module, "run_codex_prompt", lambda **kw: _fake_codex_response())
    monkeypatch.setattr(user_simulator_module, "append_role_history", lambda *a, **kw: None)

    run_public_user_simulator(
        _make_context(tmp_path),
        user_handoff={"verdict": "continue", "attempt_state": "complete_but_failed", "recoverable": True, "score": 0.42},
    )

    fb = captured["supervisor_feedback"]
    assert fb["verdict"] == "continue"
    assert fb["attempt_state"] == "complete_but_failed"
    assert fb["recoverable"] is True
    assert fb["score"] == 0.42
