# 09-deepseek-code-review — CODE REVIEW

- model: `deepseek/deepseek-v4.1-flash`
- finish_reason: stop
- usage: {"prompt_tokens": 32741, "completion_tokens": 10417, "total_tokens": 43158, "cost": 0.0223227, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0223227, "upstream_inference_prompt_cost": 0.0098223, "upstream_inference_completions_cost": 0.0125004}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 31083 reasoning_chars: 0

---

## REVIEW

I read the code against the spec. Findings below, ordered by severity. I did not restate correct behaviour.

---

## BLOCKER

### B1. `rules.symmetry_group` — the 90/270 candidate is built from the wrong centre, so every rot90/rot270 symmetry is missed (or mis-detected)
**File:** `src/rules.py`, the `ROT_90`/`ROT_270` block.

The code computes `k1 = (sr-sc)//n`, `k2 = (sr+sc)//n` and then maps `(r,c) -> (c+k1, k2-r)`. That map is a 90° rotation about the centre `((k2-k1)/2, (k2+k1)/2)` — i.e. about `(sc/n, sr/n)`, the centroid. But the *divisibility* conditions it gates on are `(sr-sc)%n==0 and (sr+sc)%n==0`, which are the conditions for the centroid to be a *half-integer* point of the right parity, not for the map to be a symmetry of the *cell set*.

Concretely, the map is only a candidate when the centroid is `(a/2, b/2)` with `a,b` of the same parity. The code's `k1,k2` are `(sr-sc)/n` and `(sr+sc)/n`; the centre it actually rotates about is `(sc/n, sr/n)`. These coincide only when `sr/n` and `sc/n` are both half-integers of the same parity — which is exactly what the two congruences test. So the *centre* is right, but the *map* is wrong: a 90° rotation about `(sc/n, sr/n)` is `(r,c) -> (sc/n + (c - sr/n), sr/n - (r - sc/n)) = (c + (sc-sr)/n, (sr+sc)/n - r)`. The code has `(c + (sr-sc)/n, (sr+sc)/n - r)` — the sign of the first component is flipped.

**Demonstration.** Take the 3-cell state `{(0,0),(1,1),(2,2)}` (a diagonal bar). Its centroid is `(1,1)`, an integer point, so a 90° rotation about it is a lattice symmetry of the *lattice* but not of this set (the set is a diagonal, not a cross). The code's `k1 = (3-3)/3 = 0`, `k2 = (3+3)/3 = 2`, map `(r,c)->(c, 2-r)`. Applied to `(0,0)` gives `(0,2)`, not in the set — correctly rejected. Now take the *cross* `{(0,1),(1,0),(1,1),(1,2),(2,1)}` (X-pentomino). Centroid `(1,1)`, `k1=0`, `k2=2`, map `(r,c)->(c,2-r)`. `(0,1)->(1,2)` ✓, `(1,0)->(0,1)` ✓, `(1,1)->(1,1)` ✓, `(1,2)->(2,1)` ✓, `(2,1)->(1,0)` ✓. This one happens to work because the set is symmetric under both the correct and the flipped map. The bug is invisible on symmetric sets and only shows on sets where the two maps differ — i.e. sets whose centroid is *not* on the diagonal `r=c`. Example: `{(0,0),(0,1),(1,1),(1,2),(2,2)}` (a staircase). Centroid `(4/5, 6/5)`, not a half-integer, so no candidate is generated — fine. The real failure is a set with centroid `(a/2,b/2)`, `a≠b`, e.g. `{(0,0),(0,1),(1,0),(1,1),(2,0),(2,1)}` (a 3×2 rectangle). Centroid `(1, 0.5)`, `sr=6, sc=3, n=6`: `(sr-sc)%6=3≠0`, so no rot90 candidate — correct, a 3×2 rectangle has no 90° symmetry. I could not construct a set where the flipped map *accepts* a non-symmetric set, because the acceptance test `image == S` is exact. **So the sign flip is latent, not exploitable** — but it is still wrong, and it will bite the moment anyone adds a rot90 candidate whose centre is off-diagonal. Downgrade to MAJOR (see M1).

**Fix:** `lambda r, c, h=(sc-sr)//n, g=(sr+sc)//n: (c + h, g - r)` and `lambda r, c, h=(sc-sr)//n, g=(sr+sc)//n: (g - c, r - h)`.

---

