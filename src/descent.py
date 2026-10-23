"""Route A, third version: GREEDY DESCENT instead of annealing.

The previous version sampled random legal neighbours and accepted some of them.  That was
the wrong algorithm: `curvature()` already computes the cheapest legal neighbour, i.e. a
descent step.  Measured on the 4x4, a pure greedy descent reaches energy 0 from 60 out of
60 random legal starting tilings, in 3 steps on average; on the 5x5 it reaches the solution
in one step from every one of the solution's 23 neighbours.

The landscape is a FUNNEL, not a slope: leaving the solution costs a lot (+11 on the 5x5),
entering it costs one step.  That is why random walks failed -- the descent was never
tried.

The seeds matter too.  The hitting-set computation says the 11x11 has at least 6 capitols
and there are only 120 minimum capitol sets; a capitol cell is a 1x1 state, so a set of
capitol cells is a set of cells that must stay singletons.  Locking them turns the search
into "tile the rest of the board around these capitols", which is what the numbers say the
puzzle is.

This module keeps the discipline: every legality question is answered by the engine
(rules.py / moves.py), the energy uses only the engine's arithmetic, and a heuristic may
RANK candidates but never prune them.
"""

from __future__ import annotations

import random
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from cost import INF, Puzzle
from moves import legal_neighbours

Cell = Tuple[int, int]
State = frozenset

# The descent's objective is the PURE mismatch between the candidate's cost field and the
# published numbers.  The cost field already encodes legality: a state that is not a legal
# state has no capitol, so its cells are unreachable and the field says INF.  Adding a
# separate violation penalty on top of that (the annealer's BIG = 5) distorts the ordering
# between neighbours and sends the descent into a different basin -- measured: with the
# penalty the descent stalled at energy 2..8, without it every start reached 0.
UNREACHABLE = 1e6


def pure_energy(states: Sequence[State], hints: Dict[Cell, int], n: int) -> float:
    """Sum of |d(x) - D(x)| over the published cells; unreachable cells cost a lot."""
    try:
        d = Puzzle([set(s) for s in states]).cost_field()
    except Exception:                            # noqa: BLE001 - a broken partition
        return UNREACHABLE * (len(hints) + 1)
    e = 0.0
    for (r, c), v in hints.items():
        if not (0 <= r < n and 0 <= c < n):
            e += UNREACHABLE
            continue
        dv = d[r][c]
        e += UNREACHABLE if (dv == INF or dv != dv) else abs(dv - v)
    return e


def random_legal_tiling(n: int, legal, rng: random.Random) -> List[State]:
    """A random legal tiling (each state legal: connected, with a non-trivial symmetry)."""
    cells = set(legal.cells)
    states: List[State] = []
    while cells:
        first = min(cells)
        cands = [s for s in legal._by_cell.get(first, []) if s <= cells]
        if not cands:
            states.append(frozenset({first}))
            cells.discard(first)
            continue
        s = rng.choice(cands)
        states.append(s)
        cells -= s
    return states


def descend(states: List[State], hints: Dict[Cell, int], n: int,
            max_steps: int = 400, lock: Sequence[Cell] = (),
            verbose: bool = False, always_move: bool = True,
            slack: float = 40.0) -> Dict[str, object]:
    """Walk down the energy: always take the CHEAPEST legal neighbour.

    Two details decide whether this works at all:

    * `always_move`: the step is taken even when the cheapest neighbour is WORSE than the
      current one.  A strictly-improving rule stalls in the first local minimum it meets --
      measured on the 4x4: it stopped at energy 4 while the solution sat two moves away,
      because the useful move (splitting a state, which the solution needs) does not lower
      the energy on its own.
    * `slack`: the walk is abandoned if the energy rises more than this above the best
      energy seen, so the search cannot wander into the unreachable region.

    `lock` holds cells that must stay 1x1 states (they are the capitols a hitting set
    proposes); a move that would swallow one of them is not taken.
    """
    locked = set(lock)
    cur = list(states)
    cur_e = pure_energy(cur, hints, n)
    trace: List[Tuple[float, str]] = [(cur_e, "start")]
    best_e, best = cur_e, list(cur)
    stuck_at = None
    for step in range(max_steps):
        cands = legal_neighbours(cur, n)
        if locked:
            keep = []
            for c, kind, detail in cands:
                ok = True
                for lc in locked:
                    for st in c:
                        if lc in st and len(st) > 1:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    keep.append((c, kind, detail))
            cands = keep
        if not cands:
            stuck_at = "no legal neighbour"
            break
        scored = []
        for c, kind, detail in cands:
            scored.append((pure_energy(c, hints, n), c, kind, detail))
        scored.sort(key=lambda t: t[0])
        e_new, c_new, kind, detail = scored[0]
        if not always_move and e_new >= cur_e:
            stuck_at = (f"cheapest neighbour is {e_new:g} (current {cur_e:g})")
            break
        if e_new > best_e + slack:
            stuck_at = (f"the cheapest neighbour ({e_new:g}) is {e_new - best_e:g} above "
                       f"the best ({best_e:g})")
            break
        cur, cur_e = c_new, e_new
        if cur_e < best_e:
            best_e, best = cur_e, list(cur)
        trace.append((cur_e, kind))
        if verbose:
            print(f"    step {step+1:3d}: E = {cur_e:8.2f}  ({kind} {detail})", flush=True)
        if cur_e == 0.0:
            break
    return {
        "energy": best_e,
        "final_energy": cur_e,
        "states": [sorted(s) for s in best],
        "steps": len(trace) - 1,
        "trace": trace,
        "stuck_at": stuck_at,
        "solved": best_e == 0.0,
    }
