# Hidden Evaluation Rule — task_205_30_arxiv_calibre_index

## 1. Grading Philosophy

Grade on whether the executor (a) ingested 8 real arxiv PDFs into Calibre,
(b) hit Semantic Scholar for live citation counts, AND (c) produced a
**real LibreOffice Calc spreadsheet that exercises the platform** —
formulas, conditional formatting on a flagged column, and an embedded
chart object. This is not a "dump fields into a CSV and convert" task.
The 8 arxiv IDs are immutable anchors; everything else is platform-depth
verification on the .ods file. Score caps in §6 override rubric totals.

## 2. Task Contract

Required deliverables under `/tmp_workspace/results/`:

- `library/` — populated Calibre library directory (`metadata.db` plus
  ≥8 imported book records).
- `index.ods` — LibreOffice Calc spreadsheet, real ODF zip, with:
  * data for all 8 arxiv_ids in alphanumeric order;
  * at least one **formula cell** (table:formula in content.xml — e.g.
    `=AVERAGE(...)`, `=SUM(...)`, `=IF(...)`);
  * **conditional formatting** on the citation_count column (a
    `style:conditional-format` / `calcext:conditional-format` block in
    styles.xml or content.xml flagging cells where citations > 1000);
  * an **embedded chart object** (`Object 1/` subdirectory inside the
    .ods zip with chart `content.xml`, plus a `META-INF/manifest.xml`
    entry with `application/vnd.oasis.opendocument.chart`);
  * columns covering at minimum arxiv_id, title, first_author,
    author_count, page_count, citation_count.
- `papers.json` — JSON `{"papers": [...]}` with 8 entries, each having
  `arxiv_id`, `title`, `first_author`, `author_count`, `page_count`,
  `citation_count`, sorted ascending by `arxiv_id`.

There is NO snapshot file, NO mock service. `sources: []` is intentional.

## 3. Source-Selection Rules

- arxiv API: `curl "https://export.arxiv.org/api/query?id_list=<id>"`
  for metadata; `wget https://arxiv.org/pdf/<id>` for PDFs.
- poppler-utils: `pdfinfo` for page counts; `pdftotext -l 1 <pdf> -`
  for first-page text (or parse arxiv API XML `<author>` tags).
- Semantic Scholar (no key needed):
  `curl "https://api.semanticscholar.org/graph/v1/paper/ARXIV:<id>?fields=citationCount"`
  Retry on HTTP 429.
- Calibre: `calibredb add --library-path=...`,
  `calibredb list --library-path=... --for-machine`.
- LibreOffice Calc: any path that produces a real .ods (headless
  conversion via `soffice --headless`, odfpy / pyexcel-ods3, or a
  template). The .ods MUST contain real formula cells, conditional
  formatting rules, and an embedded chart object — a CSV converted
  via `soffice --convert-to ods` will fail this requirement because it
  has no formulas, no conditional formatting and no chart.

NO snapshot under `/tmp_workspace/clawbench/` is used or expected.
NO API keys are required.

## 4. Ground-Truth Anchors

Structured expected answer at `references/ground_truth.json`:

- 8 immutable `arxiv_ids`.
- Per-paper canonical `title`, `first_author`, `author_count` (±1
  tolerance), `page_count` (±2 tolerance), `citation_count`
  (recorded value with ±10% tolerance and a 0.95× lower floor —
  citations grow over time, never shrink meaningfully).
- `most_cited_arxiv_id` = `2305.14314` (QLoRA, the all-time most-cited
  of the 8 by a large margin and stable under reasonable growth).
- `max_pages_arxiv_id` = `2401.05566` (Sleeper Agents, 71 pages —
  nearly 2.5x the next paper).
- 4 papers with citation_count > 1000 as of 2026-05-02:
  `2304.03442` (3882), `2305.14314` (4399), `2310.06825` (3377),
  `2403.04132` (1192). Eval requires the conditional-format rule to be
  present; whether a specific cell visibly turns red is an .ods-style
  property that is hard to test pixel-perfect, so the check is on the
  **rule existence** in styles, not visual rendering.

## 5. Checkpoint Rubric

- 0.18 — `papers.json` parses; `papers` is an array of length 8 with
  all 6 required keys per element; the set of `arxiv_id` values equals
  `ground_truth.arxiv_ids`; for each arxiv_id, `title` substring-matches
  the ground truth (case-insensitive, ≥80% chars present),
  `first_author` substring-matches, `page_count` within ±2,
  `author_count` within ±1, `citation_count` within
  `[recorded * 0.95, recorded * 1.10 + max(20, recorded*0.10)]`.
- 0.08 — `library/metadata.db` exists AND
  `calibredb list --library-path=/tmp_workspace/results/library/ --for-machine`
  (re-run by the supervisor) returns ≥8 records.
- 0.18 — `index.ods` is a valid ODF zip
  (`unzip -l index.ods` shows `content.xml` and `mimetype` =
  `application/vnd.oasis.opendocument.spreadsheet`); the `papers` data
  region contains all 8 arxiv_ids and the columns
  arxiv_id/title/first_author/author_count/page_count/citation_count
  (header row substring match, case-insensitive).
