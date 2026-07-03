# Hidden Evaluation Rule — task_101_14_excel_pivot_chart

## 1. Grading Philosophy

Judge whether the executor produced a cleaned analysis workbook that reconciles
to the source CSV — not just a raw pivot. The core difficulty is correct
handling of returns, voids, and late adjustments. Prefer recomputing values
from the source CSV over accepting the workbook's own visual claims. Process
constraints matter only insofar as they affect the audited outputs (correct
pivot values, reconciliation tying out, charts present).

## 2. Task Contract

The executor must deliver:

- `/tmp_workspace/results/pivot.xlsx` containing:
  - a cleaned-data sheet that retains original rows and marks excluded /
    negative rows clearly,
  - a region × product net-revenue pivot with grand totals,
  - a monthly momentum sheet using `correction_month` with net revenue and
    MoM % change,
  - a chart plotting monthly net revenue and MoM % change,
  - a `QA_Checks` sheet tying reconciliation totals to the pivot grand total
    and flagging void / return / late-adjustment rule application.
- `/tmp_workspace/results/reconciliation.csv` with one row per status
  (`booked`, `return`, `void`, `late_adjustment`).

Net-revenue rules from the public prompt:
- `void` rows are **excluded** from revenue.
- `return` rows are **kept as negative** revenue.
- `late_adjustment` rows are counted in their **`correction_month`**.

Real numeric currency / percent formats are required; plain-text values are
not acceptable.

## 3. Source-Selection and Target-Resolution Rules

Canonical source: `/tmp_workspace/clawbench/sources/sales_2011_q1.csv`. No
other source is in scope. Net revenue must be computed from this file using
`correction_month` for the monthly momentum view.

If a deliverable column or sheet has multiple plausible names, accept common
aliases (e.g., `Cleaned`, `Clean_Data`, `Pivot_Table`, `Momentum_Chart`,
`MonthlyMomentum`) provided the content matches the contract.

## 4. Ground-Truth Snapshot

Authoritative values are recorded in `references/ground_truth.json` (captured
from `sales_2011_q1.csv`, Q1 2011):

- Total rows: 240; voids: 12; returns: 21; late adjustments: 27.
- Total net revenue: 408,929.71 USD; tolerance ±0.05.
- `pivot_region_product`: full region × product matrix (5 regions × 4
  products).
- `monthly_net_revenue`: 2011-01 = 116,680.29 (no MoM); 2011-02 = 145,163.09
  (MoM +24.41%); 2011-03 = 147,086.33 (MoM +1.32%).
- `reconciliation_row_totals` (per-status, computed from the source CSV):
  - `booked`: row_count=180; gross_signed_revenue=+512462.43;
    excluded_revenue=0.00; included_net_revenue=+512462.43.
  - `return`: row_count=21; gross_signed_revenue=-85402.77;
    excluded_revenue=0.00; included_net_revenue=-85402.77.
  - `void`: row_count=12; included_net_revenue=0.00 (void rule fully
    excludes from revenue).
  - `late_adjustment`: row_count=27; gross_signed_revenue=-18129.95;
    excluded_revenue=0.00; included_net_revenue=-18129.95.
  - Sum of `included_net_revenue` across all four statuses =
    +408929.71 ≡ pivot grand total (within ±0.05).
- `qa_check_expected_results` (the QA_Checks sheet must surface these
  five named checks with the listed expected status):
  - `void_rule_applied` → PASS (void rows contribute 0 to net revenue).
  - `return_rule_applied` → PASS (return rows contribute negative
    revenue, total -85402.77).
  - `late_adjustment_rule_applied` → PASS (late_adjustment rows are
    counted in `correction_month`, total -18129.95).
  - `reconciliation_to_pivot_tieout` → PASS (status totals sum to
    pivot grand total within ±0.05 USD).
  - `row_count_total` → PASS (240 input rows = 180 booked + 21 return
    + 12 void + 27 late_adjustment).

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — Workbook structure.** `pivot.xlsx` opens and contains non-empty
  cleaned-data, pivot, monthly momentum / chart-bearing, and QA_Checks
  sheets (aliases accepted).
- **0.15 — Pivot values.** Every region × product cell matches
  `pivot_region_product` within ±0.05.
- **0.06 — Cleaning rules visible.** The workbook excludes voids from
  revenue, preserves returns as negative revenue, and identifies late
  adjustments (e.g., flag column, separate marker, or status column).
- **0.11 — Monthly momentum values.** Monthly net revenue uses
  `correction_month` and matches all `monthly_net_revenue` values within
  ±0.05.
- **0.08 — MoM percentages.** February and March MoM % values are present
  and match the hidden values within ±0.1 percentage points.
- **0.13 — Chart present and readable.** At least one chart object exists
  on the momentum / chart sheet and is bound to the monthly net revenue /
  MoM data.
- **0.08 — Numeric formats.** Revenue cells use a currency format and MoM
  cells use a percent format (no plain-text numbers).
