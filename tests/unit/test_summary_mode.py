"""Round 9 / A2 regression: supervision summary mode hyperparameter.

``CLAWBENCH_SUPERVISION_SUMMARY_MODE`` lets the operator dial how
thick the supervisor / user-simulator visible+hidden payload is.
5 levels:

  off       file index + image downsampling only
  wocr      off + OCR blocks
  wpreview  off + result-file text previews
  wsummary  off + semantic_transcript_blocks (DEFAULT)
  full      everything (OCR + preview + semantic + hidden eval_rule preview)

Image downsampling is ALWAYS on (independent of mode) since it's a
token-budget control, not a summary shortcut.

This test file pins:
- env var name + default value
- which modes include which payload sections
- summarize_result_dir / summarize_file honor the preview gate
- unknown mode falls back to default with a warning
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lib.supervision import content as content_mod


# ── module constants ──────────────────────────────────────────────────


def test_summary_mode_env_name_is_canonical():
    assert content_mod.SUMMARY_MODE_ENV == "CLAWBENCH_SUPERVISION_SUMMARY_MODE"


def test_summary_modes_canonical_set():
    assert content_mod.SUMMARY_MODES == ("off", "wocr", "wpreview", "wsummary", "full")


def test_default_summary_mode_is_wsummary():
    assert content_mod.DEFAULT_SUMMARY_MODE == "wsummary"


# ── resolver behavior ──────────────────────────────────────────────────


def test_supervision_summary_mode_default(monkeypatch):
    """Unset env → default ``wsummary``."""
    monkeypatch.delenv(content_mod.SUMMARY_MODE_ENV, raising=False)
    assert content_mod.supervision_summary_mode() == "wsummary"


@pytest.mark.parametrize("mode", ["off", "wocr", "wpreview", "wsummary", "full"])
def test_supervision_summary_mode_accepts_each_canonical(monkeypatch, mode):
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, mode)
    assert content_mod.supervision_summary_mode() == mode


def test_supervision_summary_mode_case_insensitive(monkeypatch):
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "FULL")
    assert content_mod.supervision_summary_mode() == "full"
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "  Wsummary  ")
    assert content_mod.supervision_summary_mode() == "wsummary"


def test_supervision_summary_mode_unknown_falls_back(monkeypatch, caplog):
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "verbose")  # invalid
    import logging
    with caplog.at_level(logging.WARNING, logger="lib.supervision.content"):
        assert content_mod.supervision_summary_mode() == "wsummary"
    assert any("unknown" in r.message.lower() for r in caplog.records)


# ── per-mode gating predicates ────────────────────────────────────────


@pytest.mark.parametrize("mode,expected", [
    ("off", False),
    ("wocr", True),
    ("wpreview", False),
    ("wsummary", False),
    ("full", True),
])
def test_includes_ocr_matrix(mode, expected):
    assert content_mod._summary_mode_includes_ocr(mode) == expected


@pytest.mark.parametrize("mode,expected", [
    ("off", False),
    ("wocr", False),
    ("wpreview", True),
    ("wsummary", False),
    ("full", True),
])
def test_includes_preview_matrix(mode, expected):
    assert content_mod._summary_mode_includes_preview(mode) == expected


@pytest.mark.parametrize("mode,expected", [
    ("off", False),
    ("wocr", False),
    ("wpreview", False),
    ("wsummary", True),
    ("full", True),
])
def test_includes_semantic_matrix(mode, expected):
    assert content_mod._summary_mode_includes_semantic(mode) == expected


@pytest.mark.parametrize("mode,expected", [
    ("off", False),
    ("wocr", False),
    ("wpreview", False),
    ("wsummary", False),
    ("full", True),
])
def test_includes_hidden_extras_matrix(mode, expected):
    assert content_mod._summary_mode_includes_hidden_extras(mode) == expected


# ── summarize_result_dir preview gating ───────────────────────────────


def test_summarize_file_preview_default_true(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    out = content_mod.summarize_file(f, base=tmp_path)
    assert out["path"] == "a.txt"
    assert out["kind"] == "text"
    assert out.get("preview") == "hello world"


def test_summarize_file_preview_opt_out(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    out = content_mod.summarize_file(f, base=tmp_path, include_text_preview=False)
    assert out["path"] == "a.txt"
    assert out["kind"] == "text"
    assert "preview" not in out, out


def test_summarize_result_dir_preview_gate(tmp_path):
    (tmp_path / "result").mkdir()
    (tmp_path / "result" / "out.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "result" / "log.json").write_text("{}", encoding="utf-8")

    with_preview = content_mod.summarize_result_dir(tmp_path / "result", include_text_preview=True)
    no_preview = content_mod.summarize_result_dir(tmp_path / "result", include_text_preview=False)

    # Both list the files.
    assert sorted(e["path"] for e in with_preview) == ["log.json", "out.txt"]
    assert sorted(e["path"] for e in no_preview) == ["log.json", "out.txt"]
    # With preview: text files carry preview.  Without: they don't.
    assert any("preview" in e for e in with_preview)
    assert all("preview" not in e for e in no_preview)


def test_summarize_result_dir_empty(tmp_path):
    """Non-existent result dir returns empty list (not error)."""
    assert content_mod.summarize_result_dir(tmp_path / "missing") == []


# ── payload composition (smoke; no real codex) ────────────────────────


def test_supervision_summary_mode_recorded_in_visible_payload(monkeypatch, tmp_path):
    """``build_visible_payload`` writes ``supervision_summary_mode`` so
    the workspace manifest can echo it without re-reading env."""
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "off")
    # Stub-out the heavy supervisor context dependencies; we only test
    # that the mode tag lands in the dict.  Use a minimal context.
    from types import SimpleNamespace

    attempt = SimpleNamespace(
        prompt_file=tmp_path / "prompt.md",
        result_dir=tmp_path / "result",
        transcript_file=tmp_path / "transcript.jsonl",
        tool_usage_file=tmp_path / "tool_usage.json",
        runtime_probe_file=tmp_path / "runtime_probe.json",
        out_dir=tmp_path,
    )
    task = SimpleNamespace(public_task="t", references=[], injection_root=tmp_path)
    context = SimpleNamespace(attempt=attempt, task=task)
    (tmp_path / "prompt.md").write_text("hi", encoding="utf-8")
    (tmp_path / "result").mkdir()

    payload = content_mod.build_visible_payload(context)
    assert payload["supervision_summary_mode"] == "off"
    # off mode → no OCR / semantic blocks
    assert "visible_image_ocr_blocks" not in payload
    assert "semantic_transcript_blocks" not in payload
    # off mode → result_files entries have no preview
    assert all("preview" not in e for e in payload["result_files"])


def test_supervision_summary_mode_full_includes_everything(monkeypatch, tmp_path):
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "full")
    from types import SimpleNamespace

    attempt = SimpleNamespace(
        prompt_file=tmp_path / "prompt.md",
        result_dir=tmp_path / "result",
        transcript_file=tmp_path / "transcript.jsonl",
        tool_usage_file=tmp_path / "tool_usage.json",
        runtime_probe_file=tmp_path / "runtime_probe.json",
        out_dir=tmp_path,
    )
    task = SimpleNamespace(public_task="t", references=[], injection_root=tmp_path)
    context = SimpleNamespace(attempt=attempt, task=task)
    (tmp_path / "prompt.md").write_text("hi", encoding="utf-8")
    (tmp_path / "result").mkdir()
    (tmp_path / "transcript.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "tool_usage.json").write_text("{}", encoding="utf-8")
    (tmp_path / "runtime_probe.json").write_text("{}", encoding="utf-8")

    payload = content_mod.build_visible_payload(context)
    assert payload["supervision_summary_mode"] == "full"
    # full mode → all gated sections present
    assert "visible_image_ocr_blocks" in payload
    assert "semantic_transcript_blocks" in payload
    assert "operation_trace_summary" in payload


def test_supervision_hidden_payload_off_mode_lists_files_only(monkeypatch, tmp_path):
    """Even in ``off`` mode, ``reference_files`` is still listed — the
    supervisor must know what to open for first-hand reading.  Only the
    preview text + OCR are gated."""
    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "off")
    from types import SimpleNamespace

    task = SimpleNamespace(
        references=["references/eval_rule.md", "references/spec.png"],
        injection_root=tmp_path,
    )
    context = SimpleNamespace(task=task)

    payload = content_mod.build_hidden_payload(context)
    assert payload["supervision_summary_mode"] == "off"
    assert payload["reference_files"] == [
        "references/eval_rule.md",
        "references/spec.png",
    ]
    # Off mode hides eval_rule preview + reference image OCR + text blocks
    assert "primary_eval_rule" not in payload
    assert "text_reference_blocks" not in payload
    assert "reference_image_ocr_blocks" not in payload


def test_workspace_manifest_records_supervision_summary_mode(monkeypatch):
    """Round 9 / Phase D follow-up: workspace_manifest.json must
    surface ``supervision_summary_mode`` so post-run audit can answer
    "which hyperparameter governed this attempt's supervisor prompt?"

    Discovered when worker3 attempts came back with the field as None at
    the manifest level — only visible/hidden payloads carried it.
    """
    from lib.supervision.workspace import _supervision_summary_mode_resolved

    monkeypatch.setenv(content_mod.SUMMARY_MODE_ENV, "wpreview")
    assert _supervision_summary_mode_resolved() == "wpreview"
    monkeypatch.delenv(content_mod.SUMMARY_MODE_ENV, raising=False)
    assert _supervision_summary_mode_resolved() == "wsummary"


def test_workspace_manifest_dict_contains_summary_mode_key():
    """Source-level guard so the manifest write site never drops the
    key on a refactor.  We don't run a full workspace build in this
    unit test — but we do confirm the dict-literal at the write site
    references _supervision_summary_mode_resolved()."""
    from pathlib import Path
    text = Path(__file__).resolve().parents[2].joinpath(
        "lib/supervision/workspace.py"
    ).read_text(encoding="utf-8")
    assert '"supervision_summary_mode": _supervision_summary_mode_resolved()' in text, (
        "workspace_manifest.json must record supervision_summary_mode"
    )
