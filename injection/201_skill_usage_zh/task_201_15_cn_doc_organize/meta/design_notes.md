# Design notes — task_101_15_cn_doc_organize

Archived design intent. NOT injected into runs. Supervisors do not need to read this to grade.

## Adversarial subset background

The 150-doc fixture comprises 120 "clean" documents whose surface features
(filename hints, leading keywords) align with their primary intent, plus 30
cross-genre documents whose surface features point to one category but
whose **primary intent** belongs to a different one. Examples:
- A contract-review meeting produces meeting minutes → category is
  `meeting`, not `contract`.
- A post-training effectiveness report is a `report`, not `training`.
- A filename like `20240825_contract_122.docx` whose body is meeting
  minutes → category is `meeting`.

The 140/150 (≥93.3%) accuracy band for full credit was chosen so that
classifying purely on filename or first-line keywords cannot saturate the
score; the executor must actually open the document body. The 30-doc
cross-genre subset is enumerated in `ground_truth.json :: adversarial_subset`.

## Filename-corruption fixture detail

A subset of source filenames are intentionally mojibake / garbled
(e.g. `Â¡Â¡_009.docx`, `ç³ç³»_003.docx`, `~$doc_*.docx`). The prompt
explicitly requires the executor to record the source filename
**byte-for-byte** in `index.md` without normalization or transliteration —
this exercises both the docx skill and faithful round-trip handling.

## Score-cap rationale

Caps are reserved for catastrophic deviations (no deliverables, credentials
leaked, fabricated sources, mass file loss). Skill-trace evidence is
captured by checkpoints, not caps, because partial skill use is still
useful work.

## v8 hardening (2026-04-29 round 1)

The v8 hardening pass added 18 NEW `.docx` files into `sources/cn_docs/` next
to the existing 150 originals. The generated fixture files are committed; the
private generator is not part of the public benchmark runtime.

Intent: push cross-genre pressure further. Each new file's filename hints
at category A while the body content is unambiguously category B. A model
that classifies on filename or first-line keywords alone will systematically
miss all 18.

| New filename                        | Filename hint | True content |
|-------------------------------------|---------------|--------------|
| 合同_v8_001.docx                    | contract      | meeting      |
| 合同_v8_002.docx                    | contract      | meeting      |
| 合同_v8_003.docx                    | contract      | training     |
| 周报_v8_004.docx                    | report        | training     |
| 周报_v8_005.docx                    | report        | training     |
| 周报_v8_006.docx                    | report        | contract     |
| 培训手册_v8_007.docx                | training      | contract     |
| 培训手册_v8_008.docx                | training      | contract     |
| 培训手册_v8_009.docx                | training      | meeting      |
| 会议_v8_010.docx                    | meeting       | report       |
| 会议_v8_011.docx                    | meeting       | report       |
| 会议_v8_012.docx                    | meeting       | other (memo) |
| 备忘_v8_013.docx                    | other (memo)  | contract     |
| 备忘_v8_014.docx                    | other (memo)  | meeting      |
| 20240312_contract_v8_015.docx       | contract      | report       |
| 20240518_training_v8_016.docx       | training      | meeting      |
| 20240725_meeting_v8_017.docx        | meeting       | training     |
| 20241108_report_v8_018.docx         | report        | contract     |

GT updates:
- `doc_count` 150 → 168
- `category_counts_expected`: contract 30→35, meeting 26→31, report 37→40,
  training 21→25, other 36→37 (sum 168)
- `min_correct_classifications` 140 → 158 (≈ 94% accuracy band)
- `correct_bands` rescaled to [158,168] / [140,157] / [123,139] / [0,122]
- `per_file_labels` extended with all 18 new filenames mapped to true
  content category
- `adversarial_subset` extended (30 → 48 entries)

eval_rule.md updates: numerical references throughout (150 → 168, 140 → 158,
band edges) restated. Cap thresholds and rubric weights unchanged; total
still 1.00.

Prompt change: "about 150" → "around 170" so the user request reflects
fixture size without revealing the exact count.

Skill-cap and skill_fork manifests left unchanged.

## v8 hardening round 5 (2026-04-29)

Round-1 v8 expansion (150 → 168 docs with 18 cross-genre adversarials)
was insufficient on its own — opus-class executors hit cap 0.95 by
classifying the bulk of docs correctly while scattering errors across
the adversarial subset. This round adds a second §5 anchor "Adversarial
classification precision" at weight 0.08 that requires the executor's
final per-file classification (mapped through `categories_accept_set`)
to match `per_file_labels` for ≥4 of 5 specific cross-genre adversarial
files: `合同_v8_001.docx` (true: meeting), `周报_v8_006.docx` (true:
contract), `培训手册_v8_007.docx` (true: contract), `会议_v8_010.docx`
(true: report), `20240312_contract_v8_015.docx` (true: report). Stepped
credit: ≥4/5 → 0.08, exactly 3/5 → 0.04, ≤2/5 → 0.00. To rebalance to
1.00, the two heaviest non-cap-anchor checkpoints lose 0.04 each: file
preservation 0.15 → 0.11 (-0.04) and filename format 0.15 → 0.11 (-0.04).
The 0.40 classification-accuracy line (band-graded) is kept intact as
the broad-coverage signal; the new anchor adds local precision pressure
on the most surface-feature-vs-content adversarial cases. Score caps
and success_threshold unchanged. Final weights: 0.05 + 0.10 + 0.40 +
0.11 + 0.11 + 0.10 + 0.05 + 0.08 = 1.00.

