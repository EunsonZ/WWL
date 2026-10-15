---
type: lesson
stage: 3
status: ready
difficulty: 进阶
estimated_minutes: 110
topics:
  - distributed-training
  - data-parallel
  - tensor-parallel
  - pipeline-parallel
  - fsdp
  - deepspeed
  - megatron
domain: artificial-intelligence
tags:
  - ai/llm/training
  - ai/distributed-systems
---

# 分布式训练、FSDP、DeepSpeed 与 Megatron

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 数据并行、参数/状态分片和张量并行改变的对象不同；它们不会自动解决不等长样本的目标加权问题。先证明全局梯度语义，再比较资源和通信。 深化与验证：[[AI/12-PyTorch/08-DDP全局目标通信与分片边界|DDP全局目标通信与分片边界]]；[[AI/12-PyTorch/09-性能剖析编译动态形状与内存账本|性能剖析编译动态形状与内存账本]]。


## 本课目标

- 区分 data parallel、state sharding、tensor parallel 与 pipeline parallel；
- 用全局 batch、每 rank 状态字节和通信点解释“更多 GPU”为什么不一定更快；
- 说明 PyTorch FSDP、DeepSpeed/ZeRO 与 Megatron 的职责层次，而不是把三个名字当成同类开关；
- 为一个 DP × TP × PP 拓扑计算 world size、global batch 和简化 pipeline bubble；
- 设计分布式 checkpoint、失败恢复、拓扑记录与资源上限；
- 知道什么时候单机优化比引入多维并行更合理。

## 先修（第一次使用）

