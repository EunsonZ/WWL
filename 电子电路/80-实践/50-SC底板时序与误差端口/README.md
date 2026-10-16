---
domain: 电子电路
type: experiment
stage: 4
aliases:
  - 底板采样电荷与残余误差复算
sources:
  - "[[电子电路/42-转换器与采样时钟/09-底板采样注入馈通与端口预算]]"
prerequisites:
  - "[[电子电路/80-实践/48-两相开关电容积分器/README]]"
---
# 同一四开关模型：顺序、注入、馈通和误差端口

主解释在[[电子电路/42-转换器与采样时钟/09-底板采样注入馈通与端口预算|底板时序与预算]]。这里运行线性电容/给定signed电荷包，不模拟真实MOS分配；没有运行ngspice/PDK，不将它们列为器件证据。一般保护机制由浮动导体守恒证明，有限曲线不代证明。

## 输入、参考与复用

[fixed-inputs.json](fixed-inputs.json) 的SI标量都是精确有理字符串。Cs=1pF、Cf=4pF；CpA=.1pF、CpB=.2pF到Vcm=1.5V；CgA=.005pF、CgB=.004pF、B–gA跨耦合=.001pF。A/B/s/x/y均相对Vcm，转移A接Vcm而非绝对0。clock是绝对5→0V，换成局部3.5→−1.5V；总自由电荷包含clock终点基线。

四输入(.2,.8,1.2,.4)V、y0=0；qA=−(.02pF)(3V−x)，qB=−.03pC，s侧off包+.002pC。它们都是给定合成量，不是实测或等分通道的推定；5V不是任意工艺耐压建议。BF、AF和BF去跨耦合共12行，每行保存track、两释放、A回参考的四份A/B电位、clock电位及自由电荷。

[bottom_plate_lab.py](bottom_plate_lab.py)是规范新源，[测试](test_bottom_plate.py)、[图源](plot_bottom.py)随行。只读复用旧[finite_ota_budget.py](../48-两相开关电容积分器/finite_ota_budget.py)的负载函数parameters，实际SHA：

    ef440af7e11abfb26db158368a106e112adc8cd61b47ad9d87776d74f7f13a2d

导入暂设dont_write_bytecode且finally恢复，命令也用-B；旧源/镜像/数据不修改，旧理想和有限OTA完整套件不重跑。新源没有活动code-sync镜像，正文链接真源而不复制程序。

新有限拓扑明确分开负载αL=LB/Cf、信号−Csx，QB先减clock基线，再用GQ=M第一列/Cf传播；off用另一Goff。A0=100、taua=3.24μs、T2=180ns、TH=820ns，初态r0=−(1+1/A0)y0。24条新行按有限名义、实际Cs+1%/Cf−.5%、加channel、加feed、加off、加确定clock六方案生成，输入与初态不换。

孔径偏移(1,−1,2,0)ns、局部斜率(1e5,−2e5,1.5e5,0)V/s；T2偏移(−2,1,0,3)ns、TH反向调整，周期仍1μs。δx=slope·δt是声明的小扰动模型。噪声围绕最后实际窗口计算，给定Kη=1e−8·(.5)^|i−j|V²、off随机包std1e−17C且iid、OTA单边白谱1e−16V²/Hz，三源组独立、初态确定。未知参考/转移开关热源/有色OTA/随机clock及交叉块在正文同一端口账本保留，未默认物理零，也未看到电容就加kT/C。

## 重要性、独立预期和失败

