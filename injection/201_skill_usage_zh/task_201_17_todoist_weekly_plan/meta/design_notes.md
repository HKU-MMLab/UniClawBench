# Design notes — task_101_17_todoist_weekly_plan

Internal archive only. Not injected into executor or supervisor view.

## Schema

- Schema: `a+b` — accept-set time-block structure plus per-day priority
  expectations.
- Difficulty: Medium.

## Revision history

- Original layout dictated a rigid "60 min morning + 90 min afternoon"
  shape per day. Revised to an accept-set structure (1–3 blocks per
  day, >3 penalized) with a reverse priority-ordering constraint
  (P4 must not outrank P1/P2 on a given day).
- Removed the previous "total minutes >= 840" floor: the public prompt
  asks the executor to "keep it concise" and caps each day at 1–3
  blocks, so a 14-hour weekly total cannot be reached without padding.
  Under-scheduling is no longer penalized.
- Added 5 already-completed records (`checked: true` plus a
  `completed_at` timestamp) into the same `items[]` array as the 25
  active tasks. IDs `1101..1105` (see `ground_truth.completed_distractor_ids`).
  A competent weekly planner must filter these out before scheduling.
- Score caps were tightened from a long list of rubric-restating bands
  down to a small set of edge-case caps (no deliverable, credentials
  leaked, fabricated tasks, completed tasks scheduled, total scope
  blowout). Skill-trace caps were softened to a per-rubric down-weight,
  since absence of a skill read does not by itself constitute an
  extreme failure.

## Rationale for the priority-first rubric

The public prompt phrases the priority requirement as "P1/P2 should
get earlier / longer blocks." The rubric encodes this as: on any day
that has a P1/P2 task due, the first scheduled block of that day must
point at a P1/P2 task. Per-day partial credit (3% deducted per
violation) keeps the line scoreable rather than binary.

## Rationale for the completed-distractor cap

Completed records are placed in the same `items[]` array, not in a
separate "archive" file, so the executor must read the field
(`checked` / `completed_at`) and filter on it. Scheduling a completed
record indicates the executor never inspected the per-record state,
which is a basic correctness failure for any task-management task.

## Round 1 hardening (2026-04-30)
- Added per_day_first_block_anchors GT field (7 day-keyed anchor titles).
- Added §5 CP "Per-day priority-first ordering precision" 0.07 (stepped 7/5-6/3-4/≤2).
- Shaved 0.07 from "Priority-first ordering" (0.15 → 0.08); the existing
  CP only checks P1/P2-class membership of the first block, while the new
  CP checks identity match against the canonical per-day anchor.
- Target: opus 0.82 → ~0.70 (likely loses 0.07 since opus uses chronological/category order for all 7 days per supervisor rationale).

## Round 2 hardening (2026-04-30) — re-anchor for promoted task
- Task promoted from continue 0.82 → pass 0.95 after R1 P1-first anchor
  (opus correctly anchored each day's first block on the canonical P1/P2
  task and cleared the new CP). Need a different precision dimension to
  push the score back into continue.
- Added §5 CP "Per-day low-priority distribution precision" 0.08
  (stepped 7/5-6/3-4/≤2). Each day's count of P3+P4 scheduled blocks
  must match GT exactly: 25→2, 26→1, 27→1, 28→1, 29→2, 30→2, 01→2.
- Added GT field `per_day_low_priority_count` (per-day expected count)
  plus an explanatory `per_day_low_priority_count_note` documenting the
  derivation (P1/P2 first, fill to 3 blocks/day with same-day P3/P4
  snapshot tasks) and acceptance criteria for what counts as a "low-
  priority" block (priority field P3/P4/3/4/low/deferred OR pointing at
  a snapshot task with priority ∈ {3,4}).
- Shaved 0.08 from "weekly_schedule.csv exists and is well-formed"
  (0.16 → 0.08). The CSV-shape CP is the heaviest non-anchor weight
  (0.16) and overlaps with multiple other CPs that already test CSV
  agreement (cross-deliverable agreement, completed-task filtering),
  so compressing it minimizes redundancy.
