---
type: lesson
domain: mathematics
stage: 1
status: ready
difficulty: 高中起点
estimated_minutes: 45
topics:
  - matrix-multiplication
  - linear-map
  - einsum
  - attention
tags:
  - mathematics/linear-algebra
  - mathematics/einsum
---

# 矩阵乘法、线性映射与 Einsum

## 本课目标

- 从“行与列配对”和“线性映射复合”两种角度理解矩阵乘法；
- 用 shape 和下标求和检查计算；
- 把转置、批量乘法和 Attention score 写成 Einsum；
- 知道线性、仿射与逐元素乘法的区别。

## 直觉轨：输出的每格都来自一次配对

设

$$
A=\begin{bmatrix}1&2\\3&4\end{bmatrix},\qquad
x=\begin{bmatrix}5\\6\end{bmatrix}.
$$

第一行与 $x$ 配对得到 $1\cdot5+2\cdot6=17$，第二行得到 $3\cdot5+4\cdot6=39$，所以

$$
Ax=\begin{bmatrix}17\\39\end{bmatrix}.
$$

一个实用口诀是：**中间维必须相等，中间维被求和，外侧维被保留。**

$$
(m\times \boxed n)(\boxed n\times p)\longrightarrow(m\times p).
$$

## 严谨轨：线性映射的复合

若 $B:\mathbb R^p\to\mathbb R^n$，$A:\mathbb R^n\to\mathbb R^m$，先做 $B$ 再做 $A$ 的复合是 $AB:\mathbb R^p\to\mathbb R^m$。因此乘法顺序不能随意交换。

元素公式为

$$
(AB)_{ij}=\sum_{k=1}^{n}A_{ik}B_{kj}.
$$

这里 $k$ 重复出现并被求和，$i,j$ 保留在输出。矩阵乘法通常不交换：即使 $AB$ 与 $BA$ 都存在，也往往 $AB\ne BA$。

### 为什么线性

映射 $L$ 若满足

$$
L(\alpha x+\beta y)=\alpha L(x)+\beta L(y),
$$

就是线性映射。矩阵乘法 $L(x)=Ax$ 满足它。神经网络层 $Ax+b$ 在 $b\ne0$ 时严格说是仿射映射；激活函数再引入非线性。

## 从下标到 Einsum

Einstein 求和约定中，一个下标在同一乘积项中恰好出现两次时，通常沿该下标求和；自由下标则出现在结果中。工程 API `einsum` 的显式 `->` 形式更直接：**出现在输出中的标签被保留，不出现的标签被求和**。同一输入中重复标签还可表示取对角线，如 `ii->i`；所以不能把“看到重复字母”当成无条件求和规则。

| 运算 | 下标式 | Einsum 字符串 |
| --- | --- | --- |
| 点积 | $s=\sum_d x_dy_d$ | `d,d->` |
| 矩阵乘法 | $C_{ij}=\sum_k A_{ik}B_{kj}$ | `ik,kj->ij` |
| 批量线性层 | $Y_{bto}=\sum_d X_{btd}W_{do}$ | `btd,do->bto` |
| Attention score | $S_{bhts}=\sum_d Q_{bhtd}K_{bhsd}$ | `bhtd,bhsd->bhts` |

Einsum 字母只是轴标签，不是固定语义；重要的是按显式输出判断哪些轴被保留、哪些轴被求和。它表达了数学关系，但实际性能仍要由库的实现、布局和 kernel 决定。

## Attention 的 shape 推演

设 $Q,K\in\mathbb R^{B\times H\times T\times D_h}$。对每个 batch、head 和两个 token 位置做特征维点积：

$$
S_{bhts}=\frac{1}{\sqrt{D_h}}\sum_{d=1}^{D_h}Q_{bhtd}K_{bhsd}.
$$

所以 $S\in\mathbb R^{B\times H\times T\times T}$。缩放 $1/\sqrt{D_h}$ 不改变 shape，它用于控制点积的典型尺度。完整机制见 [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]]。

### 一个小型数值例

$$
Q=\begin{bmatrix}1&0\\1&1\end{bmatrix},\qquad
K=\begin{bmatrix}1&1\\0&1\end{bmatrix}.
$$

则

$$
QK^\mathsf T=
\begin{bmatrix}1&0\\2&1\end{bmatrix}.
$$

第 $(2,1)$ 格的 2 来自 query $(1,1)$ 与 key $(1,1)$ 的点积；行是 query 位置，列是 key 位置。

## 常见误区

| 误区 | 更准确的说法 |
| --- | --- |
| “$AB$ 就是对应元素相乘。” | 对应元素相乘是 Hadamard 乘积；$AB$ 会沿共享维求和。 |
| “能算 $AB$ 就一定能算 $BA$。” | 前者要求 $A$ 的列数等于 $B$ 的行数；后者是另一项条件。 |
| “$AB=BA$。” | 一般不成立；交换会改变复合顺序。 |
| “`einsum` 总是最快。” | 它首先是表达工具；真实性能要测量。 |
| “$Ax+b$ 是线性映射。” | $b\ne0$ 时是仿射映射，因为它通常不把零映到零。 |

## 练习

1. $A\in\mathbb R^{3\times4}$、$B\in\mathbb R^{4\times2}$：写出 $AB$ 的 shape 和元素公式。
2. 把 $Y_{btd}=\sum_s P_{bts}V_{bsd}$ 写成 Einsum 字符串，并解释 $s$ 轴发生了什么。
3. 若 $Q$ 的序列长度为 $T_q$，$K$ 的序列长度为 $T_k$，写出 $QK^\mathsf T$ 的最后两个维度。
4. 对 $A\in\mathbb R^{n\times n}$，区分 `ii->i` 与 `ii->`：它们分别保留和求和了什么？

> [!question]- 核对要点
> 1. $(3,2)$，$(AB)_{ij}=\sum_{k=1}^{4}A_{ik}B_{kj}$。
> 2. `bts,bsd->btd`；$s$ 是 key/value 位置轴，被加权求和。
> 3. $(T_q,T_k)$。
> 4. `ii->i` 取对角线并保留长度 $n$ 的轴；`ii->` 再对该对角线求和，得到标量迹 $\operatorname{tr}(A)$。

## 成功标准

看到一条矩阵或 Einsum 公式时，你能标出被求和轴、保留轴和输出 shape，并能解释矩阵乘法为什么对应线性映射复合。

## 导航

- 上一站：[[数学/20-线性代数与几何/01-向量矩阵与张量|向量、矩阵与张量]]
- 下一站：[[数学/20-线性代数与几何/03-点积范数距离与余弦相似度|点积、范数、距离与余弦]]
- 返回：[[数学/20-线性代数与几何/00-线性代数与几何-MOC|线性代数与几何 MOC]]
- 工程连接：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/20-线性代数与几何/10-线性映射核像与四个基本子空间|线性映射核像与四个基本子空间]]；[[数学/20-线性代数与几何/14-最小二乘伪逆与正则化|最小二乘伪逆与正则化]]；[[数学/20-线性代数与几何/16-SVD的推导最优低秩与PCA|SVD的推导最优低秩与PCA]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。
