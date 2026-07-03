# Hidden Evaluation Rule — task_204_19_kate_elisabeth_london_spending

## 1. Grading Philosophy

Judge whether the executor produced a video-grounded spending extraction from
the correct Kate Elisabeth vlog. The benchmark is not a generic budgeting task:
spend rows must be traceable to the selected video's visible price overlays or
spoken audio, with timestamps and saved screenshots/keyframes.

Grade against `references/ground_truth.json` and the hidden evidence frames.
Prefer semantic row matching over brittle wording, but be strict about the
actual event, amount, currency, source video, and evidence. Polished formatting,
pie-chart aesthetics, or self-reported confidence must not compensate for a
small 5-6 row extraction, missing evidence columns, or subtitle/transcript-based
reconstruction.

## 2. Task Contract

The user asked the executor to open Kate Elisabeth's YouTube channel, identify
the latest video as of the locked 2026-04-23 benchmark snapshot whose topic is
weekly spending / cost of living in London, actually watch that video, and
create these outputs under
`/tmp_workspace/results/`:

- `london_week_spending.csv`
- `london_week_spending_pie.png`
- `london_week_spending.md`
- `spending_evidence/` with one saved video screenshot or keyframe for each
  CSV spend row

The CSV must contain these columns, case-insensitive after trimming whitespace:

- `item`
- `amount`
- `currency`
- `category`
- `timestamp`
- `evidence_frame`
- `evidence_type`
- `note`

The markdown must state the selected video title and link, explain why it is the
snapshot-latest matching video, describe category logic, report the CSV/itemized
total, report the creator's stated video grand total, and reconcile any
difference as unitemized or unconfirmed remainder rather than inventing named
purchases.

Downloaded or saved subtitle/transcript files are prohibited by the task. Browser
captions shown during playback may be used only as an accessibility aid and are
not valid standalone evidence for spend rows.

## 3. Source-Selection and Target-Resolution Rules

The locked benchmark snapshot is dated `2026-04-23`. The canonical selected
video is:

- video ID: `YQOhJE2pA9E`
- URL: `https://www.youtube.com/watch?v=YQOhJE2pA9E`
- title: `How much I Spend £ in a Week as a 25 year-old Living in London 🇬🇧`
- published: `2025-09-21`
- duration: `22:39`

The relevant but older candidate is:

- video ID: `Nk4ZeczQGwk`
- title: `What I Spend £ in a Week as a 25 year old Living and Working in London 🇬🇧 (bills, transport, food)`
- published: `2025-07-06`

Award full source-selection credit only for the canonical `YQOhJE2pA9E` video.
Use video ID first, then unambiguous title/link matching. The older July 2025
video can receive partial source-selection credit only under the caps in section
6. Unrelated videos, channel summaries, search snippets, transcript pages, or
model memory do not satisfy source selection.

## 4. Locked Ground Truth Snapshot

The canonical spend rows are the 18 itemized rows in
`references/ground_truth.json`. Match by the underlying purchase/event, not by
exact wording. A row is correct only when the executor identifies the same event,
uses GBP, and gives an amount within `0.15` GBP of the canonical amount or one of
the accepted rounded amounts in the ground truth.

Canonical rows:

1. `breakfast_chai_latte` - breakfast chai latte / coffee - GBP `9.95`
   (accept `10.00`)
2. `m_and_s_aardo_food_shop` - M&S / Aardo food shop - GBP `91.00`
3. `oyster_top_up` - Oyster / TfL top-up - GBP `85.00`
4. `tube_fare_to_class` - Tube fare to class - GBP `2.90`
5. `gym_food_and_drink` - Natural Fitness Food wrap and drink - GBP `11.95`
6. `third_space_membership_daily_allocation` - Third Space membership daily
   allocation - GBP `8.30`
7. `zara_smart_tshirt` - Zara smart T-shirt purchase - GBP `24.98`
8. `dumplings_dinner` - dumplings dinner - GBP `35.00`
9. `sweet_bun` - sweet bun / bakery treat - GBP `4.95`
10. `tube_fare_after_dinner` - Tube fare after dinner - GBP `2.90`
11. `lime_bike_home` - Lime bike ride home - GBP `2.16`
12. `clothes_shopping_brandy_urban` - clothes shopping at Brandy / Urban -
    GBP `150.00`
13. `waterstones_books` - Waterstones books - GBP `14.95` (accept `15.00`)
14. `tube_fare_to_events` - Tube fare to events - GBP `2.90`
15. `black_cab_to_event` - black cab to event - GBP `21.73`
16. `second_cab_or_taxi` - second cab / taxi ride - GBP `22.36`
17. `pres_shop_mixer_energy_drinks` - pre-drinks shop / mixers and energy
    drinks - GBP `13.15`
