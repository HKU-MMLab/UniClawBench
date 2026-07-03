# Hidden Evaluation Rule — task_104_18_linked_trip_landmarks_map

## 1. Grading Philosophy

Grade the executor on whether it delivered a video-grounded landmark-order map
for the linked YouTube video, not merely a polished city attraction list.

The three artifacts must agree with each other, but artifact existence alone is
never enough for a pass. A pass requires all of:

- the correct linked resource,
- at least five concrete stops visible in, or strongly grounded by, the video,
- an order derived from video viewing rather than subtitles, descriptions,
  blogs, or generic itinerary knowledge,
- usable coordinates for each counted stop, and
- an HTML map whose markers and route match the CSV order.

After applying score caps, use these bands exactly:

- **Pass**: `>= 0.90`
- **Continue**: `0.60 - 0.89`
- **Fail**: `< 0.60`

## 2. Task Contract

The public task asks the executor to open the YouTube link and directly watch
the travel video before creating a landmark-order map. Required outputs are:

- `/tmp_workspace/results/linked_trip_map.html`
- `/tmp_workspace/results/landmarks_order.csv`
- `/tmp_workspace/results/landmarks_notes.md`

The CSV must parse and contain at least these columns:

- `order`
- `landmark_name`
- `location_text`
- `lat`
- `lng`

The minimum acceptable deliverable has at least five landmark rows. Rows must
be concrete named stops or tightly bounded visual areas from the video.
Generic rows such as `shopping area`, `old street`, `temple`, `park`, or
`neighborhood area` do not count unless the notes identify why the video
supports that specific row and the coordinate is clearly declared approximate.

`landmarks_notes.md` must provide row-level visual evidence for the selected
stops, such as timestamps, saved-frame references, visible signage, on-screen
text, or distinctive visual features. This aligns with the public instruction
that the executor must judge landmarks and order from the video itself.

## 3. Source-Selection Rules

The locked resource is:

- URL: `https://www.youtube.com/watch?v=ndAJTy8X3eU`
- Video ID: `ndAJTy8X3eU`
- Title: `5-Day Beijing Itinerary + Top Things to Do for First Timers - Solo China Vlog`
- Channel: `Roseanne Ducut`
- City: Beijing, China

Wrong-resource outputs are not recoverable by formatting quality. Other-city
maps or generic regional maps are wrong.

Canonical evidence for landmark identity and ordering is visible video content:
direct playback, saved screenshots, frame extraction, storyboard inspection, or
other video-facing visual review of the linked video. Page metadata, subtitles,
auto-transcripts, descriptions, comments, travel blogs, and search results may
only help with spelling or coordinate lookup after a visually observed stop has
already been identified. They cannot be the primary basis for selecting
landmarks or ordering them.

## 4. Locked Ground Truth

Grade against `references/ground_truth.json` plus the hidden reference files:

- `references/reference_landmarks_order.csv`
- `references/reference_landmarks_notes.md`

The task yaml must not expose any answer-bearing reference. The concrete
landmark pool, accepted aliases, core-anchor classes, coordinate anchors, and
relative order constraints are supervisor-only data in the hidden reference
files above. Do not surface those final landmark answers in the public task or
in any executor-facing source.

For pass-level scoring, normalize candidate names to the landmark classes and
aliases configured in the hidden ground truth. Video-evidenced additions may
also count when the notes provide visible evidence and coordinates match the
named place. Do not count more than one broad/area-style row toward the
five-landmark minimum unless the video evidence distinguishes them as separate
named stops.

The pass-level relative order must be video-derived and must not contradict
the locked sequence constraints in `ground_truth.json`. An exact copy of the
hidden reference CSV is not required, but pass-level answers must include at
least five countable landmark classes, include at least two configured core
anchors, and preserve the visible route order claimed in the notes, CSV, and
map.

## 5. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within each line only when the
evidence is explicit in the artifacts or run trace.

