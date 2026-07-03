# Design notes — task_101_27_pr_triage

Internal-only archive. Not surfaced to executor, user simulator, or judge.

## Skill-evidence policy (archived)

Earlier eval iterations applied a 0.89 cap when the trace showed no read
of `/root/skills/code-analysis-skills/` or `/root/skills/who-is-actor/`.
That cap was removed from the active rubric: skill consultation is
implicit in the task contract (the prompt names both helpers) and
trace-based detection proved unreliable across runs. Outcome-grounded
checkpoints in §5 remain the primary signal; if a future revision wants
to reintroduce skill-trace gating, it should be evidence-anchored
(e.g., the `reviewer_insight` quoting the helper's contributor_label
output) rather than a path-read heuristic.

## confidence field

Public prompt mentions a "confidence score" in `triage.json`. The
supervisor cannot reliably verify a numeric confidence, so no rubric
weight or cap is attached to it. Executors that omit or include it
should not be penalized or rewarded on that basis alone.

## Score-cap rationale

Active caps in §6 are reserved for extreme failure modes (no
deliverables, credentials emitted, fabricated sources, total scope
blowout, safety violation). Earlier per-checkpoint mirror-caps
(0.84 for missing CSV, 0.88 for label miscount, 0.89 for missing skill
read) have been removed; partial credit now flows through rubric
weights instead.

## Round 2 hardening (2026-04-30) — pass→continue conversion
- Currently pass 1.0; add 2 strict anchors.
- Added §5 CPs "Contributor first-PR-date evidence per row" 0.08, "Borderline-case strict-classification" 0.06.
- Added GT fields first_pr_date_required + strict_borderline_cases (pr_5612 → newcomer, no alternates). The 0.06 anchor narrows the lenient `accepted_tenure_equivalents` policy for pr_5612 specifically; the 0.20 reviewer_insight checkpoint still allows the alternate elsewhere.
- Shaved 0.14 total: verdict-rule 0.20→0.15 (-0.05), reviewer_insight 0.25→0.20 (-0.05), triage_evidence.csv 0.15→0.11 (-0.04).
- Final weights: 0.15 + 0.15 + 0.20 + 0.15 + 0.10 + 0.11 + 0.08 + 0.06 = 1.00.
- Target: opus 1.0 → ~0.78 (loses 0.08 if first_pr_date column missing + 0.06 if pr_5612 not strict 'newcomer').

