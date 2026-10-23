#!/usr/bin/env python3
"""Two figures:
   fig1  where-562308-comes-from.png   : the search tree + histogram + leaves-by-blocks
   fig2  the-377-root-branches.png    : the full contact sheet of all 377 root branches
"""
import json, math, os
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from engine import sym_info

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
N = 4
cells = [(r, c) for r in range(N) for c in range(N)]
IDX = {c: i for i, c in enumerate(cells)}
NB = [0] * 16
for i, (r, c) in enumerate(cells):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            NB[i] |= 1 << IDX[(rr, cc)]
PAL = [(204, 153, 254), (191, 224, 255), (179, 255, 180), (255, 164, 163),
       (255, 235, 150), (150, 235, 235), (235, 200, 255), (200, 235, 255)]
GREEN, GREY, INK, MUTE, RED = (86, 190, 120), (205, 205, 205), (25, 25, 25), (120, 120, 120), (190, 30, 30)


def F(sz, bold=False):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def connected_mask(mask):
    seen = mask & -mask
    frontier = seen
    while frontier:
        b = frontier & -frontier
        frontier -= b
        i = b.bit_length() - 1
        add = 0
        for j in range(16):
            if (NB[i] >> j) & 1 and (mask >> j) & 1 and not (seen >> j) & 1:
                add |= 1 << j
        seen |= add
        frontier |= add
    return seen == mask


legal = []
for mask in range(1, 1 << 16):
    if not connected_mask(mask):
        continue
    cl = [cells[i] for i in range(16) if (mask >> i) & 1]
    cap, names, fixes, fs = sym_info(cl)
    if names:
        legal.append((mask, cap is not None))
bycell = defaultdict(list)
for m, hc in legal:
    mm = m
    while mm:
        b = mm & -mm
        mm -= b
        bycell[b.bit_length() - 1].append((m, hc))
leaf_memo = {}


def leaves(rem):
    if rem == 0:
        return 1
    if rem in leaf_memo:
        return leaf_memo[rem]
    first = (rem & -rem).bit_length() - 1
    tot = 0
    for m, hc in bycell[first]:
        if m & ~rem:
            continue
        tot += leaves(rem ^ m)
    leaf_memo[rem] = tot
    return tot


full = (1 << 16) - 1
corner = IDX[(0, 0)]
roots = sorted([m for m, hc in legal if (m >> corner) & 1], key=lambda z: (-bin(z).count("1"), z))
root_leaves = []
for m in roots:
    rest = full ^ m
    if rest == 0:
        root_leaves.append(1)
    else:
        first = (rest & -rest).bit_length() - 1
        root_leaves.append(sum(leaves(rest ^ mm) for mm, hc in bycell[first] if not (mm & ~rest)))
assert sum(root_leaves) == 562308
J = json.load(open(os.path.join(ROOT, "tree_shape_4x4.json")))
per_k = {int(k): v for k, v in J["per_k_total"].items()}
alive_k = {int(k): v for k, v in J["per_k_alive"].items()}


def thumb(d, x0, y0, cell, m):
    col = PAL[bin(m).count("1") % len(PAL)]
    for rr in range(N):
        for cc in range(N):
            x, y = x0 + cc * cell, y0 + rr * cell
            if (m >> IDX[(rr, cc)]) & 1:
                d.rectangle([x, y, x + cell, y + cell], fill=col)
            else:
                d.rectangle([x, y, x + cell, y + cell], outline=(228, 228, 228))
    d.rectangle([x0, y0, x0 + N * cell, y0 + N * cell], outline=(110, 110, 110), width=1)
    d.rectangle([x0, y0, x0 + cell, y0 + cell], outline=(230, 0, 0), width=2)


# ================= FIGURE 1 =================
W, H = 1700, 1130
im = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(im)
d.text((40, 16), "Where 562,308 comes from: it is the LEAF COUNT of the tiling search tree",
       font=F(30, True), fill=INK)
