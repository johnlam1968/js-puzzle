# 11-deepseek-code-review — CODE REVIEW

- model: `deepseek/deepseek-v4.1-flash`
- finish_reason: stop
- usage: {"prompt_tokens": 39065, "completion_tokens": 9247, "total_tokens": 48312, "cost": 0.020407452, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 8192, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.020407452, "upstream_inference_prompt_cost": 0.009311052, "upstream_inference_completions_cost": 0.0110964}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 29833 reasoning_chars: 0

---

## REVIEW

# Adversarial review

I read every file. Findings below are ordered by severity. I only list things I can prove from the inlined source.

---

## BLOCKER findings

### B1. `judge.py` — `_lb_violates` is called with the wrong arity; the search path crashes on the first node
`src/judge.py`, in `decide.rec`:
```python
if self._lb_violates(hints, new_possible):
    continue
```
but the method is defined as
```python
def _lb_violates(self, possible: int) -> bool:
```
Two positional args to a one-arg method → `TypeError` on the very first candidate state. The table path never reaches this, so the bug is invisible whenever a table exists; the moment the table is missing/stale (rule 20) or `lazy=True` (n≥5), the judge dies. The `except TruncatedLibrary` clause does not catch `TypeError`.

Fix: `self._lb_violates(new_possible)`.

### B2. `judge.py` — `_lb_violates` uses `self._near`, which is only populated inside `decide`
`_near` is built at the top of `decide`, so that part is fine — but `_lb_violates` also indexes `self._near[(r, c)]` for every hint. If `decide` is ever entered with an empty `hints` dict, `_near` is `{}` and the loop body never runs, so it returns `False` — OK. The real problem is the interaction with B1: because `_lb_violates` is called with two args, the `_near` construction is dead code on the search path. Fixing B1 exposes the next issue:

### B3. `judge.py` — `_lb_violates` is unsound as written: it prunes on the *nearest possible capitol*, but the spec's lower bound is over *all* cells that are still possible capitols, and the code's `possible` mask is wrong
In `rec`:
```python
new_possible = possible & ~mask_m | keep
```
`keep` is built as
```python
for i in range(n * n):
    if not (mask_m >> i) & 1: continue
    if cap is not None and self.cat.cells[i] == cap:
        keep |= 1 << i
```
So a state with **no capitol** contributes `keep = 0`, i.e. `possible & ~mask_m` — correct. A state **with** a capitol contributes only the capitol bit — correct. But `possible` starts as `all_cells` minus hinted `d>0` cells. The `_lb_violates` check then asks: is there a still-possible capitol within `floor((v+1)/2)` of every hint? That is the *existence* bound, which is sound. **However**, the code returns `True` (prune) when `best > radius` for *any* hint — including hints whose own state has already been placed and whose capitol is already known. For a hint `x` inside an already-placed state with a known capitol `c`, the true `d(x)` is fixed; the bound `Manh(x, c) <= floor((v+1)/2)` is necessary, so pruning when no possible capitol is within radius is sound *only if* `c` is still in `possible`. It is: `keep` adds `cap`. So this is sound. **But** the `_near` list is sorted by Manhattan distance and the loop `break`s at the first `dist > radius`; if the nearest possible capitol is at distance `radius+1` but a *farther* one is the true capitol, the code correctly prunes (no capitol within radius ⇒ violation). OK. I retract B3 as a soundness bug; the real defect is B1.

### B4. `solver.py` — `_lb_violates` is called with the wrong arity too
`src/solver.py`, `rec`:
```python
if self._lb_violates(np):
    continue
```
This one is correct (one arg). But `_lb_violates` in `solver.py` is defined as `def _lb_violates(self, possible: int)`. Fine. **However**, the solver's `_lb_violates` uses `self._near`, which is built in `__init__` from `self.hints` — correct. No bug here. (I flag it only because the judge's version is broken and the two files look identical; a reviewer skimming will assume both are fine.)

