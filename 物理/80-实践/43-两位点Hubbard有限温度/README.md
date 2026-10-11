---
title: 两位点Hubbard有限温度复算
aliases:
  - Hubbard双位点复算
stage: 0
sources:
  - https://arxiv.org/pdf/1502.02194
  - https://arxiv.org/html/quant-ph/9605038
prerequisites:
  - "[[物理/40-量子力学/20-两位点Hubbard模型与相互作用多体态]]"
---

# 两位点Hubbard有限温度复算

同样平均每个位置一个粒子，排斥、跳跃与温度为何仍给不同双占据和自旋态？[[物理/40-量子力学/20-两位点Hubbard模型与相互作用多体态#四个完整模式，六个合法占据态|主解释]]先固定模式顺序与六维空间，再推 singlet 混合、精确谱与两种能量尺度。这组标准库程序复算整个 $N=2$ 正则态，不包含 GC 或长链。

## 先写预测再运行

先写四个预测：$U/t$ 增大时基态的双占据是否降低；固定正温时自旋是否一定越来越接近 singlet；$t$ 减半怎样同时改变 $D$ 和交换能隙；负自旋点积是否已证明纠缠。把两个制备都平均每个位置一个粒子当成区分依据，将漏掉这些问题。

输入固定模式顺序 `1_up,1_down,2_up,2_down`，固定总数2。六基顺序为 `D1,T_plus,A,B,T_minus,D2`，对应模式对 `(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)`。定义总双占据 $D=\sum_i n_{i\uparrow}n_{i\downarrow}$，每位点均值为 $D/2$；自旋点积字段是 $\langle\mathbf S_1\cdot\mathbf S_2\rangle/\hbar^2$。

默认六卡：$t=0.01\,\mathrm{eV},U=0,T=30\,\mathrm K$ 的自由对照；$U=0.04$ 在5与300 K；$U=0.20$ 在5与30 K；另一个 $t=0.005,U=0.04,T=5$ 的跳跃减半例。温度扫描101点 $1,7,\ldots,601\,\mathrm K$，每卡保持自己的 $t,U$；相互作用扫描81点 $U/t=0,0.5,\ldots,40$，每卡保持自己的 $t,T$。

## 复算入口与输出

Python 3.10+，只用标准库。在本实践目录执行，目标目录必须不存在且不能是符号链接：

```bash
python3 -B hubbard_dimer.py --inputs inputs.json --output /private/tmp/hubbard-dimer-reader-output
```

每点只计算六维矩阵，不需要 GPU、数值依赖或安装步骤。本次核算按单线程60秒预算，直接 Python 入口不自带超时。环境已有统一数值守卫时，可用其实际 CLI 限时运行：

```bash
python3 -B /private/tmp/numerical_guard.py --threads 1 --timeout 60 --lock-timeout 60 -- python3 -B hubbard_dimer.py --inputs inputs.json --output /private/tmp/hubbard-dimer-guarded-output
```

守卫是环境执行工具，缺失不使标准库入口失去可复算性。已有输出、非法卡或非有限数值均简洁拒绝，退出码2；已有目录内容保全。

| 文件 | 内容与检查目的 |
|---|---|
| `spectrum.csv` | 每卡六个**各态**的能量 eV、热概率、双占据、自旋点积和六系数列向量；向量以分号分隔。三个 triplet 各占一行，不把权重误乘或漏乘三。 |
| `matrices.csv` | 同卡完整 $H,\rho,D,\mathbf s_1\cdot\mathbf s_2$ 的 $6\times6$，一体 $\gamma$ 的 $4\times4$；零起始行列 `a,b`，`dimension` 声明 shape，`H_eV` 字段含能量单位，其余无量纲。 |
| `thermal.csv` | 每卡温度变化的完整观测：平均能量、总/每点双占据、点积、位置数均值/方差/连通相关、纯度、单占据后选择成功率、条件 singlet 概率与 PPT/negativity。 |
| `interaction.csv` | 每卡固定 $t,T$ 改 $U/t$；精确四类能量/$t$、交换隙、$J_2$ 误差、基态 $D$/自旋/自然 bonding 占据及热观测。$U=0$ 的 $J_2$ 字段为空，不使用发散近似。 |
| `results.json` | 原卡、$k_B$、六基、每卡全部矩阵/向量/权重/`logZ`/观测、局部四态约化对角及谱残差；不是独立正确性认证。 |
| `spectrum.svg` | 第一卡跳跃尺度下的完整能谱与精确交换隙；近似 $4t^2/U$ 只从 $U/t\ge2$ 展示，其受控区域仍需更大 $U/t$。 |
| `correlation.svg` | 相互作用扫描的基态及热双占据、自旋；数据均来自 `interaction.csv`。电荷连通相关恒为 $-D$，无需再画同一曲线。 |
| `thermal.svg` | 温度变化的 $D$ 与**投影保留每点一个粒子后的** singlet 概率；$p_S=1/2$ 是该二自旋条件态的门槛，不能外推到未条件化完整态。 |

每卡图例分两行给案例名和参数，颜色与线型共同区分；最长合法名称也保留全文。图源在 `.py`，源码镜像 [[物理/80-实践/43-两位点Hubbard有限温度/SOURCE|SOURCE]] 保持同字节；以 `.py` 为真源。

## 输入域和派生扫描的区别

顶层严格含 `units`、`particle_number`、`mode_order`、`cases`、`temperatures_K`、`interaction_ratios`；未知键、重复 JSON 键拒绝。单位严格 `{"energy":"eV","temperature":"K"}`，`particle_number` 必须整数2，模式列表必须与上面完全相同，不能改变顺序却仍用旧向量。

每卡严格含 `name,t_eV,U_eV,temperature_K`；案例数1–12，`name` 为唯一 ASCII 字母数字、下划线或连字符，长度1–40。单卡 $10^{-5}\le t\le1\,\mathrm{eV}$、$0\le U\le2\,\mathrm{eV}$、$0.1\le T\le2000\,\mathrm K$。布尔值不当数值，NaN/Infinity拒绝。$t=0$ 为主解释的退化边界，直接卡拒绝；负 $U$、偏置、磁场、其他粒子数均不在入口模型。

`temperatures_K` 为2–121个严格递增同温度域数；`interaction_ratios` 为2–161个严格递增、0–80的无量纲数。相互作用扫描的**派生** $U=t\times\mathrm{ratio}$ 可以到80 eV，不受单卡 $U\le2$ 的输入范围限制；这只扩展同一个有限 Hamiltonian 的扫描，不能解释为真实样品参数。改变卡后选另一个新目录。

## 两条可核计算路线

源码按 CAR 占据作用生成六维 $H,D,n_i$ 与局域自旋；自旋横向项由 $s_1^+s_2^-+s_1^-s_2^+$ 构造。然后用主解释的精确 singlet–double $2\times2$ 谱与三个 triplet 做谱投影 $\rho=\sum w|v\rangle\langle v|$。基态能量和双占据使用避免 $U-R$ 相消的等价式；热权重以最低能量平移，保存 `logZ`，不计算可能溢出的裸 $Z$。

独立核对可另在完整16维 Fock 空间用 Jordan–Wigner 张量生成 $c_a$，取 $N=2$ 后直接对角化或矩阵指数，再用迹计算观测。自由 $U=0$ 还可枚举四单粒子能量 $(-t,-t,t,t)$ 的六个两轨道填充态。不要调用作者的 `spectrum()` 作为独立 oracle。输出的谱残差与解析一致性只自查，不能替代不同路线。

机器端点的负零、$10^{-15}$ 附近概率或根号舍入按有限精度解释；JSON 保留实际矩阵与观测。`conditioned_negativity=max(0,-PPT_min)` 是该二自旋态的定义，不是把未条件化 full-state 的任意负数裁成纠缠值。总数方差字段解析为0；位置数仍可涨落。

## 图与失效边界

![[物理/80-实践/43-两位点Hubbard有限温度/assets/spectrum.svg]]

完整六谱和低能交换不是同一个对象。$U/t=4$ 的近似相对能隙误差约20.71%；忽略高能状态不能只依据“排斥看起来很大”。

![[物理/80-实践/43-两位点Hubbard有限温度/assets/correlation.svg]]

固定温度继续增大 $U$，双占据下降，而交换隙也下降；电荷稳定不能保证热自旋锁定。黑色点线为零温基态，不把它当所有热卡的结果。

![[物理/80-实践/43-两位点Hubbard有限温度/assets/thermal.svg]]

升温的双占据不必单调：triplet 不含双占据，可先减少 $D$；高能双占据态随后参与。右图只讨论有明确投影条件的两个局域自旋；真实数读出、自旋测量和操作限制需要另外验证。

固定正温的 $t\to0$ 极限为 $Z=4+2e^{-\beta U}$，保留热双占据；只有低温再取极限，才为四个单占据态等权。本双位点没有热力学相变，不能认证 Mott 长程行为、真实材料谱、一般强关联算法或制备动力学。Obsidian 客户端与真人理解亦不由 CSV/SVG 正确代替。

先完成 [[物理/40-量子力学/20-两位点Hubbard模型与相互作用多体态#先预测再复算，随后改变 U、跳跃与温度|迁移题]]，再核 [[物理/80-实践/43-两位点Hubbard有限温度/ANSWERS|检查答案]]。
