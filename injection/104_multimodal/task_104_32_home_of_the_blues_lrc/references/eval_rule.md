# Hidden Evaluation Rule — Anonymous Song LRC

## 1. Grading Philosophy

Grade the submitted LRC as a synchronization deliverable for the local audio,
not as a general lyric-recognition answer. The hidden `ground_truth.lrc` and
`ground_truth.srt` are the locked benchmark for lyric order, line granularity,
and start times. The executor may use different capitalization, punctuation,
apostrophe style, or equivalent contractions, but polished formatting or a
self-reported review cannot compensate for missing lines, wrong-version timing,
or lyrics copied from elsewhere without alignment to the provided file.

The public task explicitly forbids using filename, metadata, internet lyrics,
or prior memory as the source of truth. Award high scores only when the final
artifacts show the executor worked from the local audio and produced line-level
timestamps for this exact recording.

## 2. Task Contract

The current task asks the executor to use:

- Input audio: `/tmp_workspace/clawbench/sources/song.mp3`
- Required main output: `/tmp_workspace/results/song_generated.lrc`
- Required review output: `/tmp_workspace/results/song_review.md`

If evaluating an archived run whose visible prompt explicitly requested a
different basename, apply the same checks to the exact LRC and review filenames
requested in that visible prompt. Do not give full output-contract credit for
unrequested extra LRC files when the requested file is absent.

The LRC must use standard `[mm:ss.xx]lyric text` rows, preserve chronological
order, and put each sung line on its own timestamped row. Repeated lines and the
post-interlude return after `02:02` must not be collapsed into earlier rows.

## 3. Locked Ground Truth

The source audio is a static local fixture (`song.mp3`, about `166.536` seconds).
The MP3 has no embedded lyric stream; source metadata is not a valid substitute
for listening or local audio analysis.

Score against these 21 canonical lyric rows. Non-lyric rows such as
`(instrumental intro)`, blank timestamp rows, title tags, or artist tags do not
count as lyric rows and cannot replace any row below.

| # | Start | Canonical lyric |
|---|-------|-----------------|
| 1 | `00:12.00` | Just around the corner there's heartache |
| 2 | `00:16.00` | Down the street that losers use |
| 3 | `00:23.00` | If you can wade in through the teardrops |
| 4 | `00:30.00` | You'll find me at the Home of the Blues |
| 5 | `00:34.00` | I walk and cry while my heart beats |
| 6 | `00:40.00` | Keeps time with the drag of my shoe |
| 7 | `00:46.00` | The sun never shines through this window of mine |
| 8 | `00:52.00` | It's dark at the Home of the Blues |
| 9 | `00:57.00` | Oh, but the place is filled with the sweetest mem'ries |
| 10 | `01:03.00` | Mem'ries so sweet that I cry |
| 11 | `01:10.00` | Dreams that I've had left me feeling so bad |
| 12 | `01:16.00` | I just want to give up and lay down and die |
| 13 | `01:21.00` | So if you've just lost your sweetheart |
| 14 | `01:27.00` | And it seems there's no good way to choose |
| 15 | `01:33.00` | Come along with me, misery loves company |
| 16 | `01:39.00` | You're welcome at the Home of the Blues |
| 17 | `02:02.00` | Just around the corner there's heartache |
| 18 | `02:09.00` | Down the street that losers use |
| 19 | `02:15.00` | If you can wade in through the teardrops |
| 20 | `02:21.00` | You'll find me at the Home of the Blues |
| 21 | `02:27.00` | Yeah, you're gonna find me at the Home of the Blues |

Critical timing anchors are rows `1`, `4`, `9`, `12`, `16`, `17`, `20`, and
`21`. The final return is not complete unless rows `17` through `21` are all
present as separate timestamped lyric rows.

## 4. Normalization and Matching

For lyric text matching, ignore case, punctuation, repeated whitespace,
straight versus curly apostrophes, and harmless contractions such as
`memories` / `mem'ries` or `feeling` / `feelin'`. Singular/plural changes,
different nouns, or changed verbs count as text errors when they alter the
audible phrase (`teardrop` versus `teardrops`, `shoes` versus `shoe`,
`the place` versus `but the place`).

Match submitted lyric rows to the canonical rows in order after discarding
metadata tags, blank timestamp rows, and instrumental markers. A row is
"present" only if it has its own timestamp and text that clearly corresponds to
one canonical row. A merged row covering two canonical lines counts as one
present row and one missing row.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award checkpoint credit before applying the caps in
section 6.

- **0.10 - Output contract and LRC validity.** Full credit requires the
  requested main LRC file to exist, parse as standard LRC, contain monotonically
  nondecreasing timestamps, and contain at least 18 timestamped lyric rows.
  Give at most 0.05 here if the only usable LRC is under an unrequested
  filename; give 0.00 if no parseable LRC exists.

- **0.25 - Lyric text coverage.** Score `0.25 * correct_rows / 21` using the
  ordered matching rules above. Full credit requires all 21 canonical rows to
  be present with correct audible text. Rows with only punctuation,
  capitalization, or accepted contraction differences count as correct.

- **0.15 - Granularity and song structure.** Award 0.05 for keeping rows
  `1`-`8` as separate opening/first-chorus lines, 0.04 for preserving bridge
  rows `9`-`12`, 0.03 for preserving rows `13`-`16`, and 0.03 for preserving
  the post-interlude return rows `17`-`21`. Zero the relevant subpart when
  repeated lines are collapsed, the bridge is summarized, or the final return
  is represented by fewer than five separate lyric rows.

