# Four routes outside A, B and C — and the measurement they rest on

> **Provenance.** Written by a *third* session: not the author of `docs/aodfs-layman`, and not
> the peer session that owns `main`. It was written after reading only the work files on the
> `docs/aodfs-layman` branch — `docs/LOCALITY-PLAN.md`, `docs/ALTERNATIVES.md`,
> `docs/NEXT-APPROACHES.md`, `data/derived/constraint_register_11x11.json`, and
> `data/puzzles/official-example-5x5/truth.json`. **No solver was run and no shape enumeration
> was performed.** Everything marked **MEASURED** was read off the committed data or computed by
> hand from it; everything marked **CONJECTURE** is a hypothesis with a stated test.
>
> **Why this file exists.** `NEXT-APPROACHES.md` has three routes — **A** (simulation), **B**
> (speculate the capitol count), **C** (a fuzzy ranking layer) — and all three share one shape:
> *the search has to be run*. They differ in what the search looks for; they do not differ in
> what the search enumerates. This file proposes four routes that change **what gets
> enumerated**, plus one measurement that changes what "the answer" is.

---

## 0. The measurement the four routes rest on

**MEASURED** — from the official 5×5's truth file (`data/puzzles/official-example-5x5/truth.json`,
answer 8,045).

```
row_sum(i)  =  Σ_states ( |S|  ×  |{ cells of S in row i }| )
```

| state | size | row distribution (rows 0..4) | contributes to the row sums |
|---|---|---|---|
| A | 7 | (1, 1, 2, 3, 0) | (7, 7, 14, 21, 0) |
| B | 4 | (2, 2, 0, 0, 0) | (8, 8, 0, 0, 0) |
| C | 3 | (0, 1, 2, 0, 0) | (0, 3, 6, 0, 0) |
| D | 11 | (2, 1, 1, 2, 5) | (22, 11, 11, 22, 55) |
| | | **row sums** | **37, 29, 31, 43, 55** |

⇒ **The 11-cell state alone puts 55 into row 4, and 55² = 3,025 — 37.6% of the answer 8,045.**

Two consequences:

1. **The answer is dominated by where the big states sit, row-wise.** The fine structure of the
   fillers moves it by hundreds; the big states move it by tens of thousands.
2. **Q = Σ|S|² = Σᵢ row_sum(i) is placement-invariant** — a state of size *m* adds *m* to each of
   its *m* cells, whatever rows they sit in. So for a fixed size multiset the *sum* of the row
   sums is already known (under the TIGHT reading, Q ∈ [1,801, 2,387] — `LOCALITY-PLAN.md` §4.1),
   and
   `answer = Q²/11 + Σᵢ ( row_sum(i) − Q/11 )²`.

⇒ **The answer's freedom lives in a small discrete object — the row-distribution of the big
states — not in the partition.**

**Calibration** (MEASURED, same file): 5×5, Q = 7² + 4² + 3² + 11² = 195; the Cauchy–Schwarz
floor is 195²/5 = 7,605, and the true answer is 8,045 ⇒ **the answer sits 5.8% above the floor.**
The 11×11's floor is 294,872 (`LOCALITY-PLAN.md` §4.1) ⇒ if the profile excess is comparably
small, the answer is ≈ 1.06 × 294,872 ≈ 312,000, and the real question becomes the **spread
between the 14 feasible multisets** rather than the placement.

**CONJECTURE.** The profile-excess ratio is a property of the instance family, not of the 5×5.
*Test:* measure it on any generated twin (§3). If it varies a lot, the answer's uncertainty
returns to the placement, and Route P below has to be tightened.

---

## 1. The equivalence that shrinks the deliverable

**MEASURED / derived.** A step costs the size of the state you are in, or the smaller of two
sizes when you cross a boundary. Both are functions of the **partition** (which cells are
grouped) and not of the **shape** each group is drawn as. Hence:

* the d-field is a function of the partition alone;
* the answer is a function of the partition alone, through the 11-vector of row sums;
* **two partitions with the same row-profile give the same answer**, even when their d-fields
  differ;
* and the 4×4 counter-example (same d-field, different answers — `NEXT-APPROACHES.md` §1.1) is
  *not* a counterexample to this: those two tilings differ in their state **sizes**, so their
  row sums differ.

⇒ `NEXT-APPROACHES.md` §1.1 already says *"finding one valid tiling is a complete deliverable"*
and that the deliverable is an answer SET. **This refines the unit of the deliverable: the unit
is the row-profile, not the tiling.** The search becomes *"for each distinct row-profile, find
one witness"*, and the answer set = the set of profiles that have a witness.

