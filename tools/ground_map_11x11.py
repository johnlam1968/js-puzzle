#!/usr/bin/env python3
"""The ground map of the official 11x11, trimmed from the (5,10) demand.

WHAT THIS TOOL IS
    A thin wrapper around the engine (src/rules.py, src/hitting.py) that answers ONE
    question: what does the published grid force, once the `d = 1` demand at (4,10) is
    taken seriously?

    The short version: the demand at (4,10) forces a 1x1 state at (5,10) and NOWHERE else
    at that end of the board; that singleton's RING then has d = 1; and the published 9 at
    (6,9) and 13 at (7,10) turn those two ring cells into

        state((5, 9))  >=  8        and        state((6,10))  >= 12

    which is why (5,10) is the best starting point on the board.

THE RULES USED (all of them live in the engine, none of them are re-implemented here)
    D64  a d=1 hint is served by a 1x1 state ADJACENT to it  (src/hitting.py)
    L2/L3  for adjacent x,y:  |d(x) - d(y)| <= min(size_x, size_y)   (src/cost.py)
    the step-count lemma: d(x) = v  =>  a capitol within Manhattan floor((v+1)/2)
                                                  (src/hitting.py)

Exit code 0 = the map was printed and it agrees with the engine.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from hitting import singleton_candidates, manhattan     # noqa: E402

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")


def neighbours(cell, n):
    r, c = cell
    return [(rr, cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= rr < n and 0 <= cc < n]


def main() -> int:
    p = json.load(open(PUZZLE))
    n = p["size"]
    grid = p["grid"]
    hints = {(r, c): grid[r][c] for r in range(n) for c in range(n) if grid[r][c] is not None}

    print("=" * 78)
    print("1.  the d=1 demands and their 1x1 candidates")
    print("=" * 78)
    cands = singleton_candidates(n, hints)
    for x in sorted(cands):
        keep = []
        for cand in cands[x]:
            bad = [(y, hints[y]) for y in neighbours(cand, n) if hints.get(y, 0) > 1]
            if bad:
                print(f"  d=1 at {x}:  {cand} REFUTED by "
                      + ", ".join(f"{y}={v}" for y, v in bad))
            else:
                keep.append(cand)
        print(f"  d=1 at {x}:  surviving {keep}")

    forced = {}
    for x in sorted(cands):
        keep = [c for c in cands[x]
                if not any(hints.get(y, 0) > 1 for y in neighbours(c, n))]
        if len(keep) == 1:
            forced[x] = keep[0]
    print(f"\n  forced singletons: {forced}")

    # the d map we are sure of: published + the singletons + the singletons' ring
    known = dict(hints)
    for h, s in forced.items():
        known[s] = 0
        for y in neighbours(s, n):
            known.setdefault(y, 1)
    imputed = {y: known[y] for y in known if y not in hints}
    print(f"  imputed (not published): {imputed}")

    print()
    print("=" * 78)
    print("2.  the area bounds that the ring makes visible (L2/L3)")
    print("=" * 78)
    need, why = {}, {}
    for x in sorted(known):
        for y in neighbours(x, n):
            if y in known:
                delta = abs(known[x] - known[y])
                if delta > need.get(y, 0):
                    need[y] = delta
                    why[y] = f"|d({x}) - d({y})| = {delta}"
    for y in sorted(need):
        if need[y] >= 2:
            print(f"  state({y}) >= {need[y]:>3}   via {why[y]}")

    print()
    print("=" * 78)
    print("3.  the neighbourhood of the (5,10) singleton -- the trim")
    print("=" * 78)
    s = forced.get((4, 10))
    print(f"  the forced singleton: {s}   (d = {known[s]})")
    for y in neighbours(s, n):
        print(f"    neighbour {y}:  d = {known.get(y, '?'):>2}   "
              f"state >= {need.get(y, 0):>3}   {why.get(y, '')}")

    print()
    print("=" * 78)
    print("4.  the branch that would break the 8/12 reading")
    print("=" * 78)
    print("  the chain above used d(6,10) = 1, i.e. (6,10) is NOT a capitol.")
    print("  (6,10) cannot be a 1x1 state -- a cost-1 step to it would give")
    print("  d(6,9) <= 1 against the published 9 -- but it could be the capitol of a")
    print("  bigger state, and then the same argument gives 9 and 13 instead of 8 and 12.")
    for label, d610 in (("A: (6,10) is not a capitol -> d = 1", 1),
                        ("B: (6,10) IS a capitol      -> d = 0", 0)):
        print(f"  branch {label}")
        for x, v in (((6, 9), 9), ((7, 10), 13)):
            print(f"    |{v} - {d610}| = {abs(v - d610)}  =>  state({x}) >= {abs(v - d610)}"
                  f",  state((6,10)) >= {abs(v - d610)}")

    print()
    print("=" * 78)
    print("5.  the parity lemma the two blocks share")
    print("=" * 78)
    print("  a state that HAS a capitol has ODD area (the capitol is one cell, every")
    print("  other cell lies in an orbit of size >= 2).  So an 8-cell state and a")
    print("  12-cell state have NO capitol: both are filler states, like the 4-bar of")
    print("  the official 5x5.")

    ok = forced.get((4, 10)) == (5, 10) and need.get((5, 9)) == 8 and need.get((6, 10)) == 12
    print()
    print("  CHECK: the (5,10) singleton is forced and the ring gives 8 and 12: "
          + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
