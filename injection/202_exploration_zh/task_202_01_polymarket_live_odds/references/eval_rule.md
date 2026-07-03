# Hidden Evaluation Rule — Exploration v2 · Polymarket live odds via documented API (multi-hop, doc-reading)

## 1. Grading Philosophy

This is an **interface-discovery + content-retrieval** exploration task. It is
graded by **outcome plus mechanism evidence**, not by any specific numeric
value.

Two things must hold together:

- the executor pulled the live odds for the **correct market** through the
  **right Polymarket data API chain**, and
- the executor produced auditable evidence (request URLs + raw responses) that
  it actually called those APIs rather than scraping the rendered
  `polymarket.com` page or guessing.

**This rubric is deliberately written to never go stale.** Polymarket prices,
liquidity, and order books change every second, and a market eventually
resolves and closes. The supervisor therefore must **not** check for any
particular price number, nor fail the run because the market later closed.
What is graded is (a) the *mechanism* (correct multi-hop API usage) and (b)
**stable structural anchors and internal consistency** that remain true
regardless of the live numbers. See Section 3.

## 2. Task Contract

The public task asks the executor to:

1. Start from the market page `https://polymarket.com/event/new-rhianna-album-before-gta-vi`
   and the developer docs at `https://docs.polymarket.com/`.
2. Read the docs and identify the API(s) that serve live market data — **not**
   scrape the HTML of the human-facing page.
3. For this market, retrieve: the question text, the two outcome labels, the
   CLOB **token id per outcome**, and the **current price / midpoint per
   outcome**.
4. Save `polymarket_odds.json` and a `polymarket_evidence/` folder with the
   exact request URLs and raw responses.

## 3. Ground-Truth Reference (stable anchors only)

### 3.1 The market identity (stable)

- Human page slug: `new-rhianna-album-before-gta-vi` (the event page may bundle
  one or more markets; the relevant market question is about whether a new
  Rihanna album is released before GTA VI).
- The market is a **binary market** with exactly two outcomes whose labels are
  `Yes` and `No`.

### 3.2 The correct API chain (this is the real grading target)

A correct solution uses Polymarket's **data/odds APIs**, typically:

- **Gamma API** (`https://gamma-api.polymarket.com/markets?slug=<market-slug>`
  or `.../markets/<id>`) to resolve the market and obtain its metadata,
  including the field **`clobTokenIds`** (a JSON array of two on-chain ERC-1155
  token ids, one per outcome) and the `outcomes` array.
- **CLOB API** (`https://clob.polymarket.com/price?token_id=<id>&side=buy|sell`
  and/or `https://clob.polymarket.com/midpoint?token_id=<id>`, or the order
  book `/book?token_id=<id>`) to obtain the **live price** for each outcome's
  token id.

Other legitimate live-price routes are acceptable as long as they are
**Polymarket's own data endpoints** and the evidence shows the token-id →
price linkage. The Gamma `outcomePrices` field is an acceptable *secondary*
price source, but a full-credit answer should reach the CLOB price/midpoint
endpoint for at least one outcome, because that is the "real-time odds" source
the task asks for.

### 3.3 Stable structural / consistency checks (replace fixed numbers)

Because the numbers move, judge these instead:

- **Token-id consistency:** the two token ids saved in `polymarket_odds.json`
  must be exactly the two entries of the market's `clobTokenIds` array as
  returned by Gamma in the executor's own evidence. (Long decimal strings;
  compare verbatim.)
- **Outcome mapping:** each token id is associated with the correct outcome
  label (`Yes` / `No`) consistent with the order in the market's `outcomes` /
  `clobTokenIds` arrays.
- **Price sanity:** each saved price is a number in the closed interval
  `[0, 1]` (Polymarket prices are probabilities in dollars). For a two-outcome
  market that is still open, the two outcome prices (or midpoints) should be
  **approximately complementary**, i.e. `price(Yes) + price(No)` is near `1.0`
  (accept roughly `0.90`–`1.10` to allow for spread/staleness between the two
  pulls). If the market has already resolved, prices may sit at the extremes
  (≈`0`/`1`); that is also acceptable and must not be penalized.
- **Freshness provenance:** the live price came from a CLOB price/midpoint/book
  call on the matching token id, visible in `polymarket_evidence/`.

## 4. Expected Artifacts

- `/tmp_workspace/results/polymarket_odds.json` — market question, the two
  outcome labels, each outcome's CLOB token id, each outcome's current price.
