---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - 独立合成图节点分类实践
prerequisites:
  - "[[AI/16-图表示学习/03-传播谱过平滑与任务信息]]"
  - "[[AI/16-图表示学习/04-训练拆分无图基线与泄漏]]"
sources:
  - https://proceedings.mlr.press/v70/gilmer17a/gilmer17a.pdf
  - https://arxiv.org/html/1609.02907v4
  - https://arxiv.org/html/1810.00826v3
  - https://web.stanford.edu/class/cs224w/slides/06-theory.pdf
---

# 图传播训练与评测

先读 [[AI/16-图表示学习/03-传播谱过平滑与任务信息|脉冲传播与谱]]，再读 [[AI/16-图表示学习/04-训练拆分无图基线与泄漏|可训练任务与可见性]]。本目录包含已执行的CPU合成实验：三种固定种子、两种边环境、三族模型和四个预先固定深度；不下载数据。规范源码是 [graph_task.py](graph_task.py)，绘图与审计派生源为 [render.py](render.py)，作者行为测试为 [test_graph_task.py](test_graph_task.py)。完整可阅读镜像在 [[AI/80-实践/11-图传播训练与评测/源码镜像|源码镜像]]。

## 可复算的输入与结果

- [protocol.json](protocol.json)：训练前固定的模型、深度、种子、步数、拆分和模型选择规则。Adam为 $\beta_1=.9,\beta_2=.999,\epsilon=10^{-8}$；全批训练、每轮一步，偏置不正则化。
- [inputs.json](inputs.json)：全部120张固定生成图，含邻接、两列测量与标签，生成参数见04课。每个模型只接收其中的A、X；测试标签仅评测使用。不能把公开答案文件存在解释为模型可以读取答案。
- [spectral.json](spectral.json)：同一六环/双三角形、脉冲输入与0至12步状态、特征值、到分量极限距离和全局中心化范数。
- [results/selection.json](results/selection.json)：18个按验证集选择的最终模型；在任何test评价前写出。[checkpoints.json](results/checkpoints.json) 保留全部72个模型深度候选的被选参数、epoch及120轮train/val交叉熵。
- [raw_predictions.json](results/raw_predictions.json)：1440条“模型深度—图”记录，含graph_id、split、标签、全部24个logit、每图correct/nodes/accuracy/交叉熵。阈值为logit≥0，边界正好0时判1。
- [summary.json](results/summary.json)：216条按seed/环境/模型/深度/split的逐图均值，含逐图最小/最大及中心化隐藏范数。[identity.json](results/identity.json) 将训练源码、协议、固定输入与本次结果关联；[environment.json](results/environment.json) 记录真实运行环境和时间。
- [figures/audit.json](figures/audit.json)：逐图实际边同配比例、答案列的非法泄漏构造、验证选深度与非法测试选深度的并列。没有将坏协议的分数混入主比较。读图与实际结果见 [[AI/80-实践/11-图传播训练与评测/结果解读|结果解读]]。

`inputs.json` 保留完整答案便于复算，权限纪律由明确的函数边界和执行路径审查支持：`forward(params,family,depth,A,X)` 无标签；`train_one` 只收到train/val图；所有候选与selection写完后才进入test评价。静态接口和独立重放可以检查程序路径，不能从JSON文件反推出任意外部操作者都从未偷看测试。

## 在本机重跑

需要Python与NumPy。已执行环境为Python3.14.7、NumPy2.5.2、macOS27.0.1 arm64，CPU一线程；未安装torch。根库已有 `.venv` 可供维护绘图，本实践源码运行仅需NumPy。其他机器先确认依赖，不把本机存在的环境当成跨机承诺。

