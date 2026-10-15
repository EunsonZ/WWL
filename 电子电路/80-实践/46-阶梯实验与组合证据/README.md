---
type: lab
domain: electronics
stage: 2
content_status: usable
evidence_status: partial
aliases: []
sources:
  - https://ngspice.sourceforge.io/docs/ngspice-43-manual.pdf
prerequisites:
  - "[[电子电路/10-电路基础/04-同一RC从物理到离散实现#实现层：索引、块状态与舍入]]"
  - "[[电子电路/40-反馈噪声与混合信号/03-ADC驱动建立与弱信号预算#一份失败规格与可行重设计]]"
---
# 阶梯实验与组合证据：先连接已经明确的模型

同一份数字结果如何连回电路、初值、噪声端口、采样时刻和模型域？本目录保留既有项目，以完整实验卡给可预测、可复算的组合入口。基础读者先按卡手算规定的数值；快进读者核对式子/单位/模式和源码，运行同一命令。这里的四卡完成的是内容、输入与有限CPU对照，不是全部真实实验已经执行。

## 当前四张完整卡

|合同|实验卡|必须观察的结果|
|---|---|---|
|L02|[[电子电路/80-实践/46-阶梯实验与组合证据/01-L02同一RC四域与延迟]]|τ1ms、t/s/jω/z、初值、因果ROC、T.25ms及额外寄存器/块边界|
|L04|[[电子电路/80-实践/46-阶梯实验与组合证据/02-L04非线性工作点与模型对照]]|二极管原残差/独立括根、MOS Newton/解析Q、隔直加载与工具输入|
|L07|[[电子电路/80-实践/46-阶梯实验与组合证据/03-L07噪声端口建立与ADC预算]]|DC界、随机PSD、条件量化、确定混叠和建立五种账本|
|L11|[[电子电路/80-实践/46-阶梯实验与组合证据/04-L11Buck模式平均与能量预算]]|三拓扑、全CCM见证、DCM越域反例、平均初态约定、损耗W与热假设|

每卡有输入输出时刻、具体预期、失效/陌生条件和理由题答案。正确的解析、独立数值、KCL或守恒解均可；不要求模仿一种答案措辞。

## 源码责任与执行

`joint_lab.py`是本组唯一CPU连接器，已有六个源模块仍各自是真源；不复制RC、噪声、电平或电源整模型。`inputs.json`绑定所用主库源的具体字节。连接器只在显式run/generate时读源和验证hash，再compile到临时模块名；成功/异常都恢复该临时sys.modules入口，不改sys.path、不在原目录写pycache。只有固定L02/L04/L07/L11配置，不承诺任意巨值/未建模式的通用pipeline。

MOS Newton是唯一新的窄数值连接：固定电路调用原mos的I/gds，初态0..5V、λ0...05V⁻¹、1..64迭代，每步25次以内阻尼；转float前拒bool/complex/容器/非有限/越域，残差、停滞与预算失败明确。Buck继续用已签事件模型400周期/每区间32步，记录完整模式统计后才抽样CSV，未引入无限迭代。任何输出前完成模型计算和JSON编码。

从WWL库根选择自己的**全新库外目录**：

```bash
.venv/bin/python -B '电子电路/80-实践/46-阶梯实验与组合证据/joint_lab.py' --vault . --output /private/tmp/joint-four-cards-my-new-run
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/46-阶梯实验与组合证据' -p test_joint_lab.py -v
.venv/bin/python -B '电子电路/80-实践/46-阶梯实验与组合证据/generate_figures.py' --vault . --output /private/tmp/joint-errors-my-new-figure-run
```

两CLI的`--output`和`--vault`均必填，缺参先exit2，导入不解析argv/读输入/加载绘图/生成文件。输出存在或处于库/源码子树时显式拒绝，不覆盖已完成实验。`run(vault,cards)`返回有限结果不写文件；`generate(output,vault,cards)`才写results.json和Buck抽样CSV。图层lazy加载现有CairoSVG，确定SVG真源同时渲染360/425PNG；不调用Matplotlib默认GUI、不安装依赖，不需要另一套图状态。绘图失败前不创建输出目录。

逐字阅读镜像为 [[电子电路/80-实践/46-阶梯实验与组合证据/joint_lab-源码]]、[[电子电路/80-实践/46-阶梯实验与组合证据/test_joint_lab-源码]]、[[电子电路/80-实践/46-阶梯实验与组合证据/generate_figures-源码]]；执行与编辑以Python真源为准，三源/镜像及测试作为一致单元交付。

## 预期不是日志，CPU不是工具替身

结果由真实调用既有模型生成、均为synthetic。L02应v[4]=.7792723353V、H(jωc)=(1−j)/2；L04应二极管.5553740389V、MOS2.8846153846V；L07原good10项true，10nA反例仅DC失败，0.1µs迁移在建立上失败；L11合法初态全无idle，越域初态有idle且CCM平均允许负电流。精确数字/状态约定以各卡和results字段为准，不把稀疏CSV当全模式证明。

组合测试以独立连续解、阈值/加载闭式、独立二分、三角面积、量纲与反例核组合；当前数量以 `test_joint_lab.py` 在接受版本中实际发现/运行的结果为准，不把旧汇总或静态枚举写成新的通过证据。它们不会替代已有源的物理/来源独审。原四套基线入口保留：

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/01-RC跨层' -p test_rc_lab.py -v
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/02-弱信号前端预算' -p test_frontend_budget.py -v
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/03-FSM到RTL' -p test_buffer_model.py -v
.venv/bin/python -B -m unittest discover -s '电子电路/20-器件与模拟' -p test_device_examples.py -v
```

“本组实际四输出各为10/14/6/11，总41测试通过”是既有四输出交付批次的历史运行摘要，适用其当时冻结输入；本轮未重新运行，不能用它证明当前新字节。当前 `test_joint_lab.py` 的静态 `test_` 定义数为9（含额外的大整数拒绝边界）；静态计数不等于通过。完整运行及冻结输入证据留库外；任何重跑须另记命令、版本、环境、退出码和实际发现数。本目录不添加主库机器队列或学习掌握记录。

[diode-mos-teaching.cir](diode-mos-teaching.cir)与L04中的ngspice命令是可执行输入合同；工具当前缺失，SPICE not_run，绝不生成冒充真实日志。HDL、实体ADC、PWM、PCB、仪器及人的阅读也不由CPU预算签收。每卡内容/源码、CPU运行、真实工具、实体和学习者这五层应分别登记；最终内容正确性由非作者审阅，作者不自授完整L/V信用。
