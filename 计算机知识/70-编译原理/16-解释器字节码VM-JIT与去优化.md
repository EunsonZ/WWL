---
type: lesson
domain: computer-science
stage: 3
status: ready
difficulty: 中级到进阶
estimated_minutes: 100
verified_on: 2026-09-04
topics:
  - interpreter
  - bytecode-vm
  - jit
  - inline-cache
  - deoptimization
  - osr
  - garbage-collection
tags:
  - computer-science/compiler
  - computer-science/runtime
  - computer-science/virtual-machine
---

# 解释器、字节码 VM、JIT 与去优化

一门语言“是解释型还是编译型”通常是错问题。同一实现可以先把源程序编译成字节码，再解释字节码，对热点 JIT 成机器码，又在假设失效时去优化回较低层级。有用的分类对象是**某个执行阶段**，而不是给整门语言贴唯一标签。

> [!info] 核验边界
> 本页的 VM/JIT 架构是跨实现的稳定模型。CPython 仅用来说明“字节码不必是可携带规范”：官方 `dis` 文档明确把 CPython bytecode 称为实现细节，并警告其可在 Python 版本之间变化。本页按 [Python `dis` 官方文档](https://docs.python.org/3/library/dis.html) 核对至 **2026-09-04**；不把某版本 opcode 表写成语言契约。

## 本课目标

学完后，你应能：

1. 区分 tree interpreter、stack/register bytecode VM、AOT 和 JIT；
2. 解释 verifier、dispatch 与 inline cache 各自解决什么问题；
3. 画出 tiering、guard、deoptimization 与 OSR 的状态转移；
4. 说明 code cache、GC 和调试器为何不能被当作 JIT 的外挂细节；
5. 用事件轨迹验收一个多层级 VM，而不只比较最终输出。

## 先修与连接

- 语法树与中间表示：[[计算机知识/70-编译原理/03-上下文无关文法AST-CST与歧义|文法、AST 与 CST]]、[[计算机知识/70-编译原理/07-中间表示Lowering与三地址码|中间表示与 Lowering]]
- 机器执行基础：[[计算机知识/30-计算机系统/06-指令系统汇编与程序执行|指令系统、汇编与程序执行]]
- 调用、栈帧与 ABI：[[计算机知识/30-计算机系统/03-ABI调用约定与静态动态链接|ABI、调用约定与链接]]
- 缓存成本：[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存局部性、带宽与延迟]]

## 1. 四种执行路线：不是四种语言

```text
source
  → parse / analyze
  → tree IR or bytecode IR
       ├─ tree interpreter
       ├─ stack/register VM interpreter
       ├─ AOT compiler → native/object code before deployment
       └─ JIT compiler → native code during execution
```

| 路线 | 直觉 | 主要优点 | 主要代价 |
| --- | --- | --- | --- |
| tree interpreter | 直接按 AST/语义树节点递归执行 | 实现直接，源位置和调试关系清楚 | 节点指针追踪、递归调用与类型分派开销大 |
| stack VM | 指令隐式从操作数栈取值 | 编码紧凑，前端生成简单 | 为相同表达式产生更多 push/pop 和 dispatch |
| register VM | 指令显式指定虚拟寄存器 | 指令数可更少，数据流更显式 | 指令编码可更宽，分配与验证更复杂 |
| AOT | 在运行前完成目标码生成 | 无热身编译停顿，产物易于部署与审计 | 很难利用本次运行的真实类型、值与路径 |
| JIT | 运行时按热度与反馈生成专用机器码 | 可对实际行为特化 | 编译时间、内存、停顿和去优化成为运行成本 |

AOT 和 JIT 不互斥：运行时本身可以是 AOT 编译的，应用模块可以预编译，某些热函数又可在运行期再特化。“有字节码”也不等于“没有编译”；源程序到字节码已是一次编译。

## 2. Tree interpreter：语义很直接，热路径却很散

