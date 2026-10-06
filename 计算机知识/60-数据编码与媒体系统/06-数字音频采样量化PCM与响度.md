---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 基础
estimated_minutes: 80
verified: 2026-09-03
topics:
  - media
  - encoding
  - digital-audio
  - pcm
  - loudness
tags:
  - computer-science/media
  - computer-science/encoding
  - computer-science/audio
---

# 数字音频：采样、量化、PCM 与响度

## 本课目标

学完后，你应该能够：

- 区分连续声压、离散时间样本、量化码值和播放音量；
- 在带限前提下解释采样定理、Nyquist 频率和混叠；
- 计算 PCM 的样本数、sample frame 数、时长和理论数据率；
- 读懂声道 interleaving、位深、signed/unsigned、整数/浮点和 endian；
- 区分 peak dBFS、true peak、RMS 与 LUFS；
- 识别 clipping，并说明 dither 能解决什么、不能解决什么。

本页讲工程数据布局；采样定理、DFT、STFT、窗口和 Mel 的完整数学解释在 [[数学/70-信号处理与多模态数学/02-采样定理波形STFT与Mel频谱|采样定理、波形、STFT 与 Mel 频谱]]。不要在两个知识域复制两套数学推导。

> [!tip] 首读 20 分钟
> 先沿“声压 → 抗混叠 → 采样 → 量化 → PCM 字节”读，掌握采样率、位深、sample frame、未压缩数据率和混叠反例。二读再区分 true peak/RMS/LUFS、整数/浮点 PCM、平面/交错排列与 dither。

## 1. 从声压到数字样本的四层

```text
空气声压 x(t)
  └─ 麦克风/模拟前端：换能、增益、抗混叠滤波
       └─ 采样：x[n] = x(n / fs)
            └─ 量化：连续幅度映射为有限码值
                 └─ PCM 字节：按格式约定排列、封装和保存
```

每层都可能改变信号：麦克风有频响和噪声，前置增益可能过载，抗混叠滤波器有过渡带，采样离散化时间，量化离散化幅度。文件里的 PCM 不是“原现场本身”，而是这条测量链的结果。

## 2. 采样率与混叠

若连续信号严格带限于 $B$ Hz，理想条件下要从样本唯一重建它，需要：

$$
f_s>2B.
$$

$f_s/2$ 是 Nyquist 频率。现实转换器在采样前使用抗混叠低通滤波器，并为非理想滤波器留出过渡带；因此不能把“采样率一半”理解为可以无损装到边界的全部现实频率。

### 可观察例子：10 kHz 变成 6 kHz

以 16 kHz 采样率直接采 10 kHz 正弦：

$$
10\ \text{kHz}-16\ \text{kHz}=-6\ \text{kHz}.
$$

离散样本与相位方向相反的 6 kHz 成分无法区分。10 kHz 已超过 8 kHz Nyquist 频率，于是折叠进基带。事后把文件重采样到 48 kHz 只会生成更多插值样本，不能知道原来是 10 kHz 还是 6 kHz。

> [!failure] 反例：48 kHz 文件一定比 16 kHz 更清晰
> 错。若来源先经过 16 kHz 采样或低通到 8 kHz，另存为 48 kHz 不会重建被滤掉的频率。采样率只是格式能力和时间网格，不是来源质量证明。

## 3. 量化、位深与 PCM

采样解决“何时测量”，量化解决“用哪个有限码值表示幅度”。理想均匀量化步长近似为：

$$
\Delta=\frac{x_{max}-x_{min}}{2^b},
$$

其中 $b$ 为有效位数。位深增加会增加可用码值、减小理想量化步长，但不会消除模拟噪声、失真、时钟问题或前端 clipping。

**PCM（Pulse-Code Modulation）** 在本课指逐个保存量化样本的表示。常见数值类型包括：

