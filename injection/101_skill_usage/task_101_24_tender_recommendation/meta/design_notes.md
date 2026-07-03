# Design notes — task_101_24_tender_recommendation

Internal-only archive of construction context for this task. Not injected
into the executor or supervisor; lives in `meta/` for human reference.

## Schema and difficulty

- Schema `a` — Chinese bid recommendation with a deterministic weighted
  scorecard. Inputs are four Chinese-language bid PDFs, a consolidated
  quote spreadsheet, and a committee scoring policy.
- Difficulty `Hard`. The executor must combine PDF reading, spreadsheet
  arithmetic with formula-backed cells, and structured business writing in
  a single coherent recommendation.

## Construction notes

- Vendor identifiers are bilingual (`Vendor X — 中文名`) so that either
  English or Chinese matching is acceptable in grading.
- Weights and normalization formulas come from `scoring_policy_cn.md`; the
  scorecard math is fully deterministic given the supplied numbers, which
  is why the rubric uses a tight ±0.2 tolerance.
- The top two totals (`83.7` for Vendor D, `81.3` for Vendor A) are
  intentionally within ~2.4 points so the executor must surface the
  tradeoff explicitly rather than treating it as a trivial pick.
- Risk anchors per vendor (`risk_fact_anchors` in `ground_truth.json`) are
  the response-window / warranty / delivery substrings that appear in each
  bid PDF, used to verify that the risk bullets are source-grounded.
- Three declared skill families (`pdf-smart-tool-cn`,
  `tender-finance-local`, `business-writing`) cover the three modalities
  the deliverable depends on; the rubric checks they were consulted.

## Cap rationale

Score caps in `eval_rule.md` §6 target only extreme failure modes
(no deliverables, credential emission, fabricated sources, total scope
blowout, safety violation). Earlier drafts had additional caps mirroring
individual rubric lines (missing scorecard, missing workbook, ad-hoc
weights, top-pick mismatch, missing skill reads); those were removed
because they double-counted the rubric and pushed caps above 0.7.
Per-checkpoint deductions through §5 already cover those failure modes.

## v8 hardening round 3 (2026-04-29)

opus-4.6 was still passing this task even with moderate (0.10–0.12,
≥4-of-5) dimension coverage anchors, so this round adds a strict 5/5
all-or-nothing gate. The public prompt now naturally enumerates the
five evaluation dimensions a tender review must address — price
competitiveness (per unit, total, hidden fees), delivery timeline / SLA
realism, specs / quality compliance (mandatory vs nice-to-have), vendor
risk profile (financial / track record / SOC2 / sanctions), and
contract / payment terms flexibility (advance payment, milestone
billing, warranty length) — woven into a colleague-style ask rather
than an enumerated list. The new §5 anchor "Topic dimension coverage"
is weight 0.15 with strict scoring: 5/5 → full 0.15, exactly 4/5 →
0.05, ≤3/5 → 0.00. To keep §5 weights summing to 1.00, the existing
scorecard-values, close-gap, risk-section, and workbook anchors were
each trimmed (0.20→0.15, 0.08→0.05, 0.08→0.05, 0.18→0.14). GT now
carries `topic_dimensions` (5 items) plus `min_dimensions_covered: 5`.
success_threshold and score caps are unchanged.

## v8 hardening round 5 (2026-04-29)

Round-3 strict 5/5 dimension anchor (0.15) was insufficient on its own —
opus-class executors hit cap 0.95 by satisfying every non-anchor
checkpoint plus a partial dimension match. This round adds a second §5
anchor "Vendor figure precision" at weight 0.08 that requires the
deliverable package to reference, by exact bilingual-vendor token or
numeric literal, ≥4 of 5 specific anchors: `Vendor D — 北京腾云` (top
pick, either side accepted), `Vendor A — 上海华为` (runner-up, either
side accepted), `Vendor C — 深圳麒麟` (third, either side accepted),
total `83.7` for Vendor D (within ±0.2), close-gap `2.4` points (within
±0.2). Stepped credit: ≥4/5 → 0.08, exactly 3/5 → 0.04, ≤2/5 → 0.00.
To rebalance to 1.00, the two heaviest non-first-anchor checkpoints
lose 0.04 each: Scorecard values 0.15 → 0.11 (-0.04) and Scorecard
workbook 0.14 → 0.10 (-0.04). First anchor (Topic dimension coverage at
0.15 strict 5/5) and all other weights unchanged. Score caps and
success_threshold unchanged. Final weights: 0.08 + 0.12 + 0.11 + 0.08 +
0.08 + 0.05 + 0.05 + 0.05 + 0.10 + 0.15 + 0.05 + 0.08 = 1.00.

## Round 5 hardening (2026-04-30) — score cap for F1 framework issue
- F1 framework: user_sim adds off-rubric "Chinese only" instruction; supervisor F1-penalizes English. Adding a structural cap directly to address the F1 pattern.
- §6 added "Cap 0.60 — English vendor labels in recommendation".
- Added GT fields english_vendor_labels_disallowed_in_recommendation + max_allowed_english_vendor_label_count.
- Target: opus 0.82 → ~0.60 (cap fires if standalone English vendor labels appear; bilingual format allowed).