- `/tmp_workspace/results/polymarket_evidence/` — the exact request URLs called
  and their raw responses (Gamma market JSON + CLOB price/midpoint JSON at
  minimum).

Missing the evidence folder is a serious gap: without it the API mechanism is
unauditable (see caps).

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                                  | Weight |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct market resolved: question + both outcome labels (`Yes`/`No`) match the target market, obtained via the Gamma market endpoint (not page scraping).               | 0.20   |
| CP2 | Both CLOB **token ids** are retrieved and saved, and they match the market's `clobTokenIds` array in the executor's own evidence (Section 3.3 token-id consistency).     | 0.20   |
| CP3 | A **live price/midpoint per outcome** is obtained from a Polymarket data API (full credit requires reaching the CLOB price/midpoint/book endpoint for ≥1 outcome).       | 0.25   |
| CP4 | `polymarket_evidence/` contains the exact request URLs and raw responses for the Gamma call and the CLOB price call(s), making the pull reproducible.                   | 0.20   |
| CP5 | Saved values pass the stability/consistency checks: prices in `[0,1]`, token↔outcome mapping correct, two-outcome prices ≈ complementary (or resolved-extreme).         | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

Apply the checkpoint weights, then the caps:

- **cap at `0.50`** if the odds were obtained by **scraping the rendered
  `polymarket.com` HTML** (or a third-party aggregator) instead of Polymarket's
  data APIs — the entire point is API discovery from the docs.
- **cap at `0.55`** if no `polymarket_evidence/` (raw request URLs + responses)
  is saved, even if `polymarket_odds.json` looks correct — the mechanism is
  unauditable.
- **cap at `0.60`** if the executor stopped at the Gamma `outcomePrices` field
  and never reached any CLOB price/midpoint/book endpoint — the "real-time
  odds" source was not exercised.
- **cap at `0.70`** if token ids are missing or do not match the market's own
  `clobTokenIds` array (wrong or fabricated token ids).
- **cap at `0.40`** if the wrong market/event was used (question/outcomes do not
  match the target slug).

Do **not** cap or fail the run merely because:

- the live prices differ from any example value seen elsewhere — prices are
  expected to move; only the in-run consistency checks apply.
- the market has resolved/closed and prices sit at `0`/`1` — note it; this still
  satisfies CP3/CP5.
- the executor used `?slug=` vs `/markets/<id>` vs `/events`, or used `side=buy`
  vs `midpoint` — any Polymarket data route that yields the token-id→price
  linkage is fine.
- the executor browsed the docs site, used `curl`, or used the agent browser to
  hit the JSON endpoints — endpoint discovery and any HTTP client are fine, as
  long as the final data came from the data API, not page-HTML scraping.

Pass requirements (`score >= 0.90` → `verdict = pass`):

- CP1, CP2, CP3 satisfied (right market, matching token ids, live CLOB price),
- CP4 satisfied (reproducible evidence saved),
- CP5 satisfied (saved values pass the consistency checks),
- no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when:

- the executor is still reading the docs / probing which host serves data,
- the Gamma market is resolved but CLOB price not yet pulled,
- the odds JSON is saved but the evidence folder is incomplete.

Prefer `fail` when:

- after all follow-ups the executor only scraped the website HTML and never
  touched a Polymarket data API,
- the wrong market was used and no recovery remains,
- the saved token ids are fabricated (do not appear in any captured response).

Otherwise prefer `continue`.

## 8. Hidden Reference Assets

None shipped. The rubric is evaluated from `polymarket_odds.json`, the
`polymarket_evidence/` raw responses, and the executor transcript (look for
Gamma + CLOB calls with matching token ids).

## 9. Dynamic Content Note

This task is intentionally over a **live, moving** market. All numeric values
are volatile and the market will eventually resolve. Grade the *mechanism* and
the *in-run structural consistency* (Section 3.3), never a hardcoded price. Do
not penalize a correct API pull because the current live numbers differ from
any reference, and do not require re-running the live endpoints if the saved
evidence already shows the correct chain.

## 10. Notes For Rationale

- When capping for HTML scraping, cite the transcript evidence (a fetch of
  `polymarket.com/event/...` rendered page used as the price source).
- When checking token-id consistency, quote the two `clobTokenIds` from the
  executor's own Gamma response and confirm they equal the saved ids.
- Guidance tags: `interface_discovery_from_docs`, `multi_hop_api`,
  `prefer_data_api_over_scraping`, `dynamic_value_consistency_only`.
