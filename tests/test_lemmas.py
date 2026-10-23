"""Lemma bank + the counter-examples that adversarial reviews forced us to find.

Every case in this file corresponds to a numbered defect in PLAN.md, so a regression can
never be silently undone again.
"""

import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import (Puzzle, capitol_neighbour_bound, check_L1, check_L2, check_L3, check_L5,
                   foreign_capitol_violations, high_d_cells, is_metric)
from hitting import capitol_lower_bound
from rules import capitol_of, is_legal_state, partition_of, symmetry_group

EXAMPLE_STATES = [
    [0, 1, 1, 3, 3],
    [0, 1, 1, 2, 3],
    [0, 0, 2, 2, 3],
    [3, 0, 0, 0, 3],
    [3, 3, 3, 3, 3],
]


def random_partition(n, rng, tries=400):
    """A random partition of the n x n grid into legal states (or None)."""
    cells = [(r, c) for r in range(n) for c in range(n)]
    from rules import connected, symmetry_group
    legal = []
    # enumerate legal states by growing connected sets, then exact-cover at random
    states_by_cell = {c: [] for c in cells}
    for m in range(1, 1 << (n * n)):
        s = [cells[i] for i in range(n * n) if (m >> i) & 1]
        if not connected(s):
            continue
        if not symmetry_group(s):
            continue
        for c in s:
            states_by_cell[c].append(frozenset(s))
    for _ in range(tries):
        rem = set(cells)
        chosen = []
        ok = True
        while rem:
            first = min(rem)
            cands = [s for s in states_by_cell[first] if s <= rem]
            if not cands:
                ok = False
                break
            s = rng.choice(cands)
            chosen.append(s)
            rem -= s
        if ok:
            return chosen
    return None


class TestLemmas(unittest.TestCase):
    def test_lemmas_on_random_partitions(self):
        rng = random.Random(20261023)
        for n in (3, 4):
            for _ in range(25):
                parts = random_partition(n, rng)
                if parts is None:
                    continue
                puz = Puzzle(parts)
                d = puz.cost_field()
                if not puz.capitols:
                    continue          # a capitol-less partition makes every check vacuous
                self.assertEqual(check_L1(puz, d), [], f"L1 broken on {parts}")
                self.assertEqual(check_L2(puz, d), [], f"L2 broken on {parts}")
                self.assertEqual(check_L3(puz, d), [], f"L3 broken on {parts}")
                self.assertEqual(check_L5(puz, d), [], f"L5 broken on {parts}")
                self.assertTrue(is_metric(puz))

    def test_L3_needs_the_neighbour_qualifier(self):
        """PLAN D21: L3 is false if 'y' ranges over all cells.

        1x3 row: single-cell capitol at (0,0), one 1x2 dead state at (0,1),(0,2).
        d = [0, 1, 3].  For x=(0,0) and the NON-neighbour y=(0,2): |0-3| = 3 > size_x = 1.
        """
        puz = Puzzle([{(0, 0)}, {(0, 1), (0, 2)}])
        d = puz.cost_field()
        self.assertEqual(d[0], [0, 1, 3])
        self.assertEqual(check_L3(puz, d), [])          # over neighbours it holds
        self.assertGreater(abs(d[0][0] - d[0][2]), puz.sizes[0])   # over all cells it fails


class TestE1EqualityIsNotATheorem(unittest.TestCase):
    """PLAN E1: w(x, c) = d(x) is NOT a theorem; only min(s_x, s_c) >= d(x) is.

    Witness (2x2):
      S0 = {(0,0)}                  single cell  -> capitol
      S1 = {(0,1),(1,0),(1,1)}      L-tromino    -> capitol (1,1)
    x = (0,1):  d(x) = 1 (one step into the 1x1 state, cost min(3,1)=1)
               but w(x, (1,1)) = 3 (same state, size 3)  >  d(x)
    """
    def setUp(self):
        self.puz = Puzzle([{(0, 0)}, {(0, 1), (1, 0), (1, 1)}])
        self.d = self.puz.cost_field()

    def test_witness(self):
        self.assertEqual(capitol_of({(0, 1), (1, 0), (1, 1)}), (1, 1))
        self.assertEqual(self.d[0][1], 1)
        self.assertEqual(self.puz.step_cost((0, 1), (1, 1)), 3)   # w(x, c) = 3
        self.assertGreater(self.puz.step_cost((0, 1), (1, 1)), self.d[0][1])

    def test_corrected_bound_holds(self):
        """The usable statement is min(s_x, s_c) >= d(x)."""
        x = (0, 1)
        bound = capitol_neighbour_bound(self.puz, self.d, x)
        self.assertIsNotNone(bound)
        self.assertGreaterEqual(bound, self.d[x[0]][x[1]])


