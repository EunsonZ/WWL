---
stage: 0
aliases: []
prerequisites:
  - "[[电子电路/10-电路基础/06-从电路图到节点参考方向]]"
sources:
  - "https://www.vishay.com/docs/20035/dcrcwe3.pdf"
  - "https://www.coilcraft.com/en-us/products/power/high-voltage-inductors/xal/xal40xx/xal4020-401/"
  - "https://www.murata.com/en-us/support/faqs/capacitor/ceramiccapacitor/char/0005"
  - "https://pim.murata.com/asset/pim4/ceramicCapacitorSMD/GCM188R71H104KA57-01A-EN_PDF_CERAMICCAPACITORSMD?lastModifiedDatetime=20250813115607"
  - "https://www.murata.com/en-global/support/faqs/capacitor/ceramiccapacitor/char/0039"
---

# 真实RCL：寄生、偏置与额定条件

## 两个入口与共同问题

测量入口：标着100nF的电容为什么在高频像电感、直流偏压后又不像100nF？从真实电流路径与材料状态读起。数学入口：理想 $R,1/(j\omega C),j\omega L$ 都是有效模型，在不同频段加入最少的寄生参数再检查极限。目标是解释ESR、ESL、漏电、温漂、偏压、自谐振和额定条件各自回答什么问题。

## 电阻：电功率走向热环境

低频近似 $v=Ri$，$P=I_{rms}^2R$。材料温度改变电阻，局部线性 $R(T)=R_0[1+\alpha(T-T_0)]$，$\alpha$ 单位 $\mathrm{K^{-1}}$；100ppm/K等于 $10^{-4}K^{-1}$，不是100%。温升还使参数回头改变功耗，不能把标称R永远固定。高频引线可有串联 $L_s$，电阻两端间有并联 $C_p$，例如 $Z_R=[1/(R+j\omega L_s)+j\omega C_p]^{-1}$；这是指定拓扑的等效，不是把所有寄生永远串起来。

教学 $R_0=1k\Omega,\alpha=100ppm/K,\Delta T=50K$ 得1005Ω。施加10V时初步功率0.1W，但额定功率、最大工作电压、脉冲能量都要分别检查。devices1已读Vishay CRCW doc20035 Rev14-Apr-2026印刷1–2：0603标准 $P_{70}=0.10W$、扩展功率规格为0.125W，受膜温和PCB热环境条件约束；不能把同外形不同系列统一当同额定。这里10V算例已接近0.1W，不构成“安全余量已验证”。

## 电容：至少三条电流路径

![[电子电路/80-实践/12-半导体与真实元件/assets/real-rcl.svg]]

图中每个等效模型的外部两端标为a/b，支路共节点画圆点；端口定义 $Z=(V_a-V_b)/I_a$，$I_a$ 流入a，不需要外加激励闭环来定义两端元件。教学图中 $C$ 与漏电 $R_{leak}$ 并联，该支路再与ESR、ESL串联，端口模型
$$Z_C=R_s+j\omega L_s+\left(\frac1{R_{leak}}+j\omega C\right)^{-1}.$$
忽略漏电的频段，$Z_C\approx R_s+j(\omega L_s-1/\omega C)$，自谐振 $f_{SRF}=1/(2\pi\sqrt{L_sC})$。谐振附近阻抗约为ESR，之后感抗占优；因此更多并联大容量电容未必降低所有高频噪声，布局与反谐振同样重要。ESR耗散 $I_{rms}^2R_s$；ESL决定快沿瞬间 $L_s di/dt$；漏电决定长时间直流电荷保持，三者不可互相替代。

教学 $C=100nF,L_s=1nH,R_s=0.05\Omega,R_{leak}=1G\Omega$ 给 $f_{SRF}=15.915MHz$。1MHz时 $Z\approx0.05-j1.585\Omega$；100MHz时 $Z\approx0.05+j0.612\Omega$。$R_{leak}C=100s$ 是漏电主导的理想自放电时间常数；真实介质吸收可能导致多时间常数。全部寄生为教学参数，不是下面MLCC的厂商模型。

## 具体MLCC：标称、偏压、温度和测试幅值