| 重要性 | 具体断言/独立预期 | 容差与失败意义 |
|---|---|---|
| 高：参考和电荷 | K对角LA1.105/LB1.205pF，互项−1pF；全部绝对参考同移1.25V不改电荷；BF后A释放保qB自由电荷而非B电压 | Fraction逐项精确相等；错绝对/相对、漏gate基线、把浮动接地即失败 |
| 高：保护与反例 | BF QB=−Csx−.055pC；AF QB=−Csx−Cs·uA/LA−.05pC；无cross的BF少−.005pC | 独立相位式/节点消元逐字段核，不只看末输出；qA输入项只进AF，不许据此推BF总偏差必小 |
| 高：有限端口与状态 | 负载LB≠信号Cs；off不直接改刚结束w，却改r与下一y；完整两窗与旧M负载函数一致 | 默认V绝对2e−11、C绝对2e−23作独核目标；运行守卫2e−12·max(1,|state|)。不能拿作者M调用自证物理式 |
| 高：摆幅合同 | 查起点y、转移末w、恢复末y；初态1.01V但后来回1V内仍标失败 | 定向回归和实际改卡；本卡固定外驱的确定单极点轨迹端点足够，不将范围通过冒称SR/饱和已验 |
| 高：完整预算 | 实际参数/电荷传播固定偏差，完整联合K传播随机项；参考、Ron和1/f缺何状态/核/谱均列出 | 非作者核一般式；所选小计不称全硬件或其上下界，不将未知端口设0 |
| 高：RC未复位 | τ20μs首次(1−e⁻²)kT/C；R倍/T半首次(1−e⁻.5)；Kij可由独立创新和推出 | 用kT/C归一后的绝对差<2e−13；均值保交叉项，平衡四均值不等σ²/4 |
| 中：有限实现 | 12精确行/24新两窗行、四组逐拍noise权重及RC矩阵，合法变序/参数与拒绝 | 检当前实例/改卡，不泛化全部浮点或器件；不加装饰性扫参/Monte Carlo |
| 中：图和读出 | SVG只读保存JSON，1mV binary64 nearest/ties-even教学读出默认误差≤.5mV | JSON重生字节与像素分验；图不捏造器件轨迹、真实ADC或真人结果 |

aperture_probe同时关掉channel/feed，只看早x=.4到晚A=.6的跟踪ΔB；字段signal_only_B_change_between_releases_V不是实际含馈通的绝对B。输出增量.1V，错误用晚值则.15V。关feed对照将耦合外驱固定但保容量，理想开关另按控制断开，不声称MOS gate高电位也能自行断开。

selected_noise逐拍用本次实际窗口、后续M及各窗ζ方差；不能用名义固定窗套最后clock方案。电荷C、η的V、OTA的V²/Hz分开。量化只在读出端，不反馈，不自动假设误差独立均匀或Δ²/12。

## 输入预算、环境与真命令

严格匹配固定卡字段，标量≤80字符有理串；数组等长1..16，rc_count整数2..16，bool不当计数。Cs/Cf在1fF..1μF；A0/taua/两窗/温度/步长/摆幅正；寄生/κ/谱/std非负；失配绝对≤.1，|相关系数|<1。输入及孔径变化后都在[−5,5]且保合成过驱为正，窗口变化同时保T2/TH>0；含/不含cross两浮矩阵均须正定。预算属于实验接口，不是所有SC的理论定义域。

输出目录必须不存在；验证、计算与JSON有限性检查先完成再建目录；非法卡exit2，不覆盖results或已有文件/符号链接。只需标准库，无依赖安装、无设备连接。

真实环境Python3.14.7、macOS27.0.1 arm64。两槽共享runner取一、强制线程1/禁bytecode；正式默认.0331594s、限180s；七回归.025s、限60s。以下从候选实验目录执行，均是真命令：

    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 180 -- '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B bottom_plate_lab.py --inputs fixed-inputs.json --vault-root '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL' --out results > author-run.txt 2>&1
    python3 -B /private/tmp/wwl-next-context/run_local.py --timeout 60 -- '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B -m unittest -v test_bottom_plate.py > author-tests.txt 2>&1
    '/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/.venv/bin/python' -B plot_bottom.py --results results/results.json --out results

默认曾先执行一版，再将noise改为最后方案的逐拍实际窗口；独核指出摆幅漏起点后补y_before并将probe改为纯信号ΔB，再执行上述最终命令。早期输出只保存在候选根过程目录、不发布；正式results/author-run属于最后源，未伪称从未修订，也未重跑旧套件。

发布后在本目录用标准库Python、新输出目录即可复现；多任务环境仍须共享槽协调：

    python3 -B bottom_plate_lab.py --inputs fixed-inputs.json --vault-root ../../.. --out results-rebuilt
    python3 -B plot_bottom.py --results results-rebuilt/results.json --out results-rebuilt

