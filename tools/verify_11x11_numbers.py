#!/usr/bin/env python3
"""Re-derive the official 11x11's 33 published numbers from the source image, and
compare them with the committed fixture.

Those 33 numbers are the ROOT of the whole chain: every solver run, every bound and
every conclusion about the official puzzle rests on them.  Until now they had no second
independent source in the repository -- `official-11x11/truth.json` was an empty shell
(status "unsolved"), so a wrong digit would have silently poisoned everything downstream.

This gate re-runs the pixel pipeline from assets/metric-too.png:
  grid-line detection -> per-cell ink -> self-supervised glyph templates learned from the
  5x5 example panel (leave-one-out validated) -> font-independent enclosed-hole-count
  feature -> transcript
and then compares the result with data/puzzles/official-11x11/puzzle.json.

It takes well under a second, so it can run on every commit.

Exit code 0 = the fixture agrees with the image.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PY = sys.executable

ok = True


def chk(cond, msg):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    ok = ok and bool(cond)


def main() -> int:
    print("=== re-deriving the 11x11 numbers from the source image ===")
    r = subprocess.run([PY, os.path.join(HERE, "ocr_disambiguate.py")], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        chk(False, "the OCR pipeline ran")
        return 1
    chk(True, "the OCR pipeline ran (grid lines -> glyph templates -> hole-count feature)")

    golden_path = os.path.join(ROOT, "data", "puzzles", "official-11x11", "ocr_numbers.json")
    with open(golden_path) as fh:
        golden = json.load(fh)
    with open(os.path.join(ROOT, "data", "puzzles", "official-11x11", "puzzle.json")) as fh:
        puz = json.load(fh)

    # the OCR transcript is 1-based, the fixture is 0-based
    ocr = {}
    for k, v in golden["numbers"].items():
        r0, c0 = (int(x) for x in k.split(","))
        ocr[(r0 - 1, c0 - 1)] = int(v)
    fix = {(h["row"], h["col"]): h["value"] for h in puz["hints"]}

    chk(len(ocr) == 33, f"the image yields 33 cells with ink (got {len(ocr)})")
    chk(len(fix) == 33, f"the fixture holds 33 numbers (got {len(fix)})")
    same = sum(1 for k in fix if ocr.get(k) == fix[k])
    chk(same == len(fix) == len(ocr),
        f"every published number is reproduced from the image ({same}/{len(fix)})")
    diff = [(k, fix[k], ocr.get(k)) for k in sorted(fix) if ocr.get(k) != fix[k]]
    chk(not diff, f"no disagreements (found {diff})")

    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
