# Hidden Evaluation Rule — Exploration v2 · Historic photo crop → canonical archive record (visual provenance)

## 1. Grading Philosophy

A **content-provenance** task graded by **correct canonical identification plus
a primary-source evidence chain**. The executor gets only a cropped detail of a
historic photograph — no caption/credit. The crop has no searchable text (the
small `+` marks are Hasselblad réseau fiducial crosses, a clue it is a NASA
lunar-surface photo). The executor must **visually identify** it and trace it to
the **source archive's own record**, not a Wikipedia/news copy.

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/crop.jpg`, identify what the photo
depicts, the date, the holding archive + its canonical record + the photo's
archive id, and the photographer. Save `photo_provenance.json` with conclusion +
evidence chain.

## 3. Ground-Truth Reference

- **Subject:** astronaut **Buzz Aldrin** on the lunar surface near the Lunar
  Module "Eagle"
- **Mission:** **Apollo 11**, **1969-07-20**
- **Photographer:** Neil Armstrong
- **Archive id (NASA):** **as11-40-5903**, NASA center JSC
- **Canonical URLs:** `https://images.nasa.gov/details/as11-40-5903`,
  `https://images-api.nasa.gov/asset/as11-40-5903`, or the official NASA/JSC
  Apollo 11 image archive entry for this frame.

## 4. Expected Artifacts

- `/tmp_workspace/results/photo_provenance.json` — subject, date, archive +
  canonical record + archive id, photographer, identification evidence.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct identification: an Apollo 11 lunar-surface EVA photo of Buzz Aldrin, July 1969 (from the image).           | 0.35   |
| CP2 | Canonical NASA archive record reached (NASA image library / images-api / NASA Apollo archive), not a reproduction. | 0.30   |
| CP3 | NASA archive id `as11-40-5903` reported (the specific frame this crop is from).                                    | 0.20   |
| CP4 | Evidence chain shows how it was identified and links the canonical source; date `1969-07-20` noted.                | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the final canonical pointer is a secondary reproduction
  (Wikipedia / news) and no NASA-owned archive record is reached.
- **cap at `0.50`** if misidentified (not Apollo 11 / not a Moon EVA photo).
- **cap at `0.70`** if identified as Apollo 11 Aldrin but no NASA archive id /
  canonical NASA URL is provided.
- **cap at `0.80`** if it is identified as Apollo 11 Aldrin and a NASA record is
  reached, but a different Apollo 11 frame id than `as11-40-5903` is cited —
  right event, not the exact frame this crop is from.

Do **not** cap or fail merely because:

- the executor used reverse-image/visual identification (intended method),
- the executor notes the well-known "visor portrait" association — as long as the
  reported frame matches this crop's identity and a NASA record is reached,
- Wikipedia is a stepping stone but the executor lands on the NASA record.

Pass requirements (`score >= 0.90`): CP1 (Apollo 11 Aldrin), CP2 (NASA canonical
record), CP3 (as11-40-5903), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when identified but the NASA record isn't yet traced, or only a
reproduction is reached.

Prefer `fail` when misidentified, or only a secondary reproduction is ever cited.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical record + crop origin. Supervisor-only.

## 9. Dynamic Content Note

Identity + NASA record are stable. Grade against captured evidence pointing to
NASA's own record for as11-40-5903.

## 10. Notes For Rationale

- When capping at 0.55, name the reproduction the executor stopped at.
- Guidance tags: `visual_identification_no_text`, `primary_source_nasa_archive`,
  `specific_frame_id`, `reproduction_is_secondary`.
