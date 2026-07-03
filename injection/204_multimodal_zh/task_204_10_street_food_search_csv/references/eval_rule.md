# Hidden Evaluation Rule — task_204_10_street_food_search_csv

## 1. Grading Philosophy

Judge the executor on three outcomes:

1. The requested artifact exists: `/tmp_workspace/results/street_food.csv`
   is parseable CSV with the required columns and one snack attempt per row.
2. The rows are grounded in the pinned Joshua Weissman video, not another
   creator, another video, generic street-food knowledge, external summaries,
   or downloaded subtitle/transcript files.
3. The CSV recovers a substantial, accurate subset of the locked canonical row
   baseline in `references/ground_truth.json` and handles the New York segment
   as the weak/failed `$1` case.

Prefer semantic matching over brittle string equality for snack names, price
phrases, and short reviews, but do not give credit for unsupported countries,
cities, foods, or rows that are only plausible from outside knowledge. A row
must be traceable to the fixed target video and to the hidden baseline or an
explicit accepted variant.

## 2. Task Contract

Public-task restatement:

- Open and watch Joshua Weissman's `I Tried $1 Street Food Around The World`.
- Do not switch creators, mix videos, download subtitles/transcripts, or rely
  on external recipe/list summaries.
- Save `/tmp_workspace/results/street_food.csv`.
- The CSV must include these columns: `video_id`, `video_title`, `creator`,
  `country`, `city`, `snack`, `price_text`, `review`.
- Each snack should be represented as a separate row.
- `price_text` should preserve the price expression from the video, including
  approximate prices when the video is approximate.
- `review` must contain a clear positive, negative, or mixed judgment from the
  host, not just a neutral description of ingredients.

The supervisor accepts extra columns, but missing any required column prevents
full credit and may trigger caps in Section 6.

## 3. Source-Selection and Target-Resolution Rules

The only valid target video is:

- `video_id`: `RNePQW56rDU`
- `video_title`: `I Tried $1 Street Food Around The World`
- `creator`: `Joshua Weissman`

Every scored row must identify this same video. Rows from other videos,
channels, shorts, search result snippets, generic travel-food pages, or
external listicles are wrong even when the food sounds plausible.

Accepted evidence of video work includes the YouTube watch page for
`RNePQW56rDU`, sampled video frames/screenshots, direct audio/video
observations, or notes made from actually watching the video. Merely opening
the page is not enough if the row content is later filled from text-only
sources.

Prohibited non-canonical sources include downloaded captions/subtitles,
YouTube `timedtext`, `.json3`, `.vtt`, `.srt`, `transcript.xml`,
`transcript_full.txt`, mirror caption/summary URLs, or external summaries.
Visible captions that happen to appear inside a watched video frame do not by
themselves trigger a transcript cap; creating, downloading, parsing, or reading
caption/transcript artifacts does.

## 4. Locked Ground Truth

`references/ground_truth.json` is authoritative.

The locked baseline contains 26 canonical rows across 9 canonical stops:

- Mumbai, India: fire paan; black plum popsicle; jalebi fafda breakfast plate;
  vada pav.
- New York City, United States: no true `$1` American street-food winner.
- Bangkok, Thailand: fresh coconut; grilled pork with sticky rice; shrimp
  fritter / crispy shrimp disk; chive rice cake.
- Seoul, South Korea: twisted donut; eomuk / odeng fish cake skewers; kimchi
  or red-bean croquette.
- Hanoi, Vietnam: xoi / sticky rice breakfast bowl; fried bananas; banh mi
  with beef jerky and fermented pork.
- Kuala Lumpur, Malaysia: rice-flour crepe / egg crepe; shaved ice dessert;
  stir-fried noodles.
- Mexico City, Mexico: churros; stewed meat / guisado tacos; large pastry;
  al pastor taco.
- Shanghai, China: jianbing; scallion pancake.
- Chengdu, China: guokui; `$2` buffet noted as exceptional value but above the
  strict `$1` threshold.

