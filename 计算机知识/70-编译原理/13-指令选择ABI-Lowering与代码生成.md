---
type: lesson
domain: computer-science
stage: 3
status: ready
difficulty: 进阶
estimated_minutes: 85
topics:
  - instruction-selection
  - target-lowering
  - ABI
  - calling-convention
  - code-generation
tags:
  - computer-science/compiler
  - computer-science/backend
  - computer-science/abi
---

# 指令选择、ABI Lowering 与代码生成

## 本课目标

学完后，你应该能够：

- 区分目标无关变换、目标相关合法化、指令选择、ABI lowering、寄存器分配和最终编码；
- 用 pattern matching / tree tiling 解释低级 IR 怎样被一组目标指令覆盖；
- 说明寻址模式、立即数范围、比较/分支形式和调用指令为何会改变选择结果；
- 按 ABI 追踪参数、返回值、caller-saved / callee-saved 寄存器、栈参数和栈对齐；
- 为一个小函数写出从低级 IR 到概念化机器 IR 的转换，并逐项检查其正确性边界。

适用场景：阅读编译器后端、理解同一源程序为何在不同 target 上产生不同代码、定位错误调用约定、为寄存器分配和目标文件课程建立输入。

## 先修与本页边界

建议先读：

- [[计算机知识/70-编译原理/07-中间表示Lowering与三地址码|中间表示、Lowering 与三地址码]]；
- [[计算机知识/70-编译原理/08-控制流图支配关系与SSA|控制流图、支配关系与 SSA]]；
- [[计算机知识/30-计算机系统/06-指令系统汇编与程序执行|指令系统、汇编与程序执行]]；
- [[计算机知识/30-计算机系统/03-ABI调用约定与静态动态链接|ABI、调用约定与静态/动态链接]]。

本页假定输入已经通过类型检查，并已下降为带基本块、显式 load/store、调用和低级数据类型的 IR。这里聚焦“怎样表达为目标机器能执行且符合 ABI 的操作”。全局寄存器分配和指令调度留给第 14 课；section、symbol、relocation、link 与 loader 留给第 15 课。

> [!important] 不要把 ISA、ABI 与微架构混在一起
> ISA 决定有哪些架构指令、寄存器和编码约束；ABI 决定二进制组件怎样交接参数、返回值、寄存器责任和栈；微架构决定某颗处理器怎样执行这些指令以及代价多大。同一 ISA 可以有多个 ABI，同一 ABI 也不能替代具体 CPU 的性能模型。

## 1. 直觉：后端是在受约束的零件箱里实现同一语义

低级 IR 可能写成：

```text
offset = index * 8
address = base + offset
value = load_i64(address)
result = value + 7
store_i64(address, result)
```

目标 A 也许能把“基址 + 索引 × 8 + 位移”直接放进 load/store 的地址操作数，并能把 `7` 编成算术立即数。目标 B 也许必须先移位、再相加得到地址，但同样能编码 `7`。目标 C 若立即数字段太窄，还要先把常量构造进寄存器。

三者都必须实现同一个可观察结果，但合法的指令序列、长度、临时值数量和代价不同。后端不是逐词翻译，而是在这些约束中寻找一个**合法且成本可接受的覆盖**。

## 2. 后端阶段要拆开看

| 阶段 | 典型输入与输出 | 主要问题 | 不应与什么混淆 |
| --- | --- | --- | --- |
| 目标无关优化 | 通用 IR → 等价的通用 IR | 常量传播、DCE、CFG 简化等是否由语言/IR 语义允许 | 某个 target 恰好有哪条指令 |
| target lowering / legalization | 通用低级操作 → 目标可表达的操作和类型 | 非法宽度、特殊算术、原子操作、调用等怎样展开 | 最终寄存器编号和字节编码 |
| 指令选择 | 合法化后的操作图/机器 IR → 目标伪指令或指令 | 哪些 pattern 能覆盖当前计算 | 寄存器已经分配完毕 |
| ABI lowering | 抽象 call/return/参数 → 调用约定位置与动作 | 值由哪些寄存器、栈槽或隐藏参数传递 | ISA 本身强制的唯一做法 |
| 寄存器分配与调度 | 虚拟寄存器机器 IR → 物理寄存器与合法顺序 | 有限寄存器和执行资源怎样分配 | 本页的局部 pattern 选择 |
| MC/code emission | 已定指令 → 编码字节、symbol、relocation 等 | 位域怎样编码，未知地址怎样留下补丁记录 | 链接器已经解析了所有地址 |

