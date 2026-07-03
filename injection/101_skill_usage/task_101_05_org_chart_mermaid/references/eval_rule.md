# Hidden Evaluation Rule — task_101_05_org_chart_mermaid

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed:
a Mermaid org chart, a rendered SVG, and a reviewable extraction CSV —
all grounded in the Alphabet Inc. DEF 14A 2024 proxy excerpt provided.
The rubric scores on observable artifact content (nodes, edges,
subgraphs, chair markings, advisor/observer edges, CSV rows). Only
relationships explicitly supported by the source excerpt should be
credited; do not penalize the executor for omitting inferred
executive-to-CEO reporting that the source does not state.

The declared skill (`diagram-local-mermaid`) must be genuinely
consulted; absence of skill-read evidence is handled in §6.

## 2. Task Contract

Public prompt (paraphrased): the user supplies an Alphabet Inc. proxy
statement excerpt at
`/tmp_workspace/clawbench/sources/alphabet_def14a_excerpt.md` and
requests three deliverables:

1. **Mermaid source** at `/tmp_workspace/results/org.mmd` using
   `graph TD` or `flowchart TD`. Solid arrows for board/executive
   roster relationships explicitly supported by the excerpt; dotted
   arrows for committee memberships and for non-voting advisor /
   observer relationships; each committee grouped as a subgraph;
   committee chairs visually distinguished from regular members
   (shape or styling).
2. **Rendered SVG** at `/tmp_workspace/results/org.svg`.
3. **Extraction CSV** at `/tmp_workspace/results/governance_matrix.csv`
   with columns: `person, source_role, governance_group_or_board,
   committee, committee_role, edge_type, source_quote`. One row per
   solid roster edge plus one row per committee membership /
   advisor / observer edge; chairs marked `committee_role=chair`,
   regular members `member`, and advisors/observers flagged via
   `edge_type` ∈ {advisor, observer}.

Each person is a single node even if they hold multiple roles (e.g.
the CEO who also sits on the board). Recently-departed directors
(Alan R. Mulally, Étienne Bourgeois) MUST NOT appear as current
person-nodes in `org.mmd`. Non-voting advisors / observers
(Eric E. Schmidt, Ann S. Bowers Liang) ARE expected to appear and
to be connected via dotted advisory edges only — they have no solid
roster edges.

## 3. Source-Selection and Target-Resolution Rules

The single canonical input is `alphabet_def14a_excerpt.md` under
`/tmp_workspace/clawbench/sources/`. It is a verbatim excerpt of the
Alphabet 2024 DEF 14A (SEC EDGAR accession 0001308179-24-000612, filed
2024-04-26) covering Directors, Executive Officers, Recently-Departed
Directors, Board Advisors and Observers, Board Leadership Structure,
and Board Committees sections.

Endpoint-resolution rules used by the supervisor when comparing
executor output to ground truth:

- **Person endpoints**: matched by surname alias from
  `node_surname_aliases` in `references/ground_truth.json`,
  case-insensitive.
- **Board container**: any node label whose identifier matches
  `/board/i`.
- **Executive-officer container**: any node label whose identifier
  matches both `/executive/i` and `/officer/i`.
- **Committee endpoints**: matched against `committee_memberships
  .<committee>.aliases`.
- **Departed-director check**: any node label whose surname-aliased
  text resolves to "Mulally" or "Bourgeois" (case-insensitive,
  including "Étienne Bourgeois" / "Etienne Bourgeois") flags the
  no-departed-nodes checkpoint.

## 4. Ground-Truth Snapshot

Structured ground truth lives at `references/ground_truth.json`
(schema b: row-level expected values with accepted variants). Key
numbers:

- **22 unique person-nodes** expected: 14 current directors
  (Pichai counted once here as both director and CEO) +
  6 non-CEO executive officers (Porat, Raghavan, Schindler, Walker,
  Ashkenazi, Ito) + 2 non-voting advisors / observers
  (Schmidt, Bowers Liang). Any person-node not in this list is a
  hallucination unless covered by alias.
- **20 solid roster edges**: 14 director-to-board edges +
  6 non-CEO-executive-to-executive-roster edges. Advisors /
  observers do NOT receive solid roster edges.
- **4 standing committees**: Audit and Compliance; Leadership
  Development, Inclusion and Compensation (a.k.a. Compensation);
  Nominating and Corporate Governance (a.k.a. Governance); Executive.
- **15 dotted committee-membership edges** (voting members only).
- **2 advisor / observer edges**: Schmidt → Executive Committee;
  Bowers Liang → Audit and Compliance Committee.
- **4 committee chairs**: Ferguson (Audit), Washington (Compensation),
  Hennessy (Governance), Page (Executive).
- **2 must-not-appear individuals**: Mulally and Bourgeois
  (recently-departed). They are listed in the excerpt for
  audit-trail purposes only; they are NOT current directors.

## 5. Checkpoint Rubric

