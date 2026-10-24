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

**MEASURED** — the official 5×5, using the true solution to find the tight edges.

**First, the two kinds of edge have to be kept apart** — they were mixed in the first version of
this note, and the mix is what made a wrong conclusion look right:

| kind | step cost `w` | "tight" means | what the drop Δ means |
|---|---|---|---|
| **cross-state** (the two cells are in different states) | `min(size_x, size_y)` | `min = Δ` | the **smaller** of the two states has area exactly Δ |
| **within-state** (same state) | that state's size | `Δ = size` | that state's own area is Δ |

**MEASURED** on the official 5×5 ✅ (independently re-checked):

* 40 adjacent edges = **18 cross-state + 22 within-state**;
* **all 18 cross-state edges are tight** — the 12 that are *not* tight are **100% within-state**;
* the cross-state tight drops are `{3, 4, 7}` — the *smaller* member of each pair;
* the within-state tight drops are `{3, 4, 7, 11}` — **every state's own area**.

⇒ **The "Δ set = state-size multiset" certificate comes from the *within-state* tight edges**, not
from the cross-state ones. (The cross-state drops cannot contain 11, because the 11-cell state is
never the smaller member of a pair.) Both sets are useful; they are just not the same set.

### ❌ A withdrawn claim: the dichotomy is a tautology

This note originally proposed turning the bound into an exhaustive dichotomy:

> either **both** states have area ≥ Δ+1 (the edge is not tight), or **one of them** has area
> **exactly** Δ (the edge is tight)

and claimed it was "the new knife", because "an exact area is a far smaller shape space than a
lower bound" — measured on the 4×4 catalogue as **4–60×** (e.g. at an interior anchor, 16 legal
states have area exactly 3 versus 762 with area ≥ 3).

**That claim is withdrawn.** The dichotomy is exactly equivalent to the area lower bound of §2:
since `min(size_x, size_y) ≥ Δ` and the areas are integers, "both ≥ Δ+1 or one exactly Δ" is the
*same statement* as "both ≥ Δ". It is a tautology and **it prunes nothing**. The 4–60× figure was
**post-hoc**: it counts the shapes *after* you already know the area, and the solver does not know
the area. Worse, the inference "if the edge is not tight then some other state must be exactly Δ"
is **not valid** — a cross-state edge may legally have `min(size) > Δ` (the two d-values are close,
the step is simply a big one).

⇒ **Tight edges are a diagnostic, not a pruning rule.** What they give is the *certificate* above,
plus the observation below.

### The honest limit, which is also the reason this knife is not the one we need

A tight edge pins the **smaller** of the two states. A **filler state** (no capitol) is exactly
the one that nothing else anchors, so a tight edge may pin its *neighbour* instead of itself. This
is why the tight-edge route does not obviously cure the 11×11's disease: **the filler states are
the big ones, and big states are never the "smaller member" of a pair.** On the 5×5 the 11-cell
state is the frame's largest and is pinned only by a *within-state* edge.

### What the same idea does say: the growth order is not canonical

If a state's shape is a river delta — narrow at the root, fanning out downstream — then the
**order** in which the orbits are added should be canonical: *by distance from the anchor*, like
water running downstream. Today the solver picks any cell of the frontier (`sorted(frontier)`),
which is water flowing in four directions at once.

**MEASURED** — how much work that costs, counting growth paths against distinct shapes reached.
Two independent measurements, and **they do not agree on the multiplier** — because they use
different denominators:

| measurement | frame | paths | shapes | redundancy |
|---|---|---|---|---|
| this note (leaf paths, single anchor) | 4×4 | 7,278 | 1,878 | 3.9× |
| this note (leaf paths, single anchor) | 5×5 | 501,780 | 74,014 | 6.8× |
| peer session (`tools/measure_path_redundancy.py`, all intermediate states × all corner anchors) | 4×4 | 2,309,436 | 2,420 | **954.31×** |
| peer session, canonical (Redelmeier) order | 4×4 | 2,420 | 2,420 | **1.00×** |

⇒ The **phenomenon** is the same and the canonical order fixes it (1.00×: every shape reached by
exactly one path). The **multiplier depends on the denominator**, so any quoted factor must state
its definition. The peer's tool computes both and is the reference.

### ⚠️ But the canonical order's *net* benefit in the solver is **negative**

This is the part that matters, and it was measured on the solver, not on the enumeration:

