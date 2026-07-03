# Design notes — task_101_11_obsidian_vault_audit

Internal-only archive. Never injected into the executor or supervisor prompt.

## Skill-evidence cap rationale

A skill_usage task with zero evidence of consulting the declared skill at
`/root/skills/obsidian/` cannot reach full score. Earlier framework policy
fixed this cap at 0.89; the current eval rule restates this as a sharper
extreme-failure cap (skill never consulted at all → 0.70).

## Tag-normalization majority signal

For Project Alpha, the vault majority points to `#project/alpha` (2 files
slash form vs. 1 `#Project-Alpha`). The prompt asks the executor to pick the
form most files seem to be migrating toward, so the slash form is the
expected normalized target. An executor that defends `#Project-Alpha` with
explicit majority-counting reasoning may earn partial credit on the
tag-drift line; full credit requires the slash form.

## v8 hardening (2026-04-29 round 1)

Expanded the vault from 20 → 27 notes to add precision pressure on the
audit. New notes:

| New path                              | Real status                                                          |
|---------------------------------------|----------------------------------------------------------------------|
| `Inbox/triage-2026-04.md`             | NOT orphan — referenced from `daily-2026-04-04.md`                    |
| `Inbox/random-thought.md`             | NOT orphan — referenced from `areas/customer-onboarding.md`           |
| `Drafts/launch-spec-draft.md`         | NOT orphan — referenced from `projects/alpha.md`                      |
| `meetings/launch-postmortem.md`       | Has `[[../daily-2026-04-01]]` — RESOLVES (relative path that flatten)|
| `references/standards.md`             | Has `[[Projects/Alpha]]` — RESOLVES (case-insensitive on `projects/alpha`) |
| `Drafts/scrap-thoughts.md`            | TRUE new orphan — nobody links to it; should be reported              |
| `notes/team-kickoff.md`               | New tag drift: contains both `#project/Alpha` and `#project/alpha`    |

Existing notes touched (added one wikilink each):
- `daily-2026-04-04.md` → adds `[[Inbox/triage-2026-04]]`
- `areas/customer-onboarding.md` → adds `[[Inbox/random-thought]]`
- `projects/alpha.md` → adds `[[Drafts/launch-spec-draft]]`

Eval rule changes:
- Added a 0.05 "Expanded-sample coverage" checkpoint anchored on
  `expanded_anchors_v8` in the GT.
- Reduced "Tag-drift grouping" 0.10 → 0.075 and "Path evidence" 0.10 → 0.075
  to free 0.05. Total weights still sum to 1.00.

Note count in YAML and eval_rule restated as ≈27 to match the new vault.

The 3 pseudo-orphans + 2 pseudo-broken-links create false-positive pressure:
a model that doesn't carefully follow wikilinks (and resolve
case-insensitive / relative path forms) will report them as anomalies and
lose the new 0.05 checkpoint, plus risk any precision-related caps.

## v8 hardening round 5 (2026-04-29)

Round-4 measurement showed the existing dimension anchor was insufficient
on its own — opus-class executors hit cap 0.95 by satisfying every
non-anchor checkpoint. This round adds a second §5 anchor "Vault entity
precision" at weight 0.08 that requires the deliverable package to
reference, by exact vault-relative path or wikilink string, ≥4 of 5
specific seeded anchors: `Archive/old_idea_2019.md`, `Drafts/untitled-7.md`,
`Drafts/scrap-thoughts.md`, `[[daily-2026-04-02]]`, `[[meeting-with-sam]]`.
Stepped credit: ≥4/5 → 0.08, exactly 3/5 → 0.04, ≤2/5 → 0.00. To rebalance
to 1.00, the two heaviest existing checkpoints lose 0.04 each:
Fix-plan handoff 0.20 → 0.16 (-0.04) and Orphan coverage 0.15 → 0.11
(-0.04). First anchor (Expanded-sample coverage / dimension-style anchor
inherited from v8 round-1) and all other weights unchanged. Score caps
and success_threshold unchanged. Final weights: 0.15 + 0.11 + 0.15 +
0.075 + 0.075 + 0.16 + 0.15 + 0.05 + 0.08 = 1.00.

