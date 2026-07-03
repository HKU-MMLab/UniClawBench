# Hidden Evaluation Rule — Exploration v2 · CO₂ data-point → canonical dataset row (data provenance)

## 1. Grading Philosophy

A **data-provenance** task graded by **tracing a loose number to the canonical
dataset + exact row, plus naming the underlying provider**. The executor is
given a value (Japan 2000 CO₂ ≈ 1.26 billion tonnes) with no citation. Searching
the raw number does not surface a canonical source — the executor must reason
about which dataset carries such a series, reach it, locate the Japan/2000 row,
verify the value, and name the underlying data provider that the citation hid.

## 2. Task Contract

Trace "Japan, 2000, ~1.26 billion tonnes CO₂" to its authoritative dataset +
specific series, the underlying provider, the exact value for Japan/2000, a
data link, and whether the figure checks out. Save `datapoint_provenance.json`.

## 3. Ground-Truth Reference

- **Dataset:** Our World in Data — "**Annual CO₂ emissions**"
  (`annual-co2-emissions-per-country`)
- **Underlying provider:** **Global Carbon Budget / Global Carbon Project**
  (processed by OWID)
- **Row:** `Japan, JPN, 2000` → **1,260,203,000 tonnes** (~1.26 billion t)
- **Links:** chart `https://ourworldindata.org/grapher/annual-co2-emissions-per-country`,
  CSV `.../annual-co2-emissions-per-country.csv`
- CSV row format: `Entity,Code,Year,Annual CO₂ emissions → Japan,JPN,2000,1260203000`

## 4. Expected Artifacts

- `/tmp_workspace/results/datapoint_provenance.json` — dataset + series,
  underlying provider, the Japan/2000 value, data link, check-out verdict,
  evidence chain.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct dataset identified: OWID "Annual CO₂ emissions" (annual-co2-emissions-per-country).                       | 0.30   |
| CP2 | The exact Japan/2000 row located and its value retrieved (~1.26 billion t) matching the canonical dataset.        | 0.30   |
| CP3 | Underlying provider named: Global Carbon Project / Global Carbon Budget (the citation step the clue omitted).      | 0.25   |
| CP4 | A data link + check-out verdict; reached the dataset itself, not a news/blog repeating the number.                | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the executor confirms the number only via a news/blog/stat
  aggregator and never reaches the OWID dataset.
- **cap at `0.60`** if the OWID dataset is reached + value matched but the
  underlying Global Carbon Project provider is never named.
- **cap at `0.55`** if no value is actually retrieved/matched for Japan 2000 (the
  executor asserts provenance without verifying the row).

Do **not** cap or fail merely because:

- the retrieved value differs slightly from 1,260,203,000 due to an OWID data
  re-release — accept the current OWID CSV value if it is ~1.26 billion t and
  matches the executor's own retrieval,
- the executor reaches the data via the CSV, the grapher, or the OWID API.

Pass requirements (`score >= 0.90`): CP1 (OWID dataset), CP2 (Japan/2000 value
matched), CP3 (Global Carbon Project named), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the dataset is reached but the row isn't yet matched, or
the provider isn't yet named.
Prefer `fail` when only a news/blog source is ever cited, or the dataset is wrong.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — dataset, row, value, provider. Supervisor-only.

## 9. Dynamic Content Note

OWID re-releases the Global Carbon Budget periodically; the dataset identity and
underlying provider are stable. Grade against the executor's captured value from
the current OWID data.

## 10. Notes For Rationale

- When capping at 0.60, note the underlying Global Carbon Project provider was
  not identified.
- Guidance tags: `data_point_provenance`, `canonical_dataset_row`,
  `underlying_provider_named`, `not_searchable_by_number`.
