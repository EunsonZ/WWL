---
stage: 1
aliases: []
prerequisites:
  - "[[电子电路/52-测量不确定度与辨识/04-实验设计可观测与可辨识]]"
sources:
  - "https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf"
  - "https://www.bipm.org/documents/20126/2071204/JCGM_101_2008_E.pdf"
---
# 合成测量、不确定度与RC辨识实践

读者问题：电压拟合得很精确，为什么还不知道电阻、电容各是多少？先复算同τ曲线，再增加独立电流/阻抗观测，最后给估τ的不确定度预算。本文及CSV/JSON/图全部是**合成教学数据**，没有连接仪器、获取真实读数或证明现场参数。

## 模型与数据

pairs A=1kΩ/1μF、B=2kΩ/.5μF；U=1V阶跃、v0=0、理想无载，τ=1ms。data/parameters.json给单位、采样时刻、电压/电流噪声假设、网格与MC种子；data/rc-synthetic.csv保留两组电压和电流；data/results.json保留预算、Fisher、MC和错初值拟合。sigma是构造的实验假设，不是已测仪器指标。

八个SVG及各360/425px PNG分别给：补偿真实分支图、RC实验连接图与读出链、补偿/加载响应、同τ电压与独立电流、对数坐标灵敏度、3D谷与两2D投影、相关预算、竞争模型残差与排查流程。英文图标签与主课中文文字替代对应。3D高度log10(1+SSE)无量纲；不是物理能量。V40本组提供表、谷、灵敏度和第三观测，最终信用须独立审阅，不以图数替代合同。

## 运行与输出合同

在主库根执行现有环境；不安装依赖：

```bash
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/34-测量不确定度与辨识' -p 'test_models.py' -v
MPLCONFIGDIR=/private/tmp/wwl-m23-mpl .venv/bin/python -B '电子电路/80-实践/34-测量不确定度与辨识/generate.py' --output /private/tmp/wwl-m23-new-output
```

output须显式给出，且为不存在/空目录，解析symlink后不可处于主库或源码所在电子电路子树中。generate(output)与CLI遵循同一规则；重复运行需另用一个新的目录。库外作者evidence子树可保存生成结果，但不会覆盖候选电子电路树。生成器不提供仪器操作接口，不覆盖任何非空目录。

models.py及generate.py导入不解析argv、不生成数据、不绘图；numpy/matplotlib/cairosvg在显式generate后才导入。实际绘图依赖可能建立字体缓存，命令给库外MPLCONFIGDIR；它不是生成资产，不声称冷启动库绝无临时缓存。rc_context限制绘图参数作用域，不选全局backend、不调用pyplot，成功或异常都退出上下文。未安装绘图依赖时保留源码并报告未运行，不能把缺图写成通过。

## 数值API、单位和有限范围

全部数值参数先要求type严格为builtin int/float，再转float并检查finite与范围；拒绝bool、complex、字符串、numpy标量、float子类、隐式__float__对象、NaN/inf和巨大整数转换溢出。identify_impedance单独要求builtin有限complex。这里是有限教学API，不声称覆盖所有合法物理尺度。

| API | 输入/输出与条件 |
|---|---|
| step/current/frequency/input_impedance | R∈[10,10⁷]Ω、C∈[10⁻¹²,.01]F且τ∈[10⁻⁸,100]s；t∈[0,10⁴]s；U/v0∈[−100,100]V。frequency允许ω=0，Z要求ω∈[10⁻⁶,10⁹]rad/s。current正向源→R→C。frequency返回无量纲H。 |
| identify_current | 已知零初值、正U，t=τ的正i；τ上述范围、i∈[10⁻¹²,10]A、U∈[10⁻⁶,100]V。返回R/C仍须落在RC范围。 |
| identify_impedance | ω正且Z实部为R、虚部负；只适合理想串联RC端口，不默默拟合RL/寄生网络。 |
| loaded_step | RL∈[10,10⁹]Ω、Cp∈[0,.01]F、Rs∈[0,10⁷]Ω，返回(v,K,τloaded)，τloaded须同有限范围；IC仍保留。 |
| sensitivity/fisher | logR/logC坐标两观测行单位V/A；噪声σV/σI∈[10⁻¹²,10]对应单位；是否含电流须bool。Fisher针对已知、独立、参数无关Gaussian观测假设。只电压的奇异矩阵不做逆。 |
| tau_from_crossing/tau_sensitivity | t∈[10⁻¹²,10⁴]s、U∈[10⁻⁶,100]V、0<V<U；只零IC正阶跃；计算τ/灵敏度或预算中间量不再finite时明确ValueError，极近端点不声称可靠数值支持。返回τs与对[t,V,U]灵敏度。 |
| tau_budget | ut∈[0,100]s、uV/uU∈[0,10]V、ρ∈[−1,1]；局部一阶传播，t独立，V/U可相关。返回对角、交叉与uc，未自动推定覆盖概率。 |
| mean_uncertainty/expanded | 2..10000个有限观测，幅度≤10⁹，返回均值、s/√n、n−1；扩展因子k∈[0,100]须由调用者论证。 |
| mc_tau | 明确joint Gaussian，t独立，V/U由相关normal构造；samples严格整数100..20000，seed整数0..2³²−1；使用局部Random。域外样本立即失败，不筛掉再抽。经验中央区间插值不是JCGM自适应/标准区间算法，不保证指定数值容差或真实覆盖。 |
| voltage_loss | times/values等长list/tuple，1..256项，电压[−100,100]V；σV∈[10⁻¹²,10]V；返回无量纲加权SSE。网格生成固定81²有限个点，不做无界优化。 |

step采用v0 exp(−q)+U[−expm1(−q)]避免极小t丢非零初值；current由解析式计算，不能以接近终值的U−v相减冒称微小电流可靠。预算用等价平方和计算PSD协方差传播，避免ρ=±1时负舍入方差。小数舍入只影响显示，CSV/JSON保留实际float。

## 检查的问题及未验层

17个有意义测试包括两组等价曲线、另一观测恢复参数、KCL有限差分、IC与极小t、log参数Jacobian有限差分、Fisher秩、加载、预算导数/相关性、A类均值、MC同seed/全局PRNG保全、失败不重采样、残差非唯一、无效类型与有限预算。它们是作者CPU测试，独立审阅须另核关键推导、正文、来源、图和数据。

基础往返：[[电子电路/52-测量不确定度与辨识/01-仪器阻抗带宽与探头|仪器如何进入电路]] → [[电子电路/52-测量不确定度与辨识/02-时域频域与网络测量|观测与校准平面]] → [[电子电路/52-测量不确定度与辨识/03-误差不确定度与相关预算|预算]] → [[电子电路/52-测量不确定度与辨识/04-实验设计可观测与可辨识|信息增量]] → [[电子电路/52-测量不确定度与辨识/05-从仿真到实测的故障树|受控排查]]。数学目标精确桥在04；旧RC页/数学目标反向补丁未实施。

没有SPICE、仪器/VNA/实际校准、硬件、环境实测、Obsidian客户端或真人阅读验收。小CPU实验不承担整库实验合同；本组明确区分已复算的合成模型和现实未知。
