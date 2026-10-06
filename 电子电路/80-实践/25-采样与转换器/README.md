---
stage: 1
aliases: []
sources:
  - https://www.analog.com/media/en/training-seminars/tutorials/MT-021.pdf
  - https://www.ti.com/lit/spract6
prerequisites:
  - "[[电子电路/42-转换器与采样时钟/01-采样保持量化与编码#三位的八个格子及端点]]"
  - "[[电子电路/42-转换器与采样时钟/02-DAC结构匹配与建立#电压模式R-2R：实际节点方程给权重]]"
  - "[[电子电路/42-转换器与采样时钟/03-ADC架构与逐次决定#一次三位转换的完整记录]]"
  - "[[电子电路/42-转换器与采样时钟/04-驱动回踢参考与抗混叠#采集窗口与源的动态条件]]"
---
# 采样与转换器：电压到码的可复算账本

先手算1.9V的三次SAR比较、code5的R-2R节点和电容电荷，再运行。基础入口从三码表进入；快进入口直接用KCL和电荷守恒检查源码的网络端点。所有量化码与内部DAC都使用3bit0..3V，量化区间中心和DAC下边缘是两个字段。

复制本目录至新的可写位置，再选**库外、新输出目录**运行。源码不自动安装依赖。数值模型只需stdlib；图层用已有matplotlib/CairoSVG，依赖缺失时图层记未运行。输出是可覆盖生成目录，使用者负责选择自己的路径，不可把示例用于覆盖其他人的产物。

```bash
python -B -m unittest discover -s . -p test_converter_model.py -v
python -B converter_model.py --output /private/tmp/adc-my-number-run
python -B generate_figures.py --output /private/tmp/adc-my-figure-run
```

`generate(output)`及`main(argv=None)`是显式接口；两CLI都必须有`--output`，缺参退出2且不生成文件。导入不解析argv、不初始化绘图/字体缓存、不创建文件。图层在调用时lazy import，使用direct Figure和rc_context，生成缓存留在显式输出目录并恢复环境变量；图源SVG可编辑，360/425 PNG由SVG渲染，而不是另一套假图。数值/图生成输出路径可以不同。

## 数值API及支持域

输入严格为Python int/float实标量，不接收bool、complex、str、数组或自动cast对象。位数1..20，量程.001..100V，电压输入−100..100V；域外与非有限输入ValueError。有限电压越出本次ADC量程时，quantize/sar端码饱和并返回overload。`dac`要求合法码，不隐式mask。理想实数式给floor(v/Δ)；数值API则统一按实际计算阈值 `dac(j)=j*delta` 划半开码区，相等进入上码。quantize用最多bits步的二分定位这些阈值，SAR用逐位试探，因此同一DAC阈值及其相邻浮点数不会因除法舍入而被分到不同码。3.3V三位的码3阈值约1.2374999999999998V也遵守此合同；计算阈值不是任意精度真实器件电压，不用epsilon吸附改变其邻点归属。

- `quantize`：midrise半开区间、tie向上，最高端包含；center/error单位V。`sar`：N次由MSB到LSB比较，keep为Vin≥DAC，trace保留decision/bit_index/trial/retained。
- `string_tap`：2..256正电阻（.001..1e7Ω），底到顶排列，码0..len−1。无限开路仅接受原生Python float的正`math.inf`，不接受float子类或NumPy标量的无穷；有限负载.001..1e9Ω接地，返回开路V、Rth及加载V。
- `r2r3`：固定三节点实际R-2R网络，code0..7，R.001..1e7Ω；返回v0,v1,v2列表，输入bit电压是理想0/VRef源。`cdac`固定四支含dummy，正相对权重.001..1e6，初始顶板0/底板Vin，返回浮顶V。`current_dac`三正权重、unit1e−15..0.1A、RL.001..1e7Ω；理想电流无限compliance是假设，输出可能超真实供电，调用者必须另外核对，不能把返回值叫硬件合法。
- `rc_state/share`：R.001..1e7Ω、C1e−15..1e−3F、t0..10s；初值与目标V都有限。RC采用expm1权重保存极短时间/非零初值。`rc_sine_error`返回同一时刻未延迟正弦的误差幅值，不是DCstep残差。
- `reference_cycle`：固定正取电荷0..1e−3C，T1e−12..10s，1..4096事件；Q/C>100V拒绝，迭代状态超电压域也明确拒绝。每行before/after/next_before保留初态与恢复协议。`delta_sigma`仅1..4096个|u|≤1、|s0|≤1的特定一阶更新，不接受过载输入；有界状态不是任意ΔΣ稳定证明。
- `fold`：Hz输入0..1e9、采样率1e−3..1e9Hz，返回[0,fs/2]的实余弦折叠频率；相位/复指数有符号谱需另保留，函数不声称一般重建。

所有循环有固定预算，不用浮点阈值while搜到无限。没有主库既有U4源码或镜像改动，也不依赖其绘图导入；新文件是真源。本目录不平行复制整份代码正文，读 [模型](converter_model.py)、[测试](test_converter_model.py)、[图源](generate_figures.py)；源码与测试/README作为同一交付单元。

## 参数、结果与图的合同

parameters/results以SI字段写数值/码/状态；figure-data给321个转移采样、301个建立点、SAR三决策和12个参考事件。图中只是教学时钟2μs采集+3次各1μs决定，5μsvalid、6μs周期，不冒充真实CONVST/BUSY规格。八图涵盖转移/确定误差/折叠谱/时间偏移、真实源电容参考网络、四DAC、SAR CDAC及时序、其他架构状态、建立与周期恢复。

V29在这些3bit理想拓扑/决策/时钟内提供完整过程；V30在这些确定算例内区分量化、混叠与时间扰动，统计模型条件在量化图注及正文中明确；最终信用须独立审阅后确认。本实验没有完整高阶ΔΣ、校准算法或真实型号排名。

L实验只交CPU教学验证及渲染，不把它称为已有整项硬件实验签收。生产仍需器件保证条件、源/参考真实阻抗、PVT/布局与寄生、转换时序/初始化、SPICE、硬件量测、接口UI和学习者证据。去旧 [[电子电路/80-实践/02-弱信号前端预算/README#证据与生产责任|U4责任边界]] 带回整链门槛，返回这里区分本次单元模型与传感量准确度。

R2回归保留原12测试，并核三类位宽/四个常见量程的所有内部计算阈值及上下相邻浮点数；独立有序阈值计数作为对照。开路特殊分支与普通实标量的类型规则一致。
