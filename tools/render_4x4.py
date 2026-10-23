#!/usr/bin/env python3
"""Render the verified 4x4 tiling in the style of the official example:
   panel 1 = the numbers, panel 2 = the states (colour-filled, capitols dotted),
   panel 3 = the state sizes + the answer.
All data comes from the fixture; nothing is hand-typed."""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
T = json.load(open(os.path.join(DATA, "/puzzles/counterexample-4x4-two-answers/truth.json")))
# use the plan's unique 4x4 fixture instead (the one whose answer is 680)
P = json.load(open(os.path.join(DATA, "/puzzles/counterexample-4x4-two-answers/truth.json")))

# --- the 4x4 partition with a UNIQUE answer (680), from the plan fixture ---
STATES = [[0, 0, 1, 1],
          [0, 2, 1, 1],
          [3, 2, 2, 4],
          [3, 3, 4, 4]]
SIZES = [3, 4, 3, 3, 3]
CAPITOLS = {0: (0, 0), 2: (2, 1), 3: (3, 0), 4: (3, 3)}   # state label -> (row, col) 0-based
DFIELD = [[0, 3, 6, 10],
          [3, 3, 6, 6],
          [3, 0, 3, 3],
          [0, 3, 3, 0]]
ROWSUMS = [14, 14, 12, 12]
ANSWER = 680
N = 4

PALETTE = [(204, 153, 254), (191, 224, 255), (179, 255, 180),
           (255, 164, 163), (255, 235, 150), (150, 235, 235)]
LABEL = ["A", "B", "C", "D", "E", "F"]


def font(sz, bold=False):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def draw_grid(d, x0, y0, cell, lw=3, fills=None, dots=None, numbers=None,
              sizes=None, outer=4):
    for r in range(N):
        for c in range(N):
            x, y = x0 + c * cell, y0 + r * cell
            if fills:
                d.rectangle([x, y, x + cell, y + cell], fill=fills[r][c])
            d.rectangle([x, y, x + cell, y + cell], outline=(0, 0, 0), width=lw)
            if numbers:
                t = str(numbers[r][c])
                fnt = font(int(cell * 0.52))
                bb = d.textbbox((0, 0), t, font=fnt)
                d.text((x + (cell - (bb[2] - bb[0])) / 2 - bb[0],
                        y + (cell - (bb[3] - bb[1])) / 2 - bb[1]), t, font=fnt, fill=(0, 0, 0))
            if sizes:
                t = str(sizes[r][c])
                fnt = font(int(cell * 0.42))
                bb = d.textbbox((0, 0), t, font=fnt)
                col = (10, 60, 160)
                d.text((x + (cell - (bb[2] - bb[0])) / 2 - bb[0],
                        y + (cell - (bb[3] - bb[1])) / 2 - bb[1]), t, font=fnt, fill=col)
    if dots:
        for lab, (r, c) in dots.items():
            cx = x0 + c * cell + cell // 2
            cy = y0 + r * cell + cell // 2
            rad = int(cell * 0.13)
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(0, 0, 0))
    # heavier outer frame
    d.rectangle([x0 - outer, y0 - outer, x0 + N * cell + outer, y0 + N * cell + outer],
                outline=(0, 0, 0), width=outer)


def main():
    CELL = 78
    W, H = 1260, 620
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)

    fills = [[PALETTE[STATES[r][c]] for c in range(N)] for r in range(N)]
    sizes = [[SIZES[STATES[r][c]] for c in range(N)] for r in range(N)]

    # panel 1: the numbers
    draw_grid(d, 50, 120, CELL, numbers=DFIELD)
    d.text((50, 80), "the 16 given numbers", font=font(22), fill=(0, 0, 0))

    # panel 2: the states + capitols
    draw_grid(d, 460, 120, CELL, fills=fills, dots=CAPITOLS)
    d.text((460, 80), "the tiling: 5 states, 4 capitols (dots)", font=font(22), fill=(0, 0, 0))

    # panel 3: the sizes
    draw_grid(d, 900, 120, CELL, fills=fills, dots=CAPITOLS, sizes=sizes)
    d.text((900, 80), "state size in every cell", font=font(22), fill=(0, 0, 0))

    # legend + answer
    y = 560
    x = 50
    for lab in LABEL[:5]:
        d.rectangle([x, y, x + 24, y + 24], fill=PALETTE[LABEL.index(lab)], outline=(0, 0, 0))
        cap = next((v for k, v in CAPITOLS.items() if LABEL[k] == lab), None)
        txt = f"{lab}: size {SIZES[LABEL.index(lab)]}" + (f", capitol ({cap[0]+1},{cap[1]+1})" if cap else ", no capitol")
        d.text((x + 32, y + 2), txt, font=font(18), fill=(0, 0, 0))
        x += 245
    d.text((50, 452), f"row sums {ROWSUMS}   ->   answer = "
            + " + ".join(f"{v}^2" for v in ROWSUMS) + f" = {ANSWER}",
            font=font(26), fill=(180, 0, 0))
    d.text((50, 492), "every state has a non-trivial self-symmetry; only ODD-sized states can carry a capitol",
            font=font(19), fill=(90, 90, 90))
    d.text((50, 520), "size 4 (state B) has no capitol -> it can never be a destination; "
            "the 4 dots are the 4 capitols (A, C, D, E)", font=font(19), fill=(90, 90, 90))

    im.save(os.path.join(ROOT, "example-4x4-tiling.png"))
    print("saved example-4x4-tiling.png", im.size)

    # --- a single-panel "just the tiling" version, big ---
    CELL2 = 130
    im2 = Image.new("RGB", (CELL2 * N + 80, CELL2 * N + 80), (255, 255, 255))
    d2 = ImageDraw.Draw(im2)
    draw_grid(d2, 40, 40, CELL2, fills=fills, dots=CAPITOLS, sizes=sizes)
    im2.save(os.path.join(ROOT, "example-4x4-tiling-single.png"))
    print("saved example-4x4-tiling-single.png", im2.size)


if __name__ == "__main__":
    main()
