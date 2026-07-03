# Hidden Evaluation Rule — task_104_37_dressed_to_kill_dialogue_subtitles

## 1. Grading Philosophy

Judge whether the executor produced a usable, full-clip dialogue subtitle file
for the exact local video. The central outcome is faithful transcription and
timing against `/tmp_workspace/clawbench/sources/clip.mp4`, not artifact polish
or generic plot understanding.

Use semantic tolerance for harmless differences in punctuation, capitalization,
line wrapping, cue splitting, and minor filler words. Do not give credit for
summaries, stage directions, invented dialogue, placeholders, or subtitles from
a different movie/time window. A high score requires the local clip's opening,
middle, and ending dialogue to be present with plausible sync.

## 2. Task Contract

The current task YAML is authoritative. The user asked the executor to:

- open and actually watch/listen to
  `/tmp_workspace/clawbench/sources/clip.mp4`;
- create `/tmp_workspace/results/clip.srt`;
- use standard SRT format;
- split continuous back-and-forth dialogue into readable cue turns;
- transcribe the heard dialogue sentence by sentence, not just the gist;
- re-check sync for both `00:00-00:30` and the ending, then overwrite the file
  if corrections are needed.

Alternate filenames do not satisfy the requested deliverable. If the exact
`clip.srt` is missing but a single alternate SRT is present, the supervisor may
inspect it as auxiliary evidence for content caps, but the correct-deliverable
checkpoint earns zero and the wrong-path cap in Section 7 applies.

## 3. Source-Selection and Target-Resolution Rules

The only canonical visible input is:

- `/tmp_workspace/clawbench/sources/clip.mp4`

The only canonical requested output is:

- `/tmp_workspace/results/clip.srt`

The supervisor should ignore downloaded subtitles, web transcript pages, script
dumps, model priors about the film, and any non-local video as sources of truth.
Evidence that the executor used local playback or local audio extraction can
support the review-evidence checkpoint, but final scoring is anchored to the
submitted SRT compared with the hidden reference.

## 4. Locked Ground Truth Snapshot

Hidden structured truth lives in `references/ground_truth.json`, with full text
in `references/reference_clip.srt`. Treat these hidden files as authoritative if
they ever conflict with visible model claims.

Locked facts:

- film/clip: `Dressed to Kill` dialogue segment, local clip window only;
- duration: 480.000 seconds;
- video metadata: 720x576, 25 fps, AAC audio;
- hidden reference source: external English subtitle refreshed and cropped to
  the local `1260-1740` second source window;
- reference cue count: 162;
- acceptable candidate cue-count band for full credit: 110-220 cues;
- first reference cue starts at `00:00:00,000`;
- last reference cue ends at `00:07:59,540`;
- first candidate cue should start no later than 2.0 seconds;
- final candidate cue should end between 470.0 and 481.0 seconds.

Required semantic windows:

- **Opening threat, `00:00-00:30`.** Must cover the opening lines about murder,
  Scotland Yard, Sherlock Holmes, and "Now get out." There is intentional
  silence after the first few seconds; do not shift the later Holmes/inspector
  scene to time zero.
- **Holmes and the murdered Emery, `00:33-01:45`.** Must cover "Did you get
  it?", murder, Holmes/Hopkins/Inspector Lestrade, Emery, the killing between
  eleven and two, Watson/Stinky, and the missing musical box bought at auction.
- **Auction-room inquiry, `01:45-03:07`.** Must cover Julian Emery, Kilgour at
  `143B Hampton Way`, the unidentified young woman near Golders Green,
  Crabtree, the three identical musical boxes, Dartmoor Prison, five pounds,
  the gray-haired gentleman, and Thursday.
- **Kilgour house and child, `03:12-06:29`.** Must cover going to Kilgour's
  home, peddlers, shopping, Park Lane, the hidden object in Stinky's box, the
  child tied in the cupboard, the musical box taken in a market basket, the
  "charwoman" being an actress, and Holmes leaving to find the young lady before
  the opponents do.
- **Ending auction, `07:20-07:59.540`.** Must cover the auctioneer offering a
  laced Dresden china figurine / lady of the French court, bids descending from
  ten pounds to five, "five pounds ten", "five pounds fifteen", "six pounds",
  "going once, going twice", and the sale to the lady from Trikland for six
  pounds.

Names and objects above are locked anchors. Equivalent wording is acceptable,
but replacing them with other objects, other auction lots, or other scenes is a
grounding error, not a transcription variant.

