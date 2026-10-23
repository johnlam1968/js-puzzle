"""Enumeration of legal states and of the tilings they form (plan milestone M2).

(The module is called `tilings`, not `enumerate`: a module named `enumerate` shadows the
builtin for anyone doing `from enumerate import *`.)

Three products, all measured against the constants the review rounds established:

  * legal STATES   -- connected subsets with a non-trivial self-symmetry
  * TILINGS        -- partitions of the frame into legal states
  * breakdowns     -- by number of blocks, and by number of capitol-bearing states

The counting method is an exact-cover DP over "remaining cell" masks: the first still
uncovered cell must be covered by some legal state that contains it and fits in what is
left.  This visits each complete tiling exactly once, so the DP count is a proof, not a
sample.
"""


from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))




import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from rules import capitol_of, connected, shape_key, symmetry_group

Cell = Tuple[int, int]


def _grid(n: int) -> List[Cell]:
    return [(r, c) for r in range(n) for c in range(n)]


def connected_subsets(n: int) -> List[int]:
    """Every connected subset of the n x n grid, exactly once, as a bitmask.

    Canonical form: the smallest cell of the set is the anchor, and cells are added in
    increasing order, so no set is produced twice.
    """
    cells = _grid(n)
    N = n * n
    NB: List[int] = [0] * N
    for i, (r, c) in enumerate(cells):
        m = 0
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n:
                m |= 1 << (rr * n + cc)
        NB[i] = m
    res: List[int] = []
    full = (1 << N) - 1

    def expand(mask: int, cand: int, higher: int, excl: int):
        # ESU-style canonical enumeration.  TWO invariants are needed; missing either one
        # makes the same subset appear under different insertion orders (measured: 4x4 gave
        # 1,225,288 masks instead of 11,506):
        #   higher : every cell of the set is > the anchor;
        #   excl   : a cell already processed is excluded for all later siblings, so it
        #            cannot sneak back in through the neighbour relation.
        res.append(mask)
        while cand:
            b = cand & -cand
            cand ^= b
            i = b.bit_length() - 1
            newmask = mask | b
            newcand = ((cand | (NB[i] & ~newmask)) & ~newmask & higher) & ~excl
            excl |= b
            expand(newmask, newcand, higher, excl)

    for a in range(N):
        higher = full & ~((1 << (a + 1)) - 1)
        expand(1 << a, NB[a] & higher, higher, 0)
    return res


_CATALOGUE_CACHE: Dict[int, "Catalogue"] = {}

# The tiling DP memoises on the remaining-cell mask, so it needs 2^(n*n) entries.
# 4x4 -> 65k (fine), 5x5 -> 33M (slow but feasible once), 6x6 and up -> hopeless.
MAX_DP_SIZE = 5


