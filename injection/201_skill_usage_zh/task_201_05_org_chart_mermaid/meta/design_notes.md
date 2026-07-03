# Design notes — task_101_05_org_chart_mermaid

Internal-only archive of construction history. Never injected.

## Hardening lineage

- Original (v5): 15-line pre-parsed nested-indent tree of the 2009 Obama
  Cabinet. Trivially solvable by passthrough.
- Current source: verbatim Alphabet Inc. DEF 14A 2024 proxy excerpt
  (SEC EDGAR accession 0001308179-24-000612, filed 2024-04-26),
  narrative prose that the executor must parse into nodes,
  board/executive roster edges, committee memberships, and committee
  chairs.
- Reporting-relationship handling: the rubric does not score inferred
  executive-to-CEO reporting edges, because the public source does not
  state them. Only edges explicitly supported by the excerpt count.
- Rendered-validity sub-checks accept any of: classDef styling, inline
  `style` lines, distinct Mermaid node shapes, or explicit role text
  annotations — matching the public prompt's "shape or styling is fine"
  language.
- Anti-hallucination cap targets fabricated person-nodes specifically
  (container labels are exempt), to prevent decorative invented names
  from sneaking past the node-count checkpoint.

## Iteration adjustments captured here (not in eval_rule)

- Raised dotted-edge floor (≥10/11 for full credit, was looser).
- Added explicit chair-discrimination line item separated from styling.
- Reweighted line items to 5 / 12 / 12 / 12 / 8 / 8 / 13 / 13 / 17.
- Skill-usage moved out of per-line item scoring; enforced exclusively
  via score cap (uniform with the rest of the 101_skill_usage suite).

## v8 hardening round 3 (2026-04-29)

Round-2 moderate hardening (0.10–0.12 anchors, ≥4-of-5 partial credit)
was insufficient — opus-4.6 still reliably cleared 0.90. This round
applies strict 5/5 all-or-nothing dimension coverage at weight 0.15.

- Public prompt rewritten to embed five governance dimensions as
  natural-voice clauses (no enumerated list): reporting lines,
  committee membership, dotted-line / advisor relationships, chair
  designations with tenure markers, and vacant / interim /
  recently-filled seats.
- §5 rebalanced: chair-discrimination 0.08 → 0.06 (-0.02);
  subgraph roster 0.13 → 0.10 (-0.03); governance_matrix.csv 0.13 →
  0.10 (-0.03); governance_audit.md 0.17 → 0.10 (-0.07). Total cut
  = 0.15, added as new "Topic dimension coverage" anchor at 0.15.
- New anchor scoring: 5/5 → 0.15; 4/5 → 0.05; ≤3/5 → 0.00. Stepped
  cliff: missing one dimension drops 0.10; missing two+ drops the
  full 0.15.
- ground_truth.json gains `topic_dimensions` list and
  `min_dimensions_covered: 5`.
- score caps and success_threshold unchanged.
- Final weights: 0.05 + 0.12 + 0.12 + 0.12 + 0.06 + 0.08 + 0.10 +
  0.10 + 0.10 + 0.15 = 1.00.

## v8 hardening round 4 (2026-04-29)

Round 3 strict 5/5 dimension anchor still gave the supervisor too much
slack — model passes were sticking around 0.85+ because the existing
abstract dimension list was over-rewarded. Round 4 adds a **second
anchor** ("Entity precision") at weight 0.08 to layer concrete
attribution checks on top of the existing dimension anchor.

Entity-precision anchor: requires the executor to correctly attribute
governance roles to ≥4 of 5 hardcoded figureheads (Pichai, Hennessy,
Page, Brin, Porat). An individual counts iff they appear in `org.mmd`
AND in either `governance_matrix.csv` or `governance_audit.md` with a
role attribution that matches at least one entry in
`expected_individuals[*].expected_role_anchors`. Scoring:
≥4/5 → 0.08, 3/5 → 0.04, ≤2/5 → 0.00.

Note: design brief specified "Mitic" as the 5th figurehead but the
Alphabet 2024 DEF 14A excerpt has no such name; substituted Porat
(CFO Ruth M. Porat) as the closest equivalent — she's the highest-
profile executive officer in the source and naturally appears in
properly-extracted output.

§5 rebalanced: chair-discrimination 0.06 → 0.02 (-0.04); existing
"Topic dimension coverage" 0.15 → 0.11 (-0.04); new "Entity precision"
anchor at +0.08. Final weights:
0.05 + 0.12 + 0.12 + 0.12 + 0.02 + 0.08 + 0.10 + 0.10 + 0.10 + 0.11 + 0.08 = 1.00.

ground_truth.json gains `expected_individuals` (5 surnames + role
anchors each) plus `expected_individuals_min: 4`. score caps and
success_threshold (0.90) unchanged.

## Round 6 hardening (2026-04-30) — pass trim
- Currently pass 1.0; trim by adding committee-chair tenure-in-months CP (0.05).
- Shaved 0.05 from `governance_audit.md` correctness (0.10 → 0.05).
- Target: opus 1.0 → ~0.95-0.97 (still pass; mean drop).
- §5 sum: 0.05 + 0.12 + 0.12 + 0.12 + 0.02 + 0.08 + 0.10 + 0.10 +
  0.05 + 0.11 + 0.08 + 0.05 = 1.00.
- GT additions: `chair_tenure_required_format`,
  `min_chairs_with_tenure_months`.

## Review pass (2026-04-30)

