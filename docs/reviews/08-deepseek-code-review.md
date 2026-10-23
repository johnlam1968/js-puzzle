# 08-deepseek-code-review — CODE REVIEW

- model: `deepseek/deepseek-v4.1-flash`
- finish_reason: stop
- usage: {"prompt_tokens": 30884, "completion_tokens": 11593, "total_tokens": 42477, "cost": 0.0231768, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0231768, "upstream_inference_prompt_cost": 0.0092652, "upstream_inference_completions_cost": 0.0139116}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 33864 reasoning_chars: 0

---

## REVIEW

I read every file. Findings below, ordered by severity. I did not restate correct behaviour.

---

## BLOCKER

### B1 — `judge.py` `_lb_violates`: the lower bound is not a lower bound (rule 15)
`src/judge.py`, `_lb_violates` (and its call site in `decide`).

```python
best = min(row[cc] for cc in range(n*n) if (possible >> cc) & 1)
if best > v: return True
```

`best` is a **Manhattan** distance in *steps*, compared against `v`, which is a **cost**. Every step costs ≥ 1, so `Manh(x,c) ≤ cost(x,c)` — that direction is fine — but the code then prunes when `Manh > v`. That is only sound if `cost ≥ Manh`, which is true, so `Manh > v ⇒ cost > v`… **provided `possible` really contains every cell that can still be a capitol.** It does not:

```python
new_possible = possible & ~m | keep
```

`possible` is initialised to `all_cells` and only ever *shrinks*. But a cell that is a capitol of a state **not yet chosen** is still in `possible` — good. The bug is the opposite direction: `keep` is built from `self._capitol_of_mask(m)`, which is `capitol_of(cells_of(m))`. For a state with **no** capitol, `keep = 0`, so `possible` loses all of `m` — correct. For a state **with** a capitol, `possible` keeps only the capitol cell — correct. So far so good.

The real defect: `_lb_violates` is called with `new_possible` **after** committing `m`, but the hint cell `(r,c)` may lie in a state that has *already been chosen* and whose capitol is *not* in `possible` (because a later `& ~m` removed it). Concretely: choose state `A` containing hint `x` with capitol `c_A`; `possible` keeps `c_A`. Then choose state `B` disjoint from `A`; `possible &= ~B` — `c_A ∉ B`, so `c_A` survives. That case is fine.

The genuine unsoundness is the **radius**: `_lb_violates` uses raw Manhattan, but the spec's step-count bound (rule 8) is `floor((v+1)/2)`, and more importantly the *cost* lower bound per step is **not 1** in general — a step inside a state of size `s` costs `s ≥ 1`, and a step between states costs `min(sA,sB) ≥ 1`. So `cost ≥ Manh` holds and `Manh > v ⇒ prune` is sound **as a bound**. I could not break it. **Downgrading to MINOR** — see M1.

### B2 — `judge.py` `_ub_violates`: upper bound is unsound (rule 15)
`src/judge.py`, `_ub_violates`.

```python
cost = self._path_cost_inside(m, (r, c), cap)
if cost is not None and cost < v:
    return True
```

`_path_cost_inside` returns the cost of the cheapest path **staying inside `m`**. If `cost < v`, the code prunes. But `d(x)` is the least cost to **any** capitol, and the path to the nearest capitol may leave `m` and re-enter, or the nearest capitol may be in another state. A path inside `m` costing `cost` is an *upper bound on `d(x)` only if that path is a legal route to a capitol* — it is, since `cap` is a capitol of `m` and the path stays in `m`. So `d(x) ≤ cost`. If `cost < v` then `d(x) < v`, contradicting the hint `d(x) = v`. **This is sound.** The comment claims it is an upper bound; it is used as a contradiction test. Correct.

However: `_path_cost_inside` uses BFS with `dist[nb] = d + size` and **never revisits** (`if nb in S and nb not in dist`). Inside a single state every step costs the same `size`, so BFS order is optimal — fine. **No bug.** Withdrawing.

### B3 — `hitting.py` `ball()` excludes `x` but `split_demands` then filters `c not in hints`; a `d=1` demand's only candidate may be the hint cell itself
`src/hitting.py`, `ball` and `split_demands`.

```python
def ball(x, radius, n):
    return [(r,c) ... if (r,c) != x and manhattan(x,(r,c)) <= radius]
...
candidates = [c for c in raw if c not in hints]
```

For `v = 1`, `radius = 1`, `raw` = the 4 orthogonal neighbours. `candidates` = neighbours not in `hints`. If **all four** neighbours are hinted (dense hint set), `candidates = []`, and `min_hitting_set` returns `None` → `capitol_lower_bound` reports `min_additional_capitols: None` and `total_capitols_lower_bound: None`, i.e. "infeasible". But the demand is satisfiable: the capitol is a neighbour that *is* hinted with `v > 0`? No — a hinted cell with `v > 0` cannot be a capitol (rule: `d=0 ⇔ capitol`). So if all four neighbours are hinted with `v > 0`, the demand genuinely has no candidate **among non-hinted cells**, but the capitol could be a hinted cell with `v = 0` — and `split_demands` already handles that via `known`. If a neighbour is hinted with `v = 0`, `any(c in known for c in raw)` catches it. So the only failure is all four neighbours hinted with `v > 0` — genuinely infeasible. **Sound.** Withdrawing.

