# Hidden Evaluation Rule — Exploration v2 · SEC EDGAR structured data API (reverse from human viewer)

## 1. Grading Philosophy

This is an **interface-discovery + content-retrieval** task graded by
**outcome plus mechanism evidence**.

The executor must:

- discover SEC's **structured data API** on the separate `data.sec.gov` host
  (the `submissions/CIK##########.json` endpoint) that backs the human
  `browse-edgar` viewer, and use it (not scrape the viewer HTML), and
- produce auditable evidence (request URL + raw JSON) including the required
  descriptive **User-Agent** header.

The difficulty: the human page is on `www.sec.gov/cgi-bin/...`, while the JSON
API is on a different host with a **zero-padded 10-digit CIK** path
(`CIK0000320193.json`), and SEC **rejects requests without a User-Agent**. The
"most recent 10-K" is identified by scanning the filings arrays — not by reading
a number off the page.

Grading anchors on the *mechanism* plus **stable, immutable facts** (company
identity; historical filings never change). Only "which 10-K is the latest"
advances over years — handled by a recency rule, not a hardcoded date, so this
never goes stale.

## 2. Task Contract

Start from the Apple browse-edgar page (CIK `0000320193`). Find the
`data.sec.gov` submissions API, and report: company name + ticker(s), and the
most recent 10-K's filing date, accession number, and primary document name.
Save `sec_latest_10k.json` and a `sec_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Target identity & endpoint

- CIK: **`320193`** → zero-padded path **`CIK0000320193`**.
- Correct endpoint: **`https://data.sec.gov/submissions/CIK0000320193.json`**
  (the structured filing history). Acceptable adjuncts: the per-filing index
  under `https://www.sec.gov/Archives/edgar/data/320193/<accession>/` to confirm
  the primary document, and `data.sec.gov/api/xbrl/...` for financials (not
  required here).
- A descriptive `User-Agent` (e.g. `name email`) is **required**; requests
  without it get blocked.

### 3.2 Stable facts (immutable — anchor here)

- `name` = **`Apple Inc.`**
- `tickers` includes **`AAPL`**
- These never change for this CIK.

### 3.3 Recency rule (instead of a hardcoded date)

The "most recent 10-K" must be the latest `form == "10-K"` entry by
`filingDate` in the `filings.recent` arrays (cross-index `form`, `filingDate`,
`accessionNumber`, `primaryDocument`). As of the task's construction the latest
was:

- filingDate **`2025-10-31`**, accession **`0000320193-25-000079`**, primary doc
  **`aapl-20250927.htm`**.

Apple files a new 10-K each fall, so this **will advance** over time. Grade the
executor's answer as correct if it is the **latest 10-K present in the
executor's own captured `submissions` response** — i.e. internal consistency
between the chosen entry and the raw JSON — even if that is newer than the
date above. Do **not** fail a run for returning a 10-K newer than `2025-10-31`;
**do** penalize returning an older 10-K when a newer one exists in the same
response, or confusing a 10-Q / 10-K/A for the 10-K.

### 3.4 Accession / document consistency

The accession number and primary document name reported must be the ones paired
with the chosen 10-K row in the captured JSON (same array index). Accession
format `NNNNNNNNNN-NN-NNNNNN` (dashes optional if the raw field omits them).

## 4. Expected Artifacts

- `/tmp_workspace/results/sec_latest_10k.json` — company name, ticker(s),
  latest 10-K filing date + accession number + primary document.
- `/tmp_workspace/results/sec_evidence/` — request URL(s) + raw JSON response(s)
  from `data.sec.gov`.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                             | Weight |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Data came from the `data.sec.gov` submissions JSON API for the zero-padded CIK, evidenced by saved request URL + raw JSON (with a User-Agent set).                | 0.30   |
| CP2 | Company identity correct: `Apple Inc.` + ticker `AAPL` (Section 3.2).                                                                                              | 0.15   |
| CP3 | The reported filing is the **latest 10-K** present in the captured response (recency rule, Section 3.3) — a true 10-K, not a 10-Q/10-K/A.                          | 0.30   |
| CP4 | Accession number + primary document name match the chosen 10-K's row in the captured JSON (Section 3.4).                                                           | 0.15   |
| CP5 | `sec_evidence/` makes the pull reproducible.                                                                                                                       | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the answer was obtained by **scraping the browse-edgar
  HTML** (or a third-party site) instead of the `data.sec.gov` JSON API.
- **cap at `0.55`** if no `sec_evidence/` is saved.
- **cap at `0.60`** if a wrong form type was returned as "the 10-K" (e.g. a
  10-Q, 8-K, or 10-K/A amendment treated as the annual report).
- **cap at `0.70`** if the latest 10-K was missed in favor of an older one that
  is clearly superseded in the same response.
- **cap at `0.40`** if the wrong company / CIK was used.

Do **not** cap or fail merely because:

- the returned latest 10-K is **newer** than `2025-10-31` (expected over time —
  validate against the executor's own captured JSON, not the construction date),
- the executor also called `data.sec.gov/api/xbrl/...` or fetched the archive
  index to confirm the primary document,
- the executor used `curl`/python/agent-browser, as long as a proper User-Agent
  was sent and the data came from the API.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3 satisfied, CP4 satisfied, no
cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor is still locating the JSON host, got a block
due to missing User-Agent and is retrying, or has the JSON but hasn't isolated
the latest 10-K / saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped the viewer HTML,
used the wrong company, or reported a filing not present in any captured
response.

## 8. Hidden Reference Assets

None shipped. Evaluate from `sec_latest_10k.json`, `sec_evidence/`, and the
transcript (look for a `data.sec.gov` call with a User-Agent header).

## 9. Dynamic Content Note

Company identity and historical filings are immutable; only "which 10-K is
latest" advances yearly, handled by the recency rule against the executor's own
captured response. Never hardcode-fail on the construction-time date.

## 10. Notes For Rationale

- When capping for HTML scraping, cite the browse-edgar URL used as the data
  source instead of `data.sec.gov`.
- When scoring CP3, quote the chosen filing's `form`/`filingDate`/`accessionNumber`
  from the executor's own captured JSON and confirm no newer 10-K precedes it.
- Guidance tags: `discover_separate_data_host`, `cik_zero_padding`,
  `required_user_agent`, `recency_rule_not_hardcoded_date`.
