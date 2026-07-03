# Hidden Evaluation Rule — Scaling Laws Figure 5 Aspect Ratio

## 1. Grading Philosophy

Grade whether the executor found the correct paper and recreated the **middle
Aspect Ratio panel of Figure 5** as a faithful matplotlib figure. This is not a
pixel-perfect tracing task, but a passing answer must be much more than a
plausible three-line U-shaped chart.

The primary target is the rendered PNG's visual resemblance to
`references/figure5_middle_aspect_ratio.png`. Script arrays and numeric anchors
are useful audit evidence, but they are secondary: a chart can have plausible
data and still fail if it looks like a different standalone redraw rather than
the source crop.

High scores require all of:

- correct source grounding: `Scaling Laws for Neural Language Models`,
  arXiv `2001.08361`, page 8, Figure 5 middle panel
- correct chart semantics: logarithmic aspect-ratio x-axis and percent
  `Loss Increase` y-axis
- all three required parameter series with the original legend labels
- source-like visual layout: compact paper-panel proportions, similar plot
  frame occupancy, margins, gridline density, axis/tick placement, legend
  placement, annotation placement, and vertical guide-line placement
- quantitatively close curve geometry as it appears in the crop, especially the
  shallow midrange minima above the bottom axis and the high right-tail rise of
  the `274M Params` curve
- visible evidence of at least one draw, compare-to-original, and revise cycle
- final PNG, reproducible Python script, and notes saved under
  `/tmp_workspace/results/`

Do not award a pass based on artifact existence, polished formatting, script
data, or the executor's self-confidence if the final rendered PNG is not
visually anchored to the hidden reference crop.

## 2. Task Contract

The public task asks the executor to:

1. download or otherwise obtain the arXiv paper `Scaling Laws for Neural
   Language Models`
2. identify Figure 5 and select the **middle** panel labeled `Aspect Ratio`
3. recreate that panel with Python + matplotlib
4. compare the first plotted version against the original and revise at least
   once
5. save at least these files under `/tmp_workspace/results/`:
   - `figure5_aspect_ratio_recreated.png`
   - `figure5_aspect_ratio_recreated.py`
   - `notes.md`

The final required PNG is the scored image. Extra crops, PDFs, comparison
images, or notebooks may support process evidence, but they do not replace the
required deliverables.

## 3. Target Resolution Rules

Use `references/ground_truth.json` and
`references/figure5_middle_aspect_ratio.png` as the canonical hidden snapshot.
The target facts are:

- paper title: `Scaling Laws for Neural Language Models`
- arXiv ID: `2001.08361`
- target page in the shipped render: page 8
- target figure and panel: Figure 5, middle panel only
- panel title/label: `Aspect Ratio`
- x-axis label: `Aspect Ratio (d_model / n_layer)`
- y-axis label: `Loss Increase`
- x-axis scale: logarithmic, with the visible domain roughly `4` to `1500`
- y-axis units: percentage loss increase, with the visible scale reaching
  `10%`
- required legend labels: `50M Params`, `274M Params`, `1.5B Params`

Do not give credit for reproducing the left `Feed-Forward Ratio` panel, the
right `Attention Head Dimension` panel, another figure from the paper, or a
generic scaling-law plot.

## 4. Ground-Truth Snapshot

`references/ground_truth.json` contains approximate curve anchors. Interpret
y-values as percentage points, not fractions. If the submitted script exposes
the data arrays, use log-x interpolation between submitted points when checking
anchors. If only the image is available, judge the same anchors visually against
the hidden crop.

Canonical approximate anchors:

- `50M Params`: `(8, 3.4)`, `(12, 3.0)`, `(25, 2.0)`, `(50, 1.3)`,
  `(80, 1.0)`, `(150, 1.4)`, `(300, 2.6)`, `(600, 5.5)`
- `274M Params`: `(6, 2.0)`, `(10, 1.7)`, `(15, 1.5)`, `(25, 1.2)`,
  `(50, 1.1)`, `(100, 1.3)`, `(220, 1.8)`, `(350, 3.8)`,
  `(1000, 8.2)`
- `1.5B Params`: `(8, 2.9)`, `(12, 2.3)`, `(25, 1.4)`, `(40, 1.1)`,
  `(90, 1.25)`, `(250, 1.6)`, `(600, 3.8)`

For high-score curve fidelity, require these visual/numeric facts:

- all three curves are shallow U-shapes on a log x-axis, not straight-line
  decorations on a linear axis
