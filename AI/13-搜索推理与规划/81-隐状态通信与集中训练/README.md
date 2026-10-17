---
type: practice
domain: artificial-intelligence
stage: 3
aliases: []
sources:
  - https://arxiv.org/html/1705.08926v3
  - https://arxiv.org/html/1706.02275v4
prerequisites:
  - "[[AI/13-搜索推理与规划/08-隐状态通信信用与集中训练]]"
---
# 隐状态通信与中央训练复建

主解释、一般条件和六道题解在[[AI/13-搜索推理与规划/08-隐状态通信信用与集中训练|08]]。本机实验只执行已声明的二元信道合成任务，不接真人、硬件、远程GPU或API。

## 输入与原始预测在哪里

- [[AI/13-搜索推理与规划/81-隐状态通信与集中训练/inputs.json|固定输入]]：η=.1，alpha=.2，logit盒[-6,6]，初始范围[-.25,.25]；6seed/6训练协议、每角色2000更新/每200保存checkpoint；12适应run各400新episode。
- [[AI/13-搜索推理与规划/81-隐状态通信与集中训练/signaling_lab.py|源码]]与[[AI/13-搜索推理与规划/81-隐状态通信与集中训练/test_signaling_lab.py|六项针对性检查]]：独立接收接口、16事件、旧critic顺序、反事实sender传播、档案/成本及guard。通用博弈与belief理论消费已有07/#194/#159；源码仅这个两阶段小任务，没有新造通用MARL平台。
- [[AI/13-搜索推理与规划/81-隐状态通信与集中训练/results/results.json|完整原始预测/评价]]：36runs的396个checkpoint，四logit、sender的$p(m=1\mid x)$两项、receiver的$p(a=1\mid y)$两项、8格critic与计数；216格crossplay、288角色伙伴表测试、60个适应checkpoint、三组16事件梯度一二阶矩、同历史合法/非法预测和确定码基准。
- `results/trajectory.csv.gz`保存88800行实际训练/适应记录。gzip只作体积压缩，mtime=0保证默认同环境逐字节复建；标准库可直接读，不需下载或私有服务。源码中HEADER就是列定义；没有用数值汇总代替原始行动和预测概率。
- [[AI/13-搜索推理与规划/81-隐状态通信与集中训练/code-sync/源码与测试镜像|Markdown源码镜像]]供阅读，`.py`仍是真源。两SVG由同一结果对象绘制；`assets/ai-marl-ctde/`两嵌入副本与结果SVG相等。

联合随机变量索引顺序为$x,m,y,a$，均取0/1，16事件；logit向量为`[sender_x0,sender_x1,receiver_y0,receiver_y1]`，critic扁平索引`4*x+2*y+a`。无码接收者的输入是None，使用唯一本地row0，row1没有得到假想的y；策略和其偏离评价都坍成常量分布。episode内隐藏X固定，下一episode独立重抽。成功/错误是概率，个体回报为终局点数0/1的期望J，团队为2J，均无物理单位。

每个seed的六条伪随机流是`random.Random(100*seed+i)`，i=0..5分别管初始化、X、消息采样、信道翻转、接收动作、历史档案选择；每实际episode各抽一次X/m/翻转/a。档案流只在snapshot协议使用，与其他流分开；不同协议复用相同seed是受控共同随机数，不是36个统计独立样本。没有按输出换seed或调参数。

## 旧参数、actor和critic各是什么版本

CSV的sender_version/receiver_version是该活角色已完成的梯度更新次数；critic_version为之前总访问次数。它们不一定相同：固定/无码只更新一角，snapshot一cycle有两条environment记录。`partner_checkpoint=current`用当前活搭档；snapshot列记录冻结对方表加入池的角色更新编号0/200/…；`frozen_receiver`为适应时固定的最终R。结合结果JSON中各checkpoint theta可精确恢复当轮有效对方参数。

`p_m1,p_a1`是实际采样前的行为概率，不是训练后输出；`b_sender_old,b_receiver_old`只由旧critic/当轮已知条件和取样前有效策略形成。actor更新用$r-b^{old}$，stop-gradient，之后才用本轮r更新critic。CSV保留四个**活候选**logit更新后值；snapshot的另一角色虽然在活候选里继续保存，但本条实际互动使用的可能是另一个冻结版本，因此必须同时看`active`和partner编号。日志不把冻结策略谎报为活策略。

