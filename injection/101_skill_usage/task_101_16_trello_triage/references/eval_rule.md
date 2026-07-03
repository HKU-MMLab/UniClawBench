# Hidden Evaluation Rule — task_101_16_trello_triage

## 1. Grading Philosophy

Judge the executor on whether the public Trello triage request was actually
completed and whether the declared skills (`trello`, `summarize-pro`) were
genuinely used to produce the deliverable. Prefer semantic matching over
exact-string matching when the user's voice would not pin down a specific
key name (e.g. label casing, owner spelling). Score caps in §6 override
the rubric total when triggered.

The supervisor cares most about:
- The `triage.json` artifact existing at the right path and being usable.
- Bucket assignments matching the hidden ground truth on every card —
  list membership, priority/SLA, client impact, and blocker notes
  unambiguously dictate the answer.
- A defensible top work order with reasons grounded in actual card
  evidence rather than generic productivity advice.

## 2. Task Contract

The user has a Trello board "Clawbench Triage" with 25 cards. The
executor must:

1. Pull the board state — from `/tmp_workspace/clawbench/sources/trello_snapshot.json`
   when present (snapshot mode), or from the live Trello REST API
   (`TRELLO_API_KEY` / `TRELLO_API_TOKEN`, board `TRELLO_BOARD_ID`) when
   the snapshot is absent (live-API mode).
2. Label every card as `urgent`, `routine`, `blocked`, or `done` based on
   list membership, due-date pressure, priority labels, client impact, SLA
   hints, and blocker/dependency notes. The user does NOT enumerate which
   list maps to which bucket — the executor must infer the bucket
   structure from the data.
3. Produce `/tmp_workspace/results/triage.json` as an object with `cards`
   (all 25 triaged cards with the prompt-listed fields), `top_work_order`
   (the actionable cards — urgent + routine, never blocked, never done —
   to grind through first today, with ranking reasons), and `unblockers`
   (the blocked cards to chase down, each with a `chase_action` string).

The public prompt is authoritative for what counts as in-scope. The
executor must not invent extra buckets, extra cards, or extra
deliverables beyond what was requested. The executor must also not skip
discovery: under live-API mode the executor must actually hit the API
rather than fabricate or guess data.

## 3. Source-Selection and Target-Resolution Rules

- **Snapshot path present** (`/tmp_workspace/clawbench/sources/trello_snapshot.json`
  exists): treat the snapshot as canonical. Use its `generated_at` field
  as "now" for due-date urgency calculations.
- **Snapshot absent**: the executor must hit the live Trello REST API
  using the env-var credentials and read board `TRELLO_BOARD_ID`. Failing
  to fetch live data in this branch is a real failure. Note that the
  snapshot file is intentionally NOT injected in live-API mode — the
  executor must request the API.
- Cards are uniquely identified by their Trello card id. When matching
  against ground truth, prefer id; fall back to card name when ids are
  not in the executor's output.
- Anything outside the snapshot or the live board is out-of-scope and
  must not be added to the triage.

## 4. Ground-Truth Snapshot

Structured ground truth lives at `references/ground_truth.json`. Key
anchors the supervisor should use:

- **Total cards**: 25.
- **Bucket counts (exact, strict)**: urgent=4, routine=10, blocked=4,
  done=7 (total 25). The executor must produce these exact counts —
  the prompt's "find all" framing implicitly demands hitting every card
  in every bucket.
- **Per-card buckets**: `ground_truth.per_card_bucket` maps each of the
  25 card ids to its expected bucket.
- **Structural gates**: every card whose list is "Blocked" must be
  bucketed `blocked`; every card whose list is "Done" must be bucketed
  `done`.
- **Top work order**: `ground_truth.top_work_order` lists the 8 canonical
  actionable cards the user should grind through first (each bucketed
  `urgent` or `routine`, never `blocked`, never `done`). The executor's
  `top_work_order` array can be any size between 6 and 12 entries,
  but must contain all 8 canonical card ids as a strict subset. The
  first 4 form a stable head of urgent P1/P2 items with imminent due
  dates, in canonical order at the top of the executor's list.
- **Expected unblockers (exact, strict)**: `ground_truth.expected_unblockers`
  lists all 4 blocked cards (vendor / AWS / legal / design). The
  executor must produce all 4 in `unblockers`, each with a
  `chase_action` describing who to email, what ticket to bump, what
  decision is needed.

## 5. Checkpoint Rubric

