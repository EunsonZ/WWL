---
type: practice
domain: 物理
stage: 4
aliases:
  - 实践03 矩形腔壁损扩展
sources:
  - https://web.mit.edu/6.013_book/www/chapter10/10.7.html
  - https://ocw.mit.edu/courses/6-013-electromagnetics-and-applications-spring-2009/d3be4ea78b036a6362230fb41780cf54_MIT6_013S09_notes.pdf
prerequisites:
  - "[[物理/20-电磁学/10-矩形腔壁损与有限Q]]"
---

# 实践03扩展：六壁损耗与自由衰减

先读 [[物理/20-电磁学/10-矩形腔壁损与有限Q|矩形腔壁损主解释]]，从07的 TE101 场和04的趋肤阻抗预测每面热功率，随后读固定结果。此扩展单独计算六壁有限电导的主阶损耗，原 [[物理/80-实践/03-波界面与导模端口/README|实践03]] 的 PEC、平板与界面输入/结果保持原身份；本程序没有调用或重新运行 `solve_waves.py`。

## 模型、输入与真源

唯一规范源码为 [solve_cavity_loss.py](solve_cavity_loss.py)，仅用 Python 标准库；无 `code-sync` 实现副本。[inputs.json](inputs.json) 固定真空腔20×10×60 mm、1 nJ、统一正常非磁导体 $\sigma=5.8\times10^7$ S/m、壁厚1 mm。三个变条件是 $\sigma/4$、全部尺寸和壁厚乘2、仅 $b$乘1.5；每卡初始储能均为1 nJ。材料是合成教学参数，没有实测牌号或温度数据。

所有长度为 m、电导率为 S/m、能量为 J，场为峰值 $e^{i\omega t}$ 相量。沿用07的近似 $\mu_0=4\pi10^{-7}$ H/m、精确 $c_0=299792458$ m/s并导出 $\epsilon_0$，不把现代SI的 $\mu_0$称精确定义常量。内部为全波 PEC 模场，局部壁为正常趋肤；没有求有损本征频率的反应性修正或壁内完整三维场。

程序先核输入与所有算例，再建立新输出目录；已存在目录拒绝，不替换参考结果。在本目录执行下列命令，用一个**尚不存在**的新目录名：

```sh
python3 -I -B solve_cavity_loss.py --input inputs.json --output-dir /private/tmp/wwl-cavity-loss-my-run
```

stdout为完整JSON，同时新目录有 `values.json`，两者使用相同序列化。源码不写 `assets`。本页 [results/values.json](results/values.json) 是固定卡的作者计算；[results/decay.csv](results/decay.csv) 每卡121个时间点，共484行数据；[results/scaling.csv](results/scaling.csv) 每种变化33点，共99行数据。CSV使用LF，不夹入绘图手工点。换输入时复制为自己的卡、使用新的输出目录；不用覆盖本页参考数据才能试参数。

输入只允许声明字段；所有物理量/比例须正实有限且至少为浮点最小正规数（Python `sys.float_info.min`）；低于此数或派生运算的零除/溢出、非有限结果属于本实现不可表示域，拒绝并且不建立输出目录，拒绝bool、NaN/Inf、缺字段/未知字段和重复算例名。Simpson子区间需偶整数8–256、衰减点数3–2001、扫点3–501、最多12变卡。教学卡限定 $b<\min(a,\ell)$，保持TE101唯一最低模；$b=a$等简并输入被拒绝。最低竞争模从TE011、TM110、TE201、TE102取最小频率并保存名字和间隔。程序以命名筛选 $\omega\epsilon_0/\sigma<10^{-3}$、$\delta/\min(a,b,\ell)<10^{-3}$、$t_w/\delta>10$、$Q>100$、竞争角频差与能量衰减率之比 $\Delta\omega/(\omega_0/Q)>10$ 拒绝明显不在本教学近似范围的卡。这些阈值是公开的教学筛选选择，**不是误差定理**；通过它们仍不能证明异常趋肤、粗糙度、热反馈、附近模式或真实材料满足假设。被拒绝的几何不是没有物理解，而是需要改用适合简并/其他主模的模型。

## 作者实际算了哪些量

