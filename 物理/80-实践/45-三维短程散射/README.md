---
title: 三维短程散射复算
stage: 0
aliases:
  - Born部分波截面复算
sources:
  - https://ocw.mit.edu/courses/8-06-quantum-physics-iii-spring-2018/45dbd7038c3e969491eceeae86c44d42_MIT8_06S18ch7.pdf
  - https://quantummechanics.ucsd.edu/ph130a/130_notes/node229.html
prerequisites:
  - "[[物理/40-量子力学/21-三维短程散射Born与部分波截面]]"
---
# 三维短程散射复算

同一个低能入射，弱阱为什么可用一次 Born，而接近首个束缚阈值时会漏掉两个数量级的截面？[[物理/40-量子力学/21-三维短程散射Born与部分波截面#先固定相对运动与入射幅度|主解释]]先从球波与通量定义面积，再由 Green 积分和径向匹配求同一个幅度。本实践只跑实、球形、有限程吸引方阱的可区分、单弹性相对运动；角度属于质心系。

## 先写预测

运行前给出四个预测：弱阱的 Born 前向幅为何是正且用 m；接近 $\eta=\pi^2/4$ 时 Born 低能值是否含极点；只有 s 波是否仍足以解释 $ka=2$ 的角分布；把半径加倍但保持 $\eta,ka$ 不变，截面和入射流标度怎样变。随后核 [[物理/80-实践/45-三维短程散射/ANSWERS|手算与迁移答案]]。

默认 $a=10^{-9}\,\mathrm m$、$\mu=10^{-30}\,\mathrm{kg}$，$\hbar=1.054571817\times10^{-34}\,\mathrm{J\,s}$（教学精度）。$E_a=\hbar^2/(2\mu a^2)$，$W=\eta E_a$，$E=(ka)^2E_a$。五卡依次是 weak $(0.09,0.1)$，moderate $(1,2)$，below $((\pi/2-0.02)^2,0.1)$，threshold $((\pi/2)^2,0.1)$，above $((\pi/2+0.02)^2,0.1)$；括号为 $(\eta,ka)$。

每卡保持自己的阱深，101个几何间距 $ka\in[0.03,4]$ 作能量扫描。另在共同 $ka=0.1$ 上用201个 $\eta=0,0.02,\ldots,4$ 作深度扫描。默认部分波 $l=0,\ldots,16$；角图181个均匀 $\theta\in[0,\pi]$ 点。全角积分另用64点 Gauss–Legendre，不以角图网格代替球角积分。

## 复建同一输入与输出

Python 3.10+，只用标准库，无需编译或第三方数值依赖。新环境安装符合版本的 Python 即可；终端先核 `python3 --version`。在本实践目录执行，输出目录必须不存在：

```bash
python3 -B scattering.py --inputs inputs.json --output /private/tmp/qm-scattering-reader-output
```

源码自带默认同目录输入定位，但输出始终显式指定。若现有环境有统一守卫，其实际用法是：

```bash
python3 -B /private/tmp/numerical_guard.py --threads 1 --timeout 60 --lock-timeout 60 -- python3 -B scattering.py --inputs inputs.json --output /private/tmp/qm-scattering-guarded-output
```

守卫为环境工具，缺失时仍可使用标准库学生入口；直接入口不自带超时。本单元按单线程60秒预算预跑，默认作者运行约0.23秒；时间依赖机器，不能当性能保证。非法输入退出2；目标目录已经存在或为符号链接也退出2，保留旧结果。数值与验证不启动服务，不读取硬件。

| 文件 | 对象、shape与单位 |
|---|---|
| `results.json` | 原输入、教学 $\hbar$、$E_a$、每卡全部 $L+1$ 个通道、复前向幅、全/单 s/Born/球角积分/光学总量、$L\to L+4$ 增量、散射长度及 s 束缚根；$f/a$ 和 $\sigma/a^2$ 无量纲，同时给 $\sigma$ 的 m²、$W,E$ 的 J、$k$ 的 m⁻¹。 |
| `partial-waves.csv` | 每卡每通道一行，$l$ 零起始整数；$S_l$ 两实分量、模 $\pi$ 的相移 rad、$\sigma_l/a^2$ 及 m²。相移不是连续展开的全分支。 |
| `angular.csv` | 每卡每角一行，$\theta$ rad、$\cos\theta$、复 $f/a$、实 Born 幅；三个面积/a²以及 PW/Born 的 m²/sr。全通道先相加幅再平方；单 s 行为独立对照。 |
| `energy.csv` | 每卡固定 $\eta$ 改 $ka$；全/单 s/Born 的 $\sigma/a^2$、$E$ J和新增四通道的面积/a²。 |
| `depth.csv` | 固定 `depth_scan_x` 改 $\eta$；总/单 s/Born 面积/a²、$a_s/a$、存在时的负束缚能/$E_a$。极点和无束缚态的 CSV 字段为空、JSON 为 null；不填0冒充有限值。 |
| `angular.svg` | 每卡独立窗，直接消费同一 `angular` 数组；同图比较 PW、Born 与单 s。纵轴面积/a²、横轴 rad。 |
| `energy.svg` | 直接消费 `energy`，横轴 $\log_{10}(ka)$、纵轴 $\log_{10}(\sigma/a^2)$；同色同卡，实线PW/虚线Born。自由零势不在log轴画零；若全部卡为自由势则明确改线性零图。 |
| `depth.svg` | 直接消费 `depth`，分窗画有限能截面与负能 s 分支；零能阈值不画作归一束缚态。无可画负能支时用明确的“no resolved bound branch”零虚线。 |

默认八份资产保留在 `assets/`。图源在规范 `.py`，[[物理/80-实践/45-三维短程散射/SOURCE|源码全文镜像]]供阅读；所有改变先改 `.py` 再同步镜像。CSV 可包含标准 CRLF，数值行不代表 prose。

## 输入域与浮点阈值

顶层严格含 `units,radius_m,reduced_mass_kg,l_max,angle_points,scan_x,depth_scan_eta,depth_scan_x,cases`；单位严格为 `{"length":"m","mass":"kg","energy":"J","angle":"rad"}`。$10^{-12}\le a\le10^{-6}$ m、$10^{-32}\le\mu\le10^{-26}$ kg；范围只为这个教学数值入口，不认证此全部参数都满足真实材料的非相对论近似。

`l_max` 为10–24的整数；`angle_points` 为31–361的整数。`scan_x` 有2–161个严格递增、$0.03\le ka\le4$ 的值；`depth_scan_eta` 有2–241个严格递增、$0\le\eta\le4$ 的值；`depth_scan_x` 同 $ka$ 域。案例数1–8，每卡严格含 `name,eta,x`；名称为唯一 ASCII 字母数字、下划线或连字符，长度1–24，$0\le\eta\le4$，$0.03\le x\le4$。未知/重复键、布尔冒充数字、NaN/Infinity和溢出、非法网格均拒绝。$k=0$ 只在正文作极限，不是该散射入口的合法卡；负 $W$ 的排斥球题由答案解析完成。

binary64 输入的 `eta == (pi/2)**2` 当作无可分辨阈侧：报告 $a_s$ 为 null、没有归一束缚态。若输入和阈值已被舍入为同一浮点数，程序无法恢复它原本写在阈上还是阈下；更高精度测量或计算须另用更高精度输入。可分辨的极浅阈上卡直接在 $w=\kappa a$ 上求根，$E_b/E_a=-w^2$，避免 $\eta-z^2$ 相减；近极点散射长度用

$$d=\frac{\eta-(\pi/2)^2}{\sqrt\eta+\pi/2},\qquad a_s/a=1+\frac1{\sqrt\eta\tan d}$$

稳定计算。阈值常量本身是 binary64 的 $\pi$ 表示，不宣称所有实数的阈值可无限精确分辨。

## 计算路线与独立复算接口

内部 $Q=\sqrt{x^2+\eta}$。$j_l$ 用收敛幂级数，$n_l$ 从 $n_0,n_1$ 向上递推，导数用 $j_l'=lj_l/z-j_{l+1}$ 及 $n_l'=ln_l/z-n_{l+1}$。输入域的 $0<z\le\sqrt{20}$ 保持该轻量实现有界；不能无修改推广到大参数、大 $l$ 或复势。交叉乘积匹配输出 $S_l=(D_l+iN_l)/(D_l-iN_l)$，避免内部 Bessel 零点的对数导数除零。

精确单 s 通道可独立用

$$S_0=e^{-2ix}\frac{Q\cos Q+ix\sin Q}{Q\cos Q-ix\sin Q}$$

复算；全通道可另用正则径向 ODE 和出/入 Hankel 的2×2匹配，或成熟球 Bessel 函数。Born 可由球内的三维 Fourier 积分或 $\int_0^1s^2\sin(ys)/(ys)ds$ 独立求积。负能根可另解 $z\cot z=-\sqrt{\eta-z^2}$，但极浅阈上的独立数值应保持高精度，不能复制已知相消错误。

`results` 的 `unitarity_residual`、球角积分与分波和/光学式的一致性属于作者自查；它们未独立证明匹配的物理条件。$L\to L+4$ 增量只是有限收敛指标，既不是一般无限尾界，也不是其余势形的收敛证明。本输入域上可增加 $L$、使用独立径向路线核有限精度；一般短程阈值规律仍由理论前提承担。

## 图与解释的范围

![[物理/80-实践/45-三维短程散射/assets/angular.svg]]

Born 的角度结构与全部通道的幅度干涉在同一输入下比较。weak 尚有约7%的总截面差，不能把小幅度界说成零误差；moderate 的角结构不能只用 s 波。

![[物理/80-实践/45-三维短程散射/assets/energy.svg]]

低能常数与阈值增长不同。近阈 $k|a_s|$ 大时不能直接读 $4\pi a_s^2$；有限能精确值仍遵守每通道酉性上限。

![[物理/80-实践/45-三维短程散射/assets/depth.svg]]

本固定有限球阱接通量、Fourier、分波和负能谱；它没有测真实截面，也没有运行波包碰撞、相同粒子探测、长程或非弹性散射。数值/图运行、解析理论独核、客户端显示与真人迁移为不同证据层。半导体材料的出态率或输运率需要 DOS、占据和速度条件，也不直接等于本页面积。
