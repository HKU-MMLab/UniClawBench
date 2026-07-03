"""Cover the per-attempt directory naming.

``stage_dir_name`` is the contract that lets concurrent workers drop
attempt directories into the same task directory without colliding —
the worker exports ``CLAWBENCH_HOST_TAG`` and the function bakes it
into the dir name as a middle segment.

If this contract regresses (e.g. someone drops the env-var read), two
workers picking the same task at the same time will overwrite each
other's attempts silently — exactly the bug class the host tag was
introduced to prevent.
"""
from __future__ import annotations

import re

import pytest

from lib.runner.orchestration import stage_dir_name


@pytest.fixture(autouse=True)
def _clear_host_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAWBENCH_HOST_TAG", raising=False)


def test_no_host_tag_yields_legacy_format() -> None:
    name = stage_dir_name(1)
    assert re.fullmatch(r"p1-[0-9a-f]{6}", name), name


def test_explicit_host_tag_inserted_as_middle_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAWBENCH_HOST_TAG", "worker3")
    name = stage_dir_name(1)
    assert re.fullmatch(r"p1-worker3-[0-9a-f]{6}", name), name


def test_attempt_no_propagates_to_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAWBENCH_HOST_TAG", "worker4")
    name = stage_dir_name(7)
    assert name.startswith("p7-worker4-"), name


def test_host_tag_lower_cased(monkeypatch: pytest.MonkeyPatch) -> None:
    """``CLAWBENCH_HOST_TAG=worker3`` must produce ``p1-worker3-...`` for
    consistency with the SSH alias the dispatcher logs against."""
    monkeypatch.setenv("CLAWBENCH_HOST_TAG", "worker3")
    name = stage_dir_name(1)
    assert name.startswith("p1-worker3-"), name


def test_host_tag_whitespace_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAWBENCH_HOST_TAG", "  worker4  ")
    name = stage_dir_name(2)
    assert name.startswith("p2-worker4-"), name


def test_empty_host_tag_falls_through_to_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty-string env var must NOT produce ``p1--<hex>`` — that's a
    silent bug class where the orchestrator thinks the host is tagged
    but the tag string is missing."""
    monkeypatch.setenv("CLAWBENCH_HOST_TAG", "")
    name = stage_dir_name(1)
    assert re.fullmatch(r"p1-[0-9a-f]{6}", name), name


def test_unique_suffix_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even on the same host the suffix must change every call, or two
    concurrent attempts of the same (task, host) would collide."""
    monkeypatch.setenv("CLAWBENCH_HOST_TAG", "worker1")
    seen = {stage_dir_name(1) for _ in range(20)}
    assert len(seen) == 20
