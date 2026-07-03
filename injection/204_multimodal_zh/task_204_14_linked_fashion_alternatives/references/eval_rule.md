# Hidden Evaluation Rule — task_204_14_linked_fashion_alternatives

## 1. Grading Philosophy

Judge whether the executor produced a traceable shopping report from the
locked YouTube video, not whether it found any one predetermined set of Amazon
links. Product search is live and open-ended, so full credit depends on:

1. actual visual grounding in the linked video;
2. correct selection of the first three distinct outfit / styling segments;
3. screenshot-to-description consistency;
4. Amazon product evidence with concrete price / availability signals; and
5. item-role matching between visible garments and proposed alternatives.

Do not award high scores for polished formatting, self-reported confidence,
generic fashion knowledge, transcript-only summaries, or products that merely
share a broad mood. A pass requires the final artifact and the run evidence to
make the visual chain auditable from video frame to visible garment to
Amazon alternative.

## 2. Task Contract

The public task asks the executor to open
`https://www.youtube.com/watch?v=O_C_VUtUm80`, watch the actual video frames
and motion directly, identify the first 3 clear outfit / styling segments, save
clear screenshots under `/tmp_workspace/results/fashion_looks/`, and write
`/tmp_workspace/results/fashion_alternatives.md`.

For each of the 3 looks the report must include:

- one screenshot reference for the selected video frame;
- key visible item descriptions, covering outerwear / top, bottom, shoes if
  visible, and main style keywords;
- at least 2 Amazon alternative products with product name, concrete price,
  Amazon product link, and a short visual-similarity rationale;
- a price-tradeoff note showing the choice is relatively budget-friendly while
  preserving visual similarity.

If Amazon site search is unstable, the executor may use other web search to
locate candidates, but the final links must resolve to Amazon product/detail
pages. Amazon search-result URLs alone do not satisfy the product-link
requirement.

## 3. Source and Output Resolution

Locked resource:

- Video ID: `O_C_VUtUm80`
- URL: `https://www.youtube.com/watch?v=O_C_VUtUm80`
- Channel: `Betty Studio`
- Title: `【2026春夏流行趋势】8分钟教你今年春夏怎么穿最时尚 | Pantone流行色 | 儒雅诗人风`
- Published date in hidden snapshot: `2026-04-01`

Treat downloaded subtitles, third-party outfit summaries, search-result
snippets, Pinterest / shopping collages, and prior styling knowledge as
non-canonical. They may help orientation only; they cannot replace watching
the linked video. A cropped playback frame is acceptable only when the trace or
artifacts also show it came from the locked video, not from an unrelated image
source.

The canonical output path is `/tmp_workspace/results/fashion_alternatives.md`.
When grading stored run artifacts, the supervisor may inspect mirrored
`result/` or `visible/result/` directories as evidence of the same files, but
the output-location credit is full only when the required paths or their
mirrored copies are auditable.

## 4. Locked Ground Truth and Acceptable Variance

Use `references/ground_truth.json` as the authoritative hidden snapshot. The
reference anchors define the style boundaries for the intended early video
segments:

- `All That Jazz / 爵士时代`: retro dressy mood, clean tailoring or fitted
  outer layer, and evening-leaning styling. It should not collapse into a
  plain office suit or athleisure.
- `Poetcore / 儒雅诗人风`: soft romantic / literary styling with a draped or airy
  top layer, cape / cardigan / shawl-like layer, loose outerwear, wide-leg
  trousers, or a long flowing skirt. It should not be ordinary oversized basics
  or rigid businesswear.
- `Balloon Pants / Capri Pants`: the lower-half silhouette is the focus, using
  balloon / barrel / capri / cropped trousers balanced by a simpler top. A
  skirt-led or dress-led look does not satisfy this anchor.

Exact labels, timestamp granularity, language, and minor color / fabric
descriptions may vary. Award full visual-grounding credit if the executor
selects the first three clear video-grounded outfit segments and the screenshots
and item descriptions satisfy these hidden style boundaries or objectively
prove an earlier distinct styling segment from real playback. Do not give full
credit to three later color-theme examples, presenter-only frames, duplicated
outfit formulas, or looks selected from outside the first-three sequence.

