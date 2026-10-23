"""Offline table of every tiling of a small frame: d-field -> (answer, count).

Why: the judge is fast when the hints are DENSE (the prune kills the tree) and slow when
they are sparse.  But the generator needs both ends: uniqueness of the FULL hint set
(dense, fast) and the minimal hint set (sparse, slow).  So we pay the enumeration once
and answer every subsequent question by table scan.

The table is a cache, not a deliverable: it is written to data/derived/ and gitignored.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost import Puzzle
from tilings import Catalogue

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CACHE_DIR = os.path.join(ROOT, "data", "derived")


def table_path(n: int) -> str:
    return os.path.join(CACHE_DIR, f"tiling_table_{n}x{n}.npz")


def _one_partition(args):
    (n, masks) = args
    cells = [(r, c) for r in range(n) for c in range(n)]
    st = [[0] * n for _ in range(n)]
    for lab, m in enumerate(masks):
        for i in range(n * n):
            if (m >> i) & 1:
                r, c = cells[i]
                st[r][c] = lab
    puz = Puzzle([{(r, c) for r in range(n) for c in range(n) if st[r][c] == lab}
                  for lab in range(max(max(row) for row in st) + 1)])
    if not puz.capitols:
        return None
    d = puz.cost_field()
    if any(v == float("inf") for row in d for v in row):
        return None
    return ([int(v) for row in d for v in row], puz.answer())


def build_table(n: int, workers: int = 0) -> str:
    """Enumerate every legal tiling of the n x n frame and store (d-field, answer)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cat = Catalogue(n)
    bycell = cat.by_cell
    parts: List[Tuple[int, ...]] = []

    def rec(rem: int, chosen: List[int]):
        if rem == 0:
            parts.append(tuple(chosen))
            return
        first = (rem & -rem).bit_length() - 1
        for m in bycell[first]:
            if m & ~rem:
                continue
            rec(rem ^ m, chosen + [m])

    rec((1 << (n * n)) - 1, [])
    print(f"[{n}x{n}] {len(parts):,} legal tilings -- computing cost fields", flush=True)
    t0 = time.time()
    fields = np.full((len(parts), n * n), -1, dtype=np.int16)
    answers = np.full(len(parts), -1, dtype=np.int32)
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    if workers > 1:
        import multiprocessing as mp
        with mp.Pool(workers) as pool:
            for k, res in enumerate(pool.imap(_one_partition, ((n, p) for p in parts), chunksize=500)):
                if res is not None:
                    fields[k] = res[0]
                    answers[k] = res[1]
                if k % 100000 == 0:
                    print(f"   {k:,}/{len(parts):,}  ({time.time()-t0:.0f}s)", flush=True)
    else:
        for k, p in enumerate(parts):
            res = _one_partition((n, p))
            if res is not None:
                fields[k] = res[0]
                answers[k] = res[1]
    keep = answers >= 0
    fields, answers = fields[keep], answers[keep]
    path = table_path(n)
    np.savez_compressed(path, fields=fields, answers=answers)
    print(f"[{n}x{n}] table saved: {len(answers):,} rows -> {path} "
          f"({os.path.getsize(path)/1e6:.1f} MB, {time.time()-t0:.0f}s)", flush=True)
    return path


def load_table(n: int):
    path = table_path(n)
    if not os.path.exists(path):
        return None
    try:
        d = np.load(path)
        return d["fields"], d["answers"]
    except Exception:
        return None


def answers_for_hints(fields: np.ndarray, answers: np.ndarray, n: int,
                      hints: Dict[Tuple[int, int], int]) -> Tuple[List[int], int]:
    """All answers produced by tilings whose cost field agrees with the hints on every
    hinted cell.  Returns (sorted distinct answers, number of matching tilings)."""
    mask = np.ones(len(fields), dtype=bool)
    for (r, c), v in hints.items():
        mask &= fields[:, r * n + c] == v
    sel = answers[mask]
    if len(sel) == 0:
        return [], 0
    return sorted(set(int(x) for x in sel)), int(len(sel))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    build_table(n)
