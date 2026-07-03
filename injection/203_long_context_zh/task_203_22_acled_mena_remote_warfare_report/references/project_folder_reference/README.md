# MENA Conflict Geography

This repository contains an interactive data report examining whether the rise of drones and other remote attacks in the Middle East and North Africa has been accompanied by a spatial shift from border-proximate conflict toward attacks on capital areas.

Public webpage: <https://lexieliujy.github.io/POLI3148_PS1/>

Repository: <https://github.com/lexieliujy/POLI3148_PS1>

## Project note

This reference package contains the data, notebooks, and public webpage for the analysis.

The analysis is descriptive. It does not claim to establish a causal relationship between remote attack technologies and the geography of conflict. The report uses ACLED event data and Natural Earth boundary data to build reproducible spatial indicators, then compares patterns across time and space.

For authoritative data, documentation, and citation information, use the original sources directly:

- ACLED: <https://acleddata.com/>
- Natural Earth: <https://www.naturalearthdata.com/>

## What's in this repo

| File | Purpose |
| --- | --- |
| [`docs/index.html`](docs/index.html) | Final interactive HTML report served through GitHub Pages. |
| [`code/01_data_cleaning.ipynb`](code/01_data_cleaning.ipynb) | Cleans the raw ACLED data, creates spatial indicators, and writes the processed and summary CSV files. |
| [`code/02_analysis.ipynb`](code/02_analysis.ipynb) | Reproduces the headline checks, analysis tables, and figures used in the report. |
| [`data/ACLED Data_MENA_Raw.csv`](data/ACLED%20Data_MENA_Raw.csv) | Raw ACLED MENA export used as the primary source data. |
| [`data/acled_mena_processed.csv`](data/acled_mena_processed.csv) | Cleaned event-level dataset with added spatial and event-type indicators. |
| [`data/yearly_shift_summary.csv`](data/yearly_shift_summary.csv) | Yearly summary table used for the time-series figures. |
| [`data/spatial_bucket_summary.csv`](data/spatial_bucket_summary.csv) | Summary table comparing capital areas, border-proximate areas, and other areas. |
| [`data/country_pattern_summary.csv`](data/country_pattern_summary.csv) | Country-level summary statistics. |
| [`data/support/ne_50m_admin_0_countries.zip`](data/support/ne_50m_admin_0_countries.zip) | Natural Earth country boundary data used for border-distance calculations. |
| [`requirements.txt`](requirements.txt) | Python packages needed to run the two notebooks on another computer. |

## Running the project

Install the required Python packages first:

```bash
pip install -r requirements.txt
```

Run the notebooks in order:

```bash
# 1. Open and run the data-cleaning notebook
code/01_data_cleaning.ipynb

# 2. Open and run the analysis notebook
code/02_analysis.ipynb
```

The first notebook writes:

- `data/acled_mena_processed.csv`
- `data/yearly_shift_summary.csv`
- `data/spatial_bucket_summary.csv`
- `data/country_pattern_summary.csv`

The second notebook reads those files and reproduces the analysis checks and figures.

Large CSV files are tracked with Git LFS. If a CSV opens as a small text pointer beginning with `version https://git-lfs`, run:

```bash
git lfs pull
```

## Report Output

The finished interactive report is stored in `docs/index.html`.

## Data

Primary source: ACLED event data for the Middle East and Northern Africa.

Support data: Natural Earth 1:50m administrative country boundaries.

Analytical sample:

- Region: ACLED `Middle East` and `Northern Africa`
- Years used in the report: 1997-2024
- Cleaned sample size: 343,901 event observations
- Spatial definitions:
  - `Capital-area event`: an event located in a national capital or a sub-location beginning with the capital's name.
  - `Border-proximate event`: an event within 50 km of an international land border.
  - `Spatial bucket`: capital areas, border-proximate areas, and other areas.

## Research motivation

The research question was developed from my interest in the international relations of the Middle East and North Africa. In studying recent regional conflicts and reviewing example ACLED analysis materials, I noticed the sharp increase in remote attacks, especially drone-related violence. This led me to ask whether the growing use of remote attack methods might be connected to changing conflict intensity and strategic behavior in the MENA region.

The analysis ultimately does not support my initial expectation of a broad shift from border-proximate conflict toward capital targeting. I still treat the question as analytically useful because the negative finding clarifies what the rise of remote violence does and does not appear to change in the spatial organization of conflict.

## Main analysis

The report asks whether remote violence is associated with a shift from frontier conflict toward capital targeting.

The report highlights several findings:

1. Remote attacks expanded, but the strategic center of conflict remained border-oriented.
2. MENA Looks Like Layered Conflict, Not a Clean Spatial Transition

The main descriptive conclusion is that border-linked space remains the heavier conflict geography in MENA relative to capital space.

## Design choices

- Single public report page: `docs/index.html`.
- GitHub Pages uses the `/docs` folder so the report is accessible as a webpage.
- The notebooks are self-contained: data cleaning logic is in `01_data_cleaning.ipynb`, and analysis / figure logic is in `02_analysis.ipynb`.

## Reference Note

This directory is a supervisor-side quality reference. It should be used to compare data-cleaning logic, spatial indicators, analysis structure, and report quality; it is not shown to the executor.
