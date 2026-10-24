"""Tools for the lower-right corner of the official 11x11.

TOOL 3  `grow_states`      -- enumerate every legal state of a given size that
                              contains a given anchor set, by growing whole
                              symmetry orbits (a state is a union of orbits of
                              one of the seven lattice symmetries).
TOOL 2  `check_partial`    -- given a PARTIAL partition (some states fully
                              specified), compute rigorous bounds on d(x) for
                              every cell and report which published numbers are
                              already contradicted, and what is forced.

Usage:
    python3 lr11/tools.py corner          # tool 3: lower-right candidates
    python3 lr11/tools.py check FILE      # tool 2: check a partial partition
"""

from __future__ import annotations

import json
import sys
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from lr11 import kernel as K

Cell = Tuple[int, int]
N = 11

# --------------------------------------------------------------------------- #
# the published 11x11 numbers (0-based)
# --------------------------------------------------------------------------- #
PUBLISHED: Dict[Cell, int] = {
    (0, 1): 8, (0, 2): 4, (0, 5): 11, (0, 9): 5,
    (1, 7): 11,
    (2, 2): 7, (2, 5): 1, (2, 10): 14,
    (3, 0): 28, (3, 3): 51, (3, 6): 1, (3, 8): 6,
    (4, 1): 22, (4, 8): 4, (4, 10): 1,
    (5, 3): 15, (5, 5): 10, (5, 7): 0,
    (6, 0): 11, (6, 2): 11, (6, 9): 9,
    (7, 2): 17, (7, 4): 14, (7, 7): 10, (7, 10): 13,
    (8, 0): 30, (8, 5): 6, (8, 8): 45,
    (9, 3): 10,
    (10, 1): 26, (10, 5): 0, (10, 8): 77, (10, 9): 61,
}

CAPITOL_CELLS = {c for c, v in PUBLISHED.items() if v == 0}


# --------------------------------------------------------------------------- #
# symmetry instances: every rotation/reflection that maps the 11x11 board to
# itself.  Each is a map (r,c) -> (r',c').
# --------------------------------------------------------------------------- #
def _board(n: int) -> Set[Cell]:
    return {(r, c) for r in range(n) for c in range(n)}


def symmetry_instances(n: int = N) -> List[Tuple[str, object]]:
    """Every (name, map) pair that could be a self-symmetry of a SUBSET of the
    n x n board.

    NOTE: most of these maps do NOT preserve the whole board -- only the board
    midline does.  That is deliberate and it is the right thing to do here: a
    state's own symmetry only has to preserve the STATE, not the board.  A
    state in the corner can be symmetric about a vertical axis at column 3.5
    even though the board's midline is at column 5.  `orbits_of` drops the
    orbits that leave the board, which is exactly the set of cells that cannot
    belong to any such state.

    Half-integer axes and centres are allowed: a reflection may run between two
    columns, a rotation may be about the centre of a square.
    """
    out: List[Tuple[str, object]] = []
    # vertical mirror: c -> 2b - c.  2b may be ANY integer, so the axis can sit
    # on a column OR between two columns (b = 0, 0.5, 1, ..., n-1).
    for b2 in range(2 * n - 1):
        out.append((f"refV@{b2 / 2}", lambda r, c, b2=b2: (r, b2 - c)))
    # horizontal mirror: r -> 2a - r, same half-integer axes allowed
    for a2 in range(2 * n - 1):
        out.append((f"refH@{a2 / 2}", lambda r, c, a2=a2: (a2 - r, c)))
    # 180 degree rotation about (a, b);  2a and 2b may be ANY integer, so the
    # centre may sit on a lattice point OR between two rows/columns.
    for a2 in range(2 * n - 1):
        for b2 in range(2 * n - 1):
            out.append((f"rot180@({a2 / 2},{b2 / 2})",
                        lambda r, c, a2=a2, b2=b2: (a2 - r, b2 - c)))
    # 90 / 270 degree rotations.  A 4-fold rotation about (cy,cx) maps lattice
    # points to lattice points iff cy+cx and cy-cx are integers, i.e. iff the
    # doubled centre (u,v) = (2cy,2cx) has u = v (mod 2) -- so BOTH lattice
    # points and half-lattice centres are admissible.
    for u in range(2 * n - 1):
        for v in range(2 * n - 1):
            if (u - v) % 2:
                continue
            h = (u - v) // 2
            m = (u + v) // 2
            out.append((f"rot90@({u / 2},{v / 2})",
                        lambda r, c, h=h, m=m: (c + h, m - r)))
            out.append((f"rot270@({u / 2},{v / 2})",
                        lambda r, c, h=h, m=m: (m - c, r - h)))
    # diagonal mirrors: r - c = k  and  r + c = k
    for k in range(-(n - 1), n):
        out.append((f"refD1@{k}", lambda r, c, k=k: (c + k, r - k)))
    for k in range(0, 2 * n - 1):
        out.append((f"refD2@{k}", lambda r, c, k=k: (k - c, k - r)))
    return out


