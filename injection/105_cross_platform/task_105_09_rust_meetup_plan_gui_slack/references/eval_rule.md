# Hidden Evaluation Rule — task_105_09_rust_meetup_plan_gui_slack

## 1. Grading Philosophy

Grade saved artifacts and process evidence. The executor must combine real
public web pages with real GUI applications: event page, venue/route pages,
registration page, real desktop calendar, real GUI text editor, and real Slack
Desktop. `references/ground_truth.json` is the captured factual anchor, but an
executor may receive credit for official-page changes when they provide clear
evidence.

Use these numeric score bands after caps; the verdict still follows the
recoverability and follow-up-budget rules in the global scoring contract:

- Pass: `>= 0.90`
- Continue: `0.60 - 0.89`
- Fail: `< 0.60`

### 1.1 Global Scoring Contract

- Grade original executor artifacts under `/tmp_workspace/results/`, using the
  run manifest or `visible_summary.json` result paths when available.
- The reported `score` is the final capped score after all applicable caps. A
  `pass` verdict is allowed only when this score is greater than or equal to
  the YAML `success_threshold` and the attempt state is `complete_and_passed`.
- The score band is a numeric quality assessment, not a verdict shortcut. Use
  `continue` below threshold when the remaining problem is recoverable and
  follow-up budget remains; use `fail` for terminal cases or exhausted
  follow-ups. Do not raise or lower the numeric score just to match the verdict.
- Public follow-up hints may name result artifacts, GUI surfaces, and source
  files/pages to re-check, but must not reveal corrected hidden-reference
  answers or exact hidden values.
- Validate structured artifacts directly before awarding content credit.
- Screenshot evidence earns GUI credit only when the image content shows the
  named real application and the relevant final state, or when strong
  window/process trace corroborates it.
- Service-state files prove setup availability only; they do not prove the
  executor used the application or completed the workflow.
- If multiple caps apply, use the lowest cap.

## 2. Required Deliverables

Expected result files:

- `/tmp_workspace/results/browser_event_page.png`
- `/tmp_workspace/results/browser_route_page.png`
- `/tmp_workspace/results/rust_meetup_plan_calendar_event.json`
- `/tmp_workspace/results/rust_meetup_plan_5p.md`
- `/tmp_workspace/results/note_editor_plan_screenshot.png`
- `/tmp_workspace/results/rust_meetup_plan_calendar_export.ics`
- `/tmp_workspace/results/rust_meetup_plan_calendar_screenshot.png`
- `/tmp_workspace/results/slack_desktop_evidence.png`
- `/tmp_workspace/results/slack_message_evidence.md`
- `/tmp_workspace/results/gui_evidence.md`

Useful setup audit file:

- `/tmp_workspace/clawbench/service_state/real_plan_gui_apps_task_105_09.json`

The note must have exactly these three top-level sections:

- `Event info`
- `Route estimate`
- `Arrival plan`

## 3. Source and Target Rules

Valid web sources are the real public URLs listed in the task YAML and
`references/ground_truth.json`. Do not award source credit for local mock URLs,
a local Slack-style/event-site simulator, generic guessed transit values, or
unrelated Rust events.

Intended GUI targets:

- Real desktop calendar app installed by setup service
- Real GUI note editor installed by setup service
- Real Slack Desktop installed by setup service

CLI-only creation of all final artifacts is a process miss even if content is
otherwise correct.

## 4. Locked Ground Truth

Key captured values:

- Event: `Rust Global: Tokyo`
- Date: `2025-12-08`
- Timezone: `Asia/Tokyo`
- Event time: `2025-12-08T18:30:00+09:00` to
  `2025-12-08T20:30:00+09:00`
- Required calendar start: `2025-12-08T17:50:00+09:00`
- Venue: `Toranomon Hills Forum, 5F Toranomon Hills Mori Tower,
  1-23-3 Toranomon, Minato-ku, Tokyo`
- Registration URL:
  `https://register.linuxfoundation.org/event/rust-global-tokyo-2025/register`
- Registration rule: pre-registration required; listed fee USD 30
- Route origin: `Shibuya Station`
- Route destination: `Toranomon Hills Forum`
- Route duration: `17 minutes` planned commute
- Route detail: Ginza Line Shibuya to Toranomon plus about 5 minutes walking
  from Toranomon Station Exit 1 to the venue
- Arrival plan: leave Shibuya Station around `17:33` and arrive around `17:50`
- Slack channel: `#social`
- Slack message limit: `120` characters

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.12 - Required output files and parseability.** All required result files
  exist under `/tmp_workspace/results/`; JSON files parse; the Markdown note and
  Slack evidence text are non-empty; screenshots are valid images.

- **0.13 - Event information accuracy.** The note correctly identifies the
  title, date, `18:30-20:30 JST` schedule, venue/address, registration URL, and
  pre-registration/USD 30 requirement. Full credit requires at least five of
  these six content groups with no contradiction.

