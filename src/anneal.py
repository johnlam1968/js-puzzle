"""Route A: anneal over candidate partitions, with the published numbers as the energy.

Why this exists: the OFFICIAL puzzle does not ask us to prove anything.  It asks for a
number.  A partition that reproduces the published numbers is worth an order of magnitude
more than an unfinished proof that the answer is unique -- especially because two
different partitions can share one cost field and still give different answers (the 4x4
counterexample: 304 and 112), so "is the answer unique" is itself a hunt for a second
partition, not an enumeration.

The energy is deliberately simple and every legality question is answered by the engine,
never by this file:

    energy(T) = sum over the published cells of |d_T(x) - D(x)|
              + BIG * (the number of structural violations of T)

where d_T is the cost field the engine computes for the candidate partition T, and a
structural violation is a state that is not connected or has no non-trivial self-symmetry
(or a partition that does not cover the board).

The acceptance rule is record-to-record travel: accept a proposal when it is no worse
than the best energy seen so far plus a small tolerance.  There is no temperature, so
there is nothing to tune.

Safety rule that came out of a real mistake: a heuristic signal may RANK things, it may
not PRUNE.  Nothing here ever rejects a partition because of a heuristic; only the
engine's own arithmetic feeds the energy.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Tuple

from cost import INF, Puzzle
from grow import grow_states, orbits_of, symmetry_choices
from lazycatalogue import LazyCatalogue
from rules import connected, symmetry_group

# Caches: the annealing evaluates the same states and the same growths over and over.
_GROWTH_CACHE: Dict[Tuple[int, Cell, int], List[frozenset]] = {}
_LEGAL_CACHE: Dict[frozenset, bool] = {}


_ORBIT_CACHE: Dict[Tuple[int, int], Dict[Cell, frozenset]] = {}
_CATALOGUE: Dict[int, List[frozenset]] = {}


def _legal_states(n: int) -> List[frozenset]:
    """Every legal state of an n x n board, when the catalogue can be built.

    For n <= 5 the catalogue is exact and cheap enough (5x5: 22,317 states), and it
    makes the "reshape a state" move both exact and cheap.  For n >= 6 it is not
    enumerable, and the move falls back to growing one state from a seed.
    """
    hit = _CATALOGUE.get(n)
    if hit is None:
        try:
            cat = LazyCatalogue(n)
            states = set()
            for r in range(n):
                for c in range(n):
                    for st in cat.cell_states((r, c)):
                        states.add(st)
            hit = sorted(states, key=lambda s: (-len(s), sorted(s)))
        except Exception:                # noqa: BLE001 - the catalogue may be too big
            hit = []
        _CATALOGUE[n] = hit
    return hit


def _orbit_of(n: int, cell: Cell, sym) -> frozenset:
    key = (n, id(sym))
    d = _ORBIT_CACHE.get(key)
    if d is None:
        d = orbits_of(sym, n)
        _ORBIT_CACHE[key] = d
    return d.get(cell, frozenset())


def _viable_syms(n: int, seed: Cell, syms) -> List:
    """The symmetries whose orbit of `seed` lies fully on the board.

    Iterating over ALL symmetries and testing each one cost 780 ms per move; the board
    only admits a small fraction of them.
    """
    out = []
    for sym in syms:
        o = _orbit_of(n, seed, sym)
        if o and all(0 <= r < n and 0 <= c < n for (r, c) in o):
            out.append(sym)
    return out


def _growth(n: int, seed: Cell, sym) -> List[frozenset]:
    key = (n, seed, id(sym))
    hit = _GROWTH_CACHE.get(key)
    if hit is None:
        hit = [frozenset(s) for s in grow_states(seed, sym, n)]
        _GROWTH_CACHE[key] = hit
    return hit


def _is_legal(st: frozenset) -> bool:
    hit = _LEGAL_CACHE.get(st)
    if hit is None:
        hit = bool(st) and connected(st) and bool(symmetry_group(st))
        _LEGAL_CACHE[st] = hit
    return hit

Cell = Tuple[int, int]
State = frozenset


# The penalty for a structural violation has to live on the SAME scale as the mismatch
# it is meant to be traded against.  With BIG = 1000 a single broken state cost more than
# every d-mismatch put together, so a "kick" could never be undone and the search was
# fenced inside the legal region it started in.
BIG = 5.0
# a cell that no capitol reaches: a finite penalty, not a wall
INF_PENALTY = 5.0


# --------------------------------------------------------------------------- #
# the energy
# --------------------------------------------------------------------------- #
def structural_violations(states: Sequence[State], n: int) -> int:
    """How many rules the candidate partition breaks (0 = all good)."""
    bad = 0
    cover: Dict[Cell, int] = {}
    for st in states:
        if not st:
            bad += 1
            continue
        for c in st:
            cover[c] = cover.get(c, 0) + 1
        if len(cover) and any(v > 1 for v in cover.values()):
            pass                       # overlaps are counted below
        if not _is_legal(st):
            bad += 1
    if len(cover) != n * n:
        bad += 1                        # the board is not fully covered
    elif any(v > 1 for v in cover.values()):
        bad += 1                        # some cell is claimed twice
    return bad


def energy(states: Sequence[State], hints: Dict[Cell, int], n: int,
           big: float = BIG) -> float:
    """The mismatch between the candidate's cost field and the published numbers."""
    e = big * structural_violations(states, n)
    try:
        puz = Puzzle([set(s) for s in states])
        d = puz.cost_field()
    except Exception:                    # noqa: BLE001 - a broken partition has no d field
        return e + INF_PENALTY * (len(hints) + 1)
    for (r, c), v in hints.items():
        if not (0 <= r < n and 0 <= c < n):
            e += big
            continue
        dv = d[r][c]
        if dv == INF or dv != dv:       # INF, or NaN
            e += INF_PENALTY
        else:
            e += abs(dv - v)
    return e


