# 10-deepseek-code-review — CODE REVIEW

- model: `deepseek/deepseek-v4.1-flash`
- finish_reason: stop
- usage: {"prompt_tokens": 36766, "completion_tokens": 18458, "total_tokens": 55224, "cost": 0.0331794, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0331794, "upstream_inference_prompt_cost": 0.0110298, "upstream_inference_completions_cost": 0.0221496}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 58496 reasoning_chars: 0

---

## REVIEW

# Adversarial review

I read every file. Findings below are ordered by severity. I only list things I can prove from the inlined source.

---

## BLOCKER

### B1. `judge.py` — `_lb_violates` uses Manhattan distance as a *lower* bound on cost, but the cost of a step is `min(sA,sB) >= 1` only when the two states differ; a step *inside* a state costs `s >= 1`. So `Manh(x,c)` is a valid lower bound on the number of steps, and each step costs `>= 1`, hence `cost >= Manh(x,c)`. That part is fine. **But the bound is applied to `possible` cells that include cells in states already placed with NO capitol.** Look at the update:

```python
new_possible = possible & ~mask_m | keep
```

`keep` is the capitol cell of `mask_m` if it has one. If `mask_m` has **no** capitol, `keep == 0`, so all its cells are removed from `possible` — correct. If `mask_m` **has** a capitol, only the capitol cell is kept — correct. So far so good. **However**, `possible` is initialized to `all_cells` and the *first* state placed is the anchor's state. The anchor is chosen by `_pick_anchor`, which prefers the smallest hinted value. If the anchor is a `d=0` cell, `must_fix` is set and the symmetry must fix it — good. But if the anchor is a `d>0` cell, the code does **not** require the anchor's state to be capitol-free, and it does **not** require the anchor's state to contain a capitol. That is fine for soundness. The real bug: **`_lb_violates` is called with `np` computed from `possible` BEFORE the current state is fully grown**, and `possible` still contains cells of the current partial state that are not yet known to be capitol-free. That is conservative (too many possible capitols → weaker bound → sound). Not a bug.

Let me re-read more carefully. The actual BLOCKER is in `_ub_violates`:

```python
def _ub_violates(self, hints, mask):
    cap = self._capitol_of_mask(mask)
    if cap is None:
        return False
    for (r, c), v in hints.items():
        ...
        cost = self._path_cost_inside(mask, (r, c), cap)
        if cost is not None and cost < v:
            return True
    return False
```

`_path_cost_inside` returns the cost of the cheapest path **staying inside `mask`**. But the true `d(x)` is the cost to the nearest capitol **anywhere**, which may be *outside* `mask` and cheaper. So `cost < v` does **not** imply the branch is dead — the true `d(x)` could be even smaller, but the hint says `d(x) = v`. Wait: if the true `d(x) = v`, then any path to *any* capitol costs `>= v`. A path inside `mask` to `cap` is a path to *a* capitol, so its cost is `>= v`. Therefore `cost < v` is impossible in a real solution. So the prune is **sound**. OK.

The real BLOCKER is elsewhere. Let me look at `judge.decide`'s table path:

```python
if self._table is not None:
    fields, answers, n_kept = self._table
    if len(fields) != n_kept:
        ...
        self._table = None
    else:
        ans, count = answers_for_hints(...)
        return {... "exhaustive": True ...}
if self._table is not None:
    fields, answers = self._table[0], self._table[1]
    ...
```

The second `if` is **dead code**: if `self._table` was not `None` at the first `if`, either it was set to `None` (then the second `if` is false) or it returned. So the second block never executes. That is dead code, MINOR, not a blocker.

**Actual BLOCKER — `judge.py` `_lb_violates` is unsound when `possible` is empty but a capitol already exists in a placed state.** No: if `possible == 0` it returns `True` (prune). But `possible` is updated to keep the capitol of each placed state. So if a capitol was placed, `possible` is non-empty. If no capitol placed yet and all cells consumed, `possible == 0` → prune. Correct.

Let me find the real blocker. **`judge.py` line: `new_possible = possible & ~mask_m | keep`.** Python operator precedence: `&` binds tighter than `|`, so this is `(possible & ~mask_m) | keep`. That is the intended meaning. OK.

**BLOCKER: `judge.py` `_lb_violates` computes `best = min(row[cc] for cc in range(n*n) if (possible >> cc) & 1)`.** This is the Manhattan distance from the hinted cell to the nearest *possible* capitol. But the cost from `x` to a capitol `c` is **not** bounded below by `Manh(x,c)` in general — it is bounded below by `Manh(x,c)` only because each step costs `>= 1`. That is correct. **But** the bound must be `>= v` for the branch to survive; the code prunes when `best > v`. If `best == v`, it survives. Correct.

I am not finding a blocker in judge by inspection of the prune. Let me look at **`solver.py` `_lb_violates`** — same structure, same soundness.

**BLOCKER: `solver.py` `rec` — when a state is being grown, the code calls `self._can_close(cur)` and if true recurses with `chosen + [cur]`. But it does NOT check that `cur` is a *maximal* or *canonical* state — it will close `cur` at every intermediate size, and also continue growing. That is correct for completeness (every state is reachable as some `cur`). But the code then continues to extend `cur` by orbits. The issue: `_can_close` requires `connected(cur)` and `symmetry_group(cur)` non-empty. A partial `cur` that is connected and symmetric is a legal state, so closing it is valid. Fine.**

**BLOCKER: `solver.py` — the `possible` mask update when growing.** When a new orbit `o` is added, cells of `o` not in `fixed` are removed from `possible`. But cells of `o` that ARE in `fixed` are added back to `possible`:

```python
for c in fixed:
    if c in newcur:
        np |= 1 << self.idx[c]
```

This is wrong: a fixed point of the growth symmetry `sym` is not necessarily the capitol of the final state. The capitol is decided by the **full point group** (`capitol_of`), not by `sym`. So adding `fixed` cells back to `possible` is **unsound in the wrong direction** — it makes `possible` *larger*, which makes `_lb_violates` *weaker* (more possible capitols → smaller `best` → less pruning). That is conservative, not unsound. But it can also **incorrectly keep a cell in `possible` that is provably not a capitol**, which only weakens pruning. Not a soundness bug.

Wait — the opposite direction matters for the **UB** prune. `_ub_violates` uses `capitol_of(cur)` (full group). Good.

Let me look at the **`grow.py` `grow_states` frontier bug**:

```python
for x in sorted(frontier):
    o = orb[x]
    if o & blocked_set or (o & mask) or not inside(o):
        continue
    newmask = mask | o
    newfront = {y for y in frontier if y != x}
    for y in newmask:
        for nb in (...):
            if ... and nb not in newmask:
                newfront.add(nb)
    expand(frozenset(newmask), newfront)
```

The frontier is recomputed from `newmask`, but the loop iterates over `sorted(frontier)` — the **original** frontier — and for each `x` builds `newfront` from `frontier \ {x}` plus neighbours of `newmask`. This is the standard ESU-style canonical expansion. But there is a subtle bug: `newfront` includes `y` for `y in frontier if y != x`, i.e. it keeps *all other frontier cells*, including cells that are now in `newmask`? No — `frontier` was computed as neighbours of `mask` not in `mask`, so no frontier cell is in `mask`. But after adding `o`, some frontier cells may now be in `o` (i.e. in `newmask`). The code does not remove them from `newfront`. Then in the recursive call, `orb[x]` for such an `x` would have `o & mask` non-empty (since `x in newmask`), so it is skipped. So it is harmless but wasteful. Not a correctness bug.

**BLOCKER candidate: `grow.py` `orbits_of` returns orbits keyed by cell, but `grow_states` uses `orb[anchor]` and `orb[x]` for `x in frontier`. If `x` is not in `orb` (because its orbit leaves the board), `orb[x]` raises `KeyError`.** Look:

