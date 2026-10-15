---
type: lab
domain: electronics
stage: 3
content_status: usable
evidence_status: partial
aliases: []
sources:
  - https://www.ti.com/lit/an/slva057/slva057.pdf
prerequisites:
  - "[[电子电路/48-电源与功率变换/03-BuckBoost与断续导通#Buck两状态和第三个拓扑]]"
  - "[[电子电路/48-电源与功率变换/05-状态平均与电源控制#从两个状态到同一个平均场]]"
---
# 分段电源与平均控制：CPU复算

学习问题：相同12→5 V Buck电路，平均值、纹波、导通模式和控制包络分别由什么决定？先从第03章的真实节点读出状态，在本页用另一种方法核对闭式和数值，而非把绘图结果叫实体效率。

主源码是 `power_models.py`；`test_power_models.py` 独立用伏秒、三角面积、解析LC初值解、能量积分及母线三相KCL核对。`generate.py` 是唯一资产生成器，只有明确调用 `generate(output)` 或带必填 `--output` 的 main 才导入绘图库和写新输出。没有源码镜像。全部测试/生成均为离线CPU，未安装工具，未跑SPICE、板级仿真或硬件。

## 从库根复算到新外部目录

已有 `.venv` 包含本机绘图依赖；缺依赖应记录，不自动安装。下列输出必须是新目录，不能覆盖正文资产；函数拒绝主库或源码子树，缓存用临时目录，调用后恢复原MPLCONFIGDIR/XDG_CACHE_HOME环境。

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/32-分段电源与平均控制' -p test_power_models.py -v
.venv/bin/python -B '电子电路/80-实践/32-分段电源与平均控制/generate.py' --output /private/tmp/wwl-power-reproduction-new
```

## 精确输入、采样及算法合同

参数单位全部SI，Params只接收Python实int/float，先拒bool、complex、container及非有限，再转换。领域：Vin6–24 V、L/C50–500 µH/µF、R2–200 Ω、fs50–200 kHz、d.05–.95。初态i0=0–10 A、v0=0–Vin；数值中状态绝对值必须<100（各变量按A/V各自检查，非物理混单位范数）。遇反向on电流就拒绝，因为当前模型仅承诺正常低压二极管Buck，不自动扩展成同步反向网络。

`simulate` 每周期先采样v，令d=clamp[D+K(Vref−v)]，再在on/off各分steps步RK4；cycles1–2000、steps16–256，无无限自适应迭代。切换边界显式分割，电感到零事件52次以内直接符号二分并有相邻float停止，余下idle用精确指数放电。`average=True`使用相同周期内样保持d与同一时间网格，积分平均场；它**不恢复纹波**。本实现是比例控制，不是完整PI/PWM器件。缩步与完整终点分别核验。

`conversion`给三种理想CCM比值和严格DCM域的闭式，边界单列，不能将DCM根用于CCM。`buck_summary` 的 `v_V` 使用声明模式；含ccm名称的能量/电容纹波字段是CCM候选估算，不能误读为DCM实际能量。`state_matrices`返回两状态A/B，`buck_gvd/boost_gvd`明确小信号零初态。`design_candidates()`枚举固定12组L/fs，以Ploss/(1 W)为无量纲目标，筛Δi≤.3 A、理想ΔvC≤.01 V、假设全部损耗落在一个40 K/W教学节点的温升≤10 K。这个共享热节点是有意简化，非真实MOS结温；不调用全局优化器，也不保证响应/器件尺寸。小信号可以合法复数输出；入口ω是实rad/s。Boost的正实零点按CCM固定阻载推导。

`losses`仅在CCM理想Q附近估算恒Ron/DCR/Vf、固定线性边沿及恒Coss；记录每项W、总W和该估算效率，不将任意参数不确定性藏成“实测”。`thermal`是已声明系统Rth/热容的单节点闭式，与封装θJA表区分。`magnetic_delta`只用伏秒算T，不猜芯材饱和或Steinmetz系数。`pwm_phases`返回三相占空、浮N相电压及线电压，未控制真实电机。

## 数据和可观察层

`assets/parameters.json`含同参数身份、矩阵、CCM/DCM值及损耗账户；`waveforms.csv`给秒、A、V、状态标签、样保持d，均明确合成CPU。其中CCM最后两周期由2000周期积分提取，DCM由500周期提取；平均/分段比较使用相同数值初态(.49 A,4.95 V)，400周期、每区间32步、K=.01 V⁻¹；分段模型的初态是周期开始瞬时值，平均模型初态是慢状态。把二者数值设成一样是本例的比较约定，不声称这个瞬时值等于同相位周期均值。生成前逐点确认分段无idle且两者i始终>0；parameters.json记录完整轨迹的模式与最小电流，CSV为每16步抽样，不能单凭稀疏CSV证明无零电流事件。图的第二行显示i，第一行显示v。有限波形差异包含初值约定、采样和平均近似，不是普遍误差界。原(.4 A,4 V)会出现第三态，而CCM平均场可给负i，它保留在回归中作为越域反例，不能称差异只是快纹波。CSV事件含on/off/idle，不冒充真实门极、VCD或示波器。

图为18组、每组可编辑SVG和360/425 PNG。其中Buck三状态/波形/DCM/控制承担V36，另有必要驱动、磁性隔离、整流/三相/LLC和EMI机制图。白底深色线条，颜色不是区分轨迹的唯一手段，线型和文字同时标识。LLC用真实半桥、三个储能支路、变压器与四二极管桥；下方a/b是同名次级网络，不接到初级0。

|证据层|交付意义|仍未验证|
|---|---|---|
|闭式推导|周期稳态、单位、理想CCM/DCM/RHP零点条件|真实器件偏差|
|CPU测试|指定有限域的例子、非法输入与数值收敛|一般任意输入或全部电源拓扑|
|可再生资产|源码与数据的身份一致|Obsidian客户端与真人理解|
|硬件/SPICE/工艺|未运行|驱动SOA/磁芯温升/保护时限/EMC安规|

图中开关是理想状态符号，驱动及保护图补充实体责任，但不能拿图作为器件选型认证。进一步任务是带着某一明确器件版本补寄生、损耗与最坏角条件；本实验不授权硬件或外部安装。

所有电路图的无点交叉不连接；圆点和导线端点/T 形接入表示同一网络。标注 a/b 的隔离次级命名网与初级返回分开。