真实编译器可以交错或合并这些步骤。例如，合法化可能产生更适合匹配的节点，调用序列展开可能等寄存器分配后才确定某些保存动作，分支放宽也可能在布局阶段反复进行。表格是职责分解，不是强制的单遍流水线。

### target-independent 与 target lowering 的分界

目标无关变换应只依赖源语言与 IR 已声明的语义。例如，若 IR 定义整数加法按固定位宽回绕，则把 `x + 0` 化为 `x` 不需要知道目标 ISA；若源语言把某种溢出设为陷阱或未定义，合法性又取决于该语义。

target lowering 则回答“目标能不能直接表示”：

```text
if target_has_native_i64_multiply:
    lower multiply_i64(a, b) to TARGET_MUL64(a, b)
else:
    lower multiply_i64(a, b) to checked_helper_call_or_multiword_sequence(a, b)
```

这里仍是伪代码。重要的是 lowering 必须继承原操作的溢出、异常、舍入、内存顺序和可观察副作用；“目标没有原生指令”只授权等价展开，不授权悄悄改变语义。

## 3. Pattern matching 与 tree tiling

### 从表达式树看覆盖

把表达式 `base + index * 8` 看成树：

```text
          add
         /   \
      base   multiply
             /      \
          index      8
```

目标指令模板相当于不同大小的拼图：

```text
tile A: ADD(register, register)
tile B: SHIFT_LEFT(register, 3)
tile C: ADDRESS(base, index, scale=8, displacement=0)
```

一种覆盖用 `multiply → SHIFT_LEFT`，再用 `add → ADD`；另一种用一个复合地址 tile 覆盖整棵树，并作为 load 的地址操作数。**Tree tiling**就是用合法 tiles 覆盖整棵计算树，每个节点恰好被实现，并依据代码长度、估计延迟或其他目标成本选出方案。

### 一个最小动态规划视角

```text
best_cost(node, desired_result_kind):
    candidates = every pattern whose root matches node
    for each candidate:
        cost = candidate.local_cost
        cost += sum(best_cost(child, candidate.required_child_kind))
    return candidate with minimum legal cost
```

这解释了为什么不能总是“先匹配最大片段”：一个大 pattern 可能需要额外复制、限制寄存器类别，或破坏后续融合；多个小 pattern 的全局成本反而更低。

### 树模型的边界

真实 IR 常是 DAG 或带控制/内存边的图：一个值可被多次使用，load/store 有顺序约束，比较结果可同时供分支和布尔值使用。若简单复制共享子树，可能重复昂贵计算甚至重复副作用。因此工业选择器还要表示：

- 数据依赖：使用必须看到对应定义；
- 内存依赖：两个可能别名的访问不能任意换序；
- 控制依赖：分支、异常和调用改变可执行路径；
- 特殊约束：某些操作隐式读写固定寄存器或状态位。

## 4. 手算例：两种目标约束产生两种选择

输入机器无关 IR：

```text
v_offset = multiply(v_index, 8)
v_address = add(v_base, v_offset)
v_old = load_i64(v_address)
v_new = add(v_old, 7)
store_i64(v_address, v_new)
```

假设目标 `FoldAddr` 支持缩放地址和小立即数：

```text
v_old = LOAD64 address(base=v_base, index=v_index, scale=8)
v_new = ADD64_IMMEDIATE v_old, 7
STORE64 address(base=v_base, index=v_index, scale=8), v_new
```

假设目标 `SimpleAddr` 的访存只接受“寄存器 + 小位移”，但支持左移和小立即数：

```text
v_offset = SHIFT_LEFT v_index, 3
v_address = ADD64 v_base, v_offset
v_old = LOAD64 address(base=v_address, displacement=0)
v_new = ADD64_IMMEDIATE v_old, 7
STORE64 address(base=v_address, displacement=0), v_new
```

应逐项检查：

