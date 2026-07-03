# Hidden Evaluation Rule — task_104_27_yosemite_half_dome_camping

## 1. Grading Philosophy

Judge whether the executor produced a grounded Yosemite Half Dome and camping
assessment, not whether the prose is polished. A high score requires all three
core outcomes:

1. Correct Half Dome facts from the official NPS page.
2. Correct Yosemite Valley campground facts for Upper Pines, Lower Pines, North
   Pines, and Camp 4.
3. A trip-specific, safety-conscious recommendation based on
   `/tmp_workspace/clawbench/sources/yosemite_trip.json`.

The public trip profile is intentionally not suitable for Half Dome as-is.
Do not award pass-level credit to an answer that encourages the group to attempt
Half Dome without first resolving permit, fitness, gear, exposure, and weather
constraints.

## 2. Task Contract

The executor was asked to open official NPS pages for Half Dome and Yosemite
camping, optionally follow NPS campground detail pages, read the trip JSON, and
create these files under `/tmp_workspace/results/`:

- `half_dome_guide.md`
- `campground_options.csv`
- `trip_assessment.md`
- `half_dome_reference.png`
- `campground_reference.png`

The markdown and CSV files must contain usable task answers. The screenshot
files must be viewable image artifacts from official NPS pages or clearly
derived browser captures of those pages; blank, irrelevant, or non-NPS images do
not satisfy the screenshot requirement.

Before awarding pass-level credit, inspect the actual screenshot pixels, not
only their filenames, captions, or file paths:

- A usable Half Dome screenshot must visibly show Half Dome-specific content,
  such as the Half Dome page title, Hiking Half Dome section, permit/cables
  text, map/route content, or the distance/elevation/time facts. A screenshot
  that only shows the NPS site header, cookie/banner area, road-closure alerts,
  or generic Yosemite navigation is an official-page screenshot but is not
  usable Half Dome evidence.
- A usable campground screenshot must visibly show Yosemite camping or
  campground-specific content, such as the campground table, named Yosemite
  Valley campground rows, reservation windows, fees, or a campground detail
  page. A screenshot that only shows NPS alerts/header/navigation is not usable
  campground evidence.
- If the answer text is strong but both required screenshots are only header /
  alert / unrelated official-page captures, treat this as pass-blocking
  incompleteness. Request a follow-up to save relevant page-region screenshots
  rather than passing the run.

## 3. Source-Selection and Target-Resolution Rules

Use the hidden files as the authoritative snapshot:

- `references/ground_truth.json`
- `references/campgrounds_ground_truth.csv`

The snapshot was captured on `2026-04-23`. If current live NPS pages have drifted
after that date, grade against the hidden snapshot, not against newer live page
claims. The executor may cite live NPS pages, but pass-level credit requires the
claims to be compatible with the hidden facts below.

Accept minor formatting variants, translations, and unit expansions when the
underlying fact is the same. For example, `14-16 miles`, `14 to 16 mi round
trip`, and a Chinese translation of the same fact are equivalent. Do not accept
materially different numbers, seasons, permit processes, or campground
recommendations.

Visible official NPS evidence may refine a snapshot field when it does not
contradict the locked fact. In particular, `campgrounds_ground_truth.csv` says
that Pines campground fees were "not clearly visible on the server-rendered
pages used for this task"; this is not a locked assertion that the fee is
unknown. If the executor saved a relevant NPS campground table or detail-page
screenshot that visibly shows a Pines fee such as `$36`, treat that fee as
supported official-source evidence, not as hallucinated or unsupported drift.
Likewise, exact visible date ranges such as `Apr 21-Oct 19` may be accepted as
official refinements of "roughly April to October" when they come from a saved
NPS table or page trace.

## 4. Locked Ground Truth

### Half Dome Facts

The correct Half Dome guide must include these facts:

- Round-trip distance: `14-16` miles.
- Elevation gain: `4,800` feet.
- Typical time: `10-12` hours.
- A Half Dome permit is required when the cables are up.
- Day-hiker permits are obtained through the March lottery, with a limited
  number available two days in advance.

