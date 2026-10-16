---
type: lesson
domain: mathematics
stage: 2
aliases:
  - Legendre符号与二次互反
sources:
  - https://ocw.mit.edu/courses/18-781-theory-of-numbers-spring-2012/resources/mit18_781s12_lec9/
prerequisites:
  - "[[数学/28-数论/02-同余单位与中国剩余定理]]"
---
# 二次剩余、Gauss引理与互反律

解 $x^2\equiv37\pmod{101}$，可以把101个数逐一平方。但如果问题只问有解还是无解，能否把较大的模数变小？二次互反律给出这样的交换规则；关键不是背“交换时加一个负号”，而是解释这个符号从哪里来、哪些分母不能交换。

## 对象与Euler判别：不是把Fermat倒过来用

本页p是**奇素数**。整数a的Legendre符号定义为

$$\left(\frac ap\right)=
\begin{cases}0,&p\mid a,\\1,&a\not\equiv0\pmod p\text{ 且是平方},\\-1,&\text{否则}.
\end{cases}$$

“是平方”表示存在整数x使 $x^2\equiv a\pmod p$。非零平方的每个根恰有±x两个：若 $y^2=x^2$，则 $(y-x)(y+x)=0$，在素数模域中必有一因子0；p奇且x非零使这两个根不同。因此非零平方恰有 $h=(p-1)/2$ 个，不是p−1个。

先补所需根数引理：域上的非零d次多项式至多d个不同根。d=0无根；若有根c，带余除法写 $f=(X-c)g$，其他根不等c，域中可取消 $X-c$，故它们是d−1次g的根，归纳完成。零多项式不能套该界，一般有零因子的环也不能套。

由02的Fermat，所有非零平方 $a=u^2$ 满足 $a^h=u^{p-1}=1$；它们已有h个，根数界说明 $X^h-1$ 不再有别的根。任意非零a的 $(a^h)^2=1$，同样用域的约分得 $a^h=\pm1$。所以不是平方者只能取−1，得到 **Euler判别**：

$$\boxed{a^{(p-1)/2}\equiv\left(\frac ap\right)\pmod p.}$$

p整除a时两边也0。它继而证明乘法性 $\left(\frac{ab}p\right)=\left(\frac ap\right)\left(\frac bp\right)$：分别取幂再相乘，模p相等；两边均为0或±1，p奇使所需符号可区分（零情形先单列）。这里不依赖未证明的“有限域乘法群循环”，也不是仅凭 $a^{p-1}=1$ 就认定a平方。

## Gauss引理：把一个幂变成符号翻转的次数

设 $p\nmid a$。将 $a,2a,\ldots,ha$ 各取最小正余数 $r_i\in\{1,\ldots,p-1\}$，再折回下半区间：$s_i=\min(r_i,p-r_i)\in\{1,\ldots,h\}$。记 $\nu$ 为其中 $r_i>p/2$ 的个数，即折回时改变符号的次数。

**置换是关键。** 若 $s_i=s_j$，则 $ai\equiv\pm aj$，a可逆给 $i\equiv\pm j$。i,j在1至h内，差的绝对值小于p、和最多p−1，因此只有i=j可能。h个不同的 $s_i$ 必恰为1至h的排列。相乘便有

$$a^h h!\equiv\prod_{i=1}^h r_i
\equiv(-1)^\nu\prod_{i=1}^h s_i=(-1)^\nu h!\pmod p.$$

h!可逆，取消并与Euler判别比较：

$$\boxed{\left(\frac ap\right)=(-1)^\nu.}$$

这是Gauss引理。不是“余数都不同”就够了：r本来就在1至p−1，真正要证明的是**绝对值折回后**仍无碰撞。

例 $a=3,p=7,h=3$，最小正余数为3、6、2，折回为3、1、2，只有6在上半区，所以 $(3/7)=-1$；直接非零平方集合{1,2,4}也确认无根。

## 两条补充律，与奇数floor引理

对a=−1，所有 $r_i=p-i>p/2$，所以

