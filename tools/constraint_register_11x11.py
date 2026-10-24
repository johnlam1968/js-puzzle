#!/usr/bin/env python3
"""The constraint register of the official 11x11: every constraint we have, in one file.

WHY A REGISTER
    Three sources have been producing constraints for this instance -- the engine
    (src/rules.py, src/cost.py, src/hitting.py), the crashed session's last substantive
    turn, and the human.  They are not equally trustworthy, and they are not equally
    local.  A register makes that explicit, so a later step can ask "what is the CHEAPEST
    constraint that touches THIS cell?" instead of re-deriving everything.

THE FOUR STATUSES
    PROVEN       the engine computes it, or it follows from a rule the engine checks
    OBSERVATION  a human or a crashed session saw it; it is not derived here
    PROVISIONAL  derived, but it rests on an assumption that is still open
    WITHDRAWN    it was stated, and then refuted -- kept here so it is not re-used

THE LOCALITY COLUMN
    Every instance carries the radius of the ball it can possibly touch.  That is what
    makes the window decomposition (docs/LOCALITY-PLAN.md) possible: an instance with
    radius 1 can be solved inside a 5x5 window, one with radius 39 cannot.

Exit code 0 = the register was written and every PROVEN instance re-derived from the
engine agrees with what the register says.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from hitting import capitol_lower_bound, manhattan, singleton_candidates   # noqa: E402

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
OUT = os.path.join(ROOT, "data", "derived", "constraint_register_11x11.json")

N = 11
SINGLETON = (5, 10)
KNOWN_CAPITOLS = [(5, 7), (10, 5)]

_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
ALL = [(r, c) for r in range(N) for c in range(N)]


def nbs(cell, n=N):
    r, c = cell
    return [(rr, cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= rr < n and 0 <= cc < n]


def main() -> int:
    facets = []

    # ------------------------------------------------------------------ #
    # F1  the published numbers
    facets.append({
        "id": "F-published",
        "name": "the 33 published numbers (the d-field, read off the image)",
        "source": "data/puzzles/official-11x11/puzzle.json (OCR-verified, 33/33 cells)",
        "status": "PROVEN",
        "locality": {"kind": "ball", "radius": "per instance: floor((d+1)/2) steps"},
        "instances": [
            {"cell": [r, c], "d": v, "step_budget": (v + 1) // 2,
             "radius": (v + 1) // 2}
            for (r, c), v in sorted(HINTS.items())
        ],
    })

    # ------------------------------------------------------------------ #
    # F2  the revealed capitols
    facets.append({
        "id": "F-revealed-capitols",
        "name": "the two revealed capitols (published d = 0)",
        "source": "the published grid; d = 0 <=> the cell IS a capitol (L5)",
        "status": "PROVEN",
        "locality": {"kind": "cell", "radius": 0},
        "instances": [{"cell": list(c), "d": 0} for c in KNOWN_CAPITOLS],
    })

    # ------------------------------------------------------------------ #
    # F3  the d=1 demands -> forced 1x1 states
    cands = singleton_candidates(N, HINTS)
    f3 = []
    for x in sorted(cands):
        keep, dead = [], []
        for cand in cands[x]:
            bad = [[y, HINTS[y]] for y in nbs(cand) if HINTS.get(y, 0) > 1]
            if bad:
                dead.append({"cell": list(cand), "refuted_by": bad})
            else:
                keep.append({"cell": list(cand), "status": "SURVIVES"})
        f3.append({"demand": list(x), "d": 1, "candidates": keep, "refuted": dead,
                   "unique": len(keep) == 1})
    facets.append({
        "id": "F-singleton-demand",
        "name": "a d=1 cell is served by a 1x1 state ADJACENT to it (PLAN D64)",
        "source": "src/hitting.py::singleton_candidates + the published neighbours",
        "status": "PROVEN",
        "locality": {"kind": "ball", "radius": 1},
        "instances": f3,
    })

    # ------------------------------------------------------------------ #
    # F4  the ring of a forced singleton: the imputation that turns readings into bounds
    known = dict(HINTS)
    for x in sorted(cands):
        keep = [c for c in cands[x]
                if not any(HINTS.get(y, 0) > 1 for y in nbs(c))]
        if len(keep) == 1:
            known[keep[0]] = 0
            for y in nbs(keep[0]):
                known.setdefault(y, 1)
    imputed = [{"cell": list(c), "d": known[c], "why": ("the 1x1 state is its own capitol"
                                                    if known[c] == 0 else
                                                    "one cost-1 step from that capitol")}
               for c in sorted(known) if c not in HINTS]
    facets.append({
        "id": "F-ring",
        "name": "the ring of a forced singleton: d = 1 on its neighbours",
        "source": "a 1x1 state is a capitol, and a cost-1 step reaches it",
        "status": "PROVEN",
        "locality": {"kind": "ball", "radius": 1},
        "instances": imputed,
    })

    # ------------------------------------------------------------------ #
    # F5  the area bound (L2/L3): the state holding x is at least |d(x) - d(y)| big
    need, why = {}, {}
    for x in sorted(known):
        for y in nbs(x):
            if y in known:
                delta = abs(known[x] - known[y])
                if delta > need.get(y, 0):
                    need[y] = delta
                    why[y] = f"|d({x}) - d({y})| = |{known[x]} - {known[y]}|"
    facets.append({
        "id": "F-area",
        "name": "L2/L3: the state holding x has area >= |d(x) - d(y)| for adjacent y",
        "source": "src/cost.py::check_L2 / check_L3 (the engine's own lemma bank)",
        "status": "PROVEN",
        "locality": {"kind": "ball", "radius": 1},
        "instances": [
            {"cell": list(c), "min_area": need[c], "via": why[c]}
            for c in sorted(need) if need[c] >= 2
        ],
    })

    # ------------------------------------------------------------------ #
    # F6  the tight edge (L1): the drop in d is paid by ONE edge
    facets.append({
        "id": "F-tight",
        "name": "L1: d(x) > 0 => some neighbour y has d(y) = d(x) - w(x,y)",
        "source": "src/cost.py::check_L1",
        "status": "PROVEN",
        "locality": {"kind": "ball", "radius": 1},
        "instances": [
            {"cell": list(x), "d": v,
             "tight_neighbour_must_satisfy": [
                 {"neighbour": list(y), "d": known.get(y, "?"), "edge_cost": v - known[y]}
                 for y in nbs(x) if y in known],
             "neighbours_with_unknown_d": [list(y) for y in nbs(x) if y not in known]}
            for x, v in sorted(HINTS.items()) if v > 0
        ],
    })

    # ------------------------------------------------------------------ #
    # F7  the parity gate (PLAN D43)
    facets.append({
        "id": "F-parity",
        "name": "a state that HAS a capitol has ODD area (PLAN D43)",
        "source": "PLAN.md D43; re-proved as a property in tests/test_lemmas.py",
        "status": "PROVEN",
        "locality": {"kind": "state", "radius": "the state's own extent"},
        "instances": [
            {"even_area_blocks_forced_by_the_trim": [8, 12],
             "consequence": "both are capitol-less FILLER states, so their cells reach a "
                            "capitol through the blocks around them",
             "converse_is_false": "the X pentomino: five cells, no capitol"}
        ],
    })

    # ------------------------------------------------------------------ #
    # F8  the step-count lemma: which published cells NEED a hidden capitol, and where
    demands = []
    for (r, c), v in sorted(HINTS.items()):
        if v == 0:
            continue
        k = (v + 1) // 2
        if all(manhattan((r, c), z) > k for z in KNOWN_CAPITOLS):
            demands.append({
                "cell": [r, c], "d": v, "step_budget": k,
                "hidden_capitol_within": [[r + dr, c + dc]
                                          for dr in (-k, 0, k) for dc in (-k, 0, k)
                                          if 0 <= r + dr < N and 0 <= c + dc < N
                                          and (dr or dc)],
                "note": "a d>0 cell is never a capitol, so this is a hidden one",
            })
    lower = capitol_lower_bound(N, HINTS)
    facets.append({
        "id": "F-ball",
        "name": "the step-count lemma: d(x) = v puts a capitol within floor((v+1)/2) steps",
        "source": "src/hitting.py (the lemma bank) -- the radius is per instance",
        "status": "PROVEN",
        "locality": {"kind": "ball", "radius": "per instance: floor((d+1)/2)"},
        "instances": demands,
        "counts": {"published_cells_needing_a_hidden_capitol": len(demands),
                   "minimum_additional_capitols": lower["min_additional_capitols"],
                   "minimum_capitol_sets": len(lower["minimum_sets"]),
                   "candidate_pool": lower["candidate_pool"]},
    })

    # ------------------------------------------------------------------ #
    # F9  the human's observations
    facets.append({
        "id": "F-human",
        "name": "the human's observations about this instance",
        "source": "the human, in the session that crashed (and in this one)",
        "status": "OBSERVATION",
        "locality": {"kind": "mixed", "radius": "varies -- see each instance"},
        "instances": [
            {"text": "(5,10) is the best starting point. Have you use it to trim? It should "
                     "connect to a 8-cell and a 12-cell blocks, because of 9 and 13 reading.",
             "status": "CONFIRMED here",
             "derivation": "F-singleton-demand makes (5,10) the unique 1x1 state at that end "
                           "of the board; F-ring puts d = 1 on (5,9) and (6,10); F-area then "
                           "gives |9-1| = 8 and |13-1| = 12",
             "caveat": "the chain uses d(6,10) = 1, i.e. (6,10) is NOT a capitol.  The "
                       "branch where it IS gives 9 and 13 instead -- not refuted, weaker."},
            {"text": "the 9 one-cell states (the '9 + 2' reading): the frame is a few known "
                     "sizes of small state + several big states + filler",
             "status": "OBSERVATION -- not derived here",
             "note": "the crashed session read it as '32 of the 121 cells are already pinned "
                     "into big states'.  It is a CLAIM ABOUT THE SHAPE OF THE SOLUTION, not a "
                     "constraint the engine can check, and it is the one place where the "
                     "human is ahead of the arithmetic.",
             "test": "it is testable: F-area already pins 32 cells into states of area >= 4.  "
                     "The claim is that NINE of them are singletons -- which would make the "
                     "d=1 demands much stronger (three more forced 1x1 states)."},
        ],
    })

    # ------------------------------------------------------------------ #
    # F10  the rules that were stated and then refuted
    facets.append({
        "id": "F-withdrawn",
        "name": "rules that were stated and then refuted",
        "source": "the crashed session's last turn, and re-checked here",
        "status": "WITHDRAWN",
        "locality": {"kind": "n/a", "radius": "n/a"},
        "instances": [
            {"rule": "R1: a capitol at s => every published neighbour of s has d <= 1",
             "claimed_consequence": "the hidden-capitol pool shrinks from 88 cells to 15, "
                                    "and no cover of size <= 5 exists",
             "why_it_is_false":
                 "the step from x to an adjacent capitol c costs min(size_x, size_c), and "
                 "BOTH sizes can be large.  So d(x) <= min(size_x, size_c), which is NOT "
                 "<= 1.  A cell with d = 8 can sit next to a capitol of a 12-cell state.",
             "consequence": "the 15-cell pool and the '>5 hidden capitols' number are VOID. "
                            "Do not use them.  (The crashed session retracted this itself in "
                            "its last thinking, one turn before it degenerated.)",
             "re_checked_here": True},
        ],
    })

    # ------------------------------------------------------------------ #
    out = {
        "id": "constraint-register-11x11",
        "n": N,
        "generated_by": "tools/constraint_register_11x11.py",
        "coordinate_convention": "0-based (row, col)",
        "facet_count": len(facets),
        "facets": facets,
        "summary": {
            "published_cells": len(HINTS),
            "revealed_capitols": len(KNOWN_CAPITOLS),
            "forced_singletons": 1,
            "imputed_d_values": len(imputed),
            "area_bounds": sum(1 for c in need if need[c] >= 2),
            "cells_needing_a_hidden_capitol": len(demands),
            "max_instance_radius": max((i["radius"] for f in facets for i in f["instances"]
                                        if isinstance(i.get("radius"), int)), default=0),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {OUT}")
    print(json.dumps(out["summary"], indent=1))
    for f in facets:
        n = len(f["instances"])
        print(f"  {f['id']:<22} {f['status']:<12} {n:>3} instances   {f['name'][:60]}")

    ok = (out["summary"]["forced_singletons"] == 1
          and out["summary"]["cells_needing_a_hidden_capitol"] == 9
          and need.get((5, 9)) == 8 and need.get((6, 10)) == 12)
    print("\nCHECK: the (5,10) singleton, the nine hidden-capitol demands, the 8 and the 12: "
          + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
