---
type: practice
domain: electronics
stage: 1
content_status: usable
evidence_status: partial
aliases:
  - 偏置与基本放大CPU复算
sources:
  - https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/716bbb88c4269cde3dc6cc8f9cd90f64_MIT6_012S09_lec19.pdf
  - https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/6b80a6c37210c326a3cd72e684ddd68b_MIT6_012S09_lec20.pdf
  - https://ocw.mit.edu/courses/6-012-microelectronic-devices-and-circuits-spring-2009/0e19807429a2e5bd8d181661cb23c5b4_MIT6_012S09_lec25.pdf
prerequisites:
  - "[[电子电路/26-放大电路/01-偏置与热稳定]]"
---
# 偏置与基本放大 CPU 复算

本实践回答：静态节点、电流、器件局部导数、端口 KCL 与宣称的增益能否在同一模型内相互回代？这是 M10-01..04 的理想化 CPU 支撑实践，没有进行 SPICE、实际器件测量、温升实验或工艺失配统计，不认领其它实验合同。

初次使用先打开四篇正文的节点图，再看 `results.json` 中 `mos`、`bjt` 两个 Q；快速使用则从下面的函数接口开始。数值单位统一为 V、A、Ω、S，K 为 A/V²，lambda 为 1/V，温度未作为该固定参数模型的输入。图上为易读可以显示 mA、kΩ，但代码输入不采用混合单位。

## 可复算接口

|函数|具体问题与返回|允许范围与边界|
|---|---|---|
|`mos_point(vgs,vds,k=.002,vt=1,lam=.02)`|饱和模型的 I、gm、go、ro|VDS≥VOV>0，K>0、lambda≥0；lambda=0 的 ro 用 None 表示无限大|
|`mos_bias(vg=2,vdd=5,rd=2000,rs=0,...)`|闭合漏/源电阻回路后求 Q|先正区间求根再检查饱和；截止或三极区明确失败|
|`bjt_bias(vdd=5,rt=30000,rb=10000,re=1000,rc=4000,beta=100,isat=1e-15,ut=.026)`|分压加载和指数关系联合 Q|固定温度、忽略 Early，所有参数正，VC>VB>VE，否则拒绝|
|`cs(gm,go,rd,rs=0,rl=None)`|vdrain/vgate、去掉 RL 后输出电阻|体接源，器件栅输入无限大；rs=0 支持接地极限|
|`ce(gm,beta,go,rc,re,rl=None)`|vcollector/vbase、基极输入电阻、理想基极驱动的输出电阻|局部混合 π 参数；调用者必须先绑定合法 Q；有限输入源输出式见正文|
|`cg(gm,go,rd,rl=None,rsig=0)`、`cb(gm,beta,go,rc,rl=None)`|共栅/共基的输入电阻与电流交付|输出 RL 影响输入；CG 输出测试移除 RL 保留 Rsig；CB API 不报告 Rout|
|`follower_bias(...)`、`follower(gm,go,rs,rl=None)`|漏直接接电源的 MOS Q 与跟随传递|体接源；门极不取低频电流|
|`emitter_follower(gm,beta,go,rbias,rl=None,rsource=0)`|BJT 跟随 Av、Rin、输入终止后 Rout|rsource 为置零源与偏置的等效终止，移除 RL 后测 Rout|
|`mos_reference(...)`、`mirror(vo,...)`|参考二极管栅压与简单镜输出|参考正电流；输出处于强反型饱和才返回|
|`cascode(vo,...)`|四管普通堆叠镜中点、电流及局部 Rout|每管体接源；上/下管均检查，不覆盖低压镜和共享衬底体效应|
|`bjt_mirror(vo,iref=.001,beta=100,va=None,...)`|包括两个基极电流的镜；va 有限可含 Early|参考管二极管连接，输出 BC 不正偏；va=None 是忽略 Early|
|`active_load(...)`|按指定合法 Q 合成固定栅偏置、参考电流及增益|N/P 均饱和，输出在电源内，零电导无限增益明确拒绝|