## 5. Valid-Look Criteria

A look is valid only if all of the following are true:

- The screenshot file exists, is readable, and shows a real frame from the
  locked video playback rather than a thumbnail, black/error frame, presenter
  talking head without an analyzable outfit, web-search image, or shopping
  page.
- The report ties the screenshot to a distinct early outfit / styling segment,
  using a timestamp, order note, filename, or trace evidence sufficient for the
  supervisor to verify sequence.
- The visible item description matches the screenshot. Unknown or obscured
  items should be marked as not visible; invented shoes, bottoms, fabrics, or
  accessories count against grounding.
- The look has at least 2 Amazon alternatives. Each alternative is assigned to
  a garment role or coherent outfit role that is visible in the screenshot.
- Each alternative includes a product name, concrete price observed at search
  time, Amazon product/detail link, and a rationale naming visual attributes
  such as silhouette, garment role, color family, material / texture, volume,
  length, tailoring, or styling mood.

For Amazon links, accept standard product URLs including `/dp/ASIN`,
`/gp/product/ASIN`, or equivalent Amazon detail pages with tracking parameters.
Do not count `/s?k=...` search pages, category pages, ads without a product
detail target, non-Amazon retailer pages, or dead links as valid alternatives
unless the report also provides enough ASIN/product detail evidence to verify
the product.

## 6. Checkpoint Rubric

Weights sum to 1.00. Award partial credit within each line only when the
evidence is auditable.

- **0.10 - Output shape and required paths.** Full credit requires
  `fashion_alternatives.md` plus screenshot files under
  `fashion_looks/`, with exactly or clearly at least 3 separated look sections.
  Each section must reference its screenshot and contain item descriptions,
  Amazon alternatives, prices, links, and similarity rationale. Missing
  markdown, fewer than 3 look sections, or unverifiable paths receive little or
  no credit here.

- **0.15 - Locked-video playback grounding.** Full credit requires evidence
  that the executor opened the locked YouTube video or an equivalent YouTube
  playback surface and reviewed actual frames/motion. Screenshots must be from
  the locked video. Text-only research, subtitle downloads, third-party outfit
  pages, image search, or unsupported claims of watching receive no credit.

- **0.25 - Three distinct first-video looks.** Full credit requires 3 valid
  looks representing the first 3 clear outfit / styling segments, with no
  duplicates and no presenter-only or transition frames. The selected looks
  must satisfy the hidden anchor boundaries in §4 or objectively demonstrate an
  earlier distinct segment from playback. Award roughly one third of this line
  per valid, correctly ordered look; do not credit a look whose screenshot and
  description do not match.

- **0.15 - Screenshot-to-item accuracy.** Full credit requires each look to
  describe only visible or reasonably inferable garment roles: outerwear / top,
  bottom, shoes if visible, and style keywords. Penalize invented shoes,
  bottoms, fabrics, exact colors, accessories, or segment names not supported by
  the screenshot. If a role is obscured and the report says so, do not penalize
  for that role.

- **0.15 - Amazon price and availability evidence.** Full credit requires 6
  valid Amazon product/detail links total, 2 per look, with product names and
  concrete prices observed at run time. Prices may be approximate or localized
  currency if clearly stated. Search-result links, missing prices, "price
  varies" without a concrete observed price, unavailable products with no
  replacement, or non-Amazon links lose credit.

- **0.15 - Visual similarity and item-role matching.** Full credit requires
  each alternative to match the role it is meant to replace and to explain
  specific visual attributes. A dress or skirt cannot replace a striped shirt;
  a plain office blazer cannot replace a jazz / retro evening look without
  supporting retro evidence; a skirt-led item cannot satisfy the pants-silhouette
  anchor. Generic "same vibe" explanations, filler products, or alternatives
  chosen only because they are cheap receive little credit.

- **0.05 - Integrity and no hallucinated evidence.** Full credit requires no
  fabricated source claims, no contradiction between trace and report, no
  invented screenshots, no false claim that missing paths exist, and no
  privacy/credential leakage. Minor formatting issues do not affect this line.