def orbits_of(mapfn, n: int) -> Tuple[List[List[Cell]], Set[Cell]]:
    """Orbit partition of the board under `mapfn`; cells whose orbit leaves the
    board are dropped (they cannot belong to any state invariant under it)."""
    board = _board(n)
    seen: Set[Cell] = set()
    orbits: List[List[Cell]] = []
    for cell in sorted(board):
        if cell in seen:
            continue
        orb: List[Cell] = []
        x = cell
        ok = True
        while x not in orb:
            if x not in board:
                ok = False
                break
            orb.append(x)
            x = mapfn(*x)
        if ok:
            orbits.append(orb)
            seen.update(orb)
    return orbits, seen


def _adjacent(a: Iterable[Cell], b: Set[Cell]) -> bool:
    for (r, c) in a:
        for dr, dc in K.ORTHO:
            if (r + dr, c + dc) in b:
                return True
    return False


# --------------------------------------------------------------------------- #
# TOOL 3 -- grow legal states from an anchor set
# --------------------------------------------------------------------------- #
def grow_states(target: int,
                anchors: Sequence[Cell],
                n: int = N,
                max_solutions: int = 20000,
                forbid: Optional[Set[Cell]] = None,
                seen_cap: int = 2000000) -> List[Tuple[FrozenSet[Cell], str]]:
    """Every legal state of `target` cells that contains all `anchors`.

    A legal state is 4-connected and has at least one non-trivial self-symmetry
    (official rule: a shape with no symmetry is not a state at all).  The search
    grows WHOLE ORBITS of one symmetry at a time, which is exactly what "the
    state is symmetric under that rotation/reflection" forces.

    Returns (cell_set, symmetry_name) pairs, deduplicated by cell set.
    """
    anchors = set(anchors)
    if not anchors:
        raise ValueError("need at least one anchor")
    forbid = forbid or set()
    found: Dict[FrozenSet[Cell], str] = {}

    for name, mapfn in symmetry_instances(n):
        orbits, usable = orbits_of(mapfn, n)
        if not all(a in usable for a in anchors):
            continue
        # orbits that contain an anchor are forced in
        forced_idx = [i for i, o in enumerate(orbits) if any(a in o for a in anchors)]
        base: Set[Cell] = set()
        for i in forced_idx:
            base.update(orbits[i])
        if len(base) > target:
            continue
        rest = [frozenset(o) for i, o in enumerate(orbits) if i not in forced_idx]

        # Connected-union enumeration.  An orbit may only be added when it
        # touches the cells already chosen, but it may be added in ANY ORDER --
        # a "choose the next orbit from an ordered list" scheme would miss
        # states whose low-index orbit only becomes reachable later.
        # Dedup by the resulting cell set.
        seen: Set[FrozenSet[Cell]] = {frozenset(base)}
        stack: List[FrozenSet[Cell]] = [frozenset(base)]
        while stack:
            cur = stack.pop()
            if len(cur) == target:
                if not (cur & forbid) and K.connected(cur) and K.is_legal_state(cur):
                    found.setdefault(cur, name)
                continue
            for o in rest:
                if o in cur:
                    continue
                if len(cur) + len(o) > target:
                    continue
                if not _adjacent(o, cur):
                    continue
                nxt = cur | o
                if nxt in seen:
                    continue
                seen.add(nxt)
                stack.append(nxt)
            if len(seen) > seen_cap:
                raise RuntimeError(
                    f"grow_states: the orbit search hit the {seen_cap} visited-set cap "
                    f"(symmetry {name}); raise seen_cap rather than lose states silently")
        if len(found) > max_solutions:
            break
    return [(frozenset(s), nm) for s, nm in found.items()]


