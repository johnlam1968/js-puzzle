"""Rule kernel for Jane Street's "It's a Metric, Too" (October 2026).

Written from the OFFICIAL rules text (fetched 2026-10-24 from
https://www.janestreet.com/puzzles/current-puzzle/), not from any existing
implementation in the js-puzzle repository.  The repository's `src/rules.py` is
used afterwards as an independent oracle in `selftest.py` (differential test).

Official wording -> code
------------------------
R1  "A 'state' is a connected group of 1 or more squares that is symmetric in
     some way, be it via rotation or reflection."
        -> `is_legal_state`: 4-connected AND has >= 1 non-trivial self-symmetry.
           A shape with NO non-trivial self-symmetry is NOT A STATE AT ALL
           (the L-tetromino is the canonical example).

R2  "If every nontrivial rotation or reflection of the plane that takes a state
     to itself leaves exactly 1 of its squares fixed, then that square is its
     capitol."
        -> `capitol_of`: quantify over the FULL symmetry group, not one symmetry.
           If ANY non-trivial self-symmetry fixes a number of cells other than
           exactly one, the state has NO capitol.  (1x3 bar: the vertical
           reflection fixes the middle cell but the horizontal reflection fixes
           all three -> no capitol.)

R3  "The cost of traveling from one square to an orthogonally adjacent square
     ... is equal to the size of the state you are travelling in, or, if
     travelling between two states, the lesser of the two states' sizes."
        -> cost(x,y) = min(size(state(x)), size(state(y))).  Inside one state
           both terms are that state's size, so the single formula covers both.

R4  "A number in a cell denotes the lowest cost of travelling from the numbered
     square to any state capitol."
        -> `cost_field`: Dijkstra from the set of capitols with edge weight
           min(size_x, size_y).

R5  "label each cell with the size of the state it is in.  Compute the sum of
     these values in each row, and submit as your answer the sum of the squares
     of these row sums."
        -> `row_sums` + `answer`.

Arithmetic is integer-only throughout: no floating point, because a float
centroid silently loses a symmetry and changes every published number.
"""

from __future__ import annotations

from heapq import heappop, heappush
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

Cell = Tuple[int, int]
State = FrozenSet[Cell]

# canonical names of the seven non-identity lattice symmetries
REF_D1 = "refD1"   # reflection in a line of slope +1
REF_D2 = "refD2"   # reflection in a line of slope -1
REF_H = "refH"     # reflection in a horizontal line
REF_V = "refV"     # reflection in a vertical line
ROT_180 = "rot180"
ROT_90 = "rot90"
ROT_270 = "rot270"

NON_IDENTITY = (REF_D1, REF_D2, REF_H, REF_V, ROT_180, ROT_90, ROT_270)

ORTHO = ((-1, 0), (1, 0), (0, -1), (0, 1))


# --------------------------------------------------------------------------- #
# connectivity
# --------------------------------------------------------------------------- #
def connected(cells: Iterable[Cell]) -> bool:
    """4-connected?  Diagonal neighbours do not count."""
    S = set(cells)
    if not S:
        return False
    start = next(iter(S))
    seen = {start}
    stack = [start]
    while stack:
        r, c = stack.pop()
        for dr, dc in ORTHO:
            nb = (r + dr, c + dc)
            if nb in S and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return len(seen) == len(S)


def neighbours(cell: Cell) -> List[Cell]:
    r, c = cell
    return [(r + dr, c + dc) for dr, dc in ORTHO]


def components(labels: Sequence[Sequence[int]], n: int) -> List[List[Cell]]:
    """Connected components of equal labels.  Label -1 means 'unassigned'."""
    seen = [[False] * n for _ in range(n)]
    out: List[List[Cell]] = []
    for r in range(n):
        for c in range(n):
            lab = labels[r][c]
            if lab < 0 or seen[r][c]:
                continue
            cells: List[Cell] = []
            stack = [(r, c)]
            seen[r][c] = True
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for dx, dy in ORTHO:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < n and 0 <= ny < n and not seen[nx][ny] and labels[nx][ny] == lab:
                        seen[nx][ny] = True
                        stack.append((nx, ny))
            out.append(cells)
    return out


# --------------------------------------------------------------------------- #
# symmetry group
# --------------------------------------------------------------------------- #
def _bbox(cells: Sequence[Cell]) -> Tuple[int, int, int, int]:
    r0 = min(r for r, _ in cells)
    r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    c1 = max(c for _, c in cells)
    return r0, r1, c0, c1


