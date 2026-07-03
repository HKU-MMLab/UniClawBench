# Hidden Evaluation Rule — task_105_22_ai_framework_q1_2026

## 1. Grading Philosophy

Grade on whether the deliverables answer the user's actual question:
"compare these 5 LLM agent frameworks on Q1 2026 community traction and
tell me which to pick, with a reasoned recommendation." The executor is
free to choose filenames, JSON shape, ranking methodology, and which exact
signals to collect — what matters is that the comparison is **grounded in
real Q1 2026 data**, identifies a winner with reasoning, and the per-repo
numbers are roughly correct.

Anchor facts come from `ground_truth.json`. Q1 2026 is closed historical
state — counts are immutable. Tolerances are generous (±20%) on dynamic
dimensions because the executor may use different methodologies (e.g.
HN Algolia query phrasing, Stack Overflow tag vs free-text search).

## 2. Task Contract

The user wants:
- Q1 2026 (2026-01-01 .. 2026-03-31) traction metrics for FIVE
  frameworks: `langchain-ai/langchain`, `run-llama/llama_index`,
  `crewAIInc/crewAI`, `pydantic/pydantic-ai`, `langchain-ai/langgraph`.
- A comparison report identifying a winner with reasoning.
- Some signal of "team breadth" (core contributors and what other repos
  they own) is welcome but secondary.

Required deliverables (any sensible filename under `/tmp_workspace/results/`):
- A **structured data file** with per-framework metrics for the 5 repos.
- A **ranking artefact** (CSV / table / embedded ranking in the report)
  showing the 5 frameworks ordered by some sensible composite score.
- A **comparison report** (markdown) with the recommendation.

NO snapshot file. NO mock service. NO populate step. Executor must hit
live APIs.

## 3. Source-Selection Rules

Sensible source choices include but are not limited to:
- GitHub PRs / issues / releases via `gh api search/issues` and
  `gh api repos/<r>/releases?per_page=100`
- HN community signal via `https://hn.algolia.com/api/v1/search`
- Stack Overflow signal via `https://api.stackexchange.com/2.3/search/advanced`
- GitHub contributors via `gh api repos/<r>/contributors` and
  `gh api users/<login>` for `public_repos`

The executor may use other reasonable signals (Reddit, package downloads,
etc.) — the grader checks whether the comparison is **grounded** and
the numbers used are **roughly correct**, not the exact methodology.

`GITHUB_TOKEN` is set in the executor's environment.

## 4. Ground-Truth Anchors

Per-framework Q1 2026 reference numbers (from live fetch on 2026-05-02):

| repo | merged_prs | releases | issues | hn | so | breadth |
|---|---:|---:|---:|---:|---:|---:|
| langchain-ai/langchain | 611 | 64 | 368 | 153 | 26 |  85 |
| run-llama/llama_index  | 343 |  6 | 177 |  54 |  0 | 129 |
| crewAIInc/crewAI       | 280 | 28 | 185 |  87 |  1 | 248 |
| pydantic/pydantic-ai   | 294 | 36 | 358 |  16 |  2 | 629 |
| langchain-ai/langgraph | 256 | 42 | 130 |  72 | 13 | 198 |

Cross-validation facts:
- **langchain-ai/langchain** dominates the 5 traction signals (highest on
  PRs, releases, issues, HN, SO).
- **pydantic/pydantic-ai** has by far the highest team breadth (samuel
  colvin alone has > 300 public repos).
- **langchain-ai/langgraph** has the highest PR/issue ratio (best signal
  of "shipping faster than complaints arrive").

## 5. Checkpoint Rubric

Weights sum to 1.0. Each checkpoint grades on **goal achievement**, not
field-name compliance. Use jq / grep flexibly.

- 0.09 — **All 5 frameworks present** in the structured data with
  recognisable repo names (set equality on the 5 expected `owner/name`
  strings; substring matching is fine — `langchain` / `llama_index` /
  `crewAI` / `pydantic-ai` / `langgraph` all appear). Data covers the
  Q1 2026 window (2026-01-01..2026-03-31; the dates appear somewhere in
  the data file or report).

- 0.13 — **PR / release / issue counts are roughly correct.** For each
  of the 5 frameworks, the executor's reported `q1_merged_prs`,
  `q1_releases`, and `q1_issues_opened` (or any equivalent labelled
  fields) are within ±20% of ground_truth. Scoring: at least 12 of the
  15 cells (5 repos × 3 metrics) within tolerance → 0.09; ≥ 14 within
  tolerance → 0.11; all 15 → 0.13.

- 0.09 — **HN traction signal is present and reasonable.** Per-framework
  HN story count appears for all 5 frameworks AND langchain has the
  highest HN count (langchain >> any other on HN is the stable pattern).
  Tolerance ±30% on absolute counts.

