"""Pairwise diagnosis of the lower-right corner.

The full three-state joint test is expensive, so first run the three PAIR
tests separately: (12,8), (12,16), (8,16).  A pair that has no survivor at all
is the broken hypothesis, and it is much cheaper to find.

    python3 lr11/pairs.py
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
FORBID_16 = FORBID | {(10, 6), (10, 7)}   # see docs/08, derived from 77 = 61+16

SINGLETON = frozenset({(5, 10)})


def cands(size: int, anchors, forbid=FORBID):
    out = T.grow_states(size, list(anchors), forbid=forbid)
    out = [(S, nm) for S, nm in out if T.internal_consistency(S, T.PUBLISHED) is None]
    keep = []
    for S, nm in out:
        rep = T.check_partial([SINGLETON, frozenset(S)], T.PUBLISHED)
        if rep["contradicted"] or rep["structural_problems"]:
            continue
        keep.append((S, nm))
    return keep


def mask(cells):
    m = 0
    for (r, c) in cells:
        m |= 1 << (r * 11 + c)
    return m


def pair(label, A, B, verbose=6):
    surv = []
    for (SA, na) in A:
        ma = mask(SA)
        for (SB, nb) in B:
            if ma & mask(SB):
                continue
            rep = T.check_partial([SINGLETON, frozenset(SA), frozenset(SB)], T.PUBLISHED)
            if rep["contradicted"] or rep["structural_problems"]:
                continue
            surv.append((SA, na, SB, nb))
    print(f"{label}: {len(surv)} survivors", flush=True)
    for SA, na, SB, nb in surv[:verbose]:
        print(f"    A[{na}] {sorted(SA)}")
        print(f"    B[{nb}] {sorted(SB)}")
    if len(surv) > verbose:
        print(f"    ... and {len(surv)-verbose} more")
    print(flush=True)
    return surv


def main():
    c12a = cands(12, [(6, 10), (7, 10)])
    c12b = cands(12, [(7, 10)])
    c8a = cands(8, [(5, 9), (6, 9)])
    c8b = cands(8, [(6, 9)])
    c16a = cands(16, [(10, 8), (10, 9)], FORBID_16)
    c16b = cands(16, [(10, 9)], FORBID_16)
    c16c = cands(16, [(10, 8)], FORBID_16)
    print(f"pools: 12a={len(c12a)} 12b={len(c12b)} 8a={len(c8a)} 8b={len(c8b)} "
          f"16a={len(c16a)} 16b={len(c16b)} 16c={len(c16c)}\n", flush=True)

    for name, A, B in [("12a x 8a", c12a, c8a),
                       ("12a x 8b", c12a, c8b),
                       ("12b x 8a", c12b, c8a),
                       ("12a x 16a", c12a, c16a),
                       ("12a x 16b", c12a, c16b),
                       ("12a x 16c", c12a, c16c),
                       ("8a x 16a", c8a, c16a),
                       ("8a x 16b", c8a, c16b),
                       ("8a x 16c", c8a, c16c)]:
        pair(name, A, B)


if __name__ == "__main__":
    main()
