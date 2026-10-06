---
type: lesson
stage: 2
status: ready
difficulty: 高中起点
estimated_minutes: 85
topics:
  - supervised-fine-tuning
  - peft
  - lora
  - qlora
  - four-bit-loading
domain: artificial-intelligence
tags:
  - ai/llm/training
  - ai/peft
---

# SFT、LoRA 与 QLoRA

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 低秩更新、量化基座和监督标签掩码属于不同层。SFT 的 assistant-only 损失还要按真实有效标签计数，不能把 prompt 长度混入分母。 深化与验证：[[AI/20-LLM/30-训练/15-LoRA低秩几何QLoRA与蒸馏边界|LoRA低秩几何QLoRA与蒸馏边界]]；[[AI/12-PyTorch/05-变长批处理Packing与有效Token归一化|变长批处理Packing与有效Token归一化]]。


## 本课目标

- 区分 SFT 这个训练目标与 full fine-tuning、LoRA、QLoRA 这些参数更新/存储策略；
- 解释 prompt、response、chat template、label mask 和 truncation 怎样决定模型真正学什么；
- 从矩阵 shape 计算 LoRA 可训练参数数与 AdamW 状态；
- 准确说明 QLoRA 的“4-bit”发生在哪里，哪些部分仍不是 4-bit；
- 设计基础模型、tokenizer、adapter、合并权重和评测的完整产物链；
- 在显存、许可、隐私、污染和部署风险约束下选择方法。

## 数学先修（第一次使用）

- LoRA 的低秩几何、rank 与参数量：[[数学/20-线性代数与几何/04-特征值SVD与低秩近似|特征值、SVD 与低秩近似]]；
- 4-bit 表示、scale、zero-point、group 与误差：[[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化、Scale、Zero-Point、Group 与误差]]；
- SFT 使用的 token NLL：[[数学/30-概率与统计/03-似然负对数似然与困惑度|似然、负对数似然与困惑度]]；
- 优化器与状态：[[数学/40-微积分与优化/04-SGD-Momentum-Adam与AdamW|SGD、Momentum、Adam 与 AdamW]]。

本页应用这些结论，不复制完整数学推导。

## 直觉：目标、可训练参数和存储精度是三根独立旋钮

一次微调至少要分别回答：

1. **目标**：哪些 token 的错误会产生 loss？SFT 通常让参考回答 token 成为监督目标。
2. **可训练参数**：更新全部权重，还是只更新 adapter？LoRA 只训练低秩增量。
3. **冻结基座如何存储**：常规精度还是 4-bit？QLoRA 用量化的冻结基座做前向/反向所需计算，并训练 LoRA adapter。

因此下面三句话类别不同：

- “这是 SFT”描述训练数据/目标；
- “这是 LoRA”描述可训练参数的参数化方式；
- “基座以 4-bit 加载”描述冻结权重的存储与计算入口。

一个实验可以同时是 **SFT + LoRA + 4-bit frozen base**，通常称为 QLoRA 路线。

## 精确定义

- **SFT（supervised fine-tuning）**：给定输入—目标输出或多轮对话，用监督 token 的 NLL 更新模型。
- **full fine-tuning**：允许基础模型的全部或大部分参数直接更新；它可用于 SFT、持续预训练或其他目标。
- **PEFT（parameter-efficient fine-tuning）**：只训练少量参数或新增模块的一类方法，包括 LoRA、prompt/prefix tuning、adapters 等；LoRA 是其中一种。
- **LoRA**：冻结原线性层权重 $W_0$，训练低秩增量 $\Delta W=BA$，前向使用 $W_0+\alpha/r\cdot BA$（具体缩放约定必须记录）。
- **adapter**：与特定基础模型配合的增量参数和配置；单独的 adapter 通常不是完整可运行模型。
- **QLoRA**：以 4-bit 形式保存冻结基础权重，在计算时按实现反量化/转换到计算 dtype，同时训练 LoRA 参数的 PEFT 路线。
- **chat template**：把 system/user/assistant 等结构化消息确定性地序列化成模型期待的 token 序列和控制标记。
- **label mask**：规定哪些 token 参与监督损失；常用“assistant-only”并非所有 SFT 的唯一正确选择，但必须显式记录。

