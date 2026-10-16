---
type: lab
domain: signals-systems
stage: 3
aliases:
  - 连续Haar积分系数与消失矩实验
sources:
  - "[[信号与系统/20-数字信号处理/06-多分辨率分析尺度空间与小波基]]"
prerequisites:
  - "[[信号与系统/80-实践/13-Haar分析合成与边界/README]]"
---
# 连续Haar：积分系数怎样接到已经存在的离散代码

主解释在[[信号与系统/20-数字信号处理/06-多分辨率分析尺度空间与小波基|MRA、稠密性与小波基]]。本实验只核有限可计算模型：分段多项式的解析格积分、投影残差、连续系数与旧Haar实现的接口，以及有限滤波矩和边界响应。全 $L^2$ 的稠密/交集、非零函数存在和基完备性由正文证明；44行输出不充当这些定理的模拟证明。

## 输入对象与复用接口

坐标 $\tau$ 无量纲，函数在所列半开区间上取系数从0次到2次的多项式，在所有区间外为0。JSON `segments` 逐项为 `[left,right,[a0,a1,a2]]`，允许常数或一次式省去高次零项；区间有序不重叠，可有空隙。端点单点值不影响积分。

固定输入 [fixed-inputs.json](fixed-inputs.json) 有四条函数：

| 名称 | 声明函数 | 独立的整体平方范数 |
| --- | --- | --- |
| `ramp` | $\tau1_{[0,1)}$ | $1/3$ |
| `edge` | $1_{[3/8,1)}$ | $5/8$ |
| `four_cells` | 四个四分之一格高度 $1,3,2,6$ | $50/4=12.5$ |
| `two_sides` | $1_{[-1,0)}-1_{[0,1)}$ | 2 |

投影尺度 `levels=[-4,-3,-2,-1,0,1,2,3,4,5,6]`，共44行；`finest_level=6`。细系数在固定包围区间 $[-2,2)$ 上由**积分**产生，连续归一为 $c_{J,k}=2^{J/2}\int f$，不从单点样值猜系数。该细块长 $4\cdot2^J$，每一级都是偶长；本实验不发明新的奇长多级边界合同。既有lab13的zero/repeat奇长解释继续有效，本包没有重跑其218 basis。

[mra_lab.py](mra_lab.py) 是新真源。它通过importlib调用已发布的 [lab13分析合成](../13-Haar分析合成与边界/filterbank_lab.py)，并让它继续调用 [原重采样完整卷积](../02-流式音频重采样/resample_lab.py)。两个旧源及其镜像均未修改，新源无活动code-sync镜像。实际运行复用的SHA：

- lab13：`03a5731f929b17641228708b7beb585e4c5481c3257c96e2ea8fb63483db5930`。
- resample：`773ef32198f5723e5ee7591990840efcdb30a3fbd42937d3fcf5f18d147839b1`。

Haar/db2/sparse的mask另以有限数组表示，内积定义为 $b[m]=\sum_ng_nx[2m+n]$。代码把 $g$ 反向后交给原 `offline` 完整卷积、分析phase1；长 $L$ 的偶tap结果从输出序号 $(L-2)/2$ 开始取完整支持内区间。完整零延拓输出也保存，不能把越过边缘的非零结果藏在裁剪外。db2在此只认证离散矩和有限输入输出，不计算或认证连续cascade极限、光滑阶或长边界PR。

## 重要性、独立预期与失败判据

