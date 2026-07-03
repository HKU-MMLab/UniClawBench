"""Executor-liveness decision logic for the in-container agent monitor.

This module is the single source of truth for "is the executor still alive, or
has it stalled?".  It is deliberately:

  * stdlib-only (no imports at all),
  * free of ``from __future__`` / PEP-604 annotations,

so that ``lib.runner.agents.run_monitored_agent`` can read this file's source
verbatim and inject it into the ``docker exec`` heredoc that runs *inside* the
task container (which has no access to the repo).  The SAME ``decide`` /
``run_monitor`` then run host-side under unit test and in-container in
production — no duplicated logic to drift.

Background (the bug this fixes): the original monitor only had a one-shot
*startup-silence* guard.  It snapshotted file sizes once at launch and asked
"has anything grown since launch?".  After the agent wrote its first byte the
answer was permanently "yes", so a dead-but-not-exited agent (process wedged
into a stuck parent, ``agent_procs=0`` inside the container, no file writes for
minutes) was never detected — the monitor idled until the per-turn deadline and
the dispatch slot stayed frozen.  ``decide`` adds a *rolling* inactivity
watchdog: terminate fast once no progress has been observed for ``stall_timeout``
at ANY point in the run, not just during startup.
"""


# Force-exit codes the monitor uses.  Surfaced downstream as
# ``meta.agentExitCode`` and (when no summary.json is produced) normalised by
# worker_runner's ``FAIL_rc=<rc> -> executor_incomplete`` path.  Distinct codes
# let logs tell WHY a turn ended:
#   124 - hit the hard per-turn wall-clock deadline (conventional timeout code)
#   245 - produced no output at all within the startup-silence window
#   246 - was making progress, then went silent for the rolling stall window
#         (the dead-but-not-exited-agent case)
#   247 - made *file* progress (agent.log / results / transcript bytes grew)
#         but produced no new SEMANTIC progress (no new assistant reply / no
#         new toolUse / toolResult in the transcript) for the whole
#         ``semantic_stall_timeout`` window.  This is the dead-but-writing
#         agent: openclaw keeps re-injecting runtime-context ``user`` lines,
#         or pdftocairo / screenshots / ``process poll`` keep touching files,
#         so the byte-level stall guard never fires — but the model has stopped
#         actually doing anything.  Opt-in (default disabled) because it is the
#         stricter signal; see ``lib/runner/agents.py`` for the env gate.
REASON_EXIT_CODES = {
    "deadline": 124,
    "startup-silence": 245,
    "stall": 246,
    "semantic-stall": 247,
}


def decide(
    now,
    started_at,
    last_progress_ts,
    ever_progressed,
    deadline,
    startup_silence_timeout,
    stall_timeout,
    last_semantic_ts=None,
    ever_semantic=False,
    semantic_stall_timeout=0,
):
    """Decide whether to keep waiting or force-terminate the agent.

    Pure: every input (including the clock value) is passed in, so callers and
    tests fully control time and observed progress.  Returns a reason string
    (a key of ``REASON_EXIT_CODES``) when the agent should be terminated, or
    ``""`` to keep waiting.

    Semantic-stall (opt-in, default-inert)
    --------------------------------------
    ``last_semantic_ts`` / ``ever_semantic`` / ``semantic_stall_timeout`` add a
    second, *stricter* inactivity dimension on top of the byte-level one above.
    "Semantic progress" = a new assistant reply or a new tool call/result in the
    transcript (see ``agents.semantic_progress``), NOT raw byte growth.  It only
    ever participates when ``semantic_stall_timeout > 0`` (the operator opted
    in), and it is deliberately AND-gated with the byte-level stall: a run is
    killed for ``semantic-stall`` ONLY when it ALSO looks file-stalled-or-quiet,
    so a task that is still streaming bytes for a legitimate slow turn is never
    cut on the semantic signal alone.  Default args keep every existing caller
    (and the whole non-opted-in fleet) behaving exactly as before.
    """
    # The hard wall-clock cap always wins.
    if now >= deadline:
        return "deadline"
    # Never produced any output within the startup window.
    if (
        startup_silence_timeout > 0
        and not ever_progressed
        and now - started_at >= startup_silence_timeout
    ):
        return "startup-silence"
    # Produced output earlier, then went silent for the whole stall window.
    # Gated on ever_progressed so the never-started case is handled by the
    # (shorter) startup-silence guard above rather than waiting a full
    # stall_timeout.
    byte_stalled = (
        stall_timeout > 0
        and ever_progressed
        and now - last_progress_ts >= stall_timeout
    )
    if byte_stalled:
        return "stall"
    # Semantic stall (opt-in): the model showed real semantic activity earlier,
    # then stopped producing new assistant replies / tool calls for the whole
    # semantic window, EVEN THOUGH bytes may still be growing (re-injected
    # runtime-context, screenshot/pdf side-effects).  Gated on ``ever_semantic``
    # so a run that never reached the semantic layer is left to the byte-level
    # guards.  Fires only after the (shorter) startup window has passed so it
    # never pre-empts startup-silence.
    if (
        semantic_stall_timeout > 0
        and ever_semantic
        and last_semantic_ts is not None
        and now - started_at >= startup_silence_timeout
        and now - last_semantic_ts >= semantic_stall_timeout
    ):
        return "semantic-stall"
    return ""