### B2. `judge.decide` — the LB prune is unsound: it uses Manhattan distance as a *lower* bound on cost, but cost is `min(sizeA,sizeB) ≥ 1` per step, so Manhattan is a lower bound only if every step costs ≥ 1 — which is true — but the code compares `best > v` where `best` is the *minimum Manhattan distance to any possible capitol*, and `v` is the published `d(x)`. Since `d(x) ≥ Manhattan(x, nearest capitol)` (each step costs ≥ 1), we have `Manhattan ≤ d`, so `Manhattan > v` implies `d > v` — that direction is sound. **But** the code computes `best` over `possible`, and `possible` is updated as `possible & ~mask_m | keep`. The `keep` set is the capitol of the *newly placed* state. A state with **no capitol** contributes nothing to `keep`, so its cells are removed from `possible` — correct. A state **with** a capitol contributes only that one cell — correct. So `possible` is a superset of the true capitol set. Then `best = min over possible` is a *lower* bound on the true nearest-capitol Manhattan distance. `best > v` ⟹ true distance > v ⟹ `d(x) > v` ⟹ prune. **This is sound.** I retract the concern; the LB is correct.

However: **the UB prune is unsound in the opposite direction.** `_ub_violates` checks `cost < v` where `cost = _path_cost_inside(mask, (r,c), cap)` is the cost of the *cheapest path inside the state* from the hinted cell to the state's capitol. If `cost < v`, the code prunes. But `d(x)` is the least cost to **any** capitol, so `d(x) ≤ cost`. If `cost < v`, then `d(x) ≤ cost < v`, so the hint `v` is violated — **sound**. OK, both prunes are sound. I retract B2 entirely.

---

### B3. `hitting.split_demands` — `ball` excludes `x` itself, but a `d=0` hint is a capitol and a `d>0` hint can never be a capitol, so excluding `x` is correct; **but** the radius is `(v+1)//2` and the spec (rule 8) says the nearest capitol is within `floor((v+1)/2)`. For `v=1`, radius `=1`, ball is the 4 neighbours — correct. For `v=2`, radius `=1`, ball is the 4 neighbours — but a `d=2` cell could have its capitol 2 steps away (e.g. `d=2` via two cost-1 steps through a 1×1 state). `floor((2+1)/2)=1`, so the ball is radius 1. Is that right? The step-count lemma: `v ≥ 2(k-1)+1` where `k` is the number of steps. For `v=2`: `2 ≥ 2(k-1)+1` ⟹ `k ≤ 1.5` ⟹ `k ≤ 1`. So the capitol is 1 step away. Radius 1 is correct. **No bug.**

---

### B4. `judge.decide` — `_lb_violates` is called with `new_possible` computed as `possible & ~mask_m | keep`, but operator precedence in Python makes this `(possible & ~mask_m) | keep`. That is the intended grouping. **No bug.**

---

### B5. `generator.make_puzzle` — `all_hints` is built from `d` which is `float` (`cost_field` returns `List[List[float]]`), then `int(d[r][c])`. If `d` contains `inf`, the earlier check `any(v == float("inf") ...)` catches it. **No bug.**

---

### B6. `tiletable.load_table` — `got = str(d["stamp"])`. `d["stamp"]` is a 0-d numpy array of a string. `str(np.array('abc'))` gives `'abc'`, but `str(np.array(['abc']))` gives `"['abc']"`. Since `np.savez` stores `stamp=np.array(rules_stamp(n))` (0-d), `str` gives the bare string. **But** `rules_stamp` returns a 16-char hex string, and `np.array("abc")` creates a `<U3` array; `str` of a 0-d `<U16` array is the string itself. So the comparison works. **However**, `load_table` returns `d["fields"], d["answers"], int(d["n_tilings"])` — a **3-tuple** — but `judge.decide` does `fields, answers = self._table`, unpacking **2** values. This raises `ValueError: too many values to unpack`. **BLOCKER.**

**Demonstration:**
```python
# tiletable.load_table returns (fields, answers, n_tilings)
# judge.decide:
fields, answers = self._table   # ValueError: too many values to unpack (expected 2)
```
**Fix:** `fields, answers, _ = self._table` in `judge.decide`, or return a 2-tuple from `load_table`.

---

### B7. `judge.decide` — when `self._table is not None`, it returns `"exhaustive": True` unconditionally. Rule 20 says the table must be ignored when the stamp does not match, and `load_table` does that. But rule 20 also says "its row count must be cross-checked". `load_table` reads `n_tilings` but never checks it against `len(fields)`. A truncated table would still report `exhaustive: True`. **MAJOR** (see M2).

---

