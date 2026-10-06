---
stage: 2
aliases: []
prerequisites:
  - "[[电子电路/64-光电探测与光子互连/01-发光探测与光波导]]"
  - "[[电子电路/64-光电探测与光子互连/02-光电前端与接收链]]"
  - "[[电子电路/64-光电探测与光子互连/03-调制光子集成与研究边界]]"
sources: []
---
# 光子电流与互连预算 CPU实验

同一850 nm链路：100 μW入口、10 dB最坏预算、外部QE .7、RF100 kΩ/CT10 pF/CF1 pF、A0=10⁵/fT10 MHz。参数和结果由`results.json`保存，频轴与输出PSD在`response.csv`；`calibration.csv`是正文四点解析标定数据，非硬件记录；源码是模型的唯一可执行定义。新实验没有已有code-sync镜像责任，因此不增第二份源码。图由原生SVG节点与lazy Matplotlib Figure曲线生成，示意结构不当真实制造尺寸。

## 命令与唯一源码

从主库根启动，以下CANDIDATE仅用于库外候选；发布后LAB可指向库内同名目录。输出必须是**不存在**且位于库外的新目录，重复运行换目录名，不自动删除旧记录。

```bash
PY="$PWD/.venv/bin/python"
LAB="/private/tmp/wwl-ee-revision-20261005-195537/frontier03/release/R2/电子电路/80-实践/38-光子电流与互连预算"
"$PY" -B -m unittest discover -s "$LAB" -v
"$PY" -B "$LAB/photon_models.py" --output /private/tmp/wwl-photon-numeric-NEW
"$PY" -B "$LAB/generate_figures.py" --output /private/tmp/wwl-photon-figures-NEW
```

[唯一模型源码](photon_models.py)、[独立测试](test_photon_models.py)、[图生成器](generate_figures.py)一起交接。NumPy用于独立KCL与Gauss求积和校准；Matplotlib/CairoSVG用于绘图。沿用现有环境，没有安装依赖。普通导入只用标准库，不解析argv、不生成文件、不引入NumPy/Matplotlib字体缓存。`generate`在成功/异常时恢复MPLCONFIGDIR/XDG_CACHE_HOME和rcParams，生成期间的临时字体缓存被清理；依赖首次加载本身不当做导入纯净证明。缺`--output`退出2且不写；已有目录/主库目录拒绝。

## API域与预算

`optical`支持P=0..1 W、λ=200..2000 nm、QE=0..1、被动损耗0..200 dB；这是有限算术域，材料适用波段仍需调用者验证。`tia`频率0..1 GHz、RF1..10⁹ Ω、CT10⁻¹⁵..10⁻⁶ F、CF0..10⁻⁶ F、A0 1..10⁹、fT1..10¹⁰ Hz，单极点/线性摆幅前提必须保留；不宣称全域都适合本器件。`output_psd`使用上述固定接收器，电流0...1 A、温度1..1000 K、非负有限白噪声幅度与Rsh1..10¹⁵ Ω；经典白模型不是所有温度/频率的物理保证。

`integrated_noise`限定带宽1..10 MHz、偶整数面板16..65536，明确步长B/N与模型误差；调用者比较加密结果，不能只凭预算下限称收敛。默认8192/16384与独立64点Gauss对照针对本例0..100 kHz。`mzi`电压±100 V、Vπ .001..100 V、相位±100 rad，不把范围解释为真实耐压；双端口保能。`calibrate`3..10000匹配实数1D样本，功率0..1 W、电流绝对值≤.1 A、已知暗电流，拒绝bool/complex/object/非有限/无激励。无效输入在文件创建前拒绝；校准不对未知上游耦合同时作唯一辨识。

## 可核对的结果与证据层

收到10 μW时Iph4.79899864 μA，DC输出−.479995064 V；100 kHz|Zt|100425.191 Ω，噪声0..100 kHz RMS41.3703553 μV。MZI正交点另分走一半可用功率，.1 Vpeak驱动给18.9257535 mVpeak小信号、30.6667670 μV噪声。16模型/边界/新进程测试，加成功与注入异常状态回归及再生字节比对，都是作者CPU证据，等待他人独审。

V42仅兑现光电转换、载流子节点、TIA噪声与相位转换半链；MEMS由F04贡献。无真实PD/激光器/光子PDK，无SPICE/光场/射频工具运行，无板或设备接入，无UI客户端/真人学习。固定λ、η、Id、Cj及Vπ后才谈同一链；真实生产需按正文校准流程更换适配器件参数并保留测量记录。
