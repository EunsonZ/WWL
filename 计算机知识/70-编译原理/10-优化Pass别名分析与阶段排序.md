---
type: lesson
domain: computer-science
stage: 2
status: ready
difficulty: 进阶
estimated_minutes: 75
topics:
  - compiler-optimization
  - optimization-pass
  - alias-analysis
  - dependence-analysis
  - phase-ordering
tags:
  - computer-science/compiler
  - computer-science/compiler/optimization
aliases:
  - 编译器优化 Pass
  - 别名分析与 Phase Ordering
---

# 优化 Pass、别名分析与阶段排序

## 本课目标

学完后，你应该能够：

- 用“前提—变换—语义义务—收益假设”描述一个优化 Pass，而不只背优化名称；
- 解释常量折叠与传播、死代码删除、CSE/GVN、LICM、内联和向量化各自依赖什么事实；
- 区分别名、逃逸与循环依赖分析，并说明它们为何会限制代码移动和并行化；
- 把**合法性**与**收益性**分开：先证明允许改，再估计值不值得改；
- 用具体例子说明 Pass 顺序不满足交换律，以及编译器为何采用分阶段流水线而不是“所有优化各跑一次”。

## 先修与边界

- 先修：[[计算机知识/70-编译原理/09-数据流分析格不动点活跃性与到达定义|数据流分析、格、不动点、活跃性与到达定义]]。
- 系统中的地址、缓存、SIMD 与真实执行代价分别见 [[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程虚拟地址空间与内存映射]]、[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]] 和 [[计算机知识/30-计算机系统/05-并发并行SIMD与加速器|并发、并行、SIMD 与加速器]]。
- 本课只讨论优化器如何使用这些事实，不重复体系结构与操作系统课程。

## 1. 直觉：优化是带证明义务的程序改写

优化器看到的不是“这段写得不够漂亮”，而是一个候选改写：

```text
候选 = match(IR)
事实 = analyze(candidate)

if legal(candidate, facts, language_semantics):
    if profitable(candidate, target_cost_model, profile):
        rewrite(candidate)
```

这里有两扇不能混为一谈的门：

1. **合法性（legality）**：变换后不能产生源程序不允许的新可观察行为。
2. **收益性（profitability）**：在特定目标、代码尺寸、热点和编译时间预算下，预计会更好。

“可能更快”不能替代合法性证明；“语义等价”也不保证值得做。一次合法的内联可能造成代码膨胀和指令缓存压力，一次合法的向量化也可能被短循环的准备成本抵消。

## 2. Pass、分析与失效

**Pass** 是对某种 IR 执行分析或变换的单元。分析 Pass 产生支配关系、循环结构、别名集合等事实；变换 Pass 修改 IR。修改之后，旧事实可能失效。

```text
dom = compute_dominators(function)
loops = discover_loops(function, dom)
aliases = analyze_aliases(function)

changed = run_licm(function, loops, aliases)
if changed:
    invalidate(dom, loops, aliases, except = facts_proven_preserved)
```

正确的 Pass 管理器必须知道哪些分析可复用、哪些必须重算。复用失效事实可能误编译；每次全部重算通常又会浪费编译时间。

## 3. 局部和值优化

### 3.1 常量折叠与常量传播

**常量折叠（constant folding）**在编译期求值；**常量传播（constant propagation）**把“某 SSA 值恒为常量”的事实送到它的使用点。

```text
before:
    a = 3 * 4
    b = a + input

after folding and propagation:
    b = 12 + input
```

折叠必须服从源语言和 IR 的数值语义。固定宽度整数是回绕、陷阱还是未定义？浮点舍入模式是否可观察？这些问题不能用优化器宿主语言的普通算术草率代替。

### 3.2 死代码删除（DCE）

如果一个计算结果不可达或未被使用，且计算本身没有必须保留的副作用，DCE 才能删除它。

```text
before:
    unused = pure_add(x, 1)
    print(x)

after:
    print(x)
```

反例：下列结果虽未使用，操作却可能抛异常或写外部状态。

```text
unused = divide(x, 0)       // may throw
unused = volatile_load(p)   // observable access
unused = call_unknown()     // may perform I/O
```