- **0.14 - Route estimate accuracy.** The note includes the route from Shibuya
  Station to Toranomon Hills Forum and the `17 minutes` planned commute. Full
  credit includes the Ginza Line leg and 5-minute Toranomon Station venue walk.

- **0.11 - Calendar event timing and state.** The calendar JSON and either
  screenshot or ICS export record an event for `Rust Global: Tokyo` on
  `2025-12-08`, with start time exactly `17:50` in JST/Asia-Tokyo or equivalent
  ISO offset. Full credit requires end time `20:30`, the venue, registration
  link or requirement, and a note indicating this is 40 minutes before the
  `18:30 JST` event.

- **0.14 - Note structure and synthesis.** The Markdown note has exactly the
  three requested top-level sections and each has relevant content. It must be
  a concise planning note rather than raw copied page prose.

- **0.10 - Arrival plan usefulness.** The note gives a practical plan using the
  event start and route estimate, including arrival before or around
  `17:50 JST` and departure from Shibuya Station around `17:33 JST`.

- **0.12 - Real Slack Desktop evidence.** `slack_desktop_evidence.png` and
  `slack_message_evidence.md` show real Slack Desktop targeting `#social`, with
  message length `<= 120` and content relevant to the event time, venue, route,
  or arrival plan. If no Slack workspace credentials are available, award at
  most 0.04 here for launching real Slack Desktop and documenting the blocker.
  This documented-blocker path requires a direct screenshot of the real Slack
  Desktop window showing the login, workspace-selection, or error state. A
  screenshot of Calendar, an image viewer, terminal, browser, or any other
  non-Slack application is missing Slack visual evidence even when its titlebar,
  taskbar, filename, or sidecar log mentions Slack.
  If the screenshot clearly shows a foreground Slack Desktop error dialog or
  Slack window, it may count as Slack visual evidence even when the desktop
  background or obscured windows are non-Slack applications; do not require an
  exclusive full-window Slack crop for the documented-blocker path.

- **0.14 - Web plus GUI evidence.** Full credit requires evidence of real web
  use for the event, venue/route, and registration pages, plus GUI evidence
  from the real calendar app, note editor, and real Slack Desktop. Browser
  screenshots should show real public pages rather than local mirrors or copied
  text. The calendar screenshot and note-editor screenshot carry the GUI
  workflow credit; JSON/ICS/Markdown files can corroborate content but cannot
  replace those screenshots.

Objective checks: calendar JSON must parse and include title, start, end,
timezone or offset, location, and registration link/requirement. The ICS, when
present, must contain `VEVENT`, `DTSTART` for 17:50 JST, `DTEND` for 20:30 JST,
and the Toranomon Hills location. Slack blocker credit requires both a real
Slack Desktop screenshot and an explicit explanation in
`slack_message_evidence.md`; login-blocker evidence cannot receive full Slack
credit. An import preview or unsaved calendar dialog is not enough by itself to
prove calendar creation.

## 6. Scoring Policy / Score Caps

- Cap at `0.30` if two or more required deliverables are missing, empty, or
  unreadable.
- Cap at `0.40` if the work targets the wrong event, wrong city, a local mock
  source, or public sources that conflict with the captured event without
  evidence of official-page drift.
- Cap at `0.55` if no meaningful real web-page use is evidenced and the answer
  could have been guessed from the prompt alone.
- Cap at `0.60` if browser evidence is missing for both the real event/source
  pages and the route/venue pages.
- Cap at `0.65` if no GUI use is evidenced, even if the final files are correct.
- Cap at `0.75` if the calendar event does not start exactly 40 minutes before
  the event start.
- Cap at `0.75` if Slack evidence is missing, targets the wrong channel, or has
  a message over 120 characters.
- Cap at `0.80` if the note is mostly copied page prose rather than synthesized
  planning content.
- Cap at `0.85` if the note lacks one of the three required sections.
- Cap at `0.82` if the note content is correct but there is no screenshot or
  equivalent evidence that it was open in a real graphical text editor.
- Cap at `0.88` if Slack login/workspace is unavailable and therefore no real
  `#social` message can be sent, even if all other artifacts are correct. This
  cap applies only when `slack_desktop_evidence.png` visibly shows the real
  Slack Desktop login/workspace/error state and `slack_message_evidence.md`
  explains the blocker.
- If the Slack screenshot is absent, unreadable, or shows Calendar, an image
  viewer, terminal, browser, or any other non-Slack application, use the lower
  `0.75` missing-Slack cap. Sidecar logs, process titles, or screenshots viewed
  inside another application do not avoid this lower cap.
  A foreground Slack-labeled error dialog/window counts as Slack visual evidence
  for this rule even if a Calendar or browser window is visible behind it.
- Cap at `0.70` if the executor uses Calendar Mock, Slack Mock, or any local
  Slack-style/event-site simulator as primary evidence.
- Cap at `0.70` if final calendar, note, or Slack audit artifacts appear to have
  been primarily generated by scripts and the corresponding real browser,
  calendar, text-editor, and Slack Desktop evidence is weak or absent.

## 7. Hidden Reference Assets

- `references/ground_truth.json`: captured event and route facts.
