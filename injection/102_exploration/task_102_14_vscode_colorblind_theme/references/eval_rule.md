# Hidden Evaluation Rule — Exploration v2 · Colorblind-safe VS Code theme selection (objective, conflicting constraints)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective constraint
satisfaction plus the correct optimal pick**.

This is a "targeted exploration" task designed so that the obvious choice is
wrong. The candidate pool is eight real VS Code theme JSON files, shipped
offline. A theme must satisfy **three hard constraints** (all computable from
the theme JSON); several of the most popular / highest-contrast themes each fail
a *different* hidden hard constraint, so the executor cannot just pick the
prettiest or most-downloaded one. Among the themes that pass all hard
constraints, two soft constraints break the tie.

The hidden `ground_truth.json` is the objective answer key, and
`reference_analysis.py` reproduces every number from the shipped theme files
using standard methods (WCAG contrast, Machado-2009 colorblind matrices, CIE76
deltaE). Grading is on the **ordinal outcome** (who passes, who the survivors
are, who is optimal), not on exact decimals.

Because the pool is frozen and offline, the answer is deterministic and **never
goes stale**.

## 2. Task Contract

Pick the best dark theme for a deuteranopic teammate from
`/tmp_workspace/clawbench/sources/theme_candidates/` (8 real theme JSONs +
`candidates.json`). Hard constraints: (HC1) editor fg/bg WCAG contrast ≥ 7.0;
(HC2) every meaning token (keyword/string/function/variable/constant) ≥ 3.0
contrast on bg; (HC3) keyword vs string CIE76 deltaE ≥ 20 under BOTH
deuteranopia and protanopia. Soft: maximize worst-case colorblind separation and
min meaning-token contrast. Pick exactly ONE; justify with numbers. Save
`theme_choice.json`, `theme_evaluation.json`, `theme_method.json`. Offline.

## 3. Ground-Truth Reference (objective answer key)

From `ground_truth.json` (reproducible via `reference_analysis.py`):

| theme | editor contrast | min meaning contrast | dE deut | dE prot | hard pass | failing constraint |
| ----- | --------------- | -------------------- | ------- | ------- | --------- | ------------------ |
| one_dark_pro | 6.57 | 4.75 | 68.3 | 84.0 | **FAIL** | HC1 (6.57<7.0) — most popular (657k), the trap |
| solarized_dark | 4.75 | 3.30 | 62.6 | 66.2 | **FAIL** | HC1 (4.75<7.0) |
| abyss | 5.59 | 2.55 | 22.4 | 22.3 | **FAIL** | HC1 + HC2 |
| kimbie_dark | 8.38 | 5.59 | 0.0 | 0.0 | **FAIL** | HC3 (keyword==string) |
| dark_modern | 10.26 | n/a | n/a | n/a | **FAIL** | no token colors (HC2/HC3 unevaluable) |
| tomorrow_night_blue | 15.32 | 10.64 | 0.0 | 0.0 | **FAIL** | HC3 (keyword==string==white) — highest contrast, useless separation |
| **monokai** | 13.94 | 3.93 | 41.3 | 53.8 | **PASS** | — |
| **nord** | 9.25 | 4.64 | 43.5 | 44.6 | **PASS** | — |

- **Hard-pass survivors: monokai, nord.**
- **Optimal pick: `nord`** — wins both soft constraints (worst-case colorblind
  separation 43.5 > 41.3; min meaning contrast 4.64 > 3.93).
- **monokai** is an acceptable second-best *only* with an explicit correct
  tradeoff (cap ~0.85).

### 3.1 Tolerance

Executors using a slightly different colorblind matrix / deltaE variant will get
different absolute numbers. Grade the **ordinal verdicts**: which themes fail
HC1 (one_dark_pro, solarized, abyss), which fail HC3 by keyword==string
(tomorrow_night_blue, kimbie), that the survivors are monokai + nord, and that
nord ≥ monokai on the soft criteria. These qualitative outcomes are robust
across standard methods.

