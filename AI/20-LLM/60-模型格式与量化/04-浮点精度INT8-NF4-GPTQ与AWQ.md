---
type: lesson
domain: artificial-intelligence
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 70
verified: 2026-09-02
topics:
  - floating-point
  - int8
  - nf4
  - gptq
  - awq
tags:
  - ai/llm/formats
  - ai/llm/quantization
---

# 浮点精度、INT8、NF4、GPTQ 与 AWQ

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 量化器的目标函数和校准分布决定哪些误差更重要。存储精度、反量化计算精度与 adapter 训练精度必须分开记录，不能用一个 bit 数概括。 深化与验证：[[AI/20-LLM/60-模型格式与量化/08-量化误差传播校准目标与端到端评测|量化误差传播校准目标与端到端评测]]；[[AI/20-LLM/30-训练/15-LoRA低秩几何QLoRA与蒸馏边界|LoRA低秩几何QLoRA与蒸馏边界]]。


## 本课目标

- 区分存储 dtype、计算 dtype、累加 dtype 与运行时对张量的解包方式；
- 比较 FP32、FP16、BF16、具体 FP8 变体与 INT8 的范围/精度取舍；
- 用 group、scale、zero-point、calibration 和 error 解释量化；
- 说清 NF4/bitsandbytes/QLoRA、GPTQ 与 AWQ 各自的目标、产物和运行时依赖。

## 1. “精度”至少要问四遍

看到“使用 FP16”或“4-bit 模型”时，先问：

1. **磁盘上保存什么？** 是 FP16 张量，还是 4-bit code + per-group scale？
2. **加载到 RAM/VRAM 后是什么？** 是保持压缩并由内核按需解包，还是全量反量化成 FP16？
3. **乘法和累加用什么？** 输入、权重、乘积与 accumulator 可用不同精度。
4. **哪些张量没量化？** embedding、output head、normalization、bias 或特定敏感层常可被保留为更高精度，具体由方法和实现决定。

只回答“几 bit”无法推出文件字节数、显存、内核是否加速，也无法推出质量损失。

## 2. FP32、FP16、BF16 与 FP8

| 类型 | 关键取舍 | LLM 中的常见角色 | 必须说明的边界 |
| --- | --- | --- | --- |
| FP32 | 较宽范围与约 24 位二进制有效精度，存储/带宽大 | 高精度基线、部分 master weights/累加/数值敏感算子 | “FP32”不保证数值稳定，算法和累加顺序仍重要 |
| FP16 | 尾数比 BF16 多，但指数范围小 | GPU 推理/训练存储或算子输入 | 上溢/下溢、loss scaling、累加 dtype 需单独记录 |
| BF16 | 指数宽度与 FP32 相同，范围近似 FP32，但尾数更短 | 训练/推理权重与激活，常用于需要范围而可接受较粗精度的路径 | 硬件是否原生支持、是否会转换成其他格式 |
| FP8 E4M3/E5M2 等 | 用更少指数/尾数位交换带宽和吞吐，通常需尺度管理 | 支持硬件和框架中的低精度训练/推理 | “FP8”不是一个唯一编码；E4M3FN、E5M2、FNUZ 等的范围、NaN/Inf/零规则不同 |

这些格式的位级定义、ULP、上/下溢、subnormal 与累加误差只在 [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]] 维护；本页只说它们在 LLM 工具链中的位置。

## 3. INT8 是 dtype 还是量化？两种都可能

原生 INT8 是 $-128$ 到 $127$ 的有符号整数类型。在量化中，整数 $q$ 通常是对实值 $x$ 的编码，与 scale $s$ 和可选 zero-point $z$ 共同解释：

$$
\hat{x}=s(q-z).
$$

如果一个张量的全部值共用一个 $s,z$，元数据小却难以适应局部尺度；若按 channel 或每 $g$ 个值一组，每组独立 $s,z$，误差往往变小，但元数据、访存和内核复杂度上升。

- **对称量化**常将零映射到固定中心编码，实现简洁；
- **非对称量化**选择非零 zero-point，可更好利用非对称取值范围；
- **权重专用量化**将激活保留为浮点，内核在矩阵乘时处理压缩权重；
- **权重+激活量化**还要处理动态输入的范围和异常值，是另一个问题。

group、scale、zero-point、clipping 与误差的统一数学见 [[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化 Scale、Zero-Point、Group 与误差]]。

## 4. 一个可观察的分组误差例子

一组权重为 `[-1.0, -0.1, 0.1, 1.0]`，另一组为 `[-100, -10, 10, 100]`。如果把八个值强制共用一个 scale，大值组会决定整体范围，`0.1` 可能被量化到 0 或粗糙台阶。若两组分别选 scale，小值组可使用更密的台阶，但需多保存一组 scale。

