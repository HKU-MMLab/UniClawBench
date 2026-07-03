# Hidden Evaluation Rule — task_104_29_trip_mess_archive

## 1. Grading Philosophy

Judge the executor on whether it actually organized the current noisy travel
document bundle, not whether it produced plausible travel paperwork. The core
outcomes are:

1. The requested archive, expense sheet, cleanup notes, and trip report exist
   under `/tmp_workspace/results/`.
2. The keep/drop decisions, categories, expense rows, totals, and report facts
   match the current `doc_01` through `doc_14` source files.
3. The result remains auditable after renaming: the original source provenance
   must resolve to current `doc_XX` filenames, especially in
   `expense_summary.csv` and `cleanup_notes.md`.

Use semantic matching for harmless formatting differences, localized category
labels, and minor merchant wording variants. Do not give credit for answers
that appear to use older semantic filenames, generic trip-report prose, or clean
OCR text without resolving the noisy images/PDF in the current bundle.

## 2. Task Contract

The executor must inspect `/tmp_workspace/clawbench/sources/trip_mess/` and
produce all of the following:

- `/tmp_workspace/results/trip_archive/` with category folders including at
  least `flights`, `hotel`, `transport`, `meals`, `tickets`, and `other`.
- `/tmp_workspace/results/expense_summary.csv` with columns semantically
  equivalent to `date`, `category`, `merchant_or_item`, `amount`, `currency`,
  and `source_file` / original filename.
- `/tmp_workspace/results/cleanup_notes.md` documenting duplicate, unrelated,
  and unreadable files.
- `/tmp_workspace/results/trip_report.md` summarizing the itinerary and total
  spend.

The `source_file` / original-filename values must refer to current source
filenames such as `doc_09.png`, not old semantic fixture names such as
`IMG_1043.png`, `hotel_booking.jpg`, or `blurry_receipt.jpg`.

## 3. Source-Selection and Target-Resolution Rules

The canonical source directory is
`/tmp_workspace/clawbench/sources/trip_mess/`. The in-scope fixture files are:

- `doc_01.jpg`, `doc_02.jpg`, `doc_03.jpg`, `doc_04.png`, `doc_05.png`,
  `doc_06.png`, `doc_07.pdf`, `doc_08.jpg`, `doc_09.png`, `doc_10.jpg`,
  `doc_11.png`, `doc_12.jpg`, `doc_13.jpg`, `doc_14.png`

No other source files are in scope. Older run artifacts with semantic filenames
are not valid current ground truth and must not be accepted as source mappings.

When matching archived files back to sources, the supervisor may use:

- explicit `source_file` / `original_filename` values in the CSV or notes
- original `doc_XX` tokens preserved in renamed filenames
- byte/hash identity or obvious copied visual content when files were renamed

Meaningful renamed filenames are required for archive quality, but renamed
filenames alone do not satisfy source provenance unless the original `doc_XX`
mapping is recoverable. A record that cannot be tied to a current source file is
unscored for the source-specific checkpoints and may trigger caps in Section 6.

## 4. Locked Ground Truth

Structured expected data lives at `references/ground_truth.json`. Use it as
authoritative if any source display or run artifact drifts.

Canonical trip facts:

- Traveler: `Lin Yu`
- Route: `Shanghai <-> Shenzhen`
- Dates: `2026-03-14` through `2026-03-16`
- Purpose: client workshop, office visits, dinner meeting, and short exhibition
  stop

Current keep/category map:

- `doc_09.png` - flights - MU 5351 outbound e-ticket, `2026-03-14`, `CNY 920`
- `doc_05.png` - flights - MU 5351 outbound boarding pass, no separate expense
- `doc_06.png` - flights - MU 5368 return flight, `2026-03-16`, `CNY 880`
- `doc_13.jpg` - hotel - Nanshan Central Hotel, `2026-03-14` to
  `2026-03-16`, `CNY 1880`
- `doc_01.jpg` - transport - SZ Transit Taxi, `2026-03-14`, `CNY 86`
- `doc_14.png` - transport - Shenzhen Metro top-up, `2026-03-15`, `CNY 50`
- `doc_02.jpg` - meals - Haiyun Kitchen, `2026-03-15`, `CNY 268`
- `doc_12.jpg` - meals - Blue Bottle Coffee, `2026-03-15`, `CNY 58`
- `doc_04.png` - tickets - Design Museum Shenzhen, `2026-03-16`, `CNY 120`
- `doc_07.pdf` - other - trip notes PDF
- `doc_11.png` - other - itinerary email screenshot

Current files that must be excluded or explicitly flagged:

