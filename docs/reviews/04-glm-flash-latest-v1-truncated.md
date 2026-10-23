# GLM-flash-latest — 独立评审（原题 + 设计文档）

- model: `~z-ai/glm-flash-latest` (OpenRouter)
- finish_reason: length
- usage: {"prompt_tokens": 13231, "completion_tokens": 20000, "total_tokens": 33231, "cost": 0.01198465, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.01198465, "upstream_inference_prompt_cost": 0.00198465, "upstream_inference_completions_cost": 0.01}, "completion_tokens_details": {"reasoning_tokens": 19991, "image_tokens": 0, "audio_tokens": 0}}
- content_chars: 0  reasoning_chars: 54364

---

## (no final content - reasoning trace below is the payload)

Let me work through this carefully.

Task A: verify the 5x5 example. States given:
```
0 1 1 3 3
0 1 1 2 3
0 0 2 2 3
3 0 0 0 3
3 3 3 3 3
```
Sizes: state0 = cells (0,0),(1,0),(2,0),(2,1),(3,1),(3,2),(3,3) — wait let me list. 0-based (row, col):

Row0: 0,1,1,3,3
Row1: 0,1,1,2,3
Row2: 0,0,2,2,3
Row3: 3,0,0,0,3
Row4: 3,3,3,3,3

State 0 cells: (0,0),(1,0),(2,0),(2,1),(3,1),(3,2),(3,3). That's 7 cells. Is it connected? (0,0)-(1,0)-(2,0)-(2,1)-(3,1)-(3,2)-(3,3): yes, connected. Shape: it's like a path. Symmetric? Let's check. Coordinates: (0,0),(1,0),(2,0),(2,1),(3,1),(3,2),(3,3). Hmm, is this symmetric? Capitols: state0 capitol at (2,1). Check symmetry about... Let's test reflection across the anti-diagonal? Or rotation 180 about (2.5, 1.5)? 180 about center (2.5,1.5): (r,c)→(5−r,3−c). (0,0)→(5,3) not in set. Hmm.

Try reflection across main diagonal direction: (r,c)→(c,r)? (0,0)→(0,0) ok; (1,0)→(0,1) not in set. No.

Try reflection across anti-diagonal: (r,c)→(3−c,3−r)? (0,0)→(3,3) ✓; (1,0)→(3,2) ✓; (2,0)→(3,1) ✓; (2,1)→(2,2)? (3−1, 3−2)=(2,2) — not in set. Hmm.

Try reflection across anti-diagonal line r+c=3: (r,c)→(3−c,3−r). (2,1)→(2,2)? Wait (3−1,3−2)=(2,2). Not in set. Hmm.

Try reflection across line r−c = ... main diagonal offset: (r,c)→(c+k, r−k). For (2,1) fixed: 2 = 1+k → k=1; check r−k = c: 2−1=1=c ✓. So map (r,c)→(c+1, r−1). Check: (0,0)→(1,−1) ✗. No.

Hmm, maybe the shape is symmetric under 180 rotation about (2,1)? Rotation about a cell center: (r,c)→(2r0−r, 2c0−c) with (r0,c0)=(2,1): (0,0)→(4,2) not in set.

Hmm. Let me re-examine. Maybe I mislabeled. Actually maybe the shape is symmetric under reflection across the anti-diagonal through (2,1)? Anti-diagonal r+c = 3 passes through (2,1). Reflection across r+c=3: (r,c)→(3−c, 3−r). (0,0)→(3,3) ✓ in set. (1,0)→(3,2) ✓. (2,0)→(3,1) ✓. (2,1)→(2,2)? (3−1,3−2)=(2,2). Hmm (2,2) is state 2. So not.

Wait maybe I mis-transcribed the state grid. The problem says state0 capitol at (2,1) 0-based, size 7. Let me reconsider: maybe the shape is:

(0,0),(1,0),(2,0),(2,1),(3,1),(3,2),(3,3). Hmm, this looks like a "staircase". Is it symmetric under 180° rotation about the midpoint between (2,0) and... Let's check 180 about (1.5, 1.5): (r,c)→(3−r,3−c). (0,0)→(3,3) ✓; (1,0)→(2,3)? Not in set. No.

Hmm. Maybe reflection across main diagonal r−c=... For (2,1) fixed under main-diagonal-direction reflection: (r,c)→(c+k, r−k), fixed requires r = c+k and c = r−k → k = r−c = 1. Map: (r,c)→(c+1, r−1). (0,0)→(1,−1) ✗.

Hmm, so maybe the state grid as I read it is wrong, or the capitol claim. Let me recheck the given solution: "capitols (0-based): state0 (2,1), state2 (2,3), state3 (4,4)". And the d-field has 0 at (2,1), (2,3), (4,4). Yes d field row2: 7 0 3 0 3 — zeros at (2,1) and (2,3). Row4: 25 14 13 10 0 — zero at (4,4).

So state0 must be symmetric with unique fixed cell (2,1). Let me reconsider the shape. Maybe I misread the label grid. Given:

```
0 1 1 3 3
0 1 1 2 3
0 0 2 2 3
3 0 0 0 3
3 3 3 3 3
```

State 0: positions of label 0: (0,0),(1,0),(2,0),(2,1),(3,1),(3,2),(3,3). 7 cells. Hmm.

Wait — maybe it's symmetric under reflection across the anti-diagonal r+c=3? Cells with r+c=3: (0,3),(1,2),(2,1),(3,0). (2,1) is on it. Reflect (0,0)→(3,3) ✓. (1,0)→(3,2) ✓. (2,0)→(3,1) ✓. (2,1)→(2,1) fixed ✓. (3,1)→(2,0) ✓. (3,2)→(1,0) ✓. (3,3)→(0,0) ✓. Wait I made an arithmetic error before! Reflection across r+c=3: (r,c) → (3−c, 3−r). (2,1) → (3−1, 3−2) = (2,1). Yes! Fixed! I previously wrote (2,2) — error. So state0 is symmetric under this anti-diagonal reflection, fixing only (2,1). Any other symmetry? 180 rotation about (2,1): (r,c)→(4−r,2−c): (0,0)→(4,2) not in set. So only one nontrivial symmetry, fixes exactly 1 cell → capitol (2,1). ✓ Size 7 ✓.

State 1: cells (0,1),(0,2),(1,1),(1,2) — 2x2 block, size 4. Symmetries: refH about row 0.5, refV about col 1.5, rot180. refH fixes 0 cells (axis between rows), refV fixes 0 cells, rot180 fixes 0 cells. So no capitol ✓ (each nontrivial symmetry fixes 0 cells, not exactly 1).

State 2: cells (1,3),(2,2),(2,3). Size 3. Shape: (2,2),(2,3) horizontal pair plus (1,3) above (2,3). L-tromino. Symmetric under reflection across anti-diagonal through (2,3)? r+c=5: (1,3)→(2,2)? (3−3,5−1)=(0,4)? Wait anti-diagonal reflection: (r,c)→(k−c, k−r) with axis r+c=k. Axis r+c=5: (1,3)→(5−3,5−1)=(2,2) ✓; (2,2)→(3,3)? (5−2,5−2)=(3,3) not in set. Hmm.

Try reflection across main diagonal direction r−c=const: axis r−c = −1 (through (1,2),(2,3)): map (r,c)→(c−1, r+1). (1,3)→(2,2) ✓; (2,2)→(1,3) ✓; (2,3)→(2,2)? (3−1, 2+1)=(2,3)? Wait: (c−1, r+1) with (r,c)=(2,3): (2,3). Fixed ✓. So reflection across line r−c=−1 fixes (2,3) and swaps (1,3)↔(2,2). Exactly one fixed cell. Other symmetries? refH about row 2: (1,3)→(3,3) not in set. refV about col 2.5: (2,2)↔(2,3), (1,3)→(1,2) not in set. rot180 about (1.5? ) center of the L... rot180 about (2,3)? (1,3)→(3,3) no. So only one nontrivial symmetry fixing exactly (2,3) → capitol ✓.

State 3: cells: row0: (0,3),(0,4); row1: (1,4); row2: (2,4); row3: (3,0),(3,4); row4: (4,0),(4,1),(4,2),(4,3),(4,4). Count: 2+1+1+2+5 = 11 ✓. Connected? (0,3)-(0,4)-(1,4)-(2,4)-(3,4)-(4,4)-(4,3)-(4,2)-(4,1)-(4,0); and (3,0)-(4,0) ✓. Connected. Capitol at (4,4). Symmetry: reflection across main diagonal r−c=0: (r,c)→(c,r). (0,3)→(3,0) ✓; (0,4)→(4,0) ✓; (1,4)→(4,1) ✓; (2,4)→(4,2) ✓; (3,4)→(4,3) ✓; (4,4) fixed; (0,0)? not in set. So main-diagonal reflection fixes only (4,4) ✓. Other symmetries? Probably none. Capitol (4,4) ✓.

