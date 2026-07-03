# Hidden Evaluation Rule — Hans Rosling / Gapminder Bubble Chart

## 1. Grading Philosophy

Judge the executor on whether it actually grounded the work in the TED video
and official Gapminder data, not on whether it produced plausible-looking chart
files.

The four deliverables must form one coherent answer:

- a real TED playback frame from the correct bubble-chart window
- a reproducible Python chart built from official Gapminder-derived data
- the required Gapminder-style encodings
- correct highlighting and analysis of the five countries in
  `sources/my_countries.csv`

Do not award pass-level credit for self-reported confidence, polished chart
styling, transcript-only reasoning, arbitrary mirrored datasets, or data values
that only happen to look plausible.

## 2. Task Contract

The executor must produce these exact files under `/tmp_workspace/results/`:

- `rosling_chart_screenshot.png`
- `rosling_chart_reproduced.png`
- `rosling_chart_reproduced.py`
- `my_countries_analysis.md`

Required filenames are part of the contract. JPEG-only alternatives or files
saved elsewhere may be inspected as supporting evidence, but they do not satisfy
the exact artifact-existence checkpoint.

The public request requires direct playback of the TED talk. Transcript,
caption, thumbnail, or data-page-only workflows are not canonical even if the
final chart looks reasonable.

## 3. Source-Selection and Target-Resolution Rules

Use the on-disk task files as authoritative:

- source countries: `/tmp_workspace/clawbench/sources/my_countries.csv`
- hidden expected values: `references/highlighted_countries_2003.csv`
- hidden TED frame anchor: `references/rosling_reference_frame_13m30s.png`
- hidden structured facts: `references/ground_truth.json`

The expected highlighted-country set is exactly:

- `Brazil`
- `China`
- `India`
- `Nigeria`
- `United States` (alias `USA` is acceptable only as a label alias)

The chart may contain additional countries, but the five requested countries
must be visually distinguishable from the background points and discussed in
the analysis. Highlighting the wrong countries, omitting requested countries, or
using unrelated examples cannot be repaired by a good-looking global scatter.

## 4. Locked Ground Truth

TED talk facts:

- URL: `https://www.ted.com/talks/hans_rosling_the_best_stats_you_ve_ever_seen`
- title: `The best stats you've ever seen`
- speaker: `Hans Rosling`
- duration: `1172` seconds
- target chart window: approximately `540-840` seconds
- hidden reference frame: `810` seconds (`13:30`)

The screenshot is graded against the hidden reference frame, not against a
claim in the writeup. A full-credit screenshot must be an actual TED playback
frame from the target chart window and should visibly match the 13:30 reference
family: Rosling on the TED stage with a Gapminder bubble chart showing year
`2003`, a GDP-per-capita x-axis, population-sized bubbles, and the same overall
blue projection/stage geometry. Do not accept the earlier fertility-vs-life-
expectancy chart, later internet-users chart, static thumbnails, screenshots of
transcript pages, or a recreated chart as the TED screenshot.

The hidden 13:30 TED frame itself shows the GDP-per-capita chart family from
the talk; its visible y-axis may differ from the reproduced chart spec below.
Grade the screenshot checkpoint by visual match to the hidden TED frame, and
grade the reproduction checkpoint by the explicit reproduced-chart spec.

Reproduced chart facts:

- target year: `2003`
- acceptable nearby years: `2002` or `2004` only if the executor explicitly
  explains why that nearby year was selected
- x-axis: GDP per capita, PPP, on a logarithmic scale
- y-axis: life expectancy
- bubble size: population
- color: continent or an equivalent broad world-region grouping

Official Gapminder data sources are anchored by `ground_truth.json`:

- Gapminder data landing page
- GDP per capita documentation/download
- life expectancy documentation/download
- population documentation/download

Official Gapminder DDF/open-numbers equivalents are acceptable only when the
trace or script shows they came from the Gapminder data portal and the
highlighted-country values align with `highlighted_countries_2003.csv` within
reasonable rounding tolerance. Randomly generated data, hand-entered invented
coordinates, package defaults for the wrong year, or synthetic substitutions
for the required metrics are not acceptable source grounding.

For the five highlighted countries, the expected 2003 relationships are:

- United States is far right with high life expectancy.
- China is right of India and above India.
- Nigeria has the lowest life expectancy among the highlighted set.
- Brazil is right of China on GDP per capita and slightly above China on life
  expectancy.
- China and India are the two largest highlighted bubbles by population.

A pass requires these locked facts to be satisfied after all caps are applied.
Artifacts existing on disk cannot compensate for the wrong TED frame, wrong
year, wrong axes, missing population encoding, wrong highlighted countries, or
fabricated data.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Required output files.** All four exact files in Section 2 exist in
  `/tmp_workspace/results/`, are non-empty, and the two PNGs are valid images.
  The Python file and Markdown file must be readable text. Award 0.00 for this
  line if any exact required file is missing, even if a JPEG or differently
  named equivalent exists.

- **0.20 - TED playback screenshot.** `rosling_chart_screenshot.png` is a real
  frame captured from direct playback of the TED page and matches the target
  chart window in Section 4. Full credit requires a frame from approximately
  `540-840` seconds, preferably near the hidden 13:30 reference, with the TED
  stage/video context or the projected chart clearly visible. Award no more
  than 0.08 on this line for a real TED frame from the wrong Rosling chart, and
  0.00 for thumbnails, transcripts, recreated charts, or unrelated media.

- **0.25 - Reproduced chart encodings.** The reproduction visibly and in the
  script uses the required encodings: GDP per capita on the x-axis (0.05),
  logarithmic x-scale (0.05), life expectancy on the y-axis (0.05), bubble area
  or radius scaled by population (0.05), and continent/equivalent region color
  grouping with labels or legend (0.05). Do not give credit for an encoding
  that appears only in text but is absent from the plot or script.

