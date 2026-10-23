#!/usr/bin/env python3
"""Send the original problem + the design document to GLM-flash-latest on OpenRouter
for a second opinion and fresh approaches."""
import os
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
MODEL = "~z-ai/glm-flash-latest"
URL = "https://openrouter.ai/api/v1/chat/completions"
DESIGN = open(f"{HERE}/DESIGN-approaches-and-trace-transfer.md", encoding="utf-8").read()

PROBLEM = """# THE ORIGINAL PROBLEM (Jane Street, October 2026, "It's a Metric, Too")

Official statement (verbatim):

  The 11-by-11 region above can be subdivided into various states. A "state" is a connected
  group of 1 or more squares that is symmetric in some way, be it via rotation or reflection.
  If every nontrivial rotation or reflection of the plane that takes a state to itself leaves
  exactly 1 of its squares fixed, then that square is its capitol. (So, for example, a 1-by-3
  region has no capitol, nor does the "X" pentomino.)

  The cost of traveling from one square to an orthogonally adjacent square in this nation is
  equal to the size (i.e. number of squares) of the state you are travelling in, or, if
  travelling between two states, the lesser of the two states' sizes. A number in a cell
  denotes the lowest cost of travelling from the numbered square to any state capitol.

  After determining the shapes of the states, label each cell with the size of the state it is
  in. Compute the sum of these values in each row, and submit as your answer the sum of the
  squares of these row sums.

## The 11x11 grid to solve (rows top->bottom, '.' = no number)

   .  8  4  .  . 11  .  .  .  5  .
   .  .  .  .  .  .  . 11  .  .  .
   .  .  7  .  .  1  .  .  .  . 14
  28  .  . 51  .  .  1  .  6  .  .
   . 22  .  .  .  .  .  .  4  .  1
   .  .  . 15  . 10  .  0  .  .  .
  11  . 11  .  .  .  .  .  .  9  .
   .  . 17  . 14  .  .  . 10  . 13
  30  .  .  .  .  6  .  .  . 45  .
   .  .  . 10  .  .  .  .  .  .  .
   . 26  .  .  .  0  .  .  . 77 61

(33 numbers; 0-valued cells are capitols; the grid does NOT draw the state boundaries.)

## The official 5x5 WORKED EXAMPLE (given with its solution) - use it to check your reading

Input grid (numbers only)        True solution: states, capitols, cost field, answer
 12  .  .  . 17                    states (0-based labels):
  8  .  6  3  .                      0 1 1 3 3
  .  .  .  .  .                      0 1 1 2 3
  .  7  6  . 10                      0 0 2 2 3
 25  .  .  .  0                      3 0 0 0 3
                                   3 3 3 3 3
                                  state sizes: 0->7, 1->4, 2->3, 3->11
                                  capitols (0-based): state0 (2,1), state2 (2,3), state3 (4,4);
                                                  state1 (the 2x2) has NO capitol
                                  cost field d (0-based):
                                     12  8 10  6 17
                                      8  4  6  3  6
                                      7  0  3  0  3
                                     14  7  6  3 10
                                     25 14 13 10  0
                                  row sums of state sizes: [37,29,31,43,55]
                                  answer = 37^2+29^2+31^2+43^2+55^2 = 8045
"""