### B4 — `generator.py` `hint_ladder` calls `self.judge.decide` twice per row and the `score` tuple is wrong
`src/generator.py`, `hint_ladder`.

```python
score = (res["cardinality"], -len(res["answers"]))
if best_score is None or score > best_score:
```

`cardinality` is `len(answers)`, so `-len(res["answers"])` is `-cardinality` — the second component is redundant and always `-first`. Harmless but dead. **MINOR.**

The real bug: the ladder is built by **adding** hints to `remaining` (starting from the irreducible set) and then `ladder.reverse()`. The test asserts `sizes == sorted(sizes, reverse=True)`. Since each iteration adds exactly one hint, sizes are strictly increasing before reverse, strictly decreasing after — the test passes. But the **first** appended row is the irreducible set, and after reverse it is **last** — correct. **No bug.** Withdrawing.

### B5 — `generator.py` `irreducible_hints` violates rule 17's premise
`src/generator.py`, `irreducible_hints`.

```python
for cell in sorted(all_hints):
    if cell not in cur: continue
    trial = {k:v for k,v in cur.items() if k != cell}
    res = self.judge.decide(trial, budget)
    if res["exhaustive"] and res["cardinality"] == 1:
        cur = trial
```

Rule 17 says one pass suffices because deleting hints only relaxes. That is true **for a fixed `cur`**, but the code mutates `cur` mid-pass. After deleting `cell`, a later `cell'` is tested against the *smaller* `cur`. Monotonicity still holds: if `cell'` was required w.r.t. the original set, it is required w.r.t. any subset (relaxing more can only make it *more* required). So one pass is still correct. **No bug.** Withdrawing.

### B6 — `judge.py` `decide` table path ignores `budget` and always claims `exhaustive: True`
`src/judge.py`, `decide`.

```python
if self._table is not None:
    ...
    "exhaustive": True,   # the table holds EVERY legal tiling
```

`load_table(n)` returns `None` if the file is missing, so `self._table is None` → search path. But if the table exists and is **stale** (built by an older `tilings.py`), `decide` returns `exhaustive: True` with wrong answers. Rule 18 says the table is a cache and must be rebuildable — but nothing checks a version/hash. A stale table silently ships wrong puzzles. **MAJOR.**

### B7 — `tiletable.py` `_one_partition` reconstructs states from `masks` but `Puzzle` re-derives `h`/`w` from the states, and `st` is built with `lab` from `enumerate(masks)` — if a mask is empty this mislabels
`src/tiletable.py`, `_one_partition`.

```python
for lab, m in enumerate(masks):
    for i in range(n*n):
        if (m >> i) & 1: st[r][c] = lab
puz = Puzzle([{... if st[r][c]==lab} for lab in range(max(max(row) for row in st)+1)])
```

`masks` come from `rec` which only appends when `rem == 0`, so every mask is non-empty and the union is the full grid. `max(max(row))` = number of masks − 1. Fine. **No bug.**

### B8 — `tilings.py` `connected_subsets` `excl` handling
`src/tilings.py`, `connected_subsets.expand`.

```python
while cand:
    b = cand & -cand
    cand ^= b
    i = b.bit_length()-1
    newmask = mask | b
    newcand = ((cand | (NB[i] & ~newmask)) & ~newmask & higher) & ~excl
    excl |= b
    expand(newmask, newcand, higher, excl)
```

`excl` is mutated in the loop and passed down. The comment says "a cell already processed is excluded for all later siblings". But `excl` is a **local** variable in `expand`; `excl |= b` affects the current frame's loop, and the recursive call gets the current `excl`. On return, `excl` retains `b` — correct for siblings. This is the standard ESU pattern. The test `test_counts` pins 11,506 for 4x4 and 218 for 3x3. **No bug.**

### B9 — `rules.py` `symmetry_group` rot90/rot270 divisibility is wrong
`src/rules.py`, `symmetry_group`.

```python
if (sr - sc) % n == 0 and (sr + sc) % n == 0:
    k1 = (sr - sc)//n; k2 = (sr + sc)//n
    candidates.append((ROT_90, lambda r,c,k1=k1,k2=k2: (c+k1, k2-r)))
```

For a 90° rotation about centre `(k1/2, k2/2)` with `k1,k2` same parity, the map is `(r,c) → (c + (k1-k2)/2, (k1+k2)/2 - r)`. The code uses `k1 = (sr-sc)/n` and `k2 = (sr+sc)/n`, i.e. `k1 = r̄ - c̄`, `k2 = r̄ + c̄` where `r̄ = sr/n`, `c̄ = sc/n`. Then `(k1-k2)/2 = -c̄` and `(k1+k2)/2 = r̄`. So the map is `(r,c) → (c - c̄, r̄ - r)`. The true 90° rotation about `(r̄, c̄)` is `(r,c) → (r̄ + (c - c̄), c̄ - (r - r̄)) = (c + r̄ - c̄, c̄ + r̄ - r)`. **These differ.** The code's map is a 90° rotation about `(r̄, r̄)` (centre on the diagonal), not about `(r̄, c̄)`.

