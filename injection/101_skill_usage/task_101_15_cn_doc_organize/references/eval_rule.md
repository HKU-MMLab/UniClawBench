# Hidden Evaluation Rule — task_101_15_cn_doc_organize

## 1. Grading Philosophy

Grade on whether the public request was actually carried out: 143 Chinese
`.docx` files sorted into the **four fixed buckets** declared in the prompt
(`合同 / 会议纪要 / 项目报告 / 其他`), renamed to `YYYYMMDD_<topic>.docx`,
accompanied by a faithful `index.md` catalog. Classification must reflect
**what the document is for** based on its content — the prompt explicitly
forbids filename-only classification, and many surface features (filename,
leading phrase) deliberately diverge from true content category. The
executor is expected to open and read content, not match filename
keywords.

The supervisor should also confirm that the workspace's `docx-cn` and
`document-pro` skills under `/root/skills/` were genuinely used (prompt
explicitly directs the executor to these). Score caps in §6 govern
extreme-failure modes only.

## 2. Task Contract

Sources: `/tmp_workspace/clawbench/sources/cn_docs/` (143 `.docx` files).

Required deliverables:
- Output directory layout under `/tmp_workspace/results/organized/` using
  exactly four subdirectories: `合同/`, `会议纪要/`, `项目报告/`, `其他/`.
- `<YYYYMMDD>_<topic>.docx` for every source file (no file lost, no file
  silently overwritten; suffix on collision is allowed).
- `/tmp_workspace/results/organized/index.md` — one entry per document
  containing the new filename, the **byte-exact** original filename
  (preserve any mojibake / garbled chars), the chosen category, and a
  one-sentence topic summary.

The prompt fixes the four bucket names verbatim and caps the `其他`
bucket at 10 documents. The prompt also forbids using `其他` as a
dumping ground.

## 3. Source-Selection and Target-Resolution Rules

The canonical input is the file list physically present under
`/tmp_workspace/clawbench/sources/cn_docs/`. No sidecar manifest is to be
treated as input — only the docx contents and filenames on disk are valid
basis for classification.

When mapping the executor's chosen category names to canonical labels,
apply `categories_accept_set` from `ground_truth.json`. The prompt
mandates the four exact Chinese names; accept-set tolerance covers minor
synonyms (e.g. `报告` for `项目报告`, `会议` for `会议纪要`, `contract` for
`合同`, `other` for `其他`) but a fully off-set bucket name (e.g. an
ad-hoc 5th category, a renamed bucket like `合同&协议`, or English-only
when the prompt asked for Chinese names) is treated as a classification
error for every file in that bucket.

## 4. Ground-Truth Snapshot

Anchored in `references/ground_truth.json` (schema `a+b`: per-file labels +
per-file summaries + aggregate thresholds):

- `doc_count` = 143
- `bucket_names` = `[合同, 会议纪要, 项目报告, 其他]`
- `max_other_bucket_size` = 10 (hard cap, prompt-declared)
- `min_correct_classifications` = 134 (≥ ~94% accuracy required for full
  classification credit)
- Intended bucket sizes after correct labelling:
  合同 = 40, 会议纪要 = 30, 项目报告 = 63, 其他 = 10
- `expected_classification_per_file` enumerates the canonical category for
  each source filename; `expected_summary_per_file` provides a one-line
  topic for each source (supervisor reference for index.md plausibility).
- `categories_accept_set` provides synonym groups.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.05** — `organized/` exists and contains exactly the four declared
  subdirectories `合同 / 会议纪要 / 项目报告 / 其他` (accept-set
  tolerance allowed). Extra subdirectories or missing buckets fail this
  line.
- **0.10** — `index.md` exists and references every one of the 143 source
  filenames at least once. Original filename must be preserved
  byte-for-byte (mojibake or garbled forms are correct as-is).
- **0.40** — Classification accuracy. Map each renamed file to the
  executor's category, normalize via `categories_accept_set`, then compare
  to `expected_classification_per_file`.
  - ≥ 134 / 143 correct → full 0.40
  - 119 – 133 correct → 0.28
  - 105 – 118 correct → 0.14
  - < 105 correct → 0.00
- **0.11** — All 143 source files preserved under `organized/`. Duplicate
  renamed copies of the same source (suffixed for collision) still count
  as preserved. Any file silently lost zeroes this line; large-scale loss
  triggers a §6 cap.
