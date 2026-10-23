# 07-deepseek-code-review — CODE REVIEW

- model: `deepseek/deepseek-v4.1-flash`
- finish_reason: stop
- usage: {"prompt_tokens": 20203, "completion_tokens": 17862, "total_tokens": 38065, "cost": 0.0274953, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0274953, "upstream_inference_prompt_cost": 0.0060609, "upstream_inference_completions_cost": 0.0214344}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 48298 reasoning_chars: 0

---

## REVIEW

I read all six files. Findings below, ordered by severity. I did not find anything to praise; only defects.

---

## BLOCKERS

### B1 | `src/rules.py`, `symmetry_group` — the 90/270 rotation candidate is built from the wrong centre, so rot90/rot270 are *never* admitted for any state whose centroid is a cell centre

The candidate map is

```python
candidates.append((ROT_90, lambda r, c, k1=k1, k2=k2: (c + k1, k2 - r)))
```

with `k1 = (sr-sc)//n`, `k2 = (sr+sc)//n`. The true 90° rotation about the centroid `(sr/n, sc/n)` is

```
(r,c) -> (c + (sr-sc)/n, (sr+sc)/n - r)
```

which is exactly what is written — **but only when the centroid is a lattice point**, i.e. `sr ≡ 0 (mod n)` and `sc ≡ 0 (mod n)`. The code's guard is `(sr-sc)%n==0 and (sr+sc)%n==0`, which is satisfied by e.g. `sr=1, sc=2, n=3` (centroid `(1/3, 2/3)`, a *cell centre*), and then `k1 = -1/3` is not an integer, `c + k1` is a float, and `image != S` fails. So the guard admits a candidate that can never succeed, and — worse — the *correct* rot90 about a cell-centre centroid is never generated at all.

Concretely, the official 5x5 example's 3-cell state `{(1,3),(2,2),(2,3)}` (0-based) has `sr=5, sc=8, n=3`, so `sr-sc=-3 ≡ 0`, `sr+sc=13 ≢ 0 (mod 3)`. Fine. But take the 4-cell state `{(0,0),(0,1),(1,0),(1,1)}` (the 2x2 square): `sr=2, sc=2, n=4`, `sr-sc=0`, `sr+sc=4`, both `≡0 mod 4`, so `k1=0, k2=1`, and `(r,c)->(c, 1-r)` maps `(0,0)->(0,1)`, `(0,1)->(1,1)`, `(1,0)->(0,0)`, `(1,1)->(1,0)` — that *is* a 90° rotation about `(0.5,0.5)`, correct. Now take the 4-cell state `{(0,0),(0,1),(1,1),(1,2)}` (an S/Z tetromino, `sr=2, sc=4, n=4`): `sr-sc=-2 ≢ 0 mod 4`, so no rot90 candidate — correct, it has none. The failure mode is the *cell-centre* case: `n=3`, `sr=1, sc=2` (e.g. `{(0,0),(0,1),(1,1)}`, an L-tromino). `sr-sc=-1 ≢ 0 mod 3`, so no candidate — also correct by luck. The genuinely broken case is `n` odd and `sr-sc ≡ 0`, `sr+sc ≡ 0 (mod n)` with `sr,sc` not both `≡0`: e.g. `n=3`, `sr=3, sc=3` is the lattice case; `n=5`, `sr=5, sc=5` lattice; `n=5`, `sr=0, sc=0` lattice. For odd `n`, `sr-sc ≡ 0` and `sr+sc ≡ 0 (mod n)` forces `2sr ≡ 0`, and since `gcd(2,n)=1`, `sr ≡ 0` and `sc ≡ 0`. So for odd `n` the guard is exactly the lattice condition and the bug is latent. **For even `n` it is not**: `n=4`, `sr=2, sc=0`: `sr-sc=2 ≢ 0 mod 4`. `n=4`, `sr=2, sc=2`: lattice-equivalent mod 4? `sr=2` is not `≡0 mod 4`, yet `sr-sc=0`, `sr+sc=4≡0`, so the guard fires with `k1=0, k2=1` — and `(r,c)->(c,1-r)` is a genuine 90° rotation about `(0.5,0.5)`, which is a *cell centre* for even `n`. So the code is accidentally right for even `n` too, because `k1,k2` come out integral. The real defect is narrower than I first wrote: **the guard is `(sr-sc)%n==0 and (sr+sc)%n==0`, which for even `n` admits `sr=2,sc=2,n=4` (centroid `(0.5,0.5)`, a cell centre) and produces the correct map; but it also admits `sr=2, sc=6, n=4` (centroid `(0.5,1.5)`, also a cell centre) with `k1=-1, k2=2`, map `(r,c)->(c-1, 2-r)`, which is a 90° rotation about `(0.5,1.5)` — correct.** I cannot construct a case where the guard fires and the map is wrong. **Downgrading to MAJOR** (see M1). The `try/except` around `fn(r,c)` is dead code: `fn` is a pure integer lambda that cannot raise.

### B2 | `src/enumerate.py`, `connected_subsets` — the `excl` invariant is applied to `cand` but the recursion re-adds excluded cells through `NB[i] & ~newmask`

```python
newcand = ((cand | (NB[i] & ~newmask)) & ~newmask & higher) & ~excl
excl |= b
expand(newmask, newcand, higher, excl)
```

`excl` is a *local* variable mutated inside the `while cand` loop and passed by value into the recursive call. That is the intended ESU pattern. But `excl` is initialised to `0` at every `expand` entry, and the *parent's* `excl` is not threaded into the child. In ESU the exclusion set must be inherited: a cell excluded at depth `d` must stay excluded at depth `d+1`. Here `expand(newmask, newcand, higher, excl)` passes the current `excl`, and inside the child `excl` starts as that value — so it *is* inherited. The bug is the opposite: `excl |= b` happens **after** `newcand` is computed, so `b` itself is not excluded from `newcand` — but `b` is already in `newmask`, and `& ~newmask` removes it. So `b` cannot re-enter. The comment claims "missing either one makes the same subset appear under different insertion orders (measured: 4x4 gave 1,225,288 masks instead of 11,506)". The test `test_no_duplicates` passes on 4x4 per the fixture. I could not break it by hand. **No finding** — but the comment's claim that `excl` is needed *in addition to* `higher` is unverified by any test that would fail without it; `test_counts` only checks the total, and a duplicate-producing variant would also change the total, so the test does cover it. Withdraw.

### B3 | `src/hitting.py`, `ball` — excludes `x` itself, but a capitol *can* be at `x` when `d(x)=0`; and `split_demands` never calls `ball` for `v=0`

`ball(x, radius, n)` returns `[(r,c) ... if (r,c) != x and manhattan <= radius]`. For `v=0` the hint *is* a capitol and `split_demands` skips it (`if v == 0: continue`). For `v>0`, `x` is not a capitol, so excluding `x` is correct. **No finding.**

### B4 | `src/hitting.py`, `split_demands` — `candidates = [c for c in raw if c not in hints]` drops cells that are hints with `v>0`, but a `v>0` hint cell is *not* a capitol, so it is correctly excluded. However `known` is `{x for x,v in hints.items() if v==0}`, and `raw` already excludes `x`; the `any(c in known for c in raw)` check is correct. **No finding.**

### B5 | `src/hitting.py`, `min_hitting_set` — the branch-and-bound is **not** a minimum hitting set when `demands` is empty

```python
def rec(chosen, covered):
    if best[0] is not None and len(chosen) > best[0]:
        return
    unc = [i for i in range(len(demands)) if i not in covered]
    if not unc:
        ...
        return
    i = min(unc, key=...)
    for c in demands[i][3]:
        ...
```

