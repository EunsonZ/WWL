---
type: lesson
domain: mathematics
title: Banach对偶与序列空间
aliases:
  - 序列空间的全部连续线性读数
stage: 3
sources:
  - https://terrytao.wordpress.com/2009/01/26/245b-notes-6-duality-and-the-hahn-banach-theorem/
  - https://ocw.mit.edu/courses/18-102-introduction-to-functional-analysis-spring-2021/pages/lecture-notes-and-readings/
prerequisites:
  - "[[数学/16-数学分析/17-函数空间范数完备性与紧性]]"
  - "[[数学/16-数学分析/19-Hilbert投影与Riesz表示的证明]]"
  - "[[数学/16-数学分析/20-泛函分析/05-Hahn-Banach延拓与凸集分离]]"
---
# Banach 对偶与序列空间

> 一份信号能接受多少种稳定的线性读数？知道每个坐标上的读数，就一定知道整个信号上的读数吗？

有限维中线性读数总是一行系数乘向量；无限维要同时检查级数收敛、所选范数与有限支撑的密度。对 $1\le p<\infty$，$\ell^p$ 的连续对偶确实仍由系数列完整描述；到了 $\ell^\infty$，存在所有单坐标都看不见的连续读数。失败点在密度，不能把无穷序列当成一张行数稍多的表格。

## 连续对偶是“同一个输入范数”允许的全部读数

固定实数域或复数域 $\mathbb K$。对赋范空间 $X$，

$$X^*=\{\varphi:X\to\mathbb K:\varphi\text{ 线性且连续}\},\qquad
\|\varphi\|=\sup_{\|x\|\le1}|\varphi(x)|.$$

