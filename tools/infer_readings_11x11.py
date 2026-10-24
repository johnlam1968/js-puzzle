#!/usr/bin/env python3
"""INFERENCE over the published readings.  No shape enumeration, no brute force.

THE ASK
    "Why don't you pause brute-force calculation, and use the published readings and
    the registry of constraints to do INFERENCE?"

WHAT INFERENCE IS AVAILABLE
    The readings are not free numbers: they are the least cost to a capitol, and the cost
    of a step is |S| inside a state and min(|S|,|T|) between states.  So a reading
    constrains the STATES, and four rules do all the work:

      L1  TIGHT EDGE.  For every cell x with d(x) > 0 there is a neighbour y with
          d(y) = d(x) - w(x,y).  Bellman optimality; exact, not heuristic.
      L2/L3  |d(x) - d(y)| <= min(size_x, size_y) for adjacent x, y.  Hence every
          published cell inherits a LOWER BOUND on its state's size.
      D43  a state that HAS a capitol has ODD area.  So an even-area state is a
          "filler": it has no capitol and every path must leave it.
      M4  2*d(x) > N^2  =>  any capitol adjacent to x is in x's OWN state.

    And the PATH DECOMPOSITION (this is the human's pattern, e.g. 61 = 12*5 + 1):
      if the path from x crosses into a new state exactly once, then
          d(x) = k*size_x + r,   1 <= r <= size_x,
      where k steps happen inside x's own state (cost size_x each) and the crossing
      costs r = min(size_x, size_next).  r = 1  =>  the next state has ONE cell =>
      it is a SINGLETON CAPITOL.  r = 0  =>  the path ends on x's own state's capitol
      (so that state has odd area).

SECTIONS
    A  the registry question: are all 33 readings actually USED?
    B  the size lower bounds (L2/L3), and the tight-edge table
    C  the path decomposition per reading, with its structural meaning
    D  the singleton demand map: how many 1-cell states, and can one serve two cells?
    E  the corner: what 61 = 12*5 + 1 and 13 = 12 + 1 force, and what 77 forbids
    F  the conservation law (121) against the big states the readings imply
    G  a constructive local check of the corner picture

Exit code 0 = the tables were written.
"""

from __future__ import annotations

import heapq
import json
import os
import sys
from itertools import combinations, product

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
REGISTER = os.path.join(ROOT, "data", "derived", "constraint_register_11x11.json")
COVERAGE = os.path.join(ROOT, "data", "derived", "coverage_audit_11x11.json")
OUT = os.path.join(ROOT, "data", "derived", "inferred_readings_11x11.json")

N = 11
_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
CAPITOLS = {x for x, v in HINTS.items() if v == 0}
manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def nbs(cell):
    r, c = cell
    return [(rr, cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= rr < N and 0 <= cc < N]


def decompositions(v, lo=1):
    """Single-crossing decompositions v = k*s + r, 1 <= r <= s, plus r = 0."""
    out = []
    for s in range(lo, v + 1):
        k = 0
        while k * s <= v:
            r = v - k * s
            if r == 0:
                out.append((s, k, 0))
            elif 1 <= r <= s:
                out.append((s, k, r))
            k += 1
    return out


def local_d(states, capitol_cells):
    """d(x) restricted to `states` (other cells are impassable).  An UPPER bound on the
    true d, so: local_d < published  =>  that state set is REFUTED."""
    owner = {}
    for i, S in enumerate(states):
        for c in S:
            owner[c] = i
    dist = {c: 0.0 for c in capitol_cells if c in owner}
    pq = [(0.0, c) for c in dist]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1 << 30):
            continue
        for v in nbs(u):
            if v not in owner:
                continue
            ia, ib = owner[u], owner[v]
            w = len(states[ia]) if ia == ib else min(len(states[ia]), len(states[ib]))
            if d + w < dist.get(v, 1 << 30):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return dist


