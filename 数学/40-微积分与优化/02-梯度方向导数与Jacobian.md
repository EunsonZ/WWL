---
type: lesson
domain: mathematics
stage: 1
status: ready
difficulty: 高中起点
estimated_minutes: 55
topics:
  - gradient
  - directional-derivative
  - jacobian
tags:
  - mathematics/calculus
  - mathematics/linear-algebra
---

# 梯度、方向导数与 Jacobian

## 本课目标

- 知道梯度是“标量输出对向量输入”的导数，并与输入同形；
- 从方向导数证明梯度给出局部最陡上升方向；
- 正确写出 Jacobian 的行列含义与形状；
- 区分 JVP 和 VJP，理解训练为何偏爱 VJP。

## 直觉轨：同一座山，不同走法

地形高度 $f(x,y)$ 是标量。站在一点，向东、向北或斜着走，坡度不同。梯度

$$
\nabla f=
\begin{bmatrix}
\partial f/\partial x\\
\partial f/\partial y
\end{bmatrix}
$$

像一支箭：箭头指向局部上升最快方向，长度表示最快上升率。训练要减小损失，因此通常沿 $-\nabla L$ 走一小步。

“局部最快”有三个边界：只是一阶近似、只比较同样长度的微小步子、并不保证最终到全局最低点。

## 推导轨一：梯度与方向导数

设 $f:\mathbb{R}^{n}\to\mathbb{R}$，$x\in\mathbb{R}^{n}$ 是列向量。梯度定义为

$$
\nabla_x f=
\begin{bmatrix}
\partial f/\partial x_1\\
\vdots\\
\partial f/\partial x_n
\end{bmatrix}\in\mathbb{R}^{n}.
$$

沿单位方向 $u\in\mathbb{R}^{n}$、$\lVert u\rVert_2=1$ 的方向导数：

$$
D_u f(x)=\lim_{t\to0}\frac{f(x+tu)-f(x)}{t}
=\nabla f(x)^\mathsf{T}u.
$$

由 Cauchy–Schwarz 不等式，

$$
D_u f\le \lVert\nabla f\rVert_2\lVert u\rVert_2
=\lVert\nabla f\rVert_2.
$$

当 $\nabla f(x)\ne0$ 且 $u=\nabla f/\lVert\nabla f\rVert_2$ 时取等号，所以梯度方向是局部一阶意义下的最陡上升方向；最陡下降方向是其相反数。若 $\nabla f(x)=0$，所有单位方向的一阶方向导数都为 0，此时没有由一阶信息唯一指定的归一化最陡方向；该点称为一阶驻点，还需更高阶或其他信息判断局部形态。

例：$f(x,y)=x^2+2y^2$，在 $(1,-1)$：

$$
\nabla f=(2,-4)^\mathsf{T}.
$$

向 $u=(1,0)^\mathsf{T}$ 的方向导数是 2；向 $u=(0,1)^\mathsf{T}$ 是 $-4$；沿梯度单位方向的变化率最大，为 $\sqrt{20}$。

## 推导轨二：Jacobian

若 $f:\mathbb{R}^{n}\to\mathbb{R}^{m}$，输入 $x$ 有 $n$ 个分量，输出 $y=f(x)$ 有 $m$ 个分量。本单元采用“输出排在行、输入排在列”的约定：

$$
J_f(x)=\frac{\partial y}{\partial x}
=
\begin{bmatrix}
\partial y_1/\partial x_1 & \cdots & \partial y_1/\partial x_n\\
\vdots & \ddots & \vdots\\
\partial y_m/\partial x_1 & \cdots & \partial y_m/\partial x_n
\end{bmatrix}
\in\mathbb{R}^{m\times n}.
$$

标量输出 $m=1$ 时，Jacobian 是 $1\times n$ 行向量，而梯度按约定是 $n\times1$ 列向量：

$$
J_f=(\nabla f)^\mathsf{T}.
$$

教材若把导数排布反过来，公式会多或少一个转置；先核对定义与形状，不要只背符号。

## 线性层的完整形状

设

$$
x\in\mathbb{R}^{n},\quad
W\in\mathbb{R}^{m\times n},\quad
b\in\mathbb{R}^{m},\quad
y=Wx+b\in\mathbb{R}^{m}.
$$

因为 $y_i=\sum_j W_{ij}x_j+b_i$，所以

$$
\frac{\partial y_i}{\partial x_j}=W_{ij},
\qquad J_{y,x}=W\in\mathbb{R}^{m\times n}.
$$

若下游标量损失 $L$ 给出 $g_y=\nabla_yL\in\mathbb{R}^{m}$，则

$$
g_x=\nabla_xL=J_{y,x}^\mathsf{T}g_y=W^\mathsf{T}g_y\in\mathbb{R}^{n}.
$$

权重与偏置梯度是

