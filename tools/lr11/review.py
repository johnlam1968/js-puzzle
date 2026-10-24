"""Adversarial code review of `lr11/` by external models.

    python3 lr11/review.py <model-id> <output-tag>

Uses OpenRouter with "reasoning": {"effort": "none"} so the model returns a
FINAL VERDICT instead of a reasoning trace that runs out of budget (this is
the trick the js-puzzle repository's own harnesses use).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

URL = "https://openrouter.ai/api/v1/chat/completions"
KEY = os.environ.get("OPENROUTER_API_KEY", "")

HERE = os.path.dirname(os.path.abspath(__file__))

RULES = """
OFFICIAL RULES (Jane Street, "It's a Metric, Too", October 2026), verbatim:

  The 11-by-11 region above can be subdivided into various states. A "state" is a
  connected group of 1 or more squares that is symmetric in some way, be it via
  rotation or reflection. If every nontrivial rotation or reflection of the plane
  that takes a state to itself leaves exactly 1 of its squares fixed, then that
  square is its capitol. (So, for example, a 1-by-3 region has no capitol, nor
  does the "X" pentomino.)

  The cost of traveling from one square to an orthogonally adjacent square in
  this nation is equal to the size (i.e. number of squares) of the state you are
  travelling in, or, if travelling between two states, the lesser of the two
  states' sizes. A number in a cell (below) denotes the lowest cost of travelling
  from the numbered square to any state capitol.

  After determining the shapes of the states, label each cell with the size of
  the state it is in. Compute the sum of these values in each row, and submit as
  your answer the sum of the squares of these row sums (as in the example).

Facts used as given (all proven in docs/03-hard-deductions.md):
  - (5,10) is a forced 1x1 state (a capitol).  Its neighbours (5,9) and (6,10)
    therefore have d <= 1, and (4,10)=1.
  - cost(x,y) = min(size(state(x)), size(state(y))) for adjacent cells.
  - d(x) = least cost from x to ANY capitol.
  - a state with a capitol has ODD area; an even-area state has no capitol.
  - L1: d(x)>0 implies some neighbour y has d(y) = d(x) - min(size_x, size_y).
  - L2/L3: for adjacent x,y, |d(x)-d(y)| <= min(size_x, size_y).

The 11x11 published numbers (0-based (row,col)):
  (0,1)=8 (0,2)=4 (0,5)=11 (0,9)=5 (1,7)=11 (2,2)=7 (2,5)=1 (2,10)=14
  (3,0)=28 (3,3)=51 (3,6)=1 (3,8)=6 (4,1)=22 (4,8)=4 (4,10)=1 (5,3)=15
  (5,5)=10 (5,7)=0 (6,0)=11 (6,2)=11 (6,9)=9 (7,2)=17 (7,4)=14 (7,7)=10
  (7,10)=13 (8,0)=30 (8,5)=6 (8,8)=45 (9,3)=10 (10,1)=26 (10,5)=0
  (10,8)=77 (10,9)=61
"""

PROMPT = """You are an adversarial code reviewer.  Review the two Python files below.

They implement, from scratch, the rule kernel and two search tools for the
Jane Street "It's a Metric, Too" puzzle.

{file_a}

{file_b}

THE OFFICIAL RULES ARE:

{rules}

WHAT THE CODE IS SUPPOSED TO DO

kernel.py
  * symmetry_group(cells): the full lattice symmetry group of a set of squares
    (seven non-identity candidates), mapped to the cells each element fixes.
  * is_legal_state: 4-connected AND has at least one non-trivial self-symmetry
    (per the official text, a shape with NO symmetry is not a state at all).
  * capitol_of: the official capitol rule -- quantify over the FULL group; if
    any non-trivial symmetry fixes a number of cells other than exactly one,
    there is no capitol; if all fix exactly one cell they must fix the SAME cell.
  * cost_field: Dijkstra with edge weight min(size_x, size_y).
  * row_sums / answer.

tools.py
  * grow_states: enumerate every legal state of a given size containing a given
    anchor set, by growing whole ORBITS of one symmetry at a time.
  * internal_consistency: necessary conditions on published numbers inside a
    candidate state.
  * tight_neighbour_ok: the L1 lemma applied inside a candidate state.
  * check_partial: given a PARTIAL partition, rigorous lower/upper bounds on
    d(x) and a list of contradicted published numbers.

WHAT I WANT FROM YOU

Review for CORRECTNESS, in this order of importance.

1. SOUNDNESS OF THE ELIMINATIONS.  The filters are used to throw candidate
   states away.  A filter that can eliminate a state which is part of a genuine
   solution is a FATAL bug.  Check every filter:
     - internal_consistency: is |d(x)-d(y)| <= k*dist_S(x,y) really necessary?
       Is the "even state cannot contain a published 0" rule right?
     - tight_neighbour_ok: is the range [v-k, v-1] right for a neighbour
       outside the state?  Is the "exactly v-k" right for a neighbour inside?
     - the disjointness filter.
