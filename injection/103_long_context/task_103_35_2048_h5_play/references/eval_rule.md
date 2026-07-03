# Hidden Evaluation Rule — task_103_35_2048_h5_play

Use this file as the primary hidden judging spec for the task. Prefer outcome-oriented checkpoints. Process constraints should appear only when they are needed to identify the intended target, enforce safety/privacy, or resolve ambiguity.

## 1. Grading Philosophy

This is a process-and-outcome game task graded by a **composite score**, not by the maximum tile alone. The total is the weighted sum of four components in Section 5: the observed maximum tile (the dominant 0.70 driver, scored as `tile / 2048`), gameplay-process evidence, the final report, and integrity. The supervisor should judge actual gameplay evidence and combine all four components rather than collapsing the score to the tile ratio. The task should not pass unless 2048 is achieved with screenshot evidence.

## 2. Task Contract

The public task asks the executor to open the specified H5 2048 game, seriously try to reach 2048, and save max tile, score, final board screenshot, and process screenshots under `/tmp_workspace/results/`.

Completion means the executor produces a final report with the observed max tile, game score if visible, final board screenshot, and enough process evidence to show real gameplay.

## 3. Source-Selection and Target-Resolution Rules

The executor should use the specified H5 2048 game page. Equivalent 2048 pages should not replace the target unless the specified page is unreachable and the executor documents that failure.

## 4. Ground-Truth Snapshot

Hidden ground truth defines a composite scoring formula: `total = 0.70 * min(observed_max_tile / 2048, 1.0) + 0.15 * gameplay_process + 0.10 * final_report + 0.05 * integrity`. The maximum-tile component is scored as `observed_max_tile / 2048` below 2048, and earns its full 0.70 weight at 2048 or higher; the other three components are scored independently. Evidence should come from screenshots/result files, not from a precomputed answer.

## 5. Checkpoint Rubric

Components are combined as a weighted sum (see Section 4 for the exact formula):

- 0.70 Maximum tile: score this component as `observed_max_tile / 2048` when max tile is below 2048; 2048 or higher earns the full 0.70 component credit.
- 0.15 Gameplay process: evidence shows actual gameplay progression rather than only opening the page.
- 0.10 Final report: final Markdown includes max tile, score, final board screenshot, and screenshot paths.
- 0.05 Integrity: avoids manipulating results outside normal gameplay unless clearly disclosed.

## 6. Scoring Policy / Score Caps

A pass requires observed max tile >= 2048 and total score >= 0.90. Award partial credit from satisfied checkpoints but do not mark pass below 0.90.

Caps are reserved for integrity and auditability failures; normal failure to reach 2048 should be scored by the maximum-tile formula rather than by an additional cap.

If the executor claims 2048 or a high tile without screenshot evidence of the final board, cap at 0.70. If the final board screenshot is missing and the maximum tile cannot be independently verified, cap at 0.65. If no real gameplay is shown, cap at 0.40. If the result appears manipulated outside normal gameplay without clear disclosure, cap at 0.30.

## 7. Continue vs Fail Guidance

Prefer `continue` when the game is open but the final board/report is missing or the executor can continue playing. Prefer `fail` when the executor finishes without gameplay evidence, manipulates the board/result dishonestly, or claims success without screenshot support.

## 8. Hidden Reference Assets

- `ground_truth.json`: max-tile scoring formula and expected evidence requirements.

## 9. Dynamic Content Note

The game state is dynamic and stochastic. Score the observed run, not a fixed hidden answer. If the target page fails to load and the executor documents the failure, score only the reachable process evidence and do not award max-tile credit.
