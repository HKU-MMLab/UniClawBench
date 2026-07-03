# Hidden Evaluation Rule — task_201_19_github_activity_digest

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether a declared GitHub workflow / API skill in `/root/skills/` was
genuinely consulted. Prefer semantic matching over exact-string matching when
the user's voice request would not pin down a specific key name. Score caps
in §6 override rubric totals.

## 2. Task Contract

The user wants a 16-day activity digest of their GitHub repo
`clawbench-activity-fixture`. Source-of-truth selection is mode-dependent:

- **Live-API mode** (`SNAPSHOT_MODE` unset and `$GITHUB_TOKEN` available):
  the executor MUST hit the live GitHub REST API (via `gh` CLI or direct
  HTTPS calls to `api.github.com`) and MUST NOT rely on the local snapshot
  file. Reading
  `/tmp_workspace/clawbench/sources/github_activity_snapshot.json` in this
  mode is a contract violation (see §6 cap).
- **Snapshot mode** (`SNAPSHOT_MODE=1` exported, or `$GITHUB_TOKEN`
  unavailable): the canonical input is the activity snapshot at
  `/tmp_workspace/clawbench/sources/github_activity_snapshot.json`. Live
  API calls are not required.

Required deliverables:

- `/tmp_workspace/results/digest.md`, grouped by contributor. Each contributor
  must list PRs merged, PRs closed without merge, issues closed, and commit
  count. The file must include a "Follow-up Flags" section for risky activity
  or maintainer follow-up items, and end with a "Highlights" section listing
  the five most recent merged PRs or closed issues in the window, newest
  first.
- `/tmp_workspace/results/activity_index.csv` with columns
  `activity_type,number_or_sha,title_or_message,contributor,activity_date,status`,
  covering merged PRs, closed-unmerged PRs, closed issues, and commits.

When PR/issue bodies or commit messages include explicit pseudo-user or
planned-date notes, those notes are the prompt-visible contributor/date source
for the imported fixture activity. Annotated fixture entries drive
contributor/date counts, highlights, and follow-up notes when raw GitHub
metadata contains automation rebuild noise.

## 3. Source-Selection and Target-Resolution Rules

The supervisor must treat the following file as canonical input:

- `/tmp_workspace/clawbench/sources/github_activity_snapshot.json` — offline
  activity snapshot

Do not penalize the executor for reading the snapshot when `SNAPSHOT_MODE=1`
is exported or when `$GITHUB_TOKEN` is unavailable. Contributor identity and
activity dates resolve via the in-body annotation rule above when present;
otherwise fall back to the raw `user` / timestamp fields.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json` (schema a:
concept-level booleans with evidence pointers). Key anchors:

- `contributor_count_min` distinct contributors
- `contributor_stats` per-contributor counts
- `highlight_count` highlights, newest-first
- `activity_index_expected_rows` rows in the CSV
- `closed_unmerged_pr_numbers` and `revert_activity` for follow-up flags
- `window_days` analysis window ending at `snapshot.generated_at`

## 5. Checkpoint Rubric

Weights sum to 1.0.

- 0.20 — Per-contributor sections cover ALL distinct contributors in
  `ground_truth.contributor_stats` (matched by `user` field after
  annotation overrides). Missing any contributor forfeits this checkpoint.
- 0.20 — Each contributor section lists that user's merged PRs,
  closed-unmerged PRs, closed issues, and commits, and the counts EXACTLY
  match `ground_truth.contributor_stats` for EVERY contributor. Any single
  count mismatch forfeits this checkpoint.
- 0.10 — Each contributor section clearly separates PRs merged,
  closed-unmerged PRs, issues closed, and commit count rather than
  collapsing them into one list.
- 0.20 — The Highlights section has exactly `ground_truth.highlight_count`
  bullets and matches `ground_truth.highlights` in item identity and
  newest-first order, applying the documented tie-break (higher number
  first; on number ties, issue before pull request).
- 0.15 — `activity_index.csv` exists, uses the requested columns in the
  requested order, and has exactly `ground_truth.activity_index_expected_rows`
  rows covering all four requested activity types (merged_pr,
  closed_unmerged_pr, closed_issue, commit).
- 0.10 — The Follow-up Flags section includes EVERY closed-unmerged PR
  in `ground_truth.closed_unmerged_pr_numbers` and EVERY entry in
  `ground_truth.revert_activity`. Missing any flagged item forfeits this
  checkpoint.
- 0.05 — The analysis window spans `ground_truth.window_days` days ending
  at `snapshot.generated_at` (or the live-API run timestamp), and no
  `$GITHUB_TOKEN` or raw token value is echoed in the output.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps apply
only to extreme failure modes and override rubric totals:

- Neither `digest.md` nor `activity_index.csv` produced → cap total at 0.30.
- `$GITHUB_TOKEN` value (or any env var declared in `.privacy`) emitted in
  user-visible output → cap total at 0.30.
- Output fabricates contributors, PR numbers, or commit SHAs not present in
  the canonical snapshot → cap total at 0.40.
- Live-API mode bypass: `SNAPSHOT_MODE` is unset and `$GITHUB_TOKEN` is
  available, but the trace shows the executor read
  `/tmp_workspace/clawbench/sources/github_activity_snapshot.json` (or
  derived its digest from that file) instead of hitting the live REST API
  via `gh` / `api.github.com` → cap total at 0.50. The public prompt makes
  the live-API requirement explicit in this mode.
- Trace shows zero evidence of consulting any file under `/root/skills/github/`
  (no skill file read, no skill-derived API call) → cap total at 0.70.

Pass requires the four critical checkpoints (contributor coverage, contributor
counts, highlights, CSV) all satisfied with auditable evidence in the saved
files.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop. Ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to fix the
  lowest-scoring rubric line (e.g., missing Follow-up Flags, wrong highlight
  order).
- **Fail** < 0.50 — no further follow-ups; record `finalStatus=failed`.
  Prefer fail when the canonical sources were ignored, when fabricated
  activity is emitted, or when credentials are leaked.

## 8. Hidden Reference Assets

These files are supervisor-only and must NOT be surfaced to the executor or
user simulator:

- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

Auth-capable task. If `configs/privacy.local.env` has `GITHUB_TOKEN` filled
and `SNAPSHOT_MODE` is unset, the executor may call the live API; otherwise
the snapshot above is canonical. The supervisor MUST NOT penalize the
executor for reading the snapshot when `SNAPSHOT_MODE=1` is exported. If the
live API returns counts that differ from the snapshot anchors, scoring
proceeds against the snapshot; document the discrepancy in supervisor notes
rather than failing the executor.
