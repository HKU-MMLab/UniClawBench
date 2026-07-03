# Design notes — task_101_19_github_activity_digest

Internal notes archived from earlier eval_rule revisions. Not injected into
the executor or supervisor prompts.

## Cap history

Earlier eval_rule revisions enumerated checkpoint-mirroring caps such as:

- `activity_index.csv` missing → cap 0.86
- closed-unmerged PRs mixed into merged PRs / omitted from contributor counts
  → cap 0.88
- Follow-up Flags section missing → cap 0.88
- No read of `/root/skills/github/SKILL.md` or any file under
  `/root/skills/github/` → cap 0.89 (mirrored a prior policy that any
  skill_usage task with zero evidence of consulting the declared skill could
  not reach full score)

These were collapsed because they restated rubric items rather than guarding
extreme failure. The current §6 keeps only the credentials-leak, no-deliverables,
fabricated-sources, and zero-skill-evidence cases (capped ≤ 0.70 per the
project-wide cap policy).

## Annotation override rationale

Imported fixture entries may be authored by an automation account. Public
task instructs the executor to honor the in-body pseudo-user / planned-date
notes; the rubric anchors (contributor stats, highlights, follow-up flags,
CSV rows) were captured under the post-annotation view, so supervisor
verification uses the same view.

## Snapshot vs live API

The snapshot file is canonical when `SNAPSHOT_MODE=1` is exported or when
`$GITHUB_TOKEN` is absent. Live-API runs may produce slightly different
counts as the upstream fixture repo evolves; the §9 dynamic-content note
keeps the snapshot as the scoring anchor and asks the supervisor to log,
not penalize, drift.

## v8 hardening round 9 (2026-04-30) — audit P1 cleanup

Highlights tie-break disambiguation. Previously the public prompt asked
the executor to apply "a stable secondary ordering rule (e.g. consistent
ordering by activity type, then descending number)" while §5 of
`eval_rule.md` graded highlights against `ground_truth.highlights` in
strict order. The 2026-04-22 entries (issue #27 by `dave`,
pr #13 by `carol`) share a date, and a correct executor that picked a
type-first tie-break (PR before issue) would mis-order the section
relative to GT and lose the 0.20 highlight checkpoint.

Fix is on the prompt side only (no GT, eval_rule, score-cap, or
success-threshold change): the public prompt now states the exact
tie-break used to capture GT — "list the higher-numbered activity first
(so number 27 comes before number 13); if the numbers also tie, list
the issue before the pull request." Applied identically to both
`task` and `task_snapshot` blocks so live-API and snapshot runs share
the rule.

## Review pass (2026-04-30)

User feedback (review_record.md task 19): "确保 snapshot 仅在 SNAPSHOT_MODE
下注入；split live-API vs snapshot；检查 API 是否通顺." Applied:

1. **Prompt rewrite (English, both modes)**.
   - `task` (live-API mode): now explicitly requires the executor to
     authenticate with `$GITHUB_TOKEN` and hit the live REST API via the
     `gh` CLI or direct `api.github.com` calls, and explicitly forbids
     reading the local snapshot file or any pre-exported cache for that
     run. First paragraph names the github skill ("use the github skill in
     our workspace"). No parentheses, no rubric keyword leakage. STRICT
     coverage requirement is implicit ("Cover the full set of contributors
     and activity, not a partial sample").
   - `task_snapshot`: continues to be a cleanly separated branch — reads
     `/tmp_workspace/clawbench/sources/github_activity_snapshot.json` only,
     "Do not call the live GitHub API." Same skill mention in the first
     paragraph. Same tie-break and STRICT coverage wording.

2. **Eval contract (`eval_rule.md`)**.
   - §2 rewritten to call out the two modes explicitly: live-API mode
     requires hitting `api.github.com`; snapshot mode reads the JSON file.
   - §5 tightened to STRICT (per global rule 8): per-contributor coverage
     must include ALL 5 contributors (not "at least N"); contributor stats
     must EXACTLY match GT for EVERY contributor; Follow-up Flags must
     include EVERY closed-unmerged PR and EVERY revert entry; CSV row
     count must EXACTLY equal `activity_index_expected_rows` (64).
   - §6 new cap: live-API mode bypass — if `SNAPSHOT_MODE` is unset and
     `$GITHUB_TOKEN` is available but the executor reads the snapshot file
     instead of hitting the live API, total is capped at 0.50. This is a
     net-new failure-mode cap (per global rule 11 "new caps OK"); existing
     caps unchanged.
   - §5 sum verified = 1.00 (0.20+0.20+0.10+0.20+0.15+0.10+0.05).

3. **Populator unchanged**. The existing `populate.py` already does
   GET-then-PUT-with-sha (with a 422-retry path for GitHub eventual
   consistency on the contents API), clean-rebuilds the fixture repo
   when `SNAPSHOT_MODE` is unset, and emits both the snapshot file and
   the GT JSON. No changes required for this review pass.

4. **GT unchanged**. GT was already aligned with the live-API renumbered
   PRs (1-15) and the 16-day window ending at `generated_at`; no anchors
   needed adjustment for the prompt/eval changes.