规范程序分别计算解析六面 $\int|H_t|^2dS$，再将相同矢量场直接限制到每一面，用二维复合Simpson积分逐面回代：$x$面只取 $H_z$、$y$面取 $H_x,H_z$、$z$面只取 $H_x$。体能量沿 $y$解析乘 $b$，沿 $x,z$作二维Simpson；每方向64子区间。积分路径不是只重排解析六面总式，但它仍由同一作者实现，不能充当非作者核查。

[values.json](results/values.json) 中 `cases` 保存每卡参数、频率/场峰值、趋肤/$R_s$、每面A²积分与W损耗、总W损耗、$Q,G$、两种时间常数和近似筛选量。`quadrature`保存实际逐面积分、平均电/磁能与相对差。基准卡各平均能量为0.5 nJ，总能量相对解析差约 $2.22\times10^{-16}$，总功率差约 $1.11\times10^{-16}$；本光滑整周期三角函数积分很接近浮点舍入，不能把这叫一般网格误差界或实际材料精度。

| 固定卡 | PEC参考频率（GHz） | 初始壁热（mW） | 壁损Q | 能量时间常数（ns） |
| --- | --- | --- | --- | --- |
| base | 7.900224939 | 7.135303828 | 6956.757337 | 140.148202 |
| sigma_quarter | 7.900224939 | 14.270607656 | 3478.378669 | 70.074101 |
| all_dimensions_double | 3.950112469 | 2.522710861 | 9838.340576 | 396.398975 |
| b_one_and_half | 7.900224939 | 5.905079030 | 8406.081782 | 169.345744 |

`decay.csv` 的 `time_s`在0–3个**基准**能量时间常数，同一物理时间对照各卡；`energy_ratio=exp(-t/τW)`，`amplitude_ratio=sqrt(energy_ratio)`，`energy_J=W0*energy_ratio`，`wall_power_W=P0*energy_ratio`。这里计算的是周期平均/慢包络；没有离散积分 GHz 载波，也没有宣称求完整初边值瞬态。

`scaling.csv` 的 `change=sigma` 表示固定几何扫 $\sigma/\sigma_0=0.25$–4；`all_dimensions`扫所有腔尺寸和壁厚同比0.5–2；`b_only`仅扫 $b/b_0=0.5$–1.5。每一点都由改卡后的频率、$R_s$和六壁式重算，再除基准Q；没有手设“Q必须等于根号曲线”作为计算结果。

## 图怎样从这些数据生成

先在正文作预测，再对照图和CSV/JSON。三份 [results](results/values.json) SVG与正文 `assets`同字节；生成依据在同一源码中，图均有title/desc、单位、线型和文字，不单靠颜色区分。更新正文图前须先核自己的输入/结果，不能将变卡图替换成本页默认图。

- [wall-loss.svg](assets/wall-loss.svg) 画每个面各一条，面积mm²、热功率mW；六条数值来自基准 `face_power_W`。最大面积的一面不自动意味着最大损耗，必须用其场积分。
- [ringdown.svg](assets/ringdown.svg) 左为能量比例，右为场包络比例，横轴µs；实线基准，虚线电导除4，同一物理时间读取 `decay.csv`。这不是载波电场曲线。
- [q-scaling.svg](assets/q-scaling.svg) 左为电导比与Q比；右为全尺寸比和仅b比与Q比，点来自 `scaling.csv`。仅b曲线止于1.5，未将b=a的简并当普通独立单模器件。

## 撤提示练习与证据边界

先做正文的初始能量×4与全尺寸×2题。需要复算能量×4时，只修改新卡的 `base.initial_energy_J`；保持其他输入并输出到新目录。比较每面W损耗和Q，观察线性模型怎样使它们对激励幅度作不同响应。

有限复算是指定场/局部壁近似的计算证据；没有认证真实电导、接缝、粗糙度、热反馈、频率反应性修正、介质损耗、外耦合、加载S/线宽、模式混合、商业全波、VNA或硬件。作者自查不等于非作者理论/运行验收，结构检查不等于Obsidian显示/同步，撤提示题答案不等于真人掌握。完整课程仍由 [#247](https://github.com/EunsonZ/WWL/issues/247) 承担。

返回 [[物理/20-电磁学/10-矩形腔壁损与有限Q#两个容易混淆的出口|壁损与截止/加载边界]]，再从 [[物理/20-电磁学/00-电磁学-MOC|课程地图]] 继续。
