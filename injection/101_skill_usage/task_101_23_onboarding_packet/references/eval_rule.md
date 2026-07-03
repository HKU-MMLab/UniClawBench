# Hidden Evaluation Rule — task_101_23_onboarding_packet

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the declared skills under `/root/skills/` (see §8) were genuinely
consulted. Prefer semantic matching over exact-string matching when the user's
informal phrasing would not pin a specific key name. All anchors below are
strict and tied to specific values, IDs, or counts in
`ground_truth.json`. Score caps in §6 override rubric totals.

## 2. Task Contract

The user owns a mixed-format new-hire onboarding bundle in
`/tmp_workspace/clawbench/sources/onboard/` and wants four deliverables
written under `/tmp_workspace/results/`:

- `checklist.md` — Markdown checklist grouped by Day 1 / Week 1 / Month 1,
  each item citing the source document it came from.
- `forms.xlsx` — one row per physical form file in the bundle, with name,
  due date, signature requirement, status (TODO / DONE / N_A), and notes.
  Signed copies and blank/photographed counterparts of the same form must
  remain on separate rows; statuses are inferred from the document evidence.
- `handoff_plan.md` — handoff note for the hiring manager listing
  source conflicts or stale items (with the exact disagreeing file names),
  the dependency order for first-day setup work, and forms or references
  mentioned in the packet but absent as physical files.
- `onboarding_controls.xlsx` — workbook with a `Conflicts` sheet
  (`issue`, `source_files`, `impact`, `owner_to_resolve`) and a
  `Dependency_Order` sheet (`action`, `blocked_by`, `due_window`,
  `source_files`).

The public prompt alone is authoritative for what counts as in-scope. The
supervisor must not expand scope based on anything in `references/`.

## 3. Source-Selection and Target-Resolution Rules

Sources live under `/tmp_workspace/clawbench/sources/`. Treat the following
as the canonical input set:

- `onboard/` — 20-file onboarding packet mixing PDFs, Word docs, plain text
  files, signed-form PDFs, and photographed unsigned forms.

When the same form appears as both a blank/photographed template and a signed
PDF, both physical files must be represented. When two source documents
contradict each other (e.g., welcome packet vs. IT checklist), surface the
disagreement rather than silently choosing one side.

## 4. Ground-Truth Snapshot

The structured expected answer lives at `references/ground_truth.json`
(schema `a`: mixed-format onboarding packet with form tracker, source
conflicts, and dependency handoff). The supervisor must load this file for
all thresholds and anchors used by §5.

Key anchors stored there:
- `expected_form_rows` — the 8 physical-form files with required
  per-row fields (form name keyword, due date present, signature
  required, status TODO/DONE, notes keywords). All eight must be
  present and each row must match its specified status exactly.
- `expected_handoff_conflicts` — exactly 7 conflict / missing-reference
  items, each with the disagreeing filenames the handoff must cite.
- `expected_checklist_items` — 10 timed checklist items the
  Day 1 / Week 1 / Month 1 sections must cover, each with phrase
  keywords and source files.
- `dependency_anchors` — 9 first-week dependency phrases the handoff and
  controls workbook must cite (laptop before software, Okta/SSO before
  Slack/Zoom/access requests, repo clone before bootstrap script, I-9
  within 3 business days, security training by end of Week 1, 401(k) by
  end of Month 1, remote-week laptop handoff first, etc.).
- `controls_workbook.required_sheets` / `*_columns` / `min_*_rows` — the
  exact sheet, column, and row-count expectations for
  `onboarding_controls.xlsx`.

## 5. Checkpoint Rubric

Weights sum to 1.00 (0.13 + 0.08 + 0.12 + 0.09 + 0.08 + 0.13 + 0.07 +
0.10 + 0.05 + 0.15).