$$\left(\frac{-1}p\right)=(-1)^{(p-1)/2}.$$

对a=2，$r_i=2i$ 尚未越过p，超过p/2等价于 $i>p/4$，故 $\nu=h-\lfloor p/4\rfloor$。把p写为8k+1/3/5/7分别代入，ν的奇偶为偶/奇/奇/偶，得到

$$\boxed{\left(\frac2p\right)=(-1)^{(p^2-1)/8}
=\begin{cases}1,&p\equiv1,7\pmod8,\\-1,&p\equiv3,5\pmod8.\end{cases}}$$

这里的指数是整数，因为奇数p的相邻偶数p−1、p+1中一个被4整除。

接下来为互反律准备**奇a**的floor式。设a为正奇数且与p互素，写 $ai=pq_i+r_i$，$q_i=\lfloor ai/p\rfloor$。上半余数 $r_i=p-s_i$，下半余数 $r_i=s_i$，所以

$$\sum_i r_i=\sum_i s_i+\nu p-2\sum_{r_i>p/2}s_i.$$

模2后，p奇且s为1至h排列，得 $\sum_i r_i\equiv h(h+1)/2+\nu$。另一边 $\sum_i r_i=a h(h+1)/2-p\sum_i q_i$。因a奇，两个三角数项同奇偶，故

$$\nu\equiv\sum_{i=1}^h\left\lfloor\frac{ai}p\right\rfloor\pmod2,
\qquad\boxed{\left(\frac ap\right)=(-1)^{\sum_{i=1}^h\lfloor ai/p\rfloor}.}$$

奇a不能删除：a=2,p=7时floor和为0，恰巧仍正确；换p=5时floor和也0，却 $(2/5)=-1$。因此处理2必须用上面的补充律，不能把偶因子直接塞入这条floor式。

## 二次互反律：半矩形里的每个格点只归一边

设p,q为**不同的奇素数**，$h=(p-1)/2,k=(q-1)/2$。考察整数格点

$$1\le i\le h,\qquad1\le j\le k.$$

没有点落在线 $qi=pj$ 上：若相等，互素p,q使p整除i，与 $0<i<p$ 矛盾。每个点因此恰满足 $pj<qi$ 或 $qi<pj$。固定i时，前一种有 $\lfloor qi/p\rfloor$ 个j；因为 $qi/p<q/2$，不会越过k。固定j时，后一种有 $\lfloor pj/q\rfloor$ 个i，同理不越过h。所有hk个点被无遗漏、不重叠地分完，故

$$\sum_{i=1}^h\left\lfloor\frac{qi}p\right\rfloor+
\sum_{j=1}^k\left\lfloor\frac{pj}q\right\rfloor=hk.$$

分别应用刚证的奇数floor式，得到完整的 **二次互反律**

$$\boxed{\left(\frac qp\right)\left(\frac pq\right)
=(-1)^{(p-1)(q-1)/4}.}$$

只在p、q都余3模4时交换会变号；其余情况不变号。格点不是比喻：它精确记录两边的floor指数，所以直线不能穿过格点、坐标范围不能含0，都是承重条件。

![p7 q11的半矩形格点分割](assets/reciprocity-lattice.svg)

