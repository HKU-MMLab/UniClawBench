# Hidden Evaluation Rule — Exploration v2 · Museum/archive exhibit template selection (required metadata schema + features)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective schema/feature
coverage plus the correct pick**.

The pool is six digital-exhibit templates shipped offline, each with a manifest
declaring its item-metadata schema fields and features. The use case has
**archival hard requirements** (four provenance fields + timeline + IIIF) that
the prettiest templates fail: a stunning gallery and a gorgeous scrollytelling
timeline each lack required provenance fields (rights/accession), while the
full-metadata templates lack a timeline. **Only one template** has the complete
provenance schema AND a timeline AND IIIF.

Offline + frozen → deterministic answer key (`ground_truth.json`).

## 2. Task Contract

Pick one exhibit template for a museum photo exhibition requiring: item fields
caption + credit + rights + accession_number; features timeline + IIIF large
images. Pool at `/tmp_workspace/clawbench/sources/template_candidates/` (per-
template manifests + index.json). Save `template_choice.json`,
`template_evaluation.json`, `template_method.json`. Offline.

## 3. Ground-Truth Reference (answer key)

Required fields: caption, credit, rights, accession_number. Required features:
timeline, iiif_large_images.

| template | all 4 fields | timeline | IIIF | hard pass | missing |
| -------- | ------------ | -------- | ---- | --------- | ------- |
| **collectionbuilder_archive** | ✓ | ✓ | ✓ | **PASS** | — |
| omeka_classic_exhibit | ✓ | ✗ | ✓ | FAIL | timeline (near-miss) |
| wax_minimal_archive | ✓ | ✗ | ✓ | FAIL | timeline (near-miss) |
| exhibit_timeline_story | ✗ | ✓ | ✗ | FAIL | rights, accession, IIIF (beauty trap) |
| photofolio_gallery | ✗ | ✗ | ✓ | FAIL | credit, rights, accession, timeline (beauty trap) |
| blogfolio_grid | ✗ | ✗ | ✗ | FAIL | almost everything |

- **Only survivor / gold: `collectionbuilder_archive`.**
- **Near-misses** omeka/wax (full provenance schema but no timeline) are
  acceptable ONLY with an explicit identified gap + concrete fix (e.g. Neatline
  for Omeka) → cap ~0.85.
- **Discriminator: the provenance fields (rights + accession + credit)** that the
  pretty templates lack, plus the timeline that the full-metadata ones lack.

## 4. Expected Artifacts

- `/tmp_workspace/results/template_choice.json`
- `/tmp_workspace/results/template_evaluation.json`
- `/tmp_workspace/results/template_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Final pick is **collectionbuilder_archive**, justified by full provenance schema + timeline + IIIF (cite the manifest).          | 0.35   |
| CP2 | Per-template evaluation correctly maps the 4 fields + 2 features and names the failing requirement(s) for each rejected template. | 0.20   |
| CP3 | The BEAUTY traps are caught: photofolio_gallery and exhibit_timeline_story rejected specifically for missing provenance fields (rights/accession), not vibes. | 0.20   |
| CP4 | The NEAR-MISS templates (omeka/wax) are correctly diagnosed as missing the timeline (not wrongly accepted as fully compliant).    | 0.15   |
| CP5 | Evaluation is evidence-based (manifest item_metadata_fields/features cited); reproducible method.                                 | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick is justified by appearance/feature-vibes with no
  field-by-field schema coverage analysis.
- **cap at `0.55`** if `template_choice.json` or `template_evaluation.json`
  missing.
- **cap at `0.60`** if a template missing a hard requirement is selected with no
  fix (photofolio, exhibit_timeline_story, blogfolio, or omeka/wax picked while
  ignoring the timeline gap).
- **cap at `0.70`** if a beauty trap (photofolio/exhibit_timeline_story) is
  rejected for the wrong reason (not citing the missing provenance fields).
- **cap at `0.85`** if the pick is omeka/wax WITH an explicit timeline-gap
  diagnosis and a concrete fix proposed (valid near-miss handling, just not the
  out-of-the-box answer).
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- the executor proposes the omeka/wax + timeline-plugin path as a reasoned
  alternative alongside picking collectionbuilder_archive,
- the executor notes extra nice-to-haves (map, search) beyond the hard set,
- the executor reaches the coverage by reading each manifest itself (encouraged).

Pass requirements (`score >= 0.90`): CP1 (collectionbuilder_archive), CP2, CP3
(beauty traps caught for the right reason), CP4 (near-miss diagnosed), no cap
fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has read manifests and built partial coverage
but hasn't finalized the pick or named the failing requirement per template.

Prefer `fail` when, after follow-ups, the pick is a non-covering template with no
fix, or the justification is appearance-based with no schema analysis.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — schema/feature coverage + correct pick.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic. The shipped manifests are the ground
truth.

## 10. Notes For Rationale

- When scoring CP3, quote the executor's rejection reason for photofolio_gallery
  and confirm it cites missing credit/rights/accession.
- When scoring CP4, confirm omeka/wax were flagged for the missing timeline.
- Guidance tags: `schema_coverage_selection`, `beauty_is_a_trap`,
  `provenance_fields_required`, `near_miss_needs_explicit_fix`,
  `offline_deterministic`.
