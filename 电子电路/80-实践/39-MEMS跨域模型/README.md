---
stage: 1
aliases: [MEMS跨域有限CPU实践]
sources:
  - https://ocw.mit.edu/courses/6-777j-design-and-fabrication-of-microelectromechanical-devices-spring-2007/74a80a103418ef786898f73e75d9b641_ps7_soln.pdf
prerequisites:
  - "[[电子电路/66-MEMS传感与机电耦合/01-机电耦合与传感机理]]"
  - "[[电子电路/66-MEMS传感与机电耦合/02-读出校准噪声与闭环量程]]"
  - "[[电子电路/66-MEMS传感与机电耦合/03-封装可靠性与系统复现]]"
---
# 实践39：MEMS跨域有限模型

所有图、CSV与JSON都是**合成教学模型**。板200×200×10 μm、密度2330 kg/m³是假设；f₀1 kHz和ζ=.7为独立有效参数，不是由图推导的工艺结果。没有芯片照片、仪器读数、真实封装寿命、SPICE/有限元、实际控制器或真人验收。

从库根运行已有环境（不安装）。将命令中的输出路径选为库外的新目录：

```bash
.venv/bin/python -B -m unittest discover -s 电子电路/80-实践/39-MEMS跨域模型 -v
.venv/bin/python -B 电子电路/80-实践/39-MEMS跨域模型/generate_mems.py --output /private/tmp/mems39-fresh
```

`--output`必填，函数`generate(output)`也是显式输入；目标只能不存在或空目录，拒绝主库与候选发布树，包括解析符号链接后的路径。不会隐式写默认assets、覆盖已有生成结果或选择全局Matplotlib后端。numpy/Matplotlib/cairosvg只在生成时加载；环境字体缓存应由调用者设`MPLCONFIGDIR`与`XDG_CACHE_HOME`到库外。渲染失败可能留下部分输出，保留并检查或换新空目录重跑，不声称原子事务。

## 源码与有限域

真源是[mems_model.py](mems_model.py)、[generate_mems.py](generate_mems.py)和[test_mems_model.py](test_mems_model.py)，各自同名`-源码.md`逐字镜像。函数先拒bool、字符串、复数与非Real对象，再有限值检查。所有输入SI；范围是CPU教学预算，**不是**实体额定条件。允许边界内的实数（含标准Real数值类型），浮点运算不提供无限动态范围保证。

| API | 输入与返回 | 预算/失败条件 |
|---|---|---|
| mechanics | m kg/f₀Hz/ζ→m,k N/m,b kg/s,ω₀rad/s | m1e−12..1e−3，f₀1..1e6，ζ0..10 |
| displacement | a m/s²,f Hz,K N/m→复数X m，基座输入负号 | \|a\|≤1e5，f0..1e7，K0..1e9；无阻尼精确共振及派生复数结果不可有限表示时抛ValueError；可表示的大幅值保留；它不检查几何间隙 |
| state_rhs | x m,v m/s,a,F N→ẋ与ṽ | \|x\|≤1，\|v\|≤1e4，\|F\|≤1e3；不负责积分步长 |
| capacitors | x,g m,A m²,共同Cp F→C±/ΔC/比值 | g1e−9..1e−2，A1e−14..1e−2，Cp0..1e−3；\|x\|≥g接触拒绝 |
| beam_strain | 末端x,L,t→表面应变 | L1e−6..0.1，t1e−9..0.01；t/L≤.1、\|x\|/L≤.05的细长小挠度教学域，不含残余应力 |
| bridge | δ,Vexc→va/vb/vo/共模 | δ−.95...95保证正电阻，Vexc0..20V；高阻开路读取 |
| thermal | T K,矩形输入等效B Hz→力PSD/加速度ASD与RMS/平衡位移方差 | T1..2000，B0..1e6；ζ=0时热阻尼源为0，不表示所有实体噪声为0 |
| calibrate | y V,S V/(m/s²),B V,c V/(m/s²),横轴a→a_hat | \|y,S,B,c\|≤100，S=0拒绝；\|横轴\|≤1e5，已知局部线性参数 |
| feedback_static | a,K,Fmax→x,F,F/m,saturated | K0..1e9 N/m，Fmax0..1e3N；准确重新平衡限幅力，无动态/间隙/电静力保证 |
| vibration_bias | 峰值A m/s²,q s²/m→周期平均m/s² | A0..1e5，\|q\|≤100；给定二次模型而非实测VRC |

返回都为有限标量或包含有限数的字典；当前乘积尺度上界可由预算界定。非零极小scale使校准结果超出有限浮点表示时显式拒绝；此保护不改变合法有限结果。模型有明显的端口差异：plate位移与独立cantilever末端位移、桥电压与电容读出、被动平衡与主动反馈不能互相偷换。

## 复算任务与产物

18个作者测试从原牛顿能量余额、独立分压、梁端力、整周期平均、符号/频率尺度和无效输入核对。它们是作者执行证据，需非作者另行签收。数据`results.json`记录1g电容、热B100和饱和8g平衡；`capacitance.csv`记录同几何的精确/一阶/比值。输出7个可编辑SVG与各360/425宽PNG，共21图件；加parameters/results两JSON和CSV，共24生成资产。

图像英语标签避免字体安装，正文给中文端口、单位、条件。空间图有真实X/Y/Z坐标与厚度间隙，不是把曲线旋成立体装饰；剖面与数据用同一尺寸。`readout.svg`上半质量节点Qp=0的电容分压，下半四臂电桥端点；它们是教学端口图，不是制造或芯片内部电路。CPU完整V42仅贡献MEMS位移→电容/桥路；光电到TIA属于另组，不能因此宣布完整V42合格。

必要来源阅读范围：MIT Lecture24页4–8、16–17、32–34；PS7解答页6–8；Lecture18页21–25；Lecture7页21–23；Lecture10页6；ADI数据手册Rev.D页5/7脚注和22–24信号/参考/轴方向；两篇官方应用文章的指定正文段。库外证据保留取回方式和失败范围，未声称阅读全部PDF或OCR图片系数。未签F03或其他并行候选不是本组必要前提。