因此，“SSA 结果没有 use”不等于“整条指令没有 effect”。现代 IR 往往显式建模内存、异常、原子、volatile 或 effect token，避免把副作用藏在普通值边里。

### 3.3 CSE 与 GVN

**公共子表达式消除（CSE）**复用重复计算；**全局值编号（GVN）**为能证明相等的值建立同一编号，范围可以跨基本块。

```text
v1 = add(a, b)
v2 = add(a, b)
use(v2)

rewritten:
    v1 = add(a, b)
    use(v1)
```

纯加法容易判断；内存读取则需要更强证明：

```text
x = load(p)
store(q, 7)
y = load(p)
```

只有证明 `p` 与 `q` 不别名，或证明中间写入不影响 `p` 所指位置，才能把 `y` 替换为 `x`。

## 4. 循环与跨过程优化

### 4.1 LICM：循环不变量外提

LICM 把每次迭代结果相同的计算移到循环外，以减少重复工作。

```text
before:
    for i in 0 .. n:
        scale = load(config_ptr)
        out[i] = in[i] * scale

candidate after:
    scale = load(config_ptr)
    for i in 0 .. n:
        out[i] = in[i] * scale
```

外提合法至少需要回答：循环内有没有可能通过另一个指针改写该配置？原位置的加载是否可能陷阱，而外提后会在零次迭代时也执行？加载与异常、并发或 volatile 语义是否可观察？“循环里看起来没给 `config_ptr` 赋值”远远不够。

### 4.2 内联

内联用被调函数体替换调用点。它既能消除调用开销，更重要的是暴露上下文：实参常量、精确类型和调用方别名事实可触发传播、DCE、去虚化与循环优化。

```text
function choose(flag, x):
    if flag: return x * 2
    else: return slow_path(x)

caller:
    y = choose(true, input)

after inline + propagation + DCE:
    y = input * 2
```

反例：把巨大冷函数内联进多个调用点可能增大代码尺寸，破坏指令缓存局部性，并拉长后续分析时间。内联决策通常结合函数大小、调用频率、递归深度和后续优化机会。

### 4.3 向量化

向量化把多次标量迭代组合成向量操作。它需要证明迭代间没有阻止重排的数据依赖，并处理对齐、尾部、别名、异常与浮点语义。

```text
scalar:
    for i in 0 .. n:
        out[i] = left[i] + right[i]

vector candidate:
    for i in vector_chunks(0, n, width):
        store_vector(out + i,
                     load_vector(left + i) + load_vector(right + i))
    run_scalar_tail()
```

若 `out` 可能与 `left` 错位重叠，向量批量读写可能改变原本逐元素执行的结果。优化器可以放弃向量化，也可以生成运行时别名检查，在“不重叠”分支走向量版本，在另一分支保留标量版本。

## 5. 三类关键分析：alias、escape、dependence

### 5.1 别名分析

两个引用在某个程序点可能指向同一存储位置，就存在 **may-alias**；能证明不会重叠则是 **no-alias**；必须指向同处可称 **must-alias**。保守分析在不确定时回答 may-alias，以牺牲机会换正确性。

别名分析可能利用：分配点、类型规则、字段偏移、调用摘要、语言所有权/借用约束、显式 no-alias 契约。契约若被前端或程序违反，后续优化就可能失去依据。

### 5.2 逃逸分析

若对象引用可能离开当前函数、线程或分析范围，它就**逃逸**。常见逃逸途径包括返回、写入全局、存入未知对象、传给语义未知的调用或被闭包捕获。

```text
obj = allocate()
obj.value = 3
return obj          // escapes through return
```

证明不逃逸可支持栈上分配、标量替换、消除同步或缩小别名集合。逃逸分析回答的是引用传播边界，不等同于“对象最终活多久”。

### 5.3 依赖分析

循环依赖描述不同迭代对内存或值的读写关系：真依赖（写后读）、反依赖（读后写）和输出依赖（写后写）会限制重排。

```text
for i in 1 .. n:
    a[i] = a[i - 1] + 1
```

第 `i` 次迭代读取上一次写入，存在跨迭代真依赖，不能直接让所有迭代并行。相反，若每次只读输入并写独立输出，通常更适合向量化。

