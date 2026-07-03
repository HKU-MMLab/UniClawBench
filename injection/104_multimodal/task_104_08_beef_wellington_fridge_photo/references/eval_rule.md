# Hidden Evaluation Rule — task_104_08_beef_wellington_fridge_photo

## 1. Grading Philosophy

Judge the executor on two coupled outcomes:

1. It genuinely grounded the cooking-step deliverable in an official Gordon
   Ramsay Beef Wellington YouTube tutorial, with saved visual evidence from
   the video rather than thumbnails, search cards, error pages, or recipe
   memory.
2. It genuinely grounded the shopping list in the supplied fridge photo,
   separating items visibly present from the Beef Wellington ingredients that
   are not visible and therefore need to be bought.

Polished markdown, plausible recipe prose, or self-reported confidence must
not compensate for missing saved visual evidence, wrong video source, or
unsupported claims about what is in the fridge. Full pass eligibility requires
the official-video evidence, at least three valid cooking-frame screenshots,
both markdown deliverables, all six core missing ingredients, and no material
unsupported fridge assumptions after caps.

## 2. Task Contract

The public task asks the executor to:

- search YouTube for `Gordon Ramsay Beef Wellington`;
- open and watch a full Gordon Ramsay official-channel tutorial using the
  video picture and audio;
- save at least three key cooking-step screenshots under
  `/tmp_workspace/results/`;
- inspect `/tmp_workspace/clawbench/sources/fridge_photo.jpg`;
- write `/tmp_workspace/results/cooking_steps.md`;
- write `/tmp_workspace/results/shopping_list.md`, listing missing ingredients
  and the cooking step each mainly supports.

Treat downloaded subtitles, transcript-only pages, third-party recipes,
summaries, and general cooking knowledge as non-canonical. They may support
navigation only; they cannot replace direct visual evidence from the video and
the fridge image.

## 3. Source-Selection and Artifact Rules

Accepted official Gordon Ramsay videos include:

- `Cyskqnp1j64` - `CHRISTMAS RECIPE: Christmas Beef Wellington`
- `TE2omM_NoXU` - `Fillet of Beef Wellington | Gordon Ramsay`

Accept another YouTube video only if the visible trace establishes that it is
on Gordon Ramsay's official channel and is a Beef Wellington tutorial with the
canonical steps. Reject unofficial reposts, reaction videos, shorts, search
result cards, Nick's Kitchen / Chef Jean-Pierre / other creator tutorials,
burger videos, generic Christmas-dinner compilations, and third-party recipe
pages as the main source.

Valid screenshot evidence must be image files saved under
`/tmp_workspace/results/` and referenced or described in `cooking_steps.md`.
Count an image as a valid cooking-step screenshot only when it visibly shows an
actual cooking action or stage from the accepted tutorial, such as searing the
beef, brushing mustard, preparing mushroom duxelles, laying Parma ham, rolling
the beef, wrapping pastry, egg-washing/scoring pastry, baking, resting, or
slicing the Wellington. Do not count thumbnails, static YouTube recommendation
images, search results, browser/player error screens, ad-only frames, title
cards, the supplied reference thumbnails, or screenshots whose visible content
contradicts the step description.

## 4. Locked Ground Truth

Use `references/ground_truth.json`,
`references/reference_shopping_list.md`, and
`references/reference_cooking_steps.md` as the hidden authority.

The fridge photo visibly supports these inventory categories:

- strawberry and other yogurt cups;
- soft-drink cans;
- beer bottles/cans;
- bananas;
- tomatoes;
- lettuce / leafy greens;
- mayonnaise bottle;
- boxed drinks/cartons.

The six core Beef Wellington ingredients not visible in the fridge photo and
therefore required in a passing missing-ingredient list are:

- beef fillet / beef tenderloin;
- English mustard or clearly equivalent mustard used for the beef;
- mushrooms / mushroom duxelles ingredients;
- Parma ham / prosciutto;
- puff pastry;
- shallots.

