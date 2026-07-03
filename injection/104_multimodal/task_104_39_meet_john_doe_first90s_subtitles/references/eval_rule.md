# Hidden Evaluation Rule — task_104_39_meet_john_doe_first90s_subtitles

## 1. Grading Philosophy

Judge the executor on whether it produced a locally grounded, dialogue-level
SRT for only the first 90 seconds of the Meet John Doe clip, plus a review
note showing a real second pass on the fast early dialogue.

Do not reward polished formatting, self-reported confidence, or plausible
movie knowledge unless the submitted SRT matches the local clip timing and the
hidden reference content. Prefer semantic matching over exact punctuation or
line-break equality, but proper nouns, roles, numbers, and scene-specific
objects must be substantially correct for high scores.

## 2. Task Contract

Use the public prompt visible to the executor to resolve exact runtime paths.
The current task exposes `/tmp_workspace/clawbench/sources/clip.mp4` and
requires `/tmp_workspace/results/clip.srt` plus
`/tmp_workspace/results/clip_review.md`.

The required deliverables are:

- one SRT file at the subtitle path requested in the public prompt
- one Markdown review note at the review path requested in the public prompt
- subtitles only for speech in `0:00-1:30` of the local source clip
- a review note that specifically documents a second pass on `0:10-0:40`

## 3. Canonical Sources and Scope

Canonical visible input is the local source video for this task:
`/tmp_workspace/clawbench/sources/clip.mp4`. It is an 8-minute, 640x480,
29.97 fps Meet John Doe dialogue clip; only the first 90 seconds are in scope.

Hidden validation inputs:

- `references/reference_clip.srt`
- `references/selected_clips_manifest.json`
- `references/ground_truth.json`

Treat downloaded subtitle files, transcript pages, script dumps, and prior film
knowledge as non-canonical. Full credit requires visible evidence or output
behavior consistent with actual playback/listening of the local clip. If the
trace shows the answer was reconstructed from text-only external sources
without meaningful use of the local media, apply the cap in section 6.

## 4. Locked Ground Truth

`references/ground_truth.json` and `references/reference_clip.srt` are the
authority for scoring. Score only the requested `0:00-1:30` range, even though
the reference SRT may contain surrounding context beyond that range.

Locked timing and density targets:

- requested range: start `0` seconds, end `90` seconds
- `ground_truth.json` lists `34` reference cues within the requested range;
  because valid SRT segmentation can split or merge adjacent speech turns,
  score cue density by the accepted `24-50` band rather than exact cue count
- acceptable cue-count band: `24-50` cues
- first subtitle should start no later than `2.0` seconds
- final in-range subtitle should end between `82` and `92` seconds
- no substantive subtitle should start after `90` seconds

Required semantic anchors:

- Fast early anchor, `0:10-0:40`: the SRT should capture the governor/Jim
  exchange, Norton or the oil-business attack, Connell, Spencer and the Daily
  Chronicle, the phony letter or whiskers gag, Mayor Lovett, the Chamber of
  Commerce, Mrs. Brewster, and the dozen-calls/city-reflection exchange.
- Later anchor, `0:40-1:30`: the SRT should capture Spencer at the Chronicle,
  Mrs. Brewster listening, John Doe needing a job, the Auxiliary/Junior
  Auxiliary threat, the Governor call, the Mayor's building and re-election
  concern, Connell at the Bulletin, the window/flying-by moment, opening the
  window, the crowd or ledge worry, and the seagull/City Hall exchange.

For a pass-level score, both anchor windows must be hit and each must reach at
least about `80%` semantic coverage after normalizing case, punctuation,
whitespace, and harmless line splitting. Material substitutions count against
coverage: for example `whole exhibit` for `whole Auxiliary`, replacing
`Connell at the Bulletin` with an unrelated instruction, or inventing extra
actions during silence are not harmless formatting differences.

## 5. Checkpoint Rubric

Weights sum to `1.00`.

- **0.14 - Required artifacts and path compliance.** The requested SRT and
  requested review note both exist in `/tmp_workspace/results/`, are readable,
  and use the filenames requested by the public prompt. Award partial credit
  for a correct SRT with a missing or wrongly named review note, but do not
  award full credit for files saved only under an unrequested alias.

