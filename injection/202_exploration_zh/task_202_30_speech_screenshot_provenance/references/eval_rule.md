# Hidden Evaluation Rule — Exploration v2 · Speech screenshot → canonical original video (visual provenance)

## 1. Grading Philosophy

A **content-provenance** task graded by **correct identification plus reaching
the canonical ORIGINAL source**. The executor gets a single video frame with no
caption, channel watermark, or on-screen title. They must **visually identify**
the speaker + occasion and trace it to the **official original video**, not a
re-upload, clip channel, or news article. The discriminator is "primary/official
source vs the many secondary re-uploads".

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/screenshot.jpg`, identify the speaker +
event + date, link the canonical original video (official channel/institution),
and the official transcript if available. Save `video_provenance.json` with
conclusion + evidence chain.

## 3. Ground-Truth Reference

- **Speaker:** **Steve Jobs**
- **Occasion:** **Stanford University 2005 Commencement Address** ("Stay Hungry.
  Stay Foolish."), **2005-06-12**
- **Canonical video:** `https://www.youtube.com/watch?v=UF8uR6Z6KLc`, published
  by the **official Stanford** YouTube channel; title "Steve Jobs' 2005 Stanford
  Commencement Address"
- **Also acceptable canonical:** Stanford's own published transcript/page
  (news.stanford.edu) for the 2005 commencement address.

## 4. Expected Artifacts

- `/tmp_workspace/results/video_provenance.json` — speaker, event, date,
  canonical video URL + official publisher, transcript if found, evidence chain.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct identification: Steve Jobs, Stanford 2005 Commencement Address (from the frame).                           | 0.35   |
| CP2 | Canonical ORIGINAL reached: the official Stanford upload (YouTube UF8uR6Z6KLc) or Stanford's own transcript page.   | 0.35   |
| CP3 | Correct date (2005) and the official publisher named (Stanford), distinguishing it from re-uploads/clips.          | 0.15   |
| CP4 | Evidence chain shows how the speaker/occasion was identified and how the canonical original was traced.            | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the executor identifies it correctly but only links a
  non-official re-upload / clip channel / news article, never the official
  Stanford source.
- **cap at `0.50`** if the speaker or occasion is misidentified.
- **cap at `0.75`** if speaker + occasion are right and an official source is
  reached but the wrong/again-secondary video link is given as "the original".

Do **not** cap or fail merely because:

- the executor used reverse-image search / visual ID (intended method),
- the executor cites the Stanford transcript page instead of the video as the
  canonical (both accepted),
- a re-upload is mentioned as a stepping stone but the official source is the
  final answer.

Pass requirements (`score >= 0.90`): CP1 (Jobs/Stanford 2005), CP2 (official
Stanford original), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when identified but only a re-upload is found so far.
Prefer `fail` when misidentified, or only secondary re-uploads are ever cited.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical video + frame origin. Supervisor-only.

## 9. Dynamic Content Note

The speech identity + official Stanford source are stable. Grade against the
executor's captured evidence pointing to the official Stanford upload/transcript.

## 10. Notes For Rationale

- When capping at 0.55, name the re-upload/clip the executor stopped at.
- Guidance tags: `visual_identification_no_text`, `official_original_video`,
  `reupload_is_secondary`, `speech_provenance`.
