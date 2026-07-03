# Hidden Evaluation Rule — task_204_15_trip_packing_choice

## 1. Grading Philosophy

Judge whether the executor used the visual sources and `notes.json` to make the
correct practical packing decision, not merely whether it wrote a plausible
travel checklist. The core outcome is a grounded recommendation for the best
main bag plus an executable packing plan that respects the trip, weather, and
visible inventory.

Polished prose, tables, or self-reported confidence must not compensate for a
wrong main bag, ignored itinerary/weather constraints, or invented packing
items. Prefer semantic matching over exact wording, but require the answer to
be traceable to the provided files.

## 2. Task Contract

The executor must inspect `/tmp_workspace/clawbench/sources/trip_packing/` and
produce exactly:

- `/tmp_workspace/results/packing_plan.md`

The plan must include, at minimum:

- the final selected main bag / suitcase
- must-bring items
- placement guidance for main compartment, outside/front pockets, and protected
  or quick-access items
- items that need not be packed
- direct notes if something is missing, does not fit, or creates a conflict

## 3. Source-Selection and Target-Resolution Rules

Only these source files are in scope:

- `context_01.png` - trip itinerary
- `context_02.png` - weather screenshot
- `item_group_01.png` - clothing and shoes
- `item_group_02.png` - laptop and charger
- `item_group_03.png` - toiletries
- `option_01.png` - black backpack
- `option_02.png` - black weekender / duffel-style bag
- `option_03.png` - hard-sided carry-on suitcase
- `notes.json` - user constraints and packing notes

Treat `references/ground_truth.json` as authoritative if a source label or
visual interpretation is disputed. Do not infer additional source files or
external product specifications.

## 4. Locked Ground Truth

Canonical trip reading:

- Duration is 3 days.
- Trip type is a short business / client trip.
- Itinerary includes a Day 1 client workshop, Day 2 remote work plus dinner
  meeting, and Day 3 evening return.
- Hotel check-in is near metro with frequent short transfers.
- Weather is warm, humid, and rainy: rain chance / scattered showers / light
  rain across the three days.
- Constraints include preferring no checked baggage, moving easily between
  hotel and office, carrying a laptop and charger, and needing one smart-casual
  outfit.

Canonical bag choice:

- The best main bag is `option_03.png`, the hard-sided carry-on suitcase.
- It is best because it fits a 3-day trip without checked baggage, protects
  work clothing better than the backpack or duffel, handles mixed clothing,
  toiletries, shoes, and electronics better, and is still manageable for a
  short trip with transfers.
- `option_01.png` backpack and `option_02.png` duffel are not equivalent best
  answers. They may be discussed as inferior alternatives only.

Canonical must-pack inventory:

- laptop
- charger / cables
- smart shirt
- trousers
- toiletries
- medication
- one nicer pair of shoes
- compact umbrella or other rain-ready layer/preparation

Canonical placement logic:

- Main compartment: folded clothing, toiletry kit in a sealed pouch, and nicer
  shoes protected in a bag.
- Quick access / protected access: laptop, charger, medication, and travel
  documents.
- The plan should separate electronics from liquids/toiletries and shoes, and
  should account for keeping workshop/dinner clothing reasonably neat.

Canonical items to deprioritize:

- gym gear
- extra bulky coat
- duplicate shoes if space is tight
- light sweater is optional only if space allows

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Required deliverable and answer shape.** Full credit requires
  `/tmp_workspace/results/packing_plan.md` to exist, be readable Markdown or
  plain text, and contain a clear final luggage choice plus separate sections
  or clearly labeled content for must-bring items, placement guidance, and
  unnecessary items. Zero this line if the file is absent, empty, or lacks a
  final choice.

- **0.15 - Trip, weather, and constraints are correctly read.** Award 0.03
  each for correctly using these five facts: 3-day duration; business/client
  workshop plus dinner-meeting context; warm/humid/rainy weather; no checked
  baggage preference; frequent short transfers / hotel-to-office mobility.
  Do not award credit for vague travel boilerplate that could apply to any
  trip.

- **0.30 - Correct main bag selection and justification.** Award up to 0.18
  only when the final recommended main bag is unambiguously `option_03.png` or
  the hard-sided carry-on suitcase. Award up to 0.06 for explicitly rejecting
  or subordinating the backpack and duffel because they are worse for this
  3-day work trip. Award up to 0.06 for tying the carry-on to at least three of
  these reasons: 3-day capacity, no checked bag, clothing wrinkle/protection,
  mixed shoes/toiletries/electronics load, and manageable short transfers.
  If the final choice is the backpack or duffel, this checkpoint scores 0.00.

