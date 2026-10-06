---
type: lesson
stage: 0
aliases:
  - 正规可分与Galois扩张
  - 分裂域判别
sources:
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=29
  - https://www.jmilne.org/math/CourseNotes/FT.pdf#page=38
prerequisites:
  - "[[数学/25-高等代数/30-Galois理论/01-代数扩张最小多项式与嵌入延拓]]"
---
# 分裂域、正规、可分与 Galois 判别

“多项式在某个域里有根”只解决存在性；Galois 理论需要知道全部共轭根是否都在，以及它们是否互异。本课把这三个问题拆开，再重新合并。

## 分裂域的构造与唯一性

对 $f\in F[x]$，分裂域 $E$ 满足两条：$f$ 在 $E[x]$ 中分成一次因子；$E$ 由这些根在 $F$ 上生成。存在性可逐根构造：若 $f$ 尚未分裂，取一个不可约因子 $g$，在商域 $F[x]/(g)$ 中得到一个根，再继续；次数每次下降，所以有限步结束。

唯一性不是说两个分裂域字面相等。若 $E,E'$ 都是 $f$ 的分裂域，先把 $F$ 的恒等嵌入延拓到 $E\hookrightarrow\overline{E'}$。由于 $E$ 由 $f$ 的根生成，每个根的像仍是 $f$ 的根，全部落在 $E'$，所以像包含于 $E'$；反向同理。有限次数或“像已含生成 $E'$ 的全部对应根”给出满射，故二者在保持 $F$ 的同构意义下唯一。[Milne，第 2 章“Splitting fields”，印刷 pp.28–30](https://www.jmilne.org/math/CourseNotes/FT.pdf#page=29)

## 可分：根有没有重合

