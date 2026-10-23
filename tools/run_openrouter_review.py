#!/usr/bin/env python3
"""OpenRouter multi-model review of the CURRENT (v2, corrected) design document.

Strategy for getting a REAL verdict instead of a truncated reasoning trace:
  attempt 1: max_tokens=60000, reasoning={effort:low, max_tokens:20000}
  attempt 2: max_tokens=60000, reasoning={effort:none}      (skip reasoning entirely)
  attempt 3: max_tokens=60000, no reasoning hint at all      (last resort)
If all attempts yield empty content, the reasoning trace is still saved (it is the payload).
"""
import os
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
URL = "https://openrouter.ai/api/v1/chat/completions"
DESIGN = open(os.path.join(ROOT, "docs", "DESIGN.md"), encoding="utf-8").read()

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

(row, col, value) triples, 1-based:
(1,2,8) (1,3,4) (1,6,11) (1,10,5)
(2,8,11)
(3,3,7) (3,6,1) (3,11,14)
(4,1,28) (4,4,51) (4,7,1) (4,9,6)
(5,2,22) (5,9,4) (5,11,1)
(6,4,15) (6,6,10) (6,8,0)
(7,1,11) (7,3,11) (7,10,9)
(8,3,17) (8,5,14) (8,9,10) (8,11,13)
(9,1,30) (9,6,6) (9,10,45)
(10,4,10)
(11,2,26) (11,6,0) (11,10,77) (11,11,61)

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

ASK = """# YOUR JOB: give a REAL, FINAL, COMPLETE verdict

You are an independent, adversarial reviewer. The design document below is another engineer's
route through this problem. Earlier review rounds already found and fixed 51 defects in it
(including one wrong lemma of their own, a self-contradictory growth rule, a completeness gap in
the hitting-set pipeline, and a backwards Bell-number bound). Your job is to find what is STILL
wrong, and to bring approaches they have NOT considered.

**You have NO tools.** You cannot read files, run code, or call anything. Everything is inlined
below. Never emit tool calls. Answer directly with text.

**Answer the following, in this order, and keep it under ~1200 words. Do not stop early.**

## 1. SANITY CHECK (do this first, in your head)
Verify the 5x5 example from the data given above: recompute the cost field yourself (Dijkstra
over the 4 states, same-state step = state size, cross-state step = min of the two sizes), check
the 10 printed numbers, check the answer 8045, and check which states have capitols and why.
Print your 5x5 d-field. Say PASS or FAIL.

## 2. VERDICT on the design document
APPROVE / APPROVE_WITH_CHANGES / REJECT, then 2-3 sentences of justification, then a numbered
list of the things that are STILL wrong, each with: section -> what is wrong -> a concrete
correction. Be specific (cell coordinates, numbers, counterexamples). If a claim is right, do not
pad the list with it.

## 3. NEW APPROACHES (the main point)
Propose math branches / algorithms the document does NOT contain that could crack the 11x11.
For each: the concrete quantity it computes, why it beats brute force, and how it plugs into
an AODFS-style solver. Consider (and accept or reject with reasons): the hitting-set view of
capitol positions, a different use of the 33 hints, spectral/algebraic/topological invariants of
symmetric polyomino tilings, integer programming, and anything else you know that applies.
Rank them.

## 4. HAND DEDUCTIONS on THIS 11x11
What can be deduced about the 11x11 from the 33 numbers alone, with NO search? Be concrete:
which cells, which state sizes, which symmetries. Use: d=0 => capitol; d=1 => adjacent 1x1
state; |d(x)-d(y)| <= step cost <= min(state sizes); only ODD-sized states can have a capitol;
the step-count bound (a hint of value v has a capitol within Manhattan distance floor((v+1)/2));
and the dead-state budget.

## 5. ONE NEXT EXPERIMENT
The single most promising next experiment on the 11x11, with expected cost and what counts as
success or failure.

Mark anything you could not verify as UNVERIFIED. Be concrete, terse, honest.
"""

SYSTEM = ("You are a rigorous mathematician and algorithm designer acting as an independent "
          "adversarial reviewer. You verify by computing, not by assuming. You state concrete, "
          "falsifiable claims and mark what you verified versus what you infer. "
          "You have no tools: you never emit tool calls and never claim to have run code. "
          "IMPORTANT: budget your reasoning and ALWAYS emit a final answer - a final answer of "
          "at most 1200 words is required.")


def ask(model, max_tokens, reasoning, tag):
    body = {"model": model,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": PROBLEM + "\n" + ASK + "\n\n"
                          + "# DESIGN DOCUMENT UNDER REVIEW (v2, after 4 review rounds)\n\n" + DESIGN}],
            "max_tokens": max_tokens, "temperature": 0.3}
    if reasoning is not None:
        body["reasoning"] = reasoning
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                                          "Content-Type": "application/json",
                                          "HTTP-Referer": "https://openrouter.ai",
                                          "X-Title": "jspuzzle-review"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=2400) as r:
        raw = r.read().decode()
    d = json.loads(raw)
    ch = d["choices"][0]
    msg = ch["message"]
    content = msg.get("content") or ""
    reasoning_txt = msg.get("reasoning_content") or msg.get("reasoning") or ""
    u = d.get("usage", {})
    print(f"[{tag}] model={model} finish={ch.get('finish_reason')} content={len(content)} "
          f"reasoning={len(reasoning_txt)} usage={json.dumps(u)} t={time.time()-t0:.0f}s", flush=True)
    return ch.get("finish_reason"), content, reasoning_txt, u, raw


def run(model, tag, budget=60000):
    cap = max(4000, int(budget * 0.5))
    attempts = [
        ("cap-reasoning", {"effort": "low", "max_tokens": cap}),
        ("no-reasoning", {"effort": "none"}),
        ("default", None),
    ]
    best = None
    for name, rs in attempts:
        try:
            finish, content, reasoning, u, raw = ask(model, budget, rs, f"{tag}:{name}")
        except Exception as e:
            print(f"[{tag}:{name}] FAILED {type(e).__name__}: {e}", flush=True)
            continue
        if content.strip() and (best is None or len(content) > len(best[1])):
            best = (name, content, reasoning, u, raw, finish)
        if content.strip():
            break
    if best is None:
        print(f"[{tag}] no attempt produced content", flush=True)
        return
    name, content, reasoning, u, raw, finish = best
    open(f"{HERE}/{tag}-raw.json", "w").write(raw)
    md = (f"# {tag} — 独立评审（v2 设计文档）\n\n- model: `{model}`\n- 命中尝试: {name}\n"
          f"- finish_reason: {finish}\n- usage: {json.dumps(u)}\n"
          f"- content_chars: {len(content)}  reasoning_chars: {len(reasoning)}\n\n---\n\n"
          f"## FINAL ANSWER\n\n{content}")
    if reasoning.strip():
        md += ("\n\n---\n\n## REASONING TRACE (raw)\n\n<details><summary>show</summary>\n\n"
               + reasoning + "\n\n</details>\n")
    open(f"{HERE}/{tag}.md", "w").write(md)
    print(f"[{tag}] SAVED {tag}.md  content={len(content)}", flush=True)


if __name__ == "__main__":
    model, tag = sys.argv[1], sys.argv[2]
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
    run(model, tag, budget)
