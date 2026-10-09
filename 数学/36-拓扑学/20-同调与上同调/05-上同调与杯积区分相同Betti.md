---
type: lesson
aliases:
  - 上同调环与环面杯积
sources:
  - https://pi.math.cornell.edu/~hatcher/AT/ATch3.pdf
prerequisites:
  - "[[数学/36-拓扑学/20-同调与上同调/03-圆周环面RP2的整数同调与挠]]"
  - "[[数学/36-拓扑学/20-同调与上同调/04-Euler特征Betti与消边机制]]"
---
# 上同调与杯积：区分相同 Betti 的空间

$T^2$ 与 $W=S^1\vee S^1\vee S^2$ 有相同的整数同调加法群。要继续区分，可以问两个一维观测怎样共同评价二维循环。上同调把链变为可评价的对象；杯积记录观测之间的乘法，添回一部分仅有加法群时遗失的附着信息。

## 余链升维，评价的对象是链

取系数阿贝尔群 $G$，定义 $C^k(X;G)=\operatorname{Hom}_{\mathbb Z}(C_k(X;\mathbb Z),G)$；余链 $\phi$ 把每条 $k$-链评价为 $G$ 中的值。定义
$$\delta\phi=\phi\circ\partial_{k+1},\qquad H^k(X;G)=\ker\delta_k/\operatorname{im}\delta_{k-1}.$$
由 $\partial^2=0$ 得 $\delta^2=0$。余循环评价同调类：若 $c'=c+\partial b$，则 $\phi(c')-\phi(c)=\delta\phi(b)=0$；换余循环代表 $\phi'=\phi+\delta\psi$ 也不改对循环 $c$ 的评价。因而有 $H^k\times H_k\to G$ 的配对。

连续 $f:X\to Y$ 给 $f^*\phi=\phi\circ f_\#$，方向反转，且 $(g\circ f)^*=f^*g^*$。01的棱柱链同伦双化后证明同伦映射给同一 $f^*$。有限有序 $\Delta$-复形可以在它的单形链上直接评价，胞腔的加法上同调则由胞腔链复形的 $\operatorname{Hom}(-,G)$ 计算；整数有限基下 $\delta_k$ 的矩阵为 $\partial_{k+1}^T$。

为什么双化比较仍有效？有序 $\Delta$-链包含到奇异链，02的逐骨架比较给同调同构；其映射锥是自由阿贝尔群组成的无同调链复形。每个循环/边界群都是自由群的子群，故自由；正合列 $0\to B_k\to C_k\to B_{k-1}\to0$ 因右项自由可分裂，逐维选分裂便给该无同调复形的链收缩。双化保留收缩恒等式，故包含诱导的余链限制也给上同调同构。胞腔余链可由02骨架对的相对上同调正合列同样得到：相对群仅在附着维数非零，该维是胞腔整数群的对偶；连接映射正是 $\partial^T$，原骨架核/像论证升维后给 $H^k$。这说明转置并非“把最终同调群随手对偶”。

## 整数系数为什么不能只取同调的对偶

直接转置 RP² 的链复形得到
$$C^0=\mathbb Z\xrightarrow{0}C^1=\mathbb Z\xrightarrow{\times2}C^2=\mathbb Z.$$
所以
$$H^0(\mathbb{RP}^2;\mathbb Z)=\mathbb Z,\quad H^1=0,\quad H^2=\mathbb Z/2.$$
尽管整数 $H_2=0$，整数 $H^2$ 却非零；对整数1-挠类的 $\mathbb Z$ 值观测全为0，因 $2\phi([a])=0$ 在 $\mathbb Z$ 中迫使 $\phi([a])=0$。

