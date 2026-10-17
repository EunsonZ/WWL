---
domain: 电子电路
type: experiment
stage: 5
aliases:
  - 共栅MOS与四管换向桥有限实验
sources:
  - "[[电子电路/46-电磁射频与高速/09-LNA与混频器件设计]]"
prerequisites:
  - "[[电子电路/80-实践/14-偏置与基本放大/README]]"
  - "[[电子电路/80-实践/51-有源稳定与噪声匹配/README]]"
---
# 从Q点到共栅前端，再看真实LO换向

[[电子电路/46-电磁射频与高速/09-LNA与混频器件设计|09主解释]]给完整端口、推导、反例与七题答案。本页两电路独立定义，未连接成同一接收机；单端LNA与差分桥不能直接乘GT/Friis。教学MOS1参数非PDK/实测，确定性MOS瞬态不认证周期噪声、PSS或RF硬件。

## 真源、模型与口径

[fixed-inputs.json](fixed-inputs.json)是固定SI输入。新规范源[device_lab.py](device_lab.py)使用标准库，计算3个重新偏置的Rs×4频率=12行CG节点/噪声/端口结果、DC收支、固定VG迁移与明确理想换向噪声模型；[test_device_lab.py](test_device_lab.py)是7项相关回归，[plot_devices.py](plot_devices.py)只读保存JSON画图。新源无另一个活动code-sync镜像，正文不复制程序。承重来源边界见[SOURCE-NOTES.md](SOURCE-NOTES.md)。

只读复用原[amp_lab.py](../14-偏置与基本放大/amp_lab.py)的mos_bias，以及已发布[active_match.py](../51-有源稳定与噪声匹配/active_match.py)的源/负载闭合和噪声参数。实际真源SHA在[analytical.json](results/analytical.json)中；导入暂设dont_write_bytecode且finally恢复，独立命令也-B，不更新旧缓存/源码/镜像，不重旧套件。这里复用函数不充物理正确性的独立证明。

CG体随源、gate理想AC地；VDD1.8V、vb.1V、ID目标1mA、RD800Ω、RL1kΩ经Cout1nF隔直，Rs25/50/100Ω各重新求VG，并非固定VG。KP.02、W/L10u/1u、VT.5、λ.02；TEMP=TNOM27C=300.15K，TOX20nm保Meyer：内建Cgs11.5104793323fF，外加.5pF，两者相加。G-D外.05pF、D-S外.1pF，实际@cgd/@cgb0。γ=2/3，三源同温独立单边白PSD；读出RL noisy=0，DUT NF含Rs源、沟道、RD。真实负载热源/栅噪声/衬底/1f不由此验证。

桥是四个真实Level1 NMOS，KP.002、W/L100u/1u、VT.5、λ/GAMMA0、body0、TOX20nm；RF差分Rs50Ω各半、VCM.6V，RL1k、每个输出RB1M回VCM，有效差分负载999.500249875Ω。互补LO0/1.8V、100MHz、50ps边沿；实际Meyer和动态共模保留。on-Ron50/7Ω与2/π是名义VCM处的无电荷/常Ron极限，不是每时刻的实际器件常数。

RF希望110MHz/image90MHz各1mV峰值；weakLO高.8V；large_signal两组只有110MHz .1/.4V，不冒阻塞。真正阻塞是希望110MHz1mV与130MHz.4V共同/强音单独。保DC、10/30/50MHz复投影，取500ns..1μs五个IF周期；无假造均匀样点。输出RB只锚定返回，不钳住瞬时共模：名义baseline在该窗约.3960..7882V、均值.599659V。

## 重要性、独立预期与失败

