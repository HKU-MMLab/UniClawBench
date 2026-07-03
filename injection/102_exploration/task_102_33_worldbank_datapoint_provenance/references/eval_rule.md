# Hidden Evaluation Rule — Exploration v2 · GDP data-point → canonical World Bank indicator row (data provenance)

## 1. Grading Philosophy

A **data-provenance** task graded by **tracing a loose number to the canonical
dataset + exact row**. The executor is given "Japan 2015 GDP ≈ US$4.44 trillion"
with no source. Searching the raw number does not surface a canonical source —
the executor must identify the right dataset + indicator, query the authoritative
API, locate the Japan/2015 row, and verify the value.

## 2. Task Contract

Trace "Japan 2015 GDP ≈ $4.44T" to its dataset + indicator (name + code), the
precise Japan/2015 value, an authoritative data link, and whether it checks out.
Save `datapoint_provenance.json`.

## 3. Ground-Truth Reference

- **Dataset:** **World Bank — World Development Indicators**
- **Indicator:** "**GDP (current US$)**", code **`NY.GDP.MKTP.CD`**
- **Row:** Japan (JPN), 2015 → **4,444,930,651,964.18 USD** (~US$4.44 trillion)
- **Links:** API `https://api.worldbank.org/v2/country/JPN/indicator/NY.GDP.MKTP.CD?date=2015&format=json`,
  page `https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=JP`

## 4. Expected Artifacts

- `/tmp_workspace/results/datapoint_provenance.json` — dataset, indicator
  name+code, Japan/2015 value, authoritative link, check-out verdict, evidence.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct dataset + indicator identified: World Bank WDI, "GDP (current US$)" / `NY.GDP.MKTP.CD`.                    | 0.35   |
| CP2 | The exact Japan/2015 value retrieved from the authoritative World Bank source (~$4.44T) and matched.              | 0.30   |
| CP3 | The authoritative World Bank API/data page is used (not a news/aggregator repeating the figure).                   | 0.20   |
| CP4 | Check-out verdict + evidence chain; indicator code reported (the precise series identity).                        | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the figure is confirmed only via a news/aggregator and the
  World Bank source is never reached.
- **cap at `0.65`** if the dataset is reached but the specific indicator code
  `NY.GDP.MKTP.CD` is never identified (there are several GDP indicators — current
  US$, constant, PPP; identifying the right one is the point).
- **cap at `0.55`** if no value is actually retrieved/matched for Japan 2015.

Do **not** cap or fail merely because:

- the retrieved value differs slightly due to a World Bank revision — accept the
  current API value if it is ~$4.4T and matches the executor's own retrieval,
- the executor reaches it via the API or the data.worldbank.org page.

Pass requirements (`score >= 0.90`): CP1 (WDI + NY.GDP.MKTP.CD), CP2 (Japan/2015
value matched), CP3 (World Bank source), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the dataset is reached but the indicator code/row isn't
pinned. Prefer `fail` when only a news/aggregator is cited, or the wrong indicator
(e.g. constant-US$ or PPP) is reported as the match without noting current-US$.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — dataset, indicator, row, value. Supervisor-only.

## 9. Dynamic Content Note

The World Bank occasionally revises historical values; the dataset + indicator
identity are stable. Grade against the executor's captured value from the
official API/page.

## 10. Notes For Rationale

- When capping at 0.65, note that the specific indicator code was not pinned.
- Guidance tags: `data_point_provenance`, `worldbank_indicator_code`,
  `canonical_api_row`, `not_searchable_by_number`.
