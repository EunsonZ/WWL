---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - 图分类读出与实体分组小实验
prerequisites:
  - "[[AI/16-图表示学习/07-图级读出表示能力与分组评测]]"
sources:
  - https://proceedings.mlr.press/v70/gilmer17a/gilmer17a.pdf
  - https://arxiv.org/html/1810.00826v3
---

# 图级读出与分组评测实践

本实践把一张图作为一个监督样本：输入可变长无向简单图与恰两个节点标记，判断**两个标记是否相邻**。它给读出层一个可证明能表达、又不能靠节点特征袋回答的问题。先读 [[AI/16-图表示学习/07-图级读出表示能力与分组评测|07课的对象、推导、反例与题解]]。同构拓扑即使重新标号或改标记，也属于同一身份组；本轮所有seed和split合起来都没有重复拓扑。

这是一项固定的有限合成基准。按类别平衡生成、全局拒重及计算上限拒绝抽样，使样本之间存在约束；**不同拓扑不意味着独立同分布**。不能把本次36张训练图直接塞进旧课的iid泛化公式并声称已获保证。03/04的节点实验、GraphSAGE和GAT均未重跑；这里只读复用父目录 `graph_task.py` 的JSON、digest、数组校验和稳定sigmoid。图级模型、损失和分母独立实现，防止误用节点平均指标。

## 输入、模型与选择合同

固定 [protocol.json](protocol.json) 在预跑和正式训练前落盘。种子17/29/43，节点数6/8/10，每个seed、每种大小各12张train、4张val、4张test，合计180张。每个这些小层内标签恰好各半。候选为边概率.35的连通图；选择两标记后按目标类别拒绝，随后按未标记邻接矩阵精确去重。完整 [inputs.json](inputs.json) 保留A、X、图标签、split和group_id，生成1380次提案接受180张，计算上限拒绝0次。

`canonical(A)` 按度数固定块顺序，穷举块内所有排列，取上三角邻接码的字典序最小值并包含n。任意同构保持度数，所以这是本支持域内的精确同构身份，不是度序列或WL散列。排列数超过10000时直接拒绝该候选，没有散列后备。它不适合大型规则图，例如10节点正则图会因10!超限而拒绝；本轮没有触及上限，不表示一般图都能进来。标记X完全不参与身份。全局 `seen` 跨全部seed和split共享，也因此三seed结果不能宣称三个独立实验样本。

模型只见 `A[n,n]` 与 `X[n,1]`；无自环、X为二值且恰两个1。没有图ID、split、标签、canonical码作为特征。A是部署时可见结构，标签是可由A和X计算的合成性质；这是受控结构学习任务，不是隐秘生物标签。原始输入中保留答案用于复核，程序路径仍必须隔离标签。

| 模型 | 可见特征与计算 | 可训练参数 |
| --- | --- | --- |
| bag | 无边特征 `[n/10, mean(X), max(X), 1]`，有偏置线性头 | 4 |
| fixed | 任务特定固定编码器 `ψ=sum ReLU(2X+AX-2.5)=y`，线性头 `[ψ,1]` | 2 |
| sum / mean / max | 相同一层共享编码器 `H=ReLU([X,AX]W+b)`，W为2×8、b为8；三个读出各接有偏置线性头 | 每个33 |

sum实际用 `sum(H)/10`，10是固定常量，只调数值尺度；它不是按n求mean。三种共同训练模型在同seed共享初始化、240轮全批Adam、学习率.03与λ=.01；所有参数含偏置都加λ/2平方范数，头含偏置始终投影到欧氏球B=4。三者参数数相同、迭代数相同，编码器都由各自任务共同训练。因readout尺度和优化几何不同，不能称每个数值条件都相同。此处dense NumPy逐图运算只为可复算，无稀疏加速或性能优势结论。

bag已给无边方法图大小，避免用“不给大小”制造劣势；在本受限域mean(X)=2/n、max(X)=1。相同n的正负标签平衡，任何只用这组特征的确定性分类器最多50%。fixed是人为推导的合法结构机制基线，**不是一般编码器训练成绩**，也没有把y直接传进forward。推导与误加自环后的 `ψ_loop=1+2y` 见07课。