### B8. `grow.grow_states` — the `expand` function appends `mask` to `results` **before** checking connectivity, and `close_state` is never called inside `grow_states`. So `grow_states` returns disconnected sets. `LazyCatalogue.cell_states` filters with `connected(fs)`, and `Generator._add_constructible_states` filters with `connected(st)`. But `judge.decide` calls `self.cat.cell_states(...)` which for `lazy=True` is `LazyCatalogue.cell_states` (filtered) and for `lazy=False` is `self.by_cell[first]` (from `Catalogue`, which is built from `connected_subsets` — already connected). So the filter is applied. **No bug**, but `grow_states`'s docstring says "All CONNECTED orbit-unions" — misleading. MINOR.

---

### B9. `grow.grow_states` — the `seen` set is local to each call, and `expand` is recursive. The `frontier` is recomputed from `newmask`, but `newfront = {y for y in frontier if y != x}` then adds neighbours of `newmask`. This is correct for canonical enumeration **only if** the frontier is always a superset of the true boundary. It is: `newfront` starts from the old frontier minus `x`, then adds all neighbours of `newmask` not in `newmask`. So `newfront` ⊇ boundary. **But** the enumeration is **not canonical**: the same set can be reached by adding orbits in different orders, and `seen` catches duplicates *within one call*, but the order of `sorted(frontier)` is deterministic, so each set is generated once per call. Across different `sym` values, the same set is generated multiple times — `LazyCatalogue` dedupes with `out: set`. **No bug.**

---

### B10. `tilings.connected_subsets` — the `excl` parameter is passed by value (int), and `excl |= b` mutates the local copy. The recursion passes `excl` to `expand`, so each sibling gets the accumulated `excl`. This is the ESU algorithm. **But** the initial call is `expand(1 << a, NB[a] & higher, higher, 0)` — `excl=0`. The first cell `a` is not in `excl`, so it could be re-added? No: `newcand` is masked with `& ~newmask`, and `a` is in `newmask`. **No bug.** The test `test_counts` checks 3×3=218 and 4×4=11506, which match the spec. **No bug.**

---

### B11. `tilings.Catalogue.__new__` / `__init__` — the cache is keyed by `n` only. `Catalogue(4)` and `Catalogue(4)` return the same object. But `__init__` checks `getattr(self, "_built", False) and getattr(self, "n", None) == n`. If `Catalogue(4)` is called, `_built=True`, `n=4`, returns early. If `Catalogue(5)` is called, `_built=True` but `n=4≠5`, so it rebuilds — **but it rebuilds the same cached object**, overwriting `n=4`'s data with `n=5`'s. Then `Catalogue(4)` returns the object with `n=5`. **BLOCKER.**

**Demonstration:**
```python
c4 = Catalogue(4)   # builds 4x4
c5 = Catalogue(5)   # __new__ returns c4 (cached under key 4? no — key is 5)
```
Wait — `__new__` checks `if n in _CATALOGUE_CACHE: return _CATALOGUE_CACHE[n]`. For `n=5`, `5 not in cache`, so `super().__new__(cls)` creates a **new** object. Then `__init__` runs on the new object, `_built` is False, builds 5×5, caches under key 5. So `Catalogue(4)` and `Catalogue(5)` are different objects. **No bug.** The `_built` check is for the case where `__init__` is called twice on the same object (e.g. `Catalogue(4)` then `Catalogue(4)` — but `__new__` returns the cached object, and `__init__` is called again, sees `_built=True, n=4`, returns early). **No bug.**

---

### B12. `cost.Puzzle.__init__` — `self.h = max((r for s in self.states for (r, _) in s), default=-1) + 1`. For an empty `states`, `h=0, w=0`. `owner` is `[]`. `holes` is `[]`. `capitols` is `{}`. `cost_field` returns `[]`. `row_sums` returns `[]`. `answer` returns `0`. **No crash.** But `Puzzle([])` is a degenerate case; the spec says a partition with no capitol is not a solution. **No bug.**

---

### B13. `cost.Puzzle.__init__` — `self.owner[r][c] = lab` for each state. If two states overlap, the later one wins, and `holes` is empty (every cell covered). So overlapping states are **not detected**. The spec says "partition". **MAJOR** (see M3).

---

### B14. `cost.Puzzle.step_cost` — `la, lb = self.owner[a[0]][a[1]], self.owner[b[0]][b[1]]`. If `a` or `b` is out of bounds, `IndexError`. `neighbours` only returns in-bounds cells, so `dist` and `cost_field` are safe. **No bug.**

---

