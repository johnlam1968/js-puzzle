"""M4 regression: the readings-driven AODFS solver.

The solver's contract:
  * it GROWS the tiling (never enumerates candidate states separately);
  * the verdict is three-valued: unique == exhaustive AND exactly one answer;
  * the published numbers are reproduced exactly.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import Puzzle
from solver import Solver, solve_grid


class TestSolverSmallInstances(unittest.TestCase):
    """Small frames where an exhaustive search is cheap."""

    def test_2x2(self):
        # A = {(0,0)} (1x1, its own capitol); B = {(0,1),(1,0),(1,1)} (L-tromino, capitol (1,1))
        puz = Puzzle([{(0, 0)}, {(0, 1), (1, 0), (1, 1)}])
        d = puz.cost_field()
        self.assertEqual([[int(v) for v in row] for row in d], [[0, 1], [1, 0]])
        hints = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
        res = solve_grid(2, hints, budget=200_000)
        self.assertTrue(res["exhaustive"])
        self.assertEqual(res["answers"], [puz.answer()])
        self.assertTrue(res["unique"])
        # several partitions satisfy those four numbers, but they all agree on the answer:
        # uniqueness is an ANSWER-level property (PLAN D20/E1)
        self.assertGreater(res["partitions"], 1)

    def test_2x2_no_capitol_is_not_a_solution(self):
        """Rule 5: a partition with no capitol has no cost field and is not a solution."""
        puz = Puzzle([{(0, 0), (0, 1)}, {(1, 0), (1, 1)}])   # two dominoes, no capitol
        self.assertEqual(puz.capitols, {})
        d = puz.cost_field()
        self.assertTrue(all(v == float("inf") for row in d for v in row))

    def test_budget_exhaustion_is_reported_as_not_unique(self):
        """A budget that runs out must give unique=False, never silently true."""
        s = Solver(2, {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}, budget=1)
        res = s.solve()
        self.assertFalse(res["exhaustive"])
        self.assertFalse(res["unique"])


class TestSolverAnchorRule(unittest.TestCase):
    def test_capitol_anchor_restricts_the_symmetries(self):
        """A d=0 anchor is a capitol, so only symmetries that FIX it can grow its state
        (PLAN rule 23).  Measured on the 4x4 corner: 664 grown states without the
        restriction, 155 with it."""
        from grow import grow_states, symmetry_choices
        from solver import Solver
        s = Solver(4, {(2, 1): 0})
        anchor = (2, 1)
        with_restriction = 0
        for sym in s._syms:
            if anchor not in s._fixed(sym):
                continue
            orb = s._orbits(sym)
            start = orb[anchor]
            if any(c not in s.idx for c in start):
                continue
            with_restriction += len(list(grow_states(anchor, sym, 4)))
        without = 0
        for sym in s._syms:
            orb = s._orbits(sym)
            start = orb[anchor]
            if any(c not in s.idx for c in start):
                continue
            without += len(list(grow_states(anchor, sym, 4)))
        self.assertLess(with_restriction, without)
        self.assertGreater(with_restriction, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
