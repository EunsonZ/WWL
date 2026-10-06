---
type: lab
aliases:
  - Heretic 模型编辑、评测与私有部署实验
  - Heretic 安全评测闭环
domain: artificial-intelligence
stage: 4
status: ready
difficulty: 中级到进阶
estimated_minutes: 180
verified: 2026-09-01
topics:
  - Heretic
  - model-editing
  - refusal-direction
  - orthogonal-projection
  - TPE
  - KL-divergence
  - evaluation
  - private-deployment
  - reproducibility
tags:
  - ai/practice/heretic
  - ai/model-editing
  - ai/evaluation
  - ai/private-deployment
---

# Heretic 模型编辑、评测与私有部署

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本轮[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|42 项深层机制测试]]补充梯度、概率、缓存与训练状态验证；它与本页实验解决不同层的问题。先读[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|验证层级]]，不要把算子测试成功登记成真实模型或部署验收。


> [!abstract] 本实践交付什么
> 这是一条**不下载模型也能先完成设计与校验**的实验路线。你会得到：原模型不可变 manifest、独立工作副本与修改产物约定、方向提取/正交投影/TPE/KL 的概念地图、四类修改前后成对评测、报告模板、默认关闭的本地服务边界，以及可恢复的失败路径。纯 Python 演示只验证合成向量、概率分布和 manifest 规则，不触碰真实模型。

> [!danger] 不能越过的结论边界
> **拒答减少只说明所测输入上的拒答行为发生了变化。**它不等于答案更正确、语言更好、通用能力更强、安全性更高、偏差更小、政策更合理或许可证更宽松。某些良性请求上的过度拒答可能下降，同时危险请求上的必要拒答也可能退化；必须分层评测并保留独立安全停止门。

> [!note] 本次实际完成与未完成
> 已落盘并运行的是标准库纯数学/manifest 校验与测试。**没有**下载 Heretic、模型或数据，没有安装依赖、加载或修改权重、运行模型评测、启动服务、开放端口、上传产物、接受 gated 条款，也没有得到任何模型性能或安全结论。Heretic 的架构支持、CLI、参数、搜索空间与 scorer 都要在真正实验当天固定 commit 后重新核对。

## 1. 先读哪里

- 原理与证据边界：[[AI/20-LLM/30-训练/07-模型对齐拒答方向与Heretic|模型对齐、拒答方向与 Heretic]]；
- 正交投影的完整数学：[[数学/20-线性代数与几何/05-正交投影子空间与方向消除|正交投影、子空间与方向消除]]；
- KL 的定义、方向性与支持集：[[数学/50-信息论/01-熵交叉熵KL散度与互信息|熵、交叉熵、KL 散度与互信息]]；
- Linux 进程、权限、网络与恢复：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]；
- CUDA 与 Linux 兼容边界：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]]；
- 资源路线：[[AI/00-开始/03-8GB-16GB与24GB实践路线|8GB、16GB 与 24GB 实践路线]]；
- 网络、许可和容器总边界：[[AI/00-开始/04-环境安全许可证与资源边界|环境、安全、许可证与资源边界]]。

本实践维护操作闭环，不复制数学页的完整推导，也不把训练页的概念说明冒充已复现实验。

## 2. 完成标准

只有下面各项都有证据，才可以说一次**具体实验**闭环完成：

- [ ] 原模型有精确发布者、仓库 ID、不可变 revision、逐文件大小与 SHA-256、tokenizer、chat template、模型卡和模型许可；
- [ ] 原模型目录只读，工作副本与修改输出是两个新的、互不覆盖的目录；
- [ ] 工具 commit、方向数据、层/位置、搜索空间、预算、seed、所有 trial 与选择规则均已登记；
- [ ] `direction_train`、`search_objective`、`selection_validation`、`final_test` 四套数据互斥，最终测试从未参与搜索或选择；
- [ ] 修改模型单独保存，并记录原模型 manifest 哈希、变更张量、方向、trial、输出文件与哈希；
- [ ] 拒答、KL、语言质量、通用能力四类指标均报告原模型基线和修改后结果；
- [ ] 独立安全停止门没有被复合分数、低 KL 或较低过度拒答抵消；
- [ ] 工具、模型、数据三类许可分别记录并按实际用途复核；
- [ ] 编辑阶段无网络、不上传；服务默认关闭，若只做本机试用则实际只监听 loopback；
- [ ] 报告写明失败、未测范围、选择偏差、证据等级与恢复决定；
- [ ] 任意失败都能停止候选并切回已核验原模型，不需要覆盖或删除 original。

