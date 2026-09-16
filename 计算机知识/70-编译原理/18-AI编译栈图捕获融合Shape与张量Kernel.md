---
type: lesson
domain: computer-science
stage: 4
status: ready
difficulty: 中级到进阶
estimated_minutes: 110
verified_on: 2026-09-04
topics:
  - ai-compiler
  - graph-capture
  - dynamic-shape
  - operator-fusion
  - memory-planning
  - autotuning
  - tensor-kernel
  - torch-compile
  - triton
tags:
  - computer-science/compiler
  - computer-science/ai-systems
  - computer-science/gpu
  - computer-science/tensor-kernel
---

# AI 编译栈：图捕获、融合、Shape 与张量 Kernel

AI 编译不是“把 Python 换成 CUDA”的单次翻译。它通常在 eager 执行的动态语义、可捕获图、张量/循环 IR、融合 kernel 和具体设备之间建立一系列可验证契约。各层需要同时回答：哪些操作可以重排？哪些 shape 可专用化？哪些数值差异允许？数据在哪台设备、什么 layout 和内存空间中？

> [!info] 稳定模型与快速变化案例
> “eager → graph capture/AOT/JIT → tensor/loop IR → fused kernel → target”是本页用来思考不同系统的稳定模型，不是声称所有产品都有相同组件名。`torch.compile` 和 Triton 仅作为快速变化案例，已按 [torch.compile 官方 API](https://docs.pytorch.org/docs/stable/generated/torch.compile.html)、[PyTorch Compiler Programming Model](https://docs.pytorch.org/docs/stable/user_guide/torch_compiler/compile/programming_model.html) 与 [Triton 官方文档](https://triton-lang.org/main/) 核对至 **2026-09-04**。不在本页承诺某版本 API、backend、图中断集合、支持设备或性能结果。

## 本课目标

学完后，你应能：

1. 画出 eager、graph capture、AOT/JIT、tensor/loop IR、kernel 与 target 的端到端关系；
2. 解释 guard、recompile、dynamic shape 与 graph break 如何共同界定可复用图；
3. 区分算子融合、layout 选择、memory planning 与 autotuning；
4. 识别 alias、side effect、numerics 和 device boundary 对重排/融合的限制；
5. 设计同时检查正确性、重编译稳定性、内存、延迟和稳态吞吐的验收方案。

## 先修与连接

- 张量与 shape：[[AI/10-机器学习与深度学习基础/03-张量形状广播与批处理|张量形状、广播与批处理]]
- 计算图与自动微分：[[AI/10-机器学习与深度学习基础/04-计算图与自动微分|计算图与自动微分]]
- 多层 IR 与 lowering：[[计算机知识/70-编译原理/17-LLVM-IR-Pass与MLIR方言-Lowering|LLVM IR、Pass 与 MLIR 方言 Lowering]]
- GPU 执行：[[计算机知识/40-并行与异构计算/01-CUDA/01-CPU与GPU异构执行模型|CPU 与 GPU 异构执行模型]]
- Kernel 映射：[[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|Reduction、Softmax 与 GEMM]]

## 1. 端到端稳定模型

```text
eager program
  → graph capture / tracing / staged frontend
      → graph segments plus guards and fallback boundaries
  → AOT and/or JIT compilation
      → graph/tensor IR
      → structured loop/schedule IR
      → fused kernel IR
  → target lowering, code generation and runtime launch
      → CPU / GPU / accelerator execution

runtime feedback:
  input metadata → guard check → cache hit or recompile/fallback
  measurements   → schedule/autotuning choice → cached artifact
```

实际系统可合并、跳过或复制这些层；例如某些算子直接调用预编译 library kernel，某些 graph segment 在运行期生成专用 kernel。分层的价值在于定位决策与证据：捕获错误、张量语义错误、schedule 选择不佳和 target codegen 错误不是同一问题。

## 2. Eager 与 graph capture：要捕获的是语义子集

Eager 模式通常按宿主语言执行顺序立即调度操作，中间结果与副作用在宿主语言中可观察。Graph capture 尝试把一段运算变成可整体分析的图，但必须回答：

- 张量值与宿主值如何交流？
- 基于数据的控制流是图内 op，还是需要回到 eager？
- 容器变异、I/O、随机数、全局状态、异常和自定义对象的顺序如何保持？
- 某个值被当作常量时，什么 guard 证明本次调用仍可复用该图？

```pseudo
capture(program, example_inputs):
  graph = empty
  assumptions = empty
  for each observable_step in program:
    if step has modeled graph semantics:
      append corresponding operation to graph
      record required assumptions
    else:
      end current graph segment
      preserve step in eager fallback region
  return graph_segments, guards(assumptions)
```

**Graph break** 不必是 bug；它是“当前捕获系统不把这一步包含在当前图中”的边界。它会限制跨边界融合、增加调度与缓存成本，但用错误模型强行捕获副作用更糟。优先使用诊断找出边界原因，再决定改程序、扩展捕获语义，还是接受 fallback。

## 3. AOT 与 JIT：“何时知道什么”

| 时机 | 可用信息 | 优势 | 风险 |
| --- | --- | --- | --- |
| ahead of time | 模型/程序结构、声明 shape 范围、目标设备集 | 编译成本移出关键路径，易产物审计 | 对实际 shape、stride、数据分布与设备状态知道较少 |
| just in time | 本次运行的 dtype、shape、stride、常量与设备 | 可生成更专用的 kernel/schedule | 首次编译、重编译、cache 内存与长尾停顿 |

很多系统是混合的：前向/反向图可在模型准备期生成，kernel 却可针对实际 shape 在首次触发时编译。验收必须把 capture time、compile time、autotune time 与 execution time 分开。

## 4. Guard、cache 与 recompile

编译产物只对某个前提集合正确。Guard 是这些前提的运行时判定：

```pseudo
compiled_call(inputs, program_state):
  signature = abstract_metadata(inputs, program_state)
  for artifact in cache.lookup(candidate_key(signature)):
    if every artifact.guard holds:
      return artifact.run(inputs)

  if policy permits a new specialization:
    artifact = compile_for(signature)
    cache.insert(artifact)
    return artifact.run(inputs)

  return eager_or_generic_fallback(inputs)
```

Guard 可检查 dtype、rank、shape 关系、stride/layout、device、requires-grad 状态、宿主常量、函数/模块版本或其他捕获假设。实际 guard 集合是实现契约，不应从一次日志推导为所有版本的永久列表。

重编译不一定错：少量有限 specialization 可能是预期策略。危险信号是：同一路径因不受控的 shape/宿主值不断生成新版本，cache 增长，compile time 压过 execution time。需记录 guard-failure reason、产物数、命中率、重编译上限和 fallback 行为。

## 5. Dynamic shape：动态不等于无约束

将每个维度完全常量化可生成高度专用代码，却可对每个新长度重编译。完全通用的动态 kernel 可减少版本，却可丢失 vector width、tile、对齐和静态内存规划机会。中间选择是用 **symbolic dimension + constraint** 表示可复用区域：

```pseudo
symbolic_shape_contract:
  batch = symbolic_positive_integer
  hidden = constant 4096
  sequence = symbolic_integer in supported_range
  require sequence is compatible with selected_tile_or_remainder_path
  require left.sequence == mask.sequence
```

符号 shape 不会自动证明所有变换合法。分块、向量化、重塑、广播与 buffer 尺寸都需要可证明关系，不能证明时应保留 runtime check、remainder path 或 fallback，而不是悄悄假设整除。

## 6. Tensor IR 与 loop/schedule IR

Tensor/graph IR 适合表示整个运算的数据依赖、shape、dtype 与高层 op。Loop/schedule IR 开始回答“怎样计算”：分块、循环顺序、并行映射、向量化、缓存与数据搬运。

```pseudo
tensor_semantics:
  output = activation(input * scale + bias)

scheduled_semantics:
  partition output index_space into tiles
  map tiles to parallel programs
  load input, scale, bias using explicit layout rules
  compute multiply, add, activation without materializing intermediates
  mask or handle boundary elements
  store output
```

从第一层到第二层不是简单展开：它需要 target 资源模型、shape 约束、layout 契约与数值语义。同一张量表达式可有多个合法 schedule。

## 7. Fusion：减少中间物化，不是把图全粘在一起

生产者—消费者融合可让中间值留在寄存器/片上存储或直接被消费，减少 kernel launch 和全局内存往返。但融合会受以下边界限制：

- 数据依赖和副作用顺序；
- reduction 的并行结构与同步范围；
- 注册表/片上存储占用导致的 occupancy 下降或 spill；
- 不同 op 偏好的 tile/layout 冲突；
- 复制计算的代价是否小于中间物化；
- library kernel/device boundary 或难以内联的外部调用。

反例：把一个大 reduction、多个广播与后续复杂算子强行融成超大 kernel，可能因资源压力、同步和重复计算变慢。“更少 kernel”是指标，不是目标函数。

## 8. Layout：逻辑 shape 不告诉你字节怎样放

相同逻辑 shape 可以有不同 stride、分块、向量 packing、地址空间和设备分布。Layout 选择会影响：

- 连续/coalesced 访存与 cache line 利用；
- vector/tensor 指令所需对齐和分块；
- transpose/repack 是否需要显式物化；
- producer 输出 layout 是否正好是 consumer 的高效输入；
- 多设备 shard 和 collective 的通信模式。

“去掉一个 transpose op”可能是 layout propagation 成功，也可能只是把转换成本藏到后续 kernel。验收要看物理访存、生成的转换与端到端时间，不只数 IR op。

## 9. Memory planning：复用缓冲前先证明 lifetime 不冲突

```pseudo
memory_plan(graph):
  compute use intervals under chosen schedule
  preserve externally visible outputs and saved values
  group buffers by device, address_space, size, alignment, layout
  reuse storage only when lifetimes do not overlap
  insert required synchronization across asynchronous streams
  account for aliases and views
  emit peak-memory estimate and runtime guards
```

一个 view 可与 base storage alias；in-place 更新可影响所有别名；自动微分可要求保存中间值到反向；异步设备操作在宿主返回时也许尚未读完缓冲。因此 lifetime 是调度、alias、自动微分与同步共同决定的，不是简单的“最后一个图用户后立即释放”。

[[AI/20-LLM/50-实现/06-GGML张量计算图分配器与Backend|GGML 的张量图、分配器与 Backend]]提供了一个具体 LLM 执行引擎案例：它让读者观察 view、buffer 生命周期、backend placement、跨后端 copy 与调度证据。这个案例可帮助检验本节抽象，但 GGML 的内部图和分配策略不是通用编译 IR 或 memory-planning 语义的权威定义。

## 10. Autotuning：在可认定前提下测量多个合法实现

Autotuning 可在 tile size、num warps/threads、pipeline stages、算法变体或 library/kernel 之间测量选择。一个可复现的 tuner 契约需要：

```pseudo
autotune(problem_signature, target_signature):
  candidates = generate_only_legal_schedules()
  for candidate in candidates:
    compile candidate under fixed toolchain identity
    validate candidate against reference and tolerance policy
    benchmark after warmup with synchronized boundaries
    record distribution, not only best single sample
  choose winner under latency, memory and determinism constraints
  cache result with all validity guards
```

Cache key 至少要考虑影响正确性/性能的 shape、dtype、layout、device/architecture、工具链与数值模式。在共享生产设备上无界自动试验会制造长尾延迟与资源竞争；需要预算、隔离、超时和通用 fallback。

## 11. 四类不可跨过的语义边界

### Alias：两个张量名称可能共享存储

```pseudo
base = allocate_buffer()
left_view  = view(base, first_half)
right_view = view(base, overlapping_half)
write left_view
read right_view
```

如果编译器错误假设两个 view 不 alias，就可把 read 移到 write 前或复用仍在观察的 buffer。别名未知时要么保守排序，要么生成 runtime guard 区分不重叠快路与通用路径。

### Side effect：图边不只是张量数据依赖

I/O、随机数状态、in-place 更新、全局计数器、异常、collective 与同步操作都可形成 effect/order 边。若 IR 不表达，优化器就无法区分可重排纯计算和必须保序副作用。

### Numerics：数学等价不一定浮点等价

融合和向量化可改变运算次序、中间精度、舍入与 reduction 树。可重结合、允许较低精度、确定性要求和 NaN/Inf/signed-zero 行为应是显式 numeric policy，不能从“AI 大概能容忍”推导。数值前提见 [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]]。

