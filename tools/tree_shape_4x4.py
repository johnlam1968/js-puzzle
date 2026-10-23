#!/usr/bin/env python3
"""Compute the SHAPE of the 4x4 tiling search tree, so it can be drawn.

  * legal shapes (connected + symmetric) as placements, with capitol info
  * branching factor at the corner cell (0,0)
  * total number of NODES in the DFS tree (all partial tilings)
  * number of LEAVES (= complete tilings) and the alive/dead split per block count
"""
import json, time
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
legal = []
for mask in range(1, 1 << 16):
    if not connected_mask(mask):
        continue
    cl = [cells[i] for i in range(16) if (mask >> i) & 1]
    cap, names, fixes, fs = sym_info(cl)
    if names:
        legal.append((mask, cap is not None, names))
print(f"legal states (placements) = {len(legal)}  ({time.time()-t0:.1f}s)", flush=True)

bycell = defaultdict(list)
for m, hc, nm in legal:
    mm = m
    while mm:
        b = mm & -mm
        mm -= b
        bycell[b.bit_length() - 1].append((m, hc))

corner = IDX[(0, 0)]
corner_shapes = [m for m, hc, nm in legal if (m >> corner) & 1]
print(f"legal shapes that can cover the CORNER (0,0): {len(corner_shapes)}")

# --- size of the DFS tree: nodes = 1 + sum over branches of subtree nodes ---
sys_limit = 10 ** 7
nodes_memo = {}


def sub_nodes(rem):
    """number of nodes in the subtree rooted at 'rem' (including rem itself)"""
    if rem == 0:
        return 1
    if rem in nodes_memo:
        return nodes_memo[rem]
    first = (rem & -rem).bit_length() - 1
    tot = 1
    for m, hc in bycell[first]:
        if m & ~rem:
            continue
        tot += sub_nodes(rem ^ m)
    nodes_memo[rem] = tot
    return tot


t1 = time.time()
total_nodes = sub_nodes((1 << 16) - 1)
print(f"total NODES in the search tree = {total_nodes:,}  ({time.time()-t1:.1f}s)")
print(f"leaves (complete tilings)      = 562,308")
print(f"average branching factor      = {total_nodes/562308:.2f}")

# --- per block count: total and alive ---
memo = {}


def count_k(rem, k):
    if rem == 0:
        return 1 if k == 0 else 0
    key = (rem, k)
    if key in memo:
        return memo[key]
    first = (rem & -rem).bit_length() - 1
    tot = 0
    for m, hc in bycell[first]:
        if m & ~rem:
            continue
        tot += count_k(rem ^ m, k - 1)
    memo[key] = tot
    return tot


per_k = Counter(); alive_k = Counter()
for k in range(1, 17):
    c = count_k((1 << 16) - 1, k)
    if c:
        per_k[k] = c
print("per-k total done", flush=True)

# alive: has >=1 capitol -> track with a flag
memo2 = {}


def count_k2(rem, k, need):
    if rem == 0:
        return 1 if (k == 0 and not need) else 0
    key = (rem, k, need)
    if key in memo2:
        return memo2[key]
    first = (rem & -rem).bit_length() - 1
    tot = 0
    for m, hc in bycell[first]:
        if m & ~rem:
            continue
        tot += count_k2(rem ^ m, k - 1, need and not hc)
    memo2[key] = tot
    return tot


for k in range(1, 17):
    if per_k.get(k):
        alive_k[k] = count_k2((1 << 16) - 1, k, True)
print("per-k alive done", flush=True)

out = {
    "n_legal_states": len(legal),
    "corner_branches": len(corner_shapes),
    "corner_shape_masks": corner_shapes,
    "total_nodes": total_nodes,
    "leaves": 562308,
    "per_k_total": dict(per_k),
    "per_k_alive": dict(alive_k),
    "legal_by_size": dict(Counter(bin(m).count("1") for m, hc, nm in legal)),
}
json.dump(out, open("tree_shape_4x4.json", "w"), indent=1)
print("saved tree_shape_4x4.json")
print(f"total {time.time()-t0:.1f}s")
