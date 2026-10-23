"""Rule kernel for the Jane Street state/capitol puzzle family.

THIS IS THE EXECUTABLE SPECIFICATION.  Every truth table, fixture and regression constant in
this repository is produced by it or checked against it.

Design rules that must not be violated (each one was a real bug found by an adversarial review):

1. NO FLOATING POINT.
   The official example's 3-cell state has centroid (5/3, 8/3).  In IEEE754 double precision
   rbar - cbar = -0.9999999999999998, the reflection test fails, the state is declared
   asymmetric, its capitol silently disappears, and every published number changes.
   All divisibility conditions are therefore integer congruences on (sum_r, sum_c, n).

2. The capitol rule quantifies over the FULL point group of the state, not over one symmetry.
   A state whose chosen symmetry fixes exactly one cell can still have a second symmetry that
   fixes 0 or >=2 cells -- such a state has NO capitol.  (1x3 bar: the vertical reflection
   fixes the middle cell, but the horizontal reflection fixes all three -> no capitol.)

3. A shape with no non-trivial self-symmetry is NOT a state.
   It is not a "capitol-less state"; it is not a state at all.  (The L-tetromino is the
   canonical example: it has no symmetry whatsoever.)

4. A state with no capitol is still a legal state, but a partition in which NO state has a
   capitol has no cost field at all (d is undefined) and therefore is not a solution.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

Cell = Tuple[int, int]
State = FrozenSet[Cell]

# canonical names of the seven non-identity lattice symmetries
REF_D1 = "refD1"   # reflection in a line of slope +1 (r - c = const)
REF_D2 = "refD2"   # reflection in a line of slope -1 (r + c = const)
REF_H = "refH"     # reflection in a horizontal line
REF_V = "refV"     # reflection in a vertical line
ROT_180 = "rot180"
ROT_90 = "rot90"
ROT_270 = "rot270"

NON_IDENTITY = (REF_D1, REF_D2, REF_H, REF_V, ROT_180, ROT_90, ROT_270)


# --------------------------------------------------------------------------- #
# basic geometry
# --------------------------------------------------------------------------- #
def connected(cells: Iterable[Cell]) -> bool:
    """4-connected?  (diagonal neighbours do not count)"""
    S = set(cells)
    if not S:
        return False
    start = next(iter(S))
    seen = {start}
    stack = [start]
    while stack:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if nb in S and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return len(seen) == len(S)


def _neighbours(cell: Cell) -> List[Cell]:
    r, c = cell
    return [(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))]


# --------------------------------------------------------------------------- #
# symmetry group
# --------------------------------------------------------------------------- #
def symmetry_group(cells: Iterable[Cell]) -> Dict[str, FrozenSet[Cell]]:
    """The full lattice symmetry group of `cells`, mapped to the cells each element fixes.

    Only the 8 lattice symmetries can preserve a union of axis-aligned unit squares
    (the boundary direction set {0deg, 90deg} must map to itself).  Each candidate is
    admitted only if it maps the cell set ONTO ITSELF.  The identity is not included.

    All arithmetic is integer arithmetic on (sum_r, sum_c, n) -- never on a float centroid.
    """
    cells = frozenset(cells)
    n = len(cells)
    if n == 0:
        return {}
    sr = sum(r for r, _ in cells)
    sc = sum(c for _, c in cells)
    S = set(cells)
    candidates: List[Tuple[str, object]] = []

    # reflection in a line r - c = k1
    if (sr - sc) % n == 0:
        k1 = (sr - sc) // n
        candidates.append((REF_D1, lambda r, c, k=k1: (c + k, r - k)))
    # reflection in a line r + c = k2
    if (sr + sc) % n == 0:
        k2 = (sr + sc) // n
        candidates.append((REF_D2, lambda r, c, k=k2: (k - c, k - r)))
    # reflection in a horizontal line
    if (2 * sr) % n == 0:
        a = (2 * sr) // n
        candidates.append((REF_H, lambda r, c, a=a: (a - r, c)))
    # reflection in a vertical line
    if (2 * sc) % n == 0:
        b = (2 * sc) // n
        candidates.append((REF_V, lambda r, c, b=b: (r, b - c)))
    # 180 degree rotation
    if (2 * sr) % n == 0 and (2 * sc) % n == 0:
        a, b = (2 * sr) // n, (2 * sc) // n
        candidates.append((ROT_180, lambda r, c, a=a, b=b: (a - r, b - c)))
    # 90 / 270 degree rotations
    if (sr - sc) % n == 0 and (sr + sc) % n == 0:
        k1 = (sr - sc) // n
        k2 = (sr + sc) // n
        candidates.append((ROT_90, lambda r, c, k1=k1, k2=k2: (c + k1, k2 - r)))
        candidates.append((ROT_270, lambda r, c, k1=k1, k2=k2: (k2 - c, r - k1)))

    group: Dict[str, FrozenSet[Cell]] = {}
    for name, fn in candidates:
        image = {fn(r, c) for (r, c) in S}
        if image != S:
            continue                      # the map does not preserve the state
        group[name] = frozenset((r, c) for (r, c) in S if fn(r, c) == (r, c))
    return group


def is_legal_state(cells: Iterable[Cell]) -> bool:
    """A legal state is 4-connected and has at least one non-trivial self-symmetry."""
    cells = frozenset(cells)
    if not cells or not connected(cells):
        return False
    return bool(symmetry_group(cells))


def capitol_of(cells: Iterable[Cell]) -> Optional[Cell]:
    """The capitol of a state, or None.

    Rule (official text): if EVERY non-trivial rotation or reflection that takes the state to
    itself leaves EXACTLY ONE of its squares fixed, then that square is its capitol.
    Otherwise the state has no capitol.
    """
    cells = frozenset(cells)
    group = symmetry_group(cells)
    if not group:
        return None
    fixed = [fs for fs in group.values()]
    if not all(len(fs) == 1 for fs in fixed):
        return None
    # if every non-identity element fixes exactly one cell, they fix the SAME cell
    unique = {next(iter(fs)) for fs in fixed}
    if len(unique) != 1:
        return None
    return unique.pop()


def state_size(cells: Iterable[Cell]) -> int:
    return len(set(cells))


def is_capitol_bearing(cells: Iterable[Cell]) -> bool:
    """True if this state has a capitol (i.e. it can be a destination)."""
    return capitol_of(cells) is not None


def partition_of(labels: Sequence[Sequence[int]]) -> List[State]:
    """Turn a label matrix into a list of states, indexed by POSITION.

    Labels need not be contiguous: the returned list is ordered by sorted label, so a
    matrix labelled 0,2 yields states[0] = label 0 and states[1] = label 2.  Downstream
    code re-indexes by position anyway (Puzzle enumerates the states it is given).
    """
    buckets: Dict[int, set] = {}
    for r, row in enumerate(labels):
        for c, lab in enumerate(row):
            buckets.setdefault(lab, set()).add((r, c))
    return [frozenset(v) for _, v in sorted(buckets.items())]


def label_matrix(states: Sequence[Iterable[Cell]]) -> List[List[int]]:
    """Inverse of partition_of: build a label matrix from a list of states."""
    h = max((r for s in states for (r, _) in s), default=-1) + 1
    w = max((c for s in states for (_, c) in s), default=-1) + 1
    out = [[-1] * w for _ in range(h)]
    for lab, s in enumerate(states):
        for (r, c) in s:
            out[r][c] = lab
    return out


def shape_key(cells: Iterable[Cell]) -> Tuple[Cell, ...]:
    """Canonical key of a shape up to translation (for shape-type catalogues)."""
    cells = sorted(set(cells))
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))
