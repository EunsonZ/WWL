---
type: lesson
stage: 2
status: ready
difficulty: 高中起点
estimated_minutes: 80
topics:
  - training-loop
  - gradient-accumulation
  - optimizer-state
  - checkpoint
  - reproducibility
domain: artificial-intelligence
tags:
  - ai/llm/training
  - ai/reproducibility
---

# 训练循环、Checkpoint 与复现

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 恢复模型权重只恢复了训练状态的一部分。优化器历史、数据游标、随机过程与有效 token 分母共同决定下一次更新，逐项核验比“设置 seed”更可靠。 深化与验证：[[AI/12-PyTorch/07-完整训练状态恢复与可复现实验|完整训练状态恢复与可复现实验]]；[[AI/12-PyTorch/05-变长批处理Packing与有效Token归一化|变长批处理Packing与有效Token归一化]]。


## 本课目标

- 沿一次 optimizer step 追踪 batch、前向、损失、反向、梯度裁剪和参数更新；
- 区分 micro-step、optimizer/global step、epoch 与 token budget；
- 列出真正可继续训练的 full-state checkpoint，而不只保存权重；
- 解释随机种子能控制什么、不能控制什么；
- 估算权重、梯度、AdamW 状态、激活和 checkpoint 的资源；
- 设计一次强制中断—恢复测试，并给出可观察的成功标准。

## 数学先修（第一次使用）

