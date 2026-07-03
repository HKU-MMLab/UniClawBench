"""Round 8 / B1 regression: chunked_transcripts metadata must not leak
host absolute paths into the role workspace.

From 2026-05-14 code review:

> ``chunked_transcripts`` carries ``source_path``, ``dest_path``,
> ``full_dir``, ``manifest_path`` — all host absolute paths.  These
> end up in ``workspace_manifest.json`` which the role prompt
> reads.  The role only needs role-workspace-relative paths; host
> absolute paths add token noise and leak internal layout for no
> benefit.

Round 8 / B1: replace host paths with role-workspace-relative paths.
``source_path`` / ``dest_path`` removed (the caller already adds
``rel_path``).  ``full_dir`` / ``manifest_path`` replaced with
``full_dir_rel`` / ``manifest_rel`` keyed relative to the role's
workspace_root.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.supervision.workspace import _copy_transcript_with_optional_chunking


# Helpers
_BIG_LINE = '{"x": "' + ("a" * 200) + '"}\n'


def _build_big_transcript(tmp_path: Path, line_count: int) -> Path:
    """Write a transcript large enough to trigger chunking
    (> _TRANSCRIPT_CHUNK_MAX_BYTES which defaults to 80 KB).  At 220
    bytes per line, 500 lines is ~110 KB."""
    src = tmp_path / "transcript.jsonl"
    src.write_text(_BIG_LINE * line_count, encoding="utf-8")
    return src


def test_chunked_meta_omits_host_source_dest_paths(tmp_path: Path):
    """The chunked-transcript metadata must NOT carry ``source_path``
    or ``dest_path`` — those were host absolute paths in pre-Round-8."""
    src = _build_big_transcript(tmp_path, 500)
    workspace_root = tmp_path / "ws"
    visible = workspace_root / "visible"
    visible.mkdir(parents=True)
    dest = visible / "transcript.jsonl"

    meta = _copy_transcript_with_optional_chunking(src, dest, include_full_chunks=True)
    assert meta is not None
    assert "source_path" not in meta, meta
    assert "dest_path" not in meta, meta


def test_chunked_meta_uses_relative_paths_for_full_dir_and_manifest(tmp_path: Path):
    """Full-chunk metadata must use role-workspace-relative paths via
    ``full_dir_rel`` / ``manifest_rel`` instead of host absolute
    ``full_dir`` / ``manifest_path``."""
    src = _build_big_transcript(tmp_path, 500)
    workspace_root = tmp_path / "ws"
    visible = workspace_root / "visible"
    visible.mkdir(parents=True)
    dest = visible / "transcript.jsonl"

    meta = _copy_transcript_with_optional_chunking(src, dest, include_full_chunks=True)
    assert meta is not None
    # Old absolute-path fields are gone.
    assert "full_dir" not in meta
    assert "manifest_path" not in meta
    # New relative fields are present and don't contain the tmp_path
    # absolute prefix.
    assert "full_dir_rel" in meta
    assert "manifest_rel" in meta
    assert not Path(meta["full_dir_rel"]).is_absolute()
    assert not Path(meta["manifest_rel"]).is_absolute()
    # Just to be thorough: no field value contains the host workspace
    # root path.
    for value in meta.values():
        if isinstance(value, str):
            assert str(workspace_root) not in value, f"host path leaked: {value!r}"
            assert str(tmp_path) not in value, f"host path leaked: {value!r}"


def test_capped_only_meta_carries_minimal_fields(tmp_path: Path):
    """When ``include_full_chunks=False`` (user_simulator path), the
    metadata is the smaller capped-only dict; it must also be free of
    host absolute paths."""
    src = _build_big_transcript(tmp_path, 500)
    workspace_root = tmp_path / "ws"
    visible = workspace_root / "visible"
    visible.mkdir(parents=True)
    dest = visible / "transcript.jsonl"

    meta = _copy_transcript_with_optional_chunking(src, dest, include_full_chunks=False)
    assert meta is not None
    assert meta.get("capped_only") is True
    assert "source_path" not in meta
    assert "dest_path" not in meta
    for value in meta.values():
        if isinstance(value, str):
            assert str(tmp_path) not in value
