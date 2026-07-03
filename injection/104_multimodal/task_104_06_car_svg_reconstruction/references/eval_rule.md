# Hidden Evaluation Rule — task_104_06_car_svg_reconstruction

## 1. Grading Philosophy

Grade the final rendered SVG against the public JPG and the hidden reference
render. This is a visual reconstruction task, not a vector-path clone task:
minor path simplifications, slight stroke-width differences, and small local
highlight differences are acceptable.

The strict requirement is recognizability as the same rendered car scene. A
valid SVG, polished notes, or a plausible green car is not enough for a pass if
the silhouette, viewpoint, wheel/body proportions, major components, or
black-outline style do not match the source. Use the hidden SVG only as a
reference asset for rendering and visual comparison; do not require identical
path commands or layer structure.

Overall rendered similarity to `reference_car_render.png` is the primary
scoring target. A component checklist is not enough: the final SVG must look
like the same car at a glance after rendering and normalizing to the reference
aspect ratio.

## 2. Task Contract

The executor must produce both requested files:

- `/tmp_workspace/results/car_recreated.svg`
- `/tmp_workspace/results/car_recreated_notes.md`

The SVG must be the primary deliverable and must render without fatal errors.
If preview PNGs or intermediate SVGs are present, grade only the final
`car_recreated.svg` at the requested path. Use the notes only for iteration
evidence and claimed comparison steps; visual score comes from the rendered SVG.

## 3. Evaluation Inputs and Target Resolution

Reference assets:

- Public input: `sources/car_input.jpg`
- Hidden reference render: `references/reference_car_render.png`
- Hidden source SVG: `references/reference_car.svg`

`car_input.jpg` and `reference_car_render.png` are both `1600 x 1066` images
showing the same white-background car scene. Treat the hidden render as
authoritative when JPG compression artifacts differ from the PNG render.

To compare an executor SVG, render it on a white or transparent-to-white
background and normalize to the reference aspect ratio when practical. Do not
give credit for a separately generated PNG if the requested SVG renders
differently.

## 4. Locked Ground Truth

The target is a cel-shaded/vector illustration of a bright green modified
two-door sports coupe, similar to an S13/180SX-style car, in a strong
front-right three-quarter view.

Locked composition facts:

- Canvas/reference aspect is landscape `1600 x 1066`, with a plain white
  background and no scenery.
- The non-white car/shadow region in the reference is approximately
  `1371 x 674` at offset `+124,+223` on the `1600 x 1066` render.
- The vehicle sits in the lower central area with substantial top whitespace,
  visible left/right margins, and no tight crop.
- The rear of the car is on the left; the nose/front bumper points to the
  lower right.
- The hood is a broad bright-green top plane occupying much of the right half.
- The side panel is visible along the left/center, so the view is not a flat
  side profile and not a head-on or top-down view.

Locked silhouette and proportion facts:

- Low, stretched, angular coupe stance with a long front hood, low roof,
  sloped windshield, hatch/rear quarter on the left, and a wide front bumper.
- The front wheel is large and lower/nearer the viewer; the rear wheel is
  smaller and farther left, partly tucked into the rear arch.
- The roof and windshield form grey trapezoid-like glass areas bounded by
  thick black outlines, with the roof/cabin located left of center.
- The front bumper, splitter/lip, and dark lower intakes occupy the lower
  right; the rear wing projects from the left rear.

Locked color/style/component facts:

- Dominant body color is bright green on upper surfaces, with medium/dark
  green side and lower panels.
- Thick black outlines and black shadow/underbody shapes are essential.
- Both visible wheels have black tires, dark grey multi-spoke rims, and
  yellow/orange brake-caliper cues.
- A red racing bucket seat/interior cue is visible through the side window.
- Required recognizable details include the rear wing, side window and
  windshield, side mirror, side skirt/dark lower strip, hood vents/slashes,
  front bumper openings, headlight/pop-up-light cues, and ground shadow.

