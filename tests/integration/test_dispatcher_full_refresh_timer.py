"""Round 16 / P1-2: ``run_unified_dispatch`` must use a dedicated
``last_full_refresh`` timer, not reuse ``last_recompute``.

Previously both timers shared the variable, so every fast (5s) recompute
reset the full-refresh clock and the expensive
``refresh_summary.refresh_all_tasks`` pass only ran once at startup —
no matter how long the dispatcher stayed alive.

This test sets the two intervals to a small fraction of a second and
counts how many recompute calls are full_refresh=True vs False.  After
~1.5 seconds the full_refresh count should be ~ ceil(elapsed /
full_refresh_interval), not 1.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import scripts.orchestra.dispatch as dispatch_mod
import scripts.orchestra.stats as stats_mod
from scripts.orchestra.config import (
    CodexRoleCfg,
    ControllerCfg,
    OrchestraConfig,
    PriorityCfg,
    SupervisionCfg,
    WorkerCfg,
)


def _make_state(tmp_path: Path) -> dispatch_mod.DispatchState:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    cfg = OrchestraConfig(
        controller=ControllerCfg(host="controller", data_root=tmp_path, webui_port=9005),
        workers=(WorkerCfg(name="w1", ssh="w1", parallel=1),),
        priorities=(PriorityCfg(id="P1", label="catch-all"),),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
    )
    return dispatch_mod.DispatchState(
        cfg=cfg,
        workers=[dispatch_mod.WorkerState(cfg=cfg.workers[0])],
        done_file=runtime_dir / "done.jsonl",
        inflight_file=runtime_dir / "inflight.jsonl",
    )


def test_full_refresh_fires_repeatedly_independent_of_fast_recompute(
    tmp_path: Path, monkeypatch
) -> None:
    state = _make_state(tmp_path)
    call_log: list[bool] = []  # records do_refresh value per call

    empty_buckets = [
        {"priority_id": "P1", "label": "p1", "tasks": []},
        {"priority_id": stats_mod.P100_BUCKET_ID, "label": "p100", "tasks": []},
        {"priority_id": stats_mod.P200_BUCKET_ID, "label": "p200", "tasks": []},
    ]

    def fake_recompute(*_args, do_refresh: bool = True, **kwargs):
        call_log.append(bool(do_refresh))
        # Empty buckets — keeps the loop running without dispatching.
        # Plant a bogus inflight entry so the exit guard never trips
        # (Round 16 / P0-2 requires inflight to be empty for exit).
        state.inflight_by_task[("openclaw", "m1", "s", "t")] = {
            "backend": "openclaw",
            "model_dir": "m1",
            "suite": "s",
            "task": "t",
            "worker": "w1",
        }
        return empty_buckets

    monkeypatch.setattr(stats_mod, "recompute_priorities", fake_recompute)
    # Also patch the symbol bound inside dispatch.py's module namespace
    # (it imports `stats as stats_mod`).
    monkeypatch.setattr(dispatch_mod.stats_mod, "recompute_priorities", fake_recompute)

    shutdown = threading.Event()

    def _stop_after_window():
        time.sleep(1.5)
        shutdown.set()

    threading.Thread(target=_stop_after_window, daemon=True).start()

    with ThreadPoolExecutor(max_workers=1) as ex:
        dispatch_mod.run_unified_dispatch(
            state,
            ex,
            state.cfg,
            tasks_root=tmp_path / "tasks",
            runtime_dir=tmp_path / "runtime",
            shutdown_event=shutdown,
            poll_interval_seconds=0.05,
            recompute_interval_seconds=0.1,
            full_refresh_interval_seconds=0.4,
        )

    # Sanity: the loop ran enough to invoke recompute many times.
    assert len(call_log) >= 5, f"expected ≥5 recompute calls; got {len(call_log)}"

    full_refresh_count = sum(1 for v in call_log if v)
    fast_count = len(call_log) - full_refresh_count

    # With 1.5s window and full_refresh_interval=0.4s, we expect at
    # least 3 full refreshes (one at startup + ~3 more).  The buggy
    # behavior would produce exactly 1 (only the startup fire).
    assert full_refresh_count >= 3, (
        "full_refresh should fire on its own cadence regardless of fast "
        f"recompute resets; got {full_refresh_count} full / {fast_count} fast"
    )
    # And fast recomputes should dominate (since 0.1s < 0.4s).
    assert fast_count > full_refresh_count, (
        "expected fast recomputes to outnumber full refreshes; got "
        f"{fast_count} fast vs {full_refresh_count} full"
    )
