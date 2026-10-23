"""AODFS state growth: build a candidate state by adding symmetry ORBITS.

Rules that came out of the adversarial review rounds:

  * A state is grown along the ORBIT of ONE fixed lattice symmetry sigma.  Adding an orbit
    keeps S a union of complete orbits (the sigma-closure invariant).
  * ORBIT ADDITION ALONE DOES NOT GUARANTEE CONNECTEDNESS (PLAN D65).
    Two orbits of the same sigma can be far apart, so after every orbit addition the
    connectivity of S must be re-checked; a disconnected intermediate set invalidates
    that branch.  (The search explores connected orbit-unions only.)
  * At closure the FULL point group decides the capitol (PLAN D55): a state whose chosen
    sigma fixes exactly one cell can still have another symmetry that fixes 0 or >=2 cells,
    in which case it has NO capitol.
  * The modular divisibility conditions are NECESSARY BUT NOT SUFFICIENT (PLAN D63):
    S = {(0,1),(1,0),(2,3),(3,2)} passes the rot90 row of the divisibility table but has no
    rot90 symmetry at all.  Hence every candidate map is verified explicitly against S.
"""


from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))




from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from rules import Cell, State, capitol_of, connected, symmetry_group

CellMask = int


class Symmetry:
    """A lattice symmetry of the square grid.

    The map is a FUNCTION on the whole integer lattice, not a dict over the board: a 90
    degree turn about a centre near the border sends some board cells OFF the board
    (geometrically correct!), and a dict-based map would raise KeyError instead of
    simply failing the "maps the state onto itself" test.
    """

    __slots__ = ("name", "params", "_fn")

    def __init__(self, name: str, params: Tuple, fn):
        self.name = name
        self.params = params
        self._fn = fn

    def apply(self, cell: Cell) -> Cell:
        return self._fn(cell[0], cell[1])

    def orbit(self, cell: Cell) -> FrozenSet[Cell]:
        seen = set()
        cur = cell
        while cur not in seen:
            seen.add(cur)
            cur = self._fn(cur[0], cur[1])
        return frozenset(seen)

    def __repr__(self) -> str:                      # pragma: no cover - debug aid
        return f"Symmetry({self.name}, {self.params})"


def _grid(n: int) -> List[Cell]:
    return [(r, c) for r in range(n) for c in range(n)]


def symmetry_choices(n: int) -> List[Symmetry]:
    """All lattice symmetries of the n x n grid, each with the axis/centre it is anchored at.

    * refH: horizontal line through row i                 (i = 0..n-1)
    * refV: vertical line through column j                (j = 0..n-1)
    * refD1: line r - c = k                               (k = -(n-1) .. n-1)
    * refD2: line r + c = k                               (k = 0 .. 2n-2)
    * rot180: centre (i+0.5, j+0.5)                      (i, j = 0..n-1)  -> cell centres
    * rot90 / rot270: the same centres, the two directions of the quarter turn
    """
    out: List[Symmetry] = []
    # NOTE: a lattice symmetry may have a half-integer axis or centre, and those are NOT
    # optional: the vertical domino {(0,0),(1,0)} has exactly ONE symmetry, a half-turn
    # about (0.5, 0), and a state whose only symmetry is a reflection about r = i+0.5
    # would be unreachable if only integer axes were offered.  So:
    #   refH / refV : axis at k/2 for every integer k
    #   refD1/refD2 : line r-c = k or r+c = k for integer k
    #   rot180      : centre (k1/2, k2/2) for ANY integers k1,k2
    #   rot90/270   : centre (k1/2, k2/2) with k1,k2 of the SAME parity
    for k in range(-n, 2 * n + 1):
        out.append(Symmetry("refH", (k,), lambda r, c, k=k: (k - r, c)))
    for k in range(-n, 2 * n + 1):
        out.append(Symmetry("refV", (k,), lambda r, c, k=k: (r, k - c)))
    for k in range(-(n - 1), n):
        out.append(Symmetry("refD1", (k,), lambda r, c, k=k: (c + k, r - k)))
    for k in range(0, 2 * n - 1):
        out.append(Symmetry("refD2", (k,), lambda r, c, k=k: (k - c, k - r)))
    for k1 in range(-n, 2 * n + 1):
        for k2 in range(-n, 2 * n + 1):
            out.append(Symmetry("rot180", (k1, k2),
                                lambda r, c, k1=k1, k2=k2: (k1 - r, k2 - c)))
    for k1 in range(-n, 2 * n + 1):
        for k2 in range(-n, 2 * n + 1):
            if (k1 - k2) % 2 or (k1 + k2) % 2:
                continue
            # 90 degrees about the centre (k1/2, k2/2):
            #   (r,c) -> (r0 + (c - c0), c0 - (r - r0))  = (c + (k1-k2)/2,  (k1+k2)/2 - r)
            # and the 270 degree turn is its inverse:
            #   (r,c) -> (r0 - (c - c0), c0 + (r - r0))  = ((k1+k2)/2 - c,  r + (k2-k1)/2)
            h = (k1 - k2) // 2
            g = (k1 + k2) // 2
            out.append(Symmetry("rot90", (k1, k2),
                                lambda r, c, h=h, g=g: (c + h, g - r)))
            out.append(Symmetry("rot270", (k1, k2),
                                lambda r, c, h=h, g=g: (g - c, r - h)))
    return out


