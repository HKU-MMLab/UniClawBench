# Hidden Evaluation Rule — task_104_04_panel_figure3_reproduction

## 1. Grading Philosophy

Judge the final image by careful visual comparison against the source panel,
not by the executor's explanation, saved helper crops, or the mere presence of
two circles and labels. This is a reproduction task: a pass requires the same
global layout and the same circle-line intersection topology as `图3`.

Overall visual similarity to the locked top-right source panel is the primary
grading signal. Individual anchors and labels are necessary, but they are not
sufficient: a diagram with the right primitives but a visibly different global
composition, density, circle placement, or crossing web must stay below pass.

Do not require pixel-perfect equality, identical fonts, or identical line
weights. Do require that a careful human viewer can align the final PNG with
the target panel and recognize the same construction: circle sizes, baseline
height, axis placement, line neighborhoods, crossing order, and labeled point
neighborhoods must all be consistent.

Auxiliary target crops made by the executor may help show process, but they are
not deliverables and must not compensate for a visually wrong final PNG.

## 2. Task Contract

- Source sheet: `/tmp_workspace/clawbench/sources/panel_sheet.png`
- Target panel: `图3`, the top-right panel of the six-panel sheet
- Required script: `/tmp_workspace/results/reproduce_prompt4_geometry_thales.py`
- Required final image: `/tmp_workspace/results/prompt4_geometry_replicate.png`
- Required notes: `/tmp_workspace/results/prompt4_geometry_notes.md`

The output image must contain only the reconstructed figure 3, not the full
six-panel sheet and not a different panel.

## 3. Locked Ground Truth

The authoritative reference is the top-right 512 x 512 crop of the 1536 x 1024
source sheet: approximately `(x=1024, y=0, w=512, h=512)`. Use normalized crop
coordinates below only as tolerance anchors; visual topology is still the
primary standard.

Core target anchors:

- The horizontal baseline is near `y=0.59` of the crop and runs through
  `C3`, `O`, `O2`, and `B3`; it is not a low footer line and should not cut
  through the large circle.
- The vertical `y` axis is near `x=0.46`, passes through `O` and `F3`, and sits
  just right of the dense central crossing cluster.
- `C3` is a point on the baseline far left of both circles, outside the large
  circle. A result where `C3` lies on the large circle is materially wrong.
- The large left circle is centered around `O1` near `(0.33, 0.31)` with radius
  about `0.20` of crop width. Its bottom stays above the baseline; it does not
  sag below the x-axis.
- The smaller right circle is centered on the baseline at `O2` near
  `(0.68, 0.59)` with radius about `0.15` of crop width. Its rightmost point is
  `B3` on the baseline.
- The large-to-small radius ratio is roughly 1.2 to 1.5. A huge left circle
  paired with a much smaller right circle is not the target geometry.
- Approximate named-point neighborhoods are: `A3` upper-left on the large
  circle, `P3` upper-right on the large circle, `M3` just below/right of `P3`,
  `Q3` in the center-left crossing cluster, `N3` between `Q3` and the small
  circle, `F3` on the vertical axis below the baseline, `G3` lower-right near
  the small circle, and `R3` below `F3`.

Required topology:

- The `C3` rising secant / `l5` line starts at `C3`, passes through the lower
  left side of the construction, and continues up to the right through the
  `P3`/`l5` neighborhood.
- The `l6` family descends steeply from the upper-left / central area through
  the `Q3/F3/R3` and `N3/G3` neighborhoods toward the lower right.
- A near-vertical steep line family connects the `P3`, `M3`, `N3`, and `G3`
  neighborhoods; it is compact and close to the left side of the small circle,
  not a wide symmetric fan.
- The densest crossing web is compactly located around `Q3`, `N3`, and `F3`,
  between the right edge of the large circle and the left half of the small
  circle. Simplifying this into a few clean triangle/tangent lines is a
  structural mismatch.
- Dashed helper arcs/segments and solid lines must preserve their approximate
  neighborhoods and crossing order. Exact dash styling is less important than
  whether the same helper structure is present.

## 4. Checkpoint Rubric

Weights sum to 1.00. Award partial credit inside a line only when the visual
evidence supports it; do not infer correctness from notes.

- **0.06 - Required deliverables.** The script, final PNG, and notes exist at
  the exact required paths. The final PNG opens as an image and the script is a
  plausible runnable matplotlib/Python reproduction script.
- **0.09 - Correct target isolation.** The final PNG clearly reproduces only
  `图3` from the top-right panel. It must not be another panel, a full-sheet
  redraw, or a generic geometry diagram merely labeled `图3`.
- **0.25 - Overall visual similarity to the source panel.** Full credit
  requires the final PNG to resemble the locked `图3` crop as a whole:
  circle sizes, baseline height, axis placement, whitespace, line density,
  compactness of the crossing web, and label/caption distribution should align
  visually after uniform scaling. A polished two-circle construction with a
  different global look receives little credit here.
- **0.22 - Circle, baseline, and axis composition.** The two circles,
  horizontal baseline, and vertical axis match the locked ground truth: left
  circle above the baseline, right circle centered on the baseline, `C3` far
  left outside the large circle, `O/O2/B3` on the baseline, and correct
  relative circle scale and spacing.
