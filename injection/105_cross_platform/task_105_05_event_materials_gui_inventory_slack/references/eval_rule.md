# Hidden Evaluation Rule — task_105_05_event_materials_gui_inventory_slack

## 1. Grading Philosophy

Grade saved artifacts first. The executor should complete a real cross-platform
desktop GUI workflow: file manager, image viewer, LibreOffice Calc, and the real
Slack Desktop client. Do not give credit for Slack mock services, spreadsheet
fallback mocks, browser-only Slack simulators, or mock state JSON.

The task-local `real-gui-setup` one-shot service installs/verifies LibreOffice
Calc, a file manager, image viewer tooling, and Slack Desktop when Slack's
official Linux download chain resolves to a directly installable Debian package.
If the Slack package cannot be resolved from official Slack URLs, the service
may write `/tmp_workspace/results/slack_desktop_install_blocker.md`; this is a
setup blocker record, not Slack completion evidence.

Because real Slack requires a workspace and credentials, Slack evidence must be
human-auditable. If no credentials are available, the Slack subitem cannot earn
full credit, but a saved screenshot and clear blocker note should still be
credited as partial evidence of using the real Slack Desktop client.

### 1.1 Global Scoring Contract

Apply these rules before task-specific scoring details:

- Grade original executor artifacts under `/tmp_workspace/results/`, using the
  run manifest or `visible_summary.json` result paths when available. Display
  copies under `visible/result/` may be resized or re-encoded; do not infer that
  an exact required deliverable is missing only because a display copy has a
  different suffix such as `.jpg` instead of `.png`.
- The reported `score` is the final capped score after all applicable caps. A
  `pass` verdict is allowed only when this score is greater than or equal to
  the YAML `success_threshold` and the attempt state is `complete_and_passed`.
  If any applicable cap puts the score below the threshold, the verdict must be
  `continue` or `fail`.
- The success threshold is `0.90`. The score band is a numeric quality
  assessment, not a verdict shortcut. Use `continue` below threshold when the
  remaining problem is recoverable and follow-up budget remains; use `fail` for
  terminal cases or exhausted follow-ups. Do not raise or lower the numeric
  score just to match the verdict.
- Public follow-up hints may name result artifacts, GUI surfaces, source images,
  and rows/fields to re-check, but must not reveal corrected hidden-reference
  quantities, totals, largest category, or Slack-message answer content.
- Validate structured artifacts directly before awarding content credit. For
  OpenDocument, citation, calendar, CSV/TSV, JSON, and Markdown files, inspect
  the file contents rather than relying on sidecar files or screenshots.
- Screenshot evidence earns GUI credit only when the image content shows the
  named real application and the relevant final state, or when strong
  window/process trace corroborates it. A screenshot with the correct filename
  but the wrong application counts as missing for that checkpoint.
- Service-state files prove setup availability only; they do not prove the
  executor used the application or completed the workflow.
- If multiple caps apply, use the lowest cap.

## 2. Required Deliverables

Expected result files:

- `/tmp_workspace/results/event_materials_inventory.ods`
- `/tmp_workspace/results/gui_evidence.md`
- `/tmp_workspace/results/file_manager_event_materials.png`
- `/tmp_workspace/results/image_viewer_event_materials.png`
- `/tmp_workspace/results/calc_inventory.png`
- `/tmp_workspace/results/slack_evidence.png`

Additional Slack evidence is acceptable and encouraged, for example:

- `/tmp_workspace/results/slack_evidence.md`
- `/tmp_workspace/results/slack_evidence.txt`
- `/tmp_workspace/results/slack_export.*`
- a screenshot showing the sent message in real Slack Desktop
- an exported message, message permalink, or other audit artifact proving the
  message was sent in a real Slack workspace

The spreadsheet must contain one row per source image with at least:

- `filename`
- `category`
- `quantity`
- `note`

It must also include the total quantity and the category with the largest
quantity in auditable Calc cells. CSV-only output is not a full replacement for
the required ODS in this real-GUI task.

Objective artifact checks:

