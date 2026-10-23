"""Capitol-position hitting set: a lower bound on how many capitols a puzzle must have.

Step-count lemma.  If d(x) = v and the optimal path from x to its nearest capitol uses k
steps, then every step except the last costs at least 2: a step of cost 1 means entering
or leaving a 1x1 state, and a 1x1 state IS a capitol, so the path would have ended there.
Hence  v >= 2(k-1) + 1, so  k <= (v+1)/2, and therefore

    every hint x has a capitol within Manhattan distance floor((v+1)/2) of it.

So the capitols must HIT the ball of every hint.  A hint whose ball already contains a
REVEALLED capitol is already satisfied and needs nothing; the rest demand a HIDDEN capitol.
The minimum number of hidden capitols is a minimum hitting set over the remaining demands --
and since a 1x1 state is always a capitol, hidden capitols can only sit on blank cells.

(Plan section 1.11 / D46 / D52.  Note the numbers below are the CORRECTED ones: an earlier
version failed to recognise the 22 demands already covered by the two revealed capitols.)
"""


from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))




from typing import Dict, Iterable, List, Sequence, Set, Tuple

Cell = Tuple[int, int]


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def ball(x: Cell, radius: int, n: int) -> List[Cell]:
    return [(r, c) for r in range(n) for c in range(n)
            if (r, c) != x and manhattan(x, (r, c)) <= radius]


def split_demands(n: int, hints: Dict[Cell, int]):
    """Split the hints into (uncovered demands, demands already satisfied by a revealed capitol).

    A hint with v = 0 is a revealed capitol itself.  A revealed capitol is a hint cell, so
    it can never host a HIDDEN capitol -- hidden candidates are blank cells only.

    PLAN D64: a demand with v = 1 is SPECIAL.  A step of cost 1 means entering a 1x1 state,
    and a 1x1 state IS a capitol -- so the capitol serving that demand must itself be a
    1x1 state, i.e. the cell must be a singleton in the final partition.  That is a
    state-size constraint on top of a position constraint, and it has to travel with the
    demand into the solver.
    """
    known = {x for x, v in hints.items() if v == 0}
    uncovered, satisfied = [], []
    for x, v in sorted(hints.items()):
        if v == 0:
            continue
        radius = (v + 1) // 2
        raw = ball(x, radius, n)
        if any(c in known for c in raw):
            satisfied.append((x, v, radius, []))
            continue
        candidates = [c for c in raw if c not in hints]   # a d>0 cell is never a capitol
        uncovered.append((x, v, radius, candidates))
    return uncovered, satisfied


def singleton_candidates(n: int, hints: Dict[Cell, int]) -> Dict[Cell, List[Cell]]:
    """For every d = 1 hint, the cells that could host the forced 1x1 state (PLAN D64).

    A d = 1 cell is one cost-1 step away from a capitol; a cost-1 step only happens when one
    of the two states has size 1, and a 1x1 state is always a capitol.  Hence the capitol
    serving that hint must be a SINGLETON state adjacent to the hint.
    """
    out: Dict[Cell, List[Cell]] = {}
    for x, v in sorted(hints.items()):
        if v != 1:
            continue
        r, c = x
        cands = []
        for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            # exclude only cells that are hinted with d>0 (they can never be capitols);
            # a hinted d=0 cell IS a revealed capitol and may still be a 1x1 state
            if 0 <= nb[0] < n and 0 <= nb[1] < n and hints.get(nb, 0) <= 0:
                cands.append(nb)
        out[x] = cands
    return out


