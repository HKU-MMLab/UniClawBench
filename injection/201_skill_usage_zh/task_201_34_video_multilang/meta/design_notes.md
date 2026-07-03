# Design notes — task_101_34_video_multilang

Internal-only archive of construction notes that must NOT appear in the
hidden eval_rule. The supervisor never reads this file; it exists to
preserve provenance for benchmark maintainers.

## Skill-usage anchors (historical)

Earlier revisions of `references/eval_rule.md` carried score caps that
fired whenever the trace showed no read of `SKILL.md` (or any file)
under one of the four declared helper directories:

- `/root/skills/ffmpeg-video-editor/`
- `/root/skills/openai-whisper-api/`
- `/root/skills/translate/`
- `/root/skills/markdown-formatter/`

Each missing-skill cap was set at 0.89. They were removed from the live
eval_rule because:

1. They duplicated what the rubric already measures — a faithful Chinese
   SRT + timestamped MD with glossary fidelity is essentially impossible
   to produce without exercising at least one transcription/translation
   helper, so the deliverable-quality rubric already discriminates.
2. Per the project caps policy, score caps should target extreme failure
   modes (no deliverables, credential leakage, total fabrication), not
   restate per-skill checkpoints.

If a future revision wants to reinstate per-skill auditing, prefer adding
a low-weight rubric line ("trace shows consultation of at least one
declared helper") over a hard cap.

## Rubric weights (current)

| Weight | Checkpoint                              |
|--------|-----------------------------------------|
| 0.15   | Valid SRT structure                     |
| 0.20   | Timestamp-segmented MD (≥3 segments)    |
| 0.20   | Glossary fidelity (100% hit rate)       |
| 0.20   | Concept coverage (≥5 ordered anchors)   |
| 0.10   | Chinese-language output (≥60% CJK)      |
| 0.10   | First SRT cue at ≤ 00:00:05             |
| 0.05   | Concept-order strict precision (≥8/9 in canonical order) |
| **1.00** | **Total**                             |

## v8 hardening round 9 (2026-04-30)

Round-8 measurements showed this task at PASS = 1.0. Round 9 adds a
small auxiliary CP "Concept-order strict precision" at weight 0.05.
The 9 ML concepts must appear in `talk.zh.md` in canonical order
(transformer architecture → NLP → self-attention → positional encoding
→ multi-head attention → LLMs → next-token prediction → fine-tuning →
scaling laws); ≥8 of 9 concepts must be in correct relative order
(no inversions). Stepped: 9/9 → 0.05, 8/9 → 0.025, ≤7/9 → 0.00.
Rebalance: SRT structure 0.20 → 0.15 (-0.05) funds the new line.
Final §5 sum: 0.15+0.20+0.20+0.20+0.10+0.10+0.05 = 1.00. GT gains
`concept_order_strict_required`, `min_concepts_in_canonical_order: 8`,
and `expected_concept_order` (9 entries). Score caps and
success_threshold unchanged.

## Score caps (current)

All caps ≤ 0.30 and target special edge cases:

- 0.30 — no deliverables produced
- 0.30 — credential leakage in user-visible output
- 0.30 — fabricated transcript bearing no faithful relation to the audio

## Review pass (2026-04-30)

Per review_record.md task 34: existing checks were essentially format-only
(SRT structure, MD segment count, glossary fidelity, generic concept
coverage). User asked for specific timeline checks and specific Chinese
content checks. Changes:

### YAML prompt
- Rewritten in English (was already English; tightened phrasing).
- First paragraph names all four declared skills (openai-whisper-api,
  ffmpeg-video-editor, translate, markdown-formatter) inline as the
  natural way to do the job.
- No brackets anywhere in the prompt body.
- Adds language about timestamps lining up with where each idea is
  actually spoken, and about the canonical Chinese rendering being used
  every single time — which is what the new strict checkpoints grade.

### eval_rule.md §5 (rebalanced)
Old §5 had: 0.15 SRT + 0.20 MD segments + 0.20 glossary fidelity + 0.20
concept coverage + 0.10 Chinese-language + 0.10 early cue + 0.05 concept
order = 1.00. The two 0.20 lines (glossary fidelity and concept coverage)
were format/lookup-only — they didn't actually verify *where* in the
timeline each concept landed.

New §5:
- 0.15 — Valid SRT structure (unchanged).
- 0.20 — Timestamp-segmented MD ≥3 segments (unchanged).
- 0.20 — **NEW Concept timeline anchors STRICT.** Each of 9 concepts
  must appear in an SRT cue whose start time is within ±15s of the
  expected GT window. 9/9 → 0.20; 8/9 → 0.10; ≤7/9 → 0.00. Replaces
  the old vague "concept coverage" line.
- 0.20 — **NEW Chinese term translation STRICT.** All-or-nothing per
  term, across BOTH SRT and MD. 10/10 → 0.20; 9/10 → 0.15; 8/10 →
  0.10; ≤7/10 → 0.00. Replaces the old "glossary fidelity" line but
  graded strictly per occurrence.
- 0.10 — Chinese-language ≥60% CJK (unchanged).
- 0.10 — Early first cue ≤00:00:05 (unchanged).
- 0.05 — Concept order strict precision (unchanged).

Sum: 0.15 + 0.20 + 0.20 + 0.20 + 0.10 + 0.10 + 0.05 = 1.00. Verified.

### ground_truth.json additions
- `expected_concept_timestamps_seconds`: {concept → [start_s, end_s]}
  for all 9 concepts, distributed across the ~60-second clip in
  canonical order with ~10s windows that overlap modestly to absorb
  natural conversational drift.
- `concept_timestamp_tolerance_seconds: 15` — ±15s tolerance per
  concept around the expected window's start.
- `expected_chinese_translations`: full mirror of cn_terms.json with
  all 10 entries; pinned as canonical for the strict per-term check.
- `chinese_translation_strict_per_term: true` and
  `chinese_translation_term_count: 10` for grader reference.
- `concept_timeline_partial_credit` step table for the 0.20 timeline CP.

### Notes on robustness
The timeline GT is calibrated to the actual CC0/CC-BY clip used
(~60s English ML talk). The ±15s tolerance is generous enough that
near-canonical Whisper transcriptions of the real audio land within
window without coaching, but tight enough that a fabricated transcript
or one based on a different video cannot satisfy 9/9. The strict
per-term Chinese check stops the executor from passing with a paraphrase
or a competing variant ("注意力机制" instead of "自注意力", "微调训练"
instead of "微调", or leaving English terms untranslated).

### Score caps
Cap text tightened to make the "Fabricated transcript" cap concrete:
fewer than 3 of 9 ordered concepts present in their accepted Chinese
renderings is now an explicit trigger. Cap values unchanged at 0.30.

success_threshold unchanged at 0.90.
