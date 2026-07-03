# Hidden Evaluation Rule — task_101_08_receipts_reconcile

## 1. Grading Philosophy

Judge the executor on whether the public reconciliation request was actually
delivered as a working Excel workbook plus the requested CSV, and whether the
declared OCR and spreadsheet skills under `/root/skills/` were genuinely
consulted. Prefer semantic matching over exact-string matching for column
names and store labels — the user issued the request in natural language and
did not pin down specific keys. Score caps in §6 override rubric totals when
they apply.

## 2. Task Contract

The user has three scanned German supermarket receipts in
`/tmp_workspace/clawbench/sources/receipts/` (dm-drogerie-markt, Kaisers
Tengelmann, Penny Markt) and wants them reconciled for expenses.

Required deliverables:

1. `/tmp_workspace/results/reconcile.xlsx` with two worksheets:
   - **Line items tab**: one row per OCR'd line item, with store, date,
     source image filename, item description, quantity, unit price, line
     total in euros, and a manual-review flag.
   - **Reconciliation tab**: one row per store, comparing the
     formula-backed sum of line items against the printed receipt total.
   - Money columns must use real currency / number formatting (not plain
     text), and the reconciliation tab's item-sum and difference cells
     must be formulas referencing the line-items sheet rather than pasted
     constants.
2. `/tmp_workspace/results/review_flags.csv` with one row per receipt
   covering source image, item count, printed total, item sum, difference,
   and a short manual-review note.

The public task prompt is authoritative for what counts as in-scope.

## 3. Source-Selection and Target-Resolution Rules

Inputs live under `/tmp_workspace/clawbench/sources/receipts/`. The supervisor
treats the following file list as the canonical input set:

- `receipt_dm_2014-12-11.jpg` — dm-drogerie-markt receipt scan
- `receipt_kaisers_2015-08-31.jpg` — Kaisers Tengelmann receipt scan
- `receipt_penny_2014-10-18.jpg` — Penny Markt receipt scan

Each output row in the line-items sheet must carry a source image filename
that maps to exactly one of these three scans. Store labels in the workbook
may differ from the canonical short names (`dm`, `kaisers`, `penny`) only by
case, whitespace, or full storefront name (e.g., "Kaisers Tengelmann").
Dates per store must match the snapshot in §4 exactly.

## 4. Ground-Truth Snapshot

The structured expected answer lives at `references/ground_truth.json`
(schema **a**: concept-level booleans with evidence pointers, must-hit
findings).

Key anchors used by the rubric:

| Store    | Date        | Printed total (EUR) | Line-item rows |
|----------|-------------|---------------------|----------------|
| dm       | 2014-12-11  | 11.52               | 5              |
| kaisers  | 2015-08-31  | 12.38               | 6              |
| penny    | 2014-10-18  | 7.13                | 6              |

- `expected_item_rows`: 17 (5 + 6 + 6)
- `summary_rows`: 3 (one per store)
- `review_flags_rows`: 3 (one per receipt)
- `printed_total_tolerance_eur`: 0.02 (printed-total match tolerance)
- `tolerance_eur`: 0.10 (acceptable absolute reconciliation difference)

## 5. Checkpoint Rubric

Weighted checkpoints; weights sum to 1.0.

- **0.10 — Workbook shape.** `/tmp_workspace/results/reconcile.xlsx`
  exists, opens cleanly, and contains two worksheets that semantically
  correspond to (a) line items and (b) per-receipt reconciliation summary.
- **0.10 — Line-item coverage.** The line-items sheet has exactly
  `expected_item_rows` rows (17), and per-store item counts match the
  table in §4.
- **0.15 — Required line-item columns.** The line-items sheet includes
  the prompt-requested source-image and manual-review columns; every
  row's source-image value resolves to one of the three receipt scans
  listed in §3.
- **0.10 — Store/date alignment.** Store and date pairs in both sheets
  match §4 (store names may differ only by case, whitespace, or full
  storefront name; dates must match exactly).
- **0.15 — Printed-total accuracy.** The summary sheet has exactly
  `summary_rows` (3) rows, one per store, and each printed total matches
  the §4 snapshot within `printed_total_tolerance_eur` (±0.02).
- **0.10 — Reconciliation correctness.** For every store, the calculated
  item-sum equals the sum of that store's line-item totals within ±0.02,
  `|diff_eur| ≤ tolerance_eur` (0.10), and the item-sum and difference
  cells are formulas referencing the line-items sheet rather than pasted
  numeric constants.
