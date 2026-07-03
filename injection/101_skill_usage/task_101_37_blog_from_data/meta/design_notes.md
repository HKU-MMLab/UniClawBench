# Design notes — task_101_37_blog_from_data

Internal-only. Not injected into the executor or supervisor.

## Skill-usage policy lineage

Earlier eval_rule revisions hard-capped at 0.89 when no read of any
declared skill (`csv-pipeline`, `python-dataviz`,
`newsletter-blog-writer`) appeared in the trace. The current rule
folds those three checks into a single 0.40 extreme-failure cap, on
the principle that score caps should target genuine extreme
failures rather than restate per-skill checkpoints.

## Edge cases targeted by §6 caps

- 0.30 caps: zero deliverables, credential leakage, fabricated
  numerical claims (most extreme correctness/safety failures).
- 0.40 cap: total skill-consultation absence.
- 0.50 cap: scope blowout / destructive operations outside the
  workspace.

## Deliverable rationale

The three deliverables are mutually reinforcing: the post cites
numbers, the workbook computes them with formulas, the cover image
visualizes the same monthly arc. The rubric's 0.20 + 0.20 split on
callouts and workbook reflects that internal consistency is the
load-bearing requirement.

## v8 hardening round 3 (2026-04-29)

opus-4.6 was still passing this task even with moderate (0.10–0.12,
≥4-of-5) dimension coverage anchors, so this round adds a strict 5/5
all-or-nothing gate on blog narrative coverage. The public prompt now
naturally asks for a year-in-review angle that pulls together five
dimensions — monthly totals & MoM trend, regional / store ranking,
peak month / seasonal anchor, AOV vs order-count perspective on
basket changes, and a forward-looking takeaway for next quarter —
phrased as the editorial direction a marketing colleague would
actually request, not as an enumerated list. The new §5 anchor
"Topic dimension coverage" is weight 0.15 with strict scoring: 5/5 →
full 0.15, exactly 4/5 → 0.05, ≤3/5 → 0.00. To keep §5 weights
summing to 1.00, the post-length, conclusion, and chart-x-axis
anchors were each trimmed (0.15→0.10, 0.10→0.05, 0.10→0.05). GT now
carries `topic_dimensions` (5 items) plus
`min_dimensions_covered: 5`. success_threshold and score caps are
unchanged.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 holding around 0.95 here. R5's
  most effective lever was multi-part output + a second
  entity-precision anchor; we add the precision lens for this task by
  forcing the post to inline specific numeric values rather than
  outsourcing them to the workbook.
- New "Data callout precision" line at weight 0.08 requires the post
  to cite at least 4 of 5 specific numeric callouts within ±0.5%:
  total_revenue_usd 13,457,369.32; total_orders 18,153; peak_month
  2010-11; peak_month_revenue_usd 1,970,772.86; uk_country_share_pct
  92.95%. Human-rounded equivalents ("$13.5M", "~93%") are accepted
  when paired with the right entity.
- The five values include two that already live in `required_metrics`
  (total revenue, total orders), the peak-month label and revenue
  (which the previous "concrete callouts" line already pressured),
  plus the UK country share — the latter forces the executor to
  actually compute the regional ranking rather than hand-wave it.
- Rebalance to keep the rubric total at exactly 1.00:
  Three concrete callouts 0.20→0.16 (-0.04) and Workbook structure
  0.20→0.16 (-0.04) — the two heaviest checkpoints — jointly fund
  the new 0.08 line. Final total: 0.10+0.16+0.05+0.15+0.10+0.05+
  0.16+0.15+0.08 = 1.00.
- Score caps in §6 unchanged. success_threshold in YAML unchanged.
- GT additions: `data_precision_callouts`,
  `callout_value_tolerance_pct`, `min_callouts_with_value`.

## v8 hardening round 9 (2026-04-30)

Round-8 measurements showed this task at PASS ≈0.95. Round 9 adds a
small auxiliary CP "Regional second-anchor callout precision" at
weight 0.05. The post must cite at least 2 of 3 regional second-tier
anchors — second_country_share_pct (EIRE ~4.06%), eire_peak_month
(2010-11), nl_monthly_share_pct (NL ~2.99%) — within ±1.0pp of GT
(month must match exactly). Stepped: 3/3 → 0.05, 2/3 → 0.025,
≤1/3 → 0.00. Rebalance: Topic dimension coverage 0.15 → 0.10 (-0.05)
funds the new line; tier credits scaled (5/5 → 0.10, 4/5 → 0.04).
Final §5 sum: 0.10+0.16+0.05+0.15+0.10+0.05+0.16+0.10+0.08+0.05 =
1.00. GT gains `regional_second_anchor_callouts` (3 entries),
`min_regional_callouts_within_tolerance: 2`, and
`regional_tolerance_pct: 1.0`. Score caps and success_threshold
unchanged.

