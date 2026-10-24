# The locality plan — many facets, small windows, and the questions left open

*This is the plan that came out of the (5,10) trim. It replaces nothing: it is the
"what do we do next, and how do we know it is working" document for the official 11×11.
Everything in it is measured, and every number has a tool behind it.*

| what | where | measured |
|---|---|---|
| the constraint register | `data/derived/constraint_register_11x11.json` | 10 facets, 98 instances |
| the trim itself | `tools/ground_map_11x11.py`, `docs/NEXT-APPROACHES.md` §4.7 | the 8 and the 12 |
| the two blocks | `tools/trim_510.py` | 40,862 pairs survive three filters |
| per-facet pinning power | `tools/facet_pinning_11x11.py` | F2 cuts the space in half; the rest do almost nothing |
| the size multiset | `tools/size_multiset_11x11.py` | **14 feasible multisets** under the human's reading |
| window-level pinning | `tools/facet_pinpoint_11x11.py` | **0** cells pinned by the state-local facets alone |

---

## 1. What we have, in one table

Everything below is in the register, with its status and its locality. The locality column
is the radius of the ball an instance can possibly touch — **that is the whole basis of the
window decomposition**.

| facet | what it says | status | radius | instances |
|---|---|---|---|---|
| **F-published** | the 33 numbers | PROVEN | ⌊(d+1)/2⌋ per cell | 33 |
| **F-revealed-capitols** | (5,7) and (10,5) are capitols | PROVEN | 0 | 2 |
| **F-singleton-demand** | a d=1 cell is served by a 1×1 state next to it (D64) | PROVEN | 1 | 3 |
| **F-ring** | a 1×1 state is a capitol ⇒ its neighbours have d = 1 | PROVEN | 1 | 3 |
| **F-area** | L2/L3: the state holding x has area ≥ \|d(x) − d(y)\| | PROVEN | 1 | 12 |
| **F-tight** | L1: the drop in d is paid by exactly one edge | PROVEN | 1 | 31 |
| **F-parity** | a state with a capitol has **odd** area (D43) | PROVEN | the state's own extent | 1 |
| **F-ball** | a d = v cell has a capitol within ⌊(v+1)/2⌋ steps | PROVEN | ⌊(d+1)/2⌋ per cell | 9 |
| **F-human** | the human's readings of the instance | OBSERVATION | varies | 2 |
| **F-withdrawn** | the rules that were stated and then refuted | WITHDRAWN | — | 1 |

**The one that has to be carried carefully: R1.** The crashed session used
*"a capitol at s ⇒ every published neighbour of s has d ≤ 1"*, got the pool down from 88
cells to 15, and concluded that no cover of ≤ 5 hidden capitols exists. **That rule is
false** — the step from x to an adjacent capitol c costs `min(size_x, size_c)`, and *both*
sizes can be large, so `d(x) ≤ min(size_x, size_c)` is not `≤ 1`. A cell with d = 8 can sit
next to the capitol of a 12-cell state. **The 15-cell pool and the "> 5" number are void.**
The session retracted this itself, one turn before it degenerated; the register keeps it
(WITHDRAWN) so nobody re-uses it.

---

## 2. The multi-facet, multi-attention shape of the problem

The instance has 121 cells and 33 readings, and every reading is a statement about a
**cost field** that only exists once the whole partition exists. So the naive reading
("one constraint, one search") is the wrong shape. There are **two kinds of constraint**,
and they have to be attended to differently:

```
        STATE-LOCAL facets                 FIELD-LOCAL facets
        (decide a SHAPE)                   (decide a PARTITION)
        ────────────────────               ────────────────────
        F-singleton-demand                 F-published
        F-area                             F-ring
        F-parity                           F-tight
                                           F-ball
        radius 1, or the state's extent    radius 1 .. 39
        decidable inside a 5×5 window      NOT decidable inside a window
```

⇒ **the state-local facets can be decided window by window; the field-local facets are
the JOIN.** That is the plan in one sentence, and it is the reason the two families have
to be kept apart: a window may *refuse* a candidate, but it may never *accept* one.

### 2.1 The window-local d-field sandwich

Inside a window W, the field facets become a two-sided test instead of a global one:

```
    d_upper(x) = the cheapest path from x to a capitol using ONLY in-window cells
                 (a LOWER bound on d(x), because it ignores the paths that leave W)
                 ⇒ if d_upper(x) > d(x) published, the window's sub-partition is REFUTED

    d_lower(x) = the cheapest path if leaving the window were free (one cost-1 step out)
                 (an UPPER bound on d(x))
                 ⇒ if d_lower(x) < d(x) published, the window's sub-partition is REFUTED
```

⇒ a window is a **filter**, never a witness. The last word is always the join. And the
join is where the conservation law lives.

### 2.2 The join: the conservation law (the human's law)

```
    (1)  Σ over states of |S|   =  121                      (the cell count)
    (2)  Σ over states of |S|²  =  Σ over rows of row_sum(row)  =  Q
    (3)  answer = Σ over rows of row_sum(row)²  ≥  Q² / 11   (Cauchy-Schwarz)
```

