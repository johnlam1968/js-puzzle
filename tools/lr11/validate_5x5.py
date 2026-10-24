"""Validate the assumption ledger (lr11/assume.py) on the OFFICIAL 5x5 example.

The 5x5 example is the only official puzzle with a published solution, so it
is the only place where "the assumption reproduces every published number" can
be checked end to end.

It is also the place where the capitol rule bites: the official solution has
FOUR states of sizes 7, 4, 3, 11, and the 4-cell state has NO capitol
(it is the one whose 7 symmetries fix 0 cells under rot180).  A value-only
calculation that assumes "every state has a capitol" gets this example wrong.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lr11 import assume as A

REPO = "/workspace/pz/src_tree/js-puzzle-docs-aodfs-layman"
PUZ = os.path.join(REPO, "data/puzzles/official-example-5x5")


def main() -> int:
    puzzle = json.load(open(os.path.join(PUZ, "puzzle.json")))
    truth = json.load(open(os.path.join(PUZ, "truth.json")))

    labels = truth["states"]                       # 5 rows of state labels
    n = puzzle["size"]
    states = []
    for lab in sorted({x for row in labels for x in row}):
        cells = frozenset((r, c) for r in range(n) for c in range(n)
                          if labels[r][c] == lab)
        states.append(cells)

    published = {}
    for h in puzzle["hints"]:
        published[(h["row"] - 1, h["col"] - 1)] = h["value"]

    print("=" * 74)
    print("the official 5x5 solution, read as a set of ASSUMPTIONS")
    print("=" * 74)
    for S in states:
        rep = A.state_report(S, published)
        print(f"  size {rep['size']:>2}  sym={rep['symmetry']}  capitol={rep['capitol']}")
        for issue in rep["issues"]:
            print(f"        ! {issue}")

    rep = A.analyse(states, published, n=n)
    print(f"\n  known capitols : {rep['known_capitols']}")
    print(f"  covered / free  : {rep['covered_cells']} / {rep['free_cells']}")
    print(f"  violations      : {rep['violations'] or 'none'}")
    verdicts = [v["verdict"] for v in rep["verdicts"].values()]
    print(f"  verdicts        : { {v: verdicts.count(v) for v in set(verdicts)} }")

    # the real d field, for comparison
    sys.path.insert(0, os.path.join(REPO, "src"))
    from rules import capitol_of  # noqa: E402
    import heapq
    sizes = {c: len(S) for S in states for c in S}
    caps = []
    for S in states:
        c = capitol_of(S)
        if c is not None:
            caps.append(c)
    dist = {}
    pq = []
    for c in caps:
        dist[c] = 0
        heapq.heappush(pq, (0, c))
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1 << 30):
            continue
        for dr, dc in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            v = (u[0] + dr, u[1] + dc)
            if not (0 <= v[0] < n and 0 <= v[1] < n):
                continue
            w = min(sizes[u], sizes[v])
            if d + w < dist.get(v, 1 << 30):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))

    bad = []
    for c, v in published.items():
        if dist.get(c) != v:
            bad.append((c, v, dist.get(c)))
    print(f"\n  the ledger reproduces every published hint: {not bad}  {bad}")

    # and the answer
    rows = [sum(sizes[(r, c)] for c in range(n)) for r in range(n)]
    print(f"  row sums {rows}  answer {sum(x*x for x in rows)} "
          f"(official {truth['answer']})")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