1. `8 = 2³` 的 strength reduction 在当前整数语义下是否合法；
2. 地址宽度和回绕/陷阱语义是否保持；
3. load 与 store 的宽度、对齐要求、volatile/atomic 属性是否保留；
4. `7` 是否落在目标立即数编码范围；
5. 复合地址会不会让 `v_address` 的其他使用被错误消失；
6. 两次地址计算是否能共享，还是目标编码允许各自折叠更便宜。

这只是选择到虚拟寄存器机器 IR。`v_old`、`v_new` 等还不是物理寄存器；第 14 课才决定它们放在哪里。

## 5. 寻址模式与立即数是语义受限的编码机会

### 寻址模式

常见抽象形式包括：

```text
address = base + index * scale + displacement
address = base + displacement
address = program_counter + displacement
address = stack_pointer + frame_offset
```

具体 target 只允许其中某些形式，并限制 scale、位移范围、对齐和可用寄存器。选址模式时还要区分：

- 计算的是普通整数还是可解引用地址；
- 地址空间、权限或 pointer provenance 是否在 IR 中有额外语义；
- 符号地址当前是否未知，需要第 15 课的 relocation；
- 大位移能否直接编码，还是必须先构造临时地址。

### 立即数

“常量存在”不代表“可直接嵌入这条指令”。一个 target 可能允许 12 位无符号立即数，另一个允许旋转后的位模式，第三个需要多条构造指令或常量池加载。

```text
if fits_ADD_immediate(constant):
    emit ADD_IMMEDIATE source, constant
else:
    v_constant = materialize_constant(constant)
    emit ADD_REGISTER source, v_constant
```

常量池又引入布局、可达距离和 relocation 问题，不能在选择时假设最终地址已知。

## 6. 比较、分支与控制流 lowering

同一个条件 `x < y` 可以由不同机器模型表达：

```text
model FLAGS:
    COMPARE x, y           writes implicit condition state
    BRANCH_IF_LESS target  reads implicit condition state

model BOOLEAN:
    v_cond = SET_LESS x, y
    BRANCH_IF_TRUE v_cond, target

model PREDICATE:
    p = COMPARE_TO_PREDICATE x, y
    PREDICATED_SELECT_OR_BRANCH p, ...
```

选择器必须保留 signed/unsigned、整数/浮点、有序/无序比较的区别。浮点 `NaN` 会让“不是小于”不等于“大于等于”；把一种谓词机械取反可能改错语义。

分支位移也可能有有限范围。初选时可发出抽象分支，布局后若目标太远再使用长分支或跳板。条件分支、无条件分支、间接跳转、调用和返回有不同的控制流与安全约束，不能只因最终都会改变 PC 就混成一种指令。

## 7. ABI lowering：把抽象函数边界落实为二进制合同

源级调用：

```text
pair = combine(a_i64, b_f64, c_pointer, d_i32, e_i64)
```

ABI 分类器可能产生如下概念结果：

```text
argument a -> integer_argument_register_0
argument b -> floating_argument_register_0
argument c -> integer_argument_register_1
argument d -> integer_argument_register_2 after required extension
argument e -> caller_stack_slot_0
return pair -> return_register_0 + return_register_1
```

另一 ABI 可能把聚合返回改成隐藏的 `sret` 指针：

```text
hidden_argument 0 -> address_of_caller_owned_return_storage
ordinary arguments shift to later locations
callee stores result into hidden return storage
call expression receives no ordinary register result
```

这不是优化偏好，而是调用双方必须一致的合同。仅看源函数签名仍可能不够：语言 ABI 还会规定名称修饰、聚合分类、可变参数、异常展开、TLS、构造器或虚函数相关布局。

### 参数与返回值分类

ABI lowering 通常依次处理：

1. 按类型、大小、对齐和 ABI 规则把参数分成整数、浮点、向量、聚合或内存类别；
2. 分配参数寄存器，耗尽后放入调用者栈参数区；
3. 插入要求的符号扩展、零扩展、拆分、合并或间接传递；
4. 以 ABI 指定方式返回标量、向量、聚合或隐藏地址结果；
5. 为可变参数、尾调用和异常边应用额外规则。

### caller-saved 与 callee-saved

