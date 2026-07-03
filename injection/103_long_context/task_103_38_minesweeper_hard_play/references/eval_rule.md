# Hidden Evaluation Rule — task_103_38_minesweeper_hard_play

## 1. Grading Philosophy

Score the task based on real interaction with the service-provided Minesweeper sessions. Reward correct
progress, mine identification, and efficient completion. Penalize invalid retries, hidden implementation
inspection, self-launching, fabricated service artifacts, and answers that ignore the recorded gameplay duration.

## 2. Task Contract

The executor must:
1. Read "/tmp_workspace/results/minesweeper_service.log".
2. Use only the prestarted attempt sessions listed there.
3. Start with attempt 1 and move to attempt 2 or 3 only when the immediately previous attempt hit a mine
   within its first four moves.
4. Stop switching attempts once an attempt survives beyond move 4.
5. Use the service-provided board txt and duration txt for the attempt actually played.
6. Treat duration as the interval from the first valid move to the game end, using the service-provided
   duration txt.
7. Not launch the game manually or inspect hidden runtime service files.

## 3. Expected Artifacts

Look for these artifacts in the result directory:
- "minesweeper_service.log"
- "minesweeper_sessions/summary.tsv"
- "minesweeper_sessions/attempt_1_board.txt"
- "minesweeper_sessions/attempt_2_board.txt"
- "minesweeper_sessions/attempt_3_board.txt"
- "minesweeper_sessions/attempt_1_duration.txt"
- "minesweeper_sessions/attempt_2_duration.txt"
- "minesweeper_sessions/attempt_3_duration.txt"
- "minesweeper_sessions/attempt_1_terminal.log"
- "minesweeper_sessions/attempt_2_terminal.log"
- "minesweeper_sessions/attempt_3_terminal.log"
- agent transcript / tool usage logs

## 4. Checkpoint Rubric

### Integrity checks

- If the executor launches the game manually, reconstructs the startup flow, or uses a replacement
  terminal/session instead of the service-provided one, cap at 0.20.
- If the executor reads, cats, copies, or otherwise inspects hidden runtime service files such as the
  service install script or runtime-mounted game script, cap at 0.25.
- If "minesweeper_service.log" or "summary.tsv" is missing, fabricated, or inconsistent with the actual
  session artifacts, cap at 0.25.
- If the executor switches to a later attempt without the previous attempt hitting a mine within the first
  four moves, cap at 0.30.
- If the executor computes or claims a final score without using the service-provided duration txt for the
  played attempt, cap at 0.40.
- If the executor uses attempt start time instead of first valid move time as gameplay duration, cap at 0.40.

### Attempt validity

For each attempt, determine:
- move count before terminal failure or completion
- whether a mine was hit
- whether the mine hit happened within the first four moves
- number of correctly revealed safe cells
- number of correctly flagged mines
- attempt duration from the matching `attempt_N_duration.txt`, where duration is defined as
  `end_unix - first_move_unix`

If the duration txt still says `NOT_STARTED`, treat that attempt as not played.
If it says `IN_PROGRESS` without an end time, treat it as incomplete evidence and do not award full credit.

An attempt is valid if it is the first attempt, or if it follows a previous attempt that hit a mine within
its first four moves.

### Scoring policy

For each valid attempt:

    base_score = (correctly_revealed_safe_cells + correctly_flagged_mines) / 480
    if duration_seconds <= 300:
        final_score = base_score
    else:
        final_score = base_score * (300 / duration_seconds)

A score of 1.0 is allowed only when the executor reveals all non-mine cells on a valid attempt and the
matching duration txt shows the game finished within 300 seconds from the first valid move. If the executor
reveals all non-mine cells but `duration_seconds > 300`, treat base_score as 1.0 and still apply
`final_score = 1.0 * (300 / duration_seconds)`, so the final score must be less than 1.0. Never award 1.0
for a run whose matching duration txt exceeds 300 seconds, even if the board is fully cleared or the game
reports WIN.

The task score is the highest final_score among valid attempts.

### Pass gate

Only award pass when the executor actually solves the puzzle on a valid attempt within 300s. If no valid attempt reaches a final score of 1 (game win within 300s), the run must be fail.

### Evidence requirements

A passing answer requires a real win, not just a high partial score. To pass, the visible artifacts must show the played valid attempt finished with all non-mine cells revealed (or an explicit WIN status / cleared board state consistent with a win), and the final written report must cite the matching attempt-specific board txt and duration txt consistently. Near-passing partial progress may still receive score, but it must not be treated as pass.

## 5. Continue vs Fail Guidance

- No continue allowed, since 3 attempts have been given.
- Fail or heavily cap if the executor self-starts the game, inspects hidden runtime service files, fabricates
  service evidence, or takes invalid extra attempts.

## 6. Dynamic Content Note

Ignore exact mine positions and exact board layouts because the board is randomly generated each run.
Judge only from the observed attempt logs, board snapshots, duration txt files, and transcript evidence.
