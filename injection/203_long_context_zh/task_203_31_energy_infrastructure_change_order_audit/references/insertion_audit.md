# Hidden Reference: Synthetic Implant Audit

This file documents the construction quality checks for the 1,500-message mailbox. It is hidden from the executor and is intended only to help the supervisor distinguish real task failures from data-construction problems.

## Distribution

- Total visible email files: 1,500.
- Real Enron shackleton-s public mailbox messages: 1,456.
- Synthetic implants: 44.
- Raw source index (shackleton-s_index.json) was used during construction only; it is NOT shipped in sources/.
- Cleaned real-message pool (1,456 .eml files) was an intermediate construction artifact; it is NOT shipped in sources/. Only sources/mailbox/ ships to the executor.
- Final mixed corpus stored under sources/mailbox/.
- Implant numeric id range: 0037-1492.
- Implants are deliberately spread across the mailbox rather than placed in a single directory or consecutive block.
- Four shallow issues use 3-4 emails each; the deep Red Mesa/Harbor chain uses 24 emails plus distractors.

## Plausibility Checks

- Real messages come from the public Enron shackleton-s mailbox, which provides legal/contracts/project-style corporate noise.
- Synthetic implants are English plaintext .eml files with Enron-style internal senders/recipients and ordinary field support, procurement, payment, and project-controls subjects.
- The deep issue is split across subcontract setup, field tickets, invoices, delivery tickets, photos, owner approval, treasury exception, conflict disclosure, retainage, and records-retention messages.
- Distractors mention similar project-control concepts but include benign verification or normal approval evidence.
- The public prompt does not assert that misconduct exists; it asks for a neutral energy infrastructure change-order audit.

## Expected Evaluation Shape

- Surface issues should be findable from a few linked emails and provide partial credit.
- A high score requires reconstructing the deep Red Mesa Civil / Harbor Field Services chain from many separated emails.
- Reports that only identify isolated suspicious emails without linking the cross-message chain should remain below pass threshold.

## Implant Ids

- Surface issue ids: ENP-2001-0156, ENP-2001-0476, ENP-2001-0731, ENP-2001-0895, ENP-2001-0214, ENP-2001-0588, ENP-2001-1022, ENP-2001-1376, ENP-2001-0332, ENP-2001-0644, ENP-2001-1181, ENP-2001-0448, ENP-2001-0910, ENP-2001-1329
- Deep issue core ids: ENP-2001-0037, ENP-2001-0084, ENP-2001-0129, ENP-2001-0176, ENP-2001-0223, ENP-2001-0284, ENP-2001-0341, ENP-2001-0404, ENP-2001-0469, ENP-2001-0532, ENP-2001-0611, ENP-2001-0688, ENP-2001-0746, ENP-2001-0823, ENP-2001-0914, ENP-2001-0977, ENP-2001-1058, ENP-2001-1116, ENP-2001-1194, ENP-2001-1267, ENP-2001-1338, ENP-2001-1410, ENP-2001-1463, ENP-2001-1492
- Distractor ids: ENP-2001-0260, ENP-2001-0620, ENP-2001-0869, ENP-2001-0990, ENP-2001-1088, ENP-2001-1244