Murata GCM188R71H104KA57系列的官方型号列表给标称100000pF、50Vdc、X7R、0603、±10%。官方规格的条目17–18（印刷5页，网页搜索返回的表格文本实读）在25°C、$1.0\pm0.1kHz$、$1.0\pm0.2V_{rms}$ 测电容量及DF，DF上限0.025。条目19–20（印刷6页）给室温IR大于500Ω·F、125°C大于10Ω·F，额定电压充电2min、充放电电流最大50mA。[Murata特定型号规格](https://pim.murata.com/asset/pim4/ceramicCapacitorSMD/GCM188R71H104KA57-01A-EN_PDF_CERAMICCAPACITORSMD?lastModifiedDatetime=20250813115607)

这里 $R_{IR}C_{nom}>500\Omega F$，用100nF得室温 $R_{IR}>5G\Omega$，50V对应漏电估计小于10nA；高温10Ω·F对应100MΩ、估计小于0.5μA。计算是由IR规格的推算，原手册保证项为IR，不是独立的全时间漏电保证。[Murata漏电FAQ](https://www.murata.com/en-global/support/faqs/capacitor/ceramiccapacitor/char/0039)

本作者未取得该型号完整PDF像素、DC偏压曲线或S参数，因此不能声称5V下保留多少百分比，也不能把上例1nH/0.05Ω标成它的典型值。X7R温度字母描述规定温区的无偏压温度特性，50V耐压也不保证容量不降。Class2材料的极化使偏压下局部 $C=dQ/dV$ 改变；老化、AC幅值和温度条件要一起记录。[[电子电路/22-半导体与真实元件/04-结电容存储恢复与温度#标称、Q/V与dQ/dV，三者为何不同|可积的C(V)例子]]解释定义，数值不冒充该型号曲线。这里还需实测或厂商模型补足具体频率/偏压行为。

## 电感：饱和电流与温升电流不是同一种上限

绕组有DCR，匝间并联电容 $C_p$，磁芯可有频率相关损耗。最低阶 $Z_L=[1/(R_w+j\omega L)+j\omega C_p]^{-1}$。损耗小的自谐振约 $1/(2\pi\sqrt{LC_p})$，谐振之后端口可能呈容性，不能再用 $j\omega L$。

电感为非线性时小信号 $L_{diff}=d\lambda/di$（磁链 $\lambda$ 单位Wb-turn），不是 $\lambda/i$。直流偏流令磁芯趋向饱和，局部L下降，给定电压使 $di/dt=v/L_{diff}$ 更陡；电流纹波再增加铜损和磁芯损。$I_{sat}$ 指规定下降比例、温度和测量方式的参考；$I_{rms}$ 通常指规定温升条件，不能互换为“永不损坏电流”。

devices1实际读Coilcraft XAL4020-401MEC Specifications及Notes1–6：400nH±20%在1MHz/0.1Vrms/0Adc测试，典型SRF145MHz，$I_{sat}$ 以25°C下L下降30%定义，$I_{rms}$ 依规定温升。若只做小信号400nH与145MHz的无损两参数拟合，$C_p\approx3.01pF$；这是由典型SRF反推的有效模型，未测匝间电容，亦不保证谐振峰或带外行为。实际寄生需更完整的厂商频率模型或阻抗测量。

## 从条件选择最小模型

直流分压先考虑容差、温漂与功率；秒级保电先看漏电；快沿去耦先看布局ESL与瞬态电流；开关电源电感先看偏流下L、DCR、磁芯损和温升。需要一个参数时，先找它在本工作条件的定义，再决定是否值得引入更复杂模型。[[电子电路/12-交流与变换域/02-阻抗导纳源与负载#从本构关系推导三个阻抗|阻抗与负载]]提供频域路线：这里的实部是损耗、虚部是储能相位，必须基于具体拓扑求合成，不能只比较电容标称数字。

## 理由题与迁移

1. 100MHz电容阻抗虚部为正，是否接反？答：非极性器件也可因ESL主导而呈感性；先看SRF。
2. 500Ω·F是500Ω吗？答：它是IR和标称C的乘积，需要除以F才得到Ω。
3. $I<I_{sat}$ 是否保证温升合格？答：不保证，铜损和磁芯损可先超过温升条件。
4. 迁移：把0603电阻改成另一厂商同尺寸就保留功率保证吗？答：尺寸不足以传递膜温、PCB、脉冲和电压额定条件，需新手册及安装条件。