这个例子只展示**分组尺度**的作用，不证明越小 group 在任意硬件上都更快，也不涉及误差在网络深度中的传播。

回到上一页的四值 fixture：已有程序另用同一组值计算教学对称 INT4 网格，`s=1.25/7`、整数码范围 `[-7,7]`，得到 MAE 约 `0.044643`、最大绝对误差约 `0.071429`。这一步改变的是数值近似；程序没有把这些码打包回 GGUF，原 fixture 仍是 16 字节 F32 数据，也没有实现 NF4、GPTQ、AWQ 或 K-quants。上面的两组尺度例改用相差 100 倍的范围，是为暴露一个全局 scale 的瓶颈；它不延续 fixture 的张量身份。

现在还差一个问题：同样大小的权重误差，进入一次线性层后也一样大吗？先到 [[AI/20-LLM/60-模型格式与量化/08-量化误差传播校准目标与端到端评测#权重误差相同，输出误差可以不同|两输入的加权误差反例]]算出输出变化，再回本节理解为什么校准需要输入数据；保留原来的分组讨论，不能从四值 MAE 直接选出真实模型的最佳方法。

## 5. calibration 就是“看数据后决定怎样损失更小”

并非所有量化都需要任务数据。最简单的权重范围量化只读权重本身，根据 min/max 或其他统计量选 scale。需要 calibration 的方法会用一小批代表性输入，观察激活、敏感方向、二阶近似或权重重要性，以选择更低误差的编码/保留策略。

校准集应记录来源、许可、清洗、tokenizer revision、长度分布和任务覆盖。如果校准只看英文简短文本，不能假定中文、代码、数学和长上下文的敏感性也得到保护。评测集应与选择/校准过程分离，否则会对评测过拟合。

## 6. NF4、bitsandbytes 与 QLoRA

**NF4（NormalFloat4）**使用一个面向近似正态分布权重设计的 4-bit 非均匀代码表。在 bitsandbytes 的常见工具链中，权重按 block 量化并配有尺度信息；可选“双重量化”还对这些尺度参数做进一步压缩。精确 block 大小、打包、硬件支持和 API 是库版本化行为。

可以把一个 block 的解码理解为：先从每个 4-bit code 选出代码表值 $c_q$，再用该 block 的尺度 $s$ 恢复 $\hat w=s c_q$。两个 4-bit code 可打包进一个字节，但 block scale、可选的双重量化状态和对齐仍要占空间，所以“半字节/权重”不是完整内存公式。这里只解释运行时形状；NF4 的分位点构造和误差讨论继续由 [[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化 Scale、Zero-Point、Group 与误差]] 维护。

**QLoRA**的核心是将预训练基座权重以 4-bit 形式冻结加载，在较高 compute dtype 中通过反量化参与前向/反向，只训练 LoRA 适配器。需分清：

- 4-bit 是基座权重存储/运行时表示，LoRA 参数和 optimizer state 不必也是 4-bit；
- compute dtype 常与 storage dtype 不同；
- QLoRA 训练产物通常是适配器或合并权重，并不自动成为 GGUF `Q4_K_M`；
- bitsandbytes NF4 的内存布局/内核不与 GGUF 量化张量格式互换。

训练上下文见 [[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA]]。

## 7. GPTQ 与 AWQ：相同位宽下也可以有不同的损失决策

### GPTQ

GPTQ 是训练后权重量化家族，经典思路是逐列/逐块量化权重，使用校准激活得到的二阶信息近似来补偿已量化权重对层输出的误差。实际工具对 group size、对称/非对称、激活排序、打包与 kernel 支持有自己的选项和元数据。

### AWQ

AWQ（Activation-aware Weight Quantization）的核心动机是用校准激活识别对输出更敏感的权重/通道，通过尺度变换和量化策略减少这些显著权重的信息损失。“保护显著权重”是方法动机，不表示实现会把它们全部另存为高精度稀疏列表；必须查精确工具版本。

### 把三种 4-bit 产物放到同一张检查表

```yaml
method: <nf4/gptq/awq>
source_model_revision: <immutable revision>
weight_bits: 4
group_or_block_size: <exact value>
scale_and_zero_semantics: <implementation contract>
calibration_dataset: <none or immutable dataset revision>
compute_dtype: <fp16/bf16/...>
packing_schema: <tool + version>
runtime_kernel: <engine + backend + version>
artifact_files_and_hashes: [<files>]
```

仅 `weight_bits: 4` 相同不会让三个产物兼容。若 `packing_schema`、scale/zero 解释或 kernel 不同，即使都由 safetensors 容器承载，也不能换名后直接加载。

| 方法 | 主要信号 | 常见产物定位 | 不可跳过的验证 |
| --- | --- | --- | --- |
| NF4/bitsandbytes | 权重分布与 block scale | 框架运行时中的 4-bit 基座加载，常服务 QLoRA | bitsandbytes/Transformers/目标硬件后端组合、compute dtype、适配器保存与质量 |
| GPTQ | 校准激活与近似二阶误差补偿 | 训练后权重量化与对应打包/内核 | 实现、group/zero-point、校准集、目标运行时格式与 kernel |
| AWQ | 校准激活表示的权重/通道显著性 | 激活感知的训练后权重量化 | 精确 scaling/search 实现、打包格式、内核与实测任务 |

GPTQ/AWQ 不是仅凭 `.safetensors` 后缀就能识别的唯一通用字节格式。平台可用 safetensors 容器保存打包权重与额外量化配置；相容性取决于量化器、配置 schema、打包布局和推理 kernel 的精确组合。

## 8. 格式名对照：不同后端的“4-bit”不是可换零件

| 标签 | 约束的是 | 需要哪类运行时 |
| --- | --- | --- |
| F16/BF16 safetensors | 容器中每个张量的 dtype/字节 | 知道架构与 config 的框架 |
| bitsandbytes NF4 | 库定义的 blockwise 4-bit 权重表示与量化状态 | 对应 bitsandbytes/框架/硬件支持 |
| GPTQ/AWQ 产物 | 具体实现的打包权重、scale/zero 和配置 | 明确支持该 schema 和 kernel 的引擎 |
| GGUF `Q4_0`、`Q4_K`、IQ | GGUF tensor info 里的 ggml 张量类型 | 支持该 GGUF/量化版本与 type 的 ggml 类运行时 |

转换一般需要先恢复或读懂源方法的数值语义，然后由目标工具重新编码。对已经量化的源做第二次有损量化会累积误差，不是无损“换壳”。

## 练习：为三个目标选起点

不下载模型，对下列目标分别写出“候选方法”“必须固定的运行时”“校准/评测数据”和“不适合的原因”：

1. 在支持 bitsandbytes 的 GPU 环境做 QLoRA，只训练 LoRA 适配器。
2. 在已验证 GPTQ kernel 的服务引擎中部署权重专用 4-bit 模型。
3. 在 `llama.cpp` 的特定 CPU/GPU 后端运行 GGUF，要求可移植的单文件产物。

### 成功标准

- [ ] 我不再用一个“4-bit”标签代替 storage、compute、accumulation、group 和运行时信息。
- [ ] 我能说明 NF4 与 `Q4_K_M` 不是同一个数值编码。
- [ ] 我能说明 QLoRA 训练的 4-bit 基座与可训练 LoRA 适配器的区别。
- [ ] 我会将 calibration 数据与最终评测数据分开，并记录 tokenizer/revision。

## 许可证、不可信产物与版本边界

- 框架库许可证、实现/内核许可证、基础模型权重条款、LoRA 适配器与校准数据权利必须独立记录。
- 量化库可解析一个文件不代表其来源可信；异常 shape/scale/zero-point 可触发资源耗尽、实现缺陷或安静的错误输出。
- 2026-09-02 重新对照了 QLoRA/NF4、GPTQ、AWQ 论文与官方实现；精确 ref 见 [[AI/20-LLM/60-模型格式与量化/07-一手来源快照与现场复核清单|一手来源快照与现场复核清单]]。实施时仍要从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 重查库版本、硬件支持、打包 schema 和实际 API；不将本页的稳定概念当作当前兼容矩阵。
- 保留高精度基线与配对报告；新方法失败时删除派生产物，不在原始权重上就地改写。

CUDA 中的存储/计算/累加 dtype 与 Tensor Core 路径见 [[计算机知识/40-并行与异构计算/01-CUDA/07-FP16-BF16-FP8与Tensor-Core|FP16、BF16、FP8 与 Tensor Core]]；框架/llama.cpp kernel 与真正后端证据见 [[计算机知识/40-并行与异构计算/01-CUDA/10-PyTorch扩展-Triton与llama.cpp后端|PyTorch 扩展、Triton 与 llama.cpp 后端]]。

---

**上一站**：[[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证|GGUF 结构、转换与验证]] · **下一站**：[[AI/20-LLM/60-模型格式与量化/05-K-quants-IQ与Q4_K_M|K-quants、IQ 与 Q4_K_M]] · **返回**：[[AI/20-LLM/60-模型格式与量化/00-模型格式与量化-MOC|模型格式与量化 MOC]]
