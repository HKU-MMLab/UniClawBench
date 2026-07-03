# Hidden Evaluation Rule — task_105_32_react_versions_libreoffice

## 1. Grading Philosophy

Grade on whether the executor (a) hit live `gh` for the latest stable
`facebook/react` release as of `2026-04-25`, defined as the newest
non-prerelease release published before `2026-04-25T00:00:00Z`, and the
per-major release dates, (b) hit `yt-dlp` for 8 YouTube video metadata,
(c) computed
`gap`/`video_lag_days`/`freshness_score`/`risk_level` correctly per
video, AND (d) produced a **real LibreOffice Calc spreadsheet** with
formulas + conditional formatting on the risk column, AND (e)
embedded a bar chart object directly into the .ods (odfpy / hand-XML
/ soffice macro). Score caps in §6 override rubric totals.

## 2. Task Contract

Required deliverables under `/tmp_workspace/results/`:

- `verification.json` — JSON with `current_react` (must have `tag` and
  `major`) AND a `videos` array of 8 records (in prompt order). Each
  video must have `video_id`, `video_major`, `gap`, `video_lag_days`,
  `freshness_score`, `risk_level`.
- `version_check.ods` — LibreOffice/OpenDocument spreadsheet, real ODF
  zip containing:
  * 8 video data rows + header;
  * columns including (substring match, any order) `video_id`,
    `video_major`, `gap`, `video_lag_days`, `freshness_score`,
    `risk_level`;
  * **at least 1 formula cell** (`<table:table-cell table:formula="...">`);
  * **conditional formatting rule** on the risk_level column (a
    `style:conditional-format` / `calcext:conditional-format` block);
  * **embedded chart object** referenced from the spreadsheet's
    main `content.xml` via `<draw:object>` markup (odfpy / hand-XML
    / soffice macro path).

There is NO snapshot file, NO mock service. `sources: []` is intentional.
`GITHUB_TOKEN` is set in the executor's environment via `.privacy`.

## 3. Source-Selection Rules

- GitHub: `gh api "repos/facebook/react/releases" --jq
  '[.[]|select(.published_at < "2026-04-25T00:00:00Z" and
  (.tag_name | startswith("v")) and (.prerelease|not))][0]'`
- Per-major release dates:
  `gh api "repos/facebook/react/releases/tags/v16.0.0"` (and 17/18/19)
  — extract `published_at`.
- YouTube: `yt-dlp -j https://www.youtube.com/watch?v=<id>` for
  metadata.
- LibreOffice — `.ods` authoring path: any technique that produces
  a real .ods with formula cells, conditional formatting, AND an
  embedded chart object (headless `odfpy`, `pyexcel-ods3`,
  hand-written xml then `zip -X`, or `soffice --headless` Basic
  macro). Bare CSV converted via `soffice --convert-to ods` fails
  the platform-depth checks.

NO snapshot under `/tmp_workspace/clawbench/` is used or expected.

## 4. Ground-Truth Anchors

Structured expected answer at `references/ground_truth.json`:

- As of `2026-04-25T00:00:00Z`, `current_react.tag` = `"v19.2.5"`,
  `current_react.major` = `19`.
- React major release dates: 16 → 2017-09-26, 17 → 2020-10-20,
  18 → 2022-03-29, 19 → 2024-12-05.
- 8 videos with exact `(video_id, video_major, gap, video_lag_days,
  freshness_score, risk_level)` tuples.
- `risk_level` mapping: gap 0 → `"low"`, 1 → `"medium"`, ≥2 → `"high"`.
- `freshness_score = max(0, 1 - gap*0.2)`.
- Average freshness across 8 videos = 0.7, gap=0 video count = 2.

## 5. Checkpoint Rubric

- 0.09 — `verification.json` parses; `current_react.tag == "v19.2.5"`
  AND `current_react.major == 19`.
- 0.22 — `videos` array length == 8 AND for each of the 8 video IDs
  the quintuple `(video_major, gap, video_lag_days, freshness_score,
  risk_level)` matches `ground_truth.videos` exactly. Tolerance: 0 for
  ints (`video_major`, `gap`, `video_lag_days`); ±0.01 for
  `freshness_score`; exact string for `risk_level`.
- 0.13 — `version_check.ods` is a valid ODF zip (`unzip -l` shows
  `content.xml` and `mimetype` =
  `application/vnd.oasis.opendocument.spreadsheet`), header includes
  the 7 required column names (substring match: `video_id`,
  `video_major`, `gap`, `video_lag_days`, `freshness_score`,
  `risk_level`, `router_compat_major`), data region has all
  8 video_ids and the per-video (gap, freshness_score, risk_level)
  triples match the JSON.
