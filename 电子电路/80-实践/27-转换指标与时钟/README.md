---
domain: 电子电路
type: lab
stage: 4
content_status: usable
evidence_status: partial
aliases:
  - 转换指标与时钟实验
sources:
  - https://www.analog.com/media/en/training-seminars/tutorials/MT-003.pdf
  - https://www.analog.com/media/en/training-seminars/tutorials/MT-022.pdf
  - https://www.analog.com/media/en/training-seminars/tutorials/MT-008.pdf
  - https://www.analog.com/media/en/training-seminars/tutorials/MT-086.pdf
prerequisites:
  - "[[电子电路/42-转换器与采样时钟/05-静态动态指标与采样测试#动态测试从有限DFT功率开始]]"
  - "[[电子电路/42-转换器与采样时钟/06-过采样噪声整形与重建#ΔΣ的信号和噪声分别经过什么]]"
  - "[[电子电路/42-转换器与采样时钟/07-抖动相噪与时钟环#PLL各噪声源不是同一滤波器]]"
---

# 转换指标与时钟：有限 CPU 实验

本实验分别输出跃迁宽度、有限记录功率、理想统计噪声预算、非线性一阶调制器状态和时钟相位模型。图中的数值都是教学参数。任何一条噪声曲线都不能当作另一条的实际测量。

在本目录运行 `python -B -m unittest discover -s . -v`。生成器使用 `python -B build.py --output /absolute/empty/external/path`；`--output` 必填，拒绝主库和候选内输出以及已有非空目录。导入 models 或 build 不读取 argv、不绘图、不加载 NumPy/Matplotlib；生成时才加载 Matplotlib Figure 和 CairoSVG，局部 rc_context 不修改全局配置。调用者可将 MPLCONFIGDIR 设到库外可写缓存；依赖缺失时记录失败，不安装依赖。

`models.py` 只接受有限 Python int/float（不接受 bool、complex、object、嵌套数组），频域返回 complex 的接口是 ZOH 和 PLL。静态 2–8 位、跨度 .001–1000 V；DFT 偶数 N=16–256、记录幅度不超过声明的 .01–10 V 轨幅；基波功率至少 1e-12 V²。矩形相干测试不处理任意窗，谐波与 DC/基波相撞时拒绝，多个谐波同箱只计算一次。比基波低于 1e-18 的相对功率标为 None，含义是本教学分析下限，不能解读成物理零噪声。

理想带内积分 Δ=1e-6–10 V、整数 OSR=1–256，以独立均匀误差假设计算；一阶非线性 DC 调制器输入 −.95–.95、16–65536 步，保留状态和误差，不伪装独立白噪声。块平均要求完整块，M≤256；它的有限滤波器不是理想砖墙抽取器。ZOH 归一化频率比≤10000。

抖动模型要求 2πfinσ≤.05；精确正弦时点误差要求 fin·t≤1e6、|fin·δt|≤.01。相噪输入 2–16 节点、频率 1–1e9 Hz、L=−220至−40 dBc/Hz；相邻频率比≥1.01，在 log f 与 dB 间线性插值并解析积分，方差≤.1 rad²。频率带之外不外推；载波 1 kHz–1 GHz。PLL 仅为本章正参数 PI 二阶相位模型，a=.01–1e7 s⁻¹、b=1e-4–1e14 s⁻²、阻尼 .05–10，计算频率≤1e9 rad/s。它不替含延迟、额外极点、PVT 和时钟树的实际环路证明稳定。

`data/results.json` 记录单位与条件；CSV 分别保存有限谱的每箱功率、真实调制器比特/状态/误差和跃迁点。六个 SVG 可编辑；每个同源输出 360/425 px PNG。静态误差图、折叠谱说明和周期采样扰动共同贡献 V30；其他模块的混叠物理与完整组合仍需独审。L07 只贡献转换器和时钟预算部分，不宣称已完成噪声前端、硬件或人的学习验收。

测试用 NumPy FFT 和 Parseval 对照手写有限 DFT，用独立数值积分对照理想形噪公式，用原差分方程验证非线性状态不变量，以常数谱和 1/f 谱的手算检验相噪积分，用原开环 L 与特征多项式检验 PLL。CPU 模型、来源阅读、图像可读性分别记录；HDL、SPICE、硬件、真实客户端和人读未验。
