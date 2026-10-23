# AODFS, explained without the maths

> **This is a companion, not a source of truth.** The authoritative description of AODFS is
> [`DESIGN.md` §3](DESIGN.md#3-aodfs锚点--对称轨道生长) (growth rules, pruning table, completeness
> argument, complexity). This file is the *layman's version*: what the algorithm does, why it exists,
> and what it is allowed to claim. Where the two disagree, DESIGN.md wins.

**Status of this document:** 2026-10-23 (18:05 UTC), against `main` = `cf21c25792`
("Implements M4: the readings-driven AODFS solver"). Numbers marked ✅ are measured and reproducible
with the snippets in §7. Numbers marked ⚠️ were measured during work that was still in flight and may
have moved on — see §6.

---

## 1. The one-sentence version

> **AODFS does not build a library of every possible state up front. It builds the tiling while it
> searches, and lets the numbers printed on the puzzle reject wrong branches as it goes.**

The name comes from **Anchor-Orbit DFS** (anchor + symmetric orbit + depth-first search), first
written down in `ds-A2.md`.

> ⚠️ **AODFS is this project's own name for the approach.** It is not a standard term in mathematics
> or computer science; you will not find it in a textbook. The underlying ideas are ordinary
> ("grow a shape along one symmetry, prune with the constraints"), the *name* is local.

---

## 2. The problem it solves

The puzzle hands you an 11×11 frame with 33 numbers. Each number is the cheapest cost of walking
from that cell to any **capitol**. You must work backwards: how does the frame split into **states**,
how big is each state, where is each state's capitol, and finally the number to submit.

The obvious approach is *enumerate, then filter*:

1. list every legal state shape,
2. enumerate every way of tiling the frame with them,
3. keep the tilings that reproduce all 33 numbers.

**That approach dies on size** (all figures measured, ✅):

| frame | legal states | tilings that fill it | verdict |
|---|---|---|---|
| 4×4 | 1,130 | 562,308 | fine, seconds |
| 5×5 | 22,317 | 2,638,025,192 | explodes |
| 11×11 | ≈ 1.3×10¹² | astronomical | ~1.3×10⁻¹³ of the universe's atoms |

The state library grows about **×19.7 per level**; multiplied from 4×4 to 11×11 that is ~1.3×10¹²
states. The 5×5 enumeration was still running after 8 minutes. **From 6×6 upward, a different
architecture is mandatory** — that is what AODFS is.

---

## 3. The one insight everything rests on

A state must be **symmetric** (it maps onto itself under some rotation or reflection). Once you have
picked *one* symmetry `σ`, the cells of the state **cannot appear one at a time** — they come in
groups:

- a **lonely cell** that sits exactly on the axis / at the centre of the symmetry,
- a **mirror pair** of cells,
- a **quadruple** of cells (quarter turns).

One such group is called an **orbit**: the set of cells you land on when you keep applying `σ` to
one cell until you come back.

### The example that makes it click

Take the green state of the **official 5×5 example** (7 cells). Its symmetry is the anti-diagonal
reflection `r + c = 3`, so the orbits are ✅ (measured):

```
(0,0) <-> (3,3)      a mirror pair
(1,0) <-> (3,2)      a mirror pair
(2,0) <-> (3,1)      a mirror pair
(2,1)                 * the lonely cell
```

**That lonely cell is the capitol.** The puzzle rule says a state has a capitol only if *every*
non-trivial self-symmetry fixes **exactly one** cell. So in AODFS the capitol is not something you
hunt for separately — it is the lonely cell that the symmetry hands you.

(That also explains the parity theorem: a state with a capitol must have **odd** area, because all
its other cells come in pairs.)

---

## 4. The six steps, in plain words

Vocabulary: **σ** = the symmetry you chose; **S** = the state you are growing; **rem** = the cells
not yet assigned to any state.

1. **Pick an anchor.** The top-leftmost unassigned cell `a`. (The implementation prefers a cell that
   carries a printed number, because that constrains more.)
2. **Choose a symmetry and open the state.** Pick one `σ` (4×4 offers **379** symmetries ✅,
   11×11 offers **2,422** ✅) and set the first cells of the state to the orbit of `a`.
