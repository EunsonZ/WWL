---
domain: 电子电路
type: lab
stage: 4
content_status: usable
evidence_status: partial
aliases:
  - 反馈CPU实验
sources:
  - https://www.ti.com/lit/an/sloa020a/sloa020a.pdf
  - https://ocw.mit.edu/courses/6-241j-dynamic-systems-and-control-spring-2011/996025f6db0d90b00f11c44fc49b85f9_MIT6_241JS11_textbook.pdf
prerequisites:
  - "[[电子电路/36-反馈稳定与振荡/01-反馈拓扑与返回比#四种连接各自反馈什么]]"
  - "[[电子电路/36-反馈稳定与振荡/03-RouthNyquist与根轨迹#Nyquist的方向与P、Z、N]]"
---

# 反馈稳定与振荡CPU实验

这里把六章的方程变成可核对实验，不模拟一款未指定的真实器件。所有值是教学参数，输出不是示波器记录；没有 SPICE、实际注入、硬件、Obsidian UI 或人的学习效果验收。本实验对应固定 L06 的模型层产出，目录编号23不等于新增第23个固定实验合同。

## 逐项可运行实验

在本目录运行，输出必须由调用者指定到主库和候选库之外；源码不会默认改库。示例中的Python仅表示已有依赖环境，不要求安装：

```bash
python3 -B -m unittest discover -s . -v
MPLCONFIGDIR=/private/tmp/wwl-feedback-mpl python3 -B build.py --output /private/tmp/wwl-feedback-result
```

1. `injection(2,3,do=.07)` 得 y=.01 V、u=−.03 V。依次打开 r、di、do、n，代回 u=C(r−y−n)、y=P(u+di)+do，检查不同注入路径。
2. `triple_poles(K)` 与 `triple_routh(K)` 用 K=1、8、20核对稳定/边界/不稳；`triple_loop`给复频响。`triple_step` 用三简单根的部分分式计算单位阶跃，测试另用三状态原方程 RK4，在p·t=2逐点比较。K=8不是严格稳定。图03包含展开相位、dB与阶跃；图04箭头按负频到正频，图05用s/p坐标。
3. `lead_beta` 与 `isolated_load` 用实际阻抗/KCL独立核对，读第04章解释为何变更反馈取样端会改变结论。图06画被动网络各节点的返回端，图07保留跨接电容和受控电流。
4. `wien_beta`在ωRC=1给1/3，`radius`验证径向ODE及初值；零种子不会确定性自发启动。图08画正RC反馈与负增益反馈，标星电阻只是控制模型，不承诺灯泡/JFET参数。
5. `nested_poles(1,1,2,2)` 给+1、−3；图09的两个电容、受控源和KCL对应完整矩阵。
6. `delay_limit(2,1000)` 给τ临界≈1.20920 ms；`delay_phase_crossings`只输出wmax内全部交越，预算超过即失败。第06章单独证明本族全延迟稳定范围。`robust_onepole(9,.2)`=.18来自解析全频范数，不是频点最大值。

## 数值合同与错误出口

`models.py`纯导入只加载math；`build.py`导入只加载标准库与models，不解析argv、不触发Matplotlib/字体缓存，不读写文件。只有显式调用generate才懒加载NumPy/Matplotlib/CairoSVG；用直接Figure与局部rc_context，未改全局rcParams。生成时字体库可能自行建立调用者环境缓存；示例将MPLCONFIGDIR放库外，这是调用者设置而非模块偷偷改环境。

实数接口拒绝bool、complex、object、容器、NaN/Inf及越界，标量类型仅接受Python int/float；频域合法complex由函数返回，omega仍为实数。不会先把object/complex强制转换成float。参数范围限制为教学正常区间：K≤100、p=10⁻³..10⁶ rad/s、|omega|≤10⁹ rad/s；电阻、电容范围由各函数检查。原方程在更广数学域仍成立，数值API主动缩窄域。

幅度解：t=0..100 s、r0=0或10⁻⁶..100 V、μ=0或10⁻⁶≤|μ|≤100 s⁻¹、α=10⁻⁴..100 V⁻²s⁻¹、|μt|≤100。用expm1处理短时差值，不把域外下溢写为精确零。阶跃在规范化时间θ=p·t上用规范化根s/p与留数整体求值，改变p只改变物理时钟；R2新增K=1/8/20与p=.5/1000六组缩放及原物理ODE回归。阶跃部分分式有消减，主动要求K=.1..30，t=0或 .01≤p·t≤20，p范围同上；更短时先拒绝，t=0返回已知初值。延迟根用严格单调式，每根80次二分，最多1..1000个budget；必须通过残差检查，超过数量或精度不足抛ValueError。实验默认wmax=30000 rad/s，超出部分没有数值扫描声明。

参数极值由调用者检查接口边界；R2当前16项测试覆盖无效输入、原节点/特征式、解析边界、另一实现RK4、幅度ODE差分、范数解析和纯导入。有限差分与RK4都是实验检查，不是全连续误差证书。

## 图合同和证据范围

9张原创SVG，均有360与425像素PNG。图01是四种理想单向端口模型，图02是四加法节点；图03–05合起来覆盖V27：三极点K=8边界、连续相位、完整频扫方向、P/Z/N和解析根。图07仅覆盖V15中RHP零点的电子机制，不声称V15整套曲线；未绘TIA与完整输入电容断环，V26仍无完整信用。图08非线性模型与实际RC连接分层，图09仅为两状态/延迟/鲁棒条件入口。

必要数据在results.json，包括真实生成参数说明、根、阶跃点、四注入、有限交越列表、解析范数和幅度点。SVG为源码产生的可编辑文本；PNG是阅读副本。没有代码镜像的既有目标，本组新增源码与测试是一致交接单元。源码、图及正文必须绑定同一发布manifest；本README的16 tests是作者实际执行结果，独立审阅另行签收。