Now the d-field. Edge weights: w(x,y) = size of state containing x if x,y in same state; else min(s_x, s_y). Actually "cost of traveling from one square to an orthogonally adjacent square in this nation is equal to the size of the state you are travelling in, or, if travelling between two states, the lesser of the two states' sizes." So stepping from cell x to adjacent y costs s(x) if same state, else min(s_x, s_y). Note: asymmetric? If x in state A (size 5) and y in state B (size 3), stepping x→y costs min(5,3)=3; stepping y→x also costs min = 3. Actually "the state you are travelling in" — when crossing, you're in both? The rule as given: cost = size of state you're travelling in, or if between two states, lesser of the two. So crossing edge cost = min(s_x, s_y) regardless of direction. Within a state, cost = s. So it's symmetric actually: within-state edge costs s; crossing edge costs min. Fine, undirected.

Multi-source Dijkstra from capitols (2,1), (2,3), (4,4).

Let me compute. Grid 5x5, states sizes: s0=7, s1=4, s2=3, s3=11.

Cell state map:
Row0: 0 1 1 3 3
Row1: 0 1 1 2 3
Row2: 0 0 2 2 3
Row3: 3 0 0 0 3
Row4: 3 3 3 3 3

Sources: (2,1) d=0 [state0], (2,3) d=0 [state2], (4,4) d=0 [state3].

Edge costs: between cells in same state: cost = state size. Between different states: min of sizes.

Let me denote d(r,c).

Start: d(2,1)=0, d(2,3)=0, d(4,4)=0.

From (2,1) [s=7]: neighbors (1,1) s1: cross min(7,4)=4 → d=4. (3,1) s0: same-state cost 7 → d=7. (2,0) s0: 7 → d=7. (2,2) s2: cross min(7,3)=3 → d=3.

From (2,3) [s=3]: neighbors (1,3) s2 same: 3 → d=3. (3,3) s0: cross min(3,7)=3 → d=3. (2,2) s2 same: 3 → d=3. (2,4) s3: cross min(3,11)=3 → d=3.

From (4,4) [s=11]: neighbors (3,4) s3 same: 11 → d=11. (4,3) s3 same: 11 → d=11.

Process smallest: d=3 at (2,2),(1,3),(3,3),(2,4).

(2,2) s2: neighbors (1,2) s1: cross min(3,4)=3 → 3+3=6. (3,2) s0: cross min(3,7)=3 → 6. (2,1): 3+3=6 > 0. (2,3): 0.

(1,3) s2: neighbors (0,3) s3: cross min(3,11)=3 → 6. (1,2) s1: min(3,4)=3 → 6. (1,4) s3: 3 → 6. (2,3): 0.

(3,3) s0: neighbors (3,2) s0 same: 7 → 3+7=10. (4,3) s3: cross min(7,11)=7 → 10. (3,4) s3: 7 → 10. (2,3): 0.

(2,4) s3: neighbors (1,4) s3 same: 11 → 14. (3,4) s3: 11 → 14. (2,3): 0.

Next d=4: (1,1) s1: neighbors (0,1) s1 same: 4 → 8. (1,0) s0: cross min(4,7)=4 → 8. (1,2) s1: 4 → 8. (2,1): 0.

Next d=6 candidates: (1,2)=6, (3,2)=6, (0,3)=6, (1,4)=6.

(1,2) s1: neighbors (0,2) s1 same: 4 → 10. (1,1): 4 → 6+4=10 (already 8, keep 8). (2,2): 0-ish. (1,3): 3.

(3,2) s0: neighbors (4,2) s3: cross min(7,11)=7 → 13. (3,1) s0 same: 7 → 13. (3,3) s0: 7 → 13 (currently 10, keep 10). (2,2): 3.

(0,3) s3: neighbors (0,2) s1: cross min(11,4)=4 → 10. (0,4) s3 same: 11 → 17. (1,3): 3.

(1,4) s3: neighbors (0,4) s3 same: 11 → 17. (2,4) s3: 11 → 17 (currently 14, keep 14). (1,3): 3.

Next d=7: (2,0)=7, (3,1)=7.

(2,0) s0: neighbors (1,0) s0 same: 7 → 14. (3,0) s3: cross min(7,11)=7 → 14. (2,1): 0.

(3,1) s0: neighbors (4,1) s3: 7 → 14. (3,0) s3: 7 → 14. (3,2): 6. (2,1): 0.

Next d=8: (0,1)=8, (1,0)=8.

(0,1) s1: neighbors (0,0) s0: cross min(4,7)=4 → 12. (0,2) s1: 4 → 12 (currently 10, keep 10). (1,1): 4.

(1,0) s0: neighbors (0,0) s0: 7 → 15. (2,0): 7. (1,1): 4.

Next d=10: (3,3)=10, (0,2)=10.

(3,3) s0: neighbors (4,3) s3: min(7,11)=7 → 17 (currently 11, keep 11). (3,4) s3: 7 → 17 (currently 10, keep 10). (3,2): 6. (2,3): 0.

(0,2) s1: neighbors (0,3) s3: min(4,11)=4 → 14 (currently 6, keep 6). (0,1): 4. (1,2): 3.

Next d=11: (3,4)=10? wait (3,4) was set to 10 earlier from (3,3): 3+7=10. Yes d(3,4)=10. And (4,3)=11, (4,4)=0.

Wait, (4,3): from (4,4) same-state cost 11 → 11. Also from (3,3) via cross min(7,11)=7: 10+7=17. So d(4,3)=11.

(3,4) s3: neighbors (2,4) s3 same: 11 → 10+11=21 (currently 14, keep 14). (4,4): 0. (3,3): 10.

(4,3) s3: neighbors (4,2) s3 same: 11 → 22. (3,3) s0: min(11,7)=7 → 18. (4,4): 0.

Next d=12: (0,0)=12.

(0,0) s0: neighbors (0,1): 8. (1,0): 8.

Next d=13: (4,2)=13.

(4,2) s3: neighbors (4,1) s3 same: 11 → 24. (3,2) s0: min(11,7)=7 → 20 (currently 13, keep 13). (4,3): 11.

Next d=14: (1,0)=14, (3,0)=14, (4,1)=14.

(1,0) s0: neighbors (0,0) s0: 7 → 21 (currently 12, keep 12). (1,1): 8. (2,0): 7.

(3,0) s3: neighbors (2,0) s0: min(11,7)=7 → 21 (currently 14, keep 14). (4,0) s3 same: 11 → 25. (3,1): 7.

(4,1) s3: neighbors (4,0) s3: 11 → 25. (4,2): 13. (3,1) s0: min(11,7)=7 → 21 (currently 14, keep 14).

Next d=14: (2,4)=14.

(2,4) s3: neighbors (1,4) s3: 11 → 25 (currently 6, keep 6). (3,4): 10. (2,3): 0.

Next d=17: (0,4)=17.

(0,4) s3: neighbors (0,3): 6. (1,4): 6.

Next d=21? Let's collect remaining: (4,0)=25, (4,1)=14 done, (0,4)=17 done. What's left unprocessed: (4,0)=25.

Final d-field:
Row0: (0,0)=12, (0,1)=8, (0,2)=10, (0,3)=6, (0,4)=17
Row1: (1,0)=8, (1,1)=4, (1,2)=6, (1,3)=3, (1,4)=6
Row2: (2,0)=7, (2,1)=0, (2,2)=3, (2,3)=0, (2,4)=3
Row3: (3,0)=14, (3,1)=7, (3,2)=6, (3,3)=10, (3,4)=10
Row4: (4,0)=25, (4,1)=14, (4,2)=13, (4,3)=11, (4,4)=0