A pass-level reconstruction must preserve these locked facts at a glance. A
result that reads as a different car drawing, a side-profile coupe, a generic
polygonal car, or a simplified icon is partial credit only.

## 5. Checkpoint Rubric

Weights sum to `1.00`.

- **0.05 - Output contract and renderability.** Full credit requires
  `car_recreated.svg` and `car_recreated_notes.md` at the exact requested
  paths, a valid SVG root, successful rendering without fatal errors, and a
  primarily vector-editable car. Award at most 0.05 here if the SVG exists but
  has rendering defects; award 0.00 if the main SVG is missing.

- **0.10 - Composition, scale, and viewpoint.** The render must use a plain
  white/near-white background, keep the car in the lower central area with
  similar negative space, preserve the wide landscape scene, and show the same
  front-right three-quarter orientation with rear-left to nose-lower-right
  diagonal flow. Substantial cropping, large shifts, wrong aspect, side-only
  view, top-down view, or reversed direction loses most of this line.

- **0.30 - Overall visual similarity to the hidden render.** Full credit
  requires the rendered SVG to resemble `reference_car_render.png` as a whole:
  silhouette, viewpoint, body massing, wheel/body proportions, cabin/hood/bumper
  relationships, outline thickness, color-blocking distribution, and negative
  space should match after normalization. A plausible green sports car with a
  different global look receives little credit here.

- **0.20 - Locked silhouette and body proportions.** The car must have the
  same low stretched coupe silhouette: long angular hood on the right, low
  roof/cabin left of center, sloped windshield, rear hatch/wing area on the
  left, broad front bumper, and integrated wheel arches/side skirt. A rounded
  side-profile body, a boxy hatchback, an over-simplified wedge, or a vehicle
  with the wrong roof/hood/window relationships cannot receive more than half
  credit on this line.

- **0.20 - Major components, colors, and style.** Score component presence and
  correct relative placement:
  bright/medium/dark green body planes, thick black outlines, two visible
  wheels with dark multi-spoke rims and yellow/orange calipers, grey
  windshield/side window/roof areas, red seat cue, rear wing with supports,
  front bumper/lip/intakes, hood vents/slashes, side skirt/dark lower strip,
  side mirror, and black ground shadow. Components that are present but in the
  wrong location or scale earn partial credit only. Missing wheels, missing
  cabin/glass, missing front bumper/hood, or missing rear wing are severe
  losses.

- **0.10 - Secondary detail fidelity and local relationships.** Award credit
  for close hood vent geometry, front light/bumper cut lines, cel-shaded green
  highlight/shadow layering, door and side contour lines, wheel occlusion by
  arches, front splitter shape, and the relation between glass, roof, hood,
  side panel, and seat. Random decorative black marks that do not correspond to
  the source do not count.

- **0.05 - Comparison and refinement evidence.** The notes must describe at
  least one concrete compare-and-adjust iteration against the JPG, including
  what was compared, what changed, and why the final SVG is closer. The final
  SVG should visibly reflect the claimed refinements. Generic statements such
  as "I compared and fixed it" without specific visual targets receive little
  or no credit.

