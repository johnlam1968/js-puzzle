#!/usr/bin/env python3
"""CORRECTED rule engine.

BUG FIXED: rot180 / rot90 fixed-cell sets were hard-coded to empty. That wrongly
marked any state whose ONLY symmetry is a 180-degree rotation (e.g. the W pentomino,
whose 180-rotation about its centre cell fixes exactly 1 cell) as having NO capitol.

Now every candidate is an explicit affine map; the fixed set is computed by evaluation.
"""
import heapq
from itertools import combinations

def sym_info(cells):
    """Return (capitol|None, [sym names], [fix counts]) for a set of (r,c) cells."""
    cells = list(cells); k = len(cells)
    sr = sum(r for r, c in cells); sc = sum(c for r, c in cells)
    S = set(cells)
    cands = []
    if (sr - sc) % k == 0:
        k1 = (sr - sc) // k
        cands.append(("refD1", lambda r, c: (c + k1, r - k1)))
    if (sr + sc) % k == 0:
        k2 = (sr + sc) // k
        cands.append(("refD2", lambda r, c: (k2 - c, k2 - r)))
    if (2 * sr) % k == 0:
        a = 2 * sr // k
        cands.append(("refH", lambda r, c: (a - r, c)))
    if (2 * sc) % k == 0:
        b = 2 * sc // k
        cands.append(("refV", lambda r, c: (r, b - c)))
    if (2 * sr) % k == 0 and (2 * sc) % k == 0:
        a = 2 * sr // k; b = 2 * sc // k
        cands.append(("rot180", lambda r, c: (a - r, b - c)))
    if (sr - sc) % k == 0 and (sr + sc) % k == 0:
        k1 = (sr - sc) // k; k2 = (sr + sc) // k
        cands.append(("rot90", lambda r, c: (c + k1, k2 - r)))
        # inverse of rot90: (u,v) = (c+k1, k2-r)  =>  c = u-k1, r = k2-v
        cands.append(("rot270", lambda r, c: (k2 - c, r - k1)))
    names, fixes, fixsets = [], [], []
    for name, f in cands:
        img = set(f(r, c) for r, c in cells)
        if img != S:
            continue
        fixed = {(r, c) for r, c in cells if f(r, c) == (r, c)}
        names.append(name); fixsets.append(fixed); fixes.append(len(fixed))
    cap = next(iter(fixsets[0])) if names and all(f == 1 for f in fixes) else None
    return cap, names, fixes, fixsets


def d_field(states):
    H = len(states); W = len(states[0]); sizes = {}
    for r in range(H):
        for c in range(W): sizes[states[r][c]] = sizes.get(states[r][c], 0) + 1
    cap = {}; syms = {}; fixsets = {}
    for lab in sizes:
        cells = [(r, c) for r in range(H) for c in range(W) if states[r][c] == lab]
        c0, names, fixes, fs = sym_info(cells)
        syms[lab] = names; fixsets[lab] = fs
        if c0 is not None: cap[lab] = c0
    INF = float('inf'); dist = [[INF] * W for _ in range(H)]; pq = []
    for lab, (r, c) in cap.items(): dist[r][c] = 0; heapq.heappush(pq, (0, r, c))
    while pq:
        d, r, c = heapq.heappop(pq)
        if d > dist[r][c]: continue
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < H and 0 <= cc < W): continue
            A, B = states[r][c], states[rr][cc]
            w = sizes[A] if A == B else min(sizes[A], sizes[B])
            if d + w < dist[rr][cc]: dist[rr][cc] = d + w; heapq.heappush(pq, (d + w, rr, cc))
    rows = [sum(sizes[states[r][c]] for c in range(W)) for r in range(H)]
    return dict(sizes=sizes, cap=cap, dist=dist, rows=rows, answer=sum(s * s for s in rows),
                syms=syms, fixsets=fixsets)


def connected(cells):
    S = set(cells); st = [next(iter(S))]; seen = set(st)
    while st:
        r, c = st.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if n in S and n not in seen: seen.add(n); st.append(n)
    return len(seen) == len(S)
