"""Host-side flock + TTL state for populator idempotency under workers>1.

Why a lock here (not inside each populator): auth-task populators all
share the concern that concurrent workers can race during the bootstrap
window — an empty external resource (Trello board, Notion page, etc.)
plus N workers each trying to create the fixture == duplicated fixtures
or partial state. Wrapping the call site once in ``pre_exec`` keeps that
concern off every populator's plate.

Why TTL state: once one worker has successfully populated the external
resource for this task, every subsequent worker within TTL seconds can
trust the resource is fresh and skip the populator entirely. This keeps
the per-triple wall time proportional to the lock-acquire-then-check
cost instead of re-running the full populator for every triple.

State layout (per task_id):

    /tmp/clawbench_populate/{task_id}/
        lock         # flock target (empty file, flock(LOCK_EX))
        state.json   # {"last_ok_at": ISO, "populator_sha256": hex}

The fingerprint is a SHA-256 digest of the populator script(s) — if the
script source changes, the state is treated as stale and the populator
re-runs even within TTL. This avoids "oh I patched populate.py but the
runner kept skipping because TTL said it was fresh" surprises.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


LOCK_ROOT = Path(
    os.environ.get("CLAWBENCH_POPULATE_LOCK_ROOT", "/tmp/clawbench_populate")
)
TTL_SECONDS = int(os.environ.get("CLAWBENCH_POPULATE_TTL_SECONDS", "3600"))


def _task_lock_dir(task_id: str) -> Path:
    d = LOCK_ROOT / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _populator_fingerprint(scripts: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(scripts):
        try:
            h.update(p.read_bytes())
        except OSError:
            # Unreadable script → treat as unique fingerprint so next run
            # won't short-circuit off a stale state.
            h.update(str(p).encode())
            h.update(b"\x00UNREADABLE\x00")
    return h.hexdigest()[:32]


def _is_fresh(state_path: Path, fingerprint: str, ttl_seconds: int) -> bool:
    try:
        st = json.loads(state_path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if st.get("populator_sha256") != fingerprint:
        return False  # populator source changed → refresh
    last = st.get("last_ok_at")
    if not last:
        return False
    try:
        ts = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except ValueError:
        return False
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age < ttl_seconds


@contextlib.contextmanager
def populator_lock(
    task_id: str,
    scripts: list[Path],
    *,
    ttl_seconds: int | None = None,
) -> Iterator[dict]:
    """Acquire an exclusive lock for this task_id's populators.

    Yields a dict with three fields:
      - ``skip`` (bool): True if a prior worker already populated within
        TTL. Caller should NOT run populator; record a no-op.
      - ``fingerprint`` (str): SHA-256 prefix of the populator script(s).
      - ``state_path`` (Path): pass to ``mark_populator_ok`` after a
        successful populator run.

    The lock is held for the entire duration of the ``with`` block, so
    concurrent workers for the same task_id see serialised behaviour:
    the first one either runs the populator (state refreshed) or finds
    the state already fresh (skip=True on acquire); subsequent workers
    wait, then on acquire see the freshened state and also skip.

    ``ttl_seconds=None`` uses the module-level default
    (``CLAWBENCH_POPULATE_TTL_SECONDS``, default 3600).
    """
    if ttl_seconds is None:
        ttl_seconds = TTL_SECONDS
    lock_dir = _task_lock_dir(task_id)
    lock_path = lock_dir / "lock"
    state_path = lock_dir / "state.json"
    fingerprint = _populator_fingerprint(scripts)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)  # blocks other workers on same task
        # Re-check freshness AFTER acquiring the lock — between the time
        # this worker was spawned and the time it got the lock, another
        # worker may have completed the populator and flipped state to
        # fresh.
        skip = _is_fresh(state_path, fingerprint, ttl_seconds)
        yield {"skip": skip, "fingerprint": fingerprint, "state_path": state_path}
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def mark_populator_ok(state_path: Path, fingerprint: str) -> None:
    """Write ``state.json`` to mark the populator run as complete.

    Call this inside the ``populator_lock`` with-block, after the
    populator script(s) exit with returncode=0. Skipping this call (e.g.
    on populator failure) intentionally leaves state stale so the next
    worker retries.
    """
    payload = {
        "last_ok_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "populator_sha256": fingerprint,
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
