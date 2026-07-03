# Design notes — task_101_14_excel_pivot_chart

Archive of construction-side notes that should not appear in the hidden
eval_rule (per skill_usage rewrite spec rule 2). Not injected into runs.

## Skill-trace caps (deprecated)

Earlier iterations capped scores when the agent's trace did not show a read
of `office-document-specialist-suite` or `excel-weekly-dashboard` SKILL.md
files (cap 0.89 each). These were removed because:

- They re-state the public skill declaration in `skills_declared` rather
  than gate an extreme-failure mode.
- Trace inspection is brittle (skill code can be invoked without an
  explicit SKILL.md read appearing in the visible trace).
- Per spec rule 6, §6 caps should target extreme edge cases only and stay
  at ≤ 0.7. A 0.89 cap on a process step is the wrong shape.

If skill-routing fidelity needs to be re-audited later, do it at the
benchmark-aggregate level (cross-task analysis), not inside the per-task
hidden rule.

## Other re-stated checkpoints (deprecated)

Removed caps that simply duplicated checkpoints with values > 0.7:

- Missing `reconciliation.csv` (was cap 0.86) — already covered by the
  0.20 reconciliation checkpoint.
- Missing `QA_Checks` sheet (was cap 0.88) — covered by structure +
  reconciliation checkpoints.
- Reconciliation total not tying to pivot (was cap 0.88) — same.
- `booked_month` used instead of `correction_month` (was cap 0.75) —
  already penalised through monthly-momentum and reconciliation
  checkpoints.

## Retained extreme-failure caps

- 0.30 cap on no workbook — the only deliverable; without it nothing else
  is auditable.
- 0.50 cap on voids included in revenue — the most common misread of the
  contract, worth a hard ceiling beyond the 0.12 cleaning checkpoint.
- 0.55 cap on fabricated source data — task-integrity violation; the
  executor must compute from the provided CSV.

## v8 hardening round 3 (2026-04-29)

Round-2 moderate hardening (0.10–0.12 anchors, ≥4-of-5 partial credit)
was insufficient — opus-4.6 still reliably cleared 0.90. This round
applies strict 5/5 all-or-nothing dimension coverage at weight 0.15.

- Public prompt rewritten to embed five analysis dimensions as
  natural-voice clauses (no enumerated list): region × product matrix,
  monthly progression with MoM deltas, top/bottom performers per region,
  void / return / late-adjustment isolation, and a year-over-year /
  quarter-over-quarter context hint.
- §5 rebalanced: Pivot values 0.20 → 0.15 (-0.05); Reconciliation + QA
  tie-out 0.20 → 0.15 (-0.05); Workbook structure 0.12 → 0.10 (-0.02);
  Cleaning rules 0.12 → 0.10 (-0.02); Monthly momentum 0.12 → 0.11
  (-0.01). Total cut = 0.15, added as new "Topic dimension coverage"
  anchor.
- New anchor scoring: 5/5 → 0.15; 4/5 → 0.05; ≤3/5 → 0.00. Stepped
  cliff: missing one dimension drops 0.10; missing two+ drops the
  full 0.15.
- ground_truth.json gains `topic_dimensions` list and
  `min_dimensions_covered: 5`.
- score caps and success_threshold (0.9) unchanged.
- Final weights: 0.10 + 0.15 + 0.10 + 0.11 + 0.08 + 0.08 + 0.08 +
  0.15 + 0.15 = 1.00.

## v8 hardening round 4 (2026-04-29)

