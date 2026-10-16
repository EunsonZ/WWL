---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - 有类型关系消息与尾实体补全小实验
prerequisites:
  - "[[AI/16-图表示学习/08-异质关系消息方向与知识图补全]]"
sources:
  - https://arxiv.org/html/1703.06103v4
  - https://arxiv.org/pdf/1412.6575
  - https://snap.stanford.edu/class/cs224w-2024/slides/09-hetero.pdf
  - https://papers.nips.cc/paper_files/paper/2013/file/1cecc7a77928ca8133fa24680a88d2f9-Paper.pdf
---

# 有类型关系消息与尾实体补全

本实践先用同一个 `encode()` 检查关系、方向与多重边，再在固定关系编码器的表示上真实训练三种decoder，完成一个有限尾补全任务。完整对象、等变证明、梯度、能力反例与撤提示题解见 [[AI/16-图表示学习/08-异质关系消息方向与知识图补全|08课]]。正式训练**不更新编码器**，不是R-GCN原论文端到端训练或真实知识图效果复现。旧采样/GAT/图级数据与训练不重跑，仅只读复用父 `graph_task.py` 的load/dump/digest/sigmoid；其无向数组loader不适用于本包，因此不调用。

## 锁定的任务与信息阶段

[protocol.json](protocol.json) 在短预跑前锁定，未按test成绩改模型、seed、轮数或选择规则。[inputs.json](inputs.json) 有public、train、val、test四部分。public含16实体的类型/特征、消息边、schema、合法候选；另外三部分只含各自query heads及目标正事实。

- 实体P0…P7为Person，S0…S7为Site。Person特征都是(0,0,1)，Site特征为(cosθ,sinθ,0)，θ=2πi/8；坐标是构造世界允许观察的原始测量。
- 8条已知 `at(Person,Site)` 与只从这些support事实派生的8条 `at_inv(Site,Person)` 构成唯一消息图。它在train/val/test都不变；任何 `next` 及 `next_inv` 都不出现，连train目标也不消息化。没有先把全图补成逆边再拆分。
- 目标 `next(Person,Person)`：尾编号相对头编号增加1或2（模8）为正，其余为负。协议字段 `positive_clockwise_offsets` 在本包明确表示**编号增量**；通常y向上坐标中θ递增视觉为逆时针，字段英文名不另定义几何方向。完整56个合法有向对共有16正、40负；排除self，不做Site尾候选。
- train heads=[0,2,4,6]，val=[1,5]，test=[3,7]；每头7尾，2正5负。因此train28候选对/8正例，val与test各14对/4正例。目标行按head分组，但所有实体从开始已知；这是同一KG上的转导补全，不是未见节点或整图留出，也不是外部盲测。

训练行从 `query_rows(public,train)` 穷举，不做随机负采样，也不查val/test正例来排除训练负例。这里额外保证每个训练query行的真值完备，所以“非这2个正尾=负”在该有限任务成立。现实开放世界的缺边可能只是未知，必须另声明负采样分布、已知正例过滤与假负例假设，不能照搬这个封闭世界保证。

| 阶段 | 模型可见特征/消息 | 更新或选择读什么 | filtered可读的正例 |
| --- | --- | --- | --- |
| train | 固定public与support | train完整行更新 | train |
| val | 同一public与support | val完整行CE仅选择epoch | train+val，禁止test |
| test | 同一public与support | 所有选项冻结后仅评价 | train+val+test，只供评价过滤 |

`train_all(core,public,train,val,...)` 不接test；9个checkpoint与selection写完后，`run`才首次索引test部分。val选的是逐候选BCE，不由filtered MRR选择。保存输入含答案只是供重放，不授权训练端读整份答案；函数边界与独立guard检查代码实际路径，不能保证任意外部操作者从未偷看公开输入。

最终filtered允许使用test已知正例表，是为了不把其他真实尾算成错误；它只删候选，不改变参数、消息或logit。验证filter仍没有test真值。这个任务同一query head的另一正尾就在相同阶段，实际每项filtered都会删去另一真尾；并不是只把过滤规则写在文案却从未执行。

## 编码器、decoder与预算

矩阵接收者为行、发送者为列。关系入边按重数归一，零入度该关系输出0；root分支另算一次。固定3维编码器使用恒等激活：W0=diag(0,0,1)，W_at=0，W_at_inv=diag(1,1,0)。于是Person从Site取坐标并从root保留1，得到H_Pi=(cosθ_i,sinθ_i,1)。编码器共有三块3×3**存储常量**，本轮可训练参数数为0；通用反传接口可核，不表示它已共同训练。

| formal model | 允许计算 | 可训练参数与边界 |
| --- | --- | --- |
| bilinear | 相同固定H，s=H_head R H_tailᵀ | 完整3×3矩阵，9参数；可不对称 |
| distmult | 相同固定H，s=sum a_k H_head,k H_tail,k | 3参数；同relation、共享实体向量强制交换对称 |
| no_graph | 不消费边，只取相同Person root=(0,0,1)，再用完整双线性头 | 存9参数，只有R33影响分数，其余8项只受L2；所有合法尾得分相同 |

