---
type: lab
domain: signals-systems
stage: 3
aliases:
  - db2长滤波边界与Riesz双基实验
sources:
  - "[[信号与系统/20-数字信号处理/08-db2连续构造双正交稳定性与长边界]]"
prerequisites:
  - "[[信号与系统/80-实践/14-Haar函数空间与消失矩/README]]"
---
# db2：连续证明与有限边界怎样接起来

主解释在[[信号与系统/20-数字信号处理/08-db2连续构造双正交稳定性与长边界|连续db2、真实双基与长边界]]。本实验只执行新的有限长边界、有限周期改基和cascade示意；连续存在、支撑、保守Hölder、正交MRA完备、全尺度Riesz双基由该页的推导证明，独立核查分别覆盖。有限全基向量不代替一般证明。

## 固定输入与真正复用的对象

[fixed-inputs.json](fixed-inputs.json) 固定 $x=(1,3,2,6,5,4,0,-1,2,1)$ V，$f_s=16$ Hz，$N=10$，新全基向量长度 `[6,8,10,18]` 共42个，周期细节改基参数 $a=.5$。cascade从 $1_{[0,1)}$ 开始，保存 $J=4,8,12$、显示网格间距1/128；dual部分和保留 $r=0..8$。失稳输入取 $M=8,32,128$ 个有限支持交替系数，专门在 $a=1$ 检查输出端点，不把非法参数喂给逆。

[db2_lab.py](db2_lab.py) 是新真源，**不另写db2 tap表，也不另写卷积**。实际读取：

- [已发布lab14保存JSON](../14-Haar函数空间与消失矩/results/results.json) 的 `filters[name=db2_mask].h/g`，SHA `d6fa93ff5b4aa044bdd620128683b98b0ff781f5fe2fe021e4efe223fffc1830`。
- [原重采样源码](../02-流式音频重采样/resample_lab.py) 的 `offline`，SHA `773ef32198f5723e5ee7591990840efcdb30a3fbd42937d3fcf5f18d147839b1`。

完整结果保存这两个引用和环境。旧源、旧镜像与旧数据未改，不重跑旧218 basis、44积分或两seed应用。新代码没有活动code-sync镜像，正文不复制可运行源码；[测试](test_db2_lab.py)与[图源](plot_db2.py)分别随真源保存。旧模块加载时暂设 `sys.dont_write_bytecode=True`，读取旧源也不应创建/刷新其缓存；复现命令仍统一用 `-B`。

### 相位、边界、坐标与单位

分析是相关 $A[m]=\sum_{n=0}^3h_nx[2m+n]$、D用g。旧函数是full卷积，所以传入反序tap，抽取奇相位。periodic先续原数组前三点，再从该抽取输出序号1保留N/2项（对应卷积坐标 $2m+3$）；zero full不续点、不裁抽取，得到m=−1..N/2−1。合成插零数组长 `2M−1`，分别与h/g完整卷积再相加。

- periodic的合成坐标0..N+1按modN折叠，得到N点。
- zero full合成保存全部N+4点，原点标签−2，取Python切片 `[2:2+N]`。四个区间外位置也保存，不靠隐藏尾部制造成功。
- zero dropped故意删除zero full每支首项，系数改为m=0..N/2−1；合成坐标0..N+1，裁 `[0:N]`，预测只损伤前两点。

“坐标已对齐”不消除因果等待：一个内部相关输出需收到 $x[2m+3]$，即首点后3个采样间隔。这里未实现实时流/flush状态机，不把有限数组的截取冒充流式deadline验收。

数组/系数单位V，平方和V²；N10输入平方和97V²。如果采用每样保持1/16秒的独立ZOH模型，积分为97/16 V²·s，仍需负载模型才谈J。连续db2的积分系数另有V·√s单位，任意样点数组不是这些系数。cascade的坐标与幅值无量纲，网格加密仍使用 $\Delta\tau\sum|\phi^{(J)}|^2$，不会把更多格子算成更多能量。

## 逐断言的重要性、独立预期与失败

