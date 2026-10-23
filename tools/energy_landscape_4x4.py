#!/usr/bin/env python3
"""Gate 0 for the annealing route: is the solution an ISLAND in the energy landscape?

The annealing route (Route A) searches over partitions, scoring them by how far their
cost field is from the published numbers.  Before writing an annealer, the cheap question
is: does the energy landscape even have a path to the solution?

If the true solution is an island -- if every other partition costs a lot more -- then an
annealer is a lottery ticket, not a method, and the whole route should be dropped.  If
there is a cheap neighbourhood of low-energy partitions leading towards it, the annealer
has something to climb.

This is measured on the 4x4, where EVERY legal tiling is known (562,308 of them, of which
559,585 carry a capitol) -- an exhaustive oracle for the energy function.

It reports:
  * the energy distribution (how many tilings at each energy),
  * the gap: the lowest energy among the partitions that do NOT match the numbers,
  * which answers the near-miss partitions carry -- because a near miss with a DIFFERENT
    answer would be a trap: the annealer would happily stop there.

Exit code 0 = the measurement ran.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from tiletable import load_table                   # noqa: E402


def main() -> int:
    n = 4
    with open(os.path.join(ROOT, "data", "puzzles",
                           "counterexample-4x4-two-answers", "puzzle.json")) as fh:
        puz = json.load(fh)
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    print(f"=== Gate 0: the energy landscape of every legal 4x4 tiling ===")
    print(f"    published numbers: {len(hints)} cells, values "
          f"{sorted(set(hints.values()))}")

    table = load_table(n)
    if table is None:
        print("  the offline tiling table is missing or stale; build it first")
        return 1
    fields, answers, kept = table
    print(f"    {len(fields):,} tilings in the table ({kept:,} kept)")

    # the energy of every tiling: the sum of |d - D| over the published cells
    d = np.array([hints[(r, c)] for (r, c) in hints], dtype=np.int64)
    cols = np.array([r * n + c for (r, c) in hints], dtype=np.int64)
    e = np.abs(fields[:, cols].astype(np.int64) - d[None, :]).sum(axis=1)

    print("\n  energy distribution:")
    hist = Counter(e.tolist())
    for energy in sorted(hist)[:14]:
        mark = ""
        if energy == 0:
            mark = "   <- the solutions (E = 0)"
        print(f"    E = {energy:3d}: {hist[energy]:>8,} tilings{mark}")
    if len(hist) > 14:
        print(f"    ... {len(hist) - 14} more distinct energies, "
              f"the largest is {max(hist)} with {hist[max(hist)]:,} tilings")

    zeros = int((e == 0).sum())
    print(f"\n  tilings that reproduce the published numbers exactly: {zeros:,}")
    ans0 = Counter(int(a) for a, ee in zip(answers, e) if ee == 0)
    print(f"  their answers: {dict(ans0)}")

    for budget in (1, 2, 3, 5, 10, 20, 50):
        sel = (e > 0) & (e <= budget)
        cnt = int(sel.sum())
        if cnt:
            ans = Counter(int(a) for a, ee in zip(answers, e) if ee == 0 or (0 < ee <= budget))
            distinct = len(ans)
            wrong = sum(v for k, v in ans.items() if k not in (112, 304))
            print(f"  near misses with 0 < E <= {budget:3d}: {cnt:>8,}"
                  f"   {distinct} distinct answers, {wrong} tilings with an answer"
                  f" that is NOT one of the two solutions")
    gap = int(e[e > 0].min()) if (e > 0).any() else None
    print(f"\n  the gap: the lowest energy among the NON-solutions is {gap}")
    if gap is not None and gap <= 5:
        print("  => there IS a low-energy neighbourhood: an annealer has a gradient to "
              "climb, and the route is worth building.")
    else:
        print("  => the solutions are ISOLATED: every other tiling costs much more, so "
              "an annealer would be a lottery ticket.  Do not build the annealer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