| 重要性 | 具体断言与独立预期 | 容差、失败意义 |
|---|---|---|
| 高：Q/端口/功率 | Rs50有VS.15、VD1、VG.749160686218V；gm.0201692835768S/go19.6656833825μS；VDD1.8mW等于RD/Rs/MOS/源偏置吸收之和 | 独立标量负载线/节点与区域核；默认SPICE电压/电流绝对误差分别≤2e−8V、2e−8A，解析自身收支≤2e−15W。固定VG换Rs不能沿旧Q |
| 高：复AC与实际功率 | 总Cgs=.511510479332pF；110MHz vo/e≈4.44109069−j.16361451，GT3.9500112497而非|Av|² | 三节点与不同incident-wave/Y路线独核；SPICE复增益≤2e−7V/V、Zin≤2e−5Ω。漏Meyer/体连接/Cout负载或用峰/RMS混算即失败 |
| 高：噪声与波变换 | 110MHz三PSD约1.636892e−17/1.080320e−17/4.054421e−18V²/Hz，F1.9076726168 | 逐源右端/独立协方差外积核，不import作者答案；与ngspice47绝对PSD相对≤1e−6，含已知kB常量差3.48e−7，F≤2e−7。ASD须先平方再加，不能盲套γ到所有MOS |
| 高：稳定层 | 三节点自然三次多项式正系数且p1p2>p0p3，固定所述连接/正R,C严格稳定 | 一般解析证明独核，12行Routh ratio只核实现，不代任意被动终端/真实封装的宽带认证 |
| 高：实际换向 | 名义2Ron=14.285714Ω、Re999.50025Ω、IF/e=.598148164193，RL功率转换.0715562453 | 预先固定小信号3%幅容差；实际wanted/image≈.59814086，未拟合参数。各case必须到1μs且无abort，不以exit0充完成 |
| 高：镜像/谱 | sgncos的复系数qn=2sin(nπ/2)/(nπ)，希望/image同IF；WSS输入正交频率、输出LO周期平均PSD才可求模平方和 | 两带理想SSB F2.705073712、全白RF3.172474812，包括2Ron/RB热源。不同谱不冒实际无损预选器；周期相关输入另有交叉项 |
| 高：真阻塞 | 强130MHz使30MHz约.239V，而希望10MHz约.6mV；比较希望增量先复数joint−blocker-only再取模 | 同窗同相位及步长核；有限残余不是已定位IM3，单大音不是阻塞。下游量程未由本例认证 |
| 中：有限数值/拒绝 | 默认12解析+3DC与实际3Rs×4f，8主桥、同参数5ps三例 | 7回归/合法改卡/非法接口分验。理论域比脚本预算大，不靠扩大扫参或MC充深度 |
| 中：图和有限证据 | 图由同卡解析/真实摘要产生；关键原非均匀轨迹列值保真 | SVG字节重生/像素另验；14.43MB交付只保关键投影全窗，其余仅1IF不能充全窗复算 |

source kB用现SI1.380649e−23；ngspice47 const.h用1.38064852e−23。NF同温比抵消，绝对PSD约3.48e−7差有明确来源。实际εox=3.9·8.854214871e−12与MOS1源码一致，不从测得cgs拟合。源在AC设1只是线性基激励，保存Pav1μW归一不认证该RF幅度无失真。

## 固定输入、环境与真命令

解析预算：严格schema1；标量finite且拒bool；正电阻/电容、T100..500K、f1..1e10Hz，W/L/tox1nm..1mm，ID1μA..10mA，数组1..16且去重；必须保持饱和。nominal LO_low<Vcm+VT<LO_high；这是零信号on/off条件，有限波形仍需真实端压检查。odd列表为从1开始、递增不重复正奇整数≤99。测试自动优先找当前完整库根，隔离候选可用WWL_RF_VAULT显式指定真库；SPICE生成器为本固定卡锁定若干值（含LO_low=0），不将所有解析合法变卡称为已仿真；完整数值范围以validate为准；不把范围当器件额定。输出须不存在，含坏symlink；JSON计算/allow_nan=False序列化在mkdir前，非法exit2不留新目录。

