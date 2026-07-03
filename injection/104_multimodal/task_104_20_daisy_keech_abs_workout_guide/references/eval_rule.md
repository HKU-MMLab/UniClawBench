# Hidden Evaluation Rule — Daisy Keech Abs Workout Guide

## 1. Grading Philosophy

Judge the executor on whether it actually reconstructed the locked Daisy Keech
timer-edit workout from video evidence, not whether it produced a plausible ab
routine. A passing answer must deliver the requested markdown guide and
exercise frames, identify the correct source relationship, recover the
canonical move order, preserve the one-minute timer-circuit structure, and
ground the guide in real saved frames.

Prefer semantic movement matching over exact spelling, but do not let generic
fitness knowledge compensate for missing source grounding, missing canonical
slots, bad order / timing, or thumbnail-only visual evidence.

## 2. Task Contract

The public task asks the executor to find and watch the YouTube video titled:

`Daisy Keech hourglass abs workout but just the exercises (with timer and breaks)`

Required outputs:

- `/tmp_workspace/results/abs_workout_guide.md`
- one or more image files under
  `/tmp_workspace/results/abs_workout_frames/`

The guide must include:

- the target video identity and, if applicable, the mapping to Daisy Keech's
  official original;
- an ordered exercise table;
- duration or rep notes for each exercise;
- rest / transition timing;
- screenshot references that resolve to saved files.

Downloaded subtitles or transcript pages should not be credited as evidence.
Comments, third-party workout tables, or prior knowledge may be used only as
secondary checks. They are not sufficient evidence for pass-level credit unless
the trace also shows direct playback / frame inspection of the locked or
accepted video source.

## 3. Locked Ground Truth

Grade against `references/ground_truth.json` and these hidden reference assets:

- `references/reference_exercise_table.csv`
- `references/reference_abs_workout_guide.md`
- `references/reference_abs_workout_report.md`
- `references/source_frames/`

Locked source:

- Video ID: `niLch13u0sc`
- Title: `Daisy Keech hourglass abs workout but just the exercises (with timer and breaks)`
- Channel: `s h y`

Accepted official-original source:

- Video ID: `5cWxgnJgHHs`
- Title: `Hourglass Abs Workout | 10 Minutes`
- Channel: `Daisy Keech`

The official original can receive full source credit only when the executor
explicitly explains that it is the source routine behind the locked timer edit
and still recovers the locked move family, order, and timer shape. The related
video `sz3xierpVgg` is not full-credit equivalent unless the answer clearly
maps it back to the locked edit; otherwise apply the source cap in §6.

Canonical primary sequence:

| Slot | Canonical move | Accepted wording | Timing baseline |
| --- | --- | --- | --- |
| 1 | basic crunches | crunches, bodyweight crunches | about 60s |
| 2 | bicycle kicks | bicycles, bicycle kicks | about 60s |
| 3 | jack knives | jackknives, alternating jack knives, V-ups if visually equivalent | about 60s or two 30s side splits |
| 4 | russian twists | russian twist | about 60s |
| 5 | toe taps | toe touches, bent toe taps, bent knee taps | about 60s |
| 6 | bicycle crunches | cross-body bicycle crunches; two 30s side splits accepted | about 60s total |
| 7 | scissor kicks | scissors, scissor legs | about 60s |
| 8 | reverse crunches | reverse crunch | about 60s |
| 9 | butterfly kicks | flutter kicks, butterfly flutter kicks | about 60s |

Short transition rests are expected between moves. The hidden baseline uses
minute marks `00:00`, `01:00`, ..., `08:00` with very short transitions; accept
roughly `5-10s` rests when the answer is otherwise grounded in the timer-edit
video. Side-specific rows for jack knives or bicycle crunches count as one
canonical slot if their combined placement and timing match the slot.

Distinctness requirements:

- `bicycle kicks` and `bicycle crunches` are separate slots and must not be
  collapsed into one exercise.
- `scissor kicks`, `butterfly / flutter kicks`, and generic `leg raises` are
  not interchangeable unless the screenshot and wording clearly support the
  canonical movement.
- Thumbnails, title cards, channel art, static article images, and page
  screenshots do not count as exercise-frame evidence.