⇒ It also fixes the **shape of the final report**: *answer + one witness partition + the 33
readings checked one by one + the uniqueness annotation*. (D42 / R9 / M6 already require the
annotation; what this removes is the need to enumerate everything in order to get it.)

---

## 2. Route P — profile-first: the answer set without solving the partition

**The idea.** Enumerate the **row-distributions of the big states**, not the partitions. For each
candidate distribution of the six big states (TIGHT: 2, 4, 6, 8, 12, 16 — see §6), the big part
of every row sum is determined. The remaining cells (the fillers and the singletons,
121 − 48 = 73 under TIGHT) contribute the rest, and their contribution can be **bounded without
enumerating placements**: it is a transportation problem on 11 rows with per-row capacity 11,
i.e. an LP.

⇒ Output per candidate: a **certified interval** for the answer, not a sample.

**Why it is not A, B or C.** A/B/C enumerate *tilings*; P enumerates *row-distributions* and
replaces the filler enumeration with a relaxation. A/B/C need the search to run before they
produce anything; P produces a range **without running the solver at all**.

**What it needs.** (i) the six big sizes; (ii) the multiset's Q; (iii) per-row capacity, and the
fact that a state of size *m* spanning *k* rows needs *m* ≥ *k*.

**The question it answers** — the one `LOCALITY-PLAN.md` §7 asks, *"where does the answer's
freedom actually live?"* — with an interval instead of a hunch.

---

## 3. Route T — generated twins: the test bench the window solver needs

**The gap.** `NEXT-APROACHES.md` §6 rule 7 says *"the 5×5 is the test bench."* But a 5×5 board
hosts exactly **one** 5×5 window, while the 11×11 hosts 49 (`LOCALITY-PLAN.md` §3). So the one
plan step that is entirely unbuilt — §6 step 1, **the window solver** — **cannot be validated on
the only board that has ground truth.**

**The proposal.** This repository is a *generator* as well as a solver (`src/`,
`tools/generator_selfcheck.py`), so it can mint instances whose truth is known by construction.
Generate:

* **6×6 and 7×7 twins** — 4 and 9 windows of 5×5 respectively ⇒ the window solver finally has a
  board whose answer is known, and the *"a window may refuse a candidate, never accept one"*
  discipline (`LOCALITY-PLAN.md` §2) becomes testable;
* a twin with the **reading pattern of the official 11×11** (33 readings in a similar spatial
  distribution) ⇒ the reasoning chain of `LOCALITY-PLAN.md` §5.6 (the `d = k·s + r`
  decomposition) can be **scored for hit rate** against a known truth: we would learn *at which
  step it starts to go wrong*, which is a number no amount of work on the 11×11 can give;
* a twin with the **same multiset** (TIGHT: 2, 4, 6, 8, 12, 16) ⇒ Route P can be validated on a
  known truth, and the profile-excess ratio of §0 measured on more than one instance.

**Why nobody did this.** Every route so far treats the 5×5 as the only ground truth available —
and the 5×5 is too small to exercise any of the machinery that is about to be built.

---

## 4. Route S — satisfiability instead of enumeration

Every tool in the repository is a hand-written search: grow, enumerate, bitset-join, greedy
descent, anneal. They share one failure mode: the state catalogue is 1.3e12 on the 11×11
(`LOCALITY-PLAN.md` §3).

**A different failure mode.** Ask for satisfiability instead of enumerating. Encode: a state id
per cell; legality (connectivity, a symmetry, exactly one fixed square) as constraints; the
d-field as a min-plus distance to the capitols. Z3 / MSAT / CP-SAT return UNSAT, or a witness,
without touching the catalogue.

**Where it is most likely to pay.** Not the whole 11×11 — the min-plus encoding is heavy. But
the **top-left core** is small: the nine "needs a hidden capitol" demands plus three d=1
singletons and a 13-cell ball ⇒ a few hundred unknowns, which is exactly the regime where a
solver beats a search.

**And it is orthogonal to A/B/C.** A satisfying assignment is a **witness** (what §1.1 wants); an
UNSAT result on a *local* sub-instance is a **proof that no arrangement of that core exists** —
which is exactly what the descent can never produce.

---

## 5. Route Y — style transfer: read the skeleton off the 5×5, move it to the 11×11

**MEASURED** — the official 5×5's four states, with symmetry and capitol:

