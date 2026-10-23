# DeepSeek-V4.1-Flash — Panel C

- model: `deepseek-flash` (DeepSeek-V4.1-Flash, official API)
- finish_reason: stop
- usage: {"prompt_tokens": 1645, "completion_tokens": 9454, "total_tokens": 11099, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 8022}, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 1645}
- content_chars: 2492  reasoning_chars: 31174

---

## FINAL ANSWER

**结论：** 除枚举+剪枝外，真正有产出的只有四类：**整数模算术/格点过滤器、加权图度量约束传播、CP-SAT/ILP、polyomino 组合计数/DP**。Burnside 只能做去重；图重建基本不适用；信息论只能给粗计数；区间界可证但很松。

| 分支 | 对应量/结构 | 产出 | 落地 |
|---|---|---|---|
| 群论/D4 稳定子 | 州的 8 个候选自对称、固定格数；首都=每个非平凡自对称恰固定 1 格 | 判定首都；状态 canonical form；轨道计数 | stdlib |
| 格点/模算术 | \(n,s_r,s_c\)；质心 \((s_r/n,s_c/n)\) | 旋转对称的精确整数过滤 | stdlib；**已验证** |
| 加权图度量/差分约束 | \(d\) 是到最近首都的加权最短路势；边权 \(s_x,\min(s_x,s_y)\) | L1–L4 传播、矛盾检测、面积上下界 | stdlib |
| 整数规划/CP-SAT | 每格州标号、连通流约束、自对称、\(d\) 约束 | 可行性/不可行、优化答案、紧区间 | 需外部 solver |
| Polyomino 组合/DP | 连通子集、面积分布、按行转移 | 小 \(N\) 枚举/计数；11×11 转移矩阵 | stdlib 可行但重 |
| 区间/分支定界 | 行和 \(R_r=\sum_c s_{r,c}\) | 答案证书区间 | stdlib；松 |
| 信息论/计数 | 合法划分数、答案类数 | 条件比特下界 | 仅小规模可算 |
| 图重建/metric dimension | 距离剖面、landmark 集 | 本题不适用 | 否 |
| 欧拉/平面拓扑 | 周长 \(P=4A-2e\)、洞数 \(\chi=1-h\) | 弱剪枝 | 弱 |
| 谱图论/Laplacian | 邻接谱与面积/\(d\) 无直接关系 | 无 | 花架子 |
| Monte Carlo | 随机合法划分、答案分布 | 11×11 经验分布 | stdlib；不证明 |

**筛掉一半：** 丢 **图重建、欧拉拓扑、谱图论、Monte Carlo、纯 Burnside 计数**。理由：图重建假设固定图与已知距离剖面，本题 \(d\) 只是“到最近未知首都”的标量，边权依赖未知州面积；拓扑只约束周长/洞，\(d\) 只看面积；谱无直接约束；Monte Carlo 不证明唯一性；Burnside 不解对称破缺。

**专项结论**

- **Burnside：** 数学上可数 D4 轨道，但答案 \(\sum R_r^2\) 在 90°/270° 下不守恒（行和变列和），全 D4 商化会错。只可在**状态生成去重**用 D4 canonical form，在**答案等价**上最多用 D2。不是核心工具。
- **图重建：** 不适用。\(d\) 不是标准距离剖面；4×4 反例已证明同一 \(d\) 场给答案 304 vs 112。零格确为首都（L5），但无法递归恢复州面积。**丢弃。**
- **信息论/覆盖：** 4×4 有 561,468 划分，5×5 有 \(2.638\times10^9\) 划分，约 31.3 bit 才区分划分；但答案类数未知，且完整 16 值 \(d\) 场都不够（4×4 反例）。没有形式化 hint 模型时，下界只能是很粗的计数界。**只作 sanity check。**
- **区间界：** 可给但松。令 \(L_x=\max_{y\sim x}|d(x)-d(y)|\)，由 L3 有 \(s_x\ge L_x\)。11×11 中
  \[
  \sum_r\Big(\sum_{c}L_{r,c}\Big)^2 \le \text{Answer}\le 11\cdot(11\cdot121)^2=19{,}487{,}171.
  \]
  下界通常远不紧；紧区间需 CP-SAT/分支定界。**可用作证书，不足以直接解 11×11。**
- **质心整除性：** **已验证。** 若 \(n\) 奇且 \(s_r-s_c\equiv0\)、\(s_r+s_c\equiv0\pmod n\)，则 \(2s_r\equiv0\)、\(2s_c\equiv0\)，因 \(\gcd(2,n)=1\)，得 \(s_r\equiv s_c\equiv0\pmod n\)，质心在格点。例：n=3 的 L 形 \(s_r=s_c=1\)，过不了 180° 检查；n=5 十字 \(s_r=s_c=0\)，通过。**但**只对旋转对称候选成立；奇数大小的反射-only 州可有非整质心（如竖直对称 5 格 \(s_r=0,s_c=2\)），不能因此判非法。它是便宜的精确过滤器，且基本等价于已有整数条件。
- **图论连通+面积+对称：** 只有周长/洞数恒等式，无法反推 \(d\) 或行和；弱。