18. `pasta_dinner` - pasta dinner - GBP `16.50`

The locked itemized total for these 18 rows is GBP `520.68`. The creator states
a video grand total of GBP `542.94` at approximately `00:21:48`, excluding
mortgage, water, and electricity. The canonical unitemized or unconfirmed
remainder is GBP `22.26`.

Do not require the executor to invent a named purchase for the `22.26`
remainder. A clearly labeled `unitemized_or_unconfirmed_remainder` is acceptable
for reconciliation. A named fabricated spend row for the remainder is an error.

Do not count non-spend context such as hosted/free Shard lunch, brand events, or
free drinks as spend rows unless the executor supplies a video-supported personal
price.

## 5. Checkpoint Rubric

Weights sum to 1.00. Compute checkpoint credit first, then apply all score caps
in section 6 by taking the minimum.

- **0.15 - Output artifacts and schema.** Award up to 0.05 for the required
  CSV, pie chart, markdown, and requested `spending_evidence/` directory being
  present under `/tmp_workspace/results/`; up to 0.05 for the CSV having all
  eight required columns with parseable numeric GBP amounts; up to 0.03 for one
  saved screenshot/keyframe per CSV spend row with paths that resolve from the
  CSV; and up to 0.02 for the markdown covering the required title/link,
  category logic, totals, and reconciliation fields. A differently named image
  directory can earn CP4 grounding credit if paths resolve, but it does not get
  full artifact-name credit here.

- **0.15 - Canonical video selection and viewing.** Award up to 0.10 for
  selecting `YQOhJE2pA9E` with the correct title/link; up to 0.03 for explaining
  why it is newer than the July 2025 related candidate; and up to 0.02 for trace
  or saved artifacts showing the executor opened the channel/watch page and
  actually played or inspected the selected video. Do not award viewing credit
  from transcripts, summaries, or search snippets alone.

- **0.35 - Canonical spend-row coverage and amount accuracy.** Score the 18
  rows in section 4 independently: each matched row is worth `0.35 / 18`. A
  match requires the same event, an accepted amount, GBP currency, and no
  material contradiction in the note/category. Duplicate rows count once.
  Aggregated categories such as "transport" or "shopping" do not count unless a
  distinct canonical spend row can be identified within the CSV. Extra
  unsupported rows receive no credit and may trigger caps.

- **0.20 - Video grounding and evidence quality.** Award proportionally across
  the spend rows that receive CP3 credit. Full credit requires timestamps near
  the relevant video moment, `evidence_frame` paths that open to actual saved
  screenshots/keyframes from the selected video, and `evidence_type` values that
  accurately distinguish `visible_price_overlay`, `spoken_in_video`, or
  `visible_and_spoken`. Visual-overlay-only items must be backed by frames where
  the price overlay or payment screen is readable. Spoken-only claims without a
  timestamp and saved frame/audio-context evidence are weak. Transcript text is
  not valid grounding.

- **0.15 - Totals, reconciliation, and pie chart.** Award up to 0.04 for a CSV
  or markdown itemized total that exactly sums the output spend rows; up to 0.04
  for reporting the creator's stated grand total of GBP `542.94`; up to 0.03
  for reconciling the difference as unitemized/unconfirmed remainder without a
  fabricated named purchase (full credit when the canonical GBP `520.68` /
  `22.26` relationship is recovered); and up to 0.04 for a pie chart whose
  category totals match the CSV and do not include the unitemized remainder as a
  fake category unless explicitly labeled as unconfirmed.

## 6. Scoring Policy / Score Caps

Apply every relevant cap after adding checkpoint credit. Caps are maximum final
scores and compose by `min`.

- **Cap at 0.30 - No primary CSV.** `london_week_spending.csv` is absent,
  unreadable, or not parseable as tabular data.
- **Cap at 0.35 - No substantive task answer.** The output is mostly empty,
  unrelated, or does not attempt an itemized Kate Elisabeth London spending
  extraction.
- **Cap at 0.40 - Mostly fabricated or guessed.** The answer is built from broad
  London budget categories, model priors, or invented spend names rather than
  video-specific purchases.
- **Cap at 0.45 - Wrong or unrelated video.** The selected source is not the
  canonical video and is not the older relevant July 2025 candidate.
- **Cap at 0.65 - Older relevant video.** The executor uses `Nk4ZeczQGwk`
  instead of the canonical September 2025 video.
