#!/usr/bin/env python3
"""Round 2: three DeepSeek-V4.1-Flash briefs focused on the 11x11 gap.

  A' : constraint-driven state CONSTRUCTION (no pre-enumeration) for 11x11
  B' : answer-level uniqueness judge: an implementable SPEC
  C' : hint minimisation + uniqueness judged as ONE algorithm (avoids U9/U10)

Critical prompt rules (learned the hard way):
  * the API has NO tool loop -> the model must be told "no tools, don't emit tool calls"
  * reasoning is mandatory and long -> max_tokens must be generous; reasoning_content is salvageable
"""
import json, os, threading, time, urllib.request

OUT = "/workspace/jspuzzle"
MODEL, URL = "deepseek-flash", "https://api.deepseek.com/chat/completions"

CTX = """## 背景（全部已独立验证，可直接引用）

Jane Street 谜题 "It's a Metric, Too"：N×N 方格划分成若干"州"（连通 + 有非平凡自对称的格子集）。州若**每个**非平凡自对称都恰好固定 1 格，则该格叫首都（否则该州无首都）。相邻格移动费用：同州一步 = 州面积，跨州一步 = 两州面积较小者。格子里的数字 = 该格到**最近首都**的最小总费用。答案 = Σ(每行州面积和)²。

**已验证地基**:
- 官方 5×5 example：州面积 7/4/3/11，首都 (3,2),(3,4),(5,5)（1-based），2×2 州无首都，行和 [37,29,31,43,55]，答案 **8,045**。三个独立方法复现一致。
- 首都判定用**纯整数**实现（禁浮点，双精度会让 5/3 这类质心判错 → 首都静默丢失）：n 格州令 sr=Σr, sc=Σc，6 个"保持格点阵"条件 = `(sr−sc)%n==0`、`(sr+sc)%n==0`、`(2*sr)%n==0`、`(2*sc)%n==0`（rot180 用后两者，rot90/270 用前两者）。
- 候选自对称只有 8 个（绕质心 3 旋转 + 过质心 4 反射）：polyomino 边界方向集 {0°,90°} 必须被置换 ⇒ 旋转角必 90° 倍、反射轴必 45° 倍。
- **已证引理**（4000 次随机划分暴力验证 0 反例）：L1 紧边 d(x)>0 ⇒ 存在邻格 y 使 d(y)=d(x)−w(x,y)；L2 |d(x)−d(y)| ≤ min(s_x,s_y)（邻接）；L3 s_x ≥ max_{y∈N(x)}|d(x)−d(y)|（**必须限邻格**）；L4 d(x)=1 ⇒ 邻接单格州（**反向为假**）；L5 d(x)=0 ⟺ 首都格。
- **反例 1（d 场不决定答案）**: 4×4 两个**都合法**的划分给出**完全相同**的 16 值 d 场，答案 **304 vs 112**（划分A: 第0行一整条1×4 + 12 个单格州; 划分B: 第0行两条1×2 + 12 个单格州）⇒ 唯一性必须**枚举答案集合**，"划分数"不是判据。
- **反例 2（答案只在 D2 下不变）**: 官方 example 旋转 90° → 答案 **8029 ≠ 8045**；180°/水平/竖直反射不变 ⇒ 生成器去重只能用 D2。
- **反例 3（整行 1×k 州可多方式拆分）**: 6 长行 → 5 个划分 / 4 个不同答案；11 长行 parts≥2 的分拆有 **14** 种 ⇒ 同一提示集可对应多个答案。
- **反例 4（剪枝下界）**: 搜索中真实边权未知 ⇒ 下界必须用"每步 ≥1"的最弱值，即到最近**已知**首都的 **Manh 距离**; 用真实权算 d_lb 会**误杀正解**（官方 example 自身: 10 个提示误剪 9 个）。
- **合法州库随尺寸爆炸（关键）**: 4×4 = **1,130** 个合法州（连通子集 11,506）；5×5 = **22,317** 个（连通子集 2,301,877）⇒ 每级 ×19.7。外推 **11×11 ≈ 1.3×10¹² 个合法州** ⇒ **"预枚举所有合法州"在 11×11 完全不可行**（按 10⁶/秒也要 15 天）。
- 4×4 其它回归常量（由可执行引擎 engine.py 产出）: 合法划分 562,308；其中至少含一个首都的 559,585。
- **正式盘 11×11**: 题面**没有画州边界**（原文 "can be subdivided"），只有 **33 个数字**（已机器验证：逐行 4/1/3/4/3/3/3/4/3/1/4，位置见下表），答案**不保证唯一**。
  ```
  row  1: c2=8   c3=4   c6=11  c10=5
  row  2: c8=11
  row  3: c3=7   c6=1   c11=14
  row  4: c1=28  c4=51  c7=1   c9=6
  row  5: c2=22  c9=4   c11=1
  row  6: c4=15  c6=10  c8=0
  row  7: c1=11  c3=11  c10=9
  row  8: c3=17  c5=14  c8=10  c11=13
  row  9: c1=30  c6=6   c9=45
  row 10: c4=10
  row 11: c2=26  c6=0   c9=77  c10=61
  ```
- 提示格中 d=0 的两格 ⇒ 至少两个首都：(6,8) 与 (11,6)。d=1 的三格 ⇒ 每格紧邻一个单格州：(3,6),(4,7),(5,11)。

## 通用纪律（对你这份也适用）

- ⛔ **你没有任何工具**：不能读文件、不能执行代码、不能调用工具；**不要输出任何工具调用标记**（不要 bash/DSML/function call）。所有事实都在上面；需要验算请**手算小例**。**直接产出最终答案文本。**
- **不许写完整实现代码**；可写算法伪码、公式、复杂度推导。
- **必须用具体小例**支撑每个论断；警惕"看起来对但不成立"的命题（例如"每行 1×k 州可拆分"这类结构会让答案多值）。
- 输出 **≤ 900 词**，结论先行，不要铺垫。

"""

