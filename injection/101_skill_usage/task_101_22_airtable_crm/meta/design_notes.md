# Design notes — task_101_22_airtable_crm

Internal-only archive. Not loaded by the supervisor and not visible to the
executor. Captures construction context that was scrubbed from the public
grading spec.

## v8 hardening round 2 (2026-04-29)

Round 1 of opus-4.6 testing showed this task at capped=1.0 pass — the
explicit deal-set / priority-queue rubric was easy to clear once active vs
terminal partitioning was correct. Hardening direction: introduce an
implicit multi-part requirement so the executor must deliver a real
"pipeline sanity check" across five dimensions instead of just the deal
lists. Prompt rewritten in natural voice asking which deals are stuck,
where owner workload is imbalanced, which stage is the worst bottleneck,
where dollar exposure is concentrated, and which terminal accounts have
effectively lapsed. Eval rule §5 adds a 0.10 "Dimension coverage" anchor
checkpoint requiring ≥4 of 5 dimensions surfaced with concrete substance
(non-generic). To rebalance to 1.00, audit.json complete cut 0.12→0.07,
totals match cut 0.13→0.10, owner followups consistent cut 0.13→0.11.
Ground truth gains `topic_dimensions` array and `min_dimensions_covered=4`.
Score cap numbers and success_threshold unchanged.

## v8 hardening round 5 (2026-04-29)

Round-2 dimension anchor (0.10, ≥4-of-5) was insufficient on its own —
opus-class executors hit cap 0.95 by satisfying every non-anchor
checkpoint plus a partial dimension match. This round adds a second §5
anchor "Deal-id precision" at weight 0.08 that requires the deliverable
package to reference, by exact deal_id string, ≥4 of 5 specific
priority-queue / active-stuck deal anchors: `D0028` (Zorg, Grace T.,
rank 1), `D0027` (Cogswell, Frank L., rank 2), `D0023` (Parr, Bob K.,
rank 4), `D0011` (Massive Dynamic, Dave R., rank 5), `D0001` (Acme,
Alice P., rank 7). Stepped credit: ≥4/5 → 0.08, exactly 3/5 → 0.04,
≤2/5 → 0.00. To rebalance to 1.00, the two heaviest non-anchor
checkpoints lose 0.04 each: active-stuck-set 0.18 → 0.14 (-0.04) and
priority-queue 0.15 → 0.11 (-0.04). First anchor (Dimension coverage at
0.10) and all other weights unchanged. Score caps and success_threshold
unchanged. Final weights: 0.07 + 0.14 + 0.12 + 0.12 + 0.10 + 0.11 +
0.11 + 0.10 + 0.05 + 0.08 = 1.00.

## Round 2 hardening (2026-04-30) — pass→continue conversion
- Currently pass 1.0; add 2 strict anchors to push to continue (~0.70-0.80).
- Added §5 CPs "SLA marker for top-owner next_action" 0.08, "Top-priority risk_score precision" 0.07.
- Added GT fields sla_marker_required_owners (Grace T., Erin Y. — top 2 owners by oldest_days_in_stage among the 3-stuck-deal cohort) + top_priority_risk_scores (D0028=2927.7, D0027=2775.8, D0026=2602.4 — top 3 priority_queue entries).
- Shaved 0.15 total: active-stuck-set 0.14→0.10 (-0.04), totals-match 0.10→0.07 (-0.03), owner-followups 0.11→0.07 (-0.04), priority-queue 0.11→0.07 (-0.04).
- Final weights: 0.07 + 0.10 + 0.12 + 0.12 + 0.07 + 0.07 + 0.07 + 0.10 + 0.05 + 0.08 + 0.08 + 0.07 = 1.00.
- Target: opus 1.0 → ~0.78 (loses 0.08 if next_action lacks days reference + 0.07 if risk_score drifts).

## Round 3 hardening (2026-04-30) — second orthogonal anchor
- After R2 (SLA-marker + risk_score), score dropped 1.0→0.84 (continue).
- R3 added §5 CP "Per-moving-active velocity precision" 0.08 (5/7 strict).
- Added GT fields moving_active_required_velocity_fields + velocity_class_thresholds + min_with_velocity.
- Shaved 0.08 from moving-active set correct (0.12→0.08, -0.04) and terminal-aged set correct (0.12→0.08, -0.04).
- Final weights: 0.07 + 0.10 + 0.08 + 0.08 + 0.07 + 0.07 + 0.07 + 0.10 + 0.05 + 0.08 + 0.08 + 0.07 + 0.08 = 1.00.
- Target: opus 0.84 → ~0.68 (loses 0.08 if velocity fields not added; opus typically reports stage but not velocity classification).

## Round 4 hardening (2026-04-30) — third orthogonal anchor
- After R2+R3, score 0.85 (oversaturation).
- R4 added §5 CPs "owner_followups next_action verb precision" 0.07, "Active-stuck-deal stage_history_length precision" 0.06.
- Added GT fields next_action_canonical_verbs + min_owners_with_verb_action + min_stuck_deals_with_stage_history_length.
- Shaved 0.13 from "Dimension coverage" (0.10→0.01, -0.09) and "Deal-id precision" (0.08→0.04, -0.04). Both are coverage-style anchors that overlap the new structure-precision CPs (next_action verb pattern subsumes part of the dimension surfacing requirement; stage_history_length subsumes part of the deal-id reference requirement). Dimension coverage trimmed harder since the next_action verb-precision CP plus existing SLA-marker / velocity / risk-score precision CPs together already enforce concrete substance across 4+ dimensions implicitly.
- Final weights: 0.07 + 0.10 + 0.08 + 0.08 + 0.07 + 0.07 + 0.07 + 0.01 + 0.05 + 0.04 + 0.08 + 0.07 + 0.08 + 0.07 + 0.06 = 1.00.
- Target: opus 0.85 → ~0.65.