**最推荐 2 个新分支**

1. **CP-SAT/ILP + 连通流约束 + 模算术过滤**：新增“证明无解/求紧区间/处理 11×11”能力；5×5 已有 \(2.6\times10^9\) 划分，纯枚举必败。
2. **加权图度量约束传播 + 区间分支定界**：新增“不还原完整划分也能剪枝并给证书区间”的能力；纯 stdlib 可做，直接利用 L1–L4。

**相关文献/问题：** polyomino 枚举（Klarner）、图的加权 Voronoi 图、graph metric dimension、Graph Reconstruction Conjecture、Burnside/Pólya 计数、连通约束的 single-commodity flow ILP。相似点是“对称 polyomino 划分 + 未知加权 Voronoi 中心”，但重建理论不是本题的正确类比。

---

## REASONING TRACE (raw)

<details><summary>show</summary>

We need answer in Chinese likely. Need satisfy <=900 words. Need rigorous, concrete. We need evaluate branches. Need no tools. Need maybe verify centroid modular claim by hand. Need list 8-12 branches with mapping, output, implementable. Screen half. Special eval. Recommend 2. Known literature.

We need parse puzzle enough. Need give concrete claims. Let's plan.

We need be terse, conclusion first. We need not write full code. Need mark verified/inferred/unverified.

Key: "other math branches besides enumeration+pruning." Need branches relevant.

Need evaluate Burnside. D4 equivalence for partitioning count? likely not useful for solving specific d-field because answer invariant? Wait answer = sum row state-area sums squared. Is answer invariant under D4? Row sums permuted/reversed? If rotate, rows→columns and row sums change (sum over row of state area sums vs columns). Answer is sum of squared row sums, not invariant under 90 rotation generally; under reflections preserving rows maybe. But generator dedup of 8 symmetries of states yes for canonicalizing states, not partition counting. Burnside helps count unlabeled partitions but doesn't constrain given d field; d field and answer may break symmetry. Could use canonicalization to dedupe states/placements under D4 (if searching all partitions with symmetry) but only factor 8, and answer non-invariant under 90 so cannot quotient whole solutions. Conclusion: marginal, not solve; only state dedup/canonical label.

Graph reconstruction: d field distance profile? d is min weighted distance to capitals, but capitals unknown and state partition unknown, weights depend on states. It's not graph distance profile in standard sense because edge weights s_x/min(sx,sy), and centers (capitals) unknown. Landmark recursive localization? If know a capital and some areas maybe BFS, but no; d=0 reveals capitals exactly (L5). Actually d=0 gives all capitals! Since d field given, capitals are zeros. Need state partition. Could use d to infer areas via local differences? L1-L5. But reconstruction theory not applicable: graph fixed grid, distance labels not all-pairs, weights unknown and correlated. The 4x4 counterexample decisively kills uniqueness from d. Landmark recursion maybe not.

Information theory/coverage: Need lower bound hints? Hints unclear. Could count candidate partitions vs d field. Number of legal partitions 561,468 for 4x4; answer classes? At least? Need lower bound number of hints to uniquely determine answer. If hint = reveal a cell's state/area? We can use counting: with no hints, 4x4 has at least 2 partitions same d different answer, so no d alone. But lower bound hints likely not useful without hint model. If hints are d values, d field itself not enough. If hint reveals cell labels, log2(#partitions) bits / etc. For 5x5 partition count 2.6e9 ≈ 31.3 bits. If each hint ≤? Not specified. A coarse lower bound: if hint is "membership of one cell to a named state" maybe uncertain. Need be concrete. We can say without formal hint oracle, information lower bound is ill-posed; if hint reveals full partition of one cell with ≤? Could provide: to distinguish partitions, need at least ceil(log2 2.638e9 / log2(...)). But answer uniqueness not partition uniqueness. Number of possible answers ≤ number partitions, no lower bound. Need maybe use 4x4 has at least two. For 11x11 unknown; can't give useful lower bound. Conclusion: counting gives search-space sizes and a conditional bound only; not a solution.

