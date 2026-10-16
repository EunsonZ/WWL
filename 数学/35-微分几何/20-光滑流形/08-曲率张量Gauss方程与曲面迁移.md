---
type: concept
domain: mathematics
stage: 3
aliases: []
sources:
  - https://www.maths.tcd.ie/~zaitsev/ln.pdf
  - https://www.maths.tcd.ie/~dwilkins/Courses/425/RiemGeom.pdf
prerequisites:
  - "[[数学/35-微分几何/20-光滑流形/06-Levi-Civita联络与平行移动]]"
  - "[[数学/35-微分几何/20-光滑流形/07-测地线指数映射与局部最短]]"
  - "[[数学/35-微分几何/02-参数曲面度量法向与形算子]]"
---
# 曲率：比较规则的交换误差怎样回到曲面

$\Gamma$ 可以因换图而从零变成非零，不能拿它的大小定义弯曲。把两次协变微分交换，再扣掉方向场本身不交换的误差，才得到每点真正的张量。

## 先固定号与指标

对象与正定度量沿用 [[数学/35-微分几何/20-光滑流形/06-Levi-Civita联络与平行移动|一般Levi-Civita构造]]。约定
$$R(X,Y)Z=\nabla_X\nabla_YZ-\nabla_Y\nabla_XZ-\nabla_{[X,Y]}Z,$$
并定义 $R(\partial_i,\partial_j)\partial_k=R^\ell{}_{kij}\partial_\ell$。最后两个下标是交换的微分方向，不同书会重排或取反；只抄“球曲率正”而不抄定义是不够的。

先证明它是 $(1,3)$ 型张量。把第一槽换为 $fX$，用 $[fX,Y]=f[X,Y]-Y(f)X$，两处 $Y(f)\nabla_XZ$ 抵消，余下 $fR(X,Y)Z$；第二槽由反对称同理。第三槽换成 $fZ$，二阶标量项为 $\{X(Yf)-Y(Xf)-[X,Y]f\}Z=0$，一阶的 $X(f)\nabla_YZ,Y(f)\nabla_XZ$ 成对抵消。故在三槽都 $C^\infty$ 线性，只读一点三个向量，与延拓无关。坐标代入得到
$$R^\ell{}_{kij}=\partial_i\Gamma^\ell_{jk}-\partial_j\Gamma^\ell_{ik}+\Gamma^m_{jk}\Gamma^\ell_{im}-\Gamma^m_{ik}\Gamma^\ell_{jm}. \tag{R}$$
这说明曲率只需度量至二阶导数；不是说二阶导数逐项就是曲率。

## 足够支撑截面曲率的三个恒等式

定义直接给 $R(X,Y)=-R(Y,X)$。对标量 $g(Z,W)$ 应用 $XY-YX-[X,Y]=0$，连续两次用相容性展开；交叉项 $g(\nabla_XZ,\nabla_YW)$ 与其配对抵消，留下
$$g(R(X,Y)Z,W)=-g(Z,R(X,Y)W). \tag{S}$$
这是最后两槽的反对称，关键使用度量相容。

第一Bianchi恒等式为
$$R(X,Y)Z+R(Y,Z)X+R(Z,X)Y=0.$$
因已证张量性，可在待核点把三场换成常坐标分量场，其括号为零；无挠给 $\nabla_XY=\nabla_YX$ 等。展开六个二次微分项：$\nabla_X\nabla_YZ$ 与 $-\nabla_X\nabla_ZY$ 抵消，其余两对相同。故一般成立。这个证明并不适用于任意有挠联络。

当 $n\ge2$，给二维切平面 $\Pi$ 的独立基 $X,Y$，定义
$$\boxed{K(\Pi)=\frac{g(R(X,Y)Y,X)}{g(X,X)g(Y,Y)-g(X,Y)^2}.}$$
正定性使分母严格正。若 $U=aX+bY,V=cX+dY$，$\delta=ad-bc\ne0$，前两槽反对称给 $R(U,V)=\delta R(X,Y)$；(S)给 $g(R(X,Y)V,U)=\delta g(R(X,Y)Y,X)$。因此分子乘 $\delta^2$，Gram行列式分母也乘 $\delta^2$，比值与基无关。二维流形只有整个切平面一个选择，称高斯曲率；高维通常随平面而异。一维没有二维截面，其曲率张量因前两槽反对称恒为零。

若 $g$ 换成常数倍 $c^2g$，Christoffel和 $R(X,Y)Z$ 不变，分子乘 $c^2$、分母乘 $c^4$，故 $K$ 乘 $c^{-2}$。它具有长度的负二次方单位。不定度量可能有零或负Gram，长度与局部最短不能照搬本课正定结论。

## 曲面的投影法现在来自一般唯一性

给正则嵌入曲面 $S\subset\mathbb R^3$ 的诱导度量，局部选单位法向 $n$，环境普通导数记 $D$。设 $\nabla_XY=(D_XY)^\top$。投影保联络公理；环境内积乘积法则且法向垂直切向给相容性；$D_XY-D_YX=[X,Y]$ 切向给无挠。因此由06的唯一性，这恰是诱导度量的Levi-Civita联络，而不是额外一种相近规则。

