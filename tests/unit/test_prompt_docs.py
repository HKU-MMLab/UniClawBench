"""Phase 7B — ``docs/PROMPTS.md`` keeps the main role-prompt sections in sync.

The full template bodies live in ``lib/templates/*.py``. ``docs/PROMPTS.md``
mirrors them as a runnable spec for external readers. If a template header
or behaviour-policy block is renamed, deleted, or silently dropped from the
docs, this test fails so docs and code don't drift.

This is a *structural* snapshot — it checks for headings and key marker
strings, not for exact prose, so cosmetic edits to either side stay free.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS_DOC = REPO / "docs" / "PROMPTS.md"


def _doc_text() -> str:
    return PROMPTS_DOC.read_text(encoding="utf-8")


def test_prompts_doc_lists_the_three_role_prompts() -> None:
    text = _doc_text()
    assert "## 1. Session Wrapper" in text
    assert "## 2. Supervisor Prompt" in text
    assert "## 3. User Simulator Prompt" in text


def test_prompts_doc_declares_verdict_enum_and_attempt_states() -> None:
    """The narrowed Round-6 verdict set (`pass / continue / fail`) and the
    5-state attempt enum must be visible in the doc. If a future refactor
    re-widens supervisor verdicts back to include `infra_error`, this fails
    and forces an explicit decision.
    """
    text = _doc_text()
    assert "## Verdict Rules" in text or "Verdict Rules" in text
    assert "## Attempt States" in text or "Attempt States" in text
    for attempt_state in (
        "in_progress",
        "incomplete",
        "complete_but_failed",
        "complete_and_passed",
        "terminal_failure",
    ):
        assert attempt_state in text, f"{attempt_state} missing from PROMPTS.md"


def test_prompts_doc_excludes_obsolete_verbatim_claim() -> None:
    """Phase 1A renamed the "Appendix C verbatim" claim because the prompts
    have evolved past the paper baseline (image-on-demand, transcript
    chunking, narrowed schema). Make sure the obsolete claim doesn't sneak
    back in.
    """
    text = _doc_text()
    assert "Appendix C verbatim" not in text, (
        "PROMPTS.md must not re-introduce the 'Appendix C verbatim' claim — "
        "prompts have engineering refinements past the paper baseline."
    )


def test_prompts_doc_user_simulator_section_omits_task_specific_instructions() -> None:
    """Phase 1B removed the user simulator template's
    ``Task-Specific Instructions`` slot (no task YAML used it). The doc's
    user-simulator excerpt must therefore not advertise the slot."""
    text = _doc_text()
    # Find the User Simulator section.
    marker = "## 3. User Simulator Prompt"
    assert marker in text
    section_start = text.index(marker)
    section_end = text.index("## 4.", section_start) if "## 4." in text else len(text)
    section = text[section_start:section_end]
    assert "Task-Specific Instructions" not in section, (
        "user simulator excerpt should not list the removed "
        "'Task-Specific Instructions' slot"
    )
    # Behaviour Policy is the surviving customization channel.
    assert "Behavior Policy" in section


def test_prompts_doc_mentions_image_on_demand_supervisor_rule() -> None:
    """``CLAWBENCH_CODEX_ATTACH_IMAGES`` defaults to 0; ``view_image`` is the
    only image-access channel. This is one of the engineering refinements
    over the paper Appendix C baseline and must stay documented."""
    text = _doc_text()
    assert "view_image" in text
    assert "No images are pre-attached" in text


def test_prompts_doc_supervisor_section_references_eval_rule() -> None:
    """The supervisor's grading anchor is ``references/eval_rule.md``;
    drifting away from naming it would break authors who follow the doc."""
    text = _doc_text()
    assert "references/eval_rule.md" in text
