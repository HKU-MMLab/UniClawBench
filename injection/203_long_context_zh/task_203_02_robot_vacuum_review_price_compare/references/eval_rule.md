# Hidden Evaluation Rule — task_203_02_robot_vacuum_review_price_compare

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce source use, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should care most about whether the executor genuinely read and understood BOTH long reviews and correctly extracted, attributed, and compared what each one said about its respective Dreame model — not merely whether it found the videos or looked up retail prices. The two reviews use very different formats (a single-product deep-dive vs a 12-machine round-up), so the central test is whether the executor can pull the right model out of each, report that reviewer's concrete findings and test numbers without mixing the two models up, and turn that into a grounded buying recommendation. Finding the correct sources and resolving the fuzzy creator memory is a prerequisite; the retail check and spec table support auditability but are secondary to faithful per-review comprehension.

## 2. Task Contract

The public task asks the executor to install/use the Bilibili skill, find the no-ad self-funded round-up by a creator the user vaguely remembers as `Mona's Home` (莫娜) — her first comparison episode testing a dozen new machines — and the Vacuum Wars YouTube video that rates a single Dreame model the best robot vacuum of 2025 so far; then read both reviews and (1) identify the distinct Dreame model each focuses on, (2) summarize each review's actual findings and test numbers for its model with correct attribution, (3) build a side-by-side spec comparison, (4) check US Amazon/Walmart pricing (or honestly document unavailability), and (5) recommend for a carpet-focused buyer vs an all-round buyer. The final note is saved at `/tmp_workspace/results/robot_vacuum_compare.md`.

Completion means the executor saves a clear final recommendation/comparison document plus screenshots or links that support the identified video sources, products, prices, and requested parameters.

## 3. Source-Selection and Target-Resolution Rules

Treat `Mona's Home` (莫娜) in the public prompt as a natural fuzzy memory, not an exact string requirement. The correct target creator is `莫娜的家Mona`, and the intended Bilibili video is her no-ad, self-funded round-up that tests 12 new 2026 robot vacuums, Episode 1 (`https://www.bilibili.com/video/BV1Mg5g67EN7/`), whose first four machines include the Dreame X60 Master. Reward resolving the clue to that creator and video, including corrected spelling/translation. The relevant YouTube target is the Vacuum Wars review of the Dreame L50 Ultra (`https://www.youtube.com/watch?v=cjryvaNYado`). If live search results shift, accept equivalent current pages only when they clearly point to the same creator/source and the same robot-vacuum recommendation content.

For product comparison, do not force a single identical SKU. The expected relationship is a shared brand (Dreame / 追觅) with different recommended models — the Bilibili source highlights the Dreame X60 Master and the Vacuum Wars video reviews the Dreame L50 Ultra — so a parameter-and-price comparison is valid.

## 4. Ground-Truth Snapshot

Hidden ground truth records:
- Bilibili creator: `莫娜的家Mona`.
- Bilibili video: `无广 | 12台2026年新款扫地机 横向对比视频（第一期）`.
- Bilibili URL: `https://www.bilibili.com/video/BV1Mg5g67EN7/`.
- YouTube creator: `Vacuum Wars`.
- YouTube video: `Dreame L50 Ultra Review - The BEST Robot Vacuum of 2025...So Far`.
- YouTube URL: `https://www.youtube.com/watch?v=cjryvaNYado`.
- Expected shared brand: Dreame (追觅).
- Expected products: Dreame X60 Master (Bilibili) and Dreame L50 Ultra (YouTube).