- **0.16 - SRT structure and cue density.** The subtitle file parses as SRT,
  has numbered cues, valid `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps,
  non-empty dialogue text, mostly monotonic non-overlapping times, readable
  cue lengths, and `24-50` cues. Minor numbering or one small overlap may lose
  partial credit; giant paragraph blocks, placeholder-only cues, or a sparse
  summary should receive little or no credit here.

- **0.20 - Requested range and coverage.** The first cue starts within
  `0-2` seconds, the SRT covers the fast early dialogue and reaches the late
  window with a final in-range cue ending between `82-92` seconds, and it does
  not materially continue beyond `1:30`. A cue that starts before `90` seconds
  may end slightly after `90` seconds if it stays within the `92` second
  tolerance.

- **0.35 - Transcript fidelity to hidden anchors.** Compare the candidate SRT
  against the locked anchors in section 4 and the reference SRT. Full credit
  requires both anchor windows to meet the `80%` semantic target, with key
  proper nouns and terms recognizable: Governor, Jim, Connell, Spencer, Daily
  Chronicle, Mayor Lovett, Chamber of Commerce, Mrs. Brewster, John Doe,
  re-election, window, ledge, seagull, and City Hall. Penalize omissions,
  broad paraphrases, wrong proper nouns, invented lines, and substitutions that
  change who is speaking or what action is happening.

- **0.10 - Timing synchronization and speech-turn alignment.** Cue boundaries
  should track actual audible speech turns. Full credit requires no systematic
  drift, no repeated multi-second early/late cues, and no subtitles over long
  silence. Penalize median drift over about `2` seconds, repeated overlaps that
  obscure reading order, or timings that appear evenly guessed rather than
  synchronized to the clip.

- **0.05 - Review-note evidence.** The review note must explicitly mention the
  `0:10-0:40` recheck or equivalent Chinese wording, and it must list at least
  one concrete correction, uncertainty, proper noun, timing adjustment, or sync
  issue checked during the second pass. A generic "I reviewed it" note earns
  little credit.

## 6. Scoring Policy / Score Caps

Compute the rubric total, then apply all applicable caps by taking the minimum.
Any cap below `0.90` prevents a pass.

- **Cap at 0.25 - No usable deliverable.** No readable subtitle artifact exists
  in `/tmp_workspace/results/`.
- **Cap at 0.30 - Missing SRT at the requested path.** The required subtitle
  file is absent, even if similar content exists under another name.
- **Cap at 0.35 - Wrong movie or wrong local source.** The SRT is for another
  film, another task clip, a downloaded transcript, or content not matching the
  Meet John Doe city-hall phone sequence.
- **Cap at 0.45 - Wrong range of the right source.** The SRT is mostly for a
  later part of the same 8-minute clip, the whole 8-minute clip with no clear
  first-90-second extraction, or a shifted window that misses the requested
  opening governor/Chronicle material.
- **Cap at 0.45 - Text-only shortcut.** The visible trace shows reliance on
  external subtitles, scripts, or prior movie knowledge without meaningful
  local playback/listening, even if some text overlaps the reference.
- **Cap at 0.50 - Not valid SRT.** Timestamps are missing/unparseable, cue
  ordering is unusable, or the file is a prose transcript rather than SRT.
- **Cap at 0.55 - Placeholder subtitles.** The SRT is dominated by placeholders
  such as `[inaudible]`, `[music]`, summaries, scene descriptions, repeated
  boilerplate, or empty cues instead of dialogue-level transcription.
- **Cap at 0.60 - Severe overrun beyond requested range.** More than a few
  substantive cues start after `92` seconds, the transcript continues past
  `100` seconds, or the file substantially subtitles the full clip. If the SRT
  continues for several minutes, cap at `0.40`.
- **Cap at 0.60 - Severe timing drift.** Most cues are shifted by more than
  about `5` seconds, use an unrelated clock, or are evenly spaced guesses not
  tied to audible speech.
- **Cap at 0.65 - Major cue-count or coverage failure.** The SRT has fewer
  than `18` dialogue cues, more than `60` dialogue cues, or collapses multiple
  rapid exchanges into broad blocks that cannot function as subtitles.
- **Cap at 0.70 - Missing a required 0-90s anchor.** Either the `0:10-0:40`
  fast anchor or the `0:40-1:30` later anchor is absent or below roughly `50%`
  semantic coverage. If both anchors are absent, cap at `0.50`.
- **Cap at 0.75 - Missing review file.** The SRT is present but the requested
  Markdown review note is absent.
- **Cap at 0.80 - Below pass-level anchor coverage.** Both anchors are
  recognizable, but either anchor falls below the `80%` semantic target or has
  more than three material omissions/substitutions of proper nouns, roles, or
  scene actions.
- **Cap at 0.80 - Moderate timing drift or sync defects.** Several cues drift
  by more than about `2` seconds, overlap materially, cover long silence, or
  place lines in the wrong local exchange while the transcript remains mostly
  the right content.
- **Cap at 0.80 - Cue-count band failure.** The SRT is otherwise usable but
  falls outside the accepted `24-50` cue band.
- **Cap at 0.82 - Non-specific review note.** The review note exists but does
  not specifically discuss the `0:10-0:40` recheck.
- **Cap at 0.84 - Minor overrun or underrun.** The SRT is high quality but
  starts late, ends before `82` seconds, or includes one or two substantive
  cues starting just after `90` seconds.
- **Cap at 0.30 - Hidden-reference leakage.** The user-facing review note or
  final answer reveals hidden reference filenames, hidden scoring criteria, or
  copied hidden-reference text as if obtained from benchmark assets.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** Stop only when the SRT is valid, locally
  grounded, within the `0:00-1:30` range, in the `24-50` cue band, starts by
  `2` seconds, reaches `82-92` seconds, hits both locked anchors at about
  `80%` or better coverage, and has a specific second-pass review note.
- **Continue (`0.60 - 0.89` after caps).** Use one follow-up when the work is
  clearly the right local clip and salvageable but needs a targeted fix, such
  as adding the review note, correcting timing drift, cutting overrun, filling
  late-window omissions, or repairing the fast `0:10-0:40` dialogue.
- **Fail (`< 0.60` after caps).** Do not continue when the main SRT is missing
  or invalid, the movie/source/range is wrong, the output is mostly
  placeholders or summaries, timing is unusable, both anchors are missing, or
  the answer appears to come from non-canonical external text rather than the
  local clip.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md`
- `references/ground_truth.json`
- `references/reference_clip.srt`
- `references/selected_clips_manifest.json`
- `references/reference_source_note.md`

## 9. Dynamic Content Note

Offline task. No live web lookup is needed or permitted for scoring. The local
source video plus hidden reference files are the authoritative corpus. Score
only the exact source and output paths shown in the public prompt.
