# Design notes — task_101_04_audio_transcript

Archive of version-design and benchmark-construction notes that should
not appear in the supervisor-facing eval_rule. `meta/` is never injected
into the executor or supervisor view.

## Skill-engagement cap origin

Earlier iterations of this task used a soft cap (around 0.89) when the
trace showed zero evidence of consulting `/root/skills/openai-whisper-api/`,
on the rationale that a skill_usage benchmark cannot award full marks if
the declared skill was bypassed entirely. In the current eval_rule that
intent is encoded as a positive checkpoint (skill consultation is one of
the weighted rubric lines) rather than as a soft cap, which keeps §6
reserved for genuine extreme-failure modes (no deliverable, credential
leak, fabricated transcript, safety violation).

## Source choice

`standup.wav` is intended to be a short (~60s) mono 16 kHz English
standup clip — e.g. a CC-0 demo from freesound or librivox. The anchor
phrases in `ground_truth.json` track the recorded standup script and
must be regenerated whenever the audio is re-rendered.

## v8 hardening round 4 (2026-04-29)

Round-3 abstract dimension anchors were too permissive — supervisor
awarded partial credit even when the deliverable barely mentioned the
core meeting-structure tokens. Round 4 replaces the abstract phrasing
with **anchor-keyword detection** so each dimension is binary-checkable
against a concrete word list (agenda / decisions / action / open /
speaker dynamics). Prompt rewritten to embed five meeting-structure
dimensions naturally, asking for a short trailing comment block in the
SRT or a sidecar `standup_notes.md`.

§5 rebalanced: SRT validity 0.20 → 0.15 (-0.05); cue count 0.15 → 0.10
(-0.05); first cue start 0.10 → 0.05 (-0.05); new "Topic dimension
coverage" anchor at +0.15. Final weights:
0.15 + 0.10 + 0.15 + 0.20 + 0.05 + 0.10 + 0.10 + 0.15 = 1.00.

Anchor scoring strict: 5/5 → 0.15, 4/5 → 0.05, ≤3/5 → 0.00. Anchor
matches must come from saved artifacts under `/tmp_workspace/results/`.
Anchors found inside transcribed cue text **also count** — many
agenda / decision / action vocabulary words are likely to be spoken
naturally, so this rewards a faithful transcription. ground_truth.json
gains `topic_dimensions` (5 keyword lists) plus
`min_dimensions_covered: 5`. score caps and success_threshold (0.90)
unchanged.

## v8 hardening round 8 (2026-04-30) — sidecar + honest-reporting

**Problem.** The round-4 `Topic dimension coverage` checkpoint scored
on case-insensitive substring matches against five fixed keyword lists
(`decided / agreed / approved / let's go with`, etc.). The actual
recorded audio is a single-speaker status update with **no consensus
moments** — i.e. `expected_count: 0` for `decisions_made`. A model
that honestly reports "no decision was made" loses dimension credit;
a keyword-stuffer that pads its sidecar with `decided / agreed /
approved` boilerplate passes the substring check. This is the wrong
incentive for a transcription task and rewards hallucination.

**Fix (path B — sidecar + honest-reporting).** The 0.15
`Topic dimension coverage` anchor is split and replaced with two new
checkpoints (0.10 each, total 0.20), and the surplus 0.05 is
redistributed by trimming the four highest-weight remaining checkpoints
by 0.01–0.02 each:

- **0.10 — Sidecar structured deliverable** (new). Requires
  `/tmp_workspace/results/standup_struct.json` to exist, parse as
  JSON, and contain three array keys (`decisions`, `action_items`,
  `open_questions`) with required per-element fields including a
  non-empty `source_evidence_quote`. Empty arrays are explicitly OK.
- **0.10 — Honest-reporting consistency** (new). Compares the
  sidecar against `ground_truth.expected_struct_state`:
  `decisions.expected_count: 0` (empty array is correct);
  `action_items.min_count: 1` (≥1 item, evidence verifiable in SRT
  or anchor list); `open_questions.min_count: 1` (same shape).
  Padding empty arrays when GT says no decisions were made is
  scored as hallucination.

**Weight redistribution table (round-4 → round-8):**

