# Hidden Evaluation Rule — Exploration v2 · Climate-tech pitch deck theme selection (objective, brand + readability constraints)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective constraint
satisfaction plus the correct optimal pick**.

The pool is eleven real reveal.js theme CSS files shipped offline. Four hard
constraints (dark + three contrast thresholds) eliminate every light theme and
the low-contrast dark theme; two soft constraints (brand-color alignment +
readability) break the tie among the surviving dark themes. The trap: the theme
with the **highest contrast of all (simple, 21:1)** is a LIGHT theme and fails
the dark/professional brand requirement — best numbers ≠ right pick.

The hidden `ground_truth.json` + `reference_analysis.py` reproduce every metric
from the shipped CSS (WCAG contrast on the `--r-*` variables, CIE76 deltaE of
the accent to brand #2EAA78). Grade ordinal outcomes. Offline + frozen → never
stale.

## 2. Task Contract

Pick the best reveal.js theme for a dark/professional climate-tech investor deck
(brand accent #2EAA78) from `/tmp_workspace/clawbench/sources/theme_css/`. Hard:
(HC1) dark bg lum<0.2; (HC2) text contrast ≥7; (HC3) heading ≥7; (HC4) accent
≥4.5. Soft: minimize accent deltaE to brand, then maximize min contrast. Pick
ONE; justify with numbers. Save `deck_choice.json`, `deck_evaluation.json`,
`deck_method.json`. Offline.

## 3. Ground-Truth Reference (objective answer key)

From `ground_truth.json` (reproducible via `reference_analysis.py`):

| theme | dark | text C | head C | accent C | brand ΔE | hard pass |
| ----- | ---- | ------ | ------ | -------- | -------- | --------- |
| **league** | ✓ | 14.41 | 14.41 | 9.77 | **42.3** | **PASS** |
| night | ✓ | 18.88 | 18.88 | 9.44 | 69.7 | PASS |
| black | ✓ | 17.58 | 17.58 | 7.32 | 73.7 | PASS |
| dracula | ✓ | 16.49 | 7.29 | 7.37 | 109.9 | PASS |
| moon | ✓ | 5.61 | 12.25 | 4.08 | — | FAIL (text/accent contrast) |
| simple | ✗ | 21.0 | 21.0 | 15.3 | — | FAIL (not dark) — highest-contrast TRAP |
| white/serif/beige/sky | ✗ | — | — | — | — | FAIL (not dark) |
| solarized | ✗ | 4.13 | 4.99 | 3.41 | — | FAIL (not dark + low contrast) |

- **Survivors: black, dracula, league, night.**
- **Optimal: `league`** — wins both soft constraints (accent closest to brand,
  ΔE 42.3 vs next 69.7; highest min contrast 9.77).
- **night / black** acceptable with explicit off-brand-accent tradeoff (cap ~0.85).

### 3.1 Tolerance

Grade ordinal verdicts: light themes fail HC1, moon fails text contrast, the four
dark survivors are black/dracula/league/night, league is optimal on brand +
readability. Robust across contrast/deltaE method variants.

## 4. Expected Artifacts

- `/tmp_workspace/results/deck_choice.json`
- `/tmp_workspace/results/deck_evaluation.json`
- `/tmp_workspace/results/deck_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Final pick is **league** (optimal), justified with computed metrics. (night/black with correct tradeoff → partial.)             | 0.30   |
| CP2 | Hard-pass survivor set correctly identified as **{black, dracula, league, night}**; no light/failing theme included.             | 0.20   |
| CP3 | The highest-contrast TRAP is caught: simple (and the other light themes) rejected for failing the dark requirement despite great contrast. | 0.20   |
| CP4 | Brand alignment used correctly in the tie-break: league's accent recognized as closest to #2EAA78 among the dark survivors.       | 0.15   |
| CP5 | Metrics actually computed from the CSS variables (contrast + deltaE), method shown — not eyeballed.                              | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick was made by eyeballing / theme reputation with no
  computed contrast or brand-deltaE in the artifacts.
- **cap at `0.55`** if `deck_choice.json` or `deck_evaluation.json` missing.
- **cap at `0.60`** if a hard-constraint-failing theme is the final pick
  (any light theme, or moon).
- **cap at `0.65`** if the highest-contrast LIGHT theme (simple) is selected —
  the "best numbers but wrong look" trap.
- **cap at `0.85`** if the pick is night or black with an explicit correct
  tradeoff acknowledging the off-brand accent; without acknowledging league is
  better on brand alignment, cap `0.70`.
- **cap at `0.75`** if the survivor set is wrong even if the single pick is league.
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- absolute contrast/deltaE numbers differ within method variance — grade ordinal
  verdicts (Section 3.1),
- the executor proposes overriding the accent color via CSS (reasonable), as long
  as it still picks league as the closest base,
- the executor rendered a sample slide as extra evidence (encouraged),
- the executor used python/a CSS parser — any real computation is fine.

Pass requirements (`score >= 0.90`): CP1 (league), CP2 (survivors), CP3 (light
trap caught), CP4 (brand tie-break), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor computed contrasts but not yet brand deltaE,
or has a draft pick without the survivor/tiebreak reasoning.

Prefer `fail` when, after follow-ups, the pick is a light/failing theme with no
recovery, or the choice was reputation-based with no computation.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — objective verdicts + optimal pick.
- `references/reference_analysis.py` — recomputes all metrics from the shipped
  theme CSS.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic answer key reproducible via
`reference_analysis.py`. Only tolerance is method-variance on absolute numbers.

## 10. Notes For Rationale

- When scoring CP3, quote the executor's reason for rejecting `simple` and
  confirm it cites the dark/professional requirement (not contrast).
- When scoring CP4, confirm league's accent was identified as closest to the
  brand among the dark survivors.
- Guidance tags: `objective_constraint_selection`, `best_numbers_wrong_look_trap`,
  `brand_palette_alignment`, `dark_professional_requirement`, `offline_deterministic`.