### B5. `solver.py` — `_can_close` calls `_ub_violates` with the wrong signature
`src/solver.py`:
```python
def _can_close(self, cur: FrozenSet[Cell]) -> bool:
    ...
    cap = capitol_of(cur)
    if cap is not None and self._ub_violates(cur, cap):
        return False
```
and
```python
def _ub_violates(self, state: FrozenSet[Cell], cap: Cell) -> bool:
```
That matches. But `_ub_violates` iterates `self.hints` and calls `self._path_cost(state, (r,c), cap, size)`. `_path_cost` returns `None` if `dst` is unreachable — but `cap` is in `state` by construction, so it is reachable. OK. **The real bug**: `_can_close` is called on `cur` *before* the state is known to be a legal state (it checks `connected` and `symmetry_group`, good), but it does **not** check that `cur` is a subset of `rem`. In `rec`, when `cur is not None`, the code closes `cur` and recurses with `rem & ~self._mask(cur)`. If `cur` contains cells not in `rem` (possible because `cur` was built by orbit addition from `rem` but `rem` was already reduced by a *previous* close of the same `cur` in `closed_here`), the mask subtraction is a no-op for those cells and the tiling double-counts. The `closed_here` set is per-anchor and prevents re-closing the *same* `cur`, but not a `cur` that is a superset of an already-closed state. This is a real double-count risk. Severity: MAJOR (see M2).

### B6. `grow.py` — `grow_states` returns disconnected sets, but `LazyCatalogue.cell_states` filters them with `connected(fs)` *after* the fact, so the "first orbit disconnected" case is silently dropped
`src/lazycatalogue.py`:
```python
for st in grow_states(...):
    ...
    if not connected(fs): continue
    if not symmetry_group(fs): continue
    out.add(fs)
```
`grow_states` is documented to return disconnected intermediate sets (rule 13), and the test `test_connectivity_is_only_required_at_closure` asserts the anti-diagonal L-tromino `{(0,0),(0,1),(1,1)}` is *found* by `grow_states`. But `LazyCatalogue` then drops it if it is disconnected — and `{(0,0),(0,1),(1,1)}` **is** connected, so it survives. The bug is the opposite: `grow_states` returns *every* orbit-union, including disconnected ones, and `LazyCatalogue` filters them. That is correct. **However**, `grow_states` also returns the *intermediate* sets (it appends `mask` to `results` before recursing), so `LazyCatalogue` sees every partial orbit-union, not just closed states. The `connected` + `symmetry_group` filters remove the illegal ones, but a partial orbit-union that happens to be connected and symmetric is a *legal state* and is correctly kept. So the vocabulary is complete. No bug. I retract B6.

### B7. `hitting.py` — `ball` excludes `x` itself, but a capitol can be at `x` only if `d(x)=0`, which is handled separately
`src/hitting.py`:
```python
def ball(x, radius, n):
    return [(r,c) for r in range(n) for c in range(n)
            if (r,c) != x and manhattan(x,(r,c)) <= radius]
```
For a hint with `v=1`, `radius=1`, the ball is the 4 neighbours — correct, since `x` itself has `d=1>0` and cannot be a capitol. For `v=0`, `split_demands` skips it. So excluding `x` is correct. No bug.

### B8. `hitting.py` — `split_demands` marks a demand "satisfied" if *any* revealed capitol is in the ball, but the revealed capitol may be in the *same state* as the hint, in which case the step cost is `size`, not `min(size,1)`
`src/hitting.py`:
```python
if any(c in known for c in raw):
    satisfied.append((x, v, radius, []))
    continue
```
`known` is the set of `d=0` hint cells. If a revealed capitol `c` is in the ball of `x`, the code assumes `c` serves `x`. But if `c` and `x` are in the same state, the cost from `x` to `c` is `size * steps`, which can exceed `v`. The code does not check this. This is a **soundness bug in the lower bound**: it can mark a demand satisfied when it is not, undercounting the required capitols. Severity: MAJOR. The test `test_numbers` pins the 11x11 numbers, so if the official instance happens to avoid this case, the bug is latent.

