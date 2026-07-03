"""Single source of truth for Clawbench's attempt status model.

Three kinds of state co-exist; this module gives canonical names + sets
+ ordering + normalizers for all of them so downstream code (runtime,
synth fallback, batch stats, dispatcher, monitor) classifies the same
underlying outcome identically:

  - ``SUPERVISOR_VERDICT_STATES`` — what the supervisor model is allowed
    to say about TASK SEMANTICS: ``pass`` / ``continue`` / ``fail``.
  - ``SUPERVISOR_ATTEMPT_STATES`` — the supervisor's state-machine label
    (``in_progress`` / ``incomplete`` / ``complete_but_failed`` /
    ``complete_and_passed`` / ``terminal_failure``).
  - ``FINAL_STATUS_ORDER`` — the framework's classification of the WHOLE
    attempt once all signals are gathered.  This is the canonical superset
    that the entire system (worker_runner, orchestration, refresh_summary,
    stats, top, batch_eval) must agree on.

Prior to Round 6, each of those downstream files had its own local copies
of the status sets / ordering / classifier; a new status meant chasing
the same change through six files, and inevitably one would drift.
This module is now the single home for that vocabulary.

This module is a leaf — it must not import any other ``lib.*`` module so
that ``lib/constants.py``, dispatcher scripts, and tests can all depend
on it without cycle risk.
"""
from __future__ import annotations

import re


# ── canonical ordering for "best attempt" selection (highest = best) ──
#
# Reading from top to bottom: "pass" beats everything; an attempt with
# finalStatus=pass should be selected over one with finalStatus=fail when
# both exist for the same task.  Order is exhaustive: every status the
# framework ever writes MUST appear in this tuple, and any other label
# (legacy, ops-layer, typos) gets normalised into one of these via
# ``normalize_final_status``.
FINAL_STATUS_ORDER: tuple[str, ...] = (
    "pass",                # 0  terminal success
    "budget_exhausted",    # 1  ran through full max_user_followups; no pass
    "fail",                # 2  supervisor explicit terminal failure
    "global_timeout",      # 3  cumulative executor-runtime cap hit (not wall-clock)
    "executor_incomplete", # 4  executor never cleanly completed a turn
    "rate_limit",          # 5  upstream API refused (zero agent progress)
    "infra_error",         # 6  container / docker / supervisor infra failure
    "pre_exec_failed",     # 7  host-side pre_exec script failure (subtype of infra)
    "running",             # 8  mid-flight snapshot (no terminal classification yet)
    "missing",             # 9  no usable artifact at all
)
ALL_FINAL_STATUSES: frozenset[str] = frozenset(FINAL_STATUS_ORDER)


# ── subset categorization (used by dispatcher / monitor / rerun queue) ──

TERMINAL_RESULT_STATUSES: frozenset[str] = frozenset({
    "pass", "budget_exhausted", "fail", "global_timeout",
})
"""Statuses that represent a COMPLETED attempt — the dispatcher will NOT
schedule a re-run for these.  Anything not in this set is fair game for
re-running (subject to bucket / cap rules)."""

INFRA_STATUSES: frozenset[str] = frozenset({
    "infra_error", "pre_exec_failed", "rate_limit",
})
"""Statuses caused by host / upstream environment, not by the agent
itself.  Useful for "filter out environmental noise" stats."""

INCOMPLETE_STATUSES: frozenset[str] = frozenset({
    "executor_incomplete", "running", "missing",
})
"""Statuses where the agent didn't reach a terminal classification.
Combined with ``INFRA_STATUSES`` this is the dispatcher's rerun pool."""


# ── supervisor task-semantic enums (NARROWED in Round 6) ──
#
# Round 6 deliberately removes ``infra_error`` and ``rate_limit`` from
# the supervisor's allowed verdicts: those are framework-runtime states,
# not judgements the supervisor model is qualified to make.  The
# framework synthesises ``rate_limit`` / ``infra_error`` from upstream
# HTTP responses, container lifecycle, and supervisor-invocation errors
# (see ``lib/runner/orchestration.py:structured_rate_limit_score`` and
# ``structured_runtime_error_score``); the supervisor model only ever
# answers "is the executor's WORK any good?"

SUPERVISOR_VERDICT_STATES: frozenset[str] = frozenset({
    "pass", "continue", "fail",
})

SUPERVISOR_ATTEMPT_STATES: frozenset[str] = frozenset({
    "in_progress",
    "incomplete",
    "complete_but_failed",
    "complete_and_passed",
    "terminal_failure",
})


# Legacy values that historical score.json files may still contain. The
# normalizers below translate them into the narrowed sets.
_LEGACY_VERDICT_ALIASES: dict[str, str] = {
    "infra_error": "fail",
    "rate_limit": "fail",
}
_LEGACY_ATTEMPT_STATE_ALIASES: dict[str, str] = {
    "infra_error": "terminal_failure",
    "rate_limit": "terminal_failure",
}


