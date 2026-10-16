---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - GraphSAGE邻居采样有限实践
prerequisites:
  - "[[AI/16-图表示学习/05-GraphSAGE归纳表示与邻居采样]]"
  - "[[AI/80-实践/11-图传播训练与评测/README]]"
sources:
  - https://arxiv.org/html/1706.02216v4
  - https://web.stanford.edu/class/cs224w/slides/04-GNN2.pdf
---

# GraphSAGE mean与邻居采样实践

本子目录接 [[AI/16-图表示学习/05-GraphSAGE归纳表示与邻居采样|GraphSAGE主课]]，只读复用父目录已发表的120张固定合成图、loader和逐图指标；原 [graph_task.py](../graph_task.py)、输入和原结果均未改变。新规范源码为 [sage.py](sage.py)，图与派生审计源为 [render_sage.py](render_sage.py)，作者行为测试为 [test_sage.py](test_sage.py)；[[AI/80-实践/11-图传播训练与评测/graphsage/源码镜像|完整源码镜像]] 与执行文件逐字对应。

## 输入、模型与随机对象

[inputs-reference.json](inputs-reference.json) 指向首包固定 [inputs.json](../inputs.json) 与原无图基线结果；它记录版本及引用，不复制另一套训练数据。[protocol.json](protocol.json) 在预跑和正式实验之前固定：seed17/29/43、两环境、全邻域/外部fanout2/外部fanout4、深度1/2、宽度8、120轮、Adam学习率.03、权重L2系数.001；Adam参数与首包相同，偏置不正则化。预跑仅seed17、20轮，用于检查资源与实现，没有据预跑test调协议。

每层 `concat(self, external_neighbor_mean)` 后共享仿射+tanh+保护L2归一化；输入两维，深度1/2的参数数分别49/185。全邻域与采样模型在相同深度有相同参数形状及初值，区别是邻居子集与评价采样数。原无图MLP是已验证控制，参数预算及层的定义不同；其原验证选择与原预测仅复用，不能说本次重训或严格参数匹配。

训练每轮/每层/每节点重新均匀无放回抽取 `min(fanout, degree)` 个外部邻居，孤点邻居均值为0。全邻域为全部外部邻居，不在此分支另加自环。采样结果构成有向计算关系，即使原图无向，也不能在反传里漏掉转置。

验证和测试对采样模型各预定4套mask、先平均logit后算交叉熵与 `logit >= 0` 分类；全邻域只需一套。RNG键分别为 `[seed,regime_code,split_code,draw]`，训练更新用 `[seed,regime_code,0,epoch]`；训练结果展示使用独立固定键split_code3，val为1，test为2。图/节点按固定输入文件顺序排列，mask与标签无关。固定eval mask在所有epoch间不变，选择的是这个有限采样集成的验证损失，不是全邻域网络损失。

每个fanout独立按验证逐图平均交叉熵选epoch，再选深度；严格相等先保留较早epoch，深度平分选较浅者。不按test选择fanout。所有新SAGE选择与checkpoint写出后才进入test评价与读取原baseline结果。数据依然按整图12/4/4拆分，每图24节点；两环境X同分布而非同一有限实现。图内节点不当作独立图。

这里的测试输入是首包已经公开的教学基准；本次训练程序不从test选择新模型，不代表课程开发者从未见过原test结果。需要一次全新最终检验时，先锁设计，再采独立新holdout。

## 可重跑命令和输出

Python+NumPy即可，CPU一线程，无torch或数据下载。正式环境为Python3.14.7、NumPy2.5.2、macOS27.0.1 arm64；预跑.526秒，正式6.407秒，均经统一两槽runner、一线程。这些是本机观测，不是跨机速度承诺。