Fix: only mark satisfied if `c` is in a *different* state, or if the same-state path cost is `<= v`. Since states are unknown at hint time, the safe fix is to require `c` to be a *singleton* (a 1x1 state is always a capitol and always in a different state from `x` unless `x=c`, excluded).

### B9. `tiletable.py` — `rules_stamp` hashes `rules.py`, `cost.py`, `tilings.py` but **not** `grow.py`, `lazycatalogue.py`, `judge.py`, or `solver.py`
`src/tiletable.py`:
```python
for f in ("rules.py", "cost.py", "tilings.py"):
```
Rule 20 requires the stamp to identify "the rule engine it was built from". The table is built by `Catalogue` (in `tilings.py`) using `symmetry_group`/`capitol_of` (in `rules.py`) and `Puzzle` (in `cost.py`). Those are hashed. But `grow.py` contains `symmetry_choices`, which is the *solver's* symmetry vocabulary; if `grow.py` changes (e.g. the rot90 bug that the test file mentions was fixed), the table is still considered valid. More importantly, `judge.py`'s `answers_for_hints` and `decide` logic are not hashed, so a change to the judge's hint-matching semantics would not invalidate the table. Severity: MAJOR (rule 20 violation).

Fix: hash every source file the table's correctness depends on, or hash a manifest.

### B10. `tiletable.py` — `load_table` returns `d["fields"], d["answers"], kept` but `judge.py` unpacks it as `fields, answers, n_kept` and then checks `len(fields) != n_kept`
`src/judge.py`:
```python
fields, answers, n_kept = self._table
if len(fields) != n_kept:
    ...
```
`n_kept` is `int(d["n_kept"])`, the number of rows *kept* (with a capitol). `fields` is the kept array. So `len(fields) == n_kept` always, and the cross-check never fires. Rule 20 requires the row count to be cross-checked; the check is vacuous. Severity: MAJOR.

Fix: cross-check `len(fields)` against `n_tilings` (the total) and against the expected kept count, or store a checksum.

### B11. `judge.py` — the table path returns `exhaustive: True` without verifying the table covers *every* legal tiling
`src/judge.py`:
```python
if self._table is not None:
    fields, answers, n_kept = self._table
    if len(fields) != n_kept:
        ...
    else:
        ans, count = answers_for_hints(fields, answers, n, hints)
        return {..., "exhaustive": True, ...}
```
The table is built by `build_table`, which enumerates tilings via `Catalogue.by_cell` — the *full* catalogue. For n≤4 that is exhaustive. But `load_table` only checks the stamp and `n_kept`. If the table was built with a *different* `Catalogue` (e.g. a buggy `connected_subsets`), the stamp catches it only if `tilings.py` changed. The `n_tilings` field is stored but never checked against `Catalogue(n).count_tilings()`. Severity: MAJOR (rule 20: "its row count must be cross-checked").

Fix: in `load_table`, compare `n_tilings` against a freshly computed `Catalogue(n).count_tilings()["tilings"]` (cheap for n≤4) and reject on mismatch.

### B12. `generator.py` — `hint_ladder` reverses the ladder but the test asserts `sizes == sorted(sizes, reverse=True)`
`src/generator.py`:
```python
ladder.reverse()
for i, row in enumerate(ladder):
    row["step"] = i + 1
```
The ladder is built hardest-first (irreducible set), then hints are added back one at a time, so the list grows from `len(minimal)` to `len(all_hints)`. After `reverse()`, it runs from `len(all_hints)` down to `len(minimal)`. The test:
```python
sizes = [len(r["hints"]) for r in ladder]
self.assertEqual(sizes, sorted(sizes, reverse=True), "the ladder must shrink monotonically")
```
`reverse=True` means descending, so `sizes` must be non-increasing. After `reverse()`, the first element has `len(all_hints)` and the last has `len(minimal)`, so `sizes` is non-increasing. Correct. No bug.

