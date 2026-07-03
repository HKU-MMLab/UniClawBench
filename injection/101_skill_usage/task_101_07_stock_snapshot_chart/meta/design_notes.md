# design notes — task_101_07_stock_snapshot_chart (archive)

This file is private to the meta directory and is never injected into either
the executor or the supervisor runtime. It captures version-design context
that should not appear in the hidden eval rule.

## v8 hardening round 2 (2026-04-29)

- Round-1 measurements showed opus-4.6 capping at 1.00 on this task. The
  fix targets implicit multi-part output: the task prompt now also asks
  for narrative commentary in `analysis.md` alongside the ranking table.
  The prompt deliberately asks in a casual voice ("how everyone did in
  absolute terms... how the names stack against each other... which ones
  swung around the most... worst peak-to-trough pullbacks... whether the
  moves track the broader sector / co-move with each other") so the five
  dimensions have to be inferred rather than enumerated.
- New §5 anchor at weight 0.12 checks that ≥4 of 5 hidden topic
  dimensions are covered in the commentary. The five dimension keys live
  in `ground_truth.topic_dimensions` (`absolute_returns`,
  `relative_ranking`, `volatility_risk_profile`,
  `drawdown_peak_trough_analysis`, `sector_correlation_comments`) with
  `min_dimensions_covered=4`.
- Rebalance to keep weights = 1.00: Markdown table structure 0.15→0.11
  (-0.04), Material split reconciliation 0.15→0.11 (-0.04),
  Reproducibility CSV 0.10→0.06 (-0.04). Total -0.12. New 5.8 = +0.12.
  Final total: 0.11+0.20+0.20+0.11+0.10+0.10+0.06+0.12 = 1.00.
- Score cap numbers in §6 untouched; success_threshold in YAML untouched.
- The added narrative requirement means a model that nails the table but
  drops the commentary loses 12 percentage points outright; a model that
  writes shallow commentary that only restates the ranking earns 0 on
  this checkpoint.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 still passing at ~1.00 on this
  task (the new dim anchor in R2 did not bite). Replicate the
  R5 retighten pattern that proved most effective: keep the multi-part
  output, add a second entity-precision anchor that demands concrete
  numeric values in prose.
- New "Ticker numeric precision" line at weight 0.10 requires the
  narrative paragraphs to surface adjusted-return percentages for at
  least 4 of 5 tickers, each within ±0.05 percentage points of GT.
  Pure table references do not satisfy this line — the prose itself
  must carry the numbers.
- Reference values in `ground_truth.expected_adjusted_returns`:
  TSLA 33.96, NVDA 20.24, AAPL 15.49, MSFT 4.19, GOOGL -0.14.
- Rebalance to keep weights = 1.00:
  Adjusted-ranking-correctness 0.20→0.14 (-0.06) and Topic-dim-
  coverage 0.12→0.08 (-0.04) jointly fund the new 0.10 line.
  Final total: 0.11+0.14+0.20+0.11+0.10+0.10+0.06+0.08+0.10 = 1.00.
- Score caps in §6 untouched. success_threshold in YAML untouched.
- GT additions: `expected_adjusted_returns`,
  `ticker_value_tolerance_pct_points`, `min_tickers_cited_with_value`.

## Round 7 hardening (2026-04-30) — pass trim
- Currently pass 1.0; add per-ticker corp-action note CP (0.05).
- Shaved 0.05 from Ticker numeric precision in commentary (0.10 → 0.05).
- Target: opus 1.0 → ~0.95 (still pass).

## Round 8 hardening (2026-04-30) — anchor swap (corp-action → volatility+drawdown)
- R7 corp-action anchor didn't bite (still pass 1.0); replacing with stricter "Per-ticker volatility + drawdown annotation" CP at same 0.05 weight.
- New requirement: each of 5 tickers needs both a volatility label (low/medium/high) AND a max-drawdown % anchor; strict 4-of-5 stepped credit.
- GT swapped: removed acceptable_corp_action_labels + min_tickers_with_corp_action_note; added acceptable_volatility_labels + min_tickers_with_volatility_drawdown: 4.
- §5 sum still 1.00 (pure replacement at same weight).
- Target: opus 1.0 → ~0.95 (still pass) but biting harder when prose lacks per-ticker risk annotations.

## Review pass (2026-04-30) — full redesign per user feedback (Task 7 in review_record.md)

### Why redesigned
User flagged the prior design (synthetic 2020-08-03 → 2020-09-04 window with
fabricated AAPL/TSLA pre-split prices and a hand-built corporate-actions
section) as not realistic — the snapshot's "split factor 4" on AAPL produced
absurdities like a "raw_return_pct of -71.18%" that had no real-world
referent. Confirmed user direction:
real Q1 2024 data, fixed window, real tickers, no synthetic split games,
single clawhub skill.

### Skill swap
- Removed: `market-snapshot-analysis` and `chart-image` (custom in-tree
  skills, not on the clawhub top-1000 list).
- Added: `stock-analysis` (slug verified in
  `skills_top1000_downloads.jsonl` at rank 37, 44.8k downloads). The
  user-supplied prompt cited author `awachat`, but the actual author for
  the `stock-analysis` slug in the JSONL is `udiedrichsen`; the slug
  matches and the summary is a Yahoo-Finance-powered stock-analysis skill,
  consistent with what the user described. `_meta.json` records
  `udiedrichsen` as the owner.
- `SKILL.md` written from scratch documenting (a) the live yfinance path,
  (b) snapshot-mode workflow, (c) chart conventions (cumulative-return
  overlay normalized to 1.0 at first window day so all five tickers fit
  on one panel), (d) the snapshot-mode output contract that mirrors the
  task prompt: per-ticker table with total-return % + max-drawdown %, all
  tickers as legend entries.

### Sources change
- `sources/snapshot.json` rebuilt from `yfinance` Q1 2024 download for
  AAPL, NVDA, TSLA, MSFT, GOOG. 61 trading days per ticker, first day
  2024-01-02, last day 2024-03-28 (2024-03-29 was Good Friday).
- New schema:
  ```
  {
    "tickers": [...],
    "window": {"start": "2024-01-02", "end": "2024-03-29"},
    "ohlcv_per_ticker": { "AAPL": [{date,open,high,low,close,volume}, ...], ... }
  }
  ```
- No fabricated splits, no fabricated dividends. The snapshot is a frozen
  copy of real public market data — supervisor can spot-check it
  externally against any free finance source.

### Prompt rewrite
- Real-user voice: "Hey, I'm putting together a quick brief on five
  big-cap tech names for Q1 2024 and I'd love your help."
- Skill mention is in the **first paragraph** ("Please use the workspace's
  stock-analysis skill to crunch this for me.").
- No parentheses / brackets in the prose.
- The two required metrics (Q1 total return %, max drawdown %) are stated
  explicitly per global rule #7. Optional flavor metrics
  ("realized volatility or a rough beta read") are mentioned as
  user-style afterthought but not required by eval. This satisfies global
  #9 — "common metrics + some metrics that take more work to extract" —
  the user surfaces total return % (common) and max-drawdown % (less
  common but well-defined) as required.
- Output set trimmed from {analysis.md, chart.png, returns_repro.csv} to
  the user-confirmed pair {analysis.md, chart.png}. The prior CSV
  reproducibility deliverable was a tester contrivance, not what a real
  finance teammate asks for.

### Eval rebalance (§5, sum = 1.00)
Five strict checkpoints, all 5/5 strict. No "≥4/5" partial credit lines
anywhere in §5 (per global #8: strict checkpoints).

| Weight | Check |
| ------ | ----- |
| 0.10 | Both files (`analysis.md` + `chart.png`) exist and are non-empty / well-formed. |
| 0.30 | All 5 ticker Q1 total-return % values within ±0.5 pp of GT. **Strict 5/5.** |
| 0.30 | All 5 ticker max-drawdown % values within ±0.5 pp of GT. **Strict 5/5.** |
| 0.20 | Chart `chart.png` shows all 5 tickers as legend entries. |
| 0.10 | `stock-analysis` skill evidenced as consulted (read SKILL.md, named in report, or followed snapshot-mode contract). |

Sum: 0.10 + 0.30 + 0.30 + 0.20 + 0.10 = **1.00**.

§6 score caps adjusted to match new failure modes:
- Cap 0.30 — no `analysis.md` (unchanged role).
- Cap 0.65 — three or more ticker numbers off (replaced the prior
  "computed only from raw close" cap, which assumed splits in the data;
  no splits in Q1 2024 for these names).
- Cap 0.70 — live-API violation / fabricated numbers (kept).

### GT additions
Replaced the prior split/dividend-heavy ground truth with a clean Q1
2024 set:
- `expected_q1_returns_pct`: AAPL -8.37, NVDA 83.51, TSLA -29.71,
  MSFT 12.53, GOOG 9.07.
- `expected_max_drawdowns_pct`: AAPL -13.41, NVDA -8.70, TSLA -34.59,
  MSFT -4.39, GOOG -14.39.
- `expected_first_open_per_ticker` and `expected_last_close_per_ticker`
  recorded for supervisor cross-checking.
- `expected_chart_legend`: ["AAPL", "NVDA", "TSLA", "MSFT", "GOOG"].
- `tolerance_pct_points`: ±0.5 pp on every numeric line.
- `computation_notes` documents the formulas the supervisor uses.

All numbers were computed by the same script that built the snapshot,
guaranteeing GT and source are mutually consistent.

### Verification
- `§5 sum = 0.10 + 0.30 + 0.30 + 0.20 + 0.10 = 1.00` ✓
- All 5 strict checkpoints (no ≥4/5 lenient bands) ✓
- Skill in first paragraph of prompt ✓
- Skill on top-1000 clawhub list (rank 37) ✓
- No parentheses in prompt ✓
- Real public Q1 2024 data, no synthetic splits ✓
- success_threshold (0.9) and score-cap numbers untouched per global
  rule #11 (caps reused, the cap-0.65 description was rewritten to
  match the new failure mode but the number is unchanged) ✓
- Output deliverables match prompt exactly: `analysis.md` + `chart.png`,
  no contrived CSV ✓