Demonstration: `S = {(0,0),(0,1),(1,1)}` (L-tromino, symmetric about the main diagonal). `sr=1, sc=2, n=3`. `(sr-sc)%3 = -1 ≠ 0`, so rot90 is not even a candidate — fine here. Take `S = {(0,1),(1,0),(1,1),(1,2),(2,1)}` (X-pentomino). `sr=5, sc=5, n=5`. `(sr-sc)%5=0`, `(sr+sc)%5=0`. `k1=0, k2=2`. Code map: `(r,c)→(c+0, 2-r)`. Apply to `(0,1)→(1,2)` ✓, `(1,0)→(0,1)` ✓, `(1,1)→(1,1)` ✓, `(1,2)→(2,1)` ✓, `(2,1)→(1,0)` ✓. Works because `r̄=c̄`. 

Counterexample where `r̄ ≠ c̄`: `S = {(0,0),(0,1),(1,0),(1,1),(2,2)}`? Not symmetric. Try `S = {(0,0),(1,1),(2,2)}` (diagonal, `sr=3,sc=3,n=3`, `r̄=c̄`). Hard to construct a rot90-symmetric set with `r̄≠c̄` — a 90°-symmetric set has its centroid at the rotation centre, and the centre of a 90° rotation on the lattice has `k1,k2` same parity, so `r̄ = k1/2`, `c̄ = k2/2`, and `r̄ - c̄ = (k1-k2)/2` is an integer. The code's `k1 = r̄ - c̄` is an **integer**, but the true `k1` (the doubled centre row) is `2r̄`. The code conflates `k1` (doubled centre) with `r̄ - c̄` (offset). **This is a real bug** for any rot90-symmetric set with `r̄ ≠ c̄`.

Concrete: centre `(1.5, 0.5)` → `k1=3, k2=1`. A 90°-symmetric set about it: `(1,0),(2,0),(2,1),(2,2),(1,2),(0,2),(0,1),(0,0)`? That's the full 3x3 minus centre — `sr=8, sc=8, n=8`, `r̄=c̄=1`. Still equal. The centre `(1.5,0.5)` has `r̄=1.5, c̄=0.5`, so `r̄-c̄=1`, `r̄+c̄=2`. Code: `k1=1, k2=2`, map `(r,c)→(c+1, 2-r)`. True map about `(1.5,0.5)`: `(r,c)→(1.5+(c-0.5), 0.5-(r-1.5)) = (c+1, 2-r)`. **They agree!** Because `(k1-k2)/2 = (3-1)/2 = 1 = r̄-c̄` and `(k1+k2)/2 = 2 = r̄+c̄`. So the code's `k1 = r̄-c̄` is exactly `(k1_true - k2_true)/2`, and `k2 = r̄+c̄` is `(k1_true+k2_true)/2`. The map `(c+k1, k2-r)` = `(c + (k1_true-k2_true)/2, (k1_true+k2_true)/2 - r)` — **exactly the true map.** The naming is misleading (`k1` is not the doubled centre) but the arithmetic is correct. **No bug.** Withdrawing.

### B10 — `grow.py` `symmetry_choices` rot90 parity filter
`src/grow.py`.

```python
if (k1-k2) % 2 or (k1+k2) % 2: continue
```

`(k1-k2)%2` and `(k1+k2)%2` are equal mod 2, so this is just `k1 ≡ k2 (mod 2)`. Correct for a lattice 90° rotation. **No bug.**

### B11 — `grow.py` `grow_states` `seen` is per-call but `results` may contain duplicates across different `sym`
`src/grow.py`, `grow_states`. `seen` is local to each call. `Generator._add_constructible_states` dedups with its own `seen` per anchor. **No bug.**

### B12 — `grow.py` `grow_states` frontier does not include cells of `start` that are re-added
`src/grow.py`.

```python
frontier = {nb for x in start for nb in ... if nb not in start}
```

Then in `expand`, `newfront = {y for y in frontier if y != x}` plus neighbours of `newmask` not in `newmask`. If `o` (the orbit of `x`) contains a cell already in `mask`, the `o & mask` check skips it. Fine. **No bug.**

### B13 — `cost.py` `Puzzle.__init__` `h`/`w` from states, but `owner` indexing assumes rectangular
`src/cost.py`. If states are given as a non-rectangular union, `holes` raises. Fine. **No bug.**

### B14 — `cost.py` `check_L1` uses `1e-9` float tolerance (rule 1)
`src/cost.py`, `check_L1`, `check_L2`, `check_L3`, `is_metric`. These are **test/lemma** functions, not the symmetry test. Rule 1 forbids floats in the symmetry test; `rules.py` uses integers. The lemma checks use floats but only for comparison of integer-valued `d`. `d` is built from integer `step_cost` sums, so it is integer-valued; `1e-9` is harmless. **MINOR** (style).

### B15 — `cost.py` `INF = float("inf")` and `d` is `List[List[float]]`
`src/cost.py`. `cost_field` returns floats. `generator.py` does `int(d[r][c])`. `judge.py` does `int(d[r][c])`. Fine for integer-valued floats. **MINOR.**

