# design notes — task_101_03_access_log_regex (archive)

This file is private to the meta directory and is never injected into either the
executor or the supervisor runtime. It captures version-design context that
should not appear in the hidden eval rule.

## Hardening history

- Earlier rubric drafts allowed the model to coast to high scores on
  near-right-but-not-exact numerics (parseable count, malformed line count,
  peak-hour formatting, per-status counts, top suspicious IPs).
- The current rubric tightens tolerance bands across those five dimensions to
  cut high-end ceiling on partially-correct outputs.
- A peak-to-min error-rate ratio line was considered and removed because the
  public prompt does not request that derived metric — grading on it would
  introduce a prompt-rubric separation.
- The injected scanner burst (postmortem-style 4xx/5xx lines) was added on
  top of the NASA-HTTP + ClarkNet blend to give status_distribution and
  suspicious_ips real signal beyond pure noise. Status codes 499 and 503
  exist in GT only because of this injected layer.
- Status code 508 was deliberately kept absent from the corpus so that
  fabricated rows can be detected.

## Corpus regeneration

- Seed: 20260425
- The committed `access.log` fixture is deterministic from this seed.
- Latest hardening pass modified ONLY the rubric and ground_truth fields;
  the access.log payload is unchanged from the prior revision.

## Why these specific tolerance bands

- `parseable_count_full=3, partial=10, half=25` — the parser only meets
  full credit if it nails the boundary cases for malformed lines
  (truncated timestamps, "-" methods, %00 / ..\\ smuggling probes).
- `malformed_line_count_full=0` — exact match required for full credit
  because GT=51 is a small, audit-able count; partial=2 acknowledges
  one or two boundary calls; half=4 is the last credit band.
- `status_breakdown_count_pct=0.02` — ±2% on per-key counts pushes the
  model to actually parse status codes correctly rather than approximate.
- `suspicious_ips_top10_min_overlap=9, jaccard_min=0.85` — the injected
  scanner burst guarantees a stable top-10; allowing one swap covers
  legitimate sort-tie cases without rewarding sloppy aggregation.

## v8 hardening round 2 (2026-04-29)