Compare with official:
```
12  8 10  6 17
 8  4  6  3  6
 7  0  3  0  3
14  7  6  3 10
25 14 13 10  0
```
Row3 official: 14 7 6 3 10. My (3,3)=10 but official says 3! Let me recheck. (3,3) is state 0 (label 0 in row3: "3 0 0 0 3" → (3,0)=3,(3,1)=0,(3,2)=0,(3,3)=0,(3,4)=3). So (3,3) is state 0, size 7. Neighbor (2,3) is state 2 capitol with d=0. Cross edge min(7,3)=3. So d(3,3) ≤ 0+3 = 3. I made an error: from (2,3), neighbor (3,3) cross cost min(3,7)=3 → d=3. I did compute that: "(3,3) s0: cross min(3,7)=3 → d=3." Yes I set d(3,3)=3 initially! Then later from (3,3) I wrote "(3,3) s0: neighbors (3,2) s0 same: 7 → 3+7=10" — I mistakenly treated (3,3) as having d=10. Let me redo: d(3,3)=3.

Redo from (3,3) with d=3: neighbors (3,2) s0 same-state 7 → 10. (4,3) s3 cross min(7,11)=7 → 10. (3,4) s3 cross 7 → 10. (2,3): 0.

So (3,2): from (2,2) cross 3 → 6; from (3,3) same-state 7 → 10. Keep 6. ✓ official 6.

(4,3): from (4,4) 11; from (3,3) 3+7=10. So d(4,3)=10? Official says 10. ✓. Wait official row4: 25 14 13 10 0. Yes (4,3)=10.

(3,4): from (3,3) 3+7=10; from (2,4) 3+11=14; from (4,4) same 11. So d(3,4)=10 ✓ official 10.

Now redo (4,3) expansion with d=10: neighbors (4,2) s3 same 11 → 21; (3,3): 3; (4,4): 0. So (4,2) stays 13 (from (3,2) cross 7: 6+7=13). ✓.

(3,4) with d=10: neighbors (2,4) s3 same 11 → 21 (keep 14? wait (2,4)=3 from capitol (2,3) cross min(3,11)=3). Hmm (2,4)=3. From (2,4): neighbors (1,4) s3 same 11 → 14; (3,4) s3 same 11 → 14. So (3,4) ≤ 14. Also 10 from (3,3). Keep 10 ✓.

(1,4): from (1,3) cross 3 → 6 ✓ official 6.

(0,4): from (0,3) same-state 11 → 6+11=17; from (1,4) same 11 → 6+11=17. ✓ 17.

(4,0): from (3,0) same-state 11 → 14+11=25; from (4,1) same 11 → 14+11=25. ✓ 25.

(4,1): from (3,1) cross min(11,7)=7 → 7+7=14; from (4,0) 25; from (4,2) 13+11=24. ✓ 14.

(3,0): from (2,0) cross min(7,11)=7 → 7+7=14; from (3,1) cross 7 → 14; from (4,0) same 11 → 25. ✓ 14.

(1,0): from (2,0) same 7 → 14; from (1,1) cross min(4,7)=4 → 8; from (0,0) same 7 → 12+7=19. ✓ 8.

(0,0): from (1,0) same 7 → 15; from (0,1) cross 4 → 12. ✓ 12.

(0,1): from (1,1) same 4 → 8; from (0,2) same 4 → 14. ✓ 8.

(0,2): from (1,2) same 4 → 10; from (0,3) cross min(4,11)=4 → 10; from (0,1) 12. ✓ 10.

(0,3): from (1,3) cross 3 → 6; from (0,4) same 11 → 28; from (0,2) cross 4 → 14. ✓ 6.

(1,2): from (1,1) same 4 → 8; from (2,2) cross 3 → 6; from (1,3) cross 3 → 6. ✓ 6.

(1,1): from (2,1) cross 4 → 4 ✓.

(2,2): from (2,3) same 3 → 3; from (2,1) cross 3 → 3. ✓ 3.

(2,0): from (2,1) same 7 → 7; from (3,0) cross 7 → 21; from (1,0) same 7 → 15. ✓ 7.

(3,1): from (2,1) same 7 → 7; from (3,2) same 7 → 13; from (3,0) cross 7 → 21; from (4,1) cross 7 → 21. ✓ 7.

(3,2): from (2,2) cross 3 → 6; from (3,1) same 7 → 14; from (3,3) same 7 → 10; from (4,2) cross 7 → 20. ✓ 6.

Great, full match:

Row0: 12 8 10 6 17 ✓
Row1: 8 4 6 3 6 ✓
Row2: 7 0 3 0 3 ✓
Row3: 14 7 6 3 10 ✓
Row4: 25 14 13 10 0 ✓

All 10 printed numbers match (the example says "confirm the 10 printed numbers" — the input grid has 10 numbers: 12,17,8,6,3,7,6,10,25,0; these are hints, and they match d values at those cells: (0,0)=12 ✓, (0,4)=17 ✓, (1,0)=8 ✓, (1,2)=6 ✓, (1,3)=3 ✓, (3,1)=7 ✓, (3,2)=6 ✓, (3,4)=10 ✓, (4,0)=25 ✓, (4,4)=0 ✓). 

Row sums of state sizes: row0: states 0,1,1,3,3 → 7+4+4+11+11 = 37 ✓. Row1: 0,1,1,2,3 → 7+4+4+3+11 = 29 ✓. Row2: 0,0,2,2,3 → 7+7+3+3+11 = 31 ✓. Row3: 3,0,0,0,3 → 11+7+7+7+11 = 43 ✓. Row4: all 3 → 55 ✓.

Answer: 37²=1369, 29²=841, 31²=961, 43²=1849, 55²=3025. Sum: 1369+841=2210; +961=3171; +1849=5020; +3025=8045 ✓.

PASS.

Task B: critique. Let me go through the document and find issues.

Key things to check:

1. §1.1 integer conditions. The symmetry candidates: for a polyomino S with n cells, sums sr=Σr, sc=Σc. For a symmetry fixing the centroid and preserving the grid... Let me verify the conditions.

refH (horizontal reflection, i.e., across a horizontal line): (r,c)→(a−r, c) where a = 2*r̄ = 2*sr/n. Need a integer: (2 sr) % n == 0. ✓. But wait — the reflection axis must map the cell grid to itself. A horizontal reflection mapping the set of cells to itself: axis at half-integer or integer row. a = 2sr/n must be an integer; also the axis could be at integer or half-integer row — a−r must be a valid row, and a integer suffices for the map to send integer rows to integer rows. Actually if axis is at half-integer row (between rows), a is odd integer... a = 2*row_axis. If axis at row k (integer), a=2k even; if between rows k+0.5, a=2k+1 odd. Either way a integer. Condition (2sr)%n==0 correct. But also need the map to be a symmetry of S — the condition is necessary, and then you check whether the map preserves S. Fine.

refD1 (main diagonal direction): (r,c)→(c+k, r−k)? Reflection across line r−c = k... hmm. Reflection across line r = c + k maps (r,c) → (c+k, r−k). For this to preserve the grid it's fine for any integer k. Centroid fixed: r̄ = c̄ + k → k = r̄ − c̄ = (sr−sc)/n. Need (sr−sc)%n==0. ✓ matches doc.

refD2 (anti-diagonal): reflection across r+c = k: (r,c)→(k−c, k−r), k = r̄+c̄ = (sr+sc)/n, need (sr+sc)%n==0 ✓.

rot180: (r,c)→(2r̄−r, 2c̄−c) = (a−r, b−c) with a=2sr/n, b=2sc/n. Doc says rot180 = refH 且 refV — composition of horizontal and vertical reflections is rot180, and if both reflections exist rot180 exists. But conversely rot180 can exist without refH/refV individually! E.g., a shape with 180° rotational symmetry but no reflection symmetry. The doc's table says "rot180 | refH 且 refV | (a−r, b−c)". That's wrong as a characterization: rot180 symmetry requires (2sr)%n==0 and (2sc)%n==0 (i.e., centroid at half-integer or integer lattice point), but does NOT require refH and refV to be symmetries of S. As a *candidate filter* the condition "(2sr)%n==0 and (2sc)%n==0" is necessary and sufficient for the map (a−r,b−c) to be grid-preserving; then you check if it preserves S. But writing "rot180 = refH 且 refV" conflates "the candidate map is admissible" with "the reflections are symmetries". Actually wait — as a filter on candidates: if refH is a symmetry of S then a=2sr/n is integer; if refV is a symmetry then b integer. But rot180 can be a symmetry when neither reflection is. So using "refH 且 refV" as the test for rot180 would miss rot180-symmetric states with no reflections. That's a real bug — a completeness bug in the candidate generation. Hmm, but maybe the doc means: the integer condition for rot180's map is the conjunction of the refH and refV integer conditions. The table column header is "整数条件" (integer condition). So "refH 且 refV" means the integer conditions of refH and refV both hold. That's correct as integer conditions: (2sr)%n==0 AND (2sc)%n==0. OK so it's the integer conditions, not the symmetry conditions. Ambiguous but defensible. Similarly rot90/270: refD1 且 refD2 integer conditions: (sr−sc)%n==0 and (sr+sc)%n==0 → sr≡sc≡0 mod n (for odd n; for even n, sr≡sc mod n and sr≡−sc mod n → 2sr≡0, 2sc≡0 mod n... anyway). Fine.