```python
def orbits_of(sym, n):
    orb = {}
    for c in cells:
        if c in orb: continue
        o = sym.orbit(c)
        for x in o:
            if 0 <= x[0] < n and 0 <= x[1] < n:
                orb[x] = o
    return orb
```

So `orb` only contains cells whose orbit is *entirely* on the board? No — it contains `x` if `x` is on the board, regardless of whether the whole orbit is on the board. So `orb[x]` exists for every board cell `x`. Then `inside(o)` checks `o <= board`. Good. So no KeyError.

But in `grow_states`:
```python
start = orb[anchor]
if start & blocked_set or not inside(start):
    return []
```
`anchor` is a board cell, so `orb[anchor]` exists. Good.

**BLOCKER: `solver.py` `_orbits` caches by `id(sym)`.** `symmetry_choices(n)` returns a fresh list each call, but `Solver.__init__` calls it once and stores `self._syms`. The `id` of each `Symmetry` object is stable for the lifetime of the solver. But `_orb_cache` is keyed by `id(sym)` — if a `Symmetry` object is garbage collected and a new one allocated at the same address, the cache would collide. Since `self._syms` holds references, no GC. Fine.

**BLOCKER: `lazycatalogue.py` `__new__` returns a cached instance, but `__init__` is still called on it.** Python calls `__init__` on the object returned by `__new__` if it is an instance of `cls`. So `LazyCatalogue(n)` returns the cached object and then re-runs `__init__`, which **resets `self._cell_cache = {}`** and **resets `self.max_cells` and `self.budget`**. This destroys the cache and, worse, if a caller passes different `max_cells`/`budget`, the shared instance is silently reconfigured. The docstring claims "the per-anchor cache is SHARED across instances (module level), so building a second Generator for the same size costs nothing" — **that is false**: `__init__` wipes `_cell_cache` every time. This is a MAJOR/BLOCKER performance and correctness bug (the cache is never actually reused; and a second `Generator(4)` with different budget silently changes the first one's config).

Demonstration:
```python
a = LazyCatalogue(4)
a.cell_states((0,0))
b = LazyCatalogue(4)
assert a is b
assert a._cell_cache == {}   # wiped by b's __init__
```

Fix: guard `__init__` with `if getattr(self, "_built", False): return` (as `Catalogue` does), or use a factory.

### B2. `tilings.py` `Catalogue.__init__` — same `__new__`/`__init__` pattern, but it *does* guard:
```python
if getattr(self, "_built", False) and getattr(self, "n", None) == n:
    return
```
Good. But `_CATALOGUE_CACHE[n] = self` is set at the **end** of `__init__`, and `__new__` checks the cache. If `__init__` raises (e.g. `connected_subsets` fails), the object is not cached — correct. But if `__init__` is called a second time on a cached object with a **different** `n`... `__new__` returns the cached object for the *requested* `n` only if `n in cache`. So `Catalogue(4)` then `Catalogue(5)` creates a new object. Fine.

### B3. `hitting.py` `min_hitting_set` — the branch-and-bound is **not** a correct minimum hitting set. Look:

```python
def rec(chosen, covered):
    if best[0] is not None and len(chosen) > best[0]:
        return
    unc = [i for i in range(len(demands)) if i not in covered]
    if not unc:
        ... update best ...
        return
    i = min(unc, key=lambda j: len([c for c in demands[j][3] if c not in chosen]))
    for c in demands[i][3]:
        if c in chosen: continue
        rec(chosen + [c], covered | {j for j in range(len(demands)) if c in demands[j][3]})
```

The branching picks the uncovered demand `i` with the fewest viable candidates and branches on each candidate `c` of `demands[i][3]`. This is the standard "branch on an uncovered set" algorithm and **is** complete: any hitting set must contain some `c` in `demands[i][3]`. So it finds the minimum. The `covered` set is recomputed by scanning all demands for each `c` — O(m) per branch. Correct but slow. Not a bug.

**But** `best[1]` accumulates **all** minimum sets, and the recursion explores the full tree even after finding a minimum of size `k` — it prunes only when `len(chosen) > best[0]`. So it enumerates all minimum hitting sets. That is intended (`n_minimum_sets`). Fine.

**BUG in `packing_bound`:** 
```python
for r in range(m + 1):
    found = False
    for combo in _combinations(range(m), r):
        ...
        if ok:
            best = max(best, r)
            found = True
            break
    if not found and r > 0:
        break
```
This finds the largest `r` for which *some* `r`-subset has pairwise disjoint candidate sets. But it breaks out of the outer loop as soon as no `r`-subset works. Since disjointness is monotone (a subset of a disjoint family is disjoint), if no `r`-subset works then no `(r+1)`-subset works. So the break is correct. But the `found` flag is set to `True` on the *first* working combo and then `break`s the inner loop — so it only checks one combo per `r`. That is fine for finding *whether* an `r`-subset exists. Correct.

### B4. `cost.py` `Puzzle.__init__` — the overlap check is wrong:
```python
claimed = sum(len(s) for s in self.states)
if claimed != self.h * self.w:
    raise ValueError("the states overlap: ...")
```
If two states overlap, `claimed > h*w`, so the check fires. But if the states are disjoint and cover a *sub*-rectangle, `claimed < h*w` and the check fires with a misleading message. More importantly, the `holes` check already catches uncovered cells. The overlap check is redundant but not wrong. MINOR.

**Real bug in `Puzzle.__init__`:** `self.h` and `self.w` are computed from the states, so a partition of a non-rectangular region (e.g. an L-shaped set of cells) would have `h*w > claimed` and raise. That is intended. But an **empty** `states` list gives `h=0, w=0`, `claimed=0`, `h*w=0`, no holes, no error. Then `cost_field` returns `[]`, `row_sums` returns `[]`, `answer` returns `0`. The spec says a partition with no capitol is not a solution; an empty partition has no capitol, so `answer()` returning 0 is misleading but not used. MINOR.

### B5. `rules.py` `symmetry_group` — the 90/270 candidate is added when `(sr-sc) % n == 0 and (sr+sc) % n == 0`, with `k1 = (sr-sc)//n`, `k2 = (sr+sc)//n`. The map is `(r,c) -> (c+k1, k2-r)`. For this to be a 90° rotation about the centroid, the centroid must be `((k1+k2)/2, (k1-k2)/2)`... let me verify. The map `(r,c) -> (c+k1, k2-r)` has fixed point where `r = c+k1` and `c = k2-r`, i.e. `r = c+k1`, `r+c = k2`. So `2r = k2+k1`, `r = (k1+k2)/2`, `c = (k2-k1)/2`. The centroid is `(sr/n, sc/n)`. For the map to fix the centroid: `sr/n = (k1+k2)/2` and `sc/n = (k2-k1)/2`. With `k1 = (sr-sc)/n`, `k2 = (sr+sc)/n`: `(k1+k2)/2 = (2sr/n)/2 = sr/n`. ✓. `(k2-k1)/2 = (2sc/n)/2 = sc/n`. ✓. So the map is a 90° rotation about the centroid. Good.

But the **divisibility condition** `(sr-sc) % n == 0 and (sr+sc) % n == 0` is necessary for the centroid to be a lattice point of the form `(k1/2, k2/2)` with `k1, k2` integers of the same parity. Actually for a 90° rotation about `(a/2, b/2)` to map the integer lattice to itself, we need `a, b` integers with `a ≡ b (mod 2)`. Here `k1 = (sr-sc)/n`, `k2 = (sr+sc)/n`. The condition `k1 ≡ k2 (mod 2)` is `(sr-sc)/n ≡ (sr+sc)/n (mod 2)`, i.e. `2sc/n ≡ 0 (mod 2)`, i.e. `sc/n` integer... This is **not** checked. So the code may add a `rot90` candidate whose map does not preserve the lattice. But then the `image != S` check rejects it. So it is only a wasted candidate, not a correctness bug. MINOR.

### B6. `grow.py` `symmetry_choices` — the `rot90`/`rot270` loops iterate `k1, k2` over `range(-n, 2*n+1)` and skip when `(k1-k2) % 2 or (k1+k2) % 2`. This is the parity condition. But the **range** is `-n .. 2n`, which for `n=4` is `-4..8`. The centroid of a state in a 4x4 grid has `sr/n` in `[0, 3]`, so `k1 = (sr-sc)/n` in `[-3, 3]` and `k2 = (sr+sc)/n` in `[0, 6]`. The range `-4..8` covers these. For general `n`, `k1` ranges `[-(n-1), n-1]` and `k2` ranges `[0, 2n-2]`. The range `-n..2n` covers both. Good.

But `refH` and `refV` iterate `k` over `range(-n, 2*n+1)`, and the map is `(r,c) -> (k-r, c)`. For a reflection about row `k/2`, the fixed cells are those with `r = k/2`. For `k` even, the axis is at an integer row; for `k` odd, at a half-integer. The range covers `k` from `-n` to `2n`. The centroid row `sr/n` is in `[0, n-1]`, so `k = 2*sr/n` is in `[0, 2n-2]`. Covered. Good.

### B7. `judge.py` `_lb_violates` — **the bound is computed over `possible` cells, but `possible` is initialized to `all_cells` and never restricted to cells that could actually be capitols of *odd-sized* states.** A capitol requires an odd-sized state (rule 6). The code does not use this. That only weakens pruning. MINOR.

### B8. `judge.py` `decide` — the search path's `rec` does **not** check `_ub_violates` for the *final* state when `rem == 0`. It checks `_ub_violates` for each state as it is placed (in the loop over `cands`). But the last state placed is checked before recursing. So all states are checked. Good.

**But** `_ub_violates` is called with `mask_m` for each candidate state, and it checks hinted cells *inside* `mask_m`. If a hinted cell is in a state that has a capitol, and the path inside that state to the capitol costs less than the hint, prune. Correct.

### B9. `judge.py` `decide` — **the `possible` mask is updated as `new_possible = possible & ~mask_m | keep`, but `keep` is computed from `cap = self._capitol_of_mask(mask_m)`. If `cap is None`, `keep = 0`, so all cells of `mask_m` are removed from `possible`. Correct. But if `cap` is not None, only `cap` is kept. Correct.**

**However**, the initial `possible = all_cells` includes cells that are hinted with `d > 0`. A hinted `d > 0` cell can never be a capitol (rule 12 / the code's own comment in `hitting.py`). The judge does not exclude them. This weakens the LB prune. MINOR.

### B10. `solver.py` `_pick_anchor` — 
```python
best = None
for (r, c), v in self.hints.items():
    i = r * self.n + c
    if not (rem >> i) & 1: continue
    if best is None or v < self.hints[best]:
        best = (r, c)
```
This picks the hinted cell with the smallest `v` that is still in `rem`. But `self.hints[best]` — `best` is a cell tuple, and `self.hints` is keyed by cell. Correct. But if no hinted cell is in `rem`, it falls back to the lowest-index cell. Correct.

**BUG:** `_pick_anchor` is called at the start of a new state. But the anchor must be a cell of the new state. If the smallest-`v` hinted cell is in `rem`, it is chosen. But the state grown from that anchor may not contain all hinted cells — that is fine, other states will cover them. Correct.

### B11. `solver.py` `rec` — **when `cur is None` and `rem == 0`, it calls `self._complete(chosen)`. But `chosen` is the list of closed states. `_complete` builds a `Puzzle` and checks the cost field. Correct.**

**BUG:** `_complete` does not check that the partition has at least one capitol *before* building the cost field — it does: `if not puz.capitols: return`. Correct.

### B12. `solver.py` `rec` — **the `possible` mask update when starting a new state:**
```python
np = possible
for c in start:
    if c not in fixed:
        np &= ~(1 << self.idx[c])
for c in fixed:
    if c in start:
        np |= 1 << self.idx[c]
```
This removes non-fixed cells of the first orbit from `possible` and adds back fixed cells. But the state is not yet closed, so its capitol is not yet known. Removing non-fixed cells is **unsound in the wrong direction**? No — it makes `possible` smaller, which makes `_lb_violates` *stronger* (fewer possible capitols → larger `best` → more pruning). If the removed cells could actually be the capitol of the final state, this would be **unsound** (prune a valid branch). Can a non-fixed cell of the first orbit be the capitol of the final state? The capitol is fixed by *every* symmetry in the full point group. The growth symmetry `sym` is in the point group (the state is `sym`-invariant). So the capitol must be fixed by `sym`. A non-fixed cell of `sym` cannot be the capitol. So removing them is **sound**. Good.

But the code adds back `fixed` cells that are in `start`. A fixed cell of `sym` is a candidate capitol. Correct.

**However**, when growing by a new orbit `o`:
```python
for c in o:
    if c not in fixed:
        np &= ~(1 << self.idx[c])
for c in fixed:
    if c in newcur:
        np |= 1 << self.idx[c]
```
Same logic. Sound.

### B13. `solver.py` `_can_close` — 
```python
if not connected(cur): return False
group = symmetry_group(cur)
if not group: return False
cap = capitol_of(cur)
if cap is not None and self._ub_violates(cur, cap): return False
return True
```
This returns `True` for a state with no capitol (cap is None). That is correct — a capitol-less state is legal. But then `rec` closes it and recurses. Correct.

**BUG:** `_can_close` is called at every node where `cur is not None`. If `cur` is a legal state, the code closes it AND continues to grow it. This means the same final state can be reached by closing at different intermediate sizes? No — closing `cur` means `cur` is a state in the partition. Growing `cur` further means a larger state. These are different partitions. Correct.

### B14. `generator.py` `hint_ladder` — 
```python
ladder.append({"step": len(ladder) + 1, "hints": dict(remaining), ...})
pool = {k: v for k, v in all_hints.items() if k not in remaining}
while pool:
    best, best_score = None, None
    for cell, val in pool.items():
        trial = dict(remaining); trial[cell] = val
        res = self.judge.decide(trial, budget)
        score = (res["partitions"], res["cardinality"])
        if best_score is None or score < best_score:
            best, best_score = cell, score
    remaining[best] = pool.pop(best)
    ...
ladder.reverse()
```
The ladder starts with the irreducible set (hardest) and adds hints back one at a time, choosing the hint that minimizes `(partitions, cardinality)`. Then it reverses, so the ladder goes from all hints (easiest) to the irreducible set (hardest). The test asserts `sizes == sorted(sizes, reverse=True)`, i.e. the ladder shrinks monotonically. Since `remaining` grows by one each iteration, the reversed ladder has sizes `len(minimal)+k` for `k = 0..len(pool)`, which is increasing, so reversed it is decreasing. Correct.

**BUG:** The ladder's first entry (after reverse) is the *last* `remaining`, which has all hints. But the code appends the initial `remaining` (the irreducible set) first, then adds hints. After reverse, the first entry is the one with all hints. The test asserts `len(ladder[0]["hints"]) == all_hints_count`. Correct.

**BUG:** `score = (res["partitions"], res["cardinality"])` — the comment says "the most informative hint is the one that leaves the FEWEST consistent tilings". But `res["partitions"]` is the number of *matching tilings*, and `res["cardinality"]` is the number of distinct answers. Minimizing `partitions` is the stated goal. But the code compares tuples `(partitions, cardinality)`, so it first minimizes `partitions`, then `cardinality`. Correct.

### B15. `generator.py` `worked_trace` — 
```python
if v == 1:
    cands = []
    hinted = {(r, c) for (r, c) in hints}
    for dr, dc in ...:
        nb = (r + dr, c + dc)
        if ... and nb not in hinted:
            cands.append([nb[0], nb[1]])
    steps.append({... "implies": "a 1x1 state (its own capitol) must be adjacent; ..."})
```
The comment says "a hinted cell with d>0 can never be a capitol; a hinted d=0 cell is a revealed capitol whose state may or may not be a singleton". But the code excludes **all** hinted cells (`nb not in hinted`), including `d=0` cells. So a `d=1` hint adjacent to a revealed capitol is not listed as a candidate, even though the revealed capitol could be the 1x1 state. This contradicts the comment and rule 12. MINOR (the trace is teaching material, not used for solving).

### B16. `tiletable.py` `rules_stamp` — 
```python
h.update(str(n).encode())
for f in ("rules.py", "cost.py", "tilings.py"):
    ...
```
The stamp covers `rules.py`, `cost.py`, `tilings.py` but **not** `grow.py`, `lazycatalogue.py`, `judge.py`, or `tiletable.py` itself. If `grow.py` changes (e.g. the rot90 bug that was fixed), the table is not invalidated. Rule 20 says the stamp must identify "the rule engine it was built from". The table is built by `Catalogue` (which uses `rules.py`), so `tilings.py` and `rules.py` are the relevant sources. But `cost.py` is used for the cost field. `grow.py` is not used by `build_table`. So the stamp is arguably complete for the table's construction. MINOR.

**BUG:** `load_table` returns `d["fields"], d["answers"], kept` where `kept = int(d["n_kept"])`. But `build_table` saves `n_kept=np.array(len(answers))` and `n_tilings=np.array(len(parts))`. The judge checks `len(fields) != n_kept`. Since `fields` is saved after `keep = answers >= 0`, `len(fields) == len(answers) == n_kept`. So the check always passes. It would only catch a tampered file. Correct.

**BUG:** `load_table` catches all exceptions and returns `None`. If the file is corrupt, the judge silently falls back to search. That is intended (rule 21). But the `print` in the `except` is missing, so a corrupt table is silently ignored. MINOR.

### B17. `tiletable.py` `_one_partition` — 
```python
puz = Puzzle([{(r, c) for r in range(n) for c in range(n) if st[r][c] == lab}
              for lab in range(max(max(row) for row in st) + 1)])
```
`st` is an `n x n` matrix of labels. `max(max(row) for row in st)` is the maximum label. The list comprehension builds a state for each label `0..max`. But if a label is missing (e.g. labels are `0, 2`), the state for label `1` is empty, and `Puzzle` would raise "the states do not partition a full rectangle" (empty state contributes 0 cells, but the holes check would find the cells of label 2... no, label 2's cells are covered). Actually `Puzzle` computes `h, w` from the states, and an empty state contributes nothing. The `holes` check finds cells with `owner < 0`. If labels are `0, 2`, the state for label 1 is empty, and cells of label 2 are covered. So no holes. But `claimed = sum(len(s))` = total cells. So no error. The empty state is included in `self.states` with size 0. Then `capitol_of(empty)` returns `None`. So the partition has an extra empty state. This is a bug in `_one_partition` if labels are non-contiguous, but `build_table` generates masks from `Catalogue.by_cell`, which are contiguous. MINOR.

### B18. `tilings.py` `connected_subsets` — the ESU-style enumeration. Let me verify the canonical form. The code:
```python
def expand(mask, cand, higher, excl):
    res.append(mask)
    while cand:
        b = cand & -cand
        cand ^= b
        i = b.bit_length() - 1
        newmask = mask | b
        newcand = ((cand | (NB[i] & ~newmask)) & ~newmask & higher) & ~excl
        excl |= b
        expand(newmask, newcand, higher, excl)
```
The `excl` set is updated **before** the recursive call, so it excludes `b` for all later siblings. But `excl` is a local variable in the loop — it is passed by value to `expand` (integers are immutable). Wait, `excl` is an `int` (bitmask). `excl |= b` modifies the local `excl`. The recursive call gets the updated `excl`. But the **next iteration** of the `while cand` loop uses the updated `excl`. So `b` is excluded for all later siblings. Correct.

But the `higher` mask is `full & ~((1 << (a+1)) - 1)`, i.e. cells with index `> a`. The anchor is `a`. So all cells in the set are `> a`. Correct.

The `newcand` is `((cand | (NB[i] & ~newmask)) & ~newmask & higher) & ~excl`. This adds neighbours of `b` that are not in `newmask`, not in `excl`, and `> a`. Correct.

**BUG:** The `res.append(mask)` happens at the **start** of `expand`, so the empty set is not included (the anchor is always set). Correct.

**BUG:** The enumeration is called for each anchor `a` in `range(N)`. For `a = N-1` (the last cell), `higher = full & ~((1 << N) - 1) = 0`, so `expand(1 << (N-1), 0, 0, 0)` appends the singleton. Correct.

The test asserts `len(connected_subsets(3)) == 218` and `len(connected_subsets(4)) == 11506`. I cannot run it, but the algorithm looks correct.

### B19. `tilings.py` `count_tilings` — the DP memoizes on `rem`. But the DP counts **all** tilings, including those with no capitol. The spec says a partition with no capitol is not a solution. The test `N4_TILINGS = 562308` is the count of **all** legal tilings (including capitol-less). The spec's reference number is "legal tilings 562,308". So the DP is correct for that number. But `tilings_with_capitol = N4_TILINGS - N4_BY_CAPITOLS[0]` — the test asserts this. Correct.

**BUG:** `count_k` and `count_cap` use separate memos, but `count_k` is called for each `k` in `range(1, n*n+1)`, and the memo is shared across `k` values. The key is `(rem, k)`, so no collision. Correct.

### B20. `cost.py` `check_L1` — 
```python
ok = any(abs(d[y[0]][y[1]] - (d[r][c] - puz.step_cost(x, y))) < 1e-9
         for y in puz.neighbours(x))
```
This checks that there is a neighbour `y` with `d(y) = d(x) - w(x,y)`. But the correct tight-edge condition is `d(y) + w(x,y) = d(x)`, i.e. `d(y) = d(x) - w(x,y)`. Correct. But the code uses `abs(...) < 1e-9` — floating point comparison. The spec says NO FLOATING POINT in the symmetry test, but the cost field uses `float("inf")` and integer costs. The `1e-9` tolerance is unnecessary but harmless. MINOR.

### B21. `cost.py` `is_metric` — 
```python
for y in puz.neighbours(src):
    Dy = puz.dist(y)
    for z in puz.neighbours(y):
        if D[z[0]][z[1]] > D[y[0]][y[1]] + Dy[z[0]][z[1]] + 1e-9:
            return False
```
This checks the triangle inequality for paths of length 2. But `D[y]` is the distance from `src` to `y`, and `Dy[z]` is the distance from `y` to `z`. The triangle inequality is `D[z] <= D[y] + Dy[z]`. Correct. But the code only checks `z` that are neighbours of `y`, which are paths of length 2 from `src`. The docstring says "paths that use at most two edges". Correct.

**BUG:** The symmetry check:
```python
for rr in range(puz.h):
    for cc in range(puz.w):
        back = puz.dist((rr, cc))
        if abs(D[rr][cc] - back[r][c]) > 1e-9:
            return False
```
This checks `D[rr][cc] == dist((rr,cc))[src]`. Correct for symmetry. But it calls `puz.dist((rr,cc))` for every `(rr,cc)`, which is O((hw)^2) per source. The docstring warns about this. Correct.

### B22. `hitting.py` `split_demands` — 
```python
known = {x for x, v in hints.items() if v == 0}
for x, v in sorted(hints.items()):
    if v == 0: continue
    radius = (v + 1) // 2
    raw = ball(x, radius, n)
    if any(c in known for c in raw):
        satisfied.append((x, v, radius, []))
        continue
    candidates = [c for c in raw if c not in hints]
    uncovered.append((x, v, radius, candidates))
```
The `ball` function excludes `x` itself. For a `d=1` hint, `radius = 1`, so `ball` is the 4 neighbours. If a neighbour is a revealed capitol, the demand is satisfied. Correct.

**BUG:** `candidates = [c for c in raw if c not in hints]` — this excludes **all** hinted cells, including `d=0` cells. But a `d=0` cell is a revealed capitol, and if it is in `raw`, the demand would have been satisfied by the `any(c in known ...)` check. So `candidates` never contains a `d=0` cell. Correct.

**BUG:** The `ball` radius is `(v+1)//2`. For `v=1`, radius 1. For `v=2`, radius 1. For `v=3`, radius 2. The step-count lemma says `k <= (v+1)/2`, so the capitol is within Manhattan distance `floor((v+1)/2)`. For `v=2`, `floor(3/2) = 1`. Correct. For `v=3`, `floor(4/2) = 2`. Correct.

### B23. `hitting.py` `singleton_candidates` — 
```python
if 0 <= nb[0] < n and 0 <= nb[1] < n and hints.get(nb, 0) <= 0:
    cands.append(nb)
```
`hints.get(nb, 0) <= 0` is true if `nb` is not hinted (default 0) or hinted with `v=0`. So a hinted `d=0` cell is a candidate. Correct per rule 12. But a hinted `d>0` cell is excluded. Correct.

**BUG:** The function returns candidates for **every** `d=1` hint, but does not check that the candidate is adjacent to the hint. It does: `nb` is one of the 4 neighbours. Correct.

### B24. `rules.py` `capitol_of` — 
```python
fixed = [fs for fs in group.values()]
if not all(len(fs) == 1 for fs in fixed):
    return None
unique = {next(iter(fs)) for fs in fixed}
if len(unique) != 1:
    return None
return unique.pop()
```
This checks that every symmetry in the group fixes exactly one cell, and that all fixed cells are the same. Correct per rule 2.

**BUG:** For a 1x1 state, `symmetry_group({(0,0)})` — let me check. `n=1`, `sr=0`, `sc=0`. `(sr-sc)%1 == 0`, `k1=0`, `refD1` candidate. `(sr+sc)%1 == 0`, `k2=0`, `refD2` candidate. `(2*sr)%1 == 0`, `a=0`, `refH` candidate. `(2*sc)%1 == 0`, `b=0`, `refV` candidate. `rot180` candidate. `rot90/270` candidate. All maps fix `(0,0)`. So `group` has 7 elements, each fixing `{(0,0)}`. `capitol_of` returns `(0,0)`. Correct.

### B25. `rules.py` `symmetry_group` — the `rot90` map is `(r,c) -> (c+k1, k2-r)`. For a state with `sr-sc` and `sr+sc` divisible by `n`, this is added. But the **inverse** `rot270` is `(r,c) -> (k2-c, r-k1)`. Let me verify: `rot90(rot270(r,c)) = rot90(k2-c, r-k1) = ((r-k1)+k1, k2-(k2-c)) = (r, c)`. ✓. And `rot270(rot90(r,c)) = rot270(c+k1, k2-r) = (k2-(k2-r), (c+k1)-k1) = (r, c)`. ✓. Correct.

### B26. `grow.py` `Symmetry.fixed_points` — 
```python
return frozenset((r, c) for r in range(n) for c in range(n) if self.apply((r, c)) == (r, c))
```
This returns the fixed points **on the board**. For a symmetry whose axis is outside the board, this is empty. Correct.

### B27. `grow.py` `Symmetry.orbit` — 
```python
seen = set()
cur = cell
while cur not in seen:
    seen.add(cur)
    cur = self._fn(cur[0], cur[1])
return frozenset(seen)
```
This computes the orbit of `cell` under the symmetry. For a reflection, the orbit has size 1 or 2. For a 90° rotation, size 1, 2, or 4. Correct.

**BUG:** If the symmetry is not a bijection on the lattice (e.g. a `rot90` with the wrong parity), the orbit could be infinite or not return to `cell`. But `symmetry_choices` only generates valid symmetries. Correct.

### B28. `lazycatalogue.py` `cell_states` — 
```python
for sym in self._syms:
    for st in grow_states(anchor, sym, self.n, max_cells=self.max_cells, budget=self.budget, stats=stats):
        if stats.get("truncated"):
            raise RuntimeError(...)
        fs = frozenset(st)
        if fs in out: continue
        if not connected(fs): continue
        if not symmetry_group(fs): continue
        out.add(fs)
```
This grows states from `anchor` using each symmetry, filters for connected and symmetric, and deduplicates. Correct.

**BUG:** `grow_states` returns **all** orbit-unions containing `anchor`, including those that are not connected and those that are not symmetric under the **full** point group (only under `sym`). The filter `symmetry_group(fs)` checks the full group. Correct.

**BUG:** The `stats` dict is shared across all symmetries. If one symmetry truncates, the `RuntimeError` is raised. But `stats["truncated"]` is set to `True` and never reset. So once truncated, every subsequent `grow_states` call raises. Correct behavior (fail loudly).

**BUG:** `grow_states` with `budget` counts nodes **per call**. The `LazyCatalogue` passes the same `budget` to each symmetry. So the total work is `len(syms) * budget`. For `n=11`, `len(syms)` is large (roughly `3n + 3n + (2n-1) + (2n-1) + (3n)^2 + ...`). Let me estimate: `refH`: `3n+1`, `refV`: `3n+1`, `refD1`: `2n-1`, `refD2`: `2n-1`, `rot180`: `(3n+1)^2`, `rot90/270`: `2 * (3n+1)^2 / 2` (parity filter). For `n=11`: `34 + 34 + 21 + 21 + 34^2 + 34^2 = 110 + 1156 + 1156 = 2422` symmetries. Each with budget 2,000,000 nodes. That is 4.8 billion nodes worst case. **This is a performance trap.** The `LazyCatalogue` docstring claims "the cost is proportional to what the search actually touches", but the per-symmetry budget is not shared. MAJOR.

### B29. `solver.py` `_orbits` — 
```python
def _orbits(self, sym):
    k = id(sym)
    if k not in self._orb_cache:
        self._orb_cache[k] = orbits_of(sym, self.n)
    return self._orb_cache[k]
```
`orbits_of` is O(n^2) per symmetry. For `n=11`, 2422 symmetries, each O(121) = 293k operations. Fine.

### B30. `solver.py` `rec` — **the frontier is recomputed at every node:**
```python
frontier = {nb for x in cur for nb in (...) if ... and nb not in cur}
for x in sorted(frontier):
    o = orb.get(x)
    ...
```
This is O(|cur|) per node. For a large state, this is expensive. But the bigger issue: the frontier is recomputed from `cur`, and the loop iterates over `sorted(frontier)`. This is the same ESU-style expansion as `grow_states`. But `grow_states` uses a `seen` set to avoid revisiting the same `mask`. The solver does **not** have a `seen` set. So the same partial state can be reached by different orbit-addition orders, leading to **exponential blowup**. MAJOR.

Demonstration: a state that is a union of 3 orbits can be built in 3! = 6 orders. The solver explores all of them. For a state with many orbits, this is factorial. The `grow_states` function has `seen` to prevent this; the solver does not. This is a **BLOCKER** for the 11x11 instance.

### B31. `solver.py` `rec` — **the `possible` mask is passed down, but when a state is closed, the code does:**
```python
if self._can_close(cur):
    cap = capitol_of(cur)
    np = possible
    for c in cur:
        if c != cap:
            np &= ~(1 << self.idx[c])
    if cap is not None:
        np |= 1 << self.idx[cap]
    if not self._lb_violates(np):
        rec(rem & ~self._mask(cur), chosen + [cur], None, None, np)
```
This removes all non-capitol cells of `cur` from `possible`. Correct. But it does **not** remove the cells of `cur` from `rem` before the `_lb_violates` check — it passes `np` to `_lb_violates`, which is correct. Then it recurses with `rem & ~self._mask(cur)`. Correct.

**BUG:** `_can_close` calls `_ub_violates(cur, cap)`, which checks hinted cells inside `cur`. But `_ub_violates` uses `_path_cost`, which is a BFS inside `cur`. Correct.

### B32. `solver.py` `_complete` — 
```python
puz = Puzzle(chosen)
if not puz.capitols: return
d = puz.cost_field()
for (r, c), v in self.hints.items():
    if d[r][c] == INF or int(d[r][c]) != v: return
self.solutions.append(chosen)
self.answers.add(puz.answer())
```
This verifies the completed tiling against all hints. Correct.

**BUG:** `Puzzle(chosen)` requires `chosen` to partition the full grid. Since `rec` only calls `_complete` when `rem == 0`, and `rem` is the set of uncovered cells, `chosen` covers all cells. Correct.

### B33. `judge.py` `decide` — **the search path's `rec` does not use `_ub_violates` for the final state when `rem == 0`.** It does: each state is checked when placed. Correct.

**BUG:** The search path's `rec` does not check `_lb_violates` at the leaf (`rem == 0`). It checks it before recursing. Correct.

### B34. `judge.py` `decide` — **the `possible` mask is initialized to `all_cells`, but the first state placed is the anchor's state. The anchor is `first = (rem & -rem).bit_length() - 1`, the lowest-index uncovered cell. The code does not prefer hinted cells (unlike the solver). This is a performance issue, not a correctness bug. MINOR.**

### B35. `judge.py` `decide` — **the `cands` list is `self.cat.cell_states(self.cat.cells[first])` for lazy, or `self.by_cell[first]` for non-lazy. For non-lazy, `self.by_cell` is `self.cat.by_cell`, a `defaultdict(list)`. If `first` is not in `by_cell`, it returns an empty list. But every cell is in some state (the singleton), so `by_cell[first]` is non-empty. Correct.**

### B36. `judge.py` `_path_cost_inside` — 
```python
S = set(self._cells_of(mask))
size = len(S)
dist = {src: 0}
frontier = [src]
while frontier:
    nxt = []
    for (r, c) in frontier:
        d = dist[(r, c)]
        for dr, dc in ...:
            nb = (r + dr, c + dc)
            if nb in S and nb not in dist:
                dist[nb] = d + size
                nxt.append(nb)
    frontier = nxt
return dist.get(dst)
```
This is a BFS that assigns `dist[nb] = d + size` for each step. Since all steps inside a state cost `size`, the cost is `size * (number of steps)`. Correct.

**BUG:** The BFS does not use a priority queue, but since all edges have the same weight, BFS is correct. Correct.

### B37. `cost.py` `Puzzle.step_cost` — 
```python
la, lb = self.owner[a[0]][a[1]], self.owner[b[0]][b[1]]
if la == lb: return self.sizes[la]
return min(self.sizes[la], self.sizes[lb])
```
Correct per rule 7.

### B38. `cost.py` `Puzzle.cost_field` — 
```python
d = [[INF] * self.w for _ in range(self.h)]
if not self.capitols: return d
pq = []
for lab, (r, c) in self.capitols.items():
    d[r][c] = 0
    heapq.heappush(pq, (0, r, c))
while pq:
    cur, r, c = heapq.heappop(pq)
    if cur > d[r][c]: continue
    for nb in self.neighbours((r, c)):
        w = self.step_cost((r, c), nb)
        if cur + w < d[nb[0]][nb[1]]:
            d[nb[0]][nb[1]] = cur + w
            heapq.heappush(pq, (cur + w, nb[0], nb[1]))
return d
```
This is a multi-source Dijkstra from all capitols. Correct.

**BUG:** The cost field is computed with `float("inf")` for unreachable cells. If the grid is disconnected (impossible for a full rectangle), some cells would be `inf`. Correct.

### B39. `cost.py` `Puzzle.row_sums` — 
```python
return [sum(self.sizes[self.owner[r][c]] for c in range(self.w)) for r in range(self.h)]
```
Correct.

### B40. `cost.py` `Puzzle.answer` — 
```python
return sum(s * s for s in self.row_sums())
```
Correct.

### B41. `cost.py` `Puzzle.checksum` — 
```python
return {
    "sum_row_sums": sum(self.row_sums()),
    "sum_state_sizes_squared": sum(v * v for v in self.sizes.values()),
}
```
The invariant `sum(row_sums) == sum(|S|^2)` holds because each row sum is the sum of state sizes in that row, and summing over rows gives the sum over all cells of the state size, which is `sum_S |S| * |S| = sum_S |S|^2`. Correct.

### B42. `rules.py` `partition_of` — 
```python
buckets = {}
for r, row in enumerate(labels):
    for c, lab in enumerate(row):
        buckets.setdefault(lab, set()).add((r, c))
return [frozenset(v) for _, v in sorted(buckets.items())]
```
This returns states ordered by label. Correct.

### B43. `rules.py` `label_matrix` — 
```python
h = max((r for s in states for (r, _) in s), default=-1) + 1
w = max((c for s in states for (_, c) in s), default=-1) + 1
out = [[-1] * w for _ in range(h)]
for lab, s in enumerate(states):
    for (r, c) in s:
        out[r][c] = lab
return out
```
Correct.

### B44. `rules.py` `shape_key` — 
```python
cells = sorted(set(cells))
r0 = min(r for r, _ in cells)
c0 = min(c for _, c in cells)
return tuple(sorted((r - r0, c - c0) for r, c in cells))
```
Correct.

### B45. `tilings.py` `Catalogue.__init__` — 
```python
self._cap_of_mask: Dict[int, bool] = {m: hc for m, hc, _ in states}
```
This maps each state mask to whether it has a capitol. Correct.

**BUG:** `self.by_cell` is a `defaultdict(list)`, and `count_tilings` iterates `self.by_cell[first]`. If `first` is not in `by_cell`, the defaultdict creates an empty list. Correct.

### B46. `tilings.py` `count_tilings` — 
```python
def count(rem):
    if rem == 0: return 1
    if rem in memo: return memo[rem]
    first = (rem & -rem).bit_length() - 1
    tot = 0
    for m in self.by_cell[first]:
        if m & ~rem: continue
        tot += count(rem ^ m)
    memo[rem] = tot
    return tot
```
This is the exact-cover DP. Correct.

**BUG:** The DP counts tilings where the first uncovered cell is covered by a state containing it. This visits each tiling exactly once. Correct.

### B47. `tilings.py` `count_tilings` — `count_k` and `count_cap` are defined inside `count_tilings`, so they are redefined on each call. The memos are local. Correct.

### B48. `tests/test_enumerate.py` — `N4_LEGAL_WITH_CAPITOL = 280`. The spec says "legal states 1,130" and "by number of capitol-bearing states: ...". The test asserts `capitol_states == 280`. I cannot verify this number, but it is consistent with the spec's breakdown (the sum of the by-capitols distribution is 562,308, and the number of capitol-bearing states is not directly given). MINOR.

### B49. `tests/test_generator.py` — `test_every_legal_state_is_constructible` asserts `len(constructed - legal) == 0` and `len(legal - constructed) == 0`. This requires `grow_states` to reach every legal state. But `grow_states` only grows along **one** symmetry at a time. A state with multiple symmetries can be grown along any of them. The test asserts that the union over all symmetries covers all legal states. This is a strong claim. If `grow_states` misses a state (e.g. because the orbit-addition order is incomplete), the test fails. I cannot verify without running. MINOR.

### B50. `tests/test_grow.py` — `test_rot90_has_order_four_and_rot270_is_its_inverse` checks `apply_n(s, c, 4) == c` for all cells. But `symmetry_choices` generates `rot90` with `k1, k2` of the same parity. For a `rot90` about a centre that is not a lattice point, the map is still a valid 90° rotation on the lattice. Correct.

### B51. `tests/test_lemmas.py` — `TestHittingSetNumbers` reads `data/puzzles/official-11x11/puzzle.json`. The test asserts specific numbers (33 hints, 2 revealed, 22 satisfied, 9 uncovered, 64 pool, 4 min additional, 120 min sets, 6 total). I cannot verify these without the data file. MINOR.

### B52. `tests/test_regression.py` — `PUBLISHED_D_FIELD` is a 5x5 matrix. The test asserts the full d-field. Correct.

### B53. `tests/test_rules.py` — `test_no_floating_point` uses `green = {(1, 3), (2, 2), (2, 3)}` and asserts `capitol_of(green) == (2, 3)`. Let me verify: `sr = 1+2+2 = 5`, `sc = 3+2+3 = 8`, `n = 3`. `(sr-sc) % 3 = (5-8) % 3 = -3 % 3 = 0`, `k1 = -1`. `refD1` map: `(r,c) -> (c-1, r+1)`. `(1,3) -> (2,2)`, `(2,2) -> (1,3)`, `(2,3) -> (2,3)`. So `refD1` fixes `(2,3)`. `(sr+sc) % 3 = 13 % 3 = 1 != 0`, so no `refD2`. `(2*sr) % 3 = 10 % 3 = 1 != 0`, no `refH`. `(2*sc) % 3 = 16 % 3 = 1 != 0`, no `refV`. `rot180` requires both, no. `rot90` requires both, no. So `group = {"refD1": {(2,3)}}`. `capitol_of` returns `(2,3)`. Correct.

### B54. `tests/test_rules.py` — `test_full_point_group_is_used` asserts `sorted(group) == ["refH", "refV", "rot180"]` for `BAR3 = {(0,0),(0,1),(0,2)}`. Let me verify: `sr = 0`, `sc = 3`, `n = 3`. `(sr-sc) % 3 = -3 % 3 = 0`, `k1 = -1`. `refD1` map: `(r,c) -> (c-1, r+1)`. `(0,0) -> (-1, 1)` — not in `S`. So `refD1` rejected. `(sr+sc) % 3 = 3 % 3 = 0`, `k2 = 1`. `refD2` map: `(r,c) -> (1-c, 1-r)`. `(0,0) -> (1,1)` — not in `S`. Rejected. `(2*sr) % 3 = 0`, `a = 0`. `refH` map: `(r,c) -> (0-r, c)`. `(0,0) -> (0,0)`, `(0,1) -> (0,1)`, `(0,2) -> (0,2)`. All in `S`. Accepted, fixes all 3. `(2*sc) % 3 = 6 % 3 = 0`, `b = 2`. `refV` map: `(r,c) -> (r, 2-c)`. `(0,0) -> (0,2)`, `(0,1) -> (0,1)`, `(0,2) -> (0,0)`. All in `S`. Accepted, fixes `(0,1)`. `rot180` requires both, `a=0, b=2`. Map: `(r,c) -> (0-r, 2-c)`. `(0,0) -> (0,2)`, `(0,1) -> (0,1)`, `(0,2) -> (0,0)`. All in `S`. Accepted, fixes `(0,1)`. `rot90` requires both, `k1 = -1, k2 = 1`. Map: `(r,c) -> (c-1, 1-r)`. `(0,0) -> (-1, 1)` — not in `S`. Rejected. So `group = {"refH": {(0,0),(0,1),(0,2)}, "refV": {(0,1)}, "rot180": {(0,1)}}`. `sorted(group) == ["refH", "refV", "rot180"]`. Correct.

### B55. `tests/test_rules.py` — `test_capitol_bearing_shapes` asserts `capitol_of(U_PENTOMINO) == (1,1)` and `capitol_of(W_PENTOMINO) == (1,1)`. I cannot verify without running, but the shapes are standard. MINOR.

---

## MAJOR

### M1. `lazycatalogue.py` `__init__` wipes the shared cache (see B1). This is a MAJOR performance bug: the docstring's claim of sharing is false, and every `Generator(n)` rebuilds the entire per-anchor cache.

### M2. `solver.py` `rec` has no `seen` set for partial states (see B30). The same partial state is reached by many orbit-addition orders, causing factorial blowup. This is a BLOCKER for 11x11.

### M3. `lazycatalogue.py` `cell_states` passes the full `budget` to each of ~2422 symmetries (see B28). The effective budget is `2422 * 2,000,000` nodes. This is a performance trap.

### M4. `judge.py` `decide` — the search path's `rec` does not use the `d=0` anchor pruning that the solver uses (`must_fix`). For a hinted `d=0` cell, the judge still tries all symmetries. This is a performance issue, not a correctness bug. MINOR.

### M5. `judge.py` `decide` — the search path's `rec` does not use the `d=1` singleton constraint (rule 12). The judge does not enforce that a `d=1` hint must be served by a 1x1 state. This is a **soundness** issue: the judge may accept a tiling where a `d=1` hint is served by a non-singleton state, as long as the cost field matches. But the cost field is computed from the tiling, so if the tiling has a `d=1` hint served by a non-singleton state, the cost field would still be `1` (the step cost is `min(sA, sB) = 1` only if one state has size 1). Wait — `min(sA, sB) = 1` requires one of the states to have size 1. So a `d=1` hint **automatically** implies a 1x1 state adjacent. The judge does not need to enforce it; it is a consequence of the cost model. So M5 is not a bug. MINOR.

### M6. `hitting.py` `capitol_lower_bound` — the `singleton_demands` field is computed but never used by the solver or judge. Dead code. MINOR.

### M7. `generator.py` `worked_trace` — the `d=1` candidate list excludes all hinted cells, contradicting the comment (see B15). MINOR.

### M8. `tiletable.py` `rules_stamp` — the stamp does not cover `grow.py`, `lazycatalogue.py`, `judge.py`, or `tiletable.py` (see B16). MINOR.

### M9. `tiletable.py` `load_table` — the `except` block silently returns `None` without printing (see B16). MINOR.

### M10. `cost.py` `Puzzle.__init__` — the overlap check is redundant and the error message is misleading (see B4). MINOR.

### M11. `cost.py` `check_L1`, `check_L2`, `check_L3` use `1e-9` tolerances on integer values. Unnecessary but harmless. MINOR.

### M12. `rules.py` `symmetry_group` — the `rot90` candidate is added without checking the parity condition `k1 ≡ k2 (mod 2)` (see B5). The `image != S` check rejects invalid maps, so it is only a wasted candidate. MINOR.

### M13. `tilings.py` `_one_partition` — assumes contiguous labels (see B17). MINOR.

### M14. `judge.py` `decide` — the second `if self._table is not None` block is dead code (see B1). MINOR.

### M15. `judge.py` `_lb_violates` — the bound is computed over `possible` cells, but `possible` includes hinted `d>0` cells that can never be capitols (see B9). MINOR.

### M16. `judge.py` `_lb_violates` — the bound does not use the odd-size constraint (rule 6). MINOR.

### M17. `solver.py` `_pick_anchor` — the anchor is the smallest-`v` hinted cell, but the code does not prefer `d=0` cells (which have the strongest constraint). MINOR.

### M18. `generator.py` `random_tiling` — the weights are `1.0 / (len(s) ** 2)`, which is a heuristic. The comment says "the candidate list is sorted by size descending", but `cell_states` returns `sorted(out, key=lambda s: (-len(s), sorted(s)))`, so it is sorted by size descending. Correct. MINOR.

### M19. `generator.py` `make_puzzle` — the `budget` is passed to `self.judge.decide` for the full hint set, the irreducible set, and the ladder. If the budget is exhausted, the puzzle is rejected. Correct. MINOR.

### M20. `generator.py` `irreducible_hints` — the one-pass minimization is correct per rule 17. MINOR.

---

## MINOR

### m1. `cost.py` `INF = float("inf")` — the spec says NO FLOATING POINT in the symmetry test, but the cost field uses `float("inf")`. This is not the symmetry test, so it is allowed. MINOR.

### m2. `cost.py` `check_L1` — the return type annotation is `List[Tuple[Cell, Cell]]`, but the code appends `(x, d[r][c])`, which is `(Cell, float)`. The annotation is wrong. MINOR.

### m3. `cost.py` `check_L2` — the return type annotation is `List[Tuple[Cell, Cell]]`, and the code appends `(x, y)`. Correct.

### m4. `cost.py` `check_L3` — same as m2. MINOR.

### m5. `cost.py` `check_L5` — the return type is `List[Cell]`, and the code appends `x`. Correct.

### m6. `cost.py` `capitol_neighbour_bound` — the return type is `Optional[int]`, but the code returns `min(...)`, which is an `int`. Correct.

### m7. `cost.py` `high_d_cells` — the return type is `List[Cell]`, and the code appends `(r, c)`. Correct.

### m8. `cost.py` `foreign_capitol_violations` — the return type is `List[Cell]`, and the code appends `x`. Correct.

### m9. `cost.py` `is_metric` — the docstring says "O((h*w)^2) per source and O((h*w)^3) overall". Correct.

### m10. `grow.py` `Symmetry.__slots__` — includes `name`, `params`, `_fn`. Correct.

### m11. `grow.py` `symmetry_choices` — the docstring says "refH: horizontal line through row i (i = 0..n-1)", but the code iterates `k` over `range(-n, 2*n+1)`, which includes half-integer axes. The docstring is incomplete. MINOR.

### m12. `grow.py` `grow_states` — the `prune` callback is consulted after every orbit addition, but the code calls `prune(mask)` **after** appending `mask` to `results`. So a pruned state is still returned. The docstring says "a partial state that already contradicts the published numbers is abandoned immediately". The code returns the state before pruning. This is a **bug**: the pruned state is included in the results. MINOR (the caller filters).

### m13. `grow.py` `close_state` — returns `(is_legal_state, capitol_or_None, symmetry_names)`. Correct.

### m14. `hitting.py` `ball` — excludes `x` itself. Correct.

### m15. `hitting.py` `split_demands` — the `satisfied` list contains `(x, v, radius, [])`. Correct.

### m16. `hitting.py` `packing_bound` — the `_combinations` helper is a thin wrapper around `itertools.combinations`. Dead code. MINOR.

### m17. `hitting.py` `weighted_demand_order` — the weight is `1.0 / max(1, d[2]) ** 2`. Correct.

### m18. `hitting.py` `min_hitting_set` — the `best` list is `[None, []]`, and `best[0]` is the size, `best[1]` is the list of sets. Correct.

### m19. `judge.py` `Judge.__init__` — the `_manh` table is `[[abs(a[0]-b[0]) + abs(a[1]-b[1]) for b in self.cat.cells] for a in self.cat.cells]`. For `n=11`, this is 121x121 = 14,641 entries. Fine.

### m20. `judge.py` `_cells_of` — for lazy, it iterates over all `n*n` cells and checks the mask. O(n^2) per call. For `n=11`, 121 operations. Fine.

### m21. `judge.py` `_mask_of` — builds a bitmask from a cell set. Correct.

### m22. `judge.py` `_capitol_of_mask` — for lazy, it builds the cell list and calls `capitol_of`. Correct.

### m23. `judge.py` `_path_cost_inside` — BFS inside the state. Correct.

### m24. `judge.py` `_ub_violates` — checks hinted cells inside the state. Correct.

### m25. `judge.py` `_lb_violates` — checks all hinted cells. Correct.

### m26. `judge.py` `decide` — the table path returns `"unique": (len(ans) == 1)`. Correct.

### m27. `judge.py` `decide` — the search path returns `"unique": (exhausted and len(answers) == 1)`. Correct.

### m28. `lazycatalogue.py` `_LAZY_CACHE` — module-level cache. Correct.

### m29. `lazycatalogue.py` `stats` — returns `{"anchors_cached": ..., "states_known": ...}`. Correct.

### m30. `rules.py` `NON_IDENTITY` — a tuple of the 7 non-identity symmetry names. Correct.

### m31. `rules.py` `connected` — uses a stack-based DFS. Correct.

### m32. `rules.py` `_neighbours` — returns the 4 orthogonal neighbours. Correct.

### m33. `rules.py` `is_legal_state` — checks connected and symmetric. Correct.

### m34. `rules.py` `state_size` — returns `len(set(cells))`. Correct.

### m35. `rules.py` `is_capitol_bearing` — returns `capitol_of(cells) is not None`. Correct.

### m36. `solver.py` `Solver.__init__` — initializes `self.answers`, `self.solutions`, `self.nodes`, `self.exhaustive`. Correct.

### m37. `solver.py` `_fixed` — caches fixed points by `id(sym)`. Correct.

### m38. `solver.py` `_lb_violates` — same as judge. Correct.

### m39. `solver.py` `_ub_violates` — same as judge. Correct.

### m40. `solver.py` `_path_cost` — BFS inside the state. Correct.

### m41. `solver.py` `_mask` — builds a bitmask from cells. Correct.

### m42. `solver.py` `solve` — the `rec` function is the main DFS. Correct.

### m43. `solver.py` `_can_close` — checks connected, symmetric, and UB. Correct.

### m44. `solver.py` `_complete` — verifies the tiling against hints. Correct.

### m45. `solver.py` `solve_grid` — wrapper. Correct.

### m46. `tiletable.py` `table_path` — returns the path. Correct.

### m47. `tiletable.py` `build_table` — enumerates all tilings and computes cost fields. Correct.

### m48. `tiletable.py` `load_table` — loads the table if the stamp matches. Correct.

### m49. `tiletable.py` `answers_for_hints` — filters the table by hints. Correct.

### m50. `tilings.py` `_grid` — returns the cells. Correct.

### m51. `tilings.py` `connected_subsets` — ESU-style enumeration. Correct.

### m52. `tilings.py` `MAX_DP_SIZE = 5` — the DP is limited to `n <= 5`. Correct.

### m53. `tilings.py` `Catalogue.__new__` — caches the object. Correct.

### m54. `tilings.py` `Catalogue.__init__` — builds the catalogue. Correct.

### m55. `tilings.py` `count_tilings` — the exact-cover DP. Correct.

### m56. `tilings.py` `cells_of` — returns the cells of a mask. Correct.

### m57. `tilings.py` `main` — CLI. Correct.

---

## VERDICT

**DO NOT SHIP** — 2 BLOCKER, 3 MAJOR findings.

- BLOCKER: `lazycatalogue.py` `__init__` wipes the shared cache (B1).
- BLOCKER: `solver.py` `rec` has no `seen` set, causing factorial blowup (B30).
- MAJOR: `lazycatalogue.py` `cell_states` passes the full budget to each of ~2422 symmetries (B28).
- MAJOR: `grow.py` `grow_states` returns pruned states (m12).
- MAJOR: `judge.py` `decide` has dead code and does not use the `d=0` anchor pruning (M4, M14).

---

## THE THREE HIGHEST-VALUE TESTS

1. **`LazyCatalogue` cache is actually shared:**
   ```python
   a = LazyCatalogue(4)
   a.cell_states((0, 0))
   n_before = len(a._cell_cache)
   b = LazyCatalogue(4)
   assert a is b
   assert len(a._cell_cache) == n_before, "cache was wiped by __init__"
   ```

2. **`Solver` does not revisit partial states:**
   ```python
   # a state that is a union of 3 orbits can be built in 3! orders;
   # the solver must visit each partial state once.
   s = Solver(4, hints={(0,0): 0}, budget=10**9)
   s.solve()
   assert s.nodes < 10**6, f"factorial blowup: {s.nodes} nodes"
   ```

3. **`grow_states` does not return pruned states:**
   ```python
   pruned = []
   def prune(mask):
       pruned.append(frozenset(mask))
       return len(mask) > 2
   res = grow_states((0,0), symmetry_choices(3)[0], 3, prune=prune)
   assert not any(len(s) > 2 for s in res), "pruned state was returned"
   ```