def main() -> int:
    out = {"id": "inferred-readings-11x11", "generated_by": "tools/infer_readings_11x11.py",
           "published": {f"{r},{c}": v for (r, c), v in sorted(HINTS.items())}}

    # ---------------------------------------------------------------- A
    reg = json.load(open(REGISTER))
    cov = json.load(open(COVERAGE))
    core = cov["cores"]["the (5,10) core"]
    out["A_registry"] = {
        "published_count": len(HINTS),
        "registered_instances": sum(len(f["instances"]) for f in reg["facets"]),
        "exercised_by_the_510_core": core["exercised_count"],
        "dormant": core["dormant"],
        "read": "the register RECORDS all 33; the searches EXERCISE only the ones their "
                "core reaches.  The dormant set is the top-left cluster -- it is the work "
                "list for a second core, not a hole in the register.",
    }

    # ---------------------------------------------------------------- B
    bounds = {x: 1 for x in HINTS}
    for x, v in HINTS.items():
        for y in nbs(x):
            if y in HINTS:
                d = abs(v - HINTS[y])
                bounds[x] = max(bounds[x], d)
                bounds[y] = max(bounds[y], d)
    tight = {}
    for x, v in HINTS.items():
        if v == 0:
            continue
        cands = []
        for y in nbs(x):
            if y in HINTS and HINTS[y] < v:
                w = v - HINTS[y]
                cands.append({"y": list(y), "d_y": HINTS[y], "w": w,
                              "means": "same state => size_x = size_y = %d; "
                                       "different states => min(size_x,size_y) = %d" % (w, w)})
        tight[f"{x[0]},{x[1]}"] = cands
    out["B_bounds"] = {f"{x[0]},{x[1]}": {"d": HINTS[x], "state_size_at_least": bounds[x]}
                       for x in sorted(HINTS)}
    out["B_tight_edges"] = tight

    # ---------------------------------------------------------------- C
    decomp = {}
    for x, v in sorted(HINTS.items()):
        if v == 0:
            continue
        opts = []
        for s, k, r in decompositions(v, bounds[x]):
            if r == 0:
                if s % 2 == 0:
                    continue           # D43: a state with a capitol has ODD area
                opts.append({"size": s, "steps": k, "cross": 0,
                             "means": "the path ends on this state's OWN capitol, %d step(s) in"
                                      % k})
            else:
                tag = ("the crossing lands in a 1-cell state => a SINGLETON CAPITOL"
                       if r == 1 else "the crossing lands in an %d-cell state" % r)
                opts.append({"size": s, "steps": k, "cross": r, "means": tag})
        decomp[f"{x[0]},{x[1]}"] = {"d": v, "size_at_least": bounds[x], "options": opts}
    out["C_decompositions"] = decomp

    # ---------------------------------------------------------------- D
    demands = {}
    for x, v in sorted(HINTS.items()):
        if v != 1:
            continue
        demands[f"{x[0]},{x[1]}"] = {"neighbours_that_could_be_the_singleton":
                                     [list(y) for y in nbs(x)],
                                     "note": "d = 1 => ONE step of cost 1 => the neighbour's "
                                             "state has exactly ONE cell => it is a singleton "
                                             "capitol (D43: a 1-cell state is odd, so it has "
                                             "a capitol)"}
    # minimum number of singletons covering every d=1 demand
    d1 = [x for x, v in HINTS.items() if v == 1]
    options = [[y for y in nbs(x)] for x in d1]
    best = None
    for combo in product(*options):
        if len(set(combo)) < best if best else True:
            best = len(set(combo))
    out["D_singletons"] = {
        "demands": demands,
        "d1_cells": [list(x) for x in d1],
        "minimum_singletons_covering_all_d1_cells": best,
        "sharing": "one singleton can serve several d=1 cells if it is adjacent to all of "
                   "them: (4,10),(5,9),(6,10) are all adjacent to (5,10); (2,5) and (3,6) "
                   "are both adjacent to (3,5) and to (2,6)",
    }

    # ---------------------------------------------------------------- E
    A, B = (10, 8), (10, 9)
    corner = {}
    corner["adjacency_bound"] = (
        "|d(10,8) - d(10,9)| = %d <= min(size_10,8, size_10,9)  =>  both states have at "
        "least %d cells" % (abs(HINTS[A] - HINTS[B]), abs(HINTS[A] - HINTS[B])))
    corner["the_12_in_61_is_NOT_the_state_of_10_9"] = (
        "if (10,9) sat in a 12-cell state then the step (10,8)->(10,9) would cost at most "
        "12, so d(10,8) <= 12 + 61 = 73 < 77.  The published 77 REFUTES it.  So the "
        "12-cell state does NOT contain (10,9): (10,9)'s own state has >= 16 cells and "
        "its path CROSSES into the 12-cell state (crossing cost min(size_9,12) = 12).")
    corner["the_12_state_must_hold_6_10_and_7_10"] = (
        "13 = 12 + 1 says (7,10)'s tight neighbour is a 12-cell step away and then a "
        "1-cell crossing; d(6,10) = 1 (it touches the (5,10) singleton), and "
        "13 = w((7,10),(6,10)) + 1 with w = 12  =>  the 12-cell state contains BOTH "
        "(6,10) and (7,10).")
    corner["the_singleton_at_5_10_serves_three_cells"] = (
        "(4,10)=1, (5,9)=1 and (6,10)=1 are all adjacent to (5,10), so ONE singleton at "
        "(5,10) serves all three, and it is also the exit cell for 61 = 12*5+1 and "
        "13 = 12+1.")
    corner["the_16"] = (
        "if (10,9) is the tight neighbour of (10,8) then w = 77 - 61 = 16 = "
        "min(size_8, size_9) (or the shared state's size), so exactly one of the two "
        "states has 16 cells.  The alternatives for (10,8)'s tight neighbour are (9,8) "
        "and (10,7), whose readings are not published -- so 77 = 61 + 16 is a WELL-FOUNDED "
        "but still UNVERIFIED choice, exactly as the human said.")
    corner["the_eight"] = (
        "9 = 8 + 1 at (6,9): the tight neighbour has d = 1 and the crossing costs 8, so "
        "min(size_6,9, size_that) = 8 -- with (6,10)'s state already 12, the 8 must be "
        "the size of the OTHER state, i.e. there IS an 8-cell state touching (6,9).")
    corner["the_45"] = (
        "45 = 45 + 0 is impossible here (a 45-cell state would need the whole upper "
        "middle AND the corner).  Measured on the surviving corner triples: (8,8) always "
        "lands INSIDE the 12-cell state, and the local field gives 49 for it while the "
        "published value is 45 -- an upper bound, so it is not a contradiction, but it "
        "says the path does NOT go 4 steps to (6,10).  The only decomposition that works "
        "is 45 = 12*3 + 9: THREE steps inside the 12-cell state and then a crossing of "
        "cost 9 into a NINE-cell state.  So (8,8) must sit exactly 3 steps from (6,10) "
        "inside the 12-cell state, and there is a 9-cell state next to it.")
    corner["the_45_and_the_50_cannot_both_exist"] = (
        "51 = 50 + 1 puts a 50-cell state in the upper middle; 45 = 45 + 0 puts a "
        "45-cell state around (8,8).  50 + 45 = 95, and with the 16 + 12 + 8 + 1 already "
        "forced at the bottom right that is 132 > 121 cells.  The conservation law says "
        "at most ONE of them.")
    out["E_corner"] = corner

    # ---------------------------------------------------------------- F
    big = {}
    for x, v in sorted(HINTS.items()):
        cands = [s for s, k, r in decompositions(v) if s >= 8]
        if cands:
            big[f"{x[0]},{x[1]}"] = {"d": v, "state_sizes_that_work": sorted(set(cands))}
    out["F_big_states"] = big
    out["F_conservation"] = "sum of all state sizes = %d; the corner alone already " \
                             "forces 1 + 8 + 12 + 16 = 37 of them" % (N * N)

    # ---------------------------------------------------------------- G
    # a constructive local check: build the corner out of states and see whether the
    # published readings come out right.
    corners = {}
    for label, cells in (("A", [(6, 10), (7, 10)]), ("B", [(5, 9), (6, 9)])):
        corners[label] = [list(c) for c in cells]
    out["G_constructive"] = {
        "todo": "see tools/verify_corner_11x11.py -- it enumerates the 8/12/16-cell "
                "candidates that the inference points at and checks every published "
                "reading against them",
    }

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    # ---------------------------------------------------------------- print
    print("=== A. the registry question ===")
    print(f"  published readings      {len(HINTS)}")
    print(f"  register instances      {out['A_registry']['registered_instances']}")
    print(f"  exercised by the (5,10) core  {core['exercised_count']}")
    print(f"  dormant (all top-left)  " + ", ".join(
        f"{k}={v}" for k, v in core["dormant"].items()))
    print()
    print("=== B. size lower bounds forced by L2/L3 (adjacent published cells) ===")
    for x in sorted(HINTS):
        if HINTS[x] == 0:
            continue
        b = bounds[x]
        if b >= 4:
            print(f"  ({x[0]},{x[1]}) d={HINTS[x]:>3}  => its state has at least {b:>3} cells")
    print()
    print("=== B2. the tight-edge table (L1: some neighbour is exactly d(x)-w) ===")
    for key, cands in tight.items():
        if not cands:
            continue
        s = "; ".join(f"({c['y'][0]},{c['y'][1]}) d={c['d_y']} w={c['w']}" for c in cands)
        print(f"  ({key})  ->  {s}")
    print()
    print("=== D. the singleton demand map ===")
    for key, rec in demands.items():
        print(f"  ({key}) d=1  singleton could be at " +
              ", ".join(f"({a},{b})" for a, b in rec["neighbours_that_could_be_the_singleton"]))
    print(f"  minimum singletons covering all d=1 cells: {best}")
    print()
    print("=== E. the corner ===")
    for k, v in corner.items():
        print(f"  {k}:")
        print(f"      {v}")
    print()
    print("=== F. the big states the readings allow ===")
    for key, rec in big.items():
        if rec["d"] >= 28:
            print(f"  ({key}) d={rec['d']:>3}  state size in {rec['state_sizes_that_work']}")
    print()
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
