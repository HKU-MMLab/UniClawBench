# Hidden Evaluation Rule — task_205_23_arxiv_paper_trail

## 1. Grading Philosophy

Grade on whether the deliverables answer the user's actual question:
"show me how Generative Agents (arxiv 2304.03442) has been received —
academic citations, code reproductions, and HN discussion." The executor
is free to choose filenames, JSON shape, and which exact signals to
collect. What matters is that the analysis (a) carries correct paper
metadata, (b) identifies real GitHub implementations and HN discussions,
and (c) the work is auditable (real API calls in the trace).

Anchor facts come from `ground_truth.json`. Paper metadata is immutable;
GitHub repo names and HN story IDs are immutable historical state.
Citation counts grow over time, so tolerances are one-sided generous.

## 2. Task Contract

The user wants:
- Basic paper metadata (title, authors, page count, etc.).
- Academic impact signal (citation count / S2 data).
- GitHub reception — open source implementations, top repo by stars.
- HN reception — discussion stories, top story by points.
- The first author's other notable work (a "top other paper" by citations).

Required deliverables (any sensible filename under `/tmp_workspace/results/`):
- A **structured data file** (JSON or equivalent) with the paper metadata
  + cross-source findings.
- An **analysis report** (markdown) tying the findings together.

Optional (NOT required for pass):
- A cross-source CSV or table.
- An annotated thumbnail PNG.

NO snapshot file. NO mock service. NO populate step. Executor must hit
live APIs.

## 3. Source-Selection Rules

Sensible source choices include but are not limited to:
- arxiv PDF: `wget` / `curl https://arxiv.org/pdf/2304.03442v2` then
  `pdftotext` + `pdfinfo` (poppler-utils) or any PDF library.
- arxiv API: `https://export.arxiv.org/api/query?id_list=2304.03442`.
- Semantic Scholar Graph API:
  `https://api.semanticscholar.org/graph/v1/paper/ARXIV:2304.03442`
  (note: `ARXIV:` prefix uppercase). Author papers via
  `/author/<id>/papers`.
- GitHub: `gh api search/repositories?q=generative+agents+simulacra`.
- HN: `https://hn.algolia.com/api/v1/search?query=...&tags=story`.

The executor may use other reasonable methods. Grader checks **facts**
not call signatures.

`GITHUB_TOKEN` is set in the executor's environment.

## 4. Ground-Truth Anchors

From `references/ground_truth.json`:
- Paper title: "Generative Agents: Interactive Simulacra of Human Behavior"
- arxiv ID: 2304.03442
- 6 authors, first = "Joon Sung Park"
- Page count: 22
- Publication date: 2023-04-07
- S2 citation count ≥ 3686 (was 3885 on 2026-05-02; grows over time)
- Top GitHub repo by stars: `joonspk-research/generative_agents`
- Top HN story id: 35517649 (~391 points)
- First author's top other paper (by citations): "Social Simulacra:
  Creating Populated Prototypes for Social Computing Systems"

## 5. Checkpoint Rubric

Weights sum to 1.0. Each checkpoint grades on **goal achievement**, not
field-name compliance.

- 0.13 — **Paper metadata is correct.** The data artefact contains the
  paper title (substring match on "Generative Agents" AND "Simulacra"),
  arxiv ID "2304.03442", and either page count = 22 OR an authors list
  whose first element is "Joon Sung Park". Partial 0.06 if title +
  arxiv ID present but authors / page count missing.

- 0.09 — **Academic citation signal is present.** Some Semantic Scholar
  derived value (citation count, citationCount, etc.) appears in the
  data AND is ≥ 3000 (sensible non-fabricated value; the real number
  was ~3885 at snapshot time and grows monotonically).

- 0.13 — **Top GitHub repo is correctly identified.** The string
  "joonspk-research/generative_agents" (or equivalent — case-insensitive
  substring match on "joonspk-research") appears in the data artefact
  AND is identified as the official author repo / paper-team's own
  reference implementation. The user explicitly asks for the author's
  own official repo (not a derivative project, fan reimplementation, or
  unrelated theme-game), so this string MUST be the top-flagged repo
  even if some downstream fork has more stars at snapshot time. Partial
  0.06 if the repo appears in the data but is not flagged as the
  author-official top recommendation.

- 0.09 — **Multiple GitHub repos are listed (not just one).** The data
  artefact shows at least 3 distinct GitHub repos found (even if only
  the top is named); the search wasn't capped at 1. Acceptable: any
  3-or-more entries from the typical top set
  (`joonspk-research/generative_agents`, `mkturkcan/generative-agents`,
  `nmatter1/smallville`, `QuangBK/generativeAgent_LLM`,
  `sethkarten/LLM-Economist`).