## 4. Source-Selection and Output Matching Rules

The primary output is `/tmp_workspace/results/abs_workout_guide.md`. The
supervisor may inspect equivalent copied paths inside a run directory, but the
candidate must have produced the requested result path during execution.

Screenshots are credited only if they are saved under
`/tmp_workspace/results/abs_workout_frames/` or an equivalent copied result
directory, are referenced from the guide, and visibly show an active exercise
segment from the locked / accepted video. A screenshot can include player
chrome or timer overlays; that is acceptable and often strengthens grounding.

When filenames or guide links have extension mismatches, credit the screenshot
only if the referenced image can still be unambiguously matched to a real saved
file for that move. Broken links or unreferenced orphan frames do not receive
visual-evidence credit.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — Deliverable shape and link integrity.** The markdown guide exists
  at the required path or copied result path, the frame directory exists, the
  guide contains an ordered table plus per-move screenshot references, and at
  least the referenced frame files can be resolved. Award up to 0.05 if the
  markdown exists but links / frame directory are incomplete. Zero this line if
  the guide is missing.

- **0.15 — Source identity and direct-video grounding.** Full credit requires
  identifying `niLch13u0sc` by title / URL, or identifying `5cWxgnJgHHs` with
  an explicit mapping back to the locked timer edit, plus visible trace
  evidence of playback, seeking, downloading the same video, or extracting
  frames from that source. Award at most 0.08 if the correct title is named but
  the trace shows only search snippets, comments, transcripts, or third-party
  pages. Award 0.00 for an unrelated source.

- **0.35 — Canonical moves and order.** Score the nine slots in §3:
  `0.03` per correctly recovered and distinct canonical slot, for `0.27`
  maximum. Then award up to `0.08` for order: `0.08` if the canonical order is
  preserved with only side-split rows or harmless extra notes; `0.04` if there
  are no more than two adjacent swaps / minor shifts and the routine is still
  recognizable; `0.00` if the sequence is reversed, random, or from another
  workout. Do not double-count side splits as extra canonical slots.

- **0.15 — Timing and rest accuracy.** Award up to `0.09` for durations:
  full credit when at least eight canonical slots are about one minute each
  or side splits combine to one minute, 0.045 for six or seven such slots, and
  0.00 for fewer than six. Award up to `0.04` for short rest / transition
  information: full credit for roughly `5-10s` rests or clear timer-break
  notes, 0.02 for vague "short rest" wording, 0.00 for long gym-plan rests or
  no rest information. Award `0.02` only if the overall guide reads as a
  timer circuit of about 10-11 minutes rather than a reps-only generic plan.

- **0.20 — Visual frame evidence.** Award up to `0.12` for slot-aligned
  exercise screenshots: `9/9 = 0.12`, `8/9 = 0.10`, `6-7/9 = 0.06`,
  `4-5/9 = 0.03`, fewer than four = 0.00. Each credited screenshot must be a
  saved, referenced, active exercise frame for the matching canonical slot.
  Award up to `0.04` for movement specificity across sampled frames
  (postures match the named move families, not generic floor exercise shots).
  Award up to `0.04` for visual-source integrity (frames are from the locked
  or accepted video, not thumbnails, title cards, page screenshots, unrelated
  stock images, or article screenshots).

- **0.05 — Guide usability and factual restraint.** The final guide is
  coherent enough to follow as a workout, includes concise per-move notes, and
  avoids invented source claims, hidden-reference leakage, or unsupported
  precision. Deduct here for polished but unauditable prose, false claims about
  how the video was verified, or instructions that contradict the recovered
  exercise evidence.