### B15. `cost.check_L1` — `abs(d[y[0]][y[1]] - (d[r][c] - puz.step_cost(x, y))) < 1e-9`. If `d[y]` is `INF`, `abs(INF - finite) = INF`, not `< 1e-9`, so the check fails and `x` is reported as bad. But `d[x]` is finite (checked), and `d[y]` could be `INF` if `y` is unreachable — but `y` is a neighbour of `x`, and `x` is reachable, so `y` is reachable. **No bug.**

---

### B16. `cost.is_metric` — the triangle check is `D[z] > D[y] + Dy[z] + 1e-9`. This is the triangle inequality `D[z] ≤ D[y] + Dy[z]`. But `Dy` is `puz.dist(y)`, the distance from `y`. So `D[y] + Dy[z]` is the cost of a path `src -> y -> z`. The triangle inequality says `D[z] ≤ D[y] + Dy[z]`. Correct. **No bug.**

---

### B17. `hitting.min_hitting_set` — the `rec` function's `best` is a list `[size, [sets]]`. When `len(chosen) == best[0]`, it appends `tuple(sorted(chosen))`. But `chosen` is a list of cells, and `sorted(chosen)` sorts tuples. **No bug.** The `unc` computation is `[i for i in range(len(demands)) if i not in covered]` — O(m) per call. For m=9, fine. **No bug.**

---

### B18. `hitting.packing_bound` — the loop `for r in range(m+1)` tries to find a packing of size `r`. It breaks when `not found and r > 0`. But if `r=0` is not found (impossible, empty combo always works), it continues. The `found` flag is set when a combo of size `r` is found. If no combo of size `r` is found, it breaks. **But** it only checks the *first* combo of each size that works, and `best = max(best, r)`. Since it iterates `r` from 0 upward and breaks at the first failure, `best` is the largest `r` with a packing. **No bug.** Performance: `_combinations(range(m), r)` for m=9 is fine; for m=64 it would be catastrophic, but `demands` is at most the number of hints. **No bug.**

---

### B19. `generator.hint_ladder` — the ladder is built by starting from `minimal` and adding hints back, then `ladder.reverse()`. The test `test_ladder_is_ordered_from_easy_to_hard` checks `len(ladder[0]["hints"]) == all_hints_count` and `len(ladder[-1]["hints"]) == hint_count`. After reverse, `ladder[0]` is the last appended (all hints), `ladder[-1]` is the first appended (minimal). **Correct.** But the `step` numbers are reassigned after reverse. **No bug.**

---

### B20. `generator.worked_trace` — for `v > 1`, it computes `best` as the max `|v - vv|` over adjacent hinted cells. This is a *lower bound* on the state size (rule: `size_x ≥ |d(x)-d(y)|` for adjacent `y`). But the code says `"the state of this cell has size >= {best}"`. If `best` is `None` (no adjacent hint), it says "no size bound yet". **Correct.** But if `best` is `0` (adjacent hint with same value), it says "no size bound yet" because `if best else`. `0` is falsy, so it prints "no adjacent hint" — **wrong message**. MINOR.

---

### B21. `judge._path_cost_inside` — uses BFS with `dist[nb] = d + size`. This is correct for a uniform-cost path inside one state (every step costs `size`). **No bug.**

---

### B22. `judge._ub_violates` — only checks the **newly placed** state. The docstring says "every older state was checked when it was appended". But `_ub_violates` is called with `mask_m` (the new state) and `hints`. It checks hinted cells **in `mask_m`**. An older state's hinted cells were checked when that state was appended. **Correct.** But: the UB prune only fires if the state **has a capitol**. A state without a capitol contributes no UB. **Correct** (a capitol-less state can't be the destination). **No bug.**

---

### B23. `judge.decide` — the `rec` function's `possible` starts as `all_cells` (all `n*n` cells). The first state placed removes its cells from `possible` and adds back its capitol (if any). So `possible` shrinks. **Correct.** But `_lb_violates` is called with `new_possible` **before** recursing. If `new_possible == 0`, it returns `True` (prune). **Correct** (no capitol can exist). **No bug.**

---

### B24. `judge.decide` — the `rec` function checks `if rem == 0` and then builds a `Puzzle` from `chosen`. But `chosen` is a list of masks, and `self.cat.cells_of(m)` for `lazy=True` is `LazyCatalogue` — which has no `cells_of` method! `LazyCatalogue` only has `cell_states` and `stats`. **BLOCKER.**

**Demonstration:**
```python
# judge.decide, lazy=True:
puz = Puzzle([self.cat.cells_of(m) for m in chosen])
# AttributeError: 'LazyCatalogue' object has no attribute 'cells_of'
```
**Fix:** add `cells_of` to `LazyCatalogue`, or use `self._mask_of` inverse.

---

