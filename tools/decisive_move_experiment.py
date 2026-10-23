#!/usr/bin/env python3
"""The decisive small experiment: which single legal change connects an E=1 tiling to
an E=0 one?

The energy landscape of the 4x4 says the solutions are not isolated (the lowest
non-solution energy is 1), so a local search has something to climb.  But that does not say
which MOVE climbs it.  This measures it: take the tilings at energy 1, enumerate their
one-step legal neighbours (the three atomic moves that keep the board covered), and
record the ones that reach energy 0.

The three moves (all of them keep a full cover, which is why "replace a state with a
state of a different area" is not allowed -- it would leave cells unowned):

    strip : take one cell out of a state; it becomes a 1x1 state of its own
            (which is a capitol), and the rest must still be a legal state
    split : split a state into two legal states
    merge : merge two adjacent states into one legal state

The output is the move set the search actually needs, with the area deltas and the energy
deltas -- and, if no single step reaches energy 0, the fact that the graph needs a wider
step than the energy gap suggests.

Exit code 0 = the experiment ran.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, FrozenSet, List, Sequence, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import INF, Puzzle                    # noqa: E402
from rules import connected, symmetry_group      # noqa: E402
from tilings import Catalogue                    # noqa: E402

Cell = Tuple[int, int]
State = frozenset


def is_legal(st: State) -> bool:
    return bool(st) and connected(st) and bool(symmetry_group(st))


def energy_of(states: Sequence[State], hints: Dict[Cell, int], n: int) -> float:
    try:
        puz = Puzzle([set(s) for s in states])
        d = puz.cost_field()
    except Exception:                            # noqa: BLE001
        return float("inf")
    e = 0.0
    for (r, c), v in hints.items():
        dv = d[r][c]
        e += 50.0 if (dv == INF or dv != dv) else abs(dv - v)
    return e


def neighbours(states: List[State], n: int):
    """Every one-step legal neighbour (strip / split / merge)."""
    out = []

    def emit(new_states, kind, detail):
        out.append((new_states, kind, detail))

    for i, S in enumerate(states):
        # strip: one cell leaves S and becomes a 1x1 state
        for cell in sorted(S):
            rest = frozenset(S - {cell})
            if rest and is_legal(rest):
                new = [s for k, s in enumerate(states) if k != i]
                new.append(rest)
                new.append(frozenset({cell}))
                emit(new, "strip", f"cell {cell} off a {len(S)}-cell state")
        # split: S becomes two legal states
        for A in _subsets(S):
            if not A or A == S:
                continue
            B = frozenset(S - A)
            if is_legal(A) and is_legal(B):
                new = [s for k, s in enumerate(states) if k != i]
                new.append(A)
                new.append(B)
                emit(new, "split", f"{len(S)} -> {len(A)}+{len(B)}")
    # merge: two adjacent states become one legal state
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            A, B = states[i], states[j]
            if not any(nb in B for c in A for nb in _nbrs(c, n)):
                continue
            U = frozenset(A | B)
            if is_legal(U):
                new = [s for k, s in enumerate(states) if k not in (i, j)]
                new.append(U)
                emit(new, "merge", f"{len(A)}+{len(B)} -> {len(U)}")
    return out


def _nbrs(c: Cell, n: int):
    r, cc = c
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = (r + dr, cc + dc)
        if 0 <= nb[0] < n and 0 <= nb[1] < n:
            yield nb


def _subsets(S: State):
    """The proper non-empty subsets of a small state (a state is at most a few cells)."""
    items = sorted(S)
    if len(items) > 12:
        return
    for mask in range(1, 1 << len(items)):
        yield frozenset(items[i] for i in range(len(items)) if (mask >> i) & 1)


def main() -> int:
    n = 4
    with open(os.path.join(ROOT, "data", "puzzles",
                           "counterexample-4x4-two-answers", "puzzle.json")) as fh:
        puz = json.load(fh)
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}

    print(f"=== the decisive experiment: E=1 -> E=0 in one legal step (4x4) ===")
    cat = Catalogue(n)
    bycell = cat.by_cell
    parts: List[Tuple[int, ...]] = []

    def rec(rem: int, chosen: List[int]):
        if rem == 0:
            parts.append(tuple(chosen))
            return
        first = (rem & -rem).bit_length() - 1
        for m in bycell[first]:
            if m & ~rem:
                continue
            rec(rem ^ m, chosen + [m])

    rec((1 << (n * n)) - 1, [])
    print(f"  {len(parts):,} legal tilings enumerated")

    low: List[Tuple[float, List[State]]] = []
    for part in parts:
        states = [frozenset(cat.cells_of(m)) for m in part]
        e = energy_of(states, hints, n)
        if e <= 1.0:
            low.append((e, states))
            if e == 0.0:
                print(f"    E=0 tiling: sizes {sorted(len(s) for s in states)}")
    print(f"  tilings at E <= 1: {len(low)}")

    if not low:
        print("  no E<=1 tiling found -- the experiment needs the numbers to be tighter")
        return 0

    hits = []
    for e, states in low:
        if e == 0.0:
            continue
        for new_states, kind, detail in neighbours(states, n):
            e2 = energy_of(new_states, hints, n)
            if e2 < e:
                hits.append((kind, detail, e, e2,
                             sorted(len(s) for s in states),
                             sorted(len(s) for s in new_states)))
    print(f"\n  single steps that LOWER the energy: {len(hits)}")
    for kind, detail, e, e2, a, b in hits[:20]:
        print(f"    {kind:6s} {detail:44s} E {e:5.1f} -> {e2:5.1f}   areas {a} -> {b}")
    kinds = {}
    for kind, *_ in hits:
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"\n  by move: {kinds}")
    down = [h for h in hits if h[3] == 0.0]
    print(f"  steps that reach E=0 directly: {len(down)}")
    for kind, detail, e, e2, a, b in down[:10]:
        print(f"    {kind:6s} {detail:44s} areas {a} -> {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