```pseudo
evaluate(node, environment):
  match node.kind:
    LITERAL:
      return node.value
    ADD:
      left  = evaluate(node.left, environment)
      right = evaluate(node.right, environment)
      return language_add(left, right)
    IF:
      condition = evaluate(node.condition, environment)
      return evaluate(select_branch(condition), environment)
```

这个模型把语义分支与树结构几乎一对一地写出，很适合教学、工具语言或低频配置。但每个小操作都可能经过间接指针、宿主函数调用和节点类型分派，不利于指令缓存与分支预测。

把树压平成紧凑字节码可以减少对象追踪和调用层数，却不会自动改变语言语义。语义必须在前端、VM 和后续 JIT 之间保持一致。

## 3. Stack VM 与 register VM

对表达式 `result = (a + b) * c`，两种伪指令可写成：

```pseudo
# stack VM
LOAD a
LOAD b
ADD
LOAD c
MUL
STORE result

# register VM
ADD  temp0, a, b
MUL  result, temp0, c
```

Stack VM 的指令隐式读写操作数栈；register VM 把数据流更多写进操作数。两者都可实现词法环境、闭包、异常和对象模型，差别不只是“有没有一个数组叫 stack”，而是指令集如何表达中间值与生命期。

### CPython bytecode 的边界

`dis` 能用来分析 CPython 某个版本的 bytecode，但这不代表：

- opcode 编号、名称、宽度或 cache 布局是 Python 语言规范；
- 一份持久化字节码能在任意 Python VM 或版本跨期执行；
- 观察到的指令序列等于源级语义，或适合用作安全策略边界。

**Python 语言语义**与 **CPython 字节码格式**是两层契约。若需要可持久、可交换的 IR，必须另外定义版本、兼容性、验证与升级策略。

## 4. Verifier：拒绝坏程序形状，不证明业务正确

字节码来自缓存、网络、插件或不同版本前端时，执行前的 verifier 是信任边界之一：

```pseudo
verify(function):
  require function.format_version is supported
  require every opcode is known
  require every jump target starts an instruction
  require every constant/local index is in range
  propagate abstract stack_height and value_kind over control_flow
  require merge points have compatible abstract states
  require exception regions and terminators are well formed
  accept structure, not behavioral correctness
```

Verifier 可以拒绝跳入指令中间、栈下溢、非法局部变量索引或不一致的合流状态；它不会证明算法输出正确、程序终止、资源有界，也不会把未受信任代码自动变成安全代码。即使结构合法，VM 仍需要沙箱、能力限制和资源预算。

## 5. Dispatch：解释器的紧内环

```pseudo
while frame.state is RUNNING:
  instruction = fetch(frame.program_counter)
  frame.program_counter = next_address(instruction)
  dispatch instruction.opcode:
    LOAD: execute_load(frame, instruction)
    ADD:  execute_language_add(frame, instruction)
    JUMP: frame.program_counter = instruction.target
```

Dispatch 可以是 switch、间接跳转、生成的 handler 表，或把多条常见指令合成 superinstruction。这些是实现选择；它们的正确性契约是对程序状态产生与语言语义一致的转移。

不要用“每条指令更快”代替测量。指令密度、handler 大小、间接分支可预测性、对象分配与缓存局部性会一起决定结果。

## 6. Inline cache：记录某个调用点看到了什么

对动态属性读取，通用路径可能需要查询对象形状、原型/类、描述符和可见性规则。Inline cache 把某个程序点的历史变成可验证快路：

```pseudo
load_property(site, receiver, name):
  if receiver.shape == site.cached_shape:
    return receiver.slot[site.cached_offset]
  value, shape, offset = generic_lookup(receiver, name)
  update_cache(site, shape, offset)
  return value
```

- **monomorphic**：点位稳定看到一种 shape/type；
- **polymorphic**：用小型候选链覆盖少数形状；
- **megamorphic**：形状太多，继续扩大线性快路反而更贵，应回到通用或共享缓存策略。

Cache 必须有失效契约。若类布局、方法或原型链可变，系统要么改变 shape/version，要么主动清除依赖的 cache/code，不能让旧 offset 悄悄继续命中。

## 7. Tiering：用编译预算换未来执行时间

