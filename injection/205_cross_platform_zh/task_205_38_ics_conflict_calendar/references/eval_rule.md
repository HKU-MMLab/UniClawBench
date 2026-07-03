# Hidden Evaluation Rule — task_205_38_ics_conflict_calendar

## 1. Grading Philosophy

Grade from `parsed_schedule.json`, `planning_week_schedule.ics`,
`planning_week_report.md`, calendar screenshot/tool evidence, and
`ground_truth.json`.

## 2. Task Contract

Required outputs:
- `/tmp_workspace/results/parsed_schedule.json`
- `/tmp_workspace/results/planning_week_schedule.ics`
- `/tmp_workspace/results/planning_week_report.md`
- `/tmp_workspace/results/planning_week_calendar.png`

## 3. Checkpoint Rubric

Checkpoints, total 1.00:
- 0.12 Required outputs and parseability: all files exist, JSON parses,
  and ICS contains six VEVENTs.
- 0.28 Scheduling correctness: each requested meeting is scheduled at
  the expected first feasible candidate slot, with exact title, date,
  start/end time, duration, and timezone semantics.
- 0.16 Conflict avoidance: no scheduled VEVENT overlaps the provided
  Alice/Bruno busy blocks or another scheduled meeting for the same
  attendee; impossible/blocked first candidates are explained.
- 0.10 Near-conflict reporting: JSON/report includes a hard_conflicts
  array and near_conflicts array, even if empty, and flags the expected
  edge case or explains a reasonable no-near-conflict policy.
- 0.10 ICS quality: valid VCALENDAR with UID, SUMMARY, DTSTART, DTEND,
  DESCRIPTION or ATTENDEE information, and America/Los_Angeles
  timezone-preserving values.
- 0.10 Calendar GUI evidence: screenshot is a valid PNG from a real
  calendar GUI after opening/importing the generated ICS, or transcript
  shows a credible import/open attempt plus screenshot.
- 0.08 Report quality: report lists source calendars used, selected
  timezone, scheduled meetings, skipped candidate reasons, and
  validation result.
- 0.06 Cross-artifact consistency between JSON, ICS, and report.

## 4. Scoring Policy / Score Caps

Caps:
- Cap at 0.55 if no parseable ICS is saved.
- Cap at 0.70 if one or more scheduled meetings overlap a known busy
  block.
- Cap at 0.80 if scheduling content is correct but no calendar GUI
  screenshot/evidence is present.
- Cap at 0.60 if timezone conversion is ignored or dates drift outside
  the requested week.
