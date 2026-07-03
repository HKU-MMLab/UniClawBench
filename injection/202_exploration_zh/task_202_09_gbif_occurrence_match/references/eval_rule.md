# Hidden Evaluation Rule — Exploration v2 · GBIF two-hop (species/match → occurrence/search by taxonKey)

## 1. Grading Philosophy

This is an **interface-discovery + multi-hop retrieval** task graded by
**outcome plus mechanism evidence**.

The executor must:

- use the GBIF API to **resolve a scientific name to a numeric taxon key**
  (`species/match`), then **query occurrences by that key** (`occurrence/search`
  with `taxonKey=...`) — the occurrence API does not accept a bare name, so the
  two-hop is mandatory — and
- save auditable evidence (request URL(s) + raw JSON).

Grading anchors on the mechanism + the **stable taxon key** (a GBIF backbone
identifier). Occurrence **counts grow continuously** as datasets are ingested,
so all counts are graded leniently (lower-bound + internal consistency), making
this never go stale.

## 2. Task Contract

Start at `https://www.gbif.org/`. Resolve `Panthera leo` to its taxon key
(report matched name, rank, key); query occurrence count for that key in Kenya
(KE); report the global occurrence count for that key. Save
`gbif_panthera_leo.json` and a `gbif_evidence/` folder.

## 3. Ground-Truth Reference

### 3.1 Endpoint chain (the grading target)

- Hop 1 — name resolution: `https://api.gbif.org/v1/species/match?name=Panthera%20leo`
  → returns `usageKey`, `scientificName`, `rank`, `matchType`.
- Hop 2 — occurrences: `https://api.gbif.org/v1/occurrence/search?taxonKey=<usageKey>&country=KE&limit=0`
  → `count` for Kenya; and the same without `country` (or with `limit=0`) for the
  global `count`. (Using `occurrence/count?taxonKey=...` facets is also fine.)

### 3.2 Stable anchor (taxon key)

- `Panthera leo` resolves to GBIF backbone **usageKey `5219404`**, rank
  **SPECIES**, `scientificName` `Panthera leo (Linnaeus, 1758)` (accept the
  authorship-bearing form). The taxon key is a stable backbone identifier; this
  is the primary anchor.

### 3.3 Counts (volatile — lenient, lower-bound + consistency)

- Kenya occurrence count: at construction ≈ **3,243**, and only **grows** over
  time. Grade as correct if the reported value equals the executor's **own**
  captured `count` for the `taxonKey=5219404&country=KE` query, and is a
  plausible positive number (e.g. ≥ ~1,000). Do **not** require the exact
  construction-time value.
- Global occurrence count: far larger (tens of thousands+). Same rule: must
  match the executor's own captured global `count`, must exceed the Kenya count
  (internal consistency: global ≥ country), and be plausibly large.
- A correct solution shows the country count is a strict subset of the global
  count (country ≤ global).

## 4. Expected Artifacts

- `/tmp_workspace/results/gbif_panthera_leo.json` — matched name, rank, taxon
  key, Kenya occurrence count, global occurrence count.
- `/tmp_workspace/results/gbif_evidence/` — request URL(s) + raw JSON for the
  match call and both occurrence queries.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                          | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Hop 1 done via `species/match` to resolve `Panthera leo` → taxon key, evidenced by saved request URL + raw JSON.                              | 0.25   |
| CP2 | Correct taxon key `5219404` (rank SPECIES) reported and used as the key for hop 2.                                                            | 0.20   |
| CP3 | Hop 2 done via `occurrence/search` (or `occurrence/count`) **keyed by taxonKey** with `country=KE`; a Kenya count obtained from the API.       | 0.25   |
| CP4 | Global occurrence count for the same key obtained; counts are internally consistent (Kenya ≤ global; both match captured responses).           | 0.20   |
| CP5 | `gbif_evidence/` makes the two-hop pull reproducible.                                                                                          | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if occurrence data was obtained by **scraping the gbif.org
  web UI** or a third-party site instead of the API.
- **cap at `0.55`** if no `gbif_evidence/` is saved.
- **cap at `0.60`** if the executor skipped the name→key resolution and tried to
  query occurrences by name, or used a wrong/guessed taxon key.
- **cap at `0.40`** if the wrong species was resolved.
- **cap at `0.85`** if the reported counts are internally inconsistent (e.g.
  Kenya > global) or do not match the executor's own captured responses.

Do **not** cap or fail merely because:

- the counts exceed the construction-time figures — they grow; judge against the
  captured `count` values,
- the executor used `limit=0` vs `occurrence/count` facets — either yields the
  count,
- the executor used `curl`/python/agent-browser to hit the API.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4 satisfied, no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor resolved the key but hasn't queried
occurrences, queried only one of (Kenya / global), or hasn't saved evidence.

Prefer `fail` when, after follow-ups, the executor only scraped the web UI,
resolved the wrong species, or reported counts absent from any captured response.

## 8. Hidden Reference Assets

None shipped. Evaluate from `gbif_panthera_leo.json`, `gbif_evidence/`, and the
transcript.

## 9. Dynamic Content Note

The taxon key is stable; occurrence counts grow monotonically. Anchor on the key
+ mechanism + internal consistency (country ≤ global) and grade counts as
lower-bounds against the captured responses. Never hardcode an exact count.

## 10. Notes For Rationale

- When capping for skipped resolution, note whether the executor guessed a key
  or tried a name-based occurrence query.
- When scoring CP4, quote the Kenya and global `count` from the executor's own
  captured responses and confirm Kenya ≤ global.
- Guidance tags: `name_to_key_resolution`, `taxonkey_keyed_occurrence`,
  `monotonic_growing_count_lenient`, `country_subset_of_global`.
