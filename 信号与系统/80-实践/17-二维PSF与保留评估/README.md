---
type: practice
domain: signal
stage: 1
aliases:
  - PSF保留数据实验
prerequisites:
  - "[[信号与系统/50-通信与反演/04-二维成像伴随与正则选择]]"
sources:
  - https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf
  - https://numpy.org/doc/stable/reference/routines.fft.html
---

# 二维PSF与保留评估

这个实验让读者亲自区分“实现的A正确”“凸目标已求准”“指定真图误差较小”与“实际仪器可信”。它实际运行一个小型CPU有限模型，不接相机、材料或外部服务。完整解释、推导与六题答案见 [[信号与系统/50-通信与反演/04-二维成像伴随与正则选择|主文04]]；先答 [[信号与系统/80-实践/17-二维PSF与保留评估/QUESTIONS|无答案题纸]]，再读答案。独立核查者曾先保存自己的答案再读教师解，这不是学生盲测或学习效果。

## 固定对象与输入责任

版本 `psf-holdout-v2`：[规格](spec.json)、[开发对象与两次噪声](development.json)、[另一评估对象与两次噪声](evaluation.json)。8×8 row-major像素平均、pitch=.1 mm、灰度U，非对称3×3 PSF原点(1,1)且权重和1；主体zero→2×2平均→留粗行0/1/2，A为12×64。电子Gaussian噪声σ=.02 U在平均/裁剪之后定义。PSF权重已包括像素化，不另乘像素面积。

输入中的固定噪声值是执行权威，生成时以101/202/303/404区分四组，并以 `Random(seed+10007*i).gauss(0,.02)` 产生各坐标；种子不是设备噪声分布或独立性的证据。两个真图及噪声全公开，观测使用同一有限A生成与重建，具有模型匹配优势。不能把公开文件的读取先后描述成作者未见真值或现实泛化。

- `development.json`：一幅块状对象；fit拟合，独立validation噪声做预测评分。
- `evaluation.json`：另一幅含窄条、孤峰、不可见交替末行的对象；参数锁定后test-fit拟合，test-repeat作独立预测评分，truth只算重建指标。
- 13个候选及ε=.001、ρ=.2、停机阈值预先固定。`select`接口不接truth/evaluation，`run_lab.py`将 `selection.json`写入新目录后才读evaluation文件。同分按规格声明顺序。

初次预跑发现显示用的TSVD τ=.5在这个谱下不截任何方向；v2将固定对比改为同一候选网格已有的τ=.8（保5方向），依据A谱展示机制，未按test MSE挑阈值。选择网格及赢家未变。初次运行与修改前记录保留在作者候选过程区，正式实践只保留当前可复建输入和结果，不把旧图冒充另一独立试验。

## 先检查承重断言

重要性为**高**。边界或伴随差一个索引/系数，优化器仍可收敛到错误目标；选择集泄漏则会给虚高评估。以下失败应阻止把结果当成本课的证据，不能只比较终局MSE。

| 断言与原因 | 实际检查/容差 | 失败判据 |
| --- | --- | --- |
| A包含H/B/C及正确边界；核和1不保证有限能量和保持 | 独立Fraction逐源scatter系数，与完整A逐元素精确相等；rank=12/nullity=52；末8列0 | 任一系数/秩/零方向不同 |
| A*是同一前向的Euclidean伴随；漏B*的1/4会改梯度 | 完整scatter与显式Aᵀ比较；内积绝对/相对1e−10，边缘脉冲另精确 | 只有随机内积相近而角脉冲/裁剪不符也失败 |
| 面积度量不能悄悄混入目标 | Wx=.01I、Wy=.04I核4Aᵀ；前向h不再乘面积 | 混用Aᵀ与带权内积，或二次归一化 |
| FFT实现仍是同一有限边界 | 一维显式矩阵/冲激，二维zero补长并crop、periodic核移位；差异<1e−12 | 把循环输出当线性输出或尺度错 |
| 线性重建符合已声明滤波 | oracle用AAt特征分解/正规方程，非实现的A薄SVD；绝对/相对1e−10 | 任一向量、阈值保留或指标不符 |
| TV确实解所声明强凸目标 | 每个实际TV结果完整p/q、目标、gap独立重算；8份证书，浮点gap∈[−1e−10,1e−6] U²；driver另要求r/s≤1e−7 U | 不可行q、gap超限、达到迭代上限未收敛仍参与选择 |
| 参数选择不读取评估真值，且只声称可见预测目标 | 13行评分、分族/总选择、锁文件、独立test重复评分逐项核 | 只报总赢家，或使用test真图重新挑参数 |
| 物理返回不把负寄生或小残差当真材料 | 两组εr>0/Cp≥0同读数、open/ref/sample与比值独立重算 | 混淆空气夹具与零信号open、漏几何/寄生变化 |

