"""Regression: worker_runner must locate the attempt dir under the same
canonical model directory that run_eval/run_task writes.  The shared
``model_slug(model_full)`` contract keeps single-task and orchestra results
relocatable without per-path rewrites.
"""
from __future__ import annotations

import os
import time

from lib.runner.task_config import model_slug
from scripts.orchestra.worker_runner import _model_slug, _find_attempt_dir


def test_worker_slug_matches_run_task_slug():
    # worker_runner's slug must be byte-identical to the one run_task uses, for
    # ANY model name — that's what makes the fix general, not opus-specific.
    for full in [
        "provider_primary/vendor-claude-opus-4.8-privateSuffix",
        "provider_primary/gpt-5.4",
        "provider_metered/gpt-4.1",
        "provider_next/kimi-k2.6",
        "provider_next/gemini-3.1-pro-preview",
        "Weird/Model.Name-V2_FINAL",
    ]:
        assert _model_slug(full) == model_slug(full), full


def test_find_attempt_dir_under_canonical_slug(tmp_path):
    full = "provider_primary/vendor-claude-opus-4.8-privateSuffix"
    slug = _model_slug(full)
    config_model_dir = model_slug(full)
    assert slug == config_model_dir

    # run_task writes the attempt dir under the canonical slug:
    attempt = tmp_path / "openclaw" / slug / "101_skill_usage" / "task_x" / "p1-worker1-abc123"
    attempt.mkdir(parents=True)

    assert _find_attempt_dir(tmp_path, "openclaw", slug, "101_skill_usage", "task_x") == attempt


def test_find_attempt_dir_ignores_attempts_older_than_current_run(tmp_path):
    task_dir = tmp_path / "openclaw" / "model-a" / "101_skill_usage" / "task_x"
    old = task_dir / "p1-worker1-old"
    old.mkdir(parents=True)
    old_mtime = time.time() - 60
    os.utime(old, (old_mtime, old_mtime))

    assert _find_attempt_dir(
        tmp_path,
        "openclaw",
        "model-a",
        "101_skill_usage",
        "task_x",
        min_mtime=time.time() - 1,
    ) is None