### B13. `generator.py` — `irreducible_hints` keeps a hint when the judge is not exhaustive, but the spec (rule 17) says a hint required now stays required forever; the code's conservative keep is correct, but it can return a *non-irreducible* set
`src/generator.py`:
```python
res = self.judge.decide(trial, budget)
if res["exhaustive"] and res["cardinality"] == 1:
    cur = trial
```
If the judge is not exhaustive, the hint is kept. This is conservative and correct for rule 17. But the returned set may contain hints that are *not* actually required (the judge just couldn't prove it). The test `test_hint_set_is_irreducible` asserts that deleting any hint breaks uniqueness — it calls `judge.decide(trial, budget=400000)` and asserts `not res["unique"]`. If the judge is not exhaustive on the trial, `unique` is `False`, so the test passes even if the hint was not needed. The test is weak, not the code. Severity: MINOR (test gap).

### B14. `solver.py` — `_pick_anchor` prefers the hinted cell with the smallest value, but ties are broken by iteration order of `self.hints`, which is a dict — non-deterministic across runs if hints are built from a set
`src/solver.py`:
```python
for (r, c), v in self.hints.items():
    ...
    if best is None or v < self.hints[best]:
        best = (r, c)
```
`self.hints` is built from the caller's dict. In `solve_grid`, `hints` comes from JSON, so insertion order is stable. In tests, `HINTS` is a literal dict, stable. But `Generator.make_puzzle` builds `all_hints` as a dict comprehension over `range(n)`, stable. So determinism holds in practice. Severity: MINOR (latent).

### B15. `solver.py` — `_complete` calls `Puzzle(chosen)` where `chosen` is a list of `FrozenSet[Cell]`; `Puzzle.__init__` computes `h` and `w` from the states, but if `chosen` does not cover the full frame, `Puzzle` raises `ValueError`
`src/solver.py`:
```python
def _complete(self, chosen):
    puz = Puzzle(chosen)
```
`_complete` is called when `rem == 0`, so `chosen` covers the full frame. OK. But `Puzzle.__init__` also raises if states overlap — they cannot, since `rem` is reduced by `mask_m`. OK.

### B16. `cost.py` — `Puzzle.__init__` computes `h` and `w` as `max(...) + 1`, so a partition of a *rectangular* grid with a missing corner is silently accepted as a smaller rectangle
`src/cost.py`:
```python
self.h = max((r for s in self.states for (r, _) in s), default=-1) + 1
self.w = max((c for s in self.states for (_, c) in s), default=-1) + 1
```
If the states cover `{(0,0),(0,1),(1,0)}` (an L-tromino), `h=2, w=2`, and the hole check finds `(1,1)` uncovered → raises. Good. But if the states cover `{(0,0),(0,1),(1,0),(1,1),(2,0)}` (a 3x2 minus `(2,1)`), `h=3, w=2`, hole at `(2,1)` → raises. Good. The check is correct. No bug.

### B17. `cost.py` — `checksum` asserts `sum(row_sums) == sum(|S|^2)`, but this is only true if every state is counted once per row it occupies
`src/cost.py`:
```python
def checksum(self):
    return {
        "sum_row_sums": sum(self.row_sums()),
        "sum_state_sizes_squared": sum(v * v for v in self.sizes.values()),
    }
```
`row_sums[r] = sum over c of size(owner[r][c])`. Summing over r gives `sum over cells of size(owner) = sum over states of size^2`. Correct. No bug.

### B18. `rules.py` — `symmetry_group` uses `n = len(cells)` as the divisor, but the divisibility conditions are on the *centroid*, which is `(sr/n, sc/n)`. For a state of size `n`, the centroid is `(sr/n, sc/n)`. The reflection `r - c = k` has `k = (sr - sc)/n`. The code checks `(sr - sc) % n == 0`. Correct. But for `rot90`, the condition is `(sr - sc) % n == 0 and (sr + sc) % n == 0`, and the map is `(r,c) -> (c + k1, k2 - r)` with `k1 = (sr-sc)/n`, `k2 = (sr+sc)/n`. Let me verify: a 90° rotation about `(r0, c0)` maps `(r,c) -> (r0 + (c - c0), c0 - (r - r0)) = (c + (r0 - c0), (r0 + c0) - r)`. So `k1 = r0 - c0`, `k2 = r0 + c0`. The centroid is `(r0, c0) = (sr/n, sc/n)`, so `k1 = (sr - sc)/n`, `k2 = (sr + sc)/n`. Correct. No bug.

### B19. `rules.py` — `capitol_of` returns `None` if `len(unique) != 1`, but the comment says "if every non-identity element fixes exactly one cell, they fix the SAME cell"
`src/rules.py`:
```python
fixed = [fs for fs in group.values()]
if not all(len(fs) == 1 for fs in fixed):
    return None
unique = {next(iter(fs)) for fs in fixed}
if len(unique) != 1:
    return None
return unique.pop()
```
The comment claims the `len(unique) != 1` check is redundant. Is it? Consider a state with two symmetries fixing different single cells. Can that happen? If `σ` fixes `x` and `τ` fixes `y ≠ x`, then `στ` fixes... not necessarily `x` or `y`. But `σ` and `τ` are both in the group, and the group is a subgroup of the dihedral group. The fixed-point sets of non-identity elements of a finite group acting on a set: if two elements fix different points, their product may fix neither. The code's check is a safety net. It is not redundant in general, but for the dihedral group acting on a grid, it might be. The code is correct either way. No bug.

### B20. `grow.py` — `symmetry_choices` generates `refH` for `k in range(-n, 2*n+1)`, i.e. `k` from `-n` to `2n`. The map is `(r,c) -> (k - r, c)`. For `k = -n`, the axis is at `r = -n/2`, far outside the board. For `k = 2n`, the axis is at `r = n`, also outside. These are harmless (they produce orbits that leave the board, rejected by `inside`). But the range is larger than needed: `k` should be `0..2n-2` for axes that can fix a board cell. The extra symmetries are wasted work. Severity: MINOR (performance).

### B21. `grow.py` — `symmetry_choices` generates `rot180` for `k1, k2 in range(-n, 2*n+1)`, i.e. `(2n+1)^2` centres. For `n=11`, that is `23^2 = 529` rot180 symmetries, plus `rot90/270` for same-parity `k1,k2` (about half of 529, times 2). Total symmetries ~ 529 + 529 + 529 + 529 + 529 + 2*265 ≈ 3500. The solver iterates all of them per anchor. For `n=11`, that is a performance trap. Severity: MAJOR (rule 19: nothing may be enumerated globally; the symmetry list is global and large).

Fix: restrict `k1, k2` to the range where the centre can be inside the board, i.e. `0 <= k1 <= 2(n-1)`, `0 <= k2 <= 2(n-1)`.

### B22. `grow.py` — `orbits_of` returns a dict mapping each cell to its full orbit, but the orbit may contain cells outside the board. `grow_states` checks `inside(o)` and rejects. But `orbits_of` is also used by `solver.py` via `_orbits`, and the solver checks `any(c not in self.idx for c in start)`. Correct. No bug.

### B23. `lazycatalogue.py` — `LazyCatalogue.__new__` returns a cached instance, but `__init__` is still called on it, resetting `_cell_cache` and `_syms`
`src/lazycatalogue.py`:
```python
def __new__(cls, n, *a, **kw):
    if n in _LAZY_CACHE:
        return _LAZY_CACHE[n]
    return super().__new__(cls)

def __init__(self, n, max_cells=None, budget=2_000_000):
    self.n = n
    ...
    self._cell_cache = {}
    ...
    _LAZY_CACHE[n] = self
```
When `__new__` returns a cached instance, Python still calls `__init__` on it, which **resets `_cell_cache` to `{}`**. The comment says "The per-anchor cache is SHARED across instances (module level), so building a second Generator for the same size costs nothing." But the cache is wiped on every construction. This is a real bug: the cache is not shared. Severity: MAJOR (performance, and contradicts the comment).

Fix: guard `__init__` with `if getattr(self, '_built', False): return`, as `Catalogue` does.

### B24. `lazycatalogue.py` — `cell_states` raises `TruncatedLibrary` if `stats.get("truncated")` is set, but `stats` is shared across all symmetries in the loop, so once one symmetry truncates, every subsequent symmetry raises
`src/lazycatalogue.py`:
```python
stats: dict = {}
for sym in self._syms:
    for st in grow_states(..., stats=stats):
        if stats.get("truncated"):
            raise TruncatedLibrary(...)
```
`grow_states` sets `stats["truncated"] = True` when the budget is hit. Once set, it stays set, so the next symmetry's first `st` triggers the raise. This is correct behavior (the library is incomplete), but the error message says "anchor {anchor} hit the node budget" — it was a *symmetry* that hit it. Minor. Severity: MINOR.

### B25. `judge.py` — `decide` builds `self._near` for every hint on every call, which is O(|hints| * n^2 log n^2). For the 11x11 with 33 hints, that is 33 * 121 * log(121) ≈ 33k operations per call. The judge is called many times in `irreducible_hints` and `hint_ladder`. Severity: MINOR (performance).

### B26. `judge.py` — the table path is taken whenever `self._table is not None`, but `self._table` is set in `__init__` only if `use_table and not lazy`. For `n=4`, `lazy=False`, so the table is loaded. If the table file is missing, `load_table` returns `None`, and the search path is used. The search path has B1 (crash). So for `n=4` without a table, the judge crashes. Severity: BLOCKER (same as B1).

### B27. `solver.py` — `_can_close` is called on `cur` at every node, and it calls `symmetry_group(cur)` and `capitol_of(cur)`, both of which are O(|cur|) and allocate. For a large state, this is expensive. Severity: MINOR (performance).

### B28. `solver.py` — `_ub_violates` iterates all hints and checks `(r,c) in state`, which is O(|hints|) per call. For 33 hints and many nodes, this is a hot loop. Severity: MINOR.

### B29. `solver.py` — `_path_cost` uses BFS with a dict, which is O(|state|) per call. Called from `_ub_violates` for every hint in the state. Severity: MINOR.

### B30. `tilings.py` — `connected_subsets` uses `excl` to exclude processed cells, but the `excl` is passed by value (int) and updated with `excl |= b` inside the loop. The recursive call `expand(newmask, newcand, higher, excl)` passes the updated `excl`. This is the ESU algorithm. The test `test_no_duplicates` passes for n=4. Correct.

### B31. `tilings.py` — `Catalogue.__init__` sets `self._built = True` before building, so if building raises, the cache is not updated (the `__new__` returns a new object next time). Correct.

### B32. `tilings.py` — `count_tilings` memoizes on `rem` only, but `count_k` memoizes on `(rem, k)`. Correct.

### B33. `tilings.py` — `count_cap` memoizes on `(rem, kcap)`, where `kcap` counts *down*. Correct.

### B34. `tilings.py` — `MAX_DP_SIZE = 5`, but the spec's 4x4 constants are reproduced. For n=5, the DP needs 2^25 = 33M entries, which is feasible but slow. The code raises for n>5. Correct.

### B35. `hitting.py` — `packing_bound` iterates `r` from 0 to `m`, and for each `r` tries all combinations. For `m=9` (the 11x11 case), that is 2^9 = 512 combinations, fine. For larger `m`, it is exponential. Severity: MINOR (performance).

### B36. `hitting.py` — `min_hitting_set` uses branch and bound, but the `best` list is mutated in `rec`, and the `covered` set is passed by value. Correct.

### B37. `hitting.py` — `min_hitting_set` returns `(None, [])` if any demand has no candidates. Correct.

### B38. `hitting.py` — `capitol_lower_bound` returns `"total_capitols_lower_bound": len(revealed) + size`. Correct.

### B39. `generator.py` — `random_tiling` uses `rng.choices(cands, weights=weights)`, where `weights = [1.0 / (len(s) ** 2) for s in cands]`. This is a float weight, but the spec's rule 1 forbids floating point *in the symmetry test*, not in sampling. Correct.

### B40. `generator.py` — `make_puzzle` checks `if not puz.capitols: continue`, which enforces rule 5. Correct.

### B41. `generator.py` — `make_puzzle` checks `if any(v == float("inf") for row in d for v in row): continue`, which is redundant given `puz.capitols` is non-empty (the cost field is finite iff there is a capitol). Correct but redundant.

### B42. `generator.py` — `make_puzzle` calls `self.judge.decide(all_hints, budget)` and checks `full["exhaustive"]` and `full["cardinality"] == 1`. This enforces rule 16. Correct.

### B43. `generator.py` — `worked_trace` for `v == 1` builds `cands` by checking `hints.get(nb, 0) <= 0`. This includes cells with `d=0` (revealed capitols) and cells not in hints (default 0). Correct per rule 12.

### B44. `generator.py` — `worked_trace` for `v > 1` computes `best` as the max `|v - vv|` over adjacent hints. This is a lower bound on the state size (rule 7). Correct.

### B45. `generator.py` — `hint_ladder` calls `self.judge.decide(trial, budget)` for every cell in `pool` at every rung. For 16 hints, that is 16 * 16 = 256 judge calls. Each call may be expensive. Severity: MINOR (performance).

### B46. `cost.py` — `is_metric` checks symmetry and triangle inequality for paths of length ≤ 2, but the docstring says "A full triangle check over all triples is O((hw)^3) per source and is not attempted here." The code is O((hw)^2) per source for symmetry and O(hw * 4 * 4) for triangle. Correct.

### B47. `cost.py` — `check_L1` uses `abs(...) < 1e-9`, which is floating point. The spec's rule 1 forbids floating point in the symmetry test, not in the lemma checks. But `d` is a float array (INF = float("inf")), so the checks are float. Correct.

### B48. `cost.py` — `high_d_cells` uses `2 * d[r][c] > total`, where `d` is float. For `d = INF`, the check `d[r][c] != INF` excludes it. Correct.

### B49. `cost.py` — `foreign_capitol_violations` checks `puz.owner[y[0]][y[1]] != puz.owner[x[0]][x[1]]`. Correct per rule 10.

### B50. `cost.py` — `capitol_neighbour_bound` returns the first adjacent capitol's `min(size_x, size_c)`, but the docstring says it is a lower bound. Correct.

---

## MAJOR findings (summary of the above)

- **M1 (B1/B26)**: `judge.py` `_lb_violates` arity mismatch → crash on search path.
- **M2 (B5)**: `solver.py` `_can_close` / `closed_here` can double-count tilings.
- **M3 (B8)**: `hitting.py` `split_demands` marks a demand satisfied by a same-state revealed capitol.
- **M4 (B9)**: `tiletable.py` `rules_stamp` does not hash `grow.py`, `judge.py`, `solver.py`.
- **M5 (B10/B11)**: `tiletable.py` row-count cross-check is vacuous; `n_tilings` never checked.
- **M6 (B21)**: `grow.py` `symmetry_choices` generates ~3500 symmetries for n=11 (performance trap).
- **M7 (B23)**: `lazycatalogue.py` `__init__` wipes the shared cache on every construction.

---

## MINOR findings

- **m1 (B13)**: `test_hint_set_is_irreducible` passes when the judge is non-exhaustive.
- **m2 (B14)**: `_pick_anchor` tie-breaking depends on dict order.
- **m3 (B20)**: `symmetry_choices` ranges are wider than needed.
- **m4 (B24)**: `TruncatedLibrary` message blames the anchor, not the symmetry.
- **m5 (B25/B27/B28/B29/B35/B45)**: various hot loops without caching.

---

## Dead code / misleading names / comments contradicting code

- `src/cost.py` `check_L1` docstring says "L1 tight edge" but the function returns a list of bad cells, not an edge.
- `src/grow.py` `grow_states` docstring says "The returned sets are NOT necessarily connected" but `LazyCatalogue` filters them; the docstring is correct for `grow_states` itself.
- `src/judge.py` `_lb_violates` docstring says "the nearest cell that can still be a capitol must be within the published distance" — but the code uses `floor((v+1)/2)`, not `v`. The docstring is stale.
- `src/lazycatalogue.py` docstring says "The per-anchor cache is SHARED across instances" — false (B23).
- `src/tiletable.py` `rules_stamp` docstring says "if the rule kernel changes, a table built from the old rules would silently produce wrong answers" — but the stamp misses `grow.py`/`judge.py`/`solver.py` (B9).
- `src/solver.py` `_lb_violates` docstring says "the nearest cell that can still be a capitol must be within the published distance" — same stale wording as judge.

---

## Edge cases the tests do not cover

- **Empty grid**: `Puzzle([])` → `h=0, w=0`, `holes=[]`, `claimed=0`, `h*w=0`, no error. `cost_field` returns `[]`. `answer` returns `0`. No test.
- **Single cell**: `Puzzle([{(0,0)}])` → `h=1, w=1`, capitol `(0,0)`, `d=[[0]]`, `answer=1`. No test.
- **1x2**: `Puzzle([{(0,0),(0,1)}])` → domino, no capitol, `d=[[inf,inf]]`. No test.
- **1x3**: `Puzzle([{(0,0),(0,1),(0,2)}])` → bar3, no capitol. No test.
- **States with no symmetry**: `Puzzle([{(0,0),(1,0),(2,0),(2,1)}])` → L-tetromino, `capitol_of` returns `None`, but `Puzzle` accepts it (it does not check `is_legal_state`). The spec (rule 3) says an L-tetromino is not a state at all. `Puzzle` should reject it. No test.
- **Partitions with no capitol**: `Puzzle([{(0,0),(0,1)},{(1,0),(1,1)}])` → no capitol, `d=inf`. Tested in `test_solver.py`.
- **Rectangular grids**: `Puzzle` computes `h` and `w` from the states, so a rectangular grid is supported. No test.
- **N=2**: tested in `test_solver.py`.

---

## Performance traps for 11x11

- `symmetry_choices(11)` generates ~3500 symmetries (B21). The solver iterates all of them per anchor.
- `LazyCatalogue.cell_states` calls `grow_states` for every symmetry, and `grow_states` explores all orbit-unions. For n=11, the number of orbit-unions per symmetry can be large.
- `judge.decide` builds `self._near` for every hint on every call (B25).
- `hint_ladder` calls `judge.decide` O(|hints|^2) times (B45).
- `packing_bound` is exponential in the number of demands (B35).

---

## VERDICT

**DO NOT SHIP** — 1 BLOCKER (B1/B26: judge crashes on the search path) and 7 MAJOR findings (M1–M7).

---

## THE THREE HIGHEST-VALUE TESTS THAT ARE STILL MISSING

1. **Judge search-path smoke test** (catches B1):
```python
def test_judge_search_path_does_not_crash(self):
    j = Judge(4, use_table=False)          # force the search path
    res = j.decide({(0,0): 0, (0,1): 1, (1,0): 1, (1,1): 0}, budget=200_000)
    self.assertIn("exhaustive", res)       # must not raise TypeError
```

2. **LazyCatalogue cache is actually shared** (catches B23):
```python
def test_lazy_cache_is_shared(self):
    a = LazyCatalogue(4); a.cell_states((0,0))
    b = LazyCatalogue(4)
    self.assertIs(a, b)
    self.assertGreater(len(b._cell_cache), 0)   # must NOT be wiped by __init__
```

3. **Table stamp covers every source the table depends on** (catches B9):
```python
def test_stamp_changes_when_grow_changes(self):
    import hashlib, os
    before = rules_stamp(4)
    # simulate a change to grow.py
    p = os.path.join(os.path.dirname(__file__), "..", "src", "grow.py")
    src = open(p).read()
    try:
        open(p, "w").write(src + "\n# touch\n")
        after = rules_stamp(4)
        self.assertNotEqual(before, after, "stamp must depend on grow.py")
    finally:
        open(p, "w").write(src)
```