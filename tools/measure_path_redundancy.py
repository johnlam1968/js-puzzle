#!/usr/bin/env python3
"""How many times does the growth reach the same shape by different routes?

The solver grows a state by adding one symmetry orbit at a time.  If the orbits that
end up in the state can be added in several orders, the same shape is reached by several
paths, and all of that duplicated work has to be paid for.  The "middle-state dedupe"
was a patch for that symptom: it noticed the duplicate AFTER arriving, so the repeated
path work had already happened.

The Redelmeier rule (exclude every smaller candidate once a larger one has been taken)
attacks the cause: with it, every shape is reached by exactly ONE path.

This tool measures both, for a given board size, over every (anchor, symmetry) pair:

    redundancy = (number of growth paths) / (number of distinct shapes reached)

A redundancy of 1.0 means every shape is reached exactly once.

Exit code 0 = the measurement ran.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, FrozenSet, List, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from grow import orbits_of, symmetry_choices          # noqa: E402

Cell = Tuple[int, int]
State = FrozenSet[Cell]


def grow_counts(n: int, anchor: Cell, sym, canonical: bool) -> Tuple[int, int]:
    """(growth paths, distinct shapes) for one (anchor, symmetry)."""
    orb = orbits_of(sym, n)
    board = {(r, c) for r in range(n) for c in range(n)}

    def canon_key(cells: FrozenSet[Cell]) -> int:
        return min(abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]) for c in cells)

    paths = 0
    shapes: Set[State] = set()

    def rec(cur: FrozenSet[Cell], rem: Set[Cell], forbidden: Set[Cell]):
        nonlocal paths
        paths += 1
        shapes.add(cur)
        frontier = set()
        for (r, c) in cur:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (r + dr, c + dc)
                if nb in board and nb not in cur:
                    frontier.add(nb)
        cands = []
        seen_orbit = set()
        for x in frontier:
            o = orb.get(x)
            if o is None or not o <= rem or o & cur:
                continue
            if forbidden & o:
                continue
            if canonical and o in seen_orbit:
                continue
            seen_orbit.add(o)
            cands.append(o)
        if canonical:
            cands.sort(key=canon_key)
        for i, o in enumerate(cands):
            child_forbidden = set(forbidden)
            if canonical:
                for o2 in cands[:i]:
                    child_forbidden |= o2
            rec(cur | o, rem - o, child_forbidden)

    start = frozenset(orb[anchor])
    if not start <= board:
        return 0, 0
    rec(start, board - start, set())
    return paths, len(shapes)


def main() -> int:
    sizes = [int(x) for x in sys.argv[1:]] or [4, 5]
    print("=== growth path redundancy (paths / distinct shapes) ===")
    print("    (one anchor per corner, over every symmetry of that size)")
    for n in sizes:
        syms = symmetry_choices(n)
        anchors = [(0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)]
        for canonical in (False, True):
            total_paths = 0
            total_shapes = 0
            for anchor in anchors:
                for sym in syms:
                    p, s = grow_counts(n, anchor, sym, canonical)
                    total_paths += p
                    total_shapes += s
            ratio = total_paths / total_shapes if total_shapes else float("nan")
            label = "canonical (Redelmeier)" if canonical else "plain (order-agnostic)"
            print(f"  {n}x{n}  {label:26s}: {total_paths:>9,} paths / "
                  f"{total_shapes:>7,} shapes  =>  redundancy {ratio:.2f}x")
    print("\nA redundancy of 1.00x means every shape is reached by exactly one path.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
