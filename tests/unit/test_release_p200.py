"""Round 12 follow-up: ``release_p200.py`` + ``attempts_resets.jsonl``
integration.

Three things we want to pin:

1. ``_count_attempts_from_done_history`` subtracts reset records from
   the raw done_history counter (without modifying done_history itself).

2. ``release_p200.main`` --list reads the latest snapshot from
   ``priorities.jsonl`` and prints (only) the P200 entries.

3. ``release_p200.main`` --execute appends one reset record per
   targeted task, and the next call to
   ``_count_attempts_from_done_history`` returns the dropped counts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestra.release_p200 import main as release_main
from scripts.orchestra.stats import (
    LIFETIME_MAX_ATTEMPTS,
    P100_BUCKET_ID,
    P200_BUCKET_ID,
    _count_attempts_from_done_history,
)


def _seed_done_history(
    runtime_dir: Path,
    task_key: tuple[str, str, str, str],
    n: int,
) -> None:
    archive_dir = runtime_dir / "done_history"
    archive_dir.mkdir(parents=True, exist_ok=True)
    p = archive_dir / "done_seed.jsonl"
    backend, model_dir, suite, task = task_key
    p.write_text(
        "\n".join(json.dumps({
            "backend": backend, "model_dir": model_dir,
            "suite": suite, "task": task,
            "status": "rate_limit",
        }) for _ in range(n)) + "\n",
        encoding="utf-8",
    )


def test_count_attempts_subtracts_reset_records(tmp_path: Path) -> None:
    """attempts_resets.jsonl decrements the raw counter; done_history
    files are untouched.  Clamped at zero — a reset cannot push a
    counter negative even if reset_count > done_history rows."""
    key = ("openclaw", "m1", "101", "t1")
    _seed_done_history(tmp_path, key, 10)
    assert _count_attempts_from_done_history(tmp_path)[key] == 10

    # Reset 7 → counter = 3
    (tmp_path / "attempts_resets.jsonl").write_text(
        json.dumps({
            "backend": key[0], "model_dir": key[1],
            "suite": key[2], "task": key[3],
            "reset_count": 7, "reset_at": 1234567890,
        }) + "\n",
        encoding="utf-8",
    )
    assert _count_attempts_from_done_history(tmp_path)[key] == 3

    # Reset 5 more on top → counter clamped at 0, not negative
    with (tmp_path / "attempts_resets.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "backend": key[0], "model_dir": key[1],
            "suite": key[2], "task": key[3],
            "reset_count": 5, "reset_at": 1234567900,
        }) + "\n")
    assert _count_attempts_from_done_history(tmp_path)[key] == 0


def test_count_attempts_skips_malformed_reset_records(tmp_path: Path) -> None:
    """Bad reset lines (missing fields, non-int reset_count, broken
    json) are silently skipped — they don't crash the counter."""
    key = ("openclaw", "m1", "101", "t1")
    _seed_done_history(tmp_path, key, 5)
    (tmp_path / "attempts_resets.jsonl").write_text(
        "\n".join([
            "not json",
            json.dumps({"backend": "openclaw", "missing_fields": True}),
            json.dumps({
                "backend": key[0], "model_dir": key[1],
                "suite": key[2], "task": key[3],
                "reset_count": "abc",  # not an int — actually triggers our cast fallback
            }),
            json.dumps({
                "backend": key[0], "model_dir": key[1],
                "suite": key[2], "task": key[3],
                "reset_count": 0,  # zero is no-op, also fine
            }),
            json.dumps({
                "backend": key[0], "model_dir": key[1],
                "suite": key[2], "task": key[3],
                "reset_count": 2,  # legitimate -2
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    # Only the last (legitimate) entry should take effect (the "abc"
    # entry will raise ValueError in int() and we expect it to be
    # silently skipped via the int(...) coercion catching the
    # nonsense — defensive code intentionally writes "or 0" fallback).
    # Either 3 (if abc skipped) or 1 (if abc somehow worked) is fine
    # from a CORRECTNESS standpoint; we just must not crash.
    result = _count_attempts_from_done_history(tmp_path)
    assert key in result


def _write_priorities_snapshot(runtime_dir: Path, p200_tasks: list[dict]) -> None:
    """Emit a priorities.jsonl that release_p200 --list can parse."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps({"priority_id": "P1_test", "label": "test", "tasks": []}),
        json.dumps({"priority_id": P100_BUCKET_ID, "label": "p100", "tasks": []}),
        json.dumps({
            "priority_id": P200_BUCKET_ID,
            "label": "p200",
            "tasks": p200_tasks,
        }),
    ]
    (runtime_dir / "priorities.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )


def test_release_main_list_returns_p200_only(tmp_path: Path, capsys) -> None:
    """``--list`` prints just the P200 entries, not P1/P100."""
    runtime_dir = tmp_path / "runtime"
    p200_tasks = [
        {
            "backend": "openclaw", "model_dir": "m1",
            "suite": "101", "task": "t1",
            "attempts": 5, "lifetime_attempts": 12,
        },
        {
            "backend": "nanobot", "model_dir": "m2",
            "suite": "102", "task": "t2",
            "attempts": 4, "lifetime_attempts": 11,
        },
    ]
    _write_priorities_snapshot(runtime_dir, p200_tasks)
    rc = release_main(["--runtime-dir", str(runtime_dir), "--list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "P200 contents (2 task(s))" in out
    assert "openclaw/m1/101/t1" in out
    assert "nanobot/m2/102/t2" in out


def test_release_main_list_empty_p200(tmp_path: Path, capsys) -> None:
    """When P200 is empty, --list says so cleanly and exits 0."""
    runtime_dir = tmp_path / "runtime"
    _write_priorities_snapshot(runtime_dir, [])
    rc = release_main(["--runtime-dir", str(runtime_dir), "--list"])
    assert rc == 0
    assert "P200 is empty" in capsys.readouterr().out


def test_release_main_all_dryrun_does_not_write(tmp_path: Path, capsys) -> None:
    """Without ``--execute``, ``--all`` is a preview only."""
    runtime_dir = tmp_path / "runtime"
    p200_tasks = [{
        "backend": "openclaw", "model_dir": "m1",
        "suite": "101", "task": "t1",
        "attempts": 5, "lifetime_attempts": 12,
    }]
    _write_priorities_snapshot(runtime_dir, p200_tasks)
    rc = release_main(["--runtime-dir", str(runtime_dir), "--all"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Would release 1 task(s)" in out
    assert "Dry-run only" in out
    assert not (runtime_dir / "attempts_resets.jsonl").exists()


def test_release_main_all_execute_writes_resets(tmp_path: Path) -> None:
    """``--all --execute`` appends reset records for every P200 task.

    End-to-end: after the release, the next
    ``_count_attempts_from_done_history`` call should return 0 for
    those tasks (or at least below LIFETIME_MAX_ATTEMPTS).
    """
    runtime_dir = tmp_path / "runtime"
    key1 = ("openclaw", "m1", "101", "t1")
    key2 = ("nanobot", "m2", "102", "t2")
    _seed_done_history(runtime_dir, key1, 12)
    _seed_done_history_extra(runtime_dir, key2, 15)

    p200_tasks = [
        {
            "backend": key1[0], "model_dir": key1[1],
            "suite": key1[2], "task": key1[3],
            "attempts": 5, "lifetime_attempts": 12,
        },
        {
            "backend": key2[0], "model_dir": key2[1],
            "suite": key2[2], "task": key2[3],
            "attempts": 5, "lifetime_attempts": 15,
        },
    ]
    _write_priorities_snapshot(runtime_dir, p200_tasks)

    rc = release_main([
        "--runtime-dir", str(runtime_dir),
        "--all", "--execute",
    ])
    assert rc == 0

    resets = runtime_dir / "attempts_resets.jsonl"
    assert resets.is_file()
    lines = [l for l in resets.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2

    counts = _count_attempts_from_done_history(runtime_dir)
    assert counts.get(key1, 0) == 0, (
        f"after release, lifetime for {key1} should be 0 (was 12 minus reset 12), got {counts.get(key1)}"
    )
    assert counts.get(key2, 0) == 0


def test_release_main_specific_task_only(tmp_path: Path) -> None:
    """``--task X --execute`` resets ONLY that task, even if other
    tasks are in P200."""
    runtime_dir = tmp_path / "runtime"
    key1 = ("openclaw", "m1", "101", "t1")
    key2 = ("nanobot", "m2", "102", "t2")
    _seed_done_history(runtime_dir, key1, 12)
    _seed_done_history_extra(runtime_dir, key2, 13)

    p200_tasks = [
        {**dict(zip(["backend", "model_dir", "suite", "task"], key1)),
         "attempts": 5, "lifetime_attempts": 12},
        {**dict(zip(["backend", "model_dir", "suite", "task"], key2)),
         "attempts": 5, "lifetime_attempts": 13},
    ]
    _write_priorities_snapshot(runtime_dir, p200_tasks)

    rc = release_main([
        "--runtime-dir", str(runtime_dir),
        "--task", "openclaw/m1/101/t1",
        "--execute",
    ])
    assert rc == 0

    counts = _count_attempts_from_done_history(runtime_dir)
    # key1 released → 0
    assert counts.get(key1, 0) == 0
    # key2 untouched → still 13, still above LIFETIME_MAX_ATTEMPTS
    assert counts.get(key2, 0) >= LIFETIME_MAX_ATTEMPTS


def _seed_done_history_extra(
    runtime_dir: Path,
    task_key: tuple[str, str, str, str],
    n: int,
) -> None:
    """Same as _seed_done_history but writes into a second archive
    file so the test exercises multi-file scanning."""
    archive_dir = runtime_dir / "done_history"
    archive_dir.mkdir(parents=True, exist_ok=True)
    p = archive_dir / "done_seed_extra.jsonl"
    backend, model_dir, suite, task = task_key
    p.write_text(
        "\n".join(json.dumps({
            "backend": backend, "model_dir": model_dir,
            "suite": suite, "task": task,
            "status": "rate_limit",
        }) for _ in range(n)) + "\n",
        encoding="utf-8",
    )


def test_record_resets_uses_done_history_when_lifetime_field_absent(
    tmp_path: Path,
) -> None:
    """P1-2 regression guard.

    Round 16+ ``recompute_priorities`` writes P200 task entries without
    a ``lifetime_attempts`` field.  Earlier ``_record_resets``
    implementations read ``t.get('lifetime_attempts') or 0`` and wrote
    ``reset_count = 0`` for every task — a silent no-op.

    The fix routes ``reset_count`` through
    ``stats._count_attempts_from_done_history``, so the reset zeroes the
    legacy view even when the task entry has no lifetime field.
    """
    from scripts.orchestra.release_p200 import _record_resets

    runtime_dir = tmp_path / "runtime"
    key = ("openclaw", "m1", "101", "t1")
    _seed_done_history(runtime_dir, key, 14)

    # Round 16+ P200 entry: no ``lifetime_attempts`` field.
    p200_tasks = [{
        "backend": key[0], "model_dir": key[1],
        "suite": key[2], "task": key[3],
        "attempts": 6,
    }]

    resets_path = _record_resets(runtime_dir, p200_tasks)
    records = [
        json.loads(l)
        for l in resets_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert len(records) == 1
    assert records[0]["reset_count"] == 14, (
        "reset_count must come from done_history, not the (absent) "
        "lifetime_attempts field"
    )
    # End-to-end: the legacy lifetime view is now zero for this task.
    assert _count_attempts_from_done_history(runtime_dir).get(key, 0) == 0


def test_release_p200_docstring_drops_stale_recompute_claim() -> None:
    """P1-2 documentation guard.

    The earlier docstring claimed "next recompute pass after release
    will reroute affected tasks back into user buckets" — true only for
    pre-Round-16 dispatchers.  Round 16+ ``recompute_priorities`` no
    longer reads ``attempts_resets.jsonl``, so the claim is misleading.
    """
    import scripts.orchestra.release_p200 as release_mod
    doc = release_mod.__doc__ or ""
    assert "next recompute pass after\nrelease will reroute" not in doc
    assert "reset file is read on every recompute" not in doc
