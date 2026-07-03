# Hidden Reference: Synthetic Implant Audit

This file documents the construction quality checks for the 1,500-message mailbox. It is hidden from the executor and is intended only to help the supervisor distinguish real task failures from data-construction problems.

## Distribution

- Total visible email files: 1,500.
- Real Debian Med/Science public mailing-list messages: 1,456.
- Synthetic implants: 44.
- Raw source thread pages (80 HTML files) were used during construction only; they are NOT shipped in sources/.
- Raw message pages (2928 HTML files) were used during construction only; they are NOT shipped in sources/.
- Cleaned real-message pool (1,456 .eml files) was an intermediate construction artifact; it is NOT shipped in sources/. Only sources/mailbox/ ships to the executor.
- Final mixed corpus stored under sources/mailbox/.
- Implant numeric id range: 0037-1492.
- Implants are deliberately spread across the mailbox rather than placed in a single directory or consecutive block.
- Four shallow issues use 3-4 emails each; the deep HelixQC/Meridian chain uses 24 emails plus distractors.

## Plausibility Checks

- Real messages come from Debian Med and Debian Science public mailing-list archives and keep realistic mailing-list subjects, authors, and thread content.
- Synthetic implants are English plaintext .eml files with Debian Med-style project senders/recipients and ordinary release/validation-review subjects.
- The deep issue is split across release planning, validation scope, reference-cache provenance, data governance, rerun evidence, affiliation disclosure, and records-retention messages.
- Distractors mention similar validation/version/provenance concepts but include benign verification or normal correction evidence.
- The public prompt does not assert that misconduct exists; it asks for a neutral biomedical software release-integrity review.

## Expected Evaluation Shape

- Surface issues should be findable from a few linked emails and provide partial credit.
- A high score requires reconstructing the deep HelixQC / Meridian VariantCache chain from many separated emails.
- Reports that only identify isolated suspicious emails without linking the cross-message chain should remain below pass threshold.

## Implant Ids

- Surface issue ids: BIO-2024-0156, BIO-2024-0476, BIO-2024-0731, BIO-2024-0895, BIO-2024-0214, BIO-2024-0588, BIO-2024-1022, BIO-2024-1376, BIO-2024-0332, BIO-2024-0644, BIO-2024-1181, BIO-2024-0448, BIO-2024-0910, BIO-2024-1329
- Deep issue core ids: BIO-2024-0037, BIO-2024-0084, BIO-2024-0129, BIO-2024-0176, BIO-2024-0223, BIO-2024-0284, BIO-2024-0341, BIO-2024-0404, BIO-2024-0469, BIO-2024-0532, BIO-2024-0611, BIO-2024-0688, BIO-2024-0746, BIO-2024-0823, BIO-2024-0914, BIO-2024-0977, BIO-2024-1058, BIO-2024-1116, BIO-2024-1194, BIO-2024-1267, BIO-2024-1338, BIO-2024-1410, BIO-2024-1463, BIO-2024-1492
- Distractor ids: BIO-2024-0260, BIO-2024-0620, BIO-2024-0869, BIO-2024-0990, BIO-2024-1088, BIO-2024-1244