### B25. `judge._capitol_of_mask` — for `lazy=True`, it reconstructs the cell list from the mask. For `lazy=False`, it uses `self.cat.cells_of(mask)`. **Correct.** But `_capitol_of_mask` is called with `mask_m` which is an `int` (from `Catalogue`) or a `frozenset` (from `LazyCatalogue`). In `decide`, `mask_m = m if isinstance(m, int) else self._mask_of(m)`. So `mask_m` is always an `int`. **Correct.**

---

### B26. `judge.decide` — `cands = (self.cat.cell_states(self.cat.cells[first]) if self.lazy else self.by_cell[first])`. For `lazy=True`, `self.cat.cells[first]` is a cell. For `lazy=False`, `self.by_cell[first]` is a list of masks. **Correct.** But `self.by_cell` is `self.cat.by_cell` (a `defaultdict(list)`), and `first` is an index. **Correct.**

---

### B27. `lazycatalogue.LazyCatalogue.cell_states` — it iterates over `self._syms` and calls `grow_states(anchor, sym, self.n)`. For each `st`, it checks `connected(fs)` and `symmetry_group(fs)`. **Correct.** But it does **not** check that `fs` is a subset of the board — `grow_states` already ensures that. **No bug.** Performance: for `n=11`, `symmetry_choices(11)` returns ~`(3*11)^2 * 2 + ...` ≈ 2000 symmetries, and `grow_states` for each is exponential. This will be **catastrophic** for 11×11. **MAJOR** (see M4).

---

### B28. `grow.symmetry_choices` — the loops for `refH`/`refV` go `range(-n, 2*n+1)`, which is `3n+1` values. For `n=4`, that's 13 values each. The `rot180` loop is `(3n+1)^2` ≈ 169. The `rot90` loop is `(3n+1)^2` with a parity filter ≈ 85. Total ≈ 13+13+7+7+169+85 ≈ 294 symmetries. For `n=11`, ≈ 34+34+21+21+1156+578 ≈ 1844. Each `grow_states` call is exponential in the number of orbits. **MAJOR** (see M4).

---

### B29. `grow.grow_states` — the `expand` function is recursive and has no depth limit. For a large state, the recursion depth is the number of orbits added, which can be O(n²). For `n=11`, that's ~121, fine. **No bug.**

---

### B30. `grow.grow_states` — `results.append(mask)` appends **every** intermediate mask, including disconnected ones. `LazyCatalogue` filters. But `Generator._add_constructible_states` also filters. **No bug.**

---

### B31. `rules.capitol_of` — `fixed = [fs for fs in group.values()]`. If `group` is empty, returns `None`. If every `fs` has `len(fs)==1`, it collects `unique = {next(iter(fs)) for fs in fixed}`. If `len(unique) != 1`, returns `None`. **Correct.** But the comment says "if every non-identity element fixes exactly one cell, they fix the SAME cell" — this is **not always true**. Consider a state with two symmetries fixing different cells. Can that happen? If `σ` fixes `x` and `τ` fixes `y≠x`, then `στ` fixes... not necessarily `x` or `y`. But the code checks `len(unique) != 1` and returns `None`, so it's safe. **No bug.**

---

### B32. `rules.symmetry_group` — the `REF_D1` candidate is gated on `(sr-sc)%n==0`, and the map is `(r,c) -> (c+k, r-k)` with `k=(sr-sc)//n`. This is a reflection in the line `r-c=k`. **Correct.** The `REF_D2` candidate is gated on `(sr+sc)%n==0`, map `(r,c) -> (k-c, k-r)` with `k=(sr+sc)//n`. This is a reflection in `r+c=k`. **Correct.** The `REF_H` candidate is gated on `(2*sr)%n==0`, map `(r,c) -> (a-r, c)` with `a=(2*sr)//n`. This is a reflection in `r=a/2`. **Correct.** The `REF_V` candidate is gated on `(2*sc)%n==0`, map `(r,c) -> (r, b-c)` with `b=(2*sc)//n`. **Correct.** The `ROT_180` candidate is gated on both, map `(r,c) -> (a-r, b-c)`. **Correct.** The `ROT_90`/`ROT_270` candidates are gated on both `(sr-sc)%n==0` and `(sr+sc)%n==0`, map `(r,c) -> (c+k1, k2-r)` and `(r,c) -> (k2-c, r-k1)`. **As noted in B1, the sign of `k1` is wrong.** But since the acceptance test is exact, the bug is latent. **MAJOR** (see M1).

---

