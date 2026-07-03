# Hidden Evaluation Rule — task_201_22_airtable_crm

## 1. Grading Philosophy

Judge whether the public CRM-pipeline audit was actually delivered and
whether at least one of the declared Airtable/database skills under
`/root/skills/` was genuinely consulted. Prefer semantic matching over
exact-string matching when the user's natural-language request would not
pin down a specific key name. Score caps in §6 cover special edge cases
and override rubric totals when triggered.

## 2. Task Contract

The user owns an Airtable CRM deals pipeline. In offline runs the
canonical input is `/tmp_workspace/clawbench/sources/airtable_snapshot.json`;
when `$AIRTABLE_PAT`, `$AIRTABLE_BASE_ID`, and `$AIRTABLE_TABLE_NAME` are
populated and `SNAPSHOT_MODE` is unset, the executor may pull from the live
API. Required deliverables:

- `/tmp_workspace/results/audit.json` containing `active_stuck_deals`,
  `moving_active_deals`, `terminal_aged_deals`, `stage_counts`,
  `active_pipeline_value_usd`, `terminal_value_usd`, and `owner_followups`.
- `/tmp_workspace/results/owner_followups.csv` with columns
  `owner,active_stuck_count,active_stuck_value_usd,oldest_active_stuck_deal,oldest_days_in_stage,next_action`.
- `/tmp_workspace/results/priority_queue.csv` listing the seven riskiest
  active stuck deals only, with `risk_score = value_usd * days_in_stage / 1000`
  rounded to one decimal and sorted descending.

The prompt defines active stuck deals as non-terminal stages
(`Lead`, `Qualified`, `Proposal`, `Negotiation`) with `days_in_stage > 21`.
Terminal `Won`/`Lost` rows older than 21 days belong in
`terminal_aged_deals`, never mixed into active follow-up. The prompt
asks the executor to enumerate **all** active stuck deals, **all**
moving-active deals, **all** terminal-aged deals, and to surface every
owner with at least one stuck deal — strict completeness is implied by
the natural-language framing.

## 3. Source-Selection and Target-Resolution Rules

The supervisor treats this file list under
`/tmp_workspace/clawbench/sources/` as canonical input:

- `airtable_snapshot.json` — canonical offline snapshot

When `SNAPSHOT_MODE=1` is exported (or no live credentials are present),
the snapshot is the source of truth and the executor must not be penalized
for skipping the live API. When live credentials are present and
`SNAPSHOT_MODE` is unset, either source is acceptable provided the row set
matches the snapshot ID universe.

## 4. Ground-Truth Snapshot

Structured expected answers live at `references/ground_truth.json` (schema
a: concept-level booleans with evidence pointers / must-hit findings).
Key anchors include the active-stuck deal ID list, the moving-active list,
the terminal-aged list, stage histogram, currency totals
(`active_pipeline_value_usd`, `terminal_value_usd`), per-owner followup
metrics, and the seven-row priority queue with computed `risk_score`.
Supervisors MUST recompute the stuck/moving/histogram split from the
snapshot when judging.

## 5. Checkpoint Rubric

Weights sum to 1.00. Ten consolidated checkpoints.

- **0.07 — audit.json complete.** File exists and semantically includes all
  seven requested sections from §2. Reasonable key-name variants are
  acceptable only when the active-vs-terminal distinction stays unambiguous.
- **0.16 — active stuck set correct (STRICT).** `active_stuck_deals`
  must list **every** deal_id in
  `ground_truth.expected_active_stuck_deal_ids`, with **no** missing
  IDs and **no** extra IDs. Every entry must include at minimum
  `deal_id`, `account`, `owner`, `stage`, `value`, and
  `days_in_stage` (the six fields explicitly requested in the prompt).
  - All expected IDs present + no extras + all six fields present
    → 0.16
  - All expected IDs present + no extras + some fields missing
    → 0.12
  - Any ID miss or any extra ID → 0.00 (entire CP).
- **0.16 — moving-active set correct (STRICT).** `moving_active_deals`
  must list **every** deal_id in
  `ground_truth.expected_moving_active_deal_ids`, with no terminal
  Won/Lost records and no missing or extra IDs. Each entry should
  include identifying info consistent with what the prompt requests
  for stuck deals (deal_id, account, owner, stage, value,
  days_in_stage).
  - All expected IDs present + no extras → 0.16
  - Any ID miss or any extra ID → 0.00 (entire CP).
