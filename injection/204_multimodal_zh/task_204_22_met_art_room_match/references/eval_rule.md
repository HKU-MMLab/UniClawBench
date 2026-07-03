# Hidden Evaluation Rule — The Met Artwork Room Match

## 1. Grading Philosophy

Grade the executor on whether it delivered the requested Met-page research and
made the hidden canonical room recommendation. Polished prose, self-reported
confidence, or plausible interior-design advice must not compensate for wrong
artwork facts, a wrong final recommendation, or room-fit reasoning that is not
supported by the supplied room JSON and the locked artwork evidence.

The expected recommendation is objective for this benchmark: Friedrich's
`Two Men Contemplating the Moon` is the only best final choice. Monet or van
Gogh as the final choice is not an acceptable alternative.

## 2. Task Contract

The public task asks the executor to open these three The Met collection pages:

- Claude Monet - `https://www.metmuseum.org/art/collection/search/437133`
- Vincent van Gogh - `https://www.metmuseum.org/art/collection/search/436535`
- Caspar David Friedrich - `https://www.metmuseum.org/art/collection/search/438417`

It must read `/tmp_workspace/clawbench/sources/my_room_style.json`, save
artwork screenshots under `/tmp_workspace/results/artwork_screenshots/`, and
produce exactly these primary result files:

- `/tmp_workspace/results/artworks_metadata.csv`
- `/tmp_workspace/results/visual_analysis.md`
- `/tmp_workspace/results/best_choice_for_my_room.md`

`artworks_metadata.csv` must include at least:

- `artwork_url`
- `title`
- `artist`
- `object_date`
- `medium`
- `dimensions`

## 3. Locked Ground Truth

Judge against the hidden reference files captured on `2026-04-23`:

- `references/ground_truth.csv`
- `references/ground_truth.json`
- `references/reference_best_choice.md`

Canonical metadata:

| object_id | title | artist | object_date | medium | dimensions |
| --- | --- | --- | --- | --- | --- |
| 437133 | Garden at Sainte-Adresse | Claude Monet | 1867 | Oil on canvas | 38 5/8 x 51 1/8 in. (98.1 x 129.9 cm) |
| 436535 | Wheat Field with Cypresses | Vincent van Gogh | 1889 | Oil on canvas | 28 13/16 × 36 3/4 in. (73.2 × 93.4 cm) |
| 438417 | Two Men Contemplating the Moon | Caspar David Friedrich | ca. 1825–30 | Oil on canvas | 13 3/4 x 17 1/4 in. (34.9 x 43.8 cm) |

Accept harmless typography normalization in metadata only when the underlying
value is identical, such as `x` versus `×`, extra whitespace, or an artist field
that starts with the correct artist name and adds page-sourced biographical
text. Do not accept changed measurements, changed dates, substituted titles, or
non-Met URLs.

Canonical visual cues:

- Monet: bright sunlit seaside garden; high-key color; terrace, sea, and sky
  arranged in broad horizontal bands; airy/noon-like mood.
- van Gogh: saturated greens, blues, and yellows; rich impasto and active
  directional brushwork; wind-swept, energetic, high-motion landscape.
- Friedrich: muted dusk palette with deep blues, browns, and moonlit
  highlights; two rear-view figures; quiet, contemplative, low-noise mood.

Locked room profile:

- Room: bedroom reading nook.
- Wall: `140 cm` wide by `90 cm` high, desaturated blue-gray.
- Materials: oak wood, cream linen, charcoal metal.
- Light: soft north-facing daylight.
- Preferred mood: quiet, contemplative, low-contrast, dusk-like rather than
  noon-bright.
- Avoid: very saturated yellows, restless high-energy brushwork, anything that
  makes the corner feel louder.
- Placement: one medium horizontal print above a low bookshelf.

Locked best choice:

- Sole final recommendation: `Two Men Contemplating the Moon`.
- Artist: `Caspar David Friedrich`.
- Object id: `438417`.

The placement note does not justify rejecting Friedrich. The locked dimensions
are horizontal (`13 3/4 x 17 1/4 in.`), and the hidden reference treats
Friedrich as suitable for a medium horizontal print above the bookshelf. A
recommendation that selects Monet because it is "more horizontal" or claims
Friedrich is not a horizontal fit is unsupported.

## 4. Checkpoint Rubric

Weights sum to `1.00`. Award partial credit only for evidence present in the
executor's saved outputs or visible trace. Apply score caps in section 5 after
adding checkpoint points.

- **0.10 - Required artifacts and screenshot evidence.** Award 0.04 if all
  three primary files exist in `/tmp_workspace/results/`; 0.03 if
  `artwork_screenshots/` contains at least one screenshot artifact for each of
  the three artworks; and 0.03 if the screenshots visibly document the relevant
  Met page with the main artwork image plus an identifiable title/metadata area
  for each artwork. A screenshot may be supplemented by another screenshot for
  the same artwork if one viewport cannot show both the image and metadata.

- **0.30 - Metadata accuracy.** Award 0.06 if the CSV parses, has the six
  required columns, and has one row for each of the three locked Met pages.
  Award 0.09 for correct URL/title/artist slots across all rows
  (`3 works x 3 slots`), 0.06 for all three `object_date` slots, and 0.09 for
  all `medium` and `dimensions` slots (`3 works x 2 slots`). Each slot is all
  or nothing after the normalization in section 3.

