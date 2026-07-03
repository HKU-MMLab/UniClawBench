# Hidden Evaluation Rule — Exploration v2 · Gomoku single best move (offline, unique winning move)

## 1. Grading Philosophy

A single-position **tactical-search** task graded by **exact match to the
objectively optimal move**. Unlike a multi-turn game, the executor must find the
one globally best move in this fixed position. The position is constructed so the
best move is **unambiguous and engine-free**: Black has an immediate
five-in-a-row win, and it is the unique winning move. No opponent reply matters.

## 2. Task Contract

From the 15x15 board at `/tmp_workspace/clawbench/sources/board.txt` (X=Black to
move, O=White, .=empty, rows/cols 0-14), find Black's globally best move and
report `row`, `col` (0-indexed) + reasoning in
`/tmp_workspace/results/best_move.json`.

## 3. Ground-Truth Reference

- **Best move: (row 7, col 8).** Black has four in a row at row 7, columns
  4-5-6-7; the left end (col 3) is blocked by White, so **(7,8) completes five
  (cols 4-8) — an immediate, unique win**.
- No other move wins this turn; any other move is therefore not optimal.
- Coordinate convention: 0-indexed, row 0 top, col 0 left (as stated in the board
  file).

## 4. Expected Artifacts

- `/tmp_workspace/results/best_move.json` — `row`, `col`, `reasoning`.

## 5. Checkpoint Rubric

| ID  | What matters (objective)                                                                          | Weight |
| --- | ------------------------------------------------------------------------------------------------ | ------ |
| CP1 | The move equals **(7, 8)** in the stated 0-indexed convention.                                    | 0.55   |
| CP2 | The reasoning correctly identifies that it completes five-in-a-row (the four at row 7 cols 4-7).  | 0.25   |
| CP3 | The answer is in the requested format (`row`, `col`, reasoning) and the coordinate convention is consistent with the board. | 0.20   |

Total full score: `1.00`.

## 6. Scoring Policy / Score Caps

- **cap at `0.45`** if the move is not (7,8) — i.e. a non-winning move is chosen
  (the position has a forced immediate win; missing it is the core failure).
- **cap at `0.70`** if the executor clearly identified the winning line/threat in
  the reasoning but reported the coordinate wrong due to an off-by-one / row-col
  swap (right idea, wrong cell). Use this only when the reasoning unambiguously
  describes completing the row-7 five.
- Accept (7,8) given in an alternative but clearly-stated convention (e.g.
  1-indexed (8,9), or algebraic) **only if** the executor states the convention
  and it maps to the same point; otherwise grade on the 0-indexed (7,8).

Do **not** cap or fail merely because:

- the executor also discusses White's stones or alternative moves before
  concluding (7,8),
- the reasoning is brief, as long as it names the five-completion.

Pass requirements (`score >= 0.90`): CP1 (move = (7,8)) + CP2 (correct reason),
no cap fired.

## 7. Continue vs Fail Guidance

Prefer `continue` when the executor is analyzing and has not yet committed, or
gave a coordinate in an unclear convention that may map to (7,8).
Prefer `fail` when, after follow-ups, a non-winning move is committed.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — board + best move + rationale. Supervisor-only.

## 9. Dynamic Content Note

None — fixed offline position with a unique winning move. Deterministic.

## 10. Notes For Rationale

- If capping for a wrong coordinate, quote the executor's reported (row,col) vs
  (7,8) and whether the reasoning identified the row-7 four.
- Guidance tags: `single_position_best_move`, `unique_winning_move`,
  `coordinate_convention`, `offline_deterministic`.
