"""The judge has TWO paths: the offline table (fast) and the DFS search.

The table path was masking a broken search path: a signature change in `_lb_violates` made
the search raise a TypeError on the first node, and every test still passed because the 4x4
always used the table.  These tests run the SEARCH path explicitly and check that it agrees
with the table.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from judge import Judge

HINTS_4X4 = {(0, 1): 3, (0, 2): 6, (0, 3): 10, (1, 0): 3, (1, 1): 3, (1, 2): 6, (1, 3): 6,
             (2, 0): 3, (2, 1): 0, (2, 2): 3, (2, 3): 3, (3, 0): 0, (3, 1): 3, (3, 2): 3,
             (3, 3): 0}


class TestJudgeSearchPath(unittest.TestCase):
    def test_search_path_finds_the_same_answer_as_the_table(self):
        search = Judge(4, use_table=False, lazy=False).decide(HINTS_4X4, budget=800_000)
        self.assertEqual(search["answers"], [680])
        self.assertTrue(search["exhaustive"])
        self.assertTrue(search["unique"])
        self.assertEqual(search["source"], "search")

    def test_truncated_library_reports_unknown_instead_of_crashing(self):
        j = Judge(6, use_table=False, lazy=True)
        j.cat.budget = 1                       # force the on-demand generation to truncate
        res = j.decide({(0, 0): 0}, budget=1000)
        self.assertFalse(res["exhaustive"])
        self.assertFalse(res["unique"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