- 0.13 — **Top HN story is correctly identified.** The HN story_id
  "35517649" (or its URL `https://news.ycombinator.com/item?id=35517649`)
  appears in the data AND is identified as the top / rank-1 / highest-
  points story. Partial 0.06 if the story_id appears but is not flagged
  as top.

- 0.10 — **First author's top other paper is identified.** The string
  "Social Simulacra" (case-insensitive substring) appears in the data
  artefact, attributed to the first author's other work / top other paper.
  Methodology hint: Semantic Scholar `/author/<id>/papers` sorted by
  `citationCount` desc, exclude Generative Agents itself, take top-1.
  Partial 0.05 if the string appears anywhere in the data but the
  attribution to "first author other paper" is unclear.

- 0.10 — **Paper-to-implementation chronology analysis is present and
  correct.** The data artefact contains, for at least the top 3 GitHub
  implementations by stars, each one's `first_commit_date` (ISO 8601
  date) AND a `days_since_paper_publish` integer (gap from 2023-04-07
  to first commit). Methodology hint: `gh api repos/<r>/commits?per_page=1`
  to get the Link header's `rel="last"` page number, then
  `?per_page=1&page=<last>&sha=<branch>` to fetch the earliest commit's
  `commit.author.date`. Repos's `created_at` is also acceptable as a
  proxy when commits-pagination fails. The report MUST explicitly
  identify which of the top 3 implementations appeared FIRST. Stable
  ground-truth ordering at snapshot: `mkturkcan/generative-agents` is
  the EARLIEST of the typical top-3 (first commit 2023-04-11, just 4
  days after paper publication), `nmatter1/smallville` is second
  (~40 days), `joonspk-research/generative_agents` is the official
  author repo but was committed only ~107 days post-paper. Acceptable
  identification: the report says `mkturkcan/generative-agents` (or
  matching substring) was first / fastest / earliest reproduction with
  a `~4 days` (±3) lag value. Partial 0.05 if the chronology table
  exists for ≥2 of the 3 top repos AND the gaps are correct (±5 days)
  but the explicit "earliest reproduction" identification is missing.
  Partial 0.03 if only 1 repo's first-commit date appears.

- 0.13 — **Analysis report is present and substantive.** Markdown file
  exists; mentions the paper title (or a recognisable fragment); cites
  the top GitHub repo by name (joonspk-research); cites the top HN story
  (a points value > 100, or the story_id, or the URL); cites a citation
  count from S2 (any number ≥ 3000); ties the four-source picture
  together (academic + GitHub + HN, with at least one numeric anchor per
  source).

- 0.10 — **The report makes an explicit characterisation of paper
  impact.** Some explicit summary claim about reception (e.g. "highly
  cited", "widely reproduced", "received strong community attention",
  "影响力 / 反响热烈 / 引用量已破 X 千") with at least one numeric anchor
  backing it.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- Neither structured data nor analysis report produced → 0.30.
- Output fabricates values not derivable from live APIs → 0.40.
- `$GITHUB_TOKEN` value emitted to user-visible output → 0.30.
- Trace shows zero curl / gh / wget calls (synthetic data only) → 0.40.
- PDF was claimed but not actually downloaded (no file in /tmp_workspace
  or similar; metadata was hallucinated and is wrong) → 0.40.
- Semantic Scholar dimension entirely missing (no citation signal at
  all) → cap 0.65.
- HN dimension entirely missing → cap 0.65.

Pass requires the paper-metadata checkpoint AND the top-GitHub-repo
checkpoint AND the top-HN-story checkpoint AND the report-substance
checkpoint all satisfied.

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

Paper metadata (title, authors, page count, abstract) is immutable.
GitHub repo full_names and HN story_ids are immutable historical state.
Star ordering on the lower 4 GitHub ranks may shift, so the grader
only requires the top-1 (joonspk-research) to be correctly identified.

Semantic Scholar `citationCount` grows monotonically — the rubric
accepts any value ≥ 3000 (was ~3885 at snapshot time). The first
author's top other paper ("Social Simulacra") is by 2022 publication
and remains the dominant non-Generative-Agents citation in his bibliography.

If arxiv / Semantic Scholar / GitHub / HN APIs are temporarily
unavailable, the supervisor MUST distinguish "executor failed" from
"API outage". A trace showing repeated 5xx / 429 responses is an
outage, not an executor failure — record `infra_error` in summary and
avoid penalising. Note: Semantic Scholar applies aggressive rate
limits to unauthenticated callers — a single retry with a 5-second
back-off is reasonable.
