# #149/#142 独立有限执行回执

冻结 source d533cf313ad121b4daf13dff4b29445d67dfc1e181a27596294c7499e898f489 与 fixed-inputs 296f0bdfb2bb35e1da085e908102e0dba201755f44208f76c111663e22d6cbdf 的默认运行、独立核对和相图实际渲染通过。四件作者输入在运行前逐字节复制，结束时再次核 SHA，未漂移。source 仅导入标准库，不依赖 hidden 候选 runtime。作者 expected.json 保留作为来源，独立 oracle 未读取它或 course checks 的自报期待值。

60 秒预跑实际 0.075 秒 exit0；新外部目录 CLI 上限300秒、实际0.081秒 exit0。report.json 与 pendulum-phase.svg 生成后立即逐byte拷回 cli-output/ 并核SHA；原stdout恰与report及预跑一致。命令、环境、stdout/stderr、退出码、时间与资源观测均在对应receipt。Python3.14.7，macOS27.0.1 arm64。数值CLI观测峰RSS23,707,648bytes；绘图53,198,848bytes。线程环境五项请求4，未建立OS线程数/硬内存上限保证。

独立 Fraction 全矩阵幂、adjugate inverse 和有限级数恒等式核反馈累计(3,2)、总5、a=.5临界不收敛、孤立.6与联合1.2。非正规矩阵有限幂核k4=(2048/125,256/625)，第一分量峰在k4与k5；耦合减100倍的第一分量亦减100倍，不把它等同全欧氏范数比例。

随机乘法以重复概率多项式卷积核n4/10/20全计数质量、总概率与精确均值(11/10)^n。对应最可能up_count为1/4/8，modal ratio为1/4、1/4、1/16，平均增长与典型有限结果不同；有限枚举不证明一般SLLN。Euler因子1/2、-1/2、-1、-2及六次迭代与真实exp(-t)分别核对。

阻尼摆全轨迹另算能量与角度，核V'=−.5v²与三步长有限能量下降；独立隐式中点h=1/3200、64000步参考对三档RK4端点的误差为[8.063574132413658e-09, 9.677076456158814e-10, 1.3690727317813457e-09]。Hopf半径以70digit Decimal的u=r^-2仿射ODE解核对，变分返回导数exp(-2)=0.1353352832366127与中心差分吻合；正/零/负alpha与零初值、爆破前后、unsupported/shape/最大步数/输出保护均有限核对。

expm1小t例(1e-6,100,10,1e-10)的结果与高精度参考在binary64可显示精度相同；旧直接相减误差约1.1022e-6。爆破临近前一个binary64点数学参考仍有限，接口因正分母未分辨拒绝；拒绝不是物理爆破证明。t*-1e-12仍返回有限半径，Decimal roundtrip输入参考与输出相对差为1.5416779e-05。这是强取消条件数处的实际精度边界；32epsilon护栏未在此实验中获得一般误差充分性认证，返回有限数不等于高相对精度证书。

assets/pendulum-phase.svg 为原输出逐字节副本；CairoSVG 2.9.1 离线全1000x570画布实际输出PNG并通过builtin view_image查看：刻度、完整图例、四轨迹、零流线、V=1、初值和稳定/鞍点标记完整。原英文图无中文字体问题。没有启用MCP/UI、改字体或源码；不是Obsidian显示、窄屏自适应或真人学习验收。一般数学来源与LaSalle/Hopf/SLLN论证由独立review核，此回执只签有限执行与实际离线图层。

复建：使用现存Python3.10+标准库，复制snapshot/dynamics_lab.py、fixed-inputs.json，然后用绝对源码路径与新工作区外部输出目录运行 --output-dir。完整实际命令见cli-receipt.json，独立核对命令见independent/radial-boundary/trajectory/interface receipts；renderer额外依赖既有CairoSVG，仅本次图层使用。保留任何失败，不覆盖旧输出目录。必要证据清单见artifact-sha256.json。
