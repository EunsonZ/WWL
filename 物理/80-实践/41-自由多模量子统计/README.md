---
title: 自由多模量子统计复算
aliases:
  - 四模式正则与巨正则实验
stage: 0
sources:
  - https://ocw.mit.edu/courses/8-333-statistical-mechanics-i-statistical-mechanics-of-particles-fall-2013/97bfdfb93240e2f48984629ad0c037de_MIT8_333F13_Lec23.pdf
prerequisites:
  - "[[物理/40-量子力学/19-自由多模Fock占据与量子统计]]"
---

# 自由多模量子统计复算

读者问题：严格固定两个相同粒子，与只固定平均数为 2 的储库准备，会不会产生同一个多体态？[[物理/40-量子力学/19-自由多模Fock占据与量子统计#固定 N：每个占据态一次，模式会相关|主解释]]给出对象与推导。此入口保留完整固定卡、标准库源码与同源概率图；数值只检验给定有限自由模型。

## 先写预测，再打开输出

记录三个预测：正则总数方差是否为零；GC 不同能量模式的协方差是否为零；GC 条件到恰好 $N$ 后是否恢复正则**每一个**占据态概率。再预测增加能隙、升温与增加粒子数怎样改变上层占据。不要以“均值相同”替代这些检查。

默认四模式为 $(L_\alpha,L_\beta,U_\alpha,U_\beta)$，两层各两个完整正交模式，能量 $(0,0,0.04,0.04)\,\mathrm{eV}$；内态标签的物理边界在主解释说明。温度 $334.8356149173282\,\mathrm K$ 使 $e^{-\Delta/(k_BT)}=1/4$。基准 boson/fermion 各一例，另有同温能隙加倍及目标 $N=3$ 的两对例。39 个温度样本为 50–1000 K，每个温度重新拟合 GC 化学势。

## 复算入口与输出

Python 3.10+，仅标准库，无安装步骤。在本实践目录执行，输出目录必须不存在：

```bash
python3 -B free_fock.py --inputs inputs.json --output /private/tmp/free-fock-reader-output
```

一次枚举小固定 $N$ 扇区、求 GC 有限根并卷积数分布；不枚举无限 boson Fock 空间。默认最大固定扇区 20 态。合法卡最大 $M=6,N=6$ 的 boson 扇区 462 态，最多 12 例、121 温度、总数展示上限 80。本次核算按单线程 60 秒预算；直接 Python 入口不自带超时，数值守卫负责执行时限。由已有守卫运行时可使用其实际入口：

```bash
python3 -B /private/tmp/numerical_guard.py --threads 1 --timeout 60 --lock-timeout 60 -- python3 -B free_fock.py --inputs inputs.json --output /private/tmp/free-fock-guarded-output
```

守卫属于所在环境的执行工具，不是本模型的依赖；缺失时直接入口仍可复建。JSON 错误、非法域或已有输出目录均由 CLI 简洁拒绝，退出码 2；拒绝覆盖已有目录是输入与产物保全条件。

| 文件 | 检查的问题与字段 |
|---|---|
| `canonical-states.csv` | 每行一合法占据元组；`occupations` 以分号分隔，顺序与卡 `labels` 一致；能量 eV、正则概率、GC 条件恰好 $N$ 概率。无额外排列因子。 |
| `mode-moments.csv` | 每例每系综完整 $M\times M$；零起始索引 `a,b`、均值 count、方差及协方差 count²。正则行和应为零；GC 非对角为零。 |
| `number-distribution.csv` | 正则固定数尖峰、GC 未重归一化原概率、GC 条件于总数不超过展示界的概率。后二者是不同对象。 |
| `sweep.csv` | 每例各温度与系综的总数均值、方差、上层总占据均值及 GC 化学势 eV；正则化学势为空，因为固定 $N$ 权重不含它。 |
| `results.json` | 原卡、$k_B$、完整正则概率与协方差、`logZ`/`Z`、GC `mu_eV`/`logXi`/根残差、数尾质量/一二矩/联合上界、未夹零残差、两种条件化的核对量。 |
| `number.svg` | 首个 boson/fermion 卡的总数分布。连接离散点仅为阅读，概率定义在整数处。 |
| `covariance.svg` | 同一对卡的正则/GC 协方差矩阵；数字与 `mode-moments.csv` 相同，各面板独立色深尺度。 |
| `thermal.svg` | 全部卡的温度变化；实线正则、虚线 GC，来自 `sweep.csv`。 |

图题随卡显示模式数、温度、粒子数或能谱。源码 [[物理/80-实践/41-自由多模量子统计/SOURCE|代码镜像]]由 `free_fock.py` 同步，复算以 `.py` 为真源。保存输出后把图与 CSV 同时比较，不能只凭外观核公式。

## 固定卡的合法域

顶层严格含 `units`、`cases`、`temperatures_K`、`number_cutoff`；未知键与重复键拒绝。`units` 为 `{"energy":"eV","temperature":"K"}`。`cases` 为 1–12 个对象，各严格含：

- `name`：唯一 ASCII 字母数字、下划线或连字符，长度 1–40。
- `statistics`：`boson` 或 `fermion`。
- `energies_eV`：2–6 个有限能量，0–2 eV；允许重复与非排序，模式索引按输入顺序。
- `labels`：同数量的唯一非空文字标签，长度不超过 24，不含控制字符。
- `upper_modes`：非空真子集的零起始模式索引；它定义要观察的总占据，不自动判断能量排序。
- `N`：整数 1–6。此成对比较入口对 fermion 另要求 $N<M$，因为端点无有限 GC 化学势根；正则端点仍是合法物理态。
- `temperature_K`：10–2000 K 的有限值。

`temperatures_K` 为 2–121 个严格递增、同温度域的点；`number_cutoff` 为整数，至少所有卡最大 $N$，至多 80。数值、布尔值与非有限值不会混用。改变卡后另选一个新输出目录。

## 数值稳定与对象边界

正则概率用该固定 $N$ 扇区最低能量作平移：$e^{-\beta(E-E_0)}$ 归一化，再恢复 $\log Z=\log\sum e^{-\beta(E-E_0)}-\beta E_0$。整体加能量不会使概率失去定义。合法极低温大正能量时 `Z` 浮点下溢为 0 可能发生；应读 `logZ`，不能把下溢解释为没有态。

FD 根不直接依赖浮点的 $\sum m_a-N$：在低温能隙内该差可能整段舍入成零。将能量排序，比较最低 $N$ 模式的空穴数与其余模式的粒子数，以 `logsumexp` 计算两边，仍能定位唯一数学根。所有占据均用避免指数溢出的分支计算。输出 `root_residual` 是均值一致性检查，单独为零不能认证根位置；例如 $(0,0,2,2)\,\mathrm{eV},N=2,T=10\,\mathrm K$ 必须由谱对称得到 $\mu=1\,\mathrm{eV}$。

boson 全域 GC 一二阶矩为解析值，数分布展示到总数 $C$。`tail_mass`、`tail_first_N`、`tail_second_N` 是解析总矩减保留矩；`tail_bounds` 是主解释的联合界。机器端点上，负残差在相应尺度 $10^{-11}$ 内夹零，原值另在 `raw_tail_residuals` 保留；更大的负残差拒绝。boson 的显示零不能据此称数学尾恰好为零。条件方差因同类浮点舍入的微小负端点以 `max(0,cv)` 显示；解析定义仍是 $R_2/W-(R_1/W)^2$。fermion 枚举完整总数支撑 $0\ldots M$，解析尾严格为零，不以卡的 Bose 展示界砍掉 fermion 态。

重归一化展示为 $P(S=s\mid S\le C)$，不再是未截断 GC。`gc_given_N_probabilities` 则是 $P(\mathbf n\mid S=N)$，必须与正则逐态核对；两种条件化不能互换。

## 三图各回答一个问题

![[物理/80-实践/41-自由多模量子统计/assets/number.svg]]

总数图显示“相同平均数”留下的涨落差异，也显示截断条件化曲线接近原曲线不等于尾矩为零。

![[物理/80-实践/41-自由多模量子统计/assets/covariance.svg]]

协方差图显示固定总数能在自由模型中造成跨模相关。GC 的对角矩阵来自能量模式独立；图不是纠缠判据。

![[物理/80-实践/41-自由多模量子统计/assets/thermal.svg]]

温度图检验同谱热权重与重新求 $\mu$ 的迁移；它展示有限模型，不能认证材料谱、热化动力学、相变或热力学极限 Bose 凝聚。

先完成 [[物理/40-量子力学/19-自由多模Fock占据与量子统计#改变条件，检验哪条解释能迁移|主解释的迁移题]]，再核 [[物理/80-实践/41-自由多模量子统计/ANSWERS|答案]]。实际客户端、硬件热库、真实粒子样品与真人理解均需各自证据；这里的复算接口只涵盖固定模型与数据图。