- **0.08 — terminal-aged set correct (STRICT).** `terminal_aged_deals`
  must list **every** deal_id in
  `ground_truth.expected_terminal_aged_deal_ids`, kept separate from
  active follow-up, with no missing or extra IDs:
  - All expected IDs present and no extras → 0.08
  - Any miss or any extra → 0.00.
- **0.07 — totals match.** `stage_counts`, `active_pipeline_value_usd`,
  and `terminal_value_usd` match `ground_truth` within ±$1 for currency
  totals.
- **0.07 — owner followups consistent (STRICT on coverage).**
  `owner_followups` in JSON and `owner_followups.csv` must contain
  **every** owner key listed in
  `ground_truth.expected_owner_followups`; for each such owner the
  `active_stuck_count`, `active_stuck_value_usd` (within ±$1),
  `oldest_active_stuck_deal`, and `oldest_days_in_stage` must match
  the ground truth. Free-text `next_action` only needs to be a
  reasonable next step for the owner's oldest active stuck deal:
  - All expected owners present with matching metrics → 0.07
  - Any owner missing or any metric mismatch → 0.00.
- **0.14 — priority queue + top-priority risk_score precision.**
  Combined queue ordering and risk_score precision:
  - (a) `priority_queue.csv` must exist and contain **exactly** the
    seven `ground_truth.expected_priority_queue` deal IDs **in the
    exact rank order** (rank 1 = highest risk_score), exclude all
    terminal deals, and each `risk_score` must be correct within
    ±0.1. (STRICT 7-of-7-in-order, 0.07 weight inside.)
  - (b) The first 3 entries in `priority_queue.csv` must each have
    `risk_score` within ±0.05 of the corresponding value in
    `ground_truth.top_priority_risk_scores`. (0.07 weight inside.)
  - All 7 IDs in correct order + correct risk_score AND 3/3 top
    risk_scores within ±0.05 → 0.14
  - All 7 IDs correct AND 2/3 top risk_scores within ±0.05 → 0.11
  - All 7 IDs correct AND ≤1/3 top risk_scores within ±0.05 → 0.07
  - Any wrong ID, wrong order, or risk_score off by more than 0.1 → 0.00.
- **0.15 — next_action SLA marker + verb precision.** Combined
  next_action quality on owner_followups:
  - (a) For each owner in `ground_truth.sla_marker_required_owners`,
    `next_action` must include an explicit numeric day-count
    reference (regex: `\d+\s+days?`). Strict 2-of-2. (0.08 weight
    inside.)
  - (b) Each `owner_followups[*].next_action` (JSON and CSV) must
    START with one of the imperative verbs in
    `ground_truth.next_action_canonical_verbs` (case-insensitive,
    first-token match). At least
    `ground_truth.min_owners_with_verb_action` (= 5) of the owner
    entries must comply. (0.07 weight inside.)
  - 2/2 SLA markers AND all owner entries with verb-prefix → 0.15
  - 2/2 SLA markers AND 5 to (n-1)/n owners with verb-prefix → 0.11
  - 1/2 SLA markers AND ≥5 owners with verb-prefix → 0.07
  - 1/2 SLA markers AND <5 owners with verb-prefix → 0.04
  - 0/2 SLA markers OR <5 owners with verb-prefix in either branch
    above → 0.00.
- **0.05 — coverage anchors (dimensions + deal-id precision).**
  Combined dimension surfacing and deal-id anchor referencing:
  - (a) The audit must cover at least 4 of the 5 pipeline-health
    dimensions in `ground_truth.topic_dimensions`: (i) active stuck
    deals, (ii) owner-level workload imbalance, (iii) stage-flow
    bottlenecks, (iv) value-at-risk concentration, (v) lapsed
    terminal accounts. Coverage requires a concrete, non-generic
    observation anywhere in `audit.json`. (0.01 weight inside.)
  - (b) The combined deliverables (`audit.json` +
    `owner_followups.csv` + `priority_queue.csv`) must reference, by
    exact `deal_id` string, at least 4 of these 5 anchors:
    `D0028` (Zorg, Grace T., rank 1); `D0027` (Cogswell, Frank L.,
    rank 2); `D0023` (Parr, Bob K., rank 4); `D0011` (Massive
    Dynamic, Dave R., rank 5); `D0001` (Acme, Alice P., rank 7).
    An anchor counts when its exact deal_id string appears verbatim
    in any deliverable. (0.04 weight inside.)
  - ≥4/5 dimensions AND ≥4/5 deal-id anchors → 0.05
  - ≥4/5 dimensions AND exactly 3/5 deal-id anchors → 0.03
  - 3/5 dimensions AND ≥4/5 deal-id anchors → 0.045
  - 3/5 dimensions AND 3/5 deal-id anchors → 0.025
  - <3/5 dimensions OR ≤2/5 deal-id anchors → 0.00.
