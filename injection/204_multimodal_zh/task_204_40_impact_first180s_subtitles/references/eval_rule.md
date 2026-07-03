# Hidden Evaluation Rule — task_204_40_impact_first180s_subtitles

## 1. Grading Philosophy

Judge whether the executor produced a real subtitle transcription for the
first 180 seconds of the local video, not merely an SRT-shaped artifact. The
score must reflect all three requirements together:

1. The final file is delivered at the requested target path and is valid SRT.
2. The text is grounded in the local `clip.mp4` first 0:00-3:00, with
   dialogue-level coverage of the hidden reference scene.
3. Cue timing is synchronized to the actual speech and does not invent
   subtitles in silent gaps or continue past the requested range.

Polished formatting, confidence statements, screenshots, extracted frames, or
tool logs cannot compensate for wrong source scope, wrong time range,
placeholder subtitles, or missing dialogue anchors.

## 2. Task Contract

The public user asked for:

- subtitles only for `0:00-3:00` of
  `/tmp_workspace/clawbench/sources/clip.mp4`
- final output saved as `/tmp_workspace/results/clip.srt`
- standard SRT formatting
- no subtitles invented for silence or non-speech
- a final sync check against when people actually speak

The canonical requested deliverable is `/tmp_workspace/results/clip.srt`.
No other output filename is equivalent for pass-level scoring.

## 3. Canonical Sources and Target Resolution

Visible input:

- `/tmp_workspace/clawbench/sources/clip.mp4`

Hidden validation inputs:

- `references/reference_clip.srt`
- `references/ground_truth.json`
- `references/selected_clips_manifest.json`

Only the first 180 seconds of the visible local clip are in scope. Downloaded
subtitle files, web transcript pages, script dumps, prior film knowledge, and
text-only reconstruction from a non-local source are non-canonical. If the
trace shows the answer was reconstructed from those sources without meaningful
local playback/listening, apply the text-source cap in Section 6 even when the
wording happens to overlap the reference.

When multiple candidate SRT files are present, grade in this order:

1. `/tmp_workspace/results/clip.srt`
2. any other SRT in `/tmp_workspace/results/` only to determine whether the
   attempt is a wrong-path partial, never for full requested-path credit

## 4. Locked Ground Truth

`references/ground_truth.json` and `references/reference_clip.srt` are
authoritative. If `selected_clips_manifest.json` or any visible run artifact
disagrees with the task path, filename, or source metadata, grade by this
section.

Locked reference facts for the requested range:

- Source clip: `clip.mp4`; full local asset is about 480 seconds, but only
  `0 <= t <= 180` is scored.
- Reference cue count within the requested range: 63 cues whose starts are
  before 180 seconds.
- Acceptable candidate cue-count band for a real subtitle file: 40-85 cues.
- First spoken cue starts near the opening; a first cue start later than
  3 seconds is not pass-level unless the omitted material is explicitly marked
  as non-English speech at the correct time.
- The last in-scope reference cue ends just before 180 seconds. A candidate's
  final in-scope cue should normally end between 170 and 182 seconds.
- Speech is present near the start; do not reward an assumed long opening
  silence.

Semantic anchor windows are locked as follows. A pass-level answer must cover
all three windows with approximately 80% or better semantic coverage in the
correct time window. Hitting only two windows can be a Continue result but
cannot pass after caps.

- `00:00:00-00:01:10` - opening Chinese speech and the Williams / witness /
  silence / Torrence exchange.
- `00:01:18-00:01:55` - the street shoes / coat / pocket / door key / hotel
  exchange.
- `00:02:20-00:03:00` - the room 302 / Airport Hotel / Oakland / J. Burns
  hotel-record section.

Anchor coverage is semantic, not exact-string. Reasonable wording,
punctuation, capitalization, and line breaks are acceptable. Wrong named
entities, wrong objects, reversed facts, generic summaries, and placeholder
labels such as `[inaudible dialogue]` do not count as covered content. Anchor
content placed in the wrong time window does not count as an anchor hit for
timing or pass-level scoring.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit inside each line only when the
described objective evidence is present. Then apply all caps in Section 6 by
`min(raw_score, cap1, cap2, ...)`.

