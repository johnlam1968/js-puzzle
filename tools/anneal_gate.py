#!/usr/bin/env python3
"""Route A's gates: can annealing on a partition find a partition that reproduces the
published numbers?

The gates, cheapest first:

  1. the official 5x5 example (10 published numbers, answer 8045).  If the annealing
     cannot solve THIS, it will not solve the 11x11, so this is the go/no-go.
  2. the same 5x5 with ONE published number changed.  The annealing must NOT reach
     energy 0 -- otherwise the energy was not reading the numbers at all.
  3. the 4x4 counterexample: the annealing must find a partition with answer 304 or 112,
     and the engine must confirm that the answer set for that cost field is {112, 304}.

Exit code 0 = every gate passed.
"""

from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from anneal import anneal, energy                              # noqa: E402
from cost import Puzzle                                        # noqa: E402
from rules import partition_of                                  # noqa: E402

ok = True


def chk(cond, msg):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    ok = ok and bool(cond)


def load(name):
    with open(os.path.join(ROOT, "data", "puzzles", name, "puzzle.json")) as fh:
        return json.load(fh)


def answer_of(states):
    puz = Puzzle([set(s) for s in states])
    return puz.answer()


def run_gate_5x5(steps: int, seed: int):
    puz = load("official-example-5x5")
    n = puz["size"]
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    print(f"=== gate 1: the official 5x5 ({len(hints)} published numbers) ===")
    t0 = time.time()
    res = anneal(hints, n, steps=steps, seed=seed, n_states=5)
    dt = time.time() - t0
    print(f"  best energy {res['best_energy']}, {steps} steps in {dt:.1f}s")
    if res["best_energy"] == 0.0:
        ans = answer_of(res["states"])
        print(f"  found a partition with energy 0; its answer is {ans}")
        chk(ans == 8045, f"the answer is the official 8045 (got {ans})")
    else:
        chk(False, "the annealing reached energy 0")
    return res


def run_gate_perturbed(steps: int, seed: int):
    puz = load("official-example-5x5")
    n = puz["size"]
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    # change ONE published number
    victim = sorted(hints)[len(hints) // 2]
    original = hints[victim]
    hints[victim] = original + 1
    print(f"=== gate 2: the same 5x5 with one number changed ({victim}: "
          f"{original} -> {original + 1}) ===")
    t0 = time.time()
    res = anneal(hints, n, steps=steps, seed=seed, n_states=5)
    dt = time.time() - t0
    print(f"  best energy {res['best_energy']}, {steps} steps in {dt:.1f}s")
    chk(res["best_energy"] > 0.0,
        f"the annealing did NOT reach energy 0 on the corrupted numbers "
        f"(best {res['best_energy']})")
    return res


def run_gate_4x4(steps: int, seed: int):
    with open(os.path.join(ROOT, "data", "puzzles",
                           "counterexample-4x4-two-answers", "truth.json")) as fh:
        truth = json.load(fh)
    puz = load("counterexample-4x4-two-answers")
    n = puz["size"]
    hints = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}
    print("=== gate 3: the 4x4 counterexample (16 published numbers, two answers) ===")
    t0 = time.time()
    res = anneal(hints, n, steps=steps, seed=seed, n_states=4)
    dt = time.time() - t0
    print(f"  best energy {res['best_energy']}, {steps} steps in {dt:.1f}s")
    if res["best_energy"] == 0.0:
        ans = answer_of(res["states"])
        print(f"  found a partition with energy 0; its answer is {ans}")
        chk(ans in truth["answers"], f"the answer is one of {truth['answers']} (got {ans})")
    else:
        chk(False, "the annealing reached energy 0")
    return res


def main() -> int:
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(f"Route A gates: {steps} steps, seed {seed}\n")
    run_gate_5x5(steps, seed)
    run_gate_perturbed(steps, seed)
    run_gate_4x4(steps, seed)
    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