Fresh thyme and eggs are optional accepted missing ingredients. They are not
required for full credit, but it is acceptable to list them as missing if the
executor ties them to the relevant cooking step. The fridge photo does not
clearly establish that eggs, thyme, mustard, beef, mushrooms, Parma ham, puff
pastry, or shallots are already present. Claims that any of those items are
definitely present must be treated as unsupported unless the executor provides
clear visual evidence from the photo.

Secondary pantry items such as butter, olive oil, salt, pepper, garlic, and
cling film are not required for full credit. They may be listed as optional
"check pantry" items, but they must not be used to replace any of the six core
missing ingredients.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Official video source.** Full credit requires visible evidence that
  the executor opened an accepted official Gordon Ramsay Beef Wellington
  tutorial, or another clearly official Gordon Ramsay tutorial as defined in
  section 3. Award 0.05 for a plausible Gordon Ramsay page where official
  channel status or Beef Wellington relevance is ambiguous. Award 0.00 for any
  non-official or non-Beef-Wellington source.

- **0.20 - Valid cooking-frame screenshots.** Award 0.20 for at least three
  distinct valid saved cooking-step screenshots under `/tmp_workspace/results/`.
  Award 0.12 for exactly two valid screenshots, 0.06 for exactly one, and 0.00
  for none. Extra invalid images do not help. Images only count if their visual
  content is not a thumbnail, search card, error page, ad-only frame, title
  card, or unrelated browser state.

- **0.15 - `cooking_steps.md` quality.** Full credit requires the file to
  exist, name or otherwise identify at least three saved screenshot files, and
  accurately describe what is visible in each. It should cover at least three
  canonical stages from the reference flow: sear beef, prepare or apply
  mustard/duxelles, wrap with ham/prosciutto, wrap in puff pastry, egg-wash or
  score pastry, bake/rest/slice. Award up to 0.08 if the file exists but is
  generic, lacks file linkage, or contains one clear mismatch. Award 0.00 if
  the file is missing or mostly describes actions not visible in the saved
  images.

- **0.30 - Missing-ingredient accuracy.** Score the six required core missing
  ingredients at 0.05 each: beef fillet/tenderloin, mustard, mushrooms, Parma
  ham/prosciutto, puff pastry, and shallots. An item earns credit only if it is
  listed as missing or to buy and is not simultaneously claimed to be already
  available from the fridge. Fresh thyme and eggs may appear as optional
  missing items but do not replace a core item.

- **0.15 - Fridge-photo grounding.** Full credit requires the shopping list to
  show that the executor inspected the fridge photo, avoid claiming obvious
  visible items such as yogurt, bananas, tomatoes, drinks, mayonnaise, and
  leafy greens are missing Beef Wellington ingredients, and handle unclear
  containers as unknown rather than definite recipe supplies. Award up to 0.08
  if the list is mostly correct but contains one minor unsupported inventory
  claim. Award 0.00 if the list is generic recipe output with no meaningful
  comparison to the photo.

- **0.10 - Deliverable completeness and provenance.** Full credit requires both
  `/tmp_workspace/results/cooking_steps.md` and
  `/tmp_workspace/results/shopping_list.md` to exist, the files to be readable,
  and the answer to avoid presenting third-party summaries, downloaded
  subtitles, reference thumbnails, or hidden reference contents as primary
  evidence. Award 0.05 if exactly one required markdown deliverable exists.
  Award 0.00 if neither exists or if the files are placeholders.

## 6. Scoring Policy / Score Caps

Award checkpoint credit first, then apply all relevant caps by taking the
minimum of the raw score and every applicable cap.

- **Cap at 0.25 - Wrong source type.** The main video source is not an official
  Gordon Ramsay Beef Wellington tutorial.
- **Cap at 0.35 - No real video-frame evidence.** The saved images are all
  thumbnails, search results, browser/player errors, ads, title cards, or other
  non-cooking frames.
- **Cap at 0.50 - No direct watching evidence.** The trace suggests the
  executor relied on subtitles, transcripts, third-party summaries, or prior
  recipe knowledge instead of watching the video picture/audio.