But there's a subtlety: rot90 about a cell center vs about a corner? A 90° rotation preserving the square grid must be about a lattice point (corner) or the center of a cell? Rotation by 90° about a point maps the grid to itself iff the point is a lattice point (cell corner) — rotation about a cell center by 90° maps cells to cells shifted... Actually rotating the integer lattice by 90° about a cell center (half-integer, half-integer): (r,c) → (a−c, c... let's see: rotation about (x0,y0) by 90°: (r,c)→(x0 − (c−c0), c0 + (r−r0)). For this to map ℤ² to ℤ², need x0−c+c0 integer and c0+r−r0 integer for all integers → x0+c0 integer and c0−r0 integer. Cell center: x0=r0+0.5, c0=c0+0.5... take (r0,c0) cell center = (i+0.5, j+0.5): x0+c0 = i+j+1 integer ✓; c0−r0 = j−i integer ✓. So rotation about a cell center does map ℤ² to ℤ²! E.g., rotate about center of cell (0,0) = (0.5,0.5): cell (0,0) maps to itself. Cell (1,0) (center (1.5,0.5)) → (0.5−(0.5−0.5), 0.5+(1.5−0.5)) = (0.5, 1.5) = cell (0,1). Yes! So 90° rotation about a cell center maps the grid to itself. Hmm wait, but does it map cells to cells? The rotation maps the cell [0,1]² to... rotating square [0,1]² about its center by 90° gives itself. Cell (1,0)=[1,2]×[0,1] rotates to [0,1]×[1,2] = cell (0,1). Yes. So 90° rotations about cell centers are grid-preserving. Also about lattice points (corners). So the doc's rot90 formula (c+k1, k2−r) — that's the composition refD1∘refD2 or similar, which is a rotation about the intersection of the two diagonal axes. Intersection of r−c=k1 and r+c=k2 is at ((k1+k2)/2, (k2−k1)/2) — could be integer or half-integer point. Fine, the composition formula covers it. OK.

Actually wait: is the doc's claim "旋转只固定中心" (rotations fix only the center) consistent? A 90° rotation fixes exactly one point (its center), which is either a cell center (fixed cell = that cell) or a lattice corner (fixed point at a corner, fixes 0 cells... hmm, a 90° rotation about a lattice point (corner of 4 cells) fixes no cell interior? The corner point is on the boundary of 4 cells; "fixed square" — the problem says "leaves exactly 1 of its squares fixed". A square is fixed if the rotation maps it to itself. A 90° rotation about a corner maps none of the cells to themselves (each cell adjacent to the corner maps to a different cell). Actually the cell whose corner is the center: rotating cell [0,1]² about corner (0,0) by 90° gives [−1,0]×[0,1] or [0,1]×[−1,0] — different cell. So fixes 0 cells. So a state with only rot90 symmetry about a corner has no capitol (the rotation doesn't fix exactly 1 square). And rot180 about a corner fixes 0 cells; rot180 about an edge midpoint fixes 0 cells; rot180 about a cell center fixes 1 cell. Reflections: axis through cell centers (horizontal/vertical through a row/column of cells) fixes those cells; axis between rows fixes 0 cells; diagonal axis r−c=k passes through cells whose... cells on the diagonal r−c=k: cell (r,c) with r−c=k is mapped to itself? Reflection (r,c)→(c+k, r−k): cell (r,c) maps to (c+k, r−k); this equals (r,c) iff r=c+k. So cells on the axis are fixed. The axis r−c=k passes through the centers of cells with r−c=k? Cell centers (r+0.5, c+0.5): (r+0.5)−(c+0.5)=r−c=k. Yes, the diagonal line passes through centers of cells with r−c=k, and those cells are individually fixed (the reflection maps the square to itself since the diagonal of the square is the axis). ✓.

So capitol analysis: for a state to have a capitol, every nontrivial symmetry in its symmetry group must fix exactly one cell. The doc's theorem that they all fix the same cell — plausible.

Hmm, one more check on the doc's claim in §1.2: "若 G 中每个非平凡元素都恰好固定 1 格，则那个格是首都" — fine.

2. §1.4 L1 proof: "取最近首都 c* 与 x→c* 最优路径的首步 v1，则 d(v1) ≤ dist(v1,c*) = d(x)−w(x,v1)". Hmm: d(v1) ≤ dist(v1, c*) since d is min over capitols. dist(v1,c*) = d(x) − w(x,v1)? The optimal path from x to c* has total cost d(x); first edge costs w(x,v1); remaining path from v1 costs d(x)−w(x,v1), so dist(v1,c*) ≤ d(x)−w(x,v1). And triangle inequality: d(x) ≤ d(v1) + w(x,v1) → d(v1) ≥ d(x) − w(x,v1). Combined: d(x)−w ≤ dist(v1,c*)... wait we need d(v1) = d(x)−w. We have d(v1) ≥ d(x)−w (triangle). And d(v1) ≤ dist(v1,c*) ≤ d(x)−w. So equality. ✓. But wait — triangle inequality: is d a valid thing for triangle inequality? d(x) ≤ d(v1) + w(v1,x)? d(x) is min cost to any capitol; going x→v1 then from v1 to best capitol from v1 costs w + d(v1) ≥ d(x)? Yes since d(x) is the min. ✓. L1 fine. Actually careful: L1 says exists neighbor y with d(y) = d(x) − w(x,y). The proof gives it. ✓.

3. L2: |d(x)−d(y)| ≤ min(s_x,s_y) for adjacent x,y: d(x) ≤ d(y) + w(y,x) = d(y) + min(s_x,s_y). ✓.

4. L3: s_x ≥ max over neighbors |d(x)−d(y)|: from L2, |d(x)−d(y)| ≤ min(s_x,s_y) ≤ s_x. ✓. The doc's note that the unrestricted version fails — their counterexample: 1×3 row, S0={(0,0)} size1 capitol, S1={(0,1),(0,2)} size 2. d: (0,0)=0; (0,1): cross min(1,2)=1 → 1; (0,2): from (0,1) same-state cost 2 → 3. x=(0,0) s=1, y=(0,2) d=3, non-adjacent: 1 ≥ 3 false. ✓ counterexample valid. But wait — is S1={(0,1),(0,2)} a legal state? 1×2 domino: symmetries refH (about row axis through centers) fixes 2 cells, refV about column 1.5 fixes 0 cells, rot180 fixes 0. refH fixes 2 cells ≠ 1, so no capitol — but it's still a legal state (has nontrivial symmetry). ✓. And d(0,2)=3: path (0,2)→(0,1) costs 2 (same state), (0,1)→(0,0) costs 1. Total 3. Or (0,2)→(0,1) cost 2 then... yes 3. ✓.

5. "d=2 不可能" being false: their counterexample "x 在 2 格骨牌内、邻接 7 格州首都 ⇒ d=2". x in a 2-cell domino, adjacent to a capitol of a 7-cell state: cross cost min(2,7)=2 → d(x)=2. ✓ plausible. Fine.

6. §1.5 counterexample: d-field all-1 row 0 and 0 elsewhere... Let me check: A: row 0 = one 1×4 (size 4, no capitol) + 12 singleton states. d field: row 0 cells: each singleton is its own capitol → d=0 for singletons?? Wait the d field given is [[1,1,1,1],[0,...],[0...],[0...]] — row 0 has d=1, rows 1-3 d=0. Hmm, but if rows 1–3 are all singletons, each is a capitol with d=0. Row 0 cells: 1×4 bar, no capitol. d of row-0 cells: they're adjacent to row-1 singletons (capitols, d=0), cross cost min(4,1)=1 → d=1. ✓. But wait — the 1×4 bar: is it a legal state? 1×4 has reflection along its long axis fixing 4 cells → has nontrivial symmetry, legal, no capitol. ✓. Answer A: row sums of state sizes: row0: 4 cells × size 4 = 16; rows 1–3: 4×1=4 each. Answer = 256+16+16+16 = 304 ✓. B: two 1×2 bars: row sum 8; answer = 64+48=112 ✓. Same d-field? In B, row-0 cells in dominoes: adjacent to row-1 singletons, cross cost min(2,1)=1 → d=1 ✓. Same d field. But wait — do the hints match? This counterexample is about "d field doesn't determine answer" — both partitions produce identical d fields but different answers. Valid. But hold on: in A, the 1×4 bar cells: d=1 each. In B, domino cells: d=1 each. Yes identical. ✓. Good counterexample. Though note: this requires the d-field to be fully known; with hints it's still a valid point that answer-level uniqueness is the right criterion.

