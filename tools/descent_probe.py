#!/usr/bin/env python3
"""Measure the greedy descent: does it find the solution from a COLD start?

The reviewer measured the descent from the 4x4 (60 random legal tilings, all solved) and
from the 5x5's solution's own neighbours (23/23, one step each).  The 5x5 COLD start was
the piece they could not measure -- it needs the 5x5's state catalogue.  This tool does
that, and it also records where the descent gets stuck on the 11x11, which is the number
the model should be aimed at.

  4x4 counterexample : N random legal tilings -> how many reach energy 0?
  5x5 official       : N random legal tilings -> how many reach energy 0?
  11x11 official     : from an all-singleton start -> where does it stop, and at what energy?

Exit code 0 = the measurement ran.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from descent import pure_energy                        # noqa: E402
from descent import descend, random_legal_tiling        # noqa: E402
from anneal2 import LegalStates                        # noqa: E402


def load(name):
    with open(os.path.join(ROOT, "data", "puzzles", name, "puzzle.json")) as fh:
        return json.load(fh)


def hints_of(puz):
    return {(h["row"], h["col"]): h["value"] for h in puz["hints"]}


def cold_start_test(name, n_starts, seed=0):
    puz = load(name)
    n = puz["size"]
    hints = hints_of(puz)
    print(f"=== {name}: {n_starts} random legal COLD starts, greedy descent ===")
    legal = LegalStates(n)
    rng = random.Random(seed)
    solved = 0
    steps = []
    bests = []
    t0 = time.time()
    for k in range(n_starts):
        start = random_legal_tiling(n, legal, rng)
        res = descend(start, hints, n, max_steps=400)
        if res["solved"]:
            solved += 1
        steps.append(res["steps"])
        bests.append(res["energy"])
        print(f"  start {k+1:3d}: E0 = {pure_energy(start, hints, n):7.1f} -> E = "
              f"{res['energy']:7.1f} in {res['steps']:3d} steps"
              f"{'   SOLVED' if res['solved'] else ''}", flush=True)
    print(f"  => {solved}/{n_starts} solved; mean steps "
          f"{sum(steps)/max(len(steps),1):.1f}; best energies {sorted(bests)[:5]}; "
          f"{time.time()-t0:.0f}s")
    return solved, n_starts


def eleven_eleven_probe():
    puz = load("official-11x11")
    n = puz["size"]
    hints = hints_of(puz)
    print("=== 11x11 official: greedy descent from an all-singleton start ===")
    # no catalogue needed: the all-singleton start is built directly
    cells = [(r, c) for r in range(n) for c in range(n)]
    start = [frozenset({c}) for c in cells]
    t0 = time.time()
    res = descend(start, hints, n, max_steps=60, verbose=True)
    print(f"  => stopped at E = {res['final_energy']:g} after {res['steps']} steps "
          f"({time.time()-t0:.0f}s); stuck because: {res['stuck_at']}")
    print(f"  the descent's best: E = {res['energy']:g}")
    return res


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "4x4"):
        cold_start_test("counterexample-4x4-two-answers", 12)
    if which in ("all", "5x5"):
        cold_start_test("official-example-5x5", 8)
    if which in ("all", "11x11"):
        eleven_eleven_probe()
    return 0


if __name__ == "__main__":
    sys.exit(main())
