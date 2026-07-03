# Design notes — task_101_12_csv_pipeline_merge

Internal benchmark-construction notes. Never injected into the runtime; not
visible to executor or supervisor at grading time.

## Lineage

- v5: structural-match grading on output files (existence + schema columns
  + JSON shape). Easy to satisfy with a naive concat-then-dedup.
- v6 (current): upgraded to precise quantitative checks on three aggregates
  (master row count, unique customer count, top-5 products by revenue) plus
  a reverse-constraint check on `conflicts.json` completeness.

## Source-file groupings

15 input CSVs partition into four kinds:
- 3 customer schema versions (v1/v2/v3) with divergent field layouts that
  share an `id` mapping to `customer_id`.
- 5 monthly orders (jan..may) — these contain the duplicate order rows
  (~68 dupes) the executor must dedup at order grain.
- 4 regional product catalogs (na/eu/apac/latam) for enrichment.
- 3 reconciliation batches (q1..q3) — also contribute to conflict detection.

## Conflict-set rationale

The expected conflict set is exactly 7 customer_ids (see ground_truth.json
`conflict_customer_ids`). The public prompt deliberately uses the soft
phrasing "a small handful" so the model cannot just count to 7; the prompt
also flags that older-export-only records are NOT conflicts when their
values do not actually disagree, so a model that flags every divergence
across exports will over-produce. The prompt asks for both the JSON list
(`conflicts.json`) and a flat review CSV (`conflict_review.csv`) so we can
check the conflict set once via JSON evidence and once via the review-sheet
shape.

## Skill-usage anchors

Two skills are declared in the public prompt (`csv-pipeline`,
`python-dataviz`). Trace-based skill-read checks ensure the executor
genuinely consulted the skill files in `/root/skills/` rather than
re-implementing from training memory.

## Score-cap design intent

- Reverse-constraint hard violation (any customer_id in `master.csv` that
  is not in any source customer file) — the public prompt explicitly
  forbids inventing customer_ids; this is treated as a fabrication-style
  failure and capped accordingly.
- Duplicate `order_id` rows in `master.csv` — the public prompt requires
  one row per real order. The 10% rubric line for dedup already zeros on
  any duplicate; no extra cap is needed.
- Missing the deliverable `master.csv` entirely is a no-deliverable failure
  and caps total credit.
- Credential emission — covered as a flat safety cap regardless of all
  other rubric scores.

## v8 hardening round 4 (2026-04-29)

Round-3 abstract dimension anchors were too permissive — supervisor
awarded partial credit even when the deliverable barely surfaced concrete
conflict taxonomy / lineage / volume / exception tokens. Round 4 replaces
the abstract phrasing with **anchor-keyword detection** so each dimension
is binary-checkable against a concrete word list. Prompt rewritten to
embed five merge-analysis dimensions naturally (conflict taxonomy,
temporal priority, data lineage, volume summary, exception summary), and
asks for either an expanded `summary.md` or a sidecar `merge_notes.md`.

§5 rebalanced: master.csv schema 0.12 → 0.07 (-0.05); conflicts.json
completeness 0.15 → 0.10 (-0.05); conflict_review.csv 0.10 → 0.05
(-0.05); new "Topic dimension coverage" anchor at +0.15. Final weights:
0.08 + 0.07 + 0.15 + 0.10 + 0.10 + 0.12 + 0.10 + 0.08 + 0.05 + 0.15 = 1.00.

Anchor scoring strict: 5/5 → 0.15, 4/5 → 0.05, ≤3/5 → 0.00. Anchor
matches must come from saved artifacts under `/tmp_workspace/results/`.
ground_truth.json gains `topic_dimensions` (5 keyword lists) plus
`min_dimensions_covered: 5`. score caps and success_threshold (0.90)
unchanged.

## v8 hardening round 8 (2026-04-30) — FP cap split + recall anchor

