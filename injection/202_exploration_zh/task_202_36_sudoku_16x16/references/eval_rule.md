# Hidden Evaluation Rule — Exploration v2 · 16x16 Sudoku (offline, any valid completion)

## 1. Grading Philosophy

A deterministic **constraint-solving** task graded by **validity**: ANY correct
completion that obeys the Sudoku rules and preserves the givens earns full credit
— the executor does NOT have to reproduce the specific solution shipped with the
task. The puzzle is offline and frozen. Grid size sets difficulty: the 9x9 is
the easiest tier, while this 16x16 is a larger, harder board (25x25 is larger
still).

## 2. Task Contract

Fill the 16x16 grid at `/tmp_workspace/clawbench/sources/puzzle.txt` so every
row, column, and 4x4 box contains 1 to 16 exactly once, preserving the givens.
Save `solution.txt` (16 lines x 16 numbers) and `solution.json`.

## 3. Ground-Truth Reference

`references/ground_truth.json` holds the puzzle, box dimensions, and one
reference `solution` (16x16). The reference solution is **only an example of a
valid completion** — the executor's grid does NOT need to match it. Any grid that
(a) keeps all given cells unchanged and (b) is a fully valid Sudoku is correct.

## 4. Expected Artifacts

- `/tmp_workspace/results/solution.txt` — completed grid.
- `/tmp_workspace/results/solution.json` — `solution` 2D array + approach note.

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                       | Weight |
| --- | --------------------------------------------------------------------------------------------- | ------ |
| CP1 | A completed grid is saved in the requested format (16x16, no empty cells / dots).            | 0.20   |
| CP2 | The givens are preserved (every pre-filled cell in puzzle.txt is unchanged in the answer).     | 0.20   |
| CP3 | Every row is a permutation of 1 to 16, every column is a permutation of 1 to 16, and every 4x4 box is a permutation of 1 to 16 (a fully valid completion). | 0.60   |

Total full score: `1.00`. A grid satisfying CP1+CP2+CP3 is fully correct
regardless of whether it equals the shipped reference solution.

## 6. Scoring Policy / Score Caps

- **cap at `0.50`** if any given cell was altered (the puzzle's fixed numbers must
  be respected, even if the rest is valid).
- **cap at `0.40`** if the saved grid still contains empty cells / dots.
- If the grid is complete and preserves givens but has rule violations, award
  partial credit by the fraction of rows/columns/boxes that are valid
  permutations (CP3 is the dominant weight).

Do **not** cap or fail merely because:

- the executor's grid differs from the shipped reference `solution` — ANY valid
  completion is full credit,
- the solving method differs (logic / backtracking / a solver library),
- `solution.txt` spacing differs, as long as it parses to the 16x16 grid.

Pass requirements (`score >= 0.90`): CP1 + CP2 + CP3 all satisfied (complete,
givens preserved, fully valid), no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` for a partial/near-valid grid with follow-ups left. Prefer
`fail` when, after follow-ups, the grid alters givens, stays incomplete, or has
unresolvable rule violations.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — puzzle + one reference valid solution (example
  only). Supervisor-only.

## 9. Dynamic Content Note

None — puzzle frozen offline; validity is checked by the rules, not by matching a
single canonical solution. Deterministic.

## 10. Notes For Rationale

- When capping, state the first given-cell that was altered, or the first
  row/column/box that violates the permutation rule.
- Guidance tags: `offline_sudoku`, `any_valid_completion`, `givens_preserved`,
  `grid_size_difficulty`.