- **0.10 — Numeric typing & currency formatting.** Quantity, unit-price,
  and line-total cells are stored as numeric values, and money columns
  use a number/currency format rather than plain text strings.
- **0.05 — Review-flags CSV.** `/tmp_workspace/results/review_flags.csv`
  exists with exactly one row per receipt and columns (or clear
  equivalents) for source_image, item_count, printed_total, item_sum,
  difference, and manual-review note.

- **0.10 — Topic dimension coverage (anchor-keyword detection).** The
  combined deliverables `reconcile.xlsx`, `review_flags.csv`, plus any
  trailing notes sheet inside the workbook or sidecar
  `reconcile_notes.md`, must substantively address all five receipt-
  analysis dimensions implied by the user's request. Each dimension
  carries an `anchor_phrases` list in `ground_truth.topic_dimensions`; a
  dimension is counted as **covered** iff supervisor finds at least one
  anchor phrase from its list anywhere in the deliverable package
  (case-insensitive substring match, sheet headers, sheet cells, CSV
  cells, or markdown notes all eligible):
    - **per_line_extraction** — `["line item", "qty", "unit price"]`
    - **discount_handling** — `["discount", "rabatt", "promo", "club"]`
    - **tax_breakdown** — `["tax", "VAT", "Mwst", "USt"]`
    - **payment_method** — `["cash", "card", "EC", "Visa"]`
    - **reconciliation_check** — `["matches", "discrepancy", "off by",
      "rounding", "agree", "gap", "reconcil"]`
  Strict all-or-nothing scoring on the count
  `ground_truth.min_dimensions_covered = 5`:
    - all 5 of 5 dimensions covered → full 0.10
    - any dimension missing → 0.00
  Anchor matches must come from saved artifacts under
  `/tmp_workspace/results/`, not from the executor's chat reply alone.

- **0.05 — Per-receipt MwSt rate classification.** All
  `ground_truth.min_receipts_with_mwst_classification = 3` receipts must
  have line items annotated with their MwSt rate (7% reduced or 19%
  standard German VAT, with 0% allowed for items that genuinely carry no
  VAT). Strict all-or-nothing:
  - all 3/3 receipts annotated → 0.05
  - any receipt missing MwSt annotation → 0.00.

Sum: 0.10 + 0.10 + 0.15 + 0.10 + 0.15 + 0.10 + 0.10 + 0.05 + 0.10 + 0.05 = 1.00.

The judge MUST open the workbook and verify both sheet structure and the
per-store totals against the §4 anchors; do not award full credit for a
workbook that only has the right shape but wrong values.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps apply
only to extreme-failure modes and override rubric arithmetic:

- **Cap 0.30 — No deliverables produced.** Neither
  `reconcile.xlsx` nor `review_flags.csv` exists at the declared paths
  (or both are empty / unreadable).
- **Cap 0.30 — Credentials emitted.** Any value bound to an environment
  variable declared in `.privacy` appears verbatim in the workbook, CSV,
  or executor's user-facing reply.
- **Cap 0.50 — Fabricated source.** The line-items sheet references an
  image filename that does not exist under `sources/receipts/`, or rows
  cite stores beyond the three canonical receipts.
- **Cap 0.70 — Total scope blowout.** The executor performs work
  unrelated to reconciling the three receipts (e.g., calls live banking
  APIs, scrapes external sites, generates dozens of unrelated tabs)
  beyond what the prompt requested.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/image-ocr/` OR `/root/skills/xlsx-cn/` belonging
  to the declared skill(s). A skill-usage task with zero evidence of
  consulting the declared skill(s) cannot reach a full score.

## 7. Continue vs Fail Guidance

- **Pass** (≥ 0.90, the task's `success_threshold`): executor should stop;
  the workbook is ready for expense reuse.
- **Continue** (0.50 – 0.89): supervisor may request one follow-up to
  repair the lowest-scoring rubric line (e.g., missing review-flags CSV,
  missing currency formatting, off-by-one item count on a single
  receipt).
- **Fail** (< 0.50): no further follow-ups; record `finalStatus=failed`.

## 8. Hidden Reference Assets

Supervisor-only files; never surface to the executor or user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — structured expected answers and
  per-store anchors used by §4 and §5.

## 9. Dynamic Content Note

This is an offline task — the receipt scans are local fixtures and no
live API calls are expected. Printed totals, item counts, and dates in
§4 are stable across runs; if OCR estimation introduces minor item-total
drift within the §4 tolerances, that is acceptable and the §5
reconciliation checkpoint already handles it.