- **0.35 - Timestamp accuracy.** Use the matched canonical rows and compare
  start times in seconds. Award up to 0.20 line-level timing credit:
  each matched row within `1.25s` earns full line timing credit, each matched
  row over `1.25s` but within `1.75s` earns half line timing credit, and rows
  over `1.75s` earn none. Award up to 0.10 anchor credit across the eight
  critical anchors, full per anchor only when the matched start is within
  `1.25s`. Award the final 0.05 only when there is no section-level drift:
  no group of three or more consecutive matched lyric rows may all be more
  than `1.25s` early or all more than `1.25s` late.

- **0.15 - Review note and source grounding.** Award 0.08 for the requested
  review file existing and naming concrete timestamps or sections rechecked
  after the draft, including the opening `0:00-0:20` and at least one
  chorus/re-entry timestamp. Award 0.07 for visible evidence that the executor
  used the local audio for transcription or re-timing, such as playback,
  waveform/spectrogram inspection, ASR on the local MP3, chunk review, or
  explicit local-audio timing corrections. Do not award source-grounding
  credit for web lyric lookup, filename inference, artist/title metadata, or
  unsupported claims that the audio was checked.

## 6. Scoring Policy / Score Caps

Compute the weighted rubric total, then apply all applicable caps by taking
the minimum. A run passes only if the capped score is `>= 0.90`.

- **Cap at 0.30 - Missing main LRC.** No requested LRC file exists and no
  clearly equivalent LRC artifact is present in the result directory.
- **Cap at 0.45 - Invalid or unusably tiny LRC.** The main artifact is not
  parseable standard LRC, has non-monotonic lyric timestamps, or has fewer than
  8 timestamped lyric rows.
- **Cap at 0.50 - Wrong song or non-target transcription.** The lyric content
  is clearly not this song, is mostly hallucinated, or is mostly unrelated to
  the hidden 21-row progression.
- **Cap at 0.55 - Wrong version or wrong-version timing.** The words are
  recognizably from this song but the row layout or timing corresponds to a
  different recording/version rather than this `166.536s` local audio, such as
  three or more critical anchors off by more than `3.0s` or timing that extends
  well beyond the local performance.
- **Cap at 0.60 - Copied web/prior lyrics not aligned to local audio.** The
  visible trace shows lyric-page copying, prior-memory completion, or metadata
  inference with no meaningful local audio re-timing, even if the copied words
  are mostly correct. Cap at 0.45 instead if timestamps are absent or generic.
- **Cap at 0.70 - Final return missing.** Rows `17`-`21` after the interlude
  are absent, collapsed into one or two rows, or placed outside the `02:02` to
  `02:31` performance region.
- **Cap at 0.74 - Major missing-line failure.** Fewer than 18 of the 21
  canonical rows are present as separate timestamped lyric rows.
- **Cap at 0.84 - Any missing canonical lyric row.** One or more canonical
  rows are omitted or merged so they lack their own timestamped lyric row.
  This cap is intentionally below the pass threshold because a pass requires
  complete line coverage.
- **Cap at 0.84 - Timestamp drift.** The LRC has otherwise recognizable text
  but fails the drift requirement in section 5, has median absolute timing
  error over `1.25s`, has any two critical anchors over `2.0s` off, or places
  the closing row `21` more than `2.0s` from `02:27.00`.
- **Cap at 0.84 - Missing review file.** The requested review file is absent.
  If a review exists but contains no concrete timestamp or section-specific
  recheck notes, cap at 0.90 and withhold the relevant CP5 credit.
- **Cap at 0.70 - Wrong required filename only.** A good LRC exists in the
  result directory but the requested main filename is missing. Use this cap
  only when the artifact is otherwise gradeable and clearly intended as the
  answer.

Do not penalize for harmless punctuation, capitalization, LRC metadata tags, or
extra non-lyric markers unless they hide, merge, reorder, or replace canonical
lyric rows. Do penalize title/artist/version assertions when they are used as a
substitute for local audio grounding or lead to wrong-version lyrics/timing.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** The requested LRC and review exist; all 21
  canonical lyric rows are present as separate rows; no cap below 0.90 applies;
  timing is close enough for lyrics-player use at the opening, bridge, re-entry,
  and closing anchors.
- **Continue (`0.60 - 0.89` after caps):** The LRC is for the right song and is
  mostly complete, but a fixable issue remains: one missing/merged line, a
  missing or weak review note, section-level timestamp drift, a wrong filename,
  or a post-interlude return that needs re-timing. Feedback should cite the
  specific rows or timestamps needing repair.
- **Fail (`< 0.60` after caps):** The main LRC is missing or unusable, the
  answer is the wrong song/version, there is no meaningful local-audio
  alignment, or too much of the 21-row reference is absent to repair in one
  follow-up.

## 8. Hidden Reference Assets

Supervisor-only assets:

- `references/eval_rule.md` - this grading rule.
- `references/ground_truth.lrc` - locked line-level lyric and start-time
  reference.
- `references/ground_truth.srt` - locked lyric segments with end times.

## 9. Dynamic Content Note

This is an offline task. Do not use live web lyrics, artist databases, or
metadata updates to revise the hidden reference. If the source audio and hidden
references ever appear inconsistent, flag the fixture mismatch instead of
grading against external versions of the song.
