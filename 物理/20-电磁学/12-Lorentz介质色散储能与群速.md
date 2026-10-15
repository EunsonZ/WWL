---
type: lesson
domain: 物理
stage: 4
aliases:
  - 透明Lorentz体介质
  - 材料色散与Brillouin储能
sources:
  - https://www.feynmanlectures.caltech.edu/I_31.html
  - https://farside.ph.utexas.edu/teaching/jk1/lectures/node68.html
  - https://math.mit.edu/~stevenj/papers/Welters14.pdf
prerequisites:
  - "[[物理/20-电磁学/01-场源与守恒]]"
  - "[[物理/20-电磁学/05-波传播与平面界面]]"
  - "[[物理/30-电动力学/10-受驱散射与辐射反作用#单个振子的驱动和近似对象]]"
---

# Lorentz介质色散储能与群速

透明材料里，电场每周期都推动束缚电荷，为什么没有持续发热？因为“从场取走能量”和“把能量不可逆地变成热”是两件事。极化振子可以先存下动能、势能，再交还给场。若只把频率相关的 $\epsilon(\omega)$ 代入旧的 $\epsilon|E|^2/4$，就会漏掉这部分材料能量，也会把群速和能量输运算成两个不同答案。

[[物理/20-电磁学/06-平板导模与功率归一化#同一模式的储能、群速和端口|06 的群速核验]] 与 [[物理/20-电磁学/09-TM平板导模与界面权重#全截面储能和固定厚度的速度|09 的 TM 储能]] 先处理常材料和几何色散。本页新增均匀体介质的**材料内部动力学**：从因果响应得到本构，从振子能量推出透明储能，再独立求 $k(\omega)$ 的导数。它提供以后重建色散导模所需的材料接口；本页实际求解的是体平面波。

## 一份局域材料合同与两种时间问题

取均匀、各向同性、局域线性介质，$\mathbf D=\epsilon_0\mathbf E+\mathbf P$、$\mathbf B=\mu_0\mathbf H$，背景相对介电常数在这份卡中选为 $\epsilon_\infty=1$。极化密度 $\mathbf P$ 单位 C/m²，满足

$$\ddot{\mathbf P}+\gamma\dot{\mathbf P}+\omega_0^2\mathbf P=\epsilon_0F\mathbf E,
\qquad F>0,\quad\omega_0>0,\quad\gamma\ge0.$$

$F$ 单位 s⁻²，$\omega_0,\gamma$ 单位 s⁻¹。右侧的 $\mathbf E$ 是宏观场；这里直接指定一个现象学本构，不从稀薄原子散射推导真实致密材料的局域场修正。若另外引入 $\epsilon_\infty\ne1$，背景场储能也须同步修改。

沿用电磁学的**峰值相量**，真实场为 $\operatorname{Re}(\widehat{\mathbf E}e^{+i\omega t})$，前向空间因子为 $e^{-ikz}$。代入振子方程得

$$\widehat{\mathbf P}=\epsilon_0\chi(\omega)\widehat{\mathbf E},\qquad
\chi(\omega)=\frac{F}{\omega_0^2-\omega^2+i\gamma\omega},\qquad
\epsilon_r(\omega)=1+\chi(\omega).$$

电动力学10用 $e^{-i\omega t}$；在同一正实频率处，其被动响应要取复共轭才对应本页。换时间约定会换虚部符号，不会把吸收变成增益。[Feynman I31 §31.2–31.4](https://www.feynmanlectures.caltech.edu/I_31.html) 的振子分母与本页同号；其中 $n\simeq1+\chi/2$ 是低密度近似，本页由指定本构和 Maxwell 得 $n=\sqrt{1+\chi}$。[Fitzpatrick 的介电常数推导](https://farside.ph.utexas.edu/teaching/jk1/lectures/node68.html) 可对照完整 $\epsilon_r$，原文时间符号相反。

相量给的是单色**特解**。另一个问题是：场从有限时刻开启，材料原本不动，会怎样？对欠阻尼 $\gamma<2\omega_0$，令 $\Omega=\sqrt{\omega_0^2-\gamma^2/4}$。标量 Green 核满足 $G(0^+)=0,G'(0^+)=1$：

$$G(t)=H(t)e^{-\gamma t/2}\frac{\sin\Omega t}{\Omega},\qquad
\mathbf P(t)=\epsilon_0F\int_0^tG(t-s)\mathbf E(s)\,ds.$$

这是 $\mathbf P(0)=\dot{\mathbf P}(0)=0$ 的因果响应，不依赖未来场。把 $e^{+i\omega t}$ 代入卷积，响应变换含 $\int_0^\infty G(s)e^{-i\omega s}ds$；$\gamma>0$ 时它在频率下半平面解析，响应极点在上半平面。这是本页时间号下的因果约定。

当 $\gamma=0$，齐次振荡不衰减。比如从零初值突然施加 $E_0\cos\omega t$、$\omega\ne\omega_0$，直接解出

$$P(t)=\frac{\epsilon_0FE_0}{\omega_0^2-\omega^2}
\bigl(\cos\omega t-\cos\omega_0t\bigr),\qquad t\ge0.$$

因此不能把“运行很久”作为无阻尼单色特解的准备方法。下文的透明单色计算指已准备的特解，或远离共振的绝热准备极限；脉冲实验则保留从零态产生的全部瞬态。无阻尼共振还会产生增长特解，不在透明单色合同内。

## 场与材料先共同守恒，再谈平均储能

先用真实时域量，点乘振子方程与 $\dot{\mathbf P}/(\epsilon_0F)$：

$$u_{\rm osc}=\frac{|\dot{\mathbf P}|^2+\omega_0^2|\mathbf P|^2}{2\epsilon_0F},\qquad
\partial_tu_{\rm osc}=\mathbf E\cdot\dot{\mathbf P}
-\underbrace{\frac{\gamma|\dot{\mathbf P}|^2}{\epsilon_0F}}_{q\ge0}.$$

这是单位体积的材料动能加势能，单位 J/m³；$q$ 是热功率密度 W/m³。$\mathbf E\cdot\dot{\mathbf P}$ 可正可负，表示可逆交换，不能每一刻都叫“吸收”。

对无自由体电流的 Maxwell 方程，保留极化电流 $\dot{\mathbf P}$，真空形式的场能与 Poynting 恒等式给

$$u_0=\frac{\epsilon_0|\mathbf E|^2+\mu_0|\mathbf H|^2}{2},\qquad
\partial_tu_0+\nabla\cdot(\mathbf E\times\mathbf H)=-\mathbf E\cdot\dot{\mathbf P}.$$

两式相加消去交换项：

$$\boxed{\partial_t(u_0+u_{\rm osc})+\nabla\cdot\mathbf S=-q,\qquad
\mathbf S=\mathbf E\times\mathbf H.}$$

若把累积热也纳入账本，总账闭合。这里 $u_0$ 是真空背景场能，$u_{\rm osc}$ 是指定振子模型的能量；不可先用含材料贡献的储能权重，再额外加一次振子能量。

## Brillouin 权重是材料动能与势能的和

现在限定 $\gamma=0$、$\omega\ne\omega_0$，取准备好的单色特解。峰值相量周期平均平方产生 $1/2$，所以

$$\overline u_0=\frac{\epsilon_0|\widehat{\mathbf E}|^2+\mu_0|\widehat{\mathbf H}|^2}{4},\qquad
\overline u_{\rm osc}=\frac{(\omega^2+\omega_0^2)|\widehat{\mathbf P}|^2}{4\epsilon_0F}.$$

由 $\widehat{\mathbf P}=\epsilon_0F\widehat{\mathbf E}/(\omega_0^2-\omega^2)$，直接得到

$$\frac{d[\omega\epsilon_r(\omega)]}{d\omega}
=1+\frac{F(\omega_0^2+\omega^2)}{(\omega_0^2-\omega^2)^2}>0,$$

$$\boxed{\overline u=\overline u_0+\overline u_{\rm osc}
=\frac{\epsilon_0}{4}\frac{d(\omega\epsilon_r)}{d\omega}|\widehat{\mathbf E}|^2
+\frac{\mu_0}{4}|\widehat{\mathbf H}|^2.}$$

这就是本模型的 Brillouin 总储能。电侧导数项同时包含背景电能、振子动能、振子势能；它不是把频率相关 $\epsilon_r$ 当瞬时弹簧常数。即使某频段 $\epsilon_r<0$，这个振子总能仍为正；负介电常数不表示负材料动能。

[Welters–Avniel–Johnson，PRA 90, 023847，§II A 式(1)–(4)与§II C](https://math.mit.edu/~stevenj/papers/Welters14.pdf#page=2) 给透明窗中能流、储能和群速的条件。原文用负时间号和 Gaussian 单位；本页的 SI 系数由上面的振子能量推得。这里严格使用 $\gamma=0$ 非共振透明频带，没有把透明式当作任意有损材料的精确储能。

## 同一传播分支独立求导，才得到能量速度

在 $\epsilon_r>0$ 的无损体介质，取沿 $+z$ 的横向单行波，$\widehat{\mathbf E}=E_0\mathbf e_xe^{-ikz}$，$\widehat{\mathbf H}=nE_0\mathbf e_ye^{-ikz}/Z_0$，$Z_0=\sqrt{\mu_0/\epsilon_0}$。Maxwell 给

$$n=\sqrt{\epsilon_r},\quad k(\omega)=\frac{\omega n(\omega)}c,\quad
\overline S_z=\frac{\epsilon_0cn}{2}|E_0|^2.$$

固定 $F,\omega_0$ 求频率导数：

$$\frac{dn}{d\omega}=\frac{F\omega}{n(\omega_0^2-\omega^2)^2},\qquad
v_g=\left(\frac{dk}{d\omega}\right)^{-1}
=\frac c{n+\omega\,dn/d\omega}.$$

另一条路线用实际四项能量：磁能 $\mu_0|H|^2/4=\epsilon_0n^2|E_0|^2/4$，电侧权重为 $\epsilon_r+\omega\epsilon_r'=n^2+2\omega nn'$，故

$$\overline u=\frac{\epsilon_0n(n+\omega n')}{2}|E_0|^2,
\qquad\boxed{v_E=\frac{\overline S_z}{\overline u}=v_g.}$$

相速 $v_p=c/n$ 描述相位，$v_E$ 描述共同能量，群速描述足够窄带包络的主阶移动。等号要求局域、无损、同一可微的传播分支，包络频带远离共振与传播阈值；宽带包络仍可畸变。它没有直接测定前沿到达时间。

无损 Lorentz 卡有两个传播区：$0<\omega<\omega_0$ 与 $\omega>\omega_L=\sqrt{\omega_0^2+F}$。中间 $\omega_0<\omega<\omega_L$ 的 $\epsilon_r<0$，$k$ 为虚数；这里没有实 $n$ 的传播群速，不跨禁带连接两支图线。高频传播支可有 $n<1,v_p>c$，而完整能量账仍给 $v_E\le c$：即时 $|\mathbf S|\le c u_0\le c(u_0+u_{\rm osc})$，周期平均后也成立。

![[物理/80-实践/44-Lorentz介质色散/assets/dispersion.svg]]

两列只画实际输入的两个正介电频段，横轴 $x=\omega/\omega_0$。下排群速曲线和能量速度曲线重合，由不同计算式产生；相速在高频支超过 $c$。中间空白表示没有在共振与禁带上宣称传播分支，不能用直线把两列拼接成一份宽带群延迟。

## 完整合成卡：有限能量段与界面功率分别计量

取 $f_0=\omega_0/(2\pi)=1$ GHz，$s=F/\omega_0^2=0.5$，$\gamma=0$，$f=0.75$ GHz。体内行波峰值 $E_0=100$ V/m。横向取周期面积 $A=1$ mm²、轴向取开放控制长 $\ell=2$ mm；这不是一块有侧缘、端面反射和馈电器的有限器件。$P_{\rm flux}=A\overline S_z$，$U=A\ell\overline u$，所以 $P_{\rm flux}/(U/\ell)$ 才有速度单位。

| 同一卡的量 | 结果 |
| --- | ---: |
| $\epsilon_r,n$ | 2.14285714，1.46385011 |
| $n_g=n+\omega n'$ | 2.46763304 |
| $v_p$ | $2.04797237\times10^8$ m/s |
| $v_g=v_E$ | $1.21489886\times10^8$ m/s |
| 背景电能、磁能 | $2.21354695\times10^{-8}$、$4.74331490\times10^{-8}$ J/m³ |
| 振子动能、势能 | $3.25255879\times10^{-8}$、$5.78232673\times10^{-8}$ J/m³ |
| 总储能密度 | $1.59917474\times10^{-7}$ J/m³ |
| 控制段功率、储能 | 19.4283557 µW，$3.19834948\times10^{-16}$ J |

两端向外平均功率分别为 $-P_{\rm flux},+P_{\rm flux}$，单色无损段没有净积累。周期横向边界没有侧缘净通量。

另问相同材料与频率的**真空到半空间界面**。复用 [[物理/20-电磁学/05-波传播与平面界面#用功率核 Fresnel，而非把 t 平方当答案|05 的界面导纳]]，法向入射时 $Y_0=1/Z_0,Y=n/Z_0$，

$$r=\frac{1-n}{1+n},\quad t=\frac2{1+n},\quad R=|r|^2,\quad T=n|t|^2,\quad R+T=1.$$

默认 $R=0.03544270,T=0.96455730$。这里 $r,t$ 以界面入射电场归一，表中100 V/m则是**已指定的体内行波幅**；若要让该界面实际产生100 V/m，入射峰值须为 $100/t$。反射率不依赖这份线性卡的幅度。$T$ 是界面透入通量比，不能称为已经穿过任意有限厚样片的输出，也不对整个无限半空间积分出有限总能量。

![[物理/80-实践/44-Lorentz介质色散/assets/storage-interface.svg]]

上排每个频率保持相同体内峰值，逐项展示能量放在哪里；靠近共振的材料能量增长解释群速降低。下排是同频率半空间界面的 $R,T$；反射的变化由导纳改变产生，与材料热耗散不是同一种量。

## 有损响应：负虚部对应正热，群导数不自动是运输速度

对于 $\gamma>0,\omega>0$，$\operatorname{Im}\epsilon_r<0$。取 $n=n'-in''$、$n',n''>0$，$e^{-ikz}$ 给幅度衰减 $e^{-\omega n''z/c}$。单色平均热为

$$\overline q=\frac{\gamma\omega^2|\widehat{\mathbf P}|^2}{2\epsilon_0F}
=-\frac{\omega\epsilon_0\operatorname{Im}\epsilon_r}{2}|\widehat{\mathbf E}|^2\ge0.$$

同一源文件另扫 $\gamma/\omega_0=0.08$ 的 $x\in[0.7,1.5]$，同时输出复本构、衰减和上述两种热公式；包含吸收区却不为这些点输出透明群速或透明 $R/T$。材料时域的 $u_{\rm osc}$ 仍有确定意义，但不能把 $\partial_\omega[\omega\operatorname{Re}\epsilon_r]$ 无条件当精确有损储能。

吸收区即使算得 $[d\operatorname{Re}k/d\omega]^{-1}$ 很大或为负，也须另查波包重塑、频谱过滤和能量账；透明证明中的实 $k$、无损能量及窄带前提已变。一个导数不能据此叫能量速度或前沿速度。本文不解宽带 Maxwell 初边值传播，也没有用下一节外加局域场来验证传播前沿。

## 实际从零态驱动：功先进入哪里，脉冲后又去哪里

用有限、平滑外加电场直接驱动一个位置的极化。令 $\tau=\omega_0t$、$p=P/(\epsilon_0E_0)$、$g=\gamma/\omega_0$，$s=F/\omega_0^2$，则

$$p''+gp'+p=s e(\tau),\qquad p(0)=p'(0)=0,$$

$$e(\tau)=\begin{cases}\sin^4(\pi\tau/40)\cos[0.75(\tau-20)],&0\le\tau\le40,\\0,&\text{其他时刻}.\end{cases}$$

这里是由外部装置规定 $E(t)=E_0e(\omega_0t)$ 的局部材料响应，装置做功可以计算；未同时求 Maxwell 波从空间入口到达此处的过程。以 $\epsilon_0E_0^2$ 归一能量密度：

$$w=\frac{p'^2+p^2}{2s},\quad W(\tau)=\int_0^\tau ep'\,d\tau',\quad
Q_h(\tau)=\int_0^\tau\frac{g}{s}p'^2\,d\tau',\qquad W=w+Q_h.$$

源码实际积分到 $\tau=80$，分别运行 $g=0,0.08$，同时积累功与热。默认步长0.01，再以0.005复算最终状态及全程账本。$g=0$ 在脉冲后仍留 $w\approx1.636284916$ 的自由振荡能量；$g=0.08$ 在末时刻 $W\approx2.231549148,w\approx0.014945207,Q_h\approx2.216603942$。有损卡的输入功也改变，因为运动相位与振幅改变，不能假定两卡输入功相同后再减热。全程绝对余额最大分别约 $1.39\times10^{-10},3.15\times10^{-10}$ 个归一能量单位；这是有限步长误差诊断。

![[物理/80-实践/44-Lorentz介质色散/assets/pulse-budget.svg]]

两列的上排是同一有限驱动与两种材料响应，下排比较累计输入功、当前储能和累计热。$\tau=40$ 后驱动为零；无损列的储能保持，有损列储能转成热。材料方程从当前初值和过去驱动推进，图不含空间位置或前沿到达时间。

## 预测、反例和迁移

1. 保持 $f_0,f/f_0,E_0$，把 $s$ 从0.5改0.25。先预测主频的 $n$、材料储能与群速，再运行新卡；是否可以同时保持材料不变且人为固定 $n$？
2. 把 $E_0$ 加倍，哪些量加倍、哪些变四倍、哪些不变？若保持功率而不是保持电场，是否还可用同一答案比较储能？
3. $\gamma=0$ 时在 $f=f_0$ 宣称“等待足够长就得到稳定单色响应”；指出错误。若把频率改为禁带内、仍用实平方根与 $R+T=1$ 的传播透射式，又错在哪里？
4. 脉冲结束后看见 $W$ 不变而 $Q_h$ 继续增加，是否违反能量守恒？能否据此说一个波前已经到达这个位置？
5. 有人把旧 $\epsilon_r|E|^2/4+\mu_0|H|^2/4$ 代入默认卡。算出其速度，再解释为什么它会恰好返回相速而漏掉材料动力学。

> [!question]- 核查答案
> 1. $n$ 和四项总储能下降，群速上升；本卡具体值及新扫频条件见 [[物理/80-实践/44-Lorentz介质色散/ANSWERS#改变振子强度|答案1]]。$n$ 本来由同一 $F,\omega_0,\omega$ 决定，不能改变 $F$ 却把 $n$ 当独立固定材料参数。
> 2. $P$ 与 $H$ 振幅加倍；能量、能流、局部功与热变四倍；$n,v_p,v_g,v_E,R,T$ 不变。固定功率比较需先重定幅度，储能由 $U=P\ell/v_E$ 给出。
> 3. 无阻尼共振没有有限吸引稳态；离共振的零态齐次项也不会自动消失。禁带有倏逝场，仍需正确分支与边界；它没有此页实传播群速，不能把正 $n$ 的通量式直接搬入。
> 4. 此时材料储能减少，$w+Q_h$ 保持；局域外加驱动没有求空间传播，不能核前沿。
> 5. 旧式给 $\overline u_{\rm old}=\epsilon_0n^2E_0^2/2\approx9.48662980\times10^{-8}$ J/m³，$\overline S/\overline u_{\rm old}=c/n=v_p$。旧式把频率相关本构当成瞬时本构，缺少 $\omega\epsilon_r'$ 储能权重。

复建、输入范围与完整迁移答案见 [[物理/80-实践/44-Lorentz介质色散/README|Lorentz介质色散实践]]。回到 [[物理/20-电磁学/00-电磁学-MOC|电磁学课程地图]]；继续导模时须把材料导数带入同一模式的匹配和全截面储能。真实材料拟合、空间色散、非线性/Maxwell–Bloch、任意有损导模和宽带自洽前沿传播仍需另建模型与证据。
