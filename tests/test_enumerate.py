"""M2 regression: the enumeration constants that the review rounds established.

Every number here was measured independently (author / Verifier / DeepSeek / GLM) and is
reproduced by src/enumerate.py from scratch -- nothing is copied from a fixture.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from tilings import Catalogue, connected_subsets

# 4x4 constants (measured, and reproduced here)
N4_CONNECTED = 11_506
N4_LEGAL_STATES = 1_130
N4_LEGAL_WITH_CAPITOL = 280
N4_SHAPE_TYPES = 640
N4_TILINGS = 562_308
N4_BY_BLOCKS = {1: 1, 2: 79, 3: 674, 4: 4_203, 5: 18_653, 6: 55_516, 7: 108_356,
                8: 139_234, 9: 120_713, 10: 72_574, 11: 30_794, 12: 9_261, 13: 1_949,
                14: 276, 15: 24, 16: 1}
N4_BY_CAPITOLS = {0: 2_723, 1: 11_744, 2: 45_166, 3: 59_320, 4: 126_954, 5: 75_672,
                  6: 126_390, 7: 36_268, 8: 56_637, 9: 7_264, 10: 12_224, 11: 596,
                  12: 1_273, 13: 16, 14: 60, 16: 1}      # 15 is IMPOSSIBLE


class TestConnectedSubsetEnumeration(unittest.TestCase):
    """The ESU-style canonical enumeration must produce every connected subset exactly once."""

    def test_counts(self):
        self.assertEqual(len(connected_subsets(3)), 218)
        self.assertEqual(len(connected_subsets(4)), N4_CONNECTED)

    def test_no_duplicates(self):
        subs = connected_subsets(4)
        self.assertEqual(len(subs), len(set(subs)))


class TestCatalogue4x4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = Catalogue(4)

    def test_catalogue_constants(self):
        self.assertEqual(self.cat.connected_count, N4_CONNECTED)
        self.assertEqual(self.cat.legal_count, N4_LEGAL_STATES)
        self.assertEqual(self.cat.capitol_states, N4_LEGAL_WITH_CAPITOL)
        self.assertEqual(self.cat.shape_type_count, N4_SHAPE_TYPES)

    def test_tilings_and_breakdowns(self):
        res = self.cat.count_tilings(by_blocks=True, by_capitols=True)
        self.assertEqual(res["tilings"], N4_TILINGS)
        self.assertEqual(res["tilings_by_blocks"], N4_BY_BLOCKS)
        self.assertEqual(res["tilings_by_capitols"], N4_BY_CAPITOLS)
        self.assertEqual(res["tilings_without_capitol"], N4_BY_CAPITOLS[0])
        self.assertEqual(res["tilings_with_capitol"], N4_TILINGS - N4_BY_CAPITOLS[0])

    def test_15_capitols_impossible(self):
        """T-B: k = N^2 - 1 capitols is impossible (a capitol-free state needs >= 2 cells)."""
        res = self.cat.count_tilings(by_capitols=True)
        self.assertNotIn(15, res["tilings_by_capitols"])
        self.assertIn(16, res["tilings_by_capitols"])


class TestOddSizeCapitolRule(unittest.TestCase):
    """Only odd-sized states can carry a capitol (PLAN T-A)."""

    def test_every_capitol_state_has_odd_size(self):
        cat = Catalogue(4)
        for m, has_cap, names in cat.states:
            if has_cap:
                size = bin(m).count("1")
                self.assertEqual(size % 2, 1, f"state of size {size} claims a capitol")
                self.assertNotIn(size, (2, 4, 6, 8, 10, 12, 14, 16))


if __name__ == "__main__":
    unittest.main(verbosity=2)