Interval bounds/relaxation: Can give answer interval maybe using d constraints. For 11x11 uniqueness uncertain. Need derive? Answer sum row sums squared, row sums = sum over cells in row of area(state(cell)). If area lower/upper known. d=0 capitals. L3 s_x ≥ max adjacent |Δd|, so lower bounds area for non-capital? For every cell x, area s_x at least max neighbor diff. Also state area ≤? N^2. Then row sums lower/upper: For row r, each cell contributes s_x; if area lower bounds a_x, row sum ≥ sum a_x, upper? Areas constrained by partition total ≤121 and state consistency. Simple interval: s_x ∈ [L_x, 121], but same row cells in same state counted with same area. A crude row sum lower = sum L_x, upper = sum 121 = 121*11. Then answer interval sum L_row^2 to sum U^2. Not tight. Better use areas bounded by max possible connected polyomino containing x? Hard. Could formulate ILP/CP-SAT not stdlib. Relaxation can produce certified interval via LP but external. For 11x11 maybe use local constraints to prune.

Grid/semilattice centroid: Need verify claim. Given n-cell state, coordinates integers, sr=sum r, sc=sum c. Centroid = (sr/n, sc/n). Candidate symmetries preserving lattice? Wait for a polyomino on square lattice, reflection axes may be at half-integers? The conditions given: rot180 requires (2sr)%n==0 and (2sc)%n==0 (centroid at lattice or half-lattice? Actually for 180 rotation preserving lattice, center can be integer or half-integer? Let's think: 180 rotation about (a,b) maps cell centers? Need coordinate convention. The given conditions for rot180 = (2*sr)%n==0, (2*sc)%n==0, which means centroid coordinate = integer/2? If n odd, 2sr divisible n implies n|sr since gcd(2,n)=1, so centroid integer. For rot90/270 require sr≡sc and sr≡−sc mod n, i.e. sr±sc divisible n. For n odd, both imply 2sr≡0 and 2sc≡0 mod n, so sr≡sc≡0 mod n; actually from sr−sc and sr+sc divisible n: add gives 2sr divisible n, n odd => sr divisible n; subtract => 2sc divisible n => sc divisible n. Thus centroid at grid point (integer coordinates). The claim "if odd n and both (sr−sc)≡0 and (sr+sc)≡0 mod n then sr≡sc≡0" is true. Need verify with small examples.

Can use as filter for rot90/270 (and any state with 4-fold symmetry) when n odd: centroid integer. For rot180 with n odd also requires sr,sc divisible n. Reflection conditions? Need know four reflections. If reflection vertical/horizontal axes through centroid? For cell set, axis must be at integer or half-integer depending. Given "6个保持格点阵条件" condition list only four checks? Need not. But centroid integrality for odd n for rotations. Actually for any nontrivial symmetry? For odd n, any symmetry has a fixed cell? Wait if finite set of odd size, an involution symmetry fixes an odd number? Not necessarily. For reflection, if size odd, axis contains odd? A reflection on a finite set can have odd size with axis through cells or gaps? Example 3 cells in L? Reflection vertical axis x=0.5 maps cells maybe no fixed cell? For odd size, a reflection has fixed cells on axis; axis could be between grid columns (no fixed cells), then size even? Because pairs. If axis through grid line? Need coordinate convention. But if reflection axis at half-integer between cell columns, no cell centers fixed, all pairs, even. So odd size reflection must fix at least one cell, axis through centers (integer coordinate) or maybe horizontal. Then centroid lies on axis, but not necessarily integer both coordinates? If vertical axis x=integer, centroid x=integer; y average not constrained. So not full lattice.

Important: Candidate self-symmetries only 8: rotations about centroid + 4 reflections through centroid. If state has any nontrivial symmetry, each symmetry must map grid cell centers to grid cell centers? Is that required? They say preserve lattice? Actually cell set is subset of grid cells; symmetry of polyomino maps cells to cells; axes can be at integer or half-integer coordinates. Given conditions.

The "centroid integrality" can prune states with odd n and 4-fold? For 90 rotation, n odd => centroid at grid point. For 180 rotation n odd => centroid at grid point too (since 2sr%n and n odd). For reflection odd n: one coordinate integral maybe.

Need verify with example n=5 plus shape cross centered at (0,0): cells center? coordinates maybe integers. sr=0 sc=0, n=5; divisible yes. n=3 L triomino? It has reflection but no rot? Example cells (0,0),(1,0),(0,1), n=3. sr=1, sc=1, not divisible by 3. Does it have nontrivial self-symmetry? No, L triomino no symmetry? Actually L triomino has no reflection. I triomino n=3 horizontal cells (-1,0),(0,0),(1,0): sr=0, sc=0 divisible. Good. V triomino? cells (0,0),(1,0),(0,1) no. T tetromino n=4 centroid maybe half. For odd symmetric shapes usually centroid can be non-integer if only reflection? Example plus? n=5 centroid integer. Shape with vertical reflection and odd n: e.g. cells top row 3, middle center 1, bottom center 1? Coordinates ( -1,1),(0,1),(1,1),(0,0),(0,-1) n=5, vertical axis x=0, sr sum x=0, sc sum y=1+1+1+0-1=2, not integer? centroid (0,0.4). Is this polyomino symmetric vertical? cells: row y=1 x=-1,0,1; row y=0 x=0; row y=-1 x=0. Vertical reflection x->-x fixes set. n=5 odd, centroid y=2/5 not grid. So full lattice not required; only x integer. So claim only for 4-fold rotations/180? For 180, if odd and rot180, centroid integer both. Let's test shape n=5 with rot180? Centroid must be integer? Take cross plus with cells (0,0),(±1,0),(0,±1), sr=sc=0 yes. Could there be rot180 with odd n centroid half-integer? A set invariant under 180 about half-integer center: pairs all cells except fixed cell at center. If center half-integer, no grid cell fixed (cell centers at integer), so odd size impossible (all pairs). Thus odd n rot180 implies fixed cell at center => center integer. Good. For 4-fold same.

Could use as pruning: For a proposed state with odd n and claimed 90/180/270 symmetry, require centroid coordinates integers. But this is equivalent to the modulo conditions already. The question asks candidate clue: "对奇数大小的州 n，若同时满足 (sr−sc)≡0 与 (sr+sc)≡0 (mod n)，则因 gcd(2,n)=1 有 sr≡sc≡0 (mod n)，即质心必在格点。请验证或推翻，并看它能否当剪枝过滤器。" Yes verified. But nuance: rotations about centroid; for rot180 only conditions (2sr)%n==0 and (2sc)%n==0. For n odd equivalent to sr%n=0 and sc%n=0. For rot90/270: both conditions. Then centroid at integer coordinate. This can filter after computing n,sr,sc before testing actual rotation. It is cheap and exact. It is already likely in integer candidate test; not new beyond given. But can use for state generation: enumerate connected polyominoes, compute n,sr,sc, discard impossible odd symmetric rotations. It doesn't constrain reflection only. It cannot reverse partition except as local filter. Need give small example: n=3 rot180 symmetric horizontal I: sr=0 sc=0; pass. n=3 L: sr=1,sc=1; (2sr)%3=2 !=0, fail, correctly no 180. n=5 vertical-reflection shape above: sr=0,sc=2; (2sc)%5=4 !=0, fail rot180, but still legal due reflection; so don't over-prune. That's important: if state has nontrivial self-symmetry, not necessarily rotation. The modulo condition is only for rotation candidates. A state with n odd and only reflection can have nonintegral centroid in one coordinate; so cannot require integrality for all odd states, only those whose nontrivial symmetries include rotation. But puzzle says "州（连通 + 有非平凡自对称）"; a state may be reflection-only. The "6 conditions" test all candidate symmetries; if any passes, capital if each nontrivial self-symmetry fixes exactly 1. The cap can be reflection-only. So centroid divisibility is not necessary for legal state; it is necessary for states where the accepted symmetry is rotational. Need be precise. The claim "odd n with both congruences implies centroid lattice" is true but its use as filter must be to reject a rotational symmetry candidate, not reject the state outright.

Need list branches. Let's brainstorm:

1. Enumerative combinatorics / generating functions for polyominoes and partitions — count states/partitions, canonical enumeration, memoized DP. Already in plan. But "other" maybe include.

2. Group theory (Burnside/Polya, symmetry groups) — D4 orbits, stabilizers, fixed-cell count.

3. Metric geometry / graph metric / Voronoi diagrams — d field as weighted Voronoi to capitals; reconstruct regions of influence. Could derive bisectors and constraints.

4. Algebraic graph theory / spectral graph? Maybe not.

5. Integer linear programming / constraint programming / polyhedral combinatorics — model connected components, symmetry, d constraints; external solver needed. Could be useful for 11x11.

6. Computational geometry / lattice geometry / centroid modular arithmetic — lattice/semilattice.

7. Information theory / entropy / counting lower bounds.

8. Graph reconstruction / distance profiles.

9. Combinatorial optimization / branch and bound / SAT.

10. Topology / Euler characteristic / planar graph formulas for connected polyominoes. Euler formula relates cells, adjacency edges, perimeter, holes. Connectedness and area imply perimeter etc. Could help prune or count. For a polyomino: V? For union of n unit squares connected, Euler χ = n - e + v? Actually cell complex. Perimeter = 4n - 2e_int. Euler characteristic = n - e_int + v? Not directly. For no holes, perimeter formula. Could use area + perimeter? d uses area only. Symmetry imposes perimeter. But not likely.

11. Probability / random sampling / Monte Carlo — estimate answer distribution for 11x11, find uniqueness. Could be useful but cannot prove.

12. Dynamic programming over subsets / transfer matrix — not branch? Maybe "analytic combinatorics" counting.

13. Order theory / partial orders? no.

14. Coding theory / error-correcting? Hints? no.

Need 8-12 branches, each specific. Then screen half. Need "筛掉一半" maybe list 10, say discard 5. Keep 5.

Need recommend 2 new branches: likely (a) CP-SAT/ILP with connectivity via flow and d constraints (but external solver; if no external libs maybe not pure stdlib). But question asks can land pure Python stdlib or external. If recommendation must new ability. Maybe (b) lattice/centroid modular filters + group action canonicalization? But special evaluation maybe Burnside marginal. Another: weighted Voronoi / shortest path dual / metric constraints L1-L4 as local constraint propagation. That is "metric graph / difference constraints" can derive area lower bounds and interval. Could implement stdlib. Another: combinatorial optimization / CP-SAT for 11x11 when enumeration infeasible. But external solver. They ask "new branch" not necessarily stdlib. Need recommend 2: (1) integer programming/CP-SAT with connectivity cuts and modular symmetry filters; (2) metric/Voronoi constraint propagation + interval arithmetic. Or "information-theoretic counting" for lower bounds? Need be practical.

Need known math/literature: "polyomino enumeration", "Voronoi diagrams on graphs", "graph reconstruction conjecture" (not applicable), "Burnside/Pólya", "Euler formula for polyominoes", "distance geometry / metric cones", "exact cover". The problem resembles "polyomino tiling/partition with symmetry constraints" and "weighted Voronoi game". Maybe mention "metric dimension" and "landmark-based graph distance reconstruction" (resolving sets). The d field is not a distance profile; but "metric dimension" is about resolving sets. If capitals are landmarks, d gives distance to nearest landmark with weird weights. Known "weighted Voronoi" / "additively weighted Voronoi". Also "reconstruction from distance profiles" maybe "graph metric reconstruction". Need name exact: Graph Reconstruction Conjecture (deck of vertex-deleted subgraphs) not distance profiles. "Distance profiles" in graph theory = multiset of distances from a vertex; "metric dimension" = landmark set. Our d is single scalar per cell to nearest capital, not vector distances to landmarks. So analogy fails.

Need verify hand small example for centroid claim. Use n=5 plus and L. Also mention gcd(2,n)=1. Need be careful: from (sr-sc)≡0 and (sr+sc)≡0 mod n, adding gives 2sr≡0, since gcd(2,n)=1 => sr≡0; similarly sc≡0. This is pure modular arithmetic; verified. It means centroid (sr/n,sc/n) has integer coordinates. For n odd rot90/270 or rot180. Use example n=5 plus: sr=sc=0 pass. n=3 L: sr=1 sc=1; (sr-sc)=0 mod3 but (sr+sc)=2 not; rot90 fails; (2sr)=2 mod3 fail rot180. Correct.

But wait coordinates sr=Σr, sc=Σc; if cells are indexed 0..N-1, plus centered at (1,1) n=5: cells (1,1),(0,1),(2,1),(1,0),(1,2): sr=5, sc=5? Actually sum r =1+0+2+1+1=5, sum c=5, n=5 => sr/n=1 integer. Good. If centered at (0,0) using signed coordinates same. Need not.

Need maybe derive interval bound. Can we give concrete crude formula? Let L_x = max(0, max_{y~x}|d(x)-d(y)|) by L3 for area of state containing x. Actually L3 says s_x ≥ max neighbor diff. So lower bound for area. For capitals d=0, L3 also applies? s_x ≥ max diff yes. So define a_x ≥ L_x. Row sum R_r = Σ_{c} s_{(r,c)}. Lower bound R_r ≥ Σ_c L_{r,c}. Upper? Each s_x ≤ 121 (or ≤ N^2). So R_r ≤ 121*11=1331. But total area over all cells = Σ_states s^2 ≤ 121^2; row sum upper maybe total? For row of 11 cells, each ≤121, so 1331. Then answer A = Σ R_r^2 between Σ Lrow^2 and 11*1331^2. That's very loose but certified. Can improve upper using total squared area max given 121 area partition into states? Since Σ s^2 ≤ 121^2 (all one state not legal? if all one state has symmetry? but upper). Row sum ≤ total Σ s^2? Row sum of areas over 11 cells ≤ Σ all s^2? Actually Σ_c s_c = Σ_states s^2 ≤ 121^2. So each row sum ≤121^2=14641, but also ≤11*121=1331. Use min. Answer ≤11*1331^2≈19.5M. Lower maybe 0. Not tight. Could mention use per-cell lower and state consistency; exact tight interval requires solving optimization.

Could give better: For each row, R_r = Σ_cells s_c. If lower L_c, R_r ≥ Σ L_c. Upper using remaining area? For each state intersecting row, s ≤ 121; but sum over cells in row = Σ_states |S∩row| s. Max with 11 cells each 121 is 1331. So interval. Not useful for 11x11 but can certify ranges for search. Need be honest: "可给，但不紧；紧区间需要 CP-SAT/LP".

Need information lower bound: We can compute partition counts: 4x4 561,468; 5x5 2.638e9. If a hint reveals one bit, need log2(2.6e9)≈31.3 bits to identify partition, but answer may have fewer classes. For 11x11 unknown; enumeration infeasible. Can't give lower bound on answer hints. Need maybe "至少 2 个 d 值? 4x4 counterexample shows full d (16 values) not enough; so any hint scheme weaker than full d needs more structure. This is a lower-bound of a sort: even 16 d-values (if hint = d field) insufficient." Good concrete. For answer uniqueness, need hints that expose state areas/row sums, not d. But no formal model.

Need evaluate Burnside more. Suppose count partitions modulo D4: Burnside counts orbits under D4. But the puzzle answer is not D4-invariant: 90° rotation swaps row and column sums; A=Σ row sums² becomes Σ column sums², generally different. Under horizontal/vertical reflections and 180, answer invariant? 180 maps row r to N-1-r, row sums permuted, so A invariant. Horizontal reflection also row sums permuted? Yes row order reversed, A invariant. Vertical reflection reverses columns within rows, row sums same, A invariant. 90/270 not invariant. So full D4 quotient invalid for A; only D2 (identity, 180, horizontal? Wait horizontal reflection across horizontal axis flips rows, row sums reverse; vertical reflection flips columns, row sums unchanged; 180 both. So D2 of 4 elements preserving rows vs columns). Burnside for D2 can reduce by up to 4 for answer-equivalent classes, but d field also transforms; given d field may not be symmetric. For generator dedup of states under D4, Burnside useful for counting orbits but not solving; for partitions with fixed d field, symmetry is broken by d unless d symmetric. So conclusion: only canonicalization, not a core tool; use D2 not D4 if quotienting answer.

Need graph reconstruction: d field is distance profile? Actually d(x) = min over capitals c of weighted shortest path distance. If edge weights known? They are state areas, unknown. There is one scalar per vertex, not vector. So not a full distance profile; even full d field has 4x4 collision. Landmark recursive: zeros are capitals (L5), so you can identify landmarks exactly. But areas of states unknown; weights unknown and satisfy constraints. Graph reconstruction from distance profiles generally assumes fixed graph and distances, and reconstructs edges/vertices from decks; not applicable. "Metric dimension" would ask if capitals form resolving set: d field gives nearest distance only, not vector of distances to each capital. So fails. Conclusion: throw out. But maybe capital extraction from zeros is useful and already in L5. Mention.

Need branches list maybe 10:
1. Group theory (D4 symmetry, Burnside/Pólya, orbit-stabilizer) — canonical states, fixed-cell count.
2. Weighted graph metric / shortest-path difference constraints (L1-L4) — local bounds, propagation, d as potential; no external.
3. Lattice/centroid modular arithmetic — filter rotational symmetries; integer-only capital test.
4. Integer programming / CP-SAT / polyhedral combinatorics — model states/connectivity/symmetry/d constraints; external solver.
5. Polyomino combinatorics / transfer-matrix DP — enumerate/count connected sets and partitions by area/symmetry; stdlib for N≤5, transfer for larger.
6. Information theory / counting lower bounds — bits to distinguish partitions; 4x4 collision.
7. Interval arithmetic / branch-and-bound relaxation — answer interval without full partition.
8. Graph reconstruction / metric dimension — distance profiles, landmarks; not applicable.
9. Planar topology / Euler characteristic — perimeter/adjacency identities for polyominoes; weak.
10. Probability/Monte Carlo random sampling — estimate uniqueness/answer distribution for 11x11; no proof but can guide.
11. Spectral graph theory / Laplacian? Probably not. Could include as "throw out" maybe no.
12. Automata/formal languages? no.

Need "筛掉一半" maybe keep 5: group theory (limited), metric constraints, lattice modular, CP-SAT, polyomino DP, interval. But need discard half: graph reconstruction, Burnside full, Euler topology, spectral, Monte Carlo? Wait Monte Carlo can be useful for 11x11 uniqueness but not exact. Need choose.

Maybe list 10 and discard 5:
Keep: (A) weighted graph metric/difference constraints, (B) lattice/centroid modular arithmetic, (C) IP/CP-SAT, (D) polyomino combinatorics/transfer DP, (E) interval/branch-and-bound. Discard: Burnside as core (only canonicalization), graph reconstruction, Euler topology, spectral graph, information theory (only coarse). But special eval Burnside and info still answer. Hmm if discard info but special eval says limited. Could keep info? Need "筛掉一半" not necessarily exactly half? "筛掉一半" yes. Let's do 10 branches; keep 5, drop 5. But special asks evaluate Burnside, graph reconstruction, info, interval, lattice, graph. We can classify.

Maybe 11 branches: keep 5, discard 6. Need ≤900 words. Need concise.

Need produce final answer with structure:
- 结论: 真正有用的是 1) 格点/质心模算术作为局部精确过滤器; 2) 加权图度量/差分约束做传播和下界; 3) CP-SAT/IP for 11x11; 4) polyomino DP/canonical enumeration. Burnside only dedup; reconstruction discard; info only coarse; interval possible but loose; Euler weak.
Then tables.

