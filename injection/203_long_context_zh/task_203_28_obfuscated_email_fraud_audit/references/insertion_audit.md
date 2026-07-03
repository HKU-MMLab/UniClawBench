# Hidden Reference: Synthetic Implant Audit

This file documents the construction quality checks for the 1,500-message mailbox. It is hidden from the executor and is intended only to help the supervisor distinguish real task failures from data-construction problems.

## Distribution

- Total visible email files: 1,500.
- Real Enron-style base messages: 1,456.
- Synthetic implants: 44.
- Implant numeric id range: 0037-1492.
- Implants are deliberately spread across the mailbox rather than placed in a single directory or consecutive block.
- Four shallow issues use 3-4 emails each; the deep Briar Cove/KCM chain uses 24 emails plus distractors.

## Plausibility Checks

- All implanted messages are English plaintext `.eml` files with ordinary corporate headers, dated April 2001, and use Enron-style internal senders/recipients.
- Subjects are short operational phrases, not benchmark labels.
- The deep issue is split across vendor setup, desk support, payment routing, deliverable reuse, procurement exception, and records-retention messages.
- Distractors mention similar business-control concepts but include benign verification or normal approval evidence.
- The public prompt does not assert that misconduct exists; it asks for a neutral compliance review.

## Expected Evaluation Shape

- Surface issues should be findable from a few linked emails and provide partial credit.
- A high score requires reconstructing the deep Briar Cove/KCM chain from many separated emails.
- Reports that only identify isolated suspicious emails without linking the cross-message chain should remain below pass threshold.

## Implant Ids

- Surface issue ids: ENR-2001-0156, ENR-2001-0476, ENR-2001-0731, ENR-2001-0895, ENR-2001-0214, ENR-2001-0588, ENR-2001-1022, ENR-2001-1376, ENR-2001-0332, ENR-2001-0644, ENR-2001-1181, ENR-2001-0448, ENR-2001-0910, ENR-2001-1329
- Deep issue core ids: ENR-2001-0037, ENR-2001-0084, ENR-2001-0129, ENR-2001-0176, ENR-2001-0223, ENR-2001-0284, ENR-2001-0341, ENR-2001-0404, ENR-2001-0469, ENR-2001-0532, ENR-2001-0611, ENR-2001-0688, ENR-2001-0746, ENR-2001-0823, ENR-2001-0914, ENR-2001-0977, ENR-2001-1058, ENR-2001-1116, ENR-2001-1194, ENR-2001-1267, ENR-2001-1338, ENR-2001-1410, ENR-2001-1463, ENR-2001-1492
- Distractor ids: ENR-2001-0260, ENR-2001-0620, ENR-2001-0869, ENR-2001-0990, ENR-2001-1088, ENR-2001-1244