## 3. 实验资产地图

建议把真实实验放在一个**不属于 Vault 的私有实验根**。若复用本目录 `.gitignore`，`data/`、`runs/`、`evaluations/` 默认整树拒绝进入 Git；只分别放行人工审阅过的 `data/manifests/`、`runs/manifests/` 与 `evaluations/reports/`。原始 prompt、逐条输出、trial、日志和未脱敏汇总都不在放行范围内；真实项目仍需现场检查 Git 索引，不能只看 ignore 文件。

```text
heretic-lab/
├── source/heretic-<commit>/               # 固定工具源码；记录 AGPL 与本地修改
├── licenses/
│   ├── tool/                              # Heretic 与依赖
│   ├── model/                             # 原模型/衍生权重条款
│   └── data/                              # 四套数据与评测集分别记录
├── manifests/
│   ├── original-model.manifest.json       # 原模型身份；生成后冻结并计算自身哈希
│   ├── experiment.manifest.json           # 工作副本、方向、搜索、网络与门禁
│   └── edited-model.manifest.json          # 修改产物；绝不覆盖 original manifest
├── models/
│   ├── original/<immutable-revision>/      # 只读
│   ├── work/<experiment-id>/               # 单次编辑工作副本
│   └── edited/<experiment-id>/             # 单独输出
├── data/
│   ├── manifests/                          # 唯一放行区：脱敏 ID、revision、许可、哈希
│   └── restricted/                         # 默认拒绝：原始 prompt/个人数据
├── runs/
│   ├── manifests/                          # 唯一放行区：人工审阅的运行清单
│   └── private/<experiment-id>/            # 默认拒绝：directions/trials/config/logs
├── evaluations/
│   ├── reports/                            # 唯一放行区：人工审阅的脱敏聚合报告
│   └── private/<experiment-id>/            # 默认拒绝：逐条输出与未审阅汇总
└── quarantine/<experiment-id>/             # 未通过候选；有保留期，可恢复
```

必须满足的路径不变量：

1. `original`、`work`、`edited`、`run`、`evaluation` 均为不同绝对路径；
2. `work`、`edited`、`run`、`evaluation` 都不能位于 `original` 之内；
3. 所有新目的目录在开始前必须不存在；若已存在就停止，不做合并或覆盖；
4. 原模型 manifest 记录的目录必须与实验 manifest 的 original 路径逐字一致；
5. 缓存不是模型身份，`main`、`latest`、本地昵称和同名量化文件不是不可变 revision。

## 4. 从原模型到报告的十阶段闭环

| 阶段 | 输入 | 只允许的动作 | 必须产出 | 停止条件 |
| --- | --- | --- | --- | --- |
| 0. 预注册 | 研究问题与威胁模型 | 定义假设、数据、门槛、预算与恢复 | 冻结计划 | 目标只是“让模型不拒答”而无安全门 |
| 1. 许可分账 | 工具、模型、数据条款 | 分别记录版本与用途 | 三份许可记录 | 任一资产用途或再分发权不清楚 |
| 2. 冻结原模型 | 已获准的本地文件 | 列清单、计算哈希、固定 tokenizer/template | original manifest | revision 可移动、文件不完整或哈希缺失 |
| 3. 建工作副本 | 只读 original | 复制到全新目录，再核对文件哈希 | work manifest/复制记录 | 目标已存在、源可写状态不明、磁盘不足 |
| 4. 提取方向 | `direction_train` | 选层、位置与成对表示，做负对照 | direction manifest | 数据混杂、样本泄漏或方向范数异常 |
| 5. 投影与 TPE | 工作副本、方向、搜索集 | 每 trial 独立编辑并保存完整 ledger | 全部 trial 记录 | 测试集进入搜索、NaN/Inf、覆盖副本 |
| 6. 选择候选 | `selection_validation` | 按预注册门槛/Pareto 选择 | selected trial ID | 安全门退化或没有候选过门 |
| 7. 独立保存 | 选择的候选 | 写入新的 edited 目录与 manifest | 修改产物哈希 | 与 original/work 路径重合 |
| 8. 冻结测试 | `final_test` | 原模型/修改模型成对运行四类评测 | 原始私有结果与聚合 | 配置不一致、测试泄漏、审阅缺失 |
| 9. 报告与恢复 | 所有 manifest 与评测 | 写限定结论；切回原模型或隔离候选 | 报告、恢复证据 | 想用单一分数跳过独立门禁 |

