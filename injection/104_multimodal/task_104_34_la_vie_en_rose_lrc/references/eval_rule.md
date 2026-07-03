# Hidden Evaluation Rule — task_104_34_la_vie_en_rose_lrc

## 1. Grading Philosophy

Judge the executor on whether it produced a locally synchronized LRC for the
shipped audio and an honest review note. This is not a song-identification,
web-lyrics, or memory-recall task. The final lyric text and timestamps must be
grounded in `/tmp_workspace/clawbench/sources/song.mp3`.

Use the hidden LRC/SRT as canonical local lyric-order references. The shipped
MP3 and the local start anchors in Section 4 are the timing authority. A
polished LRC using another version's timing, copied web lyrics, or generic song
knowledge cannot pass even if the words look familiar.

## 2. Task Contract

The public task asks the executor to:

- open and listen to `/tmp_workspace/clawbench/sources/song.mp3`;
- create `/tmp_workspace/results/song_generated.lrc`;
- create `/tmp_workspace/results/song_uncertainty.md`;
- use standard LRC timestamps for clear audible lyric lines or short phrases;
- keep best-effort lines for unclear or repeated passages instead of skipping
  them;
- review the chorus and ending before finalizing; and
- record the 2-3 most uncertain spots in the uncertainty file.

Only the canonical `song_*` output filenames are required and graded. Do not
give extra credit for title, artist, album, or other metadata lines.

## 3. Source-Selection and Target-Resolution Rules

The only in-scope audio source is the runtime copy of `sources/song.mp3`. The
local file is an English vocal recording, about `143.52` seconds long
(`02:23.52`). There is instrumental audio before the first vocal and during the
middle break; these instrumental spans should not be filled with invented lyric
rows.

The required output directory is `/tmp_workspace/results/`. The supervisor
grades the last saved version of the main LRC and uncertainty note. Temporary
transcripts, spectrograms, chunk files, or model output are useful evidence but
do not replace either required final artifact.

## 4. Locked Ground Truth

Hidden assets:

- `references/ground_truth.lrc`
- `references/ground_truth.srt`

These files lock the canonical English lyric progression for the local MP3.
The local MP3 has the following audible lyric slots and approximate local start
anchors:

| Slot | Local start | Expected lyric text |
|------|-------------|---------------------|
| 1 | `00:06.4` | Hold me close and hold me fast |
| 2 | `00:10.7` | The magic spell you cast |
| 3 | `00:13.9` | This is la vie en rose |
| 4 | `00:18.3` | When you kiss me, heaven sighs |
| 5 | `00:23.2` | And though I close my eyes |
| 6 | `00:26.2` | I see la vie en rose |
| 7 | `00:30.8` | When you press me to your heart |
| 8 | `00:35.1` | I'm in a world apart |
| 9 | `00:38.5` | A world where roses bloom |
| 10 | `00:42.4` | And when you speak, angels sing from above |
| 11 | `00:49.0` | Every day words seem to turn into love songs |
| 12 | `00:55.9` | Give your heart and soul to me |
| 13 | `00:59.3` | And life will always be |
| 14 | `01:02.1` | La vie en rose |
| 15 | `01:31.9` | When you press me to your heart |
| 16 | `01:36.7` | I'm in a world apart |
| 17 | `01:39.9` | A world where roses bloom |
| 18 | `01:43.6` | And when you speak, angels sing from above |
| 19 | `01:50.7` | Every day words seem to turn into love songs |
| 20 | `01:59.7` | Give your heart and soul to me |
| 21 | `02:05.0` | And life will always be |
| 22 | `02:08.4` | La vie en rose |

Locked local-audio structure:

- Instrumental intro: approximately `00:00-00:06`; no lyric at `00:00`.
- First vocal section: slots 1-14, approximately `00:06-01:07`.
- Instrumental break: approximately `01:05-01:31`; no omitted vocals should be
  inferred there.
