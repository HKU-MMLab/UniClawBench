# Hidden Evaluation Rule — task_204_13_outfit_planning

## 1. Grading Philosophy

Judge whether the executor actually uses the invite, venue image, wardrobe
images, try-on/collage looks, and `notes.json` to choose the best existing
outfit for the user's semi-formal weekend event. The answer must recommend one
complete outfit from the available clothes and explain why it beats the other
candidate looks.

Score semantic fit to the locked reference, but be strict about the final
outfit. A polished write-up, good formatting, or generic style advice cannot
compensate for choosing the wrong shoes, recommending purchases, inventing
wardrobe items, or ignoring the event constraints.

The current source bundle uses product photos and outfit collages rather than
true full-body mirror try-on photos. Grade against the visible files on disk
and `references/ground_truth.json`, not against assumptions about unavailable
try-on photos.

## 2. Task Contract

The executor must inspect
`/tmp_workspace/clawbench/sources/outfit_planning/` and produce:

- `/tmp_workspace/results/outfit_recommendation.md`

The recommendation file must include:

- the inferred event type, formality, and environment/vibe
- one final complete outfit using only existing wardrobe items visible in the
  source files
- why the chosen outfit is more suitable than the alternatives
- which alternatives are too casual, too formal, incoherent, or otherwise
  weaker
- a very small adjustment suggestion, or an explicit statement that no extra
  adjustment is needed

No shopping list, new purchase recommendation, or invented clothing item is a
valid substitute for the requested existing-wardrobe selection.

## 3. Source-Selection and Target-Resolution Rules

Canonical inputs live under
`/tmp_workspace/clawbench/sources/outfit_planning/`. Treat these runtime files
as in scope:

- `context_01.png` - invite screenshot for Design Connections, a student and
  professional mixer
- `context_02.png` - bright indoor venue image with a warm, design-forward
  lounge/studio feel
- `notes.json` - user preferences and constraints
- `look_01.jpg`, `look_02.jpg`, `look_03.jpg` - candidate outfit collages
- `item_01.png` through `item_08.png` - individual wardrobe items

The supervisor should accept descriptive names that clearly refer to these
visible items, even when the executor does not use exact filenames. Do not
credit items that are not visible in the source directory or described in
`notes.json`.

## 4. Locked Ground Truth

Use `references/ground_truth.json` as authoritative.

Canonical event reading:

- student and professional design mixer / networking event
- bright, design-forward indoor venue with an approachable creative-studio or
  lounge feel
- smart casual to semi-formal, polished, social, and career-focused
- not black-tie, not a formal ballroom, not a casual daytime hangout, and not a
  party-first/cocktail event
- practical constraints: comfortable enough for standing and mingling for
  hours; clean and polished; minimal logos; not too streetwear, not too
  corporate, not overly bright
- no separate weather/forecast constraint appears in this static bundle; do not
  reward invented weather-based reasoning. If an answer mentions weather, it
  must not override the source-grounded indoor event constraints.

Canonical best outfit, required for a pass-level answer:

- `look_02.jpg` or the same existing-wardrobe combination
- light blue / dusty-blue tailored or soft-structured blazer
- white oxford shirt
- gray / charcoal straight-leg tailored trousers
- black polished slip-on dress shoes / loafers

Required interpretation of weaker alternatives:

- `look_01.jpg` - olive chore/overshirt with dark jeans and white sneakers is
  too casual and weekend-like for a student/professional mixer
- `look_03.jpg` - black slip-dress route with blazer/loafers reads more
  fashion-shoot, occasionwear, cocktail, or heavier than the invite's polished
  but approachable networking vibe

Allowed minor adjustments:

- keep the blazer open or otherwise relaxed
- keep accessories minimal
- ensure the shirt, trousers, and shoes are neat
- prefer the polished black shoes over white sneakers

Not allowed for pass-level credit:

