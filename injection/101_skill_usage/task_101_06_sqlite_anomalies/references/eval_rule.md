# Hidden Evaluation Rule — task_101_06_sqlite_anomalies

## 1. Grading Philosophy

Judge whether the executor delivered an honest data-quality audit of the
SQLite dump and whether at least one declared SQL/data skill in
`/root/skills/` was actually used. Prefer semantic matching of category
labels over exact-string matching: the public prompt does not prescribe key
names, so the executor may name groupings freely as long as the meaning is
unambiguous. Score caps in §6 override rubric totals when triggered.

## 2. Task Contract

Restated in supervisor terms: the executor must load
`/tmp_workspace/clawbench/sources/orders.db.sql`, audit it for the four
problem families called out in the public prompt, and emit:

- `/tmp_workspace/results/anomalies.json` — JSON object grouping findings by
  problem kind, with enough per-row identifying detail (order_id /
  order_number / pk) for the user to look up each offending record.
- `/tmp_workspace/results/anomaly_rows.csv` — one CSV row per row/rule
  violation, with columns `anomaly_type, table_name, primary_key,
  order_number, customer_id, product_id, evidence_value, lookup_sql`. A row
  that violates multiple rules appears once per rule.
- `/tmp_workspace/results/reproduce.sql` — runnable SELECT statements, one
  per issue family, that reproduce the findings.

Problem families in scope: negative unit prices, duplicated business
identifiers, broken inter-table relationships (orphan foreign keys), and
rows dated outside the December 2010 import window.

The prompt is authoritative for scope; nothing in `references/` may be used
to widen it.

## 3. Source-Selection and Target-Resolution Rules

Canonical input list (anything else is out-of-scope):

- `/tmp_workspace/clawbench/sources/orders.db.sql` — the inline SQLite dump
  shipped with this injection.

The executor is expected to rehydrate this dump into a local SQLite database
(in-memory or on-disk) before running checks. The supervisor rehydrates the
same dump to verify rubric anchors in §5.

Category-label resolution: when matching rubric categories to the
executor's groupings, accept any label whose meaning is unambiguous in
context (e.g., `negative_prices`, `negative_price_rows`, `invalid_pricing`,
`price_anomalies` all map to the negative-price category). Refuse to award
a category only when no output group plausibly maps to it.

## 4. Ground-Truth Snapshot

Structured ground truth lives at `references/ground_truth.json` (schema a:
concept-level booleans with evidence pointers).

Reference counts (verified by re-running the anchor queries on the dump):

- Negative unit prices: 3 rows
- Duplicate `order_number` groups: 2 groups (5 row memberships total)
- Orphan foreign keys: 2 rows (≥1 with missing `customer_id`, ≥1 with
  missing `product_id`)
- Out-of-window dates (date(ordered_at) > `2010-12-31`): 8 rows

## 5. Checkpoint Rubric

Weights sum to 1.00. The supervisor rehydrates `orders.db.sql` and executes
the named anchor queries; checkpoint credit is anchored to those results.
All checkpoints are strict — partial coverage of an expected row set does
not earn the weight.

| Weight | Checkpoint |
|--------|------------|
| 0.10 | `anomalies.json` exists and is a JSON object grouping findings under clearly-named categories that together cover negative unit prices, duplicate order numbers, orphan foreign keys, and out-of-window dates. Label wording is the executor's choice. |
| 0.15 | The negative-price category exactly matches `SELECT order_id FROM orders WHERE unit_price < 0` on the rehydrated dump. The reported row set must equal the anchor row set (all 3 rows present, no extras). |
| 0.15 | The duplicate-order-number category exactly matches `SELECT order_number, COUNT(*) FROM orders GROUP BY order_number HAVING COUNT(*) > 1`. All 2 expected groups must be reported, with the same `order_number` values; no extra groups. |
| 0.15 | The orphan-foreign-key category includes both expected orphan rows from anti-join queries on the rehydrated dump (one with missing `customer_id`, one with missing `product_id`). Both must be present; no false positives. |
| 0.15 | The out-of-window-date category exactly matches `SELECT order_id FROM orders WHERE date(ordered_at) > date('2010-12-31')`. All 8 rows must be reported; no extras. |
| 0.10 | Skill engagement: trace shows at least one read of a file under `/root/skills/sql-toolkit/` or `/root/skills/database-operations/`, confirming a declared SQL/data skill was consulted. |
| 0.10 | `anomaly_rows.csv` exists with the eight prompt-required columns and represents one CSV row per row/rule violation. Expected violation rows: 3 negative-price + 5 duplicate-order memberships + 2 orphan + 8 out-of-window. Rows that violate multiple rules may appear more than once with different `anomaly_type`. |
| 0.10 | `reproduce.sql` exists and contains runnable SELECT statements covering all four issue families (pricing, duplicate-identifier, broken-relationship, out-of-window). |

Total: 0.10 + 0.15 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied rubric checkpoints. The caps below
override rubric totals only for extreme-failure modes:

- **No deliverables** — none of `anomalies.json`, `anomaly_rows.csv`, or
  `reproduce.sql` is present, or all are empty/unreadable: cap total at
  **0.30**.
- **No skill engagement** — trace shows no read of any file under
  `/root/skills/sql-toolkit/` or `/root/skills/database-operations/`,
  i.e. no declared SQL/data skill was consulted at all: cap total at
  **0.65**.
- **Fabricated anomaly counts** — `anomalies.json` reports rule families
  whose row sets cannot be reproduced by any reasonable query against the
  dump (counts inflated by ≥ 50% over anchor results, or rows with
  `order_id` / `order_number` values that do not exist in the dump): cap
  total at **0.50**.
- **Credentials emitted** — any value whose env var is declared in
  `.privacy` appears in any user-visible deliverable: cap total at
  **0.20**.

Pass requires all four anchor-query rubric lines (rows 2–5 in §5) fully
satisfied AND both auxiliary deliverables (`anomaly_rows.csv`,
`reproduce.sql`) present.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops; ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to fix
  the lowest-scoring rubric line (e.g. missing CSV column, one anchor-query
  family wrong, missing reproduce.sql for one issue family).
- **Fail** < 0.50 — no further follow-ups; record `finalStatus=failed`.
  Use `fail` when no deliverables were produced, or when the four anchor
  queries are uniformly wrong, or when a §6 hard cap fires.

## 8. Hidden Reference Assets

Supervisor-only; never surface to the executor or user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — anchor counts for the four anomaly
  families.

## 9. Dynamic Content Note

Offline task. The SQLite dump is shipped inline with the injection and does
not change between runs; no live API calls are expected. If the executor's
rehydration of `orders.db.sql` somehow yields different row counts than the
anchor queries above, the supervisor's rehydration is authoritative.
