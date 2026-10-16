---
type: lab
domain: electronics
course: 模拟集成电路
stage: 4
aliases:
  - OTA双环与噪声预算
sources:
  - https://www.eecis.udel.edu/~vsaxena/courses/ece614/f12/Lecture%20Notes/lec10_ece614.pdf
  - https://ngspice.sourceforge.io/docs/ngspice-manual.pdf
prerequisites:
  - "[[电子电路/26-放大电路/10-OTA噪声摆幅与双环联合规格]]"
---

# 53：同一OTA的噪声、摆幅和联合规格

这里实际运行10节点器件级教学电路：前课11只MOS与CMFB，加两路实际栅RC和两个跨输出/控制节点的桥电容。规范Python与ngspice47分别算同一个有限对象；不是PDK，也不是用一条抽象传递函数假扮完整OTA。完整推导、同数据图和六题答案在 [[电子电路/26-放大电路/10-OTA噪声摆幅与双环联合规格|主文10]]；[[电子电路/80-实践/53-OTA联合规格/QUESTIONS|无答案题纸]]可先答。非作者先保存答案再读新核心，已披露见过预跑PM数字，不冒盲测或真人理解。

## 固定输入和唯一真源

- [spec.json](spec.json)，版本 `ota-joint-v1`，固定10节点顺序/三种步进幅度/15源白噪声合同/五个具名设计角色、四个确定参数角和预算。开发预跑决定教学预算与设计，不是预注册或最优性试验；正式组按同一卡输出所有通过和失败项。
- [joint_ota.py](joint_ota.py)给新增网络KCL/非对角C、解析盖章、全状态/模态/切口、逐源谱、DC与Radau步进、完整SPICE deck。
- [run_joint.py](run_joint.py)消费卡片，重求9配置的Q/所有根/谱/输入共模及摆幅网格/步进，生成并实际启动ngspice，再保存 [results/results.json](results/results.json)。不覆盖已有输出目录。
- MOS电流及端口偏导直接加载原规范 [实践49 ota_model.py](../49-全差分OTA偏置与共模/ota_model.py) 的 `mos` 函数，卡片锁该文件SHA；没有复制旧电流律作为第二真源，也不重新扩写旧偏置课。新deck为原11MOS加明确R/C连接，源仍是原50µA理想参考。
- [test_joint_ota.py](test_joint_ota.py)含6项有关行为；[[电子电路/80-实践/53-OTA联合规格/源码与验证|两份逐字源码镜像]]仅供连续阅读，编辑以Python为准。

状态顺序 `(op,om,s,vb,sense,sc,vm,vc,gp,gm)`，电压V、KCL流出电流A，J/Fu为S，C为F，A/B为s⁻¹。主体27°C，VDD3.3V、Vic1.5V、输出共模参考1.65V；检测R各2MΩ，实际栅R各20kΩ、栅对地500pF，op/om各有Co且各5pF到vc，vc对地Cc。其余节点5pF。原11管W/L/体端、KP100/50µA/V²、阈值+.6/−.7V、λ.04V⁻¹与GAMMA0保留，实际网表逐项列出。

本模型刻意压低MOS内置寄生（沿原49的TOX=1e3等教学设置）；显式电容已经画出的不能再另算一份同名负载。30nF为外部教学控制电容，不是片上面积设计。VDD、Vref、Iref与驱动求和器理想；源的真实启动/基准噪声/动态功耗不在本模型里。

## 高重要性断言：什么结果才算同一个问题

重要性为**高**。Q不成立、漏一条电荷连接、错一个噪声端口或只看差模，都可能产生看似漂亮的错误结论。失败阈值在核对结果前固定；不会为了图更好看排除corner3或饱和步进。

| 承重断言/理由 | 核对与失败判据 |
| --- | --- |
| 同Q点器件区自洽，不从其他例题借gm/ro | 9配置独立ngspice10节点DC差<1µV；逐管KCL/偏导另由非作者网表路线核；任何必要饱和/50mV预算失败如实列出 |
| Cbridge保留两端及非对角，不能继续逐行除C | SPICE10节点各注单位AC流形成完整Z，取Y=−Z⁻¹；J误差限rtol1e−7/atol1e−14S，C限rtol1e−7/atol1e−17F；全10根由所测Y复算；单个端口曲线不足 |
| 对称DM为两个状态，CM其余八个 | 独立二状态解析与完整变换对照；门差/均和输出差/均同时变换；失配重新求Q，禁止用原单状态DM或原零泄漏 |
| 每源从真实端口进入 | 11MOS d→s与4实际R共15源，全部独立单边PSD；4配置×401频点DM/CM逐源对SPICE，rtol1e−5、atol1e−24V²/Hz；总谱必须等15源和 |
| 输入等效按声明ud端口逐频除信号增益 | 与SPICE输入等效PSD及完整AC对照，rtol1e−5；不能用输出RMS/DC增益替代，也不能把平均端口当差分端口 |
| 返回比只代表声明切口 | CM仅去vc→M3/M4 gm增量动作，桥C仍闭；行列式恒等式和完整10根另核，不能称拔整根控制线 |
| 非线性步进不是线性根的手画曲线 | 两个幅度实际ngspice vs Radau，所有10节点在可对齐时刻差<100µV；±.35V夹窄/非饱和照留，不能把更快归一化当保真 |
| 参数卡所说的条件真被执行 | 固定噪声/节点/步幅合同不一致预检拒绝；duration/count用于ODE，duration同时进入SPICE终时；资源域/新输出目录在运行前检查 |

