#!/usr/bin/env python3
"""A rigorous lower bound on the number of capitols in the official 11x11 puzzle.

Key lemma (step-count bound): if d(x) = v and the optimal path to the nearest capitol
uses k steps, then every non-final step costs >= 2 (a step of cost 1 would pass through
a 1-cell state, which IS a capitol, so the path would have ended there) and the final
step costs >= 1. Hence v >= 2(k-1) + 1, i.e.  k <= (v+1)/2, and Manh(x, c*) <= k.

=> For every hint x there must exist a capitol within Manh distance floor((v+1)/2) of x.
=> The unknown capitols must HIT the ball of every hint that no known capitol covers.
=> minimum extra capitols = minimum hitting set over those balls.
"""
import os
import json, time

P = os.path.join(DATA, "/puzzles/official-11x11/puzzle.json"
pz = json.load(open(P))
n = pz["size"]
G = pz["grid"]
hints = {(r, c): G[r][c] for r in range(n) for c in range(n) if G[r][c] is not None}
known_cap = set(x for x, v in hints.items() if v == 0)
print(f"hints={len(hints)}  known capitols (revealed 0-cells) = {sorted((r+1,c+1) for r,c in known_cap)}")


def ball(x, r):
    return [(rr, cc) for rr in range(n) for cc in range(n)
            if abs(rr - x[0]) + abs(cc - x[1]) <= r and (rr, cc) != x]


demands = []          # (hint cell, v, radius, candidate cells)
for (r, c), v in sorted(hints.items()):
    if v == 0:
        continue
    rad = (v + 1) // 2
    C = [b for b in ball((r, c), rad) if b not in hints]   # a d>0 cell can never be a capitol
    if any(c2 in known_cap for c2 in C):
        continue                                          # already satisfied by a known capitol
    demands.append(((r, c), v, rad, C))

print(f"uncovered demands = {len(demands)}")
pool = sorted({c for _, _, _, C in demands for c in C})
print(f"candidate pool (cells that could host a hidden capitol) = {len(pool)}")

# --- greedy upper bound ---
chosen = []
uncovered = set(range(len(demands)))
while uncovered:
    best, bestc = None, None
    for i in uncovered:
        cnt = sum(1 for c in demands[i][3] if c not in chosen)
        if best is None or cnt < best:
            best, bestc = cnt, demands[i][3]
    pick = None
    for c in demands[uncovered][0][3] if False else bestc:
        if c not in chosen:
            pick = c; break
    if pick is None:
        break
    chosen.append(pick)
    uncovered = {i for i in uncovered if pick not in demands[i][3]}
greedy = len(chosen)
print(f"greedy upper bound = {greedy}")

# --- exact branch & bound: minimum hitting set ---
t0 = time.time()
best_size = greedy
best_sets = []


def rec(chosen, covered):
    global best_size, best_sets
    if len(chosen) > best_size:
        return
    unc = [i for i in range(len(demands)) if i not in covered]
    if not unc:
        if len(chosen) < best_size:
            best_size = len(chosen); best_sets = [tuple(sorted(chosen))]
        else:
            best_sets.append(tuple(sorted(chosen)))
        return
    i = min(unc, key=lambda j: sum(1 for c in demands[j][3] if c not in chosen))
    for c in demands[i][3]:
        if c in chosen:
            continue
        rec(chosen + [c], covered | {j for j in range(len(demands)) if c in demands[j][3]})


rec([], set())
print(f"\nMINIMUM additional capitols (hidden) = {best_size}   ({time.time()-t0:.1f}s)")
print(f"number of minimum hitting sets = {len(best_sets)}")
for s in best_sets[:10]:
    print("   hidden capitols (1-based):", [(r + 1, c + 1) for r, c in s])
print(f"\n=> the official 11x11 tiling has AT LEAST {2 + best_size} capitols "
      f"(2 revealed + >= {best_size} hidden)")
print(f"=> and at most 121 (all singletons); k=120 impossible (T-B)")
json.dump({"min_additional": best_size, "n_min_sets": len(best_sets),
           "min_sets": [[list(c) for c in s] for s in best_sets[:50]],
           "total_capitol_lower_bound": 2 + best_size},
          open(os.path.join(HERE, "capitol_hitting_set_11x11.json", "w"), indent=1)
print("saved capitol_hitting_set_11x11.json")
