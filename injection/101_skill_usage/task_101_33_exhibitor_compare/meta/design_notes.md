# Design notes — task_101_33_exhibitor_compare

Internal-only archive. Not loaded by the supervisor and not visible to
the executor.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 capping at 1.00 here — the
  comparison table, ROI table, recommendation paragraph, and workbook
  cover all the structural rubric and there is no narrative pressure
  on the analysis. Replicate the R5 retighten pattern (multi-part
  output + concrete-anchored dimension coverage) with a tradeshow
  comparison lens.
- Public prompt extended naturally to ask for a short narrative
  section at the bottom of `compare.md` covering "booth economics,
  traffic estimate, vertical alignment, timing/logistics, and the ROI
  break-even math" for each show — phrased as the angles a marketing
  lead would actually walk through, not as an enumerated rubric.
- New §5 anchor "Tradeshow comparison dimension coverage" at weight
  0.15 requires concrete coverage of all 5 of 5 dimensions. Each
  dimension's keyword set in `ground_truth.topic_dimension_keywords`
  is consulted; dimensions are credited only when keyword mentions
  are paired with concrete numbers/names from the comparison/ROI
  tables.
- The narrative section is required to be separate from the
  recommendation paragraph so the rubric does not double-count the
  ≤8-sentence recommendation against this anchor.
- Rebalance to keep weights = 1.00:
  ROI table accuracy 0.20→0.12 (-0.08) and Workbook deliverable
  0.19→0.12 (-0.07) jointly fund the new 0.15 line.
  Final total: 0.12 + 0.12 + 0.08 + 0.12 + 0.08 + 0.08 + 0.08 + 0.12
  + 0.05 + 0.15 = 1.00.
- success_threshold (0.90) and §6 score caps unchanged.
- GT additions: `topic_dimensions`, `topic_dimension_keywords`,
  `min_topic_dimensions_covered`.

## Skill use note

Two declared skills (`pdf-extract`, `business-writing`) cover the
prospectus-extraction step and the comparison/recommendation
write-up. No skill caps in §6 — skill-use signal stays in §1 grading
philosophy and §8 reference asset notes.

## Round 1 hardening (2026-04-30)
- Tightened §5 "Workbook deliverable" to require all 8 cols in single contiguous computed row (not split layout).
- Added §5 CP "Break-even precision" 0.06 (strict 3-of-3 shows).
- Shaved 0.06 from "ROI math grounded in inputs" (0.08→0.02).
- Target: opus 0.85 → ~0.70 (loses 0.06 from workbook split + 0.06 from break-even).

