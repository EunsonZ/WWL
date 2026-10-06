---
stage: 1
aliases: [运放基础与频带CPU实验]
sources: [本目录opamp_examples.py, 本目录generate_figures.py]
prerequisites: ["[[电子电路/28-运放比较器与滤波/01-有限开环增益与虚短条件#同相电路的两条方程]]", "[[电子电路/28-运放比较器与滤波/02-反相同相求和与差分#反相：输入电流经反馈返回输出]]", "[[电子电路/28-运放比较器与滤波/03-积分微分与真实频带#同一反相节点，换成频率相关阻抗]]"]
---
# 运放基础与频带实践

唯一数值源码是 [opamp_examples.py](opamp_examples.py)，测试是 [test_opamp_examples.py](test_opamp_examples.py)，图生成器是 [generate_figures.py](generate_figures.py)。README只保留源码指针与执行合同，没有第二份代码镜像。

从WWL库根运行，使用已存在 `.venv/bin/python`（NumPy、Matplotlib、CairoSVG、Pillow），不需SciPy、不安装依赖。候选尚未发布时把 `opamp_source` 改为候选中这个目录的绝对路径。输出必须另选库外的新目录：

```bash
opamp_source="$(pwd)/电子电路/80-实践/20-运放基础与频带"
opamp_output="$(mktemp -d /private/tmp/wwl-opamp-run.XXXXXX)"
.venv/bin/python -B "$opamp_source/opamp_examples.py" --output "$opamp_output/numeric"
.venv/bin/python -B -m unittest discover -s "$opamp_source" -v
.venv/bin/python -B "$opamp_source/generate_figures.py" --output "$opamp_output/figures"
```

两个入口都是 `main(argv=None)`，必填 `--output`。导入不parse参数、不写文件、不加载NumPy/绘图库，也不创建字体缓存；显式生成时才设置输出目录内的`.mplconfig/.cache`，lazy导入依赖，以direct Figure/Agg保存，不使用pyplot。数字结果在所有计算验证后才写出。缺参退出2，未写文件；运行成功退出0。`generate(output)`是显式函数接口，调用者须给真实输出路径。

模型：A(s)=100000/(1+s/(2π·10))，输入电流0、输出电阻0。±5 V电源，教学输出窗口±4 V、共模±3 V、RL=10 kΩ直接接地。它们是规定的教学条件，不是型号保证，也不模拟限流/摆幅/压摆率。电阻四网络用相同10 kΩ/90 kΩ基础组；积分Ri=10 kΩ、Cf=100 nF、Rf=1 MΩ；微分Ri=1 kΩ、Ci=100 nF、Rf=10 kΩ、Cf=1 nF。图里电容位置、源端点与参数一致。

源码采用原导纳形式 `-Yin/[Yf+(Yin+Yf)/A]`，微分DC用 `Yin=sCi/(1+sRiCi)`，无需对s=0除零。有限A直接用`1/A=(1+j f/fp)/A0`，不先形成极大开环复数再相除。初态函数使用`expm1`减少短时相消，纯积分与泄漏初态模型明确假定理想运放；它不是把finiteA的零状态传函强行用来决定非零初始内部状态。

输入是有限real scalar，拒bool、复数（包括零虚部）、字符串、列表、array/object/nested值，先类型检查后float转换。为限制浮点运算范围，公开计算域为：R在1 mΩ–10¹² Ω、C在10⁻¹⁵–1 F、A0在1–10¹²、fp在10⁻⁹–10⁹ Hz、f在0–10¹² Hz、t在0–10¹² s、电压在±10⁶ V；这是计算接口范围，**不是这些极端参数都代表合理运放电路**。越界与非有限值抛ValueError，非有限计算结果抛ArithmeticError。求和只允许1–8条匹配支路，避免悄悄zip截断或无界规模。极端频率/导数输入明确拒绝，不让溢出的inf变成一个虚假的有效输出。模型算出线性窗口外的值只作为失效预测，不能当实物输出。

8个作者测试从两未知量原KCL与受控源方程用NumPy解四种DC网络，从复导纳方程独立解积分/微分多个频点，核一阶−3dB点/大A极限、失配共模、初态/RC解析值、固定参数闭环多项式的左半平面根与无效/极端输入。它们检查作者模型，不是独立审阅签收。

图形频率采样401点、0.1 Hz–10 MHz，状态301点、0–5 s。没有ODE步进误差；数值来自闭式函数。纯积分超过4.2 s后的虚线标明输出预测已经不在线性窗口内。频率图分开纯理想、被动RC限制、finiteA；输出SVG是可编辑线/文字，360/425 PNG、灰度及暗背景是显示核对用。`parameters.json/results.json/assets/figure-data.json`分别保留接口/参数、数例、采样与曲线数值。

没有运行SPICE、HDL、真实硬件、实际Obsidian客户端或真人学习验证，没有器件选型保证。只交M11-01..03，不把这个实践称为M11全部完成。
