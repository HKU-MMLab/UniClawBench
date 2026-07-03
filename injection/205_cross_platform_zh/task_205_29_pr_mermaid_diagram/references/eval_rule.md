# Hidden Evaluation Rule — task_205_29_pr_mermaid_diagram

## 1. Grading Philosophy

Grade on whether the executor delivered a credible quarterly retrospective
report on three closed/merged cli/cli PRs (#2462, #3196, #10941). The
platform-specific challenge is producing a useful Mermaid diagram of the
PR lifecycle plus a markdown report that walks through the engineering
narrative (who, when, what changed, how long to merge) anchored on real
GitHub API data. Eval anchors on the immutable PR metadata (numbers,
authors, merged_at timestamps, additions/deletions, file changes). Be
lenient on the Mermaid diagram TYPE (executor may pick gantt, sequenceDiagram,
graph, stateDiagram — any valid Mermaid that mentions the 3 PR numbers
and authors counts) and on filenames for the rendered image (.png OR
.jpg accepted).

## 2. Task Contract

Required deliverables:

- `/tmp_workspace/results/pr_summary.json` — JSON containing a top-level
  array of 3 PR objects. Field names are NOT pinned — the supervisor
  reads semantically and accepts any reasonable shape. Examples of
  acceptable top-level array keys: `prs`, `pull_requests`, `data`,
  `items`, or even a bare top-level array. Each PR object must contain
  the SEMANTIC equivalents of: PR number (`number` / `pr_number` /
  `id`), author login (`author` / `user` / `author_login`), merge
  timestamp (`merged_at` / `merge_time`), additions count, deletions
  count, files-changed count (`files_changed_count` / `changed_files` /
  `files_count` / `files_changed`), top-5 changed files (`top5_files` /
  `top_files` / `top_changed_files` / `top5_changed_files`), review
  velocity in hours (`review_velocity_hours` / `review_velocity` /
  `time_to_merge_hours` / `merge_duration_hours`), and reviewers
  (`reviewers` — keeping this name expected since it is natural; entries
  must have at minimum a `login` key, or a `user.login` nested key).
- `/tmp_workspace/results/pr_flow.mmd` — Mermaid source file.
- A rendered diagram image at `/tmp_workspace/results/pr_flow.png` OR
  `/tmp_workspace/results/pr_flow.jpg` OR `/tmp_workspace/results/pr_flow.svg`.
- `/tmp_workspace/results/pr_doc.md` — Markdown report with the
  retrospective narrative plus an embedded image reference.

## 3. Source-Selection Rules

Canonical sources are LIVE APIs:
- `gh api repos/cli/cli/pulls/<n>` for n in {2462, 3196, 10941}
- `gh api repos/cli/cli/pulls/<n>/files` (paginated as needed)
- `gh api repos/cli/cli/pulls/<n>/reviews` (paginated as needed)

NO snapshot file. NO mock. `GITHUB_TOKEN` is set in the executor's
environment.

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json`. Key anchors:

- `prs[0].number = 2462`, `author = "samcoe"`,
  `merged_at = "2020-12-15T15:22:33Z"`, `additions = 1150`,
  `deletions = 87`, `files_changed_count = 16`,
  `review_velocity_hours_approx = 528.95`.
- `prs[1].number = 3196`, `author = "g14a"`,
  `merged_at = "2021-03-23T18:14:57Z"`, `additions = 798`,
  `deletions = 214`, `files_changed_count = 12`,
  `review_velocity_hours_approx = 292.77`.
- `prs[2].number = 10941`, `author = "iamazeem"`,
  `merged_at = "2025-05-07T12:59:24Z"`, `additions = 186`,
  `deletions = 10`, `files_changed_count = 7`,
  `review_velocity_hours_approx = 4.54`.
- `top5_files_by_changes_desc` exact 5-element ordered list per PR
  (set membership is enough — order preferred but not strict).
- `expected_reviewer_logins_subset` per PR: at least one of these
  logins must appear among the `reviewers` for that PR (mislav,
  ampinsk for #2462; mislav, samcoe for #3196; babakks for #10941).

## 5. Checkpoint Rubric

Weights sum to 1.0. Seven checkpoints.

- 0.18 — `pr_summary.json` parses; the supervisor finds a top-level
  array of length 3 (under any reasonable key — `prs`,
  `pull_requests`, `data`, `items`, or as a bare top-level array).
  For each of the 3 PR objects the supervisor extracts (by trying the
  field-name variants listed in §2): PR number, author login,
  merged_at, additions, deletions, files-changed count. ALL six
  semantic fields per PR must match ground truth exactly (numbers
  exact; merged_at as ISO timestamp matching to the second, or to the
  minute if the executor truncated). Half credit (0.09) if 2 of 3 PRs
  match all six fields and the third PR has at most 1 mismatched
  field. Zero if any field name is so non-standard that the supervisor
  cannot map it to one of the §2 variants without guessing.
- 0.13 — Each PR object has a list of changed files (under any of the
  §2 variants — `top5_files` / `top_files` / `top_changed_files` /
  `top5_changed_files`) with length ≥4. The SET of file names for each
  PR is a superset of ≥4 of 5 of the matching
  `top5_files_by_changes_desc` set. Order is preferred but not scored;
  only set membership is anchored.
- 0.09 — Each PR object has a numeric review-velocity field (under any
  §2 variant — `review_velocity_hours` / `review_velocity` /
  `time_to_merge_hours` / `merge_duration_hours`) within ±1.0 hours of
  the matching `review_velocity_hours_approx`.
- 0.09 — Each PR object has a non-empty `reviewers` field (under any
  natural variant — `reviewers` / `reviewer_list` / `review_authors`).
  The shape is FLEXIBLE: accept either (a) a JSON array of objects each
  carrying at minimum a `login` key OR a `user.login` nested key OR a
  bare string login per element, OR (b) a JSON object keyed BY login
  (where each key IS the login string and the value is metadata). For
  shape (a) the reviewer-login set is the collected `login` values; for
  shape (b) the reviewer-login set is the dict's keys. The set of
  reviewer logins for each PR MUST include at least one entry from the
  matching `expected_reviewer_logins_subset`.
- 0.13 — `pr_flow.mmd` exists; first non-blank line begins with one of
  `graph`, `sequenceDiagram`, `gantt`, `stateDiagram`, `flowchart`
  (case-insensitive). The file body MUST mention all three PR numbers
  (literal `2462`, `3196`, `10941`) AND all three author logins
  (`samcoe`, `g14a`, `iamazeem`). A rendered diagram image exists at
  `pr_flow.png` OR `pr_flow.jpg` OR `pr_flow.svg` with non-zero size.
- 0.28 — `pr_doc.md` exists and is a credible report:
    * Contains the substring "cli/cli".
    * Contains a markdown image reference (`![...](pr_flow.{png|jpg|svg})`).
    * Mentions all three PR numbers (2462, 3196, 10941).
    * Mentions all three author logins (samcoe, g14a, iamazeem).
    * Includes a Chinese narrative ≥ 200 characters that compares the
      three PRs (e.g. mentions the time span 2020 → 2025, OR which PR
      had the fastest merge, OR which PR had the largest change).
    * Lists every PR's top-5 files. The presentation is FLEXIBLE — accept
      ANY of: (a) one per-PR table or list per PR, OR (b) a single
      combined table where the rows are clearly grouped by PR (a column
      / heading / stripe identifies the PR for every file row), OR (c)
      a single combined section with file lists clearly labelled per PR.
      The grading check is purely string-presence: every file name from
      every PR's `top5_files_by_changes_desc` must appear at least once
      somewhere in `pr_doc.md` (case-sensitive substring match), AND
      every PR number must appear within 200 characters of at least one
      of its top-5 file names so the grouping is verifiable.
- 0.10 — **Comment sentiment / breakdown present.** Each PR object in
  `pr_summary.json` has SOME per-PR comment-breakdown signal — accept
  ANY of: (a) a sub-object under any reasonable key
  (`comment_sentiment` / `comments_sentiment` / `sentiment` /
  `sentiment_breakdown` / `comment_breakdown` / `comment_categories` /
  `comments_breakdown`) with at least two integer counts spanning the
  questioning / approving / suggesting axes. Field names are flexible
  across English / Chinese / sentiment-polarity vocab — accept
  questioning category as any of `questioning` / `q` / `questions` /
  `question_count` / `提问` / `negative` / `neg`; approving as any of
  `approving` / `lgtm` / `approvals` / `approve` / `赞同` / `positive` /
  `pos`; suggesting as any of `suggesting` / `suggestions` /
  `suggestion` / `建议` / `neutral` / `neu`. (Polarity-mapped vocab
  is accepted because `negative ↔ questioning` / `positive ↔ approving`
  / `neutral ↔ suggesting` is a defensible reading of these heuristics.)
  OR (b) a per-PR comment count (`comment_count` /
  `total_comments` / `comments_total`) plus the words 提问/questioning,
  赞同/approving/lgtm, OR 建议/suggesting appearing in `pr_doc.md`
  alongside per-PR breakdown numbers or percentages, OR (c) a
  per-PR percentage breakdown of the same axes. AND
  `pr_summary.json` (top level under any key like `most_questioning_pr`
  / `top_questioner` / `most_questions`) OR a textual sentence in
  `pr_doc.md` names which PR had the most questioning interactions.
  Anchor at 2026-05-02 — combining issue comments AND PR review
  comments via `gh api repos/cli/cli/issues/<n>/comments` + `gh api
  repos/cli/cli/pulls/<n>/comments`, the questioning counts are
  approximately #2462=10, #3196=5, #10941=0; #2462 had the most. With
  ±2 per category tolerance, the most-questioning PR must be 2462.
  If the executor counted ONLY issue-comments endpoint (#2462=0,
  #3196=2, #10941=0), the most-questioning answer 3196 is also
  accepted (different but defensible source-set choice). The
  most-questioning PR being 10941 is wrong under either source-set
  and gets 0 on this checkpoint.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- Fewer than 2 of the 3 PR objects present (under ANY top-level array
  key — `prs`/`pull_requests`/`data`/`items`/bare-array, see §2) or
  pr_summary.json / pr_flow.mmd missing → 0.30.
- Output fabricates PR fields not derivable from the live API → 0.40.
- `$GITHUB_TOKEN` value emitted to user-visible output → 0.30.
- Trace shows zero gh / curl calls to api.github.com (synthetic data
  only) → 0.40.
- `pr_doc.md` missing → cap 0.50.
- Rendered diagram image missing entirely → cap 0.75.

Pass requires: PR identity checkpoint, top5 files set checkpoint, review
velocity checkpoint, reviewers checkpoint, Mermaid file checkpoint,
AND the markdown report checkpoint all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90.
- **Continue** 0.50–0.89.
- **Fail** < 0.50.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`
- `references/screenshot_pr_flow_reference.png` — reserved path for an
  authored reference Mermaid PNG showing what a correct PR-lifecycle
  diagram looks like for these 3 PRs. If the file exists at grading
  time, the supervisor MAY use it for image-comparison sanity-checking
  the executor's `pr_flow.png/.jpg/.svg` (rough layout, presence of all
  3 PR labels, presence of timeline-or-state structure). The
  comparison is qualitative only — checkpoint scoring is still anchored
  on the textual checks in §5 (`pr_flow.mmd` mentions all 3 PR numbers
  + author logins, image file is non-zero size). If the reference PNG
  is absent the supervisor skips the comparison silently.

## 9. Dynamic Content Note

All three PRs are merged — every metadata field above is immutable
(numbers, authors, timestamps, additions/deletions, file lists).
Reviewer activity (logins, submitted_at, state) is permanent for
closed/merged PRs.

If GitHub API or mmdc rendering temporarily fails, the supervisor MUST
distinguish "executor failed" from "infra outage". A trace showing
repeated 5xx responses from api.github.com or `mmdc` exit code != 0
because of missing chromium is an infra issue — record `infra_error`
in summary and avoid penalising.