- **0.20 - Artwork-specific visual analysis.** Award 0.03 if all three locked
  artworks are separately analyzed by title or artist and no substitute artwork
  is introduced; 0.06 if each artwork covers all four requested categories
  (palette/cool-warm relationship, composition, brushwork or surface texture,
  and mood); 0.09 for using the canonical visual cues in section 3 across the
  three works; and 0.02 for clearly differentiating the works rather than
  recycling the same adjectives.

- **0.30 - Final recommendation and room-fit mapping.** Award 0.10 only if
  `best_choice_for_my_room.md` names Friedrich's `Two Men Contemplating the
  Moon` as the sole best final choice. Award 0.08 for citing at least five
  concrete room JSON details from section 3. Award 0.08 for mapping Friedrich's
  muted dusk palette, contemplative subject/mood, low visual noise, and
  horizontal suitability to those room details. Award 0.04 for reasoning that
  stays supported by the locked evidence and does not contradict the room JSON
  or the canonical metadata.

- **0.10 - Correct rejection of the other two artworks.** Award 0.05 for
  explaining that Monet is weaker because its sunlit, bright, airy/noon-like
  effect conflicts with the low-contrast dusk-like reading nook. Award 0.05 for
  explaining that van Gogh is weaker because its saturated yellows, impasto,
  restless energy, and visual loudness conflict with the room's avoid list.

## 5. Scoring Policy / Score Caps

Compute the raw checkpoint score, then apply every relevant cap by taking the
minimum. These caps target benchmark-breaking errors and are stricter than the
rubric totals.

- **Cap at 0.30 - No meaningful deliverables.** Fewer than two of the three
  primary result files exist, or the result directory is essentially empty.
- **Cap at 0.40 - No credible Met-page evidence.** The output has no screenshot
  artifacts for the three Met pages and no traceable page-sourced metadata.
- **Cap at 0.50 - Missing metadata deliverable.** `artworks_metadata.csv` is
  absent, unparseable, missing the required columns, or missing rows for two or
  more locked artworks.
- **Cap at 0.75 - Incomplete metadata coverage.** The CSV is present but omits
  one locked artwork row, leaves required metadata fields blank, or has more
  than three incorrect required metadata slots.
- **Cap at 0.60 - Wrong final artwork.** The final recommendation is Monet, van
  Gogh, a tie, no single artwork, or any work other than Friedrich's
  `Two Men Contemplating the Moon`. This cap applies even if the prose is
  plausible and the other artifacts are strong.
- **Cap at 0.50 - Missing final recommendation file.**
  `best_choice_for_my_room.md` is absent or contains no identifiable final
  choice.
- **Cap at 0.45 - Generic art advice.** The narrative reads mainly as generic
  decorating or art-appreciation advice and does not analyze the three locked
  artworks using their concrete visual traits.
- **Cap at 0.70 - Unsupported room-fit reasoning.** The output mentions room
  preferences but bases the conclusion on unsupported or contradicted claims,
  such as rejecting Friedrich as non-horizontal, inventing room constraints, or
  asserting that a bright/saturated work is quiet and dusk-like without evidence.
- **Cap at 0.55 - Room JSON ignored.** The recommendation does not use concrete
  details from `/tmp_workspace/clawbench/sources/my_room_style.json`.
- **Cap at 0.80 - Screenshot requirement not met.** Text deliverables may be
  strong, but screenshots are missing for one or more artworks or do not show
  enough page context to verify the source pages.
- **Cap at 0.30 - Credential or privacy leak.** Any value whose environment
  variable is declared in `.privacy` is emitted in user-visible output.

## 6. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** stop. A pass requires the Friedrich final
  recommendation, correct or near-perfect metadata, artwork-specific visual
  analysis, concrete room JSON mapping, and no score cap below `0.90`.
- **Continue (`0.60 - 0.89` after caps):** request one repair if follow-up budget
  remains. Typical continue cases are a wrong final artwork with otherwise
  complete artifacts, weak screenshot evidence, or a small number of fixable
  metadata errors.
- **Fail (`< 0.60` after caps):** record `finalStatus=failed`; do not spend
  follow-ups on outputs that are mostly missing, generic, fabricated,
  unsupported by the room JSON, or missing the metadata/final recommendation
  deliverable.

If the follow-up budget is exhausted, the final capped score still determines
the score band: `>= 0.90` pass, `0.60 - 0.89` continue/non-passing completion, and
`<0.60` fail.

## 7. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or the
public user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.csv` - canonical Met metadata.
- `references/ground_truth.json` - canonical artwork notes, room profile, and
  expected best choice.
- `references/reference_best_choice.md` - concise explanation of why Friedrich
  is the benchmark answer and why Monet and van Gogh are weaker.

## 8. Dynamic Content Note

This is a web task with locked reference facts. The Met pages may change after
the capture date, but grading must use the hidden reference snapshot from
`2026-04-23`. If live page content differs from the reference files, judge the
executor against the reference files and flag the drift rather than changing
the expected answer.
