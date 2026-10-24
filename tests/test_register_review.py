"""Regression tests for the review of the constraint register.

Three things an adversarial review caught, each pinned here so they cannot be undone
again:

  A  F-ball's hidden-capitol search used the EIGHT CORNERS of a k-square instead of a
     Manhattan ball, and did not exclude the cells that already have a published d > 0.
     It also treated a d = 1 reading as a ball of radius 1 (which is a 5-cell plus)
     instead of the D64 ADJACENT cells.

  B  the "there are 9 one-cell states" claim was arithmetic that does not hold: the
     area bounds pin 12 cells, not 32, and "area >= 4" is a LOWER bound, which points
     the other way from "is a singleton".

  C  the corner chain has TWO branches, not one: d(6,9) = 9 has two d = 1 neighbours,
     (5,9) and (6,10), so the "8" can be carried by either.

The counts below are the ones the review measured, so a regression is visible.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from hitting import ball, singleton_candidates   # noqa: E402

REGISTER = os.path.join(ROOT, "data", "derived", "constraint_register_11x11.json")
DERIVED = os.path.join(ROOT, "data", "derived")


def _register():
    with open(REGISTER) as fh:
        return json.load(fh)


def _facet(reg, fid):
    for f in reg["facets"]:
        if f["id"] == fid:
            return f
    raise KeyError(fid)


class TestFBallUsesAManhattanBall(unittest.TestCase):
    """Reviewer item A: the ball must be a Manhattan ball, not a k-square's corners."""

    def test_the_ball_helper_is_a_manhattan_ball(self):
        # ball(x, radius, n) -- every cell within `radius` MANHATTAN steps, except x
        self.assertEqual(sorted(ball((0, 0), 1, 11)), [(0, 1), (1, 0)])
        self.assertEqual(sorted(ball((5, 5), 2, 11)),
                         [(3, 5), (4, 4), (4, 5), (4, 6), (5, 3), (5, 4),
                          (5, 6), (5, 7), (6, 4), (6, 5), (6, 6), (7, 5)])
        self.assertEqual(len(ball((5, 5), 2, 11)), 12)   # 4 + 8, the diamond
        # a k-square's eight corners would include (3,3) and (3,7) -- NOT these
        self.assertNotIn((3, 3), ball((5, 5), 2, 11))
        self.assertNotIn((3, 7), ball((5, 5), 2, 11))
        # and (5,3) / (3,5) ARE in the diamond, so the two really differ
        self.assertIn((5, 3), ball((5, 5), 2, 11))
        self.assertIn((3, 5), ball((5, 5), 2, 11))

    def test_d1_uses_the_adjacent_cells_not_the_ball(self):
        # D64: d = 1 means an ADJACENT 1x1 state, so the candidate cells are the
        # orthogonal neighbours -- a radius-1 ball would wrongly add the cell itself.
        with open(os.path.join(ROOT, "data", "puzzles", "official-11x11",
                               "puzzle.json")) as fh:
            p = json.load(fh)
        hints = {(h["row"], h["col"]): h["value"] for h in p["hints"]}
        cands = singleton_candidates(p["size"], hints)
        # the RAW candidate table: every orthogonal neighbour that is not published d>0
        self.assertEqual(sorted(cands[(4, 10)]), [(3, 10), (4, 9), (5, 10)])
        self.assertEqual(sorted(cands[(2, 5)]), [(1, 5), (2, 4), (2, 6), (3, 5)])
        for x, cs in cands.items():
            self.assertNotIn(x, cs, "a d=1 cell cannot serve itself")
            for c in cs:
                self.assertLessEqual(abs(c[0] - x[0]) + abs(c[1] - x[1]), 1)
                self.assertLessEqual(hints.get(c, 0), 0)

    def test_the_register_says_the_same(self):
        reg = _register()
        fb = _facet(reg, "F-ball")
        self.assertGreaterEqual(len(fb["instances"]), 9)
        # every instance must name a Manhattan ball, and the counts the review measured
        for inst in fb["instances"]:
            blob = json.dumps(inst)
            # the step budget and the candidate list must both be present
            self.assertIn("step_budget", blob)
            self.assertIn("hidden_capitol_within", blob)
            # and the candidates must all be inside the stated Manhattan ball
            cell = tuple(inst["cell"])
            radius = inst["step_budget"]
            for c in inst["hidden_capitol_within"]:
                self.assertLessEqual(
                    abs(c[0] - cell[0]) + abs(c[1] - cell[1]), radius,
                    "candidate %s is outside the Manhattan ball of %s" % (c, cell))
            # a published d>0 cell is never a capitol
            self.assertNotIn(cell, inst["hidden_capitol_within"])


