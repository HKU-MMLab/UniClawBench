"""Main orchestra dispatcher.

Single-threaded, single-process loop:

  while True:
      refresh_summary.refresh_all_tasks(runs)
      buckets = stats.recompute_priorities(cfg)
      for bucket in buckets:                # priority order
          while bucket has tasks:
              task = pick_next(bucket)      # respects model_caps, worker.parallel
              lock_inflight(task)
              ssh_worker_run(task)          # async
          # bucket drained; loop and refresh

The done callback (handled by ``_drain_done_file``) is what actually moves a
task out of the inflight set: workers call back over SSH to append to
``runtime/done.jsonl``.

Concurrency model: dispatch uses a thread pool to fire-and-await workers.
Each worker invocation is a single ``ssh <worker> <python> worker_runner.py ...``
that blocks until that task finishes (worker_runner does its own rsync +
done-report before exiting).  We rely on the dispatcher process being the
one source of truth for inflight state, so ``inflight.jsonl`` is
maintained in-memory and persisted on every change.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import shutil
import signal
import subprocess
import threading
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from . import config as cfg_mod
from . import preflight
from . import refresh_summary
from . import stats as stats_mod

LOG = logging.getLogger("orchestra.dispatch")


@dataclass
class WorkerState:
    cfg: cfg_mod.WorkerCfg
    inflight: int = 0
    # Exponential-backoff state for ssh-unreachable workers.  When ssh to
    # this host fails (e.g. instant "Connection refused" on a downed
    # worker), we mark it unhealthy for an increasing duration to avoid
    # a tight hot loop where the dispatcher re-tries the same dead host
    # every 3 seconds and produces hundreds of ssh failures per minute
    # while ignoring healthy peers.  Resets to 0 on the first successful
    # ssh return (rc==0 from _ssh_worker_run).
    consecutive_ssh_failures: int = 0
    unavailable_until: float = 0.0  # epoch seconds


# Backoff curve in seconds, indexed by ``consecutive_ssh_failures``
# (after the increment, so [0]=first-fail).  Caps at 300s = 5min.
_SSH_BACKOFF_SECONDS: tuple[float, ...] = (10.0, 30.0, 90.0, 300.0)

# V7: per-task SSH-level failure ceiling.  When a single task hits this
# many SSH dispatch failures (kex storm, connect timeout, etc.) we
# force it into the P100 graveyard so we don't burn slots forever on an
# unreachable target.  Five fails × backoff ladder = ≥7min on the
# wall clock before promotion, so transient blips don't trigger it.
SSH_FAIL_CEILING: int = 5


def _ssh_backoff_seconds(consecutive_failures: int) -> float:
    if consecutive_failures <= 0:
        return 0.0
    idx = min(consecutive_failures - 1, len(_SSH_BACKOFF_SECONDS) - 1)
    return _SSH_BACKOFF_SECONDS[idx]


def _bump_ssh_fail_attempts(state: "DispatchState", key: tuple[str, str, str, str]) -> None:
    """V7: increment per-task SSH failure counter; force P100 at ceiling.

    Called from both ``_ssh_worker_run`` failure branches (TimeoutExpired
    + rc!=0).  Uses ``state.lock`` because ``_drain_done_file`` writes the
    sibling ``session_attempts`` dict and we must not race with it.
    """
    with state.lock:
        state.ssh_fail_attempts[key] = state.ssh_fail_attempts.get(key, 0) + 1
        if state.ssh_fail_attempts[key] >= SSH_FAIL_CEILING:
            state.session_attempts[key] = max(
                state.session_attempts.get(key, 0),
                stats_mod.GLOBAL_MAX_ATTEMPTS,
            )
            LOG.warning(
                "ssh_fail_attempts=%d for %s — forcing P100 graveyard",
                SSH_FAIL_CEILING, key,
            )


def _reset_ssh_fail_attempts(state: "DispatchState", key: tuple[str, str, str, str]) -> None:
    """V7: clear per-task SSH failure counter on a successful dispatch."""
    with state.lock:
        state.ssh_fail_attempts.pop(key, None)


@dataclass
class DispatchState:
    cfg: cfg_mod.OrchestraConfig
    workers: list[WorkerState]
    inflight_by_task: dict[tuple[str, str, str, str], dict] = field(default_factory=dict)
    model_inflight: Counter = field(default_factory=Counter)
    lock: threading.Lock = field(default_factory=threading.Lock)
    done_file: Path = field(default=Path())
    inflight_file: Path = field(default=Path())
    # Round 12 / E1, V7-revised: in-memory, per-process attempts counter.
    # Now bumped in ``_drain_done_file`` on a DONE row that we successfully
    # release (i.e. the task actually ran and produced a result on the
    # worker — pass / fail / executor_incomplete all count).  Previously
    # bumped in reserve(), which double-counted SSH dispatch failures
    # that never actually ran the task on a worker (V7 root-cause for the
    # "10 task ghost-missed" symptom: kex_exchange_identification storm
    # bumped session_attempts to ceiling without the task ever executing).
    # Never persisted; dispatcher restart clears it (P100 "release" path).
    session_attempts: dict[tuple[str, str, str, str], int] = field(default_factory=dict)
    # Round 17: wall-clock (time.time()) when each cell's last attempt drained
    # out of inflight.  Drives the per-CELL retry backoff in ``can_start`` when
    # cfg.retry_backoff_base_seconds > 0.  In-memory; cleared on restart.
    last_release_ts: dict[tuple[str, str, str, str], float] = field(default_factory=dict)
    # V7: tracks consecutive SSH-level failures per task key (kex storm,
    # connect timeout, etc.).  When a single task hits ``SSH_FAIL_CEILING``
    # failures, we force its session_attempts to GLOBAL_MAX_ATTEMPTS so
    # recompute_priorities routes it to the P100 graveyard rather than
    # burning slots forever on a target the network cannot reach.
    ssh_fail_attempts: dict[tuple[str, str, str, str], int] = field(default_factory=dict)
    # Round 16 / P1-1: per-priority wave isolation.  Maps priority_id ->
    # set of task keys reserved within that priority's currently-open
    # wave.  ``reserve()`` adds; ``can_start()`` refuses any task that
    # appears in ANY active priority's wave (cross-bucket dedup); and
    # ``maybe_advance_round()`` clears each priority's subset
    # independently as soon as that priority's wave drains, even if
    # other priorities still have inflight tasks.
    #
    # Why per-priority: a P1 task that fails fast (rate_limit /
    # infra_error / executor_incomplete) used to wait for the entire
    # global wave — including slow P3 tasks — before it could re-enter
    # the queue.  After P0-1's session-based P200 + per-priority wave,
    # the failed P1 task moves to P2 (recoverable retry) and dispatches
    # immediately, without starving P3's still-running members.
    #
    # Disabled (no-op) when ``cfg.wave_isolation`` is False.
    dispatched_this_round: dict[str | None, set[tuple[str, str, str, str]]] = field(
        default_factory=dict
    )
    # Round 18: per-model executor key pools (lib/runner/key_pool.py).  When a
    # model_dir has a pool of keys (primary + auxiliaries), each attempt is
    # assigned a label via rate-limit-aware round-robin: ``key_pool_cursor`` is
    # the rotation index per model_dir; ``key_pool_hot`` is the last rate_limit
    # wall-clock per (model_dir, label) so the rotation skips a recently-429ed
    # key.  In-memory; cleared on restart.  Models with no pool are untouched.
    key_pool_cursor: dict[str, int] = field(default_factory=dict)
    key_pool_hot: dict[tuple[str, str], float] = field(default_factory=dict)
    # Stuck-worker detection (see ``detect_stuck_workers``).  ``last_done_ts_by_worker``
    # records the wall-clock of each worker's most recent DONE callback (updated
    # in the drain); ``stuck_flagged_workers`` holds workers currently flagged as
    # stuck so the loud STUCK warning is emitted once per stall episode, not every
    # recompute.  Both in-memory; cleared on restart.
    last_done_ts_by_worker: dict[str, float] = field(default_factory=dict)
    stuck_flagged_workers: set[str] = field(default_factory=set)
    task_meta_root: Path | None = None
    pre_exec_safety_cache: dict[tuple[str, str], tuple[bool, bool]] = field(default_factory=dict)

    def task_key(self, t: dict) -> tuple[str, str, str, str]:
        return (t["backend"], t["model_dir"], t["suite"], t["task"])

    def select_model_key(self, model_dir: str) -> str | None:
        """Pick a key-pool label for the next attempt of ``model_dir``.

        Rate-limit-aware round-robin: scan the pool in order from the rotation
        cursor and take the first label whose last rate_limit is older than the
        backoff-cap window; if every label is hot, fall back to the
        least-recently-hot one (always make progress).  Returns None for models
        without a pool (caller leaves ``model_key`` unset → legacy single-key).
        Must be called under ``self.lock`` (mutates the cursor).
        """
        labels = cfg_mod.key_pool_labels(model_dir)
        if not labels:
            return None
        now = time.time()
        window = max(1, self.cfg.retry_backoff_cap_seconds)
        n = len(labels)
        start = self.key_pool_cursor.get(model_dir, 0) % n
        chosen_idx: int | None = None
        least_idx, least_ts = start, None
        for i in range(n):
            idx = (start + i) % n
            ts = self.key_pool_hot.get((model_dir, labels[idx]), 0.0)
            if now - ts >= window:
                chosen_idx = idx
                break
            if least_ts is None or ts < least_ts:
                least_ts, least_idx = ts, idx
        if chosen_idx is None:
            chosen_idx = least_idx
        self.key_pool_cursor[model_dir] = (chosen_idx + 1) % n
        return labels[chosen_idx]

    def task_key_from_row(self, row: dict) -> tuple[str, str, str, str]:
        # Mirror of task_key, used when restoring rows from inflight.jsonl
        # on dispatcher startup.  Kept as a separate method so callers
        # signal intent ("this came from a persisted row, not a fresh
        # bucket entry").
        return (row["backend"], row["model_dir"], row["suite"], row["task"])

    def task_pre_exec_safety(self, suite: str, task: str) -> tuple[bool, bool]:
        """Return ``(has_pre_exec, parallel_safe)`` for a task YAML.

        The runner's populator lock serializes the host-side scripts
        themselves.  The dispatcher adds a broader guard: a non-parallel-safe
        populator task should not be started for two backend/model cells at the
        same time, because the executor from the first cell can observe live
        state while a second cell's pre-exec is resetting it.
        """

        if self.task_meta_root is None:
            return (False, True)
        cache_key = (suite, task)
        if cache_key in self.pre_exec_safety_cache:
            return self.pre_exec_safety_cache[cache_key]

        result = (False, True)
        path = self.task_meta_root / suite / f"{task}.yaml"
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            doc = {}
        if isinstance(doc, dict):
            pre_exec = doc.get("pre_exec") or []
            has_pre_exec = bool(pre_exec)
            result = (has_pre_exec, bool(doc.get("pre_exec_parallel_safe", False)))
        self.pre_exec_safety_cache[cache_key] = result
        return result

    def unsafe_pre_exec_task_running(
        self, t: dict, key: tuple[str, str, str, str]
    ) -> bool:
        has_pre_exec, parallel_safe = self.task_pre_exec_safety(t["suite"], t["task"])
        if not has_pre_exec or parallel_safe:
            return False
        for other_key, row in self.inflight_by_task.items():
            if other_key == key:
                continue
            if row.get("suite") != t["suite"] or row.get("task") != t["task"]:
                continue
            other_has_pre_exec, other_parallel_safe = self.task_pre_exec_safety(
                row.get("suite", ""), row.get("task", "")
            )
            if other_has_pre_exec and not other_parallel_safe:
                return True
        return False

    def restore_inflight_from_disk(self) -> int:
        """Rebuild the in-memory inflight dict from inflight.jsonl on startup.

        Without this, a dispatcher crash + restart loses track of every
        task the previous instance had handed to a worker — they stay on
        disk in inflight.jsonl (so stats correctly excludes them from new
        priority buckets) but the dispatcher's worker counters + model_caps
        start at zero, leading to over-dispatch when a new task picks up
        the same worker.

        Returns the number of rows restored.
        """
        if not self.inflight_file.exists():
            return 0
        restored = 0
        for line in self.inflight_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                key = self.task_key_from_row(row)
            except KeyError:
                continue
            self.inflight_by_task[key] = row
            self.model_inflight[row["model_dir"]] += 1
            for w in self.workers:
                if w.cfg.name == row.get("worker"):
                    w.inflight += 1
                    break
            restored += 1
        return restored

    def can_start(self, t: dict, worker: WorkerState) -> bool:
        if worker.cfg.skip:
            return False
        if worker.inflight >= worker.cfg.parallel:
            return False
        if worker.unavailable_until and time.time() < worker.unavailable_until:
            # Worker is under backoff after recent ssh failures; skip it
            # until ``unavailable_until`` has passed.  ``_ssh_worker_run``
            # resets the counter on the next successful ssh.
            return False
        cap = self.cfg.model_caps.get(t["model_dir"], self.cfg.default_model_cap)
        if cap is not None and self.model_inflight[t["model_dir"]] >= cap:
            return False
        key = self.task_key(t)
        if key in self.inflight_by_task:
            return False
        if self.unsafe_pre_exec_task_running(t, key):
            return False
        # Round 17: per-CELL retry backoff supersedes per-priority wave
        # isolation when configured.  A cell that has already drained at least
        # one attempt cannot re-dispatch until its OWN backoff window —
        # ``min(base * 2**(attempts-1), cap)`` seconds since its last drain —
        # has elapsed.  This paces a fast-failing rate_limited cell (no retry
        # storm) WITHOUT ever blocking unrelated cells (no idle tail behind a
        # slow sibling).  Fresh, never-attempted cells are never delayed.
        if self.cfg.retry_backoff_base_seconds > 0:
            attempts = self.session_attempts.get(key, 0)
            last = self.last_release_ts.get(key)
            if attempts > 0 and last is not None:
                backoff = min(
                    self.cfg.retry_backoff_base_seconds * (2 ** (attempts - 1)),
                    self.cfg.retry_backoff_cap_seconds,
                )
                if time.time() - last < backoff:
                    return False
        # Round 16 / P1-1: per-priority wave isolation (legacy fallback when
        # per-cell backoff is off).  Refuses any task that already appears in
        # ANY active priority's wave subset.  ``maybe_advance_round`` clears
        # subsets as their own waves drain.
        elif self.cfg.wave_isolation and any(
            key in members for members in self.dispatched_this_round.values()
        ):
            return False
        # Round 12 bugfix: also gate by the session_attempts ceiling so a
        # task that has already hit GLOBAL_MAX_ATTEMPTS doesn't get
        # re-dispatched from the stale flat_tasks cache between
        # recomputes.  Without this check the user-bucket cache (which
        # only refreshes every recompute_interval_seconds, default 5s)
        # keeps feeding the dispatcher exhausted tasks; the inner
        # dispatch loop fires off many SSH calls within that window and
        # session_attempts overshoots the cap by 10-100x.  Tasks tagged
        # with priority_id == P100/P200 are graveyard/suspended and
        # bypass this gate — they're flagged explicitly by recompute.
        if t.get("priority_id") not in (
            stats_mod.P100_BUCKET_ID,
            stats_mod.P200_BUCKET_ID,
        ) and self.session_attempts.get(key, 0) >= stats_mod.GLOBAL_MAX_ATTEMPTS:
            return False
        # P200 (suspended) is never dispatched at all — it's a holding
        # pen.  Even if a worker has free slots, suspended tasks stay
        # parked until manual intervention rotates done_history.
        if t.get("priority_id") == stats_mod.P200_BUCKET_ID:
            return False
        return True

    def reserve(self, t: dict, worker: WorkerState) -> None:
        with self.lock:
            # Stamp ts_start so stats.recompute_priorities can age out
            # stuck rows (worker crashed silently / dispatcher restart
            # window) via cfg.max_inflight_age_seconds.
            key = self.task_key(t)
            # Round 18: assign a key-pool label for this attempt (rate-limit-
            # aware rotation) when the model has a pool; legacy single-key
            # models leave ``model_key`` unset and behave exactly as before.
            if not t.get("model_key"):
                label = self.select_model_key(t["model_dir"])
                if label is not None:
                    t["model_key"] = label
            self.inflight_by_task[key] = {
                **t,
                "worker": worker.cfg.name,
                "ts_start": time.time(),
            }
            self.model_inflight[t["model_dir"]] += 1
            worker.inflight += 1
            # V7: session_attempts is no longer bumped here — it now counts
            # only DONE rows we actually receive back (see _drain_done_file).
            # This prevents a single SSH-storm of dispatch-but-never-executed
            # tasks from burning the GLOBAL_MAX_ATTEMPTS budget and pushing
            # the task into the P100 graveyard.  ssh_fail_attempts (below)
            # provides a separate ceiling for genuinely unreachable targets.
            # Round 16 / P1-1: record this task under its priority's
            # wave subset.  ``priority_id`` is added by run_unified_dispatch
            # when it flattens buckets; legacy/test paths that bypass that
            # step bucket under ``None``.  Cross-bucket dedup in
            # ``can_start`` walks every priority's subset so we never
            # double-dispatch even when the same task migrates between
            # priorities between recomputes.
            if self.cfg.wave_isolation:
                pid = t.get("priority_id")
                self.dispatched_this_round.setdefault(pid, set()).add(key)
            self._persist_inflight_locked()

    def maybe_advance_round(self) -> bool:
        """Round 16 / P1-1 — advance each priority's wave independently.

        For every priority_id in ``dispatched_this_round``, if its
        subset has no remaining intersection with ``inflight_by_task``
        (i.e. every task dispatched in that priority's wave has finished),
        drop the entry from the dict.  The next recompute can then
        re-classify those tasks (e.g. a fail-fast P1 task moves to P2
        recoverable) and ``can_start`` will let them dispatch again.

        Priorities whose subsets still intersect with inflight stay put.
        Returns True if at least one priority's wave advanced this call.

        Cheap O(sum of subset sizes) per call.  No-op (returns False)
        when ``cfg.wave_isolation`` is False.
        """
        if not self.cfg.wave_isolation:
            return False
        cleared: list[tuple[str | None, int]] = []
        with self.lock:
            if not self.dispatched_this_round:
                return False
            inflight_keys = set(self.inflight_by_task.keys())
            for pid in list(self.dispatched_this_round.keys()):
                members = self.dispatched_this_round[pid]
                if not members:
                    # Tidy: drop empty entries left from a prior advance
                    # so the dict doesn't accumulate stale priority ids.
                    del self.dispatched_this_round[pid]
                    continue
                still_running = members & inflight_keys
                if still_running:
                    continue
                cleared.append((pid, len(members)))
                del self.dispatched_this_round[pid]
        for pid, n in cleared:
            LOG.info(
                "wave complete for priority %s; %d task(s) drained — "
                "re-dispatch allowed in the next wave",
                pid, n,
            )
        return bool(cleared)

    def release(self, key: tuple[str, str, str, str]) -> dict | None:
        with self.lock:
            row = self.inflight_by_task.pop(key, None)
            if not row:
                return None
            self.model_inflight[row["model_dir"]] = max(
                0, self.model_inflight[row["model_dir"]] - 1
            )
            for w in self.workers:
                if w.cfg.name == row["worker"] and w.inflight > 0:
                    w.inflight -= 1
                    break
            # Round 17: stamp the drain time for the per-cell retry backoff.
            self.last_release_ts[key] = time.time()
            self._persist_inflight_locked()
            return row

    def _persist_inflight_locked(self) -> None:
        self.inflight_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.inflight_file.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for v in self.inflight_by_task.values():
                fh.write(json.dumps(v) + "\n")
        tmp.replace(self.inflight_file)


def _prune_task_attempts(task_dir: Path, keep_n: int) -> int:
    """Keep only the newest ``keep_n`` attempt subdirs in a task's runs dir.

    A task accrues one ``p*-<worker>-<hash>`` attempt directory per run; on a
    heavily-retried task these grow without bound.  After each new attempt is
    collected we prune the task dir to the newest ``keep_n`` subdirs by mtime
    (the rollup ``summary.json`` and any sibling files are untouched).  Returns
    the number of attempt dirs deleted.  Best-effort: filesystem errors are
    logged, never raised.
    """
    if keep_n < 1:
        return 0
    try:
        subdirs = [d for d in task_dir.iterdir() if d.is_dir()]
    except OSError:
        return 0
    if len(subdirs) <= keep_n:
        return 0

    def _mtime(d: Path) -> float:
        try:
            return d.stat().st_mtime
        except OSError:
            return 0.0

    subdirs.sort(key=_mtime, reverse=True)  # newest first
    deleted = 0
    for d in subdirs[keep_n:]:
        try:
            shutil.rmtree(d)
            deleted += 1
        except OSError as exc:  # noqa: BLE001
            LOG.warning("attempt-prune: failed to remove %s: %s", d, exc)
    if deleted:
        LOG.info(
            "attempt-prune: %s — kept newest %d, removed %d older",
            task_dir.name, keep_n, deleted,
        )
    return deleted


def _drain_done_file(state: DispatchState) -> int:
    """Rotate done.jsonl, then release the inflight tasks it names.

    Order matters: we atomically rename done.jsonl to
    ``done_history/done_<utc-ts>.jsonl`` FIRST and read the rotated file
    SECOND.  The rename is the atomic cut point — everything in the file at
    rename time is processed; anything appended afterwards goes to a fresh
    done.jsonl and is drained next pass.

    The earlier order (read snapshot, then rename, then process the snapshot)
    had a lost-callback race: a worker append landing between the read and
    the rename was archived but never parsed, leaking its inflight slot and
    (under ``wave_isolation``) stalling that priority's wave indefinitely.
    The archive also serves as an audit trail / future crash-replay source.
    """
    if not state.done_file.exists():
        return 0
    # Cheap, race-free pre-check: skip the rotate when there's nothing to
    # drain.  ``st_size`` is not a content snapshot, so unlike the old
    # ``read_text`` pre-read it opens no read→rename window.
    try:
        if state.done_file.stat().st_size == 0:
            return 0
    except OSError:
        return 0
    # Rotate FIRST, THEN read the rotated file.  The rename is the atomic
    # cut point: every row present at rename time lands in the archive (read
    # below); any worker append after the rename re-creates a fresh
    # done.jsonl, drained on the next pass.  Workers append via
    # ``>> done.jsonl`` over SSH and reopen the path on every append, so
    # renaming out from under them is safe.
    #
    # The OLD order (read snapshot → rename → process the snapshot) had a
    # race: a worker append landing BETWEEN the read and the rename was
    # carried into the archive but never parsed, so its inflight slot was
    # never released — the row stayed pinned forever and, under
    # wave_isolation, its priority's wave never drained (global stall).
    archive_dir = state.done_file.parent / "done_history"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"done_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jsonl"
    try:
        state.done_file.replace(archive_path)
    except OSError as exc:  # noqa: BLE001
        # Rename failed — fall back to read+truncate for this tick.  Restores
        # the small legacy race once, but never loses the whole file.
        LOG.warning("done-archive rename failed (%s); falling back to read+truncate", exc)
        raw = state.done_file.read_text(encoding="utf-8")
        state.done_file.write_text("")
    else:
        state.done_file.touch()
        raw = archive_path.read_text(encoding="utf-8")
    if not raw.strip():
        return 0
    n_done = 0
    runs_root = cfg_mod.runs_root(state.cfg)
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = (d["backend"], d["model_dir"], d["suite"], d["task"])
        # Rsync-fail path: a worker that ran the task but could NOT rsync
        # the attempt directory back to the controller (3 retries failed)
        # reports `transferred: false`.  In that case the canonical result
        # never reached this controller — releasing the inflight slot
        # would let the dispatcher re-dispatch the task while the previous
        # worker's `p*-*` dir is still orphaned remotely.  Keep the slot
        # held; the inflight-TTL pass will eventually expire it after
        # `cfg.max_inflight_age_seconds`, by which point a human can
        # decide whether to manually rescue the orphan or re-run.
        if d.get("transferred") is False:
            LOG.warning(
                "DONE-but-not-transferred [%s/%s/%s/%s] worker=%s — keeping inflight; "
                "will expire via TTL.  Reason: %s",
                d.get("backend"), d.get("model_dir"), d.get("suite"), d.get("task"),
                d.get("host_tag"), d.get("transferred_reason", "rsync_failed"),
            )
            continue
        released = state.release(key)
        if released is None:
            continue
        # V7: only DONE rows we successfully release count toward
        # session_attempts (previously bumped in reserve(), which double-
        # counted SSH-storm dispatches that never ran on a worker).  Both
        # this write and ``state.release`` mutate shared dicts; ``release``
        # already takes ``state.lock`` so we mirror that discipline here.
        with state.lock:
            state.session_attempts[key] = state.session_attempts.get(key, 0) + 1
            # Worker round-tripped, so this task is reachable; clear any
            # accumulated SSH-level failure count for it.
            state.ssh_fail_attempts.pop(key, None)
            # Stuck-worker detection: this worker just produced a DONE, so it is
            # not stalled.  Record the time and clear any stuck flag so a fresh
            # stall later re-warns.
            done_worker = released.get("worker")
            if done_worker is not None:
                state.last_done_ts_by_worker[done_worker] = time.time()
                state.stuck_flagged_workers.discard(done_worker)
            # Round 18: a rate_limit on a pooled key marks that (model_dir,
            # label) hot, so select_model_key rotates away from it for the
            # backoff-cap window.
            mk = d.get("model_key")
            if mk and d.get("status") == "rate_limit":
                state.key_pool_hot[(d["model_dir"], mk)] = time.time()
        # Refresh that task's summary AND incrementally update the flat
        # runs index the webui reads, so stats + /api/runs both see the
        # new attempt without re-walking the whole tree.
        task_dir = (
            runs_root / d["backend"] / d["model_dir"] / d["suite"] / d["task"]
        )
        try:
            refresh_summary.refresh_one_task_with_index(task_dir, runs_root)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("refresh_one_task failed: %s", exc)
        # Round 17: cap per-task experiment retention — keep the newest N
        # attempt dirs (by mtime), prune older ones.
        _prune_task_attempts(task_dir, state.cfg.max_attempts_per_task)
        LOG.info(
            "DONE [%s/%s/%s/%s] status=%s worker=%s rc=%s",
            d.get("backend"),
            d.get("model_dir"),
            d.get("suite"),
            d.get("task"),
            d.get("status"),
            d.get("host_tag"),
            d.get("rc"),
        )
        n_done += 1
    return n_done


def detect_stuck_workers(
    inflight_rows,
    last_done_ts_by_worker,
    now: float,
    *,
    stuck_age_seconds: float,
) -> list[dict]:
    """Flag workers holding inflight cells aged past the executor budget while
    the worker has produced no DONE callback within that same window.

    This is the worker-freeze signature: the in-container agents die but
    worker_runner stays alive, so the dispatcher keeps those cells inflight and
    never sees a DONE.  Recency of *any* DONE from the worker discriminates a
    genuine stall from a slow-but-churning worker (one whose individual cells
    legitimately take a long time but which keeps completing others).

    Pure / side-effect-free so it can be unit-tested and called from the
    dispatch loop.  Detection only — the caller decides whether to log a
    warning, alert the watchdog, or (deliberately not here) reclaim the slot.
    Auto-release is intentionally NOT done: the frozen worker_runner is still
    alive on the host and will self-exit at the run_eval watchdog, so releasing
    early would oversubscribe the worker.

    Args:
        inflight_rows: iterable of inflight dicts (need ``worker`` + ``ts_start``).
        last_done_ts_by_worker: {worker -> epoch of its most recent DONE}.  A
            worker absent from the map is treated as "never reported a DONE".
        now: current epoch seconds.
        stuck_age_seconds: a cell older than this — with the worker silent at
            least this long — is considered stuck.  Size as
            ``max_total_seconds + margin``.

    Returns:
        Findings sorted by worker, each
        ``{"worker", "stuck_cells", "oldest_age", "done_silence"}``.
    """
    by_worker: dict[str, list[float]] = {}
    for row in inflight_rows:
        worker = row.get("worker")
        ts_start = row.get("ts_start")
        if worker is None or not isinstance(ts_start, (int, float)):
            continue
        by_worker.setdefault(worker, []).append(float(ts_start))

    findings: list[dict] = []
    for worker, starts in by_worker.items():
        ages = [now - s for s in starts]
        stuck_cells = sum(1 for a in ages if a >= stuck_age_seconds)
        if stuck_cells == 0:
            continue
        last_done = last_done_ts_by_worker.get(worker)
        done_silence = float("inf") if last_done is None else now - last_done
        if done_silence < stuck_age_seconds:
            continue  # worker is still completing cells → slow, not stuck
        findings.append(
            {
                "worker": worker,
                "stuck_cells": stuck_cells,
                "oldest_age": max(ages),
                "done_silence": done_silence,
            }
        )
    findings.sort(key=lambda f: f["worker"])
    return findings


def _flag_stuck_workers(state: "DispatchState", now: float) -> list[dict]:
    """Run ``detect_stuck_workers`` against live state and emit a loud, deduped
    STUCK warning for each newly-stuck worker (and an INFO line when one
    recovers).  Returns the current findings (for tests / callers).

    Detection + alerting only — it does NOT reclaim the slot.  The frozen
    worker_runner is still alive on the host and self-exits at the run_eval
    watchdog; releasing here would oversubscribe the worker. The signal is for
    an external monitor or operator to skip and restart the worker.
    """
    age = getattr(state.cfg, "stuck_cell_age_seconds", 0) or 0
    if age <= 0:
        return []
    with state.lock:
        rows = list(state.inflight_by_task.values())
        last_done = dict(state.last_done_ts_by_worker)
        already = set(state.stuck_flagged_workers)
    findings = detect_stuck_workers(rows, last_done, now, stuck_age_seconds=age)
    current = {f["worker"] for f in findings}
    for f in findings:
        if f["worker"] in already:
            continue
        LOG.warning(
            "STUCK worker=%s stuck_cells=%d oldest_age=%.0fs done_silence=%s — "
            "real containers but no DONE within budget+margin (%ds); in-container "
            "agents likely dead while worker_runner hangs. Watchdog/operator "
            "should skip+restart this worker.",
            f["worker"], f["stuck_cells"], f["oldest_age"],
            ("never" if f["done_silence"] == float("inf") else "%.0fs" % f["done_silence"]),
            age,
        )
    for worker in sorted(already - current):
        LOG.info("STUCK cleared worker=%s — producing DONE / cells drained again", worker)
    with state.lock:
        state.stuck_flagged_workers = current
    return findings


def _spread_order(tasks: list[dict]) -> list[dict]:
    """Reorder bucket tasks so adjacent picks span different (model_dir, task)."""
    if not tasks:
        return tasks
    by_model: dict[str, list[dict]] = {}
    for t in tasks:
        by_model.setdefault(t["model_dir"], []).append(t)
    # Round-robin pull from per-model queues.
    keys = list(by_model.keys())
    order: list[dict] = []
    while any(by_model[k] for k in keys):
        for k in keys:
            if by_model[k]:
                order.append(by_model[k].pop(0))
    return order


def _ssh_worker_run(state: DispatchState, worker: WorkerState, task: dict) -> dict:
    """Run worker_runner.py over SSH on a worker.  Blocks until exit."""
    cfg = state.cfg
    controller_runs_dir = cfg_mod.runs_root(cfg)
    done_path = state.done_file
    # Docker image names use hyphens, but the orchestra task ``backend``
    # key uses underscores (``openclaw_edict``).  Map underscore →
    # hyphen so the auto-generated image name matches reality
    # (``clawbench-openclaw-edict:latest``).  Without this every edict
    # task fails at ``container_lifecycle.start_container`` with
    # "pull access denied for clawbench-openclaw_edict" — Round 11 + 12
    # silently misclassified 20 edict tasks as status=running rc=1.
    image = task.get("image") or (
        f"clawbench-{task['backend'].replace('_', '-')}:latest"
    )
    repo = cfg_mod.worker_repo_for(worker.cfg, cfg)
    model_full = task.get("model_full") or cfg_mod.model_full_for(task["model_dir"])
    sup = cfg.supervision.supervisor
    usim = cfg.supervision.user_simulator
    # Some non-root worker accounts cannot clean up or sync root-owned files
    # written by Docker containers. Running worker_runner via passwordless sudo
    # makes that worker's filesystem access consistent for the whole task.
    runner_bin = cfg_mod.worker_python_cmd(worker.cfg, cfg)
    cmd = (
        f"cd {shlex.quote(str(repo))} && "
        f"{runner_bin} scripts/orchestra/worker_runner.py"
        f" --repo {shlex.quote(str(repo))}"
        f" --backend {shlex.quote(task['backend'])}"
        f" --model-dir {shlex.quote(task['model_dir'])}"
        f" --model-full {shlex.quote(model_full)}"
        f" --suite {shlex.quote(task['suite'])}"
        f" --task {shlex.quote(task['task'])}"
        f" --image {shlex.quote(image)}"
        f" --controller-ssh {shlex.quote(cfg.controller.host)}"
        f" --controller-runs-dir {shlex.quote(str(controller_runs_dir))}"
        f" --controller-done-path {shlex.quote(str(done_path))}"
        f" --supervisor-provider {shlex.quote(sup.provider)}"
        f" --supervisor-model {shlex.quote(sup.model)}"
        f" --user-simulator-provider {shlex.quote(usim.provider)}"
        f" --user-simulator-model {shlex.quote(usim.model)}"
    )
    # Round 18: pass the chosen key-pool LABEL (never the secret) so the worker
    # resolves it to a real key locally.  Emitted only for pooled models, so old
    # workers (no --model-key arg) never see it until the pool is configured.
    if task.get("model_key"):
        cmd += f" --model-key {shlex.quote(task['model_key'])}"
    # Lightweight per-cell result-sync for flaky/high-latency links: ship only
    # summary/score/transcript so a network flap cannot strand a large result
    # directory and phantom-lock the slot.
    if getattr(worker.cfg, "lightweight_sync", False):
        cmd += " --lightweight-sync"
    # SSH keepalive: detect a dead TCP rather than waiting on TCP RTO
    # (~minutes).  Without this, a worker host that drops off the network
    # mid-task holds the dispatcher's ssh subprocess open indefinitely.
    # CountMax is sized to ~10 min of silence (20 × 30s) so a transient
    # WSL-load / network blip does NOT trip ssh into a non-zero exit ->
    # state.release -> re-dispatch of an attempt that is still running on the
    # worker (the double-run failure mode).  A genuinely dead worker is still
    # reclaimed ~10 min later via this same non-zero ssh exit (rc=255); the
    # STUCK detector (stuck_cell_age_seconds=2700s) only alerts (it does NOT
    # release the slot), and the inflight TTL is the 24h backstop.
    full = [
        "ssh",
        "-o", "ConnectTimeout=20",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=20",
        "-o", "TCPKeepAlive=yes",
        worker.cfg.ssh,
        cmd,
    ]
    LOG.info(
        "DISPATCH [%s] %s/%s/%s/%s",
        worker.cfg.name,
        task["backend"],
        task["model_dir"],
        task["suite"],
        task["task"],
    )
    timeout_seconds = state.cfg.worker_timeout_seconds
    try:
        r = subprocess.run(
            full,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        LOG.error(
            "ssh worker %s hung past %ds — killing and releasing inflight",
            worker.cfg.name,
            timeout_seconds,
        )
        # subprocess.run already killed the child; release the slot.
        key = (task["backend"], task["model_dir"], task["suite"], task["task"])
        state.release(key)
        # Treat hung-ssh as a failure for backoff purposes too.
        worker.consecutive_ssh_failures += 1
        worker.unavailable_until = time.time() + _ssh_backoff_seconds(worker.consecutive_ssh_failures)
        _bump_ssh_fail_attempts(state, key)
        return task
    if r.returncode != 0:
        LOG.error(
            "ssh worker %s failed rc=%s stderr=%s",
            worker.cfg.name,
            r.returncode,
            r.stderr.strip()[:300],
        )
        # Mark worker unavailable so the dispatcher doesn't hot-loop
        # re-dispatching to a host that's down.  Backoff is exponential
        # (10s → 30s → 90s → 5min cap).  First successful ssh resets.
        worker.consecutive_ssh_failures += 1
        backoff = _ssh_backoff_seconds(worker.consecutive_ssh_failures)
        worker.unavailable_until = time.time() + backoff
        LOG.warning(
            "worker %s marked unavailable for %.0fs (consecutive ssh failures: %d)",
            worker.cfg.name, backoff, worker.consecutive_ssh_failures,
        )
        # Release the inflight lock so run_one_bucket doesn't deadlock.
        # Note: any partial run on the worker may still be running but we
        # cannot wait for it.  If/when its rsync + done callback land
        # they'll arrive late but the dispatcher will still write the
        # result via _drain_done_file (release tolerates missing keys).
        key = (task["backend"], task["model_dir"], task["suite"], task["task"])
        state.release(key)
        _bump_ssh_fail_attempts(state, key)
    else:
        # ssh exited cleanly — host is reachable.  Reset backoff so
        # transient blips don't permanently demote a worker.
        if worker.consecutive_ssh_failures:
            LOG.info("worker %s recovered after %d ssh failure(s)",
                     worker.cfg.name, worker.consecutive_ssh_failures)
            worker.consecutive_ssh_failures = 0
            worker.unavailable_until = 0.0
        # V7: this task's SSH dispatch succeeded, whatever happened on
        # the worker afterwards is no longer an SSH-level failure.
        _reset_ssh_fail_attempts(
            state,
            (task["backend"], task["model_dir"], task["suite"], task["task"]),
        )
    return task


def _drain_loop(state: DispatchState, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            _drain_done_file(state)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("drain loop: %s", exc)
        stop_event.wait(2)


def run_one_bucket(
    state: DispatchState,
    executor: ThreadPoolExecutor,
    bucket: dict,
    *,
    max_tasks: int | None = None,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Submit tasks from this bucket; wait until they all finish.

    ``max_tasks`` caps how many tasks we *start*; the function still waits
    for those to finish before returning.  ``None`` means run the whole
    bucket.

    When ``shutdown_event`` fires we stop submitting NEW tasks but still
    wait on already-inflight ones so their done callbacks are drained
    and inflight.jsonl is consistent on next startup.

    Round 11 / A1: kept as a single-bucket helper for ``--once`` /
    smoke-test paths; the main loop now uses ``run_unified_dispatch``
    to fill workers across ALL priority buckets in priority order.
    """
    tasks = _spread_order(list(bucket.get("tasks") or []))
    if max_tasks is not None:
        tasks = tasks[:max_tasks]
    LOG.info("== bucket %s : %d tasks ==", bucket["priority_id"], len(tasks))
    pending = list(tasks)
    futures: list[Future] = []
    # Wait condition uses ``futures`` (tasks WE dispatched this bucket) rather
    # than ``any(w.inflight)`` (which includes restored ghost rows from the
    # Phase 3.1 inflight restore path — those have no live worker driving them
    # to DONE, so waiting on them deadlocks the bucket loop indefinitely).
    # Ghost rows are handled separately by the stats._load_inflight TTL pass
    # on the next priority recompute.
    while pending or any(not f.done() for f in futures):
        if shutdown_event is not None and shutdown_event.is_set():
            if pending:
                LOG.info(
                    "shutdown requested mid-bucket; %d tasks not yet dispatched, "
                    "waiting on %d still-running futures",
                    len(pending),
                    sum(1 for f in futures if not f.done()),
                )
            pending = []  # stop submitting new ones; let dispatched futures drain
        progress = False
        for task in list(pending):
            # Pick the worker with the fewest in-flight tasks first
            # (least-loaded scheduling). Python's sorted() is stable, so
            # ties are broken by the worker's position in cfg.workers —
            # preserving config-deterministic order when load is equal.
            # Round-5 Phase 5: replaces the previous FIFO greedy fill where
            # the first worker was always tried first; under worker-drop
            # scenarios, one later worker could fill up before any task
            # spilled to the next.
            for worker in sorted(state.workers, key=lambda w: w.inflight):
                if state.can_start(task, worker):
                    state.reserve(task, worker)
                    pending.remove(task)
                    futures.append(executor.submit(_ssh_worker_run, state, worker, task))
                    progress = True
                    break
        if not progress:
            time.sleep(2)
    for f in futures:
        try:
            f.result(timeout=1)
        except Exception:
            pass
    return len(tasks)


def run_unified_dispatch(
    state: DispatchState,
    executor: ThreadPoolExecutor,
    cfg,
    *,
    tasks_root: Path,
    runtime_dir: Path,
    max_tasks: int | None = None,
    shutdown_event: threading.Event | None = None,
    poll_interval_seconds: float = 2.0,
    recompute_interval_seconds: float = 5.0,
    full_refresh_interval_seconds: float = 60.0,
    dispatch_stagger_sec: float = 0.3,
) -> int:
    """Round 11 / A1: cross-priority dispatch (replaces bucket barrier).

    Walks ALL priority buckets each tick, flat-ordered by priority,
    and fills every idle worker with the highest-priority task it
    can take.  No T1→T2 barrier: T2 can fill an idle worker while
    T1 still has stuck inflight, eliminating the bucket-barrier
    stall Round 10 hit.

    Recomputation:
    - Buckets get refreshed every ``recompute_interval_seconds`` so
      tasks that flipped status (e.g. rate_limit → P3 retry bucket)
      get picked up automatically.
    - Between refreshes the dispatcher polls done.jsonl every
      ``poll_interval_seconds`` to release inflight slots quickly.

    Stops when:
    - shutdown_event fires (Ctrl+C / SIGTERM)
    - ``max_tasks`` (if set) have been *dispatched* and the started work drained
    - all buckets are empty AND inflight is empty (queue fully drained)

    Returns total tasks dispatched.
    """
    dispatched_count = 0
    futures: list[Future] = []
    dispatch_limit_reached = False
    last_recompute = 0.0
    # Round 16 / P1-2: distinct timer for the expensive full refresh.
    # Previously the full-refresh decision used ``last_recompute``, which
    # the fast (5s) recompute resets on every tick — so the 60s full
    # refresh fired only once at startup and never again, even after
    # hours of runtime.
    last_full_refresh = 0.0
    buckets: list[dict] = []

    while True:
        if shutdown_event is not None and shutdown_event.is_set():
            LOG.info(
                "shutdown requested; %d futures still in flight",
                sum(1 for f in futures if not f.done()),
            )
            break

        if dispatch_limit_reached:
            _drain_done_file(state)
            if not any(not f.done() for f in futures) and not state.inflight_by_task:
                LOG.info(
                    "unified dispatch: max_tasks=%d drained, exiting",
                    max_tasks,
                )
                break
            time.sleep(poll_interval_seconds)
            continue

        # Round 15 / P1: at the top of each iteration, check whether the
        # current wave has fully drained (no inflight task is still in
        # ``dispatched_this_round``).  If yes, clear the set so the next
        # recompute can re-classify members (e.g. a rate_limit task moves
        # from inflight → P2 → eligible again in the new wave).  When
        # cfg.wave_isolation is False this is a cheap no-op.
        state.maybe_advance_round()

        now = time.time()
        if now - last_recompute >= recompute_interval_seconds or not buckets:
            # Two refresh tiers:
            # - ``recompute_interval_seconds`` (default 5s): fast pass,
            #   just re-walks ``summary.json`` + ``inflight.jsonl`` to
            #   pick up newly-DONE tasks.  Closes the race window where
            #   a freshly-released task could be re-dispatched from a
            #   stale bucket cache.
            # - ``full_refresh_interval_seconds`` (default 60s): also
            #   triggers ``refresh_summary.refresh_all_tasks`` which
            #   walks every per-attempt dir.  More expensive; only
            #   needed when worker-side summary writes have to be
            #   re-aggregated (long-running rounds).
            full_refresh = (
                last_full_refresh == 0.0
                or now - last_full_refresh >= full_refresh_interval_seconds
            )
            expired_inflight: set[tuple[str, str, str, str]] = set()
            buckets = stats_mod.recompute_priorities(
                cfg, tasks_root=tasks_root, runtime_dir=runtime_dir,
                do_refresh=full_refresh,
                session_attempts=state.session_attempts,
                expired_inflight_out=expired_inflight,
            )
            # P1-1 follow-up: persist a read-only snapshot so monitoring
            # tools that recompute outside this process (top.py
            # --tasks-root) see the same P100/P200 routing the live
            # dispatcher applies.
            try:
                stats_mod.write_session_attempts_snapshot(
                    runtime_dir, state.session_attempts,
                )
            except OSError as exc:
                LOG.warning("session_attempts snapshot write failed: %s", exc)
            # Round 16 / P0-3: stats._load_inflight already rewrote the
            # on-disk inflight.jsonl to drop these rows; mirror the drop
            # in DispatchState so worker.inflight / model_inflight /
            # inflight_by_task agree with the persisted file.  release()
            # is a no-op for keys that aren't currently held.
            for key in expired_inflight:
                released = state.release(key)
                if released is not None:
                    LOG.warning(
                        "inflight: TTL released in-memory slot for "
                        "%s/%s/%s/%s (worker=%s)",
                        key[0], key[1], key[2], key[3],
                        released.get("worker"),
                    )
            # Stuck-worker stall detector: flag any worker holding cells aged
            # past the executor budget+margin while it has produced no DONE in
            # that window (the worker-freeze pattern the watchdog can miss).
            try:
                _flag_stuck_workers(state, now)
            except Exception as exc:  # noqa: BLE001 — detector must never crash the loop
                LOG.warning("stuck-worker detector failed: %s", exc)
            last_recompute = now
            if full_refresh:
                last_full_refresh = now
                # Only log full-refresh summaries; fast refreshes happen
                # every few seconds and would flood the log.
                LOG.info(
                    "unified dispatch refresh:\n%s",
                    stats_mod.summarise_priorities(buckets),
                )

        # Flat task list in priority order — first bucket's tasks first,
        # then second bucket's, etc.  Within a bucket, preserve the
        # _spread_order pattern (balance across model_dirs / suites).
        # Each task is tagged with its source priority_id so
        # ``DispatchState.can_start`` knows whether to apply the
        # session-attempts gate (skipped for P100/P200 graveyard +
        # suspended buckets, applied for everything else).
        flat_tasks: list[dict] = []
        for bucket in buckets:
            pid = bucket["priority_id"]
            for t in _spread_order(list(bucket.get("tasks") or [])):
                flat_tasks.append({**t, "priority_id": pid})

        if (
            not flat_tasks
            and not any(not f.done() for f in futures)
            and not state.inflight_by_task
        ):
            # All buckets empty + no local futures + no restored inflight =
            # queue truly drained.  Round 16 / P0-2: the inflight check
            # keeps a freshly-restarted dispatcher alive while previously-
            # restored inflight rows are still in flight on workers — exit
            # too early and we stop draining done.jsonl, leak slots, and
            # never run TTL cleanup on rows whose workers died with the
            # prior dispatcher.
            LOG.info("unified dispatch: queue drained, exiting")
            break

        # Try to fill every idle worker with the highest-priority
        # task it can take.  We sort workers by inflight (least loaded
        # first) so the work spreads evenly across the cluster.
        progress = False
        for worker in sorted(state.workers, key=lambda w: w.inflight):
            if worker.cfg.skip:
                continue
            if worker.inflight >= worker.cfg.parallel:
                continue
            # Walk tasks in priority order; first feasible one wins.
            picked: dict | None = None
            for task in flat_tasks:
                if state.can_start(task, worker):
                    picked = task
                    break
            if picked is None:
                continue
            state.reserve(picked, worker)
            flat_tasks.remove(picked)
            futures.append(executor.submit(_ssh_worker_run, state, worker, picked))
            dispatched_count += 1
            progress = True
            # Stagger the first wave of SSH dispatches so many parallel
            # ssh calls from the dispatcher do not simultaneously hit each
            # worker's sshd MaxStartups gate ("kex_exchange_identification:
            # Connection reset by peer"). After 4*N workers we drop to a
            # negligible sleep — sustained dispatch isn't bursty, the storm
            # only happens at startup when every worker is idle.
            if dispatch_stagger_sec > 0:
                stagger_threshold = 4 * max(1, len(state.workers))
                sleep_sec = (
                    dispatch_stagger_sec
                    if dispatched_count <= stagger_threshold
                    else 0.05
                )
                time.sleep(sleep_sec)
            if max_tasks is not None and dispatched_count >= max_tasks:
                LOG.info(
                    "unified dispatch: max_tasks=%d reached, stopping new dispatch and draining",
                    max_tasks,
                )
                dispatch_limit_reached = True
                break

        # Sleep briefly between dispatch waves.  done.jsonl gets drained
        # by the separate _drain_loop thread every 2s, so inflight slots
        # free up naturally between our loop iterations.
        if not progress:
            time.sleep(poll_interval_seconds)

    # Final wait on any inflight futures so done callbacks land before
    # we return.  Best-effort with a timeout per future.
    for f in futures:
        try:
            f.result(timeout=1)
        except Exception:
            pass
    return dispatched_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Clawbench orchestra dispatcher")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--tasks-root", required=True, type=Path)
    parser.add_argument("--max-workers", type=int, default=64, help="ssh thread pool size")
    parser.add_argument("--once", action="store_true", help="run a single drain pass and exit")
    parser.add_argument("--max-tasks", type=int, default=None,
                        help="cap how many tasks are started in a single dispatch run "
                             "(useful for smoke tests; default = unlimited)")
    parser.add_argument(
        "--dispatch-stagger-sec", type=float, default=0.3,
        help="V7: sleep between submit() calls during the first "
             "4 × workers dispatches to avoid sshd MaxStartups storm; "
             "decays to 0.05s thereafter.  Set to 0 to disable.",
    )
    parser.add_argument(
        "--skip-adapter-prewarm", action="store_true",
        help="V7: skip the per-worker ensure_adapter pre-warm step at "
             "startup (debug / fast-iteration only; --once also skips it).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    cfg = cfg_mod.load(args.config)
    runtime_dir = cfg_mod.runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    workers = [WorkerState(cfg=w) for w in cfg.workers]

    state = DispatchState(
        cfg=cfg,
        workers=workers,
        done_file=runtime_dir / "done.jsonl",
        inflight_file=runtime_dir / "inflight.jsonl",
        task_meta_root=args.tasks_root,
    )
    state.done_file.touch(exist_ok=True)
    state.inflight_file.touch(exist_ok=True)

    # Rebuild in-memory inflight from the persisted file so a crash +
    # restart doesn't lose model_caps / worker counter accounting.  The
    # persisted file already excludes these tasks from priority buckets
    # via stats._load_inflight, but the dispatcher's own counters need
    # to know about them too or it'll over-dispatch on the same model.
    restored = state.restore_inflight_from_disk()
    if restored:
        LOG.info("inflight: restored %d in-flight row(s) on startup", restored)

    # Preflight verifies worker docker images / apt / pip / ports before
    # dispatch.  Round-16+ deployment ships the runtime via docker images
    # (clawbench-runtime-base etc.), so the host-side apt/pip check is
    # stale on most current clusters; the cost of a stale check is a
    # mass-refusal at startup.
    #
    # Defaults are inverted from earlier rounds: preflight is OPT-IN via
    # ``CLAWBENCH_RUN_PREFLIGHT=1`` (or the legacy negative
    # ``CLAWBENCH_SKIP_PREFLIGHT=0``).  When opt-in, the same strict
    # check still applies: any reachable worker missing a required item
    # fails the dispatcher.
    _run_preflight = (
        os.environ.get("CLAWBENCH_RUN_PREFLIGHT") in {"1", "true", "yes"}
        or os.environ.get("CLAWBENCH_SKIP_PREFLIGHT") in {"0", "false", "no"}
    )
    if _run_preflight:
        try:
            preflight.preflight_check(cfg)
        except preflight.PreflightError as exc:
            LOG.error("preflight failed; refusing to dispatch:\n%s", exc)
            return 1
    else:
        LOG.info(
            "preflight skipped by default (container-only worker model).  "
            "Set CLAWBENCH_RUN_PREFLIGHT=1 to enforce host-side apt/pip/port "
            "checks on workers."
        )

    # V7: pre-warm proxy adapters on every reachable worker so the
    # first SSH wave doesn't race ``acquire_shared_proxy_tunnel`` x N
    # for the same 9001 listener — that race is the V6 root-cause of
    # task_104_36's ``Address already in use`` infra_error.  Skipped
    # for ``--once`` smoke runs (they need fast deterministic startup)
    # and ``--skip-adapter-prewarm`` (explicit override for debugging).
    if not args.once and not args.skip_adapter_prewarm:
        LOG.info("pre-warming proxy adapters on %d worker(s)...",
                 len([w for w in cfg.workers if not w.skip]))
        try:
            from . import ensure_adapter as ensure_adapter_mod
            prewarm_rc = ensure_adapter_mod.run_all(
                cfg, tasks_root=args.tasks_root,
            )
        except Exception as exc:  # noqa: BLE001
            LOG.error("adapter pre-warm crashed: %s — refusing to dispatch", exc)
            return 1
        if prewarm_rc != 0:
            LOG.error("adapter pre-warm failed on >=1 worker (rc=%d) — "
                      "refusing to dispatch", prewarm_rc)
            return 1
        LOG.info("adapter pre-warm done")

    stop_event = threading.Event()
    shutdown_event = threading.Event()
    # SIGINT / SIGTERM → set shutdown_event so run_one_bucket stops
    # submitting new tasks and the main loop exits after the current
    # bucket drains.  We deliberately do NOT kill already-inflight ssh
    # subprocesses — the worker_runner's done callback writes to
    # done.jsonl, which our drainer flushes before exit; killing them
    # would leak inflight rows.
    def _request_shutdown(signum, _frame):  # noqa: ARG001
        if not shutdown_event.is_set():
            LOG.info("shutdown requested (signal %d); draining…", signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    drainer = threading.Thread(target=_drain_loop, args=(state, stop_event), daemon=True)
    drainer.start()

    try:
        with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            # Round 11 / A1: cross-priority unified dispatch.  Drops the
            # bucket-barrier ``for bucket: run_one_bucket(); break`` in
            # favor of a unified picker that fills idle workers across
            # all buckets simultaneously, ordered by priority.  This
            # eliminates the T1-stuck-blocks-T2 stall observed when a
            # single slow task held a top-priority bucket for too long.
            if args.once:
                # ``--once`` keeps the legacy single-bucket-drain
                # behavior for smoke tests and CI fixtures, since
                # those tests rely on deterministic top-bucket-only
                # exit semantics.
                buckets = stats_mod.recompute_priorities(
                    cfg, tasks_root=args.tasks_root, runtime_dir=runtime_dir,
                    session_attempts=state.session_attempts,
                )
                try:
                    stats_mod.write_session_attempts_snapshot(
                        runtime_dir, state.session_attempts,
                    )
                except OSError as exc:
                    LOG.warning("session_attempts snapshot write failed: %s", exc)
                LOG.info(
                    "priority breakdown:\n%s",
                    stats_mod.summarise_priorities(buckets),
                )
                for bucket in buckets:
                    if bucket["tasks"]:
                        run_one_bucket(
                            state, ex, bucket,
                            max_tasks=args.max_tasks,
                            shutdown_event=shutdown_event,
                        )
                        break
                return 0

            dispatched = run_unified_dispatch(
                state, ex, cfg,
                tasks_root=args.tasks_root,
                runtime_dir=runtime_dir,
                max_tasks=args.max_tasks,
                shutdown_event=shutdown_event,
                dispatch_stagger_sec=args.dispatch_stagger_sec,
            )
            LOG.info(
                "dispatcher exiting cleanly (%d tasks dispatched this run)",
                dispatched,
            )
            return 0
    finally:
        # Final drain pass so any done.jsonl rows that landed while we
        # were tearing down still release their inflight locks.
        try:
            _drain_done_file(state)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("final drain: %s", exc)
        stop_event.set()
        drainer.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
