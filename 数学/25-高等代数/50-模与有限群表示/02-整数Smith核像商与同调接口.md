---
type: lesson
domain: mathematics
stage: 3
aliases:
  - 整数Smith的核像商合同
prerequisites:
  - "[[数学/25-高等代数/50-模与有限群表示/01-模同态正合列与PID结构]]"
sources:
  - https://kconrad.math.uconn.edu/blurbs/linmultialg/modulesoverPID.pdf
---

# 整数 Smith：核、像、商与同调接口

整数边界矩阵不仅记录“有几个独立关系”，还记录“一个关系是某个生成元的几倍”。把整数矩阵直接变成浮点秩，会抹掉商中的挠。这里固定精确的输入、变换方向和输出，使同调计算能够复用一般 PID/Smith 理论。

## 输入与返回：始终保存两侧变换

输入为整数矩阵 $B\in\mathbb Z^{m\times n}$，采用列向量，表示 $B:\mathbb Z^n\to\mathbb Z^m$。输出包括

$$U\in GL_m(\mathbb Z),\quad V\in GL_n(\mathbb Z),\quad D=UBV\in\mathbb Z^{m\times n},$$

$$D_{ii}=d_i>0\ (1\le i\le r),\quad d_i\mid d_{i+1},\quad\text{其余元素为零}.$$

整数幺模矩阵的行列式为 $\pm1$，所以逆仍为整数矩阵。允许交换、加整数倍的行/列、乘 $-1$；不可用“把一行除以 2”作为整数可逆变换。算法可以返回不同 $U,V$，但正的整除链相同。零矩阵有 $r=0$、空不变量表；必须保留 $m,n$，不能从空列表猜矩阵尺寸。

坐标方向由等式本身确定：令原输入 $x=Vy$，原输出 $b=Bx$；新输出坐标为 $z=Ub$，于是 $z=Dy$。$V$ 的列是原定义域内的新基；$U^{-1}$ 的列是原值域内的新基。把 $U,V$ 都当成同方向的换基矩阵会取错逆。

