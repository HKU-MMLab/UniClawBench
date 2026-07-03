# Hidden Evaluation Rule — task_104_38_suddenly_first120s_subtitles

## 1. Grading Philosophy

Grade only the requested first `0:00-2:00` of the local `clip.mp4`. A high
score requires all three outcomes at once:

1. The exact requested deliverable exists at `/tmp_workspace/results/clip.srt`.
2. The file is a real, readable SRT whose timings stay inside the first
   120-second window.
3. The subtitle text matches the spoken content of the local clip, including
   the locked first-120s anchors below, rather than another movie, another
   section of the same movie, a downloaded script, placeholders, or a summary.

Polished formatting, agent self-reported confidence, or evidence of tool use
must not compensate for wrong source grounding, sparse transcript coverage, or
bad timing.

## 2. Task Contract

The user asked the executor to:

- open and actually watch/listen to
  `/tmp_workspace/clawbench/sources/clip.mp4`
- subtitle only `0:00-2:00` of that local video
- save the final standard SRT as `/tmp_workspace/results/clip.srt`
- split narration and long lines at natural pauses
- rewatch the first 120 seconds and directly fix long blocks, missing words,
  overlaps, and abnormal gaps in the final file

The requested output path is part of the contract. The supervisor may inspect
other `.srt` files under `/tmp_workspace/results/` only to diagnose content and
apply caps; an otherwise good subtitle under the wrong filename cannot pass.

## 3. Source-Selection and Target-Resolution Rules

Visible canonical input:

- `/tmp_workspace/clawbench/sources/clip.mp4`

Hidden validation inputs:

- `references/reference_clip.srt`
- `references/ground_truth.json`
- `references/selected_clips_manifest.json`

The canonical movie/clip is the `suddenly` entry in
`selected_clips_manifest.json`, corresponding to full-source seconds
`1140-1620`; this task evaluates only local clip seconds `0-120`. Other
manifest entries are distractors and are not acceptable sources.

Downloaded subtitle files, web transcript pages, script dumps, or prior film
knowledge are non-canonical. If visible trace shows the answer was built from
text-only external material without meaningful local playback/listening, apply
the text-only cap in §6 even if the wording resembles the film.

## 4. Locked Ground Truth

Use `references/ground_truth.json` and `references/reference_clip.srt` as the
authoritative answer. For the requested window:

- source file: `clip.mp4`
- requested range: start `0.000s`, end `120.000s`
- reference cue set: non-empty `reference_clip.srt` cues that start before
  `120.000s`
- reference cue count within range: 55
- accepted candidate cue-count band for pass eligibility: 35-70
- first cue start must be `<= 2.000s`
- final in-range cue should end between `110.000s` and `123.000s`
- no candidate cue should start after `120.000s`; a cue that starts before
  `120.000s` may end no later than `123.000s`

Normalize text for grading by lowercasing, ignoring punctuation, accepting
minor contractions and speaker-label changes, and allowing close ASR-style
variants that preserve the same meaning. Do not give credit for reordered
dialogue, invented names, scene summaries, or generic descriptions standing in
for spoken words.

First-120s anchors are mandatory high-score checks. A pass requires at least
80% semantic coverage in each anchor, in the correct order and within the
listed timing neighborhood:

- **Anchor A, opening TV-repair setup (`0:00-0:20`)**: Ohm's law / Ellen;
  Pidge missing the ball game after the movie; getting ready to plug in the
  set while a screw is held down; the "OK" response; concern about 5,000 volts
  being dangerous; the admonition to Ellen.
- **Anchor B, electricity and wall-plug warning (`0:35-1:10`)**: call Jud;
  close call; how much 5,000 volts is; enough to kill or throw someone across
  the room; puddle/grounded explanation; "dead as a doornail"; "like blazes";
  stay away from the set and wall plugs; do not monkey with electricity unless
  you know what you are doing; "Why did you, Grandpa?"