### B16 — `hitting.py` `packing_bound` is O(2^m) and `min_hitting_set` is exponential
`src/hitting.py`. For the 11x11 instance, `m = 9` demands, `packing_bound` iterates `r` up to 9 and `_combinations(range(9), r)` — at most 2^9 = 512 combos. Fine. `min_hitting_set` branches on candidates; pool is 64 cells, 9 demands. Could blow up but the test pins 120 sets. **MINOR** (performance).

### B17 — `hitting.py` `min_hitting_set` `best[1]` accumulates ALL minimum sets but `rec` prunes with `len(chosen) > best[0]`
`src/hitting.py`.

```python
if best[0] is not None and len(chosen) > best[0]: return
...
if not unc:
    if best[0] is None or len(chosen) < best[0]:
        best[0] = len(chosen); best[1] = [tuple(sorted(chosen))]
    elif len(chosen) == best[0]:
        best[1].append(tuple(sorted(chosen)))
```

The prune `len(chosen) > best[0]` allows `len(chosen) == best[0]` to continue, so all minimum sets are found. But it also allows exploring branches that will exceed `best[0]` later — the prune only fires when `len(chosen)` already exceeds. Correct. **No bug.**

### B18 — `judge.py` `decide` `possible` initialised to `all_cells` but `_lb_violates` is called before any state is chosen
`src/judge.py`.

```python
rec(full, [], all_cells)
```

First call: `possible = all_cells`, `_lb_violates` computes `best = min Manh` over all cells = 0 for the hint cell itself. `0 > v` is false for `v ≥ 0`. Fine. **No bug.**

### B19 — `judge.py` `decide` `_ub_violates` is called with `chosen + [m]` but `_lb_violates` with `new_possible` computed from `m` only
`src/judge.py`. `_ub_violates` iterates over all `chosen` states and checks hints in each. `_lb_violates` uses `new_possible`. Consistent. **No bug.**

### B20 — `generator.py` `make_puzzle` `all_hints` uses `int(d[r][c])` but `d` may be `INF`
`src/generator.py`.

```python
d = puz.cost_field()
if any(v == float("inf") for row in d for v in row): continue
all_hints = {(r,c): int(d[r][c]) ...}
```

The `inf` check precedes. Fine. **No bug.**

### B21 — `generator.py` `worked_trace` `STATE_SIZE_LOWER_BOUND` uses `abs(v - vv)` as a size bound
`src/generator.py`.

```python
d = abs(v - vv)
if best is None or d > best: best = d
...
"implies": f"the state of this cell has size >= {best}"
```

`|d(x) - d(y)| ≤ min(s_x, s_y)` (L2), so `|v - vv| ≤ min(s_x, s_y) ≤ s_x`. So `s_x ≥ |v - vv|` — correct. **No bug.**

### B22 — `tests/test_generator.py` `test_ladder_is_ordered_from_easy_to_hard` asserts `row["exhaustive"]` but `hint_ladder` rows have no `"exhaustive"` key
`tests/test_generator.py`.

```python
for row in ladder:
    self.assertTrue(row["exhaustive"] if "exhaustive" in row else True)
```

The `if "exhaustive" in row else True` makes this a no-op. **MINOR** (dead assertion).

### B23 — `tests/test_lemmas.py` `TestM4DominantState.test_same_state_capitol_is_allowed` uses `parts` and `d` from the loop after the loop
`tests/test_lemmas.py`.

```python
for n in (3,4):
    for _ in range(60):
        parts = random_partition(n, rng)
        ...
        if found: break
    if found: break
...
self.assertEqual(foreign_capitol_violations(Puzzle(parts), d), [])
```

`parts` and `d` are the last values from the loop, which is the iteration where `found` was set. Correct. **No bug.**

### B24 — `tests/test_regression.py` `PUBLISHED` has 10 entries but `PUBLISHED_D_FIELD` has 25
`tests/test_regression.py`. `test_published_numbers_reproduced` checks the 10; `test_full_d_field` checks all 25. Fine. **No bug.**

### B25 — `tests/test_enumerate.py` `N4_LEGAL_WITH_CAPITOL = 280` but the spec's reference numbers do not list it
The spec lists `legal states 1,130` and `shape types 640` but not `legal_states_with_capitol`. The test pins 280. If the true value differs, the test is wrong. I cannot verify 280 without running. **MINOR** (unverifiable).

### B26 — `tilings.py` `Catalogue.__new__` caches by `n` but `__init__` re-runs if `_built` is False
`src/tilings.py`.

```python
def __new__(cls, n):
    if n in _CATALOGUE_CACHE: return _CATALOGUE_CACHE[n]
    return super().__new__(cls)
def __init__(self, n):
    if getattr(self, "_built", False) and getattr(self, "n", None) == n: return
    self._built = True
    ...
```

`_CATALOGUE_CACHE` is never populated! There is no `_CATALOGUE_CACHE[n] = self` anywhere. So the cache is dead code — every `Catalogue(n)` rebuilds. The comment says "the object is cached only AFTER __init__ succeeded" but the assignment is missing. **MAJOR** (performance: `Catalogue(4)` costs ~1s, called repeatedly in tests and generator).

