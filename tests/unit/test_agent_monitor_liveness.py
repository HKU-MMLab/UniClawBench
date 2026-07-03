"""Executor-liveness monitor (lib/runner/agent_monitor.py).

These tests pin the rolling-stall behaviour that was missing from the
in-container monitor: before this fix, ``observed_progress()`` compared file
sizes against a snapshot captured ONCE at startup, so the 180s startup-silence
guard was satisfied permanently after the agent wrote its first byte.  A dead-
but-not-exited agent (the executor process inside the container dies / wedges
into a stuck parent while the host ``docker exec`` keeps waiting) therefore
idled until the per-turn deadline (<=1200s) and any downstream hang only died
at the run_eval watchdog (3600s) — freezing the dispatch slot.

The fix adds a *rolling* inactivity watchdog: track the last time progress was
observed and fail fast once no progress has occurred for ``stall_timeout``,
*at any point in the run*, not just during startup.
"""
from __future__ import annotations

from lib.runner import agent_monitor as M


# ── pure decision function ────────────────────────────────────────────────


def test_decide_keeps_waiting_while_within_stall_window():
    # Progressed recently; only 100s of silence < 600s stall window → keep going.
    reason = M.decide(
        now=2000.0,
        started_at=1000.0,
        last_progress_ts=1900.0,
        ever_progressed=True,
        deadline=1000.0 + 1200.0,
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )
    assert reason == ""


def test_decide_returns_stall_when_progressed_then_silent():
    # The dead-agent-but-runner-alive case: produced output earlier, then went
    # silent for the whole stall window. Must fail fast with "stall".
    reason = M.decide(
        now=2500.0,
        started_at=1000.0,
        last_progress_ts=1900.0,  # 600s of silence
        ever_progressed=True,
        deadline=1000.0 + 1200.0 + 10_000.0,  # nowhere near the wall-clock cap
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )
    assert reason == "stall"


def test_decide_startup_silence_when_never_progressed():
    # Never produced any output within the startup window → "startup-silence",
    # NOT "stall" (stall only applies after the agent has shown it can run).
    reason = M.decide(
        now=1000.0 + 181.0,
        started_at=1000.0,
        last_progress_ts=1000.0,
        ever_progressed=False,
        deadline=1000.0 + 1200.0,
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )
    assert reason == "startup-silence"


def test_decide_no_stall_while_continuously_progressing():
    # last_progress_ts tracks "now" each tick → silence is ~0 → never stalls.
    reason = M.decide(
        now=5000.0,
        started_at=1000.0,
        last_progress_ts=5000.0,
        ever_progressed=True,
        deadline=1000.0 + 1200.0 + 100_000.0,
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )
    assert reason == ""


def test_decide_deadline_takes_precedence_over_stall():
    # At/after the hard wall-clock deadline the reason is always "deadline".
    reason = M.decide(
        now=1000.0 + 1200.0,
        started_at=1000.0,
        last_progress_ts=1000.0,
        ever_progressed=True,
        deadline=1000.0 + 1200.0,
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )
    assert reason == "deadline"


def test_reason_exit_codes_are_distinct():
    codes = M.REASON_EXIT_CODES
    assert codes["deadline"] == 124
    assert codes["startup-silence"] == 245
    assert codes["stall"] == 246
    assert codes["semantic-stall"] == 247
    assert len(set(codes.values())) == len(codes)


# ── monitor loop (dependency-injected so we control clock + progress) ──────


class _FakeClock:
    def __init__(self, start: float = 1000.0):
        self.t = start

    def now(self) -> float:
        return self.t

    def sleep(self, dt: float) -> None:
        self.t += dt


def test_run_monitor_dead_agent_but_runner_alive_fails_fast_with_stall():
    """Reproduction: agent process produces output for a while, then dies/wedges
    (poll never returns — the host docker exec keeps waiting), and no further
    progress is ever observed. The monitor MUST force-terminate with the stall
    exit code instead of idling until the per-turn deadline."""
    clock = _FakeClock(start=1000.0)
    started_at = clock.now()

    progress_calls = {"n": 0}

    def observed_progress() -> bool:
        # Agent writes output for the first 3 polls (~real startup work), then
        # the process is dead and nothing ever grows again.
        progress_calls["n"] += 1
        return progress_calls["n"] <= 3

    terminated: list[str] = []

    def terminate(reason: str):
        terminated.append(reason)
        return None  # no underlying proc exit code; fall back to reason code

    exit_code = M.run_monitor(
        poll=lambda: None,  # the host process never exits on its own
        observed_progress=observed_progress,
        terminate=terminate,
        now=clock.now,
        sleep=clock.sleep,
        started_at=started_at,
        deadline=started_at + 1200.0,  # per-turn budget
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )

    assert terminated == ["stall"]
    assert exit_code == M.REASON_EXIT_CODES["stall"]
    # It fired ~stall_timeout after the LAST observed progress, well before the
    # 1200s per-turn deadline would have fired.  The loop reads now() *before*
    # sleeping, so the 3rd (last) progress observation lands at
    # started_at + 2*poll_interval = 1004.0.
    last_progress_at = started_at + 2 * 2.0
    assert clock.now() < started_at + 1200.0
    assert last_progress_at + 600.0 <= clock.now() < last_progress_at + 600.0 + 2.0


def test_run_monitor_returns_clean_exit_code_without_terminating():
    """When the agent process exits on its own, return its code and never kill."""
    clock = _FakeClock()
    polls = iter([None, None, 0])  # alive, alive, then exited rc=0

    terminated: list[str] = []

    exit_code = M.run_monitor(
        poll=lambda: next(polls),
        observed_progress=lambda: True,
        terminate=lambda reason: terminated.append(reason),
        now=clock.now,
        sleep=clock.sleep,
        started_at=clock.now(),
        deadline=clock.now() + 1200.0,
        startup_silence_timeout=180.0,
        stall_timeout=600.0,
    )

    assert exit_code == 0
    assert terminated == []


def test_run_monitor_healthy_progress_runs_to_deadline_not_stall():
    """A continuously-progressing (healthy but slow) agent must never be killed
    for a stall — only the hard deadline ends it."""
    clock = _FakeClock(start=1000.0)
    started_at = clock.now()
    terminated: list[str] = []

    exit_code = M.run_monitor(
        poll=lambda: None,
        observed_progress=lambda: True,  # always making progress
        terminate=lambda reason: (terminated.append(reason), None)[1],
        now=clock.now,
        sleep=clock.sleep,
        started_at=started_at,
        deadline=started_at + 600.0,  # short deadline so the test is quick
        startup_silence_timeout=180.0,
        stall_timeout=300.0,
    )

    assert terminated == ["deadline"]
    assert exit_code == M.REASON_EXIT_CODES["deadline"]
