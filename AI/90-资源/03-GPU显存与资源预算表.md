---
type: reference
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 30
topics:
  - GPU显存
  - 资源预算
domain: artificial-intelligence
tags:
  - ai/resources
  - ai/gpu-budget
---

# GPU 显存与资源预算表

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 容量估算与可达速度是不同问题。先拆开权重、梯度、优化器、激活、KV 与工作区，再用实际批量和上下文验证；本轮未运行 GPU。 深化与验证：[[AI/20-LLM/40-推理/09-KV缓存分页滑窗与前缀复用|KV缓存分页滑窗与前缀复用]]；[[AI/12-PyTorch/09-性能剖析编译动态形状与内存账本|性能剖析编译动态形状与内存账本]]。


8 GB、16 GB、24 GB 是课程分流，不是硬件保证。能否运行取决于模型参数量、权重精度、上下文、batch、KV cache、激活、梯度、优化器状态、临时工作区、运行时和 GPU 架构。

## 先拆显存组成

### 只做推理

```text
峰值显存 ≈ 驻留权重 + KV cache + 临时张量/工作区 + 运行时开销 + 安全余量
```

### 做全参数训练或微调

```text
峰值显存 ≈ 权重 + 梯度 + 优化器状态 + 激活/保存张量
         + 通信与临时缓冲区 + 运行时开销 + 安全余量
```

LoRA 减少可训练参数和优化器状态，但基座权重、前向激活和许多临时张量仍然存在。QLoRA 量化基座权重，不代表整个训练过程都以 4-bit 计算。

### “放得下”与“训练得动”是两份账

一个常见的量级心算是：若权重与梯度各按 2 B/参数、Adam 的两份状态各按 4 B/参数，则只计这些常驻项约为 $12$ B/参数；若另保留 FP32 主权重，则约为 $16$ B/参数。这不是通用训练状态常数：优化器、主权重策略、分片、offload、重计算、dtype 和实现都会改变它，并且它完全没有计入激活、通信 buffer 与 allocator 碎片。

即使存储容量足够，训练或推理仍可能被 HBM 带宽、设备间互连和同步延迟限制。训练中通信／临时 buffer 会使峰值高于静态权重估算；推理中模型权重和 KV cache 的搬运又会使“算术峰值很高”不等于 token 生成很快。因此预算表必须同时写容量、带宽／互连、batch 与上下文，不能由磁盘容量或参数文件大小推断可训练性。

这组关系的来源是 [[Clippings/WorkWithLLM/教学收件箱/Untitled 1|《Untitled 1》“2019 年的真正稀缺品不是磁盘”“GPT-2 到 GPT-3 的训练状态规模”]] 与 [[Clippings/WorkWithLLM/对话原稿/分析大模型算力极限 2|《分析大模型算力极限 2》“存储不紧缺，为什么模型仍然受制于内存”]]。它们提供教学用数量级，不是本机 GPU 测量或特定硬件承诺。

## 粗略计算而非承诺

仅计算未量化连续权重时：

```text
权重字节 ≈ 参数量 × 每参数字节
```

FP32 约 4 B/参数，FP16/BF16 约 2 B/参数。量化格式不能只用“位数÷8”精确估算，因为还有 scale、zero point、分组 metadata、tensor 对齐和运行时缓冲区。

KV cache 则近似随以下量线性增长：

- 层数；
- batch 中的并发序列数；
- 已缓存 token 数；
- KV head 数与 head dimension；
- cache dtype 的每元素字节数。

因此 GQA/MQA 能减少 KV cache，但不能减少所有权重或激活。

## 三档课程路线

| 可用显存 | 默认先做 | 可以尝试但需保守配置 | 不应据此承诺 |
| --- | --- | --- | --- |
| 8 GB | 微型 Transformer、≤1.5B 级推理或示例级 QLoRA、量化推理、CPU/GPU 混合 | 短 context、小 batch、gradient accumulation、更多 CPU offload | 任意 1.5B 全参数训练或任意 7B 都流畅 |
| 16 GB | 3–4B 级 SFT/QLoRA、7–8B 量化推理、Heretic 示例级流程 | 降低 batch/context、选择较小 rank、逐层 offload | 任意 7–8B 微调都能使用长 context |
| 24 GB | 7–8B 级保守 QLoRA、较长上下文、较完整服务实验 | 根据 optimizer、checkpointing、flash attention和序列 packing 调整 | 24 GB 等于固定可训练参数上限 |

