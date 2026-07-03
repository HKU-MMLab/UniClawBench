# Design notes — task_101_09_git_digest

Archive of construction-time notes that must NOT appear in the
supervisor-visible `references/eval_rule.md`.

## Skill-usage policy lineage

Earlier iterations applied a soft cap on the total score when the trace
showed zero evidence that the executor opened any file under the declared
skill directories (`/root/skills/git-essentials/`,
`/root/skills/markdown-formatter/`). The intent was to discourage running
purely from prior knowledge in a category whose stated purpose is skill
consultation. The current eval_rule preserves this intent through the
extreme-failure cap in §6 (no read of declared skills at all), framed as
an outcome-grounded edge case rather than a soft penalty band.

## Rubric anchoring

All bullet/SHA/contributor thresholds are sourced from
`references/ground_truth.json`. The judge must extract the tarball and
recompute the 90-day window from the latest commit's author-date — do
NOT rely on remembered Flask history, since the tarball pins a specific
commit and the window slides with it.

## v8 hardening (2026-04-29 round 1)

Currently this task fully passed (capped 1.0) on opus-4.6, so we tighten
it by adding implicit multi-part requirements without touching score
caps or the ground-truth count primitives.

- Public prompt rewritten to a more conversational team-newsletter
  voice that *implicitly* asks for 5 dimensions — shipped features,
  bug fixes, deprecations/removals, performance changes, contributor
  activity — woven into a paragraph rather than enumerated as 1/2/3/4/5.
  This avoids spoon-feeding the rubric while still letting the
  supervisor verify the executor naturally addresses the dimensions.
- New checkpoint added in §5 ("Topic dimension coverage", weight 0.10)
  that scores against the implicit dimensions. Weight reclaimed by
  trimming §5 bullet #1 (existence/5-bullets) 0.20 → 0.13 and
  §5 bullet #4 (theme distinctness) 0.20 → 0.17. New rubric still
  sums to 1.00 (0.13 + 0.20 + 0.20 + 0.17 + 0.10 + 0.10 + 0.10).
- `ground_truth.json` extended with `topic_dimensions[]` and
  `min_dimensions_covered = 4`. No existing numeric thresholds
  (bullet_count, sha_prefix_len, window_days, contributor counts,
  substantive_commits[]) were modified.
- §6 score caps untouched.

## v8 hardening round 9 (2026-04-30) — audit P1 cleanup

Audit flagged a date-keyword mismatch: §5 contributor-window checkpoint
said the 90-day window ends at the repo's latest commit **author-date**,
but `ground_truth.json` and the active-contributor counts were
generated using **commit-date** (committer timestamp). On Flask the
two diverge by 1–2 contributors near the window edge, leaving the
supervisor uncertain which timestamp to grade against.

Fix (description-only, no rubric weight or cap changes):
- §5 contributor-window line now reads "ends at the repo's latest
  commit-date (i.e. the timestamp recorded by `git log --format=%cd`,
  not author-date)".
- §3 source-resolution rules append one sentence stating both executor
  and supervisor SHOULD use commit-date (committer timestamp) — not
  author-date — when applying the 90-day window, since author-date can
  be back-dated for rebases.

Untouched: §5 weights (still sum to 1.00), §6 caps, success_threshold,
ground_truth.json. The §2/§7 wording around "today" / drift remains
as-is — the new §3 sentence is the authoritative decision rule.

## Round 4 hardening (2026-04-30) — first hardening
- Currently continue 0.80 (model_capability — opus often miscounts).
- Added §5 CPs "Per-contributor count precision (top 4)" 0.07, "Per-weekday commit distribution precision" 0.06.
- Added GT fields top_contributor_commit_counts_within_1 + per_weekday_commit_distribution + min_weekdays_within_2.
- Shaved 0.13 from existing weights: Contributor table line (0.10→0.05, −0.05), Window-span line (0.10→0.05, −0.05), Topic dimension coverage (0.10→0.07, −0.03).
- New §5 sum: 0.13+0.20+0.20+0.17+0.05+0.05+0.07+0.07+0.06 = 1.00.
- Target: opus 0.80 → ~0.65.

## Round 5 hardening (2026-04-30) — score cap for commit count drift
- After R4 anchors backfired (0.80→0.88), add a structural cap.
- §6 added "Cap 0.55 — Commit count drift >10%".
- Added GT field commit_count_drift_threshold_pct: 10.
- Target: opus 0.88 → ~0.55 if commit count drift >10% from GT.

## Round 6 hardening (2026-04-30) — second cap
- After R4 + R5 (count drift cap), score 0.79.
- §6 added "Cap 0.55 — Missing top-3 contributors".
- Added GT field top_3_contributors_required.
- Target: opus 0.79 → ~0.55 if any top-3 contributor missing.

## Round 7 hardening (2026-04-30) — sha-reference cap
- After R4+R5+R6 (count drift + top-3 contributors), score 0.77.
- §6 added "Cap 0.55 — Bullets lack commit-sha references" (≥3 of 5 bullets need sha hex).
- Added GT field min_bullets_with_sha_refs: 3.
- Target: opus 0.77 → ~0.55.

## Round 10 hardening (2026-04-30) — window date-range cap
- Score still continue 0.61 after R5+R6+R7 caps.
- §6 added "Cap 0.45 — Window date-range missing" (digest must state explicit 90-day window date range).
- Added GT fields window_date_range_required_in_digest + acceptable_date_range_formats.
- §5 weights unchanged (sum still 1.00). Lower cap (0.45) provides a stronger floor than the 0.55 caps.
- Target: opus 0.61 → ~0.46 if window date-range absent from digest.

