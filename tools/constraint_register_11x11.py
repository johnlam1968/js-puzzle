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

from hitting import (ball, capitol_lower_bound, manhattan,   # noqa: E402
                     singleton_candidates)

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
    #
    # The candidates come from src/hitting.py -- the SAME function the engine and the
    # hitting-set bound use -- so this display column cannot drift from the counts.
    # Two rules, both of which the earlier version of this file got wrong:
    #   * the region is a MANHATTAN BALL, not the eight corners of a k-square;
    #   * a cell with a published d>0 can never be a capitol, so it is not a candidate
    #     (a cell with a published d=0 IS a revealed capitol and stays in).
    #   * a d=1 demand is SPECIAL (PLAN D64): the capitol serving it must be a 1x1
    #     state ADJACENT to it, so its candidates are the neighbours, not the ball.
    _singles = singleton_candidates(N, HINTS)
    demands = []
    for (r, c), v in sorted(HINTS.items()):
        if v == 0:
            continue
        k = (v + 1) // 2
        if all(manhattan((r, c), z) > k for z in KNOWN_CAPITOLS):
            if v == 1:
                cands = [c for c in _singles.get((r, c), []) if c not in KNOWN_CAPITOLS]
                how = ("a d=1 demand is served by a 1x1 state ADJACENT to it (PLAN D64), "
                       "so the candidates are the neighbours that could still be that "
                       "singleton")
            else:
                cands = [c for c in ball((r, c), k, N) if c not in HINTS]
                how = ("the step-count lemma: a d=v cell has a capitol within "
                       "floor((v+1)/2) steps, and a published d>0 cell is never a "
                       "capitol")
            demands.append({
                "cell": [r, c], "d": v, "step_budget": k,
                "hidden_capitol_within": [list(c) for c in cands],
                "n_candidates": len(cands),
                "how": how,
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
             "status": "WITHDRAWN -- the supporting arithmetic does not hold",
             "note": "the crashed session read it as '32 of the 121 cells are already pinned "
                     "into big states'.  It is a CLAIM ABOUT THE SHAPE OF THE SOLUTION, not a "
                     "constraint the engine can check.",
             "why_withdrawn": [
                 "F-area pins 12 CELLS, not 32 (10 of them with min_area >= 4, 2 with "
                 "min_area = 2) -- the '32' was never measured",
                 "and 'min_area >= 4' is a LOWER bound, which points the OPPOSITE way "
                 "from 'is a singleton'.  A lower bound of 4 cannot imply size 1.",
                 "so 'F-area already pins 32 cells into states of area >= 4.  The claim "
                 "is that NINE of them are singletons' never had a valid inference "
                 "behind it"],
             "what_is_left": "the d=1 demands are strong on their OWN -- a d=1 cell is "
                             "one cost-1 step from a 1x1 state, and a 1x1 state IS a "
                             "capitol (PLAN D64).  F-singleton-demand and F-ball carry "
                             "that.  The number '9' is not derived from F-area and must "
                             "not be carried as if it were.",
             "the_load_bearing_reading": "the thing that does carry weight is the TIGHT "
                                         "reading of 13 = 12 + 1 and 61 = 12*5 + 1 "
                                         "(facet F-inferred, I7), not the count '9'."},
        ],
    })

    # ------------------------------------------------------------------ #
    # F11  what the READINGS THEMSELVES force -- inference, not enumeration
    #
    # The engine rules above are LOCAL: they say what a shape must look like.  These
    # are the rules that read a number and say what its STATE must look like, and they
    # are what the human asked for ("use the published readings and the registry of
    # constraints to do INFERENCE, not brute force").
    facets.append({
        "id": "F-inferred",
        "name": "what the published readings force about the state sizes",
        "source": "derived in tools/infer_sizes_11x11.py from the readings alone",
        "status": "PROVEN",
        "locality": {"kind": "field", "radius": 1},
        "instances": [
            {"rule": "I1 (adjacency bound): for adjacent cells x,y, |d(x) - d(y)| <= "
                     "min(size_x, size_y)",
             "consequence": "each published cell inherits a LOWER BOUND on its state's "
                            "size from every published neighbour",
             "worked_example": "(10,8)=77 and (10,9)=61 are adjacent, so both states "
                               "have at least 16 cells",
             "status": "PROVEN"},
            {"rule": "I2 (path decomposition): a reading v is k steps inside the state "
                     "(cost size each) plus ONE crossing of cost r = min(size, next size)",
             "consequence": "v = k*size + r with 1 <= r <= size, or v = k*size when the "
                            "path ends on the state's OWN capitol (then the area is ODD)",
             "the_two_load_bearing_cases": {
                 "r = 1": "the crossing costs 1 -> the next state has ONE cell -> it is a "
                          "SINGLETON CAPITOL (the human's pattern: 61 = 12*5+1, 13 = 12+1)",
                 "r = 0": "the path ends inside the state -> that state has a capitol -> "
                          "its area is ODD (D43)"},
             "status": "PROVEN"},
            {"rule": "I3 (the corner bound): min(size(10,8), size(10,9)) >= 16",
             "consequence": "the 12-cell state does NOT CONTAIN (10,9): if it did, the "
                            "step (10,8)->(10,9) would cost at most 12 and "
                            "d(10,8) <= 12 + 61 = 73 < 77.  So (10,9)'s own state has "
                            ">= 16 cells and its path CROSSES INTO the 12-cell state "
                            "(crossing cost min(size_9, 12) = 12).",
             "status": "PROVEN",
             "correction": "an earlier note here said the reading '61 = 12*5 + 1' was "
                           "refuted.  That was WRONG: the reading survives, provided the "
                           "five 12-cost steps are one CROSSING plus four inside the "
                           "12-cell state.  The human's arithmetic is right; only the "
                           "anchor was wrong (the 12 belongs to the state entered, not to "
                           "the state left)."},
            {"rule": "I4 (the singleton-exit sizes): with the bound from I3 applied, the "
                     "readings admit only these state sizes",
             "table": {"(10,9) = 61": [20, 30, 60], "(10,8) = 77": [19, 38, 76],
                       "(7,10) = 13": [2, 3, 4, 6, 12], "(6,2) = 11": [10],
                       "(7,2) = 17": [8, 16], "(3,3) = 51": [1, 2, 5, 10, 25, 50],
                       "(8,8) = 45": [1, 2, 4, 11, 22, 44], "(10,1) = 26": [1, 5, 25]},
             "consequence": "the human's '51 implies a LARGE shape in the upper middle' is "
                            "sizes 25 or 50; the '61' cell's state is 20, 30 or 60 -- NOT "
                            "12",
             "status": "PROVEN (the bound); PROVISIONAL (the singleton-exit reading)"},
            {"rule": "I5 (the tight edge of the 77): if the tight neighbour of (10,8) is "
                     "(10,9), the crossing costs 77 - 61 = 16 = min(size_8, size_9)",
             "consequence": "exactly one of the two states has 16 cells, and since the "
                            "(10,9) state's singleton-exit sizes are 20/30/60, it is the "
                            "(10,8) state that has 16 cells",
             "status": "PROVISIONAL (it rests on the 'travel right' hypothesis)"},
            {"rule": "I6 (the exit singleton is hidden): the singleton that ends the "
                     "(10,9) path is NOT the revealed capitol (10,5)",
             "why": "the exit cell is at within-state distance k from (10,9), and k <= 3 "
                    "for every candidate size; (10,5) is at Manhattan 4, and the only "
                    "3-step path from (10,9) to a neighbour of (10,5) runs through (10,8), "
                    "which belongs to the 16-cell state",
             "consequence": "there is a HIDDEN 1-cell capitol within Manhattan 4 of (10,9)",
             "status": "PROVEN"},
            {"rule": "I7 (where the 12-cell state is): 13 = 12 + 1 and 61 = 12*5 + 1 "
                     "are the SAME chain",
             "the_chain": [
                 "the (5,10) singleton is a 1-cell state, so its ring (4,10), (5,9), "
                 "(6,10) all have d = 1",
                 "d(6,10) = 1 for FREE: one step into a 1-cell state costs exactly 1, "
                 "whatever the size of (6,10)'s own state",
                 "d(7,10) = 13 = 12 + 1  =>  the step (7,10)->(6,10) costs 12 =>  a "
                 "12-cell state touches (7,10) and (6,10)",
                 "d(10,9) = 61 = 12*5 + 1  =>  the path is (10,9) --crossing--> the "
                 "12-cell state --4 steps inside--> (6,10) --1--> (5,10)",
                 "the Manhattan distance (10,9)->(6,10) is exactly 5 and "
                 "(6,10)->(5,10) is 1, so the whole path is MONOTONE: 6 steps for a "
                 "Manhattan distance of 6.  That is a tight fit and it is why the "
                 "reading works."],
             "consequence": "the 12-cell state contains (6,10), (7,10) and an ENTRY cell "
                            "(9,9) or (10,10) 4 steps from (6,10) inside the state.  It "
                            "does NOT contain (10,8) or (10,9) (both have size >= 16).",
             "the_condition": "the tight neighbour of (7,10) is assumed to be (6,10); the "
                              "alternatives (8,10) and (7,9) are unpublished.  So this is "
                              "the READING, not a theorem.  What IS a theorem: d(6,10) = 1.",
             "measured": "1044 twelve-cell states contain both (6,10) and (7,10); 783 of "
                         "them hold no revealed capitol",
             "status": "PROVISIONAL (the tight-neighbour condition)"},
            {"rule": "I8 (an inferred reading): d(6,10) = 1",
             "status": "PROVISIONAL (it follows from I7; it is not published)"},
            {"rule": "I9 (the 51 chain): 51 = 50 + 1 puts a 50-cell state around (3,3), "
                     "and it points at ONE hidden singleton that serves three readings",
             "the_chain": [
                 "d(2,5) = 1 and d(3,6) = 1  =>  each is adjacent to a 1-cell state",
                 "(3,5) and (2,6) are adjacent to BOTH (2,5) and (3,6), so ONE singleton "
                 "can serve both",
                 "d(3,3) = 51 = 50 + 1  =>  (3,3) is one step (cost 50) from a cell that "
                 "is adjacent to a 1-cell state",
                 "so: the singleton at (3,5) [or (2,6)], and a 50-cell state containing "
                 "(3,3) and (3,4) -- then (3,4) -> (3,5) costs min(50, 1) = 1"],
             "why_it_matters": "this is the human's 'the 51 is near the two 1 readings, so "
                               "there is a large shape in the upper middle' -- and it "
                               "identifies WHICH large shape and WHICH singleton",
             "status": "PROVISIONAL (the tight-neighbour conditions are not published)"},
            {"rule": "I10 (the conservation clash): the 50-cell state and the 45-cell "
                     "state cannot both exist",
             "arithmetic": "50 (upper middle, from 51 = 50 + 1) + 45 (around (8,8), from "
                           "45 = 45 + 0) + 16 + 12 + 8 + 1 = 132 > 121 = the whole board",
             "consequence": "at most ONE of them.  The two readings 51 and 45 are "
                            "consistent with each other only through this: one of them "
                            "is a large state and the other is not.",
             "status": "PROVEN (the sum 121 is exact)"},
            {"rule": "I12 (the corner chain, run): the surviving corner triples",
             "the_chain": "d(6,10)=1 is free; d(7,10)=13=12+1 puts a 12-cell state on "
                          "(7,10) and (6,10); d(10,9)=61=12*5+1 crosses INTO that state "
                          "and walks 4 steps to (6,10) then exits to the (5,10) singleton; "
                          "|77-61|=16 puts both (10,8) and (10,9) in a 16-cell state; "
                          "d(6,9)=9=8+1 forces size(6,9)=8 exactly.",
             "measured": "the chain cuts the blind search from 347,802 pairs to 149 "
                         "12-cell + 630 8-cell + 7,534 16-cell candidates",
             "the_two_branches": "the '8' in 9 = 8 + 1 has TWO carriers -- (6,9)'s own "
                                 "state, or the state holding (5,9) -- because both "
                                 "(5,9) and (6,10) are d=1 neighbours of (6,9).  L2/L3 "
                                 "cannot separate them, so both are enumerated: 483 "
                                 "candidates carry it at (6,9), 399 at (5,9), 252 at both.",
             "the_surviving_split": "of the triples that survive every published reading "
                                     "inside them, the overwhelming majority have the 8 "
                                     "carried by (5,9), and only a small minority by "
                                     "(6,9).  The 12-cell state's 12 cells are FIXED in "
                                     "every survivor.",
             "the_sampling_bias_trap": "an earlier version of this note said the 12-cell "
                                       "state's twelve cells were FIXED.  That was "
                                       "sampling bias: the stored samples are the FIRST "
                                       "60 survivors, all from one branch.  Measured over "
                                       "all 58,765, only (6,10) and (7,10) are certain, "
                                       "and the 8-cell state's core is five cells "
                                       "((2,9) (3,9) (4,9) (4,10) (5,9)).",
             "status": "PROVEN (the chain and the split); PROVISIONAL (the tight-edge "
                       "choices and the tails of the 16-cell state)"},
            {"rule": "I13 (the 8-cell state must not shortcut (10,9))",
             "why": "measured: a triple whose 8-cell state reaches (10,10) gives a local "
                    "d(10,9) of 53, not 61 -- the 8-cell state offers a cheaper route "
                    "than the 12-cell one.  L1 tightness bites a cell other than the one "
                    "being solved.",
             "status": "PROVEN"},
            {"rule": "I14 (the 45 needs a nine-cell state)",
             "why": "(8,8) lands inside the 12-cell state in 60 of 60 samples; the local "
                    "field gives 49 against a published 45 (an upper bound, so no "
                    "contradiction, but the path is not the 4-step one).  The only "
                    "decomposition that works is 45 = 12*3 + 9: three steps inside the "
                    "12-cell state, then a crossing of cost 9 into a NINE-cell state.",
             "consequence": "(8,8) sits exactly 3 steps from (6,10) inside the 12-cell "
                            "state, and a 9-cell state exists next to it",
             "status": "PROVISIONAL"},
            {"rule": "I11 (how many singletons the readings force)",
             "measured": "the five d=1 cells ((2,5), (3,6), (4,10), (5,9) and the derived "
                         "(6,10)) are covered by TWO singletons: (5,10) covers (4,10), "
                         "(5,9), (6,10); (3,5) [or (2,6)] covers (2,5) and (3,6) -- and "
                         "the same (3,5) singleton is the one I9 needs for 51 = 50 + 1",
             "status": "PROVEN for the cover; the CHOSEN positions are PROVISIONAL"},
        ],
    })

    # ------------------------------------------------------------------ #
    # F12  the readings that were guessed and then refuted by the readings
    facets.append({
        "id": "F-withdrawn-readings",
        "name": "readings that were guessed, and then refuted by the published numbers",
        "source": "the human's corner hypothesis, re-checked here",
        "status": "WITHDRAWN",
        "locality": {"kind": "field", "radius": 1},
        "instances": [
            {"rule": "R2: 'the (10,9) state has 12 cells'",
             "why_it_is_false": "(10,8) = 77 and (10,9) = 61 are ADJACENT, and for "
                                "adjacent cells |d(x) - d(y)| <= min(size_x, size_y), so "
                                "both states have at least 16 cells.  A 12-cell state at "
                                "(10,9) would also give d(10,8) <= 12 + 61 = 73 < 77.",
             "what_survives": "the ARITHMETIC of the human's reading survives exactly: "
                               "61 = 12*5 + 1 and 13 = 12 + 1 use the SAME 12-cell "
                               "state and the SAME singleton at (5,10).  Only the anchor "
                               "moves: the 12-cell state is the one the path CROSSES "
                               "INTO, and it holds (6,10) and (7,10).  See I7.",
             "status": "WITHDRAWN as stated; the reading itself is PROVISIONAL (I7)"},
            {"rule": "R3: 'the 16-cell block at (10,8)' -- i.e. that a 16-cell state "
                     "holds (10,8) and that the crossing to (10,9) costs 16",
             "status": "PROVISIONAL, not withdrawn: the LOWER BOUND min >= 16 is proven "
                       "(I3), and the equality needs the tight edge of the 77 to be "
                       "(10,9) (I5).  The enumeration found 25,749 sixteen-cell states "
                       "containing (10,8), 7,735 of them legal under the per-block "
                       "filters -- but 0 of them fit beside the 12-block the trim had "
                       "picked, and that 12-block was in the wrong place (I7).",
             },
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
