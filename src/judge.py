"""Answer-level uniqueness judge (plan section 6.1, DeepSeek B').

`decide(N, hints, budget)` answers the only question that matters for a puzzle:
    do ALL legal tilings consistent with the hints produce the SAME answer?

Points, all earned in review:
  * The judgement is at the ANSWER level, not the partition level: two different
    partitions may share a cost field and still differ in the answer (and two
    partitions may differ while sharing the answer).
  * `unique` is THREE-valued: true only when the search was exhaustive AND the answer
    set has exactly one element.  "I did not find a second answer" is NOT uniqueness.
  * Two SOUND bounds do the pruning:
      UB  if a hinted cell's own state already contains a capitol, the path inside that
         state costs `size * steps`; if that is already below the published value, the
         branch cannot be a solution.
      LB  the nearest capitol of a hinted cell may be UNREVEALED, so a lower bound must
         run over all cells that are still POSSIBLE capitols (cells not yet shown to be
         in a capitol-free state).  If even the closest possible capitol is further away
         than the published value, the branch cannot be a solution.
         (Using only the REVEALLED capitols for this bound is INVALID -- PLAN D53.)
  * The published "Manh to the nearest REVEALLED capitol" bound is therefore never used.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost import Puzzle
from lazycatalogue import LazyCatalogue, TruncatedLibrary
from rules import capitol_of
from tilings import Catalogue
from tiletable import answers_for_hints, load_table

Cell = Tuple[int, int]
INF = float("inf")


class Judge:
    """Answers "is the answer unique?" for a given frame size."""

    def __init__(self, n: int, use_table: bool = True, lazy: Optional[bool] = None):
        self.n = n
        # For n <= 4 the full catalogue is cheap and gives the regression constants.
        # For n >= 5 it is hopeless (2.3M connected subsets at 5x5), so the states are
        # generated per anchor ON DEMAND instead (GLM code review, BLOCKER).
        if lazy is None:
            lazy = n >= 5
        self.lazy = lazy
        if lazy:
            self.cat = LazyCatalogue(n)
            self.by_cell = None
        else:
            self.cat = Catalogue(n)
            self.by_cell = self.cat.by_cell
        # manhattan distance table
        self._manh = [[abs(a[0] - b[0]) + abs(a[1] - b[1]) for b in self.cat.cells]
                      for a in self.cat.cells]
        # per-hint cells ordered by Manhattan distance: the lower-bound check stops at the
        # FIRST still-possible cell instead of scanning the whole bitmask
        self._near: Dict[Cell, List[Tuple[int, int]]] = {}
        # the offline table makes every query a scan; the DFS is the fallback
        self._table = load_table(n) if (use_table and not lazy) else None
        self.source = "table" if self._table is not None else "search"

    # ------------------------------------------------------------------ #
    def _cells_of(self, mask: int) -> List[Cell]:
        """The cells of a state mask (works for both catalogue flavours)."""
        if self.lazy:
            return [(r, c) for r in range(self.n) for c in range(self.n)
                    if (mask >> (r * self.n + c)) & 1]
        return self.cat.cells_of(mask)

    def _mask_of(self, cells) -> int:
        """Bitmask of a cell set (used by the lazy catalogue, which hands back sets)."""
        m = 0
        for (r, c) in cells:
            m |= 1 << (r * self.n + c)
        return m

    def _capitol_of_mask(self, mask: int) -> Optional[Cell]:
        if self.lazy:
            cl = [(r, c) for r in range(self.n) for c in range(self.n)
                  if (mask >> (r * self.n + c)) & 1]
        else:
            cl = self.cat.cells_of(mask)
        return capitol_of(cl)

    def _path_cost_inside(self, mask: int, src: Cell, dst: Cell) -> Optional[int]:
        """Cheapest path from src to dst staying inside the state `mask`
        (each step inside one state costs the state size).  None if unreachable."""
        S = set(self._cells_of(mask))
        size = len(S)
        dist = {src: 0}
        frontier = [src]
        while frontier:
            nxt = []
            for (r, c) in frontier:
                d = dist[(r, c)]
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (r + dr, c + dc)
                    if nb in S and nb not in dist:
                        dist[nb] = d + size
                        nxt.append(nb)
            frontier = nxt
        return dist.get(dst)

    # ------------------------------------------------------------------ #
    def _ub_violates(self, hints: Dict[Cell, int], mask: int) -> bool:
        """Upper bound: a hinted cell whose own state already reaches a capitol for less
        than its published value cannot be part of a solution.

        Only the NEWLY placed state is checked: every older state was checked when it was
        appended, so re-checking them all made each node O(|chosen|).
        """
        cap = self._capitol_of_mask(mask)
        if cap is None:
            return False
        for (r, c), v in hints.items():
            i = r * self.n + c
            if not (mask >> i) & 1:
                continue
            cost = self._path_cost_inside(mask, (r, c), cap)
            if cost is not None and cost < v:
                return True
        return False

    def _lb_violates(self, possible: int) -> bool:
        """The nearest cell that can still be a capitol must be within the published
        distance of every hinted cell.

        The radius is the TIGHT one from the step-count lemma: a hint of value v has its
        nearest capitol within Manhattan distance floor((v+1)/2) -- not v.  Using the
        loose radius made the prune far weaker than the codebase's own proof.
        """
        if possible == 0:
            return True
        for (r, c), v in self._hints_now.items():
            radius = (v + 1) // 2
            best = 1 << 30
            for dist, cc in self._near[(r, c)]:
                if dist > radius:
                    break              # the list is sorted: nothing closer is left
                if (possible >> cc) & 1:
                    best = dist
                    break              # the first hit is the nearest possible capitol
            if best > radius:
                return True
        return False


    # ------------------------------------------------------------------ #
    def decide(self, hints: Dict[Cell, int], budget: int = 2_000_000) -> Dict[str, object]:
        n = self.n
        # the lower-bound check needs, per hint, the cells ordered by Manhattan distance
        self._hints_now = {k: int(v) for k, v in hints.items()}
        self._near = {}
        for (r, c), v in self._hints_now.items():
            row = self._manh[r * self.n + c]
            self._near[(r, c)] = sorted(
                ((row[cc], cc) for cc in range(n * n)), key=lambda t: t[0])
        if self._table is not None:
            fields, answers, n_kept = self._table
            if len(fields) != n_kept:
                # a truncated / tampered cache must never be able to claim exhaustiveness
                print(f"[judge] tiling table for {n}x{n} has {len(fields)} rows but claims "
                      f"{n_kept}; ignoring it")
                self._table = None
            else:
                ans, count = answers_for_hints(fields, answers, n, hints)
                return {
                    "answers": ans,
                    "cardinality": len(ans),
                    "partitions": count,
                    "exhaustive": True,      # the table holds EVERY legal tiling
                    "nodes": 0,
                    "unique": (len(ans) == 1),
                    "source": "table",
                }
        # (the second table block was dead: the first one either returned or cleared
        # self._table.  Only the RETURN was dead -- the initialisation below it is live.)
        full = (1 << (n * n)) - 1
        all_cells = full
        answers: Set[int] = set()
        partitions = 0
        nodes = 0
        exhausted = True

        def rec(rem: int, chosen: List[int], possible: int):
            nonlocal partitions, nodes, exhausted
            if not exhausted:
                return
            nodes += 1
            if nodes > budget:
                exhausted = False
                return
            if rem == 0:
                puz = Puzzle([self._cells_of(m) for m in chosen])
                if not puz.capitols:
                    return
                d = puz.cost_field()
                for (r, c), v in hints.items():
                    if d[r][c] == INF or int(d[r][c]) != v:
                        return
                partitions += 1
                answers.add(puz.answer())
                return
            first = (rem & -rem).bit_length() - 1
            cands = (self.cat.cell_states(self.cat.cells[first]) if self.lazy
                     else self.by_cell[first])
            for m in cands:
                mask_m = m if isinstance(m, int) else self._mask_of(m)
                if mask_m & ~rem:
                    continue
                if self._ub_violates(hints, mask_m):
                    continue
                # cells of this state that are NOT its capitol cannot be capitols
                cap = self._capitol_of_mask(mask_m)
                keep = 0
                for i in range(n * n):
                    if not (mask_m >> i) & 1:
                        continue
                    if cap is not None and self.cat.cells[i] == cap:
                        keep |= 1 << i
                    # a state without a capitol contributes nothing
                new_possible = possible & ~mask_m | keep
                if self._lb_violates(new_possible):
                    continue
                rec(rem ^ mask_m, chosen + [mask_m], new_possible)
                if not exhausted:
                    return

        # a hinted cell with d>0 can never be a capitol (d=0 <=> capitol): drop it from
        # the pool of possible capitols right away (free, sound strengthening)
        start_possible = all_cells
        for (r, c), v in hints.items():
            if v > 0:
                start_possible &= ~(1 << (r * n + c))
        try:
            rec(full, [], start_possible)
        except TruncatedLibrary as exc:
            # the state library was incomplete: the verdict must be "unknown", never a
            # silent success and never a crash (GLM code review M2)
            print(f"[judge] {exc}")
            exhausted = False
        return {
            "answers": sorted(answers),
            "cardinality": len(answers),
            "partitions": partitions,
            "exhaustive": exhausted,
            "nodes": nodes,
            "unique": (exhausted and len(answers) == 1),
            "source": "search",
        }
