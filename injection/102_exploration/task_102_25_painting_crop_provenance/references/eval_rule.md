# Hidden Evaluation Rule — Exploration v2 · Painting crop → canonical museum record (visual provenance)

## 1. Grading Philosophy

This is a **content-provenance** task graded by **correct canonical
identification plus a primary-source evidence chain**.

The executor is given ONLY a cropped interior detail of a painting — no title,
signature, frame, or caption. The crop carries **no searchable text**, so the
task cannot be short-circuited by pasting a phrase into a search engine: the
executor must **visually identify** the artwork (the distinctive van Gogh
impasto sky + cypress) and then **trace it to the holding museum's own record**.

Grading rewards (a) the correct artwork + artist, and (b) reaching the
**canonical primary source** (the museum's catalog page / collection API), not
stopping at a Wikipedia/Pinterest/stock reproduction.

## 2. Task Contract

From `/tmp_workspace/clawbench/sources/crop.jpg`, identify the painting + artist
+ date, the holding museum, and its catalog/accession record (museum page or
API, not a third-party reproduction). Save `painting_provenance.json` with the
conclusion + the evidence chain (how identified + canonical museum URL).

## 3. Ground-Truth Reference

The crop is a pixel-derived interior detail of:

- **Title:** *Wheat Field with Cypresses* (accept "A Wheatfield, with Cypresses"
  / "Wheatfield with Cypresses")
- **Artist:** **Vincent van Gogh**
- **Date:** **1889**
- **Holding institution:** **The Metropolitan Museum of Art (The Met)**
- **Met object id:** **436535**
- **Accession number:** **1993.132**
- **Canonical URLs:** `https://www.metmuseum.org/art/collection/search/436535`
  and the Met API `https://collectionapi.metmuseum.org/public/collection/v1/objects/436535`
- Department: European Paintings; Medium: Oil on canvas; Public domain.

**Sibling-version note:** van Gogh painted several closely related "Wheat Field
with Cypresses" canvases (Met 1889; National Gallery London; a Saint-Rémy
study). The crop is from the **Met** version. Identifying the artwork + artist
is the core; the specific Met record (object id / accession / Met URL) is
required for full credit since the pixels come from the Met image.

## 4. Expected Artifacts

- `/tmp_workspace/results/painting_provenance.json` — title, artist, date,
  museum, object id / accession, canonical museum URL, and the identification
  evidence.

## 5. Checkpoint Rubric

| ID  | What matters (provenance)                                                                                                       | Weight |
| --- | --------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Correct artwork + artist identified: *Wheat Field with Cypresses* by Vincent van Gogh (from the image, not from text).         | 0.35   |
| CP2 | Correct holding institution (The Met) and the canonical museum record reached (Met page or Met Collection API), not a reproduction. | 0.30   |
| CP3 | Museum object id `436535` and/or accession `1993.132` reported (the specific Met record, disambiguating sibling versions).      | 0.20   |
| CP4 | Evidence chain shows HOW it was identified (visual reasoning / image search) and links the canonical source; date `1889` noted. | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if the final canonical pointer is a secondary reproduction
  (Wikipedia / WikiArt / Pinterest / stock photo) and the executor never reaches
  the holding museum's own record.
- **cap at `0.50`** if the artist is wrong (not van Gogh) — misidentification of
  the work.
- **cap at `0.75`** if the artwork + artist are right and a museum record is
  reached, but it is a **sibling version** (e.g. National Gallery London) rather
  than the Met version this crop is from — right family, wrong specific holding.
- **cap at `0.70`** if the artwork + artist are right but no museum object id /
  accession / canonical museum URL is provided at all (identification without
  provenance).

Do **not** cap or fail merely because:

- the executor used an image/reverse-image search or visual reasoning to
  identify it (that is the intended method),
- the executor cites Wikipedia as a *stepping stone* but ultimately lands on the
  Met record,
- the title is given in a minor variant spelling.

Pass requirements (`score >= 0.90`): CP1 (correct work + artist), CP2 (Met
canonical record), CP3 (Met object id or accession), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has identified the artwork but hasn't yet
traced it to the Met record, or reached a reproduction and is still looking for
the holding institution.

Prefer `fail` when, after follow-ups, the work/artist is misidentified, or the
executor only ever cites a secondary reproduction with no path to a museum
record.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — canonical record + crop origin + accepted
  variants. Supervisor-only.

## 9. Dynamic Content Note

The artwork identity and Met record are stable. Museum URLs/APIs may change
format over time; grade against the executor's captured evidence pointing to the
Met's own record for object 436535.

## 10. Notes For Rationale

- When capping at 0.55 (secondary source), name the reproduction the executor
  stopped at instead of the Met record.
- When capping at 0.75 (sibling version), name which version they landed on.
- Guidance tags: `visual_identification_no_text`, `primary_source_museum_record`,
  `disambiguate_sibling_versions`, `reproduction_is_secondary`.