## Round 8 hardening (2026-04-30) — recommendation length cap
- Score still 0.60 (continue band) after R5 cap.
- §6 added "Cap 0.60 — Recommendation too brief" (recommendation.md must be ≥150 words excluding scorecard table).
- Added GT field min_recommendation_words: 150.
- §5 weights unchanged (sum still 1.00). Existing 0.60 English-vendor cap kept intact.
- Target: thin recommendations now hit a second 0.60 cap, reinforcing the depth requirement.

## Round 10 hardening (2026-04-30) — scorecard formula strict cap
- Score still continue 0.60 after R5+R8 caps.
- §6 added "Cap 0.45 — Scorecard formulas missing" (price/delivery/total cols must use formulas, verifiable via openpyxl cell.data_type='f' or value starts with '=').
- Added GT field scorecard_formula_strict_required: true.
- §5 weights unchanged (sum still 1.00). Lower cap (0.45 < 0.60) provides a stronger floor when constants are pasted instead of formulas.
- Target: opus 0.60 → ~0.45 if scorecard uses pasted constants.

## Review pass (2026-04-30)

User feedback (review_record.md Task 24): the special-purpose
`tender-finance-local` skill must have actual usage necessity — i.e.
not using it must cause a checkable deliverable to be missing. Concrete
suggestion: have the skill's workflow create a YAML record that the
supervisor checks for.

Changes applied:

1. **`skills/tender-finance-local/SKILL.md`** — added a mandatory
   workflow step 6 instructing the executor to write
   `/tmp_workspace/results/bid_audit_trail.yaml` with one entry per
   vendor and required fields `bid_id`, `extracted_price`,
   `delivery_days`, `risk_notes`, `source`. Framed as the audit artefact
   the procurement committee uses to validate the recommendation.

2. **Task YAML prompt** — rewritten in natural English (was already
   English; tightened to avoid bracketed parentheticals per global
   rule). The first paragraph now explicitly mentions the three skills
   (`pdf-smart-tool-cn`, `tender-finance-local`, `business-writing`)
   and what each is for. A separate paragraph reminds the executor to
   follow the `tender-finance-local` workflow end-to-end so any audit
   artefacts land in `/tmp_workspace/results/` — without naming
   `bid_audit_trail.yaml` directly, so the rubric stays implicit and
   the executor must read SKILL.md to discover it.

3. **`eval_rule.md` §5** — added a STRICT 4-of-4 all-or-nothing
   checkpoint at weight 0.10 for `bid_audit_trail.yaml`. No partial
   credit: any missing vendor entry, missing required field, or empty
   value collapses the score for this anchor to 0.00. This is the
   implicit "skill must be used" check the user requested. Rebalance
   to keep §5 sum at 1.00:
     - Topic dimension coverage 0.15 → 0.10 (-0.05; thresholds
       proportionally adjusted: 5/5 → full 0.10, 4/5 → 0.03, ≤3 → 0.00)
     - Scorecard workbook 0.10 → 0.07 (-0.03)
     - Risk section coverage 0.05 → 0.03 (-0.02)
     - New audit-trail anchor +0.10
   Verification: 0.08 + 0.12 + 0.11 + 0.08 + 0.08 + 0.05 + 0.05 + 0.03
   + 0.07 + 0.10 + 0.05 + 0.08 + 0.10 = 1.00. ✓

4. **`eval_rule.md` §6** — removed the over-strict "Cap 0.60 — English
   vendor labels in recommendation" clause. The rubric still grades
   bilingual vendor naming via §5 vendor figure precision; the cap was
   redundant and triggered for any standalone "Vendor X" mention,
   which is too aggressive given the prompt itself uses those labels
   to identify files. Other caps (0.30 no-deliverables, 0.30 credentials,
   0.40 fabricated, 0.50 scope blowout, 0.30 safety, 0.60 brief, 0.45
   missing formulas) preserved unchanged. The corresponding
   `english_vendor_labels_disallowed_in_recommendation` and
   `max_allowed_english_vendor_label_count` fields are removed from
   `ground_truth.json`.

5. **`eval_rule.md` §2 / §7 / §8** — task contract now lists three
   deliverables (recommendation.md, scorecard.xlsx, bid_audit_trail.yaml).
   Continue-vs-fail guidance updated. Hidden assets list mentions the
   audit-trail schema.

6. **`ground_truth.json`** — added
   `expected_audit_trail_yaml_per_vendor` block with `path`,
   `required_vendor_count: 4`, `vendor_keys` (4 bilingual labels),
   `required_fields` list, `numeric_fields` constraint, and
   `strict_match: true`. Removed the obsolete English-vendor disallow
   fields that paired with the removed §6 cap.

Targeted effect: an executor that ignores the `tender-finance-local`
skill cannot guess this YAML exists or its required fields, so the new
0.10 strict anchor will return 0.00 — making the special skill
genuinely necessary for ≥0.90 pass.

Verification:
- §5 sum = 1.00 (computed above)
- Prompt is in English; `tender-finance-local` mentioned in first
  paragraph
- No bracketed parentheticals (em-dashes used instead of `(...)`)
- All §5 anchors are STRICT (audit-trail anchor is hard 4/4 all-or-nothing)
- Score caps unchanged (no numbers raised); cleaned up dead R5 cap.