- 0.09 — **Stack Overflow signal is present.** Per-framework SO Q1
  question count appears for all 5 frameworks (any value; even zero is a
  valid answer for some frameworks). Langchain should be highest on SO
  too. Partial 0.04 if SO numbers present but langchain is not the top.

- 0.13 — **Composite ranking is computed and langchain-ai/langchain
  comes out on top.** A ranking artefact (CSV / table) lists the 5
  frameworks in some order; langchain is rank 1 / overall top / "winner"
  per the executor's chosen scoring. The user's specified methodology is
  the arithmetic mean of per-signal ranks across {q1_merged_prs,
  q1_releases, q1_issues_opened, hn_q1_stories} — under this scheme
  langchain has the lowest (best) average rank because it tops all 4
  signals. The grader does not require this exact formula but the
  resulting top-1 must be langchain. Partial 0.06 if a ranking is
  produced but langchain is not first.

- 0.09 — **Team breadth signal is present.** For each framework, some
  measure of contributor breadth (top-N contributor logins + their
  combined `public_repos` count, or any equivalent) appears in the data.
  Bots (logins matching `[bot]`) should be filtered out. Partial 0.04 if
  breadth appears for ≥ 3 of 5 frameworks.

- 0.10 — **Cross-framework Python dependency overlap analysis is
  present and correct.** The executor must have actually fetched a
  per-framework runtime dependency list (5 dep files visible under
  `/tmp_workspace/results/` OR an equivalent per-framework `dependencies`
  array in the data artefact, sourced from the canonical pyproject.toml
  at: `libs/langchain/pyproject.toml` for langchain, `libs/langgraph/
  pyproject.toml` for langgraph, `lib/crewai/pyproject.toml` for crewAI,
  `pydantic_ai_slim/pyproject.toml` for pydantic-ai, and the root +
  `llama-index-core/pyproject.toml` for llama_index). The data /
  report MUST include a `shared_in_3plus_frameworks` (or equivalently
  named) array AND identify `pydantic` as appearing in ≥4 of 5
  frameworks (the universal "ecosystem hub" — actually present in all
  5, but ≥4 accepted to absorb dep-extraction edge cases). Acceptable
  signals: explicit phrasing like "pydantic is the universal hub" /
  "pydantic 是所有框架共用的基础" / a JSON field
  `most_shared_dep: "pydantic"`. Other packages plausibly in the ≥3
  set: `httpx`, `pyyaml`. Partial 0.05 if dep lists exist for ≥4 of 5
  frameworks but the explicit hub identification (pydantic in the
  shared set OR named as the most-shared) is missing. Partial 0.03 if
  only 1-2 framework dep lists were fetched.

- 0.09 — **Cross-validation findings are stated.** The report explicitly
  identifies langchain as the dominant framework on traction signals
  (some phrasing like "全方位领先" / "leads on all signals" / "rank 1
  across the board") AND notes pydantic-ai has the highest team breadth.
  Partial 0.04 if only one of the two findings is mentioned.

- 0.09 — **Comparison report is present and substantive.** Markdown
  exists; mentions all 5 framework names; cites at least one numeric
  metric per framework (any quantitative anchor); ends with a clear
  selection recommendation paragraph (which framework to choose, with
  reasoning).

- 0.10 — **The recommendation is defensible.** The report's final
  recommendation is langchain (the data supports it) OR makes a
  reasoned case for an alternative based on a specific narrower need
  (e.g. "if our team values graph-based orchestration, langgraph because
  of its higher PR/issue ratio"). Vague non-recommendations score 0.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- Neither structured data nor ranking produced → 0.30.
- Output fabricates values not derivable from live APIs → 0.40.
- `$GITHUB_TOKEN` value emitted to user-visible output → 0.30.
- Trace shows zero gh / curl calls (synthetic data only) → 0.40.
- Only ≤ 3 frameworks appear (executor failed to expand to 5) → 0.50.
- Stack Overflow OR HN dimension entirely missing on all frameworks
  → cap 0.65 each.

Pass requires the 5-frameworks checkpoint AND the PR/release/issue
checkpoint AND the ranking-langchain-on-top checkpoint AND the
recommendation checkpoint all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to fix
  the lowest-scoring deliverable.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

PR / release / issue counts and HN story counts for closed Q1 2026 are
historical totals and will not drift further. Tolerance is set to ±20%
to absorb methodology differences (e.g. inclusive vs exclusive endpoint
on the date window, query phrasing on Algolia, search/issues vs
GraphQL).

The contributor list and per-user `public_repos` count ARE dynamic but
the **rank ordering** between the 5 frameworks (pydantic-ai having the
highest team breadth is stable because samuelcolvin has many repos) is
checked instead of absolute numbers.

If GitHub / HN / Stack Exchange APIs are temporarily unavailable, the
supervisor MUST distinguish "executor failed" from "API outage". A
trace showing repeated 5xx responses is an outage, not an executor
failure — record `infra_error` in summary and avoid penalising.
