---
type: lesson
stage: 0
aliases:
  - Artin固定域定理
  - 域自同构线性独立
sources:
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=36
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=68
prerequisites:
  - "[[数学/25-高等代数/30-Galois理论/02-分裂域正规可分与Galois判别]]"
  - "[[数学/20-线性代数与几何/09-向量空间基维数与坐标]]"
---
# 自同构、固定域与 Artin 定理

给一个有限自同构群 $G$，共同不动的元素形成固定域
$$E^G=\{x\in E:\sigma(x)=x\text{ 对所有 }\sigma\in G\}.$$
显然 $E^G$ 是域；困难是证明它没有“藏着的自由度”：
$$[E:E^G]=|G|.$$
这个等式连接群阶与域次数，是有限 Galois 对应的发动机。

## 第一个核心引理：不同嵌入线性独立

**Dedekind–Artin 独立性。** 若 $\sigma_1,\ldots,\sigma_n:E\to\Omega$ 是不同域嵌入，则不存在不全为零的 $c_i\in\Omega$ 使
$$c_1\sigma_1(x)+\cdots+c_n\sigma_n(x)=0\qquad\text{对所有 }x\in E.$$

**证明。** 反设存在，取非零项数最少的关系，除以一个系数后可设 $c_1=1$。至少有两项；因 $\sigma_1\ne\sigma_j$，可取 $a\in E$ 使 $\sigma_1(a)\ne\sigma_j(a)$。把 $x$ 换成 $ax$：
$$\sum_i c_i\sigma_i(a)\sigma_i(x)=0.$$
用原关系乘 $\sigma_1(a)$ 后相减，第一项消失，而第 $j$ 项系数 $c_j(\sigma_j(a)-\sigma_1(a))\ne0$。得到更短的非零关系，矛盾。证毕。