## Round 2 hardening (2026-04-30) — second anchor
- Task R1 dropped 0.85→0.79 (modest); add second anchor for further pressure.
- Added §5 CP "Recommendation $value citation precision" 0.06.
- Added GT field recommendation_required_dollar_anchors (top_pick=$3,740 CDA Anaheim, runner_up=$820 ACVO, tol=5%).
- Shaved 0.06 from Tradeshow comparison dimension coverage (0.15→0.09; tier values 0.15→0.09 and 0.05→0.03).
- Target: opus 0.79 → ~0.65 (loses 0.06 if recommendation paragraph doesn't cite both top-pick + runner-up dollar values).

## Round 3 hardening (2026-04-30) — push promoted task back to continue
- Task R2 promoted 0.79→0.91 after $value citation anchor was satisfied.
- R3 added §5 CP "Per-show comprehensive comparison narrative" 0.10
  (5/5 strict, requires all 3 show names + concrete numbers per
  dimension within the same head-to-head sentence/paragraph).
- Added GT fields narrative_comparison_required_dimensions,
  narrative_comparison_min_dimensions=5,
  narrative_per_dimension_must_name_all_shows=true, and
  required_show_names (3 shows).
- Shaved 0.10 split across two CPs: Workbook deliverable
  0.12→0.07 (-0.05; tiers also halved 0.12→0.07 and 0.06→0.03) and
  Tradeshow comparison dimension coverage 0.09→0.04 (-0.05; tiers
  0.09→0.04 and 0.03→0.02).
- Final §5 sum: 0.12 + 0.12 + 0.08 + 0.12 + 0.02 + 0.08 + 0.08 +
  0.07 + 0.05 + 0.04 + 0.06 + 0.06 + 0.10 = 1.00.
- Target: opus 0.91 → ~0.55 (loses 0.10 if narrative is high-level
  rather than per-dim per-show comparison; combined with prior
  break-even and workbook-strict shaves still in play, opus likely
  loses ~0.36 across the rebalanced anchor set and the new strict
  narrative line).

## Round 4 hardening (2026-04-30) — fifth anchor
- After R1+R2+R3 (workbook + break-even + $citation + narrative), score 0.84.
- R4 added §5 CPs "Per-show track-record statistic citation" 0.07, "Per-show booth-package option citation" 0.06.
- Added GT fields track_record_required_min_shows + booth_package_options_required_per_show + acceptable_track_record_phrases.
- Shaved 0.13 from ROI table accuracy (0.12→0.07, -0.05), Recommendation defensibility (0.08→0.05, -0.03), Per-show comprehensive comparison narrative (0.10→0.05, -0.05; tiers also halved 0.10→0.05 and 0.04→0.02).
- Final §5 sum: 0.12 + 0.12 + 0.08 + 0.07 + 0.02 + 0.08 + 0.05 + 0.07 + 0.05 + 0.04 + 0.06 + 0.06 + 0.05 + 0.07 + 0.06 = 1.00.
- Target: opus 0.84 → ~0.65.

## Round 5 hardening (2026-04-30) — cap for insufficient narrative
- After R1+R2+R3+R4, score 0.84.
- §6 added "Cap 0.65 — Insufficient narrative section" (≥250 words AND all 3 show names).
- Added GT fields min_narrative_word_count + narrative_must_name_all_3_shows.
- Target: opus 0.84 → ~0.65 if narrative is brief or omits shows.

## Round 6 hardening (2026-04-30) — ROI figures citation cap
- R5's narrative cap (250 words + all-3-shows) didn't fully bite (score 0.84→0.83).
- §6 added "Cap 0.55 — Recommendation missing ROI figures" (booth_fee + staff_travel_cost cited for ≥2 of 3 shows).
- Added GT fields recommendation_required_roi_figures_per_show + min_shows_with_required_figures_in_recommendation.
- Target: opus 0.83 → ~0.55 if recommendation lacks specific cost-figure citations.

## Round 7 hardening (2026-04-30) — pros/cons structural cap
- R6 ROI figures cap didn't bite (score stayed at 0.83-0.84).
- §6 added "Cap 0.55 — Missing per-show pros/cons" (3/3 shows × ≥2 pros + ≥1 cons).
- Added GT fields per_show_pros_cons_required + min_shows_with_pros_cons + min_pros_per_show + min_cons_per_show.
- Target: opus 0.84 → ~0.55.

## Cleanup pass (2026-04-30) — remove hardening_too_strict anchors
- Per FAILURE_ROOT_CAUSE_ANALYSIS.md P1: removed 4 §5 anchors + 3 §6 caps not aligned with prompt.
- KEPT R1 Workbook deliverable (replaced) + R1 Break-even precision (both align with prompt's ROI workbook requirement).
- DELETED §5: $value citation (0.06), comprehensive narrative (0.10), track-record (0.07), booth-package (0.06).
- DELETED §6 caps: 250-word narrative, ROI figures, pros/cons.
- Restored 0.29 weight to original CPs.

## Review pass (2026-04-30) — global rules application
- **Prompt rewrite (ENGLISH, skill in first paragraph)**: Reworded
  the task field per global rules. First paragraph now opens with
  "I'm comparing 3 trade shows for our marketing budget. Please use
  the workspace's pdf-extract skill to pull facts from these
  prospectus PDFs and the business-writing skill to draft a
  recommendation." Both declared skills (`pdf-extract`,
  `business-writing`) are named in the first paragraph by their slugs.
- **Brackets removed**: Stripped all parenthetical asides from the
  prompt body. The break-even formula clause is now phrased
  prose-style ("the ceiling of cash_outlay divided by per-lead
  margin, where per-lead margin is gross margin per deal multiplied
  by the lead-to-deal conversion rate. Do not derive it from
  break-even deals.") rather than the LaTeX-style ⌈…⌉ inline.
  Narrative-section guidance is now plain prose.
- **§5 strictness sweep**: Tightened looseness flagged in shared
  rules.
  - Comparison table coverage 0.12 — kept strict (already 3×5).
  - Prospectus values backed by PDFs 0.12 — was "≥4 prospectus
    dimensions"; tightened to all 5 dimensions × 3 shows, with
    booth_fee + deposit matching show_facts.
  - Cancellation and schedule fidelity 0.08 — added explicit "strict
    3-of-3" wording.
  - ROI table accuracy 0.12 — added explicit "strict 3-of-3 shows".
  - Recommendation defensibility 0.08 — was "or for an equally
    well-argued alternative"; tightened to require exact match with
    `accepted_recommendation_pairs` (top=CDA Anaheim 2025,
    runner-up=ACVO 2025); any other pair → 0.00.
  - Workbook deliverable 0.12 — was stepped (0.12 / 0.06 / 0.00);
    tightened to all-or-nothing (0.12 / 0.00).
  - Tradeshow comparison dimension coverage 0.10 — was tiered (5/5
    → 0.10; 4/5 → 0.05); tightened to strict 5-of-5 only.
  - Break-even precision 0.06 — was tiered (3/3 → 0.06; 2/3 →
    0.03); tightened to strict 3-of-3 only.
- **§5 sum check**: 0.12 + 0.12 + 0.08 + 0.12 + 0.02 + 0.13 + 0.08 +
  0.12 + 0.05 + 0.10 + 0.06 = **1.00** ✓.
- **GT verification**: All anchors recomputed and GT-correct.
  - cash_outlay = booth_fee + staff_travel: ACVO 4500+2600=7100;
    CDA 3800+3100=6900; TX 5200+4200=9400. ✓
  - expected_gross_margin = leads × rate × margin_per_deal:
    ACVO 55×0.08×1800=7920; CDA 95×0.07×1600=10640;
    TX 70×0.06×2200=9240. ✓
  - net_contribution = gross − outlay: ACVO 7920−7100=820;
    CDA 10640−6900=3740; TX 9240−9400=−160. ✓
  - break_even_qualified_leads = ⌈outlay/(rate × margin_per_deal)⌉:
    ACVO ⌈7100/144⌉=⌈49.31⌉=50; CDA ⌈6900/112⌉=⌈61.61⌉=62;
    TX ⌈9400/132⌉=⌈71.21⌉=72. ✓
  - accepted_recommendation_pairs = `[CDA Anaheim 2025, ACVO 2025]`
    matches the highest-net-contribution and second-highest shows. ✓
- **§6 caps unchanged**: Score caps not modified per shared rule
  "不修改 score cap 数字". Existing caps remain (0.30 no
  deliverables, 0.30 fabricated sources, 0.30 scope blowout, 0.20
  credentials, 0.30 safety).
- **success_threshold (0.90) unchanged.**
