# Hidden Evaluation Rule — Exploration v2 · Steam undocumented appdetails API (reverse-discovery)

## 1. Grading Philosophy

This is an **interface-discovery + content-retrieval** task graded by
**outcome plus mechanism evidence**.

Two things must hold together:

- the executor retrieved the game's metadata for the **correct app id** through
  Steam's **storefront JSON endpoint** (`store.steampowered.com/api/appdetails`
  or an equivalent storefront data endpoint), and
- the executor produced auditable evidence (request URL + raw JSON response)
  that it actually called the endpoint rather than parsing the store page HTML.

The endpoint is **not officially documented**, so the core skill is reverse-
discovering it from the store URL / page network traffic. The grading targets
the *mechanism* plus **stable game attributes** that do not change over time.
Price is the only volatile field and is graded leniently (see Section 3.3).

## 2. Task Contract

The public task asks the executor to:

1. Start from `https://store.steampowered.com/app/1245620/ELDEN_RING/`.
2. Discover the JSON endpoint the storefront uses to render game details
   (keyed by the app id `1245620`) — **not** scrape the rendered HTML.
3. Retrieve: title, developer(s), publisher(s), supported platforms, is-free +
   price, release date, Metacritic score (if present).
4. Save `steam_appdetails.json` and a `steam_evidence/` folder with the request
   URL + raw JSON response.

## 3. Ground-Truth Reference (stable anchors)

### 3.1 Target identity & endpoint

- App id: **`1245620`** (ELDEN RING).
- Correct endpoint family:
  `https://store.steampowered.com/api/appdetails?appids=1245620`
  (optionally with `&cc=<country>&l=<lang>`). The response is keyed by the app
  id with `{"1245620": {"success": true, "data": {...}}}`.

### 3.2 Stable attributes (these do NOT change — anchor the grade here)

From the `data` object:

- `name` = **`ELDEN RING`**
- `type` = `game`
- `developers` includes **`FromSoftware, Inc.`**
- `publishers` includes **`FromSoftware, Inc.`** and **`Bandai Namco
  Entertainment`** (accept either casing / minor punctuation; at least
  FromSoftware must be present, and Bandai Namco recognized as a publisher)
- `platforms` = Windows **true**, macOS **false**, Linux **false**
- `release_date.date` = **`Feb 24, 2022`** (accept any unambiguous rendering of
  2022-02-24)
- `metacritic.score` = **`94`** (accept ±2 only if Valve revises it; the field
  must be read from the API, not invented)

### 3.3 Volatile field (graded leniently)

- `is_free` is `false`; `price_overview.final_formatted` is the current price
  (e.g. shown as `$59.99` in the US storefront, but this varies by region,
  sales, and over time). **Do not** check for a specific price number. Credit
  the executor for correctly reporting `is_free=false` and capturing *whatever*
  price the API returned for its chosen region, with the region/`cc` noted or
  inferable from the evidence. A sale price or a different-currency price is
  fine.

## 4. Expected Artifacts

- `/tmp_workspace/results/steam_appdetails.json` — title, developers,
  publishers, platforms, is_free + price, release date, metacritic.
- `/tmp_workspace/results/steam_evidence/` — the exact request URL + raw JSON
  response from the appdetails endpoint.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                          | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | The data came from the Steam storefront JSON endpoint (`/api/appdetails` or equivalent) for app id `1245620`, evidenced by the saved request URL + raw JSON.    | 0.30   |
| CP2 | Title `ELDEN RING` + developer `FromSoftware` + publishers including Bandai Namco are correctly reported (Section 3.2).                                          | 0.20   |
| CP3 | Platform support correct (Windows-only: win true, mac false, linux false) and release date `Feb 24, 2022` correct.                                              | 0.20   |
| CP4 | `is_free=false` reported and a price captured from the API (any region/sale value); Metacritic score read from the API (`94`).                                  | 0.15   |
| CP5 | `steam_evidence/` makes the pull reproducible (request URL + raw response saved).                                                                               | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the metadata was obtained by **parsing the store page
  HTML** (or a third-party site like SteamDB/IsThereAnyDeal) instead of the
  storefront JSON endpoint.
- **cap at `0.55`** if no `steam_evidence/` is saved (mechanism unauditable).
- **cap at `0.60`** if the executor reported fields but never actually called
  the appdetails endpoint (e.g. answered from prior knowledge).
- **cap at `0.40`** if a different game / app id was used.
- **cap at `0.85`** if only the volatile price is wrong/missing while all stable
  attributes and the mechanism are correct.

Do **not** cap or fail merely because:

- the captured price differs from `$59.99` (region/sale/time variation expected),
- the executor added `cc`/`l` params or pulled a localized response,
- the executor used `curl`, python `requests`, or the agent browser to hit the
  JSON endpoint — any HTTP client is fine.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4, CP5 all satisfied, no
cap fired. (CP1+CP2+CP3 are mandatory; CP4 and CP5 must also hold to clear the
0.90 threshold.)

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor is still locating the endpoint, has the JSON
but hasn't saved structured output, or saved output but not the evidence folder.

Prefer `fail` when, after follow-ups, the executor only scraped HTML, used the
wrong app, or fabricated fields not present in any captured response.

## 8. Hidden Reference Assets

None shipped. Evaluate from `steam_appdetails.json`, `steam_evidence/`, and the
transcript.

## 9. Dynamic Content Note

Only the price (and transient flags like discount %) are dynamic; everything
graded in CP2/CP3 is stable historical metadata. Never hardcode-check the price.

## 10. Notes For Rationale

- When capping for HTML scraping, cite the fetched store-page URL used as the
  data source instead of `/api/appdetails`.
- Quote the `name`, `developers`, `platforms` from the executor's own raw JSON
  when scoring CP2/CP3.
- Guidance tags: `reverse_discover_undocumented_api`,
  `prefer_json_endpoint_over_html`, `stable_attrs_anchor_dynamic_price`.
