# Hidden Evaluation Rule — Exploration v2 · Museum artifact crop → canonical museum record (visual provenance)

## 1. Grading Philosophy

A **content-provenance** task graded by **correct canonical identification plus
a primary-source evidence chain**. The executor gets only a cropped detail of a
museum object — no label. The crop has no searchable text, so the executor must
**visually identify** it (a Greek Attic black-figure amphora — galloping
horses/chariot in black silhouette on orange terracotta) and trace it to the
**museum's own catalog record**, not a third-party reproduction.

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/crop.jpg`, identify the object (type,
culture/period, technique), approximate date, holding museum + object id /
accession + canonical museum URL. Save `artifact_provenance.json` with
conclusion + evidence chain.

## 3. Ground-Truth Reference

- **Object:** **Terracotta Panathenaic prize amphora (jar)**
- **Culture:** Greek, Attic — **black-figure**
- **Date:** ca. **510 BCE**
- **Holding institution:** **The Metropolitan Museum of Art (The Met)**
- **Met object id:** **247960**, **accession 07.286.80**, Dept Greek and Roman Art
- **Canonical URLs:** `https://www.metmuseum.org/art/collection/search/247960`,
  Met API `https://collectionapi.metmuseum.org/public/collection/v1/objects/247960`

## 4. Expected Artifacts

- `/tmp_workspace/results/artifact_provenance.json` — object type, culture/date,
  museum + object id/accession + canonical URL, identification evidence.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                          | Weight |
| --- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct identification: an Attic Greek black-figure (Panathenaic) amphora (from the image).                        | 0.35   |
| CP2 | Canonical Met catalog record reached (Met page / Met Collection API), not a third-party reproduction.              | 0.30   |
| CP3 | Met object id `247960` and/or accession `07.286.80` reported (the specific record this crop is from).              | 0.20   |
| CP4 | Evidence chain shows how it was identified and links the canonical source; period (~510 BCE / Attic) noted.        | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the final canonical pointer is a secondary reproduction
  (Wikipedia / stock / auction) and the Met's own record is never reached.
- **cap at `0.50`** if misidentified (not a Greek black-figure amphora — e.g.
  called Roman, or a different vessel type entirely).
- **cap at `0.70`** if correctly typed as an Attic black-figure amphora but no
  Met object id / accession / canonical Met URL is provided.
- **cap at `0.80`** if typed correctly and a museum record is reached but it is a
  different amphora record than Met 247960 — right type, wrong specific object.

Do **not** cap or fail merely because:

- the executor used reverse-image/visual identification (intended method),
- the object is described as "Panathenaic amphora" / "Attic black-figure amphora"
  (both accepted),
- Wikipedia is a stepping stone but the executor lands on the Met record.

Pass requirements (`score >= 0.90`): CP1 (Attic black-figure amphora), CP2 (Met
canonical record), CP3 (Met 247960 or accession), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when typed correctly but the Met record isn't yet traced, or
only a reproduction is reached.

Prefer `fail` when misidentified, or only a secondary reproduction is ever cited.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical record + crop origin. Supervisor-only.

## 9. Dynamic Content Note

Object identity + Met record are stable. Grade against captured evidence pointing
to the Met's own record for object 247960.

## 10. Notes For Rationale

- When capping at 0.55, name the reproduction the executor stopped at.
- Guidance tags: `visual_identification_no_text`, `primary_source_museum_record`,
  `specific_object_id_247960`, `reproduction_is_secondary`.
