# Hidden Evaluation Rule — task_103_06_self_hosted_rss_landscape

Use this file as the primary hidden judging spec. Prefer outcome-oriented checkpoints.

## 1. Grading Philosophy

The supervisor should judge whether the executor performed real enumeration research and produced a verified inventory of genuine self-hostable RSS/feed readers, correctly excluding SaaS-only readers and read-it-later apps. Because this is live research over a changing ecosystem, judge methodology, correct identification, verification quality, and enumeration discipline — not exact star counts.

## 2. Task Contract

The public task asks the executor to research and enumerate at least 10 genuine self-hostable RSS/feed readers, recording for each: repo/link, language, license, popularity/activity signal, deployment method (confirming it is self-hostable), and a one-line scope; to exclude or clearly flag SaaS-only readers and read-it-later apps; and to save the inventory to `/tmp_workspace/results/self_hosted_rss_landscape.md`.

## 3. Source-Selection and Target-Resolution Rules

A qualifying tool is an open-source feed reader you can run on your own server. SaaS-only readers (Feedly, Inoreader) do not qualify. Read-it-later/bookmarking apps (wallabag, Pocket, Instapaper) are not feed readers and must not be counted. Verification means confirming the project is genuinely self-hostable (Docker/binary/source) and open-source, by reading the repo — not name-guessing.

## 4. Ground-Truth Snapshot

Hidden ground truth (`ground_truth.json`) lists real anchors (e.g. `FreshRSS/FreshRSS`, `miniflux/v2`, `Athou/commafeed`, `fossar/selfoss`, `nkanaev/yarr`, `0x2E/fusion`, Tiny Tiny RSS, NewsBlur) and distractors to exclude (Feedly/Inoreader as SaaS-only; wallabag/Pocket as read-it-later). Star counts are a 2026-06-20 snapshot and need not match exactly.

## 5. Checkpoint Rubric

- 0.30 Enumeration: lists at least 10 genuine self-hostable feed readers with real, resolvable links.
- 0.25 Verification: for each tool, records language, license, deployment method, and an activity/popularity signal based on reading the repo — confirming it is actually self-hostable and open-source.
- 0.20 Enumeration discipline: SaaS-only readers and read-it-later apps are excluded or clearly flagged; reward including canonical anchors (FreshRSS, Miniflux, Tiny Tiny RSS, CommaFeed).
- 0.15 No fabrication: links are real and descriptions match the actual projects.
- 0.10 Deliverable: `self_hosted_rss_landscape.md` saved at the requested path, organized and readable.

## 6. Scoring Policy / Score Caps

The task passes only at score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

If fewer than 10 genuine self-hostable readers are identified, cap at 0.70. If SaaS-only readers are listed as self-hostable, or read-it-later apps are listed as feed readers, without flagging, cap at 0.70. If the list contains fabricated repos or wrong descriptions, cap at 0.55. If the output file is missing, cap at 0.40. If entries are unverified (no license/deployment check), cap at 0.65.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has a partial or partly-unverified list. Prefer `fail` when the inventory is mostly fabricated, miscategorizes SaaS/read-it-later as self-hosted feed readers throughout, or produces no output file.

## 8. Hidden Reference Assets

- `ground_truth.json`: definition, real anchors, distractors, expected fields, scoring notes.

## 9. Dynamic Content Note

GitHub stars and project activity change continuously. Judge live findings on correctness, verification, and enumeration discipline, not on matching the snapshot exactly.