Source-grounded facts the executor's summary should be broadly consistent with (do not require exact wording):
- L50 Ultra (Vacuum Wars): top-ranked overall at video time; dual brush roll; spinning mop pads with carpet auto-lift; ProLeap threshold crossing (42mm single / up to 2.65in two-tiered); top-mounted LiDAR + front lasers/RGB camera obstacle avoidance; large 6,400mAh battery but below-average measured efficiency; flagship price.
- X60 Master (Mona's Home): track/roller-type mop pad; dual roller brush (front rubber roller + rear rubber-bristle roller) called good for carpet; relatively slow cleaning time (~100 min); some long-hair tangling and a complex mop-pad install.

## 5. Checkpoint Rubric

- 0.15 Target sources: finds and screenshots BOTH the correct `莫娜的家Mona` no-ad round-up (Episode 1) despite the imprecise user memory AND the Vacuum Wars Dreame L50 Ultra review.
- 0.15 Model identification: correctly identifies that each source focuses on a different Dreame model — the Bilibili round-up on the Dreame X60 Master and the Vacuum Wars deep-dive on the Dreame L50 Ultra — and does not blur them into one model.
- 0.30 Per-review comprehension (core): for EACH model, summarizes what that specific review actually said, including concrete strengths/weaknesses and at least some of the reviewer's specific test results or numbers, attributed to the right source. For the L50 Ultra this means Vacuum-Wars-style findings (e.g. top-ranked overall; very strong carpet deep-clean and pet-hair-on-carpet results; ProLeap threshold climbing ~42mm single / up to ~2.65in two-tiered; LiDAR + front-laser/RGB-camera obstacle avoidance; large battery but below-average measured efficiency / coverage per charge; spinning mop pads with carpet auto-lift; flagship price). For the X60 Master this means Mona's-Home-style findings (e.g. track/roller-type mop pad and dual roller brush highlighted as good for carpet; relatively slow cleaning time around 100 minutes; some long-hair tangling; complex mop-pad install). Reward correct attribution and concrete detail; penalize vague marketing-style praise with no review-grounded specifics, and penalize attributing one model's facts to the other.
- 0.15 Spec comparison: builds a side-by-side comparison of the two models covering suction (Pa), mopping method, threshold height, navigation/obstacle approach, and battery/runtime. Some of these specs (notably suction in Pa) are not stated in the review videos and must be pulled from the manufacturer or retailer product pages; reward values with a clear source citation (review, official spec page, or retailer listing) and accept an honest "not stated / not found" for a spec that genuinely cannot be located, rather than an invented number.
- 0.15 Retail check: checks Amazon and Walmart (US / Los Angeles) for each model, records links, prices, cheaper platform, and screenshots — OR honestly documents "not available / out of stock" with a screenshot where a model is not listed, instead of inventing a price.
- 0.10 Final artifact and recommendation: final Markdown is clear, grounded, includes screenshot paths, keeps the two reviews' claims distinct, and gives a practical recommendation for the carpet-focused buyer vs the all-round buyer.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failure modes that make the result fundamentally unauditable or materially answer the wrong task; do not use them as a second copy of the checkpoint rubric.

If either target video source is replaced by an unrelated source or cannot be evidenced at all, cap at 0.70. If the executor does not correctly identify the two distinct Dreame models (X60 Master from Bilibili, L50 Ultra from Vacuum Wars), or blurs the two models together, cap at 0.65. If the per-review summaries are vague marketing-style praise with essentially no review-grounded specifics, or if one model's findings are substantially attributed to the other, cap at 0.65. If the retail check is mostly fabricated or uses unsupported prices (as opposed to an honest "not available" finding), cap at 0.70. If hidden references or credentials leak into the visible result, cap at 0.50.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor found some sources but is missing screenshots, has not yet compared both retailers, or has an incomplete final Markdown. Prefer `fail` when the executor finishes with the wrong video targets, no auditable retail/product evidence, a fabricated comparison, or hidden-reference leakage.

## 8. Hidden Reference Assets

- `ground_truth.json`: target videos, URLs, products, shared brand, fuzzy-creator matching note, and source-grounded facts.
- `product_evidence/bilibili_monas_home_video.png`: Bilibili target evidence.
- `product_evidence/youtube_vacuum_wars_video.png`: YouTube target evidence.
- `product_evidence/amazon_*`, `product_evidence/walmart_*`: retailer evidence examples.
- `product_evidence/dreame_*_specs.png`: product parameter anchors.

(Prepared screenshots may be absent in this build; judge from text anchors and the executor's own screenshots when they are not present.)

## 9. Dynamic Content Note

Retail prices, availability, regional delivery, model naming, and page layout may change, and some Dreame models (e.g. the X60 Master) may have limited or regionally renamed US retail listings. Prefer executor screenshots/current links when plausible. Do not require exact hidden screenshot prices if the executor has better current evidence, and accept an honestly documented "not available / out of stock" finding for a model that is not listed on a given retailer rather than an invented price. Source-video identity is less volatile and should be held to the target-resolution rules above.
