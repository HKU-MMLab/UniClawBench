# Hidden Evaluation Rule — House of the Rising Sun LRC

## 1. Grading Philosophy

Judge whether the executor created a usable, locally grounded LRC for the
provided audio, not whether it reproduced a remembered or web-sourced version
of the song. Full credit requires:

1. the requested LRC file at `/tmp_workspace/results/song_generated.lrc`;
2. line-by-line lyric coverage of the audible local MP3 through its ending;
3. timestamps aligned to the shipped `song.mp3`, not to a longer legacy timing
   axis; and
4. a concrete review file showing that the main verses and ending were checked.

Use semantic lyric matching rather than brittle punctuation matching, but be
strict about section coverage, local-audio timing, and output artifacts. Copied
lyrics, long-version timing, self-reported confidence, or polished formatting
must not compensate for missing local-audio evidence.

## 2. Task Contract

The public task asks the executor to listen to:

- `/tmp_workspace/clawbench/sources/song.mp3`

Required deliverables:

- `/tmp_workspace/results/song_generated.lrc` - a standard LRC file using
  `[mm:ss.xx]lyric` rows, one sung line per row, with repeated lines retained.
- `/tmp_workspace/results/song_review.md` - a short review note that names
  concrete time ranges or lyric sections rechecked after drafting, especially
  the main verses and ending. Accept `song_notes.md`, `review.md`, or another
  Markdown/text file under `/tmp_workspace/results/` only if it clearly serves
  this same review function.

The supervisor may inspect trace/tool evidence for whether the local audio was
opened, played, converted, segmented, or otherwise used. However, the score is
based on saved artifacts and their agreement with the local MP3.

## 3. Locked Ground Truth and Local-Audio Boundary

Canonical hidden references:

- `references/ground_truth.lrc`
- `references/ground_truth.srt`

Authoritative source facts:

- The shipped `song.mp3` duration is `182.256` seconds (`03:02.256`).
- The hidden LRC/SRT is a legacy timing guide that continues to `03:24` /
  `03:28`, beyond the current local MP3. The local MP3 boundary overrides any
  hidden-reference timestamps after `03:02.256`.
- Required local-audio lyric anchors are the first 18 hidden-reference lyric
  units, through "I'm going back to New Orleans" near `02:52` and "My race is
  almost run" near `03:00`.
- The final two legacy rows, "I'm going back to spend my life" at `03:13` and
  "Beneath the Rising Sun" at `03:24`, are out-of-file tail rows for this
  fixture. Do not require them as audible local-MP3 lyrics, and do not reward
  placing them after the local file ends.

Expected local anchor map, with modest tolerance for faithful listening:

| Anchor | Lyric cue | Expected start |
|---|---|---:|
| A1 | There is a house in New Orleans | `00:00` |
| A2 | They call the Rising Sun | `00:05` |
| A3 | It's been the ruin of many a poor girl | `00:14` |
| A4 | And me, oh Lord, I'm one | `00:23` |
| A5 | If I had listened to what my mother said | `00:46` |
| A6 | I'd have been at home today | `00:57` |
| A7 | But I was young and foolish | `01:07` |
| A8 | Let a rambler lead me astray | `01:20` |
| A9 | My mother was a tailor | `01:27` |
| A10 | She sewed my new blue jeans | `01:36` |
| A11 | My sweetheart was a gambling man | `01:48` |
| A12 | Down in New Orleans | `02:00` |
| A13 | Oh mothers, tell your children | `02:07` |
| A14 | Not to do what I have done | `02:17` |
| A15 | To spend their lives in sin and misery | `02:29` |
| A16 | In the house of the Rising Sun | `02:39` |
| A17 | I'm going back to New Orleans | `02:52` |
| A18 | My race is almost run | `03:00` |

Wording may differ where the audio supports it, but the accepted answer must
preserve this shorter folk/female-narrator structure rather than substituting a
later The Animals-style lyric progression.

## 4. Checkpoint Rubric

Weights sum to 1.00.

- **0.20 - Required LRC artifact and syntax.** Full credit requires
  `/tmp_workspace/results/song_generated.lrc` to exist, parse as LRC, contain
  timed lyric rows in `[mm:ss.xx]lyric` format, and have monotonically
  increasing timestamps. Metadata rows may be ignored, but a differently named
  LRC does not earn this checkpoint unless `song_generated.lrc` also exists.

- **0.20 - Line segmentation and repeat handling.** Full credit requires
  roughly one row per sung line, normally 16-24 substantive timed lyric rows for
  the local fixture. Whole verses must not be collapsed into single rows, and
  repeated or continuing lines must appear separately when sung separately.

- **0.25 - Lyric and section coverage.** Score against the 18 required local
  anchor units in Section 3. Award proportional credit for semantically
  correct, in-order coverage. Full credit requires at least 17/18 anchors
  present with no substituted long-version-only verse that displaces local
  content. 15-16/18 anchors can receive most of this checkpoint; 12-14/18 is
  partial; fewer than 12/18 earns little or no credit here.

