---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - Wikidata真实小面板监督构图实验
prerequisites:
  - "[[AI/16-图表示学习/09-真实知识图快照监督构图与逐实体评价]]"
sources:
  - https://www.wikidata.org/wiki/Wikidata:Licensing
  - https://www.wikidata.org/wiki/Wikidata:REST_API
  - https://www.wikidata.org/wiki/Property:P30
  - https://www.wikidata.org/wiki/Property:P47
  - https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format#Truthy_statements
---

# Wikidata真实小面板：监督构图与逐实体评价

这次使用实际取得的公开Wikidata结构化记录。固定20地理实体面板里，遮住部分实体全部P30目标值，比较无图偏置、从训练邻国标签产生的关系特征和一个预定机制基线。它是**一张静态真实KG的已记录事实遮蔽评测**，不称现实新事实发现、未知国家归纳、国家总体基准或时间部署。[[AI/16-图表示学习/09-真实知识图快照监督构图与逐实体评价|09完整主解释]] 给对象、推导、实际语义反例与撤提示题解。

## 数据从哪里来，实际保存了什么

[panel.json](panel.json) 固定20 QID与7个候选洲：人工地理教学面板，欧洲8、非洲8、亚洲4的先验选择，不代表自然类比例。50 QID资源草案在**任何模型分数出现前**因服务限流缩减为20，随后面板和协议先交非作者；未用模型表现挑实体、补足“容易”类别或换split。

规范 [fetch_wikidata.py](fetch_wikidata.py) 通过官方REST取27个英文实体标签和20×2个单属性statement响应，合计67次，原始正文101242字节（整份JSON容器152343字节）。固定 [source-responses.json](source-responses.json) 保留每响应URL、body原文、sha256、获取时间、HTTP Date、ETag/Last-Modified；没有只存人工抄出的事实。数据收集起止为2026-10-16 16:09:08至16:16:48 UTC（本地已是10月17日），约7分40秒，包括礼貌间隔；这与下面CPU训练时间分开。

Wikidata结构化数据使用CC0，范围和原始链接见 [DATA-LICENSE.md](DATA-LICENSE.md)。没有抓取第三方reference链接的页面全文，不把普通wiki说明文章或图片也当CC0。数据许可不认证事实准确/完整。每属性分次读取，不是同一原子dump修订；获取时点、HTTP日期与修订元数据都不是现实事实生效时点。

WDQS草案遇429，classic API带maxlag报告查询服务滞后，因此实际走REST单属性读；短批REST读也遇429后，固定串行6.1秒间隔并按Retry-After退避，支持partial断点恢复。失败SPARQL草案只在库外context，没有作为正式生成输入的query.sparql发布。正式训练与离线重放完全不联网；重新fetch会得到可能变化的**新收集件**，不保证恢复旧在线修订。

[source-audit.json](source-audit.json) 与 [inputs.json](inputs.json) 从同一原始响应确定性生成：

- best rank：每实体/属性有preferred则只取preferred，否则normal；排除deprecated和非具体实体值。完整rank/qualifiers/references仍在原始响应，生成器只保留其声明的简单投影。
- 本轮23条唯一best P30中，22条落在固定7洲候选内；Russia还有Q5401域外值，单列不擅自并洲。20实体均有投影内标签，无排除实体；Russia与Turkey各有两个目标值。逐属性事实没有重复；实体身份按QID，显示名不合并，全部statement ID/取舍可追。
- 145条唯一best P47中，52条有向边两端都在面板，其他93条出面板审计。去self后按明确P47对称语义补成54有向边（27无向对），新增反向为Spain→Algeria与Italy→Algeria。没有把缺失反向静默当原始数据。
- P47可含水界/单点，不能把这张图叫纯陆地边境；面板孤点只表示截断图中孤立。没有把国家名字、QID数值、坐标、全文、其他属性或P30全部答案喂给模型。

**实际语义反例不可略去：** France的preferred Europe带P518适用部分，其他洲也有normal语句与各自限定词。best-rank优先再去限定词后得到的目标，不完整表达France各部分的地理归属。因此候选记0只表示不在这份投影中，甚至可能有投影外的原始记录支持；它不宣告世界中该关系为假。我们恢复的是明确投影，不把数字排名当现实地理裁判。

## 拆分、标签构图与候选