```text
cold code
  → interpreter
  → quickened / baseline tier
  → optimizing tier
  → deopt to baseline/interpreter when assumptions fail
```

层级越高，通常需要更多 profile、编译时间与 deopt metadata，期望从更多内联、常量化、类型特化与边界检查消除中收回成本。热度阈值不是语义，而是延迟、吞吐、代码尺寸和能耗之间的产品策略。

> [!warning] JIT 不保证更快
> 短任务可能在收回编译成本前已结束；高多态路径可反复 deopt；过多专用版本会膨胀 code cache 并伤害 instruction cache。验收时同时记录预热、编译停顿、稳态吞吐、deopt 数和内存。

## 8. Guard 与 deoptimization：特化必须可撤销

优化代码往往依赖“该调用点仍是整数”、“类版本未变”、“数组长度足够”等运行时假设。Guard 将假设变成显式检查；deoptimization 在失败时重建较低层级能理解的状态：

```pseudo
optimized_add(frame, left, right):
  guard kind(left)  == SMALL_INTEGER else deopt(id = 12)
  guard kind(right) == SMALL_INTEGER else deopt(id = 13)
  result = unchecked_integer_add(left, right)
  guard result did not overflow else deopt(id = 14)
  return result

deopt(id):
  metadata = deopt_table[id]
  rebuild inlined_frames from optimized_registers and constants
  restore source_position, locals, operand_stack, exception_state
  resume at metadata.baseline_location
```

去优化元数据要说清每个源级局部值在哪里：机器寄存器、栈、常量，或需按公式重建。只会“跳回解释器”不够；如果不能恢复可观察状态，语义已被改变。

## 9. OSR：在函数尚未返回时换层

若一个冷函数进入了极长循环，只在下次调用才使用 JIT 代码会错过主要热点。On-stack replacement（OSR）允许在循环回边等安全点把正在执行的 baseline/interpreter frame 映射到优化 frame：

```pseudo
at_loop_header(frame):
  increment loop_counter
  if loop_counter reaches optimization_threshold:
    optimized_entry = compile_osr_entry(loop_header, observed_state)
    if optimized_entry is ready and entry_guards_hold(frame):
      transfer_live_values(frame, optimized_entry)
      continue loop in optimized_code
```

OSR 与 deopt 方向相反但共享问题：两种 IR/frame 之间的 live value、异常状态、程序位置和 GC 可见性必须可精确映射。

## 10. Code cache 与失效：生成代码也是受管资源

Code cache 不是一个可无限追加的 byte array。它至少需要跟踪：

- code object 与源函数/字节码版本的对应；
- 依赖的 shape、类、常量、嵌入对象与调用目标；
- stack map、safepoint、deopt table、异常表与源位置映射；
- 代码尺寸、最后使用、执行中引用和可回收条件。

失效时不能立刻释放仍在某线程栈上执行的代码；可用版本号、依赖链、safepoint 协议与延迟回收区分“不再允许新进入”和“已可物理回收”。W^X 等可执行内存政策也是部署边界；不能假设任意目标环境都允许运行时产生并执行代码。

## 11. GC 与 JIT：所有活引用都必须被看见

解释器中的对象引用常集中在明确的 frame/stack 数组。JIT 后，引用可能在机器寄存器、native stack、嵌入代码的常量或已标量替换的虚拟对象中。因而运行时需要：

- 在 safepoint 有精确或保守的 root/stack map；
- 在移动 GC 更新嵌入或寄存器中的引用；
- 让 JIT 写操作遵守代际/并发 GC 的 write barrier；
- 在 deopt 材料化对象时保留 identity、顺序与异常语义。

反例：“优化器证明对象不用分配，所以 GC 不用知道”是不完整的。如果调试、异常或 deopt 会让该对象变得可观察，就必须有按语义材料化它的信息。

## 12. 调试与剖析：用户看见的不是机器码地址

优化可内联多层调用、删除局部变量、复制循环体或重排指令。调试契约要先定义哪些行为必须可观察：

