# Hidden Evaluation Rule — Warranty Case Cleanup

## 1. Grading Philosophy

Judge whether the executor actually inspected the current cluttered download
fixtures, selected only after-sales / warranty / return evidence, grouped it by
product or order, and produced case-level conclusions that match the locked
ground truth. Polished folders, confident prose, or generic "cleanup" notes do
not compensate for wrong source grounding, wrong keep/drop decisions, or missed
weak evidence.

The pass bar is strict: a pass requires all material case groupings,
case-readiness judgments, and missing-evidence statements to be correct after
applying score caps. Exact output folder names may vary, but the contents and
provenance must be traceable to the current `file_XX` source files.

## 2. Task Contract

The executor must inspect
`/tmp_workspace/clawbench/sources/downloads_clutter/` and produce all of:

- `/tmp_workspace/results/warranty_cases/`
- `/tmp_workspace/results/warranty_index.csv`
- `/tmp_workspace/results/missing_evidence.md`
- `/tmp_workspace/results/claims_overview.md`

`warranty_index.csv` must be a real CSV or plainly parseable CSV-like table
with at least: product name, order number, purchase date, amount, platform /
merchant, current status, and evidence files. Order numbers are required when
visible in the source; `UNKNOWN` is acceptable only if the source does not show
one, which is not the case for the three canonical cases here.

## 3. Source-Selection and Target-Resolution Rules

The authoritative input set is the current files named `file_01` through
`file_12` under `downloads_clutter/`. Do not use obsolete semantic fixture
names from earlier versions of this task as source truth.

The executor may rename copied evidence files inside `warranty_cases/`, in
English or Chinese, as long as an auditor can trace each copied file back to the
current source content. When matching result artifacts to source files, use
visible content first, then order number / product / platform, then path names.
Folder names alone are not enough if the contained files or index contradict
the source mapping.

Canonical source mapping:

- `file_09.png` - JD.com order screenshot for `JD202603010184`, Mini espresso
  machine, `2026-03-01`, `CNY 699`.
- `file_06.pdf` - espresso machine electronic invoice.
- `file_11.png` - espresso machine logistics tracking, delivered
  `2026-03-04`, signed by front desk.
- `file_01.png` - espresso machine customer-service chat: bottom leak after
  three uses, exchange requested, seller asks for order screenshot, video, and
  invoice.
- `file_04.jpg` - espresso machine defect / leak photo.
- `file_10.png` - Tmall order screenshot for `TM202512190552`, Noise
  cancelling headphones, `2025-12-19`, `CNY 1299`.
- `file_12.png` - headphones warranty page, coverage until `2027-12-19`,
  manufacturer warranty, serial verified.
- `file_02.png` - headphones support chat: right ear cup loses sound
  intermittently, warranty repair suggested, order number and serial photo
  requested.
- `file_05.jpg` - headphones serial-number photo.
- `file_03.png` - Taobao order screenshot for `TB20240210444`, Foldable desk
  lamp, `2024-02-10`, `CNY 149`, delivered.
- `file_07.pdf` - desk lamp product manual; optional supporting context only.
- `file_08.png` - unrelated old image / meme; must be dropped or explicitly
  identified as unrelated.

Obsolete semantic names such as `order_espresso.png`,
`invoice_espresso.pdf`, `tracking_espresso.png`, `chat_espresso.png`,
`espresso_machine_leak.jpg`, `order_headphones.png`,
`warranty_headphones.png`, `chat_headphones.png`, `headphones_serial.jpg`,
`desklamp_order.png`, `manual_desklamp.pdf`, or `meme_old.png` are not current
source filenames. Result-side renames are fine; treating those obsolete names
as the input source mapping is not.

## 4. Locked Ground Truth

Use `references/ground_truth.json` as authoritative. The canonical cases are:

- `espresso_machine_jd202603010184`: Mini espresso machine on JD.com /
  BrewHome Official Store. Key evidence is `file_09.png`, `file_06.pdf`,
  `file_11.png`, `file_01.png`, and `file_04.jpg`. It is the strongest case:
  exchange / after-sales evidence is largely complete. The locked missing list
  is empty. The visible chat's video request may be mentioned as a possible
  next step, but it must not be used to mark the case as weak or less ready
  than the headphones case.
- `headphones_tm202512190552`: Noise cancelling headphones on Tmall. Key
  evidence is `file_10.png`, `file_12.png`, `file_02.png`, and `file_05.jpg`.
  It is mostly ready for warranty repair, but the invoice is missing from the
  sources and must be called out.
- `desklamp_tb20240210444`: Foldable desk lamp on Taobao. Key evidence is
  `file_03.png`; `file_07.pdf` is optional supporting context. This is a weak /
  suspected / information-insufficient case, not a directly actionable claim.
  It must not be silently dropped. Missing evidence includes no issue
  description or support chat, no invoice, and no logistics or warranty
  evidence.

Readiness order is: espresso strongest, headphones mostly ready but missing
invoice, desk lamp weak / not directly actionable. `file_08.png` is unrelated.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit only for source-grounded,
auditable content; do not infer correctness from file polish.

- **0.12 - Required output shape.** All four required outputs exist under
  `/tmp_workspace/results/`. `warranty_cases/` is a directory. The index is
  parseable and contains required columns or clear equivalents. The missing
  evidence and overview files are non-empty and case-specific. Zero this line
  if any required artifact is absent.

- **0.18 - Source provenance and keep/drop decisions.** The result correctly
  identifies the three relevant product/order groups and the unrelated
  `file_08.png`. Full credit requires every key evidence file in the locked
  mapping to be either copied into the proper case folder or explicitly
  referenced as relevant evidence, `file_07.pdf` treated as optional desk-lamp
  support, and `file_08.png` excluded or explicitly listed as unrelated. Deduct
  for untraceable renames, dropped key evidence, duplicated/conflicting copies,
  or evidence paths that cannot be matched to current `file_XX` fixtures.

