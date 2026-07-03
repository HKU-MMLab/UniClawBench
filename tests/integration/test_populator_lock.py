"""Unit tests for ``lib/runner/populator_lock.py`` and the
``pre_exec_parallel_safe`` TaskSpec field.

Coverage:
1. ``populator_lock`` yields ``skip=False`` on empty state.
2. After ``mark_populator_ok``, the next enter yields ``skip=True``.
3. Changing the populator source (different fingerprint) forces
   ``skip=False`` even if ``last_ok_at`` is still within TTL.
4. An expired ``last_ok_at`` (TTL override = 0) forces ``skip=False``.
5. Two threads contending on the same task_id are mutually exclusive —
   the second only enters after the first exits.
6. ``load_task`` parses ``pre_exec_parallel_safe`` as a bool, defaulting
   to False when the key is absent.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def lock_root(tmp_path, monkeypatch):
    """Redirect populator-lock state into a tmp dir so tests don't leak
    into ``/tmp/clawbench_populate`` on the dev box."""
    root = tmp_path / "clawbench_populate"
    monkeypatch.setenv("CLAWBENCH_POPULATE_LOCK_ROOT", str(root))
    # Re-import so LOCK_ROOT picks up the env override.
    import importlib

    from lib.runner import populator_lock as mod

    importlib.reload(mod)
    yield mod
    # Restore default env for subsequent tests.
    importlib.reload(mod)


@pytest.fixture
def scripts(tmp_path):
    p = tmp_path / "populate.py"
    p.write_text("print('populate v1')\n", encoding="utf-8")
    return [p]


# ── 1. empty state → skip=False ────────────────────────────────────

def test_empty_state_yields_skip_false(lock_root, scripts) -> None:
    with lock_root.populator_lock("t_empty", scripts) as guard:
        assert guard["skip"] is False
        assert guard["fingerprint"]
        assert guard["state_path"].name == "state.json"


# ── 2. mark_populator_ok makes next enter skip=True ───────────────

def test_mark_ok_then_skip_true(lock_root, scripts) -> None:
    with lock_root.populator_lock("t_markok", scripts) as guard:
        lock_root.mark_populator_ok(guard["state_path"], guard["fingerprint"])
    with lock_root.populator_lock("t_markok", scripts) as guard2:
        assert guard2["skip"] is True


# ── 3. fingerprint change forces skip=False ───────────────────────

def test_fingerprint_change_forces_refresh(lock_root, scripts, tmp_path) -> None:
    with lock_root.populator_lock("t_fp", scripts) as guard:
        lock_root.mark_populator_ok(guard["state_path"], guard["fingerprint"])
    # Modify the populator source (simulates a dev editing populate.py).
    scripts[0].write_text("print('populate v2 — changed')\n", encoding="utf-8")
    with lock_root.populator_lock("t_fp", scripts) as guard2:
        assert guard2["skip"] is False


# ── 4. expired last_ok_at forces skip=False ───────────────────────

def test_ttl_expired_forces_refresh(lock_root, scripts) -> None:
    with lock_root.populator_lock("t_ttl", scripts) as guard:
        lock_root.mark_populator_ok(guard["state_path"], guard["fingerprint"])
    # ttl=0 makes any state immediately stale.
    with lock_root.populator_lock("t_ttl", scripts, ttl_seconds=0) as guard2:
        assert guard2["skip"] is False


def test_manually_aged_state_forces_refresh(lock_root, scripts) -> None:
    """Write an old last_ok_at directly and verify _is_fresh flips to
    False when TTL is shorter than the artificial age."""
    with lock_root.populator_lock("t_aged", scripts) as guard:
        state = guard["state_path"]
        fp = guard["fingerprint"]
    ancient = (datetime.now(timezone.utc) - timedelta(seconds=7200)).isoformat().replace(
        "+00:00", "Z"
    )
    state.write_text(json.dumps({"last_ok_at": ancient, "populator_sha256": fp}))
    with lock_root.populator_lock("t_aged", scripts, ttl_seconds=3600) as guard2:
        assert guard2["skip"] is False


# ── 5. concurrent threads mutually exclude ─────────────────────────

def test_concurrent_threads_serialize(lock_root, scripts) -> None:
    """Thread B must only enter the with-block after thread A exits.

    We detect this by recording enter/exit timestamps and asserting the
    second thread's enter time is strictly >= the first thread's exit
    time.
    """
    events: list[tuple[str, str, float]] = []
    events_lock = threading.Lock()
    start_gate = threading.Event()
    hold_seconds = 0.3

    def worker(tag: str) -> None:
        start_gate.wait()
        with lock_root.populator_lock("t_concurrent", scripts):
            with events_lock:
                events.append((tag, "enter", time.monotonic()))
            time.sleep(hold_seconds)
            with events_lock:
                events.append((tag, "exit", time.monotonic()))

    t_a = threading.Thread(target=worker, args=("A",))
    t_b = threading.Thread(target=worker, args=("B",))
    t_a.start()
    t_b.start()
    start_gate.set()
    t_a.join()
    t_b.join()

    # Sort events chronologically.
    events.sort(key=lambda e: e[2])
    # Pattern must be: X-enter, X-exit, Y-enter, Y-exit (for some X, Y).
    assert [(e[1]) for e in events] == ["enter", "exit", "enter", "exit"], events
    first_tag = events[0][0]
    second_tag = events[2][0]
    assert first_tag != second_tag  # one thread didn't take both turns
    # Second enter must be AT OR AFTER first exit (flock is strict).
    assert events[2][2] >= events[1][2]


# ── 6. TaskSpec pre_exec_parallel_safe parsing ─────────────────────


def _write_minimal_yaml(yaml_path: Path, repo_root: Path, *, parallel_safe_line: str = "") -> None:
    """Drop a minimal task yaml + injection root so load_task doesn't
    blow up on asset validation.

    ``load_task`` computes ``injection_root = repo_root / "injection" /
    category / task_id``, so we must drop the referenced files under
    that exact path (not relative to the yaml file).
    """
    task_id = yaml_path.stem
    injection_root = repo_root / "injection" / "999_parse_tests" / task_id
    injection_root.mkdir(parents=True, exist_ok=True)
    (injection_root / ".privacy").write_text("", encoding="utf-8")
    (injection_root / "sources").mkdir(exist_ok=True)
    (injection_root / "references").mkdir(exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text(
        "hidden", encoding="utf-8"
    )
    (injection_root / "skills").mkdir(exist_ok=True)
    yaml_path.write_text(
        f"""task_id: {task_id}