原始 QLoRA 方法的代表性组合包括适合近似正态权重分布的 NF4 表示、对量化常数再压缩的 double quantization，以及用于控制显存尖峰的 paged optimizer 思路。工程工具有时把更宽泛的“任意 4-bit 冻结基座 + LoRA”也称作 QLoRA；报告时要写清量化表示、group/scale、是否 double quantization、optimizer 及计算 dtype，不能只用一个方法名代替配置。

## SFT 数据：模型真正看到了什么

一条结构化样本可能是：

```text
system: 你是格式检查助手。
user: 把“温度 23 度”输出为 JSON。
assistant: {"temperature_c": 23}
```

在模型输入中，它不是三列对象，而是由**与基础模型匹配的 chat template**转换成 token IDs。训练前必须检查：

1. system/user/assistant 的控制 token 是否与模型卡和 tokenizer 一致；
2. BOS/EOS 是否被模板和 tokenizer 重复添加；
3. assistant-only mask 是否只覆盖参考回答，还是连结束标记也覆盖；
4. 多轮对话中是监督所有 assistant 回合，还是只监督最后一回合；
5. 超长样本从哪一端截断，截断后是否留下“问题没有答案”或“答案没有问题”的残片；
6. padding、packing 与跨样本 attention 是否符合设计；
7. 同一对话、模板变体或近重复是否跨 train/dev/test。

### 三种常见 loss 范围

| 范围 | 参与 loss 的 token | 适用直觉 | 风险 |
| --- | --- | --- | --- |
| 全序列 | system + user + assistant | 让模型同时拟合输入分布 | 大量容量用来复述 prompt；控制标记权重改变 |
| assistant-only | 只监督回答及规定结束标记 | 聚焦目标输出 | 错误 mask 会把全部 labels 忽略或泄漏 user token |
| 选择性回合 | 指定 assistant 回合/字段 | 处理多轮或结构化目标 | 逻辑复杂，必须可视化抽查 token 与 mask |

“assistant-only 是最佳”不是普遍定理；任务目标决定 mask。关键是把格式化文本、token ID、角色边界和 labels 对齐后抽样审阅。

## Full fine-tuning、LoRA 与 QLoRA 的职责对比

| 维度 | Full fine-tuning | LoRA | QLoRA |
| --- | --- | --- | --- |
| 基座参数 | 直接更新 | 冻结 | 冻结并以低比特形式存储 |
| 新增可训练参数 | 通常无 | 低秩 adapter | 低秩 adapter |
| optimizer state | 覆盖全部可训练基座参数 | 只覆盖 adapter/其他解冻项 | 只覆盖 adapter/其他解冻项 |
| 基座存储 | 常规训练精度，可能有 master weights | 常规加载精度 | 通常 4-bit 权重 + 量化元数据 |
| 激活 | 占用显著 | 仍占用显著 | 仍占用显著；不会随基座 4-bit 等比例消失 |
| 产物 | 新完整权重 | adapter + 基座身份，或合并权重 | adapter + 原始未量化基座身份；可另行合并/导出 |
| 主要优势 | 最大更新自由度 | 小 optimizer/checkpoint，多任务 adapter | 在基座加载显存受限时进一步节省 |
| 主要边界 | 资源和遗忘风险大 | rank/target modules 限制容量 | 量化误差、kernel/硬件兼容与合并流程更复杂 |

选择之前先问：任务需要改变多少行为？数据量/质量是否支持更大自由度？单卡瓶颈是基座权重、optimizer state 还是激活？如果激活才是峰值，改成 QLoRA 仍可能 OOM。

## LoRA 的 shape 与成本模型

对线性层 $W_0\in\mathbb R^{d_{out}\times d_{in}}$，LoRA 学习

$$
A\in\mathbb R^{r\times d_{in}},\qquad
B\in\mathbb R^{d_{out}\times r}.
$$

可训练参数数为

$$
N_{LoRA}=r(d_{in}+d_{out}),
$$

