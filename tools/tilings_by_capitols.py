#!/usr/bin/env python3
"""Tiling counts stratified by the NUMBER OF CAPITOLS (and jointly with block count).

The user's point: the natural handle on a tiling is how many states have a capitol,
because (a) a capitol is exactly a d=0 cell, which the puzzle reveals directly, and
(b) a state with a capitol must be odd-sized (and not a 1x3 / 1x4 / X-pentomino etc.).
"""
import json, time
from collections import Counter, defaultdict
from engine import sym_info, connected

def enumerate_tilings(N):
    cells = [(r, c) for r in range(N) for c in range(N)]
    IDX = {c: i for i, c in enumerate(cells)}
    NB = [0] * (N * N)
    for i, (r, c) in enumerate(cells):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < N and 0 <= cc < N:
                NB[i] |= 1 << IDX[(rr, cc)]

    def conn(mask):
        seen = mask & -mask
        frontier = seen
        while frontier:
            b = frontier & -frontier
            frontier -= b
            i = b.bit_length() - 1
            add = 0
            for j in range(N * N):
                if (NB[i] >> j) & 1 and (mask >> j) & 1 and not (seen >> j) & 1:
                    add |= 1 << j
            seen |= add
            frontier |= add
        return seen == mask

    legal = []
    for mask in range(1, 1 << (N * N)):
        if not conn(mask):
            continue
        cl = [cells[i] for i in range(N * N) if (mask >> i) & 1]
        cap, names, fixes, fs = sym_info(cl)
        if names:
            legal.append((mask, cap is not None))
    bycell = defaultdict(list)
    for m, hc in legal:
        mm = m
        while mm:
            b = mm & -mm
            mm -= b
            bycell[b.bit_length() - 1].append((m, hc))
    joint = Counter()
    by_cap = Counter()
    by_cap_blocks = defaultdict(Counter)
    cap_total = [0]
    t0 = time.time()

    def rec(rem, chosen, ncap):
        if rem == 0:
            cap_total[0] += 1
            joint[(len(chosen), ncap)] += 1
            by_cap[ncap] += 1
            by_cap_blocks[ncap][len(chosen)] += 1
            return
        first = (rem & -rem).bit_length() - 1
        for m, hc in bycell[first]:
            if m & ~rem:
                continue
            rec(rem ^ m, chosen + [m], ncap + (1 if hc else 0))

    rec((1 << (N * N)) - 1, [], 0)
    cap_total = cap_total[0]
    print(f"N={N}: {cap_total:,} tilings, {len(legal)} legal shapes, {time.time()-t0:.0f}s", flush=True)
    return cap_total, joint, by_cap, by_cap_blocks, len(legal), legal


if __name__ == "__main__":
    out = {}
    for N in (3, 4):
        tot, joint, by_cap, by_cap_blocks, nlegal, legal = enumerate_tilings(N)
        print(f"\n=== {N}x{N}: tilings by number of CAPITOLS ===")
        print("  #capitols |  #tilings |  share |  block-count range")
        for k in sorted(by_cap):
            ks = sorted(by_cap_blocks[k])
            print(f"  {k:>9} | {by_cap[k]:>9,} | {by_cap[k]/tot*100:>5.1f}% |  {ks[0]}..{ks[-1]} blocks")
        out[N] = {"total": tot, "by_cap": dict(by_cap),
                  "joint": {f"{a},{b}": v for (a, b), v in joint.items()},
                  "n_legal_shapes": nlegal}
        print(f"  impossible capitol counts for {N}x{N}: "
              f"{[k for k in range(0, N * N + 1) if k not in by_cap]}")
    json.dump(out, open("tilings_by_capitols.json", "w"), indent=1)
    print("\nsaved tilings_by_capitols.json")