Hmm wait, actually there's a subtlety: in A, are the 12 singletons each a state with capitol? Yes, 1×1 state's capitol is itself. d=0 ✓.

7. §1.6: answer invariant only under D2. Claim: rotating the official example 90° gives 8029 ≠ 8045. Hmm — is that right? If you rotate the entire partition by 90°, the states map to symmetric states, capitols map to capitols, and distances... The edge weights are preserved (sizes preserved, adjacency preserved). The d-field should be exactly the rotated d-field. Row sums, though, change because rows change! Rotating 90° permutes cells; the row sums of the rotated grid differ. So the answer (sum of squares of row sums) is NOT invariant under 90° rotation in general. Under 180° rotation, rows map to rows (reversed), so the multiset of row sums is preserved → answer invariant. Under horizontal/vertical reflection, rows map to rows → invariant. Under 90° rotation, rows map to columns → row sums become column sums, generally different. So the claim is correct and actually trivially explainable: the answer functional is defined via rows, so it's invariant under exactly the symmetries preserving the row structure (D2 generated by refH, refV — which includes rot180). ✓. Good.

8. §1.7: pruning lower bound must use min possible edge weight; using true weights kills correct solutions. Hmm — wait. Is that right? If we're searching over partitions consistent with hints, and we compute a lower bound on d(x) using... The issue: during search, the partition is partially determined; the true edge weights depend on the final partition. If you compute d_lb using assumed weights that are not lower bounds on the true weights, you could prune valid solutions. Using per-step lower bound 1 (Manhattan distance) is safe. But actually could you use a better bound? The cost of a step is at least 1 (min state size 1). Also, hmm, each step costs at least... a step into a state of size ≥1 costs ≥1. But the "步数引理" in §1.11 says every step except the last costs ≥2 because a cost-1 step means entering a 1-cell state which is a capitol. Wait: cost of a step = size of state you're travelling in. If you're travelling within a 1-cell state... a step from x to y both in the same 1-cell state is impossible (no self-loop). A step from x (state A) to y (state B) with min(|A|,|B|)=1 means one of the states is a singleton, which is a capitol. If x is the singleton, x is a capitol, d(x)=0, path ends. If y is the singleton capitol, the path should end there (d(y)=0 ≤ anything). Hmm, but the path could pass through a singleton capitol without stopping? No — if the path reaches a capitol, it stops (d is min cost to ANY capitol). Actually the path to the nearest capitol: if it passes through another capitol earlier, then that capitol is nearer, contradiction with c* being the nearest achieving the min... well c* is the nearest; passing through capitol c' means cost so far ≥ d... hmm, cost to reach c' along the path is a valid cost to a capitol, so ≥ d(x). If the total equals d(x) and c' is passed before c*, then dist(x,c') ≤ partial cost < total = d(x) = dist(x,c*) ≤ dist(x,c'), contradiction unless equal and c'=c*. Fine. So on an optimal path, no interior capitol, so no step has cost 1 except possibly... a step of cost 1 requires min(s)=1, i.e., an endpoint is a singleton = capitol. Interior steps can't have cost 1. Last step: arrives at capitol c*; the step into c* costs min(s_prev, s*) or s* if same state. Could be 1 if s*=1 (capitol is singleton) — then the path is x adjacent to singleton capitol, k=1 step, cost 1 = 2(1−1)+1 = 1 ✓. So v ≥ 2(k−1)+1 where k = number of steps. Hmm wait: is it "every step except the last costs ≥ 2"? Steps 1..k−1 are interior, cost ≥2. Step k costs ≥1. So v ≥ 2(k−1)+1 ✓. Then Manhattan(x,c*) ≤ k ≤ ⌊(v+1)/2⌋... wait k ≤ (v−1)/2 + 1 = (v+1)/2, so k ≤ ⌊(v+1)/2⌋ for... v ≥ 2k−1 → k ≤ (v+1)/2 → k ≤ ⌊(v+1)/2⌋ ✓. And Manh ≤ k steps? Manhattan distance ≤ number of steps k ✓. So Manh(x,c*) ≤ ⌊(v+1)/2⌋. ✓ Lemma seems right. Hmm, but wait: interior step cost ≥ 2 — cost of a step is the size of the state you're travelling in. Minimum state size is 1. Cost 1 happens only if... travelling within a state of size 1: impossible. Crossing between states with min size 1: one endpoint is a singleton state, which is a capitol. If x (start of step) is the singleton capitol — but x interior means d(x)>0, and a capitol has d=0, so x isn't a capitol. If y (end of step) is the singleton capitol — then the path reaches a capitol at step y; if y is interior (not the final c*), then we reached a capitol earlier, contradiction as argued. Hmm, unless y is a capitol with d(y) > 0? No, capitols have d=0. So yes, interior steps cost ≥2. ✓. Actually one more subtlety: could an interior step cost 1 by travelling *within* a 1-cell state? No self-steps. OK lemma holds.

Hmm wait, actually there's another subtlety: what about a step of cost 1 where the state you're "travelling in" has size 1 — the rule says cost = size of the state you are travelling in, or if travelling between two states, the lesser. If x and y are in the same state of size 1 — impossible. If different states, min(s_x,s_y)=1 → one is singleton → capitol. ✓.

But actually hold on — is it true that a 1×1 state's capitol is itself? The state has no nontrivial symmetry... wait, the trivial group: the identity. "every nontrivial rotation or reflection that takes the state to itself" — a 1×1 state has 4 nontrivial symmetries (D4), each fixing the 1 cell. So yes, capitol = itself. ✓. And the doc says a state must have nontrivial self-symmetry to be a state at all — a 1×1 has D4 ✓.

9. §1.8: "首都在州内 ⇒ 相邻步长 = d". Claim: if y is a capitol adjacent to x, then w(x,y) = d(x). Proof: d(x) ≤ w(x,y) + d(y) = w(x,y) + 0 → d(x) ≤ w. Also "w ≤ d(x)（离开 x 至少付 w）": any path from x starts with an edge of cost ≥ ... hmm, "离开 x 至少付 w"? That's wrong in general: leaving x can cost less than w(x,y) if another neighbor is in a smaller state. Wait: the first step of any path from x costs either s_x (if within x's state) or min(s_x, s_z). Hmm, w(x,y) = s_x if same state, or min(s_x, s_y). Is every edge out of x cost ≥ w(x,y)? If y ∈ same state as x: w = s_x; any edge from x costs ≥ s_x? Within-state edges cost s_x; cross edges cost min(s_x, s_z) ≤ s_x. Oops — cross edges can be cheaper! So "w ≤ d(x)" via "every path's first step ≥ w" is false when y is in x's state but a neighbor z is in a smaller state.

Hmm wait, let me redo. Claim: w(x,y) = d(x) when y is a capitol adjacent to x.

Case 1: y in same state as x. Then w(x,y) = s_x. d(x) ≤ w(x,y) (path x→y then done, y capitol d=0): d(x) ≤ s_x. Need s_x ≤ d(x): any path from x: first step costs... if first step stays in state (cost s_x) or crosses (cost min(s_x, s_z) ≤ s_x). So first step could be < s_x! E.g., x in a 7-cell state, y capitol of same state adjacent, but z neighbor in a 1-cell state: first step costs 1, reaching a capitol → d(x) = 1 < 7 = w(x,y). So the claim w(x,y)=d(x) is FALSE in this case!

Hmm wait, but then the doc's M2 macro and the corollaries break. Let me re-read the doc's claim: "若 y 是首都且与 x 相邻：w(x,y) = d(x)。证明：走 y 至少付 w；而 d(x) 是最少花费 ⇒ d(x) ≤ w；又 w ≤ d(x)（离开 x 至少付 w）⇒ 等号。"

