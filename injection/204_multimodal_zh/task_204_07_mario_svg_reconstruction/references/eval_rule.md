# Hidden Evaluation Rule — task_204_07_mario_svg_reconstruction

## 1. Grading Philosophy

Grade the final rendered SVG against the public JPG and the hidden reference
render. This is a visual reconstruction task, not a path-cloning task: minor
curve simplifications, small stroke-width differences, and simplified local
finger/shoe contours are acceptable.

The strict requirement is recognizability as the same rendered Mario jump
scene. A valid SVG, polished notes, or a plausible Mario-like cartoon is not
enough for a pass if the character identity, color blocking, pose geometry,
head/hat/face relationship, or limb/shoe layout is materially different from
the source. Use the hidden SVG only as a reference asset for rendering and
visual comparison; do not require identical path commands or layer structure.

Overall rendered similarity to `reference_mario_render.png` is the primary
scoring target. A broad Mario identity or a correct component checklist is not
enough if the final SVG looks like a different Mario drawing.

## 2. Task Contract

The public input is:

- `/tmp_workspace/clawbench/sources/mario_input.jpg`

The executor must produce both requested files:

- `/tmp_workspace/results/mario_recreated.svg`
- `/tmp_workspace/results/mario_recreated_notes.md`

The SVG must be the primary deliverable and must render without fatal errors.
If preview PNGs, intermediate SVGs, or comparison images are present, grade
only the final `mario_recreated.svg` at the requested path. Use the notes only
for evidence of comparison/refinement; visual score comes from the rendered
SVG.

## 3. Evaluation Inputs and Target Resolution

Reference assets:

- Public input: `sources/mario_input.jpg`
- Hidden reference render: `references/reference_mario_render.png`
- Hidden source SVG: `references/reference_mario.svg`

`mario_input.jpg` and `reference_mario_render.png` are both `1600 x 1599`
images showing the same white-background character scene. Treat the hidden PNG
render as authoritative when JPG compression differs from the PNG.

To compare an executor SVG, render it on a white or transparent-to-white
background and normalize to the reference aspect ratio when practical. Do not
give credit for a separately generated PNG if the requested SVG renders
differently.

## 4. Locked Ground Truth

The target is a bold, black-outlined vector illustration of Mario in a vertical
jumping pose, centered on a plain white background.

Locked composition facts:

- Canvas/reference aspect is nearly square, `1600 x 1599`, with no scenery,
  shadows, text, props, or colored background.
- The non-white character region in the reference is approximately
  `660 x 1293` at offset `+470,+124` on the `1600 x 1599` render.
- The character is centered horizontally, fills most of the frame vertically,
  and leaves generous white margins on all sides.
- The figure is upright and dynamic, not a horizontal running pose, flat side
  profile, chibi bust, icon, or tightly cropped portrait.

Locked pose and silhouette facts:

- One large white-gloved raised fist sits above and to the viewer's left of
  the head, connected by a red sleeve along the left side of the body.
- The head and red cap sit in the upper-right central area, below the raised
  fist; the fist does not replace or cover the face/hat structure.
- A second white-gloved fist is near the viewer's right side of the face/upper
  torso.
- Blue overalls form the dominant body and leg mass below the head, with one
  long lower leg dropping toward the bottom of the frame.
- A large foreshortened brown shoe projects toward the viewer at the lower
  right; the other brown shoe is lower/central and smaller.
- The pose reads as an upward jump with bent limbs and strong vertical flow,
  not as a walking or side-kicking stance with thin separated legs.

Locked character, color, and style facts:

- The character must read as Mario: red cap with a white circular/oval badge
  and `M` cue, red shirt/sleeves, blue overalls, yellow overall buttons, white
  gloves, brown shoes, peach face/ear, black mustache, and blue/white eyes.
- Thick black outlines define the outer silhouette and major internal shapes.
- Color blocking must stay in the same regions as the reference: red on cap,
  shirt, and raised sleeve; blue on overalls/legs; white only on gloves and
  cap badge; brown only on shoes/hair; peach on face/ear/nose.
- There is no red cape, scarf, trailing ribbon, extra background object, or
  large decorative shape absent from the target.

Locked head/face/hat facts:

- The red cap wraps around the top/right side of the head, with a front brim
  crossing above the eyes and a white badge near the top/front of the cap.
- The peach face sits under the brim with two tall eyes, a large central nose,
  black mustache below the nose, open smiling mouth, visible ear, and brown
  sideburn/hair cues.
- The nose, mustache, mouth, eyes, brim, and badge must remain in the same
  local relationship. A generic face, oversized round eyes, missing mustache,
  missing badge, or badge/face placed on the wrong part of the head is partial
  credit only.

