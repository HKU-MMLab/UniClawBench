# Hidden Evaluation Rule — task_205_34_academic_poster_inkscape

## 1. Grading Philosophy

Grade on whether the executor performed a real cross-platform poster
authoring workflow that combines (a) wget against arxiv,
(b) poppler-utils CLI for paper meta extraction (pdfinfo / pdftotext),
(c) curl against the MediaWiki API with PINNED `revids=<id>` for 5
concepts, (d) Inkscape composite SVG poster (≥1 rect for layout +
≥8 text elements covering title/authors/page-count/5 concept boxes
with ✓/✗ markers), (e) inkscape SVG→PDF export, (f) Evince
screenshot of the rendered PDF via xvfb. The Inkscape platform value
here is real composition (multiple visual elements with layout), not
a single text dump on a blank page. Anchor checks against
`ground_truth.json` — every value there is bound to an immutable
Wikipedia revision (the `&oldid=<id>` URL parameter returns identical
content forever) or to the immutable arxiv 2310.06825 v1 PDF. Score
caps in §6 override rubric totals.

## 2. Task Contract

The user wants a single composite SVG poster panel for the Mistral 7B
paper (arxiv 2310.06825) exported to PDF, plus the structured data
that backs it (paper meta, wiki lookups, cross-check CSV) and a
Evince screenshot proving the PDF renders. NO snapshot file, NO
mock, NO populate step.

The 5 concept set + pinned wiki revision IDs:

  1. Mistral_AI                            (revid 1352105656)
  2. Large_language_model                  (revid 1351510195)
  3. Mixture_of_experts                    (revid 1346279093)
  4. Generative_pre-trained_transformer    (revid 1351783271)
  5. Open-source_artificial_intelligence   (revid 1350744847)

Required deliverables:

- `/tmp_workspace/results/paper_meta.json` — JSON with keys
  `arxiv_id`, `title`, `authors` (18-element ordered list),
  `page_count`.
- `/tmp_workspace/results/wiki_lookups.json` — JSON with `concepts`
  as a 5-element list in the order Mistral_AI →
  Large_language_model → Mixture_of_experts →
  Generative_pre-trained_transformer →
  Open-source_artificial_intelligence. Each item has `name`,
  `wiki_revision_id`, `wiki_url`, `first_para_first_100_chars`.
- `/tmp_workspace/results/cross_check.csv` — header
  `concept,paper_mentions,wiki_revision_id,verification_status`,
  5 rows in the same concept order.
- `/tmp_workspace/work/poster.svg` — composite SVG: root `<svg>`
  width AND height ≥ 600 (any unit); at least 1 `<rect>` element
  (for background or box border); at least 8 `<text>` elements.
- `/tmp_workspace/results/poster_panel.pdf` — inkscape SVG→PDF
  export of the composite poster. Valid PDF (pdfinfo). pdftotext
  must extract:
  - the paper title `"Mistral 7B"`
  - the first 3 authors `"Albert Q. Jiang"`, `"Alexandre Sablayrolles"`,
    `"Arthur Mensch"` (each as a substring)
  - the page count `"9"` (as a digit; can be embedded in any phrase)
  - the 5 concept names (allow underscore↔space normalisation)
  - markers totalling 3 ✓ and 2 ✗ (Unicode U+2713 / U+2717, OR
    "VERIFIED" / "WIKI ONLY" ASCII-equivalents — accept either
    encoding so long as the 3-vs-2 split matches the expected
    cross-check)
