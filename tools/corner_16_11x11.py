#!/usr/bin/env python3
"""The lower-right corner: the 16-cell block, and the "61 + 16 = 77" reading.

THE HUMAN'S READING
    d(10,8) = 77, d(10,9) = 61, and the difference is 16.  Going LEFT from (10,8) means
    stepping through larger states (more expensive), so the cheapest route is to go
    RIGHT, through (10,9): 16 for the crossing step, then 61 more to a capitol.

WHAT THE ENGINE SAYS ABOUT THAT READING
    * both cells are HIGH-d (2d > 121), so by M4 neither may be adjacent to a capitol
      of ANOTHER state.  The 16-cost step between them is therefore a CROSS-STATE step,
      and min(size(10,8), size(10,9)) = 16: ONE of the two states is exactly 16 cells.
    * the same-state reading (both cells in one 16-cell state) cannot work: the within-
      state step costs 16, and 61 - 16 = 45 is not a multiple of 16, so a 16-cell state
      cannot produce a d of 61 at (10,9) -- it would need a 61-cell state with (10,9)
      next to its own capitol.

    So there are two live candidates for the "16-block": the state of (10,8) or the state
    of (10,9).  This tool enumerates BOTH and says which ones survive the readings.

Exit code 0 = the table was written.
"""

from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from grow import close_state, grow_states, symmetry_choices   # noqa: E402

PUZZLE = os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")
OUT = os.path.join(ROOT, "data", "derived", "corner_16_11x11.json")

N = 11
A, B = (10, 8), (10, 9)          # the 77 cell and the 61 cell
SINGLETON = (5, 10)

_p = json.load(open(PUZZLE))
_G = _p["grid"]
HINTS = {(r, c): _G[r][c] for r in range(N) for c in range(N) if _G[r][c] is not None}
ALL = [(r, c) for r in range(N) for c in range(N)]
manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def nbs(cell):
    r, c = cell
    return [(rr, cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= rr < N and 0 <= cc < N]


def enumerate_states(anchor, size, blocked=(), budget=400_000):
    found = {}
    for sym in symmetry_choices(N):
        stats = {}
        for st in grow_states(anchor, sym, N, blocked=blocked, max_cells=size,
                              budget=budget, stats=stats):
            if len(st) != size:
                continue
            fs = frozenset(st)
            if fs in found:
                continue
            ok, cap, group = close_state(fs)
            if ok:
                found[fs] = {"capitol": list(cap) if cap else None,
                             "symmetries": list(group)}
    return found


def boundary_distance(S, x):
    if any(y not in S for y in nbs(x)):
        return 0
    seen, frontier, d = {x}, [x], 0
    while frontier:
        d += 1
        nxt = []
        for u in frontier:
            for v in nbs(u):
                if v in S and v not in seen:
                    seen.add(v)
                    if any(y not in S for y in nbs(v)):
                        return d
                    nxt.append(v)
        frontier = nxt
    return 99


def l1_ok(state):
    """The published cells inside the state must be able to leave it (size * dist + 1 <= d)."""
    bad = []
    for x, v in HINTS.items():
        if x in state:
            lb = len(state) * boundary_distance(state, x) + 1
            if lb > v:
                bad.append([list(x), v, lb])
    return bad


def render(state, extra=None):
    """An ASCII map of the corner with the state sizes."""
    rows = []
    for r in range(6, 11):
        row = []
        for c in range(6, 11):
            if (r, c) in state:
                row.append(f"{len(state):>3}")
            elif extra and (r, c) in extra:
                row.append(f"{len(extra[(r, c)]):>3}")
            else:
                row.append(f"{HINTS.get((r, c), '.'):>3}")
        rows.append(" ".join(row))
    return rows


def main() -> int:
    t0 = time.time()
    out = {"id": "corner-16-11x11", "generated_by": "tools/corner_16_11x11.py"}

    variants = {}
    for label, anchor, must_exclude in (
            ("the 16-block is the state of the 77 cell (10,8)", A, B),
            ("the 16-block is the state of the 61 cell (10,9)", B, A),
            ("the 16-block holds BOTH (10,8) and (10,9)", A, None)):
        st = enumerate_states(anchor, 16, blocked=({SINGLETON} | ({must_exclude}
                                                            if must_exclude else set())))
        keep, killed = {}, []
        for fs, meta in st.items():
            if any(v == 0 and x in fs for x, v in HINTS.items()):
                killed.append([sorted(list(c) for c in fs), "a revealed capitol inside"])
                continue
            bad = l1_ok(fs)
            if bad:
                killed.append([sorted(list(c) for c in fs), f"L1: {bad}"])
                continue
            keep[fs] = meta
        variants[label] = {
            "enumerated": len(st),
            "survive_the_per_block_filters": len(keep),
            "killed": len(killed),
            "examples": [sorted(list(c) for c in fs) for fs in list(keep)[:5]],
        }
        print(f"  {label}")
        print(f"      enumerated {len(st):>6}   survive {len(keep):>6}   killed {len(killed)}"
              f"   ({time.time()-t0:.0f}s)")
        for fs in list(keep)[:3]:
            print(f"        {sorted(fs)}")

    out["variants"] = variants
    out["reading"] = {
        "d(10,8)": 77, "d(10,9)": 61, "difference": 16,
        "both_high_d": True,
        "consequence": "min(size(10,8), size(10,9)) = 16, so one of them is exactly 16",
        "same_state_reading": "impossible: 61 - 16 = 45 is not a multiple of 16",
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {OUT}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