## Round 10 hardening (2026-04-30) — post-depth cap
- Round-9 measurements: continue 0.865 (was pass before R9).
- §6 added "Cap 0.65 — Insufficient post depth" (post.md must have
  ≥700 words AND ≥3 distinct concrete data callouts in body).
- Added GT fields min_post_word_count_strict + min_distinct_callouts_required.
- §5 weights unchanged (sum still 1.00).
- Target: opus 0.865 → ~0.715 if post lacks depth.

## Review pass (2026-04-30)
Applied global review rules + GT correctness audit.

### Prompt rewrite (task YAML)
- Pulled all three skills (csv-pipeline, python-dataviz,
  newsletter-blog-writer) into the first paragraph as the natural
  request, replacing the prior "Please use the workspace's CSV,
  dataviz, and long-form drafting skills" trailing line.
- Removed every parenthesis/bracket from the public prompt
  (previous prompt had ~7 `(...)` clauses describing dimensions).
  Re-flowed the editorial direction into prose.
- Added an explicit "use the same all-store totals in the post that
  drive the workbook" sentence so the executor cannot quietly cite
  UK-only November ($1.97M) while the workbook reports the all-store
  November total ($2.07M) — matches the data_precision_callouts
  expectation for peak_month_total_revenue_usd.
- Prompt is fully ENGLISH (compliance with critical rule).

### GT corrections
- **eire_peak_month**: 2010-11 → 2010-01. Verified directly from
  CSV: EIRE Jan = $100,824.27 vs Nov = $47,943.37; January is the
  true monthly peak. Previous GT was wrong, so any executor that
  computed the right answer was being penalized.
- **second_country_share_pct**: 4.06 → 4.1431 (recomputed from CSV:
  EIRE 557,556.64 / 13,457,369.32 = 4.1431%).
- **nl_monthly_share_pct**: 2.99 → 2.9113 (NL 391,783.08 / total =
  2.9113%). Both still within ±1.0pp tolerance, but reference value
  now exact.
- **peak_month_top_store_share_pct**: 95.0 → 95.0032 (UK Nov
  $1,970,772.86 / all-store Nov $2,074,426.98).
- **uk_country_share_pct**: kept at 92.9456% (already exact).
- Added `all_store_orders: 2584` to peak_month_row.
- `callout_notes` now spells out that
  peak_month_total_revenue_usd is the all-store November figure
  $2,074,426.98 (UK 1,970,772.86 + EIRE 47,943.37 + NL 55,710.75) to
  remove the historical ambiguity flagged in review_record.

### eval_rule.md strictness
All §5 lines re-stated as strict all-or-nothing:
- 0.16 callouts: any of three missing or unreproducible → 0.
- 0.16 workbook: any of MoM formulas / share formulas /
  formula-driven store peak month / Callouts cell references
  missing → 0 (was implicit).
- 0.10 dimension coverage: 5/5 → 0.10, anything fewer → 0
  (removed the "exactly 4 of 5 → 0.04" tier).
- 0.05 regional second-anchor: 3/3 within tolerance → 0.05,
  anything fewer → 0 (was tiered 3/2/≤1; also bumped
  `min_regional_callouts_within_tolerance` 2 → 3 in GT to match).
- 0.08 data precision: 5/5 → 0.08, anything fewer → 0
  (removed "exactly 4/5 → 0.04" tier; GT
  `min_callouts_with_value` becomes effectively 5).
- Aligned eval's peak_month_revenue_usd reference ($1,970,772.86)
  with GT's all-store value ($2,074,426.98), with explicit
  semantic-credit clause for executors that pair the UK-only Nov
  figure with the all-store Nov total. Eliminates the known
  UK-only-vs-all-store mismatch flagged in review_record.

### §5 sum verification
0.10 + 0.16 + 0.05 + 0.15 + 0.10 + 0.05 + 0.16 + 0.10 + 0.05 +
0.08 = 1.00. Verified.

### Score caps unchanged
§6 caps (0.30/0.40/0.50/0.65) and success_threshold 0.90 untouched
per global rule "do not modify existing score caps".
