# Design notes — task_101_16_trello_triage

This file is archive-only. It is never injected into the executor or supervisor
context. Use it to record version-design intent and historical rationale that
should not appear in `references/eval_rule.md`.

## History of cap calibration
- Earlier rubric drafts used score caps in the 0.78 / 0.86 / 0.88 / 0.89
  band (e.g. for missing workbook, missing formulas, missing skill reads).
  These were re-cast as ordinary checkpoint deductions or removed because
  they re-stated the rubric rather than gating extreme failure modes.
- Current eval_rule keeps a small set of caps strictly ≤ 0.7, each tied to a
  genuine SPECIAL edge case (no deliverables, total scope blowout, fabricated
  sources, credential leak).

## Skill-read evidence
- The original v3-era policy required a trace read of `/root/skills/trello/`
  and `/root/skills/summarize-pro/` to award full credit. That intent is now
  expressed via the rubric's "skills genuinely used" checkpoint, scored on
  observable evidence in the deliverables (helper-style invocation pattern,
  summary phrasing, etc.) rather than a meta-level trace audit.

## SNAPSHOT_MODE branching
- `SNAPSHOT_MODE=1`: deterministic populator emits
  `trello_snapshot.json`; ground truth and snapshot match bit-for-bit.
- `SNAPSHOT_MODE=0`: snapshot file is intentionally absent; executor must
  hit the live Trello REST API (`TRELLO_API_KEY` / `TRELLO_API_TOKEN`
  against `TRELLO_BOARD_ID`). Card IDs on the live board match the snapshot
  because both are produced by the same populator run.

## Out-of-scope inputs
- Anything outside `/tmp_workspace/clawbench/sources/` (or the live Trello
  board in SNAPSHOT_MODE=0) is out-of-scope and must not expand the bucket
  taxonomy or the work-order list.

## v8 hardening round 8 (2026-04-30) — split work_order vs unblockers

The prior `top_work_order` mixed 4 urgent (actionable) cards in ranks 1-4
with 4 blocked cards in ranks 5-8. The public prompt asked for "8 cards I
should deal with first today, sorted by urgency, priority, client impact,
and blocker status" — which a reasonable executor reads as "actionable
first, blocked last (or excluded)". Models that put actionable before
blocked were penalised by the rubric, even though the read was sound.

Path B fix: split into two independent ranked lists.

- `top_work_order` (8 cards) — strictly actionable: every entry has
  `bucket` ∈ {urgent, routine}, never `blocked`/`done`. Ranks 1-4 stay
  the same (the urgent head); ranks 5-8 fill from the highest-priority
  routine cards (P2/P3 with imminent due dates):
  - rank 5: `69e52b3098b9ab154defa262` — Refactor billing service error
    handling (P2 routine, due 2026-05-05).
  - rank 6: `69e52b2e55feeae97a4dd566` — Schedule 1:1s with reports for
    next week (P3 routine, due 2026-04-30 = same day as `generated_at`).
  - rank 7: `69e52b3252b2beefd69e4ddd` — Review engineering hiring
    pipeline (P3 routine, due 2026-05-03).
  - rank 8: `69e52b2d69de0ad09ca1373f` — Draft Q3 OKR proposal (P3
    routine, due 2026-05-05).
- `expected_unblockers` (4 cards) — every blocked card with a
  `chase_action` template (who to email, what ticket to bump, what
  decision is needed). Ranked AWS quota → DPA legal → vendor pricing
  → Kai nav design (P1 internal/legal first, then P2 client-facing,
  then P2 internal design).

Rubric weight rebalance — total stays = 1.00:
- 0.18 → 0.155 (Bucket accuracy, −0.025)
- 0.21 → 0.185 (Workbook deliverable, −0.025)
- new 0.05 (Unblockers identification + chase action, +0.05)
- 0.16 (Top work order quality) and other lines unchanged.

Top work order checkpoint also tightened: any blocked card appearing
in `top_work_order` caps the line at half credit, since the prompt now
explicitly says actionable-only.

