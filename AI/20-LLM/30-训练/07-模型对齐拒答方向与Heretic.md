---
type: lesson
aliases:
  - 模型对齐、拒答方向与 Heretic
  - Heretic 定向消融
domain: artificial-intelligence
stage: 3
status: ready
difficulty: 中级到进阶
estimated_minutes: 100
verified: 2026-09-01
topics:
  - model-alignment
  - refusal-direction
  - directional-ablation
  - residual-stream
  - TPE
  - KL-divergence
  - private-deployment
tags:
  - ai/llm/training
  - ai/llm/alignment
  - ai/model-editing
---

# 模型对齐、拒答方向与 Heretic

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 某个方向能够改变拒答，不代表已定位独立、唯一、可安全删除的概念。读出相关性、因果干预、附带能力损失和隐私边界应分别评估。 深化与验证：[[AI/20-LLM/80-研究拓展/01-机制可解释性Probe干预与稀疏特征|机制可解释性Probe干预与稀疏特征]]；[[AI/20-LLM/80-研究拓展/04-隐私记忆成员推断与机器遗忘|隐私记忆成员推断与机器遗忘]]。


> [!abstract] 本课目标
> 学完后，你应当能：
> 1. 把“拒答方向”说成一个依赖数据、层、token 位置和度量的表示假设，而不是模型内部的一枚安全开关；
> 2. 解释 residual direction、正交投影与 directional ablation 的关系；
> 3. 说明 TPE 搜索和 KL scorer 分别优化什么、又不能证明什么；
> 4. 设计原模型与修改模型的成对评测，至少分开拒答、KL、语言质量、通用能力与安全结果；
> 5. 在不覆盖原权重、不上传数据、默认不开放网络的前提下规划一次可恢复实验。

> [!warning] 研究边界
> **减少拒答只说明某类输入上拒绝作答的频率或强度发生了变化。**它不自动提高答案正确性、语言质量、通用能力、安全性、合法性或许可证合规性，也不证明模型“解除偏见”“恢复真实知识”或“更诚实”。减少过度拒答可能改善某些正常任务的可用性；减少必要拒答也可能显著扩大误用和伤害面。二者必须用分层、成对且预先定义的评测来区分。