| Checkpoint                        | Round-4 | Round-8 | Δ     |
|-----------------------------------|---------|---------|-------|
| SRT validity                      | 0.15    | 0.14    | -0.01 |
| Cue count band                    | 0.10    | 0.10    | 0.00  |
| English language                  | 0.15    | 0.14    | -0.01 |
| Anchor hits                       | 0.20    | 0.18    | -0.02 |
| First cue start                   | 0.05    | 0.05    | 0.00  |
| Last cue end                      | 0.10    | 0.09    | -0.01 |
| Skill engagement                  | 0.10    | 0.10    | 0.00  |
| Topic dimension coverage          | 0.15    | —       | -0.15 |
| Sidecar structured deliverable    | —       | 0.10    | +0.10 |
| Honest-reporting consistency      | —       | 0.10    | +0.10 |
| **Total**                         | 1.00    | 1.00    | 0.00  |

`ground_truth.json` gains `expected_struct_state` (decisions /
action_items / open_questions) with `expected_count` or `min_count`
plus `anchor_phrases` and explanations. Original `topic_dimensions`
keyword block is preserved as fallback / documentation but no longer
carries weight. score caps and success_threshold (0.90) unchanged.

## Round 8 trim (2026-04-30) — disagreement-handling precision CP

Round 8 measurement showed the task at PASS 1.0 — one strict
sub-checkpoint added to drop ceiling to ~0.95. New 0.05 CP
"Speaker-disagreement-handling precision" requires the bottom
note / sidecar to either name a specific disagreement / concern /
push-back OR explicitly state no recorded disagreement, drawing
from `ground_truth.acceptable_disagreement_phrases`. To rebalance,
Anchor hits is trimmed 0.18 → 0.13 (-0.05). Final weights:
0.14 + 0.10 + 0.14 + 0.13 + 0.05 + 0.09 + 0.10 + 0.10 + 0.10 +
0.05 = 1.00. Score caps and success_threshold (0.90) unchanged.

## Review pass (2026-04-30)

User feedback (Task 4 in review_record.md):