[protocol.json](protocol.json) 在短预跑前固定。QID经固定salt的SHA256模10分组，0–5 train、6–7 val、8–9 test，同实体全部P30一起走。本次train11实体/12正事实、val4/4、test5/6。不是每条事实随机分到两边，不把两洲国家拆成两个独立样本；三个seed只改优化初始化，不是三张图。

公开support包含全部已知面板P47闭包与实体/候选类型。模型可见全部实体，是转导设置。**只有训练实体P30及由它们派生的逆边作seed**；heldout的P30正向、逆向均不构图。val/test仍用同一train种子，不把val标签回填后偷偷更改test输入。

编码接口复用08已发表 `relations.encode`：先将固定洲one-hot沿训练P30 inverse均值送到对应国家，多值seed按标签数归一；再沿P47按全部面板邻居均值传播。第二层root只保留常数1，P47无self，因此自己的目标标签不直接进入自己的最终表示。未标注邻居仍计在度分母，消息总量可小于1；孤点结构特征0。

公式是固定的，seed与特征却依赖训练标签，故称**监督构图/标签传播**，不是看训练集之前固定的ψ。不引用旧iid独立图泛化界，合法重编号也不单独证明泛化。每实体实际degree、训练邻国QID、消息向量和self系数见 [results/graph-audit.json](results/graph-audit.json)。

七候选洲全部枚举，没有随机抽负尾。训练BCE把该实体不在best-rank投影中的候选记0，这是明确的记录重建/未知当负假设，**没有现实真值完备保证**。训练行只读train正例，不查test答案过滤负例。与08人工完整行的封闭世界不同，真实开放知识图中的未记录仍可能为真。

| 阶段 | 消息/表示 | 拟合或选择 | 排名过滤真值 |
| --- | --- | --- | --- |
| train | public P47+train P30 seed | train全7候选BCE更新 | train |
| val | 同一public和train seed | val全7候选BCE选epoch | train+val，禁止test |
| test | 同一public和train seed | 选项冻结后仅评价 | train+val+test，仅供最终候选过滤 |

`train_all(core,relations,public,train,val,...)` 不接test。所有学习头和固定机制的selection先写出，然后才进入该轮test读取。原始公共数据文件包含答案供审计，程序路径隔离不是对任意外部操作者从未看答案的承诺。

## 相同打分形状，不夸大参数公平

每个国家用8维f=[七洲标签消息,1]，候选洲为7维one-hot；矩形双线性等于线性头 `f @ W`，W为8×7。适配层补一个始终0的列，调用08成熟 `scores/objective/rank`，该补列不训练、不计参数。只读父graph_task的JSON/digest/sigmoid与08规范关系模块，两个父源码身份均绑定；不复制或重训旧合成框架。

| 模型 | 规则 | 预算 |
| --- | --- | --- |
| no_graph | 国家仅常数1；候选洲仍one-hot，可学不同类别prior | 存56参数，7个bias影响分数，其余只受L2 |
| relational | 国家用实际监督邻国消息+1，同形状W | 存56参数；本训练f矩阵秩3，有效训练支持不等于56独立方向 |
| neighbor_prior | `.5*Z + .5*(train_count+1)/(train_heads+2)` 再取logit，逐洲Bernoulli值不强制和1 | 固定机制基线；无可训练参数、无epoch或混合系数搜索，只算一次 |

两学习头seed17/29/43，400轮全批Adam（β1=.9、β2=.999、ε=1e-8）、学习率.03，λ=.01，所有W包括常数行正则。各模型独立选最小val BCE的最早epoch；固定neighbor_prior预先指定.5，不看val选择。无架构搜索/后验选seed，不用test调系数。本包不共同训练encoder，也不把名义同形状说成有效自由度完全相等。

## 正式结果，保留简单机制胜出的事实

正式CPU训练+评价0.319262秒；短预跑seed17/20轮0.043841秒。**预跑也调用同一完整run，因此每轮selection后会生成其test指标**；作者只检查其环境/资源输出，协议在预跑前固定，随后未按test表现更改。正式不是外部盲测，数据本就是公开记录的教学遮蔽评测。网络获取耗时另计，不拿下载速度当模型训练速度。

主要指标先在每个实体内平均其正事实倒数排名，再在实体间等权平均（macro-country）。同时报告micro-positive-triple；Russia/Turkey多值，不把多条事实当独立实体。并列用1e-10容差与平均rank，然后取倒数；不混成随机打破并列的期望MRR。filtered只移除同头其他已知真值，保留目标；不回写分数、图或参数。