def orbits_of(sym: Symmetry, n: int) -> Dict[Cell, FrozenSet[Cell]]:
    """Full orbits of `sym` (they may leave the board).

    An orbit that leaves the board cannot be part of a state: the state would not be
    sigma-invariant inside the frame.  The orbits are therefore returned UNTRUNCATED and
    `grow_states` rejects any orbit that is not entirely inside the board.
    """
    cells = _grid(n)
    orb: Dict[Cell, FrozenSet[Cell]] = {}
    for c in cells:
        if c in orb:
            continue
        o = sym.orbit(c)
        for x in o:
            if 0 <= x[0] < n and 0 <= x[1] < n:
                orb[x] = o
    return orb


def grow_states(anchor: Cell, sym: Symmetry, n: int,
                blocked: Iterable[Cell] = (), max_cells: Optional[int] = None,
                budget: Optional[int] = None,
                stats: Optional[dict] = None) -> List[State]:
    """All orbit-unions containing `anchor` that grow along `sym`.

    The returned sets are NOT necessarily connected: connectivity is checked when a state
    is CLOSED (close_state / the callers), because the first orbit of a state can be
    disconnected (the anti-diagonal L-tromino starts from {(0,0),(1,1)}).

    `blocked` = cells that are already taken by other states.
    Intermediate sets that are not connected are pruned (PLAN D65).
    """
    orb = orbits_of(sym, n)
    blocked_set = set(blocked)
    board = {(r, c) for r in range(n) for c in range(n)}

    def inside(o) -> bool:
        return o <= board

    start = orb[anchor]
    if start & blocked_set or not inside(start):
        return []
    results: List[State] = []
    seen = set()

    nodes = [0]

    def expand(mask: frozenset, frontier: Set[Cell]):
        # NOTE: connectivity is NOT required at intermediate steps -- only at closure
        # (close_state).  The first orbit of a state can be disconnected: the
        # anti-diagonal-symmetric L-tromino {(0,0),(0,1),(1,1)} starts from the orbit
        # {(0,0),(1,1)}, which is diagonally separated.  Requiring connectivity at every
        # step (as an earlier draft did) makes such states unreachable.
        # Completeness is instead guaranteed by the frontier being computed from the WHOLE
        # current set, not just the anchor's component.
        nodes[0] += 1
        if budget is not None and nodes[0] > budget:
            if stats is not None:
                stats["truncated"] = True
            return
        if mask in seen:
            return
        seen.add(mask)
        if max_cells is not None and len(mask) > max_cells:
            return
        results.append(mask)
        for x in sorted(frontier):
            o = orb[x]
            if o & blocked_set or (o & mask) or not inside(o):
                continue
            newmask = mask | o
            newfront = {y for y in frontier if y != x}
            for y in newmask:
                for nb in ((y[0] + 1, y[1]), (y[0] - 1, y[1]),
                           (y[0], y[1] + 1), (y[0], y[1] - 1)):
                    if 0 <= nb[0] < n and 0 <= nb[1] < n and nb not in newmask:
                        newfront.add(nb)
            expand(frozenset(newmask), newfront)

    frontier = {nb for x in start for nb in ((x[0] + 1, x[1]), (x[0] - 1, x[1]),
                                          (x[0], x[1] + 1), (x[0], x[1] - 1))
                if 0 <= nb[0] < n and 0 <= nb[1] < n and nb not in start}
    expand(frozenset(start), frontier)
    return results


def close_state(cells: Iterable[Cell]) -> Tuple[bool, Optional[Cell], Tuple[str, ...]]:
    """Close a grown set into a state.

    Returns (is_legal_state, capitol_or_None, symmetry_names).
    The capitol is decided by the FULL point group (PLAN D55), not by the growth symmetry.
    """
    cells = frozenset(cells)
    if not cells or not connected(cells):
        return False, None, ()
    group = symmetry_group(cells)
    if not group:
        return False, None, ()                    # no symmetry at all -> not a state (D55/D63)
    cap = capitol_of(cells)
    return True, cap, tuple(sorted(group))
