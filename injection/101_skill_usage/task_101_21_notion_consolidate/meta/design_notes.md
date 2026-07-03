# Design notes — task_101_21_notion_consolidate

Internal-only archive of construction history. Never injected into the
executor or supervisor — supplements but does not duplicate the hidden
eval_rule.

## Snapshot vs live mode

The task supports two execution modes:

- **Snapshot mode** (default offline): canonical eight-page tree lives at
  `sources/notion_snapshot.json`. The supervisor must accept the snapshot
  page-ids `p-001` through `p-008` for cross-linking.
- **Live mode** (when `NOTION_API_TOKEN` is set): the executor calls the
  Notion API. The live page tree may surface either of two ID families
  (`34808720…` for the project-home family, `34f08720…` for the canonical
  sub-page family); both round-trip to the same content. The supervisor
  must accept either family per §3 of the eval_rule.

## Consolidation surface

The hidden ground truth captures must-hit findings as concept-level
booleans with evidence pointers:

- 6 expected decisions (p-002, p-003, p-004 sources)
- 7 expected actions (p-002, p-003, p-007, p-008 sources)
- 5 expected open questions (p-005)
- 6 expected risks (p-001, p-003, p-007, p-008)

The 6 H2 sections (Meetings, Decisions, Action Register, Open Questions,
Risks and Dependencies, References) are required; ordering is required.

## v8 hardening round 3 (2026-04-29)

Round-2 moderate hardening (0.10–0.12 anchors, ≥4-of-5 partial credit)
was insufficient — opus-4.6 still reliably cleared 0.90. This round
applies strict 5/5 all-or-nothing dimension coverage at weight 0.15.

- Public prompt (and `task_snapshot`) rewritten to embed five
  consolidation dimensions as natural-voice clauses (no enumerated
  list): decisions made, action items with owner and due date, open
  questions / unresolved, risks / concerns surfaced, and blocked /
  dependency items. Added an inline "blocked or waiting on a
  dependency" instruction inside the Action Register description.
- §5 rebalanced: Decisions captured 0.20 → 0.15 (-0.05); Actions
  captured 0.20 → 0.15 (-0.05); Document skeleton 0.15 → 0.13 (-0.02);
  Open Questions captured 0.15 → 0.12 (-0.03). Total cut = 0.15, added
  as new "Topic dimension coverage" anchor.
- New anchor scoring: 5/5 → 0.15; 4/5 → 0.05; ≤3/5 → 0.00. Stepped
  cliff: missing one dimension drops 0.10; missing two+ drops the
  full 0.15.
- ground_truth.json gains `topic_dimensions` list and
  `min_dimensions_covered: 5`.
- score caps and success_threshold (0.90) unchanged.
- Final weights: 0.13 + 0.15 + 0.15 + 0.12 + 0.15 + 0.10 + 0.05 +
  0.15 = 1.00.

## Round 8 trim (2026-04-30) — decisions per-entry page_id CP

Task measured at PASS 0.98 — one strict sub-checkpoint added to drop
ceiling to ~0.95. New 0.05 CP "Decisions per-entry source_page_id
strict" requires ≥5 Decisions entries to carry a non-empty
`source_page_id` traceable to `notion_snapshot.json::pages[*].page_id`.
Stepped scoring ≥5 → 0.05, 3-4 → 0.025, ≤2 → 0.00. To rebalance,
Topic dimension coverage trimmed 0.15 → 0.10 (-0.05) with stepped
band proportionally tightened (5/5 → 0.10, 4/5 → 0.03). Final
weights: 0.13 + 0.15 + 0.15 + 0.12 + 0.15 + 0.10 + 0.05 + 0.10 +
0.05 = 1.00. Score caps and success_threshold (0.90) unchanged.

## Review pass (2026-04-30) — cross-document anchors + strict CPs

Three reviewer requirements applied:

**(1) Snapshot mode strictly separated.** §3 of eval_rule rewritten:
snapshot mode auto-detects from any of `SNAPSHOT_MODE=1`, missing
credentials, or harness offline-banner. In snapshot mode the snapshot
is the ONLY canonical input; outbound calls to `api.notion.com` fire
new Cap 0.70 "Live-call attempt in snapshot mode". `task_snapshot`
prompt now explicitly says "Do not attempt a live Notion API call;
the snapshot is the canonical input." Live mode (NOTION_API_TOKEN
present AND no SNAPSHOT_MODE=1) keeps the dual-family page-ID
acceptance from prior rounds.

**(2) GT anchors verifiable from snapshot.** §4 of eval_rule asserts
each must-hit anchor is grounded in concrete `pages[*].blocks[*].text`
in `notion_snapshot.json`. I re-counted the snapshot inventory to
ensure every GT entry has a verbatim or near-verbatim text source —
`expected_decisions` (now 9 with the 3 finalized cross-doc decisions),
`expected_actions` (7), `expected_open_questions` (3, trimmed from 5
because schema-evolution and observability-dashboards moved up to
finalized cross-doc decisions), `expected_risks` (6).

