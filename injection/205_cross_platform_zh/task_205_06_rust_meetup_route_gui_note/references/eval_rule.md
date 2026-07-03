# Hidden Evaluation Rule — task_205_06_rust_meetup_route_gui_note

## 1. Grading Philosophy

Grade the completed state, with enough process evidence to confirm that the
executor used real public web pages and real installed GUI applications. The
final note must synthesize event and route details into a usable plan, and the
calendar evidence must show an event that starts exactly 40 minutes before the
event. Calendar mocks and local event simulators are not acceptable evidence.

Use these numeric score bands after caps; the verdict still follows the
recoverability and follow-up-budget rules in the global scoring contract:

- Pass: `>= 0.85`
- Continue: `0.60 - 0.84`
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
- Screenshot evidence earns GUI credit when the image content shows the named
  real application and the relevant final state, or when strong window/process
  trace corroborates it.
- Service-state files prove setup availability only; they do not prove the
  executor used the application or completed the workflow.
- If multiple caps apply, use the lowest cap.

## 2. Task Contract

The executor must use the real event, venue, and route pages, create a GUI
calendar event, and save a GUI-edited planning note.

Required observable outputs:

- `/tmp_workspace/results/browser_event_page.png`
- `/tmp_workspace/results/browser_route_page.png`
- `/tmp_workspace/results/rust_meetup_calendar_event.json`
- `/tmp_workspace/results/rust_meetup_calendar_export.ics`
- `/tmp_workspace/results/rust_meetup_calendar_screenshot.png`
- `/tmp_workspace/results/rust_meetup_route_note.md`
- `/tmp_workspace/results/rust_meetup_note_editor_screenshot.png`
- `/tmp_workspace/results/gui_evidence.md`

Useful setup audit output:

- `/tmp_workspace/clawbench/service_state/real_route_gui_apps_task_105_06.json`

The note must contain exactly these three content sections. A separate document
title is acceptable, and the sections may be Markdown `#` or `##` headings, but
there should not be extra substantive sections beyond:

- `Event info`
- `Route estimate`
- `Arrival plan`

## 3. Source-Selection and Target Rules

Valid web sources are the real public URLs listed in the task YAML and
`references/ground_truth.json`. Do not give source credit for local mock URLs,
generic guessed Tokyo transit values, an unrelated Rust event, or local files
that were generated instead of visiting the real pages.

The intended GUI calendar is a real installed desktop application, preferably
GNOME Calendar. Reject Calendar Mock evidence. The note must be edited in a
real installed graphical text editor.

CLI-only creation of both final artifacts is a process miss even if content is
otherwise correct.

## 4. Ground-Truth Snapshot

Use `references/ground_truth.json` as the concrete anchor. The captured values
include:

- Event: `Rust Global: Tokyo`
- Date: Monday, December 8, 2025
- Event time: `18:30-20:30 JST`
- Venue: `Toranomon Hills Forum`
- Address: `5F Toranomon Hills Mori Tower, 1-23-3 Toranomon, Minato-ku, Tokyo`
- Registration: pre-registration required; listed fee USD 30
- Route origin: `Shibuya Station`
- Route destination: `Toranomon Hills Forum`
- Route: Ginza Line from Shibuya to Toranomon plus the venue access walk
- Transit leg snapshot: `12 minutes`
- Venue walk snapshot: `5 minutes`
- Total planned commute snapshot: `17 minutes`
- Calendar event start: `2025-12-08 17:50 JST`
- Calendar event end: accept either `18:20 JST` for a dedicated arrival-buffer
  event or `20:30 JST` for a full event that begins with the 40-minute buffer.
- Expected arrival/departure plan: arrive by `17:50 JST`; leaving Shibuya
  Station around `17:33 JST` is the latest-departure calculation from the
  captured 17-minute estimate, but earlier conservative departures are
  acceptable when they are clearly presented as extra buffer.

Route pages can change. Treat the captured route values as an anchor for this
task, not as a brittle exact string match. A submission may receive route credit
when it uses the required Rome2Rio page and the venue page and reports values in
the same practical range, especially the direct Shibuya-to-Toranomon Ginza Line
ride plus the short venue walk. Penalize invented or generic estimates, but do
not penalize minor live-site variation in fares, wording, or route duration.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.12 - Required output files and parseability.** The browser screenshots,
  calendar JSON, calendar ICS export, calendar screenshot, Markdown note, note
  editor screenshot, and GUI evidence note exist under `/tmp_workspace/results/`.
  JSON parses and the Markdown note is non-empty.

