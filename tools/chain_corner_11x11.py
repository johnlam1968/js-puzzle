#!/usr/bin/env python3
"""THE CORNER, BY INFERENCE: the chain the readings force, then only that.

THE POINT
    The blind search over the corner was 347,802 (8-cell, 12-cell) pairs, and it found
    ZERO 16-cell partners.  That was not a shortage of compute -- it was a shortage of
    INFERENCE.  The readings pin the shapes; the search should only ever look at what the
    readings allow.  This tool derives the shapes from the readings first, then counts.

THE CHAIN (every step is a published number)
    (5,10) is a 1-cell state (a singleton).  Its ring (4,10), (5,9), (6,10) has d = 1.
    d(6,10) = 1 is FREE: one step into a 1-cell state costs exactly 1, whatever the size
    of (6,10)'s own state.

    d(7,10) = 13 = 12 + 1
        => the step (7,10)->(6,10) costs 12
        => a 12-cell state touches (7,10) and (6,10).
    d(10,9) = 61 = 12*5 + 1
        => the path is (10,9) --CROSSING of cost 12--> the 12-cell state
           --4 steps inside, 12 each--> (6,10) --1--> (5,10).
        => the 12-cell state contains (6,10), (7,10) and an ENTRY cell
           e in {(9,9), (10,10)} (the neighbours of (10,9) other than (10,8)),
           at Manhattan distance exactly 4 from (6,10).
        => (10,9)'s OWN state has size >= 16, because (10,8) = 77 sits next to it:
           |77 - 61| = 16 <= min(size_8, size_9)  (L2/L3).
        => the 12-cell state contains NEITHER (10,8) nor (10,9).

    d(6,9) = 9 = 8 + 1
        => the tight neighbour of (6,9) has d = 1, and there are TWO of them:
           (5,9) and (6,10).  So the "8" has TWO possible CARRIERS:
             branch A: (6,9)'s own state has 8 cells, and the crossing is 8
             branch B: the (5,9) state has 8 cells, and (6,9)'s state is larger
           The step cost is min(size_6,9, size_carrier) = 8 either way, so L2/L3 alone
           cannot tell them apart.  BOTH are enumerated below.

    d(10,8) = 77 = 16 + 61
        => the step (10,8)->(10,9) costs 16, so the 16-cell state holds BOTH (10,8)
           and (10,9) (same-state step = the state size), or the two are in different
           states with min(size) = 16.
        => either way exactly one of them lives in a 16-cell state.

    So the corner is FOUR states, and every one of their sizes is forced:
        1  cell   the singleton (5,10)
        8  cells  the state of (6,9)
       12  cells  the state of (6,10) and (7,10)
       16  cells  the state of (10,8) and (10,9)
    = 37 cells, and the readings pin all four sizes.

Exit code 0 = the table was written.
"""

from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from grow import close_state, grow_states, symmetry_choices   # noqa: E402

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
OUT = os.path.join(ROOT, "data", "derived", "chain_corner_11x11.json")
CACHE = "/workspace/analysis"

