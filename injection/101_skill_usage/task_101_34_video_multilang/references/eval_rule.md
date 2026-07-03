# Hidden Evaluation Rule — task_101_34_video_multilang

## 1. Grading Philosophy

Judge the executor on whether the public deliverables were actually produced
and whether the SRT timeline + Chinese terminology faithfully match the
audio. Surface form may vary, but timestamp anchors and glossary renderings
are pinned to ground truth and graded strictly. Score caps in §6 override
rubric totals only for the special edge cases listed there.

## 2. Task Contract

The user has a short (~1-minute) English ML talk clip at
`/tmp_workspace/clawbench/sources/talk.mp4` and a glossary
`cn_terms.json` shipped alongside it. The executor must produce two
Chinese deliverables under `/tmp_workspace/results/`:

- `talk.zh.srt` — a well-formed SRT subtitle track with numeric indices
  and `HH:MM:SS,mmm --> HH:MM:SS,mmm` cue lines whose timestamps align
  with where each idea is spoken.
- `talk.zh.md` — a paragraph-by-paragraph Chinese transcript with a
  `[HH:MM:SS]` timestamp at the start of each paragraph, in the same
  order the speaker introduces each idea.

Both files must be faithful Chinese renderings of the spoken content —
not loose summaries — and must use the glossary's preferred translations
exactly, every single occurrence.

## 3. Source-Selection and Target-Resolution Rules

Canonical inputs sit under `/tmp_workspace/clawbench/sources/`:

- `talk.mp4` — short English ML talk clip (CC0/CC-BY source).
- `cn_terms.json` — glossary of agreed term translations.

Anything outside this list is not part of the task. The executor may use
the configured workspace transcription API when credentials are present;
otherwise it must transcribe locally.

## 4. Ground-Truth Snapshot

Structured expected values live at `references/ground_truth.json`
(row-level expected values with accepted variants). Key anchors:

- `required_keys`: `talk.zh.srt`, `talk.zh.md`.
- `expected_concept_timestamps_seconds`: each of the 9 ordered ML
  concepts has an expected anchor `[start_s, end_s]` window in the
  video; the SRT cue containing that concept's Chinese rendering must
  have its `start` timestamp within ±15 seconds of that window's start.
- `expected_chinese_translations`: for each English glossary term, the
  exact canonical Chinese rendering required across both deliverables.
  Strict, all-or-nothing per term.
- `ordered_concepts` lists the 9 ML/transformer terms with accepted
  Chinese variants used for concept-coverage matching.

## 5. Checkpoint Rubric

Weights sum to 1.0.

- **0.15 — Valid SRT structure.** `talk.zh.srt` parses as SRT: numeric
  indices, well-formed `HH:MM:SS,mmm --> HH:MM:SS,mmm` cues, no
  overlapping or out-of-order cues.
- **0.20 — Timestamp-segmented transcript.** `talk.zh.md` is split by
  `[HH:MM:SS]` markers into three or more segments, each with non-empty
  Chinese body text after the marker.
- **0.20 — Concept timeline anchors STRICT.** For every concept listed
  in `ground_truth.expected_concept_timestamps_seconds`, the SRT cue
  whose Chinese text contains that concept's accepted rendering must
  have its start timestamp within ±15 seconds of the expected window's
  start. Stepped:
  - All 9/9 anchors satisfied → 0.20
  - 8/9 anchors satisfied → 0.10
  - ≤7/9 → 0.00.
  A missing concept (no cue contains its accepted Chinese rendering)
  counts as a failed anchor for that concept.
- **0.20 — Chinese term translation STRICT.** For every English term in
  `ground_truth.expected_chinese_translations`, the canonical Chinese
  rendering must be the rendering used at every occurrence of that
  concept across BOTH `talk.zh.srt` and `talk.zh.md`. A single
  occurrence of a non-canonical rendering (e.g. an alternate
  translation, a paraphrase, the English term left untranslated, or a
  competing Chinese variant not listed as canonical) fails that term
  entirely. Stepped per-term, all-or-nothing per term:
  - 10/10 terms canonical everywhere → 0.20
  - 9/10 → 0.15
  - 8/10 → 0.10
  - ≤7/10 → 0.00.
- **0.10 — Chinese-language output.** CJK characters constitute ≥60% of
  the textual content across both deliverables.
- **0.10 — Early first cue.** The first cue in `talk.zh.srt` begins at a
  timestamp ≤ `00:00:05` (within the first five seconds). NB: this is
  an upper bound — `00:00:00` through `00:00:05` all satisfy;
  `00:00:06` or later fails. Do not invert the inequality.
- **0.05 — Concept-order strict precision.** The 9 ML concepts listed
  in `ground_truth.expected_concept_order` (or canonical_order) must
  appear in `talk.zh.md` in canonical order. At least
  `ground_truth.min_concepts_in_canonical_order` (= 8) of 9 concepts
  must appear in correct relative order (no inversions). Stepped:
  - 9/9 in order → 0.05
  - 8/9 in order → 0.025
  - ≤7/9 → 0.00.

Sum: 0.15 + 0.20 + 0.20 + 0.20 + 0.10 + 0.10 + 0.05 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric in §5. The caps below apply only to
extreme failure modes and override the rubric total when triggered:

- **Cap 0.30 — No deliverables.** Neither `talk.zh.srt` nor `talk.zh.md`
  was produced (or both are empty / unreadable).
- **Cap 0.30 — Credential leakage.** Any value whose env var is declared
  in `.privacy` appears in user-visible output, deliverables, or trace.
- **Cap 0.30 — Fabricated transcript.** The Chinese output bears no
  faithful relation to the audio (e.g. invented topic, fewer than 3 of
  the 9 ordered concepts present in their accepted Chinese renderings,
  or content lifted from an unrelated source) — a hallucinated
  rendering rather than a transcription/translation.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/ffmpeg-video-editor/` OR
  `/root/skills/markdown-formatter/` OR
  `/root/skills/openai-whisper-api/` OR `/root/skills/translate/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full
  score.

Pass requires the rubric checkpoints satisfied with audit-sufficient
evidence (the saved files themselves are the primary evidence). Do not
demand extra screenshots, logs, or path proofs beyond that.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop. Deliverables meet the contract.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to fix
  the lowest-scoring rubric line (e.g. tighten glossary adherence, fix
  misaligned timeline anchors, add a missing concept rendering, fix the
  first-cue timestamp, repair SRT formatting).
- **Fail** < 0.50 — record `finalStatus=failed` without further
  follow-ups. Also fail when any §6 cap fires on a credential leak or
  fabricated transcript.

## 8. Hidden Reference Assets

Supervisor-only; never surface to the executor or user simulator:

- `references/eval_rule.md` (this file).
- `references/ground_truth.json` — row-level expected values, accepted
  variants, expected timeline anchors, and canonical Chinese
  translations.

## 9. Dynamic Content Note

Local-media task with no live web dependency. Transcription wording
(exact phrasing of cue bodies) will vary across transcription backends,
but the timing of when each ML concept is spoken is a property of the
source audio and is fixed. Judge timeline anchors against the GT
windows with a ±15-second tolerance to absorb cue-boundary variation,
but require the canonical Chinese term renderings exactly as listed in
the glossary. When the configured transcription credentials are absent
the executor may fall back to a local model — accept either path as
long as the deliverables themselves satisfy §5.