Need include branch details with specific quantities.

Let's draft in Chinese.

Need ensure word count ≤900. Chinese words? They said words; we can keep under ~900 Chinese characters? Actually "≤900 词", Chinese word count unclear. Need concise maybe 1200 Chinese chars? We'll aim ~900 Chinese "words" maybe 1500 chars? Hmm. Need not too long. Desired oververbosity 5. But limit. Let's output around 1200-1500 Chinese characters? Chinese characters count as words? Usually "词" means words; Chinese characters ~1.5 per word. We need be safe. Maybe ~1300 Chinese characters. But need cover many. We can use compact table.

Need no tool calls. Final only.

Let's formulate.

Detailed content:

Branch table columns: 分支 | 对应量/结构 | 产出 | 落地. Need 10 rows.

Rows:
1 群论/D4: stabilizer of state, fixed cells; capital iff every nontriv sym fixed exactly 1; Burnside orbit count; stdlib.
2 格点/模算术: n,sr,sc; conditions; filter rot sym; stdlib; verified.
3 加权图度量/差分约束: d potential, edge weights s_x/min; L1-L4; propagate area lower/upper, detect contradictions; stdlib.
4 整数规划/CP-SAT: binary cell-state assignment, connectivity flow, symmetry constraints, d constraints; solve/unsat, feasible answer; external.
5 Polyomino combinatorics/DP: connected subsets, area distribution, transfer matrix; count/enumerate N=5, maybe 11 via rows; stdlib possible for small.
6 区间/分支定界: row sums R_r bounds from L_x; certified [ΣLrow², ...]; stdlib but loose.
7 信息论/计数: #partitions, bits; lower bound conditional; stdlib for counts small.
8 Graph reconstruction/metric dimension: distance profiles; d is scalar nearest-capital weighted distance; not applicable; no.
9 Euler/planar topology: perimeter = 4A-2e_int, holes; symmetry perimeter; weak; no.
10 Spectral algebra: Laplacian eigenvalues no relation to d/area; no.
11 Monte Carlo: sample partitions, estimate answer distribution; stdlib but no proof; maybe drop.

