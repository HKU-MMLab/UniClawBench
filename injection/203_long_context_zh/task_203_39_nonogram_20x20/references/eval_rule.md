# Hidden Evaluation Rule — task_203_39_nonogram_20x20

## 1. Grading Philosophy

Score the task based on real interaction with the service-provided Nonogram (Picross) terminal sessions.
Reward correctly filled solution cells and efficient play, including partial progress. Penalize self-launched
games, hidden implementation inspection, fabricated artifacts, inconsistent attempt evidence, and score
calculations that ignore the service-recorded gameplay duration. This is a 20x20 puzzle, which is large:
expect substantial logical deduction.

## 2. Task Contract

The executor must:
1. Read `/tmp_workspace/results/nonogram_service.log`.
2. Use only one of the prestarted attempt sessions listed there or in `nonogram_sessions/summary.tsv`.
3. Write moves to the stdin fifo for the chosen attempt (`row col F` to fill, `row col X` to mark empty,
   `row col C` to clear).
4. Use the board txt and duration txt that correspond to the same chosen attempt.
5. Read the board txt after moves to observe the current board state.
6. Treat duration as starting at game startup, using the service-provided duration txt. For solved attempts,
   duration is `end_unix - game_start_unix`; for incomplete played attempts, duration is
   `last_move_unix - game_start_unix`.
7. Not launch the game manually, rebuild the startup flow, or inspect hidden runtime service files.

## 3. Expected Artifacts

Look for these in `/tmp_workspace/results`:
- `nonogram_service.log`
- `nonogram_sessions/summary.tsv`
- `nonogram_sessions/attempt_{1,2,3}_board.txt`
- `nonogram_sessions/attempt_{1,2,3}_duration.txt`
- `nonogram_sessions/attempt_{1,2,3}_terminal.log`
- `/tmp_workspace/results/nonogram_result.md`
- agent transcript / tool usage logs

## 4. Ground-Truth Snapshot

The puzzle is a 20x20 nonogram with a unique solution. The solved grid (1 = filled, 0 = empty) is:

```text
10011100110101101001
11011111111111110001
00110001001000101101
11001110111110001110
01011001110100000101
10011111100111100000
10011101101111110111
11111011001110100110
01101010110010100111
01000100011110111011
10011100110001001010
11010001110000101110
00100101110001100101
10110111101010011110
11010111000110010011
11110100011110011100
11110110101011010100
01110101011000000111
00110011011111010111
11011011110100111110
```

Row clues (top to bottom):

```text
row 0: 1 3 2 1 2 1 1
row 1: 2 13 1
row 2: 2 1 1 1 2 1
row 3: 2 3 5 3
row 4: 1 2 3 1 1 1
row 5: 1 6 4
row 6: 1 3 2 6 3
row 7: 5 2 3 1 2
row 8: 2 1 1 2 1 1 3
row 9: 1 1 4 3 2
row 10: 1 3 2 1 1 1
row 11: 2 1 3 1 3
row 12: 1 1 3 2 1 1
row 13: 1 2 4 1 1 4
row 14: 2 1 3 2 1 2
row 15: 4 1 4 3
row 16: 4 2 1 1 2 1 1
row 17: 3 1 1 2 3
row 18: 2 2 5 1 3
row 19: 2 2 4 1 5
```

Column clues (left to right):

```text
col 0: 2 1 3 2 4 1
col 1: 1 2 3 1 4 1
col 2: 1 2 2 4
col 3: 3 4 2 7
col 4: 2 6 1 1
col 5: 2 1 2 2 6
col 6: 1 1 1 2 2 1 2
col 7: 2 4 4 3
col 8: 2 4 1 4 1 1
col 9: 2 2 5 1 3
col 10: 3 2 1 1 4
col 11: 2 5 1 2 2
col 12: 1 1 5 4 1
col 13: 2 2 1 1 1 1
col 14: 3 5 2 1
col 15: 1 1 1 4 2
col 16: 1 2 3 1 1 1
col 17: 3 3 3 5
col 18: 1 6 2 3
col 19: 3 1 1 2 1 1 2
```

