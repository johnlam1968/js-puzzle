#!/usr/bin/env python3
"""Pixel-level extraction of the 11x11 official grid: grid geometry -> per-cell ink -> digit ID.

No third-party deps beyond PIL. Prints:
  - detected grid line positions
  - per-cell ASCII ink art for every cell that contains ink (so positions can be eyeballed)
  - template-matched digit values with a confidence margin
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = os.path.join(HERE, "metric-too.png"
im = Image.open(SRC).convert("L")
a = np.array(im).astype(int)
H, W = a.shape
ink = a < 128

# ---------- 1. grid geometry: the 11x11 block occupies the top region ----------
# vertical lines: columns with many dark pixels in y in [15, 810]
region = ink[15:810, :]
colprof = region.sum(axis=0)
rowprof = ink[:, 220:1010].sum(axis=1)          # restrict x to the grid band for rows
rowband = rowprof[0:815]


def runs(idx, thr, minlen=1):
    out, s = [], None
    for i, v in enumerate(idx):
        if v > thr and s is None:
            s = i
        elif v <= thr and s is not None:
            if i - s >= minlen:
                out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, len(idx) - 1))
    return out


vlines = [r for r in runs(colprof, 300) ]
hlines = [r for r in runs(rowband, 500) ]
# keep only lines inside the puzzle block, pick the 12 strongest on a regular lattice
print("vertical candidates:", vlines)
print("horizontal candidates:", hlines)

# refine: the grid is a regular lattice. pick the best lattice fit.
def fit_lattice(cands, lo, hi, n):
    """choose n lines evenly spaced in [lo,hi] maximizing total candidate mass."""
    best = None
    step = (hi - lo) / n
    # search phase offset
    for phase in range(0, 1000):
        off = lo + step * phase / 1000.0
        lines = [off + step * k for k in range(n + 1)]
        score = 0.0
        ok = True
        for L in lines:
            # mass within +-3 px
            xi = int(round(L))
            w = 0.0
            for dx in range(-3, 4):
                x = xi + dx
                if 0 <= x < len(colprof):
                    w = max(w, colprof[x])
            score += w
            if w < 200:
                ok = False
                break
        if ok and (best is None or score > best[0]):
            best = (score, lines)
    return best

vbest = fit_lattice(vlines, 220, 1010, 11)
hbest = fit_lattice(hlines, 15, 810, 11)

def midpoints(runs_):
    return [(a + b) / 2.0 for a, b in runs_]

# The projection already yields exactly 12 vertical and 12 horizontal lines: use them directly.
assert len(vlines) == 12 and len(hlines) == 12, (len(vlines), len(hlines))
xs, ys = midpoints(vlines), midpoints(hlines)
print("\nvertical line midpoints (12):", [round(x, 1) for x in xs])
print("horizontal line midpoints (12):", [round(y, 1) for y in ys])
print("col pitch:", [round(xs[i + 1] - xs[i], 1) for i in range(11)])
print("row pitch:", [round(ys[i + 1] - ys[i], 1) for i in range(11)])

# ---------- 2. per-cell ink ----------
def cell_art(r, c):
    x0, x1 = xs[c] + 6, xs[c + 1] - 6
    y0, y1 = ys[r] + 6, ys[r + 1] - 6
    sub = ink[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))]
    if not sub.any():
        return None, None, (0, 0)
    rows = np.where(sub.any(axis=1))[0]
    cols = np.where(sub.any(axis=0))[0]
    crop = sub[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    return crop, (int(rows[0]), int(cols[0])), (crop.shape[0], crop.shape[1])


def components(crop):
    """split digit glyphs by column gaps."""
    colink = crop.any(axis=0)
    comps, s = [], None
    for i, v in enumerate(colink):
        if v and s is None:
            s = i
        elif not v and s is not None:
            comps.append((s, i - 1)); s = None
    if s is not None:
        comps.append((s, len(colink) - 1))
    # merge components that overlap heavily (rare for digits)
    return comps


def render_ascii(crop, w=18):
    h, wd = crop.shape
    step = max(1, wd // w)
    out = []
    for r in range(0, h, max(1, step * 2)):
        line = ""
        for c in range(0, wd, step):
            blk = crop[r:r + step * 2, c:c + step]
            line += "#" if blk.any() else "."
        out.append(line)
    return out


# ---------- 3. digit templates ----------
FONTS = []
for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
          "/usr/share/fonts/TTF/DejaVuSans.ttf"]:
    try:
        FONTS.append(ImageFont.truetype(p, 60))
    except Exception:
        pass
print("\nfonts loaded:", len(FONTS))

def template_bank():
    bank = {}
    for fi, f in enumerate(FONTS):
        for d in "0123456789":
            img = Image.new("L", (90, 110), 255)
            dr = ImageDraw.Draw(img)
            dr.text((20, 10), d, font=f, fill=0)
            arr = (np.array(img) < 128)
            rs = np.where(arr.any(axis=1))[0]; cs = np.where(arr.any(axis=0))[0]
            arr = arr[rs[0]:rs[-1] + 1, cs[0]:cs[-1] + 1]
            bank[(fi, d)] = arr
    return bank

BANK = template_bank()

def match(crop):
    best = []
    for (fi, d), t in BANK.items():
        if abs(t.shape[0] - crop.shape[0]) > 0.45 * crop.shape[0] or \
           abs(t.shape[1] - crop.shape[1]) > 0.45 * crop.shape[1]:
            continue
        H1, W1 = crop.shape; H2, W2 = t.shape
        S = max(H1, H2); T = max(W1, W2)
        ca = np.zeros((S, T), bool); ta = np.zeros((S, T), bool)
        ca[:H1, :W1] = crop; ta[:H2, :W2] = t
        inter = (ca & ta).sum(); union = (ca | ta).sum()
        best.append((inter / union, d))
    if not best:
        return None, 0.0
    best.sort(reverse=True)
    return best[0][1], best[0][0]

print("\n===== 11x11 per-cell extraction =====")
transcript = {}
for r in range(11):
    for c in range(11):
        crop, off, (hh, ww) = cell_art(r, c)
        if crop is None:
            continue
        comps = components(crop)
        digits = []
        for (cs_, ce_) in comps:
            g = crop[:, cs_:ce_ + 1]
            v, conf = match(g)
            digits.append((v, round(conf, 3)))
        val = "".join(d[0] if d[0] else "?" for d in digits)
        transcript[(r + 1, c + 1)] = (val, digits)
        print(f"  ({r+1:2d},{c+1:2d})  value={val:<4s} conf={[d[1] for d in digits]}")

print("\n----- machine transcript (row,col=value) -----")
for r in range(1, 12):
    row = [f"({r},{c})={transcript[(r,c)][0]}" for c in range(1, 12) if (r, c) in transcript]
    if row:
        print("  " + "  ".join(row))
print("total cells with ink:", len(transcript))

print("\n----- ASCII art of every numbered cell (for eyeball verification) -----")
for (r, c), (val, _) in sorted(transcript.items()):
    crop, off, _ = cell_art(r - 1, c - 1)
    print(f"\n({r},{c})  machine={val}")
    for line in render_ascii(crop, 16):
        print("   " + line)