- **0.20 - Must-pack inventory coverage.** Score 0.025 for each canonical item
  present in the must-bring or equivalent required list: laptop; charger/cables;
  smart shirt; trousers; toiletries; medication; one nicer pair of shoes;
  compact umbrella or rain-ready layer/preparation. Items may be named in
  Chinese or English and may be described semantically. Do not give credit for
  unsupported substitutes that omit the canonical item.

- **0.15 - Executable placement and protection logic.** Award 0.04 for placing
  folded work clothing in the main compartment with wrinkle-conscious handling,
  0.03 for bagging/protecting shoes away from clothing, 0.03 for sealing
  toiletries away from clothing/electronics, 0.03 for putting laptop and
  charger in protected or quick-access locations, and 0.02 for keeping
  medication and travel documents quick-access. Generic "pack neatly" advice
  earns no credit for a subpoint unless the relevant item location is concrete.

- **0.10 - Pruning and conflict handling.** Award 0.03 for excluding gym gear,
  0.03 for excluding the bulky coat, 0.02 for limiting shoes to one nicer pair
  or warning against duplicate shoes, and 0.02 for calling out at least one
  realistic conflict or missing item such as cables not visible, medication not
  visible, liquid leakage, shoe/clothing contact, or capacity pressure.

Total: `0.10 + 0.15 + 0.30 + 0.20 + 0.15 + 0.10 = 1.00`.

## 6. Scoring Policy / Score Caps

Apply the rubric first, then apply all relevant caps by taking the minimum.
Caps are intended to prevent pass-level scores for failures that contradict the
locked ground truth.

- **Cap at 0.30 - No usable deliverable.** `packing_plan.md` is missing,
  unreadable, empty, or not saved under `/tmp_workspace/results/`.
- **Cap at 0.40 - No evidence of source grounding.** The plan is a generic
  packing article and does not meaningfully reference the provided trip,
  weather, bag options, visible items, or notes.
- **Cap at 0.55 - Wrong main bag choice.** The final recommendation selects
  `option_01.png` / backpack, `option_02.png` / duffel, or any non-carry-on
  item as the sole or primary main bag. This applies even if the rest of the
  packing list is detailed.
- **Cap at 0.70 - Ambiguous or undermined carry-on choice.** The answer names
  the carry-on but does not make it the clear final main plan, recommends
  multiple main bags without resolving the choice, or claims the backpack/duffel
  is equally good for the same constraints.
- **Cap at 0.65 - Ignored weather or itinerary.** The plan fails to use either
  the rainy/humid weather or the business itinerary when justifying the bag and
  packing list. If it ignores both weather and itinerary, cap at 0.55.
- **Cap at 0.75 - Missing rain preparation.** The plan otherwise reads the
  weather but omits any compact umbrella, rain-ready layer, or equivalent rain
  preparation from the required or recommended inventory.
- **Cap at 0.65 - Unsupported packing inventory.** The required packing list
  contains two or more material items not visible in the images, present in
  `notes.json`, or directly supported by itinerary/weather, and presents them
  as required rather than optional. Examples include invented extra shoes,
  gym gear, large coat, water bottle, camera, documents unrelated to travel, or
  other unsourced items that crowd out canonical essentials.
- **Cap at 0.70 - Poor inventory grounding.** The plan omits three or more
  canonical must-pack items, or it fails to distinguish visible items from
  notes-only items such as medication when making factual claims.
- **Cap at 0.80 - No concrete placement logic.** The plan lists items and a
  bag choice but lacks item-specific placement/protection guidance for clothing,
  electronics, toiletries, and shoes.

A run passes only if the final score is `>= 0.90` after all caps.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** The artifact is saved, chooses the
  hard-sided carry-on as the final main bag, correctly uses trip and weather
  context, covers the canonical must-pack inventory including rain preparation,
  gives concrete compartment/protection logic, and avoids unsupported required
  items.
- **Continue (`0.60 - 0.89` after caps):** The artifact is materially grounded
  but needs one focused repair, such as adding missing rain preparation,
  improving placement logic, pruning unsupported items, or making an already
  mentioned carry-on choice unambiguous.
- **Fail (`< 0.60` after caps):** The result is missing, generic, chooses the
  wrong main bag, ignores both itinerary and weather, or relies on fabricated
  required inventory. A wrong final main bag is a fail-level error because the
  central task is to choose the most suitable bag / suitcase.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec
- `references/ground_truth.json` - authoritative task facts, canonical bag
  choice, item list, placement logic, and unnecessary items

## 9. Dynamic Content Note

Offline task. No live API calls or external product pages are required. The
source corpus is static at runtime; grade against the local source files and
`references/ground_truth.json`, not against current online luggage or weather
information.
