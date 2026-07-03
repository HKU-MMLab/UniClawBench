# Hidden Evaluation Rule — task_103_24_world_bank_economic_report

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor actually read and analyzed the injected World Bank dataset and produced a multi-indicator, data-grounded economic comparison report with correct numbers and supporting charts. The core test is that the numbers and conclusions come from the injected CSV (`sources/worldbank_data/worldbank_indicators_2000_2023.csv`), not from the model's prior knowledge. A report full of plausible-sounding but dataset-ungrounded boilerplate should score poorly even if it reads well.

## 2. Task Contract

The public task gives the executor a CSV of real World Bank indicators (6 countries, 5 indicators, 2000-2023) and asks for an analysis report saved to `/tmp_workspace/results/economic_report.md` plus at least 3 charts (png or interactive html) under `/tmp_workspace/results/`, referenced from the report. The report must compare countries across multiple indicators and draw grounded conclusions.

Completion means the report exists, cites concrete values from the dataset, covers multiple indicators with cross-analysis, and includes working chart files that match the data.

## 3. Source-Selection and Target-Resolution Rules

All numbers must come from the injected CSV. The executor should load and compute over the CSV (e.g. with pandas or equivalent), not quote remembered figures. If the executor pulls fresh data from the live World Bank API instead, that is acceptable ONLY if the values still match the injected CSV; contradicting the injected CSV is scored as an error.

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`) lists anchor values computed from the CSV, including: China's GDP grew ~15x from 2000 to 2022 (US ~2.5x, India ~7.1x); 2022 GDP per capita roughly China $12,971 / US $76,657 / Japan $34,066 / India $2,347; 2022 per-capita CO2 roughly US 14.4t / China 8.9t / India 2.0t; China urbanization ~36.4% (2000) to ~65.2% (2022); 2022 total GDP roughly US $25.6T / China $18.3T / Japan $4.26T / Germany $4.2T / India $3.35T / Brazil $1.95T. Small rounding differences are fine; values off by more than ~5% indicate misreading or fabrication.

## 5. Checkpoint Rubric

- 0.20 Data loading and correctness: loads the injected CSV and reports values that match it (anchor values within ~5%).
- 0.25 Multi-indicator cross-analysis: analyzes at least 3 of the 5 indicators and connects them (e.g. total GDP vs GDP-per-capita vs population; emissions per capita vs total), rather than summarizing one indicator.
- 0.20 Grounded conclusions: conclusions reflect the dataset (e.g. China catch-up growth, per-capita vs total gap, per-capita CO2 ranking, China urbanization jump) and are not generic prior-knowledge claims.
- 0.20 Charts: at least 3 charts saved under results and referenced from the report; charts open/render and visually match the underlying data (correct trends, axes, country labels).
- 0.10 Report quality: `economic_report.md` is clear, well-structured (e.g. method, findings, discussion), and cites which indicator/year each number comes from.
- 0.05 Deliverables: report and chart files are saved at the requested paths and the report references the chart files.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If the report's numbers mostly do not match the injected CSV (fabricated or prior-knowledge values), cap at 0.55. If the report analyzes only a single indicator with no cross-analysis, cap at 0.65. If no chart files are produced, or charts are broken/empty/do not match the data, cap at 0.65. If `economic_report.md` is missing, cap at 0.40. If the executor ignores the injected CSV entirely and writes from general knowledge, cap at 0.50.

## 7. Continue vs Fail Guidance

Prefer `continue` when the report exists but is missing charts, covers too few indicators, or has some unverified numbers. Prefer `fail` when the report fabricates data, contradicts the CSV throughout, or produces no usable report.

## 8. Hidden Reference Assets

- `ground_truth.json`: dataset description, anchor values, expected analysis points, scoring notes.
- `sources/worldbank_data/worldbank_indicators_2000_2023.csv`: the authoritative injected dataset (also visible to the executor as a task source).

## 9. Dynamic Content Note

The World Bank may revise historical figures over time, but the injected CSV is frozen and authoritative for this task. Judge against the injected CSV. Chart styling may vary; require correctness and data-match, not a specific visual style.
