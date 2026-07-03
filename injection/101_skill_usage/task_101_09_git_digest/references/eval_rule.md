# Hidden Evaluation Rule — task_101_09_git_digest

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed
and whether the digest is anchored to commits that genuinely exist in
the supplied tarball. Prefer semantic matching over exact-string
matching: bullet themes and contributor names should be accepted on
clear paraphrase, since the user's natural-language request would not
pin down a specific label. The supervisor must extract the tarball and
recompute the 1-year (365-day) window itself; do not rely on
remembered Flask history. Score caps in §6 override rubric totals.

## 2. Task Contract

The user supplies a Flask repo tarball at
`/tmp_workspace/clawbench/sources/flask_repo.tar.gz` and asks for a
365-day commit digest written to `/tmp_workspace/results/digest.md`.

Completion requires that `digest.md` contains:

- A 5-bullet thematic summary; each bullet has a one-line description
  plus 2 representative short SHAs (7-char prefix).
- A trailing contributor table covering every contributor who made
  >=1 commit in the same 1-year window, one row per contributor,
  sorted by commit_count descending.
- Explicit identification (with short SHA) of the single largest-scale
  change in the window — the commit that touched the most files, with
  total lines changed (insertions + deletions) as a tiebreak.
- An explicit window date-range (e.g., `YYYY-MM-DD to YYYY-MM-DD`,
  `MMM DD - MMM DD`, or `since YYYY-MM-DD`).

The 1-year window ends at the latest commit's commit-date in the
tarball ("today"). Each bullet must be tied to a concrete theme that
is visible in the cited commits — generic "maintenance work" labels
do not satisfy the prompt.

## 3. Source-Selection and Target-Resolution Rules

The only canonical input is `flask_repo.tar.gz` under
`/tmp_workspace/clawbench/sources/`. The supervisor must extract this
tarball and treat its `git log` as the authoritative commit set; any
content the executor invents, fetches from outside, or carries over
from prior Flask knowledge is out of scope.

Ambiguity resolution:

- "Today" = commit-date (committer timestamp) of the tarball's latest
  commit on the default branch.
- "1-year window" / "365-day window" = strictly inclusive of the 365
  calendar days ending on that date.
- Contributor identity = the `author name` field as recorded in the
  tarball's git history; merge identical names, do not merge by email.
- Both the executor and supervisor MUST use commit-date (committer
  timestamp), not author-date, when applying the 365-day window, since
  author-date can be back-dated for rebases.
- "Largest-scale change" is determined by `git log --shortstat` over
  the 365-day window, ranking primarily by `files_changed` and using
  `insertions + deletions` (total lines) as a tiebreak. Merge commits
  whose subject begins with `Merge branch` (i.e. trivial branch-merge
  wrappers that aggregate stats from multiple commits) are excluded.
  PR-landing merge commits (e.g., subjects ending with `(#NNNN)`) are
  considered equivalent to their source commit; either SHA is accepted
  by the supervisor when both refer to the same change set.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema `c`: sorted/ranked list with deterministic tie-break). Key
anchors used in §5:

- `bullet_count = 5`
- `min_shas_per_bullet = 2`, `sha_prefix_len = 7`
- `min_substantive_commits_covered = 5` (drawn from
  `substantive_commits[]`, which lists ~22 commits across themes such
  as test cleanup, dependency maintenance, security tooling,
  context/teardown lifecycle, routing behavior, release management,
  documentation, build/tooling switch, deprecations, etc.)
- `min_distinct_themes = 3`
- `expected_commit_count = 118` (commits in the 365-day window from
  the pinned tarball; supervisor must verify by recomputation and
  prefer the recomputed value if it diverges by ≤3)
- `min_contributors_in_table = 13`, with `expected_contributor_stats[]`
  giving the expected name + commit_count for each of the 13
  contributors active in the 1-year window
- `topic_dimensions[]` lists the 5 implicit dimensions the user's
  natural-language request covers (shipped features, bug fixes,
  deprecations or removals, performance changes, contributor
  activity); `min_dimensions_covered = 4`
- `largest_scale_change_commit_sha` lists the canonical short SHA(s)
  identifying the year's largest-scale change

The supervisor must recompute the 1-year commit set from the extracted
tarball and confirm the ground_truth values against it before scoring.

## 5. Checkpoint Rubric

Weights sum to 1.0. All checkpoints are STRICT — no fractional partial
credit unless explicitly stated.

- **0.10** — `digest.md` exists at `/tmp_workspace/results/digest.md`
  and contains exactly `bullet_count` (=5) thematic bullet entries.
  Strict: not 4, not 6.
- **0.16** — Each of the 5 bullets cites exactly
  `min_shas_per_bullet` (=2) short SHAs of length `sha_prefix_len`
  (=7), and every cited SHA resolves in the extracted repo (e.g.,
  `git cat-file -e <sha>` succeeds). Strict: 5/5 bullets must satisfy.
- **0.16** — The cited SHAs collectively cover at least
  `min_substantive_commits_covered` (=5) entries from
  `ground_truth.substantive_commits[]`. Strict 5/5: ≤4 → 0.00.
- **0.14** — Bullet descriptions surface at least
  `min_distinct_themes` (=3) distinct substantive themes drawn from
  `ground_truth.substantive_commits[].theme`. Clear paraphrases are
  accepted (e.g., "test housekeeping" for "test cleanup"); generic
  catch-alls like "general maintenance" do not count. Strict 3/3
  themes: ≤2 → 0.00.
