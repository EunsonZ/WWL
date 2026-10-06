---
type: lesson
domain: artificial-intelligence
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 65
verified: 2026-09-02
topics:
  - k-quants
  - i-quants
  - q4-k-m
  - ggml
tags:
  - ai/llm/formats
  - ai/llm/quantization
---

# K-quants、IQ 与 Q4_K_M

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 格式名称是实现约定，不等于每个参数都恰好占同样 bit 数。元数据、混合精度层、硬件内核和真实激活分布共同决定成本与质量。 深化与验证：[[AI/20-LLM/60-模型格式与量化/08-量化误差传播校准目标与端到端评测|量化误差传播校准目标与端到端评测]]；[[AI/12-PyTorch/09-性能剖析编译动态形状与内存账本|性能剖析编译动态形状与内存账本]]。


## 本课目标

- 区分 `Q4_0`、`Q5_0`、`Q8_0` 等传统 block quant 与 `Q*_K` super-block 家族；
- 解释 `Q4_K` 是张量数值类型，`Q4_K_M` 是整模型的混合量化预设；
- 说清 IQ/I-quants 为何在极低 bit 区间引入更复杂的代码表/重要性信息；
- 避免用名义 bit 数直接推断真实体积、速度和质量。

## 1. 从“每个值几 bit”转向“一个 block 怎样解码”

低位权重不能只用一串裸 4-bit 整数解释。一个可解码 block 至少需要：

- 被打包的量化 code；
- 将 code 映射回近似实数的 scale；
- 某些格式中的 min/zero-point 或代码表；
- 规定一个 block/super-block 包含多少值的布局；
- 运行时内核能按该布局读取、反量化与点积。

因此平均 bits per weight（bpw）包含 code 与辅助字段分摊，往往不等于名称中的整数。例如 `Q8_0` 虽使用 8-bit code，每个 block 的 scale 会使平均 bpw 略高于 8；文件还有混合高精度张量、对齐和元数据。

## 2. `Q4_0`、`Q5_0`、`Q8_0`：传统 block quant 基线

| 类型 | 稳定地可以说 | 不应不查源码就说 |
| --- | --- | --- |
| `Q4_0` | 以较小 block 保存 4-bit 量化 code 和块尺度，是经典 ggml 低位基线之一 | 未来任意实现的结构体 padding、SIMD 打包或内核必然相同 |
| `Q5_0` | 用比 `Q4_0` 更多的 code 位表示权重，通常用更大体积换取更小近似误差 | 对每个模型/任务都必然优于某个 K-quant 预设 |
| `Q8_0` | 8-bit block quant，常作较高精度的量化基线或特定张量选择 | 它等于传统框架中任意 INT8 量化，或必然是最快的格式 |

下标 `_0` 是 ggml 类型名的一部分，不是 tokenizer 中的 special token，也不是“误差为 0”。精确 block 元素数、scale dtype、code 拼接与计算函数必须对照目标 ggml/`llama.cpp` commit 的类型定义和测试。

### 固定源码下的可手算例子