独立批量 [batch_oracle.py](batch_oracle.py) **不导入imaging_lab**：精确有理数列举源像素贡献、独立图D、AAt特征系统/正规方程和primal-dual证书；不拿重跑同一ADMM当真值。作者证书核验是另一条数值路线，不代替非作者核查。非作者另从有理显式A、图D及box-dual坐标法独立求selected dev/test，检查两解差在双方强凸gap界内，还独核2×2、4×6边界与前置分配guard；这不是对所有图像或所有solver输入的认证。

[[信号与系统/80-实践/17-二维PSF与保留评估/04-源码与验证|规范源码与行为测试全文镜像]]供连续阅读；canonical Python文件仍是唯一真源。

## 命令与资源

从库根目录执行，计算只需Python3.10+和NumPy；本次实际为Python3.14.7、NumPy2.5.2。8×8矩阵很小，常规不超过5分钟，单进程/BLAS1线程。不要对未经审查的大JSON或矩阵当通用服务。`run_lab`固定8×8/最多16候选，每次TV≤10000步；核心创建dense A前限制每边2–16且偶数，避免不合理分配。

```sh
LAB='信号与系统/80-实践/17-二维PSF与保留评估'
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python3 -B "$LAB/run_lab.py" --spec "$LAB/spec.json" --development "$LAB/development.json" \
  --evaluation "$LAB/evaluation.json" --out /private/tmp/psf-183-rebuild
python3 -B "$LAB/batch_oracle.py" --spec "$LAB/spec.json" --development "$LAB/development.json" \
  --evaluation "$LAB/evaluation.json" --result-dir /private/tmp/psf-183-rebuild \
  --out /private/tmp/psf-183-rebuild/oracle.json
python3 -B "$LAB/test_imaging_lab.py"
python3 -B "$LAB/plot_imaging.py" --lab "$LAB" --out /private/tmp/psf-183-figures
```

`run_lab`拒绝已经存在的out目录，先选新名字；oracle会覆盖指定输出文件，plot会覆盖目标目录中的三个同名SVG，所以复建均选独立目录。图命令的 `--lab`读取该目录的 `results/actual.json`及 `results/selection.json`；以上是从发布原始数组重画。若要画刚才改条件的新结果，复制spec/development/evaluation和新result目录为同一新的lab布局，再将 `--lab`指向该副本，避免图和规格错版。

在本轮协作资源池正式执行时，以上计算通过 `/private/tmp/wwl-next-context/run_local.py --timeout 120 -- <实际解释器> -B <上述脚本和参数>` 自动取得两槽之一并强制线程环境；这是本轮外部资源控制器，不是读者复建依赖。正式结果的完整argv/解释器/线程环境/退出码和stdout/stderr在 [run-result.json](run-result.json)，不把command示例代替实际执行记录。

- [run-result.json](run-result.json)：当前v2正式运行退出0，0.2684 s；输出operator12×64、四重建、两错模型及TV总赢家。
- [tests.stderr](tests.stderr) / [tests.stdout](tests.stdout)：8行为测试实际退出0，unittest记录0.053 s；覆盖角脉冲、FFT/边界、D连接、解析三像素、预测选择与资源/拒绝合同。
- [oracle-result.json](oracle-result.json)：独立批量参照PASS，13候选、8TV证书、精确rank12/nullity52；不是只核最后一张图。
- [results/selection.json](results/selection.json)：全部13拟合/验证分数，最小值TVλ=.001 U；[results/actual.json](results/actual.json)：完整A/D、内积/FFT/pulse/null探针、每个x及p/q/停机历史、真图/预测指标、错模型和物理读出。

正式结果记录输入和canonical `imaging_lab.py`的SHA256及NumPy版本；换版本浮点字节可变，先按上述容差和合同核，不要求跨平台JSON逐字相等。独立核查本次最终CLI的actual/selection与正式逐字相同。旧热反演/旧FFT算法suite没有在本包重跑，直接复用已发布证据。