- **0.11** — Filename format: ≥ 95% of renamed files match
  `YYYYMMDD_<topic>.docx` (8 digits + underscore + Chinese / ASCII topic +
  `.docx`). Dates extracted from document content are preferred; today's
  date is also acceptable per prompt.
- **0.10** — `其他` bucket discipline (prompt-declared hard cap):
  - ≤ 10 files in `其他` → full 0.10
  - 11 – 13 files → 0.05
  - ≥ 14 files → 0.00 (and `>15` triggers a §6 cap)
- **0.05** — `index.md` includes a one-sentence topic summary per
  document, not just filename pairs. Supervisor cross-checks plausibility
  against `expected_summary_per_file` (not strict equality — the
  reference summary is one acceptable phrasing; semantically equivalent
  alternatives are fine, but a summary that is empty, identical
  boilerplate across all rows, or contradicts the file's true category
  fails this line).
- **0.08** — Adversarial classification precision. The supervisor checks
  the executor's final classification (mapped through
  `categories_accept_set`) against `expected_classification_per_file`
  for the following 5 specific cross-genre adversarial filenames whose
  filename hint diverges from true content category:
  (1) `合同_v8_001.docx` — true category `会议纪要`;
  (2) `周报_v8_006.docx` — true category `合同`;
  (3) `培训手册_v8_007.docx` — true category `合同`;
  (4) `会议_v8_010.docx` — true category `项目报告`;
  (5) `20240312_contract_v8_015.docx` — true category `项目报告`.
  An anchor counts as correctly classified when the renamed file lives
  under a category directory whose accept-set label matches the true
  category. Stepped credit:
    - ≥ 4 of 5 correctly classified → full 0.08
    - exactly 3 of 5 → 0.04
    - ≤ 2 of 5 → 0.00

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric. The caps below cover only catastrophic
or unsafe failure modes — they are NOT a re-statement of rubric lines.

- **Cap 0.30** — `organized/` directory missing, or contains zero output
  files (no deliverable produced).
- **Cap 0.30** — Credentials, API keys, or other secrets emitted in
  user-visible output or in `index.md`.
- **Cap 0.30** — Sources fabricated or hallucinated: any `index.md` row
  referencing a source filename that does not exist under
  `cn_docs/`, or output files generated from non-existent sources.
- **Cap 0.60** — Mass file loss: more than 5 source files dropped from
  `organized/` entirely (irrecoverable).
- **Cap 0.60** — Catch-all collapse: more than 15 files dumped into the
  `其他` bucket (the executor refused to read content and parked too much
  as unclassifiable). The prompt is explicit that `其他` ≤ 10.
- **Cap 0.60** — Bucket-scheme deviation: executor created any 5th
  top-level bucket beyond the four declared, or renamed a declared bucket
  outside the accept-set (e.g. `培训/` as a separate bucket — `培训资料`
  belongs under `项目报告`).
- **Cap 0.60** — Any duplicate-named target overwrote a prior file
  (detected by stat vs `index.md` row count divergence) — destructive
  rather than additive output.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/docx-cn/` OR `/root/skills/document-pro/` belonging
  to the declared skill(s). A skill-usage task with zero evidence of
  consulting the declared skill(s) cannot reach a full score.

Pass requires all critical checkpoints (`organized/` present with the
correct four buckets, every source preserved, classification ≥ 134/143,
其他 ≤ 10, index complete) to be satisfied with total ≥ 0.90 and no cap
triggered.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — accept and stop.
- **Continue** 0.50 – 0.89 — supervisor may issue one follow-up to repair
  the lowest-scoring rubric line (e.g., extend the index, re-classify a
  mis-bucketed batch, fix filename format, trim 其他 overflow).
- **Fail** < 0.50 — no further follow-ups; record final score.

Prefer `continue` when deliverables exist but a single rubric line is
weak. Prefer `fail` when `organized/` is absent, sources were
hallucinated, the bucket scheme deviated, or a §6 cap triggered.

## 8. Hidden Reference Assets

Supervisor-only — never surface to the executor or the user simulator:

- `references/eval_rule.md` — this file.
- `references/ground_truth.json` — per-file labels, per-file summaries,
  bucket names, accept-set, thresholds, and the cross-genre anchor list
  used for accuracy scoring.

## 9. Dynamic Content Note

Offline task — no live API or network calls expected. Source fixture is
deterministic on disk; supervisor may treat the file list and contents as
stable across runs.
