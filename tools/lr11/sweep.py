"""Joint lower-right enumeration, parameterised by anchor sets.

    python3 lr11/sweep.py

Pipeline
--------
1. For every anchor hypothesis, enumerate the legal candidate shapes of the
   12-cell / 8-cell / 16-cell state (whole-orbit growth, `tools.grow_states`).
2. PRE-FILTER each candidate list on its own: a single state plus the forced
   1x1 state at (5,10) must already not contradict any published number.
3. Keep the pairwise-disjoint triples and apply the rigorous upper-bound
   contradiction test to the whole corner.
"""

from __future__ import annotations

import sys
from typing import Dict, FrozenSet, List, Sequence, Tuple

sys.path.insert(0, __file__.rsplit("/", 2)[0])

try:
    from lr11 import kernel as K          # package layout
    from lr11 import tools as T
except ImportError:                       # flat layout (tools/lr11/)
    import kernel as K                    # type: ignore
    import tools as T                     # type: ignore

Cell = Tuple[int, int]
FORBID = {(5, 10)} | (T.CAPITOL_CELLS - {(5, 10)})

# Rigorous consequence of the published numbers (see docs/03, D2 and the
# upper-bound argument): the 16-cell state contains (10,8) and (10,9), so the
# step (10,8)->(10,9) already costs 16 and d(10,8) = 77 = 16 + 61 exactly.
# If the 16-cell state also held (10,6) and (10,7), the path
# (10,8)->(10,7)->(10,6)->(10,5) would cost 3*16 = 48 < 77, so d(10,8) <= 48,
# contradicting the published 77.  Hence (10,6) and (10,7) cannot be in it.
FORBID_16 = FORBID | {(10, 6), (10, 7)}


def candidates(size: int, anchors: Sequence[Cell], forbid=FORBID) -> List[Tuple[FrozenSet[Cell], str]]:
    out = T.grow_states(size, list(anchors), forbid=forbid)
    return [(S, nm) for S, nm in out if T.internal_consistency(S, T.PUBLISHED) is None]


def prefilter(cands: Sequence[Tuple[FrozenSet[Cell], str]]) -> List[Tuple[FrozenSet[Cell], str]]:
    """Keep the candidates that do not ALONE contradict a published number."""
    keep = []
    for S, nm in cands:
        rep = T.check_partial([frozenset({(5, 10)}), frozenset(S)], T.PUBLISHED)
        if rep["contradicted"] or rep["structural_problems"]:
            continue
        keep.append((S, nm))
    return keep


ANCHOR_SETS = {
    "12": [[(6, 10), (7, 10)]],
    "8":  [[(5, 9), (6, 9)],
           [(6, 9)]],
    "16": [[(10, 8), (10, 9)]],
}


def sweep(verbose: int = 8) -> None:
    cache: Dict[Tuple[str, int, Tuple[Cell, ...]], List] = {}
    for key, sets in ANCHOR_SETS.items():
        size = int(key)
        forb = FORBID_16 if key == "16" else FORBID
        for a in sets:
            c = candidates(size, a, forb)
            p = prefilter(c)
            cache[(key, tuple(a))] = p
            print(f"  {key:>2}-state anchors {str(a):<40} -> {len(c):>5} legal, "
                  f"{len(p):>5} after the single-state bound check", flush=True)
    print(flush=True)

    best = []
    for a12 in ANCHOR_SETS["12"]:
        for a8 in ANCHOR_SETS["8"]:
            for a16 in ANCHOR_SETS["16"]:
                c12 = cache[("12", tuple(a12))]
                c8 = cache[("8", tuple(a8))]
                c16 = cache[("16", tuple(a16))]
                if not (c12 and c8 and c16):
                    continue
                # bitmask disjointness: O(1) per test instead of set intersection
                def mask(cells):
                    m = 0
                    for (r, c) in cells:
                        m |= 1 << (r * 11 + c)
                    return m
                m12 = [(mask(S), S, nm) for S, nm in c12]
                m8 = [(mask(S), S, nm) for S, nm in c8]
                m16 = [(mask(S), S, nm) for S, nm in c16]
                survivors = []
                for k12, S12, n12 in m12:
                    for k8, S8, n8 in m8:
                        if k12 & k8:
                            continue
                        for k16, S16, n16 in m16:
                            if (k16 & k12) or (k16 & k8):
                                continue
                            states = [frozenset({(5, 10)}), frozenset(S12),
                                       frozenset(S8), frozenset(S16)]
                            rep = T.check_partial(states, T.PUBLISHED)
                            if rep["contradicted"] or rep["structural_problems"]:
                                continue
                            survivors.append((S12, n12, S8, n8, S16, n16, rep))
                if survivors:
                    print(f"*** {len(survivors):>5} joint survivors   "
                          f"12={a12}  8={a8}  16={a16}", flush=True)
                    for S12, n12, S8, n8, S16, n16, rep in survivors[:verbose]:
                        print(f"      12[{n12}] {sorted(S12)}")
                        print(f"       8[{n8}] {sorted(S8)}")
                        print(f"      16[{n16}] {sorted(S16)}")
                        print(f"      capitols {rep['known_capitals']}  "
                              f"hidden-capitol demands {len(rep['needs_hidden_capitol'])}")
                    if len(survivors) > verbose:
                        print(f"      ... and {len(survivors)-verbose} more")
                    print(flush=True)
                    best.append((len(survivors), a12, a8, a16, survivors))

    if best:
        best.sort(key=lambda t: -t[0])
        print("=" * 74)
        print(f"BEST: {best[0][0]} joint survivors for 12={best[0][1]} 8={best[0][2]} 16={best[0][3]}")
    else:
        print("NO joint survivor for any anchor hypothesis")


if __name__ == "__main__":
    sweep()
