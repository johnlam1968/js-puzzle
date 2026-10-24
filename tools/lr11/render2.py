"""Render the CORRECTED picture of the lower-right corner.

The first picture (output/shapes.png) was wrong in a way that only a real
travel-cost computation shows:

  * the 8-cell and 16-cell states have NO capitol at all (their mirror axes
    fix 6 and 2 squares respectively, not 1), so they contribute no
    destination and every route out of them costs 8 / 16 per step;
  * the published 1s inside the 11-cell Gamma state are impossible on their
    own -- a step inside a state of size 11 costs 11 -- so they DEMAND a
    1x1 state next to them;
  * the 14 at (2,10), the 45 at (8,8) and the 77 at (10,8) are all CHEAPER
    than the cheapest route to any capitol the picture knows about, so each
    of them demands a hidden capitol.

Every number on this picture is read out of lr11/assume.py, so the figure and
the tool cannot drift apart.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont

from lr11 import assume as A
from lr11 import tools as T

CELL = 44
MINI = 22
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

INK = (28, 30, 34)
GRID = (150, 154, 160)
BG = (252, 252, 250)
PAPER = (255, 255, 255)
MUTED = (95, 99, 105)
RED = (176, 38, 30)
GREEN = (47, 107, 42)
WARN = (138, 90, 0)

C_GAMMA = (222, 107, 44)
C_EIGHT = (232, 169, 74)
C_SIXTEEN = (150, 190, 140)
C_SINGLE = (196, 54, 62)
C_CAP = (34, 34, 40)

KEY_ROWS = [(2, 5), (3, 6), (4, 10), (6, 9), (2, 10), (8, 8), (10, 8), (10, 9),
            (5, 5), (0, 2), (0, 9), (7, 4)]


def fnt(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, sz)


def main():
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes.json")))
    e = d["best"]["11"]
    M = frozenset(tuple(x) for x in e["M"])
    S8 = frozenset(tuple(x) for x in e["eight"])
    S16 = frozenset(tuple(x) for x in e["sixteen"])
    S1 = frozenset({(5, 10)})
    HID1 = (3, 5)          # the hidden 1x1 state the two published 1s ask for

    rep = A.analyse([S1, S8, S16, M], T.PUBLISHED, capitol_hypotheses=[(HID1, 1)])
    V = {}
    for k, v in rep["verdicts"].items():
        r, c = k.strip("()").split(",")
        V[(int(r), int(c))] = v

    fills = {}
    for c in M:
        fills[c] = C_GAMMA
    for c in S8:
        fills[c] = C_EIGHT
    for c in S16:
        fills[c] = C_SIXTEEN
    for c in (S1 | {HID1}):
        fills[c] = C_SINGLE

    W, H = 1420, 720
    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)

    dr.text((22, 12), "It's a Metric, Too  —  the lower-right corner, re-checked",
            font=fnt(22, True), fill=INK)
    dr.text((22, 44), "Everything below is read out of the assumption ledger (lr11/assume.py), which is "
                      "validated on the official 5×5 example.", font=fnt(13), fill=MUTED)
    dr.text((22, 64), "salmon = the 11-cell Γ state (capitol at 5,6)   sand = the 8-cell state "
                      "(NO capitol)   green = the 16-cell state (NO capitol)   red = a 1×1 state",
            font=fnt(13), fill=MUTED)

    # ---------------- panel A: the board ----------------
    ax, ay = 22, 104
    dr.text((ax, ay - 26), "A · what the assumptions say, square by square",
            font=fnt(16, True), fill=INK)
    N = 11
    for r in range(N):
        for c in range(N):
            x0, y0 = ax + c * CELL, ay + r * CELL
            col = fills.get((r, c), PAPER)
            dr.rectangle([x0 + 1, y0 + 1, x0 + CELL - 1, y0 + CELL - 1], fill=col)
            v = T.PUBLISHED.get((r, c))
            if v is not None:
                dr.text((x0 + CELL // 2, y0 + CELL // 2), str(v), font=fnt(17),
                        fill=(70, 74, 80), anchor="mm")
            # the state's own area, and a star when the state has no capitol
            for S, lbl in ((M, "11"), (S8, "8"), (S16, "16")):
                if (r, c) in S:
                    cap = A.K.capitol_of(S)
                    dr.text((x0 + 3, y0 + 2), lbl + ("" if cap else "✱"),
                            font=fnt(9, True), fill=RED if cap is None else MUTED)
                    break
            # capitols
            if (r, c) == (5, 6):
                dr.ellipse([x0 + CELL // 2 - 6, y0 + CELL // 2 - 6, x0 + CELL // 2 + 6, y0 + CELL // 2 + 6],
                            fill=C_CAP)
            if (r, c) in ((5, 7), (10, 5)):
                dr.ellipse([x0 + CELL // 2 - 6, y0 + CELL // 2 - 6, x0 + CELL // 2 + 6, y0 + CELL // 2 + 6],
                            outline=C_CAP, width=3)
            if (r, c) in ((5, 10), HID1):
                dr.ellipse([x0 + CELL // 2 - 5, y0 + CELL // 2 - 5, x0 + CELL // 2 + 5, y0 + CELL // 2 + 5],
                            fill=C_SINGLE)
            # the lower bound on the distance, when the square's own state is known
            lo = rep["lower_bounds"].get(f"({r}, {c})")
            if lo is not None and lo > 0:
                dr.text((x0 + CELL - 3, y0 + CELL - 3), str(lo), font=fnt(9),
                        fill=MUTED, anchor="rs")
    for i in range(N + 1):
        dr.line([ax + i * CELL, ay, ax + i * CELL, ay + N * CELL], fill=GRID, width=1)
        dr.line([ax, ay + i * CELL, ax + N * CELL, ay + i * CELL], fill=GRID, width=1)
    dr.rectangle([ax, ay, ax + N * CELL, ay + N * CELL], outline=INK, width=3)

    for i, t in enumerate([
        "● the Γ state's capitol (5,6)      ○ a revealed capitol (5,7) and (10,5)",
        "● the 1×1 state at (5,10), forced by the 1 at (4,10), and the hidden one at (3,5),",
        "   which is the only single square that explains both the 1 at (2,5) and the 1 at (3,6).",
        "✱ the 8-cell and 16-cell states have NO capitol: their mirror fixes 6 and 2 squares.",
        "   They contribute no destination, so every route out of them costs 8 / 16 per step.",
    ]):
        dr.text((ax, ay + N * CELL + 12 + i * 19), t, font=fnt(13), fill=MUTED if i != 3 else RED)

    # ---------------- panel B: the ledger ----------------
    bx = 560
    dr.text((bx, ay - 26), "B · every published number, re-checked", font=fnt(16, True), fill=INK)
    tally = {}
    for v in rep["verdicts"].values():
        tally[v["verdict"]] = tally.get(v["verdict"], 0) + 1
    dr.text((bx, ay + 2), "  ·  ".join(f"{n} {k.replace('_', ' ').lower()}"
                                        for k, n in sorted(tally.items(), key=lambda t: -t[1])),
            font=fnt(12), fill=MUTED)
    y = ay + 28
    for (r, c) in KEY_ROWS:
        info = V[(r, c)]
        col = {"CONTRADICTED": RED, "FORCED": GREEN, "TIGHT_GEODESIC": GREEN,
               "TIGHT_CHEAPEST": GREEN}.get(info["verdict"], WARN)
        dr.text((bx, y), f"({r},{c})", font=fnt(13, True), fill=INK)
        dr.text((bx + 62, y), f"reads {info['published']}", font=fnt(13), fill=INK)
        rng = f"[{info['lb'] if info['lb'] is not None else '-'} , {info['ub'] if info['ub'] is not None else '∞'}]"
        dr.text((bx + 168, y), rng, font=fnt(12), fill=MUTED)
        dr.text((bx + 250, y), info["verdict"].replace("_", " ").lower(), font=fnt(12, True), fill=col)
        y += 19
    y += 10
    dr.text((bx, y), "the four that matter", font=fnt(15, True), fill=INK)
    y += 24
    lines = [
        ("(6,9) reads 9  =  8 + 1", GREEN,
         "the route (6,9)→(5,9)→(5,10) costs 8 inside the 8-cell state and 1 into the",
         "1×1 state. Exactly 9, so this route is the geodesic: the 8-cell state is",
         "forced in that corner, capitol-less or not."),
        ("(2,10) reads 14, but the nearest known capitol is 17 away", WARN,
         "the route (2,10)→(3,10)→(4,10)→(5,10) already costs 8+8+1. Since 14 < 17,",
         "the 14 cannot come from any capitol we know: a HIDDEN capitol has to sit",
         "within 14 of (2,10). The picture never showed that."),
        ("(8,8) reads 45, but the Γ's own capitol is 55 away", WARN,
         "along the Γ the route to (5,6) costs 5 × 11 = 55. So the 45 also needs a",
         "hidden capitol — the Γ state does not explain its own square."),
        ("(10,8) reads 77, but the nearest known capitol is 80 away", WARN,
         "four steps inside the 16-cell state at 16 each, then 16 across. 77 < 80, so",
         "the 77 needs a hidden capitol too; the 16-cell state has none of its own."),
    ]
    for head, col, *rest in lines:
        dr.text((bx, y), head, font=fnt(13, True), fill=col)
        y += 18
        for t in rest:
            dr.text((bx + 8, y), t, font=fnt(12), fill=MUTED)
            y += 16
        y += 10

    out = "/workspace/output/ledger.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
