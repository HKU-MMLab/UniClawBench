# Hidden Evaluation Rule — Reading Corner Layout

## 1. Grading Philosophy

Judge whether the executor produced a source-grounded, physically plausible
reading-corner plan using only the items available in the task sources. A high
score requires the plan to satisfy the locked room constraints, select the
canonical reading setup, reject unsuitable items, and explain the placement
with visible evidence from the room and furniture images.

Do not reward polished interior-design prose by itself. File existence,
confident language, generic comfort advice, or invented dimensions must not
compensate for wrong furniture choices, ignored walkway constraints, or an
unsafe / impractical layout.

Chinese or English answers are both acceptable. Match by semantic item identity
when runtime source names differ from the anonymized fixture names below.

## 2. Task Contract

The user wants a no-new-purchases layout plan for the source folder
`/tmp_workspace/clawbench/sources/reading_corner/`. The executor must produce:

- `/tmp_workspace/results/reading_corner_plan.md`

The plan must cover all requested content:

- diagnose the current corner's main problems
- state which existing items should be used / kept in the reading corner
- state which existing items should not be used there
- describe approximate placement for chair, side table, lamp, and rug
- justify the plan with visible room, light, measurement, and item evidence

## 3. Locked Ground Truth

Structured expected answer lives at `references/ground_truth.json`. Treat that
file as authoritative if wording here and the JSON ever diverge.

Canonical source snapshot:

- `space_01.png` — corner overview: frosted / translucent black-framed window
  or glass-panel side on the left, warm wood floor, green plants, existing
  sage-green chair, and limited free floor area.
- `space_02.png` — measurement overlay: usable wall span about `175 cm`,
  window-side opening about `95 cm`, target walkway about `65 cm clear`, and
  explicit note that chair plus rug should stay off the aisle.
- `furn_04.png` — reference main reading chair: black high-back lounge /
  bentwood-style chair.
- `furn_07.png` — black round tray-style side table.
- `furn_02.png` — black two-head floor lamp.
- `furn_08.png` — cream round wool / shag rug; reference cozy rug choice.
- `furn_03.png` — rectangular jute rug; acceptable only with a grounded
  space / durability tradeoff and preserved walkway clearance.
- `furn_06.png` — black mesh office chair; unsuitable as reading-corner seat.
- `furn_05.png` — beige rolling metal cart; unsuitable as a core item because
  it is utilitarian and visually cluttering.
- `furn_01.png` — dark wooden dining chair; generally unsuitable for sustained
  reading because it is rigid and lacks lounge comfort.

Canonical problem diagnosis must include most of:

- usable floor area is limited
- the seating side already carries visual weight from the chair, plants, dark
  window framing, and nearby objects
- the `65 cm` walking path / aisle must remain clear
- the window / frosted-panel side is the best natural light source, so the
  seating orientation should relate to that side

Strict passing furniture set:

- primary chair: `furn_04.png`
- side surface: `furn_07.png`
- task light: `furn_02.png`
- rug: preferably `furn_08.png`; `furn_03.png` may still score if justified

Canonical layout:

- angle the lounge chair toward the window / frosted-panel side while keeping
  the aisle clear
- place the round side table on the chair's service / open side for a book or
  drink, not as an aisle obstruction
- put the floor lamp on the darker side behind or beside the chair so it works
  as reading light without blocking entry
- center the rug under / in front of the seating zone to define the nook, with
  its edge kept out of the required walkway

A plan that uses the visible in-room green chair instead of `furn_04.png` can
be coherent, but it does not satisfy the strict hidden reference combination
for a pass unless it also selects `furn_04.png` as the main reading chair.

## 4. Source-Selection and Target-Resolution Rules

The only in-scope source items are the files under
`/tmp_workspace/clawbench/sources/reading_corner/` at runtime. Do not give
credit for buying, shopping for, or relying on unsupported items such as new
shelves, ottomans, wall lights, bookcases, plants, stools, or replacement rugs.
Minor optional comments about relocating visible plants are acceptable only if
the core layout still uses the supplied furniture and does not depend on new
objects.

If an executor references public aliases such as `corner_overview.png`,
`wall_window_measurements.png`, `lounge_chair.png`, `round_side_table.png`,
`floor_lamp.png`, `wool_rug.png`, `jute_rug.png`, `office_chair.png`,
`metal_cart.png`, or `dining_chair.png`, match them to the semantic item above.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — Deliverable and requested structure.** `reading_corner_plan.md`
  exists under `/tmp_workspace/results/`, is readable Markdown or plain text,
  and contains sections or clearly labeled paragraphs covering problem
  diagnosis, selected items, rejected items, placement, and reasons. Award
  0.05 for the file and 0.05 for all required content categories.

- **0.20 — Room problem diagnosis.** Award 0.05 each for correctly identifying
  and grounding these four constraints: limited usable footprint; existing
  visual weight / clutter risk on the seating side; need to preserve the
  `65 cm` clear walkway; and left window / frosted-panel side as the best
  natural light source. Credit requires tying the claim to `space_01.png`,
  `space_02.png`, or equivalent visible / measurement evidence.