def run_monitor(
    poll,
    observed_progress,
    terminate,
    now,
    sleep,
    started_at,
    deadline,
    startup_silence_timeout,
    stall_timeout,
    poll_interval=2.0,
    semantic_progress=None,
    semantic_stall_timeout=0,
):
    """Run the liveness loop until the agent exits or must be terminated.

    Dependency-injected so it can be unit-tested host-side and inlined into the
    in-container heredoc with real implementations:

      poll()              -> None while the agent process is alive, else its
                             integer exit code.
      observed_progress() -> True if any progress signal (agent.log / results /
                             transcript) has grown since the last call.  MUST be
                             rolling (refresh its own baselines), so a healthy
                             streaming agent keeps resetting the stall clock.
      terminate(reason)   -> force-kill the agent's process tree; return the
                             underlying process exit code if known, else None.
      now() / sleep(dt)   -> clock (injectable for tests).
      semantic_progress() -> Optional, opt-in. True when NEW semantic activity
                             (a new assistant reply / new tool call / new tool
                             result in the transcript) has appeared since the
                             last call.  MUST be rolling like observed_progress.
                             ``None`` (the default) disables the whole semantic
                             dimension, so existing callers are unchanged.
      semantic_stall_timeout -> seconds of no-new-semantic-activity that trips a
                             ``semantic-stall`` termination.  0 disables (default).

    Returns the integer exit code to propagate from the monitor.
    """
    last_progress_ts = started_at
    ever_progressed = False
    semantic_enabled = semantic_progress is not None and semantic_stall_timeout > 0
    last_semantic_ts = started_at
    ever_semantic = False
    while True:
        code = poll()
        if code is not None:
            return code
        t = now()
        if observed_progress():
            ever_progressed = True
            last_progress_ts = t
        if semantic_enabled:
            try:
                semantic_hit = bool(semantic_progress())
            except Exception:
                # A transcript-parse failure must never escalate to killing a
                # live agent: treat it as "can't tell" and let the byte-level
                # guards own liveness for this tick.
                semantic_hit = True
            if semantic_hit:
                ever_semantic = True
                last_semantic_ts = t
        reason = decide(
            now=t,
            started_at=started_at,
            last_progress_ts=last_progress_ts,
            ever_progressed=ever_progressed,
            deadline=deadline,
            startup_silence_timeout=startup_silence_timeout,
            stall_timeout=stall_timeout,
            last_semantic_ts=last_semantic_ts if semantic_enabled else None,
            ever_semantic=ever_semantic if semantic_enabled else False,
            semantic_stall_timeout=semantic_stall_timeout if semantic_enabled else 0,
        )
        if reason:
            forced = terminate(reason)
            return forced if forced is not None else REASON_EXIT_CODES[reason]
        sleep(poll_interval)
