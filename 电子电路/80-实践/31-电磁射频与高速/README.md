---
domain: 电子电路
type: lab
stage: 5
content_status: usable
evidence_status: partial
aliases:
  - 传输线射频与高速模型实验
sources:
  - https://ocw.mit.edu/courses/6-013-electromagnetics-and-applications-spring-2009/790b8f65328723ec194cb440b303f8fb_MIT6_013S09_chap07.pdf
  - https://ocw.mit.edu/courses/6-013-electromagnetics-and-applications-spring-2009/f52f07ed81b664331bee2fec67df7db6_MIT6_013S09_chap08.pdf
  - https://www.ti.com/lit/an/scaa082a/scaa082a.pdf
prerequisites:
  - "[[电子电路/46-电磁射频与高速/02-传输线反射与终端#边界消元与格图]]"
  - "[[电子电路/46-电磁射频与高速/03-阻抗匹配与S参数#实参考功率波与S矩阵]]"
  - "[[电子电路/46-电磁射频与高速/07-天线与辐射入口#用完整球面积分区分三个指标]]"
---

# 电磁、射频与高速：有限CPU模型

读者沿同一0.1 m、50 Ω线分别检查传播、边界、阻抗变换，再切换到有条件的射频功率链、差共模/ISI、电源端口与天线。模型输出独立对象，不能把所有图统称成“仿真通过”。参数均为教学构造，未取某块实际PCB或器件的保证参数。

在本目录运行 `python -B -m unittest discover -s . -v`。生成用 `python -B generate.py --output /absolute/empty/external/path`；参数必填，输出拒绝候选或主库内部、已有非空目录。调用者可设置库外 MPLCONFIGDIR；依赖缺失不安装。导入 models/generate 只加载标准库，不执行 argv、写文件或加载绘图/数值重依赖。生成才加载 NumPy、CairoSVG、Matplotlib，采用直接 Figure 和局部 rc_context，不导入 pyplot或改全局 rcParams。

`data/parameters.json` 保存单位和原始教学参数，`data/results.json` 保存开放端格图的有限事件/行波、Smith点、噪声功率链、立方非线性、IQ镜像、有限码型、PDN端口和Friis预算。复结果以re/im记录；它们不是实数被偷偷丢弃的虚部。

## 有限接口与失败条件

实数入口只接受Python int/float，不接受bool、complex、object、容器、NaN或Inf；频域专用 phasor 接口明确允许有限complex。没有无限迭代或生成任意精度通用求解器。

| 接口 | 输入对象与合理范围 | 返回与条件 |
| --- | --- | --- |
| lossless | L′=1e−9–1e−3 H/m，C′=1e−13–1e−6 F/m，长1e−4–100 m；速度1e5–3e8 m/s | Z0 Ω、速度m/s、单程s；均匀无损线 |
| rlcg | R′0–1000 Ω/m、G′0–.1 S/m，L′/C′如上，f1 Hz–10 GHz | γ 1/m与Zc Ω，线性同频准TEM，不输出任意有损阶跃 |
| reflection / input_impedance | 实参考1–1000 Ω，有限被动复负载模≤1e6 Ω；None专指开路；θ±100 rad | Γ或Zin；输入阻抗极点邻域abs(1−Γ)<1e−10拒绝，应改用Γ坐标 |
| bounce | Vs±10 V、源0–1000 Ω、负载0–1000 Ω或None、Z0 1–1000 Ω、T1 ps–1 ms、rounds1–24 | 有限事件和波段，不宣称稳态；理想源开路q=−1保留未衰减反例 |
| power_waves | RMS V模≤1e6 V、I模≤1000 A、实参考1–1000 Ω | a/b √W及净W；不接受复参考冒用实公式 |
| friis_noise | 1–8级[G功率,F因子]，G .001–1e4、F1–1e4 | 总线性F、NF dB、G；同频线性匹配/同带/独立新增噪声 |
| cubic_output / cubic_metrics | x±1 V、a1 .1–100、a3 −100–0 V⁻²；指标要求a3≤−1e−4 | 单音压缩和两音外推IP3，IP3不表示可真实在截点工作；真实样本输出域和外推截点域分别声明 |
| iq_image | Q增益.5–1.5、相位误差±.5 rad | αz+βz*的系数及镜像比，完美时IRR为None（无镜像模型极限） |
| differential_skew | 单腿峰1 μV–10 V、f1 Hz–10 GHz、延迟0–1 μs、fτ≤1000 | 差模与共模峰值相量；以同一参考面为前提 |
| eye_record / isi_margin | 16–128个±1整数码，UI1 ps–1 μs，τ/UI .05–2，16–128 samples/UI；1–8符号抽头 | 精确单极恒输入更新，初值0保留；(n+1)Δt更新后时刻。抽头裕度是有符号代数余量，负值表示眼闭合而非负几何高度 |
| pdn_impedance | f1 Hz–10 GHz，1–8[C,ESR,ESL]支路，C1 pF–.01 F、ESR .1 mΩ–10 Ω、ESL1 pH–1 μH；源R .1 mΩ–10 Ω、L1 pH–.1 mH | 同一IC供回端口总Z与各支路Z；安装/偏压/PVT未知，不代替场求解 |
| dipole_pattern / friis_link | θ0–π、φ±2π；Pt馈线入射1 nW–1 kW、G .01–1e4、f1 MHz–100 GHz、r .01–1e6 m且r≥10λ、极化/匹配因子0–1 | 归一功率半径真实xyz/方向性；功率预算用增益已含辐射效率，输入接受比例单独乘。r≥10λ只是教学数值域，孔径、环境、远场和互易仍由调用者检查 |

`power_waves` 的净功率按 RMS 端口量 $\operatorname{Re}(VI^*)=V_rI_r+V_iI_i$ 计算，两个实乘积用 `math.fsum` 求和；a/b 仍按原定义返回。数学恒等式 $|a|^2-|b|^2=\operatorname{Re}(VI^*)$ 不保证用已舍入的两个大波功率相减能保留微小净功率。例如 $V=10^6\,\mathrm V$、$I=\pm10^{-12}\,\mathrm A$、$R_0=50\,\Omega$ 属于声明教学域，净功率为 $\pm10^{-6}\,\mathrm W$，直接相减却可能返回零。新回归核对正负、纯虚同相、正交及不同实参考；这是浮点实现合同，不能解释成真实高压测试或任意精度保证。

参数域只保证教学计算有明确范围，不宣称所有硬件物理都在域内，亦不把每个域内输入都解释成某个真实产品。返回有限步数组不意味着传播过程已数值收敛。

## 如何复算与质疑

19 tests 用原一阶PDE导数检验行波，用每次入射/出射重新代入源/负载边界核验20种终端组合，以已手算的4/3、8/9、28/27负载电压对照格图。Smith用开短匹配与λ/4的另一阻抗式；功率波与Re(VI*)核对；噪声以逐级新增噪声功率核对Friis；两音有限波形的三角投影检验IM3，单音实波形检验1dB压缩。IQ直接实坐标投影、眼图原ODE解析更新、PDN原KCL、球面数值积分和能流×有效面积各作为独立基准。

八个原创SVG各有360/425 px PNG。V38通过格图、开短匹配对照与Smith映射提供完整候选视觉；是否签收由独审判断。V35仅本组回流/层叠/去耦回路部分贡献，待M22实际PCB内容组合。X13的实际数学目标与电子回访步骤在正文02，候选不修改旧数学页面反向链接。

来源、CPU、作者渲染检查分别交接。SPICE、VNA校准、EM求解器、EMC、硬件、真实UI和人读均未运行，不从图像外观推定它们通过。