## Cleanup pass (2026-04-30) — remove hardening_too_strict anchors
- Per FAILURE_ROOT_CAUSE_ANALYSIS.md P1: removed prompt-not-required anchors.
- DELETED §5: "Per-weekday commit distribution precision" 0.06 (not in prompt).
- DELETED §6: cap "Commit count drift >10%" (not in prompt), cap "Bullets lack sha refs" (not in prompt).
- KEPT R4 contributor count precision, R6 missing top-3 cap, R10 window date-range cap (all aligned with prompt).
- Restored 0.06 weight to existing CPs.

## Review pass (2026-04-30) — extend window to 1 year + add largest-scale CP

User feedback (review_record.md Task 9):
1. Stretch the analysis window from 90 days to 1 year (365 days) so the
   digest forces the executor to integrate over a much larger commit set
   (118 commits, 13 distinct contributors) instead of a narrow ~50-commit
   slice.
2. Replace the "most representative commit per bullet" hand-wave with a
   deterministic "largest-scale change" identification — the commit
   touching the most files (lines as tiebreak) — and add a strict
   checkpoint for it.

### Changes

**Task YAML (prompt)**
- Rewrote first paragraph: explicitly mentions "git-essentials and
  markdown-formatter skills" up front (skill mention now in §1).
- Window changed `90-day` → `1-year` / `365 days`.
- Removed bracketed parenthetical ("(login, commits, areas-touched)")
  per global "no brackets" rule.
- "Use the last commit's author-date as today" → "commit-date as today"
  to match §3 disambiguation rule.
- Added a new third paragraph asking for the year's largest-scale
  change called out by short SHA (deterministic: most files, lines as
  tiebreak).

**Sources**
- Tarball already spans many years; window is now anchored as the last
  365 days from HEAD's commit-date (2026-04-08), i.e. 2025-04-08 to
  2026-04-08 inclusive. No tarball regeneration needed.

**eval_rule.md**
- §2 task contract: window updated to 365 days; added requirement that
  digest must explicitly identify the largest-scale change with short
  SHA, and must state the explicit window date-range.
- §3 source resolution: added explicit definition of "largest-scale
  change" (files-changed primary, lines tiebreak; trivial branch-merge
  wrappers excluded; PR-landing merge SHA accepted as equivalent to
  source SHA).
- §4 ground-truth anchors: window_days=365, expected_commit_count=118,
  min_contributors_in_table=13, added largest_scale_change_commit_sha.
- §5 rubric reweighted, all checkpoints now strict (no ≥X/Y soft
  fractions). New weights:
  - 0.10 file exists with exactly 5 bullets (was 0.13)
  - 0.16 each bullet has 2+ valid 7-char SHAs (was 0.20)
  - 0.16 substantive commits coverage ≥5 (was 0.20)
  - 0.14 distinct themes ≥3 (was 0.17)
  - 0.06 contributor table covers all 13 (was 0.05, slightly raised)
  - 0.06 365-day window (was 0.08, accept 360-370 day drift)
  - 0.10 topic dimension coverage all 5/5 (was 0.10 / 4-of-5)
  - 0.10 top-4 contributor count precision ±1 (was 0.07)
  - 0.12 NEW — largest-scale change identification by short SHA
    (strict 1/1)
- §5 sum check: 0.10 + 0.16 + 0.16 + 0.14 + 0.06 + 0.06 + 0.10 + 0.10
  + 0.12 = **1.00** ✓
- §6 caps preserved verbatim, only their description text updated to
  reference the 365-day window. No cap weights changed.
- §7 continue/fail guidance: added bullet for "largest-scale change
  mentioned narratively but SHA missing" → continue.

**ground_truth.json**
- `window_days` 90 → 365.
- Added `window_end_commit_date`, `window_start_commit_date_inclusive`,
  `expected_commit_count` (=118).
- `expected_contributor_stats` and `active_contributors` regenerated
  from `git log --since=2025-04-08 --until=2026-04-09 --format=%an`:
  - David Lord 105, Markus Heidelberg 2, then 11 single-commit
    contributors (subhajitsaha01, kadai0308, abhiram kamini, Tero
    Vuotila, James Addison, Hynek Schlawack, Grant Birkinbine,
    Christian Clauss, Badhreesh, AJ Jordan, ADITYA SAH).
- `min_contributors_in_table` 4 → 13.
- `top_3_contributors_required` reduced to the 2 contributors with
  >1 commit (only David Lord and Markus Heidelberg are uniquely
  identifiable; the other 11 are tied at 1 commit each — a
  `top_contributors_note` documents this).
- Added `largest_scale_change_commit_sha = ["adf3636", "c2705ff"]`
  (PR merge + source commit, both with 36 files / 1786 lines —
  highest in the 365-day non-trivial-merge set).
- Added `largest_scale_change_metadata` with files_changed=36,
  insertions=779, deletions=1007, total_lines=1786, commit_date,
  rationale.
- `substantive_commits[]` extended from 18 to 22 entries to better
  sample the wider 1-year window (added context lifecycle refactor
  `adf3636`, release `85793d6`, build switch `0109e49`, EOL drop
  `52df9ee`, api ergonomics `ed1c9e9`, `70d04b5`).
- `min_dimensions_covered` 4 → 5 (strict).
- `acceptable_date_range_formats` updated to include 4-digit-year
  variants since the window now spans across a year boundary.

### Verification
- `git log --since=2025-04-08 --until=2026-04-09 | wc -l`: 118 commits
  (recomputed against extracted tarball).
- `git log --shortstat --no-merges --since=... --until=...` ranked by
  files: top is `c2705ff` (36 files / 1786 lines); the merged version
  `adf3636` has identical stats.
- All substantive_commits[] sha_prefixes verified resolvable via
  `git cat-file -e`.
- §5 weight sum manually recomputed: 1.00 exact.