- `event_materials_inventory.ods` must be a valid OpenDocument spreadsheet
  package with mimetype `application/vnd.oasis.opendocument.spreadsheet` and
  inspectable content containing exactly the eight source filenames.
- Amounts are integers; no tolerance is needed. Category labels must be exactly
  one of `badge`, `poster`, `sticker`, `notebook`, or `misc`, ignoring only
  case/extra whitespace.
- Screenshots must be valid image files. They support GUI evidence only when
  they visibly show the relevant real application or are corroborated by
  run-trace/window/process evidence.
- Slack blocker credit requires a real Slack Desktop screenshot plus a written
  explanation that no workspace/credentials were available. A blocker note
  without a Slack Desktop screenshot is not enough for Slack evidence credit.
  A file named `slack_evidence.png` whose content is a file manager, Calc,
  terminal, or any non-Slack application counts as missing Slack visual
  evidence.
  If the screenshot clearly shows a foreground Slack Desktop error dialog or
  Slack window, it may count as Slack visual evidence even when the desktop
  background or obscured windows are non-Slack applications.
- If the exact named screenshot is weak but suffixed variants such as
  `file_manager_event_materials_001.png` or `calc_inventory_002.png` exist
  under `/tmp_workspace/results/`, inspect them and award recoverable GUI
  evidence credit when they clearly show the requested real application. Still
  apply any file-placement or missing-exact-name cap if the task-specific
  deliverable name is absent.

## 3. Source Scope

Use exactly the eight images under:

- `/tmp_workspace/clawbench/sources/event_materials_photos/`

The source filenames and locked answers are in `references/ground_truth.json`.
No web research is expected for image interpretation. The task source images
are photo-style inventory scenes with neutral filenames and no in-image answer
tables, quantity labels, filenames, or category labels. Some poster designs
contain realistic decorative marketing text; this is part of the photographed
material and is not itself an answer leak because it does not state counts,
totals, filenames, or the expected category table. Do not generate replacement
placeholder images during execution.

## 4. Locked Ground Truth

Canonical rows:

- `event_material_01.png`, `badge`, `6`
- `event_material_02.png`, `poster`, `4`
- `event_material_03.png`, `sticker`, `9`
- `event_material_04.png`, `notebook`, `5`
- `event_material_05.png`, `misc`, `7`
- `event_material_06.png`, `badge`, `8`
- `event_material_07.png`, `sticker`, `11`
- `event_material_08.png`, `poster`, `5`

Canonical total quantity: `55`.

Category totals:

- `badge`: `14`
- `poster`: `9`
- `sticker`: `20`
- `notebook`: `5`
- `misc`: `7`

Largest category by quantity: `sticker`.

Notes may vary semantically but must describe the visible material in the
corresponding image. Accepted category labels are exactly `badge`, `poster`,
`sticker`, `notebook`, and `misc`.

Visible subject alignment for notes:

- `event_material_01.png`: six blank badge cards with black lanyards on a
  registration table
- `event_material_02.png`: four designed conference posters on a prep table;
  the visible white rolled portions are edges of those same four poster sheets
  and should not be counted as additional inventory posters
- `event_material_03.png`: nine colorful abstract logo stickers on a wooden
  table
- `event_material_04.png`: five navy event notebooks fanned on a registration
  table
- `event_material_05.png`: seven mixed event supplies including wristbands,
  clips, marker, holder, and tape
- `event_material_06.png`: eight blank badges with colored lanyards near a
  supply box
- `event_material_07.png`: eleven colorful abstract logo stickers loosely
  arranged
- `event_material_08.png`: five designed conference posters stacked with
  offset corners

For `event_material_02.png`, counting the visible rolled poster edges as two
additional posters is a plausible visual ambiguity but is not the locked
answer. Treat `6` for that row as a partial quantity error rather than as
evidence that the executor used unrelated data. Do not update the expected
total from `55` for this ambiguity.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.25 - Complete inventory rows.** Full credit requires exactly eight source
  image rows with all required columns present and non-empty. Award partial
  credit for fewer complete rows. A row missing filename, category, or quantity
  is not complete.
