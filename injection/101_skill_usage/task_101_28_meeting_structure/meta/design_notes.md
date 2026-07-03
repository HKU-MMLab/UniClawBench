# Internal design notes — task_101_28_meeting_structure

These notes are for benchmark maintainers only. They are NOT part of the
hidden grading spec and must not be surfaced to executor or supervisor.

## Calibration history

- `min_sections` was lowered from 4 to 3 to match the actual ~1-minute
  duration of the recap clip; stepped credit on §5 line 1 still rewards
  partial structuring.
- A content-grounding rubric line (transcript anchor phrases) and a
  matching score cap were added because earlier runs showed executors
  fabricating plausible-sounding minutes from slide images alone, without
  performing any actual transcription. The anchor list is derived from
  the spoken audio of the Q2 Planning Sync clip.
- The skill-usage cap targets the case where an executor never opens any
  declared multimedia skill directory; consulting any one of the three is
  treated as sufficient since the task can be completed via several valid
  skill compositions.

## Anchor source

`ground_truth.transcript_anchor_phrases` was authored from a manual
transcript of `meeting.mp4`. Owners (`Alice`, `Bob`, `Carol`) and dates
(`May 15`, `May 22`, `June 1`) are spoken in the clip and double as
Action-Items checks.

## v8 hardening round 4 (2026-04-29)

Round-3 abstract dimension anchors were too permissive — supervisor
gave partial credit even when the deliverable barely used the concrete
meeting-minutes vocabulary. Round 4 replaces the abstract phrasing with
**anchor-keyword detection** so each dimension is binary-checkable
against a concrete word list. Prompt rewritten to embed five
meeting-minutes dimensions naturally (topic segmentation, decision
capture, action owner, timeline anchor, followup dependency).

§5 rebalanced: section count 0.15 → 0.10 (-0.05); timestamp validity
0.15 → 0.10 (-0.05); content grounded 0.25 → 0.20 (-0.05); new "Topic
dimension coverage" anchor at +0.15. Final weights:
0.10 + 0.10 + 0.15 + 0.15 + 0.15 + 0.20 + 0.15 = 1.00.

Anchor scoring strict: 5/5 → 0.15, 4/5 → 0.05, ≤3/5 → 0.00. The
`timeline_anchor` dimension accepts the literal token `"MM-DD"` OR any
real MM-DD style date string (e.g. `05-15`, `5/15`) since real minutes
will use actual dates rather than the literal placeholder. Anchor
matches must come from `/tmp_workspace/results/minutes.md`.
ground_truth.json gains `topic_dimensions` (5 keyword lists) plus
`min_dimensions_covered: 5`. score caps and success_threshold (0.90)
unchanged.

## v8 hardening round 9 (2026-04-30)

Round-8 measurements show this task at PASS ≈0.95. Round 9 adds a
small auxiliary CP "Per-section thumbnail/timestamp anchor" at weight
0.05 to nudge scores down by ~0.05. Each of the 5 sections must
include either a thumbnail filename (e.g. `frame_120s.png`) or an
explicit timestamp anchor (HH:MM:SS / MM:SS); ≥4 of 5 are required
for partial credit. Stepped: 5/5 → 0.05, 4/5 → 0.025, ≤3/5 → 0.00.
Rebalance: Content-grounded 0.20 → 0.15 (-0.05) funds the new line;
sub-tier credits scaled accordingly (7+ hits → 0.15, 5–6 → 0.10,
3–4 → 0.06). Final §5 sum: 0.10+0.10+0.15+0.15+0.15+0.15+0.05+0.15
= 1.00. GT gains `min_sections_with_thumbnail_anchor: 4` and
`acceptable_thumbnail_anchor_format`. Score caps and
success_threshold unchanged.

## Review pass (2026-04-30) — full task redesign

Per user feedback (review_record.md Task 28): the previous
~1-minute recap clip was insufficient. Redesigned as a synthetic
~10.7-minute Q3 Platform Planning Sync with:

- 5 named speakers (Alice, Bob, Carol, David, Erin), each mapped to a
  distinct macOS `say` voice (Samantha, Alex, Karen, Daniel, Moira).
- 8 agenda items varying in length: brief status updates
  (observability, warehouse) interleaved with multi-turn debates
  (billing date pushback, design system big-bang vs incremental,
  Q4 budget split).
