# Hidden Evaluation Rule — task_204_09_veritasium_top5_science_popular

## 1. Grading Philosophy

Judge the executor on whether it delivered the requested report and whether the
report is grounded in the hidden Veritasium Popular snapshot, not in whatever
YouTube ranking may be live at evaluation time.

The user-facing task identifies the fixed benchmark snapshot date.
`references/ground_truth.json` is authoritative for the channel snapshot, video
identities, order, view-count scale, scientific questions, key stages,
conclusions, and counterintuitive contrasts. Do not replace or reorder the
hidden top five based on live YouTube, search snippets, old memory, or a newly
observed popularity list.

Accept paraphrase, Chinese or English wording, and minor title punctuation or
capitalization differences. Do not accept generic science-channel summaries,
plausible but non-canonical high-view Veritasium videos, or answers that list
titles without the actual scientific question and conclusion for each video.

## 2. Task Contract

The executor must create:

- `/tmp_workspace/results/veritasium_top5.md`

The report must contain five clearly separated entries and a final comparison
table. For each entry it must state:

- selected video title,
- usable YouTube link or video ID,
- numeric view count or rounded numeric view statement seen by the executor,
- core scientific question,
- experiment design or key demonstration / explanatory setup,
- final conclusion,
- whether the conclusion is counterintuitive,
- one "intuition vs truth" style contrast.

The task explicitly says video length is not a filter. Short science
demonstrations still count when they are in the hidden top-five snapshot.

## 3. Locked Ground Truth Snapshot

Score against `references/ground_truth.json`. The canonical snapshot was
captured on `2026-04-23T01:42:41Z`.

The exact required top-five order is:

1. `uxPdPpi5W4o` - `Why Are 96,000,000 Black Balls on This Reservoir?` -
   snapshot views `110,273,106`
2. `4Wrc4fHSCpw` - `These are the asteroids to worry about` - snapshot views
   `80,580,076`
3. `AeJ9q45PfD0` - `World's Lightest Solid!` - snapshot views `62,024,160`
4. `2OSrvzNW9FE` - `Backspin Basketball Flies Off Dam` - snapshot views
   `60,195,787`
5. `AF8d72mA41M` - `Why It Was Almost Impossible to Make the Blue LED` -
   snapshot views `49,050,522`

Identity matching is by video ID first, then by unambiguous title or link.
Exact snapshot order matters for full credit. A report with the right five
videos in the wrong order cannot pass after caps.

Common wrong substitutions are explicitly non-canonical even if they are
high-view Veritasium videos:

- `094y1Z2wpJg` - `The Simplest Math Problem No One Can Solve - Collatz
  Conjecture`
- `pir_muTzYM8` - `Inside The Navy's Indoor Ocean`

View counts may drift after the snapshot. Award view-reporting credit for a
numeric value that is on the same scale as the snapshot count for the same
video, including rounded forms such as `110M`, `80M`, `62M`, `60M`, and `49M`.
Do not use live current popularity to alter the canonical set or order.

## 4. Checkpoint Rubric

Weights sum to 1.00. Apply score caps in section 5 after adding checkpoint
credit.

- **0.10 - Output file and report shape.** Full credit requires
  `/tmp_workspace/results/veritasium_top5.md` to exist, be readable, and
  contain exactly five clearly separated video entries plus a final comparison
  table. Award 0.05 if the file exists but has unclear structure or a malformed
  table. Award 0.00 if the file is missing.

- **0.25 - Canonical video identity and exact order.** Award 0.05 for each
  rank whose entry matches the canonical video ID or unambiguous title at that
  exact rank. Do not give the rank point for a correct canonical video placed at
  the wrong rank. Extra non-canonical entries do not receive credit and may
  trigger caps.

- **0.05 - Link and view reporting.** Award 0.01 per canonical entry that
  includes both a usable link or video ID and a numeric view statement on the
  same scale as the snapshot. Missing links, missing IDs, non-numeric view
  claims, or view counts clearly incompatible with the target video get 0 for
  that entry.

- **0.10 - Observable sourcing and viewing evidence.** Award up to 0.05 for
  trace or saved artifacts showing the executor reached the Veritasium channel
  video list and selected the Popular / Most popular view. Award up to 0.05
  for trace or saved artifacts showing each of the five canonical watch pages
  was opened or played (`0.01` per video). This credit cannot be earned from
  downloaded transcripts, cached ranking pages, or model self-assertions alone.

- **0.40 - Per-video scientific grounding.** Award up to 0.08 per canonical
  video, using the `canonical`, `allowed_synonyms`, and `uncertainty` fields in
  `ground_truth.json`:
  - 0.02 for the correct core scientific question.
  - 0.02 for at least one grounded key stage, demonstration, or explanatory
    setup specific to that video.
  - 0.03 for the correct final conclusion.
  - 0.01 for a correct counterintuitive or "intuition vs truth" contrast.
  Generic statements such as "it explains science" or conclusions that could
  apply to many videos earn no credit on the affected subpart.

