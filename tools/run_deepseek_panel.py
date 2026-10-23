#!/usr/bin/env python3
"""Run the 3 panel briefs on DeepSeek-V4.1-Flash (official API, model id `deepseek-flash`).
Saves BOTH content and reasoning_content (the model's reasoning is the real payload:
we measured finish_reason=length with empty content on 2/3 calls).
"""
import json, os, threading, time, urllib.request

OUT = "/workspace/jspuzzle"
MODEL = "deepseek-flash"
URL = "https://api.deepseek.com/chat/completions"

NO_TOOLS = """# ⛔ 你没有任何工具

你**不能**读文件、**不能**执行代码、**不能**调用任何工具。请**不要**输出工具调用（不要输出 bash/DSML/function call 标记）。
所有需要的事实都已在下面给出；任何"验证"请**手算小例**完成。**直接产出最终答案文本。**

"""

CTX = """## 背景（可直接引用的事实）

Jane Street 谜题 "It's a Metric, Too"：N×N 方格划分成若干"州"（连通 + 有非平凡自对称的格子集）。州若每个非平凡自对称都恰好固定 1 格，则该格叫首都。相邻格移动费用：同州一步 = 州面积，跨州一步 = 两州面积较小者。格子里的数字 = 该格到**最近首都**的最小总费用。答案 = Σ(每行州面积和)²。

- 官方 5×5 example：州面积 7/4/3/11，首都 (3,2),(3,4),(5,5)（1-based），2×2 州**无首都**，行和 [37,29,31,43,55]，答案 **8,045**。已被三个独立方法复现。
- 首都判定可用**纯整数**实现：n 格州令 sr=Σr, sc=Σc，6 个"保持格点阵"条件 = `(sr−sc)%n==0`、`(sr+sc)%n==0`、`(2*sr)%n==0`、`(2*sc)%n==0`（rot180 用后两者，rot90/270 用前两者）。**禁止浮点**（双精度会让 5/3 这类质心判错 → 首都丢失 → 数字全错且不报错）。
- 候选自对称只有 8 个：绕质心的 90/180/270 旋转 + 过质心的 4 条反射。完备性论证：polyomino 边界方向集 {0°,90°} 必须被置换。
- **已证引理**（4000 次随机划分暴力验证，0 反例）：
  L1 紧边：d(x)>0 ⇒ 存在邻格 y 使 d(y)=d(x)−w(x,y)。
  L2：|d(x)−d(y)| ≤ min(s_x,s_y)（x,y 邻接）。
  L3：s_x ≥ max_{y∈N(x)} |d(x)−d(y)|（**必须限定邻格**；不限定则为假）。
  L4：d(x)=1 ⇒ x 邻接一个单格州（**反向为假**）。
  L5：d(x)=0 ⟺ x 是首都格。
- **关键反例**：4×4 存在两个**都合法**的划分给出**完全相同**的 16 值 d 场，但答案 304 vs 112。⇒ **d 场不决定答案**。
- 规模：4×4 有 11,506 连通子集、1,124 合法州、561,468 合法划分；记忆化 DP 计数（**无提示**）0.2s，"枚举全部划分+逐叶算 d 场" 400s。5×5: 22,041 合法州、2,638,025,192 合法划分、DP 计数 239s。

## 通用纪律（对你这一份也适用）

- **不许写完整实现代码**；可写算法伪码、公式、复杂度推导。验算请**手算小例**。
- **必须用具体小例证伪/证实**，不许只讲直觉。特别警惕"看起来对但其实不成立"的命题。
- 关键反例夹具的内容（直接给你，不用读文件）：4×4，划分 A = 第 0 行一整条 1×4（面积 4，无首都）+ 其余 12 格各为单格州；划分 B = 第 0 行两条 1×2（面积 2，无首都）+ 其余 12 格各为单格州。两者 d 场完全相同 = [[1,1,1,1],[0,0,0,0],[0,0,0,0],[0,0,0,0]]；A 行和 [16,4,4,4] 答案 304，B 行和 [8,4,4,4] 答案 112。
- 输出 **≤ 900 词**，结论先行，不要铺垫。
"""

