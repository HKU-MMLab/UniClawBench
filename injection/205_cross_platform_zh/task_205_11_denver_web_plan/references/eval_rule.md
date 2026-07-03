# Hidden Evaluation Rule — task_205_11_denver_web_plan

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce web-only evidence, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should judge whether the executor performed a realistic pure-web Denver Saturday web itinerary with cafe stop planning workflow under the user's constraints and produced an auditable Markdown itinerary. Evidence matters because official attraction, ticket, cafe, map, and transit pages can change or block automation; honest documented blocks are better than invented hours, ticket rules, travel times, prices, or availability.

## 2. Task Contract

The public task fixes the city, target weekday/date-selection policy, time window, start point, candidate shortlist, route constraints, and final artifact. Completion means the executor saves /tmp_workspace/results/denver_sat_trip.md, uses only browser/web information, checks the required candidate/source pages, makes a constrained route choice for the selected date, includes route timing and rejection rationale, and clearly marks blocked or missing data rather than hallucinating unavailable details.

## 3. Source-Selection and Target-Resolution Rules

City/target-date/time window: Denver, next Saturday, 13:30-18:30. Start point: Denver Union Station. If next Saturday is a public holiday, closed day, special-hours day, sold out, or not verifiable from official pages, the executor may use the following Saturday with a documented reason.

Candidate shortlist: Denver Art Museum, Denver Botanic Gardens, Museum of Nature & Science, Meow Wolf Denver.

The executor should use Denver attraction official pages, map pages, and a cafe page. The expected planning target is to exactly two attractions plus one cafe/rest stop. It should official pages for each candidate attraction where possible, check opening hours, final admission or ticket/reservation rules where applicable, and avoid attractions whose same-day entry or rules are materially uncertain. Route timing should start at Denver Union Station and fit within 13:30-18:30; single transfer should preferably be no more than 35 minutes. The itinerary must include one cafe rest stop with a cafe page confirming status/location.

The Markdown artifact must include these top-level sections: candidate checks, chosen route, timed itinerary, why others were rejected. It must state the selected date and any skipped-date reason. It should not be merely a link dump or generic sightseeing description; it should contain a practical timed plan and explicit tradeoffs.

## 4. Ground-Truth Snapshot

Hidden references list the fixed city, target weekday/date-selection policy, time window, start point, candidate attractions, route constraints, required final artifact, required sections, and process-reference screenshots currently present under process_evidence/. The screenshot set is from an earlier successful run, illustrative, and incomplete. It does not constrain the dynamically selected target date, attraction choices, opening/ticket values, map durations, cafe status, or final itinerary. Missing hidden screenshots must not by itself penalize an executor who obtains current evidence or honestly documents blocks during execution. Hours, ticket rules, prices, map travel times, cafe hours, transit estimates, and page layouts are volatile and should not be treated as exact fixed expected values.

## 5. Checkpoint Rubric

- 0.25 Candidate official-page checks: satisfies the task-specific constraints using current web evidence or clearly documented blocks.
- 0.20 Map/cafe research: satisfies the task-specific constraints using current web evidence or clearly documented blocks.
- 0.20 Final itinerary feasibility: satisfies the task-specific constraints using current web evidence or clearly documented blocks.
- 0.20 Required Markdown artifact and sections: satisfies the task-specific constraints using current web evidence or clearly documented blocks.
- 0.15 Evidence, honesty, and web-only behavior: satisfies the task-specific constraints using current web evidence or clearly documented blocks.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If live sites block data and the executor clearly documents attempts with screenshots or notes, score the missing exact details through the relevant checkpoints rather than applying an additional cap. Because the hidden process-evidence set is incomplete, do not require the executor to match or reproduce hidden screenshot values.

If it hallucinates unavailable opening hours, admission rules, ticket availability, travel times, cafe status, transit details, holiday/closure status, or prices without evidence, cap at 0.65. If it uses the wrong city, ignores the target-date policy, uses a past or unrelated date without explanation, uses the wrong start point, candidate set, final artifact path, or ignores the web-only requirement across most of the plan, cap at 0.65. If it chooses the wrong number/type of stops or produces an itinerary that clearly cannot fit the required time window, cap at 0.75. If the final Markdown artifact is missing, cap at 0.40. If the final plan is not auditable because source/evidence paths or source references are mostly missing, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer continue when source categories remain unchecked, route timing is missing, screenshots/source notes are missing, or the final plan has not been saved. Prefer fail when the executor finishes with fabricated data, wrong constraints, an infeasible route, missing final artifact, or no auditable evidence.

## 8. Hidden Reference Assets

- ground_truth.json: fixed constraints, candidate list, required output path, required sections, screenshot index, grading notes, and volatility handling.
- process_evidence/*.png: user-provided examples of successful web evidence from an earlier run. This set is not exhaustive and may omit several candidate, cafe, map, or transit pages. It must not be treated as fixing the selected target date or current live-site values.

## 9. Dynamic Content Note

Opening hours, final admission rules, reservation policies, ticket availability, holidays, closures, special-hours days, prices, map durations, transit durations, cafe hours, and page layouts are volatile. Do not require exact hidden screenshot values. Require current evidence or honest documented blocks. A clearly qualified plan with missing-data notes can score well when sites block key data.
