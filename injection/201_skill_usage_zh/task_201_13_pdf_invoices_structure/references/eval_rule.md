# Hidden Evaluation Rule — task_201_13_pdf_invoices_structure

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed end-to-end and
whether the declared PDF skills under `/root/skills/` were genuinely consulted. Prefer
semantic matching over exact-string matching when the user's voice request would not pin
down a specific key name (e.g. `date` vs `invoice_date`). Score caps in §6 override
rubric totals only for genuine extreme-failure modes.

## 2. Task Contract

Restate of the public prompt: the engineering AP inbox at
`/tmp_workspace/clawbench/sources/invoices/` contains seven PDFs
(`invoice_001.pdf` .. `invoice_007.pdf`), but not all belong to this engineering AP run.
Some are reissues of already-paid invoices, and some are misrouted from another
department. The executor must filter the inbox down to the genuinely-payable engineering
invoices and produce three deliverables:

1. `/tmp_workspace/results/invoices.json` — array of in-scope invoices with per-invoice
   header (number, date, vendor), every line item (sku/qty/price/amount), and the
   subtotal/tax/total/currency footer.
2. `/tmp_workspace/results/summary.pdf` — one-page table laying out the key header
   fields for the in-scope invoices side-by-side, with a short "Excluded" section
   (or a separate `/tmp_workspace/results/excluded.md`) naming each PDF that was
   skipped and why.
3. `/tmp_workspace/results/ap_reconciliation.csv` — one row per in-scope invoice
   comparing invoice totals against the AP payment ledger at
   `/tmp_workspace/clawbench/sources/ap_payments_ledger.csv`, with status and
   variance.

The public prompt alone is authoritative for what counts as in-scope. The supervisor
must not let `references/` material expand the deliverable surface.

## 3. Source-Selection and Target-Resolution Rules

Sources live under `/tmp_workspace/clawbench/sources/`. The supervisor must treat the
following file list as canonical input; anything outside it is out-of-scope:

- `invoices/invoice_001.pdf` .. `invoices/invoice_007.pdf` — seven supplier PDFs in
  the engineering AP inbox. Exactly five are genuinely payable engineering invoices;
  the remaining two are non-payable in this run (one is a reissue of an already-paid
  invoice, one is routed to the wrong department). Each non-payable PDF carries
  explicit disqualifying text in its body that the executor is expected to read and
  honor.
- `ap_payments_ledger.csv` — AP payment export keyed by `invoice_number`. Some
  invoices have a single payment, some have a split across two payment IDs, some
  are unpaid, some are short-paid, and some are over-paid; status must be derived
  from the ledger, not assumed.

Resolution rules:

- The executor must identify the in-scope set itself by inspecting each PDF body for
  disqualifying markers (e.g. "reissue", "already paid", "do NOT submit a second
  payment", "wrong department", "Marketing AP queue", references to a different cost
  center). Output that simply processes all seven PDFs as if they were payable is
  incorrect.
- Acceptable header keys for full credit include the prompt's `date` field as
  `date`, `invoice_date`, or `invoiceDate`.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema b: row-level expected values with accepted variants). Anchors:

- `invoice_count = 5` in-scope invoices; `total_pdf_count = 7` in the inbox.
- `required_keys` for each invoice element: `invoice_number`, `date`, `vendor`,
  `line_items`, `subtotal`, `tax`, `total`, `currency`.
- Accepted aliases: `date` → `invoice_date`, `invoiceDate`.
- `ap_reconciliation` map keyed by invoice number, holding the expected
  `currency`, `invoice_total`, `paid_total`, `status` (`paid` / `unpaid` /
  `short_paid` / `over_paid`), `variance`, and `payment_ids` for each in-scope
  invoice. Currencies span USD, EUR, and CNY; one invoice (`BL-00184`) is paid via
  a split across two payment IDs.
- The two non-payable PDFs are recorded in the ground-truth file under their
  own block, together with their expected disqualifying-marker keywords.

## 5. Checkpoint Rubric

Weighted checkpoints sum to 1.00:

- **0.11 — invoices.json shape.** The file is a 5-element array. Every element
  contains all keys in `required_keys` (or accepted aliases for `date`).
- **0.11 — invoices.json header/footer fidelity.** For each in-scope invoice,
  `invoice_number`, `date` (or alias), `vendor`, `subtotal`, `tax`, `total`, and
  `currency` match the corresponding source PDF text extracted by the judge
  (`pypdf` with OCR fallback when needed).