## v8 hardening round 7 (2026-04-30) — `~$` lock-file fix

Removed 8 MS Word lock files (`~$doc_186/271/280/355/382/456/569/798.docx`) from `sources/cn_docs/`. They were `~$`-prefixed Word auto-generated lock files that any production document-organization workflow would correctly skip — but the prior eval treated them as canonical input, so the executor's correct exclusion was being penalized as a 8-file accuracy gap.

Updated:
- `doc_count` 168 → 160
- `category_counts_expected`: contract 35→34, meeting 31→29, report 40→39, training 25→24, other 37→34 (sum 160)
- `min_correct_classifications` 158 → 150 (~94% accuracy preserved)
- `correct_bands` rescaled to [150,160] / [133,149] / [117,132] / [0,116]
- eval_rule.md numerical references updated (168→160, 158→150, etc.)
- `per_file_labels` — 8 `~$`-prefix entries removed

## Review pass (2026-04-30) — v9 fixed bucket scheme + 其他 ≤10 cap

User review feedback for Task 15 required four substantive changes:

1. **Removed the "原生 shell 工具会被 CJK 内容和大批量重命名搞死" hint from the prompt.** That sentence telegraphed the actual checkpoint to the executor. The skill mention now reads naturally as "请你用 docx-cn 和 document-pro 这两个 skill 来读文档内容" in the first paragraph.

2. **Switched from open-choice 3–6 buckets to four FIXED buckets**: `合同 / 会议纪要 / 项目报告 / 其他`. Prompt directs the executor to use these exact Chinese directory names verbatim. Eval §6 adds a 0.60 cap for "bucket-scheme deviation" (5th bucket or off-set rename). categories_accept_set still permits limited synonym tolerance (e.g. `report` for `项目报告`) but the prompt is unambiguous about the canonical names.

3. **Hard cap on `其他` bucket at 10 documents.** Prompt declares the cap explicitly. §5 line 6 now grades `其他` size: ≤10 → 0.10, 11–13 → 0.05, ≥14 → 0.00. §6 escalates `>15` to a 0.60 cap. To make the cap enforceable on the existing fixture (which had 27 candidate `其他` docs), removed 17 generic personal-scratch docx files from sources, leaving exactly 10 truly-no-topic personal notes (one of each template family: 个人便签 / 读书笔记 / 日记片段 / 草稿 / 杂项记录 / 想法汇总 / 灵感笔记 / 碎片整理 / 临时记录 / 随手备忘). doc_count 160 → 143.

4. **Per-file GT now includes both expected classification and expected one-sentence summary.** Renamed `per_file_labels` → `expected_classification_per_file` (semantics unchanged) and added `expected_summary_per_file` mapping every source filename to a topical one-line summary derived from document content. Supervisor uses this to plausibility-check the executor's `index.md` summaries — strict equality is not required (multiple phrasings acceptable), but empty / boilerplate / contradictory summaries fail §5 line 7.

### Bucket merge rationale

Old 5-category scheme (`contract / meeting / report / training / other`) collapses to 4 by folding `training` into `项目报告`. Training materials (员工培训资料, 培训效果评估报告, 合规培训案例) are formal corporate knowledge artifacts that share document-form characteristics with reports — both are structured produced documents (vs scratch notes in `其他`). All 24 ex-training files therefore land under `项目报告`. Topical contract-related memos (`关于X合同的工作随笔`) re-label as `合同` since they ARE working contract documents. Cross-department memo (`跨部门协作随笔备忘`) re-labels as `会议纪要` (cross-dep coordination is meeting-adjacent).

### Final distribution
- 合同: 40
- 会议纪要: 30
- 项目报告: 63
- 其他: 10
- Total: 143

### Adversarial anchors (5-file precision check) re-mapped
All 5 anchor files remain cross-genre under the new 4-bucket scheme:
- 合同_v8_001: filename hint 合同, true 会议纪要
- 周报_v8_006: filename hint 项目报告, true 合同
- 培训手册_v8_007: filename hint 项目报告 (培训→报告), true 合同
- 会议_v8_010: filename hint 会议纪要, true 项目报告
- 20240312_contract_v8_015: filename hint 合同, true 项目报告

### Threshold rescaling
- min_correct_classifications: 150 → 134 (~94% of 143)
- correct_bands: [134,143] / [119,133] / [105,118] / [0,104]
- success_threshold and §6 caps unchanged
- §5 weights unchanged: 0.05 + 0.10 + 0.40 + 0.11 + 0.11 + 0.10 + 0.05 + 0.08 = 1.00

### Files changed
- `tasks/101_skill_usage/task_101_15_cn_doc_organize.yaml` — Chinese natural-language prompt, skill mention in §1, no parens, no shell-tool hint, fixed 4-bucket spec, 其他 ≤10 cap declared
- `references/eval_rule.md` — full rewrite for 4-bucket scheme, doc_count 160→143, new bucket-scheme cap, 其他 cap line, per-file summary plausibility check
- `references/ground_truth.json` — schema fields renamed to expected_classification_per_file / expected_summary_per_file; bucket_names / max_other_bucket_size / main_buckets fields added; counts and bands rescaled
- `sources/cn_docs/` — 17 generic personal-scratch docx files deleted (160 → 143)
