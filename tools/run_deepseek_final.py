#!/usr/bin/env python3
"""Compact final-answer call: effort=low so the model answers instead of reasoning forever."""
import os
import base64, json, os, urllib.request, time

PLAN = os.path.join(HERE, "PLAN-puzzle-generator.md"
plan = open(PLAN, encoding="utf-8").read()

PROMPT = f"""Adversarial review of an implementation plan. ANSWER DIRECTLY AND CONCISELY.

Budget: at most 1200 words of final answer. Do NOT write a long reasoning process; state findings as
bullet points with concrete fixes.

The plan (below) builds a generator + solver for Jane Street's "It's a Metric, Too" puzzle.
Official rules (verbatim):
  The 11-by-11 region above can be subdivided into various states. A "state" is a connected group of 1 or
  more squares that is symmetric in some way, be it via rotation or reflection. If every nontrivial
  rotation or reflection of the plane that takes a state to itself leaves exactly 1 of its squares fixed,
  then that square is its capitol. (So, for example, a 1-by-3 region has no capitol, nor does the "X" pentomino.)
  The cost of traveling from one square to an orthogonally adjacent square in this nation is equal to the
  size of the state you are travelling in, or, if travelling between two states, the lesser of the two
  states' sizes. A number in a cell denotes the lowest cost of travelling from the numbered square to any
  state capitol.
  After determining the shapes of the states, label each cell with the size of the state it is in. Compute
  the sum of these values in each row, and submit as your answer the sum of the squares of these row sums.

Already-verified facts (do not re-derive): official 5x5 example has states of sizes 7/4/3/11, capitols at
(3,2),(3,4),(5,5) 1-based, the 2x2 state has NO capitol, row sums [37,29,31,43,55], answer 8045, all 10
printed numbers reproduced. 4x4: 11,506 connected subsets, 1,124 legal states, 561,468 legal partitions,
DP counting 0.2s vs 400s for leaf-by-leaf. 5x5: 22,041 legal states, 2,638,025,192 legal partitions, DP 239s.
A prior review already found and the plan already fixed 19 defects (listed in the plan's section 0.1).

REPORT, in this exact structure:
1. VERDICT: APPROVE / APPROVE_WITH_CHANGES / REJECT (one line + 2 sentences).
2. NEW FINDINGS (things the prior review did NOT find): numbered, each = severity (BLOCKER/MAJOR/MINOR) +
   plan section + what is wrong + concrete fix. Maximum 10. If you genuinely find nothing new, say so.
3. LEMMAS L1..L5: for each, VERDICT (holds / false) + a concrete counterexample if false. Note in particular
   whether L3 as literally written in the plan's table (without any "neighbour" qualifier) is true.
4. ANSWER-UNIQUENESS: can the SAME set of hint numbers be compatible with two DIFFERENT answers?
   If yes, give a small explicit grid + the two partitions + the two answers. If no, prove it.
5. UNVERIFIED: what you could not check (short).
6. WHAT IS CORRECT: the things you verified as correct, so they are not re-litigated (max 8 bullets).

=== PLAN (v2) ===
{plan}"""

body = {"model": "deepseek-flash",
        "messages": [{"role": "system", "content": "You are a rigorous adversarial reviewer. You state findings "
                         "concretely with cell coordinates and arithmetic. You are terse. You never speculate."},
                      {"role": "user", "content": PROMPT}],
        "max_tokens": 9000, "temperature": 0.1, "effort": "low"}

req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                             data=json.dumps(body).encode(),
                             headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                                      "Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=900) as r:
    raw = r.read().decode()
d = json.loads(raw)
open(os.path.join(HERE, "ds-final-raw.json", "w").write(raw)
msg = d["choices"][0]["message"]
c = msg.get("content") or ""
print(f"finish={d['choices'][0].get('finish_reason')} content={len(c)} "
      f"reasoning={len(msg.get('reasoning_content') or '')} usage={json.dumps(d.get('usage'))} t={time.time()-t0:.0f}s")
open(os.path.join(HERE, "REVIEW-deepseek-v4.1-flash.md", "w").write(
    "# DeepSeek-V4.1-Flash 对抗式评审（计划 v2）\n\n"
    "- 模型: `deepseek-flash` = DeepSeek-V4.1-Flash（DeepSeek 官方 API，effort=low 精简档）\n"
    "- 输入: 计划 v2 全文 + 官方题面规则原文\n"
    f"- usage: {json.dumps(d.get('usage'))}\n\n---\n\n" + c)
print(c[:9000])
