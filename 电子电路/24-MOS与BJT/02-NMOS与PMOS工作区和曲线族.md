---
stage: 1
aliases:
  - MOS三极区与饱和区
sources:
  - https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/4dd0f37dcb3a9617b66b82a33894ef73_MIT6_012S09_lec09.pdf
  - https://assets.nexperia.com/documents/data-sheet/2N7002.pdf
  - https://assets.nexperia.com/documents/data-sheet/BSS84.pdf
prerequisites:
  - "[[电子电路/24-MOS与BJT/01-MOS电容与四端沟道形成]]"
---
# NMOS与PMOS工作区和曲线族

“栅已经打开”为什么还不能确定电流？栅决定沟道的电荷供给，漏源电压又改变每处剩余电荷；两者必须一起看。

基础入口：先在端口表填四个节点电压，再看曲线上每个拐点。深入入口：从局部反型电荷和漂移速度积分，检查夹断的边界。两入口在同一$V_{OV},V_{DS}$平面相遇。已有[[电子电路/20-器件与模拟/02-MOS与BJT从工作区到小信号#先看工作区，再求导|固定源体的NMOS短例]]保留1 mA入口；本页补PMOS符号、四端与推导边界。

## 先固定端口符号

|对象|常规体连接/结条件|控制量|电流参考|
|---|---|---|---|
|NMOS，p体|$V_S,V_D\ge V_B$|$V_{GS}$，$V_{DS}\ge0$，$V_{SB}\ge0$|$I_D$流入D，常规导通为正，D→S|
|PMOS，n体|$V_S,V_D\le V_B$|$V_{SG}$，$V_{SD}\ge0$，$V_{BS}\ge0$|$J=-I_D\ge0$为S→D电流大小；流入D的$I_D<0$|

四端器件符号中的体箭头沿PN结p→n的常规正向电流方向；NMOS体箭头指向沟道，PMOS从沟道指向体。三端离散符号可能把体接源、用源箭头或附体二极管；不可由屏幕上的“箭头向左/右”猜类型。V21明确画四端及体二极管方向：NMOS二极管阳极B阴极D/S，PMOS阳极D/S阴极B。按厂商封装表核脚位，电路符号位置不是TO封装脚序。[Nexperia 2N7002，印刷1–3页](https://assets.nexperia.com/documents/data-sheet/2N7002.pdf)与[BSS84，封面通知后印刷1–3页](https://assets.nexperia.com/documents/data-sheet/BSS84.pdf)支持具体离散器件极性与测试条件，未用于提取本页教学$K$。

![[电子电路/80-实践/13-MOS与BJT/assets/V21-polarity.svg]]

## 电荷沿沟道变少，电流公式随之出现

为能手算，先取长沟道、强反型、低纵向场、恒迁移率、渐变沟道、忽略串联电阻及沿沟道体效应。源为电位参考，$y=0$在S、$y=L$在D。局部电位$V(y)$由0升到$V_{DS}$，有效栅压被扣掉$V(y)$：
$$Q_n'(y)=-C_{ox}'[V_{OV}-V(y)],\quad V_{OV}=V_{GS}-V_{TH}(V_{SB}).$$
电子沿S→D漂移，但传统$I_D$沿D→S。因$Q_n'<0$，写
$$I_D=-W\mu_nQ_n'(y)\frac{dV}{dy}=W\mu_nC_{ox}'[V_{OV}-V]\frac{dV}{dy}.$$
稳态每截面电流一致，积分$I_D\int_0^Ldy=W\mu_nC_{ox}'\int_0^{V_{DS}}(V_{OV}-V)dV$，得到$K=\mu_nC_{ox}'W/L$（A/V²）及
$$I_{D0}=\begin{cases}0,&V_{OV}\le0,\\K(V_{OV}V_{DS}-V_{DS}^2/2),&0\le V_{DS}<V_{OV},\\KV_{OV}^2/2,&V_{DS}\ge V_{OV}>0.\end{cases}$$
第一行只是在此**强反型模型**里忽略弱反型电流。第二行称三极区/线性区，但整体不是线性函数；只有$V_{DS}\ll V_{OV}$时近似$I_D=KV_{OV}V_{DS}$。第三行的漏端反型电荷趋零形成夹断区，载流子仍穿越漏端耗尽区被收集；不能把“夹断”画成整个通路断电。令$V_{DS}=V_{OV}$，两行均给$KV_{OV}^2/2$，因此电流连续。[MIT6.012 L9，印刷1–5及8–14页](https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/4dd0f37dcb3a9617b66b82a33894ef73_MIT6_012S09_lec09.pdf)。

PMOS把$V_{OV,p}=V_{SG}-|V_{TH,p}|$、$V_{SD}$与$K_p>0$代入同一分段式，结果是正电流大小$J$。若需要统一流入D的电流，则$I_D=-J$，并用$V_{GS}<0,V_{DS}<0$：PMOS饱和条件$V_{SD}\ge V_{OV,p}$等价于$V_{DS}\le V_{GS}-V_{TH,p}$。不要把NMOS的不等号照搬。

## 同一电源下的两组1 mA工作点

取NMOS教学$V_{TH0}=0.5$ V、$K=2$ mA/V²、$\lambda=0$、S=B=0；G=1.5 V，D经$R_D=2$ kΩ接5 V。$V_{OV}=1$ V；先假定饱和得到$I_D=1$ mA、$V_D=5-I_DR_D=3$ V，再检查$3>1$，假定成立。

对应PMOS取$|V_{TH0,p}|=0.5$ V、同$K_p$，S=B=5 V，G=3.5 V，D经2 kΩ到地。$V_{SG}=1.5$ V，$J=1$ mA，$V_D=2$ V，$V_{SD}=3$ V满足饱和，流入D的$I_D=-1$ mA。若NMOS栅升5 mV，$I_D$精确升10.025 μA、$V_D$降20.05 mV；PMOS栅升5 mV使$V_{SG}$降，$J$降9.975 μA、$V_D$降19.95 mV。电压均反相，不能因此给PMOS的正大小跨导随便加负号。

![[电子电路/80-实践/13-MOS与BJT/assets/V21-curves.svg]]

V21曲线族每条固定一个栅过驱动，横轴是实际漏源电压；虚线标$V_{DS}=V_{OV}$。NMOS与PMOS的正大小图相同，图边给PMOS映射到有符号$I_D,V_{DS}$的方法。负载线$V_D=5-I_DR_D$只在NMOS页板的同一坐标上，Q是交点；任意曲线上的点不都是这只负载的偏置。

实际饱和电流随漏压变化。本组统一采用教学修正$I_D=I_{D0}(1+\lambda V_{DS})$，为曲线与导数连续而在两导通区都乘此因子；并非声称三极区真实器件都遵守该公式。$\lambda$单位V⁻¹。以$\lambda=.02$ V⁻¹，上述NMOS负载KCL给$V_D=3/1.04=2.884615$ V，$I_D=1.057692$ mA，仍在饱和。后续小信号、摆幅与寄生练习都回到这套参数或明确指定$\lambda=0$的对照。

## 四个理由题

1. $V_{DS}=0$且栅已强反型为什么$I_D=0$？答：有载流子但无横向驱动力，两端准费米势差为零。
2. $V_{OV}=1$ V、$V_{DS}=0.8$ V能否按饱和1 mA算？答：在三极区，实际无调制为0.96 mA；须先验区域。
3. PMOS的S=5、G=4、D=4.8 V、$V_{TH,p}=-.5$ V在哪区？答：$V_{OV,p}=.5$、$V_{SD}=.2$，三极区；流入D的$I_D<0$。
4. 迁移：把$L$减到高场器件后，为什么$K\propto1/L$不保证电流无限增大？答：恒迁移率、低场速度和一维渐变条件失效，需速度饱和、寄生及工艺模型；不能仅改$K$。

每题2分，区域/符号1分，物理理由/适用条件1分。反例是把手册$V_{GS(th)}$当“低电阻完全导通电压”：阈值在指定小电流下测量，$R_{DS(on)}$有另一个栅压和电流条件。去[[电子电路/24-MOS与BJT/04-Q点偏导与实际小信号节点|Q点偏导]]把斜率接入节点；去[[电子电路/24-MOS与BJT/05-弱反型与gm-ID取舍|弱反型]]理解截止模型遗漏的电流。