TASKS = {
 "A": """# 你的任务：逆问题的算法范式

**"从 d 场（部分提示）还原划分"这个逆问题，在 11×11（121 格）上有哪些可行的算法范式？**

1. 给 **3~5 个真正不同的范式**（例如：约束传播/弧一致性、CP/ILP 编码、图重建（graph reconstruction from distance profiles）、分层/递归 landmark 定位、min-plus 代数视角、暴力+剪枝、其它）。每个都要：
   - 状态变量是什么；
   - 约束怎么表达（**落到纯 Python stdlib**，别依赖外部 solver）；
   - 剪枝/传播规则（特别是怎么用 L1/L2/L3）；
   - **在 121 格上的复杂度数量级**（不要假装精确）；
   - 怎么**保证或检验"答案唯一"**（d 场不决定答案这件事对求解器意味着什么）。
2. **明确推荐一个**并给理由（不要罗列优缺点后说"看你"）。
3. 每个范式的**失败模式**（什么情况下会爆）。
4. 哪个范式你认为是**行不通**的（例如依赖不可用的外部 solver），明说并给替代。

## 你可以先自证的一条线索（可推翻）

有候选认为：**带提示的唯一性判定本质上不需要"计数"，需要"枚举 + 收集答案"**（因为已证 d 场不决定答案，"划分数"不是判据）；而**带提示的相容划分数通常极少**（20+ 提示是很强约束），所以"提示引导搜索 + 答案收集"可能比 DP 计数便宜得多。
请**独立判断**这条线索是否成立，若不成立给反例。""",

 "B": """# 你的任务：唯一性判定算法（U9/U10）

**给定提示集 H（部分格上的 d 值），判定「与 H 相容的所有合法划分」产生的不同答案集合是否只有 1 个元素。**
已知：4×4 合法划分 561,468 个；无提示 DP 计数 0.2s；**带提示的答案级唯一性判定至今没有可用算法**；且**同一组提示可对应不同答案**（4×4：304 vs 112）。

1. 给 **2~3 个候选判定算法**（每个：状态变量、转移、剪枝、复杂度、内存）。请认真评估并给出结论：
   - **前沿 DP（frontier/plug DP）**：状态 = 已覆盖格的前沿划分 + **已累计行和向量** + **可达答案位图**。请给出答案上界的一般推导（N×N），并判断 11×11 的位图是否可行（内存量级）。
   - **分支限界 + 传播**：用 L1/L2/L3 做 bounds propagation（L3 给州面积下界），按"最左上未分配格"展开；上界如何剪。
   - 你想到的其它（例如 min-plus/商半环上的唯一性、ILP 化判定、把提示当观测做参数估计式推断等）。
2. **明确推荐一个**并说明理由。
3. **4×4 的单次判定预期耗时**（毫秒/秒/分钟）——给推导，不要拍脑袋。
4. **5×5 与 11×11 的可扩展性**，以及在什么规模退化。
5. **生成器里的用法**：如何用它在"不可再删提示集"贪心中做单次删除判定；单次判定成本决定贪心是否可行。

## 关键自证要求

请用**具体的小例**验证你的状态设计与转移不会漏解/不会重复计数（4×4 的 561,468 与 1,124 是已知真值可用作对照）。""",

 "C": """# 你的任务：其他数学分支扫描

**除了"枚举 + 剪枝"，还有哪些数学分支对这道题有用？**

1. 列 **8~12 个可能相关的分支**，每个必须写清：
   - 在本题里**具体对应什么量/结构**（不能只写分支名）；
   - 能**产出什么**（一个可计算的界？一个计数？一个判定？一个可证明的不变量？）；
   - **能不能落地**（纯 Python stdlib 可实现吗？还是需要外部 solver/库？）。
2. **筛掉一半**，明确说哪些是花架子/不适用，为什么。宁可少而实。
3. 特别评估并给结论（不要模棱两可）：
   - **Burnside 引理/轨道计数**：对"按 D4 等价的划分"计数（生成器去重/对称性破缺）——有用吗？
   - **图重建理论（graph reconstruction from distance profiles）**：d 场是不是"距离剖面"？landmark 递归定位能否用上？注意 d 依赖于未知的州划分，这会不会让类比失效？
   - **信息论/覆盖论证**：至少需要多少提示才能唯一确定答案？能否给出**下界**（哪怕粗的）？
   - **区间界/松弛**：能否在**不还原完整划分**的前提下，给出答案的**紧区间**（对 11×11 特别有用，因为唯一性可能不成立）？
   - **格点/半格点算术**：州质心常在 1/3、1/2 处；有没有"质心整除性"这类**结构性不变量**可反向约束划分？（候选线索：对奇数大小的州 n，若同时满足 (sr−sc)≡0 与 (sr+sc)≡0 (mod n)，则因 gcd(2,n)=1 有 sr≡sc≡0 (mod n)，即质心必在格点。请验证或推翻，并看它能否当剪枝过滤器。）
   - **图论**：州连通性 + 面积 + 对称，是否蕴含某个生成树/欧拉公式式的恒等式？
4. **最推荐的 2 个新分支**，说明各自能**新增什么现有计划没有的能力**。
5. 若有**已知数学问题/文献**与本题高度相关，点名并说明相似点。

## 纪律

- 必须给**可证伪的具体论断**，标出哪些是**已验证**、哪些是**推断**。
- 特别要求：对你没把握的分支，明确标注"未验证"而不是含糊过去。""",
}


