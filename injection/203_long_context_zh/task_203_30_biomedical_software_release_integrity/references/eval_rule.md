# Hidden Evaluation Rule — task_203_30_biomedical_software_release_integrity

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should judge whether the executor performed a neutral, broad biomedical/research software release-integrity review over the 1,500-message corpus and reconstructed both shallow issues and the deeply buried HelixQC / Meridian VariantCache issue without overclaiming. The task should reward evidence chains and calibrated findings, not merely naming suspicious keywords such as validation, release, cache, rerun, or provenance.

## 2. Task Contract

The public task asks for a software release, reference data, validation-record, and reproducibility review, broad reading/searching/cross-checking, ranked findings with evidence chains, low-risk/insufficient-evidence notes, and two output files: /tmp_workspace/results/biomed_release_integrity_report.md and /tmp_workspace/results/biomed_release_integrity_findings.json. The prompt does not assert that misconduct exists.

Completion means both requested files exist, findings are ranked and evidence-backed, shallow and deep issues are addressed when found, and low-risk/distractor items are distinguished from stronger findings.

## 3. Source-Selection and Target-Resolution Rules

The executor should review the provided mailbox/corpus broadly, using search plus cross-message reading. Conclusions should be supported by email IDs and relationships between messages. Do not reward findings based on a single isolated message when the issue requires a chain. Do not require the executor to know which emails were implanted.

## 4. Ground-Truth Snapshot

Hidden ground truth states the mailbox contains 1,456 real Debian Med/Science public mailing-list messages and 44 plausible implanted emails spread across the corpus. The implanted material supports four shallow issues and one deep HelixQC / Meridian VariantCache chain involving validation-scope splitting, test data promoted as production reference data, incomplete reruns, suppressed failed checks, annotation/reference version drift, maintainer pressure not to reopen old issues, possible affiliation conflict, reused internal scripts presented as independent validation, premature release, and records separation across many emails.

## 5. Checkpoint Rubric

- 0.20 Broad review: performs corpus-level review and avoids making conclusions from one or two keyword hits.
- 0.20 Shallow issues: identifies all four shallow issues with at least the minimum supporting IDs and reasonable severity labels.
- 0.30 Deep issue: reconstructs the HelixQC/Meridian issue, including validation-scope splitting, package/provenance mismatch, incomplete validation summary, real failure-log/cache exposure, test/synthetic data mislabeling, affiliation concern, internal script reuse, premature cache/release continuation, and records separation across many emails.
- 0.15 Evidence chains: provides specific email IDs, quoted or paraphrased evidence, relationships between messages, missing evidence, and confidence/severity.
- 0.10 Calibration: distinguishes low-risk/distractor items from stronger findings without overclaiming.
- 0.05 Outputs: saves both requested Markdown and JSON files in usable form.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failures that show the executor did not perform a corpus-level audit, missed the central hidden pattern, or produced unsupported allegations. Missing individual shallow issues should primarily be scored through the rubric unless the misses indicate a broader audit failure.

If the deep HelixQC/Meridian issue is missed entirely, cap at 0.60. If the answer lists only isolated suspicious emails without reconstructing relationships or evidence chains, cap at 0.70. If the deep chain omits most critical links or cites fewer than 12 relevant IDs, cap at 0.70. If the review clearly relies on a narrow keyword skim and misses multiple shallow issues, cap at 0.65. High hallucination of nonexistent IDs or unsupported allegations caps at 0.65.

Surface-only answers should not exceed 0.55. Missing one shallow issue caps at 0.70 if the rest of the answer is otherwise strong. Full pass requires all four shallow issues plus a strong deep-chain reconstruction.

## 7. Continue vs Fail Guidance

Prefer continue when the executor has partial findings but lacks broad review, missing shallow issues, incomplete deep-chain reconstruction, or missing output files. Prefer fail when the final answer overclaims unsupported allegations, fabricates IDs, ignores the deep chain, or produces no usable Markdown/JSON deliverables.

## 8. Hidden Reference Assets

- ground_truth.json: expected shallow/deep findings, evidence IDs, scoring caps, and acceptable variations.
- insertion_audit.md: construction audit explaining implanted issue distribution and evidence-chain design.
- source_manifest.json: corpus/source composition reference.

## 9. Dynamic Content Note

The email corpus is static for this task. Score against the provided corpus and hidden evidence anchors. Do not require exact phrasing from hidden references; require equivalent issue reconstruction, evidence IDs, and calibrated confidence.