## v8 hardening round 8 (2026-04-30) — skill doc + real broken links

Earlier rounds wired two pseudo-broken-link traps into the vault
(`[[Projects/Alpha]]` and `[[../daily-2026-04-01]]`) but the declared
`obsidian` SKILL.md never documented Obsidian's wikilink resolution
rules. Without that documentation a reasonable executor would treat the
case-only / `../`-relative variants as broken links and lose precision
checkpoints. Round 8 closes that gap and adds positive signal in the
opposite direction:

1. **SKILL.md** now has a "Wikilink resolution semantics" section
   spelling out the three vanilla Obsidian rules (case-insensitive,
   relative `../`, shortest-path / stem-only). The executor that reads
   the skill knows the traps are not broken before classifying them.
2. **Two genuinely-broken wikilinks** were added to round-1 vault
   notes (NOT the R0 baseline), each chosen so it cannot resolve under
   any of the three rules:
   - `Inbox/triage-2026-04.md` → `[[truly-missing-followups]]`
     (no note with that stem anywhere in the vault)
   - `notes/team-kickoff.md` → `[[archive/q4-postmortem]]`
     (`Archive/` exists but contains no `q4-postmortem.md`; stem is
     not present anywhere else)
3. **GT** gains an `expanded_real_broken_links` field listing the 2
   new broken links with `in_file`, `wikilink`, `why`. The existing
   `false_positive_traps_pseudo_broken_links` field is preserved so
   the original precision anchor still scores against the traps.
4. **Eval rule §5** gains a 0.05 "Real-broken precision" anchor
   (stepped: 2/2 → 0.05, 1/2 → 0.025, 0 → 0). Weight comes from the
   two heaviest existing checkpoints losing 0.025 each:
   Fix-plan handoff 0.16 → 0.135, Tag-normalization handoff
   0.15 → 0.125. Score caps and success_threshold unchanged.
   Final weights: 0.15 + 0.11 + 0.15 + 0.075 + 0.075 + 0.135 +
   0.125 + 0.05 + 0.08 + 0.05 = 1.00.

## Round 8 trim (2026-04-30) — tag-volume reporting CP

Task measured at PASS 0.98 — one strict sub-checkpoint added to drop
ceiling to ~0.95. New 0.05 CP "Tag-volume reporting precision"
requires the reported total use-count to be within ±1 of canonical
for ≥2 of 3 anchored tags (`#project`, `#meeting`, `#research`).
Stepped scoring 3/3 → 0.05, 2/3 → 0.025, ≤1/3 → 0.00. To rebalance,
Vault entity precision is trimmed 0.08 → 0.03 (-0.05) with stepped
band proportionally tightened (≥4/5 → 0.03, 3/5 → 0.015). Final
weights: 0.15 + 0.11 + 0.15 + 0.075 + 0.075 + 0.135 + 0.125 + 0.05 +
0.05 + 0.03 + 0.05 = 1.00. Score caps and success_threshold
unchanged.

## Review pass (2026-04-30) — vault expansion + strict checkpoints

User feedback (review_record Task 11): (1) drop the specific
"about 27 notes" mention from the prompt, (2) ensure every audit
anchor is checkable against ground truth, (3) consider expanding
the vault for more audit surface.

### Sources changes

Vault expanded from 27 → 52 notes. Net adds:

- **+6 genuine new orphans** (clear cleanup candidates, no inbound
  links anywhere): `Drafts/half-baked-idea.md`,
  `Drafts/q3-recap-draft.md`, `Drafts/personal-todos.md`,
  `Archive/deprecated-process.md`, `Archive/old-vendor-notes.md`,
  `Inbox/unsorted-feedback.md`. Combined with the 3 v8 orphans
  (`Archive/old_idea_2019.md`, `Drafts/untitled-7.md`,
  `Drafts/scrap-thoughts.md`) → 9 expected orphans total.