The guide must include meaningful safety guidance covering at least these areas:

- Do not attempt the cables in rain, thunderstorms, or when the rock surface is
  wet.
- Bring proper footwear, gloves, enough water, and a real flashlight or
  headlamp.
- The hike is not appropriate for unprepared hikers, people uncomfortable with
  exposure, or people without endurance for a very long day.

### Yosemite Valley Campground Facts

The campground output must cover all four required Yosemite Valley options:

- `Upper Pines`: Yosemite Valley; open all year; reservations all year; released
  five months in advance.
- `Lower Pines`: Yosemite Valley; roughly April to October; reservations
  released five months in advance.
- `North Pines`: Yosemite Valley; roughly April to October; 2026 early access
  lottery plus regular leftovers / release process.
- `Camp 4`: Yosemite Valley; mid-April to October reservation season with
  reservations one week in advance; winter / off-season first-come,
  first-served; `$10 per person per night`.

If the executor cannot verify current Pines campground fees from the rendered
official pages, it is acceptable to say the fee was not clearly visible. Do not
reward invented Pines fees unless they are explicitly supported by visible
official source evidence.

For Camp 4, distinguish three separate facts:

- It can be described as open all year.
- Main-season reservations are required / available roughly mid-April through
  October or early November and are released one week in advance.
- Winter or off-season use is first-come, first-served.

Do not penalize the phrase "open all year" by itself if the output also
distinguishes the reservation season from the off-season FCFS period. If the
output says "open all year" but omits off-season FCFS, deduct the Camp 4
reservation / FCFS split credit; do not treat that omission as a full campground
coverage collapse when the rest of the Camp 4 row is grounded.

### Public Trip Constraints

The trip JSON facts that must drive the recommendation are:

- Dates: `2026-07-18` to `2026-07-20`.
- Group size: `3`.
- Trip style: first Yosemite car-camping trip.
- Fitness: mixed; two moderate hikers; one beginner comfortable only with
  `5-6` hour hikes.
- Exposure: one traveler gets anxious on exposed heights.
- Gear gaps: only two hiking boots, zero cable gloves, one headlamp, one rain
  shell, and `1.5 L` water capacity per person.
- Permit: no Half Dome day-hike permit.
- Preferences: wants Yosemite Valley, prefers reserved car camping, not strongly
  budget sensitive.

The correct assessment is:

- The group is not suited to attempt Half Dome on this trip.
- Main blockers are no permit, insufficient endurance, missing gloves /
  headlamps / water capacity, limited rain gear, and exposure anxiety.
- `Upper Pines` is the strongest campground fit.
- `Camp 4` can be a budget / backpacker-style fallback, but it is less suitable
  than Upper Pines for a first reserved car-camping trip.

## 5. Checkpoint Rubric

Weights sum to `1.00`. Award partial credit inside each line only for facts that
are present, specific, and compatible with the locked ground truth.

- **0.12 - Required artifacts and screenshot evidence.** Full credit requires
  all five requested files in `/tmp_workspace/results/`, with exact markdown and
  CSV names and two relevant viewable screenshot artifacts corresponding to
  Half Dome and campground NPS pages. Award up to 0.07 for the three text files
  and up to 0.05 for the two screenshots, normally 0.025 per relevant
  screenshot. Zero the screenshot portion for blank, irrelevant,
  header/alert-only, or non-official-page images. Do not award screenshot credit
  just because the filename is `half_dome_reference.png` or
  `campground_reference.png`; the visible pixels must contain relevant page
  content.

- **0.24 - Half Dome factual accuracy.** Award 0.04 each for the correct
  distance, elevation gain, and typical time. Award up to 0.06 for permit logic:
  permit required when cables are up, March lottery, and limited two-days-in-
  advance permits must all be present for full permit credit. Award up to 0.06
  for safety guidance covering wet rock / storms, required preparation gear, and
  unprepared / exposure-sensitive hikers. Do not give this line full credit if
  any core number or permit rule conflicts with the locked ground truth.