### Device boundary：调用完成不等于设备完成

CPU/GPU/加速器间的传输、队列、stream、event 与同步决定真实依赖。跨设备 fusion 不能只用单一图边宣称“粘在一起”；它可能需要数据传输、同步或 target-specific collective。异步测量必须用正确完成边界，否则宿主只测到 launch time。参见 [[计算机知识/40-并行与异构计算/01-CUDA/01-CPU与GPU异构执行模型|CPU 与 GPU 异构执行模型]]。

## 12. 快速变化案例：`torch.compile`

`torch.compile` 可用来观察编译包装如何在运行时捕获可编译区域、为前提建立 guards、缓存产物，并在前提变化时重编译或 fallback。官方 programming model 把 graph breaks、guards/recompilations 与 dynamic shapes 作为理解编译行为的核心边界。

但本页不把它写成版本 API 手册。现场使用时应核对目标 PyTorch 版本的：

- 调用参数与 mode/backend 契约；
- 完整图、graph break 和 fallback 的诊断方式；
- dynamic shape 策略、guard 日志与 recompile 限制；
- 分布式、自定义 op、训练/推理和特定设备的支持状态；
- 首次编译、缓存命中和稳态的分层基准。

```pseudo
torch_compile_case_study:
  run eager reference on controlled inputs
  compile the callable under a pinned environment
  record graph segments and break reasons
  vary shapes, strides, dtypes and selected host values
  record guard failures, recompilations and fallbacks
  compare outputs, effects and gradients under explicit tolerance
  report cold and warm latency separately
```