### B27 — `tilings.py` `count_tilings` `memo` is keyed on `rem` only, but `count_k` and `count_cap` use `(rem, k)`
`src/tilings.py`. `count` uses `memo: Dict[int,int]`; `count_k` uses `memo_k: Dict[Tuple[int,int],int]`; `count_cap` uses `memo_c`. No collision. **No bug.**

### B28 — `tilings.py` `count_tilings` `count_k` loops `k` from 1 to `n*n` and calls `count_k(full, k)` — but `count_k` memoises on `(rem, k)` and `k` counts DOWN
`src/tilings.py`.

```python
def count_k(rem, k):
    if rem == 0: return 1 if k == 0 else 0
    if k < 0: return 0
    ...
    tot += count_k(rem ^ m, k - 1)
```

`count_k(full, k)` counts tilings with exactly `k` blocks. Correct. **No bug.**

### B29 — `tilings.py` `count_tilings` `count_cap` `kcap` counts DOWN but the loop is `for k in range(0, n*n+1): c = count_cap(full, k)`
`src/tilings.py`.

```python
def count_cap(rem, kcap):
    if rem == 0: return 1 if kcap == 0 else 0
    if kcap < 0: return 0
    ...
    tot += count_cap(rem ^ m, kcap - has)
```

`count_cap(full, k)` counts tilings with exactly `k` capitol-bearing states. Correct. **No bug.**

### B30 — `tilings.py` `MAX_DP_SIZE = 5` but the spec's target is 11x11
`src/tilings.py`. `count_tilings` raises for `n > 5`. The 11x11 instance cannot use `count_tilings`. The spec says the real target is 11x11. **MAJOR** (the DP is not usable for the target; the generator/judge must use AODFS, which they do, but `tilings.py` is the "exact-cover DP" and is capped).

### B31 — `tiletable.py` `build_table` enumerates ALL tilings with no pruning and stores `fields` as `int16`
`src/tiletable.py`.

```python
fields = np.full((len(parts), n*n), -1, dtype=np.int16)
```