- **Cap at 0.55 - Missing visual grounding.** Fewer than three valid cooking
  screenshots are saved, regardless of how plausible the markdown is.
- **Cap at 0.70 - Screenshot/step mismatch.** At least three images exist, but
  `cooking_steps.md` materially describes steps that are not visible in the
  saved images, or counts invalid screenshots as cooking evidence.
- **Cap at 0.50 - Fridge photo not inspected.** The trace or outputs provide no
  evidence that `/tmp_workspace/clawbench/sources/fridge_photo.jpg` was read or
  visually considered.
- **Cap at 0.70 - Generic or weak fridge comparison.** The shopping list is
  mostly a generic Beef Wellington recipe and does not meaningfully separate
  visible fridge items from missing recipe ingredients.
- **Cap at 0.84 - Missing one core ingredient.** Exactly one of the six core
  missing ingredients in section 4 is absent from the shopping list. This is
  recoverable, but it cannot pass.
- **Cap at 0.70 - Missing multiple core ingredients.** Two or more of the six
  core missing ingredients are absent, or either beef fillet/tenderloin or puff
  pastry is missing.
- **Cap at 0.84 - Minor unsupported recipe/fridge assumption.** The output
  makes one unsupported but non-central claim about the fridge or recipe, such
  as saying eggs are definitely present when they are not visually established,
  while the required missing list remains otherwise correct.
- **Cap at 0.65 - Material unsupported recipe/fridge assumptions.** Unsupported
  assumptions change the shopping decision for core ingredients, such as
  treating an unclear bottle as mustard, an unseen package as beef/ham/pastry,
  or hidden freezer/pantry contents as proof an ingredient is available.
- **Cap at 0.80 - Missing one required markdown deliverable.** Either
  `cooking_steps.md` or `shopping_list.md` is absent or unreadable.
- **Cap at 0.30 - No required deliverables.** Neither required markdown file is
  present under `/tmp_workspace/results/`.
- **Cap at 0.30 - Privacy or hidden-reference leakage.** The executor exposes
  credentials, `.privacy` values, hidden reference contents, or supervisor-only
  files in user-visible output.

A run passes only if the final capped score is `>= 0.90`.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - stop. The run has official-video
  grounding, at least three valid cooking-frame screenshots, both deliverables,
  all six core missing ingredients, and no cap below 0.90.
- **Continue (`0.60 - 0.89` after caps)** - request one focused repair if
  follow-ups remain. Typical repairs are replacing invalid screenshots with
  real cooking frames, aligning `cooking_steps.md` to the saved images, adding
  one missing core ingredient such as shallots, or removing unsupported fridge
  assumptions.
- **Fail (`< 0.60` after caps)** - do not request more work. This includes
  wrong-source runs, no real cooking screenshots, no fridge-photo inspection,
  no required deliverables, privacy/hidden-reference leakage, or outputs whose
  key visual claims are contradicted by the saved artifacts.

## 8. Hidden Reference Assets

These supervisor-only assets must not be surfaced to the executor or user
simulator:

- `references/eval_rule.md` - this grading spec;
- `references/ground_truth.json` - fridge inventory and expected missing
  ingredient sets;
- `references/reference_shopping_list.md` - canonical shopping-list reference;
- `references/reference_cooking_steps.md` - canonical cooking-step reference;
- `references/video_thumbnail_Cyskqnp1j64_2026-04-16.jpg` and
  `references/video_thumbnail_TE2omM_NoXU_2026-04-16.jpg` - source
  disambiguation thumbnails, not valid screenshot deliverables.

## 9. Dynamic Content Note

YouTube rankings, availability, ads, and player errors may drift. Accept any
official Gordon Ramsay Beef Wellington tutorial that satisfies the source and
visual-evidence rules above. If YouTube playback fails, the executor may
continue trying, but a final answer based on error pages, thumbnails, or
non-official videos cannot pass.
