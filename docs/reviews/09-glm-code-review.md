# 09-glm-code-review — CODE REVIEW

- model: `~z-ai/glm-flash-latest`
- finish_reason: stop
- usage: {"prompt_tokens": 31585, "completion_tokens": 12841, "total_tokens": 44426, "cost": 0.00490549, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.00490549, "upstream_inference_prompt_cost": 0.00233729, "upstream_inference_completions_cost": 0.0025682}, "completion_tokens_details": {"reasoning_tokens": 10562, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 8629 reasoning_chars: 0

---

## REVIEW

## Findings

### BLOCKER 1 — `judge.py` / `tiletable.py`: table path crashes on unpack
`load_table` returns a **3-tuple** `(fields, answers, n_tilings)`; `Judge.__init__` unpacks it into **2**:

```python
# tiletable.py, load_table
return d["fields"], d["answers"], int(d["n_tilings"]) if "n_tilings" in d else 0
# judge.py, __init__
self._table = load_table(n) if (use_table and not lazy) else None
...
fields, answers = self._table      # ValueError: too many values to unpack
```

Demonstration: build the 4x4 table (`python tiletable.py 4`), then `Judge(4).decide({})` raises `ValueError` before any query runs. The entire table accelerator is dead code as wired. Fix: `fields, answers, _ = self._table` (and see BLOCKER-adjacent MAJOR on `n_tilings` below).

### BLOCKER 2 — `lazycatalogue.py`: `cells_of` does not exist; the lazy judge (n ≥ 5, the 11x11 target) always crashes
`Judge` calls `self.cat.cells_of(mask)` in `_path_cost_inside` and in the leaf (`Puzzle([self.cat.cells_of(m) for m in chosen])`). `LazyCatalogue` — the object the judge actually holds when `lazy=True` (the default for n ≥ 5) — defines only `cell_states` and `stats`. The non-lazy branch in `_capitol_of_mask` guards on `self.lazy`, but these two call sites do not.

Demonstration:
```python
j = Judge(5)            # lazy by default
j.decide({(0,0): 0})    # AttributeError: 'LazyCatalogue' object has no attribute 'cells_of'
```
It crashes either at the first `_ub_violates` that finds a capitol, or at the first complete tiling reached. The scale-out path (rules 19/21) has never executed to completion. Fix: add `cells_of(mask)` to `LazyCatalogue` (row-major bit order, matching `_mask_of`).

### MAJOR 3 — `judge.py`/`tiletable.py`: rule 20's row-count cross-check is missing
`load_table` reads `n_tilings` and `decide` reports `exhaustive: True`, but nothing ever compares the stored row count against anything (the stored count, a recomputed count, or `len(fields)`). A truncated/corrupted table with a *correct* stamp (e.g. partially overwritten file, or a table built by a buggy builder that itself stamped honestly) still reports `exhaustive: True`. Rule 20 explicitly requires the row count to be cross-checked. Fix: at minimum assert `len(fields) <= n_tilings` and, for n ≤ 4, recompute the tiling count from `Catalogue(n).count_tilings()` and compare. Note also that `build_table` filters out capitol-less partitions, so `len(fields) < n_tilings` is legitimate — the check must be against the *expected kept-row* semantics, not naive equality; as written neither check exists.

### MAJOR 4 — `generator.py` `hint_ladder`: selection criterion is inverted relative to its own comment
The comment says "each time choosing the one that helps most", and the ladder is supposed to move from the irreducible (hardest) set back toward all hints. Adding a hint *helps* by shrinking the consistent-tiling count, so the most helpful hint is the one that **minimises** `res["partitions"]`. The code takes the **maximum**:

```python
score = (res["partitions"], res["cardinality"])
if best_score is None or score > best_score:
```

So at every rung the generator adds back the *least* informative hint first. Concrete: if hint A leaves 1 consistent tiling and hint B leaves 900, the code adds B. The ladder is still a valid ladder (cardinality stays 1 either way), but it is the opposite of the documented "helps most" ordering, and the produced teaching material is mis-ordered. Fix: `score < best_score`, or negate.

### MAJOR 5 — `grow.py`/`lazycatalogue.py`: per-anchor state generation is unbounded and massively redundant — 11x11 is infeasible
`symmetry_choices(11)` produces ~34+34+22+22+1089+~1200 ≈ 2400 symmetries (rot180 alone is 33² = 1089 anchors, most of which can never preserve an in-board state). `LazyCatalogue.cell_states` runs the **exponential** `grow_states` for *every* symmetry for *every* anchor, with no size cap on the states generated: for a central rot180 anchor the orbit count is ~60, so up to 2⁶⁰ orbit-unions are traversed per symmetry. Nothing prunes by "state size ≤ remaining frame budget" or dedups equivalent symmetries up front. This contradicts the intent of rule 19 (on-demand generation that scales) and makes rule 21's honest-budget search unreachable in practice: the judge will exhaust its node budget inside `cell_states`, not in the search. Fix: prefilter symmetries whose fixed set/orbit structure cannot fit in-board (e.g. rot180 centre must lie within the board's half-integer lattice intersected with the board's bounding box of relevance), cap orbit-union size, and share orbit tables across anchors.

### MINOR 6 — `generator.py` `random_tiling`: comment contradicts the code
"an unweighted pick would always take one of the largest shapes" — the list is sorted size-descending, but `rng.choices` unweighted is uniform over positions, not argmax. The weighting is a reasonable design choice; the justification is false. Fix the comment.

### MINOR 7 — `generator.py` `worked_trace` v==1: candidate list includes impossible cells
`SINGLETON_NEIGHBOUR` candidates are all in-board neighbours, including **hinted** cells. A hinted cell with v > 0 cannot be the singleton capitol (its own d would be 0), and a hinted v == 0 cell is a revealed capitol whose state may not be a singleton. The trace presents candidates the engine itself would reject. Fix: filter `nb not in hints` (as `hitting.singleton_candidates` already does).

### MINOR 8 — `hitting.py` `singleton_candidates`: excludes revealed capitols as servers
`nb not in hints` also excludes v == 0 hinted cells. A revealed capitol adjacent to a d == 1 hint *could* be the forced 1x1 state; excluding it makes the reported candidate list unsound as an "or" list. (`split_demands` would mark such a demand satisfied, but `singleton_demands` in `capitol_lower_bound` is emitted for **all** v == 1 hints, satisfied ones included, with the revealed cell wrongly absent.) Fix: exclude only cells with hint value > 0.

### MINOR 9 — `cost.py` `Puzzle.__init__`: overlapping states are accepted silently
Duplicate cells across states overwrite `owner` and double-count `sizes`; only *holes* are rejected. `Puzzle([{(0,0)},{(0,0),(0,1)}])` constructs without error (the `checksum` invariant would catch it, but nothing calls it automatically). Fix: assert every cell is claimed exactly once.

### MINOR 10 — dead / misleading code
- `judge.py`: `self._cell_of_bit` is built and never used.
- `tilings.py`: `Catalogue._has_capitol` is dead (its own docstring admits it).
- `grow.py`: `grow_states(..., blocked=...)` is never called with a non-empty `blocked` by any caller shown.
- `tests/test_grow.py::test_grown_states_are_connected_orbit_unions`: the name promises connectivity is checked; the body only checks sigma-invariance. Either rename or add `self.assertTrue(connected(st))` — note the *closure* filter lives in `LazyCatalogue`/`close_state`, so as written a disconnected grown set passes this test silently.

### Categories with nothing to report
- **Symmetry test / capitol rule (`rules.py`)**: no bugs found; the integer congruence conditions are the correct necessary filters, the image check supplies sufficiency, and the full-group capitol quantification is right (pinned by the BAR3 and green-L-tromino tests).
- **Cost field / DP counters (`cost.py`, `tilings.py`)**: no bugs found; multi-source Dijkstra, exact-cover memo, and the by-blocks/by-capitols DPs are correct, and the ESU enumeration is canonical.
- **Edge cases in the *tests***: nothing covers the empty grid / single-cell `Puzzle`, a 1x2 frame, a partition with no capitol at all reaching `cost_field` (returns all-INF — correct but untested), or non-square `h × w` frames (Puzzle supports them; Judge/Generator hard-code n×n).

## VERDICT
**DO NOT SHIP** — BLOCKER: 2, MAJOR: 3.

## The three highest-value missing tests
1. **Table path round-trip**: after `build_table(4)`, `Judge(4, use_table=True).decide(hints)` must return the identical `answers`/`cardinality`/`partitions` as `Judge(4, use_table=False).decide(hints)` for the official 5x5 hint set projected to 4x4 — this alone would have caught BLOCKER 1.
2. **Lazy judge end-to-end at n=5**: `Judge(5, lazy=True).decide(full_hint_set_of_a_known_5x5_puzzle, budget=10**6)` must return `exhaustive == True` and `cardinality == 1` without raising — this alone would have caught BLOCKER 2.
3. **Stale/truncated table rejection**: write a table file with a valid stamp but `n_tilings` = 1 (or half the rows), then `Judge(4).decide({})` must NOT report `exhaustive: True` — pins rule 20's row-count cross-check.