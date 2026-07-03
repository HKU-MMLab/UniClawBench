# Design notes — task_101_29_flask_hotspots_2yr

Internal archive only. Never injected into the executor or the user-simulator.

## Rubric tightening history

The "right files AND right relative order" check (CP3 in the current rubric) is
deliberately stringent. Earlier softer variants accepted any 10/10 set
membership without ranking quality and produced false-positive passes where
the table was numerically self-consistent but the top files were either wrong
or in the wrong order, which would mislead the onboarding engineers the public
prompt names. The stepped credit ladder (10/10 + top-7 perfect → full; 10/10 +
top-5 perfect → partial; 9/10 + top-5 perfect → smaller partial; etc.) was
added so partial competence is still rewarded but a wrong top-of-list does not
silently earn high marks.

## Skill-evidence policy

Three skills are declared in the public task. The supervisor only requires
evidence of consulting *one* of them (any of the three is sufficient) before
relaxing the skill-usage cap. This is intentional: the public prompt does not
mandate using all three skills end-to-end, only that the workspace's
repo-analysis / VCS / log-analysis skills be consulted.

## Off-bench notes

- Tarball is intentionally a snapshot; "today" is the latest author-date
  inside the tarball, not the wall clock. This is restated in §9 of the
  hidden eval rule.
- Tie-break on `File` ascending after rounding is part of the public prompt,
  so it is graded as part of CP2 (sort + tie-break) rather than as a
  separate hidden rule.

## v8 hardening round 3 (2026-04-29)

opus-4.6 was still passing this task even with moderate (0.10–0.12,
≥4-of-5) dimension coverage anchors, so this round adds a strict 5/5
all-or-nothing gate. The public prompt now naturally asks for the
ranked top-10 plus four contextual reads — contributor concentration,
churn distribution shape, bug-fix subsystem clustering, and early-vs-
recent temporal trend — phrased the way an onboarding lead would
actually phrase the follow-up questions, not as an enumerated list.
The new CP7 anchor "Topic dimension coverage" is weight 0.15 with
strict scoring: 5/5 → full 0.15, exactly 4/5 → 0.05, ≤3/5 → 0.00. To
keep §5 weights summing to 1.00, CP1 / CP3 / CP4 were each trimmed by
0.05 (0.20→0.15, 0.25→0.20, 0.20→0.15) — those checkpoints still gate
the core ranking deliverable, just with slightly more headroom for the
new anchor. GT now carries `topic_dimensions` (5 items) plus
`min_dimensions_covered: 5`. success_threshold and score caps are
unchanged.

## v8 hardening round 4 (2026-04-29)

Round 3 strict 5/5 dimension anchor still didn't keep the supervisor
below 0.85. Round 4 adds a **second anchor** ("Ranking stability") at
weight 0.08, layered on top of the existing dimension anchor, requiring
the executor's reported top-10 to include ≥6 of 6 long-running Flask
core modules from `expected_top_files`. Path matching tolerates the
`src/` prefix that newer Flask layouts use (e.g., `src/flask/app.py`
matches `flask/app.py`).

Anchor files: flask/app.py, flask/blueprints.py, flask/wrappers.py,
flask/helpers.py, flask/templating.py, flask/json/__init__.py. These
are the dominant long-running Flask core modules that any honest churn
× bugfix scoring over 2 years should surface — failing to include 6 of
them is a strong signal of a buggy or invented ranking.

§5 rebalanced: CP3 (Hotspot identification + ranking) 0.20 → 0.15
(-0.05); CP7 (Topic dimension coverage) 0.15 → 0.12 (-0.03); new CP8
(Ranking stability) at +0.08. Final weights:
0.15 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.12 + 0.08 = 1.00.

Scoring: ≥6/6 → 0.08; 4–5/6 → 0.04; ≤3 → 0.00. ground_truth.json
gains `expected_top_files` (6 paths) plus `expected_top_files_min: 6`
and the path-match tolerance rule for `src/` prefixes. score caps and
success_threshold (0.90) unchanged.

## v8 hardening round 5 (2026-04-29) — CP8 rollback

Audit re-ran the eval formula `churn × log(1 + bugfix_commits)` over the
shipped `flask_repo.tar.gz` (latest author-date 2026-04-08 21:04:03
-0700, 2-year window) and found that only 2 of the 6 round-4 anchor
files actually surface in the real top-10:

- `flask/app.py` — rank #2 (854.61) ✓
- `flask/helpers.py` — rank #6 (323.50) ✓
- `flask/wrappers.py` — rank #15 (110.96)
- `flask/blueprints.py` — rank #23 (31.19)
- `flask/templating.py` — rank #108 (hotspot=0; no bugfix commit in window)
- `flask/json/__init__.py` — rank #105 (churn=2; no bugfix commit in window)