## 本机命令与实际结果

作者Python3.14.7标准库。为遵守本轮两槽/单线程/300秒合同，在WWL根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 -B AI/13-搜索推理与规划/81-隐状态通信与集中训练/signaling_lab.py --output /private/tmp/wwl-signaling-rebuild
PYTHONDONTWRITEBYTECODE=1 python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- python3 -B -m unittest discover -s AI/13-搜索推理与规划/81-隐状态通信与集中训练 -p test_signaling_lab.py
```

临时runner只调度本轮本机任务，另一台没有它时可直接运行`--`后的Python命令。先以2seed/20次更新/10次适应的小输入运行，再执行固定完整配置。正式stdout（修复无码偏离集合后成功率不变）：

```text
{"runs": 36, "adaptation_runs": 12, "final_mean_success": {"fixed_sender": 0.8548049994362931, "fixed_receiver": 0.8545696723631339, "independent": 0.8877456628324448, "ctde": 0.8883106603931988, "snapshot": 0.8550051410926192, "no_comm": 0.5}}
......
Ran 6 tests in 0.001s
OK
```

输入校验拒绝不在[0,.5]的η、非正更新数/步长、重复seed、未知协议、不整除的checkpoint块、非法适应checkpoint等。固定及适应初值也须在logit盒内，避免把固定95%角色在首步悄改；例如bound=1直接拒绝。直接调用`evaluate_probabilities(...,receiver_blind=True)`若decoder两行不相同也拒绝，防评价器向无码角色开放不存在的消息。

读取原始数据，例如：

```python
import csv, gzip
from pathlib import Path
path = Path('AI/13-搜索推理与规划/81-隐状态通信与集中训练/results/trajectory.csv.gz')
with gzip.open(path, 'rt', newline='') as f:
    rows = csv.DictReader(f)
    first = next(rows)
    print(first['mode'], first['p_m1'], first['p_a1'], first['b_sender_old'])
