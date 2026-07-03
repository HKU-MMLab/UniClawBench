# Hidden Evaluation Rule — task_204_26_funny_animal_memes

## 1. Grading Philosophy

Grade whether the executor solved the fixed target-segment task, not whether it
made generally funny animal memes. The current public task asks for the
groundhog / woodchuck food-stealing segment in the linked video and requires
one raw keyframe plus one meme image for each distinct food moment.

Use semantic visual matching against the hidden ground truth rather than exact
pixel or filename equality. Nearby frames are acceptable when the same food
moment is clear. Do not give credit for confident self-reporting, subtitle-only
inferences, generic animal scenes, stock images, or AI-generated replacements.

## 2. Task Contract

Canonical output location is `/tmp_workspace/results/`. When judging archived
run copies, `result/` or `visible/result/` is the equivalent copied result root.

Required final artifacts:

- `/tmp_workspace/results/groundhog_frames/` with one raw, non-captioned
  keyframe for each of the five required food moments.
- `/tmp_workspace/results/memes/` with one captioned meme image for each of
  the same five food moments.
- `/tmp_workspace/results/meme_index.md` with exactly five final rows, in video
  order.

Each index row must include the ordinal, food name or type, video timestamp in
`mm:ss` or `hh:mm:ss` format, raw frame filename, meme filename, scene
description, and caption text. Timestamps are mandatory, not optional.

## 3. Locked Ground Truth

Grade against `references/ground_truth.json` and
`references/reference_meme_index.md`. The visual answer key is
`references/marmot_food_reference_sheet.png` plus the five files under
`references/marmot_food_frames/`.

Locked resource:

- Primary video: `https://www.youtube.com/watch?v=39ColarOWKo`
- Accepted mirror: `https://www.dailymotion.com/video/x9rlvem`, only if it is
  the same playable video content
- Target segment: the "Chunk The Groundhog" / woodchuck food-stealing segment
  where the animal eats directly in front of a security camera
- Hidden verification window: approximately `00:10:28` through `00:10:40`

The five required food moments, in required order, are:

| order | food_id | accepted food labels | approximate timestamp | hidden frame |
| --- | --- | --- | --- | --- |
| 1 | `small_yellow_green_snack` | small yellow-green food piece, yellow-green vegetable or fruit chunk, first small food item | `00:10:28` | `marmot_food_frames/food_01_small_yellow_green_snack.png` |
| 2 | `red_apple` | red apple, apple | `00:10:29` | `marmot_food_frames/food_02_red_apple.png` |
| 3 | `banana` | banana | `00:10:30` | `marmot_food_frames/food_03_banana.png` |
| 4 | `carrot` | carrot | `00:10:34` | `marmot_food_frames/food_04_carrot.png` |
| 5 | `leafy_green` | leafy green, lettuce, green leaf, leafy vegetable | `00:10:38` | `marmot_food_frames/food_05_leafy_green.png` |

The older open-ended assets under `references/reference_frames/`,
`references/reference_memes/`, `_candidates/`, `_tiles/`, and `_filmstrip*`
are audit or legacy authoring artifacts. They do not expand the accepted answer
set and must not justify passing arbitrary funny animal scenes.

## 4. Matching Rules

Accept a raw frame or meme for a food only when all of these are true:

- The groundhog / woodchuck is clearly visible.
- The specific required food is clearly visible in the animal's paws, mouth, or
  immediate eating pose.
- The image is a frame from the target video or accepted same-content mirror.
- The meme image is derived from the corresponding raw frame, allowing normal
  cropping, scaling, and text overlay.

Timestamps may drift slightly from the table when the saved frame visibly
matches the correct food moment. A broad timestamp such as "around 10 minutes",
"unknown", or a range that cannot identify the frame does not satisfy the
timestamp requirement.

## 5. Checkpoint Rubric

Weights sum to 1.00.

| ID | What matters | Weight |
| --- | --- | --- |
| CP1 | Artifact structure: index exists; five raw keyframes exist under `groundhog_frames/`; five meme images exist under `memes/`; final filenames are unique and loadable. Award up to 0.05 for each of index, raw frames, and memes. | 0.15 |
| CP2 | Segment and food identification: target groundhog segment is selected (0.05); all five canonical foods appear exactly once in required order (0.20, 0.04 per food); no duplicate, extra final row, or replacement scene is used (0.05). | 0.30 |
| CP3 | Visual grounding: for each food, the raw frame and corresponding meme both visibly match the hidden food moment, show the groundhog and food clearly, and are video-derived. Award 0.05 per food. | 0.25 |
| CP4 | Index completeness: each row includes ordinal, food label, parseable timestamp, raw frame filename, meme filename, scene description, and caption text, and the filenames match real final artifacts. Award 0.03 per complete row. | 0.15 |
| CP5 | Meme rendering quality: caption text is readable, high-contrast, meme-like, and does not obscure the groundhog or food. Award 0.03 per meme. Caption wording may vary freely if the scene grounding is correct. | 0.15 |