而原矩阵参数数为 $d_{in}d_{out}$。是否节省取决于 rank 和目标层，不是“用了 LoRA 就固定节省 99%”。

### 数值例

一个 $4096\times4096$ 线性层有 16,777,216 个权重。rank $r=16$ 的两个因子共有

$$
16(4096+4096)=131,072
$$

个参数，是该矩阵的约 0.78125%。若 adapter 参数和梯度各 2 bytes，AdamW 的两份状态各 4 bytes，则仅这些训练状态名义约为

$$
131,072\times(2+2+4+4)\approx1.57\ \text{MB}.
$$

这不包括冻结基座、激活、临时 buffer、其他 target modules、allocator 和 checkpoint 元数据。

### rank、alpha 与 target modules

- **rank $r$** 是增量容量上界；更大不保证更好，也会线性增加 adapter/optimizer 成本。
- **alpha/scale** 决定低秩分支的缩放；不同实现的默认与公式可能不同，必须随 adapter 保存。
- **target modules** 决定在哪些线性层插入 LoRA；仅写 `rank=16` 不能复现实验。
- dropout、bias 是否训练、embedding/lm head 是否解冻、多个 adapter 怎样组合也必须记录。

## QLoRA 与 4-bit 加载的精确边界

### 哪些通常是 4-bit，哪些不是

| 组件 | 常见 QLoRA 语义 | 为什么要单独记 |
| --- | --- | --- |
| 冻结基座权重 | 低比特存储，带 group/scale 等元数据 | 名义 $4N/8$ bytes 只是下界 |
| 反量化后的计算 | 使用实现支持的计算 dtype 执行矩阵运算 | 不是所有乘加都以 4-bit 累加 |
| LoRA 参数 | 常用可训练浮点 dtype | 需要稳定反向与更新 |
| LoRA 梯度 | 浮点 | 不因基座量化而消失 |
| optimizer state | 通常为 adapter 建立的浮点状态，或专用优化器表示 | “4-bit model”不等于“4-bit optimizer” |
| 激活与临时 buffer | 由计算 dtype、序列、batch、kernel 决定 | 常成为实际显存峰值 |

NF4 描述基座量化值怎样编码；double quantization 描述量化元数据还是否再次压缩；paged optimizer 描述 optimizer/内存峰值管理。三者分别作用于不同账本，不应混成“更低的计算精度”。它们的数值误差与 group/scale 关系回到 [[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化、Scale、Zero-Point、Group 与误差]]，具体工具是否支持则按官方版本现场核验。

**名义例**：70 亿参数的 4-bit 原始 payload 下界为约 3.5 GB（十进制）。真实加载量还包括量化 scale/group 元数据、未量化模块、临时反量化/算子 workspace、adapter、激活、缓存和 allocator；因此不能把 3.5 GB 当作“任何 7B 模型都能在 4 GB 显卡训练”的承诺。

### 概念加载流程

下面是**不可直接运行的伪配置**，故意不写易变的库参数名：

```text
pin exact base repository and immutable revision
verify model license, tokenizer, chat template and file hashes
select a supported 4-bit quantization scheme and compute dtype
load frozen base without silently casting back to full precision
verify which modules remain unquantized and which parameters require gradients
insert LoRA into explicitly listed target modules
print and audit trainable parameter names/counts
run one forward, one backward and a tiny overfit test
measure actual peak memory before scheduling the full run
```

具体框架参数、支持 GPU、量化类型、kernel 和模型兼容表会变；只从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 进入当日官方文档，并固定版本与硬件。

## 从样本到 adapter 的完整流程

