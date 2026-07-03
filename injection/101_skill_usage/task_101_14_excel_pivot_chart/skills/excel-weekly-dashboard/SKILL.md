---
name: excel-weekly-dashboard
description: Designs refreshable Excel dashboards (Power Query + structured tables + validation + pivot reporting). Use when you need a repeatable weekly KPI workbook that updates from files with minimal manual work.
metadata:
  {
    "openclaw":
      {
        "version": "1.0.0",
        "author": "kowl64",
        "license": "MIT-0",
        "tags": ["excel", "dashboard", "power-query", "pivot", "validation", "kpi"],
        "category": "office-automation"
      }
  }
---

# Excel weekly dashboards at scale

## PURPOSE

Designs refreshable Excel dashboards (Power Query + structured tables +
validation + pivot reporting).

## WHEN TO USE

* TRIGGERS:
  * "Build me a Power Query pipeline for this file so it refreshes weekly with no manual steps."
  * "Turn this into a structured table with validation lists and clean data entry rules."
  * "Create a pivot-driven weekly dashboard with slicers for year and ISO week."
  * "Fix this Excel model so refresh does not break when new columns appear."
  * "Design a reusable KPI pack that updates from a folder of CSVs."
* DO NOT USE WHEN…
  * You need advanced forecasting / valuation modeling (this skill is for repeatable reporting pipelines).
  * You need a BI tool build (Power BI / Tableau) rather than Excel.
  * You need web scraping as the primary ingestion method.

## INPUTS

* REQUIRED:
  * Source data file(s): CSV, XLSX, DOCX-exported tables, or PDF-exported tables (provided by user).
  * Definition of "week" (ISO week preferred) and the KPI fields required.
* OPTIONAL:
  * Data dictionary / column definitions.
  * Known "bad data" patterns to validate (e.g., blank PayNumber, invalid dates).
  * Existing workbook to refactor.

## OUTPUTS

* If asked for **plan only (default)**: a step-by-step build plan + Power Query steps + sheet layout + validation rules.
* If explicitly asked to **generate artifacts**:
  * `workbook_spec.md` (workbook structure and named tables)
  * `power_query_steps.pq` (M code template)
  * `refresh-checklist.md`

## WORKFLOW

1. Identify source type(s) (CSV/XLSX/DOCX/PDF-export) and the stable business keys (e.g., PayNumber).
2. Define the canonical table schema: required columns, types, allowed values, and "unknown" handling.
3. Design ingestion with Power Query: prefer Folder ingest + combine, with defensive "missing column" handling.
4. Design cleansing & validation: create `Data_Staging` query (raw-normalized) and `Data_Clean` query (validated).
5. Build reporting layer: pivot table(s) off `Data_Clean` with slicers.
6. Add a "Refresh Status" sheet: last refresh timestamp, row counts, query error flags.
7. STOP AND ASK THE USER if required KPIs are unspecified, source files lack stable keys, week definition is unclear, or PDF/DOCX extraction is unreliable.

## SAFETY & EDGE CASES

* Read-only by default: provide plan + snippets unless the user explicitly requests file generation.
* Never delete or overwrite user files; propose new filenames.
* Prefer "no silent failure": include row-count checks and visible error flags.
* For PDF/DOCX sources, require user-provided exported tables (CSV/XLSX).

## Runtime

This workspace injects the skill at `/root/skills/excel-weekly-dashboard`.
The required Python libraries (`openpyxl`, `pandas`) are prepared during task
setup. Use the workflow above as a planning guide; do not install packages
during the user task.