- **0.15 - Official data and target year.** The script uses official
  Gapminder-derived GDP, life expectancy, and population data and selects 2003,
  or 2002/2004 with explicit justification tied to data availability or the
  TED frame. Full credit requires the script to be reproducible from its stated
  inputs without relying on unexplained local scratch files. Award at most 0.06
  on this line if the source is plausibly Gapminder-derived but the year is
  outside `2002-2004`, and 0.00 if the plotted data are fabricated or the
  required metrics are synthetically substituted.

- **0.15 - Highlighted-country visual treatment.** All five countries from
  `my_countries.csv` are present, visually highlighted, and labeled or
  otherwise unambiguously identifiable in `rosling_chart_reproduced.png`.
  Bubble sizes for China and India must be visibly the two largest among the
  highlighted set. Award proportional credit only for correctly highlighted
  requested countries; highlighting extra countries is acceptable only if it
  does not obscure the requested five.

- **0.15 - Country analysis accuracy and consistency.** `my_countries_analysis.md`
  correctly explains the five Section 4 relationships, cites or summarizes the
  chosen year/data basis, and remains consistent with the final chart and
  script. Award 0.03 per correct relationship. Zero any relationship that is
  contradicted elsewhere in the analysis, by the plotted chart, or by the
  hidden 2003 CSV.

## 6. Scoring Policy / Score Caps

Score each checkpoint first, then apply all relevant caps by taking the minimum
of the checkpoint total and every applicable cap.

- **Cap at 0.30 - No meaningful deliverables.** Fewer than two of the four
  required artifacts exist, or the output directory contains only scratch
  frames/data with no final chart and analysis.

- **Cap at 0.35 - No direct TED playback evidence.** The trace and artifacts
  show only transcript/caption/API/thumbnail use, or the screenshot is not from
  TED playback at all.

- **Cap at 0.45 - Wrong TED frame.** The screenshot is a real TED frame but not
  from the target `540-840` second bubble-chart window or does not resemble the
  hidden 13:30 reference. This includes the earlier fertility-vs-life-expectancy
  chart and the later internet-users chart.

- **Cap at 0.70 - Wrong reproduction year.** The reproduced chart uses a year
  outside `2002-2004`, or mixes years without a justified, documented reason.
  Cap at 0.80 instead if it uses `2002` or `2004` but fails to explain the
  nearby-year choice.

- **Cap at 0.50 - Wrong axes or missing log scale.** The reproduction does not
  use GDP per capita on the x-axis, does not use life expectancy on the y-axis,
  substitutes child survival or another y-metric for the reproduced chart, or
  plots GDP on a linear x-scale.

- **Cap at 0.60 - Missing population bubble encoding.** The reproduction is a
  scatter/line/bar chart with constant-size points or otherwise fails to encode
  population in bubble size.

- **Cap at 0.70 - Highlight failure.** One or two requested countries are not
  visibly highlighted or identifiable. Cap at 0.55 if three or more requested
  countries are missing, if the highlighted set is mostly different from
  `my_countries.csv`, or if country labels are assigned to visibly wrong
  points.

- **Cap at 0.55 - Wrong highlighted-country relationships.** The analysis or
  chart contradicts two or more locked relationships from Section 4, even if
  the countries are present.

- **Cap at 0.45 - Fabricated or synthetic data.** The chart uses random,
  hand-invented, hard-coded, or untraceable country values; fabricates official
  source claims; or derives the required metrics from unrelated formulas instead
  of using official Gapminder-derived GDP, life expectancy, and population data.

- **Cap at 0.60 - Missing or non-inspectable Python script.** The script is
  absent, empty, not Python, or cannot reasonably be inspected to verify the
  data source, year, and encodings.

- **Cap at 0.80 - Inconsistent final answer.** The screenshot, chart, script,
  and Markdown analysis contain unacknowledged contradictions about chart
  definitions, years, or country values, but the core artifacts are otherwise
  present. Do not apply this cap solely because the TED screenshot's visible
  y-axis differs from the reproduced life-expectancy chart, as long as the
  executor accurately distinguishes those two checkpoints.

A run passes only if the final capped score is `>= 0.90`.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - Use only when the executor has the exact
  required artifacts, a TED screenshot from the hidden-reference chart window,
  official 2003 or justified 2002/2004 Gapminder data, correct encodings, all
  five highlighted countries, accurate relationship analysis, and no applicable
  cap below 0.90.

- **Continue (`0.60 - 0.89` after caps)** - Use when the work is substantially
  present and repairable in one follow-up, such as a correct chart needing the
  target-year data, incomplete country analysis, missing exact PNG filenames, or
  one omitted highlighted country.

- **Fail (`< 0.60` after caps)** - Use when the core task is not recoverable
  within a normal follow-up. This includes no real TED playback evidence,
  wrong-frame screenshots capped at 0.45, wrong axes/log-scale collapses capped
  at 0.50, fabricated data capped at 0.45, mostly wrong highlighted countries
  capped at 0.55, or absent/non-inspectable scripts capped below 0.60.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - TED metadata, chart window, canonical data
  source URLs, chart spec, accepted years, and locked relationships.
- `references/highlighted_countries_2003.csv` - expected highlighted-country
  values and positions for 2003.
- `references/rosling_reference_frame_13m30s.png` - visual anchor for the TED
  screenshot checkpoint.

## 9. Dynamic Content Note

The task should be judged against the hidden snapshot, not against later TED or
Gapminder page changes. If a live page has changed, use the hidden reference
frame, hidden CSV, and `ground_truth.json` as the authoritative grading source.
