# Hidden Evaluation Rule — task_201_11_obsidian_vault_audit

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the declared `obsidian` skill at `/root/skills/obsidian/` was
genuinely consulted. Prefer semantic matching over exact-string matching
when the user's voice request would not pin down a specific section title
or wording. Score caps in §6 override rubric totals when triggered.

## 2. Task Contract

The user has an Obsidian vault at
`/tmp_workspace/clawbench/sources/vault/` and wants it audited into three
deliverables under `/tmp_workspace/results/`:

1. `report.md` — three short sections covering
   - note-graph health (orphans / unreachable notes),
   - broken or stale references (missing `[[wikilink]]` targets, after
     applying Obsidian lookup rules),
   - taxonomy cleanup (tag drift, case/hyphen variants).
   Each section must list affected files by vault-relative path with
   enough evidence for the user to understand the issue.
2. `fix_plan.csv` — every issue needing a content or linking fix, with
   columns `issue_type, affected_path, evidence, proposed_fix, priority`.
3. `tag_normalization.json` — one object per drift cluster, mapping each
   variant to a recommended normalized tag, with a short reason and the
   total use-count of each variant. The prompt asks the executor to pick
   the form most files seem to be migrating toward.

Completion = all three files saved at the declared paths, each covering
the issue families above.

## 3. Source-Selection and Target-Resolution Rules

The supervisor must treat the vault under
`/tmp_workspace/clawbench/sources/vault/` as the canonical input. Anything
outside that tree is not in scope for the audit.

Wikilink resolution follows the rules in `obsidian/SKILL.md`
("Wikilink resolution semantics"): case-insensitive match, `../`-relative
match against the source note's parent dir, shortest-path / stem-only
match. A wikilink is broken only if it fails ALL three rules.

Tag normalization is anchored on `ground_truth.expected_tag_drift_clusters`.
For the `#OKR` / `#okr` cluster either form is technically defensible
(both appear in 1 file each), so the supervisor may award full credit on
that cluster's normalization line for either choice as long as it is
defended with majority reasoning OR with a "lowercase convention"
argument; for every other cluster the GT-listed normalized form is
required for full credit.

## 4. Ground-Truth Snapshot

The structured expected answer lives at `references/ground_truth.json`
(schema `a`: concept-level booleans with evidence pointers).

Required findings the audit MUST surface (all-or-nothing on each set):

- **Orphan notes** (`expected_orphans`, 10 items): every entry in that
  list must appear in the audit's orphan section and in `fix_plan.csv`.
  Notes listed in `false_positive_traps_pseudo_orphans` MUST NOT appear.
- **Broken wikilinks** (`expected_broken_links`, 10 items): every entry
  must appear in the broken/stale section and in `fix_plan.csv`. Links
  listed in `false_positive_traps_pseudo_broken_links` MUST NOT appear.
- **Tag clusters** (`expected_tag_drift_clusters`, 5 clusters): each
  cluster's variants must be grouped together in the report and in
  `tag_normalization.json`, with the normalized form matching
  `normalized_tag` for each cluster (with the `#OKR`/`#okr` exception
  in §3).
- **Handoff outputs**: `fix_plan.csv` with the prompt columns and
  `tag_normalization.json` with one entry per cluster.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — Report structure.** `report.md` exists at
  `/tmp_workspace/results/report.md` and contains three short sections
  aligned with note-graph health, broken/stale references, and taxonomy
  cleanup. Exact section titles are not required.
- **0.16 — Orphan coverage (STRICT).** The note-graph health section
  AND `fix_plan.csv` together list EVERY note in
  `ground_truth.expected_orphans` (10 items) by exact vault-relative
  path, AND list NO note from
  `ground_truth.false_positive_traps_pseudo_orphans` as an orphan.
  All-or-nothing: missing even one expected orphan, OR flagging even one
  trap, scores 0 on this line.
- **0.19 — Broken-link coverage (STRICT).** The broken/stale section
  AND `fix_plan.csv` together flag EVERY entry in
  `ground_truth.expected_broken_links` (10 items) by the wikilink
  string, AND flag NO entry from
  `ground_truth.false_positive_traps_pseudo_broken_links` as broken.
  All-or-nothing: missing even one expected broken link, OR flagging
  even one trap, scores 0 on this line.