def symmetry_group(cells: Iterable[Cell]) -> Dict[str, FrozenSet[Cell]]:
    """Full lattice symmetry group of `cells`, mapped to the cells each element fixes.

    Only the eight lattice symmetries can preserve a union of axis-aligned unit
    squares: the boundary direction set {0 deg, 90 deg} must map to itself, so
    the angle must be a multiple of 90 deg, and the axis/centre must be a
    lattice line/point that maps the bounding box onto itself.

    Every candidate is therefore determined by the bounding box, and it is
    admitted only when it maps the cell set ONTO ITSELF.  The identity is not
    included.

    All arithmetic is integer arithmetic; no float centroid is ever formed.
    """
    cells = frozenset(cells)
    if not cells:
        return {}
    r0, r1, c0, c1 = _bbox(cells)
    q = r0 + r1          # horizontal mirror:  r -> q - r
    p = c0 + c1          # vertical mirror:    c -> p - c
    square = (r1 - r0) == (c1 - c0)

    candidates: List[Tuple[str, object]] = [
        (REF_V,   lambda r, c: (r, p - c)),
        (REF_H,   lambda r, c: (q - r, c)),
        (ROT_180, lambda r, c: (q - r, p - c)),
    ]
    if square:
        k1 = r0 - c0                      # line  r - c = k1
        k2 = r0 + c1                      # line  r + c = k2
        candidates.append((REF_D1, lambda r, c, k=k1: (c + k, r - k)))
        candidates.append((REF_D2, lambda r, c, k=k2: (k - c, k - r)))
        if (p + q) % 2 == 0:              # the 4-fold centre is a lattice point
            m = (p + q) // 2
            h = (q - p) // 2
            candidates.append((ROT_90,  lambda r, c: (c + h, m - r)))
            candidates.append((ROT_270, lambda r, c: (m - c, r - h)))

    group: Dict[str, FrozenSet[Cell]] = {}
    for name, fn in candidates:
        image = {(fn(r, c)) for (r, c) in cells}   # type: ignore[operator]
        if image != set(cells):
            continue
        group[name] = frozenset((r, c) for (r, c) in cells if fn(r, c) == (r, c))  # type: ignore[operator]
    return group


def is_legal_state(cells: Iterable[Cell]) -> bool:
    """A legal state is 4-connected and has at least one non-trivial self-symmetry."""
    cells = frozenset(cells)
    if not cells or not connected(cells):
        return False
    return bool(symmetry_group(cells))


def capitol_of(cells: Iterable[Cell]) -> Optional[Cell]:
    """The capitol of a state, or None.

    Rule R2: the capitol exists iff EVERY non-trivial self-symmetry fixes
    exactly one cell -- and all of them fix the SAME cell.
    """
    cells = frozenset(cells)
    group = symmetry_group(cells)
    if not group:
        return None
    fixed = [fs for fs in group.values()]
    if not all(len(fs) == 1 for fs in fixed):
        return None
    unique = {next(iter(fs)) for fs in fixed}
    if len(unique) != 1:
        return None
    return unique.pop()


def has_capitol(cells: Iterable[Cell]) -> bool:
    return capitol_of(cells) is not None


# --------------------------------------------------------------------------- #
# cost field and answer
# --------------------------------------------------------------------------- #
def cost_field(sizes: Sequence[int], n: int, capitols: Iterable[Cell]) -> List[List[Optional[int]]]:
    """Least cost from every cell to ANY capitol (rule R4).

    `sizes[r][c]` is the size of the state the cell belongs to; `capitols` is
    the set of capitol cells.  Unreachable cells get None.
    """
    INF = float("inf")
    dist = [[INF] * n for _ in range(n)]
    pq: List[Tuple[int, int, int]] = []
    for (r, c) in capitols:
        dist[r][c] = 0
        heappush(pq, (0, r, c))
    while pq:
        d, r, c = heappop(pq)
        if d > dist[r][c]:
            continue
        for dr, dc in ORTHO:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < n and 0 <= nc < n):
                continue
            nd = d + min(sizes[r][c], sizes[nr][nc])
            if nd < dist[nr][nc]:
                dist[nr][nc] = nd
                heappush(pq, (nd, nr, nc))
    return [[None if v == INF else int(v) for v in row] for row in dist]


def row_sums(sizes: Sequence[int], n: int) -> List[int]:
    """Row sums: for each row, the sum of the SIZES of the states occupying it."""
    return [sum(sizes[r][c] for c in range(n)) for r in range(n)]


def answer(row_sum: Sequence[int]) -> int:
    return sum(v * v for v in row_sum)


def state_sizes_from_labels(labels: Sequence[Sequence[int]], n: int) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for r in range(n):
        for c in range(n):
            lab = labels[r][c]
            if lab >= 0:
                out[lab] = out.get(lab, 0) + 1
    return out
