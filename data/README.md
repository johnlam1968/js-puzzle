# 数据契约 (JSON-first)

**为什么是 JSON**: 官方题面只有图片 → 像素只允许出现在**入口**一次 (ingest);
**出口和一切下游组件都只读 JSON**。求解器、生成器、测试、基准集都不许碰像素。

```
data/
  schema/
    puzzle.schema.json     # 题面 (输入) 的 JSON Schema
    truth.schema.json      # 标准答案 (ground truth) 的 JSON Schema
  puzzles/
    <id>/
      puzzle.json          # 输入: grid + hints + ingest 溯源
      truth.json           # 输出: states/sizes/capitols/d_field/row_sums/answer
```

## 约定

| 约定 | 说明 |
|---|---|
| 坐标 | `row`/`col` 从 1 开始; `states[r][c]` 用 **0-based** 行列索引 |
| `grid[r][c]` | 该格的提示数字; `null` = 空格 |
| `states` | 行优先的州标签矩阵; 标签 0..K-1 连续 |
| `state_sizes[k]` | 标签 k 的格数; **必须等于** states 中 k 的出现次数 |
| `state_capitol[k]` | 该州首都的 `[row, col]`; `null` = 该州无首都 |
| `capitols` | **有首都的**州的首都格集合; 应与 d_field 中值为 0 的格集合一致 |
| `d_field` | 每格到最近首都的最小费用 (与题面 hints 在被揭示格上必须一致) |
| `row_sums` | 逐行州面积之和 |
| `answer` | `sum(row_sums[i]^2)` |
| 校验恒等式 | `sum(row_sums) == sum(state_sizes[k]^2)` |
| `ingest` | 溯源: 怎么把外部素材变成 JSON + 谁验过 + 什么时候 |

## 现有 puzzle

| id | size | 状态 | 用途 |
|---|---|---|---|
| `official-example-5x5` | 5 | solved+verified | 官方 example; 三方独立复现 8045; 回归基准 |
| `official-11x11` | 11 | unsolved | 正式盘; 33 个数字已机器验证; **待求解** |
| `counterexample-4x4-two-answers` | 4 | solved+verified | 反例: 同一提示集 → 两个不同答案 (304/112) |

## 铁律

1. **不许从像素直接求解**。ingest 产出 JSON 之后, 求解器只认 JSON。
2. **每个 puzzle 都要有 ingest 溯源**; 人工核验过的写明核验人与日期。
3. **truth.json 必须自洽**: 标签计数 == state_sizes; Σ行和 == Σ|S|²; 每州至多一个首都; capitols == d_field 中 0 格集合。
4. **状态可以没有首都**, 但**整个划分至少要有一个首都** (否则 d 场无定义)。

## 结构性事实（4×4 实测，engine.py 产出）

- **只有奇数大小的州才能有首都**：对称恰好固定 1 格 ⇒ 其余格子两两配对 ⇒ |S| 奇。
  实测: size 1/3/5/7/9/11/13 有首都; 2/4/6/8/10/12/14/16 全部无首都。
  ⇒ **四连块(I/O/T/S/Z)永远不能当目的地**; 全偶数尺寸的划分直接出局。
- 4×4 铺法 562,308 = 全部; 其中**有首都的 559,585 (99.5%)**; 死的 2,723。
- 按尺寸多重集的"活的"铺法共 **206** 种（结构优先枚举的完整清单）。
