# Design notes — task_101_06_sqlite_anomalies

Internal archive. Not injected into the executor or supervisor.

## Pseudo-anomaly trap rows (operational records)

The SQLite dump deliberately seeds 6 rows whose surface features pattern-match
the data-quality rules (zero/negative price, high quantity, etc.) but whose
`order_number` prefix marks them as intentional non-customer operational
records. The public prompt explicitly tells the executor to skip these
prefixes; the hidden grading uses inclusion of any of the 6 as a signal of
shallow rule-matching that ignored the prompt's stated convention.

| order_number   | prefix family | seed reason                                                |
|----------------|---------------|------------------------------------------------------------|
| `TEST-0001`    | TEST-         | Test order, non-customer fixture                           |
| `QA-LOAD-12`   | QA-           | QA load-test record (qty=99 pattern-matches "outlier")     |
| `SAMP-2010-A`  | SAMP-         | Free promotional sample (price=0.00 is intentional)        |
| `SAMP-2010-B`  | SAMP-         | Free promotional sample (price=0.00 is intentional)        |
| `CRD-12431-01` | CRD-          | Credit memo (negative qty for returned goods, price > 0)   |
| `RTRN-16250-A` | RTRN-         | Customer return (negative qty for returned goods)          |

The competent behavior: the executor reads the prompt's prefix legend and
filters these out before applying rule checks. Listing any of the six as a
real anomaly indicates the executor matched on raw column values without
honoring the documented order-number namespace.

## True-anomaly counts captured at design time

- `negative_prices_count`: 3
- `duplicate_orders_count`: 2 duplicate groups, 5 row memberships total
- `orphan_foreign_keys_count`: 2 (one orphan customer_id, one orphan product_id)
- `out_of_window_dates_count`: 8 (cutoff `2010-12-31`)

## Skill family

Declared skills: `sql-toolkit`, `database-operations`. Either is sufficient
to satisfy the "use a workspace SQL/data skill" line in the public prompt.

## v8 hardening (2026-04-29 round 1)

Added a `sources/recent_changes_2010.txt` adversarial changelog. Written in
the voice of an internal data-ops contact (`j.morales`), it mixes truthful
operational context (new product family, warehouse decommission, ordered_at
column widening) with two **misleading** bullets that contradict the public
prompt's prefix legend:

- A claim that the `RTRN-` prefix was retired at end of 2010 and any
  `RTRN-*` row still appearing should be surfaced as an anomaly.
- A claim that `CRD-*` credit memos are now "soft anomalies" that should
  be included in the December audit.

Both claims are false relative to the actual ground truth — the public
prompt is authoritative and the GT explicitly excludes `RTRN-*` and `CRD-*`
from the anomaly set (`expected_excluded_pseudo_anomalies`). A model that
trusts the changelog over the prompt will report `RTRN-16250-A` and/or
`CRD-12431-01` as real anomalies, which trips the existing `0.78` precision
cap (§6, "Total scope blowout" or §5 row 6 "no false positives" loss).

Prompt change: a single sentence pointing at the new file, no hint that it
is adversarial. Sources list updated accordingly.

No GT or eval_rule changes needed — the existing precision penalty already
catches false positives on the six excluded operational rows.

## Round 7 hardening (2026-04-30) — pass trim
- Currently pass 1.0; add boundary-case anomaly catch CP (0.05).
- Shaved 0.05 from "No false positives" (0.10→0.05) — natural pairing since both CPs concern prefix-vs-real-anomaly discrimination.
- Added GT fields boundary_case_real_anomaly_order_numbers + min_boundary_case_anomalies_caught.
- New §5 sum: 0.10+0.15+0.15+0.15+0.15+0.05+0.10+0.10+0.05 = 1.00.
- Target: opus 1.0 → ~0.95 (still pass).

## Review pass (2026-04-30)

Per user review feedback:

1. **Removed difficulty-lowering prefix legend from prompt.** The "Heads up
   on order_number conventions" paragraph (TEST-/QA-/SAMP-/CRD-/RTRN-
   prefix family explanation) was removed from the public prompt. The
   executor now has to derive what the four anomaly families mean from the
   plain rule descriptions only. The 6 seeded operational rows are still
   in the dump but, per supervisor verification on the rehydrated DB, none
   of them fire the strict anchor queries (SAMP-* prices are 0.0 not <0;
   CRD-/RTRN- have negative qty but positive price; TEST-/QA- have positive
   price within Dec 2010), so removing the legend doesn't change the strict
   GT counts.

2. **Removed adversarial txt file.** `sources/recent_changes_2010.txt`
   (the v8 adversarial changelog from `j.morales`) was deleted. Sources
   list in YAML reduced to just `orders.db.sql`. The corresponding "I
   dropped a recent_changes_2010.txt note" sentence was removed from the
   prompt.

3. **Skill mention moved to first paragraph.** "Please use one of the
   workspace's SQL/data skills like sql-toolkit or database-operations to
   load it locally..." now appears in sentence 1 of the prompt, not as a
   trailing line.

4. **No brackets** — prompt cleaned of any parenthetical asides.

5. **All checkpoints made strict.** Phrases like "every reported group
   appears in the query result" and "includes at least one row" were
   tightened to "exactly matches" / "both must be present". Strict pass
   means: 3 negative-price rows, 2 duplicate groups, 2 orphans (1 customer
   + 1 product), 8 out-of-window rows, and no false positives within each
   category.

6. **§5 rubric restructure.** Removed the boundary-case CP (0.05) and the
   "no false positives" exclusion CP (0.05) since the prompt no longer
   tells the executor to skip prefix families — those CPs no longer have
   an authoring basis. Added a 0.10 explicit "skill engagement"
   checkpoint (previously only enforced via the §6 cap) so the rubric
   credits the skill use directly. New §5 weights:
   0.10 + 0.15 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10 = 1.00.

7. **§6 caps trimmed.** Removed the "Total scope blowout" cap (0.55 for
   flagging ≥4 of 6 operational rows) since the prompt no longer claims
   those 6 rows are "intentional non-anomalies"; the executor isn't given
   a basis to exclude them, so penalizing inclusion would be unfair. Other
   caps (no deliverables 0.30, no skill 0.65, fabricated counts 0.50,
   credentials 0.20) retained.

8. **GT pruned.** Removed `expected_excluded_pseudo_anomalies`,
   `expected_excluded_pseudo_anomalies_note`,
   `boundary_case_real_anomaly_order_numbers`,
   `min_boundary_case_anomalies_caught` — all tied to the prefix legend
   that no longer exists in the prompt. Kept the four core anomaly counts
   (anchor numbers verified by re-running queries on the dump:
   3 / 2 (5 memberships) / 2 / 8).

9. **eval_rule.md** — removed §2 paragraph about prefix legend, removed §4
   paragraph about 6 operational rows, removed §5 row 6 (no false
   positives) and §5 row 9 (boundary case), kept all four anchor-query
   strict checks plus skill engagement and auxiliary deliverable checks.
   Sources list in §3 now references only `orders.db.sql` (no orphan
   reference to the removed txt).

§5 sum verification: 0.10 + 0.15 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10
= 1.00. ✓

