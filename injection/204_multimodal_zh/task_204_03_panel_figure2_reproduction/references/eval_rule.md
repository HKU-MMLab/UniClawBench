# Hidden Evaluation Rule — task_204_03_panel_figure2_reproduction

## 1. Grading Philosophy

Judge the executor on whether it delivered a faithful Python-drawn
reproduction of the correct target panel, not on exact pixel identity and not
on generic similarity. The source image is static; the locked visual reference
is `图 2`, the top-middle panel of
`/tmp_workspace/clawbench/sources/panel_sheet.png`.

The primary scoring target is overall visual resemblance to that source panel.
Named points, labels, and analytic coordinates are only evidence in service of
the final PNG looking like the locked panel. A diagram with many correct labels
but different proportions, density, line neighborhoods, or crossing structure
cannot receive pass-level credit.

The supervisor should compare the final PNG directly against that panel after
allowing uniform scale changes, small typography differences, and minor stroke
weight differences. Do not allow output-path correctness, polished plotting,
or the executor's self-reported confidence to compensate for wrong panel
selection, wrong geometry, or wrong solid/dashed topology.

## 2. Task Contract

The executor must produce all three deliverables:

- `/tmp_workspace/results/reproduce_prompt3_complex_diagram.py` — runnable
  Python script used to generate the reproduction.
- `/tmp_workspace/results/prompt3_complex_diagram_replicate.png` — final image
  containing only the reproduced `图 2` panel.
- `/tmp_workspace/results/prompt3_complex_diagram_notes.md` — brief notes
  describing at least one concrete compare-and-adjust refinement.

The final PNG must be a reconstruction of only `图 2`. The whole six-panel
sheet, another panel, a collage of panels, or an unmodified crop/screenshot of
the source is not a valid final answer.

## 3. Locked Ground Truth

Normalize the main rectangular frame in `图 2` as
`A2=(0,0)`, `B2=(1,0)`, `D2=(0,1)`, `C2=(1,1)`, with `O` at the bottom
midpoint. Exact coordinates are not required, but the following visual facts
must be preserved after scaling:

- The target panel is the top-middle cell of the six-panel sheet, captioned
  `图 2` beneath the drawing.
- The main frame is a tall rectangle with top segment `D2-C2`, bottom segment
  `A2-B2`, vertical sides `D2-A2` and `C2-B2`, and an `x`-axis running through
  the bottom edge with an arrow to the right.
- A vertical `y`-axis passes through `O` and the central point stack, extends
  above the top segment, and has an upward arrow.
- Exterior curves `l3` and `l4` sit just outside the left and right vertical
  sides; they are near the side walls around `R2/S2` height and flare outward
  near their top and bottom ends.
- The lower central curve is a smooth U-shaped curve whose lowest point is
  `O`; it rises to the left and right toward the side-neighborhoods near
  `R2` and `S2`. It is not a parabola from `D2/C2` to `O`.
- Side points `R2` and `S2` lie on the left and right frame sides around the
  upper-middle of the rectangle; `U2` and `V2` lie lower on those same sides.
- `E2`, `G2`, and `T2` form a tight vertical stack on the center axis, with
  `E2` in the upper interior, `G2` near the mid-interior, and `T2` slightly
  below `G2`. `P2` is on the top segment near the center, and `Q2` is in the
  upper-right interior between the center axis and `C2/S2`.
- The solid and dashed line network is dense and asymmetric. It includes the
  upper solid fan through `D2`, the upper central point, and `C2`; solid
  diagonals from the upper corners and side points into the central crossing
  region; the lower U curve; and multiple dashed diagonals crossing near the
  `E2/G2/T2` stack. The dashed network is not three horizontal rows and not a
  symmetric analytic lattice.

A pass-level answer must look like this exact source panel to a careful human
viewer. Merely reusing labels such as `D2`, `C2`, `R2`, `S2`, `Q2`, and `T2`
on a different construction is insufficient.

## 4. Target Resolution Rules

