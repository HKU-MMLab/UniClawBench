# Hidden Evaluation Rule — task_201_37_blog_from_data

## 1. Grading Philosophy

Judge whether the public request was completed end-to-end: a publishable
blog post, a usable cover image, and a formula-backed analysis workbook
that all agree on the same three concrete callouts. The declared skills
under `/root/skills/` should be genuinely consulted; their absence
in the trace is treated as an extreme failure (see §6).

Prefer semantic matching over exact-string matching for blog phrasing
when the user's plain-language request would not pin down a particular
wording. Score caps in §6 override rubric totals.

All §5 checkpoints are strict and all-or-nothing — if the public
prompt names a set of items, partial coverage scores 0 on that line.

## 2. Task Contract

The executor must produce, from `monthly_sales_2010.csv`, three
deliverables under `/tmp_workspace/results/`:

- `post.md` — ~800-word newsletter blog grounded in three concrete
  business callouts computed from the CSV, including a short
  conclusion or recommendation.
- `cover.png` — a valid PNG combining bar and line chart elements,
  usable as the post's cover image.
- `analysis.xlsx` — workbook with `Monthly`, `Store_Summary`, and
  `Callouts` sheets; MoM revenue change, share-of-total revenue,
  store peak months, and the Callouts rows must be formula-backed
  with cell references back to calculation sheets.

The public prompt is authoritative for scope; nothing in
`references/` may be used to expand it.

## 3. Source-Selection and Target-Resolution Rules

The canonical input is the single CSV at
`/tmp_workspace/clawbench/sources/monthly_sales_2010.csv` — UCI
Online Retail II (Chen 2019, CC-BY 4.0) 2010 transactions aggregated
by month x top-3 country (36 rows; GBP->USD at the 2010 mid-year
reference rate 1.545).

Anything the executor invents or pulls from outside this file is not
input data; numerical claims in the post and workbook must be
derivable from this CSV.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema a: concept-level booleans with evidence pointers).

Key reference values (verified against the canonical CSV):

- Total revenue (USD): 13,457,369.32
- Total orders: 18,153
- Peak month all-store row: 2010-11, all-store revenue 2,074,426.98 USD,
  all-store orders 2,584. UK contribution that month: 1,970,772.86 USD,
  2,520 orders, 95.00% share of November.
- Stores: United Kingdom, EIRE, Netherlands
- Country shares of full-year revenue: UK 92.9456%, EIRE 4.1431%,
  Netherlands 2.9113%
- EIRE peak month: 2010-01 ($100,824.27)
- Required `Monthly` columns: month, total_revenue, total_orders,
  average_order_value, mom_revenue_change
- Required `Store_Summary` columns: store, revenue, orders,
  share_of_total_revenue, peak_month

Equivalent callouts that are equally well-supported by the CSV may
receive credit even if they are not in the required-metric list.

## 5. Checkpoint Rubric

Weighted checkpoints, total = 1.00 (0.10 + 0.16 + 0.05 + 0.15 + 0.10
+ 0.05 + 0.16 + 0.10 + 0.08 + 0.05). All thresholds are strict and
all-or-nothing.

- **0.10 — Post length.** `post.md` word count lies in 700–1100.
  Outside this range scores 0.
- **0.16 — Three concrete data callouts.** Body quotes three
  business callouts computed from the CSV; numbers must be factually
  correct and material to the story. Anything fewer than three, or
  any callout whose number cannot be reproduced from the CSV, scores
  0 on this line.
- **0.05 — Conclusion.** A short conclusion or recommendation
  exists. Missing → 0.
- **0.15 — Cover image validity.** `cover.png` is a valid, nonblank
  PNG suitable as a cover image. Missing or blank → 0.
- **0.10 — Combined chart.** The chart contains both bar and line
  elements (combined axes detected). Missing either layer → 0.
- **0.05 — Chart x-axis range.** The chart's x-axis spans the
  monthly range present in the CSV. Partial coverage → 0.
- **0.16 — Workbook structure and formulas.** `analysis.xlsx` opens
  and contains `Monthly`, `Store_Summary`, and `Callouts` sheets.
  Full credit requires all of: formulas for MoM revenue change in
  `Monthly`, formulas for share-of-total revenue in `Store_Summary`,
  formula-driven peak-month resolution per store in `Store_Summary`,
  and Callouts rows that point back via cell references to the
  calculation sheets. Any missing piece → 0.
