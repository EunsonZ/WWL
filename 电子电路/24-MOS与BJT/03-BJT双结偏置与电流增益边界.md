---
stage: 1
aliases:
  - BJT双结四工作区
sources:
  - https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/3824f86399fb8b38742c5777fafb181e_MIT6_012S09_lec17.pdf
  - https://ocw.mit.edu/courses/6-720j-integrated-microelectronic-devices-spring-2007/b38a609859a68fb34543a85a7007c219_lecture36.pdf
  - https://www.onsemi.com/download/data-sheet/pdf/2n3904-d.pdf
prerequisites:
  - "[[电子电路/20-器件与模拟/01-PN结与二极管工作点]]"
---
# BJT双结偏置与电流增益边界

为什么两只背靠背二极管不能代替一只晶体管？关键在两结之间的薄基区：一结注入的少子能穿过基区，被另一结收集。只有检查两个结的偏置，才能判断这件事是否成立。

基础入口：画B、E、C电位并计算$V_{BE},V_{BC}$，从表中选区。深入入口：把发射端注入与集电端反向注入叠加，用Ebers–Moll电流守恒解释四区。两入口汇入同一端口约定：本页$I_C,I_B,I_E$都取**流入器件**为正，所以$I_C+I_B+I_E=0$。NPN有源时通常$I_C,I_B>0,I_E<0$，不是三个正大小相加。

## 双结决定工作区

|NPN区域|$V_{BE}$|$V_{BC}$|机制与允许的近似|
|---|---|---|---|
|截止|负或不足以产生明显注入|负或不足以产生明显注入|两结无明显正注入，仍有漏电；不是$I_C$数学恒零|
|正向有源|正偏|反偏|E向B注入电子，C侧电场收集；可在低注入范围近似$I_C=\beta_F I_B$|
|饱和|正偏|正偏|两端都向B注入少子，存储增加；不能沿用正向有源$\beta_F$|
|反向有源|反偏|正偏|C承担注入、E承担收集；通常$\beta_R\ne\beta_F$|

边界0 V是结偏置正负分类；电流显著与否还取决于$U_T,I_S$和应用尺度。PNP用$V_{EB},V_{CB}$判断正偏，其常规电流方向相反。NPN符号发射极箭头B→E向外，PNP E→B向内；箭头位于E，不能据引线画在上/下判断。[MIT6.012 L17，印刷3–7页](https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/3824f86399fb8b38742c5777fafb181e_MIT6_012S09_lec17.pdf)。

$V_{CE}=V_{BE}-V_{BC}$，因此单测$V_{CE}=0.3$ V不足以保证有源。例如$V_B=.7,V_E=0,V_C=.3$ V，$V_{BE}=.7,V_{BC}=.4$，两个结均正偏，已经饱和；“.2 V门槛”只是某些指定测试电流下的工程近似。

## 从少子梯度到正向有源电流

设NPN基区均匀p型、宽$W_B$远小于扩散长度，低注入、无明显基区复合、BE结面积$A_E$。边界少子浓度近似$n_B(0)=n_{B0}e^{V_{BE}/U_T}$、$n_B(W_B)\approx0$（强反偏收集近似），扩散方程给近似线性分布。电子传统电流密度$J_n=qD_n dn/dx<0$，故流入C的电流
$$I_C\simeq-qA_E D_n\frac{dn}{dx}=\frac{qA_ED_nn_{B0}}{W_B}e^{V_{BE}/U_T}=I_Se^{V_{BE}/U_T}.$$
$q$单位C、$A_E$ m²、$D_n$ m²/s、$n_{B0}$ m⁻³、$W_B$ m，乘积为A。基极还供给向E的空穴注入及复合电流，所以$I_B$不为0。令$\alpha_F=I_C/(-I_E)$，则由守恒
$$\beta_F=I_C/I_B=\frac{\alpha_F}{1-\alpha_F}.$$
即使$\alpha_F=.99$看似接近1，$\beta_F=99$；小的传输损失变化会显著改变$\beta_F$。基区宽度、掺杂、复合、温度与注入水平影响它，不能将一个手册典型值当常数。[MIT6.012 L17，印刷9–13页](https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/3824f86399fb8b38742c5777fafb181e_MIT6_012S09_lec17.pdf)。

