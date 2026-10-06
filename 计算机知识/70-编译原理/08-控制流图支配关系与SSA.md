---
type: lesson
domain: computer-science
stage: 2
status: ready
difficulty: 进阶
estimated_minutes: 110
topics:
  - 控制流图
  - 支配关系
  - 支配树
  - 支配边界
  - SSA
  - Phi
  - Critical Edge
tags:
  - computer-science/compiler
  - computer-science/control-flow-graph
  - computer-science/ssa
  - learning/lesson
---

# 控制流图、支配关系与 SSA

## 本课目标

学完后，你应该能够：

- 从带标签和 terminator 的基本块构造控制流图（CFG），并写出可执行的结构 verifier 清单；
- 精确定义 dominance、strict dominance、immediate dominator、dominator tree 与 dominance frontier；
- 在菱形分支和循环上手算支配集合、直接支配者和支配边界；
- 依据定义点的迭代支配边界放置 `phi`，再沿支配树完成 SSA 重命名；
- 正确检查“定义支配使用”，包括 `phi` 操作数发生在入边上的特殊规则；
- 识别 critical edge，解释为什么以及怎样拆边，而不把“拆边”误当成改变程序分支语义。

适用场景：实现优化器、检查 IR 改写、理解常量传播/死代码删除、为寄存器分配建立 use-def 关系，以及阅读工业编译器中的 CFG/SSA verifier 报错。

> [!important] 本课边界
> 本页只讨论函数内、显式基本块边的经典 CFG 与 SSA。异常、协程、不可重入区域、内存 SSA 和跨过程控制流会扩展这里的模型。数据流分析的格与不动点统一框架留到下一课。所有算法先以“CFG 在分析期间不变”为前提。

## 1. 直觉：CFG 回答“可能走到哪里”，SSA 回答“这个值来自哪次定义”

普通三地址码允许同一个名字多次赋值：

```text
x = 0
if c:
    x = 1
else:
    x = 2
y = x + 1
```

只看最后一行无法知道 `x` 来自哪个赋值；答案取决于控制流。CFG 把基本块作为顶点、terminator 可能选择的转移作为有向边。SSA（Static Single Assignment）则要求每个 SSA 值只有一个静态定义，并在多条路径合流时用 `phi` 明确选择对应入边上的值。

```text
控制问题：entry 到 use 可能经过哪些块？       → CFG
必经问题：某定义是否出现在所有到 use 的路径？ → dominance
合流问题：不同路径上的定义在哪里会面？       → dominance frontier
值来源：本次 use 精确引用哪个定义？           → SSA use-def
```

图表示、DFS 和环的基础见 [[计算机知识/50-数据结构与算法/07-图的表示BFS-DFS与拓扑排序|图的表示、BFS、DFS 与拓扑排序]]；建立和维护表示不变量的方法见 [[计算机知识/50-数据结构与算法/15-如何选择数据结构与建立不变量|如何选择数据结构与建立不变量]]。

支配关系中的“每一条路径”是全称量词，找出一条绕行路径就足以构成反例；对应的推理规则见 [[数学/10-数学语言与基础/03-集合映射命题与合法推理|集合、映射、命题与合法推理]]。CFG terminator 最终可能 lowering 为机器分支、返回或异常路径，但静态 CFG 边是“按当前模型可能转移”的关系，不是一次真实 CPU trace；机器执行层见 [[计算机知识/30-计算机系统/06-指令系统汇编与程序执行|指令系统、汇编与程序执行]]。

## 2. CFG 的精确定义

一个函数内 CFG 可记为有向图：

$$
G=(V,E,entry),
$$

其中：

- `V` 是基本块集合；
- `E` 包含每个 terminator 可能转移到的函数内后继边；
- `entry ∈ V` 是函数入口；
- `succ(b) = {s | (b,s) ∈ E}`；
- `pred(b) = {p | (p,b) ∈ E}`。

`return` 块可没有函数内后继。一个函数也可能有多个返回块；若算法需要唯一 `exit`，可以增加一个**合成出口**并让所有返回块指向它，但要明确这只是分析视图，不应重复执行返回副作用。

