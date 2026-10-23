"""Rule-kernel truth table + the regressions that adversarial reviews demanded."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from rules import (capitol_of, connected, is_legal_state, shape_key, symmetry_group,
                   partition_of, label_matrix)

# ---------------------------------------------------------------- shapes ----
SINGLE = {(0, 0)}
DOMINO = {(0, 0), (0, 1)}
BAR3 = {(0, 0), (0, 1), (0, 2)}
BAR4 = {(0, 0), (0, 1), (0, 2), (0, 3)}
SQUARE4 = {(0, 0), (0, 1), (1, 0), (1, 1)}
T_TETROMINO = {(0, 0), (0, 1), (0, 2), (1, 1)}
S_TETROMINO = {(0, 1), (0, 2), (1, 0), (1, 1)}
L_TETROMINO = {(0, 0), (1, 0), (2, 0), (2, 1)}
X_PENTOMINO = {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}
U_PENTOMINO = {(0, 0), (0, 2), (1, 0), (1, 1), (1, 2)}
W_PENTOMINO = {(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)}


class TestTruthTable(unittest.TestCase):
    """The truth table from the plan, with expectations (PLAN D3)."""

    def test_capitol_bearing_shapes(self):
        self.assertEqual(capitol_of(SINGLE), (0, 0))          # 1x1: capitol is itself
        self.assertEqual(capitol_of(U_PENTOMINO), (1, 1))     # U: vertical reflection fixes 1
        self.assertEqual(capitol_of(W_PENTOMINO), (1, 1))     # W: diagonal reflection fixes 1

    def test_legal_states_without_capitol(self):
        for name, shape in (("1x2", DOMINO), ("1x3", BAR3), ("1x4", BAR4), ("2x2", SQUARE4),
                            ("T", T_TETROMINO), ("S", S_TETROMINO), ("X", X_PENTOMINO)):
            with self.subTest(shape=name):
                self.assertTrue(is_legal_state(shape), f"{name} must be a legal state")
                self.assertIsNone(capitol_of(shape), f"{name} must have NO capitol")

    def test_L_tetromino_is_not_a_state(self):
        """L has no symmetry at all: it is NOT a capitol-less state, it is not a state."""
        self.assertEqual(symmetry_group(L_TETROMINO), {})
        self.assertFalse(is_legal_state(L_TETROMINO))

    def test_official_examples_have_no_capitol(self):
        """The official page says a 1x3 region and the X pentomino have no capitol."""
        self.assertIsNone(capitol_of(BAR3))
        self.assertIsNone(capitol_of(X_PENTOMINO))

    def test_full_point_group_is_used(self):
        """PLAN D55: the capitol rule quantifies over the FULL group, not one symmetry.

        A 1x3 bar has a vertical reflection that fixes exactly the middle cell -- but its
        horizontal reflection fixes all three.  Checking only one symmetry would wrongly
        award a capitol at the middle cell.
        """
        group = symmetry_group(BAR3)
        self.assertEqual(sorted(group), ["refH", "refV", "rot180"])
        self.assertEqual(len(group["refV"]), 1)      # would-be capitol
        self.assertEqual(len(group["refH"]), 3)      # disqualifies the state
        self.assertEqual(len(group["rot180"]), 1)   # the middle cell is fixed by rot180 too
        self.assertIsNone(capitol_of(BAR3))

    def test_no_floating_point(self):
        """PLAN D1 (BLOCKER): the official example's 3-cell state has centroid (5/3, 8/3).

        Under IEEE754 double precision rbar-cbar = -0.9999999999999998, the reflection
        test fails and the capitol silently disappears.  The integer conditions must
        keep it.
        """
        green = {(1, 3), (2, 2), (2, 3)}      # the official green L-tromino, 0-based
        self.assertEqual(capitol_of(green), (2, 3))
        self.assertIn("refD1", symmetry_group(green))

    def test_shape_key_normalises_translation(self):
        self.assertEqual(shape_key({(2, 2), (2, 3), (3, 2)}), shape_key({(0, 0), (0, 1), (1, 0)}))

    def test_connectivity_is_orthogonal_only(self):
        self.assertFalse(connected({(0, 0), (1, 1)}))
        self.assertTrue(connected({(0, 0), (1, 0)}))


class TestLabelMatrixRoundTrip(unittest.TestCase):
    def test_roundtrip(self):
        states = [{(0, 0), (0, 1)}, {(1, 0)}, {(1, 1), (2, 0)}, {(2, 1)}]
        m = label_matrix(states)
        back = partition_of(m)
        self.assertEqual(sorted(map(sorted, back)), sorted(map(sorted, states)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