多项式 $f$ 可分，指它在分裂域中的根互不相同。计算判据是
$$f\text{ 可分}\iff \gcd(f,f')=1.$$
若 $a$ 是重根，则 $(x-a)^2\mid f$，所以 $f(a)=f'(a)=0$；反向也由带余除法或因式分解得到。不可约 $f$ 若不可分，则 $f'=0$；在特征 $p$ 中这等价于所有非零项次数被 $p$ 整除，即 $f(x)=g(x^p)$。特征 0 中非恒定不可约式导数不为零，因而都可分。

扩张 $E/F$ 可分，指每个 $\alpha\in E$ 的最小多项式可分。有限情形下，这等价于 $F$-嵌入 $E\hookrightarrow\overline F$ 的数量等于 $[E:F]$。这里补上不依赖 Artin 定理的计数：取生成塔 $F_i=F_{i-1}(\alpha_i)$。若 $E/F$ 可分，$\alpha_i$ 在 $F$ 上的最小多项式可分；它在 $F_{i-1}$ 上的最小多项式是前者在 $F_{i-1}[x]$ 中的因子，所以也可分。对 $F_{i-1}$ 的每个已得嵌入 $\tau$，简单扩张命题说它恰有 $[F_i:F_{i-1}]$ 个延拓，因为变换后的最小多项式有这么多个不同根；属于不同 $\tau$ 的延拓在 $F_{i-1}$ 上限制不同，不会重合。归纳相乘得到
$$|\operatorname{Hom}_F(E,\overline F)|=\prod_i[F_i:F_{i-1}]=[E:F].$$
反过来，若某个 $\alpha\in E$ 的最小多项式有少于其次数的不同根，则先走到 $F(\alpha)$ 时延拓选择已严格少于 $[F(\alpha):F]$，之后每层至多再乘相对次数，最终总数严格小于 $[E:F]$。故等号也迫使可分。

## 正规：共轭根有没有跑出域

代数扩张 $E/F$ 正规，指每个在 $E$ 中有一个根的 $F$-不可约多项式都在 $E$ 中完全分裂。有限扩张时，下列条件等价：

1. $E/F$ 正规；
2. 每个 $F$-嵌入 $\sigma:E\hookrightarrow\overline F$ 都满足 $\sigma(E)=E$；
3. $E$ 是某族 $F$-多项式的分裂域。

证明 $1\Rightarrow2$：若 $E=F(\alpha_1,\ldots,\alpha_r)$，每个 $\sigma(\alpha_i)$ 是同一最小多项式的根；正规性使这些根在 $E$ 中，所以 $\sigma(E)\subset E$。有限维下单射端同态必满射，故相等。证明 $2\Rightarrow1$：若不可约式 $g$ 有根 $\alpha\in E$，每个共轭根 $\beta$ 给出 $F(\alpha)\to\overline F$ 的嵌入；由有限嵌入延拓把它延到 $E$，条件 2 迫使 $\beta\in E$。证明与分裂域条件的往返，只需取生成元的最小多项式之积，并用分裂域最小性。

可分与正规相互独立：可分回答“不同根数够不够”，正规回答“这些根是否全留在域内”。[Milne，Definitions 3.6–3.7、Theorem 3.10，印刷 pp.37–39](https://www.jmilne.org/math/CourseNotes/FT.pdf#page=38)

## 有限 Galois 扩张的四种面孔

有限扩张 $E/F$ 满足以下等价条件：

- $E/F$ 正规且可分；
- $E$ 是某个可分 $F$-多项式的分裂域；
- $F$ 恰是有限群 $G\le\operatorname{Aut}(E)$ 的固定域；
- $|\operatorname{Aut}(E/F)|=[E:F]$。

前三项到固定域次数的关键不是定义变形，而是下一课的 Artin 定理。此处暂把“固定域推出次数”作为已标出的后续依赖，避免循环：我们将在证明 Artin 定理后返回并完成等价链。

## 两个贯穿例

**双二次扩张。** $E=\mathbb Q(\sqrt2,\sqrt3)$ 是 $(x^2-2)(x^2-3)$ 的分裂域；特征 0 保证可分，所以 $E/\mathbb Q$ Galois。

**三次式。** $x^3-2$ 的实根记 $\alpha$，原三次域 $\mathbb Q(\alpha)$ 可分却不正规。加入 $\omega=e^{2\pi i/3}$ 得
$$L=\mathbb Q(\alpha,\omega).$$
$\mathbb Q(\alpha)$ 是实域，$\omega\notin\mathbb Q(\alpha)$，故
$$[L:\mathbb Q]=[L:\mathbb Q(\alpha)]\,[\mathbb Q(\alpha):\mathbb Q]=2\cdot3=6.$$
$L$ 包含三个互异根 $\alpha,\omega\alpha,\omega^2\alpha$，是可分式的分裂域，因此 Galois。

## 正特征的两种失败不能混在一起

令 $F=\mathbb F_p(t^p)$、$E=\mathbb F_p(t)$。$t$ 的最小多项式是 $x^p-t^p=(x-t)^p$。它已经在 $E$ 中分裂，所以扩张正规；但只有一个不同根，故不可分。自同构必须固定 $t$，所以群平凡，而次数为 $p$。

另一方面，令 $v=u^p-u$。每个平移 $u\mapsto u+a$（$a\in\mathbb F_p$）固定 $v$，给出 $p$ 个不同的 $\mathbb F_p(v)$-自同构。一般的“自同构数不超过扩张次数”给 $[\mathbb F_p(u):\mathbb F_p(v)]\ge p$；而 $u$ 满足 $x^p-x-v$，次数又至多 $p$，所以恰为 $p$，该式就是最小多项式。其导数为 $-1$，根恰为 $u+a$，故扩张可分且正规，全部自同构正是这些平移；加法群 $(\mathbb F_p,+)\cong C_p$。这说明“特征 $p$”本身不排除 Galois；问题在具体导数和根是否齐全。

## 练习与完整答案

**题。** 设 $F$ 的特征不为 2，$a,b\in F^\times$，且 $a,b,ab$ 都不是平方。证明 $F(\sqrt a,\sqrt b)/F$ 是四次 Galois 扩张；若删去“$ab$ 不是平方”，哪一步会变？

> [!question]- 解答
> $x^2-a$ 不可约，第一层次数 2。若 $\sqrt b=r+s\sqrt a$，平方比较系数得 $2rs=0$。若 $s=0$ 则 $b$ 是平方；若 $r=0$ 则 $b/a=s^2$，从而 $ab=(as)^2$ 是平方，均矛盾。因此第二层次数 2，总次数 4。该域是 $(x^2-a)(x^2-b)$ 的分裂域；特征不为2使四个根互异，所以有限 Galois。若 $ab$ 是平方，例如 $b=ac^2$，则 $\sqrt b=c\sqrt a$ 已在第一层，次数降为2；仍可能 Galois，但不能再宣称四次或有四个独立符号变换。

下一课 [[数学/25-高等代数/30-Galois理论/03-自同构固定域与Artin定理|Artin 固定域定理]] 将补上“有限自同构群精确决定次数”的核心证明。