- 0.18 — **Formula present**: `unzip -p index.ods content.xml | grep -c
  'table:formula'` ≥ 1 — i.e. at least one `<table:table-cell
  table:formula="...">` element with a formula attribute. Common shapes
  that pass: `of:=AVERAGE(...)`, `of:=SUM(...)`, `of:=IF(...)`,
  `of:=COUNTIF(...)`, `=AVERAGE(...)` (legacy syntax).
- 0.13 — **Conditional formatting present**: `unzip -p index.ods
  content.xml styles.xml 2>/dev/null | grep -E -c
  'conditional-format|calcext:condition'` ≥ 1 — i.e. there is a
  `<calcext:conditional-format>` (or `<style:conditional-format>`)
  block defining at least one rule. The supervisor does NOT require a
  specific style name; presence of any conditional-formatting rule is
  sufficient (the user wants citations > 1000 highlighted; the executor
  may choose any visible style for it).
- 0.13 — **Embedded chart object present (loosened).** A chart-like
  signal must exist inside `index.ods`. Accept ANY of: (a)
  `unzip -l index.ods | grep -E -c 'Object[ _]?[0-9]+/(content\.xml|.*\.xml)'`
  ≥ 1 — embedded chart object subdirectory; OR (b) `META-INF/manifest.xml`
  lists at least one entry with mediatype
  `application/vnd.oasis.opendocument.chart`; OR (c) `content.xml`
  contains a `<chart:chart` or `<draw:object` xml fragment that
  references a chart sub-object. Any one of these three signals counts.
  Inserting a real chart through `soffice --headless` CLI alone is
  awkward — odfpy / direct xml manipulation / a Basic macro driven via
  `soffice --headless --norestore --calc 'macro:///...'` are all
  acceptable production paths.
- 0.12 — **First-author affiliation mapping**: each element in
  `papers.json.papers` MUST have a non-empty string field
  `first_author_affiliation`. For each arxiv_id, the value MUST
  case-insensitively contain at least one of the
  `expected_first_author_affiliation_substrings` listed in
  `ground_truth.first_author_affiliations` (≥7 of 8 papers must
  match). AND `papers.json` MUST have a top-level
  `affiliation_distribution` JSON object whose values are positive
  integers summing to a count `>=8` (allowing co-affiliations) AND
  `<=12` (sanity bound). The set of distinct keys (case-insensitive,
  whitespace-collapsed) must contain at least 6 distinct affiliations
  (these 8 papers come from 7+ different institutions per
  ground_truth).

## 6. Scoring Policy / Score Caps

- Trace shows zero arxiv / S2 / calibredb activity → 0.40 (synthetic
  data only).
- Trace shows zero `wget`/`curl` against `arxiv.org` AND
  `library/metadata.db` reports 0 books → 0.40.
- `index.ods` exists but `unzip` fails or it has no `content.xml` →
  cap §5 .ods checkpoints at 0.
- `index.ods` was produced by `soffice --headless --convert-to ods` on
  a CSV with NO post-processing AND has 0 formulas / 0 conditional
  formats / 0 charts → cap §5 platform-depth checkpoints (formula,
  conditional formatting, chart) at 0 each (no global cap).
- `citation_count` values exactly equal recorded ground-truth AND
  trace shows zero S2 requests → 0.55 (suspected hard-coded).

Pass requires ≥ 0.90 — i.e. all 7 checkpoints satisfied OR 6 satisfied
plus near-miss on one of the platform-depth checks. The first-author
affiliation checkpoint is a hard pass requirement (cannot be skipped).

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor stops.
- **Continue** 0.50–0.89 — supervisor may request one follow-up,
  typically to add the missing platform feature (formula, conditional
  formatting rule, or chart object) into the .ods.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`
- `references/screenshot_index_ods_reference.png` — reserved path for
  an authored reference screenshot showing what a correct
  `index.ods` looks like when opened in LibreOffice Calc (the 8-row
  table, the citation>1000 rows highlighted red, and the embedded
  bar chart of page_count vs arxiv_id). If the file exists at grading
  time, the supervisor MAY use it for image-comparison sanity-checking
  (does the executor's .ods, when opened, broadly match the layout —
  row count, chart presence, conditional-format shading). The
  comparison is qualitative only — checkpoint scoring is still
  anchored on the zip-introspection checks in §5. If the reference
  PNG is absent the supervisor skips the comparison silently.

## 9. Dynamic Content Note

The 8 arxiv IDs are immutable; titles and first authors are stable.
`page_count` may shift by 1-2 if authors revise. `citation_count`
grows over time — eval applies a percentage tolerance with a 0.95×
floor; the relative `most_cited_arxiv_id == "2305.14314"` ranking is
the more stable anchor.

If arxiv API or download is temporarily unavailable, the supervisor
distinguishes "executor failed" from "API outage" — repeated 5xx is
`infra_error`, not penalised. Same for Semantic Scholar 429/5xx.