If `demands == []`, `unc == []`, `best[0] = 0`, `best[1] = [()]`. Correct. If some demand has an **empty candidate list** (`demands[i][3] == []`), the `for c in demands[i][3]` loop body never executes, `rec` returns without recording anything, and `best[0]` stays `None`. `capitol_lower_bound` then returns `"min_additional_capitols": None` and `"total_capitols_lower_bound": 2 + None` → **TypeError**. Can a demand have an empty candidate list? `candidates = [c for c in raw if c not in hints]`; `raw` is the ball of radius `(v+1)//2` around `x`, which for `v>=1` has radius `>=1` and therefore contains at least one cell (the grid is at least 1x1 and `x` has a neighbour unless `n=1`). For `n=1` there are no neighbours and `raw` is empty → empty candidates → crash. The 11x11 instance is safe, but the function is advertised as general. **MAJOR** (see M2).

### B6 | `src/cost.py`, `Puzzle.__init__` — `self.h`/`self.w` are derived from the *states*, so a partition that does not cover a full rectangle silently produces a smaller grid

```python
self.h = max((r for s in self.states for (r,_) in s), default=-1) + 1
self.w = max((c for s in self.states for (_,c) in s), default=-1) + 1
```

For the official 5x5 example this is 5x5. For a partition of a *sub*-rectangle it is the bounding box, and `owner` is `-1` nowhere because every cell of the bounding box is covered — unless the partition has a hole. If a state set omits an interior cell, `owner[r][c] == -1`, and `step_cost` does `self.sizes[-1]` → **KeyError**. `Puzzle` never validates that the states partition a rectangle. The tests never construct such a `Puzzle`. **MAJOR.**

### B7 | `src/cost.py`, `cost_field` — `d` is `float` (`INF = float("inf")`), and `check_L5` compares `d[r][c] == 0`; `has_capitol_at` uses `self.capitols.get(...) == cell`. For a capitol at `(0,0)`, `self.capitols.get(owner[0][0])` returns `(0,0)`, and `(0,0) == (0,0)` is True. Fine. But `cost_field` returns `INF` for *every* cell when `self.capitols` is empty, and `check_L5` then flags every cell as a violation (`is_cap = (INF == 0) = False`, `has_capitol_at = False`, so `False != False` is False → no violation). Actually `is_cap != puz.has_capitol_at(x)` is `False != False` → `False`, so no violation. **No finding.** But `check_L1` skips `d[r][c] in (INF, 0)` — `INF` is a float, `d[r][c]` is a float, `in` uses `==`, fine.

### B8 | `src/cost.py`, `is_metric` — the triangle-inequality loop is `O(h^2 w^2)` per source and calls `puz.dist((rr,cc))` inside the double loop, which is cached, so it is `O((hw)^2)` total. For 11x11 that is `14641^2 ≈ 2.1e8` — slow but not fatal. The *symmetry* check `abs(D[rr][cc] - back[r][c]) > 1e-9` is correct. **MINOR** (performance).

### B9 | `src/enumerate.py`, `Catalogue.__new__`/`__init__` — the cache returns a *partially constructed* object if `__init__` raises, and `__init__`'s guard is wrong

```python
def __new__(cls, n):
    if n in _CATALOGUE_CACHE:
        return _CATALOGUE_CACHE[n]
    obj = super().__new__(cls)
    _CATALOGUE_CACHE[n] = obj
    return obj

def __init__(self, n):
    if getattr(self, "_built", False) and getattr(self, "n", None) == n:
        return
    self._built = True
    ...
```

`_CATALOGUE_CACHE[n] = obj` happens **before** `__init__` runs. If `__init__` raises (e.g. `MemoryError` on 11x11), the cache holds a half-built object with `_built` unset; the next `Catalogue(n)` returns it and `__init__` runs again — actually that is fine because `_built` is False. But if `__init__` raises *after* `self._built = True` (e.g. in `connected_subsets`), the cache holds an object with `_built=True` and `n` set, and the next call returns it with `self.states` missing → `AttributeError` on `count_tilings`. **MAJOR.**

### B10 | `src/enumerate.py`, `count_tilings` — `memo` is keyed on `rem` only, but `count` is called with `by_blocks`/`by_capitols` variants that use *separate* memos. Fine. However `count` is defined inside `count_tilings` and `memo` is local, so repeated calls to `count_tilings` rebuild the memo. For 11x11 the DP over `2^121` masks is **impossible** — the memo will hold up to `2^121` entries. The 4x4 case is `2^16 = 65536` masks, fine. The 11x11 target is not reachable by this DP. **BLOCKER for the stated target** (see V).

### B11 | `src/enumerate.py`, `count_k` — `for k in range(1, n*n+1): c = count_k(full, k)`. `count_k(rem, k)` returns `1 if k==0 else 0` at `rem==0`. For `k > n*n` it is never called. The memo key is `(rem, k)`. Correct. But `count_k` does not prune `k < 0`: `count_k(rem, k-1)` with `k=0` and `rem != 0` recurses to `k=-1`, `-2`, ... until `rem==0` (returns 0) or the memo fills. For `k=0` and `rem != 0` the recursion explores the entire subtree before returning 0. **MINOR** (performance), but for 11x11 it is fatal.

### B12 | `src/enumerate.py`, `count_cap` — `if kcap < 0: return 0` is checked **after** `if rem == 0: return 1 if kcap == 0 else 0`. So `count_cap(0, -1)` returns 0 (correct) and `count_cap(rem, -1)` returns 0 (correct). Fine. But the memo key `(rem, kcap)` is stored *after* the `kcap < 0` check, so negative keys are never memoised — correct.

### B13 | `src/grow.py`, `symmetry_choices` — the `rot90` map is built as `rr, cc = c + dx, r + dy` with `dx, dy = i - j, j - i`. For `i+j` odd, the centre is `(i+0.5, j+0.5)`. The 90° rotation about that centre is `(r,c) -> (c + (i-j), (i+j+1) - r)`? Let me verify: centre `(i+0.5, j+0.5)`. Rotate `(r,c)` by 90°: `(r', c') = (i+0.5 - (c - (j+0.5)), j+0.5 + (r - (i+0.5))) = (i - c + j + 1, j + r - i)`. The code gives `(c + i - j, r + j - i)`. These differ: code's `rr = c + i - j`, correct is `rr = i + j + 1 - c`. **These are different maps.** The code's map is a 90° rotation about a *different* centre. Let me check with `i=0, j=1` (centre `(0.5, 1.5)`): code `dx=-1, dy=1`, `(r,c)->(c-1, r+1)`. Correct 90° about `(0.5,1.5)`: `(r,c)->(0+1+1-c, 1+r-0) = (2-c, 1+r)`. Code gives `(c-1, r+1)`. For `(0,0)`: code `(-1,1)` (off-grid), correct `(2,1)`. **The code's rot90 is wrong.** It is a 90° rotation about `(0.5, 0.5)` shifted — actually `(r,c)->(c-1, r+1)` is a 90° rotation about `(0.5, 0.5)` composed with a translation. This is a **BLOCKER** for `grow.py`, but `grow.py` is not exercised by any test in the suite (no test imports `grow`). The `rules.py` `symmetry_group` is the one used by `enumerate.py` and `cost.py`, and it is separate. So `grow.py`'s `symmetry_choices` is dead code as far as the tests go, but it is wrong.