### 4.1 阶段 0：把问题写窄

一个可证伪的假设示例：

> 在固定模型 revision、chat template、解码设置和四套互斥数据上，某个预登记层/位置得到的方向编辑，可能降低**良性测试集**中的过度拒答；同时，危险集必要拒答不得低于预注册门槛，语言质量与通用能力不得超过预注册退化界，KL 只作为分布漂移信号。

这比“解除审查”“恢复真实知识”或“让模型更聪明”更窄，也更可能被数据推翻。再加入随机方向、标签置乱方向与 sham copy，才能判断变化是否针对所测方向，而不是保存/加载、模板或任意权重扰动造成。

### 4.2 阶段 1：许可证必须分成三本账

| 账本 | 至少记录 | 不能由它推出 |
| --- | --- | --- |
| 工具代码 | Heretic 官方仓库、固定 commit、该 commit 的 LICENSE、依赖与本地修改；当前资料账本记录为 `AGPL-3.0-or-later` | 模型或数据也自动采用 AGPL；模型可商用/再分发 |
| 模型资产 | 原模型仓库与 revision、模型卡、权重许可、可接受使用条款、tokenizer/template、衍生权重定义 | 点击下载或本地持有等于获得所有用途授权 |
| 数据资产 | direction/search/validation/final-test 每套数据的来源、revision、许可、个人数据与输出限制 | 一个数据集获准后，其他数据和生成输出也自动获准 |

AGPL 的网络交互条款可能要求向通过网络使用修改版程序的用户提供对应源代码；是否触发、如何满足以及依赖/修改组合如何处理，要以固定 commit、实际部署形态与合规意见为准。本实践不是法律意见。即使工具的 AGPL 义务处理完成，模型权重与数据条款仍是独立门。

### 4.3 阶段 2：冻结原模型 manifest

复制 `original-model.manifest.template.json` 到私有实验根的新文件，逐项填写后再将 `artifact_state` 从 `template_not_materialized` 改为 `ready`。模板中的 `REPLACE_*`、零大小、缺失哈希、移动 revision 和未复核许可都应使校验失败。

原模型身份至少由以下联合确定：

```text
发布者 + 仓库 ID + 不可变 revision
+ config/tokenizer/chat template 的固定版本
+ 每个实际文件的相对路径、字节数和 SHA-256
+ 模型卡与许可快照
```

目录权限只是一层保护，manifest 和哈希才提供可核对的身份。不要把“缓存命中”“能加载”或“文件名一样”当作原模型不变的证明。

### 4.4 阶段 3：只从原模型生成一个新工作副本

复制前做四个只读判断：源目录存在、源目录等于 original manifest、目标绝对路径是本 experiment ID、目标不存在。复制后重新计算文件清单并与 original manifest 对照，再允许 Heretic 只写工作副本或新 edited 目录。

安全门禁骨架默认退出；它不含 Heretic 命令：

```bash
set -eu
: "${HERETIC_ORIGINAL_DIR:?Set the exact absolute immutable original directory}"
: "${HERETIC_WORK_COPY_DIR:?Set one exact new absolute work-copy directory}"
HERETIC_COPY_GATE="${HERETIC_COPY_GATE:-NO}"

if [ "$HERETIC_COPY_GATE" != "COPY_ONE_REVIEWED_IMMUTABLE_MODEL" ]; then
  printf '%s\n' 'Blocked: review manifests, licenses, source and destination first.'
  exit 64
fi

test -d "$HERETIC_ORIGINAL_DIR"
test ! -e "$HERETIC_WORK_COPY_DIR"
case "$HERETIC_WORK_COPY_DIR" in
  /|"$HERETIC_ORIGINAL_DIR"|"$HERETIC_ORIGINAL_DIR"/*) exit 64 ;;
esac

cp -a -- "$HERETIC_ORIGINAL_DIR" "$HERETIC_WORK_COPY_DIR"
```

