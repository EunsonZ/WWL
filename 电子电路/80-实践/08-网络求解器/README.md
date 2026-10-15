---
type: lab
domain: electronics
stage: 3
aliases: []
sources: []
prerequisites:
  - "[[电子电路/14-网络建模与仿真/01-图论电路与关联矩阵]]"
content_status: usable
evidence_status: partial
---

# 网络求解器：从手算到可拒绝错误输入的复算

本实验服务M07-01…06。先在纸上得到三电阻v=(5/11,3/11) V、跨节点源v=(0.5,−0.5) V和负载二端口V2=0.2 V，再用脚本比较；遇到奇异系统先判断相容与自由量，而不是马上替换求解器。手算位于六章各自主例，测试依据包括KCL、功率、端口关系和不同算法二分根。

**唯一数值源码**：[network_examples.py](network_examples.py)。**唯一图生成源码**：[generate_figures.py](generate_figures.py)。测试为[test_network_examples.py](test_network_examples.py)。此处不复制Python到Markdown镜像。导入这两个模块不生成文件；命令的`--output`必填，省略时解析参数即退出，输出禁止放入主库。脚本不安装依赖，不启动服务。

从WWL库根运行；本批现成`.venv`有NumPy 2.5.3、CairoSVG 2.9.1，SciPy不存在，因此用`numpy.linalg.solve`和明确后向Euler差商。更换环境须先确认依赖；不自动安装。输出目录由读者显式指定为库外，例如：

```bash
.venv/bin/python -B 电子电路/80-实践/08-网络求解器/network_examples.py --output /private/tmp/wwl-network-results
.venv/bin/python -B 电子电路/80-实践/08-网络求解器/generate_figures.py --output /private/tmp/wwl-network-figures --raster
.venv/bin/python -B -m unittest discover -s 电子电路/80-实践/08-网络求解器 -p 'test_network_examples.py' -v
```

候选尚未发布时把源码参数改为隔离候选的绝对路径；现有候选输出放在本页`assets/`，它位于库外，作为独立审阅的冻结证据。发布后仍用上述库外输出参数，不覆盖正文的既有附件。`--raster`只在已有CairoSVG时使用；不带该参数可仅生成SVG。

## 逐项复算

|函数/实验|独立预期|实际可检验对象|
|---|---|---|
|incidence/resistor_network|消元v=(5/11,3/11)，功率5/11 mW|支路反向Y不变、电流反号、KCL/功率|
|mna|超节点v=(0.5,−0.5)，j=−0.5 mA|完整增广式与独立VCVS四行例|
|constraint_ranks|并源5/3秩2对3；5/5秩均2|相容/不相容分别标注|
|cv_source|斜坡j=−1 mA|初值不一致、复数输入直接拒绝，时间必须严格递增|
|rc_backward|首步0.2 V；解析0.2211992 V|h减半使固定1 ms时误差下降|
|diode_newton|单调括区间[0,0.6]；二分根|原指数残差、有限差分Jacobian、回溯/失败；二分相邻浮点停滞/预算失败|
|cubic_step|根−1/0/1；从2一步16/11|零Jacobian拒绝，找到一根不排除其余|
|z_parameters/transfer|Z/Y/h/T同一端口，H=0.2|四种参数回代、中心差分灵敏度|

11个测试方法通过；这包括多个物理/代数检查，并不表示通用电路仿真器已实现。程序没有通用网表解析、MOS模型、多节点非线性迭代、稀疏LU、自动微分或一般DAE求解器；这些是明确的后续范围，不用标题暗示已有能力。

另以数值梯形积分核对RC有限带噪声解析arctan积分，单位为V²。

源/缩放/二端口使用SI数字，MNA有混合单位行列，`results.json`键标注V/A/S/Ω，h/ABCD明确为混合单位。输出`diode_trace`每步记录残差A与阻尼系数。误差与残差不能混为一项。`results.json`为机器数据，不要求人手维护哈希。

## 图与实验信用

四幅SVG为原生确定性图：支路与关联矩阵、C并理想源一致约束、二极管切线/阻尼/迭代、AC与tran不同流程。每幅已实际生成360/425 px PNG并由作者查看；图中文字采用英文符号避免字体替换，但正文解释各节点、箭头和单位。来源为本批推导/数值数据，未调用图像生成插件。

计划`figures.json`没有M07专属条目，本批图只认领M07正文“必须设计的图”，不冒用其他V编号。计划L04只兑现二极管最小Newton、手算与独立二分对照，MOS和SPICE对照未运行；L03属于RLC能量/相轨迹，本批RC误差不能抵充L03。HDL/形式与本实验无接口，不伪造日志。

[rc-analysis.cir](rc-analysis.cir)是可审查SPICE输入。当前PATH未找到ngspice；**SPICE not_run**。硬件、真实Obsidian客户端、真人阅读验证同为not_run。作者数值/渲染检查通过后仍需独立审阅；本页不是独立签收证明。精确路径、字节哈希、来源阅读边界与缺口保存于库外READY报告，由唯一发布者使用。
