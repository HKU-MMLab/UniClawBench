# Hidden Evaluation Rule — task_105_08_event_materials_gui_full_stack

## 1. Grading Philosophy

Grade saved artifacts first. The executor should complete a cross-platform GUI
workflow with real desktop applications: file manager, image viewer,
LibreOffice Calc, LibreOffice Writer, and Slack Desktop. Correct inventory data
and auditable saved state matter more than prose, but pure scripted output
without credible GUI/object evidence must be capped.

The Slack target is real Slack Desktop, not a benchmark mock. A full-credit
Slack result requires credible evidence that a message was sent or prepared in
a logged-in Slack workspace/channel named `#social`. If no Slack credentials or
workspace are available, award only the limited evidence credit for launching
real Slack Desktop and documenting the blocker.

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
  quantities, totals, category totals, largest category, or Slack-message answer
  content.
- Validate structured artifacts directly before awarding content credit. For
  OpenDocument, citation, calendar, CSV/TSV, JSON, and Markdown files, inspect
  the file contents rather than relying on sidecar files or screenshots.
- Screenshot evidence earns GUI credit only when the image content shows the
  named real application and the relevant final state, or when strong
  window/process trace corroborates it. A screenshot with the correct filename
  but the wrong application counts as missing for that checkpoint. For Slack
  blocker evidence, a foreground Slack-labeled error dialog/window counts even
  if other applications are visible behind it; do not require an exclusive
  full-window Slack crop.
- Service-state files prove setup availability only; they do not prove the
  executor used the application or completed the workflow.
- If multiple caps apply, use the lowest cap.

## 2. Required Deliverables

Expected result files:

- `/tmp_workspace/results/event_materials_inventory.ods`
- `/tmp_workspace/results/event_materials_summary.odt`
- `/tmp_workspace/results/slack_desktop_evidence.png`
- `/tmp_workspace/results/slack_message_evidence.md`
- `/tmp_workspace/results/gui_evidence.md`

The spreadsheet must contain one row per source image with at least:

- `filename`
- `category`
- `quantity`
- `note`

It must also include the total quantity and the category with the largest
quantity in auditable spreadsheet cells. Companion CSV/TXT/Markdown sidecars can
help debugging, but cannot replace missing spreadsheet content.

The Writer summary must independently state the inventory list or a compact
equivalent, the total quantity, category totals, and the largest category.

Objective artifact checks:

- `event_materials_inventory.ods` must be a valid OpenDocument spreadsheet
  package with mimetype `application/vnd.oasis.opendocument.spreadsheet` and
  inspectable content containing exactly the eight source filenames. CSV is
  audit-only and cannot earn full spreadsheet-deliverable credit.
- `event_materials_summary.odt` must be a valid OpenDocument text package with
  mimetype `application/vnd.oasis.opendocument.text`. TXT is audit-only and
  cannot earn full Writer-deliverable credit.
- Quantities are integers; no tolerance is needed. Category labels must be
  exactly one of `badge`, `poster`, `sticker`, `notebook`, or `misc`, ignoring
  only case/extra whitespace.
- Screenshots must be valid image files. Slack blocker credit requires a real
  Slack Desktop screenshot plus a written explanation that no
  workspace/credentials were available.
  A `slack_desktop_evidence.png` file whose pixels show Thunar, Calc, Writer,
  a terminal, or any other non-Slack application is missing Slack visual
  evidence, even if the filename is correct. Hash-identical duplicates of
  non-Slack screenshots do not count as Slack evidence.
  If the screenshot clearly shows a foreground Slack Desktop error dialog or
  Slack window, it may count as Slack visual evidence even when the desktop
  background or obscured windows are non-Slack applications.
  The `0.88` Slack-login-unavailable cap applies only when there is real Slack
  Desktop visual evidence of the login/workspace/error state plus a written
  blocker explanation. If the real Slack screenshot is absent or wrong-app,
  apply the missing-Slack cap instead.

## 3. Source Scope

Use exactly the eight images under:

- `/tmp_workspace/clawbench/sources/event_materials_photos/`

The source filenames and locked answers are in `references/ground_truth.json`.
The shipped source directory contains only the eight neutral-name PNG images
that the executor should inspect. The current source images are task-local
photo-style inventory scenes, not the older flat benchmark placeholder PNGs.
They contain no answer tables, quantity labels, filenames, category labels, or
totals. Some poster designs contain realistic decorative marketing text; this
is part of the photographed material and is not an answer leak because it does
not state the expected inventory rows. No web research is expected for image
interpretation. Slack evidence should come from the real Slack Desktop client
installed by the task service; without workspace credentials, only the
documented-login-blocker path can receive partial Slack credit.

## 4. Locked Ground Truth

Canonical rows:

- `event_material_01.png`, `badge`, `6`, `six blank badge cards with black lanyards on a registration table`
- `event_material_02.png`, `poster`, `4`, `four designed conference posters on a prep table with visible rolled poster edges`
- `event_material_03.png`, `sticker`, `9`, `nine colorful abstract logo stickers on a wooden table`
- `event_material_04.png`, `notebook`, `5`, `five navy event notebooks fanned on a registration table`
- `event_material_05.png`, `misc`, `7`, `seven mixed event supplies including wristbands, clips, marker, holder, and tape`
- `event_material_06.png`, `badge`, `8`, `eight blank badges with colored lanyards near a supply box`
- `event_material_07.png`, `sticker`, `11`, `eleven colorful abstract logo stickers loosely arranged`
- `event_material_08.png`, `poster`, `5`, `five designed conference posters stacked with offset corners`

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