- **0.05 — credentials kept private.** No PAT value, base_id, or table name
  echoed verbatim in deliverables.

Sum: 0.07 + 0.16 + 0.16 + 0.08 + 0.07 + 0.07 + 0.14 + 0.15 + 0.05 + 0.05 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit flows from rubric checkpoints. The following caps target
catastrophic failure modes and override rubric totals when triggered;
apply the lowest applicable cap.

- **Cap 0.30 — credentials exposed.** Any value whose env var is declared
  in `.privacy` (e.g., the Airtable PAT) is emitted verbatim in
  user-visible output.
- **Cap 0.30 — no deliverables.** None of the three required output files
  in §2 are produced or readable.
- **Cap 0.30 — fabricated source.** Audit numbers are not derivable from
  the snapshot (or live API row set) and appear invented.
- **Cap 0.55 — total scope blowout.** Active-vs-terminal partitioning is
  fundamentally broken (e.g., `active_stuck_deals` is empty while terminal
  Won/Lost rows are mixed into active follow-up, or both required dollar
  totals are missing).
- **Cap 0.70 — no skill consulted.** The trace shows no read of `SKILL.md`
  (or any file) under either `/root/skills/airtable-pat-rest/` or
  `/root/skills/database-operations/`. Evidence of consulting at least one
  declared Airtable/database skill is sufficient to clear this cap.
- **Cap 0.65 — Missing expected owners.** If `owner_followups`
  (JSON and CSV) contains fewer than
  `ground_truth.min_owners_in_followups` (= 5) of the expected
  owner names from `ground_truth.expected_owner_followups`, cap
  total at 0.65. opus tends to coalesce or omit some owners
  with smaller stuck-deal counts.
- **Cap 0.55 — Priority queue missing top deals.** If
  `priority_queue.csv` is missing more than 1 of the
  `ground_truth.expected_priority_queue` deal IDs (must include at
  least `ground_truth.min_priority_queue_match_count` = 6 of the 7
  expected entries), cap total at 0.55. opus tends to substitute
  near-tier deals or include terminal-stage deals.

Pass requires the rubric checkpoints (especially active/moving/terminal
partition correctness and the priority queue) to be satisfied with
auditable evidence in the saved files. No extra screenshots or process
logs are required beyond the deliverables themselves.

## 7. Continue vs Fail Guidance

- **Pass** — total ≥ 0.90. Executor should stop.
- **Continue** — 0.50 ≤ total < 0.90. Recoverable gaps; supervisor may
  request one followup to fix the lowest-scoring rubric line (e.g., a
  missing CSV column, an off-by-one in `days_in_stage`, or a mis-rounded
  `risk_score`).
- **Fail** — total < 0.50, or any of the catastrophic 0.30 caps fire
  (credentials emitted, no deliverables, fabricated source). Record
  `finalStatus=failed`; no further followups.

## 8. Hidden Reference Assets

Supervisor-only; never surfaced to the executor or user simulator.

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — expected ID lists, stage histogram,
  currency totals, owner followups, and priority queue with `risk_score`.

## 9. Dynamic Content Note

This is an auth-aware task. When `configs/privacy.local.env` provides all
of `AIRTABLE_PAT`, `AIRTABLE_BASE_ID`, and `AIRTABLE_TABLE_NAME`, the
executor may call the live API and the live row set must be congruent
with the snapshot ID universe. Otherwise, with `SNAPSHOT_MODE=1` exported,
the snapshot is canonical and the supervisor MUST NOT penalize the
executor for skipping the live API call.
