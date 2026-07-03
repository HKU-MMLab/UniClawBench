# Hidden Evaluation Rule — task_205_35_rss_hn_weekly_pdf

## 1. Grading Philosophy

Grade on whether the executor performed a real cross-platform workflow
that combines (a) curl/newsboat against 5 stable RSS feeds (current
contents — Q1 2026 articles will not be present by 2026-05-02 because
RSS feeds carry only the most-recent ~10 entries; this is the realistic
constraint, NOT a bug), (b) HN Algolia REST search API for Q1 2026
top 20 stories (HN's full historical corpus is queryable, so this part
IS deterministic), (c) per-URL cross-reference + overlap_rate
computation (expected ≈ 0 because the time windows don't intersect),
(d) lightweight topic clustering on combined titles, (e) ImageMagick
(or matplotlib / gnuplot) bar chart for topic frequency, (e2) per-feed
editorial-slant classification across 4 categories
(security/tech/business/lifestyle) AND a stacked-bar positioning chart,
(f) **pandoc + xelatex Markdown→PDF rendering with a real multi-page
polished layout (cover + TOC + topic sections + Feed Positioning
section + 2 embedded charts)** — not a flat 1-page text dump, (g)
Evince GUI screenshot via xvfb. The PDF formatting depth is the
platform value here.

Anchor checks against `ground_truth.json` — the HN objectIDs/points
for Q1 2026 are HISTORICAL (after 2026-04-01) and therefore frozen.
Score caps in §6 override rubric totals.

**Realistic-data note 2026-05-03**: the `q1_articles` per feed is
EXPECTED to be empty / near-empty at grading time because RSS feeds
do not retain ~5 months of history. This is a known design decision,
not a bug — the eval grades the PIPELINE (executor correctly notes
zero, computes overlap_rate=0, and the PDF still renders the
non-empty parts). The executor is expected to ALSO emit a
`current_articles` field per feed (the feed's currently available
items, regardless of date) so the Feed Positioning slant analysis has
real titles to classify. See §5 for the loosened acceptance.

## 2. Task Contract

The user wants a Q1-2026 tech-news report PDF that cross-references
5 RSS feeds with HN top 20 stories AND is rendered as a polished
multi-section document (cover, TOC, topic chapters, embedded chart).
NO snapshot file, NO mock, NO populate step.

Required deliverables:

- `/tmp_workspace/results/feed_articles.json` — JSON with `feeds` as
  a 5-element list in the order
  HN-RSS → Lobsters → Ars Technica → The Hacker News → Wired.
  Each item has `url`, `q1_articles` (list of `{title, link,
  pub_date}` filtered to pub_date in 2026-01-01 ≤ d < 2026-04-01 UTC —
  expected EMPTY by 2026-05-02 because RSS feeds rotate items out
  within weeks), AND `current_articles` (list of the feed's currently
  available items regardless of date — expected ≈ 10 entries per
  feed, used by the per-feed slant classification in §5). The
  `current_articles` field is REQUIRED so the slant classification has
  real data; if the executor only emits `q1_articles` and skips
  `current_articles` entirely, the supervisor falls back to inspecting
  `feed_positioning.json` independently and §5 still grades.
- `/tmp_workspace/results/hn_top_stories.json` — JSON with `period`
  == "2026-Q1" and `top_stories` as a 20-element list, sorted by
  points DESC then created_at DESC. Each item has objectID, title,
  url, points, num_comments, created_at.
- `/tmp_workspace/results/overlap_summary.json` — JSON with
  `hn_total` == 20, `hn_with_rss_match` (count of HN top-20 stories
  whose `url` appears in any RSS feed's `q1_articles[*].link`),
  `overlap_rate` == hn_with_rss_match / 20.
- `/tmp_workspace/results/topics.json` — JSON with `top_3_topics` as
  a 3-element list of `{topic, approx_count}`. Topics extracted from
  combined HN top-20 + all RSS article titles.
- `/tmp_workspace/results/topic_chart.png` — bar chart, width ≥ 400
  px, height ≥ 200 px. Must be referenced from the markdown source
  so pandoc embeds it into the final PDF.
- `/tmp_workspace/results/feed_positioning.json` — per-feed editorial
  slant. JSON with `per_feed` as a 5-element list. Each entry has
  `url`, `category_distribution` (dict of 4 floats summing to 1.0
  ±0.01 across security/tech/business/lifestyle), `dominant_category`
  (one of those 4 keys), and `total_classified` (int). Order
  must match `ground_truth.rss_feed_urls_ordered`.
- `/tmp_workspace/results/feed_positioning_chart.png` — stacked bar
  chart, width ≥ 500 px, height ≥ 300 px, 5 bars (one per feed),
  4 stacked colors (one per category). Must be referenced from the
  markdown source so pandoc embeds it as the second image.
- `/tmp_workspace/results/weekly_report.pdf` — pandoc + xelatex
  generated PDF. Page count ≥ 3. pdfinfo reports valid PDF.
  pdftotext extracts:
  - "2026" AND "Q1" (cover)
  - at least 2 of the 3 topic strings from `topics.json` (chapter
    headings)
  - "overlap" or "Overlap" or the numeric overlap_rate (closing
    stats)
  - "Feed Positioning" section heading (case-insensitive substring)
  pdfimages -list reports ≥ 2 embedded images (topic chart +
  feed_positioning chart).
- `/tmp_workspace/results/evince_screenshot.png` — non-empty PNG
  showing Evince viewer.

## 3. Source-Selection Rules

Canonical sources are LIVE:
- RSS: `curl <feed_url>` for each of the 5 URLs in
  `ground_truth.rss_feed_urls_ordered`
- HN Algolia search: `curl 'https://hn.algolia.com/api/v1/search'
  --data-urlencode 'tags=story' --data-urlencode
  'numericFilters=created_at_i>=1767225600,created_at_i<1775001600'
  --data-urlencode 'hitsPerPage=30'` and locally sort/take top 20
- ImageMagick / matplotlib / gnuplot for the bar chart
- pandoc → PDF via xelatex (texlive-xetex, fonts-noto-cjk)
- Evince + xvfb-run + scrot/import for the screenshot

NO snapshot file. NO mock. Reading from any local fixture under
`/tmp_workspace/clawbench/` is undefined behaviour.

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json`. Key
anchors:

- `period_unix_range` = 1767225600 ≤ created_at_i < 1775001600
- `rss_feed_urls_ordered` — exact 5-element list
- `hn_top_20_q1_2026_object_ids_set` — exact 20-element set of
  immutable HN objectIDs. Q1 2026 ended 2026-04-01, points frozen.
- `hn_top_20_q1_2026_ordered_by_points_desc_then_created_at_desc` —
  authoritative ranking
- `expected_overlap_rate.value` = 0.0 ± 0.05 (RSS items have rotated
  out of Q1 by 2026-05-02)
- `expected_top_3_topics_keywords_any_2_required` — at least 2 of the
  3 reported topics must contain (case-insensitive substring) one of
  the listed AI/tech keywords

## 5. Checkpoint Rubric

Weights sum to 1.0. (9 weighted checkpoints.)

- 0.04 — `feed_articles.json` parses; `feeds` has exactly 5 items in
  the exact URL order specified in
  `ground_truth.rss_feed_urls_ordered`. `q1_articles` MUST exist as a
  list per feed (empty list is the expected/correct answer by
  2026-05-02). Acceptable to ALSO have `current_articles` per feed
  with the live feed contents (~10 entries) — recommended but not
  scored on this checkpoint; the slant analysis in the
  feed_positioning checkpoint will expect either `current_articles`
  OR will independently re-fetch the feed.
- 0.18 — `hn_top_stories.json` parses; `period` == "2026-Q1";
  `top_stories` has exactly 20 items; the SET of `objectID` values
  equals `ground_truth.hn_top_20_q1_2026_object_ids_set`; the
  top item's objectID == "47340079" (highest-points anchor at 4229).
  Ranking matches
  `ground_truth.hn_top_20_q1_2026_ordered_by_points_desc_then_created_at_desc`
  (rank-by-rank). Tolerate the listed tied-pair swap (ranks 8/9).
- 0.05 — `overlap_summary.json` parses; `hn_total` == 20;
  `hn_with_rss_match` is a non-negative integer; `overlap_rate` ==
  `hn_with_rss_match / 20` (within 0.001) AND `overlap_rate` ∈
  [0.0, 0.20] (loosened bound). The realistic answer at 2026-05-02 is
  `overlap_rate` ≈ 0 because Q1 RSS articles are no longer in any
  feed by then. The bound is widened upward to 0.20 (= 4/20) to
  tolerate (a) executors that match HN URLs against `current_articles`
  rather than `q1_articles`, OR (b) tied URL formats / WWW prefix
  reductions producing accidental matches. ANY overlap_rate in [0,
  0.20] is correct; a value > 0.20 indicates fabrication and fails
  the checkpoint.
- 0.09 — `topics.json` parses; `top_3_topics` has exactly 3 items,
  each with a non-empty `topic` string. At least 2 of the 3 topics
  (case-insensitive substring) match one of
  `expected_top_3_topics_keywords_any_2_required`.
- 0.09 — **Topic temporal precedence present (methodology check).**
  Each of the 3 entries in `topics.json.top_3_topics` carries the THREE
  precedence-related fields: `rss_first_date` (string or null),
  `hn_first_date` (string or null), `lead_time_days` (signed int/float
  or null). The `lead_time_days` MUST equal
  `hn_first_date - rss_first_date` in days WHEN BOTH dates are
  non-null (±2 days tolerance for tz/parse drift); if either
  source-date is null then `lead_time_days` may be null. The top-level
  `most_rss_first_topic` field exists and is either (a) a string
  matching one of the 3 topic strings (case-insensitive), or (b)
  `null` if every topic has null `lead_time_days`. Anchor at
  2026-05-02: live RSS feeds carry only April-May 2026 articles while
  HN top-20 covers Jan-Mar 2026 — these windows do not overlap, so
  `rss_first_date` will be null for HN-derived Q1 topics. The most
  realistic correct answer is `most_rss_first_topic = null`, with all
  3 topics having `rss_first_date = null` and `lead_time_days = null`.
  Both null answers AND any non-null defensible answer are accepted as
  long as the arithmetic check holds where dates ARE provided. This
  is a METHODOLOGY check (3 fields per topic + top-level field
  present), not a specific value answer.
- 0.08 — `topic_chart.png` exists AND is a valid PNG AND width ≥
  400 px AND height ≥ 200 px AND has at least 2 distinct non-white
  colors (proves it's a chart, not a blank canvas).
- 0.26 — **PDF formatting depth** (the headline checkpoint).
  `weekly_report.pdf` exists AND `pdfinfo` reports it as a valid PDF
  AND Pages ≥ 3 AND pdftotext extracts:
  (a) BOTH "2026" AND "Q1" (cover),
  (b) at least 2 of the 3 topic strings from topics.json (chapter
      headings — case-insensitive substring),
  (c) "overlap" / "Overlap" / numeric overlap_rate value (closing
      stats),
  (d) "Feed Positioning" / "feed positioning" / "FEED POSITIONING"
      section heading (case-insensitive substring),
  AND `pdfimages -list weekly_report.pdf` reports ≥ 2 embedded
  images (topic chart + feed_positioning chart). All 5
  sub-conditions required. Half credit (0.13) if the PDF satisfies
  (a)+(b)+(c) AND has ≥ 1 image but is missing the Feed Positioning
  heading OR the second embedded image.
- 0.09 — `evince_screenshot.png` exists AND is a valid PNG of size
  > 0.

- 0.12 — **Per-feed editorial slant analysis present and grounded.**
  Source data: the executor classifies titles from each feed's
  CURRENT contents (`feed_articles.json.feeds[i].current_articles[*].title`
  if present, otherwise from a re-fetch of the live feed). NOT from
  `q1_articles` (which is empty by 2026-05-02). The slant analysis
  is therefore grounded on what the feed actually serves on grading
  day — the 2 anchor-feed dominant calls are stable enough across
  feed drift that this remains deterministic in the rough sense.
  `feed_positioning.json` parses AND `per_feed` is a 5-element list
  in the exact URL order specified in
  `ground_truth.rss_feed_urls_ordered` AND each entry has a
  `category_distribution` dict with the 4 keys
  {`security`, `tech`, `business`, `lifestyle`} whose values sum to
  1.0 ±0.01 AND a `dominant_category` field set to the key with the
  highest fraction in that dict AND a `total_classified` int ≥ 1.
  AND the dominant_category for `https://feeds.feedburner.com/TheHackersNews`
  is `"security"` AND the dominant_category for
  `https://www.wired.com/feed/rss` is `"lifestyle"` (the two extreme
  anchor feeds — TheHackersNews titles are dominated by
  CVE/breach/hack content, Wired's feed is dominated by reviews/gifts/
  promo content; both unlikely to flip under future feed drift). The
  3 mixed-tech feeds (HN/Lobsters/Ars Technica) are NOT anchor-checked
  for dominant call (executor's keyword list may classify them as
  `tech` or one of the other 3 — any consistent call accepted).
  Half credit (0.06) if `feed_positioning.json` parses with the right
  structure but only ONE of the 2 anchor-feed dominant calls matches.
  AND `feed_positioning_chart.png` exists AND is a valid PNG AND
  width ≥ 500 px AND height ≥ 300 px AND has ≥ 4 distinct non-white
  colors (proves it's a stacked bar with multiple categories
  rendered, not a flat single-color bar).

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- `weekly_report.pdf` is empty / corrupted / not produced by pandoc
  → 0.40.
- `weekly_report.pdf` Pages == 1 (executor produced a single-page
  text dump, no real layout) → cap 0.55.
- `weekly_report.pdf` has fewer than 2 embedded images (charts not
  both embedded) → cap 0.70.
- `top_stories` set differs from ground_truth (executor invented or
  wrong-period stories, or grabbed only top 10 instead of 20) → 0.40.
- Trace shows zero curl / newsboat / pandoc calls (synthetic data
  only) → 0.30.
- Fewer than 5 feeds in `feed_articles.json` → cap 0.55.
- `topic_chart.png` missing → cap 0.70.
- `feed_positioning.json` missing entirely → cap 0.80.
- `feed_positioning_chart.png` missing → cap 0.78.
- "Feed Positioning" section heading absent from PDF → cap 0.82.

Pass requires the HN-objectID-set + ranking checkpoint AND the
overlap-summary checkpoint AND the PDF formatting depth checkpoint
AND the per-feed editorial-slant checkpoint all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to
  fix the lowest-scoring deliverable (often the PDF formatting,
  the topic clustering, or the chart embedding).
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

Q1 2026 ended 2026-04-01, so HN points / num_comments and the top-20
set are now frozen. The 5 RSS feeds carry only the latest ~10 entries;
by 2026-05-02 the in-Q1 articles have already rotated out, so empty
`q1_articles` per feed is expected and not penalised. The crossref
overlap is therefore expected to be near 0; that is intentional. The
PDF + topic chart is about the TOOLCHAIN and FORMATTING running
end-to-end, not the content density.

Per-feed editorial-slant classification uses live current titles per
feed (Q1 is empty by reference date, so the executor must use what's
currently in the feed). The 2 anchor dominant-category calls (
TheHackersNews → security, Wired → lifestyle) are extreme enough to
remain stable under future feed drift; the other 3 mixed-tech feeds
(HN/Lobsters/Ars Technica) are not anchor-checked. The category
keyword lists in the prompt are seeds — the executor may extend
them, but the dominant call must still match for the 2 anchor feeds.

If the HN Algolia API or RSS feeds are temporarily unavailable, the
supervisor MUST distinguish "executor failed" from "API outage". A
trace showing repeated 5xx responses is an outage, not an executor
failure — record `infra_error` in summary and avoid penalising.