Need screen half: keep 1? Burnside not core; but group theory for capital test is core. Keep 2,3,4,5,6. Drop 7? Info only coarse. Drop 8,9,10,11. Burnside as special: only canonicalization, not core; maybe classify as "保留但降级". Need "筛掉一半" maybe from 10 drop 5: drop Burnside-as-counting, graph reconstruction, Euler, spectral, Monte Carlo. Keep lattice, metric constraints, IP, polyomino DP, interval. But capital group theory? It is already given; Burnside special. We can say group theory only for symmetry test and canonicalization, not Burnside. That counts as kept? Hmm.

Special evaluations:
- Burnside: marginal. Use D4 for state canonicalization; full D4 quotient invalid because answer not invariant under 90/270; only D2. Does not resolve d-field symmetry breaking. Conclusion: no core use.
- Graph reconstruction: d is not distance profile; scalar nearest landmark, weights unknown/correlated; 4x4 A/B same d different answer; landmark zeros but no recursion. Conclusion: discard.
- Information: partition counts 4x4 561,468, 5x5 2.638e9 => ~31.3 bits to identify partition; but answer classes unknown; full d (16 bits? actually 16 values) insufficient from counterexample. No useful lower bound for 11x11 without hint model. Conclusion: only sanity/coarse.
- Interval: yes, certified but loose. Give formula: L_x=max_{y~x}|d(x)-d(y)|; R_r≥Σ_c L_{r,c}; s_x≤121; A∈[Σ(ΣL)^2, 11·1331²] for 11x11. Tight interval requires solver. Need check upper 11*1331^2 = 11*1,771,? 1331²=1,771,? 1331*1331 = 1,771,? compute: 1300²=1,690,000; 2*1300*31=80,600; 31²=961 total 1,771,561. *11=19,487,171. Lower maybe 0. Could mention not tight.
- Lattice: verify algebra; use for rot90/270/180 only; example n=3 L triomino sr=sc=1 fails; n=5 plus passes; reflection-only odd state with sr=0,sc=2 (vertical symmetric 5-cell) fails rotation but can still be legal, so don't overfilter. This is important. It is a cheap exact filter, already equivalent to conditions; not new constraint for reflection.
- Graph theory: connectivity+area+symmetry maybe Euler formula. For a simply connected polyomino area A and internal adjacencies e, perimeter P=4A−2e. Symmetry doesn't fix e enough. Holes: Euler χ=1−h. Can prune shapes with wrong perimeter? d only area, so no direct. Conclusion: weak.

