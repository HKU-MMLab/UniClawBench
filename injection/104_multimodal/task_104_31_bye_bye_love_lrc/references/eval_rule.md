# Hidden Evaluation Rule — task_104_31_bye_bye_love_lrc

## 1. Grading Philosophy

Grade whether the executor produced a locally timed LRC for the shipped audio,
not whether it identified the public song. The public task explicitly
forbids using filenames, metadata, internet lyrics, existing LRC/SRT files, or
memory as the source of truth. A high score therefore requires both correct
deliverables and evidence that the timing was checked against the local MP3.

The hidden `ground_truth.lrc` and `ground_truth.srt` are canonical for lyric
order and section coverage. Their original timestamps are not fully canonical,
because the shipped local MP3 is only `148.464` seconds long while the hidden
LRC/SRT continue past three minutes. Evaluate timing against the local MP3
boundary and the local-audio anchors in Section 4.

Do not reward polished formatting, self-reported confidence, song metadata, or
web lyric text when the LRC is not synchronized to the local audio.

## 2. Task Contract

The executor is asked to open:

- `/tmp_workspace/clawbench/sources/song.mp3`

Required outputs:

- `/tmp_workspace/results/song_generated.lrc`
- `/tmp_workspace/results/song_notes.md`

The main output must be a standard LRC file with lines of the form
`[mm:ss.xx]lyric`, monotonically increasing timestamps, natural line or phrase
segmentation, and no required lyric timestamp after the audible local file
ends. The notes file must briefly state concrete time ranges or checkpoints
that were rechecked after the first LRC draft.

Do not accept older title-based task-output names as the primary deliverable
for the current task unless `song_generated.lrc` also exists with equivalent
content.

## 3. Source Selection and Normalization Rules

The only in-scope audio is the file shipped as:

- `/tmp_workspace/clawbench/sources/song.mp3`

The supervisor may use tool traces, saved intermediate files, and final
artifacts to determine whether the executor worked from this local file. Use
semantic lyric matching after light normalization:

- Ignore case, punctuation, apostrophe style, repeated spaces, and hyphenation.
- Accept phrase splits or joins when the canonical lyric words remain in
  order and the split timestamps are plausible.
- Do not accept substitutions that change the lyric meaning or indicate ASR
  failure, such as wrong nouns in repeated refrain phrases, wrong
  subject/object in a verse line, or replacing key bridge words with unrelated
  homophones.
- Extra blank LRC metadata rows do not earn lyric credit and should not mask
  missing lyric rows.

## 4. Locked Ground Truth

Canonical text sequence:

- The lyric sequence is the 32 timed text rows in `references/ground_truth.lrc`
  and the matching cues in `references/ground_truth.srt`.
- All 32 canonical lyric rows are expected to be represented in the final LRC,
  but rows may be split into shorter phrase lines when the words stay in order.
- The legacy hidden rows after `02:28` are not optional lyrics; they are audible
  earlier in this shorter local MP3 and must be retimed before the local vocal
  ending.

Current local-audio facts:

- `song.mp3` duration is `148.464` seconds.
- First audible lyric begins around `00:08.5`.
- The first narrative verse starts around `00:33.5-00:34.5`.
- The second chorus/reprise starts around `00:57.5-00:58.5`.
- The bridge section starts around `01:23.0-01:24.0`.
- The final chorus starts around `01:47.0-01:48.0`.
- The repeated closing refrain lines occur around `02:09-02:20`.
- After about `02:21`, the remaining file is outro/fade/silence; no required
  lyric should be timestamped later than `02:22` unless supported by clear
  audible vocal evidence, and no required lyric may be after `02:28.464`.

For pass-level timing, compare canonical lyric-row onsets after mapping split
phrases back to their row. A high-quality LRC should keep most onsets within
about `1.5` seconds of the local-audio phrase start, with no major section
anchor drifted by more than `3` seconds.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.15 - Required deliverables and format.** `song_generated.lrc` exists at
  `/tmp_workspace/results/`, parses as LRC, has timestamped lyric lines in
  nondecreasing order, and contains no required lyric timestamp beyond the
  `148.464` second file duration. `song_notes.md` exists. Award at most `0.08`
  here if either required output uses only a legacy filename.

- **0.20 - Canonical lyric coverage.** Full credit requires all 32 canonical
  lyric rows from `ground_truth.lrc` represented in order after normalization,
  including the opening chorus, first narrative verse, reprise chorus, bridge,
  final chorus, and repeated closing refrain rows. Deduct proportionally for
  isolated word errors, but zero this checkpoint if any major section is absent.

- **0.15 - Granularity and line structure.** The LRC should use natural lyric
  lines or short phrases, not block paragraphs. A typical good answer has
  roughly `32-50` timed lyric rows because canonical rows may be split into
  phrases. Full credit requires repeated chorus/outro material to appear as
  separate timed rows rather than one collapsed block.

- **0.25 - Local timing accuracy.** Score by local-audio alignment, not by the
  legacy hidden timestamps. Full credit requires the first lyric, narrative
  verse, reprise chorus, bridge, final chorus, and closing repetitions to land
  in the Section 4 windows, with most mapped lyric rows within about `1.5`
  seconds of their local onset and no systematic early/late drift. Award no
  more than half of this checkpoint if the LRC is globally plausible but more
  than three section anchors are drifted by `>3` seconds.

