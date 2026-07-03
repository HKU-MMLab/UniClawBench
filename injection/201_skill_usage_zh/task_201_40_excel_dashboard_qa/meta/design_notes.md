# Design notes — task_101_40_excel_dashboard_qa

Internal archive only. NOT injected into the executor or supervisor at run time.

## Workbook construction

`sales_dashboard_2024.xlsx` contains:

- A `Raw` sheet that is the source of truth for transactions in 2024.
- Pivot / Chart / Summary sheets with calculations derived from `Raw`.
- 9 seeded numerical/structural anomalies on the calculation sheets that are
  reproducible by aggregating `Raw` (see `ground_truth.json.seeded_anomalies`).
- 3 calculation cells (`Pivot!B12`, `Chart!B5`, `Summary!B6`) that mismatch
  `Raw` but each carries an Excel cell COMMENT documenting an out-of-band
  business reason (CFO memo, RMA returns adjustment, audit holdback). These
  are intentional overrides — listing them as material anomalies is a
  false-positive failure mode.

Reading cell comments (via `openpyxl` `cell.comment` or equivalent) is the
intended way to disambiguate. Competent dashboard QA inspects comments
before flagging.

## Failure modes the rubric is calibrated against

- Not opening the workbook at all and only producing generic QA prose.
- Opening only the calculation sheets and never reconciling against `Raw`.
- Listing all 12 mismatches (9 real + 3 documented overrides) without
  checking comments.
- Skipping the CSV deliverable.
- Producing the artifacts but never reading the declared spreadsheet/SQL
  skills.

## Skill declarations

`excel-xlsx`, `automate-excel`, `duckdb-cli-ai-skills` are all genuinely
useful here: `excel-xlsx` for openpyxl-style reads (including comments),
`automate-excel` for higher-level workbook walks, and `duckdb-cli-ai-skills`
for one-line SQL reproductions over the `Raw` sheet.

## Round 1 hardening (2026-04-30)
- Added §5 CP "Structural-anomaly cell-id precision" 0.07 (exact sheet+cell
  coord required; off-by-one/adjacent cells not credited).
- Existing GT already contains the structural seeded anomaly `Pivot!A5`
  (category `missing_total_row`); the new CP filters `seeded_anomalies`
  on category contains `"structural"` or `"missing"`. NO GT additions —
  the CP reads the existing list. Note: only one structural-category
  item exists today (Pivot!A5); CP wording uses "all structural-category
  cells" so it remains stable if future R2 adds more.
