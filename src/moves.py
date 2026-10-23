"""The legal neighbours of a tiling: the three atomic moves that keep the board covered.

Why these three and not "replace a state with a state of a different area": a tiling has
to COVER the board, so any change has to keep every cell owned.  Replacing a state with a
different-sized one would leave its old cells unowned.  The moves here never do that:

    strip : take one cell out of a state; the cell becomes a 1x1 state of its own (a 1x1
            state is always a capitol), and the rest must still be a legal state
    split : split a state into two legal states
    merge : merge two adjacent states into one legal state

This module is the single source of truth for that move set: the annealer uses it for its
curvature measurement and for its kicks, and tools/decisive_move_experiment.py uses it
to measure the landscape.

The measurement that made the move set worth measuring (4x4, every legal tiling):

    the two solutions -- [1 x 12, 2, 2] and [1 x 12, 4] -- are ONE merge apart
    (1 + 3 -> 4), and that merge is the only single step that lowers the energy from 1
    to 0.  That single edge is what the annealer walks.

The 5x5 tells the other half of the story: its solution has only nine legal neighbours
and the cheapest costs 11 energy units, i.e. it stands on a CLIFF.  A local search needs
a good jump there, not a smaller step.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Sequence, Tuple

from rules import connected, symmetry_group

Cell = Tuple[int, int]
State = frozenset


def is_legal(st: State) -> bool:
    """A legal state: connected, and with a non-trivial self-symmetry."""
    return bool(st) and connected(st) and bool(symmetry_group(st))


def neighbours_of_cell(c: Cell, n: int):
    r, cc = c
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = (r + dr, cc + dc)
        if 0 <= nb[0] < n and 0 <= nb[1] < n:
            yield nb


def _subsets(S: State):
    """The proper non-empty subsets of a small state."""
    items = sorted(S)
    if len(items) > 12:
        return
    for mask in range(1, (1 << len(items)) - 1):
        yield frozenset(items[i] for i in range(len(items)) if (mask >> i) & 1)


def legal_neighbours(states: Sequence[State], n: int
                     ) -> List[Tuple[List[State], str, str]]:
    """Every one-step legal neighbour of a tiling, with the move and a description."""
    out: List[Tuple[List[State], str, str]] = []
    states = list(states)

    for i, S in enumerate(states):
        # strip: one cell leaves S and becomes a 1x1 state of its own
        for cell in sorted(S):
            rest = frozenset(S - {cell})
            if rest and is_legal(rest):
                new = [s for k, s in enumerate(states) if k != i]
                new.append(rest)
                new.append(frozenset({cell}))
                out.append((new, "strip", f"cell {cell} off a {len(S)}-cell state"))
        # split: S becomes two legal states
        for A in _subsets(S):
            B = frozenset(S - A)
            if is_legal(A) and is_legal(B):
                new = [s for k, s in enumerate(states) if k != i]
                new.append(A)
                new.append(B)
                out.append((new, "split", f"{len(S)} -> {len(A)}+{len(B)}"))

    # merge: two adjacent states become one legal state
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            A, B = states[i], states[j]
            if not any(nb in B for c in A for nb in neighbours_of_cell(c, n)):
                continue
            U = frozenset(A | B)
            if is_legal(U):
                new = [s for k, s in enumerate(states) if k not in (i, j)]
                new.append(U)
                out.append((new, "merge", f"{len(A)}+{len(B)} -> {len(U)}"))
    return out


def curvature(states: Sequence[State], energy_fn, n: int) -> Dict[str, object]:
    """The local curvature of a tiling: the energy of its cheapest legal neighbour.

    A small gap means a gentle slope -- a hill climb works.  A big gap means a cliff: the
    cheapest way out costs a lot, and a search that only accepts improvements cannot even
    leave.  The 4x4's solutions sit on a slope (their cheapest neighbour is the other
    solution, one energy unit away); the 5x5's solution sits on a cliff (its cheapest
    neighbour costs 11).
    """
    here = energy_fn(states)
    cands = legal_neighbours(states, n)
    if not cands:
        return {"energy": here, "cheapest": None, "gap": None, "neighbours": 0,
                "classification": "isolated"}
    best = None
    best_move = None
    for new_states, kind, detail in cands:
        e = energy_fn(new_states)
        if best is None or e < best:
            best, best_move = e, (kind, detail)
    gap = None if best is None else best - here
    cls = "gentle" if (gap is not None and gap <= 1) else "cliff"
    return {
        "energy": here,
        "cheapest": best,
        "gap": gap,
        "neighbours": len(cands),
        "classification": cls,
        "cheapest_move": best_move,
    }
