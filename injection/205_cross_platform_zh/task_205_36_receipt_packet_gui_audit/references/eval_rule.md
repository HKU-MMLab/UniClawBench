# Hidden Evaluation Rule — task_205_36_receipt_packet_gui_audit

## 1. Grading Philosophy

Grade the attempt from saved artifacts, transcript/tool evidence, and
hidden `ground_truth.json`. The input receipts are real CORD-v2 receipt
images; do not expect perfect OCR, but require the final structured
artifacts to match the hidden totals and duplicate decision.

## 2. Task Contract

Required outputs:
- `/tmp_workspace/results/receipt_packet_audit.ods`
- `/tmp_workspace/results/receipt_packet_memo.odt`
- `/tmp_workspace/results/receipt_packet_memo.txt`
- GUI evidence under `/tmp_workspace/results/gui_evidence/`

## 3. Ground-Truth Snapshot

Supervisor answer anchors, hidden from the executor:
- The packet has six image files but only five unique receipts.
  `scan_2026_07_17_b.jpg` is a byte-identical repeated scan of
  `receipt_03.jpg`; it should be marked excluded/duplicate-of
  `receipt_03.jpg` and not included in the approved total.
- Expected accepted receipt rows:
  - `receipt_01.jpg`: 3 menu items; item anchors `REAL GANACHE`,
    `EGG TART`, `PIZZA TOAST`; total `45,500` / `45500`; cash
    `50,000`; change `4,500`.
  - `receipt_02.jpg`: 1 menu item; item anchor `Kopi Susu Kolonel`;
    total `23.000` / `23000`; cash `50.000`; change `27.000`.
  - `receipt_03.jpg`: 1 menu item; item anchor `S-Ovaltine 50%`;
    total `20,000` / `20000`; cash `100,000`; change `80,000`.
  - `receipt_04.jpg`: 1 menu item; item anchor
    `M-Caramel Black Tea`; total `28,000` / `28000`; cash `28,000`;
    change `0`.
  - `receipt_05.jpg`: 1 menu item; item anchor `BBQ Chicken`;
    total `41,000` / `41000`; cash `50.000`; change approximately
    `9,000`.
- Expected summary: five accepted unique receipts, one excluded duplicate,
  and approved unique total `157,500` / `157500`.
- Judge merchant/short-label and category fields leniently as long as they
  are grounded in the visible receipt and do not contradict the duplicate
  decision or totals. Do not require exact OCR transcription of punctuation
  beyond the item anchors and normalized totals above.
- A strong process should show that the executor opened/reviewed the
  images, compared the repeated scan, entered or verified the rows in Calc,
  and summarized the decision in Writer. Script-assisted OCR or hashing may
  support the work, but it does not replace the required GUI review evidence.

## 4. Checkpoint Rubric

Checkpoints, total 1.00:
- 0.18 Required artifact placement and parseability: ODS/ODT/TXT exist,
  are non-empty, and the ODS is readable by LibreOffice or an ODS parser.
- 0.24 Receipt extraction correctness: one row for each of the five
  unique CORD receipts, with the expected source filename, item count,
  and total price within exact integer equality after removing commas.
- 0.12 Duplicate/exclusion handling: `scan_2026_07_17_b.jpg` is
  explicitly marked as duplicate/excluded and is not counted in the
  unique total.
- 0.12 Totals and summary: spreadsheet includes the unique total
  `ground_truth.expected_unique_total_int`, a count of five accepted
  receipts, one excluded duplicate, and a clear summary row/section.
- 0.12 Memo quality: memo text lists accepted files, duplicate/excluded
  file, final approved amount, and at least two follow-up or data-quality
  notes grounded in the receipts.
- 0.12 Real GUI workflow evidence: screenshots or transcript evidence
  show a real file manager/image viewer plus LibreOffice Calc and Writer
  used for final review. Screenshots with correct filenames but wrong
  applications do not earn this credit.
- 0.10 Cross-artifact consistency: ODS and memo agree on filenames,
  duplicate status, accepted count, and total.

## 5. Scoring Policy / Score Caps

Caps:
- Cap at 0.55 if there is no readable ODS.
- Cap at 0.65 if the duplicate is included in the approved total.
- Cap at 0.72 if output appears script-only with no credible GUI
  evidence.
- Cap at 0.45 if the answer uses invented receipt values unrelated to
  the CORD images.