# --------------------------------------------------------------------------- #
# filters that use the published numbers
# --------------------------------------------------------------------------- #
def internal_consistency(S: FrozenSet[Cell], published: Dict[Cell, int]) -> Optional[str]:
    """Necessary conditions on the published numbers INSIDE a candidate state.

    * inside one state of size k every step costs k, so for ADJACENT cells
      |d(x) - d(y)| <= k                     (the L2/L3 lemma)
    * for any two cells of the state, |d(x) - d(y)| <= k * dist_S(x, y)
    * a published 0 inside a state of even size is impossible (an even state
      has no capitol, so no cell of it can have d = 0)
    * the state's capitol must READ 0 if it is published at all.  This is what
      kills a 1x1 state sitting on a published 1: a singleton is its own
      capitol, so it would read 0, never 1.
    """
    k = len(S)
    inside = {c: v for c, v in published.items() if c in S}
    for (r, c), v in inside.items():
        for dr, dc in K.ORTHO:
            nb = (r + dr, c + dc)
            if nb in inside and abs(v - inside[nb]) > k:
                return f"adjacent published numbers {v} and {inside[nb]} differ by more than {k}"
    # all-pairs via the in-state graph distance
    dist = _state_distances(S)
    cells = list(inside)
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            d = dist.get((a, b))
            if d is not None and abs(inside[a] - inside[b]) > k * d:
                return (f"published {inside[a]} at {a} and {inside[b]} at {b} differ by "
                        f"{abs(inside[a]-inside[b])} > {k}*{d}")
    if k % 2 == 0:
        for c, v in inside.items():
            if v == 0:
                return f"published 0 at {c} inside an even-sized state (size {k})"
    cap = K.capitol_of(S)
    if cap is not None and cap in published and published[cap] != 0:
        return (f"the state's capitol is {cap}, but that cell reads {published[cap]}, "
                f"not 0 (a 1x1 state on a published 1 would be caught here too)")
    return None


def _state_distances(S: FrozenSet[Cell]) -> Dict[Tuple[Cell, Cell], int]:
    """All-pairs graph distance inside the state (BFS from every cell)."""
    out: Dict[Tuple[Cell, Cell], int] = {}
    s = set(S)
    for start in s:
        d = {start: 0}
        q = [start]
        for x in q:
            for nb in K.neighbours(x):
                if nb in s and nb not in d:
                    d[nb] = d[x] + 1
                    q.append(nb)
        for t, dd in d.items():
            out[(start, t)] = dd
    return out


