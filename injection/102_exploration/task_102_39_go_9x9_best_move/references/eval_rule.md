# Hidden Evaluation Rule — Exploration v2 · Go 9x9 single best move (KataGo-normalized continuous score)

## 1. Grading Philosophy

A single-position **best-move** task on a 9x9 board (the smaller, easier board). The position is a
**balanced midgame** produced by KataGo self-play (root winrate ~0.48, near-even),
so there is a genuine decision gradient: the best move is decisively best and
weak moves lose real points. Scoring is **KataGo's per-move evaluation,
normalized to [0,1]** — a strong-but-suboptimal move earns proportional credit,
the best move earns 1.0. The ground truth was generated with a real KataGo engine
(see Section 3) and is shipped as a precomputed move table.

## 2. Task Contract

From the 9x9 position (`board.txt` + `position.sgf`, Black to move, komi 7),
find the globally best move; report `row`, `col` (0-indexed), `gtp`, and reasoning
in `/tmp_workspace/results/best_move.json`.

## 3. Ground-Truth Reference

Generated with **KataGo v1.16.4 (Eigen/CPU)**, network
`kata1-b28c512nbt-s8209287936-d4596492266`, analysis at 800 visits, on a
balanced self-play midgame. `references/ground_truth.json` contains:
- `best_move` — KataGo's top move: **B2** (row 7, col 1).
- `move_table` — every analyzed legal move → `normalized` score in [0,1] (plus
  raw winrate / scoreLead / visits).
- Normalization: `score(m) = 0.5*norm(scoreLead) + 0.5*norm(winrate)` across all
  analyzed legal moves; best = 1.0, worst = 0.0; pass/illegal ≈ 0.

`services/katago-scorer/` ships the harness to regenerate this table.

## 4. Scoring (canonical)

```
final_task_score = move_table[chosen_move_gtp].normalized      # clipped [0,1]
```

Map the executor's reported coordinate (either `gtp`, or `(row,col)` via the
stated 0-indexed convention) to a GTP coordinate and look it up in `move_table`.
A move absent from the table (extremely low value / illegal) scores ~0. A pass
scores `move_table["pass"].normalized` (≈0 here).

## 5. Checkpoint Rubric

The task score IS the normalized value of the chosen move (Section 4). For
reporting, decompose:

| ID  | What matters                                                                                  | Weight |
| --- | -------------------------------------------------------------------------------------------- | ------ |
| CP1 | A single legal move is chosen and saved in the requested format (`row`,`col`,`gtp`,reasoning). | 0.10   |
| CP2 | The move maps unambiguously to a GTP coordinate present in the move table.                     | 0.10   |
| CP3 | The move's normalized KataGo score (Section 4) — this dominates and IS the continuous grade.   | 0.80   |

Final score = `0.10*(CP1) + 0.10*(CP2) + 0.80*normalized(move)`, but in practice
report `final_task_score = normalized(move)` when CP1/CP2 hold (the harness score
already reflects move quality). Use the decomposition only if the answer is
malformed.

## 6. Scoring Policy / Score Caps

- The normalized score is the grade; there is no separate cap — a near-best move
  naturally scores high, a blunder low.
- **score 0** if the answer is a pass, an illegal move, or a coordinate that
  cannot be mapped to a board point.
- **cap at `0.10`** (format only) if no parseable move is saved.
- Pass threshold `0.90` means the executor must choose a move KataGo scores
  >= 0.90 — effectively the top move or a near-tie with it.

Do **not** penalize:

- using the SGF or the grid (either is fine),
- GTP case / row-direction, as long as it resolves to a real point,
- choosing a move that ties the top within the normalization (it will score ~1.0
  by construction).

## 7. Continue vs Fail Guidance

Prefer `continue` while the executor is analyzing or gave an ambiguous
convention. Prefer `fail` only if it passes/blunders with no follow-ups left.

## 8. Hidden Reference Assets

- `references/ground_truth.json` — best move + full normalized move table + the
  KataGo engine/network/visits provenance.
- `services/katago-scorer/` — runnable harness to regenerate the table.

## 9. Dynamic Content Note

The position + KataGo table are frozen offline (deterministic at the recorded
visit count). If regenerated via the harness, use the latest `move_table`.

## 10. Notes For Rationale

- Quote `normalized[chosen_move]` and the executor's coordinate mapping.
- If the move isn't in the table, note that and score ~0.
- Guidance tags: `single_position_best_move`, `katago_normalized_continuous_score`,
  `balanced_midgame`, `larger_board_harder`.
