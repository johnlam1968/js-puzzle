#!/usr/bin/env python3
"""3x3: how many tilings are compatible with k hints?

Build the full table of legal 3x3 tilings -> (d-field, answer), then for a reference
tiling measure, as a function of k (number of revealed d-values):
   - how many tilings are compatible with those k hints
   - how many DISTINCT ANSWERS those compatible tilings produce
That is the whole point of the puzzle: the numbers do the disambiguating.
"""
import itertools, time
from collections import Counter, defaultdict
from engine import sym_info, connected, d_field

N = 3
cells = [(r, c) for r in range(N) for c in range(N)]
IDX = {c: i for i, c in enumerate(cells)}
NB = [0] * 9
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
        for j in range(9):
            if (NB[i] >> j) & 1 and (mask >> j) & 1 and not (seen >> j) & 1:
                add |= 1 << j
        seen |= add
        frontier |= add
    return seen == mask


t0 = time.time()
legal = []
for mask in range(1, 1 << 9):
    if not connected_mask(mask):
        continue
    cl = [cells[i] for i in range(9) if (mask >> i) & 1]
    cap, names, fixes, fs = sym_info(cl)
    if names:
        legal.append((mask, cap is not None))
print(f"3x3 legal states (placements) = {len(legal)}")

bycell = defaultdict(list)
for m, hc in legal:
    mm = m
    while mm:
        b = mm & -mm
        mm -= b
        bycell[b.bit_length() - 1].append(m)

parts = []


def rec(rem, chosen):
    if rem == 0:
        parts.append(tuple(chosen))
        return
    first = (rem & -rem).bit_length() - 1
    for m in bycell[first]:
        if m & ~rem:
            continue
        rec(rem ^ m, chosen + [m])


rec((1 << 9) - 1, [])
print(f"3x3 legal tilings = {len(parts)}  ({time.time()-t0:.1f}s)")

table = []
for p in parts:
    st = [[None] * N for _ in range(N)]
    for lab, m in enumerate(p):
        mm = m
        while mm:
            b = mm & -mm
            mm -= b
            i = b.bit_length() - 1
            st[i // N][i % N] = lab
    R = d_field(st)
    if not R["cap"]:            # no capitol at all -> d field undefined -> not a solution
        continue
    flat = tuple(int(R["dist"][r][c]) for r in range(N) for c in range(N))
    table.append((flat, R["answer"], tuple(sorted(R["cap"].values()))))
print(f"3x3 tilings with a defined d-field (>=1 capitol) = {len(table)}")

# reference tiling: pick one with a "nice" number of blocks and a capitol
from collections import Counter as C
blkcount = Counter()
for df, ans, caps in table:
    pass
# choose the reference = the tiling whose d-field is most "spread" (many distinct values)
best = max(table, key=lambda t: len(set(t[0])))
df0, ans0, caps0 = best
print(f"\nreference tiling: d-field = {list(df0)}  answer = {ans0}  capitols = {list(caps0)}")

print("\n  k  hints |  mean #compatible tilings | mean #distinct answers | worst-case #answers")
for k in range(0, N * N + 1):
    tot = 0
    totans = 0
    worst = 0
    for combo in itertools.combinations(range(N * N), k):
        cnt = 0
        ansset = set()
        for df, ans, _ in table:
            if all(df[i] == df0[i] for i in combo):
                cnt += 1
                ansset.add(ans)
        tot += cnt
        totans += len(ansset)
        worst = max(worst, len(ansset))
    ncomb = len(list(itertools.combinations(range(N * N), k)))
    print(f"  {k:>2}       |        {tot/ncomb:>10.1f}          |      {totans/ncomb:>8.2f}         |      {worst:>4}")

print("\n=> 提示越少, 候选越多; 提示全给时, 候选被压到 1（除非该划分的 d 场本身有歧义）")