[verify_evidence.py](verify_evidence.py)是作者批量核验器，**不import joint_ota或重跑它当答案**：直接读取SPICE OP/AC/15源PSD、10列注流Z和两组原始瞬态，核有限矩阵、逐源贡献和指标；[verification.json](verification.json)是实际PASS结果，[verify-run.json](verify-run.json)是实际命令/退出码。非作者另外从网表平方差KCL、五点偏导、两端电容、独立Q与PSD求解、BDF和DM解析路线验收，不能把作者验证器冒称那份独核。

## 原始数据与实际结果

[run-result.json](run-result.json)保存当前canonical输入/程序实际命令、线程环境、耗时、退出码与stdout/stderr；正式完整组退出0，约3.823s。原始运行记录的库外路径保留执行时名称，不作为当前复建依赖；按下方相对路径命令执行。真实引擎是从官方源码局部编译的arm64 ngspice47，binary SHA `aad64d99db6966f3a7e3304e3980f8ea295c41bd6b9ebd5ed07d35f927070d6e`，结果JSON保存实际 `-v` 输出与hash；不是厂商预编译或硅测量。

`results/spice/`每个实际进程保留 `input.cir`、`command.json`、`stdout.txt`、`stderr.txt`与原始文本输出，不只保留终局摘要：

- 9个 `*-op/operating.txt`：五种设计角色及四角的完整10电压。
- 四个 `*-ac-noise/`：DM/CM AC；`noise-dm.txt`和`noise-cm.txt`保留15源、总谱与DM输入等效；`integrated-*.txt`另保模拟器自身的积分结果。
- `balanced-Y/`：同一Q向10节点分别注1A小信号AC电流的完整10列；1A是线性传递的单位探针，不是器件实际大信号电流。
- `balanced-step-0.06/`与`balanced-step-0.35/`：两个实际非线性轨迹，原始时间步≤.5µs，`.ic`列出全部10状态。与ODE1µs网格比较属于插值对齐口径，不是每个SPICE原始时刻的最大差。

实际最大OP差约.873nV；Y抽取J最大差约8.24×10⁻¹⁸S、C约2.32×10⁻²³F，最近匹配根差约2.22×10⁻⁵s⁻¹。4组总DM谱与逐源参照的最大相对差小于8.4×10⁻¹³。很小的数字表示所声明教学模型内一致，不能当设备噪声、容差或实际准确度。

两组SPICE首样是5ns，未记录0时刻；比较只取作者网格中t≥5ns的点（即1µs起），不将首样外推为T0。按该口径，±.06/±.35V步进10节点最大差52.44/26.89µV，未超100µV限额。非作者另用BDF解同初态，和Radau最大差约21.93/10.30nV；两种口径不混用。初态由deck `.ic` 与输入条件另核，不因缺T0样本宣称不符合初态。

balanced名义预算全通过；starting失败DM裕度与两种输出噪声；dm_only只失败CM裕度；heavy_output失败CM裕度与平均斜率。四角中corner3在Vic1.35V的余量约20.39mV，仅该项未过50mV预算，仍在饱和。检查字段为五个输入共模点和七个摆幅点，不证明连续区间/任意波形/工艺良率。

[tests-run.json](tests-run.json)保留6行为测试记录，覆盖电荷能量/桥接、旧Q在栅RC下不变、全Jacobian与真实切口、2维DM/15源、非线性小信号极限及固定合同拒绝。小信号极限测试允许50nV绝对误差，符合本Radau `rtol=2e−8`作用于约1.6V节点的数值尺度；不是把元件误差设50nV。开发时过严2nV测试失败、噪声plot选择和JSON序列化失败均保留在作者过程区，未把失败partial目录当成功结果。旧09/49的成熟SPICE组与旧噪声主课没有在本包重跑。

## 自己复建

本复建入口采用Python3.12+、NumPy和SciPy；本次实际Python3.12.11、NumPy2.5.4、SciPy1.18.1。复用现有库外隔离环境与ngspice47，未改系统或主库venv；新机可在自己的局部venv安装所需版本。模拟器官方归档/完整编译选项与源码SHA沿 [实践49环境说明](../49-全差分OTA偏置与共模/data/spice/README.md)复建，不把runtime、tarball或数据库复制进本实践。

从WWL根执行，替换解释器/模拟器绝对路径，选尚不存在的库外输出目录：

