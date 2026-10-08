---
type: lesson
stage: 0
aliases:
  - Galois根式可解判别
  - 单位根Kummer与可解群
sources:
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=46
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=75
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=77
prerequisites:
  - "[[数学/25-高等代数/30-Galois理论/05-双二次扩张与S3全部对应]]"
  - "[[数学/25-高等代数/15-有限群Cauchy与Sylow计数]]"
---
# 根式可解与 Galois 群边界

“能用根式解”不是看见某个根写成 $\sqrt[n]a$ 就结束。判别对象是多项式的**全部根**及其分裂域；从根式塔到群的正规列，还必须处理单位根、正规闭包和循环扩张。

## 定义先说清

域扩张 $R/F$ 称根式扩张，如果存在塔
$$F=F_0\subset F_1\subset\cdots\subset F_m=R,\qquad F_i=F_{i-1}(\alpha_i),\quad \alpha_i^{n_i}\in F_{i-1}.$$
多项式 $f\in F[x]$ **可由根式求解**，指存在这样的 $R$（必要时再取更大的域），使 $f$ 的分裂域包含于 $R$。这要求所有根同时落入某个有限根式塔；只写出一个根不够。

有限群 $G$ **可解**，指有次正规列
$$G=G_0\triangleright G_1\triangleright\cdots\triangleright G_m=1$$
且每个商 $G_i/G_{i+1}$ 阿贝尔。有限阿贝尔群可再细分出循环素数阶商，所以也可要求各商循环。

## 为什么先加入单位根

若 $K$ 含全部 $n$ 次单位根，$\operatorname{char}K\nmid n$，且 $a\in K$，那么 $x^n-a$ 的根是 $\alpha,\zeta_n\alpha,\ldots$。它的分裂域由一个根 $\alpha$ 生成；任一 $K$-自同构把
$$\alpha\longmapsto\zeta_n^j\alpha,$$
所以 Galois 群嵌入 $\mu_n$，是循环群（实际阶可严格小于 $n$）。若 $K$ 不含 $\zeta_n$，单纯加入 $\alpha$ 未必得到正规扩张；$x^3-2$ 正是例子，$\mathbb Q(\alpha)$ 还缺 $\omega$。

