# Hidden Evaluation Rule — task_205_21_nextjs_learning_path

## 1. Grading Philosophy

Grade on whether the deliverables answer the user's actual question:
"compare Next.js v15.3.1 with v15.3.0, then rank these YouTube tutorials by
recency and topic-coverage so I know what to study first." The executor is
free to choose filenames, JSON shape, and intermediate methodology. What
matters is that the final artefacts (a) are present, (b) carry the correct
anchor facts (release dates, video IDs/metadata, topic-coverage ordering),
and (c) the analysis is grounded in real fetched data, not invented.

Anchor facts come from `ground_truth.json` and reference immutable
historical state on 2026-05-02: the v15.3.0 / v15.3.1 release pair,
the immutable v15.3.1 commit SHA, and 5 specific YouTube video IDs
whose static metadata does not change.

## 2. Task Contract

The user wants:
- A version comparison covering both v15.3.0 and v15.3.1 (peer deps,
  release timing, sense of "release notes shrunk vs grew").
- A ranking of the 5 YouTube tutorials by recency, with some way to flag
  which one is most relevant to v15.
- A learning-path / study-plan document tying it all together.

Required deliverables (any sensible filename under `/tmp_workspace/results/`):
- A **structured data file** (JSON or equivalent) carrying both versions'
  release metadata and the per-video analysis.
- A **video ranking file** (CSV / table / or table embedded in the report)
  that orders the 5 videos by upload date, newest first.
- A **learning-path document** (markdown) with the comparison conclusion +
  recommended study order.

NO snapshot file. NO mock service. NO populate step. Executor must hit
live APIs.

## 3. Source-Selection Rules

Sensible source choices include but are not limited to:
- GitHub releases via `gh api repos/vercel/next.js/releases/tags/...`
- npm metadata via `npm view next@<ver> --json`
- YouTube video metadata + auto-subs via `yt-dlp`
- Optionally curl on raw.githubusercontent.com for upgrade docs / changelog

The executor may use other reasonable methods (e.g. parsing the GitHub
release body directly for breaking-change context) — the grader checks
**facts**, not call signatures.

`GITHUB_TOKEN` is set in the executor's environment.

## 4. Ground-Truth Anchors

From `references/ground_truth.json`:
- v15.3.0 published 2025-04-09, v15.3.1 published 2025-04-17 (~7 days apart)
- peer deps unchanged across this patch (same 6 keys both sides)
- v15.3.1 commit SHA `fa536cf2c94475cecb7585680c5d96e35e00ba7b`
- 5 video IDs with fixed (duration_seconds, upload_date)
- The v15-era video (uploaded after 2024-10-21 v15.0.0 release):
  `Zq5fmkH0T78` only
- Highest v15 topic-coverage video: `Zq5fmkH0T78` (the JavaScript Mastery
  v15 crash course, ~5h 23m, covers 6 of 7 v15 keywords)
- Upload-date-desc order: Zq5fmkH0T78, ZVnjOPwW4ZA, _w0Ikk4JY7U,
  mTz0GXj8NN0, Sklc_fQBmcs

## 5. Checkpoint Rubric

Weights sum to 1.0. Each checkpoint is graded on whether the **deliverable
achieves the goal**, not on field-name compliance. Use jq / grep / regex
flexibly; accept multiple JSON shapes and multiple filenames.

- 0.13 — **Both versions appear with correct release dates.** The data
  artefact contains v15.3.0 published_at = 2025-04-09 (date or full
  ISO timestamp; "2025-04-09T20:19:59Z" exact OR just "2025-04-09" both
  acceptable) AND v15.3.1 published_at = 2025-04-17. Either GitHub-style
  or npm-style timestamps count. Partial 0.06 if only one of the two is
  correct.

- 0.09 — **Peer dependencies for both versions present and identified as
  unchanged.** The artefact lists peer deps for both versions (the 6 keys:
  @opentelemetry/api, @playwright/test, babel-plugin-react-compiler,
  react, react-dom, sass) AND somewhere the analysis notes the peer deps
  are the same / unchanged across v15.3.0 → v15.3.1 (any phrasing:
  "unchanged" / "no change" / "identical" / 数组相等 / `peer_dependencies_unchanged: true`
  field / etc.). Partial 0.04 if peer deps appear but the unchanged
  conclusion is not explicit.

- 0.09 — **Release-notes size delta is correctly characterised.** Either
  the data artefact carries a numeric word-count delta (negative number
  with magnitude > 1000, indicating v15.3.1 is much shorter), OR the
  report-style conclusion explicitly states v15.3.1's release notes are
  much shorter / smaller / 瘦 / 缩水 / patch-style vs v15.3.0's full release.
  Both forms accepted.

