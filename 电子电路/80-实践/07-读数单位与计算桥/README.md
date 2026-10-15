---
type: experiment
domain: electronics
stage: 1
content_status: usable
evidence_status: partial
aliases:
  - 读数与计算桥解析实验
sources:
  - "https://media.fluke.com/62682b5a-9860-440d-a754-b2d90062deb6_original%20file.pdf"
  - "https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html"
prerequisites:
  - "[[电子电路/05-数学与物理桥梁/06-两节点矩阵尺度与数组复算]]"
---
# 读数、单位与计算桥：解析实验

从每一个带单位输入生成一个可核对预测。core_lab.py是模型真源，无硬件/网络访问；test_core_lab.py核对守恒、积分、加载、单位和数组；build_visuals.py用局部Matplotlib配置绘图，导入不出图，必须给--output。没有code-sync镜像、没有仪器接线或实测动作。

## 从函数到数据

函数divider接受vs_v、r1_ohm、r2_ohm、rl_ohm，以V返回输出。None表示开路，不能传0Ω冒称开路；负电阻、bool、NaN/Inf等无效输入报错。函数数组示例在06正文逐行解释。当前函数是本组有限双精度教学参数下的解析模型，不保证任意极大/极小有限数字可计算；实际器件也不因函数返回有限就通过认证。

assets/predictions.json保留单位字段、四负载预测、源吸能账、探头教学参数、两节点电流/电压与两份实际网表；assets/charge-data.csv把分段电流的时间、电压、净电荷、储能记录为SI。measurement-record.csv将理论预测和实测列分开，实测、设备、量程与插孔列空白；不得把预测转抄成实测。

## 复现

从库根执行下列相对路径命令，使用现有.venv；生成结果写到库外的新目录/private/tmp/wwl-corebridge-reproduction，保留发布assets。实际版本Python3.14.7、NumPy2.5.3、Matplotlib3.11.2、CairoSVG2.9.1；无需安装。

```bash
.venv/bin/python -B -m unittest discover -s 电子电路/80-实践/07-读数单位与计算桥 -p 'test_core_lab.py' -v
MPLCONFIGDIR=/private/tmp/wwl-ee-corebridge-mpl .venv/bin/python -B 电子电路/80-实践/07-读数单位与计算桥/build_visuals.py --output /private/tmp/wwl-corebridge-reproduction
```

八项测试覆盖：精确5/6与多负载KCL；两源吸能和功率交叉项；RC瞬时/积分能量守恒；分段正负电荷与能量；dB阻抗条件/对数反算；探头KCL/表负担；节点残差/功率/单位缩放/弱接地敏感性；无效输入。CPU运行不验证真实接法、保护地或读数。

## L00和L01的当前合同

| 合同项 | 当前交付 | 证据边界 |
|---|---|---|
| L00节点表与预测 | 仪器页s/a/0定义、V03节点电流图、JSON节点数据 | 解析模型 |
| L00仪器接法 | 并联V表、串联A表、实际地夹导通模型SVG | 手册原则已读，真实设备未确认 |
| L00限流与断电 | 0–5 V/5 mA教学目标、断电改线和插孔检查说明 | 无设备/限流/断电实测 |
| L00实测记录 | CSV实测字段空白 | 不制造读数 |
| L01分压两解 | accepted foundation主解释的直接分压与Vth=1 V、Rth=800Ω；本组Fraction和KCL复算RL4kΩ得5/6 V | accepted正文 + 本组CPU |
| L01加载数据 | 本组预测数组；已有accepted V04曲线继续为主图 | 不重复生成冻结图 |
| L01实测 | 未执行 | 不称实验完成 |

## 可编辑视图

V02-source-absorption补源吸能实际网络；V03-two-node-currents补各支路箭头；V07-magnitude补复数模距离。它们是局部新资产，未修改任何accepted foundation图。另有meters、earth-path、probe-loading、energy-ledger、exp-db、charge-slope共9SVG/PNG。电路SVG原宽360/font14，统计图4.25in竖排，文字可编辑；PNG与SVG来自同一figure或电路SVG派生。图是合成解析图，不是器件照片或仪器截图。

未执行全库结构/测试、真实Obsidian、SPICE、硬件或真人陌生题；独立语义签收仍待完成。来源原读段与输入版本在库外source-reading.md、accepted-inputs.json及READY.md。
