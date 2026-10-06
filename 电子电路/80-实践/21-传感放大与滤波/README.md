---
type: lab
domain: 电子电路
stage: 2
content_status: usable
evidence_status: partial
aliases:
  - 传感放大与滤波CPU复算
sources:
  - https://www.ti.com/lit/an/snoa515a/snoa515a.pdf
  - https://www.ti.com/lit/an/sloa034/sloa034.pdf
  - https://www.ti.com/lit/pdf/snoa998
  - https://www.ti.com/lit/an/sloa049d/sloa049d.pdf
  - https://www.ti.com/lit/pdf/snaa320
prerequisites:
  - "[[电子电路/28-运放比较器与滤波/04-跨阻仪表与传感端口#跨阻的闭环与噪声增益]]"
  - "[[电子电路/28-运放比较器与滤波/05-比较器迟滞与波形发生#比较器的高低状态与阈值KCL]]"
  - "[[电子电路/28-运放比较器与滤波/06-滤波原型与有源实现#三个二阶原型的定义与公平比较]]"
  - "[[电子电路/28-运放比较器与滤波/07-基准与精密误差预算#保证界、校准与RSS是三件事]]"
---
# 传感放大与滤波：同一节点模型的CPU复算

初学入口：在四篇正文先完成手算，再运行 `results.json` 对照符号和SI单位。快速入口：阅读 `sensor_filter_lab.py` 的API合同与 `test_sensor_filter_lab.py` 的独立节点矩阵；测试从不同表达出发，不只复制函数结果。两入口最终都检查同一份结果与图。

这是离线CPU教学模型，不是SPICE、板级稳定认证、比较器实测、ADC参考实测或长期漂移实验。没有认领其它RLC/硬件实验的合同。各章的四道题保留迁移与理由评分，脚本通过也不能代替读者解释。

## 从库根运行到新的库外输出

使用已有Python环境，不自动安装。NumPy只供测试及画图，Matplotlib/CairoSVG只供生成图。CPU预算源码只用stdlib。源码是真源，本组没有另建code-sync镜像。

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/21-传感放大与滤波' -p test_sensor_filter_lab.py -v
.venv/bin/python -B '电子电路/80-实践/21-传感放大与滤波/sensor_filter_lab.py' --output /private/tmp/wwl-sensor-my-run
.venv/bin/python -B '电子电路/80-实践/21-传感放大与滤波/generate_sensor_views.py' --output /private/tmp/wwl-sensor-my-views
```

为自己的运行选择新的目录；例子不授权覆盖现存结果。候选没有库根`.venv`时，可以使用主库已有环境的绝对Python路径，但脚本路径仍相对候选库根。生成不指向正文冻结`assets`。两个程序均要求`--output`，先解析参数，缺参退出2且不生成。导入不读取命令行、不导入重绘依赖、不写调用者/MPL/XDG目录；`generate(output)`才在显式输出目录设置默认绘图缓存。已有MPLCONFIGDIR/XDG变量由调用者控制，生成不擅自覆盖。

## 模型与API有效范围

所有数值参数先拒绝bool、complex、数组/容器及非有限量，再转换为float。支持NumPy实标量；不将complex即使虚部为0强转为实数。输出前验证全部本函数输入。单位统一SI，不接收字符串“10k”。这是明确窄范围教学接口，不承诺任意有限巨数。

| 接口 | 范围与返回意义 |
|---|---|
| `tia`/`tia_metrics` | f 0–1 GHz，RF 1 Ω–1 GΩ，CT 1 fF–1 nF，CF 0–1 nF，A0 10³–10⁸，fT 1 kHz–100 MHz；返回跨阻Ω、噪声增益、电压噪声传递、L=A/N与闭环极点rad/s。单开环极点、零输出阻抗 |
| `instrumentation` | 输入0.5–4.5 V，Rf/Rg各100 Ω–1 MΩ，k1/k2 0.1–100、参考0.2–4.8 V；给三输出、Ad/Acm与假定输出0.2–4.8 V范围布尔，不把超限输出偷偷截成合法值。理想线性三运放 |
| `thresholds` | VL 0–0.5 V、VH 4–5 V、Vref 1–4 V、电阻100 Ω–1 MΩ；可选开漏Rp，释放输出由5 V上拉及反馈负载共同算。不可达阈值拒绝 |
| `oscillator` | R 100 Ω–1 MΩ、C 1 pF–10 μF、常延迟0–1 ms且≤0.1RC；刚性参考、瞬时轨切换、周期稳态。不给启动结果冒充稳态 |
| `prototype_response` | 二阶、`butterworth`/`chebyshev1`/`bessel`，x=ω/ωc 0–10⁴；DC=1、相对DC−3dB角频率共同为1。Chebyshev1通带纹波1dB，边缘0.764587，群延迟乘ωc归一化 |
| `filter_model` | `sk`/`mfb`；f0–100 MHz、R100 Ω–1 MΩ、C1 pF–10 μF、SK K1–2.9且理想阻尼正；A0可None（理想）或10³–10⁸、fT1 kHz–100 MHz。返回有限A响应及三阶Routh状态，不保证实际器件稳定 |
| `precision_dc` | vin/Vref 0–5 V；Rf/Rg 100 Ω–1 MΩ，Rs 0–1 MΩ，Vos ±1 mV，两个Ib ±1 μA，A0 10³–10⁸。精确有符号DC节点式，±4.8 V摆幅状态只报告、不截断 |
| `reference_budget` | 1–20个0–10⁶ ppm界项，参考1–5 V；可另传真实标准差列表。`worst`字段与`uncorrelated_sigma`字段不同，独立标准差假设必须由使用者提供 |

内部根求解`bracket`使用直接符号比较、200次预算与相邻浮点停止；不通过残差相乘判断同号。图形调用仅在本表范围内生成。示例参数是教学分配，不当作具体型号保证表；有限A与真实数据手册条件分列在正文。

## 输出、检验与未运行层

`results.json`包含CF=0/1pF的TIA、仪放匹配/比失配、推挽/开漏阈值、零延迟/1μs振荡、三原型、SK/MFB有限A和基准校准前后账本。complex以real/imag对象保存，非法NaN不序列化。`frequency.csv`六列标题自带单位；TIA单位Ω，放大器响应无量纲，环路相位deg。图的波形时刻从周期稳态vC=1.7 V开始，不暗示电容从0启动。

9个SVG均是可编辑真源结果：TIA实际电路及环路Bode、三运放实际仪放、开漏迟滞比较器、RC振荡电路与实际指数/方波、SK实际电路、MFB实际电路、原型幅度/群延迟、参考加载。每个都由同一SVG渲染360/425 PNG；绘图颜色同时有线型区别。CPU程序可以独立生成JSON/CSV，绘图程序在同一输出单元调用它，不另放私有数值副本。

作者测试检查：TIA独立KCL与受控源矩阵、闭环根与单位交越；仪放输出级KCL及差共模展开；开漏负载KCL、常延迟事件端点；三原型−3dB归一化、Chebyshev多项式定义和群延迟相位差分；SK/MFB复数节点矩阵与三阶多项式/Routh；精密DC独立KCL；保证界/σ语义与非法输入/极小残差同号。独立审阅通过后才可发布。作者自检不写成独审。

V26仅完成本组TIA、输入电容与明确环路定义/Bode部分，尚不包含合同要求的普通反相放大器全套组合；V25这里只回顾供电、有限A与范围，不单独认领其完整图合同。9图不代表全部44图目标完成。真实运放PVT/寄生、比较器延迟曲线、SPICE模型、传感器、仪器校准、PCB与人的阅读/掌握结果均未运行。