Let me double-check the `rot270` line: `{(r,c): (b - cc, a - rr) for (r,c),(rr,cc) in m.items()}` with `a,b = 2i+1, 2j+1`. This composes the (wrong) rot90 with a 180° about `(i+0.5, j+0.5)`, giving `(2i+1 - (c+i-j), 2j+1 - (r+j-i)) = (i+j+1-c, j+i+1-r)`. That is the *correct* rot270 about `(i+0.5, j+0.5)`. So `rot270` is right and `rot90` is wrong — they are not inverses. **BLOCKER** (in `grow.py`).

### B14 | `src/grow.py`, `grow_states` — `seen` is a `set` of `frozenset`s, and `expand` appends `mask` to `results` *before* checking `seen`? No: `if mask in seen: return` comes first, then `seen.add(mask)`, then `results.append(mask)`. Correct. But `expand` is called with `frozenset(start)` and `frontier`; the recursion adds orbits and re-checks connectivity. The `frontier` is rebuilt as `{y for y in frontier if y != x}` plus neighbours of `newmask`. This can *lose* frontier cells that were in `frontier` but are now in `newmask` — they are removed by `y != x` only for the chosen `x`, not for all `y in newmask`. So `newfront` may contain cells already in `newmask`. The `expand` loop then does `o = orb[x]; if o & mask: continue`, so it is harmless. **MINOR.**

### B15 | `src/grow.py`, `close_state` — returns `(True, cap, names)` where `cap` may be `None`. The docstring says "Returns (is_legal_state, capitol_or_None, symmetry_names)". Correct.

### B16 | `src/rules.py`, `capitol_of` — `fixed = [fs for fs in group.values()]`; `if not all(len(fs) == 1 for fs in fixed): return None`. For a state with a single non-trivial symmetry that fixes exactly one cell, this returns that cell. For a state with *no* non-trivial symmetry, `group` is empty and `capitol_of` returns `None` — but such a shape is not a state at all. The docstring says "if EVERY non-trivial rotation or reflection ... leaves EXACTLY ONE of its squares fixed". Correct. But `unique = {next(iter(fs)) for fs in fixed}` — if `fixed` is empty (group empty), `unique` is empty, `len(unique) != 1` → `None`. Correct.

### B17 | `src/rules.py`, `symmetry_group` — the `refD1` map is `(r,c) -> (c+k, r-k)` with `k = (sr-sc)//n`. The reflection in the line `r - c = k` is `(r,c) -> (c+k, r-k)`. Correct. `refD2` is `(r,c) -> (k-c, k-r)` with `k = (sr+sc)//n`, reflection in `r+c=k`. Correct. `refH` is `(r,c) -> (a-r, c)` with `a = 2sr//n`, reflection in `r = a/2`. Correct. `refV` is `(r,c) -> (r, b-c)` with `b = 2sc//n`. Correct. `rot180` is `(r,c) -> (a-r, b-c)`. Correct. `rot90` is `(r,c) -> (c+k1, k2-r)` with `k1=(sr-sc)//n, k2=(sr+sc)//n`. For a lattice centroid this is correct. For a cell-centre centroid (even `n`, `sr,sc` both `≡ n/2 mod n`), `k1,k2` are integers and the map is correct. For a centroid that is neither (odd `n`, `sr` or `sc` not `≡0`), the guard `(sr-sc)%n==0 and (sr+sc)%n==0` forces `sr≡sc≡0`, so the map is correct. **So `rules.py`'s rot90 is correct in all cases where it fires.** The `grow.py` copy is the broken one. Good — that narrows B13 to `grow.py` only.

### B18 | `src/rules.py`, `symmetry_group` — the `try/except` around `fn(r,c)` is dead code (pure integer lambdas). **MINOR** (dead code).

### B19 | `src/rules.py`, `partition_of` — `buckets.setdefault(lab, set()).add((r,c))` then `[frozenset(v) for _, v in sorted(buckets.items())]`. If labels are non-contiguous (e.g. `0, 2`), the returned list is indexed by *position*, not by label, so `states[1]` is the state labelled `2`. `Puzzle` then assigns `lab = enumerate(states)`, so labels are renumbered. The test `test_roundtrip` uses contiguous labels. **MINOR.**

### B20 | `tests/test_lemmas.py`, `random_partition` — the loop `for m in range(1, 1 << (n*n)): pass` is a no-op placeholder, and the *real* enumeration below it is `for m in range(1, 1 << (n*n))` which for `n=4` is 65535 iterations, each building a list and calling `connected` and `symmetry_group`. That is fine for 4x4 but the placeholder is dead code. **MINOR.**

### B21 | `tests/test_lemmas.py`, `TestM4DominantState.test_same_state_capitol_is_allowed` — the final line `self.assertEqual(foreign_capitol_violations(Puzzle(parts), d), [])` uses `parts` and `d` from the *last* iteration of the search loop, not from the `found` case. If the search breaks out of the inner loop on `found`, `parts` and `d` are from the iteration where `found` was set — actually `found` is set inside the same iteration, and the `break`s exit immediately, so `parts`/`d` are the found case. But if `found` is set in the `n=3` loop and the outer `break` fires, `parts`/`d` are the n=3 case. Correct. **No finding.**

### B22 | `tests/test_regression.py`, `TestFixturesAgreeWithTheEngine.test_counterexample_fixture_gives_two_answers` — `self.assertEqual(dfs[0], dfs[1])` compares two `List[List[float]]`. `INF` is `float("inf")`, and `inf == inf` is True, so this works. But if either field has a `NaN` it would fail; no NaN is produced. **No finding.**

### B23 | `tests/test_regression.py`, `PUBLISHED_D_FIELD` — row 2 is `[7, 0, 3, 0, 3]`. The capitols are at 0-based `(2,1)` and `(2,3)`, so `d[2][1]=0` and `d[2][3]=0`. Correct. Row 4 is `[25, 14, 13, 10, 0]`, capitol at `(4,4)`. Correct.

### B24 | `tests/test_enumerate.py`, `N4_BY_CAPITOLS` — the dict omits `15` and the test asserts `assertNotIn(15, ...)`. The spec says "15 IMPOSSIBLE". Correct. But the dict also omits `0`? No, `0: 2_723` is present. The spec's list is `0,2723 1,11744 ... 14,60 (15 IMPOSSIBLE) 16,1`. The test dict matches. **No finding.**

### B25 | `tests/test_enumerate.py`, `N4_LEGAL_WITH_CAPITOL = 280` — the spec does not give this number directly, but `N4_BY_CAPITOLS` sums to `562308` and the number of capitol-bearing *states* is 280. The spec's "legal states 1,130" and "shape types 640" are checked. **No finding.**

### B26 | `src/cost.py`, `high_d_cells` — `2 * d[r][c] > total` with `d` a float. For `d = 12.5` and `total = 25`, `25 > 25` is False. The spec says "2*d(x) > N^2". Correct. But `d` is a float and `2*d` may be `25.000000000000004` for `d=12.5`? `12.5` is exactly representable, `2*12.5 = 25.0` exactly. For integer `d`, `2*d` is exact. **No finding.**

### B27 | `src/cost.py`, `foreign_capitol_violations` — the derivation in the docstring says "for a capitol c in a DIFFERENT state, w(x,c) = min(size_x, size_c) >= d(x), and the two states are disjoint, so 2*d(x) <= size_x + size_c <= N^2". The last inequality `size_x + size_c <= N^2` is true because the states are disjoint subsets of the grid. Correct. But the code checks `puz.owner[y] != puz.owner[x]` — correct. **No finding.**

### B28 | `src/hitting.py`, `packing_bound` — the loop `for r in range(m+1): found = False; for combo in _combinations(range(m), r): ... if ok: best = max(best, r); found = True; break; if not found and r > 0: break`. This finds the largest `r` for which *some* `r`-subset has pairwise disjoint candidate sets. But it breaks out of the `r` loop as soon as no `r`-subset works, which is correct only if the property is monotone in `r` — it is (a subset of a disjoint family is disjoint). So the first `r` that fails means all larger `r` fail. Correct. But `packing_bound` is **never called** by `capitol_lower_bound` or any test. **MINOR** (dead code).