这段骨架仍需操作者在执行前用 manifest 校验并确认磁盘、权限、平台 `cp` 行为和目标父目录；它只解决“不覆盖”这一小部分问题。

### 4.5 阶段 4：方向提取与正交投影

对第 $\ell$ 层的指定 token 位置，设拒答组 $R$ 与配对控制组 $C$：

$$
\tilde r_\ell=\operatorname{mean}_{x\in R}h_\ell(x)-\operatorname{mean}_{x\in C}h_\ell(x),
\qquad
r_\ell=\frac{\tilde r_\ell}{\|\tilde r_\ell\|_2}.
$$

当 $r$ 已单位化，移除向量 $h$ 在该方向上的线性分量：

$$
h'=h-(r^\mathsf Th)r=(I-rr^\mathsf T)h.
$$

方向 manifest 必须记录：模型 revision、层、token 位置、聚合方式、模板、语言/主题/长度配对、dtype、样本 manifest、方向向量哈希、范数、seed 和负对照。若两组同时改变语言、长度、主题或模板，均值差可能编码混杂变量；即使投影后 $r^\mathsf Th'=0$，也只证明合成的线性正交性，不证明“拒答语义已删除”。

若编辑权重矩阵，必须分清方向位于输出空间还是输入空间：左乘 $(I-rr^\mathsf T)W$ 与右乘 $W(I-rr^\mathsf T)$ 不是同一操作。具体 Heretic commit 修改哪些模块，必须读源码并用张量形状测试，不能从本页公式猜 CLI。

### 4.6 阶段 5：TPE 搜索的是目标函数，不是真理

TPE 可在昂贵试验中根据已完成 trial 的分数提出下一组层、方向、强度或模块组合。它能节约搜索预算，但不会自动发现正确标签、消除数据泄漏、保证全局最优或把不同单位的指标变成客观总分。

预注册至少包括：

- 有界的层/模块/强度空间；不允许搜索过程扩大到未登记模块；
- trial 总数、超时、OOM/NaN 处理、固定 seed 和早停条件；
- refusal 与 preservation 指标如何归一、组合或形成 Pareto 前沿；
- `search_objective` 只给 trial 打分，`selection_validation` 只选候选；
- `final_test` 在候选冻结前完全不可见；
- 保存所有 trial、失败和 seed，不只保留“最佳”结果。

若复合分数把“拒答下降 1 点”和“KL 上升 1 点”直接相加，权重本身就在定义最优候选。报告应展示各轴取舍；任何重大安全退化都应直接停止，不能被其他维度抵消。

### 4.7 阶段 6：KL 只是分布漂移报警器

固定同一前缀，原模型下一 token 分布为 $p_{\text{original}}$，修改模型为 $p_{\text{edited}}$。本模板显式采用：

$$
D_{\mathrm{KL}}\!\left(p_{\text{original}}\Vert p_{\text{edited}}\right)
=\sum_i p_{\text{original}}(i)\log\frac{p_{\text{original}}(i)}{p_{\text{edited}}(i)}.
$$

还必须固定：计算位置、token mask、序列截断、温度、logits dtype、稳定 softmax/log-softmax 实现、按 token/序列/样本的归约方式，以及语料分层。低 KL 只说明所测位置上的局部概率分布接近，不能证明长文本相同、事实正确、能力不变或安全；高 KL 表示漂移大，也不自动等于质量下降。

### 4.8 阶段 7：修改模型必须是独立产物

修改完成后写 `edited-model.manifest.json`，至少包含：