- Reprise/ending: slots 15-22, approximately `01:32-02:18`, with the final
  `rose` held into the fade.
- No vocal line should start after the `02:23.52` file end.

Text normalization:

- Ignore capitalization, punctuation, comma placement, and `Every day` versus
  `Everyday`.
- `La vie en rose` must be recognized as that phrase; ASR confusions such as
  `L'Aviaro's`, `love beyond all`, or unrelated substitutions are not correct.
- Slot 4 is canonically `heaven sighs`. `heaven size` / `heaven sides` may earn
  partial lyric credit only if the uncertainty note explicitly flags that word
  as uncertain; it is not a full-text match.
- Combining two adjacent slots into one LRC row earns text credit for the words
  but loses line-break and timing credit unless both starts are otherwise
  recoverable.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Output shape and LRC validity.** The main LRC exists, parses as LRC,
  has monotonically increasing `[mm:ss.xx]` or `[mm:ss]` timestamps, and
  contains at least 20 non-empty timed lyric rows. Metadata rows are allowed but
  ignored. Empty timed rows, duplicate timestamp rows, unsorted timestamps, or
  lyric starts beyond `02:23.52` reduce this line; a non-parseable LRC earns
  0.00 here.

- **0.30 - Lyric-slot accuracy.** Score the 22 locked slots in Section 4. Award
  `0.30 * correct_slots / 22` after text normalization. A slot is correct only
  when the expected lyric is present in the right order and not replaced by
  translation, wrong-language lyrics, ASR nonsense, or another song/version.
  Adjacent-line merges can count for lyric text but should still be penalized
  under output shape and timing.

- **0.15 - Structural coverage.** Full credit requires all major local-audio
  sections: opening verse slots 1-6, middle/bridge slots 7-14, the instrumental
  gap left without invented lyrics, and reprise/ending slots 15-22. Award
  0.05 for slots 1-6, 0.05 for slots 7-14, 0.04 for slots 15-22, and 0.01 for
  not filling the instrumental intro/break with hallucinated lyric rows.

- **0.25 - Local timestamp alignment.** Compare each emitted lyric slot to the
  local start anchors in Section 4, not to web, metadata, or another recording's
  timing.
  For each matched slot, give full timing credit if the start is within
  `1.25s`, half credit if within `2.50s`, and zero if farther away or if the
  line is matched only by order with no recoverable local start. This line is
  `0.25 * timing_points / 22`, capped at 0.15 for any output with a consistent
  section shift over `5s` after the first minute.

- **0.10 - Uncertainty and review note.** `song_uncertainty.md` exists and
  lists exactly 2-3 concrete uncertain spots with timestamps or line references.
  Full credit requires at least one spot from the chorus or reprise/ending, and
  the note must show the executor reviewed the final LRC rather than writing a
  generic disclaimer. Missing, generic, or overbroad notes receive little or no
  credit here.

- **0.10 - Source grounding and process honesty.** Visible trace and artifacts
  should show meaningful use of the local audio: playback, chunking, waveform or
  spectrogram inspection, local ASR with review, or equivalent local listening
  work. Do not award this line for outputs produced only from the filename,
  metadata, internet search, copied web lyrics, old memory, or the hidden
  reference file. This line also covers final-artifact hygiene: no unrelated
  source files, no translations, and no self-contradictory claims that the LRC
  is for a different recording.

Total: `0.10 + 0.30 + 0.15 + 0.25 + 0.10 + 0.10 = 1.00`.

## 6. Scoring Policy / Score Caps

Award rubric credit first, then apply all applicable caps with `min(score,
cap)`. Caps are intentionally strict so that artifact existence or polished
formatting cannot compensate for wrong local audio grounding.

- **Cap at 0.30 - No deliverables.** Neither an accepted main LRC nor an
  accepted uncertainty note exists in `/tmp_workspace/results/`.