category: 999_parse_tests
agent_sys: openclaw
agent_id: main
model: p/m
task: |
  do stuff
references:
  - references/eval_rule.md
sources: []
skills: []
{parallel_safe_line}
""",
        encoding="utf-8",
    )


def test_parallel_safe_flag_true(tmp_path) -> None:
    from lib.task import load_task

    repo_root = tmp_path
    tasks_dir = repo_root / "tasks" / "999_parse_tests"
    tasks_dir.mkdir(parents=True)
    yaml_path = tasks_dir / "task_p_safe.yaml"
    _write_minimal_yaml(yaml_path, repo_root, parallel_safe_line="pre_exec_parallel_safe: true")
    task = load_task(yaml_path, repo_root=repo_root)
    assert task.pre_exec_parallel_safe is True


def test_parallel_safe_flag_false_when_explicit(tmp_path) -> None:
    from lib.task import load_task

    repo_root = tmp_path
    tasks_dir = repo_root / "tasks" / "999_parse_tests"
    tasks_dir.mkdir(parents=True)
    yaml_path = tasks_dir / "task_p_false.yaml"
    _write_minimal_yaml(yaml_path, repo_root, parallel_safe_line="pre_exec_parallel_safe: false")
    task = load_task(yaml_path, repo_root=repo_root)
    assert task.pre_exec_parallel_safe is False


def test_parallel_safe_flag_default_false_when_absent(tmp_path) -> None:
    from lib.task import load_task

    repo_root = tmp_path
    tasks_dir = repo_root / "tasks" / "999_parse_tests"
    tasks_dir.mkdir(parents=True)
    yaml_path = tasks_dir / "task_p_missing.yaml"
    _write_minimal_yaml(yaml_path, repo_root, parallel_safe_line="")
    task = load_task(yaml_path, repo_root=repo_root)
    assert task.pre_exec_parallel_safe is False
