#!/usr/bin/env python3
"""Two demos of validate.py on 11x11 candidate partitions."""
import subprocess, sys, os

def run(name, rows):
    path = f"/tmp/{name}.txt"
    open(path, "w").write("\n".join(rows) + "\n")
    print("#" * 78)
    print(f"# DEMO {name}")
    print("#" * 78)
    p = subprocess.run([sys.executable, "validate.py", "--grid", path],
                       capture_output=True, text=True)
    out = p.stdout
    # keep the informative parts
    for line in out.splitlines():
        if ("MISMATCH" in line or "FAIL" in line or "PASS" in line or "row sums" in line
                or "ANSWER" in line or "distinct states" in line or "RESULT" in line
                or line.strip().startswith("no state") or "capitol" in line and "state" in line):
            print(line)
    print(f"\n>>> exit code = {p.returncode}   ({'PASS' if p.returncode == 0 else 'PROBLEM FOUND'})")
    print()

# demo A: seven pieces, all rectangles/bars -> legal states but NO capitol at all
A = []
A.append("A" * 11)                       # row 1: 1x11 bar
for r in range(2, 12):
    A.append("B" + "D" * 9 + "C")        # B = col 1, C = col 11, D = rows2-6 cols2-10
# rebuild properly: rows 2-6 -> D ; rows 7-11 -> E/F/G
A = ["A" * 11]
for r in range(2, 7):
    A.append("B" + "D" * 9 + "C")
for r in range(7, 12):
    A.append("B" + "E" * 4 + "F" * 3 + "G" * 2 + "C")
run("demoA_seven_pieces", A)

# demo B: same but split D so there is at least one 1x1 state (a capitol exists)
B = ["A" * 11]
for r in range(2, 6):
    B.append("B" + "D" * 9 + "C")
B.append("B" + "D" * 8 + "H" + "C")     # (6,10) = H, a 1x1 state -> capitol
for r in range(7, 12):
    B.append("B" + "E" * 4 + "F" * 3 + "G" * 2 + "C")
run("demoB_seven_pieces_with_capitol", B)