**(3) Cross-document decision anchors added.** Three new
proposed→revised→final trajectories embedded in the snapshot:

- **Schema evolution**: p-002 (lean JSON-Schema, tentative) →
  p-005 (revised: protobuf-favorable benchmark, deferred) →
  p-008 (FINAL: adopt protobuf, supersedes p-002).
- **Dedup window size**: p-001 (10-min proposal) →
  p-004 (15-min draft) → p-007 (FINAL: 20-min for GA,
  supersedes p-001 and p-004).
- **Observability ownership**: p-001 (Erin solo) →
  p-005 (revised: Erin-solo not realistic) →
  p-007 (FINAL: Dave + Erin co-own, supersedes p-001).

Each trajectory requires the executor to read all 3 pages to lock in
the correct final form — reading only one page returns stale
guidance. The snapshot blocks carry inline "(Cross-doc anchor: …)"
hints that name the upstream/downstream page_ids so a careful reader
spots the trajectory.

**§5 rebalanced (all-strict, no `≥X/Y` partial bands except the new
cross-doc one and topic-dim coverage):**

- 0.13 → 0.10 Document skeleton (-0.03; now exact 1 H1 + 6 H2 in order)
- 0.15 → 0.13 Decisions captured (-0.02; STRICT: all 9 of 9, miss any → 0)
- 0.15 → 0.12 Actions captured (-0.03; STRICT: all 7 of 7)
- 0.12 → 0.08 Open Questions captured (-0.04; STRICT: all 3 of 3)
- 0.15 → 0.13 Risks captured (-0.02; STRICT: all 6 of 6)
- 0.10 → 0.08 Meetings deduplicated (-0.02; tightened month-uniqueness)
- 0.05 → 0.05 Rendered output (unchanged)
- 0.10 → 0.07 Topic dimension coverage (-0.03; stepped 5/5→0.07,
  4/5→0.02, ≤3/5→0)
- 0.05 → 0.04 Decisions per-entry source_page_id (-0.01)
- NEW 0.20 Cross-document decision tracking: STRICT all 3 trajectories
  resolved with final form + final source_page_id + explicit
  superseded-page citation. Stepped 3/3→0.20, 2/3→0.10, 1/3→0.04, 0→0.

Sum: 0.10+0.13+0.12+0.08+0.13+0.08+0.05+0.07+0.04+0.20 = **1.00** ✓.

**New score cap.** Cap 0.55 "Stale-decision pollution" fires if the
executor lists a tentative/revised form (10-min window, 15-min
window, "lean JSON-Schema", "Erin owns all dashboards") in the
Decisions section without a superseded annotation — would cause the
new lead to act on stale guidance. Existing caps unchanged.

**Prompt rewrites.** Both `task` and `task_snapshot` rewritten in
ENGLISH per global rule 3a. Skill mention moved to first paragraph
(rule 4): "use one of the workspace's Notion or knowledge-base
consolidation skills — specifically the notion-token-api skill … and
the local-knowledge-consolidator skill". All bracket-style asides
removed (rule 6) and replaced with em-dash or comma asides. New
paragraph between deliverable description and format-list explicitly
warns about cross-document decisions: "some decisions show up in
more than one page — proposed early in one page, revised in a later
one, and finally confirmed in a retro or follow-up page. For those,
only the final form belongs in the Decisions section, and the entry
must explicitly note that the earlier version is superseded".
`task_snapshot` adds the "Do not attempt a live Notion API call"
guard for snapshot-mode separation.

**GT additions.** `expected_decisions` grew 6 → 9 (added the 3
finalized cross-doc decisions on p-007/p-007/p-008).
`expected_open_questions` shrank 5 → 3 (the schema-evolution and
observability open questions are now finalized decisions).
`cross_document_decisions` array added with `proposed → revised →
final` structure, `supersedes` list, and `executor_must_*` boolean
flags. `cross_document_decisions_required: 3` added.

**Snapshot additions.** `notion_snapshot.json` updated with the
three trajectories: p-001 gets two new "Initial proposal" bullets
(observability ownership, dedup window), p-002 gets a "schema
evolution lean JSON-Schema tentative" bullet, p-005 gets revised
versions of the schema-evolution and observability questions
(replacing the open-question forms), p-007 gets a new "Decisions"
heading with the finalized observability-ownership and
dedup-window-20-min entries, p-008 gets a "Decisions" heading with
the finalized protobuf entry. Generated_at unchanged
(2026-04-19T18:00:00Z) — content is what changed.

**Score-cap policy unchanged.** success_threshold stays 0.90.
