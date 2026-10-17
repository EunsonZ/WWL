---
domain: 电子电路
type: experiment
stage: 5
aliases:
  - LC启动与边沿频综的有限联合接收机
sources:
  - "[[电子电路/46-电磁射频与高速/10-射频振荡与频率综合]]"
prerequisites:
  - "[[电子电路/80-实践/52-LNA与LO换向器件/README]]"
  - "[[电子电路/42-转换器与采样时钟/07-抖动相噪与时钟环]]"
---
# 先让LO振起来，再检查同一接收机能否过规格

[[电子电路/46-电磁射频与高速/10-射频振荡与频率综合|10主解释]]给从负差分电导/非线性稳幅，到PFD电荷泵、双噪声相位预算、同RX功率/噪声/三阶/量程的完整推导及六题答案。先做[无答案题纸](QUESTIONS.md)，再回主文。本包没有把可执行的教学模型命名成PDK/PCB或真实接收机签核。

## 三层实际对象，各自的真源

1. **实际器件网表**：[oscillator/](oscillator/README.md)保存五条ngspice47交叉耦合NMOS LC瞬态、真实OP与有限关键窗口。来自官方source的本机构建版本/架构/hash、卡、命令与失败检测可查，无runtime或full重复波形入包。它实际给启动/有限稳幅/调C与步长证据，不给随机相噪。
2. **混合动态与低偏移相位模型**：[synth_rx.py](synth_rx.py)与[spec.json](spec.json)定义整数N、两锁存PFD/理想CP/串联RC、有限VCO调谐与边沿事件积分，以及锁定平均双源NT/S。Kv20MHz/V是独立声明的有限调谐模块，主文给正C(u)构造；没有从固定25pF的99.23MHz瞬态冒取该斜率。无PDK提取、真实复位延迟/死区/电流源顺从与采样相噪传递认证。
3. **同一有限RX模块链**：真实旧CG的Q/三节点/电荷/两RF带噪声，通过显式输入1kΩ/输出差分50Ω单向缓冲后接09桥的基波降阶转换及独立等效热源。IF/缓冲/驱动/控制的功耗与噪声卡、平坦立方失真卡、高偏移输出LO谱卡均声明，不能说两个旧MOS电路已经实际级联。

只读复用[旧device_lab.py](../52-LNA与LO换向器件/device_lab.py)的point/lna_case/mixer_limit，以及其原[amp_lab.py](../14-偏置与基本放大/amp_lab.py)、[active_match.py](../51-有源稳定与噪声匹配/active_match.py)合同。三真源SHA在[结果](results/results.json)；导入暂禁bytecode并finally恢复，不改旧源/旧镜像、不重旧成熟数值套件。源码直接链接为真源，本包没有另一个活动code-sync程序镜像。

## 固定输入、单位与裁决

[spec.json](spec.json)的schema为synth-rx-v1。电压V、电流A、RΩ、CF、时间s、普通频率Hz；Kv字段是Hz/V，进入相位环才乘2π，Kφ=Ip/(2π)为A/rad。相位谱是**单边rad²/Hz**，不是SSB dBc/Hz。时域q以分频后周期计，φout=2πNq；所有事件保未包裹q，不用模相位隐藏累计误差。

PFD参考/反馈上升沿置各自锁存位，两位同高瞬时共同reset，电流±100µA/0。数值同沿判定1fs，精确数学同时的沿共同消费；这允许单段相位约1e−8分频周期的裁决误差，不是物理anti-backlash/死区。初态PFD0，下一参考沿为1/fref；初始反馈分频相位由卡给。三初态(.89V,.02cycle)、(.2,.3)、(1.6,.7)目标100MHz；第四相同N10/参考12MHz目标120MHz，不可达82..118MHz调谐范围。

R=1/2/8kΩ、C10nF，u=clip(z+R·i,0,1.8)。各i恒定事件段用解析电荷/相位积分，比较下一参考沿、反馈整数沿、调谐夹限边界与终点。z是电容状态，可以在理想模型中wind-up；调谐端始终限幅，z超1.8不是声称实物CP可以无限提供顺从电压。运行1ms；最后20参考周期的参考沿wrapped误差<.001cycle，周期平均输出频率误差<1kHz为有限锁定验收，不检查瞬时窄脉冲频率一直近目标。

平均NT/S只在已锁、不削顶、f≪fref下使用。三R的IpR=.1/.2/.8V，z锁定.9V有余量；R10k会在小脉冲也夹限，预检拒绝将其继续称为未限幅连续环。积分限制100Hz..1MHz≤fref/10，log变量积分保df。三源标签不等于三种独立物理器件，卡只给参考/VCO两个独立等效相位源，真实CP/R/divider噪声仍需另交端口。

