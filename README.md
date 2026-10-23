# js-puzzle

Generator + solver for Jane Street's **"It's a Metric, Too"** (October 2026) family of puzzles:
subdivide an N×N frame into symmetric **states**, each state may have a **capitol**, and travel
costs depend on state sizes. The puzzle gives a few numbers (cost-to-nearest-capitol) and asks
for `sum(row_sums²)`.

> Status: **design + review complete, implementation starting (M1)**.
> No solver is released yet; the rule engine, data contract and verification tooling are.

---

## The puzzle family in one paragraph

* A **state** is a 4-connected set of squares with a non-trivial self-symmetry.
* A state's **capitol** is the square fixed by *every* non-trivial self-symmetry — but only if
  each of them fixes **exactly one** square. Otherwise the state has **no capitol**.
* Moving to an orthogonally adjacent square costs the state size (same state) or
  `min(sizeA, sizeB)` (across states).
* A number in a cell = the least total cost from that cell to **any** capitol.
* Answer = label each cell with its state size, sum per row, then sum the squares of row sums.

**Fully verified facts** (three independent parties: author, Verifier, DeepSeek-V4.1-Flash):
official 5×5 example → states of size 7/4/3/11, capitols at (3,2)/(3,4)/(5,5) (1-based),
the 2×2 state has **no** capitol, row sums `[37,29,31,43,55]`, answer **8,045**.

---

## Repository layout

```
PLAN.md                      the plan: what to build + acceptance criteria (D1–D59, V1–V26)
docs/DESIGN.md               design archive: routes explored, verdicts, math core, AODFS, trace transfer
docs/reviews/                all adversarial review rounds (5 independent rounds, 59 defects found)
src/                         implementation (M1: rules.py, cost.py ...)
tools/                       engine + verification + analysis scripts
data/puzzles/<id>/puzzle.json  puzzle input  (grid + hints + ingest provenance)
data/puzzles/<id>/truth.json   ground truth (states, sizes, capitols, d-field, row sums, answer)
data/schema/                 JSON Schema for both files
```

### Data contract (the only interchange format)

Pixels exist **only** at the ingest boundary. Everything downstream reads JSON.

* `grid[r][c]` = the hint value, or `null` for a blank cell (1-based hints in `hints[]`).
* `states[r][c]` = state label (0-based matrix); `state_sizes[k]` = cell count of label `k`.
* `state_capitol[k]` = `[row, col]` or `null`; `capitols` = the capitol cells of states that have one.
* Invariant: `capitols` == the set of cells where `d_field == 0`; `sum(row_sums) == sum(|S|²)`.

---

## Key results so far

| quantity | value |
|---|---|
| 4×4 legal state **types** / placements | 640 / 1,130 |
| 4×4 legal tilings (with ≥1 capitol) | 562,308 (559,585 alive) |
| 4×4 search tree | 1,300,765 nodes, root branching 377, avg branching 2.31 |
| 5×5 legal states / tilings | 22,317 / 2,638,025,192 (×19.7 per size step) |
| 11×11 legal states | ≈1.3×10¹² (extrapolated) → pre-enumeration infeasible |
| 11×11 capitol count | **≥ 6** (hitting-set lower bound, exact B&B) |
| 11×11 hints | 33 (machine-read from the official PNG, cross-checked 3 ways) |

### The theorems that matter

* **Only odd-sized states can have a capitol** (a symmetry fixing one square pairs up the rest).
* **`k = N²−1` capitols is impossible**; a capitol-free state has ≥2 cells.
* **The d-field does not determine the answer** — two different 4×4 partitions share the same
  16-value cost field but give answers 304 and 112 ⇒ uniqueness must be judged at the **answer** level.
* **The answer is invariant only under D2** (180°, and the two axis reflections) — 90° rotation
  changes it (official example: 8045 → 8029).
* **Capitol-adjacent step**: for a capitol `c` adjacent to `x`, `min(size_x, size_c) ≥ d(x)`
  (a **lower bound**; equality does *not* generally hold).

---

## Tooling in `tools/`

| script | purpose |
|---|---|
| `engine.py` | rule kernel — the **executable specification** (symmetry group, capitol rule, cost field) |
| `check_contract.py` | 63 data-contract assertions; exit code 0 = all green |
| `validate.py` | validate a candidate state partition against the published numbers |
| `shapes4x4.py` | 4×4 shape catalogue + tiling counts (three countings) |
| `tilings_by_capitols.py` | tilings stratified by number of capitols |
| `capitol_bound_11x11.py` | exact hitting-set lower bound on the 11×11 capitol count |
| `ambiguity_3x3.py` | "number of hints → candidate/answer count" curve |
| `tree_shape_4x4.py` | the search-tree shape (root branching, node counts) |
| `draw_tree_4x4.py` | renders the "where 562,308 comes from" figures |
| `render_4x4.py` | pixel-exact 4×4 three-panel figure |
| `ocr_11x11_v2.py`, `ocr_disambiguate.py` | pixel ingest of the official 11×11 (self-supervised glyph templates) |
| `run_openrouter_review.py` | multi-model adversarial review harness (OpenRouter) |
| `verify_reviews.py` | independently re-verifies claims made by reviewers |

Everything is **Python standard library only**.

---

## Reviewing with external models

```bash
python3 tools/run_openrouter_review.py "<model-id>" "<output-tag>"
```

Add `"reasoning": {"effort": "none"}` to get a **final verdict** instead of a reasoning trace
that runs out of budget (this is what makes DeepSeek/GLM actually answer).

---

## License

MIT (add a LICENSE file if you want to publish under one).
