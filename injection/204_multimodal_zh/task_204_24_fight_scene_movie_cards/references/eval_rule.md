# Hidden Evaluation Rule — task_204_24_fight_scene_movie_cards

## 1. Grading Philosophy

Judge the executor on whether it delivered an auditable movie-card page built
from the frozen local compilation, not on whether it produced polished files or
plausible classic-film guesses.

Full-credit work must satisfy all core facts at once:

- the five local 10-second segments are identified as the canonical movies in
  the canonical segment mapping below;
- each title has the correct release year;
- each row/card is tied to a screenshot captured from the matching segment
  window in the local source video; and
- the CSV and HTML expose enough clip-specific evidence for a supervisor to
  verify how the answer was reached.

Public web search is allowed and expected as confirmation, but it cannot replace
local-video grounding. Do not reward external clip lists, generic film
knowledge, or visually plausible but wrong movie IDs.

## 2. Task Contract

The public task asks the executor to open:

- `/tmp_workspace/clawbench/sources/classic_movie_compilation.mp4`

and produce:

- `/tmp_workspace/results/movie_picks.csv`
- `/tmp_workspace/results/movie_picks.html`
- five representative screenshot assets under
  `/tmp_workspace/results/movie_picks_assets/`

The CSV must contain at least these columns:

- `movie_title`
- `release_year`
- `screenshot_file`
- `recommendation_reason`
- `identification_clue`

The HTML must render one card per movie with a screenshot, title, release year,
and one-sentence recommendation reason. Extra columns, extra styling, and
additional analysis files are acceptable only if the required outputs are
correct.

## 3. Locked Ground Truth and Segment Mapping

Grade against `references/ground_truth.json` and the hidden reference frames
under `references/reference_assets/`. The source is a frozen 50-second video,
640x480 at 10 fps, divided into five consecutive 10-second segments.

Canonical segment identities:

| Segment | Time window | Reference frame | Movie title | Year | Visual anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | `0:00-0:10` | `segment_01.jpg` at about `0:05` | `Dressed to Kill` | `1941` | exterior porch/railing, woman with large basket, man by vehicle |
| 2 | `0:10-0:20` | `segment_02.jpg` at about `0:15` | `His Girl Friday` | `1940` | newsroom/office, man in light suit holding woman near desks and phones |
| 3 | `0:20-0:30` | `segment_03.jpg` at about `0:25` | `Impact` | `1949` | courtroom, woman in dark hat/veil at witness area |
| 4 | `0:30-0:40` | `segment_04.jpg` at about `0:35` | `Meet John Doe` | `1941` | tense interior with seated woman, older standing man, tall man at right |
| 5 | `0:40-0:50` | `segment_05.jpg` at about `0:45` | `Suddenly` | `1954` | domestic room, three men, fedora-wearing man near window |

Accepted aliases are limited to aliases in `ground_truth.json` and harmless
formatting variants such as `Dressed to Kill (1941)` where the title and year
remain unambiguous. Different films, franchise labels, remakes, placeholders
such as "unknown", and right-genre/wrong-title guesses do not count.

If public sources conflict with this locked ground truth, the hidden ground
truth controls. The executor must produce its own screenshots from the local
video; hidden reference filenames or reference assets are not candidate
deliverables.

## 4. Target Resolution and Normalization

Match each CSV row and HTML card to a canonical segment using this order:

1. explicit `segment_order`, `segment`, `clip_label`, or time-window metadata;
2. the visual content of the linked `screenshot_file`, compared to the hidden
   contact sheet and per-segment frames;
3. CSV/card order, only when no explicit or visual mapping is available.

A segment can receive credit only once. Duplicate rows/cards for one segment do
not cover a missing segment. Extra rows/cards for noncanonical movies are
hallucinated content.

Normalize movie titles case-insensitively and ignore minor punctuation,
parenthetical year suffixes, and leading/trailing whitespace. Release years must
match the canonical four-digit year exactly. A correct title with a wrong or
missing year is not a correct movie identity for caps, though the title may
receive limited line-item credit where the rubric explicitly allows it.

