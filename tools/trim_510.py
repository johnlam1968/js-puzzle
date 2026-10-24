#!/usr/bin/env python3
"""The (5,10) trim: enumerate the two blocks the trim forces, score them, and seed the
greedy descent with the survivors.

WHY THIS TOOL EXISTS
    docs/NEXT-APPROACHES.md 4.4g.1 left one item open: the greedy descent stalls at
    E = 480 from the all-singletons start, and the fix is a better SEED.  The `d = 1`
    demand at (4,10) forces a 1x1 state at (5,10), and the published 9 at (6,9) and 13
    at (7,10) then force an 8-cell block and a 12-cell block around it.  That is a seed
    with the AREAS in it, not just the capitol positions.

THE THREE FILTERS (all one-sided, so a survivor is necessary, never sufficient)
    F1  a cell inside a capitol-less block must be able to leave it:
          |block| * dist_to_boundary(x) + 1 <= d(x)
    F2  a path through the core is ONE path, so d(x) <= core_path(x): a core path
        CHEAPER than a published d refutes the core
    F3  the step-count lemma: the ball of radius floor((v+1)/2) around a hint must still
        contain a cell that CAN be a capitol -- not inside a filler block (a block with
        no capitol has none) and not a published d > 0 cell (such a cell is never one)

    F3 is what connects the core to the rest of the board, and it is cheap.

WHAT IT WRITES
    data/derived/trim_510.json   the surviving pairs, with the shape lists and the scores

Exit code 0 = the tool ran and the derived file was written.
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import INF, Puzzle                     # noqa: E402
from descent import pure_energy                  # noqa: E402
from grow import close_state, grow_states, symmetry_choices   # noqa: E402
from moves import legal_neighbours               # noqa: E402

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
OUT = os.path.join(ROOT, "data", "derived", "trim_510.json")

N = 11
SINGLETON = (5, 10)
KNOWN_CAPITOLS = {(5, 7), (10, 5), SINGLETON}

_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
ALL = [(r, c) for r in range(N) for c in range(N)]


def neighbours(cell, n=N):
    r, c = cell
    return [(rr, cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= rr < n and 0 <= cc < n]


manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


# --------------------------------------------------------------------------- #
def enumerate_states(anchor, size, blocked=(SINGLETON,), budget=60_000):
    """Every legal state of exactly `size` cells that contains `anchor`.

    AODFS orbit growth, straight from src/grow.py -- the same growth the solver uses.
    """
    found = {}
    for sym in symmetry_choices(N):
        stats = {}
        for st in grow_states(anchor, sym, N, blocked=blocked, max_cells=size,
                              budget=budget, stats=stats):
            if len(st) != size:
                continue
            fs = frozenset(st)
            if fs in found:
                continue
            ok, cap, group = close_state(fs)
            if ok:
                found[fs] = {"capitol": list(cap) if cap else None,
                             "symmetries": list(group)}
    return found


def core_field(core_states):
    """(dist, owner): the cheapest path from each core cell to the (5,10) capitol."""
    owner = {}
    for i, S in enumerate(core_states):
        for c in S:
            owner[c] = i
    dist = {SINGLETON: 0}
    pq = [(0, SINGLETON)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1 << 30):
            continue
        for v in owner:
            if v == u or abs(v[0] - u[0]) + abs(v[1] - u[1]) != 1:
                continue
            ia, ib = owner[u], owner[v]
            w = len(core_states[ia]) if ia == ib else min(len(core_states[ia]),
                                                          len(core_states[ib]))
            if d + w < dist.get(v, 1 << 30):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return dist, owner


def core_path(dist, owner, core_states, x):
    """The cheapest path from x into the core and on to the (5,10) capitol.

    The entry cost is the PESSIMISTIC one (the size of the core state entered): the real
    cost is min(size of x's own state, that size), which is <= this.  So a core path
    that is CHEAPER than a published d is still a sound refutation.
    """
    if x in owner:
        return dist.get(x)
    best = None
    for y in owner:
        if y not in dist or abs(y[0] - x[0]) + abs(y[1] - x[1]) != 1:
            continue
        c = len(core_states[owner[y]]) + dist[y]
        if best is None or c < best:
            best = c
    return best


def boundary_distance(S, x):
    if any(y not in S for y in neighbours(x)):
        return 0
    seen, frontier, d = {x}, [x], 0
    while frontier:
        d += 1
        nxt = []
        for u in frontier:
            for v in neighbours(u):
                if v in S and v not in seen:
                    seen.add(v)
                    if any(y not in S for y in neighbours(v)):
                        return d
                    nxt.append(v)
        frontier = nxt
    return 99


def score_core(core_states):
    """(hard violations, soft error, detail) for a joint core."""
    hard, soft, detail = 0, 0, []
    allc, filler = set(), set()
    for S in core_states:
        allc |= S
        if len(S) % 2 == 0:                 # even area => no capitol => filler block
            filler |= S
    dist, owner = core_field(core_states)

    for x, v in HINTS.items():
        for S in core_states:
            if x in S and len(S) % 2 == 0:
                lb = len(S) * boundary_distance(S, x) + 1
                if lb > v:
                    hard += 1
                    detail.append([x, v, lb, "F1: cannot leave its block for less than d"])
    for x, v in HINTS.items():
        cc = core_path(dist, owner, core_states, x)
        if cc is None:
            continue
        if cc < v:
            hard += 1
            detail.append([x, v, cc, "F2: a core path is CHEAPER than the published d"])
        else:
            soft += abs(cc - v)
            detail.append([x, v, cc, "EXPLAINS" if cc == v else "not exact"])
    for x, v in HINTS.items():
        if v == 0:
            continue
        ball = [c for c in ALL if c != x and manh(c, x) <= (v + 1) // 2]
        if any(c in KNOWN_CAPITOLS for c in ball):
            continue
        if not any(c not in filler and HINTS.get(c, 0) <= 0 for c in ball):
            hard += 1
            detail.append([x, v, None, "F3: its ball of possible capitols is empty"])
    return hard, soft, detail


def prefilter(cands, size, must_have, must_not):
    keep = []
    for fs, meta in cands.items():
        if must_have not in fs or (must_not and must_not in fs):
            continue
        if any(v == 0 and x in fs for x, v in HINTS.items()):
            continue
        if any(x in fs and size * boundary_distance(fs, x) + 1 > v
               for x, v in HINTS.items()):
            continue
        keep.append((fs, meta))
    return keep


# --------------------------------------------------------------------------- #
def energy_bucket(states):
    """The pure energy, with the bucket queue (src/cost.py) -- 3x faster than the heap."""
    try:
        d = Puzzle([set(s) for s in states]).cost_field_bucket()
    except Exception:                                        # noqa: BLE001
        return 1e6 * (len(HINTS) + 1)
    e = 0.0
    for (r, c), v in HINTS.items():
        dv = d[r][c]
        e += 1e6 if (dv == INF or dv != dv) else abs(dv - v)
    return e


def descend(states, max_steps=200, lock=(SINGLETON,), slack=60.0):
    cur = list(states)
    cur_e = energy_bucket(cur)
    best_e, best = cur_e, list(cur)
    trace = [[cur_e, "start"]]
    stuck = None
    for _ in range(max_steps):
        cands = legal_neighbours(cur, N)
        if lock:
            keep = []
            for c in cands:
                ok = True
                for lc in lock:
                    for st in c[0]:
                        if lc in st and len(st) > 1:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    keep.append(c)
            cands = keep
        if not cands:
            stuck = "no legal neighbour"
            break
        scored = sorted(((energy_bucket(c[0]), c[0], c[1]) for c in cands), key=lambda t: t[0])
        e_new, c_new, kind = scored[0]
        if e_new > best_e + slack:
            stuck = f"the cheapest neighbour ({e_new:g}) is {e_new - best_e:g} above the best"
            break
        cur, cur_e = c_new, e_new
        if cur_e < best_e:
            best_e, best = cur_e, list(cur)
        trace.append([cur_e, kind])
        if cur_e == 0.0:
            break
    return {"energy": best_e, "final": cur_e, "steps": len(trace) - 1,
            "trace": trace, "stuck": stuck, "solved": best_e == 0.0,
            "states": [sorted(s) for s in best]}


def seed_from(fs8, fs12):
    used = set(fs8) | set(fs12) | {SINGLETON}
    core = [frozenset(fs8), frozenset(fs12), frozenset({SINGLETON})]
    core += [frozenset({(r, c)}) for r in range(N) for c in range(N) if (r, c) not in used]
    return core


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "candidates", "descent"])
    ap.add_argument("--top", type=int, default=5, help="how many pairs to descend with")
    ap.add_argument("--steps", type=int, default=200)
    args = ap.parse_args()

    t0 = time.time()
    s8 = enumerate_states((5, 9), 8)
    s12 = enumerate_states((6, 10), 12)
    p8 = prefilter(s8, 8, (5, 9), (6, 10))
    p12 = prefilter(s12, 12, (6, 10), (5, 9))
    print(f"candidates: {len(s8)} eight-cell, {len(s12)} twelve-cell")
    print(f"after the per-block filter: {len(p8)} eight-cell, {len(p12)} twelve-cell",
          flush=True)

    scored = []
    for fs8, m8 in p8:
        for fs12, m12 in p12:
            if fs8 & fs12:
                continue
            hard, soft, det = score_core([fs8, fs12, frozenset({SINGLETON})])
            if hard == 0:
                scored.append((soft, fs8, fs12, m8, m12, det))
    scored.sort(key=lambda t: t[0])
    print(f"{len(scored)} pairs survive F1+F2+F3  ({time.time()-t0:.0f}s)\n")

    out = {
        "id": "trim-510",
        "generated_by": "tools/trim_510.py",
        "n": N,
        "singleton": list(SINGLETON),
        "forced": {
            "singleton_at": [5, 10],
            "state((5,9))_min": 8,
            "state((6,10))_min": 12,
            "why": "the d=1 demand at (4,10) forces the 1x1 state at (5,10); its ring has "
                   "d = 1; L2/L3 then give |9-1| = 8 and |13-1| = 12",
            "branch": "if (6,10) were itself a capitol (d = 0) the bounds would be 9 and 13",
        },
        "counts": {"eight_cell_candidates": len(s8), "twelve_cell_candidates": len(s12),
                   "eight_cell_after_prefilter": len(p8),
                   "twelve_cell_after_prefilter": len(p12),
                   "pairs_surviving": len(scored)},
        "pairs": [],
    }
    for soft, fs8, fs12, m8, m12, det in scored[:40]:
        out["pairs"].append({
            "soft_error": soft,
            "eight_cell": sorted(list(c) for c in fs8),
            "twelve_cell": sorted(list(c) for c in fs12),
            "eight_cell_symmetries": m8["symmetries"],
            "twelve_cell_symmetries": m12["symmetries"],
            "explains": [[x[0], x[1], x[2]] for x in det if x[3] == "EXPLAINS"],
        })

    if args.stage in ("all", "descent"):
        print("=" * 78)
        print("the seeded descent")
        print("=" * 78)
        runs = []
        for i, (soft, fs8, fs12, *_rest) in enumerate(scored[:args.top]):
            seed = seed_from(fs8, fs12)
            e0 = energy_bucket(seed)
            t1 = time.time()
            r = descend(seed, max_steps=args.steps)
            print(f"[{i+1}] soft={soft}  start E = {e0:.0f}  ->  best E = {r['energy']:.0f} "
                  f"after {r['steps']} steps  ({time.time()-t1:.0f}s)  stuck: {r['stuck']}")
            print(f"     E: " + " -> ".join(f"{e:.0f}" for e, _ in r["trace"][:16]) + " ...")
            runs.append({"soft_error": soft, "start_energy": e0, "best_energy": r["energy"],
                         "steps": r["steps"], "stuck": r["stuck"], "solved": r["solved"],
                         "trace": r["trace"]})
            if r["solved"]:
                print("     *** SOLVED ***")
                break
        out["descent_runs"] = runs
        out["descent_baseline_all_singletons"] = {
            "best_energy": 480, "steps": 40,
            "source": "docs/NEXT-APPROACHES.md 4.4g.1 (the all-singletons start stalls)",
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, sort_keys=False)
    print(f"\nwrote {OUT}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
