"""Tests for src/grow.py -- the AODFS orbit-growth machinery.

These were missing when an adversarial code review found a wrong rot90/rot270 map in
grow.py (the file had no test at all, so the bug was invisible).  Every symmetry in
`symmetry_choices` must now be checked for the algebraic properties that define it.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from grow import close_state, grow_states, orbits_of, symmetry_choices
from rules import capitol_of, connected, symmetry_group


def apply_n(sym, cell, times):
    for _ in range(times):
        cell = sym.apply(cell)
    return cell


class TestSymmetryChoices(unittest.TestCase):
    def setUp(self):
        self.n = 4
        self.syms = symmetry_choices(self.n)

    def test_every_symmetry_is_a_bijection(self):
        """Bijectivity must be checked on the LATTICE, not on the board: a quarter turn about
        a centre near the border sends some board cells off the board (geometrically
        correct) and so is not a bijection of the board."""
        big = [(r, c) for r in range(-self.n, 2 * self.n) for c in range(-self.n, 2 * self.n)]
        for sym in self.syms:
            img = [sym.apply(c) for c in big]
            self.assertEqual(len(set(img)), len(big), f"{sym} is not injective on the lattice")

    def test_reflections_are_involutions(self):
        for sym in self.syms:
            if sym.name.startswith("ref"):
                for c in [(r, cc) for r in range(self.n) for cc in range(self.n)]:
                    self.assertEqual(apply_n(sym, c, 2), c, f"{sym} is not an involution")

    def test_rot180_is_an_involution(self):
        for sym in self.syms:
            if sym.name == "rot180":
                for c in [(r, cc) for r in range(self.n) for cc in range(self.n)]:
                    self.assertEqual(apply_n(sym, c, 2), c)

    def test_rot90_has_order_four_and_rot270_is_its_inverse(self):
        cells = [(r, cc) for r in range(self.n) for cc in range(self.n)]
        r90 = {s.params: s for s in self.syms if s.name == "rot90"}
        r270 = {s.params: s for s in self.syms if s.name == "rot270"}
        self.assertEqual(set(r90), set(r270))
        for params, s in r90.items():
            t = r270[params]
            for c in cells:
                self.assertEqual(apply_n(s, c, 4), c, "rot90 must have order 4")
                self.assertEqual(t.apply(s.apply(c)), c, "rot270 must invert rot90")
                self.assertEqual(s.apply(t.apply(c)), c)

    def test_rot90_fixed_point_is_the_centre(self):
        """A 90 turn may only fix the centre cell (and only if the centre is a cell)."""
        cells = [(r, cc) for r in range(self.n) for cc in range(self.n)]
        for s in [x for x in self.syms if x.name in ("rot90", "rot270")]:
            fixed = {c for c in cells if s.apply(c) == c}
            self.assertLessEqual(len(fixed), 1, f"{s} fixes more than one cell")

    def test_reflection_axis_passes_through_its_fixed_cells(self):
        for s in [x for x in self.syms if x.name in ("refD1", "refD2")]:
            fixed = {c for c in [(r, cc) for r in range(self.n) for cc in range(self.n)]
                     if s.apply(c) == c}
            if s.name == "refD1":
                self.assertTrue(all(r - cc == s.params[0] for (r, cc) in fixed))
            else:
                self.assertTrue(all(r + cc == s.params[0] for (r, cc) in fixed))


class TestGrowStates(unittest.TestCase):
    def test_grown_states_are_connected_orbit_unions(self):
        n = 4
        for sym in symmetry_choices(n):
            for anchor in [(0, 0), (1, 2), (2, 2)]:
                for st in grow_states(anchor, sym, n):
                    # the state must be invariant under the growth symmetry
                    self.assertEqual({sym.apply(c) for c in st}, set(st),
                                     "grown state is not sigma-invariant")

    def test_connectivity_is_only_required_at_closure(self):
        """D68: the first orbit of a state can be DISCONNECTED (the anti-diagonal L-tromino
        starts from {(0,0),(1,1)}), so connectivity must be checked when the state is
        closed, not at every intermediate step."""
        n = 3
        found = set()
        for s in symmetry_choices(n):
            for st in grow_states((0, 0), s, n):
                found.add(frozenset(st))
        self.assertIn(frozenset({(0, 0), (0, 1), (1, 1)}), found)

    def test_growth_finds_the_known_small_states(self):
        n = 3
        syms = {s.name + str(s.params): s for s in symmetry_choices(n)}
        # the L-tromino {(0,0),(0,1),(1,0)} is symmetric about the main diagonal
        found = []
        for s in symmetry_choices(n):
            for st in grow_states((0, 0), s, n):
                found.append(frozenset(st))
        self.assertIn(frozenset({(0, 0), (0, 1), (1, 0)}), found)
        self.assertIn(frozenset({(0, 0), (0, 1), (1, 1)}), found)

    def test_close_state_uses_the_full_point_group(self):
        # a 1x3 bar: the vertical reflection fixes one cell, the horizontal one fixes three
        legal, cap, names = close_state({(0, 0), (0, 1), (0, 2)})
        self.assertTrue(legal)
        self.assertIsNone(cap)
        self.assertEqual(len(names), 3)

    def test_close_state_rejects_shapeless_sets(self):
        legal, cap, names = close_state({(0, 0), (1, 1)})     # disconnected
        self.assertFalse(legal)
        legal, cap, names = close_state({(0, 0), (1, 0), (2, 0), (2, 1)})   # L-tetromino: no symmetry
        self.assertFalse(legal)
        self.assertIsNone(cap)


if __name__ == "__main__":
    unittest.main(verbosity=2)