固定p=7,q=11，h=3,k=5，15点中 $7j<11i$ 的floor和为1+3+4=8，另一边为0+1+1+2+3=7，总和15。两符号分别 $(11/7)=(4/7)=1$ 与 $(7/11)=-1$，乘积−1。图中圆/方与颜色双编码两侧，点都不在线上；规范源码与实际输出在 [[数学/28-数论/80-整数同余与单位有限复算#二次剩余与Pell固定实验|复算页]]。

## 从交换符号返回实际同余

101为素数：试除不超过 $\sqrt{101}<11$ 的素数2、3、5、7均不整除。因37余1模4，

$$\left(\frac{37}{101}\right)=\left(\frac{101}{37}\right)
=\left(\frac{27}{37}\right)=\left(\frac3{37}\right)^3
=\left(\frac{37}3\right)=\left(\frac13\right)=1.$$

因此有两个根；有限逐类检查得到21、80，$21^2=441\equiv37$，另一根为−21。互反律先判存在性，找到根是下一项算法任务；本页并未给一般快速开平方算法。另一方面

$$\left(\frac7{101}\right)=\left(\frac{101}7\right)=\left(\frac37\right)=-1,$$

故 $x^2\equiv7\pmod{101}$ 无解，不必一百次试平方。若解 $Ax^2+Bx+C\equiv0\pmod p$，须先有 $p\nmid2A$ 才可完成平方，变成 $(2Ax+B)^2\equiv B^2-4AC$；判别式符号为0/1/−1分别给1/2/0个根，再乘 $(2A)^{-1}$ 返回x。p=2或A=0时须另处理，不能继续除以2A。

### 改成合数分母，会丢掉什么

Legendre分母规定为奇素数；复合奇数n可另定义Jacobi符号 $\left(\frac an\right)=\prod_{p^e\parallel n}\left(\frac ap\right)^e$，但值1不保证是模n平方。例如 $(2/15)=(2/3)(2/5)=(-1)(-1)=1$，却模3已经无平方等于2，因此模15也无解。模15的完整平方集合为{0,1,4,6,9,10}，根数也可能超过2（如1有1/4/11/14四根）。不能把素数域的根数界、±根唯一或Euler判别机械换成合数。需要时回 [[数学/28-数论/02-同余单位与中国剩余定理#整数CRT：从现有互素结论继续到兼容条件|已交CRT]] 分素数幂局部核条件；本课不证明全部合数模平方根算法。

## 撤提示迁移

1. 用Gauss引理手算 $(3/11)$，列余数与折回计数；再用互反律核符号，指出交换变号条件。
2. 判断 $x^2\equiv2\pmod{13}$ 与 $x^2\equiv-1\pmod{13}$，给可解者的两根。能否把floor奇偶公式直接用于偶数a=2？
3. 解 $x^2+3x+1\equiv0\pmod{11}$：写判别式、根与逆元；把模数改2时，原方法哪一步失效？
4. 某程序报告 $(2/15)=1$ 并宣布找到两个根，问题出在哪里？若把互反律p=q=7代入，为什么不是“正好都奇素数所以仍成立”？

### 迁移答案

1. h=5，3i的最小正余数为3、6、9、1、4；6与9超过11/2，ν=2，所以 $(3/11)=1$。互反时3、11都余3模4，$(3/11)=-(11/3)=-(2/3)=1$。
2. 13余5模8，$(2/13)=-1$，无解；13余1模4，$(−1/13)=1$，根为5、8，因为25余12。奇a的floor式不能直接用于2；p=5的明确反例已说明补充律必要。
3. 判别式 $9-4=5$，$4^2\equiv5\pmod{11}$，两平方根为4、7；$2^{-1}\equiv6$，故原式两根为 $(-3+4)\cdot6\equiv6$、$(-3-4)\cdot6\equiv2$。直接代入分别得55、11。若模2，2A=0无逆，直接枚举0、1的原式均1，所以无解，理由来自另一条路线。
4. 合数15下算的是Jacobi值，1不充分，模3就排除2；素数域“恰两根”的前提也丢失。p=q时Legendre $(p/p)=0$ 且格点线上有点，互反律要求不同素数；右侧若硬算为−1，而左侧为0，这正是去条件反例。

实际读源2026-10-17：[MIT18.781的Lecture9](https://ocw.mit.edu/courses/18-781-theory-of-numbers-spring-2012/resources/mit18_781s12_lec9/) Lemma39/40、Theorem41/42给Euler/Gauss/floor/格点路线；Euler判别本页改用根数证明，避开额外原根先修。原讲义OCR有若干符号缺失，本页按完整定义与推导核对，不复制损坏公式。继续 [[数学/28-数论/04-连分数逼近与Pell方程|连分数与Pell]]，区分局部同余可解与全局整数解；返回 [[数学/28-数论/00-数论-MOC|数论地图]]。