共同训练只按val的**逐图交叉熵**取240轮中最小值，同值保留最早轮。bag/fixed是凸头优化，不通过val调参：从零开始投影梯度，预定最多5000步，球上Frank–Wolfe gap≤1e-8即停止。目标J含正则；凸性给 `J(w)-min J ≤ ∇J(w)·w+B||∇J(w)||`，这是返回参数的优化证书，不等于精确极小点，也不能偷套要求精确解的算法稳定性结论。本轮bag1步gap0；fixed40步gap6.90e-9、头范数4。07课中的固定编码器风险界只是在额外iid假设成立时的理论接口，本轮采样合同不满足该假设；共同训练更不属于固定特征类。

所有15份selection及checkpoint先完成并写出，再首次进入test指标循环。train标签拟合，val标签只选择共同训练epoch，test标签只记最终指标。没有选seed、扫架构或按测试分数选读出。预跑用seed17、24图、20轮，只检查资源路径，随后正式协议未改；输入/协议和程序路径可核，不能因此保证任意外部操作者从未读过公开答案。

## 本次真实结果

每个seed的test是12张图，按图平均。accuracy直接比较logit≥0；CE用自然对数与稳定logaddexp。raw有900条模型—图记录，summary45条（含train/val/test），selection15份。每个test大小各4图，bag各大小50%，其余模型各大小100%。重标号审计的900次重放只检验不变性，不增加样本数。

| seed | model | selected epoch / convex steps | test graphs | accuracy | graph-mean CE |
| --- | --- | --- | --- | --- | --- |
| 17 | bag | convex 1 | 12 | 0.500000 | 0.693147 |
| 17 | fixed | convex 40 | 12 | 1.000000 | 0.151562 |
| 17 | sum | 236 | 12 | 1.000000 | 0.212708 |
| 17 | mean | 240 | 12 | 1.000000 | 0.164932 |
| 17 | max | 70 | 12 | 1.000000 | 0.027853 |
| 29 | bag | convex 1 | 12 | 0.500000 | 0.693147 |
| 29 | fixed | convex 40 | 12 | 1.000000 | 0.151562 |
| 29 | sum | 217 | 12 | 1.000000 | 0.192869 |
| 29 | mean | 240 | 12 | 1.000000 | 0.149649 |
| 29 | max | 78 | 12 | 1.000000 | 0.026818 |
| 43 | bag | convex 1 | 12 | 0.500000 | 0.693147 |
| 43 | fixed | convex 40 | 12 | 1.000000 | 0.151562 |
| 43 | sum | 234 | 12 | 1.000000 | 0.221177 |
| 43 | mean | 232 | 12 | 1.000000 | 0.174050 |
| 43 | max | 70 | 12 | 1.000000 | 0.023884 |


三种共同训练读出都达到100%并不矛盾：本任务只问是否存在两个相邻标记。每个读出都能保留一个足以回答该问题的门控信号；mean还可从原始标记均值恢复n。不能拿通用“mean丢重复次数”的反例直接判本任务必败，也不能把max的较小CE宣传为一般架构排名。CE不同反映不同尺度、正则和训练路径下的置信度。本包没有制造优化失败案例；bag的失败有严格信息限制，有限共同训练成功也不证明普遍可优化性。

![[AI/80-实践/11-图传播训练与评测/graphlevel/figures/test-readouts.svg]]

下面同一条四节点路径只改变标记，便可得到两个不同答案。它们的未标记拓扑身份相同，只作解释夹具，不进入180张训练数据，更不能拆到train和test两边“扩样本”。节点数4不同于正式训练大小，图中mean是该夹具门控的真实均值。

![[AI/80-实践/11-图传播训练与评测/graphlevel/figures/marked-path.svg]]

## 在本机重跑与复核