- **0.24 - Campground CSV accuracy.** Full credit requires a parseable CSV or
  clearly table-like CSV file with campground name, open season, reservation
  requirement / window, fee note, and notes or equivalent columns. Award 0.08
  for including all four required rows, 0.08 for correct seasons and
  reservation windows, 0.04 for correct Camp 4 fee and reservation / FCFS split,
  and 0.04 for useful notes that distinguish car-camping suitability,
  first-come-first-served risk, and Valley location. Omit credit for unsupported
  live-page drift or invented fees that conflict with hidden facts. Do not
  deduct for Pines fees or exact date ranges when they are visibly supported by
  saved official NPS table/detail-page evidence and remain compatible with the
  hidden season/reservation facts.

- **0.25 - Trip-specific assessment.** Award up to 0.06 for explicitly using
  the trip JSON constraints, including dates, group size / style, fitness,
  exposure anxiety, gear, permits, and camping preferences. Award up to 0.07 for
  a clear conclusion that this trip should not attempt Half Dome. Award up to
  0.06 for explaining the no-go conclusion with the required blockers: no
  permit, 10-12 hour effort versus 5-6 hour comfort, gear gaps, water capacity,
  and exposure anxiety. Award up to 0.04 for recommending `Upper Pines` as the
  best fit and explaining why it beats Camp 4 for this group. Award up to 0.02
  for realistic preparation or alternate-hike advice.

- **0.10 - Official-source grounding and no hallucinated drift.** Credit
  visible evidence that the executor used official NPS pages and the on-disk
  trip JSON: citations, saved snapshots, browser trace, or content that is
  clearly derived from those sources. Zero this line if the answer is mostly
  generic travel advice, relies on non-official sources for core facts, or uses
  live web content to contradict the hidden `2026-04-23` snapshot.

- **0.05 - Safety and feasibility discipline.** Full credit requires advice
  that is legal, feasible, and conservative about Half Dome risk. Zero this line
  for suggestions to hike without a permit, proceed on wet cables, rely on a
  phone light instead of a headlamp, under-carry water for a summer Half Dome
  attempt, ignore exposure anxiety, or treat the daily lottery as guaranteed.

Total: `0.12 + 0.24 + 0.24 + 0.25 + 0.10 + 0.05 = 1.00`.

## 6. Scoring Policy / Score Caps

First compute the rubric score in Section 5. Then apply every relevant cap
below; the final score is `min(rubric_score, all_applicable_caps)`. This task's
public YAML success threshold is `0.90`; a score can pass only if it is `>= 0.90`
after caps.

- **Cap at 0.30 - No usable deliverables.** Fewer than two of the three text
  deliverables exist, or the submitted files are empty / unreadable.

- **Cap at 0.35 - No official-source grounding.** There is no credible evidence
  that the official NPS Half Dome or camping pages were opened or used for core
  facts.

- **Cap at 0.45 - Unsafe or infeasible Half Dome advice.** The assessment tells
  the group to attempt Half Dome on this trip despite no permit, says hiking the
  cables without a permit is acceptable, recommends proceeding in storms / wet
  rock, or otherwise gives advice that would create an obvious safety, legal, or
  feasibility risk.

- **Cap at 0.55 - Wrong permit rules.** The output says no permit is required
  when cables are up, invents a walk-up / campground-based permit path, treats a
  wilderness permit alone as sufficient for day hikers, omits permits entirely
  while recommending Half Dome, or says the two-days-in-advance permit supply is
  guaranteed.

- **Cap at 0.60 - Core Half Dome facts materially wrong.** Two or more of
  distance, elevation gain, time, or safety-critical wet-rock / thunderstorm
  guidance conflict with the locked ground truth.

- **Cap at 0.60 - Campground coverage collapse.** The campground output omits
  two or more of Upper Pines, Lower Pines, North Pines, and Camp 4, or does not
  provide season / reservation information for most listed campground rows.

