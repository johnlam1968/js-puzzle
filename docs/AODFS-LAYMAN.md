# AODFS, explained without the maths

> **This is a companion, not a source of truth.** The authoritative description of AODFS is
> [`DESIGN.md` §3](DESIGN.md#3-aodfs锚点--对称轨道生长) (growth rules, pruning table, completeness
> argument, complexity). This file is the *layman's version*: what the algorithm does, why it exists,
> and what it is allowed to claim. Where the two disagree, DESIGN.md wins.

**Status of this document:** 2026-10-23 (18:20 UTC), against `main` = `71092be59e`
("Cuts the solver's work by 2.6x, and fixes the broken judge search path"). Numbers marked ✅ are
measured and reproducible with the snippets in §7. Numbers marked ⚠️ were measured during work that
was still in flight and may have moved on — see §6.

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
* **The readings-driven solver now solves the fully revealed 4×4** — `main` = `71092be59e`:
  `answers=[112, 304]`, `cardinality=2`, `partitions=2`, `exhaustive=True`, **206 nodes, 0.03 s**
  ✅ (measured).

> That last line is worth its own check, because it is easy to believe a solver that reports two
> answers. Here is an independent argument that **two is the most there can be**: the published
> 4×4 cost field has twelve cells reading 0, and a cell reading 0 *is* a capitol; a state has at
> most one capitol, and a state with a capitol but more than one cell has an odd area, so the
> other cells would read ≥ 1 — contradiction. Hence those twelve cells are twelve 1×1 states, and
> the four remaining cells (the top row) can only be one 1×4 bar (answer 304) or two 1×2 dominoes
> (answer 112). **Two is the truth, and the solver now reports it.**

### ⚠️ The one thing that is still not working: sparse hints

| instance | hints | budget | answers | nodes | wall clock | rate |
|---|---|---|---|---|---|---|
| 4×4 `counterexample` (fully revealed) | 16/16 | 400,000 | **[112, 304]**, `exhaustive=True` | **206** | 0.03 s | 6,700 /s |
| 5×5 **official example** | 10/25 | 400,000 | **none** | 400,001 | 46 s | 8,632 /s |
| 11×11 official | 33/121 | 200,000 (of 3,000,000) | none so far | 200,000 | 846 s | 237 /s |

**The bottleneck is density, not speed.** A fully revealed 4×4 is solved in 206 nodes; the official
5×5 — which has a *known* answer of 8,045 and a published `truth.json` with the whole partition —
finds nothing in 400,000 nodes. The 11×11 is sparser than either.

⇒ **The 5×5 example is the next gate to build**, not the 4×4: it is the cheapest instance that is
simultaneously *sparse* and *has ground truth*, so it actually discriminates. The fully revealed
4×4 no longer does (206 nodes).

### 6.1 The prune that is designed but not implemented: the area lower bound

`docs/DESIGN.md` §3.3 lists it as **L3/L2**, and `PLAN.md` has it too:

> two adjacent cells that are *both* hinted, x and y ⇒ the state containing x has area ≥ |D(x) − D(y)|

**The one-line derivation**: the step between two adjacent cells costs `min(size_x, size_y)`, which
is at most `size_x`; the difference in their d-values cannot exceed one step; therefore
`|Dx − Dy| ≤ size_x`.

`src/solver.py` implements only two prunes — `_lb_violates` (Manhattan distance to a cell that
could still be a capitol) and `_ub_violates` (the in-state path cost). **The area bound is not
among them.**

What it would buy, computed from the **published 5×5 numbers alone** (no ground truth needed) ✅:

| hinted cell (0-based) | d | area lower bound | true area in the solution |
|---|---|---|---|
| (3,4) | 10 | **≥ 10** | 11 |
| (4,4) | 0 | **≥ 10** | 11 |
| (0,0) | 12 | ≥ 4 | 7 |
| (1,0) | 8 | ≥ 4 | 7 |
| (1,2) | 6 | ≥ 3 | 4 |
| (1,3) | 3 | ≥ 3 (tight) | 3 |
| (3,1) | 7 | ≥ 1 | 7 |
| (3,2) | 6 | ≥ 1 | 7 |

Every bound is consistent with the known solution, so **the prune does not kill the truth** — and
two of them pin the big 11-cell state at ≥ 10, which is exactly the kind of constraint that
strangles the "filler" states.

It is cheap to implement: precompute `need[x] = max{|Dx − Dy| : y is a hinted neighbour of x}`
once (O(hints × 4)), carry `need(S) = max{need[x] : x ∈ S}` while growing, and refuse to close a
state with `|S| < need(S)`.

### 6.2 A counting bug worth knowing about (it inflated a number you may have seen)

An earlier version of the solver reported **58,721 partitions** for the fully revealed 4×4. That
number is **not real**: the solver counted the *same* tiling over and over, because different
search paths reached it and nothing deduplicated them. (Its first three recorded "solutions" were
byte-identical.) The *answer set* was never affected — it was a set — but the partition count was
inflated by four orders of magnitude, and the search was correspondingly slow. With
deduplication the same instance reports **2** partitions, which is the correct answer.

⇒ A general lesson for this codebase: **when a search reports a count, check that the count is
plausible against a small argument before trusting it.** 58,721 tilings of a 4×4 that has only two
possible answers should have been obvious as absurd.

### 6.3 Where the time goes (profile, as of `cf21c25792`)