d.text((40, 56), "every complete tiling of the 4x4 frame is reached exactly once  |  562,308 leaves  |  "
                 "1,300,765 nodes  |  root branching factor 377", font=F(19), fill=MUTE)

# Panel A
ax, ay, aw, ah = 40, 100, 470, 340
d.rectangle([ax, ay, ax + aw, ay + ah], outline=(215, 215, 215))
d.text((ax + 16, ay + 12), "STEP 1 - the anchor rule", font=F(20, True), fill=INK)
g = 44
gx, gy = ax + 22, ay + 56
for r in range(N):
    for c in range(N):
        x, y = gx + c * g, gy + r * g
        d.rectangle([x, y, x + g, y + g], outline=(170, 170, 170))
d.ellipse([gx + g * .3, gy + g * .3, gx + g * .7, gy + g * .7], fill=(0, 0, 0))
d.text((gx + g * 1.3, gy + 4), "always cover the", font=F(15), fill=INK)
d.text((gx + g * 1.3, gy + 24), "top-left uncovered cell", font=F(15), fill=INK)
d.text((gx + g * 1.3, gy + 50), "-> every tiling reached", font=F(14), fill=MUTE)
d.text((gx + g * 1.3, gy + 70), "   exactly once (no dupes)", font=F(14), fill=MUTE)
d.text((ax + 16, ay + 268), "STEP 2 - the branches", font=F(20, True), fill=INK)
d.text((ax + 16, ay + 298), "the anchor can be covered by 377 legal shapes", font=F(15), fill=INK)
d.text((ax + 16, ay + 318), "(1,130 legal shapes exist in a 4x4 frame)", font=F(14), fill=MUTE)

# Panel B
bx, by, bw, bh = 530, 100, 1130, 340
d.rectangle([bx, by, bx + bw, by + bh], outline=(215, 215, 215))
d.text((bx + 16, by + 12), "STEP 3 - the tree", font=F(20, True), fill=INK)


def box(x, y, w, h, fill, lines):
    d.rounded_rectangle([x, y, x + w, y + h], 10, fill=fill, outline=INK, width=2)
    yy = y + 12
    for ln, fnt, col in lines:
        d.text((x + 14, yy), ln, font=fnt, fill=col); yy += fnt.size + 5


box(bx + 20, by + 52, 165, 100, (255, 240, 200), [("4x4 frame", F(15, True), INK), ("16 cells", F(14), MUTE)])
d.line([bx + 185, by + 102, bx + 212, by + 102], fill=INK, width=2)
box(bx + 212, by + 52, 250, 100, (225, 240, 255),
    [("377 legal shapes can", F(15, True), INK), ("cover the corner (0,0)", F(15), INK),
     ("= 377 root branches", F(15, True), RED)])
d.line([bx + 462, by + 102, bx + 489, by + 102], fill=INK, width=2)
box(bx + 489, by + 52, 275, 100, (225, 255, 225),
    [("each branch keeps", F(15, True), INK), (f"1 .. {max(root_leaves):,} leaves", F(15), INK),
     (f"mean {sum(root_leaves)//len(root_leaves):,}, total 562,308", F(15, True), RED)])
d.line([bx + 764, by + 102, bx + 791, by + 102], fill=INK, width=2)
box(bx + 791, by + 52, 185, 100, (255, 225, 225), [("562,308", F(28, True), RED),
                                                   ("complete tilings", F(13), INK)])
hx, hy, hw, hh = bx + 20, by + 178, bw - 40, 145
d.rectangle([hx, hy, hx + hw, hy + hh], outline=(225, 225, 225))
d.text((hx + 10, hy + 8), "how many complete tilings each of the 377 root branches carries (log scale)",
       font=F(15, True), fill=INK)
vals = sorted(root_leaves)
BINS = 30
lo, hi = math.log10(vals[0]), math.log10(vals[-1])
hist = [0] * BINS
for v in vals:
    hist[min(BINS - 1, int((math.log10(v) - lo) / (hi - lo) * BINS))] += 1
