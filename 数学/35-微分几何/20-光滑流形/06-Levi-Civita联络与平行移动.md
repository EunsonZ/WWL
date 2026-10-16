---
type: concept
domain: mathematics
stage: 3
aliases: []
sources:
  - https://www.maths.tcd.ie/~zaitsev/ln.pdf
  - https://math.stanford.edu/~conrad/diffgeomPage/handouts/linearode.pdf
prerequisites:
  - "[[数学/35-微分几何/20-光滑流形/02-切向量余切与坐标变换]]"
  - "[[数学/35-微分几何/20-光滑流形/04-定向单位分解与流形积分]]"
---
# Levi-Civita联络：不同点的方向怎样比较

在同一点，切向量可以相加；两个不同点的切空间没有天然的“相同分量”。把曲面上的空间导数投影回切平面是一个好办法，但抽象流形未必已经嵌在三维空间。需要先从度量本身构造一个坐标无关的比较规则，再证明原投影法恰好是它。

## 对象、类型与单位

以下 $M$ 是无边界、Hausdorff、第二可数的有限维实 $C^\infty$ 流形，$g$ 是**光滑正定**对称二阶协变张量。[[数学/35-微分几何/20-光滑流形/04-定向单位分解与流形积分#bump与单位分解的一般存在证明|单位分解]] 已证明这种度量存在；这里只研究给定的一个 $g$。边界可研究其内部或另作延拓，但局部初值定理不保证测地线永远留在带边区域。

记 $\mathfrak X(U)$ 为局部光滑向量场；所有构造与限制到更小开集相容。坐标 $x^i$ 下 $\partial_i=\partial/\partial x^i$，重复上下指标从 $1$ 到 $n$ 求和，$g^{ij}$ 是矩阵 $g_{ij}$ 的逆，并非逐项倒数。Lie括号是导子的交换子：
$$[X,Y]f=X(Yf)-Y(Xf),\qquad [X,Y]^k=X^i\partial_iY^k-Y^i\partial_iX^k.$$
二阶偏导项抵消，所以它仍是向量场；$[fX,Y]=f[X,Y]-Y(f)X$、$[X,fY]=f[X,Y]+X(f)Y$ 直接由乘积法则得到。交换子展开也给 Jacobi 恒等式。

公式本身不预设坐标量纲。若 $[x^i]=U_i$、长度单位为 $L$，则 $[g_{ij}]=L^2/(U_iU_j)$，$[\Gamma^k_{ij}]=U_k/(U_iU_j)$。后面的图与程序把所有长度除以选定 $L$、坐标和参数作无量纲数；恢复尺度时长度乘 $L$，截面曲率乘 $L^{-2}$。弧长坐标与角坐标的量纲不能混用。

## 联络的公理为什么多一项

联络 $\nabla_XY\in\mathfrak X(U)$ 对两个场实双线性，满足
$$\nabla_{fX}Y=f\nabla_XY,\qquad \nabla_X(fY)=X(f)Y+f\nabla_XY.$$
第一槽只读当前方向，第二槽还要读被微分场的变化。设 $\nabla_{\partial_i}\partial_j=\Gamma^k_{ij}\partial_k$，公理强制
$$(\nabla_XY)^k=X^i\partial_iY^k+\Gamma^k_{ij}X^iY^j.$$
因此 $\nabla_XY(p)$ 一般不只由 $X(p),Y(p)$ 决定。两个联络的差 $A(X,Y)=\nabla_XY-\widetilde\nabla_XY$ 却在两槽都 $C^\infty$ 线性，因为 $X(f)Y$ 抵消；$A$ 是 $(1,2)$ 型张量。挠率
$$T(X,Y)=\nabla_XY-\nabla_YX-[X,Y]$$
同样是张量，在坐标中为 $(\Gamma^k_{ij}-\Gamma^k_{ji})X^iY^j\partial_k$。

令旧坐标 $x=x(y)$，新基 $\bar\partial_b=(\partial_bx^i)\partial_i$。把这两个新基代入联络公理，导数同时作用在分量和旧基上，再写 $\partial_k=(\partial y^a/\partial x^k)\bar\partial_a$，得到
$$\bar\Gamma^a_{bc}=\frac{\partial y^a}{\partial x^k}\left(\Gamma^k_{ij}\frac{\partial x^i}{\partial y^b}\frac{\partial x^j}{\partial y^c}+\frac{\partial^2x^k}{\partial y^b\partial y^c}\right).$$
第二导数项说明 $\Gamma$ 不是张量。它的工作正是补偿“基在动”；删掉它再追问几何为何变了，等于拆掉秤的校准后怪物体增重。

## Koszul公式给存在与唯一

我们要求无挠 $T=0$，并要求度量相容：
$$Xg(Y,Z)=g(\nabla_XY,Z)+g(Y,\nabla_XZ).$$
对 $X,Y,Z$ 循环写三式，以前两式减第三式，用 $\nabla_XY-\nabla_YX=[X,Y]$ 消去未知项，得到
$$\begin{aligned}
2g(\nabla_XY,Z)={}&Xg(Y,Z)+Yg(Z,X)-Zg(X,Y)\\
&-g(X,[Y,Z])+g(Y,[Z,X])+g(Z,[X,Y]). \tag{K}
\end{aligned}$$
这是任何候选都必须满足的式子，正定性给非退化，故至多一个。存在性不能只说“倒过来定义”：必须检查右侧确实给一个场和联络。

把右侧的一半记 $B(X,Y,Z)$。将 $Z$ 换成 $fZ$，前两项额外出现 $X(f)g(Y,Z),Y(f)g(Z,X)$，第三项 $-(fZ)g(X,Y)=-fZ(g(X,Y))$ 没有 $Z(f)$ 项；括号展开的额外项恰抵消前两项，留下 $B(X,Y,fZ)=fB(X,Y,Z)$。同样展开第一、第二槽给
$$B(fX,Y,Z)=fB(X,Y,Z),\quad B(X,fY,Z)=fB(X,Y,Z)+X(f)g(Y,Z).$$
于是每点的 $B(X,Y,\cdot)$ 是余切向量，存在唯一 $\nabla_XY$ 与之配对；用逆矩阵 $g^{ij}$ 求分量说明所得场光滑，以上两恒等式给联络公理。再把(K)的 $X,Y$ 互换相减，得到
$$B(X,Y,Z)-B(Y,X,Z)=g([X,Y],Z),$$
故无挠；把 $Y,Z$ 互换相加，得到
$$B(X,Y,Z)+B(X,Z,Y)=Xg(Y,Z),$$
故度量相容。这个构造在任意开集唯一，重叠上自动相同，给全局唯一 **Levi-Civita联络**。它不要求先选定向，更不要求全局坐标。

坐标场括号为零，(K)化为
$$\boxed{\Gamma^k_{ij}=\tfrac12g^{k\ell}(\partial_i g_{j\ell}+\partial_jg_{i\ell}-\partial_\ell g_{ij}).}$$
若只要无挠，欧氏空间上任意对称 $\Gamma^k_{ij}$ 都可；只要相容，在二维欧氏空间上取 $\nabla_XY=D_XY+\alpha(X)JY$，其中 $J$ 是旋转90°、$\alpha$ 是非零一形式，仍相容，但一般有挠。两个条件共同选出唯一规则。

## 沿曲线的场，不必延成同一个全场

给光滑曲线 $\gamma:I\to M$，沿曲线的场是 $V(t)\in T_{\gamma(t)}M$。自交时同一几何点的两个参数时刻可带不同向量，未必来自单值全局场。定义
$$ (D_tV)^k=\dot V^k+\Gamma^k_{ij}(\gamma)\dot x^iV^j.$$
将 $V$ 的坐标转换求导，额外的二阶坐标导数正与上面的 $\bar\Gamma$ 补偿，故 $D_tV$ 是坐标无关的沿曲线场。若 $V=Y\circ\gamma$，它才简写为 $\nabla_{\dot\gamma}Y$。

平行条件 $D_tV=0$ 是线性系统 $\dot V^k=-\Gamma^k_{ij}\dot x^iV^j$。局部存在唯一来自 [[数学/16-数学分析/16-度量完备压缩映射与微分方程|Picard积分不动点]]；在紧参数段上取有限图段逐次延拓，系数有界，积分不等式 $|V(t)|\le |V(a)|+C\int_a^t|V|$ 给 $|V(t)|\le |V(a)|e^{C|t-a|}$，（令 $w(t)=|V(a)|+C\int_a^t|V|$，则 $w'\le Cw$，乘 $e^{-Ct}$ 积分即得该界），所以不会在图段内部爆破。可得端点间线性平行移动。反向走曲线是逆，度量相容给
$$\frac d{dt}g(V,W)=g(D_tV,W)+g(V,D_tW),$$
故平行移动保内积。它通常依赖路径；[[数学/35-微分几何/20-光滑流形/08-曲率张量Gauss方程与曲面迁移#从平行角接回Gauss–Bonnet|曲率与闭路转角]] 将给精确反例。

## 弯坐标中的直线

在欧氏平面取 $x=u,\ y=v+u^2$，则
$$g=du^2+(dv+2u\,du)^2,\quad(g_{ab})=\begin{pmatrix}1+4u^2&2u\\2u&1\end{pmatrix}.$$
旧直角坐标的 $\Gamma=0$，变换公式只留下 $\Gamma^v_{uu}=2$；其他为零。物理直线 $(x,y)=(t,0)$ 在新坐标是 $(u,v)=(t,-t^2)$：$\ddot v+2\dot u^2=-2+2=0$。物理恒定方向 $(1,0)$ 的新分量 $(1,-2t)$ 也满足 $D_tV=0$，范数始终1。坐标曲线看起来是抛物线，空间依然平坦。完整曲率核验和同数据图在 [[数学/35-微分几何/20-光滑流形/82-联络测地与曲率精确复算|复算页]]。

## 迁移题

1. 在 $x>0$ 的一维流形给 $g=x^2dx^2$，求 $\Gamma^x_{xx}$，并找使度量成为常数的坐标。能否由“$\Gamma\ne0$”判曲率非零？
2. 上述剪切图中在 $t=1$，物理恒定方向的坐标分量、普通导数、联络修正分别是什么？若错按张量规则令新 $\Gamma=0$，平行方程残差是多少？
3. 在欧氏二维定义 $\nabla_XY=D_XY+dx(X)JY$。验证相容，并算 $T(\partial_x,\partial_y)$，其中 $J\partial_x=\partial_y$。
4. 给等距微分同胚 $F:(M,g)\to(N,h)$，证明它保Levi-Civita联络和平行移动；不能仅用某张图里分量相同作理由。

## 题解与回程

1. $\Gamma=\frac12x^{-2}\partial_x(x^2)=1/x$。令 $r=x^2/2$，$dr=x\,dx$，故 $g=dr^2$；$x>0$ 上这是到 $r>0$ 的微分同胚，$\Gamma^r_{rr}=0$。一维 $R$ 由前两槽反对称恒零，非零Christoffel不能判断曲率。
2. 在 $t=1$，$V=(1,-2)$，普通导数 $(0,-2)$，联络项 $(0,2)$，总和0。错令新Christoffel零便得到残差 $(0,-2)$。这也是测地线加速度的同一抵消。
3. $J$ 对欧氏内积反伴随：$\langle JY,Z\rangle+\langle Y,JZ\rangle=0$，所以新增的两项在相容式中抵消。$T(X,Y)=dx(X)JY-dx(Y)JX$，于是 $T(\partial_x,\partial_y)=J\partial_y=-\partial_x\ne0$。只满足相容不能推出Levi-Civita。
4. 在 $M$ 上定义 $\widehat\nabla_XY=dF^{-1}(\nabla^N_{dFX}dFY)$，向量场通过微分同胚确实成为目标单值场。链式法则给联络公理，等距给相容，$dF[X,Y]=[dFX,dFY]$（在目标函数上用导子交换子即可验证）给无挠。因此由唯一性 $\widehat\nabla=\nabla^M$。由沿曲线坐标公式给 $dF(D_tV)=D_t(dFV)$，故平行移动被保持。

下一步到 [[数学/35-微分几何/20-光滑流形/07-测地线指数映射与局部最短|测地线初值与局部最短]]，再回 [[数学/35-微分几何/03-坐标变换联络与测地线#切向投影给联络|原曲面投影构造]] 看其如何由一般唯一性认证。来源实际阅读于2026-10-17：[Zaitsev，§4.2，pp41–43](https://www.maths.tcd.ie/~zaitsev/ln.pdf) 给联络/相容/坐标公式与投影连接；本页另用完整Koszul构造证明坐标无关存在性。[Conrad，Linear ODE，§2–3](https://math.stanford.edu/~conrad/diffgeomPage/handouts/linearode.pdf) 支持沿曲线线性系统的存在延拓。来源不替代本文展开。
