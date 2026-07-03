"""Round 16 / P2-2: ``codex.build_session_prompt`` must thread
``workspace_manifest['privacy_available']`` into
``_role_workspace_prompt_files`` so the answer_supervisor wrapper
mentions the ``privacy/`` directory when there are real privacy
assets to inspect.

Before the fix, ``build_session_prompt`` invoked
``_role_workspace_prompt_files(role_name)`` with the default
``has_privacy=False``, so the wrapper's "Start Here" list missed
``privacy/`` even when the workspace README enumerated it.
``answer_supervisor`` could still find the directory by reading the
README, but the prompt was inconsistent — masking grading errors when
the supervisor relied on the explicit file list.
"""
from __future__ import annotations

import re
from typing import Any

import pytest

from lib.supervision import codex as codex_mod


def _build_prompt(role: str, *, privacy_available: bool) -> str:
    return codex_mod.build_session_prompt(
        role_name=role,
        role_instructions="be careful",
        workspace_manifest={"privacy_available": privacy_available, "files": []},
    )


def test_answer_supervisor_with_privacy_lists_privacy_dir() -> None:
    text = _build_prompt("answer_supervisor", privacy_available=True)
    assert "privacy/" in text, (
        "answer_supervisor prompt must list `privacy/` when the manifest "
        "advertises privacy_available=True"
    )


def test_answer_supervisor_without_privacy_omits_privacy_dir() -> None:
    text = _build_prompt("answer_supervisor", privacy_available=False)
    assert "privacy/" not in text, (
        "answer_supervisor prompt must NOT list `privacy/` when the "
        "manifest does not declare privacy_available"
    )


def test_public_user_simulator_never_lists_privacy_dir() -> None:
    """``public_user_simulator`` should never see privacy assets,
    regardless of the manifest flag — that's the role's whole point."""
    text_on = _build_prompt("public_user_simulator", privacy_available=True)
    text_off = _build_prompt("public_user_simulator", privacy_available=False)
    assert "privacy/" not in text_on
    assert "privacy/" not in text_off


def test_executor_role_never_lists_privacy_dir() -> None:
    """The executor role uses a different prompt path entirely, but if
    something accidentally pushed it through ``build_session_prompt``,
    privacy should still stay invisible."""
    text = _build_prompt("executor", privacy_available=True)
    assert "privacy/" not in text


def test_prompt_includes_role_name_and_instructions() -> None:
    """Sanity check: the template still renders the role and the
    instructions block so the privacy threading didn't regress the
    rest of the wrapper."""
    text = _build_prompt("answer_supervisor", privacy_available=True)
    # role_name appears in the wrapper (template-driven).
    assert "answer_supervisor" in text
    assert "be careful" in text