(2) is the one that touches the answer: a state of size m contributes m to each of the m
rows it crosses, so it contributes m² to the sum of the row sums. **The size multiset
fixes the sum of the row sums**, and with it a floor for the answer.

⇒ **so the window decomposition has a knapsack at its centre**: the window sub-partitions
must be completable to a global multiset of total 121, and their Σ|S|² must add up to a
feasible Q. That is a much sharper join than "the pieces have to fit together".

---

## 3. The windows, and where the locality breaks

The 11×11 is 11×11; a 5×5 window is exhaustible (22,317 legal states, and the counting
DP over them takes 239 s), while the 11×11's state catalogue is hopeless (1.3e12). So:

* **49 windows** of 5×5 (stride 1) cover the board, and every legal state that fits in a
  window is a 5×5 state, translated. The catalogue is computed **once** and reused 49 times.
* **The states that do not fit in a window are the big ones**: a 16-cell state cannot live
  in 5×5 rows × 5×5 cols if it is 8 cells wide. ⇒ **the big states are a separate,
  explicitly global facet**, and they are FEW: the ground map's area bounds name six
  groups (≥16, ≥12, ≥8, ≥6, ≥4, ≥2), and the TIGHT reading says they are six different
  states. Six big states, and each has a few thousand shapes — that is enumerable.
* **The two blocks the (5,10) trim forces land in two different windows**: the 8-block
  sits in rows 2–5 × cols 8–10, the 12-block in rows 6–9 × cols 6–10. They touch at
  (5,10)/(6,10). ⇒ the window decomposition is not an imposition here, it is what the
  instance already looks like.

### 3.1 The measured disappointment (and it is the important one)

`tools/facet_pinpoint_11x11.py` asks, for every window and every cell: **which sizes can
this cell's state still have?** The answer, over all 49 windows and all 121 cells:

> **0 cells are pinned.** Not one.

⇒ the *state-local* facets alone pin no size at all. The area bounds are lower bounds
(≥ 8, ≥ 12, …), and lower bounds do not determine a size. ⇒ **the only facets that can
pin a size are the field-local ones, and they can only be applied at the join.**

That is an uncomfortable result and it is the most useful thing measured so far, because
it says where the work is:

* the window decomposition **cannot** be a parallel search over windows that each produce
  a size map. It has to be a **constraint-propagation** scheme: the windows prune each
  other, and the pruning runs through the field facets and the conservation law.
* the field facets are the expensive ones, so the cheap thing to build is still the window
  solver — but as a **filter**, with the join doing the deciding.

---

## 4. The pinning power, facet by facet

`tools/facet_pinning_11x11.py` measures each facet's killing power on the (8-cell,
12-cell) candidate slice around the (5,10) singleton — 86,359 pairs that pass the
per-block pre-filter (which is F1 + F4):

| facet | kills | pinning power | note |
|---|---|---|---|
| **F2 — the core-path test** | **45,493** | **47.3%** | *the only facet doing real work here* |
| F3 — the capitol ball | 4 | ~0% | weak on this slice; it is the one that reaches the rest of the board |
| F1 — leave the block | 0 | — | already applied by the pre-filter |
| F4 — a revealed capitol inside a filler | 0 | — | already applied by the pre-filter |
| **joint** | | **40,862 survive (47.3%)** | |

⇒ **read it as a ranking of what to implement next**: F2 — "a path through the core may
not be cheaper than a published d" — is the facet that halves the space, and it is a
*partition-level* facet, not a state-level one. The state-level facets (F1, F4) are nearly
free but nearly useless *on their own*; they pay off only in combination with a
partition-level test.

### 4.1 The multiset, and the human's 9

`tools/size_multiset_11x11.py` enumerates the feasible size multisets under the
conservation law. Constraints: the total is 121; the number of singletons is s; at least 6
odd parts (a state with a capitol has odd area, and the hitting set puts the capitol count
at ≥ 6); and the six area bounds as constraints on the six largest parts.

