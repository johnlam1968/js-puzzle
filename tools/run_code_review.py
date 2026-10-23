#!/usr/bin/env python3
"""Ask an external model to REVIEW THE CODE (not the design).

Sends src/*.py and tests/*.py plus the specification they must satisfy, and asks for a
bug list with file/line/proof/fix.  The reviewer is told it has no tools, so every claim
must be justified by reasoning or by a snippet it writes in its answer.
"""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
URL = "https://openrouter.ai/api/v1/chat/completions"

SPEC = """## THE SPECIFICATION THE CODE MUST SATISFY

Puzzle: an N x N grid is partitioned into "states". A state is a 4-connected set of squares
with at least one non-trivial lattice self-symmetry (rotation 90/180/270 about its centroid,
or reflection through a horizontal / vertical / 45-degree line through its centroid).
A state's CAPITOL is the square fixed by every non-trivial self-symmetry -- but only if each
such symmetry fixes EXACTLY ONE square; otherwise the state has NO capitol.
Travel: one orthogonal step inside a state costs the state size; a step between two states
costs min(sizeA, sizeB). A cell's value d(x) = the least total cost from x to ANY capitol.
ANSWER = label every cell with its state size, sum per row, then sum the squares of the row sums.

Hard-won rules the code MUST respect (each was a real bug found in review):
 1. NO FLOATING POINT anywhere in the symmetry test. The official example's 3-cell state has
    centroid (5/3, 8/3); in IEEE754 doubles rbar-cbar = -0.9999999999999998, the reflection
    test fails, the capitol silently disappears and every published number changes.
    All divisibility conditions must be integer congruences on (sum_r, sum_c, n).
 2. The capitol rule quantifies over the FULL point group, not one symmetry. A 1x3 bar has a
    vertical reflection fixing exactly one cell, but its horizontal reflection fixes all
    three, so it has NO capitol.
 3. A shape with no non-trivial symmetry is NOT a state at all (the L-tetromino).
 4. The modular divisibility conditions are NECESSARY BUT NOT SUFFICIENT: every candidate map
    must still be verified to send the state onto itself.
 5. A state with no capitol is still a legal state, but a partition with NO capitol anywhere
    has an undefined cost field and is not a solution.
 6. Only odd-sized states can carry a capitol (a symmetry fixing one square pairs up the rest).
 7. The cost of a step between two DIFFERENT states is min(sA,sB); a step inside a state is s.
    For a capitol c adjacent to x: min(s_x, s_c) >= d(x) -- a LOWER BOUND, not an equality
    (the nearest capitol of x may be an unknown one, so w(x,c) can exceed d(x)).
 8. The step-count bound: if d(x)=v, the nearest capitol is within Manhattan distance
    floor((v+1)/2), because every step except the last costs at least 2.
 9. The d-field does NOT determine the answer: two different 4x4 partitions can share the same
    16-value cost field and give answers 304 and 112. Uniqueness must be judged at the ANSWER level.
10. A capitol-adjacent bound of the form "2*d(x) > N^2 forbids an adjacent capitol" is only
    valid for a capitol in ANOTHER state; a same-state capitol is possible.
11. Connected-subset enumeration must be canonical (each subset exactly once): a set is
    built from its smallest cell, cells are added in increasing order, and an already
    processed cell must be excluded for all later siblings.

Rules added by the later rounds (the generator/judge/grow code must respect them too):
 12. A d = 1 hint must be served by a capitol that sits in a 1x1 state (the capitol of a
     1x1 state is that cell), and that requirement has to travel with the demand.
 13. Connectivity is checked when a state is CLOSED, not at every intermediate growth
     step: the first orbit of a state can be disconnected (the anti-diagonal L-tromino
     starts from {(0,0),(1,1)}), so requiring it mid-growth makes legal states unreachable.
 14. The uniqueness judge is THREE-valued. "I did not find a second answer" is NOT
     uniqueness: unique == (search exhausted) AND (answer set has exactly one element).
 15. The judge may only prune with SOUND bounds: an upper bound (a hinted cell whose own
     state already reaches a capitol for less than its published value) and a lower bound
     over the cells that are still POSSIBLE capitols. A bound computed over the REVEALLED
     capitols alone is invalid.
 16. The generator may only ship a puzzle whose answer-uniqueness was PROVED (exhaustive);
     if the full hint set is not answer-unique then NO hint subset can repair it (deleting
     hints only relaxes), so the partition must be rejected outright.
 17. Hint minimisation may use one pass: deleting hints only relaxes the constraint set, so
     a hint that is required now stays required forever.
 18. The tiling table is a CACHE, not a deliverable: it must be rebuildable from scratch
     and must never be the only source of truth.

Rules added by the scale-out round (the code must respect them too):
 19. NOTHING may be enumerated globally for a big frame: the catalogue of all connected
     subsets is hopeless from 6x6 up, so the legal states of a cell must be generated ON
     DEMAND from that cell (orbit growth), and nothing may depend on a global catalogue.
 20. The offline tiling table is a CACHE: it must carry a stamp of the rule engine it was
     built from and must be IGNORED when that stamp does not match the current sources, and
     its row count must be cross-checked. A stale table must never be able to report
     "exhaustive: True".
 21. The uniqueness judge must be able to run WITHOUT the table (search path) and must
     report honestly when its budget was exhausted (unique = unknown, never silently true).

Rules added by the M4 solver round:
 22. The solver GROWS the tiling; it must not enumerate candidate states separately and
     then place them (that re-generates the same states and does not scale).
 23. A d = 0 anchor is a capitol, so the symmetry used to grow its state MUST fix it;
     most candidate symmetries are therefore impossible from the start.
 24. A partial state may only abandon growth when the published numbers already rule it
     out; the solver's vocabulary must not be shrunk by a size cap.
 25. The solver's verdict stays three-valued: exhaustive + one answer = unique; a budget
     that runs out = unknown, never silently unique.

Known reference numbers the code must reproduce (4x4):
  connected subsets 11,506 | legal states 1,130 | shape types (up to translation) 640
  legal tilings 562,308 | by number of blocks: 1,79,674,4203,18653,55516,108356,139234,
    120713,72574,30794,9261,1949,276,24,1
  by number of capitol-bearing states: 0,2723 1,11744 2,45166 3,59320 4,126954 5,75672
    6,126390 7,36268 8,56637 9,7264 10,12224 11,596 12,1273 13,16 14,60 (15 IMPOSSIBLE) 16,1
  official 5x5 example: states of size 7/4/3/11, capitols at 1-based (3,2),(3,4),(5,5),
    the 2x2 state has no capitol, row sums [37,29,31,43,55], answer 8045.
"""

