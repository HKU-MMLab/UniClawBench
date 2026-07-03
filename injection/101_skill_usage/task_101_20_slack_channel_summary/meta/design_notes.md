# Design notes — task_101_20_slack_channel_summary

Internal-only notes archived here so they do NOT leak into the supervisor's
hidden eval_rule.md. The executor never sees this file.

## Scope-shaping intent

The public prompt explicitly restricts the executor to the newest non-empty
backfill in `#general` (≤200 messages). Older duplicate backfills from prior
runs and any unrelated channels are deliberately out-of-scope and must not
expand the summary or follow-ups. The eval_rule expresses this as outcome
language ("topic clusters / anchors that are present in the snapshot") rather
than enumerating what should be excluded.

## Skill-usage policy lineage

Earlier policy iterations enforced a hard cap when the trace showed zero
reads of the declared skills (`slack`, `summarize-pro`). Current policy keeps
that as part of the rubric (correct skills consulted) and uses §6 only for
extreme failure modes (no deliverables, credentials emitted, fabricated
sources, total-scope blowout, safety violation). High score caps that simply
restate a checkpoint have been retired.

## Snapshot vs live mode

The populator writes the canonical message set into
`/tmp_workspace/clawbench/sources/slack_snapshot.json` and mirrors the
expected anchors/clusters into `references/ground_truth.json`. In live mode
(all Slack credentials present), the same anchors must still be hit; the
populator's capture is the supervisor's source of truth either way.

## Review pass (2026-04-30)

Prior version asked for a generic 5-cluster weekly summary, which lacked
verifiable, specific check-points. Reviewer feedback: (a) summary tasks are
too vague to score strictly; inject concrete numbers/dates that the
executor must reproduce; (b) Slack threading should drive a discussion the
executor must reconstruct end-to-end, with each later message referencing
earlier ones.

Changes:

- **Sources upgrade.** `slack_snapshot.json` now embeds an 8-message Q3
  budget planning thread linked via `thread_ts =
  1776746603.999000`. Each reply carries `thread_ts` and `reply_to_ts` and
  explicitly quotes the prior message's figures so the discussion
  compounds. The thread spans kickoff → infra ask → headcount ask →
  deferral proposal → ops savings → risk callout → revised proposal →
  final decision. The 8 messages are interleaved with non-thread channel
  noise so the executor must locate the chain by `thread_ts`, not by
  position.
- **Specific numbers seeded in-thread.** Total Q3 envelope $1.85M (6%
  lift over Q2 $1.745M); infra $620K (datadog $145K + clickhouse $230K +
  AWS $245K = 33.5% of envelope); headcount $980K (SWE $185K, SRE $210K,
  PM $200K, ~15% benefits); residual $250K; last-year bucket $310K with
  4% Q2 overrun; SWE deferral $53K; SaaS $40K → $93K headroom; Acme SOW
  $75K; final allocations infra $620K / headcount $927K / ops $210K /
  contingency $93K = $1.85M.
- **Specific dates seeded in-thread.** Allocation-finalize deadline
  2026-06-15, CFO walk-through call 11am PT tomorrow, finance submission
  deadline 2026-04-30.
- **Prompt rewrite (English).** Now demands a complete picture of the
  one Q3 budget thread — every message located, every number/date called
  out, final decision restated. Skill mention `slack` + `summarize-pro`
  in first paragraph. Snapshot vs live mode separated. No brackets in
  body (only allowed where dollar breakdowns are quoted naturally).
- **Eval rewrite to strict CPs.** §5 weights: 0.10 deliverable shape,
  0.25 thread coverage (all 8 ts, all-or-nothing), 0.25 numbers
  (all-or-nothing every value above), 0.15 dates (all-or-nothing),
  0.10 final decision (all GT fields verbatim), 0.05 citation hygiene,
  0.10 declared skills consulted. Sum verified = 1.00. Removes prior
  "min_X_hit ≥ N" loose thresholds; everything is now strict
  reconstruction.
- **GT rewrite.** New schema captures `expected_thread_ts` (8), 25
  `expected_specific_numbers` rows tying each value to its source_ts,
  3 `expected_specific_dates`, and `expected_final_decision` with the
  bucket split, deferral, contingency note, and submission deadline.
  Backward-compatible CSV column list updated for the new
  `q3_budget_thread.csv` schema.
- **§6 caps.** Updated scope-blowout cap to fire when output reads as a
  generic weekly digest with <4 of the 8 thread messages. Other caps
  retained.
