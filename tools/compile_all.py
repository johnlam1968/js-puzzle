#!/usr/bin/env python3
"""Every python file in the repository must compile.

Four tools in this repository had never run: each had a syntax error of its own (a missing
parenthesis, a missing import, an undefined name, an output path that wrote "w" inside
os.path.join).  Nobody noticed, because nothing ever imported or executed them -- and
because a file that cannot be parsed also cannot be reviewed.

This gate is three lines of work and it catches that whole class of rot.

Exit code 0 = every file compiles.
"""

from __future__ import annotations

import pathlib
import py_compile
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

files = [p for p in ROOT.rglob("*.py")
         if ".git" not in p.parts and "__pycache__" not in p.parts]

errors = []
for p in files:
    try:
        py_compile.compile(str(p), doraise=True)
    except Exception as exc:                      # noqa: BLE001 - report anything
        errors.append((p.relative_to(ROOT), exc))

print(f"{len(files)} python files, {len(errors)} broken")
for path, exc in errors:
    print(f"  BROKEN  {path}: {exc}")

sys.exit(1 if errors else 0)
