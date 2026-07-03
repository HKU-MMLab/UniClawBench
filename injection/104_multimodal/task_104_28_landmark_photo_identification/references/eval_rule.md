# Hidden Evaluation Rule — task_104_28_landmark_photo_identification

## 1. Grading Philosophy

Grade the executor on whether it produced a complete, source-file-grounded
landmark identification report for the 30 bundled travel photos. Artifact
existence, polished prose, or self-reported confidence is not enough for a
pass. A pass requires the CSV rows to map back to the exact source filenames
and to match the locked landmark, city, and country facts.

The task is an offline image-identification task. The authoring manifest,
hidden URLs, hidden hashes, and hidden ground truth are supervisor-only aids
and must not substitute for evaluating the saved artifacts against the photo
fixture.

After applying score caps, use these bands exactly:

- **Pass**: `>= 0.90`
- **Continue**: `0.60 - 0.89`
- **Fail**: `< 0.60`

## 2. Task Contract

The public task asks the executor to inspect every image under:

- `/tmp_workspace/clawbench/sources/travel_photos/`

Required outputs are:

- `/tmp_workspace/results/landmark_report.csv`
- `/tmp_workspace/results/landmark_summary.md`

The CSV must parse and must use this exact header:

```csv
file_name,landmark,city,country
```

It must contain exactly one row for each of the 30 source filenames and no
extra rows. Rows should be sorted by `file_name`. The markdown summary must
briefly list the 10 most confident identifications and 3 confusing cases with
the visual basis for those judgments.

## 3. Source-File Matching Rules

The supervisor matches rows by source filename. The exact fixture set is the
30 files listed in Section 4. Row order alone is not a valid source-file
mapping for pass-level scoring.

Use these rules when reading the CSV:

- The required mapping key is the `file_name` column. A near-equivalent column
  such as `filename` or `source` may be used only to estimate content accuracy,
  but the schema and cap penalties still apply because the public task required
  `file_name`.
- A row whose filename is blank, malformed, duplicated, or not in the fixture
  set is unmatched and earns zero landmark, city, and country accuracy credit.
- Missing source files, duplicate source files, invented filenames, and extra
  non-fixture rows trigger the caps in Section 6.
- Do not infer row identity from alphabetical order when filenames are absent.
  A table of 30 landmark guesses without per-row filenames has no reliable
  source-file mapping.

## 4. Locked Ground Truth

Use `references/ground_truth.json` as the authoritative answer set for
canonical values and accepted aliases. The authoring URLs and `sha256` fields
inside that file are provenance metadata only; do not expose them and do not
use them as public answer evidence.

Canonical filename-to-answer mapping:

| file_name | landmark | city | country |
| --- | --- | --- | --- |
| `0jj4nac6crjgvu.jpg` | Louvre Pyramid | Paris | France |
| `0we0ech08qejhn.jpg` | Chateau Frontenac | Quebec City | Canada |
| `0z4nwcsdof6gn0.jpg` | Hagia Sophia | Istanbul | Turkey |
| `2emaapje1hgx8l.jpg` | Notre-Dame de Paris | Paris | France |
| `35dot43ize3bgv.jpg` | Empire State Building | New York City | United States |
| `6ww8ewocfkd49a.jpg` | Statue of Liberty | New York City | United States |
| `7hmb5cxco0pijr.jpg` | Trevi Fountain | Rome | Italy |
| `7j20xye3rdu2mp.jpg` | Christ the Redeemer | Rio de Janeiro | Brazil |
| `89bmiq6gu6y5wb.jpg` | Leaning Tower of Pisa | Pisa | Italy |
| `8a7gjn6x46eddt.jpg` | Big Ben | London | United Kingdom |
| `8a9afo5pbwxghj.jpg` | Brandenburg Gate | Berlin | Germany |
| `8c28c0eciwm87e.jpg` | Golden Gate Bridge | San Francisco | United States |
| `8ubrb987d9odns.jpg` | Sagrada Familia | Barcelona | Spain |
| `95nwaxch6j7z5l.jpg` | Gateway Arch | St. Louis | United States |
| `9eb8ti0sa6j096.jpg` | Atomium | Brussels | Belgium |
| `adkh19jtsqd5je.jpg` | One World Trade Center | New York City | United States |
| `b9ejmzuu7a6trl.jpg` | Buckingham Palace | London | United Kingdom |
| `ca58wp4jtvu6i0.jpg` | Taj Mahal | Agra | India |
| `e9hn43i8u3nnyk.jpg` | Kiyomizu-dera | Kyoto | Japan |
| `f517efy1y4zkmh.jpg` | Sydney Opera House | Sydney | Australia |
| `itkfpjvw9gzly4.jpg` | Eiffel Tower | Paris | France |
| `jiw7xwrgwbdazg.jpg` | Colosseum | Rome | Italy |
| `k6bo7zw13l8218.jpg` | Milan Cathedral | Milan | Italy |
| `ka991hhnu26eg2.jpg` | Petronas Twin Towers | Kuala Lumpur | Malaysia |
| `lt8zi6wktxwdm7.jpg` | Great Pyramid of Giza | Giza | Egypt |
| `occ4ev59zwove7.jpg` | Temple of Heaven | Beijing | China |
| `oss10faube44vg.jpg` | The Shard | London | United Kingdom |
| `oxm3m1cu8tgitl.jpg` | CN Tower | Toronto | Canada |
| `rxkfnd7rnm6p4z.jpg` | Angkor Wat | Siem Reap | Cambodia |
| `secvfxp5e5xxsk.jpg` | Burj Khalifa | Dubai | United Arab Emirates |

