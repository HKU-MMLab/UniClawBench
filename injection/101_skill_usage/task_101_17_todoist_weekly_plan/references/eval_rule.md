# Hidden Evaluation Rule — task_101_17_todoist_weekly_plan

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the declared skills under `/root/skills/` (see §8) were genuinely
used. The rubric prizes outcome correctness over process: a faithful weekly
plan that respects priority ordering, sticks to real Todoist items, and
emits the three required deliverables in agreement with each other.

The public prompt fixes the canonical 7-day window
(2026-04-25 .. 2026-05-01), so date-keyed checkpoints below use those
exact dates. Process constraints are limited to what is needed to audit
the result: the skills declared in the prompt must show up in the trace,
credentials must not leak into user-visible output, and tasks already
marked done in the snapshot must not be scheduled. Score caps in §6
override rubric totals when extreme failures occur.

## 2. Task Contract

The user asks for a 7-day plan derived from their Todoist tasks. The
canonical input is a 7-day Todoist snapshot at
`/tmp_workspace/clawbench/sources/todoist_snapshot.json` (25 active tasks
across 4 projects, with `due_date` values 2026-04-25..2026-05-01). When
`SNAPSHOT_MODE=1` is exported, the snapshot is canonical. When the
executor was given the live-API variant of the prompt (no SNAPSHOT_MODE
export), the executor may fetch from the live Todoist API using
`$TODOIST_API_TOKEN`; in that mode the snapshot file must NOT be the
required source.

The prompt explicitly fixes the 7-day window as 2026-04-25 (Saturday)
through 2026-05-01 (Friday), inclusive. The plan must cover exactly
those seven dates.

Required deliverables:
- `/tmp_workspace/results/weekly.md` — 7 daily sections covering
  2026-04-25..2026-05-01, each with 1–3 time blocks pointing at that
  day's most important tasks. Priority ordering: P1/P2 > P3 > P4.
- `/tmp_workspace/results/weekly_schedule.csv` — one row per scheduled
  block with columns `date, start_time, end_time, duration_minutes,
  task_title, project, priority, due_date, reason`. Blocks must stay
  within 1–3 per day and must not overlap on the same date.
- `/tmp_workspace/results/weekly.ics` — calendar events matching the
  scheduled blocks in the CSV. Event summary contains task title and
  project; description contains priority and due date.

Nothing in `references/` may expand scope.

## 3. Source-Selection and Target-Resolution Rules

When `SNAPSHOT_MODE=1` is exported the canonical source is
`/tmp_workspace/clawbench/sources/todoist_snapshot.json` and the
supervisor must NOT penalize the executor for skipping the live API.
When `SNAPSHOT_MODE` is unset the executor was prompted to use the live
API via `$TODOIST_API_TOKEN`; in that mode reading the snapshot file is
not the canonical path (the snapshot may still be referenced by the
populator but it is not part of the user-visible contract).

The snapshot's `items[]` array contains both active and already-completed
records. Records with `checked: true` or a `completed_at` timestamp must
be treated as "already done — do not schedule." Only the 25 active
records (IDs 1000..1024) are eligible for the weekly plan.

If multiple tasks share a due date, ties are broken by priority (P1
first, then P2, P3, P4). Within the same priority, any deterministic
ordering by `id` or by Todoist `order` is acceptable.

## 4. Ground-Truth Snapshot

Structured ground truth at `references/ground_truth.json`. Key values
the supervisor cross-checks:

- `day_count` = 7 with canonical dates 2026-04-25 .. 2026-05-01.
- `projects_min` = 2 (out of 4: Work / Personal / Learning / Home).
- `snapshot_task_count` = 55 total records, of which `active_task_count`
  = 25 are eligible; the remaining 30 are completed records (listed in
  `completed_distractor_ids`) that must be filtered out before
  scheduling.
- `per_day_high_priority` lists, for each of the 7 dates, the P1/P2
  tasks due that day and their canonical IDs / content.
- `per_day_first_block_anchors` keys are the seven canonical dates
  2026-04-25..2026-05-01; each value is the canonical title of the
  P1/P2 task that the first block of that day must point at.
- `must_appear_on_specific_day` enumerates strict task→date pairings:
  every listed Todoist id must appear in `weekly.md`, the CSV, and the
  ICS on the specified date. These are deterministic, not soft
  preferences.
- CSV / ICS blocks reference only snapshot tasks and agree with
  `weekly.md` on titles.