Twelve weighted checkpoints. Weights sum to 1.00. All anchors are
strict — partial credit is only granted where explicitly listed.

- **0.05 — Files exist and Mermaid header.** Both `org.mmd` and
  `org.svg` exist at the declared paths, and `org.mmd` starts with
  `graph TD` or `flowchart TD` (case-insensitive, leading
  whitespace/comments allowed). Missing either file → 0.

- **0.13 — Node count (strict, all 22).** All 22 expected
  person-nodes (14 directors, 5 non-CEO execs, 2 advisors/observers;
  Pichai counts once) appear as nodes in `org.mmd`,
  surname-level alias-matched (case-insensitive). Strict
  all-or-nothing:
  - 22/22 → 0.13
  - <22/22 → 0.

- **0.13 — Solid roster edges (strict, all 20).** 20 expected,
  syntax `-->` / `---` / `==>`. Endpoint resolution per §3.
  Strict all-or-nothing:
  - 20/20 → 0.13
  - <20/20 → 0.
  Do not require or reward inferred executive-to-CEO edges.
  Advisors / observers (Schmidt, Bowers Liang) MUST NOT appear in
  solid roster edges; if they do, the corresponding edge does not
  count toward the 20 expected.

- **0.13 — Dotted committee-membership edges (strict, all 15).**
  15 voting-member edges expected, syntax `-.->`, `..>`, or
  `-.-`. Set-overlap counted by alias-matched (surname, committee)
  pairs. Strict all-or-nothing:
  - 15/15 → 0.13
  - <15/15 → 0.

- **0.05 — Advisor / observer edges (strict, both 2).** Two
  expected: Schmidt → Executive Committee; Bowers Liang → Audit
  Committee. Both must use dotted/dashed Mermaid edge syntax
  (`-.->`, `..>`, `-.-`). Strict all-or-nothing:
  - 2/2 → 0.05
  - <2/2 → 0.