def call(tag, task, max_tokens=40000):
    body = {"model": MODEL,
            "messages": [
                {"role": "system", "content":
                 "You are a rigorous mathematician and algorithm designer. You verify by computing, "
                 "not by assuming. You state concrete, falsifiable claims and mark what you verified "
                 "vs what you infer. You are terse; lead with the conclusion."},
                {"role": "user", "content": NO_TOOLS + task + "\n" + CTX}],
            "max_tokens": max_tokens, "temperature": 0.2, "effort": "high"}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                                          "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            raw = r.read().decode()
    except Exception as e:
        open(f"{OUT}/ds-panel{tag}.md", "w").write(f"# FAILED: {type(e).__name__}: {e}\n")
        if hasattr(e, "read"):
            open(f"{OUT}/ds-panel{tag}.md", "a").write(e.read().decode()[:2000])
        print(f"[{tag}] FAILED {e}", flush=True)
        return
    d = json.loads(raw)
    open(f"{OUT}/ds-panel{tag}-raw.json", "w").write(raw)
    m = d["choices"][0]["message"]
    content = m.get("content") or ""
    reasoning = m.get("reasoning_content") or ""
    u = d.get("usage", {})
    print(f"[{tag}] finish={d['choices'][0].get('finish_reason')} content={len(content)} "
          f"reasoning={len(reasoning)} usage={json.dumps(u)} t={time.time()-t0:.0f}s", flush=True)
    body_md = (f"# DeepSeek-V4.1-Flash — Panel {tag}\n\n"
               f"- model: `{MODEL}` (DeepSeek-V4.1-Flash, official API)\n"
               f"- finish_reason: {d['choices'][0].get('finish_reason')}\n"
               f"- usage: {json.dumps(u)}\n"
               f"- content_chars: {len(content)}  reasoning_chars: {len(reasoning)}\n\n---\n\n")
    body_md += ("## FINAL ANSWER\n\n" + content) if content.strip() else \
               ("## (no final content — reasoning trace below is the payload)\n\n" + reasoning)
    if content.strip() and reasoning.strip():
        body_md += "\n\n---\n\n## REASONING TRACE (raw)\n\n<details><summary>show</summary>\n\n" + reasoning + "\n\n</details>\n"
    open(f"{OUT}/ds-panel{tag}.md", "w").write(body_md)


threads = [threading.Thread(target=call, args=(t, task)) for t, task in TASKS.items()]
for t in threads: t.start()
for t in threads: t.join()
print("all panels done", flush=True)