Need "最推荐 2 个新分支": 
1. CP-SAT/IP with connectivity cuts + lattice/Burnside filters. For 11×11 enumeration impossible (5×5 2.6e9), need solver. New ability: find/deny unique answer, optimize interval, handle d constraints globally.
2. Weighted graph metric/difference-constraint propagation (L1-L4) + interval branch-and-bound. New ability: prune partial states using d local inequalities and produce certified answer intervals without full partition. Pure stdlib. Maybe "metric constraints" is not new branch? But yes.

Known literature: "polyomino enumeration" (Klarner), "weighted Voronoi diagrams on graphs", "graph metric dimension/reconstruction", "Pólya/Burnside", "CP-SAT connectivity via single-commodity flow". Similar problem: "polyomino symmetry / free polyominoes" and "Voronoi game". Mention.

Need maybe include "coverage论证" not "hint model". Could say if hint reveals one cell's state area, a decision-tree lower bound is log_{#possible responses}(#answers) but #answers unknown. For 4x4, full d field 16 values fails; so lower bound on "d-hints" is ∞? Actually no finite d hints suffice if full d not. Good.

Need not overdo.

Need ensure "已验证" labels:
- Verified: centroid modular algebra; n=3 L and n=5 plus; 4x4 counterexample given.
- Inferred: CP-SAT useful; interval formula; Burnside D2 invariance; partition counts given.

