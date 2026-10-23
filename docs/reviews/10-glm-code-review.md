# 10-glm-code-review — CODE REVIEW

- model: `~z-ai/glm-flash-latest`
- finish_reason: stop
- usage: {"prompt_tokens": 35508, "completion_tokens": 26007, "total_tokens": 61515, "cost": 0.007828992, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.007828992, "upstream_inference_prompt_cost": 0.002627592, "upstream_inference_completions_cost": 0.0052014}, "completion_tokens_details": {"reasoning_tokens": 24034, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 7105 reasoning_chars: 0

---

## REVIEW

## Review

### BLOCKER

None found — the rule kernel (`rules.py`), the cost field, and the enumeration constants are correct against the spec and the published fixtures.

### MAJOR

**M1 | solver.py, `rec` start-of-state branch (~line "for s in self._syms") | the same tiling is enumerated once per symmetry of each state.**
A state grown under σ is a union of σ-orbits, hence σ-invariant; a state with k non-trivial symmetries is reachable from the same anchor under k different σ, producing the identical closed state and therefore the identical complete tiling. Concrete demo on the 2×2 corner:

```python
# anchor (0,0), state {(0,0),(0,1),(1,0),(1,1)}:
#   refD1 k=0: orbit{(0,0)} -> orbit{(0,1),(1,0)} -> orbit{(1,1)}   -> same square
#   refH  k=1: orbit{(0,0),(1,0)} -> orbit{(0,1),(1,1)}             -> same square
```
So `partitions` and `solutions` count/list duplicates and the node budget is multiplied by the group order (fatal on 11x11, where whole subtrees are re-explored). `unique` itself survives only because `answers` is a set — but a provably-unique puzzle can be reported `unknown` purely from the wasted budget. Judge's two paths are immune (catalogue / `cell_states` dedupe by mask/set); the solver is not. Fix: canonicalise the growth symmetry (e.g. grow only under the group element that is lexicographically smallest at which the state is a union of orbits, or dedupe closed states per anchor within a node).

**M2 | lazycatalogue.py, `cell_states` (raise) + judge.py lazy path | budget exhaustion crashes instead of reporting "unknown" (violates rule 21).**
`LazyCatalogue.cell_states` raises `RuntimeError` when `grow_states` sets `truncated`; `Judge.decide` calls it inside `rec` with no handler, so a tight budget aborts `decide` with an exception instead of returning `exhaustive: False`. Same crash propagates out of `Generator.make_puzzle`. Demo:

```python
from lazycatalogue import LazyCatalogue
LazyCatalogue(6, budget=1).cell_states((0,0))   # -> RuntimeError, not a partial result
```
Fix: catch/propagate a `truncated` flag; `Judge.decide` must return `{"exhaustive": False, "unique": False}`.

**M3 | judge.py `_lb_violates` and solver.py `_lb_violates` | the lower bound uses radius `v` instead of the codebase's own proven radius `⌊(v+1)/2⌋`.**
By the step-count lemma (hitting.py's derivation, rule 8) the *nearest* capitol of a hinted cell lies within Manhattan `⌊(v+1)/2⌋`, not merely `v`. The prune `best > v` is sound but far weaker than the sound `best > (v+1)//2` — and `hitting.split_demands` already uses the tight radius, so the two modules disagree. On 11x11 this is the difference between pruning and not pruning. Fix: `if best > (v + 1) // 2: return True` in both places.

**M4 | generator.py `worked_trace`, v==1 branch | candidates wrongly exclude revealed capitols, contradicting the code's own comment and `hitting.singleton_candidates`.**
The comment says "a hinted d=0 cell is a revealed capitol whose state may or may not be a singleton", but the filter `nb not in hinted` drops it anyway. `hitting.singleton_candidates` correctly uses `hints.get(nb, 0) <= 0`. Demo: a d=1 hint adjacent to a revealed capitol that *is* a 1x1 state — `worked_trace` reports an empty candidate list ("must be adjacent" with no candidates), which is a false statement in the shipped teaching material. Fix: use the same `hints.get(nb, 0) <= 0` predicate.

**M5 | judge.py + solver.py `_lb_violates` | O(#hints × N²) pure-Python bit scan at every node — the 11x11 perf trap.**
`min(row[cc] for cc in range(self.n*self.n) if (possible >> cc) & 1)` is ~121 iterations × 33 hints per node ≈ 4·10³ interpreted ops/node; at 10⁶–10⁷ nodes that is 10⁹–10¹⁰ ops. Fix: precompute per-hint candidate lists, maintain `possible` incrementally, or iterate `while poss: b = poss & -poss ...`. (Related, same functions: hinted cells with `v > 0` are never removed from `possible`, although `d=0 ⇔ capitol` means they can never host one — a free, sound strengthening.)

### MINOR

- **judge.py `decide`**: the *second* `if self._table is not None:` block is dead code (the first always returns or sets `_table = None`) — and it unpacks a 3-tuple into two names, so if it were ever reached it would `TypeError`. Delete it.
- **judge.py table path**: claims `exhaustive: True` while the table only stores capitol-bearing tilings; with empty/degenerate hint sets `partitions` undercounts. Also `n_tilings` is stored (rule 20's row-count cross-check) but never checked — a file truncated in *both* `fields` and `n_kept` passes.
- **lazycatalogue.py `__new__`**: a cached instance is returned for any `n`, silently ignoring different `max_cells`/`budget` arguments on later constructions.
- **generator.py `random_tiling` comment**: describes "sorted by size descending, picked uniformly among the first few" — the code actually samples with `1/len(s)²` weights. Comment contradicts code.
- **generator.py `__init__` comment / non-lazy branch**: `self.cat` is *always* a `LazyCatalogue`; the "small frames build the whole library once" branch merely pre-warms the lazy per-anchor cache. Misleading.
- **solver.py / judge.py**: no prune that a hinted `v == 0` cell must be its state's capitol (`_ub_violates` with `v=0` can never fire, since `cost < 0` is impossible). Sound but free pruning lost.
- **Rectangular / degenerate frames**: `Puzzle` handles h≠w, 1xN, and even the empty partition, but `Catalogue`, `Judge`, `Solver`, `Generator` hardcode n×n; no test covers `Puzzle([{(0,0)}])`, 1x2, 1x3, N=2, or a no-capitol partition's `cost_field` (all-INF) behaviour.
- **hitting.py `min_hitting_set`**: collects *all* optimal sets (`best[1].append`) — exponential memory in degenerate cases; only the count is used.

Categories with nothing to report: the DP counters in `tilings.py` (the ESU `higher`/`excl` invariants are correct — I verified the cross-sibling duplicate scenario is prevented by `excl` accumulating sibling anchors, and the memo keys are sound), and the hitting-set LP/packing commentary is accurate.

### VERDICT
**SHIP AFTER FIXES** — 0 BLOCKER, 5 MAJOR (M1–M5; M1/M3/M5 are the ones that decide whether 11x11 finishes at all).

### THE THREE HIGHEST-VALUE MISSING TESTS

1. **Solver counts each tiling once.** On a 3x3 (or 4x4 with a coarse budget) hint set:
   `assert Solver(3, hints).solve()["partitions"] == Judge(3, lazy=False).decide(hints)["partitions"]` — currently the solver overcounts whenever any state has ≥2 symmetries.
2. **Budget exhaustion is honest, not fatal.**
   `res = Judge(5, lazy=True).decide(full_hints, budget=10); assert res["exhaustive"] is False and res["unique"] is False` — currently raises `RuntimeError` out of `LazyCatalogue.cell_states`.
3. **d=1 demands may be served by a revealed capitol.** Construct a partition where a d=1 hint is adjacent to a revealed capitol that is a 1x1 state, then:
   `assert any(tuple(c) == revealed_cap for c in worked_trace_candidates)` and `assert revealed_cap in hitting.singleton_candidates(n, hints)[hint_cell]` — currently `worked_trace` returns `[]` while `hitting` returns the capitol.