- **+6 genuine new broken wikilinks** (none resolves under any of
  the three Obsidian rules):
  - `meetings/budget-review.md` → `[[finance/q2-budget]]`
  - `notes/roadmap-draft.md` → `[[milestones/2026-h2-plan]]`
  - `areas/security.md` → `[[runbooks/incident-response-v2]]`
  - `projects/delta.md` → `[[clients/onboarding-tier-3]]`
  - `daily-2026-04-06.md` → `[[follow-ups/sam-april-action-items]]`
  - `meetings/qbr-2026-q1.md` → `[[archive/2025-q4-results]]`
    (Archive/ exists, but no q4-results stem in vault)

  Combined with the 4 existing broken links (`[[daily-2026-04-02]]`,
  `[[meeting-with-sam]]`, `[[truly-missing-followups]]`,
  `[[archive/q4-postmortem]]`) → 10 expected broken links total.
- **+3 new tag-drift clusters** (each has ≥2 variants in distinct
  files):
  - `#follow-up` (2 files) ↔ `#follow_up` (1 file)
  - `#weekly-review` (2 files) ↔ `#weekly_review` (1 file)
  - `#OKR` (1 file) ↔ `#okr` (1 file)

  Combined with the 2 v8 clusters (the `#project/alpha` family
  with 3 case/hyphen variants, and `#note_tag`/`#note-tag`)
  → 5 expected tag-drift clusters total.
- **+10 well-linked benign notes** to anchor the graph and create
  audit noise: `meetings/budget-review.md`,
  `meetings/qbr-2026-q1.md`, `meetings/standup-mon.md`,
  `meetings/standup-wed.md`, `notes/roadmap-draft.md`,
  `notes/research-summary.md`, `notes/dependencies-map.md`,
  `areas/security.md`, `projects/delta.md`,
  `references/api-contract.md`, `runbooks/deploy-checklist.md`,
  `daily-2026-04-06.md`, `daily-2026-04-07.md`,
  `daily-2026-04-08.md`, `people/jordan.md`, `people/morgan.md`,
  `people/taylor.md`, `Index/people-moc.md`,
  `Index/meetings-moc.md`. (Note: `meetings/qbr-2026-q1.md`,
  `meetings/budget-review.md`, `notes/roadmap-draft.md`,
  `daily-2026-04-06.md`, `areas/security.md`, `projects/delta.md`
  also each carry a broken wikilink — they are simultaneously
  benign (well-linked-from-MOC) AND broken-link-source-notes.)
- **MOC.md updated** to link the new daily notes, areas/security,
  projects/delta, notes/roadmap-draft, notes/research-summary,
  references/api-contract, references/decision-log,
  references/glossary, notes/dependencies-map, notes/team-kickoff,
  Index/people-moc, Index/meetings-moc, meetings/launch-postmortem,
  daily-2026-04-03, daily-2026-04-05. This anchors notes that
  would otherwise read as graph-orphans but are not cleanup
  candidates (they are normal per-day or per-reference notes).

All v8 false-positive traps preserved unchanged:
`Inbox/triage-2026-04.md`, `Inbox/random-thought.md`,
`Drafts/launch-spec-draft.md` (pseudo-orphans);
`[[../daily-2026-04-01]]`, `[[Projects/Alpha]]` (pseudo-broken
links).

### Prompt edits

- Removed "about 27 notes" — prompt no longer mentions any
  specific note count.
- Skill mention moved into the FIRST sentence: "audit my Obsidian
  vault ... using the obsidian skill".
- Added explicit per-section requirements that are verifiable:
  "list every orphan", "list every wikilink whose target does not
  resolve", "group each cluster of case- or hyphen-drifted tag
  variants together", and a per-variant use-count requirement in
  `tag_normalization.json`.
- Added "every orphan, every broken wikilink, and every tag-drift
  cluster" coverage requirement on `fix_plan.csv` so all-or-nothing
  scoring lines up with prompt wording.
