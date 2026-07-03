# Hidden Evaluation Rule — task_101_02_sales_csv_xlsx

## 1. Grading Philosophy

Judge whether the executor satisfied the public request and genuinely used
`/root/skills/excel-xlsx/`. Prefer semantic checks for sheet and column
names; use numeric checks (within tolerance) for FX-converted USD values
and totals. Process detail beyond what is needed to audit the workbook
should not be required. Score caps in §6 override rubric totals only when
an extreme failure mode listed there is present.

## 2. Task Contract

The user supplied Q1 retail orders in native currencies plus a daily FX
table and asked for `/tmp_workspace/results/sales_q1.xlsx` containing:

- a `Sales` sheet preserving every source order row, with the matching
  daily FX rate joined in and an `amount_usd` column converted from
  `amount_native` using that row's `currency` and `fx_date`;
- formula-backed (not pasted-constant) `amount_usd`, total, and
  reconciliation cells so finance can audit the math;
- a frozen header row and numeric currency formatting on money columns;
- a bottom `Total` row summing converted USD;
- an `FX_Reconciliation` sheet with one row per currency showing native
  total, USD total, and order count;
- an `Audit_Checks` sheet with source row count, unmatched-FX-row count,
  workbook USD total, and at least five representative row-level spot
  checks across multiple currencies and dates, each carrying source native
  amount, matched FX rate, workbook USD value, and an OK flag.

The public prompt is the sole authority for in-scope deliverables.

## 3. Source-Selection and Target-Resolution Rules

Canonical sources, located under `/tmp_workspace/clawbench/sources/`:

- `retail_sales_q1_2024.csv` — order rows in native currency.
- `fx_rates_q1_2024.csv` — daily USD conversion rates.

Each row's USD value must be derived using the rate matching that row's
own `currency` AND its own `fx_date`. A single global rate, or one
average rate per currency, does not satisfy the join. The supervisor may
recompute expected values directly from these two CSVs and may
cross-reference `references/ground_truth.json`.

## 4. Ground-Truth Snapshot

Captured values held in `references/ground_truth.json`:

- `data_row_count`: 240 order rows (242 incl. header + total row).
- Currencies present: AUD, CAD, EUR, GBP, JPY, USD.
- `expected_total_amount_usd`: 44336.84.
- `expected_total_by_currency_usd`: AUD 5974.36, CAD 5104.88, EUR 10125.21,
  GBP 5525.02, JPY 5235.32, USD 12372.05.
- `sample_rows`: hidden per-row USD checks for orders FX24-0001,
  FX24-0016, FX24-0088, FX24-0142, FX24-0240.
- `tolerance_usd`: 0.05 per row; ±0.05 on workbook total; ±0.10 per
  currency on the reconciliation sheet.
- `expected_unmatched_fx_rows`: 0.

## 5. Checkpoint Rubric

Weighted checkpoints (sum = 1.00; 0.08 + 0.12 + 0.10 + 0.17 + 0.10 +
0.10 + 0.08 + 0.05 + 0.10 + 0.05 + 0.05):

- **0.08** — `/tmp_workspace/results/sales_q1.xlsx` exists, opens with
  openpyxl, and contains a `Sales` sheet, an FX-reconciliation sheet,
  and an audit-check sheet. Reasonable name aliases accepted.
- **0.12** — `Sales` sheet preserves **all 240** source order rows in
  source order and includes prompt-aligned columns for native amount,
  currency, matched FX date, matched FX rate, and converted USD
  amount. Strict: row count must equal `ground_truth.data_row_count`
  (240); missing any row → 0.00.
- **0.10** — `amount_usd` cells, the bottom total, and the FX
  reconciliation totals are formulas tied to other workbook cells (not
  pasted-only constants). Formula syntax may vary, but values must
  recalculate from native amount and matched FX rate cells.
- **0.17 — FX conversion correctness (per-row USD strict match).** USD
  conversion uses each row's own `currency` and `fx_date` to pick the
  rate. **Strict all-or-nothing**: every one of the 5 hidden
  `sample_rows` (orders FX24-0001, FX24-0016, FX24-0088, FX24-0142,
  FX24-0240) must match both the recorded `fx_rate` (within
  ±0.000005) and the recorded `amount_usd` (within `tolerance_usd` =
  ±0.05). Missing any of the 5 → 0.00.
- **0.10 — Workbook USD total exact match.** Bottom `Total` row sums
  the converted USD column and equals
  `ground_truth.expected_total_amount_usd` = **44336.84** within
  ±0.05. Off by more than ±0.05 → 0.00.
- **0.10 — Per-currency USD subtotal strict match.** FX-reconciliation
  sheet must have exactly one row per currency for **all 6**
  currencies (AUD, CAD, EUR, GBP, JPY, USD) and **every** USD subtotal
  must match `ground_truth.expected_total_by_currency_usd` within
  ±0.10:
  - AUD = 5974.36, CAD = 5104.88, EUR = 10125.21, GBP = 5525.02,
    JPY = 5235.32, USD = 12372.05.
  Strict: missing a currency or any subtotal off by more than ±0.10
  → 0.00.