## 13. 快速变化案例：Triton

Triton 是编写高效自定义张量/GPU kernel 的语言与编译工具链案例。它适合把“按 program instance 映射数据块、显式 load/store/mask、选择 block size 和调优配置”与手写低层线程细节区分开。官方文档同时包含 Python API、Triton language 语义、教程、调试与 Triton MLIR dialects/ops；具体表面会快速变化。

```pseudo
fused_elementwise_kernel:
  program_id = current_parallel_program
  offsets = program_id * BLOCK + local_range(BLOCK)
  mask = offsets < number_of_elements
  x = load input at offsets where mask
  y = activation(x * scale + bias)
  store y at offsets where mask
```

这个伪 kernel 只说明映射直觉，不是可运行 Triton 代码。BLOCK、数据排布、边界 mask、精度、设备资源和调优选择都要在目标版本与硬件上验证。自定义 kernel 的 CPU/toy 结果不证明 GPU 编译、正确同步或性能。

## 14. 一条完整例子：bias + activation + reduction

```pseudo
eager_semantics:
  shifted = input + bias
  activated = activation(shifted)
  output = reduce_sum(activated, axis = last_dimension)

capture_contract:
  input and bias are tensors on same supported device
  dtypes are compatible under explicit promotion rules
  bias is broadcast-compatible with input
  no observable mutation aliases shifted or activated
  numeric policy permits selected reduction ordering

symbolic_shapes:
  input shape = [batch, sequence, hidden]
  bias shape = [hidden]
  batch and sequence may vary within guarded constraints
  hidden belongs to supported specialization set

fusion_candidates:
  candidate_A = fuse add and activation, materialize before reduction
  candidate_B = fuse add, activation and reduction in one kernel
  candidate_C = use a library reduction after fused producer

selection:
  reject illegal candidates by alias/effect/numeric checks
  benchmark legal candidates for representative shape buckets
  include compile time, peak memory and deterministic-mode requirement
  cache winner under device, layout, dtype, shape and toolchain guards
```

