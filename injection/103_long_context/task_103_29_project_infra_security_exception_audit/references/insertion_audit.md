# Hidden Reference: Synthetic Implant Audit

This file documents the construction quality checks for the 1,500-message mailbox. It is hidden from the executor and is intended only to help the supervisor distinguish real task failures from data-construction problems.

## Distribution

- Total visible email files: 1,500.
- Real Apache httpd dev public mailing-list messages: 1,456.
- Synthetic implants: 44.
- Raw source archives downloaded under sources/raw_public_emails/: 36 monthly mbox files.
- Cleaned real-message pool stored under sources/clean_real_emails/: 1,456 .eml files.
- Final mixed corpus stored under sources/mailbox/.
- Implant numeric id range: 0037-1492.
- Implants are deliberately spread across the mailbox rather than placed in a single directory or consecutive block.
- Four shallow issues use 3-4 emails each; the deep Peregrine/Nightjar chain uses 24 emails plus distractors.

## Plausibility Checks

- Real messages come from the public Apache httpd dev mailing list archive and keep realistic mailing-list headers, subjects, and thread content.
- Synthetic implants are English plaintext  files with Apache-style project senders/recipients and ordinary infrastructure/release-review subjects.
- The deep issue is split across infra access, service-owner records, log export, security review, release pressure, affiliation disclosure, and records-retention messages.
- Distractors mention similar access/security/release-review concepts but include benign verification or normal approval evidence.
- The public prompt does not assert that misconduct exists; it asks for a neutral project infrastructure security exception review.

## Expected Evaluation Shape

- Surface issues should be findable from a few linked emails and provide partial credit.
- A high score requires reconstructing the deep Peregrine BuildWorks / Nightjar CI chain from many separated emails.
- Reports that only identify isolated suspicious emails without linking the cross-message chain should remain below pass threshold.

## Implant Ids

- Surface issue ids: ASF-2024-0156, ASF-2024-0476, ASF-2024-0731, ASF-2024-0895, ASF-2024-0214, ASF-2024-0588, ASF-2024-1022, ASF-2024-1376, ASF-2024-0332, ASF-2024-0644, ASF-2024-1181, ASF-2024-0448, ASF-2024-0910, ASF-2024-1329
- Deep issue core ids: ASF-2024-0037, ASF-2024-0084, ASF-2024-0129, ASF-2024-0176, ASF-2024-0223, ASF-2024-0284, ASF-2024-0341, ASF-2024-0404, ASF-2024-0469, ASF-2024-0532, ASF-2024-0611, ASF-2024-0688, ASF-2024-0746, ASF-2024-0823, ASF-2024-0914, ASF-2024-0977, ASF-2024-1058, ASF-2024-1116, ASF-2024-1194, ASF-2024-1267, ASF-2024-1338, ASF-2024-1410, ASF-2024-1463, ASF-2024-1492
- Distractor ids: ASF-2024-0260, ASF-2024-0620, ASF-2024-0869, ASF-2024-0990, ASF-2024-1088, ASF-2024-1244