## Round 1 hardening (2026-04-30)
- Added top_4_urgent_canonical_ids + adversarial_urgent_card_names GT fields.
- Added §5 CP "Top-4 urgent ordering precision" 0.06 (4/4 strict by id+bucket).
- Added §5 CP "Adversarial-urgent bucket precision" 0.05 (SOC2 + integration tests must be urgent).
- Shaved 0.11 from existing weights: Bucket accuracy 0.155→0.095 (−0.06), Workbook deliverable 0.185→0.135 (−0.05).
- Target: opus 0.77 → ~0.65 (loses 0.06 if mislabels + 0.05 if SOC2/integration tests not urgent).

## Round 2 hardening (2026-04-30) — second anchor
- Task R1 anchor (top-4-urgent ordering 0.06 + adversarial bucket 0.05) didn't bite (score went 0.77→0.83).
- Added §5 CP "Owner_Load formula + top-2 precision" 0.07.
- Added GT field top_owners_by_load (Blair=5 total, Devon=5 total — top 2 by active+urgent+blocked).
- Shaved 0.07 from Workbook deliverable (0.135→0.065).
- Target: opus 0.83 → ~0.70 (loses 0.07 if top-load owner counts drift OR formulas missing).

## Round 3 hardening (2026-04-30) — third anchor
- After R1+R2 (top-4 ordering + adversarial bucket + owner_load precision), score 0.83→0.795 minor drop.
- R3 added §5 CP "Per-urgent-card SLA + due-pressure precision" 0.08 (4/4 strict).
- Added GT fields urgent_card_required_fields + urgent_card_min_with_fields.
- Shaved 0.08 from Top work order quality (0.16→0.08); the R1 top-4 ordering anchor (0.06) already covers head precision, so the broader top_work_order CP shed weight.
- Target: opus 0.795 → ~0.65 (loses 0.08 if sla_hours/due_pressure_score not included).

## Round 4 hardening (2026-04-30) — fourth anchor
- After R1+R2+R3, score still at 0.81 (anchors landed inconsistently).
- R4 added §5 CP "Per-card priority-vs-due-date contradiction detection" 0.08.
- Added GT fields contradictions_required_count + contradiction_examples.
- Shaved 0.08 from Per-card data completeness (0.12→0.08, −0.04) and Reason grounding (0.08→0.04, −0.04).
- New §5 sum: 0.10+0.08+0.095+0.10+0.08+0.05+0.04+0.065+0.05+0.06+0.05+0.07+0.08+0.08 = 1.00.
- Target: opus 0.81 → ~0.70 (loses 0.08 if contradictions not surfaced).

## Round 5 hardening (2026-04-30) — cap for shallow unblockers
- After R1+R2+R3+R4 anchors, score 0.79.
- §6 added "Cap 0.65 — Shallow unblockers chase_action" (≥3 of 4-6 unblockers must have ≥20-char chase_action).
- Added GT fields min_chase_action_chars + min_unblockers_passing_chase_action_min_length.
- Target: opus 0.79 → ~0.65 if chase actions are short.

## Round 6 hardening (2026-04-30) — replacement strict cap
- R5's chase_action cap (≥3 of unblockers, 20-char min) didn't fire (score went 0.79→0.84).
- §6 added "Cap 0.55 — Insufficient unblockers detail" (4-of-4 strict, 30-char min, must name person/team or ticket/system).
- Added GT fields min_unblockers_count + min_unblockers_chase_action_chars + min_unblockers_passing_strict.
- Target: opus 0.84 → ~0.55 if unblocker chase actions are vague.

## Round 10 hardening (2026-04-30) — Cards sheet completeness cap
- Score still continue 0.61 after R5+R6 caps.
- §6 added "Cap 0.45 — Cards sheet incomplete" (Cards sheet must have ≥25 rows AND all rows complete on required fields).
- Added GT fields min_cards_sheet_rows + required_cards_sheet_fields.
- §5 weights unchanged (sum still 1.00). Lower cap (0.45) provides a stronger floor than the existing 0.55 unblockers cap.
- Target: opus 0.61 → ~0.46 if Cards sheet is partial.

## Review pass (2026-04-30)

