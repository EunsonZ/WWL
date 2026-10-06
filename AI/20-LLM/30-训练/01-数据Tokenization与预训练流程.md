---
type: lesson
stage: 2
status: ready
difficulty: 高中起点
estimated_minutes: 90
topics:
  - data-cleaning
  - deduplication
  - tokenization
  - sequence-packing
  - pretraining
domain: artificial-intelligence
tags:
  - ai/llm/training
  - ai/data
---

# 数据、Tokenization 与预训练流程

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 原始字节数、去重后的有效文本、训练 token 与重复 epoch 是不同口径。训练目标和数据治理应一起记录，否则无法解释扩规模的收益来源。 深化与验证：[[AI/20-LLM/30-训练/14-预训练数据配方去重课程与消融|预训练数据配方去重课程与消融]]；[[AI/20-LLM/10-原理/07-语言模型目标分词粒度与评测可比性|语言模型目标分词粒度与评测可比性]]。


## 本课目标

- 把“收集网页文本”拆成来源登记、清洗、去重、切分、tokenization 和 packing；
- 区分训练 tokenizer 与用固定 tokenizer 编码文本；
- 解释 padding、packing、文档边界、causal mask 与 loss mask 的职责；
- 设计一个**从随机初始化开始**、真的执行 next-token 学习的微型预训练，而不是调用现成模型伪装训练；
- 分别用实际处理位置 $T_{processed}$ 与监督位置 $T_{loss}$ 估算硬件成本、训练预算和 loss normalization；
- 在训练前发现许可、隐私、secret 与评测污染风险。

## 数学先修（第一次使用）