- **Anchor C, FBI arrival (`1:15-2:00`)**: Mrs. Benson / husband / widow;
  owner of the house / father-in-law; John Baron as special agent; Federal
  Bureau of Investigation / F.B.I.; these are his men; request to speak with
  Mr. Benson; invitation into the house; Mr. Benson greeting the men; "come
  right in" / make yourselves at home; Treasury Department / old days exchange.

All three anchor windows in `ground_truth.json` are compulsory so that a
candidate cannot pass while omitting the opening, electricity warning, or FBI
arrival portions of the requested range.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit inside a line only when the described
thresholds are met after the §4 normalization; then apply all caps in §6.

- **0.10 — Exact deliverable.** Full credit only if
  `/tmp_workspace/results/clip.srt` exists and is the final subtitle file.
  Give 0.00 for this line if only a differently named SRT exists.

- **0.15 — Standard SRT validity and readability.** Cues must parse as
  numeric SRT entries with `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps,
  monotonically increasing times, non-empty dialogue text for speech cues, no
  material overlaps, and readable segmentation. Full credit requires most cues
  to be 1-2 text lines, no routine line longer than about 90 characters, and no
  routine cue longer than 7 seconds. Zero this line if the file is not
  parseable as SRT.

- **0.15 — Requested range and cue coverage.** Full credit requires all of:
  cue count in the 35-70 band, first cue start `<= 2.000s`, final in-range cue
  end `110.000-123.000s`, no cue start after `120.000s`, and no large silent
  gaps where reference speech exists. Give at most half of this line for cue
  counts of 30-34 or 71-80, or for final coverage ending between 90 and 110
  seconds. Give 0.00 if the subtitle covers less than 75 seconds of the
  requested range or mostly covers a different range.

- **0.15 — Timing synchronization.** Align candidate cues to the non-empty
  in-range reference cues by order and nearby text. Full credit requires median
  start/end drift `<= 1.0s` and 90th-percentile drift `<= 2.5s`, with no
  anchor window systematically shifted. Award at most half credit when median drift is
  `<= 2.0s` and 90th-percentile drift is `<= 4.0s`. Give 0.00 when the SRT is
  globally offset, repeatedly early/late by more than 5 seconds, or impossible
  to align to the reference.

- **0.35 — Transcript fidelity and anchors.** Award 0.20 for global dialogue
  coverage across the non-empty in-range reference cues: full credit for at
  least 85% of the spoken content units in order, about half credit for
  70-84%, and 0.00 below 60%. Award the remaining 0.15 as 0.05 per locked anchor A/B/C: full anchor
  credit requires at least 80% semantic coverage inside that anchor, half
  anchor credit requires 60-79%, and 0.00 below 60%. Dialogue that belongs to a
  different scene or movie earns no fidelity credit even if it is fluent SRT.

- **0.10 — Local-source discipline and cleanup.** Full credit requires visible
  evidence of using the local clip/audio/video for transcription or review, and
  a final file without placeholder subtitles, scene summaries, invented
  speaker identities, repeated draft fragments, abnormal overlaps, or obvious
  second-pass cleanup failures. Incidental bracketed sound effects may be
  acceptable only when they describe actual non-speech audio and do not replace
  spoken dialogue.

Total: `0.10 + 0.15 + 0.15 + 0.15 + 0.35 + 0.10 = 1.00`.

## 6. Scoring Policy / Score Caps

Compute the rubric score first, then apply every applicable cap by taking the
minimum. If any cap below 0.90 applies, the run cannot pass.

- **Cap at 0.25 — No usable subtitle deliverable.** No SRT-like file exists in
  `/tmp_workspace/results/` or the result directory is missing.

- **Cap at 0.80 — Wrong output path.** A usable SRT exists under
  `/tmp_workspace/results/`, but the final requested
  `/tmp_workspace/results/clip.srt` is absent.

- **Cap at 0.50 — Not valid SRT.** The output is a plain transcript, markdown,
  JSON, empty file, or otherwise not parseable as standard SRT.

- **Cap at 0.45 — Wrong movie, wrong source, or wrong range.** The dialogue is
  mostly from another movie, another scene, a different part of `Suddenly`, or
  a web/script source rather than the local clip seconds `0-120`. This cap also
  applies when all mandatory `ground_truth.json` anchor windows are absent.

- **Cap at 0.65 — Cue-count or coverage failure.** Cue count is below 30 or
  above 80, first cue starts after 5 seconds, final coverage ends before 100
  seconds, or large blocks of reference speech are missing even though the
  candidate is from the right clip.

- **Cap at 0.55 — Severe cue-count or coverage collapse.** Cue count is below
  20 or above 100, first cue starts after 10 seconds, final coverage ends
  before 75 seconds, or more than half of the requested range has no usable
  transcript where the reference contains speech.

- **Cap at 0.84 — One first-120s anchor below pass level.** Exactly one locked
  anchor A/B/C has less than 80% semantic coverage but at least 60% coverage.
  This marks a near-miss as Continue, not Pass.

- **Cap at 0.70 — Missing first-120s anchors.** Any locked anchor A/B/C is
  below 60% semantic coverage, or two anchors are below the 80% pass level.

- **Cap at 0.55 — Anchor collapse.** Two or more locked anchors are below 60%
  semantic coverage, or the electricity/wall-plug anchor and FBI-arrival anchor
  from `ground_truth.json` are both effectively missing.

- **Cap at 0.80 — Noticeable timing drift.** Median aligned cue drift is over
  2 seconds, 90th-percentile drift is over 4 seconds, or an anchor window is
  consistently early/late enough that subtitles would visibly distract.

- **Cap at 0.65 — Severe timing drift.** The subtitle file has a systematic
  offset over 5 seconds, repeated overlaps/gaps that break viewing, or anchor
  dialogue placed more than 8 seconds from the matching reference window.

- **Cap at 0.60 — Placeholder or summary subtitles.** More than 20% of cues
  are placeholders such as `[inaudible]`, `[music]`, "dialogue continues", or
  broad scene summaries, or placeholders replace spoken dialogue in any locked
  anchor.

- **Cap at 0.40 — Mostly placeholder output.** The file is primarily
  placeholders, descriptions, or summaries with little actual transcribed
  dialogue.

- **Cap at 0.80 — Minor overrun beyond requested range.** Any cue starts after
  `120.000s`, or a cue that starts before 120 seconds ends after `123.000s`,
  but the overrun is brief and not a substantial continuation.

- **Cap at 0.60 — Substantial overrun beyond requested range.** Multiple cues
  start after `120.000s`, any cue extends past `130.000s`, or more than 10% of
  subtitle text belongs after the requested 2-minute cutoff.

- **Cap at 0.45 — Major overrun / full-clip transcription.** The output
  continues past `150.000s`, covers a large portion of the 8-minute clip, or
  ignores the 0:00-2:00 range constraint.

- **Cap at 0.45 — Text-only reconstruction.** Visible trace shows no
  meaningful local playback/listening or local audio/video processing, and the
  transcript appears reconstructed from external subtitles, scripts, or film
  knowledge.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) — stop only when the exact `clip.srt` exists,
  all caps are clear, all locked anchors meet the 80% threshold, cue coverage
  is in range, timing is synchronized, and there is no material overrun.
- **Continue** (`0.60 - 0.89` after caps) — the output is salvageable but needs a
  specific repair, such as the exact filename, one weak anchor, sparse cue
  coverage, timing drift, cleanup of placeholders, or a small cutoff problem.
- **Fail** (`< 0.60` after caps) — no further repair should be requested for
  wrong movie/source/range, anchor collapse, severe coverage failure, invalid
  SRT, mostly placeholder output, major overrun, or no usable deliverable.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file)
- `references/ground_truth.json`
- `references/reference_clip.srt`
- `references/selected_clips_manifest.json`

## 9. Dynamic Content Note

Offline task. The local video and hidden references are static. If the on-disk
clip, `ground_truth.json`, and `reference_clip.srt` ever disagree, treat the
hidden reference files as authoritative for grading and flag the mismatch
rather than searching the web or inferring a new answer.
