---
domain: 电子电路
type: experiment
stage: 4
content_status: usable
evidence_status: partial
aliases: []
sources:
  - https://www.eecis.udel.edu/~vsaxena/courses/ece697A/s10/Lecture%20Notes/Switched%20Capacitor%20Design/Switched%20Capacitor%20Circuits%201.pdf
prerequisites:
  - "[[电子电路/42-转换器与采样时钟/08-开关电容电荷时序与离散传函]]"
---
# 两相开关电容积分器的电荷复算

本实验回答：同一两相网络中，每拍哪一块板带来新电荷，输出如何保留初态，改在转移后读取为何少一个离散延迟？先读 [[电子电路/42-转换器与采样时钟/08-开关电容电荷时序与离散传函#两个相位的电荷账本|实际端点与守恒集合]]，再用此处数据核对每行的符号、单位和读相。

规范源码 [sc_charge_lab.py](sc_charge_lab.py) 只用 Python 标准库；电容、电压与电荷用 `fractions.Fraction` 精确运算。它模拟理想OTA完全建立的电荷端口，未求解MOS开关、运放瞬态、热噪声、采样混叠或真实ΔΣ环路。图中的相位间隔是协议示意；运行成功不能认证器件摆幅、建立或噪声。

## 固定输入与可复算输出

[fixed-inputs.json](fixed-inputs.json) 将SI值写成有理数字符串：$C_s=10^{-12}$ F、$C_f=4\times10^{-12}$ F、寄生对照 $C_p=2\times10^{-13}$ F、$f_s=10^6$ Hz、$y_0=1/2$ V与四样本 $(1,-1/2,3/2,-1)$ V。输入数组shape为(4,)，状态 $y[0..4]$的shape为(5,)，转移后读数数组shape为(4,)；不是四路同时采样。一般入口接受1至100个样本，图仅画前至多四拍记录。

默认理想账本用无寄生 $C_s$；同一次运行另算A到0的并联 $C_p$。它不是在默认物理模型中遗漏该寄生，而是用两组明确的端点对象比较。两组都用同一输入和初态，没有重新抽样。

| 固定输出 | 要核对的问题 |
| --- | --- |
| [data/charge-ledger.csv](data/charge-ledger.csv) | 每拍 $q_{f,s}^{\rm old}+q_{s,A}=q_{f,s}^{\rm new}$，转移后Cs A板为0 |
| [data/parasitic-ledger.csv](data/parasitic-ledger.csv) | A到0新增 $C_px[n]$如何改变每次转移 |
| [data/results.json](data/results.json) | 实际端点、开关状态、shape、系数与所有SI电荷字段 |
| [data/phase-endpoints.svg](data/phase-endpoints.svg) | 两开关究竟连接哪两点，每一相哪些导通 |
| [data/read-timing.svg](data/read-timing.svg) | 同拍转移前y[n]与转移后w[n]的读取位置及有限样本分解 |

CSV电荷字段单位为C，JSON有理数都是精确字符串。正文表换成pC显示，需要乘 $10^{12}$；不能把CSV中的分母当数值精度不足。输出摘要为：

```json
{"Req_ohm": "1000000", "alpha": "1/4", "alpha_with_Cp": "3/10", "w_after_V": ["1/4", "3/8", "0", "1/4"]}
```

无寄生转移前读数为 $[1/2,1/4,3/8,0]$ V，转移后为 $[1/4,3/8,0,1/4]$ V。固定 $C_p$对照转移后为 $[1/5,7/20,-1/10,1/5]$ V。每行零输入项恒1/2 V，零状态转移后为 $[-1/4,-1/8,-1/2,-1/4]$ V，二者相加复现总输出。

## 在新目录复建

从WWL根运行下列命令，`sc-output`必须不存在或为空；可选其他新目录。脚本拒绝非空目录、符号链接输出目录以及源码/输入目录及其祖先，保全已有输入和输出。非法输入在创建输出前拒绝。不覆盖交付的data目录；重建后再逐字比较。

```bash
python3 -I -B '电子电路/80-实践/48-两相开关电容积分器/sc_charge_lab.py' --out-dir /private/tmp/sc-output
```

如需改变输入，先将固定JSON复制到新文件，修改六个已有字段，使用 `--input /private/tmp/sc-input.json --out-dir /private/tmp/sc-other-output`。标量必须是有理数字符串；Cs、Cf、fs正，Cp非负，x是非空一维列表。数值、零分母、非正参数、额外字段与空数组都拒绝，不默默变成浮点、截断或补默认值。$y_0$和样本可正、零、负。合法非固定输入只核其确定电荷；并不自动改变模型适用条件。

核对总输出还需独立检查每拍电荷等式、初态分解和读取协议；简单逐字重建是同源一致性证据。[[电子电路/80-实践/48-两相开关电容积分器/04-源码与验证|完整源码镜像]] 与规范文件一致，便于在正文中阅读。迁移任务与完整答案在 [[电子电路/42-转换器与采样时钟/08-开关电容电荷时序与离散传函#无方法提示的迁移任务|课程迁移区]]；完成本实验后带着改变的端点、初态与时刻回去，核对为何方程变化。

本实验的确定模型不按每拍自动加 $kT/C$；边际方差及跨拍相关需回到 [[电子电路/38-随机噪声与测量/04-积分带宽与kT-C#开关保持和其他耗散改变了问题|噪声保持协议]]。真实器件、台架、Obsidian显示/同步与真人迁移未由本代码认证。