其一般框架是自由整数链复形的上同调通用系数短正合列
$$0\to\operatorname{Ext}_{\mathbb Z}(H_{k-1},G)\to H^k(-;G)\to\operatorname{Hom}_{\mathbb Z}(H_k,G)\to0.$$
最右映射就是刚定义的评价；序列自然，但分裂一般没有自然的首选。为本课的**有限自由链复形**可具体证明：$C_k\to B_{k-1}$ 的短正合列因 $B_{k-1}$ 自由而分裂，选 $C_k=Z_k\oplus L_k$。消费整数 Smith 主解释，将每个包含 $B_k\subset Z_k$ 选成对角基。整个链复形遂分成单个自由生成元、以及两项 $\mathbb Z\xrightarrow{\times m}\mathbb Z$ 的直和；$m=1$ 是可缩对，$m>1$ 给低维 $\mathbb Z/m$。双化两项后，低维核为 $G[m]=\{g:mg=0\}$，高维商为 $G/mG$。这分别对应 $\operatorname{Hom}(\mathbb Z/m,G)$ 与 $\operatorname{Ext}(\mathbb Z/m,G)$；自由单项只贡献 $\operatorname{Hom}(\mathbb Z,G)=G$，其 Ext 为0。有限直和相加即给上式及非首选分裂。具体解释/计算所需整数基仍归 [[数学/25-高等代数/50-模与有限群表示/02-整数Smith核像商与同调接口|整数 Smith 主解释]]，这里不再证明 Smith 结构定理。

对 RP² 的 $H_1=\mathbb Z/2$，Ext 在下一维给 $\mathbb Z/2$，解释 $H^2$ 的来源。改成 $\mathbb F_2$ 系数则余边界乘2变0，$H^0,H^1,H^2$ 都是 $\mathbb F_2$；这里**不把模2的一维类当作整数一维类**。后续若研究 RP² 的模2杯积，需另用模2单形模型；本课不从三项零矩阵推断那个杯积，因为边界矩阵不包含所需的对角映射信息。

## 杯积的定义与良定义

从现在起系数取有单位的交换环 $R$，本课计算固定 $R=\mathbb Z$。有序奇异单形 $\sigma=[v_0,\dots,v_{p+q}]$ 上，对余链 $\alpha\in C^p,\beta\in C^q$ 定义
$$
(\alpha\smile\beta)(\sigma)
=\alpha(\sigma|[v_0,\dots,v_p])\,\beta(\sigma|[v_p,\dots,v_{p+q}]).
$$
一维与一维相乘，评价一个三角形的前边和后边；共有的顶点 $v_p$ 把两个观测接在同一单形上。乘法在 $R$ 中完成，不是链之间的拼接。

展开删面交错和，删前段的项组成 $\delta\alpha\smile\beta$，删后段的项组成 $(-1)^p\alpha\smile\delta\beta$；切分点左右的两个多余项符号相反。故一般恒等式为
$$\delta(\alpha\smile\beta)=\delta\alpha\smile\beta+(-1)^p\alpha\smile\delta\beta.$$
余循环相乘仍是余循环；若 $\alpha$ 换成 $\alpha+\delta\lambda$ 且 $\beta$ 闭，则增量为 $\delta(\lambda\smile\beta)$；若 $\beta$ 改一个余边界，同样由恒等式为余边界。于是得到良定义的
$H^p(X;R)\times H^q(X;R)\to H^{p+q}(X;R)$。

两次按相同断点取面，直接给结合律；拉回复合与取面相容给 $f^*(\alpha\smile\beta)=f^*\alpha\smile f^*\beta$，常数0维类1给单位。因而 $H^*(X;R)$ 是分次环且同伦等价诱导环同构。本课所用交换符号将从环面模型直接计算；一般分次交换定理另需一个链同伦，不能仅从单形余链公式声称余链层已经交换。

## 环面的两个三角形给可逐项复算的积

将单位正方形对边同向识别，沿左下至右上的对角线剖分。取有序三角形
$$t_1=[(0,0),(1,0),(1,1)],\qquad t_2=[(0,0),(0,1),(1,1)].$$
![[数学/36-拓扑学/20-同调与上同调/assets/torus-ordered-cup.svg]]

这是允许顶点/边识别的 $\Delta$-复形，**不是一个顶点的普通抽象单纯复形**。水平方向边记 $a$，竖直记 $b$，对角边 $c$；每条边的取向由坐标递增给定。商空间中顶点都成为 $v$，但单形参数顶点的先后仍保留。按有序面公式
$$\partial t_1=b-c+a,\qquad\partial t_2=a-c+b,$$
所以在行 $a,b,c$、列 $t_1,t_2$ 顺序下
$$\partial_2=\begin{pmatrix}1&1\\1&1\\-1&-1\end{pmatrix},\quad\partial_1=(0\ 0\ 0),\quad z=t_1-t_2.$$
$z$ 是有向整体面：$t_2$ 的顶点次序与平面正定向相反，故使用负号。核为 $\mathbb Zz$，没有3-胞腔，$H_2=\mathbb Z[z]$；$H_1=\mathbb Z\langle a,b,c\rangle/\mathbb Z(a+b-c)$，所以 $c=a+b$，结果为 $\mathbb Z^2$。

