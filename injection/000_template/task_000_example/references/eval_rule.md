# Evaluation Rule Template

Use this file as the primary hidden judging spec for the task.
Prefer outcome-oriented checkpoints. Process constraints should appear only
when they are needed to identify the intended target, enforce safety /
privacy, or resolve ambiguity. Do not require excessive "proof of work"
beyond what is needed to audit the final result.

## 1. Grading Philosophy

State what the supervisor should care about most: satisfied checkpoints and
the supported final result.
List any process constraints that still matter, and explain why they matter.

## 2. Task Contract

Restate the public task in supervisor terms.
Define what the executor must accomplish and what counts as completion.

## 3. Source-Selection and Target-Resolution Rules

Specify which source the executor should use when source choice matters
(e.g., first search result, specific URL).
Define how to resolve ambiguity when multiple candidates exist.

## 4. Ground-Truth Snapshot

Record the hidden ground-truth captured at a specific date.
Include concrete values (product names, prices, URLs, video IDs) so the supervisor can verify.

## 5. Checkpoint Rubric

Define weighted checkpoints that together total 1.0.
Each checkpoint should specify: the observable state or saved result that
matters, the minimum visible evidence needed, and the hidden reference
anchor (if any).
Favor checkpoints like "right target identified", "correct page reached",
"result saved", and "safety preserved".
Avoid checkpointing every intermediate click unless the task genuinely
depends on it.

## 6. Scoring Policy / Score Caps

Define score caps for real failure modes or safety violations.
Partial credit should come from satisfied checkpoints.
Do not demand extra screenshots, logs, or path proofs beyond what is needed
for auditability.
Specify pass requirements (all critical checkpoints satisfied, evidence
sufficient for audit).

## 7. Continue vs Fail Guidance

List scenarios where the supervisor should prefer `continue` (recoverable gaps).
List scenarios where the supervisor should prefer `fail` (unrecoverable mistakes).

## 8. Hidden Reference Assets

List the hidden files the supervisor should use for cross-checking.
Explain what each file shows and how it anchors the checkpoints above.

## 9. Dynamic Content Note (if applicable)

Note any values that may change between the hidden capture and the actual run.
Explain how the supervisor should handle such differences in scoring.
