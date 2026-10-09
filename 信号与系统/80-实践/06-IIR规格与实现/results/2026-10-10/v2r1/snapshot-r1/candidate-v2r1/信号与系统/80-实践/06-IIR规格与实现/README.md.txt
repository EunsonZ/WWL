---
type: experiment
domain: signals-and-systems
stage: 2
content_status: draft
evidence_status: partial
aliases: []
sources:
  - https://github.com/EunsonZ/WWL/issues/178
prerequisites:
  - "[[信号与系统/20-数字信号处理/04-IIR设计二阶节与幅相取舍]]"
---

# IIR规格与实现实验

先从 [[信号与系统/20-数字信号处理/04-IIR设计二阶节与幅相取舍#从两个误差不等式推阶数与系数|完整规格到系数]] 预测N27，再查看结果。算法真源 [iir_lab.py](iir_lab.py) 从48kHz、6／8kHz带边、.01／.001幅度误差构造Butterworth、数字极点与完整SOS。输出保留理想原型、生成float64节模型、binary32实际递推和W8/F4饱和四种不同对象。

## 独立参照与接受范围

| 要核的结论 | 参照与验收方法 |
| --- | --- |
| 27阶是本原型的最小可行整数 | 不用ceil／log公式，逐次乘带边比的平方直到误差比；96kHz改为30阶，5kHz通带改为17阶 |
| 数字频带幅度达标 | 理想tan映射幅度单调，端点证明全带；独立乘极点／零点与SOS频响观察系数；`strict_machine_certificate`对两份固定系数分别以精确dyadic输入及Decimal向外包围认证完整闭频带，所有cell达标且无缝覆盖才返回true |
| 同H的直接／级联等价 | 80位Decimal扩展精确binary64节系数，独立直接I差分和转置直接II／SOS核80拍，容差1e−55；精确代数证明在正文 |
| 通带群延迟预算 | 原型极点／相位差分只作观察；严格机器证书用同一SOS的J(c)/Q(c)向外包围，通带每cell延迟上界≤96sample，不借用另外生成的极点 |
| 相同幅度可超过延迟预算 | r=.99全通DC额外199sample，>2ms；不改原幅度 |
| 指定精度与内部峰值 | 主12k拍两音记录；binary32每乘积、相加、状态存储舍入，无FMA；直接型及升／降半径SOS对同一Decimal参照核误差和峰值 |
| 二阶节次序与饱和 | 独立20拍W8/F4手算，2V输入，高→低末总输出16code，低→高32code；后者无饱和，前者确有存储饱和 |
| 系数／极限环界 | a1 −1.98→−1.9802有实根>1；保留a=.75、q0=1、W8F4的一格不动点，不把稳定极点当整数趋零保证 |

binary32SOS的512拍测试接受绝对误差≤2e−5·(1+|参考|)V；12k拍报告给实际最大误差，不以短测试容差代填长记录通过。直接型若超过有限范围，记录第一个失败样点及失败前误差，不能把短前缀冒充全轨迹。实际峰值只针对固定输入，不等于所有有界输入的内部状态上界；升／降次序不是最优排列定理。

## 执行协议

Python标准库即可，Mac M4 Pro可作同一CPU教学实验，无GPU／硬件或安装依赖。由实际执行者在本目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_iir_lab.py
PYTHONDONTWRITEBYTECODE=1 python3 iir_lab.py --output /private/tmp/wwl-iir178-output
```

输出目录必须库外、全新，既存路径或含AGENTS.md祖先拒绝。`results.json`包括三个设计的Ω带边／阶数／极点／全部节系数、直接展开系数Decimal字符串、幅度端点、`machine_certificates`两组严格包围及完整系数分数、接收／未决cell、每节Q下界、同SOS群延迟范围；另保留binary32节极点半径估计和原型极点延迟观察、两次SOS与直接型误差／内部峰值，以及逐拍饱和事件。系数均以源码公式与完整JSON为准；直接展开系数不是短小舍入表。

**当前状态：NOTRUN**。历史运行日志未恢复，不能沿用旧PASS；本候选作者只作AST／链接／镜像／SVG XML自查，没有导入或执行实验。源码、固定输入和独立测试已准备；执行者另记录实际命令、Python版本、退出结果与外部JSON路径。执行者核 `machine_certificates` 两组 `certified=True` 且两带无未决cell、闭带覆盖为true；通带平方幅度≥.9801且≤1.0201、阻带平方幅度≤.000001、同SOS通带延迟0..96sample、精确Schur条件全为true。半径抽点只辅助观察；长记录须报告完整样点数、误差和失败位置，不把允许直接型失败当作全部实现通过。通过后才补课中实际延迟和精度数据。既有FIR的193tap、96sample延迟及全带余量复用原证据，本组未重跑FIR；本次数字同拍输出为48kHz，未拿不同抽取速率的成本相互比较。

## 真源、镜像与显示

[test_iir_lab.py](test_iir_lab.py) 独立核阶数、差分／转置状态、相位导数、固定位代码；[[信号与系统/80-实践/06-IIR规格与实现/04-源码与验证|code-sync阅读镜像]]逐字对应两文件。导入无I/O、测试不写结果；显式CLI才生成新外部目录。系数设计用float64三角函数，Decimal保存其精确二进制值后高精度递推，不能称已经精确认证原型的超越函数舍入。

图源 [数字设计链](assets/design-chain.svg)、[中间尺度](assets/internal-scale.svg) 是可编辑SVG，文字与值来自正文推导／手算；实际显示需独核。这里没有SPICE、运放、ADC、DSP芯片或实时音频设备测量；也没有把模型走读当真人迁移通过。


## 图中的数字怎样复算

两张SVG本身是可编辑向量图源。`design-chain.svg`的π/4、π/3、Ωp/Ωs、27阶及13+1节，依次核 `results.json` 的 `design`；`internal-scale.svg`的8、1/8、16V、.25V来自两节DC与输入2V，1V／2V终值核 `fixed_high_first.output_codes[-1]` 与 `fixed_low_first.output_codes[-1]` 除16。上界7.9375V是127/16。图只显示这份固定合同；改系数、输入或位宽时先重算对应公式／轨迹再改SVG标注，不保留过期“通过”图。


## 第二版：严格机器证书的执行范围

第一版的float复数求界只保留为 `amplitude_estimate` 和 `ideal_pole_delay_estimate`，没有认证权限。第二版用80位私有Decimal向下／向上舍入、精确二进制系数输入、c域有理端点和自适应二分，严格包围固定binary64／binary32 SOS的完整幅度与同系数通带延迟。输出包含全部接收cell、未决cell、精确系数分数与覆盖不变量；算术异常退出或任何未决项都不得代填PASS。此认证只支持主48kHz、6/8kHz的规格，96k/5k迁移仍提供设计预测与抽点，不挪用主证书。

每带默认最多131072次cell求值、深度24（硬上限28），达到上限报告未认证；正常调用不需安装依赖。执行者记录cell数与耗时，长记录误差／饱和仍单独验。作者只静态自查，没有运行新测试或CLI。
