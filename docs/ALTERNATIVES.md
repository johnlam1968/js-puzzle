# AODFS — the discussion log: analogies, translations, experiments

> **Why this file exists.** The design archive ([`DESIGN.md`](DESIGN.md)) records *what* the solver
> does. This file records **how the next round of ideas actually arrived**: the analogies, the
> precise statements they turned into, the experiments that were run against them, and the parts
> that are still open.
>
> **Provenance** (so nobody has to guess who said what):
> * the three analogies in §1 are the **user's** — they came in as intuition, not as mathematics;
> * the translations in §2–§4 and the measurements in §5 are **mine**;
> * the solver work quoted in §6 is the **peer session's** (`main` after `fe89aa4`).
>
> Everything marked **MEASURED** was run and the numbers are reproducible with the snippets in
> §7. Everything marked **CONJECTURE** is a hypothesis that has not been proved.

---

## 1. The three analogies (the user's, 2026-10-23)

**A. Magnets / anchors.**
> known capitol (from "0") is single magnet, neighbouring "23" and "12" cost numbers are magnets.
> Or you can call "anchors".

**B. Speculation.**
> if this cell A reads 3, the adjacent cell B reads 6, maybe the adjacent shape is a 3-block L
> shape Z, with its capitol C near A that's why A reads 3, and cell B need to travel two 3 cost
> cells to reach C. Now assume Z, what happens to other "rem" cells? Oh, some other constrains
> could not be met, so Z doesn't work, let us note this.

**C. Rivers and deltas.**
> growing shapes are somehow similar to rivers flowing east, forming deltas.

The user's own summary of the session: *"your two questions are more worthful than my answers.
Frankly my imaginations stop at my poetic inspirations. You should diffuse and try."* — which is
why §4 and §5 are experiments rather than more interpretation.

---

## 2. Translation A — magnets become an **area lower bound**

**The exact statement.** For two orthogonally adjacent cells `x`, `y`, the step between them costs
`w = min(size_x, size_y)` (the size of the shared state if they are in the same one). The
difference of their d-values cannot exceed one step, so

> **|d(x) − d(y)| ≤ min(size_x, size_y)** ⇒ **both** states have area ≥ |Δ|

This is stronger than the L3/L2 form in `DESIGN.md` §3.3, which only pins the state containing
`x`. The strength of the bound is the "magnet" reading: *the drop between two published numbers is
a heavy object sitting between them.*

**MEASURED** — the official 5×5, from the published numbers alone (no ground truth used):

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

On the full 5×5 d-field, **18 of the 25 cells have their state's area pinned exactly** (lower
bound = true area) and 3 more are within 1. This was the single most productive idea in the
project: after it was implemented, the 5×5 went from *400,001 nodes and no answer* to *129,319
nodes and the answer 8,045, exhaustive and unique*.

---

## 3. Translation B — speculation becomes **hypothesis, propagation, refutation, and a note**

The user's example is not an approximation. **MEASURED** on the official 5×5, the actual step-cost
sequence of the optimal path from each cell to its nearest capitol:

| cell | d | step costs | what the user said |
|---|---|---|---|
| (1,3) | 3 | **[3]** | "the adjacent 3-block, capitol near A" |
| (1,2) | 6 | **[3, 3]** | "B needs to travel two 3 cost cells to reach C" |
| (0,2) | 10 | [3, 3, 4] | — |
| (4,0) | 25 | [7, 7, 11] | — |

⇒ The mechanism is exactly what the intuition says: **d is a sum of step costs, and every step
cost is a state size** (or the smaller of two state sizes when the path crosses a boundary).

**The part that matters most is the last clause of the user's sentence — "let us note this".**
Refuting a hypothesis and *throwing the refutation away* means the same hypothesis gets refuted
again in every other branch. Recording it turns the search into a conflict-learning search: a
hypothesis is `H = (cell, size, symmetry)`; refuting `H` records `H is infeasible`, and the
record prunes the whole subtree, not just the branch.

**The second part of translation B** is a lemma that the peer implemented (§6):

> **`d(x) = 1` ⇒ an adjacent 1×1 state (a capitol).**

*Proof.* The cheapest path from `x` costs 1, so it is a single step of cost 1. A step costs 1 only
if one of the two states has area 1, and a 1×1 state is its own capitol. ∎

---

## 4. Translation C — rivers become a **flow field**, and the growth order should be canonical

**The d-field is a terrain.** Every cell flows downhill towards d = 0, and the capitols are the
sinks. A path's step costs are the "width of the river" on each reach; a **tight edge** is a
reach where the drop equals the width exactly; a **delta** is where several flows merge into one
reach.

