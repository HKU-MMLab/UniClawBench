"""Shared pytest fixtures for unit / integration / e2e tests.

The three test tiers live under ``tests/{unit,integration,e2e}/``:

* ``unit/``        pure logic, no IO, milliseconds
* ``integration/`` multi-module wiring, mock IO at the boundary
* ``e2e/``         orchestra dispatch round-trip, ssh + subprocess
                   mocked but real file IO on a temp runs tree

Fixtures defined here are visible to every tier.  Tier-specific
fixtures live in the tier's own ``conftest.py``.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterator

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

# Make ``lib`` / ``scripts`` importable from every test file without
# each one re-doing the sys.path dance.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# New clones do not have ``configs/models.local.json``. Production code keeps
# requiring an explicit local registry, but the test suite should be runnable
# from a clean checkout without private provider credentials.
os.environ.setdefault("CLAWBENCH_ALLOW_EXAMPLE_CONFIG", "1")


@pytest.fixture
def repo_root() -> Path:
    """The Clawbench repo root, useful for tests that want to read
    static fixture files committed in-tree (configs/, tasks/, etc.)."""
    return REPO_ROOT


@pytest.fixture
def tmp_runs_root(tmp_path: Path) -> Path:
    """A blank runs/ tree under a per-test ``tmp_path``.

    Tests that exercise the orchestra dispatcher's file IO use this to
    avoid touching any developer-specific external data mount or leaving
    stray attempt directories in the workspace.
    """
    runs = tmp_path / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    return runs


@pytest.fixture
def mock_models_registry() -> list[str]:
    """A small synthetic provider/model registry — five entries spanning
    the dot/dash/underscore edge cases that the real
    ``configs/models.local.json`` produces.

    Used by tests that exercise ``lib.util.model_naming`` without
    depending on whatever's in the live config.
    """
    return [
        "fake_a/model-1.0",
        "fake_a/model.2.0",
        "fake_b/aws.claude-test-4.6",
        "fake_b/gpt-5.4",
        "fake_c/no-dots-here",
    ]


@pytest.fixture
def write_models_json(tmp_path: Path) -> Iterator[Path]:
    """Helper that writes a synthetic models.local.json to tmp and
    returns its path; useful when a test needs to exercise the
    ``load_registry`` filesystem code path."""
    payload = {
        "providers": {
            "fake_a": {"models": [{"id": "model-1.0"}, {"id": "model.2.0"}]},
            "fake_b": {"models": [{"id": "aws.claude-test-4.6"}, {"id": "gpt-5.4"}]},
            "fake_c": {"models": [{"id": "no-dots-here"}]},
        }
    }
    target = tmp_path / "models.local.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    yield target