2. COMPLETENESS OF grow_states.  Can it MISS a legal state?  Consider:
     - the seven symmetry instances: are they complete for the 11x11 board?
       (reflections about half-integer axes, rotations about half-integer
       centres, the two diagonal mirrors)  Is the "square bounding box"
       requirement for the diagonal mirrors and the 90-degree rotations right?
     - the orbit-growth DFS: can it miss a state because of the connectivity
       pruning, the size pruning, or the "increasing index" ordering?
     - can a state be symmetric under a symmetry that does NOT preserve the
       board, and would the orbit code then drop it wrongly?
3. THE SYMMETRY GEOMETRY.  Check the integer arithmetic of refD1 / refD2 /
   rot90 / rot270 and the conditions under which each candidate is offered.
   Check the claim "only the eight lattice symmetries can preserve a union of
   axis-aligned unit squares".
4. check_partial: are the LOWER bound (free cells given size 1) and the UPPER
   bound (paths restricted to known cells) really valid bounds on d(x)?  Is the
   treatment of a state with no capitol correct (it contributes no capitol to
   the Dijkstra sources)?
5. Anything that is silently wrong: off-by-one, a wrong sign, an
   off-by-one in an index, a silent exception, a filter that is never applied,
   a variable that is computed but not used.

Answer with a numbered list of findings.  For each finding give
  SEVERITY: FATAL / MAJOR / MINOR / NIT
  LOCATION: file and line or function
  WHAT IS WRONG: one or two sentences
  FIX: the concrete change
Be concrete and cite code.  If a piece of reasoning is correct, say so in one
line and move on -- do not pad.  If you believe a filter is unsound, prove it
with a concrete example (a set of cells, or a published number) rather than
asserting it.  A "FATAL" verdict must come with a concrete counterexample.

Finish with a final verdict line:  VERDICT: SOUND  or  VERDICT: UNSOUND
and a one-sentence justification.
"""


def collect() -> str:
    out = []
    for name in ("kernel.py", "tools.py"):
        with open(os.path.join(HERE, name)) as fh:
            src = fh.read()
        out.append(f"########## FILE: lr11/{name} ##########\n{src}")
    return "\n\n".join(out)


def call(model: str, tag: str, budget: int = 14000) -> None:
    # GLM's endpoint makes reasoning MANDATORY and refuses effort:none
    # ("Reasoning is mandatory for this endpoint and cannot be disabled."),
    # so for GLM we omit the parameter and give it a bigger token budget; the
    # reasoning trace then IS the payload (same convention as the repository's
    # own harnesses).
    glmmode = ("glm" in model or "z-ai" in model)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT.replace("{file_a}", "%FILE_A%")
                      .replace("{file_b}", "%FILE_B%").replace("{rules}", RULES)}],
        "max_tokens": 32000 if glmmode else budget,
        "temperature": 0.1,
    }
    if not glmmode:
        body["reasoning"] = {"effort": "none"}
    files = collect()
    body["messages"][0]["content"] = body["messages"][0]["content"].replace(
        "%FILE_A%", files.split("########## FILE: lr11/kernel.py ##########")[1]
        .split("########## FILE: lr11/tools.py")[0])
    body["messages"][0]["content"] = body["messages"][0]["content"].replace(
        "%FILE_B%", "########## FILE: lr11/tools.py ##########" + files.split(
            "########## FILE: lr11/tools.py ##########")[1])
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://openrouter.ai",
                 "X-Title": "js-puzzle lr11 code review"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=2400) as r:
        raw = r.read()
    # the OpenRouter gateway can prepend whitespace/newlines before the JSON
    payload = json.loads(raw.decode("utf-8", "replace").strip())
    ch = payload["choices"][0]
    msg = ch["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    print(f"[{tag}] finish={ch.get('finish_reason')} content={len(content)} "
          f"reasoning={len(reasoning)} {time.time()-t0:.0f}s", flush=True)
    md = (f"# {tag} — CODE REVIEW of lr11/\n\n- model: `{model}`\n"
          f"- finish_reason: {ch.get('finish_reason')}\n"
          f"- usage: {json.dumps(payload.get('usage', {}))}\n"
          f"- content_chars: {len(content)} reasoning_chars: {len(reasoning)}\n\n---\n\n")
    md += content.strip() if content.strip() else (
        "## (no final content — reasoning trace below is the payload)\n\n" + reasoning)
    if content.strip() and reasoning.strip():
        md += "\n\n---\n\n## REASONING TRACE (raw)\n\n<details><summary>show</summary>\n\n" \
              + reasoning + "\n\n</details>\n"
    path = os.path.join(HERE, f"review-{tag}.md")
    with open(path, "w") as fh:
        fh.write(md)
    print(f"[{tag}] wrote {path}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    call(sys.argv[1], sys.argv[2])
