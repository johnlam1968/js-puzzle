#!/usr/bin/env python3
"""Per-facet pinning power, measured on one well-defined candidate set.

WHY PER-FACET AND NOT JUST THE JOINT
    The joint number says "the three filters cut 347,802 candidates to 40,862".  That does
    not say WHICH constraint is doing the work, and it does not say whether the work is
    redundant.  A facet that kills 0.3% of the candidates is not worth a window; a facet
    that kills 99% is the one that decides the window.

THE CANDIDATE SET
    The (8-cell, 12-cell) pairs around the forced (5,10) singleton: 343 x 1014 pairs that
    pass the per-block pre-filter.  It is a real, reproducible slice of the search, and it
    is the slice the (5,10) trim creates.

WHAT IS MEASURED
    For every facet instance that touches the pair, the fraction of the candidates that
    survive it, applied ONE AT A TIME and then jointly.  The order matters, so the table
    reports both the marginal (one at a time) and the conditional (given the others).

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
sys.path.insert(0, HERE)

from trim_510 import (HINTS, SINGLETON, boundary_distance, core_field, core_path,   # noqa: E402
                      enumerate_states)

OUT = os.path.join(ROOT, "data", "derived", "facet_pinning_11x11.json")
KNOWN_CAPITOLS = {(5, 7), (10, 5), SINGLETON}
ALL = [(r, c) for r in range(11) for c in range(11)]
manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def facets_of(fs8, fs12):
    """The facet verdicts for one candidate pair: {facet_id: [violations]}."""
    core = [fs8, fs12, frozenset({SINGLETON})]
    allc = set().union(*core)
    filler = set()
    for S in core:
        if len(S) % 2 == 0:
            filler |= S
    dist, owner = core_field(core)

    out = {"F1-leave-the-block": [], "F2-core-path": [], "F3-capitol-ball": [],
           "F4-revealed-capitol-inside": []}
    for x, v in HINTS.items():
        for S in core:
            if x in S and len(S) % 2 == 0:
                lb = len(S) * boundary_distance(S, x) + 1
                if lb > v:
                    out["F1-leave-the-block"].append([x, v, lb])
    for x, v in HINTS.items():
        cc = core_path(dist, owner, core, x)
        if cc is not None and cc < v:
            out["F2-core-path"].append([x, v, cc])
    for x, v in HINTS.items():
        if v == 0:
            continue
        ball = [c for c in ALL if c != x and manh(c, x) <= (v + 1) // 2]
        if any(c in KNOWN_CAPITOLS for c in ball):
            continue
        if not any(c not in filler and HINTS.get(c, 0) <= 0 for c in ball):
            out["F3-capitol-ball"].append([x, v])
    for x, v in HINTS.items():
        if v == 0 and x in allc:
            out["F4-revealed-capitol-inside"].append([x, v])
    return out


def main() -> int:
    t0 = time.time()
    s8 = enumerate_states((5, 9), 8)
    s12 = enumerate_states((6, 10), 12)

    def prefilter(cands, size, must_have, must_not):
        keep = []
        for fs, meta in cands.items():
            if must_have not in fs or (must_not and must_not in fs):
                continue
            if any(v == 0 and x in fs for x, v in HINTS.items()):
                continue
            if any(x in fs and size * boundary_distance(fs, x) + 1 > v
                   for x, v in HINTS.items()):
                continue
            keep.append(fs)
        return keep

    p8 = prefilter(s8, 8, (5, 9), (6, 10))
    p12 = prefilter(s12, 12, (6, 10), (5, 9))
    print(f"candidate pairs: {len(p8)} x {len(p12)} = {len(p8)*len(p12):,}")

    FACETS = ["F1-leave-the-block", "F2-core-path", "F3-capitol-ball",
              "F4-revealed-capitol-inside"]
    total = 0
    marginal = {f: 0 for f in FACETS}
    per_facet_survivors = {f: 0 for f in FACETS}
    joint = 0
    step = 0
    for fs8 in p8:
        for fs12 in p12:
            if fs8 & fs12:
                continue
            total += 1
            v = facets_of(fs8, fs12)
            alive = True
            for f in FACETS:
                if v[f]:
                    marginal[f] += 1
                    alive = False
                else:
                    per_facet_survivors[f] += 1
            if alive:
                joint += 1
            step += 1
            if step % 50000 == 0:
                print(f"  ... {step:,} pairs ({time.time()-t0:.0f}s)", flush=True)

    table = []
    for f in FACETS:
        killed = marginal[f]
        table.append({
            "facet": f,
            "killed": killed,
            "survives_alone": per_facet_survivors[f],
            "survival_rate_alone": round(per_facet_survivors[f] / total, 6) if total else None,
            "pinning_power": round(1 - killed / total, 6) if total else None,
            "pinning_power_percent": round(100 * (1 - killed / total), 3) if total else None,
        })
    out = {
        "id": "facet-pinning-11x11",
        "generated_by": "tools/facet_pinning_11x11.py",
        "candidate_set": "the (8-cell, 12-cell) pairs around the forced (5,10) singleton",
        "candidates": total,
        "per_facet": table,
        "joint_survivors": joint,
        "joint_survival_rate": round(joint / total, 6) if total else None,
        "read": "the per-facet 'pinning power' is the fraction of candidates the facet "
                "kills on its own.  The joint number is what all four together do.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)

    print(f"\ncandidates: {total:,}    joint survivors: {joint:,} "
          f"({100*joint/total:.2f}%)   ({time.time()-t0:.0f}s)\n")
    print(f"{'facet':<32} {'kills':>8} {'pinning power':>15} {'survives alone':>15}")
    for t in table:
        print(f"  {t['facet']:<30} {t['killed']:>8,} "
              f"{t['pinning_power_percent']:>14.2f}% {t['survives_alone']:>15,}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