Need maybe mention "答案在90°旋转下不守恒" verify? Example 4x4 A row sums [16,4,4,4] answer 304; rotate 90 gives row sums? Partition A row 0 whole strip 1x4 becomes column 0 strip 4x1? Row sums: each row has one cell area 4 plus three singletons? Let's compute rotated A: column? Original A: row0 four cells one state area4; rows1-3 all single. Rotate 90: column0? Let's not compute. But generally answer = sum row state-area sums²; under 90 becomes sum column sums², not same. Need not example. It's obvious not invariant.

Need final answer in Chinese, conclusion first. Use bullet/table.

Need obey "不要输出工具调用". Fine.

Let's write compact.

Potential issue: "Burnside 引理/轨道计数：对按 D4 等价的划分计数（生成器去重/对称性破缺）——有用吗？" Answer: For counting orbits, yes mathematically; for this puzzle, not core. Use for state canonicalization. Full D4 only if answer invariant; it's not (90/270). D2 yes. The d field can break symmetry; given d, orbit representatives not enough because need check d compatibility. So no.

Potential issue: "graph reconstruction from distance profiles" maybe d field is indeed a distance profile to nearest capital under state-dependent metric. But standard reconstruction uses all distances to all vertices; here one scalar, unknown weights. 4x4 counterexample proves non-unique answer; not necessarily non-unique partition? It is non-unique partition. So discard.