- 0.18 — **Formula present**: `unzip -p version_check.ods content.xml |
  grep -c 'table:formula'` ≥ 1 — at least one
  `<table:table-cell table:formula="...">`. Acceptable shapes:
  `of:=AVERAGE(...)`, `of:=SUM(...)`, `of:=IF(...)`,
  `of:=COUNTIF(...)`, `=AVERAGE(...)` (legacy).
- 0.13 — **Conditional formatting present**:
  `unzip -p version_check.ods content.xml styles.xml 2>/dev/null |
  grep -E -c 'conditional-format|calcext:condition'` ≥ 1.
  Presence of any conditional-format rule is sufficient (the user
  wants high-risk rows highlighted; the executor may choose any visible
  style).
- 0.13 — **Embedded chart object present in .ods.**
  `unzip -p version_check.ods content.xml | grep -c 'draw:object'`
  ≥ 1 — the spreadsheet's main `content.xml` references at least
  one embedded chart frame via `<draw:object>` markup. The
  programmatic odfpy / hand-XML chart path is the canonical way to
  satisfy this — `unzip -l version_check.ods` typically also lists
  an `Object N/` directory whose `content.xml` carries
  `<chart:chart>` / `<chart:plot>` markup, but the load-bearing
  check is the parent `content.xml`'s `draw:object` reference.
- 0.12 — **react-router compatibility column present.** EACH of the 8
  records in `verification.json.videos` has a `router_compat_major`
  integer field (4 / 5 / 6 / 7), AND the `version_check.ods` data
  region contains a `router_compat_major` column (header substring
  match) populated with integer values for all 8 rows. Per-video
  expected `router_compat_major` values (anchor at 2026-05-02, derived
  from `npm view 'react-router' time --json` major .0.0 dates
  RR4=2017-03-11, RR5=2019-03-18, RR6=2021-11-03, RR7=2024-11-22 +
  `npm view 'react-router@<n>' peerDependencies` checks):
    * uN0dioTiAwI (React 16, upload 2017-12-11) → expected 4
    * BnasObkCGtQ (React 16, upload 2018-10-25) → expected 4
    * _B7pGf8QJWo (React 17, upload 2020-09-11) → expected 5
    * N0DhCV_-Qbg (React 18, upload 2022-03-29) → expected 6
    * dCLhUialKPQ (React 19, upload 2025-01-24) → expected 7
    * TtPXvEcE11E (React 19, upload 2025-09-15) → expected 7
    * 8D-rWP3c088 (React 17, upload 2020-09-28) → expected 5
    * jLS0TkAHvRg (React 18, upload 2022-04-10) → expected 6
  Tolerance: each video's reported `router_compat_major` MUST be within
  ±1 of the expected value (so React 18 video may pick 5/6/7; React 19
  may pick 6/7; React 17 may pick 4/5/6; React 16 may pick 3/4/5). At
  least 6 of 8 videos must satisfy the ±1 tolerance for full credit;
  4-5 of 8 → half credit (0.06); fewer than 4 → 0. Any video reporting
  a non-integer or value outside {3,4,5,6,7} is counted as a miss.

## 6. Scoring Policy / Score Caps

- Output fabricates videos / values not derivable from live APIs → 0.40.
- Trace shows zero `gh` or `yt-dlp` calls (synthetic data only) → 0.40.
- `version_check.ods` exists but `unzip` fails → cap §5 .ods
  checkpoints at 0.
- `version_check.ods` was produced by `soffice --headless --convert-to
  ods` on a CSV with NO post-processing AND has 0 formulas / 0
  conditional formats → cap §5 platform-depth checkpoints (formula,
  conditional formatting) at 0 each (no global cap).
- No programmatic chart object embedded in `version_check.ods`
  (`grep -c 'draw:object' content.xml` returns 0) → cap §5 chart
  checkpoint at 0; no global score cap.
- `$GITHUB_TOKEN` value emitted to user-visible output → 0.30.
- Per-major release dates were not actually fetched (executor
  hard-coded them with no `gh api releases/tags/v...` trace) → 0.55.

Pass requires ≥ 0.90 — i.e. all 7 checkpoints satisfied OR 6 satisfied
plus near-miss on one of the platform-depth checks.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to
  add the missing platform feature (formula, conditional formatting,
  chart object) into the .ods.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All version-related anchors are immutable under the `2026-04-25` as-of
snapshot — the React `v19.2.5` release is fixed in GitHub's release
history and is the latest non-prerelease before `2026-04-25T00:00:00Z`;
per-major release dates are immutable; the 8 YouTube video IDs have
static metadata.

If GitHub or YouTube APIs are temporarily unavailable, the supervisor
distinguishes "executor failed" from "API outage" — repeated 5xx is
`infra_error`, not penalised.