A pass-level reconstruction must preserve these locked facts at a glance. A
generic Mario drawing, a side-view kick, a simplified mascot icon, or a valid
SVG with the wrong proportions remains below pass even if filenames and notes
are correct.

## 5. Checkpoint Rubric

Weights sum to `1.00`. Award partial credit within a line only for visible
evidence in the final rendered SVG and required files.

- **0.05 - Output contract and renderability.** Full credit requires
  `mario_recreated.svg` and `mario_recreated_notes.md` at the exact requested
  paths, a valid SVG root, successful rendering without fatal errors, and a
  primarily vector-editable reconstruction. Award at most 0.05 here if the SVG
  exists but has rendering defects; award 0.00 if the main SVG is missing.

- **0.10 - Composition, scale, and canvas.** The render must use a plain
  white/near-white background, keep the figure centered with similar negative
  space, preserve the near-square scene, and make the character tall in the
  frame rather than tiny, shifted, stretched, or tightly cropped. Substantial
  aspect drift, background additions, or a figure that occupies the wrong
  part of the canvas loses most of this line.

- **0.30 - Overall visual similarity to the hidden render.** Full credit
  requires the rendered SVG to resemble `reference_mario_render.png` as a
  whole: upright jump silhouette, head/fist/body/shoe placement, relative
  scale of the head, gloves, overalls, legs, and shoes, black-outline weight,
  color-blocking distribution, and negative space should match after
  normalization. A plausible Mario drawing with a different pose or body layout
  receives little credit here.

- **0.20 - Locked pose, silhouette, and body proportions.** The rendered
  character must preserve the same vertical jump: raised left glove above the
  head, head/cap below-right of that glove, second fist at the right upper
  torso, dominant blue overalls, long dropping leg, and large lower-right
  forward shoe. Walking poses, flat side-kicks, thin/lanky separated legs,
  tiny torso, huge misplaced head, or raised glove geometry that replaces the
  head earn little credit on this line.

- **0.15 - Major components, color blocking, and black-outline style.** Score
  the required Mario components and their placement: red cap/badge and red
  shirt/sleeves, blue overalls/legs, yellow buttons, white raised glove and
  white side glove, brown shoes, peach face/ear/nose, black mustache, and
  thick black outlines. Components present in the wrong location, wrong color,
  or wrong scale earn partial credit only. Missing red/blue/brown/white color
  families, missing gloves, missing shoes, missing overalls, or weak/no black
  outline style are severe losses.

- **0.10 - Head, face, and hat local fidelity.** Award credit for the cap dome
  and brim wrapping the head, white `M` badge cue, eyes under the brim, large
  nose centered over the mustache, open mouth below, ear/sideburn placement,
  and correct face-to-hat proportions. A generic smiley face, wrong badge
  shape/location, missing mustache, oversized eyes that dominate the face, or
  a head/hat relationship unlike the reference cannot receive more than half
  credit on this line.

- **0.07 - Limb, glove, shoe, and local detail fidelity.** Award credit for
  the raised glove's large rounded fist with finger arcs, the second fist near
  the face/upper torso, chunky connected limbs, the lower-right foreshortened
  shoe with sole/crease cues, and the smaller trailing shoe. Random decorative
  lines, detached limbs, horizontal shoe bars, or shoe/glove shapes that do not
  match the source projection earn little credit.

- **0.03 - Comparison and refinement evidence.** The notes must describe at
  least one concrete compare-and-adjust iteration against the JPG, including
  what was compared, what changed, and why the final SVG is closer. The final
  SVG should visibly reflect the claimed refinements. Generic statements such
  as "I compared and fixed it" without specific visual targets receive little
  or no credit.

Total: `0.05 + 0.10 + 0.30 + 0.20 + 0.15 + 0.10 + 0.07 + 0.03 = 1.00`.

## 6. Scoring Policy / Score Caps

Award the rubric line-by-line, then apply all relevant caps using `min`.
Caps are designed to prevent a formally valid SVG, nominal Mario identity, or
confident notes from passing when the visual reconstruction misses locked
ground truth. Caps never raise a score.

- **Cap at 0.25 - No requested main SVG.** `mario_recreated.svg` is absent
  from `/tmp_workspace/results/`, unreadable, or not an SVG file.
- **Cap at 0.40 - Invalid or unusable SVG.** The SVG exists but has no valid
  `<svg>` root, cannot be rendered by normal SVG tooling, renders blank/empty,
  or has fatal XML/SVG errors.
- **Cap at 0.50 - Raster-only or non-editable submission.** The file is merely
  an embedded screenshot/raster image or otherwise not a meaningfully editable
  vector reconstruction, even if it visually resembles the source.
