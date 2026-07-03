# Hidden Evaluation Rule — task_105_04_rag_benchmark_gui_zotero_obsidian_calc

## 1. Grading Philosophy

Judge whether the executor completed a real desktop application workflow for the
ARES paper. The workflow covers a PDF reader or browser PDF viewer, Zotero,
Obsidian, and LibreOffice Calc. Do not award GUI-usage credit for local
substitute web applications or tools that merely imitate those desktop apps.

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
- The score band is a numeric quality assessment, not a verdict shortcut. Use
  `continue` below threshold when the remaining problem is recoverable and
  follow-up budget remains; use `fail` for terminal cases or exhausted
  follow-ups. Do not raise or lower the numeric score just to match the verdict.
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
- Treat file-content credit and screenshot/GUI credit as separate evidence
  streams. For example, a valid ODS can earn Calc content credit even when the
  Calc screenshot is unclear, but an unclear screenshot cannot earn the Calc GUI
  evidence credit; likewise, a clear Calc screenshot cannot replace direct ODS
  inspection for spreadsheet content.
- Service-state files prove setup availability only; they do not prove the
  executor used the application or completed the workflow.
- If multiple caps apply, use the lowest cap.

## 2. Task Contract

The executor must use:

- `/tmp_workspace/clawbench/sources/papers/ares_rag_evaluation.pdf`
- real Zotero
- real Obsidian
- real LibreOffice Calc

Expected artifacts:

- setup state, as supporting service evidence only:
  `/tmp_workspace/clawbench/service_state/task_105_04_real_apps_state.json`
- PDF reader evidence such as `pdf_reader_ares.png`
- Zotero evidence such as `zotero_ares_record.png`
- Zotero export such as `zotero_ares_record.bib` or `zotero_ares_record.ris`
- Obsidian evidence such as `obsidian_rag_benchmark_note.png`
- `RAG Benchmark Note.md` in an Obsidian vault or an exported equivalent
- `rag_benchmark_note_export.md`
- `rag_reading_tracker.ods`
- Calc evidence such as `calc_rag_reading_tracker.png`
- optional audit sidecar `rag_reading_tracker.csv`; it cannot replace the
  required ODS
- optional `gui_evidence.md` explaining which real desktop windows were used

## 3. Source and Ground Truth

The executor's only required paper source is the local PDF:

- `/tmp_workspace/clawbench/sources/papers/ares_rag_evaluation.pdf`

That local PDF was prepared from ACL Anthology. These URLs are provenance for
supervisors only; they do not create any live-download or live-web requirement
for the executor:

- paper page: `https://aclanthology.org/2024.naacl-long.20/`
- PDF: `https://aclanthology.org/2024.naacl-long.20.pdf`

The hidden file `references/ares_rag_evaluation_source_evidence.md` contains a
cleaned supervisor excerpt derived from the local PDF. It is not a public
source for the executor.

Use `references/ground_truth.json` as authoritative. Canonical facts:

- title: `ARES: An Automated Evaluation Framework for Retrieval-Augmented
  Generation Systems`
- authors: Jon Saad-Falcon; Omar Khattab; Christopher Potts; Matei Zaharia
- year: `2024`
- venue: `Proceedings of NAACL-HLT 2024, Volume 1: Long Papers`
- main task: automated evaluation of RAG systems using tailored LM judges
- metric dimensions: context relevance, answer faithfulness, answer relevance,
  with prediction-powered inference confidence intervals
- method: synthetic training data, fine-tuned lightweight LM judges, and a small
  human preference validation set
- evaluation scope: KILT, SuperGLUE, and AIS
- limitation: needs a small human validation set, domain expertise for some
  domains, substantial GPU resources, and was evaluated only on English datasets

## 4. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Required artifact placement/readability.** The PDF screenshot,
  Zotero screenshot/export, Obsidian screenshot/export, and Calc tracker
  artifacts are present under `/tmp_workspace/results/` and readable. The
  setup state JSON may support environment diagnosis but is not an executor
  deliverable and should not be required for this checkpoint.
- **0.15 - PDF reader evidence and source grounding.** The local PDF was opened
  or reviewed in a real PDF reader or browser PDF viewer; facts match ARES.
- **0.18 - Zotero record/export.** Real Zotero evidence plus BibTeX/RIS export
  show correct title, authors, year, venue, and PDF attachment or attachment
  path.
- **0.22 - Obsidian note/export.** Real Obsidian evidence plus Markdown export
  exist and include
  the required sections: `What task does it benchmark?`, `What metric matters
  most?`, and `One limitation`, answered with synthesis.
