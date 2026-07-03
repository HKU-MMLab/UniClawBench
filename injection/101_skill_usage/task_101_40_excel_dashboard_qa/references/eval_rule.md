# Hidden Evaluation Rule — task_101_40_excel_dashboard_qa

## 1. Grading Philosophy

Score the executor on whether the cross-source QA was actually delivered:
both `qa.md` and `qa_repro.csv` exist, the executor ran SQL against
`sales.db` AND inspected `sales_dashboard_2024.xlsx`, and every one of the
nine seeded inconsistencies between the workbook and the database is
identified with a DuckDB SQL query that reproduces the database's correct
value. Score caps in §6 override rubric totals.

## 2. Task Contract

The user delivered two sources:

- `sales_dashboard_2024.xlsx` — Excel dashboard with Raw + Pivot + Chart +
  Summary sheets.
- `sales.db` — sqlite database, the canonical "source of truth" with 2400
  transactions, 4 regions (NA / EMEA / APAC / UK), 4 products, and 4
  quarters of 2024.

Two artifacts are required:

- `/tmp_workspace/results/qa.md` — every inconsistency between the
  workbook and `sales.db` (sheet + cell, xlsx value, sql value, one-sentence
  explanation), the corresponding DuckDB SQL query for each, and a ≤6
  sentence overall verdict.
- `/tmp_workspace/results/qa_repro.csv` — one row per inconsistency with
  columns `sheet`, `cell`, `category`, `xlsx_value`, `sql_value`,
  `duckdb_sql`, `status` (or clear equivalents).

The public prompt alone is authoritative for what counts as in-scope.

## 3. Source-Selection and Target-Resolution Rules

Two canonical inputs under `/tmp_workspace/clawbench/sources/`:

- `sales_dashboard_2024.xlsx`
- `sales.db`

`sales.db` is the source of truth. Anything outside these two files is
not in scope. When a calculation cell on a non-Raw sheet conflicts with
`sales.db`, the executor is expected to inspect the cell's Excel COMMENT
before classifying it: cells that carry a comment documenting an
intentional business override (CFO memo, RMA adjustment, audit holdback)
must NOT be reported as material inconsistencies. The three documented
overrides are listed in `ground_truth.documented_override_cells`.

## 4. Ground-Truth Snapshot

`references/ground_truth.json` (schema `a`: cross-source dashboard QA)
encodes:

- `canonical_db_aggregates` — full set of correct totals from `sales.db`.
- `min_inconsistencies` (= 9) — required count of seeded inconsistencies.
- `anomaly_types_min` (= 6) — distinct seeded categories.
- `min_seeded_hits` (= 9) — STRICT, all-of-list match by sheet+cell.
- `min_qa_repro_rows` (= 9) — minimum rows in the CSV deliverable.
- `expected_inconsistencies[]` — the canonical list of nine seeded bugs,
  each with `sheet`, `cell`, `category`, `xlsx_value`, `sql_value`,
  `sql_query`, and `issue`.
- `documented_override_cells[]` — three cells (Pivot!B16, Chart!B6,
  Summary!B7) that mismatch `sales.db` on purpose; flagging any of them as
  a real inconsistency triggers the override cap.
- `qa_repro_columns` — the prompt-aligned CSV column set.

## 5. Checkpoint Rubric

Weights total 1.00.

- **0.30 — Strict seeded-inconsistency recall.** Every one of the
  `min_seeded_hits` (= 9) entries in `expected_inconsistencies` is matched
  by exact sheet+cell coordinate AND a semantically correct description of
  the bug. STRICT — partial credit is binary on the 9-of-9 floor:
  - 9/9 seeded inconsistencies hit by exact sheet+cell + correct issue
    semantics → 0.30
  - ≤8/9 → 0.00. Missing even one seeded cell loses the full 0.30.
- **0.20 — DuckDB SQL grounded against sales.db.** Every listed
  inconsistency has an accompanying DuckDB / SQL query that, when run
  against `sales.db`, produces the canonical `sql_value`. The query MUST
  reference the `sales` table (or otherwise touch `sales.db`); pure
  Excel-cell-arithmetic queries do not count. STRICT — binary on the
  9-of-9 floor:
  - 9/9 inconsistencies have a sales.db SQL query whose result matches
    `sql_value` (within ±0.5% for currency / percentage; exact for integer
    units) → 0.20
  - ≤8/9 → 0.00.
- **0.10 — Numeric accuracy of xlsx_value vs sql_value pairs.** For each
  reported inconsistency the executor's `xlsx_value` matches what is
  literally stored in the workbook AND `sql_value` matches the GT
  `sql_value` (±0.5% currency / percentage, exact for integer units and
  string labels). Stepped:
  - 9/9 pairs accurate → 0.10
  - 7-8/9 pairs accurate → 0.05
  - ≤6/9 → 0.00.
- **0.10 — Category coverage.** Findings span at least
  `anomaly_types_min` (= 6) distinct categories from
  `expected_inconsistencies[*].category` (the seeded set covers 7
  distinct categories: aggregation_error, missing_region,
  quarter_rollup_error, wrong_date_filter, missing_total_row,
  typo_product_name, wrong_value, average_value_error). Stepped:
  - ≥6 distinct categories → 0.10
  - 4-5 → 0.05
  - ≤3 → 0.00.
