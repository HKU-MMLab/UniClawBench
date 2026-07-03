# Status Model — single source of truth

Round-6 (2026-05-13) consolidated Clawbench's attempt-status vocabulary
into a single module, [`lib/status.py`](../lib/status.py).  All
downstream code — runtime classifier, refresh_summary synth fallback,
dispatcher priority queues, monitor (`top.py`), batch statistics — now
reads ranking, canonical names, normalization, and classification from
that one place.

This document is a map of the vocabulary.  For implementation details
see `lib/status.py` itself; for the live priority decision logic see
`classify_attempt_outcome`.

## Three kinds of state

The framework juggles three distinct state spaces.  Mixing them up
caused the bugs Round-6 fixes — keep them straight:

| State kind | Who decides | Allowed values |
|---|---|---|
| **Supervisor verdict** | the supervisor MODEL | `pass`, `continue`, `fail` |
| **Supervisor attempt_state** | the supervisor MODEL | `in_progress`, `incomplete`, `complete_but_failed`, `complete_and_passed`, `terminal_failure` |
| **Framework final_status** | the FRAMEWORK (after gathering all signals) | one of `FINAL_STATUS_ORDER` (below) |

The supervisor MODEL judges **task semantics** only — did the agent
succeed, should the user say more, is it terminally wrong.  The
**framework** detects runtime issues (HTTP 429, container died, host
pre-exec failed) from external signals and labels them itself.

## FINAL_STATUS_ORDER

The canonical 10-value vocabulary every component agrees on.  Higher
in the list = better ("best attempt" selection prefers earlier
entries):

```
pass                  ← terminal success (0)
budget_exhausted      ← ran through full max_user_followups; no pass (1)
fail                  ← supervisor explicit terminal failure (2)
global_timeout        ← cumulative wall-clock cap hit (3)
executor_incomplete   ← executor never cleanly completed a turn (4)
rate_limit            ← upstream API refused (zero agent progress) (5)
infra_error           ← container / docker / supervisor infra failure (6)
pre_exec_failed       ← host-side pre_exec script failure (subtype of infra) (7)
running               ← mid-flight snapshot (no terminal classification yet) (8)
missing               ← no usable artifact at all (9)
```

Anything that isn't in this list (legacy values, ops-layer strings,
typos) is normalised via `lib.status.normalize_final_status` at the
boundary, so downstream code only ever sees the 10 canonical names.

## Subset categorization

```
TERMINAL_RESULT_STATUSES = {pass, budget_exhausted, fail, global_timeout}
INCOMPLETE_STATUSES      = {executor_incomplete, running, missing}
INFRA_STATUSES           = {infra_error, pre_exec_failed, rate_limit}
```

- `TERMINAL_RESULT_STATUSES` — definitive evaluation outcomes. By default the
  dispatcher will not schedule a re-run; `global_timeout` is the only terminal
  status that can be retried, and only if the orchestra config declares an
  explicit `status_in: [global_timeout]` tier. Wildcard/catch-all priorities do
  not pick it up.
- `INCOMPLETE_STATUSES ∪ INFRA_STATUSES` — the rerun pool.

## The single classifier

`classify_attempt_outcome(...)` in `lib/status.py` is the only place
that produces a `final_status` from raw signals.  Both code paths use it:

- **Path A (runtime, in-memory)** —
  [`lib/runner/orchestration.py:resolve_attempt_outcome`](../lib/runner/orchestration.py)
  adapts the live `score` dict + `terminal_reason` to `classify_attempt_outcome`
  kwargs, then applies score-based pass promotion.
- **Path B (synth fallback)** —
  [`scripts/orchestra/refresh_summary.py:_derive_status_from_artifacts`](../scripts/orchestra/refresh_summary.py)
  reads on-disk `score.json` + `meta.json` for an attempt that lacks
  its own `summary.json`, and adapts those to the same kwargs.

