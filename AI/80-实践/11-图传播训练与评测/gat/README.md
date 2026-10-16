---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - GAT与均匀图消息的有限对照
prerequisites:
  - "[[AI/16-图表示学习/06-GAT图注意力归一化与多头消息]]"
  - "[[AI/80-实践/11-图传播训练与评测/README]]"
  - "[[AI/80-实践/11-图传播训练与评测/graphsage/README]]"
sources:
  - https://arxiv.org/html/1710.10903v3
  - https://web.stanford.edu/class/cs224w/slides/04-GNN2.pdf
---

# GAT图注意力的有限实践

这里执行 [[AI/16-图表示学习/06-GAT图注意力归一化与多头消息|GAT主课]] 的同一模型与学习链。规范源码为 [gat.py](gat.py)、图源为 [render_gat.py](render_gat.py)、作者行为测试为 [test_gat.py](test_gat.py)；[[AI/80-实践/11-图传播训练与评测/gat/源码镜像|完整源码镜像]] 逐字对应。父目录的固定输入、loader、指标与已有无图/GraphSAGE控制只读复用，不改旧源码、旧结果，不复制另一套训练框架。

## 固定任务、参数与基线公平范围

[inputs-reference.json](inputs-reference.json) 指向首包120张固定图及已发表控制；数据生成、合法时点、整图12/4/4拆分和节点标签对象沿用04课。每图24节点，训练只访问train标签，validation只用于选择，test与两组旧baseline结果在全部新GAT选择写出后才进入评价。两环境特征同分布而非配对同一实现，图内节点不当独立图。这个test已经公开使用过；本次是复用教学基准，不声称新盲测或普遍排名。

[protocol.json](protocol.json) 在预跑前固定：seed17/29/43、两环境、attention/uniform两个方案；两层，隐藏2头×4维拼接后ELU，输出2头×1个logit取均值；self进入每行合法邻域，Leaky斜率.2，无dropout/采样/残差。每方案120轮Adam，学习率.03、权重L2系数.001，Adam参数与父实践相同，偏置不正则化。固定按最小验证逐图平均交叉熵选epoch，严格平分留早期轮；不搜索深度/头数/学习率，不看test改seed或阈值，分类直接logit≥0。

attention每头的变换、左右评分向量与偏置都训练，共62个标量参数。uniform保存相同参数形状与相同值投影初始化，但直接把合法邻域设为等权，20个评分参数不影响输出、不更新、不正则化，有效42个可训练标量。它检验“加入可学习打分”的整体差别，不构成相同有效参数预算的比较。

原无图控制与全邻域GraphSAGE的验证选择、原始预测在 [baseline_reference.json](results/baseline_reference.json) 中标记复用，**未重训**。GraphSAGE深度1/2的49/185参数、tanh+L2归一化、外部邻居/self拼接，与本GAT不匹配；旧无图还在深度0/1/2/4上选择。候选集合、激活、归一化、self处理及实际计算预算不同，不能把全部架构分差都归因于attention，也不宣称完整公平榜单。

原论文§2.1式1–6提供经典masked加性GAT；§3.3还做固定注意力的同结构对照。本包借用其问题设置，不重现其数据、头数、dropout、训练率或已发表性能。

## 输入、输出与本机命令

Python+NumPy即可，CPU一线程、不用GPU或外部数据。实测Python3.14.7、NumPy2.5.2、macOS27.0.1 arm64；seed17/20轮预跑约.094秒，固定正式训练约1.103秒，经统一两槽runner。预跑仅查资源与实现，没有依据预跑test换协议。运行时间不包括大图稀疏优化，更不是跨机速度保证。