| 重要性 | 具体断言与预期（不是调用被测函数作答案） | 容差及失败意义 |
| --- | --- | --- |
| 高 | 归一化与连续度量：四格 $c_2=(.5,1.5,1,3)$，范数平方12.5，层级账 $9+1+2.5$ | 默认解析比较绝对 $2\times10^{-13}$；把原点值或50直接代入即失败 |
| 高 | ramp的误差平方为 $1/(12\,4^j)$（$j\ge0$）；edge在 $j=0,1,2$ 为 $15/64,3/32,1/16$，$j\ge3$ 为0 | 由区间积分/方差直接推导；默认绝对 $2\times10^{-13}$，有系统偏差则积分、平均或归一错误 |
| 高 | `two_sides`的粗投影平方范数 $2^{j+1}$（$j\le0$），不会跨0相消成一个共同格平均 | 默认绝对 $2\times10^{-13}$；失败说明格索引或负轴处理错误 |
| 高 | 直接积分的每个 $c_j,d_j$ 应等于旧bank对 $c_{j+1}$ 的输出；逆合成还原细系数；层级能量等于 $\|P_Jf\|_2^2$ | 实现守卫 $2\times10^{-11}\max(1,\sqrt E)$，能量 $2\times10^{-11}\max(1,E)$；数值接口失败不能由全空间定理遮盖 |
| 高 | db2离散矩 $(0,0,-\sqrt{3/2})$，Haar的1阶矩 $-1/\sqrt2$；三mask偶移相关0位为1、非0偶位为0 | 默认矩绝对 $2\times10^{-13}$；检查实际有限tap代数，不由“名字叫db2”认证 |
| 高 | 多项式完整卷积的内区间，应等于独立 $\sum g_n(2m+n)^q$；边缘保留完整输出，不能套内区间消多项式 | 对本长度/幅值完整数组比较绝对 $2\times10^{-10}$；失败指向tap反向/抽取相位/slice |
| 高（理论） | Haar闭性、稠密、交集零、两端极限与ONB；lazy/refinement和sparseQMF反例 | 非作者核正文推导和primary承重段；不拿矩阵/有限曲线代一般证明 |
| 中 | 4条函数×11尺度以及变式卡，核当前解析实现对空隙、负轴、非对齐边缘与二次式的行为 | 有限确定性例检查接口；不泛化成所有JSON、所有浮点输入或所有长度的形式验证 |

不做装饰性参数扫描，不另加Monte Carlo。算子能量与系数关系是当前重要对象；此处没有噪声生成器，所以没有借增加采样点降低每样噪声来创造SNR。若将基恢复到有时间单位的形式，先按正文的 $T^{-1/2}$ 与积分测度变换单位，再谈物理能量。

本输入合同只允许1..8条函数、每条1..16段、区间在 $[-2,2]$、多项式次数不高于2、原系数绝对不超过10000；尺度在[-6,8]且最多13个不重复整数，细尺度在[1,8]；滤波输入偶长8..64、次数固定为整数 `[0,1,2]`。bool不当作数值或次数。预算约束属于实验接口，不是小波理论的定义域。内部变换系数不再套原系数幅值预算。输出目录必须尚不存在；先验输入/源错误退出2，不能拿空结果目录当运行成功。

## 环境与实际命令

本次用既有 `.venv`，Python3.14.7、NumPy2.5.3、macOS27.0.1 arm64，没有安装依赖。[results.json](results/results.json)保存环境、原输入、两个实际旧源路径与SHA。全局共享runner提供2个flock槽，本包每次取一个槽、强制 `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`，未扩大并发；默认组耗时约0.016s，限时180s，远小于5分钟预算。

以下是当时在本实验候选目录执行的真命令；主库仅作为读取旧源和解释器的位置：

```bash
WWL_HAAR_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/13-Haar分析合成与边界/filterbank_lab.py' WWL_RESAMPLE_SOURCE='/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/02-流式音频重采样/resample_lab.py' /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-context/run_local.py --timeout 60 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest -v test_mra_lab.py > author-tests.txt 2>&1
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B /private/tmp/wwl-next-context/run_local.py --timeout 180 -- /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B mra_lab.py --inputs fixed-inputs.json --haar-source '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/13-Haar分析合成与边界/filterbank_lab.py' --resample-source '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/信号与系统/80-实践/02-流式音频重采样/resample_lab.py' --output results > author-run.txt 2>&1
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B plot_mra.py --results results/results.json --output results
```

