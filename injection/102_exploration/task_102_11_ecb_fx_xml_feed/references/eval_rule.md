# Hidden Evaluation Rule — Exploration v2 · ECB FX reference-rate feed discovery (hidden XML, derived cross-check)

## 1. Grading Philosophy

An **interface-discovery + content-retrieval** task graded by **outcome plus
mechanism evidence**, dynamic-proof.

The executor must discover the ECB's machine-readable euro reference-rates feed
(`eurofxref-daily.xml`) — which the human pages are built from but whose URL is
not obvious — and use it (not scrape the rendered HTML table) to pull the latest
rates, then compute a derived cross rate. Rates change daily, so the rubric never
checks a fixed number; it grades the **mechanism** (correct feed + parse) and
**internal consistency** (the derived cross rate computed from the executor's own
pulled EUR rates).

## 2. Task Contract

Discover the ECB FX feed, pull the latest reference date + EUR→USD, EUR→JPY,
EUR→GBP, and derive USD→JPY. Save `ecb_fx.json` + `ecb_evidence/` (feed URL + raw
response).

## 3. Ground-Truth Reference (stable structure, not values)

- Canonical feed: **`https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`**
  (the 90-day `eurofxref-hist-90d.xml` or the full-history feed are also
  acceptable ECB feeds). The data is a namespaced XML with nested `<Cube>`
  elements: an outer `<Cube time='YYYY-MM-DD'>` and inner
  `<Cube currency='USD' rate='...'/>` rows. The executor must parse this
  structure (the namespace + nested Cube is the discovery/parse challenge).
- The rates are **EUR-based** (rate = units of currency per 1 EUR).
- **Derived check (the consistency anchor):** USD→JPY = (JPY per EUR) / (USD per
  EUR). The executor's reported USD/JPY must equal its own pulled
  EUR→JPY ÷ EUR→USD within rounding (e.g. ±0.5). This is what makes the task
  gradeable without a fixed value.
- Sanity ranges (loose, just to catch nonsense): EUR→USD typically ~0.9–1.3,
  EUR→JPY ~120–200, EUR→GBP ~0.7–0.95. Do not hard-fail on range; these only flag
  a clearly wrong parse.

## 4. Expected Artifacts

- `/tmp_workspace/results/ecb_fx.json` — reference date, EUR→USD/JPY/GBP, derived
  USD→JPY.
- `/tmp_workspace/results/ecb_evidence/` — feed URL + raw XML response.

## 5. Checkpoint Rubric

| ID  | What matters (outcome + mechanism)                                                                               | Weight |
| --- | -------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Data came from the ECB machine-readable feed (eurofxref XML), evidenced by the saved feed URL + raw response — not HTML-table scraping. | 0.35   |
| CP2 | The three EUR reference rates (USD/JPY/GBP) and the reference date are extracted by correctly parsing the nested Cube XML. | 0.30   |
| CP3 | The derived USD→JPY cross equals the executor's own EUR→JPY ÷ EUR→USD within rounding (internal consistency).    | 0.20   |
| CP4 | `ecb_evidence/` makes the pull reproducible (feed URL + raw XML saved).                                          | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the rates were obtained by scraping the rendered ECB HTML
  table (or a third-party FX site) instead of the ECB XML feed.
- **cap at `0.55`** if no `ecb_evidence/` (feed URL + raw response) is saved.
- **cap at `0.70`** if the derived USD/JPY is inconsistent with the executor's own
  EUR rates (math/parse error) while the feed was used.
- **cap at `0.60`** if the wrong/non-ECB feed was used (e.g. a third-party FX API
  presented as "the ECB feed").

Do **not** cap or fail merely because:

- the rates differ from any example value — they are daily; only mechanism +
  internal consistency are graded,
- the executor used the daily, 90-day, or full-history ECB feed (all acceptable),
- the executor used `curl`/python/an XML parser — any real parse is fine.

Pass requirements (`score >= 0.90`): CP1 (ECB feed), CP2 (rates + date parsed),
CP3 (consistent cross), CP4 (evidence), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` while the executor is locating the feed or parsing the nested
Cube structure. Prefer `fail` when, after follow-ups, only HTML scraping was done
or a non-ECB source was used.

## 8. Hidden Reference Assets

None shipped. Evaluate from `ecb_fx.json`, `ecb_evidence/`, and the transcript.

## 9. Dynamic Content Note

Rates are published each ECB business day; the feed URL + XML structure are
stable. Grade mechanism + the internal cross-rate consistency, never a fixed rate.

## 10. Notes For Rationale

- When capping for HTML scraping, cite the ECB HTML page used instead of the XML
  feed.
- When checking CP3, recompute EUR→JPY ÷ EUR→USD from the executor's own values.
- Guidance tags: `discover_hidden_xml_feed`, `parse_namespaced_nested_xml`,
  `derived_cross_rate_consistency`, `dynamic_value_mechanism_only`.
