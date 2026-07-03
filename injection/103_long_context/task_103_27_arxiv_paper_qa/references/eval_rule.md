# Hidden Evaluation Rule — task_103_27_arxiv_paper_qa

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor actually read the three injected PDFs and answered specific, number-level questions correctly, with the right paper attribution — not from prior memory of famous papers. The filenames are obfuscated, so identifying each paper from its content is part of the task. Answers are graded against the values that appear in the injected PDFs.

## 2. Task Contract

The public task gives three PDFs at `sources/papers/paper_a.pdf`, `paper_b.pdf`, `paper_c.pdf` and a list of questions, and asks the executor to answer them in `/tmp_workspace/results/paper_qa.md`, citing which paper (and where possible which table/section) each answer comes from. The executor must read the PDFs (they cannot be answered reliably from memory because they target specific numbers).

## 3. Source-Selection and Target-Resolution Rules

Answers must be grounded in the injected PDFs. The executor should identify paper_a = Transformer/"Attention Is All You Need", paper_b = ResNet/"Deep Residual Learning", paper_c = BERT from content, not filename. Numbers must match the PDFs; recited approximations that differ from the paper's stated values are scored as errors.

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`) gives the question set and answers, including:
- Transformer: big model 28.4 BLEU (WMT14 EN-DE) and 41.8 BLEU (EN-FR); encoder N=6 layers; d_model=512; base model ~65M params (Table 3).
- ResNet: ensemble 3.57% top-5 error on ImageNet; up to 152 layers; 34-layer baseline 3.6 billion FLOPs; ResNet-110 = 1.7M params.
- BERT: BASE L=12/H=768/A=12/110M; LARGE L=24/H=1024/A=16/340M; GLUE 80.5%; SQuAD v1.1 Test F1 93.2.
- Correct paper-topic mapping (translation / image recognition / language pre-training).

## 5. Checkpoint Rubric

- 0.15 Paper identification: correctly identifies all three papers from content despite obfuscated filenames.
- 0.55 Factual correctness: answers the specific questions with correct numbers attributed to the right paper. Award proportionally across the questions (Q1-Q7); a correct numeric answer with right attribution earns the question's share, a wrong/missing/misattributed number does not.
- 0.15 Cross-paper question (Q7): correctly compares across papers (parameter-count ranking where stated and the topic mapping).
- 0.10 Evidence/citation: each answer says which paper and, where possible, which table/section the value comes from.
- 0.05 Deliverable: `paper_qa.md` saved at the requested path, organized by question.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If the executor answers mostly from memory and gets specific numbers wrong or swaps numbers between papers, cap at 0.55. If it fails to identify the papers from content (treats them as unknown and answers generically), cap at 0.60. If `paper_qa.md` is missing, cap at 0.40. If answers carry no paper attribution at all, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer `continue` when some answers are present but others are missing or unverified. Prefer `fail` when answers are largely fabricated, numbers are wrong throughout, or no answer file is produced.

## 8. Hidden Reference Assets

- `ground_truth.json`: paper identities, question set, answers, anchors, scoring notes.
- `sources/papers/paper_a.pdf`, `paper_b.pdf`, `paper_c.pdf`: the injected PDFs (also visible task sources).

## 9. Dynamic Content Note

The PDFs are frozen arXiv versions. Judge answers against the injected PDFs, not against any newer revisions.