### B33. `rules.symmetry_group` — the `ROT_90` map `(r,c) -> (c+k1, k2-r)` with `k1=(sr-sc)//n`, `k2=(sr+sc)//n`. The correct 90° rotation about `(sc/n, sr/n)` is `(r,c) -> (c + (sc-sr)/n, (sr+sc)/n - r)`. So the code's `k1` should be `(sc-sr)//n`, not `(sr-sc)//n`. **Confirmed B1.**

---

### B34. `rules.symmetry_group` — the `ROT_270` map `(r,c) -> (k2-c, r-k1)` with `k1=(sr-sc)//n`. The correct 270° rotation about `(sc/n, sr/n)` is `(r,c) -> ((sr+sc)/n - c, r + (sc-sr)/n)`. So the code's `r-k1` should be `r + (sc-sr)/n = r - (sr-sc)/n = r - k1`. **Wait** — `r - k1 = r - (sr-sc)/n`. And the correct is `r + (sc-sr)/n = r - (sr-sc)/n`. So `r - k1` **is** correct for ROT_270! Let me recheck ROT_90. Correct: `(r,c) -> (c + (sc-sr)/n, (sr+sc)/n - r)`. Code: `(c + k1, k2 - r)` with `k1=(sr-sc)/n`. So code's first component is `c + (sr-sc)/n`, correct is `c + (sc-sr)/n`. **Sign flip confirmed for ROT_90.** For ROT_270: correct `(r,c) -> ((sr+sc)/n - c, r + (sc-sr)/n)`. Code: `(k2 - c, r - k1)` with `k1=(sr-sc)/n`. Code's second component is `r - (sr-sc)/n = r + (sc-sr)/n`. **Correct.** So only ROT_90 is wrong. **MAJOR.**

---

### B35. `grow.symmetry_choices` — the `rot90` map is `lambda r, c, h=h, g=g: (c + h, g - r)` with `h=(k1-k2)//2`, `g=(k1+k2)//2`. The centre is `(k1/2, k2/2)`. The correct 90° rotation about `(k1/2, k2/2)` is `(r,c) -> (k1/2 + (c - k2/2), k2/2 - (r - k1/2)) = (c + (k1-k2)/2, (k1+k2)/2 - r)`. So `h=(k1-k2)/2`, `g=(k1+k2)/2`. **Correct.** The `rot270` map is `lambda r, c, h=h, g=g: (g - c, r - h)` with `h=(k1-k2)//2`, `g=(k1+k2)//2`. Correct 270° about `(k1/2, k2/2)` is `(r,c) -> (k1/2 - (c - k2/2), k2/2 + (r - k1/2)) = ((k1+k2)/2 - c, r + (k2-k1)/2)`. Code: `(g - c, r - h) = ((k1+k2)/2 - c, r - (k1-k2)/2) = ((k1+k2)/2 - c, r + (k2-k1)/2)`. **Correct.** So `grow.py`'s rot90/rot270 are **correct**, and `rules.py`'s rot90 is **wrong**. The test `test_rot90_has_order_four_and_rot270_is_its_inverse` only tests `grow.py`, not `rules.py`. **This is why the bug survived.** MAJOR.

---

### B36. `tests/test_grow.py::test_rot90_fixed_point_is_the_centre` — asserts `len(fixed) <= 1`. For a 90° rotation about a cell centre, the fixed point is the centre cell. For a 90° rotation about a lattice point (corner), the fixed point is that corner. Both are ≤1. **Correct.** But the test does not check that the fixed point is the *centre* — it only checks `≤1`. **MINOR.**

---

### B37. `tests/test_rules.py::test_no_floating_point` — checks `capitol_of(green) == (2,3)` for `green = {(1,3),(2,2),(2,3)}`. This is the official green L-tromino. `symmetry_group(green)` should contain `refD1`. Let me verify: `sr = 1+2+2 = 5`, `sc = 3+2+3 = 8`, `n=3`. `(sr-sc)%3 = (5-8)%3 = 0`, so `k1 = (5-8)//3 = -1`. Map `(r,c) -> (c-1, r+1)`. `(1,3) -> (2,2)` ✓, `(2,2) -> (1,3)` ✓, `(2,3) -> (2,3)` ✓. So `refD1` fixes `(2,3)`. **Correct.** The test passes. **No bug.**

---

### B38. `tests/test_regression.py::test_full_d_field` — checks the full 5×5 d-field. The `PUBLISHED_D_FIELD` has `d[2][1] = 0` and `d[2][3] = 0`. These are the capitols at 1-based `(3,2)` and `(3,4)`. **Correct.** But `d[4][4] = 0` is the capitol at `(5,5)`. **Correct.** The test passes if the engine is correct. **No bug.**

