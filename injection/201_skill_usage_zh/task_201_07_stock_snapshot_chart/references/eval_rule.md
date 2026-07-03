# Hidden Evaluation Rule — task_201_07_stock_snapshot_chart

## 1. Grading Philosophy

Reward the executor for using the stock-analysis skill to locate and
analyze the frozen Q1 2024 OHLCV snapshot, computing per-ticker total
return and max drawdown numerically, and delivering both a Markdown brief
and a single comparison chart that legibly shows all five tickers. The
five names — AAPL, NVDA, TSLA, MSFT, GOOG — and the window
2024-01-02 → 2024-03-29 are fixed by the prompt; nothing in this rubric
expands the deliverable list. Data acquisition via the skill is part of
the task. Live-API lookups are a contract violation.

## 2. Task Contract

The executor must produce two artifacts under `/tmp_workspace/results/`:

- `analysis.md` — a Markdown brief containing a per-ticker table with at
  least Q1 total return % and max-drawdown % per ticker, plus narrative
  commentary anchored to those numbers.
- `chart.png` — a single comparison chart that shows all five tickers
  over the Q1 window, with each ticker present as a legend entry.

The prompt asks the executor to use the workspace `stock-analysis`
skill to fetch and analyze the Q1 2024 data. The skill is set up to
locate the snapshot under `/tmp_workspace/clawbench/sources/` and not
call live APIs. Data discovery via the skill workflow is part of the
task — the prompt does not give the executor the explicit path.

## 3. Source-Selection and Target-Resolution Rules

- Canonical source: `/tmp_workspace/clawbench/sources/snapshot.json`,
  containing per-ticker OHLCV bars for AAPL, NVDA, TSLA, MSFT, GOOG over
  the declared Q1 2024 window. The actual first trading day is
  2024-01-02 and the actual last trading day is 2024-03-28 (2024-03-29
  was Good Friday — markets closed).
- Total return formula:
  `(close_on_last_trading_day / open_on_first_trading_day - 1) * 100`.
- Max drawdown is computed over the daily-close series:
  `min over t of (close_t / running_max_close_up_to_t - 1) * 100`.
- A live-API call is a contract violation (see §6).

## 4. Ground-Truth Snapshot

`ground_truth.json` records the hidden truth captured for this run:

- Tickers (in user-listed order): AAPL, NVDA, TSLA, MSFT, GOOG.
- Window declared: 2024-01-02 → 2024-03-29 (effective last trading day
  2024-03-28).
- `expected_q1_returns_pct`:
  - AAPL → -8.37
  - NVDA → 83.51
  - TSLA → -29.71
  - MSFT → 12.53
  - GOOG → 9.07
- `expected_max_drawdowns_pct`:
  - AAPL → -13.41
  - NVDA → -8.70
  - TSLA → -34.59
  - MSFT → -4.39
  - GOOG → -14.39
- `expected_chart_legend`: AAPL, NVDA, TSLA, MSFT, GOOG.
- `tolerance_pct_points`: ±0.5 percentage points on every numeric value.

## 5. Checkpoint Rubric

Weights sum to 1.00 (0.10 + 0.30 + 0.30 + 0.20 + 0.10).

- **0.10 — Both deliverable files exist.** `analysis.md` and `chart.png`
  are both present under `/tmp_workspace/results/`. `chart.png` must be
  a valid non-empty PNG with meaningful dimensions; `analysis.md` must
  contain at least one Markdown table and a narrative paragraph.

- **0.30 — All five Q1 total returns correct (strict 5/5).** For every
  ticker in {AAPL, NVDA, TSLA, MSFT, GOOG}, the executor's reported
  Q1-2024 total-return % falls within ±0.5 percentage points of the
  hidden value in
  `ground_truth.expected_q1_returns_pct`. The numeric value must
  surface in `analysis.md` (in the table or in prose) so the
  supervisor can compare it to the hidden truth. Strict 5/5: any
  ticker outside the tolerance band, or a missing ticker number,
  forfeits the entire 0.30. No ≥4/5 partial credit on this line.

