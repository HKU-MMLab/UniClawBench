# Hidden Evaluation Rule — task_105_40_pypi_upgrade_web_audit

## 1. Grading Philosophy

The task is a live official-web verification against fixed PyPI target
versions. Do not require current latest package versions. Grade against
`upgrade_targets.json` and `ground_truth.expected_release_info`.

## 2. Task Contract

Required outputs:
- `/tmp_workspace/results/pypi_upgrade_audit.json`
- `/tmp_workspace/results/pypi_upgrade_report.md`
- one or more screenshots under `/tmp_workspace/results/pypi_screenshots/`

## 3. Checkpoint Rubric

Checkpoints, total 1.00:
- 0.12 Required output placement/parseability: JSON parses, Markdown is
  readable, and screenshot directory contains valid PNG evidence.
- 0.24 Package/version coverage: all five packages are present with
  correct current_pin and target_version from the input files.
- 0.18 Official PyPI metadata: for each target version, report includes
  official PyPI URL, first upload time/date, requires_python, file count,
  and wheel/sdist availability matching hidden ground truth or current
  PyPI API if metadata is unchanged.
- 0.12 Browser/live-web evidence: screenshots or transcript show real
  official PyPI pages were opened for multiple packages; API-only work
  can support metadata but does not earn full browser evidence.
- 0.10 Upgrade risk judgment: gives a concise risk note per dependency
  grounded in version jump size, Python requirement, and package role.
- 0.08 JSON schema quality: top-level `packages` array plus
  `summary`, with numeric file_count and booleans for has_wheel/has_sdist.
- 0.08 Markdown report quality: includes comparison table, source URLs,
  checked date, and final recommendation order.
- 0.08 Cross-artifact consistency across JSON, Markdown, screenshots,
  and input target file.

## 4. Scoring Policy / Score Caps

Caps:
- Cap at 0.55 if `pypi_upgrade_audit.json` is missing or invalid.
- Cap at 0.70 if fewer than four target packages are correctly covered.
- Cap at 0.75 if no official PyPI browser/page evidence is saved.
- Cap at 0.50 if the report grades against current latest instead of
  the fixed target versions.
- If PyPI has a temporary outage, documented attempts with screenshots
  or curl errors may receive partial evidence credit; fixed input and
  hidden ground truth should still guide the report.