Priority order (see the function's docstring for the full text):

1. Infra (`rate_limit` / `infra_error` / `pre_exec_failed`)
2. `completion_gate_failed` → `fail`
3. Supervisor explicit terminal (`pass` / `fail`).  Trumps
   framework interruption signals — the presence of the verdict in
   score.json proves a supervisor cycle ran.
4. `not executor_completed_ever` → `executor_incomplete`
5. Runtime terminal exits (`global_timeout` / `budget_exhausted`)
6. Default → `executor_incomplete`

## Normalization at the boundary

`normalize_final_status(value, rc=None)` maps any incoming status
string (including legacy + ops-layer values) to a canonical
`FINAL_STATUS_ORDER` member:

| Incoming | Canonicalized to |
|---|---|
| any of the 10 canonical names | unchanged |
| `no_summary`, `broken_json` | `missing` |
| `FAIL_rc=<N>` | `executor_incomplete` |
| `continue` (legacy verdict-as-status) | `executor_incomplete` |
| `stopped` (legacy catch-all) | `executor_incomplete` |
| empty / unknown | `missing` |

This is invoked by `scripts/orchestra/worker_runner.py` before writing
the DONE payload, so the dispatcher never sees an ops-layer string on
the wire.  `lib.status.build_status_counts` also routes through
this normaliser, so batch summaries can ingest legacy artifacts
without leaving any result un-counted.

## Legacy supervisor verdict translation

Old `score.json` files baked `verdict=infra_error` / `verdict=rate_limit`
into the supervisor's output schema.  Round-6 narrowed the schema so
the supervisor model only emits `pass` / `continue` / `fail`.  When a
reader encounters the legacy values:

- `normalize_supervisor_verdict("infra_error")` → `"fail"` (the run did
  not reach pass; semantically a fail).  The infra-flavoured
  `final_status` is preserved via the framework's separate
  `infra_error=True` flag on the score record.
- `normalize_supervisor_verdict("rate_limit")` → `"fail"`.  The
  rate-limit flavour is preserved via `rate_limit=True` on the score.

The validator (`lib/supervision/answer_supervisor.py:validate_answer_supervisor_payload`)
applies the same translation to fresh model outputs that haven't yet
caught up to the narrowed schema, leaving a `legacy_verdict_seen`
breadcrumb so operators can spot models that need re-prompting.

## What lives where

| Concern | Module | Function |
|---|---|---|
| Canonical name list | `lib/status.py` | `FINAL_STATUS_ORDER` |
| Subset categorization | `lib/status.py` | `TERMINAL_RESULT_STATUSES` / `INCOMPLETE_STATUSES` / `INFRA_STATUSES` |
| Ranking | `lib/status.py` | `status_rank()` |
| Classification | `lib/status.py` | `classify_attempt_outcome()` |
| Boundary normalization | `lib/status.py` | `normalize_final_status()` |
| Legacy supervisor translation | `lib/status.py` | `normalize_supervisor_verdict()` / `normalize_supervisor_attempt_state()` |
| Batch stats | `lib/status.py` | `build_status_counts()` |
| Supervisor enums (narrowed) | `lib/constants.py` | `VERDICTS` / `ATTEMPT_STATES` |
| Supervisor enums (legacy superset) | `lib/constants.py` | `LEGACY_VERDICTS` / `LEGACY_ATTEMPT_STATES` |
| Runtime Path A | `lib/runner/orchestration.py` | `resolve_attempt_outcome()` |
| Synth Path B | `scripts/orchestra/refresh_summary.py` | `_derive_status_from_artifacts()` |
| DONE payload normalization | `scripts/orchestra/worker_runner.py` | `_normalize_final_status` import + call |

Adding a new status: edit `lib/status.py` (add to `FINAL_STATUS_ORDER`,
decide which subset frozenset gets it, teach `classify_attempt_outcome`
when to emit it).  Nothing else should need to change.