Candidate B 的 kernel 更少，却可因 reduction 资源需求、跨 block 同步或寄存器压力不如 A/C。编译器要在法律性过滤后选择，不能让 autotuner 用性能测量掩盖错误结果。

## 15. 反例清单

1. **“抓到图就等于编译成功”**：图还要通过 lowering、target codegen、runtime launch 与输出/副作用验收。
2. **“dynamic shape 永不重编译”**：符号约束也有适用域；超出约束、layout/device 改变或新分支都可触发新产物。
3. **“融合越多越快”**：资源压力、reduction、layout 冲突与复制计算可使大 kernel 更慢。
4. **“数学上同一个公式就能随意重排”**：浮点舍入、特殊值、低精度与确定性会改变结果。
5. **“宿主计时结束就是 GPU 计算结束”**：异步 launch 需要正确 event/同步边界才能测执行时间。
6. **“autotuning 最快单次值是真理”**：噪声、预热、频率、共享资源与错误候选都可伪造 winner。

## 16. 练习：设计一个可诊断的张量编译管线

对“张量线性变换 → bias → activation → reduction”设计伪管线：

1. 写 eager reference 的操作、可观察副作用和 numeric policy；
2. 列出 capture 能接受的操作与两个 graph-break 边界；
3. 为 dtype、device、shape 关系、stride/layout 和宿主常量设计 guards；
4. 设计一个静态 shape 专用版本和一个符号 shape 版本；
5. 给出至少三个 fusion/schedule 候选，先过滤不合法候选，再 autotune；
6. 计算 buffer lifetime，标出 view alias、saved-for-backward 和异步完成点；
7. 设计 shape 分布漂移后的 recompile 上限、泛化与 fallback 策略；
8. 分开报告 capture、compile、autotune、cold run、warm run 和 peak memory。

