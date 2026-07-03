# Hidden Evaluation Rule — LLaMA Figure 2 Reasoning Curves

## 1. Grading Philosophy

Judge whether the executor recreated the three requested panels from the actual
Figure 2 of `LLaMA: Open and Efficient Foundation Language Models`, not merely
whether it produced polished learning-curve plots with the right titles.
The primary target is visual similarity to the hidden panel crops
(`figure2_triviaqa.png`, `figure2_siqa.png`, and `figure2_piqa.png`). Endpoint
values, labels, and script data are necessary audit evidence, but they are not
sufficient for pass-level credit if the rendered panels look like generic
illustrative curves instead of the source figure.

Full-credit work must show:

- correct source grounding: arXiv `2302.13971`, Figure 2, page 8 in the hidden
  render
- the exact requested panels: `TriviaQA`, `SIQA`, and `PIQA`
- the original chart semantics: 4 solid LLaMA size curves, 1 dashed Chinchilla
  baseline, accuracy vs. `Billion of tokens`
- visual trace fidelity to the hidden crops, including endpoint order,
  approximate endpoint values, curve extents, early-rise shape, local wiggles,
  crossings / near-crossings, and unequal spacing between series
- source-like rendered layout: panel aspect, margins, grid density, line
  weights, dashed baseline placement, and empirical trace texture
- the required output files plus visible evidence that at least one comparison
  against the source figure informed a revision

Do not award pass-level credit for outputs that only satisfy the artifact
contract, labels, axes, and legend. Generic monotonic curves, table-value
substitutions, and coarse hand sketches are partial-credit outcomes.

## 2. Task Contract

The public task asks the executor to:

1. download or otherwise consult the arXiv paper `LLaMA: Open and Efficient
   Foundation Language Models`
2. locate Figure 2 on the correct page
3. recreate the `TriviaQA`, `SIQA`, and `PIQA` panels with Python + matplotlib
4. compare the first draft to the source figure and make at least one
   correction
5. save all required outputs under `/tmp_workspace/results/`

Required final deliverables:

- `/tmp_workspace/results/figure2_triviaqa.png`
- `/tmp_workspace/results/figure2_siqa.png`
- `/tmp_workspace/results/figure2_piqa.png`
- `/tmp_workspace/results/figure2_recreate.py`
- `/tmp_workspace/results/notes.md`

Aliases for the three image names are not accepted for full artifact credit.
Extra diagnostic crops or PDFs are allowed but do not replace the required
outputs.

## 3. Source-Selection and Target-Resolution Rules

Use `references/ground_truth.json` as the canonical structured target and the
hidden reference images as the authoritative visual target:

- `references/llama_page8_full.png` - full hidden page render
- `references/figure2_full.png` - full Figure 2 crop
- `references/figure2_triviaqa.png` - target `TriviaQA` panel
- `references/figure2_siqa.png` - target `SIQA` panel
- `references/figure2_piqa.png` - target `PIQA` panel

The visible PDF rendering, antialiasing, and font metrics may differ slightly
from the hidden assets. Those differences are not material. Panel identity,
series semantics, curve geometry, relative ordering, and approximate values are
material.

When the submitted image and generating script disagree, grade the rendered
image as the final answer, then use the script to clarify intent, point counts,
data anchors, and whether the plot was generated from source-figure traces or
from generic formulas.

## 4. Ground-Truth Snapshot

The target paper is `LLaMA: Open and Efficient Foundation Language Models`,
arXiv `2302.13971`. The target is `Figure 2`, captioned `Evolution of
performance on question answering and common sense reasoning during training`.
The required panels are `TriviaQA`, `SIQA`, and `PIQA`.

Common chart facts:

- x-axis label: `Billion of tokens`
- y-axis label: `Accuracy`
- x-axis span: approximately `0` to `1500`, with ticks at `0, 250, 500, 750,
  1000, 1250, 1500`
- LLaMA series and expected colors: `7B` blue, `13B` orange, `33B` green,
  `65B` red
- Chinchilla: purple dashed horizontal baseline
- 7B and 13B traces terminate near `1000B` tokens; 33B and 65B traces continue
  to about `1400B` tokens. Drawing all series cleanly to `1500B` is a visible
  geometry error.

Approximate right-edge targets from `ground_truth.json`:

| Panel | Chinchilla | LLaMA 7B | LLaMA 13B | LLaMA 33B | LLaMA 65B |
| --- | ---: | ---: | ---: | ---: | ---: |
| `TriviaQA` | 64.1 | 56.5 | 63.3 | 69.9 | 72.4 |
| `SIQA` | 51.3 | 48.8 | 50.6 | 50.6 | 51.9 |
| `PIQA` | 81.8 | 79.4 | 80.1 | 81.9 | 82.8 |

Pass-level endpoint tolerance:

- `TriviaQA`: LLaMA endpoints should be within about `2.0` accuracy points of
  the table above, and the baseline should be within about `1.0`.
- `SIQA`: LLaMA endpoints should be within about `0.8` accuracy points, and
  the baseline should be within about `0.4`.
