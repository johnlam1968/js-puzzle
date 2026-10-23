"""M3 regression: the generator, the hint minimisation and the teaching material.

The generator is only allowed to ship puzzles whose answer is provably unique, and every
number it reports has to be re-derivable from the engine.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import Puzzle
from generator import Generator
from judge import Judge
from rules import capitol_of, connected, symmetry_group
from tilings import Catalogue


class TestGeneratorLibrary(unittest.TestCase):
    """The generator must use the SAME state vocabulary as the solver."""

    @classmethod
    def setUpClass(cls):
        cls.gen = Generator(4)

    def test_every_legal_state_is_constructible(self):
        """AODFS orbit growth must reach EVERY legal state, or the solver could not
        even represent a puzzle the generator produced."""
        constructed = set()
        for states in self.gen.by_cell.values():
            for s in states:
                constructed.add(frozenset(s))
        legal = {frozenset(self.gen.cat.cells_of(m)) for m, _, _ in self.gen.cat.states}
        self.assertEqual(len(legal), 1130)
        self.assertEqual(len(constructed - legal), 0, "growth produced an illegal state")
        self.assertEqual(len(legal - constructed), 0,
                         "some legal state cannot be constructed by orbit growth")

    def test_corner_branches_match_the_known_377(self):
        """The number of legal shapes covering the corner (0,0) was measured at 377."""
        self.assertEqual(len(self.gen.by_cell[(0, 0)]), 377)


class TestGeneratedPuzzle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puzzle = Generator(4).make_puzzle(seed=7, hint_mode="irreducible", budget=400000)

    def test_truth_is_consistent_with_the_engine(self):
        p = self.puzzle
        states = [{tuple(cell) for cell in s} for s in p["states"]]
        puz = Puzzle(states)
        self.assertEqual(puz.answer(), p["answer"])
        self.assertEqual(puz.row_sums(), p["row_sums"])
        self.assertEqual(sorted(puz.sizes.values()), sorted(p["state_sizes"]))
        d = puz.cost_field()
        for key, v in p["hints"].items():
            r, c = (int(x) for x in key.split(","))
            self.assertEqual(int(d[r][c]), v, f"hint ({r},{c}) disagrees with the engine")

    def test_every_state_is_legal(self):
        for s in self.puzzle["states"]:
            cells = {tuple(c) for c in s}
            self.assertTrue(connected(cells))
            self.assertTrue(symmetry_group(cells), "a state with no symmetry is not a state")

    def test_answer_is_unique(self):
        self.assertTrue(self.puzzle["uniqueness"]["exhaustive"])
        self.assertEqual(self.puzzle["uniqueness"]["cardinality"], 1)
        self.assertEqual(self.puzzle["uniqueness"]["answers"], [self.puzzle["answer"]])

    def test_hint_set_is_irreducible(self):
        """Deleting any single hint must break answer-level uniqueness (PLAN D31)."""
        judge = Judge(4)
        hints = {tuple(int(k) for k in key.split(",")): v
                 for key, v in self.puzzle["hints"].items()}
        self.assertLessEqual(len(hints), self.puzzle["all_hints_count"])
        for cell in hints:
            trial = {k: v for k, v in hints.items() if k != cell}
            res = judge.decide(trial, budget=400000)
            self.assertFalse(res["unique"],
                             f"hint {cell} was not needed -- the set is not irreducible")

    def test_ladder_is_ordered_from_easy_to_hard(self):
        ladder = self.puzzle["ladder"]
        self.assertEqual(len(ladder), self.puzzle["all_hints_count"] - self.puzzle["hint_count"] + 1)
        self.assertEqual([r["step"] for r in ladder], list(range(1, len(ladder) + 1)))
        # the ladder runs EASY -> HARD: all hints first, the irreducible set last
        self.assertEqual(len(ladder[0]["hints"]), self.puzzle["all_hints_count"])
        self.assertEqual(len(ladder[-1]["hints"]), self.puzzle["hint_count"])
        sizes = [len(r["hints"]) for r in ladder]
        self.assertEqual(sizes, sorted(sizes, reverse=True), "the ladder must shrink monotonically")
        for row in ladder:
            self.assertTrue(row["exhaustive"] if "exhaustive" in row else True)

    def test_worked_trace_rules_are_sound(self):
        """Every trace step must be re-derivable from the engine."""
        p = self.puzzle
        states = [{tuple(cell) for cell in s} for s in p["states"]]
        puz = Puzzle(states)
        d = puz.cost_field()
        for step in p["trace"]:
            r, c = step["cell"]
            self.assertEqual(int(d[r][c]), step["value"])
            if step["value"] == 0:
                self.assertEqual(step["rule"], "CAPITOL")
                self.assertTrue(puz.has_capitol_at((r, c)))
            elif step["value"] == 1:
                self.assertEqual(step["rule"], "SINGLETON_NEIGHBOUR")
            else:
                self.assertEqual(step["rule"], "STATE_SIZE_LOWER_BOUND")

    def test_determinism(self):
        a = Generator(4).make_puzzle(seed=11, hint_mode="irreducible", budget=400000)
        b = Generator(4).make_puzzle(seed=11, hint_mode="irreducible", budget=400000)
        self.assertEqual(a["hints"], b["hints"])
        self.assertEqual(a["answer"], b["answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