RX同RF希望110MHz/镜像90MHz、LO100MHz、阻塞130/150MHz各−35dBm，希望−80dBm，带宽100kHz。温度300.15K、KB采用现SI1.380649e−23。前置匹配同温衰减L=1/2/4；缓冲Gb1/Fb2/输入1k/输出差分50Ω/功耗1mW。IF GI100/FI5/功耗2mW；LO再生.5mW、PFD/CP/分频1mW为声明预算，不从理想栅端零DC推零能量。LC的3.6mW来自本机SPICE有限观察，不是仪器实测；与CG实际Q1.8mW共同入有限预算，合计9.900000mW。

基波频移模型只保指定希望/镜像RF噪声带，未定义为物理无损预选；09的全白高odd谱反例仍成立。其确定性失真测试另声明平坦无记忆LNA立方卡，IIP3=1mW；G1来自旧器件中心频率，a3=−2sqrt(G1)/(3PIIP3)单位W⁻¹。IF前实信号用√W功率幅，平均x²为W；输入整周期16384点/fs1.28GHz，复投影先joint−blocker-only再取模。未将此a3冒称MOS提取IP3，未把相干IM3当热噪声合到NF。 峰值在理想2cos乘法后、任何低通/信道选择之前观察，声明IF增益对所有保留和/差频平坦，包括210/230/250MHz及最高550MHz（低于640MHz Nyquist）；不是实际带限10MHz IF/ADC峰值。若增加带限滤波，须重新计算该观测点与预算。

远偏移倒易混频**不调用连续PLL传递**：它用独立声明的输出LO谱，1MHz外Sout=scale·Sv，scale1/10；这两个卡低偏移完全相同。实IF10MHz的130MHz阻塞看20/40MHz偏移，150看40/60MHz，四项分别以Sφ/2乘PB·G·B/L，窄带内近似常谱。没有只取最近一侧，也未认证全方波高odd LO相噪、周期相关、实际采样PLL带外谱或离散杂散。

## 重要性落实到断言、容差与失败

| 重要性与原因 | 固定断言/不同路线预期 | 失败与容差 |
|---|---|---|
| 高：差分端口与启动 | Ga=(go−gm)/2而非−gm；每侧Rp近400Ω，差分正损耗1.25mS，有源约−3.178mS | 半电路/功率共轭与实际OP独核。Rp近似不是全极点证书；规范图每侧与差分C/L不能混 |
| 高：真实稳幅来源 | 2mA/1mV种子实际约99.231840MHz、峰.99387455V、3.6mW；1µA种子衰减；M1大半周期离开原OP饱和区 | 每case完成2µs，无abort；名义晚窗两半峰差<1e−6V，实际10→5ps频差<20ppm、峰差<2ppm。未从线性条件推有限幅 |
| 高：零初态与浮点 | 精确对称解不自行离开；实际零显式种子仍可由舍入激发 | 保存真实启动而非改写预期；不由此声称实际噪声/启动概率 |
| 高：事件积分/状态 | 12条全段电荷Δz=iΔt/C与clip-affine相位积分、边沿/锁存顺序/参考/反馈整数、全trace身份 | 独立段积分/漏沿核；电荷误差<3e−12V，分频相位<3e−8cycle（含1fs同沿裁决）。最后20期判据固定；只证所给初态/时窗 |
| 高：局部环与双源谱 | R2k的a4e5/b2e10、64.150kHz/82.929°；三R参考/VCO方差各自积分 | 不同状态空间resolvent/Hz分段积分核，积分相对2e−8、绝对1e−18rad²；不把超fref或削顶小脉冲传递算作同模型 |
| 高：器件到RX参考面 | 旧CG真实终端G1≈3.95001125/F1≈1.90767262，经明确匹配缓冲接源差分50Ω桥；两RF带各自PSD | 自写3节点KCL核（不import增量核心/旧源作答案）；G/F相对1e−8、绝对PSD1e−30W/Hz。直接串不相容旧端口即失败 |
| 高：三次复幅与损耗 | 130/150MHz产生110MHzIM3；L1/2/4的C/IM3约25/31.021/37.041dB | signed-frequency多项式卷积独核wanted/blocker/joint，复幅绝对3e−16√W；IM3按1/L³，不以幅相减代复差 |
| 高：带外谱/联合失败 | 四偏移RM名义3.575606e−14W；同带内抖动的far×10使L4 SNR24.924→23.608dB | 带外PSD独立输入，常谱窄带近似；不从小抖动推出低RM。NF/gain/量程/IM3/热+RM SNR/功耗/有限捕获一起判 |
| 中：有限接口和图 | 数值guard、已有目录保护、源绑定、必要行为测试；三个SVG/PNG只读保存数据 | 非有限/bool/超工作量/无锁定余量须明确拒绝；图列/轴/裁剪/中文另目视，源/图通过不冒native或真人 |