- 6 explicit decisions, 11 named action items, 8 specific ISO calendar
  dates (`2026-06-29`, `2026-09-01`, `2026-09-08`, `2026-09-15`,
  `2026-09-22`, `2026-10-01`, `2026-10-15`, `2026-12-15`).
- 1 deferred open question (EU expansion timing).
- 2 controversial decisions with multi-turn debate (billing cutover
  date Bob vs Carol; design system migration approach Carol vs
  David/Bob).

Synthesis approach:
1. Hand-authored transcript at `sources/transcript.txt` (48 turns,
   ~13 min wall clock).
2. `say -v <voice> -r 175 -o turn_NNN.aiff <text>` per turn.
3. `afconvert` each AIFF to 16 kHz mono PCM WAV.
4. Concatenate WAVs via Python `wave` module with 0.4 s gaps.
5. `afconvert -f mp4f -d aac@16000 -b 64000` to produce
   `meeting.mp4` (3.0 MB AAC-in-mp4 container, audio-only).
6. Per-turn timestamps captured to `sources/timestamps.json`.

Note: ffmpeg is unavailable on the maintainer host; mp4 here is a
valid AAC-in-MP4 container with audio track only. Whisper accepts it.
The bundled transcript also lives in `sources/` as a supervisor
reference; the executor must still run real transcription on the
audio.

Slides regenerated at `sources/slides/` to match new agenda
(`slide_01.png` … `slide_10.png`: 1 title card + 8 topic slides +
1 action items slide), drawn with PIL (1280×720).

Prompt rewritten in **English** (per user critical rule §3a),
mentions skills in the first paragraph, no parentheses/brackets
beyond inline use, no enumerated rubric keywords. Asks for verbatim
specific dates and explicit Open Questions block. The five
meeting-minutes dimensions are still embedded naturally in the
prompt body (agenda/topic/discussion of, decided/agreed/approved,
owner/assigned to/responsible, due date language, depends on /
blocked by / after).

Eval rebalanced for new ground truth — strict full-credit thresholds
on user-stated requirements:

| Weight | Checkpoint                                           |
|--------|------------------------------------------------------|
| 0.10   | Section count == 8                                   |
| 0.10   | Timestamp validity + topic anchor (8/8 within ±15 s) |
| 0.10   | Per-section thumbnail resolves (8/8)                 |
| 0.15   | All 6 decisions captured                             |
| 0.15   | All 11 action items with correct owners              |
| 0.15   | All 8 specific dates verbatim                        |
| 0.10   | Content grounded — ≥16/24 anchor hits                |
| 0.10   | Action Items + Open Questions blocks structured      |
| 0.05   | Topic dimension coverage (5/5)                       |

§5 sum verified: 0.10+0.10+0.10+0.15+0.15+0.15+0.10+0.10+0.05 = **1.00**.

New score cap added: **Cap 0.50 — Wrong-owner attribution at scale**
(≥4 wrong owners). Existing caps unchanged. `success_threshold`
unchanged (0.90). `services/task-setup/install.sh` unchanged — ffmpeg
+ yt-dlp/srt deps still appropriate for the in-container executor
who will use the declared multimedia skills.

GT (`ground_truth.json`) replaced wholesale with new schema-`a` block
including `expected_decisions`, `expected_action_items_with_owners`,
`expected_specific_dates`, `expected_topic_timestamps`,
`controversial_decisions`, and updated
`transcript_anchor_phrases` (24 phrases, `min_anchor_hits = 16`).

## Compliance fix (2026-04-30)
- Removed prompt rubric leakage (keyword enumerations).
- Tightened all completeness CPs to strict (no second-tier credit).

## Known issues (2026-05-02)
- `sources/slides/slide_10.png` (action-items recap slide) renders the
  count as "9 action items" but the ground truth lists 11 action items
  (matching the audio recap in `meeting.mp4`). No rasterizer source
  (SVG / mermaid / render script) is shipped alongside the PNG, so a
  surgical re-render is not possible without re-authoring the slide
  pipeline. Eval is unaffected: the rubric grades action-item
  capture from the audio transcript via
  `expected_action_items_with_owners`, and the slide count is not a
  scored anchor. Re-render the slide with the correct count next time
  the slide pipeline is touched.
