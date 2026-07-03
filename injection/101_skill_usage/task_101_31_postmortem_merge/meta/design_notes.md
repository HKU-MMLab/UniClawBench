# Design notes — task_101_31_postmortem_merge

Internal-only archive. Not loaded by the supervisor and not visible to the
executor. Captures construction context that was scrubbed from the public
grading spec.

## Skill-usage signal

The task declares four organization/writing skills in `skills/`:

- `runesleo-systematic-debugging`
- `markdown-formatter`
- `memory-manager`
- `daily-digest`

Earlier drafts capped the score at 0.89 when no `SKILL.md` read appeared in
the trace under any declared skill directory. That cap was removed during
revision because (a) it was a checkpoint restatement, not an extreme-
failure cap, and (b) "evidence of skill use" is hard to verify from the
supervisor's vantage and overlaps with the existing structural rubric. If
we want to reintroduce a skill-use signal, prefer wiring it into the
checkpoint rubric instead of the cap section.

## Why the incident-grounding line carries 17%

The original failure mode we were trying to catch: the executor produces
four ultra-generic causes ("communication issues", "lack of automation"),
six matrix rows that cite filenames but never reference actual incident
specifics, and a checklist of platitudes. All structural checks pass, but
the synthesis is useless. The 17% line plus the 0.60 cap on <4/6 grounded
PMs is the deliberate counter to that mode.

## Cap rationale

All §6 caps are at or below 0.60 except the 0.30 floors for credentials,
safety violations, and missing deliverables. The earlier draft used 0.78–
0.89 caps tied to specific structural deficiencies (missing matrix,
missing register, ignoring the 2025 files). Those overlapped with the
checkpoint rubric and were rolled into checkpoints or the broader
"scope blowout" / "generic boilerplate" caps.

## Source mix

Three real public postmortems (Cloudflare 2019/2022, GitLab 2017) plus
three synthetic-but-realistic 2025 incidents. The synthetic three are
designed to give the action register fresh, modern owner roles
(SRE/platform/release-eng) so the deliverable does not feel like a museum
piece.

## v8 hardening round 2 (2026-04-29)

Round 1 of opus-4.6 testing showed this task at capped=1.0 pass — the
section structure plus four root causes plus six matrix rows was easy to
satisfy once incident-specific grounding cleared. Hardening direction:
add an implicit cross-cutting dimension requirement so the executor must
actually deliver director-grade synthesis instead of just a structurally
valid markdown skeleton. Prompt rewritten in natural voice asking what
kinds of root causes keep showing up, where detection keeps falling short
in similar ways, how response/comms tend to break down, what a sensible
prevention coverage story looks like, and which issues are systemic vs
one-off. Eval rule §5 adds a 0.12 "Dimension coverage" anchor checkpoint
requiring ≥4 of 5 dimensions surfaced with concrete substance. To
rebalance to 1.00, section structure cut 0.12→0.08 (-0.04), checklist
domains cut 0.09→0.06 (-0.03), open gaps cut 0.08→0.05 (-0.03), checklist
non-duplication cut 0.08→0.06 (-0.02). Ground truth gains
`topic_dimensions` array and `min_dimensions_covered=4`. Score cap numbers
and success_threshold unchanged.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 still passing at ~1.00 here; the R2
  dim anchor did not move the score because the model surfaces all five
  dimensions easily. Add the same R5 retighten pattern that worked
  elsewhere: a second entity-precision anchor that requires concrete
  filename-plus-anchor pairing.
- New "Postmortem citation precision" line at weight 0.10 demands the
  deliverables explicitly reference at least 4 of 5 specific postmortem
  filenames, each paired with a matching incident anchor in the same
  paragraph/cell/row. The five anchored PMs (taken from the six in
  `pm_files`) are recorded in `pm_citation_set` plus
  `pm_citation_anchors`. The 6th PM (`pm_2025_q3_config_drift.md`) is
  intentionally excluded from this anchor list so the executor must
  show real reading rather than mention every filename.
- Filename-only citations or anchor-only mentions do not satisfy the
  line; both must co-occur.
- Rebalance to keep weights = 1.00:
  Common Root Causes 0.15→0.10 (-0.05) and Incident-specific grounding
  0.17→0.12 (-0.05) jointly fund the new 0.10 line. The grounding
  line's stepped credit is rescaled (6/6→0.12, 5/6→0.08, 4/6→0.05,
  3/6→0.02). New rubric total: 0.08+0.10+0.09+0.09+0.06+0.05+0.06+
  0.13+0.12+0.12+0.10 = 1.00.
- Score caps in §6 unchanged. success_threshold in YAML unchanged.
- GT additions: `pm_citation_set`, `pm_citation_anchors`,
  `min_pm_citations_with_anchor`.

## Review pass (2026-04-30)

