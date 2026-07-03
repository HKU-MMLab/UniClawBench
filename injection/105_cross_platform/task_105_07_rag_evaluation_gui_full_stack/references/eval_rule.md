# Hidden Evaluation Rule — task_105_07_rag_evaluation_gui_full_stack

## 1. Grading Philosophy

Judge whether the executor completed a five-GUI workflow for the real RAGAS
paper using real desktop applications: a PDF reader, Zotero, Obsidian,
LibreOffice Calc, and LibreOffice Writer. Do not award credit for the old local
GUI suite, a web mock, or substituting a generic browser tab for the requested
PDF reader checkpoint.

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
- Service-state files prove setup availability only; they do not prove the
  executor used the application or completed the workflow.
- If multiple caps apply, use the lowest cap.

## 2. Task Contract

The executor must use:

- `/tmp_workspace/clawbench/sources/papers/ragas_evaluation.pdf`

Expected artifacts:

- `/tmp_workspace/results/pdf_reader_screenshot.png` or equivalent PDF-reader evidence
- `/tmp_workspace/results/zotero_record_screenshot.png`
- `/tmp_workspace/results/zotero_record_export.bib`, `.ris`, or `.rdf`
- `/tmp_workspace/results/obsidian/RAG Evaluation Note.md`
- `/tmp_workspace/results/obsidian_note_screenshot.png`
- `/tmp_workspace/results/rag_evaluation_note_export.md`
- `/tmp_workspace/results/rag_reading_tracker.ods`
- `/tmp_workspace/results/calc_tracker_screenshot.png`
- `/tmp_workspace/results/rag_quick_judgment.odt`
- `/tmp_workspace/results/rag_quick_judgment.txt`
- `/tmp_workspace/results/writer_judgment_screenshot.png`
- `/tmp_workspace/results/real_gui_evidence.md` or equivalent GUI/process evidence

CSV/TXT sidecars can help inspection but do not replace the requested ODS/ODT
artifacts or the GUI evidence that those files were created/opened in real
LibreOffice.

## 3. Source and Ground Truth

The executor's only required paper source is the local PDF:

- `/tmp_workspace/clawbench/sources/papers/ragas_evaluation.pdf`

That local PDF was prepared from ACL Anthology. These URLs are provenance for
supervisors only; they do not create any live-download or live-web requirement
for the executor:

- paper page: `https://aclanthology.org/2024.eacl-demo.16/`
- PDF: `https://aclanthology.org/2024.eacl-demo.16.pdf`

The hidden file `references/ragas_evaluation_source_evidence.md` contains a
cleaned supervisor excerpt derived from the local PDF. It is not a public
source for the executor.

Use `references/ground_truth.json` as authoritative. Canonical facts:

- title: `RAGAS: Automated Evaluation of Retrieval Augmented Generation`
- authors: Shahul Es; Jithin James; Luis Espinosa-Anke; Steven Schockaert
- year: `2024`
- venue: `Proceedings of EACL 2024: System Demonstrations`
- main task: reference-free automated evaluation of RAG pipelines
- metric suite: faithfulness, answer relevancy, and context relevancy
- limitation: RAGAS relies heavily on evaluator LLMs and can be affected by LLM
  choice, randomness, API changes, and model suitability
- worth reading further: yes, because it provides practical reference-free
  metrics, a Python API, and integration value for RAG workflows

## 4. Checkpoint Rubric

Weights sum to 1.00.

- **0.12 - PDF reader evidence and source grounding.** Screenshot or process
  evidence shows the real RAGAS PDF was opened/reviewed in a real PDF reader
  application such as Evince, and facts match the PDF.
- **0.18 - Zotero record.** Real Zotero evidence shows correct title, authors,
  year, venue, and PDF attachment. Full credit requires a screenshot plus an
  inspectable export or saved Zotero evidence.
- **0.22 - Obsidian note/export.** Both files exist, match each other,
  and include `Main Task`, `Main Metric`, and `One Limitation` sections.
- **0.16 - LibreOffice Calc tracker.** ODS row includes title, year, main task,
  metric suite, and worth-reading decision; saved screenshot or equivalent
  evidence shows the tracker open in real LibreOffice Calc.
