# The locality plan — many facets, small windows, and the questions left open

*This is the plan that came out of the (5,10) trim. It replaces nothing: it is the
"what do we do next, and how do we know it is working" document for the official 11×11.
Everything in it is measured, and every number has a tool behind it.*

| what | where | measured |
|---|---|---|
| the constraint register | `data/derived/constraint_register_11x11.json` | 10 facets, 97 instances |
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

## 1.5 Which of the 33 numbers are actually USED?

*"Has the constraint registry taken all official revealed numbers into consideration?"*

**Two different answers, and the second one matters.**

* **Recorded: yes, all 33.** F-published has 33 instances, one per published cell.
* **Used: 24–26 of them, depending on the core.** The rest are **dormant** — in the
  register, and not yet in any search.

`tools/coverage_audit_11x11.py` measures it. A number is *exercised* by a search over a
core when one of the three tests actually touches it: F1 (it sits inside a candidate
block), F2 (it is adjacent to the core, so a path through the core is a real path), F3 (its
step-count ball hits the core, so "the ball must still contain a possible capitol" bites).

| core | exercised | dormant |
|---|---|---|
| the (5,10) core: the 8-block + the 12-block + the singleton | **26 / 33** | 7 |
| the lower-right corner: (10,8) + (10,9) + (5,10) | **24 / 33** | 9 |
| the whole board (the trivial upper bound) | 33 / 33 | 0 |

**The dormant set of the (5,10) core is exactly the top-left cluster:**

| dormant number | what it is waiting for |
|---|---|
| (2,5) = 1, (3,6) = 1 | **the two other d=1 demands** — and their singletons, which are the only certain 1×1 states in the top-left half |
| (0,1) = 8, (0,2) = 4 | the ≥ 4 states of the top-left corner |
| (2,2) = 7 | the top-left cluster |
| (5,7) = 0, (10,5) = 0 | the two revealed capitols, which are in the *middle* of the board |

⇒ **so the honest state of the project is: the bottom-right corner is being worked with
26 of the 33 readings; the top-left corner has 7 readings that nothing has touched yet.**

