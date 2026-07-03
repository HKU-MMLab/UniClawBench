# Hidden Evaluation Rule — task_104_05_panel_figure5_reproduction

## 1. Grading Philosophy

Judge the executor on the final, user-visible deliverables, with the final PNG
as the primary artifact. The task is not pixel-perfect tracing, but it is a
geometry-reproduction task: a correct answer must reproduce the specific
figure-5 construction from the source sheet, not merely draw a plausible circle
with many chords.

Use the source image itself as the visual authority. Notes, script comments,
or self-reported confidence cannot compensate for a visibly wrong construction.
Give credit for small local drift in line endpoints, label offsets, and stroke
weight only when the locked geometric relationships below remain recognizable.
Overall visual similarity to the bottom-middle `图 5` crop is the primary
grading signal: a component-complete circle diagram still cannot pass if its
global composition, lattice density, chord placement, or dashed-helper layout
looks like a different construction.

## 2. Task Contract

The public source sheet is:

- `/tmp_workspace/clawbench/sources/panel_sheet.png`

The executor must identify `图 5` as the bottom-middle panel in the six-panel
sheet and produce only that figure. Required outputs are:

- `/tmp_workspace/results/reproduce_prompt5_geometry_circle_chord_tangent.py`
- `/tmp_workspace/results/prompt5_geometry_replicate.png`
- `/tmp_workspace/results/prompt5_geometry_notes.md`

The script must be a runnable Python/matplotlib reproduction script. The final
image must be a recreated drawing, not the full source sheet and not a pasted
crop of the source panel.

## 3. Source Selection and Locked Ground Truth

The source sheet is static at runtime and is `1536 x 1024` pixels. The target is
the lower-middle cell, approximately `x = 512..1024`, `y = 512..1024`. When in
doubt, judge against the visible `图 5` panel in that cell and ignore neighboring
panel fragments.

Locked visual facts for `图 5`:

- One large thin black circle, centered near the intersection labeled `G5`,
  occupies most of the panel.
- The horizontal diameter runs through `A5`, `E5`, `G5`, `F5`, and `B5`, with
  axis arrows extending left and right outside the circle and the `x` label on
  the right.
- The vertical axis runs through `C5`, `G5`, `H5`, and `D5`, with the `y` label
  and arrow above `C5`.
- Circumference points and labels are placed as follows: `C5` top, `D5` bottom,
  `A5` left, `B5` right, `P5` upper-left, `Q5` upper-right, `M5` lower-left,
  and `N5` lower-right.
- Interior labels are not arbitrary: `E5` and `F5` are on the horizontal
  centerline near the left and right side chords, `G5` is at the axis
  intersection, and `H5` sits below `G5` on or very near the vertical axis.
- Required solid structure includes the circle, the two axes, top chord
  `P5-Q5`, bottom chord `M5-N5`, side chords `P5-M5` and `Q5-N5`, cap slants
  `C5-P5`, `C5-Q5`, `D5-M5`, and `D5-N5`, long crossed diagonals `P5-N5` and
  `Q5-M5` meeting around `G5`, and the `C5`-to-lower-side slants that create
  the compact crossings near `E5/F5/G5`.
- Required dashed structure is limited and local: a shallow dashed helper arc
  near the top between the upper side points, a shallow dashed helper arc near
  the bottom between the lower side points, and diagonal/side helper segments
  running through the `E5/F5` neighborhoods toward `D5`. Dashed helpers should
  not become a dense all-to-all star lattice.
- The figure uses black solid and dashed strokes on a white background, with a
  centered caption `图 5` below the drawing.

Common non-ground-truth interpretations are explicitly wrong: a regular
45-degree octagon model, an octagon perimeter around `A5/P5/C5/Q5/B5/N5/D5/M5`,
a generic box-plus-star diagram, or a simplified triangle/hexagram that lacks
the side chords and compact center-neighborhood crossings.

## 4. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within a line only for visible,
user-facing evidence in the final output and required files.

