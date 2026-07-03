# Design notes — task_101_13_pdf_invoices_structure

Internal archive for benchmark-construction history. Not injected into the executor or the supervisor.

## Distractor PDFs (scope-discrimination layer)

Two extra PDFs were added on top of the 5 in-scope invoices to test scope discrimination:

- `invoice_006.pdf` — `BL-00184-R`, a reissue of already-paid `BL-00184` (covered by `PAY-1002` + `PAY-1003`). The PDF body contains the disqualifying string "do NOT submit a second payment".
- `invoice_007.pdf` — `LCS-2025-0314`, vendor "Lumen Creative Studio", cost center 4200 (Marketing). The PDF body says "route to Marketing AP queue, NOT to Engineering AP".

Disqualifying marker keywords (for grading): `BL-00184-R`, `reissue`, `already paid`, `BL-00184`, `LCS-2025-0314`, `marketing`, `wrong department`, `cost center 4200`, `Lumen Creative`.

Expected behavior:
- Excluded from `invoices.json` (5 in-scope only).
- Excluded as rows from `ap_reconciliation.csv`.
- Acknowledged in an "Excluded" / "Out of scope" / "Skipped" section (in `summary.pdf` bottom or a separate `excluded.md`) with a one-line reason for each.

Acceptable Excluded section header words: "Excluded", "Out of scope", "Skipped", "排除".

## Iteration history

- Initial cut: 5 invoices, no scope-discrimination layer.
- Later iteration: added the 2 distractor PDFs above and the Excluded-note grading rule to differentiate executors that blindly process every PDF in the inbox from those that read each PDF's body and apply the prompt's filter instruction.

## Skill mapping

Declared skills: `pdf` (extraction side) and `pdf-generator` (summary PDF side). The supervisor expects trace evidence of consulting these — handled in §6 score caps.

## v8 hardening round 3 (2026-04-29)

Round-2 moderate hardening (0.10–0.12 anchors, ≥4-of-5 partial credit)
was insufficient — opus-4.6 still reliably cleared 0.90. This round
applies strict 5/5 all-or-nothing dimension coverage at weight 0.15.

- Public prompt rewritten to embed five extraction dimensions as
  natural-voice clauses (no enumerated list): header fields including
  payment terms, full line items including description, monetary
  reconciliation including shipping breakout, payment status vs ledger,
  and per-invoice currency/unit consistency check.
- §5 rebalanced: invoices.json header/footer fidelity 0.20 → 0.15
  (-0.05); line items 0.15 → 0.12 (-0.03); arithmetic and currency
  consistency 0.10 → 0.07 (-0.03); ap_reconciliation.csv shape 0.10 →
  0.08 (-0.02); ap_reconciliation.csv values 0.10 → 0.08 (-0.02).
  Total cut = 0.15, added as new "Topic dimension coverage" anchor.
- New anchor scoring: 5/5 → 0.15; 4/5 → 0.05; ≤3/5 → 0.00. Stepped
  cliff: missing one dimension drops 0.10; missing two+ drops the
  full 0.15.
- ground_truth.json gains `topic_dimensions` list and
  `min_dimensions_covered: 5`.
- score caps and success_threshold (0.90) unchanged.
- Final weights: 0.15 + 0.15 + 0.12 + 0.07 + 0.10 + 0.05 + 0.08 +
  0.08 + 0.05 + 0.15 = 1.00.

## v8 hardening round 5 (2026-04-29)

Round-3 dimension anchor (5/5 strict, 0.15) was insufficient on its own —
opus-class executors hit cap 0.97 by satisfying every non-anchor
checkpoint plus a partial dimension match. This round adds a second §5
anchor "Invoice numeric precision" at weight 0.08 that requires the
deliverable package to reference, by exact invoice-number string, ≥4 of 5
specific in-scope anchors: `INV-2025-0001`, `BL-00184`, `2025-Q1-117`,
`HCG-2025-0041`, `SL-2025-00876`. Stepped credit: ≥4/5 → 0.08, exactly
3/5 → 0.04, ≤2/5 → 0.00. To rebalance to 1.00, the two heaviest non-anchor
checkpoints lose 0.04 each: invoices.json shape 0.15 → 0.11 (-0.04) and
invoices.json header/footer fidelity 0.15 → 0.11 (-0.04). Topic dimension
anchor (0.15 strict 5/5) and all other weights unchanged. Score caps and
success_threshold unchanged. Final weights: 0.11 + 0.11 + 0.12 + 0.07 +
0.10 + 0.05 + 0.08 + 0.08 + 0.05 + 0.15 + 0.08 = 1.00.