- **0.14 - LibreOffice Writer judgment.** ODT and TXT exist; judgment is <=80 Chinese
  characters or <=80 English words, states worth-reading decision, gives a
  PDF-grounded reason, and saved screenshot or equivalent evidence shows the
  judgment open in real LibreOffice Writer.
- **0.08 - Cross-app consistency.** All artifacts agree on title, year, metric
  suite, limitation, and worth-reading decision.
- **0.10 - Real GUI usage evidence.** Evidence covers all five real GUI
  applications and includes screenshots or process/window evidence.

### 4.1 Objective Artifact Inspection

Validate the saved files directly:

- Zotero export: acceptable extensions are `.bib`, `.ris`, and `.rdf`; the file
  must contain the canonical title, year `2024`, at least three authors, venue,
  and the local PDF filename or attachment path.
  JSON/TXT files may be useful audit sidecars but do not satisfy the Zotero
  export checkpoint unless the public task explicitly accepted them. Attachment
  credit requires the PDF to be tied to the same Zotero parent item.
- Obsidian note/export: both Markdown files must be readable text and include
  the `Main Task`, `Main Metric`, and `One Limitation` sections with facts that
  match `ground_truth.json`.
- Calc tracker: the ODS should be a valid OpenDocument spreadsheet package and
  include one row with title, year, task, metric suite, and worth-reading
  decision. CSV sidecars are content evidence only and cannot receive full Calc
  artifact credit.
- Writer judgment: the ODT should be a valid OpenDocument text package; the TXT
  copy must contain the same <=80-word/character judgment.
  Valid ODS/ODT files should receive content credit when their `content.xml`
  or extracted text is correct; do not dismiss them only because they are small.
  If the executor says the ODS or ODT was produced by headless LibreOffice,
  scripted conversion, or a hand-built OpenDocument zip, then opening it later
  in Calc or Writer can support GUI display evidence but does not satisfy the
  real-app save requirement for that file.
- Screenshots support GUI credit only if they are valid images and visibly show
  real desktop applications or are corroborated by run trace/window evidence.
  Obsidian screenshots must show the actual note, Calc screenshots must show
  the tracker sheet without a blocking error dialog, and Writer screenshots
  must show Writer with the judgment text. Startup screens, wrong applications,
  and blocking file-not-found dialogs do not earn the corresponding GUI credit.

## 5. Score Caps

- Cap at `0.30` if no required artifact is usable.
- Cap at `0.45` if real Zotero or Obsidian artifacts are missing.
- Cap at `0.55` if no spreadsheet artifact exists.
- Cap at `0.60` if Writer judgment is missing.
- Cap at `0.60` if no GUI evidence exists.
- Cap at `0.70` if fewer than three GUI objects are evidenced.
- Cap at `0.80` if fewer than all five GUI objects are evidenced.
- Cap at `0.78` if the Zotero record is not exported as `.bib`, `.ris`, or
  `.rdf`, even if JSON/TXT sidecars contain correct fields.
- Cap at `0.70` if the evidence comes from the removed web GUI suite or another
  mock instead of real desktop applications.
- Cap at `0.78` if most final files were directly generated by scripts,
  database writes, or hand-built OpenDocument archives and the final real-app
  screenshots do not show those files open in the corresponding applications.
- Cap at `0.86` if either required OpenDocument deliverable was primarily
  created by headless conversion, scripted conversion, or a hand-built
  OpenDocument archive rather than being created and saved through the
  corresponding LibreOffice GUI, even if the resulting file is valid and later
  displayed in the GUI. Use the stricter `0.78` cap above when this affects most
  final files or final-state screenshots are weak.
- Cap at `0.75` if CSV/TXT/Markdown sidecars contain the correct content but the
  required ODS or ODT deliverable is missing or unusable.
- Cap at `0.65` if artifacts describe the wrong paper or stale synthetic
  RAGEval facts.
- Cap at `0.80` if main task, metric suite, limitation, or worth-reading
  decision is materially wrong.
- Cap at `0.75` if the note is mostly copied abstract text.

Pass is `>= 0.87`; continue is `0.60-0.86`; fail is `< 0.60`.

## 6. Dynamic Content Note

This task is deterministic after the PDF is downloaded into sources. Do not
require live internet during execution.
