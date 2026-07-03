# Design notes — task_101_01_boarding_pass_ocr (archive only)

This file is supervisor-side archive material. It is **never injected** into the
executor environment because `meta/` is excluded from the runtime drop. Keep
this for benchmark-construction continuity only; do not migrate any of this
content back into `references/eval_rule.md`.

## Corpus expansion history

The fixture corpus grew from a single fabricated boarding pass to a stack of
six realistic-synthetic passes that cover the dominant boarding-pass OCR
failure modes:

1. `pass_01.jpg` — UA traditional paper stub, mild ~2 degree rotation
2. `pass_02.jpg` — DL narrow thermal-printer stub (gritty mono)
3. `pass_03.jpg` — AA mobile PDF printout, full-width QR block (resilience)
4. `pass_04.jpg` — LH traditional stub, ~22 degree rotation (resilience)
5. `pass_05.jpg` — JAL bilingual JA/EN stub, fold crease + glare
6. `pass_06.jpg` — UA return leg, torn top-right corner

The corpus was generated deterministically with seed `20260425`. The generated
images and `ground_truth.per_file` are committed as benchmark fixtures; any
future regeneration should happen in a private fixture-building workspace before
the resulting assets are reviewed and imported.

## Past rubric tightening

Earlier passes used a flat per-pass linear average for field accuracy. This was
later replaced with a stepped-band scoring rule on the absolute count of
correctly-normalized fields across all six passes (max 42), and a hard cap was
introduced for the two resilience fixtures (`pass_03` and `pass_04`). These
changes are now part of the active rubric — see `references/eval_rule.md`.

A calibration rubric line that depended on per-field confidence emission was
present in earlier drafts. It has been removed because the supervisor cannot
verify executor-emitted confidence scores. Field-level accuracy and
no-hallucination remain the primary correctness signals.

## v8 hardening round 4 (2026-04-29)

Round-3 abstract dimension anchors were too generous for the supervisor — the
abstract phrasing of "demographic mix" or "fare-class spread" was awarded
partial credit even when the deliverable barely mentioned any concrete token.
Round 4 makes the dimension coverage **anchor-keyword detectable** so that
each dimension is binary-checkable against a list of concrete phrases. The
prompt was rewritten to embed five travel-portfolio dimensions (pax
demographics, route geography, fare class, frequency status, timing
pattern) as a natural-voice clause without enumerating them.

§5 rebalanced: itinerary_review.csv 0.10 → 0.05 (-0.05); field format
normalization 0.10 → 0.05 (-0.05); no-hallucinated-content 0.10 → 0.05
(-0.05); new "Topic dimension coverage" anchor at +0.15. Field-accuracy
line stays 0.40 (already strict, the dominant signal). Final weights:
0.10 + 0.40 + 0.10 + 0.10 + 0.05 + 0.05 + 0.05 + 0.15 = 1.00.

Anchor scoring is strict: 5/5 → 0.15, 4/5 → 0.05, ≤3/5 → 0.00. Anchor
phrases must appear inside artifacts under `/tmp_workspace/results/`, not
just the executor's chat reply, so that supervisor matching is grounded in
the saved deliverable. ground_truth.json gains `topic_dimensions` (5
keyword lists) plus `min_dimensions_covered: 5`. score caps and
success_threshold (0.90) unchanged.

## Review pass (2026-04-30) — user feedback
- Removed prompt parenthetical for per-image extraction.
- Removed seat / gate / needs_manual_review requirements.
- Removed 3rd paragraph (5-dim summary).
- Tightened all CPs to strict (no ≥X/Y; full all-or-nothing).
- §5 rebalanced to sum 1.00.

Concrete changes:
- Prompt rewritten in natural Chinese spoken voice; skill `ocr-local` named
  inline in the first paragraph; no parentheses; no rubric anchor enumeration.
- expected_fields: 7 → 5 (dropped seat, gate). Total slots: 42 → 30.
- itinerary_review.required_columns: dropped seat, gate, needs_manual_review.
- Dropped manual_review_true_files, topic_dimensions, min_dimensions_covered
  from ground_truth.json.
- §5 weights before / after:
  - 0.10 output shape → 0.10 (unchanged, now strict 6/6 well-formed)
  - 0.40 field accuracy stepped → 0.50 strict (all 30/30 or 0)
  - 0.10 resilience pass_04 → 0.10 strict (5/5 or 0)
  - 0.10 resilience pass_03 → 0.10 strict (5/5 or 0)
  - 0.05 format normalization → 0.10 strict (100% or 0)
  - 0.05 no hallucination → 0.05 (unchanged)
  - 0.05 itinerary_review.csv → 0.05 strict (all 6/6 boarding_time correct
    + all required cols or 0)
  - 0.15 topic dimension coverage → REMOVED
  - Sum: 0.10 + 0.50 + 0.10 + 0.10 + 0.10 + 0.05 + 0.05 = 1.00 ✓
- §6 caps: resilience-collapse threshold expression updated from
  ">= 3 of 7" to ">= 3 of 5" (denominator follows the new field count;
  the numeric `resilience_cap_threshold = 3` is preserved). All other cap
  numbers unchanged.