- **0.22 - Case grouping archive quality.** Espresso, headphones, and desk
  lamp must be separated by product/order. Espresso must contain only the JD
  espresso evidence set; headphones must contain only the Tmall headphones
  evidence set; desk lamp must be represented as weak/suspected using
  `file_03.png` and optionally `file_07.pdf`. No espresso/headphones evidence
  may be conflated, and no folder may mix different order numbers. Full credit
  requires clear, non-generic renames for copied evidence.

- **0.22 - `warranty_index.csv` factual accuracy.** The index must have one
  row for each canonical case, including the weak desk lamp case. For each row,
  check product name, exact order number, purchase date, amount/currency,
  platform / merchant, status, and evidence-file references against the locked
  ground truth. Full credit requires all three rows and all visible fields
  correct after harmless formatting normalization (`CNY 699` vs `699 yuan` is
  acceptable). Wrong or missing visible order numbers are material errors.

- **0.14 - `missing_evidence.md` accuracy.** The missing-evidence file must
  state that the headphones case lacks an invoice and that the desk lamp lacks
  issue/support-chat evidence, invoice, and logistics or warranty evidence. It
  should not list locked critical missing evidence for espresso. Optional next
  steps, such as recording a leak video because the chat asks for one, are
  acceptable only if clearly labeled optional and not used to downgrade the
  espresso case below headphones.

- **0.12 - `claims_overview.md` readiness conclusions.** The overview must
  distinguish the three cases in the locked readiness order: espresso is the
  strongest / largely complete after-sales exchange case; headphones are mostly
  ready for warranty repair but missing an invoice; desk lamp is weak,
  information-insufficient, and not directly actionable. The overview must also
  confirm that `file_08.png` is unrelated or otherwise excluded.

Total: `0.12 + 0.18 + 0.22 + 0.22 + 0.14 + 0.12 = 1.00`.

## 6. Scoring Policy / Score Caps

Compute the rubric score line-by-line, then apply every applicable cap by
`min(raw_score, cap)`. Caps are strict and may prevent a pass even when the
folder structure looks polished.

- **Cap at 0.30 - No usable deliverables.** Fewer than two required output
  artifacts exist, or the result is only a final chat message with no saved
  files.
- **Cap at 0.35 - Generic cleanup notes.** The artifacts contain generic
  advice such as "check invoice/logistics/warranty" without case-specific order
  numbers, products, source-backed evidence, and readiness conclusions.
- **Cap at 0.40 - Wrong case grouping.** Files are grouped by document type,
  dumped into one folder, mixed across products/orders, or otherwise not
  organized by product/order.
- **Cap at 0.45 - Obsolete source mapping.** The answer treats old semantic
  fixture names such as `order_espresso.png` or `meme_old.png` as the source
  filenames instead of the current `file_XX` inputs, and the provenance cannot
  be traced to the current fixtures. Do not apply this cap merely because the
  executor renamed copied result files descriptively.
- **Cap at 0.50 - Missing a clearly supported case.** Either the espresso or
  headphones case is absent from `warranty_cases/` or absent from
  `warranty_index.csv`.
- **Cap at 0.55 - Major wrong keep/drop decision.** The result includes
  `file_08.png` as warranty evidence, drops two or more locked key evidence
  files from espresso/headphones, or keeps a broad set of unrelated files
  without explaining exclusions.
- **Cap at 0.60 - Missing-evidence file not meaningful.** `missing_evidence.md`
  is absent, empty, or does not identify at least the headphones invoice gap.
- **Cap at 0.70 - Missed weak/suspected evidence.** The desk lamp order
  `TB20240210444` is silently omitted from all of the index, missing-evidence
  file, overview, and case archive, or it is incorrectly treated as a fully
  actionable warranty case.
- **Cap at 0.80 - Material readiness reversal.** The overview or index says
  headphones are more complete than espresso, marks headphones fully complete
  without the invoice caveat, or marks espresso non-actionable because of a
  supposedly required missing item.
- **Cap at 0.84 - Inconsistent weak-case handling.** The desk lamp appears in
  one artifact but is missing or contradicted in the index, missing-evidence
  file, or overview. A pass requires consistent desk-lamp treatment across
  case archive or explicit case note, index, missing-evidence file, and
  overview.
- **Cap at 0.84 - Visible order-number error.** Any canonical visible order
  number is wrong, omitted, or set to `UNKNOWN`, including the desk lamp
  `TB20240210444`.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) - stop. A passing run has all required
  artifacts, current `file_XX` provenance, correct keep/drop decisions, all
  three canonical cases in the index, case-specific missing-evidence notes, and
  the locked readiness order.
- **Continue** (`0.60 - 0.89` after caps) - request one targeted repair when
  the archive is mostly source-grounded but has fixable defects, such as a
  missing desk-lamp row, inconsistent weak-case handling, a wrong readiness
  label, or a missing invoice note.
- **Fail** (`< 0.60` after caps) - do not continue. This includes generic
  cleanup-only outputs, wrong grouping, obsolete source mapping that cannot be
  traced to `file_XX`, major keep/drop failures, or absence of meaningful
  missing-evidence documentation.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - structured expected cases, key files,
  optional supporting files, missing evidence, ignored files, and readiness
  order.

## 9. Dynamic Content Note

Offline task. The corpus is static at runtime; judge against the current
on-disk `file_XX` fixtures and `references/ground_truth.json`. If output names
or older run artifacts conflict with the current ground truth, the current
ground truth wins.