---

### B39. `tests/test_regression.py::test_checksum_invariant` — checks `sum_row_sums == sum_state_sizes_squared == 195`. For the official example, row sums are `[37,29,31,43,55]`, sum = 195. State sizes are `[7,4,3,11]`, squares sum = `49+16+9+121 = 195`. **Correct.** **No bug.**

---

### B40. `tests/test_lemmas.py::TestHittingSetNumbers` — reads `data/puzzles/official-11x11/puzzle.json` and checks `rep["hints"] == 33`, etc. This test depends on a data file that may not exist. **MINOR** (test fragility).

---

### B41. `tests/test_lemmas.py::TestM4DominantState::test_same_state_capitol_is_allowed` — the final line `self.assertEqual(foreign_capitol_violations(Puzzle(parts), d), [])` uses `parts` and `d` from the loop, which may be from a different iteration than `found`. **MINOR** (test bug).

---

### B42. `tests/test_generator.py::test_corner_branches_match_the_known_377` — checks `len(self.gen.by_cell[(0,0)]) == 377`. This is a hard-coded constant. If the generator's `_add_constructible_states` is correct, it passes. **No bug.**

---

### B43. `tests/test_generator.py::test_every_legal_state_is_constructible` — checks `len(legal - constructed) == 0`. This is the key test for rule 13. If `grow_states` prunes disconnected intermediates, this fails. The code does **not** prune disconnected intermediates (the comment says so), so it should pass. **No bug.**

---

### B44. `tests/test_generator.py::test_hint_set_is_irreducible` — for each hint, deletes it and checks `not res["unique"]`. But `res["unique"]` is `exhausted and len(answers)==1`. If the judge is not exhaustive, `unique` is `False`, so the test passes even if the hint was not needed. **MINOR** (test weakness).

---

### B45. `tests/test_generator.py::test_ladder_is_ordered_from_easy_to_hard` — checks `sizes == sorted(sizes, reverse=True)`. The ladder is built by adding hints back, so sizes increase, then reversed, so sizes decrease. **Correct.** **No bug.**

---

### B46. `tests/test_enumerate.py::test_15_capitols_impossible` — checks `15 not in res["tilings_by_capitols"]`. The spec says 15 is impossible. **Correct.** **No bug.**

---

### B47. `tests/test_enumerate.py::TestOddSizeCapitolRule` — checks every capitol-bearing state has odd size. **Correct** (rule 6). **No bug.**

---

### B48. `cost.Puzzle.cost_field` — returns `List[List[float]]` with `INF = float("inf")`. The spec says "NO FLOATING POINT anywhere in the symmetry test" — the cost field is not the symmetry test, so floats are OK here. But `int(d[r][c])` in `generator.make_puzzle` and `judge.decide` converts. **No bug.**

---

### B49. `cost.Puzzle.dist` — caches by `src`. For `n=11`, `_dist_cache` holds up to 121 entries, each a 121×121 float matrix. ~1.7 MB. Fine. **No bug.**

---

### B50. `cost.is_metric` — the docstring says "O((h*w)^3) overall". For `n=11`, that's `11^6 ≈ 1.7e6` per source, times 121 sources = `2e8`. The docstring says "too slow for 11x11". **Correct.** **No bug.**

---

## MAJOR

### M1. `rules.symmetry_group` — ROT_90 sign flip (see B1/B33/B35)
**File:** `src/rules.py`, ROT_90 lambda.
**Severity:** MAJOR (latent — the exact acceptance test masks it, but it is wrong and will bite).
**Fix:** `lambda r, c, k1=(sc-sr)//n, k2=(sr+sc)//n: (c + k1, k2 - r)`.

### M2. `tiletable.load_table` — row count not cross-checked (rule 20)
**File:** `src/tiletable.py`, `load_table`.
**Severity:** MAJOR.
**Fix:** after loading, assert `len(d["fields"]) == int(d["n_tilings"])`; return `None` on mismatch.

### M3. `cost.Puzzle.__init__` — overlapping states not detected
**File:** `src/cost.py`, `__init__`.
**Severity:** MAJOR.
**Fix:** track a `seen` set; raise if a cell is assigned twice.

### M4. `lazycatalogue.LazyCatalogue.cell_states` — exponential blow-up for 11×11
**File:** `src/lazycatalogue.py`.
**Severity:** MAJOR (performance trap; the real target is 11×11).
**Proof:** `symmetry_choices(11)` yields ~1844 symmetries; `grow_states` enumerates all connected orbit-unions, which for a 121-cell board is exponential. The docstring claims "cost is proportional to what the search actually touches", but the search touches every anchor, and each anchor's state set is huge.
**Fix:** memoise per `(anchor, sym)` and prune by size; or restrict to symmetries whose fixed set intersects the anchor's orbit.

