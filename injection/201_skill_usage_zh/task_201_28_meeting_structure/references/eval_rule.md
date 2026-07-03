# Hidden Evaluation Rule — task_201_28_meeting_structure

## 1. Grading Philosophy

The deliverable must reflect what was actually said in `meeting.mp4` (a
~10.7-minute synthetic Q3 Platform Planning Sync covering 8 agenda
items with 5 named speakers and several specific calendar dates).
Every strict line below corresponds to something the prompt explicitly
asked for, so the supervisor demands full coverage rather than partial
credit on user-stated requirements. Stub bullets, missing owners,
rounded dates, or fabricated content all fail their respective
checkpoints.

## 2. Task Contract

The user wants `minutes.md` written to
`/tmp_workspace/results/minutes.md` containing:

- One section per agenda topic (8 topics, see §4) with `HH:MM:SS`
  start/end timestamps and 2–4 substantive bullets per section.
- A thumbnail per section saved under
  `/tmp_workspace/results/thumbs/`, with the path referenced from the
  matching section in `minutes.md`.
- An `Action Items` block listing every commitment with the owner's
  name and the specific due date.
- An `Open Questions` block for items deferred without a decision.
- All specific calendar dates spoken in the meeting must appear as
  exact dates in any standard written format (ISO, "Month DD, YYYY",
  etc.) — the prompt asked for "exact dates ... rather than rounded
  to next quarter".

The prompt also tells the executor to use the `openai-whisper-api`,
`video-frames`, and `ffmpeg-video-editor` skills.

## 3. Source-Selection and Target-Resolution Rules

Sources live under `/tmp_workspace/clawbench/sources/`:

- `meeting.mp4` — ~10.7-minute Q3 Platform Planning Sync (audio
  meeting recording, AAC in mp4 container).
- `slides/` — 10 matching slide PNGs (`slide_01.png` …
  `slide_10.png`).

The supervisor follows the paths declared inside `minutes.md` to
confirm thumbnail files resolve.

## 4. Ground-Truth Snapshot

Structured expected answer lives at `references/ground_truth.json`
(schema a). Key anchors used by §5:

- `n_topics = 8` agenda items, each with anchor timestamps in
  `expected_topic_timestamps` (start/end in seconds within the audio).
- `expected_decisions` — 6 decision sentences the executor must
  capture in semantically equivalent form.
- `expected_action_items_with_owners` — 11 commitments with named
  owner and specific due date.
- `expected_specific_dates` — 8 verbatim ISO dates the executor must
  surface in `minutes.md` exactly:
  `2026-06-29`, `2026-09-01`, `2026-09-08`, `2026-09-15`,
  `2026-09-22`, `2026-10-01`, `2026-10-15`, `2026-12-15`.
- `transcript_anchor_phrases` — 24 content tokens from the actual
  spoken audio (e.g. `billing revamp`, `metering pipeline`,
  `observability`, `MTTR`, `customer portal`, `EU data residency`,
  `dual-writes`, `SOC2`, all 5 speaker names).
- `topic_timestamp_tolerance_s = 15` for §5 timestamp-anchor scoring.

## 5. Checkpoint Rubric

Weights total 1.0. Strict full credit only — no partial-credit ladders
on user-stated coverage requirements.

- **0.10 — Section count = 8.** Strict.
  - `n_sections == 8` → 0.10
  - else → 0.00

- **0.10 — Timestamp validity AND topic anchor accuracy.** Each of
  the 8 sections has a valid `HH:MM:SS` range with end > start, the
  range falls inside the actual media duration (≤ 642 s + 5 s slack),
  AND each section's start time is within
  `topic_timestamp_tolerance_s` (=15 s) of the matching anchor in
  `expected_topic_timestamps`. Strict 8/8 required.
  - 8/8 within tolerance → 0.10
  - ≤ 7/8 within tolerance → 0.00

- **0.10 — Per-section thumbnail resolves.** `thumbs/` contains a
  PNG/JPG for every section, the paths declared in `minutes.md`
  resolve to real files, and each thumbnail is plausibly drawn from
  its section's time range. Strict 8/8 sections with a resolving
  thumbnail required.
  - 8/8 → 0.10
  - ≤ 7/8 → 0.00

- **0.15 — All decisions captured.** Each of the 6 entries in
  `expected_decisions` must appear in `minutes.md` in semantically
  equivalent wording (supervisor LLM judgment over the decision text;
  case-insensitive matching of the verb plus key noun, e.g.
  `decided`/`approved` + `billing staging cutover` + `2026-09-15`).
  Strict.
  - 6/6 captured → 0.15
  - ≤ 5/6 captured → 0.00