ASK = """# YOUR JOB: second opinion + NEW approaches

You are an independent, adversarial reviewer. The design document below is another engineer's
route through this problem: which parts are wrong, shaky, or missing - and are there math branches
they never considered that could crack the 11x11?

**You have NO tools.** You cannot read files, run code, or call anything. Everything you need is
inlined below. Do not emit tool calls. Do not try to read files. Answer directly with text.

## Task A - independent sanity check of the setup (do this FIRST, in your head)
Before reviewing anything, verify the 5x5 example from the data given above:
- recompute the cost field with your own Dijkstra over the 4 states, confirm the 10 printed numbers;
- confirm the answer 8045;
- confirm which states have capitols and why.
If any of that fails, say so loudly and show your arithmetic. If it passes, say PASS in one line.

## Task B - critique the design document
Go through it section by section. For each claim that is **wrong, unproven, overstated, or
missing**, write a numbered finding: section -> what is wrong -> a concrete correction.
Be specific: cell coordinates, numbers, or a counterexample. Do not write "add more tests".
Pay special attention to:
- the rule kernel (integer arithmetic, the 8 candidate symmetries, the capitol rule);
- the five lemmas and the two parity theorems;
- the "d-field does not determine the answer" counterexample and the answer-level uniqueness rule;
- the AODFS algorithm and its completeness argument;
- the hitting-set reformulation of capitol positions;
- the claim that a 4x4 "worked trace" can transfer to the 11x11.

## Task C - NEW approaches (the main point)
Propose math branches / algorithms **not present in the document** that could help, especially for
the 11x11. Ideas to consider (you are free to reject them and bring better ones):
- a different way to pin down the capitol positions (the doc uses a hitting-set / set-cover bound);
- a way to exploit that the 11x11 has only 33 hints over 121 cells;
- spectral / algebraic / topological invariants of a symmetric polyomino tiling;
- the role of the 2 known capitols and the 3 cells with value 1 (which force 1x1 states);
- a human-solvable deduction chain for THIS specific 11x11 - what can be deduced by hand today,
  from the numbers alone, without any search?
- anything in combinatorics, graph theory, or integer programming that the doc missed.

## Task D - a concrete next step
Give the single most promising next experiment on the 11x11, with its expected cost and what
result would count as success or failure.

## Output format
1. SANITY CHECK: PASS/FAIL on the 5x5 example (with the d-field you computed).
2. CRITIQUE: numbered findings (severity + section + what's wrong + concrete fix).
3. NEW APPROACHES: ranked, each with the concrete quantity it computes and why it helps.
4. HAND DEDUCTIONS: what you can deduce about the 11x11 from the 33 numbers alone, right now.
5. ONE NEXT EXPERIMENT: as above.
Be concrete, terse, and honest. Mark anything you could not verify as UNVERIFIED.
"""

SYSTEM = ("You are a rigorous mathematician and algorithm designer acting as an independent "
          "adversarial reviewer. You verify by computing, not by assuming. You state concrete, "
          "falsifiable claims, and you mark what you verified versus what you infer. "
          "You have no tools: you never emit tool calls, you never claim to have run code.")

body = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROBLEM + "\n" + ASK + "\n\n" +
         "# DESIGN DOCUMENT UNDER REVIEW (by another engineer)\n\n" + DESIGN},
    ],
    "max_tokens": 20000,
    "temperature": 0.3,
}

req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                             headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                                      "Content-Type": "application/json",
                                      "HTTP-Referer": "https://openrouter.ai",
                                      "X-Title": "jspuzzle-review"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=1800) as r:
        raw = r.read().decode()
except Exception as e:
    print("REQUEST FAILED:", type(e).__name__, e, file=sys.stderr)
    if hasattr(e, "read"):
        print(e.read().decode()[:2000], file=sys.stderr)
    sys.exit(1)

d = json.loads(raw)
open(f"{HERE}/glm-review-raw.json", "w").write(raw)
ch = d["choices"][0]
msg = ch["message"]
content = msg.get("content") or ""
reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
u = d.get("usage", {})
print(f"model={MODEL} finish={ch.get('finish_reason')} content={len(content)} "
      f"reasoning={len(reasoning)} usage={json.dumps(u)} t={time.time()-t0:.0f}s")
md = (f"# GLM-flash-latest — 独立评审（原题 + 设计文档）\n\n"
      f"- model: `{MODEL}` (OpenRouter)\n- finish_reason: {ch.get('finish_reason')}\n"
      f"- usage: {json.dumps(u)}\n- content_chars: {len(content)}  reasoning_chars: {len(reasoning)}\n\n---\n\n")
md += ("## FINAL ANSWER\n\n" + content) if content.strip() else \
      ("## (no final content - reasoning trace below is the payload)\n\n" + reasoning)
if content.strip() and reasoning.strip():
    md += "\n\n---\n\n## REASONING TRACE (raw)\n\n<details><summary>show</summary>\n\n" + reasoning + "\n\n</details>\n"
open(f"{HERE}/REVIEW-glm-flash-latest.md", "w").write(md)
print(md[:6000])