- **Cap at 0.35 - Wrong object/scene.** The render is not a white-background
  cartoon character scene.
- **Cap at 0.45 - Wrong character despite nominal SVG.** The render is a valid
  SVG but does not read as Mario, or lacks core Mario identity cues such as red
  cap, blue overalls, white gloves, brown shoes, black mustache, and cap badge.
- **Cap at 0.55 - Wrong color blocking despite nominal SVG.** The character is
  Mario-like but major color families are missing, swapped, or placed in the
  wrong regions, such as blue shirt/red pants, non-white gloves, non-brown
  shoes, or a large red cape/scarf/ribbon absent from the source.
- **Cap at 0.58 - Wrong pose geometry despite nominal SVG.** The SVG is valid
  and Mario-like but the silhouette is not the source jump: walking stance,
  side-running pose, flat horizontal kick, missing raised fist, raised fist
  covering/replacing the head, missing lower-right foreshortened shoe, or
  body/legs arranged in a materially different geometry.
- **Cap at 0.60 - Major component collapse.** Two or more core component
  groups are omitted, tiny, detached, or merged beyond recognition: cap/badge,
  face/nose/mustache/eyes, raised glove, side glove, blue overalls/body,
  lower-right shoe, trailing leg/shoe, or thick black outline structure.
- **Cap at 0.89 - Mario-like but visually mismatched.** Apply when the SVG has
  broad Mario identity and most locked components, but the rendered result does
  not visually resemble `reference_mario_render.png` in overall pose,
  silhouette, head/fist/body/shoe placement, body proportions, color-blocking
  distribution, or outline hierarchy. A component-complete Mario drawing cannot
  pass without source-like rendered similarity.
- **Cap at 0.70 - Generic Mario-like reconstruction.** The result has broad
  Mario identity and the right palette, but reads as a different Mario drawing
  because the head/body proportions, limb layout, shoe placement, or silhouette
  differ at a glance from the reference.
- **Cap at 0.78 - Major placement/proportion mismatch.** Most components are
  present, but important relative positions or scales are wrong, such as the
  head too large/small for the body, body too squat or too thin, raised glove
  too low/small, forward shoe too horizontal/oversized/undersized, lower leg
  not dropping vertically, or face/hat shifted away from the reference layout.
- **Cap at 0.82 - Local geometry/detail mismatch.** The overall figure is
  close, but pass-critical local relationships remain visibly wrong: cap brim
  and badge relation, eyes/nose/mustache/mouth placement, glove finger arcs,
  shoe sole/crease projection, yellow button/strap placement, or outline
  thickness/shape hierarchy.
- **Cap at 0.84 - Missing required refinement evidence.** Notes are missing,
  do not document a concrete compare-and-adjust step, or are materially
  inconsistent with the final SVG.
- **Cap at 0.70 - Source-grounding violation.** Trace evidence shows the
  executor used internet search, copied a found Mario graphic, or directly
  read hidden reference assets instead of reconstructing from the public JPG.
  Cap at 0.50 if the output is a direct copy or wrapper around the hidden SVG
  or another source asset.

A run passes only if the final score is `>= 0.90` after caps. Any applicable
cap below `0.90` prevents a pass.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) - executor should stop. This requires a
  renderable, vector-editable SVG that is recognizably the same Mario jump
  scene with the locked composition, pose, color/style, head/face/hat geometry,
  limb/shoe layout, and refinement notes substantially satisfied.
- **Continue** (`0.60 - 0.89` after caps) - one or more repairable visual
  errors remain. Use follow-up feedback to name the largest mismatch: pose
  geometry, figure scale, head/hat/face relationship, raised glove, side glove,
  overalls/leg mass, foreground shoe, color blocking, or missing refinement
  evidence.
- **Fail** (`< 0.60` after caps) - no further follow-up should be requested.
  This includes missing/invalid SVGs, raster-only submissions, wrong
  character/scene, wrong color family, wrong jump geometry, or collapsed major
  components. Do not rescue these runs with notes, valid filenames, or generic
  recognizability as Mario.

If follow-up budget is exhausted while the score remains in the Continue band,
the task is still not passed; record the final non-passing status according to
the harness.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
the user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/reference_mario.svg` - hidden source SVG for rendering/reference
  comparison only.
- `references/reference_mario_render.png` - authoritative hidden PNG render.

No separate ground-truth JSON is used for this task; the locked facts in
Section 4 are the authoritative ground truth.

## 9. Dynamic Content Note

This is an offline static-image task. No live API calls, web searches, or
external references are needed. If the public JPG and hidden render ever drift,
prefer the hidden render for grading and flag the fixture mismatch separately.