# ── rank index for sorting (higher = better) ──
_RANK = {status: len(FINAL_STATUS_ORDER) - i for i, status in enumerate(FINAL_STATUS_ORDER)}


def status_rank(status: str | None) -> int:
    """Return a numeric rank for use as a sort key.  Higher = better.

    Unknown / legacy / blank statuses fall through to 0 (worst), so
    sorted([...], key=status_rank, reverse=True) reliably puts the best
    attempt first even when one of the inputs is malformed.
    """
    return _RANK.get((status or "").lower(), 0)


# ── normalizer for messy / legacy / ops-layer status strings ──

_FAIL_RC_RE = re.compile(r"^fail_rc=(-?\d+)$", re.IGNORECASE)


def normalize_final_status(value: str | None, *, rc: int | None = None) -> str:
    """Map any incoming status string to a canonical ``FINAL_STATUS_ORDER``
    member.

    Historically ``scripts/orchestra/worker_runner.py`` wrote
    operations-layer strings into DONE payloads:

      - ``"no_summary"`` when the attempt-level summary.json was absent
      - ``"broken_json"`` when summary.json failed to parse
      - ``"FAIL_rc=<rc>"`` when the agent exited non-zero AND no summary

    Those leaked into stats, monitor displays, refresh_summary's
    rollup, and the dispatcher's rerun queue — each treating them as
    custom enum members.  This function maps all such variants to a
    canonical ``FINAL_STATUS_ORDER`` member at the boundary, so
    downstream code only ever sees the 10-value vocabulary.

    Args:
        value: the raw status string (any case).
        rc: optional process exit code, used as a tiebreaker when the
            value itself doesn't disambiguate.  Currently unused; kept
            in the signature for forward compatibility with new
            operations-layer strings that may want an rc-aware mapping.

    Returns:
        One of ``FINAL_STATUS_ORDER`` values.  Never raises.
    """
    raw = (value or "").strip().lower()
    if not raw:
        return "missing"
    if raw in ALL_FINAL_STATUSES:
        return raw

    # worker_runner ops-layer fallbacks
    if raw == "no_summary":
        return "missing"
    if raw == "broken_json":
        return "missing"
    if _FAIL_RC_RE.match(raw):
        # The runner couldn't read a summary AND the agent exited
        # non-zero.  That's an executor-side issue (process crashed),
        # not an infra one — maps to executor_incomplete to match
        # Round-5 Phase 4's design: crashes without supervisor terminal
        # verdict are NOT infra_error.
        return "executor_incomplete"

    # Legacy supervisor verdict accidentally stored as a finalStatus
    # (pre-Round-6 some code paths conflated the two).
    if raw == "continue":
        return "executor_incomplete"
    if raw == "stopped":
        # Pre-Round-6 resolve_attempt_outcome's catch-all was "stopped".
        # The review recommends mapping it to executor_incomplete so
        # downstream filters can treat the rerun pool uniformly.
        return "executor_incomplete"

    # Anything we don't recognise: give it the lowest-information bucket
    # and rely on the surrounding error log to flag the unknown value.
    return "missing"


def normalize_supervisor_verdict(value: str | None) -> str:
    """Backward-compat: map old supervisor verdict values to the narrowed set.

    Old data has ``verdict=infra_error`` / ``verdict=rate_limit`` baked
    into score.json (and into supervision_trace.jsonl).  Reading those
    needs a translation:

      - ``infra_error`` / ``rate_limit`` verdicts → ``fail`` (semantically
        the run did not reach pass).  The infra / rate flavour is
        preserved separately in score.infra_error / score.rate_limit
        flags, which ``classify_attempt_outcome`` reads to produce the
        right final_status.

    Returns ``""`` for blank / unknown values so callers can branch on
    presence.
    """
    raw = (value or "").strip().lower()
    if raw in SUPERVISOR_VERDICT_STATES:
        return raw
    if raw in _LEGACY_VERDICT_ALIASES:
        return _LEGACY_VERDICT_ALIASES[raw]
    return ""


def normalize_supervisor_attempt_state(value: str | None) -> str:
    """Backward-compat for the attempt_state enum.  Same shape as
    ``normalize_supervisor_verdict``."""
    raw = (value or "").strip().lower()
    if raw in SUPERVISOR_ATTEMPT_STATES:
        return raw
    if raw in _LEGACY_ATTEMPT_STATE_ALIASES:
        return _LEGACY_ATTEMPT_STATE_ALIASES[raw]
    return ""


# ── shared classifier: ONE function for both Path A and Path B ──

