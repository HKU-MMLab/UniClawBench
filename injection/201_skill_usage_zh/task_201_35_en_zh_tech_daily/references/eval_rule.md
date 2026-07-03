# Hidden Evaluation Rule — task_201_35_en_zh_tech_daily

## 1. Grading Philosophy

Judge the executor on whether the public request was actually completed and
whether the three declared workspace skills under `/root/skills/` were
genuinely consulted while producing the digest. The canonical Top 10 is
deterministic — there is exactly one correct ordering and one correct set
of category counts and day counts. Score caps in §6 override rubric totals.

## 2. Task Contract

The user has two snapshots in `/tmp_workspace/clawbench/sources/`:

- `ai_news_zh_snapshot.json` — 60 Chinese-language tech news items, 20 each
  for 2026-04-18, 2026-04-19, 2026-04-20, each with title, link, pub_date,
  summary, primary_category.
- `github_trending_snapshot.json` — 45 GitHub trending Python AI/LLM/agent
  repos, 15 each captured on 2026-04-18, 2026-04-19, 2026-04-20, each with
  name, description, url, stars, captured_on, topics, primary_category.

Required artifacts:

1. `/tmp_workspace/results/digest.md` containing
   - `## Top 10` — exactly 10 items, 5 news + 5 repos, in the canonical
     order defined in §3 and §4. Each line carries Chinese title, `[news]`
     or `[repo]` tag, URL, source day, 1-sentence Chinese summary.
   - `## Categories` — exactly 4 buckets named **AI**, **chip**, **cloud**,
     **web**, with counts that sum to 10 and match the canonical
     distribution in §4 exactly.
   - `## By Day` — news-day distribution that matches the canonical 2/2/1
     split in §4 exactly.
2. `/tmp_workspace/results/selection_audit.csv` — exactly 10 rows with
   the column set listed in §4.

Completion = both files present, structurally valid, and matching the
canonical answer in §4 to within the strictness in §5.

## 3. Source-Selection and Target-Resolution Rules

Canonical inputs are exactly the two snapshot files above. Anything else
is out of scope; no live network calls expected.

Canonical ranking signal (used by the supervisor when re-deriving the
expected Top 10):

- **News pool (5 picks)** — within each capture day, sort by `pub_date`
  descending. Take **2 from 2026-04-20, 2 from 2026-04-19, 1 from
  2026-04-18**, in that order. This per-day cap keeps the digest
  representative of all three days while still preferring recency.
- **Repo pool (5 picks)** — among items with `captured_on == "2026-04-20"`
  (the latest snapshot), sort by `stars` descending. Take the top 5. The
  star count from the latest capture day is the canonical popularity
  value; older captures of the same repo are not surfaced again.
- Ties within each pool are broken by source-file order.
- The merged Top 10 is news[0..4] then repos[0..4].

## 4. Ground-Truth Snapshot

Structured expected answer at `references/ground_truth.json` (schema c:
ranked list with deterministic tie-break). Key facts:

- `top_count`: 10 (5 news + 5 repos, exact)
- **Expected Top 10 in canonical order**:
  1. `[news]` 中芯国际：3nm GAA 工艺试产成功，明年 H1 量产 — 2026-04-20 22:10 — chip
  2. `[news]` 海光信息：DCU-Z 系列 GPU 流片完成，FP16 算力达 H100 的 90% — 2026-04-20 21:30 — chip
  3. `[news]` 寒武纪：思元 690 训练芯片完成流片，FP8 算力达 H100 的 80% — 2026-04-19 22:30 — chip
  4. `[news]` 亚马逊 AWS Bedrock 中国区正式商用，与中信云合作 — 2026-04-19 22:00 — cloud
  5. `[news]` 华为云盘古大模型 6.0 正式商用，专注科学计算 — 2026-04-18 22:30 — cloud
  6. `[repo]` opendatalab/MinerU — 60591 stars (2026-04-20) — AI
  7. `[repo]` openai/swarm — 21351 stars (2026-04-20) — AI
  8. `[repo]` Skyvern-AI/skyvern — 21287 stars (2026-04-20) — web
  9. `[repo]` emcie-co/parlant — 17987 stars (2026-04-20) — AI
  10. `[repo]` PKU-YuanGroup/Open-Sora-Plan — 12156 stars (2026-04-20) — AI
