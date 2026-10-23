"""Catalogue-free state lookup: generate the legal states of a cell ON DEMAND.

Why this exists (GLM code review, BLOCKER): `Catalogue` materialises EVERY connected
subset of the frame and runs the symmetry test on each.  That is fine for 4x4 (11,506
subsets) and survivable for 5x5 (2.3M subsets, ~55 s), but it is hopeless for 6x6
(~30M) and absurd for 11x11.  Yet the search only ever needs the legal states that
contain ONE cell -- the current anchor.

So: `LazyCatalogue.cell_states(anchor)` grows the states containing that anchor with
the SAME orbit growth the solver uses, and caches them per anchor.  Nothing global is
enumerated, so the cost is proportional to what the search actually touches.

The full `Catalogue` stays available as an accelerator for small frames (and for the
regression constants); `LazyCatalogue` is what scales.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, FrozenSet, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grow import grow_states, symmetry_choices
from rules import connected, symmetry_group

Cell = Tuple[int, int]


_LAZY_CACHE: Dict[int, "LazyCatalogue"] = {}


class LazyCatalogue:
    """Legal states of an n x n frame, generated per cell on demand.

    The per-anchor cache is SHARED across instances (module level), so building a second
    Generator for the same size costs nothing.
    """

    def __new__(cls, n: int, *a, **kw):
        if n in _LAZY_CACHE:
            return _LAZY_CACHE[n]
        return super().__new__(cls)

    def __init__(self, n: int, max_cells: Optional[int] = None, budget: int = 2_000_000):
        self.n = n
        self.cells: List[Cell] = [(r, c) for r in range(n) for c in range(n)]
        self._cell_cache: Dict[Cell, List[FrozenSet[Cell]]] = {}
        self._syms = symmetry_choices(n)
        # NO size cap by default: capping the state size would silently remove LEGAL states
        # from the solver's vocabulary (the 4x4 corner has 377 legal shapes, and a cap of
        # half the frame would drop 264 of them).  The search is bounded by a NODE BUDGET
        # instead, and hitting the budget is reported honestly rather than hidden.
        self.max_cells = max_cells
        self.budget = budget
        _LAZY_CACHE[n] = self

    def cell_states(self, anchor: Cell) -> List[FrozenSet[Cell]]:
        """Every legal state that contains `anchor`."""
        if anchor in self._cell_cache:
            return self._cell_cache[anchor]
        out: set = set()
        stats: dict = {}
        for sym in self._syms:
            for st in grow_states(anchor, sym, self.n, max_cells=self.max_cells,
                                  budget=self.budget, stats=stats):
                if stats.get("truncated"):
                    raise RuntimeError(
                        f"state generation for {self.n}x{n} anchor {anchor} hit the node "
                        f"budget ({self.budget}); the state library would be INCOMPLETE. "
                        f"Use a bigger budget, or the hint-driven growth (AODFS).")
                fs = frozenset(st)
                if fs in out:
                    continue
                if not connected(fs):
                    continue
                if not symmetry_group(fs):
                    continue
                out.add(fs)
        res = sorted(out, key=lambda s: (-len(s), sorted(s)))
        self._cell_cache[anchor] = res
        return res

    def stats(self) -> Dict[str, int]:
        return {"anchors_cached": len(self._cell_cache),
                "states_known": sum(len(v) for v in self._cell_cache.values())}


if __name__ == "__main__":
    import time
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    anchors = [(0, 0), (0, 1), (2, 2)]
    lc = LazyCatalogue(n)
    for a in anchors:
        t0 = time.time()
        st = lc.cell_states(a)
        print(f"  anchor {a}: {len(st):,} legal states ({time.time()-t0:.1f}s)   {lc.stats()}")
