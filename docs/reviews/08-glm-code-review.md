# 08-glm-code-review — CODE REVIEW

- model: `~z-ai/glm-flash-latest`
- finish_reason: stop
- usage: {"prompt_tokens": 29828, "completion_tokens": 28144, "total_tokens": 57972, "cost": 0.007836072, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.007836072, "upstream_inference_prompt_cost": 0.002207272, "upstream_inference_completions_cost": 0.0056288}, "completion_tokens_details": {"reasoning_tokens": 26243, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 7100 reasoning_chars: 0

---

## REVIEW

## Findings

**1. BLOCKER — `tilings.py` / `judge.py` / `generator.py`: the 11x11 target is unreachable by construction.**
`Catalogue.__init__` calls `connected_subsets(n)`, which materialises *every* connected subset of the frame (~10¹²+ for 11x11) and runs `symmetry_group` on each. `Judge.__init__` and `Generator.__init__` both build a `Catalogue`, and the judge's only non-table path is a DFS over all tilings; the table path requires `build_table` to first materialise *every* tiling in a Python list (`parts`). There is no code path that proves answer-uniqueness for 11x11. The hitting-set module works on hints alone, but the deliverable pipeline (generator → judge) cannot run on the real instance at all. Fix: the judge needs a hint-driven search with the sound UB/LB prunes over *locally grown* states (the AODFS machinery already exists in `grow.py`), not a precomputed catalogue of everything.

**2. MAJOR — `tilings.py`, `Catalogue`: the per-size cache is never written.**
`_CATALOGUE_CACHE` is read in `__new__` but nothing ever inserts into it, despite the comment "Cached per size" and the `__init__` guard that presumes it.

```python
from tilings import Catalogue
a = Catalogue(4); b = Catalogue(4)
print(a is b, a.seconds)   # False, rebuilt from scratch (~seconds each time)
```
The test suite constructs `Catalogue(4)` at least five times. Fix: `type(self)._CATALOGUE_CACHE[n] = self` at the end of a successful `__init__` (matching the comment's stated intent).

**3. MAJOR — `generator.py`, `hint_ladder`: the greedy is dead code and the docstring is false.**
`score = (res["cardinality"], -len(res["answers"]))` and `cardinality == len(answers)` always, so `score == (k, -k)`. Worse, `remaining` starts at the *irreducible* set, which already has cardinality 1; adding hints can only shrink the answer set, so cardinality is 1 at every step and the score is the constant `(1, -1)`. "each time choosing the one that helps most" never discriminates — the ladder order is just dict insertion order. Fix: score by `res["partitions"]` (number of consistent tilings), which does vary, or delete the selection logic and the claim.

**4. MAJOR — `judge.py`, `_ub_violates`: quadratic re-verification at every node.**
Each candidate state triggers `_capitol_of_mask` (a full `symmetry_group` recomputation) and `_path_cost_inside` (fresh BFS) for **every previously chosen state**, not just the new one `m`. Cost per node is O(|chosen| · (group computation + BFS)). On the search fallback (fresh clone, no table) this alone can eat the entire 2M-node budget. Fix: check only `m` (older states were already checked when they were appended), and precompute each catalogue state's capitol once (the mask→capitol table, not mask→bool).

**5. MAJOR — `judge.py` / `tiletable.py`: the cache is de facto the only source of truth, with no validation (rule 18).**
`load_table` trusts any existing `npz` blindly: no row-count cross-check against `Catalogue.count_tilings()`, no version/engine hash. A stale table (built by an older kernel) makes `decide` return `exhaustive: True` on wrong data — silently shipping non-unique puzzles. Conversely, on a clean clone (no table) the search fallback cannot finish inside any practical budget for n ≥ 5, so `make_puzzle` always raises. Fix: store `(n, kernel_hash, expected_tiling_count)` in the npz and verify on load; refuse to ship if the table is absent and the search is not exhaustive.

**6. MINOR — `cost.py`, `Puzzle.__init__`: overlapping states are accepted silently.**
Only holes are detected; overlaps silently overwrite `owner` (last label wins) and corrupt `sizes`.

```python
p = Puzzle([{(0, 0)}, {(0, 0), (0, 1)}])   # no error; owner[0][0] == 1, sizes {0:1, 1:2}
```
Fix: after filling `owner`, assert each cell was written exactly once.

**7. MINOR — `hitting.py`, `split_demands`: "satisfied" ignores rule 12 for d=1 demands.**
A d=1 demand is dropped as satisfied when *any* revealed capitol is within Manhattan radius 1 — but per rule 12 the server must be a 1x1 state, and a revealed capitol in a larger state cannot serve it. The lower bound stays valid (only weakened), but the reported `satisfied_by_revealed` count (the published "22") can be wrong. Fix: only mark v=1 demands satisfied if the revealed capitol can be a singleton, else keep the demand with the revealed cell excluded from candidates (as `singleton_candidates` already does).

**8. MINOR — `hitting.py`, `packing_bound`: O(2^m · m²) with no cap.**
Called unconditionally from `capitol_lower_bound`; with a dense hint set (m ≈ 30+) on 11x11 this explodes. Fix: cap m or use a greedy disjoint-packing.

**9. MINOR — dead code / misleading names.**
`rules.state_size`, `rules.is_capitol_bearing`, `Catalogue._has_capitol`, `grow_states`'s `blocked` parameter (no caller passes it), `hitting._combinations` (a pointless re-import wrapper). `is_metric` checks only ≤2-edge triangle paths — documented, but the name overstates what is verified.

**10. MINOR — test weaknesses.**
`test_generator.test_ladder_is_ordered_from_easy_to_hard`: `row["exhaustive"] if "exhaustive" in row else True` is vacuous (ladder rows never carry that key). `test_lemmas.TestM4.test_same_state_capitol_is_allowed` reads `parts`/`d` leaked from loop variables after the loops — brittle. `TestHittingSetNumbers` and `test_regression` fixtures error out (not skip) if the data files are missing.

**Edge cases not covered by any test:** N=1 (`Catalogue(1)`, answer for a single cell); the empty partition (`Puzzle([])` returns answer 0 with no error); a 1×N rectangular `Puzzle` (works in `cost.py`, unsupported in `Judge`/`Catalogue` — untested mismatch); a partition with no capitol anywhere at the `Puzzle` level (rule 5 — only the generator filters it, nothing tests `cost_field() == INF` everywhere); N=2 catalogue/tiling counts.

No logic bugs found in: `rules.symmetry_group`/`capitol_of` (integer congruences are the correct necessary conditions, explicit image check covers sufficiency, full-group quantification correct), the ESU enumeration, the exact-cover DP counters, the multi-source Dijkstra cost field, or the judge's UB/LB prunes (both verified sound against rules 7/8/10/15).

## VERDICT
**SHIP AFTER FIXES** — BLOCKER: 1, MAJOR: 4.

## Three highest-value missing tests

1. **Rule 5 end-to-end:** `Puzzle([{(0,0),(0,1)}, {(1,0),(1,1)}]).cost_field()` is all `INF`, and `Judge(2).decide({})` returns `cardinality == 0` and `unique is False` (a capitol-less partition is not a solution).
2. **Cache contract:** `Catalogue(4) is Catalogue(4)` is `True` (currently fails), and a corrupted/stale `tiling_table_4x4.npz` (e.g. row count ≠ `count_tilings()`) must make `Judge.decide` refuse the table instead of returning `exhaustive: True`.
3. **Rule 12 with a hostile revealed capitol:** a hint set containing a d=1 hint whose every neighbour is hinted and whose ball contains only a revealed non-singleton capitol — assert `split_demands` does **not** report it as satisfied and `min_hitting_set` reports infeasibility (or keeps the demand), not a silently reduced bound.