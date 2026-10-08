---
type: lesson
domain: artificial-intelligence
content_status: draft
evidence_status: unreviewed
aliases:
- Gaussian条件化与Kalman递推
sources:
- https://ee363.stanford.edu/archive/lectures/estim.pdf
- https://ee363.stanford.edu/archive/lectures/kf.pdf
prerequisites:
- '[[AI/45-机器人与具身智能/02-Bayes滤波与Kalman状态估计]]'
- '[[数学/20-线性代数与几何/18-分块矩阵Schur补与矩阵指数]]'
---

# 从线性 Gaussian 条件化到 Kalman 递推

**读者问题：** 只看到有噪声的位置 $y_k$，为什么一个矩阵乘上“读数减预测”就能同时修正位置和速度？答案不是经验加权，而是联合 Gaussian 的精确条件分布。一般 Bayes 归一与滤波语义已在[[AI/45-机器人与具身智能/02-Bayes滤波与Kalman状态估计|基础课]]说明；此处补齐矩阵推导、shape、单位和三步复算。

## 一个分块 Gaussian 已包含更新式

设 $a\in\mathbb R^n$、$b\in\mathbb R^p$ 联合 Gaussian：

$$
\begin{gathered}
\begin{bmatrix}a\\b\end{bmatrix}
\sim\mathcal N\!\left(
\begin{bmatrix}\mu_a\\\mu_b\end{bmatrix},
\begin{bmatrix}\Sigma_{aa}&\Sigma_{ab}\\
\Sigma_{ba}&\Sigma_{bb}
\end{bmatrix}
\right),\\
\Sigma_{bb}\succ0.
\end{gathered}
$$

令 $K=\Sigma_{ab}\Sigma_{bb}^{-1}$，残差 $r=a-\mu_a-K(b-\mu_b)$ 满足 $\operatorname{Cov}(r,b)=0$。联合 Gaussian 下这推出 $r$ 与 $b$ 独立，因此直接得到（也覆盖退化的联合分布）

$$
\mathbb E[a\mid b]
=\mu_a+\Sigma_{ab}\Sigma_{bb}^{-1}(b-\mu_b),
$$

$$
\operatorname{Cov}(a\mid b)
=\Sigma_{aa}-\Sigma_{ab}\Sigma_{bb}^{-1}\Sigma_{ba}.
$$

若整个联合协方差还正定，才也可把联合密度的二次型对 $b$ 固定并配方，等价于对分块精度矩阵做消元；不能只由 $\Sigma_{bb}\succ0$ 推出整体精度矩阵存在。例如 $a=b\sim\mathcal N(0,1)$ 的联合协方差为 $\begin{bmatrix}1&1\\1&1\end{bmatrix}$，行列式为零，但观察 $b=2$ 时 $a\mid b=2$ 是点质量 $\delta_2$，上述条件均值为 $2$、条件方差为 $0$。