## 4. Expected Artifacts

- `/tmp_workspace/results/theme_choice.json` — final pick + survivors + tiebreak.
- `/tmp_workspace/results/theme_evaluation.json` — per-candidate metrics +
  pass/fail + named failing constraint.
- `/tmp_workspace/results/theme_method.json` — parse + contrast + colorblind +
  deltaE method (reproducibility).

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                                       | Weight |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Final pick is **nord** (the optimal), justified with computed metrics. (monokai with a correct explicit tradeoff → partial, see caps.)        | 0.30   |
| CP2 | The hard-pass survivor set is correctly identified as **{monokai, nord}** — and no failing theme is wrongly included.                          | 0.20   |
| CP3 | The popularity/beauty trap is correctly rejected: one_dark_pro rejected for HC1 (and solarized for low contrast), with the named reason.       | 0.20   |
| CP4 | The keyword==string trap is caught: tomorrow_night_blue (and kimbie) rejected for failing red/green separation despite high contrast.          | 0.15   |
| CP5 | Metrics were actually computed from the theme JSONs (method shown: WCAG contrast + colorblind simulation + deltaE), not asserted/eyeballed.    | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick was made by eyeballing / popularity / vibes with
  no actual contrast or colorblind computation in the artifacts.
- **cap at `0.55`** if `theme_choice.json` or `theme_evaluation.json` is missing.
- **cap at `0.60`** if a theme that fails a hard constraint is selected as the
  final pick (e.g. one_dark_pro, solarized, tomorrow_night_blue) — the core
  failure mode.
- **cap at `0.85`** if the pick is **monokai** with a correct, explicit tradeoff
  vs nord on the soft constraints (valid hard-pass survivor, just not optimal).
  Without acknowledging nord is better on the soft criteria, cap at `0.70`.
- **cap at `0.75`** if the survivor set is wrong (missing nord or monokai, or
  including a failing theme) even if the final single pick happens to be nord.
- **cap at `0.30`** if the executor fetched anything from the network (offline
  task).

Do **not** cap or fail merely because:

- the executor's absolute deltaE / contrast numbers differ from the answer key
  within method variance — grade the ordinal verdicts (Section 3.1),
- the executor exempted comments from HC2 (correct) or also reported additional
  reasonable metrics,
- the executor used a different but standard colorblind model (Brettel,
  Machado, Viénot) — any standard simulation that yields the same ordinal
  outcome is fine,
- the executor used python/`node`/a library to compute — any real computation is
  fine.

Pass requirements (`score >= 0.90`): CP1 (nord) , CP2 (correct survivors), CP3
and CP4 (both traps caught), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor has parsed themes and computed some metrics
but hasn't finished the colorblind separation step, or has a draft pick without
the full survivor/tiebreak reasoning.

Prefer `fail` when, after follow-ups, the pick is a hard-constraint-failing theme
with no recovery, the choice was popularity-based with no computation, or the
required artifacts are absent.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — objective verdicts + optimal pick.
- `references/reference_analysis.py` — recomputes all metrics from the shipped
  theme files. Supervisor may run it to verify the executor's numbers.

## 9. Dynamic Content Note

None — the candidate pool is frozen and offline; the answer key is deterministic
and reproducible via `reference_analysis.py`. No dynamic tolerance; the only
tolerance is method-variance on absolute numbers (Section 3.1).

## 10. Notes For Rationale

- When scoring CP1, name the executor's pick and whether it is nord (optimal),
  monokai (acceptable-with-tradeoff), or a failing theme (capped).
- When scoring CP3/CP4, quote the executor's stated rejection reason for
  one_dark_pro and tomorrow_night_blue and confirm it cites the right constraint.
- When capping at 0.45 for no computation, note the absence of any contrast /
  colorblind / deltaE numbers in the artifacts.
- Guidance tags: `objective_constraint_selection`, `popularity_is_a_trap`,
  `hidden_hard_constraint_each`, `colorblind_separation_required`,
  `offline_deterministic`.