| 类别 | 调用前仍需要该值时，谁负责保存 | 直觉 |
| --- | --- | --- |
| caller-saved / volatile | 调用者 | 被调函数可以自由覆盖；跨调用活跃的值需由调用者保护 |
| callee-saved / non-volatile | 被调者 | 被调函数若使用，必须在返回前恢复调用者看到的原值 |

“保存”不一定发生：若寄存器中的值在调用后不再活跃，就无需保存 caller-saved；若被调函数没使用某个 callee-saved，也无需形成对应 save/restore。活跃性与实际分配会影响最终序言/尾声。

### 栈帧与对齐不变量

一个概念化调用序列：

```text
caller:
    reserve outgoing_stack_arguments_and_required_padding
    preserve live caller-saved values before argument moves overwrite them
    place stack arguments without destroying still-needed sources
    place register arguments using a parallel-copy schedule
    CALL callee
    read return location
    restore preserved caller values
    release outgoing area

callee entry:
    establish frame if required
    save every callee-saved register actually used
    allocate aligned local_and_spill_area
    execute body
    restore saved registers
    dismantle frame
    RETURN
```

旧 R0=7 在调用后还活跃，而实参3要进入 R0，必须先保护7：

| 步骤 | R0 | 独立保存槽 | 结果位置 |
| --- | --- | --- | --- |
| 保存旧值 | 7 | 7 | — |
| 装入实参 | 3 | 7 | — |
| CALL | 被调用者接收3，返回后可覆盖 | 7 | ABI返回寄存器 |
| 读取返回 | 返回值 | 7 | 复制到不被恢复覆盖的位置 |
| 恢复旧值 | 7 | 可释放 | 返回结果保留 |

参数交换 `R0←old R1, R1←old R0` 是并行复制；顺次 R0=R1; R1=R0 会丢旧R0。可用不承载活值、也不被该搬运覆盖的临时寄存器：`tmp=R0; R0=R1; R1=tmp`；或预留满足 ABI 对齐的独立临时栈槽进行 store/load。临时槽不能覆盖保存槽或栈参数区，所有槽与 padding 一并纳入调用点对齐。

若 ABI 要求“调用点的栈指针按 `A` 字节对齐”，则必须满足：

```text
stack_pointer_at_call mod A = required_residue
```

不同 ABI 对 residue、返回地址是否已计入、red zone、shadow/home space、栈增长方向和动态对齐的规定不同。不能从某个平台记住一个常数后套用到所有 target。

## 8. ABI 是跨过程约束，也是优化边界

普通直接调用的可见动作至少包含：

- 读取实参和可能的内存；
- 覆盖 ABI 允许覆盖的寄存器；
- 改变栈、返回地址与可能的异常展开状态；
- 产生函数声明所允许的内存或外部副作用。

编译器可在证明安全时内联调用，从而消除部分 ABI 搬运；但保留下来的外部边界必须完全遵守 ABI。跨语言 FFI、手写汇编、错误的函数指针类型和不一致编译选项会绕开类型系统保护，使“每个文件单独编译成功”仍在运行时损坏寄存器或栈。

尾调用也不是把 `CALL` 换成 `JUMP` 那么简单。它必须确保：

- 当前函数不再需要自己的栈帧和局部清理；
- 参数位置能转成被调函数所需位置；
- ABI、异常/析构、返回值和安全机制允许复用返回路径；
- 间接目标与控制流保护约束得到满足。

## 9. 代码生成正确性的核心不变量

对每个基本块和调用边，可以检查：

1. **语义保持**：目标序列对所有已定义输入产生与 IR 相同的可观察行为；
2. **定义支配使用**：每个虚拟值在使用前沿合法路径被定义；
3. **类型与位宽**：截断、扩展、符号性、浮点舍入和向量 lane 语义明确；
4. **内存顺序**：volatile、atomic、fence、alias 与异常顺序没有被非法重排；
5. **控制流闭合**：每个块有合法终结指令，所有目标块存在；
6. **调用约定一致**：参数与返回位置匹配，寄存器保存责任和栈对齐满足 ABI；
7. **目标合法性**：指令、操作数组合、立即数、寻址模式和寄存器类别都可编码；
8. **元数据连续**：源位置、异常边、stack map、unwind/debug 所需信息没有无故丢失。