⇒ **and that is exactly the shape of the multi-attention plan**: not one core and a
surround, but **two cores** — the (5,10) core in the bottom-right and a second one in the
top-left built from the two d=1 demands (whose singletons are forced: (2,5)'s is one of
(3,5)/(2,6)/(2,4) and (3,6)'s is one of (2,6)/(4,6)/(3,5), and (2,6) can serve both) — and
the **join** between them is the conservation law of §2.2.

⇒ **the join is not a formality.** The two cores are at opposite ends of the board, and
the total is 121: the sizes the two cores consume must leave exactly the right number of
cells for everything in between, with exactly the right Σ|S|². That is a knapsack with one
real constraint, and it is the constraint that the 14 feasible multisets of §4.1 live in.

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

## 5.5 The lower-right corner: the "61 + 16 = 77" reading

The human's reading of the corner: from the 77 cell at (10,8), going LEFT would step
through larger (more expensive) states, so the cheapest route goes RIGHT, through the 61
cell at (10,9): **16 for the crossing step, then 61 more to a capitol.**

**The engine's verdict, in three lines:**

* both cells are **high-d** (2·61 > 121), so by M4 neither may be adjacent to a capitol of
  *another* state. The 16-cost step between them is therefore a **cross-state** step, and
  `min(size(10,8), size(10,9)) = 16` — **one of the two states is exactly 16 cells.**
* **the sharper version of the same constraint, and it is measured, not assumed.**
  `d(10,8) = 77` is the *exact* minimum cost to any capitol (L1 tight), so **every**
  candidate path from (10,8) to any capitol must cost ≥ 77. If a cell `y` of the 16-block
  touches a capitol `c`, the path inside the block to `y` plus the crossing costs
  `16·dist_S((10,8), y) + min(16, size_c) ≥ 16·dist_S + 1`, so **`dist_S ≥ 5`**. ⇒ the
  16-block may touch a revealed capitol only from 5 steps away inside the block:
  `(10,6)`, `(10,4)` and `(9,5)` are **out** (Manhattan 4 from (10,8)); `(5,8)` and
  `(6,7)` are **allowed** (distance 5). *M4 alone would forbid all of them — it is too
  strong; the L1 form is the one to use.*
* ~~the **same-state** reading cannot work: `61 − 16 = 45` is not a multiple of 16.~~
  **CORRECTED — this was wrong.** A 16-cell state has no capitol (D43: a state with a
  capitol has odd area), so the path out of (10,9) does not stay inside the state; it
  crosses into other states, and that crossing is not required to be a multiple of 16.
  The enumeration confirms it: **19,513 sixteen-cell states hold both (10,8) and (10,9)**.
  ⇒ **both readings survive**, and they differ in exactly one thing:
  **(A)** different states ⇒ the crossing step is `min(s(10,8), s(10,9)) = 16` ⇒ **one of
  the two states has exactly 16 cells**; **(B)** the same state ⇒ that state has 16 cells
  and holds both cells. Either way there is a **16-cell state next to (10,8)**.
* ⇒ **the two live candidates for the "16-block"**: the state of (10,8), or the state of
  (10,9). `tools/corner_16_11x11.py` enumerates all three variants:

| variant | enumerated | survive the per-block filters |
|---|---|---|
| the 16-block holds (10,8) | 25,749 | 12,626 |
| the 16-block holds (10,9) | 11,501 | 6,656 |
| the 16-block holds **both** | 39,019 | 19,513 |

(`tools/corner_joint_11x11.py` then adds the joint filters: M4, L1, disjointness from the
8- and 12-blocks, and the "must poke out" test below.)

**Two measurements that come out of the corner, both of them usable by hand:**

**(a) The 16-block cannot fit in the corner.** Take the best-scoring (8, 12) pair from
`tools/trim_510.py` (S8 = rows 2-5 cols 8-10 + (5,9); S12 = rows 6-9, cols 6-10), plus
the forced singleton (5,10) and the two revealed capitols. In the window
**rows 5-10 x cols 6-10** (30 cells) that leaves exactly **15 free cells**:

```
   5,6* 5,7X 5,8* 5,9X 5,10X
   6,6* 6,7* 6,8* 6,9X 6,10X
   7,6X 7,7X 7,8X 7,9X 7,10*
   8,6* 8,7X 8,8X 8,9X 8,10X
   9,6X 9,7X 9,8* 9,9* 9,10*
  10,6* 10,7* 10,8* 10,9* 10,10*
   (* = free,  X = taken)
```

⇒ **a 16-cell state containing (10,8) cannot be contained in that window** (15 < 16), so it
**must poke out through row 4 or column 5**, and the only cells it can reach are
**(4,6), (5,5), (6,5), (8,5)** — of which (5,5)=10 and (8,5)=6 are published, so F1 bites
on them. *This is a one-line check for any hand-built shape: if it does not contain one of
those four cells, it is wrong.* (Necessary, conditional on that 8/12 pair — not sufficient.)

**(b) The size of the (10,9) state is narrowed to five values.** Write the path from (10,9)
to its capitol as *k* steps inside its own state (cost *s* each) plus one exit step
(cost `min(s, s_next)`), plus whatever the exit lands on:

```
   61 = k*s + r          0 <= r <= s,  r = 0 only if the path ends inside the state
```

With the area bound `s >= 16` this leaves **s in {16, 20, 30, 60, 61}** — every other
size in 16..61 cannot produce a 61 (the remainder would exceed *s* or land negative).
And M4 kills the degenerate reading: `s = 61, k = 0` means the first step lands on a
**foreign** capitol, which `2*61 > 121` forbids. So the 61 is produced either by

* **s = 61**: (10,9) sits next to its **own** capitol (a 61-cell state), or
* **s = 16 / 20 / 30 / 60**: the path leaves the state and crosses into a smaller one —
  and *s = 20, 30, 60* all have **r = 1**, i.e. the exit is into a **singleton** capitol,
  which is exactly the shape of a solution: a big filler state, then a 1-cell capitol.

**(c) A shape that is not symmetric is not a state.** `docs/DESIGN.md` §3.1: a state is
**connected and has a non-trivial self-symmetry** ("州 = 连通 + 有非平凡自对称；否则不是州，
不是'无首都的州'"). The orbit growth enumerates exactly that space, so the enumeration is
**complete over states** — and a hand-built shape can be checked for it in one line:
*if it has no lattice symmetry, it is not a state and no reading can save it.* (This is
also why a 16-cell state has no capitol at all: an odd area is necessary for a capitol,
and 16 is even.)

**(d) The best (8,12) pair and the 16-block are incompatible.** Measured on the single
best-scoring pair from the trim: of the 25,749 sixteen-cell states containing (10,8),
**8,787** pass the L1-tightness and L1-leave filters, and **0** of them are disjoint from
that 8- and 12-block — the corner is already full. The same for the 16-block anchored at
(10,9): 5,155 pass the per-block filters, **0** are disjoint.

⇒ so one of the three shapes in the corner is not the one the trim picked. That is the
one number to take away from this round: **the trim's best pair is only one of 40,862
survivors, and the three shapes have to be chosen together.**

The full funnel, measured (`tools/corner_joint_11x11.py`):

| the 16-block holds | enumerated | no capitol inside | L1 tightness | L1 leave-the-block | disjoint from the best 8/12 pair |
|---|---|---|---|---|---|
| (10,8) | 25,749 | 14,191 | 8,787 | 7,735 | **0** |
| (10,9) | 11,501 | 7,386 | 5,774 | 5,155 | **0** |
| **both** | 39,019 | 21,725 | 13,694 | 12,160 | **0** |

⇒ **7,735 and 5,155 legal sixteen-cell shapes sit in the corner; the best-scoring 8- and
12-block leaves them no room at all.** `tools/corner_triple_11x11.py` then joins the 16-blocks
against **all** 40,862 surviving (8,12) pairs with a bitset index, so the answer is no
longer "the best pair" but "how many pairs admit a 16-block".

**And the methodological agreement.** *"Working out a larger shape is convenient, more
convenent than working out possible smaller shapes."* That is not just a convenience — it
is the reason the plan works. A big state is **rigid**: it has a symmetry, so it is a union
of orbits, and AODFS grows it orbit by orbit from an anchor. A small state is **cheap but
numerous**: there are 22,317 legal states in a 5×5, and the small ones are exactly the
filler states whose *sizes* are all the answer needs. So: **grow the big ones (rigid,
few, global), absorb the small ones (numerous, cheap, window-local)** — and the join
between the two is the conservation law.

---

## 5.6 INFERENCE: what the readings themselves force

*"Why don't you pause brute-force calculation, and use the published readings and the
registry of constraints to do inference?"* — **the right call, and it changes the answer.**

The rules so far were LOCAL: they say what a shape must look like. The rules here read a
**number** and say what its **state** must look like. `tools/infer_sizes_11x11.py`.

**The two rules that do all the work**

| rule | statement | why |
|---|---|---|
| **I1** the adjacency bound | for adjacent x,y: `\|d(x) − d(y)\| ≤ min(s_x, s_y)` | the step between them costs at most the smaller state, and the path continues |
| **I2** the path decomposition | `v = k·s + r`, `1 ≤ r ≤ s`, or `v = k·s` | k steps inside the state (cost s each) then ONE crossing of cost `r = min(s, next size)` |

and the two cases that carry the information:

* **`r = 1`** ⇒ the crossing costs 1 ⇒ the next state has **one cell** ⇒ it is a
  **singleton capitol**. This is the human's own pattern: `61 = 12×5 + 1`, `13 = 12 + 1`.
* **`r = 0`** ⇒ the path ends inside the state ⇒ that state has a capitol ⇒ its area is
  **odd** (D43).

**What comes out**

| cell | d | its state has at least | singleton-exit sizes |
|---|---|---|---|
| (10,8) | 77 | **16** | 19, 38, 76 |
| (10,9) | 61 | **16** | **20, 30, 60** |
| (6,2) | 11 | 6 | 10 |
| (7,2) | 17 | 6 | 8, 16 |
| (0,1) | 8 | 4 | 7 |
| (3,8) | 6 | 2 | 5 |
| (4,8) | 4 | 2 | 3 |
| (3,3) | 51 | 1 | 1, 2, 5, 10, **25, 50** |
| (8,8) | 45 | 1 | 1, 2, 4, 11, 22, 44 |
| (10,1) | 26 | 1 | 1, 5, 25 |

**Three deductions that change the plan**

1. **The "12" does not belong to (10,9) — it belongs to the state it CROSSES INTO.**
   (10,8) and (10,9) are adjacent, so I1 gives `min(s₈, s₉) ≥ 16`; a 12-cell state
   *containing* (10,9) would also give `d(10,8) ≤ 12 + 61 = 73 < 77`, so it is refuted.
   **But the arithmetic `61 = 12×5 + 1` survives, with the anchor moved:** the path
   *crosses into* a 12-cell state (cost `min(s₉,12) = 12`, legal because `s₉ ≥ 16`),
   walks 4 steps inside it (12 each), and exits to the (5,10) singleton for 1.
   **The human's reading was right; only my first placement of it was wrong.** (This is
   recorded as a CORRECTION in the register, facet F-withdrawn-readings.)
2. **The 12-cell state holds (6,10) and (7,10).** `13 = 12 + 1` puts a 12-cell state on
   the step (7,10)->(6,10); `d(6,10) = 1` (one step into the (5,10) singleton) and
   `d(7,10) = 12 + 1` put both in the **same** state. ⇒ **the trim's 12-block was in the
   wrong place** — and that is exactly why **no** 16-cell block could fit beside it
   (0 survivors). Measured: **1,044** twelve-cell states contain both (6,10) and (7,10);
   **783** hold no revealed capitol; **149** also carry an entry cell 4 steps from (6,10).
   Compare: 347,802 blind pairs.
3. **The exit singleton is (5,10), not a hidden one.** Measured: the exit of the 61 path
   is the cell that steps into the **1-cell state at (5,10)**, and the whole path
   (10,9) -> ... -> (6,10) -> (5,10) is 6 steps for a Manhattan distance of 6 — monotone.
   ⇒ the corner needs **no** hidden singleton at all: (5,10) serves (4,10), (5,9),
   (6,10) *and* the 61 path.

⇒ **the corner is now mostly INFERRED, not searched:** a 12-cell state at (6,10)+(7,10),
a 16-cell state at (10,8), a 20/30/60-cell state at (10,9), a hidden singleton near
(10,9), and the known (5,10) singleton. The search that remains is *three* enumerations
with those anchors — not 347,802 pairs.

### 5.7 THE CHAIN, RUN: 632 surviving corner triples

*"Why don't you pause brute-force calculation, and use the published readings and the
registry of constraints to do inference?"* — **done, and it paid.**
`tools/chain_corner_11x11.py` reads the chain off the readings and then enumerates
**only what the chain allows**:

| the chain | what it forces |
|---|---|
| `d(6,10) = 1` | free: one step into a 1-cell state costs 1 whatever (6,10)'s own state is |
| `d(7,10) = 13 = 12 + 1` | the step (7,10)->(6,10) costs 12 ⇒ **a 12-cell state touches both** |
| `d(10,9) = 61 = 12*5 + 1` | the path crosses **into** the 12-cell state, walks 4 steps inside it, then exits to the (5,10) singleton. Manhattan (10,9)->(5,10) = 6 = the 6 steps of the path ⇒ **monotone** |
| `\|77 − 61\| = 16 ≤ min(size₈, size₉)` | (L2/L3) both states have ≥ 16 cells ⇒ the 12-cell state contains neither (10,8) nor (10,9) |
| `d(10,8) = 77 = 16 + 61` | the step (10,8)->(10,9) costs 16 ⇒ **a 16-cell state holds both** |
| `d(6,9) = 9 = 8 + 1` | the step (6,9)->(6,10) costs 8 and (6,10)'s state is 12 ⇒ min = 8 forces **size(6,9) = 8 exactly** |

**The candidate space, before and after**

| | count |
|---|---|
| the blind search: (8-cell, 12-cell) pairs | 347,802 |
| 12-cell candidates the chain allows | **149** |
| 8-cell candidates the chain allows | **630** |
| 16-cell candidates the chain allows | **7,534** |
| disjoint (8,12) pairs that leave room for a 16 | 9,707 |
| triples | 1,209,079 |
| triples whose local field **equals** d(10,9) = 61 | **711,132** |
| triples whose local field **equals** d(10,8) = 77 | **302,332** |
| triples **not refuted** by any published reading inside them | **58,765** |

**The two branches of the "8"** — a correction, and it changed the numbers. `d(6,9) = 9`
has **two** d=1 neighbours, (5,9) and (6,10), so the "8" in `9 = 8 + 1` has **two
carriers**:

* **branch A** — (6,9)'s own state has 8 cells (483 candidates);
* **branch B** — the state holding (5,9) has 8 cells (399 candidates; 252 do both).

An earlier version of this section hard-coded branch A and reported 632 survivors. With
both branches enumerated the count is **58,765**, and the split is lopsided:

| the 8 is carried by | survivors |
|---|---|
| (5,9) | **58,133** |
| (6,9) | 632 |

⇒ **the "8" is far more likely to live at (5,9) than at (6,9)** — which is worth knowing,
because (5,9) is also the cell the 61 path's neighbour set depends on.

**The survivors share a probabilistic skeleton.** Measured over all 58,765 of them:

| state | 100% of every survivor | ≥ 50% | 10–50% |
|---|---|---|---|
| 12-cell | (6,10) (7,10) | (8,10) 99.5%, (6,8) (6,9) 98.8%, (9,10) 87.2%, (6,7) 80.2%, (10,10) 79.5% | (7,8) 68.8%, (7,9) 65.8%, (8,9) 62.4%, (6,6) 60.6%, (9,9) 41.9%, (7,7) 41.5%, (8,8) 31.8%, (5,8) 28.6%, (4,8) 18.6%, (3,8) 13.8%, (8,7) 13.6% |
| 8-cell | (4,9) (4,10) (5,9) | (3,9) 73.9%, (2,9) 56.4% | (4,8) 47.7%, (1,9) 39.6%, (2,10) 38.2%, (3,10) 37.9%, (3,8) 37.0%, (0,9) 27.0% |
| 16-cell | (10,8) (10,9) | (9,6) 74.7%, (8,5) 74.5%, (8,6) 70.9%, (9,7) 69.6%, (10,7) 69.1%, (9,5) 55.9%, (7,5) 54.6%, (8,4) 53.5% | 32 cells between 10% and 50%, 50 below 10% |

`d(7,10)=13`, `d(10,9)=61`, `d(10,8)=77` are **explained exactly** in every survivor.

⚠ *A note on how this table was NOT to be read.* An earlier version of this section
said the 12-cell state's twelve cells were "FIXED" — that was **sampling bias**: the
60 stored samples are the first 60 survivors, they all come from one branch, and they
made the state look rigid. Measured over the whole set, only two of its cells are
certain. The counts in `data/derived/chain_corner_11x11.json` are the real ones.

⇒ **the 8-cell state's core is five cells** — (2,9) (3,9) (4,9) (4,10) (5,9) — and the
12-cell state's core is the (6,8)–(6,10) / (7,8)–(7,10) band. The 16-cell state's tail
is the least pinned of the three: 50 of its 53 possible cells appear in under 10% of the
survivors, so **the next constraint has to come from outside this chain**.

**Two more deductions came out of the run itself**

* **the 8-cell state must not give (10,9) a shortcut.** Measured: a triple where the
  8-cell state reaches (10,10) produces a local d(10,9) of **53**, not 61 — the 8-cell
  state offers a cheaper route than the 12-cell one. So the 8-cell state has to be
  positioned so that the 12-cell route stays the cheapest. This is the L1 tightness
  rule biting a *different* cell than the one being solved.
* **the 45 needs a nine-cell state.** (8,8) lands inside the 12-cell state in **60 of 60**
  samples, and the local field gives 49 for it against a published 45 (an upper bound, so
  no contradiction — but the path is not the 4-step one). The only decomposition that
  works is **45 = 12×3 + 9**: three steps inside the 12-cell state and then a crossing of
  cost 9 into a **nine-cell state**. So (8,8) sits exactly 3 steps from (6,10) inside the
  12-cell state, and there is a 9-cell state next to it.

---

## 5.8 Three register claims, MEASURED

A review of the register raised three things that were worth checking rather than
believing.  `tools/register_claims_11x11.py` recomputes all three from the register file.

**A. The six area bounds come from six different edges.** The bound for x is
`|d(x) − d(y)|` for an adjacent y.  The six bound-pairs are

| edge | bound |
|---|---|
| (0,1)–(0,2) | ≥ 4 |
| (3,8)–(4,8) | ≥ 2 |
| (5,9)–(6,9) | ≥ 8 |
| (6,2)–(7,2) | ≥ 6 |
| (6,10)–(7,10) | ≥ 12 |
| (10,8)–(10,9) | ≥ 16 |

and **no two of them share a cell** ⇒ six different edges of the d-field, so the six
bounds cannot be the same state boundary.  *But this still shows six different EDGES, not
six different STATES: the "≥" has to become "=" — and that step is the real question.*

**B. The step-count ball is inert for the four big readings.** The board's largest
Manhattan distance is 20, and the radius is `floor((v+1)/2)`:

| reading | radius | |
|---|---|---|
| d(10,8)=77 | 39 | covers the board — inert |
| d(10,9)=61 | 31 | inert |
| d(3,3)=51 | 26 | inert |
| d(8,8)=45 | 23 | inert |

⇒ **the bottom-right corner gets no help from the ball at all.** The 9 readings that
actually generate a hidden-capitol demand are the ones in the **top left** plus the d=1
chain ⇒ *the pressure is in the top left, not in the corner everybody has been staring
at.*

**C. The answer depends only on the row profile.** The answer is `Σ_rows (row sum)²`,
and the cost field depends only on the **partition** (which cell is in which state, and
each state's size) — **not on the shape**.  So two partitions with the same row profile
give the same answer, and the search target can be **one witness per distinct row
profile** instead of every partition.  Shape legality then filters partitions instead of
being a search dimension.  (And `Σ row sums = Σ|S|² = Q` depends only on the multiset of
sizes, so Q is fixed before anything is placed.)

---

## 6. The plan, in order

0. **Close the coverage gap (§1.5).** 7 of the 33 readings are dormant, and they are all
   in the top-left. Build the SECOND core there — from the two d=1 demands (their
   singletons are forced) and the (0,1)/(0,2) ≥ 4 states — and then the two cores are
   joined by the conservation law. *Cheap, and it is the only thing that makes the
   top-left half of the board do any work.*
1. **Build the window solver** on one 5×5 window, with the three filters: the
   state-local facets (F1/F4 as a pre-filter on the catalogue), the field facets as the
   d-sandwich (§2.1), and the conservation law as a partial-sum check. Measure how many
   sub-partitions of one window survive. *This is the missing piece: the window solver
   is the only thing in the plan that has not been written.*
2. **Run it on the 49 windows** and keep, per window, the surviving sub-partitions and
   their size maps.
3. **Join** the two cores with the knapsack: the sum of the cells is 121, the sum of the
   squares is a feasible Q, and the six big states are grown globally across the
   boundaries.
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