- **Cap at 0.65 - Missing trip constraints.** The assessment does not appear to
  read the trip JSON, or it ignores three or more decisive constraints among no
  permit, 5-6 hour beginner comfort limit, exposure anxiety, missing gloves,
  insufficient headlamps, insufficient rain shells, insufficient water capacity,
  first car-camping style, and reserved Valley camping preference.

- **Cap at 0.70 - Wrong campground recommendation.** The assessment fails to
  recommend `Upper Pines` as the strongest fit, recommends Camp 4 / Lower Pines /
  North Pines as the primary option without a constraint-based reason, or
  recommends a non-Valley campground despite the explicit Valley and reserved
  car-camping preferences.

- **Cap at 0.75 - Unsupported live webpage drift.** The answer relies on current
  live-page claims that conflict with `references/ground_truth.json` or
  `references/campgrounds_ground_truth.csv`, and the conflict affects a scored
  Half Dome, campground, permit, fee, season, or recommendation fact. Newer
  screenshots or citations do not override the hidden snapshot.

  Do not apply this cap to official NPS table/detail-page facts that refine but
  do not contradict the snapshot, such as visible Pines `$36` fees or exact
  April/October campground dates shown in a saved relevant NPS screenshot.

- **Cap at 0.80 - Superficial trip use.** The output mentions the trip JSON but
  gives a generic Yosemite recommendation and fails to connect the final advice
  to at least four public-source constraints.

- **Cap at 0.84 - Pass-blocking incompleteness.** Any one of these prevents a
  pass even if the rest is strong: missing one required text deliverable; no
  usable screenshot evidence; Half Dome permit process missing either March
  lottery or two-days-in-advance permits; Camp 4 fee missing; or Upper Pines
  recommended without explaining why it fits the trip preferences.

- **Cap at 0.89 - One required screenshot unusable.** If exactly one of the two
  required screenshots is relevant and the other is missing, blank, header-only,
  alert-only, unrelated, or not an official NPS page, the run cannot pass even
  when the text deliverables are otherwise strong. Request a follow-up for the
  missing page-region screenshot.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps).** The executor should stop. The result contains
  all core hidden facts, all key deliverables, a safe no-go Half Dome assessment,
  an Upper Pines recommendation grounded in the trip JSON, and two relevant NPS
  page-region screenshots.

- **Continue (`0.60-0.89` after caps).** A follow-up may be requested when the
  work is substantially grounded and safe but has recoverable gaps, such as one
  weak screenshot, incomplete campground detail, a missing Camp 4 fee, a vague
  Upper Pines rationale, or partial but not dangerous permit detail.

- **Fail (`< 0.60` after caps).** Do not request further follow-up. This
  includes no usable deliverables, no official-source grounding, materially
  wrong Half Dome permit rules, unsafe / illegal advice, or a recommendation
  that encourages this group to attempt Half Dome while ignoring the trip JSON.

When a cap below `0.90` applies, the verdict cannot be `pass` even if artifacts
exist and the prose is polished. Formatting quality, screenshots, or confident
language must not compensate for wrong locked facts, wrong campground choice,
missing trip constraints, or unsafe recommendations.

When giving safe public feedback, preserve concrete, non-hidden repair actions.
For this task, it is safe to ask the executor to:

- Replace any NPS header/alert-only screenshot with a screenshot where the
  Half Dome facts, permit/cables section, campground table, or named campground
  details are visibly present.
- Ensure fee fields only use values visible in saved official NPS evidence, or
  say that the fee was not clearly visible.
- Distinguish Camp 4's reservation season from its off-season first-come,
  first-served period.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - canonical Half Dome, camping, and trip
  recommendation facts.
- `references/campgrounds_ground_truth.csv` - canonical campground row facts.

## 9. Dynamic Content Note

This task intentionally combines live browsing with hidden snapshot grading.
Grade against the snapshot captured on `2026-04-23`. If NPS content changes,
do not infer a new correct answer from the live page; score only the facts that
match the hidden ground truth and apply the unsupported-drift cap when newer
claims contradict the snapshot.