# --------------------------------------------------------------------------- #
# the moves -- every one keeps the board fully covered
# --------------------------------------------------------------------------- #
def _neighbours(c: Cell, n: int):
    r, cc = c
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = (r + dr, cc + dc)
        if 0 <= nb[0] < n and 0 <= nb[1] < n:
            yield nb


def move_cell(states: List[State], rng: random.Random, n: int) -> Optional[List[State]]:
    """Move one cell into an adjacent state (or into a new singleton state)."""
    if not states:
        return None
    i = rng.randrange(len(states))
    st = states[i]
    if not st:
        return None
    cell = rng.choice(sorted(st))
    if len(st) == 1:
        return None
    targets = []
    for j, other in enumerate(states):
        if j == i:
            continue
        if any(nb in other for nb in _neighbours(cell, n)):
            targets.append(j)
    if targets and rng.random() < 0.8:
        j = rng.choice(targets)
        out = list(states)
        out[i] = frozenset(st - {cell})
        out[j] = frozenset(states[j] | {cell})
        return out
    # otherwise it becomes a singleton state of its own
    out = list(states)
    out[i] = frozenset(st - {cell})
    out.append(frozenset({cell}))
    return out


def merge_states(states: List[State], rng: random.Random, n: int) -> Optional[List[State]]:
    """Merge two states that touch each other."""
    if len(states) < 2:
        return None
    pairs = []
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            if any(nb in states[j] for c in states[i] for nb in _neighbours(c, n)):
                pairs.append((i, j))
    if not pairs:
        return None
    i, j = rng.choice(pairs)
    out = [s for k, s in enumerate(states) if k not in (i, j)]
    out.append(frozenset(states[i] | states[j]))
    return out


def split_state(states: List[State], rng: random.Random, n: int) -> Optional[List[State]]:
    """Split a state into two connected parts (by cutting out one cell)."""
    idx = [i for i, s in enumerate(states) if len(s) >= 2]
    if not idx:
        return None
    i = rng.choice(idx)
    st = states[i]
    cell = rng.choice(sorted(st))
    rest = st - {cell}
    # the connected components of the rest
    seen = set()
    comps = []
    for c in sorted(rest):
        if c in seen:
            continue
        stack = [c]
        comp = set()
        seen.add(c)
        while stack:
            x = stack.pop()
            comp.add(x)
            for nb in _neighbours(x, n):
                if nb in rest and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(frozenset(comp))
    if len(comps) < 2:
        return None
    out = [s for k, s in enumerate(states) if k != i]
    out.extend(comps)
    return out