- unsigned integer PCM：某些 8-bit WAV PCM 常以中点附近表示零；
- signed integer PCM：常见 16/24/32-bit PCM 以二进制补码附近的对称约定表示正负幅度，精确范围由格式规定；
- floating-point PCM：常用归一化浮点值处理，可能暂时超过 $[-1,1]$，但最终整数输出或模拟链仍有上限。

“24-bit 音频”至少有三层，不能只报一个数字：

| 字段 | 它回答什么 | 24-bit 的两种常见但不同的声明 |
| --- | --- | --- |
| **valid bits** | 样本中真正携带数值精度的有效位数 | 24 valid bits |
| **stored/container bits** | 每个 channel sample 在文件/API 槽位中实际占用多少 bit | 24（紧密 packed）或 32（24 位值置于 32-bit 槽位） |
| **block_align** | 一个 interleaved sample frame 实际占多少 byte | stereo packed 24-bit 为 6；stereo 32-bit 容器为 8 |

对简单的交错整数 PCM，`block_align = channels × 每个 channel sample 的已存储 byte 数`；后者通常是 `ceil(stored/container bits / 8)`，但应以格式字段为准。有效位深影响量化精度，stored/container bits 和 `block_align` 决定文件载荷大小。故“24 valid bits in 32-bit container”不能按 3 byte/channel 估算，也不要仅靠文件长度猜。

## 4. sample、sample frame、声道与时长

音频术语中的 **sample** 有时指单个声道的一个值，有时被口语化为同一时刻的整组声道。为避免歧义，本页使用：

- **channel sample**：一个声道在一个时刻的数值；
- **sample frame**：同一时刻所有声道的一组数值。

双声道、48 kHz 意味着每秒 48,000 个 sample frame，即 96,000 个 channel sample。文件中未压缩交错 PCM 的字节数据率应从格式的 block alignment 得出：

$$
R_{\mathrm{byte}}=f_s\times\mathrm{block\_align}\quad\text{byte/s},
\qquad R_{\mathrm{bit}}=8R_{\mathrm{byte}}.
$$

例如 48 kHz、stereo、**24 valid bits / 24 stored bits packed**，每个 channel sample 为 3 byte，因此 `block_align = 2 × 3 = 6`：

$$
48\,000\times6=288\,000\ \text{byte/s}
=2\,304\,000\ \text{bit/s}.
$$

十秒纯载荷为 2,880,000 byte；容器头、metadata、padding 另算。若仍是 24 valid bits、但存入 32-bit container，则 `block_align = 2 × 4 = 8`、数据率为 384,000 byte/s；数值精度相同，载荷却不同。

## 5. Interleaving 与 planar 布局

三帧 stereo PCM 可以有两种抽象布局：

```text
interleaved: L0 R0 L1 R1 L2 R2
planar:      L0 L1 L2 | R0 R1 R2
```

文件格式、API 和硬件可能选不同布局。把 planar 当 interleaved 会出现声道错乱或时间顺序错误；把 stereo channel sample 数误当 frame 数，会把时长算成两倍。

多声道还必须知道**channel layout**：六个声道不自动告诉你哪一个是 center、LFE 或 surround。声道数、声道标签/布局和 interleaving 是三个不同字段。

## 6. Endian：先按容器规范读字节

以 signed 16-bit 样本 `0x1234` 为例：

| 字节序 | 文件/内存中先出现的 byte |
| --- | --- |
| little-endian | `34 12` |
| big-endian | `12 34` |

不能用 CPU 原生字节序替代文件格式约定。RIFF/WAVE 常见字段采用 little-endian，但“所有 `.wav` 载荷都必然是最简单的 little-endian PCM”仍是过度推断：WAVE 容器可承载非 PCM、扩展格式和附加 chunk。读取时应解析 FourCC、chunk length、format tag、有效位深、block alignment 和 channel mask，再决定如何解释载荷。

底层整数与字节序基础见 [[计算机知识/30-计算机系统/01-数据表示字节序与对齐|数据表示、字节序与对齐]]。

## 7. 电平：dBFS 不等于响度

