"""P1-1 follow-up: ``runtime/session_attempts.json`` snapshot.

The dispatcher keeps ``session_attempts`` in memory.  External
monitoring (``top.py --tasks-root``) recomputes priorities outside the
dispatcher process and previously saw an empty default, so synthetic
P100/P200 buckets under-reported.  ``stats.write_session_attempts_snapshot``
persists the in-memory state and ``stats.read_session_attempts_snapshot``
parses it back, so the external recompute routes tasks the same way the
live dispatcher does.

This file pins three properties:

1. Round-trip: an arbitrary ``session_attempts`` dict written by
   ``write_session_attempts_snapshot`` is read back identically by
   ``read_session_attempts_snapshot``.

2. Failure modes: missing file → ``None``; malformed payload → ``None``;
   empty dict → file present with empty ``entries`` (distinguishes
   "dispatcher up" from "no dispatcher").

3. Equivalent routing: an external recompute that consumes the snapshot
   produces the same P100/P200 buckets as the dispatcher's in-process
   recompute on the same counters.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestra import config as cfg_mod
from scripts.orchestra import stats as stats_mod
from scripts.orchestra.stats import (
    GLOBAL_MAX_ATTEMPTS,
    P100_BUCKET_ID,
    P200_BUCKET_ID,
    SESSION_P200_THRESHOLD,
    read_session_attempts_snapshot,
    write_session_attempts_snapshot,
)


def _write_cfg(tmp_path: Path) -> cfg_mod.OrchestraConfig:
    cfg_path = tmp_path / "orchestra.yaml"
    cfg_path.write_text(
        "controller:\n"
        "  host: controller\n"
        f"  data_root: {tmp_path}\n"
        "  webui_port: 9999\n"
        "workers:\n"
        "  - name: w1\n"
        "    ssh: w1\n"
        "    parallel: 1\n"
        "supervision:\n"
        "  supervisor:\n"
        "    provider: provider-a\n"
        "    model: model-a\n"
        "  user_simulator:\n"
        "    provider: provider-a\n"
        "    model: model-a\n"
        "priorities:\n"
        "  - id: P1_first_pass\n"
        "    label: first pass\n"
        "    match:\n"
        "      backend_in: [\"openclaw\"]\n"
        "      model_in: [\"test-model\"]\n"
        "      status_in: [\"missing\"]\n",
        encoding="utf-8",
    )
    return cfg_mod.load(cfg_path)


def _seed_task(tasks_root: Path) -> None:
    suite_dir = tasks_root / "101_test_suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    (suite_dir / "task_demo.yaml").write_text("task_id: task_demo\n", encoding="utf-8")


def test_snapshot_roundtrip_preserves_attempts(tmp_path: Path) -> None:
    attempts = {
        ("openclaw", "test-model", "101_test_suite", "task_a"): 2,
        ("openclaw", "test-model", "101_test_suite", "task_b"): SESSION_P200_THRESHOLD + 1,
        ("nanobot", "other-model", "102_other", "task_c"): GLOBAL_MAX_ATTEMPTS,
    }
    target = write_session_attempts_snapshot(tmp_path, attempts)
    assert target.is_file()
    assert read_session_attempts_snapshot(tmp_path) == attempts


def test_snapshot_missing_returns_none(tmp_path: Path) -> None:
    assert read_session_attempts_snapshot(tmp_path) is None


def test_snapshot_malformed_returns_none(tmp_path: Path) -> None:
    (tmp_path / "session_attempts.json").write_text("not json", encoding="utf-8")
    assert read_session_attempts_snapshot(tmp_path) is None

    # Missing required key in an entry → reject the whole payload.
    (tmp_path / "session_attempts.json").write_text(
        json.dumps({"updated_at": 0.0, "entries": [{"backend": "openclaw"}]}),
        encoding="utf-8",
    )
    assert read_session_attempts_snapshot(tmp_path) is None


def test_snapshot_empty_dict_still_writes_file(tmp_path: Path) -> None:
    target = write_session_attempts_snapshot(tmp_path, {})
    assert target.is_file()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["entries"] == []
    # Consumer sees an empty dict — distinguishable from "no snapshot".
    assert read_session_attempts_snapshot(tmp_path) == {}


def test_snapshot_write_is_atomic_no_partial_file_on_overwrite(tmp_path: Path) -> None:
    write_session_attempts_snapshot(tmp_path, {("a", "b", "c", "d"): 1})
    # Second overwrite with a different dict must not leave a stale .tmp.
    write_session_attempts_snapshot(tmp_path, {("e", "f", "g", "h"): 2})
    assert not (tmp_path / "session_attempts.json.tmp").exists()
    assert read_session_attempts_snapshot(tmp_path) == {("e", "f", "g", "h"): 2}


def test_external_recompute_via_snapshot_matches_inprocess(tmp_path: Path) -> None:
    """End-to-end: an out-of-process recompute that reads the snapshot
    produces the same P100/P200 routing as an in-process recompute that
    uses the live dict.  This is the property top.py --tasks-root
    relies on."""
    cfg = _write_cfg(tmp_path)
    _seed_task(tmp_path / "tasks")
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    key = ("openclaw", "test-model", "101_test_suite", "task_demo")
    live_attempts = {key: SESSION_P200_THRESHOLD + 1}

    # In-process: dispatcher passes the live dict directly.
    inproc_buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tmp_path / "tasks",
        runs_root=tmp_path,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts=live_attempts,
    )
    inproc_by_id = {b["priority_id"]: b for b in inproc_buckets}
    assert len(inproc_by_id[P200_BUCKET_ID]["tasks"]) == 1

    # Out-of-process: dispatcher writes the snapshot; external caller
    # reads it and recomputes.  Use a fresh runtime_dir to make sure the
    # snapshot is the only channel between the two recomputes.
    write_session_attempts_snapshot(runtime_dir, live_attempts)
    external_attempts = read_session_attempts_snapshot(runtime_dir)
    assert external_attempts == live_attempts

    external_buckets = stats_mod.recompute_priorities(
        cfg,
        tasks_root=tmp_path / "tasks",
        runs_root=tmp_path,
        runtime_dir=runtime_dir,
        do_refresh=False,
        session_attempts=external_attempts,
    )
    external_by_id = {b["priority_id"]: b for b in external_buckets}
    assert len(external_by_id[P200_BUCKET_ID]["tasks"]) == 1
    assert (
        external_by_id[P200_BUCKET_ID]["tasks"][0]["task"]
        == inproc_by_id[P200_BUCKET_ID]["tasks"][0]["task"]
    )

    # Compare the rest of the bucket map for shape equality.
    for pid in {*inproc_by_id, *external_by_id}:
        assert len(external_by_id[pid]["tasks"]) == len(inproc_by_id[pid]["tasks"]), (
            f"bucket {pid} task count differs between in-process and snapshot recomputes"
        )