The round-4 assumption that "any honest churn × bugfix scoring should
surface ≥6 of these 6" is contradicted by the actual repo history in
this 2-year window. Templating and the json package have effectively
stopped receiving bug-fix traffic, and blueprints / wrappers churn is
modest. CP8 was therefore awarding 0/0.08 to a correct executor —
turning a "ranking stability" check into an unreachable ceiling.

Round 5 deletes CP8 entirely and folds the 0.08 back into the two
checkpoints that already exercise ranking quality against the
supervisor's live recompute:

- CP3 (Hotspot identification + ranking) 0.15 → 0.20 (+0.05). Stepped
  tiers scaled accordingly: 10/10+top7 → 0.20, 10/10+top5 → 0.13,
  9/10+top5 → 0.10, 8/10 → 0.06, <8 → 0.00.
- CP4 (Numeric agreement) 0.15 → 0.18 (+0.03).

Final weights: 0.15 + 0.15 + 0.20 + 0.18 + 0.10 + 0.10 + 0.12 = 1.00.
ground_truth.json drops `expected_top_files`,
`expected_top_files_min`, `expected_top_files_match_rule`, and
`expected_top_files_note`. Score caps and success_threshold (0.90)
unchanged.

## Round 2 hardening (2026-04-30) — pass→continue conversion
- Currently pass 1.0; add 2 strict anchors.
- Added §5 CPs "Tie-break note precision" 0.08, "Top-3 file path canonical precision" 0.07.
- Added GT fields required_tie_break_count + top_3_file_paths_canonical.
- Shaved 0.15 total from existing weights.
- Target: opus 1.0 → ~0.77 (loses 0.08 if tie-break notes missing + 0.07 if top-3 paths drift).

## Round 3 hardening (2026-04-30) — second orthogonal anchor
- After R2 (tie-break + top-3 paths), score dropped 1.0→0.85.
- R3 added §5 CP "Per-hotspot churn-formula citation" 0.08 (≥6/10 strict).
- Added GT field hotspot_formula_required + min_top10_with_formula_citation.
- Shaved 0.08 from CP4 (Numeric agreement) 0.14 → 0.06.
- Final weights: 0.15 + 0.15 + 0.15 + 0.06 + 0.08 + 0.09 + 0.09 + 0.08 + 0.07 + 0.08 = 1.00.
- Target: opus 0.85 → ~0.65 (loses 0.08 if opus shows scores without formula computation).

## Round 4 hardening (2026-04-30) — third anchor
- After R2+R3, score 0.84.
- R4 added §5 CPs "Per-top-10 recent-half-share precision" 0.07, "Per-top-10 primary_author identification" 0.06.
- Added GT fields per_top10_required_fields + min_top10_with_fields.
- Shaved 0.13 from CP3 (Hotspot identification + ranking) 0.15 → 0.10, CP4 (Numeric agreement) 0.06 → 0.03, CP7 (Topic dimension coverage) 0.09 → 0.04.
- Target: opus 0.84 → ~0.65.

## Round 5 hardening (2026-04-30) — cap for missing synthesis
- After R2+R3+R4, score 0.62.
- §6 added "Cap 0.55 — Missing synthesis paragraph" (≥80 words tying findings to takeaways).
- Added GT field min_synthesis_paragraph_words: 80.
- Target: opus 0.62 → ~0.55 if synthesis missing.

## Round 6 hardening (2026-04-30) — strict anchor fields cap
- R5's synthesis cap didn't bite (score 0.62→0.64).
- §6 added "Cap 0.55 — Top-10 missing anchor fields" (≥8/10 rows must have all 6 anchor fields).
- Added GT fields required_top10_anchor_fields + min_top10_rows_with_all_fields.
- Target: opus 0.64 → ~0.55 if rows lack any of the 6 required fields.

## Round 9 hardening (2026-04-30) — push to 0.40
- After R2+R3+R4+R5+R6 (multiple caps), score 0.55.
- §6 added "Cap 0.40 — Missing per-file ownership stats".
- Added GT fields per_file_ownership_stats_required + min_top10_with_ownership_stats + required_ownership_fields.
- Target: opus 0.55 → ~0.40.

## Cleanup pass (2026-04-30) — remove hardening_too_strict anchors
- Per FAILURE_ROOT_CAUSE_ANALYSIS.md P1: removed 5 §5 anchors + 3 §6 caps for hotspot row-level metadata not in prompt.
- DELETED §5: tie-break note (0.08), top-3 path canonical (0.07), churn-formula citation (0.08), recent_half_share_pct (0.07), primary_author (0.06).
- DELETED §6 caps: synthesis paragraph, top-10 anchor fields, ownership stats.
- Restored 0.36 weight to original §5 CPs (Hotspot identification, Numeric agreement, Topic dim coverage).

## Review pass (2026-04-30) — global rules + strict canonical top-10

Applied global review rules from /tmp/clawbench_modify_instructions.md:

