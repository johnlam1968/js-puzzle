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


class TestSolver4x4Regression(unittest.TestCase):
    """The 4x4 fixture is the one instance with a KNOWN answer (680), so it is the only
    end-to-end regression available for the solver.

    It took 125,534 nodes before the three pruning fixes of the fourth review round
    (tight lower-bound radius, per-anchor state dedupe, capitol-free hints removed from the
    pool of possible capitols); before them the search had not found the answer after
    200,000 nodes."""

    HINTS = {(0, 1): 3, (0, 2): 6, (0, 3): 10, (1, 0): 3, (1, 1): 3, (1, 2): 6, (1, 3): 6,
             (2, 0): 3, (2, 1): 0, (2, 2): 3, (2, 3): 3, (3, 0): 0, (3, 1): 3, (3, 2): 3,
             (3, 3): 0}

    def test_known_answer_680(self):
        res = solve_grid(4, self.HINTS, budget=400_000)
        self.assertIn(680, res["answers"])
        self.assertEqual(res["cardinality"], 1)
        # the partition is unique up to the order of the states
        self.assertEqual(res["partitions"], 1)


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


class TestSolver4x4CounterexampleGate(unittest.TestCase):
    """The performance GATE for the solver.

    data/puzzles/counterexample-4x4-two-answers is the hardest small instance: ALL 16
    cells are hinted, and the same cost field admits TWO different answers (112 and 304).
    It is the measuring stick for every optimisation: if an optimisation changes a verdict,
    or blows the node budget, this test says so.

    The answers are read from the fixture's truth file -- they are not written by hand here.
    """

    def test_all_sixteen_hints_give_the_two_known_answers(self):
        import json
        with open(os.path.join(ROOT, "data", "puzzles",
                               "counterexample-4x4-two-answers", "puzzle.json")) as fh:
            puz = json.load(fh)
        with open(os.path.join(ROOT, "data", "puzzles",
                               "counterexample-4x4-two-answers", "truth.json")) as fh:
            truth = json.load(fh)
        hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
        self.assertEqual(len(hints), 16)
        res = solve_grid(puz["size"], hints, budget=600_000)
        self.assertEqual(sorted(res["answers"]), sorted(truth["answers"]))
        self.assertEqual(res["cardinality"], 2)
        self.assertFalse(res["unique"])


class TestSolver5x5OfficialExample(unittest.TestCase):
    """The SPARSE gate: 10 published numbers on a 5x5 (2 of every 5 cells).

    This is the instance that exposed the real bottleneck.  With 16 of 16 hints (the 4x4)
    the solver needed 206 nodes; with 10 of 25 it found NOTHING in 400,000 nodes until
    the L3/L2 area lower bound went in -- "the state holding a hinted cell must be at
    least |D(x) - D(y)| big" -- which cut the same search to 129,319 nodes and produced
    the official answer.

    The expected answer is read from the fixture's truth file, not written by hand.
    """

    def test_official_example_gives_8045(self):
        import json
        base = os.path.join(ROOT, "data", "puzzles", "official-example-5x5")
        with open(os.path.join(base, "puzzle.json")) as fh:
            puz = json.load(fh)
        with open(os.path.join(base, "truth.json")) as fh:
            truth = json.load(fh)
        hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
        self.assertEqual(len(hints), 10)
        res = solve_grid(puz["size"], hints, budget=2_000_000)
        self.assertEqual(res["answers"], [truth["answer"]])
        self.assertEqual(res["answers"], [8045])
        self.assertTrue(res["exhaustive"])
        self.assertTrue(res["unique"])
        self.assertLess(res["nodes"], 400_000)      # the performance gate