主路线：[[AI/00-开始/03-8GB-16GB与24GB实践路线]]。

### 同一张表如何用于多模态规划

8/16/24 GB 档位本身不区分模态；它们只决定你应先从哪一种可测量的小输入开始。VLM 需要额外记录分辨率、图片数和视觉 token；音频需要记录采样率、时长、声道和流式窗口；扩散需要记录分辨率、latent 尺寸、采样步数和 VAE。它们现有核心原理课程，但没有本轮真实模型 GPU 验证，所以下表不是工具建议或模型兼容表。

| 模态 | 写入预算表的额外字段 | 先缩小什么 | 课程地图 |
| --- | --- | --- | --- |
| VLM | 分辨率、图片数、预处理、Patch/视觉 token | 图片数、分辨率、batch | [[AI/30-VLM/00-VLM-MOC\|VLM]] |
| 语音/音频 | 采样率、时长、声道、帧/窗口、是否流式 | 时长、采样率、batch/窗口 | [[AI/40-语音与音频模型/00-语音与音频模型-MOC\|语音与音频]] |
| 扩散 | 输出尺寸、latent、步数、sampler、VAE | 尺寸、步数、batch | [[AI/50-扩散模型/00-扩散模型-MOC\|扩散]] |

## 配置旋钮的因果方向

| 旋钮 | 通常怎样影响显存 | 还会怎样影响结果 |
| --- | --- | --- |
| 降低 batch size | 减少激活、KV 和部分临时缓冲 | 吞吐下降；训练噪声与 accumulation 语义需记录 |
| 降低 context length | 明显减少激活和 KV cache | 无法覆盖长上下文行为 |
| gradient accumulation | 保持较大有效 batch 而降低单步激活 | 增加步数和耗时；归一化必须正确 |
| activation checkpointing | 用重算换激活内存 | 训练更慢；随机操作和边界需验证 |
| LoRA rank | 增加时提高 adapter 参数/状态 | 容量与过拟合风险同时变化 |
| 量化基座权重 | 降低驻留权重 | 产生误差与 kernel/格式约束 |
| CPU offload | 降低 GPU 驻留量 | PCIe/统一内存传输可能成为瓶颈 |
| continuous batching | 提高服务利用率 | 并发 KV cache 和调度复杂度上升 |

## 一张可复核预算表

每次实验先填，不要只写“8 GB 可跑”：

| 字段 | 示例格式 |
| --- | --- |
| 模型与 revision | `组织/模型@完整revision` |
| 参数量与架构 | dense/MoE、层数、hidden、KV heads |
| 权重格式 | BF16、NF4、GGUF Q4_K_M 等 |
| 任务 | prefill/decode、SFT、QLoRA、Heretic |
| context / batch | 最大 token、micro/effective batch |
| optimizer / adapter | AdamW 状态 dtype、LoRA rank/targets |
| 内存技术 | checkpointing、offload、KV cache dtype |
| 软件 | 驱动、runtime、框架/commit、容器 digest |
| 观测 | 启动前、稳态、峰值、OOM 日志 |
| 质量 | 基线、修改后指标和样例集 |

## 容器并不提供 GPU 驱动

容器路径是：宿主 Linux 内核和 NVIDIA 驱动 → NVIDIA Container Toolkit → 容器内 CUDA runtime/toolkit → PyTorch 或工具。容器不能修复宿主驱动不兼容，也不会自动授予 `/dev/nvidia*` 权限。

先修：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界]]、[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev]]。

## 练习与成功标准

给一项 16 GB QLoRA 实验列出至少六类显存占用，并选择两个最先调整的旋钮。成功标准是能解释为什么“把 batch 从 4 降到 1”可能仍然 OOM，以及下一步应检查权重格式、context、optimizer、临时 workspace 还是碎片化。

## 导航

- 返回：[[AI/90-资源/00-AI资源-MOC]]
- 推理预算：[[AI/20-LLM/40-推理/04-推理显存量化与硬件路线]]
- 训练预算：[[AI/20-LLM/30-训练/03-SFT-LoRA与QLoRA]]
- CUDA：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC]]