- **Cap at 0.40 - Main LRC unusable.** The main LRC is missing, cannot be parsed
  as LRC, has non-monotonic timestamps that prevent lyric-player use, or has
  fewer than 8 non-empty timed lyric rows.
- **Cap at 0.45 - Wrong language or wrong song.** The output is primarily
  French, a translation, instrumental descriptions, another song, or unrelated
  text instead of the English local-audio lyrics.
- **Cap at 0.50 - Copied web/legacy lyrics not aligned to local audio.** The
  output visibly copies a web lyric page, a downloaded LRC/SRT, metadata-driven
  text, or another recording's timing without local re-timing. Indicators include
  long-version timestamps continuing toward `03:14`, the long-version reprise
  beginning near `02:01` with lines not audible at that point, or any lyric
  start after the shipped `02:23.52` audio ends.
- **Cap at 0.60 - External lyrics used despite some re-timing.** The trace shows
  internet/downloaded lyrics or old-memory lyrics were used as the primary
  source, even if the executor later adjusted some timestamps to the MP3.
- **Cap at 0.65 - Severe timestamp drift.** Median drift across matched slots is
  greater than `6s`, or at least two major sections are shifted by more than
  `8s`, making karaoke synchronization unreliable.
- **Cap at 0.70 - Major line omissions.** Fewer than 16 of the 22 locked lyric
  slots are present, or the output omits an entire major section such as the
  reprise/ending slots 15-22.
- **Cap at 0.75 - Wrong-version local structure.** The lyrics are mostly
  correct, but the structure follows a different recording: for example it
  invents first-reprise opening lines during the local instrumental break,
  misses the `01:31.9` reprise entry, or treats the shipped file as a longer
  rendition.
- **Cap at 0.80 - Missing uncertainty/review handling.** The uncertainty file is
  absent, or the final answer gives no evidence that the chorus and ending were
  reviewed after drafting the LRC.
- **Cap at 0.82 - Moderate timestamp drift.** More than 25% of matched slots are
  over `2.50s` from the local anchors, or one major section is consistently
  shifted by `4-8s`.
- **Cap at 0.84 - Weak uncertainty note.** The uncertainty file exists but is
  generic, lists fewer than 2 or more than 3 spots, lacks timestamps/line
  references, or does not include any chorus/reprise/ending review.
- **Cap at 0.88 - Minor omissions or hallucinated rows.** One or two locked
  lyric slots are missing, or the LRC includes one or two non-audible timed
  lyric rows such as an invented `00:00` lead-in. This can still pass only if
  the remaining content and timing are strong.

A run passes only if the capped score is `>= 0.90`.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** Stop only when the LRC covers the local
  22-slot structure, aligns to the shipped `02:23.52` MP3, includes the
  reprise/ending, and has a concrete 2-3 item uncertainty note.
- **Continue (`0.60 - 0.89` after caps).** Request a targeted follow-up when the
  run is recoverable, such as fixing drifted chorus/reprise timestamps, adding
  the missing uncertainty note, removing hallucinated intro/break lyrics, or
  filling a small number of omitted local-audio lines.
- **Fail (`< 0.60` after caps).** Do not spend further follow-ups on missing or
  unusable LRC output, wrong-language/wrong-song responses, copied web or
  non-local timing with no local synchronization, fewer than half the lyric slots,
  or timestamp drift so large that the result is not usable as an LRC.

If the raw rubric score and a cap disagree, the cap controls. If the executor's
visible process conflicts with the final artifact, grade the final artifact for
content/timing and the trace for source-grounding caps.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) - grading spec.
- `references/ground_truth.lrc` - canonical local lyric-order reference.
- `references/ground_truth.srt` - same canonical local lyric progression in SRT
  form.

## 9. Dynamic Content Note

Offline task. Do not use live web content or external song databases for ground
truth. If the on-disk MP3 duration or audible content ever differs from the
`143.52s` local-audio snapshot above, flag the fixture mismatch instead of
silently judging against a different recording.