- swapping the canonical black shoes for white sneakers in the final outfit
- selecting the jeans/sneakers route as the final outfit
- selecting the black dress route as the final outfit
- recommending a new bag, jacket, shirt, shoe, or accessory as necessary to make
  the outfit work
- treating the event as casual, black-tie, corporate interview, club/party, or
  outdoor/weather-driven

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within each checkpoint only when the
evidence is explicit in the produced recommendation.

- **0.10 - Output artifact and directness.** The required Markdown file exists
  at `/tmp_workspace/results/outfit_recommendation.md`, is readable, and names
  one final outfit choice. Full credit requires a complete outfit with top,
  layer if used, bottom or dress, and shoes. If the file is missing, empty, or
  only gives general advice, this line is 0.00.

- **0.20 - Event and constraint reading.** Correctly identifies the event as a
  Design Connections student/professional mixer or equivalent networking
  context, recognizes the bright indoor creative venue, and places formality at
  smart casual to semi-formal. Full credit also reflects the user's constraints
  from `notes.json`: polished, minimal, comfortable for standing/mingling, not
  too streetwear, not too corporate/black-tie, and not overly bright. Deduct for
  missing one of these dimensions; zero this line if the answer bases the
  recommendation on a casual hangout, formal gala, job interview, outdoor
  weather concern, or party-first reading.

- **0.35 - Final outfit correctness.** Full credit requires the canonical
  existing-wardrobe outfit: light/dusty-blue blazer, white oxford shirt,
  gray/charcoal straight-leg tailored trousers, and black polished slip-on dress
  shoes/loafers. Minor wording differences are fine (`navy` vs `blue`,
  `charcoal` vs `gray`, `dress shoes` vs `loafers`) when the selected visible
  items are unambiguous. Award at most 0.25 here if the final outfit is based on
  the blazer/oxford/trouser formula but changes one required component. Award
  at most 0.15 here if the final outfit mixes canonical and non-canonical items
  in a way that weakens the event fit. Award 0.00 here if the final outfit is
  primarily `look_01`, primarily `look_03`, a generic capsule outfit, or uses
  new/unseen clothing as a required component.

- **0.15 - Grounded visual and note-based reasoning.** Explains the choice with
  concrete visible/source-grounded evidence: invite text or event title,
  indoor venue mood, blazer structure/color, white oxford polish, gray trouser
  straight-leg/clean fit, black shoe polish, and relevant `notes.json`
  preferences. Full credit requires at least four distinct grounded references
  spanning event/venue, wardrobe, and notes. Generic fashion maxims without
  source details earn at most 0.05.

- **0.12 - Alternative comparison.** Correctly discusses at least two weaker
  alternatives, including why `look_01` is too casual and why `look_03` is more
  occasionwear/fashion-shoot/heavy/less aligned. Partial credit is available
  for one correct alternative comparison. Do not credit comparisons that
  reverse the locked interpretation, such as praising white sneakers as the
  best final shoe over the black loafers.

- **0.05 - Minor adjustment compliance.** Gives only small no-purchase
  adjustments that fit the locked answer, such as leaving the blazer open,
  keeping accessories minimal, neat trouser/shoe presentation, or explicitly
  saying no extra adjustment is needed. Zero this line if the adjustment turns
  into shopping, requires a new item, or changes the final outfit away from the
  canonical combination.

- **0.03 - No hallucinated or contradictory source claims.** The answer does
  not invent wardrobe items, filenames, mirror-photo details, weather, dress
  code text, or user preferences that are absent from the sources. It also does
  not materially contradict visible evidence, such as claiming the selected
  black loafers are white sneakers. Any clear hallucinated required item zeroes
  this line and may trigger a cap in §6.

Total: `0.10 + 0.20 + 0.35 + 0.15 + 0.12 + 0.05 + 0.03 = 1.00`.

## 6. Scoring Policy / Score Caps

Score checkpoint-by-checkpoint, then apply all relevant caps by `min`. A run
passes only if the final score is `>= 0.90` after caps.