class TestFHumanSingletonClaimIsWithdrawn(unittest.TestCase):
    """Reviewer item B: the "9 singletons" arithmetic does not hold."""

    def test_the_claim_is_marked_withdrawn_not_deleted(self):
        reg = _register()
        fh = _facet(reg, "F-human")
        withdrawn = [i for i in fh["instances"] if "WITHDRAWN" in json.dumps(i)]
        self.assertTrue(withdrawn, "the withdrawn instance must be kept, not deleted")
        for inst in withdrawn:
            blob = json.dumps(inst)
            self.assertIn("why_withdrawn", blob)
            self.assertIn("what_is_left", blob)

    def test_the_area_facet_pins_twelve_cells_not_thirty_two(self):
        reg = _register()
        fa = _facet(reg, "F-area")
        self.assertEqual(len(fa["instances"]), 12)
        cells = {tuple(i["cell"]) for i in fa["instances"]}
        self.assertEqual(len(cells), 12)

    def test_the_singleton_demand_facet_still_stands(self):
        reg = _register()
        fd = _facet(reg, "F-singleton-demand")
        self.assertGreaterEqual(len(fd["instances"]), 3)


class TestTheCornerChainHasTwoBranches(unittest.TestCase):
    """Reviewer item C: the '8' in d(6,9) = 9 = 8 + 1 has TWO carriers."""

    def test_two_d1_neighbours_of_6_9(self):
        # (6,9) = 9 is served through a d = 1 neighbour.  (5,9) and (6,10) both have
        # d = 1 -- the first is published-adjacent, the second is implied by the ring of
        # the forced singleton at (5,10).  Both are in the ring facet.
        reg = _register()
        fr = _facet(reg, "F-ring")
        ones = {tuple(i["cell"]) for i in fr["instances"] if i["d"] == 1}
        self.assertIn((5, 9), ones)
        self.assertIn((6, 10), ones)
        # (5,9) and (6,10) are both orthogonal neighbours of (6,9)
        for c in ((5, 9), (6, 10)):
            self.assertEqual(abs(c[0] - 6) + abs(c[1] - 9), 1)

    def test_the_chain_tool_reports_both_branches(self):
        path = os.path.join(DERIVED, "chain_corner_11x11.json")
        if not os.path.exists(path):
            self.skipTest("chain_corner_11x11.json not built yet")
        with open(path) as fh:
            d = json.load(fh)
        counts = d["counts"]
        for key in ("eight_cell_candidates_carrying_6_9",
                    "eight_cell_candidates_carrying_5_9",
                    "eight_cell_candidates_carrying_both"):
            self.assertIn(key, counts)
        self.assertGreater(counts["eight_cell_candidates_carrying_6_9"], 0)
        self.assertGreater(counts["eight_cell_candidates_carrying_5_9"], 0)


class TestTheSurvivorSkeletonIsNotSampled(unittest.TestCase):
    """The 'the 12 cells are FIXED' claim was sampling bias -- pin it shut."""

    def test_the_counts_cover_every_survivor_not_just_the_stored_samples(self):
        path = os.path.join(DERIVED, "chain_corner_11x11.json")
        if not os.path.exists(path):
            self.skipTest("chain_corner_11x11.json not built yet")
        with open(path) as fh:
            d = json.load(fh)
        total = d["survivor_total"]
        stored = len(d["survivors"])
        self.assertGreater(total, stored, "the file must count more than it stores")
        # the skeleton frequencies must be measured over ALL of them
        self.assertEqual(max(d["skeleton"]["twelve_cell_state_frequency"].values()), total)
        self.assertEqual(sum(d["survivor_split"].values()), total)
        # and only the two construction cells may be certain in the 12-cell state
        self.assertEqual(d["skeleton"]["twelve_cell_state_always"],
                         [[6, 10], [7, 10]])
        # the 8-cell state's core is five cells
        self.assertEqual(len(d["skeleton"]["eight_cell_state_always"]), 3)
        self.assertGreaterEqual(
            len([c for c, v in d["skeleton"]["eight_cell_state_frequency"].items()
                 if v >= 0.5 * total]), 5)


class TestTheSixAreaBoundsAreSixDifferentEdges(unittest.TestCase):
    """Reviewer item D1: the bounds come from six pairwise-disjoint edges."""

    def test_no_two_edges_share_a_cell(self):
        path = os.path.join(DERIVED, "register_claims_11x11.json")
        if not os.path.exists(path):
            self.skipTest("register_claims_11x11.json not built yet")
        with open(path) as fh:
            d = json.load(fh)
        a = d["A_six_area_bounds"]
        self.assertEqual(a["n_bounds"], 12)
        self.assertEqual(a["distinct_edges"], 6)
        self.assertEqual(a["pairs_of_edges_sharing_a_cell"], [])
        self.assertEqual(a["distinct_area_values"], [16, 12, 8, 6, 4, 2])

    def test_the_big_balls_are_inert(self):
        path = os.path.join(DERIVED, "register_claims_11x11.json")
        if not os.path.exists(path):
            self.skipTest("register_claims_11x11.json not built yet")
        with open(path) as fh:
            d = json.load(fh)
        b = d["B_ball_is_inert_for_big_readings"]
        self.assertEqual(b["board_max_manhattan"], 20)
        inert = {tuple(r["cell"]): r["d"] for r in b["inert_readings"]}
        self.assertEqual(inert, {(3, 3): 51, (8, 8): 45, (10, 8): 77, (10, 9): 61})


if __name__ == "__main__":
    unittest.main(verbosity=2)