"离开 x 至少付 w" — leaving x costs at least w. That's the dubious step. If y is in a *different* state from x: w = min(s_x, s_y). Is every departure from x cost ≥ min(s_x, s_y)? Departure costs: within-state s_x, or cross min(s_x, s_z). Is min(s_x,s_z) ≥ min(s_x,s_y)? Not necessarily — s_z could be smaller than s_y. Hmm. E.g., x in state size 5, y capitol of state size 3 adjacent (w=3), z in state size 1 adjacent (w=1). Then d(x) = 1 (step to z, a capitol). w(x,y)=3 ≠ 1. So the claim is false!

Wait, but maybe I'm misreading the cost rule. "The cost of traveling from one square to an orthogonally adjacent square in this nation is equal to the size of the state you are travelling in, or, if travelling between two states, the lesser of the two states' sizes." Hmm — "the state you are travelling in": when you move from x to y within state A, you're travelling in A, cost |A|. When moving between states... cost = min. Hmm, alternatively the intended reading: cost = size of the state containing the square you're *in* (i.e., departing)? "travelling in" — ambiguous. The worked example: let's check with the alternative reading. In the example, (2,1) capitol of state0 (size 7), neighbor (1,1) in state1 (size 4): d(1,1)=4. Under "departing state size" reading: cost from (1,1) to (2,1) = s(1,1) = 4 → d(1,1) = 4 ✓. Under min reading: min(4,7)=4 ✓. Both give 4. Check (3,3) state0, neighbor (2,3) capitol of state2 (size 3): d(3,3)=3. Departing reading: cost = s(3,3)=7 → d(3,3) ≤ 7, but also via other routes... official d(3,3)=3. Under departing reading: path (3,3)→(2,3) costs 7 → 7. Alternative: (3,3)→(3,2)? same state cost 7... hmm all departures from state-0 cells cost 7 under departing reading until you cross... wait under departing reading, crossing from (3,3)[s7] to (2,3)[s3] costs 7 (the state you're travelling in = state you're leaving? or the state you're in when travelling — you're in both). Hmm. Under departing reading d(3,3): neighbors (2,3) capitol: cost 7 → 7. (3,2),(3,1) same state: 7 each. (3,4) state3: cost 7 → then from (3,4)... this gives d(3,3) ≥ ... let's see if 3 is achievable: no, every departure from a state-0 cell costs 7. So d(3,3) ≥ 7 under departing reading, but official says 3. So the departing reading is wrong; the correct reading is: within-state edges cost s; cross edges cost min(s_x,s_y). That's what I used and it reproduced the official field exactly. ✓ So the rule is: cross edges cost min.

OK so back to §1.8. Under the correct rule, is "y capitol adjacent to x ⇒ w(x,y) = d(x)" true? Counterexample as above: x in 5-cell state, adjacent to capitol y of 3-cell state and capitol z of 1-cell state. w(x,y) = min(5,3) = 3, but d(x) = 1 (via z). So claim false in general. BUT — maybe the doc intends this as a pruning heuristic under additional conditions? It says "强推论，本文的宏动作基础" and derives M2: "x 与首都 c 相邻 ⇒ w(x,c)=d(x)；d(x) 偶 ⇒ x 所在州面积 = d(x)". Let me think about when it holds. Hmm, actually wait. Let me reconsider. d(x) ≤ w(x,y) always (since y is a capitol, going directly gives cost w). For the reverse, we need that no cheaper first step exists. The doc asserts "w ≤ d(x)" because "离开 x 至少付 w". This holds only if w(x,y) is the minimum cost departure from x. When is that guaranteed? If y is in the same state as x: w = s_x, and departures cost ≥ ... within-state: s_x; cross: min(s_x, s_z) which can be < s_x. So not guaranteed either. Hmm, so M2 is broken in general?

Wait, wait. Let me reconsider. Hmm, actually maybe there's a subtlety: cross edge cost min(s_x, s_z) — if s_z < s_x, cost s_z. So departure cost can be as low as min over neighbors' states and own state. So "离开 x 至少付 w(x,y)" is false unless w(x,y) = min over all neighbors.

Hmm, but hold on — maybe the doc's M2 is still correct in the specific usage? Let's test M2's corollary against the official 5×5 example: (1,1) d=4 adjacent to capitol (2,1). w((1,1),(2,1)) = min(4,7) = 4 = d(1,1) ✓ here. (3,3) d=3 adjacent to capitol (2,3): w = min(7,3) = 3 = d ✓. (3,1) d=7 adjacent to capitol (2,1): w = min(7,7)=7 (same state) = d ✓. (2,2) d=3 adjacent to capitol (2,3)? (2,2)-(2,3) adjacent, same state 2, w=3=d ✓. (2,4) d=3 adjacent (2,3): same state, w=3 ✓. (3,4) d=10 adjacent (4,4) capitol: w = min(11,11)=11 ≠ 10! So M2 fails right in the official example: (3,4) is adjacent to capitol (4,4) (state 3, same state, w=11) but d(3,4)=10 (via (3,3) cross cost 7). So the claim "w(x,c)=d(x) for adjacent capitol c" is FALSE, with a counterexample in the official worked example itself!

Wait, (3,4) and (4,4): both state 3, adjacent, w = 11. d(3,4) = 10 (path (3,4)→(3,3) cost min(11,7)=7, then (3,3)→(2,3) cost 3; total 10). And (4,4) is a capitol adjacent to (3,4). So w=11 ≠ d=10. M2 is refuted by the official example. Unless the doc means something weaker... "若 y 是首都且与 x 相邻：w(x,y) = d(x)" — plainly false. Actually hmm, wait: maybe they intend d(x) ≤ w and the reverse direction only when... no, they claim equality. And the corollary "d(x) 偶 ⇒ x 所在州面积 = d(x) ⇒ 死州": from w(x,c)=d(x): if c in different state, w = min(s_x, s_c); capitol state s_c is odd (T-A); if d(x) even... hmm. Let me see the intended logic: w(x,c) = d(x). If same state: s_x = d(x); s_x odd (capitol state odd) → d(x) odd. If different states: min(s_x, s_c) = d(x); s_c odd. If d(x) even: then min = d(x) even ≠ s_c odd... min(s_x,s_c)=d(x); if s_c were the min, d(x)=s_c odd, contradiction; so s_x = d(x), even, and x's state has size d(x) and... "死州" (dead state) — hmm why dead? If s_x = d(x) even, x's state has even size → no capitol (T-A) → dead. OK. And "d(x) 奇 ⇒ x 所在州面积 = d(x)，或首都所在州面积 = d(x)". So M2's corollaries rely on the false equality.

But actually, maybe there's a weaker true statement: d(x) ≤ w(x,c) and... hmm. Let me think about what IS true. If c is a capitol adjacent to x: d(x) ≤ w(x,c). Also, hmm, is there a lower bound d(x) ≥ something? Not obviously.

Actually wait, maybe I should double check the direction of the cost rule once more, because M2 might be intended under a different reading where cost of a step = size of the state you're *entering*? Let's test: entering reading: step x→y costs s_y if same state... no wait. "cost of traveling from one square to an adjacent square = size of the state you are travelling in" — when you travel from x to y, if both in state A, you travel in A: cost |A|. If x∈A, y∈B, A≠B: you're travelling between two states: cost min(|A|,|B|). That's the reading I verified. Under "entering" reading: cost = s_y always? Check (3,3): step to (2,3): s=3 → d ≤ 3 ✓ consistent. Step (1,1)→(2,1): s(2,1)=7 → cost 7, d(1,1) would be... (1,1)→(1,2)? s(1,2)=4 → then (1,2)→(2,2) s=3 → (2,2)→(2,3) s=3: total 4+3+3=10 > 4. Hmm (1,1)→(2,1) cost 7; other paths: (1,1)→(0,1) cost 4... to reach a capitol: capitols (2,1),(2,3),(4,4). (1,1)→(2,1): 7. (1,1)→(1,2)→(2,2)→(2,3): 4+3+3=10. (1,1)→(1,0)→(2,0)→... (1,0) s0 size7: cost 7; (2,0) cost 7... worse. So entering reading gives d(1,1)=7 ≠ 4. So entering reading wrong. My reading confirmed. Good.

So finding: §1.8/M2 is false, counterexample (3,4)-(4,4) in the official 5×5. Actually wait, let me double-check (3,4) is adjacent to (4,4): yes, vertically. Both state 3. w = 11. d(3,4) = 10. So M2 false. Hmm, but hold on — maybe the doc's M2 is meant as: "if y is a capitol and x adjacent, and additionally w(x,y) is the cheapest departure"... The doc presents it as unconditional. It's a genuine error. Severity: high, since M2 is one of three macro-moves and is used to derive constraints on the 11×11 (e.g., "(11,9)=77 与 (11,10)=61 相邻，Δ=16 ⇒ 两州面积 ≥ 16" — that one uses L2/L3 which is fine; but M2-based deductions like "d(x) 偶 ⇒ 死州" are unsound).

