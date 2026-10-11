---
domain: 物理
type: lesson
stage: 5
aliases: []
sources:
  - https://farside.ph.utexas.edu/teaching/jk1/lectures/node11.html
  - https://farside.ph.utexas.edu/teaching/em/lectures/node128.html
prerequisites:
  - "[[物理/30-电动力学/04-参考系四矢量与协变场#势、规范和 Maxwell 的统一 SI 合同]]"
  - "[[物理/30-电动力学/03-有限极化源到偶极辐射#远处功率为什么不能随时等于机械损失]]"
---

# 场动量与 Maxwell 应力

一束光被镜面反射，即使镜面没有升温，也可以受力。要算出受力的时刻与大小，只比较控制体两侧的光强还不够：波进入控制体后，需要时间走到镜面，期间动量存在场中。本页从局部平衡推到一个有限时长的反射脉冲，分别计算边界通量、场储存和物质受力，再把同一对象写成能动量张量。

## 从 Lorentz 力到局部动量账

以下是 SI 真空场，物质的电荷、电流显式计入 $\rho,\mathbf J$。延续 [[物理/30-电动力学/01-势规范与守恒源#从 Maxwell 到两个势方程|Maxwell 方程与守恒源]]，有

$$u=\frac{\epsilon_0E^2}{2}+\frac{B^2}{2\mu_0},\quad
\mathbf S=\frac{\mathbf E\times\mathbf B}{\mu_0},\quad
\partial_tu+\nabla\cdot\mathbf S=-\mathbf J\cdot\mathbf E.$$

$u$ 是 J/m³，$\mathbf S$ 是 W/m²。能量交换 $\mathbf J\cdot\mathbf E$ 不能独自给出力的方向。定义场动量密度与 Maxwell 应力

$$\mathbf g=\epsilon_0\mathbf E\times\mathbf B=\frac{\mathbf S}{c^2},$$
$$\sigma_{ij}=\epsilon_0(E_iE_j-\tfrac12\delta_{ij}E^2)
+\frac1{\mu_0}(B_iB_j-\tfrac12\delta_{ij}B^2).$$

$g$ 的单位为 kg/(m²·s)，$\sigma$ 的单位为 Pa。空间指标 $i,j=1,2,3$，$(\nabla\cdot\sigma)_i=\partial_j\sigma_{ij}$。用恒等式

$$\nabla\cdot(\mathbf E\mathbf E-\tfrac12E^2I)
=(\nabla\cdot\mathbf E)\mathbf E-\mathbf E\times(\nabla\times\mathbf E)$$

及磁场的对应式，代入 $\nabla\cdot\mathbf B=0$、$\nabla\times\mathbf E=-\partial_t\mathbf B$、$\nabla\times\mathbf B=\mu_0\mathbf J+c^{-2}\partial_t\mathbf E$，得到

$$\nabla\cdot\sigma
=\rho\mathbf E+\mathbf J\times\mathbf B
+\epsilon_0\partial_t(\mathbf E\times\mathbf B).$$

因此物质的 Lorentz 力密度满足

$$\boxed{\mathbf f=\rho\mathbf E+\mathbf J\times\mathbf B
=\nabla\cdot\sigma-\partial_t\mathbf g.}$$

对固定控制体 $V$、向外法线 $\mathbf n$ 积分，

$$\mathbf F_{\rm matter,V}=\oint_{\partial V}\sigma\mathbf n\,dA
-\frac d{dt}\int_V\mathbf g\,dV.$$

符号尤其容易误读：这里 $\sigma$ 是**应力**；把守恒式写成“储存增加 + 向外通量 = 负的物质所得”时，动量通量张量是 $\Pi=-\sigma$。对于沿 $+z$ 的真空平面波，$\sigma_{zz}=-u$，故向 $+z$ 面流出的 $z$ 动量通量为 $-\sigma_{zz}=u>0$。不要把能量通量的箭头机械复制到应力上。[Fitzpatrick 的动量守恒推导](https://farside.ph.utexas.edu/teaching/jk1/lectures/node11.html)也区分这两个符号。

这里最稳妥的物质边界是包围物体、位于真空中的积分面。若把积分面放进介质，宏观场和材料动量如何划分需另行说明；不能直接把本页 $\epsilon_0\mathbf E\times\mathbf B$ 替换成任意 $\mathbf D,\mathbf H$ 的组合而沿用全部结论。

要检查源场与已有自由场相加后如何记账，可转到 [[物理/30-电动力学/11-相容初值自由场与有源叠加#平方中的交叉项决定源功|11 的交叉项与源功]]，接着完成同页有限控制层的能量与动量收支；该平面模型按单位横截面积给出能量、动量和力。完成后返回本页的有限反射脉冲，继续使用这里的真空应力约定。

## 有限反射脉冲与表面电流

令理想导体占据 $z\ge0$、被支架固定，真空在 $z<0$。导体内部场为零，入射波沿 $+z$，电场沿 $x$。用一个有有限时间支持的实波形

$$F(\tau)=\begin{cases}\sin^2(\pi\tau),&0<\tau<1,\\0,&\text{其余},\end{cases}
\qquad \tau=t/T.$$

这里 $F$ 就是瞬时场包络的完整波形，不另乘未声明载波，平方后不加谐波平均的 $1/2$。入射与反射解为

$$\mathbf E_i=E_0F(\tau-z/cT)\hat{\mathbf x},\quad
\mathbf B_i=(E_0/c)F(\tau-z/cT)\hat{\mathbf y},$$
$$\mathbf E_r=-E_0F(\tau+z/cT)\hat{\mathbf x},\quad
\mathbf B_r=(E_0/c)F(\tau+z/cT)\hat{\mathbf y}.$$

镜面处切向 $E$ 相消、切向 $B$ 相加，满足理想导体边界。记 $F_i=F(\tau-z/cT),F_r=F(\tau+z/cT)$，则

$$u=\epsilon_0E_0^2(F_i^2+F_r^2),\quad
S_z=\epsilon_0cE_0^2(F_i^2-F_r^2),\quad \sigma_{zz}=-u.$$

电、磁能的交叉项在总能量中相消；总场的能流也恰为两束行波之差。对包住导体表面的薄盒，真空侧外法线是 $-\hat{\mathbf z}$，故镜面压力向 $+z$：

$$p_{\rm mir}(t)=2\epsilon_0E_0^2F(\tau)^2=\frac{2I_i(0,t)}c.$$

可用源力独立核对。由边界条件得到表面电流 $\mathbf K=2E_0F(\tau)\hat{\mathbf x}/\eta_0$，其中 $\eta_0=\mu_0c$。表面源所受力使用去掉自身跳变后的平均磁场 $\mathbf B_{\rm avg}=(\mathbf B_{\rm outside}+\mathbf B_{\rm inside})/2=(E_0/c)F\hat{\mathbf y}$，于是 $\mathbf K\times\mathbf B_{\rm avg}=p_{\rm mir}\hat{\mathbf z}$。若直接用外侧全场，会把自场也当外场，错误地再多一倍。

本例在横向无限延伸，**所有能量和动量都按单位面积给出**；有限时长不意味着无限平面波的总能量有限。它也可视为无侧向泄漏的理想横向周期单元。有限光束的边缘衍射、真实材料频散、支架弹性以及自由镜面的 Doppler 反冲都不在该边值问题中。

## 控制体里存下的动量不能省略

选真空薄层 $-\ell<z<0$，$\ell=cT/2$。层内没有物质源，定义 $d=\ell/(cT)=1/2$、$\zeta=z/(cT)$：

$$\frac{P_{\rm field,z}}A=\epsilon_0E_0^2T G(\tau),\qquad
G(\tau)=\int_{-d}^{0}[F(\tau-\zeta)^2-F(\tau+\zeta)^2]\,d\zeta.$$

变量代换并对积分上下限求导，

$$G'(\tau)=F(\tau+d)^2+F(\tau-d)^2-2F(\tau)^2.$$

左边界的净向内 $z$ 动量通量包含**和**：反射波携带负 $z$ 动量离开，等于控制体正 $z$ 动量增加。于是

$$\underbrace{\epsilon_0E_0^2[F(\tau+d)^2+F(\tau-d)^2]}_{\text{左边界输入}}
=\underbrace{p_{\rm mir}(t)}_{\text{右边界给镜面}}
+\underbrace{\frac d{dt}(P_{\rm field,z}/A)}_{\text{场储存变化}}.$$

在 $\tau=-1/4$，镜面还没有收到波，压力为零；左边界输入却已有 $\epsilon_0E_0^2/4$，它恰好全部成为场动量。把左边界输入直接当镜面力，会预测提前半个传播时延的受力。图中储存变化也会为负，表示原来存下的场动量正在释放，不表示能量密度为负。

![[物理/80-实践/32-场动量与多极辐射/assets/mirror-balance.svg]]

图纵轴统一除以 $\epsilon_0E_0^2$，分别画左边界输入、镜面压力和场动量变化率；下方给出同一薄层几何和波向。实践用空间数值积分求 $G$，再作时间差分，与上式三项逐时核对。

能量也有单独的收支：若 $H(\tau)=\int_{-d}^{0}(F_i^2+F_r^2)d\zeta$，则场能/面积为 $\epsilon_0E_0^2cT H$，且 $H'=F(\tau+d)^2-F(\tau-d)^2$；镜面处 $S_z=0$。固定理想镜面不吸收能量，也不移动做功，但得到冲量，并把它传给支架。

整段脉冲有 $\int_0^1\sin^4(\pi\tau)d\tau=3/8$，所以入射能量面密度与镜面冲量面密度为

$$\mathcal W_i/A=\frac38\epsilon_0cE_0^2T,\qquad
\mathcal I_z/A=\frac34\epsilon_0E_0^2T=\frac{2\mathcal W_i}{cA}.$$

取 $E_0=10^3$ V/m、$T=10$ ns，得到 $\ell\approx1.499$ m、$\mathcal W_i/A\approx9.9541$ μJ/m²、压力峰值 $17.7084$ μPa、冲量面密度 $6.64064\times10^{-14}$ N·s/m²。压力峰值、能量、冲量是三个不同量。

## 同一均匀场的能动量如何换系

沿用 [[物理/30-电动力学/04-参考系四矢量与协变场#同一均匀场和同一测试电荷|同一均匀场]] 的 $x^0=ct$、$\eta=\operatorname{diag}(1,-1,-1,-1)$ 与 $F^{0i}=-E_i/c$。能动量张量定义为

$$T^{\mu\nu}=\frac1{\mu_0}\left[-F^{\mu\alpha}F^{\nu}{}_{\alpha}
+\frac14\eta^{\mu\nu}F^{\alpha\beta}F_{\alpha\beta}\right]
=\begin{pmatrix}u&\mathbf S^T/c\\\mathbf S/c&-\sigma\end{pmatrix}.$$

它是 $4\times4$ 矩阵，各分量均为 J/m³；$T^{0i}=cg_i=S_i/c$，空间块是负应力。协变局部守恒为

$$\partial_\mu T^{\mu\nu}=-f^\nu,\qquad
f^\nu=F^{\nu\lambda}J_\lambda=(\mathbf J\cdot\mathbf E/c,\rho\mathbf E+\mathbf J\times\mathbf B).$$

零分量乘 $c$ 恢复 Poynting 定理，空间分量恢复前面的动量账。场并不单独闭合；加上交换相反的物质能动量，才得到总守恒。[能动量张量的教材推导](https://farside.ph.utexas.edu/teaching/em/lectures/node128.html)采用不同时间指标排列，比较时先换约定。

在 $S$ 中 $\mathbf E=E_0\hat{\mathbf y},B=0$，令 $u_0=\epsilon_0E_0^2/2$，则 $T=\operatorname{diag}(u_0,u_0,-u_0,u_0)$。以 $+0.6c\hat{\mathbf x}$ 被动 boost 到 $S'$，

$$T'=\Lambda T\Lambda^T,\qquad
u'=T'^{00}=2.125u_0,\quad S'_x/c=T'^{01}=-1.875u_0.$$

上式的 $u'$ 由 $E'=1.25E_0\hat y,B'=-0.75E_0\hat z/c$ 独立计算也相同，$g'_x=-1.875u_0/c$。场不变量没有改变，能量密度却改变了。这里比较同一事件的局部密度；对有限物体积分得到总四动量，还需一致的时空积分面以及支撑它的物质应力，不能把同一坐标体积内的场能随意当作孤立粒子能量。

## 角动量、反冲与迁移练习

关于固定原点的场角动量为 $\mathbf L_{\rm field}=\int_V\mathbf r\times\mathbf g\,dV$。应力对称，体积分中额外的反对称项消失，得到

$$\boldsymbol\tau_{\rm matter}
=\oint_{\partial V}\mathbf r\times(\sigma\mathbf n)\,dA
-\frac d{dt}\int_V\mathbf r\times\mathbf g\,dV.$$

这是力矩的基本计算对象；下一页 [[物理/30-电动力学/08-守恒源展开与多极辐射#功率图不能代替反冲和角动量|多极辐射]] 将说明仅有角功率为什么还不足以算角动量。

要将这个积分算到底，进入 [[物理/30-电动力学/12-多极辐射角动量通量#应力的次阶项怎样留下角动量|12 的应力次阶与全角通量]]：同一有限电／磁源分别核外部应力和内部源力矩，比较周期平均与本页瞬态储存，再检验改变力矩原点。

1. 半引导：把左边界移到 $\ell=cT$，重写 $G'$，预测最早左边界输入和最早镜面压力的时刻；镜面整段冲量改变吗？
2. 撤提示：一个固定平板把整段入射能量的比例 $R$ 反射、比例 $\mathcal T$ 透射，其余吸收。前后均为真空、垂直入射、最终邻近场储能回到初值。求平板所得冲量和热量，并检查吸收板与理想镜面两个极限。
3. 有人用本页零分量的能量定理证明“支架没有受力，因为没吸热”。指出缺少哪个可计算对象。

> [!question]- 答案和错误条件
> 1. $d=1$，$G'=F(\tau+1)^2+F(\tau-1)^2-2F(\tau)^2$；左边界最早 $t=-T$，镜面仍为 $t=0$，总冲量不变。改变控制体只改变储存项与边界传播时延。
> 2. $\mathcal I_z/A=(1+R-\mathcal T)\mathcal W_i/(cA)=[(1-R-\mathcal T)+2R]\mathcal W_i/(cA)$；在无其他机械功或储能变化的理想热吸收模型中，热量/面积为 $(1-R-\mathcal T)\mathcal W_i/A$。吸收板冲量 $\mathcal W_i/c$，镜面 $2\mathcal W_i/c$，后者热量零。这里 $R,\mathcal T$ 是整段能量比，不能未说明频散就用于瞬时幅度。吸收板的边界也不是理想导体的 $E_t=0$。
> 3. 缺少动量平衡的空间分量。固定支架可承担非零力而速度为零，因而机械功率为零；能量与动量收支互相兼容，不是互相替代。

代码、空间积分和差分结果见 [[物理/80-实践/32-场动量与多极辐射/README#反射脉冲的独立核对|本机实践]]。真实镜面或天线的温升、位移、反冲测量尚未执行。