> [!note] 当前证据状态
> 本页依据 2026-09-01 的 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 与 [Heretic 官方仓库](https://github.com/p-e-w/heretic) 讲解方法和实验纪律。**本次没有下载仓库、模型或数据，没有安装、编辑权重、运行评测、启动服务或验证任何版本的性能数字。**支持架构、参数名、默认搜索空间、依赖、CLI 和 scorer 实现都属于快速变化事实；真正实验前须固定仓库 commit，并以该 commit 的文档和源码重新核对。

## 1. 先把“对齐”和“拒答”拆开

“模型对齐”是一个宽泛目标：模型行为需要与产品规则、用户意图、风险政策、事实要求及适用法律协调。拒答只是其中一种可观察行为，而且至少要区分：

|现象|可能解释|单看拒答率能否判断好坏|
|---|---|---|
|对明确危险请求拒答|安全策略按预期工作|不能；还要看绕过、变体和非拒答答案|
|对正常医疗、教育或代码请求也拒答|过度拒答，损害效用|不能；还要人工判断请求是否确实无害|
|不拒答但只给安全的概述|有条件帮助或风险降级|不能；二元拒答标签会漏掉这种差异|
|不拒答并输出危险细节|安全退化|不能；“更愿意回答”不是质量|
|拒答措辞变短，但危险内容仍泄露|表面行为变化|不能；必须检查完整输出内容|

因此，本课不把“原模型”预设为正确，也不把“修改模型”预设为更好。实验要回答更窄的问题：

1. 在预先标注的请求集合上，拒答行为改变了多少？
2. 修改对非目标分布造成了多大概率分布漂移？
3. 正常语言质量和通用任务能力是否保持？
4. 安全、隐私、偏差和滥用风险是否恶化？
5. 这些结论能否跨模板、语言、主题、随机种子和解码设置复现？

## 2. 什么是 residual direction

Transformer 每一层都会维护并更新 residual stream。为方便讨论，记第 $\ell$ 层、某个指定 token 位置的 residual 表示为 $h_\ell(x)\in\mathbb R^d$。研究者可以在两组对照输入上提取表示：

- $R$：在原模型上倾向触发拒答的样本；
- $C$：与 $R$ 在语言、长度、主题、模板等方面尽量匹配，但不应触发同类拒答的控制样本。

最简单的候选方向是两组均值之差，再做单位化：

$$
\tilde r_\ell
=\operatorname{mean}_{x\in R}h_\ell(x)
-\operatorname{mean}_{x\in C}h_\ell(x),
\qquad
r_\ell=\frac{\tilde r_\ell}{{\|\tilde r_\ell\|}_2}.
$$

这里的 $r_\ell$ 可称为该实验定义下的 **residual direction**。它是一个统计对比量，不是从模型中直接读出的“拒答神经元”。它依赖：

- 选了哪一层、哪个 token 或哪些 token 的聚合；
- 使用 base prompt、chat template、system prompt 还是生成中的 token；
- 正例和控制例如何配对；
- 激活是否中心化、归一化或跨层合并；
- 模型 revision、tokenizer、dtype 和推理实现；
- 拒答标签来自规则、分类器还是人工复核。

> [!important] 最危险的混杂
> 如果 $R$ 全是长英文危险请求，而 $C$ 全是短中文普通请求，均值差可能主要编码语言、长度、主题或模板。即使消融后拒答减少，也不能据此断言找到了因果性的“拒答方向”。最低限度应有成对控制、训练/验证/测试隔离、不同主题和语言的复现，以及对随机方向或无关方向的负对照。

## 3. directional ablation 与正交投影

若 $r$ 已单位化，向量 $h$ 在该方向上的分量是 $(r^\mathsf Th)r$；从表示中移除这部分可写成：

$$
h'=h-(r^\mathsf Th)r=(I-rr^\mathsf T)h.
$$

这就是单方向正交投影的方向消除形式。完整推导、多个方向组成的子空间、非正交基和数值稳定性统一放在数学权威页：[[数学/20-线性代数与几何/05-正交投影子空间与方向消除|正交投影、子空间与方向消除]]。本页只讨论它在模型编辑中的解释和证据边界。

### 3.1 在激活上干预，还是在权重上编辑

概念上至少有两条路径：

1. **运行时激活投影**：在前向传播到特定层时，把 residual 表示投影到 $r$ 的正交补；适合做可撤销的因果探针，但需要 hook，且运行时持续发生。
2. **权重定向消融**：修改会写入或读取 residual stream 的某些线性映射，使指定方向的写入/读取能力减弱；得到新的权重产物，不再依赖同一 hook。

如果矩阵 $W$ 的**输出空间**与 $r$ 同维，左乘 $(I-rr^\mathsf T)W$ 是从输出中移除该方向；如果其**输入空间**与 $r$ 同维，右乘 $W(I-rr^\mathsf T)$ 是阻止读取该方向。两者作用不同，维度也可能不同，不能因为都出现投影矩阵就互换。具体工具修改哪些矩阵、层和模块，必须以固定 Heretic commit 的实现为准，不能由本页公式反推。

### 3.2 消融强度不一定只能是 0 或 1

实验可能使用强度 $\alpha$：

$$
h'=\left(I-\alpha rr^\mathsf T\right)h.
$$

- $\alpha=0$：不改；
- $\alpha=1$：完全移除选定线性分量；
- 其他值：缩放而非完全消除。

这只是便于理解的通式，不代表某个 Heretic 版本的参数名或允许范围。更大的编辑强度、更多层或更宽的方向子空间，常会带来更强行为变化，也可能造成更广泛能力损伤；实际关系需要测量，不能由公式保证。

### 3.3 方向消融不能证明什么

即使验证了 $r^\mathsf Th'=0$，也只证明在指定内积、指定位置和该次线性操作下，选定方向分量被移除。它仍不能证明：

- 拒答语义只沿一个方向编码；
- 后续层不会重新构造相似信号；
- 拒答变化来自目标机制，而不是语言能力损伤；
- 方向在别的语言、模板、模型版本或解码设置上稳定；
- 修改后的回答正确、安全或符合政策。

## 4. Heretic 在实验中的角色

本课把 Heretic 看作一个**对 Transformer 权重进行定向消融、搜索候选编辑并对候选打分的研究工具**。一个审慎的概念流程是：

```text
固定原模型、tokenizer、模板与对照数据
  -> 提取各层 residual 表示
  -> 估计一个或多个候选拒答方向
  -> 对 direction index、attention/MLP 层权重核等编辑超参数生成 trial
  -> 每个 trial 产生独立候选，不覆盖原模型
  -> 用拒答、KL 和能力保留信号给 trial 打分
  -> 在未参与搜索的测试集上重新比较
  -> 只有证据充分时才保留候选；否则回到原模型
```

上图是方法地图，不是特定版本的 CLI 契约。真实运行前，应从官方仓库的固定 commit 记录：支持的架构、配置 schema、默认数据、实际 scorer 定义、TPE 库与 sampler 设置、输出格式以及许可证。

## 5. TPE 搜索：它搜索的是目标函数，不是真理

先区分**固定 Heretic 实现的优化变量**与**研究者可能另外设计的实验旋钮**。依据本页核验日的官方 README，Heretic 当时的参数化消融针对 attention out-projection 与 MLP down-projection，并优化：

- `direction_index`：选择一个 residual direction，或使用逐层方向；非整数值还可按该版实现插值；
- 对上述两个组件分别设置的层权重核参数：`max_weight`、`max_weight_position`、`min_weight`、`min_weight_distance`。

同一实现说明还把候选 residual direction 建立在 harmful/harmless prompts 的 first-token residual difference-of-means 上。这些是**核验日实现事实**，不是 Heretic 名称的永久数学定义；实验前必须固定仓库 commit，再从该 commit 的配置 schema、README 与源码重核参数名、允许范围、插值、方向数据和实际被修改矩阵。

更宽泛的 directional-ablation 研究还可能改变：

- 使用哪些层或层区间；
- 方向从哪个位置、哪组样本估计；
- 编辑强度；
- 作用于哪些投影或线性模块；
- 拒答目标与能力保持 scorer 的组合权重；
- 数据切分、随机种子和 trial 预算。

这些项目中有些是方法设计或实验控制，不是上述 Heretic 实现默认交给 TPE 的 candidate variable。尤其随机种子和 trial 预算控制搜索过程，本身不应在没有明确研究设计时与模型编辑参数混为一谈。

Tree-structured Parzen Estimator（TPE）是一类面向昂贵黑箱目标的序贯模型优化方法。直觉上，它会依据已完成 trial 的分数，把较好和较差区域分别建模，再优先提出更可能落入“较好区域”的候选。它比穷举更节省预算，但不保证找到全局最优，也不会修正错误的标签、数据泄漏或目标函数。

下面伪代码只表达核验日 Heretic 参数边界；字段仍是语义占位符，不是可直接复制的 CLI/config schema：

```text
search_split, validation_split, final_test_split = disjoint_splits(dataset)

heretic_space = {
    direction_index,
    attention_out_projection: {
        max_weight, max_weight_position, min_weight, min_weight_distance
    },
    mlp_down_projection: {
        max_weight, max_weight_position, min_weight, min_weight_distance
    },
}

for trial in TPE.ask(heretic_space, fixed_seed, fixed_budget):
    candidate = heretic_directional_ablation(
        immutable_original,
        direction_index=trial.direction_index,
        attention_kernel=trial.attention_out_projection,
        mlp_kernel=trial.mlp_down_projection,
    )
    trial_score = score_refusal_and_preservation(
        candidate,
        reference=immutable_original,
        data=search_split,
    )
    TPE.tell(trial, trial_score)

selected = choose_with_predeclared_rule(validation_split)
report_once(selected, final_test_split)
```

### TPE 的四个证据陷阱

1. **把测试集用于搜索。** 搜索看过的样本已经是训练信号，不能再作为最终泛化证据。
2. **把复合分数当成客观单位。** “拒答下降 1 点”和“KL 上升 1 点”没有天然可比尺度；权重变化会改变最优候选。
3. **只报告最佳 trial。** 多次搜索会产生选择偏差；应保留所有 trial、失败和随机种子。
4. **搜索空间决定结论。** 没有搜索到的 direction index、层权重核形状，或研究设计中根本未纳入的模块，不代表它们更差；预算不足也可能错过更稳健的候选。

建议先登记搜索空间、方向、预算、seed、停止规则和选择规则；最后报告 Pareto 前沿，而不是只给一个混合总分。例如同时展示“拒答变化”和“能力漂移”，让读者看到取舍。

## 6. KL scorer：测分布漂移，不替代质量评测

对同一个前缀，记原模型的下一 token 分布为 $p_{\text{orig}}$，修改模型为 $p_{\text{edit}}$。一种能力保持代理是，在良性/通用文本上计算：

$$
D_{\mathrm{KL}}\!\left(p_{\text{orig}}\,\|\,p_{\text{edit}}\right).
$$

KL 散度的定义、方向性、非负性与使用条件见 [[数学/50-信息论/01-熵交叉熵KL散度与互信息|熵、交叉熵、KL 散度与互信息]]；本页不复制完整推导。

### 使用 KL scorer 时必须记录

- 方向是 $D_{\mathrm{KL}}(p_{\text{orig}}\|p_{\text{edit}})$、反向还是对称化变体；
- 在 prompt token、回答 token 还是完整序列上计算；
- tokenizer、chat template、mask、截断、温度和 logits dtype；
- 按 token、序列还是样本如何归约，是否对长度加权；
- scorer 数据来自搜索集、验证集还是最终测试集；
- 对数概率和 softmax 是否使用数值稳定实现。

**低 KL** 只说明在所测语料和归约方式上，修改模型的 token 分布接近原模型。它不证明两个模型生成同样的长文本，也不证明正确性、推理能力或安全性保持。**高 KL** 表示分布变化较大，但也不自动说明质量下降：修改可能修复原模型的错误。KL 是漂移报警器和代理指标，不是最终裁判。

还要避免循环论证：如果原模型本身在某类正常任务上过度拒答，让修改模型在这些位置保持极低 KL，可能与“减少过度拒答”的目标冲突。评测应把目标域和能力保持域明确分开。

## 7. 最低可接受的对照评测

始终使用**完全相同**的 tokenizer、chat template、system prompt、采样参数、最大长度和数据顺序比较原模型与修改模型。若确需改变其中一个变量，应另开消融组，不能把差异归因于权重编辑。

|评测维度|应记录的指标|它能支持的窄结论|它不能支持的结论|
|---|---|---|---|
|拒答行为|危险集拒答率、良性集过度拒答率、部分回答/安全改写比例；人工复核混淆矩阵|所定义数据和标签上，拒答行为如何改变|总体质量、安全或“更少审查”|
|KL / 分布漂移|原模型到修改模型的 token KL、分位数、按主题/语言分层|良性参考语料上的局部概率分布变化|长程生成等价、事实正确或能力保持|
|语言质量|盲评流畅性、连贯性、重复、乱码、截断、指令遵循；成对偏好及置信区间|输出可读性或退化迹象|知识正确、推理正确或安全|
|通用能力|覆盖多个任务族的固定测试：知识、推理、数学、代码、长上下文；准确率/通过率与方差|所测任务、版本和设置上的能力差值|未测领域、真实生产表现或无损编辑|
|安全与滥用|危险内容合规率、越狱稳健性、隐私泄露、偏差、工具调用边界；由合格审阅者按风险分层|所测威胁模型上的风险变化|法律合规、所有攻击都安全或可公开部署|
|运行稳定性|加载成功、NaN/Inf、显存、延迟、崩溃、确定性|该硬件与固定版本下的工程可运行性|更高质量、更安全或跨平台兼容|

### 7.1 拒答标签不要只靠关键词

只搜索“不能”“抱歉”等词会把安全替代方案误判为拒答，也会漏掉没有拒答措辞却不给实质答案的输出。建议：

1. 先定义互斥标签：完全拒答、带安全替代的拒答、有限帮助、正常回答、危险配合、不可判定；
2. 分类器或正则只做初筛；
3. 对边界样本和随机样本做盲人工复核；
4. 报告标注指南、复核比例和一致性，而不是只报单个拒答百分比。

### 7.2 能力保持需要效应量和不确定性

“分数只下降 0.3”没有样本数和方差就无法解释。对成对结果报告绝对差、相对差、置信区间或 bootstrap 区间；这些量的定义、抽样单位与适用边界见 [[数学/30-概率与统计/05-统计估计置信度与模型评测|统计估计、置信度与模型评测]]。对生成任务使用多个固定 seed。预先定义可接受退化阈值，并把未达到统计分辨率写成“证据不足”，不要写成“能力完全保持”。

### 7.3 安全和合规是独立门

- **安全**：需要基于用途和威胁模型的危险输出审查；低拒答率通常会扩大需要审查的范围。
- **政策/法律合规**：取决于部署地、行业、数据、用户、模型许可与组织政策；技术分数不能代替合规意见。
- **许可合规**：工具、原模型、修改后权重、数据集、评测集和推理服务依赖分别适用自己的条款。

如果修改模型在安全测试上显著恶化，即使 KL 很低、通用能力不降，也不应进入服务阶段。

## 8. 实验数据：配对、隔离和最小暴露

推荐至少拆成四个互不重叠的集合：

1. `direction_train`：只用于估计方向；
2. `search_objective`：只用于 TPE trial 打分；
3. `selection_validation`：选择候选和阈值；
4. `final_test`：冻结方案后只评一次。

数据条目使用稳定 ID，原始危险文本与结果分离存放。报告可保存类别、哈希、标签和聚合结果，避免把高风险提示、个人数据或受限测试集原文复制进 Git、日志或笔记。任何云 API、遥测或上传都不属于本课默认路线。

### 建议的负对照

- 同维度随机方向；
- 从打乱标签的数据估计的方向；
- 不编辑权重但执行完整保存/加载流程的 sham candidate；
- 与目标层数相同、但位于无关层区间的候选；
- 不同模板、语言和主题上的外部分布测试。

只有目标方向相对这些对照表现出稳定、特异且可复现的效果，才可以谨慎地说“证据支持该方向与所测拒答行为有关”。仍不应把它升级成唯一机制或完整因果解释。

## 9. 原模型、修改模型和评测产物必须分开

推荐使用同一实验根目录下的明确分区；实际绝对路径由操作者填写，不在命令历史里拼接 token：

```text
heretic-lab/
├── source/
│   └── heretic-<commit>/          # 工具源码快照；记录 AGPL 义务
├── models/
│   ├── original/<model-revision>/ # 只读原模型、tokenizer、模型卡与哈希
│   └── edited/<experiment-id>/    # 修改权重；永不覆盖 original
├── data/
│   ├── restricted/                # 不进 Git；最小权限
│   └── manifests/                 # ID、来源、revision、许可、哈希
├── runs/<experiment-id>/
│   ├── config/                    # 搜索空间、seed、环境锁定
│   ├── directions/                # 层、位置、估计法与方向哈希
│   ├── trials/                    # 每个 TPE trial 的参数和状态
│   └── logs/                      # 经脱敏的运行日志
└── evaluations/<experiment-id>/
    ├── raw-private/               # 原始输出；不进 Git，不上传
    ├── summaries/                 # 分层指标、置信区间、失败案例 ID
    └── report.md                  # 结论、限制与复现清单
```

### 三类产物的最小清单

|产物|必须记录|不要混淆|
|---|---|---|
|原模型|发布者、仓库 ID、不可变 revision、文件与 SHA-256、tokenizer、chat template、模型卡、模型许可/可接受使用条款|缓存路径不是模型身份；同名量化也不是同一权重|
|修改模型|原模型指针、Heretic commit、完整配置、数据 manifest、方向与 trial ID、变更张量列表、输出哈希、修改模型的分发条件|工具 AGPL 不会自动授予模型权重权利|
|评测产物|数据集/评测集版本与许可、prompt ID、scorer 版本、采样参数、硬件/软件环境、原始结果哈希、汇总脚本版本|汇总分不能替代原始失败样本和安全复核|

### 推荐 `.gitignore` 边界

把下面规则放在**实验项目自己的** `.gitignore`，而不是盲目复制到 Vault 根；是否保留脱敏小型汇总由项目决定：

```gitignore
# 权重与导出
/models/original/
/models/edited/
*.safetensors
*.bin
*.pt
*.pth
*.gguf

# 模型/框架缓存
/.cache/
/cache/
/hf-cache/
/torch-cache/

# 受限数据与原始输出
/data/restricted/
/evaluations/*/raw-private/
/runs/*/logs/

# 密钥与本地环境
.env
.env.*
*.key
*.pem
```

不要忽略 provenance manifest、许可证记录和经过审核的聚合报告，否则无法解释输出来自哪个输入。也不要依赖 `.gitignore` 撤回已经提交的敏感文件；提交前应检查 Git 索引和历史。

## 10. 许可证必须分账

截至本页核验日，Heretic 官方仓库记录的工具许可证为 **AGPL-3.0-or-later**。这只描述工具代码的许可，不等于：

- 原模型权重变成 AGPL；
- 获得基础模型的商用、再分发或衍生权重发布权；
- 数据集、评测集或生成输出可以任意公开；
- 通过网络提供修改版工具服务时没有源码提供义务。

每次实验分别保存并审阅：

1. Heretic 固定 commit 对应的 LICENSE 与本地修改；
2. 原模型模型卡、权重许可和可接受使用条款；
3. 修改后模型是否被原许可视为衍生物，以及标注/再分发要求；
4. 方向估计数据、评测数据及其输出使用条款；
5. 容器镜像、推理运行时和其他依赖的许可。

AGPL 的网络交互条款、模型许可或数据许可对具体部署的影响可能需要法律/合规复核。本页是工程检查清单，不是法律意见。

## 11. 默认路线：离线或仅回环的容器实验

容器优先是为了固定用户态依赖、限制写入范围并便于清理，不是为了宣称“绝对安全”。GPU、host kernel、NVIDIA 驱动和容器 runtime 仍属于宿主机信任边界。

### 11.1 容器配置基线

- 镜像固定 digest，不使用会漂移的 `latest`；保存 Dockerfile/Containerfile 与构建来源。
- 编辑阶段默认 `network=none`；提前准备的模型和源码以只读 mount 进入。
- 原模型只读挂载；只给 `models/edited/<experiment-id>`、`runs/<experiment-id>` 和必要缓存独立可写目录。
- 非 root 用户运行；不使用 privileged、host PID、host IPC、host network，也不挂载容器 socket。
- GPU 只暴露实验需要的设备；限制 CPU、内存、共享内存和文件描述符。
- 不把 Hub token、SSH key 或整个人目录挂进容器；确需 secret 时使用只读临时 secret mount，并关闭日志回显。
- 输出先落私有目录，完成哈希和许可检查后才决定是否保留；默认不上传。

下面只是**门禁骨架**，故意没有填工具命令；直接复制会在门禁处退出：

```bash
HERETIC_EXECUTE="${HERETIC_EXECUTE:-NO}"
if [ "$HERETIC_EXECUTE" != "I_REVIEWED_LICENSE_DATA_AND_OUTPUT_PATHS" ]; then
  printf '%s\n' 'Blocked: review immutable input, licenses, data and output paths first.'
  exit 64
fi

# 在这里填入已核对的固定镜像 digest、只读输入 mount、独立输出 mount、
# --network=none、非 root 用户、GPU 范围和固定 Heretic commit 对应命令。
false  # 未经逐项替换和复核，仍然拒绝执行
```

### 11.2 Ubuntu、Arch native 与容器的差别

|路线|优点|责任边界与风险|
|---|---|---|
|容器（默认）|用户态依赖与实验产物容易分区；可复现镜像|仍依赖 host GPU、driver 与 Container Toolkit；镜像 CUDA 不能修复 host driver|
|Ubuntu native|当具体 Ubuntu 版本在 NVIDIA 支持表中时，可按官方 validated 路线匹配 driver/Toolkit；LTS 变化较慢|不要混用 Ubuntu 仓库、NVIDIA 仓库和手工安装；升级前核对具体版本矩阵|
|Arch native|包路径与滚动系统一致，适合熟悉 Arch 全量升级纪律的用户|Arch 通常不在 NVIDIA validated distribution table；kernel、driver、compiler、Toolkit 要作为滚动组合验证，不能复制 `apt`/NVIDIA Ubuntu 步骤|

系统分层与当前支持矩阵的核验方法见 [[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]]；Linux 学习入口见 [[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]，发行版包管理边界见 [[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|pacman、apt、dnf 与 yum 包管理]]，进程、权限和服务隔离见 [[计算机知识/20-操作系统/01-Linux/06-用户权限进程与作业控制|用户、权限、进程与作业控制]]。

不要在原生 Ubuntu 或 Arch 路线中先卸载现有驱动“重来”，也不要让容器安装 host kernel driver。任何 driver、Toolkit、包仓库或内核变更都是本课之外的系统级任务，需要独立备份与恢复计划。

## 12. 私有服务：默认只监听 loopback

Heretic 的模型编辑与修改后模型的推理服务是两个阶段。只有离线评测通过且确有交互需要时，才用**另一个固定版本的推理运行时**加载修改权重。默认配置必须是：

```text
service_enabled = false
bind_host = 127.0.0.1
allow_lan = false
allow_public = false
upload_enabled = false
telemetry_enabled = false
```

若服务启动，先在宿主机检查实际监听，而不是相信配置文件：

```bash
PORT="${PORT:?Set the exact local service port for a read-only check}"
ss -lntp "sport = :$PORT"
```

可接受的默认结果应只出现 `127.0.0.1:<port>`，IPv6 使用时只出现 `[::1]:<port>`。如果出现任意网卡通配地址或非预期接口，立即停止服务并回到 loopback 配置。日志不得记录完整 prompt、完整 response、认证 secret 或个人数据。

### 12.1 LAN 是显式例外，默认关闭

本课**不提供公网暴露路线**。LAN 访问只有在所有以下条件都满足，并经负责人显式开启后才可考虑：

1. **显式开关**：`allow_lan=false` 是持久默认值；一次变更需记录负责人、目的、到期时间、客户端 IP/CIDR、精确服务端私网 IP 和端口。没有填写这些字段就拒绝启动。
2. **精确监听**：绑定一张指定的私网接口 IP，不使用任意接口通配地址；启动后用 `ss -lntp` 或 `lsof -nP -iTCP:<port> -sTCP:LISTEN` 对 PID、地址和端口做精确核对。
3. **认证**：每个客户端使用独立、可撤销的短期凭据，或使用双向 TLS；拒绝匿名访问。secret 放在权限受限的 runtime secret 中，不写进命令历史、镜像、Git 或评测日志。
4. **TLS**：即使是 LAN 也使用 TLS；证书校验不能关闭。若由反向代理终止 TLS，后端仍只监听 loopback，代理只监听上一步批准的私网 IP。
5. **防火墙**：默认拒绝，仅允许批准的源 IP/CIDR 到**唯一端口**；不要开放整个子网的所有端口。Ubuntu 可能由 nftables/ufw 管理，Arch 可能直接使用 nftables 或选定前端；先识别当前唯一权威防火墙，避免多套规则冲突。
6. **应用限制**：限制请求体、并发、速率和上下文长度；禁用工具执行、文件读取和任意 URL 抓取；记录脱敏审计事件。
7. **双向验证**：从批准客户端验证 TLS 与认证；从未批准客户端确认拒绝；在宿主机复查监听和防火墙计数器。
8. **自动恢复默认**：到期后停止服务、恢复 `allow_lan=false`、撤销凭据和临时规则，再复查只剩 loopback 或无监听。

防火墙检查只需要选择本机实际使用的一种，不要把以下命令全跑一遍：

```bash
# 只读检查；按系统选择一个
nft list ruleset
ufw status numbered
firewall-cmd --list-all
```

> [!danger] 停止条件
> 若无法确定监听地址、TLS 证书来源、认证机制、权威防火墙、允许的客户端或日志是否脱敏，LAN 服务不得启动。不要用路由器端口转发、隧道、UPnP、云反向代理或公网 IP 绕过这道门。

## 13. 恢复、隔离与删除

### 13.1 最快恢复：重新选择原模型

1. 停止加载修改模型的推理进程；
2. 将服务配置指回只读 `models/original/<model-revision>`，不要把修改权重覆盖回原目录；
3. 重新核对原模型 manifest 与文件哈希；
4. 只在 loopback 做最小加载和已知样例验证；
5. 记录回退原因、候选 experiment ID 和受影响时间段。

如果使用 `current` 指针，指针的切换也要记录目标绝对路径和旧值，不能让模糊模型名自动解析到不同 revision。

### 13.2 先隔离，后决定删除

不满意的候选先移动到实验根内的 `quarantine/<experiment-id>`，保留 manifest、哈希、评测摘要和到期日；原模型永远不进入清理目标。下面的恢复性移动默认被门禁阻止，而且要求源、目标均为精确绝对路径：

```bash
QUARANTINE_MOVE="${QUARANTINE_MOVE:-NO}"
SOURCE_CANDIDATE="${SOURCE_CANDIDATE:?Set one exact edited candidate directory}"
QUARANTINE_PARENT="${QUARANTINE_PARENT:?Set the exact quarantine parent}"

if [ "$QUARANTINE_MOVE" != "MOVE_ONE_REVIEWED_CANDIDATE" ]; then
  printf 'Would quarantine: %s -> %s\n' "$SOURCE_CANDIDATE" "$QUARANTINE_PARENT"
  exit 64
fi

# 复核 SOURCE_CANDIDATE 不等于实验根、models/original 或共享缓存后，
# 才把下方注释改成单一、可恢复的移动操作；本页不提供递归删除命令。
# mv -- "$SOURCE_CANDIDATE" "$QUARANTINE_PARENT/"
false
```

最终删除前应确认：服务已停、目录未被 mount、没有进程打开文件、manifest 已保留、保留期已过、目标不是原模型/实验根/共享缓存。优先使用系统垃圾桶或存储快照；不要执行 broad prune、通配清理或递归删除未解析变量。容器也只按本实验的明确 container/image/volume ID 清理，不运行全局 prune。

## 14. 纸上练习：设计一个不会自证成功的实验

选择一个公开、许可清楚的小模型作为**假想对象**，不下载、不运行。写一页实验注册表，包含：

1. 原模型 ID、不可变 revision、tokenizer/template 与许可字段；
2. direction/search/validation/final-test 四个互斥 split；
3. residual direction 的层、token 位置、配对策略和两个负对照；
4. TPE 搜索空间、预算、seed、复合目标和 Pareto 选择规则；
5. KL 的方向、mask、归约和良性参考语料；
6. 拒答、语言质量、通用能力、安全四类独立门槛；
7. 原模型、修改模型、评测产物的三个目录与三份 manifest；
8. 容器只读/可写 mount、`network=none`、非 root 与 GPU 范围；
9. loopback 监听检查，以及 LAN 默认关闭的七项审批证据；
10. 失败时回到原模型和隔离候选的路径。

### 成功标准

- [ ] 我的结论没有把“拒答减少”写成“质量、安全或合规提高”。
- [ ] 我能说明 residual direction 的数据、层、位置、模板和混杂变量。
- [ ] 我能解释左/右投影的空间差异，并指向数学权威页而非复制完整推导。
- [ ] 我把 TPE 用过的数据与最终测试集隔离，并报告全部 trial 或选择偏差。
- [ ] 我记录 KL 方向与归约，且没有用低 KL 代替能力与安全测试。
- [ ] 我至少成对比较拒答、KL、语言质量和通用能力，并另设安全门。
- [ ] 工具 AGPL、模型权重许可和数据许可分别记录。
- [ ] 原模型不可变；修改模型、缓存、原始输出均不进入 Git。
- [ ] 容器是默认路线，编辑阶段无网络；服务默认关闭且仅允许 loopback。
- [ ] LAN 例外同时具备显式开关、精确私网监听、认证、TLS、防火墙和撤销步骤。
- [ ] 我的恢复步骤只切回已核验原模型，清理步骤不包含 broad prune 或不受控递归删除。

## 15. 核验与继续学习

快速变化的版本事实统一回到：

- [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]；
- [Heretic 官方仓库](https://github.com/p-e-w/heretic) 的固定 commit、README、源码与 LICENSE；
- 选定基础模型的官方模型卡与精确 revision；
- 选定数据集/评测集的官方说明、版本与许可证。

每次真正实验应在实践页记录“查到了什么、固定了什么、实际运行了什么、哪些未验证”，不能把本课程的概念说明当成已复现证据。

---

**返回训练路线**：[[AI/20-LLM/30-训练/00-LLM训练-MOC|LLM 训练 MOC]] · **上一站**：[[AI/20-LLM/30-训练/06-LLaMA-Factory数据配置训练与导出|LLaMA-Factory 数据配置、训练与导出]] · **下一站**：[[AI/20-LLM/30-训练/08-分布式训练FSDP-DeepSpeed与Megatron|分布式训练、FSDP、DeepSpeed 与 Megatron]] · **进入实践**：[[AI/80-实践/06-Heretic模型编辑评测与私有部署/00-Heretic模型编辑评测与私有部署|Heretic 模型编辑、评测与私有部署]] · **数学前置**：[[数学/20-线性代数与几何/05-正交投影子空间与方向消除|正交投影与方向消除]]、[[数学/50-信息论/01-熵交叉熵KL散度与互信息|KL 散度]] · **系统前置**：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 与 Linux 部署边界]]