函数接收有限实标量。bool、complex（即使虚部为零）、字符串、object/complex/普通数组、嵌套列表均在转换前拒绝；NumPy 实标量可用。不是批量数组 API。非法范围、越工作区、非有限派生结果抛错；不会把无穷大分母的增益静默写成零。极端值可能因算术溢出抛 `OverflowError`，同样表示未得到有效结果。二分先直接比较非零端点的符号，拒绝同号区间；不相乘判断，以免极小残差下溢。可表示范围内，二分有最多 160 次预算，遇相邻 float 停止并选残差较小端点；预算耗尽显式失败。它处理的是本页限定单调支路，不承诺一般电路多解求解器。

模型中的 `ro=None` 表示导电通道小信号内阻无限大，不是缺失数据；其它返回 None 情形没有被用来隐藏失败。固定参数 MOS 使用 `1+lambda*VDS`，不可与 `1+lambda*(VDS−VDSsat)` 混用。BJT 偏置没有 Early；镜的 `va` 若给出，则参考与输出都使用 `1+VCE/VA` 并联合基极电流重求。

## 从库根执行，输出在库外

当前库已有 NumPy、Matplotlib、CairoSVG 与 Pillow 的 `.venv`。如本机缺这些依赖，应记录未运行，不能把安装或改测试当作绿色结果。`amp_lab.py` 的计算只需要 Python 标准库；测试的独立矩阵复算需要 NumPy，生成需要 Matplotlib、CairoSVG。

```bash
MPLCONFIGDIR=/private/tmp/wwl-amplifier-mpl .venv/bin/python -B '电子电路/80-实践/14-偏置与基本放大/generate.py' --output /private/tmp/wwl-amplifier-recompute
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/14-偏置与基本放大' -v
```

生成目录包含 `assets/*.svg`、`assets/*.png` 与 `results.json`。`generate(output)` 可程序调用；无参数 CLI 失败，import 不写文件、不启动 GUI、不加载绘图库。绘图使用直接 Figure/Agg，局部 `matplotlibrc` 在生成函数内生效；SVG 不含动态时间戳，并固定散列盐。重新生成到新的库外目录后按字节比较发布资产，避免写回已冻结图。

## 四个可检查任务

1. 重新求两个 MOS Q，代回 `VD+ID*RD=5`、`VS=ID*RS`，再检查 VDS≥VOV。答案应得到 1.057692 mA 与 .557623 mA；加入 RS 后不能复制旧 gm。
2. 给局部 CS 两节点矩阵输入 vg=1 V，用 NumPy 解 vd、vs，检查全部 KCL。对退化例 vd/vg=−1.435250；输出电阻测试必须移除 RL 并把 vg 置零。1 V 在此是线性模型的单位测试，不声称实际大信号可线性摆动 1 V。
3. 对镜输出电压在 Q 两侧各变化 h，算中央差分。简单镜斜率约 1/51.980762 kΩ；级联在 VO=3.961524 V 时约 1/5.613962 MΩ。h 过大会偏离局部，过小会受到浮点消减误差。
4. 把输出改为 .5 V 的简单镜或 2.5 V 的普通堆叠镜。正确结果是说明工作区失败，而不是输出零、完整继续画饱和曲线或宣称实测失效。正文说明怎样换模型，当前 API 不实现三极区。

`test_amp_lab.py` 包含八组实际检查：Q 回代/导数；另实现两节点矩阵与测试源；CG/CB/跟随端口；镜 KCL/有限差分；有源负载平衡与极限；无效输入/派生失败/迭代停止；极小同号残差与实际镜无根回归；纯 import 与必填 CLI。脚本通过只证明这些有限 CPU 合同，不能证明器件来源的所有断言、真实电路安全或读者学会。

图源 `generate.py` 为真源，当前没有另造 code-sync 镜像。图覆盖的是 V22 的本地参数/节点、V23 静态路径和 V24 镜/负载部分；差分对与 V24 全部目标、寄生、频带、仿真和实际测量未验证。