- **0.10 - Required final presentation.** Award 0.01 per entry, up to 0.05,
  for explicitly covering all required fields from section 2. Award up to 0.05
  for a final table that lists all five selected videos and whether each is
  counterintuitive. The table may be in Chinese or English and may include
  extra columns, but it must cover all five videos.

## 5. Scoring Policy / Score Caps

Compute the checkpoint total, then apply all relevant caps by taking the
minimum. Caps target failure modes that should not pass even if formatting is
polished.

- **Cap at 0.00 - Missing primary output.** `veritasium_top5.md` is absent or
  unreadable.
- **Cap at 0.30 - No substantive answer.** The output exists but is mostly
  empty, contains unrelated content, or does not attempt the requested
  Veritasium top-five report.
- **Cap at 0.55 - Fewer than four canonical videos.** The selected set
  contains zero to three of the five locked canonical videos.
- **Cap at 0.55 - Non-target source mixed in.** Any selected entry is from
  another channel, is not a Veritasium upload, or is not a science experiment /
  science explanation video.
- **Cap at 0.60 - Multiple wrong substitutions.** Two or more entries are
  plausible high-view Veritasium videos but not in the locked top five,
  including the common wrong substitutions listed in section 3.
- **Cap at 0.78 - One wrong substitution.** Exactly one entry is a non-
  canonical high-view Veritasium substitution while the other four entries are
  canonical.
- **Cap at 0.84 - Correct set but wrong order.** All five canonical videos are
  present but not in the exact locked order.
- **Cap at 0.84 - Missing required report fields.** Any selected entry lacks a
  usable link or video ID, lacks a numeric view statement, lacks a specific core
  scientific question, or lacks a specific final conclusion.
- **Cap at 0.84 - Final table missing.** The report does not include the final
  comparison table requested by the user.
- **Cap at 0.84 - Weak Popular-page evidence.** The final set matches the
  hidden answer, but trace and artifacts do not show use of the YouTube channel
  Popular / Most popular view or equivalent on-site channel sorting.
- **Cap at 0.70 - Viewing/source-process failure.** The trace shows reliance
  on downloaded subtitles, transcript pages, cached ranking pages, search
  snippets, or prior-memory lists as the primary basis for scientific content,
  with no meaningful opening of the selected watch pages.
- **Cap at 0.70 - Shallow factual grounding.** Two or more canonical entries
  omit either the actual scientific question or the actual conclusion.
- **Cap at 0.65 - Contradictory science.** Two or more entries state
  conclusions that materially conflict with `ground_truth.json`.
- **Cap at 0.55 - Title-list answer.** The report mostly lists titles, links,
  and views but gives generic or absent scientific questions/conclusions.
- **Cap at 0.50 - Hidden snapshot rejected.** The executor explicitly replaces
  the fixed benchmark snapshot order or set because a live page, search result,
  or old remembered list appears different.
- **Cap at 0.30 - Credential or privacy leak.** Any value whose environment
  variable is declared in `.privacy` is emitted in user-visible output.

A run passes only if the final score is `>= 0.90` after all caps. A score that
would have passed before caps but is capped below 0.90 is not a pass.

## 6. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - Stop. The report has the locked canonical
  set in exact order, complete links/views, sufficient Popular-page and watch-
  page evidence, grounded scientific questions/conclusions for all five
  videos, and the final comparison table.
- **Continue (`0.60 - 0.89` after caps)** - Request one focused follow-up if
  the issue is recoverable, such as a missing final table, weak view-count
  reporting, one wrong high-view substitution, correct set in the wrong order,
  or one or two shallow per-video summaries.
- **Fail (`< 0.60` after caps)** - Do not request further work. This includes
  missing output, fewer than four canonical videos, title-list answers, mixed
  non-Veritasium/non-science sources, explicit rejection of the hidden snapshot,
  or privacy leakage.

When giving public feedback, do not reveal hidden video IDs or benchmark
internals. Ask the executor in general terms to re-check the Veritasium Popular
ordering, include the missing required fields, or strengthen the actual
question/conclusion summaries.

## 7. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - authoritative snapshot, accepted synonyms,
  common wrong substitutions, view counts, and per-video scientific facts.

## 8. Dynamic Content Note

YouTube is live and may change after the benchmark snapshot. Ignore live
ranking changes during grading. If the current YouTube Popular page disagrees
with the hidden snapshot, still score against `ground_truth.json`; optionally
note the drift as a benchmark-data issue, but do not reward a different live
top five.