从本子目录执行。输出目录必须尚不存在；集成后 `--parent ..` 指向已发表父实践；独立候选可改成主库父实践的绝对路径，只读其数据。

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 -B gat.py --parent .. --output /private/tmp/wwl-gat-new-run
python3 -B -m unittest -v test_gat
python3 -B render_gat.py --output /private/tmp/wwl-gat-redraw
```

绘图默认重画本目录保存的 `results/`；不会自动使用第一条新运行。对新一轮，把该轮 `results/` 放到独立工作目录，再 `render_gat.py --root /该目录 --output /新的图目录`。改变协议属于新实验，先锁可见性/选择再看test。

- [identity.json](results/identity.json)：本次新源码/协议及父输入、core、两旧基线引用的实际身份；[environment.json](results/environment.json) 为环境和实测时间。
- [checkpoints.json](results/checkpoints.json)：12次训练的被选参数及完整120轮train/val交叉熵；[selection.json](results/selection.json) 记录12个验证选epoch，先于test评价写出。
- [raw_predictions.json](results/raw_predictions.json)：240条模型—图记录，每条保留24个logit、标签、correct/nodes/accuracy/自然对数交叉熵。[summary.json](results/summary.json) 是36条按seed/环境/方案/split的逐图均值与逐图最小/最大。
- [baseline_reference.json](results/baseline_reference.json)：两已发表控制的6+6个验证选择及各120条原始预测。原参数仍在各自父目录维护，不复制第二套checkpoint。
- [fixtures.json](results/fixtures.json)：三节点路径的同源码单头alpha/输出、以及静态排序的共同两key条件权重。[figures/selected_data.json](figures/selected_data.json) 与 [selected_table.md.txt](figures/selected_table.md.txt) 由结果确定生成全部24个最终比较行，未重选模型。

前向接口为 `forward(params,A,X,variant,protocol)`，不接标签、graph_id、split或seed。mask只从A加一个self得到，输出节点数可变；实现仍只支持同批相同节点数的简单无向无权图。17节点夹具仅验证计算接口，未验证新分布准确率。

## 断言、重要性与实际验证

主课给完整公式与导数；如下清单把实验目标与失败判据固定下来。作者测试不是独立oracle，最终非作者签收另按实际字节核对。

| 断言与重要性理由 | 本机/外部与固定输入、命令 | 独立预期、容差与失败判据 | 本次结果与未验范围 |
| --- | --- | --- | --- |
| 高：归一化对象、self/孤点与mask决定模型语义 | 本机三节点路径及一孤点；`python3 -B -m unittest test_gat.GatTests.test_hand_attention_mask_and_stability` | 解析alpha/输出误差≤1e-12；行和1、非边精确0、孤点self=1；合法分数1000而非边1e100仍有限 | 作者通过；非作者独立标量对照，不以作者softmax求真值 |
| 高：完整梯度包含score与value路径 | 本机固定5节点路径+孤点、非零特征；`python3 -B -m unittest test_gat.GatTests.test_all_parameter_gradients` | 中心FD步长1e-6、每参数绝对误差≤1e-7；避Leaky折点，不能只检查W或正则梯度 | 两方案全部参数通过；独核另查query评分的非正则任务梯度，未声称折点有唯一导数 |
| 高：heads形状、一般等变与新节点计算 | 本机同图任意重排及17节点夹具；`python3 -B -m unittest test_gat.GatTests.test_permutation_heads_and_new_size` | 重排误差≤1e-12；hidden输入宽8、最终shape(G,N)、末层均值等于手动合并 | 作者通过；不同n只证接口，不证归纳准确率 |
| 高：静态排序/均匀控制解释不能写反 | 本机query -2/+2、key -1/+1；`python3 -B -m unittest test_gat.GatTests.test_static_ranking_and_uniform_control` | 两query都更偏key+1但alpha数值不同；uniform修改评分参数不影响输出 | 作者通过；不将单头排序限制扩大成全网络分类不可能 |
| 高：标签访问、旧基线、逐图分母与选择时点影响成绩含义 | 本机全部120固定图和旧结果；新 `gat.py` 与全部raw/selection/轨迹 | 独核重放240logit记录、36summary和12最早最低val epoch；test及旧baseline只在新选择后用；反转test标签不改参数/选择/logit | 作者保留所有输出；最终时点guard/独立重算由非作者完成，公开test适应性边界不消失 |
| 中：图和计时只描述本次有限实现 | 本机 `render_gat.py` 与environment；外部接口见下 | 3图由同fixtures/summary确定重建，数值/单位一致；不预设多头或dense更快 | 三SVG已实际Cairo渲染目视；稀疏/GPU/真实图未验 |

按模块执行前述完整测试命令即可覆盖全部四项。LeakyReLU在0的代码导数约定为.2；手算路径有一项原分数0，但该图只核前向，参数FD使用另一组远离折点的固定输入。稳定softmax和稳定逻辑损失分别避免指数溢出；数值稳定不自动保证对象选择正确。

## 结果与坏例

![[AI/80-实践/11-图传播训练与评测/gat/figures/gat_comparison.svg]]

每个圆/方/三角分别为seed17/29/43，在4张test图上的平均；短横为三seed均值。所有方案预先列定，不按test挑赢家，无置信区间。无图与SAGE标星表示已发表控制复用，预算与模型选择集合的差异见前文。

同配环境下无图/SAGE_full/uniform/GAT均值分别为.7361/.9097/.9167/.9201；异配分别为.7743/.9618/.7639/.8854。在这批异配图中，GAT超过同结构uniform，但仍低于已发表SAGE_full；不能将“可学权重”解释为普遍胜过分开self/neighbor。

保留seed43同配坏例：GAT均值.8229，uniform为.8333，两者最差图均只有.6667；seed29异配GAT虽均值.8854，最差图只有.6667。这些不被删掉，也不凭低分推断具体是表达限制、优化或分布问题。当前固定少量公开图不支持普遍排名；完整分布与失效解释还需另定实验。

完整最终24行如下，test均值按图等权，每图节点数24；最小/最大为4张test图的范围。

| seed | 环境 | 模型 | val选epoch | test逐图均值 | 逐图最小–最大 |
| --- | --- | --- | --- | --- | --- |
| 17 | heterophily | GAT | 56 | 0.8958 | 0.7500–0.9583 |
| 17 | heterophily | SAGE_full* | 50 | 0.9583 | 0.8750–1.0000 |
| 17 | heterophily | no_graph* | 28 | 0.7500 | 0.7083–0.8333 |
| 17 | heterophily | uniform | 47 | 0.8021 | 0.7083–0.8750 |
| 17 | homophily | GAT | 62 | 0.9688 | 0.9167–1.0000 |
| 17 | homophily | SAGE_full* | 113 | 0.9479 | 0.7917–1.0000 |
| 17 | homophily | no_graph* | 17 | 0.7396 | 0.6667–0.7917 |
| 17 | homophily | uniform | 51 | 0.9688 | 0.9167–1.0000 |
| 29 | heterophily | GAT | 107 | 0.8854 | 0.6667–1.0000 |
| 29 | heterophily | SAGE_full* | 97 | 0.9479 | 0.8750–1.0000 |
| 29 | heterophily | no_graph* | 15 | 0.8021 | 0.7500–0.8750 |
| 29 | heterophily | uniform | 27 | 0.7917 | 0.5000–1.0000 |
| 29 | homophily | GAT | 75 | 0.9688 | 0.9167–1.0000 |
| 29 | homophily | SAGE_full* | 67 | 0.9792 | 0.9583–1.0000 |
| 29 | homophily | no_graph* | 120 | 0.8021 | 0.7083–0.9167 |
| 29 | homophily | uniform | 120 | 0.9479 | 0.8750–1.0000 |
| 43 | heterophily | GAT | 90 | 0.8750 | 0.7083–1.0000 |
| 43 | heterophily | SAGE_full* | 70 | 0.9792 | 0.9583–1.0000 |
| 43 | heterophily | no_graph* | 22 | 0.7708 | 0.7083–0.8333 |
| 43 | heterophily | uniform | 57 | 0.6979 | 0.5833–0.8333 |
| 43 | homophily | GAT | 120 | 0.8229 | 0.6667–1.0000 |
| 43 | homophily | SAGE_full* | 85 | 0.8021 | 0.6667–1.0000 |
| 43 | homophily | no_graph* | 44 | 0.6667 | 0.6250–0.7083 |
| 43 | homophily | uniform | 120 | 0.8333 | 0.6667–1.0000 |


## 真实图、解释与大图的外部接口

真实数据接入前要先给出实体去重、边/特征时点、标签来源、许可和部署时可见关系，再锁拆分和模型选择。当前原始A必须对称、无输入自环、0/1；有向边、权重、边属性或关系类型需要另写mask/打分合同，不能悄悄塞入现API。

大图验证须实现稀疏按边打分、分段softmax和gather/scatter，测真实峰值内存、吞吐与邻域获取成本。当前dense源码每头保留G×N×N的raw/alpha与梯度缓存，复杂度不能写成已经达到稀疏O(E)内存；多头也增加参数与缓存，未测GPU并行收益。

若要用注意力作解释，先定义解释目标和独立忠实性检验；若要声称因果，另需对应干预或识别设计。权重图本身没有提供这些证据。当前已验证小合成CPU训练、数学有限例、程序行为和三图；真实图、稀疏大图/GPU、跨机复现、Obsidian点击显示与真人迁移均未验。异质图/知识图谱、边/时间任务及原完整图级统计比较仍未完成，#161继续OPEN。
