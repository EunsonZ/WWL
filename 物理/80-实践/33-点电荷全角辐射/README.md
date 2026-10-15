---
domain: 物理
type: practice
stage: 5
aliases: []
sources:
  - https://farside.ph.utexas.edu/teaching/em/lectures/node132.html
prerequisites:
  - "[[物理/30-电动力学/09-点电荷全角辐射#同一束能量有两个时间分母]]"
---

# 点电荷全角辐射：角度、时钟与总能量

先读 [[物理/30-电动力学/09-点电荷全角辐射#从完整球面积分得到 Larmor 和 Liénard|角积分推导]]，再用这里的原叉乘角场积分复算。源码为 [radiation.py](radiation.py)，输入为 [inputs.json](inputs.json)，保留输出在 [output/results.json](output/results.json)。只用 Python 3 标准库，单进程、单线程，不联网、不安装依赖。

进入本实践目录，将结果写到一个**尚不存在**的目录：

```bash
python3 -B radiation.py --inputs inputs.json --output /tmp/wwl-radiation-new-run
```

输出目录若存在则拒绝执行；换一个新目录保留旧运行。`--inputs` 可指向复制后修改的输入；不要拿本页固定参数表认证改过的数据。实践不依赖候选作者本机的并发管理脚本；本机协作期间运行通过统一双槽外层守卫，守卫不属于物理算法。

## 角度时钟和全角积分分别核对什么

程序在实验室构造 $\mathbf n\times[(\mathbf n-\boldsymbol\beta)\times\mathbf a]$，积分 $|\mathbf Q|^2/\kappa^5$，不调用 Liénard 总量作为积分函数。方位角周期梯形16/32节点；极角用 $\mu=(w+\beta)/(1+\beta w)$ 的换元和完整 Jacobian，$w$ 上80/160区间 Simpson。解析总量是独立对照。该换元在本光滑积分中消除窄前向峰带来的采样困难；这几个高精度结果不说明同一网格能处理任意非光滑角源。

`cases` 的加速度是共同归一单位下的分量，`integral` 与 `oracle` 均已除 $C=q^2/(16\pi^2\epsilon_0c^3)$；不把这个数字当 W。默认四例分别为静止平行、$\beta=0.6$平行/垂直、$\beta=0.995$混合加速度 $(a_\perp,a_\parallel)=(0.6,0.8)$。最大相对差约 $2.08\times10^{-14}$。`z_momentum_residual` 核对 $\int\mu U_{\rm em}d\Omega/P-\beta$，最大约 $2.07\times10^{-14}$；未将这个远区动量率直接叫作完整自力。

[angles.csv](output/angles.csv) 保存 $\beta=0,0.6$ 的 $U_{\rm em}/P$，单位 sr⁻¹；[beam.csv](output/beam.csv) 保存 $\beta=0.995$ 的发射/接收角强度除以 $Ca^2$。图的右侧各除以自己的峰值，原数据仍保留绝对相对系数。两峰的 $\gamma\theta$ 分别约0.501738与0.448800，与高 $\gamma$ 极限的0.5和$1/\sqrt5$相连。图在 [emission-angle.svg](output/assets/emission-angle.svg)，由同一脚本的同批数组生成。

## 有限运动脉冲的绝对归一化

沿用 [[物理/30-电动力学/06-有限运动脉冲与因果场#始终存在的电荷只在有限时间运动|06 的电荷历史]]，$q=1$ nC、$L=3$ m、$b=0.2$，$T=L/c$；常数与既有课程一致。这里补出全角总量，并不改变原来横向一个方向的结果。

| 量 | 默认作者运行 |
|---|---:|
| $T$ | 10.0069228559 ns |
| 全角总辐射能量 | 409.670590746 pJ |
| 同一轨迹的非相对论 Larmor 预测 | 394.238136551 pJ |
| 相对论值 / 非相对论值 | 1.039145006 |
| $+y$ 单方向能量 | 47.0587111405 pJ/sr |
| 错误地取 $4\pi$ 倍横向值 / 真总量 | 1.443494403 |

沿源时间用100/200区间 Simpson 积分解析 Liénard 功率；另一条计算在100个时间子区间的各节点先积分全角原场，然后积时间。此输入两结果及两时间网格在显示浮点精度相同，记录差为0，不意味着严格符号相等或数值误差数学上为零。[pulse.csv](output/pulse.csv) 给同一轨迹的相对论与低速预测，量纲为 W；该表没有拿近区全场 Poynting 通量冒充辐射。

## 改条件再预测

复制输入，分别改变 `pulse_b` 和 `pulse_L_m`。固定 $b$、$L$加倍时应使 $W$减半；增大$b$则不能把 $W\propto b^2$ 当精确关系，因为 $\gamma^6$ 同时改变。角度例中把同一大小加速度从平行旋到垂直，应在固定速度下从 $\gamma^6$变为$\gamma^4$。极端$b\to1$要另外做时间网格收敛，本页默认100/200节点不是任意$b$的保证。

当前保留的是作者实际运行的有限输出（2026-10-11，`/usr/bin/python3`，两槽外层守卫下exit0，约0.21s含启动/守卫）。未观测峰值RSS，未声称内存硬限制。重要理论、独立复建与图像检查由单独验收完成后记录；这里不把作者断言视为独立签收，也不声称真实Obsidian显示、实验装置或真人学习已验证。返回 [[物理/30-电动力学/09-点电荷全角辐射#把06的有限运动补成总能量|正文同一脉冲]] 解释表中相对论修正与错误各向同性外推。
