# Hidden Evaluation Rule — Exploration v2 · Offline LoC-style rights-image selection (item-level rights + dedup, objective)

## 1. Grading Philosophy

This is a **candidate-selection / filtering** task graded by **objective set
matching plus correct trap diagnosis**.

It is the offline, complexified successor to the v1 live-LoC rights-images task
(scored ~0.72, depended on live pages). The catalog is shipped and frozen, so
the answer is deterministic. The four rules each have a trap: collection-level
rights can mask an item-level restriction, thumbnails masquerade as available
images, non-image media (text/sound) carry scans, and the same image is
catalogued under multiple records. **Exactly five** distinct usable images
exist.

## 2. Task Contract

Select 5 distinct usable images where: item-level rights are open ('No known
restrictions'/'Public domain'), a full image is available (not thumbnail), the
item is a photograph (not text/sound), and duplicates (shared `dedup_group`) are
collapsed. Catalog at `/tmp_workspace/clawbench/sources/records/`. Save
`usable_images.json`, `rejected_records.json`, `selection_method.json`. Offline.

## 3. Ground-Truth Reference (answer key)

**Five usable dedup groups, canonical ids: {R01, R03, R06, R08, R10}.**

Duplicate equivalences (either id of a pair is acceptable, but NOT both):
- g_migrant_mother: **R01** ≡ R02
- g_brooklyn_bridge: **R03** ≡ R11

| id | verdict | reason |
| -- | ------- | ------ |
| R01 | USABLE | photograph, item rights open, full image — Migrant Mother |
| R02 | DUP of R01 | same image (g_migrant_mother) |
| R03 | USABLE | photograph, public domain, full image — Brooklyn Bridge |
| R04 | REJECT | thumbnail only (full_image=false) |
| R05 | REJECT | item_rights RESTRICTED (collection open but item-level wins) |
| R06 | USABLE | Coney Island |
| R07 | REJECT | not an image (manuscript_text) |
| R08 | USABLE | Grand Central |
| R09 | REJECT | rights undetermined/advisory |
| R10 | USABLE | Lincoln Memorial |
| R11 | DUP of R03 | same image (g_brooklyn_bridge) |
| R12 | REJECT | not an image (sound_recording) + no full image |

**Key tests:** R05 (item-vs-collection rights), R02/R11 (dedup), R07/R12 (media
type), R04 (thumbnail-only).

Acceptable selection = exactly 5 records, **one per usable group**; picking both
R01+R02 or both R03+R11 is a dedup failure.

## 4. Expected Artifacts

- `/tmp_workspace/results/usable_images.json`
- `/tmp_workspace/results/rejected_records.json`
- `/tmp_workspace/results/selection_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | The selection is exactly 5 distinct usable images, one per usable dedup group (canonical {R01,R03,R06,R08,R10}, dup-substitution allowed). | 0.35   |
| CP2 | No trap record (R04/R05/R07/R09/R12) is included, and no dedup pair has both halves selected.                                    | 0.25   |
| CP3 | The item-vs-collection rights test (R05) is handled correctly — rejected for item-level restriction despite open collection rights. | 0.15   |
| CP4 | Each rejection cites the correct specific trap; duplicates are labeled as duplicate-of-<id>.                                      | 0.15   |
| CP5 | Method artifact shows the rights-authority + dedup rules applied (reproducible).                                                  | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.55`** if any trap record is included in the selection, OR both
  halves of a dedup pair are selected (the core failures).
- **cap at `0.55`** if `usable_images.json` is missing.
- **cap at `0.65`** if R05 is accepted (read collection-level rights instead of
  item-level) — the central rights trap.
- **cap at `0.70`** if the selection is the right idea but wrong count (≠5
  distinct groups) — e.g. 4 usable + 1 trap, or 5 but with a dup pair.
- **cap at `0.75`** if the selection is correct but rejections lack specific
  per-record trap reasons.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- the executor picks R02 instead of R01, or R11 instead of R03 (either member of
  a dedup group is fine),
- the executor orders the selection differently or adds extra evidence fields,
- the executor uses python/jq to filter — any real per-record evaluation is fine.

Pass requirements (`score >= 0.90`): CP1 (exact 5 distinct groups), CP2 (no
trap/dup), CP3 (R05 handled), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has evaluated some records but not all, or has
the selection but incomplete rejection reasons / unresolved dedup.

Prefer `fail` when, after follow-ups, the selection includes traps or dup pairs
with no correction, or rights were judged from collection-level only.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — usable groups, dedup pairs, per-record traps.

## 9. Dynamic Content Note

None — frozen offline catalog; deterministic answer set.

## 10. Notes For Rationale

- When capping at 0.65 for R05, confirm whether the executor cited item-level vs
  collection-level rights.
- When scoring CP2, name any included trap or both-halves-of-a-dup-pair error.
- Guidance tags: `exact_set_selection`, `item_rights_over_collection`,
  `thumbnail_not_full_image`, `media_type_must_be_image`, `dedup_shared_group`,
  `offline_deterministic`.