- **0.10 - Required artifact shape.** All three required files exist under
  `/tmp_workspace/results/`. The CSV parses, has the required columns, has
  integer-like increasing `order` values, and has at least five rows. The notes
  file is non-empty and the HTML file is non-empty.

- **0.20 - Landmark identity and completeness.** Full credit requires at least
  five countable landmark classes from the locked ground truth or
  video-evidenced additions, with no duplicate inflation. The answer must
  include at least two configured core anchors from the hidden ground truth.
  Give up to 0.18 when five countable landmarks are present but only one core
  anchor is present or one row is overly generic. Give up to 0.10 for three or
  four countable landmarks from the correct city/resource. Zero this line for
  wrong-city or mostly generic rows.

- **0.15 - Visit-order correctness.** Full credit requires the CSV order,
  notes order, and map route to preserve the video-derived sequence and the
  locked relative-order constraints in the hidden ground truth. Give up to
  0.08 for one unsupported adjacent swap or one weakly justified insertion.
  Zero this line when the order is alphabetical, geographically optimized,
  copied from a generic itinerary, or internally inconsistent.

- **0.15 - Visual-video grounding.** Full credit requires row-level evidence
  for at least five counted landmarks, using timestamps, frame/storyboard
  references, saved screenshots, on-screen text, or distinctive visual
  features. At least three counted rows must have strong direct evidence such
  as visible on-screen text, an unmistakable landmark, or a saved frame. Give
  up to 0.08 when the notes mention visual review but lack row-level evidence.
  Zero this line when subtitles, page descriptions, blogs, or search results
  are the primary basis for identity or order.

- **0.15 - Coordinate accuracy and specificity.** Full credit requires numeric
  latitude/longitude for every counted row, with coordinates matching the named
  place within the tolerances configured in the hidden ground truth. Give up to
  0.08 for one or two imprecise but plausible coordinates. Zero this line when
  coordinates are missing, non-numeric, placeholders, outside the locked
  geographic region, or attached to the wrong named landmark.

- **0.10 - HTML map quality.** Full credit requires a real interactive map
  artifact that can be opened locally, shows one marker per CSV row or counted
  landmark, and draws an ordered route/polyline/connection. Give up to 0.05 if
  the map is present but has minor rendering or basemap issues while markers
  and route data are still inspectable. Zero this line if the HTML is missing,
  static prose only, or does not encode markers and an ordered route.

- **0.10 - CSV, map, and notes consistency.** Full credit requires the same
  ordered landmark set in all three deliverables. Names may be normalized, but
  row count, order, coordinates, and route endpoints must agree. Give up to
  0.05 for one minor naming mismatch that does not change the route. Zero this
  line if the map hardcodes a different landmark list/order than the CSV, if
  the notes describe a different route, or if map coordinates do not correspond
  to the CSV.

- **0.05 - Uncertainty handling and no hallucinated extras.** Full credit
  requires uncertain rows to be labeled as approximate and justified from
  visible video evidence. Fabricated, unsupported, or travel-guide-only stops
  lose this line. Extra rows are allowed only if they are video-grounded and do
  not distort the required ordered route.

## 6. Scoring Policy / Score Caps

Compute the rubric total, then apply every applicable cap by taking the
minimum. Caps are intentionally stricter than the raw rubric for high-risk
failure modes.

- **Cap at 0.30 - No useful deliverables.** Two or more required artifacts are
  missing, empty, or unparsable.

- **Cap at 0.30 - Wrong resource or wrong city.** The result is primarily
  about another city, a generic regional itinerary, or a different video.

- **Cap at 0.45 - No meaningful visual-video grounding.** The trace and
  artifacts show no meaningful playback, frame/storyboard inspection,
  screenshot capture, or visual analysis of the linked video. Opening the page
  or reading metadata alone is not enough.

- **Cap at 0.60 - Non-visual shortcut used as primary source.** The route is
  substantially based on subtitles, auto-transcripts, page descriptions,
  comments, blogs, travel guides, or search snippets, even if some video access
  occurred.

