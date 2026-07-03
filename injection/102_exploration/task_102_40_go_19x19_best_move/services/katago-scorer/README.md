# KataGo Scorer Harness

This directory ships a **runnable harness** that turns a Go position into the
canonical per-move scoring table used to grade the "single best move" task.

## Why a harness instead of pre-computed scores?

KataGo needs its binary + a neural-network weights file + real compute (ideally a
GPU). That toolchain was **not available in the task-authoring sandbox**, so the
exact per-move KataGo scores could not be baked in at authoring time. This
harness is the reproducible bridge: install KataGo, run `score_moves.py`, and it
emits `move_scores.json` — the canonical ground-truth scoring table.

Until KataGo output is generated, the supervisor falls back to the **engine-free
tactical anchor** recorded in `../references/ground_truth.json` (a position with
a clear, verifiable best move), so the task is still gradeable today.

## How to produce the canonical scoring table

```bash
# 1. install KataGo + a network (e.g. from https://katagotraining.org/ )
# 2. run the analysis engine through the scorer:
python3 score_moves.py \
  --sgf ../../sources/position.sgf \
  --katago /path/to/katago \
  --model  /path/to/kata-network.bin.gz \
  --config /path/to/analysis.cfg \
  --komi 7 \
  --out    move_scores.json
```

`move_scores.json` will contain:
- `best_move` — KataGo's top move (GTP coord, e.g. `F5`)
- `normalized` — every legal move → score in `[0,1]`
- `raw` — per-move `scoreLead` + `winrate`

## Normalization (canonical)

For every analyzed legal move `m` (Black's perspective):

```
norm_score(m)   = (scoreLead(m) - min_scoreLead) / (max_scoreLead - min_scoreLead)
norm_winrate(m) = (winrate(m)   - min_winrate)   / (max_winrate   - min_winrate)
score(m)        = 0.5 * norm_score(m) + 0.5 * norm_winrate(m)     # in [0,1]
```

The argmax move → `1.0`; the worst legal move → `0.0`; pass/illegal → `0`.

## Task score mapping

```
final_task_score = score(chosen_move)   # rounded to 2 dp, clipped to [0,1]
```

So a strong-but-not-best move still earns proportional credit, exactly as the
task intends. The eval_rule consumes `move_scores.json` when present; otherwise
it uses the engine-free anchor.


## Status in THIS environment

KataGo IS installed and was used to generate the shipped ground truth:
- engine: `/home/sankuai/conda/envs/katago/bin/katago` (v1.16.4, Eigen/CPU)
- network: `kata1-b28c512nbt-s8209287936-d4596492266.bin.gz`
- config: `analysis_example.cfg`

The precomputed normalized move table is in `../references/ground_truth.json`
(`move_table`). Re-run the scorer only to regenerate or verify it.
