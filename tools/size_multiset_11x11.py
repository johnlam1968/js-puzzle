#!/usr/bin/env python3
"""The conservation law as a join constraint: what the readings say about the SIZE MULTISET.

THE OBSERVATION
    "we can observe all the cues (readings) from the official 11x11 panel, and identify
     all possible (and some deterministic) hints, then we know the rough number of shapes
     and their constituent cell numbers.  After all, total cells always must equal 121."

TWO CONSERVATION LAWS, AND THEY ARE DIFFERENT OBJECTS
    (1)  sum over states of |S|    =  121            (the cell count -- the user's law)
    (2)  sum over states of |S|^2  =  sum over rows of row_sum(row)   =  Q

    (2) is the one that touches the ANSWER: a state of size m contributes m to each of
    the m rows it crosses, so it contributes m^2 to the sum of the row sums.  Hence

        answer = sum over rows of row_sum(row)^2  >=  Q^2 / 11     (Cauchy-Schwarz)

    So the size multiset fixes the SUM of the row sums, and with it a floor for the
    answer.  The multiset is what the readings constrain; the PLACEMENT is what the
    answer still needs -- and the placement is what the window decomposition has to
    supply.

THE CONSTRAINTS ON THE MULTISET
    * it sums to 121;
    * exactly s parts of size 1 (s = 2 is forced, 9 is the human's claim);
    * at least 6 odd parts (a state with a capitol has ODD area -- PLAN D43 -- and the
      hitting set puts the capitol count at >= 6);
    * the area bounds the ground map found, as constraints on the SIX LARGEST parts:
      p1 >= 16, p2 >= 12, p3 >= 8, p4 >= 6, p5 >= 4, p6 >= 2  (TIGHT -- the human's
      picture, in which the 8-block and the 12-block are different blocks).
      LOOSE is the variant in which one big state may serve several of those bounds.

THE ENUMERATION
    The six largest parts are enumerated directly (a non-increasing tuple with those
    minimums); the rest is a partition of the remaining total into parts in [2, p6],
    counted by a dynamic program that also tracks the number of odd parts, the number of
    parts, and the sum of the squares.

Exit code 0 = the table was written.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from hitting import capitol_lower_bound                  # noqa: E402

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
OUT = os.path.join(ROOT, "data", "derived", "size_multiset_11x11.json")

N = 11
TOTAL = N * N
MIN_CAPITOLS = 6
BOUNDS = [16, 12, 8, 6, 4, 2]      # on the six largest parts (TIGHT)

_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
MAX_ODD = 24


def rest_dp(limit, max_part):
    """cnt[mx][R][k], sq[mx][R][k], n[mx][R][k] for partitions of R into parts in [2, mx]
    with exactly k odd parts: the count, the sum of the squares, and the number of parts.
    """
    cnt = [[[0] * (MAX_ODD + 1) for _ in range(limit + 1)] for _ in range(max_part + 1)]
    sq = [[[0] * (MAX_ODD + 1) for _ in range(limit + 1)] for _ in range(max_part + 1)]
    n = [[[0] * (MAX_ODD + 1) for _ in range(limit + 1)] for _ in range(max_part + 1)]
    cnt[2][0][0] = 1
    for mx in range(2, max_part + 1):
        odd = mx % 2
        for R in range(0, limit + 1):
            for k in range(MAX_ODD + 1):
                c = cnt[mx - 1][R][k]
                if not c:
                    continue
                cnt[mx][R][k] += c
                sq[mx][R][k] += sq[mx - 1][R][k]
                n[mx][R][k] += n[mx - 1][R][k]
                if R + mx <= limit and k + odd <= MAX_ODD:
                    cnt[mx][R + mx][k + odd] += c
                    sq[mx][R + mx][k + odd] += sq[mx - 1][R][k] + c * mx * mx
                    n[mx][R + mx][k + odd] += n[mx - 1][R][k] + c
    return cnt, sq, n


def top_tuples(mins, budget):
    """All non-increasing tuples (p1..pk) with p_i >= mins[i] and the sum <= budget."""
    k = len(mins)

    def rec(i, last, chosen, used):
        if i == k:
            yield tuple(chosen)
            return
        lo = max(mins[i], chosen[0] if chosen else 0)
        hi = min(last, budget - used)
        for v in range(lo, hi + 1):
            yield from rec(i + 1, v, chosen + [v], used + v)

    return rec(0, budget, [], 0)


def variant(singletons, tight, cnt, sq, n):
    mins = BOUNDS if tight else [BOUNDS[0]]
    budget = TOTAL - singletons
    total_multisets = 0
    q_min, q_max = None, None
    st_min, st_max = None, None
    for top in top_tuples(mins, budget):
        used = sum(top)
        R = budget - used
        mx = top[-1]
        if R == 0:
            ks = [0]
        else:
            ks = range(0, MAX_ODD + 1)
        odd_top = sum(1 for p in top if p % 2)
        for k in ks:
            c = cnt[mx][R][k]
            if not c:
                continue
            if odd_top + singletons + k < MIN_CAPITOLS:
                continue
            total_multisets += c
            q = sum(p * p for p in top) + singletons + sq[mx][R][k]
            nstates = len(top) + singletons + n[mx][R][k]
            q_min = q if q_min is None else min(q_min, q)
            q_max = q if q_max is None else max(q_max, q)
            st_min = nstates if st_min is None else min(st_min, nstates)
            st_max = nstates if st_max is None else max(st_max, nstates)
    return {
        "singletons": singletons,
        "multisets": total_multisets,
        "Q_min": q_min, "Q_max": q_max,
        "states_min": st_min, "states_max": st_max,
        "answer_floor_min": (q_min * q_min // N) if q_min else None,
        "answer_floor_max": (q_max * q_max // N) if q_max else None,
    }


def main() -> int:
    lower = capitol_lower_bound(N, HINTS)
    print(f"hitting set: >= {lower['min_additional_capitols']} hidden capitols, "
          f"{len(lower['minimum_sets'])} minimum sets, pool {lower['candidate_pool']}")
    print(f"total cells: {TOTAL}   capitol lower bound: {MIN_CAPITOLS}\n")

    cnt, sq, n = rest_dp(TOTAL - 2, TOTAL - 2)
    report = {}
    for tight in (True, False):
        for s in (2, 3, 9):
            v = variant(s, tight, cnt, sq, n)
            label = ("TIGHT: the six area bounds are six DIFFERENT big states"
                     if tight else
                     "LOOSE: one big state may serve several of the bounds")
            v["variant"] = label
            report[f"{'tight' if tight else 'loose'}-singletons{s}"] = v
            print(f"  {label}")
            print(f"      singletons = {s}")
            print(f"      feasible size multisets : {v['multisets']:>14,}")
            if v["Q_min"] is not None:
                print(f"      Q = sum |S|^2            : {v['Q_min']:>14,} .. {v['Q_max']:,}")
                print(f"      number of states        : {v['states_min']:>14,} .. "
                      f"{v['states_max']:,}")
                print(f"      answer floor Q^2/11      : {v['answer_floor_min']:>14,} .. "
                      f"{v['answer_floor_max']:,}")
            print()

    out = {
        "id": "size-multiset-11x11",
        "generated_by": "tools/size_multiset_11x11.py",
        "total_cells": TOTAL,
        "capitol_lower_bound": MIN_CAPITOLS,
        "hitting_set": {"min_additional": lower["min_additional_capitols"],
                        "minimum_sets": len(lower["minimum_sets"]),
                        "candidate_pool": lower["candidate_pool"]},
        "bounds_used": BOUNDS,
        "variants": report,
        "laws": {
            "cells": "sum over states of |S| = 121",
            "row_sums": "sum over rows of row_sum(row) = sum over states of |S|^2 = Q",
            "answer": "answer = sum over rows of row_sum(row)^2 >= Q^2 / 11",
        },
        "open": [
            "how many singletons are there really?  2 is forced, 9 is the human's claim",
            "are the six area bounds met by six different states?  (TIGHT vs LOOSE)",
            "the placement: the multiset fixes Q, but the answer needs the row sums",
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
