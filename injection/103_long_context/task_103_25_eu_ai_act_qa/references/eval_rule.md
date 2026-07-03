# Hidden Evaluation Rule — task_103_25_eu_ai_act_qa

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor read the injected EU AI Act text and answered specific questions about penalty amounts, phased application dates, and risk-tier rules correctly, with article/annex citations — not from prior memory. These are precise figures and dates that must be looked up. Answers are graded against the injected regulation text.

## 2. Task Contract

The public task gives the EU AI Act (Regulation (EU) 2024/1689) as injected sources — a PDF (`sources/regulation/eu_ai_act_2024_1689.pdf`) and a normalized text extract (`sources/regulation/eu_ai_act_2024_1689.txt`) — plus a list of questions, and asks the executor to answer them in `/tmp_workspace/results/eu_ai_act_qa.md` with citations to the relevant articles/annex.

## 3. Source-Selection and Target-Resolution Rules

Answers must be grounded in the injected text. The penalty amounts, percentages, and phased dates must match the injected regulation; recited approximations that differ are errors. The executor may read either the PDF or the text extract.

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`) includes:
- Article 5 (prohibited practices) infringement: up to EUR 35 000 000 or 7% of worldwide annual turnover.
- Incorrect/misleading information to authorities: up to EUR 7 500 000 or 1%.
- Intermediate tier (other non-compliance): up to EUR 15 000 000 or 3%.
- General application date: 2 August 2026. Phased: Chapters I and II (incl. prohibitions) from 2 February 2025; GPAI-model rules, governance and penalties from 2 August 2025; certain high-risk obligations from 2 August 2027.
- High-risk use cases are listed in Annex III; risk tiers: prohibited (Art. 5), high-risk (Annex III / Art. 6), transparency-obligation systems, plus separately governed general-purpose AI models.

## 5. Checkpoint Rubric

- 0.55 Factual correctness: answers Q1-Q6 with correct amounts/percentages/dates from the text. Award proportionally across the six questions; a correct, text-grounded answer earns the question's share, a wrong/missing one does not.
- 0.20 Penalty-tier accuracy: the three penalty tiers (35M/7%, 15M/3%, 7.5M/1%) are correctly matched to their infringement types, not swapped.
- 0.15 Date accuracy: the phased application dates (2 Feb 2025, 2 Aug 2025, 2 Aug 2026, 2 Aug 2027) are correct and matched to the right provisions.
- 0.05 Evidence/citation: answers cite the relevant article (e.g. Art. 99) or Annex III.
- 0.05 Deliverable: `eu_ai_act_qa.md` saved at the requested path, organized by question.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If the penalty amounts or percentages are wrong or swapped between tiers, cap at 0.60. If the phased application dates are wrong (e.g. claims everything starts 2 Aug 2026), cap at 0.60. If `eu_ai_act_qa.md` is missing, cap at 0.40. If the executor answers generically without grounding in the injected text, cap at 0.55.

## 7. Continue vs Fail Guidance

Prefer `continue` when some answers are present but others missing/unverified. Prefer `fail` when amounts and dates are largely wrong or no answer file is produced.

## 8. Hidden Reference Assets

- `ground_truth.json`: question set, answers, anchors, scoring notes.
- `sources/regulation/eu_ai_act_2024_1689.pdf` and `.txt`: the injected regulation (also visible task sources).

## 9. Dynamic Content Note

The injected OJ text is frozen and authoritative for this task. Judge answers against the injected PDF/text, not against summaries or later amendments.