- **0.23 - Major line topology.** The `C3` rising secant, `l5`, `l6`, steep
  `P3/M3/N3/G3` family, and main solid/dashed helper lines occupy the same
  neighborhoods and cross in the same order as the target.
- **0.12 - Intersection and label neighborhoods.** The compact `Q3/N3/F3`
  crossing web, `D3`, `G3`, `R3`, circle contact points, and labels are in
  visually consistent neighborhoods. Labels must be present and attached to
  the right structural points, but minor typography differences are acceptable.
- **0.03 - Evidence of compare-and-adjust.** Notes describe at least one
  concrete visual comparison against the original panel and a resulting
  correction. Generic claims of confidence or "pixel tracing" without a
  concrete correction receive no credit here.

Total: `0.06 + 0.09 + 0.25 + 0.22 + 0.23 + 0.12 + 0.03 = 1.00`.

## 5. Scoring Policy / Score Caps

Compute the rubric total, then apply all applicable caps by taking the minimum.
A run can pass only if the final score after caps is `>= 0.90`.

- **Cap at 0.30 - Missing final PNG.** The final image is absent, unreadable,
  or not at `/tmp_workspace/results/prompt4_geometry_replicate.png`.
- **Cap at 0.40 - Wrong target.** The output redraws the full sheet, selects
  the wrong panel, mirrors/rotates the panel, or makes a diagram that is not
  recognizably figure 3.
- **Cap at 0.50 - Missing core primitives.** Either circle is missing, the
  baseline is missing, or the line network is so sparse that the result is only
  a labeled sketch.
- **Cap at 0.60 - Circle/baseline collapse.** The baseline cuts through or
  below the large circle, the right circle is not centered on the baseline with
  `B3` at its right edge, or `C3` is placed on the large circle instead of far
  left outside it.
- **Cap at 0.65 - Major line topology wrong.** The `C3` rising secant, `l5`,
  `l6`, or the steep `P3/M3/N3/G3` family are in the wrong neighborhoods or
  cross in a visibly different order.
- **Cap at 0.70 - Known false-positive pattern.** Apply this cap to polished
  outputs that contain the required files, two circles, labels, and many lines
  but are visually/structurally different from the target, including any three
  or more of these symptoms: oversized left circle that reaches or crosses the
  baseline; `C3` on the left circle; right circle too far right or too small
  relative to the large circle; vertical axis dominating the center instead of
  sitting just right of the crossing web; `Q3/N3/F3/G3` cluster shifted,
  sparse, or converted into clean triangular/tangent lines; wide symmetric fan
  from `D3` rather than the compact source line family.
- **Cap at 0.89 - Visual mismatch despite correct primitives.** Apply when
  the output contains the two circles, axes, labels, and many required line
  families, but the final PNG does not visually align with the locked `图3`
  crop in global layout, circle/baseline proportions, line density, crossing
  compactness, or label neighborhoods. Primitive completeness alone cannot
  pass.
- **Cap at 0.75 - Intersection web simplified or misplaced.** The main
  circle/baseline layout is broadly present, but the dense crossing web around
  `Q3`, `N3`, `F3`, and nearby line contacts is not visually faithful.
- **Cap at 0.80 - Labels detached or mostly wrong.** Most required labels are
  absent, unreadable, rendered as literal markup, or attached to the wrong
  points, even if some geometry is plausible.
- **Cap at 0.84 - Required script or notes missing.** The final PNG is present
  and may be visually good, but either required non-image deliverable is
  missing. This prevents pass because the task explicitly requested all three
  artifacts.
- **Cap at 0.88 - Minor but material anchor drift.** All components are
  present, but one core anchor family is still visibly off: circle size/spacing,
  baseline height, `C3`/`B3` placement, or the compact `Q3/N3/F3` neighborhood.

Artifact polish, clean typography, high resolution, executor self-assessment,
or saved verification crops must not raise a capped score.

## 6. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** The final PNG is a faithful single-panel
  reproduction of `图3`, and no cap below 0.90 applies.
- **Continue (`0.60 - 0.89` after caps):** The correct panel and required files
  are present, but one or more fixable geometry issues remain. Typical continue
  cases include a broadly correct two-circle/baseline setup with a misplaced
  `Q3/N3/F3` web, wrong `l5/l6` neighborhoods, or labels needing relocation.
- **Fail (`< 0.60` after caps):** The output is the wrong target, lacks the
  final PNG, omits core primitives, or is a generic/structurally unrelated
  construction. If follow-up budget is exhausted, a capped continue-quality
  result should become terminal failure according to the run controller.

## 7. Hidden Reference Assets

- `references/eval_rule.md` (this file) - grading spec.
- `sources/panel_sheet.png` - public source sheet; the hidden rule locks the
  target to its top-right `图3` panel.

## 8. Dynamic Content Note

Offline static task. No web lookup or live data is needed. If an executor's
auxiliary crops disagree with the on-disk `panel_sheet.png`, judge against the
on-disk source image.
