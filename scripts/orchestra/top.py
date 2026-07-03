"""Cursor-positioned terminal monitor for the orchestra cluster.

Refreshes every second by default.  Layout (left to right, top to bottom):

  1. Per-worker row: in-flight, executed, pass, completed, incomplete, pending,
     oldest in-flight runtime, CPU%, MEM%, free disk
  2. Cluster TOTAL row + progress bar
  3. Priority remaining table (one row per bucket)
  4. Status breakdown per worker (pass / fail / BE / GT / colored rate_limit /
     infra_error / executor_incomplete)
  5. Active models across cluster — provider → model two-level tree
  6. Recent failures (newest 5, across all workers)

Color choices (no dim greys — every signal needs to pop):
  rate_limit          → yellow  (33)
  infra_error         → red     (31)
  executor_incomplete → magenta (35)
  pass / completed    → green   (32)
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import config as cfg_mod

# Inject the repo root so we can import the lib.status single-source-of-truth.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.status import TERMINAL_RESULT_STATUSES, normalize_final_status  # noqa: E402

# Synthetic priority bucket ids appended by ``stats.recompute_priorities``
# but NOT present in ``cfg.priorities``.  Round 16 / P1-5: the renderer
# must iterate ``priorities`` itself instead of ``zip(cfg.priorities,
# priorities)`` so these buckets show up too.
SYNTHETIC_BUCKET_IDS = {"P100_session_exhausted", "P200_suspended"}

# --------------------------------------------------------------------------
# ANSI helpers
# --------------------------------------------------------------------------
RESET = "\033[0m"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
CLR_LINE = "\033[K"
CLR_SCREEN = "\033[2J\033[H"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
BOLD = "\033[1m"


def _color(s: str, code: str) -> str:
    return f"{code}{s}{RESET}"


def _go(row: int, col: int = 1) -> str:
    return f"\033[{row};{col}H{CLR_LINE}"


# --------------------------------------------------------------------------
# Probes
# --------------------------------------------------------------------------
@dataclass
class WorkerSnapshot:
    name: str
    reachable: bool
    inflight: int = 0
    cpu_pct: float = 0.0
    mem_pct: float = 0.0
    disk_free_gib: int = 0
    active_models: list[str] | None = None  # full provider/model strings
    oldest_etime: str = ""


def _ssh_run(host: str, cmd: str, timeout: int = 8) -> tuple[int, str]:
    proc = subprocess.run(
        ["ssh", "-o", f"ConnectTimeout={timeout}", "-o", "BatchMode=yes", host, cmd],
        capture_output=True,
        text=True,
        timeout=timeout + 4,
    )
    return proc.returncode, proc.stdout


def probe_worker(host: str) -> WorkerSnapshot:
    cmd = r"""