| seed | model | selected epoch | test BCE | entity raw MRR | entity filtered MRR | entity Hits@1 | micro filtered MRR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | no_graph | 226 | 0.381556 | 0.600000 | 0.616667 | 0.300000 | 0.638889 |
| 17 | relational | 223 | 0.353258 | 0.700000 | 0.716667 | 0.500000 | 0.722222 |
| 29 | no_graph | 215 | 0.381551 | 0.600000 | 0.616667 | 0.300000 | 0.638889 |
| 29 | relational | 219 | 0.353255 | 0.700000 | 0.716667 | 0.500000 | 0.722222 |
| 43 | no_graph | 216 | 0.381556 | 0.600000 | 0.616667 | 0.300000 | 0.638889 |
| 43 | relational | 221 | 0.353259 | 0.700000 | 0.716667 | 0.500000 | 0.722222 |
| fixed | neighbor_prior | none | 0.277356 | 0.933333 | 0.950000 | 0.900000 | 0.916667 |


三seed都得到同样排名只是本面板上的初始化观察，不是总体鲁棒性证书或三独立图置信区间。结构头比无图头的实体MRR高.1，但预定neighbor_prior明显更好，不能只截出结构头对弱基线的一段差距宣传GNN胜利。

![[AI/80-实践/11-图传播训练与评测/real/figures/entity-results.svg]]

逐项解释采用seed17，全部三seed原始结果仍保留：

- Mali经训练邻国Niger得到Africa信号，结构头排名由2变1，兑现了这轮主要提升。
- Algeria的P47邻国包含Italy/Spain等跨水关系；其消息Africa=4/7、Europe=2/7，结构头仍把Europe排前，固定机制却正确。度数与消息不是单一的地理真值。
- Turkey在**本面板**度0，三种方法只能回到先验排序，实体filtered MRR=.75；不能据此说现实Turkey没有邻国。
- China收到Russia和India的seed，得到Asia=.75、Europe=.25。但训练实体的Asia输入列全0，不等于训练没有Asia标签（Russia/India本身有）。这一特征方向没有任务数据梯度，验证也不提供同样支持；自由W不自动知道洲坐标语义，固定机制反而保留它，China排名从3到1。
- 训练Netherlands与Morocco的最终输入都为Europe=.5、其他0、常数1，目标却分别Europe与Africa；同输入的任意确定性头都不能同时恢复不同标签。这个表示碰撞与Asia特征覆盖不足又是两种机制，不全归优化，更不是多层过平滑。

![[AI/80-实践/11-图传播训练与评测/real/figures/supervised-support.svg]]

## 离线复现与必要时重新获取