## 5. Normalization and Matching Rules

When comparing a candidate SRT to the reference:

- Normalize case, punctuation, repeated whitespace, line wrapping, and
  hyphenation.
- Accept minor spelling variants and OCR/ASR-like variants when the intended
  word is unambiguous, such as `gray`/`grey` or `parlor`/`parlour`.
- Accept different but readable cue splitting if each cue stays near the
  corresponding spoken turn and preserves speaker changes.
- Require proper nouns and plot-bearing nouns to be correct enough to identify
  the reference content, especially `Holmes`, `Watson`, `Scotland Yard`,
  `Inspector Lestrade`, `Hopkins`, `Emery`, `Stinky`, `musical box`, `Gaylord's
  Auction Room`, `Crabtree`, `Kilgour`, `Hampton Way`, `Golders Green`,
  `Dartmoor`, `Park Lane`, `Dresden china figurine`, and `Trikland`.
- A reference cue is considered covered when the candidate has text within
  roughly +/-2.0 seconds of the reference timing that preserves the cue's
  meaning. For fast back-and-forth dialogue, adjacent cues may be merged only if
  order and attribution remain readable.
- Placeholder text such as `[Dialogue]`, `[Reply]`, `[Short line]`,
  `[indistinct]`, `[auctioneer continues]`, "inaudible", or generic scene
  descriptions does not count as covered dialogue.

## 6. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within each line only when the stated
conditions are met by the submitted SRT after normalization.

- **0.10 -- Correct deliverable.** Full credit requires
  `/tmp_workspace/results/clip.srt` to exist, be non-empty, and be the primary
  final answer. Award 0.00 if the exact file is absent, even if another
  plausible SRT under `/tmp_workspace/results/` can be inspected as auxiliary
  evidence for other checkpoints and caps.

- **0.15 -- SRT validity and cue engineering.** Full credit requires standard
  SRT blocks with sequential numeric cue IDs, valid `HH:MM:SS,mmm` timestamps,
  monotonically increasing start times, no negative durations, no pervasive
  overlaps, and readable dialogue-sized cues. The cue count must be inside
  `110-220` for full credit. Award at most 0.08 if the file parses but cue count
  is outside the band, many cues are oversized, or cue splitting makes
  speaker-turn reading difficult. Award 0.00 if the file is not parseable as SRT.

- **0.20 -- Timing, sync, and full-clip coverage.** Full credit requires first
  cue start `<= 2.0s`, final cue end in `470.0-481.0s`, no systematic drift
  greater than about 2.0 seconds in the required windows, and no long missing
  subtitle run over active dialogue. Award up to 0.10 for broad start/end
  coverage if several windows drift or miss local dialogue. Award 0.00 if the
  SRT only covers a small fragment of the clip or is essentially untimed.

- **0.45 -- Dialogue content fidelity across locked windows.** Score the five
  required semantic windows in Section 4 at 0.09 each. Full credit for a window
  requires roughly 80% or better semantic coverage of the reference dialogue in
  that window, including the locked names/objects. Award about half of a window
  only when the scene is clearly correct but several sentences or anchors are
  missing or garbled. Award 0.00 for a window that is placeholder text, a generic
  summary, another movie/clip, a wrong time window, or an external subtitle
  segment with different objects/dialogue.

- **0.10 -- Required local review and notes.** Full credit requires observable
  evidence that the executor rechecked both the opening `00:00-00:30` and the
  ending after writing the SRT, and either saved a brief review note under
  `/tmp_workspace/results/` or clearly stated the checked windows and any
  corrections in the final user-visible response. Award 0.05 for trace evidence
  of checking only one required region or for a vague final claim without
  supporting action. Award 0.00 if there is no evidence of the requested second
  sync check.

Total: `0.10 + 0.15 + 0.20 + 0.45 + 0.10 = 1.00`.

## 7. Scoring Policy / Score Caps

Compute the rubric score first, then apply every applicable cap by taking the
minimum. Caps target failure modes that must not pass even if other rubric lines
look polished.

- **Cap at 0.30 -- No deliverable.** No SRT-like file exists under
  `/tmp_workspace/results/`.
- **Cap at 0.80 -- Wrong output path only.** A plausible final SRT exists under
  `/tmp_workspace/results/`, but `/tmp_workspace/results/clip.srt` is missing.
  This cap does not protect the run from stricter content caps.