- **Cap at 0.30 - No usable deliverable.** The required recommendation file is
  missing, unreadable, empty, or not saved under `/tmp_workspace/results/`.

- **Cap at 0.40 - Ignores the wardrobe task.** The answer does not choose from
  the provided clothes, gives only generic outfit advice, or makes a shopping
  recommendation the core solution.

- **Cap at 0.45 - Clearly wrong outfit choice.** The final recommendation is
  primarily the jeans-and-white-sneakers / olive chore-jacket route
  (`look_01`), the black slip-dress route (`look_03`), or another outfit that
  does not center the blazer + white oxford + gray trousers formula.

- **Cap at 0.70 - Near-miss outfit with wrong key component.** The answer
  correctly chooses the blazer + white oxford + gray trousers core but swaps
  the canonical black polished slip-on shoes/loafers for white sneakers or any
  other non-canonical shoe as the final recommendation. This cap is intended
  to keep a well-reasoned sneaker-swap answer in Continue rather than Pass.

- **Cap at 0.55 - Event, environment, or weather constraints ignored.** The
  answer ignores the student/professional mixer, indoor creative venue, and
  standing/mingling requirements, or bases the final choice on unsupported
  outdoor/weather assumptions. If a future runtime fixture adds explicit
  weather constraints, failure to honor them also triggers this cap.

- **Cap at 0.60 - Weak or absent source grounding.** The answer may choose a
  plausible outfit but does not cite concrete evidence from the invite, venue,
  visible wardrobe, looks, or `notes.json`.

- **Cap at 0.65 - Hallucinated wardrobe items.** The final outfit requires any
  item not present in the source images or `notes.json`, including a new bag,
  new shoes, different blazer, different trousers, jewelry, coat, or accessory.
  If the hallucinated item is merely optional and clearly not part of the final
  outfit, apply the rubric deduction but not this cap.

- **Cap at 0.75 - Missing alternative analysis.** The answer does not compare
  the chosen outfit against the weaker candidate looks, or discusses only one
  alternative.

- **Cap at 0.80 - Missing minor adjustment requirement.** The answer otherwise
  selects the correct outfit but omits the requested small adjustment / "no
  extra adjustment needed" statement.

- **Cap at 0.80 - Contradictory final recommendation.** The answer names the
  canonical outfit in one place but elsewhere clearly recommends a conflicting
  final item, such as saying to wear the black loafers and then concluding with
  white sneakers.

- **Cap at 0.30 - Privacy or credential leak.** Any value whose environment
  variable is declared private is emitted in user-visible output. No such
  values are expected in this task.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** - stop only when the recommendation selects
  the canonical existing-wardrobe outfit, respects the mixer/venue constraints,
  is visibly grounded, compares both weaker looks, includes the minor
  adjustment requirement, and has no active cap below 0.90.

- **Continue (`0.60 - 0.89` after caps)** - request one follow-up when the answer
  is mostly grounded and recoverable, such as choosing the right blazer/oxford/
  trouser core but swapping in white sneakers, omitting one alternative
  comparison, missing the minor adjustment statement, or needing clearer final
  wording.

- **Fail (`<0.60` after caps)** - do not spend follow-ups on answers that lack a
  usable deliverable, ignore the provided wardrobe, choose a clearly wrong
  outfit family, invent required items, or misread the event/weather context so
  badly that the recommendation is not anchored to the source bundle.

If follow-up budget is exhausted, keep the numeric score and verdict consistent
with these bands: Pass `>= 0.90`, Continue `0.60 - 0.89`, Fail `<0.60`.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file) - grading spec
- `references/ground_truth.json` - authoritative event reading, canonical best
  outfit, weaker alternatives, and acceptable minor adjustments

## 9. Dynamic Content Note

Offline task. No live API calls or current weather lookups are expected. The
supervisor compares executor output to the static source bundle and
`references/ground_truth.json`. If fixture names in historical manifests differ
from the live `item_*.png` / `look_*.jpg` names, grade by the visible file
contents and locked ground truth rather than by old manifest labels.
