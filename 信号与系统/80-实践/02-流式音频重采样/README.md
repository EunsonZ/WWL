---
type: lab
domain: signals-and-systems
stage: 2
content_status: draft
evidence_status: partial
aliases: []
sources:
  - "https://www.analog.com/media/en/technical-documentation/dsp-book/dsp_book_Ch16.pdf"
  - "https://www.dsprelated.com/freebooks/sasp/Downsampling_Aliasing.html"
  - "https://www.dsprelated.com/freebooks/sasp/Polyphase_Decomposition.html"
  - "https://www.analog.com/media/en/technical-documentation/dsp-book/dsp_book_Ch28.pdf"
prerequisites:
  - "[[信号与系统/10-连续与离散系统/05-同一波形的采样误认]]"
---

# U3 流式音频重采样：48k到16k

读者问题：一条低频加10k的48k列表，怎样在16k下保留目标信息，并保证任意块切分不改变已定义的输出？**基础入口**先到 [[信号与系统/20-数字信号处理/01-FIR滤波设计与频率规格#手算核与迁移验收|四样本卷积]]算[1,20,16]，再预测6k伪峰。**快进入口**从 [[信号与系统/20-数字信号处理/02-多速率与流式重采样#多相是同一和式的索引重排|多相和式]]核对索引、边界及计数。两入口汇入同一实验，不另造简化正确性合同。

## 准备、操作与停点

仅用已有 Python3/NumPy 运行数值与测试，绘图另需已有 Matplotlib；不自动安装、不用SciPy、不读录音装置。命令从本实验目录执行，`/private/tmp/wwl-u3-qa` 是明确库外输出位置，可自行替换，禁止指向课程assets或冻结候选。生成器不会猜测输出路径。

```bash
python3 -B -m unittest -v test_resample_lab.py
python3 -B resample_lab.py --output /private/tmp/wwl-u3-qa/data
MPLCONFIGDIR=/private/tmp/wwl-u3-qa/mpl python3 -B plot_resample.py --output /private/tmp/wwl-u3-qa/plots
```

1. 不运行代码，手算10k降至16k后的列表恒等频率与幅值，说明为什么后置数字滤波不能识别两个来源。
2. 看 [[信号与系统/20-数字信号处理/01-FIR滤波设计与频率规格|FIR设计课]]，在图上分别指通带、过渡、阻带，解释截止7k与保留6k的区别。
3. 运行测试/生成器，比较 `offline`、`polyphase`、`Stream`；先查输出长度4064，再查最大误差。停点：输出长度不同不能直接做逐项误差比较。
4. 比较失败/成功谱；解释取m=64开始的理由，再读 [[信号与系统/20-数字信号处理/02-多速率与流式重采样#频谱证据的完整定义|单边幅值定义]]，不能称为PSD。
5. 读 [[信号与系统/20-数字信号处理/03-有限字长块状态与实时合同|有限字长与恢复课]]，先预测32位风险，再看40位饱和计数；写出当前CPU证据还缺什么生产验收。

![滤波规格](assets/filter-spec.svg)
![全局状态与块边界](assets/state-timeline.svg)
![失败与成功的单边幅值谱](assets/alias-spectrum.svg)

这三张图分别回答“抑制哪一带”“保留哪些全局点”“失败留下什么”。不使用3D，因为这里没有需要曲面表达的第二自变量；颜色也不承担唯一信息。每张附实际425px PNG，修改源 [plot_resample.py](plot_resample.py) 可在库外确定性复算。

## 数据与边界

| 文件 | 数据定义 | 复算责任 |
| --- | --- | --- |
| [coefficients.csv](assets/coefficients.csv) | k、无量纲h、Q15整数 | 对称193抽头、DC与量化频响 |
| [samples.csv](assets/samples.csv) | m、完整浮点输出、流式输出、Q15输出，V | 全卷积零延拓；尾部与启动仍保留 |
| [spectrum.csv](assets/spectrum.csv) | Hz、直接抽取/前滤波/Q15单边峰值幅度，V | 矩形窗3840点，内部双倍、DC/Nyquist不双倍 |
| [results.json](assets/results.json) | 精确规格、相位、长度、误差、饱和计数、谱定义 | deterministic，未记录时钟时间戳或机器特有路径 |

固定输入N=12000，0.6 V的1k余弦加0.3 V的10k余弦；前后零延拓。对称核L=193、截止7000 Hz，保留n≡0(mod3)，输出4064点，内容延迟2ms。整段与流式当前最大误差约3.33e−16 V，与多相参考约8.88e−16 V；定点最大误差约1.01e−4 V。直接抽取6k幅度0.3 V，成功6k约3.028e−6 V。不得把这一个成功纯音或图的显示底线当作整个频带保证；完整核的网格加解析余量见FIR课和结果JSON。

所有生成脚本要求`--output`；没有隐式写assets或测试快照。输出JSON按键排序、无运行时间；SVG移除Date并固定hashsalt；PNG固定Software标记。CSV是17位有效数字。依赖/字体版本改变仍可能改变图文件字节，数学数据和显式合同用于跨环境比较；相同环境本次两次输出字节相等。

## 测试承担的责任

[test_resample_lab.py](test_resample_lab.py) 有11项独立期望/不变量测试：手算全卷积及非零相位；7点所有64种分块×3相位；随机长短核多相对照；空记录、重复flush、拒绝closed、无效块不变状态；10k/6k恒等；对称与DC/群延迟；精确半格负数舍入、输入/输出/累加器饱和；奇偶N的DC/Nyquist幅值；丢点/每块复位的故意失败；shape/复数/nonfinite/参数拒绝；极小正截止频率导致不可归一化时拒绝且不泄漏NaN/警告。测试不生成文件、不写候选。

规范真源 [resample_lab.py](resample_lab.py)、[test_resample_lab.py](test_resample_lab.py) 和 [plot_resample.py](plot_resample.py) 与 [[信号与系统/80-实践/02-流式音频重采样/04-实验源码与验证|正式code-sync镜像]]一起交接。浮点stream有O(L)持久环，但临时分配和Python开销存在；固定点只实现规格参考。没有序号协议、绝对时间偏移/缺口有效掩码、驱动或声音设备功能。

## 撤去方法提示的独立交付

一份新输入只知道：fₛ=48000，目标≤5k，含未知幅值/相位9k干扰，块可能空、最后长度未必是3的倍数。要求结果在16k中可解释，含明确时间轴和故障声明。提交一份规格、完整记录与分块一致性证据、低频/带外判据、尾部政策及一种缺块恢复设计。不得仅改采样率标签、展示一个成功波形或写“使用重采样API”。

> [!question]- 答案与接受标准
> 9k在16k折到7k；须在降采样前抑制，并给出目标通带误差、阻带要求、过渡和输入干扰幅值预算（未知时声明相对抑制及绝对误差未知）。可接受窗FIR、优化FIR或其他经核验方法。正确索引/历史、全局相位、EOF与空块合同必须同时保证；滤波长度/时刻映射与输出数量按实际N/L/p推导。能独立比较任意切分并给小手算例，比仅两块成功更强。恢复可插零或重启新段并标有效性/绝对原点；缺失声音无法从该数据保证恢复。合法不同尾部裁剪方式也接受，但须先声明所比较的数学对象，不得将full与same混作一个对象。

## 已验与未验

本次已有CPU数值运行、11项相关测试、同环境确定性复算、三张实际425px渲染；正式库结构/链接/镜像检查记录由候选REPORT提供。来源核对到三课所列具体段落。本课仍是draft/partial：独立内容复核是后续签收责任，不替读者填写掌握度。

Obsidian真实客户端、真人无提示学习、盲听、目标机WCET、声卡/ADC/驱动、真实缺块恢复、RTL/综合/时序、连续生产运行均未验证。CPU规格模拟不能推出这些层成功。