Row matching is distinct-baseline matching:

- A CSV row matches a baseline row only when country/city and snack identity
  match after normalization or accepted variants in `ground_truth.json`.
- A duplicate output row for the same baseline item does not count again.
- A row outside the locked baseline is not credited. Count it as
  wrong/unsupported for caps if it materially inflates coverage, replaces a
  required baseline row, or cannot be verified from the hidden references.
- For price/review scoring, the matched row must also preserve an accepted
  price phrase and contain at least one review keyword or a clearly equivalent
  host sentiment from the baseline.

The New York row is special: it must communicate that a true `$1` American
street-food winner was not found or was weak. A plain `New York, Samosa, $1`
winner row is not acceptable unless the review explicitly frames it as a weak,
not-really-American substitute.

## 5. Checkpoint Rubric

Weights sum to 1.00. Apply Section 6 caps after adding checkpoint credit.

- **0.15 - Output shape.** Award 0.05 if
  `/tmp_workspace/results/street_food.csv` exists and parses as CSV; 0.05 if
  all required columns are present; 0.05 if there are at least 10 data rows and
  rows are snack-level rather than aggregated country summaries. Missing file
  or unparseable CSV earns 0.00 for this checkpoint.

- **0.15 - Fixed target identification and single-video constraint.** Full
  credit requires every non-empty row to identify `RNePQW56rDU`,
  `I Tried $1 Street Food Around The World`, and `Joshua Weissman`, with no
  mixed creators or videos. Award up to 0.10 for mostly correct but incomplete
  metadata. Award 0.00 if the target video cannot be determined from the CSV.

- **0.25 - Distinct canonical row recovery.** Count distinct baseline rows
  matched by country/city/snack identity, ignoring duplicates and wrong rows.
  Score `0.25 * min(correct_distinct_baseline_rows, 12) / 12`. Full credit on
  this line requires at least 12 distinct baseline matches. Rows with correct
  video metadata but non-baseline country/city/snack combinations do not count.

- **0.15 - Canonical stop breadth and row discipline.** Award up to 0.10 for
  distinct canonical stops covered, prorated to full credit at 7 stops. Award
  up to 0.05 for row discipline: full if there are no duplicate,
  aggregate, or wrong/unsupported rows; 0.025 if there are only 1-2 such rows;
  0.00 if there are 3 or more.

- **0.15 - Price and review semantic accuracy.** Score the first 12 distinct
  matched baseline rows used in checkpoint 3. Each row has two slots:
  `price_text` and `review`. Price is correct if it matches an accepted price
  phrase or close equivalent in `ground_truth.json`; review is correct if it
  contains a baseline review keyword or an equivalent host sentiment. Score
  `0.15 * correct_slots / 24`; unfilled slots from missing matched rows count
  as incorrect.

- **0.10 - New York weak/failed `$1` case.** Full credit requires a United
  States / New York City row that says no true `$1` American street-food winner
  was found, the dollar slice is no longer `$1`, or the samosa is only a weak
  not-really-American substitute. Award 0.05 if the failure is mentioned but
  the row fields are incomplete. Award 0.00 if New York is missing or presented
  as a straightforward successful `$1` American winner.

- **0.05 - Video-first source grounding.** Full credit requires trace evidence
  of watching the target video and no downloaded/read transcript, subtitle, or
  external summary artifacts. Award 0.025 if there is substantial video-frame
  evidence but a prohibited text artifact appears incidentally and is not used
  to populate row facts. Award 0.00 if the answer is text-source-driven,
  transcript/subtitle-driven, or lacks meaningful watched-video evidence.

## 6. Scoring Policy / Score Caps

Checkpoint credit is additive, then caps apply by `min(raw_score, cap)`.
Caps are intentionally strict because the public task forbids transcript
downloads and requires pinned-video row extraction. A run can pass only if the
final capped score is `>= 0.90`.

- **Cap at 0.30 - No usable deliverable.** The CSV is missing, empty,
  unparseable, or saved only outside `/tmp_workspace/results/`.

