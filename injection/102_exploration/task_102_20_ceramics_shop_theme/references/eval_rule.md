# Hidden Evaluation Rule — Exploration v2 · Japanese-minimalist ceramics shop theme selection (quantified aesthetic + features)

## 1. Grading Philosophy

This is a **candidate-selection** task graded by **objective constraint
satisfaction plus the correct pick**.

The subjective brief ("Japanese-minimalist") is operationalized into computable
constraints: a muted palette (average HSV saturation ≤ 0.25) and an imagery-
forward layout (product image area ratio ≥ 0.45), on top of practical hard
requirements (working cart+checkout, responsive). The pool is six theme
manifests shipped offline. The traps: the most beautiful muted theme isn't a
store, an on-aesthetic theme is desktop-only, another is too text-heavy, and the
colorful ones fail the muted-palette threshold. **Only one** theme passes all
four. The answer key + `reference_analysis.py` compute saturation from the hex
palettes. Offline + frozen → deterministic; grade ordinal outcomes.

## 2. Task Contract

Pick one ceramics-shop theme that is: a real store (cart+checkout), responsive,
muted palette (avg HSV saturation ≤ 0.25), imagery-forward (product image ratio
≥ 0.45). Pool at `/tmp_workspace/clawbench/sources/theme_candidates/`. Save
`theme_choice.json`, `theme_evaluation.json`, `theme_method.json`. Offline.

## 3. Ground-Truth Reference (answer key)

| theme | ecom | responsive | avg sat | img ratio | hard pass | fails |
| ----- | ---- | ---------- | ------- | --------- | --------- | ----- |
| **shibui_ceramics** | ✓ | ✓ | 0.151 | 0.62 | **PASS** | — |
| kinfolk_journal | ✗ | ✓ | 0.071 | 0.70 | FAIL | HC1 ecommerce (beauty trap) |
| wabi_shop_fixed | ✓ | ✗ | 0.147 | 0.58 | FAIL | HC2 responsive (near-miss) |
| muji_living | ✓ | ✓ | 0.101 | 0.28 | FAIL | HC4 imagery ratio (near-miss) |
| bold_bazaar | ✓ | ✓ | 0.526 | 0.50 | FAIL | HC3 muted palette |
| neon_market | ✓ | ✓ | 0.718 | 0.40 | FAIL | HC3 + HC4 |

- **Only survivor / gold: `shibui_ceramics`.**
- **Near-misses** wabi (not responsive) / muji (small imagery) acceptable ONLY
  with explicit gap diagnosis + a concrete fix → cap ~0.85.
- The discriminators are the **quantified aesthetic** (saturation, imagery ratio)
  plus the store + responsive basics.

## 4. Expected Artifacts

- `/tmp_workspace/results/theme_choice.json`
- `/tmp_workspace/results/theme_evaluation.json`
- `/tmp_workspace/results/theme_method.json`

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                                                          | Weight |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| CP1 | Final pick is **shibui_ceramics**, justified with computed metrics (ecom + responsive + sat ≤0.25 + ratio ≥0.45).               | 0.30   |
| CP2 | Per-theme evaluation correct across the four hard requirements; failing requirement(s) named for each rejected theme.            | 0.20   |
| CP3 | The BEAUTY trap is caught: kinfolk_journal rejected specifically for not being an ecommerce theme (despite the best palette).     | 0.20   |
| CP4 | The NEAR-MISS themes are diagnosed correctly: wabi (not responsive) and muji (product imagery too small), not wrongly accepted.   | 0.15   |
| CP5 | Palette saturation was actually computed from the hex values (method shown); evaluation is evidence-based, not eyeballed.         | 0.15   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the pick was made on vibes with no computed saturation /
  no per-requirement check in the artifacts.
- **cap at `0.55`** if `theme_choice.json` or `theme_evaluation.json` missing.
- **cap at `0.60`** if a theme failing a hard requirement is the final pick with
  no fix (kinfolk, bold, neon, or wabi/muji while ignoring their gap).
- **cap at `0.70`** if kinfolk_journal is rejected for the wrong reason (not
  citing the missing cart/checkout) — diagnosing the beauty trap correctly is a
  discriminator.
- **cap at `0.85`** if the pick is wabi or muji WITH explicit gap diagnosis +
  concrete remedy (valid near-miss handling, not the out-of-the-box answer).
- **cap at `0.30`** if the executor used the network (offline task).

Do **not** cap or fail merely because:

- absolute saturation values differ slightly by HSV method — grade the ordinal
  verdicts (muted: shibui/kinfolk/wabi/muji; loud: bold/neon),
- the executor proposes the near-miss + remedy path alongside picking shibui,
- the executor reports extra reasonable metrics (whitespace, typography).

Pass requirements (`score >= 0.90`): CP1 (shibui_ceramics), CP2, CP3 (beauty
trap caught for the right reason), CP4 (near-misses diagnosed), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor computed saturation but hasn't checked all
requirements, or has a draft pick without per-theme failing-reason analysis.

Prefer `fail` when, after follow-ups, the pick is a failing theme with no fix, or
the choice was vibe-based with no computation.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — verdicts + correct pick.
- `references/reference_analysis.py` — recomputes saturation + verdicts from the
  shipped manifests.

## 9. Dynamic Content Note

None — frozen offline pool; deterministic answer key reproducible via
`reference_analysis.py`. Only tolerance is HSV-method variance on saturation.

## 10. Notes For Rationale

- When scoring CP3, quote the executor's reason for rejecting kinfolk_journal and
  confirm it cites the missing cart/checkout.
- When capping at 0.45, note the absence of computed saturation in the artifacts.
- Guidance tags: `quantified_aesthetic_selection`, `beauty_is_a_trap`,
  `muted_palette_threshold`, `imagery_forward_ratio`, `offline_deterministic`.