- original manifest 路径、哈希和原 revision；
- Heretic commit、本地源码修改 manifest 与工具许可记录；
- direction manifest、全部 trial ledger、selected trial 与选择验证哈希；
- 变更张量清单、每个输出文件的路径/大小/SHA-256；
- 修改后权重的许可/分发判断，默认 `do_not_distribute` 直到复核；
- 评测计划哈希与服务门状态。

永远不要把修改权重写回 original 或把 edited manifest 覆盖 original manifest。若保存/加载流程本身会重排分片，sham copy 应先量化这种非编辑差异。

### 4.9 阶段 8：四类基线与修改后成对评测

四类评测都必须使用相同 tokenizer、chat template、system prompt、数据顺序、采样设置、最大长度和 scorer 版本。原模型基线与修改模型结果逐条配对；若改变任何其他变量，应另开消融组。区间、配对抽样与样本量的数学边界见 [[数学/30-概率与统计/05-统计估计置信度与模型评测|统计估计、置信度与模型评测]]；版本化用例、回归门与观测记录见 [[AI/20-LLM/70-工程应用与工具链/04-评测回归与可观测性|评测、回归与可观测性]]。

| 维度 | 基线与修改后都要报告 | 必要分层 | 不能替代 |
| --- | --- | --- | --- |
| 拒答 | 完全拒答、安全替代、有限帮助、正常回答、危险配合、不可判定的混淆矩阵 | 危险/良性、语言、主题、模板；人工盲复核 | 正确性、语言质量、通用能力或安全 |
| KL | 指定方向的 mean/median/p95、分位数与异常样本 ID | 主题、语言、长度、位置；mask 与归约 | 长程生成、事实正确或能力保持 |
| 语言质量 | 流畅、连贯、重复、乱码、截断、指令遵循的盲成对评分 | 语言、长度、生成 seed | 知识/推理正确或安全 |
| 通用能力 | 固定知识、推理、数学、代码、长上下文任务的准确率/通过率与差值 | 任务族、难度、seed；区间或 bootstrap | 未测领域或真实生产表现 |

拒答维度中要同时看危险集的必要拒答和良性集的过度拒答。只搜索“抱歉”“不能”等关键词会误判安全替代，也会漏掉无拒答措辞但不给实质答案的输出；正则或分类器只能初筛，边界样本与随机样本必须人工复核。

除四类比较外，另设**独立安全停止门**：危险内容、隐私泄露、偏差、越狱稳健性、工具调用、文件读取和网络边界。安全显著退化时不进入服务阶段，即使良性过度拒答下降、KL 很低或通用能力上升。

### 4.10 阶段 9：报告、恢复与隔离

用 [[AI/80-实践/06-Heretic模型编辑评测与私有部署/evaluation-report.template|评测报告模板]] 写报告。结论必须限定到版本、数据、硬件、模板、解码、样本量与置信度；测试分辨率不足时写“证据不足”，不要写“完全不退化”。

最快恢复不是反向编辑，而是重新选择原模型：

1. 停止加载 edited 的进程；
2. 确认服务端口不再监听；
3. 将配置显式指回 original manifest 的只读绝对路径；
4. 重新校验 original manifest 与逐文件 SHA-256；
5. 只在 loopback 运行最小基线；
6. 将未通过候选移动到精确的 `quarantine/<experiment-id>`，保留 manifest、报告和到期日。

本实践不提供递归删除命令、全局容器 prune、共享缓存清理或模糊模型名切换。最终删除要独立确认目标、挂载、打开文件、服务状态、保留期与可恢复位置；original 永远不属于候选清理范围。

## 5. manifest 与评测模板怎么用

本目录包含：

