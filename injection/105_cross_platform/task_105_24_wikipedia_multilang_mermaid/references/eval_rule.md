# Hidden Evaluation Rule — task_105_24_wikipedia_multilang_mermaid

## 1. Grading Philosophy

Grade on whether the executor actually did the multilingual Wikipedia
comparison the user asked for: pulled the FOUR pinned oldids, computed
some kind of similarity over external links across the four languages,
checked the article-thickness intuition (German is thinnest), and
produced a Mermaid concept map plus a brief Chinese write-up that
states which language pairs are most/least similar.

This is goal-achievement grading. We do NOT enforce exact JSON schema
field names, exact filenames beyond what's needed to find the work, or
13 separate sub-checkpoints. Five semantic checkpoints, weights sum 1.0.

## 2. Task Contract

The user pinned to immutable oldids — these MUST be the revisions used:
- en: 1350358134
- zh: 91416611
- ja: 108911848
- de: 262493853

The user expects to find:
- en–ja is the most similar pair (Jaccard ≈ 0.48)
- zh–de is the least similar pair (Jaccard ≈ 0.06)
- de version is the thinnest (≈ 8736 bytes vs en's ≈ 21072)
- A Mermaid concept map that visualises the comparison
- A short Chinese write-up tying it together

Deliverables should land somewhere under `/tmp_workspace/results/`.
Filenames may vary; supervisor scans the results directory and uses
flexible matching (any `.json` containing the four oldids; any `.mmd`
file; any `.md` write-up).

## 3. Source-Selection Rules

Live MediaWiki API:
- `curl 'https://{lang}.wikipedia.org/w/api.php?action=parse&format=json&prop=sections|externallinks&oldid={oldid}'`
- Article thickness via `prop=info|categories|images&revids={oldid}`

NO snapshot file exists. NO mock service. NO API key required.

Common pitfall: passing both `page=Next.js` AND `oldid=...` to the
parse API → MediaWiki returns `invalidparammix`. Use ONLY oldid.

## 4. Ground-Truth Snapshot Anchors

See `references/ground_truth.json` for the full reference. Key facts:

- All 4 oldids are immutable (1350358134, 91416611, 108911848,
  262493853).
- External link counts: en=51, zh=59, ja=42, de=15.
- Article byte lengths: en≈21072, zh≈18743, ja≈24279, de≈8736.
- Jaccard pairs (±0.05 tolerance):
  en–zh ≈ 0.45 | en–ja ≈ 0.48 | en–de ≈ 0.06
  zh–ja ≈ 0.40 | zh–de ≈ 0.06 | ja–de ≈ 0.08
- Most similar pair: {en, ja}; least similar: {zh, de}.
- Thinnest article: de.

## 5. Checkpoint Rubric

Five semantic checkpoints, weights sum 1.0.

- 0.20 — **Correct revisions used.** Some JSON file under
  `/tmp_workspace/results/` references all 4 pinned oldids
  (1350358134, 91416611, 108911848, 262493853). Either as explicit
  `revision_id` / `oldid` fields, or in a captured URL string. The
  presence of these 4 integers in the result corpus confirms the
  executor pinned to immutable revisions and didn't fall back to the
  live page.

- 0.20 — **Per-language metadata correct.** For each of the 4
  languages, the executor's recorded values include AT LEAST TWO of:
    * `external_links_count` matching ground_truth (en=51, zh=59,
      ja=42, de=15) within ±2
    * `article_length_bytes` matching ground_truth within ±100
    * `top_level_sections_count` matching ground_truth (en=7, zh=5,
      ja=6, de=5) within ±1
  Score: 0.05 per language that has at least 2 of 3 right.

- 0.20 — **Pairwise similarity computed and credible.** Some structure
  in the output expresses pairwise similarity (a 4×4 matrix, a list of
  6 pairs, or named pair scores) covering all 6 unique pairs of
  {en, zh, ja, de}. At least 5 of the 6 Jaccard values are within
  ±0.10 of ground_truth. The output (or the write-up) identifies
  en–ja (or "en/ja", "English/Japanese") as the most similar pair OR
  identifies zh–de (or "zh/de", "Chinese/German") as the least similar.

- 0.15 — **German-is-thinnest observation captured.** The write-up
  OR the JSON identifies German as the shortest/thinnest version
  (smallest `article_length_bytes`, or explicit text like "德语版最薄"
  / "de is the shortest"). Bonus: the write-up notes that despite
  being the shortest, de has the highest information density (cats +
  imgs / KB).

- 0.15 — **Mermaid concept map exists and renders.** A `.mmd` (or
  similarly named) file under `/tmp_workspace/results/` whose first
  non-blank line begins with one of `mindmap`, `graph TD`, `graph LR`,
  or `flowchart`. The source must contain the literal substring
  "Next.js" AND each of the four language identifiers (en/zh/ja/de OR
  English/中文/日本語/Deutsch). A rendered PNG (PNG magic bytes
  0x89 0x50 0x4E 0x47, file size > 1024 bytes) MUST also be present
  in the results directory. Half credit (0.075) if only the source
  exists with no rendered PNG. If a reference image exists at
  `references/screenshot_mermaid.png`, the supervisor may also do a
  loose visual layout comparison (node count parity, presence of all
  4 lang labels), but this is informational only and does not change
  the score.

- 0.10 — **Chinese write-up exists.** A markdown file (any name) in
  results, 200–800 zh chars; mentions all four language codes (en/zh/
  ja/de or 英/中/日/德); states which pair is most similar AND which
  pair is least similar; mentions the German-thinnest observation
  with at least one numeric value (byte length, link count, or
  similarity score).

## 6. Scoring Policy / Score Caps

Partial credit from the 5 checkpoints. Caps:

- No JSON file referencing the 4 oldids AND no Mermaid file → 0.20.
- Output uses non-pinned current revisions instead of the supplied
  oldids → 0.40.
- Trace shows zero curl/wget/http calls to wikipedia.org → 0.40.

Pass requires checkpoints 1, 2, 3 (revisions + per-lang metadata +
pairwise similarity) all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up.
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All anchors here are immutable because the user pinned to specific
oldids. External-link sets, byte lengths, section counts, langlinks,
and Jaccard values cannot drift. If observed values diverge from
ground_truth, that is an executor bug (almost always: used the live
page instead of the oldid, or normalised URLs differently).

If Wikipedia API is temporarily unavailable, supervisor records
`infra_error` and avoids penalising. Repeated 5xx is an outage.