机器 IR verifier 能证明部分结构不变量，却不能证明整个目标序列与源程序语义等价。完整验证还要结合第 11 课的差分测试、性质测试、translation validation 或形式化方法：[[计算机知识/70-编译原理/11-优化正确性语义保持与验证测试|优化正确性、语义保持与验证测试]]。

## 10. 常见失败与适用边界

- **把目标无关优化写进一个 target pattern。** 会让语义判断散落在后端，也难以复用于其他 target。
- **把合法化当作无损格式转换。** 辅助函数调用可能引入调用 clobber、异常、浮点环境或运行时依赖。
- **只匹配值，不匹配副作用。** 复制或删除 load、call、atomic 会改变可观察行为。
- **立即数超范围仍硬编码。** 最终编码失败，或截断后悄悄生成错误常量。
- **混淆 signed 与 unsigned / ordered 与 unordered。** 比较和分支在负数或 `NaN` 上出错。
- **只看 ISA，不看 ABI。** 指令本身合法，但跨函数后参数、返回值、栈或保存寄存器错位。
- **假设所有聚合都走寄存器。** 大小、字段类别和 ABI 不同会改成拆分或间接传递。
- **过早固定 frame offset。** spill、动态栈对象、对齐和调用区尚未确定时，最终偏移还会改变。
- **以指令条数代替性能。** 一条复杂指令可能有更高延迟或资源压力；较长序列也可能并行得更好。代价模型在第 14 课展开。

## 练习

### 练习 1：区分阶段

把以下动作分别归入“目标无关优化、target lowering、指令选择、ABI lowering、寄存器分配、编码/重定位”，并解释理由：

```text
delete unreachable block
split unsupported 128-bit add into supported pieces
choose scaled-address load
put fifth integer argument on caller stack
assign virtual value v7 to physical register R2
leave a patch record for an unknown external symbol address
```

### 练习 2：手工 tile

对表达式：

```text
result = load_i32(base + index * 4 + 12) + 300
```

分别假设：

- Target A 有复合地址模式，算术立即数范围为 `[-128, 127]`；
- Target B 只有寄存器地址，算术立即数范围足以容纳 `300`。

为两个 target 写出概念化机器 IR，标出每个 tile 覆盖了哪些节点，并说明常量 `300` 或地址 `12` 何时必须额外物化。

### 练习 3：ABI 调用追踪

自行给定一个 toy ABI：两个整数参数寄存器、一个浮点参数寄存器、其余参数走栈；一个整数返回寄存器；`R0–R2` 为 caller-saved，`R3–R4` 为 callee-saved；调用点要求 16 字节对齐。然后 lowering：

```text
answer = f(integer_a, float_b, integer_c, integer_d)
```

画出调用前后位置表，并给出“若调用后仍需要 `integer_a`”时的保存决策。再故意少加一段 padding，计算调用点对齐余数并指出错误。

### 练习 4：找出不安全变换

判断下列选择何时不安全，并写出所缺前提：

```text
replace floating_compare_not_less with floating_compare_greater_or_equal
duplicate a load whose address may name volatile memory
replace checked multiply by wrapping shift
replace call followed by return with unconditional jump
```

## 成功标准

- 我能在一张图上指出 target-independent、target lowering、instruction selection、ABI lowering、register allocation 和 emission 的责任边界；
- 我能用 tiles 覆盖一个表达式树，并解释共享节点和副作用为何让真实问题超出简单树；
- 我能依据立即数与寻址限制，为两个概念 target 生成不同但等价的机器 IR；
- 我能按一份给定 ABI 放置参数和返回值，计算栈对齐，并解释 caller/callee-saved 的责任；
- 我能列出至少五项机器 IR 不变量，并明确结构合法不等于语义等价或运行性能已验证。

---

**上一站**：[[计算机知识/70-编译原理/12-运行时对象布局栈堆闭包异常与GC|运行时：对象布局、栈堆、闭包、异常与 GC]] · **下一站**：[[计算机知识/70-编译原理/14-寄存器分配指令调度与目标代价模型|寄存器分配、指令调度与目标代价模型]] · **实践**：[[计算机知识/80-实践/08-编译原理/06-指令选择寄存器分配与重定位/README|指令选择、寄存器分配与重定位实践]] · **返回 MOC**：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