1. **定义行为目标和禁止退化项**：格式、领域术语、拒绝策略、事实性或风格各自怎样测；
2. **冻结 base identity**：仓库、revision、文件哈希、架构、tokenizer、chat template、许可；
3. **登记 SFT 数据**：来源、权利、PII/secret、去重、train/dev/test 和污染扫描；
4. **格式化并可视化 mask**：至少抽查短/长、单轮/多轮、特殊字符和截断边界；
5. **建立未训练基线**：同一 prompts、模板、解码参数与评测代码；
6. **选择 full/LoRA/QLoRA**：根据目标自由度和实测权重/状态/激活峰值；
7. **极小 batch 过拟合**：确认 trainable parameters、梯度、mask、loss 和保存/加载接线；
8. **短跑校准**：测 tokens/s、峰值显存、checkpoint 大小和预计总成本；
9. **正式训练与 checkpoint**：记录有效 token、学习率、adapter 状态、恢复测试；
10. **冻结 dev/test 评测**：与 base 对照，报告平均和失败类别，不只挑展示样本；
11. **保存 adapter manifest**：base/tokenizer/chat template、target modules、rank/alpha、数据和代码身份；
12. **决定是否合并/导出**：把 adapter 与基座组合会生成新的完整权重产物，需要重新验证精度、加载、许可与哈希。

## 实际例子：200 条自有格式转换样本

目标：让基础模型把自然语言温度描述转成固定 JSON。只使用团队明确有权训练的合成/人工审校数据。

### 设计

- 160/20/20 按模板家族而不是随机行切 train/dev/test；
- dev/test 包含不同说法、负数、小数、无单位和无法解析的拒绝案例；
- 固定 base revision、tokenizer 和 chat template；
- 先保存 base 的格式有效率、数值正确率和拒绝正确率；
- 使用 LoRA 做第一候选；只有基座常规精度加载不下时才尝试 QLoRA；
- 先在 8 条样本上过拟合，确认 assistant-only mask 与 EOS；
- 正式训练后用同一确定性解码设置比较 base 与 adapter；
- 保留失败样本类别，不把训练集中“背过”的 exact match 作为泛化证据。

### 验收表

| 指标 | base | adapter | 最低要求 |
| --- | ---: | ---: | ---: |
| JSON schema 有效率 | 实测 | 实测 | 预先定义 |
| 温度数值正确率 | 实测 | 实测 | 预先定义 |
| 无法解析输入的正确处理 | 实测 | 实测 | 预先定义 |
| 通用回归小集 | 实测 | 实测 | 不低于容差 |
| dev/test 近重复命中 | 扫描 | 扫描 | 命中项隔离并复核 |

只有阈值在训练前定义，表格才不是看到结果后挑标准。

## Adapter、合并权重与部署身份

一个可用 adapter 目录至少要能回答：

- 它要求哪个精确 base revision、tokenizer 与 chat template？
- target modules、rank、alpha、dropout、bias 和额外解冻参数是什么？
- 训练数据 manifest、SFT 模板、mask、截断、token budget、种子和代码版本是什么？
- adapter 文件与配置哈希是什么？加载后 trainable/total 参数是否符合预期？
- 许可是否允许内部使用、商用、修改和再分发？基础模型与数据条件是否要求额外声明？
- 未合并 adapter、合并后的完整权重、量化导出分别经过了哪些最小加载和任务评测？

合并不是简单“复制文件”：它把低秩增量加到某一精度的基座权重上。若用错误 base、错误 target modules 或先经过有损量化的基座，结果可能不可逆地偏离。保留原 adapter 和精确 base 身份，先在副本上合并并比较输出。

## 常见误区与诊断

| 误区/现象 | 更准确的判断 |
| --- | --- |
| “QLoRA 是 4-bit 训练所有参数。” | 通常是 4-bit 冻结基座 + 浮点 LoRA/梯度/optimizer/激活路径。 |
| “adapter 只有几 MB，所以只需几 MB 显存。” | 仍要加载基座并保存激活和临时 buffer。 |
| “trainable parameters 越少越不会过拟合。” | 小而重复的数据仍可被 adapter 记忆。 |
| “SFT loss 下降说明回答更正确。” | 只说明监督 token 更像训练参考；事实性与安全需独立评测。 |
| “换 tokenizer 也能加载同一 base。” | token ID 与 embedding 语义可能错位。 |
| “合并后就是原 adapter 的无损副本。” | dtype、量化、merge 顺序和实现会带来差异，必须回归。 |
| QLoRA OOM | 先分解基座、激活、序列、batch、临时 buffer，而不是只看 nominal 4-bit。 |