此无图对照是明确的“每实体原始root特征+同形状头”类，不声称排除所有可能的无图规则。它没有从实体文件顺序或ID取圆坐标；Site特征虽公开，但Person到Site的关联只有at边携带。用ID查表或手工把Person与同编号Site绑定会改变可见接口。

三种decoder按同一固定seed17/29/43初始化，标准差.05；600轮全批Adam，学习率.03，β1=.9/β2=.999/ε=1e-8；CE平均所有本split候选对，λ/2||decoder||²且λ=.01。含常数坐标的R33也正则。各模型独立取600轮中val CE最低者，同值保留最早轮；无test调参、架构搜索或后验选seed。3参数与9参数不是相同预算；这里检验结构限制及受控学习，不给普遍架构排名或效率排名。

08课给完整R的圆坐标构造，能分开全部56合法有向对；对角头却对合法反向pair强制相同分数。同型next的一正一负反向对才是有效表达反例，不能拿Person→Site的非法反方向证明at必败。固定编码器对方向/关系的保留与decoder最后能否使用，是两层不同的合同。

## 实际结果及有限失败

正式运行0.305562秒，Python3.14.7/NumPy2.5.2/macOS27.0.1 arm64，CPU一线程，无GPU/下载或新增依赖。短预跑只用seed17/20轮0.033012秒，查看资源路径后默认协议未改。本机时间不认证跨机或大图上限。

每个test有2个query heads、4个正三元组评价query、每头7候选尾。raw在候选中保留另一正尾；filtered删另一已知正尾。MRR按正三元组平均，不把候选数、实体数或节点数当独立图样本。

| seed | decoder | selected epoch | test CE | raw MRR | filtered MRR | filtered Hits@1 | filtered Hits@3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | bilinear | 416 | 0.152476 | 0.750000 | 1.000000 | 1.000000 | 1.000000 |
| 17 | distmult | 118 | 0.475983 | 0.375000 | 0.416667 | 0.000000 | 1.000000 |
| 17 | no_graph | 62 | 0.598270 | 0.250000 | 0.285714 | 0.000000 | 0.000000 |
| 29 | bilinear | 449 | 0.152476 | 0.750000 | 1.000000 | 1.000000 | 1.000000 |
| 29 | distmult | 152 | 0.476064 | 0.375000 | 0.416667 | 0.000000 | 1.000000 |
| 29 | no_graph | 53 | 0.598270 | 0.250000 | 0.285714 | 0.000000 | 0.000000 |
| 43 | bilinear | 429 | 0.152476 | 0.750000 | 1.000000 | 1.000000 | 1.000000 |
| 43 | distmult | 125 | 0.475904 | 0.666667 | 0.750000 | 0.500000 | 1.000000 |
| 43 | no_graph | 52 | 0.598270 | 0.250000 | 0.285714 | 0.000000 | 0.000000 |


完整双线性头的raw MRR=.75并不表示有1/4事实“错了”：两个真尾有先后，原始排名是1和2，倒数均值.75；删去另一正尾后二者均rank1。DistMult的三个seed结果均保留，43较好仍不推翻其全域交换恒等式；有限测试query表现与全域分类表达能力不是同一个命题。没有把所有低分唯一归因于优化失败，也不把较少参数带来的作用隐藏。

无图所有尾并列，raw rank4，filtered rank3.5，故MRR=.25和2/7。本包容差1e-10，先计算平均名次再取倒数；这不等于随机打破并列后的期望MRR，Hits的定义也与本rank合同一致。不存在按实体ID给同分项额外优势。

![[AI/80-实践/11-图传播训练与评测/relations/figures/decoder-scores.svg]]

![[AI/80-实践/11-图传播训练与评测/relations/figures/relation-messages.svg]]

## 本机复现与原始输出