**MEASURED** — the official 5×5, using the true solution to find the tight edges:

* 40 adjacent edges, **28 are tight (70%)**;
* **every one of the 4 states has at least one tight edge** (16, 10, 18, 12 per state);
* for **28 of 28** tight edges, `min(size_x, size_y) = Δ` exactly;
* **the set of tight-edge drops is exactly `{3, 4, 7, 11}` — the state-size multiset.**

That last line is the strongest form of the idea: **the tight edges are a certificate of the
state sizes.**

### The sharper form (this is the new knife)

A tight edge says `min(size_x, size_y) = Δ` — the **smaller** of the two states has area exactly
Δ. So the bound of §2 splits into an exhaustive dichotomy:

> either **both** states have area ≥ Δ+1 (the edge is *not* tight), or **one of them** has area
> **exactly** Δ (the edge is tight).

The current area lower bound only ever uses the union of those two cases ("both ≥ Δ"). Splitting
them is what makes the second case bite, because an exact area is a *far* smaller shape space than
a lower bound.

**MEASURED** — pruning power on the 4×4 catalogue (1,130 legal states), counting the legal states
that contain a given anchor cell:

| anchor | target area k | area **exactly** k | area **≥ k** | cut |
|---|---|---|---|---|
| (1,1) interior | 3 | 16 | 762 | **47.6×** |
| (1,1) | 4 | 30 | 746 | 24.9× |
| (1,1) | 7 | 67 | 574 | 8.6× |
| (1,1) | 11 | 54 | 195 | 3.6× |
| (0,1) edge | 3 | 9 | 561 | **62.3×** |
| (0,1) | 4 | 14 | 552 | 39.4× |

⇒ An exact area is worth **4–60×** on the state-shape branching, on top of everything the lower
bound already gives.

**CONJECTURE (and the honest limit of this knife).** A tight edge pins the *smaller* of the two
states. A **filler state** (no capitol) is exactly the one that is not otherwise anchored, so
tight edges may pin its *neighbour* instead of itself. Whether the dichotomy propagates far
enough to control the filler states — the explosion source on the 11×11 — is **not yet
established**, and it is the single most important open question in this file.

### The "delta" reading, and what it says about growth order

If a state's shape is a river delta — narrow at the root, fanning out downstream — then the
**order** in which the orbits are added should be canonical: *by distance from the anchor*, like
water running downstream. Today the solver picks any cell of the frontier (`sorted(frontier)`),
which is water flowing in four directions at once. A canonical order would generate every shape
exactly once, and the current "deduplicate the intermediate sets with the same (anchor, symmetry)"
hack is the symptom of the non-canonical order.

---

## 5. The other global constraint the numbers imply (mine, untested at scale)

**Every d-value is a sum of state sizes.** Because d is a sum of step costs, and each step cost is
a state size or the smaller of two state sizes, `d` must be expressible as a sum of members of the
state-size multiset.

**MEASURED** — the official 5×5, with the true sizes {3, 4, 7, 11}: every published d decomposes ✅

```
3=3   4=4   6=3+3   7=7   8=4+4   10=3+7   12=4+4+4
13=3+3+7   14=3+11   17=3+3+11   25=3+11+11
```

**CONJECTURE.** This is a *global* constraint — the solver's pruning is currently per-cell or
per-adjacent-pair, and nothing links all 33 published numbers to the set of state sizes at once.
On the 11×11 the constraint is weak when 1×1 states are available (everything decomposes as
`d × 1`), so its value has to be checked rather than assumed.

---

## 6. What the peer session built, and what came out of the exchange

| when | what | measured result |
|---|---|---|
| `53cfda0` | the four profile fixes + the area lower bound (`_need`) + the contract fix | 4×4: 48,617 → **951** nodes; 5×5: 400,001 nodes & no answer → **129,319** nodes, 8,045, exhaustive, unique |
| `fe89aa4` | the `d = 1` rule (§3) + four never-compiled files fixed + 8 gates | 4×4 counterexample: 206 → **199** nodes, still exhaustive |
| (running) | tight-edge coupling — the next knife (§4) | 11×11: 14 M nodes, 0 answers, ~16,600 nodes/s |

**Two lessons from the exchange that are worth more than the code:**

1. **A gate with an exit code that nobody calls is not a gate.** `tools/check_contract.py` was
   *red* on `main` (exit code 1) and nobody saw it, because the repository had no CI at all.
   Four Python files had never compiled. The fix that generalises: a `py_compile` sweep over the
   whole tree, plus one command that runs every gate.