- each series has a minimum near `40-120` aspect ratio and visually around
  `1%` loss increase; the minima should not touch the bottom axis
- left side ordering is approximately blue/green above orange near the lowest
  x-values
- right side ordering is `274M Params` highest, `50M Params` next,
  `1.5B Params` lowest
- the `274M Params` right tail reaches roughly `8%` near `10^3`; `50M Params`
  reaches roughly `5-6%`, and `1.5B Params` reaches roughly `3-4%`
- the panel includes the original-style upper-left legend, bold/centered
  explanatory annotation, and two vertical guide lines marking the broad good
  architecture range

Anchor tolerance for full curve credit: at least `19 / 24` anchors within
`+/-1.0` percentage point for targets at or below `3%`, and within `+/-1.5`
percentage points for targets above `3%`, with no required series failing its
minimum-region or right-tail-ordering check.

Anchor credit is not pass-sufficient. A submission that matches the anchors but
has obviously different visual layout, plot aspect, margins, gridline density,
legend placement, annotation placement, or guide-line placement must be capped
below pass.

## 5. Checkpoint Rubric

Weights sum to `1.00`.

- **0.08 - Source and panel grounding.** Full credit requires the notes,
  transcript, or artifacts to identify the exact paper, arXiv ID or title,
  page 8/Figure 5, and the middle `Aspect Ratio` panel. Partial credit is
  allowed only when the correct paper is found but page/panel evidence is
  incomplete.

- **0.07 - Required deliverables and reproducibility.** Full credit requires
  the final PNG, Python script, and notes in `/tmp_workspace/results/`. The
  script must be a real matplotlib program that can regenerate the final-style
  chart without relying on hidden references, screenshots, or manual post-edit
  steps. Award at most `0.04` here if one required artifact is missing, and
  `0.00` if the required PNG is missing.

- **0.10 - Axes, scales, labels, and units.** Full credit requires a log x-axis
  spanning roughly `4-1500`, major ticks around `10^1`, `10^2`, `10^3`, x-label
  equivalent to `Aspect Ratio (d_model / n_layer)`, y-label `Loss Increase`,
  percent y-ticks, and a visible y-scale reaching about `10%`. If the image is
  plotted in fractional units but formatted and visually scaled exactly as
  percent loss, accept it. If the visible y-axis tops out near `6%`, this line
  cannot exceed `0.05`.

- **0.35 - Visual similarity to the hidden crop.** Full credit requires the
  rendered PNG to look like a recreation of
  `figure5_middle_aspect_ratio.png`: compact paper-panel proportions, similar
  plot-frame occupancy, thin axes/gridlines, similar whitespace, upper-left
  legend location, centered annotation location, two vertical guide lines in
  the same broad x-region, and no unrelated standalone title or modernized
  chart theme. A clean standalone chart with correct labels but visibly
  different layout should receive at most `0.12` here.

- **0.25 - Curve fidelity.** Full credit requires the anchor and trend checks
  in Section 4. Award about `0.18` if the plot is recognizably the same panel
  but misses several anchors or one endpoint amplitude. Award about `0.10` if
  it is only a generic three-curve U-shape with the right labels. Award `0.00`
  if the curves are monotonic, flat, randomly shaped, or match another panel.

- **0.10 - Compare-and-refine evidence.** Full credit requires observable
  evidence that an initial plot was compared against the original and then
  revised. Accept saved comparison/intermediate images, transcript evidence of
  reopening the original after plotting, or notes that cite concrete visual
  corrections and are supported by artifacts or command history. Notes that
  merely claim "I iterated" without observable support earn at most `0.03`.

- **0.05 - Rendering honesty.** The script and notes should make clear that
  the output is an approximate matplotlib recreation, not a copied crop or
  exact digitization. The scored PNG must be the script-rendered figure. Zero
  this line if the final image was manually edited after rendering or if the
  notes claim exact source data that were not actually available.