| state | size | symmetry | capitol | shape |
|---|---|---|---|---|
| D | 11 | refD2 (the bbox anti-diagonal) | (4, 4) | an **L hugging the bottom row and the right column**, plus (0,3) and (3,0) |
| A | 7 | refD2 | (2, 1) | a diagonal-symmetric slab |
| C | 3 | refD1 | (2, 3) | a small L |
| B | 4 | 7 elements, fix counts {2,2,0,0,0,0,0} | **none** | the 2×2 block — a filler |

⇒ **Three hypotheses, each testable on the 11×11 before any search runs:**

1. The biggest state is a **corner-hugging L whose capitol is that corner** — the 11-cell state's
   capitol is the board corner (4,4), and the state is the union of one row and one column.
2. The symmetry is always a **reflection of the state's own bounding box** (refD1 / refD2), never
   a free-floating axis.
3. Exactly one state is a **capitol-less filler**, and it is the smallest structured shape (the
   2×2).

**Why this is a route and not a curiosity.** If the 11×11 was built the same way, its big states
are also corner- or edge-hugging L/frame shapes with the capitol at the extremal point, and the
candidate set collapses from 1.3e12 to a few dozen. The first test is cheap: does the 11×11's
reading field admit such a skeleton? The "61" at (10,9) constrains that corner's state to sizes
{20, 30, 60} (`LOCALITY-PLAN.md` §5.6) — a corner L with the capitol at (10,10) is one of the
candidates.

**The honest caveat.** n = 1. `ALTERNATIVES.md` §4 is a lesson in exactly this failure ("a factor
measured in one context does not transfer"). This route is worth **one** cheap experiment, not a
strategy.

---

## 6. The six area bounds have a certificate

**MEASURED** — `data/derived/constraint_register_11x11.json`, facet `F-area`, 12 instances. The
12 minimum-area values de-duplicate to **{2, 4, 6, 8, 12, 16}**, one per edge:

| edge | Δ | where |
|---|---|---|
| (0,1) − (0,2) | 4 | top-left |
| (3,8) − (4,8) | 2 | middle-right |
| (6,2) − (7,2) | 6 | middle-left |
| (10,8) − (10,9) | 16 | bottom-right corner |
| (5,9)\* − (6,9) | 8 | lower-middle-left (\* imputed d = 1) |
| (6,10)\* − (7,10) | 12 | lower-middle-right (\* imputed d = 1) |

⇒ **Six edges, six disjoint regions, six distinct states** — and they are exactly the six area
bounds of the ground map (≥16, ≥12, ≥8, ≥6, ≥4, ≥2).

⇒ So the TIGHT reading is **not a reading of the picture**: the bounds are the d-field's own
tight edges, and the *"are the six area bounds six different states?"* half of
`LOCALITY-PLAN.md` §7's open question is **already settled**. What remains is only **"≥" → "="**,
which is a much smaller question than the one the plan poses.

⇒ And the other candidate load-bearing claim is *not* load-bearing: the "9 one-cell states"
(`F-human`, instance 2) is marked `OBSERVATION -- not derived here`, and its own proposed test
does not work — see `ALTERNATIVES.md` §10.

---

## 7. What is still open (from this file)

* **Is the TIGHT multiset right** — i.e. are the six big states *exactly* 2, 4, 6, 8, 12, 16?
  After §6, this is the only load-bearing reading left, and it is the one the plan does not
  foreground.
* **Does the profile-excess ratio (5.8% on the 5×5) hold across instances?** Measurable on the
  twins of §3; it decides how tight Route P's intervals will be.
* **Which of the six big states' row-distributions are geometrically possible at all?** (a state
  of size *m* can span at most *m* rows, and it must be symmetric about *something*)
* **Does the 11×11's big state hug a corner** (hypothesis Y1)? One cheap test.
* **Is the top-left core small enough for SAT?** The answer decides whether Route S is worth it.

---

## 8. Where the pieces live

| file | what it holds |
|---|---|
| `docs/NEW-ROUTES.md` | this file: routes P, T, S, Y; the 5×5 row-profile measurement; the six-edge certificate |
| `docs/NEXT-APPROACHES.md` | routes A, B, C — the three that need the search to be run |
| `docs/LOCALITY-PLAN.md` | the plan: the facets, the window decomposition, the conservation-law join |
| `docs/ALTERNATIVES.md` | the discussion log: the analogies, their translations, the measurements — and §10, the register defect |
| `src/grow.py` | the growth machinery (the shapes) |
| `src/hitting.py` | the hitting set and the `d = 1` rule — **the engine's ball is Manhattan; the register's display is not** (`ALTERNATIVES.md` §10) |
| `tools/generator_selfcheck.py` | the generator — Route T's raw material |