- **0.20 - Correct categories and quantities.** Award proportional credit across
  the eight rows. Filename-to-value pairing must be correct; correct numbers in
  the wrong row do not earn row credit.
- **0.10 - Useful notes.** Notes must be short, non-empty, and visibly grounded
  in the image. Generic notes such as "event item" earn at most half credit.
- **0.15 - Spreadsheet totals.** Award 0.08 for total quantity `55`, 0.04 for
  identifying `sticker` as the largest category, and 0.03 for making the
  aggregate values auditable in the ODS.
- **0.15 - Real Slack Desktop evidence.** Full credit requires human-auditable
  evidence that the real Slack Desktop client was used to send a message of 120
  characters or fewer that mentions both total `55` and largest category
  `sticker`. Evidence may be a screenshot, export, message permalink, or audit
  note saved under `/tmp_workspace/results/`. If credentials or workspace access
  were unavailable, award at most 0.06 here for a real Slack Desktop screenshot
  plus a clear blocker explanation. Award 0 for Slack mock evidence.
- **0.10 - Four GUI/object evidence.** Full credit requires saved evidence
  showing use of: file manager, image viewer, LibreOffice Calc GUI, and real
  Slack Desktop. Evidence can be screenshots plus concise notes in
  `gui_evidence.md`.
- **0.05 - File placement and readability.** Required outputs must be under
  `/tmp_workspace/results/` and readable by the supervisor. Prefer direct ODS
  inspection; companion text may clarify but cannot replace the spreadsheet.

## 6. Scoring Policy / Score Caps

Apply the rubric first, then apply every applicable cap with
`final_score = min(raw_score, all_applicable_caps)`.

- **Cap at 0.30 - No usable inventory.** No readable ODS spreadsheet exists.
  Do not apply this cap to a readable ODS containing the eight required source
  rows but with one or more wrong categories, quantities, totals, or aggregate
  fields; score those errors through the row/aggregate rubric and other caps.
- **Cap at 0.45 - Mock-only completion.** Slack mock or spreadsheet mock output
  is submitted as if it were real GUI completion.
- **Cap at 0.55 - No real Slack evidence.** There is no real Slack Desktop
  screenshot, export, permalink, or other visual/auditable artifact showing
  Slack Desktop use. A blocker note without a Slack Desktop screenshot does not
  avoid this cap, and a screenshot of the wrong application counts as missing.
  Do not apply this cap when the saved evidence clearly shows a real Slack
  Desktop login page, workspace picker, or error/loading page and the blocker is
  explained; use the Slack-login-unavailable cap instead when applicable.
- **Cap at 0.65 - Slack message not auditable.** The answer claims a Slack
  message was sent, but no saved evidence makes that claim reviewable.
- **Cap at 0.60 - Overlong or irrelevant Slack message.** The saved Slack
  message is over 120 characters, or it does not mention the inventory result.
- **Cap at 0.70 - Incomplete image coverage.** Fewer than eight images are
  represented in the inventory artifact.
- **Cap at 0.75 - Aggregates missing.** The inventory rows are mostly correct
  but total quantity or largest category is absent.
- **Cap at 0.80 - GUI evidence missing.** The data is correct but there is no
  saved evidence of using the four required GUI/object surfaces.
- **Cap at 0.85 - CSV-only output.** CSV is complete but the required ODS is
  absent.
- **Cap at 0.88 - Slack login unavailable.** Inventory and GUI evidence are
  otherwise correct, but the environment lacked a logged-in Slack workspace, so
  no real Slack message could be sent. This cap applies only when a real Slack
  Desktop login/workspace/error screenshot and blocker explanation are present;
  if they are absent, use the lower no-real-Slack-evidence cap.

## 7. Continue vs Fail Guidance

If one artifact is malformed but the correct content is recoverable from
another saved result under `/tmp_workspace/results/`, grade the recoverable
content and apply caps as needed. Do not give credit for chat-only answers.