任何实现至少以精确整数核对 $UBV=D$、$U,V$ 的幺模性、矩阵 shape、正性和整除链。一般定理证明见 [[数学/25-高等代数/50-模与有限群表示/01-模同态正合列与PID结构#PID 上 Smith 对角化：不假设 Euclidean 函数|PID Smith 对角化]]；精确小例只核对具体实现，不能替代存在性证明。

## 核、像与商怎样从同一返回值读出

因为 $UBV=D$ 且 $\mathbb Z$ 无零因子：

| 对象 | 精确表示 | 必须保留的区别 |
|---|---|---|
| $\ker B$ | $V$ 的第 $r+1,\ldots,n$ 列构成整数基 | 是整个整数核的基，不是随意缩放的有理零空间基 |
| $\operatorname{im}B$ | $U^{-1}d_ie_i$，$i=1,\ldots,r$，构成整数基 | 向量 $U^{-1}e_i$ 未必属于像 |
| $\operatorname{coker}B$ | $\bigoplus_{i=1}^r\mathbb Z/d_i\mathbb Z\oplus\mathbb Z^{m-r}$ | $d_i=1$ 的项为零；$d_i>1$ 给挠，自由秩为 $m-r$ |

具体商同构把原向量 $b$ 映到 $Ub$：前 $r$ 坐标分别模 $d_i$，剩余坐标保留为整数。两个整数向量属于同一剩余类，当且仅当这些输出相同。单独返回 $r$ 无法恢复这个判断。

### 一个包含非平凡左右变换的精确例

$$B=\begin{pmatrix}4&6\\2&6\end{pmatrix},\quad U=\begin{pmatrix}0&1\\-1&2\end{pmatrix},\quad V=\begin{pmatrix}1&-3\\0&1\end{pmatrix}.$$

先算 $UB=\begin{pmatrix}2&6\\0&6\end{pmatrix}$，再右乘 $V$ 得 $D=\operatorname{diag}(2,6)$。两变换行列式均为 1。也可独立用子式核对：一阶子式 gcd 为 2，$|\det B|=12$，因此 $d_1=2,d_2=12/2=6$。

核为零，像有基 $(4,2)^T,(-6,0)^T$，商为 $\mathbb Z/2\oplus\mathbb Z/6$，共有 12 个元素。原输出 $(a,b)^T$ 的商坐标为 $(b\bmod2,(-a+2b)\bmod6)$。整数基变换不能把这个商消成零；在 $\mathbb Q$ 上 $B$ 可逆，商却为零。基础环改变了问题。

## 同调消费合同：先求整数核，再把边界放进去

给出相邻整数边界矩阵

$$A=\partial_k\in\mathbb Z^{m\times n},\qquad B=\partial_{k+1}\in\mathbb Z^{n\times p},\qquad AB=0.$$

目标是 $H_k=\ker A/\operatorname{im}B$。先精确核对 $AB=0$，否则连商的包含关系都不成立。

1. 对 $A$ 返回 $(U_A,D_A,V_A)$，满足 $U_AAV_A=D_A$，记非零对角项数为 $r$。
2. 取 $K=V_A[:,r+1:n]\in\mathbb Z^{n\times(n-r)}$，其列是整数核的基；这里列号使用从 1 开始的数学记法。
3. 计算整数矩阵 $V_A^{-1}B$。因 $D_AV_A^{-1}B=U_AAB=0$，其前 $r$ 行必须恰为零；把后 $n-r$ 行记为 $C$，则 $B=KC$。
4. 对 $C$ 再作 $U_CCV_C=D_C$，非零正对角项为 $e_1\mid\cdots\mid e_s$。于是

$$\boxed{H_k\cong\bigoplus_{i=1}^s\mathbb Z/e_i\mathbb Z\ \oplus\ \mathbb Z^{n-r-s}.}$$

第二次 Smith 的对象是**边界在整数循环基中的坐标** $C$。不能把环境空间的一次秩计算冒充这一步。对循环 $x=Kz$，商坐标为 $U_Cz$；原链空间中的挠/自由代表可以取 $KU_C^{-1}e_i$。实现需返回 $K,C$ 与所用变换，才能追踪这些代表及其阶，而不是只给一个抽象群名字。

### 两个一眼可核对的同调输入

先看 $\mathbb Z\xrightarrow{\times2}\mathbb Z\to0$。乘 2 的核为 0、像为 $2\mathbb Z$，右端同调为 $\mathbb Z/2$。改成 $\mathbb Q\xrightarrow{\times2}\mathbb Q\to0$，核仍为 0，但像变为整个 $\mathbb Q$，商为 0。两边的矩阵秩都为 1，不能据此说同调相同。

再取 $A=(1\quad1)$、$B=(2\quad-2)^T$。$AB=0$，整数核基可取 $K=(1\quad-1)^T$，且 $B=K(2)$，所以 $H=\mathbb Z/2$。若误取 $K'=(2\quad-2)^T$ 作为“核基”，虽然它张成同一个有理零空间，却漏掉整数循环 $(1,-1)^T$，错误地得到坐标关系 $C'=(1)$ 和零同调。这是必须保存幺模变换的直接理由。

## 同一方法在整数与多项式环上保留什么

| 基础环 | 关系矩阵 | Smith 不变量 | 商的解释 |
|---|---|---|---|
| $\mathbb Z$ | 本页 $B=\begin{pmatrix}4&6\\2&6\end{pmatrix}$ | 正整数 $2,6$ | 有限 Abel 群 $\mathbb Z/2\oplus\mathbb Z/6$ |
| $F[t]$ | $\begin{pmatrix}t&1\\0&t\end{pmatrix}$ | 首一多项式 $1,t^2$ | 一个长度 2 的幂零循环模 $F[t]/(t^2)$ |
| $F[t]$ | $tI-T$ | 首一整除链 $d_i(t)$ | 线性算子 $T$ 的有理标准形块 |

最后两行的呈示、变换与循环分解已在 [[数学/25-高等代数/07-多项式矩阵Smith标准形与有理标准形#从 $tI-A$ 到有理标准形|原 Smith 主解释]] 完整展开，直接复用。整数挠元阶与多项式湮灭关系具有相同商模机制，但不是同一组数值不变量；$F[t]$ 的单位为非零常数，$\mathbb Z$ 的单位只有 $\pm1$。

## 迁移题与答案

1. **只保存 Smith 对角线足够计算同调代表吗？** 不够。它给抽象商类型；要把循环和边界坐标互相转换，还需 $U,V$、整数核基以及边界在核中的坐标。
2. **实数 SVD 报零奇异值，能否直接读出 $\mathbb Z/2$？** 不能。秩只描述扩到域后的维数，既不提供整数饱和核基，也不保留非单位整除不变量。
3. **Smith 与相似变换相同吗？** 不同。Smith 允许独立更换定义域和值域基，形式为 $UBV$；单个算子的相似变换要求同一个空间两端同步，形式为 $P^{-1}TP$。$tI-T$ 的呈示才把这两种分类正确接起来。

本页合同基于精确整数运算。通用大规模 Smith 算法的性能、数值近似与任意环上的分类不由这些小例保证；一般环也不能无条件套用 PID 定理。


## 精确实现与读取边界

在 [[数学/25-高等代数/50-模与有限群表示/06-整数Smith与表示精确复算#输入、返回和停止边界|完整左右变换的精确实现]] 读取 U/D/V、K/C 和代表。源码以从0开始的切片 `rows[rank:]`／每行 `row[rank:]` 对应本页从1开始的数学列号；只返回 D 的库接口不足以兑现本页的原坐标合同。固定输入与独立预期答案在那里给出，实际执行状态单独记录。