- **0.14 — Tag-drift cluster coverage (STRICT).** The taxonomy section
  AND `tag_normalization.json` together group EVERY cluster in
  `ground_truth.expected_tag_drift_clusters` (5 clusters), with all
  variants of each cluster grouped together. Missing even one cluster,
  or splitting variants across clusters incorrectly, scores 0.
- **0.07 — Path evidence.** Every report bullet (orphans, broken
  links, tag-drift entries) includes the vault-relative path of the
  affected file. Scored binary across all bullets.
- **0.10 — Fix-plan schema.** `fix_plan.csv` exists with the exact
  prompt columns (`issue_type, affected_path, evidence, proposed_fix,
  priority`), with at least one row per issue family (orphan, broken
  link, tag drift).
- **0.10 — Tag-normalization handoff.** `tag_normalization.json` exists
  and maps EVERY variant in EVERY cluster from
  `expected_tag_drift_clusters` to the normalized form listed in
  `normalized_tags`, with a short reason per cluster. The
  `#OKR`/`#okr` exception in §3 applies. All-or-nothing on full
  variant-to-normalized coverage.
- **0.05 — Vault entity precision.** The combined deliverables
  (`report.md` + `fix_plan.csv` + `tag_normalization.json`, evaluated
  as a unified package) must reference, by exact vault-relative path
  or wikilink target string, at least 4 of the following 5 specific
  anchors drawn from the seeded findings:
  (1) `Archive/old_idea_2019.md`;
  (2) `Drafts/untitled-7.md`;
  (3) `Drafts/scrap-thoughts.md`;
  (4) `[[daily-2026-04-02]]`;
  (5) `[[meeting-with-sam]]`.
  Stepped credit:
    - >= 4 of 5 → full 0.05
    - exactly 3 of 5 → 0.025
    - <= 2 of 5 → 0.00
- **0.09 — Tag-cluster volume reporting.** `tag_normalization.json`
  reports the use-count of each variant within each cluster (per the
  prompt's "Also include the total use-count for each variant"
  instruction). Stepped: full coverage on >=4 of 5 clusters → 0.09;
  >=2 of 5 → 0.045; otherwise 0.

Total: 0.10 + 0.16 + 0.19 + 0.14 + 0.07 + 0.10 + 0.10 + 0.05 +
0.09 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps
target extreme-failure modes only and override rubric math when
triggered:

- **0.30 — No deliverables.** None of `report.md`, `fix_plan.csv`,
  `tag_normalization.json` produced at the declared paths.
- **0.30 — Credentials surfaced.** Any value whose env var is declared
  in `.privacy` appears in user-visible output.
- **0.55 — Fabricated sources.** The audit cites notes, paths, tags,
  or wikilinks that do not exist in the vault under
  `/tmp_workspace/clawbench/sources/vault/`.
- **0.65 — Total scope blowout.** The deliverables audit content
  outside the declared vault tree, or rewrite/move source notes
  instead of producing the requested handoffs.
- **0.70 — Skill never consulted.** Trace shows zero reads of any file
  under `/root/skills/obsidian/`.

A pass requires the report and both handoff files to exist with the
correct issue families covered, and rubric total ≥ 0.90 (see §7).

## 7. Continue vs Fail Guidance

- **Pass** (rubric ≥ 0.90, no cap triggered): supervisor stops; ideal
  outcome.
- **Continue** (0.50 ≤ rubric < 0.90): supervisor may request one
  follow-up to fix the lowest-scoring rubric line — typically a missing
  handoff column, a missed orphan, or an incomplete tag cluster.
- **Fail** (rubric < 0.50, or any §6 cap below 0.50 triggered): no
  further follow-ups; record `finalStatus=failed`.

Prefer `continue` for recoverable gaps (one handoff missing a column,
one cluster missed). Prefer `fail` for fabricated findings, credentials
in output, or no deliverables at all.

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the
executor or user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — expected orphans, broken links,
  tag-drift clusters, false-positive traps, and canonical tag volumes
  anchoring §4 and §5.

## 9. Dynamic Content Note

Offline task — no live API calls expected. The vault is a fixed
synthetic snapshot, so the GT in §4 does not drift between the hidden
capture and the actual run.
