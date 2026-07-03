# Design notes — task_101_23_onboarding_packet

Internal-only history kept out of the executor-visible spec.

## Prior rubric / cap design

Earlier passes of `eval_rule.md` carried the following caps that were
not extreme failure modes and have been retired in favor of fewer,
sharper caps targeting credential leak, no-deliverables, scope blowout,
source-bundle modification, and form-merge collapse:

- 0.65 cap on `forms.xlsx` missing/unopenable — folded into rubric weight
  (form tracker schema + form-row coverage already worth 0.37 combined).
- 0.80 cap on `handoff_plan.md` missing — folded into conflict + dependency
  rubric (0.20 combined).
- 0.82 cap on `onboarding_controls.xlsx` missing/unopenable — folded into
  the 0.17 controls-workbook checkpoint.
- 0.84 cap on signed/blank merge — kept in spirit but tightened to a
  systematic-merge cap (0.65) so single isolated mistakes do not penalize
  beyond rubric weight.
- 0.89 cap requiring evidence of one declared skill read — removed because
  it was a checkpoint restatement; trace-based skill verification now lives
  in §1 grading philosophy and §8 reference asset notes.

## Skill use note

Three declared skills (`pdf-ocr-local`, `office`, `data-analysis`) cover
PDF OCR for photographed forms, Word/Excel handling, and tabular control
sheet construction respectively. Evidence of any one is treated as
sufficient corroboration in the live rubric.

## Workbook contract

`controls_workbook.required_sheets` = ["Conflicts", "Dependency_Order"].
Required columns and minimum row counts live in
`references/ground_truth.json` so the supervisor can adjust thresholds
without rewriting the prose spec.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 capping at 1.00 here — the four
  declared deliverables (checklist, forms.xlsx, handoff_plan.md,
  controls.xlsx) cover all the structural rubric and there is no
  narrative pressure on the manager-facing handoff. Replicate the R5
  retighten pattern (multi-part output + concrete-anchored dimension
  coverage) with a manager-summary lens that forces the executor to
  surface 5 onboarding pillars.
- Public prompt extended naturally: a `summary.md` (or top-of-workbook
  `Summary` sheet) walks through "how the mandatory form sign-offs are
  tracked, what equipment provisioning the new hire needs, what the
  training schedule looks like, what access provisioning has to happen
  and in what order, and how the buddy / mentorship arrangement is
  set up". The five dimensions are not enumerated and the scoring
  keywords are not revealed.
- New §5 anchor "Onboarding dimension coverage" at weight 0.15
  requires concrete coverage of all 5 of 5 dimensions. Each
  dimension's keyword set in `ground_truth.topic_dimension_keywords`
  is consulted; a dimension counts only when keyword mentions are
  paired with a source file, form name, or scheduled item.
- Rebalance to keep weights = 1.00:
  Form-row coverage 0.17→0.09 (-0.08) and Controls workbook 0.17→0.10
  (-0.07) jointly fund the new 0.15 line.
  Final total: 0.13 + 0.08 + 0.12 + 0.09 + 0.08 + 0.13 + 0.07 + 0.10
  + 0.05 + 0.15 = 1.00.
- success_threshold (0.90) and §6 score caps unchanged.
- GT additions: `topic_dimensions`, `topic_dimension_keywords`,
  `min_topic_dimensions_covered`.

## v8 hardening round 9 (2026-04-30) — audit P1 cleanup

Source-bundle leakage cleanup on `manager_followup_notes.txt`. The
prior file was structured as four tightly-aligned bullets that mapped
1-to-1 onto the four §5 rubric anchors (conflicts-surfaced /
form-row-coverage / dependency-order / missing-reference-forms) and
even reused the rubric verbs ("flag anything missing", "keep both
visible", "surface the disagreements", "double-check that nothing in
the IT setup section is scheduled before"). Reading the notes was
effectively reading the rubric.

Rewrite collapses the bullet structure into prose paragraphs in a
hurried-manager voice. Each underlying onboarding signal is preserved
(remote-week reconciliation, missing-form worry, blank+signed
direct-deposit pair stays separate, IT-bootstrap dependency, welcome
guide vs policy disagreements with filenames) but framed as the
manager's own concerns rather than rubric mirrors. No GT / eval_rule /
score-cap / success-threshold change — sources-only edit, executor
still has the necessary deliverable cues without the cheat-sheet
shape.

## Review pass (2026-04-30)

User-specific review_record asks for explicit checkable checkpoints
and verifiable GT references. Audit found the prior eval/GT used soft
"at least N" thresholds without per-item verification, and lacked
explicit per-form-row field requirements / explicit handoff conflict
list.

Changes:

- Task YAML rewritten in English (was already English; refreshed for
  clarity). The skill mention is now in the first paragraph naming
  pdf-ocr-local + office + data-analysis with their specific roles
  (OCR for photographed forms, office for Word/Excel, data-analysis
  for tabular tracking). All parenthetical asides removed in favor of
  natural prose; the eight expected physical form filenames are
  enumerated in the prompt so the per-row contract is unambiguous.
- GT additions:
  - `expected_form_rows` upgraded from `{source,status}` to per-row
    `{source, form_name_keywords, due_date_required,
    signature_required, status, notes_keywords}` for all 8 forms.
  - Renamed `source_conflicts` → `expected_handoff_conflicts` and
    bumped from 6 to 7 explicit topics (added missing emergency
    contact completion). Each topic carries the exact disagreeing
    filenames the handoff must cite.
  - Added `expected_checklist_items` (10 timed items with section,
    phrase keywords, and source files) so the checklist anchor is
    GT-verifiable instead of structural-only.
  - `min_conflicts` 5 → 7 and `min_dependency_items` 7 → 9; the
    workbook `min_conflict_rows` / `min_dependency_rows` updated to
    match.
- Eval rule (§5):
  - All anchors now strict and cite GT keys. "At least N" softness
    removed: checklist anchor demands ≥ 8/10 items (missing >2
    fails), conflicts anchor demands ≥ 6/7 (missing >1 fails),
    dependency anchor demands ≥ 8/9 (missing >1 fails), form rows
    anchor demands all 8 with per-row field checks, status anchor
    demands all 8 status strings exactly. Form tracker schema demands
    exactly 8 rows (was "at least 8").
  - Source coverage anchor now requires every bullet to cite
    filenames matching the GT entry — no bullet may be cite-free.
  - Controls workbook anchor now ties row source_files cells back to
    the 7 expected_handoff_conflicts and 9 dependency_anchors.
  - No-fabrication anchor now triggers loss of the 0.05 weight on any
    citation to a non-existent filename.
- §5 sum verification: 0.13 + 0.08 + 0.12 + 0.09 + 0.08 + 0.13 + 0.07
  + 0.10 + 0.05 + 0.15 = 1.00 ✓
- §6 score caps unchanged. success_threshold (0.90) unchanged.
- All GT values verified against the actual sources/onboard/ contents
  (8 form files exist as listed; welcome.pdf says Acme Corp + 3rd
  floor; it_setup_checklist.txt says 14th floor; benefits.docx
  references a Benefits Election Form not present as a file;
  policies.pdf and welcome.pdf both require security/compliance
  training but no module asset is in the bundle; signed forms all
  dated 2025-04-14 by Alex Morgan).
