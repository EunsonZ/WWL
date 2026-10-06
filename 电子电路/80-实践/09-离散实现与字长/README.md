---
aliases: [离散实现与字长实践]
stage: 3
prerequisites:
  - "[[电子电路/12-交流与变换域/16-z变换差分方程与更新时刻]]"
sources: []
---
# 离散实现与字长实践

先读16页的保持区间与更新时刻，再用此处的源码检查一拍延迟、初值和量化。快进读者可直接跑测试，然后回17页比较数值积分与标准双线性滤波器的不同输入合同。源码为真源；本目录不替换已有01-RC跨层的真源或镜像。

## 运行与输出位置

使用已有主库虚拟环境，无需安装。从本目录运行：

```bash
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B -m unittest -v test_discrete_lab
/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B build_visuals.py --output /private/tmp/wwl-discrete-new-assets
```

`build_visuals.generate(output)`只在明确给定的目录创建图与数据；CLI的`--output`必填，缺参退出2且不写文件。导入两个模块不会解析argv、创建目录、生成文件或初始化绘图库。核心只用Python标准库；测试只读对照原RC的NumPy实现；绘图生成器延迟使用已有CairoSVG。库外新目录适合复算；无输出路径默认值。

## 数值接口与单位

`simulate(inputs,T_s=.00025,initial_V=.4,method='exact',tau_s=.001)`接受有限实电压序列。四方法为`exact/euler/backward/trapezoid_hold`，每个`u[k]`恒定作用于`[kT,(k+1)T)`；返回`len(inputs)+1`个边界电压，首项保留初值，空输入返回一个首项。步长与时间常数单位s，电压单位V，系数无量纲。非有限参数、复数源/初值、嵌套非标量或不可表示派生量明确拒绝。输入须为有限长度序列；本实现没有求收敛的无限循环。

`interval_h(theta,T,method)`返回同合同的零状态`b z^-1/(1-a z^-1)`，theta单位rad/sample。`bilinear_h(theta,T,prototype_tau)`是标准端点输入滤波器的零状态频响，分子为`c(1+z^-1)`；它不提供保持区间状态接口。`modal_map(s,T,method)`支持有限复模态(s单位1/s)，输出无量纲z；`prewarp(theta,T)`在严格主频段`-pi<theta<pi`给rad/s。极点映射、完整H和真实输入采样不是同一种操作。非法参数/singular/数值溢出均拒绝；稳定不保证小误差。

`Format(W,F)`定义有符号W位代码与格点`2^-F`。`simulate_codes`输入为已编码的整数，首项保留提供的初始整数，仍返回n+1项；状态/输入代码解释为V，系数代码无量纲。先用Python精确整数乘加，再核对声明累加器位宽，向最近偶数(或显式向零)舍入一次，再饱和(或显式回绕)到W位。默认累加器`2W+1`位。累加器越界抛`OverflowError`，不默默回绕。

`fir_codes`是零历史、无反馈的抽头延迟线，一个输入对应一个输出，返回n项。它与保存边界状态的RC接口有不同的首点/长度合同。FIR累加器默认`2W+ceil(log2(L))+1`位。此处的整数CPU参考不模拟具体DSP指令流水或ADC。

## 可复查的实验

L02的本组CPU部分包括：同一个R=1kΩ、C=1µF、T=.25ms、v0=.4V的四种积分；独立RK4与原RC接口对照；单边初值项、双边左右侧ROC、单位样本延迟；Euler的T=2τ边界和2.5τ发散。V14给t/s/jω/z的同参数及初值项；V17给保持区间和n+1边界；V18给μ=sT稳定域与实际z单位圆映射。

L13的本组CPU部分包括：W16/F14的精确整数RC；Fraction枚举核对负数与ties-to-even；粗格点的一代码不动点和两代码周期；饱和/回绕/累加器越界；FIR输入清零后的历史清空；有条件的确定性误差界。有限序列测试与固定步数枚举分别记录，不把“没有遇到”写成无限时间证明。正文给有限状态鸽巢证明及其边界。

已运行证据限于CPU数值、生成器进程合同、SVG/XML与360/425px作者目检。没有运行SPICE、硬件ADC/DSP、真实Obsidian客户端、真人阅读或掌握度验收。图数据是教学模型输出。

## 图件与数据

7份SVG可编辑，含title/desc；每份有360/425px PNG，原画布425px且文本至少13px。参数与输入完整写在`assets/parameters.json`。`state-data.csv`记录时间(s)、四积分电压(V)与实际保持序列；`modal-data.csv`记录μ与各z映射；`frequency-data.csv`区分数字Hz、rad/sample与原型rad/s；`integer-data.csv`记录整数代码、解码V及粗格点LSB。所有资产由`build_visuals.py`生成，数值结构应可重现，渲染环境可能影响PNG字节。

[[电子电路/80-实践/09-离散实现与字长/code-sync/discrete_sources|三份源码与测试镜像]]按源文件逐字同步；修改源码时同时更新测试和镜像。
