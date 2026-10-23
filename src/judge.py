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
from rules import capitol_of
from tilings import Catalogue
from tiletable import answers_for_hints, load_table

Cell = Tuple[int, int]
INF = float("inf")


class Judge:
    """Answers "is the answer unique?" for a given frame size."""

    def __init__(self, n: int, use_table: bool = True):
        self.n = n
        self.cat = Catalogue(n)
        self.by_cell = self.cat.by_cell
        self._cap_of_mask = self.cat._cap_of_mask
        self._cell_of_bit = {}
        for i, c in enumerate(self.cat.cells):
            self._cell_of_bit[1 << i] = c
        # manhattan distance table
        self._manh = [[abs(a[0] - b[0]) + abs(a[1] - b[1]) for b in self.cat.cells]
                      for a in self.cat.cells]
        # the offline table makes every query a scan; the DFS is the fallback
        self._table = load_table(n) if use_table else None
        self.source = "table" if self._table is not None else "search"

    # ------------------------------------------------------------------ #
    def _capitol_of_mask(self, mask: int) -> Optional[Cell]:
        cl = self.cat.cells_of(mask)
        return capitol_of(cl)

    def _path_cost_inside(self, mask: int, src: Cell, dst: Cell) -> Optional[int]:
        """Cheapest path from src to dst staying inside the state `mask`
        (each step inside one state costs the state size).  None if unreachable."""
        S = set(self.cat.cells_of(mask))
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
    def _ub_violates(self, hints: Dict[Cell, int], chosen: Sequence[int]) -> bool:
        """Upper bound: a hinted cell whose own state already reaches a capitol for less
        than its published value cannot be part of a solution."""
        for m in chosen:
            if not self._cap_of_mask.get(m):
                continue
            cap = self._capitol_of_mask(m)
            if cap is None:
                continue
            for (r, c), v in hints.items():
                i = r * self.n + c
                if not (m >> i) & 1:
                    continue
                cost = self._path_cost_inside(m, (r, c), cap)
                if cost is not None and cost < v:
                    return True
        return False

    def _lb_violates(self, hints: Dict[Cell, int], possible: int) -> bool:
        """Lower bound: over the cells that are still POSSIBLE capitols, the closest one
        must be reachable in at least Manh(x, c) steps, each costing >= 1."""
        if possible == 0:
            return True                     # no capitol can exist any more
        for (r, c), v in hints.items():
            row = self._manh[r * self.n + c]
            best = min(row[cc] for cc in range(self.n * self.n) if (possible >> cc) & 1)
            if best > v:
                return True
        return False

    # ------------------------------------------------------------------ #
    def decide(self, hints: Dict[Cell, int], budget: int = 2_000_000) -> Dict[str, object]:
        n = self.n
        if self._table is not None:
            fields, answers = self._table
            ans, count = answers_for_hints(fields, answers, n, hints)
            return {
                "answers": ans,
                "cardinality": len(ans),
                "partitions": count,
                "exhaustive": True,          # the table holds EVERY legal tiling
                "nodes": 0,
                "unique": (len(ans) == 1),
                "source": "table",
            }
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
                puz = Puzzle([self.cat.cells_of(m) for m in chosen])
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
            for m in self.by_cell[first]:
                if m & ~rem:
                    continue
                if self._ub_violates(hints, chosen + [m]):
                    continue
                # cells of this state that are NOT its capitol cannot be capitols
                cap = self._capitol_of_mask(m)
                keep = 0
                for i in range(n * n):
                    if not (m >> i) & 1:
                        continue
                    if cap is not None and self.cat.cells[i] == cap:
                        keep |= 1 << i
                    # a state without a capitol contributes nothing
                new_possible = possible & ~m | keep
                if self._lb_violates(hints, new_possible):
                    continue
                rec(rem ^ m, chosen + [m], new_possible)
                if not exhausted:
                    return

        rec(full, [], all_cells)
        return {
            "answers": sorted(answers),
            "cardinality": len(answers),
            "partitions": partitions,
            "exhaustive": exhausted,
            "nodes": nodes,
            "unique": (exhausted and len(answers) == 1),
            "source": "search",
        }
