# Hidden Evaluation Rule — task_104_35_love_is_strange_lrc

## 1. Grading Philosophy

Grade the executor on whether it delivered a locally audio-grounded timed LRC,
not whether it recognized the song or reproduced a familiar lyric page. The
public task explicitly forbids using the filename, metadata, internet lyrics,
existing LRC/SRT files, or prior memory as the source of truth. Full-credit
answers must therefore satisfy both outcomes:

1. A valid LRC is saved in the requested results location and aligns to the
   shipped MP3's audible lyric timing.
2. The required review/revision file exists and gives concrete evidence of the
   requested second pass over the opening, middle repeated/dialogue region, and
   ending.

Accept small wording variants, spelling differences, and punctuation changes
when they preserve the same audible lyric and section role. Do not accept a
polished but wrong-version lyric, a copied web lyric with timestamps fitted to a
different recording, or a flattened monologue in place of the male/female
call-and-response structure.

## 2. Task Contract

The executor must work from the local audio under
`/tmp_workspace/clawbench/sources/`. In current runtime prompts the source and
outputs are:

- Input audio: `/tmp_workspace/clawbench/sources/song.mp3`
- Main output: `/tmp_workspace/results/song_generated.lrc`
- Review output: `/tmp_workspace/results/song_revision_log.md`

The authoring YAML/source manifest uses the same anonymous source and output
names. Legacy title-based aliases should be accepted only when the visible
runtime prompt used those names. Do not give duplicate credit for both naming
schemes.

The LRC must use standard `[mm:ss.xx]text` style timed lyric rows. Metadata tags
are optional and do not earn credit. Title/artist tags copied from metadata or
outside knowledge may support a source-grounding cap, especially when the lyric
timing also matches a different recording instead of the local file.

## 3. Locked Ground Truth

Canonical hidden references:

- `references/ground_truth.lrc`
- `references/ground_truth.srt`

The local MP3 duration is `174.288` seconds, approximately `02:54.3`. The
reference LRC/SRT contains 31 lyric rows, but rows beginning after the local
audio end are reference-continuation rows only. For this local fixture:

- Rows 1-26 of `ground_truth.lrc` begin before or at the audible file end and
  are the scored lyric/timing rows.
- Rows 27-31 begin after `02:54.3`; do not require them, and do not reward an
  answer merely for carrying them over from a full external lyric/LRC.
- A row that starts before `02:54.3` but is truncated by the file ending still
  counts as an audible onset and should be represented if heard.

Required section anchors, taken from the hidden references and local audio:

- Opening vocal onset: row 1 at about `00:14`, with rows 1-3 spanning the first
  vocal phrase through about `00:25`.
- Main verse close: rows 14-15 around `01:28` to `01:34`.
- Dialogue/call-and-response entry: rows 16-18 around `01:44` to `01:54`.
- First call response inside the dialogue: row 19 around `02:02`.
- Later dialogue prompts/responses: rows 20-23 around `02:12` to `02:36`.
- Local-tail refrain onsets: rows 24-26 around `02:43`, `02:47`, and `02:53`.

For line matching, normalize case, punctuation, apostrophes, whitespace,
speaker-label syntax, and spacing variants such as one-word vs two-word forms.
Speaker labels are optional, but if present they must not invert the
male/female exchange. Adjacent split/merged lines can receive semantic content
credit, but separate-row timing credit requires distinct timestamps in the
expected order.

Improved wording over the hidden reference is acceptable only when it is
plausibly supported by the local audio and remains aligned to the locked
section anchors. It cannot rescue an answer whose timing or structure matches a
different public recording.

## 4. Source-Selection and Output-Resolution Rules

The only in-scope source is the single shipped MP3 under
`/tmp_workspace/clawbench/sources/`. Any web page, downloaded lyric file,
metadata field, previous memory of the song, or generated transcript unverified
against the local audio is non-canonical.

When multiple LRC files exist in `/tmp_workspace/results/`, grade the file at
the exact requested path first. If that file is missing, grade the accepted
alias only if it is clearly the executor's final answer and the revision log
refers to it. Scratch WAVs, waveform images, players, or spectrograms are
evidence only; they are not substitutes for the LRC or review file.

When assessing source grounding, use visible trace evidence: local playback,
segmented listening, local audio processing, waveform checks, or explicit
manual corrections can support the score. Self-reported listening in the review
file is not enough if the trace shows no local-audio work and the LRC has copied
or wrong-version timing.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award points line-by-line, then apply the caps in section
6 by taking the minimum.

- **0.15 - Output shape and LRC validity.** The main LRC exists at the required
  path or accepted alias, parses as LRC, contains at least 24 timed lyric rows
  before `02:54.3`, uses nondecreasing timestamps, and has no required-looking
  lyric rows after the local file end. Partial credit is allowed for minor
  formatting issues; zero this line if the file cannot be parsed.

- **0.25 - Lyric content coverage.** Score rows 1-26 from the hidden LRC.
  Full credit requires at least 25 of 26 audible rows represented in order,
  with all critical anchor groups present: rows 1-3, 14-15, 16-23, and 24-26.
  Give proportional partial credit for fewer matched rows, but do not count
  hallucinated extra verses or post-file lyric continuations as coverage.

- **0.25 - Timestamp alignment to the local MP3.** Full credit requires the
  critical anchors in section 3 within about `+/- 3` seconds and at least 80%
  of scored rows within `+/- 5` seconds of the hidden row starts. Partial
  credit may be awarded for usable but looser alignment. A global offset,
  compression of the dialogue pauses, or timing that matches another recording
  should lose most or all of this line.

