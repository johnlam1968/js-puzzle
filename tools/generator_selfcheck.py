#!/usr/bin/env python3
"""Generator self-check: build a puzzle, then re-verify it from scratch.

This is the gate that catches a generator that produces a puzzle it cannot itself solve:
the states are re-read from the published truth, the cost field is recomputed by the
engine, the answer is recomputed, and the solver is asked whether the published hints
really pin that answer down.

Exit code 0 = all checks passed.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from cost import Puzzle                                    # noqa: E402
from generator import Generator                             # noqa: E402
from solver import solve_grid                               # noqa: E402

ok = True


def chk(cond, msg):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    ok = ok and bool(cond)


def main() -> int:
    g = Generator(4)
    puz = g.make_puzzle(7)

    # 1. the published states still produce the published answer
    # the generator publishes the states as a list of cell lists, and the hints as a
    # { "row,col": value } map
    p = Puzzle([{tuple(c) for c in st} for st in puz["states"]])
    chk(p.answer() == puz["answer"], f"answer {puz['answer']} reproduced by the engine "
                                      f"(got {p.answer()})")
    chk(p.row_sums() == puz["row_sums"], "row sums reproduced by the engine")

    # 2. the published hints are the d values of the published grid
    d = p.cost_field()
    if isinstance(puz["hints"], dict):
        hints = {tuple(int(x) for x in k.split(",")): v for k, v in puz["hints"].items()}
    else:
        hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    chk(all(0 <= r < puz["size"] and 0 <= c < puz["size"] for r, c in hints),
        "every published hint is 0-based and on the board")
    chk(all(int(d[r][c]) == v for (r, c), v in hints.items()),
        "every published hint equals the cost field of the published partition")

    # 3. the solver, given only the hints, finds the answer back
    res = solve_grid(puz["size"], hints, budget=400_000)
    chk(puz["answer"] in res["answers"],
        f"the solver recovers the answer {puz['answer']} from the hints alone "
        f"(got {res['answers']})")
    chk(res["unique"] is True, "the published hints pin the answer down uniquely "
                                f"(verdict: {res['answers']}, exhaustive={res['exhaustive']})")

    # 4. the trace is not empty and mentions the rules it claims to apply
    chk(len(puz["trace"]) > 0, f"the worked trace has {len(puz['trace'])} steps")
    chk(any(s.get("rule") for s in puz["trace"]), "the trace names the rule it applies")

    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
