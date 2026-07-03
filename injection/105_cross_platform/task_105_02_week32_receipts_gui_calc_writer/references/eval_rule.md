# Hidden Evaluation Rule — Week 32 Receipts via File Manager, Calc, and Writer

## 1. Grading Philosophy

Grade the saved results first, then the mechanism evidence. The executor must
extract the values from the six provided receipt images, build a spreadsheet in
a real LibreOffice Calc GUI workflow, and create a real LibreOffice Writer
summary document. Correct final artifacts matter most, but this task is
specifically a cross-platform GUI task, so a pure script that fabricates all
outputs without opening the file manager or image viewer, Calc, and Writer
workflow must be capped.

Do not require a specific sequence of clicks. Credit any normal desktop route
that visibly or transcript-wise uses a file manager or image viewer for the
receipts, LibreOffice Calc or `localc` for the spreadsheet, and LibreOffice
Writer or `lowriter` for the summary. Saved screenshots under
`/tmp_workspace/results/gui_evidence/` are preferred evidence, especially
`file_manager_or_receipts.png`, `calc_week32_expenses.png`, and
`writer_week32_summary.png`.

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
- The success threshold is `0.88`. The score band is a numeric quality
  assessment, not a verdict shortcut. Use `continue` below threshold when the
  remaining problem is recoverable and follow-up budget remains; use `fail` for
  terminal cases or exhausted follow-ups. Do not raise or lower the numeric
  score just to match the verdict.
- Public follow-up hints may name result artifacts, GUI surfaces, and source
  files/pages to re-check, but must not reveal corrected hidden-reference
  answers or exact hidden values.
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

## 2. Task Contract

The public task asks the executor to:

1. Open `/tmp_workspace/clawbench/sources/receipts/week_32/` with the desktop
   file manager or real image viewer and read six receipt images.
2. Use the local LibreOffice Calc GUI to create
   `/tmp_workspace/results/week32_expenses.ods`.
3. Use the local LibreOffice Writer GUI to create
   `/tmp_workspace/results/week32_summary.odt`.
4. Save a plain-text copy of the summary as
   `/tmp_workspace/results/week32_summary.txt`.
5. Save GUI screenshots under `/tmp_workspace/results/gui_evidence/`, including
   evidence for receipt review, Calc, and Writer.
6. Use the public category taxonomy exactly: `Groceries`, `Meals`, and
   `Transportation`.

Completion requires all three expected result files at the exact paths above.
Full GUI-mechanism credit also requires meaningful screenshot/process evidence.

## 3. Source Rules

The only receipt sources are the six JPG files under:

`/tmp_workspace/clawbench/sources/receipts/week_32/`

The executor may zoom, OCR, or manually transcribe from those images. It must
not invent extra receipts, use external receipt examples, or replace the
source images. The hidden `ground_truth.json` is for supervisor use only.

## 4. Ground Truth

Use `references/ground_truth.json` as the canonical answer. The values are:

| Date | Merchant | Category | Amount |
| --- | --- | --- | ---: |
| 2021-08-18 | 99 Cents Only Stores | Groceries | 23.17 |
| 2021-06-12 | Harpoon Harry's | Meals | 13.92 |
| 2025-01-04 | L'Oro Di Napoli | Meals | 52.45 |
| 2011-12-31 | Love's #207 | Transportation | 47.26 |
| 2007-02-18 | Shell | Transportation | 20.87 |
| 2012-01-02 | Smith's #190 | Transportation | 48.12 |

Overall total: `205.79`.

Category totals:

| Category | Amount |
| --- | ---: |
| Groceries | 23.17 |
| Meals | 66.37 |
| Transportation | 116.25 |

Highest spending category: `Transportation`, amount `116.25`.

Tolerate normal currency formatting such as `$20.87`, `20.87`, or `20.870`.
Dates may be ISO `YYYY-MM-DD` or an unambiguous local equivalent. Merchant and
category matching may ignore case and extra whitespace.

The receipt for `receipt_05.jpg` visibly contains both `NB OIL CO INC #1` and
`SHELL`; accept merchant strings that identify either the Shell brand, NB Oil,
or both. For categories, require the public taxonomy labels. `Transport` is an
acceptable abbreviation for `Transportation`, but semantically related labels
such as `Dining`, `Fuel`, `Gas`, or combined labels like `Groceries/Household`
do not match the required category labels.

## 5. Checkpoint Rubric

| ID | Observable result | Weight |
| --- | --- | ---: |
| CP1 | All three required result files exist at exactly `/tmp_workspace/results/week32_expenses.ods`, `/tmp_workspace/results/week32_summary.odt`, and `/tmp_workspace/results/week32_summary.txt`; each is non-empty. | 0.15 |
| CP2 | The spreadsheet contains exactly six receipt rows, one per source image, with usable columns for Date, Merchant, Category, and Amount. | 0.18 |
| CP3 | Receipt row data in the spreadsheet matches the six ground-truth date / merchant / category / amount tuples. Award partial credit for mostly correct rows; amount errors over 0.01 should count as wrong for that row. | 0.24 |
| CP4 | The spreadsheet includes correct calculations or summary cells for overall total `205.79`, all category totals, and highest category `Transportation` at `116.25`. | 0.15 |
| CP5 | The Writer ODT summary restates the week, the six receipts, the overall total, category totals, and the highest category. It should be independently readable without opening the spreadsheet. | 0.13 |
| CP6 | `week32_summary.txt` is a clean plain-text export/copy of the Writer summary and contains the same key totals and highest-category conclusion. | 0.07 |
| CP7 | GUI workflow evidence: saved screenshots, transcript, process/window evidence, or saved file metadata shows the executor used a real file manager or image viewer plus LibreOffice Calc and Writer GUI launchers. Full credit requires screenshots or similarly concrete evidence for receipt review, Calc, and Writer. | 0.08 |