### 可达与不可达

若存在从 `entry` 到 `b` 的有向路径，则 `b` 可达。很多 dominance 定义和算法只对可达块工作：不可达块上“每条 entry 路径都经过谁”会出现空路径的逻辑歧义。

编译器可以选择：

1. verifier 直接拒绝不可达块；
2. 结构上允许，但在 dominance/SSA 前移除或隔离；
3. 为每个不可达连通部分另建伪入口。

三者都可实现，关键是不能一边把不可达块当普通可达块，一边套用只对可达图成立的定理。

## 3. CFG verifier：先验证图，再运行图算法

一个基础函数级 verifier 可以按以下顺序工作：

```text
VERIFY_CFG(function):
    require exactly one designated entry block
    require every block has a unique stable identity

    for each block b:
        require b has exactly one terminator
        require terminator(b) is the last instruction
        require terminator successor count matches its opcode
        for each successor s of terminator(b):
            require s belongs to function

    recomputed_pred = reverse all successor edges
    require cached predecessor lists equal recomputed_pred

    for each block b:
        require phi nodes, if any, form a prefix of b
        require ordinary operand/result types satisfy opcode contracts
        for each phi in b:
            require exactly one incoming value per predecessor edge
            require incoming labels/edge identities match pred(b)
            require incoming value types equal phi result type

    apply the function's explicit unreachable-block policy
```

若 IR 允许同一前驱通过两个不同 switch case 形成**平行边**，`phi` 输入必须按边身份而非仅按前驱块名计数；另一种选择是在规范化阶段合并平行边。verifier 必须与此政策一致。

还应检查：

- 每个 SSA 结果只定义一次；
- 块内普通使用出现在定义之后；
- 跨块使用满足定义支配使用；
- terminator 引用的条件和值类型正确；
- 删除或替换边后，前驱表与 `phi` 输入同步更新。

> [!warning] verifier 的证明边界
> verifier 通过说明 CFG/SSA 属于结构上合法的 IR 集合，不说明某次重写保持了源程序语义。把 `then` 和 `else` 的目标对调仍可能结构合法，却执行相反行为。

## 4. Dominance：所有入口路径上的“必经点”

对可达块 `d` 和 `n`：

> 若从 `entry` 到 `n` 的**每一条路径**都包含 `d`，则称 `d` 支配 `n`，写作 `d dom n`。

由定义可得每个块都支配自身。若 `d dom n` 且 `d ≠ n`，则 `d` **严格支配** `n`。

对非入口可达块 `n`，它的 **immediate dominator** `idom(n)` 是严格支配 `n` 且最靠近 `n` 的唯一块：其他严格支配者也支配 `idom(n)`。以 `idom` 为父边就得到 **dominator tree（支配树）**。

支配树是 CFG 派生出的树，不等于 CFG 本身：CFG 可以有合流和环；支配树为每个可达非入口块选出唯一父节点。

### 集合方程

经典迭代定义为：

$$
Dom(entry)=\{entry\},
$$

$$
Dom(n)=\{n\}\cup\bigcap_{p\in pred(n)}Dom(p),\qquad n\ne entry.
$$

初始化时可令非入口可达块的 `Dom(n)=V_reachable`，反复取交集直到不再变化。这是一个 must 性质：只有出现在**所有**前驱路径上的块才保留。

## 5. 手算例 1：菱形 CFG 的支配集合与树

CFG：

```text
        B0_entry
        /       \
     B1_left   B2_right
        \       /
          B3_join
             |
          B4_exit
```

边为 `B0→B1, B0→B2, B1→B3, B2→B3, B3→B4`。迭代稳定后：

| 块 | `Dom` 集合 | `idom` |
| --- | --- | --- |
| `B0` | `{B0}` | 无 |
| `B1` | `{B0,B1}` | `B0` |
| `B2` | `{B0,B2}` | `B0` |
| `B3` | `{B0,B3}` | `B0` |
| `B4` | `{B0,B3,B4}` | `B3` |