- **0.15 - Duet/call-and-response structure.** Rows 16-26 must preserve the
  alternating dialogue/refrain structure as distinct timed turns in the correct
  order. Full credit requires separate rows for the address/answer, the
  question/call, the two later prompt/response turns, the setup line, and the
  local-tail refrain rows. Speaker labels may be absent or formatted
  differently, but the structure must remain readable and not be collapsed into
  a generic block.

- **0.10 - Local-audio grounding and revision behavior.** Credit visible work
  from the shipped MP3: actual playback, local transcription followed by
  manual checking, segment re-listening, or concrete timestamp corrections.
  Deduct heavily for relying on metadata/title recognition, internet searches,
  or old-memory lyrics. Zero this line when the trace shows only copied
  lyrics/LRC or no source-audio interaction.

- **0.10 - Review/revision file quality.** The review file exists at
  `/tmp_workspace/results/song_revision_log.md` or accepted alias,
  and briefly states concrete rechecks or corrections for the opening, the
  middle/dialogue or repeated region, and the ending. Generic completion claims,
  empty files, or logs that contradict the visible artifacts receive at most
  half of this line.

## 6. Scoring Policy / Score Caps

Partial credit from section 5 is the raw score. Apply every cap that fits and
use the minimum capped score. A run passes only if the final score is `>= 0.90`.

- **Cap at 0.30 - No main deliverable.** The main LRC and accepted aliases are
  all missing from `/tmp_workspace/results/`.
- **Cap at 0.40 - Wrong song or no lyric transcription.** The LRC is mostly
  unrelated to the local audio, contains no meaningful lyric transcription, or
  is only instrumental/placeholders.
- **Cap at 0.50 - Invalid or too short LRC.** The LRC is not parseable as timed
  LRC, has fewer than 8 timed lyric rows, or timestamps are so malformed that
  row order cannot be evaluated.
- **Cap at 0.55 - Copied web/full-recording lyrics not aligned to the local
  audio.** Apply when the answer resembles a common full lyric/LRC or metadata-
  identified version and fails the locked local anchors, such as placing the
  opening vocal near `00:00`, placing the dialogue around the first minute,
  adding a full extra verse as if it were required, or carrying scored lyrics
  beyond `02:54.3`.
- **Cap at 0.60 - Severe timestamp drift.** Apply when the opening is before
  `00:05` and the dialogue begins before `01:15`, or when the median drift of
  matched rows is more than `15` seconds.
- **Cap at 0.70 - Wrong duet/call-response structure.** Apply when rows 16-23
  are missing, collapsed into one vague block, reordered, assigned to the wrong
  voices in a way that changes the exchange, or represented by fewer than six
  distinct dialogue turns.
- **Cap at 0.74 - Major line omissions.** Apply when fewer than 22 of the 26
  audible reference rows are represented, regardless of how polished the
  remaining rows are.
- **Cap at 0.75 - Large anchor drift.** Apply when any critical anchor group
  is more than `15` seconds from the locked ground-truth time, or the dialogue
  is compressed so that rows 16-26 land more than `20` seconds earlier or later
  by the tail.
- **Cap at 0.80 - Degraded dialogue detail.** Apply when the dialogue section
  exists but one or two required prompt/response turns are merged, omitted, or
  ambiguous enough that the call-and-response is not reliably usable.
- **Cap at 0.84 - Pass-blocking omissions or drift.** Apply when any critical
  anchor group from section 3 is absent, when fewer than 24 of 26 audible rows
  are represented, when the median matched-row drift exceeds `5` seconds, or
  when more than 20% of scored rows fall outside `+/- 5` seconds.
- **Cap at 0.84 - Missing review file.** Apply when the required
  `song_revision_log.md` or accepted alias is missing. A good LRC
  without the requested review file should continue, not pass.
- **Cap at 0.80 - Non-specific or false review file.** Apply when the review
  file exists but gives only generic claims, omits the requested recheck areas,
  or claims corrections not reflected in the final LRC.
- **Cap at 0.45 - No local-audio grounding with forbidden-source evidence.**
  Apply when the visible trace shows lyric lookup, downloaded LRC/SRT, metadata
  extraction, or prior song-knowledge as the effective source and no meaningful
  local listening/re-timing.

These caps are intentionally stricter than artifact-existence scoring. A
complete-looking LRC, speaker labels, or a confident revision log cannot
override wrong source grounding, wrong duet structure, missing lines, or
timestamp drift against the local MP3.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** Stop only when the LRC is locally aligned,
  covers at least 24 of 26 audible rows with all critical anchors present,
  preserves the dialogue/refrain structure, and includes a concrete review
  file. No cap below `0.90` may be active.
- **Continue (`0.60 - 0.89` after caps).** Request one follow-up when the answer
  is recoverable: a valid LRC exists but the review file is missing, a few rows
  or dialogue turns need repair, or timestamp drift can be corrected by
  re-listening to the specified regions.
- **Fail (`< 0.60` after caps).** Do not request more work when there is no
  usable LRC, the answer is for the wrong recording/song, the output is copied
  from forbidden sources without local alignment, or the line/timing errors are
  too extensive to repair within a short follow-up.

## 8. Hidden Reference Assets

Supervisor-only files:

- `references/eval_rule.md` - this grading rule.
- `references/ground_truth.lrc` - canonical row order, text, and start-time
  anchors.
- `references/ground_truth.srt` - same transcript with end times for checking
  section spans.

## 9. Dynamic Content Note

Offline task. Do not browse or use live lyric sites to update the answer. If
runtime filenames differ between the authoring YAML and visible prompt, grade
the visible prompt's requested paths while using the hidden references and the
local MP3 duration above as the grading authority.
