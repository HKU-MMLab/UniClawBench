---
name: automate-excel
description: Automates reading, writing, merging, transforming, and validating Excel (.xlsx/.xls) files. Use when the user works with spreadsheets, .xlsx files, Excel data — for cleaning, joining, validating, deduplicating, aggregating, filtering, or auditing tabular data.
metadata:
  {
    "openclaw":
      {
        "version": "1.0.0",
        "author": "zways",
        "license": "MIT-0",
        "tags": ["excel", "xlsx", "pandas", "openpyxl", "validation", "audit"],
        "category": "office-automation"
      }
  }
---

# Automate Excel

Automates reading, writing, merging, transforming, and validating Excel
(`.xlsx` / `.xls`) files. Use when the user is working with spreadsheets and
needs to clean / join / validate / aggregate tabular data.

## Technical stack

* `openpyxl` — cell operations, formatting, formulas
* `pandas` — analysis, pivoting, group-by aggregations
* `xlrd` — legacy `.xls` read support

## Scripts (16)

| Script | Purpose |
| :-- | :-- |
| `merge_sheets.py` | Combine multiple Excel files or sheets into one table |
| `excel_to_csv.py` | Export a sheet to CSV |
| `csv_to_excel.py` | Convert CSV(s) to Excel (single → sheet, multi → sheets) |
| `filter_excel.py` | Filter rows by column conditions (`=`, `>`, `<`, contains) |
| `split_excel.py` | Split by row count or by column value into multiple files |
| `deduplicate_excel.py` | Drop duplicates by specified columns, keeping first/last |
| `aggregate_excel.py` | Group by column and aggregate (sum / count / mean / min / max) |
| `validate_excel.py` | Validate required columns, duplicate keys, empty rows |
| `select_columns.py` | Select / rename / sort columns |
| `merge_tables.py` | Merge two tables by key column (VLOOKUP-style) |
| `transpose_excel.py` | Transpose rows and columns |
| `template_fill.py` | Fill templates with `{{column_name}}` placeholders |
| `rename_sheets.py` | Rename worksheets |
| `vlookup_multi.py` | Multi-table VLOOKUP via successive left joins |
| `format_conditional.py` | Apply conditional formatting |
| `format_columns_as_text.py` | Format columns as text to prevent scientific notation display |

## When to use this skill

* QA-ing a workbook handed off by another teammate before reviewing it.
* Validating that required columns are present and key columns are unique.
* Merging or joining multiple sheets / files into one canonical table.
* Aggregating / summarizing tabular data into pivot-style outputs.
* Auditing dashboards: cross-checking that pivot/chart numbers tie back to raw data.

## Patterns

### Read + validate a workbook

```python
import pandas as pd
df = pd.read_excel("workbook.xlsx", sheet_name="Raw")
# Required columns must all be present
required = {"OrderID", "Region", "Amount"}
missing = required - set(df.columns)
assert not missing, f"missing columns: {missing}"
# Key column should be unique
assert df["OrderID"].is_unique, "OrderID duplicates detected"
# No fully-blank rows
assert not df.isna().all(axis=1).any(), "fully-blank rows present"
```

### Re-derive a pivot from raw data

```python
import pandas as pd
df = pd.read_excel("workbook.xlsx", sheet_name="Raw")
pivot = df.pivot_table(index="Region", columns="Product",
                       values="Amount", aggfunc="sum", fill_value=0)
pivot.loc["Total"] = pivot.sum(numeric_only=True)
pivot["Total"] = pivot.sum(axis=1)
print(pivot)
```

### Cross-check a sheet against the raw

```python
import pandas as pd
raw = pd.read_excel("workbook.xlsx", sheet_name="Raw")
dashboard = pd.read_excel("workbook.xlsx", sheet_name="Pivot")
# Compare the dashboard total against the raw sum
raw_total = raw["Amount"].sum()
dashboard_total = dashboard.loc[dashboard["Region"] == "Total", "Total"].iloc[0]
delta = abs(raw_total - dashboard_total)
print(f"raw_total={raw_total}, dashboard={dashboard_total}, delta={delta}")
```

## Runtime

This workspace injects the skill at `/root/skills/automate-excel`. The
required Python libraries (`openpyxl`, `pandas`, `xlrd`) are prepared by the
task setup service. Use the patterns above directly; do not run package
installation during the user task.