| 重要性 | 独立预期与理由 | 默认容差或失败意义 |
|---|---|---|
| 高：连续存在/正则/正交/完备 | $m_0=((1+z)/2)^2Q$，$\max|Q|=\sqrt3$给 $\gamma=2-\log_2\sqrt3>1$；共同支撑的分布极限，再用5lag连续积分与partition unity得正交；MRA两端极限给ONB | 由非作者核推导及MIT具体段落，不用本程序、cascade图或42basis作证明；本页仅保证 $C^\alpha,\alpha<.207519$，非最佳指数 |
| 高：真实连续双基稳定 | $I+aS$ 的统一界 $1-|a|,1+|a|$ 与几何逆；对所有尺度同界；$a=.5$平方界[.25,2.25] | 非作者独核全尺度论证、dual内积与非紧支撑反证；$a=1$交替输入输出平方范数2/M击穿下界 |
| 高：长滤波PR/归一 | 对任意声明偶N，periodic $E^*E=I$；zero full为(N+2)×N等距嵌入。独立矩阵的每列应与源码一致 | 当前42个basis的最大RE−I与E*E−I应<2e−12；失败指向反序、phase、保留m、折叠/crop；不能拿固定N外推全部长度 |
| 高：边界失效 | 删m=−1后 $E_{keep}^*E_{keep}=I-vv^*$，$v=(\sqrt3/2,-1/2,0,...)$。输入v的保留系数为0；固定输入SSE=$(\sqrt3/2-3/2)^2\approx.401923788646684$ | 独立解析推导；默认重建与解析预测的最大样点差<2e−12、SSE差<2e−12；若只看均值或内部点会漏这个不可辨识方向 |
| 高：周期双基逆 | 圆周 $S^M=I$ 必须除 $1-(-a)^M$；M2/a.5遗漏分母给.75I。全保留恢复但系数平方和一般≠输入平方和 | 默认basis重建<2e−12；独立显式矩阵/几何和核全部q和恢复，非拿作者unmix自证 |
| 中：有限cascade显示 | 第一层4格为√2h；每层格数 $3\cdot2^J-2$、积分1、Δτ加权范数1、整数移相关0 | 默认绝对2e−12；曲线只示意有限迭代，检查归一/索引不认证连续存在，也无点值一致收敛承诺 |
| 中：改输入与接口 | 合法负a、零a、高幅数组、N改成非2幂、不同J与显示网格；非法类型/奇长/重复预算拒绝 | 实际改卡和非法CLI另核，有限覆盖不充所有浮点输入的形式验证；不增加装饰性扫参或Monte Carlo |

实现守卫按原幅值 $s=\max(1,\max|x|)$ 和逆稳定因子设恢复容差 `2e−11*s/max(1e−10,1−abs(a))`，basis守卫 `2e−10/max(1e−10,1−abs(a))`；这些是运行拒绝阈值，默认独核采用上表更严容差。$|a|\to1$ 的数学逆放大和浮点相消会恶化，没有对全部允许接近1的数声称统一绝对精度。$a=0$ 回到正交，dual紧支撑、Parseval成立，不能把默认.5的差异套给零卡。

本实验没有噪声生成器。正交/双基界决定输入扰动如何传到系数或反演，不能凭更多cascade格子声称SNR变好；去噪实测仍复用07/实践15的独立真值合同。

## 输入预算、环境和实际命令

有限输入要求偶N6..64，原样点有限且绝对值≤1e6；内部系数不套原幅值预算。basis长度为4..64的不同偶数，最多12项；fs有限且0<fs≤1e6；实数 $|a|<1$；cascade为1..12不重复整数，最多5项；显示分母整数16..256、dual末shift整数1..16；失稳M为2..256不重复偶数，最多8项。bool不当数值/计数。输出目录必须尚不存在，失败退出2且不建立结果目录。这是有限实验预算，不是小波理论定义域。

实际环境为既有Python3.14.7、NumPy2.5.3、macOS27.0.1 arm64，未安装依赖。共享runner只有两槽，本次各用一槽，强制OMP/OpenBLAS/MKL等线程1，限时180s；默认数值0.0241324s，远低于5分钟。`results.json`保留各线程环境。

当时执行的正式数值命令如下（首条确实未带-B；后续模块加载已加禁止缓存保护）：

```bash
python3 /private/tmp/wwl-next-context/run_local.py --timeout 180 -- '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' '/private/tmp/wwl-next-182-final/信号与系统/80-实践/16-db2连续与长边界/db2_lab.py' --inputs '/private/tmp/wwl-next-182-final/信号与系统/80-实践/16-db2连续与长边界/fixed-inputs.json' --vault-root '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL' --out '/private/tmp/wwl-next-182-final/信号与系统/80-实践/16-db2连续与长边界/results' > '/private/tmp/wwl-next-182-final/信号与系统/80-实践/16-db2连续与长边界/author-run.txt' 2>&1
```