## 两端注入的统一电流账本

定义$f=e^{V_{BE}/U_T}-1$、$r=e^{V_{BC}/U_T}-1$，两者无量纲，$I_S>0$（A）、$\beta_F,\beta_R>0$无量纲。忽略Early、串联电阻、高注入、击穿与动态存储，Ebers–Moll的等价传输表示为
$$I_T=I_S(f-r),\qquad I_B=I_S(f/\beta_F+r/\beta_R),$$
$$I_C=I_T-I_Sr/\beta_R,\qquad I_E=-I_T-I_Sf/\beta_F.$$
相加严格为0。它可看成B→E和B→C两注入支路加C→E传输受控支路，不能只把两个二极管串起来。正向有源$f\gg1,r\simeq-1$时回到$\beta_F$；反向有源交换$f,r$后回到另一增益$\beta_R$。制造时E往往重掺杂、C承受更高反偏，所以交换E/C通常不对称。[MIT6.720 L36，36-3至36-8](https://ocw.mit.edu/courses/6-720j-integrated-microelectronic-devices-spring-2007/b38a609859a68fb34543a85a7007c219_lecture36.pdf)。

![[电子电路/80-实践/13-MOS与BJT/assets/V21-bjt-transport.svg]]

V21 BJT传输页板画上述三支路；[[电子电路/24-MOS与BJT/02-NMOS与PMOS工作区和曲线族#先固定端口符号|V21符号图]]同时画NPN/PNP箭头；图中的$V_{BE},V_{BC}$箭头是参考端点，不把正偏画成任意固定0.7 V电源。

## 工作点先验和β的反例

沿用5 V供电、$R_C=2$ kΩ、E=0，给教学$V_B=.7$ V、$I_S=10^{-15}$ A、$U_T=.026$ V、$\beta_F=100$。先按有源式算$I_C\simeq0.49266$ mA，$V_C\simeq4.0147$ V，$V_{BC}\simeq-3.3147$ V；假定有源成立。若要**另设**$I_C=1$ mA，则应取$V_{BE}=U_T\ln(10^{-3}/I_S)\simeq.718407$ V，$V_C=3$ V。`.7 V`、`1 mA`和这个$I_S,U_T$不可同时宣称是同一偏置。

若给$I_B=50$ μA而直接用$\beta_F=100$算$I_C=5$ mA，$V_C=5-(5\mathrm{mA})(2\mathrm{k}Ω)=-5$ V，显然与有源双结条件不相容。负载最多供约2.5 mA；此时应解双结模型或在指定开关设计中用饱和电压近似。强迫$\beta=I_C/I_B$是外电路所施加的比值，不是饱和器件重新出现了常数增益。[onsemi2N3904，Rev3印刷2页](https://www.onsemi.com/download/data-sheet/pdf/2n3904-d.pdf)将有源$h_{FE}$与$V_{CE(sat)}$的电流条件分别列出，本页未把其曲线数化为教学$I_S$。

四区复算`ebers`只对给定电压计算电流；有限指数域会拒绝溢出，绝不冒充包含击穿的全物理模型。高注入、早期效应及饱和存储需相应扩展。小信号$g_m,r_π$应在已验有源Q内计算，见[[电子电路/24-MOS与BJT/04-Q点偏导与实际小信号节点|从Q到节点模型]]。

## 四个理由题

1. $V_B=.6,V_E=0,V_C=.4$ V为何不是正向有源？答：$V_{BC}=+.2$ V，BC也正偏；阈值不能只看$V_{CE}$。
2. 两个独立二极管为何无法产生$\beta$？答：它们没有共享薄基区的少子传输，注入流不能被另一结收集。
3. 发射极与集电极交换为什么常能导电却增益不同？答：反向有源的注入效率、面积与掺杂不对称，$\beta_R$不同，且须另查反偏耐压。
4. 迁移：1 mA有源放大器改成大基极电流开关，为什么关断可能变慢？答：双结正偏产生额外少子存储，关断需移走；本页静态Ebers–Moll不能给存储时间。

每题2分，双结/对象1分，机制或模型边界1分。成功不是背出“.7/.2”，而是从三个实际电位算两个结电压并拒绝不自洽的假定。
