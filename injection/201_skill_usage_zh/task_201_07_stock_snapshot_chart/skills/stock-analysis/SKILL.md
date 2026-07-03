---
name: stock-analysis
description: Analyze stocks and cryptocurrencies using Yahoo Finance data. Supports portfolio management, watchlists with alerts, dividend analysis, 8-dimension stock scoring, viral trend detection, and rumor / early-signal detection. Use for stock analysis, portfolio tracking, earnings reactions, crypto monitoring, trending stocks, or finding rumors before they hit mainstream.
metadata:
  clawdbot:
    emoji: "📈"
    requires:
      bins:
        - python3
---

# Stock Analysis Skill

Yahoo-Finance-powered analysis toolkit for equities, ETFs, and crypto. The
default data path is the `yfinance` library, but the skill also accepts a local
OHLCV snapshot as a stand-in source when the user provides one — in that case
the snapshot is canonical and the skill must not call out to a live API.

## Core capabilities

1. Fetch and cache OHLCV history for one or more tickers over an arbitrary
   window. When a snapshot file is supplied (e.g. `snapshot.json` with a
   `ohlcv_per_ticker` map), prefer it.
2. Compute total return over a window from open-on-first-day to close-on-last-
   day, expressed as a percentage. Distinguish raw return from
   split/dividend-adjusted total return.
3. Compute peak-to-trough max drawdown over the window using daily closes.
4. Compute additional risk metrics on demand: realized volatility (std of
   daily log returns), beta vs. a sector or market proxy, and Sharpe-like
   risk-adjusted scores.
5. Render comparison charts:
   - Cumulative-return overlay (one normalized line per ticker, indexed to
     1.0 at the first window day) — best for cross-ticker comparison when
     starting prices differ widely.
   - K-line / candlestick chart for a single ticker.
   - Sparkline / mini-chart for a watchlist row.
6. Save chart output as PNG suitable for embedding in a Markdown report.
7. 8-dimension scoring (momentum, value, quality, etc.) and dividend-history
   summary are available but optional — only run them when the user asks.

## Snapshot mode workflow

When the user hands you a local snapshot rather than asking for live data:

1. Read the snapshot file. Validate that it contains a tickers list, a
   declared window, and per-ticker OHLCV bars.
2. Treat the snapshot's window as authoritative — do not extend it with live
   data, and do not silently substitute live prices.
3. For each ticker, compute the requested metrics directly from the bars in
   the snapshot. Total return uses the `open` of the first bar and the
   `close` of the last bar. Drawdown is computed over the daily-close series.
4. When rendering a comparison chart, normalize each ticker's close series to
   1.0 at the first window day so a single y-axis can show every ticker
   meaningfully — five tickers on a raw-price y-axis are not comparable
   because the absolute price levels differ by an order of magnitude.
5. Always include all snapshot tickers as legend entries on the chart, in
   the order the user listed them. Use a distinct color per ticker.

## Output contract for snapshot reports

When asked to produce an analysis report from a snapshot, write:

- `analysis.md` — a Markdown report. Include at minimum:
  - A short summary paragraph.
  - A per-ticker table with total-return % and max-drawdown % for the
    window.
  - Brief commentary that interprets the numbers (which ticker won the
    quarter, who had the worst pullback, etc.).
- `chart.png` — one comparison chart with all tickers as legend entries,
  cumulative-return overlay style by default.

## Anti-patterns

- Do not call `yfinance.download` when a snapshot is supplied — that
  bypasses the user's frozen window.
- Do not invent ticker prices that are not in the snapshot.
- Do not drop tickers from the chart legend; users compare across all of
  them.