规范源码 [graphlevel.py](graphlevel.py)、[test_graphlevel.py](test_graphlevel.py)、[render_graphlevel.py](render_graphlevel.py)；可阅读同版 [[AI/80-实践/11-图传播训练与评测/graphlevel/源码镜像|源码镜像]]。仅需Python与NumPy；默认父目录必须保有已发表 `graph_task.py`，不复制整套旧训练框架。输出选择尚不存在的新路径，源码拒绝覆盖。以下从本graphlevel目录运行：

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 -B graphlevel.py generate --output /private/tmp/wwl-graphlevel-new-inputs.json
python3 -B graphlevel.py train --inputs /private/tmp/wwl-graphlevel-new-inputs.json --output /private/tmp/wwl-graphlevel-new-results
python3 -B -m unittest -v test_graphlevel
python3 -B render_graphlevel.py --output /private/tmp/wwl-graphlevel-new-figures
```

最后一条用当前目录已保存结果画已发表图。新一轮作图须将同轮protocol.json、inputs.json、results/放入独立目录，再用 `--root /同轮目录 --output /新图目录`，不混旧输入和新预测。render只需当前脚本与graphlevel源码，不加载父模型。

候选区没有复制父源码，维护者运行时给 `--parent /主库/AI/80-实践/11-图传播训练与评测`，测试设置 `WWL_GRAPH_PARENT` 为同一路径。正式数值、短预跑和作者测试均通过团队两槽运行器 `python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 -B ...`，CPU一线程，Python3.14.7/NumPy2.5.2/macOS27.0.1 arm64；正式训练加评测3.786秒，预跑.076秒，只是本机实测，不是跨机上限。无GPU、下载或新增依赖。

重要输入和结果入口：

- [results/identity.json](results/identity.json) 绑定规范源码、父core、协议和输入；[results/environment.json](results/environment.json) 记录实际环境与耗时。
- [results/checkpoints.json](results/checkpoints.json) 含最终参数及共同训练240轮train/val轨迹；[results/selection.json](results/selection.json) 含所选epoch及凸头证书。
- [results/raw_predictions.json](results/raw_predictions.json) 每条给图ID、拓扑组、节点数、y、logit、correct、CE；[results/summary.json](results/summary.json) 可从raw重算。
- [results/permutation_audit.json](results/permutation_audit.json) 保存反序重标号的logit差；[figures/readout-fixtures.json](figures/readout-fixtures.json) 保留路径图的A/X/门控数值；[figures/test-points.json](figures/test-points.json) 与 [figures/results-table.md](figures/results-table.md) 从同一summary派生。

| 要核的断言 | 重要性与原因 | 本机输入/命令与独立预期；失败判据 |
| --- | --- | --- |
| 未标记拓扑全局分组与可见性 | 高：重复实体泄漏会使整图拆分失效 | generate固定协议；独核小n全排列与另一路完整同构回溯，跨split/seed同构或把X作为身份即失败；超过cap必须拒绝 |
| 图级任务可表达、无图限制公平 | 高：否则会把表达不可能误报优化失败 | 全枚举小路径标记对；独立ψ=y、sum X·AX=2y、bag按n正负相同，任一反例即失败；自环变式不得仍称ψ=y |
| 共同训练与凸头梯度/证书 | 高：训练结果和理论优化对象都依赖它 | unittest全参数中心差分；非作者另写标量前向与loss，光滑点梯度绝差≤1e-7，max并列仅验所声明次梯度；凸gap独立重算≤1e-8+1e-12，否则失败 |
| 标签时点、val选择、raw逐图指标 | 高：直接影响评价正确性 | 非作者拦截test标签访问及反转test标签，训练参数/selection/logit应不变；全部900logit重放绝差≤1e-10，45summary/15selection重算≤1e-10，任何不符即失败 |
| 不变性、图和本机展示 | 中：保护解释与数值映射 | 全邻接及X同时重排，logit差≤1e-10；render新目录重建5派生文件须同字节，SVG实际栅格渲染目视轴/图例，不声称速度比较 |

作者5项行为测试实际通过：n4全部64标号图归11类、所有小路径标记对、五模型全部参数差分及重排、读出复制/并列梯度与投影、两种凸头证书。重要结论另由非作者独立复算；作者测试不替代最终独核。图的SVG用已有CairoSVG实际渲染再目视；读者运行源码不需要该渲染依赖。

## 迁移与尚未验证

外部真实图接口仍是列表 `[{A:n×n, X:n×d, graph_label, entity_group, time}]`；先定义部署时可见结构/特征与图标签，再给实体及时间拆分，固定预处理和验证选择。当前图标签生成器、恰两标记、ψ和binary头都不能直接当真实分子/知识图标签模型。大型图用经过验证的同构/实体标识流程处理去重，不放大穷举cap冒充可扩展；不同实体也可能共享采样机构或时间依赖，另查统计条件。

本包已验有限CPU合成任务、代码路径、逐图指标、精确身份与SVG；未验真实数据许可/标签、跨域风险、稀疏大图、GPU、跨机运行、Obsidian客户端显示或真人学习。07图级单元不自动关闭#161；异质图/知识图谱、真实图评测及整课剩余验收仍须独立处理。