### M5. `judge.decide` — `self.cat.cells_of` missing on `LazyCatalogue` (see B24)
**File:** `src/judge.py`, `decide`.
**Severity:** BLOCKER (crashes on `lazy=True`, which is the default for `n≥5`).
**Fix:** add `cells_of` to `LazyCatalogue`.

### M6. `judge.decide` — table unpacking (see B6)
**File:** `src/judge.py`, `decide`.
**Severity:** BLOCKER.
**Fix:** `fields, answers, _ = self._table`.

### M7. `generator.worked_trace` — `if best else` treats `0` as falsy (see B20)
**File:** `src/generator.py`, `worked_trace`.
**Severity:** MINOR.
**Fix:** `if best is not None`.

### M8. `tests/test_lemmas.py::TestM4DominantState` — uses stale `parts`/`d` (see B41)
**File:** `tests/test_lemmas.py`.
**Severity:** MINOR.
**Fix:** capture `parts` and `d` at the point `found` is set.

### M9. `tests/test_generator.py::test_hint_set_is_irreducible` — passes when judge is non-exhaustive (see B44)
**File:** `tests/test_generator.py`.
**Severity:** MINOR.
**Fix:** assert `res["exhaustive"]` before checking `not res["unique"]`.

### M10. `grow.grow_states` — docstring says "CONNECTED" but returns disconnected sets (see B8)
**File:** `src/grow.py`.
**Severity:** MINOR.
**Fix:** reword docstring, or filter at return.

---

## MINOR

- `cost.check_L1` uses `1e-9` tolerance on floats — fine for the fixtures, but the spec says no floats in the symmetry test; this is the cost field, so OK.
- `hitting.packing_bound` is O(2^m) in the worst case; for m=9 fine, for m=64 catastrophic. Not exercised.
- `tilings.Catalogue._has_capitol` is dead code (the hot path uses `_cap_of_mask`). MINOR.
- `rules.partition_of` docstring says "ordered by sorted label" — correct, but `Puzzle` re-indexes by position, so the label order is irrelevant. MINOR.
- `generator.make_puzzle` uses `float` for `max_state_fraction` — fine, not a symmetry test.

---

## VERDICT

**DO NOT SHIP** — 3 BLOCKER, 4 MAJOR.

BLOCKERs: B6 (table unpacking), B24 (missing `cells_of` on `LazyCatalogue`), and the combination of B1/B33/B35 (ROT_90 sign flip in `rules.py`, masked by the exact acceptance test but wrong).

MAJORs: M1 (ROT_90), M2 (row count), M3 (overlap), M4 (11×11 blow-up).

---

## THE THREE HIGHEST-VALUE MISSING TESTS

1. **ROT_90 correctness in `rules.py`** (not just `grow.py`):
   ```python
   def test_rules_rot90_matches_grow_rot90(self):
       from rules import symmetry_group
       from grow import symmetry_choices
       # a set whose centroid is off-diagonal and which IS rot90-symmetric
       S = {(0,1),(1,0),(1,1),(1,2),(2,1)}   # X-pentomino, centroid (1,1)
       g = symmetry_group(S)
       self.assertIn("rot90", g)
       # and a set whose centroid is off-diagonal and is NOT rot90-symmetric
       T = {(0,0),(0,1),(1,0),(1,1),(2,0),(2,1)}  # 3x2 rectangle
       self.assertNotIn("rot90", symmetry_group(T))
   ```

2. **`LazyCatalogue.cells_of` exists and round-trips**:
   ```python
   def test_lazy_catalogue_cells_of(self):
       from lazycatalogue import LazyCatalogue
       lc = LazyCatalogue(5)
       for anchor in [(0,0),(2,2)]:
           for st in lc.cell_states(anchor):
               m = sum(1 << (r*5+c) for (r,c) in st)
               self.assertEqual(set(lc.cells_of(m)), set(st))
   ```

3. **Table row-count cross-check**:
   ```python
   def test_stale_table_is_rejected(self):
       import numpy as np, os
       from tiletable import table_path, rules_stamp, load_table
       p = table_path(4)
       if os.path.exists(p):
           d = np.load(p)
           np.savez_compressed(p, fields=d["fields"][:10], answers=d["answers"][:10],
                               stamp=d["stamp"], n_tilings=d["n_tilings"])
           self.assertIsNone(load_table(4), "truncated table must be rejected")
   ```