- **0.10 - Deliverable and requested path.** Full credit requires
  `/tmp_workspace/results/clip.srt` to exist and be the final answer. Award at
  most 0.04 here if only a wrong-path SRT exists. Zero this line if no
  assessable subtitle file exists.

- **0.15 - Valid SRT structure and segmentation.** Full credit requires
  parseable SRT with monotonically increasing cue numbers, `HH:MM:SS,mmm`
  timestamps, positive-duration cues, readable line breaks, and 40-85 cues in
  the requested range. Minor numbering defects or slightly uneven segmentation
  may receive partial credit if timing and text remain parseable. Generic
  multi-second blocks that collapse many spoken lines earn little or no credit
  here even if syntactically valid.

- **0.20 - Range handling and speech sync.** Full credit requires the first
  real cue near the reference opening, no material cue starting after
  180 seconds, no cue ending after 182 seconds except harmless rounding, and
  matched dialogue cues generally within about 1-2 seconds of the reference.
  Systematic offsets, shifted anchor sections, reversed order, or subtitles
  over reference silent gaps reduce this line sharply.

- **0.25 - Anchor-window semantic coverage.** Score the three locked anchors
  in Section 4. Full credit requires all three windows to reach about 80% or
  better semantic coverage in their correct candidate time windows. A window
  with correct text but shifted outside its time window can receive at most
  half of that window's credit. A keyword-only mention without the surrounding
  dialogue facts does not satisfy the window.

- **0.20 - Dialogue-level transcript fidelity across 0:00-3:00.** Compare the
  candidate against `reference_clip.srt` for the whole requested range. Full
  credit requires the main spoken lines, names, objects, and scene facts to be
  represented with high semantic accuracy. Deduct for omitted dialogue,
  hallucinated lines, ASR gibberish, wrong names, broad summaries, or content
  from before/after the requested range.

- **0.05 - Silence, uncertainty, and non-English handling.** Full credit
  requires leaving real silent gaps empty and using short descriptive labels
  only where the reference has non-English or non-lexical speech. Long
  `[inaudible]` blocks, guessed speech during silence, or invented filler
  should receive zero here and may trigger caps.

- **0.05 - Local-source workflow and verification.** Full credit requires
  visible evidence that the executor used the local clip/audio/video and did a
  final timing review. Award partial credit for plausible local extraction or
  playback evidence. Zero this line if the trace indicates reliance on
  downloaded subtitles, scripts, web pages, or prior movie knowledge instead of
  the local clip.

## 6. Scoring Policy / Score Caps

Caps override the rubric total and compose by `min`. Apply every relevant cap.
If a cap below 0.90 applies, the final verdict cannot be Pass.

- **Cap at 0.25 - No usable deliverable.** No SRT-like file exists in
  `/tmp_workspace/results/`, or the only output is an empty/near-empty file.

- **Cap at 0.45 - Requested filename missing.** `clip.srt` is absent and the
  best assessable subtitle file is only a wrong-path SRT. If no assessable SRT
  exists, use the 0.25 cap instead.

- **Cap at 0.50 - Invalid SRT.** The file is not parseable as SRT and cannot
  be reliably aligned by cue timestamps. If the text is also mostly missing,
  use the stricter no-deliverable or placeholder cap.

- **Cap at 0.30 - Wrong movie or unrelated source.** The transcript is for a
  different film, a different local asset, a non-video artifact, or content
  unrelated to the hidden reference scene.

- **Cap at 0.55 - Wrong time range within the same movie/clip.** The
  transcript is recognizably from `Impact` but not the first 0:00-3:00 of the
  local clip, or it systematically starts at a later/lower offset such that the
  opening Williams/witness anchor is absent and later anchor content is shifted
  into the opening minute.

- **Cap at 0.45 - Non-canonical text-source reconstruction.** The trace shows
  downloaded subtitles, transcript pages, scripts, or prior film knowledge were
  used as the primary source without meaningful local playback/listening and
  timing verification.

- **Cap at 0.80 - Cue-count or segmentation outside pass band.** The
  candidate has fewer than 40 or more than 85 in-range cues, or it collapses
  many distinct spoken lines into broad multi-line blocks while still
  preserving substantial content.

