# Hidden Evaluation Rule — Exploration v2 · NASA image crop → canonical NASA record (visual provenance)

## 1. Grading Philosophy

A **content-provenance** task graded by **correct canonical identification plus
a primary-source evidence chain**. The executor gets only a cropped detail of an
astronomy image — no caption. The crop has no searchable text, so the executor
must **visually identify** the object (an edge-on galaxy with a bright bulge and
dark dust lane — the "sombrero" shape) and trace it to **NASA's own image
record**, not a blog/news reproduction.

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/crop.jpg`, identify the astronomical
object, the NASA telescope/instrument, the NASA image id + canonical NASA record
URL, and the release date. Save `image_provenance.json` with conclusion +
evidence chain.

## 3. Ground-Truth Reference

- **Object:** the **Sombrero Galaxy** (Messier 104 / M104 / NGC 4594)
- **Image:** "The Sombrero Galaxy Split Personality", **Spitzer Space Telescope**
  (infrared), NASA center **JPL**
- **NASA id:** **PIA15426**, released **2012-04-24**
- **Canonical URLs:** `https://images.nasa.gov/details/PIA15426`,
  `https://images-api.nasa.gov/asset/PIA15426`, or JPL Photojournal
  `https://photojournal.jpl.nasa.gov/catalog/PIA15426`

## 4. Expected Artifacts

- `/tmp_workspace/results/image_provenance.json` — object, telescope, NASA id,
  canonical URL, date, and identification evidence.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct object identified: the Sombrero Galaxy / M104 (from the image).                                            | 0.35   |
| CP2 | Canonical NASA record reached (NASA image library / images-api / JPL Photojournal), not a secondary reproduction.  | 0.30   |
| CP3 | NASA image id `PIA15426` reported (the specific record this crop is from); Spitzer/infrared + JPL noted.           | 0.20   |
| CP4 | Evidence chain shows how it was identified and links the canonical source; release date noted.                     | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the final canonical pointer is a secondary reproduction
  (Wikipedia / news / astro-blog) and no NASA-owned record is reached.
- **cap at `0.50`** if the object is misidentified (not M104).
- **cap at `0.70`** if M104 is correctly identified but no NASA image id /
  canonical NASA URL is provided.
- **cap at `0.80`** if M104 is right and a NASA-owned page is reached, but it is a
  different M104 image record (NASA has several) rather than PIA15426 — right
  object, not the exact record this crop is from.

Do **not** cap or fail merely because:

- the executor used reverse-image/visual identification (intended method),
- the object name is given as M104 / Messier 104 / NGC 4594 (all accepted),
- Wikipedia is used as a stepping stone but the executor lands on the NASA record.

Pass requirements (`score >= 0.90`): CP1 (Sombrero/M104), CP2 (NASA canonical
record), CP3 (PIA15426), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the object is identified but the NASA record isn't yet
traced, or only a reproduction is reached.

Prefer `fail` when the object is misidentified, or only a secondary reproduction
is ever cited.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical record + crop origin. Supervisor-only.

## 9. Dynamic Content Note

Object identity + NASA record are stable. Grade against the executor's captured
evidence pointing to NASA's own record for PIA15426.

## 10. Notes For Rationale

- When capping at 0.55, name the reproduction the executor stopped at.
- Guidance tags: `visual_identification_no_text`, `primary_source_nasa_record`,
  `specific_image_id_PIA15426`, `reproduction_is_secondary`.