Total: `1.00`.

## 6. Scoring Policy / Score Caps

Apply checkpoint weights first, then caps:

- Fail to `0.0` if no required result file exists.
- Cap at `0.40` if the run never uses the provided receipt images.
- Cap at `0.55` if the spreadsheet is missing or unusable, even if the text
  summary contains some correct values.
- Cap at `0.65` if the spreadsheet has fewer than six receipt rows.
- Treat a valid ODS package with no auditable receipt table, no six source rows,
  or no required totals as an unusable spreadsheet for CP2-CP4 and the `0.55`
  cap, even if CSV/TSV/TXT sidecars contain correct data. A valid ODS with only
  one to five receipt rows triggers the `0.65` cap.
- Cap at `0.70` if the ODS or ODT is a plain text, CSV, HTML, or renamed file
  rather than a valid LibreOffice/OpenDocument package.
- Cap at `0.75` if all outputs are generated by a pure command-line script or
  programmatic file writer with no credible GUI use of file manager/image
  viewer, Calc, and Writer.
- Cap at `0.80` if the ODS/ODT files are not valid LibreOffice documents but
  there is an auditable CSV/text sidecar containing the correct data. Sidecars
  cannot satisfy the real Calc/Writer deliverable requirement; still require
  evidence that the executor attempted the GUI workflow.
- Cap at `0.87` if totals are correct but one or two merchant/category/date
  fields are wrong or missing.
- Do not apply the `0.55` unusable-spreadsheet cap merely because an otherwise
  readable spreadsheet has wrong receipt values or wrong category labels. Use
  checkpoint partial credit and the data-error caps above for auditable but
  incorrect sheet content.
- Cap at `0.90` if the spreadsheet is correct but the Writer summary or text
  export is incomplete.
- Cap at `0.95` if the GUI evidence is weak but plausible, for example a
  transcript shows `libreoffice --calc` and `libreoffice --writer` launches but
  no file manager/image-viewer evidence.
- Award no CP7 credit for screenshots that are blank, unrelated, or created
  after the fact without showing the relevant applications or source receipts.

Do not penalize harmless formatting differences: currency symbols, column
order, extra notes, sorted rows, or additional formulas are acceptable if the
required facts are clear and correct.

## 7. Artifact Inspection Guidance

Validate the application artifacts, not just filenames:

- `week32_expenses.ods` should be a readable OpenDocument spreadsheet. It should
  contain `mimetype` with `application/vnd.oasis.opendocument.spreadsheet` and
  inspectable `content.xml` data, or it should open successfully in
  LibreOffice/`soffice --headless --convert-to`.
  The ODS `content.xml` or converted sheet content must itself contain the six
  receipt rows, Date/Merchant/Category/Amount fields, overall total `205.79`,
  all category totals, and highest category. Correct CSV/TSV sidecars may
  support audit, but they cannot satisfy CP2, CP3, or CP4 when the ODS lacks
  those values.
- `week32_summary.odt` should be a readable OpenDocument text document with
  `mimetype` equal to `application/vnd.oasis.opendocument.text` and inspectable
  summary text.
- Screenshot evidence should exist under `/tmp_workspace/results/gui_evidence/`
  or an equivalently named result path and should visibly show receipt review,
  Calc with the expense sheet, and Writer with the summary. Screenshots are
  supporting evidence; still grade the saved ODS/ODT/TXT content.
- The service state JSON
  `/tmp_workspace/clawbench/service_state/libreoffice-gui-setup.json` records
  package installation and launch checks for LibreOffice, the file manager, and
  image viewer. It helps explain environment failures but does not replace
  executor evidence.

## 8. Continue vs Fail Guidance

Prefer `continue` when:

- LibreOffice is still installing and the executor has not retried after the
  ready marker appears.
- One or more result files are missing but the executor is still actively
  editing or exporting.
- The spreadsheet exists but is missing the text summary/export.
- The totals are slightly inconsistent and follow-ups remain.

Prefer `fail` when:

- Follow-ups are exhausted and required result files are still missing.
- The executor used unrelated data instead of the shipped receipt images.
- The saved artifacts are empty, corrupt, or impossible to inspect and there is
  no auditable fallback.
- The executor refuses the GUI requirement and only submits script-generated
  artifacts.

Otherwise prefer `continue` if a targeted follow-up can likely recover the
missing artifact or correction.

## 9. Hidden Reference Assets

- `references/ground_truth.json`: canonical machine-readable receipt data,
  totals, category totals, highest category, and expected result paths.

The source receipt images are public to the executor but may also be inspected
by the supervisor to verify that the hidden ground truth matches the images.

## 10. Dynamic Content Note

This task is deterministic. The receipt images, expected totals, and output
paths do not depend on network state, locale, current date, or timezone.

The `services/libreoffice-gui-setup/install.sh` service installs LibreOffice
Calc/Writer, `pcmanfm`, `eog`, X11 helpers, and startup probes. It writes
`/tmp_workspace/clawbench/service_state/libreoffice-gui-ready` and structured
state at `/tmp_workspace/clawbench/service_state/libreoffice-gui-setup.json`.
The service is only setup support; do not award or remove points solely because
the marker exists. Grade the saved artifacts and GUI workflow evidence.
