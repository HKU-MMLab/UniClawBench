---
name: test-runner
license: MIT
description: >
  This skill should be used when the user needs to run, analyze, or report on
  automated test suites. It interprets test results from CI logs, JSON reports,
  or local test execution, identifies flaky tests, categorizes failures, and
  provides structured pass/fail summaries. Trigger phrases include "run tests",
  "check test status", "test results", "CI status", "test report".
---

# Test Runner Skill

> **GitHub**: [https://github.com/clawhub/test-runner](https://github.com/clawhub/test-runner)

Runs or interprets automated test results and produces structured reports.
Supports pytest, jest, mocha, go test, and generic JUnit XML. When test
execution is not possible (e.g., snapshot-only environments), the skill
reads CI metadata or test result JSON and produces a summary.

## Usage

Describe what you need in natural language:

```
"Check the test status for this PR"
"Summarize the CI results"
"Which tests are failing and why?"
"Is the test suite green?"
"Find flaky tests in the last 10 runs"
```

## Capabilities

1. **Parse test results** — reads pytest JSON, JUnit XML, or CI log fragments
2. **Categorize failures** — distinguishes genuine bugs from flaky tests and infra issues
3. **PR readiness check** — given PR metadata with CI status fields, reports whether tests pass
4. **Coverage summary** — extracts line/branch coverage from coverage reports

## Output Format

Returns a structured object with:
- `total_tests`, `passed`, `failed`, `skipped`, `flaky`
- `failures[]` — each with test name, error message, category
- `verdict` — "green", "red", or "flaky"

## When to Use

Use this skill when you need to assess whether code changes are safe to merge
based on test results, or when producing a PR triage that considers CI status.