- `doc_08.jpg` - duplicate hotel booking, duplicate of `doc_13.jpg`
- `doc_03.jpg` - unrelated cat photo
- `doc_10.jpg` - blurred/unreadable receipt; do not extract an expense row

Canonical expense rows are exactly these 8 rows, totaling `CNY 4262`:

| date | category | merchant_or_item | amount | currency | source_file |
| --- | --- | --- | ---: | --- | --- |
| 2026-03-14 | flights | MU 5351 Shanghai to Shenzhen | 920 | CNY | doc_09.png |
| 2026-03-16 | flights | MU 5368 Shenzhen to Shanghai | 880 | CNY | doc_06.png |
| 2026-03-14 | hotel | Nanshan Central Hotel | 1880 | CNY | doc_13.jpg |
| 2026-03-14 | transport | SZ Transit Taxi | 86 | CNY | doc_01.jpg |
| 2026-03-15 | transport | Shenzhen Metro top-up | 50 | CNY | doc_14.png |
| 2026-03-15 | meals | Haiyun Kitchen | 268 | CNY | doc_02.jpg |
| 2026-03-15 | meals | Blue Bottle Coffee | 58 | CNY | doc_12.jpg |
| 2026-03-16 | tickets | Design Museum Shenzhen | 120 | CNY | doc_04.png |

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within a checkpoint only for
verifiable, source-grounded content. Apply score caps in Section 6 after adding
checkpoint credit.

- **0.10 - Required output shape.** Full credit requires the archive directory,
  all six required category folders, `expense_summary.csv`, `cleanup_notes.md`,
  and `trip_report.md` to exist and be readable. The CSV must parse as a table
  with columns mappable to date, category, merchant/item, amount, currency, and
  source file. Missing or unreadable required artifacts receive no credit for
  the affected portion of this checkpoint.

- **0.25 - Archive keep/drop and categorization.** Score against the 14 current
  source files. Full credit requires all 11 kept files to appear in the correct
  category folders and the 3 excluded files not to be archived as normal trip
  documents. The boarding pass `doc_05.png` must be kept under `flights` but
  must not create an extra expense. Renamed kept files should include date,
  category, and key information, and the original `doc_XX` source must remain
  recoverable from filenames, CSV, notes, or copied-file identity. Wrong
  category or unresolved provenance receives no file-level credit.

- **0.15 - Cleanup notes.** Full credit requires `cleanup_notes.md` to mention
  all three current exclusions by `doc_XX` filename and reason:
  `doc_08.jpg` duplicate of `doc_13.jpg`, `doc_03.jpg` unrelated cat photo, and
  `doc_10.jpg` unreadable/too blurry for reliable extraction. Partial credit is
  proportional by correctly identified file plus reason; semantic old names do
  not satisfy the source-file requirement.

- **0.35 - Expense summary accuracy.** Full credit requires exactly the 8
  canonical rows in Section 4 and no extra expense rows. Award `0.05` for a
  parseable CSV with required columns and numeric CNY amounts; `0.24` for the
  eight rows (`0.03` each) where date, category, merchant/item, amount,
  currency, and current `doc_XX` source_file all match after normalization;
  `0.04` for the exact total `CNY 4262`; and `0.02` for avoiding duplicate,
  boarding-pass-only, unreadable, or unrelated expense rows. A row with an old
  semantic source filename earns no row credit even if the amount is correct.

- **0.10 - Trip report quality.** Full credit requires a grounded report that
  reconstructs the Shanghai to Shenzhen trip over `2026-03-14` to
  `2026-03-16`, mentions the outbound/return flights, hotel stay, taxi/metro,
  workshop/office visit, dinner, museum stop, and the exact total spend
  `CNY 4262`. Generic summaries, unsupported traveler names, wrong dates, or
  missing total-spend reconciliation receive little or no credit here.

- **0.05 - Noisy-source grounding and non-hallucination.** Full credit requires
  evidence in outputs or trace that the executor handled the noisy visual/PDF
  bundle rather than relying on clean filename priors: it must not turn the cat
  image or blurred receipt into trip evidence, must detect the hotel duplicate,
  and must not invent expenses, people, vendors, or files outside the current
  source set.

## 6. Scoring Policy / Score Caps

Compute the rubric total first, then apply all caps below by taking the minimum
applicable score. Caps target pass-critical failures and compose by `min`.

- **Cap at 0.30 - No deliverables.** Fewer than two of the four required output
  areas exist under `/tmp_workspace/results/`.
- **Cap at 0.35 - Archive mostly missing.** The archive directory or most
  required category folders are absent, even if summaries exist.
