---
stage: 2
aliases: []
sources:
  - https://raw.githubusercontent.com/The-OpenROAD-Project/OpenSTA/master/sdc/Sdc.tcl
  - https://openroad.readthedocs.io/en/latest/main/src/cts/README.html
prerequisites:
  - "[[电子电路/37-芯片实现与时序/01-工艺标准单元与PPA#逻辑、时序与几何是不同视图]]"
  - "[[电子电路/37-芯片实现与时序/03-SDC约束与静态时序#SDC写的是环境与采样关系]]"
  - "[[电子电路/37-芯片实现与时序/06-扫描BIST与制造测试#制造缺陷与模型不是同一集合]]"
---
# 时序约束与物理预算：从输入合同到不同证据

基础入口先手算10ns两沿的setup/hold，再枚举AND/OR小网络的12故障。快进入口检查源码单位、Elmore下游C与CRC补零协议。这里有能执行的CPU模型和可供STA工具读取的完整教学输入，实际执行层分别记录。

复制本目录至库外可写位置，所有生成选择新的输出目录，勿覆盖他人的路径。无需安装；数值仅stdlib，图层需已有matplotlib/CairoSVG，缺失记not_run。

```bash
python -B -m unittest discover -s . -p test_implementation_model.py -v
python -B implementation_model.py --output /private/tmp/implementation-my-number-run
python -B generate_figures.py --output /private/tmp/implementation-my-figure-run
```

两个CLI必填`--output`，缺参exit2不写；`generate(output)`和`main(argv=None)`供显式调用。导入不解析argv、不初始化绘图/字体缓存、不写文件；绘图lazyimport、direct Figure与rc_context，MPL/XDG缓存限定显式输出并恢复环境变量。SVG是真源生成输出、PNG是它的360/425渲染，不是另一套图。源/测试/README直接交付，不创建平行code-sync复制。

## 数值合同与支持域

Python原生int/float实标量，bool/complex/数组/嵌套/cast对象不接收，非有限及域外ValueError，先校验不静默丢虚部。每个循环固定次数，最多4096bit/step，3input故障模式最多8组，序列最多9动作，无浮点while搜索。以下是教学有限域，不声称覆盖任意SI动态范围。

- `timing`以秒返回setup/hold slack和选中capture时刻；时间0..1s、period1e−15..1s、skew−1..1s，min≤max；cycles1..16只移动setup关系，调用者承担真实enable协议，hold保持本模型同沿关系。负slack保留，不钳成pass。
- `effort`限定同一每级g/b/p，N1..16、H1e−6..1e6、g.01..100、b1..100、p0..100。F=H(gb)^N；连续相等努力下D=N(F^(1/N)+p)。返回Cin链以g/b均匀近似，每相邻h_on=H^(1/N)，实际h_total=b h_on，不能把该链用于任意不均匀g/b。返回奇偶极性，选N不能忽略逻辑函数。
- `power`C1e−18..1e−3F、V0..100V、f0..1e12Hz、活动次数0..100/cycle、短路峰/泄漏0..1A、短路宽0..1s。动态项的α是上升次数，三角直通脉冲是假设，返回W；支持域只保证计算有限，不自动保证波形占空物理一致。
- `elmore_tree`固定根Rd/R1/R2、Ca/Cb对地拓扑，R0..1e9Ω、C1e−18..1e−3F，返回阶跃一阶矩s，不叫测得t50。`supply`只DC恒流负载，V0..100、I0..100A、R0..1e6Ω、宽/厚1e−12..1m；drop>V拒绝，J单位A/m²，未给EM限值。`utilization`cell/core/block面积m²在0..1，core>0且blocked<core，U>1保留为不可行指示。
- `power_sequence`只规定九动作的有序前缀，power_good/reset_released是显式外部bool前提，错误顺序/不满足恢复边界拒绝；不模型模拟供电时间，非一般低功耗协议验证器。
- `scan_shift`三bit旧值同时更新，len(serial)+1行含初态，SO每沿返回旧q2；`logic/faults`固定n=a&b,y=n|c,unused=!a，12原始单stuck-at故障不折叠；完整8向量检测10，未观测unused不可检测。
- `lfsr`三位seed0..7、steps0..4096，zero允许但锁死明确；非零seed1的周期7由枚举。`signature`三位初态0..7、最多4096bit，反馈递推如章06；零初态对应x³M(x) mod(x³+x+1)，不同位串0000/1011别名。无真实随机/所有故障等概率假设。

## 输入视图与工具责任

[timing_top.v](timing_top.v)有4只TDFF与2只TINV，用单时钟每拍DFF、同步a路径和async_in两级。两份cells*.lib全部由本实验人工给定：fast TINV=.1ns/tCQ=.15/setup=.2/hold=.1，slow .4/.8/.7/.15；每个时序弧只一个slew点，不刻画负载非线性/真实PVT，不是代工厂characterization。网表不含powerpins/async reset，这是逻辑timing模型；电源/复位物理责任由正文拓扑说明，不能从此网表声称实现完成。

[example.sdc](example.sdc)提供时钟、max/minIO、slew、load、分开uncertainty及只切async_in到sync1/D例外，级间仍timed。没有在每拍capture上偷偷加multicycle。[exceptions-demo.sdc](exceptions-demo.sdc)默认error，只有调用者另行证明对应设计同波形两端enable后才可设置协议flag/真实端点并执行，不能作用于本普通网表来消违例。

```bash
# 仅在已有OpenSTA时，从复制出的实验目录执行；本次未运行。
sta -exit run_sta.tcl
```

run_sta.tcl用脚本所在目录绑定2Liberty/netlist/SDC，报告输入/输出约束和min/max。预期验收条件是实际解析/链接无error、所有同步端点有clock/IO、min/max/recovery等需要的报告完整、例外只命中首级、无新增未说明违例；记录工具版本、命令、输入SHA和真实输出。未执行就没有timing.log，CPU2.8/−.25ns是另一组手算预算，不是该网表STA的期望数。复制者若改参数必须更新版本，不拿以前CPU结果当新布局角签核。

综合需要RTL/映射库/约束和等价；布局布线需要tech/LEF/供电/宏/RC角，之后提取/STA/DRC/LVS/IR/EM；DFT插入及制造ATPG需合法scan库/模式/故障模型。当前sta/yosys/iverilog/openroad命令未发现，所以这些actualtoolrun均not_run；不自动安装、不伪造日志。Tcl语法/命名集合的教学stub检查即使通过也只属输入检查，不能冒充OpenSTA执行。

## 图件与验收范围

10原创SVG与20个360/425PNG，含工艺剖面/单元、布局空间、努力曲线、不同STAdeadline、RC树/clocktree、供电回路、CDC/复位、powerdomain、scan故障和LFSR。figure-data按SI/索引记录CPU参数与结果。V32仅补物理路径/max-min预算，已有M16的透明/沿与波形前提仍由其原页承担；V34仅补同步级间/复位与电源责任，未实现Gray异步FIFO、未模拟模拟亚稳态，不升级整体图信用。最终范围由独立审阅确认。

作者测试为CPU模型/输入/导入合同，图片实际小屏核读另记。SPICE、STA/综合/HDL/physical/formal工具、真实客户端、硬件、真人学习均未运行。没有将modelpass转成流片/制造测试覆盖或整个M18工程能力验收。
