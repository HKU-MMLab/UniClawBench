# Hidden Evaluation Rule — task_205_14_iwatch_web_compare

Use this file as the primary hidden judging spec for the task. Judge whether the executor performed a realistic pure-web product comparison and produced an auditable Markdown recommendation without inventing marketplace details.

## 1. Grading Philosophy

The task is about comparing a specific product across marketplace pages and an official product page. Prices, shipping, return policies, seller ratings, listing conditions, reviews, and availability are volatile. Honest documentation of unavailable, blocked, region-mismatched, used, refurbished, or wrong-variant listings is better than fabricating a perfect comparison.

## 2. Task Contract

Target product: Apple Watch Series 9 45mm Midnight Aluminum Case, Midnight Sport Band, GPS. Shipping/location context: Los Angeles, United States. Required marketplaces: Amazon, eBay, AliExpress. Required official source: Apple official product page. Final artifact: /tmp_workspace/results/apple_watch_series9_45mm_midnight_web_compare.md.

The executor should use only browser/web information, find one best-matching listing per marketplace when possible, compare required fields, verify target specifications against the official page, and make a recommendation based on total cost, spec match, seller credibility, return convenience, and product-specific concerns. If a marketplace lacks a credible match, the executor should mark it as missing or unsuitable rather than forcing a bad recommendation.

## 3. Target and Source Rules

The comparison must not recommend these wrong or unsuitable variants as if they were the target: Apple Watch SE, Series 8, Series 10, Ultra, 41mm, different color, different case material, Cellular version, renewed, used, open-box. Used, renewed, refurbished, open-box, locked, wrong-size, wrong-color, wrong-connectivity, or wrong-model listings may be mentioned only if clearly marked unsuitable or not directly comparable.

Required comparison fields: price, shipping / delivery estimate, return policy, seller/store credibility, condition, GPS / Cellular match, case size/color/material/band match, 2 pros, 2 cons.

No separate review page is required unless the executor uses one as supporting evidence.

## 4. Ground-Truth Snapshot

Hidden ground truth fixes the target product, marketplace set, official source requirement, required output path, required comparison fields, unsuitable variants, and any available process_evidence screenshots. Process evidence is illustrative and incomplete; missing hidden screenshots should not by itself penalize an executor who obtains current evidence or documents blocks.

## 5. Checkpoint Rubric

- 0.20 Product/spec verification: uses the official product page and correctly identifies the target configuration.
- 0.25 Marketplace coverage: checks Amazon, eBay, and AliExpress, with one best match or clear unsuitable/missing explanation for each.
- 0.20 Comparison completeness: records price, shipping/delivery, return policy, seller/store credibility, condition or product-specific fields, and pros/cons where available.
- 0.15 Recommendation quality: recommendation is based on total cost, credibility, returns, condition, and spec match rather than lowest sticker price alone.
- 0.10 Wrong-variant handling: avoids recommending wrong models, variants, used/refurbished/open-box items, or unsupported listings unless explicitly marked unsuitable.
- 0.10 Evidence and artifact: final Markdown exists at the required path and includes source URLs/evidence notes or documented blocks.

## 6. Score Caps

Pass threshold is 0.90. If the final artifact is missing, cap at 0.40. If the executor compares a materially wrong product family across most sources, cap at 0.55. If it omits the official product page or does not verify target specs, cap at 0.75. If it checks fewer than two marketplaces, cap at 0.70. If it fabricates prices, shipping, return policies, seller credibility, review content, or availability without evidence, cap at 0.65. If the final recommendation is not auditable because source links/evidence are mostly absent, cap at 0.70.

## 7. Continue vs Fail Guidance

Prefer continue when marketplace coverage, official spec verification, comparison fields, evidence, or final Markdown are incomplete. Prefer fail when the executor finishes with fabricated product data, materially wrong variants, no official verification, or no final artifact.