Hmm wait, actually let me re-derive: is there a corrected version? If c is a capitol adjacent to x, then d(x) ≤ w(x,c). Also, the first step of the optimal path from x: if the optimal path has length 1, then d(x) = w(x,c') for some adjacent capitol c'. So: d(x) = min over neighbors z of w(x,z) where z capitol... no: d(x) = min over paths; a 1-step path exists iff some adjacent cell is a capitol, and then d(x) = min over adjacent capitols c' of w(x,c'). So the correct statement: if y is an adjacent capitol, then d(x) ≤ w(x,y), with equality iff y is the cheapest adjacent capitol (and 1-step is optimal). The doc's equality claim needs the extra hypothesis that w(x,y) ≤ every other departure cost from x. So M2 should be: d(x) ≤ w(x,c), and if additionally w(x,c) ≤ min over all neighbors z of (z capitol ? w(x,z) : ∞)... this is getting complicated; the point for the review: M2 as stated is false, counterexample given.

Hmm, wait, actually let me reconsider — maybe the doc intends "y 是首都且与 x 相邻" plus implicitly that d(x) is realized by a 1-step path... no. I'll flag it.

Actually hold on, let me reconsider whether even "d(x) ≤ w(x,c)" combined with parity gives anything. The corollary "d(x) even ⇒ x's state size = d(x) (dead state)": under the false equality. With only d(x) ≤ w(x,c): if same state, s_x = w ≥ d(x), no equality forced. So no.

But hmm, wait: is there a true related statement? If x is adjacent to capitol c and w(x,c) = min over all edges incident to x, then d(x) = w(x,c). Because d(x) ≥ (min first-step cost) = w(x,c)? Hmm: any path from x has first step cost ≥ min edge cost out of x = m. And d(x) ≤ w(x,c) = m if c achieves the min. So d(x) = m... wait need d(x) ≥ m: d(x) = cost of optimal path ≥ first step cost ≥ m ✓. And d(x) ≤ w(x,c)=m ✓. So equality. So corrected M2: if adjacent capitol c attains the minimum edge cost out of x, then d(x) = w(x,c). That's the fix.

10. §1.9 T-A: only odd-size states can have capitols. A symmetry fixing exactly 1 cell: the group acts; nontrivial elements each fix exactly 1 cell (the same cell). The state's cells are partitioned into orbits under the group; the fixed cell is a singleton orbit; all other orbits have size = |orbit| ≥ 2. Orbits under a group containing a reflection have size 1 or 2; under rotation 180, size 1 or 2; rot90: orbits size 1 or 4. Hmm: if the group is generated by a 90° rotation, orbits have size 4 (non-fixed) → |S| = 1 + 4k, odd ✓. If group = {id, σ} with σ an involution (reflection or 180°): orbits size 1 or 2, exactly one fixed cell (since each nontrivial element fixes exactly 1 cell and they all fix the same cell) → |S| = 1 + 2k odd ✓. If group is D2 (id, refH, refV, rot180) with all three fixing the same single cell: orbits... under full D2 action, orbit of a non-fixed cell: could have size 2 or 4. Hmm: if orbit size 2, then the cell is fixed by some nontrivial element — but nontrivial elements fix only the capitol. So all non-capitol cells have orbit size 4 → |S| = 1 + 4k odd ✓. D4 similar: orbits size ≤ 8, non-fixed cells have orbit size > 1... could a non-capitol cell have orbit size 2 under D4? Orbit size 2 means stabilizer size 4 — stabilizer contains nontrivial elements fixing the cell — but only the capitol is fixed by any nontrivial element. Wait, "each nontrivial element fixes exactly 1 cell" and all fix the same cell (the theorem). So any non-capitol cell is fixed by no nontrivial element → orbit size = |G|. |G| ∈ {2,4,8} → |S| = 1 + |G|k odd ✓. T-A holds. ✓.