- **0.06 — Required deliverables and reproducibility.** Full credit requires
  all three exact paths to exist, the PNG to be readable, the script to be
  runnable without manual edits, and the notes file to be non-empty. Award at
  most 0.05 here if the final PNG exists but either the exact script or notes
  file is missing. Award 0.00 if the final PNG is missing or unreadable.

- **0.08 — Correct target selection and output scope.** Full credit requires a
  single-panel reproduction of bottom-middle `图 5`, not the full six-panel
  sheet and not any other numbered figure. Minor whitespace/caption cropping is
  acceptable. Zero this line for a wrong panel, full-sheet redraw, collage, or
  output dominated by source-sheet context.

- **0.25 — Overall visual similarity to the source panel.** Full credit
  requires the final PNG to resemble the `图 5` crop as a whole: circle scale
  and centering, axis/caption placement, chord density, solid/dashed balance,
  central crossing compactness, label distribution, and whitespace should
  match after uniform scaling. A clean circle-plus-chords diagram with a
  different visual layout receives little credit here.

- **0.18 — Global circle, axes, and scale.** Full credit requires one circular
  outer boundary, a centered vertical and horizontal diameter crossing at `G5`,
  `A5/B5/C5/D5` at the correct compass positions, and axis arrow/label
  placement matching the source. Deduct for an ellipse, off-center axes,
  displaced `G5`, missing diameter endpoints, wrong aspect ratio, or excessive
  whitespace that changes the panel composition.

- **0.22 — Main solid lattice fidelity.** Full credit requires the named solid
  structure in §3 to be present with the correct endpoints, crossings, and
  solid-vs-dashed classification. Score this line by visual completeness:
  top/bottom/side chords, cap slants, crossed diagonals through `G5`, compact
  `C5`-driven crossings near `E5/F5`, and absence of dominant extra scaffold
  lines must all be substantially correct. A result that preserves the circle
  and axes but changes the crossing order, omits side chords, swaps solid and
  dashed roles, or replaces the construction with a regular polygon/star earns
  little or no credit on this line.

- **0.12 — Dashed helper fidelity.** Full credit requires the top and bottom
  shallow dashed helper arcs and the diagonal/side dashed helpers around
  `E5/F5` and the lower interior to match the source in location, extent, and
  style. Award at most 0.07 if dashed lines exist but are generic long
  diagonals or decorative arcs unrelated to the source. Award 0.00 if dashed
  helpers are omitted or are mostly solid.

- **0.06 — Points, labels, and local neighborhoods.** Full credit requires the
  visible labels `A5`, `B5`, `C5`, `D5`, `P5`, `Q5`, `M5`, `N5`, `E5`, `F5`,
  `G5`, `H5`, `x`, `y`, and `图 5` to be present, legible, and placed in the
  same neighborhoods as the source. Deduct for missing labels, labels attached
  to the wrong point, `E5/F5` moved off the horizontal centerline, `G5` not at
  the axis crossing, or `H5` absent/misplaced.

- **0.03 — Compare-and-adjust evidence.** Full credit requires the notes to
  state that the executor compared against the source figure and made at least
  one concrete geometry correction, and the script/notes should not assert a
  false ground-truth model such as "regular octagon" when the final image is
  judged. Generic "saved outputs" notes receive at most 0.01.

Total: `0.06 + 0.08 + 0.25 + 0.18 + 0.22 + 0.12 + 0.06 + 0.03 = 1.00`.

## 5. Scoring Policy / Score Caps

Compute the rubric score first, then apply all applicable caps by taking the
minimum. Caps never raise a score. A score at or above the pass threshold must
reflect a genuinely source-grounded figure-5 reproduction after caps.

- **Cap at 0.30 — No usable final image.** The final
  `/tmp_workspace/results/prompt5_geometry_replicate.png` is missing,
  unreadable, blank, or not an image.
- **Cap at 0.35 — No meaningful geometry.** The output is mostly text,
  screenshots, empty axes, or disconnected marks rather than a figure-5
  construction.