Total: `0.10 + 0.15 + 0.35 + 0.15 + 0.20 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

Partial credit is awarded line-by-line under §5. Caps override rubric totals
and compose by `min`. A run passes only if the final capped score is `>= 0.90`.

- **Cap at 0.30 — Missing primary deliverable.** No usable
  `abs_workout_guide.md` exists in `/tmp_workspace/results/` or the copied
  result directory.
- **Cap at 0.40 — No exercise-frame deliverable.** The guide exists, but no
  usable files were saved under `abs_workout_frames/`.
- **Cap at 0.45 — Wrong source.** The selected workout is clearly unrelated to
  `niLch13u0sc`, `5cWxgnJgHHs`, or a strongly mapped Daisy Keech hourglass abs
  source.
- **Cap at 0.45 — Generic workout knowledge.** The answer is primarily a
  generic ab routine or wellness guide and could have been written without
  finding the Daisy Keech video.
- **Cap at 0.55 — Text-only or shortcut reconstruction.** The correct title
  or video ID appears, but the trace and artifacts show reliance on subtitles,
  comments, transcripts, third-party tables, or search snippets without
  direct playback / frame checking.
- **Cap at 0.60 — Missing most canonical moves.** Fewer than six of the nine
  canonical move slots in §3 are recovered, even if the guide is plausible.
- **Cap at 0.75 — Incomplete canonical routine.** Only six or seven canonical
  slots are recovered, or distinct required slots such as `bicycle kicks` and
  `bicycle crunches` are collapsed.
- **Cap at 0.84 — One canonical slot missing.** Exactly eight canonical slots
  are recovered. This is continue-worthy but not pass-level because the public
  task asks for every exercise.
- **Cap at 0.70 — Bad order.** The answer contains many correct move names but
  is reversed, substantially shuffled, or follows a third-party article order
  rather than the canonical timer sequence.
- **Cap at 0.84 — Material timing / rest errors.** The source and move list
  are mostly correct, but two or more canonical slots have wrong / missing
  durations, the routine is presented as a reps-only plan, or rest information
  contradicts the short timer-break pattern.
- **Cap at 0.55 — No visual grounding.** The output has no valid active
  exercise screenshots for canonical slots, even if markdown names moves.
- **Cap at 0.75 — Weak visual grounding.** Fewer than six canonical slots have
  valid saved and referenced exercise frames.
- **Cap at 0.84 — Incomplete per-move screenshots.** Fewer than nine
  canonical slots have valid saved and referenced exercise frames. This allows
  follow-up repair but prevents pass-level credit.
- **Cap at 0.70 — Thumbnail / unrelated-image evidence.** Most credited
  images are thumbnails, title cards, page screenshots, channel art, unrelated
  fitness imagery, or static article images rather than active exercise frames.
- **Cap at 0.50 — Fabricated verification.** The guide claims direct viewing,
  frame extraction, or exact timer observations that are contradicted by the
  trace or by the saved artifacts.
- **Cap at 0.30 — Credential / privacy leak.** Any value whose env var is
  declared in `.privacy` is emitted in user-visible output. No such value is
  expected for this task, so any leak is severe.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** — stop. The answer identifies the locked
  source or accepted official-original mapping, recovers all nine canonical
  move families in canonical order, gives one-minute / short-rest timer
  information, includes valid saved screenshots for every canonical slot, and
  produces a usable guide.
- **Continue (`0.60 - 0.89` after caps)** — request one targeted repair when
  the correct source is found but the result is missing one move, has six to
  eight canonical moves, has incomplete timing / rest cleanup, has correct
  moves in a poor but fixable order, or needs additional slot-aligned frames.
- **Fail (`< 0.60` after caps)** — no further follow-up; record
  `finalStatus=failed`. This includes missing deliverables, wrong-source
  workouts, generic workout plans, text-only shortcut reconstructions, no
  visual grounding, or fewer than six canonical moves.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — locked source metadata, accepted resource
  mapping, canonical sequence, and boundary notes.
- `references/reference_exercise_table.csv` — canonical order, move names,
  duration hints, rest hints, and minute marks.
- `references/reference_abs_workout_guide.md` — concise expected guide shape.
- `references/reference_abs_workout_report.md` and `references/source_frames/`
  — visual movement anchors and screenshot policy.

## 9. Dynamic Content Note

This is a web-video task, so live YouTube metadata, view counts, or page layout
may drift. Treat the hidden ground truth and reference assets as authoritative
for grading. If live source access fails but the executor already captured
auditable frames from the locked / accepted video and produced the requested
guide, grade those artifacts against the snapshot above rather than requiring
current live metadata to match exactly.