由 [[数学/16-数学分析/20-泛函分析/02-开映射与有界逆定理#对象：上界、下界与两个方向的稳定性|有界等价于连续]]，这就是满足某个统一 $|\varphi(x)|\le C\|x\|$ 的线性读数。复空间中这里“线性”总是复线性，故 $\varphi(ix)=i\varphi(x)$。全部代数线性泛函构成更大的代数对偶，本课不把未证连续的泛函自动收进 $X^*$。

这一定义依赖范数。例如 $c_{00}$ 上的总和 $s(x)=\sum x_n$ 在 $\ell^1$ 范数下有范数1；在 $\ell^2$ 范数下，取前 $N$ 项都为 $1/\sqrt N$，则输入范数1而读数 $\sqrt N$，所以不连续。没有先说允许什么误差，就没有说清“稳定测量”。

### 为什么即使 X 未完备，对偶也完备

取 $X^*$ 中的范数 Cauchy 列 $\varphi_n$。对每个固定 $x$，

$$|\varphi_n(x)-\varphi_m(x)|\le\|\varphi_n-\varphi_m\|\|x\|,$$

所以标量列 Cauchy，定义 $\varphi(x)=\lim_n\varphi_n(x)$。有限和与标量乘法可穿过标量极限，故 $\varphi$ 线性；Cauchy 列范数有公共上界 $C$，所以 $|\varphi(x)|\le C\|x\|$。最后给定 $\varepsilon>0$，选 $N$ 使 $m,n\ge N$ 时 $\|\varphi_n-\varphi_m\|\le\varepsilon$，固定 $n$ 后令 $m\to\infty$，得

$$|(\varphi_n-\varphi)(x)|\le\varepsilon\|x\|\quad\text{对所有 }x.$$

取单位球上确界得到 $\|\varphi_n-\varphi\|\le\varepsilon$。因此 $X^*$ 是 Banach 空间；这里需要标量域完备，没有使用 $X$ 完备。

## Hahn–Banach 怎样保证读数足以辨认向量

对任意 $x\ne0$，先在一维子空间 $\mathbb Kx$ 上定义 $f(\alpha x)=\alpha\|x\|$。它的范数是1，由 [[数学/16-数学分析/20-泛函分析/05-Hahn-Banach延拓与凸集分离#保范数版本与复数域重建|保范数延拓]] 得 $\varphi_x\in X^*$ 满足

$$\|\varphi_x\|=1,\qquad\varphi_x(x)=\|x\|.$$

因此 $x\ne y$ 时对 $x-y$ 作此构造，便有连续读数能区分它们。等价地，

$$\|x\|=\sup_{\|\varphi\|\le1}|\varphi(x)|.$$

此处对**固定向量** $x$ 的读数上确界能被某个 $\varphi_x$ 取到；它不意味着每个固定 $\varphi$ 都在单位球上取得自身范数。后面的 $\ell^1$ 例将明确区分这两个量词。

定义 $X^{**}=(X^*)^*$ 和自然映射

$$J:X\to X^{**},\qquad (Jx)(\varphi)=\varphi(x).$$

$Jx$ 对 $\varphi$ 线性，$|(Jx)(\varphi)|\le\|x\|\|\varphi\|$；上面的定理给反向范数不等式，所以 $\|Jx\|=\|x\|$。$J$ 也是线性、单射。若 $X$ Banach，则 $J(X)$ 完备，因而在 $X^{**}$ 中闭：像内收敛列拉回是 Cauchy，极限仍来自 $X$。这些不说明 $J$ 满射；“反身”专指该自然映射满射，其与弱紧性的完整关系见 [[数学/16-数学分析/20-泛函分析/09-弱星紧性与反身空间#反身性：自然嵌入满射恰好对应闭球弱紧|自然嵌入与反身性]]。[MIT 18.102 Lecture 6](https://ocw.mit.edu/courses/18-102-introduction-to-functional-analysis-spring-2021/resources/mit18_102s21_lec06/) 的双对偶部分对应这个接口。

对任意子空间 $M\subset X$，限制映射 $R:X^*\to M^*$、$R\varphi=\varphi|_M$ 线性且范数至多1；Hahn–Banach 说它满射，并能为每个读数找到同范数原像，不说原像唯一。两个延拓之差在 $M$ 上为0，也由连续性在 $\overline M$ 上为0；$M$ 稠密时唯一性成立。这个区别将解释为什么有限坐标有时足够、有时不够。

## 先处理复共轭：对偶配对不一定是内积

本课用**系数配对**

$$\varphi_a(x)=\sum_{n\ge1}a_nx_n.$$

它对 $a$ 和 $x$ 都线性，因此 $a\mapsto\varphi_a$ 可以作为复线性同构。若偏好数学内积形式，令 $y_n=\overline{a_n}$，则

$$\varphi_a(x)=\sum_nx_n\overline{y_n}=\langle x,y\rangle\quad(p=2).$$

这与 [[数学/16-数学分析/19-Hilbert投影与Riesz表示的证明#Riesz 表示：每个连续线性读数都是一个内积|第一变量线性的 Riesz 表示]] 完全一致，但 $y\mapsto\langle\cdot,y\rangle$ 是共轭线性，不是复线性。两种记号都可用，不能一面省略系数共轭，一面又把它叫相同的 Riesz 向量。例如 $\varphi(z)=iz$ 的系数是 $a=i$，Riesz 向量却是 $y=-i$。

## 有限支撑的密度：坐标证据能否决定全部读数的闸门

记 $c_{00}$ 为有限支撑序列，$P_Nx=(x_1,\ldots,x_N,0,\ldots)$。$1\le p<\infty$ 时，

$$\|x-P_Nx\|_p^p=\sum_{n>N}|x_n|^p\to0,$$

所以 $c_{00}$ 在 $\ell^p$ 中稠密。若 $\varphi$ 连续，令 $a_n=\varphi(e_n)$，则

$$\varphi(x)=\lim_N\varphi(P_Nx)=\lim_N\sum_{n=1}^Na_nx_n.$$

这已经给出唯一可能的系数；尚需证明它属于正确的 $\ell^q$、级数绝对收敛以及范数恰好相等。

在 $\ell^\infty$ 中，$\|\mathbf1-P_N\mathbf1\|_\infty=1$，有限支撑不稠密。其闭包恰为 $c_0=\{x:x_n\to0\}$：$c_0$ 中截断的一致误差趋零；反过来有限支撑列的一致极限在充分靠后的坐标上一致很小，所以也趋零。每个坐标都知道，不等于每个连续读数都知道。

## 一般定理：1＜p＜∞ 时全部对偶恰是 ℓq

设 $1<p<\infty$，$q=p/(p-1)$。**定理：** 每个 $\varphi\in(\ell^p)^*$ 唯一写成 $\varphi_a$，其中 $a\in\ell^q$，且 $\|\varphi_a\|=\|a\|_q$；系数映射为线性等距同构。

先给一个 $a\in\ell^q$。由 [[数学/16-数学分析/17-函数空间范数完备性与紧性#Hölder 与 Minkowski 的机制|Hölder 不等式]] 的计数测度版本，

$$\sum_n|a_nx_n|\le\|a\|_q\|x\|_p.$$

所以级数绝对收敛，定义有界线性泛函且 $\|\varphi_a\|\le\|a\|_q$。对 $a\ne0$，定义（$a_n=0$ 时令 $x_n=0$）

$$x_n=\frac{\overline{a_n}}{|a_n|}\frac{|a_n|^{q-1}}{\|a\|_q^{q-1}}.$$

因 $(q-1)p=q$，$\sum|x_n|^p=1$，且

$$\varphi_a(x)=\frac{\sum|a_n|^q}{\|a\|_q^{q-1}}=\|a\|_q.$$

这既证明范数相等，也证明每个非零泛函在单位球上取到范数。零泛函范数为0，任一单位向量都取到0。

反向取任意 $\varphi\in(\ell^p)^*$，设 $a_n=\varphi(e_n)$。对每个 $N$ 记 $S_N=\sum_{n=1}^N|a_n|^q$，取有限支撑测试向量

$$z_n=\begin{cases}\overline{a_n}|a_n|^{q-2},&n\le N,\ a_n\ne0,\\0,&\text{其他}.
\end{cases}$$

即 $z_n$ 的相位抵消 $a_n$ 的相位，模长为 $|a_n|^{q-1}$；分开零值避免 $q<2$ 时出现未定义的负次幂。于是

$$S_N=\varphi(z)\le\|\varphi\|\|z\|_p=\|\varphi\|S_N^{1/p}.$$

若 $S_N=0$，$S_N^{1/q}\le\|\varphi\|$ 显然；否则可除以 $S_N^{1/p}$，得到同一不等式。单调令 $N\to\infty$，得 $a\in\ell^q$ 且 $\|a\|_q\le\|\varphi\|$。前述 Hölder 构造给连续的 $\varphi_a$；它与 $\varphi$ 在每个 $e_n$、从而在 $c_{00}$ 上相同，由稠密性在整个 $\ell^p$ 上相同。唯一性也由逐个代 $e_n$ 得到，所有方向都已证明。

此外，$a^{[N]}=P_Na$ 给有限坐标读数，且

$$\|\varphi_a-\varphi_{a^{[N]}}\|=\left(\sum_{n>N}|a_n|^q\right)^{1/q}\to0.$$

这里是**读数算子范数**的收敛，含义是同一个截断对所有单位输入都准确，不只是每个固定输入最终准确。

## 端点 p＝1：全部有界系数，但最大值可能不取得

对 $a\in\ell^\infty$、$x\in\ell^1$，

$$\sum|a_nx_n|\le\|a\|_\infty\|x\|_1,$$

给 $\|\varphi_a\|\le\|a\|_\infty$。代 $x=e_n$ 得 $\|\varphi_a\|\ge|a_n|$ 对所有 $n$ 成立，取上确界便得到相等；不需要存在一个最大系数。

反过来若 $\varphi\in(\ell^1)^*$，$a_n=\varphi(e_n)$ 满足 $|a_n|\le\|\varphi\|$，故 $a\in\ell^\infty$；再由有限支撑密度得到 $\varphi=\varphi_a$。因此

$$\boxed{(\ell^1)^*\cong\ell^\infty,\qquad\|\varphi_a\|=\sup_n|a_n|.}$$

非零 $a$ 的泛函在单位球上取得范数，当且仅当存在某个坐标满足 $|a_n|=\|a\|_\infty$。有这样的坐标时，取相位相消的单坐标单位向量即可。反之，若所有系数都严格小于 $M=\|a\|_\infty$，任何 $\|x\|_1=1$ 都满足

$$\sum_n(M-|a_n|)|x_n|>0,$$

因为至少一项 $|x_n|>0$，该项损失为正。故 $|\varphi_a(x)|\le\sum|a_nx_n|<M$。

例如 $a_n=1-1/n$ 有上确界1却不取到，所以 $\|\varphi_a\|=1$，没有单位向量取等；$\varphi_a(e_n)\to1$ 只提供逼近。它不违反前面 Hahn–Banach 的“对每个固定 $x$ 可以另选一个读数取得 $\|x\|$”：这次是把读数固定住，量词已换。

端点还改变截断行为：$\|\varphi_a-\varphi_{P_Na}\|=\sup_{n>N}|a_n|$，只有 $a\in c_0$ 时趋零。取 $a=\mathbf1$，则对每个 $x\in\ell^1$，部分和都趋于总和，却始终有读数范数误差1。这与紧算子课“逐向量和统一”的区别是同一个量词问题。

## 同一局部测量进入对偶表

上一课在 $M=\operatorname{span}\{e_1\}$ 上标定 $f(te_1)=t$。现在可列出不同空间中的全部保范数延拓：

| 输入空间 | 对偶系数范数 | 保持原范数1且 $a_1=1$ 的条件 |
|---|---|---|
| $\ell^1$ | $\|a\|_\infty$ | 其余系数任意满足 $|a_n|\le1$，不唯一 |
| $\ell^2$ | $\|a\|_2$ | 其余系数必须全为0，唯一 |
| $\ell^p,\ 1<p<\infty$ | $\|a\|_q$ | 其余系数必须全为0，唯一 |

例如有限两坐标系数 $(1,i)$ 在 $\ell^1$ 上增益为1，在 $\ell^2$ 上增益为 $\sqrt2$；同一个读数 $x_1+ix_2$，换输入误差球就换最坏增益。实轴标定不能擅自替复读数确定相位；必须明确原子空间对哪个数域线性。

## 为什么 ℓ∞ 的对偶严格大于 ℓ1

每个 $a\in\ell^1$ 都定义 $\ell^\infty$ 上的连续读数 $\varphi_a(x)=\sum a_nx_n$，上界为 $\|a\|_1\|x\|_\infty$。当 $a\ne0$ 时，取每个非零坐标的 $x_n=\overline{a_n}/|a_n|$（其余取0），得到范数1的有界序列且 $\varphi_a(x)=\sum|a_n|$；零系数的结论直接成立，故这是 $\ell^1\hookrightarrow(\ell^\infty)^*$ 的线性等距嵌入。

要证明它不满射，不必描述整个庞大对偶。令 $c\subset\ell^\infty$ 是所有收敛序列，定义

$$L:c\to\mathbb K,\qquad L(x)=\lim_{n\to\infty}x_n.$$

极限运算使它线性，$|L(x)|\le\|x\|_\infty$，常数列 $\mathbf1$ 取等，故 $\|L\|=1$。Hahn–Banach 给同范数延拓 $\Lambda:\ell^\infty\to\mathbb K$。特别地

$$\Lambda(e_n)=0\quad(\forall n),\qquad\Lambda(\mathbf1)=1.$$

若存在 $a\in\ell^1$ 使 $\Lambda(x)=\sum a_nx_n$ 对全部有界序列成立，逐个代 $e_n$ 强迫所有 $a_n=0$，再代 $\mathbf1$ 却应得1，矛盾。因此该自然嵌入严格不满。这个构造与 [Tao 245B Notes 6 的 generalized limit 段](https://terrytao.wordpress.com/2009/01/26/245b-notes-6-duality-and-the-hahn-banach-theorem/) 相对应。

失败机制非常具体：$c_{00}$ 只在 $c_0$ 中稠密；$\Lambda$ 可以在整个 $c_0$ 上为0，却在 $\mathbf1$ 上非零。若误将 $\mathbf1$ 视为其有限截断在一致范数中的极限，便会得到“连续泛函把0变成1”的假矛盾；实际截断误差一直是1。

这里的 $\Lambda$ 不是“所有序列通常意义的极限”：普通极限仍对振荡序列不存在。定理也未给出算法或唯一值，不能从这一步额外声称延拓具有移位不变性；具有额外条件的 Banach limit 是更专门的对象。本课只需要这组明确的值来证明 $\ell^1$ 不是全部对偶。

## 点值、有限坐标、加权和与极限各自看见什么

$\ell^p$ 是实际序列空间，坐标评价 $\delta_k(x)=x_k$ 连续、范数1。有限坐标读数是它们的有限线性组合；无穷加权和何时连续由上述 $\ell^q$ 条件决定；$\Lambda$ 则是 $\ell^\infty$ 上超出这类加权和的存在例。

函数空间不能机械照搬“点值”。$C([0,1])$ 配一致范数时，$f\mapsto f(t)$ 连续且范数1。$L^2(0,1)$ 的元素按几乎处处相等取等价类，单点值根本不由等价类确定；即使只在连续函数子空间先定义点值，取在固定内部点高1、支集宽趋零的三角峰，其 $L^2$ 范数趋零而该点读数仍为1，也说明它不连续。因此不能请求 Hahn–Banach 将这个点值作为有界 $L^2$ 读数延拓；缺的是原始有界性。

物理中也要区分“线性幅读数”和“概率”。到 [[物理/40-量子力学/02-态算子测量与二态相干#内积约定先接上现有数学|二态的内积接口]]，固定归一探测方向 $\phi$，$\psi\mapsto\langle\phi|\psi\rangle=\langle\psi,\phi\rangle_{数学}$ 是范数1的复线性泛函；这正对应本页 $\ell^2$ 配对及系数共轭。返回同页的 Born 规则时，概率是幅的模平方，纯态期望一般是二次型，不能把它们也叫对 $\psi$ 线性。HB 延拓保证某种线性读数的数学存在，不生成新的可实现测量装置或测量公理。

## 两道撤去提示的迁移题

**题一。** 同一个系数列 $a_n=n^{-1/2}$，分别能否在 $\ell^1,\ell^2,\ell^4$ 上定义连续读数 $\sum a_nx_n$？若只观察前 $N$ 个坐标，误差是否在全部单位输入上一致趋零？

> [!question]- 答案
> $\ell^1$ 的对偶是 $\ell^\infty$，$a$ 有界且范数1；尾部最大系数 $(N+1)^{-1/2}\to0$，故此例有限坐标读数在算子范数下收敛。$\ell^2$ 需要 $a\in\ell^2$，但 $\sum1/n$ 发散，所以不连续；$\ell^4$ 需要 $a\in\ell^{4/3}$，但 $\sum n^{-2/3}$ 发散，也不连续。不能只用“每项系数趋零”判定后两者。有限支撑测试向量已给出增益无界：将主证明中 $z^{[N]}$ 归一化，读数分别为 $(\sum_{n\le N}n^{-1})^{1/2}$ 与 $(\sum_{n\le N}n^{-2/3})^{3/4}$，都发散；因此不存在一致误差控制的全空间有界读数可供逼近。

**题二。** 两个连续泛函在每个 $e_n$ 上都相同，能否断言它们相同？分别判断 $\ell^p$（$1\le p<\infty$）、$c_0$ 和 $\ell^\infty$。再判断：有限坐标读数能否在算子范数下逼近上述 $\Lambda$？

> [!question]- 答案
> 前两种可以：差在 $c_{00}$ 为0，有限支撑在指定范数中稠密，连续性延到全空间。$\ell^\infty$ 不可以，$\Lambda$ 与零泛函在所有 $e_n$ 上相同，却对 $\mathbf1$ 不同。
>
> 若 $\psi_N$ 只依赖前 $N$ 坐标，取 $x^{(N)}=(0,\ldots,0,1,1,\ldots)$，则 $\|x^{(N)}\|_\infty=1$、$\psi_N(x^{(N)})=0$，而该列收敛到1，$\Lambda(x^{(N)})=1$。所以 $\|\Lambda-\psi_N\|\ge1$，不可能算子范数逼近。更一般任意有限坐标集合也可在这些坐标设0、其余设1得到同样结论。

本课识别的是序列空间上的连续对偶；[[数学/16-数学分析/20-泛函分析/10-Lp对偶表示与测度条件|Lp 对偶课]] 将单坐标测试换成区域示性输入，经有限正 RN、复测度桥梁及 σ有限拼接证明连续场的表示。弱/弱星拓扑与反身性由 [[数学/16-数学分析/20-泛函分析/08-弱拓扑弱星拓扑与收敛|后续两课]] 接续：先按测试对象定义拓扑，再判断双对偶球中的极限能否回到原空间。一般对偶识别、复数约定和极限延拓的重要性高，需要非作者核对；有限系数例已精确算完，无需让数值模拟替无穷量词签字。