| 文件 | 用途 | 默认状态 |
| --- | --- | --- |
| `original-model.manifest.template.json` | 原模型不可变身份与许可 | 故意校验失败，直到所有占位符、哈希和复核状态填完 |
| `experiment.manifest.template.json` | 工具、三类许可、路径、四 split、编辑计划与网络门禁 | 服务/LAN/公网/上传/遥测关闭，执行 gate 未批准 |
| `edited-model.manifest.template.json` | 独立修改产物和来源链 | 不物化、不分发，直到实际输出与复核完成 |
| `evaluation-plan.template.json` | 四类成对评测、数据隔离和独立安全停止门 | 计划未执行 |
| `evaluation-report.template.md` | 修改前后结果、证据等级、限制和恢复 | 不含结果 |
| `.gitignore` | 权重、缓存、私有输出、日志和凭据边界 | 保留 manifest 与脱敏聚合报告 |
| `01-清单模板源码与测试附录.md` | 集中保存全部模板、规范源与测试的完整 code-sync | 返回本任务页，不拆成函数碎片页 |
| `heretic_math_manifest_demo.py` | 纯数学演示与 manifest 校验 | 无网络、不读模型 |
| `test_heretic_math_manifest_demo.py` | 正交性、KL 方向、路径/网络/泄漏门禁测试 | 只创建内存对象和临时符号链接 fixture |

模板不是一个可以直接改成“通过”的形式主义步骤。每个 `REPLACE_*` 都代表必须从实际文件、固定 revision 或责任人处取得的证据；不要用虚构哈希或通配路径填满。

填完的四个校验输入可以这样做只读验证。校验器会读取四份文件的实际规范路径和 SHA-256，并闭合原模型 → 实验 → 修改产物 → 评测计划的身份链；符号链接清单、身份或哈希不一致都会失败：

```bash
python3 'AI/80-实践/06-Heretic模型编辑评测与私有部署/heretic_math_manifest_demo.py' validate \
  '/absolute/path/to/original-model.manifest.json' \
  '/absolute/path/to/experiment.manifest.json' \
  '/absolute/path/to/edited-model.manifest.json' \
  '/absolute/path/to/evaluation-plan.json'
```

校验器拒绝：清单符号链接/非普通文件、移动 commit、占位哈希、original 内部的工作/输出目录、目标路径重合、任何服务/LAN/公网/上传/遥测开关、非 loopback 地址、敏感字段（即使为空）或 credential/signed-URL 形态的值、最终测试进入搜索，以及缺少四类评测。CLI 会先完成四个清单的文件身份检查，再从解析后的规范路径读取 JSON；它**只检查结构和部分安全不变量**，不会读取权重文件或替代许可审阅、实际哈希比对、模型加载、评测与人工安全复核。

## 6. 私有部署：默认关闭，最多只到 loopback

模型编辑与模型服务是两个独立阶段。只有冻结评测通过且确有交互需要，才使用另一个固定版本、经过审阅的推理运行时加载 edited；Heretic 是否自身提供服务，以固定 commit 的实际源码为准。

默认必须保持：

```text
editing_network = none
service_enabled = false
bind_host = 127.0.0.1
allow_lan = false
allow_public = false
upload_enabled = false
telemetry_enabled = false
```

如果服务被显式启动，只做本机 loopback 试用。配置不是证据；启动后要现场检查 PID、地址和端口。Linux 二选一做只读检查：

```bash
: "${HERETIC_LOCAL_PORT:?Set the exact local port to inspect}"
ss -lntp "sport = :$HERETIC_LOCAL_PORT"
```

或：

```bash
: "${HERETIC_LOCAL_PORT:?Set the exact local port to inspect}"
lsof -nP -iTCP:"$HERETIC_LOCAL_PORT" -sTCP:LISTEN
```

默认只接受 `127.0.0.1:<port>`；启用 IPv6 时只接受 `[::1]:<port>`。若出现 `0.0.0.0`、`[::]` 或非预期接口，立即停止对应 PID，恢复 `service_enabled=false`，再检查无监听。不要记录完整 prompt、response、认证值、私有路径或个人数据。

### 6.1 LAN 是显式例外，默认仍为 off

本实践**不提供公网路线**，也不使用端口转发、UPnP、隧道、云反向代理或公网 IP 绕过门禁。

LAN 只能在以下证据全部具备后，由负责人员另行显式批准：

