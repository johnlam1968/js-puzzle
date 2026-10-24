"""Audit of the 'best surviving triple' that was drawn in output/shapes.png.

The user is right that a picture of three states is not a solution.  This
script re-runs the rigorous checker on exactly the triple that was drawn, and
audits three specific claims:

  C1  a published 1 cell must NOT be a 1x1 state (a singleton is its own
      capitol, so it would read 0);
  C2  the 16-cell state drawn in the picture cannot produce d(10,8) = 77;
  C3  the drawn triple cannot produce d(2,10) = 14.

It also records what the enumeration actually ASSUMED about the two revealed
capitols (5,7) and (10,5) -- in particular whether their state size was fixed
to 1 or left free.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lr11 import kernel as K
from lr11 import tools as T

Cell = tuple


def load_triple():
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes.json")))
    e = d["best"]["11"]
    M = frozenset(tuple(x) for x in e["M"])
    S8 = frozenset(tuple(x) for x in e["eight"])
    S16 = frozenset(tuple(x) for x in e["sixteen"])
    single = frozenset({(5, 10)})
    return M, S8, S16, single, e


def exact_within_known(states, capits, n=11):
    """Exact d-field over the KNOWN states only: edges inside a known state cost
    the state size, edges into a free cell are not used at all (a free cell's
    state size is unknown, so we cannot bound the crossing from above without
    also bounding the free side).  This is an UPPER bound on the true d."""
    size = {}
    for S in states:
        for c in S:
            size[c] = len(S)
    import heapq
    INF = float("inf")
    dist = {}
    pq = []
    for c in capits:
        dist[c] = 0
        heapq.heappush(pq, (0, c))
    while pq:
        d, u = heapq.heappop(pq)
        if u in dist and d > dist[u]:
            continue
        for v in K.neighbours(u):
            if not (0 <= v[0] < n and 0 <= v[1] < n):
                continue
            if u not in size or v not in size:
                continue           # only fully-known edges
            w = min(size[u], size[v])
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return {c: v for c, v in dist.items() if v != INF}


def main():
    M, S8, S16, single, e = load_triple()
    states = [single, S8, S16, M]
    names = ["singleton(5,10)", "8-state", "16-state", "Gamma(11)"]

    print("=" * 78)
    print("A. the drawn triple, re-checked")
    print("=" * 78)
    for nm, S in zip(names, states):
        cap = K.capitol_of(S)
        print(f"  {nm:<18} size={len(S):>2}  capitol={cap}  "
              f"published@capitol={T.PUBLISHED.get(cap, 'not published')}")

    rep = T.check_partial(states, T.PUBLISHED)
    print(f"\n  contradicted        : {len(rep['contradicted'])}")
    for c, v, why in rep["contradicted"]:
        print(f"      {c} reads {v}: {why}")
    print(f"  structural problems : {len(rep['structural_problems'])}")
    for why in rep["structural_problems"]:
        print(f"      {why}")
    print(f"  known capitols      : {rep['known_capitals']}")
    print(f"  covered / free cells: {rep['covered_cells']} / {rep['free_cells']}")

    capits = set(rep["known_capitals"])
    ub = exact_within_known(states, capits)
    print("\n  upper bounds from the KNOWN states alone (exact inside them):")
    for c in sorted(T.PUBLISHED):
        u = ub.get(c)
        p = T.PUBLISHED[c]
        flag = ""
        if u is not None and u < p:
            flag = "   <<< CONTRADICTION"
        elif u is not None and u == p:
            flag = "   (geodesic: no hidden capitol may be closer)"
        print(f"      {c} published {p:>3}   known-state upper bound "
              f"{'-' if u is None else u:>4}{flag}")

    print()
    print("=" * 78)
    print("B. claim C1 -- a published 1 cell must not be a 1x1 state")
    print("=" * 78)
    ones = [c for c, v in T.PUBLISHED.items() if v == 1]
    print(f"  published 1 cells: {sorted(ones)}")
    for c in ones:
        s1 = frozenset({c})
        why = T.internal_consistency(s1, T.PUBLISHED)
        cap = K.capitol_of(s1)
        print(f"    {c}: singleton is a legal state = {K.is_legal_state(s1)}; "
              f"its capitol is {cap} (so d would be 0, but the cue says 1)")
        print(f"          internal_consistency() says: {why!r}   "
              f"<- {'GAP: does not catch it' if why is None else 'caught'}")

    print()
    print("=" * 78)
    print("C. claim C2 -- the drawn 16-cell state vs the 77 at (10,8)")
    print("=" * 78)
    cap16 = K.capitol_of(S16)
    dist = T._state_distances(S16)
    for c in [(10, 8), (10, 9)]:
        j = dist.get((c, cap16))
        if j is None:
            print(f"  {c}: capitol {cap16} is not connected inside the state")
            continue
        route = len(S16) * j
        print(f"  {c} -> capitol {cap16}: {j} in-state steps x {len(S16)} = {route}"
              f"   (published {T.PUBLISHED[c]})"
              + ("   <<< TOO CHEAP: d <= %d < %d" % (route, T.PUBLISHED[c])
                 if route < T.PUBLISHED[c] else ""))
    # the bottom-right 5-cell corner
    corner = frozenset(x for x in S16 if x[0] >= 9 and x[1] >= 8)
    print(f"  bottom-right corner of the 16-state: {sorted(corner)} ({len(corner)} cells)")
    print(f"  published numbers inside it: "
          f"{ {c: T.PUBLISHED[c] for c in sorted(corner) if c in T.PUBLISHED} }")

    print()
    print("=" * 78)
    print("D. claim C3 -- can d(2,10) = 14 be reached in the drawn triple?")
    print("=" * 78)
    print(f"  (2,10) is inside a drawn state? "
          f"{[nm for nm, S in zip(names, states) if (2,10) in S] or 'no - it is free'}")
    u = ub.get((2, 10))
    print(f"  upper bound from known states alone: {u}")
    lo = rep["near_known_optimistic"].get("(2, 10)")
    hi = rep["near_known_pessimistic"].get("(2, 10)")
    print(f"  check_partial lower bound (optimistic) : {lo}")
    print(f"  check_partial upper bound (to a revealed capitol): {hi}")
    # what sizes could the state of (2,10) have for d = 14 to be reachable?
    print("  to reach exactly 14 the state of (2,10) must be large enough that the")
    print("  crossing cost does not undercut it; the neighbours are (1,10),(3,10),(2,9):")
    for nb in K.neighbours((2, 10)):
        inside = [nm for nm, S in zip(names, states) if nb in S]
        print(f"    {nb}: {inside or 'free'}"
              + (f"  published {T.PUBLISHED[nb]}" if nb in T.PUBLISHED else ""))

    print()
    print("=" * 78)
    print("E. what did the enumeration assume about the revealed capitols?")
    print("=" * 78)
    print(f"  revealed capitols (published 0): {sorted(T.CAPITOL_CELLS)}")
    for c in sorted(T.CAPITOL_CELLS):
        st = [nm for nm, S in zip(names, states) if c in S]
        print(f"    {c}: inside a drawn state? {st or 'NO - its state size was left FREE'}")
    print("  in check_partial the revealed 0-cells are added to `known_capitals` but")
    print("  NOT to `known_size`, so their state size is never fixed to 1.")
    print("  the singleton that WAS forced is (5,10), from d(4,10)=1:")
    print("     cost((4,10)->(5,10)) = min(|S(4,10)|, |S(5,10)|) = 1")
    print("     and |S(4,10)| = 1 is impossible (a singleton reads 0, not 1)")
    print("     => |S(5,10)| = 1.  Sound.")


if __name__ == "__main__":
    main()