def classify_attempt_outcome(
    *,
    verdict: str = "",
    attempt_state: str = "",
    rate_limit: bool = False,
    infra_error: bool = False,
    infra_error_type: str = "",
    completion_gate_failed: bool = False,
    executor_completed_ever: bool = False,
    agent_exit_code: int | None = None,
    completion_reason: str = "",
    followup_budget_exhausted: bool = False,
    terminal_reason: str = "",
    passed_flag: bool = False,
) -> str:
    """Return the canonical finalStatus for an attempt.

    This is the SINGLE classifier used by both:
      - ``lib/runner/orchestration.py:resolve_attempt_outcome``
        (Path A, runtime: builds outcome from in-memory score dict)
      - ``scripts/orchestra/refresh_summary.py:_derive_status_from_artifacts``
        (Path B, synth fallback when per-attempt summary.json is absent:
        builds outcome from on-disk score.json + meta.json)

    Priority order — exactly matches the if/elif chain below:

      1. **Infra** — ``rate_limit`` / ``infra_error`` / ``pre_exec_failed``.
         Upstream-API / in-container / supervisor infra failure; never scored.
      2. **completion_gate_failed → fail**.  Supervisor wanted to call
         ``pass`` but executor didn't sign off → demote.
      3. **Supervisor explicit terminal** — ``pass`` /
         ``attempt_state=complete_and_passed`` / ``passed_flag`` /
         ``attempt_state=terminal_failure`` / ``verdict=fail``.
         An explicit supervisor classification (pass OR fail) trumps
         all framework-detected interruption signals: the presence of
         the verdict in score.json proves at least one supervisor cycle
         ran, which is stronger evidence than executor_completed_ever.
      4. **Cumulative runtime terminal exits** — ``global_timeout`` (when
         ``terminal_reason`` starts with ``global-timeout`` or
         ``completion_reason in (timeout, …)``) and ``budget_exhausted``
         (when ``terminal_reason == followup-limit-reached`` or
         ``followup_budget_exhausted=True`` or ``verdict=budget_exhausted``).
         Round-7: these PRECEDE the incomplete catch-all — an explicit
         cumulative budget/timeout terminal means the run genuinely exhausted
         its budget (terminal failure) and must leave the queue, not be
         re-dispatched forever as an "incomplete".  ``agent_exit_code==124`` is
         intentionally NOT here — it is a PER-TURN deadline, not cumulative
         (see priorities 5/6).
      5. **Executor never cleanly completed AND no cumulative terminal
         signal** → ``executor_incomplete``.  Strong-sense catch-all: process
         crash, per-turn-deadline first-turn kill (exit 124 + ever=False),
         externally killed with no budget/timeout reason — kept here for
         bounded retry.
      6. **Per-turn deadline after ≥1 clean turn** — ``agent_exit_code==124``
         with the executor having completed a turn → ``global_timeout``.
      6. **Default** → ``executor_incomplete``.  Review recommends this
         instead of the legacy ``stopped`` catch-all so the rerun pool
         doesn't accumulate an extra hard-to-interpret category.
    """
    v = (verdict or "").lower()
    s = (attempt_state or "").lower()
    tr = (terminal_reason or "").lower()
    cr = (completion_reason or "").lower()

    # 1. Infra states
    if v == "rate_limit" or rate_limit:
        return "rate_limit"
    if v == "infra_error" or infra_error:
        if (infra_error_type or "").lower() == "pre_exec_failed":
            return "pre_exec_failed"
        return "infra_error"

    # 2. completion_gate_failed beats any supervisor-claimed pass
    if completion_gate_failed:
        return "fail"

    # 3. Supervisor explicit terminal verdict (any explicit pass/fail
    # classification trumps framework interruption signals — presence of
    # the verdict proves at least one supervisor cycle ran).
    if passed_flag or s == "complete_and_passed" or v == "pass":
        return "pass"
    if s == "terminal_failure" or v == "fail":
        return "fail"

    # 4. Runtime-known terminal exits take PRECEDENCE over the incomplete
    # catch-all (Round-7, ordering reversed from the original).  Rationale:
    # an EXPLICIT budget/timeout terminal signal means the run genuinely
    # exhausted its budget — it is a terminal failure, not an undiagnosed
    # incomplete.  Letting these fall through to ``executor_incomplete``
    # (a non-terminal status) made the dispatcher re-dispatch a run that had
    # already burned its full budget, forever.  Reserving the incomplete
    # catch-all for the STRONG sense (no terminal signal AND never completed
    # a turn — crash / externally-killed-with-no-reason) lets timeout/budget
    # runs leave the queue (bounded retry) instead of churning.
    # NOTE: ``agent_exit_code == 124`` is deliberately NOT in this precedence
    # block — it is a PER-TURN deadline (per-turn ~1200s cap), not a cumulative
    # budget timeout.  A first-turn 124 with ever=False is a genuine incomplete
    # ("stuck on a huge file at deadline") and must stay incomplete (priority-5)
    # for bounded retry; only a 124 AFTER a clean turn is timeout-ish
    # (priority-6).  Only CUMULATIVE terminal signals jump the queue here:
    if (
        tr.startswith("global-timeout")
        or cr in ("timeout", "global-timeout", "global_timeout")
    ):
        return "global_timeout"
    if (
        tr == "followup-limit-reached"
        or followup_budget_exhausted
        or v == "budget_exhausted"
    ):
        return "budget_exhausted"

    # 5. Executor never cleanly completed any turn AND no cumulative terminal
    # signal — the strong-sense incomplete catch-all.  Catches:
    #   - executor crashed (agent_exit != 0) with no budget/timeout reason
    #   - per-turn deadline kill on the FIRST turn (agent_exit_code==124,
    #     ever=False) — genuine incomplete, kept here for bounded retry
    #   - externally killed mid-flight before any terminal signal
    if not executor_completed_ever:
        return "executor_incomplete"

    # 6. Per-turn deadline (agent_exit_code==124) AFTER at least one clean
    # turn — executor was making progress then ran out of per-turn time;
    # treat as global_timeout (terminal).
    if agent_exit_code == 124:
        return "global_timeout"

    # 7. Default — see docstring
    return "executor_incomplete"