User feedback (review_record.md Task 5):
1. Drop `governance_audit.md` deliverable entirely.
2. Deepen the source markdown — more independent nodes, advisors,
   recently-departed seats, dotted/advisory edges.

Changes applied:

**sources/alphabet_def14a_excerpt.md** — expanded from 14 → 22
person-nodes:
- Directors expanded 10 → 14: added Ann Mather (Audit), Sundeep Reddy
  (Governance), Yolanda Park (Compensation), Diego Salazar (Audit,
  replacing Bourgeois).
- Executive officers expanded 4 → 6 (non-CEO): added Anat Ashkenazi
  (CFO Google Cloud) and Hiroshi Ito (SVP People Ops).
- Recently-departed section added: Alan R. Mulally (retired May 2023),
  Étienne Bourgeois (resigned Jan 2024). Both are explicitly flagged
  as "must not appear as current nodes".
- Board Advisors and Observers section added: Eric E. Schmidt
  (Technical Advisor → Executive Committee), Ann S. Bowers Liang
  (non-voting observer → Audit Committee). Both render as dotted
  advisory edges only — no solid roster edges.

**task YAML (`task` field)**:
- Removed all governance_audit.md / evidence-trail / per-committee
  stat-block / chair-tenure-in-months language.
- Kept org.mmd + org.svg + governance_matrix.csv as deliverables.
- Skill mention naturally embedded in first sentence ("can you use
  one of the diagram skills in the workspace…").
- No brackets in the prompt body; numbers / counts are not enumerated.
- Added explicit guidance: dotted edges cover both committee
  memberships and advisor/observer relationships; recently-departed
  individuals must not appear as current nodes.

**eval_rule.md (§5 fully rewritten)** — 12 strict checkpoints:
- 0.05 files exist + Mermaid header
- 0.13 node count (strict 22/22; 21→0.07; <21→0)
- 0.13 solid roster edges (strict 20/20)
- 0.13 dotted committee edges (strict 15/15)
- 0.05 advisor/observer edges (strict 2/2)
- 0.05 no departed-director hallucination (strict 0 forbidden)
- 0.05 chair discrimination (strict 4/4)
- 0.08 rendered validity (was 0.08 — SVG surname threshold raised
  10/14 → 18/22)
- 0.10 subgraph roster completeness (strict 4/4)
- 0.10 governance_matrix.csv correctness (strict 5 sub-conditions)
- 0.07 topic dimension coverage (strict 5/5)
- 0.06 entity precision (5 figureheads, strict 5/5 → 0.06; 4/5 → 0.03)

§5 sum verification: 0.05 + 0.13 + 0.13 + 0.13 + 0.05 + 0.05 + 0.05 +
0.08 + 0.10 + 0.10 + 0.07 + 0.06 = **1.00** ✓.

Score caps unchanged (0.30 no-deliverables, 0.30 privacy, 0.50
fabricated source, 0.60 skill not consulted). Cap 0.50 fabricated
source now also explicitly catches Mulally/Bourgeois renders.

Strict-anchor philosophy: anchors with stepped credit kept only
where one-off slip is plausible and not catastrophic (e.g. 21/22
nodes still gets some credit; advisor/observer 1/2 partial). The
all-or-nothing strict tier (e.g. no-departed-director, chair 4/4)
applies where the source is unambiguous and a miss reflects
careless extraction.

**ground_truth.json** rewritten:
- nodes_expected list now 22 entries.
- node_count: 22.
- New fields: `current_director_count: 14`,
  `current_executive_officer_count_excl_ceo: 6` (Porat, Raghavan,
  Schindler, Walker, Ashkenazi, Ito), `advisor_observer_count: 2`,
  `must_not_appear: [Mulally, Bourgeois variants]`.
- Removed `governance_audit` block and `chair_tenure_required_format`
  / `min_chairs_with_tenure_months`.
- solid_reporting_edges list now 20 entries.
- dotted_committee_edges_expected list now 15 entries.
- New `advisor_observer_edges_expected` list with 2 entries.
- governance_matrix.solid_rows_expected = 20,
  committee_rows_expected = 15, advisor_observer_rows_expected = 2,
  edge_types now includes "advisor", "observer".

(Solid-edge count audit: 14 director-to-board + 6 non-CEO exec-to-roster
= 20. Pichai is a director, not a non-CEO exec, so he appears once
under the board. Total person-nodes = 14 directors + 6 non-CEO execs +
2 advisors = 22. Cross-checked: nodes_expected list in GT has 22
canonical entries.)

## Compliance fix (2026-04-30)

Tightened five strict-coverage CPs in §5 to true all-or-nothing
scoring. The previous half-credit tiers (21/22→0.07, 19/20→0.07,
14/15→0.07, 1/2→0.02, 3/4→0.02) created off-by-one slack that
contradicts the "strict" labeling and the natural-voice "every"
framing of the public prompt. Per global rule #8 (if the prompt
describes the whole set, eval must hit 100%), all five anchors are
now binary:

- Node count: 22/22 → 0.13; <22/22 → 0.
- Solid roster edges: 20/20 → 0.13; <20/20 → 0.
- Dotted committee edges: 15/15 → 0.13; <15/15 → 0.
- Advisor/observer edges: 2/2 → 0.05; <2/2 → 0.
- Chair discrimination: 4/4 → 0.05; <4/4 → 0.

Weights unchanged. §5 sum verification: 0.05 + 0.13 + 0.13 + 0.13 +
0.05 + 0.05 + 0.05 + 0.08 + 0.10 + 0.10 + 0.07 + 0.06 = **1.00** ✓.
Score caps and success_threshold unchanged.
