---
type: lesson
domain: mathematics
stage: 1
status: ready
difficulty: 高中起点
estimated_minutes: 55
topics:
  - trigonometry
  - complex-number
  - rotation
  - rope
tags:
  - mathematics/linear-algebra
  - mathematics/geometry
  - mathematics/rope
---

# 三角函数、复数旋转与 RoPE

## 本课目标

- 从单位圆理解正弦、余弦与弧度；
- 用旋转矩阵和复数乘法描述二维旋转；
- 推导旋转保持长度、内积只依赖相对角度；
- 从二维分块旋转理解 RoPE 的相对位置性质与局限。

## 直觉轨：位置变成不同速度的钟表

单位圆上角度 $\theta$ 对应点 $(\cos\theta,\sin\theta)$。把二维向量旋转 $\theta$ 用矩阵表示：

$$
R(\theta)=
\begin{bmatrix}
\cos\theta&-\sin\theta\\
\sin\theta&\cos\theta
\end{bmatrix}.
$$

RoPE 把 query 和 key 的某个偶数维子空间两两配对。每一对像一根钟表指针，位置 $m$ 让它转过 $m\omega_j$；不同特征对使用不同频率 $\omega_j$。两位置的 Attention 点积因此自然包含位置差 $n-m$。若待处理维度是奇数，必须另外规定未配对坐标如何处理；不能从二维分块公式自动推出。

## 严谨轨一：三角函数与弧度

弧度定义为弧长除以半径，整圆为 $2\pi$。单位圆直接给出

$$
\cos^2\theta+\sin^2\theta=1.
$$

角和公式为

$$
\cos(\alpha+\beta)=\cos\alpha\cos\beta-\sin\alpha\sin\beta,
$$

$$
\sin(\alpha+\beta)=\sin\alpha\cos\beta+\cos\alpha\sin\beta.
$$

把两个旋转矩阵相乘并使用角和公式，可得

$$
R(\alpha)R(\beta)=R(\alpha+\beta),
\qquad
R(\theta)^\mathsf T=R(-\theta).
$$

同时 $R(\theta)^\mathsf TR(\theta)=I$，所以旋转保持点积、长度与角度。

## 严谨轨二：复数是二维旋转的简写

把 $(x,y)$ 对应复数 $z=x+iy$。Euler 公式

$$
e^{i\theta}=\cos\theta+i\sin\theta
$$

给出

$$
ze^{i\theta}
=(x\cos\theta-y\sin\theta)
+i(x\sin\theta+y\cos\theta),
$$

恰好等同于 $R(\theta)(x,y)^\mathsf T$。复数写法不是额外的神秘机制，只是把二维旋转的两条实数公式压缩成一条。