For `event_material_02.png`, the locked count is the four designed poster
sheets. The visible white rolled portions are edges of those same four poster
sheets and should not be counted as extra inventory posters. If an executor
counts that row as `6` posters, award only partial quantity credit for that row
instead of treating the whole inventory as unrelated, and keep the expected
total at `55`.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.20 - Complete inventory rows.** Full credit requires exactly eight source
  image rows with all required columns present and non-empty. Award partial
  credit for fewer complete rows. A row missing filename, category, or quantity
  is not complete.
- **0.20 - Correct categories and quantities.** Award proportional credit across
  the eight rows. Filename-to-value pairing must be correct; correct numbers in
  the wrong row do not earn row credit.
- **0.08 - Useful notes.** Notes must be short, non-empty, and visibly grounded
  in the image. Generic notes such as "event item" earn at most half credit.
- **0.12 - Spreadsheet totals.** Award 0.06 for total quantity `55`, 0.03 for
  identifying `sticker` as the largest category, and 0.03 for making aggregate
  values auditable in the ODS spreadsheet.
- **0.15 - Writer summary.** Full credit requires an ODT that restates the
  eight-image inventory, total `55`, all category totals, and largest category
  `sticker`. TXT/Markdown sidecars may corroborate content but cannot replace
  the ODT.
- **0.12 - Real Slack Desktop evidence.** Full credit requires a screenshot or
  other credible evidence from real Slack Desktop targeting `#social`, with a
  message of 120 characters or fewer that mentions both total `55` and largest
  category `sticker`. If Slack is not logged in, award at most 0.04 for
  launching real Slack Desktop and documenting the credential/workspace blocker.
- **0.08 - Five GUI/object evidence.** Full credit requires `gui_evidence.md`
  or equivalent saved evidence showing use of: file manager, image viewer,
  LibreOffice Calc, LibreOffice Writer, and real Slack Desktop.
- **0.05 - File placement and readability.** Required outputs must be under
  `/tmp_workspace/results/` and readable by the supervisor. ODS/ODT are required;
  CSV/TXT sidecars are audit-only.

## 6. Scoring Policy / Score Caps

Apply the rubric first, then apply every applicable cap with
`final_score = min(raw_score, all_applicable_caps)`.

- **Cap at 0.30 - No usable inventory.** No readable ODS spreadsheet exists.
  Do not apply this cap to a readable ODS containing the eight required source
  rows but with one or more wrong categories, quantities, totals, category
  totals, or aggregate fields; score those errors through the row/aggregate
  rubric and other caps.
- **Cap at 0.45 - Missing Writer summary.** No readable ODT summary exists.
- **Cap at 0.50 - Missing Slack evidence.** No Slack Desktop screenshot or
  message evidence is saved, or the saved Slack screenshot shows the wrong
  application rather than Slack Desktop/login/workspace/error state.
- **Cap at 0.60 - Wrong Slack target.** The saved message is not targeted at
  `#social`.
- **Cap at 0.60 - Overlong or irrelevant Slack message.** The message is over
  120 characters, or it does not mention the inventory result.
- **Cap at 0.70 - Incomplete image coverage.** Fewer than eight images are
  represented in the inventory artifact.
- **Cap at 0.75 - Aggregates missing.** The inventory rows are mostly correct
  but total quantity or largest category is absent.
- **Cap at 0.80 - GUI evidence missing.** The data is correct but there is no
  saved evidence of using the five required GUI/object surfaces.
- **Cap at 0.75 - CSV/TXT-only sidecars.** CSV, TXT, Markdown, or other sidecars
  are complete, but the required ODS or ODT deliverable is missing.
- **Cap at 0.88 - Slack login unavailable.** Inventory and office artifacts are
  otherwise correct, but the environment lacked a logged-in Slack workspace, so
  no real `#social` message could be sent, and a real Slack Desktop
  login/workspace/error screenshot plus blocker explanation are present. If the
  screenshot is missing or not Slack, use the lower missing-Slack cap.
- **Cap at 0.70 - Mock Slack or mock office used.** The evidence comes from the
  removed local mock/fallback services instead of real desktop applications.
- **Cap at 0.70 - Script-substituted office workflow.** The ODS/ODT or sidecar
  artifacts appear to have been primarily generated by scripts and the
  corresponding real Calc/Writer screenshots are weak or absent.
- **Cap at 0.90 - Weak Writer summary.** The inventory and Slack outputs are
  correct but the Writer summary omits either category totals or the largest
  category.

## 7. Continue vs Fail Guidance

Prefer `continue` when:

- LibreOffice is still installing and the executor has not retried after the
  ready marker appears.
- One or more result files are missing but the executor is still actively
  editing or exporting from real LibreOffice.
- The spreadsheet exists but the required Writer summary or Slack evidence is
  missing.
- Totals are slightly inconsistent and follow-ups remain.

Prefer `fail` when:

- Follow-ups are exhausted and required result files are still missing.
- The executor used unrelated data instead of the shipped source images.
- Saved artifacts are empty, corrupt, or impossible to inspect.
- The executor refuses the GUI requirement and only submits script-generated
  artifacts.

Otherwise prefer `continue` if a targeted follow-up can likely recover the
missing artifact or correction.

## 8. Dynamic Content Note

This task is deterministic. The image contents, expected totals, and output
paths do not depend on network state, locale, current date, or timezone.

The task-local setup service installs LibreOffice Calc/Writer, file/image GUI
helpers, and Slack Desktop when absent, then writes
`/tmp_workspace/clawbench/service_state/real_event_gui_apps_task_105_08.json`.
Grade the saved artifacts and real GUI/object evidence, not the marker alone.
