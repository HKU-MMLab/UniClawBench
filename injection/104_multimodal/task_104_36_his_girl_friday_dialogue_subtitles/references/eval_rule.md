# Hidden Evaluation Rule — task_104_36_his_girl_friday_dialogue_subtitles

## 1. Grading Philosophy

Judge the executor on whether it produced a dense, synchronized dialogue SRT
for the local 8-minute clip and a real first-minute review note. This is a
local-video transcription task, not a search task. Exact punctuation and minor
line breaks are not important, but the subtitles must preserve the spoken
dialogue, character names, scene events, and timing of the provided
`clip.mp4`.

Do not give pass credit for polished files that are the wrong clip, generic
summaries, placeholder subtitles, or copied subtitles from the wrong time range.
Self-reported confidence or a detailed notes file cannot compensate for sparse
dialogue coverage, wrong transcript content, or unsynchronized cues.

## 2. Task Contract

The public task asks the executor to open and actually watch/listen to:

- `/tmp_workspace/clawbench/sources/clip.mp4`

The required final deliverables are exactly:

- `/tmp_workspace/results/clip.srt`
- `/tmp_workspace/results/clip_notes.md`

The executor must create standard SRT subtitles for the whole clip, split by
actual speech rather than giant blocks, then rewatch the first 60 seconds and
fix any sync issues directly in the SRT. The notes file must state what was
reviewed, with special attention to the first 60 seconds.

If an obvious misnamed SRT or notes file is present in `/tmp_workspace/results/`
or the visible result directory, the supervisor may inspect it for content
scoring and feedback. However, missing the exact requested path receives no
output-path credit and triggers the path cap in Section 6.

## 3. Source-Selection and Target-Resolution Rules

Canonical task input is only the local video `sources/clip.mp4`. Hidden
references are for supervision only and must not be surfaced to the executor:

- `references/reference_clip.srt`
- `references/ground_truth.json`
- `references/selected_clips_manifest.json`
- `references/reference_source_note.md`

The hidden manifest locks the clip as `His Girl Friday`, local duration about
480.013 seconds, resolution 640x480, from source window 3840-4320 seconds. Do
not accept subtitles for another public-domain movie task, another His Girl
Friday segment, the full movie without cropping, or a downloaded subtitle file
that is not aligned to this local clip.

## 4. Locked Ground Truth Snapshot

The reference subtitle file has 175 cues. A normal accepted candidate should
have 120-230 real dialogue cues, start within the first 2.0 seconds, and end
between 470 and 481 seconds. Bracketed labels such as `[rapid overlapping
dialogue]`, `[inaudible]`, or `[dialogue continues]` are not real dialogue cues.

Semantic matching is judged against `references/reference_clip.srt`. Paraphrase
is acceptable only when it preserves who said what and the plot meaning. The
supervisor should score content by time window and may use these locked anchor
facts:

- `00:00-01:30`: reporters discuss Williams, the roof, drainpipe/windows, the
  story walking in the window, Mollie, how Williams got the gun, Bruce's money,
  Mrs. Baldwin calling the men murderers, and Mollie saying she knows where
  Williams is before jumping.
- `01:30-03:15`: the jump/ambulance aftermath, Williams hidden in the desk,
  Bruce's mother, Louie Peluso taking her away, Hildy trying to get Bruce out of
  jail, and Walter arguing this is war while "Earl Williams captured by the
  Morning Post" is the story.
- `03:15-06:00`: Walter's career pitch covers Livingston/Stanley, La Guardia,
  exposing/crucifying the ward heelers, a Hildy Johnson cigar, moving Williams
  in the desk with pulleys, calling Duffy, ignoring the European war, Bruce
  returning from jail after wiring Albany for $100, and the money/wallet/check
  confusion.
