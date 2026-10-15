---
stage: 2
aliases: []
sources:
  - https://openroad.readthedocs.io/en/latest/main/src/dft/README.html
  - https://ece-research.unm.edu/jimp/vlsi_test/slides/html/bist1.html
prerequisites:
  - "[[电子电路/34-时序状态与协议/01-锁存触发与采样窗口#反馈保存的是一位状态]]"
  - "[[电子电路/32-组合逻辑/02-布尔代数真值表与卡诺图]]"
---
# 扫描、BIST与制造测试

**读者问题：功能仿真跑过了，为什么制造后还要专门的测试模式？** 基础入口先让一个本应变化的节点被固定0，找能在输出看到差别的输入；快进入口用激励/传播/可观测性构造故障集合，再读扫描和签名的代价。本文是有限小网络的故障模型练习，不把它的百分比搬到真实芯片良率。

## 制造缺陷与模型不是同一集合

开路、桥连、短路、接触/via缺陷、参数偏移、速度失效可以影响逻辑/电气。单stuck-at模型把某逻辑线永久固定0或1，以便有限分析；它不覆盖所有真实缺陷。transition故障关心一个边沿能否及时到达，需要两拍激励与at-speed捕获；桥连/路径延迟/模拟/存储故障需要其他模型。功能验证问规格与实现是否一致，制造测试问实例在选定故障模型/条件下有无异常，两种“覆盖”分母不同。

小网络 n=a AND b，y=n OR c，另外unused=NOT a无观测输出。节点a/b/c/n/y/unused各两种stuck-at，**12个原始单故障**，不做等价折叠。在给定输入下先在故障节点钳位，再按图传播；例如aSA0需要a=1激励，b=1使AND能传播，c=0避免OR掩盖，于是110正常y1、故障y0。输入111虽也把a设1，却被c1遮住，不能检测该故障。

![[电子电路/80-实践/29-时序约束与物理预算/assets/scan-fault.svg]]

图同时画功能AND/OR网络、未观察支路和扫描mux/DFF数据路。输入、输出与testclock/SE明确；它没有模拟过渡故障、亚稳态或实际电气短路。

枚举全部8种a/b/c输入，前五节点10个故障各有至少一个可见差异，unused两故障在本输出永不可观察。完整向量的rawcoverage=10/12=83.333%，对可检测集合为10/10=100%。后一百分比必须注明排除了什么；把无观测故障从分母删掉而只写100%会误导。CPU结果逐故障列检测向量，不只报数字。真实ATPG可证明某模型下不可测或放弃/超时，aborted不应自动改成untestable以抬高覆盖。

## 扫描给内部状态控制和观察通道

普通flop沿后Q'=Dfunctional；扫描flop在SE=1时选SI，SE=0时选功能D。三只串链q0/q1/q2，新态=[SI,oldq0,oldq1]，SO=沿前oldq2；一次沿所有旧值同时读取，不能顺序更新让新SI瞬间穿透三层。要装入[q0,q1,q2]=[1,1,0]，从初态000依次送0、1、1，得到000→100→110。SI顺序是目标字倒序。本小例a/b/c由链设置、y为直接输出；若内部结果不直接可见，要functional capture进入flop后shiftout。

完整scan测试有shift装载、SE切换满足时序、functionalcapture、shift观察，并可把下一向量装载与上一个结果移出重叠。长度N单链每向量成本大致Nshift+capture，链数增加缩短shift但占I/O/布线和测试控制。scan_enable不应在采样窗口任意变，testclock与功能clock关系、跨clock/edge链锁定锁存器、reset旁路和power模式均需专门约束。慢shift通过不证明高速功能捕获通过。

[OpenROAD DFT文档的scan-cell/chain/enable和scan_replace/plan段](https://openroad.readthedocs.io/en/latest/main/src/dft/README.html)提供这三个结构及工具入口。本组没有执行scan insertion；当前工具能力/限制应读固定版本，本文自己的MUX/DFF示意不声称等同某库合法scanflop。

## BIST：可重复生成不等于穷尽故障

逻辑BIST可用LFSR产生伪随机向量并用MISR压缩输出，自含初始化、测试时钟、向量数、故障模型和期望signature。三位教学LFSR定义整数state bits q2q1q0，新state=((state<<1)&7)|((q2 XOR q0)&1)，seed001：001→011→111→110→101→010→100→001，周期7；seed000永远000。由完整状态枚举证明此递推的非零周期，不借“LFSR”名称自动承诺所有多项式都最大周期。对应输入覆盖7种非零字，会漏000；伪随机也可能对随机抵抗故障长期不给所需激励。

![[电子电路/80-实践/29-时序约束与物理预算/assets/bist.svg]]

图给三个DFF和反馈XOR明确端点，MISR的输入反馈也定义出来；没有把两个不同递推混叫同一个电路。扫描与BIST会制造高活动，shift/capture峰值功耗、IRdrop、温度可能超正常应用；提高测试频率不能只看总测试秒数。

## 签名碰撞是信息损失

另定义三位串行signature更新：f=oldq2 XOR responsebit，newq=((oldq<<1)&7) XOR (011 if f else000)，初态000。这是本例的多项式除法递推：把从左到右的位串当作高位先到的M(x)，求x³M(x)除以x³+x+1的余式。不是未补零的M(x)余式。0000和1011这两个不同四位响应均得到000；每一步代回即可证实别名。签名相同不证明响应完全同，也不证明无制造故障。

若假设所有长响应错误等可能、线性满秩压缩等，可给接近2^−m的碰撞概率；真实故障响应分布与测试集一般不满足这一均匀假设，故障覆盖须直接分析目标集合。[UNM VLSI Test BIST讲义的Signature Analysis及Aliasing Probability段](https://ece-research.unm.edu/jimp/vlsi_test/slides/html/bist1.html)明确提醒错误响应比例不等于故障检测比例。本页只用其边界提醒，碰撞、LFSR序列和小网覆盖均为独立有限枚举。

MemoryBIST还需要地址遍历、写/读模式与故障假设，例如write0/read0/write1/read1能检简单stuckbit，但不能保证耦合/地址译码/保持故障全部覆盖；March测试的方向、操作序列及memorymacro接口另成合同，不用泛称BIST消除条件。生产还含测试机时序/电压/温度、探针/封装、测试逃逸、误杀、诊断、修复/熔丝、安全的testmode权限。

## 四题及理由

1. 本小网络只用111检测aSA0吗？**不能。** n可能变0但c1让y仍1；检测需110等去掉掩盖。
2. 本8向量rawcoverage83.333%与功能分支覆盖100%矛盾吗？**不矛盾。** 分母分别是12故障与软件/RTL分支，不能互相换证据。
3. seed000、递推正确，为何BIST向量不变化？**零是该线性递推固定点。** 需要合法非零seed及启动/重置协议；正确电路也可因测试初始化错误失效。
4. 正常/故障signature相同能验收无故障吗？**不能。** 0000/1011给显式别名，需故障检测覆盖/多签名或其他诊断，不能仅用一小码代替全响应事实。
