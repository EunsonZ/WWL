---
type: lesson
domain: computer-science
stage: 4
status: ready
difficulty: 中级到进阶
estimated_minutes: 110
verified_on: 2026-09-04
topics:
  - llvm-ir
  - static-single-assignment
  - verifier
  - compiler-pass
  - mlir
  - dialect
  - progressive-lowering
tags:
  - computer-science/compiler
  - computer-science/intermediate-representation
  - computer-science/llvm
  - computer-science/mlir
---

# LLVM IR、Pass 与 MLIR 方言 Lowering

LLVM IR 与 MLIR 都是中间表示基础设施，但不应被压成“两种文本汇编”。LLVM IR 为多种优化与目标生成提供低层、类型化、SSA 中心的共同形式；MLIR 用 operation、value、block、region 和 dialect 保留多层领域语义，让系统能逐步 lowering，不必在前端立即丢掉结构。

> [!info] 官方资料与时效边界
> 本页按 [LLVM Language Reference](https://llvm.org/docs/LangRef.html)、[LLVM Tutorial](https://llvm.org/docs/tutorial/)、[MLIR Language Reference](https://mlir.llvm.org/docs/LangRef/) 与 [MLIR Target LLVM IR](https://mlir.llvm.org/docs/TargetLLVMIR/) 核对至 **2026-09-04**。内容只总结稳定模型，不记录某个版本的 C++ API、Pass 命令行名称、dialect 完整 op 列表或建构步骤。这些表面接口会变，实际项目应固定工具链版本并查当版本文档。

## 本课目标

学完后，你应能：

1. 从 module、function、basic block、instruction 和 SSA value 解释 LLVM IR；
2. 区分 parser 接受、verifier 通过、优化正确与程序功能正确；
3. 设计 analysis/transform pass 及其依赖、失效和顺序契约；
4. 用 operation、value、block、region 与 dialect 阅读 MLIR 结构；
5. 规划一条保留语义的 progressive lowering 路线，并为每一步定义验证点。

## 先修与连接

- CFG、SSA 与数据流：[[计算机知识/70-编译原理/08-控制流图支配关系与SSA|控制流图、支配关系与 SSA]]、[[计算机知识/70-编译原理/09-数据流分析格不动点活跃性与到达定义|数据流分析与不动点]]
- 优化的语义契约：[[计算机知识/70-编译原理/11-优化正确性语义保持与验证测试|优化正确性、语义保持与验证]]
- VM 与 JIT：[[计算机知识/70-编译原理/16-解释器字节码VM-JIT与去优化|解释器、字节码 VM、JIT 与去优化]]
- 目标指令与 ABI：[[计算机知识/30-计算机系统/06-指令系统汇编与程序执行|指令系统、汇编与程序执行]]

## 1. LLVM IR 的位置：可分析的低层契约

```text
source-language AST / high-level IR
  → LLVM IR module
      → functions
          → basic blocks
              → typed instructions producing/using SSA values
  → optimization and legalization
  → target-specific lowering and code generation
```

LLVM IR 的文本、in-memory 和 bitcode 形式用于表达同一层语义，但不应假设它们是无版本的永久存储契约。LLVM IR 也不是“完全无目标信息”：target triple、data layout、地址空间、调用约定、intrinsic 与属性都可影响含义和合法 lowering。

### Module、function 与 global

- **module** 是全局变量、函数、别名、metadata 及目标信息的顶层容器；
- **function** 有签名、参数、基本块与属性，也可只声明而不定义；
- **global** 的链接、可见性、地址空间和初始化不能用“一块全局内存”概括。

这些对象最终与符号和 ABI 相连，见 [[计算机知识/70-编译原理/15-目标文件符号重定位链接与装载|目标文件、符号、重定位、链接与装载]]。

## 2. Basic block、SSA value 与 memory

基本块是单入的直线指令序列，末尾由 terminator 决定控制流。LLVM IR 指令可产生有类型的 SSA value，后续使用点引用该定义：

```pseudo
function absolute(input):
entry:
  is_negative = compare input < 0
  branch is_negative, negative_block, merge_block(input)

negative_block:
  negated = subtract 0, input
  branch merge_block(negated)

merge_block(result_from_predecessor):
  return result_from_predecessor
```

这里用“块参数/合流值”伪语法表达 SSA 合流直觉；LLVM IR 的具体合流形式以 LangRef 为准。重点是：每个 SSA 名称代表一次定义，使用必须在控制流上被定义支配。

SSA 不代表“程序没有可变状态”。内存还可以经由 load/store/call 被读写；指针别名与外部调用会限制优化。将一个局部内存位置提升为 SSA value 是分析/变换成果，不是读入 IR 时的无条件事实。

## 3. 语义不只在 opcode 名字里

阅读一条 IR 指令时，至少问：

1. 操作数和结果的类型是什么？
2. 整数溢出、浮点特殊值、不对齐、越界和 poison/undefined 相关前提是什么？
3. 是否读写内存、抛出/展开、同步、返回或影响控制流？
4. attribute、metadata 和 intrinsic 是语义承诺、优化提示，还是调试信息？
5. data layout 和 target 会如何影响尺寸、对齐、地址空间与调用？

优化器能利用的是**前端真正有权承诺的事实**。若为了“让代码更快”虚构不成立的 attribute 或前提，后续变换即使完全符合 LLVM IR 语义，也可能与源语言行为不一致。

## 4. Verifier：每次边界转换后的结构门

```pseudo
pipeline(ir):
  verify ir after frontend construction
  for each transformation_stage:
    run transformation_stage
    verify ir
    optionally compare semantics on differential tests
  lower to target representation
  verify target-side constraints
```

LLVM verifier 用来检查 IR 的良构性与特定不变量，例如指令类型关系、基本块结构、SSA 定义/使用约束与某些属性一致性。但“verifier 通过”只说明 IR 符合这些规则，不说明：

- 前端正确实现了源语言；
- pass 在所有输入上保持行为；
- 程序不含数组越界、竞态、资源耗尽或业务逻辑错误；
- 该 IR 在任意 target/data layout 上都有同一行为。

只 parse 成功就更弱：文本语法可读并不代表 dominance、类型、region 或 dialect 约束已通过验证。

## 5. Pass：分析、变换与失效

| 类型 | 输入/输出契约 | 例子性问题 |
| --- | --- | --- |
| analysis pass | 读 IR，产生可缓存事实 | 哪些值是 live？哪些内存可能 alias？ |
| transform pass | 重写 IR，必须保持约定语义 | 删掉该指令会不会删掉可观察副作用？ |
| utility/canonicalization | 把多种等价形式收敛到更易处理的形式 | 是否真正终止？是否造成 rewrite 循环？ |

一个 transform 改了 CFG、指令、内存读写或调用图后，之前缓存的 dominance、loop、alias 或 liveness 结果可能已失效。Pass manager 能编排分析与失效，却不能替 pass 作者自动推断所有语义。每个 pass 应说清：

```pseudo
pass_contract:
  requires = [verified_input_form, target_assumptions, analyses]
  may_change = [instructions, control_flow, memory_effect_summary]
  preserves = [language_observable_behavior, selected_analyses]
  establishes = [canonical_form_or_lower_level_invariants]
  diagnostics = [changed, not_changed, rejected_with_reason]
```

### Pass 顺序为什么是设计问题

- canonicalization 可暴露后续模式，但过早展开高层 op 也会丢掉可优化结构；
- inlining 可放大局部优化机会，也可导致 IR/code size 膨胀；
- loop 变换可依赖 alias、trip count 和数值语义；
- 两个各自正确的 pass 也可在不合适的 precondition 下组合失败。

不要以“反复跑到 IR 不再变”作通用解法。重写可在等价形式之间来回振荡，或虽然终止但以过高成本收敛。需要单调度量、明确 rewrite 优先级、迭代上限与诊断。

## 6. LLVM Tutorial 的正确使法

LLVM Tutorial 通过一个小语言串起 lexer、parser/AST、LLVM IR 生成、JIT 和优化。它适合建立端到端心智模型，但不应被当作生产编译器的完整架构处方。真实前端还要处理：

- 源语言精确语义、诊断与源位置；
- 模块、链接、ABI、异常、GC 和调试信息；
- 未定义/错误状态与安全边界；
- 多目标、增量编译、缓存、可复现构建与回归测试。

教程给出的是可学习骨架，不是证明“任何语言只需把 AST 直接翻译成 LLVM IR”。

## 7. MLIR 的五个基本名词

MLIR 用可扩展的 operation 图/层次表示程序。五个名词的关系是：

```text
operation
  ├─ consumes values
  ├─ produces values
  ├─ has attributes and types
  └─ may contain regions
         └─ contain blocks
                ├─ have block arguments (values)
                └─ contain ordered operations

dialect = a namespace plus a family of operations/types/attributes
          with defined semantics, verification and transformations
```

### Operation

Operation 是通用语义单元：可表示算术、函数、循环、张量、内存、设备或领域特定动作。它有名称、操作数、结果、attribute，并可拥有零个或多个 region。“所有 op 都是一条 CPU 指令”是错的：高层 op 可表示整个矩阵乘或模型调用。

### Value

Value 由 operation result 或 block argument 产生，并带类型。Value 是 SSA 数据流边，不等于可变内存单元。内存效应需由相应 op、type、interface 与 effect 契约表示。

### Block

Block 拥有参数与有序 operation，其控制流语义取决于所属 region/dialect。不应无条件把每个 MLIR block 等同于 LLVM IR basic block；不同 region kind 可持有不同控制流/图语义。

### Region

Region 是嵌套在 operation 中的 block 容器。它让循环体、条件分支、函数体或其他层次结构保持显式，而不必过早扯平成全局 CFG。

### Dialect

Dialect 是可扩展的命名空间与语义族，可定义 op、type、attribute、verification、canonicalization 与 lowering。Dialect 不是随意字符串标签；若没有明确语义和转换契约，只是把不清楚的操作换了命名空间。

## 8. Progressive lowering：每次只消除一类抽象

一条示意路线可以是：

```text
domain dialect
  → tensor / structured-compute dialects
  → loop / vector / control-flow forms
  → explicit memory and lower-level arithmetic forms
  → LLVM dialect plus dialects translatable to LLVM IR
  → LLVM IR
  → target code
```

这不是 MLIR 规定的唯一 dialect 顺序。真正稳定的思想是：

1. 在某层仍有用时保留该层抽象；
2. 一个 conversion 将明确非法的 op/type 改写为目标允许的形式；
3. 每个过渡点验证前置条件、剩余 illegal op、语义保留和 target 约束；
4. 到 LLVM IR 的常见终段分为：先 conversion 到可翻译为 LLVM IR 的 dialect 集合，再 translation 成 LLVM IR。

“Lowering”不一定意味“每次只产生一条更低层指令”。一个高层 op 可展开为多个循环与内存操作；一组 op 也可融合成一个 target kernel。关键是目标 dialect 的合法集与语义契约。

## 9. 示例：从领域矩阵运算到 LLVM IR

```pseudo
high_level:
  result = MATRIX_MULTIPLY(left, right)
  annotations = [element_type, shapes, layout_constraints, numeric_mode]

structured_tensor_level:
  define iteration dimensions and reduction dimension
  preserve tensor value semantics

loop_and_vector_level:
  tile iteration space
  vectorize legal inner computation
  make remainder handling explicit

memory_level:
  choose buffers and address spaces
  make loads, stores, strides and lifetimes explicit
  preserve alias and side-effect ordering

llvm_dialect_level:
  legalize types, control flow, calls and memory operations
  retain target/data-layout requirements

llvm_ir_translation:
  translate only supported dialect operations
  verify LLVM IR
  continue target-specific optimization and code generation
```

这条路线中，shape、layout、浮点重结合权限、alias、内存空间与越界语义不能在某次 lowering 中“默认差不多”。每次优化都要有前提和正确性依据。

### 反例：前端立即展开成指针循环

若前端一开始就把 `MATRIX_MULTIPLY` 降为一串不透明指针加法与 load/store，后续要重新猜测哪些循环维度是并行、哪个是 reduction、输入是否重叠、layout 是否连续。过早 lowering 不是必然错误，但它会将高层事实从显式契约变成后续分析问题。

## 10. 设计 dialect 与 lowering 时的核心问题

| 问题 | 必须记录的契约 |
| --- | --- |
| op 是什么 | 操作数/结果类型、shape、attribute、region 语义 |
| op 能否重排 | memory effects、alias、异常/中断、同步与数值约束 |
| 哪些形式合法 | verifier 的局部与 region/dialect 不变量 |
| canonical form 是什么 | 收敛度量、rewrite 优先级与终止策略 |
| lowering 保留什么 | 可观察行为、精度、错误、layout、设备与 ABI |
| 哪些 op 应被消除 | conversion target 的 legal/illegal/dynamic-legal 条件 |
| 如何诊断失败 | 原 op 位置、未满足前提、剩余非法形式 |

一个好 dialect 不以 op 数量多为目标，而以“这层信息是否能被清楚表达、验证、变换和有界地降级”为目标。

## 11. 反例清单

1. **“LLVM IR 有类型，所以是内存安全的”**：类型良构不排除指针越界、错误 lifetime 或竞态。
2. **“能 parse 就能 codegen”**：parse、verify、legalize 到某 target 是不同关卡。
3. **“pass 输出更短就更优”**：还要考察语义、target 成本、compile time 与 code size。
4. **“dialect 越多越先进”**：无明确边界会制造重复 op、循环 conversion 与语义缝隙。
5. **“lowering 只是语法替换”**：type conversion、layout、memory effects、control flow 与 ABI 都可成为转换的核心。

## 12. 练习：为张量表达式设计三层 IR

给定语义：“对两个张量元素相加，紧接着做矩阵乘”。只使用伪 IR，不调用真实 LLVM/MLIR API。

1. 高层定义 `TENSOR_ADD` 与 `MATRIX_MULTIPLY`，包含类型、shape、layout 和 numeric mode；
2. 中层用 region/block/value 表示结构化 iteration 与 reduction；
3. 低层写出显式 buffer、loop、load/store 与 control flow；
4. 为每层写 verifier 不变量和非法输入；
5. 定义两个 analysis pass、两个 transform pass，标出依赖与失效；
6. 说明中层到低层时如何保留 alias、side effect、shape 失败和浮点语义；
7. 在伪管线中标出何时 verify，何时做差分测试。

### 成功标准

- 能用一张图正确连接 operation、value、block、region 和 dialect；
- 三层 IR 各自保留有用抽象，没有把同一层用不同名字重写三次；
- 至少一个 pass 明确使某 analysis 失效，而不是宣称全部 preserve；
- 某个 lowering 失败时能指出具体 illegal op/type 和未满足前提；
- 能解释 verifier 通过为何仍不证明矩阵结果正确。

## 13. 官方来源

- [LLVM Language Reference Manual](https://llvm.org/docs/LangRef.html)：LLVM IR 的规范性语义入口。
- [My First Language Frontend with LLVM Tutorial](https://llvm.org/docs/tutorial/)：前端、IR、优化与 JIT 的教学链路。
- [MLIR Language Reference](https://mlir.llvm.org/docs/LangRef/)：operation、value、block、region 与 dialect 的语言结构。
- [MLIR Target LLVM IR](https://mlir.llvm.org/docs/TargetLLVMIR/)：向 LLVM dialect 转换、再向 LLVM IR 翻译的终段边界。

## 导航

- 上一站：[[计算机知识/70-编译原理/16-解释器字节码VM-JIT与去优化|解释器、字节码 VM、JIT 与去优化]]
- 下一站：[[计算机知识/70-编译原理/18-AI编译栈图捕获融合Shape与张量Kernel|AI 编译栈：图捕获、融合、Shape 与张量 Kernel]]
- 返回：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/70-编译原理/10-系统课程/03-语法分析FIRST_FOLLOW与LR|语法分析：从预测集合到移进归约冲突]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