Total: `0.10 + 0.15 + 0.25 + 0.15 + 0.15 + 0.15 + 0.05 = 1.00`.

## 7. Scoring Policy / Score Caps

Compute the rubric score first, then apply all applicable caps by `min`.
Caps are strict pass guards; a run capped below `0.90` cannot pass regardless
of polish or self-reported confidence.

- **Cap at 0.30 - Missing final report.** No usable
  `fashion_alternatives.md` exists in the required output area or mirrored run
  artifact.
- **Cap at 0.35 - Wrong source.** The report is based on the wrong video,
  wrong channel, generic trend research, or unrelated images.
- **Cap at 0.40 - Text-only or non-visual attempt.** There is no real
  screenshot evidence from the locked video playback.
- **Cap at 0.50 - Fabricated or unrelated screenshots.** Screenshots are
  thumbnails, black/error pages, shopping pages, unrelated web images, or
  otherwise not traceable to the locked video.
- **Cap at 0.55 - No direct playback evidence.** The only source evidence is
  downloaded subtitles, third-party summaries, downloaded-frame extraction, or
  transcript/search snippets, with no auditable direct playback review of the
  linked video.
- **Cap at 0.59 - Fewer than 3 valid looks.** The final report has only 1 or
  2 valid video-grounded outfit sections, even if those sections are strong.
- **Cap at 0.65 - Three sections but fewer than 3 grounded segments.** The
  markdown has 3 sections, but at least one section is presenter-only,
  transition/error footage, duplicate, or not tied to a distinct video outfit.
- **Cap at 0.75 - Wrong sequence or anchor mismatch.** The looks are from the
  locked video but are later segments, color-theme examples, or otherwise not
  the first-three styling sequence required by the ground truth.
- **Cap at 0.80 - Incomplete Amazon evidence.** Any look lacks 2 valid Amazon
  product/detail links with concrete prices and product names.
- **Cap at 0.82 - Role mismatch or generic shopping filler.** One or more
  alternatives are visibly the wrong garment role for the selected look, or the
  report relies on generic low-price items without visual similarity evidence.
- **Cap at 0.82 - Weak budget / availability support.** Products are named but
  prices, availability, or price-tradeoff reasoning are missing or too vague to
  verify.
- **Cap at 0.30 - Privacy or credential leak.** Any value whose environment
  variable is declared private is emitted in user-visible output.

## 8. Continue vs Fail Guidance

- **Pass (`>= 0.90` after caps):** The report is complete, video-grounded, and
  has 3 valid first-sequence looks with 6 role-matched Amazon alternatives,
  concrete prices, and auditable screenshot evidence. The executor should stop.
- **Continue (`0.60 - 0.89` after caps):** The work is substantially grounded
  in the correct video and likely recoverable with one targeted revision, such
  as replacing a weak Amazon product, adding missing concrete prices, tightening
  the visual rationale, or correcting one weakly described look.
- **Fail (`< 0.60` after caps):** Record `finalStatus=failed`; do not pass the
  attempt. This includes missing report, wrong source, text-only work, fabricated
  screenshots, fewer than 3 valid looks, or mostly non-Amazon / non-role-matched
  shopping output.

If follow-up budget is exhausted, still apply the numeric thresholds exactly:
scores below `0.60` are fail, scores from `0.60` to `0.89` are continue only if
the harness can continue, and scores `>= 0.90` are pass.

## 9. Hidden Reference Assets

These files are supervisor-only and must not be surfaced to the executor or
public user simulator:

- `references/eval_rule.md` - this grading spec.
- `references/ground_truth.json` - locked resource metadata, canonical style
  anchors, acceptable synonyms, negative boundaries, output schema, and common
  mistakes.
- `references/reference_fashion_anchor_report.md` - compact style-boundary aid.

## 10. Dynamic Content Note

The video identity and style-anchor boundaries are locked by the hidden
snapshot. Amazon inventory, prices, availability, and URL shapes may change.
Do not grade against an exact hidden product list. Instead, grade whether the
executor captured enough run-time evidence to show that each proposed product
was an Amazon product, had an observed price, was available or plausibly
orderable at search time, and visually matched the garment role it was meant to
replace.