以 2026-09-02 固定的 `llama.cpp` `b96806d96061049a5b574269b049bf6241d63d46` 中 [`ggml/src/ggml-common.h`](https://github.com/ggml-org/llama.cpp/blob/b96806d96061049a5b574269b049bf6241d63d46/ggml/src/ggml-common.h) 为例，只算 block 本身：

| 张量 type | 每 block 权重数 | block 字节 | block 内 effective bpw | 为什么不等于名义 bit |
| --- | ---: | ---: | ---: | --- |
| `Q4_0` | 32 | $2+16=18$ | $18×8/32=4.5$ | 16 B code 外还有 2 B FP16 scale |
| `Q8_0` | 32 | $2+32=34$ | $34×8/32=8.5$ | 32 B INT8 code 外还有 2 B FP16 scale |
| `Q4_K` | 256 | $2+2+12+128=144$ | $144×8/256=4.5$ | code 外还有 super-block scale/min 和压缩的局部 scale/min |

这张表的价值是显示“同为 4.5 bpw 也可有不同 block 语义”；它不是整模型文件大小表。`Q4_K_M` 还会混合多种 tensor type，metadata/对齐也在 block 之外，因此必须从实际产物统计。任何不固定 commit 的数字都只能当作示意。

## 3. K-quants：super-block 内再组织局部量化参数

K-quants 家族包含 `Q2_K`、`Q3_K`、`Q4_K`、`Q5_K`、`Q6_K` 等类型。其共同设计方向是：在较大 super-block 内包含多个局部 block，局部 block 有压缩的 scale/min 等参数，super-block 再提供整体尺度。这比“整个张量一个 scale”更能跟随局部分布，又通过分层参数压缩控制开销。

以 `Q4_K` 为例，“4”指权重 code 的核心位数，“K”指这个 super-block 方案家族。它仍需 scale/min 等辅助字段，平均 bpw 不是精确 4.000。精确字段位宽、block 大小和端序由当时的 ggml type/量化版本定义。

## 4. `Q4_K_M` 是预设，不是单一张量 type

> [!important] 核心区分
> - `Q4_K`：一个张量在 GGUF tensor info 中可声明的 ggml 数值类型。
> - `Q4_K_M`：`llama-quantize` 一类整模型预设名，量化器依张量角色使用不同精度，以在体积与质量之间折中。

`_S`、`_M`、`_L` 类后缀是预设名的一部分，但不是每个位宽都必然有三档，也不是跨版本、跨工具的永久精确张量分配契约。2026-09-02 固定的 `llama.cpp` 源码中，`Q4_K` 标签就是 `Q4_K_M` 的别名，而 `Q4_K_M` 默认 type 是 `Q4_K`，但量化器会按张量类别、层位置、GQA/MoE 与架构等条件选用 `Q5_K`/`Q6_K` 等更高 type。这个例子证明了“必须固定源码”，不应被复制成未来版本的永久规格。

在每次实施中：

1. 固定 `llama.cpp` commit 与 GGUF quantization version；
2. 读该 commit 的 quantizer 帮助、预设映射与测试；
3. 转换后从 GGUF tensor infos 统计实际 type 和字节；
4. 将“要求的预设”与“实际张量混合”都写入 manifest。

`Q4_K_M` 完全不改变 Unicode 或 tokenizer 编码。如果量化后 token ID 与高精度基线不同，应先定位 tokenizer/chat template/元数据转换错误，不是用“4-bit 所以文本被压缩了”解释。

## 5. IQ/I-quants：在更低位预算中花更多设计复杂度

IQ（常称 I-quants/importance-aware quants）家族包含 `IQ1_*`、`IQ2_*`、`IQ3_*`、`IQ4_*` 等类型。它们不是“把 K 字母换成 I”的同义名，而是在代码表、非线性编码、块结构与重要性加权上采用更复杂的方案，尤其用于在极低 bpw 下减少质量崩塌。

某些 IQ/K-quant 工作流程可以使用 importance matrix（imatrix）：`llama.cpp` 的相应工具会在代表性校准输入的前向过程中，累计相关张量输入激活的平方统计（例如 `Σ(Act²)`），供量化器作为量化误差加权代理。它不是逐权重消融、梯度归因，也不直接测量某个权重对最终输出的因果贡献。这使输出产物不再只取决于原始权重，还取决于：

- imatrix 生成工具的 commit 和参数；
- 校准输入、tokenizer、上下文长度与语言/任务覆盖；
- 哪些张量包含/排除；
- 量化器如何使用重要性数据。

越低 bit 不但更依赖校准与任务分布，也更依赖实现了对应解码/点积的硬件内核。如果后端要先将 IQ 大规模解包为高精度，磁盘变小不会线性转化为 RAM/VRAM 或速度收益。

## 6. 为何低 bit 可能更慢

推理时间可粗略拆成读权重、解码/反量化、数学计算、同步/调度和 KV cache 访存。降低 bpw 主要减少权重带宽和容量，但会增加更复杂的解码；内核向量化与硬件指令支持决定这个交换是否值得。

| 场景 | 可能的主导因素 | 为何不能单看 bpw |
| --- | --- | --- |
| 大 batch/prefill | 矩阵乘吞吐、后端 kernel、batching | 高精度 Tensor Core/向量路径可能很高效 |
| batch 1 decode | 每 token 读权重的带宽、KV cache 与小核心开销 | 低 bpw 常有带宽优势，但复杂解码也可反超 |
| GPU offload 不完整 | CPU↔GPU 转移、分层同步、两端内核 | 体积适合不代表分割调度高效 |
| 长上下文 | KV cache 容量/带宽、attention 算法 | 权重量化不一定同步量化 KV cache |

## 7. 选择时读的不是名字，而是 manifest

候选 GGUF 至少记录：

| 字段 | 作用 |
| --- | --- |
| 基础模型 ID + revision + source hashes | 防止拿不同基础权重的量化文件比较 |
| tokenizer/chat template hashes | 确保 token 序列和聊天包装一致 |
| `llama.cpp` commit + GGUF/quantization version | 固定预设映射、格式读取和内核实现 |
| 请求的预设 + 实际 tensor type 统计 | 防止仅信文件名，可重建真实平均 bpw |
| imatrix/calibration 来源与参数 | 评估适用分布、泄漏与权利 |
| 文件哈希、字节数、许可证 | 完整性、追溯和使用/分发边界 |

## 练习：批判五个说法

对每句判断“正确”“错误”或“信息不足”，并写一句理由：

1. “`Q4_K_M` 把 tokenizer 编码为 4 bit。”
2. “一个文件名以 `Q4_K_M.gguf` 结尾，所有张量必然是 `Q4_K`。”
3. “在同一后端、同一设置下，某个 IQ2 产物实测比 Q4 慢，这在工程上可能发生。”
4. “`Q8_0` 文件的平均 bits per weight 必然恰好是 8.000。”
5. “两个 `Q4_K_M` 文件要可比，先确认基础模型、tokenizer、量化器 commit 和实际 tensor type 分布。”

### 参考结果与成功标准

1 错误；2 错误；3 正确；4 错误；5 正确。

- [ ] 我会从 tensor info 读实际 type，而不只信文件名。
- [ ] 我能说明 `Q4_K` 与 `Q4_K_M` 的 type/预设边界。
- [ ] 我知道 `_S/_M/_L` 的精确混合规则必须在目标 commit 现场核对。
- [ ] 我不会由更低 bpw 直接推出更快、更省运行时内存或质量可接受。

## 许可证、不可信文件与版本边界

- GGUF 量化不改变基础模型的许可证与可接受使用条款；量化者不能仅因创建新文件就为它换上不相容许可。
- imatrix/校准文本也有来源、隐私和许可边界；不把真实用户提示词、密钥或未授权内容放入量化产物/日志。
- 来源不明的 GGUF 即使结构合法也不代表权重无后门、metadata 真实、tokenizer 正确或不会耗尽资源。
- 本页以 2026-09-02 对照的 ggml GGUF 规范 `d4716378882593333721eb33f153144b6885caf2` 和 `llama.cpp` `b96806d96061049a5b574269b049bf6241d63d46` 为语义快照。类型列表、预设映射、imatrix 选项、内核和性能都易变；精确文档/源码入口见 [[AI/20-LLM/60-模型格式与量化/07-一手来源快照与现场复核清单|一手来源快照与现场复核清单]]，实施时再从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 重查目标 commit。
- 保留高精度 GGUF 基线与输入哈希；候选未通过时只删除派生量化产物，不覆盖基线。

为了解释为何么同一 type 在 CPU 与 CUDA 上会有不同性能排序，继续阅读 [[计算机知识/40-并行与异构计算/01-CUDA/04-内存层级合并访问与BankConflict|内存层级、合并访问与 Bank Conflict]]、[[计算机知识/40-并行与异构计算/01-CUDA/09-Roofline与Nsight性能方法|Roofline 与 Nsight 性能方法]]与 [[计算机知识/40-并行与异构计算/01-CUDA/10-PyTorch扩展-Triton与llama.cpp后端|llama.cpp CUDA 后端]]。

---

**上一站**：[[AI/20-LLM/60-模型格式与量化/04-浮点精度INT8-NF4-GPTQ与AWQ|浮点精度、INT8、NF4、GPTQ 与 AWQ]] · **下一站**：[[AI/20-LLM/60-模型格式与量化/06-格式量化选择与质量评测|格式、量化选择与质量评测]] · **返回**：[[AI/20-LLM/60-模型格式与量化/00-模型格式与量化-MOC|模型格式与量化 MOC]]