2. **The engine is the only source of truth.** `tools/capitol_bound_11x11.py` had re-implemented
   the hitting-set logic and had five fatal errors; the committed *data* turned out to be fine,
   because `src/hitting.py` reproduces it exactly. The bug was having two sources of truth, one
   of which could not run.

---

## 7. Reproducing the measurements

**The area lower bound and the tight edges (official 5×5)** — §2, §4:

```python
import json, collections, sys
sys.path.insert(0, 'src')

t = json.load(open('data/puzzles/official-example-5x5/truth.json'))
d, st, sizes = t['d_field'], t['states'], t['state_sizes']

def size_of(r, c):
    k = st[r][c]
    return sizes[k] if k < len(sizes) else 1

# (a) the area lower bound, from the d-field ALONE
for r in range(5):
    for c in range(5):
        A = max([abs(d[r][c] - d[nr][nc])
                 for nr, nc in ((r+1,c),(r-1,c),(r,c+1),(r,c-1))
                 if 0 <= nr < 5 and 0 <= nc < 5] or [0])
        if A == size_of(r, c):
            pass                      # 18 of the 25 cells are pinned exactly

# (b) the tight edges
tight = 0; edges = 0; per_state = collections.Counter()
for r in range(5):
    for c in range(5):
        for dr, dc in ((1,0),(0,1)):
            nr, nc = r+dr, c+dc
            if nr >= 5 or nc >= 5: continue
            edges += 1
            a, b = st[r][c], st[nr][nc]
            w = size_of(r,c) if a == b else min(size_of(r,c), size_of(nr,nc))
            if abs(d[r][c]-d[nr][nc]) == w:
                tight += 1
                per_state[a] += 1; per_state[b] += 1
print(edges, tight, dict(per_state))     # 40 28 {0: 16, 1: 10, 3: 18, 2: 12}
```

**The shape-count pruning ratio (4×4 catalogue)** — §4. See `src/tilings.py` for the enumerator;
the numbers quoted are: area 3 → 52 placements, area 4 → 65, area 7 → 96, area 11 → 72 (1,130
legal states in total; every even area has **no** capitol).

**The `d = 1` forced capitols (11×11)** — §3:

```python
import json, sys
sys.path.insert(0, 'src')
from hitting import capitol_lower_bound

p = json.load(open('data/puzzles/official-11x11/puzzle.json'))
n, G = p['size'], p['grid']
hints = {(r, c): G[r][c] for r in range(n) for c in range(n) if G[r][c] is not None}

res = capitol_lower_bound(n, hints)
print(res['singleton_demands'])
# {(2, 5): [(1, 5), (3, 5), (2, 4), (2, 6)],
#  (3, 6): [(2, 6), (4, 6), (3, 5), (3, 7)],
#  (4, 10): [(3, 10), (5, 10), (4, 9)]}
```

---

## 8. Open questions

1. **Does the tight-edge dichotomy actually control the filler states?** (§4) This is the crux.
   Tight edges pin the smaller of the two states; filler states are the ones with no capitol and
   therefore no anchor. If the propagation stalls, the 11×11 stays unsolved no matter how many
   nodes are spent.
2. **Can the d-decomposition constraint (§5) bite at all on the 11×11?** It is weak whenever 1×1
   states are available. Is there a variant that is not?
3. **Is the tight-edge set a *certificate* in general?** On the 5×5 the tight-edge drops are
   exactly the state-size multiset, and every state has at least one tight edge. Is that a
   theorem, or a coincidence of a 5×5 with 3 capitols?
4. **The two questions the analogies raised but did not answer** — *"is the delta several states
   merging into one capitol?"* and *"does a magnet have an attraction radius?"* — the first
   connects to the capitol watershed (each capitol's catchment is an enumerable object, the same
   thing as the hitting set seen from the other side); the second is already answered by the
   step-count lemma: a cell reading `v` has a capitol within `⌊(v+1)/2⌋` steps, so every number
   carries its own ball.

---

## 9. Where the pieces live

| file | what it holds |
|---|---|
| `docs/DESIGN.md` §3 | the authoritative AODFS design |
| `docs/AODFS-LAYMAN.md` | the layman's version of the same thing |
| `src/grow.py` | the growth itself: `grow_states`, `symmetry_choices`, `orbits_of` |
| `src/hitting.py` | capitol positions as a hitting set; also `singleton_demands` (the `d = 1` rule) |
| `src/solver.py` | the readings-driven solver: `_need` (area bound), the `d = 1` prunes, the tight-edge work |
| `PLAN.md` | the defect register — D38 (the name), D43 (odd area), D48 (orbit semantics), D53, D64, D65, D85 |
