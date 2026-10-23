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
    """
    known = {x for x, v in hints.items() if v == 0}
    uncovered, satisfied = [], []
    for x, v in sorted(hints.items()):
        if v == 0:
            continue
        radius = (v + 1) // 2
        raw = ball(x, radius, n)
        if any(c in known for c in raw):
            satisfied.append((x, v, radius))
            continue
        candidates = [c for c in raw if c not in hints]   # a d>0 cell is never a capitol
        uncovered.append((x, v, radius, candidates))
    return uncovered, satisfied


def min_hitting_set(demands: Sequence[Tuple[Cell, int, int, List[Cell]]]):
    """Exact minimum hitting set (branch and bound, 'fewest viable candidates' first)."""
    best = [None, []]      # [size, [sets]]

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
    return {
        "hints": len(hints),
        "revealed_capitols": sorted(x for x, v in hints.items() if v == 0),
        "satisfied_by_revealed": len(satisfied),
        "uncovered_demands": len(demands),
        "candidate_pool": len(pool),
        "min_additional_capitols": size,
        "n_minimum_sets": len(sets),
        "minimum_sets": sets,
        "total_capitols_lower_bound": len([x for x, v in hints.items() if v == 0]) + size,
    }