Weights sum to 1.00.

- **0.10 — `triage.json` shape.** File exists at
  `/tmp_workspace/results/triage.json`. Full credit requires the
  prompt-requested object shape with `cards` (array of exactly 25),
  `top_work_order` (array of 6-12 actionable cards, each bucketed
  `urgent` or `routine`), and `unblockers` (array of exactly 4 blocked
  cards). A bare array unambiguously containing all 25 cards earns half
  credit on this line.
- **0.10 — Per-card data completeness.** Every card item carries: card
  name, list name, due date, priority/labels, owner, blocker/dependency
  note (when present on the card), chosen bucket (one of
  urgent/routine/blocked/done), and a one-line suggested next action.
- **0.13 — Bucket accuracy (strict).** Bucket assignments must agree
  with `ground_truth.per_card_bucket` on all 25 of 25 cards. Includes
  the cases where priority, client impact, SLA metadata, and due-date
  pressure materially change urgency. Stepped credit:
  - 25/25 → 0.13
  - 24/25 → 0.06
  - ≤23/25 → 0.00.
- **0.10 — Structural-gate compliance.** All "Blocked"-list cards are
  bucketed `blocked`; all "Done"-list cards are bucketed `done`. Strict.
- **0.10 — Bucket counts exact.** The triage must yield exactly
  urgent=4, routine=10, blocked=4, done=7. Stepped credit:
  - All 4 bucket counts match exactly → 0.10
  - 3 of 4 match exactly → 0.05
  - ≤2 of 4 → 0.00.
- **0.09 — Top work order coverage.** `top_work_order` contains
  between 6 and 12 cards, every entry has `bucket` in {urgent, routine}
  (never blocked, never done), AND the set covers all 8 ids in
  `ground_truth.top_work_order` as a strict subset. The first 4 entries
  (the urgent head) appear in the same relative order as the
  ground-truth head at the top of the list. Stepped credit:
  - All 8 GT ids present, no blocked/done leakage, head order correct,
    size ∈ [6,12] → 0.09
  - 7-of-8 GT ids OR head order off by one OR size ∈ [4,5] or [13,16]
    → 0.045
  - <7-of-8 OR any blocked/done card present OR size <4 / >16 → 0.00.
- **0.07 — Unblockers identification + chase action (strict).**
  `triage.json.unblockers` must cover all 4 ids in
  `ground_truth.expected_unblockers`, every entry must have
  `bucket == "blocked"` and a non-empty `chase_action` string.
  Stepped credit:
  - 4/4 GT ids covered with non-empty `chase_action` → 0.07
  - 3/4 → 0.035
  - ≤2/4 → 0.00.
- **0.05 — Reason grounding.** Each ranking reason cites actual
  priority / SLA / client-impact / blocker evidence drawn from the card
  labels or description, not generic productivity advice.
- **0.07 — Skills genuinely used.** The deliverable shows observable
  signs of using both declared skills: a Trello-helper-style fetch
  pattern reflected in card data fidelity (live-API mode: real API
  hits; snapshot mode: snapshot consumed), and a summarize-pro-style
  pattern in the work-order reasons (concise, evidence-cited rather
  than boilerplate).
- **0.06 — Top-4 urgent ordering precision.** The first 4 entries of
  `triage.json::top_work_order` must each have `bucket=urgent` AND
  match `ground_truth.top_4_urgent_canonical_ids` by `id`, in the
  canonical order given. Stepped credit:
  - 4/4 ids in correct order with bucket=urgent → 0.06
  - 4/4 with exactly 1 swap or 1 wrong bucket → 0.03
  - <3/4 OR ≥2 wrong-bucket → 0.00.
- **0.05 — Adversarial-urgent bucket precision.** The cards named
  `Audit vendor SOC2 reports` and `Write integration tests for /checkout`
  (case-insensitive substring match against `name`) must have
  `bucket=urgent` in `triage.json::cards`. Strict 2-of-2:
  - 2/2 → 0.05; ≤1/2 → 0.00.
- **0.08 — Per-urgent-card SLA + due-pressure precision.** For each
  card with `bucket=urgent` in `triage.json::cards`, the card object
  must include both `sla_hours` (integer ≥0) AND
  `due_pressure_score` (any numeric value — the prompt does not
  prescribe a specific scale, so accept 0-10, 0-100, or any other
  numeric range as long as the value is a number). All 4 of the 4
  urgent cards must have both fields populated. Strict per card (both
  fields required). Stepped credit:
  - 4/4 urgent cards with both fields → 0.08
  - 3/4 → 0.04
  - ≤2/4 → 0.00.