class TestD53ManhPruneIsUnsound(unittest.TestCase):
    """PLAN D53: 'Manh(x, nearest REVEALLED capitol) > D(x) => prune' kills the true solution.

    In the official example the only REVEALLED capitol is (5,5); the hint (2,4)=3 has its true
    capitol at (3,4), which is not revealed.  The rule therefore fires on a true hint.
    """
    def setUp(self):
        self.puz = Puzzle(partition_of(EXAMPLE_STATES))
        self.d = self.puz.cost_field()
        self.revealed = {(4, 4)}                      # 0-based: only (5,5) is revealed

    def test_rule_fires_on_a_true_hint(self):
        x = (1, 3)                                     # the hint (2,4)=3, 0-based
        self.assertEqual(self.d[1][3], 3)
        m = min(abs(x[0] - a) + abs(x[1] - b) for (a, b) in self.revealed)
        self.assertGreater(m, 3)                       # the unsound rule would prune
        self.assertTrue(self.puz.has_capitol_at((2, 3)))   # ...but the true capitol is there

    def test_correct_usable_constraint_is_existence_only(self):
        """The sound global statement is on the other side: a capitol EXISTS nearby."""
        x = (1, 3)
        radius = (self.d[1][3] + 1) // 2
        near = [c for c in self.puz.neighbours(x) if self.puz.has_capitol_at(c)]
        self.assertTrue(near)                           # a capitol is adjacent
        self.assertLessEqual(radius, 2)


class TestM4DominantState(unittest.TestCase):
    """PLAN D58 (corrected): 2*d(x) > N^2  =>  any capitol adjacent to x is in x's OWN state,
    so x's state covers more than half the board.

    The first wording ("x cannot be adjacent to ANY capitol") is false: a capitol in x's own
    state is possible.  The test below pins the corrected statement.
    """

    def test_on_the_official_example(self):
        puz = Puzzle(partition_of(EXAMPLE_STATES))
        d = puz.cost_field()
        self.assertEqual(foreign_capitol_violations(puz, d), [])
        # the official example DOES have high-d cells, and none of them touches a
        # foreign-state capitol
        self.assertTrue(high_d_cells(puz, d))

    def test_on_random_partitions(self):
        rng = random.Random(7)
        for n in (3, 4):
            for _ in range(15):
                parts = random_partition(n, rng)
                if parts is None:
                    continue
                puz = Puzzle(parts)
                d = puz.cost_field()
                self.assertEqual(foreign_capitol_violations(puz, d), [])

    def test_same_state_capitol_is_allowed(self):
        """The counter-example that killed the first wording.

        A cell with 2*d(x) > N^2 CAN be adjacent to a capitol -- as long as that capitol lies
        in x's OWN state.  We search for a genuine case and pin it.
        """
        rng = random.Random(7)
        found = None
        for n in (3, 4):
            for _ in range(60):
                parts = random_partition(n, rng)
                if parts is None:
                    continue
                puz = Puzzle(parts)
                d = puz.cost_field()
                for x in high_d_cells(puz, d):
                    for y in puz.neighbours(x):
                        if puz.has_capitol_at(y):
                            self.assertEqual(puz.owner[y[0]][y[1]], puz.owner[x[0]][x[1]],
                                             "the adjacent capitol must be in x's own state")
                            found = (n, x, y, d[x[0]][x[1]])
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                break
        self.assertIsNotNone(found, "expected to find a same-state-capitol counter-example")
        n, x, y, dv = found
        self.assertGreater(2 * dv, n * n)
        self.assertEqual(foreign_capitol_violations(Puzzle(parts), d), [])


class TestHittingSetNumbers(unittest.TestCase):
    """PLAN D52 / V25: the corrected 11x11 capitol lower bound.

    22 of the 31 non-zero hints are already covered by the two revealed capitols,
    leaving 9 real demands over a 64-cell pool; minimum 4 hidden capitols;
    120 minimum hitting sets; so the solution has at least 6 capitols.
    """
    def test_numbers(self):
        import json
        with open(os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")) as fh:
            p = json.load(fh)
        n = p["size"]
        hints = {(h["row"], h["col"]): h["value"] for h in p["hints"]}   # already 0-based
        rep = capitol_lower_bound(n, hints)
        self.assertEqual(rep["hints"], 33)
        self.assertEqual(len(rep["revealed_capitols"]), 2)
        self.assertEqual(rep["satisfied_by_revealed"], 22)
        self.assertEqual(rep["uncovered_demands"], 9)
        self.assertEqual(rep["candidate_pool"], 64)
        self.assertEqual(rep["min_additional_capitols"], 4)
        self.assertEqual(rep["n_minimum_sets"], 120)
        self.assertEqual(rep["total_capitols_lower_bound"], 6)
        # pin the EXACT demand list: it was hand-transcribed wrong once (PLAN D60),
        # so the list must live in code, not in prose.
        from hitting import split_demands
        unc, sat = split_demands(n, hints)
        self.assertEqual(sorted((r + 1, c + 1) for (r, c), _, _, _ in unc),
                         [(1, 2), (1, 3), (1, 6), (1, 10), (3, 3), (3, 6), (4, 7), (5, 11), (7, 1)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
