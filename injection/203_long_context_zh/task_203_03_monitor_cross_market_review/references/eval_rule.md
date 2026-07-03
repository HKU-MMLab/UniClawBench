# Hidden Evaluation Rule — task_203_03_monitor_cross_market_review

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce source use, or resolve ambiguity.

## 1. Grading Philosophy

The supervisor should care most about whether the executor genuinely read BOTH monitor buying guides and correctly extracted, attributed, and contrasted what each one recommends in the 2K / 1440p 27-inch high-refresh segment — turning two long, format-different guides (a Chinese 40+-monitor all-spec round-up vs a North American 1440p-focused guide) into a clear cross-market comparison. The central insight to be tested is that the two markets share some brands (ASUS and MSI) but essentially no shared specific models, with the Chinese guide leaning on domestic value brands (KTC, HKC, Titan Army/深色) that the North American guide never mentions. Finding the correct sources and resolving the 野生的装机宅 / 小峰 creator identity is a prerequisite; faithful per-guide model extraction and the cross-market brand analysis are the core. This task does NOT require retail price shopping — judge the analysis of the videos themselves.

## 2. Task Contract

The public task asks the executor to install/use the Bilibili skill, find the 2025 self-funded no-ad monitor round-up by `野生的装机宅` (who introduces himself as 小峰), and the Monitors Unboxed YouTube "Best 1440p Gaming Monitors of 2025" guide; then (1) extract each guide's 2K/1440p 27-inch high-refresh model picks, (2) identify the brands recommended by both guides and the specific model(s) each guide picks under those brands, (3) explain the cross-market differences including which brands are unique to each market, and (4) give a practical US-shopper takeaway. The final write-up is saved at `/tmp_workspace/results/monitor_1440p_compare.md`.

Completion means both guides are correctly identified and their segment picks extracted, the shared brands and the domestic-vs-international split are correctly analyzed, claims are attributed to the right source, and a usable Markdown comparison is saved.

## 3. Source-Selection and Target-Resolution Rules

The Bilibili creator's profile name is `野生的装机宅`; in the video he calls himself `小峰`. Treat either as a correct identification of the same source, and treat the intended video as his 2025 self-funded, no-ad round-up covering 40+ monitors across all specs (`https://www.bilibili.com/video/BV1gkwHerEP5/`). The YouTube target is the Monitors Unboxed "Best 1440p Gaming Monitors of 2025" update (`https://www.youtube.com/watch?v=SnS3DC3ClSI`). The analysis must be grounded in the two guides' own content; do not require or reward substituting unrelated third-party "best monitor" lists for the two named guides. If live pages shift, accept equivalent current versions only when they clearly are the same creator and the same guide.

## 4. Ground-Truth Snapshot

Hidden ground truth records each guide's 1440p 27-inch high-refresh picks and the cross-market structure (full lists in `ground_truth.json`). Key anchors:
- Bilibili (野生的装机宅 / 小峰) 2K 27-inch high-refresh picks include: KTC H27T22C, KTC H27T22X, HKC G27H2, Titan Army/深色 G73, ASUS VG27AQL3A, KTC H2716, MSI MAG274QRFW, ASUS VG27AQML EA.
- Monitors Unboxed 1440p picks include: AOC Q27G3XMN, MSI G274QPF-QD, LG 27G83A/27GP850, ASUS ROG XG27ACS, ASUS ROG XG27AQDMG, the QD-OLED group (MSI MPG271QRX, Dell Alienware AW2725DF, Gigabyte FO27Q3, ASUS ROG XG27ACDNG), LG 27G83Q / Gigabyte M27QX / MSI G274QPX, and the ASUS ROG Swift OLED PG27AQDP.
- Shared brands across both guides in this segment: ASUS and MSI — but with NO overlapping specific model.
- Brands essentially unique to the Bilibili guide: KTC, HKC, Titan Army/深色. Brands prominent in the YouTube guide but not in the Bilibili 2K-27 segment: AOC, LG, Dell/Alienware, Gigabyte.

Do not require the executor to list every model verbatim; reward correct, source-attributed extraction of a representative set plus the correct shared-brand and domestic-vs-international conclusions.

## 5. Checkpoint Rubric