预训练主线最小化 next-token 负对数似然。概率、NLL 与 PPL 的定义和推导统一见 [[数学/30-概率与统计/03-似然负对数似然与困惑度|似然、负对数似然与困惑度]]；本页只说明数据怎样成为这个目标的输入。参数怎样从损失得到梯度，留到 [[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]。

## 直觉：先建可追溯食材链，再开炉

训练语料像食材，tokenizer 像切法，packing 像装盘，模型训练像按同一规则反复试吃并调整配方。切得再快，也无法修复无权使用、夹带密码或把考试答案混进训练集的数据。

真正可复现的输入不是一个名为 `final_clean_v7` 的大文件，而是：

```text
原始来源清单 + 许可/同意状态 + 获取时间 + 不可变快照哈希
  + 每一步清洗配置与统计
  + 分组/切分规则
  + tokenizer 文件与哈希
  + packing/mask 规则
  + 最终 shard 清单与哈希
```

## 精确定义

- **文档（document）**：具有来源、边界和稳定 ID 的最小治理单位，例如一篇文章或一段完整对话；它不一定等于一个训练序列。
- **样本（sample）**：数据管道交给训练器的一个逻辑实例；一个样本可被截断、拆分或与别的样本一起 packing。
- **语料库（corpus）**：按明确纳入规则组成的文档集合，并带来源与版本记录。
- **清洗（cleaning）**：依据可记录规则修复或排除解析失败、乱码、模板噪声、危险内容或不满足质量门槛的文档。
- **去重（deduplication）**：识别同一或高度相似内容的多个实例，并按保留规则分组、删除或隔离；它不是普通质量过滤。
- **tokenizer**：把文本映射为 token ID 序列并能反向解码的固定规则及资产，通常包含规范化、预切分、子词模型、词表、特殊 token 和后处理。
- **训练 tokenizer**：只用训练语料估计子词/字节单元和词表；这会从数据学习统计。
- **编码（tokenization/encoding）**：用已经固定的 tokenizer 把某段文本转成 ID；不会更新模型参数。
- **packing**：把多个短 token 序列紧密放进固定长度 block，以减少 padding；是否允许跨文档注意力必须另行规定。
- **预训练**：从随机初始化或既有权重出发，用自监督目标学习语料分布。本课的“微型从零预训练”特指随机初始化的 decoder-only 模型学习 next-token NLL。

## 数据管线：顺序为什么重要

### 1. 先登记权利、来源和不可变原始快照

为每个来源记录：来源 ID、获取方式、获取日期、内容范围、许可/同意依据、地域或用途限制、原始哈希、负责人和删除请求通道。原始区只读，清洗产物另建版本；否则无法说明某条记录从哪里来，也无法重做过滤。

“网上能看”不等于允许自动抓取、训练、再分发或商用。robots 规则、站点条款、版权、隐私、数据库权利与模型许可证属于不同约束，不能用一个“公开”字段代替。

### 2. 可靠解码与结构恢复

先验证字节编码、Unicode、压缩包和文件格式，再抽取正文、标题、语言、时间与来源字段。保留原始 ID；不要只留下清洗后文本。常见失败包括 mojibake、PDF 断词、HTML 导航栏重复、JSON 转义层级错误和多轮对话角色错位。

### 3. 规则化清洗，但不抹掉语义

可以处理：空文档、控制字符、重复模板、极端乱码、解析失败、明显广告壳与不符合纳入范围的语言。每条规则要输出“扫描数、命中数、保留/隔离/删除数”和代表性样本。

不要为了“干净”盲目：

- 把所有空白合并会破坏代码缩进和表格；
- 全部转小写会改变专名、缩写和代码；
- 删除标点会改变自然语言和 tokenizer 分布；
- 用关键词大批删除敏感主题会产生不可见的代表性偏差。

### 4. PII、secret 与高风险材料

扫描邮箱、手机号、地址、账号标识、访问令牌、私钥、医疗/财务记录等只是候选发现，不能证明完全无敏感数据。命中项应按政策做隔离、脱敏或删除，并保留不含原文的处置记录。不要把真实 secret 放进日志、测试样本或“负例”。

### 5. 精确去重与近似去重

先做**规范化后的精确哈希**：例如只统一可安全统一的换行和外层空白，再对完整文档哈希。保留原始哈希和规范化规则版本，避免不同文本被过度折叠。

近似重复需要比较片段集合或向量相似度。常见工程路线是 shingling + MinHash/LSH 生成候选，再对候选做更精细比较和人工抽样。它能降低全对全比较成本，但阈值会产生：

- **假阳性**：两个合法不同文本被判重复，导致代表性丢失；
- **假阴性**：改标题、插广告、翻译或轻度改写绕过去重，导致重复仍在。

去重单位要与风险对应：代码许可证头、新闻转载、同一对话的多个导出、同一作者跨站发布不应只靠一个全局阈值决定。

### 6. 以“信息不会跨界”为目标切分

先确定不可跨集合的分组键，再切 train/dev/test。可能的分组单位包括原始文档、网站、作者、会话、仓库、时间窗口或事件。若同一人的连续消息被随机拆到训练和测试，表面测试分数会泄漏上下文。

推荐顺序：

1. 冻结评测来源与测试集合；
2. 用原始 ID、规范化哈希和近似候选排除训练重叠；
3. 在训练集合内部去重并生成版本化 manifest；
4. 只用训练集合拟合 tokenizer 和其他数据驱动预处理；
5. dev/test 只用固定规则编码，不反向调整词表或阈值。

更完整的污染与治理流程见 [[AI/20-LLM/30-训练/09-数据污染评测泄漏与训练治理|数据污染、评测泄漏与训练治理]]。

### 7. 混合数据源：配比也是训练数据的一部分

预训练很少只有一个来源。若来源 $i$ 有 $T_i$ 个可用 token，却以采样概率 $p_i$ 进入训练，那么一次固定 $T_{processed}$ 预算中它的期望贡献由 $p_i$ 决定，而不只是由文件大小决定。上采样低资源语言能提高其可见度，也会增加重复暴露和记忆风险；按原始 token 比例采样则可能让大来源淹没小而重要的领域。

因此 manifest 还要记录：来源集合、过滤后 token 数、采样权重、是否放回采样、最大重复次数、课程学习/权重调度、随机种子，以及每个 optimizer step 实际消费的来源计数。`epoch` 在混合或流式数据中尤其容易误导：应按来源同时报告 $T_{processed}$、$T_{loss}$、覆盖率和重复率。改变去重或 tokenizer 后 token 数会变化，旧采样权重不能未经重算直接复用。

一个最小审计表应能回答：

|问题|需要的证据|
|---|---|
|小来源是否被过度重复？|文档唯一数、每文档曝光次数分布、按来源 $T_{processed}$/$T_{loss}$|
|大来源是否垄断更新？|每 step/每阶段的来源计数与累计比例|
|课程学习是否偷偷看了 test？|调度规则只由 train/dev 制定，test 保持冻结|
|质量权重是否放大了偏差？|各语言/领域的保留率、权重变化与人工抽样|

## Tokenizer：学习切法与使用切法是两件事

### 一个 tokenizer 资产至少包含什么

| 组件 | 作用 | 必须验证的边界 |
| --- | --- | --- |
| normalization | 规定 Unicode/空白等怎样规范化 | 是否改变代码、重音、大小写或不可逆字符 |
| pre-tokenization | 在学习子词前建立候选边界 | 空格、标点、CJK、emoji、字节怎样处理 |
| subword/byte model | 决定文本怎样拆成词表单元 | 算法与训练语料版本 |
| vocabulary | token 字符串与整数 ID 映射 | 大小、哈希、保留 ID 与未知字符策略 |
| special tokens | BOS、EOS、PAD、UNK、角色或控制标记 | ID 不冲突，训练与推理语义一致 |
| post-processing | 自动加边界或模板 | 是否重复添加 BOS/EOS，是否改变 label mask |

训练 tokenizer 时只看 train，固定后再编码 dev/test。基础模型微调时通常必须复用与权重匹配的 tokenizer；随意重训词表会使 embedding 行和 ID 语义错位，除非你同时明确调整模型并重新训练相关参数。

### 不只看“压缩率”

需要至少测试：

- `decode(encode(text))` 在允许的规范化边界内能否还原；
- ASCII、中文、组合重音、emoji、代码缩进、换行和异常字节；
- 每种语言的字符/token 或字节/token 分布，避免单一语言极端低效；
- 特殊 token 是否只在规定位置出现；
- 空字符串、超长字符串与未知输入怎样处理；
- tokenizer 文件、配置、词表和实现版本是否一起固定。

## Packing、padding 与 mask

假设 block 长度 $S=8$，两篇文档编码为：

```text
文档 A: [BOS, 11, 12, 13, EOS]
文档 B: [BOS, 21, EOS]
```

直接 padding 得到两个长度 8 的序列，要计算 16 个位置，其中 8 个是 PAD。packing 可把它们装成一个 block：

```text
[BOS, 11, 12, 13, EOS, BOS, 21, EOS]
```

但还要回答两个独立问题：

1. **attention mask**：文档 B 是否允许看到文档 A？连续语料预训练有时允许；样本独立任务通常应使用文档边界 mask。
2. **loss mask**：哪些位置参与损失？PAD、某些控制 token、SFT 的用户 prompt 常被忽略；“能被注意到”不等于“必须作为目标计分”。

还必须把三项容易漏掉的实现语义写入测试：文档边界处预测的是 `EOS`、下一文档的 `BOS` 还是被 mask；position IDs 在新文档处继续还是重置；若要求样本隔离，attention mask 是否真的是 block-diagonal，而不只是“没有 PAD”。只检查 packed token 数没有丢失，不能证明训练条件关系正确。

### Mask 不等于少算

至少维护两本 token 账：

|账本|定义|主要用途|
|---|---|---|
|$T_{processed}$|实际提交给模型并由底层 kernel 处理的位置|FLOPs、显存/吞吐、硬件与时间预算|
|$T_{loss}$|label/loss mask 后进入监督损失与归一化分母的位置|梯度尺度、监督预算、不同 masking 方案比较|

在普通 fixed-shape dense batch 中，PAD 即使不进入 loss，通常仍占张量位置；SFT 的 assistant-only mask 和 prefix mask 也只是不监督 prompt/prefix，模型仍需处理它们才能形成回答 token 的条件表示。普通 attention mask 往 logits 上加屏蔽值，也不等于底层矩阵乘法跳过这些位置。

packing 只有在减少了实际 batch/block 数或配合相应 kernel 时才降低处理位置。真正的 unpadding、packed/varlen kernel 或经过验证的 block-sparse 实现可以跳过一部分 padding/稀疏位置；是否省算必须用实际输入 shape、kernel 路径、profiler 和 $T_{processed}$ 计数证明，不能从 mask 中推断。

自回归训练把输入位置 $t$ 用来预测下一个 token。block 被截断时要记录剩余片段怎样处理；随手丢弃尾部会改变数据分布，循环拼接又可能制造虚假跨 epoch 邻接。

## 一个真实的微型从零预训练

“真实”在这里表示：tokenizer 从训练语料拟合；模型参数随机初始化；每一步都做前向、NLL、反向和 optimizer update；最后用从未参与更新的 validation 比较。模型很小，但过程与大训练共享核心接口。

### 实验设计

| 项目 | 一个可审核的微型选择 | 为什么这样选 |
| --- | --- | --- |
| 数据 | 800 篇自写或明确允许训练的短文档 | 来源与删除边界清楚 |
| 切分 | 按文档来源分 640/80/80 | 不把同文档片段随机泄漏 |
| tokenizer | train-only，词表 512，固定 special IDs | 足以观察切分，又便于检查 |
| 模型 | 4 层、hidden 128、4 heads、随机初始化、权重共享 | 约百万参数量级，仍是完整 decoder-only 模型 |
| block | 128 token，明确文档边界与 loss mask | 成本可控，mask 可单测 |
| 基线 | 训练前 dev NLL/PPL；一个 batch 过拟合 | 先证明数据—模型—损失接线正确 |
| 主跑 | 分别固定/记录 $T_{processed}$ 与 $T_{loss}$，定期保存 full checkpoint | 不用“若干 epoch”掩盖处理成本或监督量差异 |
| 结论 | dev NLL、样本生成、污染扫描、失败与限制 | 训练损失下降不是唯一证据 |

概念流程如下；这是**不可直接运行的伪代码**，可运行实现放在实践页：

```text
load immutable manifest
assert licenses_and_consent_are_recorded
train_docs, dev_docs, test_docs = grouped_split(documents)
assert no_exact_or_reviewed_near_overlap(train_docs, dev_docs, test_docs)

tokenizer = fit_tokenizer(train_docs_only)
train_blocks = tokenize_pack_and_mask(train_docs, tokenizer)
dev_blocks = tokenize_pack_and_mask(dev_docs, tokenizer)

model = randomly_initialize_small_decoder()
record(validation_nll_before_training)
assert can_overfit_one_tiny_batch(model)

for each optimizer_step within fixed_token_budget:
    accumulate_next_token_gradients(train_blocks)
    update_parameters_and_scheduler()
    periodically_evaluate_and_save_full_state()

restore_latest_checkpoint_in_fresh_process()
evaluate_once_on_frozen_test_set()
```

完整可修改实验入口：[[AI/80-实践/01-微型Transformer预训练/00-微型Transformer预训练|微型 Transformer 预训练实验]]。

## 流程与成本模型

### 数据量与步数

若每个 rank 的 micro-batch 是 $B_\mu$ 条序列、长度 $S$、梯度累积 $A$ 次、data-parallel 副本 $D$ 个，则 fixed-shape dense 实现每个 optimizer step 的处理位置上限为

$$
T_{processed,step}=B_\mu\times S\times A\times D.
$$

监督位置则为

$$
T_{loss,step}=\sum \text{loss\_mask},
$$

且通常 $T_{loss,step}\le T_{processed,step}$。若训练预算定义为累计 $L$ 个监督 token，步数近似为 $\lceil L/\overline{T_{loss,step}}\rceil$；若目标是按 sampler 遍历固定样本一遍，optimizer step 数由样本/batch/尾批规则决定，单纯改变 loss mask 不会增加或减少这一遍的 batch 数。硬件工作量则按累计 $T_{processed}$ 记录。

**例子**：单设备 $D=1$，$B_\mu=2$、$S=128$、$A=4$，dense 路径每步最多处理 1,024 个位置。若平均只有 90% 位置参与损失，则 $\overline{T_{loss,step}}\approx921.6$。累计处理 800,000 个位置约需 782 步；累计监督 800,000 个 token 则约需 $\lceil800,000/921.6\rceil=869$ 步。若只是遍历一个固定样本集合，仍应直接从 batch 数计算 epoch 步数。

### 存储与计算

- 原始快照、清洗中间产物、tokenized shards 和 checkpoint 会同时存在；磁盘预算不能只看最终数据文件。
- token ID 若按固定整数宽度保存，粗略数据体积为 token 数乘每 ID 字节数，再加索引、边界、mask、压缩和文件系统开销。
- dense Transformer 全参数预训练可用约 $6N T_{processed}$ FLOPs 作量级估算，其中 $N$ 要声明是否按常见口径排除 embedding，$T_{processed}$ 是实际由模型/kernel 处理的位置；$T_{loss}$ 只描述监督与归一化，不能代入硬件成本。LoRA/冻结参数、重计算、具体架构与 kernel 会改变常数和适用范围，因此它不是具体硬件耗时承诺。
- tokenizer 训练和近似去重也有独立 CPU/内存/临时磁盘成本；大语料必须先小样本估算峰值。

## 训练前质量门

只有以下证据同时存在才进入主训练：

- 来源 manifest、许可/同意状态和原始哈希可读；
- 清洗、PII/secret 扫描、精确与近似去重都有统计和抽样复核；
- train/dev/test 按正确单位隔离，评测重叠已经扫描；
- tokenizer 只在 train 上拟合，特殊 ID、往返和多语言/代码样例测试通过；
- packing 不丢 token、不重复计分，attention/loss mask 与设计一致；
- 随机初始化模型的 loss 有合理量级，一个极小 batch 可以明显过拟合；
- 训练前 dev 基线、配置、种子、代码/环境标识与磁盘上限已经记录。

## 常见失败与定位

| 现象 | 优先检查 | 不要立刻下的结论 |
| --- | --- | --- |
| loss 完全不降 | label shift、mask、梯度、学习率、token ID 范围 | “模型太小” |
| train 降、dev 不降 | 重复、分布差异、过拟合、错误切分 | “需要更多 epoch” |
| PPL 异常好 | 测试泄漏、重复、padding 是否计入、tokenizer 是否一致 | “架构领先” |
| 生成只有特殊 token | BOS/EOS/PAD ID、post-processing、loss mask | “采样器坏了” |
| token 数暴涨 | Unicode/字节回退、目标语言覆盖、错误解码 | “语料更丰富” |

## 安全、许可与资源边界

- 只对有明确权利和用途依据的数据运行训练；不把“教育实验”当作绕过许可、隐私或保密义务的理由。
- 原始文本、训练 shards、缓存、日志和 checkpoint 都可能包含可恢复样本；访问控制和删除流程要覆盖全部副本。
- 不在示例里保存真实 PII、secret、私有 URL 或 gated 模型访问凭据。
- 先限制文档数、token 数、进程数、worker、内存、临时磁盘和训练时长；观察到解析炸弹、磁盘异常增长或 OOM 循环时停止。
- 数据清洗会改变代表性；记录按来源/语言/类别的保留率，避免一个全局质量分把小语种或特定写作风格系统性删除。
- 工具接口和 tokenizer 实现版本只从 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 进入官方来源并在实施时固定；本页没有下载或运行任何外部模型/数据。

## 练习

### 练习 1：为一组短文设计 manifest

选择 20 篇你有权使用的短文本，只写字段设计，不放真实敏感内容。字段至少包含 source ID、document ID、许可/同意状态、原始哈希、语言、时间、split group、清洗状态和删除状态。

### 练习 2：手工检查 packing

把长度分别为 5、3、7 的三个 token 序列装入长度 8 的 block。写出：

1. 是否跨文档；
2. attention mask 是否阻断跨文档可见性；
3. loss mask 排除哪些位置；
4. 不能装下的尾部怎样处理。

### 练习 3：计算训练步数

目标是累计 1,200,000 个 $T_{loss}$，$B_\mu=3$、$S=256$、$A=2$、$D=2$，使用 fixed-shape dense kernel。计算每步 $T_{processed}$；若平均 12% 位置被 loss mask，估算每步 $T_{loss}$、所需 optimizer steps 与累计 $T_{processed}$。再说明如果问题改成“对一个固定样本集合跑一遍 epoch”，为什么 mask 不会改变 batch 数。

<details>
<summary>核对要点</summary>

- 每步 $T_{processed}=3\times256\times2\times2=3,072$；12% 被 mask 时，平均 $T_{loss}\approx2,703.36$。
- 监督预算约需 $\lceil1,200,000/2,703.36\rceil=444$ 步，对应累计 $T_{processed}=444\times3,072=1,363,968$ 个位置。实际运行应累计整数 mask 计数，不使用长期小数替代日志。
- 固定样本集合的一遍 epoch 有多少 batch 由 sampler、batch 与尾批规则决定；loss mask 改变监督量和梯度归一化，不会自动改变 batch 数或 dense kernel 的 shape。
- packing 方案不唯一，但必须能从 block 还原文档边界，并明确尾部、EOS、attention 和 loss 的规则。

</details>

## 成功标准

- 能清楚区分清洗、去重、切分、训练 tokenizer、编码与 packing；
- 能指出为什么评测集合要先冻结，tokenizer 只能在 train 上拟合；
- 能画出从原始文档到 input IDs、labels、attention mask 与 loss mask 的对应关系；
- 能设计一个随机初始化、真实更新参数、有 train/dev/test 与 checkpoint 的微型预训练；
- 能分开累计 $T_{processed}$ 与 $T_{loss}$，分别用于硬件成本、监督预算和 loss normalization；
- 能说明 assistant-only、prefix/PAD mask 为什么不自动减少 dense 计算，以及何种 unpadding/packed/varlen/sparse 实现才可能减少处理位置；
- 能说明去重扫描、PII 扫描和许可登记各自不能证明什么。

## 导航

- 返回模块：[[AI/20-LLM/30-训练/00-LLM训练-MOC|LLM 训练 MOC]]
- 上一级：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
- 下一站：[[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]]
- 污染与治理：[[AI/20-LLM/30-训练/09-数据污染评测泄漏与训练治理|数据污染、评测泄漏与训练治理]]
- 原理先修：[[AI/20-LLM/10-原理/01-文本Unicode-Token与词表|文本、Unicode、Token 与词表]]
- 实践：[[AI/80-实践/01-微型Transformer预训练/00-微型Transformer预训练|微型 Transformer 预训练实验]]
- Python 数据处理：[[计算机知识/10-编程语言/01-Python/04-容器迭代器生成器与推导式|容器、迭代器与生成器]]、[[计算机知识/10-编程语言/01-Python/05-异常文件IO与上下文管理|异常、文件 I/O 与上下文管理]]
- 版本核验：[[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]
