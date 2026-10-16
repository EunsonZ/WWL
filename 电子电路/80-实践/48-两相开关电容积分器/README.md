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

## 有限OTA两状态复算

有限窗口中，转移末输出w与下一拍转移前输出y可能不同。新增源码 [finite_ota_budget.py](finite_ota_budget.py) 保存反馈电荷归一值r与实际输出y两个状态，按先φ2转移、后S2断开的孤立窗口复算。它是正文声明的单极点OTA电压端口模型；开关理想、采样已建立、输出连续，无压摆或饱和。静态增益的精确分数与有限窗口的浮点指数分别给出。旧理想实验继续使用上面的入口。

从WWL根运行，输出必须是不存在或为空的新目录：

```bash
python3 -I -B '电子电路/80-实践/48-两相开关电容积分器/finite_ota_budget.py' --out-dir /private/tmp/sc-finite-output
```

默认输入是相邻的 [finite-ota-inputs.json](finite-ota-inputs.json)。更改实验请复制输入到新文件，使用 `--inputs /private/tmp/sc-finite-inputs.json --out-dir /private/tmp/sc-finite-other`。标量都是有理数字符串，电容单位F、时间s、电压V、OTA输入单边Hz谱V²/Hz。Cs、Cf、A0、taua、误差目标及最大步幅为正，Cp、两个窗口和白源谱允许0。输入samples是一维L项（1≤L≤32），eta_cov_V2必须为L×L精确对称半正定矩阵，单位V²；它声明已有采样端口协方差，代码不另添kT/C。非零初态同时给y0_V与s0_V：它们决定初始Cf电荷，不能只给y。Vos_V是固定输入等效偏置，不是随机源。

| 固定有限模型输出 | 核对用途 |
| --- | --- |
| [finite-data/phase-budget.csv](finite-data/phase-budget.csv) | 逐窗Q、目标、w、下一y、求和节点、电荷；电荷C，电压V |
| [finite-data/noise-budget.csv](finite-data/noise-budget.csv) | 每个样本对最后y的采样/两相OTA端口权重，无量纲；协方差在输入JSON、方差在results.json |
| [finite-data/results.json](finite-data/results.json) | 精确静态递推、M为2×2/N与G为2×1、时常s、选定端口预算与窗口条件 |
| [finite-data/finite-phase.svg](finite-data/finite-phase.svg) | 同一首样本的连续两窗轨迹：w=0.254608529 V，下一y=0.252580326 V |

输出拒绝非空目录、输出符号链接、文件目标以及源码/输入目录及其祖先。参数验证与结果有限性检查在写入前完成；交付finite-data应保留，用新目录复建后比较。零窗口合法，表示该窗没有经过时间，不能据此投影回静态关系。输出方差只覆盖给定eta与声明的白OTA输入源；不认证真实器件总噪声。

[[电子电路/80-实践/48-两相开关电容积分器/05-有限OTA源码与验证|有限模型完整源码镜像]]兑现代码阅读入口。推导、适用条件及四道迁移题的完整答案见 [[电子电路/42-转换器与采样时钟/08-开关电容电荷时序与离散传函#有限直流增益：剩余电荷使积分器漏积|有限增益推导]] 与 [[电子电路/42-转换器与采样时钟/08-开关电容电荷时序与离散传函#有限OTA与噪声的无提示迁移|有限模型迁移区]]。第二题改A0=50、Cp_F=1/5000000000000、Tphi2_s=9/100000000、Tisolated_s=1/12500000、s0_V=-1/100，保留y0_V=1/2；重建应得首w≈0.303361217 V、下一y≈0.248679655 V。

底板先断与器件端口另到[[电子电路/80-实践/50-SC底板时序与误差端口/README|实践50]]：用同一给定q/C模型比较两种断开顺序、跨clock与反馈off，并将超额电荷/真实负载接回本源的M。该后续四开关拓扑的信号符号/采样电荷不同，不能沿用这里的输入N；本实验旧源/镜像和数据继续保留。