3. **Compute the frontier.** `F` = the unassigned cells that touch the state already.
4. **Add one whole orbit.** Take an `x` in `F` and add **the entire orbit of `x`** at once. A
   non-fixed cell brings its mirror along (2 or 4 cells); a fixed cell contributes only itself.
5. **Try to close the state.** A set `S` becomes a state when it is **connected**, has a non-trivial
   symmetry, and — this is the subtle part — when **every** non-trivial symmetry of `S` fixes exactly
   one cell. That cell is the capitol. Otherwise `S` is a legal state with *no* capitol.
6. **Close it and move on**, or go back to step 4 and grow it bigger. When the frame is full, you
   have a tiling.

**Why this cannot miss a solution** (DESIGN.md §3.4): take any legal tiling, and for each of its
states pick one of its non-trivial symmetries. The state is σ-invariant and connected, so it admits a
BFS order in which every step adds an orbit that lies inside the state — so the growth *can* reach
it. Since all pruning rules are **necessary** conditions, nothing legitimate is cut.

---

## 5. The brakes: the 33 printed numbers

Search explodes without pruning, and the printed numbers are free, exact constraints:

| the numbers say | then |
|---|---|
| a cell reads **0** | it **is** a capitol, so the symmetry you grow with **must fix it** |
| a cell reads **1** | one of its neighbours is a 1×1 single-cell state |
| two adjacent cells read `x` and `y` | the state containing `x` has area ≥ \|Dx − Dy\| |
| a cell reads **> 0** | it must have a strictly cheaper neighbour to step to |

The `d = 0` rule is by far the strongest, because a capitol pins the symmetry. Measured ✅:

| frame | candidate symmetries | symmetries that fix the anchor | share |
|---|---|---|---|
| 4×4, anchor (2,1) | 379 | **7** | 1.8% |
| 11×11, anchor (6,8) | 2,422 | **7** | 0.3% |

On the 4×4 the same rule cut the *generated candidate states* for one anchor from 1,123 to 297
(3.8×) ✅ (the snippet is in §7).

### One trap worth writing down

**Do not use "Manhattan distance to the nearest *revealed* capitol" as a lower bound.** The nearest
capitol may be unrevealed. That rule prunes the true hint `(2,4) = 3` of the official example. Only
the *existence* side is valid: a cell reading `v` has a capitol within Manhattan distance
`⌊(v+1)/2⌋`. (PLAN D53.)

---

## 6. What is actually working, and what is not

### ✅ Verified

* **The rule kernel** (symmetry group, capitol rule, cost field) is integer-only — no floating
  point, because floating point silently lost a capitol on the official example once already.
* **The official 5×5 example** reproduces: states of size 7/4/3/11, capitols at (3,2)/(3,4)/(5,5)
  (1-based), the 2×2 state has **no** capitol, row sums `[37, 29, 31, 43, 55]`, answer **8,045** —
  confirmed independently by three parties (author, Verifier pixel OCR, DeepSeek-V4.1-Flash vision).
* **The generator (M3)** builds 4×4 puzzles in ~1 s with 5–10 hints, each with a *proof* that the
  answer is unique and the search was exhaustive.
* **The 4×4 enumeration constants** all reproduce: 11,506 connected subsets / 1,130 legal states /
  640 shape types / 562,308 tilings / 559,585 with at least one capitol.
* **The growth machinery** (`src/grow.py`) is implemented and tested (`tests/test_grow.py`).

### ⚠️ Measured while the work was still in flight (read the date before quoting)