TASKS = {
 "A2": """# 任务 A'：11×11 上"不预枚举"的州构造算法

**问题**: 合法州库在 11×11 约 1.3×10¹² 个，预枚举不可行。那么求解器如何**在约束下直接构造**州？

请给出**一个**具体可实现的构造算法（不要罗列），并回答:

1. **构造规则**: 从锚点（最左上未分配格）出发，如何生长出一个连通且对称的格子集？给出保持对称的精确规则（对 8 类对称分别如何处理；注意"加 x 的前提是 mirror(x) ∈ S ∪ {x}"，轴上格自镜像只能加一个）。说明何时判定一个候选集合为"合法州"、如何取首都。
2. **提示剪枝**: 生长过程中如何用 33 个提示值剪枝？哪些提示值能约束"这个格属于面积多大的州"？L3（面积下界）与 Manh 下界怎么进入生长过程？
3. **完备性**: 怎样保证不漏掉任何与提示相容的合法划分？（这是本题最难的一点，请给出可验证的论证，而不是"枚举所有"。）
4. **复杂度**: 每个锚点的候选数大致多少？总搜索节点数在 11×11 上的数量级估计（可给数量级，不要假装精确）。你用什么依据估的？
5. **停止判据与报告格式**: 什么时候能说"已穷尽"？如果预算耗尽，交付什么（候选答案集合 + 基数 + 是否穷尽）？
6. **自证**: 在 4×4 反例夹具上（d 场 = [[1,1,1,1],[0,0,0,0],[0,0,0,0],[0,0,0,0]]，答案 304 与 112 两个），你的算法必须报"答案集合基数 = 2，不唯一"。写出你期望看到的中间量（每个锚点的候选数、终止条件）作为可核对的靶子。""",

 "B2": """# 任务 B'：答案级唯一性判定器的可执行规格

**问题**: 给定提示集 H（部分格上的 d 值），判定「与 H 相容的所有合法划分」产生的**不同答案**集合是否只有 1 个元素。已知: 4×4 合法州 1,130 / 合法划分 562,308（无提示，DP 计数 0.2s）；5×5 合法州 22,317（11×11 预枚举不可行）。

请给出一份**可交给程序员直接实现**的规格:
1. **接口**: 函数签名、输入（提示集 + 网格尺寸 + 预算）、输出（答案集合、基数、划分数、是否穷尽、节点数）。
2. **算法步骤**: 从锚点展开 → 构造候选州 → 检验与提示一致 → 收集答案 → 早停条件。给出"检验与提示一致"这一步的**正确做法**（提示格在候选州内时，如何用最小可能边权得到可证的下界；注意用真实边权会误杀正解）。
3. **答案的定义**: "答案" = Σ_r(行州面积和_r)²。要不要在搜索中增量维护行和？怎么维护才能支持"发现第二个不同答案就早停"？
4. **"相容"的判定**: 一个划分与提示相容 = 对每个提示格 x 有 d(x) = 提示值。给出如何在**不重算整张 d 场**的前提下做这个判定（或说明必须重算并给出代价）。
5. **完备性/正确性的可核对靶子**: 在 4×4 夹具上应输出什么（答案集合、基数、划分数、是否穷尽）？在官方 5×5 example 的 10 个提示上应输出什么？
6. **代价模型**: 4×4 / 5×5 / 11×11 上单次判定的数量级估计与依据。""",

 "C2": """# 任务 C'：提示集最小化 + 唯一性判定，合成一个算法

**问题**: 生成器要造"答案级唯一"的 puzzle，并挑一个**尽量少**的提示集。目前的困难: 唯一性判定与提示选择是两步，且唯一性判定的代价未实测。

请给出一个**单一算法**，完成:
1. 输入: 一个合法划分（ground truth）+ 网格尺寸 + 预算。输出: 该划分是否"可出题"、一个提示集、以及该提示集下的答案集合基数。
2. **可出题的判据**: 若"全揭示"都不唯一，则**任何**提示子集都不唯一 ⇒ 直接拒用该划分。给出这个判据怎么算（不要靠试）。
3. **单调性利用**: 已知 H'⊆H ⇒ 与 H' 相容的划分更多 ⇒ 答案集合只增不减; 故"删掉 h 后不唯一"⇒ h 永远不可删 ⇒ **只扫一遍**即可得到不可再删提示集。请把这条写进算法并说明为什么不需要"删到不动点"。
4. **单次删除判定的代价**: 每次判定是一次答案级唯一性判定 ⇒ 总代价 ≈ |H| × 单次判定。请给出**单次判定的实测预期**（4×4 / 5×5 / 11×11 的数量级）与依据; 并说明若单次判定太贵，生成器应如何退让（例如换划分、换提示数下限、报失败）。
5. **难度档位**: 如何产出"最容易"与"最难"两档（最容易 = 全部提示；最难 = 不可再删集）？并说明"最难"是相对于给定求解器与剪枝强度而言的。
6. **自证靶子**: 在 4×4 夹具上，从"全揭示 16 格"开始贪心删，期望删到几个提示才不可再删？请手算这个数（该夹具的完整 d 场已知、答案集合 = {304,112}），并说明你用什么理由判断已不可再删。""",
}