$$
\nabla_WL=g_yx^\mathsf{T}\in\mathbb{R}^{m\times n},
\qquad
\nabla_bL=g_y\in\mathbb{R}^{m}.
$$

每个结果都与被求导对象同形，这是排错的第一道门。

## JVP 与 VJP

- **JVP**：$Jv\in\mathbb{R}^{m}$，问“输入沿方向 $v\in\mathbb{R}^{n}$ 变化时，所有输出怎样变”；对应前向模式自动微分。
- **VJP**：$u^\mathsf{T}J\in\mathbb{R}^{1\times n}$，问“输出的加权组合如何影响所有输入”；对应反向模式自动微分。

训练通常是“参数很多 $n\gg1$，最终损失只有一个 $m=1$”。一次 VJP 就能得到损失对全部参数的梯度，而逐参数做 JVP 代价很高。框架中的 `backward()` 本质上连续计算 VJP，通常不会构造完整 Jacobian。

把JVP/VJP放进 [[数学/35-微分几何/20-光滑流形/02-切向量余切与坐标变换#余切空间和拉回走对偶方向|切方向与余切拉回]]：一般映射F的矩形Jacobian A把方向送为Av，对偶读数拉为Aᵀb，不要求A可逆。该课再用同一y=2x、f=x²核df分量2→1与方向3→6、配对6；固定dx²时g_y=1/4、梯度分量2→4。回 [[AI/10-机器学习与深度学习基础/04-计算图与自动微分#预览：反向传播输出什么|自动微分原代码]] 时，本页固定Euclid坐标的偏导数组与梯度公式保留；换图后的余切读数只有经过指定度量才成为同一几何梯度。

## 广播与批次的边界

若批次 $X\in\mathbb{R}^{B\times n}$，线性层输出 $Y=XW^\mathsf{T}+b\in\mathbb{R}^{B\times m}$。偏置 $b$ 被广播给 $B$ 个样本，反向时其梯度必须沿批次维求和：

$$
\nabla_b L=\sum_{k=1}^{B}\nabla_{Y_k}L.
$$

广播在前向复制影响，在反向汇总贡献。忘记求和是手写反向传播的常见错误。

## 与微型 Transformer、训练和 CUDA 的连接

注意力里的 $Q=XW_Q$、$K=XW_K$、$V=XW_V$ 都遵循线性层的 Jacobian 规则。反向过程可分解为矩阵乘法、归约和逐元素 VJP；CUDA 擅长并行这些操作，但布局、归约次序和浮点精度会影响数值误差，而不会改变这里的数学形状契约。

## 练习与成功标准

设 $f(x_1,x_2)=(x_1+2x_2,\ x_1x_2)^\mathsf{T}$。

1. 写出 $J_f(x)\in\mathbb{R}^{2\times2}$。
2. 在 $x=(3,4)^\mathsf{T}$ 计算方向 $v=(1,0)^\mathsf{T}$ 的 JVP。
3. 令下游梯度 $u=(2,-1)^\mathsf{T}$，计算 $J_f^\mathsf{T}u$。

**成功标准**：得到

$$
J_f=\begin{bmatrix}1&2\\x_2&x_1\end{bmatrix},\quad
Jv=(1,4)^\mathsf{T},\quad
J^\mathsf{T}u=(-2,1)^\mathsf{T},
$$

并能逐项说清结果的形状和含义。

上一站：[[数学/40-微积分与优化/01-导数偏导数与链式法则|导数、偏导与链式法则]] · 下一站：[[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]] · 返回：[[数学/40-微积分与优化/00-微积分与优化-MOC|微积分与优化 MOC]]

## 定理条件补充：方向导数和 Jacobian 的对象

等式 $D_u f(x)=\nabla f(x)^{\mathsf T}u$ 对全可微标量函数成立；只有坐标偏导存在不保证任意方向都服从同一个线性模型。采用 $f:\mathbb R^n\to\mathbb R^m$、$J_f\in\mathbb R^{m\times n}$、向量为列向量的约定时，JVP $J_fv$ 是 $m\times1$；VJP 的行写法 $u^{\mathsf T}J_f$ 是 $1\times n$，其转置 $J_f^{\mathsf T}u$ 才是 $n\times1$。反向传播通常储存后者。二者数值对应但形状不同。

[[数学/15-微积分/11-多元极限偏导与全微分|多元极限偏导与全微分]] 和 [[数学/16-数学分析/11-多元微分逆映射与隐函数定理|多元微分逆映射与隐函数定理]] 给出定义、反例和链式法则的证明。


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/15-微积分/11-多元极限偏导与全微分|多元极限偏导与全微分]]；[[数学/15-微积分/12-多元链式法则隐函数与约束优化|多元链式法则隐函数与约束优化]]；[[数学/20-线性代数与几何/17-矩阵范数条件数与数值稳定性|矩阵范数条件数与数值稳定性]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。
