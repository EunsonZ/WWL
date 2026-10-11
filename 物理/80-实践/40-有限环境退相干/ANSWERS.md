---
type: exercise
domain: physics
stage: 2
aliases: []
sources:
  - https://www.preskill.caltech.edu/ph219/chap2_15.pdf
  - https://www.preskill.caltech.edu/ph219/chap3_15.pdf
prerequisites:
  - "[[物理/40-量子力学/18-有限环境与约化态退相干]]"
---
# 有限环境退相干：答案与独立复算接口

先写下 [[物理/80-实践/40-有限环境退相干/README#默认卡的手算检查点|默认卡]] 的预测，再展开本页。答案沿主解释的基顺序与H归一化；它是可检查的另一条推导入口，不是已运行的实验收据。

## 不调用乘积公式的一条手算与数值接口

将浴配置列成$\mathbf b=(b_1,\ldots,b_N)$，各$b_k\in\{0,1\}$，令$z_k=(-1)^{b_k}$。完整有序基的H本征角频率直接是

$$\nu_{s,\mathbf b}=\frac{(-1)^s\omega_s}{2}
 +\frac12\sum_k\omega_kz_k+\frac{(-1)^s}{2}\sum_kg_kz_k.$$

可独立构造对角矩阵或对其相位逐元素相乘，不需调用作者函数。任意全态矩阵元按

$$\rho_{s\mathbf b,s'\mathbf b'}(t)
=e^{-it(\nu_{s,\mathbf b}-\nu_{s',\mathbf b'})}
\rho_{S,ss'}(0)\rho_{E,\mathbf b\mathbf b'}(0)$$

演化，再按$(\rho_S)_{ss'}=\sum_{\mathbf b}\rho_{s\mathbf b,s'\mathbf b}$求和。两支差$\nu_{0,\mathbf b}-\nu_{1,\mathbf b}=\omega_s+\sum_kg_kz_k$，于是

$$L(t)=\sum_{\mathbf b}q_{\mathbf b}e^{-it\sum_kg_kz_k},\qquad
q_{\mathbf b}=\langle\mathbf b|\rho_E|\mathbf b\rangle.$$

它适用于本H下任意浴态，即使浴因子间有相关。逐自旋乘积浴再有$q_{\mathbf b}=\prod_k(1+r_{k,z}z_k)/2$；展开$2^N$项与乘积因子比较是独立代数核查。同一z边际并不足以确定有关联的$q_{\mathbf b}$；例如N=2，$I_4/4$与$(|00\rangle\langle00|+|11\rangle\langle11|)/2$都有每个z边际零，但前者$L=\cos(g_1t)\cos(g_2t)$，后者$L=\cos[(g_1+g_2)t]$。这两浴都对角且可分，说明“知道各自局部极化”与“假设乘积浴”是不同输入条件。

完整H是对角并不意味初始ρ也是对角。纯+x浴有大量非对角项，它们正是全态纠缠判断需要的对象；不能只保留$q_{\mathbf b}$再把全态错误替换成混对角浴。独立完整矩阵路线应从密度矩阵张量积构造初态，核其全部矩阵元、全局纯度和偏迹。

## 同一局部曲线，两个不同联合态

对于S+x和纯浴，系统本征值为$(1\pm|L|)/2$，所以$\mathcal P_S=(1+|L|^2)/2$。在L=0时局部$I/2$，全态却仍纯，可用局部熵1 bit认定S:E纯态纠缠；在|L|=1时两条件浴态只差相位，系统与浴再因子分离。

对$I/2$逐自旋混浴，各$q_{\mathbf b}=2^{-N}$，联合态是

$$\rho_{SE}(t)=2^{-N}\sum_{\mathbf b}
|\psi_{\mathbf b}(t)\rangle\langle\psi_{\mathbf b}(t)|\otimes|\mathbf b\rangle\langle\mathbf b|,$$

$$|\psi_{\mathbf b}(t)\rangle=
[e^{-it(\omega_s+B_{\mathbf b})/2}|0\rangle+
 e^{it(\omega_s+B_{\mathbf b})/2}|1\rangle]/\sqrt2.$$

这份显式非负乘积混合证明可分。因为不同浴标签正交，全局纯度为$2^{-N}$，N=4给1/16；系统局部ρ却与纯+x浴相同。可分不等于两子系统无相关，也不要求所有条件系统态互相对易；这里不把它推广为所有方向上的“无量子相关”判据。

当浴z=.8，纯$(.6,0,.8)$和混$(0,0,.8)$有相同L。混浴的单因子纯度$.82$，全局$.82^4=.45212176$；纯浴全局1。因每因子$|\cos gt-i.8\sin gt|\ge.8$，四因子模不小于.4096；这是保守下界，不表示所有因子在同一时刻同时达到下界。

当S初态混合，局部熵从0时起就可能非零。尤其$S=I/2$时，$\rho_S$始终$I/2$，且全态可写$\tfrac12\sum_s|s\rangle\langle s|\otimes U_s\rho_EU_s^\dagger$，无须浴对角即可可分。z本征系统则只有一个条件支，同样保持乘积。不能把“bath是纯态”单独当作局部混态等于纠缠的充分条件。

## 复现究竟恢复了什么

默认$g_k=.5k$ rad/μs、$t_R=2\pi$ μs时$\cos(g_kt_R)=(-1)^k$、sin零，L=1；$\rho_{01}(t_R)=c e^{-i1.3\cdot2\pi}$。恢复的是自由框架的ρ或相干模/纯度，x/y概率仍须带系统自由相位。默认S+x在这个时刻x+$\approx.345491503$，y+$\approx.975528258$，并非初值x+=1、y+=.5。浴自由相位也未同时复现，故不宣称全联合态回到初态。

仅第四g改为$\sqrt2$，原复现时前三因子相乘为1，$L=\cos(2\pi\sqrt2)\approx-.8582161857$；相干模小于1。负号是相干相位，不能把$L$的实值当成负概率。有限不共度谱仍有近似回返，找不到旧公共周期并不证明永久不可逆。

全部g减半使L的时间尺度加倍；若$\omega_s$不减半，$\rho_{01,g/2}(t)=c e^{-i\omega_st}L_g(t/2)$，不是$\rho_{01,g}(t/2)$。因此x/y曲线没有整体等比例拉伸，这正可检验是否把系统自由相位丢了。

## 共振交换的独立二乘二块

$\sigma_+=|0\rangle\langle1|$、$\sigma_-=|1\rangle\langle0|$，所以$\sigma_+\otimes\sigma_-$将$|10\rangle$送到$|01\rangle$，另一项反向。共振自由项在这两个态上均为零，按$(01,10)$基得到$\kappa X$；$(\kappa X)^2=\kappa^2I$直接给

$$e^{-it\kappa X}=I\cos(\kappa t)-iX\sin(\kappa t).$$

初|01>后的01系数cos、10系数$-i\sin$。这两个系数属于不同浴基，偏迹交叉项消失，得到对角系统态而非在系统上制造横向干涉。$p_0=\cos^2\kappa t$，$E_S=-E_E=\hbar\omega\cos(2\kappa t)/2$；总H能量与相互作用能量的期望在这个初态都为0，范数守恒。

若两份自由频率不同，块为$\begin{pmatrix}\Delta/2&\kappa\\\kappa&-\Delta/2\end{pmatrix}$，$\Delta=\omega_s-\omega_E$，转移概率变成

$$P_{01\to10}=\frac{4\kappa^2}{\Delta^2+4\kappa^2}
\sin^2\!\left(\frac{\sqrt{\Delta^2+4\kappa^2}}2t\right).$$

此项是手算迁移；当前输入只实现共振omega一值，不能改两个未实现的自由频率却继续称已跑失谐模型。真实浴能量弛豫还需更多允许模、谱、初态和极限，不能把此单浴可逆交换叫作测得T₁。

## 携带条件返回主解释

看到局部熵，先问全态是否纯；看到相干模下降，另查能量/布居；看到有限时间拟合，另查相关函数、复现和环境状态。对本纵向模型$B(t)=B$，连通相关函数恒为Var B，初始$|L|^2=1-\mathrm{Var}(B)t^2+O(t^4)$，没有自动形成指数Markov律。

回到 [[物理/40-量子力学/18-有限环境与约化态退相干#有限复现为何不等于一般不可逆|主解释的记忆反例]]，再与 [[物理/40-量子力学/17-含时微扰与黄金律的时间窗口#长时间是相对于相关时间，短时间是相对于耗尽和复现|跃迁率中间窗]] 比较。两页问不同观测、不同模型条件，不能把17的Γ贴到此处L，也不能用这组有限图认证真实器件退相干时间。