ASK = """# YOUR JOB: review this CODE, adversarially

You are a senior reviewer for a research codebase. You will be given the full source of the
implementation and its test suite. Find BUGS.

⛔ You have NO tools: you cannot read files, run code, or call anything. Everything is inlined
below. **Never emit tool calls.** If you want to demonstrate a bug, write the tiny snippet
that would exhibit it INSIDE YOUR ANSWER.

Focus on:
 1. **Logic bugs** in the symmetry test, the capitol rule, the cost field, the enumeration,
    the DP counters, and the hitting-set code. Off-by-one, wrong base case, wrong sign, a
    filter that never fires, a memo key that collides.
 2. **Places where the code contradicts the SPECIFICATION above** (numbered rules 1-11).
 3. **Edge cases the tests do not cover** (empty grid, single cell, 1x2, 1x3, states with no
    symmetry, partitions with no capitol, rectangular grids, N=2).
 4. **Performance traps** that would blow up on the 11x11 instance (the real target).
 5. **Dead code, misleading names, or comments that contradict the code.**

For each finding give: severity (BLOCKER/MAJOR/MINOR) | file and line | what is wrong | a
concrete demonstration or proof | the fix.
Do NOT restate what the code does correctly. Do not pad the list. If you find nothing in a
category, say so in one line.

Finish with:
 6. **VERDICT**: SHIP / SHIP AFTER FIXES / DO NOT SHIP, in one line, plus the count of
    BLOCKER and MAJOR findings.
 7. **THE THREE HIGHEST-VALUE TESTS** that are still missing, each as a concrete assertion.

"""

NO_TOOLS = ("⛔ You have NO tools: no file reading, no code execution, no tool calls of any kind. "
            "Never emit a tool call. Write any demonstration snippet inside your answer.\n\n")


def collect():
    out = []
    for d in ("src", "tests"):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if f.endswith(".py"):
                p = os.path.join(ROOT, d, f)
                out.append(f"### FILE: {d}/{f}\n```python\n{open(p, encoding='utf-8').read()}\n```\n")
    return "\n".join(out)


def call(model, tag, budget=60000):
    body = {"model": model,
            "messages": [{"role": "system", "content":
                          "You are a meticulous senior code reviewer. You find real bugs and prove "
                          "them. You never speculate about code you have not read. You are terse and "
                          "concrete."},
                         {"role": "user", "content": NO_TOOLS + SPEC + ASK + collect()}],
            "max_tokens": budget, "temperature": 0.1, "reasoning": {"effort": "none"}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                                          "Content-Type": "application/json",
                                          "HTTP-Referer": "https://openrouter.ai",
                                          "X-Title": "jspuzzle-code-review"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=2400) as r:
        raw = r.read().decode()
    d = json.loads(raw)
    ch = d["choices"][0]
    msg = ch["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    u = d.get("usage", {})
    print(f"[{tag}] finish={ch.get('finish_reason')} content={len(content)} reasoning={len(reasoning)} "
          f"usage={json.dumps(u)} t={time.time()-t0:.0f}s", flush=True)
    md = (f"# {tag} — CODE REVIEW\n\n- model: `{model}`\n- finish_reason: {ch.get('finish_reason')}\n"
          f"- usage: {json.dumps(u)}\n- content_chars: {len(content)} reasoning_chars: {len(reasoning)}\n\n---\n\n")
    md += ("## REVIEW\n\n" + content) if content.strip() else \
          ("## (no final content — reasoning trace below is the payload)\n\n" + reasoning)
    if content.strip() and reasoning.strip():
        md += "\n\n---\n\n## REASONING TRACE (raw)\n\n<details><summary>show</summary>\n\n" + reasoning + "\n\n</details>\n"
    with open(os.path.join(ROOT, "docs", "reviews", f"{tag}.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"[{tag}] saved docs/reviews/{tag}.md", flush=True)


if __name__ == "__main__":
    call(sys.argv[1], sys.argv[2])
