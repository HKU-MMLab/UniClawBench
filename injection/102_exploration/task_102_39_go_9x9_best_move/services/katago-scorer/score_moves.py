#!/usr/bin/env python3
"""
KataGo per-move scorer + normalizer for Clawbench Go "single best move" tasks.

PURPOSE
-------
Given a Go position (SGF) and KataGo's analysis engine, this script queries
KataGo for the evaluation of EVERY legal move from the position, normalizes the
per-move scoreLead (and winrate) into [0,1], and writes a lookup table mapping
each move -> normalized score. The eval_rule uses that table to turn the
executor's chosen move into the final task score.

WHY THIS EXISTS AS A HARNESS (not pre-baked output)
---------------------------------------------------
KataGo requires its binary + a neural-network weights file + non-trivial
compute, which were NOT available in the task-authoring sandbox. This harness is
the reproducible bridge: install KataGo, point this script at it, and it emits
the canonical ground-truth scoring table. Until then, the eval_rule falls back to
the engine-free tactical anchor recorded in references/ground_truth.json.

USAGE
-----
  1) Install KataGo and download a network, e.g.:
       katago analysis -config analysis.cfg -model <network.bin.gz>
     (the analysis engine reads JSON queries on stdin, writes JSON on stdout)
  2) Run:
       python3 score_moves.py --sgf position.sgf --katago /path/to/katago \
           --model /path/to/model.bin.gz --config analysis.cfg \
           --out move_scores.json
  3) move_scores.json contains:
       {
         "best_move": "F5",
         "normalized": { "F5": 1.0, "E1": 0.42, ..., "pass": 0.0 },
         "raw": { "F5": {"scoreLead": ..., "winrate": ...}, ... }
       }

NORMALIZATION (canonical)
-------------------------
For every analyzed legal move m (Black's perspective):
    s(m)  = scoreLead(m)
    w(m)  = winrate(m)
    norm_score(m)   = (s(m) - min_s) / (max_s - min_s)        # 0..1
    norm_winrate(m) = (w(m) - min_w) / (max_w - min_w)        # 0..1
    score(m) = 0.5 * norm_score(m) + 0.5 * norm_winrate(m)    # 0..1
The argmax move => 1.0; the worst legal move => 0.0. A pass or illegal move => 0.

TASK SCORE
----------
final_task_score = score(chosen_move), rounded to 2 dp, clipped to [0,1].
"""
import argparse, json, subprocess, sys

def parse_sgf_setup(path):
    txt = open(path).read()
    size = 9
    import re
    m = re.search(r"SZ\[(\d+)\]", txt)
    if m: size = int(m.group(1))
    def coords(tag):
        return re.findall(tag + r"\[([a-z]{2})\]", txt)
    ab = coords("AB"); aw = coords("AW")
    def to_gtp(sgf2):
        col = ord(sgf2[0]) - ord('a'); row = ord(sgf2[1]) - ord('a')
        letters = "ABCDEFGHJKLMNOPQRST"  # GTP skips 'I'
        return letters[col] + str(size - row)
    black = [to_gtp(x) for x in ab]
    white = [to_gtp(x) for x in aw]
    return size, black, white

def build_query(size, black, white, komi=7.0):
    moves = []  # no move history; use initialStones
    stones = [["B", b] for b in black] + [["W", w] for w in white]
    return {
        "id": "clawbench_go",
        "rules": "tromp-taylor",
        "komi": komi,
        "boardXSize": size,
        "boardYSize": size,
        "initialStones": stones,
        "moves": moves,
        "analyzeTurns": [0],
        "maxVisits": 1000,
        "includeMovesOwnership": False,
        "reportDuringSearchEvery": 1e9,
    }

def normalize(move_infos):
    # move_infos: list of {"move": "F5", "scoreLead": x, "winrate": w}
    if not move_infos:
        return {}, None
    ss = [mi["scoreLead"] for mi in move_infos]
    ws = [mi["winrate"] for mi in move_infos]
    min_s, max_s = min(ss), max(ss)
    min_w, max_w = min(ws), max(ws)
    def nz(x, lo, hi):
        return 0.0 if hi <= lo else (x - lo) / (hi - lo)
    out = {}
    for mi in move_infos:
        score = 0.5 * nz(mi["scoreLead"], min_s, max_s) + 0.5 * nz(mi["winrate"], min_w, max_w)
        out[mi["move"]] = round(max(0.0, min(1.0, score)), 4)
    best = max(move_infos, key=lambda mi: 0.5*nz(mi["scoreLead"],min_s,max_s)+0.5*nz(mi["winrate"],min_w,max_w))
    return out, best["move"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sgf", required=True)
    ap.add_argument("--katago", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--komi", type=float, default=7.0)
    ap.add_argument("--out", default="move_scores.json")
    args = ap.parse_args()

    size, black, white = parse_sgf_setup(args.sgf)
    query = build_query(size, black, white, args.komi)

    proc = subprocess.Popen(
        [args.katago, "analysis", "-config", args.config, "-model", args.model],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    out, _ = proc.communicate(json.dumps(query) + "\n", timeout=600)

    move_infos = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        resp = json.loads(line)
        for mi in resp.get("moveInfos", []):
            move_infos.append({
                "move": mi["move"],
                "scoreLead": mi.get("scoreLead", 0.0),
                "winrate": mi.get("winrate", 0.0),
            })

    normalized, best = normalize(move_infos)
    raw = {mi["move"]: {"scoreLead": mi["scoreLead"], "winrate": mi["winrate"]} for mi in move_infos}
    result = {"best_move": best, "normalized": normalized, "raw": raw,
              "board_size": size, "komi": args.komi}
    json.dump(result, open(args.out, "w"), indent=2)
    print("wrote", args.out, "best_move=", best, "n_moves=", len(normalized))

if __name__ == "__main__":
    main()
