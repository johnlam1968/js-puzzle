#!/usr/bin/env python3
"""Two-call DeepSeek-V4.1-Flash review:
  call A (vision): independently re-derive the 5x5 example from the PNG; check symmetry-candidate completeness
  call B (text)  : adversarial review of the plan (lemmas, uniqueness criterion, generator, spot-check fixes)
effort=high, generous max_tokens (v1 died with finish_reason=length: all budget went to reasoning).
"""
import os
import base64, json, os, sys, urllib.request, time

PLAN = os.path.join(HERE, "PLAN-puzzle-generator.md"
IMG = os.path.join(HERE, "metric-too.png"
MODEL = "deepseek-flash"
BASE = "https://api.deepseek.com/chat/completions"

plan = open(PLAN, encoding="utf-8").read()
b64 = base64.b64encode(open(IMG, "rb").read()).decode()

RULES = """
The 11-by-11 region above can be subdivided into various states. A "state" is a connected group of 1 or more squares that is symmetric in some way, be it via rotation or reflection. If every nontrivial rotation or reflection of the plane that takes a state to itself leaves exactly 1 of its squares fixed, then that square is its capitol. (So, for example, a 1-by-3 region has no capitol, nor does the "X" pentomino.)

The cost of traveling from one square to an orthogonally adjacent square in this nation is equal to the size (i.e. number of squares) of the state you are travelling in, or, if travelling between two states, the lesser of the two states' sizes. A number in a cell (below) denotes the lowest cost of travelling from the numbered square to any state capitol.

After determining the shapes of the states, label each cell with the size of the state it is in. Compute the sum of these values in each row, and submit as your answer the sum of the squares of these row sums (as in the example).
"""

SYSTEM = ("You are a rigorous adversarial engineering reviewer with strong mathematical and algorithmic "
          "analysis skills. You verify claims by computing, not by assuming. You never fill gaps with "
          "speculation: unknown means unknown. You are terse and concrete; prefer arithmetic and explicit "
          "cell coordinates over prose.")

CALL_A = f"""TASK A — independently re-derive the 5x5 worked EXAMPLE from the attached image.

The attached PNG is the official Jane Street puzzle page image. Its BOTTOM band contains a 5x5 worked
example in three side-by-side panels:
  LEFT   = the input grid: 10 cells contain numbers, the rest are blank
  MIDDLE = the same grid with each STATE filled in a different colour and a black dot on each CAPITOL
  RIGHT  = the same grid with each cell labelled by its STATE SIZE, plus the printed text "example answer = 8,045"

Official rules (verbatim):
{RULES}

Do this, from the image, WITHOUT trusting any number in this prompt:
1. Read the MIDDLE panel's fill colours to recover the state partition (a state = a maximal run of same-coloured cells).
   Output it as a 5x5 ASCII grid of state labels (A/B/C/...) plus each state's cell count.
2. Find the black dots in the MIDDLE panel -> the capitols. Output their (row, col), 1-based from top-left.
3. For each state, work out its self-symmetries (rotations about its centroid, reflections through lines
   through its centroid: horizontal, vertical, and the two 45-degree diagonals) and whether the capitol rule
   holds: "every non-identity symmetry that maps the state to itself fixes EXACTLY 1 cell" -> that cell is the
   capitol; otherwise the state has NO capitol. Show which symmetry fixes which cells.
4. Read the LEFT panel's 10 numbers (positions and values).
5. Compute from scratch the 5x5 cost field: a step between two orthogonally adjacent cells in the SAME state
   costs that state's size; a step between two DIFFERENT states costs min(sizeA, sizeB). d(cell) = minimum total
   cost from that cell to ANY state capitol (multi-source Dijkstra from the capitols). Show your 5x5 d-field.
6. Compare your d-field against the 10 given numbers. PASS/FAIL each.
7. From the RIGHT panel's sizes, compute the row sums and the final answer sum(row_sums^2).
   Check it against the printed 8,045. PASS/FAIL.

Also answer this precise question:
  Is the plan's claim in section 3.1 correct that the ONLY possible self-symmetries of a polyomino are the 8
  lattice ones (identity, 90/180/270 rotation about the centroid, 4 reflections through the centroid)?
  Give the full argument, or a counterexample shape with an extra symmetry.

Output format: numbered sections 1..7 as above, then "VERDICT: PASS/FAIL" for the 8,045 check, then the
symmetry question. Show your arithmetic. Do not skip the d-field."""

CALL_B = f"""TASK B — adversarial review of an implementation plan.

CONTEXT. The plan (below) builds a generator + solver for Jane Street's October 2026 puzzle "It's a Metric, Too".
Official rules (verbatim):
{RULES}

The plan's section 0.1 lists 19 defects that a PREVIOUS reviewer already found; the plan claims all are now fixed.
The previous reviewer's independent facts you may trust as given:
  - The official 5x5 example has states of sizes 7/4/3/11, capitols at (2,1),(2,3),(4,4), the 2x2 state has NO
    capitol, row sums [37,29,31,43,55], answer 8045, and its 10 printed numbers are all reproduced.
  - Measured: 4x4 has 11,506 connected subsets, 1,124 legal states, 561,468 legal partitions; a memoised DP counts
    them in 0.2s, while "enumerate all partitions and compute a d-field per leaf" takes 400s.
  - 5x5 has 22,041 legal states, 2,638,025,192 legal partitions; DP counting takes 239s.
  - L1/L2/L3/L5 were checked against 4,000 random partitions with 0 counterexamples; L4's converse is FALSE.

YOUR JOB — find what is STILL wrong. Specifically:
1. Section 3.5 lemmas: try to REFUTE each of L1 (tight edge), L2 (|dx-dy| <= min(sx,sy)), L3 (size lower bound),
   L4 (d=1 => adjacent to a 1-cell state), L5 (d=0 <=> capitol) with an explicit counterexample, and check whether
   the PROOFS given in the plan are correct. Is any lemma stated too strongly?
2. Section 3.3/3.4: the plan now defines uniqueness at the ANSWER level ("the set of answers produced by all
   partitions compatible with the hints has size 1") because different partitions can share a d-field and row sums.
   Is that the right criterion for a puzzle? Could two different answers be compatible with the same hints?
   Can you construct a case where the same hints admit two different ANSWERS (not just two partitions)?
3. Section 3.1.2: the plan forbids floating point in the rule kernel and uses integer divisibility conditions.
   Verify the six conditions are the correct exact equivalents of "the transformation maps the unit-square
   lattice to itself". Any off-by-one or missing condition?
4. Section 3.1.1's completeness argument for the 8 candidate symmetries: is it sound? Any gap?
5. Sections 3.4/3.7: the generator uses randomised exact-cover backtracking; hints use greedy deletion to an
   "irreducible" set. Any infinite loop, non-termination, or subtle flaw? Does greedy deletion actually guarantee
   the answer-level uniqueness it claims?
6. Section 6 milestones M1-M6: are any completion criteria unreachable, self-contradictory, or unfalsifiable?
   M6 claims to report all candidate answers for the 11x11 — is that operationally achievable?
7. Spot-check the section 0.1 fixes against the plan body: is any fix applied WRONG or only half-applied?
   (Pay attention to D2's L4 rewrite, D6's answer-level uniqueness, D7's budgeted 5x5 search, D10's "33 numbers".)
8. What did the previous review MISS? Wrong algorithmic claims, missing test coverage, invalid scale assumptions,
   requirements that are mathematically impossible, or silent-failure modes.

Output:
1. VERDICT: APPROVE / APPROVE_WITH_CHANGES / REJECT + 2-3 sentences.
2. REFUTED LEMMAS: for each of L1..L5 give verdict + counterexample if any.
3. FINDINGS: numbered; each = severity (BLOCKER/MAJOR/MINOR) + plan section + what is wrong + a CONCRETE fix.
   Do not merely repeat the 19 items in section 0.1.
4. UNVERIFIED: what you could not check, stated plainly.
5. NOTHING-WRONG-CHECK: what you verified as correct, so it is not re-litigated.

=== PLAN DOCUMENT (v2) ===
{plan}"""


def call(tag, content_parts, max_tokens=30000):
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": content_parts}],
            "max_tokens": max_tokens, "temperature": 0.2, "effort": "high"}
    req = urllib.request.Request(BASE, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                                          "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1200) as r:
        raw = r.read().decode()
    d = json.loads(raw)
    open(fos.path.join(HERE, "ds-{tag}-raw.json", "w").write(raw)
    msg = d["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    u = d.get("usage", {})
    print(f"[{tag}] finish={d['choices'][0].get('finish_reason')} content_chars={len(content)} "
          f"reasoning_chars={len(reasoning)} usage={json.dumps(u)} t={time.time()-t0:.0f}s")
    open(fos.path.join(HERE, "ds-{tag}.md", "w").write(content if content.strip() else
                                                        "### (empty content — reasoning only)\n\n" + reasoning)
    return content


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("a", "both"):
        call("a", [{"type": "text", "text": CALL_A},
                   {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}],
             max_tokens=30000)
    if which in ("b", "both"):
        call("b", CALL_B, max_tokens=40000)