- **Cap at 0.45 - Required schema failure.** The CSV exists but lacks two or
  more required columns, or required fields are so misaligned that rows cannot
  be evaluated reliably.

- **Cap at 0.45 - Wrong or unidentified target.** The CSV does not identify
  Joshua Weissman's target video by usable `video_id`, title, or creator.

- **Cap at 0.55 - Mixed or wrong video sources.** Rows clearly combine content
  from multiple videos, creators, shorts, search snippets, or generic
  street-food summaries.

- **Cap at 0.45 - Transcript/subtitle-only behavior.** The final rows are
  reconstructed primarily from downloaded/read subtitle or transcript artifacts
  (`timedtext`, `.json3`, `.vtt`, `.srt`, `transcript.xml`,
  `transcript_full.txt`, mirror captions/summaries) and there is no meaningful
  row-level evidence from watched video frames or audio.

- **Cap at 0.70 - Prohibited transcript/subtitle reliance.** The trace shows
  the executor downloaded, parsed, or read subtitle/transcript artifacts and
  used them to populate row names, prices, or reviews, even if the executor
  also opened the watch page or saved screenshots. Visible captions inside
  screenshots alone do not trigger this cap.

- **Cap at 0.84 - Insufficient canonical recovery for pass.** Fewer than 10
  distinct baseline rows are recovered, or fewer than 6 canonical stops are
  covered.

- **Cap at 0.70 - Severe missing-row problem.** Only 6-7 distinct baseline
  rows are recovered, or only 4 canonical stops are covered.

- **Cap at 0.55 - Minimal canonical recovery.** Five or fewer distinct
  baseline rows are recovered, or three or fewer canonical stops are covered.

- **Cap at 0.80 - Wrong/unsupported row inflation.** Three or more output rows
  are duplicates, aggregates, or unsupported by the locked baseline.

- **Cap at 0.60 - Major wrong-row problem.** At least 25% of output data rows
  are wrong, duplicate, aggregate, or unsupported by the locked baseline.

- **Cap at 0.50 - Majority wrong rows.** At least half of output data rows are
  wrong, duplicate, aggregate, or unsupported by the locked baseline.

- **Cap at 0.84 - New York mishandled.** The New York segment is missing or is
  treated as a normal successful `$1` American street-food item instead of the
  canonical failed/weak `$1` case.

- **Cap at 0.65 - Empty price/review fields.** More than half of otherwise
  evaluable rows have blank or non-informative `price_text` or `review` fields.

- **Cap at 0.30 - Credential/privacy leak.** Any value whose environment
  variable is declared private is emitted in user-visible output.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - Stop. The CSV is present, the target video
  is fixed and single-source, at least 10 canonical rows across at least 6
  canonical stops are recovered, New York is handled correctly, and no
  pass-blocking cap applies.

- **Continue (`0.60 - 0.89` after caps)** - Request one focused repair when the
  CSV and target video are basically correct but the result is below pass due
  to fixable issues: 6-9 canonical rows, 4-5 stops, missing New York handling,
  a small number of wrong/duplicate rows, or incomplete price/review fields.
  If transcript/subtitle reliance caps the score, the follow-up should ask for
  a watched-video-only correction, not for polishing the existing transcript
  output.

- **Fail (`< 0.60` after caps)** - Stop and mark failed. This includes missing
  CSVs, wrong or mixed videos, transcript/subtitle-only answers, five or fewer
  canonical rows, three or fewer canonical stops, majority wrong/unsupported
  rows, or unrecoverable schema/content failures.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - authoritative target video, baseline rows,
  accepted price/review variants, and grading expectations.

## 9. Dynamic Content Note

This is a pinned offline grading task. Do not broaden scoring based on current
YouTube recommendations, search snippets, comments, external web pages, or a
model's prior knowledge of street food. If live video content, captions, or
external sources appear to conflict with `references/ground_truth.json`, grade
against the hidden ground truth and flag the drift rather than expanding the
accepted answer set.