### B29 | `src/hitting.py`, `weighted_demand_order` — uses `1.0 / max(1, d[2])**2`, a float. The spec's rule 1 says "NO FLOATING POINT anywhere in the symmetry test" — this is not the symmetry test, so it is allowed. But the function is **never called**. **MINOR** (dead code).

### B30 | `src/hitting.py`, `singleton_candidates` — **never called** by `capitol_lower_bound` or any test. The docstring says "PLAN D64: a demand with v = 1 is SPECIAL ... it has to travel with the demand into the solver." But `split_demands` does **not** attach the singleton constraint to the demand, and `min_hitting_set` ignores it. So the D64 constraint is documented and implemented in a dead function, and the actual lower bound ignores it. **MAJOR** — the code contradicts its own docstring and the spec's rule 8.

### B31 | `src/hitting.py`, `capitol_lower_bound` — `pool = sorted({c for _,_,_,C in demands for c in C})`. If `demands` is empty, `pool` is empty, `min_hitting_set([])` returns `(0, [()])`, `n_minimum_sets = 1`. The test expects `n_minimum_sets = 120` for the 11x11 instance. **No finding** for the tested case.

### B32 | `src/hitting.py`, `min_hitting_set` — the `best[1]` list accumulates *all* minimum sets, but the pruning `if best[0] is not None and len(chosen) > best[0]: return` only prunes strictly larger. When a new smaller set is found, `best[1]` is *replaced* (`best[1] = [tuple(sorted(chosen))]`), discarding previously found larger sets. Correct. But when `len(chosen) == best[0]`, it appends. The `chosen` list is sorted before storing, so two different orderings of the same set produce the same tuple — but the recursion never produces the same set twice because it only adds cells not already in `chosen`. **No finding.**

### B33 | `src/hitting.py`, `min_hitting_set` — the branching picks `i = min(unc, key=lambda j: len([c for c in demands[j][3] if c not in chosen]))`. This is "fewest viable candidates". But the loop `for c in demands[i][3]` iterates over **all** candidates, including those already in `chosen` (skipped by `if c in chosen: continue`). Correct. **No finding.**

### B34 | `src/hitting.py`, `split_demands` — `radius = (v + 1) // 2`. The spec's rule 8 says "floor((v+1)/2)". For `v=1`, `(1+1)//2 = 1`. For `v=2`, `3//2 = 1`. For `v=3`, `4//2 = 2`. Correct. **No finding.**

### B35 | `src/hitting.py`, `ball` — `manhattan(x, (r,c)) <= radius` and `(r,c) != x`. The spec says "within Manhattan distance floor((v+1)/2)". Correct. **No finding.**

### B36 | `src/cost.py`, `check_L1` — `abs(d[y] - (d[x] - w)) < 1e-9`. For integer `d` and `w`, this is exact. But `d` is a float and `INF` is skipped. **No finding.**

### B37 | `src/cost.py`, `check_L2` — `lim = min(sizes[owner[x]], sizes[owner[y]])`. The spec's rule 7 says the step cost between different states is `min(sA,sB)` and inside a state is `s`. For adjacent `x,y` in the *same* state, `lim = size_x`, and the lemma `|d(x)-d(y)| <= size_x` is L3, not L2. L2 as stated ("|d(x)-d(y)| <= min(size_x, size_y)") is trivially true for same-state neighbours since `min = size_x`. **No finding.**

### B38 | `src/cost.py`, `check_L3` — `if sizes[owner[x]] < abs(d[x]-d[y]) - 1e-9`. For same-state neighbours, `size_x` is the step cost, so `|d(x)-d(y)| <= size_x` by the triangle inequality of `d` along the edge. Correct. **No finding.**

### B39 | `src/cost.py`, `Puzzle.step_cost` — `la, lb = owner[a], owner[b]`; `if la == lb: return sizes[la]`. If `a` or `b` is out of bounds, `owner[a[0]][a[1]]` raises `IndexError`. `neighbours` bounds-checks, so `step_cost` is only called on in-bounds cells. **No finding.**

### B40 | `src/cost.py`, `Puzzle.dist` — the cache `_dist_cache` is keyed on `src` and stores `List[List[float]]`. For 11x11, `is_metric` calls `dist` for every cell, so the cache holds 121 grids of 121 floats — fine. **No finding.**

### B41 | `src/cost.py`, `Puzzle.cost_field` — multi-source Dijkstra from all capitols. Correct. But it does **not** cache, so repeated calls recompute. `check_L1` etc. take `d` as an argument, so they do not recompute. **MINOR.**

### B42 | `src/cost.py`, `Puzzle.checksum` — `sum_row_sums == sum_state_sizes_squared`. For the official example, `sum_row_sums = 195` and `sum(|S|^2) = 49+16+9+121 = 195`. Correct. **No finding.**

### B43 | `src/enumerate.py`, `Catalogue.__init__` — `self._cap_of_mask = {m: hc for m, hc, _ in states}`. `hc` is a bool. `count_cap` does `has = 1 if self._cap_of_mask[m] else 0`. Correct. **No finding.**

### B44 | `src/enumerate.py`, `Catalogue.__init__` — `self.by_cell[i].append(m)` for every cell `i` in `m`. The DP picks `first = (rem & -rem).bit_length() - 1` and iterates `by_cell[first]`. Correct. **No finding.**

### B45 | `src/enumerate.py`, `Catalogue.__init__` — `types.add(shape_key([...]))`. `shape_key` normalises translation. The spec says "shape types (up to translation) 640". Correct. **No finding.**

### B46 | `src/enumerate.py`, `Catalogue._has_capitol` — dead code (the hot path uses `_cap_of_mask`). **MINOR.**

### B47 | `src/enumerate.py`, `main` — `print(f"... {cat.seconds:.1f}s")`. Fine.

### B48 | `src/grow.py`, `Symmetry.orbit` — `while cur not in seen: seen.add(cur); cur = self._map[cur]`. If `self._map` is not a permutation (e.g. the broken rot90 maps off-grid), `self._map[cur]` raises `KeyError`. The broken rot90 in `symmetry_choices` maps `(0,0)` to `(-1,1)` for `i=0,j=1`, which is not in `_map` → `KeyError`. **BLOCKER** (same root as B13).

### B49 | `src/grow.py`, `orbits_of` — `for c in cells: if c in orb: continue; o = sym.orbit(c); for x in o: orb[x] = o`. If `o` contains a cell not in `cells` (off-grid), `orb[x]` is set for an off-grid `x`, and `orb` has extra keys. Harmless but wrong. **MINOR.**

### B50 | `src/grow.py`, `grow_states` — `start = orb[anchor]`; `if start & blocked_set: return []`. Correct. **No finding.**

### B51 | `src/grow.py`, `grow_states` — `expand` is recursive and `seen` is a `set` of `frozenset`s. For 11x11 the number of connected orbit-unions can be large; recursion depth is bounded by the number of orbits. **MINOR** (performance).

### B52 | `src/rules.py`, `connected` — `start = next(iter(S))`; `seen = {start}`; DFS. Correct. **No finding.**

### B53 | `src/rules.py`, `is_legal_state` — `if not cells or not connected(cells): return False; return bool(symmetry_group(cells))`. Correct. **No finding.**

### B54 | `src/rules.py`, `shape_key` — `cells = sorted(set(cells))`; `r0 = min(...)`. If `cells` is empty, `min` raises. **MINOR.**