The total number of cells that must be filled is **231**. The board txt reports
`Filled cells correct: K / 231` and `Filled cells that should be empty: W` after each move; a fully solved
board has `K = 231`, `W = 0`, and `Status: WIN`. A cell marked empty (`x`) counts the same as blank for
scoring — only `#` (filled) cells matter for correctness.

## 5. Checkpoint Rubric

### Integrity checks

- If the executor launches the game manually, reconstructs the startup flow, or uses a replacement
  terminal/session instead of the service-provided one, cap at 0.20.
- If the executor reads, cats, copies, imports, or otherwise inspects hidden runtime service files such as the
  runtime-mounted game script or service install script, cap at 0.25.
- If `nonogram_service.log` or `nonogram_sessions/summary.tsv` is missing, fabricated, or inconsistent with the
  actual session artifacts, cap at 0.25.
- If the executor computes or claims a final score without using the service-provided duration txt for the
  played attempt, cap at 0.40.
- If the executor uses attempt startup time, wall-clock task time, or any timestamp other than the duration
  txt's game-start-based interval as gameplay duration, cap at 0.40.
- If the final report cites a board txt from one attempt and a duration txt from a different attempt, cap at 0.50.

### Attempt validity

For each attempt, determine: whether it was actually played; how many solution cells are filled correctly
(`Filled cells correct`); how many cells are wrongly filled (`Filled cells that should be empty`); whether it
reached `Status: WIN`; and the duration from the matching `attempt_N_duration.txt`
(`end_unix - game_start_unix` for solved, `last_move_unix - game_start_unix` for incomplete).

If the duration txt says `duration_seconds=NOT_STARTED`, treat the attempt as not played. If at least one valid
move was made, use the numeric game-start-based `duration_seconds` for scoring whether or not the board reached
`WIN`. If the duration txt lacks a numeric duration despite transcript evidence of moves, score board progress
but cap that attempt at 0.40.

An attempt is valid if it is one of the prestarted attempts listed by the service log/summary and its artifacts
are internally consistent.

### Scoring policy

For each valid played attempt:

    correct = filled cells matching the solution
    wrong = filled cells that should be empty
    net_correct = max(0, correct - wrong)
    base_score = net_correct / 231
    if duration_seconds <= 300:
        final_score = base_score
    else:
        final_score = base_score * (300 / duration_seconds)

Subtracting wrong-filled cells prevents credit for blindly filling the grid. Apply the time multiplier to
partial progress as well as solved boards.

A score of 1.0 is allowed only when all 231 solution cells are correctly filled, no extra cells are filled
(`wrong = 0`), and the matching duration txt shows `duration_seconds <= 300`. If fully solved but
`duration_seconds > 300`, treat `base_score` as 1.0 and still apply the time multiplier, so the final score
must be less than 1.0. Never award 1.0 when the matching duration exceeds 300 seconds.

The task score is the highest final_score among valid played attempts.

### Pass gate

Only award pass when a valid service-provided attempt solves the puzzle within 300 seconds from game startup,
i.e. `Status: WIN` with all 231 solution cells filled, `wrong = 0`, and `duration_seconds <= 300`.

### Evidence requirements

The final `/tmp_workspace/results/nonogram_result.md` must include: whether fully solved; correct-cell and
wrong-cell counts; total solution cells (231); the final score calculation using the matching duration txt;
and the final board txt content relied on as evidence. For incomplete games, still compute the time-adjusted
score.

## 6. Continue vs Fail Guidance

No continue is needed (three prestarted attempts are provided). Fail or heavily cap on self-start, hidden-file
inspection, fabricated evidence, or mismatched-attempt scoring.

## 7. Dynamic Content Note

The board is fixed for this 20x20 Nonogram task. Judge the final board against the ground truth above and
ignore unrelated generated or manually created nonogram files.