- **0.13 — Checklist structure and coverage.** `checklist.md` groups items
  under Day 1 / Week 1 / Month 1 headings, every bullet cites at least
  one source filename, AND the sections collectively contain all 10 items
  in `ground_truth.expected_checklist_items` (each item is satisfied when
  a bullet in the correct section contains any keyword from
  `phrase_keywords` and cites a file from the item's `source_files`).
  Missing more than 2 of the 10 items fails this anchor entirely.
- **0.08 — Source coverage.** Every conflict, missing-reference, and
  dependency item in `handoff_plan.md` cites the exact source filename(s)
  listed for that item in `ground_truth.expected_handoff_conflicts.files`
  or `ground_truth.dependency_anchors`. No bullet may be cite-free.
- **0.12 — Form tracker schema.** `forms.xlsx` exposes the columns
  form name, due date, signature requirement, status, notes (case- and
  spacing-insensitive header match) AND contains exactly
  `ground_truth.min_forms_rows` (= 8) physical-form rows — no more, no
  fewer. Extra synthetic / phantom rows fail this anchor.
- **0.09 — Form-row coverage.** Every entry in
  `ground_truth.expected_form_rows` has a row whose source reference,
  form-name cell, or note maps back to the exact source filename. For
  each of the 8 rows: form_name_keywords match the name cell,
  signature_required is "Yes", and at least one notes_keyword appears
  in the notes cell. The due_date cell must be non-empty ONLY for rows
  with `due_date_required: true` (the two I-9 rows, since policies.pdf
  states "within 3 business days of start"); for rows with
  `due_date_required: false` (the other 6 forms — W-4, Direct Deposit,
  Emergency Contact, NDA, both blank/photo templates and signed
  counterparts) the due_date cell may be empty, "N/A", "Not stated in
  bundle", or any plausible placeholder. All eight must satisfy these
  per-row checks.
- **0.08 — Status inference.** Each of the 8 expected_form_rows has the
  exact status string in `ground_truth.expected_form_rows[*].status`
  (TODO for blank/photographed, DONE for signed). No row may be merged
  with another. A single mismatched status fails this anchor.
- **0.13 — Conflicts surfaced.** `handoff_plan.md` identifies all 7
  topics in `ground_truth.expected_handoff_conflicts`. For each topic,
  the document must (a) describe the conflict / missing item in language
  that matches the topic semantics, and (b) cite every filename listed
  in `expected_handoff_conflicts[*].files` for that topic. Missing more
  than 1 of the 7 topics fails this anchor.
- **0.07 — Dependency order.** `handoff_plan.md` includes all 9
  dependency / order phrases in `ground_truth.dependency_anchors`
  (semantic match acceptable). Missing more than 1 of the 9 fails this
  anchor.
- **0.10 — Controls workbook.** `onboarding_controls.xlsx` opens as a
  workbook, contains exactly the two sheets in
  `controls_workbook.required_sheets`, exposes the requested columns on
  each sheet, has at least `min_conflict_rows` (= 7) rows on Conflicts
  AND at least `min_dependency_rows` (= 9) rows on Dependency_Order.
  Each Conflicts row's `source_files` cell must cite filenames matching
  one of the 7 expected_handoff_conflicts entries; each Dependency_Order
  row's `action` must semantically map to one of the 9 dependency_anchors.
- **0.05 — No fabrication.** No phantom forms, invented policy
  requirements, or sources not actually present in `onboard/`. Any
  citation to a filename that does not exist in `onboard/` triggers loss
  of this anchor.
- **0.15 — Onboarding dimension coverage.** A short narrative
  `summary.md` (or a `Summary` sheet at the top of `forms.xlsx`) must
  surface concrete observations across all 5 of
  `ground_truth.min_topic_dimensions_covered` (= 5) hidden dimensions in
  `ground_truth.topic_dimensions`. Each dimension's keyword set in
  `ground_truth.topic_dimension_keywords` is consulted: a dimension
  counts as covered when the narrative uses any keyword from its set
  AND grounds the mention in a concrete source file, form name, or
  scheduled item from the packet.

  The five dimensions and their keyword sets (case-insensitive):
  - `mandatory_forms` — keywords `["I-9", "W-4", "NDA", "code of
    conduct"]`. Mentioning at least 2 of the form types paired with
    a specific source file or signed/blank status satisfies this
    dimension.
  - `equipment_requests` — keywords `["laptop", "monitor",
    "headset", "badge"]`. Naming at least 2 equipment items from
    the IT / facilities flow.
  - `training_schedule` — keywords `["onboarding", "compliance",
    "tools", "kickoff"]`. Discussing the training arc with at
    least one keyword and a Day 1 / Week 1 / Month 1 anchor.
  - `access_provisioning` — keywords `["VPN", "okta", "github",
    "slack", "email"]`. Naming at least 2 access systems with a
    dependency or order note.
  - `buddy_mentorship` — keywords `["buddy", "mentor", "shadow",
    "peer"]`. Calling out the buddy/mentor arrangement explicitly,
    citing the source file (manager notes / welcome guide) that
    references it.

  Tiers: 5/5 → 0.15; exactly 4/5 → 0.05; ≤ 3/5 → 0.00. A bare
  bullet list with no concrete grounding does not satisfy any
  dimension.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoint weights in §5. The caps below
exist for special, extreme failure modes — not as restatements of the
rubric — and a triggered cap overrides any rubric total.

- **Cap 0.30 — No deliverables.** None of the four files in §2 are
  produced under `/tmp_workspace/results/`.
- **Cap 0.30 — Credentials emitted.** Any value whose env var is
  declared in `.privacy` appears in user-visible output.
- **Cap 0.50 — Total scope blowout.** The deliverables summarize material
  not present in `onboard/` (e.g., invented policies, fabricated form
  files, hallucinated company facts) such that more than half of the
  checklist or form rows have no source-file backing.
- **Cap 0.60 — Safety / packet integrity violation.** The executor edits,
  re-signs, or otherwise modifies the source bundle, or surfaces the
  contents of `references/` to the user.
- **Cap 0.65 — Form/blank merge collapse.** The executor systematically
  merges signed and blank counterparts of the same form into single rows,
  destroying the per-file row contract.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/pdf-ocr-local/` OR `/root/skills/office/` OR
  `/root/skills/data-analysis/` belonging to the declared skill(s). A
  skill-usage task with zero evidence of consulting the declared
  skill(s) cannot reach a full score.

Pass = all critical checkpoints satisfied (form-row coverage, conflicts,
controls workbook) and total ≥ 0.90 with no cap triggered.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop. Ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to fix
  the lowest-scoring rubric line, especially when only one of the four
  deliverables is missing or one workbook fails to open.
- **Fail** < 0.50 — record `finalStatus=failed`; do not request more
  follow-ups.

Prefer `continue` when the executor produced most deliverables but missed
a row count, sheet column, or one conflict citation. Prefer `fail` when no
results files exist, when sources were modified, or when any cap in §6
fires.

## 8. Hidden Reference Assets

Supervisor-only — must not be surfaced to the executor or user simulator:
- `references/eval_rule.md` (this file) — the grading spec.
- `references/ground_truth.json` — the structured answer key, including
  `expected_form_rows`, `expected_handoff_conflicts`,
  `expected_checklist_items`, `dependency_anchors`, and the
  `controls_workbook` sheet/column/row contract.

Declared skills the executor is expected to consult (under
`/root/skills/`): `pdf-ocr-local`, `office`, `data-analysis`. Evidence
that the trace touched any one of the three is sufficient corroboration
of skill use; the executor is not required to read all three.

## 9. Dynamic Content Note

Offline task — no live API calls expected. All sources are static files in
`onboard/`, and ground-truth values are fixed at capture time. There are
no dynamic values the supervisor needs to reconcile.