作者独立有限检查[verify_results.py](verify_results.py)不import synth_rx/旧模块，另用3×3节点、精确多项式卷积、clipped-ramp原函数、二状态resolvent+50001对数网格梯形积分；[verification.json](verification.json)实际PASS。14组有限数值与208776段中，最大电荷恒等误差1.46e−15V、最大相位段残差9.96e−9cycle。它是作者自核；非作者另用独立KCL、Hz Gauss–Legendre、signed-frequency卷积及全事件certificate核了同版，不把作者脚本当真值。

## 实际命令、有限预算与复建

作者实际Python3.12.11、NumPy2.5.4、SciPy1.18.1，macOS arm64；ngspice47版本与本机构建hash见[environment.json](oscillator/environment.json)。没有更改系统依赖、启动外部服务、远端GPU或蒙特卡洛。正式数值共享两槽runner取一、强制1线程/禁bytecode，核心3.1196s、exit0；[run-result.json](run-result.json)保完整argv/stdout/stderr。五SPICE各不足2s，原始命令和耗时按case可查。

从本实验目录执行，**核心输出目录必须不存在**，含普通目录/文件/坏symlink；数值/JSON序列化先完成再建目录，非法exit2不建输出；不声称磁盘写入故障能事务回滚全部多文件。

    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /private/tmp/wwl-next-184-env/python-env/bin/python -B synth_rx.py --input spec.json --vault-root /实际WWL根 --out /private/tmp/synth-rx54-rebuilt
    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 120 -- /private/tmp/wwl-next-184-env/python-env/bin/python -B verify_results.py --results /private/tmp/synth-rx54-rebuilt/results.json --out /private/tmp/synth-rx54-verification.json
    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 60 -- /private/tmp/wwl-next-184-env/python-env/bin/python -B -m unittest -v test_synth_rx.py

正式包已实际执行这三类命令：核心真实绝对命令在run-result，独立作者校核输出在verification，当前6必要行为回归0.003s/exit0见[tests-run.txt](tests-run.txt)。上述可复制命令中的“实际WWL根”须替换，并选新的输出/校核文件；共享runner是本机协作工具，别的机器可用其Python/SciPy直接执行同argv并自行限线程/时间。核心导入旧相对合同必须给完整vault-root，不要把这几个文件孤立复制后期待旧源自动存在。

预算：N整数1..100，参考100k..100MHz，T10µs..3ms且每trace≥40参考周期，最多6R×8初态；由最大VCO频率/参考率/T先估全组事件数≤500000，每trace另≤100000，超限在分配/长循环前拒绝。R100..100kΩ但还须锁定IpR有严格调谐余量；固定该卡的参考×N必须等RX100MHz。噪声积分域限100Hz..1MHz并≤fref/10；其余范围是教学数值预算，不是元件额定。固定RF频率、缓冲/温度/端口与模型标签会预检一致；改schema外的真实滤波/CP/VCO或RF结构应另改模型，不能仅换描述字符串声称已运行另一电路。

核心现实现允许有限R/初态/噪声/损耗等变卡，其他固定结构按validate检查；绘图是**当前固定卡布局**，图中固定端口/标题/预算提示不自动适配任意改卡。改变卡后须重建分析并核图label；本文三图只对应正式spec，不把漂亮图片当新变卡结果。

## 正式原始输出怎样读