A valid screenshot must:

- exist on disk under `/tmp_workspace/results/movie_picks_assets/` or a
  subpath referenced from that directory;
- be referenced by the CSV and rendered or linkable from the HTML;
- be an actual frame from the local compilation, not a web still, generated
  image, repeated thumbnail, or hidden reference path; and
- visually match the same 10-second segment as the row/card's movie identity.

Small timestamp drift inside the correct 10-second window is acceptable. A frame
from the wrong segment, an unrelated classic-film still, or a repeated frame
used for multiple segments is incorrect.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 - Required deliverables and schema.** Full credit requires
  `movie_picks.csv` and `movie_picks.html` in `/tmp_workspace/results/`, a
  screenshot asset directory, at least five candidate rows/cards, and all
  required CSV columns. Award 0.05 if only one of CSV/HTML is usable. Award
  0.00 if neither primary result file is usable.

- **0.35 - Canonical movie identity by segment.** There are five scored
  segment identity slots worth 0.07 each. For each segment, award 0.05 for the
  canonical title or accepted alias and 0.02 for the exact canonical release
  year, after assigning the row/card to a segment under Section 4. Missing,
  placeholder, wrong-title, wrong-year, or wrong-segment answers receive no
  credit for the failed subslot.

- **0.20 - Screenshot provenance and segment match.** There are five scored
  screenshot slots worth 0.04 each. For each segment, award credit only if the
  referenced screenshot file exists, is under `movie_picks_assets/`, is visible
  from the HTML/card path, and visually matches that segment's 10-second local
  source window. Do not award this credit for web images, copied reference
  paths, duplicate screenshots covering multiple segments, broken image links,
  or screenshots from the wrong segment.

- **0.15 - CSV/HTML cross-file mapping and coverage.** There are five scored
  segment coverage slots worth 0.03 each. For each segment, the CSV row, HTML
  card, title/year, and screenshot reference must all describe the same
  canonical segment. Full credit requires exactly one coherent card/row for
  each of the five segments. Rows/cards may appear in any order only when
  segment labels or screenshots make the mapping unambiguous.

- **0.10 - Clip-specific recommendation and identification evidence.** There
  are five scored evidence slots worth 0.02 each. For each segment, award credit
  when the recommendation reason is specific to the identified movie or visible
  scene, and `identification_clue` briefly records a concrete visual, dialogue,
  search term, or source-confirmation clue. Generic praise, empty confidence
  notes, or clues that could fit nearly any black-and-white film receive no
  credit for that segment.

- **0.10 - Local-source grounding and non-hallucination.** Award up to 0.05 for
  visible evidence that the executor opened, scrubbed, probed, or extracted
  frames from the required local video. Award up to 0.05 for avoiding
  hallucinated noncanonical movies, external screenshots presented as local
  frames, fabricated segment labels, or unsupported claims that are not backed
  by the saved artifacts.

## 6. Scoring Policy / Score Caps

Compute the rubric total, then apply every applicable cap below by `min`.
Caps are intentionally strict: polished design, confident wording, or correct
generic genre analysis cannot compensate for wrong locked facts or ungrounded
screenshots.

- **Cap at 0.30 - No primary deliverables.** Neither `movie_picks.csv` nor
  `movie_picks.html` exists or parses as a usable result.
- **Cap at 0.50 - One primary deliverable missing.** Exactly one of the CSV or
  HTML is missing or unusable.
- **Cap at 0.45 - No local-video grounding.** The visible trace and artifacts
  show no opening, probing, scrubbing, frame extraction, or screenshot capture
  from `/tmp_workspace/clawbench/sources/classic_movie_compilation.mp4`.
- **Cap at 0.84 - Any wrong or missing movie identity.** Fewer than all five
  canonical segment identities have both the correct title and correct release
  year.