- **0.05 — No departed-director hallucination (strict).**
  `org.mmd` MUST NOT contain a person-node whose alias resolves to
  "Mulally" or "Bourgeois" (any spelling, including "Étienne
  Bourgeois" / "Etienne Bourgeois"). Strict:
  - 0 forbidden nodes present → 0.05
  - ≥1 forbidden node present → 0.

- **0.05 — Chair discrimination (strict, all 4).** Each of the 4
  committees must name a chair matching `committee_chairs`. Chair
  status is detectable via any of: (a) `classDef`/`:::chair`/
  `class NODE` styling on the chair's node; (b) inline `style NODE …`;
  (c) distinct shape (`[[...]]`, `([...])`, `{{...}}`) versus regular
  members in the same subgraph; (d) explicit text annotation
  (`(Chair)`, `_chair` suffix, etc.). Strict all-or-nothing:
  - 4/4 → 0.05
  - <4/4 → 0.
  Vice-chair is not required.

- **0.08 — Rendered validity.** Four sub-checks:
  - (a) `org.mmd` carries a Mermaid header as standalone, OR is
    embedded in a fenced ` ```mermaid ` block.
  - (b) `subgraph` syntax used for at least the 4 standing
    committees.
  - (c) At least 2 distinct visual treatments are observable to
    distinguish node roles. Accept any of: `classDef` /
    `:::classname` / `class NODE classname;`, inline `style NODE …`,
    distinct Mermaid shapes (`{{...}}`, `([...])`, `[[...]]`,
    `((...))` vs default `[...]`), or explicit role text
    annotations (`(Chair)`, `_chair`, `(Advisor)`, `(Observer)`).
  - (d) `org.svg` is a parseable, non-empty SVG containing an
    `<svg>` root and at least 18 of the 22 expected surnames as
    text content (or equivalent renderer text/title nodes).
  - 4/4 → 0.08; 3/4 → 0.05; 2/4 → 0.02; <2 → 0.

- **0.10 — Subgraph roster completeness (strict, all 4).** Each of
  the 4 standing committees has a `subgraph` block enumerating (or
  referencing via edges) every alias-matched member of that committee.
  Advisors/observers may but need not be inside the committee
  subgraph (a dotted edge crossing the boundary suffices).
  - 4/4 committees fully covered → 0.10
  - 3/4 → 0.05
  - <3 → 0.

- **0.10 — `governance_matrix.csv` correctness (strict).** File
  exists with the required columns and reconciles to the diagram:
  - 20 solid roster rows
  - 15 committee-membership rows
  - 2 advisor / observer rows (edge_type ∈ {advisor, observer})
  - all 4 chairs marked `committee_role=chair`
  - every row carries a short source quote from the excerpt
  Minor column-name variants accepted if content is unambiguous.
  Strict tier:
  - All 5 sub-conditions satisfied → 0.10
  - 4 of 5 satisfied → 0.05
  - ≤3 of 5 → 0.

- **0.07 — Topic dimension coverage (strict 5/5).** The combined
  deliverables (`org.mmd` / `org.svg` / `governance_matrix.csv`,
  evaluated as a unified package) must visibly address all five
  governance dimensions implied by the user's request:
  (1) **reporting lines** — the solid hierarchy from current
  directors to the board container and from non-CEO executives
  to the executive-officer container;
  (2) **committee membership** — the audit / compensation /
  governance / executive rosters as dotted edges or subgraph
  entries;
  (3) **dotted-line / advisor / observer relationships** — the
  Schmidt → Executive and Bowers Liang → Audit advisory edges
  rendered with dotted/dashed Mermaid edge syntax distinct from
  solid roster edges, OR labeled as advisor/observer in the CSV
  edge_type column;
  (4) **chair / head designations** — at least the four
  committee chairs identified visually or in CSV
  `committee_role=chair`;
  (5) **vacant / interim / recently-filled seats** — explicit
  acknowledgment, in either the diagram (e.g. annotation /
  comment) or the CSV (e.g. a row or comment) of the
  recently-filled audit seats (Salazar replacing Bourgeois,
  Ferguson chair effective 2023-10-31, Washington member
  effective 2023-10-31), OR an explicit "no current vacant or
  interim seats" statement that demonstrates the executor
  checked. (Listing Mulally / Bourgeois as departed in CSV
  comments / a row with edge_type=departed counts.)
  - 5/5 dimensions → 0.07
  - 4/5 → 0.03
  - ≤3/5 → 0.

- **0.06 — Entity precision (governance figureheads, strict).**
  The combined deliverables must correctly attribute board /
  chair / CEO / governance roles to the five hardcoded figureheads
  listed in `ground_truth.expected_individuals`:
  `["Pichai", "Hennessy", "Page", "Brin", "Porat"]`. An individual
  counts as **correctly reported** iff they appear by surname (or
  any alias from `node_surname_aliases`) in `org.mmd` AND in
  `governance_matrix.csv` with a role attribution consistent with
  the ground truth (Pichai → CEO / Executive Committee; Hennessy →
  Chair of the Board / Governance chair; Page → Executive
  Committee chair; Brin → director + Executive Committee; Porat →
  executive officer / CFO). Strict scoring:
  - 5/5 → 0.06
  - 4/5 → 0.03
  - ≤3/5 → 0.

Sum: 0.05 + 0.13 + 0.13 + 0.13 + 0.05 + 0.05 + 0.05 + 0.08 + 0.10 + 0.10 + 0.07 + 0.06 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric in §5. The following caps cover
extreme failure modes only — each replaces the rubric total with
`min(rubric_total, cap)` when the listed condition is met. The lowest
applicable cap wins.

- **Cap 0.30 — No deliverables.** None of `org.mmd`, `org.svg`,
  `governance_matrix.csv` exist. The executor effectively did not
  perform the task.
- **Cap 0.30 — Privacy / credential leak.** Any value whose env var
  is declared in `.privacy` appears in user-visible output. Offline
  task, but the policy is preserved for consistency with the suite.
- **Cap 0.50 — Fabricated source content.** `org.mmd` introduces
  any person-node whose label does not alias-match one of the 22
  entries in `permitted_nodes`. (Container/committee labels are
  exempt.) One fabricated person-node is enough to trigger this cap,
  even if the node is visually styled. This targets hallucinated
  governance figures, not minor naming variants. Note: rendering
  Mulally or Bourgeois as a current director ALSO trips this cap
  in addition to the 0.05 no-departed checkpoint penalty.
- **Cap 0.70 — Skill not consulted.** Trace shows zero reads of
  `/root/skills/diagram-local-mermaid/SKILL.md` or any file under
  `/root/skills/diagram-local-mermaid/`. A skill_usage task with no
  evidence the declared skill was opened cannot reach the top band.

No additional proof-of-work artifacts beyond the three deliverables
are required.

## 7. Continue vs Fail Guidance

- **Pass / stop** at total ≥ 0.90. All three deliverables present,
  rubric solidly satisfied; no follow-up needed.
- **Continue** in band 0.50 – 0.89. Supervisor may request one
  follow-up to fix the lowest-scoring rubric line — most commonly
  missing committee members (now larger rosters), advisor/observer
  edges, the no-departed-director check, or CSV row miscount.
- **Fail** below 0.50. Stop the run; record `finalStatus=failed`. No
  further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only — never surface to the executor or user simulator:

- `references/eval_rule.md` (this file) — judging spec.
- `references/ground_truth.json` — canonical surname aliases,
  committee membership lists, expected solid/dotted edge sets,
  committee chairs, advisor/observer edges, must-not-appear
  individuals.

## 9. Dynamic Content Note

Offline task — no live API calls. The source fixture
(`alphabet_def14a_excerpt.md`) is a static verbatim excerpt of a
historical SEC filing and does not change between captures. No
dynamic-content tolerance is needed.