def call(tag, task, max_tokens=40000):
    body = {"model": MODEL,
            "messages": [
                {"role": "system", "content":
                 "You are a rigorous mathematician and algorithm designer. You verify by computing, "
                 "not by assuming. You state concrete, falsifiable claims and mark what you verified "
                 "vs what you infer. You are terse; lead with the conclusion."},
                {"role": "user", "content": task + "\n" + CTX}],
            "max_tokens": max_tokens, "temperature": 0.2, "effort": "high"}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                                          "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            raw = r.read().decode()
    except Exception as e:
        open(f"{OUT}/ds-{tag}.md", "w").write(f"# FAILED: {type(e).__name__}: {e}\n")
        print(f"[{tag}] FAILED {e}", flush=True); return
    d = json.loads(raw)
    open(f"{OUT}/ds-{tag}-raw.json", "w").write(raw)
    m = d["choices"][0]["message"]
    content = m.get("content") or ""; reasoning = m.get("reasoning_content") or ""
    u = d.get("usage", {})
    print(f"[{tag}] finish={d['choices'][0].get('finish_reason')} content={len(content)} "
          f"reasoning={len(reasoning)} usage={json.dumps(u)} t={time.time()-t0:.0f}s", flush=True)
    md = (f"# DeepSeek-V4.1-Flash — {tag}\n\n- model: `{MODEL}` (official API)\n"
          f"- finish_reason: {d['choices'][0].get('finish_reason')}\n- usage: {json.dumps(u)}\n"
          f"- content_chars: {len(content)}  reasoning_chars: {len(reasoning)}\n\n---\n\n")
    md += ("## FINAL ANSWER\n\n" + content) if content.strip() else \
          ("## (no final content — reasoning trace below is the payload)\n\n" + reasoning)
    if content.strip() and reasoning.strip():
        md += "\n\n---\n\n## REASONING TRACE (raw)\n\n<details><summary>show</summary>\n\n" + reasoning + "\n\n</details>\n"
    open(f"{OUT}/ds-{tag}.md", "w").write(md)


threads = [threading.Thread(target=call, args=(t, task)) for t, task in TASKS.items()]
for t in threads: t.start()
for t in threads: t.join()
print("all briefs done", flush=True)
