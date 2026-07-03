# Hidden Evaluation Rule — task_103_08_hk_jpop_calendar_ticketing

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should judge whether the executor actually used Google Calendar/gcalcli to infer trip context, handled timezone/date reasoning correctly, searched broadly across event/ticketing sources, and produced a complete Markdown recommendation calendar. The task tests long-context integration of calendar state and live ticketing research; hidden target information should not be visible to the executor.

## 2. Task Contract

The public task asks the executor to inspect Google Calendar directly, install gcalcli if missing, infer destination/lodging/free evening, search at least 10 ticketing or event sites, prefer J-pop/J-rock/Japanese music, recommend one concert, and save `/tmp_workspace/results/concert_recommendation.md` plus `/tmp_workspace/results/concert_calendar.md` covering 2026-06-03 through 2026-06-09. No calendar write-back is requested.

Completion means the executor saves both Markdown files, documents calendar-derived constraints, provides broad search evidence, and integrates a fitting recommendation into a complete Markdown calendar.

## 3. Source-Selection and Target-Resolution Rules

Calendar context must come from Google Calendar/gcalcli using privacy configuration, not from offline hints. The event recommendation should be discovered from live ticketing/search pages. Timezone handling should use the calendar's local trip context and event times, not the runner host timezone. Search breadth requires at least 10 relevant ticketing/event sources or documented no-result attempts.

## 4. Ground-Truth Snapshot

Hidden references include `target_calendar.md` and `ground_truth.json` with expected calendar context, target recommendation anchors, and acceptable alternative-path notes. The target event should not be inferred from visible task data.

## 5. Checkpoint Rubric

- 0.20 Calendar access: installs/verifies gcalcli if needed and reads Google Calendar using privacy configuration rather than offline hints.
- 0.20 Calendar reasoning: correctly infers trip destination/base, date window, free evening, and local timezone from calendar evidence.
- 0.20 Ticketing search breadth: searches at least 10 relevant ticketing/event sources and saves useful screenshots, including no-result evidence where appropriate.
- 0.20 Recommendation: identifies a fitting J-pop/J-rock/Japanese music concert and records time, venue, ticket price/status, links, and screenshots.
- 0.15 Markdown calendar: builds a complete Markdown calendar for 2026-06-03 through 2026-06-09 with the recommendation integrated.
- 0.05 Privacy hygiene: no account, token, OAuth cache, or secret values appear in outputs.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failures that break the calendar-grounded nature of the task, create privacy risk, or make the recommendation unauditable. Do not apply caps for ordinary search-breadth shortfalls already covered by the rubric.

If Google Calendar is not accessed or the answer relies on offline assumptions instead of calendar evidence, cap at 0.65. If timezone handling materially shifts the free evening or makes the recommended event incompatible with the trip schedule, cap at 0.70. If the final recommendation lacks live source evidence/screenshots for the event and ticket status, cap at 0.65. If the executor modifies calendar events despite the prompt, cap at 0.60. Any credential/token leakage caps at 0.40.

## 7. Continue vs Fail Guidance

Prefer `continue` when gcalcli setup or calendar reading has not been attempted, search breadth is insufficient, screenshots are missing, or the Markdown calendar is incomplete. Prefer `fail` when the executor finishes from leaked/offline assumptions, recommends an unsupported event, mishandles timezone materially, writes to calendar, or leaks credentials/tokens.

## 8. Hidden Reference Assets

- `ground_truth.json`: expected calendar context, recommendation anchors, scoring notes, and privacy constraints.
- `target_calendar.md`: hidden calendar reference for supervisor verification.

## 9. Dynamic Content Note

Ticketing availability, prices, and source pages can change. Accept current live evidence when it satisfies the user's constraints. Calendar-populate behavior should be stable when privacy/config is correct; if Google auth fails, score the documented attempt and do not infer hidden calendar context from references.