规范 [wikidata_task.py](wikidata_task.py)、[fetch_wikidata.py](fetch_wikidata.py)、[test_wikidata_task.py](test_wikidata_task.py)、[render_real.py](render_real.py)；完整 [[AI/80-实践/11-图传播训练与评测/real/源码镜像|源码镜像]]。数值仅需Python与NumPy，默认父目录保有已发表graph_task.py与relations/relations.py。以下从本real目录运行，输出路径必须尚不存在：

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 -B wikidata_task.py prepare --output /private/tmp/wwl-real-new-prepared
python3 -B wikidata_task.py train --inputs /private/tmp/wwl-real-new-prepared/inputs.json --output /private/tmp/wwl-real-new-results
python3 -B -m unittest -v test_wikidata_task
python3 -B render_real.py --output /private/tmp/wwl-real-new-figures
```

末条重画当前目录已保存结果。新一轮作图须将同轮inputs.json、results/放在独立目录，再用 `--root /同轮目录 --output /新图目录`，不混预测/标签；此绘图布局针对当前固定面板，不是自动地理地图。

普通复现优先使用已附源，无需在线抓取。若确需新收集件，运行 `python3 -B fetch_wikidata.py --output /private/tmp/wwl-wikidata-new-source.json`；脚本只读官方公共端点，单响应150KB/总原文2MB上限，串行6.1秒，遇429/503按Retry-After至少等60秒、最多5次重试，留partial断点。将新source-responses.json与同版panel/protocol置独立root后再prepare；它是新数据，不覆盖本次源或沿用旧成绩。可靠真实时间任务仍需另外取得真实生效/观测时点，不能给静态边随手配日期。

候选未复制父源码，维护时传 `--parent /主库/AI/80-实践/11-图传播训练与评测`，测试设置 `WWL_GRAPH_PARENT` 为同路径。正式prepare/预跑/训练/作者测试/图生成均经团队两槽运行器 `python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 -B ...`，CPU一线程；网络fetch独立串行不占数值槽。已执行Python3.14.7/NumPy2.5.2/macOS27.0.1 arm64，无GPU、框架安装或旧实验重跑。

## 原始输出与核查入口

- [results/identity.json](results/identity.json) 绑定规范源码、固定输入、协议、原始源、面板与两父源码7身份；[environment.json](results/environment.json) 记录真实数值时间。
- [checkpoints.json](results/checkpoints.json) 给6学习头的参数/400轮train-val轨迹和固定机制记录；[selection.json](results/selection.json) 共7项。
- [raw_scores.json](results/raw_scores.json) 共980候选对，含QID、split、y、logit、CE；[query_ranks.json](results/query_ranks.json) 154项正事实排名及移除尾实体，能查filtered具体删什么。
- [head_metrics.json](results/head_metrics.json) 140项实体指标；[summary.json](results/summary.json) 21项split均值。一个实体在不同模型出现多次不增加样本数。
- [features.json](results/features.json) 保存27实体×8维H；[graph-audit.json](results/graph-audit.json) 保存20实体的监督可见路径，来源投影审计另见source-audit。
- [figures/diagnostics.json](figures/diagnostics.json) 含test实体指标、train输入列最大值/秩与碰撞对；[support-layout.json](figures/support-layout.json) 给实际图位置/边及可见seed；[results-table.md](figures/results-table.md) 给完整7行test表。

| 断言 | 重要性及原因 | 固定输入/命令、独立预期及失败判据 |
| --- | --- | --- |
| 许可、原始响应、rank/qualifier投影与QID身份 | 高：合法且可复算不等于测到正确对象 | 固定source/panel，prepare；独立解析67 body hash、20实体/23 P30/145 P47、过滤取舍与multi值，任一身份/取舍不符即失败；不能把投影0当现实假 |
| split与监督图无heldout正/逆标签 | 高：标签种子可直接给答案 | QID整组hash、仅train seed；非作者拦截test直到所有selection写完，改test真值应不改变特征/参数/选择/logit；出现self边/heldout seed或阶段访问即失败 |
| 基线与结构信号/新矩形头适配 | 高：无图尾表示清零会造假弱基线 | Country常数、Continent one-hot；独立Fraction算多洲/边度/孤点，改变P47或seed不影响no_graph。新适配全56参数差分绝差≤1e-7；旧成熟公式不重复全面重审 |
| raw、rank、macro/micro与val选择 | 高：多值实体会改变分母 | 980分数独立重放绝差≤1e-10，154 rank/140实体/21summary与7selection重算≤1e-10；macro/micro不可偷换，filtered阶段不得错 |
| 源到图/实际展示与案例 | 中：图须兑现同一模型/输入 | 两SVG与3数值/表派生共5文件重建逐字一致；真实栅格渲染目视，标清非地图/单位/seed。Netherlands-Morocco碰撞与train Asia列0须可重算 |

作者4项新增行为测试实际通过：rank投影/重数/身份/原文hash、监督seed无self/孤点和合法no_graph尾表示、矩形头适配小夹具差分与固定机制、macro不同于micro。重要断言由非作者另独立核；不把测试数当正确性分数。两SVG经已有CairoSVG真实渲染并目视，刻度/单位、训练标签可见性和图例清楚；源码运行不要求CairoSVG。

## 已完成与真正未验

本包已取得实际公开KG、固定原始源、离线prepare、训练与逐实体评价；有限真实KG入口已兑现这一层，不再整体记为“真实图未做”。静态公开数据的实体外推、其他关系、公开小型时间数据、连续边属性等仍可在本机自主推进；source没有可靠事件时间时就不称时间测试。

面板选择、关系/标签投影、未知当负与有监督seed限定了当前结论；未验证自然国家总体、现实缺失发现率、真实时间部署、因果、概率校准、大图稀疏/GPU、跨机器、Obsidian客户端或真人理解。机构受限数据、巨大计算或专用硬件/人体验证才对应具体外部条件。#161仍须另核完整scope，首个真实小面板不自动关闭课程。
