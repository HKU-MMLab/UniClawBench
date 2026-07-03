# Hidden Evaluation Rule — task_103_01_headphone_review_price_compare

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should care most about whether the executor found the intended Bilibili and YouTube recommendation sources, resolved the user's fuzzy creator memory correctly, identified the shared brand/product relationship, and produced an evidence-backed buying note. Source screenshots matter because finding the correct two recommendation videos is itself a core long-context target-resolution checkpoint. Price and specification evidence matters because live retail pages can vary and the final recommendation must be auditable.

## 2. Task Contract

The public task asks the executor to install/use the Bilibili skill, search Bilibili for 2025 head-worn headphone recommendations with attention to `poorplayer (Qiong Wan Zu)`, find a This is Tech Today YouTube recommendation video, save source screenshots, identify shared recommended brand/product overlap, compare Amazon and Walmart prices in the Los Angeles region, record requested product parameters when models differ, and save a final Markdown buying note under `/tmp_workspace/results/`.

Completion means the executor saves a clear final recommendation/comparison document plus screenshots or links that support the identified video sources, products, prices, and requested parameters.

## 3. Source-Selection and Target-Resolution Rules

Treat `poorplayer (Qiong Wan Zu)` in the public prompt as a natural fuzzy memory, not an exact string requirement. The correct target creator is `PoorPlayers (Qiong Wan Zu)`; reward resolving the clue to that creator and video, including corrected capitalization/spelling. The relevant YouTube target is from This is Tech Today. If live search results shift, accept equivalent current pages only when they clearly point to the same creator/source and 2025 headphone recommendation content.

For product comparison, do not force a single identical SKU if the two sources recommend different Sony models. The expected relationship is a shared brand with different products, so a parameter-and-price comparison is valid.

## 4. Ground-Truth Snapshot

Hidden ground truth records:
- Bilibili creator: `PoorPlayers (Qiong Wan Zu)`.
- Bilibili video: `Self-funded testing of 600+ headphones, massive data with professional equipment, just to tell you which headphone is worth choosing in 2025 [PoorPlayers Loadout.sp]`.
- Bilibili URL: `https://www.bilibili.com/video/BV1aMbNzWEcb/`.
- YouTube creator: `This is Tech Today`.
- YouTube video: `The BEST Headphones of the Year: An AUDIO ENGINEER's Review`.
- YouTube URL: `https://www.youtube.com/watch?v=zakPRMGlRbw`.
- Expected shared brand: Sony.
- Expected products: Sony WH-ULT900N / ULT WEAR and Sony WH-1000XM6.

## 5. Checkpoint Rubric

- 0.20 Target Bilibili source: finds and screenshots the correct PoorPlayers (Qiong Wan Zu) recommendation source despite the imprecise user memory.
- 0.15 Target YouTube source: finds and screenshots the relevant This is Tech Today headphone recommendation source.
- 0.15 Shared-brand reasoning: identifies Sony as the shared brand and does not force the two sources into one identical product when evidence points to different Sony models.
- 0.20 Retail comparison: compares Amazon and Walmart for each relevant product, records links, prices, cheaper platform, and enough screenshots to audit the comparison.
- 0.20 Product parameters: records the requested technical parameters with evidence or clear current-source citations.
- 0.10 Final artifact: final Markdown is clear, grounded, includes screenshot paths, and gives a practical recommendation.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failure modes that make the result fundamentally unauditable or materially answer the wrong task; do not use them as a second copy of the checkpoint rubric.

If either target video source is replaced by an unrelated source or cannot be evidenced at all, cap at 0.70. If the executor never resolves the shared-brand comparison target, cap at 0.65. If the retail comparison is mostly fabricated, uses unsupported prices, or has no usable purchase-page evidence, cap at 0.60. If hidden references or credentials leak into the visible result, cap at 0.50.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor found some sources but is missing screenshots, has not yet compared both retailers, or has an incomplete final Markdown. Prefer `fail` when the executor finishes with the wrong video targets, no auditable retail/product evidence, a fabricated comparison, or hidden-reference leakage.

## 8. Hidden Reference Assets

- `ground_truth.json`: target videos, URLs, products, shared brand, and fuzzy-creator matching note.
- `product_evidence/bilibili_poorplayers_video.png`: Bilibili target evidence.
- `product_evidence/youtube_this_is_tech_today_video.png`: YouTube target evidence.
- `product_evidence/amazon_*`, `product_evidence/walmart_*`: retailer evidence examples.
- `product_evidence/sony_*_specs.png`: product parameter anchors.

## 9. Dynamic Content Note

Retail prices, availability, regional delivery, and page layout may change. Prefer executor screenshots/current links when plausible. Do not require exact hidden screenshot prices if the executor has better current evidence. Source-video identity is less volatile and should be held to the target-resolution rules above.