WWL_SC_ROOT可指定测试所读的另一个真实库根。换机旧源必须具备同一端口函数/可核版本。源码和图源参数都是--out，不是--out-dir。

## 实际结果与独核

[results.json](results/results.json)保存全部逐沿自由电荷/A/B、三方案12行、六有限方案24行、逐拍noise矩阵/权重/小计、RC两初态K、读出/过载标志、旧源SHA和环境。[edge-ledger.csv](results/edge-ledger.csv)电荷单位C、电压V；[budget.csv](results/budget.csv)保存同样点V。[author-run.txt](author-run.txt)、[author-tests.txt](author-tests.txt)为实际日志。

七项回归包含BF/AF闭式、整体参考变换、自由q保护而非B电压不变、off符号、起始摆幅、RC创新和、非法合同。[topology.svg](results/topology.svg)画四开关/永久Cf/局部参考/全部耦合端点与相状态；[budget.svg](results/budget.svg)画同输入顺序、有限读相、确定差量。图只从[保存数据生成](plot_bottom.py)。

精确BF最后.703V；AF69929/110500≈.632841629V；BF无cross .698V。有限最后方案下一y=(.0630606616654,.275815072855,.587828123603,.699076041323)V，最后w=.698498844876V。所选方差6.098773014724728e−9V²，不是确定总差(.69907604−.65)V的平方。±.6V首越界均n3；±1V通过只针对确定轨迹，不认证SR或随机路径越界概率。

RC平衡方差4.141947e−13V²，首次3.5813954296e−13、R倍/T半1.6297291536e−13；四均值零初态1.6883063451e−13、平衡1.7728029978e−13、错误独立均值1.03548675e−13V²。该独立RC不认证SC会自动产生相同K。

非作者不用候选或旧OTA函数作答案，由节点约束/逐相一阶状态、逐源脉冲传播独核780字段及CSV：全部12/24行、四组noise权重/ζ方差/Kη、RC矩阵/均值通过；另3张合法CLI卡含多端口/窗口/负相关、初态越界后恢复、零误差源，由独立oracle复算；11非法CLI与已有输出保护通过。一般物理推导、七答案及未知端口协方差合同分别读核。最终两正式SVG经非作者CairoSVG渲染并实际查看通过：B字移离参考支路、确定轨迹限定与自适应差量bar均清晰；从保存JSON重生两SVG逐字节一致。27个wiki/标题/图目标（含三页返回）和13个relative路径、3个Python AST/两正式XML及三页patch apply --check通过。三改卡图另只核控制流/XML，未冒称像素观察；原生Obsidian仍未验。

## 外部验证接口

| 重要性 | 真实输入/条件 | 预期、失败与证据 |
|---|---|---|
| 高：PDK电荷/寄生 | 模型版本/许可、W/L/体端、PVT、绝对偏压、clock边沿/阻抗、各端I/Q/Jacobian | 核端电荷与换参考守恒，提取signed包/C；超容差换模型，不把半分通道或5V耐压当已验 |
| 高：动态/过载 | OTA极点/负载/SR/摆幅、转移Ron、A/B额外态、参考阻抗和完整时序 | 核三读数/起点/极值、节点残余及电流积分；单极点失败回MNA/器件瞬态，不裁线性输出续算电荷 |
| 高：完整噪声 | 各R温度、有限谱/1/f低频条件、参考/clock/packet联合K、复位/保持 | 完整hᵀKh及交叉核、不重计；缺源/核不报全硬件RMS，真实转移热源未由本数值认证 |
| 中：校准/差分/迁移 | 输入/PVT扫描、差分匹配、训练与独立复核、原始样点/带宽 | 分别比输入相关残差与总偏差；拟合不等外推，真人能否自主改端点另验 |
| 中：真实采集/显示 | 实际时标/校准、正确库/页及客户端 | 与原始数据/端口一致；本包不称已运行台架、Obsidian或真人实验 |

可本机算的电荷、相位、一般噪声传播与RC相关已在正文完成；外部缺的是模型卡/提取/量测参数与实际层，不把缺硬件作为不推电荷的理由。
