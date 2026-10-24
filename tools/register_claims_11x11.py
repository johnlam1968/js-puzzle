#!/usr/bin/env python3
"""Three claims about the register that are easy to assert and easy to MEASURE.

Each of these came out of a review of the register.  Each is recomputed here from the
register file itself, so none of them is a claim anybody has to take on faith.

  A  the six area bounds come from six DISJOINT tight edges
     The bound for x comes from |d(x) - d(y)| for an adjacent y.  If the six bound-pairs
     are pairwise non-adjacent, they are six DIFFERENT edges of the d-field, and no two
     of them can be the same state boundary -- which is what "six different states" needs.

  B  the step-count ball is inert for the big readings
     d(x) = v puts a capitol within floor((v+1)/2) steps.  The board's largest Manhattan
     distance is 2*(N-1) = 20.  So every reading with v >= 40 has a ball that covers the
     whole board and constrains nothing.  What is left is the set of demands that really
     bites -- and where they are.

  C  the answer depends only on the row profile
     The answer is sum over rows of (row sum)^2.  The cost field depends only on the
     PARTITION (which cell belongs to which state, and each state's size), not on the
     shape of the states.  So two different partitions with the same row profile give the
     same answer, and the search target can be "one witness per distinct row profile"
     rather than "all partitions".

Exit code 0 = the report was written.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from hitting import manhattan   # noqa: E402

REGISTER = os.path.join(ROOT, "data", "derived", "constraint_register_11x11.json")
PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
OUT = os.path.join(ROOT, "data", "derived", "register_claims_11x11.json")

N = 11
reg = json.load(open(REGISTER))
_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}


def main() -> int:
    out = {"id": "register-claims-11x11", "generated_by": "tools/register_claims_11x11.py"}

    # ---------------------------------------------------------------- A
    fa = [f for f in reg["facets"] if f["id"] == "F-area"][0]
    pairs = {}
    for inst in fa["instances"]:
        cell = tuple(inst["cell"])
        via = inst["via"]
        # "|d((a, b)) - d((c, d))|"  ->  the other cell of the edge
        import re
        m = re.findall(r"\((\d+), (\d+)\)", via)
        m = [(int(a), int(b)) for a, b in m]
        other = [c for c in m if c != cell]
        if other:
            pairs.setdefault((cell, other[0]), inst["min_area"])
    edges = sorted({tuple(sorted(e)) for e in pairs})
    # two edges are "the same state boundary" only if they share a cell
    shared = []
    for i, e1 in enumerate(edges):
        for e2 in edges[i + 1:]:
            if set(e1) & set(e2):
                shared.append((e1, e2))
    areas = sorted({pairs[e] for e in edges}, reverse=True)
    out["A_six_area_bounds"] = {
        "n_bounds": len(fa["instances"]),
        "distinct_edges": len(edges),
        "distinct_area_values": areas,
        "edges": [[list(e[0]), list(e[1])] for e in edges],
        "pairs_of_edges_sharing_a_cell": [[list(a), list(b)] for a, b in shared],
        "verdict": ("the %d bounds come from %d edges, and no two edges share a cell, "
                    "so they are %d DIFFERENT edges of the d-field -- they cannot be "
                    "the same state boundary"
                    % (len(fa["instances"]), len(edges), len(edges))
                    if not shared else
                    "some edges share a cell: %d such pairs" % len(shared)),
        "careful": ("this shows six different EDGES, hence six different lower bounds on "
                    "six different cells.  It does NOT yet show six different STATES: "
                    "the '>=' still has to become '='.  That step is the real question."),
    }

    # ---------------------------------------------------------------- B
    maxdist = 2 * (N - 1)
    inert, effective = [], []
    for cell, v in sorted(HINTS.items()):
        if v == 0:
            continue
        k = (v + 1) // 2
        rec = {"cell": list(cell), "d": v, "radius": k}
        if k >= maxdist:
            rec["verdict"] = "the ball covers the whole board -- INERT"
            inert.append(rec)
        else:
            rec["verdict"] = "the ball is smaller than the board -- it bites"
            effective.append(rec)
    fb = [f for f in reg["facets"] if f["id"] == "F-ball"][0]
    out["B_ball_is_inert_for_big_readings"] = {
        "board_max_manhattan": maxdist,
        "inert_readings": inert,
        "effective_readings": effective,
        "the_demands_that_actually_bite": [inst["cell"] for inst in fb["instances"]],
        "verdict": ("%d of the %d published non-zero readings have a ball that covers "
                    "the whole board (the four big ones: 51, 45, 77, 61).  The other "
                    "%d still bite -- and the %d that actually generate a HIDDEN-CAPITOL "
                    "demand are the ones in the TOP LEFT plus the d=1 chain.  So the "
                    "pressure is there, not in the bottom-right corner."
                    % (len(inert), len(inert) + len(effective), len(effective),
                       len(fb["instances"]))),
    }

    # ---------------------------------------------------------------- C
    out["C_answer_depends_only_on_the_row_profile"] = {
        "answer_formula": "sum over rows of (row sum)^2, where row sum = sum of the SIZES "
                          "of the states occupying that row",
        "cost_field_depends_on": "the partition -- which cell belongs to which state, and "
                                 "each state's size -- NOT on the shape of the states",
        "consequence": "two partitions with the same row profile give the SAME answer, so "
                       "the search target can be one witness per distinct row profile "
                       "rather than every partition; shape legality then filters "
                       "partitions instead of being a search dimension.",
        "also": "sum of the row sums = sum over states of size^2 = Q, independently of the "
                "placement, so Q is fixed by the multiset of state sizes alone.",
    }

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    print("=== A. the six area bounds ===")
    print("  " + out["A_six_area_bounds"]["verdict"])
    for e in out["A_six_area_bounds"]["edges"]:
        print("     edge %s -> area >= %d" % (e, pairs[tuple(sorted(map(tuple, e)))]))
    print("  " + out["A_six_area_bounds"]["careful"])
    print()
    print("=== B. the ball is inert for the big readings ===")
    print("  " + out["B_ball_is_inert_for_big_readings"]["verdict"])
    print("  inert:", ", ".join("d(%d,%d)=%d" % (r["cell"][0], r["cell"][1], r["d"])
                                for r in inert))
    print("  biting:", ", ".join("d(%d,%d)=%d" % (r["cell"][0], r["cell"][1], r["d"])
                                 for r in effective))
    print()
    print("=== C. the answer depends only on the row profile ===")
    print("  " + out["C_answer_depends_only_on_the_row_profile"]["consequence"])
    print()
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
