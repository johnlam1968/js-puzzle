#!/usr/bin/env python3
"""Local curvature of a known solution: how expensive is the cheapest step away?

The annealing route (Route A of docs/NEXT-APPROACHES.md) needs to know which *regime* it is
in before it burns a long run:

  gentle -- the cheapest neighbour of the solution costs E <= 1.  A hill-climb with a small
            kick can climb it (measured: the 4x4 reaches E = 0 in 79 s).
  cliff  -- the cheapest neighbour costs E >= 10.  The low-energy basin around the solution
            is tiny, so a hill-climb has nothing to climb.  Allowing the search to get
            worse is NOT enough (measured: a tolerance sweep on the 5x5 never got past
            E = 50) -- what the landscape needs is a jump in the RIGHT direction, and the
            cheapest legal neighbour is the best the local arithmetic can offer.

This tool measures that curvature.  It needs no offline table and no exhaustive oracle: it
takes a known solution, lists its legal neighbours, and evaluates the energy of each.  The
energy is the one the annealer uses: the sum over the published cells of |d_T(x) - D(x)|.

THE MOVE SET IS NOT DEFINED HERE.  It comes from `src/moves.py`, which is the single
implementation shared by the tool and the annealer -- one move set, one source of truth.
If that module is missing, this tool refuses to run rather than quietly growing a second
copy of the rules.

Usage:
    python3 tools/local_curvature.py                      # the 4x4 and the 5x5 fixtures
    python3 tools/local_curvature.py --depth 2            # also look two steps out
    python3 tools/local_curvature.py --puzzle official-example-5x5
    python3 tools/local_curvature.py --json               # machine-readable only

Exit code 0 = the measurement ran.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:
    from cost import Puzzle                       # noqa: E402
    from rules import connected, symmetry_group  # noqa: E402
except ImportError as exc:                        # pragma: no cover
    sys.stderr.write(f"cannot import the rule engine: {exc}\n")
    raise SystemExit(1)

try:
    # THE one move set.  Do not re-implement it here.
    from moves import legal_neighbours, curvature  # noqa: E402
except ImportError as exc:
    sys.stderr.write(
        "src/moves.py is missing or does not expose legal_neighbours()/curvature().\n"
        "The move set must have exactly one implementation (the engine is the only source of\n"
        "truth), so this tool refuses to grow its own.  Fetch src/moves.py from main and retry.\n")
    raise SystemExit(1)


# --------------------------------------------------------------------------- #
# the energy (the annealer's energy, unchanged)
# --------------------------------------------------------------------------- #
def make_energy(hints):
    def energy(states):
        try:
            puz = Puzzle([frozenset(s) for s in states])
        except Exception:
            return None
        if not puz.capitols:
            return None
        d = puz.cost_field()
        total = 0
        for (r, c), v in hints.items():
            dv = d[r][c]
            if dv == float("inf"):
                return None
            total += abs(int(dv) - v)
        return total
    return energy


def states_from_matrix(matrix, n):
    labels = sorted({matrix[r][c] for r in range(n) for c in range(n)})
    return [frozenset((r, c) for r in range(n) for c in range(n) if matrix[r][c] == lab)
            for lab in labels]


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def measure(label, solution, hints, n, depth=2):
    energy = make_energy(hints)
    e0 = energy(solution)
    if e0 is None:
        return {"solution": label, "error": "the solution's cost field is undefined"}

    cur = curvature(solution, energy, n)
    cur = dict(cur) if isinstance(cur, dict) else {"value": cur}

    # `gap` is the curvature: the cheapest neighbour's energy (0 when a neighbour is
    # ANOTHER solution -- the two 4x4 answers are one split/merge apart).
    gap = cur.get("gap")
    cheapest = cur.get("cheapest")
    neighbours = cur.get("neighbours")

    # Two steps out: how small is the low-energy basin?
    # NOTE: the minimum must be taken over the states REACHED, never over a set that
    # includes the solution itself -- the solution has E = 0 and would make every
    # "minimum" read as 0.
    two_step = None
    if depth >= 2:
        start = _key(solution)
        one_step = legal_neighbours(solution, n)
        seen = {_key(st) for st in one_step}
        best1 = None
        for st in one_step:
            e = energy(list(st))
            if e is not None and (best1 is None or e < best1):
                best1 = e
        best2 = None
        for st in one_step:
            for st2 in legal_neighbours(list(st), n):
                k = _key(st2)
                if k in seen or k == start:
                    continue
                seen.add(k)
                e = energy(list(st2))
                if e is not None and (best2 is None or e < best2):
                    best2 = e
        two_step = {"states_reached": len(seen), "lowest_energy_one_step": best1,
                    "lowest_energy_two_steps": best2}

    # the regime, and what the landscape suggests the search should accept
    if gap is not None and gap <= 1:
        classification = "gentle"
        recommended = {"accept": "hill-climb", "tolerance": 0,
                       "note": "a small kick is enough; the cheapest neighbour is within reach"}
    elif gap is not None and gap >= 10:
        classification = "cliff"
        recommended = {"accept": "best-neighbour", "tolerance": int(gap),
                       "note": "a tolerance alone does not work (measured on the 5x5); the search "
                               "needs a jump in the right direction -- the cheapest legal "
                               "neighbour is the best the local arithmetic can offer"}
    else:
        classification = "in-between"
        recommended = {"accept": "hill-climb-with-kick", "tolerance": int(gap or 0)}

    out = {
        "solution": label,
        "energy": e0,
        "gap": gap,
        "cheapest_neighbour_energy": cheapest,
        "neighbours": neighbours,
        "neighbour_convention": "src/moves.py legal_neighbours(): peel + split + merge over "
                                "legal states, counting DISTINCT resulting tilings",
        "cheapest_move": cur.get("cheapest_move"),
        "classification": classification,
        "recommended": recommended,
        "two_step": two_step,
        "state_sizes": sorted(len(s) for s in solution),
    }
    return out


def _key(states):
    return tuple(sorted((frozenset(s) for s in states), key=lambda z: sorted(z)))


def load(pid):
    puz = json.load(open(os.path.join(ROOT, "data", "puzzles", pid, "puzzle.json")))
    truth = json.load(open(os.path.join(ROOT, "data", "puzzles", pid, "truth.json")))
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    return puz, truth, hints


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--puzzle", default=None,
                    help="puzzle id under data/puzzles (default: both fixtures)")
    ap.add_argument("--depth", type=int, default=2, help="how many steps out to look (default 2)")
    ap.add_argument("--json", action="store_true", help="print only the JSON")
    args = ap.parse_args()

    results = []
    if args.puzzle:
        puz, truth, hints = load(args.puzzle)
        n = puz["size"]
        if "alternative_partitions" in truth:
            for part in truth["alternative_partitions"]:
                results.append(measure(
                    f"{args.puzzle}: {part['name']} (answer {part['answer']})",
                    states_from_matrix(part["states"], n), hints, n, args.depth))
        else:
            results.append(measure(
                f"{args.puzzle} (answer {truth.get('answer')})",
                states_from_matrix(truth["states"], n), hints, n, args.depth))
    else:
        puz, truth, hints = load("counterexample-4x4-two-answers")
        for part in truth["alternative_partitions"]:
            results.append(measure(
                f"4x4 {part['name']} (answer {part['answer']})",
                states_from_matrix(part["states"], 4), hints, 4, args.depth))
        puz, truth, hints = load("official-example-5x5")
        results.append(measure(
            f"5x5 official example (answer {truth.get('answer')})",
            states_from_matrix(truth["states"], 5), hints, 5, args.depth))

    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