| | nodes | time |
|---|---|---|
| 4×4 fixture, before | 951 | 0.3 s |
| 4×4 fixture, with the canonical order | **559 (−41%)** | 0.1 s |
| 5×5 official, before | 129,319 | 7.1 s |
| 5×5 official, with the canonical order | **109,848 (−15%)** | **13.7 s (twice as slow)** |

⇒ **With pruning on, most of the path duplication is already cut by the lower/upper bounds before
the duplicate state is ever reached.** So the redundancy measured on the *unpruned* enumeration does
not transfer to the *pruned* search, and the per-node cost of building the candidate table plus
sorting exceeds the saving. The 11×11 rate fell from 16,600 to 6,667 nodes/s.

⇒ **The lesson (and the second time this file has been wrong in the same way):** a factor measured
in one context does **not** transfer to another. Here the contexts are "enumerate the state
library" and "search a pruned tree" — different enough that the conclusion flips. The repair the
peer found is to make the *pruning* cheap instead: a single integer AND test ("is there still a
cell that could be a capitol within the radius?") before the expensive early-exit scan, which
restores 16,000 nodes/s on the 11×11 and makes the 5×5 **2.2× faster than before the change**.

⇒ So the canonical order is *not* the lever it looked like. What it did deliver is a **cleaner
measurement instrument** (954× → 1.00×) and a **diagnosis**: the duplication is real in the
enumeration, and invisible in the pruned search. Which means the explosion on the 11×11 is **not**
an ordering artefact — it is a genuine combinatorial problem.

### The landscape is a funnel — and a **greedy descent** walks it

**MEASURED** (a pure best-improvement descent: always move to the cheapest legal neighbour; no
randomness, no annealing, no tolerance):

| instance | start | result |
|---|---|---|
| 4×4 counter-example | 60 random legal tilings (cold start) | **60/60 reach E = 0**, average **3.0 steps** |
| 5×5 official | each of the 23 neighbours of the solution | **23/23**: the single cheapest legal move lands exactly on the solution, from E = 11/12/15/23/25/72 |
| 11×11 official | the all-singletons start | **stalls at E = 480** after 40 steps (82 states) |

⇒ Leaving the solution is expensive; **entering it is one step**. The landscape is a funnel that
funnels inward, and a **random walk cannot walk a funnel** — which is why the annealer's tolerance
sweep (0/5/11/15 → best E = 50) never moved: the moves were *sampled*, not *greedy*.

⇒ ⇒ **the right primitive is the descent, and it was already written**: `src/moves.py::curvature()`
returns `cheapest` and `cheapest_move`. It was implemented, and then an annealer was run instead
of it.

⇒ ⇒ and it is affordable: from the all-singletons 11×11 start only **220 of 7,260 merge pairs are
legal (3%)** ⇒ ~220 energy evaluations per step ⇒ **~0.5 s/step** ⇒ a few hundred steps is a few
minutes. The per-step cost is set by the number of *legal* moves, not the number of candidates.

### Where the model still earns its place

The descent does the walking, so a decision model is **not** needed to pick the next step. What is
left for it — and it is a real job, not a consolation prize:

1. **Escaping a local minimum** — the 11×11's descent stalls at E = 480 from the naive start.
2. **A better start** — the hitting set already produces candidate capitol sets; seeding the
   descent with one of them instead of all-singletons is the obvious experiment, and it uses the
   one half of the work that is currently unused.
3. **A prior on the area map** — the area lower bound says "≥ 7"; nothing local says "a 40-cell
   state here is unusual".
4. **The terrain read** — the d-field is a picture; "the plateau around here looks like one large
   state" is information the local bounds never look at.

### A note on the revisions in this file

Two claims in here were **withdrawn** after the peer session re-measured them, and both withdrawals
are recorded rather than deleted, because the *reason* they failed is the reusable part:

| withdrawn claim | why it failed | what replaced it |
|---|---|---|
| "the refined dichotomy (both ≥ Δ+1, or one exactly Δ) is a new, sharper bound" | it is **logically equivalent** to the bound it refines — a tautology with zero pruning power; and the "4–60×" that backed it was measured *after* the area was already known, so the solver cannot use it | the sharper statement is about **which branch is provable**, not about the union |
| "a cliff landscape forces the search to accept worsening moves" | the measurement (leaving the solution costs 11, two steps out costs 17) is true but was read **outward**; inward, the solution is one step away from every neighbour | the landscape is a **funnel**, and the primitive is a **greedy descent**, not a tolerance |

⇒ The common shape of both failures: **a statement that was true in one direction or one context
was used as if it held in the other.** Both times, the peer caught it. Both times the fix was to
measure *the thing the solver will actually do*.

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

**CONJECTURE — and, on the 11×11, *certainly* dead.** This is a *global* constraint: the
solver's pruning is currently per-cell or per-adjacent-pair, and nothing links all 33 published
numbers to the set of state sizes at once. But the `d = 1` rule (§3) forces **three 1×1 states**
in the 11×11, and once a 1 is available every d decomposes as `d × 1`. So on the 11×11 this
constraint is not merely weak — it is **provably vacuous**. It is recorded here as an observation,
not as a weapon. (On the 5×5 it is also vacuous *in that sense*: the 5×5's true solution has no
1×1 state, which is why the decomposition happens to be informative there.)

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

**The growth-path redundancy** — §4, the evidence for the canonical order. For each (anchor,
symmetry), count the legal *orderings* of orbit additions against the distinct shapes they
reach:

```python
import sys, collections; sys.path.insert(0, 'src')
from grow import symmetry_choices, orbits_of

def redundancy(n):
    board = {(r, c) for r in range(n) for c in range(n)}
    tot_orders = tot_shapes = 0
    for sym in symmetry_choices(n):
        orb = orbits_of(sym, n)
        orbits = sorted({frozenset(o) for o in orb.values() if o <= board}, key=sorted)
        idx = {o: i for i, o in enumerate(orbits)}
        start = idx.get(frozenset(orb[(0, 0)]))
        if start is None: continue
        paths = {1 << start: 1}                 # shape -> number of valid orderings
        stack = [1 << start]; done = set()
        while stack:
            m = stack.pop()
            if m in done: continue
            done.add(m); p = paths[m]
            inside = {c for i, o in enumerate(orbits) if (m >> i) & 1 for c in o}
            border = {c for i, o in enumerate(orbits) if not (m >> i) & 1 for c in o} - inside
            for i, o in enumerate(orbits):
                if (m >> i) & 1 or not (o & border): continue
                nm = m | (1 << i)
                paths[nm] = paths.get(nm, 0) + p
                if nm not in done: stack.append(nm)
        tot_orders += sum(paths.values()); tot_shapes += len(paths)
    return tot_orders, tot_shapes

for n in (4, 5):
    o, s = redundancy(n)
    print(n, o, s, f'{o/s:.1f}x')
# 4 7278 1878 3.9x
# 5 501780 74014 6.8x
```

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

1. **Does a canonical growth order control the filler states?** (§4) This is now the crux. The
   tight-edge dichotomy was withdrawn as a tautology; what remains is that the growth order is not
   canonical, with a measured **3.9× (4×4) / 6.8× (5×5)** redundancy and *every* shape reachable
   by more than one path. If a Redelmeier-style order removes that duplication, the 11×11's
   explosion is (in part) an artefact of ordering rather than of combinatorics — and if it does
   not, the filler states need a different constraint entirely.
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
| `docs/NEXT-APPROACHES.md` | the specification for the three routes that came out of it: simulation, a fuzzy ranking layer, capitol-count speculation |
| `src/grow.py` | the growth itself: `grow_states`, `symmetry_choices`, `orbits_of` |
| `src/hitting.py` | capitol positions as a hitting set; also `singleton_demands` (the `d = 1` rule) |
| `src/solver.py` | the readings-driven solver: `_need` (area bound), the `d = 1` prunes, the tight-edge work |
| `docs/LOCALITY-PLAN.md` | the plan that came out of the (5,10) trim: the facet register, the 5×5 window decomposition, the conservation law as the join, and the per-facet pinning power |
| `tools/constraint_register_11x11.py` | every constraint we have, with its source, its status and its locality |
| `tools/ground_map_11x11.py` | the ground map of the 11×11, trimmed from the (5,10) demand |
| `tools/trim_510.py` | the two blocks the trim forces, the three filters, and the seeded descent |
| `tools/facet_pinning_11x11.py` | the per-facet pinning power, measured on the (5,10) candidate slice |
| `tools/facet_pinpoint_11x11.py` | which sizes a cell can still have, window by window |
| `tools/size_multiset_11x11.py` | the feasible size multisets under the conservation law (121) |
| `tools/coverage_audit_11x11.py` | which of the 33 published numbers a given core actually exercises |
| `tools/infer_sizes_11x11.py` | INFERENCE: what the 33 readings force about the state sizes (no search) |
| `tools/corner_joint_11x11.py` | the 16-block against the readings, step by step |
| `tools/corner_triple_11x11.py` | the (8,12,16) corner triple, joined with a bitset index |
| `tools/infer_readings_11x11.py` | INFERENCE from the readings alone: size bounds, tight edges, path decompositions |
| `tools/chain_corner_11x11.py` | the corner chain (61 = 12*5+1, 13 = 12+1, 77 = 61+16) -> 632 surviving triples |
| `tools/corner_16_11x11.py` | the lower-right corner: the 16-cell block and the "61 + 16 = 77" reading |
| `docs/NEW-ROUTES.md` | four routes outside A/B/C: profile-first, generated twins, satisfiability, style transfer |
| `PLAN.md` | the defect register — D38 (the name), D43 (odd area), D48 (orbit semantics), D53, D64, D65, D85 |

---

## 10. A defect in the constraint register (a third session, 2026-10-23)

*Found while re-reading the register's facets, instance by instance. It changes a displayed
field, not a computed number — but the displayed field is the one a plan gets read from.*

`tools/constraint_register_11x11.py` builds the `F-ball` instance list like this:

```python
"hidden_capitol_within": [[r + dr, c + dc]
                          for dr in (-k, 0, k) for dc in (-k, 0, k)
                          if 0 <= r + dr < N and 0 <= c + dc < N
                          and (dr or dc)],
```

**This is not the ball.** It is the **eight corner points of the k-box** (the Chebyshev
corners), and it does not exclude cells that carry a published `d > 0` — those cells can never
be capitols, because a cell with a reading is not a capitol and a cell with `d = 0` already is
one.

**The engine is right; the register's display is not.** `src/hitting.py::ball()` is Manhattan
(`|Δr| + |Δc| ≤ radius`) and `split_demands()` filters with
`candidates = [c for c in raw if c not in hints]`. So the register's *counts* — 9 demands,
`candidate_pool` 64, `min_additional_capitols` 4, `minimum_capitol_sets` 120 — are **correct**;
only the printed geography is wrong.

**MEASURED** — engine truth vs. the register's list:

| demand | true candidates | the register prints |
|---|---|---|
| (0,1) d=8 | **13** | [(0,5), (4,1), (4,5)] — and (0,5)=11, (4,1)=22 cannot be capitols |
| (0,5) d=11 | **36** | [(6,5)] |
| (2,2) d=7 | **24** | 3 corner points |
| (6,0) d=11 | **33** | 3 corner points |
| (0,9) d=5 | **10** | 3 corner points |
| (2,5) / (3,6) / (4,10) d=1 | 4 / 4 / 3 | the 8-neighbourhood, including published cells |

⇒ **The top-left corner is not pinned to a handful of cells.** Any plan built on "the hidden
capitols are at (4,5), (6,5), (0,6)…" is built on a fiction.

**The fix** (one line):

```python
"hidden_capitol_within": [list(c) for c in ball((r, c), k, N) if c not in HINTS],
```

### 10.1 A second observation, on the "9 one-cell states" claim

`F-human`'s second instance records where that claim came from:

> *"F-area already pins 32 cells into states of area >= 4. The claim is that NINE of them are
> singletons…"*

Two things do not line up:

1. F-area pins **12** cells, not 32 (and only 10 of them have a minimum area ≥ 4; two are = 2);
2. **"area ≥ 4" is the opposite of "is a singleton"** — a lower bound cannot produce a singleton.

⇒ So the entry's own proposed test cannot discriminate, and the note *"it is the one place where
the human is ahead of the arithmetic"* may have it the wrong way round: this looks like
arithmetic that was written wrong, not intuition that ran ahead. The claim is a statement about
the *shape of the solution*, and it should be carried as an observation — not as the thing the
narrowing depends on. (`docs/NEW-ROUTES.md` §6 shows what the narrowing actually rests on: the
six tight edges, {2, 4, 6, 8, 12, 16}.)

**Status:** reported to the `docs/aodfs-layman` session; **not yet fixed** in the branch this
was written against (checked at `9058c21e`).
