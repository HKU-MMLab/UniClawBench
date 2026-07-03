# Hidden Evaluation Rule — Exploration v2 · Bilingual academic-lab Hugo theme selection (conflicting feature requirements)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective feature-coverage
matching plus the correct pick**.

The pool is six real Hugo themes shipped offline, with feature flags normalized
from their real upstream `theme.toml` manifests (also shipped under
`raw_theme_manifests/`). The use case needs THREE features together
(multilingual + team-members + publications); **only one candidate has all
three**. The decoys are deliberate: one theme has "Academic" in its name
(`academic_cv`) but is a single-person CV with no team system; the most popular
theme (`papermod`) has neither members nor publications. Every candidate is
multilingual + MIT, so i18n and license do NOT discriminate — an executor that
justifies its pick on those alone has not done the real comparison.

Offline + frozen → deterministic answer key (`ground_truth.json`).

## 2. Task Contract

Pick one Hugo theme for a bilingual (EN+ZH) research-LAB site needing a
team/people system and a publications list, free static hosting, permissive
license. Pool at `/tmp_workspace/clawbench/sources/theme_candidates/`
(`candidates.json` + raw `theme.toml` manifests). Save `theme_choice.json`,
`theme_evaluation.json`, `theme_method.json`. Offline.

## 3. Ground-Truth Reference (answer key)

Hard requirements: HR1 multilingual, HR2 team-members system, HR3 publications
system, HR4 static + permissive license.

| theme | multilingual | team_members | publications | permissive | hard pass | missing |
| ----- | ------------ | ------------ | ------------ | ---------- | --------- | ------- |
| **research_group** | ✓ | ✓ | ✓ | ✓ | **PASS** | — |
| academic_cv | ✓ | ✗ | ✓ | ✓ | FAIL | HR2 (single-person CV) — NAME TRAP |
| papermod | ✓ | ✗ | ✗ | ✓ | FAIL | HR2+HR3 — POPULARITY TRAP |
| ananke | ✓ | ✗ | ✗ | ✓ | FAIL | HR2+HR3 |
| hugo_book | ✓ | ✗ | ✗ | ✓ | FAIL | HR2+HR3 |
| terminal | ✓ | ✗ | ✗ | ✓ | FAIL | HR2+HR3 |

- **Only survivor / gold: `research_group`** (Hugo Blox Research Group) — the
  only theme with team-members AND publications AND i18n. No tie-break needed.
- **Key discriminators: HR2 (team-members) and HR3 (publications)** — NOT i18n or
  license (all candidates share those).

## 4. Expected Artifacts

- `/tmp_workspace/results/theme_choice.json`
- `/tmp_workspace/results/theme_evaluation.json`
- `/tmp_workspace/results/theme_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                               | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| CP1 | Final pick is **research_group**, justified by it covering all four hard requirements (esp. team-members + publications).               | 0.35   |
| CP2 | Per-candidate evaluation correctly maps feature coverage and names the failing hard requirement for each rejected theme.                | 0.20   |
| CP3 | The NAME trap is caught: academic_cv rejected specifically for lacking a team/members system (HR2), not for some wrong reason.          | 0.20   |
| CP4 | The POPULARITY trap is caught: papermod rejected for lacking members AND publications, not chosen for being popular/fast.               | 0.15   |
| CP5 | Evaluation is evidence-based (theme.toml feature lists / shipped manifests cited), not asserted; method is reproducible.                | 0.10   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick is justified only by i18n/license/popularity
  (the non-discriminating attributes) with no team-members/publications analysis.
- **cap at `0.55`** if `theme_choice.json` or `theme_evaluation.json` is missing.
- **cap at `0.60`** if a theme missing a hard requirement is the final pick
  (academic_cv, papermod, ananke, hugo_book, terminal).
- **cap at `0.70`** if academic_cv is rejected for the WRONG reason (e.g. claimed
  it has no publications — it does have publications; the real gap is the team
  system) — diagnosing WHY the name-trap fails is a discriminator.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- the executor also notes nice-to-have differences (events/talks, search) beyond
  the hard set,
- the executor reads the raw `theme.toml` and reaches the same coverage by its
  own normalization (encouraged),
- the executor proposes a fallback/runner-up as long as the primary pick is
  research_group.

Pass requirements (`score >= 0.90`): CP1 (research_group), CP2, CP3 and CP4
(both traps caught for the right reason), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has read manifests and built partial coverage
but hasn't finalized the pick or named the failing requirement per theme.

Prefer `fail` when, after follow-ups, the pick is a non-covering theme with no
recovery, or the justification is purely popularity/i18n with no feature
analysis.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — feature coverage + correct pick.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic. (Upstream themes evolve, but the
shipped manifests are the ground truth for this task.)

## 10. Notes For Rationale

- When scoring CP3, quote the executor's rejection reason for academic_cv and
  confirm it cites the missing team/members system.
- When capping at 0.45, note that the justification used only i18n/license/
  popularity (attributes all candidates share).
- Guidance tags: `feature_coverage_selection`, `name_is_a_trap`,
  `popularity_is_a_trap`, `non_discriminating_attributes`, `evidence_from_manifests`.