## Round 1 hardening (2026-04-30)
- Added §5 CP "Split-payment recognition precision" 0.07 (per-split-invoice
  strict; stepped: all → 0.07, one missed → 0.03, ≥2 missed → 0.00).
  Currently keys off the single split-payment invoice BL-00184
  (payment_ids = PAY-1002 + PAY-1003) — the only invoice in
  `ap_reconciliation` with ≥2 payment_ids.
- GT unchanged: BL-00184 already had `payment_ids: ["PAY-1002","PAY-1003"]`,
  `paid_total: 691.09`, `status: "paid"`, `variance: 0.0`.
- Shaved 0.07 from existing reconciliation CPs to rebalance:
  ap_reconciliation.csv shape 0.08 → 0.05 (-0.03);
  ap_reconciliation.csv values 0.08 → 0.04 (-0.04). Total cut = 0.07.
- Final weights: 0.11 + 0.11 + 0.12 + 0.07 + 0.10 + 0.05 + 0.05 + 0.04 +
  0.07 + 0.05 + 0.15 + 0.08 = 1.00.
- Target: opus 0.80 → ~0.73 (loses 0.07 if opus marks BL-00184 as unpaid
  when GT has it as split-paid).

## Round 2 hardening (2026-04-30) — re-anchor for promoted task
- Task promoted from continue 0.80 → pass 0.98 after R1 split-payment anchor
  (opus correctly recognized BL-00184 as split-paid and cleared the new CP).
  We need a different precision anchor to push the score back into continue.
- Added §5 CP "Per-invoice tax-rate classification precision" 0.08
  (≥4-of-5 strict). Each in-scope invoice must surface its tax rate as
  an explicit percentage (8.5%, 19.0%, 0.0%, 0.0%, 13.0% for the five
  in-scope invoices) — a bare `tax` amount without a rate is insufficient.
  Stepped: 5/5 → 0.08, 4/5 → 0.04, ≤3/5 → 0.00.
- Note on tactic: the user's R2 plan suggested German MwSt 7%/19% per-line
  classification, but the actual five in-scope invoices span four tax
  regimes (US sales tax 8.5%, German VAT 19%, US zero-rate cloud/services,
  China VAT 13%) — no German 7% reduced-rate invoice exists in this
  source set. The softer fallback (require explicit tax-rate %
  attribution per invoice, ≥4/5) is used instead. Opus's typical failure
  mode is reporting `tax: 25.78` without surfacing `tax_rate_pct: 8.5`.
- Added GT field `tax_rate_classification_anchors` with
  `expected_per_invoice` (per-id rate, currency, comment) and
  `min_invoices_with_correct_tax_rate_classification: 4`, plus an
  `acceptance_note` listing accepted key names and the ±0.5 pp tolerance.
- Shaved 0.08 from "Topic dimension coverage" (0.15 → 0.07) — the new
  tax-rate anchor is itself a precision check on the existing
  monetary_totals dimension, so this is the cleanest place to compress.
  All other CP weights unchanged.
- Final weights: 0.11 + 0.11 + 0.12 + 0.07 + 0.10 + 0.05 + 0.05 + 0.04 +
  0.07 + 0.05 + 0.07 + 0.08 + 0.08 = 1.00.