## 图怎样复建，怎样读

[plot_imaging.py](plot_imaging.py)只读同版固定数组，不调用solver或改变指标，标准库生成 [forward.svg](results/forward.svg)、[reconstruction.svg](results/reconstruction.svg)、[selection.svg](results/selection.svg)。三份PNG是同SVG的实际本地resvg渲染： [前向](results/forward.png)、[重建](results/reconstruction.png)、[选择](results/selection.png)。本轮复用了隔离环境resvg-py0.5.0与macOS PingFang字体，未更改系统依赖；可选 [preview_svg.py](preview_svg.py)把SVG转1600px PNG，数值重建不需要它。它的字体路径是macOS接口，其他平台需换为本机字体：

```sh
python3 -B "$LAB/preview_svg.py" --results /private/tmp/psf-183-figures
```

图已实际查看：文字、坐标、核系数、12×64热图、同视野像素、超界红框与最后一行未读清楚。独立者另核图字段/显示范围及实际PNG。尚未在Obsidian客户端实走，不从本地PNG推断客户端或真人结果。

TV test MSE≈.051345、PSNR≈12.895 dB，低于pinv的MSE≈.076881；但TV的独立repeat预测MSE≈.000732反而高于pinv≈.000600。翻错PSF的MSE≈.049705又略低于正确TV，真实A残差却从.025847增至.102829 U。孤峰1 U被TV压成约.353 U，不可见末行被先验填平。读图时必须同时看这几个不讨巧的结果；它们解释方法的目标和边界。

## 只改一个条件，先写预测

- 把evaluation真图row7改另一非负模式，保留噪声；zero读数完全相同，所有重建/选择不变，只有依赖truth的指标变。再比较periodic时为何不能复用该零方向结论。
- 保留数据，把重建边界换periodic或核旋转180°；正式已有这两组。先指出物理连接改变，再核假定/真实模型残差，不能按更低的一次MSE宣布哪套仪器模型真实。
- 将ε改0：本实现明确拒绝；先用主文三像素裸TV族解释为何不能直接删去强凸依据。若另写裸TV求解器，须自行给存在/唯一或选解政策与新证书。
- 把灰度及σ统一放大s=1000：TVλ也乘1000，ε与岭λ不变。当前规格刻意把灰度/参数限在小有限教学范围，若实际改脚本允许新单位，先重做预算/容差和目标单位；不要只改数组、沿用未经缩放的λ。
- 把10000步降为1：应出现候选未收敛的明确失败，不能照常给“最佳参数”。失败早于新selection文件/评估读取，不可把失败目录当完整运行。

这些改变检验机制，不需追加大规模性能或设备任务。完整六题及答案在主文；题纸不带答案，便于先保存预测。

## 设备/真实数据的下一接口

本实验已经执行有限CPU模型和数值核查；下面才是**未执行的具体应用接口**，不是把能在本机做却没做的事推成外部待验：

| 应用输入 | 必要条件和观察 | 不能据什么过关 |
| --- | --- | --- |
| 真实二维PSF：固定物距/波段/焦点的点源或独立标靶，暗场、平场、曝光与像素pitch/放大率 | 明确读数是平均/积分/计数；保留未归一化增益、位置相关PSF、饱和与边界；用未参与拟合的点/标靶预测 | 把归一化核或一次好看重建当PSF校准 |
| 独立重复原始帧与噪声标定 | 固定对象，查shot/readout/共同漂移、bin发生位置和协方差；禁止把存档帧副本算新观测 | 用σ=.02合成噪声冒认相机噪声 |
| 同轴读出：几何/端边界/接触记录、寄生基线、参考和样品端口读数 | 查参考是否保同一增益与寄生，读数单位pF或Q/V，分开独立与共同误差；新观测是否解除(κ,1)核方向 | 一次残差小或数值网格收敛当介电参数真实 |

没有启动设备、远端GPU或训练神经先验。此有限实验与主文满足原课程规定的等价手算/轻量数值解释层；未知设备的性能、材料真值和总体泛化仍需自己的数据。返回 [[信号与系统/50-通信与反演/02-前向算子反卷积与正则化重建#同一 MAP，后验尺度仍不同|旧课同MAP不同后验]]，勿把本页凸目标的gap当成后验方差。