Normalize answers before matching by lowercasing, stripping surrounding
whitespace, removing diacritics, collapsing punctuation and repeated spaces,
and ignoring harmless hyphen/apostrophe differences. Accept canonical values
and the aliases listed in `ground_truth.json`, including common short forms
such as `NYC`, `USA`, `US`, `UK`, and `UAE` where listed.

For the `landmark` field only, also accept harmless parenthetical or slash
combinations made entirely of accepted names for the same fixture, such as
`Elizabeth Tower (Big Ben)` for `8a7gjn6x46eddt.jpg` or
`Milan Cathedral (Duomo di Milano)` for `k6bo7zw13l8218.jpg`. Do not accept a
composite that introduces a different landmark, a different city, or an
unsupported broader area.

Generic answers do not count as landmark matches. Examples include city-only
or country-only landmark cells (`Paris`, `London`, `New York`, `Italy`), broad
classes (`tower`, `bridge`, `cathedral`, `palace`, `pyramid`, `skyscraper`),
or vague phrases such as `famous landmark in Paris`.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award row-level accuracy only for rows matched to a
fixture filename under Section 3.

- **0.15 - CSV artifact, schema, and source coverage.** Full credit requires
  `landmark_report.csv` to exist under `/tmp_workspace/results/`, parse as
  CSV, use exactly `file_name,landmark,city,country`, contain exactly 30 data
  rows, cover every fixture filename exactly once, contain no extra filenames,
  and be sorted by `file_name`. Give up to 0.05 for a parseable CSV with the
  required information but wrong column order or naming. Give up to 0.10 when
  the schema is correct but one or two source rows are missing, duplicated, or
  unsorted. Zero this line if the CSV is missing or cannot be parsed.

- **0.45 - Landmark identification accuracy.** Score proportionally as
  `0.45 * landmark_correct / 30`. A row is correct only when the landmark cell
  matches the canonical landmark or an accepted alias for that same file after
  Section 4 normalization. City-only, category-only, blank, or different
  landmark answers score zero for the row.

- **0.15 - City accuracy.** Score proportionally as
  `0.15 * city_correct / 30`. The city must match the canonical city or an
  accepted city alias for that same file. The answer does not receive city
  credit merely because the landmark is in the right country.

- **0.10 - Country accuracy.** Score proportionally as
  `0.10 * country_correct / 30`. The country must match the canonical country
  or an accepted country alias for that same file.

- **0.10 - Markdown summary quality and visual support.** Full credit requires
  `landmark_summary.md` to exist, be readable, list 10 high-confidence
  filename-linked identifications that are correct or accepted aliases, and
  list 3 potentially confusing filename-linked cases with short visual
  justifications. Visual support must refer to features visible in the image,
  such as silhouette, facade, material, setting, skyline, water, or distinctive
  structural details. Give up to 0.05 when the summary exists but lacks either
  the 10-confidence list or the 3-confusing-cases list. Zero this line for a
  missing, empty, or generic summary.

- **0.05 - No unsupported or hallucinated content.** Full credit requires all
  reported rows and summary statements to stay within the 30-photo fixture and
  avoid invented filenames, non-existent landmarks, unsupported provenance
  claims, or confidence claims contradicted by the visible image. Deduct this
  line for hidden-reference leakage, fabricated source files, or visual
  rationale that is plainly not present in the relevant photo.

## 6. Scoring Policy / Score Caps

Compute the rubric total, then apply every applicable cap by taking the
minimum. Caps are deliberately strict because high scores must reflect correct
source-file mapping and correct landmark IDs, not just a plausible attraction
list.

- **Cap at 0.30 - No useful deliverable.** `landmark_report.csv` is missing,
  empty, or unparsable.

- **Cap at 0.50 - Missing source-file mapping.** The answer provides landmark
  guesses but lacks a usable per-row source filename mapping, omits the
  `file_name` concept entirely, or can only be matched by row order. This
  includes prose-only answers and tables without original filenames.

