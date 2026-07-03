# Hidden Evaluation Rule — Exploration v2 · Cropped chart → canonical chart page + underlying data source (provenance)

## 1. Grading Philosophy

A **content-provenance** task graded by **correct canonical identification plus
a primary-source evidence chain**. The executor gets a chart image with the
**title and the data-source footer removed**. The visible curves + country
labels + units let the executor recognize the topic, but the real work — and the
discriminator — is tracing it to (a) the **canonical interactive chart page** and
(b) the **underlying data provider** that the cropped-off footer concealed. A
plain search of "CO2 emissions chart" returns countless lookalikes, so the
executor must reconstruct provenance, not pattern-match.

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/crop.jpg`, identify what the chart
measures + units, the canonical chart page (publisher's own, not a news reuse),
the underlying data provider, and a data-download link. Save
`chart_provenance.json` with conclusion + evidence chain.

## 3. Ground-Truth Reference

- **Chart:** "**Annual CO₂ emissions**" — annual total CO₂ emissions by
  country/region over time, in tonnes (excludes land-use change).
- **Canonical chart page:** **Our World in Data** grapher
  `https://ourworldindata.org/grapher/annual-co2-emissions-per-country`
- **Underlying data source:** the **Global Carbon Budget / Global Carbon
  Project** (e.g. "Global Carbon Budget 2025 / v15"), with major processing by
  Our World in Data — **this is the key provenance step the cropped footer hid**.
- **Data download:** `.../annual-co2-emissions-per-country.csv`
- Units: tonnes (chart axis shows "billion t").

## 4. Expected Artifacts

- `/tmp_workspace/results/chart_provenance.json` — measure + units, canonical
  chart URL, underlying data provider, data-download link, evidence chain.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct identification: annual CO₂ emissions by country over time (tonnes).                                       | 0.25   |
| CP2 | Canonical chart page reached: the OWID grapher 'annual-co2-emissions-per-country' (the publisher's own chart).     | 0.30   |
| CP3 | Underlying data provider named: Global Carbon Budget / Global Carbon Project (processed by OWID) — the hidden step. | 0.30   |
| CP4 | Evidence chain + a data-download/source link; units noted. Did not stop at a news reuse of the chart.              | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the executor stops at a news article / blog / slide that
  reused the chart and never reaches OWID's own grapher page.
- **cap at `0.60`** if it reaches the OWID chart page but never identifies the
  underlying data provider (Global Carbon Project) — the cropped-footer step is
  the point of the task.
- **cap at `0.50`** if the chart subject is misidentified (not CO₂ emissions by
  country).

Do **not** cap or fail merely because:

- the Global Carbon Budget version/year differs from "2025/v15" (accept naming
  the Global Carbon Project / Global Carbon Budget as the origin),
- the executor recognized the OWID house style as a clue (fine) as long as it
  confirms the specific grapher page,
- the executor used the visible country labels/units to identify the topic.

Pass requirements (`score >= 0.90`): CP1 (CO₂ by country), CP2 (OWID grapher
page), CP3 (Global Carbon Project as underlying source), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the chart topic is identified and the OWID page reached
but the underlying data provider isn't yet named, or only a reuse is found.

Prefer `fail` when the subject is misidentified, or only a secondary reuse is
ever cited with no path to OWID + its data source.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical chart + data source + crop origin.
  Supervisor-only.

## 9. Dynamic Content Note

OWID updates the underlying Global Carbon Budget version periodically; the chart
page URL and the data-provider identity (Global Carbon Project) are stable. Grade
against the executor's captured evidence; accept the current version it finds.

## 10. Notes For Rationale

- When capping at 0.60, note that the underlying Global Carbon Project source was
  not identified.
- Guidance tags: `chart_provenance`, `canonical_chart_page`,
  `underlying_data_provider_hidden_by_crop`, `reuse_is_secondary`.