为什么 `B1` 不支配 `B3`？因为存在路径 `B0→B2→B3` 不经过 `B1`。为什么 `B0` 支配所有块？因为所有入口路径都从 `B0` 开始。

支配树为：

```text
B0
├── B1
├── B2
└── B3
    └── B4
```

### 正确性不变量

集合迭代每一步都按“本块 + 所有前驱共同支配者”更新。若一个块 `d` 不在某个前驱的支配集合中，就存在一条到该前驱而不经过 `d` 的路径，再接上这条入边便得到一条到当前块而不经过 `d` 的路径，所以 `d` 不能保留。反过来，若 `d` 支配每个前驱，则每条进入当前块的路径都经过某个前驱且已经过 `d`。

## 6. Dominance frontier：支配停止保持“严格”的边界

块 `x` 的 dominance frontier 定义为：

$$
DF(x)=\{y\mid \exists p\in pred(y),\ x\ dom\ p\ \land\ x\ \text{不严格支配}\ y\}.
$$

直觉：`x` 支配了通向 `y` 的至少一条入边来源，但到了 `y`，另一路可能绕开 `x`，因此 `x` 的支配性在合流处停止。

在上面的菱形中：

```text
DF(B1) = {B3}
DF(B2) = {B3}
DF(B0) = ∅
DF(B3) = ∅
```

`B1` 支配它自身这个 `B3` 的前驱，但不支配 `B3`；`B2` 同理。这正是两条分支定义需要在 `B3` 合流的地方。

### 循环中的自身边界

考虑 `Entry→Header`、`Header→Body`、`Body→Header`、`Header→Exit`。`Header` 支配 `Body`，又不**严格**支配自身，所以 `Header ∈ DF(Header)`；`Body` 也把 `Header` 放进自己的支配边界。这个“自己可出现在自己的 frontier”不是矛盾，而是循环头需要合并“第一次进入”和“上一轮回边”值的信号。

## 7. SSA：每个值一个静态定义

SSA 形式要求：

1. 每个 SSA 名字恰好有一个定义；
2. 每个普通使用都被其定义支配；
3. 多前驱块中的 `phi` 依据**实际到达的入边**选择对应值。

把菱形分支改写为：

```text
B0_entry:
    branch c, B1_left, B2_right

B1_left:
    x1 = const 1
    goto B3_join

B2_right:
    x2 = const 2
    goto B3_join

B3_join:
    x3 = phi [B1_left: x1], [B2_right: x2]
    y1 = add x3, 1
    goto B4_exit

B4_exit:
    return y1
```

`phi` 不是在运行时同时执行两个 copy。它表示：若控制沿 `B1→B3` 到达，`x3=x1`；若沿 `B2→B3` 到达，`x3=x2`。许多后端最终会在入边上插入并行 copy，再消除 `phi`。

### Phi 放置：迭代支配边界

对原程序变量 `x`，收集定义块集合 `DefBlocks(x)`。经典最小 SSA 放置过程是：

```text
worklist = DefBlocks(x)
has_phi = ∅

while worklist not empty:
    take block d
    for each y in DF(d):
        if y not in has_phi:
            insert empty phi for x at start of y
            add y to has_phi
            if y not in DefBlocks(x):
                add y to worklist
```

之所以要迭代：新 `phi` 自身也是一个新定义，它的值可能继续流到更远的合流点。若使用 pruned SSA，可再结合活跃性，只在 `x` 进入该块时仍可能被使用的地方放 `phi`；这会减少无用 `phi`，但依赖下一课的数据流结果。

## 8. 重命名：沿支配树维护每个变量的定义栈

放好空 `phi` 后，按支配树深度优先遍历：

```text
RENAME(block b):
    remember each variable stack's current height

    for each phi result in b:
        create fresh SSA name and push it on that variable's stack

    scan ordinary instructions in order:
        replace every variable use with top of its stack
        for every variable definition:
            create fresh SSA name and push it

    for each CFG successor s of b:
        for each phi of variable x in s:
            set the incoming operand for edge b -> s to top(stack[x])

    for each child c of b in the dominator tree:
        RENAME(c)

    restore all stacks to their remembered heights
```