规范 [relations.py](relations.py)、[test_relations.py](test_relations.py)、[render_relations.py](render_relations.py)；完整 [[AI/80-实践/11-图传播训练与评测/relations/源码镜像|源码镜像]] 供阅读。仅需Python与NumPy；默认父目录需有已发表graph_task.py。新输出路径必须尚不存在，避免覆盖已发表结果。从本relations目录执行：

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 -B relations.py generate --output /private/tmp/wwl-relations-new-inputs.json
python3 -B relations.py train --inputs /private/tmp/wwl-relations-new-inputs.json --output /private/tmp/wwl-relations-new-results
python3 -B -m unittest -v test_relations
python3 -B render_relations.py --output /private/tmp/wwl-relations-new-figures
```

末条默认重画当前目录已保存结果；新一轮作图须把同轮protocol.json、inputs.json、results/放入独立目录，再传 `--root /同轮目录 --output /新图目录`。不混旧真值与新分数。render使用同版规范encoder/decoder生成夹具与图，没有额外训练。

候选区未复制父源码，维护时传 `--parent /主库/AI/80-实践/11-图传播训练与评测`，测试设置 `WWL_GRAPH_PARENT` 为同一路径。正式数值/预跑/测试通过团队两槽运行器 `python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 -B ...`，一线程、≤5分钟，不占GPU。

- [results/identity.json](results/identity.json) 绑定规范源码、输入、协议和只读父core；[environment.json](results/environment.json) 给实际环境与耗时。
- [checkpoints.json](results/checkpoints.json) 保存9个最终参数和每个模型600轮train/val轨迹；[selection.json](results/selection.json) 给选择与val CE。
- [raw_scores.json](results/raw_scores.json) 保存504条候选对的seed/model/split/head/relation/tail/y/logit/CE，允许完整独立重放。
- [query_ranks.json](results/query_ranks.json) 保存144条正三元组的raw/filtered rank、实际删掉的尾、过滤真值所属阶段；[summary.json](results/summary.json) 有27项split均值。没有只保留总分。
- [message_barrier.json](results/message_barrier.json) 给16个目标事实及其逆边是否存在于消息图的逐项false记录；该事后审计不承担训练构图职责。
- [figures/message-fixtures.json](figures/message-fixtures.json) 留关系交换/重数的同模型输入与输出；[score-matrices.json](figures/score-matrices.json) 留seed17三图矩阵与共同色标；[results-table.md](figures/results-table.md) 从summary派生全部9行test数字。

## 断言重要性与失败判据

| 断言 | 重要性及原因 | 固定输入/命令与独立预期、失败判据 |
| --- | --- | --- |
| 类型/方向/重数与root/孤点 | 高：输入对象错会改变算法与答案 | generate与message夹具；独立标量按边计接收者均值，2×1+3的均值应5/3，关系交换应−2/+2，反向schema非法应拒绝，差>1e-12即失败 |
| 通用VJP与正式decoder梯度 | 高：训练与后续接共同训练依赖它 | unittest全坐标中心差分；非作者独立标量encoder/decoder，光滑点绝差≤1e-7，关系层反传必须用归一矩阵转置，错误即失败 |
| 无图与decoder表达限制 | 高：防止把不可表达误报优化失败 | 同型合法反向pair的DistMult分数相同，完整R解析构造覆盖56合法pair；no_graph 7尾同分，任一反例即失败 |
| 目标/逆目标隔离与test标签时点 | 高：逆边可直接给出答案 | 固定public消息16边；非作者拦截test读取直到selection完成，变test正例后checkpoint/selection/logit应不变；target或next_inv入图、test参与train/val即失败 |
| 候选/过滤/排名/选择 | 高：filtered权限与指标决定评价 | 504分数重放绝差≤1e-10，144query独立排/删尾、27summary与9selection误差≤1e-10；均分7尾rank4→3.5，改并列合同或filter阶段不符即失败 |
| 等变与图显示 | 中：保护重编号与读图含义 | 类型/特征/各关系同步重排，节点与对应pair分数误差≤1e-10；五派生文件重建逐字一致、SVG真实渲染目视。合法重排不等于泛化 |

作者5项行为测试实际通过（.032秒），覆盖有向多重边/schema/孤点、通用encoder VJP、三decoder全部参数梯度/固定表示/对称性、类型随实体重排和目标消息屏障、并列与阶段局部负例。重要断言另由非作者独立复算，不将作者测试数量当语义证明。两SVG使用主库已有CairoSVG实际渲染并目视，坐标/方向/数值/共同logit色标可读；读者执行无需CairoSVG。

## 后续本机任务与外部接口分别保留

本包仅一张人工构造KG，query相关，seed只是初始化敏感性组；不套独立图iid风险界，不声称真实KG、实体归纳、时间预测、因果或关系置信校准。dense关系矩阵及全候选枚举用于小图复算，未证明稀疏加速/大图性能。

公开小型真实KG的合法获取、实体/逆事实去重、CPU基线和公开时点拆分，是**后续可在本机自主完成、本包未做**的任务。接口应至少包含entities(id/type/feature/observed_at)、facts(head/relation/tail/observed_at/source)、schema、逆/等价关系规则、split与过滤真值的阶段说明；先锁定获取时点和实体组，训练预处理只拟合允许部分，重建消息图时从允许事实再派生逆边。候选集合与filter需按实体生效时点定义，不能让未来实体/事实偷渡回过去。静态公开KG没有真实时间戳时，随机附日期不能称真实时间验证。

只有确实需要未公开或受限数据、机构授权、超出本机内存/时限的大计算、专用GPU或真人结果时，才属于相应外部条件。当前未做的跨机复现、目标Obsidian客户端和真人学习也未认证；不能由本机运行推定。#161仍OPEN，后续整课验收另核完整scope，不能从本关系单元关闭。