- **Expected category distribution** (must match exactly):
  - **AI: 4** (items 6, 7, 9, 10)
  - **chip: 3** (items 1, 2, 3)
  - **cloud: 2** (items 4, 5)
  - **web: 1** (item 8)
  - sum: 10
- **Expected news-day distribution** (must match exactly):
  - 2026-04-20: 2 (items 1, 2)
  - 2026-04-19: 2 (items 3, 4)
  - 2026-04-18: 1 (item 5)
- `selection_audit_columns` (in this order):
  `final_rank, source_tag, source_day, title, url, popularity_value,
  category, selection_reason`

## 5. Checkpoint Rubric

Weights sum to 1.00.

| # | Weight | Checkpoint |
|---|--------|------------|
| 1 | 0.08 | `digest.md` exists and `## Top 10` contains exactly 10 items, with `[news]` and `[repo]` tags both present and balanced 5+5 |
| 2 | 0.20 | All 10 Top-10 items match the §4 canonical set by URL or title — strict 10/10. Every expected item must appear; any missing or substituted item zeros this line. |
| 3 | 0.18 | Top-10 ordering matches §4 exactly: 5 news first by per-day-capped recency, then 5 repos by descending latest-day stars (off-by-one swaps lose partial credit) |
| 4 | 0.15 | `## Categories` block has exactly 4 buckets named **AI / chip / cloud / web** with counts **4 / 3 / 2 / 1** matching §4 exactly (any deviation in bucket names or counts loses full credit for this line) |
| 5 | 0.12 | `## By Day` block reports news-day distribution **2026-04-20: 2 / 2026-04-19: 2 / 2026-04-18: 1** exactly, and the 5 selected news items can be verified against this split |
| 6 | 0.10 | All 10 titles rendered in Chinese (≥ 50% CJK characters); English repo descriptions translated into Chinese in the per-line summary, not copied verbatim |
| 7 | 0.10 | `selection_audit.csv` exists with exactly 10 rows and the §4 column set; `popularity_value` is `pub_date` for news rows and the 2026-04-20 stars value for repo rows |
| 8 | 0.07 | `selection_reason` column on each row references the correct ranking signal (per-day recency cap for news, latest-day stars for repos) — generic placeholders lose credit |

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. The following caps target
specific edge failures and override rubric math:

- **Cap 0.30** — neither `digest.md` nor `selection_audit.csv` is
  produced (no deliverables).
- **Cap 0.30** — any credential value declared in `.privacy` (or any
  obvious secret) appears in the user-visible output.
- **Cap 0.70** — the trace shows zero reads of any file under
  `/root/skills/news-snapshot-zh/`, `/root/skills/repo-snapshot-cn/`, or
  `/root/skills/translate/` (skill-usage task with no skill engagement).
- **Cap 0.60** — Top-10 items reference URLs or titles not present in
  either snapshot (fabricated sources).
- **Cap 0.65** — Top-10 covers fewer than 2 of the 3 capture days on the
  news side (day-distribution blowout — collapses to single-day digest).
- **Cap 0.70** — `selection_audit.csv` is missing entirely while
  `digest.md` is present.

Pass requirement: rubric total at or above the threshold in §7, with
checkpoints 1, 2, 4, and 5 each at least half-credited.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90 — accept and stop.
- **Continue** 0.50 – 0.89 — supervisor may request one follow-up to
  repair the lowest-scoring rubric line (typically rubric #3, #5, or #8).
- **Fail** < 0.50 — record `finalStatus=failed`; no further follow-ups.

Prefer `continue` when shortfalls are recoverable. Prefer `fail` on
fabricated sources, credential leakage, total absence of deliverables,
or single-day collapse.

## 8. Hidden Reference Assets

Supervisor-only — never surfaced to the executor or user simulator:

- `references/eval_rule.md` (this file)
- `references/ground_truth.json`

## 9. Dynamic Content Note

Offline task. All three days of snapshots are committed captures and do
not change between hidden capture and run time. No live API calls
expected.