- **0.18 - LibreOffice Calc tracker.** ODS created with real LibreOffice Calc
  contains Title, Year, Main Task, Main Metric or Metric Dimensions, and Worth
  reading further. CSV sidecars can clarify audit details but cannot earn full
  ODS content credit when the ODS is missing or empty. Score the ODS contents by
  direct file inspection; score the Calc screenshot only as final-state GUI
  evidence.
- **0.09 - Cross-app consistency.** Zotero, note, export, and Calc agree.
- **0.08 - Real GUI usage evidence.** Credible screenshots, transcripts,
  process/window evidence, or file metadata cover the PDF reader, Zotero,
  Obsidian, and LibreOffice Calc.

### 4.1 Objective Artifact Inspection

Validate artifacts directly before awarding the corresponding credit:

- Zotero export: `.bib` or `.ris`, non-empty, contains the canonical title,
  at least three of four authors, year `2024`, the NAACL/ACL venue, and either
  an attachment path or the local PDF filename.
  Zotero attachment credit also requires same-record evidence in the screenshot,
  export, or Zotero database: the PDF must be tied to the target ARES parent
  item, not just present elsewhere in the filesystem.
- Obsidian note/export: Markdown text with the three required section headings
  and source-grounded answers for task, metric dimensions, and limitation.
  Obsidian GUI credit requires a screenshot showing the actual note title or
  required sections open in Obsidian. Startup screens, folder choosers, and empty
  vault screens do not prove the note was created in Obsidian.
- Calc tracker: `rag_reading_tracker.ods` should be a valid OpenDocument
  spreadsheet package with mimetype
  `application/vnd.oasis.opendocument.spreadsheet` and inspectable content
  containing title, year, task, metric dimensions, and a yes/no decision.
  Give content credit for a valid, inspectable ODS even if GUI evidence is weak;
  give GUI credit only when Calc visibly opens the sheet or trace evidence
  strongly supports real Calc use. For full Calc GUI screenshot credit, the
  screenshot should show real LibreOffice Calc with the tracker open and the
  A:E columns plus the filled data row visible enough to corroborate the saved
  spreadsheet. If the screenshot is cropped, wrapped, zoomed, or side-panel
  blocked so that the fifth column or data row cannot be audited, do not
  penalize the ODS content credit, but withhold the Calc screenshot/final-state
  GUI portion.
- Screenshots are valid GUI evidence only if they visibly show real desktop
  applications or are corroborated by process/window trace. A setup state JSON
  alone can earn setup credit but not GUI-usage credit.

## 5. Score Caps

- Cap at `0.30` if no usable deliverable exists.
- Cap at `0.45` if Zotero or note artifacts are missing.
- Cap at `0.55` if no spreadsheet artifact exists.
- Cap at `0.60` if no GUI evidence exists.
- Cap at `0.70` if fewer than three GUI objects are evidenced.
- Cap at `0.80` if the Obsidian Markdown content exists but no screenshot or
  trace shows the note open in real Obsidian.
- Cap at `0.82` if Zotero bibliographic metadata is mostly correct but the PDF
  attachment to the same Zotero item is not auditable.
- Cap at `0.70` if the workflow uses local substitute applications instead of
  real Zotero, Obsidian, and LibreOffice Calc.
- Cap at `0.78` if final Markdown, citation, and ODS artifacts appear to be
  generated directly by scripts and the corresponding real application final
  states are not visible, even when the file contents are mostly correct.
- Cap at `0.75` if there is no evidence from saved artifacts, screenshots,
  transcript, window/process trace, or service state that the required real
  applications were available or launched.
- Cap at `0.65` if the artifacts describe the wrong paper or stale synthetic
  BenchRAG facts.
- Cap at `0.80` if the main task, metric dimensions, or limitation are
  materially wrong.
- Cap at `0.75` if the note is mostly copied abstract text.

Pass is `>= 0.85`; continue is `0.60-0.84`; fail is `< 0.60`.

### 5.1 Feedback Targeting

When returning repair feedback, name the lowest-scoring missing requirement or
the lowest applicable cap. Do not describe Calc screenshot visibility as the
primary blocker if the active cap is the Zotero same-record attachment cap, and
do not imply that fixing a screenshot can cure missing structured artifact
content. If both ODS content and Calc screenshot evidence are flawed, state them
as separate issues.

## 6. Dynamic Content Note

This task is deterministic after the PDF is downloaded into sources. Do not
require live internet during execution.
