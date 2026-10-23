# 07-glm-code-review — CODE REVIEW

- model: `~z-ai/glm-flash-latest`
- finish_reason: stop
- usage: {"prompt_tokens": 19561, "completion_tokens": 25919, "total_tokens": 45480, "cost": 0.006631314, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.006631314, "upstream_inference_prompt_cost": 0.001447514, "upstream_inference_completions_cost": 0.0051838}, "completion_tokens_details": {"reasoning_tokens": 23303, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 9017 reasoning_chars: 0

---

## REVIEW

# Review

## BLOCKERS

**B1 | src/grow.py, `symmetry_choices` rot90/rot270 (the `dx, dy` block) — the "rot90" map is not a rotation.**
Code: `(r,c) -> (c+i-j, r+j-i)`. Apply it twice:
`(r,c) -> (c+i-j, r+j-i) -> (r+2(i-j), c+2(j-i))` — a **translation**, not rot180. A 90° rotation squared is rot180; therefore this map is not a rotation at all (it is the reflection `r-c = i-j`, i.e. a duplicate of `refD1`). The rot270 entry `(b-cc, a-rr) = (i+j+1-r, i+j+1-c)` is exactly **rot180 about (i+0.5, j+0.5)** — another duplicate. The correct rot90 about cell centre (i,j) is `(r,c) -> (c+i-j, i+j-r)` (rules.py has it right: `(c+k1, k2-r)`); rot270 is `(i+j-c, r+j-i)`. The second component's sign on `r` is wrong.
Consequence: `grow_states` can never grow a genuinely rot90-symmetric state (e.g. the 2×2 square, whose rot90 centre (0.5,0.5) is additionally excluded by the `i+j % 2 == 0: continue` filter, which is unjustified — every cell centre (i+0.5, j+0.5) is a valid rot90 centre). Demonstration:

```python
from grow import symmetry_choices
s = [x for x in symmetry_choices(4) if x.name == "rot90" and x.params == (1, 2)][0]
m = s._map
assert m[m[(0, 0)]] != (0, 0)          # a rot90 must square to rot180, not translate
# m[(0,0)] == (-1, 1); m is refD1-type, order 2, and not closed on the grid
```

**B2 | src/grow.py, `symmetry_choices` — half the symmetry classes are missing, and the ones offered are not bijections of the grid.**
- `refH`/`refV` are offered only through **integer** lines (`2*i - r`), i.e. grid lines. The half-integer axes `r = i+0.5` (through cell-centre rows), which rules.py's `(2*sr)%n` congruence correctly covers, are absent.
- `rot180` is offered only about **(odd, odd)** doubled centres `(2i+1, 2j+1)`. Mixed-parity centres exist: the vertical domino `{(0,0),(1,0)}` has centroid (0.5, 0) and rot180 map `(r,c)->(1-r, -c)` — not offered.
- Worse, the offered boundary-anchored maps are not permutations of the grid: `refH` with `i=0` maps `(1,c) -> (-1,c)`, which is not a key of `_map`, so `Symmetry.orbit` raises `KeyError` on the second hop (and `refD1` with `k=-(n-1)` likewise). Concrete failure:

```python
from grow import symmetry_choices, orbits_of
s = [x for x in symmetry_choices(3) if x.name == "refH" and x.params == (0,)][0]
orbits_of(s, 3)        # KeyError: (-1, 0)  — the map leaves the grid
```

Net effect: a state whose *only* symmetry is a half-integer-axis reflection or a mixed-parity rot180 (the vertical domino is the smallest example) cannot be produced by `grow_states` at all. Fix: derive the symmetry candidates from the same integer centroid congruences as `rules.symmetry_group`, and represent each symmetry as a map on the *state's* cells (images may leave the grid only for cells outside the state), not as a total grid permutation.

**B3 | tests/ — grow.py has zero test coverage.** Both blockers above are invisible to CI: no test file imports `grow`. Any module labelled "AODFS state growth" that is the solver's engine and has no truth-table test (compare each `Symmetry` map against `rules.symmetry_group` on known shapes) is a shipping hazard.

## MAJORS

**M1 | src/hitting.py, `min_hitting_set` / `capitol_lower_bound` — crash instead of "infeasible".**
If any demand has an empty candidate list (or the demands are jointly unhittable), `rec` returns without ever setting `best[0]`, so `min_hitting_set` returns `(None, [])` and `capitol_lower_bound` dies on `len(...) + size` (`TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'`). Demonstration:

```python
from hitting import capitol_lower_bound
hints = {(0, 0): 1, (0, 1): 2, (1, 0): 2}   # v=1 hint whose whole ball consists of hints
capitol_lower_bound(3, hints)               # TypeError; must report infeasibility instead
```

Fix: return an explicit "infeasible" status when a demand has no candidates or the search exhausts without a solution.

**M2 | src/cost.py — Rule 5 and partition validity are enforced nowhere.**
`cost_field()` silently returns an all-INF grid for a capitol-less partition (rule 5: such a partition "is not a solution"), and `Puzzle.__init__` performs no validation: overlapping states or uncovered cells leave `owner[r][c] == -1`, and `step_cost`/`row_sums` then fail with `KeyError` on `sizes[-1]` (or worse, `sizes[-1]` silently returns the *last* state's size — Python negative indexing — giving a wrong answer rather than a crash when the label −1 cell is only read, e.g. in `row_sums`). Demonstration:

```python
from cost import Puzzle
p = Puzzle([[(0, 0), (0, 1)], [(0, 1)]])   # overlapping cells, cell (1,0) uncovered
p.row_sums()                               # KeyError or silently wrong via sizes[-1]
```

Fix: validate coverage + disjointness in `__init__`; raise/flag when `cost_field` is undefined.

**M3 | src/enumerate.py — the design cannot reach the stated 11×11 target.**
`connected_subsets` materialises **every** connected induced subgraph as a Python int in a list. The count grows ~×5.5 per size (3×3: 218, 4×4: 11,506 ⇒ 11×11 is of order 10¹⁰–10¹¹ masks); both the enumeration time and the list memory are infeasible, and `Catalogue.__init__` additionally runs `symmetry_group` on each and stores `by_cell` index. The 11×11 instance — the real target — is unreachable with this architecture; a per-cell orbit/DP growth (or the fixed `grow.py`) with streaming counting is required. This should at minimum be documented as a hard scaling wall, not left to be discovered.

**M4 | src/hitting.py — documented machinery does not exist; three functions are dead code.**
`split_demands`'s docstring (PLAN D64) promises the v=1 "must be a singleton state" constraint "travels with the demand into the solver" — it does not: the returned demand tuples carry no singleton flag, and `singleton_candidates`, `weighted_demand_order`, and `packing_bound` are called from nowhere. The shipped lower bound is therefore weaker than the module claims, and `packing_bound`'s careful LP note describes a bound that is never computed.

## MINORS

- src/enumerate.py — module named `enumerate` shadows the builtin; any future use of `enumerate(...)` inside it or in importers of `from enumerate import *` breaks silently.
- src/cost.py `is_metric` — verifies the triangle inequality only for length-2 paths via two adjacencies; the docstring's "genuine metric" claim is far stronger than what is checked.
- src/cost.py — `check_L3` is strictly implied by `check_L2` (`min(sx,sy) ≤ sx`); one of the two is redundant.
- tests/test_lemmas.py `random_partition` — dead placeholder loop `for m in range(1, 1 << (n*n)): pass`; and it can return capitol-less partitions, for which all four `check_L*` calls are vacuous (every cell is INF), so the "25 random partitions" can silently verify nothing.
- src/hitting.py `split_demands` — inconsistent tuple arity (satisfied: 3-tuples, uncovered: 4-tuples); any consumer iterating uniformly breaks.
- src/grow.py module docstring — the example "S = {(0,1),(1,0),(2,3),(3,2)} passes the rot90 row of the divisibility table" is false: sr−sc = −3 and −3 % 4 = 1 ≠ 0. Comment contradicts the math.
- src/enumerate.py `_has_capitol` — dead code by its own comment.
- Test gaps (category 3): no empty-grid, N=1, N=2-catalogue, or rectangular (h≠w) `Puzzle` test; no test that a capitol-less partition's cost field is all-INF and is rejected as a solution; no test that `symmetry_choices` maps agree with `rules.symmetry_group`.

Nothing found in: rules.py logic (symmetry congruences are complete over the valid lattice centres — cell centres and grid vertices for rot90 — and rule 4's explicit `image == S` verification is present), the ESU enumeration's canonicity (rule 11), the DP counters, or the cost-field/Dijkstra semantics (rules 7, 8, 10 are correctly implemented and tested).

## VERDICT

**DO NOT SHIP** — BLOCKER: 2 (grow.py rot90/rot270 maps; grow.py incomplete/non-bijective symmetry set), MAJOR: 4.

## Three highest-value missing tests

1. **Symmetry-map law test for grow.py** (kills B1+B2 immediately):
```python
for sym in symmetry_choices(5):
    if sym.name in ("rot90", "rot270"):
        assert all(sym.apply(sym.apply(sym.apply(sym.apply(c)))) == c for c in sym._map), sym
    assert set(sym._map.values()) == set(sym._map.keys())   # total permutation of the grid
assert any(grow_states((0, 0), s, 3) and {(0,0),(1,0)} in [frozenset(x) for x in grow_states((0,0), s, 3)]
           for s in symmetry_choices(3))   # vertical domino is growable
```
2. **Hitting-set infeasibility**: `assert capitol_lower_bound(3, {(0,0):1, (0,1):2, (1,0):2})` reports infeasibility (raises a dedicated exception or returns a status), and does not raise `TypeError`.
3. **Degenerate partitions**: `Puzzle([{(0,0),(0,1)}, {(1,0),(1,1)}])` (two dominoes, no capitol) → `cost_field()` is all INF **and** the pipeline classifies the partition as "not a solution"; plus `Catalogue(1)` gives `connected=1, legal=1, tilings=1` and `Catalogue(2)` tilings reproduce an independently computed constant.