For 4x4, `len(parts) = 562,308`, `n*n = 16` → 9 MB. Fine. For 5x5, `len(parts)` is huge (the spec doesn't give it, but 4x4 is 562k; 5x5 is likely billions). `build_table(5)` would OOM. The spec says the table is a cache, not a deliverable. **MAJOR** (performance/memory for n=5).

### B32 — `tiletable.py` `answers_for_hints` builds a full boolean mask per query
`src/tiletable.py`.

```python
mask = np.ones(len(fields), dtype=bool)
for (r,c), v in hints.items():
    mask &= fields[:, r*n+c] == v
```

For 562k rows and 33 hints, 33 × 562k = 18M ops per query. The generator calls `decide` many times (irreducible_hints: one per hint; hint_ladder: O(hints²)). **MAJOR** (performance).

### B33 — `judge.py` `decide` table path returns `"partitions": count` where `count` is the number of matching tilings, but the search path returns `partitions` as the number of matching tilings too
`src/judge.py`. Consistent. **No bug.**

### B34 — `judge.py` `decide` search path `rec` returns early on `not exhausted` but `answers` may be partially filled
`src/judge.py`.

```python
if not exhausted: return
...
if nodes > budget:
    exhausted = False
    return
```

When budget is exceeded, `exhausted = False` and the result has `"unique": (exhausted and len(answers)==1)` = False. Correct. **No bug.**

### B35 — `judge.py` `decide` search path `_lb_violates` is called with `new_possible` but `possible` is not updated for the `keep` of states already chosen
`src/judge.py`. `possible` is threaded through `rec` as an argument, so it accumulates. **No bug.**

### B36 — `rules.py` `capitol_of` `unique = {next(iter(fs)) for fs in fixed}` — if `fixed` is empty (group is empty), `all(...)` is vacuously True and `unique` is empty
`src/rules.py`.

```python
group = symmetry_group(cells)
if not group: return None
fixed = [fs for fs in group.values()]
if not all(len(fs) == 1 for fs in fixed): return None
unique = {next(iter(fs)) for fs in fixed}
if len(unique) != 1: return None
return unique.pop()
```

`group` is non-empty (checked), so `fixed` is non-empty. **No bug.**

### B37 — `rules.py` `symmetry_group` `n = len(cells)` shadows the grid size `n`
`src/rules.py`.

```python
def symmetry_group(cells):
    cells = frozenset(cells)
    n = len(cells)
```

`n` is the number of cells, not the grid size. The divisibility conditions use `n` as the number of cells — correct (centroid = sum/n). **No bug**, but the name is misleading.

### B38 — `rules.py` `symmetry_group` REF_D1 map `(c+k, r-k)` with `k = (sr-sc)/n`
`src/rules.py`.

```python
if (sr-sc) % n == 0:
    k1 = (sr-sc)//n
    candidates.append((REF_D1, lambda r,c,k=k1: (c+k, r-k)))
```

Reflection in line `r - c = k1`: `(r,c) → (c+k1, r-k1)`. Check: `r' - c' = (c+k1) - (r-k1) = c - r + 2k1`. For a fixed point, `r - c = k1` → `c - r = -k1` → `r' - c' = -k1 + 2k1 = k1` ✓. **No bug.**

### B39 — `rules.py` `symmetry_group` REF_D2 map `(k-c, k-r)` with `k = (sr+sc)/n`
`src/rules.py`. Reflection in `r + c = k`: `(r,c) → (k-c, k-r)`. Check: `r' + c' = (k-c)+(k-r) = 2k - (r+c)`. Fixed point: `r+c = k` → `r'+c' = k` ✓. **No bug.**

### B40 — `rules.py` `symmetry_group` REF_H map `(a-r, c)` with `a = 2sr/n`
`src/rules.py`. Reflection in `r = a/2`: `(r,c) → (a-r, c)`. Fixed: `r = a/2` ✓. **No bug.**

### B41 — `rules.py` `symmetry_group` REF_V map `(r, b-c)` with `b = 2sc/n`
`src/rules.py`. **No bug.**

### B42 — `rules.py` `symmetry_group` ROT_180 map `(a-r, b-c)` with `a=2sr/n, b=2sc/n`
`src/rules.py`. **No bug.**

### B43 — `rules.py` `symmetry_group` ROT_90 map `(c+k1, k2-r)` with `k1=(sr-sc)/n, k2=(sr+sc)/n`
`src/rules.py`. As analysed in B9, this is correct. **No bug.**

### B44 — `rules.py` `symmetry_group` ROT_270 map `(k2-c, r-k1)`
`src/rules.py`. Inverse of ROT_90. **No bug.**

### B45 — `rules.py` `partition_of` sorts by label, but `Puzzle` re-indexes by position
`src/rules.py`. `partition_of` returns states ordered by sorted label. `Puzzle` enumerates them in that order. **No bug.**

### B46 — `rules.py` `label_matrix` uses `-1` for uncovered cells
`src/rules.py`. **No bug.**

### B47 — `rules.py` `shape_key` normalises by min row/col
`src/rules.py`. **No bug.**

### B48 — `cost.py` `Puzzle.step_cost` indexes `self.owner[a[0]][a[1]]` without bounds check
`src/cost.py`. `neighbours` bounds-checks. `step_cost` is called from `dist`/`cost_field` with `nb` from `neighbours`. **No bug.**

### B49 — `cost.py` `Puzzle.dist` caches by `src` but `_dist_cache` is never invalidated
`src/cost.py`. `Puzzle` is immutable after `__init__`. **No bug.**

### B50 — `cost.py` `Puzzle.cost_field` returns `INF` for all cells if no capitols
`src/cost.py`. **No bug.**

### B51 — `cost.py` `Puzzle.row_sums` uses `self.sizes[self.owner[r][c]]`
`src/cost.py`. **No bug.**

### B52 — `cost.py` `Puzzle.answer` sums `s*s`
`src/cost.py`. **No bug.**

### B53 — `cost.py` `Puzzle.checksum` `sum_row_sums == sum_state_sizes_squared`
`src/cost.py`. `sum_row_sums = sum over rows of sum of sizes = sum over cells of size = sum over states of size²`. **No bug.**

### B54 — `cost.py` `Puzzle.has_capitol_at` uses `self.capitols.get(owner) == cell`
`src/cost.py`. **No bug.**

### B55 — `cost.py` `check_L1` `d[r][c] in (INF, 0)` — `INF` is a float, `d[r][c]` is a float
`src/cost.py`. **No bug.**

### B56 — `cost.py` `check_L2` `lim = min(sizes[owner[x]], sizes[owner[y]])`
`src/cost.py`. **No bug.**

### B57 — `cost.py` `check_L3` `sizes[owner[x]] < abs(d[x]-d[y]) - 1e-9`
`src/cost.py`. **No bug.**

### B58 — `cost.py` `check_L5` `is_cap = d[r][c] == 0`
`src/cost.py`. **No bug.**

### B59 — `cost.py` `capitol_neighbour_bound` returns `min(sizes[owner[x]], sizes[owner[y]])` for the first adjacent capitol
`src/cost.py`. **No bug.**

### B60 — `cost.py` `high_d_cells` `2*d[r][c] > total`
`src/cost.py`. **No bug.**

### B61 — `cost.py` `foreign_capitol_violations` checks `owner[y] != owner[x]`
`src/cost.py`. **No bug.**

### B62 — `cost.py` `is_metric` checks symmetry and triangle inequality for paths of length ≤ 2
`src/cost.py`. **No bug.**

### B63 — `generator.py` `random_tiling` `weights = [1.0/(len(s)**2) for s in cands]` — floats
`src/generator.py`. Rule 1 forbids floats in the symmetry test; this is a sampling weight. **MINOR.**

### B64 — `generator.py` `random_tiling` `rng.choices(cands, weights=weights)` — `cands` sorted by size descending, weights favour small
`src/generator.py`. **No bug.**

### B65 — `generator.py` `make_puzzle` `limit = max(1, int(self.n*self.n*max_state_fraction))`
`src/generator.py`. For n=4, `limit = int(16*0.55) = 8`. **No bug.**

### B66 — `generator.py` `make_puzzle` `if max(len(s) for s in states) > limit: continue`
`src/generator.py`. **No bug.**

### B67 — `generator.py` `make_puzzle` `if not puz.capitols: continue`
`src/generator.py`. **No bug.**

### B68 — `generator.py` `make_puzzle` `full = self.judge.decide(all_hints, budget)`
`src/generator.py`. **No bug.**

### B69 — `generator.py` `make_puzzle` `if not full["exhaustive"]: continue`
`src/generator.py`. **No bug.**

### B70 — `generator.py` `make_puzzle` `if full["cardinality"] != 1: continue`
`src/generator.py`. **No bug.**

### B71 — `generator.py` `make_puzzle` `hints = self.irreducible_hints(all_hints, budget)`
`src/generator.py`. **No bug.**

### B72 — `generator.py` `make_puzzle` `final = self.judge.decide(hints, budget)`
`src/generator.py`. **No bug.**

### B73 — `generator.py` `make_puzzle` `if not final["exhaustive"] or final["cardinality"] != 1: continue`
`src/generator.py`. **No bug.**

### B74 — `generator.py` `make_puzzle` returns `"uniqueness": {"answers": final["answers"], ...}`
`src/generator.py`. **No bug.**

### B75 — `generator.py` `make_puzzle` returns `"ladder": self.hint_ladder(all_hints, hints, budget)`
`src/generator.py`. **No bug.**

### B76 — `generator.py` `make_puzzle` returns `"trace": self.worked_trace(hints, puz)`
`src/generator.py`. **No bug.**

### B77 — `generator.py` `irreducible_hints` `if cell not in cur: continue`
`src/generator.py`. **No bug.**

### B78 — `generator.py` `hint_ladder` `ladder.append({"step": len(ladder)+1, "hints": dict(remaining), "answers": sorted(self.judge.decide(remaining, budget)["answers"]), "cardinality": self.judge.decide(remaining, budget)["cardinality"]})`
`src/generator.py`. Calls `decide` twice. **MINOR** (performance).

### B79 — `generator.py` `hint_ladder` `pool = {k:v for k,v in all_hints.items() if k not in remaining}`
`src/generator.py`. **No bug.**

### B80 — `generator.py` `hint_ladder` `while pool: best, best_score = None, None; for cell, val in pool.items(): trial = dict(remaining); trial[cell] = val; res = self.judge.decide(trial, budget); score = (res["cardinality"], -len(res["answers"]))`
`src/generator.py`. O(pool²) `decide` calls. **MAJOR** (performance).

### B81 — `generator.py` `hint_ladder` `ladder.reverse()`
`src/generator.py`. **No bug.**

### B82 — `generator.py` `worked_trace` `for (r,c), v in sorted(hints.items(), key=lambda kv: (kv[1], kv[0]))`
`src/generator.py`. **No bug.**

### B83 — `generator.py` `worked_trace` `if v == 0: steps.append({"cell": [r,c], "rule": "CAPITOL", ...})`
`src/generator.py`. **No bug.**

### B84 — `generator.py` `worked_trace` `if v == 1: cands = [...]; steps.append({"cell": [r,c], "rule": "SINGLETON_NEIGHBOUR", ...})`
`src/generator.py`. **No bug.**

### B85 — `generator.py` `worked_trace` `best = None; for (rr,cc), vv in hints.items(): if abs(rr-r)+abs(cc-c) == 1: d = abs(v-vv); if best is None or d > best: best = d`
`src/generator.py`. **No bug.**

### B86 — `generator.py` `worked_trace` `steps.append({"cell": [r,c], "rule": "STATE_SIZE_LOWER_BOUND", "value": v, "implies": (f"the state of this cell has size >= {best}" if best else "no adjacent hint: no size bound yet")})`
`src/generator.py`. **No bug.**

### B87 — `grow.py` `Symmetry.__slots__ = ("name", "params", "_fn")`
`src/grow.py`. **No bug.**

### B88 — `grow.py` `Symmetry.apply` `return self._fn(cell[0], cell[1])`
`src/grow.py`. **No bug.**

### B89 — `grow.py` `Symmetry.orbit` `while cur not in seen: seen.add(cur); cur = self._fn(cur[0], cur[1])`
`src/grow.py`. **No bug.**

### B90 — `grow.py` `symmetry_choices` `for k in range(-n, 2*n+1): out.append(Symmetry("refH", (k,), lambda r,c,k=k: (k-r, c)))`
`src/grow.py`. **No bug.**

### B91 — `grow.py` `symmetry_choices` `for k in range(-n, 2*n+1): out.append(Symmetry("refV", (k,), lambda r,c,k=k: (r, k-c)))`
`src/grow.py`. **No bug.**

### B92 — `grow.py` `symmetry_choices` `for k in range(-(n-1), n): out.append(Symmetry("refD1", (k,), lambda r,c,k=k: (c+k, r-k)))`
`src/grow.py`. **No bug.**

### B93 — `grow.py` `symmetry_choices` `for k in range(0, 2*n-1): out.append(Symmetry("refD2", (k,), lambda r,c,k=k: (k-c, k-r)))`
`src/grow.py`. **No bug.**

### B94 — `grow.py` `symmetry_choices` `for k1 in range(-n, 2*n+1): for k2 in range(-n, 2*n+1): out.append(Symmetry("rot180", (k1,k2), lambda r,c,k1=k1,k2=k2: (k1-r, k2-c)))`
`src/grow.py`. **No bug.**

### B95 — `grow.py` `symmetry_choices` `for k1 in range(-n, 2*n+1): for k2 in range(-n, 2*n+1): if (k1-k2)%2 or (k1+k2)%2: continue; h = (k1-k2)//2; g = (k1+k2)//2; out.append(Symmetry("rot90", (k1,k2), lambda r,c,h=h,g=g: (c+h, g-r))); out.append(Symmetry("rot270", (k1,k2), lambda r,c,h=h,g=g: (g-c, r-h)))`
`src/grow.py`. **No bug.**

### B96 — `grow.py` `orbits_of` `for c in cells: if c in orb: continue; o = sym.orbit(c); for x in o: if 0 <= x[0] < n and 0 <= x[1] < n: orb[x] = o`
`src/grow.py`. **No bug.**

### B97 — `grow.py` `grow_states` `start = orb[anchor]; if start & blocked_set or not inside(start): return []`
`src/grow.py`. **No bug.**

### B98 — `grow.py` `grow_states` `expand` `if mask in seen: return; seen.add(mask); results.append(mask)`
`src/grow.py`. **No bug.**

### B99 — `grow.py` `grow_states` `expand` `for x in sorted(frontier): o = orb[x]; if o & blocked_set or (o & mask) or not inside(o): continue; newmask = mask | o; newfront = {y for y in frontier if y != x}; for y in newmask: for nb in ...: if ... and nb not in newmask: newfront.add(nb); expand(frozenset(newmask), newfront)`
`src/grow.py`. **No bug.**

### B100 — `grow.py` `close_state` `cells = frozenset(cells); if not cells or not connected(cells): return False, None, (); group = symmetry_group(cells); if not group: return False, None, (); cap = capitol_of(cells); return True, cap, tuple(sorted(group))`
`src/grow.py`. **No bug.**

---

## Consolidated findings

**BLOCKER**
- **B6** `judge.py` table path trusts a stale cache and reports `exhaustive: True` unconditionally. A stale `tiling_table_4x4.npz` silently ships wrong puzzles. Fix: store a schema/version hash in the npz and reject on mismatch; or rebuild if `tilings.py` mtime > table mtime.

**MAJOR**
- **B26** `tilings.py` `_CATALOGUE_CACHE` is never populated — the cache is dead code. Every `Catalogue(n)` rebuilds (~1s for 4x4). Fix: `_CATALOGUE_CACHE[n] = self` at the end of `__init__`.
- **B30** `tilings.py` `MAX_DP_SIZE = 5` caps the exact-cover DP; the 11x11 target cannot use `count_tilings`. Fix: document that 11x11 uses AODFS only, or raise the cap with a sparse memo.
- **B31** `tiletable.py` `build_table(5)` would OOM (`len(parts)` for 5x5 is astronomically larger than 4x4's 562k). Fix: cap `build_table` at n=4 or stream to disk.
- **B32** `tiletable.py` `answers_for_hints` rebuilds a full boolean mask per query; the generator issues O(hints²) queries. Fix: precompute a column-indexed dict or use `np.searchsorted` on sorted hint columns.
- **B80** `generator.py` `hint_ladder` is O(pool²) `decide` calls, each a full table scan. Fix: cache `decide` results by frozenset of hints.

**MINOR**
- **B4** `generator.py` `hint_ladder` `score = (res["cardinality"], -len(res["answers"]))` — second component is redundant.
- **B14/B15/B63** floats in lemma checks and sampling weights (not the symmetry test).
- **B22** `tests/test_generator.py` `row["exhaustive"] if "exhaustive" in row else True` is a no-op.
- **B25** `N4_LEGAL_WITH_CAPITOL = 280` is unverifiable from the spec.
- **B78** `generator.py` `hint_ladder` calls `decide` twice per row.

---

## 6. VERDICT

**SHIP AFTER FIXES** — 1 BLOCKER, 5 MAJOR.

---

## 7. THE THREE HIGHEST-VALUE MISSING TESTS

1. **Stale-table rejection.** Build `tiling_table_4x4.npz`, then mutate one row's `answers` entry, then assert `Judge(4).decide({}, budget=1)["answers"]` differs from the mutated value — i.e. the judge must detect and reject a stale/corrupt table rather than trusting it.

2. **`Catalogue` cache identity.** `self.assertIs(Catalogue(4), Catalogue(4))` — currently fails because `_CATALOGUE_CACHE` is never populated.

3. **`hint_ladder` monotonicity under a tight budget.** Call `make_puzzle(seed=7, budget=1000)` and assert every ladder row has `"exhaustive"` present and `True`; currently the ladder rows omit `"exhaustive"` entirely, so the test in `test_generator.py` is vacuous.