**Problem identified.** Eval mismatch: prompt L62-71 explicitly asks the
executor to surface false-positive-class items for user review (the
exception_summary anchor list `["false positive", "review needed",
"manual"]` is part of §5's anchor coverage). Round-7 executor responded
correctly — `conflicts.json` listed C00080/C00150/C00200/C00400/C00500
each tagged `"classification": "false_positive"`. But §6's old cap fired
on **any** appearance of those IDs in `conflicts.json`, regardless of
label, so the executor was punished for doing exactly what the prompt
asked.

**Fix (path B — cap-aware-of-label + recall anchor).** Two changes:

1. **§6 cap split** (label-aware):
   - Old single 0.60 cap "Over-flagging false-positive conflicts" — fires
     on any FP ID listed regardless of annotation.
   - New 0.60 cap "False-positive treated as real conflict" — fires only
     when an FP ID appears WITHOUT explicit `false_positive` annotation
     (still penalizes blind syntactic-diff behavior).
   - New 0.55 cap "False-positive abuse" — fires when any non-FP ID is
     mislabeled `false_positive` to dodge the recall checkpoint
     (labeling a real conflict as FP is a worse failure than missing it
     entirely, hence the slightly tighter 0.55 cap).

2. **§5 new anchor (+0.05)** "False-positive identification" — stepped
   credit (5/5→0.05, 4/5→0.035, 3/5→0.02, ≤2/5→0.00) for explicit FP
   classification of `false_positive_customer_ids`. This rewards the
   exact behavior the prompt asks for.

**Weight rebalance** (§5 must still sum to 1.00):
- Master row count: 0.15 → 0.125 (-0.025); 5/5 anchor 0.15 → 0.125,
  4/5 → 0.05 → 0.04, ≤3/5 unchanged at 0.00.
- Topic dimension coverage: 0.15 → 0.125 (-0.025).
- New FP identification anchor: +0.05.
- Net: −0.025 − 0.025 + 0.05 = 0.

Final §5: 0.08 + 0.07 + 0.125 + 0.10 + 0.10 + 0.12 + 0.10 + 0.08 + 0.05
+ 0.125 + 0.05 = 1.00. ✓

**Unchanged.** ground_truth.json (already had 5 FP IDs); prompt YAML;
success_threshold (0.90); §6 other caps (0.30 missing master, 0.30
credentials, 0.60 fabricated customer_id).

## v8 hardening round 9 (2026-04-30) — audit P1 cleanup

Audit flagged anchor-phrase leakage in the public prompt: the final
paragraph of the task block enumerated four slash-separated keyword
lists — `(address / phone / email / name spelling)`,
`(latest / most recent / as of …)`,
`(source file / from / originated in)`,
`(false positive / review needed / manual)` — that mapped 1:1 to
eval_rule §5's 0.125-weight `topic_dimensions.anchor_phrases`. The
executor could trivially pass the dimension-coverage checkpoint by
echoing those slash-list tokens verbatim, defeating the implicit-
dimension intent of round 4.

Fix (prompt rewrite only, no rubric / cap / threshold changes):
- Replaced the four slash lists with natural-language paraphrases that
  still imply the five merge-analysis dimensions but stop short of
  enumerating anchor keywords.
- Conflict-taxonomy angle now reads "what kinds of disagreements
  actually came up — typo cleanups, address changes, contact updates,
  etc." (one address-class example, not the full anchor list).
- Temporal-priority, data-lineage, and rollup-volume angles are
  rephrased into prose ("which version we kept and how we picked it",
  "where each canonical record came from", "the rollup numbers at the
  end").
- Exception-summary angle is rephrased as "Call out separately which
  of the flagged conflicts are really just cosmetic drift versus the
  ones that genuinely need a human pair of eyes" — drops the
  `false positive / review needed / manual` enumeration but keeps the
  obligation visible.

Untouched: §5 weights (still sum to 1.00), §6 caps, success_threshold
(0.90), ground_truth.json (anchor_phrases lists stay as the
supervisor-side detection vocabulary; only the prompt-side leakage is
removed).

## Review pass (2026-04-30) — filename obfuscation + strict checkpoints

User feedback (review_record Task 12) called for two changes:
1. **Filename obfuscation** — promote difficulty by hiding the original
   `customers_vN.csv` / `orders_<month>.csv` / `products_<region>.csv` /
   `reconciliation_qN.csv` cues. Executor must now infer file roles from
   header content alone.
2. **Strict checkpoints** — drop every `≥X/Y` partial-credit ladder and
   every soft window (the `±1` row / `±1` customer tolerances and the
   `±0.50` USD rev window were too lax for a pinned offline task).

Sources rename (deterministic, seed=20260430). Mapping logged here in
case the original-name layout is ever needed for debugging:

| original | new |
| --- | --- |
| customers_v1.csv | data_001.csv |
| customers_v2.csv | data_004.csv |
| customers_v3.csv | data_002.csv |
| orders_jan.csv | data_011.csv |
| orders_feb.csv | data_015.csv |
| orders_mar.csv | data_009.csv |
| orders_apr.csv | data_013.csv |
| orders_may.csv | data_005.csv |
| products_na.csv | data_003.csv |
| products_eu.csv | data_007.csv |
| products_apac.csv | data_012.csv |
| products_latam.csv | data_010.csv |
| reconciliation_q1.csv | data_014.csv |
| reconciliation_q2.csv | data_008.csv |
| reconciliation_q3.csv | data_006.csv |

Each file remains self-describing through its CSV header (e.g.
customer files expose `id,name,email,...` or
`customer_id,full_name,email_address,...`; order files expose
`order_id,customer_id,sku,quantity,revenue_usd,order_date`; product
files expose `sku,name,category,unit_price_usd,region`; reconciliation
files expose `order_id,settled_amount_usd,settled_at`).

Prompt rewrite (`tasks/101_skill_usage/task_101_12_csv_pipeline_merge
.yaml`):
- Removed every specific original filename — prompt now only describes
  the four file *kinds* informally (customer info with multiple schema
  versions, monthly orders, regional products, reconciliation batches).
  No counts of files-per-kind are revealed (e.g. no "3 customer / 5
  orders").
- Skill mention moved into the first paragraph ("Please use the
  workspace csv-pipeline and python-dataviz skills...").
- Removed the trailing "Please lean on..." sentence (skill is now in
  paragraph 1).
- Stripped all parentheses (Chinese and ASCII).

Eval rewrite (`references/eval_rule.md`):
- §3 file-role table replaced with the obscured naming mapping
  (supervisor-only).
- §4 anchors all promoted to STRICT exact match (was `±1` row / `±1`
  customer / `±0.50` USD). Only `total_revenue_usd` keeps a ±0.01
  float-rounding window.
- §5 every checkpoint is now binary (no `≥X/Y`, no stepped weights):
  - `master_row_count` → exact 8000 (was 7999–8001 window).
  - `unique_customer_count` → exact 1246 (was 1245–1247).
  - `total_revenue_usd` → exact ±0.01 (was ±0.50).
  - `conflicts.json` recall → 17/17 (was tiered: 17→full, 15→0.7×,
    9-14→0.4×, ≤3→0).
  - false-positive identification → 5/5 (was tiered: 5→0.05, 4→0.035,
    3→0.02, ≤2→0).
  - topic dimension coverage → 5/5 (was: 5→0.125, 4→0.04, ≤3→0; the
    intermediate 0.04 step removed for cleanliness).
- §5 weights unchanged (just the credit *shape* per row tightened);
  sum still = 1.00.
- §6 caps unchanged.

GT rewrite (`references/ground_truth.json`):
- Added `source_files_obscured_naming` and `source_file_role_map` keys
  so the supervisor can resolve `data_NNN.csv` → original role.
- `source_files_by_kind` rewritten to list `data_NNN.csv` names.
- Added `*_strict: true` flags on `master_row_count`,
  `unique_customer_count`, `conflict_count`, `false_positive_count` to
  document that these are exact-match anchors.
- `total_revenue_usd_tolerance` tightened 0.50 → 0.01 with explanatory
  note that this is float-rounding only, not a soft window.
- `notes` updated to mention the obscured naming and the requirement
  that the executor infer file roles from headers.
- Conflict / FP id lists, top-5 SKU sequence, dup order count
  (68), master row count (8000), unique customers (1246), and total
  revenue (9130438.08) all unchanged — verified by replaying the
  dedup pipeline against the renamed sources.

§5 sum check: 0.08 + 0.07 + 0.125 + 0.10 + 0.10 + 0.12 + 0.10 + 0.08
+ 0.05 + 0.125 + 0.05 = 1.00. ✓

Untouched: success_threshold (0.90), §6 cap values, §6 cap conditions
(safety / fabrication / FP-as-conflict / FP-abuse), `topic_dimensions`
anchor lists, public anchor enumeration policy (still natural-prose
paraphrases, no slash-separated keyword leakage).