- 0.13 — **Video metadata is correct for all 5 videos.** Each of the 5
  expected `video_id` strings appears (Sklc_fQBmcs, _w0Ikk4JY7U,
  ZVnjOPwW4ZA, mTz0GXj8NN0, Zq5fmkH0T78) AND each has its correct
  `upload_date` (YYYYMMDD or YYYY-MM-DD format both acceptable; date
  values must match ground_truth). Per-video duration in seconds within
  ±2 of expected accepted. Partial: ≥ 4 of 5 videos correct → 0.06.

- 0.13 — **Ranking by upload date is correct.** The video-ranking
  artefact (CSV, table in markdown, or JSON array — any form) orders the
  5 videos newest-to-oldest as: Zq5fmkH0T78, ZVnjOPwW4ZA, _w0Ikk4JY7U,
  mTz0GXj8NN0, Sklc_fQBmcs. Partial 0.06 if ordering is reversed
  (oldest-to-newest) but otherwise correct.

- 0.13 — **The most-recent / highest v15-relevance video is correctly
  identified as the recommended starting point.** The learning-path
  document must clearly recommend `Zq5fmkH0T78` (or the JavaScript
  Mastery v15 crash course title) as the top-recommended / first /
  most-relevant tutorial. Acceptable signals: explicit "建议先看" /
  "推荐第一个看" / "start with" / "begin with" / "排第一" / "rank 1"
  attached to that video.

- 0.10 — **Per-video v15 topic coverage analysis is present.** Each video
  has some indicator of how much v15 content it covers (a coverage score,
  a list of topics hit, a paragraph, etc.). The relative ordering must
  preserve `Zq5fmkH0T78` as the highest-coverage video (strict). Other
  videos may differ in absolute scores but Zq5fmkH0T78 is the strict max.

- 0.10 — **Per-video subtitle keyword analysis is present and correct.**
  The executor must have actually pulled the English auto-subs for all 5
  videos (5 `*.vtt` files visible in `/tmp_workspace/results/` OR an
  equivalent per-video transcript file count of 5; a trace showing
  `yt-dlp --write-auto-subs ... --sub-lang en` for the 5 video IDs is
  also acceptable). The data artefact carries a per-video × per-keyword
  count matrix covering the 7 keywords (`async`, `react 19`, `fetch`,
  `cookies`, `headers`, `params`, `router cache`) — case-insensitive
  substring matches accepted. The report / data must explicitly identify
  `Zq5fmkH0T78` as the video with the **deepest v15 coverage** based on
  the subtitle analysis (it covers 6 of the 7 keywords vs ≤3 for any
  other video, and dwarfs the others on total occurrences — both
  `topics_covered` and `total_occurrences` are stable rank-1 properties
  even if absolute counts drift across yt-dlp player versions). Partial
  0.05 if subtitle files exist for ≥4 of 5 videos and counts are
  present but the explicit "deepest coverage" identification is missing
  or wrong. Partial 0.03 if only 1 or 2 videos have subtitle data.

- 0.10 — **Learning-path document is present and substantive.** Markdown
  file exists; mentions both "v15.3.0" and "v15.3.1" version strings;
  includes per-video commentary (~5 video segments or per-video bullets);
  ends with a recommended learning order or study plan section.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- Neither structured data file nor video ranking produced → 0.30.
- Output fabricates videos / values / fails to fetch v15.3.0 (only
  v15.3.1 anchors present) → 0.50.
- `$GITHUB_TOKEN` value emitted to user-visible output → 0.30.
- Trace shows zero gh / yt-dlp / npm / curl calls (synthetic data
  only) → 0.40.
- All 5 videos missing from output → 0.40.

Pass requires the version-dates checkpoint (0.13) AND the ranking
checkpoint (0.13) AND the v15-recommendation checkpoint (0.13) all
satisfied AND the learning-path document present.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to fix
  the lowest-scoring deliverable.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

Release dates, peer-deps lists, commit SHA, and video IDs / static
metadata are all immutable historical state. View counts and engagement
metrics ARE dynamic and are intentionally not graded.

YouTube auto-subs (if used) are generated server-side by Google's ASR
and may drift slightly between yt-dlp player versions. The grader does
not require an exact subtitle word count — only that the **rank order**
of v15-relevance places `Zq5fmkH0T78` strictly highest is preserved
(this is a much more stable property than absolute counts).

If GitHub / npm / YouTube APIs are temporarily unavailable, the
supervisor MUST distinguish "executor failed" from "API outage". A
trace showing repeated 5xx responses is an outage, not an executor
failure — record `infra_error` in summary and avoid penalising.