INFL=$(pgrep -cf '[s]cripts/run_eval.py' 2>/dev/null || echo 0)
LOAD=$(uptime | sed -nE 's/.*load average: ([0-9.]+).*/\1/p')
NCPU=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
MEM=$(free -m 2>/dev/null | awk '/^Mem:/{printf("%.0f", $3*100/$2)}')
DISK=$(df -BG / 2>/dev/null | awk 'NR==2{gsub("G","",$4);print $4}')
MODELS=$(ps -eo args 2>/dev/null | grep '[s]cripts/run_eval.py' | grep -v grep | sed -nE 's|.*--model ([^ ]+).*|\1|p' | sort | uniq -c | awk '{print $2"x"$1}' | tr '\n' ' ')
OLDEST=$(ps -eo etime,args 2>/dev/null | grep '[s]cripts/run_eval.py' | grep -v grep | sort | head -1 | awk '{print $1}')
echo "INFL=$INFL LOAD=$LOAD NCPU=$NCPU MEM=$MEM DISK=$DISK OLDEST=$OLDEST"
echo "MODELS=$MODELS"
"""
    # Presentation-only reachability: a single ConnectTimeout=6 probe with 0
    # retries paints a host RED the instant it blips (a WSL worker under load
    # or mid-reboot routinely misses one probe while perfectly healthy).
    # Require TWO consecutive failures (1 retry) and a longer 12s timeout
    # before declaring the worker down.  Pure display layer -- no dispatch /
    # correctness impact.
    rc, out = -1, ""
    for _attempt in range(2):
        try:
            rc, out = _ssh_run(host, cmd, timeout=12)
        except subprocess.TimeoutExpired:
            rc, out = -1, ""
        if rc == 0:
            break
    if rc != 0:
        return WorkerSnapshot(name=host, reachable=False)
    snap = WorkerSnapshot(name=host, reachable=True)
    for line in out.splitlines():
        if line.startswith("INFL="):
            for kv in line.split():
                k, _, v = kv.partition("=")
                if k == "INFL":
                    snap.inflight = int(v or 0)
                elif k == "LOAD":
                    try:
                        load = float(v or 0)
                    except ValueError:
                        load = 0
                    # scale below
                    snap.cpu_pct = load
                elif k == "NCPU":
                    try:
                        ncpu = max(1, int(v or 1))
                    except ValueError:
                        ncpu = 1
                    snap.cpu_pct = (snap.cpu_pct / ncpu) * 100.0
                elif k == "MEM":
                    snap.mem_pct = float(v or 0)
                elif k == "DISK":
                    snap.disk_free_gib = int(v or 0)
                elif k == "OLDEST":
                    snap.oldest_etime = v or ""
        elif line.startswith("MODELS="):
            payload = line[len("MODELS="):].strip()
            snap.active_models = [t for t in payload.split() if t]
    return snap


# --------------------------------------------------------------------------
# Aggregations
# --------------------------------------------------------------------------
@dataclass
class WorkerProgress:
    queue_total: int = 0
    done: int = 0
    pass_: int = 0
    completed: int = 0  # passed/fail/BE/GT
    incomplete: int = 0
    fails: list[dict] | None = None
    status_counts: collections.Counter | None = None


# Round-6: source TERMINAL from lib.status single source of truth.
TERMINAL = TERMINAL_RESULT_STATUSES


def read_runtime_progress(runtime_dir: Path, controller_done_lines: int = 0) -> dict[str, WorkerProgress]:
    """Reconstruct per-worker progress from done.jsonl archive history.

    Round-4 Phase 3.4 (commit e9b6a69b) changed the on-disk format from
    a single appendable ``done_history.jsonl`` file to a rotated
    directory ``done_history/`` where each drain pass writes
    ``done_<utc-ts>.jsonl``.  Round-5 Phase 5 adapts this reader: it
    iterates every archive file in the directory, falling back to the
    legacy single file when present (back-compat).  Before this fix
    ``top`` showed all stats as 0 because the legacy file was absent.
    """
    out: dict[str, WorkerProgress] = collections.defaultdict(WorkerProgress)
    archive_dir = runtime_dir / "done_history"
    legacy_file = runtime_dir / "done_history.jsonl"

    if archive_dir.is_dir():
        archives = sorted(archive_dir.glob("done_*.jsonl"))
    elif legacy_file.exists():
        archives = [legacy_file]
    else:
        return out

    for archive in archives:
        try:
            text = archive.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            host = d.get("host_tag") or "?"
            prog = out[host]
            prog.done += 1
            # Round 16 / P2-1: route raw done-history status through
            # normalize_final_status so legacy strings (``no_summary``,
            # ``FAIL_rc=137``, pre-Round-6 ``continue`` / ``stopped``) map
            # to canonical FINAL_STATUS_ORDER values and the per-worker
            # throughput view stops fragmenting on equivalent terms.
            st = normalize_final_status(d.get("status") or "", rc=d.get("rc"))
            if prog.status_counts is None:
                prog.status_counts = collections.Counter()
            prog.status_counts[st] += 1
            if st == "pass":
                prog.pass_ += 1
            if st in TERMINAL:
                prog.completed += 1
            else:
                prog.incomplete += 1
                if prog.fails is None:
                    prog.fails = []
                prog.fails.append(d)
    return out


# --------------------------------------------------------------------------
# Round 16 / P1-4: canonical unique-task view (one row per task key)
# --------------------------------------------------------------------------
@dataclass
class UniqueTaskView:
    """A point-in-time best-status snapshot keyed by task identity.

    ``read_runtime_progress`` counts every DONE callback line (one per
    attempt, including retries).  This view collapses to one row per
    canonical ``(backend, model_dir, suite, task)`` key, surfacing the
    BEST current status per the rolled-up ``summary.json`` — so the
    operator can see "how many of the 80 tasks have a terminal result?"
    instead of "how many DONE callbacks have we logged?".
    """
    by_key: dict[tuple[str, str, str, str], str]
    status_counts: collections.Counter
    total: int
    completed: int
    pending: int


def compute_unique_task_view(runs_root: Path) -> UniqueTaskView:
    """Read ``runs_root/.runs_index.json`` (or fall back to a full
    ``summary.json`` walk) and return a status snapshot keyed on the
    canonical 4-tuple.

    All statuses are routed through ``normalize_final_status`` so legacy
    values (``no_summary``, ``broken_json``, pre-Round-6 ``FAIL_rc=N``)
    collapse to the canonical vocabulary.
    """
    by_key: dict[tuple[str, str, str, str], str] = {}
    status_counts: collections.Counter = collections.Counter()
    index_file = runs_root / ".runs_index.json"
    rows: list[dict] = []
    if index_file.exists():
        try:
            payload = json.loads(index_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                rows = list(payload.get("rows") or [])
        except (OSError, json.JSONDecodeError):
            rows = []
    if not rows and runs_root.is_dir():
        # Fallback: walk the runs tree for summary.json files.  Slower
        # but covers the case where the dispatcher hasn't refreshed the
        # index yet.
        for sj in runs_root.rglob("summary.json"):
            try:
                rel = sj.relative_to(runs_root)
            except ValueError:
                continue
            parts = rel.parts
            if len(parts) != 5 or parts[-1] != "summary.json":
                # Expected layout: <backend>/<model_dir>/<suite>/<task>/summary.json
                continue
            try:
                payload = json.loads(sj.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rows.append(
                {
                    "summaryPath": "/".join(parts[:-1]),
                    "finalStatus": payload.get("finalStatus")
                    or payload.get("final_status"),
                }
            )

    for row in rows:
        path = row.get("summaryPath") or ""
        parts = path.split("/")
        if len(parts) != 4:
            continue
        key = (parts[0], parts[1], parts[2], parts[3])
        status = normalize_final_status(row.get("finalStatus") or "missing")
        by_key[key] = status

    for st in by_key.values():
        status_counts[st] += 1

    total = len(by_key)
    completed = sum(1 for st in by_key.values() if st in TERMINAL_RESULT_STATUSES)
    pending = total - completed
    return UniqueTaskView(
        by_key=by_key,
        status_counts=status_counts,
        total=total,
        completed=completed,
        pending=pending,
    )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def _load_done_entries(runtime_dir: Path) -> list[dict]:
    """Read every row from done_history/ + legacy done_history.jsonl.

    Returns a flat list of dict entries (with ``backend`` / ``model_dir`` /
    ``status`` / ``suite`` / ``task`` keys).  Used by render() to count
    finished tasks per priority bucket — see comment near the
    ``Priorities (remaining | finished)`` block."""
    out: list[dict] = []
    archive_dir = runtime_dir / "done_history"
    legacy_file = runtime_dir / "done_history.jsonl"
    if archive_dir.is_dir():
        archives = sorted(archive_dir.glob("done_*.jsonl"))
    elif legacy_file.exists():
        archives = [legacy_file]
    else:
        return out
    for archive in archives:
        try:
            text = archive.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            out.append(d)
    return out


def read_throughput(
    dispatch_log: Path, tail_bytes: int = 400_000
) -> tuple[int, float | None, float | None, float | None]:
    """Parse the dispatcher's ``TOTAL N`` progress lines from the tail of
    ``dispatch.log`` -> (remaining, net/h over 90min, net/h over 30min,
    ETA-hours).

    ``net/h`` is how fast ``TOTAL`` (remaining unique tasks) DRAINS, not the
    raw DONE rate -- it nets out re-queued churn (rate_limit / retries) so it
    reflects true progress.  Only the file tail is read so this stays cheap on
    the 1s refresh even when dispatch.log is large.
    """
    try:
        size = dispatch_log.stat().st_size
        with open(dispatch_log, "rb") as f:
            if size > tail_bytes:
                f.seek(size - tail_bytes)
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return (0, None, None, None)
    pts: list[tuple[float, int]] = []
    last_ts: float | None = None
    for line in data.splitlines():
        m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", line)
        if m:
            try:
                last_ts = datetime.strptime(
                    m.group(1), "%Y-%m-%d %H:%M:%S"
                ).timestamp()
            except ValueError:
                pass
        mt = re.search(r"^\s*TOTAL\s+(\d+)\s*$", line)
        if mt and last_ts is not None:
            pts.append((last_ts, int(mt.group(1))))
    if not pts:
        return (0, None, None, None)
    total = pts[-1][1]
    now_ts = pts[-1][0]

    def rate(window_sec: int) -> float | None:
        s = [(t, v) for t, v in pts if t >= now_ts - window_sec]
        if len(s) >= 2 and s[-1][0] > s[0][0]:
            dt_h = (s[-1][0] - s[0][0]) / 3600
            drained = s[0][1] - s[-1][1]
            if dt_h > 0.05:
                return drained / dt_h
        return None

    r90, r30 = rate(5400), rate(1800)
    eta = (total / r90) if (r90 and r90 > 0) else None
    return (total, r90, r30, eta)


def render(
    cfg: cfg_mod.OrchestraConfig,
    snapshots: list[WorkerSnapshot],
    progress: dict[str, WorkerProgress],
    priorities: list[dict],
    done_entries: list[dict] | None = None,
    unique_view: UniqueTaskView | None = None,
    throughput: tuple[int, float | None, float | None, float | None] | None = None,
) -> None:
    if done_entries is None:
        done_entries = []
    if unique_view is None:
        unique_view = UniqueTaskView(
            by_key={}, status_counts=collections.Counter(),
            total=0, completed=0, pending=0,
        )
    sys.stdout.write(CLR_SCREEN + HIDE)
    row = 1

    sys.stdout.write(_go(row) + _color("==== Clawbench Orchestra Monitor ", BOLD + CYAN))
    sys.stdout.write(_color("refresh 1s  ", CYAN))
    sys.stdout.write(_color(time.strftime("%Y-%m-%d %H:%M:%S"), BOLD))
    sys.stdout.write(_color("  ====", CYAN))
    row += 2

    # Throughput headline (net drain of TOTAL remaining + ETA) parsed from
    # dispatch.log.  Answers "are we making real progress and when do we land?"
    if throughput is not None:
        total_rem, r90, r30, eta = throughput
        r90_s = str(round(r90)) if r90 else "—"
        r30_s = str(round(r30)) if r30 else "—"
        eta_s = f"{eta:.1f}h" if eta else "—"
        sys.stdout.write(
            _go(row)
            + _color(
                f"TOTAL remaining={total_rem}   net/h  90m={r90_s}  30m={r30_s}   ETA={eta_s}",
                BOLD + CYAN,
            )
        )
        row += 2

    # Per-worker last-completion age + "crash" signal: last-20 attempts each
    # finishing in <10s = an instant-fail loop. Keyed by done-history host_tag.
    lastdone_by_tag: dict[str, str] = {}
    rows_by_tag: dict[str, list[dict]] = collections.defaultdict(list)
    for d in done_entries:
        tag = d.get("host_tag") or "?"
        ea = d.get("ended_at") or ""
        if ea > lastdone_by_tag.get(tag, ""):
            lastdone_by_tag[tag] = ea
        rows_by_tag[tag].append(d)
    board_now = max(lastdone_by_tag.values()) if lastdone_by_tag else ""
    crash_by_tag: dict[str, int] = {}
    for tag, tag_rows in rows_by_tag.items():
        tag_rows.sort(key=lambda d: d.get("ended_at") or "")
        crash_by_tag[tag] = sum(
            1 for d in tag_rows[-20:] if (d.get("duration_sec") or 0) < 10
        )

    def _ago(ea: str) -> str:
        # Timezone-free relative age vs the board's newest completion.
        if not ea or not board_now:
            return "-"
        try:
            mins = (
                datetime.fromisoformat(board_now) - datetime.fromisoformat(ea)
            ).total_seconds() / 60
        except ValueError:
            return "?"
        if mins < 2:
            return "now"
        return f"{int(mins)}m" if mins < 90 else f"{mins / 60:.1f}h"

    # The in-flight column shows CLAIM(exec):
    #   * CLAIM (inflight.jsonl) = true slot occupancy.  A claim is held for the
    #     task's WHOLE lifecycle — ssh-dispatch -> run_eval[executor/user_sim/
    #     supervisor/grading] -> result rsync-back -> DONE-callback -> release —
    #     and the dispatcher gates ``worker.inflight < parallel`` on it, so it
    #     is the real "is the slot filled / dispatched full" number.
    #   * exec = pgrep(run_eval) = only the EXECUTION sub-phase.  It excludes
    #     ssh-setup, the result rsync, the DONE-callback and teardown, so it
    #     under-counts occupancy.  claim-minus-exec = tasks in those transition
    #     phases, especially on high-latency links with full-artifact sync.
    claims_by_worker: collections.Counter = collections.Counter()
    try:
        _inf = cfg_mod.runtime_dir() / "inflight.jsonl"
        for _l in _inf.read_text(encoding="utf-8").splitlines():
            _l = _l.strip()
            if _l:
                claims_by_worker[json.loads(_l).get("worker", "?")] += 1
    except Exception:
        pass

    sys.stdout.write(
        _go(row)
        + f"{'node':<5} {'claim(exec)':<12} {'done':<6} {'pass':<6} {'comp':<6} {'incomp':<7} {'cpu%':<6} {'mem%':<6} {'free':<6} {'oldest':<8} {'lastdone':<8} note"
    )
    row += 1
    cluster_inflight = 0
    cluster_done = cluster_pass = cluster_comp = cluster_incomp = 0
    for snap, w in zip(snapshots, cfg.workers):
        # Map the worker to its done-history host_tag when it differs from the
        # configured worker name.
        # so its progress / lastdone / crash counts resolve.  Was a bug: a
        # plain ``name.lower()`` lookup silently zeroed any worker whose tag
        # differs from its config name.
        tag = w.effective_host_tag
        prog = progress.get(tag, WorkerProgress())
        claimed = claims_by_worker.get(snap.name, 0)
        cluster_inflight += claimed
        cluster_done += prog.done
        cluster_pass += prog.pass_
        cluster_comp += prog.completed
        cluster_incomp += prog.incomplete
        if not snap.reachable:
            sys.stdout.write(_go(row) + f"{snap.name:<5} " + _color("(unreachable)", RED))
            row += 1
            continue
        ld = _ago(lastdone_by_tag.get(tag, ""))
        note = ""
        if ld not in ("-", "now") and ld.endswith("h"):
            note += _color("STALL ", YELLOW)
        cr = crash_by_tag.get(tag, 0)
        if cr >= 3:
            note += _color(f"crash{cr}/20", MAGENTA)
        sys.stdout.write(
            _go(row)
            + f"{snap.name:<5} {f'{claimed}/{w.parallel}({snap.inflight})':<12} "
            f"{prog.done:<6} {_color(f'{prog.pass_:<6}', GREEN)} "
            f"{prog.completed:<6} {_color(f'{prog.incomplete:<7}', YELLOW)} "
            f"{snap.cpu_pct:<6.0f} {snap.mem_pct:<6.0f} {f'{snap.disk_free_gib}G':<6} {snap.oldest_etime:<8} "
            f"{ld:<8} {note}"
        )
        row += 1

    sys.stdout.write(_go(row) + _color("─" * 100, CYAN))
    row += 1
    sys.stdout.write(
        _go(row)
        + f"ATTEMPT THROUGHPUT  inflight={cluster_inflight}  done={cluster_done}  "
        f"{_color(f'pass={cluster_pass}', GREEN)}  "
        f"completed={cluster_comp}  "
        f"{_color(f'incomplete={cluster_incomp}', YELLOW)}"
    )
    row += 1
    sys.stdout.write(
        _go(row) + _color("  (counts every DONE callback line; one task may appear N times)", CYAN)
    )
    row += 2

    # Round 16 / P1-4: canonical task view, one row per (backend,
    # model_dir, suite, task).  Independent of how many retries each
    # task has taken — answers "how many of the 80 tasks are done?".
    sys.stdout.write(_go(row) + _color("Tasks (unique-by-task):", BOLD))
    row += 1
    if unique_view.total:
        sys.stdout.write(
            _go(row)
            + f"  total={unique_view.total}  "
            f"{_color(f'completed={unique_view.completed}', GREEN)}  "
            f"{_color(f'pending={unique_view.pending}', YELLOW)}"
        )
        row += 1
        # Per-status breakdown, normalized.
        ordered = [
            "pass", "budget_exhausted", "fail", "global_timeout",
            "executor_incomplete", "rate_limit", "infra_error",
            "pre_exec_failed", "running", "missing",
        ]
        seen = [s for s in ordered if unique_view.status_counts.get(s)]
        seen += [s for s in unique_view.status_counts if s not in ordered]
        line = "  "
        for st in seen:
            n = unique_view.status_counts.get(st, 0)
            if not n:
                continue
            col = ""
            if st == "pass":
                col = GREEN
            elif st in ("fail", "infra_error"):
                col = RED
            elif st in ("rate_limit", "budget_exhausted"):
                col = YELLOW
            elif st in ("executor_incomplete", "global_timeout"):
                col = MAGENTA
            tag = f"{st}={n}  "
            line += _color(tag, col) if col else tag
        sys.stdout.write(_go(row) + line)
        row += 1
    else:
        sys.stdout.write(
            _go(row)
            + _color(
                "  (no .runs_index.json or summary.json files yet — view will populate as the dispatcher refreshes)",
                CYAN,
            )
        )
        row += 1
    row += 1

    # Priority bucket remaining (one row per actual bucket; iterates the
    # full priorities list so synthetic P100/P200 are visible too).
    # Round 16 / P1-5: the previous ``zip(cfg.priorities, priorities)``
    # silently dropped synthetic buckets at the end of the list.  Now we
    # iterate ``priorities`` directly and resolve labels from
    # ``cfg.priorities`` only when the bucket id matches a user-defined
    # entry.
    cfg_label_by_id = {p.id: p.label for p in cfg.priorities}
    sys.stdout.write(_go(row) + _color("Priorities (remaining tasks per bucket):", BOLD))
    row += 1
    for bucket in priorities:
        bid = bucket.get("priority_id") or "?"
        n = len(bucket.get("tasks") or [])
        label = (
            bucket.get("label")
            or cfg_label_by_id.get(bid)
            or ("synthetic" if bid in SYNTHETIC_BUCKET_IDS else "")
        )
        sys.stdout.write(
            _go(row)
            + f"  {bid:<28} remaining={n:<5}  {label}"
        )
        row += 1
    row += 1

    # Active models across cluster (provider → model: count)
    sys.stdout.write(_go(row) + _color("Active models across cluster:", BOLD))
    row += 1
    by_provider: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for snap in snapshots:
        for m in snap.active_models or []:
            # m is like "provider/model-namex3"
            spec, _, count = m.rpartition("x")
            try:
                cnt = int(count) if count.isdigit() else 1
            except ValueError:
                cnt = 1
            provider, _, model = spec.partition("/")
            by_provider[provider][model] += cnt
    for provider in sorted(by_provider):
        total = sum(by_provider[provider].values())
        sys.stdout.write(_go(row) + f"  {provider:<35} total={total}")
        row += 1
        items = by_provider[provider].most_common()
        for j, (model, cnt) in enumerate(items):
            prefix = "└─" if j == len(items) - 1 else "├─"
            sys.stdout.write(_go(row) + f"    {prefix} {model:<32} {cnt}")
            row += 1
    row += 1

    # Per-worker status breakdown (use colours for the three failure flavours)
    sys.stdout.write(_go(row) + _color("Status breakdown per worker:", BOLD))
    row += 1
    for snap, w in zip(snapshots, cfg.workers):
        prog = progress.get(w.effective_host_tag, WorkerProgress())
        if not prog.status_counts:
            sys.stdout.write(_go(row) + f"  {snap.name}: (no results yet)")
            row += 1
            continue
        s = prog.status_counts
        line = f"  {snap.name}: "
        for st in ("pass", "fail", "budget_exhausted", "global_timeout"):
            line += f"{st[:4]}={s.get(st, 0)}  "
        line += _color(f"rate_limit={s.get('rate_limit', 0)}  ", YELLOW)
        line += _color(f"infra_error={s.get('infra_error', 0)}  ", RED)
        line += _color(f"executor_incomplete={s.get('executor_incomplete', 0)}", MAGENTA)
        sys.stdout.write(_go(row) + line)
        row += 1
    row += 1

    # Per-model view: current inflight vs cap + last-40min outcome mix, sorted
    # by recent rate_limit so the 429 offenders surface.  The per-worker block above
    # is by WORKER; this answers "which MODEL is getting 429'd / timing out now".
    MODEL_WIN_SEC = 2400
    cutoff_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - MODEL_WIN_SEC))
    per_model: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for d in done_entries:
        if (d.get("ended_at") or "") < cutoff_iso:
            continue
        st = normalize_final_status(d.get("status") or "", rc=d.get("rc"))
        per_model[d.get("model_dir") or "?"][st] += 1
    inflight_by_model: collections.Counter = collections.Counter()
    try:
        inf_path = cfg_mod.runtime_dir() / "inflight.jsonl"
        for line in inf_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                inflight_by_model[json.loads(line).get("model_dir") or "?"] += 1
    except Exception:
        pass
    sys.stdout.write(_go(row) + _color("Per-model  (inflight/cap | last 40min done — sorted by 429):", BOLD))
    row += 1
    sys.stdout.write(
        _go(row)
        + f"  {'model':<42} {'in/cap':<8} {'done':<5} {'pass':<5} {'429':<5} {'g_to':<5} {'429%':<5}"
    )
    row += 1
    caps = cfg.model_caps
    keys = set(per_model) | set(inflight_by_model)

    def _mk(md: str) -> tuple[int, int]:
        return (-per_model[md].get("rate_limit", 0), -inflight_by_model.get(md, 0))

    for md in sorted(keys, key=_mk):
        c = per_model[md]
        done = sum(c.values())
        inf = inflight_by_model.get(md, 0)
        if not done and not inf:
            continue
        rl = c.get("rate_limit", 0)
        cap = caps.get(md)
        pct = f"{round(100 * rl / done)}%" if done else "-"
        incap = f"{inf}/{cap if cap is not None else '-'}"
        name = md or "?"
        line = f"  {name:<42} {incap:<8} {done:<5} "
        line += _color(f"{c.get('pass', 0):<5} ", GREEN)
        line += _color(f"{rl:<5} ", YELLOW) if rl else f"{rl:<5} "
        line += f"{c.get('global_timeout', 0):<5} {pct:<5}"
        if done and rl / done >= 0.25:
            line += _color("  <<429", YELLOW)
        sys.stdout.write(_go(row) + line)
        row += 1
    row += 1

    # Recent failures (newest 5)
    sys.stdout.write(_go(row) + _color("Recent failures (last 5 across cluster):", BOLD))
    row += 1
    pool: list[dict] = []
    for prog in progress.values():
        if prog.fails:
            pool.extend(prog.fails)
    pool.sort(key=lambda d: d.get("ended_at", ""), reverse=True)
    for d in pool[:5]:
        st = normalize_final_status(d.get("status") or "", rc=d.get("rc"))[:24]
        st_col = MAGENTA if st == "executor_incomplete" else (YELLOW if st == "rate_limit" else (RED if st == "infra_error" else ""))
        st_disp = _color(f"{st:<22}", st_col) if st_col else f"{st:<22}"
        line = f"  {d.get('ended_at', '')[-8:]:<9}  {st_disp} rc={d.get('rc', '?'):<5}  {d.get('host_tag', '?'):<3}  {d.get('suite', '?')[:8]}/{d.get('task', '?')[:50]}"
        sys.stdout.write(_go(row) + line)
        row += 1
    sys.stdout.flush()


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Clawbench orchestra top monitor")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument(
        "--tasks-root",
        type=Path,
        default=None,
        help="When set, top.py computes ``remaining`` LIVE by calling "
             "stats.recompute_priorities (without refresh) on every render, "
             "instead of trusting the dispatcher-written priorities.jsonl. "
             "Useful when the dispatcher is blocked on a long-running bucket "
             "and priorities.jsonl is stale.",
    )
    parser.add_argument(
        "--dispatch-log",
        type=Path,
        default=None,
        help="dispatcher log to parse for throughput; default is "
             "<controller.data_root>/logs/dispatch.log",
    )
    args = parser.parse_args()

    cfg = cfg_mod.load(args.config)
    runtime_dir = cfg_mod.runtime_dir()
    dispatch_log = args.dispatch_log or (cfg.controller.data_root / "logs" / "dispatch.log")

    try:
        while True:
            # Probe each worker
            snaps = []
            for w in cfg.workers:
                if w.skip:
                    snaps.append(WorkerSnapshot(name=w.name, reachable=False))
                    continue
                snap = probe_worker(w.ssh)
                snap.name = w.name
                snaps.append(snap)

            # Read priorities + progress
            priorities: list[dict] = []
            if args.tasks_root is not None:
                # Live mode: compute priorities ourselves so ``remaining``
                # updates every render, independent of the dispatcher's
                # bucket-drain cadence.  ``do_refresh=False`` keeps this
                # cheap — we trust the dispatcher to refresh task-level
                # summary.json files.
                #
                # P1-1 follow-up: read the dispatcher's session_attempts
                # snapshot so synthetic P100/P200 buckets reflect the
                # live in-memory state instead of an empty default.
                #
                # Wrap in try/except so a transient disk hiccup doesn't
                # crash the monitor.
                try:
                    from . import stats as _stats_mod
                    _session_attempts = _stats_mod.read_session_attempts_snapshot(
                        runtime_dir,
                    )
                    priorities = _stats_mod.recompute_priorities(
                        cfg, tasks_root=args.tasks_root, do_refresh=False,
                        session_attempts=_session_attempts,
                    )
                except Exception:
                    priorities = []
            if not priorities:
                prios_file = runtime_dir / "priorities.jsonl"
                if prios_file.exists():
                    for line in prios_file.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            priorities.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                else:
                    priorities = [{"priority_id": p.id, "label": p.label, "tasks": []} for p in cfg.priorities]

            progress = read_runtime_progress(runtime_dir)
            done_entries = _load_done_entries(runtime_dir)
            throughput = read_throughput(dispatch_log)
            # Round 16 / P1-4: canonical task view from the runs index.
            try:
                runs_root = cfg_mod.runs_root(cfg)
                unique_view = compute_unique_task_view(runs_root)
            except Exception:
                unique_view = None
            render(cfg, snaps, progress, priorities, done_entries, unique_view, throughput)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        sys.stdout.write(SHOW + "\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
