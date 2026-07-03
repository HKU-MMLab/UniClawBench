# Hidden Evaluation Rule — task_204_17_plant_corner_care

## 1. Grading Philosophy

Judge whether the executor produced a plant-by-plant care plan that is
actually grounded in the supplied images and `habits.json`, not a generic house
plant template. The answer must preserve the three canonical plant-care reads:

1. pothos / trailing vine: generally healthy, but sprawling / untidy enough to
   benefit from brighter indirect light management, rotation, and light pruning
   or repositioning
2. snake plant: largely healthy, but the shared weekly watering routine is too
   aggressive or risky for it
3. small rosette succulent: generally healthy-looking to mildly stretched, but
   the clearest case for the brightest available light and the driest watering
   schedule

Reward concise, practical next steps. Penalize confident diagnoses that are not
visible in the images, especially rootbound claims, rot, pests, exact pot
measurements, severe etiolation, or urgent repotting/division when those claims
replace the locked priorities below.

## 2. Task Contract

The executor must inspect `/tmp_workspace/clawbench/sources/plant_corner/`,
including the plant images and the watering/light habit file, and produce:

- `/tmp_workspace/results/plant_care_plan.md`

The plan may be in Chinese or English. It must give, for each canonical plant
group, a current-state judgment, the highest-priority issue, and one or more
simple executable next steps. Optional evidence copies or notes under
`/tmp_workspace/results/` are neutral; they do not compensate for a wrong or
missing final plan.

## 3. Source-Selection and Target-Resolution Rules

Canonical input files are the files present at runtime under
`/tmp_workspace/clawbench/sources/plant_corner/`. The supervisor treats these
fixtures as in scope:

- `plant_01_overview.jpg`, `plant_01_detail.jpg` — pothos / trailing vine
  source group
- `plant_02_overview.jpg`, `plant_02_detail.jpg` — snake plant source group
- `plant_03_overview.jpg`, `plant_03_detail.jpg` — small rosette succulent
  source group
- `space_01.png` — environmental context, including window/desk placement
- `habits.json` or the runtime alias `my_plant_habits.json` — habit context

Do not require the executor to use these exact filenames in the prose. Match by
semantic plant group. Extra background-plant sections are allowed only if they
do not replace, obscure, or contradict the three canonical groups.

## 4. Locked Ground Truth

Structured expected answer lives at `references/ground_truth.json`; the
following snapshot is authoritative for grading.

Canonical plant mapping and required care logic:

- **Plant 01: pothos / trailing vine.** Heart-shaped green and variegated
  trailing leaves, glossy and mostly healthy. The useful read is
  healthy-but-sprawling / untidy / desk-space management, not a severe rescue
  case. Priority actions should be bright indirect or morning-light management,
  occasional rotation, and light pruning, redirecting, or repositioning of long
  vines. Accept `pothos`, `devil's ivy`, `epipremnum`, `trailing vine`, or
  uncertainty with the same care logic. Do not require strong distress language.

- **Plant 02: snake plant.** Upright sword-like leaves, stable and
  healthy-looking from the available images. The required priority is that the
  same-amount weekly watering routine is too frequent or too risky for this
  plant; advice should say to let soil dry thoroughly and water less often than
  the pothos. Repotting, division, or crowding may be mentioned only as optional
  / uncertain; it must not be the main issue.

- **Plant 03: small rosette succulent.** Small succulent with fleshy leaves,
  generally healthy-looking though it may be described as mildly stretched or
  light-hungry. It is the plant that most needs the brightest available
  placement, especially the east-facing window / sill, rotation, and a much
  drier watering schedule. The answer should separate it from the weekly
  same-amount watering habit. Exact species is not required.

Required environmental context:

- The window is east-facing, with strongest light in the morning.
- Watering every Sunday with the same amount for all pots is suboptimal.
- The owner wants a low-maintenance routine, has limited desk space, sometimes
  runs AC near the desk, rarely rotates pots, and rarely repots.

Pass constraints:

