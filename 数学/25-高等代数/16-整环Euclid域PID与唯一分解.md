---
type: lesson
stage: 0
aliases:
  - 欧几里得整环主理想整环唯一分解整环
  - Gauss引理的适用条件
sources:
  - https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html
  - https://ocw.mit.edu/courses/res-18-012-algebra-ii-student-notes-spring-2022/mit18_702s22_full_lec.pdf
prerequisites:
  - "[[数学/25-高等代数/01-多项式整除Euclid算法与Bezout恒等式]]"
  - "[[数学/25-高等代数/12-环理想商环与同态基本定理]]"
---
# 整环、Euclid 域、PID 与唯一分解

在整数中，约分、Bézout 和唯一分解常常一起出现；换了环，它们可以分开。本页回答：**因子分解需要哪些结构，哪一步失效会造成什么后果？** 默认 $R$ 是交换含单位元的环，且 $1\ne0$。整环是没有非零零因子的这种环：$ab=0$ 推出 $a=0$ 或 $b=0$。域当然是整环，但整环不要求非零元素全可逆。

先看 [[数学/25-高等代数/12-环理想商环与同态基本定理#环比域保留了更多不可逆结构|模 6 的零因子]]。在 $\mathbb Z/6\mathbb Z$ 中 $2\cdot1=2\cdot4$，不能约去非零的 2；在整环中 $a\ne0$ 且 $ab=ac$，则 $a(b-c)=0$，所以 $b=c$。**约分不需要 $a$ 可逆**；例如在 $\mathbb Z$ 中可以约去 2，但 $1/2$ 不在环内。约分也不能把 $2x=1$ 强行解成一个整数。

## 因子需要先分清单位、关联、不可约与素元

单位 $u$ 有环内逆元；$a,b$ 关联表示 $a=ub$，$u$ 是单位。它们差一个可逆因子，在分解唯一性中视作同一种因子。整数的单位是 $\pm1$；$F[x]$ 的单位是非零常数；$\mathbb Z[i]$ 的单位是 $\pm1,\pm i$。

非零非单位 $p$ 称**不可约**，若 $p=ab$ 必使 $a$ 或 $b$ 为单位；它不能分成两个非单位。非零非单位 $p$ 称**素元**，若 $p\mid ab$ 必使 $p\mid a$ 或 $p\mid b$。素元控制它如何整除别人的乘积，含义更强。整环中素元必不可约：若 $p=ab$，不妨 $p\mid a$，写 $a=pc$，非零约分得 $1=bc$，所以 $b$ 是单位。反向在一般整环中不成立，后面给出完整反例。

最大公因子 $d$ 指 $d\mid a,b$，且任意公因子都整除 $d$；不是靠数值“大小”定义。若存在，它只在关联意义下唯一。UFD（唯一分解整环）要求每个非零非单位有有限不可约分解，且分解在重排和各因子关联之外唯一。**存在性也属于定义**，仅有“不可约都素”而没有分解终止不能直接叫 UFD。[Sharifi §5.1，Definitions 5.1.1–5.1.5、5.1.23 与 Proposition 5.1.27](https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html)

## Euclidean → PID：最小余数为什么控制整个理想

Euclidean（Euclid）整环有函数 $\delta:R\setminus\{0\}\to\mathbb N$，对任意 $a\in R,b\ne0$，存在 $q,r\in R$，使
$$a=qb+r,\qquad r=0\ \text{或}\ \delta(r)<\delta(b).$$
本页采用这个带余除法定义，不额外要求 $\delta$ 乘法性。$\mathbb Z$ 可取绝对值，$F[x]$ 可取次数；[[数学/25-高等代数/01-多项式整除Euclid算法与Bezout恒等式#为什么整数算法会出现在多项式中|既有多项式除法证明]] 已说明系数域为何必需，这里不重抄。

PID（主理想整环）是每个理想都由一个元素生成的整环。设 Euclidean 整环的理想 $I\ne(0)$，在 $I$ 的非零元素中选 $\delta$ 最小的 $d$。任意 $a\in I$，除以 $d$ 得 $a=qd+r$。余数也在 $I$；非零余数会比 $d$ 更小，矛盾，故 $r=0$。于是 $a\in(d)$，而 $d\in I$ 保证 $(d)\subset I$，故 $I=(d)$。零理想由 0 生成。证明的关键是“余数仍在同一个理想”，不是凭借任何两个数存在 gcd 就推所有理想主生成。[MIT 2022，Proposition 12.6，印刷 p60](https://ocw.mit.edu/courses/res-18-012-algebra-ii-student-notes-spring-2022/mit18_702s22_full_lec.pdf#page=60)

## PID → UFD：先保障终止，再保障素性与唯一性

**第一步：理想升链终止。** 若 $I_1\subset I_2\subset\cdots$，并集 $I$ 也是理想。PID 使 $I=(d)$，而 $d$ 属于某个 $I_N$，所以 $(d)\subset I_N\subset I$，从 $N$ 起全链相等。尤其主理想不可能无限严格上升。

**第二步：分解存在。** 假设有非零非单位不能分解为有限个不可约因子。若 $a$ 是这样的元素，它不是不可约，故 $a=bc$、$b,c$ 均非单位，至少一个因子也不能分解，否则合并两边分解就能分解 $a$。选该因子作下一步，得到严格上升链 $(a)\subsetneq(b)\subsetneq\cdots$：若 $(a)=(b)$，则 $b=at= bct$，整环中 $b\ne0$ 可约，得 $ct=1$，违反 $c$ 非单位。与第一步矛盾，故分解必须存在。

**第三步：不可约必素。** 设 $p$ 不可约、$p\mid ab$ 且 $p\nmid a$。PID 中 $(p,a)=(d)$；$d\mid p$，不可约性迫使 $d$ 为单位或与 $p$ 关联。后者会使 $p\mid a$，故 $d$ 为单位，$(p,a)=R$。因此存在 $u,v\in R$，$up+va=1$。乘以 $b$，得 $b=upb+vab$，右侧都被 $p$ 整除，故 $p\mid b$。

**第四步：唯一性。** 若 $up_1\cdots p_r=vq_1\cdots q_s$，其中 $u,v$ 单位，$p_i,q_j$ 不可约，则素性使 $p_1$ 整除某个 $q_j$。不可约 $q_j$ 使它与 $p_1$ 关联。吸收单位、重排并约去这个非零因子，归纳继续。不能一侧先无因子而另一侧还剩非单位，因为非单位的乘积在整环中仍是非单位：乘积若可逆，各因子也可逆。因此 $r=s$，所有因子一一关联。[Sharifi，Corollary 5.1.20、Proposition 5.1.21、Theorem 5.1.29；MIT，Theorem 12.3](https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html)

链条现在完整：Euclidean 整环 $\Rightarrow$ PID $\Rightarrow$ UFD $\Rightarrow$ 整环。每条箭头提供的能力不同；其逆向不能默认成立。

## Gaussian 整数：同一例子走完整条链

在 $\mathbb Z[i]$ 中用 $N(a+bi)=a^2+b^2$。它是整数值乘法范数，且 $N(z)=0$ 仅当 $z=0$。对 $\alpha,\beta\in\mathbb Z[i]$、$\beta\ne0$，把复数 $\alpha/\beta$ 的实、虚部各取最近整数得到 $q$。两方向误差绝对值均不超过 $1/2$，故
$$N(\alpha-q\beta)=N(\beta)N(\alpha/\beta-q)\le\tfrac12N(\beta)<N(\beta).$$
于是它 Euclidean，继而 PID、UFD。这里在复数域计算商来**选整数格点**，最后的 $q,r$ 均回到 $\mathbb Z[i]$，没有假装环中全元素可逆。

取 $\alpha=7+5i,\beta=3+2i$，有 $\alpha/\beta=(31+i)/13$，取 $q=2$，$r=1+i$，$N(r)=2<13=N(\beta)$。且 $5=(2+i)(2-i)$；两个因子范数为素数 5，所以不可约，因为非单位因子范数均至少为 2，不可能乘为 5。整数 5 在这里可约，与它在 $\mathbb Z$ 的素性完全相容，**素性必须绑定所在环**。[Sharifi，Proposition 5.4.15、Corollary 5.4.16](https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html)

## 逆箭头和一般整环的反例

**UFD 不必 PID。** $\mathbb Z[x]$ 是 UFD（下一节 Gauss 的推论），但理想 $(2,x)$ 不主生成。若 $(2,x)=(f)$，则 $f\mid2$，次数比较使 $f$ 是常整数，且 $f\mid x$ 使 $f=\pm1$，故理想应为全环。然而模 2 后令 $x=0$ 的同态把 $(2,x)$ 全送到 0，把 1 送到 1，说明它是真理想，矛盾。于是这里 gcd$(2,x)=1$，却没有 $u(x)2+v(x)x=1$。UFD 的 gcd 不能自动提供 PID 的 Bézout。

**PID 不必 Euclidean。** 标准例为 $R=\mathbb Z[\omega]$、$\omega=(1+\sqrt{-19})/2$。它是 PID 的正向核验在 [Sharifi Example 5.4.26 与 Proposition 5.4.25](https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html) 使用 Dedekind–Hasse 范数；该逐情形验证是本页明确的进阶依据，本页没有提供其完整展开，也不凭“小范围搜索找不到余数”证明它非 Euclidean。

非 Euclidean 一侧可以在这里证明，排除**任何**满足本页定义的 $\delta$。若有这样的 $\delta$，选所有非零非单位中 $\delta$ 最小的 $b$；每个余数 $r$ 只能是 0 或单位。乘法范数
$$N(a+c\omega)=a^2+ac+5c^2=(a+c/2)^2+19c^2/4$$
显示非整数元素范数至少 5，单位只有 $\pm1$。除整数 2 得 $2=qb+r$、$r\in\{0,1,-1\}$，故非单位 $N(b)>1$ 整除 1、4 或 9。方程 $N(b)=3,9$ 若 $c\ne0$，$|c|\ge2$ 已使范数至少 19；$c=\pm1$ 时 $a^2\pm a+5=3$ 或 9 无整数解。因此可能的 $b$ 只能为 $\pm2,\pm3$，范数为 4 或 9。再除 $\omega$，余数仍只能为 0、1、−1，然而 $N(\omega)=N(\omega-1)=5$、$N(\omega+1)=7$ 均不能被 4 或 9 整除，矛盾。[Sharifi Lemma 5.4.22、Example 5.4.23](https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html)

**整环不必 UFD，不可约不必素。** 在 $\mathbb Z[\sqrt{-5}]\subset\mathbb C$，$N(a+b\sqrt{-5})=a^2+5b^2$ 乘法性成立；单位仅为 $\pm1$。没有范数为 2 或 3 的元素。2 的范数为 4，非单位分解只能要求两个范数为 2；3 的范数为 9，只能要求两个范数为 3，均不可能。$1\pm\sqrt{-5}$ 的范数为 6，非单位分解需要范数 2 和 3，也不可能。因此这四个元素都不可约；单位只有 $\pm1$，它们两两不关联，却有
$$6=2\cdot3=(1+\sqrt{-5})(1-\sqrt{-5}).$$
2 整除右侧乘积，却不整除任一因子（系数除以 2 不再是整数），所以它不可约而不素。环是整环，**非零乘法约分仍然合法**；失败的是“不可约整除乘积就整除某个因子”。[Sharifi Example 5.4.20](https://www.math.ucla.edu/~sharifi/notes/algebra-ch05.html)

## Gauss 引理把系数环与分式域接起来

设 $R$ **是 UFD**，$K=\operatorname{Frac}(R)$。非零多项式的内容 $c(f)$ 是系数的 gcd，按单位倍确定；内容是单位时称本原。可以写 $f=c(f)f_0$，$f_0$ 本原。Gauss 引理说本原多项式的乘积仍本原。

证明：若本原 $f,g$ 的乘积不本原，系数有一个不可约公因子 $p$。UFD 中 $p$ 是素元，故 $R/(p)$ 是整环。把两多项式系数模 $p$，本原性保证它们都非零；整环上的多项式乘积非零（首项乘积非零），与乘积系数全为 0 矛盾。由此得到 $c(fg)\sim c(f)c(g)$，$\sim$ 表示关联。[MIT，Definition 12.17、Lemma 12.18，印刷 p62](https://ocw.mit.edu/courses/res-18-012-algebra-ii-student-notes-spring-2022/mit18_702s22_full_lec.pdf#page=63)

更具体地，若本原 $f\in R[x]$ 在 $K[x]$ 分解为正次数 $AB$，分别清分母、除内容，写 $A=aA_0,B=bB_0$，$a,b\in K^\times$，$A_0,B_0\in R[x]$ 本原。于是 $f=abA_0B_0$。将 $ab=s/t$ 取约分形式；$tf=sA_0B_0$ 两侧取内容得 $t\sim s$，约分使它们均为单位。所以 $ab\in R^\times$，分解回到 $R[x]$。反向的正次数分解当然也是 $K[x]$ 的分解。因此本原且正次数的 $f$ 在 $R[x]$ 不可约，当且仅当在 $K[x]$ 不可约；常数非单位需单独考虑，不能把它在 $K[x]$ 中已成单位忘掉。

此外 $R[x]$ 也是 UFD：内容用 $R$ 的分解，本原部分用 Euclidean 整环 $K[x]$ 的有限唯一分解；每个因子清分母后取本原代表。上段内容论证使乘积只差 $R$ 的单位，并让 $K[x]$ 中本原因子的关联降回 $R[x]$ 中的关联，所以存在性和唯一性都传回。于是 $\mathbb Z[x]$、$F[x,y]$ 是 UFD。回读 [[数学/25-高等代数/02-多项式的根重数不可约性与插值#如何判断不可约|Eisenstein 证明路线]] 时，现在能看清它使用 Gauss 的那一步，以及为什么不能直接对任意含零因子的系数环套用。[MIT，Theorem 12.11，印刷 p61](https://ocw.mit.edu/courses/res-18-012-algebra-ii-student-notes-spring-2022/mit18_702s22_full_lec.pdf#page=62)

例如 $2x+2$ 在 $\mathbb Z[x]$ 非本原，分成非单位 2 与 $x+1$；但在 $\mathbb Q[x]$ 中 2 是单位，次数一使它不可约。这正是上述等价命题需要“本原”的原因。

## 跟算与迁移题

1. 在 $\mathbb Z[i]$ 中分解 2；说明 $1+i$ 为何不可约，以及两个出现的因子是否关联。
2. $R$ 为 PID，非零非单位 $p$ 不可约。证明 $R/(p)$ 是域，并说明哪一步依赖 PID。
3. $\mathbb Z[\sqrt{-5}]$ 中从 $2\mid (1+\sqrt{-5})(1-\sqrt{-5})$ 推任一因子被 2 整除，具体错在哪里？

> [!question]- 答案
> 1. $2=(1+i)(1-i)=-i(1+i)^2$。$N(1+i)=2$ 是素整数，所以非单位分解不可能；$1-i=-i(1+i)$，两个因子关联。这不是两个不同不可约因子的分解反例。
> 2. 任何严格包含 $(p)$ 的理想 $I$ 在 PID 中为 $(d)$。$p\in(d)$，故 $p=dc$；不可约性使 $d$ 单位或 $c$ 单位。$c$ 单位会使 $(d)=(p)$，违反严格包含；所以 $d$ 单位，$I=R$。因此 $(p)$ 极大，[[数学/25-高等代数/12-环理想商环与同态基本定理#素理想、极大理想的判别|极大理想的商为域]]。依赖 PID 的是把任意理想 $I$ 写成 $(d)$；一般整环只能知道 $(p)$ 在主理想中极大。
> 3. 推理偷偷使用了“不可约即素”；本环中 2 虽不可约却不素。若直接约去等式两侧的同一非零元素则仍然合法，二者不是同一个操作。

[[数学/25-高等代数/81-有限群与因子分解复算|复算实验]] 用精确整数与有理数核对 Gaussian 除法、内容乘法和范数反例；它只核对受限案例，不证明一般 PID 或 UFD。[[数学/25-高等代数/17-群环域结构综合题与反例|综合题]] 接着练习如何在给定对象中选择正确的结构工具。