- Target: opus 0.98 → ~0.85 (loses 0.08 if tax-rate classification absent
  in ≥2 invoices, which is the documented opus failure mode for invoice
  extraction; also loses 0.08 from the topic-dimension shave even when it
  passes that anchor's 5/5 threshold). Likely lands in continue band.

## Round 3 hardening (2026-04-30) — push pass to continue
- Currently pass 0.96 after R1 split-payment + R2 MwSt anchors satisfied.
- R3 added §5 CP "Per-invoice metadata field completeness" 0.10
  (5/5 invoices × all-3-fields strict: po_number, vendor_contact,
  payment_terms). Stepped: 5/5 → 0.10, 4/5 → 0.05, ≤3/5 → 0.00.
- Added GT fields per_invoice_required_fields (po_number,
  vendor_contact, payment_terms),
  per_invoice_required_fields_min_invoices=4, and
  per_invoice_required_fields_min_per_invoice=3.
- Shaved 0.10 split across two CPs: invoices.json shape 0.11→0.06
  (-0.05) and summary.pdf content 0.10→0.05 (-0.05). Other weights
  untouched.
- Final §5 sum: 0.06 + 0.11 + 0.12 + 0.07 + 0.05 + 0.05 + 0.05 +
  0.04 + 0.07 + 0.05 + 0.07 + 0.08 + 0.08 + 0.10 = 1.00.
- Target: opus 0.96 → ~0.55 (loses 0.10 if any of
  po_number/vendor_contact/payment_terms missing in ≥2 invoices —
  opus typically extracts header subtotal/tax/total cleanly but
  drops PO# and contact rows; combined with prior tax-rate anchor
  pressure, drops to continue range).

## Cleanup pass (2026-04-30) — remove hardening_too_strict anchors
- DELETED §5: "Per-invoice tax-rate classification" 0.08, "Per-invoice metadata field completeness" 0.10 (prompt does not require these fields).
- KEPT R1 split-payment precision (aligned with prompt's reconciliation requirement).
- Restored 0.18 weight to original CPs (Topic dim 0.07→0.15, invoices.json shape 0.06→0.11, summary.pdf 0.05→0.10).

## Review pass (2026-04-30)
Applied user review_record Task 13 + global rules.

### Prompt (task YAML)
- Removed exact in-scope vs out-of-scope counts (no "5 in-scope + 2 excluded"
  hint). Body now says only "not every PDF in that folder belongs in this
  engineering AP run" + "some are reissues / some are misrouted from another
  department" — executor must derive the count from PDF body text.
- Skill mention moved into the first paragraph: "Please use the workspace's
  pdf skill for the extraction side and the pdf-generator skill for the
  report side."
- Removed all parentheses/brackets per global rule 6. Replaced inline
  parenthetical specs with em-dash / "with" phrasing.
- Decision on excluded section: KEPT and STRENGTHENED. The prompt now
  requires `/tmp_workspace/results/excluded.md` listing every PDF that was
  not included in invoices.json with a one-sentence reason grounded in
  body text. The audit-trail framing is preserved as the user voice
  rationale.

### Eval rule §5 (all anchors strict; sum still 1.00)
- 0.05 "scope discrimination" → upgraded to **0.05 "Out-of-scope PDF
  identification (strict)"**: must produce excluded.md (or summary.pdf
  Excluded section) listing both `invoice_006.pdf` (BL-00184-R, reissue)
  and `invoice_007.pdf` (LCS-2025-0314, marketing) by filename and
  invoice number with valid reason. Strict all-or-nothing — replaces
  previous "halve if one missing" stepping. Also kills the CP if
  out-of-scope leaks into invoices.json or ap_reconciliation.csv.
- 0.07 split-payment recognition → strict all-or-nothing
  (was: stepped 0.07/0.03/0.00).
- 0.15 topic dimension coverage → strict all-or-nothing
  (was: stepped 0.15/0.05/0.00).
- 0.08 invoice numeric precision → strict all-or-nothing 5/5
  (was: stepped ≥4/5 → 0.08, 3/5 → 0.04, ≤2/5 → 0.00).
- §5 weight sum unchanged: 0.11 + 0.11 + 0.12 + 0.07 + 0.10 + 0.05 +
  0.05 + 0.04 + 0.07 + 0.05 + 0.15 + 0.08 = 1.00.
- §6 caps unchanged. success_threshold (0.90) unchanged.

### Ground truth
- Added top-level `expected_out_of_scope_pdfs` array with two entries
  (invoice_006.pdf / BL-00184-R, invoice_007.pdf / LCS-2025-0314), each
  carrying canonical_reason + accepted_reason_keywords. Mirrors the
  existing `out_of_scope_invoices` block in a list shape that the
  supervisor can iterate when grading the new strict CP.
- All other GT fields unchanged.