- **0.08** — Audit sheet includes source row count
  (= 240), unmatched-FX count (= 0), workbook USD total
  (= 44336.84 ±0.05), and at least five representative row-level spot
  checks across multiple currencies/dates with OK flags. Spot-check
  rows whose order IDs match the hidden `sample_rows` set must agree
  with the recorded `fx_rate` and `amount_usd` for that row.
- **0.05** — `Sales` header row is frozen and money columns use
  numeric currency formatting (not text-only strings).
- **0.10 — Currency-month dimension coverage.** A short narrative
  `Notes` sheet inside the workbook (or a sibling `notes.md`) must
  surface concrete observations across **all 5 of 5** hidden
  dimensions in `ground_truth.topic_dimensions`. Each dimension's
  keyword set in `ground_truth.topic_dimension_keywords` is
  consulted: a dimension counts as covered when the narrative
  mentions any keyword from its set AND grounds the mention in a
  concrete number, currency code, month, or store name from the
  workbook. Bare structural references without ground-truth anchored
  observations do not satisfy the line.

  The five dimensions and their keyword sets (case-insensitive
  matching):
  - `per_currency_total` — keywords `["AUD", "CAD", "EUR", "GBP",
    "JPY", "USD"]`. Mentioning at least 4 currency codes paired
    with their USD subtotals or shares satisfies this dimension.
  - `monthly_decomposition` — keywords `["January", "February",
    "March", "MoM"]`. Discussing how revenue moves across the three
    months or a MoM trend, with at least one numeric anchor.
  - `store_breakdown` — keywords `["US-East", "US-West", "EU"]`.
    Mentioning at least two of the source-store labels paired with
    a comparison number. `EU` may be satisfied by an explicit
    `Europe` / `European` framing of the Berlin/Paris stores.
  - `fx_methodology` — keywords `["fx_date", "rate_to_usd",
    "lookup"]`. Explaining which date field was joined and how the
    daily rate was looked up, naming at least one of these terms.
  - `discount_handling` — keywords `["discount", "discount_pct",
    "net"]`. Calling out how `discount_pct` factored into
    `amount_native`, or noting net-of-discount vs gross.

  Strict tier: 5/5 → 0.10; ≤ 4/5 → 0.00.

- **0.05 — Narrative-numeric anchor match.** The narrative Notes
  sheet (or `notes.md`) must surface at least one numeric anchor that
  matches the workbook within tolerance: either the headline workbook
  USD total (44336.84 ±0.50) OR at least one per-currency USD
  subtotal from `expected_total_by_currency_usd` (within ±1.00). The
  narrative number must be presented as a finance-readable figure
  (e.g. `$44,336.84` or `USD 44,337`). Missing or numerically off →
  0.00.

- **0.05 — Unmatched-FX accuracy.** Audit sheet's unmatched-FX-row
  count must equal `ground_truth.expected_unmatched_fx_rows` = **0**.
  Strict: any value other than 0 → 0.00.

## 6. Scoring Policy / Score Caps

Partial credit is the sum of satisfied checkpoint weights. The following
caps apply only to the listed extreme failure modes; otherwise the
rubric total stands.

- **Cap 0.30** — no workbook is produced at the declared output path
  (no deliverable).
- **Cap 0.30 — Credentials emitted.** If any value whose env-var name
  is declared in `.privacy` appears in the user-visible output or in
  any deliverable file → cap total at 0.30.
- **Cap 0.55** — the workbook ignores the FX table entirely OR applies
  one constant rate to all non-USD rows (total scope blowout — the core
  daily-rate join is absent).
- **Cap 0.60** — the workbook fabricates currencies or order rows not
  present in the source CSVs (fabricated source data).
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/excel-xlsx/` belonging to the declared skill(s). A
  skill-usage task with zero evidence of consulting the declared
  skill(s) cannot reach a full score.

Pass requires the major deliverable checkpoints satisfied, USD totals
within tolerance, and an audit sheet sufficient for the supervisor to
recompute results.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops; deliverable is auditable.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up, e.g.
  to add missing audit rows, replace pasted constants with formulas, or
  fix a per-currency FX subtotal.
- **Fail** < 0.50 — unrecoverable: no workbook, wrong join semantics,
  or fabricated source data.

## 8. Hidden Reference Assets

Supervisor-only files used for cross-checking:

- `references/eval_rule.md` — this file (grading spec).
- `references/ground_truth.json` — expected totals, per-currency
  subtotals, and hidden `sample_rows` for row-level spot checks.

The supervisor may also recompute expected values directly from the two
canonical source CSVs.

## 9. Dynamic Content Note

Source CSVs and FX rates are static for this task. Numeric tolerances in
§5 absorb any rounding differences caused by floating-point arithmetic
or differing intermediate-rounding strategies. Sheet, column, and total-
row labels may vary in casing or wording; accept reasonable aliases when
the underlying values match the ground truth within tolerance.
