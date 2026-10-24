"""Self-tests for `lr11/kernel.py`.

Three independent checks:

1. OFFICIAL 5x5 EXAMPLE -- reconstruct the published example and check every
   published number, the capitols, the row sums and the answer (8,045).
2. REPO 4x4 COUNTEREXAMPLE -- the two legal partitions with answers 304 and 112.
3. DIFFERENTIAL TEST -- compare my kernel against the repository's
   `src/rules.py` (the "executable specification") on thousands of random
   connected shapes: symmetry group, capitol, legality.

Run:  python3 lr11/selftest.py
"""

from __future__ import annotations

import importlib.util
import os
import random
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from lr11 import kernel as K          # package layout
except ImportError:                       # flat layout (tools/lr11/)
    import kernel as K                    # type: ignore

REPO_SRC = os.environ.get(
    "JS_PUZZLE_SRC",
    "/workspace/pz/src_tree/js-puzzle-docs-aodfs-layman/src",
)


# --------------------------------------------------------------------------- #
# 1. official 5x5 example
# --------------------------------------------------------------------------- #
def official_5x5() -> bool:
    n = 5
    # state ids: 0=purple(7) 1=blue(4) 2=green(3) 3=red(11)
    layout = [
        [0, 1, 1, 3, 3],
        [0, 1, 1, 2, 3],
        [0, 0, 2, 2, 3],
        [3, 0, 0, 0, 3],
        [3, 3, 3, 3, 3],
    ]
    labels = layout
    groups: List[List[Tuple[int, int]]] = [[] for _ in range(4)]
    for r in range(n):
        for c in range(n):
            groups[labels[r][c]].append((r, c))

    caps = {i: K.capitol_of(set(g)) for i, g in enumerate(groups)}
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f"  FAIL {label}: got {got!r}, want {want!r}")
        else:
            print(f"  ok   {label}: {got!r}")

    print("official 5x5 example")
    chk("state sizes", [len(g) for g in groups], [7, 4, 3, 11])
    chk("capitols (0-based)", sorted(c for c in caps.values() if c), [(2, 1), (2, 3), (4, 4)])
    chk("blue 2x2 has no capitol", caps[1], None)

    sizes = [[len(groups[labels[r][c]]) for c in range(n)] for r in range(n)]
    capitols = [c for c in caps.values() if c is not None]
    d = K.cost_field(sizes, n, capitols)

    published = {(0, 0): 12, (0, 4): 17, (1, 0): 8, (1, 2): 6, (1, 3): 3,
                 (3, 1): 7, (3, 2): 6, (3, 4): 10, (4, 0): 25, (4, 4): 0}
    bad = {k: (d[k[0]][k[1]], v) for k, v in published.items() if d[k[0]][k[1]] != v}
    chk("all 10 published numbers", bad, {})

    rs = K.row_sums(sizes, n)
    chk("row sums", rs, [37, 29, 31, 43, 55])
    chk("answer", K.answer(rs), 8045)
    return ok