User-driven review: drop xlsx deliverable entirely (json/xlsx redundancy),
remove specific list-name mentions from prompt (those are exam points),
strip implicit numeric anchors ("8 cards today", "4-6 unblockers") from
prompt language, ensure live-API mode actually requires API request, and
make all surviving checkpoints strict (no "≥X/Y" softening).

### Prompt changes (task field, live-API mode)
- Removed list enumeration "Todo / Doing / Blocked / Done" — user explicitly
  said list discovery is itself an exam point.
- Removed "25 cards spread across four lists" framing — replaced with the
  more user-voiced "is a mess and I want to know what to actually work on
  first today".
- Removed "8 cards I should actually grind through today" → replaced with
  "the cards I should actually grind through today" (no implicit count).
- Removed "4-6 blocked cards" → replaced with "the blocked cards" / "the
  cards I need to chase down" (no implicit count).
- Removed all xlsx deliverable language (Cards / Work_Order /
  Bucket_Summary / Owner_Load sheets, formula expectations, etc.).
- Reworded skill mention to be in the first paragraph, natural-voiced:
  "Please use the trello skill to pull the live board state, then use the
  summarize-pro skill to turn the card evidence into a clean work order".
- Removed parenthetical asides — no brackets remain.
- Made live-API path explicit and load-bearing: "Hit the live Trello REST
  API: board id is in $TRELLO_BOARD_ID, auth is $TRELLO_API_KEY and
  $TRELLO_API_TOKEN. Fetch the lists and all cards on the board yourself".

### task_snapshot (snapshot mode)
- Identical structure but mentions `sources/trello_snapshot.json` and the
  `generated_at` timestamp instead of the API. Snapshot is ONLY exposed
  via this branch — live-API mode does not inject the snapshot file.

### Eval rule changes
- Removed CP "Workbook deliverable" (0.065) and "Owner_Load formula +
  top-2 precision" (0.07) entirely.
- Removed CP "Per-card priority-vs-due-date contradiction detection"
  (0.08) — this was a synthetic harness without a public prompt anchor.
- Reweighted §5 to sum 1.00:
  - Per-card data completeness 0.08 → 0.10 (+0.02)
  - Bucket accuracy 0.095 → 0.13 strict 25/25 (+0.035)
  - Bucket counts new line 0.10 (+0.10) — exam-point recovery for
    discovering the bucket structure
  - Top work order quality 0.08 → 0.09 strict 8/8 (+0.01)
  - Unblockers identification 0.05 → 0.07 strict 4/4 (+0.02)
  - Reason grounding 0.04 → 0.05 (+0.01)
  - Skills genuinely used 0.05 → 0.07 (+0.02)
- §5 sum check: 0.10 + 0.10 + 0.13 + 0.10 + 0.10 + 0.09 + 0.07 + 0.05 +
  0.07 + 0.06 + 0.05 + 0.08 = 1.00.
- All anchors now strict: bucket accuracy 25/25 (no ≥23 softening),
  top work order 8/8 GT ids (no "overlap ≥6"), unblockers 4/4 (no
  "≥3 → half credit"), bucket counts exact 4/10/4/7.
- Removed all Cap 0.45 (Cards sheet incomplete) — xlsx no longer
  required.
- Added Cap 0.40 — Live-API mode bypass: if snapshot is absent and
  the executor's data shows no API-hit evidence, cap at 0.40 — stops
  the executor from short-circuiting the live-API requirement.
- Snapshot/live-API separation is documented in §3 and §9: snapshot
  file is intentionally NOT injected in live-API mode.

### Ground truth changes
- Removed `workbook_requirements` block entirely (cards_sheet_required_columns,
  bucket_summary_expected_counts, owner_load_expected_counts,
  formula_expectation, work_order_required_count).
- Removed `min_cards_sheet_rows`, `required_cards_sheet_fields`,
  `top_owners_by_load`, `contradictions_required_count`,
  `contradiction_examples` (no longer evaluated).
- Kept all per-card buckets, priority map, top_work_order ids,
  expected_unblockers with chase actions.
- Bucket counts (urgent=4, routine=10, blocked=4, done=7) preserved
  as the strict implicit anchor.