1. The bottom-note guidance leaned too hard on deterministic format —
   bracketed keyword enumerations like `(decided / agreed / approved
   / let's go with)` were both rubric-leaking (per global rule #6 and
   #12 — no parens, no rubric-keyword enumeration in prompts) and felt
   mechanical. Rewrite as natural language describing what to cover
   ("how the agenda flowed, what was actually decided, who took on
   which action item, what was left open, how the room split when
   anyone pushed back") without keyword lists.
2. The json schema description was technically fine but dry — soften
   it to "I also want a structured json record … so I can grep it
   later" and describe the fields prose-style.
3. Add CONTENT-based checkpoints, not just structural shape checks.

### Prompt changes (`tasks/101_skill_usage/task_101_04_audio_transcript.yaml`)

- **Skill mention moved to first paragraph.** Was at the end of the
  first paragraph already, but rephrased to come immediately as part
  of the request: "Please use one of the workspace's transcription
  skills to turn it into subtitles for me, and save the result to
  …".
- **Removed all parenthetical keyword enumerations:**
  `(first / next / follow up)`, `(decided / agreed / approved / let's
  go with)`, `(I'll, we'll, owns, by Friday, due …)`, `(unclear, TBD,
  still figuring out, need to confirm)`, `(disagree, concern, push
  back, support)`. Replaced with natural-language description: "how
  the agenda actually flowed, what was actually decided, who took on
  which action item, what was left open or unresolved, and how the
  room split when anyone pushed back". This satisfies global rules #6
  (no parens) and #12 (no rubric-keyword enumeration in prompts).
- **Softened json schema phrasing.** Was a tight schema list; now a
  conversational request: "I also want a structured json record …
  so I can grep it later. It should have three arrays — decisions,
  action_items, open_questions. For each decision give me what was
  decided and a short quote …". Same fields required, just
  prose-style.
- **No-padding warning preserved** ("If the meeting genuinely had
  nothing in one of these buckets, just leave that array empty and
  say so in the note — please don't pad it to look complete") because
  it's a behavioural instruction, not a rubric leak, and is the
  honesty incentive that the §6 hallucinated-decisions cap rewards.

### Eval changes (`references/eval_rule.md`)

Added three CONTENT-based CPs and rebalanced §5:

- **0.15 — decisions content match.** Strict equality with
  `expected_decisions` (empty array per GT). Padded entries fail this
  CP outright. Bottom note must also explicitly acknowledge no
  decisions were taken.
- **0.15 — action_items content match.** Must contain ≥1 entry
  matching every `expected_action_items` entry on (owner, what,
  evidence_anchor) triple via canonical-or-accepted-variant
  substring. Deadline matched only when non-null in GT (here `null`
  is acceptable per GT's deadline_accepted = ["today", "by end of
  day", "eod", null]).
- **0.10 — open_questions content match.** Must contain ≥1 entry
  matching every `expected_open_questions` entry on (question,
  evidence_anchor) pair via canonical-or-accepted-variant substring.

The previous "Topic dimension coverage" via substring keyword anchors
and "Honest-reporting consistency" using min_count surface heuristics
were both replaced by these strict, GT-driven content matches. The
"Speaker-disagreement-handling precision" 0.05 CP from the round-8
trim was folded out (the natural-language note is no longer a
rubric-graded section — it's only required as part of the decisions
content-match CP, which requires acknowledging no-decisions).

Anchor coverage tightened: was "5/7 of `ordered_anchor_phrases` in
order" → now strict "ALL 7 in order". The prompt asks for a faithful
transcription of the audio so every recorded line is in scope (per
global rule #8 — strict checkpoints, no `≥X/Y` slack).

**Weight redistribution table (round-8-trim → review-pass):**

| Checkpoint                          | Round-8 trim | Review pass | Δ     |
|-------------------------------------|--------------|-------------|-------|
| SRT validity                        | 0.14         | 0.10        | -0.04 |
| Cue count band                      | 0.10         | 0.05        | -0.05 |
| English language                    | 0.14         | 0.10        | -0.04 |
| Ordered anchor coverage (strict 7/7)| 0.13         | 0.10        | -0.03 |
| First cue start                     | 0.05         | 0.03        | -0.02 |
| Last cue end                        | 0.09         | 0.05        | -0.04 |
| Skill engagement                    | 0.10         | 0.10        | 0.00  |
| Sidecar structured (shape)          | 0.10         | 0.07        | -0.03 |
| Honest-reporting consistency        | 0.10         | —           | -0.10 |
| Speaker-disagreement precision      | 0.05         | —           | -0.05 |
| decisions content match (NEW)       | —            | 0.15        | +0.15 |
| action_items content match (NEW)    | —            | 0.15        | +0.15 |
| open_questions content match (NEW)  | —            | 0.10        | +0.10 |
| **Total**                           | 1.00         | 1.00        | 0.00  |

§5 sum verified: `0.10 + 0.05 + 0.10 + 0.10 + 0.03 + 0.05 + 0.10 +
0.07 + 0.15 + 0.15 + 0.10 = 1.00` ✓

### GT changes (`references/ground_truth.json`)

Added explicit content lists to drive the new CPs:

- **`expected_decisions: []`** — single-speaker status update has no
  consensus moments. Empty is the correct answer; padding is
  hallucination.
- **`expected_action_items`** — one entry: owner = speaker,
  what = "investigate the notification service latency bug",
  deadline = "today" (or null acceptable), evidence anchored to
  "notification service latency bug". Includes `owner_accepted`,
  `task_accepted`, `deadline_accepted`, `evidence_anchor_accepted`
  variant lists for paraphrase tolerance.
- **`expected_open_questions`** — one entry: question = "need access
  to the staging logs to confirm the missing database index",
  evidence anchored to "need access to the staging logs". Includes
  `question_accepted` and `evidence_anchor_accepted` variant lists.
- **`content_match_policy`** — case-insensitive substring against
  canonical-or-accepted-variant for owner / what / question /
  source_evidence_quote.

Existing fields (`min_anchor_hits`, `topic_dimensions`,
`min_dimensions_covered`, `acceptable_disagreement_phrases`,
`expected_struct_state`) preserved for backward compatibility but no
longer carry rubric weight.

### Score caps

New cap added per global rule #11 (existing caps untouched, new caps
for new failure modes are OK):

- **Cap 0.60 — Hallucinated decisions.** Triggers when the executor
  pads `decisions` despite the empty-GT and the prompt's explicit
  no-padding instruction. Higher than the existing 0.40 fabricated-
  transcript cap because this is a more nuanced failure (the
  transcript itself may be fine, but the structured deliverable is
  dishonest).

success_threshold (0.90) unchanged.