Score the rubric first, then apply all applicable score caps in section 6 by
taking the minimum of the raw rubric score and every matching cap.

## 6. Score Caps

Caps target failure modes that the weighted rubric might otherwise over-credit.
Apply the most restrictive cap supported by the evidence.

- Cap at `0.30` if no substantive deliverables are produced, or fewer than
  three final meme images exist.
- Cap at `0.40` if `meme_index.md` is missing or unusable.
- Cap at `0.45` if the work is not grounded in the linked target video or an
  accepted same-content playable mirror, including subtitle-only, summary-only,
  text-only, or unauditable claims.
- Cap at `0.45` if any final required raw frame or meme is AI-generated, stock,
  web-sourced, or otherwise not extracted from the target video/mirror.
- Cap at `0.50` if the answer follows the obsolete open-ended prompt and
  produces arbitrary funny animal scenes, even if some scenes come from the
  same compilation.
- Cap at `0.55` if the selected scenes are from the wrong segment, meaning not
  the groundhog / woodchuck food-stealing segment in front of the security
  camera.
- Cap at `0.59` if the answer reaches the correct groundhog segment but misses,
  duplicates, or replaces two or more of the five required foods.
- Cap at `0.75` if all five required foods are present but the order is wrong
  or the index-to-image pairing swaps food moments.
- Cap at `0.80` if exactly one of the five required foods is missing, wrong,
  duplicated in place of another, or visually unclear.
- Cap at `0.80` if no raw keyframes are provided under `groundhog_frames/` and
  only captioned meme images are available.
- Cap at `0.84` if one or two otherwise-correct raw keyframes are missing,
  captioned, or not separately linked from the index.
- Cap at `0.84` if any required timestamp is absent, marked unknown, optional,
  too vague to identify the frame, or not attached to the corresponding food
  row.
- Cap at `0.84` if the index omits required raw-frame or meme filenames for
  otherwise correct images, or filenames do not match actual final artifacts.
- Cap at `0.75` if meme captions are missing, unreadable, too low contrast, or
  obscure the animal or food in two or more memes.

An answer can pass only if the capped score is `>= 0.90`. Therefore any cap of
`0.84` or lower makes the verdict `continue` or `fail`, not `pass`.

## 7. Continue vs Fail Guidance

- **Pass** (`>= 0.90` after caps): all five canonical food moments from the
  locked groundhog segment are present exactly once in order; raw frames, memes,
  timestamps, filenames, and index rows are complete; captions are readable; no
  cap below pass applies.
- **Continue** (`0.60 - 0.89` after caps): the run is substantially on the
  correct groundhog segment but needs repair, such as one missing or weak food,
  missing raw-frame artifacts, missing or vague timestamps, filename mismatches,
  or caption readability issues.
- **Fail** (`< 0.60` after caps): the run is not grounded in the target video,
  uses generated or stock images, follows arbitrary funny animal scenes, selects
  the wrong segment, produces too few deliverables, or misses/replaces two or
  more required food moments.

When follow-ups are available, use `continue` only for defects that can be fixed
by adding or correcting artifacts from the already identified groundhog segment.
Do not continue an open-ended animal-meme answer that has not found the locked
groundhog food segment; it should fail under the caps.

## 8. Hidden Assets and Dynamic Content Note

Supervisor-only references:

- `references/eval_rule.md`
- `references/ground_truth.json`
- `references/reference_meme_index.md`
- `references/reference_meme_notes.md`
- `references/marmot_food_reference_sheet.png`
- `references/marmot_food_frames/food_01_small_yellow_green_snack.png`
- `references/marmot_food_frames/food_02_red_apple.png`
- `references/marmot_food_frames/food_03_banana.png`
- `references/marmot_food_frames/food_04_carrot.png`
- `references/marmot_food_frames/food_05_leafy_green.png`

This is an online-video task, but the grading answer key is fixed by the hidden
snapshot in `ground_truth.json`. If the live website changes, becomes
unavailable, or shows a different video, judge the executor against the locked
ground-truth segment and flag the resource drift rather than accepting a new
set of animal memes.
