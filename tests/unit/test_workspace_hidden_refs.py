"""Round 9 / A4 regression: hidden_references manifest reflects real copy state.

Pre-fix, ``workspace_manifest.json:hidden_references_available`` just
echoed the ``include_hidden_references`` parameter — it lied when the
task declared references that weren't actually on disk (eval_rule.md
missing, image path typo, etc.).  Supervisor saw the manifest, assumed
the rubric was present, and graded freely without consulting it.

Round 9 / A4 splits the manifest field into:

  hidden_references_requested   (caller's intent)
  hidden_references_available   (reality: at least primary eval_rule.md
                                  copied AND at least 1 ref copied)
  hidden_references_copied_count
  hidden_references_missing
  primary_eval_rule_available
  primary_eval_rule_path

These tests pin the new fields against three scenarios:
- include=True + eval_rule + 1 image all present → all positive
- include=True + eval_rule missing → available=False, missing lists it
- include=False → requested=False, copied_count=0
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import json
import pytest

from lib.supervision.workspace import _copy_reference_workspace_files


def _build_context(tmp_path: Path, references: list[str], create_files: dict[str, str] | None = None):
    """Build a minimal SupervisorContext stub for _copy_reference_workspace_files."""
    injection = tmp_path / "injection"
    injection.mkdir(parents=True, exist_ok=True)
    refs_src = injection / "references"
    refs_src.mkdir(exist_ok=True)
    for rel, body in (create_files or {}).items():
        target = injection / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    task = SimpleNamespace(
        references=list(references),
        injection_root=injection,
        public_task="t",
    )
    return SimpleNamespace(task=task)


def test_hidden_refs_all_present(tmp_path):
    """include + eval_rule.md + 1 image (text proxy) all on disk →
    copied_count=2, missing=[], primary_eval_rule_available=True."""
    context = _build_context(
        tmp_path,
        references=["references/eval_rule.md", "references/notes.md"],
        create_files={
            "references/eval_rule.md": "# eval rule\n",
            "references/notes.md": "supporting notes\n",
        },
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    files, image_paths, status = _copy_reference_workspace_files(context, workspace)
    assert status["hidden_references_copied_count"] == 2
    assert status["hidden_references_missing"] == []
    assert status["primary_eval_rule_available"] is True
    assert status["primary_eval_rule_path"] == "references/eval_rule.md"


def test_hidden_refs_eval_rule_missing(tmp_path):
    """eval_rule.md declared but not on disk → primary_eval_rule_available=False,
    missing lists it.  copied_count counts only what made it."""
    context = _build_context(
        tmp_path,
        references=["references/eval_rule.md", "references/notes.md"],
        create_files={
            # eval_rule.md NOT created; notes.md exists
            "references/notes.md": "supporting notes\n",
        },
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    files, image_paths, status = _copy_reference_workspace_files(context, workspace)
    assert status["primary_eval_rule_available"] is False
    assert "references/eval_rule.md" in status["hidden_references_missing"]
    # notes.md still copied; eval_rule.md missing → count = 1
    assert status["hidden_references_copied_count"] == 1


def test_hidden_refs_all_missing(tmp_path):
    """No references on disk at all → 0 copied, all listed missing,
    primary_eval_rule_available=False."""
    context = _build_context(
        tmp_path,
        references=["references/eval_rule.md", "references/spec.png"],
        create_files={},  # nothing on disk
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    files, image_paths, status = _copy_reference_workspace_files(context, workspace)
    assert status["primary_eval_rule_available"] is False
    assert status["hidden_references_copied_count"] == 0
    assert sorted(status["hidden_references_missing"]) == sorted([
        "references/eval_rule.md",
        "references/spec.png",
    ])


def test_hidden_refs_empty_task(tmp_path):
    """Task declares no references → empty status (no missing).  The
    role workspace then has no rubric — caller should detect this and
    pre-empt the supervisor call (treats as pre_exec_failed-ish)."""
    context = _build_context(tmp_path, references=[], create_files={})
    workspace = tmp_path / "ws"
    workspace.mkdir()
    files, image_paths, status = _copy_reference_workspace_files(context, workspace)
    assert status["hidden_references_copied_count"] == 0
    assert status["hidden_references_missing"] == []
    assert status["primary_eval_rule_available"] is False