分贝表达的是比值。若比较同类幅度：

$$
L_{dB}=20\log_{10}\frac{|A|}{A_{ref}}.
$$

若比较同类功率：

$$
L_{dB}=10\log_{10}\frac{P}{P_{ref}}.
$$

### 7.1 peak dBFS

dBFS 以数字满刻度为参考。对归一化样本峰值 $p$：

$$
L_{peak}=20\log_{10}p\ \text{dBFS}.
$$

- $p=1$ 是 0 dBFS；
- $p=0.5$ 约为 -6.02 dBFS；
- 数字静音是零幅度，理想对数为 $-\infty$ dBFS。

固定点 PCM 中 0 dBFS 附近是码值上限，不表示某个固定的声压级。扬声器音量、DAC、功放和声学环境会决定实际 SPL。

### 7.2 sample peak 与 true peak

相邻离散样本之间的重建波形可能超过所有样本值，形成 **inter-sample peak**。因此 sample peak 没超过 0 dBFS，并不保证转换、重采样或有损编码后不会过载。true-peak 测量通过过采样/滤波估计连续重建波形的峰值，通常以 dBTP 表示。

### 7.3 RMS 与 LUFS

- RMS 描述一段数值信号的均方根幅度，不含完整听觉加权与节目门控。
- LUFS/LKFS 基于 ITU-R BS.1770 的频率加权、声道加权和能量汇总；节目响度工作流还会使用门控。
- LUFS 是对感知响度的标准化估计，不是人体在所有内容、耳机和环境中的完美听感。

不存在对任意音频都成立的“peak dBFS 减某个常数就得到 LUFS”。一个短促点击和持续正弦可以有相同 peak，却有完全不同的时均能量和响度。

> [!important] 当前规范边界（核验日期：2026-09-03）
> ITU-R BS.1770-5 是当前 in-force 的响度与 true-peak 算法入口。EBU R128 v5.0 在广播节目归一化语境建议 -23 LUFS；这不是所有流媒体、播客、游戏或个人项目必须套用的全球唯一目标。交付时应遵守目标平台的当前规范并保留 true-peak headroom。

## 8. Clipping：上游过载不能靠降低文件音量修复

当信号超出某一环节可表示范围，值会被截断或以非线性方式饱和：

```text
理想波形:    /\      /\
            /  \    /  \
clipped:   /----\  /----\
```

可能的 clipping 层包括麦克风胶囊、模拟前置放大器、ADC、固定点处理节点、混音总线、DAC 和功放。若 ADC 前已经削顶，进入文件的平顶样本丢掉了原峰形；之后整体衰减只会得到“更小声的削顶波形”。修复工具只能估计，不能证明还原原声。

判断时不要只找连续相同的最大整数：模拟软削顶、限幅器、浮点文件和后续增益可能没有这种简单形状。应结合波形、峰值/true peak、频谱、监听和信号链记录。

## 9. Dither：把相关量化失真换成噪声

将高精度信号降到较低整数位深时，直接舍入的量化误差可能与信号相关，尤其在低电平出现谐波或“砂砾感”。在最终量化前加入适当的小随机噪声，可以让误差去相关，使失真更像稳定噪声。常见 TPDF dither 用两个独立均匀噪声之和形成三角概率分布。

正确边界：

- dither 通常只在**真正降低有效位深的最终量化点**加入一次；
- 它不会恢复已 clipping 的波形，不会消除底噪，也不会提升采样率；
- 反复 dither 会累积噪声；中间浮点处理不应每一步都重新加；
- noise shaping 可把部分噪声能量推向听觉较不敏感频带，但会改变频谱和 headroom，需按目标采样率/用途验证。

> [!failure] 反例：加 dither 能把 16-bit 变成真正的 24-bit
> 错。dither 能改善低位深量化误差的统计性质，不能创造来源从未记录的精确信息。把 16-bit 样本放进 24-bit 容器只增加零位或计算空间。

## 10. 一份可审计的 PCM 描述