### 成功标准

- 能从 eager 一直追踪到 target kernel，每层都有明确输入、输出和 verifier/诊断；
- 至少一个 graph break 被解释为正确性边界，而不是笼统称为失败；
- 至少一个 shape 变化命中原符号版本，另一个超出 guard 后按策略重编译或 fallback；
- fusion 前已检查 alias、side effect、numerics 和 device boundary；
- autotuning 只比较已证明合法的候选，缓存键包含 target/toolchain 身份；
- eager 与 compiled 路径在值、梯度、异常和可观察副作用上按显式容差策略一致；
- 报告没有用 toy/CPU 成功替代真实 GPU/target 编译与性能证据。

## 17. 官方来源

- [`torch.compile` 官方 API](https://docs.pytorch.org/docs/stable/generated/torch.compile.html)：当前 API 入口；使用时以目标版本为准。
- [PyTorch Compiler Programming Model](https://docs.pytorch.org/docs/stable/user_guide/torch_compiler/compile/programming_model.html)：graph breaks、guards/recompilations 与 dynamic shapes 等运行模型。
- [Triton 官方文档](https://triton-lang.org/main/)：Triton language、API、教程、调试与 IR dialect 入口。

## 导航

- 上一站：[[计算机知识/70-编译原理/17-LLVM-IR-Pass与MLIR方言-Lowering|LLVM IR、Pass 与 MLIR 方言 Lowering]]
- 延伸：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]
- 返回：[[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
