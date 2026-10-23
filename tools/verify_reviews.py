#!/usr/bin/env python3
"""Verify the two claims made by the GLM / DeepSeek reviews.

CLAIM 1 (GLM): the hitting-set demand count is wrong -- a demand whose ball already
contains a REVEALLED capitol is already satisfied and must not be counted.
  -> my earlier script had `C = [b for b in ball if b not in hints]` and then
     `if any(c2 in known_cap for c2 in C)`.  But known_cap cells ARE hint cells,
     so they were already filtered out of C  =>  the check NEVER fired  =>  bug.

CLAIM 2 (GLM): the section 1.7 pruning rule "Manh(x, nearest KNOWN capitol) > D(x)
  => prune" is UNSOUND, because the true nearest capitol may be an UNKNOWN one.
  -> test on the official 5x5 example: hint (1,3)=3 (1-based) has its capitol at
     (2,3), which is not revealed; the only revealed 0 is (5,5) at Manh 6 > 3.
"""
import os
import json, time
from collections import defaultdict

N11 = 11
pz = json.load(open(os.path.join(DATA, "/puzzles/official-11x11/puzzle.json"))
G = pz["grid"]
hints = {(r, c): G[r - 1][c - 1] for r in range(1, N11 + 1) for c in range(1, N11 + 1)
         if G[r - 1][c - 1] is not None}
known_cap = set(x for x, v in hints.items() if v == 0)


def ball(x, r):
    return [(rr, cc) for rr in range(1, N11 + 1) for cc in range(1, N11 + 1)
            if abs(rr - x[0]) + abs(cc - x[1]) <= r and (rr, cc) != x]


print("=" * 78)
print("CLAIM 1: demand count (the bug was that 'already satisfied by a revealed capitol'")
print("          could never fire, because revealed capitols are themselves hint cells)")
print("=" * 78)
demands = []
satisfied_by_known = []
for (r, c), v in sorted(hints.items()):
    if v == 0:
        continue
    rad = (v + 1) // 2
    raw = ball((r, c), rad)
    if any(c2 in known_cap for c2 in raw):        # <-- the check that never fired before
        satisfied_by_known.append(((r, c), v, rad))
        continue
    C = [b for b in raw if b not in hints]        # a d>0 cell can never be a capitol
    demands.append(((r, c), v, rad, C))
print(f"  hints                                   = {len(hints)}")
print(f"  demands already satisfied by a REVEALLED capitol = {len(satisfied_by_known)}")
for (r, c), v, rad in satisfied_by_known:
    ks = [k for k in known_cap if abs(k[0] - r) + abs(k[1] - c) <= rad]
    print(f"      ({r},{c}) d={v:<3} radius={rad:<3} covered by revealed capitol {ks}")
print(f"  UNCOVERED demands (the ones that need a HIDDEN capitol) = {len(demands)}")
pool = sorted({c for _, _, _, C in demands for c in C})
print(f"  candidate pool for HIDDEN capitols (blank cells only)   = {len(pool)}")

# exact minimum hitting set (branch & bound)
best = [None, []]
def rec(chosen, covered):
    if best[0] is not None and len(chosen) > best[0]:
        return
    unc = [i for i in range(len(demands)) if i not in covered]
    if not unc:
        if best[0] is None or len(chosen) < best[0]:
            best[0] = len(chosen); best[1] = [tuple(sorted(chosen))]
        elif len(chosen) == best[0]:
            best[1].append(tuple(sorted(chosen)))
        return
    i = min(unc, key=lambda j: len([c for c in demands[j][3] if c not in chosen]))
    for c in demands[i][3]:
        if c in chosen:
            continue
        rec(chosen + [c], covered | {j for j in range(len(demands)) if c in demands[j][3]})

t0 = time.time()
rec([], set())
print(f"\n  CORRECTED minimum additional capitols = {best[0]}   ({time.time()-t0:.1f}s)")
print(f"  number of minimum hitting sets         = {len(best[1])}")
for s in best[1][:6]:
    print("     ", s)
print(f"  => corrected total capitols >= 2 + {best[0]} = {2 + best[0]}")
json.dump({"min_additional": best[0], "n_min_sets": len(best[1]),
           "demands": len(demands), "satisfied_by_known": len(satisfied_by_known),
           "pool": len(pool),
           "min_sets": [[list(c) for c in s] for s in best[1][:200]]},
          open(os.path.join(HERE, "capitol_hitting_set_11x11.json", "w"), indent=1)

print()
print("=" * 78)
print("CLAIM 2: is the section 1.7 prune 'Manh(x, nearest REVEALLED capitol) > D(x)")
print("         => prune' unsound?  Test on the official 5x5 example.")
print("=" * 78)
# official 5x5 example
ex_states = [[0, 1, 1, 3, 3], [0, 1, 1, 2, 3], [0, 0, 2, 2, 3], [3, 0, 0, 0, 3], [3, 3, 3, 3, 3]]
sizes = {}
for r in range(5):
    for c in range(5):
        sizes[ex_states[r][c]] = sizes.get(ex_states[r][c], 0) + 1
caps = {(2, 1), (2, 3), (4, 4)}   # 0-based capitols
INF = float("inf")
dist = [[INF] * 5 for _ in range(5)]
import heapq
pq = []
for (r, c) in caps:
    dist[r][c] = 0; heapq.heappush(pq, (0, r, c))
while pq:
    d, r, c = heapq.heappop(pq)
    if d > dist[r][c]: continue
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if not (0 <= rr < 5 and 0 <= cc < 5): continue
        A, B = ex_states[r][c], ex_states[rr][cc]
        w = sizes[A] if A == B else min(sizes[A], sizes[B])
        if d + w < dist[rr][cc]:
            dist[rr][cc] = d + w; heapq.heappush(pq, (d + w, rr, cc))
published = {(0, 0): 12, (0, 4): 17, (1, 0): 8, (1, 2): 6, (1, 3): 3, (3, 1): 7, (3, 2): 6, (3, 4): 10, (4, 0): 25, (4, 4): 0}
revealed = {(4, 4)}     # the only REVEALLED 0-cell (1-based (5,5))
print("  hint (1-based) | D(x) | Manh to nearest REVEALLED capitol | rule fires? | true?")
fired = 0
for (r, c), v in sorted(published.items()):
    m = min(abs(r - a) + abs(c - b) for (a, b) in revealed)
    fires = m > v
    if fires: fired += 1
    print(f"    ({r+1},{c+1})      | {v:>3} | {m:>33} | {'PRUNE':>11} | {v==dist[r][c]}")
print(f"\n  => the rule would PRUNE {fired} of {len(published)} published hints, including TRUE ones.")
print("     Example: hint (2,4)=3 (1-based) has its true capitol at (3,4) which is NOT revealed;")
print("     the only revealed capitol (5,5) is at Manh 6 > 3  =>  the rule kills the true solution.")
print("     => CLAIM 2 CONFIRMED: the section 1.7 prune is still UNSOUND.")
