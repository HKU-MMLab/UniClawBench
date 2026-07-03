# Hidden Evaluation Rule — task_203_22_acled_mena_remote_warfare_report

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should judge whether the executor obtained or credibly worked with ACLED-style MENA data, constructed the requested spatial indicators, analyzed remote warfare patterns, and built a usable interactive HTML report. The final report's analytical and visualization quality matters; a visually present but geographically wrong or empty map should not receive high credit.

## 2. Task Contract

The public task asks for ACLED MENA data for the specified date range/event types, capital-area and border-proximate variables, factor analysis or similar indicator decomposition, an ACLED-style approximately 1,500-word interactive HTML report, and at least three chart families: remote/air-drone trend, capital-vs-border composition, and a time-slider geographic scatter map.

Completion means a report HTML and supporting outputs exist, the indicators and analysis are documented, and the interactive visualizations render with meaningful data.

## 3. Source-Selection and Target-Resolution Rules

Use ACLED data when accessible through the configured account. If ACLED access/export is blocked, the executor may use documented fallback data only if it clearly labels the limitation and avoids fabricating rows. Capital-area and border-proximate indicators should be derived from location/country/capital/border logic rather than arbitrary labels.

## 4. Ground-Truth Snapshot

Hidden references include a reference project folder with data-cleaning/analysis notebooks, processed MENA summaries, shapefile support, and HTML report/map examples. Exact row counts can differ because ACLED exports and access windows may change, but the method shape and qualitative findings are anchored there.

## 5. Checkpoint Rubric

- 0.15 Data access: obtains usable ACLED MENA data or documents a genuine access/export block while preserving privacy.
- 0.20 Spatial indicators: correctly constructs capital-area and border-proximate indicators from location/capital/border logic.
- 0.15 Remote warfare analysis: identifies remote warfare / air-drone variables and performs a meaningful factor-style or indicator-decomposition analysis.
- 0.20 Visualizations: produces the required charts with populated data, including a time-varying map whose points appear in the MENA region rather than at wrong coordinates or empty locations.
- 0.20 Report quality: coherent research question, methodology, findings, discussion, conclusion, ACLED-like style, and approximately requested length.
- 0.10 Render/self-check: evidence that the HTML opens and interactive elements render.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failures that invalidate the empirical report or make the HTML impossible to audit; partial analytical weaknesses should be scored through the rubric.

If the interactive map is blank, has no time variation, or places most points outside the expected region because of coordinate reversal/parsing errors, cap at 0.65. If no real data is used and the report is mostly invented, cap at 0.45. If the required spatial indicators are entirely absent, cap at 0.65. If the HTML is missing, cannot be opened, or contains only static placeholder content, cap at 0.60. If ACLED access fails but the executor documents a serious attempt and builds a clearly labeled partial report from non-confidential fallback evidence, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer `continue` when data access is incomplete but recoverable, indicators are missing, visualizations have not been rendered, or the report lacks a self-check. Prefer `fail` when the final report is fabricated, map coordinates are materially wrong, ACLED/privacy handling is unsafe, or required outputs are missing.

## 8. Hidden Reference Assets

- `ground_truth.json`: expected method, chart families, quality checks, and acceptable access-block handling.
- `project_folder_reference/`: reference implementation with notebooks, data summaries, support shapefile, and HTML report/map examples.

## 9. Dynamic Content Note

ACLED exports, row counts, and site/login behavior can change. Do not require exact row counts or identical figures. Require method consistency, meaningful data, correct geography, and honest documentation of access limitations.
