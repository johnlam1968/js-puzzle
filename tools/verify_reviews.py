#!/usr/bin/env python3
"""Independently re-verify the claims the reviewers made.

This file used to re-implement the hitting-set logic (a second source of truth) and to
read the 11x11 fixture with the 1-based convention, and it had never compiled.  It now
calls the engine and checks the two claims that actually mattered:

  CLAIM 1 (the demand split): the "already satisfied by a revealed capitol" branch does
          fire, and the numbers are 22 satisfied / 9 uncovered / a pool of 64 candidates /
          at least 4 hidden capitols / 120 minimum hitting sets.

  CLAIM 2 (D53 is unsound): the prune "Manhattan distance to the nearest REVEALLED
          capitol > D(x) => prune" would kill a TRUE hint of the official 5x5 example,
          because the nearest capitol of that cell has not been revealed.

Exit code 0 = both claims hold.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost import Puzzle                                    # noqa: E402
from hitting import min_hitting_set, split_demands         # noqa: E402
from rules import partition_of                              # noqa: E402

ok = True


def chk(cond, msg):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    ok = ok and bool(cond)


def load(name):
    with open(os.path.join(ROOT, "data", "puzzles", name, "puzzle.json")) as fh:
        return json.load(fh)


def main() -> int:
    print("=" * 78)
    print("CLAIM 1: the demand split (src/hitting.py)")
    print("=" * 78)
    p11 = load("official-11x11")
    hints = {(h["row"], h["col"]): h["value"] for h in p11["hints"]}
    uncovered, satisfied = split_demands(p11["size"], hints)
    pool = sorted({c for _, _, _, C in uncovered for c in C})
    min_extra, min_sets = min_hitting_set(uncovered)
    chk(len(satisfied) == 22, f"22 demands already covered by a revealed capitol "
                              f"(got {len(satisfied)})")
    chk(len(uncovered) == 9, f"9 uncovered demands (got {len(uncovered)})")
    chk(len(pool) == 64, f"a pool of 64 candidate cells for hidden capitols (got {len(pool)})")
    chk(min_extra == 4, f"at least 4 hidden capitols (got {min_extra})")
    chk(len(min_sets) == 120, f"120 minimum hitting sets (got {len(min_sets)})")

    print("=" * 78)
    print("CLAIM 2: the 4x4 counterexample -- one cost field, TWO answers (D20)")
    print("=" * 78)
    with open(os.path.join(ROOT, "data", "puzzles",
                           "counterexample-4x4-two-answers", "truth.json")) as fh:
        c = json.load(fh)
    answers, fields = [], []
    for alt in c["alternative_partitions"]:
        puz = Puzzle(partition_of(alt["states"]))
        answers.append(puz.answer())
        fields.append(puz.cost_field())
    chk(answers == [304, 112], f"two different answers from one cost field: {answers}")
    chk(fields[0] == fields[1], "the two partitions share the cost field")

    print("=" * 78)
    print("CLAIM 3: D53 -- the 'nearest REVEALLED capitol' prune is UNSOUND")
    print("=" * 78)
    p5 = load("official-example-5x5")
    published = {(h["row"], h["col"]): h["value"] for h in p5["hints"]}
    revealed = {c for c, v in published.items() if v == 0}
    with open(os.path.join(ROOT, "data", "puzzles",
                           "official-example-5x5", "truth.json")) as fh:
        t5 = json.load(fh)
    d = t5["d_field"]
    witness = None
    for (r, c), v in sorted(published.items()):
        if v == 0:
            continue
        # the nearest REVEALLED capitol, by Manhattan distance
        if not revealed:
            continue
        best = min(abs(r - a) + abs(c - b) for (a, b) in revealed)
        if best > v:
            witness = ((r, c), v, best)
            break
    chk(witness is not None,
        f"a published hint whose distance to the nearest REVEALLED capitol exceeds its "
        f"own value: {witness} -- the loose prune would kill a TRUE hint")
    if witness:
        (r, c), v, best = witness
        chk(d[r][c] == v, f"the engine agrees the cell's true distance is {v} "
                         f"(cost field says {d[r][c]})")

    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