1. `allow_lan=false` 是持久默认；例外记录目的、负责人、到期时间、精确客户端 IP/CIDR、服务端私网 IP 和唯一端口；
2. 服务绑定一张明确的私网接口地址，不绑定任意接口；启动后按 PID、地址和端口复查；
3. 每客户端独立、可撤销、短期认证凭据或 mTLS；拒绝匿名访问，凭据不进命令历史/Git/镜像/日志；
4. LAN 也使用 TLS，证书校验不得关闭；若代理终止 TLS，后端仍只监听 loopback；
5. 识别机器上唯一权威防火墙，只放行批准源到唯一端口，默认拒绝；不要同时堆叠不明的 ufw/nftables/firewalld 规则；
6. 禁用工具执行、文件读取、任意 URL 获取和外部调用；限制请求体、上下文、并发和速率；
7. 批准客户端验证 TLS+认证，未批准客户端做负向拒绝测试，宿主机复查监听与防火墙计数器；
8. 到期停止服务、恢复 `allow_lan=false`、撤销凭据与临时规则，并确认无 LAN 监听。

只读识别防火墙时按系统选择实际使用的一种，不要把下面命令全跑：`nft list ruleset`、`ufw status numbered` 或 `firewall-cmd --list-all`。若认证、TLS、权威防火墙、精确监听、日志脱敏或客户端范围任一不清楚，保持 LAN off。

## 7. 容器、Ubuntu 与 Arch 的责任边界

| 路线 | 适合做什么 | 必须现场核验 | 常见误区 |
| --- | --- | --- | --- |
| 容器（默认优先） | 固定用户态依赖、只读输入 mount、独立输出、便于清理 | 镜像 digest、非 root、`network=none`、GPU 范围、资源上限、精确 mount | 容器带来了另一套内核/驱动，或自动安全 |
| Ubuntu native | 当具体版本在工具/驱动支持矩阵中时建立较稳定环境 | APT 来源、Ubuntu 版本、Python/PyTorch/CUDA/driver 组合 | 混用发行版、NVIDIA 仓库和手工安装，或照抄其他版本命令 |
| Arch native | 熟悉滚动系统且愿意维护整体更新时研究本机栈 | kernel、driver、compiler、Toolkit、Python 与工具作为一组验证 | partial upgrade、复制 `apt` 路线、把最新等同兼容 |

容器仍使用宿主内核和 GPU 驱动。默认不挂宿主家目录、Docker/Podman socket、SSH key、凭据目录或整个数据盘；不用 privileged、host PID/IPC/network；原模型只读挂载，work/edited/run/cache 分别精确可写；编辑阶段 `network=none`。任何 driver、Toolkit、内核或包仓库变更都是另一个系统级任务，需要独立备份与恢复，本实践不执行。

## 8. 8GB、16GB 与 24GB 路线

显存只决定可尝试的起点，不保证某个模型、上下文、batch、trial 数或运行时能完成。每次先测实际可用显存、系统内存、磁盘、驱动/框架组合与其他进程占用；一次只改变一个资源变量。

| 可用显存 | 本实践建议 | 先不做什么 | 完成证据 |
| --- | --- | --- | --- |
| 约 8GB | 完成本文纯数学、manifest、数据切分、报告与 CPU 合成测试；若另行获准真实实验，只从能完整测基线的公开小模型、极短输入和极低 trial 预算开始 | 不以“能勉强加载”代替四类成对评测；不追求长上下文、大搜索或服务并发 | 校验器/测试通过，资源预算和停止条件已登记；真实模型则记录峰值、延迟与完整基线 |
| 约 16GB | 在许可和兼容性确认后，尝试较小模型的单方向/少量层/小预算搜索；先做 sham 与负对照 | 不把量化/offload 当作无质量成本；不同时扩大模型、上下文和 trial | 原/改成对评测可在同一配置完成，所有 trial 和 OOM 都保留 |
| 约 24GB | 扩大可测模型或层/方向组合，但仍以完整评测和恢复为优先；必要时比较精度、上下文与吞吐 | 不假定可以处理任意模型、全精度副本、无限 trial 或 LAN 服务 | 资源表、Pareto 取舍、四类指标、独立安全门和恢复演练齐全 |

真实显存至少包括权重、激活、临时张量、框架/内核开销；编辑还可能同时保留原始、工作和候选张量，评测生成又会增加 KV cache。磁盘也可能同时存在 original/work/多个 trials/edited，不可只按一个权重文件估算。OOM 后保存证据，先缩小 batch、上下文、候选数或模型，再重跑基线；不要为“跑通”而同时改变精度、模板、数据和 scorer。