- **Prompt rewrite (ENGLISH, natural, no brackets, skill in first paragraph).**
  Replaced templated phrasing with conversational user voice: "Hey, I want to
  find the 10 hottest files in the Flask repo over the last 2 years…".
  Mentions all three skills (code-analysis-skills + git + log-analyzer) by
  natural names ("repo-analysis, version-control-history, and log-analysis
  skills") in the first paragraph. Eliminated all parentheses; replaced
  parenthetical examples with em-dashes or "for example" lists. Hotspot
  formula is stated inline as `churn * log(1 + bugfix)`. Tie-break stated
  inline. The follow-up "context" ask is preserved but de-bulleted into
  prose so it feels like a real onboarding lead's request.

- **Strict checkpoints (no ≥X/Y).** §5 rewritten so every CP is
  all-or-nothing on its primary check. CP3 now demands the full canonical
  top-10 in exact order (any swap or missing path → 0.00); CP4 demands
  10/10 numeric agreement on Churn (exact int), BugFix (exact int), and
  Hotspot (±0.5 absolute tolerance) — any single row failing any of the
  three zeros the whole CP. CP6 strict 10/10 on path resolvability. CP7
  strict 5-of-5 dimension coverage (4-of-5 fallback removed).

- **GT correctness re-derived from sources/.** Extracted
  `sources/flask_repo.tar.gz`, ran `git log --no-merges` (HEAD ancestry,
  non-merge commits only) over the window 2024-04-08..2026-04-08
  inclusive (latest author-date in tarball is 2026-04-08), and recomputed
  hotspot for every changed path with churn = insertions+deletions and
  bugfix = number of non-merge HEAD commits whose lowercased message
  contains "fix" or "bug". 157 non-merge commits in window. Top-10
  (canonical, with tie-break by File ascending after rounding to 2
  decimals):
    1. uv.lock                  churn=8132 bugfix=1 hotspot=5636.67
    2. src/flask/app.py         churn= 531 bugfix=4 hotspot= 854.61
    3. tests/test_basic.py      churn= 335 bugfix=3 hotspot= 464.41
    4. requirements/dev.txt     churn= 643 bugfix=1 hotspot= 445.69
    5. src/flask/sansio/app.py  churn= 322 bugfix=2 hotspot= 353.75
    6. src/flask/helpers.py     churn= 201 bugfix=4 hotspot= 323.50
    7. pyproject.toml           churn= 280 bugfix=2 hotspot= 307.61
    8. docs/appcontext.rst      churn= 244 bugfix=2 hotspot= 268.06
    9. CHANGES.rst              churn= 120 bugfix=7 hotspot= 249.53
   10. docs/config.rst          churn= 142 bugfix=3 hotspot= 196.85
  GT JSON now embeds this list verbatim under `top_10` plus
  `latest_author_date`, `window_start`, `commit_counting`,
  `bugfix_match_rule`, `path_match_rule` (src/ optional), and
  `hotspot_tolerance: ±0.5`.

- **§5 sum verified.** 0.10 (CP1) + 0.10 (CP2) + 0.25 (CP3) + 0.20 (CP4)
  + 0.10 (CP5) + 0.05 (CP6) + 0.20 (CP7) = 1.00.

## Fix pass (2026-05-02) — git history-simplification ambiguity resolved

**Root cause identified:** The review-pass GT was computed using per-file
`git log -- <path>`, which invokes Git's default history-simplification.
When a merge commit is TREESAME for a given file on one parent, Git follows
only that parent's history and skips commits from the merged branch, even if
those commits touched the file. This produced lower churn and bugfix counts
for files modified on the `stable` branch (e.g., `src/flask/app.py` showed
churn=529 / bugfix=3 instead of the true 531 / 4).

The model's natural approach — running a single global `git log --no-merges
--numstat` and attributing each numstat line to its file — avoids this
simplification entirely because no pathspec is supplied. This gives
deterministic, unambiguous counts.

**Changes made:**

1. **GT updated** to use `git log --after=2024-04-08 --no-merges --numstat`
   (global, non-merge commits, 157 commits in window). Three values changed:
   - `src/flask/app.py`:       churn 529→531, bugfix 3→4, hotspot 733.35→854.61
   - `requirements/dev.txt`:   churn 583→643, bugfix 1→1, hotspot 404.10→445.69
   - `pyproject.toml`:         churn 276→280, bugfix 2→2, hotspot 303.22→307.61
   Top-10 file list and ordering remain identical.

2. **eval_rule.md §3** updated to specify `--no-merges` in the supervisor
   recomputation instruction.

3. **git skill SKILL.md** forked: added "Churn / Hotspot Analysis" section
   recommending `--no-merges` global log for per-file statistics, with a
   caution against per-file pathspec (history-simplification).

4. **skill_fork_manifest.json** updated to record the git skill change.