T-B: "k = N²−1 永远不合法" — for an N×N puzzle where the answer... hmm, what's k here? Context: "k = N²−1 永远不合法；k = N² 只在全单格时可能". I think k = number of capitols? "无首都的州不可能是 1 格 ⇒ 每块死州 ≥2 格 ⇒ N²−k ≥ 2". Hmm: N²−k ≥ 2 where k = number of capitols? If every state has at most 1 capitol, #capitols ≤ #states. N² − k... hmm, N²−k ≥ 2 means... Actually I think k here is the number of capitols and the claim is total cells minus capitols ≥ 2? That would say: at most N²−2 capitols, i.e., you can't have N²−1 capitols. If you have N²−1 capitols, then... hmm, each capitol is in a distinct state (each state has ≤1 capitol). N²−1 capitols → ≥ N²−1 states → the remaining 1 cell: if it's a singleton state, it's a capitol too → N² capitols; if it joins another state... but all other states are singletons (since N²−1 capitols need N²−1 cells at least, each capitol in a distinct state, states are disjoint...). Hmm: N² cells, N²−1 capitols. Each capitol occupies ≥1 cell, distinct states. So ≥ N²−1 cells are in capitol-states. The last cell: either its own singleton state (→ it's a capitol → N² capitols, contradiction with exactly N²−1) or it belongs to one of the capitol-states. Can a state have 2 cells and a capitol? Sure (e.g., domino has no capitol; but L-tromino has one). Hmm, so N²−1 capitols: e.g., N=2: 3 capitols? States: one L-tromino... no wait 2×2: states could be a 3-cell L (capitol? L-tromino symmetries: one reflection fixes 1 cell → capitol ✓... actually L-tromino has exactly one reflection symmetry fixing the corner cell) + 1 singleton (capitol). That's 2 capitols in 4 cells = N²−2. For N²−1 = 3 capitols in 4 cells: need 3 states each with capitol: sizes must be odd... 3 states, sizes summing to 4, each odd: 1+1+2 — 2 is even, no capitol. So impossible ✓ for N=2. General: N²−1 capitols → N²−1 states with capitols (each odd size ≥1) + 1 extra cell. The extra cell either forms its own state (singleton → capitol → N² capitols, contradiction) or joins a state making it even... if it joins a state of odd size s, new size s+1 even → that state loses its capitol → only N²−2 capitols. Contradiction. So k=N²−1 impossible ✓. T-B seems right. And "k=N² 只在全单格时可能": all states singletons → all capitols. Could there be N² capitols with a non-singleton state? Each capitol needs a distinct state of odd size ≥ 1; N² capitols need ≥ N² cells with... total cells N², so all states size 1. ✓.

Hmm wait, actually is T-B about the number of capitols or something else? "k = N²−1 永远不合法" — in context of §1.11: "且 <= 121，k=120 不可能 (T-B)" — yes k = number of capitols, 121 = 11². OK.

11. §1.10, §2 constants: can't verify (UNVERIFIED), but plausible.

12. §1.11 hitting set: 31 demands (33 hints minus 2 revealed capitols... wait, the 11×11 has two 0-valued cells: (6,8) and (11,6) 1-based — let me check the grid: row 6 has "0" at position 8: row6: "11 . 11 . . . . . . 9 ." — position 8 is "."? Let me index the grid carefully.

Grid (1-based, rows 1–11, cols 1–11):
Row1: . 8 4 . . 11 . . . 5 .
Row2: . . . . . . . 11 . . .
Row3: . . 7 . . 1 . . . . 14
Row4: 28 . . 51 . . 1 . 6 . .
Row5: . 22 . . . . . . 4 . 1
Row6: . . . 15 . 10 . 0 . . .
Row7: 11 . 11 . . . . . . 9 .
Row8: . . 17 . 14 . . . 10 . 13
Row9: 30 . . . . 6 . . . 45 .
Row10: . . . 10 . . . . . . .
Row11: . 26 . . . 0 . . . 77 61

Zeros: (6,8) and (11,6). ✓ two revealed capitols. 33 numbers total: count: row1: 4 (8,4,11,5); row2: 1 (11); row3: 3 (7,1,14); row4: 4 (28,51,1,6); row5: 3 (22,4,1); row6: 3 (15,10,0); row7: 3 (11,11,9); row8: 4 (17,14,10,13); row9: 3 (30,6,45); row10: 1 (10); row11: 4 (26,0,77,61). Total: 4+1+3+4+3+3+3+4+3+1+4 = 33 ✓.

So 31 non-zero hints, 2 revealed capitols. Hitting set: each hint (x, v) demands a capitol within Manh distance ⌊(v+1)/2⌋. Candidate pool 88 = 121 − 33 = 88 (hint cells can't be capitols except the d=0 ones). ✓ consistent. "最小额外首都数 = 5" → ≥7 capitols total. Can't verify the exact numbers 1,592 / 17.6s (UNVERIFIED) but the framework is sound. One issue: the hitting-set lower bound uses only the ball constraint; but also each hint's ball must contain a capitol *of a neighboring-or-closer state*... actually just a capitol within distance ⌊(v+1)/2⌋ — fine as necessary condition. But note: the ball constraint derivation assumed the optimal path doesn't pass through other capitols and interior steps cost ≥2 — verified above. One more subtlety: the last step could cost more than 1, making the bound still valid (v ≥ 2(k−1)+1 uses last step ≥1). ✓.

Hmm, wait: one more subtlety in the step lemma: interior steps cost ≥ 2 — but what about a step of cost 2 within... fine, ≥2. But actually could an interior step cost exactly 2 in a state of size 2? Yes (domino, no capitol). Fine.

Also: the hitting set gives a LOWER bound on capitols; but for the search, enumerating minimal hitting sets (1,592 of them) as candidate capitol positions — danger: the true capitol set need not be a *minimal* hitting set! The true set of capitols is *a* hitting set, but it may contain more than the minimum number, and restricting to the 1,592 minimal ones could exclude the true solution. The doc says "先解击中集、再对每个候选首都集跑轨道生长" — if they only try minimal hitting sets, they may miss solutions. They do say "首都数 ≥ 7" as a bound, which is valid. But the pipeline "对每个候选首都集跑 AODFS" must consider supersets of minimal hitting sets, or at least all hitting sets of size = true count. This is a completeness gap. Actually more precisely: the true capitol set H is a hitting set; if |H| > min, H ⊇ some minimal hitting set H' (every hitting set contains a minimal one). So if you enumerate minimal hitting sets and then allow *adding* capitols during growth, you're fine. But if you fix exactly the minimal set as THE capitols, you lose. The doc's step 1-2 is ambiguous; flag it.

Also: the candidate pool "88 格" excludes hint cells with d>0 — justified: a cell with d(x)>0 is not a capitol (L5: d=0 ⟺ capitol). ✓. But wait, L5 requires "全图至少一个首都" ✓.

Also the hitting-set demand for hint value v: ball radius ⌊(v+1)/2⌋ in Manhattan distance. For v=1: radius 1 — the capitol is adjacent or the cell itself... but the cell itself can't be a capitol (d>0), so adjacent. ✓ consistent with M3.

13. §2.2 frontier DP: answer bitmap 19,487,171 bits — answer upper bound N⁷ = 11⁷ = 19,487,171 ✓ (11⁷ = 19487171 ✓). 2.44 MB ✓ (19487171/8 ≈ 2.44MB). Bell(11) = 678,570 ✓ (Bell numbers: B10=115975, B11=678570 ✓). 678570 × 2.44MB ≈ 1.65 TB ✓. But the argument "前沿状态数 ≥ Bell(11)" — Bell(11) is the number of set partitions of 11 elements; the frontier has ≤11 cells, each with a label; the number of distinct frontier labelings ≤ Bell(11)+... actually distinct labelings of 11 frontier cells where labels are set partitions: at most Bell(11) = 678570 distinct patterns (plus shape masks etc.). So the state count is ≥... hmm, they claim ≥ Bell(11) as a lower bound on states — actually the number of distinct frontier partitions is at most Bell(11), and could be fewer reachable. As a lower bound on DP state count it's shaky (it's an upper bound on the frontier-labeling component). But combined with shape masks it's clearly huge. Minor overstatement. Also the answer bitmap: do you need the full bitmap? For uniqueness you need to detect whether two different answers exist — you could store a hash + one exemplar, or count answers... but counting distinct answers requires set membership. Could store the set of achievable answers more cleverly? The set of achievable answer values could be large. Alternatively, since we just need cardinality of answer set, maybe store min/max + count via... no, distinct values needed. OK, their infeasibility conclusion is probably right in spirit; the Bell(11) lower bound is the weak step. Also 2.44MB × 678570 assumes all combinations reachable — overestimate. But also they need shape masks which multiply further. I'd call it "directionally right, proof sloppy".

14. §2.3: 5×5 legal states 22,317, partitions 2.6e9, ×19.7 per level extrapolation to 1.3e12 for 11×11. The extrapolation ×19.7 per level from 5×5 to 11×11: 19.7^6 ≈ 19.7^6. 19.7² ≈ 388, 19.7³ ≈ 7645, 19.7⁶ ≈ 5.8e7. 22,317 × 5.8e7 ≈ 1.3e12 ✓ arithmetic consistent. But extrapolating a growth ratio linearly per level is hand-wavy (growth rate itself grows). UNVERIFIED but plausible order.

15. §3.4 completeness argument: "任取合法划分 P，当前锚点所在州 S 取其一非平凡对称 σ；S 是 σ-不变且连通 ⇒ 存在 S 的 BFS 序，每步加入的轨道 ⊆ S ⇒ 生长必能到达 S". Issue: the growth rule as stated adds orbits cl_σ(x) only when σ(x) ∈ S ∪ {x}... The claim is that any σ-invariant connected S can be built by adding σ-orbits one at a time keeping intermediate sets... hmm, the intermediate sets need not be connected or σ-closed during growth? The rule maintains "σ-闭包与边界 F". The completeness claim: there's an ordering of orbits such that each partial union is connected? Not obvious! Counterexample: a σ-symmetric state where... hmm, actually for the DFS to reach S, each intermediate set must be a union of orbits of σ (since we add whole orbits) and connected (rule 5 requires connectivity to close the state, but intermediate growth sets maybe need not be connected until closure?). The doc's growth maintains boundary F = cells adjacent to S; if intermediate sets are disconnected, the boundary still exists. Hmm, the completeness argument is sketchy: "存在 S 的 BFS 序，每步加入的轨道 ⊆ S" — a BFS order of cells, but we add orbits. Need: an ordering of the orbits such that adding them one by one keeps... what invariant? If the invariant is just "current set ⊆ S and σ-closed", then trivially any order of orbits works, and eventually we reach S. But then the "可取 S 为州" branch requires connectivity — only checked at closure. But the pruning during growth (readings) might rely on connectivity? Also the boundary F definition requires S connected? F = neighbors of S — fine even if disconnected. Hmm, but there's a subtler issue: the growth must also be able to *stop* — the state S is σ-closed by construction. But is every σ-symmetric connected state reachable? Yes: order the orbits arbitrarily, add them one at a time; final set = S which is connected. Intermediate sets may be disconnected but if the algorithm doesn't require intermediate connectivity, fine. But rule 3's frontier F and rule 4's condition "σ(x) ∈ S ∪ {x}" — hmm, "加 x 的前提是 σ(x) ∈ S ∪ {x}"?? That's odd: to add x's orbit you need σ(x) already in S or x itself fixed? That would prevent adding an orbit pair (x, σ(x)) fresh — you could never add a new pair where both x and σ(x) are outside S! Wait: "规则：加 x 的前提是 σ(x) ∈ S ∪ {x}；若 x 不是 σ 的固定格，必须同时加入其镜像". Hmm, that's contradictory: if x is not fixed, σ(x) ∉ {x}, so we need σ(x) ∈ S — but then adding "the orbit" means adding x only (its mirror already in S). So orbits are added one cell at a time?? No wait — "必须同时加入其镜像" contradicts "前提 σ(x) ∈ S". I think the intended rule: pick x in frontier; add the full orbit {x, σ(x), ...}; the condition "σ(x) ∈ S ∪ {x}" is about... hmm, maybe it's a typo and means the orbit-closure condition. This is internally inconsistent as written — flag as unclear/contradictory. Actually maybe the intended semantics: you can add x together with its mirror; the condition ensures σ-closure is maintained. As written it's contradictory ("前提是 σ(x) ∈ S ∪ {x}" but then "必须同时加入其镜像" — if σ(x) ∈ S already, there's no mirror to add). So the growth rule spec is garbled. Flag.

Also completeness: the anchor is "最左上未分配格" of the *remaining* region — but the state containing that cell in P might have any symmetry; the DFS branches over all σ and centers q. For each σ