三者相互支持但不互相替代：alias 判断地址是否可能重叠；escape 判断引用是否越过分析边界；dependence 判断操作顺序是否承载语义。

## 6. 阶段排序：Pass 不满足交换律

设 `A`、`B` 为两个 Pass，通常不能假定 `A(B(IR)) = B(A(IR))`。

典型链条是：

```text
inline
-> constant propagation
-> branch simplification
-> dead code elimination
-> loop canonicalization
-> LICM
-> vectorization
-> cleanup DCE
```

- 先内联才可能看见常量实参；先做一次 DCE 未必能删掉内联后才暴露的冷分支。
- 循环规范化让 LICM 和向量器看到可识别形态；过早展开循环可能放大 IR，使分析更慢。
- LICM 可减少循环体工作，也可能改变寄存器压力；向量化后再做标量风格优化，效果未必相同。
- CSE 可能减少指令，也可能延长值的活跃区间，增加寄存器压力和 spill。

生产编译器常采用“规范化—暴露机会—主要优化—清理”的多阶段流水线，并对部分廉价 Pass 迭代到固定点或预算上限。阶段排序本身就是搜索问题；目标相关成本模型与 profile-guided information 会改变答案。

## 7. 一个完整决策：能否外提一次加载

面对循环内 `load(p)`，可以按以下顺序审查：

1. **支配与循环结构**：新位置是否支配所有使用点？
2. **别名与修改集合**：循环中所有写是否都能证明不影响 `p`？
3. **控制与异常**：原加载是否只在条件分支发生？外提会不会让原本不执行的陷阱提前发生？
4. **语言语义**：是否涉及原子、volatile、并发可见性或规定的异常顺序？
5. **收益**：预头块是否高频执行但循环常零次？外提后活跃区间和寄存器压力如何？
6. **验证**：IR 结构检查、专项测试与差分测试能覆盖哪些风险？

这套顺序体现核心纪律：分析给事实，合法性消费事实，成本模型决定是否实施，验证负责发现证明或实现中的漏洞。

## 练习

1. 对 `x = 4 * 8; if x > 0 then use(a) else use(b)` 画出 folding、propagation、分支简化与 DCE 的先后关系，写出每一步 IR 伪代码。
2. 对 `load(p); store(q); load(p)` 分别给出 no-alias、may-alias、must-alias 三种结论下 CSE 的合法性。
3. 设计一个 LICM 反例：循环可能执行零次，而候选外提指令可能抛异常。指出改变了哪个可观察行为。
4. 为数组逐元素相加列出向量化前必须确认的依赖、别名、尾部和浮点条件；再写一个运行时版本化的伪代码框架。
5. 比较“先内联后常量传播”和“只先常量传播不再重跑”得到的结果，说明阶段排序为何影响最终 IR。
6. 给一个合法但可能亏损的优化，以及一个看起来有收益但不合法的优化；分别说明判断依据。

## 成功标准

- 你能为至少六类优化写出各自的合法性前提，而不是只描述变换表面；
- 你能用 `load/store` 例子解释 alias、escape 和 dependence 的不同问题；
- 你会把“能不能改”与“值不值得改”分开记录；
- 你能构造一个 Pass 顺序反例，并指出需要重跑或清理 Pass 的原因；
- 你的向量化或 LICM 方案明确处理副作用、异常、零迭代、别名和尾部边界。

---

**上一站**：[[计算机知识/70-编译原理/09-数据流分析格不动点活跃性与到达定义|数据流分析、格、不动点、活跃性与到达定义]] · **下一站**：[[计算机知识/70-编译原理/11-优化正确性语义保持与验证测试|优化正确性、语义保持与验证测试]] · **系统连接**：[[计算机知识/30-计算机系统/05-并发并行SIMD与加速器|并发、并行、SIMD 与加速器]] · **返回**：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/70-编译原理/10-系统课程/05-中间表示CFG与SSA|中间表示、控制流与 SSA：给优化一个可证明的对象]]
- [[计算机知识/70-编译原理/10-系统课程/06-优化等价性数据流与陷阱|优化必须保持什么：别名、溢出、异常与浮点]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
