---
type: practice
domain: signals-and-systems
stage: 1
content_status: draft
evidence_status: partial
aliases: []
sources:
  - "https://ocw.mit.edu/courses/6-003-signals-and-systems-fall-2011/pages/lecture-notes/"
prerequisites:
  - "[[信号与系统/10-连续与离散系统/04-频率响应与采样重建]]"
---

# 采样与系统辨别：U2的可复算实验

先读 [[信号与系统/10-连续与离散系统/05-同一波形的采样误认|同一波形的采样误认]]，写下四点手算与预测，再运行这里的代码。实验规格是理想连续电压、固定采样时刻、无模拟前端、无随机性；它只验证解析教学构造与CPU数值，没有ADC、仪器、真实时钟、真人学习或生产验证。

## 一次运行应该留下什么

规范真源是本目录 [signal_lab.py](signal_lab.py)，测试是 [test_signal_lab.py](test_signal_lab.py)。分别有 [[信号与系统/80-实践/01-采样与系统辨别/code-sync/signal_lab|生成源码镜像]] 与 [[信号与系统/80-实践/01-采样与系统辨别/code-sync/test_signal_lab|测试源码镜像]]；镜像不是另一份运行实现。修改时两者同步。

环境需要Python、NumPy、Matplotlib、Pillow及Arial Unicode MS字体。当前作者已用本机现有Python 3.14.7、NumPy 2.5.3、Matplotlib 3.11.2、arm64 CPU执行；没有安装依赖。其他环境先检查依赖，缺依赖或字体应报告未运行，不删检查来变绿。`-B`避免向源码目录写字节码；Matplotlib缓存放到库外。

在本目录运行，下例输出与缓存均为新建库外目录，可改为自己的库外路径：

```bash
MPLCONFIGDIR=/private/tmp/wwl-u2-cache XDG_CACHE_HOME=/private/tmp/wwl-u2-cache python3 -B signal_lab.py --output /private/tmp/wwl-u2-run
python3 -B -m unittest discover -s . -p 'test_signal_lab.py' -v
```

脚本不会自动运行设备或读取用户音频；数据来自显式公式。默认生成5份CSV、results.json、5张可编辑SVG、同版PNG和425px预览。生成耗时与依赖版本不属于系统理论结论。

| 文件 | 对象/单位与用途 |
| --- | --- |
| [samples.csv](assets/samples.csv) | 32点，n整数、t_s秒；cos2_v/cos6_v、边界相位、量化输入/输出/误差与漏看脉冲均为V |
| [waveforms.csv](assets/waveforms.csv) | 0–1 s的1001个绘图时刻；这是绘图网格，不是采样率被提高了 |
| [dft-amplitude.csv](assets/dft-amplitude.csv) | N=32矩形窗，f_hz与单边幅值V；内部正频率翻倍，DC/Nyquist不翻倍，不是PSD |
| [convolution-terms.csv](assets/convolution-terms.csv) | 翻转平移图的求和索引、输入V、核无量纲与各项贡献V |
| [first-order.csv](assets/first-order.csv) | τ=1 ms、y(0)=0.4 V、1 V阶跃，零输入/零状态/总输出各V |
| [results.json](assets/results.json) | 环境、规则、关键差值与证据范围；浮点容差不替代解析恒等式 |

## 本版实际结果与独立期望

所有正式测试已在上述作者环境实际运行，11项通过。四点余弦的独立期望[1,0,−1,0] V；在t=1/16 s两连续值差√2 V。生成的32点两序列最大浮点差约2.18×10⁻¹⁴ V，是三角函数求值误差。4 Hz phase=0样本最大绝对值约1.08×10⁻¹⁴ V，解析值为0。

量化独立输入为1 Hz、0.83 V、phase=0.3 rad，Δ=0.25 V，半格向较大格点舍入，不限幅；最大误差0.11275473 V，低于0.125 V预算。第一点0.792929286 V量化为0.75 V；常值0.1 V的误差恒为−0.1 V，反驳无条件白噪声模型。0.03–0.08 s矩形脉冲的可见采样数0。固定0.01 s采样偏移让本构造2/6 Hz样本的最大差变为0.49345779 V；这个现象不是任意非均匀采样的重建保证。

测试不从生成结果读答案：手算四点、√2连续差、±1 Nyquist列、量化半格负值、常值误差、卷积[1,2.5,1]、初值0.4/e与1−1/e、DC/Nyquist与奇数DFT幅值、10 Hz迁移相位均独立设置。无效输入覆盖非正采样率、非整数点数、NaN、空/二维/复数值、非正时间常数、负时间与非法脉冲区间。使用1e−13量级容差只针对短序列float64三角函数，而不是硬件误差预算。

## 图与阅读边界

[alias-spectrum.svg](assets/alias-spectrum.svg)连接连续波形、样本与频谱；[nyquist-quantization.svg](assets/nyquist-quantization.svg)将相位边界与值轴误差分图；[convolution.svg](assets/convolution.svg)逐步翻转平移并检查y[1]=2.5 V；[roc.svg](assets/roc.svg)解释双边变换侧别；[sampling-flow.svg](assets/sampling-flow.svg)解释操作顺序。作者已经检查同版425px PNG，修正了流程图不被现有字体支持的Unicode下标；线型/标记可区别两波形，背景阴影可在灰度识别ROC。未在真实Obsidian客户端检查字体/公式/页面渲染，也未做真人盲做或延迟回访。

## 独立迁移的交付

完成主课末尾10 Hz、不同相位、Δ=0.1 V及附加瞬态联合题，先交新数据与理由，再展开答案。接受等价证明/观测设计，但须区分“本构造被区分了”和“所有允许输入均唯一重建”。想延伸到STFT时，去 [[数学/70-信号处理与多模态数学/02-采样定理波形STFT与Mel频谱#4. STFT：局部时间片上的 DFT|已有STFT主解释]] 携带f_s、N、窗与幅值单位，回来解释泄漏与混叠的不同；本实验不重复STFT/Mel整课。
