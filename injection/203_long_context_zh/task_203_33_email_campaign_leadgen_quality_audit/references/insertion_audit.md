# Hidden Reference: Synthetic Implant Audit

This file documents the construction quality checks for the 1,500-message mailbox. It is hidden from the executor and is intended only to help the supervisor distinguish real task failures from data-construction problems.

## Distribution

- Total visible email files: 1,500.
- Real Apache SpamAssassin Public Corpus messages: 1,456.
- Synthetic implants: 44.
- Raw public archives (5 tar.bz2 archives plus extracted files) were used during construction only; they are NOT shipped in sources/.
- Cleaned real-message pool (1,456 .eml files) was an intermediate construction artifact; it is NOT shipped in sources/. Only sources/mailbox/ ships to the executor.
- Final mixed corpus stored under sources/mailbox/.
- Implant numeric id range: 0037-1492.
- Implants are deliberately spread across the mailbox rather than placed in a single directory or consecutive block.
- Four shallow issues use 3-4 emails each; the deep BrightWave/Northstar chain uses 24 emails plus distractors.

## Plausibility Checks

- Real messages come from the public SpamAssassin ham/spam corpus, which provides broad email-campaign, list, marketing, newsletter, sales, spam, and ordinary personal/business background noise.
- Synthetic implants are English plaintext .eml files with ordinary campaign-operations, list-management, vendor-settlement, invoice, and reporting subjects.
- The deep issue is split across campaign kickoff, recipient-list overlap, suppression-list handling, seed/test traffic, bounce and complaint treatment, raw send logs, invoice release, makegood credit, DBA/payment routing, closeout, and records-retention messages.
- Distractors mention similar campaign-quality concepts but include benign verification or normal approval evidence.
- The public prompt does not assert that misconduct exists; it asks for a neutral email campaign / lead-generation quality review.

## Expected Evaluation Shape

- Surface issues should be findable from a few linked emails and provide partial credit.
- A high score requires reconstructing the deep BrightWave Leads / Northstar Reach chain from many separated emails.
- Reports that only identify isolated suspicious emails without linking the cross-message chain should remain below pass threshold.
- Reports that treat ordinary public spam messages as internal campaign findings without supporting links should be penalized for calibration.

## Implant Ids

- Surface issue ids: CAM-2003-0156, CAM-2003-0476, CAM-2003-0731, CAM-2003-0895, CAM-2003-0214, CAM-2003-0588, CAM-2003-1022, CAM-2003-1376, CAM-2003-0332, CAM-2003-0644, CAM-2003-1181, CAM-2003-0448, CAM-2003-0910, CAM-2003-1329
- Deep issue core ids: CAM-2003-0037, CAM-2003-0084, CAM-2003-0129, CAM-2003-0176, CAM-2003-0223, CAM-2003-0284, CAM-2003-0341, CAM-2003-0404, CAM-2003-0469, CAM-2003-0532, CAM-2003-0611, CAM-2003-0688, CAM-2003-0746, CAM-2003-0823, CAM-2003-0914, CAM-2003-0977, CAM-2003-1058, CAM-2003-1116, CAM-2003-1194, CAM-2003-1267, CAM-2003-1338, CAM-2003-1410, CAM-2003-1463, CAM-2003-1492
- Distractor ids: CAM-2003-0260, CAM-2003-0620, CAM-2003-0869, CAM-2003-0990, CAM-2003-1088, CAM-2003-1244