# --------------------------------------------------------------------------- #
# TOOL 2 -- rigorous partial-partition checking
# --------------------------------------------------------------------------- #
def check_partial(states: Sequence[FrozenSet[Cell]],
                  published: Dict[Cell, int],
                  n: int = N) -> dict:
    """Check a PARTIAL partition against the published numbers.

    `states` are fully specified states (cell sets).  Cells not covered are
    free.  Returns a report with three kinds of statement.

    UB(x)  -- a rigorous UPPER bound on d(x).
              d(x) is the least cost to ANY capitol, so d(x) <= the cost of
              any particular path to a REVEALED capitol.  We take the cheapest
              such path, but we may only use edges whose cost can be bounded
              from above: an edge between a known cell (size k) and a free
              cell costs min(k, s_free) <= k, so we charge k; an edge between
              two FREE cells has no upper bound and is therefore forbidden.
              => a published value v with UB(x) < v is CONTRADICTED.

    LB(x)  -- the cheapest distance from x to the nearest REVEALED capitol in
              the OPTIMISTIC graph (free cells given size 1).  This is NOT a
              bound on d(x) -- d(x) may be smaller because an UNREVELED capitol
              can be closer.  It says: "the cheapest capitol for x is not a
              revealed one, so a hidden capitol must exist within v steps of
              x" (the hitting-set constraint).
    """
    known_size: Dict[Cell, int] = {}
    known_capitals: Set[Cell] = set()
    # a published 0 IS a capitol (official rule: d(x)=0 <=> x is a capitol),
    # so every revealed 0 is a source for the distance computation
    for c, v in published.items():
        if v == 0:
            known_capitals.add(c)
    for S in states:
        k = len(S)
        for c in S:
            known_size[c] = k
        cap = K.capitol_of(S)
        if cap is not None:
            known_capitals.add(cap)

    def search(optimistic: bool) -> Dict[Cell, Optional[int]]:
        """optimistic=True  -> LB (free cells cost 1)
           optimistic=False -> UB (free<->free edges are forbidden, and an
                                   edge with one known cell is charged that
                                   known cell's size, an upper bound)"""
        import heapq
        INF = float("inf")
        dist: Dict[Cell, float] = {}
        pq: List[Tuple[int, Cell]] = []
        for c in known_capitals:
            dist[c] = 0
            heapq.heappush(pq, (0, c))
        while pq:
            d, u = heapq.heappop(pq)
            if u in dist and d > dist[u]:
                continue
            for v in K.neighbours(u):
                if not (0 <= v[0] < n and 0 <= v[1] < n):
                    continue                    # the board is a hard boundary
                ku = known_size.get(u)
                kv = known_size.get(v)
                if ku is None and kv is None:
                    if optimistic:
                        w = 1
                    else:
                        continue                # no upper bound on min(su,sv)
                elif ku is None:
                    w = 1 if optimistic else kv
                elif kv is None:
                    w = 1 if optimistic else ku
                else:
                    w = min(ku, kv)
                nd = d + w
                if v not in dist or nd < dist[v]:
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return {c: (None if v == INF else int(v)) for c, v in dist.items()}

    lb = search(True)
    ub = search(False)

    contradicted = []
    needs_hidden_capitol = []
    for c, v in sorted(published.items()):
        U = ub.get(c)
        L = lb.get(c)
        if U is not None and U < v:
            contradicted.append((c, v, f"upper bound {U} < published {v}: the cheapest "
                                         f"route to a revealed capitol is already cheaper"))
        elif L is not None and L > v:
            needs_hidden_capitol.append((c, v, f"the nearest revealed capitol is at least {L} "
                                              f"away but the cell reads {v}, so an UNREVELED "
                                              f"capitol must be within {v} steps"))
        elif U is not None and U == v:
            needs_hidden_capitol.append((c, v, f"published value equals the upper bound {U}: "
                                              f"the route to a revealed capitol is the geodesic, "
                                              f"so no hidden capitol may be closer"))

    # structural checks on the specified states
    problems = []
    for S in states:
        if not K.connected(S):
            problems.append(f"state {sorted(S)} is not 4-connected")
        if not K.symmetry_group(S):
            problems.append(f"state {sorted(S)} has NO non-trivial symmetry, so it is not a state at all")
        cap = K.capitol_of(S)
        if cap is not None and cap in published and published[cap] != 0:
            problems.append(f"state with capitol at {cap} but the published value there is {published[cap]}")
        for c in S:
            if c in published and published[c] == 0 and cap != c:
                problems.append(f"published 0 at {c} but that state's capitol is {cap}")

    return {
        "known_capitals": sorted(c for c in known_capitals if c is not None),
        "contradicted": contradicted,
        "needs_hidden_capitol": needs_hidden_capitol,
        "structural_problems": problems,
        # not bounds on the true d(x): the two ends of the distance to the
        # capitols we already KNOW about.  A hidden capitol can be nearer.
        "near_known_optimistic": {str(c): v for c, v in sorted(lb.items()) if v is not None},
        "near_known_pessimistic": {str(c): v for c, v in sorted(ub.items()) if v is not None},
        "covered_cells": len(known_size),
        "free_cells": n * n - len(known_size),
    }


# --------------------------------------------------------------------------- #
# JOINT corner enumeration
# --------------------------------------------------------------------------- #
# d-values that follow from the forced singleton at (5,10): every neighbour of
# a 1x1 capitol is reached in one step of cost 1, so its d is AT MOST 1.
DERIVED_D_MAX: Dict[Cell, int] = {(4, 10): 1, (5, 9): 1, (6, 10): 1}


