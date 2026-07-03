# Hidden Evaluation Rule — task_203_23_global_earthquake_report

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor built a correct, genuinely interactive HTML visualization and analysis from the injected USGS earthquake snapshot. The core tests are: (a) the data comes from the injected GeoJSON, (b) the map places epicenters in geographically correct locations (no coordinate reversal, no collapse to (0,0)), (c) the time control actually filters events, and (d) the magnitude chart and any stated counts match the snapshot. A static or broken page, or generic seismology prose not tied to the snapshot, should score poorly.

## 2. Task Contract

The public task gives the executor a frozen USGS GeoJSON snapshot (`sources/usgs_data/earthquakes_m45_past30days.geojson`, M4.5+ past 30 days) and asks for a single self-contained interactive HTML at `/tmp_workspace/results/earthquake_report.html` containing: a geographic epicenter map, a working time control over the ~30-day window, a magnitude distribution chart, and a short written analysis (e.g. Ring-of-Fire clustering).

Completion means the HTML opens, the three interactive elements work, points are geographically correct, and the analysis is grounded in the snapshot.

## 3. Source-Selection and Target-Resolution Rules

The visualization must be built from the injected GeoJSON. Coordinates are `[longitude, latitude, depth_km]` — longitude first. A map that swaps lon/lat (placing points in the wrong hemisphere) or collapses everything to one spot fails the geographic-correctness check. Re-pulling live data is acceptable only if methodology is sound and clearly noted, but the injected snapshot is the ground-truth reference.

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`): the snapshot has 523 events, magnitudes 4.5-7.8, window ~2026-05-21 to 2026-06-20, largest ~M7.8 near the Philippines, and ~80% of events fall along the Pacific Ring of Fire by a rough lon/lat heuristic. Magnitude distribution is heavily skewed toward M4.5-5.0. Small filtering differences are fine; counts wildly off, or coordinates reversed, indicate an error.

## 5. Checkpoint Rubric

- 0.20 Data grounding: loads the injected GeoJSON; stated counts/extremes match it (e.g. ~523 events, max ~M7.8 Philippines).
- 0.25 Map correctness: epicenter map renders with points in geographically correct positions (Ring-of-Fire pattern visible, no lon/lat swap, no all-at-(0,0)).
- 0.20 Working time control: a slider or animation over the ~30-day window that visibly changes which events are displayed (not a static decoration).
- 0.15 Magnitude chart: a magnitude distribution chart that matches the data (skew toward M4.5-5.0).
- 0.10 Analysis: short written analysis grounded in this snapshot (Ring-of-Fire clustering, largest event, distribution), not generic prior-knowledge prose.
- 0.10 Deliverable: a single openable `earthquake_report.html` at the requested path that renders without missing-asset/JS errors that break the visualization.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If the map has reversed coordinates, points concentrated in the wrong region, or collapses to a single point, cap at 0.60. If the page is static with no working time control, cap at 0.65. If the magnitude chart is blank or absent, cap at 0.70. If the HTML cannot be opened or is broken, cap at 0.40. If the report's numbers are fabricated or contradict the snapshot, cap at 0.55. If the executor ignores the injected snapshot and writes generic earthquake content, cap at 0.50.

## 7. Continue vs Fail Guidance

Prefer `continue` when the HTML exists but an element (time control, chart) is incomplete or a count is unverified. Prefer `fail` when the map is geographically wrong throughout, the page is static/broken, or the output is generic prose with no real visualization.

## 8. Hidden Reference Assets

- `ground_truth.json`: snapshot description, anchor values, coordinate convention, expected analysis points.
- `sources/usgs_data/earthquakes_m45_past30days.geojson`: the authoritative injected snapshot (also a visible task source).

## 9. Dynamic Content Note

The live USGS feed changes daily; the injected snapshot is frozen and authoritative. Judge against the snapshot. Chart/map libraries and styling may vary; require interactivity, geographic correctness, and data-match rather than a specific toolkit.