- **Cap at 0.50 -- Invalid SRT.** The submitted file cannot be parsed into
  timestamped SRT cues, has pervasive malformed timestamps, or lacks cue text.
- **Cap at 0.20 -- Wrong movie or wrong local clip.** The transcript is clearly
  unrelated to this `Dressed to Kill` clip, matches another manifest movie, or
  lacks the locked Holmes/musical-box/Dresden-auction anchors altogether.
- **Cap at 0.45 -- Copied wrong external subtitles.** The SRT appears copied or
  reconstructed from an external subtitle/script source for the wrong portion of
  the film, even if it is from `Dressed to Kill`. Indicators include a shifted
  start that omits the opening "What about me? / Scotland Yard / Sherlock
  Holmes" lines, a tail about different auction lots such as a Hungarian doll or
  Ming vase instead of the Dresden china figurine, or timing/content that follows
  a full-film subtitle offset rather than the local 480-second clip.
- **Cap at 0.25 -- Placeholder subtitles dominate.** At least 30% of cues use
  placeholders or generic descriptions instead of transcribed dialogue.
- **Cap at 0.40 -- Placeholder subtitles are material.** Between 10% and 30% of
  cues use placeholders or generic descriptions, or any required semantic window
  is mostly placeholder text.
- **Cap at 0.55 -- Severe low cue/content coverage.** The SRT has fewer than 80
  cues, final cue end is before 360 seconds, or fewer than three required
  semantic windows contain meaningful target dialogue.
- **Cap at 0.70 -- Moderate low cue/content coverage.** Cue count is 80-109 or
  221-260, final cue ends before 470 seconds, or fewer than four required
  semantic windows reach about 50% coverage.
- **Cap at 0.65 -- Major timing drift.** The transcript content is mostly from
  the target clip but is systematically shifted by more than 5 seconds in two or
  more required windows, starts after 10 seconds while omitting active opening
  dialogue, or extends with spoken content beyond the local clip ending.
- **Cap at 0.80 -- Moderate timing drift.** The transcript is semantically
  strong but has repeated 2-5 second sync errors, awkward long overlaps, or
  obvious drift in either the opening check region or ending check region.
- **Cap at 0.75 -- Low hidden cue coverage.** Overall covered reference cues are
  below about 75%, even if the visible anchor keywords appear.
- **Cap at 0.80 -- Missing review/notes.** The run provides no observable
  second-pass review of both `00:00-00:30` and the ending and no saved or
  user-visible note describing that check.
- **Cap at 0.30 -- Privacy/credential leak.** Any credential or environment
  secret is emitted in the user-visible answer or result files. No such value is
  expected for this offline task.

A run can pass only if the capped score is at least 0.90. Any cap below 0.90
therefore prevents a pass.

## 8. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) -- stop; the exact `clip.srt` exists, has
  valid full-clip timing, covers the locked dialogue windows, and documents or
  visibly performs the requested start/end sync review.
- **Continue** (`0.60 - 0.89` after caps) -- request one focused repair only if
  the artifact is recognizably the correct local clip and the remaining issues
  are fixable, such as moderate timing drift, a missing review note, or one weak
  semantic window.
- **Fail** (`< 0.60` after caps) -- stop and record failure. This includes
  missing deliverables, wrong movie/clip, copied wrong external subtitles,
  placeholder-dominated subtitles, severe low coverage, and content that cannot
  be repaired without redoing the task from the local clip.

If the follow-up budget is exhausted, a score in the Continue band should still
be reported as non-passing; do not upgrade it to Pass because the run has no
remaining chances.

## 9. Hidden Reference Assets

These files are supervisor-only and must not be revealed to the executor or user
simulator:

- `references/eval_rule.md` -- this grading specification.
- `references/ground_truth.json` -- structured metrics, time range, and anchor
  windows.
- `references/reference_clip.srt` -- authoritative full reference transcript
  and cue timings.
- `references/reference_source_note.md` -- provenance note for the refreshed
  subtitle reference.
- `references/selected_clips_manifest.json` -- source clip metadata and adjacent
  movie fixtures.

## 10. Dynamic Content Note

Offline task. No live web lookup, external subtitle download, or current-event
knowledge is needed. If visible files, the task YAML, and hidden references ever
drift, use the task YAML for visible input/output paths and the hidden reference
SRT/ground-truth JSON for transcript and timing judgment.