- 梯度和反向传播的定义与推导：[[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]；
- SGD、Momentum、Adam、AdamW、偏差修正和 weight decay：[[数学/40-微积分与优化/04-SGD-Momentum-Adam与AdamW|SGD、Momentum、Adam 与 AdamW]]；
- 训练/验证 NLL 与 PPL：[[数学/30-概率与统计/03-似然负对数似然与困惑度|似然、负对数似然与困惑度]]。

本页不重复这些数学推导，只关心它们在训练状态机里何时发生、哪些状态必须保存。

## 直觉：训练是带记忆的状态机

把训练想成一盘正在进行的棋局。模型权重只是棋子现在的位置；优化器动量、学习率阶段、随机数发生器、下一批数据的位置和已经看过的 token 都是棋局历史。只拍一张棋盘照片，可以继续“下另一盘”，却不一定能从原局下一手继续。

因此要先说清三种恢复目标：

1. **精确续跑目标**：下一批样本、学习率、随机操作和状态尽量与未中断运行一致；
2. **数值近似续跑目标**：允许并行归约或 kernel 导致小数值差异，但损失和模型质量落在预先定义的容差内；
3. **warm start**：只加载权重，从新的优化器、数据顺序或学习率开始一段新实验。

第三种不应写成“已从 checkpoint 无缝恢复”。

## 精确定义

- **micro-batch**：一次前向/反向在一个 data-parallel rank 上处理的样本集合。
- **micro-step**：为一个 micro-batch 计算并累积梯度的一次循环；它不一定更新参数。
- **gradient accumulation**：连续处理若干 micro-batches，把梯度累积后只做一次 optimizer update。
- **optimizer step / global step**：优化器读取当前梯度、更新自身状态与参数的一次边界；学习率调度和 checkpoint 计数必须说明是否以它为单位。
- **epoch**：按数据采样定义遍历训练集合一遍。流式、重采样、混合数据源或无限数据管道中，epoch 可能只是人为的步数段，不等于每条文档恰好一次。
- **token budget**：允许参与训练目标的有效 token 总量；跨不同 packing/batch 方案时，它通常比 epoch 更可比。
- **checkpoint**：一个带版本和完整性信息的训练状态快照；是否“完整”取决于承诺的恢复目标。
- **随机种子（seed）**：初始化伪随机数发生器状态的输入值；同 seed 不等于任何环境下逐 bit 相同。
- **可复现（reproducible）**：给定明确的输入、代码、环境、硬件和容差，重复过程得到满足预先声明等价标准的结果。

## 一次训练更新的正确边界

以下是**不可直接运行的伪代码**。重点是状态顺序，不绑定某个框架 API：

```text
set model to training mode
clear gradients from the previous optimizer step

# 先固定本 optimizer step 的全部 micro-batch，或至少先取得其有效 token 计数。
micro_batches = fetch_and_record_this_optimizer_step()
local_valid_tokens = sum(count_valid_loss_tokens(batch) for batch in micro_batches)
data_parallel_replica_count = size_of_data_parallel_group()
global_valid_tokens = all_reduce_sum_across_data_parallel_replicas(local_valid_tokens)
require(global_valid_tokens > 0)

for batch in micro_batches:
    logits = forward(batch.inputs)
    loss_sum, valid_token_count = masked_next_token_loss(logits, batch.labels)
    require(valid_token_count == count_valid_loss_tokens(batch))

    if data_parallel_gradient_collective == "mean":
        # 常见 DDP/FSDP 会在 replica 间平均梯度；乘 D 抵消该平均。
        normalized_loss = loss_sum * data_parallel_replica_count / global_valid_tokens
    else if data_parallel_gradient_collective == "sum":
        normalized_loss = loss_sum / global_valid_tokens
    else:
        fail("必须声明梯度 collective 的 sum/mean 语义")

    backward_and_accumulate(normalized_loss)

check_gradients_are_finite()
optionally_clip_gradients_using_the_declared_rule()
optimizer_updates_parameters_and_its_state()
scheduler_updates_at_its_declared_boundary()
increment_global_step_and_tokens_seen()

if checkpoint_due:
    save_full_state_at_this_clean_step_boundary()
```

关键点：

- 清理梯度应发生在新的累积窗口前；顺序写错会把上一 step 的梯度混进来或把刚算出的梯度清掉。
- 变长序列和 loss mask 下，按**整个 optimizer step、全部 data-parallel replicas 的有效 token 总数**归一化，通常比盲目除以固定累积次数更清楚。分母必须在反向前已知；还要记录梯度 collective 是求和还是求平均，否则会多除或少乘一个 replica 数。
- 梯度裁剪发生在反向之后、optimizer update 之前；混合精度下还要说明裁剪的是缩放前还是还原后的梯度。
- scheduler 有按 optimizer step、epoch 或评测指标更新的不同语义；恢复后不能偷偷换计数单位。
- 最容易恢复的 checkpoint 边界是完整 optimizer step 之后。若在梯度累积中途保存，就还要保存现有梯度、已累积有效 token、micro-step 和数据游标。

## batch 与进度成本模型

设每个 data-parallel rank 的 micro-batch 序列数为 $B_\mu$、累积次数为 $A$、副本数为 $D$，则

$$
B_{global}=B_\mu A D.
$$

固定长度 $S$ 时，物理 token 上限为 $B_{global}S$；实际监督 token 是 loss mask 的总和。训练日志至少同时记录：

- `global_step`：完成了多少 optimizer updates；
- `micro_step`：若允许中途 checkpoint，当前在累积窗口的哪个位置；
- `tokens_seen_physical`：模型实际处理的位置数；
- `tokens_seen_loss`：真正参与损失的 token 数；
- `samples_seen` 与按来源拆分的采样计数。

**例子**：$B_\mu=1$、$A=8$、$D=4$，每步共有 32 条序列。长度 1,024 时物理上限为 32,768 token；若 mask 后有效比例 75%，平均只有 24,576 个监督 token。学习率或训练预算若按 token 定义，应使用后者的真实累计值。

## Full-state checkpoint 要保存什么

### 训练数值状态

| 状态 | 为什么需要 | 缺失后的真实语义 |
| --- | --- | --- |
| 模型参数与 buffer | 当前函数和归一化等持久状态 | 无法从该点继续 |
| optimizer state | AdamW 的一阶/二阶矩、step 等 | 变成新 optimizer 的 warm start |
| learning-rate scheduler | warmup、衰减、plateau 等阶段 | 恢复后学习率轨迹改变 |
| mixed-precision scaler | 动态 loss scaling 历史（若使用） | 溢出/跳步行为可能改变 |
| 梯度与 accumulation 进度 | 只在 micro-step 中途保存时需要 | 必须退回上一个完整 optimizer step |
| EMA 或其他训练辅助状态 | 若评测/导出依赖它 | 评测权重或后续更新不一致 |

### 随机性与数据状态

- 语言运行时、数值库、框架 CPU 及每个设备的 RNG state；
- dropout、随机 masking、采样、数据增强等使用哪个 RNG；
- sampler 的 epoch、shuffle 状态、已消费位置与 data-parallel rank 映射；
- 流式数据 shard、文档/样本 ID、当前 offset、worker 分配与重试/跳过记录；
- 已处理的物理 token、有效 token、样本和各数据源混合计数。

只保存一个整数 seed 通常不够：若恢复前已经消耗了不同数量的随机数，后续序列就错位。保存 RNG **当前状态**比只记初始 seed 更接近精确恢复。

### 身份与证据状态

- 完整训练配置及其哈希，不能只保存“与上次相同”；
- 模型架构、tokenizer、chat template、special IDs 与 base revision；
- 数据 manifest、清洗/去重/切分/packing 版本和 shard 哈希；
- 代码 commit 或不可变源码包标识、依赖锁、框架/驱动/硬件与并行拓扑；
- global step、epoch 语义、wall-clock、累计资源和上次验证指标；
- checkpoint schema 版本、每个分片大小与校验哈希。

## 优化器状态为何比 adapter 大得多

先建立字节账本，而不是背“某模型需要多少 GB”。假设 $N$ 个可训练参数：

- bf16/fp16 参数：名义约 $2N$ bytes；
- 同精度梯度：约 $2N$ bytes；
- AdamW 的 $m$、$v$ 若各用 fp32：约 $8N$ bytes；
- 若另存 fp32 master weights：再约 $4N$ bytes；
- 激活、临时 buffer、allocator、量化元数据和通信 bucket 另算。

所以 10 亿个**可训练**参数仅参数 + 梯度 + 两份 fp32 AdamW 状态名义上就约 12 GB；有 fp32 master weights 时约 16 GB，还没有计算激活。实际实现、精度和分片策略会改变数字。

这也解释了 LoRA/QLoRA 的一个核心收益：优化器状态只为可训练 adapter 参数建立，而不是为冻结基座的全部参数建立。基座权重和激活仍要占资源，详见 [[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA]]。

### checkpoint 磁盘模型

在“完整 optimizer step 后保存、不保存梯度”的约定下，checkpoint 可能包含参数、optimizer state、master weights、scheduler/RNG/metadata，但不必包含当前梯度。粗略大小为

$$
M_{ckpt}\approx M_{model}+M_{optimizer}+M_{master}+M_{aux}+M_{shard\ metadata}.
$$

若分布式保存为多分片，**每个 rank 文件变小不代表总 checkpoint 变小**。保存时还可能同时存在旧版本、新临时版本和文件系统副本，磁盘峰值应至少按两个完整 checkpoint 加安全余量预算。

## 安全写入与恢复协议

### 保存

1. 只在声明的干净边界触发，例如 optimizer step 完成之后；
2. 写入新的临时 checkpoint 目录，不覆盖最后一个已知良好版本；
3. 每个分片写完后计算大小与哈希；
4. 最后写 manifest 和“完成”标记，再以文件系统支持的原子方式发布；
5. 在新 checkpoint 通过独立加载前，不删除旧版本；
6. 保留 `latest` 与 `best` 的语义差别，不能只用一个会被覆盖的名字。

### 加载前

1. 检查 schema、分片数量、文件大小与哈希；
2. 比较架构、tokenizer、数据 manifest、优化器、scheduler 和精度配置；
3. 检查 world size/分片格式是否允许当前拓扑加载；
4. 先加载到隔离路径或只读验证，不覆盖现有结果；
5. 明确这是 exact/near-exact resume 还是 warm start。

### 恢复后

1. 日志第一行记录 `resumed_from`、原 global step、token 计数和 checkpoint 哈希；
2. 核对下一批样本 ID、学习率、optimizer step 与 RNG 摘要；
3. 运行一次短验证，检查 loss 与已知 checkpoint 指标是否在容差内；
4. 只在成功完成至少一个新 checkpoint 后清理临时文件；
5. 任何配置变更都建立新的 run ID，不静默续写旧实验。

## 随机种子不是什么魔法开关

同一个 seed 仍可能得到不同结果，原因包括：

- GPU kernel 或原子操作的非确定性执行顺序；
- 不同 GPU、驱动、编译器、框架或 kernel 选择；
- 多卡 collective 的归约顺序和节点时序；
- data loader worker 启动顺序、prefetch、超时与失败重试；
- 流式数据在恢复时源内容或顺序变化；
- 混合精度舍入、loss-scaling 跳步和不同 batch packing；
- 分布式 world size 改变导致随机流、batch 划分或数值归约变化。

因此复现声明应分层：

| 层级 | 可接受标准示例 |
| --- | --- |
| 数据复现 | 文档/样本 ID、tokenizer、block 与 mask 哈希一致 |
| 状态复现 | 参数、optimizer、scheduler、RNG、游标成功加载 |
| 数值复现 | 固定环境下若干步 loss/参数摘要逐 bit 或在严格容差内 |
| 统计复现 | 多 seed 指标均值/离散程度落在预先声明范围 |
| 行为复现 | 冻结评测集上的任务、安全与回归指标满足阈值 |

逐 bit 不可得时应报告 near-exact 或 statistical reproducibility，而不是把差异隐藏在“GPU 随机性”一句话里。

## 实际例子：100 步强制中断—恢复

设计两条从同一初始状态开始的微型 run：

- **连续组**：直接训练到 global step 100；
- **恢复组**：训练到 step 60，保存 full-state，终止进程，在全新进程加载并训练到 100。

预先记录比较项：

1. step 61 的样本 ID、有效 token 数和学习率；
2. step 61 前的模型/optimizer/RNG 摘要；
3. step 61～65 的 loss 序列；
4. step 100 的参数摘要、dev NLL/PPL 和固定 prompts 输出；
5. 连续/恢复两组允许的 bit-exact 或数值容差。

若只加载 step 60 权重、重新创建 optimizer，第二组是 warm start 对照，不是 full resume。若数据顺序不同，即使最终指标接近，也不能宣称数据轨迹完全复现。

## 常见失败

| 现象 | 常见根因 | 修复方向 |
| --- | --- | --- |
| 恢复后 loss 突跳 | optimizer/scheduler/scaler 缺失，batch 重复或跳过 | 检查 full-state 与数据游标 |
| 学习率重新 warmup | scheduler step 没保存或计数单位改变 | 保存并核对 global step 语义 |
| 同 seed 仍不一致 | 非确定性 kernel、worker、collective、环境漂移 | 固定环境并声明复现层级 |
| checkpoint 偶尔无法加载 | 保存时中断、部分分片或覆盖旧版本 | 临时目录 + manifest + 完成标记 |
| 磁盘突然耗尽 | 多 rank 重复全量保存、临时/旧版本并存 | 预估总量并验证保存格式 |
| 训练“继续”但重看旧数据 | sampler/stream offset 未恢复 | 记录样本 ID 与 shard offset |

## 安全、许可与资源边界

- checkpoint 可能记忆训练数据，也可能含路径、run 名、环境变量或配置中的敏感字段；保存前做元数据白名单，绝不写入 token、密码或私有下载 URL。
- 不把 checkpoint 上传、共享或放入公共对象存储，除非基础模型、数据、adapter/权重和输出分别允许且已完成隐私审查。
- 恢复文件视为不可信输入：优先使用明确张量/结构格式，验证来源与哈希，不执行来源未知的序列化对象或恢复脚本。
- 设置 checkpoint 数量、保存频率、磁盘水位与过期策略；清理前先验证新版本，保留至少一个已知良好恢复点。
- 共享集群中只给作业所需路径最小权限；日志和崩溃转储也可能包含样本、配置或凭据。
- 框架、确定性选项和 checkpoint API 的版本行为会变化；实施时只从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 进入官方文档并固定环境。本页没有承诺跨版本/跨硬件 bit-exact。

## 练习

### 练习 1：判断是不是 resume

以下三种加载分别属于 exact/near-exact resume、warm start，还是无法判断？说明缺失证据。

1. 加载模型权重，optimizer 重新初始化，数据从头 shuffle；
2. 加载模型、optimizer、scheduler、RNG、sampler 和 manifest，同硬件继续；
3. 加载所有状态，但从 8 卡改成 4 卡并换了 kernel。

### 练习 2：算显存账本

一个 100M 可训练参数模型使用 2-byte 权重、2-byte 梯度、两份 4-byte AdamW 状态，暂不算 master weights。计算这四项名义总量；再说明为什么它不是训练峰值。

### 练习 3：写恢复验收单

为“step 200 中断，step 500 完成”写出至少八个恢复后检查项，其中必须包含下一 batch ID、学习率、有效 token、optimizer step、验证 loss 和 checkpoint 哈希。

<details>
<summary>核对要点</summary>

- 1 是 warm start；2 在其环境与确定性承诺下可能是 exact/near-exact；3 至少需要重新定义为数值或统计复现，不能自动称精确续跑。
- 100M 参数的名义总量为 $100M\times(2+2+4+4)=1.2$ GB（十进制）。还缺激活、临时 buffer、allocator、通信、可能的 master weights 和框架开销。
- 验收应先定义容差，而不是看到差异后再放宽。

</details>

## 成功标准

- 能从 batch 获取一直讲到 optimizer/scheduler update，并指出 accumulation 的干净保存边界；
- 能列出 full-state checkpoint 的数值、随机性、数据和身份状态；
- 能计算 AdamW 状态的名义字节量，并解释为何 checkpoint 与显存峰值不同；
- 能准确说出 seed、RNG state、确定性 kernel 与统计复现的差别；
- 能实施或审阅一次强制中断—恢复对照，而不把 weights-only 加载误称为 resume。

## 导航

- 返回模块：[[AI/20-LLM/30-训练/00-LLM训练-MOC|LLM 训练 MOC]]
- 上一站：[[AI/20-LLM/30-训练/01-数据Tokenization与预训练流程|数据、Tokenization 与预训练流程]]
- 下一站：[[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA]]
- 分布式 checkpoint：[[AI/20-LLM/30-训练/08-分布式训练FSDP-DeepSpeed与Megatron|分布式训练、FSDP、DeepSpeed 与 Megatron]]
- 优化器数学：[[数学/40-微积分与优化/04-SGD-Momentum-Adam与AdamW|SGD、Momentum、Adam 与 AdamW]]
- 预训练实践：[[AI/80-实践/01-微型Transformer预训练/00-微型Transformer预训练|微型 Transformer 预训练实验]]
- Python 工程：[[计算机知识/10-编程语言/01-Python/05-异常文件IO与上下文管理|文件 I/O 与上下文管理]]、[[计算机知识/10-编程语言/01-Python/14-测试调试与代码质量|测试、调试与代码质量]]
- GPU 数值与异步边界：[[计算机知识/40-并行与异构计算/01-CUDA/06-Stream-Event与异步流水线|Stream、Event 与异步流水线]]、[[计算机知识/40-并行与异构计算/01-CUDA/07-FP16-BF16-FP8与Tensor-Core|FP16、BF16、FP8 与 Tensor Core]]
- 上一级：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
- 版本核验：[[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]