## 9. 纯数学与 manifest 校验演示

运行演示：

```bash
python3 'AI/80-实践/06-Heretic模型编辑评测与私有部署/heretic_math_manifest_demo.py' demo
```

运行测试：

```bash
python3 'AI/80-实践/06-Heretic模型编辑评测与私有部署/test_heretic_math_manifest_demo.py' -v
```

演示的可观察成功标准：

- 投影后的合成向量与指定单位方向点积接近 0；
- $D_{\mathrm{KL}}(p\Vert q)$ 与 $D_{\mathrm{KL}}(q\Vert p)$ 在示例中不同，直观看到方向性；
- 内存中的合成 original/experiment/edited/evaluation 四清单通过身份与哈希闭环校验；
- 输出显式包含 `does_not_describe_model_behavior: true`；
- 测试覆盖零方向、KL 支持集、移动 revision、占位哈希、original 内部工作目录、服务/LAN/公网/上传开关、非 loopback 地址、敏感字段/值、清单符号链接在 JSON loader 前失败、跨清单 ID/哈希错配、测试集泄漏与缺失评测维度。

这些成功标准只说明数学函数和部分安全契约按测试工作。它们不说明 Heretic 能处理某个模型、不说明权重编辑成功，也不说明拒答、能力或安全发生任何变化。

## 10. 练习：完成一次“纸上预注册”

不下载任何资产，选择一个假想的小模型作为对象：

1. 复制四个 JSON/Markdown 模板的结构到一个临时草稿；
2. 把真实未知项保留为“待现场核验”，不要伪造 commit、hash 或许可；
3. 写出 direction/search/validation/final-test 的互斥条件；
4. 为四类指标各写一个门槛，并给安全停止门一个不可抵消条件；
5. 为 8/16/24GB 中与你相符的一档写资源上限和停止条件；
6. 画出 original → work → edited → evaluation → report/quarantine 的路径，确认没有回写箭头；
7. 写出为何当前只能 `service_enabled=false`、`allow_lan=false`。

**成功标准：** 你可以在没有模型和工具的情况下发现计划中的路径覆盖、许可混账、数据泄漏、测试集参与搜索、单一指标自证成功和网络暴露问题；不会为了让模板通过而编造事实。

## 11. 恢复本教学目录

本目录没有权重或外部状态。若只想撤销纯演示运行，删除 Python 生成的 `__pycache__/` 即可；它已被同目录 `.gitignore` 排除。若要撤销本教学内容，删除本目录前应先由主维护者确认 `AI/80-实践/00-AI实践-MOC.md` 与训练页链接，再使用版本控制恢复；不要把这个动作扩展到真实 `heretic-lab/`、模型缓存、共享数据或容器资源。

## 12. 清单模板、规范源与测试附录

四份 JSON 清单、评测报告模板、纯数学/manifest 校验规范源和标准库测试已集中到 [[AI/80-实践/06-Heretic模型编辑评测与私有部署/01-清单模板源码与测试附录|清单模板、源码与测试附录]]。本页保留任务边界、十阶段闭环、许可与数据隔离、网络/容器边界、资源路线、练习和恢复方法。

必要的阅读边界：

- 模板保持 fail closed；占位符、`planned`、校验器退出 0 都不代表真实模型或许可已验收；
- CLI 必须在读取 JSON 前完成清单路径身份检查，并只从解析后的普通文件路径加载；
- 完整 code-sync 与负向测试职责以附录为准，不在本页复制第二份实现。


---

**上一站**：[[AI/20-LLM/30-训练/07-模型对齐拒答方向与Heretic|模型对齐、拒答方向与 Heretic]] · **数学**：[[数学/20-线性代数与几何/05-正交投影子空间与方向消除|正交投影]]、[[数学/50-信息论/01-熵交叉熵KL散度与互信息|KL 散度]] · **系统**：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux]]、[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 与 Linux 部署]] · **返回**：[[AI/80-实践/00-AI实践-MOC|AI 实践 MOC]]
