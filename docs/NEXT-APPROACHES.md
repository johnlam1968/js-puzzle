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

### 1.1 The official puzzle needs **one** answer, not a proof of uniqueness

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
        # record-to-record travel: accept anything close to the best-ever
        if E2 <= best_E + THRESHOLD(it) or rng.random() < exp(-(E2 - E) / temperature(it)):
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

### 4.4 The honest limits

* **It cannot prove uniqueness.** For our *generator* it is therefore unusable as-is; for the
  *official puzzle* it is legitimate (§1.1). A separate counter-example hunt (§1.1, task B) is
  what buys confidence.
* **The landscape is rugged**: the cost field jumps (a 0 is a capitol), so a 0/1 mismatch count
  anneals badly. Use the sum of absolute deviations, with hard violations weighted heavily.
* **Every accepted state must be engine-legal**, or the annealer will wander through illegal
  configurations and the energy will be meaningless. This is the "engine is the only source of
  truth" rule, applied to a stochastic search.

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
