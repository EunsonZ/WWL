---
stage: 2
aliases: []
sources:
  - https://docs.kicad.org/9.0/en/cli/cli.html
  - https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/
prerequisites:
  - "[[电子电路/50-PCB布局与调试/01-符号引脚封装与BOM替代#先确定电路，再决定空间]]"
  - "[[电子电路/50-PCB布局与调试/05-KiCad项目到制造包与人工复核#ERC和DRC回答不同问题]]"
---
# RCDAQ-P1：同一板、不同证据层

基础入口按J1→R1→OUT→C1/R2→GND手算1V加载；快进入口核21焊盘、4网、27前层segments、5地via的几何图与采样电荷/频率阻抗边界。全部模型和图对应同一原创40×30mm无源板，ADC在J2外部，没有假装板上IC/MCU存在。

## 文件与版本

board.json是教学坐标/引脚/路由合同；project有rcdaq.kicad_pro/sch/pcb，自有symbol/footprint库与librarytables、rcdaq.net、bom.csv/testpoints.csv、fabrication-checklist。原生格式候选可编辑但本机未发现kicad-cli，真实软件parse/save、ERC/DRC、B.Cu填区、Gerber/钻孔导出尚未运行。CPU解析只是有限s-expression字段与网集核对。采购MPN全部UNSELECTED；自有0805等几何尚未经实际MPN/厂商规则核，不能送厂。教学源文件generator标wwl_pcb1，未伪装成eeschema/pcbnew写出的工具产物。

源pcb_model.py/test_pcb_model.py/generate_figures.py各只一真源，不创建重复code-sync副本；原库与他人源码未动。SVG是真源生成输出，360/425PNG从同SVG渲染，图是原创教学模型，不是实际CAD截图/照片/仪器读数。

## 有限API及物理合同

模型只接受Python原生int/float实数，拒bool/complex/数组/cast对象及非有限；先校验再算，不静默丢虚部。标量支持域刻意有限：t0..100s、source/initial0..3.3V、R/load/probe1..1e9/1e12Ω、C1pF..10mF。rc保持v(0)=initial，expm1计算小时间步，明确load与probe并联；返回V、τ(s)、pole(Hz)、gain无量纲，t非常大视为稳态指数衰减。

sharing/coupling按指定初态电荷守恒，不是实测ADC参数；内部C1fF..1mF、crossC1fF..1μF，外C1pF..10mF，电压/edge±3.3V合同分别校验。loop f0..1GHz、L0..1mH、ΔI±1A、edge1ps..1s、R0..1MΩ；decap f1..1GHz、C1pF..10mF、ESR0..1MΩ、ESL1fH..1mH，返回阻抗实/虚/幅及理想自谐振、容量与ESR项。模型域只保证计算有限，不证明任意参数可物理实现；同一L不能重复算入元件/线路，图2/20nH为假设非提取。energy最多32个有限C、V≤3.3V，只算本板电容不包含外电源/线缆。

geometry只收原生dict/list坐标和有限标签：最多128pads、64via、8nets、每网≤64paths/每path≤64points，总segments≤512、正交非零路径；板内范围.5..39.5×.5..29.5mm。输出中心线异网交叉、按本教学焊盘尺寸的异网接近、明确图连接。GND把via及THT GND视为矩形B.Cu连续面锚点，这是**模型假设**，实际zone未填；不替代ERC/DRC、铜多边形/热焊盘/最小孔距/EM场。所有图算法迭代有固定预算，没有浮点while找收敛。

## 运行方法

复制完整实验到库外新目录。两个CLI必须显式--output，缺参exit2不写caller/MPL/XDG；导入不解析argv，不写、不初始化绘图/字体，不改PRNG。generate(output)与main(argv=None)可显式调用。数值stdlib；图仅在generate内部lazy import已有matplotlib/CairoSVG，direct Figure、rc_context，MPL/XDG缓存限定输出下并恢复环境；成功/绘图异常均恢复环境与rcParams，缺依赖not_run、不安装。

```bash
python -B -m unittest discover -s . -p test_pcb_model.py -v
python -B pcb_model.py --output /private/tmp/rcdaq-my-numeric
python -B generate_figures.py --output /private/tmp/rcdaq-my-figures
```

results.json和assets/figure-data.json分别标SI电路及mm几何，RC R1k/C1u/RL10k，初值.4V。板图按同board.json引用与坐标，不追求虚假真实照片。改CAD应同步引脚网表/BOM/testpoints及模型版本，比较修改的来源，不把旧hash的结果当新板结果。

## 工具和实物的验收接口

正文05给真实KiCad9可执行命令及制造清单，正式执行须记录工具版本、输入SHA、原始输出、parity/填区和人工复核。教学CAD没有供应商批准的制造参数或可采购BOM。仪器接地、限流计划与故障树在正文06；实际上电/探针/照片/硬件测量都未跑。

V35贡献为连续/分割回流、F/B剖面、GNDvia、外ADC去耦真实闭环与明确基带/边沿频段；资格待独审。V37只有同板原理图/布局/TP和安全计划，缺同板授权照片/实物仪器证据，partial。未消费ArduinoUno/photo线索，也未借单元件照片拼凑同板。X13仅解释有限RLC/频率模型边界，不签完整场/PDE桥。SPICE/EM提取/KiCad/UI/ERC/DRC/manufacture/Gerberviewer/hardware/humanlearning均not_run。
