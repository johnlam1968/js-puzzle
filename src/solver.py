"""Readings-driven AODFS solver: the tiling is GROWN, not enumerated.

Architecture (this is what makes it scale past 4x4):

  * one DFS over (partial tiling x partial state).  There is no separate "list of
    candidate states" step -- a state's growth IS a branch of the search, so nothing is
    ever generated twice;
  * the anchor of the state being grown is the most constrained HINTED cell, so the
    published numbers bite immediately;
  * while a state grows, the LOWER BOUND prune runs: the nearest cell that can still be
    a capitol must be within the published distance of every hinted cell.  Only cells
    that are still POSSIBLE capitols count -- using only the revealed capitols here
    would be unsound (PLAN D53);
  * when a state is closed, the UPPER BOUND prune runs: if a hinted cell inside it
    already reaches a capitol for less than its published value, the branch dies;
  * a completed tiling is verified exactly against every published number.

The verdict is three-valued: `unique` is true only when the search was EXHAUSTIVE and
the answer set has exactly one element.  "I did not find a second answer" is not
uniqueness -- and in this puzzle family it really happens (two partitions may share a
cost field but differ in the answer).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost import Puzzle
from grow import Symmetry, orbits_of, symmetry_choices
from rules import capitol_of, connected, symmetry_group

Cell = Tuple[int, int]
INF = float("inf")


class Solver:
    """Solve a puzzle from its published numbers."""

    def __init__(self, n: int, hints: Dict[Cell, int], budget: int = 2_000_000,
                 report_every: int = 0):
        self.n = n
        self.hints = {k: int(v) for k, v in hints.items()}
        self.budget = budget
        self.report_every = report_every
        self.cells: List[Cell] = [(r, c) for r in range(n) for c in range(n)]
        self.idx = {c: i for i, c in enumerate(self.cells)}
        self._syms = symmetry_choices(n)
        self._orb_cache: Dict[int, Dict[Cell, FrozenSet[Cell]]] = {}
        self._fixed_cache: Dict[int, FrozenSet[Cell]] = {}
        # per symmetry: the mask of every cell's orbit, and the cells whose orbit lies
        # fully on the board.  These are static (the board never changes), so the two
        # per-node orbit checks become O(1) integer tests instead of two set scans.
        self._orbdata_cache: Dict[int, Tuple[Dict[Cell, FrozenSet[Cell]],
                                             Dict[Cell, int], FrozenSet[Cell]]] = {}
        # per state mask: (has a non-trivial symmetry, capitol or None).  ONE symmetry
        # group computation per state instead of two (capitol_of used to recompute it).
        self._state_cache: Dict[int, Tuple[bool, Optional[Cell]]] = {}
        # per anchor: the symmetries that can grow a state containing it
        self._anchor_cache: Dict[Cell, list] = {}
        self.answers: Set[int] = set()
        self.solutions: List[List[FrozenSet[Cell]]] = []
        self.nodes = 0
        self.exhaustive = True
        self._manh = [[abs(a[0] - b[0]) + abs(a[1] - b[1]) for b in self.cells]
                      for a in self.cells]
        # per-hint cells ordered by Manhattan distance: the lower-bound check stops at the
        # FIRST still-possible cell instead of scanning the whole bitmask (the scan was
        # ~33 hints x 90 cells per node and dominated the runtime on the 11x11)
        # L3/L2 area lower bound: for two ADJACENT hinted cells x and y the step between
        # them costs w = min(size_x, size_y), and |d(x) - d(y)| <= w (the path x -> y ->
        # y's nearest capitol is a valid path from x), so the state holding x has area
        # >= |D(x) - D(y)|.  The published numbers are the exact d values, so the bound is
        # sound for the solver's contract.
        self._need: Dict[Cell, int] = {}
        for (r, c), v in self.hints.items():
            best = 0
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (r + dr, c + dc)
                if nb in self.hints:
                    best = max(best, abs(v - self.hints[nb]))
            self._need[(r, c)] = best
        self._near: Dict[Cell, List[Tuple[int, int]]] = {}
        for (r, c), v in self.hints.items():
            row = self._manh[r * self.n + c]
            self._near[(r, c)] = sorted(
                ((row[cc], cc) for cc in range(self.n * self.n)), key=lambda t: t[0])

    # ------------------------------------------------------------------ #
    def _orbits(self, sym: Symmetry) -> Dict[Cell, FrozenSet[Cell]]:
        k = id(sym)
        if k not in self._orb_cache:
            self._orb_cache[k] = orbits_of(sym, self.n)
        return self._orb_cache[k]

    def _fixed(self, sym: Symmetry) -> FrozenSet[Cell]:
        k = id(sym)
        if k not in self._fixed_cache:
            self._fixed_cache[k] = sym.fixed_points(self.n)
        return self._fixed_cache[k]

    def _orbitdata(self, sym: Symmetry):
        """(orbits, orbit masks, on-board cells) for one symmetry -- computed once.

        Only 261-287 of the 2,422 symmetries of an 11x11 board have their orbit fully
        inside the board for a given anchor, so the previous "does the orbit leave the
        board?" scan was rejecting ~89% of the branches one cell at a time.
        """
        k = id(sym)
        d = self._orbdata_cache.get(k)
        if d is None:
            orb = self._orbits(sym)
            masks: Dict[Cell, int] = {}
            onboard = set()
            for cell, o in orb.items():
                if any(c not in self.idx for c in o):
                    continue
                m = 0
                for c in o:
                    m |= 1 << self.idx[c]
                masks[cell] = m
                onboard.add(cell)
            d = (orb, masks, frozenset(onboard))
            self._orbdata_cache[k] = d
        return d

    def _anchor_syms(self, anchor: Cell):
        """The symmetries that can grow a state containing `anchor`, with their orbit data.

        Static per anchor: the board never changes, so this is computed once per anchor
        and reused.  For a given anchor only a small fraction of the lattice symmetries
        have their orbit fully on the board (on the 11x11: 261-287 of 2,422), and the
        old code discovered that one cell at a time, inside the search.
        """
        hit = self._anchor_cache.get(anchor)
        if hit is None:
            out = []
            for sym in self._syms:
                orb, omask, onboard = self._orbitdata(sym)
                if anchor in onboard:
                    out.append((sym, orb, omask, self._fixed(sym)))
            hit = out
            self._anchor_cache[anchor] = hit
        return hit

    def _state_info(self, cur_mask: int, cur: FrozenSet[Cell]) -> Tuple[bool, Optional[Cell]]:
        """(has a non-trivial symmetry, capitol) for a state -- ONE group computation.

        The rules module computed the symmetry group twice per state: once for the
        legality test and once inside capitol_of.  The capitol is derived from the very
        same group here, and the result is cached by the state's mask, so a state that
        shows up in several branches is computed once.
        """
        hit = self._state_cache.get(cur_mask)
        if hit is not None:
            return hit
        group = symmetry_group(cur)
        cap: Optional[Cell] = None
        if group:
            # only an ODD-sized state can carry a capitol: a symmetry that fixes exactly
            # one cell pairs up all the others, so the area is odd (PLAN D43)
            if len(cur) % 2 == 1:
                fixed = list(group.values())
                if all(len(fs) == 1 for fs in fixed):
                    unique = {next(iter(fs)) for fs in fixed}
                    if len(unique) == 1:
                        cap = unique.pop()
        hit = (bool(group), cap)
        self._state_cache[cur_mask] = hit
        return hit

    # ------------------------------------------------------------------ #
    def _lb_violates(self, possible: int) -> bool:
        """The nearest cell that can still be a capitol must be within the published
        distance of every hinted cell.

        The radius is the TIGHT one from the step-count lemma: a hint of value v has its
        nearest capitol within Manhattan distance floor((v+1)/2) -- not v.  Using the
        loose radius made the prune far weaker than the codebase's own proof.
        """
        if possible == 0:
            return True
        for (r, c), v in self.hints.items():
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

    def _ub_violates(self, state: FrozenSet[Cell], cap: Cell) -> bool:
        """The state is already cheaper than a published number: the branch is dead.

        One BFS from the capitol gives the step count to every cell of the state; the
        cost of a path is (steps x state size), because every step enters the state.
        The old code ran a separate BFS per hinted cell of the state.
        """
        size = len(state)
        dist = {cap: 0}
        frontier = [cap]
        while frontier:
            nxt = []
            for (r, c) in frontier:
                d = dist[(r, c)] + 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (r + dr, c + dc)
                    if nb in state and nb not in dist:
                        dist[nb] = d
                        nxt.append(nb)
            frontier = nxt
        for (r, c), v in self.hints.items():
            if (r, c) not in state:
                continue
            steps = dist.get((r, c))
            if steps is not None and steps * size < v:
                return True
        return False

    def _path_cost(self, state: FrozenSet[Cell], src: Cell, dst: Cell, size: int):
        if src == dst:
            return 0
        dist = {src: 0}
        frontier = [src]
        while frontier:
            nxt = []
            for (r, c) in frontier:
                d = dist[(r, c)]
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (r + dr, c + dc)
                    if nb in state and nb not in dist:
                        dist[nb] = d + size
                        nxt.append(nb)
            frontier = nxt
        return dist.get(dst)

    # ------------------------------------------------------------------ #
    def _pick_anchor(self, rem: int) -> Cell:
        """Prefer a hinted cell, the tightest one first (smallest published value)."""
        best = None
        for (r, c), v in self.hints.items():
            i = r * self.n + c
            if not (rem >> i) & 1:
                continue
            if best is None or v < self.hints[best]:
                best = (r, c)
        if best is not None:
            return best
        return self.cells[(rem & -rem).bit_length() - 1]

    def _mask(self, cells: Iterable[Cell]) -> int:
        m = 0
        for (r, c) in cells:
            m |= 1 << (r * self.n + c)
        return m

    # ------------------------------------------------------------------ #
    def solve(self) -> Dict[str, object]:
        full = (1 << (self.n * self.n)) - 1
        t0 = time.time()

        def rec(rem: int, chosen: List[FrozenSet[Cell]],
                cur: Optional[FrozenSet[Cell]], sym: Optional[Symmetry],
                possible: int, closed_here: Set[FrozenSet[Cell]],
                grown_here: Set[int],
                orb: Optional[Dict[Cell, FrozenSet[Cell]]] = None,
                omask: Optional[Dict[Cell, int]] = None,
                fixed: Optional[FrozenSet[Cell]] = None):
            """Grow one state at a time; when it is closed, start the next one."""
            if not self.exhaustive:
                return
            self.nodes += 1
            if self.nodes > self.budget:
                self.exhaustive = False
                return
            if self.report_every and self.nodes % self.report_every == 0:
                print(f"    ... {self.nodes:,} nodes, {len(self.answers)} answers, "
                      f"{time.time()-t0:.0f}s", flush=True)

            if cur is None:
                # start a new state at the anchor, trying every symmetry
                if rem == 0:
                    self._complete(chosen)
                    return
                anchor = self._pick_anchor(rem)
                # A d=0 anchor is a CAPITOL: the symmetry we grow the state with must fix
                # it, so most symmetries are impossible from the start.  This is the single
                # biggest pruning win on a big frame (150 candidate symmetries -> ~8).
                must_fix = self.hints.get(anchor) == 0
                # one set per ANCHOR: a state with k symmetries is reachable under each of
                # them, so without this the same subtree is explored k times (M1)
                closed_here: Set[FrozenSet[Cell]] = set()
                for s, orb, omask, fixed in self._anchor_syms(anchor):
                    if must_fix and anchor not in fixed:
                        continue
                    start = orb[anchor]
                    start_mask = omask[anchor]
                    if start_mask & ~rem:
                        continue                     # the orbit hits cells already taken
                    np = possible
                    for c in start:
                        if c not in fixed:
                            np &= ~(1 << self.idx[c])
                    for c in fixed:
                        if c in start:
                            np |= 1 << self.idx[c]
                    if self._lb_violates(np):
                        continue
                    rec(rem & ~start_mask, chosen, frozenset(start), s, np,
                        closed_here, set(), orb, omask, fixed)
                    if not self.exhaustive:
                        return
                return

            # a state is being grown: close it, or extend it by one orbit
            # The same partial state can be reached by adding the same orbits in different
            # orders; the subtree below it is IDENTICAL (it depends only on the state, the
            # symmetry and the remaining cells), so the second visit is dead work
            # (GLM code review, MAJOR 2).
            cur_mask = self._mask(cur)
            if cur_mask in grown_here:
                return
            grown_here.add(cur_mask)
            already_closed = cur in closed_here
            if self._can_close(cur, cur_mask) and not already_closed:
                closed_here.add(cur)
                cap = self._state_info(cur_mask, cur)[1]
                np = possible
                for c in cur:
                    if c != cap:
                        np &= ~(1 << self.idx[c])
                if cap is not None:
                    np |= 1 << self.idx[cap]
                if not self._lb_violates(np):
                    rec(rem & ~cur_mask, chosen + [cur], None, None, np, set(), set())
                    if not self.exhaustive:
                        return
            frontier = {nb for x in cur for nb in ((x[0] + 1, x[1]), (x[0] - 1, x[1]),
                                                  (x[0], x[1] + 1), (x[0], x[1] - 1))
                        if 0 <= nb[0] < self.n and 0 <= nb[1] < self.n and nb not in cur}
            for x in sorted(frontier):
                o_mask = omask.get(x)
                if o_mask is None:
                    continue                         # the orbit leaves the board
                if o_mask & cur_mask:
                    continue                         # overlaps the state already grown
                if o_mask & ~rem:
                    continue                         # the orbit hits cells already taken
                o = orb[x]
                newcur = cur | o
                np = possible
                for c in o:
                    if c not in fixed:
                        np &= ~(1 << self.idx[c])
                for c in fixed:
                    if c in newcur:
                        np |= 1 << self.idx[c]
                if self._lb_violates(np):
                    continue
                # the new orbit's cells leave the remaining region as well
                rec(rem & ~o_mask, chosen, frozenset(newcur), sym, np,
                    closed_here, grown_here, orb, omask, fixed)
                if not self.exhaustive:
                    return

        # a hinted cell with d>0 can never be a capitol (d=0 <=> capitol), so it leaves
        # the pool of possible capitols right away (a free, sound strengthening)
        start_possible = full
        for (r, c), v in self.hints.items():
            if v > 0:
                start_possible &= ~(1 << self.idx[(r, c)])
        rec(full, [], None, None, start_possible, set(), set())
        return {
            "answers": sorted(self.answers),
            "cardinality": len(self.answers),
            "partitions": len(self.solutions),
            "exhaustive": self.exhaustive,
            "nodes": self.nodes,
            "unique": (self.exhaustive and len(self.answers) == 1),
            "seconds": time.time() - t0,
            "solutions": [[sorted(s) for s in p] for p in self.solutions[:5]],
        }

    def _can_close(self, cur: FrozenSet[Cell], cur_mask: int) -> bool:
        if not connected(cur):
            return False
        # the state must be big enough to carry the difference of its hinted neighbours
        need = 0
        for c in cur:
            nb = self._need.get(c)
            if nb is not None and nb > need:
                need = nb
        if len(cur) < need:
            return False
        has_group, cap = self._state_info(cur_mask, cur)
        if not has_group:
            return False                     # no symmetry -> not a state at all
        if cap is not None and self._ub_violates(cur, cap):
            return False
        return True

    def _complete(self, chosen: List[FrozenSet[Cell]]):
        puz = Puzzle(chosen)
        if not puz.capitols:
            return
        d = puz.cost_field()
        for (r, c), v in self.hints.items():
            if d[r][c] == INF or int(d[r][c]) != v:
                return
        self.solutions.append(chosen)
        self.answers.add(puz.answer())


def solve_grid(n: int, hints: Dict[Cell, int], budget: int = 2_000_000,
               report_every: int = 0):
    return Solver(n, hints, budget=budget, report_every=report_every).solve()


if __name__ == "__main__":
    import json
    path = sys.argv[1]
    p = json.load(open(path))
    n = p["size"]
    hints = {(h["row"], h["col"]): h["value"] for h in p["hints"]}
    # The hint coordinates are 0-based (data/schema/puzzle.schema.json).  A file that
    # uses another base used to blow up as "IndexError: list index out of range" deep
    # inside the Manhattan table; a clean error is much easier to act on.
    bad = [c for c in hints if not (0 <= c[0] < n and 0 <= c[1] < n)]
    if bad:
        raise SystemExit(
            f"{path}: {len(bad)} hint(s) are outside the {n}x{n} board, e.g. {bad[0]}. "
            f"Hint coordinates must be 0-based (row 0..{n-1}, col 0..{n-1}); "
            f"this file looks 1-based -- shift every hint by -1 before using it.")
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 2_000_000
    res = solve_grid(n, hints, budget, report_every=200000)
    print(json.dumps({k: v for k, v in res.items() if k != "solutions"}, indent=1))
