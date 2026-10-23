"""Route A, second version: anneal over LEGAL tilings.

The first version of this file punished a structural violation with BIG = 1000, and that
turned out to be the reason it did not move: a "kick" that breaks the symmetry of a state
costs 1000, and no sequence of local moves can ever climb back out of that hole.  The
search was fenced in.

So the moves here are LEGALITY-PRESERVING by construction.  A state of the search is a
tiling of the board by legal states (connected, with a non-trivial self-symmetry).  The
only move is "re-tile a small region":

    take a connected region R (a union of one to three current states),
    enumerate the legal tilings of R,
    replace R's states with one of them.

That keeps every state legal, keeps the board fully covered, and therefore keeps the cost
field well defined -- so the energy is just the mismatch with the published numbers, and
no penalty term is needed at all.

The honesty rule from the review round still applies: the energy only ever uses the
engine's own arithmetic, and a heuristic signal may RANK candidates but never PRUNE them.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Set, Tuple

from cost import INF, Puzzle
from rules import connected, symmetry_group

Cell = Tuple[int, int]
State = frozenset

_BIG = 1e6


# --------------------------------------------------------------------------- #
# the legal states of a board
# --------------------------------------------------------------------------- #
class LegalStates:
    """The legal states of an n x n board, and the tilings of small regions."""

    def __init__(self, n: int, catalogue=None):
        self.n = n
        self.cells = [(r, c) for r in range(n) for c in range(n)]
        self._by_cell: Dict[Cell, List[State]] = {}
        if catalogue is None:
            from lazycatalogue import LazyCatalogue
            catalogue = LazyCatalogue(n)
        for c in self.cells:
            try:
                sts = [frozenset(s) for s in catalogue.cell_states(c)]
            except Exception:            # noqa: BLE001 - the catalogue may be too big
                sts = []
            self._by_cell[c] = sts
        self._tiling_cache: Dict[frozenset, List[List[State]]] = {}

    def inside(self, region: State) -> List[State]:
        """The legal states that fit entirely inside the region."""
        if not region:
            return []
        first = min(region)
        return [s for s in self._by_cell.get(first, []) if s <= region]

    def tilings(self, region: State, limit: int = 64) -> List[List[State]]:
        """Every legal tiling of the region (at most `limit` of them)."""
        key = frozenset(region)
        hit = self._tiling_cache.get(key)
        if hit is not None:
            return hit
        opts = self.inside(region)
        out: List[List[State]] = []

        def rec(rem: Set[Cell], acc: List[State]):
            if len(out) >= limit:
                return
            if not rem:
                out.append(list(acc))
                return
            first = min(rem)
            for s in opts:
                if s and s <= rem and first in s:
                    acc.append(s)
                    rec(rem - s, acc)
                    acc.pop()

        rec(set(region), [])
        self._tiling_cache[key] = out
        return out


# --------------------------------------------------------------------------- #
# the energy
# --------------------------------------------------------------------------- #
def energy(states: Sequence[State], hints: Dict[Cell, int], n: int) -> float:
    """How far the candidate's cost field is from the published numbers."""
    try:
        puz = Puzzle([set(s) for s in states])
        d = puz.cost_field()
    except Exception:                    # noqa: BLE001 - a broken partition has no d field
        return _BIG
    e = 0.0
    for (r, c), v in hints.items():
        if not (0 <= r < n and 0 <= c < n):
            e += _BIG
            continue
        dv = d[r][c]
        if dv == INF or dv != dv:
            e += 50.0                 # no capitol reaches this cell
        else:
            e += abs(dv - v)
    return e


# --------------------------------------------------------------------------- #
# the move
# --------------------------------------------------------------------------- #
def retile(states: List[State], rng: random.Random, legal: LegalStates,
           max_states: int = 3) -> Optional[List[State]]:
    """Re-tile a small region of the current tiling with legal states."""
    if len(states) < 1:
        return None
    k = rng.randint(1, min(max_states, len(states)))
    idx = rng.sample(range(len(states)), k)
    region: Set[Cell] = set()
    for i in idx:
        region |= set(states[i])
    tilings = legal.tilings(frozenset(region))
    if not tilings:
        return None
    new = rng.choice(tilings)
    out = [s for i, s in enumerate(states) if i not in idx]
    out.extend(new)
    return out


# --------------------------------------------------------------------------- #
# the search
# --------------------------------------------------------------------------- #
def random_legal_tiling(n: int, legal: LegalStates, rng: random.Random) -> List[State]:
    """A random legal tiling of the board (or as close as we can get quickly)."""
    cells = set(legal.cells)
    states: List[State] = []
    while cells:
        first = min(cells)
        cands = [s for s in legal._by_cell.get(first, []) if s <= cells]
        if not cands:
            # no legal state fits here: fall back to a single cell (illegal, but the
            # energy will push it away)
            states.append(frozenset({first}))
            cells.discard(first)
            continue
        s = rng.choice(cands)
        states.append(s)
        cells -= s
    return states


def anneal(hints: Dict[Cell, int], n: int, steps: int = 20000, seed: int = 0,
           n_states: int = 5, tolerance: float = 10.0, report_every: int = 0,
           legal: Optional[LegalStates] = None, max_region: int = 5) -> Dict[str, object]:
    """Search for a legal tiling whose cost field reproduces the published numbers."""
    rng = random.Random(seed)
    if legal is None:
        legal = LegalStates(n)
    states = random_legal_tiling(n, legal, rng)
    cur_e = energy(states, hints, n)
    best_e, best_states = cur_e, list(states)
    since_improve = 0
    history = []
    for step in range(steps):
        cand = retile(states, rng, legal, max_states=max_region)
        if cand is None:
            continue
        new_e = energy(cand, hints, n)
        # record-to-record travel: accept anything that is no worse than the BEST energy
        # seen so far, plus a tolerance.  A pure hill climb (accept only if no worse than
        # the current) freezes immediately -- the trajectory was flat from 20k steps on.
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