[results/results.json](results/results.json)保存全部固定输入/当前源SHA、3套谱401频点/独立积分面积、12混合轨迹摘要、旧源SHA/器件输出与RX噪声/3损耗复幅/2带外谱/18联合预算。全部数有限，复量以[实,虚]表示。每条trace在results/raw/*.json.gz，完整未抽点，列为[t秒,z伏,未包裹分频周期,PFD电流状态,event]，保行数及解压字节SHA；[rx-waveform.json.gz](results/raw/rx-waveform.json.gz)保同一16384点应力波形[t_s,input_joint_sqrtW,output_joint_sqrtW]。JSON不是仿造随机测量，所有输入可追。

[oscillator/README.md](oscillator/README.md)定义SPICE的正式有限白名单：完整late1..2µs非均匀时间/差分/共模/电源流（可复算频率/峰/功率），startup0..200ns逐实际行，以及末完整周期全部节点/支流。0.2..1µs不在紧凑波形里，不充全时窗可复建；summary有原full派生100ns幅度箱，原full SHA与列/窗口映射在每case interface。图的启动只画正式0..200ns，晚期指标另列，不跨缺失窗补线。

summary的20周期工作区占比与device-cycle.gz单周期复算占比时窗不同，不能要求逐bit一样；前者由原full独立处理保留，后者可从正式单周期自行核截止/三极/饱和。低尾流无稳态周期不强报频率。纯线宽/确定性FFT没有被收作相噪证据。

原始SPICE源/生成/运行脚本在执行后仅作输入/路径参数化；不凭AST声称已跑过复建后的新模拟。实际成功deck/argv始终保留，隔离复制后可重生并运行；不要在原证据目录直接运行生成器覆盖证据。ngspice有时exit0却analysis aborted，各case还核真实终时/日志，不能以CLI成功代完整波形。

## 图与可变条件的入口

[plot_synth.py](plot_synth.py)只读保存JSON/gzip，写oscillator/pll/receiver三个SVG；[preview_svg.py](preview_svg.py)是可选本地resvg-py0.5.0+PingFang显示适配，已输出三个1600px PNG并实际目视。图源SVG均有title/desc；不是AI生成电路图。新图重建另选目录，绘图会覆盖同名图，**不适用核心的拒绝覆盖合同**：

    python3 -B plot_synth.py --root /本实验绝对路径 --out /private/tmp/synth-rx54-plots
    /private/tmp/wwl-next-172-analytics/render-env/bin/python -B preview_svg.py --results /private/tmp/synth-rx54-plots

第二条是作者已存在隔离显示环境，并非要求读者有该绝对路径；只有本地安装resvg_py及字体时才用自己的Python改路径，SVG本身为阅读底座。核心数值不依赖该显示包。三个实际PNG及SVG留正式results，客户端/真人层不由图片替代。

预测后改条件：R2k→10k应被锁定脉冲余量预检拒绝；第四初态initials[3].reference_Hz=12MHz保持N10，已实际有限运行后明确不可锁（不改噪声预算的标称参考字段）；只改带外谱scale1→10不改变100Hz..1MHz抖动却使RM×10；L1→4使C/IM3+12.041dB同时NF+6.021dB。要复验器件拓扑就按oscillator卡在新副本真实跑，别把改Python的Kv说成改了变容器件。

## 真正未验的高重要性接口

| 层 | 必须给的具体输入 | 观察/失败与证据 |
|---|---|---|
| 真实VCO/PDK | 许可模型版本、C–V/Kv/振幅耦合、所有端压/尾源顺从、tank Q/SRF、版图/封装/PVT、实际负载/驱动能量 | 启动与稳幅、频率范围/余量、真实功耗；漂移/不启动/过压回具体工作区，不从MOS1模拟推工艺良率 |
| 随机相噪 | 经验证周期轨道及逐源热/1f/相关谱、相位响应/ISF或PSS/周期噪声、供电/AM–PM | 保实际输出PSD/单边/载频/积分范围/相噪仪底噪与杂散；确定性FFT、静态.noise、总RMS互不替代 |
| 真实PLL | PFD reset/deadzone/anti-backlash、CP源漏匹配/输出阻抗/顺从、真实RC寄生热源、分频最大速率/延迟、VCO调谐卡、采样传递 | 保存全初态/频差/相位/饱和/锁定窗口，核捕获与带外谱；不同延迟/滤波拓扑不能沿用本二阶传递 |
| 全RX/PCB/仪器 | 真实复端口/源调谐、balun/缓冲损耗与热源、全RF噪声带/谐波终端、两音电平/间距/相位、ADC前量程、校准去嵌/原始数据/不确定度 | 核同一NF/增益/压缩/阻塞/倒易混频/功耗，保失败卡；本包声明模块不是已接通的硬件链 |
| 阅读与迁移 | 正确WWL版本/真实Obsidian目标、独立读者改条件的过程 | 新10/54可发现性留#128接口；静态/像素/模型独核不冒native客户端或真人学习效果 |

原#186要求的有限有源端口/代表器件/启动稳幅/频综捕获/同RX综合由08/51、09/52和本10/54成链；整项是否关闭由fresh原范围与独立验收、实际发布确认共同判定，不把本机可跑模型剩作“外部设备”。上述真实未验层不改写成已验，也不凭它们无限加入所有RFIC研究分支。