作者标准库环境Python3.14.7/macOS27.0.1 arm64，解析与7回归均通过。共享两槽runner取一、线程1/禁bytecode、单组限180/60s；无蒙特卡洛，无旧44/218等套件。以下是作者实际从本目录执行的命令：

    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 180 -- '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B device_lab.py --input fixed-inputs.json --vault-root '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL' --out results > author-run.txt 2>&1
    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 60 -- '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B -m unittest -v test_device_lab.py > author-tests.txt 2>&1
    '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B plot_devices.py --analysis results/analytical.json --spice spice/reader-evidence/results.json --out results

解析正式运行后只收紧LO low的on/off guard并补拒绝回归，无数值算法漂移；没有为guard重复12/41行计算。真实日志[author-run.txt](author-run.txt)、[author-tests.txt](author-tests.txt)保留。

SPICE由隔离执行lane直接生成/运行，ngspice47 arm64官方source tar版本/二进制hash见[actual-binary.txt](spice/reader-evidence/actual-binary.txt)。实际Python3.12.11/NumPy2.5.4用于波形处理，未改系统环境。各deck实际命令/elapsed/exit保在case的command-result.json，典型wanted案：

    python3 /private/tmp/wwl-next-context/run_local.py --timeout 300 -- /private/tmp/wwl-next-184-env/install/bin/ngspice -b mixer.cir

8主case逐个串行经同一共享槽，单例约.7s；加上三案5ps与LNA均远小于5分钟。原trapezoid发生真实timestep-too-small（进程仍exit0），改用同参数Gear2/maxstep10ps后全部到1μs，再以5ps核三个关键案；不是调器件卡去凑输出。早期错误/浮置共模/325MB全raw过程保临时区，不混作本版本成功，也不随正文入库。

## 正式有限证据与复建

唯一SPICE正式白名单是[reader-evidence/README.md](spice/reader-evidence/README.md)及其整目录，逻辑大小约14.43MB（约13.76MiB）。含同版fixed卡、3案小OP/AC/noise原始输出、11条桥case的deck/log/命令与实际非均匀三列gzip；[interface.json](spice/reader-evidence/interface.json)明确原full.raw SHA、列映射/选取/当前输出hash。

8条关键整窗是wanted/image/weakLO/joint/blockeronly五主case与三条5ps，保500ns..1μs全部点和紧邻左边界原row，不抽稀；可重算24个10/30/50MHz关键复投影。baseline/large_signal两组共3条仅最后1IF周期，供图与局部观察；其原500ns整窗9个投影只复用已核摘要，重建要按deck重跑。原full独核33个投影的事实不等于正式有限文件全部能重算33个。

[analytical.json](results/analytical.json)为解析结果、源SHA/全输入；[SPICE results.json](spice/reader-evidence/results.json)为实际Q、复AC、ASD/F、8主案的同窗投影/CM范围；[5ps结果](spice/reader-evidence/convergence-step5ps/results.json)给同参数差量。[lna.svg](results/lna.svg)、[mixer.svg](results/mixer.svg)由同两份保存数据生成。

不运行新模拟即可独立复算交付整窗（包内summarize.py为compact适配入口；需Python+NumPy）：

    python3 -B spice/reader-evidence/recompute_compact.py --output /private/tmp/rf52-compact-recomputed.json

重跑要先复制本实验到新的临时目录，保原始证据；解析指定真实库根与新输出目录：

    python3 -B device_lab.py --input fixed-inputs.json --vault-root /实际WWL根 --out results-rebuilt
    python3 -B plot_devices.py --analysis results-rebuilt/analytical.json --spice spice/reader-evidence/results.json --out results-rebuilt

只在这份临时副本中运行reader-evidence/generate_lna.py、generate_mixer.py，然后在各新case目录调用ngspice47；这些生成器写自身所在副本，不能直接拿当前证据目录当新输出。完整重建和compact源码入口见reader README。换卡应同时重建分析和SPICE，不能把新输入的图叠到旧SPICE摘要；绘图布局只支持最多4个Rs案，数值预算较宽。