- **0.25 — Furniture selection against ground truth.** Award 0.06 for choosing
  `furn_04.png` as the primary reading chair and explaining why it beats the
  dining and office chairs; 0.06 for choosing `furn_07.png` as the side table;
  0.06 for choosing `furn_02.png` as the task lamp; 0.05 for choosing
  `furn_08.png` as the rug, or 0.03 for choosing `furn_03.png` with a
  grounded tradeoff; and 0.02 for explicitly keeping the selected set limited
  to existing source items.

- **0.25 — Layout feasibility and room constraints.** Award 0.07 for chair
  placement angled toward the window side while staying out of the aisle; 0.05
  for a side-table position that is reachable but does not pinch the walkway;
  0.05 for lamp placement behind / beside the chair on the darker side without
  blocking entry; 0.05 for rug placement that defines the nook while keeping
  chair plus rug off the aisle; and 0.03 for explicitly using the `175 cm`,
  `95 cm`, or `65 cm` measurements to justify feasibility.

- **0.10 — Rejection of unsuitable items.** Award 0.04 for explicitly rejecting
  `furn_06.png` / the office chair with a room- or comfort-grounded reason,
  0.04 for explicitly rejecting `furn_05.png` / the rolling cart with a
  clutter / footprint reason, and 0.02 for correctly rejecting or deprioritizing
  `furn_01.png` and any unchosen rug with a grounded reason.

- **0.10 — Evidence quality and no hallucination.** Award 0.04 for concrete
  references to both room images and at least two furniture item images; 0.03
  for avoiding unsupported source filenames, invented measurements, and
  fabricated item features; and 0.03 for preserving the no-new-purchases
  requirement throughout the recommendation.

Total: `0.10 + 0.20 + 0.25 + 0.25 + 0.10 + 0.10 = 1.00`.

## 6. Scoring Policy / Score Caps

Apply the rubric first, then apply all applicable caps by taking the minimum.
A capped score below `0.90` cannot pass, even if the uncapped rubric total is
high.

- **Cap at 0.30 — No usable deliverable.** `reading_corner_plan.md` is missing,
  empty, unreadable, or saved outside `/tmp_workspace/results/` with no
  equivalent visible result artifact.
- **Cap at 0.40 — Unsafe or physically impractical layout.** The plan places
  chair, rug, lamp, table, or cart in the required walking path; blocks entry
  or egress; creates a clear trip / stability hazard; or contradicts the note
  that chair plus rug should stay off the aisle.
- **Cap at 0.50 — Ignored room constraints.** The plan does not use the
  measurement note, does not mention the walkway, treats the compact
  `175 cm x 95 cm` corner as a generic spacious room, or misses the window /
  frosted-panel light relationship.
- **Cap at 0.55 — Wrong core furniture.** The plan chooses the office chair or
  dining chair as the main reading seat, uses the metal cart as the primary
  side surface, omits a side table or lamp entirely, or otherwise lacks a
  coherent chair + surface + task-light setup.
- **Cap at 0.70 — Missing one reference core item.** The plan is otherwise
  grounded but does not select one of the required core items
  (`furn_04.png`, `furn_07.png`, `furn_02.png`). This cap is stricter than the
  rubric because all three are needed for the hidden reference layout.
- **Cap at 0.80 — No explicit exclusions.** The plan never says which existing
  items should not be used in this corner, or rejects only vague categories
  rather than specific source items.
- **Cap at 0.84 — Defensible but non-reference main chair.** The plan uses the
  visible green chair from `space_01.png` as the main chair instead of
  selecting `furn_04.png`, while otherwise preserving the side table, lamp,
  rug, measurements, and aisle. This may be a reasonable public-facing answer
  but is below the strict hidden pass threshold.
- **Cap at 0.50 — Unsupported hallucinated core items or purchases.** The
  recommendation depends on buying or adding an item not shown in the sources,
  such as a new shelf, ottoman, wall sconce, bookcase, storage unit, or
  replacement chair / rug.
- **Cap at 0.70 — Minor unsupported hallucinations.** The core layout is based
  on source items, but the answer invents non-critical source filenames,
  dimensions, materials, or item features not visible in the files.
- **Cap at 0.65 — Generic answer.** The response could apply to almost any
  reading nook and lacks concrete visible details from the room and item
  images, even if it mentions the requested output file.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps) — stop. Requires no cap below `0.90`, a
  complete deliverable, the canonical core furniture selection, a walkway-safe
  layout, explicit exclusions, and source-grounded reasoning.
- **Continue** (`0.60 - 0.89` after caps) — request one targeted follow-up when
  the answer is mostly recoverable, such as adding explicit item exclusions,
  tightening the rug / walkway placement, citing the measurements, replacing a
  defensible but non-reference chair choice with `furn_04.png`, or removing
  minor hallucinated optional items.
- **Fail** (`< 0.60` after caps) — do not request more work. This includes
  missing deliverables, generic plans with no real source use, unsafe layouts,
  wrong core furniture, recommendations that require new purchases, or answers
  that ignore the measurement / walkway constraints.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — canonical problems, reference furniture
  combination, rug policy, avoid items, and layout anchors.

## 9. Dynamic Content Note

Offline task — no live API calls are expected. The corpus is static at runtime;
judge against the on-disk fixtures and `references/ground_truth.json`. If the
fixture filenames or public aliases drift, match by visible item identity and
flag the mismatch rather than inventing a new ground truth.