- **Cap at 0.40 — Wrong panel or full-sheet redraw.** The output reproduces a
  different numbered panel, redraws the entire six-panel sheet, or leaves the
  target panel embedded in a multi-panel/collage image.
- **Cap at 0.50 — Crop or trace instead of reproduction.** The PNG is visibly
  a pasted/cropped source raster, or the script primarily copies/crops the
  source image instead of drawing a matplotlib reconstruction.
- **Cap at 0.55 — Circle/axis failure.** The main circle is missing, badly
  non-circular, or the horizontal/vertical axes do not cross at the circle
  center.
- **Cap at 0.58 — Regular-octagon false positive.** The answer models the
  panel as a regular 45-degree octagon, draws an octagon perimeter
  `A5-P5-C5-Q5-B5-N5-D5-M5-A5`, or uses a boxy octagon/rectangle scaffold with
  many all-to-all dashed diagonals. This cap applies even if all labels and
  required filenames are present.
- **Cap at 0.89 — Visual mismatch despite correct components.** Apply when
  the output contains the circle, axes, labels, and many required chords or
  helpers, but the final PNG does not visually resemble the locked `图 5`
  panel in circle scale, lattice density, chord placement, dashed-helper
  neighborhoods, central crossing compactness, or label distribution.
  Component completeness alone cannot pass.
- **Cap at 0.70 — Generic circle-with-chords.** The result has a circle,
  axes, and labels but lacks the specific side chords, top/bottom chords, and
  compact center-crossing lattice from §3.
- **Cap at 0.74 — Simplified star/triangle false positive.** The result keeps
  the circle and axes but replaces the source lattice with a few long crossed
  diagonals, a hexagram/triangle pattern, or top/bottom arcs while omitting or
  misplacing the side vertical chords and `E5/F5/G5/H5` neighborhoods.
- **Cap at 0.78 — Material solid-lattice mismatch.** Fewer than roughly
  three-quarters of the required solid segments in §3 are present with the
  correct endpoints and line style, or the main crossing order around `G5` is
  visibly different.
- **Cap at 0.80 — Dashed-helper collapse.** The main solid lattice is mostly
  recognizable, but the top/bottom dashed arcs and side/lower dashed helpers
  are omitted, mostly solid, or replaced by unrelated full-length star lines.
- **Cap at 0.82 — Interior point/label neighborhoods wrong.** `E5` and `F5`
  are not on the horizontal centerline, `G5` is not at the axis intersection,
  `H5` is absent or placed in the wrong region, or more than four named labels
  are missing/illegible.
- **Cap at 0.84 — No real refinement evidence.** The final image is otherwise
  close, but the notes do not document a concrete compare-and-adjust iteration,
  or the script cannot regenerate the final PNG without manual repair.

## 6. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) — executor should stop. This requires the
  correct single target panel, exact deliverable paths, a close circle/axis
  composition, the locked solid lattice, source-matching dashed helpers, and
  correct point/label neighborhoods. No cap below 0.90 may apply.
- **Continue** (`0.60 - 0.89` after caps) — one or more repairable visual
  errors remain. Typical continue cases include the correct panel with good
  circle/axes but flawed dashed helpers, label neighborhoods, or a simplified
  lattice that can be corrected with another comparison pass.
- **Fail** (`< 0.60` after caps) — no further follow-up should be requested.
  This includes missing/blank images, wrong-panel or full-sheet outputs,
  pasted crops, regular-octagon false positives, and generic diagrams whose
  main construction is not the source figure.

## 7. Hidden Reference Assets

Supervisor-only assets:

- `references/eval_rule.md` (this file) — grading spec.

The public source image remains the visual ground truth for this task; do not
surface hidden grading language to the executor or user simulator.

## 8. Dynamic Content Note

Offline task — no live API calls are expected. The source sheet is static. If
an executor claims to have used a different source image, different panel
numbering, or external geometry facts, ignore those claims and judge against
the `图 5` panel in `/tmp_workspace/clawbench/sources/panel_sheet.png`.
