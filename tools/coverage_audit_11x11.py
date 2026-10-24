#!/usr/bin/env python3
"""Which of the 33 published numbers are actually EXERCISED by the current searches?

THE QUESTION
    "Has the constraint registry taken all official revealed numbers into consideration?"

THE HONEST ANSWER, SPLIT IN TWO
    * the REGISTER records all 33 (F-published has 33 instances) -- yes.
    * the SEARCHES use only the ones that are geometrically near the blocks they are
      working on.  The rest are DORMANT: recorded, and waiting for a core that reaches
      them.

    This tool measures the split, per core, so the gap is a number instead of a worry.

HOW A NUMBER IS EXERCISED
    F1  it sits INSIDE a candidate block (then "it must be able to leave the block" bites)
    F2  it is ADJACENT to the core (then a path through the core is a real path, and a
        cheap one would contradict the published value)
    F3  its step-count ball INTERSECTS the core (then "the ball must still contain a
        possible capitol" bites, because a filler block has no capitol)

    A number that is none of these is exercised by NOTHING in that search.

Exit code 0 = the audit was written.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from hitting import singleton_candidates          # noqa: E402

REGISTER = os.path.join(ROOT, "data", "derived", "constraint_register_11x11.json")
OUT = os.path.join(ROOT, "data", "derived", "coverage_audit_11x11.json")

N = 11
_p = json.load(open(os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def exercised(core_cells, label, extra_note=""):
    """Which published numbers does a search over this core actually use?"""
    core = set(core_cells)
    active = {}
    for x, v in HINTS.items():
        why = []
        if x in core:
            why.append("F1 (inside a block)")
        if any(manh(x, y) == 1 for y in core):
            why.append("F2 (adjacent to the core)")
        radius = (v + 1) // 2
        ball = {(x[0] + dr, x[1] + dc) for dr in range(-radius, radius + 1)
                for dc in range(-radius, radius + 1)
                if (dr or dc) and 0 <= x[0] + dr < N and 0 <= x[1] + dc < N}
        if ball & core:
            why.append(f"F3 (its ball of radius {radius} hits the core)")
        if why:
            active[x] = {"d": v, "by": why}
    dormant = {x: v for x, v in HINTS.items() if x not in active}
    return {
        "core": label,
        "note": extra_note,
        "core_cells": sorted(list(c) for c in core),
        "exercised": {f"{x[0]},{x[1]}": active[x] for x in sorted(active)},
        "exercised_count": len(active),
        "dormant": {f"{x[0]},{x[1]}": v for x, v in sorted(dormant.items())},
        "dormant_count": len(dormant),
    }


def main() -> int:
    reg = json.load(open(REGISTER))
    facets = {f["id"]: f for f in reg["facets"]}

    # core 1: the (5,10) trim -- the 8-block, the 12-block and the singleton
    trim = json.load(open(os.path.join(ROOT, "data", "derived", "trim_510.json")))
    best = trim["pairs"][0]
    core510 = ([tuple(c) for c in best["eight_cell"]]
               + [tuple(c) for c in best["twelve_cell"]] + [(5, 10)])

    # core 2: the lower-right corner -- the 16-block and the singleton
    c1 = exercised(core510, "the (5,10) core: the 8-block + the 12-block + the singleton",
                   "the best-scoring pair from tools/trim_510.py")
    c2 = exercised([(10, 8), (10, 9), (5, 10)], "the lower-right corner: (10,8) + (10,9) + (5,10)",
                   "the corner the human is working by hand")
    c3 = exercised([(r, c) for r in range(N) for c in range(N)], "the whole board",
                   "the upper bound: everything is adjacent to everything")

    out = {
        "id": "coverage-audit-11x11",
        "generated_by": "tools/coverage_audit_11x11.py",
        "published_numbers": len(HINTS),
        "cores": {"the (5,10) core": c1, "the lower-right corner": c2, "the whole board": c3},
        "read": "a number that is DORMANT in every core we actually search is a number "
                "we are not using.  The dormant set of the (5,10) core is the work list "
                "for a SECOND core in the other corner.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    for name, c in out["cores"].items():
        print(f"  {name}: {c['exercised_count']}/{len(HINTS)} exercised, "
              f"{c['dormant_count']} dormant")
        if c["dormant_count"] and c["dormant_count"] < 30:
            print("      dormant: " + ", ".join(
                f"{k}={v}" for k, v in c["dormant"].items()))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