- Final weights: 0.12 + 0.12 + 0.10 + 0.08 + 0.07 + 0.10 + 0.10 + 0.08
  + 0.08 + 0.10 + 0.05 = 1.00.
- Target: opus 0.95 → ~0.83 (loses 0.08 if daily P3/P4 count drifts on
  ≥3 days — opus's typical failure mode is to under-schedule, packing
  only 1-2 P1/P2 blocks per day and skipping the P3/P4 fill, which
  drops the per-day low-priority count to 0 instead of 1-2 across
  most days).

## Round 3 hardening (2026-04-30) — third anchor
- After R1+R2 (P1-first + low-priority count), score 0.95→0.59 (good drop).
- R3 added §5 CP "Per-deferred-block defer-metadata" 0.07 (≥3 strict).
- Added GT fields deferred_block_required_fields + min_deferred_blocks_with_metadata.
- Shaved 0.07 from "weekly_schedule.csv exists and is well-formed" (0.08→0.01); CSV-shape redundancy is already heavy after R2 shave (no-overlap, real-tasks-only, 1-3-per-day all enforced by other CPs and §6 caps), so this line can absorb another 0.07 without losing audit coverage.
- Target: opus 0.59 → ~0.45 (loses 0.07 if deferred-block metadata absent; opus typically just schedules without defer notes).

## Round 4 hardening (2026-04-30) — fourth anchor (ICS precision)
- After R1+R2+R3, score 0.83 (oversaturation in R3).
- R4 added §5 CPs "ICS UID canonical-pattern precision" 0.07, "ICS DTSTART/DTEND format strict" 0.06.
- Added GT fields ics_uid_pattern_required + min_vevents_with_canonical_uid + ics_dtstart_dtend_format_required + ics_dtformat_strict.
- Shaved 0.13 from "weekly.ics exists and matches the CSV" (0.10→0.04, -0.06), "Cross-deliverable agreement & readability" (0.05→0.02, -0.03), and "Project coverage" (0.10→0.06, -0.04). The ICS shape line is now subsumed by the new UID + DT format precision anchors; readability partially overlaps cross-format agreement also enforced by the strict CPs; project-coverage is a low-precision soft-floor that is implicitly enforced by the snapshot-mapping CP (which rules out invented tasks and thus implicitly forces some project diversity).
- Target: opus 0.83 → ~0.65 (loses up to 0.13 if ICS UID/format drift; opus often uses non-canonical UIDs).

## Review pass (2026-04-30)

User-driven review pass. Three review_record items addressed:

1. **Snapshot mode separation.** The prior YAML had a single `task` field
   that mentioned both `$TODOIST_API_TOKEN` and the snapshot path,
   bleeding the snapshot reference into live-API mode. Split into:
   - `task` (live-API variant) — only mentions `$TODOIST_API_TOKEN`,
     no snapshot file reference.
   - `task_snapshot` (snapshot variant, gated by `SNAPSHOT_MODE=1`) —
     references `/tmp_workspace/clawbench/sources/todoist_snapshot.json`.
   Added a new §6 cap "0.50 — Snapshot leak in live-API mode" and a
   `snapshot_mode_separation` GT block describing the rule. eval §3
   updated to make the live-API-mode rule explicit.

2. **Hint removal.** Both prompt variants stripped the soft hints "if
   a day has no tasks, 'free day' is fine — don't invent work to fill
   it" and "Cover at least two of my projects overall." These were
   leakages of rubric criteria into the prompt and discouraged the
   strict 7-day full-coverage anchor. Project-coverage is still scored
   in §5 (0.05) but no longer pre-announced in the prompt.