独核发现 `[False,True,2] == [0,1,2]` 会绕过初始次数值比较后，作者加逐项 `type is int` 并在原输入回归中加入这张卡；复用第一条命令、只将日志改为 `author-tests-final.txt`，7项再次通过。该输入校验不改变当前固定输入的数值路线，默认44行**没有重复运行**。最初日志、最终日志和默认运行分别保留，避免把复用报成重跑。

发布后若在同一既有环境复现，可从本目录使用兄弟目录默认源：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B mra_lab.py --inputs fixed-inputs.json --output results-rebuilt
python -B plot_mra.py --results results-rebuilt/results.json --output results-rebuilt
```

`results-rebuilt`须是新目录。此直接命令不自动取得协调槽；同一多任务协作环境仍使用共享runner。换机先建立可用NumPy环境，不把本机已有依赖当成换机已验证。

## 实际结果与保存物

- [author-run.txt](author-run.txt)：4条函数、44行、约0.015956s。
- [author-tests.txt](author-tests.txt) 与 [author-tests-final.txt](author-tests-final.txt)：初始/布尔次数修复后均7项通过。高幅合法函数、负轴和解析误差均覆盖。
- [results.json](results/results.json)：全部cell积分系数/格高度/误差、4条连续→旧bank桥的每层c/d、3mask的tap/矩/完整边界输出/内区片，以及sparse连续box反例参数。
- [projections.csv](results/projections.csv)：44行整体投影账本；字段单位均按无量纲坐标的函数平方积分。
- [plot_mra.py](plot_mra.py) 从保存JSON生成 [projections.svg](results/projections.svg) 和 [moments.svg](results/moments.svg)；绘图不重新运行数值、不增补额外模拟。

默认最大连续积分→旧bank系数差为 $1.7764\times10^{-15}$，最大逆合成差 $8.8818\times10^{-16}$，最大层级能量差 $1.4211\times10^{-14}$。ramp的 $j=6$ 误差平方约 $2.0345052083\times10^{-5}$，对应 $1/49152$。edge的零误差来自已对齐格结构，不是图上把小值压成0；图表直接写误差平方，不取对数、不加floor。

非作者审阅用独立Fraction分段积分、原始完整卷积与相位索引作答案，不import作者或旧source来当oracle：逐核默认44行全部cell/CSV、4桥与三mask全输出。另一张实际CLI卡含负轴二次式、非网格对齐edge和区间空隙，`J=3`、尺度[-6,-2,0,1,3,8]、滤波长12，共18行/3桥也通过。一般证明另读MIT具体段落与正文，有限数值通过不替代那些证明。最终两正式SVG已由非作者用CairoSVG渲染并实际查看：edge图包含[0,1]完整投影及断点两侧泄漏/原函数零基线，moments图同高box与重叠阴影清晰，无截断重叠；从保存JSON重生两SVG字节一致。23wiki目标/标题与15relative路径独核通过。单signal保存JSON子集实际绘图与XML通过，只认证该控制流，未作该子集像素观察。原生Obsidian仍未验证。

## 不从这个实验推出什么

本包不连接设备、不采集真人或传感器记录、不运行去噪/压缩，不认证连续db2/cascade或其他长小波的完备性/光滑性。若迁移到真实输入，至少保留时间/采样率与坐标T、样本/量化单位、通道与抗混叠前端、记录起点/长度、延拓/裁剪/相位、校准及缺样标记；若从样值近似积分，还须给采样/带宽假设或积分误差界。

外部验证应先对已知常值、斜坡、断点与已知幅值参考输入，检查完整输出区间、边缘系数和能量单位；改变采样率时不能只保持数组范数而丢掉 $\Delta t$。若实测系数与预测差异超过事先按量化、积分近似和测量噪声形成的容差，应先查参考面/单位/边界/时间标定，再讨论小波选择。这里没有得到任何硬件、实时deadline、原生Obsidian或真人理解结果。
