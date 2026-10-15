---
stage: 3
aliases: []
prerequisites:
  - "[[电子电路/60-TCAD与器件场模型/01-漂移扩散Poisson与接触网格]]"
sources:
  - https://devsim.net/examples_short.html
  - https://www.iue.tuwien.ac.at/phd/klima/node23.html
---
# 器件场与紧凑模型：有限CPU复现合同

本实验唯一数值源码为 `field_models.py`，测试为 `test_field_models.py`，图真源为 `generate_figures.py`。参数 `parameters.json`、合成端口点 `synthetic-bar.csv`、冻结 `results.json` 和assets是可复算输入/结果，不另造镜像。导入仅stdlib，无numpy/matplotlib、无argv解析、文件生成或fontcache。函数计算时才lazy import NumPy；图生成用直接Figure，不用pyplot。

从库根运行，沿用现有.venv；不安装SciPy/TCAD工具。发布后可用如下命令。输出必须是新建、尚不存在的库外目录，第一次的输出不能重复复用。这里的/tmp名称由操作者选唯一值，不是授权覆盖旧目录：

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/36-器件场与紧凑模型' -v
.venv/bin/python -B '电子电路/80-实践/36-器件场与紧凑模型/field_models.py' --output /private/tmp/f01-numeric-new
.venv/bin/python -B '电子电路/80-实践/36-器件场与紧凑模型/generate_figures.py' --output /private/tmp/f01-figures-new
```

候选未发布时，将源码路径替换为候选完整路径；本次实际argv/exits留在库外READY证据。`main(argv=None)`先解析必填--output；缺参数退出2且不写任何文件。new_output拒绝已存在目录及AGENTS+scripts/check_vault.py标识的主库内路径；其他目录是否授权仍由调用者负责。数值数据全部先计算再建输出；图缓存只进入显式输出下.mpl/.xdg，两env在finally恢复，rc参数局部context，异常也恢复。图错误输出目录可保留排障，不能当成功。

|API/对象|支持域与预算|已兑现与未兑现|
|---|---|---|
|poisson(x,rho,ε,left,right)|native list/tuple 3..257节点，等长；x∈[0,1]m严格递增、最小间距1pm；ρ±10⁷C/m³、ε∈[ε0,100ε0]、端点±10V|常ε一维节点控制体积，稠密NumPy solve；不含材料界面/自适应/通用稀疏求解器|
|sg_current/transport|φ±1V、边δ±80、n∈[1,10²⁶]m⁻³、μ[10⁻⁶,10]m²/Vs、T250..400K、h[1pm,1m]；同节点预算|规定φ的电子稳态无R/G，共用J联立；不提供全偏置自洽DD、空穴数值运输或高场物理|
|equilibrium_case|N4..128、a0..2、ε同上；固定L1μm/ni10¹⁶/T300；Newton1..60、每轮20阻尼；容差10⁻¹³..10⁻⁵|制造解PB自洽平衡，n/p解析消去；预算耗尽/不降/越u范围明确RuntimeError，无默默夹指数|
|bar_conductance/fit_origin|n10¹⁶..10²⁵、A10⁻¹⁸..10⁻⁴m²、L1nm..1m；fit2..257点，V±1V/I±1A，激励至少1nV，正G|常μ合成条形G及过原点等权LS；不唯一分μ/n，不假称真实工艺、置信区间或BSIM模型卡|

上述域是数值教学API范围，不认证物理模型在域的每点真实有效。bool、complex（包括0虚部）、NaN/inf、字符串、形状/重复网格、预算超限等转换前拒绝ValueError，不悄悄丢虚部。网格病态/线性失败由求解器错误或残差证据暴露，不能仅因返回数组就宣布物理通过。有限尺寸上限控制CPU工作量；不是商业性能基准。

解析与另一实现对照：固定ρ二次φ在非均匀网格精确；独立逐段积分D再用末端φ求D0，与矩阵Poisson比较。SG由积分因子整边积分对照，另核零场、热平衡及常场守恒。PB以连续制造解做8/16/32/64网格误差，不以自己离散残差当连续精度。合成端口G用qμnA/L手算与另一组μ/2、2n同端口反例；材料ε固定ρ敏感度用1/ε解析比。这12项是作者检查，独审另外绑定。

固定材料研究/校准复现计划：

1. 记录真实样品/工艺与几何、接触、材料/统计/复合模型、版本及数据权限；本次device_id=synthetic-bar，real_PDK=null。不能将其改名真实硅器件。
2. 专业工具若以后获授权并已有可执行程序，保存实际version/help、网格、接触、电势初始化和DD方程；输出残差与两端电流。无工具就not_run，不生成“软件日志”。
3. 同一连续问题细化网格、保持材料/接触不变；收敛失败、守恒不足或误差未达目标时停止参数提取。量纲/状态不能混容差。
4. 实测I/Q、温度和几何重复记录；先分提取/保留验证集，再选损失权重/参数界及预算。辨识秩不足就报告只能估组合参数；不得伪造唯一材料参数。
5. 模型卡绑定适用V/T/尺寸/频带与已知失效；在生产指标预算内分别处理测量、数值和物理遗漏误差。关联误差不默认RSS。真正工艺角落/温漂/击穿/自热/非准静态/寿命需要另验，本次无生产资格。

V41仅完成F01原创Poisson/DD网格与场到端口层级；F02封装RLC/热/机械由另组以后组合。本图比例是示意，不当制造尺寸。专业TCAD/DEVSIM、SPICE、真实PDK/工艺、硬件/仪表、UI及真人学习not_run。结果表示本机CPU有限模型正确性检查，不声称穷尽TCAD研究。
