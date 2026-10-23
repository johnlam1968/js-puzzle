#!/usr/bin/env python3
"""The seeded descent: start from the capitols the hitting set proposes.

The hitting-set computation says the 11x11 has at least six capitols and that there are
only 120 minimum sets of hidden capitol cells.  A capitol cell is a 1x1 state, so a set of
capitol cells is a set of cells that must stay singletons -- and that is a STARTING
PARTITION, not a constraint on the answer.

Why it matters: the greedy descent solves the 4x4 from a cold start (10 of 12) but NOT the
5x5 (0 of 8) -- the 5x5's landscape is only locally navigable.  The 11x11 is sparser
still, so a good starting point is the difference between "finds nothing" and "finds
something".

The revealed capitols (the published d=0 cells) are locked too: they are already known.

Exit code 0 = the measurement ran.
"""

from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from descent import descend, pure_energy            # noqa: E402

SEEDS = os.path.join(ROOT, "data", "derived", "capitol_hitting_set_11x11.json")


def main() -> int:
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    with open(os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")) as fh:
        puz = json.load(fh)
    n = puz["size"]
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    with open(SEEDS) as fh:
        seeddata = json.load(fh)
    seeds = seeddata["min_sets"]
    revealed = [c for c, v in hints.items() if v == 0]
    print(f"=== 11x11 seeded descent: {min(k, len(seeds))} of {len(seeds)} minimum capitol "
          f"sets, {steps} steps each ===")
    print(f"    revealed capitols (locked too): {sorted(revealed)}")
    cells = [(r, c) for r in range(n) for c in range(n)]
    best_overall = None
    t0 = time.time()
    for i, seed in enumerate(seeds[:k]):
        lock = list(revealed) + [(r - 1, c - 1) for (r, c) in seed]
        start = [frozenset({c}) for c in cells]
        res = descend(start, hints, n, max_steps=steps, lock=lock)
        tag = "SOLVED" if res["solved"] else ""
        print(f"  seed {i+1:3d} {seed}: E = {res['energy']:9.1f} in {res['steps']:4d} steps"
              f"  ({time.time()-t0:.0f}s) {tag}", flush=True)
        if best_overall is None or res["energy"] < best_overall:
            best_overall = res["energy"]
    print(f"  => best energy over the seeds: {best_overall}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