| reading | singletons | feasible multisets | Q = Σ\|S\|² | number of states | answer floor Q²/11 |
|---|---|---|---|---|---|
| TIGHT | 2 | **13** | 1,851 … 3,475 | 9 … 33 | 311,472 … 1,097,784 |
| TIGHT | 3 | **11** | 2,185 … 2,579 | 10 … 27 | 434,020 … 604,658 |
| **TIGHT** | **9 (the human's claim)** | **14** | 1,801 … 2,387 | 16 … 33 | **294,872 … 517,979** |
| LOOSE | 2 | 274,040 | 1,731 … 23,397,103 | 7 … 111,354 | 272,396 … 4.98e13 |
| LOOSE | 3 | 415,597 | 1,693 … 22,336,976 | 7 … 100,953 | 260,568 … 4.54e13 |
| LOOSE | 9 | 357,023 | 1,423 … 13,759,644 | 10 … 63,158 | 184,084 … 1.72e13 |

⇒ **the human's "9" is worth a factor of ~25,000 in the multiset space** (357,023 → 14),
and the TIGHT reading of the six area bounds is worth another factor of ~10⁴. This is the
single largest narrowing in the whole project, and it comes from a *reading of the
instance*, not from the engine.

⇒ **and it gives the answer a floor**: under the human's reading the answer is at least
**294,872**. For comparison, the official 5×5's answer is 8,045 on 25 cells; scaling by
the area, the 11×11 should land in the low hundreds of thousands — so the floor is in the
right neighbourhood, and it is a *check* on the reading, not just a bound.

⇒ **the remaining freedom is the placement, not the multiset.** With 14 multisets and Q
between 1,801 and 2,387, the sum of the row sums is nearly known; what is left is which
rows the states cross, and that is exactly what the window decomposition has to supply.

---

## 5. The shape-growing part: the descent, and where it actually stalls

The (5,10) trim was for a seed (NEXT-APPROACHES.md §4.4g.1). Measured:

| start | best E | plateau? | note |
|---|---|---|---|
| all singletons | 480 | yes, after 40 steps | the previous measurement |
| seeded with the (5,10) trim, best pair | **236** | yes, after ~100 steps (1,200 steps run) | still not 0 |

⇒ **the seed halves the stall energy (480 → 236) and that is all it does.** The seeded
descent reaches a local minimum and stays there for 1,100 further steps. So:

* the descent is **not** the mechanism that finishes this instance — it is the mechanism
  that gets the search to the *right basin*;
* the shape-growing machinery (AODFS) is what has to carry the rest, and it has to grow
  the shapes **across the window boundaries**, not inside them.

⇒ **the growth plan**: for each of the six big states, grow it with AODFS from its anchor
(the published cell inside it), prune with the field facets as it grows (the `prune` hook
in `src/grow.py` exists for exactly this), and let the windows absorb the small states
around it. The state's shape is a *global* object; its *neighbourhood* is what the windows
supply.

---

## 6. The plan, in order

1. **Build the window solver** on one 5×5 window, with the three filters: the
   state-local facets (F1/F4 as a pre-filter on the catalogue), the field facets as the
   d-sandwich (§2.1), and the conservation law as a partial-sum check. Measure how many
   sub-partitions of one window survive. *This is the missing piece: the window solver
   is the only thing in the plan that has not been written.*
2. **Run it on the 49 windows** and keep, per window, the surviving sub-partitions and
   their size maps.
3. **Join** with the knapsack: the sum of the cells is 121, the sum of the squares is a
   feasible Q, and the six big states are grown globally across the boundaries.
4. **Only then** run the seeded descent, as a verifier of the join rather than as the
   search.
5. **Keep the model (Route C, §2 of NEXT-APPROACHES.md) for what it is good at**: ranking
   the big states' shapes, which is where the local arithmetic runs out. It may reorder,
   never veto.

---

## 7. The questions left open

* **How many singletons are there really?** 2 is forced, 9 is the human's claim, and the
  claim is worth a factor of 25,000 in the multiset space. **It is also falsifiable**: the
  d=1 demands only account for 3 of them. *If the claim is wrong, the whole tightening
  above evaporates.* → this is the first thing to test, and it is cheap: enumerate the
  partitions of the 121 cells that have exactly 9 singletons and see whether any of them
  can carry the readings.
* **Are the six area bounds six different states?** TIGHT vs LOOSE is a factor of ~10⁴ in
  the multiset space. The (5,10) picture says TIGHT (the 8-block and the 12-block are
  different blocks, since (6,10) is in one and (5,9) in the other). But the *bounds*
  themselves do not say that — only the picture does.
* **Is (6,10) a capitol?** If it is, the readings give 9 and 13 instead of 8 and 12
  (NEXT-APPROACHES.md §4.7, Step 5), and the two branches predict different shapes.
* **Where does the answer's freedom actually live?** With 14 multisets and Q known to
  within 30%, the answer's spread comes from the row placement. The Cauchy-Schwarz floor
  is 294,872; the ceiling is unknown. *A cheap and useful next measurement: for one
  feasible multiset, enumerate the placements of its parts on the 11×11 and look at the
  spread of the answer.* That would turn "we know the floor" into "we know the range".
* **Can the window solver beat the global solver on the 11×11?** The global solver is
  hopeless (1.3e12 states). The window solver is 49 × 22,317 candidates with a filter. The
  comparison has never been run, and it is the whole bet of this plan.
* **Is the 5×5 the right window size?** The 4×4 is exhaustible in 0.2 s and the 5×5 in
  239 s; a 6×6 is already past the count. The (5,10) trim's two blocks fit in 5×5 but
  not in 4×4 (the 12-block is 4 rows × 5 cols) ⇒ **5×5 is the smallest window that can
  hold the forced shapes, and that is an argument for it that is not about performance.**

---

## 8. What is deliberately not done

* **`src/` is untouched.** The solver's area bound (`src/solver.py::_need`) still uses
  published neighbours only, so it does not see the ring-imputed 8 and the 12. That is an
  engine change and it belongs on `main`.
* **No claim of uniqueness.** The official puzzle does not promise a unique answer
  (NEXT-APPROACHES.md §1.1); the deliverables here are an answer SET and the evidence.
* **The model's role stays where it was**: it may reorder candidates, and the engine
  decides. Nothing in this plan lets a score veto a shape.
