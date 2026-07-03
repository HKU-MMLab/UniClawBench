# Hidden Evaluation Rule — task_101_21_notion_consolidate

## 1. Grading Philosophy

Grade on whether the public request was actually completed: a faithful
consolidation of the eight project sub-pages into the three required
deliverables, with source page_ids preserved so the user can cross-link back
to Notion. Reward semantic correctness over verbatim string matches when the
user prompt does not pin down exact phrasing. The Notion / knowledge-base
skills in `/root/skills/` (`notion-token-api`, `local-knowledge-consolidator`)
should be genuinely consulted, not merely listed. Score caps in §6 override
rubric totals.

## 2. Task Contract

The user owns a Notion project-home with eight sub-pages. The executor must
read the page tree (live API in connected mode, or
`/tmp_workspace/clawbench/sources/notion_snapshot.json` in snapshot mode) and
emit:

- `/tmp_workspace/results/consolidated.md` — one document with H1 project
  title and H2 sections in this order: Meetings, Decisions, Action Register,
  Open Questions, Risks and Dependencies, References.
- `/tmp_workspace/results/decision_log.csv` — columns
  `date,topic,decision,status,source_page_id,source_excerpt`.
- `/tmp_workspace/results/action_register.csv` — columns
  `owner,action,due_date,status_or_blocker,source_page_id`.

Every section and tracker file must preserve `source_page_id` for each row /
bullet. Empty `due_date` is acceptable only when the source does not state
one. The prompt alone defines scope.

## 3. Source-Selection and Target-Resolution Rules

Canonical input lives under `/tmp_workspace/clawbench/sources/`:

- `notion_snapshot.json` — canonical offline snapshot of the eight pages.

**Snapshot mode is strict and auto-detected.** Snapshot mode is active when
ANY of the following holds:

1. `SNAPSHOT_MODE=1` is exported in the executor's environment, OR
2. No Notion credentials are present (`NOTION_API_TOKEN` unset / empty), OR
3. The executor's harness banner declares the run as offline / snapshot.

In snapshot mode the snapshot file is the **only** canonical input. The
executor must not be penalized for skipping a live API call, and must not
inject content that does not appear in the snapshot. Conversely, when
snapshot mode is NOT active and live credentials are present, the executor
is expected to call the live API; reading the snapshot in live mode does
not by itself fail the task but must still ground every claim in the live
page tree (the snapshot and the live tree are kept in sync by the
populator).

**Page-id format flexibility (live mode only):** the live Notion API may
surface either of two ID families for the same page tree the executor was
directed to (`34808720…` for the project-home family, `34f08720…` for the
canonical sub-page family). Both round-trip to the same page content.
Accept any of:

1. The canonical snapshot ID (`p-001` through `p-008`), OR
2. Any 32-hex-char Notion ID whose first 8 hex chars are `34808720` or
   `34f08720`, OR
3. The dashed UUID equivalents of (2).