### B55 | `src/rules.py`, `label_matrix` — `h = max((r for s in states for (r,_) in s), default=-1) + 1`. If `states` is empty, `h=0, w=0`, returns `[]`. Correct. **No finding.**

### B56 | `tests/test_rules.py`, `test_no_floating_point` — `green = {(1,3),(2,2),(2,3)}`; `capitol_of(green) == (2,3)`. Let me verify: `sr=5, sc=8, n=3`. `sr-sc=-3 ≡ 0 mod 3`, `k1=-1`. `refD1`: `(r,c)->(c-1, r+1)`. `(1,3)->(2,2)`, `(2,2)->(1,3)`, `(2,3)->(2,3)`. So `refD1` fixes `(2,3)`. `sr+sc=13 ≢ 0 mod 3`, so no `refD2`. `2sr=10 ≢ 0 mod 3`, no `refH`. `2sc=16 ≢ 0 mod 3`, no `refV`. `2sr,2sc` not both `≡0`, no `rot180`. `sr-sc ≡ 0` but `sr+sc ≢ 0`, no `rot90/270`. So `group = {refD1: {(2,3)}}`, `capitol_of` returns `(2,3)`. Correct. **No finding.**

### B57 | `tests/test_rules.py`, `test_full_point_group_is_used` — `BAR3 = {(0,0),(0,1),(0,2)}`. `sr=0, sc=3, n=3`. `sr-sc=-3 ≡ 0`, `k1=-1`. `refD1`: `(r,c)->(c-1, r+1)`. `(0,0)->(-1,1)` off-grid → image ≠ S. `sr+sc=3 ≡ 0`, `k2=1`. `refD2`: `(r,c)->(1-c, 1-r)`. `(0,0)->(1,1)` off-grid → image ≠ S. `2sr=0 ≡ 0`, `a=0`. `refH`: `(r,c)->(0-r, c)`. `(0,0)->(0,0)`, `(0,1)->(0,1)`, `(0,2)->(0,2)`. Image = S. Fixed = all 3. `2sc=6 ≡ 0`, `b=2`. `refV`: `(r,c)->(r, 2-c)`. `(0,0)->(0,2)`, `(0,1)->(0,1)`, `(0,2)->(0,0)`. Image = S. Fixed = `{(0,1)}`. `rot180`: `(r,c)->(0-r, 2-c)`. `(0,0)->(0,2)`, `(0,1)->(0,1)`, `(0,2)->(0,0)`. Image = S. Fixed = `{(0,1)}`. `rot90`: `sr-sc ≡ 0`, `sr+sc ≡ 0`, `k1=-1, k2=1`. `(r,c)->(c-1, 1-r)`. `(0,0)->(-1,1)` off-grid → image ≠ S. So `group = {refH: 3 cells, refV: 1 cell, rot180: 1 cell}`. The test asserts `sorted(group) == ["refH","refV","rot180"]`. Correct. `capitol_of` returns `None` because `refH` fixes 3. Correct. **No finding.**

### B58 | `tests/test_rules.py`, `test_capitol_bearing_shapes` — `U_PENTOMINO = {(0,0),(0,2),(1,0),(1,1),(1,2)}`. `sr=3, sc=5, n=5`. `sr-sc=-2 ≢ 0 mod 5`, no `refD1`. `sr+sc=8 ≢ 0`, no `refD2`. `2sr=6 ≢ 0`, no `refH`. `2sc=10 ≡ 0`, `b=2`. `refV`: `(r,c)->(r, 2-c)`. `(0,0)->(0,2)`, `(0,2)->(0,0)`, `(1,0)->(1,2)`, `(1,1)->(1,1)`, `(1,2)->(1,0)`. Image = S. Fixed = `{(1,1)}`. `rot180`: `2sr ≢ 0`, no. `rot90`: `sr-sc ≢ 0`, no. So `group = {refV: {(1,1)}}`, `capitol_of` returns `(1,1)`. Correct. **No finding.**

### B59 | `tests/test_rules.py`, `test_capitol_bearing_shapes` — `W_PENTOMINO = {(0,0),(0,1),(1,1),(1,2),(2,2)}`. `sr=4, sc=6, n=5`. `sr-sc=-2 ≢ 0`, no `refD1`. `sr+sc=10 ≡ 0`, `k2=2`. `refD2`: `(r,c)->(2-c, 2-r)`. `(0,0)->(2,2)`, `(0,1)->(1,2)`, `(1,1)->(1,1)`, `(1,2)->(0,1)`, `(2,2)->(0,0)`. Image = S. Fixed = `{(1,1)}`. `2sr=8 ≢ 0`, no `refH`. `2sc=12 ≢ 0`, no `refV`. `rot180`: `2sr ≢ 0`, no. `rot90`: `sr-sc ≢ 0`, no. So `group = {refD2: {(1,1)}}`, `capitol_of` returns `(1,1)`. Correct. **No finding.**

### B60 | `tests/test_rules.py`, `test_legal_states_without_capitol` — `X_PENTOMINO = {(0,1),(1,0),(1,1),(1,2),(2,1)}`. `sr=5, sc=5, n=5`. `sr-sc=0 ≡ 0`, `k1=0`. `refD1`: `(r,c)->(c, r)`. `(0,1)->(1,0)`, `(1,0)->(0,1)`, `(1,1)->(1,1)`, `(1,2)->(2,1)`, `(2,1)->(1,2)`. Image = S. Fixed = `{(1,1)}`. `sr+sc=10 ≡ 0`, `k2=2`. `refD2`: `(r,c)->(2-c, 2-r)`. `(0,1)->(1,2)`, `(1,0)->(2,1)`, `(1,1)->(1,1)`, `(1,2)->(0,1)`, `(2,1)->(1,0)`. Image = S. Fixed = `{(1,1)}`. `2sr=10 ≡ 0`, `a=2`. `refH`: `(r,c)->(2-r, c)`. `(0,1)->(2,1)`, `(1,0)->(1,0)`, `(1,1)->(1,1)`, `(1,2)->(1,2)`, `(2,1)->(0,1)`. Image = S. Fixed = `{(1,0),(1,1),(1,2)}` — 3 cells. So `capitol_of` returns `None`. Correct. **No finding.**

### B61 | `tests/test_rules.py`, `test_legal_states_without_capitol` — `T_TETROMINO = {(0,0),(0,1),(0,2),(1,1)}`. `sr=1, sc=4, n=4`. `sr-sc=-3 ≢ 0 mod 4`, no `refD1`. `sr+sc=5 ≢ 0`, no `refD2`. `2sr=2 ≢ 0`, no `refH`. `2sc=8 ≡ 0`, `b=2`. `refV`: `(r,c)->(r, 2-c)`. `(0,0)->(0,2)`, `(0,1)->(0,1)`, `(0,2)->(0,0)`, `(1,1)->(1,1)`. Image = S. Fixed = `{(0,1),(1,1)}` — 2 cells. `rot180`: `2sr ≢ 0`, no. `rot90`: `sr-sc ≢ 0`, no. So `group = {refV: 2 cells}`, `capitol_of` returns `None`. Correct. **No finding.**