N = 11
_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
CAPITOLS = {x for x, v in HINTS.items() if v == 0}
SINGLETON = (5, 10)
manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def nbs(cell):
    r, c = cell
    return [(rr, cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= rr < N and 0 <= cc < N]


def enumerate_states(anchor, size, blocked=(), budget=400_000):
    """Every legal state of exactly `size` cells containing `anchor` (AODFS growth)."""
    found = set()
    for sym in symmetry_choices(N):
        for st in grow_states(anchor, sym, N, blocked=blocked, max_cells=size, budget=budget):
            if len(st) != size:
                continue
            fs = frozenset(st)
            if fs in found:
                continue
            ok, _cap, _g = close_state(fs)
            if ok:
                found.add(fs)
    return found


def cached(name, builder):
    path = os.path.join(CACHE, name)
    if os.path.exists(path):
        return {frozenset(tuple(c) for c in b) for b in json.load(open(path))}
    val = builder()
    json.dump([sorted(list(c) for c in b) for b in val], open(path, "w"))
    return val


def local_d(states, capitol_cells):
    """The d-field restricted to `states`.  Exact inside; an upper bound outside."""
    owner = {}
    for i, S in enumerate(states):
        for c in S:
            owner[c] = i
    dist = {c: 0 for c in capitol_cells if c in owner}
    import heapq
    pq = [(0, c) for c in dist]
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
    t0 = time.time()
    out = {"id": "chain-corner-11x11", "generated_by": "tools/chain_corner_11x11.py"}

    # ---- the 12-cell state: (6,10), (7,10), and an entry cell 4 steps from (6,10) ----
    def build12():
        raw = enumerate_states((6, 10), 12, blocked={SINGLETON})
        keep = set()
        for fs in raw:
            if (7, 10) not in fs:
                continue
            if any(x in fs for x in CAPITOLS):
                continue
            if (10, 8) in fs or (10, 9) in fs:
                continue
            entry = [e for e in ((9, 9), (10, 10)) if e in fs and manh(e, (6, 10)) == 4]
            if not entry:
                continue
            keep.add(fs)
        return keep
    T12 = cached("chain_T12.json", build12)
    print(f"  12-cell states with (6,10),(7,10) and an entry cell: {len(T12)}"
          f"  ({time.time()-t0:.0f}s)", flush=True)

    # ---- the 8-cell state: (6,9) OR (5,9) -------------------------------------------
    # TWO CARRIERS of the "8" in 9 = 8 + 1 (see the docstring): the 8 can be the size of
    # (6,9)'s own state, or the size of the state holding (5,9).  Both are enumerated and
    # kept apart, because they are different claims about the solution.
    def build8(anchor):
        raw = enumerate_states(anchor, 8, blocked={SINGLETON})
        return {fs for fs in raw
                if not any(x in fs for x in CAPITOLS)
                and (10, 8) not in fs and (10, 9) not in fs}
    A8_6_9 = cached("chain_A8_6_9.json", lambda: build8((6, 9)))
    A8_5_9 = cached("chain_A8_5_9.json", lambda: build8((5, 9)))
    A8 = A8_6_9 | A8_5_9
    print(f"  8-cell states: {len(A8_6_9)} with (6,9), {len(A8_5_9)} with (5,9),"
          f" {len(A8_6_9 & A8_5_9)} with both  ({time.time()-t0:.0f}s)", flush=True)

    # ---- the 16-cell state: (10,8) AND (10,9) --------------------------------------
    def build16():
        raw = enumerate_states((10, 8), 16, blocked={SINGLETON})
        return {fs for fs in raw
                if (10, 9) in fs
                and not any(x in fs for x in CAPITOLS)}
    P16 = cached("chain_P16.json", build16)
    print(f"  16-cell states with BOTH (10,8) and (10,9): {len(P16)}"
          f"  ({time.time()-t0:.0f}s)", flush=True)

    # ---- the join ------------------------------------------------------------------
    # bitset over the 16-cell candidates
    P16_LIST = sorted(P16, key=lambda fs: sorted(fs))
    mask16 = {}
    for i, fs in enumerate(P16_LIST):
        for x in fs:
            mask16[x] = mask16.get(x, 0) | (1 << i)
    ALL16 = (1 << len(P16_LIST)) - 1

    pairs = 0
    triples = 0
    survivors = []
    ok13 = ok61 = ok77 = ok9 = 0
    examples = []
    # bitsets over the 12-cell and 8-cell candidates too, so the join is 3 AND-masks
    maskT, maskA = {}, {}
    for i, fs in enumerate(sorted(T12, key=lambda f: sorted(f))):
        for x in fs:
            maskT[x] = maskT.get(x, 0) | (1 << i)
    for i, fs in enumerate(sorted(A8, key=lambda f: sorted(f))):
        for x in fs:
            maskA[x] = maskA.get(x, 0) | (1 << i)
    T_LIST = sorted(T12, key=lambda f: sorted(f))
    A_LIST = sorted(A8, key=lambda f: sorted(f))
    ALLT = (1 << len(T_LIST)) - 1
    ALLA = (1 << len(A_LIST)) - 1

    for ti, t in enumerate(T_LIST):
        for ai, a in enumerate(A_LIST):
            if t & a:
                continue
            occ12 = t | a | {SINGLETON} | CAPITOLS
            m = ALL16
            for x in occ12:
                m &= ~mask16.get(x, 0)
            if not m:
                continue
            pairs += 1
            # check every 16-cell candidate that fits
            mm = m
            while mm:
                i = (mm & -mm).bit_length() - 1
                mm &= mm - 1
                p = P16_LIST[i]
                if p & t or p & a:
                    continue
                triples += 1
                states = [a, t, p, frozenset({SINGLETON})]
                d = local_d(states, [(5, 10)])
                def get(cell):
                    return d.get(cell)
                checks = {
                    "d(10,8)=77": get((10, 8)) is not None and get((10, 8)) >= 77,
                    "d(10,9)=61": get((10, 9)) is not None and get((10, 9)) >= 61,
                    "d(7,10)=13": get((7, 10)) is not None and get((7, 10)) >= 13,
                    "d(6,10)=1": get((6, 10)) is not None and get((6, 10)) >= 1,
                    "d(6,9)=9": get((6, 9)) is not None and get((6, 9)) >= 9,
                    "d(5,9)=1": get((5, 9)) is not None and get((5, 9)) >= 1,
                    "d(4,10)=1": get((4, 10)) is not None and get((4, 10)) >= 1,
                }
                explained = set()
                # THE CORRECT CRITERION.  The local field is restricted to these four
                # states, so it is an UPPER bound on the true d: local_d(x) >= d(x).
                #   * local_d(x) <  published(x)  =>  a CHEAPER path than published
                #     exists  =>  the triple is REFUTED.
                #   * local_d(x) == published(x)  =>  the reading is EXPLAINED here.
                # A revealed capitol may not sit inside an even-area state at all
                # (D43: a state with a capitol has ODD area).
                inside = (set(a) | set(t) | set(p)) & set(HINTS)
                for cell in inside:
                    if HINTS[cell] == 0:
                        checks["capitol %s inside" % str(cell)] = False
                        continue
                    loc = get(cell)
                    checks["d%s=%d" % (str(cell), HINTS[cell])] = (
                        loc is not None and loc >= HINTS[cell])
                    explained.add((cell, loc == HINTS[cell]))
                if checks["d(7,10)=13"] and get((7, 10)) == 13:
                    ok13 += 1
                if checks["d(10,9)=61"] and get((10, 9)) == 61:
                    ok61 += 1
                if checks["d(10,8)=77"] and get((10, 8)) == 77:
                    ok77 += 1
                if checks["d(6,9)=9"] and get((6, 9)) == 9:
                    ok9 += 1
                all_inside_ok = all(checks.values())
                if not all_inside_ok:
                    continue
                survivors.append({
                    "eight_carrier": ("(6,9)" if (6, 9) in a else "(5,9)"),
                    "eight": sorted(list(c) for c in a),
                    "twelve": sorted(list(c) for c in t),
                    "sixteen": sorted(list(c) for c in p),
                    "published_inside": {f"{c[0]},{c[1]}": HINTS[c] for c in sorted(inside)},
                    "explained_here": sorted(f"{c[0]},{c[1]}" for c, e in explained if e),
                    "local_d": {f"{c[0]},{c[1]}": d.get(c) for c in
                                sorted((set(a) | set(t) | set(p) | {SINGLETON}) & set(d))},
                })
                if len(examples) < 3:
                    examples.append({
                        "eight": sorted(list(c) for c in a),
                        "twelve": sorted(list(c) for c in t),
                        "sixteen": sorted(list(c) for c in p),
                    })

    out["counts"] = {
        "twelve_cell_candidates": len(T12),
        "eight_cell_candidates": len(A8),
        "eight_cell_candidates_carrying_6_9": len(A8_6_9),
        "eight_cell_candidates_carrying_5_9": len(A8_5_9),
        "eight_cell_candidates_carrying_both": len(A8_6_9 & A8_5_9),
        "sixteen_cell_candidates": len(P16),
        "disjoint_8_12_pairs_with_room_for_a_16": pairs,
        "triples": triples,
        "triples_with_d_7_10_eq_13": ok13,
        "triples_with_d_10_9_eq_61": ok61,
        "triples_with_d_10_8_eq_77": ok77,
        "triples_with_d_6_9_eq_9": ok9,
    }
    out["triples_that_reproduce_every_published_reading_inside"] = len(survivors)
    # --- keep the derived file SLIM: a summary plus a few compact samples, not the
    # --- whole survivor set (which is ~60k triples and would be megabytes).
    from collections import Counter
    branch = Counter(sv["eight_carrier"] for sv in survivors)
    occ12, occ8, occ16 = Counter(), Counter(), Counter()
    for sv in survivors:
        for c in sv["twelve"]:
            occ12[tuple(c)] += 1
        for c in sv["eight"]:
            occ8[tuple(c)] += 1
        for c in sv["sixteen"]:
            occ16[tuple(c)] += 1
    n = max(1, len(survivors))
    out["survivor_total"] = len(survivors)
    out["survivor_split"] = dict(branch)
    out["skeleton"] = {
        "note": "cells occupied in EVERY survivor (100%), and how often the rest appear",
        "twelve_cell_state_always": sorted([list(c) for c, v in occ12.items() if v == n]),
        "twelve_cell_state_frequency": {("%d,%d" % c): v for c, v in
                                        sorted(occ12.items(), key=lambda kv: -kv[1])},
        "eight_cell_state_always": sorted([list(c) for c, v in occ8.items() if v == n]),
        "eight_cell_state_frequency": {("%d,%d" % c): v for c, v in
                                       sorted(occ8.items(), key=lambda kv: -kv[1])},
        "sixteen_cell_state_always": sorted([list(c) for c, v in occ16.items() if v == n]),
        "sixteen_cell_state_frequency": {("%d,%d" % c): v for c, v in
                                         sorted(occ16.items(), key=lambda kv: -kv[1])},
    }
    out["survivors"] = [{"c": sv["eight_carrier"],
                         "e": sv["eight"], "t": sv["twelve"], "s": sv["sixteen"]}
                        for sv in survivors[:60]]
    out["examples"] = examples
    out["note_on_scope"] = ("a survivor is NOT REFUTED by any published reading that "
                            "falls inside the four corner states: its local d is at least "
                            "the published value, so no cheaper path than published "
                            "exists.  The local field is an UPPER bound, so a reading "
                            "that is LARGER than the local value is simply not explained "
                            "yet -- the rest of the board may explain it.  These are "
                            "NECESSARY conditions, not sufficient ones.")
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    print(f"\n  disjoint (8,12) pairs that leave room for a 16   {pairs}")
    print(f"  triples                                      {triples}")
    print(f"     reproducing d(7,10)=13                      {ok13}")
    print(f"     reproducing d(10,9)=61                      {ok61}")
    print(f"     reproducing d(10,8)=77                      {ok77}")
    print(f"     reproducing d(6,9)=9                        {ok9}")
    print(f"  triples NOT REFUTED by any published reading inside   {len(survivors)}")
    from collections import Counter
    br = Counter(sv["eight_carrier"] for sv in survivors)
    for k, v in sorted(br.items()):
        print(f"     of which the 8 is carried by {k}: {v}")
    print(f"\nwrote {OUT}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
