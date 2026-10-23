# AODFS, explained without the maths

> **This is a companion, not a source of truth.** The authoritative description of AODFS is
> [`DESIGN.md` §3](DESIGN.md#3-aodfs锚点--对称轨道生长) (growth rules, pruning table, completeness
> argument, complexity). This file is the *layman's version*: what the algorithm does, why it exists,
> and what it is allowed to claim. Where the two disagree, DESIGN.md wins.

**Status of this document:** 2026-10-23 (17:25 UTC). The numbers marked ✅ are measured and
reproducible with the snippets in §7. The numbers marked ⚠️ belong to work that was still **in flight**
when this was written (the solver, `src/solver.py`, is not on `main` yet) — see §6.

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

On the 4×4 the same rule cut the *generated candidate states* for one anchor from 664 to 155
(4×) ⚠️.

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

### ⚠️ In flight at the time of writing (not on `main`)

* **The solver** (`src/solver.py`) merges "grow a state" and "place a state" into one DFS. It was
  still being written when this document was written, and it is **not committed to `main`**.
* **4×4 with all 16 cells hinted: 200,000 nodes and no answer yet.** With every cell constrained,
  the search should be nearly trivial, so this is a *pruning* defect, not a scale problem.
* **11×11 is running with a 3,000,000-node budget** and had not produced a result.
* Honest complexity budget (DESIGN.md §3.5): ~10⁴–10⁸ candidates per anchor, 10⁹–10¹¹ nodes
  overall ⇒ a **node budget is mandatory**, and exhausting it must be reported as `unknown` —
  never as "unique".

> **The honest one-liner:** AODFS is currently *the only route that has been seriously argued* and
> *the direction the implementation is actually taking* — it is **not** a finished solver.

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