# --------------------------------------------------------------------------- #
# 2. repo 4x4 counterexample
# --------------------------------------------------------------------------- #
def counterexample_4x4() -> bool:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f"  FAIL {label}: got {got!r}, want {want!r}")
        else:
            print(f"  ok   {label}: {got!r}")

    print("repo 4x4 counterexample")
    partitions = {
        "A row0 = one 1x4 bar": (
            [[0, 0, 0, 0], [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],
            304,
        ),
        "B row0 = two 1x2 dominoes": (
            [[0, 0, 5, 5], [1, 2, 3, 4], [6, 7, 8, 9], [10, 11, 12, 13]],
            112,
        ),
    }
    for name, (labels, want_answer) in partitions.items():
        n = 4
        groups = {}
        for r in range(n):
            for c in range(n):
                groups.setdefault(labels[r][c], []).append((r, c))
        sizes = [[len(groups[labels[r][c]]) for c in range(n)] for r in range(n)]
        caps = [K.capitol_of(set(g)) for g in groups.values()]
        caps = [c for c in caps if c is not None]
        d = K.cost_field(sizes, n, caps)
        rs = K.row_sums(sizes, n)
        chk(f"{name}: answer", K.answer(rs), want_answer)
        # the published d-field of this instance: row0 all 1, rows 1..3 all 0
        want_d = [[1] * 4, [0] * 4, [0] * 4, [0] * 4]
        chk(f"{name}: d-field", d, want_d)
    return ok


# --------------------------------------------------------------------------- #
# 3. differential test against the repository's rules.py
# --------------------------------------------------------------------------- #
def _load_repo_rules():
    path = os.path.join(REPO_SRC, "rules.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("repo_rules", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def differential(n_samples: int = 4000, size: int = 7) -> bool:
    repo = _load_repo_rules()
    if repo is None:
        print("differential test: SKIP (repo src/rules.py not found at "
              f"{REPO_SRC})")
        return True
    rng = random.Random(20261024)
    mismatches = []
    checked = 0
    for _ in range(n_samples):
        # random connected blob
        start = (rng.randrange(size), rng.randrange(size))
        cells = {start}
        target = rng.randint(1, 14)
        while len(cells) < target:
            r, c = rng.choice(sorted(cells))
            dr, dc = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < size and 0 <= nb[1] < size:
                cells.add(nb)
        mine_group = K.symmetry_group(cells)
        repo_group = repo.symmetry_group(cells)
        mine_fixed = {k: set(v) for k, v in mine_group.items()}
        repo_fixed = {k: set(v) for k, v in repo_group.items()}
        mine_cap = K.capitol_of(cells)
        repo_cap = repo.capitol_of(cells)
        mine_legal = K.is_legal_state(cells)
        repo_legal = repo.is_legal_state(cells)
        checked += 1
        if mine_fixed != repo_fixed or mine_cap != repo_cap or mine_legal != repo_legal:
            mismatches.append((sorted(cells), mine_fixed, repo_fixed, mine_cap, repo_cap))

    print(f"differential test: {checked} random shapes")
    if mismatches:
        print(f"  FAIL: {len(mismatches)} mismatches")
        for m in mismatches[:3]:
            print("   cells:", m[0])
            print("     mine group:", m[1], " repo group:", m[2])
            print("     mine capitol:", m[3], " repo capitol:", m[4])
        return False
    print("  ok   symmetry group, capitol and legality agree on every shape")
    return True



def differential_diagonal(n_samples: int = 3000, size: int = 9) -> bool:
    """Targeted differential test on shapes that HAVE a diagonal symmetry.

    Random blobs almost never have one, so the generic differential test barely
    exercises refD1/refD2 and the half-lattice 90-degree rotations.  Here the
    shapes are built symmetrically on purpose.
    """
    repo = _load_repo_rules()
    if repo is None:
        print("diagonal differential test: SKIP (no repo rules.py)")
        return True
    rng = random.Random(99)
    bad = 0
    checked = 0
    for _ in range(n_samples):
        # build a shape symmetric under the transpose (r <-> c) around a random
        # diagonal, then optionally glue a few symmetric pieces
        cells = set()
        for _ in range(rng.randint(1, 8)):
            r = rng.randrange(size)
            c = rng.randrange(size)
            cells.add((r, c))
            cells.add((c, r))
        if not cells:
            continue
        mine = {k: set(v) for k, v in K.symmetry_group(cells).items()}
        theirs = {k: set(v) for k, v in repo.symmetry_group(cells).items()}
        mc, rc = K.capitol_of(cells), repo.capitol_of(cells)
        ml, rl = K.is_legal_state(cells), repo.is_legal_state(cells)
        checked += 1
        if mine != theirs or mc != rc or ml != rl:
            bad += 1
            if bad <= 3:
                print("   MISMATCH", sorted(cells))
                print("     mine:", mine, mc, ml)
                print("     repo:", theirs, rc, rl)
    print(f"diagonal differential test: {checked} symmetric shapes")
    if bad:
        print(f"  FAIL: {bad} mismatches")
        return False
    print("  ok   symmetry group, capitol and legality agree on every symmetric shape")
    return True


def main() -> int:
    results = [official_5x5(), counterexample_4x4(), differential(),
               differential_diagonal()]
    print()
    if all(results):
        print("ALL GREEN")
        return 0
    print("FAILURES PRESENT")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
