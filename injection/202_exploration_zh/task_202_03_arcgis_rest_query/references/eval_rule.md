# Hidden Evaluation Rule — Exploration v2 · ArcGIS REST service query (read metadata, don't assume fields)

## 1. Grading Philosophy

This is an **interface-exploration + query-construction** task graded by
**outcome plus mechanism evidence**.

The executor must:

- explore the ArcGIS REST service to discover the **correct layer** (US states)
  and that layer's **real field names** (they cannot be guessed), and
- run the service's **query operation** to return the requested filtered set,
  with auditable evidence (request URLs + raw JSON).

The deliberate traps — which make this non-trivial — are: (a) the service has
four layers and the states layer is **not** the obvious first one, and (b) the
intuitive field name (`POP2007`, `population`, etc.) is **wrong**; the real
field is `pop2000`. Reading metadata is mandatory.

This dataset is a **static sample server**, so the matching set is stable; but
the rubric still anchors on mechanism + structural correctness so it survives
any future field-label or sample-data refresh.

## 2. Task Contract

Start from `https://sampleserver6.arcgisonline.com/arcgis/rest/services/USA/MapServer`.
Find the states layer, learn its real field names, and query for states with
year-2000 population `> 10,000,000`. Report layer id+name, the population field
name, the match count, and the sorted matching list. Save `arcgis_states.json`
and an `arcgis_evidence/` folder (service metadata + layer metadata + query
URLs and raw responses).

## 3. Ground-Truth Reference

### 3.1 Service structure (stable)

`MapServer` layers:

- `0` Cities
- `1` Highways
- `2` **States**  ← the correct layer
- `3` Counties

### 3.2 Field name (the key trap)

The States layer's year-2000 population field is **`pop2000`** (lowercase).
Note the field list also contains `pop00_sqmi`; the population *count* field is
`pop2000`, not the per-sqmi density. Guessing `POP2007`/`POP2000`/`population`
yields a query error or empty result — the executor must read
`.../MapServer/2?f=json` to learn the real name.

### 3.3 Correct query & result (current sample data)

Query: `.../MapServer/2/query?where=pop2000>10000000&outFields=state_name,pop2000&returnGeometry=false&f=json`

Matching states: **7**, sorted descending:

| state_name   | pop2000   |
| ------------ | --------- |
| California   | 33871648  |
| Texas        | 20851820  |
| New York     | 18976457  |
| Florida      | 15982378  |
| Illinois     | 12419293  |
| Pennsylvania | 12281054  |
| Ohio         | 11353140  |

Cross-check: `&returnCountOnly=true` returns `{"count":7}`.

If the sample server's data is ever refreshed and the exact list shifts, grade
on (a) correct layer + field discovery, (b) a correctly-formed `where=pop2000>10000000`
query, and (c) internal consistency between the saved count and the saved list
from the executor's own evidence — not on the frozen seven names above.

## 4. Expected Artifacts

- `/tmp_workspace/results/arcgis_states.json` — layer id/name, population field
  name, match count, sorted matching list (name + population).
- `/tmp_workspace/results/arcgis_evidence/` — request URLs + raw JSON for
  service metadata, layer-2 metadata, and the query.

## 5. Checkpoint Rubric

| ID  | What matters (outcome)                                                                                                                                  | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct states layer identified as **layer 2 / "States"**, evidenced by a fetch of the service metadata.                                                | 0.20   |
| CP2 | Correct population field name **`pop2000`** discovered from the layer-2 metadata (not assumed); evidence shows the layer field list was read.            | 0.25   |
| CP3 | A well-formed query operation was actually called against layer 2 with `where=pop2000>10000000`, evidenced by the saved query URL + raw response.        | 0.25   |
| CP4 | Result is correct & internally consistent: match count = number of rows in the saved list; sorted descending; values come from the API response.        | 0.20   |
| CP5 | `arcgis_evidence/` makes the exploration reproducible (metadata + query URLs and raw responses saved).                                                   | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the answer was produced **without calling the query
  operation** (e.g. the executor dumped the whole layer and eyeballed, used a
  map screenshot, or hand-listed states from memory).
- **cap at `0.50`** if the wrong layer (Cities/Counties/Highways) was queried.
- **cap at `0.55`** if the field name was assumed (e.g. `POP2007`) and the query
  errored/returned empty, with no metadata-read recovery.
- **cap at `0.60`** if no `arcgis_evidence/` is saved.
- **cap at `0.85`** if the count and the list disagree (internal inconsistency)
  or the list isn't sorted as requested while everything else is correct.

Do **not** cap or fail merely because:

- the executor used `where=pop2000 > 10000000` with spaces, `pop2000>1e7`, or
  added `orderByFields=pop2000 DESC` server-side — any correct filter is fine,
- the executor also pulled `returnCountOnly=true` as a cross-check (encouraged),
- the executor used `curl` / python / agent browser to hit the REST endpoints.

Pass requirements (`score >= 0.90`): CP1, CP2, CP3, CP4 satisfied, no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor is still enumerating layers, has read
metadata but not yet queried, or queried but hasn't saved structured output /
evidence.

Prefer `fail` when, after follow-ups, the executor never ran a query operation,
used the wrong layer with no recovery, or fabricated a list not backed by a
captured response.

## 8. Hidden Reference Assets

None shipped. Evaluate from `arcgis_states.json`, `arcgis_evidence/`, and the
transcript.

## 9. Dynamic Content Note

This is a static ArcGIS *sample* service, so dynamic-content excuses do not
apply to correctness; nonetheless grade primarily on mechanism + internal
consistency so the task survives a future sample-data refresh.

## 10. Notes For Rationale

- When capping for "no query operation", cite what the executor used instead
  (full-layer dump, screenshot, memory).
- Quote the field list from the executor's own layer-2 metadata response when
  scoring CP2.
- Guidance tags: `explore_service_metadata`, `discover_real_field_names`,
  `must_use_query_operation`, `count_list_consistency`.