以下两条从本实验候选目录执行。测试命令首次记为`author-tests.txt`；测试把旧函数存成class属性时被Python自动绑定，多传self，7项中2项报harness错误，**不是正式数值失败**。改为`staticmethod`后，同命令改日志为`author-tests-final.txt`，7项通过；加旧源缓存保护后再次复用该最终命令，仍7项通过（0.018s），默认42basis结果未重跑。

```bash
python3 /private/tmp/wwl-next-context/run_local.py --timeout 60 -- '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B -m unittest -v test_db2_lab.py > author-tests-final.txt 2>&1
'/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B plot_db2.py --results results/results.json --out results
```

发布后从本实验目录可用同一已准备环境复现（输出换新目录）：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B db2_lab.py --inputs fixed-inputs.json --vault-root ../../.. --out results-rebuilt
python -B plot_db2.py --results results-rebuilt/results.json --out results-rebuilt
```

这里`../../..`是WWL库根。直接命令不自动取得协调槽，多任务环境仍使用共享runner；换机须准备NumPy，未声称已跨机器运行。数值代码和图源参数名分别是`--out`，不杜撰`--output`。

## 实际输出与独立验证

- [results.json](results/results.json)保存固定输入所有子带、完整合成区间、每样点恢复、边界null例、42basis指标、周期双基q、a=1失稳端点、有限cascade显示数据、实际引用SHA与环境。
- [samples.csv](results/samples.csv)逐个保存N10原时间/原V及四方案恢复；[author-run.txt](author-run.txt)保存真实调用结果。
- [author-tests.txt](author-tests.txt)保留首次harness错误，[author-tests-final.txt](author-tests-final.txt)是最终7项通过。测试含12个任意full系数脉冲的独立支撑期望、解析null、M2周期逆/错分母、a1有限端点、非法bool和合法1e6幅值/a0。
- [functions.svg](results/functions.svg)、[boundaries.svg](results/boundaries.svg)由[plot_db2.py](plot_db2.py)只读保存JSON生成。函数图dual显示窗口不是完整支撑；精确ψ尾范数界约.00225527，不含有限cascade误差。残差图直接画保存浮点误差，不设零floor。

默认periodic/fullzero/双基最大basis RE−I均≤4.4409e−16；前两者最大E*E−I≤3.3307e−16。固定输入前两种系数平方和均96.99999999999997V²，双基102.6436322151508V²，三者重建SSE在1.13e−29V²以内；dropped误差.401923788646684V²符合解析预期。单位null输入在dropped中变成数值零，而完整zero恢复；a1的M8/32/128输出平方范数分别.25/.0625/.015625，圆周交替输入输出精确零。

非作者先建Q(√3)精确oracle，核因式分解、归一/half-sums、自相关和连续二阶矩；随后不用作者实现或旧offline作答案，以显式有限矩阵核默认JSON/CSV全部数组、176个新分析/合成列（包括zero_full任意N+2系数的transpose）。真实CLI变式N14/fs8000、负a−.375、basis4/12/22、J1/5/9、显示分母96/dual末shift3，以及N6全零/a0，均通过；10张非法卡退出2且不建输出。连续正文一般证明、七题答案另逐段核对，未把这些有限列当连续定理。最终两正式SVG已由非作者CairoSVG渲染并实际查看：ASCII上标无缺字、两种边界分行SSE准确，坐标/单位/图例/显示范围清晰；从保存JSON重生两SVG字节一致。43wiki目标/标题（含五页返回）与16relative路径、AST/XML、当前五页patch apply --check均通过。负a/a0图只作控制流/XML，不声称这些变式像素已看。原生Obsidian仍未验证。

## 真实数据的外部验证接口

本包未连接设备、未采集真人/真实传感器、未验实时deadline或原生Obsidian。迁移输入至少保存：校准V和参考负载、fs与实际时间戳/缺样、原N与有序样点、tap/相关相位、边界mode和起止/flush、每个子带m及合成原点/crop。连续系数还须声明从样值近似积分的带宽/误差假设；不能直接把样点当正交尺度系数。

受控验证可依次输入已知幅值常量、斜坡、单脉冲与端点方向v，按实际量化/噪声预算预设最大重建误差；完整系数先检PR，再单独阈值并用独立参考检查全域和局部误差。periodic真实尾首不连续会产生额外边缘响应，但完整系数PR仍可成立；把periodic分析与zero合成混用、漏m或错crop则应出现可预测恢复错误。超过预算先查单位、时标、边界及数据丢失，再讨论小波平滑性；图形漂亮不认证传感器保真。