for i, v in enumerate(hist):
    if not v:
        continue
    bwv = hw / BINS
    x0 = hx + 8 + i * bwv
    hgt = (v / max(hist)) * (hh - 56)
    d.rectangle([x0, hy + hh - 22 - hgt, x0 + bwv * .84, hy + hh - 22], fill=(120, 170, 220))
    if v > 3:
        d.text((x0 + 2, hy + hh - 20 - hgt), str(v), font=F(11), fill=INK)
d.text((hx + 10, hy + hh - 20), f"1 leaf  ({vals[0]})", font=F(12), fill=MUTE)
d.text((hx + hw - 200, hy + hh - 20), f"{vals[-1]:,} leaves", font=F(12), fill=MUTE)

# Panel C: bar chart
cx, cy = 40, 480
d.text((cx, cy - 28), "STEP 4 - and each root branch is itself a subtree: the 562,308 leaves, grouped by how many blocks the tiling has",
       font=F(19, True), fill=INK)
bx0, by0, bw0, bh0 = cx + 70, cy + 16, 1520, 290
d.rectangle([bx0, by0, bx0 + bw0, by0 + bh0], outline=(225, 225, 225))
ks = sorted(per_k)
mxv = max(per_k.values())
base = by0 + bh0 - 46
for i, k in enumerate(ks):
    x0 = bx0 + 26 + i * ((bw0 - 52) / len(ks))
    w = (bw0 - 52) / len(ks) * 0.60
    htot = (math.log10(per_k[k] + 1) / math.log10(mxv + 1)) * (bh0 - 96)
    d.rectangle([x0, base - htot, x0 + w, base], fill=GREY)
    av = alive_k.get(k, 0)
    if av > 0:
        hav = (math.log10(av + 1) / math.log10(mxv + 1)) * (bh0 - 96)
        d.rectangle([x0, base - hav, x0 + w, base], fill=GREEN)
    d.text((x0 - 2, base - htot - 17), f"{per_k[k]:,}", font=F(12), fill=INK)
    d.text((x0 - 2, base + 6), str(k), font=F(13, True), fill=INK)
d.text((bx0 + 26, by0 + 10), "green = tilings with at least one capitol (a cost field exists)   grey = no capitol at all (dead)",
       font=F(15, True), fill=INK)
d.text((bx0 + 26, base + 26), "number of blocks in the tiling", font=F(14), fill=MUTE)

# Panel D: sample of the 377
dx, dy = 40, 860
d.text((dx, dy - 26), "STEP 5 - a sample of 12 of the 377 root branches (full contact sheet in the second image)",
       font=F(19, True), fill=INK)
cell = 32
pitch = 4 * cell + 6
for i, m in enumerate(roots[:12]):
    thumb(d, dx + i * pitch, dy, cell, m)
d.text((dx, dy + 4 * cell + 12), "each mini-frame: the red cell is the anchor (0,0) that must be covered next; "
                                "the coloured cells are one legal state", font=F(14), fill=MUTE)
im.save(os.path.join(ROOT, "where-562308-comes-from.png"))
print("saved where-562308-comes-from.png", im.size)

# ================= FIGURE 2: the contact sheet =================
cols = 27
cell = 15
pitch = 4 * cell + 3
rows = (len(roots) + cols - 1) // cols
W2, H2 = 40 + cols * pitch + 20, 90 + rows * pitch + 30
im2 = Image.new("RGB", (W2, H2), (255, 255, 255))
d2 = ImageDraw.Draw(im2)
d2.text((40, 16), "All 377 root branches of the 4x4 tiling search tree", font=F(26, True), fill=INK)
d2.text((40, 52), "every legal shape that can cover the corner cell (red). Each one roots a subtree; the 377 subtrees "
                  "contain all 562,308 complete tilings.", font=F(16), fill=MUTE)
for i, m in enumerate(roots):
    r, c = divmod(i, cols)
    thumb(d2, 40 + c * pitch, 90 + r * pitch, cell, m)
im2.save(os.path.join(ROOT, "the-377-root-branches.png"))
print("saved the-377-root-branches.png", im2.size)