## 5. Checkpoint Rubric

Weights sum to 1.00. Every checkpoint below is strict — no "≥ X / Y"
soft thresholds.

- **0.10 — 7 daily sections covering canonical dates.** `weekly.md`
  contains exactly 7 day sections covering 2026-04-25, 2026-04-26,
  2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30, and 2026-05-01.
  Missing any one of the seven dates, or covering a date outside that
  window, fails this line.
- **0.10 — 1–3 blocks per day, strict.** Every one of the seven days
  has between 1 and 3 time blocks. Any day with 0 blocks (when active
  tasks are due that day) or with >3 blocks fails this line.
- **0.05 — Project coverage.** The plan mentions at least 2 of the 4
  projects (Work / Personal / Learning / Home) overall.
- **0.14 — Per-day priority-first ordering, strict (7/7).** For each
  of the seven canonical dates, the FIRST scheduled block of that day
  in `weekly.md` AND in `weekly_schedule.csv` must match the canonical
  anchor in `ground_truth.per_day_first_block_anchors[<date>]`
  (case-insensitive substring of the canonical title within the first
  block's task title or description). All 7 days must match. Any miss
  on any day fails this line (binary 0.14 vs 0).
- **0.16 — `must_appear_on_specific_day` strict pairings.** Every task
  listed in `ground_truth.must_appear_on_specific_day` must appear on
  the specified date in `weekly.md`, in `weekly_schedule.csv`, and in
  `weekly.ics`. Each listed task is a P1 or P2 item that the user's
  prompt explicitly anchors via "the first block on each day must
  point at the most important task due that day" plus the fixed
  canonical 7-day window. All listed pairings must be satisfied
  across all three deliverables (binary 0.16 vs 0; one missing
  pairing in any of the three deliverables fails the line).
- **0.08 — Duration on every block.** Every block in `weekly.md`
  carries an explicit duration (e.g. `60 min`, `1 hour`, `90m`).
  Missing duration on any block fails this line (binary).
- **0.10 — Tasks correspond to active snapshot items.** Every task
  title or topic referenced in `weekly.md`, the CSV, and the ICS maps
  1:1 to an entry in `items[]` whose `checked` is `false` and that
  has no `completed_at` timestamp. Any invented or hallucinated task,
  or any reference to a completed-distractor id, fails this line
  (binary).
- **0.04 — `weekly_schedule.csv` exists and is well-formed.** Required
  columns present in the exact order required by the prompt; one row
  per scheduled block; 1–3 rows per date; no same-day time overlaps;
  durations match the Todoist `duration` when one is provided or are
  a clearly-shorter planned subset.
- **0.07 — Per-deferred-block defer-metadata, strict.** When the
  executor defers a task to a later date than the user's original
  due date (any block whose effective scheduled_date > the snapshot
  task's `due_date`), the block must include both an explicit original
  due date (e.g. `moved_from_date` field or "originally due ...") AND
  a one-line `defer_reason`. Either every deferred block has both
  fields (full credit) or any deferred block missing either field
  fails the line (binary 0.07 vs 0). If the executor produced no
  deferred blocks at all, this line passes by default.
- **0.04 — `weekly.ics` exists and matches the CSV.** Calendar events
  for the same scheduled blocks; event summary includes task title and
  project; description includes priority and due date.
- **0.02 — Cross-deliverable agreement & readability.** `weekly.md`,
  the CSV, and the ICS agree on selected task titles and dates (minor
  paraphrase tolerated); the markdown is human-readable.
- **0.06 — ICS UID canonical-pattern strict.** Every VEVENT in
  `weekly.ics` must have a UID matching the canonical pattern
  `task_<id>@todoist-weekly-plan`. The accepted `<id>` family depends
  on the executor's source mode:
  - In snapshot mode (`SNAPSHOT_MODE=1` exported), `<id>` must be the
    integer Todoist task id from the snapshot (`active_id_range`
    1000..1024). Any non-integer UID fails this line.
  - In live-API mode (no `SNAPSHOT_MODE`, executor used
    `$TODOIST_API_TOKEN`), the live Todoist v2 API returns
    alphanumeric task ids (e.g. `6gQf4crMh4PgphMq`). Both the
    snapshot integer family and the live alphanumeric family round-
    trip to the same task content via the populator. In live mode,
    accept any of: (a) integer UIDs from the snapshot family
    `1000..1024`, or (b) live alphanumeric UIDs of the form
    `task_[A-Za-z0-9]{8,}@todoist-weekly-plan` consistently produced
    across all VEVENTs from the same Todoist account read.
  All VEVENTs must use a correctly-formatted UID under the active
  mode; any mismatched UID fails this line (binary 0.06 vs 0).
- **0.04 — ICS DTSTART/DTEND format strict.** Every VEVENT must have
  both DTSTART and DTEND in `YYYYMMDDTHHMMSSZ` (UTC, with `Z`
  suffix). Local timezone formats (`TZID=`, naked datetime) do NOT
  count. Any one mismatched VEVENT fails this line (binary 0.04 vs
  0).

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps
override rubric totals when extreme failures occur:

- **Cap 0.30 — No primary deliverable.** `weekly.md` is missing or
  unreadable.
- **Cap 0.30 — Credentials emitted in user-visible output.** Any
  occurrence of `$TODOIST_API_TOKEN` or its resolved value in
  `weekly.md`, the CSV, the ICS, or chat output.
- **Cap 0.60 — Fabricated tasks.** `weekly.md`, the CSV, or the ICS
  schedules a task that does not correspond to any record in the
  snapshot's `items[]` array.
- **Cap 0.50 — Already-completed tasks scheduled.** Any task whose
  snapshot record has `checked: true` or a `completed_at` timestamp
  is included in `weekly_schedule.csv`, `weekly.ics`, or `weekly.md`.
  Canonical IDs of completed records are enumerated in
  `ground_truth.json.completed_distractor_ids`.
- **Cap 0.50 — Snapshot leak in live-API mode.** When `SNAPSHOT_MODE`
  is NOT exported (live-API variant of the prompt was given), if the
  executor's trace shows it read directly from
  `/tmp_workspace/clawbench/sources/todoist_snapshot.json` to source
  the weekly plan instead of going through the Todoist skill's API
  path. Reading the snapshot when SNAPSHOT_MODE=1 is set is fine.
- **Cap 0.70 — Total scope blowout.** `weekly.md` schedules more than
  5 time blocks on three or more days, indicating wholesale disregard
  of the 1–3-per-day envelope.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/todoist/` OR `/root/skills/plan-my-day/` belonging
  to the declared skill(s). A skill-usage task with zero evidence of
  consulting the declared skill(s) cannot reach a full score.

Pass requires all critical checkpoints satisfied (priority ordering,
real snapshot tasks only, all three deliverables present and in
agreement) and total ≥ 0.90.

## 7. Continue vs Fail Guidance

- **Pass (≥ 0.90):** all three deliverables present, priority ordering
  honored, only active snapshot tasks scheduled, no caps triggered.
  Executor should stop.
- **Continue (0.50 – 0.89):** prefer one follow-up to fix the lowest-
  scoring rubric line — for example, missing ICS, missing duration on
  some blocks, or one priority-first violation. Recoverable.
- **Fail (< 0.50):** missing primary deliverable, fabricated tasks, or
  credentials leaked. No further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only — must NOT be surfaced to the executor or user
simulator:

- `references/eval_rule.md` — this file.
- `references/ground_truth.json` — per-day high-priority anchors,
  expected output paths, must-appear-on-specific-day pairings, and
  the IDs of completed records that must be filtered out.

The executor's trace should also show reads of the two declared
skills:

- `/root/skills/todoist/SKILL.md` (or any file under
  `/root/skills/todoist/`) — task-management skill for interpreting
  the Todoist export.
- `/root/skills/plan-my-day/SKILL.md` (or any file under
  `/root/skills/plan-my-day/`) — scheduling skill for the time-block
  layout.

Absence of either skill in the trace is a soft signal of skill
neglect; the supervisor may down-weight the relevant rubric line on
that basis but should not cap the total on this signal alone.

## 9. Dynamic Content Note

This is an authenticated task. The 7-day window is now hard-coded in
the prompt (2026-04-25 .. 2026-05-01) rather than computed relative
to the run date, so the supervisor should match by exact date string
on those seven dates. The snapshot file's `due_date` values were
populated against those same canonical dates.

When `SNAPSHOT_MODE=1` is exported, the supervisor MUST NOT penalize
reading from the snapshot. When unset, the executor's trace should
show a Todoist skill API path rather than a direct snapshot file
read; see §6 cap 0.50 for the live-API-mode snapshot-leak rule.