### B62 | `tests/test_rules.py`, `test_legal_states_without_capitol` — `S_TETROMINO = {(0,1),(0,2),(1,0),(1,1)}`. `sr=2, sc=4, n=4`. `sr-sc=-2 ≢ 0`, no `refD1`. `sr+sc=6 ≢ 0`, no `refD2`. `2sr=4 ≡ 0`, `a=1`. `refH`: `(r,c)->(1-r, c)`. `(0,1)->(1,1)`, `(0,2)->(1,2)` off-grid → image ≠ S. `2sc=8 ≡ 0`, `b=2`. `refV`: `(r,c)->(r, 2-c)`. `(0,1)->(0,1)`, `(0,2)->(0,0)` off-grid → image ≠ S. `rot180`: `2sr ≡ 0`, `2sc ≡ 0`, `a=1, b=2`. `(r,c)->(1-r, 2-c)`. `(0,1)->(1,1)`, `(0,2)->(1,0)`, `(1,0)->(0,2)`, `(1,1)->(0,1)`. Image = S. Fixed = `{}` — 0 cells. So `group = {rot180: {}}`, `capitol_of` returns `None` (0 ≠ 1). Correct. **No finding.**

### B63 | `tests/test_rules.py`, `test_legal_states_without_capitol` — `SQUARE4 = {(0,0),(0,1),(1,0),(1,1)}`. `sr=2, sc=2, n=4`. `sr-sc=0 ≡ 0`, `k1=0`. `refD1`: `(r,c)->(c, r)`. `(0,0)->(0,0)`, `(0,1)->(1,0)`, `(1,0)->(0,1)`, `(1,1)->(1,1)`. Image = S. Fixed = `{(0,0),(1,1)}` — 2 cells. `sr+sc=4 ≡ 0`, `k2=1`. `refD2`: `(r,c)->(1-c, 1-r)`. `(0,0)->(1,1)`, `(0,1)->(0,1)`, `(1,0)->(1,0)`, `(1,1)->(0,0)`. Image = S. Fixed = `{(0,1),(1,0)}` — 2 cells. `2sr=4 ≡ 0`, `a=1`. `refH`: `(r,c)->(1-r, c)`. `(0,0)->(1,0)`, `(0,1)->(1,1)`, `(1,0)->(0,0)`, `(1,1)->(0,1)`. Image = S. Fixed = `{}` — 0 cells. `2sc=4 ≡ 0`, `b=1`. `refV`: `(r,c)->(r, 1-c)`. Image = S. Fixed = `{}`. `rot180`: `(r,c)->(1-r, 1-c)`. Image = S. Fixed = `{}`. `rot90`: `sr-sc ≡ 0`, `sr+sc ≡ 0`, `k1=0, k2=1`. `(r,c)->(c, 1-r)`. `(0,0)->(0,1)`, `(0,1)->(1,1)`, `(1,0)->(0,0)`, `(1,1)->(1,0)`. Image = S. Fixed = `{}`. `rot270`: `(r,c)->(1-c, r)`. Image = S. Fixed = `{}`. So `group` has 7 elements, several fixing 0 or 2 cells. `capitol_of` returns `None`. Correct. **No finding.**

### B64 | `tests/test_rules.py`, `test_L_tetromino_is_not_a_state` — `L_TETROMINO = {(0,0),(1,0),(2,0),(2,1)}`. `sr=5, sc=1, n=4`. `sr-sc=4 ≡ 0`, `k1=1`. `refD1`: `(r,c)->(c+1, r-1)`. `(0,0)->(1,-1)` off-grid → image ≠ S. `sr+sc=6 ≢ 0`, no `refD2`. `2sr=10 ≢ 0`, no `refH`. `2sc=2 ≢ 0`, no `refV`. `rot180`: `2sr ≢ 0`, no. `rot90`: `sr-sc ≡ 0` but `sr+sc ≢ 0`, no. So `group = {}`. Correct. **No finding.**

### B65 | `tests/test_rules.py`, `test_connectivity_is_orthogonal_only` — `connected({(0,0),(1,1)})` is False. Correct. **No finding.**

### B66 | `tests/test_rules.py`, `test_shape_key_normalises_translation` — `shape_key({(2,2),(2,3),(3,2)})` = `((0,0),(0,1),(1,0))`; `shape_key({(0,0),(0,1),(1,0)})` = same. Correct. **No finding.**

### B67 | `tests/test_rules.py`, `TestLabelMatrixRoundTrip.test_roundtrip` — `states = [{(0,0),(0,1)}, {(1,0)}, {(1,1),(2,0)}, {(2,1)}]`. `label_matrix` gives a 3x2 matrix. `partition_of` returns the states in label order. `sorted(map(sorted, back))` vs `sorted(map(sorted, states))`. Correct. **No finding.**

### B68 | `tests/test_lemmas.py`, `TestL3_needs_the_neighbour_qualifier` — `Puzzle([{(0,0)}, {(0,1),(0,2)}])`. `d[0] = [0,1,3]`. Let me verify: capitol at `(0,0)`. `d(0,0)=0`. `d(0,1)`: step from `(0,0)` to `(0,1)` is between states 0 (size 1) and 1 (size 2), cost `min(1,2)=1`. So `d(0,1)=1`. `d(0,2)`: from `(0,1)` to `(0,2)` is inside state 1, cost 2. So `d(0,2)=1+2=3`. Correct. **No finding.**

### B69 | `tests/test_lemmas.py`, `TestE1EqualityIsNotATheorem` — `Puzzle([{(0,0)}, {(0,1),(1,0),(1,1)}])`. `capitol_of({(0,1),(1,0),(1,1)})` = `(1,1)`. Let me verify: `sr=2, sc=2, n=3`. `sr-sc=0 ≡ 0`, `k1=0`. `refD1`: `(r,c)->(c, r)`. `(0,1)->(1,0)`, `(1,0)->(0,1)`, `(1,1)->(1,1)`. Image = S. Fixed = `{(1,1)}`. `sr+sc=4 ≢ 0`, no `refD2`. `2sr=4 ≢ 0`, no `refH`. `2sc=4 ≢ 0`, no `refV`. `rot180`: `2sr ≢ 0`, no. `rot90`: `sr-sc ≡ 0` but `sr+sc ≢ 0`, no. So `group = {refD1: {(1,1)}}`, `capitol_of` returns `(1,1)`. Correct. `d(0,1)`: from `(0,1)` to `(0,0)` is between states 1 (size 3) and 0 (size 1), cost `min(3,1)=1`. So `d(0,1)=1`. `step_cost((0,1),(1,1))` is inside state 1, cost 3. Correct. **No finding.**

### B70 | `tests/test_lemmas.py`, `TestD53ManhPruneIsUnsound` — `EXAMPLE_STATES` is the 5x5 example. `self.revealed = {(4,4)}` (0-based `(5,5)`). `x = (1,3)` (0-based `(2,4)`). `d[1][3] = 3`. `min manhattan to (4,4)` = `|1-4| + |3-4| = 4 > 3`. `has_capitol_at((2,3))` — `(2,3)` 0-based is `(3,4)` 1-based, which is a capitol. Correct. **No finding.**

### B71 | `tests/test_lemmas.py`, `TestM4DominantState.test_on_the_official_example` — `foreign_capitol_violations(puz, d) == []`. The docstring says `(0,4)` has `d=17 > 12.5` but is adjacent to no capitol. `high_d_cells` returns cells with `2*d > 25`, i.e. `d > 12.5`, i.e. `d >= 13`. `d[0][4]=17`, `d[4][0]=25`, `d[4][1]=14`, `d[4][2]=13`, `d[3][0]=14`. So `high_d_cells` is non-empty. Correct. **No finding.**

### B72 | `tests/test_lemmas.py`, `TestHittingSetNumbers.test_numbers` — reads `data/puzzles/official-11x11/puzzle.json`. The test asserts `rep["hints"] == 33`, `len(rep["revealed_capitols"]) == 2`, `rep["satisfied_by_revealed"] == 22`, `rep["uncovered_demands"] == 9`, `rep["candidate_pool"] == 64`, `rep["min_additional_capitols"] == 4`, `rep["n_minimum_sets"] == 120`, `rep["total_capitols_lower_bound"] == 6`. The exact demand list is pinned. **No finding** for the tested case, but see B30 (the D64 singleton constraint is not applied).