不要只写“48k WAV”。最低应记录：

```text
container: RIFF/WAVE
codec/sample format: linear PCM, signed integer
sample rate: 48000 sample frames/s
channels/layout: 2, L/R
valid bits per sample: 24
stored/container bits per channel sample: 24, packed in 3 bytes（若为 32-bit container 必须明确写 32）
block_align: 6 byte/sample frame（stereo packed 24-bit；不从 valid bits 猜）
byte rate: 288000 byte/s（sample_rate × block_align）
byte order: little-endian
interleaving: L0 R0 L1 R1 ...
duration/frame count: 明确数值
level evidence: sample peak、true peak、integrated LUFS 及所用标准/工具版本
metadata/privacy: 保留和删除的 chunk
```

这份描述把容器、样本格式、时序、布局、响度证据和元数据分开。它比后缀或“无损音频”更能支撑复现。

## 练习

1. 一段 90 秒、48 kHz、stereo、24-bit packed PCM 有多少 sample frame、channel sample 和纯载荷 byte？
2. 给定 interleaved stereo 16-bit little-endian 字节 `00 00 FF 7F 00 80 34 12`，按两帧 `L0 R0 L1 R1` 写出四个十六进制样本，并指出 `0x8000` 按 signed 16-bit 的含义。
3. 一个文件 sample peak 为 -1 dBFS，能否推出 true peak 不超过 0 dBTP？能否推出 integrated loudness 为 -14 LUFS？解释原因。
4. 录音机输入前置已经削顶，导入 DAW 后衰减 12 dB。波形是否恢复？dither 是否有帮助？
5. 设计从 32-bit float master 输出 16-bit PCM 的最后步骤，标出增益/限制、true-peak 检查和 dither 的顺序。

## 成功标准

- [ ] 得到 90 秒音频含 4,320,000 sample frame、8,640,000 channel sample、25,920,000 byte 纯载荷。
- [ ] 能从 little-endian 字节重建每个 signed 16-bit 值，并不把 channel sample 数当时长帧数。
- [ ] 能解释采样前抗混叠、重采样不能恢复已混叠信息。
- [ ] 能分别定义 sample peak、true peak、RMS、LUFS，不做固定换算。
- [ ] 能判断 clipping 位于哪一层，并说明后续衰减不是恢复。
- [ ] 能说明 dither 的使用时点、收益、代价和不能解决的问题。

## 官方来源与核验边界

以下入口于 **2026-09-03** 核验；本页据此说明算法和格式语义，不代表本机录放链已校准：

- [ITU-R BS.1770-5：Algorithms to measure audio programme loudness and true-peak audio level](https://www.itu.int/rec/R-REC-BS.1770)：当前响度与 true-peak 算法入口。
- [EBU R128 v5.0](https://tech.ebu.ch/publications/r128)：广播响度归一化、LRA 和 maximum true peak 的应用建议。
- [Microsoft WAVEFORMATEX](https://learn.microsoft.com/en-us/windows/win32/api/mmreg/ns-mmreg-waveformatex)：WAVE 音频流格式字段入口；它也说明 WAVE 可描述非 PCM 格式，不能只按后缀猜。

---

**上一站**：[[计算机知识/60-数据编码与媒体系统/05-图像表示色彩空间采样与图像编码|图像表示、色彩空间、采样与图像编码]] · **下一站**：[[计算机知识/60-数据编码与媒体系统/07-音频编码变换心理声学码率与延迟|音频编码：变换、心理声学、码率与延迟]] · **返回**：[[计算机知识/60-数据编码与媒体系统/00-数据编码与媒体系统-MOC|数据编码与媒体系统 MOC]] · **AI 出口**：[[AI/40-语音与音频模型/00-语音与音频模型-MOC|语音与音频模型 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/09-计算机网络-课程地图|计算机网络 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/35-计算机网络/04-UDP-TCP可靠传输与应用分帧|网络：UDP、TCP、可靠传输与应用分帧]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