Reject only IDs that don't trace back to one of the eight project pages
(random hex, unrelated workspace IDs). Establish equivalence by matching
page title or content snippets to entries in the snapshot. In snapshot
mode the only valid `source_page_id` values are `p-001` … `p-008`.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json` (schema
`a` — concept-level booleans with evidence pointers). The supervisor MUST
load both `ground_truth.json` and `notion_snapshot.json` to verify values
against the executor's output. Every anchor in §5 is grounded in concrete
text in the snapshot — the supervisor can match each must-hit by searching
`notion_snapshot.json::pages[*].blocks[*].text`.

Key anchors:

- `expected_sections` — the six required H2 section names, in order.
- `decision_log_columns` / `action_register_columns` — required CSV headers.
- `expected_decisions` (9 entries), `expected_actions` (7 entries),
  `expected_open_questions` (3 entries), `expected_risks` (6 entries) —
  must-hit findings keyed to `p-001` … `p-008`.
- `cross_document_decisions` (3 entries) — proposed → revised → final
  trajectories keyed to specific page_ids.

## 5. Checkpoint Rubric

Weights sum to 1.00. All checkpoints are STRICT (full-count, all-or-nothing
on the must-hit anchors, no partial-credit "≥ X of Y" bands except where
explicitly stepped below).

- **0.10 — Document skeleton.** `consolidated.md` has exactly one H1
  (the project title) and exactly six H2 headings, matching
  `expected_sections` byte-for-byte (case-insensitive whitespace-trim) and
  appearing in the listed order. Missing one H2, an extra H2, or wrong
  ordering → 0.

- **0.13 — Decisions captured (strict).** Decisions section in
  `consolidated.md` AND `decision_log.csv` use exactly the columns in
  `decision_log_columns` and contain a row for **all 9** entries in
  `expected_decisions` (semantic match: matching `topic` plus a decision
  text that semantically conveys the GT decision). Each row carries a
  valid `source_page_id` from the snapshot. Missing any of the 9 → 0.

- **0.12 — Actions captured (strict).** Action Register section AND
  `action_register.csv` use exactly the columns in
  `action_register_columns` and contain a row for **all 7** entries in
  `expected_actions`. Each row preserves owner, preserves stated due
  date where present (empty string when GT due_date is `""`), and a
  valid `source_page_id`. Missing any of the 7 → 0.

- **0.08 — Open Questions captured (strict).** Open Questions H2 lists
  **all 3** entries in `expected_open_questions`, each with owner /
  pending-owner or next-step detail and a valid `source_page_id`.
  Missing any of the 3 → 0.

- **0.13 — Risks captured (strict).** Risks and Dependencies H2 lists
  **all 6** entries in `expected_risks`, each with evidence,
  mitigation or next action, owner / responsible role where inferable,
  and a valid `source_page_id`. Missing any of the 6 → 0.

- **0.08 — Meetings deduplicated.** Meetings section grouped by month;
  no two bullets share an identical leading phrase of ≥40 chars
  verbatim, and each calendar month present in the snapshot
  (Feb / Mar / Apr 2026) appears exactly once as a heading or bullet
  group label.

- **0.05 — Rendered output.** Outputs are rendered Markdown / CSV, not
  raw Notion block JSON (no `{` tokens followed by `"type":"paragraph"`
  etc., no raw JSON arrays in the body of `consolidated.md`).

- **0.07 — Topic dimension coverage.** The combined deliverables
  (`consolidated.md` + `decision_log.csv` + `action_register.csv`,
  evaluated as a unified package) must visibly address all five
  consolidation dimensions implied by the user's request: (1)
  **Decisions made** — at least 9 distinct decisions captured (the
  full `expected_decisions` set) with decision text, status field, and
  source_page_id; (2) **Action items with owner and due date** — all 7
  actions with owner field AND `due_date` populated per source (empty
  string when source doesn't state); (3) **Open questions /
  unresolved** — Open Questions H2 contains all 3 questions each with
  owner-or-next-step detail and source_page_id; (4) **Risks /
  concerns surfaced** — Risks and Dependencies H2 captures all 6
  risks each with evidence and mitigation; (5) **Blocked / dependency
  items** — at least one row in `action_register.csv` AND/OR Risks and
  Dependencies H2 explicitly flags a blocked or dependency item (any
  of: a `status_or_blocker` value containing "blocked", "waiting",
  "depends on", "dependency"; a Risks bullet/row whose evidence or
  risk text identifies a dependency or blocker; or an explicit "no
  blocked items" disclaimer that demonstrates the executor checked).
  - 5 of 5 dimensions clearly addressed → full 0.07.
  - exactly 4 of 5 → 0.02.
  - ≤ 3 of 5 → 0.00.

- **0.04 — Decisions per-entry source_page_id strict.** Every entry in
  the Decisions section and `decision_log.csv` has a non-empty
  `source_page_id` referencing `notion_snapshot.json::pages[*].page_id`.
  At least `ground_truth.decisions_min_count` (= 5) entries must carry
  valid page IDs. Stepped:
  - all decision rows have valid page_id → 0.04
  - 1-2 missing → 0.02
  - ≥3 missing → 0.00.

- **0.20 — Cross-document decision tracking (strict).** The executor
  must correctly resolve **all 3** cross-document decisions in
  `ground_truth.cross_document_decisions`:

  1. **Schema evolution** — proposed in p-002 (lean JSON-Schema,
     tentative), revised in p-005 (open question, benchmark favors
     protobuf), finalized in p-008 (adopt protobuf).
  2. **Dedup window size** — proposed in p-001 (10 min), revised in
     p-004 (15 min draft), finalized in p-007 (20 min for GA).
  3. **Observability ownership** — proposed in p-001 (Erin solo),
     revised in p-005 (Erin-solo not realistic), finalized in p-007
     (Dave and Erin co-own).

  For each cross-doc decision, the Decisions section must:
  - report the FINAL form only (the binding decision from the
    `final.source_page_id` page), not the proposed or revised form;
  - cite the FINAL `source_page_id` (p-008, p-007, p-007 respectively)
    in the Decisions row's `source_page_id` column;
  - explicitly note in the decision text or a cross-link annotation
    that the earlier-page version(s) listed in `supersedes` are
    superseded / obsolete (any of: "supersedes p-002", "obsoletes
    p-001", "earlier p-004 draft no longer applies", "replaces the
    p-002 tentative", or equivalent phrasing that names the
    superseded page_id explicitly).

  Tentative or revised forms (e.g. "lean toward JSON-Schema" from
  p-002, "10-minute LRU window" from p-001, "Erin owns all dashboards"
  from p-001) MUST NOT appear as standalone entries in the Decisions
  section — those are stale guidance the new lead must not act on.
  Including them as separate Decisions rows without a "superseded"
  annotation is a hard miss for that cross-doc decision.

  Stepped scoring:
  - all 3 cross-doc decisions correctly resolved with final form,
    final source_page_id, and explicit superseded annotation → 0.20.
  - exactly 2 of 3 correct → 0.10.
  - exactly 1 of 3 correct → 0.04.
  - 0 of 3 correct → 0.00.

  A cross-doc decision counts as "correct" only if all three
  sub-conditions hold: final form, final source_page_id, and at least
  one superseded-page citation matching `supersedes`.

Total: `0.10 + 0.13 + 0.12 + 0.08 + 0.13 + 0.08 + 0.05 + 0.07 + 0.04 + 0.20 = 1.00`.

## 6. Scoring Policy / Score Caps

Partial credit accrues from satisfied checkpoints. The following caps fire
only on extreme-failure modes and override the rubric total:

- **Cap 0.30 — No deliverables produced.** None of the three required
  output files in §2 exist or all are unreadable.
- **Cap 0.30 — Credential leakage.** Any value whose env var is declared
  in `configs/.privacy` appears in user-visible output.
- **Cap 0.30 — Fabricated sources.** Tracker rows or section bullets cite
  `source_page_id` values that don't trace back to any of the eight project
  pages, or quote `source_excerpt` text not present in the snapshot.
- **Cap 0.55 — Total scope blowout.** The output ignores the eight-page
  project tree entirely (e.g. summarizes unrelated content, dumps full raw
  Notion JSON without consolidation, or fewer than 2 of `expected_sections`
  appear as H2).
- **Cap 0.55 — Stale-decision pollution.** The Decisions section lists
  any of the cross-document tentative/revised forms (10-min dedup window,
  15-min dedup window, "lean JSON-Schema", "Erin owns all dashboards
  alone") as a current decision without a "superseded" annotation
  pointing to the final-form page. This is a correctness failure: the
  new lead would act on stale guidance.
- **Cap 0.70 — Skill consultation absent.** Trace shows no read of any
  file under any subdirectory of `/root/skills/` whose folder name appears
  in this task's declared `skills:` list. Reading any one declared skill
  (regardless of specific file path within it) is sufficient to clear
  this cap; the cap targets the case where the executor produced output
  with no evidence of consulting the workspace skill kit at all.
- **Cap 0.70 — Live-call attempt in snapshot mode.** Snapshot mode is
  active per §3 and the trace shows an outbound HTTP call to
  `*.notion.com` / `api.notion.com` (or the executor injects content not
  present in `notion_snapshot.json`). Reading the snapshot is the only
  permitted source path in snapshot mode.

Pass requires all three deliverable files present, the §5 rubric ≥ 0.90,
and no cap fired.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — supervisor stops; ideal outcome.
- **Continue** 0.50 – 0.89 — recoverable gaps (e.g. one tracker missing
  rows, one section under-populated, header column typo, one cross-doc
  decision misattributed). Supervisor may request one follow-up
  targeting the lowest-scoring rubric line.
- **Fail** < 0.50 — unrecoverable (no deliverables, fabricated sources,
  credential leak, total scope blowout, stale-decision pollution).
  Record `finalStatus=failed` with no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only; never surface to the executor or user simulator:

- `references/eval_rule.md` (this file) — the grading spec.
- `references/ground_truth.json` — schema-`a` expected concepts and
  evidence pointers anchoring §5, including `cross_document_decisions`.
- `sources/notion_snapshot.json` — canonical eight-page tree used to
  validate `source_page_id` and `source_excerpt` claims, and to verify
  every cross-document decision trajectory.

## 9. Dynamic Content Note

Auth task. If `configs/privacy.local.env` populates `NOTION_API_TOKEN` AND
`SNAPSHOT_MODE` is not set to 1, the executor may call the live Notion
API; otherwise the snapshot is canonical and a live call will fire the
0.70 cap in §6. Live mode may surface page IDs in either of the two
families documented in §3 — accept both. The cross-document decision
trajectories are the same in either mode (the populator keeps the live
tree and the snapshot in sync).