Round 3 strict 5/5 dimension anchor still didn't push the supervisor
below 0.85 — abstract dimension descriptions left too much room for
generous interpretation. Round 4 adds a **second anchor** ("Numeric
precision") at weight 0.08 layered on top of the existing dimension
anchor.

Numeric-precision anchor: 5 high-signal `(region, product)` corner /
spotlight cells from the pivot matrix (UK/Stationery 46275.49,
NL/Bag -98.17, EIRE/Kitchen 32993.64, AU/Stationery -2920.02, DE/Bag
23622.64). Mix of large positive, small negative, and corner cells —
hard to nail all 5 without actually computing the pivot end-to-end.
Scoring: ≥3/5 within ±0.05 USD → 0.08, 2/5 → 0.04, ≤1 → 0.

§5 rebalanced: cleaning rules 0.10 → 0.06 (-0.04); existing "Topic
dimension coverage" 0.15 → 0.11 (-0.04); new "Numeric precision"
anchor at +0.08. Final weights:
0.10 + 0.15 + 0.06 + 0.11 + 0.08 + 0.08 + 0.08 + 0.15 + 0.11 + 0.08 = 1.00.

ground_truth.json gains `expected_pivot_cell_corner` (5 anchor cells)
plus `expected_pivot_cell_corner_min: 3` and tolerance 0.05. score
caps and success_threshold (0.9) unchanged.

## Round 7 hardening (2026-04-30) — pass trim
- Currently pass 1.0; add MoM sign-change note CP (0.05).
- Shaved 0.05 from Numeric precision (pivot anchor cells) (0.08 → 0.03).
- Target: opus 1.0 → ~0.95.

## Review pass (2026-04-30)

User feedback (review_record Task 14): the 0.15 reconciliation + QA
checkpoint did not specify what content to verify in
`reconciliation.csv` or the `QA_Checks` sheet — it only checked
"reconciles to pivot grand total" and "rules flagged as applied". This
left room for shallow placeholder content (hard-coded "PASS" strings,
header-only CSV) to score full credit. Added explicit content checks.

**Prompt YAML changes** (`tasks/101_skill_usage/task_101_14_excel_pivot_chart.yaml`):
- Skill mention pulled into the first paragraph as natural language —
  "use the office-document-specialist-suite skill together with the
  excel-weekly-dashboard skill" — instead of the trailing "use the
  workspace's spreadsheet and analysis skills" sentence.
- Removed all parentheses (rule 6). Em-dashes used in their place.
- Removed the bold-asterisk emphasis on `**net revenue**` (markdown
  emphasis is a tell of templating). Kept the inline-code style for
  literal column / status names because they refer to source columns.
- Removed the trailing instruction sentence about skills (now in §1).

**eval_rule changes** (`references/eval_rule.md`):

§4 ground-truth snapshot now records explicit `reconciliation_row_totals`
(booked +512462.43 / 180 rows, return -85402.77 / 21 rows, void 0.00 /
12 rows, late_adjustment -18129.95 / 27 rows, sum 408929.71) and the
five named QA checks with PASS expectations.

§5 0.15 "Reconciliation + QA tie-out" rewritten as strict, content-based:
- Per-status row counts must match exactly (180/21/12/27).
- Per-status `included_net_revenue` must match the GT row totals
  within ±0.05 USD (booked +512462.43, return -85402.77, void 0.00,
  late_adjustment -18129.95).
- Sum of all four `included_net_revenue` rows must tie to the pivot
  grand total +408929.71 within ±0.05 USD.
- `QA_Checks` sheet must surface all five named checks
  (void_rule_applied, return_rule_applied, late_adjustment_rule_applied,
  reconciliation_to_pivot_tieout, row_count_total) with PASS status
  AND a formula-backed / directly traceable check expression — not a
  hard-coded string.
- Strict pass/fail at this checkpoint: any single miss → 0.00 (no
  partial credit). This is consistent with global rule 8.

§5 0.11 "Topic dimension coverage" tightened: 5/5 → 0.11, ≤4/5 →
0.00 (was 4/5 → 0.04). The prompt explicitly enumerates all five
analysis concerns, so partial dimension coverage is no longer
rewarded.

§5 0.03 "Numeric precision (pivot anchor cells)" tightened: all 5/5
required → 0.03, ≤4/5 → 0.00 (was 3/5 → 0.03, 2/5 → 0.015). Removes
the soft-cliff partial-credit branch on a pure spot-check anchor.

§5 weights unchanged on totals. Sum verified:
0.10 + 0.15 + 0.06 + 0.11 + 0.08 + 0.08 + 0.08 + 0.15 + 0.11 + 0.03
+ 0.05 = 1.00.

**ground_truth.json changes** (`references/ground_truth.json`):
- `expected_counts` gains `booked: 180` (was missing — only void /
  return / late_adjustment / total were specified).
- New `reconciliation_row_totals` block — per-status authoritative
  values for `row_count`, `gross_signed_revenue_usd`,
  `excluded_revenue_usd`, `included_net_revenue_usd`, plus the
  `sum_included_net_revenue_usd: 408929.71` tieout target and
  tolerance.
- New `qa_check_expected_results` array — five named checks
  (void_rule_applied, return_rule_applied, late_adjustment_rule_applied,
  reconciliation_to_pivot_tieout, row_count_total) each with
  expected_status PASS and a `validates` description tying back to
  the row totals.
- New `qa_check_required_count: 5` and
  `qa_check_must_be_formula_backed: true` flags.
- Verified against source `sales_2011_q1.csv` (240 rows: 180 booked +
  21 return + 12 void + 27 late_adjustment; net total 408929.71).

**Score caps & success_threshold**: unchanged (0.30 no workbook,
0.50 voids in revenue, 0.55 fabricated source; threshold 0.9).