- **Cap at 0.45 - Severe keep/drop failure.** The result treats two or more of
  `doc_03.jpg`, `doc_08.jpg`, and `doc_10.jpg` as normal kept trip documents,
  or drops three or more canonical kept files without a clear note.
- **Cap at 0.75 - Any material keep/drop error.** One excluded file is kept as
  a normal trip document, one canonical expense-bearing file is dropped, or the
  duplicate/unrelated/unreadable distinction is materially wrong.
- **Cap at 0.50 - Old semantic source bundle.** The output appears to be based
  primarily on older semantic filenames such as `IMG_1043.png`,
  `capture_8811.png`, `return_mailshot.png`, `hotel_booking.jpg`,
  `hotel_booking_copy.jpg`, `taxi_7782.jpg`, `metro_topup.png`,
  `dinner_receipt.jpg`, `coffee_scan.jpg`, `museum_ticket.png`,
  `email_screenshot.png`, `itinerary_notes.pdf`, `cat_photo.jpg`, or
  `blurry_receipt.jpg`, and does not map them back to current `doc_XX` sources.
- **Cap at 0.74 - Mixed or stale source mapping.** Any otherwise correct CSV
  expense row or cleanup-note source identifier uses a semantic old filename
  instead of the current `doc_XX` filename. This cap blocks a pass because
  current provenance is part of the task contract.
- **Cap at 0.58 - Major expense failure.** `expense_summary.csv` is missing,
  unparsable, has fewer than 6 correct canonical rows, misses the hotel, misses
  both flight expenses, or includes the unreadable `doc_10.jpg` as a real
  expense.
- **Cap at 0.72 - Incomplete eight-row expense set.** Exactly 6 or 7 canonical
  rows are correct, or there are extra noncanonical expense rows.
- **Cap at 0.84 - Wrong total/count despite mostly correct rows.** All or most
  expense semantics are present, but the CSV does not contain exactly 8
  canonical expense rows totaling exactly `CNY 4262` after normalization.
- **Cap at 0.65 - OCR-only/noisy-document collapse.** The result shows reliance
  on raw OCR/filename clues without visual verification and consequently
  mishandles noisy documents, such as treating `doc_10.jpg` as readable,
  misidentifying the cat photo, missing the duplicate hotel image, or failing
  to inspect the PDF/screenshot context.
- **Cap at 0.70 - Generic trip report.** `trip_report.md` is generic, could
  describe any trip, or omits the canonical route/dates/itinerary and exact
  spend reconciliation.
- **Cap at 0.80 - Weak renaming/provenance.** Files are copied into category
  folders but not meaningfully renamed, or the renamed archive cannot be audited
  back to current source files without guesswork.
- **Cap at 0.50 - Fabricated or out-of-scope content.** The output adds
  invented source files, invented expenses, or materially unsupported trip
  facts not present in the current sources.
- **Cap at 0.30 - Credential/privacy leak.** Any value from a declared privacy
  source is emitted in user-visible output. No such value is expected in this
  task; this is defense in depth.

A run passes only if the final capped score is `>= 0.90`.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** Stop only when the current `doc_XX` source
  mapping, 11 kept files, 3 cleanup exclusions, exactly 8 expense rows, exact
  `CNY 4262` total, and grounded trip report are all satisfied well enough that
  no cap below `0.90` applies.
- **Continue (`0.60 - 0.89` after caps).** A follow-up is appropriate when the
  work is substantially present and recoverable, such as one missing cleanup
  reason, a mostly correct archive with a small category/provenance issue, or a
  CSV that needs a limited fix to current `doc_XX` source mappings or totals.
- **Fail (`<0.60` after caps).** Do not request more work when deliverables are
  missing, the result is built on the old semantic filename bundle with no
  current mapping, keep/drop decisions are severely wrong, expense extraction is
  mostly wrong, or there is no evidence the noisy sources were inspected.

## 8. Hidden Reference Assets

Supervisor-only reference files:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - authoritative current `doc_XX` inventory,
  expense rows, expected total, and output contract.
- `references/source_document_reference_sheet.jpg` - hidden visual contact
  sheet for auditing the noisy `doc_01` through `doc_14` bundle.
- `references/source_provenance.md` - provenance notes for generated noisy
  source imagery.

## 9. Dynamic Content Note

Offline task. The corpus is static at runtime. Judge renamed archive filenames
semantically, but judge original source provenance strictly against the current
`doc_XX` filenames in `references/ground_truth.json`. If the source files on
disk and the ground truth ever disagree, treat `ground_truth.json` as
authoritative and flag the fixture drift rather than using older run artifacts
as answer keys.
