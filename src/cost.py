"""Cost field, metric properties and the lemma bank.

Cost model (official text):
  * moving between two orthogonally adjacent squares in the SAME state costs the state size;
  * moving between two different states costs min(sizeA, sizeB);
  * a number in a cell = the least total cost from that cell to ANY state capitol;
  * the answer = sum over rows of (sum of state sizes in that row)^2.

Conventions used here (and only here):
  * `dist(x, y)` is the metric between two cells.
  * `d(x)` is the POTENTIAL (least cost to the nearest capitol).  d is NOT a metric.
  These two are different objects and are kept in different functions on purpose: L2's proof
  uses the triangle inequality of dist, not of d.
"""

from __future__ import annotations

import heapq
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from rules import Cell, State, capitol_of, connected, symmetry_group

INF = float("inf")


class Puzzle:
    """A partition of a grid into states, with its derived quantities."""

    def __init__(self, states: Sequence[Iterable[Cell]]):
        self.states: List[State] = [frozenset(s) for s in states]
        self.h = max((r for s in self.states for (r, _) in s), default=-1) + 1
        self.w = max((c for s in self.states for (_, c) in s), default=-1) + 1
        self.sizes: Dict[int, int] = {i: len(s) for i, s in enumerate(self.states)}
        self.owner: List[List[int]] = [[-1] * self.w for _ in range(self.h)]
        for lab, s in enumerate(self.states):
            for (r, c) in s:
                self.owner[r][c] = lab
        self.capitols: Dict[int, Cell] = {}
        for lab, s in enumerate(self.states):
            cap = capitol_of(s)
            if cap is not None:
                self.capitols[lab] = cap
        self._dist_cache: Dict[Cell, List[List[float]]] = {}

    # ------------------------------------------------------------------ #
    def step_cost(self, a: Cell, b: Cell) -> int:
        """Cost of one orthogonal step between adjacent cells a and b."""
        la, lb = self.owner[a[0]][a[1]], self.owner[b[0]][b[1]]
        if la == lb:
            return self.sizes[la]
        return min(self.sizes[la], self.sizes[lb])

    def neighbours(self, cell: Cell) -> List[Cell]:
        r, c = cell
        out = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.h and 0 <= cc < self.w:
                out.append((rr, cc))
        return out

    def dist(self, src: Cell) -> List[List[float]]:
        """Weighted distance from `src` to every cell (Dijkstra).  dist is a genuine metric."""
        if src in self._dist_cache:
            return self._dist_cache[src]
        d = [[INF] * self.w for _ in range(self.h)]
        d[src[0]][src[1]] = 0
        pq = [(0, src[0], src[1])]
        while pq:
            cur, r, c = heapq.heappop(pq)
            if cur > d[r][c]:
                continue
            for nb in self.neighbours((r, c)):
                w = self.step_cost((r, c), nb)
                if cur + w < d[nb[0]][nb[1]]:
                    d[nb[0]][nb[1]] = cur + w
                    heapq.heappush(pq, (cur + w, nb[0], nb[1]))
        self._dist_cache[src] = d
        return d

    def cost_field(self) -> List[List[float]]:
        """d(x): least cost from x to ANY capitol.  Undefined (inf) if there is no capitol."""
        d = [[INF] * self.w for _ in range(self.h)]
        if not self.capitols:
            return d
        pq = []
        for lab, (r, c) in self.capitols.items():
            d[r][c] = 0
            heapq.heappush(pq, (0, r, c))
        while pq:
            cur, r, c = heapq.heappop(pq)
            if cur > d[r][c]:
                continue
            for nb in self.neighbours((r, c)):
                w = self.step_cost((r, c), nb)
                if cur + w < d[nb[0]][nb[1]]:
                    d[nb[0]][nb[1]] = cur + w
                    heapq.heappush(pq, (cur + w, nb[0], nb[1]))
        return d

    def row_sums(self) -> List[int]:
        """Sum of state sizes in each row."""
        return [sum(self.sizes[self.owner[r][c]] for c in range(self.w)) for r in range(self.h)]

    def answer(self) -> int:
        """sum(row_sums^2)."""
        return sum(s * s for s in self.row_sums())

    def checksum(self) -> Dict[str, int]:
        """The invariant sum(row_sums) == sum(|S|^2) must hold for any partition."""
        return {
            "sum_row_sums": sum(self.row_sums()),
            "sum_state_sizes_squared": sum(v * v for v in self.sizes.values()),
        }

    def has_capitol_at(self, cell: Cell) -> bool:
        return self.capitols.get(self.owner[cell[0]][cell[1]]) == cell


# --------------------------------------------------------------------------- #
# lemma bank  (all verified by brute force over random partitions)
# --------------------------------------------------------------------------- #
def check_L1(puz: Puzzle, d: List[List[float]]) -> List[Tuple[Cell, Cell]]:
    """L1 tight edge: d(x)>0 => there is a neighbour y with d(y) = d(x) - w(x,y)."""
    bad = []
    for r in range(puz.h):
        for c in range(puz.w):
            x = (r, c)
            if d[r][c] in (INF, 0):
                continue
            ok = any(abs(d[y[0]][y[1]] - (d[r][c] - puz.step_cost(x, y))) < 1e-9
                     for y in puz.neighbours(x))
            if not ok:
                bad.append((x, d[r][c]))
    return bad