- **Cap at 0.50 - No saved video evidence.** No screenshots/keyframes from the
  selected video are saved, or the CSV evidence paths do not resolve to image
  files.
- **Cap at 0.55 - Subtitle/transcript violation or text-only extraction.**
  `/tmp_workspace/results/` contains `.vtt`, `.srt`, subtitle, or transcript
  artifacts; or the trace/result shows downloaded subtitles, YouTube transcript
  text, third-party transcripts, channel summaries, or other text-only sources
  used as the primary extraction source. Browser captions visible during
  playback do not trigger this cap by themselves unless they are the sole
  evidence for the spend rows.
- **Cap at 0.55 - Six or fewer canonical rows.** The CSV matches `<= 6` of the
  18 canonical spend rows, even if those few rows are correct and polished.
- **Cap at 0.65 - Fewer than twelve canonical rows.** The CSV matches `7-11`
  canonical spend rows.
- **Cap at 0.75 - Fewer than fourteen canonical rows.** The CSV matches `12-13`
  canonical spend rows.
- **Cap at 0.84 - Fewer than sixteen canonical rows.** The CSV matches `14-15`
  canonical spend rows. A passing score requires at least 16 matched canonical
  spend rows after all other caps.
- **Cap at 0.70 - Required evidence schema missing.** The CSV omits any of the
  required `timestamp`, `evidence_frame`, or `evidence_type` columns, or those
  fields are blank for most rows.
- **Cap at 0.70 - Visual-overlay collapse.** Most visual-overlay-only rows are
  missing or unsupported by readable frames, especially the Oyster/TfL top-up,
  Tube fares, gym food/drink, Third Space allocation, Zara, cab/taxi, mixer, and
  pasta rows.
- **Cap at 0.78 - Invented or misclassified extras.** Unsupported spend rows or
  named purchases for the unitemized remainder materially affect the CSV total
  or pie chart, while the core video and some canonical rows are correct.
- **Cap at 0.80 - Pie chart failure.** The pie chart is missing, unreadable, or
  inconsistent with the CSV category totals.
- **Cap at 0.80 - Grand-total/remainder failure.** The markdown omits the
  stated GBP `542.94` grand total, treats it as fully itemized without
  explanation, or fails to reconcile the difference from the CSV total.
- **Cap at 0.84 - Weak snapshot-latest-video rationale.** The correct video is
  used, but the answer does not explain how it was selected as the latest
  matching channel video in the locked snapshot.
- **Cap at 0.30 - Credential or privacy leak.** Any value whose environment
  variable is declared in `.privacy` is emitted in user-visible output.

A run passes only if the final score is `>= 0.90` after caps. A run capped below
`0.90` is not a pass even if the uncapped checkpoint total is high.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - Stop. The executor selected the canonical
  video, produced the required files and CSV schema, avoided subtitle/transcript
  artifacts, matched at least 16 of 18 canonical spend rows with accepted
  amounts, saved usable video evidence for the rows, and handled the GBP
  `542.94` total/remainder and pie chart correctly.
- **Continue (`0.60 - 0.89` after caps)** - Request one focused follow-up if the
  work is recoverable: the correct video is selected, primary artifacts exist,
  and the likely fix is to inspect more visual price overlays, add missing
  timestamps/evidence paths, repair the CSV schema, regenerate the pie chart, or
  reconcile the total.
- **Fail (`< 0.60` after caps)** - Do not request further work. This includes
  missing CSV, unrelated video, fabricated budget-style answers, subtitle or
  transcript artifacts/primary reliance, no saved video evidence, privacy
  leakage, or outputs matching six or fewer canonical rows.

When giving public feedback, do not reveal the hidden canonical row list or
exact benchmark internals. Ask the executor in general terms to re-watch the
selected video, capture the visible price overlays, add required evidence
columns/screenshots, or remove subtitle/transcript-derived artifacts.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or user
simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - authoritative video snapshot, canonical
  spend rows, accepted amounts, totals, and subtitle policy.
- `references/reference_video_selection.md` - source-selection snapshot and
  older-candidate note.
- `references/spending_evidence_reference_sheet.jpg` - contact sheet of the 18
  canonical spend frames.
- `references/evidence_frames/spend_*.jpg` - per-row hidden evidence frames.

## 9. Dynamic Content Note

YouTube is live and may change after the `2026-04-23` snapshot. Score this
benchmark against `references/ground_truth.json` and the canonical video above,
not against a later channel ordering, search result, transcript, or model
memory. If live YouTube has drifted, note the drift as a benchmark issue rather
than rewarding a different video or altered spend list.