- **0.20 - Local-MP3 timing alignment.** Compare matched lyric rows to the
  anchor map. Full credit requires the opening, mid-song, warning verse, and
  final local ending anchors to be within about `5` seconds where the lyric cue
  is clear, with no systematic shift. Minor line-break differences are fine;
  visible lyrics-player drift is not.

- **0.10 - Local-audio ending coverage.** Full credit requires the LRC to cover
  the ending of the actual `03:02.256` MP3: A17 near `02:52` and A18 near
  `03:00` must be represented, and the last substantive lyric timestamp should
  fall in the final `15` seconds of the local audio unless the trace proves the
  audio itself ends earlier.

- **0.05 - Review evidence.** Full credit requires a concrete review file under
  `/tmp_workspace/results/` as defined in Section 2. It must mention specific
  reviewed timestamps, ranges, or sections such as the main verses, warning
  verse, `02:52-03:02` ending, or corrections made after re-listening.

## 5. Scoring Policy / Score Caps

Award checkpoint credit first, then apply all applicable caps by taking the
minimum. Caps below are intentionally strict; they target failures that cannot
be rescued by formatting or partial content elsewhere.

- **Cap at 0.30 - Missing main LRC.** `/tmp_workspace/results/song_generated.lrc`
  is absent. A correctly named review file or auxiliary LRC under another name
  does not remove this cap.

- **Cap at 0.50 - Invalid or tiny LRC.** The main file is not recognizable LRC,
  has non-monotonic timestamps, has fewer than 8 substantive timed lyric rows,
  or is mostly prose/placeholders rather than timed lyrics.

- **Cap at 0.45 - Not grounded in the local audio.** Trace or artifact evidence
  shows only web lookup, copied lyric pages, copied hidden references, prior
  memory, or a model-generated lyric without any meaningful use of
  `/tmp_workspace/clawbench/sources/song.mp3`.

- **Cap at 0.70 - Wrong long-version timing.** The LRC follows the legacy
  long-version axis rather than the local MP3, including any of these objective
  signs: required lyric anchors placed after `03:05`, final rows at or near
  `03:13` / `03:24`, timestamps extending beyond `03:02.256` for substantive
  lyrics, or a final lyric near `03:24` instead of the local ending near
  `03:00-03:02`.

- **Cap at 0.80 - Missing local-audio ending.** A17/A18 are missing, the last
  substantive lyric timestamp is before `02:47`, or the ending is represented
  only by vague/instrumental notes rather than the sung local ending. If the
  last substantive lyric timestamp is before `02:15`, cap at `0.55` instead.

- **Cap at 0.70 - Major lyric omissions.** Fewer than 15 of the 18 required
  local anchor units are present, a full required verse is omitted, or the
  output substitutes a substantially different version of the song for the
  local female-narrator structure. If fewer than 10 anchors are present, cap at
  `0.50`.

- **Cap at 0.80 - Timestamp drift.** More than one third of matched anchor rows
  drift by over `8` seconds from the local anchor map, or any major section
  (opening, middle, warning verse, ending) is shifted enough to be visibly
  unusable in a lyrics player. If most anchors are shifted by over `20`
  seconds, cap at `0.60`.

- **Cap at 0.84 - Missing review file.** No qualifying review file exists under
  `/tmp_workspace/results/`, or the only note is generic and does not name any
  concrete reviewed timestamps, ranges, or sections.

- **Cap at 0.75 - Wrong required filename.** A good LRC exists only under a
  non-requested filename and `/tmp_workspace/results/song_generated.lrc` is
  missing or stale. This cap composes with the missing-main-LRC cap if there is
  no usable main file at all.

Do not penalize merely for punctuation, capitalization, "Lord" vs. "God" style
variants, or slightly different line breaks that remain faithful to the local
audio. Do penalize omissions, invented verses, copied long-version timing, and
timestamps that would visibly desynchronize a lyrics player.

A run passes only if the final capped score is `>= 0.90`.

## 6. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - The main LRC is correctly named, valid,
  locally timed, covers at least 17/18 local anchors including A17/A18, and has
  a concrete review file. Stop the attempt.

- **Continue (`0.60 - 0.89` after caps)** - The LRC exists and is plausibly for
  this audio, but one fixable issue remains: missing review file, a few omitted
  lyric anchors, ending lines needing extension/retiming, or moderate drift.
  Use a follow-up if available and ask for targeted repair.

- **Fail (`< 0.60` after caps)** - No usable main LRC exists, the output is not
  grounded in the local audio, most lyric anchors are missing, the song/version
  is fundamentally wrong, or timing is so drifted that the result is unusable.
  If follow-ups are exhausted, record terminal failure.

## 7. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.lrc` - canonical lyric-order and timing anchors.
- `references/ground_truth.srt` - parallel subtitle timing anchors.

## 8. Dynamic Content Note

Offline task. Do not use live web results to change the expected answer. If the
on-disk MP3 and hidden references conflict, the actual local MP3 duration and
audible content control timing and ending coverage; the hidden references
remain lyric-order anchors only within the `03:02.256` local-audio boundary.