Total: `0.05 + 0.10 + 0.30 + 0.20 + 0.20 + 0.10 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

Award the rubric line-by-line, then apply all relevant caps using `min`.
Caps are designed to prevent a formally valid SVG or confident notes from
passing when the visual reconstruction misses locked ground truth.

- **Cap at 0.25 - No requested main SVG.** `car_recreated.svg` is absent from
  `/tmp_workspace/results/`, unreadable, or not an SVG file.
- **Cap at 0.40 - Invalid or unusable SVG.** The SVG exists but has no valid
  `<svg>` root, cannot be rendered by normal SVG tooling, renders blank/empty,
  or has fatal XML/SVG errors.
- **Cap at 0.50 - Raster-only or non-editable submission.** The file is merely
  an embedded screenshot/raster image or otherwise not a meaningfully editable
  vector reconstruction, even if it visually resembles the source.
- **Cap at 0.35 - Wrong object/scene.** The render is not a car scene on a
  plain white background.
- **Cap at 0.45 - Wrong car family/color style.** The render is a car but not
  a bright green black-outlined modified sports coupe in the target visual
  style.
- **Cap at 0.55 - Wrong silhouette or viewpoint despite valid SVG.** The SVG
  is valid but the car is primarily side-profile, top-down, head-on, reversed,
  boxy/rounded in the wrong way, or otherwise not recognizable as the same
  low front-right three-quarter coupe silhouette.
- **Cap at 0.58 - Major component collapse despite valid SVG.** The SVG is
  valid but omits or collapses two or more core component groups: two clear
  wheels, cabin/glass, front hood/bumper/lip, rear wing, red seat/interior,
  or black outline/underbody style.
- **Cap at 0.89 - Component-complete but visually mismatched.** Apply when
  the SVG contains most locked components and colors, but the rendered result
  does not visually resemble `reference_car_render.png` in silhouette,
  viewpoint, body massing, wheel placement, cabin/hood/bumper relationships,
  outline style, or scene scale. A checklist-complete green car cannot pass
  without source-like rendered similarity.
- **Cap at 0.70 - Generic reconstruction.** The result is a plausible green
  modified car with several correct features, but the body contours, wheel
  placement, roof/window flow, front bumper, or hood/side relationships are
  visibly different from the source at a glance.
- **Cap at 0.78 - Major placement/proportion mismatch.** Most components are
  present, but important relative positions or scales are wrong, such as
  wheels not seated in arches, front wheel not dominant, hood too small,
  cabin too high/central, front bumper misplaced, or wing detached from the
  rear geometry.
- **Cap at 0.82 - Over-simplified or sparse detail.** The silhouette and
  component set are broadly right, but secondary details are too sparse,
  random, or icon-like to be a faithful reconstruction of the complex render.
- **Cap at 0.84 - Missing required refinement evidence.** Notes are missing,
  do not document a concrete compare-and-adjust step, or are materially
  inconsistent with the final SVG.
- **Cap at 0.70 - Source-grounding violation.** Trace evidence shows the
  executor used internet search, copied a found car graphic, or directly read
  hidden reference assets instead of reconstructing from the public JPG.
  Cap at 0.50 if the output is a direct copy or wrapper around the hidden SVG
  or another source asset.

A run passes only if the final score is `>= 0.90` after caps. Any applicable
cap below `0.90` prevents a pass.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** The final SVG is renderable, vector-editable,
  and recognizably the same green front-right three-quarter car scene, with
  the locked silhouette, major components, color/style, and refinement notes
  substantially satisfied.
- **Continue (`0.60 - 0.89` after caps):** The SVG is valid and in the correct
  family, but one or more fixable visual lines remain below pass quality.
  Use follow-up feedback to name the largest mismatch: silhouette/viewpoint,
  wheel placement, front bumper/hood, roof/glass/seat, wing, or missing
  refinement evidence.
- **Fail (`< 0.60` after caps):** The output is missing/invalid, the wrong
  object or car family, the wrong silhouette/viewpoint, or has collapsed major
  components. Do not rescue these runs with notes, valid file paths, or generic
  recognizability as a car.

If follow-up budget is exhausted while the score remains in the Continue band,
the task is still not passed; record the final non-passing status according to
the harness.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
the user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/reference_car.svg` - hidden source SVG for rendering/reference
  comparison only.
- `references/reference_car_render.png` - authoritative hidden PNG render.

No separate ground-truth JSON is used for this task; the locked facts in
Section 4 are the authoritative ground truth.

## 9. Dynamic Content Note

This is an offline static-image task. No live API calls, web searches, or
external references are needed. If the public JPG and hidden render ever drift,
prefer the hidden render for grading and flag the fixture mismatch separately.