- A pass requires all three canonical plant groups to be present and aligned
  with the care logic above. Polished formatting, long explanations, copied
  source files, or confident language cannot compensate for wrong plant
  priorities.
- A high-scoring answer may split the pothos overview into multiple pothos
  subpots or mention a background plant from `space_01.png`, but only if the
  three canonical care logics remain complete and correct.
- A high-scoring answer must keep uncertainty where the visual evidence is
  limited, especially exact species, pot drainage, rootbinding, pests, rot, and
  precise severity.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within each checkpoint only for
observable content in `plant_care_plan.md`; do not infer intent from the
executor's transcript unless the saved file is ambiguous about file existence.

- **0.10 — Deliverable shape and coverage.** `plant_care_plan.md` exists in
  `/tmp_workspace/results/`, is readable Markdown or plain text, and covers the
  canonical pothos, snake plant, and succulent groups. Each covered group must
  include current state, priority issue, and next step. Full credit requires all
  three groups; two groups earns at most 0.06 here; one group earns at most
  0.03; no usable file earns 0.00.

- **0.10 — Source grounding and habit context.** The plan explicitly uses both
  visual evidence and habit/environment context. Full credit requires mention
  of the east-facing / morning-light condition and the same-Sunday /
  same-amount watering habit, plus at least one relevant visual observation
  from leaves, growth habit, pot/placement, desk space, AC, or rotation. Award
  up to 0.06 if either the visual grounding or the habit context is present but
  incomplete. Generic advice with no visible link to the sources earns 0.00.

- **0.15 — Plant identification and mapping.** Correctly maps the three
  canonical source groups to functional plant categories: pothos/trailing vine,
  snake plant, and succulent. Exact Latin or cultivar names are not required.
  Award 0.05 per correctly mapped group. If an extra background plant is
  discussed, it is neutral unless it causes a canonical group to be omitted or
  misread.

- **0.17 — Pothos / trailing vine diagnosis and advice.** Full credit requires
  framing plant 01 as generally healthy / not a rescue case, identifying
  sprawling, untidy, long-vine, desk-space, or uneven-light management as the
  priority, and recommending rotation plus pruning, redirecting, or brighter
  indirect / morning-light placement. Deduct for making rootbinding, severe
  yellowing, severe droop, pest damage, or urgent repotting the main diagnosis
  unless stated as uncertain and secondary.

- **0.17 — Snake plant diagnosis and advice.** Full credit requires describing
  plant 02 as mostly stable / healthy-looking and identifying the shared weekly
  watering routine as too frequent or risky for snake plant. The next step must
  be drier care: let soil dry thoroughly, water less often than the pothos, and
  avoid overwatering. Deduct heavily if the answer says weekly equal watering is
  fine or makes repotting/division/crowding the main priority.

- **0.19 — Succulent diagnosis and advice.** Full credit requires identifying
  plant 03 as the clearest light-and-dry-care priority, recommending the
  brightest available east-window/sill placement, rotation, and watering only
  after the soil dries much more fully than the other pots. It may describe the
  plant as healthy-looking, compact, light-hungry, or mildly leggy. Deduct for
  missing either the bright-light priority or the separate dry watering
  schedule. Deduct for severe unsupported rescue framing such as irreversible
  decline, rot, or mandatory surgery unless presented cautiously as optional.

- **0.12 — Practicality, prioritization, and uncertainty.** Advice is simple
  enough for a low-maintenance owner, prioritizes the succulent light/dry-care
  adjustment and the snake plant watering change, and avoids overcomplicated
  schedules. The plan explicitly acknowledges uncertainty for fuzzy species or
  non-visible facts such as drainage, root condition, pests, or exact pot size.
  Award up to 0.08 if the advice is actionable but either prioritization or
  uncertainty language is weak.

Total: `0.10 + 0.10 + 0.15 + 0.17 + 0.17 + 0.19 + 0.12 = 1.00`.

## 6. Scoring Policy / Score Caps

Compute the rubric score in §5, then apply all relevant caps by `min`. A run
passes only if the final score after caps is `>= 0.90`.