def check_L2(puz: Puzzle, d: List[List[float]]) -> List[Tuple[Cell, Cell]]:
    """L2: |d(x)-d(y)| <= min(size_x, size_y) for adjacent cells."""
    bad = []
    for r in range(puz.h):
        for c in range(puz.w):
            x = (r, c)
            for y in puz.neighbours(x):
                if d[r][c] == INF or d[y[0]][y[1]] == INF:
                    continue
                lim = min(puz.sizes[puz.owner[r][c]], puz.sizes[puz.owner[y[0]][y[1]]])
                if abs(d[r][c] - d[y[0]][y[1]]) > lim + 1e-9:
                    bad.append((x, y))
    return bad


def check_L3(puz: Puzzle, d: List[List[float]]) -> List[Tuple[Cell, Cell]]:
    """L3: size_x >= |d(x)-d(y)| for ADJACENT y.  (The 'neighbour' qualifier is mandatory:
    the literal 'all y' version is false -- see PLAN D21.)"""
    bad = []
    for r in range(puz.h):
        for c in range(puz.w):
            x = (r, c)
            for y in puz.neighbours(x):
                if d[r][c] == INF or d[y[0]][y[1]] == INF:
                    continue
                if puz.sizes[puz.owner[r][c]] < abs(d[r][c] - d[y[0]][y[1]]) - 1e-9:
                    bad.append((x, y))
    return bad


def check_L5(puz: Puzzle, d: List[List[float]]) -> List[Cell]:
    """L5: d(x) == 0  <=>  x is a capitol."""
    bad = []
    for r in range(puz.h):
        for c in range(puz.w):
            x = (r, c)
            is_cap = d[r][c] == 0
            if is_cap != puz.has_capitol_at(x):
                bad.append(x)
    return bad


def capitol_neighbour_bound(puz: Puzzle, d: List[List[float]], x: Cell) -> Optional[int]:
    """The CORRECT macro-move M2.

    If c is a capitol adjacent to x then  min(size_x, size_c) >= d(x).
    It is a LOWER BOUND, not an equality: the nearest capitol of x may be an UNKNOWN one, so
    the true step cost to a *particular* adjacent capitol can exceed d(x).
    (PLAN D53 / E1.)
    """
    for y in puz.neighbours(x):
        if puz.has_capitol_at(y) and d[x[0]][x[1]] != INF:
            return min(puz.sizes[puz.owner[x[0]][x[1]]], puz.sizes[puz.owner[y[0]][y[1]]])
    return None


def high_d_cells(puz: Puzzle, d: List[List[float]]) -> List[Cell]:
    """Cells whose cost to the nearest capitol is more than half the board: 2*d(x) > N^2.

    These cells cannot be adjacent to a capitol of ANOTHER state (see
    `foreign_capitol_violations`).
    """
    total = puz.h * puz.w
    out = []
    for r in range(puz.h):
        for c in range(puz.w):
            if d[r][c] != INF and 2 * d[r][c] > total:
                out.append((r, c))
    return out


def foreign_capitol_violations(puz: Puzzle, d: List[List[float]]) -> List[Cell]:
    """M4 violations: a high-d cell adjacent to a capitol belonging to ANOTHER state.

    Derivation: for a capitol c in a DIFFERENT state, w(x,c) = min(size_x, size_c) >= d(x),
    and the two states are disjoint, so 2*d(x) <= size_x + size_c <= N^2 -- contradiction.

    NOTE two corrections that adversarial review forced:
      * v1 said "x cannot be adjacent to ANY capitol" -- FALSE: a capitol in x's OWN state is
        possible (that is exactly the surviving case);
      * even the surviving case only implies "x's state covers more than half the board"
        IF x really is adjacent to a capitol -- otherwise the constraint is vacuous.
        (The official 5x5 example shows this: (0,4) has d=17 > 12.5 but sits in a state of
        size 11 and is adjacent to NO capitol at all.)
    """
    out = []
    for x in high_d_cells(puz, d):
        for y in puz.neighbours(x):
            if puz.has_capitol_at(y) and puz.owner[y[0]][y[1]] != puz.owner[x[0]][x[1]]:
                out.append(x)
                break
    return out


def is_metric(puz: Puzzle) -> bool:
    """dist is a genuine metric: symmetric, zero on the diagonal, triangle inequality."""
    for r in range(puz.h):
        for c in range(puz.w):
            src = (r, c)
            D = puz.dist(src)
            for rr in range(puz.h):
                for cc in range(puz.w):
                    back = puz.dist((rr, cc))
                    if abs(D[rr][cc] - back[r][c]) > 1e-9:
                        return False                      # symmetry
            for y in puz.neighbours(src):
                Dy = puz.dist(y)
                for z in puz.neighbours(y):
                    if D[z[0]][z[1]] > D[y[0]][y[1]] + Dy[z[0]][z[1]] + 1e-9:
                        return False                      # triangle inequality
    return True