- **0.10 - Local-source process evidence.** The visible trace or saved notes
  should show playback, audio probing, ASR/transcription from the local MP3, or
  manual re-listening/re-timing against local audio. Merely reading metadata or
  identifying the public song earns no credit here.

- **0.10 - Review notes quality.** `song_notes.md` must name concrete reviewed
  time ranges or checkpoints and describe what was checked or corrected. Vague
  notes such as "I reviewed the whole song" without intervals earn at most
  `0.04`.

- **0.05 - No noncanonical additions.** The LRC must not add unrelated spoken
  text, website watermarks, artist/title guesses as lyric lines, or full-song
  tail lyrics not audible in the local MP3. Standard metadata tags are allowed
  but do not substitute for lyric content.

Total: `0.15 + 0.20 + 0.15 + 0.25 + 0.10 + 0.10 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

Award checkpoint credit first, then apply the caps below by `min`. A run passes
only if the capped score is `>= 0.90`.

- **Cap at 0.30 - Main LRC missing.** No
  `/tmp_workspace/results/song_generated.lrc` exists.
- **Cap at 0.40 - Not a valid LRC answer.** The main file is prose, JSON, SRT,
  or fewer than 8 timestamped lyric lines.
- **Cap at 0.50 - Wrong song or unrecognizable lyric content.** The output is
  not recognizably the hidden lyric sequence in `ground_truth.lrc`, or it
  substitutes a different recording/song.
- **Cap at 0.55 - Wrong song/version timing.** The lyric text is mostly right
  but timestamps follow a different/full-length version rather than the local
  `148.464` second MP3. Strong indicators include narrative verse near
  `00:44`, bridge near `01:53`, final chorus after `02:21`, or any required
  lyric rows placed in the `02:28-03:20` range from the legacy hidden LRC.
- **Cap at 0.45 - Copied web lyrics not aligned to local audio.** The visible
  trace shows lyric lookup/copying, downloaded LRC/SRT, or prior-knowledge
  reconstruction with no evidence of local listening/ASR/re-timing, and the
  result is not synchronized to the shipped MP3.
- **Cap at 0.70 - Major lyric-line omissions.** Any major section is missing,
  or `>=5` of the 32 canonical lyric rows cannot be matched after
  normalization.
- **Cap at 0.84 - Minor lyric-line omissions.** `1-4` canonical lyric rows are
  missing or replaced by materially wrong text. This prevents a pass even if
  timing and formatting are good.
- **Cap at 0.65 - Severe timestamp drift.** At least three major section
  anchors are off by more than `6` seconds, or the LRC has a consistent global
  offset that would make lyrics visibly unusable in a player.
- **Cap at 0.80 - Moderate timestamp drift.** Most lyrics are recognizable but
  repeated drift over `3` seconds affects multiple sections, or the outro is
  visibly early/late while the rest is usable.
- **Cap at 0.78 - Outro/reprise collapse.** The final chorus or repeated
  closing refrain rows are collapsed into one line, omitted, or not separately
  timed even though they are audible in the local MP3.
- **Cap at 0.84 - Missing review file.** `song_notes.md` is absent, empty, or
  only exists under an obsolete filename. Since pass requires `>= 0.90`, missing
  review evidence cannot pass.
- **Cap at 0.88 - Review file too vague.** The notes file exists but does not
  identify concrete reviewed time ranges or checkpoints.
- **Cap at 0.75 - No local-source evidence.** Artifacts may be plausible, but
  the trace shows no playback, audio probing, local ASR, waveform/silence
  analysis, or manual timing work against the shipped MP3.
- **Cap at 0.60 - Required lyrics after file end.** Any required lyric is
  timestamped after `02:28.464`, even if the text matches the hidden reference.

Do not apply a cap for harmless punctuation, capitalization, apostrophe,
hyphenation, or phrase-splitting differences when content and local timing are
otherwise correct.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** Stop. This requires the current filenames,
  near-complete 32-row lyric coverage, local-audio timing through the outro,
  and concrete review notes.
- **Continue (`0.60 - 0.89` after caps):** Request one focused repair when the
  LRC exists and is recognizably the correct local song but is blocked by
  fixable issues such as missing notes, a few omitted lyric rows, moderate
  drift, weak review intervals, or collapsed outro rows.
- **Fail (`< 0.60` after caps):** Stop and record failure. This includes no
  LRC, invalid LRC, wrong song/version timing copied from a full-length source,
  web lyrics with no local alignment, severe section omissions, or required
  lyrics after the file end.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.lrc` - canonical lyric text order and legacy timing
  reference.
- `references/ground_truth.srt` - equivalent canonical cue sequence and legacy
  timing reference.

## 9. Dynamic Content Note

Offline task. No live web lookup is required or useful. If source metadata or a
webpage disagrees with the local MP3, grade against the local MP3 and the hidden
canonical lyric sequence. If future fixture audio duration differs from
`148.464` seconds, flag fixture drift rather than silently accepting
full-length web timing.