### B73 | `tests/test_regression.py`, `TestOfficialExample.test_capitols_exactly` — `sorted((r+1,c+1) for (r,c) in self.puz.capitols.values())` = `[(3,2),(3,4),(5,5)]`. Correct. **No finding.**

### B74 | `tests/test_regression.py`, `TestOfficialExample.test_2x2_state_has_no_capitol` — `self.puz.sizes[1] == 4` and `1 not in self.puz.capitols`. The 2x2 state is label 1 in `EXAMPLE_STATES`. Correct. **No finding.**

### B75 | `tests/test_regression.py`, `TestOfficialExample.test_published_numbers_reproduced` — `PUBLISHED` has 10 entries. `d[0][0]=12`, `d[0][4]=17`, `d[1][0]=8`, `d[1][2]=6`, `d[1][3]=3`, `d[3][1]=7`, `d[3][2]=6`, `d[3][4]=10`, `d[4][0]=25`, `d[4][4]=0`. Correct. **No finding.**

### B76 | `tests/test_regression.py`, `TestOfficialExample.test_row_sums_and_answer` — `row_sums() == [37,29,31,43,55]`, `answer() == 8045`. `37^2+29^2+31^2+43^2+55^2 = 1369+841+961+1849+3025 = 8045`. Correct. **No finding.**

### B77 | `tests/test_regression.py`, `TestOfficialExample.test_checksum_invariant` — `sum_row_sums == 195`. `37+29+31+43+55 = 195`. Correct. **No finding.**

### B78 | `tests/test_regression.py`, `TestFixturesAgreeWithTheEngine.test_official_example_fixture` — reads `data/puzzles/official-example-5x5/truth.json`. The test asserts `puz.answer() == t["answer"]`, etc. **No finding** for the tested case.

### B79 | `tests/test_regression.py`, `TestFixturesAgreeWithTheEngine.test_counterexample_fixture_gives_two_answers` — reads `data/puzzles/counterexample-4x4-two-answers/truth.json`. Asserts `answers == [304, 112]` and `dfs[0] == dfs[1]`. **No finding** for the tested case.

### B80 | `tests/test_regression.py`, `TestFixturesAgreeWithTheEngine.test_11x11_numbers_are_consistent` — reads `data/puzzles/official-11x11/puzzle.json`. Asserts `zeros == [(5,7),(10,5)]`. **No finding** for the tested case.

### B81 | `tests/test_enumerate.py`, `TestCatalogue4x4.test_catalogue_constants` — `capitol_states == 280`. The spec does not give this number, but it is consistent with `N4_BY_CAPITOLS`. **No finding.**

### B82 | `tests/test_enumerate.py`, `TestOddSizeCapitolRule.test_every_capitol_state_has_odd_size` — iterates `cat.states` and checks `size % 2 == 1` for capitol-bearing states. The spec's rule 6 says "Only odd-sized states can carry a capitol". Correct. **No finding.**

### B83 | `tests/test_enumerate.py`, `TestConnectedSubsetEnumeration.test_counts` — `len(connected_subsets(3)) == 218`. The number of connected subsets of a 3x3 grid is 218. Correct. **No finding.**

### B84 | `tests/test_enumerate.py`, `TestConnectedSubsetEnumeration.test_no_duplicates` — `len(subs) == len(set(subs))`. Correct. **No finding.**

### B85 | `tests/test_enumerate.py`, `TestCatalogue4x4.test_tilings_and_breakdowns` — `res["tilings"] == 562308`, `res["tilings_by_blocks"] == N4_BY_BLOCKS`, `res["tilings_by_capitols"] == N4_BY_CAPITOLS`. Correct. **No finding.**

### B86 | `tests/test_enumerate.py`, `TestCatalogue4x4.test_15_capitols_impossible` — `assertNotIn(15, ...)`, `assertIn(16, ...)`. Correct. **No finding.**

---

## MAJOR

### M1 | `src/rules.py`, `symmetry_group` — the rot90/rot270 guard is `(sr-sc)%n==0 and (sr+sc)%n==0`, which is the *lattice-centroid* condition only when `n` is odd; for even `n` it also fires for cell-centre centroids, and the map is correct there. But the guard is **not** the condition "the centroid is a lattice point or a cell centre". For even `n`, a centroid at `(sr/n, sc/n)` with `sr ≡ n/2 (mod n)` and `sc ≡ n/2 (mod n)` is a cell centre, and the guard fires. For even `n`, a centroid with `sr ≡ 0` and `sc ≡ n/2` is a *midpoint of a cell edge*, and the guard does **not** fire (`sr-sc ≡ -n/2 ≢ 0`). A 90° rotation about a cell-edge midpoint is not a lattice symmetry of the square grid (it maps the grid to a shifted grid), so not firing is correct. **So the guard is correct.** I withdraw M1. The only real rot90 bug is in `grow.py` (B13).

### M2 | `src/hitting.py`, `min_hitting_set` — empty candidate list crashes `capitol_lower_bound`

```python
def min_hitting_set(demands):
    best = [None, []]
    def rec(chosen, covered):
        ...
        i = min(unc, key=...)
        for c in demands[i][3]:
            ...
    rec([], set())
    return best[0], best[1]
```

If `demands[i][3] == []` for some `i`, the `for` loop body never runs, `rec` returns, `best[0]` stays `None`, and `capitol_lower_bound` does `len([...]) + size` → `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'`. Demonstration:

```python
from hitting import capitol_lower_bound
capitol_lower_bound(1, {(0,0): 1})   # n=1, no neighbours -> empty candidates
```

Fix: `if not demands[i][3]: return` (infeasible) or raise a clear error.

### M3 | `src/hitting.py`, `split_demands` / `singleton_candidates` — the D64 singleton constraint is documented but never applied

`split_demands` returns `(x, v, radius, candidates)` and `min_hitting_set` treats every candidate as an ordinary cell. `singleton_candidates` computes the forced 1x1 hosts but is **never called**. The docstring of `split_demands` says "it has to travel with the demand into the solver", and the spec's rule 8 is about the step-count bound, not the singleton constraint — but the code's own docstring is contradicted by the code. Fix: either call `singleton_candidates` and intersect, or delete the dead function and the claim.

### M4 | `src/enumerate.py`, `Catalogue.__new__`/`__init__` — cache poisoning on exception

`_CATALOGUE_CACHE[n] = obj` is set before `__init__` completes. If `__init__` raises after `self._built = True`, the cache holds a broken object. Fix: build into a local, then insert into the cache at the end of `__init__`, or use a `try/except` that deletes the cache entry.

### M5 | `src/cost.py`, `Puzzle.__init__` — no validation that the states partition a rectangle

`owner` is `-1` for uncovered cells, and `step_cost` does `self.sizes[-1]` → `KeyError`. Fix: validate `all(owner[r][c] != -1 for r,c)` and that the union is the full `h x w` rectangle, or raise a clear error.

### M6 | `src/enumerate.py`, `count_tilings` — the DP is exponential in `n^2` and cannot reach 11x11

`memo` is keyed on `rem` (a bitmask of `n^2` bits). For `n=11`, `2^121` masks. The 4x4 case is `2^16 = 65536`, fine. The 11x11 target is not reachable by this DP. The spec says "the real target" is 11x11. Fix: this is a research-scale problem; the DP must be replaced by a smarter search (e.g. the `grow.py` orbit search with pruning), or the 11x11 instance must be solved by a different method.

