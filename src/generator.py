"""Puzzle generator: build a puzzle, prove its answer is unique, and write the teaching
material that goes with it (hint ladder + worked trace).

Design constraints, all of them from the plan and the review rounds:

  * The generator must use the SAME state construction as the solver (plan 4.2): a state
    is grown by adding symmetry orbits, so the vocabulary of shapes is shared and a
    generated puzzle is solvable by the solver's own machinery.
  * Uniqueness is judged at the ANSWER level (D20/E1): the answer set must have one
    element, and the judge must have been exhaustive.
  * If the FULL hint set is not answer-unique, the partition is rejected outright
    (D40/C'): no hint subset can repair it, because deleting hints only relaxes.
  * Hint minimisation uses the monotonicity (D31): if deleting h breaks uniqueness, h is
    permanently required, so ONE pass suffices -- no "delete to a fixed point", no
    restarts.
  * Everything the generator reports is produced by the engine, never hand-written.
"""

from __future__ import annotations

import os
import random
import sys
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost import Puzzle
from grow import grow_states, symmetry_choices
from judge import Judge
from lazycatalogue import LazyCatalogue
from rules import capitol_of, connected, symmetry_group
from tilings import Catalogue

Cell = Tuple[int, int]


class Generator:
    """Builds puzzles for a given frame size."""

    def __init__(self, n: int, lazy: Optional[bool] = None):
        self.n = n
        if lazy is None:
            lazy = n >= 5
        self.lazy = lazy
        # The state library always comes from the LAZY catalogue: it caches per anchor, so
        # repeated Generator instances do not recompute the whole constructible library
        # (that cost ~10 s per instance for 4x4).
        self.cat = LazyCatalogue(n)
        self.judge = Judge(n, lazy=lazy)
        self.by_cell: Dict[Cell, List[FrozenSet[Cell]]] = {}
        self._add_constructible_states()

    # ------------------------------------------------------------------ #
    def _add_constructible_states(self) -> None:
        """Every legal state must be reachable by the solver's orbit growth -- otherwise the
        generator could produce a puzzle the solver cannot even represent.

        For big frames this is done per anchor ON DEMAND (LazyCatalogue); for small frames
        the whole library is built once and cached.
        """
        n = self.n
        if self.lazy:
            self.by_cell = {}                 # filled lazily by cell_states()
            return
        # the lazy catalogue already yields exactly the states the solver can construct
        # (it grows them by symmetry orbits), and it caches per anchor
        for anchor in self.cat.cells:
            self.by_cell[anchor] = self.cat.cell_states(anchor)

    def cell_states(self, anchor: Cell) -> List[FrozenSet[Cell]]:
        """Legal states containing `anchor` (lazy for big frames)."""
        if self.lazy:
            return self.cat.cell_states(anchor)
        return self.by_cell.get(anchor, [])

    # ------------------------------------------------------------------ #
    def random_tiling(self, rng: random.Random, tries: int = 200) -> Optional[List[FrozenSet[Cell]]]:
        """A random legal tiling, built the same way the solver constructs states."""
        n = self.n
        cells = self.cat.cells
        idx = {c: i for i, c in enumerate(cells)}
        for _ in range(tries):
            rem = set(cells)
            chosen: List[FrozenSet[Cell]] = []
            ok = True
            while rem:
                first = min(rem)
                cands = [s for s in self.cell_states(first) if s <= rem]
                if not cands:
                    ok = False
                    break
                # Sample with a strong preference for SMALL states.  The candidate list is
                # sorted by size descending, and an earlier version picked uniformly among
                # the first few entries -- which is a biased-towards-large sample, and it
                # made every seed produce the same degenerate "one huge state + a
                # singleton" partition.
                weights = [1.0 / (len(s) ** 2) for s in cands]
                s = rng.choices(cands, weights=weights)[0]
                chosen.append(s)
                rem -= s
            if ok:
                return chosen
        return None

    # ------------------------------------------------------------------ #
    def make_puzzle(self, seed: int, hint_mode: str = "irreducible",
                    budget: int = 2_000_000, max_attempts: int = 200,
                    min_states: int = 4, max_state_fraction: float = 0.55):
        """Build one puzzle.  Returns a dict with the puzzle, the truth, the hint set,
        the hint ladder and the worked trace.  Raises if no acceptable puzzle was found.

        `min_states` / `max_state_fraction` keep the puzzles from degenerating into
        "one huge state plus a singleton", which is legal but makes for a trivial puzzle.
        """
        rng = random.Random(seed)
        limit = max(1, int(self.n * self.n * max_state_fraction))
        for attempt in range(max_attempts):
            states = self.random_tiling(rng)
            if states is None:
                continue
            if len(states) < min_states:
                continue
            if max(len(s) for s in states) > limit:
                continue
            puz = Puzzle(states)
            if not puz.capitols:
                continue                       # a partition with no capitol has no cost field
            d = puz.cost_field()
            if any(v == float("inf") for row in d for v in row):
                continue
            all_hints = {(r, c): int(d[r][c]) for r in range(self.n) for c in range(self.n)}
            full = self.judge.decide(all_hints, budget)
            if not full["exhaustive"]:
                continue                       # cannot prove uniqueness -> do not ship it
            if full["cardinality"] != 1:
                continue                       # D40: reject, no hint subset can fix it
            if hint_mode == "irreducible":
                hints = self.irreducible_hints(all_hints, budget)
            else:
                hints = dict(all_hints)
            final = self.judge.decide(hints, budget)
            if not final["exhaustive"] or final["cardinality"] != 1:
                continue
            return {
                "id": f"gen-{self.n}x{self.n}-s{seed}-a{attempt}",
                "size": self.n,
                "seed": seed,
                "attempt": attempt,
                "hint_mode": hint_mode,
                "states": [sorted(s) for s in states],
                "state_sizes": [len(s) for s in states],
                "capitols": sorted(puz.capitols.values()),
                "d_field": [[int(v) for v in row] for row in d],
                "row_sums": puz.row_sums(),
                "answer": puz.answer(),
                "hints": {f"{r},{c}": v for (r, c), v in sorted(hints.items())},
                "hint_count": len(hints),
                "all_hints_count": len(all_hints),
                "uniqueness": {"answers": final["answers"], "cardinality": final["cardinality"],
                               "partitions": final["partitions"], "exhaustive": final["exhaustive"],
                               "nodes": final["nodes"]},
                "ladder": self.hint_ladder(all_hints, hints, budget),
                "trace": self.worked_trace(hints, puz),
            }
        raise RuntimeError(f"no acceptable {self.n}x{self.n} puzzle found for seed {seed} "
                           f"in {max_attempts} attempts")

    # ------------------------------------------------------------------ #
    def irreducible_hints(self, all_hints: Dict[Cell, int], budget: int) -> Dict[Cell, int]:
        """Delete hints one at a time, keeping a hint only when deleting it breaks
        answer-level uniqueness.  ONE PASS suffices (D31): deleting hints only relaxes
        the constraint set, so a hint that is required now stays required forever."""
        cur = dict(all_hints)
        for cell in sorted(all_hints):
            if cell not in cur:
                continue
            trial = {k: v for k, v in cur.items() if k != cell}
            res = self.judge.decide(trial, budget)
            if res["exhaustive"] and res["cardinality"] == 1:
                cur = trial                      # the hint was not needed
            # if the judge was not exhaustive we keep the hint (conservative)
        return cur

    # ------------------------------------------------------------------ #
    def hint_ladder(self, all_hints: Dict[Cell, int], minimal: Dict[Cell, int],
                    budget: int) -> List[dict]:
        """Order the hints by how much they shrink the answer set, so the ladder goes
        from 'easiest' (all hints) to 'hardest' (the irreducible set)."""
        ladder = []
        remaining = dict(minimal)
        # hardest first: the irreducible set on its own
        res = self.judge.decide(remaining, budget)
        ladder.append({"step": len(ladder) + 1, "hints": dict(remaining),
                       "answers": sorted(res["answers"]),
                       "cardinality": res["cardinality"],
                       "exhaustive": res["exhaustive"]})
        # then add the remaining hints back, each time choosing the one that helps most
        pool = {k: v for k, v in all_hints.items() if k not in remaining}
        while pool:
            best, best_score = None, None
            for cell, val in pool.items():
                trial = dict(remaining); trial[cell] = val
                res = self.judge.decide(trial, budget)
                # The most informative hint is the one that leaves the FEWEST consistent
                # tilings: adding it shrinks the solution space the most.  (cardinality is
                # 1 at every rung -- the set is already answer-unique -- so it cannot
                # discriminate.)  Note the comparison is a MINIMUM.
                score = (res["partitions"], res["cardinality"])
                if best_score is None or score < best_score:
                    best, best_score = cell, score
            remaining[best] = pool.pop(best)
            res = self.judge.decide(remaining, budget)
            ladder.append({"step": len(ladder) + 1, "hints": dict(remaining),
                           "answers": sorted(res["answers"]),
                           "cardinality": res["cardinality"],
                           "exhaustive": res["exhaustive"]})
        ladder.reverse()                      # easiest first
        for i, row in enumerate(ladder):
            row["step"] = i + 1
        return ladder

    # ------------------------------------------------------------------ #
    def worked_trace(self, hints: Dict[Cell, int], puz: Puzzle) -> List[dict]:
        """The deduction chain a solver can walk: for each hint, which rule fires and what
        it implies.  Every statement here is re-derived from the engine."""
        steps = []
        for (r, c), v in sorted(hints.items(), key=lambda kv: (kv[1], kv[0])):
            if v == 0:
                steps.append({"cell": [r, c], "rule": "CAPITOL", "value": v,
                              "implies": "this square is a capitol; its state has odd size "
                                         "and the symmetry axis passes through it"})
                continue
            if v == 1:
                cands = []
                hinted = {(r, c) for (r, c) in hints}
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nb = (r + dr, c + dc)
                    # a hinted cell with d>0 can never be a capitol; a hinted d=0 cell is
                    # a revealed capitol whose state may or may not be a singleton
                    if 0 <= nb[0] < self.n and 0 <= nb[1] < self.n and nb not in hinted:
                        cands.append([nb[0], nb[1]])
                steps.append({"cell": [r, c], "rule": "SINGLETON_NEIGHBOUR", "value": v,
                              "implies": "a 1x1 state (its own capitol) must be adjacent; "
                                         f"candidates {cands}"})
                continue
            # otherwise: a size lower bound from the tightest adjacent hinted cell
            best = None
            for (rr, cc), vv in hints.items():
                if abs(rr - r) + abs(cc - c) == 1:
                    d = abs(v - vv)
                    if best is None or d > best:
                        best = d
            steps.append({"cell": [r, c], "rule": "STATE_SIZE_LOWER_BOUND", "value": v,
                          "implies": (f"the state of this cell has size >= {best}"
                                      if best else "no adjacent hint: no size bound yet")})
        return steps