## 安全、许可与资源边界

- SFT 很容易把少量私密问答、客户数据、密钥或个人信息直接记进模型；数据最小化、授权、脱敏、访问控制和删除流程必须先于训练。
- 基础模型许可、数据许可、训练代码许可、adapter 许可和合并权重的再分发条件分别核对；adapter 很小不代表不受基础权重和数据条件约束。
- 不自动信任远程模型仓库中的自定义加载代码；固定 revision，核对文件和来源，在隔离环境做最小加载。
- 先跑小 batch、短序列、少 steps，并记录停止条件；发生 NaN、OOM 重启循环、磁盘告警、未知上传或异常网络时停止。
- 不把降低拒答、增强某类回答或训练成功等同于安全提升；对危险能力、隐私复述、偏差和越权行为做单独评测。
- 4-bit/PEFT 工具与硬件兼容性易变，本页只讲稳定边界；实际命令必须按 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 当日复核。

## 练习

### 练习 1：算 LoRA 参数

某线性层 $W\in\mathbb R^{2048\times8192}$，LoRA rank 为 8。计算原矩阵与 LoRA 因子的参数数和比例；说明这个比例为什么不能直接当成整模型显存比例。

### 练习 2：审计“4-bit 训练”说法

为基座权重、量化元数据、反量化计算、LoRA 参数、梯度、optimizer state、激活分别写出你要检查的 dtype/字节来源。指出哪一项没有证据时就不能宣称“全部 4-bit”。

### 练习 3：画 label mask

为一个两轮 system/user/assistant 对话列出 token 区段，并分别画出“全序列”“所有 assistant 回合”“只训练最后 assistant 回合”的 loss mask。说明截断发生在第二个回答中间时怎样处置。

<details>
<summary>核对要点</summary>

- 原矩阵参数为 $2048\times8192=16,777,216$；LoRA 为 $8(2048+8192)=81,920$，约 0.488%。
- 该比例只针对一个目标矩阵的增量参数；基础权重、其他层、激活、临时 buffer、精度和 allocator 仍要计算。
- “4-bit”若只证实冻结基座存储，就只能这样表述；不能外推到 optimizer、梯度或累加精度。

</details>

## 成功标准

- 能把 SFT 目标、LoRA 参数化和 QLoRA 基座存储三条轴分开；
- 能从 $d_{in},d_{out},r$ 算出 adapter 与 optimizer 状态量；
- 能在样本上指出 chat template、BOS/EOS、truncation、attention mask 与 label mask；
- 能解释 4-bit nominal payload 为什么不是训练峰值显存；
- 能为 adapter 写出足以重载、评测、合并和许可审查的 manifest；
- 能用冻结 dev/test 与 base 对照，而不是用训练样本展示代替评测。

## 导航

- 返回模块：[[AI/20-LLM/30-训练/00-LLM训练-MOC|LLM 训练 MOC]]
- 上一站：[[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]]
- 下一站：[[AI/20-LLM/30-训练/04-偏好优化RLHF-DPO-ORPO与KTO|偏好优化：RLHF、DPO、ORPO 与 KTO]]
- 低秩数学：[[数学/20-线性代数与几何/04-特征值SVD与低秩近似|特征值、SVD 与低秩近似]]
- 量化数学：[[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化、Scale、Zero-Point、Group 与误差]]
- 实践：[[AI/80-实践/02-SFT-LoRA与QLoRA/00-SFT-LoRA与QLoRA|SFT、LoRA 与 QLoRA 实验]]
- Python/环境：[[计算机知识/10-编程语言/01-Python/12-包管理器选择锁定与迁移|包管理器选择、锁定与迁移]]、[[计算机知识/10-编程语言/01-Python/14-测试调试与代码质量|测试、调试与代码质量]]
- CUDA/显存：[[计算机知识/40-并行与异构计算/01-CUDA/04-内存层级合并访问与BankConflict|CUDA 内存层级]]、[[计算机知识/80-实践/04-CUDA/04-Profiling与Offload观察|Profiling 与 Offload 观察]]
- 上一级：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
- 版本核验：[[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]