* **The solver is on `main`** as of `cf21c25792` ("Implements M4: the readings-driven AODFS
  solver", adding `src/solver.py` and `tests/test_solver.py`). It merges "grow a state" and
  "place a state" into one DFS, and its verdict is three-valued (`unique` is true only when the
  search was **exhaustive** *and* the answer set has one element).
* **4×4 with every cell hinted: the search finds the right answers but does not finish.** It
  returns `{112, 304}` — correct — but needs more than 400,000 nodes to do it, and it had not
  exhausted the space. This is a *throughput* problem, not a correctness problem; see §6.1 and
  §6.2.
* **11×11 was running with a 3,000,000-node budget** and had produced no answers after the first
  200,000 nodes (237 nodes/s).
* Honest complexity budget (DESIGN.md §3.5): ~10⁴–10⁸ candidates per anchor, 10⁹–10¹¹ nodes
  overall ⇒ a **node budget is mandatory**, and exhausting it must be reported as `unknown` —
  never as "unique".

> **The honest one-liner:** AODFS is currently *the only route that has been seriously argued* and
> *the direction the implementation is actually taking* — it is **not** a finished solver.

### 6.1 What the solver actually does today (measured)

Five runs of `src/solver.py` as it stands on `main` = `cf21c25792` ✅:

| instance | hints | budget | answers found | nodes | wall clock | rate |
|---|---|---|---|---|---|---|
| 4×4 `counterexample` (fully revealed) | 16/16 | 400,000 | **[112, 304]** ✅ = the fixture's expected set | 400,001 | 271 s | 1,476 /s |
| 4×4 hand-built | 15/16 | 50,000 | none | 50,001 | 25 s | 1,973 /s |
| 4×4 hand-built | 15/16 | 200,000 | none | 200,001 | 122 s | 1,638 /s |
| 4×4 hand-built | 15/16 | 2,000,000 | **none** | 2,000,001 | 839 s | 2,383 /s |
| 11×11 official | 33/121 | 200,000 (of 3,000,000) | none so far | 200,000 | 846 s | **237 /s** |

Two things to read off this table:

1. **The solver is not wrong — it is slow.** On the fully revealed 4×4 it returns exactly the
   answer set the fixture predicts, `{112, 304}`, with `cardinality=2` — the hardest semantic case
   in the family, and it gets it right. The completeness of the readings-driven path is therefore
   *supported*, not merely hoped for.
2. **But sparsity kills it.** 33 hints on 121 cells is a much weaker constraint than 16 hints on 16
   cells, and at that sparsity the 4×4 finds *nothing* in 2,000,000 nodes. The 11×11 is the same
   story with 237 nodes/s: 3,000,000 nodes would take **3.5 hours** and, on the 4×4 evidence, would
   probably still return `answers=[]`.

### 6.2 Where the time actually goes

A `cProfile` run over 60,001 nodes of the fully revealed 4×4 (94.7 s under the profiler) ✅:

| hot spot | cost | why |
|---|---|---|
| `rules.py:75 symmetry_group` | **25.3 s (27%)** | the *full point group* of a state, recomputed at every growth step |
| `rules.py:137 capitol_of` | **27.7 s (29%)** | calls `symmetry_group` **again** ⇒ the group is computed twice per check |
| `solver.py:83` (the LB inner scan) | 11.2 s (12%) | 13.9 M generator calls: for every hint, scan all n² cells |
| `min` over that scan | 18.0 s (19%, overlapping) | the same scan's inner `min` |
| `solver.py:63/69 _orbits` / `_fixed` | 8.0 s (8%) | 1.7 M cache *lookups* — hoisted out of the loop would vanish |
| `solver.py:170` (orbit leaves the board) | 3.5 s | 4.3 M generator calls, re-checked for every symmetry at every state |

Four concrete fixes, in the order I would make them:

1. **Skip the point group for even-sized states.** A state can only have a capitol if its area is
   **odd** (PLAN D43: a symmetry that fixes exactly one cell leaves the rest in pairs). The parity
   of the area is known for free while growing — a pair-orbit adds 2, a quarter-turn orbit adds 4,
   a fixed cell adds 1 — so half of all the `symmetry_group` calls can be skipped outright, and the
   remaining ones halve again by not calling `capitol_of` on top of `symmetry_group`.
2. **Make the lower-bound check proportional to the candidates, not to the board.** `solver.py:83`
   scans all n² cells *per hint* and rebuilds a fresh big integer for each one. Iterating over the
   **set bits** of `possible` instead (and building that list once per call, not once per hint)
   turns O(hints × n²) into O(n² + hints × k), where k is the number of cells that can still be a
   capitol — and k shrinks as the search deepens.
3. **Precompute the board-feasible symmetries, per anchor.** The symmetry loop sweeps **all** 2,422
   symmetries for every new state on the 11×11, and 89% of them die one line later because their
   orbit leaves the frame. Measured ✅: for a given anchor only **261–287 of 2,422** symmetries
   (≈11%) have an on-board orbit. The board never changes, so this is a static table
   (2,422 × 121 entries) built once — a **~9× cut** on the symmetry fan-out.
4. **Hoist `_orbits(sym)` / `_fixed(sym)` out of the inner loops** and compute the state→capitol
   distances with **one BFS from the capitol** instead of one BFS per hinted cell inside the state
   (`_ub_violates` / `_path_cost`).

None of these change what the solver *decides*; they change how long it takes to decide it. That
is why they come before any new pruning rule.

### 6.3 The gap that matters most: no 4×4 regression gate

`tests/test_solver.py` covers the 2×2 case and the semantics of budget exhaustion, but there is
**no test that says "4×4, all 16 cells hinted ⇒ the right answer, in a bounded number of nodes"**.

That single missing gate is why the current state is hard to read:

* Without it, "slow" is unquantified — nobody can tell a 2× slowdown from a 100× one.
* With it, every pruning change has a number to move, and the 11×11 work stops being a leap of
  faith.

The 4×4 with all 16 cells hinted is the cheapest possible benchmark: the answer is known, the
tilings are enumerable (562,308 of them, 559,585 with a capitol), and the correct answer can be
computed offline. A solver that cannot do that quickly has a defect that will only be 1000× more
expensive on the 11×11.

**Use the fixture that already exists.** `data/puzzles/counterexample-4x4-two-answers/` is a *fully
revealed* 4×4 (all 16 cells hinted) whose cost field is compatible with **two** answers, 304 and
112. It is the ideal gate because it exercises three things at once: the maximum number of hints,
the "two answers" path, and the three-valued verdict (it must report `cardinality=2`,
`unique=false`, and `exhaustive=true` once the search completes — PLAN V21).

The solver already gets the **answers** right on it (§6.1); what is missing is the *node count* and
the `exhaustive=true` part, which needs the search to finish rather than to hit a budget. A gate
like `answers == {112, 304} and exhaustive is True and nodes < N` turns "the solver is slow" into
a number that every optimisation has to move.

⚠️ Note: that fixture is one of the two files with **1-based** hints — see §6.4 — so the gate must
convert, or the fixtures must be normalised first.

### 6.4 A contract bug found while writing this document

The three puzzle fixtures in `data/puzzles/` **do not agree on the indexing of `hints[]`**:

| fixture | `hints[0].row` | indexing |
|---|---|---|
| `official-11x11` | 0 | **0-based** ✅ (matches the schema) |
| `official-example-5x5` | 1 | **1-based** ❌ |
| `counterexample-4x4-two-answers` | 1 | **1-based** ❌ |

`data/schema/puzzle.schema.json` says `grid` is "row-major, 0-based" and `hints` is "hint cells,
0-based (row, col), consistent with grid[r][c]". `README.md` contradicts it ("1-based hints in
`hints[]`"). And `src/solver.py`'s command line reads hints as 0-based — so the CLI agrees with the
schema and with the 11×11, and **misreads the other two fixtures**.

Three consequences, in increasing order of severity:

1. The solver has **no validation** that a hint coordinate lies inside the frame, so a 1-based
   file does not produce a clean error — it produces
   `IndexError: list index out of range` from the Manhattan table.
2. Any test or benchmark built on the 5×5 example or the 4×4 counterexample must convert
   1-based → 0-based **by hand** until the fixtures are normalised.
3. The target puzzle itself is the odd one out: it is the only file that already follows the
   schema, so a future "normalisation" of the other two files must not touch it.

This is worth fixing before the 4×4 gate is written, otherwise the gate will be measuring a
coordinate offset rather than a pruning defect.

---

## 7. Reproducing the numbers in this document

Run from the repository root, with `src/` on the path.

**Candidate symmetry counts, and how many of them fix a given cell** (§1, §5):

```python
import sys; sys.path.insert(0, 'src')
from grow import symmetry_choices

def fixes(s, cell):
    r, c = cell
    return s.apply((r, c)) == (r, c)

for n, anchor in ((4, (2, 1)), (11, (6, 8))):
    syms = symmetry_choices(n)
    fx = [s for s in syms if fixes(s, anchor)]
    print(n, len(syms), len(fx))
# 4 379 7
# 11 2422 7
```

**The orbit decomposition of the official green state** (§3):

```python
import json, sys; sys.path.insert(0, 'src')
from grow import symmetry_choices, orbits_of

states = json.load(open('data/puzzles/official-example-5x5/truth.json'))['states']
S0 = {(r, c) for r in range(5) for c in range(5) if states[r][c] == 0}
sym = [s for s in symmetry_choices(5) if s.name == 'refD2' and s.params == (3,)][0]
orb = orbits_of(sym, 5)
groups = {}
for c in sorted(S0):
    groups.setdefault(frozenset(orb[c] & S0), []).append(c)
for g in sorted(groups, key=sorted):
    print(sorted(g))
# [(0, 0), (3, 3)] / [(1, 0), (3, 2)] / [(2, 0), (3, 1)] / [(2, 1)]
```

The last group has one element — the lonely cell `(2, 1)`, which is the capitol recorded in
`truth.json` as `state_capitol[0] = [2, 1]`.

**How much the `d = 0` rule buys on the candidate states** (§5):

```python
import sys; sys.path.insert(0, 'src')
from solver import Solver
from grow import grow_states

hints = {(0,1):3,(0,2):6,(0,3):10,(1,0):3,(1,1):3,(1,2):6,(1,3):6,
         (2,0):3,(2,1):0,(2,2):3,(2,3):3,(3,0):0,(3,1):3,(3,2):3,(3,3):0}
s = Solver(4, hints)
anchor = (2, 1)                      # a cell that reads 0 => it is a capitol

def count(restrict):
    n = 0
    for sym in s._syms:
        if restrict and anchor not in s._fixed(sym):
            continue                 # the symmetry must fix the capitol
        orb = s._orbits(sym)
        if any(c not in s.idx for c in orb[anchor]):
            continue                 # the orbit leaves the board
        n += len(grow_states(anchor, sym, 4))
    return n

print(count(False), count(True))
# 1123 297
```

**The fully revealed 4×4 benchmark of §6.1** (mind the 1-based hints of that fixture — see §6.4):

```python
import json, sys, time; sys.path.insert(0, 'src')
from solver import solve_grid

p = json.load(open('data/puzzles/counterexample-4x4-two-answers/puzzle.json'))
hints = {(h['row'] - 1, h['col'] - 1): h['value'] for h in p['hints']}   # 1-based -> 0-based

t0 = time.time()
res = solve_grid(4, hints, budget=400_000)
print(res['answers'], res['cardinality'], res['exhaustive'], res['nodes'], time.time() - t0)
# [112, 304] 2 False 400001 271.0...
```

The expected answer set is the fixture's own `answers: [304, 112]`.

---

## 8. Four traps that are easy to re-introduce

1. **The v1 growth rule was self-contradictory.** It said "you may add `x` only if `σ(x)` is already
   in `S ∪ {x}`" *and* "you must add `x`'s mirror at the same time" — if the mirror is already there
   there is nothing to add, and if it is not there the premise is violated. Fixed by rewriting the
   rule in **orbit semantics**: add a whole orbit at a time (PLAN D48).
2. **Check connectivity when you CLOSE the state, not at every step.** The first orbit of a legal
   state can be disconnected — the anti-diagonal L-tromino starts from `{(0,0), (1,1)}`, which is
   diagonally separated. Requiring connectivity mid-growth makes legal states unreachable
   (PLAN D65/D68).
3. **The capitol rule quantifies over the FULL point group, not over `σ` alone.** A state whose
   chosen `σ` fixes exactly one cell can still have a second symmetry fixing 0 or ≥2 cells — then
   it has **no** capitol (PLAN D55).
4. **Never cap the state size.** A size cap silently deletes legal shapes from the vocabulary (on
   the 4×4 it cut the legal shapes around one corner from 377 down to 113, i.e. it changed the
   problem). Bound the *node count* and fail honestly when the budget is hit (PLAN D85).

---

## 9. Where the pieces live

| file | what it holds |
|---|---|
| `src/grow.py` | the growth itself: `grow_states`, `symmetry_choices`, `orbits_of` |
| `src/rules.py` | the rule kernel: symmetry group and capitol rule (integer only) |
| `src/hitting.py` | capitol positions as a hitting set (a lower bound, and candidate seeds) |
| `docs/DESIGN.md` §3 | the authoritative AODFS design |
| `PLAN.md` | the defect register — AODFS entries are D38, D48, D65, D85 |