- **Cap at 0.35 - Less than two-thirds coverage.** Fewer than 20 fixture
  filenames can be matched to rows after Section 3 matching.

- **Cap at 0.84 - Incomplete or dirty fixture coverage.** Any fixture filename
  is missing, duplicated, blank, malformed, or accompanied by a non-fixture
  extra row. A run cannot pass unless all 30 source files are covered exactly
  once.

- **Cap at 0.84 - Wrong CSV schema.** The report is parseable and mostly
  complete but does not use the exact required four-column schema. The
  supervisor may still score row accuracy from near-equivalent columns, but
  the run cannot pass with the wrong public contract.

- **Cap at 0.84 - Too many wrong landmark IDs for pass.** Fewer than 27 of the
  30 landmark cells match the locked ground truth after alias normalization.

- **Cap at 0.70 - Major landmark-ID weakness.** Fewer than 24 of the 30
  landmark cells are correct, even if city and country columns are plausible.

- **Cap at 0.50 - Broad landmark-ID collapse.** Fewer than 20 of the 30
  landmark cells are correct.

- **Cap at 0.84 - Vague city-only or category-only landmark answers.** One to
  four landmark cells are vague city names, country names, or broad categories
  instead of concrete named landmarks. These rows already score zero, and the
  cap prevents an otherwise polished report from passing with generic
  landmark IDs.

- **Cap at 0.60 - Systematic vague answers.** Five or more landmark cells are
  city-only, country-only, category-only, blank, or `unknown` style answers.

- **Cap at 0.84 - Location columns not pass-level.** Fewer than 27 cities or
  fewer than 28 countries match the locked ground truth after alias
  normalization.

- **Cap at 0.70 - Systematically missing city/country data.** City or country
  columns are mostly blank, generic, copied from the landmark name, or
  systematically shifted to the wrong location even when some landmark names
  are correct.

- **Cap at 0.84 - Missing or incomplete required summary.** The CSV may be
  strong, but `landmark_summary.md` is missing, empty, lacks the 10
  high-confidence list, or lacks the 3 confusing cases.

- **Cap at 0.84 - Hallucinated confidence without visual evidence.** The
  summary claims high confidence for three or more photos without any
  image-specific visible feature, or uses confidence rationales that are
  plainly not visible in the corresponding photo. Generic statements such as
  `iconic landmark` alone are not visual evidence.

- **Cap at 0.70 - Systematic hallucinated visual evidence.** Most confidence
  or confusion explanations are invented, copied from external descriptions,
  refer to features absent from the image, or are not tied to source
  filenames.

- **Cap at 0.50 - Fabricated fixture or hidden-reference leakage.** The answer
  invents multiple source files, reports landmarks outside the fixture as if
  they were inputs, exposes hidden provenance URLs or hashes as answer
  evidence, or otherwise relies on supervisor-only metadata.

- **Cap at 0.30 - Credential or privacy leak.** Any value whose environment
  variable is declared private is emitted in user-visible output. No such
  value is expected in this task.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** Stop. The CSV uses the required schema,
  maps all 30 source filenames exactly once, has at least pass-level landmark,
  city, and country accuracy, and the summary contains visually grounded
  confidence/confusion notes.

- **Continue (`0.60 - 0.89` after caps):** Ask for one focused revision when
  the attempt is substantially based on the correct photo set and can be fixed
  without restarting. Typical continue cases include one or two missing or
  duplicated filenames, 24-26 correct landmark IDs, mostly right landmarks with
  city/country cleanup needed, a missing summary, or confidence notes that need
  visible feature support.

- **Fail (`< 0.60` after caps):** Do not request more work. This includes no
  parseable CSV, no reliable source-file mapping, fewer than 20 matched source
  files, fewer than 20 correct landmark IDs, systematic city-only/category-only
  answers, fabricated fixture files, hidden-reference leakage, or privacy
  leakage.

When giving continue feedback, name the lowest-scoring concrete defect, for
example: `add the missing source filename rows`, `replace city-only landmark
cells with named landmarks`, `fix the wrong city/country fields`, or `add
visual reasons for the high-confidence and confusing cases`.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
public user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - locked filename mappings, canonical
  landmark/city/country values, accepted aliases, source URLs, and authoring
  hashes.

## 9. Dynamic Content Note

This is an offline fixture. Network state and live web pages are irrelevant to
grading. Use the bundled 30 source files and `references/ground_truth.json` as
the locked answer set. If provenance hashes or external URLs drift from the
current image bytes, grade the executor's saved artifacts by filename and
locked canonical answer, and flag the fixture mismatch separately rather than
re-authoring the answers from the web.