- **Cap at 0.50 - Fewer than three countable landmarks.** The CSV contains
  fewer than three concrete video-grounded landmark classes after duplicate
  and generic rows are removed.

- **Cap at 0.70 - Fewer than five countable landmarks.** The CSV contains only
  three or four countable video-grounded landmark classes.

- **Cap at 0.84 - Missing core-anchor coverage.** The answer has at least five
  countable rows but includes fewer than two configured core anchors from the
  hidden ground truth. This prevents a pass for a route made only of secondary
  stops.

- **Cap at 0.75 - Wrong landmark order.** The answer has at least five
  plausible landmarks but contains two or more major inversions against the
  locked relative-order constraints, or places route segments in an unsupported
  itinerary order.

- **Cap at 0.84 - Weak ordered-route evidence.** Landmark identities are
  mostly correct, but the notes do not provide enough visual/timestamp
  evidence to justify the stated order. This is a continue case, not a pass.

- **Cap at 0.55 - HTML map missing or unusable.** `linked_trip_map.html` is
  absent, empty, not HTML, or contains no inspectable marker/route data.

- **Cap at 0.70 - Bad map/CSV consistency.** The map uses a different
  landmark list, order, or coordinate set than `landmarks_order.csv`, or the
  route/polyline does not follow the CSV order.

- **Cap at 0.80 - Partial map/CSV consistency failure.** Marker count differs
  from CSV row count by more than one, order labels are missing or misleading,
  or the map omits a counted stop while the CSV and notes otherwise look
  plausible.

- **Cap at 0.50 - Fabricated or unusable coordinates.** Coordinates are
  placeholders (`0,0`), identical repeated values, city centroids for all rows,
  non-numeric for most rows, outside the locked geographic region, or attached
  to unrelated places.

- **Cap at 0.70 - Multiple coordinate mismatches.** Two or more counted rows
  have coordinates materially inconsistent with their named landmarks after
  allowing the hidden tolerance rules.

- **Cap at 0.84 - One major coordinate mismatch.** Exactly one counted row has
  a materially wrong coordinate, unless the row is an explicitly approximate
  area row and the coordinate is still in the declared neighborhood.

- **Cap at 0.50 - Hallucinated route inflation.** The CSV reaches five rows
  mainly by splitting one visual area into several generic rows or by adding
  unsupported attractions not visible in the video.

## 7. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** Stop. The artifacts are complete, the route
  is video-grounded, at least five countable landmarks are present, the order is
  justified, the coordinates are usable, and the map matches the CSV.

- **Continue (`0.60 - 0.89` after caps):** Ask for one focused revision when
  the attempt is substantively video-based but fixable. Typical continue cases
  include thin visual evidence, one missing core anchor, one major coordinate
  error, insufficient notes for ordering, or a map/CSV mismatch that can be
  repaired without redoing the whole task.

- **Fail (`< 0.60` after caps):** Do not request more work. This includes
  wrong-resource/wrong-city outputs, missing or unusable deliverables, no
  meaningful video grounding, fabricated coordinate sets, or fewer than three
  countable landmarks.

When giving continue feedback, point to the lowest-scoring concrete defect:
for example, "add row-level video-frame evidence for at least five landmarks",
"fix the map so it uses the CSV order", or "replace generic/fabricated rows
with video-visible landmarks."

## 8. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
public user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - locked resource metadata, canonical
  landmark pool, accepted aliases, order constraints, and common mistakes.
- `references/reference_landmarks_order.csv` - hidden example route and
  coordinate anchors.
- `references/reference_landmarks_notes.md` - hidden notes describing the
  intended video-grounded boundary.

## 9. Dynamic Content Note

This is an offline evaluation of the current fixture state. The linked YouTube
resource is treated as locked to the metadata in Section 3 and
`ground_truth.json`. If the live page later changes, do not re-author the
answer from new web content during grading. Use the hidden ground truth and
the visible run artifacts available to the supervisor.
