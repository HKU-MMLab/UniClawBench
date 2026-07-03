# Hidden Evaluation Rule — task_105_01_rag_survey_gui_zotero_obsidian

## 1. Grading Philosophy

Judge whether the executor completed a GUI workflow from the real local PDF into
the real Zotero and Obsidian desktop applications. The result must be grounded
in the downloaded paper `Retrieval-Augmented Generation for Large Language
Models: A Survey`, not in generic RAG knowledge, a web mock, or the previous
synthetic fixture.

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

The executor must inspect:

- `/tmp_workspace/clawbench/sources/rag_survey_pack/rag_survey.pdf`

and use:

- a visible PDF reader or browser PDF viewer
- the real Zotero desktop app installed by the setup service
- the real Obsidian desktop app installed by the setup service

Required outputs:

- `/tmp_workspace/results/rag_survey_note_export.md`
- `/tmp_workspace/results/zotero_rag_survey_export.bib` or an equivalent Zotero
  export with the same base name and a standard citation extension such as
  `.bib`, `.ris`, or `.rdf`
- `/tmp_workspace/results/pdf_reader_screenshot.png`
- `/tmp_workspace/results/zotero_record_screenshot.png`
- `/tmp_workspace/results/obsidian_note_screenshot.png`

Useful setup evidence is written by the service to:

- `/tmp_workspace/clawbench/service_state/zotero-obsidian-ready.json`

Do not require this service-state file from the executor, but use it as
supporting evidence that real applications were made available.

## 3. Source Selection

The executor's only required paper source is the local PDF:

- `/tmp_workspace/clawbench/sources/rag_survey_pack/rag_survey.pdf`

That local PDF was prepared from arXiv. These URLs are provenance for
supervisors only; they do not create any live-download or live-web requirement
for the executor:

- paper page: `https://arxiv.org/abs/2312.10997`
- PDF source: `https://arxiv.org/pdf/2312.10997`

The hidden reference file `references/rag_survey_source_evidence.md` is a
cleaned audit/accessibility aid for supervisors. It is not a public source for
the executor and does not replace visible PDF/GUI evidence.

## 4. Locked Ground Truth

Use `references/ground_truth.json` as authoritative. Key facts:

- title: `Retrieval-Augmented Generation for Large Language Models: A Survey`
- authors: Yunfan Gao; Yun Xiong; Xinyu Gao; Kangxiang Jia; Jinliu Pan; Yuxi
  Bi; Yi Dai; Jiawei Sun; Meng Wang; Haofen Wang
- year: `2024`
- venue/id: `arXiv preprint arXiv:2312.10997v5`
- citation key: `gao2024retrieval`
- survey objective: systematically review RAG for LLMs, including paradigms,
  retrieval, generation, augmentation, evaluation, challenges, and future work
- organization: Naive RAG, Advanced RAG, Modular RAG
- scope: over 100 RAG studies, 26 tasks, nearly 50 datasets
- evaluation dimensions include context relevance, answer faithfulness, answer
  relevance, noise robustness, negative rejection, information integration, and
  counterfactual robustness
- challenges include retrieval quality, noisy/irrelevant context, context
  compression, long-context LLM tradeoffs, multimodal expansion, and immature
  or non-standardized RAG evaluation metrics

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Required artifacts.** The Markdown note, Zotero export, and three
  screenshots exist, are non-empty, and are readable.
- **0.12 - Real GUI workflow evidence.** Screenshots or equivalent evidence show
  visible PDF/browser PDF use, real Zotero desktop use, real Obsidian desktop
  use, and saved/exported artifacts. Award little or no credit here for web
  mocks, mock state JSON, or script-only artifacts.
- **0.14 - Zotero record/export.** The Zotero export contains the correct title,
  authors, year, venue/arXiv ID, citation key, relevant tags or keywords, and a
  useful PDF-grounded summary/abstract when the export format supports it.
- **0.12 - Obsidian note structure.** Markdown has metadata/front matter or
  equivalent, links to the same citation key, lives in or is exported from the
  requested Obsidian vault, and is readable as a literature note.