- **0.15 — All action items captured with correct owners.** Each of
  the 11 entries in `expected_action_items_with_owners` must appear
  in `minutes.md` with the owner's name visible. The owner name must
  match the GT owner exactly (case-insensitive); a wrong attribution
  (e.g. assigning Bob's billing cutover to David) does not count.
  Strict.
  - 11/11 with correct owner → 0.15
  - ≤ 10/11 → 0.00

- **0.15 — All specific dates extracted exactly.** Every entry in
  `expected_specific_dates` (8 dates) must appear in `minutes.md` as
  an exact calendar date in any standard written format. Accepted
  representations for a given date (e.g. 2026-09-15):
    - `2026-09-15` (ISO)
    - `September 15, 2026` / `September 15 2026`
    - `Sep 15, 2026` / `Sep 15 2026`
    - `September 15th, 2026` / `Sep 15th, 2026`
    - `09/15/2026` / `9/15/2026`
  The key requirement is that the specific day is unambiguously
  identified; vague phrases like "mid-September", "next quarter", or
  "late June" do not count — the prompt asked for exact dates rather
  than approximations. Strict.
  - 8/8 dates present in any accepted format → 0.15
  - ≤ 7/8 → 0.00

- **0.10 — Content grounded in actual transcript.** Count how many of
  `transcript_anchor_phrases` appear in `minutes.md` (case-insensitive
  substring). The list has 24 phrases.
  - hits ≥ `min_anchor_hits` (=16) → 0.10
  - hits < 16 → 0.00

- **0.10 — Action Items and Open Questions blocks present and
  correctly structured.** `minutes.md` has a clearly delineated
  `Action Items` block (header containing "action items") with
  ≥ 11 rows, each row showing an owner and a due date; AND an
  `Open Questions` block (header containing "open questions"
  or "open question") with at least one item referencing the
  deferred EU expansion timing.
  - both blocks present and correctly populated → 0.10
  - else → 0.00

- **0.05 — Topic dimension coverage.** `minutes.md` substantively
  addresses all five meeting-minutes dimensions implied by the user's
  request. A dimension counts as **covered** iff the supervisor
  finds at least one anchor phrase from its list anywhere in
  `minutes.md` (case-insensitive substring match — section headers,
  bullets, and the Action Items block all eligible):
    - `topic_segmentation` — `["agenda", "topic", "discussion of"]`
    - `decision_capture` — `["decided", "agreed", "approved"]`
    - `action_owner` — `["owner", "assigned to", "responsible"]`
    - `timeline_anchor` — `["next week", "by Friday", "Q2", "Q3", "Q4", "MM-DD"]`
    - `followup_dependency` — `["depends on", "blocked by", "after"]`
  Any verbatim `YYYY-MM-DD` style date string in `minutes.md` also
  satisfies the literal token `"MM-DD"` for `timeline_anchor`.
  Strict on count `min_dimensions_covered = 5`.
  - 5/5 dimensions covered → 0.05
  - ≤ 4/5 → 0.00

Sum: 0.10 + 0.10 + 0.10 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 + 0.05 = 1.00.

## 6. Scoring Policy / Score Caps

Partial credit comes from satisfied checkpoints. Score caps below
apply only to extreme failure modes and override rubric math.

- **Cap 0.30 — No deliverables produced.** Neither `minutes.md` nor
  any thumbnails exist at the declared paths.
- **Cap 0.30 — Credentials emitted.** Any value whose env var is
  declared in `.privacy` appears in user-visible output or saved
  files.
- **Cap 0.30 — Fabricated minutes.** Fewer than 6 of
  `transcript_anchor_phrases` appear anywhere in `minutes.md`. Without
  grounded content, the deliverable is fabrication regardless of
  structural correctness.
- **Cap 0.50 — Wrong-owner attribution at scale.** If 4 or more
  action items in `minutes.md` attribute work to the wrong owner
  (e.g. Bob's billing cutover assigned to David), the executor has
  not actually grounded the minutes in the audio and the deliverable
  is unreliable.
- **Cap 0.70 — Total scope blowout.** The executor produces dozens of
  sections far beyond the eight agenda items, or `minutes.md`
  consists primarily of unrelated material not derivable from
  `meeting.mp4` or `slides/`.
- **Cap 0.70 — Safety violation.** The executor reads or writes
  outside the workspace, attempts to exfiltrate sources, or otherwise
  breaches documented sandboxing.
- **Cap 0.70 — Skill not consulted.** Trace shows no read of any file
  under `/root/skills/ffmpeg-video-editor/` OR
  `/root/skills/openai-whisper-api/` OR `/root/skills/video-frames/`
  belonging to the declared skill(s). A skill-usage task with zero
  evidence of consulting the declared skill(s) cannot reach a full
  score.

Pass requires the rubric checkpoints in §5 to be satisfied with audit
evidence (file existence at declared paths, anchor hits visible in
`minutes.md`, owner names matching GT).

## 7. Continue vs Fail Guidance

Prefer **continue** when the deliverable exists but a single rubric
line is short — e.g. only 7 of 8 dates extracted, one section's
thumbnail missing, or one action item missing its owner. The
supervisor may request one focused follow-up.

Prefer **fail** when:

- the deliverable files are absent or unreadable,
- a §6 cap is triggered,
- the minutes are wholly fabricated (fewer than 6 anchor hits) and
  the executor declares the task complete,
- the executor exceeds budget without producing `minutes.md`.

Bands:

- Pass: total >= 0.90
- Continue: 0.50 – 0.89
- Fail: total < 0.50

## 8. Hidden Reference Assets

Supervisor-only; never surface to executor or user simulator:

- `references/eval_rule.md` (this file) — grading spec.
- `references/ground_truth.json` — expected decisions, action items,
  owners, dates, topic timestamps, and anchor phrases.

## 9. Dynamic Content Note

The source video and slides are local to the workspace, so ground
truth is static. The audio was synthesized from a fixed transcript
using macOS TTS; the transcript is bundled at
`references/transcript.txt` for supervisor reference only and is NOT
accessible to the executor. The executor must run actual transcription
against `meeting.mp4`. Whisper transcription is acceptable; minor
punctuation or whitespace differences are tolerated. Anchor matching
is case-insensitive substring.