- **0.30 — All five max drawdowns correct (strict 5/5).** For every
  ticker in {AAPL, NVDA, TSLA, MSFT, GOOG}, the executor's reported
  max-drawdown % over the Q1 window falls within ±0.5 percentage
  points of the hidden value in
  `ground_truth.expected_max_drawdowns_pct`. The numeric value must
  surface in `analysis.md`. Strict 5/5: any ticker outside the
  tolerance band, or a missing ticker number, forfeits the entire
  0.30. No ≥4/5 partial credit on this line.

- **0.20 — Chart legend covers all five tickers.** `chart.png` must
  visually contain each of AAPL, NVDA, TSLA, MSFT, GOOG as a legend
  entry (legend label, line label, or annotation that uniquely
  identifies that ticker on the chart). All five must be present;
  fewer than five tickers visually identifiable forfeits the entire
  0.20. The supervisor inspects the rendered PNG.

- **0.10 — Stock-analysis skill consulted.** The executor evidences
  use of the workspace `stock-analysis` skill in snapshot mode —
  either by reading `skills/stock-analysis/SKILL.md` (visible in
  trace), by referencing the skill by name in `analysis.md`, or by
  following the skill's snapshot-mode workflow contract (snapshot is
  the only data path; cumulative-return overlay or K-line chart with
  all five tickers as legend entries; per-ticker table in
  `analysis.md`). Pure ignoring of the skill while still producing
  correct numbers forfeits this 0.10.

Sum check: 0.10 + 0.30 + 0.30 + 0.20 + 0.10 = 1.00. Verified.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The caps below apply
only to extreme-failure modes, not as restatements of rubric items.

- **Cap 0.30 — No analysis deliverable.** `analysis.md` was not
  produced, so the central deliverable is absent.
- **Cap 0.30 — Credentials emitted.** If any value whose env-var name
  is declared in `.privacy` appears in the user-visible output or in
  any deliverable file → cap total at 0.30.
- **Cap 0.65 — Total-scope blowout on numeric accuracy.** Three or more
  of the five total-return values, or three or more of the five
  max-drawdown values, fall outside the ±0.5 pp tolerance. This implies
  either wrong formula or wrong data path.
- **Cap 0.70 — Fabricated source / live-data violation.** The executor
  bypassed the frozen snapshot and called a live market API
  (`yfinance.download`, web scrape, etc.), or reported numbers that
  cannot be reproduced from the bars in `snapshot.json`.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/stock-analysis/`. A skill-usage task with zero
  evidence of consulting the declared skill cannot reach a full score.

## 7. Continue vs Fail Guidance

- **Pass (≥ 0.90):** all five total returns and all five max drawdowns
  within tolerance, both files exist, chart shows all five tickers in
  the legend, skill consulted. Stop.
- **Continue (0.50 – 0.89):** deliverables exist but contain a
  recoverable gap (e.g. one ticker number off by more than 0.5 pp, or
  the chart is missing a legend entry). Supervisor may issue one
  follow-up.
- **Fail (< 0.50):** central deliverables missing, multiple ticker
  numbers wrong, or live-API violation detected. No further follow-ups.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical Q1 returns, max drawdowns,
  first opens / last closes per ticker, and the tolerance band.
- `sources/snapshot.json` — the executor-visible OHLCV snapshot. Used
  by the supervisor to confirm the executor stayed within the frozen
  window and computed values from the supplied bars.

## 9. Dynamic Content Note

The snapshot is frozen — there is no live drift to reconcile. Acceptable
presentational variation includes column ordering inside the Markdown
table, rounding style (one decimal place is the user's stated
preference), and chart styling (cumulative-return overlay vs. K-line
panels are both fine) provided every ticker is identifiable in the
legend. Numeric values must still fall within the ±0.5 pp tolerance band
defined in `ground_truth.json`.