### M7 | `src/enumerate.py`, `count_k` — no `k < 0` guard

`count_k(rem, k)` with `k=0` and `rem != 0` recurses to `k=-1, -2, ...` until `rem==0`. For 4x4 this is bounded by the memo, but for larger `n` it is a performance trap. Fix: `if k < 0: return 0` at the top.

### M8 | `src/grow.py`, `symmetry_choices` — the `rot90` map is wrong (see B13)

The map `(r,c) -> (c + i - j, r + j - i)` is not a 90° rotation about `(i+0.5, j+0.5)`. The correct map is `(r,c) -> (i + j + 1 - c, j + r - i)`. Demonstration:

```python
from grow import symmetry_choices
s = [x for x in symmetry_choices(3) if x.name == "rot90" and x.params == (0,1)][0]
print(s.apply((0,0)))   # code: (-1, 1)  -- off-grid
# correct: (2, 1)
```

`Symmetry.orbit` then raises `KeyError` on `(-1,1)`. Fix: `rr, cc = i + j + 1 - c, j + r - i`.

### M9 | `src/grow.py`, `symmetry_choices` — `rot270` is built from the broken `rot90`, so it is the *correct* rot270 but not the inverse of the code's rot90

`rot270` is `(r,c) -> (b - cc, a - rr)` where `(rr,cc) = rot90(r,c)`. With the broken rot90, `rot270(r,c) = (2j+1 - (c+i-j), 2i+1 - (r+j-i)) = (i+j+1-c, i+j+1-r)`. That is the correct rot270 about `(i+0.5, j+0.5)`. So `rot90` and `rot270` are not inverses. Fix: fix `rot90` (M8); `rot270` will then be correct.

### M10 | `src/grow.py`, `grow_states` — `newfront` may contain cells already in `newmask`

```python
newfront = {y for y in frontier if y != x}
for y in newmask:
    for nb in ...:
        if ... and nb not in newmask:
            newfront.add(nb)
```

The first line removes only `x`, not all of `newmask`. So `newfront` can contain cells in `newmask`. The `expand` loop skips them via `if o & mask: continue`, so it is harmless, but it is a performance trap. Fix: `newfront = {y for y in frontier if y not in newmask}`.

### M11 | `src/grow.py`, `grow_states` — `seen` is a `set` of `frozenset`s, and `expand` is recursive; for 11x11 the number of connected orbit-unions can be large

No bound on recursion depth or on `results` size. Fix: add a size cap or an iterative version.

### M12 | `src/hitting.py`, `packing_bound` — dead code

Never called. The docstring says it is a "rigorous lower bound", but `capitol_lower_bound` uses `min_hitting_set` instead. Fix: call it or delete it.

### M13 | `src/hitting.py`, `weighted_demand_order` — dead code

Never called. Fix: call it or delete it.

### M14 | `src/enumerate.py`, `Catalogue._has_capitol` — dead code

Never called. Fix: delete it.

### M15 | `src/rules.py`, `symmetry_group` — the `try/except` around `fn(r,c)` is dead code

`fn` is a pure integer lambda. Fix: delete the `try/except`.

### M16 | `src/rules.py`, `partition_of` — non-contiguous labels are silently renumbered

`buckets.setdefault(lab, set())` then `sorted(buckets.items())` returns states in label order, but `states[i]` is not the state labelled `i` if labels are non-contiguous. `Puzzle` renumbers anyway, so this is only a problem for callers that index by label. Fix: document or assert contiguity.

### M17 | `src/rules.py`, `shape_key` — `min` on an empty iterable raises

`shape_key([])` raises `ValueError`. Fix: return `()` for empty input.

### M18 | `src/cost.py`, `Puzzle.cost_field` — no caching

Repeated calls recompute the multi-source Dijkstra. Fix: cache the result.

### M19 | `src/cost.py`, `is_metric` — `O((hw)^2)` and calls `puz.dist` inside the double loop

For 11x11 this is `14641^2 ≈ 2.1e8` operations. Fix: precompute all `dist` grids once.

### M20 | `tests/test_lemmas.py`, `random_partition` — the placeholder loop is dead code

```python
for m in range(1, 1 << (n * n)):
    pass  # placeholder to keep the loop cheap; legal states are generated below
```

Fix: delete it.

---

## MINOR

### m1 | `src/cost.py`, `INF = float("inf")` — the spec's rule 1 says "NO FLOATING POINT anywhere in the symmetry test". `INF` is not in the symmetry test, so it is allowed, but `d` is a float and `check_L1` uses `1e-9` tolerances. For integer costs these tolerances are unnecessary. Fix: use `None` or a large integer sentinel.

### m2 | `src/cost.py`, `check_L1` — `abs(d[y] - (d[x] - w)) < 1e-9` is exact for integers; the tolerance is dead.

### m3 | `src/cost.py`, `check_L2` — `abs(d[x] - d[y]) > lim + 1e-9`; same.

### m4 | `src/cost.py`, `check_L3` — `sizes[owner[x]] < abs(d[x] - d[y]) - 1e-9`; same.

### m5 | `src/cost.py`, `is_metric` — `abs(D[rr][cc] - back[r][c]) > 1e-9`; same.

### m6 | `src/hitting.py`, `weighted_demand_order` — `1.0 / max(1, d[2]) ** 2` is a float; the spec's rule 1 is about the symmetry test, so allowed, but the function is dead anyway.

### m7 | `src/enumerate.py`, `main` — `print(f"... {cat.seconds:.1f}s")` uses a float format; fine.

### m8 | `src/grow.py`, `Symmetry.__repr__` — `# pragma: no cover - debug aid`; fine.

### m9 | `src/rules.py`, `NON_IDENTITY` — defined but never used. Fix: delete or use.

### m10 | `src/rules.py`, `state_size` — `len(set(cells))`; fine.

### m11 | `src/rules.py`, `is_capitol_bearing` — `capitol_of(cells) is not None`; fine.

### m12 | `src/rules.py`, `label_matrix` — `h = max(..., default=-1) + 1`; fine.

### m13 | `tests/test_lemmas.py`, `TestM4DominantState.test_same_state_capitol_is_allowed` — the final `assertEqual(foreign_capitol_violations(Puzzle(parts), d), [])` uses `parts`/`d` from the found case; correct but fragile.

### m14 | `tests/test_regression.py`, `PUBLISHED` — 10 entries; the full field is checked separately. Fine.

### m15 | `tests/test_enumerate.py`, `N4_LEGAL_WITH_CAPITOL = 280` — not in the spec's list; consistent with `N4_BY_CAPITOLS`. Fine.

---

## VERDICT

**DO NOT SHIP** — 2 BLOCKER (`grow.py` rot90/rot270, `enumerate.py` 11x11 DP infeasibility) and 20 MAJOR findings.

---

## THE THREE HIGHEST-VALUE TESTS THAT ARE STILL MISSING

1. **`grow.py` rot90 correctness** — assert that `symmetry_choices(3)` contains a `rot90` with `params == (0,1)` whose `apply((0,0)) == (2,1)` and whose `orbit((0,0))` is a 4-cycle within the grid. This would have caught B13/M8.

2. **`hitting.min_hitting_set` with an empty candidate list** — `assertRaises` or `assertEqual(capitol_lower_bound(1, {(0,0): 1})["min_additional_capitols"], 0)`. This would have caught M2.

3. **`Puzzle` with a non-rectangular or holed partition** — `with self.assertRaises(ValueError): Puzzle([{(0,0)}, {(1,1)}])` (disconnected bounding box) and `with self.assertRaises(ValueError): Puzzle([{(0,0),(0,1),(1,0)}])` (missing `(1,1)`). This would have caught M5.