# Hidden Evaluation Rule — task_205_03_rust_tokyo_meetup_gui_calendar

## 1. Grading Philosophy

Judge the executor on a real public-web workflow and observable GUI outputs:

1. They used the real Rust Foundation / Linux Foundation pages as the event
   source, not a local mock page.
2. They created the event in a real desktop calendar GUI such as GNOME Calendar.
3. They saved auditable real-calendar evidence under `/tmp_workspace/results/`.
4. They wrote a concise Markdown summary at
   `/tmp_workspace/results/rust_global_tokyo.md`.

Use `references/ground_truth.json` as the captured factual anchor, while
allowing strong evidence from the official public pages if they changed.

### 1.1 Global Scoring Contract

- Grade original executor artifacts under `/tmp_workspace/results/`, using the
  run manifest or `visible_summary.json` result paths when available.
- The reported `score` is the final capped score after all applicable caps. A
  `pass` verdict is allowed only when this score is greater than or equal to
  the YAML `success_threshold` and the attempt state is `complete_and_passed`.
- The success threshold is `0.90`. The score band is a numeric quality
  assessment, not a verdict shortcut. Use `continue` below threshold when the
  remaining problem is recoverable and follow-up budget remains; use `fail` for
  terminal cases or exhausted follow-ups. Do not raise or lower the numeric
  score just to match the verdict.
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

## 2. Task Contract

- Open the real public Rust Foundation / Linux Foundation pages named in the
  task YAML.
- Extract the date, official time, venue, registration rule, and registration
  link for `Rust Global: Tokyo`.
- Use a real desktop calendar GUI, preferably GNOME Calendar, to create one
  calendar event whose title contains `Rust Global: Tokyo`.
- The calendar event must start 30 minutes before the official start and end at
  the event's official end time.
- Save a Markdown summary to `/tmp_workspace/results/rust_global_tokyo.md`.
- Save calendar evidence to `/tmp_workspace/results/calendar_evidence.json`
  plus a screenshot at `/tmp_workspace/results/calendar_gui.png` showing the
  saved event in the real calendar GUI. An ICS export at
  `/tmp_workspace/results/rust_global_tokyo.ics` is useful supporting evidence
  but is not a substitute for the GUI screenshot.

Calendar Mock state, a local HTTP event simulator, or pure script-only file
creation is not an acceptable substitute for the requested GUI evidence.

## 3. Source-Selection Rules

Valid factual sources are the real public pages listed in the task YAML and
`references/ground_truth.json`. Do not award source credit for local mock URLs,
a copied local fixture page, generic search snippets, or an unrelated Rust
event.

## 4. Ground-Truth Snapshot

Key captured values:

- Title: `Rust Global: Tokyo`
- Official date: December 8, 2025
- Official program time: 18:30-20:30 JST
- Required calendar start: `2025-12-08T18:00:00+09:00`
- Required calendar end: `2025-12-08T20:30:00+09:00`
- Time zone: `Asia/Tokyo` / JST
- Venue: `Toranomon Hills Forum, 5F, Toranomon Hills Mori Tower,
  1-23-3 Toranomon, Minato-ku, Tokyo 105-6305, Japan`
- Registration link:
  `https://register.linuxfoundation.org/event/rust-global-tokyo-2025/register`
- Registration rule: pre-registration is required; registration fee is USD 30.

Accept semantically equivalent time formats if the instant and time zone are
unambiguous. The calendar start must be 18:00 JST, not 18:30 JST.

## 5. Checkpoint Rubric

Weights sum to 1.00. Apply Section 6 caps after adding checkpoint credit.

- **0.15 - Real web source use and evidence.** Full credit requires evidence
  that the executor opened or read the real event/registration/venue pages and
  grounded facts in them. Award 0.08 if final facts match the public pages but
  source-use evidence is thin. Award 0.00 if the attempt uses a local mock.

- **0.20 - Event fact extraction accuracy.** Award up to 0.04 each for correct
  title/date, official time range, venue, registration rule, and registration
  link.

- **0.25 - Calendar event content.** Award 0.05 if
  `/tmp_workspace/results/calendar_evidence.json` exists and is parseable JSON;
  0.05 for title containing `Rust Global: Tokyo`; 0.07 for start time exactly
  30 minutes before official start (`18:00 JST` on December 8, 2025); 0.04 for
  correct end time (`20:30 JST`); 0.04 for a description, location, or notes
  field containing the venue plus registration link or registration rule.

- **0.10 - Real GUI calendar evidence.** Full credit requires a credible
  screenshot from a real desktop calendar GUI showing the saved event in a
  calendar view or event detail screen. An ICS export, backend store, or audit
  JSON can corroborate the screenshot, but cannot receive this credit by itself.
  If the desktop calendar displays times in a different system time zone, accept
  converted times only when JSON/ICS/backend evidence makes the JST instant
  unambiguous.

- **0.20 - Markdown deliverable.** Award 0.05 if
  `/tmp_workspace/results/rust_global_tokyo.md` exists and is readable; 0.05 if
  it identifies the event title and date; 0.05 if it summarizes time, venue,
  and registration requirements accurately; 0.05 if it is useful synthesis in
  the executor's own words.

- **0.10 - Cross-artifact consistency.** Calendar evidence, screenshot/export
  if available, and Markdown must agree on title, date/time, venue, and
  registration link.

## 6. Scoring Policy / Score Caps

- **Cap at 0.30 - No usable deliverable.** Neither required output exists, or
  outputs are saved only outside `/tmp_workspace/results/`.
- **Cap at 0.45 - Missing calendar evidence.** Markdown exists but
  `calendar_evidence.json` is missing or unparseable and there is no
  saved-event GUI screenshot proving the event.
- **Cap at 0.55 - Missing Markdown.** Calendar evidence exists but
  `rust_global_tokyo.md` is missing or empty.
- **Cap at 0.60 - Wrong source.** The answer is based on a local mock page,
  local mock URL, or unrelated event.
- **Cap at 0.70 - Wrong calendar timing.** The calendar title is correct but
  the start is not 30 minutes before the official start, or the end time is
  materially wrong.
- **Cap at 0.72 - Mock calendar used.** Evidence depends on Calendar Mock or a
  custom mock instead of a real desktop calendar GUI.
- **Cap at 0.75 - No saved-event GUI screenshot.** Correct JSON, ICS, backend
  store, or process traces exist, but there is no credible screenshot showing
  the saved event in a real desktop calendar GUI calendar view or event detail.
- **Cap at 0.75 - Pending import only.** GUI evidence shows an import preview
  but no saved event visible in a calendar view or event detail screen.
- **Cap at 0.80 - Markdown copied from source.** The Markdown deliverable is
  mostly pasted page prose and lacks useful synthesis.

## 7. Hidden Reference Assets

- `references/ground_truth.json`: captured event facts and expected output
  paths.

## 8. Dynamic Content Note

These are real public websites. If an executor documents an official-page
change after the capture date, grade against the current official page only
when the evidence is clear and the output remains internally consistent.