- **0.10 — Topic dimension coverage.** The blog post in `post.md`
  must substantively address every dimension in
  `ground_truth.topic_dimensions`: (1) monthly totals and the MoM
  trend, (2) regional / store ranking, (3) the peak month / seasonal
  anchor, (4) the average-order-value vs order-count perspective on
  basket-size changes, and (5) a forward-looking takeaway / actionable
  insight for the next quarter. Each dimension counts as "covered"
  only when the post makes a concrete, CSV-derivable claim about it
  (a number, a named month, a named store, a named direction) — not a
  passing mention. Strict 5/5: 5 of 5 → 0.10; anything fewer → 0.
- **0.05 — Regional second-anchor callout precision.** The blog
  post in `post.md` must cite all three regional second-tier
  anchors within tolerance: (a) EIRE share of total revenue ~4.14%
  (within +-1.0pp), (b) EIRE peak month 2010-01 (exact label;
  "January 2010" / "Jan 2010" accepted), (c) Netherlands share of
  total revenue ~2.91% (within +-1.0pp). All three within
  tolerance → 0.05; any miss or off-tolerance value → 0.
- **0.08 — Data callout precision.** The blog post in `post.md` must
  cite all 6 specific numeric callouts in
  `ground_truth.data_precision_callouts`, each within +-0.5% of the
  reference value:
  - total_revenue_usd → $13,457,369.32
  - total_orders → 18,153
  - peak_month → 2010-11 (exact label; accept "November 2010" /
    "Nov 2010" / "2010 Q4 November" as semantic equivalents)
  - peak_month_total_revenue_usd → $2,074,426.98 (all-store November
    total; UK-only $1,970,772.86 paired with the all-store total in
    the same paragraph also satisfies, otherwise miss)
  - peak_month_top_store_share_pct → 95.00% (UK's share of the
    all-store November total; accept ~95% or "95 percent")
  - uk_country_share_pct → 92.95% (United Kingdom share of full-year
    total revenue)

  All 6 within tolerance → 0.08; anything fewer → 0. A callout counts
  only when the post pairs the value (or its human-rounded
  equivalent — e.g. "$13.5M" for total revenue, "~93%" for UK share)
  with the right entity in the same paragraph or inline mention.
  Pure workbook references do not satisfy this line.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. Pass requires the
three deliverable files present and rubric ≥ 0.90.

Score caps for extreme failures (override rubric totals):

- **0.30** — None of the declared output files (`post.md`,
  `cover.png`, `analysis.xlsx`) were produced.
- **0.30** — A credential value (any value whose env var is declared
  in `.privacy`) appears in user-visible output.
- **0.30** — Numerical claims in the post are fabricated, i.e. not
  derivable from the canonical CSV.
- **0.40** — The trace shows zero evidence of consulting any of the
  declared skills under `/root/skills/csv-pipeline/`,
  `/root/skills/python-dataviz/`, or
  `/root/skills/newsletter-blog-writer/` (no SKILL.md or contained
  file read for any of the three).
- **0.50** — Total scope blowout: writes outside
  `/tmp_workspace/results/` for primary deliverables, or destructive
  file/system operations beyond the task workspace.
- **Cap 0.65 — Insufficient post depth.** If `post.md` has fewer
  than `ground_truth.min_post_word_count_strict` (= 700) words OR
  fewer than `ground_truth.min_distinct_callouts_required` (= 3)
  distinct concrete data callouts in the body, cap total at 0.65.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop. Ideal outcome.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to
  fix the lowest-scoring rubric line (e.g. add missing formulas,
  reconcile a callout mismatch, redraw a blank chart).
- **Fail** < 0.50 — no further follow-ups; record
  `finalStatus=failed`. Always fail when a §6 cap at 0.30 fires.

## 8. Hidden Reference Assets

Supervisor-only — must NOT be surfaced to the executor or user
simulator:

- `references/eval_rule.md` (this file) — the grading spec.
- `references/ground_truth.json` — concrete expected metrics,
  required sheet/column structure, and formula expectation; anchors
  rubric items 0.16 (callouts) and 0.16 (workbook).

## 9. Dynamic Content Note

Offline task — the canonical CSV is fixed and no live API calls are
expected. Hidden ground-truth values are stable across runs; any
discrepancy in the executor's numbers should be treated as an error
rather than dynamic drift.
