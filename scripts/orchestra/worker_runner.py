"""Worker-side entrypoint, invoked by ``dispatch`` over SSH on each worker host.

Responsibilities:
  1. Run a single task via ``scripts/run_eval.py``, instructing it (via the
     ``CLAWBENCH_HOST_TAG`` environment variable) to embed our hostname in
     the attempt-subdir name so concurrent attempts from different workers
     never collide.
  2. Locate the resulting attempt directory.
  3. ``rsync`` it back to the controller's runs root.
  4. Tell the controller we're done by appending a JSON line to its
     ``runtime/done.jsonl``.
  5. Delete our local copy so the worker accumulates no run residue.

This module is intentionally lightweight — it has no dependency on the rest
of the orchestra package — so it can be deployed as a standalone file to
every worker.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

# Inject the repo root so the lib.status single-source-of-truth is importable
# on a worker that runs this file directly (not as a package).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from lib.status import normalize_final_status as _normalize_final_status
except Exception:
    # On a worker that hasn't been re-synced after Round 6, lib.status
    # might be missing. Fall back to a no-op so worker_runner stays
    # backwards-compatible (the dispatcher's drain will still accept
    # the legacy ops-layer status strings, just without normalization
    # at the source).
    def _normalize_final_status(value, *, rc=None):  # type: ignore[misc]
        return value or "missing"


def _terminalize_stale_nonterminal(raw_status: str, rc) -> str:
    """Map a STALE non-terminal on-disk status + a nonzero exit code to the
    real ops-layer terminal (caller still normalizes via lib.status).

    rc==124 reaching worker_runner is the ``run_eval`` watchdog (``os._exit(124)``)
    force-killing a WEDGED eval process — a hung supervisor/grader call, an
    un-joined thread, or a rate-limit retry storm. The EXECUTOR did not exceed
    its own budget; the whole eval wedged. So this is ``executor_incomplete``
    (bounded rerun), NOT ``global_timeout``. ``global_timeout`` is reserved for
    the in-loop cumulative executor-budget terminal, which writes its own
    terminal ``summary.json`` (raw_status='global_timeout', never reaching this
    stale-running path). Any other nonzero (SIGKILL -9, crash) is likewise
    ``FAIL_rc`` -> ``executor_incomplete``.
    """
    if raw_status in ("running", "missing") and rc not in (0, None):
        return f"FAIL_rc={rc}"
    return raw_status


try:
    # The canonical run directory name shared by run_eval and orchestra:
    # ``runs/<backend>/model_slug(model_full)/<suite>/<task>/p*``.  Keep this
    # import in sync with dispatch config validation so single-task and
    # distributed runs are relocatable without path rewriting.
    from lib.runner.task_config import model_slug as _model_slug
except Exception:
    def _model_slug(model):  # type: ignore[misc]
        return (model or "unknown-model").replace("/", "-").replace(".", "-")

try:
    # Round 18: resolve a per-attempt key-pool LABEL → real key locally, so the
    # executor uses a pooled key without any secret crossing the SSH boundary.
    from lib.runner import key_pool as _key_pool
except Exception:
    _key_pool = None  # type: ignore[assignment]

DEFAULT_REPO = Path("/opt/clawbench/Clawbench")


# Round 12 follow-up: container-death watchdog.
#
# When ``run_eval`` crashes early, the dispatcher's SSH-side bookkeeping
# considers the worker slot free the instant ``worker_runner`` returns.
# But ``docker run -d`` started a detached container; that container can
# persist for several seconds while ``run_eval``'s finally block is
# still calling ``docker_rm`` (slow under daemon load).  During that
# window the dispatcher fires a new task into the same slot, the new
# task starts another container, and now two containers exist where
# the dispatcher thinks one does.  At parallel >=17 this cascade is
# what produces the over-spawn observed in Round 12 probe2 (84
# containers vs 70-slot cap).
#
# Closing the race window here, on the worker side, before SSH returns,
# means the dispatcher's slot release is gated on actual container
# death — and stays simple (SSH exit = slot free).
_CONTAINER_DEATH_POLL_INTERVAL = 0.5
_CONTAINER_DEATH_MAX_WAIT_SEC = 20


def _wait_for_containers_gone(task_id: str) -> None:
    """Poll ``docker ps`` until any containers matching this task are
    gone, then force-kill stragglers.

    Containers are named ``clawbench-<task_id>-session-<uuid>`` by
    ``lib/runner/container_lifecycle.py:start_container``.  We grep by
    the ``clawbench-<task_id>-`` prefix so any session UUID is caught.

    No-op when ``docker`` is unavailable (test envs).  Best-effort:
    errors are swallowed rather than raised — the existing finally
    blocks in ``run_eval`` and the dispatcher-side recompute already
    handle the residual cases.
    """
    pattern = f"clawbench-{task_id}-"
    deadline = time.time() + _CONTAINER_DEATH_MAX_WAIT_SEC
    last_seen: list[str] = []
    while time.time() < deadline:
        try:
            r = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"name={pattern}"],
                capture_output=True, text=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return  # docker absent or hung — nothing we can do
        ids = [i for i in r.stdout.split() if i]
        if not ids:
            return  # container(s) cleaned up naturally
        last_seen = ids
        time.sleep(_CONTAINER_DEATH_POLL_INTERVAL)
    # Hit the timeout — force-kill whatever is left.  This is the
    # belt-and-suspenders cleanup: ``run_eval``'s finally should have
    # done it; if it didn't (SIGKILL'd worker_runner, daemon hang,
    # whatever), at least we don't leave the container running.
    if last_seen:
        try:
            subprocess.run(
                ["docker", "rm", "-f", *last_seen],
                check=False, capture_output=True, timeout=10,
            )
            print(
                f"[worker] force-removed {len(last_seen)} stuck container(s) "
                f"for task {task_id}",
                file=sys.stderr,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass


def _hostname_tag() -> str:
    return socket.gethostname().lower().replace("-", "")


def _find_attempt_dir(
    runs_root: Path,
    backend: str,
    model_dir: str,
    suite: str,
    task: str,
    *,
    min_mtime: float | None = None,
) -> Path | None:
    task_dir = runs_root / backend / model_dir / suite / task
    if not task_dir.is_dir():
        return None
    def _fresh_enough(path: Path) -> bool:
        if min_mtime is None:
            return True
        try:
            return path.stat().st_mtime >= min_mtime
        except OSError:
            return False
    candidates = sorted(
        (
            p
            for p in task_dir.iterdir()
            if p.is_dir() and p.name.startswith("p") and _fresh_enough(p)
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _run_one(
    *,
    repo: Path,
    task_yaml: Path,
    image: str,
    backend: str,
    model_full: str,
    supervisor_provider: str,
    supervisor_model: str,
    user_simulator_provider: str,
    user_simulator_model: str,
    timeout_sec: int,
    extra_env: dict[str, str],
) -> tuple[int, str, str]:
    """Run scripts/run_eval.py once and return ``(rc, stdout, stderr)``.

    Capture stdout/stderr in full so the caller can save them into the
    attempt directory.  Without this the runner used to discard everything
    and a network flake / install.sh death looked identical to a passing
    run (rc=1 with no logs anywhere reachable from the controller).
    """
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        str(task_yaml),
        image,
        "--agent-sys",
        backend,
        "--model",
        model_full,
        "--supervisor-provider",
        supervisor_provider,
        "--supervisor-model",
        supervisor_model,
        "--user-simulator-provider",
        user_simulator_provider,
        "--user-simulator-model",
        user_simulator_model,
        "--fresh",
    ]
    env = os.environ.copy()
    env.update(extra_env)
    try:
        r = subprocess.run(
            cmd,
            cwd=str(repo),
            env=env,
            timeout=timeout_sec,
            capture_output=True,
            text=True,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired as exc:
        # Exception attrs may be None or bytes; coerce to str safely.
        out = exc.stdout
        err = exc.stderr
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return -999, out or "", (err or "") + f"\n[worker_runner] TimeoutExpired after {timeout_sec}s\n"


def _rsync_to_controller(attempt_dir: Path, controller_ssh: str, controller_runs_dir: Path, key: dict, lightweight: bool = False) -> tuple[bool, str]:
    """Rsync the attempt dir back to the controller.

    Returns ``(transferred, reason)`` where ``transferred`` is True on
    success and ``reason`` is a short failure tag the controller will
    log if transferred is False.
    """
    target = (
        controller_runs_dir
        / key["backend"]
        / key["model_dir"]
        / key["suite"]
        / key["task"]
    )
    # Ensure remote parent exists, then rsync the whole attempt dir.
    mkdir_cmd = [
        "ssh",
        "-o",
        "ConnectTimeout=15",
        controller_ssh,
        f"mkdir -p {_quote(target)}",
    ]
    subprocess.run(mkdir_cmd, check=False)

    # Round 9 / A1: never transfer privacy/env.env to the controller.  The
    # supervisor's role workspace can read it locally on the worker, but
    # the env.env values (provider API keys, account credentials,
    # task-level secrets) must NOT live in the long-term run archive that
    # the WebUI / aggregator / operator dashboards read.  Excluding at
    # the rsync layer means even a misbehaving collector cannot pull the
    # values to the controller.
    # The Codex CLI's plugin marketplace pack, raw role-home transcripts, and
    # npm/package caches are regenerated inside the container image and can be
    # large. They also may contain supervisor-only context. Exclude them at the
    # rsync layer so the controller archive keeps only evaluation artifacts.
    if lightweight:
        # Some remote workers cannot reliably ship full attempt directories during
        # short network flaps. Lightweight mode transfers only the files the
        # controller needs to mark the cell terminal, score it, and analyze it.
        # Full artifacts remain in the worker's local runs/ for a later batch sync.
        rsync_cmd = [
            "rsync", "-aP", "--timeout=60",
            "--include=summary.json", "--include=score.json",
            "--include=transcript.jsonl", "--include=meta.json",
            "--include=usage.json", "--exclude=*",
            "-e", "ssh -o ConnectTimeout=15",
            str(attempt_dir) + "/",
            f"{controller_ssh}:{target}/{attempt_dir.name}/",
        ]
    else:
        rsync_cmd = [
            "rsync",
            "-aP",
            # I/O timeout: if a flap stalls the stream, fail this attempt fast (rc=30)
            # and let the retry loop resume via --partial, instead of hanging on a
            # half-open TCP connection until the kernel times out minutes later.
            "--timeout=90",
            "--exclude=codex_sessions/*/workspace/privacy/",
            "--exclude=codex_sessions/*/home/sessions/",
            "--exclude=codex_sessions/*/home/.tmp/",
            "--exclude=codex_sessions/*/home/.cache/",
            "--exclude=codex_sessions/*/home/.npm/",
            "-e",
            "ssh -o ConnectTimeout=15",
            str(attempt_dir) + "/",
            f"{controller_ssh}:{target}/{attempt_dir.name}/",
        ]
    # Full result rsync over a high-latency link can be cut by a transient
    # network flap, yielding rc=23 (partial transfer). `-aP` keeps partial files,
    # so each retry resumes instead of restarting; the retry window just needs to
    # outlast common multi-minute flaps. Low-latency workers usually succeed on
    # attempt 0, so this is cheap for local clusters.
    last_rc = -1
    retries = 8
    for attempt in range(retries):
        r = subprocess.run(rsync_cmd, capture_output=True, text=True)
        last_rc = r.returncode
        if r.returncode == 0:
            return True, "ok"
        time.sleep(min(10 * (attempt + 1), 90))  # 10,20,..,90 — ~5min total window
    return False, f"rsync_failed_after_{retries}_retries_rc={last_rc}"


def _gc_stale_docker_resources() -> None:
    """Round 12 follow-up: piggyback on the worker GC schedule to also
    clean stopped docker containers + dangling images + build cache
    that haven't been used in 14 days.

    Containers tagged ``clawbench-*`` should normally be removed by
    ``run_eval``'s finally block or the new ``_wait_for_containers_gone``
    fallback in this file.  Anything older than 14 days is by
    definition abandoned (crashed worker_runner SIGKILL'd before
    cleanup, host reboot, etc.) — safe to delete.

    Best-effort: docker daemon unavailable / hung is silently
    swallowed.  Runs synchronously but typically <2s for the daily
    sweep.
    """
    cmds = [
        # Stopped containers older than 2h. A 14d window lets exited cell
        # containers pile up and bloat docker storage. Cell containers are
        # short-lived; 2h is ample for post-mortem inspection of a recent
        # failure while keeping the backlog bounded.
        ["docker", "container", "prune", "-f", "--filter", "until=2h"],
        # Dangling images (no tag, no container) older than 14d.  Kept long so
        # we don't re-pull base images between runs.
        ["docker", "image", "prune", "-f", "--filter", "until=336h"],
        # Build cache older than 14d.
        ["docker", "builder", "prune", "-f", "--filter", "until=336h"],
    ]
    for cmd in cmds:
        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return  # docker absent or hung — skip the rest


def _gc_stale_local_attempts(runs_root: Path, cleanup_days: int) -> int:
    """Sweep abandoned ``p*-*`` attempt directories older than N days.

    A crashed worker (OOM, container kill, host reboot) leaves its
    in-progress attempt under ``$repo/runs/<backend>/<model>/<suite>/<task>/p*/``
    without rsync-ing or cleaning up.  Over months this accumulates;
    pruning anything past ``cleanup_days`` keeps worker disk from
    filling without removing anything the dispatcher might still need
    (the dispatcher's authoritative copy is on the controller, not
    here).  Set ``cleanup_days=0`` to disable.

    Returns the number of directories removed.
    """
    if cleanup_days <= 0 or not runs_root.is_dir():
        return 0
    cutoff = time.time() - cleanup_days * 86400
    removed = 0
    # The runs/ tree is 4 levels deep: backend/model_dir/suite/task/p*-*.
    # We walk just deep enough to find the p*-* attempt dirs.
    for backend_dir in runs_root.iterdir():
        if not backend_dir.is_dir():
            continue
        for model_dir in backend_dir.iterdir():
            if not model_dir.is_dir():
                continue
            for suite_dir in model_dir.iterdir():
                if not suite_dir.is_dir():
                    continue
                for task_dir in suite_dir.iterdir():
                    if not task_dir.is_dir():
                        continue
                    for attempt in task_dir.iterdir():
                        if not attempt.is_dir() or not attempt.name.startswith("p"):
                            continue
                        try:
                            if attempt.stat().st_mtime < cutoff:
                                shutil.rmtree(attempt, ignore_errors=True)
                                removed += 1
                        except OSError:
                            continue
    return removed


def _report_done(controller_ssh: str, done_path: Path, payload: dict) -> None:
    line = shlex.quote(json.dumps(payload, separators=(",", ":")))
    cmd = [
        "ssh",
        "-o",
        "ConnectTimeout=15",
        controller_ssh,
        f"mkdir -p {_quote(done_path.parent)} && printf '%s\\n' {line} >> {_quote(done_path)}",
    ]
    last = None
    for attempt in range(3):
        try:
            last = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            last = exc
        else:
            if last.returncode == 0:
                return
        time.sleep(2 * (attempt + 1))
    if isinstance(last, subprocess.TimeoutExpired):
        raise RuntimeError("controller DONE callback timed out after 3 attempts")
    rc = getattr(last, "returncode", "?")
    stderr = (getattr(last, "stderr", "") or "").strip()
    raise RuntimeError(f"controller DONE callback failed after 3 attempts rc={rc} stderr={stderr[:300]}")


def _quote(p: Path | str) -> str:
    return shlex.quote(str(p))


def main() -> int:
    parser = argparse.ArgumentParser(description="Clawbench worker runner")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--model-full", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--timeout", type=int, default=20000)
    parser.add_argument("--controller-ssh", required=True, help="ssh alias of the controller")
    parser.add_argument("--controller-runs-dir", type=Path, required=True)
    parser.add_argument("--controller-done-path", type=Path, required=True)
    parser.add_argument("--host-tag", default=None, help="overrides auto-detected host tag")
    parser.add_argument(
        "--lightweight-sync", action="store_true", dest="lightweight_sync",
        help="Sync only summary/score/transcript metadata instead of the full "
             "attempt directory. Useful for remote or flaky workers; full "
             "artifacts stay in the worker's local runs/ for later batch sync."
    )
    # Supervisor + user-simulator bindings come from the dispatcher's
    # orchestra.local.yaml supervision: block (no hard-coded fallbacks
    # here — a missing flag should fail loudly so a misconfigured
    # dispatcher is caught on the first task instead of silently using
    # the wrong grader).
    parser.add_argument("--supervisor-provider", required=True)
    parser.add_argument("--supervisor-model", required=True)
    parser.add_argument("--user-simulator-provider", required=True, dest="user_simulator_provider")
    parser.add_argument("--user-simulator-model", required=True, dest="user_simulator_model")
    # Round 18: optional key-pool LABEL chosen by the dispatcher (e.g. "primary"
    # / "aux1").  Resolved to a real key locally below; absent for non-pooled
    # models, so this stays backward-compatible.
    parser.add_argument("--model-key", default=None, dest="model_key",
                        help="executor key-pool label (resolved to a real key on this worker)")
    parser.add_argument(
        "--cleanup-days", type=int, default=14,
        help="prune abandoned p*-* attempt dirs older than N days at startup "
             "(0 disables; default 14)"
    )
    args = parser.parse_args()

    # GC abandoned local attempt dirs from previous crashed runs.  This
    # is a per-invocation sweep; it costs ~1 stat per attempt dir under
    # $repo/runs/ so it stays cheap even on a long-lived worker host.
    n_gc = _gc_stale_local_attempts(args.repo / "runs", args.cleanup_days)
    if n_gc:
        print(f"[worker] gc: removed {n_gc} stale attempt dir(s) older than {args.cleanup_days}d", file=sys.stderr)
    # Round 12: also prune docker resources >14d.  Cheap (no-op if
    # nothing to clean); runs at the start so it never blocks the new
    # task's container.
    _gc_stale_docker_resources()

    host_tag = args.host_tag or _hostname_tag()
    attempt_id = f"{host_tag}-{uuid.uuid4().hex[:6]}"

    task_yaml = args.repo / "tasks" / args.suite / f"{args.task}.yaml"
    if not task_yaml.exists():
        print(f"[worker] task yaml missing: {task_yaml}", file=sys.stderr)
        return 2

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    # Round 18: resolve the dispatcher-chosen key-pool LABEL to a real key and
    # inject it as the executor provider's env var, so run_eval's normal ${ENV}
    # expansion (nanobot + openclaw) yields the pooled key.  Fails safe to the
    # provider's default key on any miss.  The secret is materialized here, on
    # the worker — never on a command line.
    key_override: dict[str, str] = {}
    if getattr(args, "model_key", None) and _key_pool is not None:
        try:
            key_override = _key_pool.resolve_pool_env_override(
                args.repo / "configs" / "models.local.json",
                args.repo / "configs" / "api.local.env",
                args.model_dir,
                args.model_key,
                str(args.model_full).split("/", 1)[0],
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] key-pool resolve failed ({exc}); using provider default key", file=sys.stderr)
        # Log the env-var NAME + label only, never the key value.
        print(
            f"[worker] key-pool {args.model_dir} label={args.model_key} -> "
            + (f"override {next(iter(key_override))}" if key_override else "unresolved; provider default"),
            file=sys.stderr,
        )
    t0 = time.time()
    rc, run_stdout, run_stderr = _run_one(
        repo=args.repo,
        task_yaml=task_yaml,
        image=args.image,
        backend=args.backend,
        model_full=args.model_full,
        supervisor_provider=args.supervisor_provider,
        supervisor_model=args.supervisor_model,
        user_simulator_provider=args.user_simulator_provider,
        user_simulator_model=args.user_simulator_model,
        timeout_sec=args.timeout,
        extra_env={**key_override, "CLAWBENCH_HOST_TAG": host_tag, "CLAWBENCH_ATTEMPT_ID": attempt_id},
    )
    duration = int(time.time() - t0)

    runs_root = args.repo / "runs"
    # run_eval/run_task writes the attempt dir under the shared canonical
    # model_slug.  Locate it there; the controller rsync target should match
    # when the orchestra config was validated against the same function.
    local_model_dir = _model_slug(args.model_full)
    attempt_dir = _find_attempt_dir(
        runs_root, args.backend, local_model_dir, args.suite, args.task,
        min_mtime=t0,
    )

    # Catastrophic early failure case: run_eval blew up before
    # ``stage_dir_name`` ever created a p<n>-* directory.  Manufacture one
    # so the captured stdout/stderr still travel back to the controller.
    if attempt_dir is None:
        task_dir = runs_root / args.backend / local_model_dir / args.suite / args.task
        task_dir.mkdir(parents=True, exist_ok=True)
        attempt_dir = task_dir / f"p1-{host_tag}-{uuid.uuid4().hex[:6]}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "WORKER_RUNNER_NO_ATTEMPT_DIR").write_text(
            "run_eval.py exited before any stage directory was created.\n"
            "See worker_runner_stderr.log for the captured failure output.\n",
            encoding="utf-8",
        )

    # Persist the run_eval log so failures are debuggable from the controller.
    try:
        (attempt_dir / "worker_runner_stdout.log").write_text(run_stdout, encoding="utf-8")
        (attempt_dir / "worker_runner_stderr.log").write_text(run_stderr, encoding="utf-8")
    except OSError as exc:  # noqa: BLE001
        print(f"[worker] could not write runner logs: {exc}", file=sys.stderr)

    # run_eval writes summary.json at the task level (one per repo run).  In
    # the orchestra layout each worker only contributes one attempt and we
    # want every attempt to carry its own summary so refresh_summary on the controller
    # can rebuild the rolled-up view from the p*-* siblings.
    attempt_summary_path = attempt_dir / "summary.json"
    task_dir = runs_root / args.backend / local_model_dir / args.suite / args.task
    task_summary_path = task_dir / "summary.json"
    if task_summary_path.exists() and not attempt_summary_path.exists():
        try:
            shutil.copy2(task_summary_path, attempt_summary_path)
        except OSError as exc:
            print(f"[worker] could not copy task summary into attempt: {exc}", file=sys.stderr)

    # Compute a raw operations-layer status, then normalize at the boundary
    # so the DONE payload never carries non-domain strings.  Round-6 Phase 2
    # routes everything through lib.status.normalize_final_status:
    #   - no_summary / broken_json → missing
    #   - FAIL_rc=<rc>             → executor_incomplete
    #   - valid finalStatus from summary.json → unchanged (passthrough)
    raw_status = "no_summary"
    if attempt_summary_path.exists():
        try:
            d = json.loads(attempt_summary_path.read_text(encoding="utf-8"))
            raw_status = (d.get("finalStatus") or d.get("final_status") or "missing").lower()
        except Exception:
            raw_status = "broken_json"
    elif rc != 0:
        raw_status = f"FAIL_rc={rc}"

    # Round-7/Round-20: a run_eval watchdog (os._exit(124)) or a SIGKILL that
    # fires AFTER the placeholder summary.json (finalStatus=running) was written
    # but BEFORE orchestration advanced it leaves a STALE non-terminal 'running'
    # on disk, while rc carries the real signal.  Without this, the dispatcher
    # reads 'running' as a brand-new in-flight attempt and re-dispatches forever.
    # Terminalize via _terminalize_stale_nonterminal: rc==124 is the run_eval
    # watchdog killing a WEDGED eval process (hung supervisor/grader, etc.) ->
    # executor_incomplete (bounded rerun), NOT global_timeout — the executor did
    # not exceed its OWN budget; global_timeout is reserved for the in-loop
    # cumulative executor-budget terminal, which writes its own summary.json and
    # never reaches here.  Also rewrite the on-disk summary.json so the controller's
    # refresh_summary rollup reflects the real terminal (keeping the watchdog
    # reason marker so the mislabel migration / audits can still find these).
    if raw_status in ("running", "missing") and rc not in (0, None):
        raw_status = _terminalize_stale_nonterminal(raw_status, rc)
        if rc == 124 and attempt_summary_path.exists():
            try:
                _d = json.loads(attempt_summary_path.read_text(encoding="utf-8"))
                if (_d.get("finalStatus") or "").lower() in ("running", "missing", ""):
                    _d["finalStatus"] = _normalize_final_status(raw_status, rc=rc)
                    _d["finalStatusReason"] = "run_eval-watchdog-rc124"
                    attempt_summary_path.write_text(
                        json.dumps(_d, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
            except Exception as _exc:
                print(f"[worker] could not terminalize stale running summary: {_exc}",
                      file=sys.stderr)

    status = _normalize_final_status(raw_status, rc=rc)

    transferred = False
    transferred_reason = "no_attempt_dir"
    if attempt_dir is not None:
        transferred, transferred_reason = _rsync_to_controller(
            attempt_dir,
            args.controller_ssh,
            args.controller_runs_dir,
            {
                "backend": args.backend,
                "model_dir": args.model_dir,
                "suite": args.suite,
                "task": args.task,
            },
            lightweight=getattr(args, "lightweight_sync", False),
        )

    payload = {
        "backend": args.backend,
        "model_dir": args.model_dir,
        "suite": args.suite,
        "task": args.task,
        "host_tag": host_tag,
        "attempt_id": attempt_id,
        "attempt_dir": str(attempt_dir) if attempt_dir else None,
        "model_key": getattr(args, "model_key", None),
        "status": status,
        "rc": rc,
        "duration_sec": duration,
        "started_at": started_at,
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "transferred": transferred,
        "transferred_reason": transferred_reason,
    }
    _report_done(args.controller_ssh, args.controller_done_path, payload)

    # Clean up local attempt to free worker disk — only if rsync
    # succeeded.  When rsync fails the dir stays for the periodic GC
    # sweep (or human investigation); deleting it here would orphan the
    # only copy of a possibly-debuggable failed attempt.
    if transferred and attempt_dir is not None and attempt_dir.is_dir():
        try:
            shutil.rmtree(attempt_dir)
        except OSError:
            pass

    # Round 12 follow-up: hold SSH return until any container we
    # started has actually died, so the dispatcher doesn't release the
    # slot prematurely.  Without this, the over-spawn cascade kicks in
    # at high parallelism. This adds
    # ~0 ms on the happy path (containers are usually gone by the time
    # ``run_eval``'s finally returns) and bounded ~20s on crash paths.
    _wait_for_containers_gone(args.task)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