- `06:00-08:00`: Bruce and Hildy argue over the 9 o'clock train, whether Hildy
  wants to leave, Walter calling Bruce a spy, the "biggest thing in my life"
  exchange, icebox/love accusations, Hildy choosing newspaperman identity over
  suburban life, the mock turtle line, and Butch being needed as a matter of
  life and death.

For a high score, the candidate must capture at least 85% of meaningful spoken
content overall and at least 75% in every window above. A run cannot pass if
any major window is missing, replaced by placeholders, or mostly wrong even if
the file structure is valid.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within a line only when the described
standard is materially satisfied.

- **0.10 - Required deliverables at exact paths.** Full credit requires both
  `/tmp_workspace/results/clip.srt` and `/tmp_workspace/results/clip_notes.md`.
  If equivalent but misnamed files exist, score this line 0.00 and apply the
  path cap, while still inspecting them for the other lines.

- **0.15 - SRT structure and readability.** The SRT parses as numbered cues
  with valid `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps, monotonic cue order,
  no negative durations, no substantial overlaps, readable cue lengths, and no
  collapse into a few huge blocks. Full credit also requires 120-230 real
  dialogue cues. Zero this line if the file is not recognizable as SRT.

- **0.15 - Full-clip timing coverage and synchronization.** Full credit
  requires first cue start `<= 2.0s`, last cue end in `470-481s`, no omitted
  speech-heavy span longer than 30 seconds, and spot-checked cue starts within
  about 1.5 seconds of the matching speech in the opening, middle, and late
  portions. Minor local drift is acceptable only if it is corrected and does
  not persist.

- **0.40 - Dialogue content fidelity.** Score 0.10 for each locked window in
  Section 4. A window earns 0.10 when it captures at least about 80% of the
  spoken content and all listed anchor facts; 0.05 when it captures 50-79% or
  misses one important anchor; 0.00 when it is below 50%, mostly placeholders,
  generic summaries, wrong speaker/action content, or from the wrong scene.

- **0.10 - Local-source grounding and no copied wrong text.** Full credit
  requires visible evidence or artifact metadata consistent with playback,
  listening, extraction, or manual checking of the local video. Zero this line
  if the trace shows reliance on downloaded subtitles, script pages, prior film
  knowledge, or another clip without meaningful local verification.

- **0.10 - First-60-second review note quality.** Full credit requires
  `clip_notes.md` to state that the first 60 seconds were reviewed and to
  mention at least one concrete sync, timing, segmentation, or correction focus.
  Accept Chinese or English wording such as `前60秒`, `60 秒`, `0:00-1:00`,
  `first 60 seconds`, `reviewed`, `sync`, `timing`, `复核`, `校对`, `修正`,
  `时间轴`, or `同步`. A generic note that does not mention the first minute
  earns at most 0.04 on this line.

## 6. Scoring Policy / Score Caps

Compute the rubric total from Section 5, then apply every applicable cap by
`min(raw_score, cap1, cap2, ...)`. Caps target severe failures and override
otherwise good formatting.

- **Cap at 0.20 - No primary subtitle deliverable.** No SRT-like subtitle file
  is present anywhere in the expected results/visible result area.

- **Cap at 0.30 - Not recognizable as SRT.** The main subtitle artifact cannot
  be parsed as SRT, has no timestamped cues, or is a prose transcript only.

- **Cap at 0.80 - Wrong output paths only.** The content may be inspectable,
  but the required `clip.srt` or `clip_notes.md` exact path is missing and only
  misnamed equivalents were saved.

- **Cap at 0.25 - Wrong movie or wrong clip.** The subtitles are clearly for
  another movie, another Clawbench subtitle task, the full movie opening, or a
  His Girl Friday segment other than the 3840-4320 second local window.

- **Cap at 0.35 - Copied wrong external subtitles.** The content appears copied
  from an external subtitle/script source but is shifted to the wrong time
  range, contains unrelated scenes, or is not aligned to the local clip.

- **Cap at 0.45 - Text-only reconstruction without local verification.** Trace
  shows no meaningful playback, audio extraction, frame/video inspection, or
  local timing work, even if the text looks plausible.

- **Cap at 0.35 - Placeholder subtitles.** More than 10% of cues, more than 30
  seconds of runtime, or any entire anchor window is represented by placeholders
  such as `[rapid overlapping dialogue]`, `[inaudible]`, `[music]`, or
  `[dialogue continues]` instead of actual spoken words.

- **Cap at 0.55 - Low cue coverage.** The SRT has fewer than 80 real dialogue
  cues, covers less than half of the clip's spoken content, or omits two or
  more locked windows.

- **Cap at 0.75 - Marginal cue coverage.** The SRT has 80-119 real dialogue
  cues, misses one locked window, or consists mostly of broad paraphrases rather
  than subtitle-level dialogue.

- **Cap at 0.84 - Cue density outside accepted band.** The SRT has fewer than
  120 or more than 230 real dialogue cues, but otherwise contains substantial
  local transcription. This prevents a pass for sparse or excessively fragmented
  subtitles that still need repair.

- **Cap at 0.65 - Material timing drift.** A sustained offset greater than 5
  seconds affects any speech-heavy span of at least 60 seconds, the first-minute
  sync is visibly wrong, cue order drifts relative to speakers, or many cues
  appear before/after the corresponding speech.

- **Cap at 0.45 - Severe timing drift or wrong offset.** The subtitles are
  globally shifted by more than 15 seconds, are timed for another source file,
  or cannot be matched to the local clip timeline.

- **Cap at 0.60 - Major tail omission.** Final meaningful cue ends before
  450 seconds, or the final Bruce/Hildy/Walter portion from about 6:00-8:00 is
  missing.

- **Cap at 0.80 - Missing review note.** No notes file exists at the required
  path or as an obvious equivalent.

- **Cap at 0.84 - Missing first-minute review evidence.** A notes file exists,
  but it does not state that the first 60 seconds/opening minute was reviewed
  for sync or timing.

- **Cap at 0.70 - Semantic shortfall.** The candidate hits some anchor topics
  but falls below 85% overall dialogue coverage or below 75% in any locked
  window.

- **Cap at 0.50 - Low semantic fidelity.** Two or more locked windows score
  0.00 for content fidelity, or many lines preserve names but change the actual
  dialogue/action enough to misrepresent the scene.

- **Cap at 0.30 - Hidden-reference leak.** The user-facing notes or final
  answer reveal hidden reference file contents, hidden scoring details, or
  supervisor-only paths as if copied from the benchmark references.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** Stop only when the exact requested files
  exist, the SRT is dense and synchronized for the whole local clip, the locked
  dialogue windows are all substantially correct, and no cap below 0.90 applies.

- **Continue (`0.60 - 0.89` after caps).** Use a follow-up when the output is
  recognizably for the correct clip but needs repair, such as renaming to exact
  paths, fixing first-minute sync drift, replacing sparse/mistranscribed
  dialogue, reducing over-fragmentation, adding the review note, or completing a
  missing window.

- **Fail (`< 0.60` after caps).** Do not continue when the main SRT is missing,
  malformed, mostly placeholders, the wrong movie/clip, copied from the wrong
  external subtitle range, severely mistimed, or too sparse to repair with one
  normal follow-up.

If follow-up budget is exhausted, record the final capped score and do not mark
the run as pass unless it is at least 0.90 after all caps.

## 8. Hidden Reference Assets

These files are supervisor-only:

- `references/eval_rule.md`
- `references/ground_truth.json`
- `references/reference_clip.srt`
- `references/reference_source_note.md`
- `references/selected_clips_manifest.json`

## 9. Dynamic Content Note

Offline task. No live web lookup is needed or expected. The local `clip.mp4`
and hidden `reference_clip.srt` are authoritative. If a downloaded subtitle or
script conflicts with the local clip timing, grade against the local clip and
apply the external-subtitle caps above.