- No brackets used.

### eval_rule.md edits

- Removed "≈27 notes" mention.
- Replaced the loose "≥2 from seeded set" orphan check with a
  STRICT all-or-nothing check on `expected_orphans` (9 items).
- Replaced the implicit broken-link check with a STRICT
  all-or-nothing check on `expected_broken_links` (10 items).
- Replaced the loose "≥2 case/hyphen variants together" tag-drift
  check with a STRICT all-or-nothing check on
  `expected_tag_drift_clusters` (5 clusters).
- Added §4 explicit lists of expected/forbidden items so the
  supervisor can verify each anchor against GT.
- Added 0.04 "Tag-cluster volume reporting" CP to align with the
  new prompt requirement.
- Removed the v8 "Expanded-sample coverage" CP (precision against
  pseudo-orphans / pseudo-broken-links is now enforced inside the
  STRICT orphan and broken-link CPs, so the v8 CP would
  double-count).
- Removed the v8 "Real-broken precision" CP (now subsumed by the
  STRICT broken-link CP).
- Final §5 weights: 0.10 + 0.16 + 0.19 + 0.14 + 0.07 + 0.10 +
  0.10 + 0.05 + 0.05 + 0.04 = **1.00**.
- Score caps unchanged.

### ground_truth.json edits

- New top-level fields: `expected_orphans`, `expected_broken_links`,
  `expected_tag_drift_clusters` (one structured object per cluster
  with `variants`, `normalized_tag`, `majority_reason`).
- `tag_volume_canonical_counts` added so the supervisor has the
  exact canonical count per anchor tag (`#project=1`, `#meeting=4`,
  `#research=3`).
- `false_positive_traps_*` preserved with their reasoning fields so
  the STRICT precision logic in §5 is auditable.
- `vault_note_count: 52` documented for supervisor reference.
- Old `expanded_anchors_v8` block removed; its content is folded
  into the new structured fields.
- `handoff_outputs.normalized_tags` updated to cover all 11
  variants across 5 clusters.

### Strictness checkpoints (summary)

| CP                                  | Weight | Scoring         |
|-------------------------------------|--------|------------------|
| Report structure                    | 0.10   | binary           |
| Orphan coverage                     | 0.16   | **STRICT all-or-nothing** on 9 expected + 0 traps |
| Broken-link coverage                | 0.19   | **STRICT all-or-nothing** on 10 expected + 0 traps |
| Tag-drift cluster coverage          | 0.14   | **STRICT all-or-nothing** on 5 clusters |
| Path evidence                       | 0.07   | binary           |
| Fix-plan schema                     | 0.10   | binary           |
| Tag-normalization handoff           | 0.10   | all-or-nothing on 11 variants |
| Vault entity precision              | 0.05   | stepped (≥4/5 → 0.05, 3/5 → 0.025) |
| Tag-volume reporting precision      | 0.05   | stepped (3/3 → 0.05, 2/3 → 0.025) |
| Tag-cluster volume reporting        | 0.04   | stepped (≥4/5 → 0.04, ≥2/5 → 0.02) |
| **Total**                           | **1.00** |               |

Caps unchanged. `success_threshold` unchanged at 0.90.

## v1 audit fix (2026-05-01)

- Added `Index/MOC.md` to `expected_orphans` (now 10 items, was 9).
- Reason: empirical grep of the vault confirmed `Index/MOC.md` has zero
  incoming wikilinks. By the strict Obsidian "orphan = no incoming
  links" definition, it qualifies as orphan. Both opus-4.6 and gpt-5.4
  independently flagged it during R2 testing and were incorrectly
  zeroed under §5 0.16 strict all-or-nothing.
- Sibling MOCs `meetings-moc.md` and `people-moc.md` remain non-orphan
  because `MOC.md` itself links to them (1 incoming link each).
- Eval rule §4 + §5 0.16 updated: 9 → 10 items.
