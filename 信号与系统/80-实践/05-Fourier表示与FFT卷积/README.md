---
type: experiment
domain: signals-and-systems
stage: 2
content_status: draft
evidence_status: partial
aliases:
  - Fourier小数组与块状态实验
sources:
  - https://github.com/EunsonZ/WWL/issues/177
prerequisites:
  - "[[信号与系统/10-连续与离散系统/06-Fourier四种表示与FFT卷积]]"
---

# Fourier小数组与块状态实验

从 [[信号与系统/10-连续与离散系统/06-Fourier四种表示与FFT卷积#有限数组与周期延拓|四点有限记录]] 带着延拓、归一化与输出长度进入。这里计算有限数组和流式状态；一般CTFS／CTFT／DTFT的收敛仍由正文与数学主课证明。先在纸上预测，再与独立求和参照核对，不能从一张FFT图推出全类定理。

## 预测表与实际算子

| 固定输入 | 预测／独立参照 | 真源入口 |
| --- | --- | --- |
| r=(1,2,1,0)，N=4 | DFT=(4,−2j,0,2j)，DTFS除4；逆除4 | `dft`、`fft`、`idft`、`ifft`、`dtft` |
| r与h=(1,1,1) | full=(1,3,4,3,1,0)；N4循环=(2,3,4,3) | `linear_convolution`、`circular_convolution` |
| x=(1,2,4)，h=(1,2) | full=(1,4,8,8)；N3循环=(9,4,8)；valid互相关=(5,10) | `frequency_convolution`、`valid_correlation` |
| 翻核(2,1) | full=(2,5,10,4)，取索引1..2复得互相关 | `fft_linear_convolution`后显式裁剪 |
| x与右邻规则C、右移S | C0S0=(2,5,2)，S0C0=(0,5,10)，CpSp=SpCp=(6,5,10) | `right_correlation`、`shift` |
| r切成(1,2)、空块、(1,0) | 发布(1,3)、空、(4,3)，EOF尾(1,0) | `OverlapAdd`、`stream_blocks` |
| 长4矩形截窗cos(2π·1.25n/4)，fs=8Hz | 补到16仅将网格2Hz改0.5Hz；窗第一零点半宽仍2Hz | `cases()['window']`，同一DTFT的不同样点 |

`fft`／`ifft`的域是非空2幂长度；`dft`／`idft`接受任意非空长度，因此N=3循环例用显式DFT。正向不归一化，逆除N。输入允许有限实／复标量，bool、NaN、inf和嵌套数组拒绝；复数结果始终保留。CNN式valid互相关与固定C矩阵另限制实输入，无共轭、偏置、步幅或隐含padding。单样点核、核比块长、空输入full输出与M=1的空tail各有声明。

## 分块状态怎样验

每个非空`push`发布与输入块等长的样点，输出起点是调用前`consumed`。tail恒长M−1，属于输出；空块不改变时间或tail。`flush`首次只发尾，重复为空，无输入时EOF为空，EOF后即使空push也拒绝。整块校验／计算成功之后才提交状态；坏块不能消耗时间。改变合法块划分应保持原全卷积的全局位置与末尾长度，而非只比较若干中央点。

测试的输入(1,−2,3,0,4,−1)含全部32种连续分块，分别配M=1、2、4、9的核，在边界插空块。独立参照用双循环将每个x[n]h[m]加到n+m，不调用FFT或本库卷积。另一参照用显式cos/sin求复DFT；指定小数组还固定手算期望。周期交换例的27组小整数只检实际函数，任意向量的证明仍是正文Cp=I+2Sp⁻¹。

## 执行与证据位置

只需Python标准库，不需GPU、音频驱动、NumPy或框架安装。Mac M4 Pro可运行同一组有限教学计算；CPU数值通过不代表实时音频设备或CNN框架已经验收。从此目录运行，输出目录须在库外且尚不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_fourier_lab.py
PYTHONDONTWRITEBYTECODE=1 python3 fourier_lab.py --output /private/tmp/wwl-fourier177-output
```

`results.json`记录固定输入、未舍去的实／虚部、块偏移／状态和网格参数。目录重跑须换新路径；已有路径或任何含AGENTS.md的祖先目录拒绝。导入真源不会写文件，单元测试不生成图／数据，输出函数才写新外部目录。数值误差接受范围为 `2e−11·(1+|期望值|)`，小数组另有更紧断言；整数手算不因这份容差允许折回误差8。

**实际执行：2026-10-10 已完成本版同字节 Fourier 的8项测试、规范CLI与独立oracle。** 独立显式DFT、双循环卷积、有限／周期移位矩阵及连续变换有限实例共162项比较，最大缩放误差6.365e−15；六点输入的32种分块与四种核共128种布局均核对full输出和EOF。完整输入、输出、日志与独立审阅见 [实际结果与边界](results/2026-10-10/README.md)。五张SVG的系统WebKit完整画布已实际渲染并查看；Obsidian、360px窄列与真人迁移仍未验证。有限实例不替代正文的一般定理。

## 源码与可编辑图

[fourier_lab.py](fourier_lab.py) 是算法真源，[test_fourier_lab.py](test_fourier_lab.py) 是独立参照测试；[[信号与系统/80-实践/05-Fourier表示与FFT卷积/04-源码与验证|正式code-sync镜像]]逐字映射两者。修改源码后同步镜像，不在Markdown另维护第二套实现。已有 [[数学/70-信号处理与多模态数学/80-多模态数学最小实验|多模态数学实验]]的幅度／Mel计算维持原接口；本组用完整复数来核逆变换，不更改已有特征数值。

三张SVG是可编辑的教学图真源，标注来自正文手算，尚需显示验收：[四种表示](assets/four-representations.svg)、[四点蝶形](assets/four-point-butterfly.svg)、[OLA全局时间线](assets/overlap-add-timeline.svg)。图说明对象／中间值／索引，不替代实际执行JSON。重叠保留只在正文比较历史输入、污染区及EOF，不提供未实现的OLS API；框架padding、真实设备deadline、硬件性能与真人迁移须有各自后续证据。


## 图中的数字怎样复算

三张SVG本身是可编辑向量图源。`four-representations.svg`按正文四种分析／合成式核周期、单位和归一化；`four-point-butterfly.svg`按r的偶支(1,1)、奇支(2,0)及W₄=(1,−j)手算，并核 `results.json.four`；`overlap-add-timeline.svg`按块(1,2)、(1,0)、h=(1,1,1)与全局偏移0、2重做局部full，再核 `results.json.ola.events` 的发布／tail。改变块划分只移动局部放置方式，图的全局输出仍须与直接full同值。图的可复算性和XML有效不代替实际渲染验收。