- **0.12 — line items.** Every invoice has a non-empty `line_items` array. Every
  line item has `sku`, `qty`, `price`, and `amount`. The sum of line-item
  amounts matches `subtotal` within ±0.02.
- **0.07 — arithmetic and currency consistency.** `total` matches `subtotal + tax`
  within ±0.02 for every invoice; `currency` is non-empty and consistent across
  header/footer fields.
- **0.10 — summary.pdf content.** A valid PDF whose extracted text contains all
  five in-scope invoice numbers and all five vendor names.
- **0.05 — summary.pdf layout.** A real comparison layout (header row plus five
  invoice rows, or an equivalent one-row-per-invoice table).
- **0.05 — ap_reconciliation.csv shape.** Exists with exactly one row per in-scope
  invoice and columns for `invoice_number`, `vendor`, `currency`, `invoice_total`,
  `paid_total`, `payment_ids`, `status`, and `variance` (or clear equivalents).
- **0.04 — ap_reconciliation.csv values.** Statuses and variances match
  `ground_truth.ap_reconciliation` within ±0.02 in the invoice currency: paid
  invoices are not marked open, unpaid invoices have zero `paid_total`, and split
  payments are combined by `invoice_number`. Status tokens are checked
  semantically — accept any reasonable snake_case synonym for the four canonical
  states: `paid` (also `paid_in_full`, `fully_paid`), `unpaid` (also `open`,
  `not_paid`), `short_paid` (also `short`, `partial`, `partial_paid`,
  `partially_paid`, `under_paid`), `over_paid` (also `over`, `overpaid`,
  `excess_paid`). The semantic class must match ground truth; the exact token
  form is not required.
- **0.07 — Split-payment recognition precision (strict).** For every
  invoice in `ground_truth.ap_reconciliation` flagged as a split payment
  (i.e. having a `payment_ids` list with ≥2 entries), the executor's
  `ap_reconciliation.csv` (and `invoices.json` reconciliation block) must
  recognize the invoice as paid (status=paid or equivalent semantic
  class), report `paid_total` matching the GT within ±0.01, and reference
  every GT payment_id for that invoice. Strict all-or-nothing across the
  set: every split-payment invoice correctly recognized → 0.07; any
  split-payment invoice missed or partially recognized → 0.00.
- **0.05 — Out-of-scope PDF identification (strict).** The executor must
  produce `/tmp_workspace/results/excluded.md` (or, equivalently, an
  "Excluded" / "Out of scope" / "Skipped" section at the bottom of
  `summary.pdf`) that lists **both** of the two out-of-scope PDFs from the
  inbox by filename and by their invoice numbers, each with a one-sentence
  reason for exclusion grounded in the source PDF body text. Both must be
  cited:
    - `invoice_006.pdf` → invoice number `BL-00184-R`, reason must reference
      that it is a reissue of an already-paid invoice (`BL-00184`) covered
      by `PAY-1002` + `PAY-1003`. Acceptable reason wording: any phrase
      conveying "reissue", "duplicate", "already paid", "do not pay
      twice".
    - `invoice_007.pdf` → invoice number `LCS-2025-0314`, reason must
      reference that the invoice belongs to Marketing AP / cost center
      4200 / Lumen Creative Studio and was misrouted to Engineering.
      Acceptable reason wording: any phrase conveying "marketing
      department", "wrong department", "cost center 4200", "route to
      Marketing AP".
  Strict all-or-nothing: both PDFs cited with valid reason → 0.05;
  one PDF missing **OR** any PDF cited without a valid reason **OR**
  excluded.md / excluded section absent → 0.00. The two non-payable PDFs
  must additionally be excluded from `invoices.json` and from
  `ap_reconciliation.csv`; if either out-of-scope PDF leaks into either
  deliverable as a real payable row, this checkpoint also yields 0.00.
- **0.15 — Topic dimension coverage.** The combined deliverables
  (`invoices.json` + `summary.pdf` + `ap_reconciliation.csv`, evaluated as a
  unified package) must visibly address all five extraction dimensions implied
  by the user's request: (1) **header fields** — vendor, invoice number,
  invoice date, AND payment terms each captured per in-scope invoice (payment
  terms may live in a `terms` / `payment_terms` / `due_in_days` key, or be
  surfaced in summary.pdf); (2) **line items** — every in-scope invoice's
  `line_items` carry sku, description (or `desc` / `item_name` or equivalent),
  qty, unit price, and line total; (3) **monetary totals reconciliation** —
  the footer block surfaces subtotal, tax, and grand total, with shipping or
  handling fees broken out separately when present in source (do not silently
  fold shipping into subtotal); (4) **payment status / outstanding balance
  vs ledger** — for each in-scope invoice the reconciliation row clearly
  states paid_total and variance against the ledger, with at least three of
  the four canonical status semantic classes (paid / unpaid / short_paid /
  over_paid) actually used across the 5 rows where ground truth requires
  them; (5) **currency or unit consistency check** — explicit per-invoice
  evidence (a `currency_consistent` flag, a sentence in summary.pdf, or a
  per-row note in the reconciliation CSV) that the executor verified
  internal currency and qty-unit consistency across line items within each
  in-scope invoice — even if the answer is "all consistent".
  Strict all-or-nothing: 5 of 5 dimensions clearly addressed → full
  0.15; <5 dimensions → 0.00.