def tight_neighbour_ok(S: FrozenSet[Cell], x: Cell, v: int,
                       exact: Dict[Cell, int], upper: Dict[Cell, int]) -> Optional[str]:
    """L1 applied inside a candidate state of size k = |S|.

    The tight neighbour y of x satisfies  d(y) = v - min(k, s(y)), so
        d(y) is exactly v-k   if y is inside S,
        d(y) lies in [v-k, v-1]  if y is outside S (the crossing cost is the
                                 smaller of the two state sizes, at least 1).
    At least one neighbour must admit such a value.
    """
    k = len(S)
    lo, hi = v - k, v - 1
    if v == 0:
        return None            # d(x)=0 means x IS a capitol; L1 does not apply
    if hi < 0:
        return f"published {v} at {x} inside a state of size {k}: no neighbour can have d < {v}"
    for y in K.neighbours(x):
        if y not in S:
            if y in exact:
                if lo <= exact[y] <= hi:
                    return None
            elif y in upper:
                if lo <= upper[y]:
                    return None
            else:
                return None          # unknown: always admissible
        else:
            if y in exact and exact[y] != v - k:
                continue
            if y in exact and exact[y] == v - k:
                return None
            if y not in exact:
                return None          # d(y) = v-k is possible
    return (f"published {v} at {x} inside a state of size {k}: no neighbour admits a "
            f"d-value in [{lo}, {hi}]")


def corner_joint(verbose: int = 25) -> dict:
    """Jointly enumerate the lower-right corner: 12-state, 8-state, 16-state.

    The three states must be pairwise disjoint, and every published number
    inside them must satisfy the internal lemmas AND the tight-neighbour rule.
    """
    forbid = {(5, 10)} | (CAPITOL_CELLS - {(5, 10)})
    c12 = [(S, nm) for S, nm in grow_states(12, [(6, 10), (7, 10), (8, 10)], forbid=forbid)
           if internal_consistency(S, PUBLISHED) is None]
    c16 = [(S, nm) for S, nm in grow_states(16, [(10, 8), (10, 9)], forbid=forbid)
           if internal_consistency(S, PUBLISHED) is None]
    c8 = [(S, nm) for S, nm in grow_states(8, [(5, 9), (6, 9)], forbid=forbid)
          if internal_consistency(S, PUBLISHED) is None]
    print(f"candidates: 12-state {len(c12)}, 8-state {len(c8)}, 16-state {len(c16)}")

    exact = dict(PUBLISHED)
    upper = dict(DERIVED_D_MAX)
    survivors = []
    rejected = {"disjoint": 0, "tight": 0, "partial": 0}
    for S12, n12 in c12:
        for S8, n8 in c8:
            if S12 & S8:
                rejected["disjoint"] += 1
                continue
            bad = None
            for S in (S12, S8):
                for cell, v in PUBLISHED.items():
                    if cell in S:
                        bad = tight_neighbour_ok(S, cell, v, exact, upper)
                        if bad:
                            break
                if bad:
                    break
            if bad:
                rejected["tight"] += 1
                continue
            for S16, n16 in c16:
                if (S16 & S12) or (S16 & S8):
                    rejected["disjoint"] += 1
                    continue
                bad = None
                for S in (S12, S8, S16):
                    for cell, v in PUBLISHED.items():
                        if cell in S:
                            bad = tight_neighbour_ok(S, cell, v, exact, upper)
                            if bad:
                                break
                    if bad:
                        break
                if bad:
                    rejected["tight"] += 1
                    continue
                survivors.append((S12, n12, S8, n8, S16, n16))

    print(f"pairs after disjointness + tight-neighbour rules: {len(survivors)} "
          f"(rejected: {rejected})")

    # final rigorous pass: partial-partition bounds (Dijkstra is the bottleneck,
    # so it runs on a bounded prefix and the count of unchecked ones is reported)
    import os
    cap = int(os.environ.get("LR11_CHECK_CAP", "2000"))
    ok = []
    checked = 0
    for S12, n12, S8, n8, S16, n16 in survivors:
        if checked >= cap:
            break
        checked += 1
        states = [frozenset({(5, 10)}), frozenset(S12), frozenset(S8), frozenset(S16)]
        rep = check_partial(states, PUBLISHED)
        if not rep["contradicted"] and not rep["structural_problems"]:
            ok.append((S12, n12, S8, n8, S16, n16, rep))
    if checked < len(survivors):
        print(f"NOTE: only the first {checked} of {len(survivors)} survivors got the "
              f"full bound check (raise LR11_CHECK_CAP to cover the rest)")
    print(f"after the partial-partition bound check: {len(ok)}")
    for S12, n12, S8, n8, S16, n16, rep in ok[:verbose]:
        print("-" * 74)
        print(f"  12-state sym={n12:<22} {sorted(S12)}")
        print(f"   8-state sym={n8:<22} {sorted(S8)}")
        print(f"  16-state sym={n16:<22} {sorted(S16)}")
        print(f"   known capitols: {rep['known_capitals']}")
    if len(ok) > verbose:
        print(f"  ... and {len(ok)-verbose} more")
    return {"c12": c12, "c8": c8, "c16": c16, "survivors": survivors, "ok": ok}


