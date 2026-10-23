#!/usr/bin/env python3
"""Data-contract checker. Exit code is the verdict (0 = all good)."""
import json, sys
from engine import sym_info, d_field
import os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
D = os.path.join(ROOT, "data", "puzzles")
ok = True
def chk(cond, msg):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    ok = ok and bool(cond)

print("=== official-example-5x5 ===")
t = json.load(open(f"{D}/official-example-5x5/truth.json"))
R = d_field(t["states"])
chk(R["answer"] == 8045, f"answer == 8045 (got {R['answer']})")
chk(R["rows"] == [37,29,31,43,55], f"row_sums == [37,29,31,43,55] (got {R['rows']})")
zeros = sorted((r,c) for r in range(5) for c in range(5) if R["dist"][r][c]==0)
chk(sorted(map(tuple,t["capitols"])) == zeros, f"capitols == d-field zero set (fixture {sorted(map(tuple,t['capitols']))} vs engine {zeros})")
chk(sorted(R["cap"].values()) == zeros, "engine capitols == d-field zero set")
sizes = R["sizes"]
chk(t["state_sizes"] == [sizes[k] for k in sorted(sizes)], "state_sizes == engine sizes")
chk(sum(t["row_sums"]) == sum(v*v for v in sizes.values()), f"sum(row_sums) == sum(|S|^2)  ({sum(t['row_sums'])} vs {sum(v*v for v in sizes.values())})")
# every state's symmetry labels must match the engine
for k in sorted(sizes):
    cells = [(r,c) for r in range(5) for c in range(5) if t["states"][r][c]==k]
    cap, names, fixes, fs = sym_info(cells)
    chk(sorted(t["state_symmetry"][k]) == sorted(names), f"state {k} symmetry labels {t['state_symmetry'][k]} vs engine {names}")
    chk(t["state_fix_counts"][k] == fixes, f"state {k} fix counts {t['state_fix_counts'][k]} vs engine {fixes}")
    exp = list(cap) if cap else None
    chk(t["state_capitol"][k] == exp, f"state {k} capitol {t['state_capitol'][k]} vs engine {exp}")
pub = {(0,0):12,(0,4):17,(1,0):8,(1,2):6,(1,3):3,(3,1):7,(3,2):6,(3,4):10,(4,0):25,(4,4):0}
chk(all(R["dist"][r][c]==v for (r,c),v in pub.items()), "all 10 published numbers reproduced")

print("=== official-11x11 ===")
p11 = json.load(open(f"{D}/official-11x11/puzzle.json"))
n = p11["size"]
grid = p11["grid"]
chk(len(grid)==n and all(len(r)==n for r in grid), "grid is n x n")
chk(sum(1 for r in grid for v in r if v is not None) == p11["hint_count"] == 33, "33 cells with ink")
chk(p11["row_hint_counts"] == [4,1,3,4,3,3,3,4,3,1,4], "per-row hint counts 4/1/3/4/3/3/3/4/3/1/4")
for h in p11["hints"]:
    chk(grid[h["row"]-1][h["col"]-1] == h["value"], f"hint ({h['row']},{h['col']})={h['value']} consistent with grid")
chk(json.load(open(f"{D}/official-11x11/truth.json"))["status"] == "unsolved", "truth status == unsolved")

print("=== counterexample-4x4-two-answers ===")
c = json.load(open(f"{D}/counterexample-4x4-two-answers/truth.json"))
ans = []
for alt in c["alternative_partitions"]:
    R2 = d_field(alt["states"])
    chk(R2["answer"] == alt["answer"], f"{alt['name']}: answer {R2['answer']} == fixture {alt['answer']}")
    chk(R2["dist"] == alt["d_field"], f"{alt['name']}: d_field matches")
    ans.append(R2["answer"])
chk(ans == [304,112], f"two distinct answers {ans}")
chk(c["alternative_partitions"][0]["d_field"] == c["alternative_partitions"][1]["d_field"], "same d-field for both partitions")
print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