- **0.16 - Survey content accuracy.** Correctly explains the objective, Naive /
  Advanced / Modular RAG organization, and retrieval/generation/augmentation
  framing.
- **0.12 - Evaluation coverage.** Mentions the survey's evaluation discussion,
  including 26 tasks, nearly 50 datasets, and at least three evaluation
  dimensions from ground truth.
- **0.08 - Challenges/limitations.** Identifies at least three source-grounded
  RAG challenges.
- **0.10 - RAG evaluation-plan synthesis.** Connects the survey to a practical
  RAG evaluation plan, such as tracking context relevance, faithfulness, answer
  relevance, robustness, and separate retrieval/generation components.
- **0.06 - Cross-artifact consistency.** Zotero export, Obsidian note/export,
  and screenshots agree on title, citation key, and core facts.

### 5.1 Objective Artifact Inspection

Use deterministic file checks before assigning content credit:

- A Zotero export is acceptable only if its extension is `.bib`, `.ris`, or
  `.rdf`, it is non-empty text/XML, and it contains the canonical title,
  arXiv ID `2312.10997`, year `2024`, and at least six of the ten authors.
- The Markdown note must be plain text with the canonical title or citation key
  and at least four paper-grounded sections or headings covering objective,
  paradigms/components, evaluation, challenges, and evaluation-plan use.
- Screenshots should be valid image files. They support GUI/process credit only
  when they visibly show real PDF/Zotero/Obsidian windows or are corroborated by
  the run trace/window/process evidence.
- A PDF screenshot that shows only viewer chrome or blank page areas earns at
  most partial PDF-viewer credit, even if the path is correct. It can still be
  corroborated by other screenshots or trace evidence showing that the supplied
  local PDF was opened and read.
- Zotero attachment credit requires same-record evidence: a visible attached
  PDF child row, nonzero attachment count, a Zotero database/export file link
  tied to the same parent item, or another auditable proof that the local PDF is
  attached to the target paper record. A screenshot showing `0 Attachments` is
  negative evidence and cannot receive attachment credit.
- Obsidian screenshot credit requires the opened note title or note content to
  be visible. Startup pages, vault pickers, empty panes, or unrelated notes do
  not prove the requested note was created in Obsidian.
- The service state JSON may prove that Zotero/Obsidian were installed, but it
  does not prove the executor used them.

## 6. Score Caps

Apply rubric first, then every relevant cap.

- Cap at `0.30` if no required artifact is usable.
- Cap at `0.55` if `rag_survey_note_export.md` is missing or not a literature
  note.
- Cap at `0.70` if the Zotero export is missing or unusable.
- Cap at `0.82` if Zotero bibliographic fields are mostly correct but there is
  no auditable proof that the local PDF is attached to the same Zotero record.
- Cap at `0.68` if there is no real GUI evidence.
- Cap at `0.50` if the submitted evidence relies on the old local web mock or
  mock state JSON instead of real Zotero/Obsidian.
- Cap at `0.60` if the work is not based on the supplied PDF.
- Cap at `0.72` if more than two bibliographic fields are wrong.
- Cap at `0.78` if the note misses two or more of survey objective,
  paradigms, core components, evaluation, and challenges.
- Cap at `0.80` for material hallucinations or stale facts from the old
  synthetic paper.

Pass is `>= 0.88`; continue is `0.60-0.87`; fail is `< 0.60`.

## 7. Continue vs Fail Guidance

Prefer continue for bounded missing artifacts or one weak section. Prefer fail
for the wrong paper, no real GUI evidence, mock-only evidence, or multiple
invented paper facts.

## 8. Hidden Reference Assets

- `references/eval_rule.md`
- `references/ground_truth.json`
- `references/rag_survey_source_evidence.md`

Public source assets:

- `sources/rag_survey_pack/rag_survey.pdf`

Task-local setup service:

- `services/zotero-obsidian-setup/install.sh`

## 9. Dynamic Content Note

The task uses a static downloaded PDF. Do not re-grade against live web changes.
The setup service downloads current Zotero and Obsidian installers, but the
paper facts and expected analysis remain fixed by the local PDF and hidden
ground truth.