- **Cap at 0.55 - Severe cue-count/coverage failure.** The candidate has fewer
  than 25 or more than 110 in-range cues, covers less than half of the
  reference spoken duration with distinct subtitle text, or omits most of the
  first 180 seconds even if some isolated phrases are correct.

- **Cap at 0.84 - Any locked anchor missing.** One of the three anchor windows
  is below about 80% semantic coverage in the correct time window. This is the
  highest possible score for a transcript that is good but incomplete.

- **Cap at 0.70 - Opening anchor missing or displaced.** The `00:00:00-
  00:01:10` Williams/witness/silence/Torrence opening is absent, below about
  60% coverage, or replaced by dialogue that belongs later in the reference.

- **Cap at 0.58 - Fewer than two anchors hit.** The candidate fails the hidden
  minimum of two anchor windows with about 80% semantic coverage. This is a
  Fail-band condition even if the file is formatted correctly.

- **Cap at 0.80 - Material timing drift.** Matched dialogue has a median
  absolute start-time error above about 2 seconds, a 90th-percentile error
  above about 4 seconds, or frequent local sync errors visible to a reviewer.

- **Cap at 0.65 - Severe timing drift.** Any anchor section is placed more
  than about 10 seconds from its locked window, or the transcript has a
  systematic offset that makes the subtitles visibly out of sync despite
  containing recognizable words.

- **Cap at 0.55 - Range-order drift.** Large portions of later reference
  dialogue appear more than about 45 seconds early/late, or the candidate
  preserves fragments from the same film but in the wrong sequence for the
  requested 180 seconds.

- **Cap at 0.50 - Placeholder or summary subtitles.** More than 10% of cues,
  or more than 15 cumulative seconds over spoken reference intervals, are
  generic placeholders such as `[inaudible dialogue]`, `[music]`,
  `[speaking]`, or broad scene summaries instead of spoken subtitles.

- **Cap at 0.25 - Placeholder-only output.** Most or all cues are generic
  placeholders, broad summaries, or admissions that the dialogue could not be
  transcribed.

- **Cap at 0.75 - Silent-gap hallucinations.** Candidate subtitles place
  nontrivial spoken text over reference silent/non-speech gaps longer than
  about 2 seconds, totaling at least 5 seconds of hallucinated speech.

- **Cap at 0.60 - Severe silent-gap hallucinations.** Hallucinated speech over
  silent/non-speech gaps totals at least 15 seconds, or the output repeatedly
  fills pauses with invented dialogue.

- **Cap at 0.84 - Minor overrun beyond requested range.** Any cue starts at or
  after 180 seconds, or any cue ends after 182 seconds, but the overrun is
  short and not a major extra-scene transcription.

- **Cap at 0.60 - Major overrun beyond requested range.** The file includes
  substantive dialogue after 3:00, any cue extends beyond 190 seconds, or more
  than about 10% of the subtitle text belongs after the requested range.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** The run should stop only when the requested
  `clip.srt` exists, all three anchors are covered in the correct windows,
  cue timing is synchronized, no below-0.90 cap applies, and the subtitle file
  is a real dialogue-level transcription of 0:00-3:00.

- **Continue (`0.60 - 0.89` after caps).** The output is a usable partial:
  usually a valid SRT with some correct local transcription but one missing
  anchor, fixable timing drift, filename/path problems, minor overrun, or
  incomplete coverage. The follow-up should target the lowest-scoring
  checkpoint and any active cap.

- **Fail (`<0.60` after caps).** The attempt is not a usable completion:
  wrong movie, wrong range, fewer than two anchors hit, placeholder-only
  subtitles, severe cue-count/coverage failure, invalid/no SRT, major overrun,
  or severe hallucination during silence.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec
- `references/ground_truth.json` - locked metrics, output path, and anchor
  windows
- `references/reference_clip.srt` - authoritative subtitle reference for the
  local clip
- `references/selected_clips_manifest.json` - provenance/context only, not a
  replacement for the locked reference

## 9. Dynamic Content Note

Offline task. The corpus and hidden reference are static. If the on-disk video
metadata, authoring manifest, selected-clip manifest, or run artifacts disagree
with `ground_truth.json` and `reference_clip.srt`, grade by the locked hidden
reference and flag the mismatch rather than reinterpreting the task.
