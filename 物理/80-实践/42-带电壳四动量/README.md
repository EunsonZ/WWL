---
domain: 物理
type: lab
stage: 5
aliases: []
sources:
  - https://arxiv.org/abs/1808.09320
prerequisites:
  - "[[物理/30-电动力学/13-有限带电壳与总四动量#同时切片怎样留下三分之四问题]]"
---

# 带电壳四动量：场积分与材料闭合

这张有限卡用两条计算路线比较同一静态球壳：从变换后的电场／磁场积分能量与动量，再从局部能动量张量 boost 积分。随后纳入维持壳形的膜张力，核对整体能量、动量及不变量。理论、符号和壳面平衡的主解释在 [[物理/30-电动力学/13-有限带电壳与总四动量|13 有限带电壳]]；这里给实际源码、固定输入、图和可改变条件。

## 从静止卡复建六个结果

只需要 Python 3.10+ 标准库。先到此目录，选一个**尚不存在**的输出目录：

```bash
python3 charged_shell.py --inputs inputs.json --out /private/tmp/charged-shell-first
```

命令成功返回 JSON 摘要，目录内恰有六文件：`results.json`、`beta-sweep.csv`、`convergence.csv`、`parameter-cases.csv`、`momentum.svg`、`shell-slices.svg`。本页随库的 [默认输入](inputs.json) 与 [默认结果](assets/results.json) 对应；[规范源码](charged_shell.py)和 [[物理/80-实践/42-带电壳四动量/SOURCE#源码镜像|镜像]]是同一实现。`elapsed_s` 只是运行时长观察，其他输出可复建比较。

程序在计算前验证完整卡和输出父目录；输出路径已存在、为符号链接或坏卡均拒绝，不提供覆盖选项。新目录的父目录要已存在。数值时长与全局并发上限由调用环境控制；源码本身有网格、参数和样本数上限，不声称有内存硬限制。

固定卡为 $Q=1$ nC、$a=1$ cm、膜静能 $W=1$ μJ、观察者 $\beta_v=0.6$，即壳在新系向 $-x$ 运动。$\epsilon_0=8.8541878128\times10^{-12}$ F/m 是源码明示的固定教学值。静态壳和它的惯性换系在理论上允许所有 $|\beta_v|<1$；CLI 限制 $|\beta_v|\le0.9$，用有限范围观察变换与收敛，未用数值卡认证临近光速的条件数。

| 输入字段 | 意义与允许范围 |
| --- | --- |
| `charge_C` | 带符号电荷，$10^{-15}\le|Q|\le10^{-6}$ C；零电荷不在这张 $4/3$ 对照卡范围 |
| `radius_m` | 正半径，$10^{-6}\le a\le10$ m |
| `material_rest_energy_J` | 独立膜静能，$10^{-15}\le W\le10^{-2}$ J，并核 $W\ge U_{\rm em}/2$ |
| `beta` | 观察者沿 $x$ 的有符号速度比，$-0.9\le\beta_v\le0.9$ |
| `n_mu,n_phi,n_radial` | 整数网格，分别8–256、8–64、8–128；三者乘积不超过1500000 |
| `beta_sweep` | 2–31个不重复、同范围的速度比，输出前按大小排序 |

JSON 要恰有上述八个字段，拒绝缺项、多项、重复键、布尔型数字、非有限量和超范围值。`material_rest_energy_J` 被当成已给的平衡状态能量，没有假定 $W$ 由场能或张力唯一决定。

## 两条积分与有限网格误差

源码采用 $\mu=n_x\in[-1,1]$ 的中点网格和方位角周期梯形。全径向范围用 $q=a/r\in[0,1]$ 紧化：

$$\frac{E(r)}{E(a)}=q^2,\qquad \frac{r^2|dr|}{a^3}=q^{-4}dq.$$

能量积分的两因子相消，径向积分的被积函数是常数；这是此 Coulomb 壳的解析结构。`n_radial` 改变不会带来有意义的径向截断收敛；它不是将任意场积分都做成常数的通用方法。程序直接使用全 $[0,1]$，无穷远未被截掉。

每个角节点分别计算变换后的 $E',B'$ 与 $T'^{00},T'^{01}$；两条路线共享模型、网格和体积因子，所以它们相同能检出局部变换/代码错误，不能独自认证全部解析模型。材料膜的空间分布及静能也作局部 boost，再用 $d^3x'=d^3x/\gamma_v$ 的同一测度积分。解析基准与误差分别输出，不能用字段名里“exact”把数值值改名为精确解。

默认 $n_\mu=64$ 的结果为 $U_{\rm em}=4.4937758961\times10^{-7}$ J，数值整体 $\mathcal E'\approx1.8117466721\times10^{-6}$ J、$cp'_x\approx-1.0870743340\times10^{-6}$ J；对应解析值分别是 $1.8117219870\times10^{-6}$ J、$-1.0870331922\times10^{-6}$ J。差值来自角网格。

`convergence.csv` 比较8、16、32、64、128和用户指定 $n_\mu$。本中点网格

$$\langle\mu^2\rangle_N=\frac13-\frac1{3N^2},\qquad
\Delta S\equiv\int(T^{11}_{\rm em}+T^{11}_{\rm mat})d^3x=\frac{U_{\rm em}}{2N^2}.$$

因此整体能量误差为 $\gamma_v\beta_v^2\Delta S$，$cp'_x$ 误差为 $-\gamma_v\beta_v\Delta S$，网格加倍缩小4倍。特别要注意，数值不变量残差恰为

$$\frac{\mathcal E_{\rm num}'{}^2-c^2p_{\rm num}'{}^2}{\mathcal E_0^2}-1
=-\beta_v^2\left(\frac{\Delta S}{\mathcal E_0}\right)^2.$$

它缩小16倍，**会掩盖能量、动量本身的较大误差**。默认不变量残差约 $-5.16\times10^{-10}$，并不说明两个分量已各自准确到 $10^{-10}$；必须同时看各分量误差和应力平衡残差。

## 改变一张卡并解释结果

复制输入到库外新文件，改变半径为0.02 m，先预测再运行：

```bash
python3 - <<'PY'
import json
from pathlib import Path
card=json.loads(Path('inputs.json').read_text())
card['radius_m']=0.02
Path('/private/tmp/charged-shell-a2.json').write_text(json.dumps(card,indent=2)+'\n')
PY
python3 charged_shell.py --inputs /private/tmp/charged-shell-a2.json --out /private/tmp/charged-shell-a2
```

也可改 `charge_C` 的大小或符号、`beta` 的正负、`n_mu`。每次选择新的输出目录，保留旧结果方便比较。`parameter-cases.csv` 另列同一默认卡的半径加倍、电荷加倍、反号，并保持 $W$ 固定，给出材料局部能量界是否仍满足。

这些变卡每次重新指定平衡张力，比较的是不同规定膜状态。它们没有提供同一材料的 $W(a,Q)$、充电做功或弹性响应，因此不能当成同一膜随时间演化的实验。`membrane_removed` 只给**静止初始切片**上的未平衡压力与空间应力积分；它没有后续时间延拓，不输出跨系等时面的完整积分。

图用同一数值结果生成，单位、观察者速度和动量符号均在图中标明；曲线的横轴是改变观察者，不能解释成力作用下的时间轨迹。半径与电荷扫描也不是真实材料测量。

## 带着结果返回主解释

先比较 `default.field_E/field_cp` 与 `default.tensor_E/tensor_cp`，再比较数值总量与解析总量；最后检查网格加密。`same_slice_em_E_J/same_slice_em_cp_J` 是在**同一静止 $t=0$ 几何面**上换坐标后的解析协变积分，用来与各观察者自己的等时面作区别；它不是另一次普通 $t'=0$ 场能测量。

回到 [[物理/30-电动力学/13-有限带电壳与总四动量#Laue 条件为何使总积分闭合|13 的 Laue 条件]]，解释材料膜为何令总空间应力积分为零；再回到 [[物理/30-电动力学/13-有限带电壳与总四动量#同一几何积分面始终协变|13 的同面与异面]]，说明场张量保持协变而场的观察者等时积分仍有 $4/3$ 的原因。练习答案在 [[物理/80-实践/42-带电壳四动量/ANSWERS#迁移题核查|ANSWERS]]。这张卡没有运行加速壳、微观材料、任意点电荷自力或强场动力学；真实客户端显示与真人理解也不是一次程序运行能证明的结果。