定义余循环 $x,y$ 的边值为
$$x(a)=1,x(b)=0,x(c)=1;\qquad y(a)=0,y(b)=1,y(c)=1.$$
在两个三角形上，$\delta x=1+0-1=0,\delta y=0+1-1=0$；顶点余边界为0，所以它们代表 $H^1$ 的两个生成元。任意2-余链用 $(r,s)$ 记值，$\operatorname{im}\delta_1=\mathbb Z(1,1)$，故 $H^2=\mathbb Z$，评价 $z$ 为 $r-s$；取 $u$ 值 $(1,0)$，它满足 $u(z)=1$。

杯积只需读前后边：

| 有序面 | 前边 $[v_0v_1]$ | 后边 $[v_1v_2]$ | $x\smile y$ | $y\smile x$ | $x\smile x$、$y\smile y$ |
| --- | --- | --- | --- | --- | --- |
| $t_1$ | $a$ | $b$ | $1$ | $0$ | 都0 |
| $t_2$ | $b$ | $a$ | $0$ | $1$ | 都0 |

所以在整数上同调中
$$x\smile y=u,\qquad y\smile x=-u,\qquad x^2=y^2=0.$$
高于2维的群为0，连同单位已给出整个环，常记为 $\Lambda_{\mathbb Z}(x,y)$。这里 $y\smile x=-u$ 因评价 $z=t_1-t_2$ 得 $-1$，有具体符号理由。这个模型也说明只知道最小胞腔模型中 $\partial_2=0$，仍算不出杯积；还要保留面如何分成前后部分。

## 同样的加法群，楔和的积为什么为零

$W=S^1_a\vee S^1_b\vee S^2$ 的胞腔余边界皆0，所以 $H^0=\mathbb Z,H^1=\mathbb Z^2,H^2=\mathbb Z$，与环面一样。包含 $i:S^2\hookrightarrow W$ 在 $H^2$ 上诱导同构：它在胞腔余链上保留唯一2-胞腔，边界为0；在 $H^1$ 上诱导零映射，因为球面 $H^1=0$。对任意 $x',y'\in H^1(W)$，自然性给
$$i^*(x'\smile y')=i^*x'\smile i^*y'=0.$$
因 $i^*:H^2(W)\to H^2(S^2)$ 单射，推出 **所有一维类乘积都为0**。环面却有非零 $x\smile y$，因此两个分次环不同构，两空间不可能同伦等价。此处不只是比较一组选中的基；“所有乘积为零”与“存在非零乘积”都在任意换基下成立。

## 自测与边界

1. 环面中 $(x+y)^2$、$(2x-y)\smile(x+3y)$ 为何？
2. 为什么 RP² 的整数 $H^2=\mathbb Z/2$ 不代表存在整数基本2-循环？
3. 一个程序只得到 $c_k$ 和边界矩阵，能否自动输出一般空间的杯积？

> [!question]- 完整答案
> 1. $(x+y)^2=x^2+xy+yx+y^2=u-u=0$；第二个积为 $6xy-yx=7u$。交叉项不能按普通交换多项式处理。
> 2. 整数 $H_2=0$，该 $H^2$ 来自上同调 UCT 的 $\operatorname{Ext}(H_1,\mathbb Z)$；评价到 $\operatorname{Hom}(H_2,\mathbb Z)$ 为零。这里不存在能让它评价成非零整数的2-循环。
> 3. 不能。环面和楔和的最小胞腔链群及边界矩阵完全一样，杯积却不同。还需与对角映射相容的单形/胞腔对角数据；本课保留了两三角形有序面数据来完成指定算例。

来源定位：[Hatcher §3.1 Theorem 3.2（UCT）与 Theorem 3.5（胞腔余链），§3.2 Lemma 3.6（杯积余边界）及 Example 3.7（环面）](https://pi.math.cornell.edu/~hatcher/AT/ATch3.pdf)。本课的两三角形坐标与杯积表逐项给出，模2 RP² 杯积和 Poincaré 对偶没有作为已完成内容。
