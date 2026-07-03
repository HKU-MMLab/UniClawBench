"""Dispatcher-side stall detector (scripts/orchestra/dispatch.py).

A previous external watchdog missed a freeze where workers held real
containers but their in-container agents had died: the dispatcher kept counting
those cells inflight, and because healthy workers kept the aggregate terminal
count climbing, the watchdog judged health=ok.

``detect_stuck_workers`` is the in-repo, testable signal the user asked for: a
worker that holds >=1 inflight cell aged past ``stuck_age_seconds`` AND has
produced no DONE callback within that same window is flagged.  Recency of DONE
from the worker is the discriminator that separates "stuck" from "slow but
churning".
"""
from __future__ import annotations

from scripts.orchestra.dispatch import detect_stuck_workers


def _row(worker: str, ts_start: float, task: str = "t"):
    return {"backend": "openclaw", "model_dir": "m", "suite": "101",
            "task": task, "worker": worker, "ts_start": ts_start}


def test_flags_worker_with_old_cells_and_no_recent_done():
    now = 10_000.0
    rows = [
        _row("worker1", now - 3000, "a"),  # 50 min old > 2700s threshold
        _row("worker1", now - 2900, "b"),
    ]
    # worker1 never reported a DONE.
    findings = detect_stuck_workers(rows, {}, now, stuck_age_seconds=2700)
    assert len(findings) == 1
    f = findings[0]
    assert f["worker"] == "worker1"
    assert f["stuck_cells"] == 2
    assert f["oldest_age"] >= 3000


def test_does_not_flag_worker_that_recently_completed_a_cell():
    now = 10_000.0
    rows = [_row("worker2", now - 3000, "a")]  # has an old cell...
    # ...but completed something 60s ago → slow-but-churning, not stuck.
    findings = detect_stuck_workers(
        rows, {"worker2": now - 60}, now, stuck_age_seconds=2700
    )
    assert findings == []


def test_does_not_flag_worker_with_only_young_cells():
    now = 10_000.0
    rows = [_row("worker3", now - 100, "a"), _row("worker3", now - 200, "b")]
    findings = detect_stuck_workers(rows, {}, now, stuck_age_seconds=2700)
    assert findings == []


def test_isolates_stuck_workers_from_healthy_ones():
    now = 10_000.0
    rows = [
        _row("worker1", now - 3000, "a"),       # stuck (old, no done)
        _row("worker3", now - 3000, "b"),       # stuck (old, no done)
        _row("worker2", now - 3000, "c"),       # old BUT done recently → healthy
        _row("worker4", now - 100, "d"),        # young → healthy
    ]
    last_done = {"worker2": now - 30}
    findings = detect_stuck_workers(rows, last_done, now, stuck_age_seconds=2700)
    flagged = sorted(f["worker"] for f in findings)
    assert flagged == ["worker1", "worker3"]


def test_old_done_beyond_window_still_flags():
    now = 10_000.0
    rows = [_row("worker1", now - 3000, "a")]
    # Last DONE was 50 min ago — also beyond the 2700s window → still stuck.
    findings = detect_stuck_workers(
        rows, {"worker1": now - 3000}, now, stuck_age_seconds=2700
    )
    assert [f["worker"] for f in findings] == ["worker1"]
