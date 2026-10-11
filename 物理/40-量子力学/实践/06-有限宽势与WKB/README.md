---
type: practice
domain: physics
stage: 2
aliases:
  - 有限宽势与WKB复算
sources:
  - https://ocw.mit.edu/courses/8-06-quantum-physics-iii-spring-2018/bf207c35150e1f5d93ef05d4664f406d_MIT8_06S18ch3.pdf
  - https://ocw.mit.edu/courses/8-04-quantum-physics-i-spring-2016/a565b327f85c7721b18f1074dbd69ede_MIT8_04S16_LecNotes11.pdf
  - https://ocw.mit.edu/courses/8-04-quantum-physics-i-spring-2016/79c490b96f77e1374c42d7119a940091_MIT8_04S16_LecNotes17.pdf
prerequisites:
  - "[[物理/40-量子力学/12-有限宽势匹配束缚与透射共振]]"
  - "[[物理/40-量子力学/13-WKB局部尺度转折点与量子化]]"
---
# 有限宽势与WKB复算

先读 [[物理/40-量子力学/12-有限宽势匹配束缚与透射共振#传播矩阵把三个内部支接起来|三个内部支的统一匹配]]。本实践给有限实矩形势与WKB谐振子的标准库程序、固定输入和同模型图。源码 [finite_wkb.py](finite_wkb.py) 是真源，[inputs.json](inputs.json) 给七个散射条件，[checks.json](assets/checks.json) 保留实际结果。固定教学尺度为 $m=10^{-30}$ kg、$\ell=10^{-9}$ m，$E_*=\hbar^2/(2m\ell^2)$；$h=6.62607015\times10^{-34}$ J·s 按 SI 精确定义，$\hbar=h/(2\pi)$。质量和长度是模型选择。

## 有限矩形势的固定答案

脚本中的坐标 $\xi=x/\ell$，能量 `e=E/E_star`，势 `v=V/E_star`，宽度 `width=a/ell`，导数是 $d/d\xi$。输入、结果及图的无量纲值不能直接当作 J 或 m。

| 条件 | 可先手算的结果 |
| --- | --- |
| `e=1,v=2,width=1` | $r=-i\tanh1$, $t=e^{-i}\operatorname{sech}1$, $T=\operatorname{sech}^21\approx0.419974342$ |
| `e=1,v=1,width=1` | 内部线性支，$T=4/5$, $\tau=1/(1-i/2)$ |
| `e=1+π²,v=1,width=1` | $q\ell=\pi$, $r=0$, $\tau=-1$, $T=1$ |
| `e=π²−1,v=−1,width=1` | 势阱内部 $q\ell=\pi$, $T=1$；正能共振 |
| `e=2,v=0,width=1` | $r=0,t=1$；检查全局相位参考 |
| `e=1±10⁻⁸,v=1,width=1` | 分别走衰减/传播支，连续趋向阈值 $4/5$ |
| 浅阱 $b=\ell,W/E_*=\pi^2/8$ | 唯一偶束缚态，$E_b/E_*=-\pi^2/16$，$N^2\ell=1/(1+4/\pi)$，$P_{\rm out}=2/(\pi+4)$ |

`r,t,tau` 在 JSON 中按 `[实部,虚部]` 输出。`tau=t*exp(ik*a)`；检查复相位时必须选同一参考面。七输入中的共振能量用双精度小数表示，检查容差允许其与解析 $\pi^2$ 的浮点差别。

## 运行、输出与误差

从包含 `物理/` 的课程根目录执行，Python 3 标准库，单线程，无安装，无外部服务：

```sh
python3 '物理/40-量子力学/实践/06-有限宽势与WKB/finite_wkb.py'
```

输出位置由源码所在目录决定，会写本实践 `assets/` 的两JSON、三CSV和三SVG。保留固定结果时，在自己的新临时副本中运行；在副本修改 `inputs.json` 后必须相应改变答案和图注。当前图固定使用源码内明确的绘图条件，不会自动把输入数组的任意新案例改成图。

每例直接构造 $2\times2$ 传播矩阵，代入左右界面的 $\phi,\partial_\xi\phi$，检查连续性、出口 `tau,ik*tau`、$R+T=1$；在 $\xi=-1,a/(4\ell),3a/(4\ell),a/\ell+1$ 四点从复波函数求净流，再与 $T$ 比较。无量纲残差容差 $10^{-12}$，没有把答案重新归一到 $R+T=1$。源码还对衰减手算、阈值和第一共振分别核独立解析数值。

浅阱用已知解析函数，内部 $[-1,1]$ 用 Simpson 2000面板积分，外部无限尾用精确积分，范数容差 $10^{-12}$。它核的是指定函数归一与匹配，未用数值搜索求全体有限阱谱。只有一个偶根的论证在正文由单调性和奇支符号给出，积分通过没有替代这个证明。

作者本次执行 exit 0：七案例最大匹配/通量残差 $4.4408920985\times10^{-16}$，浅阱积分范数 $1.0000000000000093$。这个误差在浮点和求积层；解析通量等式、算子域和共振条件由正文推导。独立核查者应在自己的副本运行，并以界面方程或另一组基本解核复幅度，避免只重复作者的闭式率。

## 图怎样消费同一模型

[finite-transmission.svg](assets/finite-transmission.svg) 从同一 `scatter` 复幅度产生 $V_0=\pm4E_*,a=2\ell$ 的率曲线；[transmission.csv](assets/transmission.csv) 保留401能量点。范围 $0.05\le E/E_*\le20$，正能左入射，同质量双侧开通道。有限取样不能替代解析共振位置与峰值。

[barrier-field.svg](assets/barrier-field.svg) 和 [barrier-field.csv](assets/barrier-field.csv) 固定 `e=1,v=2,width=1`，上窗是复幅度的实/虚部，下窗为势与能量；CSV另给 $|\phi|^2$ 与净流比。两个纵轴分别无量纲化，真实幅度取 $A=\ell^{-1/2}$ 时为 $\psi=A\phi$，真实能量为 $E_*e$。

这不是实验测量、归一波包的含时碰撞、三维截面、真实材料参数拟合或隧穿时间测量。极厚势垒的双曲函数会溢出，当前输入没有检验任意厚度的稳定传输算法；有损/非弹性或质量台阶应另立 Hamiltonian。SVG源码含title/desc，实际Obsidian/LaTeX显示和真人撤提示理解另属验证层。

## WKB作用量与局部失效的固定答案

读 [[物理/40-量子力学/13-WKB局部尺度转折点与量子化#用谐振子分开能量正确与波函数误差|谐振子WKB的单位与归一约定]]。`wkb_outputs` 固定 $n=0,5,20$，$e=n+1/2$，转折坐标 $\eta_t=\sqrt{2e}$。先用 $\eta=\eta_t\sin\theta$ 换元，将作用量积分变成光滑的 $\int_{-\pi/2}^{\pi/2}2e\cos^2\theta d\theta$，Simpson2000面板结果与精确 $\pi e$ 比较，容差 $10^{-12}$。本次最大求积差 $1.4210854715\times10^{-14}$，只是这三个固定积分的数值误差。

形状的真源为精确Hermite递推和正文封闭 $J(\eta)$，没有ODE步进或拟合。另在转折坐标的0、50%、90%、99%处输出精确幅度、WKB幅度、$\epsilon$ 与 $\chi$；$n=0$ 中心的解析 $\chi=1/2$，$n=20$ 中心 $\chi=1/(8\cdot20.5^2)\approx2.97442\times10^{-4}$，99%处则 $\epsilon\approx8.60145,\chi\approx93.2323$。WKB形状误差没有作为通过/失败阈值：这里有意展示近似的失效，`PASS` 只表示指定求积及矩形势检查通过。

[wkb-checks.json](assets/wkb-checks.json) 保留三态诊断，[wkb-oscillator.csv](assets/wkb-oscillator.csv) 保留 $n=0,20$ 各501点，[wkb-oscillator.svg](assets/wkb-oscillator.svg) 比较同模型形状；端点不求WKB，区间只到 $\pm0.99\eta_t$。坐标、幅度、能量均已按正文给定尺度无量纲化，可选任意 $m>0,\omega>0$ 恢复物理单位，图未指定真实振子器件。

领先形状用振荡平均给定的幅度规范，未重新归一去掩盖低能偏差。两转折量子化的谐振子精确能级是特殊成功，不证明任意势的WKB误差界。代码没有实现Airy函数或连接的数值匹配，没有求一般势的能级、绝热演化或跃迁率；Airy连接系数由正文与原始课程核对，独立核查者应分别核其条件、方向和 $\pi/4$ 相位。

返回 [[物理/40-量子力学/12-有限宽势匹配束缚与透射共振#改一个条件检验解释|条件变化与撤提示题]] 或 [[物理/40-量子力学/00-量子力学-MOC#累计正文与实践|课程入口]]。