- `PIQA`: LLaMA endpoints should be within about `0.8` accuracy points, and
  the baseline should be within about `0.5`.

Panel-specific visual anchors:

- `TriviaQA`: very steep early rise, then noisy saturation; right-edge order is
  `65B > 33B > 13B > 7B`; 13B ends near the Chinchilla baseline, not near 56;
  33B and 65B continue beyond the 7B/13B traces.
- `SIQA`: narrow `40-52` y-range; all curves jump quickly into the high 40s
  and then fluctuate; 13B, 33B, and 65B stay close with local reversals /
  near-crossings; 7B is lower and terminates near `1000B`.
- `PIQA`: `65B` ends modestly above Chinchilla; Chinchilla sits near or
  roughly level with 33B near the right edge; 7B and 13B remain below 33B with
  13B slightly above 7B; lower LLaMA curves form a tight high-70s /
  low-80s band rather than evenly spaced parallel bands.

Use the denser `trace_points_approx` entries in `ground_truth.json` when
checking mid-curve shape. These points are still approximate visual anchors;
they do not replace the requirement that each rendered panel visually resemble
the hidden crop.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.06 - Source grounding.** Full credit requires clear evidence that the
  executor identified the correct paper, arXiv ID, page, Figure 2, and caption.
  Zero this line for the wrong paper, wrong figure, or ungrounded guessing.

- **0.06 - Required artifacts.** All five required files must exist in
  `/tmp_workspace/results/` with the exact required names. The script must run
  or be plausibly runnable without hidden local paths, and the three images must
  be final rendered plots rather than placeholder crops or empty figures. Award
  no more than 0.04 here if any required image is missing, and no more than 0.05
  if only `notes.md` or the script is missing.

- **0.10 - Panel identity, axes, and styling.** The three outputs must be the
  three required panels with correct titles, approximate y-axis ranges
  (`TriviaQA` about 20-70+, `SIQA` 40-52, `PIQA` 65-82.5), x-axis token scale,
  grid/axis style close to the source, and visible labels or legends sufficient
  to identify the plotted series. Style does not need pixel-perfect fonts, but
  a modernized chart theme that obscures source-figure proportions should lose
  credit.

- **0.13 - Series semantics.** Each panel must contain exactly four solid LLaMA
  traces for 7B, 13B, 33B, and 65B plus one dashed horizontal Chinchilla
  baseline. Colors, line styles, legend labels, and trace extents must match
  the source. Deduct heavily for extra model curves, missing curves, wrong
  dashed/solid semantics, non-horizontal Chinchilla, or all LLaMA curves drawn
  through the full x-axis.

- **0.50 - Visual geometry against hidden crops.** Score about one third of
  this credit per panel. A panel earns full visual-geometry credit only if its
  rendered appearance resembles the corresponding hidden crop: early rise,
  local wiggles, saturation shape, crossings / near-crossings, endpoint
  ordering, endpoint spacing, curve termination points, baseline placement,
  trace thickness, and panel proportions. A panel that has the right labels but
  generic smooth monotonic curves earns at most `0.05` of its panel share. A
  panel with materially wrong right-edge ordering, endpoint values, or trace
  extents earns at most `0.04` of its panel share.

- **0.10 - Compare-and-refine evidence.** Full credit requires visible evidence
  of at least one source comparison and correction: transcript, notes, source
  crops, before/after images, or script comments tied to specific Figure 2
  discrepancies. A self-reported "I compared it" statement with no concrete
  correction earns at most 0.04.

- **0.05 - Reproducibility and honesty.** The submitted script should be the
  generator for the final images and should not misrepresent invented formulas
  as exact training logs. Approximate digitization is acceptable if described
  honestly. Zero this line for unrelated scripts, hidden dependencies, or
  fabricated claims that the original raw training logs were used.