## 实际结果、独核与证据边界

默认解析12行、3DC；作者7回归通过，包括节点/波合同、DC功率、固定VG反例、三态特征多项式直接行列式、换向热源与导入成功/异常不生bytecode。非作者不import本源作答案，自解偏置/三节点、实际incident-wave S、两噪声注入外积和二次式最优参数：默认及3合法变卡共41行通过，三次Routh一般证明单独通过；17非法中15初轮正确、两LO低电平缺陷修后均exit2且不建目录，边界合法1.09V卡通过。旧课实验没有重跑。

独核实际12行SPICE OP/复AC/主要PSD通过；原全波形11案的33个复投影以逐段线性×指数的独立解析积分核，并以二阶导数界解释trapezoid差。正式compact另核11gzip/明文/原full hash、逐行列映射与8整窗24关键复投影，且实际运行compact重算CLI通过。三条短窗不冒全窗复算。

默认wanted/image有限转换率约.598140858/.598140832，small3%PASS；弱LO有限比.000143108不等理想零。true-blocker-only的10MHz残余约5.528μV，joint10约.597051mV；复数相减后的希望增量约.597127mV。5ps时wanted变化约3nV、joint10约86nV，但blocker-only残余5.528→5.644μV，不能把它标成精确物理IM3/PSS。baseline虽差分≈0，共模仍大幅摆动；图保留它，未将均值写成瞬时固定.6V。

修后主文/七答案经独立终读通过，WSS/周期平均PSD与非零GAMMA题条件已收紧。两正式SVG最终Cairo实际像素通过，保存JSON重生逐字节一致；分类轴不叠数值tick、噪声条明示Rs50/110MHz。含共享返回的29wiki/标题/图目标、21relative、9py AST/2SVG XML及四旧页patch当前apply--check通过。reader两生成器在隔离副本实际重建11份deck字节一致（未重模拟），summarize与直接compact入口的重算JSON一致；输出坏symlink/固定SPICE LOlow=0 guard亦已收尾。真实PDK、宽带VNA/PCB、完整周期器件噪声、原生Obsidian和真人未验。

## 外部层与原课程余项

| 重要性 | 具体输入/条件 | 预期、失败与续接 |
|---|---|---|
| 高：真实LNA器件 | 模型/PDK版本与许可、Q/PVT、体连接、端电荷/噪声相关/寄生与RF电平 | 复验gm/输入/功率/噪声、稳定与压缩；失败回节点/模型，不从可运行MOS1推真实工艺准确 |
| 高：实际LO/周期噪声 | 驱动阻抗/能量、边沿/死区/占空、各端谐波阻抗、相容周期噪声源/谱 | 检谐波传递/相关交叉项及SSB/DSB带宽；普通AC/noise或本确定性瞬态不能替代 |
| 高：真实级联与阻塞 | balun/预选器模型和损耗热源、LNA输出到桥的实际差分加载、阻塞谱/相位与下游量程 | 同参考面合预算；端口不相同不得直接乘GT/Friis，强音通过本桥不保证ADC未饱和 |
| 高：VNA/PCB测量 | 校准/去嵌面、偏置/激励/温度、原始复数数据、元件Q/SRF/地寄生、不确定度 | 与08合同接续；有源内部极点、周期噪声、硬件稳定分别验，不把单点/确定性结果推广 |
| 中：客户端/学习 | 正确WWL版本路径/实际显示、真人独立迁移过程 | 模型/像素/结构和真人分层；新09发现性按#128接口，不复用旧页UI观察 |

本实验的LNA代表节点与LO开关/希望镜像端口证据保留；[[电子电路/80-实践/54-振荡频综与接收机/README|54后续完整链]]已交实际有限LC启动/稳幅、PFD/CP捕获和双源积分，并在显式匹配模块层比较同RX的NF/增益/三阶/量程/功耗。原08/09/10有限主线由此接齐，真实全器件级联、周期噪声与硬件仍按明确接口另验。