- source position 如何映射到 bytecode 和 native PC；
- 内联函数如何重建为逻辑 stack trace；
- 断点会使现有代码失效、进入可调试 tier，还是依靠 safepoint；
- 被优化掉的局部值是“不可用”，还是可从 deopt metadata 重建；
- profiler 时间应归属给生成代码、逻辑函数，还是 JIT 编译器。

“打开 debugger 后变慢”可能是预期的语义/可观察性取舍，但必须明示说明，不能让用户误把 debug 测量当稳态产品性能。

## 13. 一条完整例子：动态加法热循环

```pseudo
source loop:
  repeat many times:
    total = total + item.value

baseline observations:
  loop_header count becomes hot
  property site mostly sees Shape_ListItem_V3
  add site mostly sees SMALL_INTEGER

optimized version:
  OSR entry maps total, item, iterator_index
  guard item.shape == Shape_ListItem_V3
  load value from cached slot
  guard total and value are SMALL_INTEGER
  perform checked integer addition
  guard no overflow

exceptional iteration:
  item has Shape_CustomProxy
  shape guard fails
  rebuild logical frames and operand state
  resume generic property lookup at baseline tier
  record deopt reason without changing program result
```

这条轨迹同时覆盖 inline cache、tiering、guard、OSR 和 deopt。正确性验收不能只比较常见输入：还要触发 shape 变化、整数溢出、异常、GC 和断点，确认返回值、异常位置和可观察副作用与无 JIT 路径一致。

## 14. 反例清单

1. **“字节码就是跨平台稳定格式”**：有些 VM 会把它做成版本化文件格式，CPython bytecode 则明确是实现细节。
2. **“通过 verifier 就是安全代码”**：结构合法不阻止无限循环、资源耗尽或获取本不该有的能力。
3. **“命中 inline cache 就不用失效”**：快路之所以正确，正是因为 guard/version 证明当前状态仍匹配。
4. **“去优化是 JIT 失败”**：在推测优化中，可正确恢复是设计能力；真正问题是错误、频繁震荡或成本失控。
5. **“基准只需一个最终 ops/s”**：这会隐藏启动、热身、编译停顿、内存与长尾 deopt。

## 15. 练习：设计一台可去优化的小 VM

不写真实机器码，只交付伪指令、状态表与轨迹。

1. 定义 `CONST`、`LOAD_LOCAL`、`LOAD_PROPERTY`、`ADD`、`JUMP_IF_FALSE`、`RETURN` 六类伪指令，选择 stack 或 register VM；
2. 写出 verifier 检查的结构不变量；
3. 为 `LOAD_PROPERTY` 设计 monomorphic cache 及 shape version 失效策略；
4. 定义 interpreter → baseline → optimized 的热度条件；
5. 选一个循环头作 OSR 入口，列出 live values；
6. 设计两个 guard 失败场景，展示如何重建 logical frames；
7. 标出 GC safepoint、root map、source position 和 code-cache 回收条件。

### 成功标准

- verifier 能拒绝至少一个栈/索引错误和一个非法跳转；
- 常见输入轨迹至少命中一次 inline cache 并进入优化 tier；
- 反例轨迹至少触发一次 deopt，恢复后与纯解释路径的值、异常和副作用顺序一致；
- 报告分开 cold start、warm-up、steady state、compile pause、deopt count 和 code-cache size；
- 能解释一个“不 JIT 反而更好”的工作负载。

## 16. 官方来源与延伸阅读

- [Python `dis` — Disassembler for Python bytecode](https://docs.python.org/3/library/dis.html)：CPython bytecode 的分析入口与“实现细节”边界。
- 下一课使用 LLVM/MLIR 官方资料将“虚拟机执行”接到“多层 IR 与 progressive lowering”。

## 导航

- 上一站：[[计算机知识/70-编译原理/15-目标文件符号重定位链接与装载|目标文件、符号、重定位、链接与装载]]
- 下一站：[[计算机知识/70-编译原理/17-LLVM-IR-Pass与MLIR方言-Lowering|LLVM IR、Pass 与 MLIR 方言 Lowering]]
- 返回：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


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
