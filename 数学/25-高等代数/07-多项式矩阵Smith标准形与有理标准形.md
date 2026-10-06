---
type: lesson
domain: mathematics
course: 高等代数
level: undergraduate
revision: 2
reviewed: 2026-09-05
tags:
  - mathematics/algebra
  - mathematics/core
---

# 多项式矩阵Smith标准形与有理标准形

## 为什么还需要不含特征根的标准形

实数域里的 $t^2+1$ 无法分成一次因子，数值特征根也可能不适合精确计算。有理标准形完全在底域中工作，用不可约多项式和伴随矩阵取代逐个特征值，背后的工具是多项式矩阵的 Smith 标准形。

## Smith 变换保持的是模结构

在 $F[t]$ 上，允许交换行列、加多项式倍的行列、乘非零常数。它们对应左右乘行列式为非零常数的可逆多项式矩阵，称幺模变换。任意多项式矩阵可化为
$$\operatorname{diag}(d_1,\ldots,d_r,0,\ldots,0),\qquad d_1\mid d_2\mid\cdots\mid d_r,$$
其中 $d_i$ 首一。存在性沿用 Euclid 算法：选最小次数非零元素移到左上，取余减小其他元素；若左上尚不整除余下子块，再引入一项继续降次数，最终满足整除，递归剩余块。

唯一性可用行列式因子说明：令 $\Delta_k$ 为所有 $k$ 阶子式的首一最大公因式，$\Delta_0=1$，则 $d_k=\Delta_k/\Delta_{k-1}$。幺模变换不改变这些公因式，因为新子式是旧子式的多项式线性组合，逆变换给出反向整除。

## 一个非对角的手算例子

对 $M(t)=\begin{pmatrix}t&1\\0&t\end{pmatrix}$，所有一阶子式的最大公因式为 1，行列式为 $t^2$，所以 Smith 形为 $\operatorname{diag}(1,t^2)$。显式操作：交换两列得到 $\begin{pmatrix}1&t\\t&0\end{pmatrix}$；第二行减 $t$ 倍第一行得 $\begin{pmatrix}1&t\\0&-t^2\end{pmatrix}$；第二列减 $t$ 倍第一列，最后第二行乘 $-1$，即得标准形。

原来两个对角上的 $t$ 并不意味着不变因子是 $t,t$，因为非对角的 1 会把它们连接成一个长的模生成关系。

## 从 $tI-A$ 到有理标准形

先区分证明层级：前面的 Euclid 降次数段是 **Smith 存在性的证明路线**，不是每一步消元的完整证明。本节的结构结论以“$F[t]$ 上每个有限矩阵有 Smith 形”为明确输入；本节用到的关系矩阵列独立，因此只需 Conrad §2 Theorem 2.14 的完整对齐基定理：它给环境自由模与关系子模各一组基，关系基逐项为 $d_i$ 倍环境基，且满足整除链；写成两组基的坐标变换正是本节所需的 $PBQ$ 对角化。下面 **完整证明这个输入如何给出循环分解及 $tI-A$ 的呈示**，不额外借用“有限生成模结构定理”作黑箱。

记 $R=F[t]$。先给一般有限生成 $R$-模 $M$ 选生成元 $m_1,\ldots,m_n$，定义满射 $\pi:R^n\to M$，$e_i\mapsto m_i$。第一同构定理给 $M\cong R^n/\ker\pi$。还要证明核有有限关系，而不能假定存在有限呈示。

**核的有限基引理。** $R$ 是 PID，因为多项式除法使每个非零理想由其中最小次数首一元素生成。对任意子模 $N\subset R^n$ 归纳 $n$：投影到第一坐标的像是理想 $(a)$。若 $a=0$，直接在后 $n-1$ 坐标归纳。若 $a\ne0$，选 $u\in N$ 第一坐标为 $a$。每个 $v\in N$ 的第一坐标为 $ba$，于是 $v-bu$ 落在零第一坐标子模 $N_0$。且 $Ru\cap N_0=0$，因为 $ca=0$ 在整环中迫使 $c=0$。所以 $N=Ru\oplus N_0$；归纳给它一个至多 $n$ 元的有限自由基。$n=1$ 正是理想为主的情况。

取 $N=\ker\pi$ 的基，将其列向量组成 $n\times m$ 矩阵 $B$。关系子模就是 $\operatorname{im}B$，故 $M\cong\operatorname{coker}B:=R^n/\operatorname{im}B$。若 $D=PBQ$ 是 Smith 形，$P\in GL_n(R),Q\in GL_m(R)$，则
$$\operatorname{im}(BQ)=\operatorname{im}B,\qquad P(\operatorname{im}B)=\operatorname{im}D.$$
右乘 $Q$ 是关系生成元的可逆基变换，左乘 $P$ 是环境自由模的可逆基变换；映射 $[v]\mapsto[Pv]$ 因此给两个商的同构，逆为 $[w]\mapsto[P^{-1}w]$。若 $D$ 有 $r$ 个非零对角项，逐坐标取剩余类的映射给
$$\operatorname{coker}D\cong\bigoplus_{i=1}^r R/(d_i)\ \oplus\ R^{n-r}.$$
其核恰为 $d_1Re_1+\cdots+d_rRe_r$，故该商分解没有隐含“关系互不影响”的假定。若 $M$ 为挠模，自由部分必须为0：自由部分的非零基向量不被任何非零多项式杀死。单位 $d_i$ 的商为0，删去后便得到有限生成挠模的循环分解，且 Smith 输入给 $d_1\mid\cdots\mid d_s$。

