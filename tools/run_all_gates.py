#!/usr/bin/env python3
"""Run every gate of this repository, in one place, and fail if any of them fails.

A gate that nobody calls is not a gate.  `tools/check_contract.py` had a non-zero exit
code for months and nothing ever ran it; when the judge's search path was broken by a
signature change, 62 tests stayed green because the 4x4 always used the offline table.
CI would have caught both.

Gates (all must exit 0):
  1. the data contract  -- fixtures agree with the engine, coordinates are 0-based
  2. the test suite    -- rules, growth, lemmas, generator, solver, regressions
  3. the generator     -- a fresh puzzle can be built and re-verified end to end
  4. the candidate validator -- a known-good partition still validates

Usage:  python3 tools/run_all_gates.py [--quick]
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PY = sys.executable


def run(name: str, argv: list, timeout: int = 1800) -> bool:
    print(f"\n=== {name} ===", flush=True)
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=ROOT, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout}s")
        return False
    out = p.stdout or ""
    tail = out.strip().splitlines()[-12:]
    for line in tail:
        print("  " + line)
    dt = time.time() - t0
    print(f"  -> exit {p.returncode} in {dt:.1f}s")
    # the exit code is the verdict; the log is only there to explain it
    return p.returncode == 0


GATES = [
    ("every python file compiles (py_compile over the whole tree)",
     [PY, "tools/compile_all.py"], 300),
    ("data contract (fixtures vs engine, 0-based coordinates)",
     [PY, "tools/check_contract.py"], 600),
    ("test suite",
     [PY, "-m", "unittest", "discover", "-s", "tests", "-q"], 1800),
    ("generator self-check (build a puzzle, re-verify it)",
     [PY, "tools/generator_selfcheck.py"], 900),
    ("candidate validator self-test",
     [PY, "tools/validate.py", "--selftest"], 600),
    ("the 11x11's 33 numbers, re-derived from the source image",
     [PY, "tools/verify_11x11_numbers.py"], 300),
    ("the 11x11 capitol bound: the engine against data/derived/",
     [PY, "tools/capitol_bound_11x11.py"], 300),
    ("the reviewers' claims, re-verified against the engine",
     [PY, "tools/verify_reviews.py"], 300),
]


def main() -> int:
    quick = "--quick" in sys.argv
    gates = GATES[:2] if quick else GATES
    results = []
    for name, argv, timeout in gates:
        results.append((name, run(name, argv, timeout)))
    print("\n" + "=" * 72)
    bad = [n for n, ok in results if not ok]
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("=" * 72)
    if bad:
        print(f"RESULT: {len(bad)} GATE(S) FAILED")
        return 1
    print("RESULT: ALL GATES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