The only in-scope source is
`/tmp_workspace/clawbench/sources/panel_sheet.png`. Resolve `图 2` as the
top-row, middle-column panel of the six-panel sheet. If the executor created
extra helper crops or diagnostic images, ignore them except as evidence of
iteration; grade the required final PNG as the submitted answer.

When judging visual similarity, compare against the source panel itself rather
than against the executor's notes or reconstructed coordinate system. Invented
analytic coordinates count only if they reproduce the same visible geometry.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within each line only for observable
evidence in the final artifacts.

- **0.06 — Required deliverables and generation path.** Full credit requires
  the exact final PNG, exact script, and exact notes path to exist; the PNG must
  open; the script must be plausibly runnable and tied to generating the PNG;
  and the notes must be non-empty. Missing final PNG zeroes this line.

- **0.09 — Correct panel selection and isolation.** The final PNG must depict
  only the top-middle `图 2` panel, not the whole sheet, not `图 1/3/4/5/6`,
  and not a mixture. Full credit also requires the composition to be cropped or
  framed as a single diagram with the `图 2` caption/labeling context preserved
  or intentionally omitted only outside the drawing area.

- **0.25 — Overall visual similarity to the source panel.** Full credit
  requires the final PNG to align with the source panel's global silhouette,
  aspect, whitespace, drawing density, line-length balance, label density, and
  relative placement of the frame, axes, curves, and central crossing network.
  This is a holistic visual-comparison score. A clean but visibly different
  reconstruction with the right labels should receive little credit here.

- **0.18 — Outer geometry, axes, and major curves.** Credit depends on the
  rectangular `D2-C2-A2-B2` frame, bottom `x`-axis, central `y`-axis, exterior
  `l3/l4` side curves, and the central U-shaped curve all matching the source
  proportions and placements. The U curve must bottom at `O` and rise toward
  the side-neighborhoods, not to the top corners.

- **0.17 — Landmark and point neighborhoods.** Named points must occupy the
  correct relative neighborhoods: `A2/B2/D2/C2` at frame corners, `O` at the
  bottom midpoint, `P2` near the top-center segment, `R2/S2` on opposite sides
  at similar upper-middle heights, `U2/V2` lower on the side walls,
  `E2/G2/T2` stacked on the center axis, and `Q2` in the upper-right interior.
  Penalize visible shifts greater than about one-tenth of the frame width or
  height on any major landmark, and penalize any swapped or invented
  neighborhoods.

- **0.20 — Solid/dashed topology and crossings.** The line network must
  preserve which helpers are solid vs dashed, which anchors they connect, and
  where the major crossings fall. Full credit requires the upper solid fan,
  side-to-center solid diagonals, lower-center crossing around `G2/T2`, slanted
  branch through `Q2` toward `S2`, and multi-direction dashed diagonals to be
  recognizable in the same neighborhoods as the source. A clean construction
  with the wrong connections earns little credit here even if labels are
  present.

- **0.03 — Labels, styling, and readability.** Labels for the visible anchors
  (`A2`, `B2`, `C2`, `D2`, `O`, `P2`, `Q2`, `R2`, `S2`, `T2`, `U2`, `V2`,
  `E2`, `G2`, `l3`, `l4`, `x`, `y`, and `图 2` or acceptable variants) should
  be present, legible, and near the correct marks. Accept subscript formatting
  variants such as `D_2` or `D2`, but not labels placed on the wrong points.

- **0.02 — Compare-and-adjust evidence.** Notes or observable workflow must
  identify the correct panel and describe at least one concrete refinement made
  after comparing a draft against the source, such as moving a point, changing a
  dashed/solid helper, reshaping `l3/l4`, or reshaping the U curve. Vague claims
  like "made it better" do not earn this line.

Total: `0.06 + 0.09 + 0.25 + 0.18 + 0.17 + 0.20 + 0.03 + 0.02 = 1.00`.

## 6. Scoring Policy / Score Caps

Apply the rubric first, then apply all relevant caps by taking the minimum.
Caps are intentionally strict so that visually wrong reconstructions cannot
pass through artifact completeness alone.

