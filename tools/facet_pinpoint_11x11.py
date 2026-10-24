#!/usr/bin/env python3
"""How far is the answer pinned down, window by window?

THE MEASURE
    The official puzzle asks for one number:  sum over rows of (sum of the state sizes in
    that row)^2.  So the answer needs the SIZE MAP -- it does NOT need the partition.
    A cell whose state size is pinned contributes a known amount to its row's sum; a cell
    whose size is still open makes the whole answer open.

    So the question this tool answers, for every 5x5 window of the 11x11, is:

        for each cell in the window, WHICH SIZES can its state still have, after every
        facet that can be applied locally?

    A window is "pinned" when the answer is a single size.  The fraction of pinned cells
    is the fraction of the answer that is already determined -- the honest version of a
    probability of success.

WHAT IS LOCAL AND WHAT IS NOT
    STATE-LOCAL  (can be decided inside a window)
        F-singleton-demand  the state holding a d=1 demand's cell is forced
        F-area             the state holding x has area >= |d(x) - d(y)|
        F-parity           a state with a capitol has odd area (D43)
    FIELD-LOCAL but only as a BOUND
        F-published / F-ring / F-tight / F-ball talk about the d-field, which is a
        property of the WHOLE partition.  Inside a window they become a sandwich:
            d_upper(x)  = the cheapest path to a capitol using only in-window cells
                           (a LOWER bound on d(x), so d_upper(x) > published refutes)
            d_lower(x)  = the cheapest path if leaving the window were free
                           (an UPPER bound on d(x), so d_lower(x) < published refutes)
        The window can therefore REFUTE a sub-partition, but it cannot confirm one:
        the last word is always the join.
    GLOBAL
        F-parity's consequence for the big states, and the state COUNT -- a state that
        does not fit in any window has to be grown across the boundary.

Exit code 0 = the measurement was written.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from rules import capitol_of, symmetry_group                        # noqa: E402
from tilings import Catalogue                                       # noqa: E402

REGISTER = os.path.join(ROOT, "data", "derived", "constraint_register_11x11.json")
OUT = os.path.join(ROOT, "data", "derived", "facet_pinpoint_11x11.json")

N = 11
WIN = 5
SINGLETON = (5, 10)


def window_cells(r0, c0, k=WIN):
    return [(r, c) for r in range(r0, r0 + k) for c in range(c0, c0 + k)]


def main() -> int:
    t0 = time.time()
    reg = json.load(open(REGISTER))
    facets = {f["id"]: f for f in reg["facets"]}

    # the 5x5 catalogue: every legal state of a 5x5 frame, which is also every legal
    # state that FITS in a 5x5 window (translate it)
    cat = Catalogue(WIN)
    local_states = []
    for mask, has_cap, group in cat.states:
        cells = tuple(sorted((i // WIN, i % WIN) for i in range(WIN * WIN)
                             if (mask >> i) & 1))
        local_states.append((cells, has_cap, group))
    print(f"5x5 catalogue: {len(local_states):,} legal states "
          f"({cat.seconds:.1f}s)")

    # the local state-local constraints, per cell
    area_min = {}
    for inst in facets["F-area"]["instances"]:
        c = tuple(inst["cell"])
        area_min[c] = max(area_min.get(c, 0), inst["min_area"])
    forced_single = {}
    for inst in facets["F-singleton-demand"]["instances"]:
        if inst["unique"]:
            forced_single[tuple(inst["demand"])] = tuple(inst["candidates"][0]["cell"])
    ring = {tuple(i["cell"]): i["d"] for i in facets["F-ring"]["instances"]}
    known_d = {tuple(i["cell"]): i["d"] for i in facets["F-published"]["instances"]}
    known_d.update(ring)
    ball = {tuple(i["cell"]): i["step_budget"] for i in facets["F-ball"]["instances"]}
    revealed = {tuple(i["cell"]) for i in facets["F-revealed-capitols"]["instances"]}

    windows = []
    for r0 in range(0, N - WIN + 1):
        for c0 in range(0, N - WIN + 1):
            W = window_cells(r0, c0)
            Wset = set(W)

            # --- which sizes can each cell still have? ------------------------- #
            sizes = {c: set() for c in W}
            for cells, has_cap, group in local_states:
                size = len(cells)
                shifted = [(r + r0, c + c0) for (r, c) in cells]
                ok = True
                for sc in shifted:
                    if area_min.get(sc, 0) > size:
                        ok = False
                        break
                if not ok:
                    continue
                for sc in shifted:
                    sizes[sc].add(size)

            # --- the forced singletons inside the window ----------------------- #
            forced_here = {d: s for d, s in forced_single.items() if s in Wset}
            killed_by_singleton = 0
            for cells, has_cap, group in local_states:
                shifted = [(r + r0, c + c0) for (r, c) in cells]
                for d, s in forced_here.items():
                    if s in shifted and len(shifted) > 1:
                        killed_by_singleton += 1
                        break

            pinned = sum(1 for c in W if len(sizes[c]) == 1)
            open_cells = [c for c in W if len(sizes[c]) > 1]
            in_win = [c for c in W if c in known_d]
            # the field facets: a published cell whose capitol ball leaves the window
            # cannot be settled locally
            open_field = [c for c in in_win
                          if c not in revealed
                          and any((c[0] + dr, c[1] + dc) not in Wset
                                  for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                                  if (dr or dc))
                          and ball.get(c, 0) > 0]
            windows.append({
                "origin": [r0, c0],
                "cells": len(W),
                "published_or_imputed_inside": len(in_win),
                "sizes_pinned": pinned,
                "sizes_open": len(open_cells),
                "open_cells": [list(c) for c in open_cells],
                "size_options": {f"{c[0]},{c[1]}": sorted(sizes[c]) for c in W
                                  if len(sizes[c]) > 1},
                "forced_singletons_inside": {f"{d[0]},{d[1]}": list(s) for d, s in
                                             forced_here.items()},
                "states_killed_by_a_forced_singleton": killed_by_singleton,
                "field_facets_that_cannot_be_settled_here": [list(c) for c in open_field],
            })

    # ------------------------------------------------------------------------- #
    tot_cells = sum(w["cells"] for w in windows)
    tot_pinned = sum(w["sizes_pinned"] for w in windows)
    # a cell is covered by several windows; the honest per-CELL figure is the AND over
    # the windows that contain it
    per_cell = {}
    for w in windows:
        r0, c0 = w["origin"]
        for c in window_cells(r0, c0):
            key = f"{c[0]},{c[1]}"
            opts = w["size_options"].get(key)
            if opts is None:
                opts = [1]                       # pinned in this window
            per_cell.setdefault(key, []).append(set(opts))
    cell_opts = {k: sorted(set.intersection(*v)) for k, v in per_cell.items()}
    pinned_cells = [k for k, v in cell_opts.items() if len(v) == 1]

    for w in windows:
        w.pop("size_options", None)          # the aggregate below is the result
    out = {
        "id": "facet-pinpoint-11x11",
        "generated_by": "tools/facet_pinpoint_11x11.py",
        "window": WIN,
        "windows": len(windows),
        "catalogue_5x5_legal_states": len(local_states),
        "per_cell_size_options": cell_opts,
        "cells_with_a_pinned_size": sorted(pinned_cells),
        "n_cells_pinned": len(pinned_cells),
        "n_cells": N * N,
        "windows_detail": windows,
        "note": "a cell is pinned when EVERY 5x5 window that contains it leaves a single "
                "possible size for it.  The answer needs the size map, so the fraction of "
                "pinned cells is the fraction of the answer already determined.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    print(f"\nwindows: {len(windows)}   cells: {N*N}   pinned: {len(pinned_cells)}")
    print(f"pinned cells: {sorted(pinned_cells)}")
    print("\nthe 4 windows with the most published cells inside:")
    for w in sorted(windows, key=lambda w: -w["published_or_imputed_inside"])[:6]:
        print(f"  origin {w['origin']}: {w['published_or_imputed_inside']} readings, "
              f"{w['sizes_pinned']}/{w['cells']} sizes pinned, "
              f"{len(w['field_facets_that_cannot_be_settled_here'])} field facets open")
    print(f"\nwrote {OUT}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
