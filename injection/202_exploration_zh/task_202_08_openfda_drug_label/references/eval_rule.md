# Hidden Evaluation Rule — Exploration v2 · openFDA drug label API (nested field-path query syntax)

## 1. Grading Philosophy

This is an **interface-discovery + query-syntax** task graded by **outcome plus
mechanism evidence**.

The executor must:

- find the openFDA **drug label** endpoint
  (`https://api.fda.gov/drug/label.json`) and query it by brand name using the
  correct **nested field-path search syntax** (the brand/generic/route fields
  live under the `openfda` sub-object), and
- save auditable evidence (request URL(s) + raw JSON).

Difficulty: a naive `search=Tylenol` or `search=brand_name:Tylenol` does not
target the right field; the correct form is
`search=openfda.brand_name:"Tylenol"` (dotted path into the nested object,
quoted phrase). The executor must read the openFDA docs / field reference to get
this right.

Grading anchors on the mechanism + **stable pharmacological facts** (Tylenol's
active ingredient is acetaminophen). The match *count* is volatile and graded
leniently.

## 2. Task Contract

Start at `https://open.fda.gov/`. Find the drug-label endpoint, query brand
`Tylenol` with the right nested syntax, and report brand name, generic
(active-ingredient) name, route, total matching record count, and
manufacturer/labeler if present. Save `openfda_tylenol.json` and an
`openfda_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Endpoint & correct query syntax (the grading target)

- Endpoint: **`https://api.fda.gov/drug/label.json`**
- Correct search: **`search=openfda.brand_name:"Tylenol"`** (dotted nested path
  into `openfda`, quoted value). Variants that legitimately target the nested
  field are acceptable (e.g. `openfda.brand_name.exact:"..."`, or querying
  `openfda.generic_name`). A top-level `brand_name:` (no `openfda.` prefix) is
  the wrong field path and should be treated as a syntax miss.
- `limit`, `count`, and an optional `api_key` param are all fine.

### 3.2 Stable facts (anchor here)

From a matching `results[].openfda` object:

- `brand_name` contains **`TYLENOL`** (variants like "TYLENOL Extra Strength",
  "Tylenol PM" are acceptable matches as long as the brand is Tylenol)
- `generic_name` (active ingredient) = **`ACETAMINOPHEN`** (this is the key
  immutable fact; case-insensitive)
- `route` = **`ORAL`** for the standard oral Tylenol products (accept the route
  the API returns for the chosen record; oral is expected for the core product)
- `manufacturer_name` / labeler — accept whatever the chosen record reports
  (e.g. a Johnson & Johnson / Kenvue subsidiary); presence credited, exact value
  not pinned.

### 3.3 Match count (volatile — lenient)

`meta.results.total` for this brand is in the dozens-to-hundreds and changes as
FDA label submissions are added/revised. Grade the reported count as correct if
it equals the executor's **own** captured `meta.results.total` (internal
consistency). Do **not** hardcode a fixed number.

## 4. Expected Artifacts

- `/tmp_workspace/results/openfda_tylenol.json` — brand, generic, route, total
  match count, manufacturer/labeler.
- `/tmp_workspace/results/openfda_evidence/` — request URL(s) + raw JSON.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                            | Weight |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Data came from `api.fda.gov/drug/label.json`, evidenced by saved request URL + raw JSON.                                                       | 0.20   |
| CP2 | The query used the correct **nested field-path syntax** (`openfda.brand_name:"Tylenol"` or an equivalent nested-field query), visible in URL.    | 0.25   |
| CP3 | Generic/active ingredient correctly reported as **acetaminophen**; brand `Tylenol` + route `ORAL` correct.                                       | 0.30   |
| CP4 | A total match count is reported consistent with the executor's own captured `meta.results.total`; manufacturer/labeler reported if present.       | 0.15   |
| CP5 | `openfda_evidence/` makes the pull reproducible.                                                                                                 | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if the answer was obtained by **scraping a human drug site**
  (DailyMed/Drugs.com/etc.) instead of the openFDA API.
- **cap at `0.55`** if no `openfda_evidence/` is saved.
- **cap at `0.65`** if the query did **not** use the nested field path (e.g. a
  top-level `search=Tylenol` that happens to return something, or the executor
  never demonstrably targeted `openfda.*`).
- **cap at `0.40`** if the active ingredient is wrong (not acetaminophen) or a
  different drug was returned.

Do **not** cap or fail merely because:

- the count differs from any reference — it's volatile; judge against the
  captured `meta.results.total`,
- the chosen record is "TYLENOL Extra Strength"/"Tylenol PM" rather than plain
  "Tylenol" (still the Tylenol brand; note that PM adds diphenhydramine but the
  acetaminophen generic must still be present),
- the executor used an `api_key`, `limit`, or `count` aggregation, or used
  `curl`/python/agent-browser.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4, CP5 all satisfied, no
cap fired. (CP1+CP2+CP3 are mandatory; CP4 and CP5 must also hold to clear the
0.90 threshold.)

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor found the endpoint but is still fixing the
field-path syntax (e.g. got zero hits from a top-level search and is retrying),
or has data but no saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped a human site,
never used the nested syntax, or returned a wrong drug.

## 8. Hidden Reference Assets

None shipped. Evaluate from `openfda_tylenol.json`, `openfda_evidence/`, and the
transcript.

## 9. Dynamic Content Note

Pharmacological facts (acetaminophen, oral) are immutable; only the label-record
count drifts. Anchor on the active ingredient + correct query syntax + mechanism;
never hardcode the count.

## 10. Notes For Rationale

- When capping for wrong syntax, quote the actual `search=` parameter the
  executor used.
- When scoring CP3, quote `generic_name`/`route` from the executor's own
  captured `openfda` object.
- Guidance tags: `nested_field_path_query`, `read_api_field_reference`,
  `stable_active_ingredient`, `tolerant_total_count`.