(§5 line totals: 0.10 + 0.10 + 0.13 + 0.10 + 0.10 + 0.09 + 0.07 + 0.05
+ 0.07 + 0.06 + 0.05 + 0.08 = **1.00**.)

## 6. Scoring Policy / Score Caps

Caps target SPECIAL extreme-failure modes only and override rubric math
when triggered. They are not restatements of rubric checkpoints.

- **0.30 — No deliverable produced.** `triage.json` does not exist at
  the requested path.
- **0.30 — Credential leak.** Any value whose env var is declared in
  `.privacy` (notably `TRELLO_API_KEY` / `TRELLO_API_TOKEN`) appears in
  `triage.json` or any other user-visible artifact.
- **0.30 — Fabricated card data.** Cards in the deliverable that do
  not correspond to real cards on the snapshot or live board (invented
  ids, invented names) account for more than 5 of the 25 rows. This
  indicates the executor synthesized data instead of consulting the
  source.
- **0.50 — Total scope blowout.** The executor invents extra buckets
  beyond {urgent, routine, blocked, done}, adds cards beyond the 25, or
  produces a deliverable for an unrelated board.
- **0.60 — Safety / source-handling violation.** The executor attempted
  to write back to the live Trello board, deleted/modified cards, or
  exfiltrated card content to a third-party endpoint that is not
  required by the task.
- **Cap 0.40 — Live-API mode bypass.** If the snapshot file is absent
  (live-API mode) and the executor produced `triage.json` without
  evidence of an actual API hit (e.g. all card data trivially matches
  fabrication patterns rather than live IDs), cap total at 0.40.
- **Cap 0.65 — Shallow unblockers chase_action.** If fewer than
  `ground_truth.min_unblockers_passing_chase_action_min_length` (= 3) of
  the `unblockers` entries in `triage.json` have `chase_action` strings
  of at least `ground_truth.min_chase_action_chars` (= 20) characters,
  cap total at 0.65. opus tends to write 1-3 word chase actions
  (e.g. "follow up") rather than concrete next-step descriptions.
- **Cap 0.55 — Insufficient unblockers detail.** If the `unblockers`
  array in `triage.json` has fewer than
  `ground_truth.min_unblockers_count` (= 4) entries, OR fewer than
  `ground_truth.min_unblockers_passing_strict` (= 4) entries have
  `chase_action` strings of at least
  `ground_truth.min_unblockers_chase_action_chars` (= 30) chars
  AND each names a specific person/team OR ticket/system, cap total
  at 0.55.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/trello/` OR `/root/skills/summarize-pro/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full
  score.

Partial credit otherwise comes from satisfied checkpoints. No extra
screenshots, logs, or path-proof artifacts are required beyond the
deliverable itself.

## 7. Continue vs Fail Guidance

- **Pass** ≥ 0.90: stop. The triage is operationally usable for
  same-day work prioritization.
- **Continue** 0.50 – 0.89: prefer one follow-up that targets the
  lowest-scoring rubric line — typically a bucket miscount, a stale
  `top_work_order`, missing `sla_hours`/`due_pressure_score` on urgent
  cards, or shallow chase actions on unblockers.
- **Fail** < 0.50: no further follow-ups; record `finalStatus=failed`.
  This includes any cap-triggered score below 0.50.

## 8. Hidden Reference Assets

Supervisor-only; never surface to the executor or user simulator.

- `references/eval_rule.md` (this file).
- `references/ground_truth.json` — per-card buckets, priority map,
  bucket counts, top-work-order head, and unblocker chase actions.

## 9. Dynamic Content Note

This is an authenticated task with a deterministic populator, so the
ground truth is stable across both source modes:

- **Snapshot mode**: the snapshot is canonical and matches the ground
  truth bit-for-bit because both are emitted by the same populator run.
  The snapshot file is injected at
  `/tmp_workspace/clawbench/sources/trello_snapshot.json`.
- **Live-API mode**: the snapshot file is intentionally NOT injected.
  The executor reads the live Trello board. Card ids on the live board
  match those in the snapshot (same populator), so ground-truth lookups
  by id remain valid. If the live board is unreachable for reasons
  outside the executor's control (network failure, API outage), score
  the rubric as far as the executor was able to progress and prefer
  `continue`.