class Catalogue:
    """The legal states of an n x n frame, indexed for the exact-cover DP.

    Cached per size: building the catalogue for 4x4 costs about a second, and the test
    suite wants it several times.
    """

    def __new__(cls, n: int):
        # NOTE: the object is cached only AFTER __init__ succeeded (see __init__), so a
        # failed construction can never leave a half-built object in the cache.
        if n in _CATALOGUE_CACHE:
            return _CATALOGUE_CACHE[n]
        return super().__new__(cls)

    def __init__(self, n: int):
        if getattr(self, "_built", False) and getattr(self, "n", None) == n:
            return
        self._built = True
        self.n = n
        self.cells = _grid(n)
        self.idx = {c: i for i, c in enumerate(self.cells)}
        t0 = time.time()
        subs = connected_subsets(n)
        self.connected_count = len(subs)
        states: List[Tuple[int, bool, Tuple[str, ...]]] = []
        for m in subs:
            cl = [self.cells[i] for i in range(n * n) if (m >> i) & 1]
            group = symmetry_group(cl)
            if not group:
                continue                                   # not a state at all
            cap = capitol_of(cl)
            states.append((m, cap is not None, tuple(sorted(group))))
        self.states = states
        self.legal_count = len(states)
        self.capitol_states = sum(1 for _, hc, _ in states if hc)
        self._cap_of_mask: Dict[int, bool] = {m: hc for m, hc, _ in states}
        self.by_cell: Dict[int, List[int]] = defaultdict(list)
        for m, hc, _ in states:
            for i in range(n * n):
                if (m >> i) & 1:
                    self.by_cell[i].append(m)
        # distinct shape types up to translation
        types = set()
        for m, _, _ in states:
            types.add(shape_key([self.cells[i] for i in range(n * n) if (m >> i) & 1]))
        self.shape_type_count = len(types)
        self.seconds = time.time() - t0
        # cache the FINISHED object (a half-built one must never be cached)
        _CATALOGUE_CACHE[n] = self

    # ------------------------------------------------------------------ #
    def count_tilings(self, by_blocks: bool = False, by_capitols: bool = False) -> Dict[str, object]:
        n = self.n
        if n > MAX_DP_SIZE:
            raise ValueError(
                f"the exact-cover DP needs a memo over 2^(n*n) masks; n={n} would need "
                f"2^{n*n} entries.  Only n <= {MAX_DP_SIZE} is feasible -- larger frames "
                f"need AODFS with the readings as constraints, not enumeration.")
        full = (1 << (n * n)) - 1
        memo: Dict[int, int] = {}

        def count(rem: int) -> int:
            if rem == 0:
                return 1
            if rem in memo:
                return memo[rem]
            first = (rem & -rem).bit_length() - 1
            tot = 0
            for m in self.by_cell[first]:
                if m & ~rem:
                    continue
                tot += count(rem ^ m)
            memo[rem] = tot
            return tot

        out: Dict[str, object] = {
            "size": n,
            "connected_subsets": self.connected_count,
            "legal_states": self.legal_count,
            "legal_states_with_capitol": self.capitol_states,
            "shape_types": self.shape_type_count,
            "tilings": count(full),
        }
        if by_blocks:
            memo_k: Dict[Tuple[int, int], int] = {}

            def count_k(rem: int, k: int) -> int:
                if rem == 0:
                    return 1 if k == 0 else 0
                if k < 0:
                    return 0
                key = (rem, k)
                if key in memo_k:
                    return memo_k[key]
                first = (rem & -rem).bit_length() - 1
                tot = 0
                for m in self.by_cell[first]:
                    if m & ~rem:
                        continue
                    tot += count_k(rem ^ m, k - 1)
                memo_k[key] = tot
                return tot

            dist = Counter()
            for k in range(1, n * n + 1):
                c = count_k(full, k)
                if c:
                    dist[k] = c
            out["tilings_by_blocks"] = dict(dist)
        if by_capitols:
            # count tilings by how many of their states carry a capitol.
            memo_c: Dict[Tuple[int, int], int] = {}

            def count_cap(rem: int, kcap: int) -> int:
                """completions that use EXACTLY kcap capitol-bearing states (kcap counts DOWN)"""
                if rem == 0:
                    return 1 if kcap == 0 else 0
                if kcap < 0:
                    return 0
                key = (rem, kcap)
                if key in memo_c:
                    return memo_c[key]
                first = (rem & -rem).bit_length() - 1
                tot = 0
                for m in self.by_cell[first]:
                    if m & ~rem:
                        continue
                    has = 1 if self._cap_of_mask[m] else 0
                    tot += count_cap(rem ^ m, kcap - has)
                memo_c[key] = tot
                return tot

            dist = Counter()
            for k in range(0, n * n + 1):
                c = count_cap(full, k)
                if c:
                    dist[k] = c
            out["tilings_by_capitols"] = dict(dist)
            out["tilings_without_capitol"] = dist.get(0, 0)
            out["tilings_with_capitol"] = sum(v for k, v in dist.items() if k >= 1)
        return out

    def cells_of(self, mask: int) -> List[Cell]:
        """The cells of a state mask."""
        return [self.cells[i] for i in range(self.n * self.n) if (mask >> i) & 1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="enumerate legal states and tilings of an NxN frame")
    ap.add_argument("--size", type=int, default=4)
    ap.add_argument("--by-blocks", action="store_true")
    ap.add_argument("--by-capitols", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    t0 = time.time()
    cat = Catalogue(args.size)
    print(f"[{args.size}x{args.size}] connected subsets = {cat.connected_count:,} "
          f"({cat.seconds:.1f}s)", flush=True)
    print(f"           legal states = {cat.legal_count:,}   "
          f"(with a capitol: {cat.capitol_states:,})   shape types = {cat.shape_type_count:,}", flush=True)
    res = cat.count_tilings(by_blocks=args.by_blocks, by_capitols=args.by_capitols)
    print(f"           tilings = {res['tilings']:,}   ({time.time()-t0:.1f}s total)")
    if args.by_blocks:
        print("           by blocks:", {k: v for k, v in sorted(res["tilings_by_blocks"].items())})
    if args.by_capitols:
        print("           by capitols:", {k: v for k, v in sorted(res["tilings_by_capitols"].items())})
    if args.json:
        print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