- **Cap at 0.20 — No usable answer.** No readable final image and no meaningful
  script or notes are present under `/tmp_workspace/results/`.
- **Cap at 0.30 — Missing final PNG.** The required
  `prompt3_complex_diagram_replicate.png` is absent or unreadable.
- **Cap at 0.35 — Wrong target.** The final image is another panel, the whole
  six-panel sheet, a multi-panel collage, or cannot be identified as `图 2`.
- **Cap at 0.45 — Generic or unrelated construction.** The result is a generic
  geometric sketch that reuses some labels but lacks the locked `图 2`
  silhouette and dense crossing structure.
- **Cap at 0.55 — Missing major visual anchors.** Any two of these are absent
  or badly distorted: rectangular frame, central `y`-axis through `O`, bottom
  `x`-axis/base, exterior `l3/l4` side curves, or the lower U curve.
- **Cap at 0.60 — Source crop instead of reproduction.** The final PNG is an
  unmodified crop/screenshot of the source panel, or the script merely copies
  the source image instead of drawing a reproduction.
- **Cap at 0.68 — Wrong internal topology despite correct outline.** The outer
  frame is recognizable, but the internal solid/dashed network is a different
  graph, such as horizontal dashed bands, a symmetric triangular lattice, or
  diagonals that do not anchor to the source neighborhoods around
  `D2/C2/R2/S2/U2/V2/E2/G2/T2`.
- **Cap at 0.89 — Visual mismatch despite correct primitives.** Most required
  points, labels, axes, and helper lines are present, but the final PNG does
  not visually resemble the locked `图 2` panel in overall proportions,
  drawing density, line-neighborhood placement, curve silhouettes, or crossing
  layout. Correct labels and a plausible coordinate model cannot pass without
  source-like visual alignment.
- **Cap at 0.75 — Material landmark or curve displacement.** The figure has the
  right panel and most primitives, but the U curve is visibly the wrong shape or
  attaches to the wrong endpoints, `E2/G2/T2` are not a tight center-axis
  stack, `Q2` is not in the upper-right interior, or multiple side points are
  shifted by more than about 10% of the frame dimension.
- **Cap at 0.80 — Solid/dashed encoding collapse.** Most helper lines are
  present but dashed-vs-solid styling is mostly wrong or indistinguishable,
  causing the visual construction to no longer match the source.
- **Cap at 0.84 — Pass-blocking omissions.** The geometry is otherwise close
  but one of the following remains: the script is missing or not plausibly
  runnable, the notes lack concrete compare-and-adjust evidence, more than
  three important labels are missing or placed on wrong points, or the caption
  and axis labels are absent in a way that makes the panel identity ambiguous.

A run can pass only if the capped score is at least 0.90 and no cap below 0.90
applies.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) — use only when the final PNG is recognizably
  the same `图 2` construction with the correct panel, major landmarks, U curve,
  center stack, and solid/dashed crossing topology. Small typography, stroke,
  or local coordinate imperfections are acceptable.
- **Continue** (`0.60 - 0.89` after caps) — use when the executor selected the
  correct panel and produced a partially faithful diagram, but one or more
  fixable issues remain in point placement, U-curve shape, line topology,
  dashed-vs-solid styling, labels, script path, or iteration notes. If the
  follow-up budget is exhausted, do not convert this to a pass.
- **Fail** (`< 0.60` after caps) — use when the output is missing, targets the
  wrong panel, redraws the whole sheet, is a generic sketch, is a direct source
  crop, or lacks enough locked ground-truth structure for a targeted repair.

## 8. Asset Visibility

These files have different visibility:

- `references/eval_rule.md` (this file) — supervisor-only grading spec; do not
  surface it to the executor or user simulator.
- `sources/panel_sheet.png` — public source sheet already exposed by the task;
  its top-middle panel is the visual ground truth for scoring.

## 9. Dynamic Content Note

Offline visual-reproduction task. No live API calls or external references are
needed. If helper crops or screenshots disagree with the original
`panel_sheet.png`, treat the original source sheet as authoritative.
