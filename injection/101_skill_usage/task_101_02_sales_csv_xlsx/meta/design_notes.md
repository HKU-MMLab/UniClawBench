# Design notes — task_101_02_sales_csv_xlsx

Internal-only archive. Not loaded by the supervisor and not visible to the
executor. Captures version-design context that should not appear in the
hidden eval rule.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 capping at 1.00 on this task — the
  workbook checkpoints are fully nailed and there is no narrative pressure
  on the deliverable. Replicate the R5 retighten pattern that worked on
  task_15: combine multi-part output (a `Notes` sheet or sibling
  `notes.md`) with a concrete-anchored dimension coverage line.
- Public prompt rewritten to ask for the narrative naturally
  ("how revenue breaks out per currency, how it moves month over month,
  how the stores compare, what FX methodology you used, and how discounts
  factored in") without enumerating the five dimensions or revealing the
  scoring keywords.
- New §5 anchor "Currency-month dimension coverage" at weight 0.15
  requires concrete coverage of all 5 of 5 dimensions. Each dimension's
  keyword set in `ground_truth.topic_dimension_keywords` is consulted;
  dimensions are credited only when keyword mentions are paired with
  concrete numbers from the workbook.
- The five dimensions (per_currency_total, monthly_decomposition,
  store_breakdown, fx_methodology, discount_handling) cover currency,
  time, geography, FX-method, and price-mechanic axes — all directly
  derivable from the source CSVs. `store_breakdown` accepts both
  `EU` and `Europe` since the source data has Berlin/Paris stores
  rather than a literal `EU` label.
- Rebalance to keep weights = 1.00:
  formula-backed cells 0.20→0.13 (-0.07) and USD-conversion-correctness
  0.20→0.12 (-0.08) jointly fund the new 0.15 line.
  Final total: 0.10 + 0.15 + 0.13 + 0.12 + 0.10 + 0.10 + 0.10 + 0.05
  + 0.15 = 1.00.
- success_threshold (0.9) and §6 score caps unchanged.
- GT additions: `topic_dimensions`, `topic_dimension_keywords`,
  `min_topic_dimensions_covered`.

## Round 6 hardening (2026-04-30) — pass trim
- Currently pass 1.0; trim by adding currency edge-case CP (0.05).
- Shaved 0.05 from Currency-month dimension coverage (0.15 → 0.10;
  tiers rebalanced to 5/5 → 0.10; 4/5 → 0.03; ≤3/5 → 0.00).
- Target: opus 1.0 → ~0.95 (still pass; small mean drop).
- §5 sum: 0.10 + 0.15 + 0.13 + 0.12 + 0.10 + 0.10 + 0.10 + 0.05 +
  0.10 + 0.05 = 1.00.

## Review pass (2026-04-30)

User feedback on Task 2 (review_record.md):
1. 不要这么多括号 — rewrite prompt as natural prose without parentheses.
2. 增加对具体数值的检查 — add explicit numeric GT-value checks (not just
   file existence), e.g. USD totals must equal specific values, FX
   rates must match GT.

### Prompt changes
- Removed every parenthesis from the prompt; rephrased the bracketed
  asides as inline natural prose (em-dashes, commas).
- Skill mention moved into the first sentence: "please use the
  excel-xlsx skill to build the workbook" — no longer a tail line.
- Trimmed colons and tightened to user-spoken cadence ("Hey, can you
  help me wrap up our Q1 retail export?").
- No rubric keyword leakage — kept dimension hints natural ("how
  revenue breaks out per currency, how it moves month over month",
  etc.) without naming the five dimension keys.

### Eval changes
- §5 restructured to 12 checkpoints, sum = 1.00 (verified):
  0.08 + 0.12 + 0.10 + 0.12 + 0.10 + 0.10 + 0.08 + 0.05 + 0.10
  + 0.05 + 0.05 + 0.05 = 1.00.
- New strict numeric checks calling out the actual GT values inside
  the rubric text, so the supervisor can verify directly:
  - Workbook USD total must equal **44336.84** within ±0.05.
  - All 6 per-currency subtotals listed inline (AUD 5974.36, CAD
    5104.88, EUR 10125.21, GBP 5525.02, JPY 5235.32, USD 12372.05),
    each within ±0.10.
  - Per-row USD strict match (5/5 hidden sample rows must match both
    `fx_rate` within ±0.000005 AND `amount_usd` within ±0.05).
  - Sales row count must equal 240 (strict, not ≥).
  - Audit unmatched-FX count must equal 0 (strict).
- Tightened to all-or-nothing where prompt implied "all":
  - Per-row USD: was "≥ 4 of 5", now "all 5 of 5" → 0.12 binary.
  - Currency dimension coverage: was tiered 5/5 → 0.10, 4/5 → 0.03,
    ≤3/5 → 0.00; now strict 5/5 → 0.10, otherwise → 0.00.
  - Per-currency subtotal: now requires all 6 currencies present.
- New CP "Narrative-numeric anchor match" (0.05) — narrative must
  carry at least one workbook-anchored figure (workbook USD total
  ±0.50 or any per-currency subtotal ±1.00) presented as a
  finance-readable figure.
- New CP "Unmatched-FX accuracy" (0.05) — strict equality with GT
  expected count of 0.

### GT changes
- Added `tolerance_total_usd` (0.05), `tolerance_currency_subtotal_usd`
  (0.10), `tolerance_fx_rate` (0.000005) so the supervisor sees
  numeric thresholds explicitly.
- Added `expected_audit_source_row_count` (240) and
  `expected_audit_workbook_usd_total` (44336.84) for the audit-sheet
  numeric anchors.
- Added `narrative_numeric_anchor` block describing primary/fallback
  acceptance for the new narrative-anchor CP.
- All previously captured numbers (per-currency subtotals, sample
  rows with order_id + fx_rate + amount_usd) are kept and now
  directly cited from §5 rubric text.