从本目录执行，输出都用**尚不存在的新路径**。已有路径会拒绝，避免覆盖已发表结果。

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 -B graph_task.py generate --output /private/tmp/wwl-gnn-new-inputs.json
python3 -B graph_task.py train --inputs /private/tmp/wwl-gnn-new-inputs.json --output /private/tmp/wwl-gnn-new-results
python3 -B graph_task.py spectral --output /private/tmp/wwl-gnn-new-spectral.json
python3 -B -m unittest -v test_graph_task
python3 -B render.py --output /private/tmp/wwl-gnn-new-figures
```

最后一条默认用本目录已保存输入/谱/结果重画已发表图；不是用前面新输出作图。要画一轮新结果，建一个独立新目录，把同轮的 `inputs.json`、`spectral.json`、`results/` 放进去，然后 `render.py --root /该目录 --output /新的图目录`。不能用旧输入配新预测。CLI的 `--protocol` 是复现实验接口；本包只核默认固定协议，改协议属于新实验，须先定split/深度/训练规则再看test。

正式默认运行约1.53秒，预跑只用seed17和40轮约.21秒；这是本机实测值，不是他机上限。没有GPU、外部下载或架构搜索。图通过同输入输出的SVG生成，维护端用已有CairoSVG实际渲染四图并目视；课程代码不要求CairoSVG。

## 本次核查与证据边界

实验需要核对的断言按影响记录：

| 断言 | 重要性 | 作者检查及独核接口 |
| --- | --- | --- |
| train/val/test为独立生成的整图；模型不接收标签/图ID；test不选模型 | 高 | 固定RNG键、函数边界、输入可见性与selection写出顺序；非作者查生成和训练路径 |
| 非规则行均值反传用转置；每项参数梯度正确 | 高 | 三节点非规则图、全参数中心有限差分；非作者用独立标量循环前向与FD |
| 每图correct/节点分母/CE与逐图均值正确，选项来自val | 高 | 保留全部原始logit、标签、轨迹；非作者从raw重算并重放checkpoint |
| 两图固定线性谱、脉冲状态及分量投影 | 中 | Fourier/块矩阵推导与同输入状态；非作者Fraction及解析谱核算 |
| 四张图来自同次输入输出，轴和色标对应 | 中 | 同源render与SVG真实渲染、数字及标签检查；客户端仍需另验 |

作者4项行为测试均过：全部参数有限差分、节点重排/无图改边不变、谱/分量极限、拆分和指标（含正负极小logit与零的阈值边界）。重要结论的独立验收由本包外的非作者审阅记录承担，整合前须以最终字节签收；作者测试不替代该条件。非作者发现sigmoid舍入可使极小负logit错判后，已改为直接比较logit≥0并重跑正式实验；五份数值输出与修前逐字一致，源码identity已刷新。实际结果解读保留坏种子和失败解释，不把测试数当作内容正确性的分数。

本包已执行合成CPU训练、原始指标核查和四图渲染；未验证真实图数据、GPU、Obsidian客户端点击/显示、其他机器复现或真人迁移。#161整课仍未结项：[[AI/80-实践/11-图传播训练与评测/graphsage/README|GraphSAGE mean与邻居采样子实践]] 只读复用本包固定图和无图基线，补self/neighbor拼接、无放回枚举与有限训练；[[AI/80-实践/11-图传播训练与评测/gat/README|GAT子实践]] 继续用共享打分、局部行softmax和多头完成同数据有限对照；[[AI/80-实践/11-图传播训练与评测/graphlevel/README|图级读出子实践]] 将可变大小图汇成一个预测，补sum/mean/max表达边界、未标记拓扑分组与逐图分类评价；真实图评测、异质图/知识图谱与更多拆分协议仍有独立范围。

## 迁移到真实图前的接口

保留模型的 `A[G,N,N]`、`X[G,N,d]`、节点标签及按图评测接口，但实际图大小可不同，需使用列表/掩码并明确每图分母；当前固定大小批实现不可直接声称支持变长图。接入真实数据前，给出实体去重、获取时点、部署时可见边/特征、标签来源和数据许可；先锁定整图/实体/时间拆分，再拟合任何可学习预处理。先跑无图基线，再比较图模型。若部署任务是同图转导或边预测，应重写数据与评价合同，不能只替换文件名。