Total: `0.08 + 0.07 + 0.10 + 0.35 + 0.25 + 0.10 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

Award checkpoint credit first, then apply all relevant caps by `min`.

- **Cap at 0.25 - No usable final figure.** The required PNG is absent,
  unreadable, blank, or not a chart.
- **Cap at 0.25 - Wrong paper or wrong figure.** The attempt is based on a
  different paper, a different arXiv record, or not Figure 5.
- **Cap at 0.35 - Wrong panel.** The output reproduces the left
  `Feed-Forward Ratio` panel, the right `Attention Head Dimension` panel, or a
  mixture of panels instead of the middle `Aspect Ratio` panel.
- **Cap at 0.45 - Original crop copied instead of recreated.** The final PNG
  is just a screenshot/crop of the paper or an image edit of the hidden/source
  panel rather than a matplotlib recreation.
- **Cap at 0.50 - Core semantics missing.** The final chart lacks log-x
  behavior, uses the wrong y-variable, or has fewer than two of the three
  required parameter series.
- **Cap at 0.65 - One required series or legend identity missing.** Exactly
  one required series is absent, mislabeled, or visually indistinguishable from
  another series.
- **Cap at 0.70 - Wrong trend family.** The target paper/panel is named but
  the curves are not shallow U-shapes with midrange minima and right-tail
  degradation.
- **Cap at 0.74 - Generic but decorated chart.** The chart has the right
  labels and three U-shaped curves but omits most original panel structure
  such as the annotation, two vertical guide lines, upper-left legend, percent
  y-ticks, or paper-like aspect/styling.
- **Cap at 0.89 - Visual mismatch despite good data.** Apply when the script
  or arrays match most anchors but the final rendered PNG does not visually
  resemble the hidden crop: materially different aspect ratio, plot-frame
  occupancy, margins, tick/grid density, legend placement, annotation position,
  guide-line position, line/marker scale, or standalone-chart presentation.
  This cap is intended for polished charts that are semantically correct but
  visually not a faithful reconstruction.
- **Cap at 0.84 - Severe visual mismatch.** Apply when the output is clearly a
  modern standalone explanatory chart or different layout even though it has
  the right source, axes, labels, and broad curve trends. Large visual
  dissimilarity cannot pass on numeric anchors alone.
- **Cap at 0.82 - Compressed right tail / y-scale false positive.** Apply when
  the output is structurally the right chart but the y-axis or data are scaled
  too low, such as a visible y-axis maximum below `8%`, the `274M Params`
  right tail below `7%` near `10^3`, or all right-tail endpoints staying below
  about `6%`.
- **Cap at 0.82 - Hand-waved curve geometry.** Apply when the plot is
  recognizable but fewer than `16 / 24` Section 4 anchors are within tolerance,
  any required series lacks the source-like midrange minimum above the bottom
  axis, or the right-tail ordering is not `274M > 50M > 1.5B`.
- **Cap at 0.84 - Missing script or non-reproducible script.** The final image
  exists, but `figure5_aspect_ratio_recreated.py` is missing, does not run in a
  normal Python/matplotlib environment, or cannot regenerate a materially
  similar image.
- **Cap at 0.84 - Missing or ungrounded notes.** `notes.md` is absent or does
  not state which paper, figure/panel, and concrete post-comparison
  corrections were used.
- **Cap at 0.80 - Self-reported refinement only.** The notes describe
  iterations, but there is no observable intermediate/comparison artifact,
  transcript evidence, command evidence, or script history showing that a
  plotted version was compared with the original and revised.
- **Cap at 0.30 - Credential or privacy leak.** Any value from a protected
  environment variable or private credential appears in user-visible output.

A run passes only if the final score is `>= 0.90` after caps.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) - stop. The final figure is the correct
  middle Figure 5 panel, with correct deliverables, source grounding, axis
  semantics, curve geometry, refinement evidence, and clear visual resemblance
  to `figure5_middle_aspect_ratio.png`.
- **Continue** (`0.60 - 0.89` after caps) - request one focused fix when the
  attempt is on the correct paper/panel and has recoverable issues such as a
  compressed y-axis, missing annotation/guide lines, weak right-tail endpoints,
  standalone layout that does not resemble the crop, missing comparison
  evidence, or a missing note/script.
- **Fail** (`< 0.60` after caps) - stop and mark failed. This includes wrong
  paper/figure/panel, copied screenshots instead of matplotlib recreation, no
  usable final figure, missing core axis semantics, or outputs that are generic
  charts with no evidence of examining the original panel.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec
- `references/ground_truth.json` - target facts and approximate curve anchors
- `references/figure5_middle_aspect_ratio.png` - authoritative visual crop of
  the middle panel
- `references/scaling_laws_page8_full.png` - full page context for Figure 5

## 9. Dynamic Content Note

The paper and target panel are static. Network or PDF rendering differences do
not change the expected answer. If arXiv or rendered pixels differ slightly,
judge against the hidden crop and the approximate anchors in
`references/ground_truth.json`.