def regrow_state(states: List[State], rng: random.Random, n: int,
                 syms=None) -> Optional[List[State]]:
    """Rebuild one state under a different symmetry -- the move that changes a state's
    shape, and with it the state's capitol and its area."""
    if not states:
        return None
    if syms is None:
        syms = symmetry_choices(n)
    i = rng.randrange(len(states))
    st = states[i]
    if not st:
        return None
    seed = rng.choice(sorted(st))
    others = [s for k, s in enumerate(states) if k != i]
    taken = set()
    for s in others:
        taken |= s
    legal = _legal_states(n)
    if legal:
        # the exact catalogue: pick a legal state that does not collide with the others
        tries = 0
        while tries < 40:
            tries += 1
            shape = legal[rng.randrange(len(legal))]
            if shape & taken or not shape:
                continue
            break
        else:
            return None
    else:
        viable = _viable_syms(n, seed, syms)
        if not viable:
            return None
        order = list(viable)
        rng.shuffle(order)
        shape = None
        for sym in order[:8]:            # a few tries, not all of them
            shapes = _growth(n, seed, sym)
            if not shapes:
                continue
            cand = rng.choice(shapes)
            if cand & taken:
                continue
            shape = cand
            break
        if shape is None:
            return None
        out = list(states)
        out[i] = frozenset(shape)
        # the cells of the old state that the new shape does not use go to their
        # neighbours, so the board stays fully covered
        leftover = sorted(st - set(shape))
        out = [s for k, s in enumerate(out) if k != i]
        out.append(frozenset(shape))
        for cell in leftover:
            put = None
            for k, s in enumerate(out):
                if any(nb in s for nb in _neighbours(cell, n)):
                    put = k
                    break
            if put is None:
                out.append(frozenset({cell}))
            else:
                out[put] = frozenset(out[put] | {cell})
        return out
    return None


MOVES = (move_cell, merge_states, split_state, regrow_state)


# --------------------------------------------------------------------------- #
# the search
# --------------------------------------------------------------------------- #
def random_partition(n: int, rng: random.Random, n_states: int) -> List[State]:
    """A random partition of the board into n_states cell sets (not legal, just a start)."""
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)
    states: List[State] = []
    per = max(1, len(cells) // n_states)
    i = 0
    for k in range(n_states):
        take = per if k < n_states - 1 else len(cells) - i
        states.append(frozenset(cells[i:i + take]))
        i += take
    return states


def anneal(hints: Dict[Cell, int], n: int, steps: int = 20000, seed: int = 0,
           n_states: int = 5, tolerance: float = 1.0, kick_after: int = 400,
           report_every: int = 0) -> Dict[str, object]:
    """Search for a partition whose cost field reproduces the published numbers."""
    rng = random.Random(seed)
    states = random_partition(n, rng, n_states)
    cur_e = energy(states, hints, n)
    best_e, best_states = cur_e, list(states)
    since_improve = 0
    history = []
    for step in range(steps):
        if since_improve >= kick_after:
            # a kick: a few random moves, then back to the best
            states = list(best_states)
            cur_e = best_e
            for _ in range(rng.randrange(2, 6)):
                mv = rng.choice(MOVES)
                cand = mv(states, rng, n)
                if cand is not None:
                    states = cand
            cur_e = energy(states, hints, n)
            since_improve = 0
        mv = rng.choice(MOVES)
        cand = mv(states, rng, n)
        if cand is None:
            continue
        new_e = energy(cand, hints, n)
        # record-to-record travel: accept anything no worse than the BEST energy seen
        # (plus a tolerance).  A pure hill climb freezes: the trajectory was flat from
        # 20k steps on.
        if new_e <= best_e + tolerance:
            states, cur_e = cand, new_e
            if new_e < best_e:
                best_e, best_states = new_e, list(cand)
                since_improve = 0
            else:
                since_improve += 1
        else:
            since_improve += 1
        if report_every and (step + 1) % report_every == 0:
            history.append((step + 1, cur_e, best_e))
    return {
        "best_energy": best_e,
        "states": [sorted(s) for s in best_states],
        "steps": steps,
        "history": history,
        "solved": best_e == 0.0,
    }