反方向需要 Kummer 结论：若 $K$ 含相应单位根，特征不整除 $n$，则次数 $n$ 的循环 Galois 扩张可写成 $K(\sqrt[n]a)$（更一般的阿贝尔指数 $n$ 扩张由若干 $n$ 次根生成）。这是本课明确使用的外部定理，证明依赖 Hilbert 90/Kummer 配对，见 Milne Proposition 5.27 与 Theorem 5.30，印刷 pp.74–76；本页不把它压成“显然”。[Milne，Kummer theory，印刷 pp.75–76](https://www.jmilne.org/math/CourseNotes/FT.pdf#page=76)

## 特征 0 的等价定理，两方向各缺什么

**定理。** 若 $\operatorname{char}F=0$，$f\in F[x]$，则 $f$ 可由根式求解，当且仅当其分裂域 $L/F$ 的 Galois 群可解。[Milne，Theorem 5.34，印刷 pp.76–77](https://www.jmilne.org/math/CourseNotes/FT.pdf#page=77)

### 可解群 $\Rightarrow$ 根式

取足够大的 $N$（例如 $(\deg f)!$），先加原始 $N$ 次单位根：$F'=F(\zeta_N)$。这是根式步骤，因为 $\zeta_N^N=1$。基域变大后，$f$ 的 Galois 群是原群的一个子群，仍可解。把其可解列细化为循环商
$$G=G_0\triangleright\cdots\triangleright G_m=1.$$
基本定理把它反转成域塔
$$F'=K_0\subset K_1\subset\cdots\subset K_m=LF',$$
其中 $K_i/K_{i-1}$ 是循环 Galois 扩张。因 $F'$ 已含所需单位根，Kummer 定理把每一层写成加入某个根式。因此 $LF'$，连同 $L$ 中所有根，都落在根式塔中。

### 根式 $\Rightarrow$ 可解群

给定一个包含全部根的根式塔，先把各步所需单位根全部加入 $F$，记所得分圆扩张为 $F'/F$；它的 Galois 群嵌入 $(\mathbb Z/N\mathbb Z)^\times$，因而阿贝尔。把根式塔与 $F'$ 合成，仍写每步为 $\alpha_i^{n_i}=a_i$，其中 $a_i$ 在前一层。

现在做正规闭包归纳。令 $N_{i-1}$ 是前 $i-1$ 层所有 $F$-共轭的合成域，已经对 $F$ 正规。对前一层的每个 $F$-嵌入 $\sigma$，在 $N_{i-1}$ 上加入
$$x^{n_i}-\sigma(a_i)$$
的全部根，并把所有这些分裂域合成得到 $N_i$。因 $N_{i-1}$ 已含所需单位根，每个分裂域的 Galois 群都嵌入循环群 $\mu_{n_i}$；合成域的群 $\operatorname{Gal}(N_i/N_{i-1})$ 嵌入这些循环群的直积，所以是阿贝尔。限制同态给出群扩张
$$1\to\operatorname{Gal}(N_i/N_{i-1})\to\operatorname{Gal}(N_i/F)\to\operatorname{Gal}(N_{i-1}/F)\to1.$$
从 $N_0=F'$ 的阿贝尔群开始归纳，$\operatorname{Gal}(N_m/F)$ 可解。分裂域 $L$ 包含在 $N_m$ 且对 $F$ 正规，限制同态把 $\operatorname{Gal}(N_m/F)$ 满射到 $\operatorname{Gal}(L/F)$；可解群的商仍可解。

“取正规闭包”不能省：原根式塔本身可能不正规，因而没有可直接套基本定理的 Galois 群。“加入单位根”也不能省：否则 $x^n-a$ 的全部共轭未必在同一层。完整正规闭包归纳见 Milne Theorem 5.34 的证明；本页给出依赖清楚的主线，不复制其全部 Kummer 技术细节。

## $x^3-2$ 为什么可解，而三次实域仍不 Galois

分裂域 $L=\mathbb Q(\alpha,\omega)$ 的群为 $S_3$，有正规列
$$S_3\triangleright A_3\triangleright1,$$
商分别为 $C_2,C_3$，所以群可解。根式表达中 $\alpha=\sqrt[3]2$ 给一个根，乘 $\omega,\omega^2$ 才给另外两个根。$\mathbb Q(\alpha)$ 非正规与“方程可由根式解”完全相容：判别看的是分裂域的群，不是单根域的自同构群。

## 五次方程的准确说法

不存在适用于所有一般五次方程的统一根式公式，因为存在 Galois 群为 $S_5$ 的五次式，而 $S_5$ 不可解；关键群论依赖是 $A_5$ 非阿贝尔单群（本课程未重证其单纯性）。这不表示每个五次式都不可用根式解：$x^5-2$ 的根为 $\zeta_5^k\sqrt[5]2$，显然在 $\mathbb Q(\zeta_5,\sqrt[5]2)$ 中，其群是可解的半直积的子群。

## 正特征边界

特征 $p$ 中，$x^p-t$ 满足导数 0，加入 $\alpha=t^{1/p}$ 是根式步骤，却有
$$x^p-t=(x-\alpha)^p.$$
扩张纯不可分、没有 $p$ 个不同共轭，自同构群平凡。这里“根式步骤给循环 Galois 层”的论证彻底失效；而且特征 $p$ 中不存在非平凡的 $p$ 次单位根，因为 $x^p-1=(x-1)^p$。

若只讨论**可分**多项式并对指数与特征作合适限制，可以建立正特征版本；次数为 $p$ 的循环扩张通常由 Artin–Schreier 方程 $x^p-x-a$ 描述，而不是 Kummer 的 $x^p-a$。因此本页的双向定理明确限定特征 0，不把正特征反例藏进脚注。

## 练习与完整答案

**题。** 判断以下推理哪里成立、哪里缺条件：

1. $x^4-2$ 的根都可由根式写出，所以其 Galois 群可解。
2. $f$ 有一个根落在根式扩张中，所以 $f$ 可由根式求解。
3. 有限 Galois 群阿贝尔，所以分裂域可由**仅一步**加入一个根式得到。

> [!question]- 解答
> 1. 成立于特征0。全部根是 $\pm\sqrt[4]2,\pm i\sqrt[4]2$，落在 $\mathbb Q(i,\sqrt[4]2)$；由定理群可解。仅写 $\sqrt[4]2$ 时仍要补 $i$ 才覆盖分裂域。
> 2. 对任意可约多项式不成立。取 $f=(x-1)g$，其中 $g$ 是一个 Galois 群为 $S_5$ 的不可解五次式；根 $1$ 已在底域（当然也在根式扩张中），但 $g$ 的根没有全部进入任何根式塔，所以 $f$ 不可由根式求解。若额外假设 $f$ 在特征0上不可约，则结论反而成立：一个根位于根式塔时，对该塔做上文的单位根扩充与正规闭包会带入这个根的全部 $F$-共轭，也就是 $f$ 的全部根；对应 Galois 群因此可解。
> 3. 若“仅一步”指 $L=F(\alpha)$ 且 $\alpha^n\in F$，结论不成立。取 $L=\mathbb Q(\sqrt2,\sqrt3)$：它是 $(x^2-2)(x^2-3)$ 的分裂域，次数为 $4$，独立变换两个平方根的符号给出阿贝尔群 $C_2\times C_2$，且 $L$ 全实、正规。若 $L=\mathbb Q(\alpha)$、$\alpha^n=a\in\mathbb Q$，则 $\alpha$ 的四个共轭都实且都满足 $t^n=a$；奇数次该方程只有一个实根，偶数次至多两个，矛盾。这里并不否定两层根式塔 $\mathbb Q\subset\mathbb Q(\sqrt2)\subset L$；例如 $\beta=\sqrt2+\sqrt3$ 甚至是原始元，却不是纯根式生成元。
>
> 正确替代是：在特征 $0$ 下有限阿贝尔群可解，所以分裂域**包含于**某个有限根式塔。有限阿贝尔群先分解或细化成循环商；给底域加入足够单位根后，Kummer 才把各循环 Galois 层实现为根式。若不加入单位根，即使 $x^3-a$ 的一个根已在，另外两个根也可能不在。

本路线到此把“扩张—嵌入—固定域—基本定理—根式边界”接完。有限例的机械核对见 [[数学/25-高等代数/30-Galois理论/80-Galois对应有限复算|复算页]]；它不替代本页使用的 Kummer 外部定理。
