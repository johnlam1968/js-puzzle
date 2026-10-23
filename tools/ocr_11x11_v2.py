#!/usr/bin/env python3
"""Self-supervised OCR: build digit templates from the EXAMPLE panel (whose 10 values are known
and independently verified), then classify the 11x11 grid glyphs with normalized IoU.

Validation: leave-one-out over the example's own known digits.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict

SRC = os.path.join(HERE, "metric-too.png"
im = Image.open(SRC).convert("L")
A = np.array(im).astype(int)
INK = A < 128

CANVAS = (20, 30)   # normalized glyph box (w, h)


def lines_from_runs(runs):
    return [(a + b) / 2.0 for a, b in runs]


def detect_lines(y0, y1, x0, x1, mincount):
    reg = INK[y0:y1, x0:x1]
    colp = reg.sum(axis=0); rowp = reg.sum(axis=1)
    out = []
    for prof, off, axis in ((colp, x0, "x"), (rowp, y0, "y")):
        rs, s = [], None
        for i, v in enumerate(prof):
            if v > mincount and s is None: s = i
            elif v <= mincount and s is not None:
                rs.append((s + off, i - 1 + off)); s = None
        if s is not None: rs.append((s + off, len(prof) - 1 + off))
        out.append(rs)
    return out[0], out[1]


def normalize(glyph):
    """scale glyph into a fixed canvas, preserving aspect, centred."""
    h, w = glyph.shape
    scale = min(CANVAS[0] / w, CANVAS[1] / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    img = Image.fromarray((glyph * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    arr = np.array(img) < 128
    canvas = np.zeros((CANVAS[1], CANVAS[0]), bool)
    oy = (CANVAS[1] - nh) // 2; ox = (CANVAS[0] - nw) // 2
    canvas[oy:oy + nh, ox:ox + nw] = arr
    return canvas


def glyphs_in(cellmask):
    colink = cellmask.any(axis=0)
    comps, s = [], None
    for i, v in enumerate(colink):
        if v and s is None: s = i
        elif not v and s is not None: comps.append((s, i - 1)); s = None
    if s is not None: comps.append((s, len(colink) - 1))
    out = []
    for a, b in comps:
        sub = cellmask[:, a:b + 1]
        rows = np.where(sub.any(axis=1))[0]
        out.append(sub[rows[0]:rows[-1] + 1])
    return out


def cell_crop(x0, x1, y0, y1, pad=7):
    return INK[int(round(y0 + pad)):int(round(y1 - pad)),
               int(round(x0 + pad)):int(round(x1 - pad))]


def iou(a, b):
    i = (a & b).sum(); u = (a | b).sum()
    return i / u if u else 0.0


# ---------------- 1. example panel geometry (left panel = input numbers) ----------------
ex_v, ex_h = detect_lines(1000, 1310, 60, 380, 200)
print("example panel vertical lines:", ex_v)
print("example panel horizontal lines:", ex_h)
ex_x = lines_from_runs(ex_v); ex_y = lines_from_runs(ex_h)
print("example x:", [round(v, 1) for v in ex_x])
print("example y:", [round(v, 1) for v in ex_y])

# known: 12@(1,1) 17@(1,5) 8@(2,1) 6@(2,3) 3@(2,4) 7@(4,2) 6@(4,3) 10@(4,5) 25@(5,1) 0@(5,5)
KNOWN = {(1, 1): "12", (1, 5): "17", (2, 1): "8", (2, 3): "6", (2, 4): "3",
         (4, 2): "7", (4, 3): "6", (4, 5): "10", (5, 1): "25", (5, 5): "0"}

bank = defaultdict(list)          # digit -> list of normalized glyphs
for (r, c), val in KNOWN.items():
    crop = cell_crop(ex_x[c - 1], ex_x[c], ex_y[r - 1], ex_y[r])
    gs = glyphs_in(crop)
    assert len(gs) == len(val), f"glyph count {len(gs)} != len({val}) at {(r,c)}"
    for g, ch in zip(gs, val):
        bank[ch].append(normalize(g))
print("\ntemplate digits from example:", {k: len(v) for k, v in sorted(bank.items())})

# synthetic templates for digits missing from the example bank (4 and 9)
FONTPATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
synth = defaultdict(list)
for fp in FONTPATHS:
    try: f = ImageFont.truetype(fp, 40)
    except Exception: continue
    for d in "0123456789":
        img = Image.new("L", (60, 80), 255); ImageDraw.Draw(img).text((10, 5), d, font=f, fill=0)
        arr = np.array(img) < 128
        rs = np.where(arr.any(axis=1))[0]; cs = np.where(arr.any(axis=0))[0]
        synth[d].append(normalize(arr[rs[0]:rs[-1] + 1, cs[0]:cs[-1] + 1]))

ALL = {d: bank.get(d, []) + synth[d] for d in "0123456789"}


def classify(glyph):
    n = normalize(glyph)
    scored = []
    for d, temps in ALL.items():
        best = max((iou(n, t) for t in temps), default=0.0)
        scored.append((best, d))
    scored.sort(reverse=True)
    return scored[0][1], scored[0][0], scored[1][0]


# ---------------- 2. leave-one-out validation on the example itself ----------------
print("\n--- leave-one-out validation on the example's own 10 numbers ---")
ok = 0
for (r, c), val in KNOWN.items():
    crop = cell_crop(ex_x[c - 1], ex_x[c], ex_y[r - 1], ex_y[r])
    got = ""
    for g in glyphs_in(crop):
        d, conf, _ = classify(g); got += d
    flag = "OK " if got == val else "FAIL"
    ok += (got == val)
    print(f"  {flag} ({r},{c}) truth={val} got={got}")
print(f"  validation: {ok}/10")

# ---------------- 3. classify the 11x11 grid ----------------
gx, gy = detect_lines(15, 810, 220, 1010, 300)
GX = lines_from_runs(gx); GY = lines_from_runs(gy)
print("\n11x11 vertical lines:", [round(v, 1) for v in GX])
print("11x11 horizontal lines:", [round(v, 1) for v in GY])

transcript, cellmap = {}, {}
for r in range(1, 12):
    for c in range(1, 12):
        crop = cell_crop(GX[c - 1], GX[c], GY[r - 1], GY[r])
        if not crop.any(): continue
        gs = glyphs_in(crop)
        digs = []
        for g in gs:
            d, conf, second = classify(g)
            digs.append((d, round(conf, 3), round(second, 3)))
        val = "".join(d for d, _, _ in digs)
        transcript[(r, c)] = val
        cellmap[(r, c)] = digs

print("\n--- 11x11 machine transcript (row,col=value  [conf]) ---")
for r in range(1, 12):
    items = [(c, transcript[(r, c)]) for c in range(1, 12) if (r, c) in transcript]
    if items:
        print(f"  row {r:2d}: " + "   ".join(f"c{c}={v}" for c, v in items))
print("total cells with ink:", len(transcript))

print("\n--- per-glyph confidence (sorted ascending = weakest first) ---")
weak = []
for k, digs in cellmap.items():
    for i, (d, conf, second) in enumerate(digs):
        weak.append((conf, second, k, i, d))
weak.sort()
for conf, second, k, i, d in weak[:12]:
    print(f"  conf={conf} second={second} cell={k} glyph#{i} -> '{d}'")

json.dump({f"{r},{c}": v for (r, c), v in transcript.items()},
          open(os.path.join(HERE, "grid_11x11_transcript.json", "w"), indent=1)
print("\nsaved -> /workspace/jspuzzle/grid_11x11_transcript.json")