User feedback for Task 31 (review_record.md):
1. Supervisor must be able to verify executor output via eval_rule + GT.
2. Design must use bounded space — e.g. Common Root Causes is exactly
   4 specific patterns, and the task requires finding all of them so
   the supervisor can compare executor output against the truth.

### Changes applied

**Task YAML (`task_101_31_postmortem_merge.yaml`)**

- Prompt rewritten in English (was already English; reinforced).
- Skill mention pulled into the first paragraph naming all four
  declared skills (runesleo-systematic-debugging, markdown-formatter,
  memory-manager, daily-digest).
- Bounded-space wording made explicit without naming the count: "every
  cross-cutting pattern that the six PMs actually support, with no
  recurring pattern left out", "every one of the six incidents
  represented in the matrix", "one action that addresses each
  cross-incident root-cause pattern from the synthesis, and one action
  that is specifically motivated by each of the six source incidents".
- Removed parenthetical brackets in narrative; preserved square
  brackets only inside the inline domain tag enumeration.
- Original "at least four real cross-incident patterns" softened to
  "every cross-cutting pattern that the six PMs actually support" so
  the prompt does not enumerate the count but the eval can check the
  full bounded set.

**Ground truth (`ground_truth.json`)**

- New `expected_root_causes` array with the 4 bounded cross-incident
  patterns the six PMs support, each with `required_keyword_groups`
  for supervisor matching and `supporting_pms` plus
  `min_supporting_pms = 3`:
  - `rc_unsafe_rollout` — unsafe rollout / change validation gap.
  - `rc_missing_guardrail` — missing automated guardrail or policy /
    lint check.
  - `rc_observability_blindspot` — observability / dashboard blind
    spot.
  - `rc_unexercised_recovery` — rollback / backup / fallback path
    never exercised.
- New `expected_matrix_incidents` array enumerating all 6 PM filenames
  for the 6/6 strict matrix check.
- New `expected_action_register_entries` block:
  - `by_root_cause` — 4 required actions, each tied to a root-cause
    pattern with matching keyword list for supervisor matching.
  - `by_incident` — 6 required actions, each tied to a specific PM
    filename.
- Tightened `min_dimensions_covered` 4 → 5 (all 5 surfaced) and
  `min_pm_citations_with_anchor` 4 → 5 (all 5 anchored PMs cited)
  to match the bounded-space tightening.
- Retained `cross_incident_cause_anchors` removed in favor of the
  more structured `expected_root_causes` (semantically richer for
  supervisor matching).

**Eval rule (`eval_rule.md`)**

- §1 explicitly states bounded GT and supervisor must verify against
  it.
- §2 declares all-or-nothing requirements: 4/4 root causes, 6/6
  matrix rows, 4/4 action register root-cause coverage, 6/6 action
  register incident coverage, 6/6 incident-specific grounding,
  5/5 dimension coverage, 5/5 PM citation precision.
- §4 documents how the supervisor evaluates each strict line against
  the GT JSON keys.
- §5 rebalanced to 1.00 with strict 4/4, 6/6, 5/5 thresholds:
  - 0.06 sections order
  - 0.14 strict 4/4 root-cause coverage with required keyword groups
  - 0.10 strict 6/6 matrix
  - 0.05 checklist domain tags
  - 0.05 open gaps with ≥2-incident tie-back
  - 0.05 non-duplication / no fabricated filenames
  - 0.07 action register schema + ≥10 rows
  - 0.10 strict 4/4 action register root-cause coverage
  - 0.10 strict 6/6 action register incident coverage
  - 0.13 strict 6/6 incident-specific grounding
  - 0.07 strict 5/5 dimension coverage
  - 0.08 strict 5/5 PM citation precision
  - Sum = 0.06 + 0.14 + 0.10 + 0.05 + 0.05 + 0.05 + 0.07 + 0.10 +
    0.10 + 0.13 + 0.07 + 0.08 = 1.00 (verified).
- §6 caps unchanged (per shared instruction "do not modify existing
  cap numbers").
- §7 success threshold unchanged at ≥0.90.

### Why this satisfies the user feedback

- **Supervisor can verify**: every strict checkpoint resolves to a
  concrete keyword list, filename list, or anchor list in the GT. No
  rubric line says "looks good"; each says "compare to
  `ground_truth.<key>` and count hits".
- **Bounded space**: the answer space for Common Root Causes is
  exactly 4 specific patterns (with required keyword groups), the
  matrix is exactly 6 incidents, the action register requires 4
  cross-incident pattern entries and 6 PM-motivated entries, and
  citation precision is 5/5. The executor cannot pass these lines
  with vague boilerplate; the supervisor simply diffs against the GT.
- **Score cap numbers unchanged**, no new caps added (per shared
  rules), but the existing strict checkpoint structure absorbs the
  tightening so a model that produces only 3 root-cause patterns
  loses 0.14, not just 0.05.