- Shaved 0.07 from "Seeded-anomaly recall" (0.25→0.18).
- Target: opus 0.85 → ~0.78 (opus reported `Pivot!B5`/`Pivot!B11` for the
  structural defect — both off-target — losing 0.07. May need second
  anchor in R2.

## Round 2 hardening (2026-04-30) — second anchor
- R1 added structural-anomaly precision CP (0.07). Score dropped 0.85→0.78.
- Added §5 CP "Documented-override explicit-naming precision" 0.06.
- Added GT field documented_override_cells (companion to existing
  `expected_excluded_decoy_cells`; cleaner schema for the new CP).
- Shaved 0.06 from "SQL realism and breadth" (0.10→0.04).
- Target: opus 0.78 → ~0.62 (loses 0.06 if opus silently excludes documented
  overrides without naming them, which is its typical behavior).

## Round 3 hardening (2026-04-30) — third orthogonal anchor
- After R1+R2 (structural cell-id + override naming), score stuck at 0.78.
- R3 added §5 CP "Per-anomaly impact-quantification + confidence" 0.10 (≥7/9 strict).
- Added GT fields per_anomaly_required_fields + confidence_label_acceptable_values + min_anomalies_with_impact_fields.
- Shaved 0.10 from Numeric accuracy (0.10→0.00; folded into seeded-anomaly recall + CSV-completeness which already enforce the same numeric tolerance implicitly, eliminating the redundancy).
- Target: opus 0.78 → ~0.60 (loses 0.10 if impact_usd/confidence fields absent; opus typically gives expected/observed but not USD impact).

## Round 4 hardening (2026-04-30) — fourth anchor
- After R1+R2+R3, score 0.68.
- R4 added §5 CPs "Per-anomaly recommended-fix precision" 0.07, "Per-anomaly responsible_team identification" 0.06.
- Added GT fields per_anomaly_remediation_required_fields + responsible_team_acceptable_values + min_anomalies_with_remediation.
- Shaved 0.13 from SQL reproductions (0.15→0.10, -0.05), Seeded-anomaly recall (0.18→0.13, -0.05), CSV completeness (0.15→0.12, -0.03).
- Final §5 sum: 0.10 + 0.10 + 0.10 + 0.13 + 0.00 + 0.05 + 0.04 + 0.12 + 0.07 + 0.06 + 0.10 + 0.07 + 0.06 = 1.00.
- Target: opus 0.68 → ~0.50.

## Round 5 hardening (2026-04-30) — cap for incomplete qa_repro
- After R1+R2+R3+R4, score 0.75 (went UP in R4 — anchors backfired).
- §6 added "Cap 0.60 — Incomplete qa_repro.csv" (≥9 rows AND ≥7 with recommended_fix).
- Added GT fields min_qa_repro_rows + min_rows_with_recommended_fix.
- Target: opus 0.75 → ~0.60 if rows or recommended_fix missing.

## Round 10 hardening (2026-04-30) — documented-override misflag cap
- Score still continue 0.60 after R5 cap.
- §6 added "Cap 0.45 — Documented-override misflagged" (strict 0-tolerance — none of Pivot!B12, Chart!B5, Summary!B6 may be flagged as real anomaly).
- Added GT fields max_documented_override_misflags: 0 + strict_override_handling: true.
- §5 weights unchanged (sum still 1.00). Lower cap (0.45) reinforces the existing 0.60 false-positive cap with a stricter floor.
- Target: opus 0.60 → ~0.45 if any documented override misflagged.

## Cleanup pass (2026-04-30) — remove hardening_too_strict anchors
- Per FAILURE_ROOT_CAUSE_ANALYSIS.md P1: removed metadata fields not in prompt (impact_usd, confidence_label, recommended_fix, responsible_team).
- KEPT §5 R1 structural-cell precision + R2 documented-override naming + §6 R10 documented-override misflag cap (all align with prompt).
- DELETED §5: impact-quantification (0.10), recommended-fix (0.07), responsible_team (0.06).
- MODIFIED §6 R5 cap: removed recommended_fix portion, kept 9-row floor.
- Restored 0.23 weight to original CPs.

## Review pass (2026-04-30) — cross-source SQL+xlsx redesign

User feedback (review_record Task 40):
1. Data volume too small — increase scale.
2. SQL was only nominally relevant — make SQL the core mechanic.
3. Need a task that validates xlsx vs SQL consistency and seeds bugs in xlsx.

### Sources redesign
- **NEW** `sources/sales.db` — sqlite "source of truth" with 2400 rows in a
  single `sales(txn_id, txn_date, region, product, units, unit_price, revenue)`
  table. 4 regions (NA / EMEA / APAC / UK), 4 products (Alpha / Beta /
  Gamma / Delta), full year 2024 dates, weighted region/product
  distributions (deterministic — `random.seed(20240430)`).
- Canonical aggregates (computed once at build time, baked into
  `ground_truth.canonical_db_aggregates`):
  - Total revenue: 45,167,871.87
  - Revenue/region: NA 15.58M, EMEA 11.08M, APAC 10.72M, UK 7.79M
  - Revenue/quarter: Q1 11.60M, Q2 10.63M, Q3 11.49M, Q4 11.45M
  - Units/product: Alpha 213,024, Beta 217,401, Gamma 193,472, Delta 112,544
  - Top region: NA (34.5%)
  - Avg txn revenue: 18,819.95 (= total / 2400)
- **REWRITTEN** `sources/sales_dashboard_2024.xlsx` — Raw sheet now mirrors
  the 2400 DB rows; Pivot / Chart / Summary sheets are "derived from
  sales.db" with seeded bugs.

### Seeded inconsistencies (9 total, must all be caught — STRICT 9/9)
1. **Pivot!B3 — aggregation_error** — EMEA 110,777,936 (10x inflated vs
   sales.db 11,077,793.60). Bug type: wrong SUMIF/aggregation.
2. **Pivot!B5 — missing_region** — UK = 0 although sales.db has UK
   transactions worth 7,786,650.98. Bug type: missing region.
3. **Pivot!B11 — quarter_rollup_error** — Q3 = 11,585,204.78 vs sales.db
   11,485,204.78 (overstated by exactly 100,000).
4. **Pivot!B12 — wrong_date_filter** — Q4 = 0; date filter excludes Q4
   transactions. sales.db Q4 = 11,447,163.62.
5. **Pivot!A6 — missing_total_row** — no Grand Total row after the
   four-region pivot.
6. **Chart!A3 — typo_product_name** — "Bata" instead of canonical "Beta"
   from sales.db.
7. **Chart!B5 — wrong_value** — Delta units = 1,125,440 (10x sales.db
   total of 112,544).
8. **Summary!B2 — wrong_value** — Total Revenue 22,583,935.93 (≈half of
   sales.db total 45,167,871.87).
9. **Summary!B5 — average_formula_error** — avg = total/500 = 90,335.74
   instead of total/COUNT(*) = 18,819.95.

Categories covered: aggregation_error, missing_region,
quarter_rollup_error, wrong_date_filter, missing_total_row,
typo_product_name, wrong_value, average_formula_error (8 distinct
categories — `anomaly_types_min` set to 6 to give some slack on category
labelling differences).

### Documented-override decoys (3, must NOT be flagged as bugs)
- Pivot!B16 — CFO catalog-migration credit (-12,500), comment cites
  MEMO-CFO-2024-Q4-03. Disagrees with sales.db on purpose.
- Chart!B6 — RMA returns adjustment (-847 units), comment cites RMA-2024.
- Summary!B7 — Q4 audit-holdback "~$30k under audit", comment cites
  Crowe LLP / AUD-2024-CLW-Q4.

### Eval rule shifts
- §5 redesigned around **STRICT 9-of-9 floors** on the two core CPs:
  - 0.30 — Strict seeded-inconsistency recall (9/9 binary).
  - 0.20 — DuckDB SQL grounded against sales.db (9/9 binary; queries
    must reference the `sales` table).
- 0.10 each — Numeric accuracy of xlsx_value / sql_value pairs, Category
  coverage (≥6/8), CSV completeness (9/9 rows binary).
- 0.05 each — Verdict length, Structural-cell precision (Pivot!A6),
  Documented-override naming (3/3), Cross-source confirmation (xlsx + SQL
  both touched).
- §5 sum: 0.30 + 0.20 + 0.10 + 0.10 + 0.10 + 0.05 + 0.05 + 0.05 + 0.05 = 1.00.
- §6 caps include new "No reconciliation against sales.db" 0.40 and
  retained "Documented-override misflagged" 0.45.

### Prompt changes (English)
- First paragraph naturally names all three skills (excel-xlsx,
  automate-excel, duckdb-cli-ai-skills) and points executor to both
  sources/sales.db and sources/sales_dashboard_2024.xlsx.
- No brackets.
- Prompt explicitly states "wherever the dashboard disagrees with what a
  fresh SQL query on sales.db produces, that is a bug worth flagging" —
  matching the strict 9/9 evaluation.
- Documented-override heads-up is preserved so the cell-comment decoys
  remain a fair test.

