#!/usr/bin/env python3
"""4x4: what are the legal shapes, and how many partitions do they make?

Three independent views:
  (1) shape catalogue  : distinct legal shapes up to translation, by size & symmetry
  (2) partition count  : memoised DP over remaining-cell masks (independent of any brute-force enumerator)
  (3) plausibility     : Bell(16) vs connected-only partitions vs symmetric-only partitions
"""
import time
from collections import Counter, defaultdict
from math import comb
from engine import sym_info

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
conn_masks, legal_masks = [], []
for mask in range(1, 1 << 16):
    if not connected_mask(mask):
        continue
    conn_masks.append(mask)
    cl = [cells[i] for i in range(16) if (mask >> i) & 1]
    cap, names, fixes, fs = sym_info(cl)
    if names:
        legal_masks.append((mask, cap is not None, tuple(names)))
print(f"[1] connected subsets of 4x4          = {len(conn_masks):,}")
print(f"[2] legal states (connected+symmetric)= {len(legal_masks):,} placements  ({time.time()-t0:.1f}s)", flush=True)


def canon(mask):
    r0 = min(r for r, c in cells if (mask >> IDX[(r, c)]) & 1)
    c0 = min(c for r, c in cells if (mask >> IDX[(r, c)]) & 1)
    out = 0
    for r, c in cells:
        if (mask >> IDX[(r, c)]) & 1:
            out |= 1 << IDX[(r - r0, c - c0)]
    return out


types = {}
for mask, hascap, names in legal_masks:
    k = canon(mask)
    e = types.setdefault(k, {"size": bin(mask).count("1"), "names": names, "cap": hascap, "placements": 0})
    e["placements"] += 1
print(f"[3] distinct legal SHAPE TYPES (up to translation) = {len(types)}", flush=True)
bysize = defaultdict(lambda: [0, 0, 0])
for v in types.values():
    bysize[v["size"]][0] += 1
    bysize[v["size"]][1] += v["placements"]
    bysize[v["size"]][2] += 1 if v["cap"] else 0
print("\n    size | shape types | placements in 4x4 | types with a capitol")
for s in sorted(bysize):
    t, p, c = bysize[s]
    print(f"    {s:>4} | {t:>11} | {p:>17} | {c:>19}")
symcnt = Counter(v["names"] for v in types.values())
print("\n    by symmetry signature (shape types):")
for names, c in sorted(symcnt.items(), key=lambda x: -x[1]):
    print(f"      {str(list(names)):<58} {c}")

bycell = defaultdict(list)
for mask, hascap, names in legal_masks:
    mm = mask
    while mm:
        b = mm & -mm
        mm -= b
        bycell[b.bit_length() - 1].append((mask, hascap))
memo = {}


def count(rem):
    if rem == 0:
        return 1
    if rem in memo:
        return memo[rem]
    first = (rem & -rem).bit_length() - 1
    tot = 0
    for mask, hascap in bycell[first]:
        if mask & ~rem:
            continue
        tot += count(rem ^ mask)
    memo[rem] = tot
    return tot


full = (1 << 16) - 1
t1 = time.time()
total = count(full)
print(f"\n[4] legal PARTITIONS (DP over masks) = {total:,}   ({len(memo)} masks, {time.time()-t1:.1f}s)", flush=True)

memo2 = {}


def count_k(rem, k):
    if rem == 0:
        return 1 if k == 0 else 0
    key = (rem, k)
    if key in memo2:
        return memo2[key]
    first = (rem & -rem).bit_length() - 1
    tot = 0
    for mask, _ in bycell[first]:
        if mask & ~rem:
            continue
        tot += count_k(rem ^ mask, k - 1)
    memo2[key] = tot
    return tot


dist = Counter()
for k in range(1, 17):
    c = count_k(full, k)
    if c:
        dist[k] = c
print("[5] partitions by number of blocks:")
for k in sorted(dist):
    print(f"      {k:>2} blocks: {dist[k]:>10,}")
print(f"      TOTAL    : {sum(dist.values()):,}", flush=True)


def bell(n):
    B = [1]
    for m in range(1, n + 1):
        B.append(sum(comb(m - 1, j) * B[j] for j in range(m)))
    return B[n]


bycell_c = defaultdict(list)
for mask in conn_masks:
    mm = mask
    while mm:
        b = mm & -mm
        mm -= b
        bycell_c[b.bit_length() - 1].append(mask)
memo3 = {}


def count_c(rem):
    if rem == 0:
        return 1
    if rem in memo3:
        return memo3[rem]
    first = (rem & -rem). bit_length() - 1
    tot = 0
    for mask in bycell_c[first]:
        if mask & ~rem:
            continue
        tot += count_c(rem ^ mask)
    memo3[rem] = tot
    return tot


conn_parts = count_c(full)
print("\n[6] plausibility:")
print(f"      Bell(16) (ALL set partitions of 16 cells)   = {bell(16):,}")
print(f"      partitions into CONNECTED blocks only      = {conn_parts:,}  ({conn_parts/bell(16)*100:.1f}% of Bell)")
print(f"      partitions into CONNECTED+SYMMETRIC blocks = {total:,}  ({total/bell(16)*100:.2f}% of Bell, {total/conn_parts*100:.1f}% of connected-only)")
print(f"\ntotal {time.time()-t0:.1f}s")