需要补 Euler 公式为何成立时，读 [[电子电路/05-数学与物理桥梁/03-欧拉公式旋转与正弦投影#由旋转规则建立复指数|由旋转微分方程建立复指数]]：带单位圆与旋转保持长度的性质，回来核对初值 $w(0)=1$ 和 $dw/d\theta=iw$ 如何给出同一对象的实部、虚部。这里对角度 $\theta$ 求导；链接中的虚数单位 $j$ 对应本页的 $i$，不是 RoPE 的特征块编号 $j$。若改对物理时间求导，还须带上角速度，成为 $dw/dt=i\omega w$。该处有导数推导和唯一性说明；后面的 RoPE 应用不充当 Euler 公式的证明。

物理时间也能作旋转参数。[[电子电路/12-交流与变换域/01-相量峰值有效值与波形回译#完整算例：两个同频电压怎样相加|同频电压的相量叠加]]采用 $\theta(t)=\omega t+\phi$，$\omega$ 用 rad/s、$t$ 用 s，复幅度带 V。本页的 $m\omega_j$ 是位置索引形成的特征旋转角；两者共享二维旋转代数，但物理时间、信号单位和 Attention 分数各有自己的模型。带两种角参数去比较，回来说明旋转恒等式本身既不保证长上下文可靠，也不保证电路在任意激励下处于正弦稳态。

## RoPE 的核心推导

设位置 $m,n$ 处、第 $j$ 个二维特征块的未旋转 query/key 为 $q_{m,j},k_{n,j}\in\mathbb R^2$。旋转后表示为

$$
\widetilde q_{m,j}=R(m\omega_j)q_{m,j},
\qquad
\widetilde k_{n,j}=R(n\omega_j)k_{n,j}.
$$

它们的点积为

$$
\begin{aligned}
\widetilde q_{m,j}^\mathsf T\widetilde k_{n,j}
&=q_{m,j}^\mathsf T R(m\omega_j)^\mathsf T R(n\omega_j)k_{n,j}\\
&=q_{m,j}^\mathsf T R((n-m)\omega_j)k_{n,j}.
\end{aligned}
$$

绝对位置 $m,n$ 通过旋转写入表示，旋转算子在点积中合成为相对位移 $n-m$。但分数仍依赖内容向量 $q_{m,j}$ 与 $k_{n,j}$；这条等式不是说 Attention score 只是 $n-m$ 的函数。完整隐藏维的 score 是所有二维块贡献之和。

### 四维数值例

令两个二维块频率为 $\omega_0=\pi/2$、$\omega_1=\pi/4$。同一个基础向量

$$
x=(1,0,\;1,0)
$$

在位置 $m=1$ 变为

$$
\widetilde x_1=(0,1,\;\tfrac{\sqrt2}{2},\tfrac{\sqrt2}{2}).
$$

第一块转 90°，第二块转 45°；频率不同使多个相对尺度同时可见。

## 与 Attention 和上下文长度的连接

RoPE 通常作用于 query/key，然后再做点积 Attention，因此 shape 不变，数值关系改变。频率选择、缩放方案、训练长度和推理长度共同影响长上下文外推；“公式能在任意位置计算”不等于模型在任意长度都可靠。工程与经验边界见 [[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|位置编码、RoPE 与上下文]]，Attention 主体见 [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]]。

在实现侧，二维对如何排布、旋转与缓存会影响访存和 kernel 融合；参见 [[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]。

## 常见误区

| 误区 | 更准确的说法 |
| --- | --- |
| “旋转会改变向量长度。” | 正交旋转保持二范数；浮点实现只会有舍入误差。 |
| “度数可直接放进常见数学库。” | 多数库的 `sin`/`cos` 接收弧度。 |
| “复数引入了不同于旋转矩阵的新几何。” | 在这里复数乘单位模复数与二维旋转完全等价。 |
| “RoPE 只使用相对位置。” | 单个表示用绝对位置旋转；query-key 点积呈现相对位移结构。 |
| “能计算超长位置就等于成功外推。” | 数值可计算不保证分布外行为、精度或任务效果。 |

## 练习

1. 用矩阵乘法验证 $R(\pi/2)(1,2)^\mathsf T=(-2,1)^\mathsf T$，并检查长度不变。
2. 证明 $R(a)^\mathsf TR(b)=R(b-a)$。
3. 若 $m=3,n=8,\omega=0.1$，RoPE 点积中的相对旋转角是多少？交换 query/key 位置后角度如何变化？
4. 两对 query/key 的位置差都是 5，它们的 RoPE Attention score 是否必然相同？写出决定答案的其他量。

> [!question]- 核对要点
> 1. $\cos(\pi/2)=0,\sin(\pi/2)=1$；旋转前后二范数都是 $\sqrt5$。
> 2. $R(a)^\mathsf T=R(-a)$，再用旋转复合律。
> 3. $(8-3)\times0.1=0.5$ 弧度；交换后为 $-0.5$ 弧度。
> 4. 不必然。位置差只决定相对旋转算子；未旋转内容向量 $q_{m,j}$、$k_{n,j}$ 和各块频率 $\omega_j$ 也进入分数。

## 成功标准

你能在旋转矩阵与复数表示之间互译，能推导 $R(m\omega)^\mathsf TR(n\omega)=R((n-m)\omega)$，并能说明这条恒等式对 RoPE 证明了什么、没有证明什么。

## 导航

- 上一站：[[数学/20-线性代数与几何/05-正交投影子空间与方向消除|正交投影、子空间与方向消除]]
- 返回：[[数学/20-线性代数与几何/00-线性代数与几何-MOC|线性代数与几何 MOC]]
- 实践：[[数学/20-线性代数与几何/80-低秩近似数值实验|低秩近似数值实验]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/20-线性代数与几何/10-线性映射核像与四个基本子空间|线性映射核像与四个基本子空间]]；[[数学/20-线性代数与几何/14-最小二乘伪逆与正则化|最小二乘伪逆与正则化]]；[[数学/20-线性代数与几何/16-SVD的推导最优低秩与PCA|SVD的推导最优低秩与PCA]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。
