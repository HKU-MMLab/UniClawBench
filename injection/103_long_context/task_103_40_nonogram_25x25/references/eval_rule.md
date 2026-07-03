# Hidden Evaluation Rule — task_103_40_nonogram_25x25

## 1. Grading Philosophy

Score the task based on real interaction with the service-provided Nonogram (Picross) terminal sessions.
Reward correctly filled solution cells and efficient play, including partial progress. Penalize self-launched
games, hidden implementation inspection, fabricated artifacts, inconsistent attempt evidence, and score
calculations that ignore the service-recorded gameplay duration. This is a 25x25 puzzle, which is large:
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

The puzzle is a 25x25 nonogram with a unique solution. The solved grid (1 = filled, 0 = empty) is:

```text
0011111110011000010101111
1101010100010011001001011
0111100110111110000010001
1001001111101000001010001
1011011111001110111011000
1110110001010000100111111
0100111101110111010000000
1100000100110111000110111
1110111001011001000010100
0001100111000101110111000
1001100101110101000011000
0001101011111111100101100
1010100110111101001001110
0101011110000110110101101
1100110110111000011100110
1110001011101111101001110
0001111111100011001111011
0010111110011011111110010
1110100000100101100111111
1111111101100011010101001
0101110100010001001001010
1110111111100000101011001
0100011110100110010110010
1010110001110011100011111
1000110001100011100001100
```

Row clues (top to bottom):

```text
row 0: 7 2 1 1 4
row 1: 2 1 1 1 1 2 1 1 2
row 2: 4 2 5 1 1
row 3: 1 1 5 1 1 1 1
row 4: 1 2 5 3 3 2
row 5: 3 2 1 1 1 6
row 6: 1 4 3 3 1
row 7: 2 1 2 3 2 3
row 8: 3 3 1 2 1 1 1
row 9: 2 3 1 3 3
row 10: 1 2 1 3 1 1 2
row 11: 2 1 9 1 2
row 12: 1 1 1 2 4 1 1 3
row 13: 1 1 4 2 2 1 2 1
row 14: 2 2 2 3 3 2
row 15: 3 1 3 5 1 3
row 16: 8 2 4 2
row 17: 1 5 2 7 1
row 18: 3 1 1 1 2 6
row 19: 8 2 2 1 1 1 1
row 20: 1 3 1 1 1 1 1 1
row 21: 3 7 1 1 2 1
row 22: 1 4 1 2 1 2 1
row 23: 1 1 2 3 3 5
row 24: 1 2 2 3 2
```

Column clues (left to right):

```text
col 0: 1 3 2 1 1 2 2 1 2
col 1: 2 4 3 5
col 2: 1 1 2 1 1 1 3 1 1
col 3: 5 3 1 1 2
col 4: 1 1 2 5 1 6 2
col 5: 2 3 1 2 2 6
col 6: 1 2 1 1 1 1 3 1 2
col 7: 5 2 2 3 2 4
col 8: 1 3 1 7 2
col 9: 4 4 2 1 1 2
col 10: 2 2 3 3 2 4
col 11: 3 4 3 1 1 1 1
col 12: 1 3 1 2 2 1
col 13: 1 1 2 5 1 1 1
col 14: 2 1 2 1 1 3 1 3
col 15: 1 7 6 2
col 16: 2 1 1 1 1 2 1 2
col 17: 1 1 1 1 2 1 1 1
col 18: 1 2 1 4 2
col 19: 1 1 1 1 1 2 4 1
col 20: 4 4 3 3
col 21: 2 2 5 2 4 2
col 22: 1 1 2 5 1 2
col 23: 2 1 1 1 5 1 2
col 24: 4 1 1 1 1 2 1 1
```

The total number of cells that must be filled is **338**. The board txt reports
`Filled cells correct: K / 338` and `Filled cells that should be empty: W` after each move; a fully solved
board has `K = 338`, `W = 0`, and `Status: WIN`. A cell marked empty (`x`) counts the same as blank for
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
    base_score = net_correct / 338
    if duration_seconds <= 420:
        final_score = base_score
    else:
        final_score = base_score * (420 / duration_seconds)

Subtracting wrong-filled cells prevents credit for blindly filling the grid. Apply the time multiplier to
partial progress as well as solved boards.

A score of 1.0 is allowed only when all 338 solution cells are correctly filled, no extra cells are filled
(`wrong = 0`), and the matching duration txt shows `duration_seconds <= 420`. If fully solved but
`duration_seconds > 420`, treat `base_score` as 1.0 and still apply the time multiplier, so the final score
must be less than 1.0. Never award 1.0 when the matching duration exceeds 420 seconds.

The task score is the highest final_score among valid played attempts.

### Pass gate

Only award pass when a valid service-provided attempt solves the puzzle within 420 seconds from game startup,
i.e. `Status: WIN` with all 338 solution cells filled, `wrong = 0`, and `duration_seconds <= 420`.

### Evidence requirements

The final `/tmp_workspace/results/nonogram_result.md` must include: whether fully solved; correct-cell and
wrong-cell counts; total solution cells (338); the final score calculation using the matching duration txt;
and the final board txt content relied on as evidence. For incomplete games, still compute the time-adjusted
score.

## 6. Continue vs Fail Guidance

No continue is needed (three prestarted attempts are provided). Fail or heavily cap on self-start, hidden-file
inspection, fabricated evidence, or mismatched-attempt scoring.

## 7. Dynamic Content Note

The board is fixed for this 25x25 Nonogram task. Judge the final board against the ground truth above and
ignore unrelated generated or manually created nonogram files.
