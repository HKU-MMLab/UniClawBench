# Design notes — task_101_35_en_zh_tech_daily

Internal-only archive of construction history. Not injected into runtime
context, not surfaced to executor or supervisor.

## Score-cap policy origin

Earlier eval_rule revisions used a graded set of caps (0.84 / 0.86 / 0.89)
keyed to individual rubric lines (e.g., missing audit CSV → 0.84, unbalanced
top-10 → 0.86, no read of declared skill files → 0.89). These collapsed to
near-rubric restatements and rewarded model failures with high scores.

The hardened policy keeps caps at ≤ 0.7 and reserves them for genuine edge
failures: zero deliverables, credential leakage, total scope blowout (e.g.,
no skills consulted at all), no audit CSV, fabricated/hallucinated source
items. Per-rubric shortfalls are now expressed only via the rubric weights.

## Skill-evidence rationale

The task is in the skill_usage family; three skills are declared
(`news-snapshot-zh`, `repo-snapshot-cn`, `translate`). The supervisor caps
the run when the trace shows zero engagement with any of the three skill
directories — this is the family-wide convention: a skill_usage run with
no skill-file reads is not a successful skill-usage demonstration.

## Snapshot-fidelity rationale

Both source files are real captures (36kr RSS / hot-list and GitHub search
API, 2026-04-20). The hidden ranking signals — pub_date desc for news,
stars desc for repos — were chosen because they are the only public,
deterministic signals embedded in the snapshots. The rubric does not
penalize alternate defensible orderings as long as they remain consistent
with the snapshot fields.

## Review pass (2026-04-30)

Per review_record.md Task 35: "参考全局要求修改 + 进一步增加数据量(多天数据)
+ 增加明确的排序、数量 checkpoint".

### Source expansion to 3 days

- News: 20 items × 3 days (2026-04-18 / 2026-04-19 / 2026-04-20) = 60 items
- Repos: 15 items × 3 days = 45 items, each repo carries `captured_on` field
  so the supervisor can pick the latest snapshot day's stars deterministically.
- Each item now has `primary_category` ∈ {AI, chip, cloud, web, auto, finance,
  energy, biotech, telecom, media} so the canonical category counts derive
  directly from the snapshot.

### Canonical ranking — strict and deterministic

To satisfy "增加明确的排序、数量 checkpoint" while preserving multi-day
coverage:

- News pool (5 picks): per-day cap of 2/2/1 across 2026-04-20 / 2026-04-19 /
  2026-04-18, within each day sorted by pub_date desc, ties by source order.
- Repo pool (5 picks): among `captured_on == "2026-04-20"`, sorted by stars
  desc, top 5. Older captures of the same repo are not surfaced again.

### Engineered Top-10 outcome

The top items in the snapshots were tuned so the canonical Top 10 lands on
exactly **4 buckets — AI:4 / chip:3 / cloud:2 / web:1** with a **2/2/1
news-day split**. These are the strict checkpoints the eval enforces:

- §5#2 expects all 10 expected items present (10/10 in the canonical set)
- §5#3 expects the exact ordering (off-by-one swaps lose partial credit)
- §5#4 expects exactly **AI:4 / chip:3 / cloud:2 / web:1** (no other
  bucket name or count accepted)
- §5#5 expects exactly **2026-04-20:2 / 2026-04-19:2 / 2026-04-18:1**

### Cap update

Added **Cap 0.65** for news side covering fewer than 2 of 3 capture days
(single-day-collapse failure mode, distinct from "no skill engagement").
Existing caps preserved.

### YAML prompt rewrite

- Skill usage moved into the first paragraph ("Please use the
  news-snapshot-zh helper... repo-snapshot-cn helper... translate skill...").
- Removed parentheses; expressed counts naturally without enumerating
  exact totals (let executor count).
- Added explicit `## By Day` block requirement in the digest so the
  day-distribution checkpoint is visible to the executor, but did not
  enumerate the canonical 2/2/1 split (avoid leaking rubric).

### Rubric weights

§5 weights: 0.08 + 0.20 + 0.18 + 0.15 + 0.12 + 0.10 + 0.10 + 0.07 = 1.00 ✓