- Round-1 measurements showed opus-4.6 capping at 1.00 on this task. The
  fix targets implicit multi-part output: the task prompt now also asks
  for a companion `report.md` written in natural prose alongside
  `summary.json`. The prompt purposely does not enumerate the dimensions
  ("traffic trends, status mix, suspicious IPs, URL hotspots, anomaly
  timeline") — they have to be inferred from a casual user request.
- New §5.8 anchor at weight 0.12 checks that ≥4 of 5 hidden topic
  dimensions are covered in the narrative. The five dimension keys live
  in `ground_truth.topic_dimensions` (`traffic_volume_trends`,
  `status_code_distribution`, `suspicious_ip_behaviors`,
  `url_hotspot_patterns`, `anomaly_timeline`) with
  `min_dimensions_covered=4`.
- Rebalance to keep totals at 1.00: §5.4 10→6 (-4), §5.5 15→11 (-4),
  §5.7 15→11 (-4); inner thresholds reduced proportionally so each tier
  remains internally coherent. §5.8 adds 12 → final total 5+20+15+6+11
  +20+11+12 = 100.
- Score cap numbers in §6 untouched; success_threshold in YAML untouched.
- The added narrative requirement means a model that nails the JSON but
  drops the narrative loses 12 percentage points outright; a model that
  writes a narrative that only repeats `total_requests` without the four
  other lenses earns at most 3% on §5.8.

## v8 hardening round 6 (2026-04-29)

- Round-5 measurements show opus-4.6 still around 0.94 on this task. The
  R5 retighten pattern that worked best elsewhere ("multi-part + a second
  entity-precision anchor") is replicated here with a status-code
  precision lens.
- New §5.9 anchor at weight 0.08 checks that the companion `report.md`
  cites at least 4 of 5 specific status codes
  (`status_precision_codes` = `[499, 503, 502, 504, 408]`) with counts
  within ±2% of GT (or explicit zero for the absent codes 502/504/408).
- The five-code set was chosen to mix two postmortem codes that exist
  in the corpus (`499->236, 503->171`) with three plausible-looking
  network/server-failure codes that are absent (`502, 504, 408`). The
  executor cannot bluff — they have to actually look at the
  distribution and report the absences explicitly.
- Rebalance to keep the rubric total at exactly 1.00:
  §5.2 20→16 (-4) and §5.6 20→16 (-4) are the two heaviest checkpoints
  and donate 4 percentage points each. §5.9 picks up 8. Inner tier
  thresholds in §5.2 and §5.6 are scaled down so each tier stays
  internally coherent (§5.2: 12→10, 6→5; §5.6: 11→9, 5→4).
- Score caps in §6 unchanged. success_threshold in YAML unchanged.
- GT additions: `status_precision_codes`, `status_precision_counts`,
  `min_status_codes_cited`.

## Review pass (2026-04-30)

User review feedback on `task_101_03_access_log_regex` triggered four
prompt-side changes plus matching eval/GT updates.

Prompt (`task` field in YAML) changes:
- Skill mention "请用工作区里某个 log-analysis skill" moved to the very
  first paragraph, blended into the natural request voice ("Please use
  one of the workspace's log-analysis skills to chew through this for
  me, I don't want to hand-roll regex again."). Was previously a
  detached sentence at the bottom of the prompt.
- `suspicious_ips` threshold dropped from "≥50 4xx hits" to "at least
  10 4xx hits" — increases candidate set from 12 IPs to 21 IPs and
  exposes a long tail with several legitimate user agents (e.g.
  `slc12.xmission.com`, `clark.net`, `piweba4y.prodigy.com`) mixed in
  with the synthesized scanner bursts. Forces the model to actually
  walk the full set rather than coasting on the obvious top-five.
- `top_urls` ranking expanded from top-20 to top-50. Tail entries
  include catalog GIFs, icon paths, and `/htbin/cdt_main.pl` style
  CGI handlers, which tests that the model preserves count-desc and
  path-asc tie-breaks deeper into the distribution.
- The anomaly-timing guidance was rewritten to explicitly require both
  a precise hour bucket AND a precise 4xx+5xx error count, both pulled
  from `summary.json` so the prose ties out with the structured data.
  Was previously vague ("roughly when things start looking off").

Eval rule (`references/eval_rule.md`) changes:
- §2 Task Contract updated: top_urls "top 50" (was 20), suspicious_ips
  "≥10 4xx" (was ≥50). Added contract sentence that `report.md` must
  cite the exact peak hour bucket and exact error count.
- §4 Ground-Truth Snapshot reflects 50-entry `top_urls` and the new
  `anomaly_time_anchor` field plus the `>= 10 4xx hits` extended
  `suspicious_ips_all` list.
- §5.4 (Top URLs identity and ordering): rebuilt around 50 entries
  with new tier thresholds (50 for full, first 30 for partial, ≥40
  of 50 paths for quarter, <40 → 0). Weight unchanged at 6%.
- §5.6 weight 16 → 12. Inner penalty thresholds shrunk
  proportionally (partial 9 → 7, sum-deduction 4 → 3 percentage
  points). Released 4 percentage points to fund the new §5.10.
- §5.7 (Suspicious IPs) made strict on the top-10 sub-line: replaced
  partial-credit ladder (overlap ≥9 + Jaccard fallback) with strict
  "all 10 IPs match exactly" all-or-nothing scoring on the 4-point
  sub-weight. Top-5 ordered ladder retained because it exercises a
  different precision question (ordering, not membership). Added a
  per-entry penalty for spurious IPs with `fourxx_count < 10` to
  enforce the new ≥10 threshold.
- NEW §5.10 (4%) "Anomaly time anchor precision" — strict
  all-or-nothing checkpoint: report.md must cite both the hour bucket
  ("01/Jul/1995 04" or ISO equivalent) AND the exact 4xx+5xx error
  count (417, ±2) within the same paragraph. Missing either → 0%.
  This is the matching eval anchor for the rewritten anomaly-timing
  guidance in the prompt.
- §5 weight inventory: 5+16+15+6+11+12+11+12+8+4 = 100. Sum verified.
- §6 score caps untouched. success_threshold in YAML untouched at 0.90.

Ground truth (`references/ground_truth.json`) changes:
- `schema_notes` updated to mention the 10-threshold and anomaly anchor.
- `top_urls` re-derived as full top-50 (length 50 confirmed). Last
  entry: `/software/winvn/winvn.html` count 176; rank 51 sat at 174
  so no tie ambiguity at the boundary.
- `suspicious_ips_all` extended from 12 entries (≥50) to 21 entries
  (≥10) — re-derived directly from the deterministic `access.log`
  payload. Top-10 list and top-5 list unchanged because the dominant
  scanner IPs still rank at the top.
- NEW field `anomaly_time_anchor` with `hour_bucket`, `hour_bucket_iso`,
  `error_count` (417), `total_requests_in_bucket` (1881), `error_rate`,
  and a notes string. Used by §5.10.
- NEW tolerance band `anomaly_error_count_abs` (= 2) for the §5.10
  count tolerance.
- All other GT fields unchanged. `access.log` payload unchanged
  (same seed=20260425, builder=`build_access_log_v7.py`).
