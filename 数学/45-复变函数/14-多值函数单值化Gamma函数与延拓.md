---
type: lesson
domain: mathematics
course: 复变函数
level: undergraduate
revision: 2
reviewed: 2026-09-05
tags:
  - mathematics/complex
  - mathematics/core
---

# 多值函数单值化Gamma函数与延拓

## 把多值现象放到更合适的空间

沿闭路解析延拓 $\sqrt z$ 一圈会换号，两圈才回来。与其强迫它在去零平面单值，不如把两个切开平面的边交叉粘合成两层 Riemann 曲面。对数需要无限层，绕一圈上升 $2\pi i$。曲面上的函数可单值，投影到原平面才表现为多值。

这里的曲面不是任意三维图像，而是局部有复坐标、坐标转换全纯的一维复流形。具体平方根曲面可用关系 $w^2=z$ 表示，参数 $w$ 在分支点也能作为好的曲面坐标。把分支点一概叫“本性奇点”会混淆定义域与函数奇性。

## Gamma 函数怎样从积分延伸到整个平面

当 $\operatorname{Re}z>0$，定义
$$\Gamma(z)=\int_0^\infty t^{z-1}e^{-t}\,dt,$$
这里 $t>0$ 使用实对数。零端由 $t^{\operatorname{Re}z-1}$ 可积控制，无穷端由指数衰减控制；在右半平面紧集上，对参数导数出现的 $\log t$ 幂仍可支配，所以函数全纯。

分部积分得 $\Gamma(z+1)=z\Gamma(z)$，并有 $\Gamma(1)=1$，故 $\Gamma(n+1)=n!$。递推式用来定义左侧延拓：$\Gamma(z)=\Gamma(z+1)/z$。逐步向左得到亚纯函数，在 $0,-1,-2,\ldots$ 有简单极点，留数为 $(-1)^n/n!$。对负整数不能把 Gamma 当成有限阶乘值。

## Beta 积分解释反射公式的来源

对 $\operatorname{Re}a,\operatorname{Re}b>0$，绝对收敛允许对两份 Gamma 积分用换元 $s=ru,t=r(1-u)$，Jacobian 为 $r$，得到
$$B(a,b)=\int_0^1u^{a-1}(1-u)^{b-1}\,du=\frac{\Gamma(a)\Gamma(b)}{\Gamma(a+b)}.$$
取 $b=1-a$、$0<\operatorname{Re}a<1$，再令 $u=x/(1+x)$，转为 $\int_0^\infty x^{a-1}/(1+x)\,dx$。钥匙孔围道给出 $\pi/\sin\pi a$，所以
$$\Gamma(a)\Gamma(1-a)=\frac\pi{\sin\pi a}.$$
随后由亚纯恒等定理延拓到允许的其他点。这个推导把实二重积分、换元、分支和留数连接起来，不是孤立背诵特殊函数恒等式。

## 无穷乘积如何指定零点

一个简单非平凡例子是
$$\frac1{\Gamma(z)}=ze^{\gamma z}\prod_{n=1}^{\infty}\left(1+\frac zn\right)e^{-z/n},$$
其中 $\gamma$ 为 Euler 常数。因 $\log(1+z/n)-z/n=O_K(n^{-2})$ 在固定紧集上成立，适当避开有限个零点后尾部对数一致收敛，这说明补偿因子为何必要；裸乘积通常发散。该具体乘积可由 Gamma 的 Euler 有限乘积极限推出，完整推导列为进阶阅读。

Weierstrass 分解定理与 Mittag–Leffler 定理分别解决“给定离散零点”与“给定离散主部”的全局构造，需要收敛修正，而不是任意把无穷多局部表达相加相乘。离散点集在域内部无聚点是关键前提。本节给出概念桥梁，不声称已证明两项一般构造定理。

## 自测与解答

求 $\Gamma(1/2)$ 与 $\operatorname{Res}(\Gamma,-2)$，并说明两个结果各依赖什么。

> [!question]- 解答
> 实积分中令 $t=u^2$，$\Gamma(1/2)=2\int_0^\infty e^{-u^2}\,du=\sqrt\pi$，使用已证明的 Gaussian 积分。递推延拓给出 $\Gamma(z)=\Gamma(z+3)/[z(z+1)(z+2)]$，在 $z=-2$ 留数为 $\Gamma(1)/[(-2)(-1)]=1/2$。前者是正半轴积分，后者是局部亚纯行为，不能在负参数处直接使用原积分定义。

## 继续学习

前一节：[[数学/45-复变函数/13-Schwarz引理正规族与Riemann映射|Schwarz引理正规族与Riemann映射]]。

课程地图：[[数学/45-复变函数/00-复变函数-MOC|复变函数课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/46-数理方程/13-Bessel-Legendre函数与正交展开|Bessel-Legendre函数与正交展开]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Jiří Lebl：Guide to Cultivating Complex Analysis，作者开放教材](https://www.jirka.org/ca/)
- [Juan Ponce Campuzano：Complex Analysis，作者开放教材](https://complex-analysis.com/)
