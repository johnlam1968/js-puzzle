"""End-to-end regression on the official 5x5 example + the invariant checks.

Ground truth (independently reproduced by author / Verifier / DeepSeek-V4.1-Flash):
  states of size 7 / 4 / 3 / 11, capitols at (3,2) (3,4) (5,5) 1-based,
  the 2x2 state has NO capitol, row sums [37,29,31,43,55], answer 8045.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import Puzzle, check_L1, check_L2, check_L3, check_L5, is_metric
from rules import partition_of

DATA = os.path.join(ROOT, "data", "puzzles")

EXAMPLE_STATES = [
    [0, 1, 1, 3, 3],
    [0, 1, 1, 2, 3],
    [0, 0, 2, 2, 3],
    [3, 0, 0, 0, 3],
    [3, 3, 3, 3, 3],
]
PUBLISHED = {(0, 0): 12, (0, 4): 17, (1, 0): 8, (1, 2): 6, (1, 3): 3,
             (3, 1): 7, (3, 2): 6, (3, 4): 10, (4, 0): 25, (4, 4): 0}
PUBLISHED_D_FIELD = [[12, 8, 10, 6, 17],
                     [8, 4, 6, 3, 6],
                     [7, 0, 3, 0, 3],
                     [14, 7, 6, 3, 10],
                     [25, 14, 13, 10, 0]]


class TestOfficialExample(unittest.TestCase):
    def setUp(self):
        self.puz = Puzzle(partition_of(EXAMPLE_STATES))
        self.d = self.puz.cost_field()

    def test_state_sizes(self):
        self.assertEqual(sorted(self.puz.sizes.values()), [3, 4, 7, 11])

    def test_capitols_exactly(self):
        caps = sorted((r + 1, c + 1) for (r, c) in self.puz.capitols.values())
        self.assertEqual(caps, [(3, 2), (3, 4), (5, 5)])

    def test_2x2_state_has_no_capitol(self):
        # state 1 is the 2x2 block
        self.assertEqual(self.puz.sizes[1], 4)
        self.assertNotIn(1, self.puz.capitols)

    def test_published_numbers_reproduced(self):
        for (r, c), v in PUBLISHED.items():
            self.assertEqual(self.d[r][c], v, f"d({r+1},{c+1})")

    def test_full_d_field(self):
        for r in range(5):
            for c in range(5):
                self.assertEqual(self.d[r][c], PUBLISHED_D_FIELD[r][c])

    def test_row_sums_and_answer(self):
        self.assertEqual(self.puz.row_sums(), [37, 29, 31, 43, 55])
        self.assertEqual(self.puz.answer(), 8045)

    def test_checksum_invariant(self):
        ck = self.puz.checksum()
        self.assertEqual(ck["sum_row_sums"], ck["sum_state_sizes_squared"])
        self.assertEqual(ck["sum_row_sums"], 195)

    def test_lemmas_hold_on_the_example(self):
        self.assertEqual(check_L1(self.puz, self.d), [])
        self.assertEqual(check_L2(self.puz, self.d), [])
        self.assertEqual(check_L3(self.puz, self.d), [])
        self.assertEqual(check_L5(self.puz, self.d), [])

    def test_dist_is_a_metric(self):
        self.assertTrue(is_metric(self.puz))


class TestFixturesAgreeWithTheEngine(unittest.TestCase):
    """data/ must be reproducible from the engine, not hand-written (PLAN D37)."""

    def test_official_example_fixture(self):
        with open(os.path.join(DATA, "official-example-5x5", "truth.json")) as fh:
            t = json.load(fh)
        puz = Puzzle(partition_of(t["states"]))
        self.assertEqual(puz.answer(), t["answer"])
        self.assertEqual(puz.row_sums(), t["row_sums"])
        self.assertEqual(sorted(puz.sizes.values()), sorted(t["state_sizes"]))
        # capitols / state_capitol are 0-based (same coordinate space as states and d_field)
        caps = sorted(puz.capitols.values())
        self.assertEqual(caps, sorted(tuple(x) for x in t["capitols"]))
        d = puz.cost_field()
        self.assertEqual([[int(x) for x in row] for row in d], t["d_field"])

    def test_counterexample_fixture_gives_two_answers(self):
        with open(os.path.join(DATA, "counterexample-4x4-two-answers", "truth.json")) as fh:
            t = json.load(fh)
        answers = []
        dfs = []
        for alt in t["alternative_partitions"]:
            puz = Puzzle(partition_of(alt["states"]))
            answers.append(puz.answer())
            dfs.append(puz.cost_field())
            self.assertEqual(puz.answer(), alt["answer"])
        self.assertEqual(answers, [304, 112])
        self.assertEqual(dfs[0], dfs[1])          # same cost field, different answers

    def test_11x11_numbers_are_consistent(self):
        with open(os.path.join(DATA, "official-11x11", "puzzle.json")) as fh:
            p = json.load(fh)
        n = p["size"]
        self.assertEqual(len(p["grid"]), n)
        self.assertTrue(all(len(r) == n for r in p["grid"]))
        cnt = sum(1 for row in p["grid"] for v in row if v is not None)
        self.assertEqual(cnt, 33)
        self.assertEqual(cnt, p["hint_count"])
        for h in p["hints"]:
            self.assertEqual(p["grid"][h["row"]][h["col"]], h["value"])
        zeros = sorted((h["row"], h["col"]) for h in p["hints"] if h["value"] == 0)
        self.assertEqual(zeros, [(5, 7), (10, 5)])   # 0-based == (6,8),(11,6) 1-based


if __name__ == "__main__":
    unittest.main(verbosity=2)