The solver was profiled before the optimisation round. A `cProfile` run over 60,001 nodes of the
fully revealed 4×4 (94.7 s under the profiler) ✅:

| hot spot | cost | why |
|---|---|---|
| `rules.py:75 symmetry_group` | 25.3 s (27%) | the *full point group* of a state, recomputed at every growth step |
| `rules.py:137 capitol_of` | 27.7 s (29%) | calls `symmetry_group` **again** ⇒ the group is computed twice per check |
| `solver.py:83` (the LB inner scan) | 11.2 s (12%) | 13.9 M generator calls: for every hint, scan all n² cells |
| `min` over that scan | 18.0 s (19%, overlapping) | the same scan's inner `min` |
| `solver.py:63/69 _orbits` / `_fixed` | 8.0 s (8%) | 1.7 M cache *lookups* — hoisted out of the loop would vanish |
| `solver.py:170` (orbit leaves the board) | 3.5 s | 4.3 M generator calls, re-checked for every symmetry at every state |

The four fixes that came out of it — all of which preserve the solver's *decisions* and only change
how long it takes to reach them:

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

### 6.4 A contract bug, and the reason nobody noticed

The three puzzle fixtures in `data/puzzles/` **did not agree on the indexing of `hints[]`**:

| fixture | `hints[0].row` | indexing |
|---|---|---|
| `official-11x11` | 0 | **0-based** ✅ (matches the schema) |
| `official-example-5x5` | 1 | **1-based** ❌ |
| `counterexample-4x4-two-answers` | 1 | **1-based** ❌ |

`data/schema/puzzle.schema.json` says `grid` is "row-major, 0-based" and `hints` is "hint cells,
0-based (row, col), consistent with grid[r][c]". `README.md` contradicted it ("1-based hints in
`hints[]`"). And `src/solver.py`'s command line read hints as 0-based — so the CLI agreed with the
schema and with the 11×11, and **misread the other two fixtures**, with no bounds check, so a
1-based file produced `IndexError: list index out of range` instead of a clean error.

**The data itself was fine**: with the correct 0-based reading, the official 11×11's grid agrees
with its 33 hints in **33 of 33** cells ✅. Only the check was rotten.

**Why nobody noticed**: `tools/check_contract.py` on `main` (both `cf21c25792` and `71092be59e`)
**exits with code 1** — 32 of the 33 hint checks fail, because the check reads
`grid[row-1][col-1]` against 0-based hints, which is a negative index and therefore silently reads
the *last* row of the frame. And the reason nobody saw the red gate is the real lesson:

> **The repository has no `.github/` directory and therefore no CI.** A gate with an exit code that
> nobody ever calls is not a gate.

⇒ The single highest-value change to this repository is not a prune at all: it is one command
that runs the contract check, the tests and the generator self-check and fails on any non-zero
exit — wired into CI. Without it, a changed signature in the search path can pass a full green
test suite (the fast table path never exercises the slow search path), and a stale check can sit
red on `main` for hours.

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

**The fully revealed 4×4 benchmark of §6** (mind the 1-based hints of that fixture — see §6.4):

```python
import json, sys, time; sys.path.insert(0, 'src')
from solver import solve_grid

p = json.load(open('data/puzzles/counterexample-4x4-two-answers/puzzle.json'))
hints = {(h['row'] - 1, h['col'] - 1): h['value'] for h in p['hints']}   # 1-based -> 0-based

t0 = time.time()
res = solve_grid(4, hints, budget=400_000)
print(res['answers'], res['cardinality'], res['partitions'], res['exhaustive'], res['nodes'])
# [112, 304] 2 2 True 206
```

The expected answer set is the fixture's own `answers: [304, 112]`, and the expected partition
count is 2 (see the argument in §6).

**The sparse benchmark — the official 5×5 example** (§6). This is the one that still fails:

```python
import json, sys, time; sys.path.insert(0, 'src')
from solver import solve_grid

p = json.load(open('data/puzzles/official-example-5x5/puzzle.json'))
hints = {(h['row'] - 1, h['col'] - 1): h['value'] for h in p['hints']}   # 1-based -> 0-based

t0 = time.time()
res = solve_grid(5, hints, budget=400_000, report_every=100_000)
print(res['answers'], res['exhaustive'], res['nodes'], time.time() - t0)
# [] False 400001 46.3      <- the known answer 8045 is NOT found
```

**The area lower bound of §6.1**, computed from the published numbers alone:

```python
import json
p = json.load(open('data/puzzles/official-example-5x5/puzzle.json'))
H = {(h['row'] - 1, h['col'] - 1): h['value'] for h in p['hints']}

need = {}
for (r, c), v in H.items():
    need[(r, c)] = max(
        [abs(v - H[nb]) for nb in ((r+1, c), (r-1, c), (r, c+1), (r, c-1)) if nb in H] or [0])

for (r, c), v in sorted(H.items()):
    if need[(r, c)]:
        print(f"({r},{c}) d={v} -> its state has area >= {need[(r, c)]}")
# (0,0) d=12 -> its state has area >= 4
# (1,0) d=8  -> its state has area >= 4
# (1,2) d=6  -> its state has area >= 3
# (1,3) d=3  -> its state has area >= 3
# (3,1) d=7  -> its state has area >= 1
# (3,2) d=6  -> its state has area >= 1
# (3,4) d=10 -> its state has area >= 10
# (4,4) d=0  -> its state has area >= 10
```

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
