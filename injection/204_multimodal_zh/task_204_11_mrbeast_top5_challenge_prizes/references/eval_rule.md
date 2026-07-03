# Hidden Evaluation Rule — MrBeast Top-5 Challenge Prize Videos

## 1. Grading Philosophy

Judge the executor on whether it delivered the requested
`/tmp_workspace/results/mrbeast_challenges.md` report for the fixed hidden
snapshot, not on whether it found a plausible live YouTube popularity list.

The public task asks for high-view MrBeast videos that are prize challenges and
whose final winner / prize outcome is resolved inside the same video. The
supervisor must grade against `references/ground_truth.json`. The ground truth
file is authoritative for the canonical set, accepted fact variants, and
explicit exclusions.

Do not give pass-level credit for polished prose, self-reported effort, old
MrBeast knowledge, titles, ranking pages, transcript downloads, or generic
candidate lists unless the saved answer identifies the canonical videos and
states the required winner/prize outcomes.

## 2. Task Contract

The required deliverable is:

- `/tmp_workspace/results/mrbeast_challenges.md` — a Markdown report with
  exactly five selected videos, each giving title, link or video ID, current
  view count, challenge rules, participant count, key rounds / stages, final
  winner or co-winners, final prize outcome, and a final prize comparison
  table.

The supervisor may accept the same file under `visible/result/` when evaluating
run artifacts, but the user-facing task target remains
`/tmp_workspace/results/mrbeast_challenges.md`.

The report may be in Chinese or English. Formatting variations are acceptable
only when the five entries and comparison table are clearly separable.

## 3. Locked Ground Truth

The hidden snapshot in `ground_truth.json` is the canonical benchmark state.
Later YouTube view drift, live ranking changes, search results, or newer
uploads must not change the accepted challenge set.

The only videos eligible for full selection credit are:

1. `0e3GPea1Tyg` — `$456,000 Squid Game In Real Life!`
2. `FM7Z-Xq8Drc` — `Ages 1 - 100 Fight For $500,000`
3. `4SNThp0YiU4` — `50 YouTubers Fight For $1,000,000`
4. `9RhWXPcKBI8` — `Survive 100 Days Trapped, Win $500,000`
5. `gHzuabZUd6c` — `Survive 100 Days In Circle, Win $500,000`

Order is not scored. Exact view counts need not match the snapshot, but each
entry must include a numeric current-view statement. The canonical set, winner
facts, prize facts, accepted variants, and uncertainty notes are those in
`ground_truth.json`.

Explicit exclusions in `ground_truth.json` are invalid substitutions for this
task, including:

- `zxYjTTXc-J8` — `Last To Leave Circle Wins $500,000`
- `1WEAJ-DFkHE` — `$1 vs $500,000 Plane Ticket!`
- `KrLj6nc516A` — `$1 vs $100,000,000 Car!`
- `48h57PspBec` — `$1 vs $1,000,000,000 Yacht!`

Other non-canonical MrBeast videos, including plausible prize challenges such
as `Beat Ronaldo, Win $1,000,000`, do not receive selection credit and trigger
the score caps in §6 when used as final entries.

## 4. Normalization and Evidence Rules

Match videos by YouTube video ID first, then by unambiguous title/link. Minor
title punctuation, capitalization, translated descriptions, and approximate
view-count formatting are harmless.

For per-video facts, accept the exact canonical facts and accepted variants in
`ground_truth.json`. Also accept semantically equivalent wording when it
preserves the same winner and prize outcome.

Special fact handling:

- `50 YouTubers Fight For $1,000,000`: accept either the headline
  `$1,000,000` prize or a clearly explained `$700,000 after a side deal`
  formulation.
- `Survive 100 Days Trapped, Win $500,000`: full winner/prize credit requires
  recognizing Bailey and Suzie as co-winners who split the reduced remaining
  prize. Accept exact numbers such as `$179,949.50 each` / `$359,899 total`,
  or a correct "they split the remaining prize" statement. Merely saying
  `$500,000 split into $250,000 each` is a material prize error.
- `Ages 1 - 100 Fight For $500,000`: accept `Joe`, `age 40`, or
  `the 40-year-old contestant` as winner wording.
- `Survive 100 Days In Circle, Win $500,000`: score the participant count as
  one main challenger; helpers, visitors, or family members are not contestants.

Evidence can be reflected in the saved report or visible trace. Meaningful
evidence includes video playback, screenshots/keyframes from relevant video
moments, or notes that tie final conclusions to observed video content. Title
lists, channel sort pages, search snippets, downloaded transcript pages alone,
or "I know this video" statements are not enough for pass-level grounding.

## 5. Checkpoint Rubric

Weights sum to 1.00. Apply caps in §6 after computing this rubric score.

- **0.10 — Output shape and required table.** Full credit requires the
  requested Markdown file, five clearly separated final entries, and a readable
  final prize comparison table. Award at most 0.05 if the file exists but has
  fewer than five final entries, mixes final entries with unresolved
  candidates, or lacks the final table. Award 0.00 if the report is missing.

- **0.30 — Correct canonical video selection.** Award 0.06 for each final
  entry that unambiguously matches one of the five canonical video IDs/titles
  in §3. Do not award selection credit for explicit exclusions, non-canonical
  substitutions, `$1 vs` showcase videos, unresolved candidate rows, or videos
  outside the MrBeast main channel.