# ── shared score-based promotion: single source for Path A and Path B ──

# Status names from which a high-enough score is allowed to promote to ``pass``.
# Anything in {fail, executor_incomplete, infra_error, rate_limit,
# pre_exec_failed} carries a strong "not-pass" signal that score alone must
# never override — supervisor said the answer is wrong, or the executor /
# framework declared the run unusable.
_PROMOTION_BLOCKING_STATUSES: frozenset[str] = frozenset({
    "fail",
    "executor_incomplete",
    "infra_error",
    "rate_limit",
    "pre_exec_failed",
})


def apply_score_based_promotion(
    final_status: str,
    final_score: float,
    success_threshold: float,
) -> tuple[str, bool]:
    """Pass-promotion gate shared by Path A (runtime) and Path B (refresh).

    When the classifier returned a "completed-normally" terminal state
    (e.g. ``budget_exhausted`` or ``global_timeout``) but the captured
    supervisor score meets ``task.success_threshold``, promote to ``pass``.
    Definitive failure paths are never promoted — the supervisor or runtime
    has already rendered a not-pass classification.

    Returns ``(promoted_status, passed_flag)``.

    Path A: called from ``lib/runner/orchestration.py:resolve_attempt_outcome``.
    Path B: called from
    ``scripts/orchestra/refresh_summary.py:_derive_status_from_artifacts``
    using the ``success_threshold`` persisted into ``score.json``.
    """
    if (
        final_status not in _PROMOTION_BLOCKING_STATUSES
        and final_score >= success_threshold
    ):
        return "pass", True
    return final_status, False


# ── public artifact schema versions ────────────────────────────────────
#
# The top-level JSON artifacts the runner emits are part of Clawbench's
# public surface: third-party consumers read them to plot results, run
# secondary analyses, and audit individual attempts. Each carries an
# explicit ``schema_version`` so a future field rename / removal / type
# change can be detected without guessing.
#
# Bumps must be deliberate: only on a *breaking* change to a field that
# downstream consumers may already read. Adding a new optional field is
# NOT a bump. The field name is ``schema_version`` (snake_case) to match
# the existing ``supervision_decision`` schema field — keep both forms
# the same so a reader can branch on one name.
SUMMARY_SCHEMA_VERSION = "clawbench.summary/v1"
SCORE_SCHEMA_VERSION = "clawbench.score/v1"
META_SCHEMA_VERSION = "clawbench.meta/v1"
SESSION_META_SCHEMA_VERSION = "clawbench.session_meta/v1"
BATCH_SUMMARY_SCHEMA_VERSION = "clawbench.batch_summary/v1"


# ── batch statistics helper ──

def build_status_counts(results) -> dict[str, int]:
    """Build a complete statusCounts breakdown for a batch of result dicts.

    Used by ``lib/runner/orchestration.py:batch_run`` and
    ``scripts/batch_eval.py`` so the summary always carries the full
    ``FINAL_STATUS_ORDER`` keys (zero-padded for any not present), not
    just the handful of fields the old code counted by hand.

    Args:
        results: an iterable of dicts that each have a ``finalStatus``
            (or ``final_status``) key.  Anything else gets normalised
            via ``normalize_final_status``.

    Returns:
        ``{status_name: count}`` with every value in ``FINAL_STATUS_ORDER``
        present as a key (zero-padded).
    """
    counts = {s: 0 for s in FINAL_STATUS_ORDER}
    for r in results:
        raw = r.get("finalStatus") or r.get("final_status") or ""
        canonical = normalize_final_status(raw)
        if canonical in counts:
            counts[canonical] += 1
    return counts