## Round 5 hardening (2026-04-30) — cap for missing owners
- After R2+R3+R4 anchors, score 0.83.
- §6 added "Cap 0.65 — Missing expected owners" (≥5 of expected owners required).
- Added GT field min_owners_in_followups: 5.
- Target: opus 0.83 → ~0.65 if any expected owners missing.

## Round 6 hardening (2026-04-30) — second cap
- After R2+R3+R4+R5 (multiple anchors + missing-owners cap), score 0.78.
- §6 added "Cap 0.55 — Priority queue missing top deals" (≥6 of 7 expected deal IDs).
- Added GT field min_priority_queue_match_count: 6.
- Target: opus 0.78 → ~0.55 if priority_queue.csv drifts.

## Review pass (2026-04-30) — user-record-driven changes
Aligned task with review_record.md item #22:
1. **Top-7 most dangerous deals are now obviously discoverable.** All
   seven priority-queue entries (D0028, D0027, D0026, D0023, D0011,
   D0005, D0001) share the trifecta: very high value (75k–95k USD),
   late stage (Proposal / Negotiation / Qualified), and many
   days_in_stage (42–70). Their risk_scores (3360.0–6650.0) are
   dramatically higher than any non-top-7 stuck deal. The largest
   non-top-7 stuck risk is ~1792 (D0043, 51220 × 35 / 1000) — a >1500
   gap to rank 7. Inspecting the snapshot makes the top-7 visible at
   a glance.
2. **Dataset expanded from 33 → 64 deals.** Added D0034..D0064 (31
   new deals, all <3000 risk_score) covering the realistic Lead /
   Qualified / Proposal / Negotiation / Won / Lost mix. Resulting
   partition: 30 active stuck (was 17), 17 moving-active (was 7), 13
   terminal-aged (was 7), 4 terminal-fresh.
3. **Prompt no longer enumerates row counts or stuck counts.** Both
   `task` (live mode) and `task_snapshot` (offline mode) now use
   "every", "all the deals", "all of them" framing instead of "~33
   rows" or "the seven riskiest". Skill usage is mentioned in the
   first paragraph (airtable-pat-rest + database-operations). All
   English. No brackets used in user-visible flow.
4. **Evaluation tightened to STRICT on the four core completeness
   checkpoints** per global rule #8 ("if prompt describes the whole
   set, eval must hit 100%"): active stuck (10/10 strict, no partial
   credit), moving-active (8/8 strict), terminal-aged (8/8 strict),
   priority queue 7-of-7 in correct order with risk_score ±0.1, and
   owner-followups requires every expected owner to be present with
   matching metrics. Step-down credit removed from these four anchors.
5. **Ground truth regenerated.** GT now has 9 owners, 30 active
   stuck deal IDs, 17 moving-active IDs, 13 terminal-aged IDs,
   stage_counts with new totals, active_pipeline_value=$1,857,271.16,
   terminal_value=$685,405.48. `sla_marker_required_owners` updated
   to top-2 owners by oldest_days_in_stage = [Grace T. (70d), Frank
   L. (65d)]. `top_priority_risk_scores` = {D0028: 6650.0, D0027:
   5525.0, D0026: 4840.0}.
6. **Populator made data-driven.** `write_outputs` now derives
   `sla_marker_required_owners`, `top_priority_risk_scores`,
   `topic_dimensions`, velocity / next_action thresholds, and the
   missing-owner / priority-queue floors directly from PLAN, so a
   future PLAN edit auto-regenerates a consistent GT.
7. **§5 sum = 1.00 verified.** New weights: 0.07 + 0.10 + 0.08 +
   0.08 + 0.07 + 0.07 + 0.07 + 0.08 + 0.07 + 0.08 + 0.01 + 0.05 +
   0.04 + 0.07 + 0.06 = 1.00. Score caps and success_threshold
   unchanged.

## Compliance fix (2026-04-30)

§5 had grown to 15 weighted entries with smallest = 0.01 (Dimension
coverage), making grading brittle and error-prone. Per global rule
(consolidate small overlapping CPs), merged five logically related
pairs into composite anchors. Total CP count reduced 15 → 10. No
new behaviour required from the executor — sub-conditions inside
each composite are identical to the prior individual CPs; only the
score aggregation tier within each composite changed.

Consolidations:
- Active stuck set (0.10) + stage_history_length precision (0.06)
  → "active stuck set + stage_history_length" 0.16. Both target
  active_stuck_deals structure.
- Moving-active set (0.08) + per-moving-active velocity precision
  (0.08) → "moving-active set + velocity precision" 0.16. Both
  target moving_active_deals.
- Priority queue (0.07) + top-priority risk_score precision (0.07)
  → "priority queue + top-priority risk_score precision" 0.14.
  Both target priority_queue.csv.
- SLA marker for top-owner next_action (0.08) + next_action verb
  precision (0.07) → "next_action SLA marker + verb precision"
  0.15. Both target owner_followups[*].next_action quality.
- Dimension coverage (0.01) + Deal-id precision (0.04) → "coverage
  anchors (dimensions + deal-id precision)" 0.05. Both are
  coverage/anchor checks (smallest CP rolled up here, eliminating
  the brittle 0.01 line item).

Final 10-CP weights: 0.07 + 0.16 + 0.16 + 0.08 + 0.07 + 0.07 + 0.14
+ 0.15 + 0.05 + 0.05 = **1.00** ✓. Smallest CP is now 0.05 (was
0.01). Score caps in §6 unchanged. success_threshold unchanged.