程序求解 $\Sigma_{bb}K^\mathsf T=\Sigma_{ab}^\mathsf T$，避免显式形成逆矩阵。Gaussian 条件化与线性最小均方估计的课程推导可对照 [Stanford EE363 Estimation](https://ee363.stanford.edu/archive/lectures/estim.pdf)；下面的机器人参数和手算是本组教学构造。

## 把 $a=x_k$、$b=y_k$ 代入

测量前已有

$$
\begin{gathered}
x_k\mid\mathcal Y_{k-1}\sim\mathcal N(\hat x_k^-,P_k^-),\\
y_k=Hx_k+r_k,\\
r_k\sim\mathcal N(0,R),
\end{gathered}
$$

其中 $r_k$ 与 $x_k$ 条件独立。于是

$$
\begin{gathered}
\begin{bmatrix}x_k\\y_k\end{bmatrix}\Bigm|\mathcal Y_{k-1}
\sim\mathcal N(m_k,C_k),\\
m_k=\begin{bmatrix}\hat x_k^-\\H\hat x_k^-\end{bmatrix},\\
C_k=\begin{bmatrix}
P_k^-&P_k^-H^\mathsf T\\
HP_k^-&HP_k^-H^\mathsf T+R
\end{bmatrix}.
\end{gathered}
$$

定义创新、创新协方差和 Kalman 增益

$$
\begin{gathered}
\nu_k=y_k-H\hat x_k^-,\\
S_k=HP_k^-H^\mathsf T+R,\\
L_k=P_k^-H^\mathsf T S_k^{-1}.
\end{gathered}
$$

条件化公式直接给出

$$
\hat x_k=\hat x_k^-+L_k\nu_k,
$$

$$
\begin{aligned}
P_k={}&(I-L_kH)P_k^-(I-L_kH)^\mathsf T\\
&+L_kRL_k^\mathsf T.
\end{aligned}
$$

第二式是 Joseph 形式。展开并使用 $L_kS_k=P_k^-H^\mathsf T$，可化成 $P_k=P_k^--P_k^-H^\mathsf TS_k^{-1}HP_k^-$；Joseph 形式把舍入前的结果写成两个半正定项之和。对精确增益两式代数等价，Joseph 形式也不会修复错误的模型或错误的 $R$。

## shape 和单位逐项核对

本例 $x=[p,v]^\mathsf T\in\mathbb R^2$，$y\in\mathbb R$：

| 量 | shape | 各项单位 |
| --- | --- | --- |
| $P$ | $2\times2$ | $P_{pp}$ 为 m²，$P_{pv}$ 为 m²/s，$P_{vv}$ 为 m²/s² |
| $H=[1\ 0]$ | $1\times2$ | 把状态映射为位置读数 |
| $R$、$S$ | $1\times1$ | m² |
| $L$ | $2\times1$ | 第一行无量纲，第二行为 s⁻¹ |
| $\nu$ | $1$ | m |
| $L\nu$ | $2$ | 分别为 m、m/s |

所以速度增益大于 1 并不表示“相信传感器超过 100%”；它带有 s⁻¹ 单位，把位置创新转成速度修正。把增益矩阵全部解释成百分比会丢掉单位。

## 预测一步怎样产生速度信息

后验经过已知控制和独立过程噪声：

$$
\begin{gathered}
\hat x_{k+1}^-=A\hat x_k+Bu_k,\\
P_{k+1}^-=AP_kA^\mathsf T+W.
\end{gathered}
$$

取每段恒定加速度扰动 $\eta_k\sim\mathcal N(0,0.2^2)$ m/s²，$w_k=B\eta_k$，则

$$
\begin{aligned}
W&=0.2^2BB^\mathsf T\\
&=\begin{bmatrix}0.000016&0.00016\\0.00016&0.0016\end{bmatrix}.
\end{aligned}
$$

$W$ 是秩一半正定矩阵，因为同一个未知加速度同时改变下一步位置和速度；它不是“数值坏掉”。这一离散噪声模型也不能直接替换成连续白噪声积分的协方差。

## 三次位置读数，逐步手算

令

$$
\begin{gathered}
\hat x_0^-=\begin{bmatrix}0\\0\end{bmatrix},\\
P_0^-=\begin{bmatrix}0.04&0\\0&0.25\end{bmatrix},\\
R=0.01,
\end{gathered}
$$

$$
\begin{gathered}
(y_0,y_1,y_2)=(0.10,0.14,0.18)\ \mathrm m,\\
(u_0,u_1)=(0.5,-0.2)\ \mathrm{m/s^2}.
\end{gathered}
$$

在 $k=0$，$S_0=0.05$、$L_0=[0.8,0]^\mathsf T$，所以

$$
\begin{gathered}
\hat x_0=\begin{bmatrix}0.08\\0\end{bmatrix},\\
P_0=\begin{bmatrix}0.008&0\\0&0.25\end{bmatrix}.
\end{gathered}
$$

施加 $u_0=0.5$ 后，

$$
\begin{gathered}
\hat x_1^-=\begin{bmatrix}0.09\\0.10\end{bmatrix},\\
P_1^-=\begin{bmatrix}0.018016&0.05016\\0.05016&0.2516\end{bmatrix}.
\end{gathered}
$$

现在位置—速度交叉项不再为零。$y_1=0.14$ 给出

$$
\begin{gathered}
\nu_1=0.05,\\
S_1=0.028016,\\
L_1=\begin{bmatrix}0.64306111\\1.79040548\end{bmatrix},
\end{gathered}
$$

$$
\begin{gathered}
\hat x_1=\begin{bmatrix}0.12215306\\0.18952027\end{bmatrix},\\
P_1=\begin{bmatrix}
0.00643061&0.01790405\\
0.01790405&0.16179326
\end{bmatrix}.
\end{gathered}
$$

再施加 $u_1=-0.2$ 并用 $y_2=0.18$ 更新，得到

$$
\begin{gathered}
\nu_2=0.02394289,\\
L_2=\begin{bmatrix}0.66755279\\1.67628884\end{bmatrix},
\end{gathered}
$$

$$
\begin{gathered}
\hat x_2=\begin{bmatrix}0.17204025\\0.18965547\end{bmatrix},\\
P_2=\begin{bmatrix}
0.00667553&0.01676289\\
0.01676289&0.07887024
\end{bmatrix}.
\end{gathered}
$$

第二、三次位置创新都修正了速度，因为动力学在 $P^-$ 中建立了交叉协方差。

## 独立解析对照：一次性条件化整个历史

递推代码之外，实验把独立 Gaussian 向量

$$
\xi=(x_0,w_0,w_1,r_0,r_1,r_2)
$$

堆叠起来，把 $x_2$ 与 $Y=(y_0,y_1,y_2)$ 都写成 $\xi$ 的仿射函数，再直接用本页第一组条件化公式计算 $p(x_2\mid Y)$。它没有调用 Kalman 递推。结果为

$$
\mathbb E[x_2\mid Y]
=\begin{bmatrix}0.172040253035\\0.189655473049\end{bmatrix},
$$

$$
\begin{gathered}
\operatorname{Cov}(x_2\mid Y)\\
=\begin{bmatrix}
0.006675527875&0.016762888396\\
0.016762888396&0.078870239948
\end{bmatrix}.
\end{gathered}
$$

递推与一次性条件化的最大绝对差分别为 $2.78\times10^{-17}$ 和 $1.11\times10^{-16}$。这是同一概率模型的两条代数路径；固定浮点一致性没有证明模型符合真实传感器。

## 练习与完整答案

1. **为什么 $S_k$ 必须可解？** 若 $R\succ0$，则对任意非零 $q$，$q^\mathsf TS_kq=q^\mathsf THP^-H^\mathsf Tq+q^\mathsf TRq>0$，所以 $S_k\succ0$。
2. **若 $P^-_{pv}=0$，位置读数能立刻改速度吗？** 不能。此时 $L$ 的速度行是零；预测后 $AP A^\mathsf T$ 可建立交叉项，后续读数才会修正速度。
3. **把 $R$ 调小会怎样？** 在模型内增益通常增大、后验协方差缩小；若真实噪声并未变小，报告的协方差会过度自信，创新诊断会暴露失配。
4. **已施加输入为什么能直接进入均值预测？** 控制器知道实际发送并执行的 $u_k$，条件于历史时它是已知量，不贡献协方差。若执行器有未知饱和或迟滞，就应使用实际施加输入或把误差建模；继续使用命令值会形成模型偏差。

下一课：[[AI/45-机器人与具身智能/20-状态估计与LQG/02-可检测性稳态滤波与误差诊断|可检测性、稳态滤波与误差诊断]]。复算入口：[[AI/45-机器人与具身智能/20-状态估计与LQG/80-状态估计与LQG复现实验|实验]]。
