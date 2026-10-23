# 11-glm-code-review — CODE REVIEW

- model: `~z-ai/glm-flash-latest`
- finish_reason: error
- usage: {"prompt_tokens": 36662, "completion_tokens": 11623, "total_tokens": 48285, "cost": 0, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.008909164, "upstream_inference_prompt_cost": 0.00439944, "upstream_inference_completions_cost": 0.004509724}, "completion_tokens_details": {"reasoning_tokens": 9779, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 7209 reasoning_chars: 0

---

## REVIEW

## FINDINGS

### BLOCKER 1 — judge.py, `rec` in `decide`
`if self._lb_violates(hints, new_possible):` — but the method is `def _lb_violates(self, possible: int)`. Every call on the **search path** raises `TypeError: _lb_violates() takes 2 positional arguments but 3 were given`. The whole non-table Judge is dead: any `Judge(n, use_table=False)` call, any stale-table fallback, and every `n >= 5` judgement (lazy ⇒ no table) crashes instead of returning a verdict. The solver.py copy is correct, so the crash is invisible as long as a fresh 4x4 table exists — exactly the silent-divergence scenario rules 20/21 were written to prevent.

Fix: `self._lb_violates(new_possible)`.

Demonstration:
```python
from judge import Judge
j = Judge(2, use_table=False)          # search path
j.decide({(0,0):0, (0,1):1, (1,0):1, (1,1):0})   # -> TypeError, not a verdict
```

### BLOCKER 2 — solver.py, close branch marks `closed_here` before the prune
```python
already_closed = cur in closed_here
if self._can_close(cur) and not already_closed:
    closed_here.add(cur)          # <-- marked BEFORE the lb check
    ...
    if not self._lb_violates(np):
        rec(...)
```
`closed_here` is shared across all symmetries of one anchor, but `possible` is symmetry-dependent (different `fixed` sets ⇒ different `np`). If set `S` is closable under sym σ₁ and the lb check fails there, `S` is marked closed, and the later σ₂ branch that reaches the *same frozenset* with a *passing* `np` is silently skipped (`already_closed`). The tiling is missed while the verdict still says `exhaustive: True` — a false uniqueness proof, the worst failure mode in this codebase.

Fix: move `closed_here.add(cur)` after the lb check passes (or key the set by `(cur, possible)`).

### MAJOR 3 — tiletable.py `rules_stamp` covers the wrong files
The stamp hashes only `rules.py, cost.py, tilings.py`. The table's *content* is produced by `tiletable.build_table` itself and depends on `grow.py`/`symmetry_choices` for nothing — but `cost.py`'s cost model and `rules.py` are not the only things that can change semantics: any edit to the enumeration in `tiletable.py` (e.g. the `_one_partition` capitol filter, or a future change to the exact-cover in `Catalogue`) leaves the stamp matching and a stale table answering `exhaustive: True`. Rule 20 requires the stamp to identify the rule engine; it identifies a subset of it. Fix: hash every file the table depends on, including `tiletable.py` and `tilings.py`'s `connected_subsets`.

### MAJOR 4 — the row-count cross-check (rule 20) is self-referential
`n_tilings` is written to the npz and **never read**. `judge.decide` validates `len(fields) == n_kept`, but `n_kept` is computed by the same build that produced `fields`, so a build truncated mid-way (worker crash, disk-full, manual tampering of rows *and* counters) passes the check and reports `exhaustive: True`. A real cross-check must compare `n_tilings` against an independent constant (the measured 562,308 for 4x4) or against a cheap recomputation of the tiling count. Fix: store the known per-size constant and verify `n_tilings == EXPECTED[n]` on load, or recompute `Catalogue(n).count_tilings()`.

### MAJOR 5 — LazyCatalogue cannot actually serve 11x11 (rule 19 is nominally met, rule 24 is not)
`LazyCatalogue.cell_states` calls `grow_states` with **no `prune` hook and no reading-driven constraint**: it enumerates *every* orbit-union of *every* symmetry containing the anchor up to 121 cells. `symmetry_choices(11)` emits ~34+34+21+21+1156+~578·2 ≈ 2400 symmetries; for a corner anchor the σ=symmetric-about-the-main-diagonal family alone is exponential. The 2M node budget will trip immediately, `TruncatedLibrary` is raised, and every Judge/Solver verdict on the real target becomes `unknown` — the scale-out goal is not met, it is just reported honestly. Fix: pass the hint-driven `prune` callback (the hook already exists in `grow_states`) into the catalogue, and pre-filter symmetries by whether the anchor's orbit even fits the remaining region.

### MINOR 6 — judge.py: dead second table block
The `if self._table is not None:` block after the first (which either returns or sets `self._table = None`) is unreachable; it also omits the `n_kept` check the first block performs. Delete it.

### MINOR 7 — generator.py `worked_trace`: dead variable
`hinted = {(r, c) for (r, c) in hints}` is computed and never used (and the tripled comment above the loop contradicts itself). Delete.

### MINOR 8 — lazycatalogue.py: cache ignores constructor parameters
`__new__` returns a cached instance; `__init__` then overwrites `self.budget`/`self.max_cells`, but `_cell_cache` entries were computed under the *first* instance's budget. A second `LazyCatalogue(11, budget=10**9)` silently reuses possibly-truncated-free but differently-scoped results. Key the cache on `(n, max_cells, budget)` or forbid divergent parameters.

### MINOR 9 — cost.py `is_metric` docstring understates cost
Per source it runs `puz.dist` for **every** cell, i.e. O((hw)·(hw log hw)) per source, O((hw)³ log) overall — not "O((hw)²) per source". The "do not call on the big instance" advice stands, but the stated complexity is wrong by a factor (hw).

### MINOR 10 — dead code
`rules.NON_IDENTITY` is never referenced. `Puzzle._dist_cache` grows without bound on repeated `dist()` calls (leaks on long solver runs). `grow_states`' frontier retains cells that became interior (skipped via `o & mask` each time) — quadratic-frontier drift on big growths.

### Categories with nothing to report
Symmetry test / capitol rule / cost field / DP counters / connected-subset enumeration: no logic bugs found beyond the above; the integer congruences, the full-point-group capitol rule, the ESU dedupe, and the exact-cover DP all check out against the stated constants.

### Untested edge cases
No test covers: N=1; rectangular (non-square) frames — `Puzzle` tolerates them but `Judge`/`Solver`/`Catalogue`/`grow` all hardcode n×n masks and will silently misbehave on an h≠w frame; empty hint dict through the search path; a partition whose *only* state is capitol-free fed to `Judge` (rule 5's "not a solution" branch in the search, not just `cost_field`).

---

## VERDICT
**DO NOT SHIP** — BLOCKER: 2, MAJOR: 3. The Judge search path crashes on every call, and the solver can report `exhaustive: True` while missing tilings.

## THE THREE HIGHEST-VALUE MISSING TESTS

1. **Judge search path agrees with the table path (kills BLOCKER 1).**
   `self.assertEqual(Judge(4, use_table=False).decide(HINTS_680, budget=400_000), Judge(4, use_table=True).decide(HINTS_680, budget=400_000))` — on the 4x4 fixture hints; today the left side raises TypeError.

2. **Solver exhaustiveness vs brute force on 3x3 (kills BLOCKER 2).**
   For ~20 random 3x3 hint sets: `Solver(3, hints).solve()["answers"]` must equal the answer set obtained by filtering all `Catalogue(3)` tilings through `Puzzle.cost_field` — set equality both directions, with `exhaustive == True`. Any missed-tiling bug (like the `closed_here` marking) shows up as a missing answer on the solver side.

3. **Stale/tampered table must never claim exhaustive (kills MAJORS 3–4).**
   Build a 4x4 table