```sh
LAB='电子电路/80-实践/53-OTA联合规格'
BASE='电子电路/80-实践/49-全差分OTA偏置与共模/ota_model.py'
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
/absolute/python -B "$LAB/run_joint.py" --spec "$LAB/spec.json" --base "$BASE" \
  --ngspice /absolute/local-prefix/bin/ngspice --out /private/tmp/ota-joint-my-new-run
/absolute/python -B "$LAB/verify_evidence.py" --lab "$LAB" --results /private/tmp/ota-joint-my-new-run \
  --out /private/tmp/ota-joint-my-new-run/verification.json
/absolute/python -B "$LAB/test_joint_ota.py"
/absolute/python -B "$LAB/plot_joint.py" --lab "$LAB" --out /private/tmp/ota-joint-figures
```

省略 `--ngspice`只运行Python有限模型，**不等于**已经有引擎证据，raw核验器此时不能给PASS。driver是固定v1教学工作负载，保留五个具名设计角色与字段结构；可以在给定域内改参数，不能将它当任意网表服务。固定PSD/频带/节点/步幅合同若改动即拒绝，不会只改标签仍静默跑原问题。每设计都校验参数范围，最多6角色/4角、每次最多12个输入共模点和17个摆幅点、输出网格101–4001、时窗.1–5ms；当前v1实际为9配置/2001点/2ms。改变duration会同时改变ODE与SPICE终时，SPICE最大步仍.5µs。当前case角色是固定课程接口，不建议删除/重命名必需角色。

本轮正式仿真经 `/private/tmp/wwl-next-context/run_local.py --timeout 240 -- <实际python> -B <脚本argv>`取得共享两槽之一并强制1线程，全部常规远短于5分钟。资源池脚本不是读者复建依赖。编译/安装复用已有证据，本包未新安装依赖、未启服务。

`run_joint`拒绝已有out；核验器、绘图会覆盖指定文件，均选新目录。绘图的 `--lab`读取该目录的spec及 `results/results.json`，以上命令从发布同版数组重画；要画新修改结果，将该卡与新results放入同一个新lab副本，再指向它。不得把旧spec配新数组。三张SVG均由 [plot_joint.py](plot_joint.py)生成；可选 [preview_svg.py](preview_svg.py)使用resvg-py渲1600px PNG，数值计算不依赖它：

```sh
/absolute/python-with-resvg -B "$LAB/preview_svg.py" --results /private/tmp/ota-joint-figures
```

本次使用已有隔离resvg-py0.5.0与macOS PingFang字体，三张PNG已实际查看，图/标签/接地/浮点零与失败角清楚；其他平台替换字体路径。尚未在Obsidian客户端实际走读，也未测真人学习结果。

## 改一个条件前先预测

1. `starting→dm_only`只加Co；先预测两模态，再比较PM和逐源谱。`dm_only→balanced`只加Cc；DM不变不代表CM/面积/控制速度不变。
2. 把Rg20k改40k，保持Cg；门时间常数和Rg热噪声都变。非作者已实际跑一组独立ngspice变式，验证栅R输入等效PSD由8kTR翻倍；不能只改RC极点却忘记新增噪声。
3. 只改M3 mismatch=1.02，先重求Q；CMRR、噪声消去与稳定是不同判断。不能把确定2%偏差叫统计失配良率。
4. `half_bias`只将Iref改25µA，结果JSON保留Q/完整线性与噪声。输出噪声稍降而输入等效与CM噪声更坏；没有额外跑该半偏置的大步进，不替它声称SR/全预算通过。
5. 只看±.35V的大步归一化曲线，会以为建立更快；同时核实际终点相对DC切线的压缩和器件区，再说明它违反的是什么。当前不是给所有幅度报告一个固有SR常数。

## 工艺与实测：高重要性的具体下一接口

这些是本模型明确尚未验证的层；本机可执行的工作点/噪声/双环/非线性已经做完，不能把它们笼统推成“外部待验”。

| 真实对象 | 必须给的输入和故障点 | 观察与通过条件 |
| --- | --- | --- |
| PDK/器件电荷 | foundry/模型版本、角、W/L、体端、温度、实际Cgs/Cgd/结电荷、噪声/相关模型；替换压低寄生的教学卡 | 重新核每管Q/工作区、非线性Q(V)与完整导数/电荷矩阵；不能只保持同一个gm和几个对地C |
| 实际偏置/基准 | 基准启动、供电变化、参考噪声/PSRR、镜像失配及相关性 | 电源/参考/各支流同测；每新噪声源按自己的端口加入，不在已算源上重复加 |
| 实际负载/版图 | 负载范围、ESR/ESL、输入源阻抗、走线和衬底寄生、输出取样/注入位置 | 同一配置测DM及CM，必要时重列状态；探头加载不能被忽略 |
| 硅/硬件标定 | 电源/温度/激励幅度/频段、端口标定、重复噪声记录、DC范围及动态阈值 | 区分静态余量、统计良率和实际建立；SPICE与确定四角不签硅，也不以一条能带图或一般控制证书代替器件事实 |

实际来源核读：UDel Lecture10第3–4页电阻与沟道噪声；ngspice47源码的MOS1噪声支路/常数/谱输出与现行47+手册接口分别定位。温度幂律是声明的有限敏感性族，其适用条件回主文物理返回，不是本课校准过的工艺。#128/#251继续负责实际客户端/导航验收，不在本实验另造平台。