- **0.15 — Reconciliation + QA content tie-out.** Strict, content-based
  evaluation of both deliverables. All of the following must hold:
  - `reconciliation.csv` exists at
    `/tmp_workspace/results/reconciliation.csv` with one row per status
    in {`booked`, `return`, `void`, `late_adjustment`}.
  - Row counts: `booked`=180, `return`=21, `void`=12, `late_adjustment`=27
    (all four exact matches required).
  - `booked` row's `included_net_revenue` matches +512462.43 within
    ±0.05 USD.
  - `return` row's `included_net_revenue` matches -85402.77 within
    ±0.05 USD (must be negative).
  - `void` row's `included_net_revenue` = 0.00 within ±0.05 USD (void
    rule applied → contributes nothing).
  - `late_adjustment` row's `included_net_revenue` matches -18129.95
    within ±0.05 USD.
  - Sum of all four `included_net_revenue` values equals the pivot
    grand total +408929.71 within ±0.05 USD (reconciliation.csv ↔
    pivot tie-out).
  - The `QA_Checks` sheet exists in `pivot.xlsx` and surfaces all five
    named checks listed in `ground_truth.qa_check_expected_results`
    (void_rule_applied, return_rule_applied,
    late_adjustment_rule_applied, reconciliation_to_pivot_tieout,
    row_count_total). For each check the sheet must show the expected
    status (PASS for all five) AND a formula-backed or directly
    traceable check expression (cell formula, computed value, or
    reference) — not a hard-coded "PASS" string with no underlying
    computation.
  - All checks above are required for full 0.15. Strict pass/fail at
    this checkpoint: any single missing row, mismatched count,
    out-of-tolerance amount, missing QA check, or hard-coded status
    string fails the checkpoint to 0.00 (no partial credit).
- **0.11 — Topic dimension coverage.** The combined deliverables
  (`pivot.xlsx` + `reconciliation.csv`, evaluated as a unified package)
  must visibly address all five analysis dimensions implied by the
  user's request: (1) **region × product matrix** — the existing pivot
  presents net revenue across all 5 regions × 4 products with grand
  totals; (2) **monthly progression with MoM deltas** — the monthly
  momentum sheet (or an explicit Jan/Feb/Mar walk inside the workbook)
  surfaces all three months AND shows the MoM % change for Feb and Mar
  as numeric percents (not plain text); (3) **top / bottom performers
  per region** — for each region the workbook makes the strongest /
  weakest product cell visually or numerically callable out (any of:
  conditional formatting that highlights max/min, a separate
  top-bottom column, a ranking sheet, or a per-region top-1 / bottom-1
  table — a flat unranked pivot alone is insufficient); (4) **void /
  return / late-adjustment isolation** — these three statuses are
  shown as their own reconciliation rows with row count and revenue
  impact, AND the cleaned-data sheet flags / separates them rather
  than silently merging into headline; (5) **prior-period or
  quarter-over-quarter context hint** — at minimum a sentence,
  callout cell, or summary line acknowledging the year-over-year /
  quarter-over-quarter context (either an actual prior-period
  comparison if derivable, OR an explicit "no prior-period baseline
  in source" disclaimer that demonstrates the executor checked).
  - 5 of 5 dimensions clearly addressed → full 0.11.
  - ≤ 4 of 5 → 0.00 (strict — the prompt explicitly enumerates all
    five concerns, so the deliverable must address all five).

- **0.03 — Numeric precision (pivot anchor cells).** All five
  high-signal `(region, product)` anchor cells in
  `ground_truth.expected_pivot_cell_corner` must match within
  ±0.05 USD. Strict pass/fail:
  - 5 of 5 anchor cells match within tolerance → full 0.03
  - ≤ 4 of 5 → 0.00.

Sum: 0.10 + 0.15 + 0.06 + 0.11 + 0.08 + 0.13 + 0.08 + 0.15 + 0.11 + 0.03 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit is the sum of satisfied checkpoint weights. The following
caps apply only to extreme failure modes, not to ordinary checkpoint misses:

- **Cap 0.30 — No deliverables.** No workbook is produced at
  `/tmp_workspace/results/pivot.xlsx`.
- **Cap 0.50 — Voids included in revenue.** The pivot or monthly totals
  include `void` rows in revenue (the prompt explicitly forbids this — a
  fundamental misread of the contract).
- **Cap 0.55 — Fabricated source.** The executor invents data not present
  in `sales_2011_q1.csv` (e.g., synthetic rows, hand-edited totals not
  derivable from the source) instead of computing from the canonical CSV.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/office-document-specialist-suite/` OR
  `/root/skills/excel-weekly-dashboard/` belonging to the declared
  skill(s). A skill-usage task with zero evidence of consulting the
  declared skill(s) cannot reach a full score.

A pass requires the structure, pivot values, reconciliation, and at least
one chart checkpoint all satisfied, with evidence sufficient to audit.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to fix a
  recoverable gap (missing chart, missing format, missing QA row, off-by-a
  tolerance value).
- **Fail** < 0.50 — unrecoverable; no further follow-ups.

Prefer `continue` when the workbook exists and the pivot is broadly correct
but one auxiliary deliverable is missing or malformed. Prefer `fail` when
the cleaning rules are fundamentally wrong — for example, void rows
counted in revenue, returns dropped instead of negated, or `booked_month`
used for late adjustments throughout — or when no usable workbook exists.

## 8. Hidden Reference Assets

Supervisor-only — never surface to the executor or user simulator:

- `references/eval_rule.md` (this file) — the hidden grading spec.
- `references/ground_truth.json` — pivot matrix, monthly values, row counts,
  reconciliation expectations, tolerance.

## 9. Dynamic Content Note

The source CSV is fixed and shipped with the task; the ground-truth values
are deterministic from that input. Tolerance ±0.05 USD covers floating-point
rounding from different aggregation orders. MoM percentages use ±0.1
percentage points to absorb display-rounding differences. No live or
network-dependent values are involved.