- **Cap at 0.60 - Only three canonical identities correct.** Exactly three of
  the five segment identities are correct.
- **Cap at 0.45 - Two or fewer canonical identities correct.** At most two of
  the five segment identities are correct, including placeholders or
  unconfirmed rows.
- **Cap at 0.35 - Mostly fabricated identity set.** The output primarily names
  noncanonical films, remakes, franchises, or generic unknowns instead of the
  locked five-film set.
- **Cap at 0.84 - Any wrong segment mapping.** All five movie IDs may be
  present, but at least one title/year is attached to the wrong segment,
  screenshot, time window, CSV row, or HTML card.
- **Cap at 0.75 - Substantially scrambled segment mapping.** Two or more
  titles/screenshots/time windows are mapped to the wrong segment, even if the
  correct movie titles appear somewhere in the output.
- **Cap at 0.60 - Segment mapping cannot be determined.** The output lists
  movies but provides no reliable row/card order, segment labels, time windows,
  or screenshot evidence that assigns them to the five source segments.
- **Cap at 0.84 - Any required screenshot missing.** One or more of the five
  canonical segments lacks a referenced, existing screenshot file.
- **Cap at 0.65 - Multiple screenshots missing.** Fewer than four valid
  segment screenshots are present.
- **Cap at 0.50 - No usable screenshots.** Screenshots are absent, all image
  links are broken, or only nonlocal/web/generated images are supplied.
- **Cap at 0.84 - Any screenshot fails the five-window source check.** One or
  more submitted screenshots do not visually match the same 10-second source
  segment as the row/card they support.
- **Cap at 0.70 - Screenshot set does not cover the five 10-second source
  segments.** Screenshots exist but are repeated, drawn from fewer than five
  distinct segment windows, drawn from wrong windows, or cannot be matched to
  the hidden contact sheet/per-segment frames.
- **Cap at 0.70 - Required card coverage incomplete.** The HTML exists but
  omits one or more canonical segment cards, or the CSV has fewer than five
  canonical rows.
- **Cap at 0.84 - Required identification clues absent.** The
  `identification_clue` column is missing, empty for most rows, or contains only
  generic confidence statements with no clip-level evidence.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** stop. A passing run must have all five
  canonical title/year identities, correct segment mapping, five local
  screenshots matching the five 10-second source windows, complete CSV/HTML
  cards, and specific identification clues. If any cap below 0.90 applies, the
  run cannot pass.
- **Continue (`0.60 - 0.89` after caps):** request repair when follow-up is
  available. Typical continue cases include exactly four correct movie IDs, one
  missing or wrong screenshot, one title attached to the wrong segment, missing
  clues despite otherwise correct facts, or incomplete HTML/CSV wiring that is
  fixable from existing artifacts.
- **Fail (`< 0.60` after caps):** do not request more work. Typical fail cases
  include two or fewer correct canonical identities, no usable screenshots, no
  evidence of local-video use, mostly fabricated movie IDs, or missing primary
  deliverables.

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
public user simulator:

- `references/eval_rule.md` - this grading specification.
- `references/ground_truth.json` - canonical segment identities, accepted
  aliases, locked source metadata, reference screenshot hashes, and output
  expectations.
- `references/reference_movie_picks.csv` and
  `references/reference_movie_picks.html` - reference-format examples.
- `references/reference_movie_picks_notes.md` - authoring notes for the frozen
  segment list.
- `references/reference_assets/movie_segments_reference_sheet.jpg` and
  `references/reference_assets/segment_01.jpg` through `segment_05.jpg` -
  hidden frames used to verify screenshot segment provenance.

## 9. Dynamic Content Note

This is an offline static-video task. No live web result is authoritative over
the hidden reference snapshot. If the on-disk source video and
`ground_truth.json` ever drift apart, treat `ground_truth.json` and the hidden
reference frames as authoritative and flag the fixture drift rather than
re-judging the task from external sources.