- **0.06** — Contributor table lists every contributor with >=1
  commit in the 1-year window, one row per contributor, sorted by
  `commit_count` descending. Strict: every active contributor in
  `ground_truth.expected_contributor_stats` (13 names) must appear,
  with the table sorted descending by commit count. Missing any one
  contributor → 0.00.
- **0.06** — The analysis window spans `window_days` (=365) calendar
  days and ends at the repo's latest commit-date (i.e. the timestamp
  recorded by `git log --format=%cd`, not author-date), confirmed by
  re-extracting the tarball. Strict: a window ≥360 and ≤370 days is
  accepted; outside that → 0.00.
- **0.10** — Topic dimension coverage. `digest.md` naturally addresses
  all 5 implicit dimensions the user asked for: shipped features, bug
  fixes, deprecations or removals, performance changes, contributor
  activity. The supervisor uses keyword/topic matching against the
  tarball's git log to verify each dimension is grounded in real
  commits in the 1-year window; dimensions that genuinely had no
  activity may be acknowledged as "no activity this window" and still
  count toward coverage if the digest explicitly notes the absence
  rather than omits the topic. Strict 5/5: ≤4 → 0.00.
- **0.10** — Per-contributor count precision (top 4). For the top 4
  contributors by commit count in
  `ground_truth.expected_contributor_stats`, the digest's contributor
  table must report each commit count within ±1 of GT. Strict 4/4:
  any contributor off by >1 → 0.00. (David Lord is the dominant
  contributor; the next 3 are tied at low single-digit counts and the
  supervisor must accept any 3 valid 1-of-12 contributors as filling
  the tied slots, as long as the count for each row is within ±1 of
  the recomputed GT for that name.)
- **0.12** — Largest-scale change identification. `digest.md` MUST
  explicitly identify the single commit that is the largest-scale
  change in the 365-day window — the commit with the most files
  changed (primary) with insertions+deletions total as tiebreak. The
  digest must include the short 7-char SHA of that commit. Accepted
  SHAs are listed in `ground_truth.largest_scale_change_commit_sha`
  (any one of the listed equivalents is sufficient — the source
  commit and its PR-landing merge commit both count). Strict 1/1:
  wrong SHA, missing SHA, or only a vague "biggest refactor" mention
  without the SHA → 0.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from the rubric in §5. The following caps target
extreme-failure modes only and override the rubric total when
triggered:

- **Cap 0.30 — no deliverable produced.** `digest.md` is missing,
  empty, or contains no bullet/table structure recognizable as the
  requested digest.
- **Cap 0.30 — fabricated commit anchors.** Any cited SHA fails to
  resolve in the extracted repo (e.g., `git cat-file -e` errors), or
  the contributor table contains names absent from the tarball's
  1-year commit set. Fabricated provenance is the failure mode this
  cap targets, not a single typo.
- **Cap 0.30 — credentials emitted.** Any value whose env var is
  declared in `.privacy` appears in `digest.md` or any other
  user-visible artifact.
- **Cap 0.40 — total scope blowout.** The deliverable enumerates
  commits or contributors clearly outside the 1-year window (e.g.,
  multi-year history beyond 365 days, unrelated repositories),
  indicating the task contract was not honored.
- **Cap 0.55 — Missing top-3 contributors.** If the contributor table
  in `digest.md` (or contributor_stats section) is missing ANY of the
  3 contributors named in `ground_truth.top_3_contributors_required`,
  cap total at 0.55. Top contributors define the digest narrative;
  omitting them indicates broken aggregation.
- **Cap 0.45 — Window date-range missing.** If `digest.md` doesn't
  state the 1-year window date-range explicitly (e.g.,
  `2025-04-08 to 2026-04-08`, or `since YYYY-MM-DD`), cap total at
  0.45. Critical metadata for grounded reading.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/git-essentials/` OR
  `/root/skills/markdown-formatter/` OR `/root/skills/discord/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full
  score.

A run that satisfies all §5 checkpoints and trips no §6 cap should
score >=0.90.

## 7. Continue vs Fail Guidance

Prefer **continue** when:

- `digest.md` exists with the right shape but is missing 1 bullet, 1
  contributor row, or has only 1-2 SHAs in one bullet.
- Themes are mostly correct but one bullet uses an over-generic label
  that could be tightened.
- The window endpoint is off by a small drift (e.g., used author-date
  rather than commit-date) but the commit set is otherwise plausible.
- Largest-scale change is mentioned narratively but the explicit short
  SHA is missing.

Prefer **fail** when:

- No `digest.md` was produced or the file is empty/unrecognizable.
- Cited SHAs cannot be resolved in the tarball, or contributor names
  are fabricated.
- Credentials from `.privacy` were emitted.
- The digest enumerates content from far outside the 365-day window
  (scope blowout).

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the
executor or user simulator:

- `references/eval_rule.md` (this file) — the grading spec.
- `references/ground_truth.json` — concrete thresholds, expected
  substantive commit anchors, the active-contributor list with
  commit counts, and the largest-scale change SHA.

## 9. Dynamic Content Note

Offline task — no live API or network calls are expected. The Flask
tarball is pinned to a specific commit, so the 365-day window, the
contributor counts, and the largest-scale change identification are
deterministic across runs. If the supervisor's recomputation from the
tarball disagrees with `ground_truth.json` on a specific count, prefer
the recomputed value and accept executor output that matches the
recomputation.
