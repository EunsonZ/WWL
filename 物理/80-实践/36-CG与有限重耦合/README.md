---
type: practice
domain: physics
stage: 2
aliases:
  - 九维CG与三自旋重耦合复算
sources:
  - https://dlmf.nist.gov/34.1
  - https://dlmf.nist.gov/34.2
  - https://dlmf.nist.gov/34.4
  - https://arxiv.org/abs/1009.2811
prerequisites:
  - "[[物理/40-量子力学/15-CG变换重耦合与相位约定]]"
---
# CG与有限重耦合复算

先在 [[物理/40-量子力学/15-CG变换重耦合与相位约定|正文15]] 写出预期，再用本页源码检查三件事：自行生成全部 CG 耦合列；把27维的两种三自旋耦合列直接内积；改变 j、相位或制备后重新算测量。两自旋共同旋转与不可约分解的理论入口在 [[物理/40-量子力学/14-角动量相加与两自旋耦合#一般 j₁、j₂ 加法为何只有这些块|14的一般加法]]。

## 从固定输入到实际输出

需要 Python 3 标准库，无 NumPy、SymPy 或外部 CG 表。源码真源是 `cg_recoupling.py`，固定输入是 `inputs.json`。在本目录运行：

```bash
python3 cg_recoupling.py --input inputs.json --output assets
```

在此次候选环境已有数值双槽守卫，可用下列预跑命令；守卫不属于本实践源码的安装依赖，不需要读者另装：

```bash
python3 /private/tmp/numerical_guard.py --threads 1 --timeout 60 -- python3 cg_recoupling.py --input inputs.json --output assets
```

源码是单线程纯 Python；守卫将数值库线程环境限制为1并控制两槽，不声称提供内存限额。模型矩阵最大为49×49（两个输入均为 j=3 时），本页三体只有27维；本次实际运行约0.2秒。默认作者复算给9/12/27维，固定 J,M 的三体列数为3，最大残差约 $2.22\times10^{-15}$，阈值 $10^{-11}$。这是本机作者运行结果，独立审阅与独立运行仍分别承担验收；没有硬件测量证据。

| 输入键 | 默认值与含义 | 可改范围 |
| --- | --- | --- |
| `main_two_j` | `[2,2]`：自旋1×自旋1完整9维主例 | 固定；程序拒绝替换，图尺寸与文件名对应主例 |
| `variant_two_j` | `[3,2]`：3/2×1完整12维迁移 | 每个 2j 必须为整数0..6；要有两个数 |
| `three_two_M` | `2`：三个spin1的总 J=1、M=1 | 整数−2、0、2；三种M另在内部全重算 |
| `multiplet_phases_radians` | `[0.23,-0.47,0.71]`：主例 J=2,1,0 的列相位 | 三个有限实弧度；一整个J块使用相同相位 |
| `left_phases_radians`、`right_phases_radians` | 每组3相位，分别用于 AB 标签 e、BC 标签 f 的0,1,2列 | 各三个有限实弧度 |
| `phase_samples` | `241`：从0到2π的相干制备相位样本 | 整数3..2001，包含两端 |
| `tolerance` | `1e-11`：最大矩阵/概率残差阈值 | 有限正数，至多1e-8；过小可能被浮点残差拒绝 |

`two_j`、`two_M` 是整数的两倍量子数，不是 Hilbert 维数；单因子维数等于 `two_j+1`。所有算子用 $J_z/\hbar,J^2/\hbar^2$ 无量纲单位，概率无量纲，相位弧度；没有能量、时间或空间分布输入。新输入复算请用独立输出目录，例如 `--output /private/tmp/cg-changed`，以便和固定交付数据比较。

## 如何从算子构造而非读取表

源码 `couple(t1,t2)` 按乘积基 $(m_1,m_2)$ 双递减构造总 Z、升降矩阵与 $K=L_-L_++Z^2+Z$。由最大 J 开始，在每个 M=J 块把已知更高 J 列投影出去，投影种子是 $m_1=j_1,m_2=J-j_1$；两遍正交化后最高态归一，端点系数正。再以正降算符因子生成整块，不额外归一各列。

```text
states = {}
for J from j1+j2 down to abs(j1-j2) in steps of 1:
    v = product_basis_vector(m1=j1, m2=J-j1)
    twice: subtract projections onto all earlier states at M=J
    normalize v; choose its m1=j1 coefficient positive
    for M from J down to -J:
        store v as column (J,M)
        if M > -J: v = Lminus v / sqrt((J+M)(J-M+1))
Q = all stored columns
```

输出前逐项核 $Q^\dagger Q=I,KQ=Q\operatorname{diag}[J(J+1)],ZQ=Q\operatorname{diag}M$、升算符关系；等自旋额外用直积行置换检查 $(-1)^{2j-J}$ 交换奇偶。不同自旋的交换是到反序因子空间的映射，本代码不把它误充本空间的奇偶标签。

`cg_factorial` 另实现 [DLMF 34.1.1](https://dlmf.nist.gov/34.1#E1) 的 CG/3j 相位关系与 [34.2.4–5](https://dlmf.nist.gov/34.2#E4) 的有限阶乘和。阶乘的有理数部分用 `Fraction` 求和，根式最后转双精度。它没有用最高态向量生成该和，因此可抓相位/递推错误；两条公式实现仍属于作者源码，不能自称独立审阅。

`recoupling` 使用两次 `couple` 把 W_e、V_f 写进三因子直积空间，得到27×3的 W,V，然后直接 `R=V†W`。行 f、列 e，e、f从0到2。它从27×27实际总 Casimir 与 AB/BC平方算子分别验证共同本征量、两基同一子空间和中间算子投影，再用 [DLMF 34.4.2](https://dlmf.nist.gov/34.4#E2) 的含四个三角因子的 Racah 和另算6j。

## 七个数据产物怎样读

| 文件 | 实际保存什么 |
| --- | --- |
| [results.json](assets/results.json) | 两体基/列标签、完整 Q9/Q12、三体27行基及 W/V/R、6j、中间算子和非零对易子；相位测试与逐项残差 |
| [cg-nine.csv](assets/cg-nine.csv) | 主例81条：每条一个乘积行/耦合列，含整数两倍标签和零系数 |
| [cg-variant.csv](assets/cg-variant.csv) | 默认迁移144条：12×12，块为6+4+2；改输入时尺寸随实际 j 改变 |
| [recoupling.csv](assets/recoupling.csv) | 九条 f/e：有符号内积、常规6j及绝对值平方 |
| [phase-migration.csv](assets/phase-migration.csv) | 241相位下 $(W_0+e^{i\phi}W_1)/\sqrt2$ 的三种BC概率及解析 $p(f=0)$ |
| [cg-nine.svg](assets/cg-nine.svg) | 9×9有符号 Q，由实际数组画；横轴 J,M，纵轴 m1,m2 |
| [recoupling.svg](assets/recoupling.svg) | 实际 R、有标签的 W0 概率条与同相位CSV的三条曲线 |

CG 表内本应为零的位置可能出现 $10^{-16}$ 量级浮点数。CSV/JSON保留原数，图将绝对值小于 $10^{-12}$ 的格显示为0；没有把原数据改写成精确代数值。默认 R 的第一列平方为 $1/9,1/3,5/9$，BC平均平方为 $4\hbar^2$。J=1,M=1空间是三维重复表示空间，整个 M=1 产品块六维；JSON W/V的27行没有用任意三行子矩阵冒充完整态。

![[物理/80-实践/36-CG与有限重耦合/assets/cg-nine.svg]]

![[物理/80-实践/36-CG与有限重耦合/assets/recoupling.svg]]

相位改基用 $Q'=QD,b'=D^\dagger b$，重耦合改基用 $R'=D_V^\dagger R D_W$。默认文件保存同一态的 Born 概率不变，并保存“改列却不改旧坐标”会产生不同制备的对照。相干扫描的相位是固定基中改变制备的相对相位；这两种相位任务在源码不同函数中处理。

## 手算与变条件检查

预测答案见 [[物理/40-量子力学/15-CG变换重耦合与相位约定#自行预测后改变条件|正文15迁移]]。默认变 j 已实际算3/2×1十二维，不复用旧六维结果。还可以把 `variant_two_j` 改为 `[4,2]`，先预测维数15、J=3,2,1、块7+5+3，再在独立输出目录检查谱和系数；这条建议本身不表示所有可能输入已穷举验收。改 `three_two_M=0` 应保持 R 和 W0的BC概率，SVG标题跟随实际 M。

复算重要结果时除了看最大残差，还应独立读取列标签、抽取至少一列手核升降与正交、用直积态计算一个 Born 概率，并检验改变条件是否改变应该改变的量。只看到运行退出零或图像渲染成功，不足以证明推导或学习效果。

本实现有界小规模、双精度，不保证大 j、任意多体或近抵消场景的稳定性。有限纯态的基变换没有实现真实测量、动态控制、空间交换或完整 boson/fermion 统计；三可寻址因子的标签也不是不可分辨粒子本体标签。