## Round 3 hardening (2026-04-30) — push pass to continue
- After R2 (first-PR-date + borderline strict), score 1.0 → 0.92 (still pass).
- R3 added §5 CP "Per-PR test-coverage assessment" 0.10 (5/6 strict).
- Added GT fields per_pr_required_test_assessment + test_coverage_acceptable_values + per_pr_test_assessment_min.
- Shaved 0.10 from verdict-rule CP (0.15 → 0.05).
- Final weights: 0.15 + 0.05 + 0.20 + 0.15 + 0.10 + 0.11 + 0.08 + 0.06 + 0.10 = 1.00.
- Target: opus 0.92 → ~0.65 (loses 0.10 if test_coverage_assessment field absent in 2+ PRs; opus typically doesn't include this).

## Round 4 hardening (2026-04-30) — third anchor
- After R2+R3 (first-PR-date + borderline strict + test-coverage), score 0.82.
- R4 added §5 CPs "Per-PR review-thread-depth precision" 0.07, "Per-PR time_open_days precision" 0.06.
- Added GT fields required_per_pr_metadata_fields + min_prs_with_metadata.
- Shaved 0.13 from verdict-rule (0.05 → 0.02), reviewer_insight (0.20 → 0.15), triage_evidence.csv (0.11 → 0.06).
- Target: opus 0.82 → ~0.65.

## Round 5 hardening (2026-04-30) — cap for shallow evidence
- After R2+R3+R4, score 0.69.
- §6 added "Cap 0.65 — Shallow evidence per PR" (≥5 of 6 PRs need ≥30-char evidence).
- Added GT fields min_evidence_chars_per_pr + min_prs_with_substantive_evidence.
- Target: opus 0.69 → ~0.55 if evidence rows are shallow.

## Round 6 hardening (2026-04-30) — verdict-rule cap
- R5's evidence cap didn't fire (score stayed 0.69).
- §6 added "Cap 0.55 — Verdict rule drift" (verdicts must match deterministic approvals/change-requests rule).
- Added GT fields deterministic_verdict_rule + verdict_rule_strict_required.
- Target: opus 0.69 → ~0.55 if any verdict deviates from rule.

## Round 7 hardening (2026-04-30) — file-reference cap
- R6 verdict-rule cap didn't fire (score stayed 0.69).
- §6 added "Cap 0.55 — reviewer_insight lacks file/path references" (≥4/6 PRs need file/path in reviewer_insight).
- Added GT field min_reviewer_insights_with_file_reference: 4.
- Target: opus 0.69 → ~0.55.

## Round 8 hardening (2026-04-30) — counts-fields cap
- After R5/R6/R7, score still 0.65 (continue band).
- §6 added "Cap 0.55 — Missing approvals/change-requests counts" (≥5/6 rows must have both approvals_count + change_requests_count integers).
- Added GT fields per_pr_required_count_fields + min_prs_with_count_fields: 5.
- §5 weights unchanged (sum still 1.00). Target: opus 0.65 → ~0.55 if count fields absent.

## Round 9 hardening (2026-04-30) — push to 0.40
- After R5+R6+R7+R8 (multiple caps), score 0.55 (fail).
- §6 added "Cap 0.40 — Missing per-PR tenure tags".
- Added GT fields per_pr_required_tenure_tag + min_prs_with_tenure_tag + acceptable_tenure_labels.
- Target: opus 0.55 → ~0.40.

## Cleanup pass (2026-04-30) — remove hardening_too_strict anchors
- Per FAILURE_ROOT_CAUSE_ANALYSIS.md P1: removed 4 §5 anchors + 4 §6 caps that check for content the prompt does NOT require.
- KEPT R2 borderline-strict (0.06) + R6 verdict-rule cap (prompt explicitly states verdict rule).
- DELETED 4 §5 anchors (first_pr_date, test_coverage, review_thread_depth, time_open_days) totaling 0.31 weight.
- DELETED 4 §6 caps (shallow evidence, file/path refs, approvals/change-requests counts, contributor_tenure tag).
- Restored 0.31 weight to original CPs (verdict-rule, reviewer_insight, triage_evidence.csv).

## Review pass (2026-04-30) — REDESIGN to real Flask GitHub history
Per user feedback (review_record.md task 27): the synthetic 6-PR setup
was replaced with **7 real Flask PRs** sourced from `pallets/flask`
GitHub history. `gh` CLI was unavailable on the host, so PR data was
fetched via WebFetch against `github.com/pallets/flask/pull/<N>` and
`api.github.com/.../pulls`. Verdicts are now anchored to the real
merged-vs-closed outcome at decision time.

### PR roster (7 real, mixed merge/reject)
- pr_5375 — *Added some Changes in README.rst to pull* — **reject** —
  ghost (NONE, prior_merged_prs=0). Closed 2024-01-01 by davidism;
  ThiefMaster declined cosmetic README rewrite.
- pr_5382 — *untag without `object_hook`* — **merge** — davidism
  (MEMBER, prior_merged_prs=380). Self-merged 2024-01-15 into 3.0.x for
  3.0.1.
- pr_5384 — *Update mongoengine.rst* — **reject** — ahmetelgun (NONE,
  prior_merged_prs=0). Closed 2024-02-03; davidism declined redirect to
  third-party fork.
- pr_5389 — *Fix jinja_loader typehint* — **merge** — Siecje
  (CONTRIBUTOR, prior_merged_prs=4). Approved + merged 2024-02-03 for
  3.0.2.
- pr_5393 — *fix super call in list comprehension* — **merge** —
  r04922101 (CONTRIBUTOR, prior_merged_prs=2). Approved + merged
  2024-02-03 for 3.0.2.
- pr_5402 — *Fixed the Readme, app.run()* — **reject** — ByteJoseph
  (NONE, prior_merged_prs=0). Closed 2024-02-03 by davidism — README
  already shows the recommended dev-server pattern.
- pr_5433 — *Fixed broken docstring for jinja_loader in scaffold.py* —
  **reject** — MagnusOxlund (NONE, prior_merged_prs=0). Closed
  2024-03-10; branch carried 42 unrelated upstream commits.

### Sources structure
`/tmp_workspace/clawbench/sources/pr_snapshots/pr_<NNNN>/{meta.json,reviews.json,diff.txt}`
— `base/` and `head/` trees from the prior synthetic build were
removed (they were never actually populated with Flask source for the
real PRs and would have required GBs of repo state). The `diff.txt`
field is sufficient for code-quality assessment of the 7 PRs.

### Prompt (English, skill mention in para 1, no brackets)
First paragraph names both skills (`code-analysis-skills` for
code-review and `who-is-actor` for the contributor label). Verdict
domain reduced to `merge | reject` (no `hold`) so it lines up with
the real GitHub outcome (merged vs. closed-unmerged). Three
deliverables retained: `triage.json`, `triage.md`,
`triage_evidence.csv` (8 columns).

### §5 rubric (sum = 1.00 verified)
- 0.30 verdict matches real GitHub outcome (STRICT 7/7)
- 0.20 contributor label matches GT (STRICT 7/7)
- 0.15 triage.json shape and field completeness (STRICT)
- 0.10 reviewer_insight cites evidence on all 7 (STRICT 7/7)
- 0.10 triage.md grouped by merge/reject (STRICT)
- 0.10 triage_evidence.csv 8 cols + 7 rows (STRICT)
- 0.05 approval_count/change_request_count cells match GT (STRICT 7/7)
Sum: 0.30+0.20+0.15+0.10+0.10+0.10+0.05 = 1.00.

### §6 caps
- Kept extreme-failure caps (no deliverables / credentials / fabricated
  sources / scope blowout / safety violation) at their existing values.
- Verdict-rule cap rewritten: now `Cap 0.55 — verdict disagrees with
  real Flask outcome` (i.e., deterministic `merged_at`-based rule).
- Removed prior synthetic-only caps; no new caps added beyond the
  rewrite of the existing verdict-rule cap.

### GT changes
- `pr_count` 6 → 7, new `pr_ids`, `expected_verdicts`,
  `expected_contributor_labels`, `actual_outcome_evidence` (with real
  GitHub merged_at / closed_at / rejection_reason text),
  `review_signal_counts`, `triage_evidence_columns` (8 cols),
  `triage_md_required_sections` = ["merge", "reject"].
- Removed the synthetic `tenure_by_pr`, `accepted_tenure_equivalents`,
  `strict_borderline_cases` blocks — replaced by the
  `expected_verdicts`/`expected_contributor_labels` real-outcome
  anchors.

### Skill usage
`code-analysis-skills` and `who-is-actor` are both mentioned in the
first paragraph of the prompt. `code-analysis-skills` is the natural
helper for diff/code-quality reasoning; `who-is-actor` consumes
`author_association` + `prior_merged_prs` from `meta.json` to label
the contributor.
