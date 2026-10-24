"""Render the discovered lower-right shapes on the official 11x11 grid.

Produces /workspace/output/shapes.png:
  A) the official board, published numbers, the forced singleton and the two
     revealed capitols;
  B) the three candidate shapes of the (8,8) state (area 8 / 10 / 11), each on
     its own mini grid;
  C) the best surviving triple: Gamma state + 8-cell state + 16-cell state.

Deterministic drawing -- an image model would garble the numbers.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

Cell = Tuple[int, int]
N = 11
CELL = 46
MINI = 22
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

INK = (28, 30, 34)
GRID = (150, 154, 160)
BG = (252, 252, 250)
PAPER = (255, 255, 255)
MUTED = (95, 99, 105)

C_GAMMA = (222, 107, 44)
C_EIGHT = (52, 110, 196)
C_SIXTEEN = (26, 145, 132)
C_SINGLE = (196, 54, 62)
C_CAP = (34, 34, 40)

_here = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(_here, "shapes.json")))
PUB: Dict[Cell, int] = {}
for k, v in data["published"].items():
    r, c = k.split(",")
    PUB[(int(r), int(c))] = v
BEST = data["best"]


def fnt(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, sz)


def grid(d: ImageDraw.ImageDraw, ox: int, oy: int, sc: int,
         fills: Dict[Cell, Tuple[int, int, int]] = None,
         marks: Dict[Cell, str] = None,
         show_pub: bool = True, pub_size: int = 20) -> None:
    fills = fills or {}
    marks = marks or {}
    for r in range(N):
        for c in range(N):
            x0, y0 = ox + c * sc, oy + r * sc
            col = fills.get((r, c), PAPER)
            d.rectangle([x0 + 1, y0 + 1, x0 + sc - 1, y0 + sc - 1], fill=col)
            if (r, c) in marks:
                d.text((x0 + sc - 6, y0 + 6), marks[(r, c)], font=fnt(int(sc * 0.32), True),
                       fill=marks_color(marks[(r, c)]), anchor="rm")
            elif show_pub and (r, c) in PUB:
                d.text((x0 + sc // 2, y0 + sc // 2), str(PUB[(r, c)]), font=fnt(pub_size),
                       fill=(70, 74, 80), anchor="mm")
    for i in range(N + 1):
        d.line([ox + i * sc, oy, ox + i * sc, oy + N * sc], fill=GRID, width=1)
        d.line([ox, oy + i * sc, ox + N * sc, oy + i * sc], fill=GRID, width=1)
    d.rectangle([ox, oy, ox + N * sc, oy + N * sc], outline=INK, width=3 if sc > 30 else 2)


def marks_color(ch):
    return {"S": C_SINGLE, "C": C_CAP}.get(ch, INK)


def main():
    W = N * CELL
    img = Image.new("RGB", (1420, 1480), BG)
    d = ImageDraw.Draw(img)

    d.text((22, 14), "It's a Metric, Too  —  the first shapes of the lower-right corner",
           font=fnt(23, True), fill=INK)
    d.text((22, 48), "Jane Street, October 2026  ·  0-based (row, col)  ·  found by exhaustive "
                     "enumeration under the official rules, not guessed", font=fnt(14), fill=MUTED)
    d.text((22, 70), "orange = the (8,8) state (a Γ piece)    blue = the 8-cell state    "
                     "teal = the 16-cell state    red = the forced 1×1 state    "
                     "S = singleton    C = revealed capitol", font=fnt(14), fill=MUTED)

    ax, ay = 22, 120
    W = N * CELL

    # ---------------- A ----------------
    d.text((ax, ay - 28), "A · the board as published", font=fnt(17, True), fill=INK)
    grid(d, ax, ay, CELL,
         fills={(5, 10): C_SINGLE},
         marks={(5, 10): "S", (5, 7): "C", (10, 5): "C"})
    for i, t in enumerate([
        "33 published numbers.  (5,10) is a forced 1×1 state: the d=1 at (4,10) needs a",
        "singleton neighbour, and (3,10) / (4,9) are ruled out by the 14 at (2,10) and the 4 at (4,8)."]):
        d.text((ax, ay + W + 14 + i * 20), t, font=fnt(13), fill=MUTED)

    # ---------------- B ----------------
    bx = 572
    d.text((bx, ay - 28), "B · the (8,8) state — three candidate areas, one shape family",
           font=fnt(17, True), fill=INK)
    mini_w = N * MINI
    for i, (key, lbl) in enumerate([("8", "area 8"), ("10", "area 10"), ("11", "area 11")]):
        e = BEST[key]
        M = [tuple(x) for x in e["M"]]
        sx = bx + i * (mini_w + 24)
        grid(d, sx, ay, MINI,
             fills={(r, c): C_GAMMA for (r, c) in M},
             pub_size=11)
        d.text((sx, ay + mini_w + 8), f"{lbl} · {e['M_sym']}", font=fnt(12, True), fill=C_GAMMA)
    ty = ay + mini_w + 36
    for i, (t, col) in enumerate([
        ("The (8,8) state is a Γ: a spine plus a foot at (8,7),(8,8).  Area 8 gives ONE shape;", MUTED),
        ("areas 10 and 11 give the same shape one cell longer.  Area 11 is the most self-consistent:", MUTED),
        ("its rot180 fixes (5,6) so it carries a capitol, and 45 = 4×11 + 1 falls out exactly.", MUTED),
        ("The 12-cell reading (exit at (6,10)) is dead: (12-cell, 8-cell) has ZERO survivors,", (150, 60, 60)),
        ("and the killer is the 45 at (8,8).", (150, 60, 60))]):
        d.text((bx, ty + i * 20), t, font=fnt(13), fill=col)

    # ---------------- C ----------------
    cx, cy = ax, ay + W + 96
    d.text((cx, cy - 28), "C · best surviving triple", font=fnt(17, True), fill=INK)
    e = BEST["11"]
    fills: Dict[Cell, Tuple[int, int, int]] = {}
    for x in e["M"]:
        fills[tuple(x)] = C_GAMMA
    for x in e["eight"]:
        fills[tuple(x)] = C_EIGHT
    for x in e["sixteen"]:
        fills[tuple(x)] = C_SIXTEEN
    fills[(5, 10)] = C_SINGLE
    grid(d, cx, cy, CELL, fills=fills,
         marks={(5, 10): "S", (5, 7): "C", (10, 5): "C"})
    for i, t in enumerate([
        "Γ state (orange, 11 cells) + 8-cell state (blue) + 16-cell state (teal) + the 1×1 state (red)",
        "and the two revealed capitols.  Still 33 candidates for the 8-cell state; the next cut uses",
        "the published 6 at (3,8) and the 4 at (4,8)."]):
        d.text((cx, cy + W + 14 + i * 20), t, font=fnt(13), fill=MUTED)

    out = "/workspace/output/shapes.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