Total: `0.06 + 0.06 + 0.10 + 0.13 + 0.50 + 0.10 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

Award partial credit line-by-line under the checkpoint rubric, then apply all
relevant caps below by taking the minimum. Caps target observed false positives
and unrecoverable task failures; they override polished presentation.

- **Cap at 0.20 - No usable deliverables.** None of the three required plot
  images exists in `/tmp_workspace/results/`.

- **Cap at 0.25 - Wrong source.** The work is based on a paper other than
  arXiv `2302.13971`, a non-Figure-2 plot, or unrelated training curves.

- **Cap at 0.35 - Wrong panel set.** The executor does not recreate at least
  two of `TriviaQA`, `SIQA`, and `PIQA`.

- **Cap at 0.45 - Missing required panel.** Exactly one of the three required
  panels is absent or replaced by a crop / screenshot instead of a recreated
  matplotlib plot.

- **Cap at 0.50 - Broken series semantics.** Any required panel lacks the four
  LLaMA size curves, lacks the dashed Chinchilla baseline, adds unrelated
  series, or confuses baseline and LLaMA line styles in a way that changes the
  chart meaning.

- **Cap at 0.60 - No evidence of consulting Figure 2.** The outputs could have
  been produced from the prompt and public model-performance priors alone:
  correct labels may exist, but there is no source page, crop, transcript, or
  concrete notes showing Figure 2 inspection.

- **Cap at 0.70 - Different curve family.** One or more panels is visibly not
  the same curve family as the hidden crop, even if it has the right title,
  axes, and legend.

- **Cap at 0.89 - Endpoint-correct but visually mismatched.** Apply when the
  endpoint values and broad ordering are mostly correct, but the rendered
  panels do not visually resemble the hidden crops in empirical trace texture,
  local wiggles, crossings / near-crossings, spacing between curves, plot
  proportions, or trace extents. Numeric endpoint matching alone cannot pass.

- **Cap at 0.74 - Coarse seven-point redraw.** The final curves are mostly
  straight segments through a small grid such as `0, 250, 500, ..., 1500`, with
  no local wiggles, no empirical trace texture, and all curves extended to the
  same right edge. This cap applies even when endpoint ordering is roughly
  correct.

- **Cap at 0.78 - Generic monotonic / illustrative redraw.** The panels look
  like clean illustrative learning curves rather than digitized empirical
  traces: smooth monotonic bands, evenly spaced series, little or no noise, and
  no source-specific crossings / near-crossings. This includes upsampled
  polylines that visually remain coarse and monotonic.

- **Cap at 0.80 - Wrong curve extents.** In two or more panels, 7B and 13B are
  drawn to `1500B` instead of stopping near `1000B`, or 33B/65B do not extend
  to about `1400B`. If this occurs in only one panel, cap at 0.84.

- **Cap at 0.80 - PIQA baseline/order failure.** In `PIQA`, 65B is not above
  Chinchilla near the right edge, 7B/13B are not clearly below the Chinchilla
  baseline, or the 33B curve is far below/above the baseline rather than close
  to it. If the order is broadly right but the lower-curve band is spread too
  evenly or too high, cap at 0.82.

- **Cap at 0.82 - Formula-generated synthetic traces.** The script primarily
  generates all panels from parametric log/log-linear/spline formulas plus
  synthetic noise, with no multi-point digitization of the hidden/source crop.
  Synthetic noise does not by itself count as source-figure fidelity.

- **Cap at 0.82 - TriviaQA table-value substitution.** `TriviaQA` endpoints are
  anchored to table values or generic benchmark scores instead of Figure 2
  traces, e.g. 7B near `50`, 13B near `56-57`, 33B near `65`, or 65B near `68`.
  The source crop has substantially higher right-edge values for all four
  LLaMA traces.

- **Cap at 0.84 - Table endpoints conflict with Figure 2.** The script or notes
  explicitly prioritize paper table values over the Figure 2 visual traces for
  any panel, and this causes visible endpoint or spacing errors. Figure 2 is
  the target, not the paper's final benchmark table.

- **Cap at 0.84 - One materially wrong panel.** Two panels are passable, but
  one required panel has materially wrong shape, endpoint ordering, endpoint
  values, or series extents.

- **Cap at 0.84 - Missing concrete revision evidence.** Final plots exist, but
  there is no concrete compare-and-refine evidence tied to a source-figure
  discrepancy. A note that merely says "revised" without what changed is not
  enough for pass-level credit.

- **Cap at 0.84 - Missing generator.** The three images exist, but
  `figure2_recreate.py` is missing, unrelated, or cannot plausibly regenerate
  the final plots.

Runs capped below 0.90 cannot pass. Artifact existence, nice formatting, or
executor confidence cannot raise a run above an applicable cap.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) - executor should stop. A pass requires all
  required artifacts, correct source grounding, correct series semantics, and
  all three rendered panels close enough to the hidden crops in visual layout,
  empirical trace geometry, endpoints, and extents.

- **Continue** (`0.60 - 0.89` after caps) - supervisor may request one follow-up
  if the executor is on the correct paper and has fixable artifacts, such as a
  missing revision note, one panel with wrong endpoint spacing, wrong curve
  extents, or over-smoothed traces that can still be re-digitized.

- **Fail** (`< 0.60` after caps) - no further follow-up is warranted. This
  includes wrong paper/figure, missing most required panels, no usable plots,
  broken chart semantics, or no evidence that Figure 2 was consulted.

If a run scores at or above 0.60 by raw rubric but is capped below 0.60 for a
fundamental task violation, use the capped score and fail.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec
- `references/ground_truth.json` - paper ID, target panels, baseline values,
  and approximate endpoints
- `references/llama_page8_full.png` - authoritative full page render
- `references/figure2_full.png` - authoritative full Figure 2 crop
- `references/figure2_triviaqa.png` - authoritative target panel crop
- `references/figure2_siqa.png` - authoritative target panel crop
- `references/figure2_piqa.png` - authoritative target panel crop

## 9. Dynamic Content Note

Offline task. The paper and hidden crops are static for grading. Do not require
live arXiv access during supervision if the executor already left sufficient
source-grounding evidence. If a live PDF render differs slightly from the hidden
crop, grade against the hidden crop and `ground_truth.json`.