# --------------------------------------------------------------------------- #
# the lower-right analysis
# --------------------------------------------------------------------------- #
def corner_report() -> None:
    print("=" * 78)
    print("TOOL 3 -- lower-right corner candidates (official 11x11)")
    print("=" * 78)

    # (a) the forced singleton
    print("\n[a] the forced 1x1 state at (5,10)")
    forced = frozenset({(5, 10)})
    print(f"    legal state: {K.is_legal_state(forced)}   capitol: {K.capitol_of(forced)}")

    # (b) the 12-cell state: anchors (6,10),(7,10),(8,10)
    print("\n[b] the 12-cell state (anchors (6,10),(7,10),(8,10))")
    forbid = {(5, 10)} | CAPITOL_CELLS - {(5, 10)}
    cands = grow_states(12, [(6, 10), (7, 10), (8, 10)], forbid=forbid)
    print(f"    raw legal candidates: {len(cands)}")
    kept = []
    for S, nm in cands:
        why = internal_consistency(S, PUBLISHED)
        if why is None:
            kept.append((S, nm))
    print(f"    after the published-number filters: {len(kept)}")
    for S, nm in sorted(kept, key=lambda t: sorted(t[0]))[:40]:
        cap = K.capitol_of(S)
        print(f"      sym={nm:<22} capitol={cap}  cells={sorted(S)}")
    if len(kept) > 40:
        print(f"      ... and {len(kept)-40} more")

    # (c) the 8-cell state: anchors (6,9) and (5,9) -- both readings
    print("\n[c] the 8-cell state, reading A' (contains (5,9) AND (6,9))")
    c8a = grow_states(8, [(5, 9), (6, 9)], forbid=forbid)
    print(f"    raw legal candidates: {len(c8a)}")
    kept8a = [(S, nm) for S, nm in c8a if internal_consistency(S, PUBLISHED) is None]
    print(f"    after the published-number filters: {len(kept8a)}")
    for S, nm in sorted(kept8a, key=lambda t: sorted(t[0]))[:25]:
        print(f"      sym={nm:<22} cells={sorted(S)}")
    if len(kept8a) > 25:
        print(f"      ... and {len(kept8a)-25} more")

    print("\n[d] the 8-cell state, reading B' (contains (6,9) only)")
    c8b = grow_states(8, [(6, 9)], forbid=forbid)
    kept8b = [(S, nm) for S, nm in c8b
              if internal_consistency(S, PUBLISHED) is None and (5, 9) not in S]
    print(f"    raw legal candidates: {len(c8b)}   excluding those containing (5,9): {len(kept8b)}")
    for S, nm in sorted(kept8b, key=lambda t: sorted(t[0]))[:25]:
        print(f"      sym={nm:<22} cells={sorted(S)}")
    if len(kept8b) > 25:
        print(f"      ... and {len(kept8b)-25} more")

    # (e) the 16-cell state: anchors (10,8),(10,9)
    print("\n[e] the 16-cell state (anchors (10,8),(10,9))")
    c16 = grow_states(16, [(10, 8), (10, 9)], forbid=forbid)
    print(f"    raw legal candidates: {len(c16)}")
    kept16 = [(S, nm) for S, nm in c16 if internal_consistency(S, PUBLISHED) is None]
    print(f"    after the published-number filters: {len(kept16)}")
    for S, nm in sorted(kept16, key=lambda t: sorted(t[0]))[:40]:
        print(f"      sym={nm:<22} cells={sorted(S)}")
    if len(kept16) > 40:
        print(f"      ... and {len(kept16)-40} more")


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "corner":
        corner_report()
        return 0
    if cmd == "joint":
        corner_joint()
        return 0
    if cmd == "check":
        path = argv[1]
        with open(path) as fh:
            data = json.load(fh)
        states = [frozenset(tuple(c) for c in S) for S in data["states"]]
        pub = {tuple(k): v for k, v in data.get("published", {}).items()} or PUBLISHED
        rep = check_partial(states, pub)
        print(json.dumps(rep, indent=2, default=str))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
