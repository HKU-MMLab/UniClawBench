"""Round 8 / A6 regression: refresh_one_task picks the BEST attempt
when multiple attempts of the same task share a status rank.

From 2026-05-14 code review:

> Pre-fix sort key was ``(status_rank, -i)``: at the same status, this
> always preferred the earliest attempt (largest -i = smallest i).
> Re-runs with fixed schemas, higher scores, or fresher artefacts got
> buried behind a stale first attempt.

Round 8 / A6 changes the key to:

    (status_rank, finalScore, non_synthetic, mtime, i)

so:
  - within a status, higher finalScore wins
  - non-synthetic (real summary.json) wins over synthetic
  - newer (higher mtime) wins
  - i is the final stable order
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from scripts.orchestra.refresh_summary import refresh_one_task


def _write_attempt(task_dir: Path, name: str, *, final_status: str, final_score: float | None = None) -> Path:
    p = task_dir / name
    p.mkdir(parents=True, exist_ok=True)
    payload = {
        "finalStatus": final_status,
        "passed": final_status == "pass",
    }
    if final_score is not None:
        payload["finalScore"] = final_score
    (p / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_higher_score_wins_at_same_status(tmp_path: Path) -> None:
    """Two ``fail`` attempts.  The one with the higher finalScore must
    be the resolved attempt — pre-fix this used to be whichever appeared
    first in directory order."""
    task_dir = tmp_path / "task_001"
    _write_attempt(task_dir, "p1-host-aaa", final_status="fail", final_score=0.2)
    _write_attempt(task_dir, "p2-host-bbb", final_status="fail", final_score=0.7)

    summary = refresh_one_task(task_dir)
    assert summary is not None
    # The higher-score attempt is at index 2 (sorted alphabetically).
    assert summary["resolvedAttempt"] == 2, summary
    assert summary["finalScore"] == 0.7


def test_non_synthetic_wins_over_synthetic(tmp_path: Path) -> None:
    """Two ``fail`` attempts with the same score.  The one with a real
    per-attempt summary.json wins over the one built via the
    synth-fallback (score.json + meta.json)."""
    task_dir = tmp_path / "task_002"
    # Real summary attempt
    _write_attempt(task_dir, "p1-host-real", final_status="fail", final_score=0.3)
    # Synthetic attempt: score.json + meta.json, no summary.json
    p_synth = task_dir / "p2-host-synth"
    p_synth.mkdir()
    (p_synth / "score.json").write_text(
        json.dumps({
            "verdict": "fail",
            "overall_score": 0.3,
            "capped_score": 0.3,
        }),
        encoding="utf-8",
    )
    (p_synth / "meta.json").write_text(
        json.dumps({"everExecutorCompleted": True, "agentExitCode": 0}),
        encoding="utf-8",
    )

    summary = refresh_one_task(task_dir)
    assert summary is not None
    # The non-synthetic real-summary attempt (index 1) must win.
    assert summary["resolvedAttempt"] == 1, summary


def test_newer_wins_when_status_and_score_and_synthetic_tie(tmp_path: Path) -> None:
    """Three ``executor_incomplete`` attempts with no score data and all
    real summaries.  The newest (highest mtime) wins."""
    task_dir = tmp_path / "task_003"
    p1 = _write_attempt(task_dir, "p1-host-old", final_status="executor_incomplete")
    p2 = _write_attempt(task_dir, "p2-host-mid", final_status="executor_incomplete")
    p3 = _write_attempt(task_dir, "p3-host-new", final_status="executor_incomplete")

    # Force ascending mtimes.
    base = time.time() - 1000
    os.utime(p1, (base, base))
    os.utime(p2, (base + 100, base + 100))
    os.utime(p3, (base + 200, base + 200))

    summary = refresh_one_task(task_dir)
    assert summary is not None
    # Newest attempt (index 3) wins.
    assert summary["resolvedAttempt"] == 3, summary


def test_pass_still_beats_fail_regardless_of_other_keys(tmp_path: Path) -> None:
    """Sanity guard: status rank stays primary.  A ``pass`` attempt with
    low score beats a ``fail`` attempt with high score."""
    task_dir = tmp_path / "task_004"
    _write_attempt(task_dir, "p1-host-pass", final_status="pass", final_score=0.5)
    _write_attempt(task_dir, "p2-host-fail", final_status="fail", final_score=0.95)

    summary = refresh_one_task(task_dir)
    assert summary is not None
    assert summary["finalStatus"] == "pass"
    assert summary["resolvedAttempt"] == 1


def test_zero_scores_are_preserved_not_treated_as_missing(tmp_path: Path) -> None:
    task_dir = tmp_path / "task_005"
    p = task_dir / "p1-host-zero"
    p.mkdir(parents=True)
    (p / "summary.json").write_text(
        json.dumps(
            {
                "finalStatus": "fail",
                "passed": False,
                "score": 0.8,
                "rawFinalScore": 0.0,
                "finalScore": 0.0,
                "runtimeMs": 0,
                "runtime_ms": 1234,
            }
        ),
        encoding="utf-8",
    )

    summary = refresh_one_task(task_dir)
    assert summary is not None
    assert summary["rawFinalScore"] == 0.0
    assert summary["finalScore"] == 0.0
    assert summary["attempts"][0]["runtimeMs"] == 0
