# Hidden Reference: Synthetic Implant Audit

This file documents the construction quality checks for the 1,500-message mailbox. It is hidden from the executor and is intended only to help the supervisor distinguish real task failures from data-construction problems.

## Distribution

- Total visible email files: 1,500.
- Real Enron kaminski-v public mailbox messages: 1,456.
- Synthetic implants: 44.
- Raw source index (kaminski-v_index.json) was used during construction only; it is NOT shipped in sources/.
- Cleaned real-message pool (1,456 .eml files) was an intermediate construction artifact; it is NOT shipped in sources/. Only sources/mailbox/ ships to the executor.
- Final mixed corpus stored under sources/mailbox/.
- Implant numeric id range: 0037-1492.
- Implants are deliberately spread across the mailbox rather than placed in a single directory or consecutive block.
- Four shallow issues use 3-4 emails each; the deep Blue Ridge/Northstar chain uses 24 emails plus distractors.

## Plausibility Checks

- Real messages come from the public Enron kaminski-v mailbox, which provides research, quantitative analytics, model, and business-analysis corporate noise.
- Synthetic implants are English plaintext .eml files with Enron-style internal senders/recipients and ordinary research-budget, analytics support, consulting, data subscription, and payment subjects.
- The deep issue is split across vendor setup, research budget line splitting, consulting invoices, workpaper reuse, data extracts, steering approval, treasury exception, conflict disclosure, closeout, and records-retention messages.
- Distractors mention similar research-budget concepts but include benign verification or normal approval evidence.
- The public prompt does not assert that misconduct exists; it asks for a neutral internal research / analytics budget compliance review.

## Expected Evaluation Shape

- Surface issues should be findable from a few linked emails and provide partial credit.
- A high score requires reconstructing the deep Blue Ridge Quant / Northstar Research chain from many separated emails.
- Reports that only identify isolated suspicious emails without linking the cross-message chain should remain below pass threshold.

## Implant Ids

- Surface issue ids: ANL-2001-0156, ANL-2001-0476, ANL-2001-0731, ANL-2001-0895, ANL-2001-0214, ANL-2001-0588, ANL-2001-1022, ANL-2001-1376, ANL-2001-0332, ANL-2001-0644, ANL-2001-1181, ANL-2001-0448, ANL-2001-0910, ANL-2001-1329
- Deep issue core ids: ANL-2001-0037, ANL-2001-0084, ANL-2001-0129, ANL-2001-0176, ANL-2001-0223, ANL-2001-0284, ANL-2001-0341, ANL-2001-0404, ANL-2001-0469, ANL-2001-0532, ANL-2001-0611, ANL-2001-0688, ANL-2001-0746, ANL-2001-0823, ANL-2001-0914, ANL-2001-0977, ANL-2001-1058, ANL-2001-1116, ANL-2001-1194, ANL-2001-1267, ANL-2001-1338, ANL-2001-1410, ANL-2001-1463, ANL-2001-1492
- Distractor ids: ANL-2001-0260, ANL-2001-0620, ANL-2001-0869, ANL-2001-0990, ANL-2001-1088, ANL-2001-1244
