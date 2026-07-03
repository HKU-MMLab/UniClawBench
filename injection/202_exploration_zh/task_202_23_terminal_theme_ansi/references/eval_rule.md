# Hidden Evaluation Rule — Exploration v2 · Terminal ANSI theme selection (objective, conflicting constraints)

## 1. Grading Philosophy

A **candidate-selection** task graded by **objective constraint satisfaction plus
the correct optimal pick**. The pool is seven real Windows Terminal color schemes
shipped offline. Four hard constraints (fg/bg contrast + ANSI separation) defeat
reputation-based picking: a popular muted scheme (Nord) has ANSI colors too close
together, and a high-contrast scheme (Monokai Remastered) reuses the **same color
for red and purple**. Five schemes pass; the largest minimum ANSI separation
breaks the tie. The answer key + `reference_analysis.py` recompute every number
from the shipped JSONs. Offline + frozen → deterministic; grade ordinal outcomes.

## 2. Task Contract

Pick the best dark terminal scheme for distinguishable ANSI CLI output from
`/tmp_workspace/clawbench/sources/theme_candidates/`. Hard: (HC1) fg/bg ≥ 4.5;
(HC2) min chromatic-ANSI deltaE ≥ 18; (HC3) blue-purple ≥ 18; (HC4) red-green ≥
25. Soft: maximize min ANSI deltaE, then fg/bg contrast. Pick ONE; justify with
numbers. Save `theme_choice.json`, `theme_evaluation.json`, `theme_method.json`.
Offline.

## 3. Ground-Truth Reference (objective answer key)

| scheme | fg/bg | min ANSI ΔE | blue-purple | red-green | hard pass |
| ------ | ----- | ----------- | ----------- | --------- | --------- |
| **Solarized Dark Higher Contrast** | 8.99 | **40.3** | 78.1 | 111.3 | **PASS** |
| Dracula | 13.36 | 37.7 | 37.7 | 136.6 | PASS |
| One Half Dark | 10.48 | 31.2 | 52.7 | 76.6 | PASS |
| Gruvbox Dark | 10.75 | 28.8 | 56.1 | 79.0 | PASS |
| Ubuntu | 15.13 | 28.1 | 28.1 | 113.9 | PASS |
| Monokai Remastered | 13.86 | **0.0** | 92.1 | 142.4 | **FAIL** (red==purple #f4005f) |
| Nord | 9.25 | **15.8** | 24.8 | 61.4 | **FAIL** (ANSI too close) |

- **Survivors:** Solarized Dark Higher Contrast, Dracula, One Half Dark, Gruvbox
  Dark, Ubuntu.
- **Optimal: `Solarized Dark Higher Contrast`** — largest min ANSI separation
  (40.3).
- **Dracula** acceptable second-best (37.7) with explicit tradeoff (cap ~0.85).

### 3.1 Tolerance

Grade ordinal verdicts: Monokai fails (red==purple identical), Nord fails (min
ANSI < 18), the other five pass, Solarized Dark HC has the largest min ANSI
separation. Robust across deltaE variants.

## 4. Expected Artifacts

- `/tmp_workspace/results/theme_choice.json`
- `/tmp_workspace/results/theme_evaluation.json`
- `/tmp_workspace/results/theme_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                          | Weight |
| --- | -------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Final pick is **Solarized Dark Higher Contrast** (optimal), justified with computed metrics. (Dracula with correct tradeoff → partial.) | 0.30   |
| CP2 | Hard-pass survivor set correctly identified (the five), no failing scheme wrongly included.                       | 0.20   |
| CP3 | The duplicate-color trap is caught: Monokai rejected because red and purple are the same color (min ANSI ΔE 0).    | 0.20   |
| CP4 | The closeness trap is caught: Nord rejected for ANSI colors too close (min ΔE < 18), not chosen for being popular.  | 0.15   |
| CP5 | Metrics actually computed from the theme JSONs (contrast + ANSI deltaE), method shown — not eyeballed.            | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick was made by reputation/eyeball with no computed
  contrast/deltaE in the artifacts.
- **cap at `0.55`** if `theme_choice.json` or `theme_evaluation.json` missing.
- **cap at `0.60`** if a hard-constraint-failing scheme (Monokai/Nord) is the
  final pick.
- **cap at `0.70`** if Monokai is rejected for a vague reason (e.g. "too bright")
  rather than the identical red/purple colors — diagnosing the real failure is a
  discriminator.
- **cap at `0.85`** if the pick is Dracula with an explicit correct tradeoff vs
  Solarized Dark HC; without acknowledging the latter is better, cap `0.70`.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- absolute deltaE values differ within method variance — grade ordinal verdicts,
- the executor weights additional ANSI pairs or includes the bright variants
  (reasonable extra analysis),
- the executor used python/a library to compute — any real computation is fine.

Pass requirements (`score >= 0.90`): CP1 (Solarized Dark HC), CP2 (survivors),
CP3 and CP4 (both traps caught for the right reason), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when contrasts are computed but ANSI separation isn't, or a
draft pick lacks survivor/tiebreak reasoning. Prefer `fail` when the pick is a
failing scheme with no recovery, or reputation-based with no computation.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — verdicts + optimal pick.
- `references/reference_analysis.py` — recomputes all metrics from the shipped
  theme JSONs.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic answer key reproducible via
`reference_analysis.py`. Only tolerance is deltaE-method variance.

## 10. Notes For Rationale

- When scoring CP3, confirm the executor identified the red==purple identical
  color (not just "low contrast").
- Guidance tags: `objective_constraint_selection`, `identical_ansi_color_trap`,
  `popular_palette_too_close_trap`, `ansi_separation_required`,
  `offline_deterministic`.
