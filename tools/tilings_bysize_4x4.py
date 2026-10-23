#!/usr/bin/env python3
"""4x4 tilings grouped by SIZE MULTISET, split into "alive" (has >=1 capitol) and "dead".

The question the user is asking: "how many ways to tile a 4x4 frame with pieces of
given sizes?"  e.g. "4 four-blocks -- is there only one way?"  and "3 four-blocks
+ 4 single blocks".

Also proves/prints the key structural fact: a state with a capitol has ODD size
(all non-fixed cells pair up under the symmetry), so even-sized states are dead weight.
"""
import time
from collections import Counter, defaultdict
from engine import sym_info, connected

N = 4
cells = [(r, c) for r in range(N) for c in range(N)]
IDX = {c: i for i, c in enumerate(cells)}
NB = [0] * 16
for i, (r, c) in enumerate(cells):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            NB[i] |= 1 << IDX[(rr, cc)]


def connected_mask(mask):
    seen = mask & -mask
    frontier = seen
    while frontier:
        b = frontier & -frontier
        frontier -= b
        i = b.bit_length() - 1
        add = 0
        for j in range(16):
            if (NB[i] >> j) & 1 and (mask >> j) & 1 and not (seen >> j) & 1:
                add |= 1 << j
        seen |= add
        frontier |= add
    return seen == mask


t0 = time.time()
legal, cap_of = [], {}
for mask in range(1, 1 << 16):
    if not connected_mask(mask):
        continue
    cl = [cells[i] for i in range(16) if (mask >> i) & 1]
    cap, names, fixes, fs = sym_info(cl)
    if names:
        legal.append(mask)
        cap_of[mask] = cap
print(f"legal states (placements) = {len(legal)}  ({time.time()-t0:.1f}s)")

bycell = defaultdict(list)
for m in legal:
    mm = m
    while mm:
        b = mm & -mm
        mm -= b
        bycell[b.bit_length() - 1].append(m)

# --- enumerate tilings lazily, group by size multiset ---
bysizes = Counter()
alive_by_sizes = Counter()
per_k = Counter()
alive_per_k = Counter()
capitol_sizes = Counter()
n = 0


def rec(rem, chosen):
    global n
    if rem == 0:
        n += 1
        sizes = tuple(sorted(bin(m).count("1") for m in chosen))
        bysizes[sizes] += 1
        per_k[len(chosen)] += 1
        alive = any(cap_of[m] is not None for m in chosen)
        if alive:
            alive_by_sizes[sizes] += 1
            alive_per_k[len(chosen)] += 1
            for m in chosen:
                if cap_of[m] is not None:
                    capitol_sizes[bin(m).count("1")] += 1
        return
    first = (rem & -rem).bit_length() - 1
    for m in bycell[first]:
        if m & ~rem:
            continue
        rec(rem ^ m, chosen + [m])


rec((1 << 16) - 1, [])
print(f"legal tilings of 4x4 = {n:,}  ({time.time()-t0:.1f}s)")

print("\n=== by number of blocks ===")
print("  blocks |   all tilings |  with >=1 capitol (ALIVE) |  dead")
for k in sorted(per_k):
    a = per_k[k]; l = alive_per_k.get(k, 0)
    print(f"  {k:>6} | {a:>13,} | {l:>22,} | {a-l:>6,}")

print("\n=== the two cases you named ===")
q1 = (4, 4, 4, 4)
q2 = (4, 4, 4, 1, 1, 1, 1)
for nm, q in (("4 x size-4 blocks", q1), ("3 x size-4 + 4 x size-1", q2)):
    print(f"  {nm:<26} all={bysizes.get(q,0):>6,}   alive={alive_by_sizes.get(q,0):>6,}")
print(f"  (for reference: 4 x size-4 blocks ALIVE = 0  -> no tetromino has a capitol)")

print("\n=== size multisets with at least one ALIVE tiling (top 25 by count) ===")
rows = [(s, alive_by_sizes[s], bysizes[s]) for s in bysizes if alive_by_sizes.get(s)]
rows.sort(key=lambda x: -x[1])
print("   size multiset                    alive    all")
for s, a, t in rows[:25]:
    print(f"   {str(list(s)):<32} {a:>7,} {t:>9,}")
print(f"\n   total ALIVE tilings = {sum(alive_by_sizes.values()):,}  of {n:,}  "
      f"({sum(alive_by_sizes.values())/n*100:.1f}%)")
print(f"   distinct ALIVE size multisets = {len(rows)}")

print("\n=== which block sizes can carry a capitol? ===")
by_size_tot = Counter(); by_size_cap = Counter()
for m in legal:
    by_size_tot[bin(m).count("1")] += 1
    if cap_of[m] is not None:
        by_size_cap[bin(m).count("1")] += 1
print("   size | legal placements | of which have a capitol")
for s in sorted(by_size_tot):
    print(f"   {s:>4} | {by_size_tot[s]:>16} | {by_size_cap[s]:>21}")
print("\n   => only ODD sizes can carry a capitol (non-fixed cells pair up under the symmetry).")
print(f"\ntotal {time.time()-t0:.1f}s")
