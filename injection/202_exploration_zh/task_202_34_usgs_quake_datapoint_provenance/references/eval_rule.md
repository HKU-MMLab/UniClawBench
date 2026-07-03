# Hidden Evaluation Rule — Exploration v2 · Earthquake attributes → canonical USGS event record (data provenance)

## 1. Grading Philosophy

A **data-provenance** task graded by **tracing loose attributes to the canonical
USGS event record + confirming its parameters**. The executor is given a few
attributes (M~9.1, Tohoku Japan, March 2011) and must reach the authoritative
USGS event (event id + page/API), not Wikipedia/news, and confirm magnitude,
coordinates, depth, origin time.

## 2. Task Contract

Find the official USGS record for the M~9.1 March 2011 Tohoku earthquake; report
the event id + page, magnitude, lat/lon, depth, origin time (UTC), and whether
the given attributes match. Save `quake_provenance.json`.

## 3. Ground-Truth Reference

- **Source:** USGS Earthquake Hazards Program (ANSS ComCat)
- **Event id:** **`official20110311054624120_30`** — "2011 Great Tohoku
  Earthquake, Japan"
- **Magnitude:** **9.1**
- **Coordinates:** lat **38.297**, lon **142.373**
- **Depth:** **29 km**
- **Origin time:** **2011-03-11T05:46:24.120Z** (epoch ms 1299822384120)
- **Links:** event page
  `https://earthquake.usgs.gov/earthquakes/eventpage/official20110311054624120_30/executive`,
  API `https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=official20110311054624120_30&format=geojson`

## 4. Expected Artifacts

- `/tmp_workspace/results/quake_provenance.json` — USGS event id + page,
  magnitude, coordinates, depth, origin time, match verdict, evidence chain.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | The canonical USGS event reached: event id `official20110311054624120_30` via USGS event page or FDSN API.        | 0.35   |
| CP2 | Magnitude 9.1 and origin time (2011-03-11 ~05:46 UTC) confirmed from the USGS record.                              | 0.25   |
| CP3 | Epicenter coordinates (lat 38.297 / lon 142.373, ±0.1°) and depth (29 km, ±5 km) confirmed from USGS.             | 0.25   |
| CP4 | Match verdict + evidence chain; used the USGS source, not Wikipedia/news as the canonical.                        | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the parameters are reported only from Wikipedia/NOAA/news
  and the USGS event record is never reached.
- **cap at `0.65`** if the right event is identified but no USGS event id is
  reported (the precise canonical handle).
- **cap at `0.70`** if coordinates/depth are wrong beyond tolerance or not
  confirmed from USGS.

Do **not** cap or fail merely because:

- the executor notes the historical M9.0 vs USGS M9.1 discrepancy — accept USGS
  9.1 as canonical; reporting 9.0 with the USGS-9.1 note is fine,
- the executor reaches it via the event page or the FDSN API,
- tiny coordinate/time differences within the stated tolerances.

Pass requirements (`score >= 0.90`): CP1 (USGS event id), CP2 (mag + time), CP3
(coords + depth within tolerance), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the event is identified but the USGS record/id isn't yet
reached, or some parameters are unconfirmed.
Prefer `fail` when only Wikipedia/news is ever cited, or the wrong event is found.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — event id + parameters + tolerances.
  Supervisor-only.

## 9. Dynamic Content Note

The USGS event record is stable (historical event). Grade against the executor's
captured USGS evidence; tolerances above absorb minor catalog revisions.

## 10. Notes For Rationale

- When capping at 0.55, name the secondary source the executor stopped at.
- Guidance tags: `data_point_provenance`, `usgs_event_id`,
  `confirm_parameters_from_source`, `secondary_sources_capped`.