这证明的是把嵌入看成 $E\to\Omega$ 的函数时，在 $\Omega$ 上独立；它不是把自同构当作 $E$-线性映射，因为自同构通常不保持 $E$ 中所有标量。[Milne，Dedekind’s theorem，印刷 pp.67–68](https://www.jmilne.org/math/CourseNotes/FT.pdf#page=68)

## Artin 定理的“至多”方向

设 $G=\{\sigma_1,\ldots,\sigma_n\}$ 是 $E$ 的有限自同构群，$F=E^G$。要证任意 $n+1$ 个元素 $\alpha_1,\ldots,\alpha_{n+1}$ 在 $F$ 上相关。

考虑 $n$ 个方程、$n+1$ 个未知量的齐次系统
$$\sum_{j=1}^{n+1}\sigma_i(\alpha_j)x_j=0\qquad(i=1,\ldots,n).$$
在域 $E$ 上未知数多于方程，所以有非零解。选一个非零坐标数最少的解，重排并缩放使 $x_1=1$。对任意 $\tau\in G$，给所有系数和值施加 $\tau$；左侧的行变成 $\tau\sigma_i$ 对应的行，而左乘 $\tau$ 只排列 $G$。因此 $(1,\tau x_2,\ldots)$ 也是解。与原解相减，第一坐标变成 0。极小性迫使差为零，所以每个 $x_j$ 被所有 $\tau$ 固定，即 $x_j\in F$。这正给出 $\alpha_j$ 的非平凡 $F$-线性关系。

故 $\dim_F E\le n$；特别地，有限群的固定域自动给出有限扩张。这一步不预先假设 $E/F$ 有限。

## “至少”方向与精确等号

已知 $m=[E:F]\le n$，取 $F$-基 $b_1,\ldots,b_m$。任一函数 $E\to E$ 若是 $F$-线性的，就由它在这 $m$ 个基向量上的值决定，因此所有 $F$-线性函数嵌入 $E^m$。若 $n>m$，$n$ 个自同构的值向量
$$(\sigma_i(b_1),\ldots,\sigma_i(b_m))\in E^m$$
在 $E$ 上线性相关，便产生 $\sum_i c_i\sigma_i=0$ 的函数关系，违背独立性引理。所以 $n\le m$。结合两边：
$$\boxed{[E:E^G]=|G|}.$$

再令 $A=\operatorname{Aut}(E/E^G)$。显然 $G\subseteq A$；对任意有限扩张，自同构数至多等于次数，所以
$$|G|\le|A|\le[E:E^G]=|G|,$$
于是 $A=G$。这就是 **Artin 固定域定理**。[Milne，Theorem 3.4 与 Corollary 3.5，印刷 pp.36–37](https://www.jmilne.org/math/CourseNotes/FT.pdf#page=37)

## 为什么它补完 Galois 判别

若 $E$ 是可分多项式 $f\in F[x]$ 的分裂域，所有 $F$-嵌入都把根置换回 $E$，成为自同构；逐层可分计数给 $|\operatorname{Aut}(E/F)|=[E:F]$。设其固定域为 $F'\supset F$，Artin 定理又给 $[E:F']$ 等于同一个群阶，所以塔式迫使 $F'=F$。

反过来，若有限群 $G$ 作用在 $E$ 上并令 $F=E^G$，对任意 $\alpha\in E$ 考虑
$$P_\alpha(x)=\prod_{\beta\in G\alpha}(x-\beta).$$
群置换轨道，故系数被 $G$ 固定，落在 $F$；而 $P_\alpha(\alpha)=0$，所以最小多项式 $m_{\alpha,F}$ 在 $F[x]$ 中整除 $P_\alpha$。轨道元素互异，$P_\alpha$ 是 $E[x]$ 中互异一次因子的乘积；它的任一因子 $m_{\alpha,F}$ 因而也在 $E$ 中分裂且无重根。因此每个最小多项式可分并分裂，$E/F$ 正规可分。这里再次得到有限 Galois 的等价刻画，而且没有循环引用基本定理。

## 在双二次例中直接看固定条件

令 $E=\mathbb Q(\sqrt2,\sqrt3)$，$G$ 是两个独立变号生成的 $V_4$。若
$$u=a+b\sqrt2+c\sqrt3+d\sqrt6$$
被两个变号都固定，先变 $\sqrt2$ 得 $b=d=0$，再变 $\sqrt3$ 得 $c=0$，故 $u=a\in\mathbb Q$。所以 $E^G=\mathbb Q$。Artin 定理把这次系数计算推广为任意有限自同构群的次数等式。

## 改变假设：无限群不能照抄群阶等式

有限性进入了齐次系统的 $n$ 行以及有限维比较。无限 Galois 扩张中，固定域对应的是带 Krull 拓扑的**闭子群**；$|G|=[E:F]$ 也不再是这里的有限整数等式。例如代数闭包的自同构群与扩张维数都是无限对象，不能用“未知数多一个”的有限矩阵论证。无限理论见 Milne 第 7 章，本课程不把它冒充本定理的直接推论。

## 练习与完整答案

**题。** 设 $G=\langle\sigma\rangle$ 作用在 $E=\mathbb Q(\sqrt2,\sqrt3)$ 上，其中 $\sigma$ 同时改变两个平方根的符号。求 $E^G$，并只用 Artin 定理与塔式核对答案次数。

> [!question]- 解答
> 固定 $u=a+b\sqrt2+c\sqrt3+d\sqrt6$ 要求 $b=c=0$，而 $a,d$ 任意，所以 $E^G=\mathbb Q(\sqrt6)$。群阶为2，Artin 给 $[E:E^G]=2$；又 $[E:\mathbb Q]=4$，塔式给 $[E^G:\mathbb Q]=2$，与 $x^2-6$ 不可约一致。注意群只含“同时变号”，不能额外要求分别变号也固定；多加两个未在 $G$ 中的条件会错误地把固定域缩成 $\mathbb Q$。

下一课用本定理证明 [[数学/25-高等代数/30-Galois理论/04-有限Galois基本定理与正规商群|有限 Galois 基本定理的两个方向]]。