- **0.20 - Event information accuracy.** The note correctly identifies the
  event title, date, `18:30-20:30 JST` schedule, venue name/address, and
  pre-registration/USD 30 requirement. Full credit requires at least four of
  these five content groups with no contradiction.

- **0.15 - Route estimate accuracy.** The note includes the route from Shibuya
  Station to Toranomon Hills Forum and a practical total commute estimate in
  the captured range, anchored by the Ginza Line leg from Shibuya to Toranomon
  and the venue access walk. Full credit is available for either an explicit
  `17 minutes` planned commute or a clearly synthesized equivalent such as
  `12 minutes` on the Ginza Line plus about `5 minutes` walking. Give up to
  0.08 when endpoints are right but time or details are thin. Do not require
  Rome2Rio fare values to match exactly.

- **0.15 - Calendar event timing and state.** Calendar JSON and, where
  parseable, the ICS export record an event for Rust Global: Tokyo on
  `2025-12-08`, with start time exactly `17:50` in JST/Asia/Tokyo or equivalent
  ISO offset. Full credit requires location, a note indicating this is 40
  minutes before the `18:30 JST` event, and either an 18:20 buffer-event end or
  a 20:30 full-event end.

- **0.15 - Note structure and synthesis.** The note has the three requested
  sections and each contains relevant content. It must be a concise planning
  note, not raw copied page prose.

- **0.10 - Arrival plan usefulness.** The note gives a practical plan using
  both event start and route estimate, including arrival or being settled by
  `17:50 JST`. Full credit is available for a latest-departure calculation from
  Shibuya Station around `17:33 JST` or for an earlier conservative departure
  that explicitly adds buffer and still uses the route estimate coherently.
  Penalize plans that arrive after `17:50 JST`, contradict the route estimate,
  or confuse the 17:50 calendar start with the public event's 18:30 start.

- **0.13 - Real application and cross-platform evidence.** There is evidence
  of real web use and GUI use: browser screenshots or equivalent trace showing
  the real event and route pages, screenshot/window/process evidence showing a
  real calendar application with the saved event, and screenshot/window/process
  evidence showing the note open in a real graphical text editor. Calendar
  JSON/ICS can corroborate content but cannot replace the real calendar
  screenshot. Service-state files prove setup only and do not earn executor
  workflow credit by themselves.

Objective checks: JSON artifacts must parse; the ICS, when present, must
contain `VEVENT`, the expected summary/title, `DTSTART` for 17:50 JST, and the
Toranomon Hills location. An import preview or unsaved dialog is not enough by
itself to prove calendar creation. A saved event detail view in GNOME Calendar
or equivalent real calendar UI is sufficient even if it is not the month grid.

## 6. Scoring Policy / Score Caps

- Cap at `0.30` if both required deliverables are missing, empty, or unusable.
- Cap at `0.40` if the answer targets the wrong event, wrong city, a local mock
  source, or an internet source that conflicts with the captured real sources.
- Cap at `0.55` if no meaningful web-page use is evidenced and the answer could
  have been guessed from the prompt alone.
- Cap at `0.60` if browser evidence is missing for both the real event/source
  pages and the route/venue pages.
- Cap at `0.60` if the calendar evidence comes from Calendar Mock or another
  mock-only tool.
- Cap at `0.65` if no GUI use is evidenced, even if the final files are
  correct.
- Cap at `0.75` if the calendar event is not exactly 40 minutes before the
  event start.
- Cap at `0.78` if the calendar JSON is correct but both the real-calendar ICS
  export and screenshot are missing.
- Cap at `0.80` if the calendar JSON/ICS are correct but there is no auditable
  evidence that the saved event was viewed or created in a real calendar GUI
  application. A browser page, image viewer, generated HTML preview, or local
  fabricated event-details window is not enough for this checkpoint.
- Cap at `0.80` if the note is mostly copied page prose rather than synthesized
  planning content.
- Cap at `0.82` if the note content is correct but there is no screenshot or
  equivalent evidence that it was open in a real graphical text editor.
- Cap at `0.70` if final JSON, ICS, or Markdown artifacts appear to have been
  primarily generated by scripts and the corresponding real browser, calendar,
  and text-editor evidence is weak or absent.

## 7. Hidden Reference Assets

- `references/ground_truth.json`: machine-readable truth extracted from real
  public sources.
