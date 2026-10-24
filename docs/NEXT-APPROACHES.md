# Next approaches — three ideas, turned into algorithms

> **What this file is.** A specification, not a result. Three ideas are written down here as
> algorithms and pseudo-code so that they can be implemented and *measured* against each other
> before anyone spends time on the 11×11.
>
> **The ideas came from the user** (§0); the translation, the scoping and the pseudo-code are mine.
> The lesson that shapes the whole file is in §1: a heuristic that *cuts* can cut the truth, so
> every fuzzy layer here **orders** and never **prunes**.
>
> **Read §1 first.** It changes the target, and therefore changes which of these three routes is
> even legitimate.

---

## 0. The three ideas, as given

1. > *"If we don't rely on strict calculation, we might add a touch of simulation. Simulation
   > sometimes beat deterministic calculation to tackle a problem."*
2. > *"If we use a fuzzy function to determine the probability of success of a shape, we can cut
   > it, if the probability is low. If we don't use calculation, we can use image/vision judgement.
   > For example, we can know if a shape overlap with other highly probable shapes in
   > consideration."*
3. > *"Shapes are many. But capitols are less. If we speculate the numbers of capitols, we reduce
   > our search/simulation."*

---

## 1. The reframing that makes (1) legitimate — and the rule that makes (2) safe

### 1.1 The official puzzle asks for **a number** — and does not promise that number is unique

**The puzzle states**: the rules, an example that works with them, the numbers on the 11×11
frame, and *"submit as your answer the sum of the squares of these row sums"*. **It never says the
answer is unique.** If several tilings satisfy the rules and the cues and give different numbers,
**there is no stated basis for rejecting any of them** — and the puzzle maker may not know either.

**The repository already agrees** — this is not a new reading, it is `PLAN.md`:

| the plan says | what it means |
|---|---|
| **R9** | "the 11×11 panel draws no state boundaries; the partition itself may not be unique ⇒ the official deliverable is **all candidate answers + their partitions + a uniqueness annotation**; if it is not unique, report that honestly" |
| **D20** | "the same set of hints can correspond to **different answers**" (the 4×4 counter-example) |
| **M6** | "if the answer is not unique, give **every candidate answer with its partition**" |
| **D42** | "when the search is not exhaustive, **you may not output 'unique'**" |

⇒ **Therefore the deliverable is an ANSWER SET plus an honest uniqueness annotation — not a
proof of uniqueness.** `exhaustive=false` is a *legal, reportable* state.

⇒ **What this changes in the search:**

* **Finding one valid tiling is a complete deliverable** (modulo the annotation). The remaining
  budget is spent looking for *more* answers, not on proving there are none.
* **The 84%-free filler states stop being fatal.** We no longer need a constraint that pins every
  filler area; we need one that finds a consistent assignment.
* **The exact route's failure mode becomes explicit**: "26 M nodes, 0 answers" produced *nothing
  reportable*, because with zero answers there is no answer to report — and the only thing
  exhaustion would have added is the uniqueness annotation, which is optional.
* **The near-miss diagnostic (§4.4) becomes more valuable**, not less: it is the one output the
  exact route cannot produce at all.

⇒ **A spec conflict to resolve** (flagged to the peer): **D39** says *"stop early as soon as a
second distinct answer is found"*, while **R9/M6** say *"deliver **all** candidate answers"*.
Both cannot hold — stopping at the second answer means not having all of them. The consistent
reading: the early stop settles the **uniqueness verdict** (`unique=false`), but the **collection**
of answers should keep going until the budget ends. The report should say how many were found and
whether the search was exhaustive — never imply completeness without it.

⇒ **One practical nuance** (not a contradiction, just a reporting matter): the *intended* answer is
the one Jane Street's own generator produced, so a second valid answer will differ from the
official one. The honest report leads with the answer that matches the official one when it is
found, and lists every other valid answer with its proof.

This is the single most important thing in this file.

The *generator* (our own tool) needs a **proof** that the answer is unique: that needs exhaustion,
and exhaustion is exactly what simulation cannot give. But the **official puzzle** is a different
job. We are not asked to prove anything; we are asked for a number.

⇒ The official task decomposes into two *separate* questions:

| task | method | needs exhaustion? |
|---|---|---|
| **(A) find one tiling** consistent with the 33 published numbers | simulation is fine | **no** |
| **(B) be confident the answer is unique** | hunt for a counterexample (a second tiling with a *different* answer) | no — a counterexample hunt is also simulation |

And note the special structure of this puzzle family: two different tilings can share the *same*
cost field and still give different answers (the 4×4 counter-example: 304 vs 112). So (B) is not
"enumerate the tilings" — it is **"hunt for a second answer"**, which is a much easier target, and
one that a heuristic can attack.

⇒ **Consequence: the current goal — "exhaust the 11×11 search" — is the wrong goal.** We have
spent 15.6 M nodes trying to prove something we do not need to prove. A route that finds *one*
answer in ten minutes is worth more than a route that proves uniqueness in ten hours.

### 1.2 The rule that makes (2) safe

A fuzzy score may **order** the search. It may **not** prune it.

This is not a style preference; it is the same failure mode as the withdrawn tight-edge claim
(§4 of `ALTERNATIVES.md`): a heuristic that is not a *proof* can cut the true branch. The fix is
structural, not careful:

> **Fuzzy layer ⇒ ranking only. Hard constraints ⇒ the engine only.**

The engine (`src/rules.py`, `src/cost.py`) remains the only thing allowed to decide what is legal.
A model may rank; it may not rule.

---

## 2. Route C — a fuzzy ranking layer (idea 2)

### 2.1 The mental model to borrow

