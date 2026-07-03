"""End-to-end coverage of the webui ``/api/runs`` cache freshness check.

The webui reads ``<runs_root>/.runs_index.json`` as a fast path; when
any ``summary.json`` is newer than the index, the webui must fall back
to walking the tree.  The fallback is the only safety net that lets
operators run ``scripts/run_eval.py`` directly without first refreshing
the cache — if it regresses, every direct run silently returns stale
data.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from scripts.orchestra.refresh_summary import (
    refresh_all_tasks,
    rebuild_index_only,
)


def _seed_task(
    runs_root: Path,
    *,
    backend: str,
    model_dir: str,
    suite: str,
    task: str,
    status: str,
    runtime_ms: int | None = 1234,
) -> Path:
    task_dir = runs_root / backend / model_dir / suite / task
    p_dir = task_dir / "p1-host-aaaaaa"
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": task,
                "backend": backend,
                "model": "fake/model",
                "finalStatus": status,
                "passed": status == "pass",
                "runtimeMs": runtime_ms,
                "score": 0.5,
                "attempts": [{"attempt": 1, "outDir": str(p_dir), "finalStatus": status}],
            }
        ),
        encoding="utf-8",
    )
    return task_dir


def _set_webui_runs_root(monkeypatch: pytest.MonkeyPatch, runs_root: Path) -> None:
    monkeypatch.setenv("CLAWBENCH_RUNS_DIR", str(runs_root))
    # webui.server reads RUNS at import time, so we need to monkeypatch
    # the module attribute too.
    import webui.server as server

    monkeypatch.setattr(server, "RUNS", runs_root)


def test_fast_path_returns_cached_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    _seed_task(runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_001", status="pass")
    refresh_all_tasks(runs_root)
    assert (runs_root / ".runs_index.json").exists()

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    cached = _load_runs_index(runs_root)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["taskId"] == "task_001"
    assert cached[0]["finalStatus"] == "pass"


def test_index_runtime_uses_attempt_meta_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    task_dir = _seed_task(
        runs_root,
        backend="openclaw",
        model_dir="fake-model",
        suite="101_a",
        task="task_runtime",
        status="pass",
        runtime_ms=0,
    )
    attempt_dir = next(p for p in task_dir.iterdir() if p.is_dir() and p.name.startswith("p"))
    (attempt_dir / "meta.json").write_text(json.dumps({"runtimeMs": 4321}), encoding="utf-8")
    refresh_all_tasks(runs_root)

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    cached = _load_runs_index(runs_root)
    assert cached is not None
    assert cached[0]["runtimeMs"] == 4321


def test_missing_index_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    _seed_task(runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_x", status="pass")
    # Don't generate the index

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    assert _load_runs_index(runs_root) is None


def test_stale_index_triggers_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    task_dir = _seed_task(
        runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_stale", status="pass"
    )
    refresh_all_tasks(runs_root)

    # Force-touch the summary to a timestamp clearly beyond the 1 s
    # clock-skew slack that the freshness check tolerates.
    later = time.time() + 5
    os.utime(task_dir / "summary.json", (later, later))

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    assert _load_runs_index(runs_root) is None, "stale index must trigger fallback"


def test_meta_newer_than_index_triggers_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    task_dir = _seed_task(
        runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_meta_stale", status="pass"
    )
    refresh_all_tasks(runs_root)
    attempt_dir = next(p for p in task_dir.iterdir() if p.is_dir() and p.name.startswith("p"))
    meta_path = attempt_dir / "meta.json"
    meta_path.write_text(json.dumps({"runtimeMs": 9999}), encoding="utf-8")
    later = time.time() + 5
    os.utime(meta_path, (later, later))

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    assert _load_runs_index(runs_root) is None, "newer attempt meta must invalidate cached index"


def test_within_clock_skew_slack_still_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    task_dir = _seed_task(
        runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_close", status="pass"
    )
    refresh_all_tasks(runs_root)

    # Touch summary 0.5 s in the past — strictly older than the index,
    # so the fast path must still serve.
    earlier = time.time() - 0.5
    os.utime(task_dir / "summary.json", (earlier, earlier))

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    assert _load_runs_index(runs_root) is not None


def test_version_mismatch_triggers_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    _seed_task(runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_v", status="pass")
    refresh_all_tasks(runs_root)

    # Bump the schema version so the webui's known constant doesn't
    # match → it must fall back rather than crash on a future schema.
    index = runs_root / ".runs_index.json"
    payload = json.loads(index.read_text())
    payload["version"] = 999
    index.write_text(json.dumps(payload), encoding="utf-8")

    _set_webui_runs_root(monkeypatch, runs_root)
    from webui.server import _load_runs_index

    assert _load_runs_index(runs_root) is None


def test_index_only_cli_rebuilds_without_touching_summaries(tmp_path: Path) -> None:
    """``refresh_summary --index-only`` is the operator's escape
    hatch after a manual run_eval / rsync.  Verify it rebuilds the
    index from existing task-level summary.json files and does NOT
    modify any summary.json (which would lose a manual edit the
    operator was trying to surface)."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    task_dir = _seed_task(
        runs_root, backend="openclaw", model_dir="fake-model", suite="101_a", task="task_manual", status="pass"
    )
    # Materialise the task-level summary.json first (refresh_all_tasks
    # rolls per-attempt summaries up to the task level).
    refresh_all_tasks(runs_root)
    summary_path = task_dir / "summary.json"
    assert summary_path.exists()
    summary_bytes = summary_path.read_bytes()

    # Now wipe the cache and ask --index-only to rebuild it.
    (runs_root / ".runs_index.json").unlink()
    rebuilt = rebuild_index_only(runs_root)
    assert rebuilt == 1
    assert (runs_root / ".runs_index.json").exists()
    # summary.json must be byte-identical
    assert summary_path.read_bytes() == summary_bytes