核心不变量：进入 `RENAME(b)` 时，`stack[x]` 顶部是支配 `b`、且在当前支配树路径上最近的 `x` 定义；离开时恢复栈，避免一个兄弟支配子树中的定义泄漏到另一个兄弟。

若栈为空而出现使用，说明源程序存在“可能未定义即使用”，或构造器遗漏了入口默认定义/诊断。不能随便生成一个常量掩盖错误。

## 9. “定义支配使用”的精确检查

### 普通指令

若定义与使用在不同块，定义块必须支配使用块。若在同一块，定义还必须出现在使用之前；块级 dominance 本身不能说明块内顺序。

### Phi 操作数

`phi` 的结果定义在目标块开头，但每个 incoming operand 被视为在对应的**前驱边末端**使用：

```text
v3 = phi [P: v1], [Q: v2]
```

因此检查 `P: v1` 时，应要求 `v1` 的定义支配边 `P→当前块` 的来源位置；若 `v1` 在 `P` 内定义，它必须位于 `P` 的 terminator 之前。不能要求 `v1` 的定义支配 `phi` 所在块，因为另一路 `Q` 本来就可绕过该定义。

这个规则解释了为什么上例中的 `x1` 合法：`B1` 不支配 `B3`，但 `x1` 只在 `B1→B3` 入边上被使用。

### Phi 结果

`phi` 结果在块首定义，支配同块中其后的普通指令，也可支配该块所支配的后继区域。多个 `phi` 概念上并行，不应让同块某个 `phi` 依赖另一个 `phi` 的“文本先后顺序”来表达顺序计算。

## 10. Critical edge：不能唯一归属源块或目标块的边

CFG 边 `u→v` 是 **critical edge**，当且仅当：

```text
out_degree(u) > 1  且  in_degree(v) > 1
```

源块有多个后继，所以把只属于 `u→v` 的指令无条件放在 `u` 末尾会影响其他后继；目标块有多个前驱，所以把它无条件放在 `v` 开头会影响其他入边。

例如：

```text
U ─────────→ W
└────→ V ──→ W

边：U→V、U→W、V→W
```

边 `U→W` 为 critical edge。拆边时增加只承载该边的新块 `S`：

```text
原来：U -> W
现在：U -> S -> W
```

同时更新：

- `U` terminator 的目标从 `W` 改为 `S`；
- `W` 的 predecessor 从该条 `U` 入边改为 `S`；
- `W` 中每个 `phi` 的对应 incoming label/edge identity 改为 `S`，值本身保持；
- 新块 `S` 以 `goto W` 终结，并继承适当的 source provenance。

拆边不应改变“何时选择这条分支”，只是在选中后增加一个确定执行的块。它常用于放置 `phi` 消解 copy、边上 instrumentation 或只对某条路径执行的转换。

> [!warning] 不要把任意边都叫 critical
> “有分支”或“进入合流块”各自都不够，必须同时满足源多后继、目标多前驱。无条件拆所有边虽可能保持语义，却会膨胀 CFG、影响布局和分析成本。

## 11. 复杂度前提

设可达 CFG 有 `V` 个块、`E` 条边、`N` 条指令：

- 构造前驱/后继表和基础 verifier 通常为 `O(N + V + E)`；
- 用显式支配集合反复取交集的教学算法容易达到较高多项式成本，位集合可改善常数，但不适合超大函数；
- Lengauer–Tarjan 一类算法可在接近线性的时间内求 dominator tree，但实现与证明更复杂；课程不把“算法名字”当作无需验证的黑盒；
- 已有 dominator tree 时，经典 SSA 重命名对指令、phi 输入和 CFG 边做常数次工作，通常为 `O(N + E)`；
- phi 放置成本依赖 dominance frontier 的总大小，最坏情况下 frontier 关系本身就可能很大；
- 拆一条边是局部常数规模的结构改写，但若每次都重算全函数 dominance，批量 pass 的总成本会放大。

