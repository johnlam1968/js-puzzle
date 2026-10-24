"""Triple test: 8-cell + 16-cell + a MID-sized state anchored at (8,8).

The pairwise diagnosis showed:
    (12,8)   -> 0 survivors      the 12-cell hypothesis is the broken one
    (12,16)  -> 154k+ survivors
    (8,16)   -> 42346 survivors  the 8-cell and 16-cell states coexist

and the published 45 at (8,8) is the number that kills the 12-cell reading:
any 12- or 8-cell state next to (8,8) gives (8,8) a route to a revealed
capitol costing 32-41 < 45.  So (8,8) most likely belongs to a MID-sized
state.  45 = 5*9, 3*15, 4*11+1, 44+1 are the decompositions that fit.

This script enumerates those mid-sized candidates, prefilters them with a
necessary condition derived from the cone, and then runs the triple test
against the surviving (8,16) pairs.

    python3 lr11/triple.py
"""

from __future__ import annotations

import sys
from typing import List, Tuple

sys.path.insert(0, __file__.rsplit("/", 2)[0])

try:
    from lr11 import kernel as K
    from lr11 import tools as T
except ImportError:
    import kernel as K          # type: ignore
    import tools as T           # type: ignore

FORBID = {(5, 10)} | (T.CAPITOL_CELLS - {(5, 10)})
FORBID_16 = FORBID | {(10, 6), (10, 7)}
SINGLETON = frozenset({(5, 10)})

MID_SIZES = [4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 25, 30, 33, 36, 40, 44, 45, 50]


def prefiltered(size, anchors, forbid):
    out = T.grow_states(size, list(anchors), forbid=forbid)
    out = [(S, nm) for S, nm in out if T.internal_consistency(S, T.PUBLISHED) is None]
    keep = []
    for S, nm in out:
        rep = T.check_partial([SINGLETON, frozenset(S)], T.PUBLISHED)
        if rep["contradicted"] or rep["structural_problems"]:
            continue
        keep.append((S, nm))
    return keep


def cone_ok(S) -> bool:
    """Necessary condition from the published 45 at (8,8).

    If the mid-sized state M has a capitol, the route inside M from (8,8) to
    that capitol costs |M| * dist_M((8,8), capitol).  Since d(8,8) = 45, that
    route can be at most 45, so |M| * dist <= 45.
    """
    cap = K.capitol_of(S)
    if cap is None:
        return True
    dist = T._state_distances(S)
    d = dist.get(((8, 8), cap))
    if d is None:
        return False
    return len(S) * d <= 45


def main():
    c8 = prefiltered(8, [(5, 9), (6, 9)], FORBID)
    c16 = prefiltered(16, [(10, 8), (10, 9)], FORBID_16)
    print(f"pools: 8-cell={len(c8)}  16-cell={len(c16)}\n", flush=True)

    # the (8,16) pairs that survive on their own
    print("pair (8,16):", flush=True)
    pair816 = []
    for (S8, n8) in c8:
        for (S16, n16) in c16:
            if S8 & S16:
                continue
            rep = T.check_partial([SINGLETON, frozenset(S8), frozenset(S16)], T.PUBLISHED)
            if rep["contradicted"] or rep["structural_problems"]:
                continue
            pair816.append((S8, n8, S16, n16))
    print(f"  {len(pair816)} surviving (8,16) pairs", flush=True)

    for size in MID_SIZES:
        cM = prefiltered(size, [(8, 8)], FORBID)
        cM = [(S, nm) for (S, nm) in cM if cone_ok(S)]
        if not cM:
            continue
        print(f"\nmid state of size {size}: {len(cM)} candidates after the cone filter",
              flush=True)
        # for each mid candidate, keep the (8,16) pairs that also work with it
        keep = []
        for (S8, n8, S16, n16) in pair816:
            for (SM, nm) in cM:
                if (SM & S8) or (SM & S16):
                    continue
                rep = T.check_partial([SINGLETON, frozenset(S8), frozenset(S16),
                                       frozenset(SM)], T.PUBLISHED)
                if rep["contradicted"] or rep["structural_problems"]:
                    continue
                keep.append((S8, n8, S16, n16, SM, nm, rep))
        print(f"  -> {len(keep)} triples", flush=True)
        for S8, n8, S16, n16, SM, nm, rep in keep[:5]:
            print(f"     8[{n8}]  {sorted(S8)}")
            print(f"    16[{n16}] {sorted(S16)}")
            print(f"    M[{nm}] size={len(SM)} {sorted(SM)}")
            print(f"    capitols={rep['known_capitals']}")
        if len(keep) > 5:
            print(f"     ... and {len(keep)-5} more")


if __name__ == "__main__":
    main()