3. **Strict deterministic anchors + GT date fix.** The prior
   `per_day_first_block_anchors` keyed on 2026-04-25..2026-05-01 but
   the prompt said "next 7 days," letting executors drift to other
   date windows and invalidate the anchors. Fix applied via option (b)
   from the review_record: hardcoded the canonical 7-day window
   (2026-04-25 Sat .. 2026-05-01 Fri) directly into both prompt
   variants. The GT dates remain as-is and are now reachable by
   construction.

   Added a new strict CP "must_appear_on_specific_day strict pairings"
   (0.12, binary). The new GT field `must_appear_on_specific_day`
   enumerates seven (id, scheduled_date) pairs:
   - 1021 → 2026-04-25 (board pre-read, P1)
   - 1015 → 2026-04-26 (DDIA Chapter 7, P1)
   - 1002 → 2026-04-27 (Acme MSA SOW, P1)
   - 1017 → 2026-04-28 (MIT 6.824 quiz, P1)
   - 1011 → 2026-04-29 (Globex escalation, P1)
   - 1012 → 2026-04-30 (Walgreens refill, P1)
   - 1020 → 2026-05-01 (invoice mismatch, P2 — only P1/P2 due that day)
   Each listed task must appear on the listed date in `weekly.md`,
   the CSV, and the ICS. One missing pairing in any of the three
   deliverables fails the line.

4. **All §5 CPs strict (no ≥ X / Y).** Reworked all stepped-credit
   lines into binary 7/7 strict checks. Per-day priority-first
   ordering: 7/7 strict (was 7/5-6/3-4/≤2 stepped). Per-day low-
   priority count: 7/7 strict. ICS UID: every VEVENT canonical
   pattern (was ≥15/19). ICS DT format: every VEVENT strict (was
   already strict). Deferred-block metadata: every deferred block
   strict (was ≥3/any). Removed `min_deferred_blocks_with_metadata`
   and `min_vevents_with_canonical_uid` GT fields; replaced with
   `deferred_block_strict: true` and `ics_uid_strict: true`.

5. **§5 weight rebalance after strict-conversion + new CP.**
   Reweighted to fit the new "must_appear_on_specific_day" 0.12 CP
   while keeping all other CPs reasonably weighted:
   - 0.10 (was 0.12) — 7 daily sections covering canonical dates
   - 0.10 (was 0.12) — 1-3 blocks per day
   - 0.05 (was 0.06) — Project coverage
   - 0.10 (was 0.07 + 0.08) — Per-day priority-first ordering 7/7
     strict (consolidated the prior class-membership and identity-
     match CPs into a single strict line)
   - 0.12 (NEW) — must_appear_on_specific_day strict pairings
   - 0.08 (was 0.10) — Duration on every block (now binary)
   - 0.10 — Tasks correspond to active snapshot items
   - 0.04 (was 0.01) — CSV well-formed (regained 0.03 since we no
     longer have the second priority-class CP)
   - 0.07 — Per-deferred-block defer-metadata
   - 0.08 — Per-day low-priority distribution 7/7 strict
   - 0.04 — `weekly.ics` exists and matches the CSV
   - 0.02 — Cross-deliverable agreement & readability
   - 0.06 (was 0.07) — ICS UID canonical-pattern strict
   - 0.04 (was 0.06) — ICS DTSTART/DTEND format strict
   Sum: 1.00 (verified).

Files touched:
- `tasks/101_skill_usage/task_101_17_todoist_weekly_plan.yaml` (full
  rewrite of `task` and `task_snapshot` in ENGLISH; skill mention
  in first paragraph; canonical 7-day window hardcoded).
- `injection/101_skill_usage/task_101_17_todoist_weekly_plan/references/eval_rule.md`
  (full rewrite of §1, §2, §3, §4, §5, §6, §9 to reflect strict
  binary CPs, snapshot-mode separation, and canonical date window).
- `injection/101_skill_usage/task_101_17_todoist_weekly_plan/references/ground_truth.json`
  (added `canonical_dates`, `must_appear_on_specific_day`,
  `snapshot_mode_separation`, `deferred_block_strict`,
  `ics_uid_strict`; fixed anchor dates to canonical window;
  removed soft `min_*` thresholds).
- this design_notes.md.

§5 sum verification: 0.10+0.10+0.05+0.10+0.12+0.08+0.10+0.04+0.07+
0.08+0.04+0.02+0.06+0.04 = 1.00.