现在回到 $A\in M_n(F)$。让 $R$ 作用于 $V=F^n$：$p(t)\cdot v=p(A)v$。给定向量 $v$，$v,Av,\ldots,A^nv$ 线性相关，所以有非零多项式杀死 $v$；这直接证明 $V$ 为挠模，无需在此预借 Cayley–Hamilton。标准基在 $R$ 上仍生成 $V$。

它的精确呈示是 $V\cong R^n/(tI-A)R^n$。定义 $\Phi(\sum_{k=0}^d t^kv_k)=\sum_{k=0}^d A^kv_k$，它是 $R$-线性满射，且 $\Phi((tI-A)q)=0$。反向包含要展开：
$$t^kv-A^kv=(tI-A)\sum_{j=0}^{k-1}t^{k-1-j}A^jv\quad(k\ge1).$$
对 $q(t)=\sum t^kv_k$ 求和，得到 $q-\Phi(q)\in(tI-A)R^n$；若 $\Phi(q)=0$，便有 $q\in(tI-A)R^n$。所以核正好是这些关系。对 $tI-A$ 作 Smith 变换，再应用刚才的商分解，得到
$$V\cong\bigoplus_i F[t]/(d_i),\qquad d_1\mid\cdots\mid d_s,$$
这里只列非单位不变因子。$tI-A$ 的行列式为首一 $n$ 次多项式，不为0，故也可从矩阵秩看见没有自由商坐标。

前面的非对角算例也可直接从关系检验：$B=\begin{pmatrix}t&1\\0&t\end{pmatrix}$ 的两列给 $te_1=0$ 与 $e_1+te_2=0$，所以 $e_1=-te_2$，全部商由 $e_2$ 生成且 $t^2e_2=0$。若 $p(t)e_2$ 落在列空间，写成 $(ta+b,tb)$，第一坐标0给 $b=-ta$，故 $p=-t^2a$；关系恰为 $(t^2)$，并非只知道它被 $t^2$ 杀死。因此商确为 $R/(t^2)$，与 Smith 形 $\operatorname{diag}(1,t^2)$ 一致。这也是 $A=\begin{pmatrix}0&-1\\0&0\end{pmatrix}$ 的一个长度2幂零链。

在每个循环分量取 $v,Av,\ldots,A^{k-1}v$ 为基，若
$d=t^k+c_{k-1}t^{k-1}+\cdots+c_0$，矩阵为伴随矩阵
$$C(d)=\begin{pmatrix}0&0&\cdots&-c_0\\1&0&\cdots&-c_1\\0&1&\cdots&-c_2\\\vdots&\vdots&\ddots&\vdots\end{pmatrix}.$$
省略号表示前 $k-1$ 列的下副对角为 1，其余为零，最后一列依次为负系数。$k=1$ 时即标量 $-c_0$。

最小多项式是最大不变因子 $d_s$，特征多项式是 $\prod_i d_i$。这给出任何数域上的完整相似分类。再把不变因子分成不可约幂，可得到初等因子；当它们为一次因子的幂时，恢复 Jordan 块。

## 自测与解答

已知不变因子为 $t-1$ 与 $(t-1)^2(t+1)$，矩阵大小、最小多项式与特征多项式分别是什么？

> [!question]- 解答
> 维数是次数之和 $1+3=4$；最小多项式为 $(t-1)^2(t+1)$，特征多项式为 $(t-1)^3(t+1)$。在特征不为 2 的数域上分裂后，特征值 1 的 Jordan 块为 2、1，特征值 $-1$ 有一个大小 1 的块。

## 继续学习

前一节：[[数学/25-高等代数/06-Jordan标准形广义特征向量与幂零链|Jordan标准形广义特征向量与幂零链]]。 下一节：[[数学/25-高等代数/08-双线性型合同与实二次型惯性|双线性型合同与实二次型惯性]]。

课程地图：[[数学/25-高等代数/00-高等代数-MOC|高等代数课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/25-高等代数/12-环理想商环与同态基本定理#从同态到商结构|环理想商环与同态基本定理]] 解释商中代表元的运算为何良定义；本页的每个循环分量 $F[t]/(d_i)$ 正是把关系 $d_i[v]=0$ 编码成一个商。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Sheldon Axler：Linear Algebra Done Right，作者站点](https://linear.axler.net/)
- [J. S. Milne：群、环、域与 Galois 理论课程笔记](https://www.jmilne.org/math/CourseNotes/)
- 结构证明的精确依赖：[Keith Conrad, Modules over a PID, §2 Theorem 2.2（有限自由模的子模）、Theorem 2.14（对齐基，给本节列独立关系矩阵的对角化）、§4 Theorem 4.1 与 Corollary 4.3（商到循环分解），PDF pp.2–3、6–9、11–12](https://kconrad.math.uconn.edu/blurbs/linmultialg/modulesoverPID.pdf)。文件无明示日期/版号，以2026-09-17获取的25页版本及库外证据 SHA-256 标识；不是上述 Axler/Milne 首页对 Smith 内容的代言。

条件边界：删去挠性，$F[t]$ 本身为有限生成模，却有自由部分，不能分成有限个非零 $F[t]/(d)$ 的挠直和；删去有限生成性，$\bigoplus_{n\ge1}R/(t)$ 是挠模却没有有限生成集，不能得到本页的有限分解；删去 PID 条件，$F[x,y]$ 的理想 $(x,y)$ 不为主（同时整除 $x,y$ 的非单位不存在），核的有限自由基引理与这种单变量 Smith 论证即不再适用。