- 0.15 Target sources: finds and screenshots BOTH the correct Bilibili 野生的装机宅/小峰 2025 round-up AND the Monitors Unboxed 1440p 2025 guide, resolving the 野生的装机宅/小峰 identity.
- 0.25 Per-guide model extraction (core): from each guide, lists a representative set of the actual 2K/1440p 27-inch high-refresh models recommended, attributed to the correct guide. Reward concrete real model names from each source (e.g. KTC H27T22C / HKC G27H2 / ASUS VG27AQML EA on the Bilibili side; AOC Q27G3XMN / ASUS ROG XG27AQDMG / Dell AW2725DF on the YouTube side). Penalize invented model names and penalize attributing one guide's models to the other.
- 0.25 Shared-brand analysis (core): correctly identifies ASUS and MSI as the brands recommended by both guides in this segment, names the specific model(s) each guide picks under those brands, and states that the exact models do not overlap across the two markets.
- 0.15 Video-only detail questions (anti-shortcut, core): correctly answers the four detail questions whose answers appear ONLY in the spoken video content, not in any written best-of summary (see `video_only_detail_qa` in ground truth): (a) the HKC G27H2 had a past 混发面板 / mixed-panel issue, now standardized on the AUO 8.b panel; (b) the cheapest 27-inch 2K pick, KTC H27T22C, is also called the H27T22S 护眼版; (c) among 1440p 360Hz QD-OLEDs the Dell Alienware AW2725DF is the "best calibrated" but, like the Gigabyte model, lacks decent USB-C power delivery; (d) the reviewer's rule of thumb is a 30-40% discount to step down from a 1440p 240Hz OLED to an LCD. Award proportionally across the four; these are the strongest signal that the executor actually watched the videos.
- 0.10 Cross-market difference: explains which brands are essentially unique to the Chinese guide (KTC, HKC, Titan Army/深色) vs prominent on the North American side (AOC, LG, Dell/Alienware, Gigabyte), capturing the domestic-vs-international split.
- 0.05 Reasoning/attribution: where a guide gives a standout reason for a pick (panel type, response time, local dimming/HDR, color accuracy, value), summarizes it and attributes it to the correct source.
- 0.05 Final artifact: final Markdown is clear, keeps the two guides' claims distinct, includes screenshot paths and source links, and gives a usable US-shopper takeaway.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for failure modes that make the result fundamentally unauditable or materially answer the wrong task; do not use them as a second copy of the checkpoint rubric.

If either target guide is replaced by an unrelated "best monitor" source or cannot be evidenced at all, cap at 0.70. If the executor claims the two guides recommend the same specific models, or otherwise misses that the shared brands (ASUS, MSI) have no overlapping model, cap at 0.65. If the per-guide model lists are largely fabricated or one guide's models are substantially attributed to the other, cap at 0.65. If the domestic-vs-international brand split is entirely missed, cap at 0.70. If the video-only detail questions are mostly wrong, missing, or answered with vague hand-waving — a strong sign the executor read a written best-of summary instead of watching the videos — cap at 0.70 even if the model lists look right. If hidden references or credentials leak into the visible result, cap at 0.50.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has found the sources but has incomplete model extraction, has not yet done the shared-brand analysis, or has an incomplete Markdown. Prefer `fail` when the executor finishes with the wrong sources, fabricated model lists, a claim that the two guides recommend identical models, or hidden-reference leakage.

## 8. Hidden Reference Assets

- `ground_truth.json`: target videos, URLs, per-guide model lists, shared brands, unique-brand split, source-grounded facts, and dynamic-content note.
- `source_evidence/bilibili_xiaofeng_video.png`: Bilibili target evidence (placeholder; may be absent).
- `source_evidence/youtube_monitors_unboxed_video.png`: YouTube target evidence (placeholder; may be absent).

(Prepared screenshots may be absent in this build; judge from text anchors and the executor's own screenshots when they are not present.)

## 9. Dynamic Content Note

Both videos are static and already published. Monitor availability and pricing change over time and differ by region, so do not require exact prices or exhaustive model lists. The per-guide model picks, the shared brands (ASUS, MSI) with non-overlapping models, and the domestic-vs-international brand split are the stable anchors. Source-guide identity is less volatile and should be held to the target-resolution rules above.
