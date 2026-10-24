"""TOOL 4 -- the assumption ledger.

The protocol the picture missed:

    assume a state's area (with or without its exact shape)
      -> recompute the travelling distance to EVERY capitol
         (and assume the capitols' own state sizes)
      -> check ALL published travelling costs for consistency
      -> and check the impact of the assumption on every OTHER cell.

This module implements exactly that, and it is deliberately paranoid about
three things that a value-only calculation gets wrong:

  1. A state's capitol exists only if EVERY non-trivial self-symmetry fixes
     exactly ONE cell.  A mirror axis that runs *along* a column of cells
     fixes all of them, so such a state has NO capitol -- and therefore
     contributes NO destination to the distance field.  Even-sized states
     always fall in this class (a state with a capitol has size 1 + a sum of
     2/4/8, so it is always odd).

  2. A cell that reads 1 cannot be a 1x1 state: a singleton is its own
     capitol, so it would read 0.

  3. A cell that reads 0 is a capitol, but that does NOT make it a singleton.
     The size of a capitol's own state is a separate assumption.

Usage:
    python3 lr11/assume.py spec.json
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lr11 import kernel as K

Cell = Tuple[int, int]
State = FrozenSet[Cell]
N = 11


# --------------------------------------------------------------------------- #
# state legality -- the part that a "does the number fit?" check misses
# --------------------------------------------------------------------------- #
def state_report(S: Iterable[Cell], published: Dict[Cell, int]) -> dict:
    """Everything that can be said about one assumed state."""
    S = frozenset(S)
    size = len(S)
    grp = K.symmetry_group(S)
    cap = K.capitol_of(S)
    issues: List[str] = []

    if not S:
        return {"size": 0, "symmetry": [], "capitol": None, "issues": ["empty state"]}
    if not K.connected(S):
        issues.append("not 4-connected")
    if not grp:
        issues.append("no non-trivial self-symmetry: not a state at all")
    if size % 2 == 0:
        issues.append("even size => no capitol (a state with a capitol is always odd)")
    if cap is None and grp:
        fixed = {nm: len(fs) for nm, fs in grp.items()}
        issues.append("no capitol: its symmetries fix " +
                      ", ".join(f"{nm}:{k}" for nm, k in sorted(fixed.items())) +
                      " cells (needs exactly 1)")
    if cap is not None:
        if cap in published and published[cap] != 0:
            issues.append(f"its capitol {cap} reads {published[cap]}, not 0")
    # every published 0 inside the state must be that state's capitol
    zeros = [c for c in S if published.get(c) == 0]
    if zeros and (cap is None or zeros != [cap]):
        issues.append(f"published 0 inside the state at {zeros} but the capitol is {cap}")
    return {
        "size": size,
        "symmetry": sorted(grp),
        "capitol": cap,
        "issues": issues,
    }


# --------------------------------------------------------------------------- #
# the distance field under an assumption
# --------------------------------------------------------------------------- #
def _dijkstra(n: int, src: Iterable[Cell], size_of: Dict[Cell, int],
               optimistic: bool) -> Tuple[Dict[Cell, int], Dict[Cell, List[Cell]]]:
    """Least cost from the sources, plus the route that achieves it.

    `size_of` gives the size of the state of every KNOWN cell.  Cells that are
    not in it are "free": their state size is unknown, so an edge touching one
    has an unknown cost min(known, free).

    optimistic = True   (the LOWER book)
        every edge is charged as little as it can be: a free cell is charged 1
        (its state could be a 1x1), a known-known edge is charged exactly.
        The result is a lower bound on the distance to the KNOWN capitols.

    optimistic = False  (the UPPER book)
        a free<->free edge is FORBIDDEN: min(su,sv) has no upper bound when
        both sizes are unknown, so no path through them can be used to bound
        the distance from above.  A known<->free edge is charged the KNOWN
        side, which IS an upper bound on min(known, free).
        The result is an upper bound on the distance to the KNOWN capitols.
    """
    import heapq
    INF = float("inf")
    dist: Dict[Cell, float] = {}
    prev: Dict[Cell, Cell] = {}
    pq: List[Tuple[int, Cell]] = []
    for s in src:
        dist[s] = 0
        heapq.heappush(pq, (0, s))
    while pq:
        d, u = heapq.heappop(pq)
        if u in dist and d > dist[u]:
            continue
        for v in K.neighbours(u):
            if not (0 <= v[0] < n and 0 <= v[1] < n):
                continue
            ku, kv = size_of.get(u), size_of.get(v)
            if ku is None and kv is None:
                if not optimistic:
                    continue
                w = 1
            elif ku is None:
                w = 1 if optimistic else kv
            elif kv is None:
                w = 1 if optimistic else ku
            else:
                w = min(ku, kv)
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    routes: Dict[Cell, List[Cell]] = {}
    for c in dist:
        chain = [c]
        while chain[-1] in prev:
            chain.append(prev[chain[-1]])
        routes[c] = chain
    return {c: int(v) for c, v in dist.items() if v != INF}, routes


def analyse(states: Sequence[Iterable[Cell]],
            published: Dict[Cell, int],
            n: int = N,
            capitol_hypotheses: Sequence[Tuple[Cell, int]] = (),
            hidden_capitols: Sequence[Cell] = ()) -> dict:
    """The assumption ledger.

    states              -- the assumed states (cell sets).  Their AREA is
                          therefore assumed exactly; their shape is assumed
                          exactly too, but only the area and the capitol matter
                          for the numbers.
    capitol_hypotheses -- (cell, size) pairs: "treat this cell as a capitol,
                          and its state has this many squares".  This is how a
                          hidden capitol is put into the calculation.
    hidden_capitols    -- cells that are capitols of a state whose SIZE is
                          still unknown (they are sources but their outgoing
                          edges have no known cost).
    """
    states = [frozenset(s) for s in states]
    size_of: Dict[Cell, int] = {}
    state_of: Dict[Cell, int] = {}
    reports = []
    for i, S in enumerate(states):
        rep = state_report(S, published)
        rep["index"] = i
        rep["cells"] = sorted(S)
        reports.append(rep)
        for c in S:
            size_of[c] = len(S)
            state_of[c] = i

    # ---- capitols -------------------------------------------------------- #
    known_capitols: Set[Cell] = set(hidden_capitols)
    for S in states:
        cap = K.capitol_of(S)
        if cap is not None:
            known_capitols.add(cap)
    # a published 0 is a capitol; if it is not inside an assumed state, its
    # state size is unknown -> it is a free source.
    free_capitols: Set[Cell] = {c for c, v in published.items()
                                if v == 0 and c not in size_of}
    known_capitols |= free_capitols
    for cell, k in capitol_hypotheses:
        size_of[cell] = k
        known_capitols.add(cell)

    # ---- two distance fields --------------------------------------------- #
    # lower book: every free cell is as small as it can be (size 1)
    lb, lb_route = _dijkstra(n, known_capitols, size_of, optimistic=True)
    # upper book: free<->free edges cannot be bounded from above, so they are
    # dropped; a known<->free edge is charged the known side, which IS an
    # upper bound on the crossing cost min(su,sv).
    ub, ub_route = _dijkstra(n, known_capitols, size_of, optimistic=False)

    # ---- verdicts on the published numbers ------------------------------- #
    # NOTE the asymmetry, and it is the whole point of the ledger.
    # The two books are about the distance to the capitols we ALREADY KNOW
    # about (the published 0s, the capitols of the assumed states, and the
    # assumed capitols).  They are NOT bounds on the true d(x): an UNREVEALED
    # capitol can be nearer than both.  Hence:
    #   ub < v   is a CONTRADICTION  (a known capitol is strictly cheaper)
    #   lb > v   is NOT a contradiction -- it is a DEMAND: a hidden capitol
    #            has to exist, strictly nearer than the nearest known one.
    verdicts: Dict[Cell, dict] = {}
    for c, v in sorted(published.items()):
        L = lb.get(c)
        U = ub.get(c)
        if L is not None and U is not None and L == U == v:
            verdict = "FORCED"
            why = f"the assumptions pin the distance to exactly {v}"
        elif U is not None and U < v:
            verdict = "CONTRADICTED"
            why = (f"a KNOWN capitol is already reachable for {U} < the published {v}: "
                   f"the number cannot be the minimum")
        elif U is not None and U == v:
            verdict = "TIGHT_GEODESIC"
            why = (f"a known capitol is reachable for at most {v}, and the number says the "
                   f"minimum is {v}: no hidden capitol may be nearer")
        elif L is not None and L > v:
            verdict = "NEEDS_HIDDEN_CAPITOL"
            why = (f"the nearest KNOWN capitol is at least {L} away, but the cell reads {v}, "
                   f"so an UNREVEALED capitol has to be strictly nearer than that")
        elif L is not None and L == v:
            verdict = "TIGHT_CHEAPEST"
            why = (f"{v} is the floor: no capitol can be nearer than {v}, and one has to sit "
                   f"at exactly {v}")
        else:
            verdict = "NEEDS_EXACT_PATH"
            why = (f"the published {v} sits inside the range "
                   f"[{L if L is not None else '-'}, {U if U is not None else '-'}]: a capitol "
                   f"has to be reachable at exactly {v}")
        verdicts[c] = {
            "published": v, "lb": L, "ub": U, "verdict": verdict, "why": why,
            "route_to_known_capitol": [list(x) for x in ub_route.get(c, [])] or None,
        }

    violations = [(c, d) for c, d in verdicts.items() if d["verdict"] == "CONTRADICTED"]

    # ---- the impact of each assumed state on the other cells --------------- #
    impact = []
    for i, S in enumerate(states):
        touched = sorted(c for c in S if c in published)
        reach = {c: lb.get(c) for c in touched}
        impact.append({
            "index": i,
            "size": len(S),
            "capitol": reports[i]["capitol"],
            "published_inside": {str(c): published[c] for c in touched},
            "distance_inside": {str(c): reach[c] for c in touched},
            "issues": reports[i]["issues"],
        })

    return {
        "states": reports,
        "known_capitols": sorted(known_capitols),
        "free_capitols": sorted(free_capitols),
        "covered_cells": len(size_of),
        "free_cells": n * n - len(size_of),
        # NOT bounds on the true d: they are the two ends of the distance to
        # the capitols we already KNOW about.  A hidden capitol can be nearer
        # than both, which is why "lb > v" is a demand and not a contradiction.
        "near_known_optimistic": {str(c): v for c, v in sorted(lb.items())},
        "near_known_pessimistic": {str(c): v for c, v in sorted(ub.items())},
        "verdicts": {str(c): d for c, d in verdicts.items()},
        "violations": [(str(c), d["verdict"]) for c, d in violations],
        "impact": impact,
    }


# --------------------------------------------------------------------------- #
# where could the hidden capitol be?
# --------------------------------------------------------------------------- #
def hidden_capitol_candidates(published: Dict[Cell, int],
                              states: Sequence[Iterable[Cell]],
                              n: int = N,
                              cap: int = 40) -> Dict[Cell, List[Cell]]:
    """For every published cell that NEEDS a hidden capitol, list the cells
    that could BE that capitol.

    A cell y can be the hidden capitol of x if some path from x to y can be
    paid for with exactly the published amount, in the relaxation where every
    free cell may be sized freely.  This is a NECESSARY condition, computed
    with a cost-aware search over (cell, cost).
    """
    size_of: Dict[Cell, int] = {}
    for S in states:
        for c in S:
            size_of[c] = len(S)
    src = {c for c, v in published.items() if v == 0}
    for S in states:
        k = K.capitol_of(S)
        if k is not None:
            src.add(k)

    out: Dict[Cell, List[Cell]] = {}
    for x, v in sorted(published.items()):
        if v == 0:
            continue
        # Dijkstra over (cell, cost) keeping, for every cell, the set of
        # achievable path costs is expensive; instead keep the min and the
        # max reachable cost per cell, which brackets the exact value.
        # A path's cost is a sum of edge costs; a known<->known edge is fixed,
        # a known<->free edge is in [1, known size], a free<->free edge is in
        # [1, infinity) but bounded by the state sizes of its endpoints.
        import heapq
        INF = float("inf")
        lo: Dict[Cell, int] = {s: 0 for s in src}
        hi: Dict[Cell, int] = {s: 0 for s in src}
        pq: List[Tuple[int, Cell]] = [(0, s) for s in src]
        seen: Set[Tuple[Cell, int]] = set()
        # max reachable cost: charge every edge the full known size, and cap
        # free<->free edges by the largest possible state (the board size).
        BIG = n * n
        while pq and len(seen) < 400000:
            d, u = heapq.heappop(pq)
            if (u, d) in seen:
                continue
            seen.add((u, d))
            for w in K.neighbours(u):
                if not (0 <= w[0] < n and 0 <= w[1] < n):
                    continue
                ku, kv = size_of.get(u), size_of.get(w)
                if ku is None and kv is None:
                    wlo, whi = 1, BIG
                elif ku is None:
                    wlo, whi = 1, kv
                elif kv is None:
                    wlo, whi = 1, ku
                else:
                    wlo = whi = min(ku, kv)
                nd = d + wlo
                if w not in lo or nd < lo[w]:
                    lo[w] = nd
                    heapq.heappush(pq, (nd, w))
                # max: this is not a shortest-path quantity, so it is computed
                # separately with a relaxed relaxation
        cands = []
        for y in range(n):
            for z in range(n):
                if (y, z) in lo and lo[(y, z)] <= v <= _max_cost((y, z), src, size_of, n, BIG):
                    cands.append((y, z))
        if cands:
            out[x] = sorted(cands)
    return out


def _max_cost(target, src, size_of, n, BIG) -> int:
    """The largest path cost from any source to `target` in the relaxation
    (every edge charged as much as it can be).  Computed with a Bellman-Ford
    style relaxation on a finite budget."""
    import heapq
    # maximise: use Dijkstra on the negated cost
    dist = {s: 0 for s in src}
    pq = [(-0, s) for s in src]
    best = {s: 0 for s in src}
    while pq:
        negd, u = heapq.heappop(pq)
        d = -negd
        if d < best.get(u, -1):
            continue
        for w in K.neighbours(u):
            if not (0 <= w[0] < n and 0 <= w[1] < n):
                continue
            ku, kv = size_of.get(u), size_of.get(w)
            if ku is None and kv is None:
                wgt = BIG
            elif ku is None:
                wgt = kv
            elif kv is None:
                wgt = ku
            else:
                wgt = min(ku, kv)
            nd = d + wgt
            if nd > best.get(w, -1):
                best[w] = nd
                heapq.heappush(pq, (-nd, w))
    return best.get(target, -1)


# --------------------------------------------------------------------------- #
def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    spec = json.load(open(argv[0]))
    published = {tuple(int(x) for x in k.split(",")): v
                 for k, v in spec.get("published", {}).items()}
    if not published:
        from lr11 import tools as T
        published = dict(T.PUBLISHED)
    states = [frozenset(tuple(c) for c in S) for S in spec.get("states", [])]
    caps = [(tuple(c), k) for c, k in spec.get("capitol_hypotheses", [])]
    hidden = [tuple(c) for c in spec.get("hidden_capitols", [])]
    rep = analyse(states, published, capitol_hypotheses=caps, hidden_capitols=hidden)
    print(json.dumps(rep, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
