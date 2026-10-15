---
title: IQ与频谱离线实验
stage: 2
aliases: []
sources: []
prerequisites:
  - "[[电子电路/12-交流与变换域/19-复数包络IQ与FFT频移]]"
---

# IQ与频谱离线实验

先读 [[电子电路/12-交流与变换域/19-复数包络IQ与FFT频移|复数包络、双正交本振和FFT尺度]] 的定义与推导；本目录为其唯一源码单元，不要求复制到另一镜像。目标是复算 N=128、fs=128 Hz、fc=16 Hz、带宽4 Hz案例，把频谱图的每一个峰对应回公式。

在本目录运行已有 Python 环境即可测试，测试仅需标准库：

```bash
python3 -B -m unittest -v
```

生成可编辑 SVG、数据 JSON 与从 SVG 实际栅格化的360/425像素灰度及暗底 PNG，须指定**主库外**的绝对输出目录。绘图需要本机已有 Matplotlib、CairoSVG、Pillow；程序不安装依赖。可用本批已经存在的 Python：

```bash
MPLCONFIGDIR=/private/tmp/wwl-iq-mpl XDG_CACHE_HOME=/private/tmp/wwl-iq-cache /Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python -B build_visuals.py --output /private/tmp/wwl-iq-user-output
```

`build_visuals.py` 导入无文件输出，第三方依赖均在 `generate` 中加载；遗漏 `--output` 在解析参数时退出2，先于任何绘图库初始化。主库内输出被拒绝，缺依赖按实际错误退出，不隐式安装。库外候选包含本次已生成的 `assets`；真实客户端对 Obsidian 引用和阅读效果仍须另验。

`iq.py` 的所有函数只返回值，不写文件，也不启动GUI。`upconvert(z,fs,carrier)` 接收有穷数值复包络（V，峰值约定），返回真实RF电压；`mix(x,fs,lo,phase=0)` 接收有穷实电压，返回 `2*x*exp(-j*(LO+phase))` 的复数结果。phase 单位 rad，fs/carrier/lo/cutoff 单位 Hz；LO频率必须在0与fs/2之间。输入长度为2至4096的二次幂，支持有界读取迭代器；超过预算显式失败。bool、文本、二维数据、NaN、Inf以及真实电压输入中的任何复数（包括1+0j）均拒绝，先验证再转换成float。复包络和FFT接受有限复数；频域虚部不会丢弃。派生运算溢出显式失败。

`fft` 采用前向不缩放、逆向1/N；`bin_lowpass` 是对周期片段的非因果bin投影，保留 |f|≤cutoff。`demodulate` 另检查保守截止条件 `cutoff < min(lo, fs/2-lo)`；调用者仍须判断实际包络支持、频偏后通带及镜像是否分开，API不知道任意输入的模拟来源，不能宣称其已抗混叠。

`case.json` 保存样本和复数坐标对 `[real,imag]`，不把复包络当实波；输出参数固定，能直接核对正文。测试以独立DFT核对FFT，以周期三角投影核对I=2/Q=−1与RMS，并撤去增益、Q符号、LO相位、LO频率、采样和整bin假设。非整bin案例有可测恢复误差，不能视为滤波器已通过硬件验收。

本次仅验证本机CPU、公式数值和文件渲染；没有运行SPICE、TCAD、RF硬件、实时滤波器、浏览器/Obsidian UI或人类阅读实验。
