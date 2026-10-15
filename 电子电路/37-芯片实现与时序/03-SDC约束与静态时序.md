---
stage: 2
aliases: []
sources:
  - https://raw.githubusercontent.com/The-OpenROAD-Project/OpenSTA/master/sdc/Sdc.tcl
  - https://docs.amd.com/r/2023.2-English/ug903-vivado-using-constraints/Relaxing-Setup-While-Maintaining-Hold
prerequisites:
  - "[[电子电路/34-时序状态与协议/02-建立保持时钟偏斜与路径#固定同沿关系再算deadline]]"
  - "[[电子电路/37-芯片实现与时序/01-工艺标准单元与PPA#逻辑、时序与几何是不同视图]]"
---
# SDC约束与静态时序

**读者问题：为什么代码仿真都对，芯片还会错过采样窗口？** 基础入口把发射沿、最晚/最早数据和接收沿放到同一ns轴；快进入口直接写max/min不等式，再用SDC明确分析哪些端点、哪些模式。静态时序沿网表弧传播时间界，不靠试尽数据波形；它假设模型/约束和路径关系正确，不能证明功能、CDC协议或电源模式正确。

## 同一网络有最晚稳定和最早污染

取正沿源L_k=kT、目的C_k=kT+s，s=capture−launch。新值最晚L_k+tCQmax+dmax；要供下一capture，须≤C_(k+1)−setup−us。最早L_k+tCQmin+dmin；不能污染本拍旧值直到C_k+hold+uh。因此

\[S_{setup}=T+s-tCQ_{max}-d_{max}-setup-u_s,\quad S_{hold}=tCQ_{min}+d_{min}-s-hold-u_h.\]

每项s，S≥0才满足该检查。最短组合路径未必是最长路径同一个输入分支；min/max须分别传播。T10ns、s+.5ns、tCQmax.8、dmax6、setup.7、us.2，setup slack2.8ns。tCQmin.15、dmin.25、hold.10、uh.05，hold slack−.25ns。调慢到20ns只改善setup；若插buffer使dmin+.30、dmax+.50，则setup2.3、hold+.05，改善一项时回查另一项。

![[电子电路/80-实践/29-时序约束与物理预算/assets/sta-paths.svg]]

图区分下一沿setup与同沿hold，同时将时钟树延迟与数据延迟分别画出。此图补物理路径预算，与已有M16采样/透明波形配合；不称为真实STA输出或亚稳态电压。

## SDC写的是环境与采样关系

[OpenSTA Sdc.tcl的create_clock、IO delay及路径例外帮助](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenSTA/master/sdc/Sdc.tcl)是本文命令形状依据。实践文件指定库时间单位ns、电容pF，create_clock period10、waveform{0 5}，输入a到达min.2/max1.2ns，输入slew.1ns，输出y外部需求max1.0/min−.2ns，输出load.020pF；setup uncertainty.2、hold.05ns。实际库需同单位核对，不把SDC裸数字误作秒。

输入delay是外部源相对参考时钟到达端口的时间，不是内部门延迟。max给最新到达，min给最早到达；只给max可能掩盖输入hold。输出delay描述外部接收器需求及板级路径。简单同相同源时钟、板级数据延迟忽略时，外部setup1.0ns使本芯片端口须在下一沿前1ns有效，所以-max1.0；外部hold.2ns使新值须在本拍沿后.2ns才变化，所以-min=−.2。含板级时钟/data skew或不同沿时须按绝对时刻重建，负min不是“物理负传播时间”。输入slew/驱动模型和负载C影响库时序；不能以set_input_delay替代驱动强度。

时钟latency区分源与网络，到layout后propagatedclock用实际树延迟；uncertainty用于未覆盖的抖动/模型预算。若确定性skew已经显式传播，不能又把同一个skew全额计作uncertainty。OCV/早晚角/相关性需工具策略，单一typ表不能代表全部签核角。

## false path是责任转移，不是修复

本小网表有async_in→u_sync1/D异步采样，u_sync1/Q→u_sync2/D仍同域。教学例外只切前一段，不切两级之间，也不切第一层输出到任意功能逻辑。分析责任转到CDC结构、布局/解析预算、协议及同步单元；第一段没有普通确定setup保证，切掉报告不会使它成为无亚稳态风险路径。

false path也可来自可证明不能同时激活的功能路径，但须模式/逻辑依据。不能因某路径违例便设false。宽泛set_clock_groups或-from所有寄存器-to所有寄存器会把真正同步路径一并藏掉。每条例外须记录起点/终点/through、模式、为什么不可按普通关系分析、谁负责替代验收，并查命中数量；空集合不代表安全。

## 两拍路径要先证明第一拍不采

同波形同频时钟、两端使能只在约定相位每两拍有效，源在未使能期间保存数据，接收在中间第一拍不采，可把setup移到C_(k+2)。若只设setup2，许多SDC语义同时把相关hold关系移到C_(k+1)；常见成对约束setup2与hold1恢复原同沿保持关系。这里须**两端真实使能/采样合同**，不能用“通常慢”推导。

[AMD UG903 2023.2 的Relaxing Setup While Maintaining Hold](https://docs.amd.com/r/2023.2-English/ug903-vivado-using-constraints/Relaxing-Setup-While-Maintaining-Hold)明确以每两周期使能为前提，并分别移动setup/hold。相同波形时-start/-end可等价；不同频率/相位不能机械套N−1，先标选中的launch/capture沿，再核工具报告。

实践的example.sdc**没有**对普通每拍DFF设multicycle；可执行exceptions-demo.sdc只在显式声明外部协议保证enable并指定实际端点后演示两条命令，默认拒绝应用。CPU仅计算指定沿间预算，不假装解析完整SDC、证明使能或做STA。

反例：本例普通u_capture每沿都采，组合路径12ns，设setup2得到表面裕量并不改变10ns时它已采错的事实。另一反例是把复位recovery/removal全部false而未验证释放：数据setup通过仍可因异步控制撤除违例出错。

## 报告必须绑定输入和检查覆盖

真正运行需同版门级网表、Liberty各角、SDC各模式、布线RC/SPEF与工具版本。保存未约束端点、被例外切断的路径、setup/hold/recovery/removal、slew/cap/fanout、时钟与WNS/TNS，而不仅截图一个绿数字。WNS最坏slack、TNS按工具定义累加违例，不能解释为出错概率。

本组提供run_sta.tcl及完整纯教学cells-fast/slow.lib，命令入口 `sta -exit run_sta.tcl`；当前未发现sta，actual tool run=not_run，不生成fake timing.log。模型级手算2.8/−.25与这个简化Liberty网表的报告数不强行相等：前者指定另一组max/min预算，后者用于让读者学习输入绑定与命令。[[电子电路/80-实践/29-时序约束与物理预算/README#输入视图与工具责任|实践输入与预期条件]]列真正执行后的验收门槛。

## 四题及理由

1. 把s从+.5改−.5ns，首例两个slack？**setup1.8、hold+.75ns。** clock早到分别收紧下一沿、放松同沿要求。
2. 忽略输出-min只看-max，可宣称外部接口通过吗？**不能。** 可能新值太早破坏板上接收器hold；需最早路径与时钟关系。
3. false掉u_sync1/Q到u_sync2/D有什么损失？**隐藏了解析时间与第二层同域采样预算。** 正确结构例外针对异步输入到第一层，其他检查仍保留。
4. 同频两拍路径设setup3，应总加hold2吗？**只有按特定关系恢复同沿hold且功能允许三拍时。** 不同频率、相位、边沿和使能不能套口诀；普通每拍capture无权改成三拍。