从本子目录运行。输出路径必须尚不存在；已有目录拒绝覆盖。集成后 `--parent ..` 指向已发表父实践；独立候选可把该参数设为实际主库父实践绝对路径，保持只读。

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 -B sage.py --parent .. --output /private/tmp/wwl-sage-new-run
python3 -B -m unittest -v test_sage
python3 -B render_sage.py --output /private/tmp/wwl-sage-redraw
```

最后一条重画本目录已保存 `results/`，不会自动改用前一条新结果。要画新一轮，使用一个独立工作目录，放入同轮 `results/`，并用 `render_sage.py --root /该目录 --inputs /同轮父输入文件 --output /新的图目录`。修改fanout/步数/深度后属于新实验，先锁新协议，再看新test，不将旧图贴到新数字上。

- [results/identity.json](results/identity.json)：本次新源码、协议、父输入、父core及复用baseline的实际身份；[environment.json](results/environment.json) 为环境和时间。
- [checkpoints.json](results/checkpoints.json)：36个SAGE候选的参数、120轮轨迹、验证选epoch及实际训练时间。[selection.json](results/selection.json) 为18个独立fanout最终选择，均在test评价前保存。
- [raw_predictions.json](results/raw_predictions.json)：720条候选—图记录，含每图24个logit、标签、correct/nodes、准确率和自然对数交叉熵；[summary.json](results/summary.json) 为108条按seed/环境/fanout/深度/split的逐图均值。
- [baseline_reference.json](results/baseline_reference.json)：原无图模型6个验证选择与对应120条原始图预测，标记“复用、未重训”。其原checkpoint仍由父目录维护，不复制第二套参数。
- [enumeration.json](results/enumeration.json)：固定四邻居值的全部子集、样本均值、有限总体方差及ReLU反例，无Monte Carlo估计误差。[figures/degree_audit.json](figures/degree_audit.json) 为被选模型的测试节点按度分箱计数，只是描述性节点统计，不把分箱计数当独立图样本数。
- [figures/selected_data.json](figures/selected_data.json) 与 [selected_table.md.txt](figures/selected_table.md.txt) 由同一summary/selection生成下表和图，不改变选择。

## 采样、梯度和数据合同的实验清单

所有命令从本目录运行；`test_sage` 各测试名可作 `python3 -B -m unittest test_sage.SageTests.测试名` 执行。独核应使用自己的标量/有理数真值，不能调用作者聚合器再称独立oracle。

| 断言及重要性理由 | 固定输入/命令入口 | 预期与容差 | 实际作者结果与独核接口 |
| --- | --- | --- | --- |
| 高：采样目标是外部邻居总体均值，影响所有后续统计解释 | 度4星图+度1叶+孤点；`test_sampling_count_full_and_isolate` | 不含self/不重复；度≤fanout的算子与full逐字相等；孤点全0 | 作者通过；独核应变fanout/邻度/重编号枚举，而非调用作者采样求真值 |
| 高：条件无偏与方差、非线性反例 | 值(-1,0,1,2)全部子集；`test_exact_enumeration_and_nonlinearity` | 均值.5；f2方差5/12；ReLU均值.25而全均值后为0，浮点误差≤1e-12 | 作者Fraction路线通过；完整枚举已保存 |
| 高：concat/归一化/采样算子转置的全部参数导数 | 固定同一mask的两层星图；`test_all_parameter_gradients` | 中心差分步长1e-6；绝对误差≤1e-6；不能两侧换mask | 全参数通过；独核需自己前向并冻结mask，覆盖full/f2 |
| 高：零范数保护与新节点数的计算接口 | `test_zero_norm_gradient_and_new_node_count` | 零向量输出0；保护分支FD步长1e-7误差≤1e-6；17节点前向shape=(1,17) | 作者通过；不据shape通过宣称新总体泛化 |
| 高：重编号与label/split可见性、逐图指标 | `test_coupled_permutation_and_normalization`；全部raw/checkpoint/selection | 搬运mask误差≤1e-12；独核重算每图CE/阈值分母、108summary/18selection；test标签翻转不改训练/选择/logit | 作者耦合测试通过；最终独核按实际字节另签，不由作者声明替代 |
| 中：展示/资源只支持本机有限实现 | `render_sage.py`；environment与每候选train_seconds | 同输入确定性图重建；轴/单位/点值一致；不预设采样更快 | 两图已Cairo实际渲染目视；稠密实现未证明大图加速 |

作者5项测试均通过，包括零规范化分支和17节点接口。重要断言还须由非作者核查最终源码、正文与结果，整合前另有签收。图是生成的有限结果，不代替数学证明或独立测试。

## 结果怎样解释

![[AI/80-实践/11-图传播训练与评测/graphsage/figures/sage_comparison.svg]]

圆/方/三角分别是seed17/29/43，每点为4张test图的等权准确率均值，短横线为三个seed均值。横轴是预先声明的三个fanout方案与已发表无图控制，没有用test反选方案；没有置信区间。

同配环境的无图/full/f2/f4三seed均值为.7361/.9097/.8785/.9201，异配为.7743/.9618/.9479/.9826。分开self与neighbor后，本任务的异配环境也能有高分，和“平均邻居一定只能做同配”不符；但模型结构、参数和训练目标已改变，不能把改进全部归为某一个因素。三个seed和公开小基准不足以建立普遍排名。

保留的坏例是seed43同配fanout2：均值.7604、最差图.625，低于full均值.8021；同时seed29异配fanout2的.9896又高于full的.9479。更大fanout也没有每seed都超过full；采样改变训练轨迹和目标、评价还做有限logit集成，不是只给一个固定预测加零均值噪声。

在seed43同配fanout2的96个测试节点中，度1–2为4/5正确、度3–5为48/59、度6以上为21/32；这是对该失败组的描述，节点相关且样本不等，不能推出“高程度因采样而因果性更差”。固定120图共有2880节点，度范围0–12，4个孤点与46个度1节点；孤点处理既有确定性夹具，也需在实际结果中保留空分箱为null而非误报0%或100%。

本机36个候选的训练时间（含采样和每轮验证）按方案取中位数，full约.083秒、fanout2约.230秒、fanout4约.182秒。采样在这个稠密全节点实现里更慢，符合采样开销与4次评价的事实；不把少读邻居条目误报成实际加速。这里不同评价draw数也没有保持计算预算相同。

完整最终选择如下；每行最小/最大来自4张test图，原始logit可独立重算。

| seed | 环境 | 模型 | val选深度 | val选epoch | test逐图均值 | 逐图最小–最大 |
| --- | --- | --- | --- | --- | --- | --- |
| 17 | heterophily | f2 | 2 | 120 | 0.9062 | 0.8333–0.9583 |
| 17 | heterophily | f4 | 2 | 77 | 0.9792 | 0.9167–1.0000 |
| 17 | heterophily | full | 2 | 50 | 0.9583 | 0.8750–1.0000 |
| 17 | heterophily | no_graph(reused) | 0 | 28 | 0.7500 | 0.7083–0.8333 |
| 17 | homophily | f2 | 2 | 34 | 0.9375 | 0.8750–1.0000 |
| 17 | homophily | f4 | 2 | 37 | 0.9688 | 0.9167–1.0000 |
| 17 | homophily | full | 2 | 113 | 0.9479 | 0.7917–1.0000 |
| 17 | homophily | no_graph(reused) | 4 | 17 | 0.7396 | 0.6667–0.7917 |
| 29 | heterophily | f2 | 2 | 94 | 0.9896 | 0.9583–1.0000 |
| 29 | heterophily | f4 | 2 | 98 | 1.0000 | 1.0000–1.0000 |
| 29 | heterophily | full | 2 | 97 | 0.9479 | 0.8750–1.0000 |
| 29 | heterophily | no_graph(reused) | 2 | 15 | 0.8021 | 0.7500–0.8750 |
| 29 | homophily | f2 | 2 | 112 | 0.9375 | 0.8333–1.0000 |
| 29 | homophily | f4 | 2 | 54 | 0.9688 | 0.9583–1.0000 |
| 29 | homophily | full | 2 | 67 | 0.9792 | 0.9583–1.0000 |
| 29 | homophily | no_graph(reused) | 2 | 120 | 0.8021 | 0.7083–0.9167 |
| 43 | heterophily | f2 | 2 | 99 | 0.9479 | 0.8750–1.0000 |
| 43 | heterophily | f4 | 2 | 120 | 0.9688 | 0.9167–1.0000 |
| 43 | heterophily | full | 2 | 70 | 0.9792 | 0.9583–1.0000 |
| 43 | heterophily | no_graph(reused) | 0 | 22 | 0.7708 | 0.7083–0.8333 |
| 43 | homophily | f2 | 2 | 100 | 0.7604 | 0.6250–0.9167 |
| 43 | homophily | f4 | 2 | 113 | 0.8229 | 0.6667–1.0000 |
| 43 | homophily | full | 2 | 85 | 0.8021 | 0.6667–1.0000 |
| 43 | homophily | no_graph(reused) | 0 | 44 | 0.6667 | 0.6250–0.7083 |


## 真实图和大图的外部接口

本子实践只验证小型合成CPU任务与固定图接口。对真实图，需要先声明实体去重、特征与边时点、标签取得方式和许可，再锁整图/实体/时间拆分；采样器只消费部署时可见的外部邻居。若输入图大小不同，可逐图调用当前前向，训练批处理需引入列表/掩码和明确每图分母；本包并没有实现变长图混批。

要验证大图收益，需要真正的目标节点小批、反向邻域展开、稀疏gather/scatter、缓存/去重以及峰值内存与吞吐测量，不能用当前稠密全图matmul推断。GraphSAGE的mean/concat/采样接口不覆盖GAT注意力、异质关系、知识图谱或所有时间部署问题。真实数据、大型/GPU训练、跨机复现、Obsidian点击显示与真人迁移未验，#161整课继续OPEN。