The **System One** decision-model shape (TypeSafe's docs, `docs.typesafe.ai/introduction`) fits this
problem unusually well:

* a **state** (the partial tiling plus the published numbers) is handed to a model;
* **atomic questions** are asked against that state, evaluated independently and in parallel;
* each question returns a **typed value, a probability distribution and a confidence** — not prose;
* three question kinds suffice here:
  * **`Noul`** — a predicate: "is this orbit entirely on the board and not overlapping?" ⇒ a
    0–1 value, for risk checks;
  * **`Score`** — a rubric: "how plausible is this shape?" ⇒ a score, probabilities, confidence;
  * **`Choice`** — the alternatives: "which orbit should we grow next?" ⇒ choice, probabilities,
    confidence;
* **policy lives in application code**: thresholds, ranking, and **confidence gating** — abstain
  when confidence is low and fall back to a deterministic path.

The user's own `system1-measure` repository is the natural home for the question sets and the
evidence trail: it is the *measurement* side (question sets, composition, format, producer/reader,
rules), which is exactly what a shape score needs — **a number plus the evidence behind it**.

### 2.2 What to ask about a candidate shape

| kind | question | signal | computed by |
|---|---|---|---|
| `Noul` | the orbit is on the board and touches no placed state | hard | **the engine** |
| `Score` | area fit: does the grown state's area sit in `[need(S), area_budget]`? | area lower bound (§2 of `ALTERNATIVES.md`) + remaining cells | arithmetic |
| `Score` | capitol fit: does the state have a capitol? is it consistent with the `d=0` / `d=1` cells? | rule kernel | **the engine** |
| `Score` | **conflict**: how many other high-scoring candidate shapes want the same cells? | the user's "overlap" idea — see §2.3 | arithmetic |
| `Choice` | which orbit to grow next | all of the above combined | model |

### 2.3 The conflict score — the "overlap" idea, made concrete

The user suggested: *"we can know if a shape overlap with other highly probable shapes in
consideration"*. Concretely:

```
def conflict_scores(candidates, top_n=16):
    # candidates: the orbit-unions reachable from the current state, with their partial scores
    # 1. take the top_n candidates by partial score
    # 2. for each pair (X, Y), conflict(X, Y) = |X ∩ Y| / min(|X|, |Y|)
    #    (how much of the smaller shape the other one steals)
    # 3. a shape that conflicts with many high-scoring shapes is less likely to be right:
    #    score(X) -= sum over the top_n of conflict(X, Y) * score(Y)
    return {X: score(X) - sum(conflict(X, Y) * score(Y) for Y in top_n if Y is not X)
            for X in candidates}
```

The intuition: if two plausible shapes want the same cells, **at most one of them can be in the
true tiling** — so the one that conflicts with *more* of the plausible set is the less likely one.
This is a *ranking* signal; it is not a proof, and it must never be used to delete a candidate.

### 2.4 The model's actual job in this project: **propose the kick**

The general form of a fuzzy layer is "rank the candidates". In *this* project the measurement
(§4.4g) says something sharper: a hill-climb in a **cliff** landscape has nothing to climb — the
cheapest neighbour of the 5×5's solution costs 11 — so what the search needs is not a better
ordering of small moves, it is a **good big jump**.

⇒ **The model's job: when the climb is stuck, say WHERE to jump and to WHAT.**

> ⚠️ **REVISED after §4.4g.1.** A greedy descent does the walking, so the model is *not* needed to
> choose the next step. Its remaining jobs are narrower and more honest:
> **(a) escaping a local minimum** — the 11×11's descent stalls at E = 480 from the naive start;
> **(b) a better start** — a capitol set from the hitting set instead of all-singletons;
> **(c) a prior on the area map** — no local arithmetic expresses "a 40-cell state here is
> unusual"; **(d) the vision read** of the d-field as a terrain, which the local bounds never look
> at. It is a *proposer of starts and escapes*, not a guide for every step.

```
KICK PROPOSAL (the model)
  state      : the stuck tiling, the published numbers, the d-field, the incumbent's areas
  questions  :
      Noul  "which regions are legal to re-partition at all?"      -> the ENGINE, not the model
      Score "is this region a wide plateau in the d-field?"       -> model (the terrain read)
      Score "is this re-partition plausible (area, symmetry)?"    -> model
      Score "does it conflict with the other high-scoring plans?" -> model (the overlap signal)
      Choice "which single plan should we try?"                    -> model, returns probabilities
  output     : one proposed move, with a confidence
  then       : the ENGINE checks legality; the ARITHMETIC scores it; the annealer accepts or rejects
```

**Why this is safe** — the architecture is *propose, don't verify*:

* the model never decides legality (the engine does) and never decides truth (the arithmetic does);
* a model answer only ever **replaces the deterministic default** for the kick, so a garbage model
  costs speed and nothing else;
* **confidence gating**: below the floor, fall back to the deterministic kick;
* the model's scores are **ranking keys, not probabilities** (§4.5).

**Why it is not redundant with the arithmetic** — three places where it has information the
arithmetic does not:

1. **A prior over areas.** The area lower bound gives a *floor* (`need[x]`) and never an upper
   preference. A model can say "a 40-cell state here is unusual", which the bound cannot.
2. **The terrain read.** The area bound uses only *adjacent* published cells; the *global shape* of
   the d-field (a wide plateau) is information the local bound never sees.
3. **Conflict.** "Two plausible shapes want the same cells" has no arithmetic counterpart at all —
   it is the user's "overlap" idea, and it is a statement about the *competition* between plans,
   not about one plan.

⇒ ⇒ **And the vision variant has a precise home here**: the d-field rendered as a picture is a
terrain; "the plateau around rows 5–8, columns 9–11 looks like one large state" is exactly the
kind of proposal the cliff regime needs — and it is a proposal, so it can be wrong without
endangering the search.

### 2.4 Pseudo-code: the ranking layer, with a deterministic fallback

```python
# ---- policy lives here, in code, not in the model ----
CONF_FLOOR = 0.55          # below this we do not trust the model
USE_FUZZY_RANKING = True

def order_candidates(state, candidates):
    """candidates: list of (orbit, partial_state).  Returns them in the order to try."""
    if not USE_FUZZY_RANKING:
        return canonical_order(candidates)          # the deterministic fallback (see §4)
    res = jev.ask(QUESTIONS, state=state, options=[c.orbit for c in candidates])
    if res.confidence < CONF_FLOOR:
        return canonical_order(candidates)          # ABSTAIN -> deterministic path
    order = sorted(candidates, key=lambda c: -res.probabilities.get(c.orbit, 0.0))
    # the model may only RANK: every candidate stays in the list
    assert set(order) == set(candidates)
    return order
```

**Three properties to keep, and one to test:**

1. **Legality is decided by the engine, never by the model.** A `Noul` answer of 0.3 is *not* a
   veto; it is a low score.
2. **The model may only reorder.** The `assert` above is the mechanical guarantee.
3. **Confidence gating** means the model can be switched off with no loss of correctness.
4. **Test:** the 5×5 must still return 8,045, and the 4×4 counter-example still `{112, 304}` —
   with a *node budget*, so a good order shows up as fewer nodes and a bad one as more.

### 2.5 Where the "image/vision" variant fits

The user floated vision judgement as an alternative to calculation. The concrete, defensible
version: **the d-field is a picture of a flow field** — a terrain whose valleys point at the
capitols. A vision model looking at the rendered 11×11 numbers could be asked *"where does the
terrain look flat and wide?"* — i.e. *"where is there likely a big state?"* — and that is a
**prior on the area bounds**, which is exactly the signal the solver already wants (§2 of
`ALTERNATIVES.md`).

Treat it as **one more `Score` question, with a `confidence`**, never as a constraint. And note
the honest cost: a vision call per node is far too slow, so this can only be used at the **top of
the search** (to seed or to order a handful of candidate states), not inside the inner loop.

---

## 3. Route B — speculate the number of capitols (idea 3)

### 3.1 The idea, sharpened

*"Shapes are many. But capitols are less."* The capitol set is the small object: the hitting set
already says the 11×11 has **≥ 4 hidden capitols** (≥ 6 total), drawn from a **64-cell** pool.
Everything else — the shapes — is determined (or over-determined) once the capitol set is fixed,
because **each state's growth is anchored at its capitol**: only the 7 symmetries that fix a given
cell are viable, instead of 2,422.

⇒ Speculating the *number* `k` of capitols turns one enormous search into a sequence of much
smaller ones.

### 3.2 Pseudo-code

```python
def capitol_sets_by_size(N, hints, k_min, k_max):
    """Enumerate capitol sets of EXACTLY size k that hit every demand."""
    demands = []                       # (hint cell, radius) for every published cell
    for (r, c), v in hints.items():
        if v == 0: continue            # a revealed capitol: it is in the set already
        demands.append(((r, c), (v + 1) // 2))
    known = {x for x, v in hints.items() if v == 0}
    pool = {c for c in all_cells(N)
            if c not in hints or c in known}          # a d>0 cell can never be a capitol
    for k in range(k_min, k_max + 1):
        for C in hitting_sets_exactly(demands, pool, k):
            if C & known != known: continue
            if not consistent_with_d1(C, hints): continue   # the d=1 rule (§3 of ALTERNATIVES.md)
            yield k, C

def hitting_sets_exactly(demands, pool, k):
    """Classic set-cover enumeration with a size cap: pick one uncovered demand, try each
    candidate that covers it, recurse.  Prune when |chosen| + ceil(uncovered / max_cover) > k."""
    ...
```

### 3.3 Anchored growth — the whole point

```python
def grow_from_capitols(N, hints, C):
    """Every state is grown from its own capitol: the symmetry is pinned from the first step."""
    states = []
    for c in C:                                   # each capitol anchors exactly one state
        placed = False
        for sym in symmetries_fixing(c):           # only 7 of 2,422 survive this filter
            for S in grow_states(anchor=c, sym=sym, n=N):
                if not engine_legal(S): continue
                if area_of(S) < need(S): continue  # the area lower bound
                states.append(S); placed = True; break
            if placed: break
        if not placed: return None                 # this capitol set is impossible
    return states
```

### 3.4 The honest accounting

* **The win is the anchoring**, not the number `k` itself: 2,422 candidate symmetries become 7 per
  state, and the state shape is no longer searched blindly.
* **The cost is the enumeration of capitol sets.** The minimal hitting sets are 120 (size 4
  hidden); sets of size 5, 6, … are far more numerous, so `k` must be capped by something. Two
  useful caps: the total area (121 cells; every capitol state has area ≥ 1) and the pool size
  (64). In practice `k` = 6…12 is where the trade still looks favourable — **and that range is an
  assumption to be measured, not a fact.**
* **This is DESIGN §7's pipeline, finally implemented.** Until now the hitting set was computed and
  never used. The `d = 1` rule gives the extra consistency check in `consistent_with_d1`.

### 3.5 What `k` buys that is *not* about shapes

A small, provable bonus: **the number of odd-area states is odd** (the frame is 121 cells, an odd
total, and the areas sum to it). Every state *with* a capitol has odd area. So the number of
odd-area *filler* states has the same parity as `k + 1`. Filler states are exactly the ones the
search cannot pin down, so this is a free constraint on the part of the solution that is hardest.

### 3A. The filler states — the one real problem, and a trap in its first formulation

**The diagnosis** (measured by the peer session on the 4×4): of the 135 filler states closed, only
**16% have their area pinned** by the area lower bound; **84% are completely free**. The filler
states are where the explosion lives, and the tight-edge route (withdrawn, §4 of
`ALTERNATIVES.md`) cannot touch them because it pins the *smaller* of two states.

**The first formulation of the fix is vacuous, and the trap is worth writing down.**

The natural idea: *if a hinted cell `z`'s optimal path to its capitol passes through a filler state
`F`, then each step inside `F` costs `|F|`, so*

> |F| ≤ D(z) − (the cheapest cost of a path that avoids F)

**That bound is empty.** The paths that avoid `F` are a *subset* of all paths, so the cheapest
avoiding path is **never cheaper** than the true minimum:

```
d_avoid(z, F) >= D(z)        for every z and every F
```

⇒ the right-hand side `D(z) − d_avoid(z, F)` is **≤ 0**, and the bound says `|F| ≤ 0`. ❌
**MEASURED** on the official 5×5, for the 4-cell filler state and every published cell: the
avoiding cost is 21 vs D=12, 14 vs D=8, and equal to D everywhere else — **never below**. The
sign is the wrong way round.

### 3A.1 What survives: the crossing is *detectable*, and it is worth something

The same computation gives a **usable** statement. Define

> `d_avoid(z, F)` = the cheapest cost from `z` to any capitol **with F's cells removed**
> (the other states' sizes are known, so this is one Dijkstra).

Then

> **If `d_avoid(z, F) > D(z)`, the optimal path from `z` must pass through `F`.**

**MEASURED** on the official 5×5: for the 4-cell filler state, exactly two published cells have
`d_avoid > D` — (0,0) with 21 vs 12, and (1,0) with 14 vs 8. Those are precisely the cells whose
optimal path crosses the filler state; all the others have `d_avoid = D` (their path avoids it).

⇒ So the **detection** of "this cell's path goes through this filler state" is exact and cheap
(one Dijkstra per (cell, state) pair, cacheable). What is *not* yet obtained is a clean bound.

### 3A.2 The surviving form: an equation in the area, not a bound

Write the optimal path of `z` as: reach an outside cell `u` (cost `c_prefix`), cross into `F` at
`p` (cost `min(|A|, a)`, where `A` is `u`'s state and `a = |F|`), take `k` **internal** steps
inside `F` (cost `k·a` each), cross out at `q` (cost `min(|B|, a)`), and continue to a capitol
(cost `c_suffix`):

> **D(z) = c_prefix(u) + min(|A|, a) + k·a + min(|B|, a) + c_suffix(v)**

Everything except `a` and `k` is computable **without knowing `a`** (the prefix and suffix paths
avoid `F`), and `k` is bounded by the *geometry of the candidate*: the path inside `F` visits at
most `a` cells, so `k ∈ {1, …, a−1}` and the possibilities are enumerable per candidate.

**MEASURED** — for the 4-cell filler state of the official 5×5, the optimal path of (0,0) is
`(0,0) → (0,1) → (1,1) → (2,1)` with costs `4 + 4 + 4`: crossing into the filler state costs
`min(7, a)`, one internal step costs `a`, crossing out costs `min(a, 7)`. Substituting gives
`12 = min(7,a) + a + min(a,7)`, which has **exactly one solution: a = 4** ✓ — the true area.

⇒ So the surviving form is a **test on a candidate state**, not a bound: *a candidate filler state
is inconsistent if no (u, p, q, v, k) makes the equation hold with a = |F|.* Whether that test
ever bites is an **empirical** question — see §3A.3.

### 3A.3 The measurement protocol (and the baseline discipline)

**Do not run this on the shared machine; it is specified here so that whoever has the CPU can run
it.** The protocol has one hard rule:

> **Measure every candidate constraint ON TOP OF the current solver** (area lower bound L3/L2 +
> the `d = 1` rule + the canonical growth order + the hybrid lower-bound check). Otherwise the
> constraint gets credited with the 15% that the ordering change already delivered.

```
def measure_filler_bound(N=4, hints=..., budget=...):
    # 0. baseline: the current solver's node count on the 4x4 fixture
    # 1. enumerate all 562,308 tilings of the 4x4 (the oracle)
    # 2. for every tiling T:
    #       for every filler state F in T:
    #           for every published neighbour z of F:
    #               if d_avoid(z, F) > D(z):          # the path crosses F
    #                   if not equation_solvable(F, z, T):   # §3A.2
    #                       record "the test would have pruned T"
    # 3. report: how many tilings survive the test, and how many nodes the
    #    corresponding prune would save
```

**What "success" looks like**: the test prunes a *substantial* fraction of tilings **without
pruning the true one** (the 4×4 fixture must still yield `{112, 304}`; the 5×5 must still yield
8,045). **What "failure" looks like**: the test prunes almost nothing, or it prunes the true
tiling — in which case this whole branch is dead and the honest conclusion is the one in §3A.4.

### 3A.4 The conclusion this branch may be heading towards — and why Route A then becomes the answer

There is a real possibility that **no local constraint pins the filler areas**, because the
published numbers simply do not say enough about the states that carry no flow. If the §3A.3
measurement comes back empty, then the exact search has **no more constraints to find**, and the
remaining gap is not a missing lemma — it is the price of exactness.

⇒ **That is the strongest argument for Route A**, and it is worth stating plainly:

> The official puzzle asks for **one number**. If the exact route has run out of *provable*
> constraints, the simulation route is not a consolation prize — it is the appropriate tool, and
> the three-valued "exhaustive" verdict is a property of our *generator*, not of the puzzle.

⇒ So §3A.3 is worth running **even if the test fails**, because a negative result is itself the
decision: it says "stop looking for constraints, switch tools".

---

## 4. Route A — a touch of simulation (idea 1)

### 4.1 What to simulate

Not the *search* — the *tiling*. The energy of a candidate tiling is measurable, and the local
moves between tilings are cheap.

```python
def energy(T, hints):
    d = engine.cost_field(T)                       # one Dijkstra over n^2 cells
    e = sum(abs(d[x] - D[x]) for x in hints)       # how far off the published numbers are
    e += BIG * engine.count_structural_violations(T)   # symmetry / connectivity / one capitol
    return e
```

**Moves** (every one validated by the engine, never by ad-hoc checks):

| move | effect |
|---|---|
| re-symmetry | re-derive a state's symmetry (or move its axis/centre) |
| move a cell | shift one cell from state A to state B |
| split / merge | split a state into two legal states, or merge two adjacent legal states |
| add/remove a capitol | turn a state into one with or without a capitol |
| shift a state | translate or rotate a whole state, if it stays on the board and legal |

### 4.2 Pseudo-code

```python
def anneal(N, hints, seed, iters, skeleton=None):
    rng = random.Random(seed)                     # fixed seed: runs are reproducible
    T = skeleton or random_legal_tiling(N)        # §3's skeleton, if we have one
    E = energy(T, hints)
    best, best_E = T, E
    for it in range(iters):
        T2 = propose(T, rng)                      # one legal move
        E2 = energy(T2, hints)
        # ITERATED LOCAL SEARCH: pure hill-climb, plus a kick when stuck.
        # NOT record-to-record: measured on the 4x4, a tolerance of 0 reached E=0 while
        # tolerances of 5 and 20 stalled at E=90 -- the tolerance lets the current state
        # drift away from the best-ever, so the search wanders inside the band instead of
        # climbing.  On this landscape (integer, stepped, extremely sparse) climbing is
        # exactly what works.  Keep the tolerance as an option, default 0.
        if E2 <= E or (stuck(it) and kick(T, rng)):
            T, E = T2, E2
        if E < best_E:
            best, best_E = T, E
        if E == 0:
            return engine.verify(best)            # exact verification, never a shortcut
    return None
```

**Record-to-record travel** rather than plain simulated annealing: the accept test is "close to
the best seen", which escapes local minima more reliably on combinatorial landscapes, and it has
no temperature to tune.

### 4.3 The gates, in increasing cost — run them in this order

1. **5×5, 25 cells, ~10⁵ moves (seconds).** The official 5×5 example: 10 published numbers, the
   answer is 8,045, and the true partition is known. *If the annealer cannot find the 5×5, the
   11×11 is hopeless* — so this gate is the go/no-go, and it costs seconds.
2. **5×5 with a wrong hint** (perturb one published number). The annealer must then fail to reach
   `E = 0` — this tests that the energy is actually reading the numbers.
3. **4×4 counter-example**: the annealer must find a tiling with answer 304 *or* 112, and the
   engine must confirm the answer set is `{112, 304}`.
4. **11×11**: only after (1) passes.

### 4.4 The failure mode of the exact route is the *diagnostic* of the simulation route

The exact route's failure looks like this: **26 M nodes, 0 answers, no information**. A simulation
that also fails can do better than that:

> **A near miss is an output, not a failure.**

⇒ **Never stop at "E = 0 or nothing".** Record the *best* energy reached and, crucially, **which
published numbers disagree and by how much**. A best energy of 2 with "the only mismatch is
(7,2), off by 2" is a **constraint on the true solution** — exactly the kind of lead the exact
search cannot produce, because it never reaches a partial state worth reporting.

```
def anneal_report(...):
    found = Counter()          # answer -> how many restarts produced it
    best = None
    for restart in range(R):
        T, E = anneal(..., seed=restart)
        if best is None or E < best.E: best = snapshot(T, E)
        if E == 0:
            found[engine.answer(T)] += 1
    return {
      "answers_found":     sorted(found),                 # what we ACTUALLY found
      "discovery_counts":  dict(found),                  # how often each one appeared
      "answers_exhaustive": False,                       # can we prove there are no others? no
      "uniqueness":        False if len(found) > 1 else "unknown",
      "best_energy":       best.E,
      "mismatches":        [(x, D(x), d_T(x)) for x in published if d_T(x) != D(x)],
    }
```

**The three layers must not be merged** — they answer different questions, and the simulation
route's `unknown` has a *different reason* than the exact route's:

| layer | question | simulation route | exact route |
|---|---|---|---|
| `answers_found` | what did we actually find? | the answers, each with its partition and engine verification | the same |
| `answers_exhaustive` | could there be more? | **cannot be proved ⇒ always `false`/unknown** | `true` only if the search exhausted |
| `uniqueness` | is the answer unique? | ≥2 found ⇒ `false`; 1 found ⇒ **`unknown`** | ≥2 ⇒ `false`; 1 found + exhausted ⇒ `true`; else `unknown` |

⇒ **"we found exactly one answer" must NEVER be written as "the answer is unique".** Measured
reason (peer, 4×4): 30 restarts × 20,000 steps gave `{304: 4, 112: 2}`; a shorter run
(6 restarts) gave `{304: 2}` — **the rarer answer was simply missed.** ⇒ The *discovery rate* is
itself a reportable quantity ("answer A appeared in 4 of 30 restarts, answer B in 2 of 30"), and it
tells the reader how much more may be out there far better than a bare `unique=unknown` does.

**And "E = 0" is not enough on its own.** The 4×4 counter-example proves that this puzzle family
can have **two different answers with the identical cost field** — so a single zero-energy
solution does not certify the answer. The simulation must therefore collect an **answer set**
over many restarts (task B of §1.1), and the report should say `answers_found = {304, 112}`
rather than "the answer is 304".

### 4.4b Gate 0 — the landscape is benign, and that settles the route

**MEASURED** (peer session, `tools/energy_landscape_4x4.py`, all 559,585 legal 4×4 tilings,
energy = Σ|d_T(x) − D(x)| over the published cells):

| energy | tilings |
|---|---|
| **E = 0** | **2** ← the two solutions (answers 112 and 304) |
| E = 1 | 2 |
| E = 2 | 59 |
| E = 3 | 74 |
| E = 4 | 727 |
| E = 5 | 714 |
| E = 6 | 5,431 |
| max | 508 |

⇒ **The gap between the best solution and the best non-solution is 1** ⇒ the true solutions are
**not isolated points** ⇒ a gradient exists to walk ⇒ **the simulation route is GO.**

**And the sharper reading** (the number that matters most):

| neighbourhood | tilings | distinct answers | tilings whose answer is **not** 112/304 |
|---|---|---|---|
| 0 < E ≤ 1 | 2 | 3 | 2 |
| 0 < E ≤ 2 | 61 | 13 | 61 |
| 0 < E ≤ 5 | 1,576 | 84 | 1,576 |
| 0 < E ≤ 10 | 55,333 | 420 | **55,327 (99.99%)** |

⇒ **The energy is a weak signal for *which answer* and a strong signal for *how close to a
solution*.** Among the 55,333 tilings within E ≤ 10, essentially every one leads to the **wrong**
answer. ⇒ The "E = 0 is not a certificate" caution of §4.4 is now a number.

⇒ **The order-of-magnitude argument that makes this route the right tool**: the target set has
**2 members in 559,585** — **0.0004%**. Exhaustive search cannot find a set that small inside a
space that large; a local search that can walk a one-step gradient can. That is the difference
between "the exact route is exhausted" and "the exact route is not the right tool", and it is a
quantitative statement, not a hope.

### 4.4c What the *right* move graph looks like

**The hard constraint on any move: the tiling must keep covering the frame.** That single fact
rules out the most obvious formulation — *"replace one state with another legal state of a
different area"*. If the areas differ, the cells of the old state are covered by nobody and the
tiling is illegal. ⇒ **A move has to preserve the covering, which means it has to be a
split or a merge, not a replacement.**

⇒ **The atomic moves that change a state's area by exactly one, and need no state catalogue:**

```
def neighbours(T):
    """Every neighbour of T differs in ONE state, and the area DELTA is 1 where possible."""
    for S in T.states:
        # (1) PEEL: take one cell off S.  The cell becomes a 1x1 state -- which is a capitol --
        #     and the rest must still be a legal state.  Area split: (1, |S|-1)  => delta 1.
        for c in S:
            rest = S - {c}
            if rest and engine.is_legal_state(rest):
                yield T.replace_state(S, rest, {c})
        # (2) SPLIT: cut S into two legal states.  Area split: (p, |S|-p)  => delta can be 1.
        for A in proper_subsets(S):
            if engine.is_legal_state(A) and engine.is_legal_state(S - A):
                yield T.replace_state(S, A, S - A)
    # (3) MERGE: two adjacent legal states into one legal state.  (a, b) -> (a+b).
    for (A, B) in adjacent_state_pairs(T):
        if engine.is_legal_state(A | B):
            yield T.replace_states(A, B, A | B)
```

⇒ **the good news: the fine step (Δarea = 1) is catalogue-free.** The catalogue was only needed
for the "replace with a different area" formulation, which was wrong. The peer's orbit-level
move (add/remove one σ-orbit ⇒ Δarea ±2 or ±4) is a **coarser variant of the same idea**, not a
necessity — so the 11×11 does not have to settle for ±2/±4.

⇒ **But the area delta is not the whole story, and this is what the 4×4/5×5 difference is
about.** A *peel* creates a new capitol, and a new capitol changes the d-field **globally** — so
the energy can jump by much more than 1. Measured by the peer: on the 4×4 (16 published numbers,
the d-field nearly pinned) the peel moves walk *down* the gradient; on the 5×5 (10 published
numbers) they do not. ⇒ **the granularity of the energy change is governed by how well the
published numbers pin the d-field, not by how fine the move is.** A finer move cannot fix a
sparsely-pinned landscape; it can only help when the landscape is already nearly pinned.

⇒ **⇒ therefore: do not guess the move set. Measure it.** The decisive experiment is tiny:

```
# 4x4: what connects an E=1 tiling to an E=0 tiling?
for T in tilings_with_energy(1):                 # only 2 of them
    for T2 in neighbours(T):                     # one legal split / merge / peel away
        if energy(T2) == 0:
            record(move = diff(T, T2), area_delta = ..., energy_delta = ...)
```

⇒ The answer is **the move the graph must contain, and the step size it must have** — and if no
single move connects them, then the graph needs a wider step and the energy's granularity is
coarser than the gap of 1 suggests. Either way the answer is a fact instead of a guess.

### 4.4d The relaxed d-field: **withdrawn**

*Originally proposed here: the true d-field is undefined when a partition has no capitol, so
relax the capitol set to "every cell that is the unique fixed point of some symmetry of its own
state", which makes the field defined everywhere and smooth.*

**Withdrawn, and the peer's objection is right.** A state with **no symmetry at all** — the normal
intermediate of a growth — has *no* uniquely-fixed cell, so it contributes *no* candidate capitol,
so the relaxed field is **still undefined there**: the wall survives. The only way to make it
defined is to let every cell of an asymmetric state be a candidate capitol — and then every cell
is its own candidate at distance 0, so `d_relaxed ≡ 0` and **the objective loses all resolution**.

⇒ **The wall is narrower than I thought, and it does not need a new objective.** The d-field of a
partition is defined as long as the partition has **at least one capitol**; a *legal* state with no
capitol (a 1×3 bar) is no obstacle at all, because its cells flow to some *other* state's capitol.
The only undefined case is "the whole partition has no capitol" — and that state is rare and
**self-escaping**: the working move (peel a cell into a 1×1 state) *creates* a capitol.

⇒ So the wall is removed by **making the penalty climbable**, not by smoothing the objective:
same-scale penalty (the peer's `BIG = 5` instead of `BIG = 1000`) + a pure hill-climb gets the 4×4
to `E = 0` directly, and no relaxed field is needed. Measured: `BIG = 1000` never recovered;
`BIG = 5` reached `E = 0` in 79 s.

⇒ **Two rules that came out of that** (also added to the cross-agent rules):
1. **A penalty must be on the scale of the objective, and a penalised configuration must have a
   path back.** A penalty an order of magnitude above the objective is a **wall**, not a penalty.
2. **When a search stalls, measure the landscape before tuning parameters.** Gate 0 answered in
   three minutes what a week of parameter fiddling would not have.

> **Relaxed definition.** The candidate capitol set of a partition = every cell that is the unique
> fixed point of some symmetry of its own state (a *capitol candidate*). Define
> `d_relaxed(x) = min over candidates c of the cost of the cheapest path from x to c`.
> The true d-field is the special case where the candidate set happens to be exactly the real
> capitols, and `d_relaxed ≤ d_true` always.

⇒ **two-phase design**: *optimise* the relaxed energy (smooth, wall-free, defined everywhere),
then *verify* every candidate with the strict engine. A relaxed-E = 0 partition is a **candidate**,
not a solution — and the strict check is what turns it into one.

### 4.4e Two rules about penalties and stalls, from the same failure

1. **A penalty must be on the scale of the objective, and a penalised configuration must have a
   path back.** `BIG = 1000` against an energy whose scale is 10–500 is not a penalty, it is a
   **wall**: the search cannot climb out of a single violation. The test: *can the search return
   from every configuration it can reach?* If not, the penalty is a wall.
2. **When a search stalls, measure the landscape before tuning parameters.** Gate 0 (§4.4b) cost
   three minutes on the 4×4 oracle and answered the question that a week of parameter fiddling
   would not have: *is there still a gradient?* Use the small exhaustive oracle, not the big
   instance.

### 4.4f The energy evaluation is the bottleneck on the 11×11

One evaluation = one shortest-path computation over 121 cells with integer edge weights (the
state sizes). A heap-based Dijkstra is ~0.5 ms in Python ⇒ 10⁴ moves/s would cost 5 s of CPU per
second of annealing. ⇒ Use a **bucket queue (Dial's algorithm)** — the weights are small integers,
so the bucket queue is O(E + max weight) and several times faster — and cache the d-field per
candidate state set.

### 4.4g The local curvature: measured, and it decides the acceptance regime

**The measurement that the move graph needed.** No table, no oracle: take a *known* solution, list
its legal neighbours (peel / split / merge), and compute the energy of each. The lowest one is the
**local curvature** — how expensive the cheapest step away from the solution is.

**MEASURED** ✅ (the two 4×4 solutions and the official 5×5 solution):

| solution | neighbours | energy distribution of the neighbours | cheapest neighbour |
|---|---|---|---|
| 4×4, answer **304** (12 singletons + one 4-bar) | 20 | 0×1, 1×2, 2×10, 4×4, 6×3 | **E = 0** — the split of the 4-bar into two 2-dominoes *is* the other solution |
| 4×4, answer **112** (12 singletons + two dominoes) | 24 | 0×1, 2×16, 4×4, 6×3 | **E = 0** — the merge of the dominoes *is* the other solution |
| 5×5 official, answer **8045** (states 3/4/7/11) | **9** | 11×1, 12×2, 15×1, 23×3, 25×1, **72×1** | **E = 11** — *no neighbour below 10 at all* |

⇒ **The two 4×4 solutions are one split/merge apart.** That is the edge the annealer walks, and it
is why the 4×4 works.

⇒ **And the 5×5's solution sits on a cliff**: the cheapest step away costs 11, and it has only nine
neighbours at all. **That is why the annealer cannot reach it** — not because the move set is
coarse, but because the local geometry offers nothing to climb.

**The mechanism is the solution's *shape*, not the hint density.** Repeating the 4×4 measurement
with random subsets of the published numbers leaves the cheapest neighbour at E = 0 all the way down
to **2 of 16 hints** (measured) — so sparsity alone is not what creates the cliff. What creates it
is a solution made of **few large states**: every move then changes a state's area by a lot, and
every path crossing that state changes cost ⇒ the d-field shifts ⇒ the energy jumps. A solution
made of many small states (the 4×4: twelve singletons) has a neighbourhood of cheap moves.

⇒ **⚠️ The consequence that matters for the 11×11: the 4×4's success does not transfer.** The
published 11×11 numbers force large states (the neighbours (10,8)=77 and (10,9)=61 ⇒ **both**
states have area ≥ 16), so the 11×11's solution is a *few large states* solution — the cliff
regime, not the gentle one.

⇒ **⇒ the curvature measurement tells you which regime you are in** — and the *two-step* basin
says how big the hole is. **MEASURED** (the minimum over the states *reached*, never over a set
that includes the solution itself — the solution has E = 0 and would make every minimum read 0):

| solution | cheapest 1-step | cheapest 2-step | |
|---|---|---|---|
| 4×4, answer 304 | 0 (the other answer) | 2 | gentle |
| 4×4, answer 112 | 0 (the other answer) | 1 | gentle |
| **5×5 official, answer 8045** | **11** | **17** | cliff |

⇒ **⇒ the 5×5's neighbourhood FUNNELS UPWARD when measured *outward*.**

> ⚠️ **⚠️ THAT MEASUREMENT WAS READ IN THE WRONG DIRECTION — see §4.4g.1. The landscape is a
> funnel that funnels *inward*: entering the solution is ONE step from every neighbour.**

⇒ ⇒ **and the density argument says this matters more and more as the puzzle gets sparser**: the
E = 0 set of the 4×4 is 2 tilings in 559,585 (0.0004%); the 5×5's is far smaller; the 11×11's
would be smaller still. ⇒ **⇒ at that density, "can you jump in the right direction" beats "how
far you jump" by orders of magnitude.**

### 4.4g.1 ⚠️ CORRECTION: the landscape is a funnel, and a **greedy descent** walks it

The measurement above ("leaving the solution costs ≥ 11; two steps out costs 17") is **correct**,
but it was read in the wrong direction, and the reading produced a wrong conclusion — which was
then handed on as advice, so it is worth writing down properly.

**MEASURED** — a **pure best-improvement descent** (no randomness, no annealing, no tolerance:
*always move to the cheapest legal neighbour*):

| instance | start | result |
|---|---|---|
| 4×4 counter-example | **60 random legal tilings (cold start)** | **60/60 reach E = 0**, average **3.0 steps** |
| 5×5 official example | each of the **23 neighbours** of the solution | **23/23**: the single cheapest legal move lands **exactly on the solution** (E → 0) — from E = 11, 12, 15, 23, 25 and even 72 |
| 11×11 official | the all-singletons start (121 states) | **stalls at E = 480** after 40 steps (82 states) — a local minimum with no improving neighbour |

⇒ **⇒ entering the solution is ONE step from every one of its neighbours.** Leaving it is
expensive; *entering* it is trivial. **The landscape is a funnel, and it funnels inward.**

⇒ **⇒ so the conclusion reverses:**

* ❌ "a cliff landscape forces the search to accept worsening moves" — **withdrawn**; the 5×5's
  solution is reached by a **monotone descent** from every neighbour.
* ❌ "the annealer needs a big kick and a tuned tolerance" — **not needed**. What the annealer did
  was take *sampled* moves; a **random walk cannot walk a funnel**, whatever the tolerance. That
  is why the tolerance sweep (0/5/11/15 → best E = 50) never moved: **the moves were random, not
  greedy.** The fix is not a better schedule, it is a different rule.
* ✅ **the right primitive is a greedy best-improvement descent**: enumerate the legal neighbours,
  evaluate them, step to the cheapest. It is deterministic — and it was **already written**: the
  peer's `src/moves.py::curvature()` returns `cheapest` and `cheapest_move`, i.e. **the descent
  was implemented and then an annealer was run instead of it.**

⇒ **⇒ and it is affordable.** The legal-move set is tiny next to the raw candidate set: from the
all-singletons start, **220 of 7,260 merge pairs are legal (3%)** ⇒ ~220 energy evaluations per
step ⇒ **~0.5 s/step** ⇒ a few hundred steps is a few minutes. The per-step cost is set by the
number of *legal* moves, not by the number of candidates.

⇒ **⇒ and where the 11×11 still needs help, the model's job is now precisely defined** (§2.4):

* the descent **stalls at E = 480** from the all-singletons start ⇒ the instance needs a **better
  start or an escape**, not a better step rule;
* ⇒ **the obvious candidate is the seed data that is currently unused**: seed the descent with a
  capitol set from the hitting set (DESIGN §7) instead of the all-singletons start, and see
  whether the descent then runs to E = 0. That is *Route B feeding a greedy descent* — a new
  algorithm that uses both halves of the work done so far;
* ⇒ and the diagnostic to instrument is **"how often does the greedy descent stall, and at what
  energy?"** — that number is what the model has to beat.

### ⚠️ Corrected: the lever is a **good** jump, not a **big** one

The first version of this note concluded that a cliff landscape *forces* the search to be allowed
to get worse. **The peer tested that directly and it is false** — a tolerance sweep on the 5×5:

```
5x5 official example, 6 restarts x 30,000 steps:
  tolerance  0: best 50   answers {}
  tolerance  5: best 50   answers {}
  tolerance 11: best 50   answers {}      <- the measured gap
  tolerance 15: best 50   answers {}
  tolerance 25: best 60   answers {}      <- worse
```

⇒ **⇒ allowing the current state to degrade is not enough.** A tolerance only *permits* a
worsening; it does not say *which direction* to worsen in. The search wanders inside a band of
radius 11 while the solution sits at one particular edge of that band.

⇒ **⇒ the lever is a GOOD jump.** And the arithmetic can already offer the local version of one:
the **cheapest legal neighbour**, even if it is worse — "the best jump this terrain offers". The
**model's** version of the same thing is a jump chosen by the *terrain* (a wide plateau in the d-field
= a large state), which is information the arithmetic cannot rank.

⇒ **And the reason this matters more than the size of the jump** is density. The E = 0 set of the
4×4 is **2 tilings in 559,585 (0.0004%)**; the 5×5's must be far sparser (of the same order as
10⁻⁹). ⇒ **⇒ at that density, "can you jump in the RIGHT direction" beats "how far you jump" by
several orders of magnitude.** That is the quantitative form of the model's role.

⇒ **⇒ and the acceptance criterion for the model becomes measurable** (the peer's addition, and it
is the right one):

> **The model may change the ORDER of the candidates, never the SET.**
> ⇒ Verify it by running with the model **off** and **on**, and comparing **how many restarts each
> needs to reach E = 0** — *not* the final answer, which is identical either way. **That ratio is
> the model's value, and it cannot be negative**, because the engine is the referee and the model
> only reorders.

⇒ **⇒ and that is where the System One model earns its place (§2.5): a hill-climb in a cliff
landscape has nothing to climb, so what is needed is a good **big jump** — and choosing *where* to
jump is exactly a judgement call, not an arithmetic one.**

### 4.4h The multi-window ladder: speculate small, refute bigger, check globally

The user's own way of playing, which turns out to be a well-founded strategy:

> speculate locally on a small grid, refute/trim with the cell readings on a bigger one, then
> check globally.

**The formal shape of it.** The speculation inside a `k×k` window is a partition of its cells
into groups — "which cells belong to the same state" — and the number of such partitions is the
**Bell number B(k²)**:

| window | speculation space B(k²) |
|---|---|
| 2×2 (4 cells) | **15** |
| 3×3 (9 cells) | **21,147** |
| 4×4 (16 cells) | **10,480,142,147** |

⇒ **⇒ the ladder is not about making the enumeration smaller — the last rung is the same
10-billion problem. It is about making the REFUTATION cheaper and more local**: a speculation that
a bigger window's readings kill is discarded before it ever reaches the global search.

**MEASURED — how strong is the local refutation really?** The only local force available is the
**magnet** (the user's word): a cell reading 0 is a capitol, so its state must be symmetric about
it, which forces the local pattern; a cell reading 1 must have a 1×1 state next to it. Counting the
partitions of a 3×3 window that survive the magnet's symmetry constraint, on the real 11×11:

| window | all local partitions | surviving the magnet | survive |
|---|---|---|---|
| 3×3 centred on a `d = 0` capitol | 21,147 (+203) | 6,988 | **32.7%** |
| 3×3 centred on a `d = 1` cell | 42,497 | 13,783 | **32.4%** |

⇒ **⇒ the local refutation removes about two thirds of the local patterns — useful, but nowhere
near decisive.** The global arithmetic (the real d-field) is what does the work.

**The caveat that explains why**: **symmetry and area are global properties.** A state's area is
not determined by a window, and a state's symmetry is not either (the mirror of a cell inside the
window may lie outside it). ⇒ **a window's readings cannot be evaluated in isolation at all** — the
local step has to be a speculation about *structure*, with the global arithmetic as the referee.

**⇒ ⇒ so the ladder's role, exactly: it is a PROPOSER, not a refuter.** And that is precisely the
slot the System One model is being asked to fill (§2.4) — which makes the two ideas one thing:

* the **ladder** = a deterministic proposer of local structures (which cells are grouped near each
  magnet);
* the **model** = a possibly better proposer of the same thing (it can read the *terrain*, which
  the ladder cannot);
* the **arithmetic** = the referee, always.

⇒ **⇒ and one refinement worth making if the ladder is to be used: put the windows where the
speculation space is small.** A window centred on a magnet and **aligned with a candidate symmetry**
has a much smaller space than a Bell number, because the local pattern is then "which orbits of σ
are included" rather than "which partition of the cells" — and a 3×3 window around a magnet has
only a handful of orbits.

### 4.5 A caution about the probabilities in §2

The decision model returns `probabilities`. **Those numbers are not calibrated** — a score of
0.7 does not mean "70% of the time this shape is right". Treat them as **ranking keys only**;
never as a probability in any threshold that claims to be a probability, and never as a
likelihood in a Bayesian argument. A ranking that is badly calibrated is still a fine ranking.

### 4.6 The honest limits

* **It cannot prove uniqueness.** For our *generator* it is therefore unusable as-is; for the
  *official puzzle* it is legitimate (§1.1). A separate counter-example hunt (§1.1, task B) is
  what buys confidence.
* **The landscape is rugged**: the cost field jumps (a 0 is a capitol), so a 0/1 mismatch count
  anneals badly. Use the sum of absolute deviations, with hard violations weighted heavily.
* **Every accepted state must be engine-legal**, or the annealer will wander through illegal
  configurations and the energy will be meaningless. This is the "engine is the only source of
  truth" rule, applied to a stochastic search.

### 4.7 The (5,10) trim — the seed the descent was missing

§4.4g.1 left one item open: *"the obvious candidate is the seed data that is currently unused:
seed the descent with a capitol set from the hitting set instead of the all-singletons start."*
A capitol set is a weak seed — it says only *where* the capitols are, not *how big* the blocks
around them are. The `d = 1` demand at (4,10) says much more, and it says it in one line.

> **The observation.** *(5,10) is the best starting point. Have you use it to trim? It should
> connect to a 8-cell and a 12-cell blocks, because of 9 and 13 reading.*

**MEASURED — the observation is correct, and it is provable, not a guess.**

**Step 1 — (5,10) is the ONE forced 1×1 state at that end of the board.** A `d = 1` cell is
served by a 1×1 state *adjacent* to it (PLAN D64), and the candidates for the demand at (4,10)
are (3,10), (5,10), (4,9). A 1×1 state at `x` makes **every** neighbour of `x` have `d = 1`, so a
neighbour with a published value > 1 refutes it:

| candidate | refuted by | why |
|---|---|---|
| (3,10) | (2,10) = **14** | a singleton at (3,10) would give d(2,10) = 1 |
| (4,9) | (4,8) = **4** | a singleton at (4,9) would give d(4,8) = 1 |
| **(5,10)** | — | **survives** |

⇒ **the demand at (4,10) forces exactly one 1×1 state, at (5,10)** — and the other two `d = 1`
demands ((2,5) and (3,6)) do *not* have a unique candidate, so (5,10) is the only *certain*
singleton on the board.

**Step 2 — the step the earlier ground map was missing: impute `d = 1` on the singleton's ring.**
A 1×1 state is its own capitol, so `d(5,10) = 0`, and every neighbour of it reaches a capitol in
one cost-1 step:

```
d(4,10) = 1   (published — and it is the demand that created the singleton)
d(5, 9) = 1   (imputed)
d(6,10) = 1   (imputed)
```

⇒ **this is the whole trim.** The previous ground map listed the bounds from *published*
neighbours only, so it never saw the two numbers that matter most in the bottom-right corner.

**Step 3 — the 9 and the 13 read off the ring.** For adjacent `x, y`, `|d(x) − d(y)| ≤ min(size_x,
size_y)`, so the state holding `x` has area `≥ |d(x) − d(y)|` (L2/L3):

| pair | difference | consequence |
|---|---|---|
| (6,9)=9 ↔ (5,9)=1 | **8** | state((5,9)) ≥ **8**, state((6,9)) ≥ 8 |
| (7,10)=13 ↔ (6,10)=1 | **12** | state((6,10)) ≥ **12**, state((7,10)) ≥ 12 |

⇒ **the singleton at (5,10) is flanked by an 8-cell block and a 12-cell block**, and the two
numbers that say so are the published **9** and **13**. The reading is *mechanical*: the cost of
crossing a block of size `m` is `m`, and the singleton's ring costs 1, so `9 = 8 + 1` and
`13 = 12 + 1`.

**Step 4 — a parity lemma that the two blocks share.** A state that HAS a capitol has **odd**
area: the capitol is one cell and every other cell lies in an orbit of size ≥ 2. ⇒ **an 8-cell
state and a 12-cell state have NO capitol at all.** Both blocks are *filler* states, like the
4-bar of the official 5×5. MEASURED over the whole enumeration: **0 of 623** eight-cell states
and **0 of 2790** twelve-cell states contain the anchor have a capitol.

**Step 5 — the one caveat, stated honestly.** Step 3 used `d(6,10) = 1`. That holds unless (6,10)
is itself a capitol. It cannot be a 1×1 state (a cost-1 step to it would give `d(6,9) ≤ 1`,
against the published 9), but it *could* be the capitol of a bigger state, and then the same
argument gives **9 and 13** instead of 8 and 12. ⇒ the 8/12 reading is the branch in which (6,10)
is **not** a capitol; the other branch is not refuted, only weaker. The tightness also needs the
tight edge (L1) to land on the ring: the drop 9 → 1 must be paid by one edge, so at least one of
state((5,9)), state((6,9)) is exactly 8, and at least one of state((6,10)), state((7,10)) is
exactly 12.

**Step 6 — the trim, run for real.** AODFS orbit growth (`src/grow.py`) from the two anchors,
then three sound filters:

| filter | what it says | 8-cell | 12-cell |
|---|---|---|---|
| — | legal states of that size containing the anchor | 623 | 2790 |
| F1 | a cell inside a capitol-less block must be able to leave it: `m · dist + 1 ≤ d` | 343 | 1014 |
| F2 | a path through the core is *one* path, so `d ≤ core_path`; a cheaper core path refutes it | — | — |
| F3 | the step-count lemma: the ball of radius `⌊(v+1)/2⌋` around a hint must still contain a cell that can be a capitol | — | — |
| — | **pairs that survive all three** | **40,862 of 347,802** | |

The best pair explains five published numbers **exactly**:

```
8-cell  [(2,9),(3,8),(3,9),(3,10),(4,8),(4,9),(4,10),(5,9)]        sym refH+refV+rot180
12-cell [(6,9),(6,10),(7,6),(7,7),(7,8),(7,9),(8,7),(8,8),(8,9),(8,10),(9,6),(9,7)]  sym rot180

d(4,10) =  1   core path =  1   EXPLAINS      d(7,10) = 13   core path = 13   EXPLAINS
d(6, 9) =  9   core path =  9   EXPLAINS      d(8, 8) = 45   core path = 45   EXPLAINS
```

⇒ the route the two numbers describe is literally there in the shapes: **(6,9) → (5,9) costs 8
(the 8-block) and (7,10) → (6,10) costs 12 (the 12-block), and each ends with a cost-1 step
into the (5,10) singleton.** The 8 and the 12 are not a coincidence of the arithmetic; they are
the two halves of the user's picture, and the shapes that carry them are enumerated.

**Step 7 — the seeded descent, which is what the trim was for.** With the core in place (the
8-block, the 12-block, the (5,10) singleton, everything else singletons) the greedy descent of
§4.4g.1 now runs *past* the point where the all-singletons start stalls:

| start | best E | steps | stuck? |
|---|---|---|---|
| all singletons (previous measurement) | **480** | 40 | **yes** — a local minimum with no improving neighbour |
| seeded with the (5,10) trim, best of 5 pairs | **236** | 200 | not yet — but see below |
| the same pair, run for 1,200 steps | **236** | 1,200 | **yes** — a plateau at E = 236 |

⇒ **the seed halves the stall energy (480 → 236) and that is all it does.** The 1,200-step run
reaches E = 236 within about 100 steps and then stays there for 1,100 more. The seeded
descent is therefore **not** the mechanism that finishes this instance: it is the mechanism
that finds the right basin, and the shapes still have to be *grown* (Route A / AODFS) from
there. The other four seeded starts land at E = 260 / 289 / 257 / 244, all of them still
descending at step 200 — the same shape of result.

⇒ **the honest caveat: none of them reached E = 0.** A lower E is progress, not a solution.
The only thing that counts is `E = 0` verified by the engine.

**Where this goes next.** The plan for the rest of the search — the facet register, the 5×5
window decomposition, the conservation law as the join, and the per-facet pinning power — is
`docs/LOCALITY-PLAN.md`.

**What this does NOT establish.** The filters are one-sided, so a survivor is *necessary*, never
*sufficient*: 40,862 pairs survive, and the ranking among them is a heuristic. The branch in
§Step 5 is open. And a descent that reaches a lower E is progress, not a solution — the only
thing that counts is `E = 0` verified by the engine.

**What was deliberately NOT changed.** `src/` — the engine — is untouched. In particular the
solver's area bound (`src/solver.py::_need`) still uses *published* neighbours only, so it does
not see the ring-imputed `d = 1` bounds of §Step 2. Extending it is an engine change and
belongs on `main`, not on this branch.

---

## 5. How the three compose

```
for k, C in capitol_sets_by_size(11, hints, 6, 12):        # B: the skeleton
    skeleton = grow_from_capitols(11, hints, C)           # B: anchored growth
    if skeleton is None: continue
    T = anneal(11, hints, seed=hash(k, C), iters=..., skeleton=skeleton)   # A: fill the filler
    if T and engine.verify(T): return T
```

* **B** decides *where the flow comes from* (the capitols) and makes the search anchored.
* **C** decides *what to try next* inside the anchored growth — a ranking, never a veto.
* **A** decides *how to fill the rest* (the filler states), which is where the combinatorial
  explosion actually lives.

The three are complementary, and — this is the point — **each can be validated separately and
cheaply** on the 5×5 and the 4×4 before the 11×11 is touched.

---

## 6. The safety rules, in one place

1. **A fuzzy signal may only reorder.** Pruning on a non-proof can delete the truth.
2. **Legality is the engine's business.** A model never vetoes a shape.
3. **Confidence gating** ⇒ when the model is unsure, the deterministic path is used.
4. **Every score carries its evidence** (the `system1-measure` discipline): a shape's score must
   come with the signals that produced it, so a wrong score can be debugged rather than guessed
   at.
5. **Simulation finds candidates; the engine decides.** No result leaves the annealer without
   exact verification.
6. **Reproduction**: fixed seeds, recorded budgets, and the run log committed — the same
   discipline the data contract already demands.
7. **The 5×5 is the test bench.** Any new route must pass the 5×5 (answer 8,045) and the 4×4
   counter-example (answers `{112, 304}`) before it is allowed near the 11×11.

---

## 7. What is still open

* **The `k` range for the 11×11** (6…12?) is a guess that the capitol-set enumeration will
  settle, one way or the other.
* **Whether the conflict score (§2.3) helps or hurts** — a bad ranking can be worse than an
  arbitrary one, and only the node counts will say.
* **Whether the annealer needs the skeleton (§3) at all** — it might find the 5×5 without one,
  which would simplify the pipeline a lot.
* **How the vision variant (§2.5) would ever be fast enough** to sit inside the search, rather
  than only at its top.
* **Is there any constraint that pins a filler state's area?** (§3A) The naive version of the
  "path crosses the filler state" bound is *vacuous* — the avoiding paths are a subset of all
  paths, so `d_avoid ≥ D` and the right-hand side is ≤ 0. The surviving form is an equation in
  the area, which pins it *exactly* on the 5×5's one filler state — but whether it bites in
  general is empirical (§3A.3). **A negative result would be the most valuable outcome of the
  whole project**: it would say the exact route has run out of constraints, and that the
  simulation route (§4) is the right tool rather than a consolation prize.
* **Is (6,10) a capitol or not?** (§4.7, Step 5) The 8/12 reading of the (5,10) trim assumes
  it is not; the branch where it *is* gives 9 and 13 instead and is not refuted. The two
  branches predict different shapes, so one of them is wrong, and the descent may say which.
* **Does the seeded descent ever reach E = 0?** (§4.7, Step 7) It is at E = 236 after 200 steps
  and still descending, where the all-singletons start stalls at 480. The step budget is the
  only thing that stopped it.
* **Should the engine's area bound use the imputed `d = 1` ring?** (§4.7) `src/solver.py::_need`
  uses published neighbours only, so the solver's prune does not see the 8 and the 12 that the
  (5,10) ring makes visible. That is an engine change, and it belongs on `main`.
* **The 40,862 surviving (8-cell, 12-cell) pairs** (§4.7) are *necessary*, not sufficient. The
  three filters are one-sided, so something else has to rank them — and the ranking is where the
  model of §2 would earn its place.

---

## 8. Where the pieces live

| file | what it holds |
|---|---|
| `docs/ALTERNATIVES.md` | the discussion log: the analogies, their translations, the measurements |
| `docs/DESIGN.md` §3 | the authoritative AODFS design |
| `src/rules.py`, `src/cost.py` | the engine: legality and the cost field (the only validators) |
| `src/hitting.py` | the hitting set, and `singleton_demands` (the `d = 1` rule) |
| `src/grow.py` | the growth machinery |
| `system1-measure` (separate repo) | the measurement side: question sets, composition, rules — the natural home for the §2 question sets |