写
$$D_XY=\nabla_XY+b(X,Y)n,\quad S(X)=-D_Xn.$$
$D_Xn$ 切向，因为 $X\langle n,n\rangle=0$；微分 $\langle Y,n\rangle=0$ 得 $b(X,Y)=g(SX,Y)$，无挠给 $b$ 对称。这与 [[数学/35-微分几何/02-参数曲面度量法向与形算子#第二形式为什么给形算子|原第二形式/形算子]] 约定相同，球面外法向的主曲率是 $-1/R$。

环境平坦：$D_XD_YZ-D_YD_XZ-D_{[X,Y]}Z=0$。其切向部分逐项为
$$0=R(X,Y)Z-b(Y,Z)SX+b(X,Z)SY,$$
因为 $D_X(b(Y,Z)n)$ 的切向部分只有 $-b(Y,Z)SX$，系数导数在法向。于是得到一般曲面的 **Gauss方程**
$$g(R(X,Y)Z,W)=b(Y,Z)b(X,W)-b(X,Z)b(Y,W).$$
取 $Z=Y,W=X$，除以Gram行列式，得到 $K=\det S=k_1k_2$。左侧只用度量，右侧用嵌入；两者相等证明了Gauss卓越定理在正则曲面上的一般形式。翻法向使 $b,S$ 同时变号，$K$ 不变。抽象流形未必给了嵌入和 $S$，内在定义仍然成立。

等距微分同胚把联络拉回后仍无挠、相容，故由唯一性保联络；把曲率定义中的各项推前即保 $R$ 与 $K$。所以半径固定的球面不能与平面局部等距，因为对应点的 $K$ 分别为 $1/R^2$ 和0；圆柱 $K=0$ 却可局部展开为平面。$K=0$ 不保证整体同胚、单连通或绕数消失。

## 一般度量算例与旧球柱的准确关系

本节先用量纲一致的弧长坐标 $x$ 与半径函数 $f$ 写公式；$f=1+x^2$、$e^x$ 等具体输入均先以固定长度 $L$ 无量纲化，对应物理度量 $L^2[d\xi^2+f(\xi)^2d\theta^2]$，不是把有单位的长度直接与1相加。

在 $I\times\mathbb R$（也可将第二坐标模 $2\pi$）给
$$g=dx^2+f(x)^2d\theta^2,\qquad f\in C^\infty(I),\quad f>0.$$
从一般Christoffel式得到仅有的非零候选
$$\Gamma^x_{\theta\theta}=-ff',\qquad \Gamma^\theta_{x\theta}=\Gamma^\theta_{\theta x}=f'/f.$$
所以一般测地线在这组坐标中明确满足
$$\ddot x-ff'\dot\theta^2=0,\qquad \ddot\theta+2(f'/f)\dot x\dot\theta=0.$$
球面、圆柱的旧方程分别由上述f代入，旧曲面推导是这个一般度量方程的特例。对 $f=1+x^2$，取 $x(0)=1,\dot x(0)=0,\dot\theta(0)=1/2$，初速度平方 $0+2^2(1/2)^2=1$；方程强制 $\ddot x(0)=1,\ddot\theta(0)=0$。因此保持 $x=1$ 的坐标纬线即使按常速走，也不测地：它缺少所需的径向加速度。这里用一般初值定理保证对应真实测地线局部存在，没有假装已解出其全局轨迹。

在(R)取 $\ell=x,k=\theta,i=x,j=\theta$，有
$$R^x{}_{\theta x\theta}=-(f'^2+ff'')+f'^2=-ff'',\qquad K=-f''/f.$$
因此球面取 $f(x)=R\sin(x/R)$，$0<x<\pi R$，给 $K=1/R^2$；圆柱取 $f=R$ 给0。旧 [[数学/35-微分几何/04-曲率内外在几何与完整算例#内在曲率从度量也能算出|正交度量复算]] 是这个一般理论的两个特例，保留其空间曲线代回和全局长度比较。球极点处 $f=0$ 是该坐标失效，应换01的球面双图，不能把退化矩阵输入本页公式。

还可直接指定 $f=1+x^2$；它在整个实轴正，给 $K=-2/(1+x^2)$。无须先证明它能作为某个三维旋转曲面实现，抽象正定度量已经合法。若试用 $x$ 作旋转曲面的弧长，则轮廓半径导数必须满足 $|f'|\le1$，这里远离0处不满足；这只否定那种特定嵌入参数法，不否定度量。三维乘积度量 $dx^2+f^2d\theta^2+dz^2$ 的 $x\theta$ 平面曲率仍为上述负值，$xz$ 平面为0；“一个点只有一个曲率数”在高维已经失效。

## 从平行角接回Gauss–Bonnet

局部正交标架 $e_1=\partial_x,e_2=f^{-1}\partial_\theta$ 满足
$$\nabla e_1=\omega\,e_2,\quad\nabla e_2=-\omega\,e_1,\qquad \omega=f'\,d\theta.$$
因此 $d\omega=f''dx\wedge d\theta=-K\,dA$，其中 $dA=f\,dx\wedge d\theta$。一般标架的同一恒等式和转框 $\omega\mapsto\omega+d\lambda$ 已在 [[数学/35-微分几何/10-Gauss-Bonnet/02-联络形式结构方程与局部证明#一张符号表先锁住结构方程|原结构方程]] 完整证明，本页补上其一般联络来源。

若平行单位向量写 $V=\cos\phi\,e_1+\sin\phi\,e_2$，则 $D_tV=0$ 等价于 $\phi'+\omega(\dot\gamma)=0$。对正向矩形 $D=[a,b]\times[0,\Theta]$，取 $\Theta>0$ 且处于同一图中，四边直接积分或分片FTC给
$$\Delta\phi=-\oint_{\partial D}\omega=(f'(a)-f'(b))\Theta=\int_DK\,dA.$$
角的连续提升给一个实数，最终方向只读模 $2\pi$。$f=1+x^2,a=0,b=1,\Theta=1$ 时面积为 $4/3$、$\oint\omega=2$、平行移动转角为 $-2$ 弧度；实际同数据图与有理结果在 [[数学/35-微分几何/20-光滑流形/82-联络测地与曲率精确复算|复算页]]。若在同一点沿常值路径，移动为恒等，而沿此闭路转角非零，证明保内积不代表与路径无关。

整体Gauss–Bonnet仍由 [[数学/35-微分几何/10-Gauss-Bonnet/03-三角剖分消边与全局定理|局部到整体]] 的边界项、转角和拓扑计数完成；新曲率张量不是省掉那些前提的通行证。一般紧支撑整体Stokes已在05证明，矩形有角的这里可直接逐边FTC，不冒称05已经证明任意角点流形理论。

## 迁移题

1. 对 $g=dx^2+e^{2x}d\theta^2$ 求所有非零Christoffel与 $K$；把度量乘9后联络与曲率怎样变？
2. 在正交单位基中 $S=\mathrm{diag}(2,-3)$，求 $K$，再取 $X=2e_1,Y=e_1+e_2$ 验证分子/Gram分母。翻法向会改变什么？
3. 对 $f=1+x^2$，沿 $[0,1]\times[0,1/2]$ 正向边界平行移动，求 $\oint\omega,\Delta\phi,\int KdA$。如果反向走呢？
4. 剪切欧氏图有 $\Gamma^v_{uu}=2$，却 $R=0$；三维乘积例又在同一点有两种截面曲率。分别反驳哪两个判断？能否由 $K=0$ 推断一个完整圆柱与平面全局等距？

## 题解与回程

1. $f=e^x$，故 $\Gamma^x_{\theta\theta}=-e^{2x}$，$\Gamma^\theta_{x\theta}=\Gamma^\theta_{\theta x}=1$，其余零，$K=-1$。乘9是 $c=3$ 的常尺度变换，联络不变、曲率为 $-1/9$（恢复长度单位时再按所选尺度解释）。
2. $K=2(-3)=-6$。$b(X,X)=8,b(Y,Y)=-1,b(X,Y)=4$，分子 $-8-16=-24$；$g(X,X)=4,g(Y,Y)=2,g(X,Y)=2$，Gram分母 $8-4=4$，比值仍 $-6$。翻法向使 $S,b,k_1,k_2$ 变号，$K$ 不变。
3. $f'=2x$，右边向上贡献 $2\cdot\frac12=1$，左边为0，两水平边 $d\theta=0$；故 $\oint\omega=1,\Delta\phi=-1,\int_DKdA=-1$。反向边界的 $\oint\omega=-1$，平行角为 $+1$；若同时反转填面定向，$\int_{-D}KdA=+1$。若只反走边界而保留原填面方向，则应写 $\Delta\phi=-\int_DKdA$，不能把边界与填面方向拆开后仍声称同号。
4. 第一个反驳“Christoffel非零便曲率非零”；第二个反驳“高维一点只有一个截面曲率”。完整圆柱与平面不可能全局等距微分同胚，因为其基本群分别为 $\mathbb Z$ 和0（[[数学/36-拓扑学/10-覆盖空间与van-Kampen/00-覆盖空间与van-Kampen-MOC|覆盖空间路线]] 给绕数/提升），但都局部平坦。局部曲率数据不抹掉整体拓扑。

来源实际阅读于2026-10-17：[Zaitsev，§4.4，pp46–48，Theorem4.20](https://www.maths.tcd.ie/~zaitsev/ln.pdf) 的曲率/一般子流形Gauss方程与 [Wilkins，§4–5，尤其Gauss–Codazzi及卓越定理](https://www.maths.tcd.ie/~dwilkins/Courses/425/RiemGeom.pdf)。Zaitsev Example4.21及随后Definition4.22的槽顺序将 $R(e_1,e_2,e_1,e_2)$ 写为主曲率乘积，与其前面的(4.10)在该槽顺序不一致；本课锁定 $g(R(e_1,e_2)e_2,e_1)=k_1k_2$，按Gauss方程逐项推导，不沿用那一处符号。