- **0.10 — CSV completeness.** `qa_repro.csv` exists with one row per
  reported inconsistency, includes the prompt columns or clear
  equivalents (`sheet`, `cell`, `category`, `xlsx_value`, `sql_value`,
  `duckdb_sql`, `status`), and covers all nine seeded sheet+cell
  references with both `xlsx_value` and `sql_value` populated. STRICT —
  binary on the 9-of-9 floor:
  - 9/9 seeded cells in the CSV with both values + duckdb_sql → 0.10
  - ≤8/9 → 0.00.
- **0.05 — Verdict length.** The overall verdict paragraph in `qa.md` is
  ≤6 sentences.
- **0.05 — Structural-anomaly cell-id precision.** The structural seeded
  inconsistency (`expected_inconsistencies` item with category
  `missing_total_row`, currently `Pivot!A6`) must be flagged with the
  EXACT cell coordinate. Off-by-one (e.g. `Pivot!A5` or `Pivot!B6`) is not
  credited:
  - Exact `Pivot!A6` (or row 6 with explicit description "missing total
    row after the region rollup") → 0.05
  - Off-by-one or off-by-row → 0.02
  - Not flagged → 0.00.
- **0.05 — Documented-override explicit-naming precision.** For each of
  the 3 cells in `documented_override_cells` (Pivot!B16, Chart!B6,
  Summary!B7), the deliverables (`qa.md` and/or `qa_repro.csv`) must
  explicitly reference the cell coordinate AND label it as intentional /
  documented / business override / not an anomaly:
  - 3/3 documented overrides explicitly named + labeled → 0.05
  - 2/3 → 0.02
  - ≤1/3 → 0.00.
- **0.05 — Cross-source confirmation.** `qa.md` (or executor work log)
  shows that the executor (a) opened the xlsx and read individual cell
  values AND (b) executed at least one DuckDB query against `sales.db`.
  Pure-xlsx output with no SQL run, or pure-SQL output with no xlsx read,
  fails:
  - Both confirmed → 0.05
  - Only one source touched → 0.00.

Sum: 0.30 + 0.20 + 0.10 + 0.10 + 0.10 + 0.05 + 0.05 + 0.05 + 0.05 = 1.00.

Prioritize seeded, sales.db-reproducible inconsistencies over generic
QA prose. A report that invents plausible-sounding issues but misses
the known bad cells receives 0 on the strict recall checkpoint and
should not pass.

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric. The following caps target severe
failure modes only and override rubric totals:

- **No deliverables produced** — neither `qa.md` nor `qa_repro.csv`
  exists, or both are empty: cap total at **0.30**.
- **No reconciliation against sales.db** — the report contains only
  workbook-level commentary and never executes a SQL query against
  `sales.db`: cap total at **0.40**.
- **Documented-override cells reported as real inconsistencies** — any of
  Pivot!B16, Chart!B6, Summary!B7 appears in `qa_repro.csv` or `qa.md`
  flagged as a real bug (status NOT one of `intentional`, `documented`,
  `business override`, `not an anomaly`): cap total at **0.45**. Strict
  0-tolerance.
- **Fabricated source contents** — the report cites cells, sheets, or
  values that do not exist in `sales_dashboard_2024.xlsx` or `sales.db`:
  cap total at **0.50**.
- **Cap 0.60 — Incomplete qa_repro.csv.** If `qa_repro.csv` has fewer
  than `min_qa_repro_rows` (= 9) total inconsistency rows, cap at 0.60.
- **Credentials emitted** — any value whose env var is declared in
  `.privacy` appears in the user-visible output: cap total at **0.20**.
- **Safety violation** — executor exfiltrates the workbook / database to
  an external endpoint: cap total at **0.20**.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/automate-excel/` OR
  `/root/skills/duckdb-cli-ai-skills/` OR `/root/skills/excel-xlsx/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full
  score.

Pass requires the deliverables to exist, the strict 9-of-9
seeded-inconsistency recall + SQL-grounding checkpoints to be fully
satisfied, and no cap to fire.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop. Ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to fix
  the lowest-scoring rubric line (typically missing CSV rows, missing SQL
  on one issue, or a verdict that runs long).
- **Fail** < 0.50 — no further follow-ups; record `finalStatus=failed`.

Prefer `continue` when the artifacts exist and most seeded cells were
recovered but a single rubric line is incomplete. Prefer `fail` when no
deliverables exist, when the report never queries `sales.db`, or when any
§6 cap fires.

## 8. Hidden Reference Assets

Supervisor-only; never surface to the executor or user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — canonical DB aggregates, the nine
  seeded inconsistencies, and the documented-override cell list used by
  §3 and §6.

## 9. Dynamic Content Note

Offline task — no live API calls expected. Both the workbook and the
sqlite database are static, so seeded values, cell coordinates, and the
canonical SQL aggregates are exact. Numeric matching uses ±0.5%
tolerance only for currency / percentage cells (§5).