- **Cap at 0.30 — No usable deliverable.** `plant_care_plan.md` is missing,
  unreadable, empty, or unrelated to plant care.

- **Cap at 0.40 — No source grounding.** The answer is a generic houseplant
  template with no clear use of the provided images or habit file.

- **Cap at 0.45 — Unsafe or materially wrong care advice.** The plan gives
  advice likely to harm a canonical plant, such as recommending the same weekly
  watering amount for snake plant or succulent, increasing water for the
  succulent without dryness checks, placing the succulent in low light,
  applying harsh chemicals without visible pests, or ignoring drainage while
  prescribing frequent watering.

- **Cap at 0.50 — Misidentified or omitted plants.** Two or more canonical
  plant groups are omitted, swapped, or identified in a way that drives the
  wrong care logic. If exactly one canonical group is misidentified but the
  advice remains partly compatible, cap at 0.70.

- **Cap at 0.55 — Undifferentiated care.** The plan gives the same watering,
  light, and next-step advice to all plants or fails to separate pothos, snake
  plant, and succulent needs.

- **Cap at 0.55 — Succulent priority missed.** The plan does not identify the
  succulent as needing the brightest placement and the driest / least frequent
  watering of the group.

- **Cap at 0.65 — Watering-habit context ignored.** The answer does not use
  the shared Sunday / same-amount watering habit to differentiate plant care,
  even if individual advice is otherwise plausible.

- **Cap at 0.70 — Major overdiagnosis displaces priorities.** One major
  unsupported diagnosis becomes the main recommendation, such as rootbound
  pothos requiring repotting, overcrowded snake plant requiring division, or a
  severely failing succulent requiring surgery, when the locked priority should
  be light/rotation/pruning or watering differentiation. If two or more such
  overdiagnoses drive the plan, cap at 0.55.

- **Cap at 0.75 — Unsupported visual claims.** The plan relies on visible
  claims not supported by the images, such as confirmed pests, root rot,
  drainage holes/no drainage holes, exact pot diameters, exact vine lengths,
  exact lean angles, severe yellowing, or rootbinding. If unsupported claims
  are minor and explicitly uncertain, do not apply this cap.

- **Cap at 0.80 — Missing required uncertainty.** The plan presents exact
  species, drainage, root condition, pests, or disease status as certain where
  the sources do not support certainty, but the plant priorities are otherwise
  correct.

- **Cap at 0.84 — Minor contradiction in an otherwise strong answer.** The
  plan gets the three canonical priorities mostly right but includes one
  localized contradiction that could confuse care, such as saying the snake
  plant is "fine with weekly watering" while later advising dry checks.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps)** — stop only when the saved plan covers all
  three canonical groups, applies the locked care logic, is grounded in images
  and habits, and has no cap below 0.90.

- **Continue (`0.60 - 0.89` after caps)** — request one targeted revision when
  the output is complete and source-based but has fixable issues: one plant
  priority is wrong, uncertainty language is missing, watering differentiation
  is incomplete, or unsupported claims need to be softened.

- **Fail (`< 0.60` after caps)** — no further follow-up is warranted when the
  file is missing, generic, unsafe, omits or swaps multiple canonical plants,
  gives undifferentiated care, misses the succulent light/dry-care priority, or
  has multiple overdiagnoses that drive wrong recommendations.

If the follow-up budget is exhausted, keep the numerical band above but set the
requested action according to the harness rules; do not mark a capped
`0.60 - 0.89` answer as pass.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` — this grading spec.
- `references/ground_truth.json` — locked expected plant groups, plant states,
  priority issues, next steps, environmental factors, and uncertainty note.

## 9. Dynamic Content Note

Offline task — no live web lookup is required. The plant images and habit file
are static fixtures. Species naming can be flexible, but the care logic and
visible-evidence discipline are not flexible. If the fixture images and
`references/ground_truth.json` ever appear to disagree, treat the ground-truth
file as authoritative and flag the mismatch rather than re-judging from
general plant knowledge.