- GPU、host/device、显存、kernel 与线程层次：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]；
- 梯度如何产生：[[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]；
- optimizer state 为何存在：[[数学/40-微积分与优化/04-SGD-Momentum-Adam与AdamW|SGD、Momentum、Adam 与 AdamW]]；
- 单进程 checkpoint 与恢复：[[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]]。

本页不推导梯度和优化器公式，只追踪它们分布在哪些 rank、何时通信和怎样保存。

## 直觉：切不同东西，解决不同瓶颈

有四种常见“切法”：

- **data parallel（DP）**：每个副本处理不同 micro-batch，模型计算相同；解决吞吐，但普通复制不解决单卡模型/状态内存。
- **state sharding**：把参数、梯度或 optimizer state 分散保存，需要计算时再通信；主要解决状态内存。
- **tensor parallel（TP）**：把一层内部的大矩阵运算切到多设备；解决单层放不下或单层计算过大。
- **pipeline parallel（PP）**：把不同层放在不同 stage，让多个 micro-batch 像流水线一样流过；解决整模型深度放不下。

这四者可以组合，但每加一维都会增加通信、调度、checkpoint 和排错复杂度。正确顺序是先说出瓶颈，再选切法。

## 精确定义：分布式基本词汇

- **process/rank**：一个参与分布式作业的进程及其全局编号；常见是一进程对应一 GPU，但不是定义要求。
- **world size**：全部 rank 数。
- **process group**：参与某类 collective 的 rank 子集，例如 data-parallel group 或 tensor-parallel group。
- **collective**：一组 rank 共同参与的通信，如 all-reduce、all-gather、reduce-scatter、broadcast。
- **replica**：拥有等价模型计算语义的一组参数副本；分片后一个 replica 可能由多个 rank 共同组成。
- **global batch**：一次 optimizer update 在所有 data-parallel replicas 上合计处理的样本数。
- **communication topology**：rank 到节点、GPU、互连和 process group 的映射；同样 world size 在不同互连上性能可完全不同。

## Data Parallel：切 batch

每个 DP replica：

1. 拿到不同 micro-batch；
2. 用等价参数做前向/反向；
3. 在 optimizer step 前同步梯度或等价更新信息；
4. 得到一致参数，继续下一步。

若每个 DP rank 的 micro-batch 序列数是 $B_\mu$、累积次数 $A$、DP 副本数 $D$，则

$$
B_{global}=B_\mu A D.
$$

增加 $D$ 会放大全局 batch。若保持学习率和 token budget 不变却忘了调整 step 数，训练轨迹就已改变；多卡速度比较也必须在相同有效 token 和质量目标下进行。

### 普通复制式 DP 的内存边界

设参数、梯度、optimizer state 的总字节分别为 $M_p,M_g,M_o$。普通复制式 DP 每个 rank 都要承受近似

$$
M_p+M_g+M_o+M_{act}+M_{buffer}.
$$

它可以加快吞吐，却没有把这三类持久状态除以 $D$。梯度同步通常需要与梯度规模同量级的 collective 流量；梯度累积能减少同步频率，但会改变有效 batch 与优化设置。

## ZeRO 与 FSDP：切训练状态

### ZeRO 的三个概念阶段

以下是稳定职责，不绑定某个版本参数名：

- **stage 1**：分片 optimizer state；参数和梯度仍复制。
- **stage 2**：再分片梯度；参数仍复制。
- **stage 3**：再分片参数；计算某个模块时按需 gather，并在适当边界重新分片。

若忽略激活、通信 buffer、临时 gather、碎片与不均衡，理想每 rank 稳态账本近似为：

| 方案 | 每 rank 参数/梯度/优化器状态 |
| --- | --- |
| 普通 DP | $M_p+M_g+M_o$ |
| ZeRO-1 | $M_p+M_g+M_o/D$ |
| ZeRO-2 | $M_p+(M_g+M_o)/D$ |
| ZeRO-3 | $(M_p+M_g+M_o)/D$ |

这不是峰值显存承诺。stage 3/FULL sharding 在层计算前后会 all-gather/reduce-scatter，预取策略和大层会产生峰值；激活不会因为状态分片自动除以 $D$。

### FSDP 的职责

**FSDP（Fully Sharded Data Parallel）**是 PyTorch 中围绕模块包装、参数/梯度/optimizer state 分片、按需 materialization、混合精度和分片 checkpoint 的分布式训练机制。概念上，它可实现从“只分梯度/optimizer”到“参数也完全分片”的策略。

FSDP 不是：

- tensor parallel 的同义词；单个被 gather 的层若仍放不下，就需要 TP 或模型结构调整；
- 自动的 pipeline scheduler；
- 自动解决激活峰值、数据污染或训练稳定性的按钮；
- 跨任意版本/拓扑都可直接加载的 checkpoint 保证。

模块 wrapping 粒度很关键：过大导致 gather 峰值，过小导致过多通信和调度开销。参数共享、tied embeddings、冻结参数和 LoRA 插入点要在分片前后保持语义一致。

### DeepSpeed 与 ZeRO 的职责

**DeepSpeed**是一个训练运行时/优化库，ZeRO 是其中的状态分片家族。其能力边界可包括优化器与状态管理、CPU/NVMe offload、pipeline parallel、混合精度和训练引擎集成；具体支持、配置名和组合限制随版本变化。

因此：

- “用了 DeepSpeed”没有说明是 ZeRO 哪一阶段、是否 offload、是否 PP；
- offload 把压力移到主存、PCIe/NVMe 和 I/O，不是免费显存；
- FSDP 与 ZeRO-3 都能解决全状态分片，但属于不同集成与 checkpoint 生态，不能把配置互换；
- 选择要比较目标框架、模型支持、checkpoint、运维能力和实测通信，而不只比较营销吞吐数字。

## Tensor Parallel：切一层矩阵

TP 把同一线性层/attention/MLP 的张量沿特定维度切到一个 TP group。每个 rank 只计算部分结果，再用 all-reduce、all-gather 或 reduce-scatter 组合。

### 一个 shape 直觉

设线性层 $Y=XW$，$W$ 很大：

- **按输出列切 $W$**：各 rank 得到 $Y$ 的一部分输出特征；后续若需要完整 $Y$，要 gather。
- **按输入行切 $W$**：各 rank 对一部分输入通道产生部分和；要 reduce 才得到完整输出。

实际 Transformer 常把相邻的 column/row-parallel 线性层成对安排，减少不必要的完整张量复制。attention heads、GQA 组数、隐藏维、词表和 MLP 维度是否能被 TP size 整除必须显式检查。

### TP 的成本特征

- collective 发生在许多层内，频率远高于“每 step 同步一次梯度”的直觉；
- 需要低延迟、高带宽互连，跨慢网络扩 TP 往往得不偿失；
- 单层参数/部分激活可分摊，但某些 norm、embedding、输出和临时 buffer 仍复制或另有切法；
- 数值归约顺序改变，bit-exact 复现边界也会改变。

## Pipeline Parallel：切层并排 micro-batches

PP 把连续层分到 $P$ 个 stage：stage 0 处理早期层，把激活发给 stage 1；反向时梯度按相反方向返回。为了不让后续 stage 长时间等待，把一个 global batch 拆成 $m$ 个 pipeline micro-batches 交错执行。

在各 stage 计算完全均衡、忽略通信和复杂 schedule 的理想模型下，简单流水线效率约为

$$
\frac{m}{m+P-1},
$$

bubble 比例约为 $(P-1)/(m+P-1)$。例如 $P=4,m=8$ 时，理想效率约 $8/11\approx72.7\%$；这只是理解 bubble 的模型，不是实际吞吐承诺。

PP 的主要难点：

- stage 计算量不均造成最慢 stage 决定吞吐；
- micro-batch 更多可减少 bubble，却影响激活内存和全局 batch；
- stage 边界要传激活/梯度，隐藏维、序列长度和 dtype 决定流量；
- schedule 会影响权重版本、激活保存和恢复语义；
- 跨 stage 的 tied weights、loss、embedding 或跳连需要额外通信。

## Megatron 的职责边界

**Megatron（常指 Megatron-LM/Megatron-Core 生态）**面向大规模 Transformer 的模型并行与高性能训练，核心专长包括 tensor parallel、pipeline parallel，以及与 sequence/context/expert parallel、数据并行和优化 kernel 的组合。

它解决的是“怎样把 Transformer 的层与张量映射到多维 process groups，并高效调度”；它不是单纯 ZeRO stage 的别名。常见组合可能是：

- Megatron 负责 TP/PP 和模型结构切分；
- data-parallel 维使用复制或分布式 optimizer/state sharding；
- checkpoint 同时带 TP/PP/DP 拓扑语义。

能否把 Megatron 与某个 DeepSpeed/FSDP 版本组合、支持哪些模型、checkpoint 怎样转换，属于易变实现事实，不能由本页概念说明推断。

### Sequence、Context 与 Expert Parallel 不要混为一谈

这些名称在不同实现中的张量布局与通信细节会变，下面只给稳定职责：

|维度|主要切分对象|常见通信/约束|不能自动解决|
|---|---|---|---|
|sequence parallel|某些层/算子中的序列位置或与 TP 配套的激活工作|reduce-scatter/all-gather；常与 TP 组和特定 layer 实现绑定|任意长上下文；KV/attention 全部内存|
|context parallel|长序列/attention 上下文在设备间分区|attention 所需 K/V 或部分结果交换；因果 mask、位置编码和负载必须正确|模型参数/optimizer state 放不下|
|expert parallel|MoE 的 experts 分到不同 ranks，token 路由到对应 expert|all-to-all、容量因子、路由负载与 dropped/overflow token|dense 模型的单层矩阵；路由器本身的质量和稳定性|

sequence parallel 与 context parallel 都可能“切序列维”，但前者常是 TP 配套的激活/层实现策略，后者直接面向长上下文 attention 的分区。具体工具若使用不同定义，必须以固定版本的张量 shape、process group 和 collective 为准。expert parallel 只在模型确有稀疏专家结构时有意义；expert 数量多不等于负载均衡或吞吐线性增长。

对于 MoE，还要额外记录每个 expert 的 token 计数、路由熵/负载、容量溢出、all-to-all 时间和 auxiliary loss。只报“激活参数更少”会漏掉总权重存储、跨设备路由和热点 expert。

## FSDP、DeepSpeed、Megatron 一张职责表

| 名称 | 主要抽象层 | 擅长解决 | 不应自动推断 |
| --- | --- | --- | --- |
| FSDP | PyTorch 模块/参数分片 | 参数、梯度、optimizer state 的 data-parallel 分片与 materialization | 已有 TP/PP；激活已分片；任意 world size 可直接续跑 |
| DeepSpeed | 训练引擎与优化生态 | ZeRO、offload、优化器、PP 等组合 | “DeepSpeed”就等于 ZeRO-3；offload 更快；配置跨版本兼容 |
| Megatron | Transformer 模型并行与大规模训练组件 | TP、PP、多维 process groups、模型特化 kernel | 自动解决数据治理；等同 FSDP/ZeRO；任意架构直接兼容 |

三者不是简单的“三选一同类产品”。先画所需 DP/状态分片/TP/PP 维度，再选择能实现这些维度且团队能恢复、调试和验证的栈。

## 一个 32 GPU 的组合例子

假设拓扑为：

```text
DP = 4 replicas
TP = 4 ranks per tensor-parallel group
PP = 2 pipeline stages
world size = 4 * 4 * 2 = 32 ranks
```

每个 DP replica 由 $4\times2=8$ 个 rank 共同承载一份模型。若每个 pipeline micro-batch 每个 replica 有 2 条序列，每次 optimizer step 累积/调度 8 个 micro-batches，则

$$
B_{global}=2\times8\times4=64\ \text{sequences}.
$$

注意 $D=4$，不是 world size 32；TP/PP rank 共同计算同一批序列，不能再乘进 batch。若 block 长 2,048 且全部位置有效，每步最多 131,072 token。

通信图至少包括：

- TP group：层内频繁 collectives；
- PP 相邻 stage：发送激活和反向梯度；
- DP group：梯度同步或参数/梯度/optimizer state 的 shard collectives；
- checkpoint：每个 TP/PP/DP shard 写入并由全局 manifest 描述。

这个拓扑只有在模型 shape 可切、stage 足够均衡、节点互连匹配、checkpoint 可恢复时才成立。

## 决策流程：按瓶颈逐步增加复杂度

1. **先建立单 rank 正确性基线**：一个 batch 可过拟合，loss/mask/checkpoint 正确；
2. **模型和 optimizer 都放得下，只需吞吐**：优先普通 DP/DDP；
3. **optimizer/梯度/参数总状态放不下，但单层可短时 materialize**：考虑 FSDP/ZeRO；
4. **激活峰值过大**：先调 micro-batch、序列、activation checkpointing；状态分片不自动解决；
5. **单层矩阵 gather 后仍放不下**：考虑 TP；
6. **模型深度整体放不下，单 stage 可放下**：考虑 PP 并测 bubble/均衡；
7. **需要组合**：用 DP × TP × PP 明确乘积、process groups、batch 和 checkpoint；
8. **每增加一维都做缩放实验**：1→2→4 设备分别测有效 tokens/s、峰值内存、通信占比、质量和恢复。

不要一开始就把 FSDP、offload、TP、PP、activation checkpointing 和混合精度全打开；失败时无法知道是哪条边界错了。

## 分布式 checkpoint 与恢复

一个可恢复的 distributed checkpoint 还需记录：

- world size、节点/rank 映射、DP/TP/PP sizes 和 process groups；
- 参数到 shard 的映射、共享权重和 padding/对齐规则；
- 每个 shard 的文件大小、哈希、完成状态与全局 manifest；
- optimizer state 与参数 shard 的对应关系；
- global step、pipeline micro-step、sampler/RNG 和有效 token；
- checkpoint 是否支持 reshard 到不同 world size，实际验证过哪些转换；
- 保存/加载时的峰值 CPU RAM、GPU 显存、临时磁盘和总耗时。

所有 rank 写完不等于全局 checkpoint 完成。只在 coordinator 验证 shard 齐全、manifest 写完并发布完成标记后，才更新 `latest`。任何一个 rank 缺失都应使整个版本不可作为恢复点。

## 性能、成本与故障诊断

| 现象 | 可能瓶颈 | 定向证据 |
| --- | --- | --- |
| GPU 利用率周期性低 | PP bubble 或 data loader | stage timeline、micro-batch 数、I/O wait |
| 加 GPU 反而变慢 | collective/网络占主导、global batch 变化 | 通信时间、每有效 token 耗时、同 token budget 比较 |
| FSDP 峰值仍 OOM | 大模块 all-gather、预取、激活/临时 buffer | 分项峰值与 wrap 边界 |
| TP 某些 size 失败 | hidden/head/vocab/MLP 维不可整除 | 每层 shard shape 检查 |
| collective hang | rank 未进入同一 collective、异常退出、网络故障 | 每 rank 最后一步和 process group 事件 |
| checkpoint 可见但无法加载 | shard 缺失、拓扑/schema 不匹配 | 全局 manifest、哈希和 reshard 支持 |
| loss 与单卡不同 | batch/归一化、数据顺序、归约、seed 改变 | 有效 token、样本 ID、grad norm 与容差 |

## 安全、许可与资源边界

- 多节点作业会把训练样本、梯度、参数和日志送过互连；使用受控网络、加密/隔离策略和最小权限共享存储，不把 coordinator 或 dashboard 默认暴露到公网。
- 调度器凭据、对象存储 token、私有模型 URL 不写进配置、checkpoint、命令历史或日志；采用运行时最小权限注入。
- 先设置 GPU 数、最长 wall-time、失败重试次数、磁盘/对象存储预算和自动停止阈值；collective hang/OOM 重启循环会持续消耗资源。
- 分布式 checkpoint 可能是基础权重的完整可重构副本；访问、保留、删除和再分发必须遵守模型与数据许可。
- 不用公开 benchmark 吞吐替代本集群实测；拓扑、互连、精度、序列和模型 shape 不同就不具可比性。
- FSDP、DeepSpeed、Megatron、CUDA/通信库的具体版本、参数、兼容矩阵和 checkpoint API 都会变化。实施时只从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 进入官方来源并固定版本；本页未验证任何特定组合。

## 练习

### 练习 1：区分切法

分别为下列瓶颈选择第一候选，并说明它不自动解决什么：

1. 模型完全放得下，但数据吞吐太慢；
2. AdamW 状态导致 OOM，单层可放下；
3. 单个 MLP 矩阵本身无法在一张 GPU materialize；
4. 每层能放下，但 80 层整体放不下。

### 练习 2：算三维拓扑

64 张 GPU，TP=8、PP=4。计算 DP；若每个 replica 每个 pipeline micro-batch 1 条序列、累计 16 个 micro-batches，求 global batch。写出为什么不能再乘 TP 和 PP。

### 练习 3：算理想分片账本

某训练每个 replica 有 $M_p=20$ GB 参数、$M_g=20$ GB 梯度、$M_o=80$ GB optimizer state，$D=8$。忽略其他开销，计算普通 DP、ZeRO-1、ZeRO-2、ZeRO-3 每 rank 名义状态；再列出至少四项未计峰值。

### 练习 4：为长上下文与 MoE 选维度

一个 dense 模型参数能放下，但 attention 激活随上下文增长而 OOM；另一个 MoE 模型只有少数 experts 过载。分别说明为什么第一候选可能是 context parallel/激活策略、第二个才涉及 expert parallel，并列出各自至少三项通信或正确性证据。

<details>
<summary>核对要点</summary>

- 练习 1：依次为 DP、FSDP/ZeRO 类状态分片、TP、PP；还要分别检查数据、激活、通信和 checkpoint。
- 练习 2：$D=64/(8\times4)=2$；global batch $=1\times16\times2=32$。TP/PP ranks 在共同计算同一序列，不代表独立样本副本。
- 练习 3：普通 DP 120 GB；ZeRO-1 $20+20+80/8=50$ GB；ZeRO-2 $20+(20+80)/8=32.5$ GB；ZeRO-3 $120/8=15$ GB。未计激活、all-gather、通信 bucket、临时 buffer、allocator、碎片和不均衡。
- 练习 4：长上下文首先是 attention/激活问题，不能靠 ZeRO 或 expert parallel 解决；要验证 mask、位置编码、K/V/结果通信和数值对照。MoE 过载要看路由分布、all-to-all、容量溢出和 auxiliary loss；增加 experts/ranks 不保证自动均衡。

</details>

## 成功标准

- 能从瓶颈选择 DP、state sharding、TP 或 PP，而不是按工具名猜；
- 能算 $B_{global}$，不会把 TP/PP ranks 错当额外数据副本；
- 能解释 ZeRO 三阶段与 FSDP full sharding 的状态边界及峰值例外；
- 能准确概括 FSDP、DeepSpeed、Megatron 的职责和可组合关系；
- 能区分 sequence/context/expert parallel，并说明它们各自切什么、通信什么；
- 能画出 TP 层内 collective、PP stage 通信和 DP 同步三类通信；
- 能写出分布式 checkpoint 的全局完成条件，并在小规模做中断恢复与 1→2→4 缩放验证。

## 导航

- 返回模块：[[AI/20-LLM/30-训练/00-LLM训练-MOC|LLM 训练 MOC]]
- 上一站：[[AI/20-LLM/30-训练/07-模型对齐拒答方向与Heretic|模型对齐、拒答方向与 Heretic]]
- 下一站：[[AI/20-LLM/30-训练/09-数据污染评测泄漏与训练治理|数据污染、评测泄漏与训练治理]]
- 单进程状态：[[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]]
- CUDA 先修：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]
- 并发与系统直觉：[[计算机知识/30-计算机系统/05-并发并行SIMD与加速器|并发、并行、SIMD 与加速器]]、[[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]]
- 硬件路线：[[AI/00-开始/03-8GB-16GB与24GB实践路线|8GB、16GB 与 24GB 实践路线]]
- 上一级：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
- 版本核验：[[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]