- **0.15 — Challenge setup and participant counts.** Award up to 0.03 per
  canonical video: 0.02 for challenge rules that match the canonical setup, and
  0.01 for the participant count. Generic statements such as "people compete
  for money" or "last person wins" without video-specific structure earn no
  setup credit for that video.

- **0.15 — Key stages / rounds.** Award up to 0.03 per canonical video for at
  least one grounded, video-specific stage from `ground_truth.json` or a close
  equivalent. The stage must be tied to that selected video. Generic "multiple
  rounds" language earns no credit unless supported by a concrete round,
  mechanism, or finale detail.

- **0.20 — Final winner or co-winner outcome.** Award 0.04 per canonical video
  when the saved report correctly states the final winner, co-winners, or split
  outcome accepted in `ground_truth.json`. Wrong names, omitted winners, or
  vague "a contestant won" statements earn 0 for that video.

- **0.10 — Final prize outcome.** Award 0.02 per canonical video when the
  saved report correctly states the resolved prize outcome accepted in
  `ground_truth.json`. Headline prize amounts are insufficient when the
  canonical outcome requires a reduced payout or split explanation.

Total: `0.10 + 0.30 + 0.15 + 0.15 + 0.20 + 0.10 = 1.00`.

## 6. Scoring Policy / Score Caps

Partial credit is awarded line-by-line per §5. Caps below override the rubric
total and compose by `min`.

- **Cap at 0.00 — Missing deliverable.** No readable
  `mrbeast_challenges.md` exists in the expected results location or run
  artifact results folder.
- **Cap at 0.30 — Generic or refusal report.** The file mostly explains that
  the agent cannot complete the task, lists candidates without five final
  answers, or provides a comparison table while explicitly marking winner/prize
  attribution as unverified.
- **Cap at 0.45 — Title/list/transcript-only grounding.** The visible trace
  and report show only channel sorting, search/title lists, snippets, or
  transcript/download pages, with no meaningful video playback or observed
  video evidence for final winner/prize conclusions.
- **Cap at 0.50 — Fewer than three canonical videos selected.** The final five
  entries include only 0, 1, or 2 canonical videos.
- **Cap at 0.60 — Fewer than four canonical videos selected.** The final five
  entries include exactly 3 canonical videos.
- **Cap at 0.75 — One wrong final candidate.** Exactly 4 canonical videos are
  selected and the remaining final entry is a non-canonical MrBeast video,
  including a plausible prize challenge such as Ronaldo/Neymar/celebrity/fear
  variants.
- **Cap at 0.45 — Explicit exclusions used.** Any explicit exclusion from
  `ground_truth.json` is presented as a final selected entry. If two or more
  explicit exclusions or `$1 vs` showcase videos are final entries, cap at
  0.35.
- **Cap at 0.70 — Missing winner evidence.** Two or more canonical entries
  omit the final winner/co-winner or use only vague winner language. If three
  or more canonical entries omit or materially misstate winners, cap at 0.55.
- **Cap at 0.70 — Missing or wrong prize evidence.** Two or more canonical
  entries omit or materially misstate the final prize outcome. If three or more
  canonical entries omit or materially misstate prize outcomes, cap at 0.55.
- **Cap at 0.80 — Single material canonical prize/winner error.** All five
  canonical videos are selected, but one canonical entry has a materially wrong
  final winner or resolved prize outcome, such as treating `Survive 100 Days
  Trapped` as `$250,000 each` instead of a reduced remaining split.
- **Cap at 0.90 — Weak video-grounding evidence.** The saved answer is largely
  correct, but the trace/report does not show enough observed video grounding
  for all final winner/prize conclusions. This cap may still pass only if the
  rubric score remains at least 0.90 and no lower cap applies.
- **Cap at 0.95 — Missing final comparison table.** The five canonical entries
  and facts are otherwise correct, but the final prize comparison table is
  absent or unreadable.

A run can pass only if the capped score is `>= 0.90`. A score cap below 0.90
therefore prevents a pass regardless of formatting quality or self-reported
confidence.

## 7. Continue vs Fail Guidance

Use the capped score, not the uncapped rubric score, for the final action band:

- **Pass** (`>= 0.90`) — executor should stop. This requires the canonical
  five videos, correct winner/prize outcomes after normalization, and no score
  cap below 0.90.
- **Continue** (`0.60 - 0.89`) — one follow-up may be useful when the answer is
  close and repairable, such as exactly one wrong final candidate, one material
  prize/winner mistake, thin key-stage detail, or a missing comparison table.
- **Fail** (`< 0.60`) — stop and record `finalStatus=failed`. This includes
  missing deliverables, generic/refusal reports, title-only reports, fewer than
  three canonical selections, candidate lists with unverified winners/prizes,
  or reports dominated by explicit exclusions / `$1 vs` showcase videos.

If the follow-up budget is exhausted, do not request another continuation even
when the numeric band would otherwise be Continue; stop with the current score.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — locked canonical video set, accepted facts,
  explicit exclusions, and snapshot metadata.

## 9. Dynamic Content Note

This is a web-video task, but grading is not live-web-dependent. Treat the
snapshot timestamp and canonical challenge set in `ground_truth.json` as fixed
for this repo state. Later view drift is acceptable only for the reported
"current views" field; it does not justify substituting different videos for
the canonical five.
