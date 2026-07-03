# Hidden Evaluation Rule — Exploration v2 · Colorblind + grayscale safe scientific palette (objective, conflicting constraints)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective constraint
satisfaction plus the correct optimal pick**.

The pool is nine real 5-color palettes shipped offline (`palettes.json`). Two
hard constraints conflict in a way that defeats reputation-based picking:

- the famous **jet/rainbow** palette has good color separation but dies in
  grayscale (the textbook "don't use rainbow" trap), and
- **Okabe-Ito**, the palette everyone reaches for when they hear "colorblind
  safe", passes the red-green test but **fails the grayscale/print
  requirement** here — an expert-knowledge trap.

Only **viridis** and **Paired** pass both hard constraints; **viridis** is
optimal on the soft tie-breakers. The hidden `ground_truth.json` +
`reference_analysis.py` reproduce every number from the shipped pool. Grade on
the **ordinal outcome**, not exact decimals. Offline + frozen → never stale.

## 2. Task Contract

Pick the best 5-color palette for a colorblind-readable AND grayscale-printable
scientific figure, from `/tmp_workspace/clawbench/sources/palettes.json`. Hard:
(HC1) min pairwise deltaE ≥ 15 under both deuteranopia and protanopia; (HC2) min
pairwise grayscale luminance separation ≥ 5 (0-100 scale). Soft: maximize
worst-case red-green separation, then grayscale separation. Pick ONE; justify
with numbers. Save `palette_choice.json`, `palette_evaluation.json`,
`palette_method.json`. Offline.

## 3. Ground-Truth Reference (objective answer key)

From `ground_truth.json` (reproducible via `reference_analysis.py`):

| palette | worst-case RG deltaE | grayscale min sep | hard pass | failing |
| ------- | -------------------- | ----------------- | --------- | ------- |
| jet | 24.6 | 1.6 | **FAIL** | HC2 grayscale — the rainbow trap |
| okabe_ito | 17.0 | 1.1 | **FAIL** | HC2 grayscale — the "CB-safe" expert trap |
| **viridis** | 19.4 | 6.9 | **PASS** | — |
| **Paired** | 16.6 | 6.3 | **PASS** | — |
| Set1 | 9.9 | 1.9 | **FAIL** | HC1 red-green |
| Dark2 | 5.8 | 1.8 | **FAIL** | HC1 |
| Accent | 2.8 | 1.8 | **FAIL** | HC1 |
| Set2 | 2.5 | 1.5 | **FAIL** | HC1 |
| Pastel1 | 1.8 | 2.6 | **FAIL** | HC1 |

- **Survivors: viridis, Paired.**
- **Optimal: `viridis`** — wins both soft constraints (RG 19.4 > 16.6, grayscale
  6.9 > 6.3).
- **Paired** acceptable second-best with explicit tradeoff (cap ~0.85).

### 3.1 Tolerance

Grade ordinal verdicts: jet fails grayscale, okabe_ito fails grayscale (NOT
red-green), the Set/Accent/Pastel qualitative schemes fail red-green, survivors
are viridis+Paired, viridis optimal. Robust across standard colorblind models
(Brettel/Machado/Viénot) and deltaE variants.

## 4. Expected Artifacts

- `/tmp_workspace/results/palette_choice.json`
- `/tmp_workspace/results/palette_evaluation.json`
- `/tmp_workspace/results/palette_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Final pick is **viridis** (optimal), justified with computed metrics. (Paired with correct tradeoff → partial, see caps.)        | 0.30   |
| CP2 | Hard-pass survivor set correctly identified as **{viridis, Paired}**; no failing palette wrongly included.                        | 0.20   |
| CP3 | The grayscale trap on jet is caught: jet rejected for grayscale failure despite good color separation, with the named reason.     | 0.15   |
| CP4 | The expert trap on okabe_ito is caught: rejected for FAILING grayscale (not for red-green — it passes red-green).                 | 0.20   |
| CP5 | Metrics actually computed (colorblind simulation + deltaE + grayscale luminance), method shown — not asserted from reputation.    | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick was reputation/eyeball based with no computed
  colorblind/grayscale metrics in the artifacts.
- **cap at `0.55`** if `palette_choice.json` or `palette_evaluation.json` missing.
- **cap at `0.60`** if a hard-constraint-failing palette is the final pick
  (jet, okabe_ito, Set1, etc.).
- **cap at `0.70`** if okabe_ito is rejected for the WRONG reason (claimed it
  fails red-green — it does not; it fails grayscale). Correctly diagnosing WHY
  the expert palette fails is the discriminator.
- **cap at `0.85`** if the pick is **Paired** with an explicit correct tradeoff
  vs viridis; without acknowledging viridis is better, cap `0.70`.
- **cap at `0.75`** if the survivor set is wrong even if the single pick is
  viridis.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- absolute deltaE/luminance numbers differ within method variance — grade the
  ordinal verdicts (Section 3.1),
- the executor used a different standard colorblind model or deltaE variant,
- the executor rendered a sample figure / grayscale preview as extra evidence
  (encouraged),
- the executor used python/a library to compute — any real computation is fine.

Pass requirements (`score >= 0.90`): CP1 (viridis), CP2 (survivors), CP3 and CP4
(both traps caught, okabe_ito for the right reason), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor computed red-green separation but not yet
grayscale (or vice versa), or has a draft pick without full survivor/tiebreak
reasoning.

Prefer `fail` when, after follow-ups, the pick is a failing palette with no
recovery, the choice was reputation-based with no computation, or required
artifacts are absent.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — objective verdicts + optimal pick.
- `references/reference_analysis.py` — recomputes all metrics from the shipped
  `palettes.json`.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic answer key reproducible via
`reference_analysis.py`. Only tolerance is method-variance on absolute numbers.

## 10. Notes For Rationale

- When scoring CP4, quote the executor's stated reason for rejecting okabe_ito
  and confirm it is grayscale, not red-green.
- When capping at 0.45, note absence of any computed metrics in the artifacts.
- Guidance tags: `objective_constraint_selection`, `rainbow_is_a_trap`,
  `famous_cb_palette_fails_grayscale`, `grayscale_print_constraint`,
  `offline_deterministic`.