```

结果图的脚本接口只支持这张信道模型；可以通过`--input`改变η、步长、种子与预算，不支持更换状态/奖励后沿用原解释。曲线从各run的冻结精确评价均值生成，不从原始奖励平滑。表格保存全精度，图坐标保留4小数，格内成功率保留2位；比较时不得拿显示舍入当原结果。

## 实验重要性、独立预期与失败判据

| 对象/断言 | 重要性与原因 | 独立预期/容差与失败判据 |
| --- | --- | --- |
| 相同局部历史与无码界 | 高；若泄漏X，整项任务已换 | 独立枚举同y两x，R分布逐字相同；无信息条件下任意参数J=.5（浮点≤1e-12），R偏离只能常量，gain≈0。任何合法任务J>1−η+1e-12或无码gain显著>0先查合同 |
| 通信公式/两种码/有限logit边界 | 高；承重概率与观测性 | 用Fraction另枚16事件核$J=.5+.5(1-2η)ΔpΔd$，正/反匹配.9、跨码.1；clip6上界.896053585133824，固定95%伙伴界.858219711327223，≤1e-12；不把有限随机域称达到确定上界 |
| 四维score与中央baseline | 高；信用机制可能改错目标 | 独立事件加权和/解析导数核均值[-.0256,.0256,-.0504,.0504]，三张旧表均值差≤1e-12，二阶矩/方差≤1e-12；再中央差分1e-5核导数≤1e-9。一般零均值证明另在正文 |
| 旧表→actor→critic及全部采样行为 | 高；用本轮答案更新baseline会破坏一般论证 | 不调用作者Trainer，重建随机流/历史档案，独立运行均值或计数恢复旧表，88800行行动/版本/partner/概率≤1e-12、actor logit≤1e-10；错误顺序、数据漏行、冻结角色改变都失败 |
| 396训练+60适应checkpoints、216crossplay、288角色伙伴表 | 高；高分可能只是熟悉约定 | 独立16事件或闭式J，逐份原始theta→概率/每人/团队/失败与合法BR增益误差≤1e-12；no_comm须使用盲策略类，变输入再核。固定partner真表与未见表分标，不拿适应后成绩冒冻结迁移 |
| 默认复建与图/副本 | 中；防不同图解释不同实验 | 同Python/代码配置4产物逐字节重建；两asset与结果图相同；学习图66点、三矩阵108格、适应10点按真实数据映射坐标误差≤1e-3像素；SVG格显示2位按四舍五入核 |
| 有限学习优劣 | 中；这是本种子族描述，不是一般定理 | 保留全部seed与失败约定，不用均值微差宣称优越/均衡；训练步数与环境预算分别核。不同Python库若舍入差改变动作，必须报分叉，不擅自放宽到仅均值近似 |

本包实现是实际离散消息学习和训练用中央critic，不是先写好正确码再只演示发送。固定码仅作有标记的参照/伙伴条件；independent/ctde/snapshot两角色均由随机小logit开始采样学习。中央critic在本任务奖励确定时很快可学对，不代表复杂逼近/长时记忆或稀疏回报也易学。通用算法收敛不从六seed实验或COMA的带条件引理借来。

图矩阵显示的“错误”包含信道噪声与搭档约定；完整公式和正/反码边界允许分别诊断，不能拿一个总失败率当机制识别。反事实baseline是学习估计，不是现实因果贡献、人的责任或公平分配证据。

## 冻结测试与适应必须分开

`heldout`是沿用的结果字段，含每份候选面对四种固定角色表、两个角色方向，共36×4×2=288条。其中固定伙伴训练条件下的相同正码表是熟悉控制；其他未出现在该run训练中的表是新伙伴，但这些表都属于相同合成机制。档案自博弈只面对单seed自己的历史，不会偷偷把其他seed的最终策略加入训练。

适应是另12次run：固定ctde最终接收者，分别从95%正码和95%反码发送者开始，用400条新奖励进行无baseline学习，只更新sender。每个适应checkpoint的期望评价仍冻结；适应期间收集的轨迹则是不断变策略的新数据，版本递增。它不是继续更新原R，更不是测试时不学习的 heldout。

## 原八目标与闭合判断

| 原目标 | 当前具体交付 |
| --- | --- |
| 1 联合状态/行动/收益/观测与社会基准 | 07协调表与Nash基准保留；08完整八状态两阶段通信表与有限策略映射 |
| 2 有效环境/他人策略变化 | 07固定对手边缘化已交；08sender/decoder版本与策略条件化、历史池目标及适应新样本继续消费 |
| 3 集中训练与分散执行 | 08信息表、真实学习critic、局部actor/独立PG/CTDE比较，脚本不向执行R传X |
| 4 固定seed、团队/个体/失败与新伙伴 | 07原24runs保留；08六seed/六协议、完整checkpoint/跨seed/固定表测试及单列适应 |
| 5 通信或信用反例/实际学习 | 08离散m确实由actor采样学习，已知BSC介入；中央旧表反事实baseline，消息不可辨/无码上界/方差反例，不能把起名或转发当学习 |
| 6 同任务只改对手/版本 | 07原q变化完整；08冻结R后S版本400步改变且评价口径独立 |
| 7 两真状态同历史与泄漏 | 08 decide(0,0)/decide(1,0)，相同局部历史强制同分布，非法X表得1被标泄漏；通信增加信息必须先声明时序 |
| 8 偏离、团队、未见与执行合法分开 | 07原检查保留；08按本地信息允许的4/2种映射枚举BR，弱Nash/团队改进反例与各冻结表结果 |

在本包与已实收07同版完整独核并正式发布后，可建议#167按原有限课程范围结项。一般深度MARL收敛、长期博弈所有任务族、现实信道/机器人/真人合作、原生Obsidian/同步不在此有限数据证据内；不能由“原scope闭合”宣布这些层已验。

若以后接实际通信设备，高重要性接口必须保留：双方设备/时钟与真实发送接收字段、丢失翻转/延迟日志、消息可见时序、独立信道校准样本、冻结partner版本、接收者能否窥视标签的检查，以及匹配/无码/新搭档对照。如果接真人，应另声明信息披露、同意、退出、奖励含义、随机配对和样本单位。这里没有运行这些任务，不以模拟成功替代它们，也不把它们加成原有限课关闭前的隐形门槛。

返回[[AI/13-搜索推理与规划/08-隐状态通信信用与集中训练#撤去步骤再迁移|六道迁移题]]；实际改变一个先验、观测或更新时点后，先改预期与失败判据，再重运行。