def packing_bound(demands) -> int:
    """A rigorous lower bound on the number of hidden capitols, from a dual certificate.

    If k demands have pairwise DISJOINT candidate sets, then k different capitols are
    needed (one per demand).  This is the integer dual certificate of the hitting-set LP:
    a packing of disjoint demand balls.

    NOTE on the LP relaxation: the plain LP relaxation of the hitting-set ILP
    (min sum y_c s.t. sum_{c in ball} y_c >= 1) has optimum <= the integer optimum, so it
    is a WEAKER count than the exact integer minimum -- its value is as a *certificate of
    infeasibility* for a candidate set, not as a sharper bound.  (The review round that
    proposed it stated it would be "tighter"; that is wrong and is corrected here.)
    """
    best = 0
    m = len(demands)
    for r in range(m + 1):
        found = False
        for combo in _combinations(range(m), r):
            sets = [set(demands[i][3]) for i in combo]
            ok = True
            for i in range(len(sets)):
                for j in range(i + 1, len(sets)):
                    if sets[i] & sets[j]:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                best = max(best, r)
                found = True
                break
        if not found and r > 0:
            break
    return best


def _combinations(iterable, r):
    from itertools import combinations
    return combinations(iterable, r)


def weighted_demand_order(demands):
    """Order demands by how much information they carry: tight balls first.

    Weight = 1 / radius^2 (a hint with a small radius constrains far fewer cells and is
    therefore the most informative).  This is a heuristic for enumeration order, NOT a bound.
    """
    return sorted(demands, key=lambda d: (1.0 / max(1, d[2]) ** 2, d[2], d[0]))


def min_hitting_set(demands: Sequence[Tuple[Cell, int, int, List[Cell]]]):
    """Exact minimum hitting set (branch and bound, 'fewest viable candidates' first)."""
    best = [None, []]      # [size, [sets]]

    if any(not d[3] for d in demands):
        # a demand with no candidate cell can never be satisfied
        return None, []

    def rec(chosen: List[Cell], covered: Set[int]):
        if best[0] is not None and len(chosen) > best[0]:
            return
        unc = [i for i in range(len(demands)) if i not in covered]
        if not unc:
            if best[0] is None or len(chosen) < best[0]:
                best[0] = len(chosen)
                best[1] = [tuple(sorted(chosen))]
            elif len(chosen) == best[0]:
                best[1].append(tuple(sorted(chosen)))
            return
        i = min(unc, key=lambda j: len([c for c in demands[j][3] if c not in chosen]))
        for c in demands[i][3]:
            if c in chosen:
                continue
            rec(chosen + [c], covered | {j for j in range(len(demands)) if c in demands[j][3]})

    rec([], set())
    return best[0], best[1]


def capitol_lower_bound(n: int, hints: Dict[Cell, int]) -> Dict[str, object]:
    """Full report: how many capitols must the solution have, and what they could be."""
    demands, satisfied = split_demands(n, hints)
    size, sets = min_hitting_set(demands)
    pool = sorted({c for _, _, _, C in demands for c in C})
    if size is None:
        return {
            "hints": len(hints),
            "revealed_capitols": sorted(x for x, v in hints.items() if v == 0),
            "satisfied_by_revealed": len(satisfied),
            "uncovered_demands": len(demands),
            "candidate_pool": len(pool),
            "min_additional_capitols": None,
            "n_minimum_sets": 0,
            "minimum_sets": [],
            "total_capitols_lower_bound": None,
            "note": "at least one demand has no candidate cell: the instance is infeasible",
        }
    revealed = sorted(x for x, v in hints.items() if v == 0)
    singles = singleton_candidates(n, hints)
    return {
        "hints": len(hints),
        "revealed_capitols": revealed,
        "satisfied_by_revealed": len(satisfied),
        "uncovered_demands": len(demands),
        "candidate_pool": len(pool),
        "min_additional_capitols": size,
        "n_minimum_sets": len(sets),
        "minimum_sets": sets,
        "total_capitols_lower_bound": len(revealed) + size,
        # PLAN D64: a d=1 demand must be served by a 1x1 state, so the capitol that covers
        # it has to be a SINGLETON.  These are the cells where that can happen.
        "singleton_demands": {x: c for x, c in singles.items()},
        # dual certificate: k demands with pairwise disjoint candidate sets need k capitols
        "packing_bound": packing_bound(demands),
        # enumeration order: the tightest (smallest radius) demands first
        "demand_order_tight_first": [(d[0], d[1], d[2]) for d in weighted_demand_order(demands)],
    }