这些结论假定块和值以紧凑 ID 或均摊常数时间映射访问。若 predecessor 是每次查询时全图扫描，许多“线性”步骤会退化。复杂度模型的前提见 [[计算机知识/50-数据结构与算法/01-复杂度模型渐近分析与摊还分析|复杂度模型、渐近分析与摊还分析]]。

## 12. 失败边界与常见误解

| 误解或失败 | 后果 | 修正 |
| --- | --- | --- |
| 只改 successor、不改 predecessor/phi | 图的双向索引和 SSA 输入不一致 | 通过单一边改写 API 原子更新并立即 verify |
| 对不可达块直接套 dominance | 结果依赖未说明的空路径约定 | 先实施明确的不可达政策 |
| 把 `phi` 当普通 eager 函数调用 | 错以为所有输入都在块首求值 | 把 incoming use 绑定到对应入边 |
| 只检查定义块支配使用块 | 漏掉同块“先使用后定义” | 额外检查块内顺序 |
| 插入一次 frontier 就停止 | 循环或多级合流处可能漏 phi | 把新 phi 定义块继续加入工作列表 |
| 每个合流块给每个变量都放 phi | 结构可合法但产生大量死 phi | 用定义点，必要时再用活跃性剪枝 |
| 拆 critical edge 忘记 source/phi | 调试映射或值来源错误 | 作为结构化操作同步更新所有引用 |
| verifier 通过就认为优化正确 | 对调分支、替换值仍可结构合法 | 另做语义保持证明与差分验证 |

异常边会让“调用一定落到下一块”的假设失效；协程和不可重入区域也可能需要特殊控制流节点。引入这些机制前应扩展 CFG 语义和 verifier，而不是让分析器静默忽略边。

## 练习

1. 对本页菱形 CFG 从初始化开始迭代 `Dom` 集合，写出每轮变化；再根据最终集合画 dominator tree。
2. 给 `B1` 与 `B2` 各放一个 `x` 定义，手算 `DF(B1)`、`DF(B2)`，插入 `phi` 并完成 SSA 重命名。
3. 为 `Entry→Header`、`Header→Body/Exit`、`Body→Header` 的循环计算支配集合与 frontier；给循环变量 `i` 放置入口值和回边值的 `phi`。
4. 故意构造三个非法 SSA：同名结果定义两次、普通使用不被定义支配、`phi` 漏一条前驱边。指出 verifier 应报哪条不变量。
5. 构造一条 `out_degree(U)>1` 且 `in_degree(V)>1` 的 critical edge，拆成 `U→S→V`，逐项更新 successor、predecessor 与 phi 输入。
6. 解释为什么“`d` 支配 `n`”不能用“我找到了一条经过 `d` 的路径”证明；给出一条绕开 `d` 的反例路径即可推翻什么命题？

## 成功标准

- 你能从 terminator 重建 `succ/pred`，并用 verifier 检出块尾、边和 phi 输入不一致；
- 你能用“所有 entry 路径”而非“某条路径”判断 dominance，并手算 `idom` 与 dominator tree；
- 你能用 dominance frontier 找到菱形合流和循环头上的 phi 候选点；
- 你能沿支配树用定义栈完成重命名，并解释兄弟子树之间为何要恢复栈；
- 你能分别检查普通 use、同块 use 和 phi incoming use 的定义支配规则；
- 你能按两个度数条件识别 critical edge，并在拆边后保持 CFG/phi 一致；
- 你能明确区分 CFG/SSA 结构合法与程序语义等价。

---

**上一站**：[[计算机知识/70-编译原理/07-中间表示Lowering与三地址码|中间表示、Lowering 与三地址码]] · **下一站**：[[计算机知识/70-编译原理/09-数据流分析格不动点活跃性与到达定义|数据流分析、格、不动点、活跃性与到达定义]] · **返回**：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/70-编译原理/10-系统课程/05-中间表示CFG与SSA|中间表示、控制流与 SSA：给优化一个可证明的对象]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
