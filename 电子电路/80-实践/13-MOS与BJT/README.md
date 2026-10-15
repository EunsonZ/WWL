---
stage: 1
aliases: []
sources:
  - https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/f539d85c15f389afd2290abfc6ca4318_MIT6_012S09_lec10.pdf
prerequisites:
  - "[[电子电路/24-MOS与BJT/01-MOS电容与四端沟道形成]]"
---
# MOS与BJT：从电荷、Q点到节点和模型边界

`transistor_lab.py`是真源，直接从目录执行；无重复代码镜像。纯导入不写文件、不建图、不启动GUI；绘图重依赖只在显式`generate(output)`后初始化。R2以独立新进程、陌生argv及全新MPLCONFIGDIR/XDG_CACHE_HOME检查模块导入和缺省输出参数，确认调用者目录及缓存目录均无新增文件。参数都是SI标量，所有DC输入先验finite real再转float；complex、bool、字符串、NaN、Inf明确拒绝。频域API返回complex，这是合法输出。教学模型不含实际器件参数提取。

在本目录，用已有Python运行：

```bash
python3 -B -m unittest -v test_transistor_lab.py
python3 -B transistor_lab.py --output /private/tmp/wwl-transistor-experiment
python3 -B build_visuals.py --output /private/tmp/wwl-transistor-visuals
```

`--output`必须由调用者指定；不提供则argparse退出2，禁止默认把计算产物写主库。重建图先输出库外，经图审查后才以精确文件清单发布到assets。`bias`二分解$[0,V_{DD}]$上电阻KCL，当前分段教学模型电流单调，故正电源/电阻下有唯一交点；最大迭代数1–10000、正电流容差、浮点停滞与预算耗尽均显式失败。返回`kcl`是A单位残差，不靠“迭代结束”冒称收敛。

|函数|对象/单位|条件及输出|
|---|---|---|
|`threshold(vsb,...)`|体偏V，γ为√V，phi2为V|vsb≥0；返回阈值V|
|`mos(vgs,vds,vsb,...)`|K A/V²，λ V⁻¹|NMOS常规vds/vsb≥0；id A、gm/gds/gmb S、region；反向与体正偏拒绝|
|`bias(vg,...)`|VDD V，RD Ω，tol A|固定S=0，解VD及局部参数；默认vsb=0|
|`ebers(vbe,vbc,...)`|Is A，UT V，β无量纲|两结模型、流入各端为正；显式限制指数≤700，不含击穿|
|`weak(vgs,vds,...)`|I0 A、n无量纲、DIBL V/V|固定体温度，vgs<有效阈值、n≥1；返回id/gm/gds及斜率V/dec|
|`moscap(psi,...)`|ψ V，NA m⁻³，Cox F/m²|仅耗尽近似psi>0；返回W m、Qd C/m²、VGB V、电容F/m²|
|`source_gain(...)`|gm/gmb/go S、rsource Ω|体交流地，源退化实际D/S节点；含go·RS项的实数增益|
|`ac_gain(f,...)`|f Hz、C F、g S、R Ω|S=B交流地，G/D两节点；返回vd/vsrc complex|

从`experiment()`先读同一Q：λ=0时1 mA/3 V，5 mV输入精确输出−20.05 mV；λ=.02时需重解Q。再独立改变γ/体偏，看固定栅压时阈值与gmb；改变weak的n/I0/漏压，看电流倍率和有限VDS项；改变AC的Cgd/Rsig/RL，看增益与相位。不同调用的默认模型条件要看表，不能把单独指定BJT电压与1 mA局部参数当同一物理Q。

测试提供另一种局部电荷积分、闭式负载交点、中心差分三偏导、MOSCAP电荷差分、BJT端流守恒/对称交换极限、弱反型decade与DIBL导数、频域独立消元，并检验无效输入和迭代失败。有限差分通过只证明指定公式的实现关系，不能替代半导体原理、真实工艺及学习效果的独立审核。

图V20是结构和电荷类型；V21是MOS/BJT符号、区域与曲线；V22是实际偏置/小信号/寄生节点；V23/V24为弱反型与频率曲线。SVG源和360/425像素PNG均由同一build脚本生成，线型与文字支持灰度阅读；结构不制造尺寸。每张图的正文位置说明了端口、变量和读图问题。

对应正文：[[电子电路/24-MOS与BJT/02-NMOS与PMOS工作区和曲线族|区域与符号]]、[[电子电路/24-MOS与BJT/03-BJT双结偏置与电流增益边界|双结区]]、[[电子电路/24-MOS与BJT/04-Q点偏导与实际小信号节点|Jacobian到实际电路]]、[[电子电路/24-MOS与BJT/05-弱反型与gm-ID取舍|效率与速度]]、[[电子电路/24-MOS与BJT/06-寄生短沟道与紧凑模型层级|拓扑与模型版本]]。

未运行SPICE/PDK/TCAD/硬件，未核真实Obsidian UI及人类学习结果。来源实读页段和复用的先前研究包见本批库外source-read-ledger；交接证据绑定精确文件hash，不是自签内容正确。
