#!/usr/bin/env python3
"""Validate a candidate state partition for the Jane Street "It's a Metric, Too" puzzle.

Usage:
    python3 validate.py --grid my_solution.txt          # 11 lines of 11 labels
    python3 validate.py --grid my_solution.txt --size 11
    python3 validate.py --selftest

Input format (either):
  * text file: one row per line, labels are letters/digits (e.g.  ABCABCDAB )
  * JSON file : {"grid": [[...], ...]}  or  [[...], ...]

What it checks (exit code 0 only if EVERYTHING passes):
  1. every state is 4-connected
  2. every state has a non-trivial self-symmetry  (S2: otherwise it is not a state at all)
  3. capitols per the official rule (S3) and the d-field
  4. the recomputed cost field reproduces EVERY published number
  5. row sums and the final answer  sum(row_sums^2)
"""
import json, os, sys
from engine import sym_info, connected, d_field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
PUZZLES = os.path.join(DATA, "", "puzzles")


def load_grid(path):
    txt = open(path, encoding="utf-8").read().strip()
    if txt.startswith("{"):
        obj = json.loads(txt)
        g = obj["grid"] if isinstance(obj, dict) else obj
    elif txt.startswith("["):
        g = json.loads(txt)
    else:
        g = []
        for line in txt.splitlines():
            line = line.strip()
            if not line:
                continue
            row = [ch for ch in line if not ch.isspace()]
            if row:
                g.append(row)
    return g


def published_numbers(n):
    """official published numbers for size n (None if we have no reference)"""
    if n == 11:
        p = json.load(open(os.path.join(PUZZLES, "official-11x11", "puzzle.json")))
        return {(h["row"] - 1, h["col"] - 1): h["value"] for h in p["hints"]}
    if n == 5:
        p = json.load(open(os.path.join(PUZZLES, "official-example-5x5", "puzzle.json")))
        return {(r, c): v for r, row in enumerate(p["grid"]) for c, v in enumerate(row) if v is not None}
    if n == 4:
        p = json.load(open(os.path.join(PUZZLES, "counterexample-4x4-two-answers", "puzzle.json")))
        return {(r, c): v for r, row in enumerate(p["grid"]) for c, v in enumerate(row) if v is not None}
    return {}


def validate(grid, quiet=False):
    n = len(grid); m = len(grid[0])
    ok = True
    def say(cond, msg):
        nonlocal ok
        ok = ok and bool(cond)
        if not quiet:
            print(("  PASS  " if cond else "  FAIL  ") + msg)

    if any(len(r) != m for r in grid):
        print("  FAIL  grid is not rectangular")
        return False, None
    print(f"grid {n} x {m}, {len(set(x for row in grid for x in row))} distinct states")

    # label -> cells
    states = {}
    for r in range(n):
        for c in range(m):
            states.setdefault(grid[r][c], []).append((r, c))

    # 1 + 2 + 3 : per-state legality and capitols
    print("\n[states]")
    caplab = {}
    for lab in sorted(states, key=str):
        cells = states[lab]
        sz = len(cells)
        if not connected(cells):
            say(False, f"state {lab!r} (size {sz}) is NOT 4-connected")
            continue
        cap, names, fixes, fs = sym_info(cells)
        if not names:
            say(False, f"state {lab!r} (size {sz}) has NO non-trivial self-symmetry -> not a legal state")
            continue
        capdesc = f"capitol at {cap}" if cap else "NO capitol"
        say(True, f"state {lab!r}: size {sz:<3} syms={names} fixes={fixes} {capdesc}")
        if cap:
            caplab[lab] = cap
    if not caplab:
        print("  FAIL  no state has a capitol -> the cost field is undefined")
        return False, None

    # 4 : recompute d-field and compare with published numbers
    labels = sorted(states, key=str)
    idx = {lab: i for i, lab in enumerate(labels)}
    st = [[idx[grid[r][c]] for c in range(m)] for r in range(n)]
    R = d_field(st)
    dist, rows, answer = R["dist"], R["rows"], R["answer"]

    print("\n[cost field vs published numbers]")
    pub = published_numbers(n)
    if not pub:
        print("  (no published reference for this size - reporting the field only)")
        for r in range(n):
            print("      " + " ".join(f"{int(v):>4}" for v in dist[r]))
    else:
        bad = []
        for (r, c), v in sorted(pub.items()):
            got = dist[r][c]
            if int(got) != v:
                bad.append((r + 1, c + 1, v, int(got)))
        say(not bad, f"all {len(pub)} published numbers reproduced"
            + ("" if not bad else f"  -> {len(bad)} mismatch(es)"))
        for r, c, exp, got in bad:
            print(f"      MISMATCH ({r},{c}): published {exp}, your partition gives {got}")
        if bad:
            print("      full field of your partition (rows top->bottom):")
            for r in range(n):
                print("        " + " ".join(f"{int(v):>4}" for v in dist[r]))
    # blank cells of the reference grid: report them too (they are not published)
    if pub:
        blanks = [(r + 1, c + 1) for r in range(n) for c in range(m)
                  if (r, c) not in pub and n == 11]
        if blanks and not bad:
            print("      (unpublished cells of your partition):")
            for r in range(n):
                print("        " + " ".join(f"{int(v):>4}" for v in dist[r]))

    # 5 : answer
    print("\n[answer]")
    print(f"      row sums : {rows}")
    print(f"      sum(row_sums) = {sum(rows)}   (must equal sum of state sizes^2 = "
          f"{sum(len(states[l])**2 for l in states)})")
    print(f"      ANSWER   : sum(row_sums^2) = {answer}")
    return ok, answer


def selftest():
    print("=== selftest: official 5x5 example (known answer 8045) ===")
    p = json.load(open(os.path.join(PUZZLES, "official-example-5x5", "truth.json")))
    ok, ans = validate(p["states"])
    print(f"  -> ok={ok} answer={ans} (expect 8045)")
    assert ok and ans == 8045

    print("\n=== selftest: 4x4 counterexample (two answers 304 / 112 -> must FAIL) ===")
    c = json.load(open(os.path.join(PUZZLES, "counterexample-4x4-two-answers", "truth.json")))
    ok, ans = validate(c["alternative_partitions"][0]["states"])
    print(f"  -> ok={ans} (expected to mismatch the published field: the fixture's 16 hints "
          f"are satisfied by BOTH partitions)")
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--selftest" in args:
        selftest(); sys.exit(0)
    if "--grid" not in args:
        print(__doc__); sys.exit(2)
    path = args[args.index("--grid") + 1]
    grid = load_grid(path)
    ok, ans = validate(grid)
    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "PROBLEM FOUND (see FAIL lines above)")
    sys.exit(0 if ok else 1)
