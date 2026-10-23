#!/usr/bin/env python3
"""4x4 answer-level uniqueness, computed exactly.

Step 1: enumerate every legal partition of 4x4 (states = connected + symmetric).
Step 2: for each, compute its d-field and answer -> table.
Step 3: for ANY hint subset, the compatible partitions are those whose d-field
        matches on the hinted cells; the answer set is the set of their answers.
Step 4: with the table, ALL 2^16 hint subsets can be tested -> provably MINIMAL
        hint set, plus the greedy irreducible set for comparison.
"""
import heapq, itertools, json, sys, time
from engine import sym_info, connected

N = 4
cells = [(r, c) for r in range(N) for c in range(N)]
IDX = {c: i for i, c in enumerate(cells)}
NB = [0] * (N * N)
for i, (r, c) in enumerate(cells):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N: NB[i] |= 1 << IDX[(rr, cc)]

def legal_masks():
    """all masks that are a legal state (connected + non-trivial symmetry)"""
    out = []
    for mask in range(1, 1 << 16):
        seen = mask & -mask; frontier = seen
        while frontier:
            b = frontier & -frontier; frontier -= b; i = b.bit_length() - 1
            add = 0
            for j in range(N * N):
                if (NB[i] >> j) & 1 and (mask >> j) & 1 and not (seen >> j) & 1: add |= 1 << j
            seen |= add; frontier |= add
        if seen != mask: continue
        cl = [cells[i] for i in range(16) if (mask >> i) & 1]
        cap, names, fixes, fs = sym_info(cl)
        if names: out.append((mask, cap is not None))
    return out

def partitions(placements_by_cell):
    res = []
    def rec(rem, chosen):
        if rem == 0:
            res.append(tuple(chosen)); return
        first = (rem & -rem).bit_length() - 1
        for mask, hascap in placements_by_cell[first]:
            if mask & ~rem: continue
            rec(rem ^ mask, chosen + [mask])
    rec((1 << 16) - 1, [])
    return res

def analyse(masks):
    """d-field + answer + capitols for a partition given as list of masks"""
    owner = [0] * 16
    sizes = {}
    for lab, m in enumerate(masks):
        sizes[lab] = bin(m).count("1")
        mm = m
        while mm:
            b = mm & -mm; mm -= b; owner[b.bit_length() - 1] = lab
    caplab = {}
    for lab, m in enumerate(masks):
        cl = [cells[i] for i in range(16) if (m >> i) & 1]
        cap, names, fixes, fs = sym_info(cl)
        if cap is not None: caplab[lab] = cap
    INF = float("inf")
    dist = [INF] * 16
    pq = []
    for lab, (r, c) in caplab.items():
        dist[IDX[(r, c)]] = 0; heapq.heappush(pq, (0, IDX[(r, c)]))
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist[i]: continue
        r, c = cells[i]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < N and 0 <= cc < N): continue
            j = IDX[(rr, cc)]
            A, B = owner[i], owner[j]
            w = sizes[A] if A == B else min(sizes[A], sizes[B])
            if d + w < dist[j]: dist[j] = d + w; heapq.heappush(pq, (d + w, j))
    rows = [sum(sizes[owner[r * N + c]] for c in range(N)) for r in range(N)]
    return tuple(dist), sum(s * s for s in rows), rows

if __name__ == "__main__":
    t0 = time.time()
    pl = legal_masks()
    print(f"legal states: {len(pl)}  ({time.time()-t0:.1f}s)", flush=True)
    bycell = [[] for _ in range(16)]
    for m, hc in pl:
        mm = m
        while mm:
            b = mm & -mm; mm -= b; bycell[b.bit_length() - 1].append((m, hc))
    parts = partitions(bycell)
    print(f"legal partitions: {len(parts)}  ({time.time()-t0:.1f}s)", flush=True)
    table = {}
    for p in parts:
        df, ans, rows = analyse(p)
        table.setdefault(df, []).append(ans)
    print(f"distinct d-fields: {len(table)}  ({time.time()-t0:.1f}s)", flush=True)
    amb = sum(1 for v in table.values() if len(set(v)) > 1)
    print(f"  d-fields with >1 distinct answer: {amb}")
    mult = sum(1 for v in table.values() if len(v) > 1)
    print(f"  d-fields realised by >1 partition: {mult}")

    # the plan's 4x4 fixture
    FIX = tuple(x for row in [[0,3,6,10],[3,3,6,6],[3,0,3,3],[0,3,3,0]] for x in row)
    print(f"\nfixture d-field present? {FIX in table}  answers={sorted(set(table.get(FIX,[])))}  partitions={len(table.get(FIX,[]))}")
    assert FIX in table and set(table[FIX]) == {680} and len(table[FIX]) == 1

    # ---- answer-level uniqueness for ANY hint subset (from the table) ----
    def answers_for(hint_idx):
        out = set()
        for df, anss in table.items():
            if all(df[i] == FIX[i] for i in hint_idx):
                out |= set(anss)
        return out
    def unique(hint_idx):
        return len(answers_for(hint_idx)) == 1

    allidx = list(range(16))
    print(f"\nfull reveal (16 hints) unique? {unique(allidx)}  answers={sorted(answers_for(allidx))}")
    # ---- provably minimal hint set (exhaustive over 2^16 subsets) ----
    best = None
    for k in range(0, 17):
        for combo in itertools.combinations(allidx, k):
            if unique(list(combo)):
                best = combo; break
        if best is not None: break
    print(f"PROVABLY MINIMAL hint set: size={len(best)} cells={[ (i//N+1, i%N+1) for i in best ]}  values={[FIX[i] for i in best]}")
    print(f"  answers with that hint set: {sorted(answers_for(list(best)))}")
    # ---- greedy irreducible set (order: row-major) for comparison ----
    cur = list(allidx)
    for i in allidx:
        trial = [x for x in cur if x != i]
        if unique(trial): cur = trial
    print(f"greedy irreducible set: size={len(cur)} cells={[(i//N+1,i%N+1) for i in cur]} values={[FIX[i] for i in cur]}")
    json.dump({"minimal_hint_set": [[i // N + 1, i % N + 1] for i in best],
               "minimal_values": [FIX[i] for i in best],
               "minimal_size": len(best),
               "greedy_irreducible": [[i // N + 1, i % N + 1] for i in cur],
               "greedy_size": len(cur),
               "table_entries": len(table),
               "dfields_with_multiple_answers": amb},
              open(os.path.join(ROOT, "data", "puzzles", "counterexample-4x4-two-answers", "minimal_hints_4x4.json"), "w"), indent=1)
    print(f"\ntotal {time.time()-t0:.1f}s")