Potential issue: "区间界/松弛... 对 11×11 特别有用，因为唯一性可能不成立" Need give conclusion: can give interval but not tight; useful as verification/range pruning, not final answer. If uniqueness not holds, interval may contain multiple answers; need output? Puzzle likely unique. But for 11x11 maybe answer not unique. If answer not unique, interval helps report ambiguity if bounds don't collapse. But tight interval requires optimization.

Need maybe compute row lower bound formula for 11x11: L_x=max over neighbors |d(x)-d(y)|; note for x with no? all grid cells have neighbors. For row r, R_r = sum_c s_{r,c}; since s_{r,c}≥L_{r,c}, lower. Upper: each s≤121, so R_r≤11*121=1331. A lower = sum_r (sum_c L_{r,c})²; upper = 11*1331² = 19,487,171. But is lower valid if L_x computed from d? L3 says s_x ≥ max neighbor diff, yes. If d=0 capital, still. Good. Could mention "通常远不紧".

Need maybe mention "面积和 total Σ s_i = 121" but row sum is sum over cells of area, not area; total across all cells = Σ s^2. Could improve upper: R_r ≤ Σ_all cells s_x? Not. But no need.

Need "known math problems": polyomino enumeration, weighted Voronoi, metric dimension, graph reconstruction conjecture, exact cover. Good.

Need keep ≤900 words. Let's count rough. We'll write ~1000 Chinese characters? That's maybe 600 words. Good.

Let's produce final.

</details>