- `/tmp_workspace/results/evince_screenshot.png` — non-empty PNG
  showing the Evince viewer rendering `poster_panel.pdf` (xvfb
  headless capture acceptable). The supervisor checks (a) PNG width
  ≥ 800 px AND height ≥ 500 px, AND (b) ≥ 4 distinct non-white
  colors (proves it's a rendered PDF page, not a blank white grab),
  AND (c) Evince window chrome is on screen (toolbar / page-index
  counter / sidebar icons — substring "Evince" or page-counter
  "/N" pattern via OCR is the cheap proxy; if OCR is unavailable
  the chrome check falls back to the ≥4-color heuristic).

## 3. Source-Selection Rules

Canonical sources are LIVE:
- arxiv: `wget https://arxiv.org/pdf/2310.06825 -O /tmp_workspace/work/paper.pdf`
- pdfinfo / pdftotext: poppler-utils CLI tools
- Wikipedia (PINNED via revids):
  `curl "https://en.wikipedia.org/w/api.php?action=query&revids=<ID>&prop=revisions|extracts&exintro&explaintext&format=json"`
- Inkscape: `inkscape --export-type=pdf --export-filename=<out>.pdf
  <in>.svg` (or `inkscape -o <out>.pdf <in>.svg`). The SVG itself
  may be hand-written (heredoc, python, xmlstarlet) — what matters
  is that it is a real composite (rect + ≥8 text) that exports to a
  PDF whose pdftotext output passes the string checks.
- Evince + xvfb-run + scrot/import for the screenshot of
  `poster_panel.pdf` rendered by Evince.

NO snapshot file. NO mock. Reading from any local fixture under
`/tmp_workspace/clawbench/` is undefined behaviour (the directory is
empty).

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json`. Key
anchors:

- `paper.arxiv_id` = `"2310.06825"` (exact)
- `paper.page_count` = `9` (exact, immutable)
- `paper.title` = `"Mistral 7B"` (exact, taken from paper body —
  PDF metadata `/Title` field is intentionally empty)
- `paper.first_three_authors` =
  `["Albert Q. Jiang", "Alexandre Sablayrolles", "Arthur Mensch"]`
- `wiki_concepts[*].wiki_revision_id` = exact integers — pinned via
  the `&oldid=` URLs the user provided. Wikipedia returns identical
  content for these revids forever.
- `wiki_concepts[*].first_para_first_100_chars` = first 100 chars of
  the `extract` returned by the MediaWiki `revids=<id>` query —
  frozen.
- `cross_check_csv_rows` = exact ordering and values (3 verified +
  2 wiki_only)
- `poster_pdf_required_strings` = paper title + 3 first authors +
  page count "9" + 5 concept names + (3 ✓ markers AND 2 ✗ markers,
  any of the accepted encodings)

## 5. Checkpoint Rubric

Weights sum to 1.0. (7 weighted checkpoints.)

- 0.13 — `paper_meta.json` parses; `arxiv_id` == "2310.06825" AND
  `page_count` == 9 AND `title` == "Mistral 7B" AND `authors` is a
  list whose first element == "Albert Q. Jiang" and length == 18.
- 0.18 — `wiki_lookups.json` parses; `concepts` has 5 items in the
  specified order; for each item `wiki_revision_id` matches
  ground_truth exactly (5/5 required) AND
  `first_para_first_100_chars` matches ground_truth (allow ±2 char
  edit-distance for unicode normalisation).
- 0.13 — `cross_check.csv` exists with header line + 5 data rows;
  each row's `(concept, paper_mentions, wiki_revision_id,
  verification_status)` matches ground_truth exactly. Concept order
  preserved. Pass requires 5/5 rows correct.
- 0.18 — `poster.svg` exists AND parses as XML AND root `<svg>`
  reports width AND height attributes (or viewBox) such that both
  dimensions ≥ 600 AND contains at least 1 `<rect>` element AND at
  least 8 `<text>` elements. Counts use the SVG namespace
  (xmlstarlet `count(//svg:rect)`, `count(//svg:text)`).
- 0.18 — `poster_panel.pdf` exists AND pdfinfo reports it as a
  valid PDF AND pdftotext extracts ALL of:
  (a) paper title "Mistral 7B",
  (b) all 3 first authors as separate substrings (Albert Q. Jiang,
      Alexandre Sablayrolles, Arthur Mensch),
  (c) the digit "9" appearing somewhere in the page-count region,
  (d) all 5 concept names (underscore↔space normalised),
  (e) marker count: exactly 3 ✓ + 2 ✗ (or 3 "VERIFIED" + 2 "WIKI
      ONLY" ASCII-equivalents). The 3-vs-2 split is what proves the
      cross-check was wired into the layout.
- 0.08 — **Evince screenshot of poster_panel.pdf exists.**
  `/tmp_workspace/results/evince_screenshot.png` exists AND is a
  valid PNG of size > 0 bytes AND width ≥ 800 px AND height ≥ 500
  px AND has ≥ 4 distinct non-white colors (proves it's a rendered
  PDF page, not a blank white grab). The cheap chrome-presence
  proxy: substring "Evince" or page-counter "/N" pattern via OCR;
  if OCR is unavailable the chrome check falls back to the ≥4-color
  heuristic.
- 0.12 — **Cross-Wikipedia language coverage**:
  `/tmp_workspace/results/multi_lang_availability.json` exists,
  parses, and has top-level `concepts` as a JSON array of length 5
  in the SAME order as the 5 anchored concepts (Mistral_AI →
  Large_language_model → Mixture_of_experts →
  Generative_pre-trained_transformer → Open-source_artificial_intelligence).
  Each item MUST have keys `name`, `en`, `zh`, `ja`. Each of `en`,
  `zh`, `ja` MUST be one of `"yes"` or `"no"` (string). All 5 `en`
  values MUST be `"yes"`. At least 4 of 5 concepts must match the
  expected `(zh, ja)` pair from
  `ground_truth.multi_lang_availability_expected`. Trace must show
  at least one curl/wget against an `*.wikipedia.org` URL containing
  `langlinks`.

## 6. Scoring Policy / Score Caps

Partial credit from satisfied checkpoints. Caps:

- `poster_panel.pdf` is a copy of the original arxiv PDF (no inkscape
  composition — pdftotext yields zero of the required strings) → 0.45.
- `wiki_lookups.json` revids don't match ground_truth (executor used
  `&prop=revisions` without `revids=` and got the live latest) → 0.40.
- Trace shows zero wget / pdftotext / curl / inkscape calls
  (synthetic data only) → 0.30.
- `poster.svg` has < 1 rect OR < 8 text elements (executor produced
  a flat text dump, not a composite poster) → cap 0.65.
- `poster_panel.pdf` missing the marker count or wrong split (e.g.,
  4 ✓ + 1 ✗) → cap 0.70.
- `cross_check.csv` not aligned with the actual marker split in the
  PDF (data and visual disagree) → cap 0.75.

Pass requires the 3 "exact value" checkpoints (paper meta, wiki
lookups, cross_check CSV) + the SVG composite-structure checkpoint
+ the PDF string-extraction checkpoint + the multi-lang availability
checkpoint all satisfied.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — executor should stop.
- **Continue** 0.50–0.89 — supervisor may request one follow-up to
  fix the lowest-scoring deliverable (most often the SVG composition
  step or the marker count).
- **Fail** < 0.50 — no further follow-ups.

## 8. Hidden Reference Assets

Supervisor-only:
- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

All anchors are immutable: arxiv PDFs are write-once, page count and
authors of a published version do not change, Wikipedia revisions are
write-once even if the page is later edited (the listed revids keep
returning the same content via `revids=<id>` or `?oldid=<id>`). The 5
revids in `ground_truth.wiki_concepts[*].wiki_revision_id` were
captured 2026-05-02 and pinned via `?oldid=` in the URLs the user
supplies — they are stable forever.

If arxiv, Wikipedia APIs are temporarily unavailable, the supervisor
MUST distinguish "executor failed" from "API outage". A trace showing
repeated 5xx responses is an outage, not an executor failure —
record `infra_error` in summary and avoid penalising.
