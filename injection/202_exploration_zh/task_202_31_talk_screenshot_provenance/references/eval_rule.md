# Hidden Evaluation Rule — Exploration v2 · Talk screenshot → canonical original video (visual provenance)

## 1. Grading Philosophy

A **content-provenance** task graded by **correct identification plus reaching
the canonical ORIGINAL source**. The executor gets a single talk video frame
with no caption/channel/title. They must **visually identify** the speaker + talk
and trace it to the **official original video**, not a re-upload, clip channel,
or summary.

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/screenshot.jpg`, identify the speaker +
talk title + venue/year, and link the canonical original video + official
publisher/talk page. Save `talk_provenance.json` with conclusion + evidence chain.

## 3. Ground-Truth Reference

- **Speaker:** **Sir Ken Robinson**
- **Talk:** **"Do schools kill creativity?"**, **TED** (TED2006)
- **Canonical video:** `https://www.youtube.com/watch?v=iG9CE55wbtY`, published by
  the **official TED** YouTube channel
- **Also acceptable canonical:** the official TED.com talk page for "Sir Ken
  Robinson: Do schools kill creativity?".
- Context: this is among the most-viewed TED talks, so identification from the
  frame + reverse image search is feasible.

## 4. Expected Artifacts

- `/tmp_workspace/results/talk_provenance.json` — speaker, talk title,
  venue/year, canonical video URL + official publisher/talk page, evidence chain.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct identification: Sir Ken Robinson, "Do schools kill creativity?" (from the frame).                          | 0.35   |
| CP2 | Canonical ORIGINAL reached: the official TED upload (YouTube iG9CE55wbtY) or the official TED.com talk page.        | 0.35   |
| CP3 | Venue (TED) and the official publisher named, distinguishing it from re-uploads/clips/summaries.                   | 0.15   |
| CP4 | Evidence chain shows how the speaker/talk was identified and how the canonical original was traced.                | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if identified correctly but only a non-official re-upload /
  clip / summary is linked, never the official TED source.
- **cap at `0.50`** if the speaker or talk is misidentified.
- **cap at `0.75`** if speaker + talk are right and an official TED source is
  reached but a secondary link is given as "the original".

Do **not** cap or fail merely because:

- the executor used reverse-image search / visual ID (intended method),
- the executor cites the TED.com talk page instead of the YouTube video (both
  accepted),
- a re-upload is a stepping stone but the official TED source is the final answer.

Pass requirements (`score >= 0.90`): CP1 (Robinson / "Do schools kill
creativity?"), CP2 (official TED original), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when identified but only a re-upload is found so far.
Prefer `fail` when misidentified, or only secondary re-uploads are ever cited.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical video + frame origin. Supervisor-only.

## 9. Dynamic Content Note

The talk identity + official TED source are stable. Grade against the executor's
captured evidence pointing to the official TED upload/talk page.

## 10. Notes For Rationale

- When capping at 0.55, name the re-upload/clip the executor stopped at.
- Guidance tags: `visual_identification_no_text`, `official_original_video`,
  `reupload_is_secondary`, `talk_provenance`.