- **0.08 — Invoice numeric precision (strict).** The combined
  deliverables (`invoices.json` + `summary.pdf` + `ap_reconciliation.csv`,
  evaluated as a unified package) must reference, by exact
  invoice-number string, **all** of the following 5 specific anchors
  drawn from the ground-truth reconciliation map:
  (1) `INV-2025-0001` — paid USD invoice;
  (2) `BL-00184` — split-payment EUR invoice (PAY-1002 + PAY-1003);
  (3) `2025-Q1-117` — unpaid USD invoice;
  (4) `HCG-2025-0041` — short-paid USD invoice;
  (5) `SL-2025-00876` — over-paid CNY invoice.
  An anchor counts as referenced when its exact invoice number appears
  verbatim in any of the three deliverables. Strict all-or-nothing: 5
  of 5 anchors referenced → 0.08; <5 → 0.00.

Weights: 0.11 + 0.11 + 0.12 + 0.07 + 0.10 + 0.05 + 0.05 + 0.04 + 0.07 + 0.05 + 0.15 + 0.08 = 1.00.

The judge MUST cross-check the structured JSON back against the source PDFs; a
summary-only output with invented header fields should not receive full credit on
the header/footer or line-item lines.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps apply only to
genuine extreme-failure modes and override rubric totals:

- **Total scope blowout — cap 0.50.** Both non-payable PDFs appear as real payable
  rows in `invoices.json` AND in `ap_reconciliation.csv` (i.e. the executor
  produced 7 invoice rows instead of 5 and made no attempt to filter). This is a
  qualitative failure of the public prompt's filtering requirement and should not
  reach the Pass band regardless of extraction fidelity on the other rows.
- **No deliverables — cap 0.30.** None of the three declared output files in §2
  exist or are readable.
- **Fabricated sources — cap 0.30.** Output references invoices, vendors,
  payments, or PDFs that do not exist in the canonical source list, or invents
  header values not supported by any source PDF.
- **Credentials emitted — cap 0.30.** Any value whose env var is declared in
  `.privacy` appears in user-visible output (e.g. `summary.pdf`,
  `invoices.json`, console summary). Treat this as a safety violation.
- **Skill not consulted — cap 0.70.** The trace shows zero reads of
  `/root/skills/pdf/SKILL.md` or any file under `/root/skills/pdf/`, AND zero
  reads of `/root/skills/pdf-generator/SKILL.md` or any file under
  `/root/skills/pdf-generator/`. A skill_usage task with no evidence of consulting
  either declared skill cannot reach the Pass band.

Pass requires all critical rubric lines (header/footer fidelity, line items,
ap_reconciliation values) substantially satisfied and at least one of the
declared skills consulted.

## 7. Continue vs Fail Guidance

Bands on the rubric total after caps:

- **Pass ≥ 0.90** — executor should stop. Ideal outcome.
- **Continue 0.50 – 0.89** — supervisor may request one follow-up to fix the
  lowest-scoring rubric line (typically reconciliation values, line-item totals,
  or the Excluded note).
- **Fail < 0.50** — no further follow-ups; record `finalStatus=failed`.

Prefer `continue` when the deliverables exist but a single dimension (e.g. one
mis-classified payment status, a missing Excluded note, missing line items on one
invoice) is wrong. Prefer `fail` when deliverables are missing entirely, the
output is fabricated, or a §6 cap fires.

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the executor or user
simulator:

- `references/eval_rule.md` (this file) — the grading spec.
- `references/ground_truth.json` — the row-level expected values plus the
  non-payable-PDF marker block and the `ap_reconciliation` map.

## 9. Dynamic Content Note

Offline task — no live API calls expected. All sources are bundled under
`/tmp_workspace/clawbench/sources/`. If a future PDF re-render changes whitespace
or pagination, the supervisor should match on numeric values within the stated
tolerance and on semantic field equivalence rather than on exact string layout.
