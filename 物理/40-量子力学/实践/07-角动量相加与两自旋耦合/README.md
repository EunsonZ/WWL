---
type: practice
domain: physics
stage: 2
aliases:
  - 角动量相加与两自旋耦合复算
sources:
  - https://ocw.mit.edu/courses/8-05-quantum-physics-ii-fall-2013/f27e44d7b761cec0ef1d01734f0a23b8_MIT8_05F13_Chap_10.pdf
  - https://www.preskill.caltech.edu/ph219/chap2_15.pdf
prerequisites:
  - "[[物理/40-量子力学/14-角动量相加与两自旋耦合]]"
---
# 角动量相加与两自旋耦合复算

先在 [[物理/40-量子力学/14-角动量相加与两自旋耦合#双自旋从最高态降到三重态，再补单态|正文的最高权构造]] 预测耦合基，再检查 [couple_spins.py](couple_spins.py) 从 Pauli 张量积生成的矩阵。不要把两段都背后的同一张 CG 表当成两次独立计算。本实践针对可分别寻址的 A、B 自旋 $1/2$，空间 $\mathbb C^2\otimes\mathbb C^2$，基顺序固定 `00,01,10,11`（索引 `2*i+j`）。不改实践05的两体/接触散射源码或历史输出。

## 固定输入和先验预测

[inputs.json](inputs.json) 给精确 SI 定义常数 $h=6.62607015\times10^{-34}$ J·s、教学交换频率 $J_c/h=10^6$ Hz、五个检查点 $\theta/\pi=0,1/2,1,3/2,2$ 与240个图间隔。$\hbar=h/(2\pi)$，$J_c=6.62607015\times10^{-28}$ J，$\theta=J_ct/\hbar=2\pi(J_c/h)t$。有限矩阵内部使用 $S/\hbar$、$J/\hbar$ 和 $K=\mathbf S_A\cdot\mathbf S_B/\hbar^2$；能量和时间另以 J、s 报告。复数在 JSON 按 `[real,imag]` 编码，不按两个真实维度解释。

先用笔算给以下答案，然后看生成的 [checks.json](assets/checks.json)：

- 降算符从 `00` 构造 $(01+10)/\sqrt2$ 和 `11`，正交态 $(01-10)/\sqrt2$ 被 $J_\pm$ 消灭。耦合序为 `t+,t0,t-,s`，$J^2/\hbar^2$ 为 `2,2,2,0`，$J_z/\hbar$ 为 `1,0,-1,0`，交换本征值为 `+1,+1,+1,-1`。
- Pauli 积给 $K$ 的中间块 $\left(\begin{smallmatrix}-1&2\\2&-1\end{smallmatrix}\right)/4$。完整谱为 $-3/4,1/4,1/4,1/4$；四态的能量依耦合顺序为 $J_c/4,J_c/4,J_c/4,-3J_c/4$，即 $1.6565175375\times10^{-28}$ J（三重）和 $-4.9695526125\times10^{-28}$ J。
- 初态 `01`、$\theta=\pi/2$ 时，去掉统一相位的态为 $(01-i10)/\sqrt2$，局部态 $I_2/2$、纯度1/2、$\langle X_A Y_B\rangle=+1$；$\theta=\pi$ 时带完整相位的态为 $e^{-i\pi/4}|10\rangle$，时间 $0.5\ \mu$s。总 j 的两个结果概率始终各半。
- 改为 $|+x\rangle_A|0\rangle_B$，$\theta=\pi/2$ 时 $\rho_A=\left(\begin{smallmatrix}3&1-i\\1+i&1\end{smallmatrix}\right)/4$，$p_{x+}=p_{z+}=p_{y+}=3/4$，局部纯度 $7/8$，总 triplet/singlet 概率为 $3/4,1/4$。$\theta=\pi$ 时 A 是 `0`，$p_{z+}=1,p_{x+}=p_{y+}=1/2$。
- 经典混态 $(|01\rangle\langle01|+|10\rangle\langle10|)/2$ 与 H 对易，整份混态恒定，局部态始终 $I/2$、$\langle X_A Y_B\rangle=0$。不能把它与同总 j 概率的纯 `01` 互换。
- 在同一正时间 $0.25\ \mu$s 翻耦合符号，相当于 $\theta=-\pi/2$：`01` 的人口/局部纯度不变，$\langle X_A Y_B\rangle=-1$；新制备的 $p_{y+}=1/4$，x+、z+ 仍为3/4。JSON 的 `sign_reversal_at_positive_time` 单独标明正时间和负耦合。

## 运行及输出位置

脚本只用 Python 标准库、单线程，最大矩阵 $4\times4$，不需要安装或 GPU。作者首次小规模预跑及完整默认运行均约0.04秒；当前冻结输出对应默认固定输入。程序每次覆写自己源码旁的 `assets/checks.json`、`exchange.csv` 和两张 SVG，不依赖当前工作目录。因此检验冻结候选时先复制本目录到自己的临时位置再运行。

候选作者运行的实际命令是：

```sh
python3 '/private/tmp/wwl-stage-spin-20261012/物理/40-量子力学/实践/07-角动量相加与两自旋耦合/couple_spins.py'
```

整合后从包含 `物理/` 的 vault 根运行：

```sh
python3 '物理/40-量子力学/实践/07-角动量相加与两自旋耦合/couple_spins.py'
```

数值计算用双精度复浮点，没有时间步进。检查点的矩阵指数另外使用缩放平方与 Taylor 求和，缩放后矩阵无穷范数不超过1，每项小于 $10^{-17}$ 后停，最多80项；不收敛时直接报错。默认 $0\le\theta\le2\pi$ 以及符号翻转点的指数与谱投影形式比较。Taylor截断误差、浮点舍入与物理模型误差分别是不同对象，当前小矩阵残差不能推广到无限谱或任意长时间数值稳定性。

## 哪些链真正交叉检查

从 `σ_i/2` 的 Kronecker 积构造局部与总算子，验证单自旋 Casimir、总角动量对易关系、$K=(J^2/\hbar^2-3I/2)/2$、显式 K 矩阵、$\mathsf P=2K+I/2$ 以及 H 自伴/总角动量守恒。Q 的三重态列由降算符生成，单态列用正交组合补齐；检查 Q 酉性、投影完备、每列的 $J^2,J_z,K,\mathsf P$ 本征关系和单态升降消灭。独立实对称 Jacobi 对角化只接受 K 矩阵，未输入耦合列向量，复算其有重数的谱。

演化第一条计算用 $U=e^{-i\theta/4}P_t+e^{3i\theta/4}P_s$；检查点另以直接矩阵指数复核。对两制备都从联合列向量形成 $4\times4$ 密度矩阵，再用 $\sum_j\rho_{ij,kj}$ 得 $2\times2$ 的 $\rho_A$；x/y/z 出口通过矩阵投影的 Born 规则计算。它们与正文解析式、纯度及总 j 概率对比。统一相位 $e^{0.37i}$ 单独检查密度矩阵不变；混态以 $U\rho U^\dagger$ 演化检查不变性与联合 $X_A Y_B$。无量纲容差为 $2\times10^{-12}$；当前作者输出最大残差 $1.3322676295501878\times10^{-15}$。残差分组记录为同类检查在所有实际采样点的最大值，图采样不是新独立实验。

[exchange.csv](assets/exchange.csv) 有241行，记录 $\theta$（rad）、$t$（s）、两制备的联合/局部概率、`XY_01`、总 j 概率和约化纯度。[exchange.svg](assets/exchange.svg) 直接消费同一行数据；[coupled-spectrum.svg](assets/coupled-spectrum.svg) 直接使用已构造耦合态对 K 的期望值和标签。SVG含 `title/desc`，坐标/图例显式给条件；没有外部字体、网络资源或图片依赖。

## 改条件时重新预测什么

保持正耦合，改 `exchange_frequency_Hz` 会把达到相同 $\theta$ 的时间按反比缩放；以固定 $\theta$ 作图时概率曲线不变。若要比较固定物理时间，应先重新算 $\theta=2\pi f t$，不能拿旧横轴充当新时间预测。正文的负耦合例已在正时间单独核过；默认图保持正频率标尺。改变制备则须改联合向量、解析对照与图注，不能只改标题后复用旧 CSV。一般 j 的加法、外场、各向异性、时间变化耦合和环境不在此脚本中。

**撤提示。** 固定 $t=0.25\ \mu$s，把正 $J_c$ 翻倍，同时将制备改成 $|+x\rangle_A|0\rangle_B$。只测 A 的 z+，能否认定总 j 已成为1？

> [!question]- 解释性答案
> 新 $\theta=\pi$，A 的 z+ 概率为1，但总 triplet/singlet 概率仍为 $3/4,1/4$。局部纯态并不把联合总 j 变成确定值；此时全态是 `0` 与 `+x` 的乘积，总 j 仍须联合测量。可按正文直接投影重算，不必先运行脚本。

本次有作者实际源码计算和生成资产；重要公式/相位仍需非作者独立核查，真实 Obsidian 显示与真人撤提示效果未由程序认证。输出是四维有效模型预测，没有物理量子硬件、材料交换参数拟合、相同电子空间波函数、量子层析或真实交换实验数据。回到 [[物理/40-量子力学/14-角动量相加与两自旋耦合#可寻址自旋、粒子标签与完整交换约束|适用对象与交换约束]]，再返回 [[物理/40-量子力学/00-量子力学-MOC#全课仍要完成的六阶段|全课未完成范围]]。
