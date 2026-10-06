---
stage: 2
aliases: []
sources:
  - https://documentation-service.arm.com/static/63f3499c9567172d4e2aadd6
prerequisites:
  - "[[电子电路/34-时序状态与协议/06-复位亚稳态与CDC协议#单bit、脉冲、多bit不是同一个任务]]"
  - "[[电子电路/34-时序状态与协议/06-复位亚稳态与CDC协议#异步assert，同域同步deassert]]"
---
# CDC、RDC、低功耗与上电顺序

**读者问题：时钟一样、逻辑一样，为什么只复位或断电一个模块仍会破坏事务？** 基础入口把一笔数据的拥有者、请求/应答和电源状态排成表；快进入口读异步控制对采样窗口和协议epoch的影响，再验证本页有限状态顺序。它是自足教学序列，不是某芯片推荐的通用寄存器写表。

## CDC结构必须对应信息类型

单bit慢状态可用目的clk两级同步，第一层输出不直接用于功能；两层之间短且受约束，额外解析时间降低风险，未把失败概率归零。短脉冲可能完全落在目的两沿间，增加第三层也恢复不了没采到的信息；多bit编码逐位同步可能混出不存在的字，需要握手锁住数据、或适当的异步FIFO。

带回 [[电子电路/34-时序状态与协议/06-复位亚稳态与CDC协议#单bit、脉冲、多bit不是同一个任务|已接受CDC类型与Gray入口]] 的01→10混字和指针例，再返回图中看哪个信号必须保持、哪个走同步链。本组补的是物理路径/电源边界与复位，不实现完整异步FIFO或真实亚稳态波形。

![[电子电路/80-实践/29-时序约束与物理预算/assets/cdc-reset.svg]]

图上解析时间采用明确的边沿参考。设首级launch沿为 $L_0$，目的下一capture沿为 $L_0+T+s$，$s$ 是capture相对理想下一沿的偏移，正skew让第二级晚采；$d_{12}$ 是首级输出到第二级D的wire/buffer延迟，$t_{setup,2}$ 是第二级setup，$u$ 是额外不确定度预算，全部单位s。从第二级截止倒推，首级输出须在 $L_0+T+s-d_{12}-t_{setup,2}-u$ 前进入模型要求的有效状态。

还必须说明指数尾部从哪里开始计时。本教学记 $t_{ref}=L_0+\delta_1$，$\delta_1$ 是与器件拟合定义一致的首级有效CQ/内部尾部时间起点偏移。于是可用尾部解析预算为

$$T_r=T+s-\delta_1-d_{12}-t_{setup,2}-u.$$

这里 $\delta_1$ **不是**“setup违例进入亚稳态后，普通 $t_{CQ,max}$ 仍保证在该时间内解析”的上界；违例正会撤销正常CQ保证。它只是在声明好的characterization参考下，把时钟沿、内部解析节点或输出尾部之间的起点差记账。若拟合prefactor已经吸收起点偏移，或模型从内部节点直接计时，应使用那一套等价参考，不能再扣一次CQ或任意拼接另一套 $\tau$。实际器件的prefactor、$\tau$、time-origin和PVT须同一characterization，本章没有这些真实参数，不能输出真实MTBF。$T_r\le0$ 时也不能声称有正的解析窗口，应改变预算/实现并重新检查。

教学例取 $T=1$ns、$s=0$、$\delta_1=0.2$ns、$d_{12}=0.1$ns、$t_{setup,2}=0.1$ns、$u=0.05$ns，得 $T_r=0.55$ns。漏掉首级起点偏移会错得0.75ns。仅为核对指数敏感度，假设同一模型 $\tau=0.05$ns，则尾部指数改善因子的比是 $\exp((0.75-0.55)/0.05)=e^4\approx54.598$；这不是实测MTBF或真实失效率。回访 [[电子电路/34-时序状态与协议/06-复位亚稳态与CDC协议#模拟亚稳态不是第三个合法bit|正常CQ保证失效与解析尾部]] 与 [[电子电路/34-时序状态与协议/06-复位亚稳态与CDC协议#只算假设清楚的可靠性趋势|同一概率模型的参数条件]]，返回本图检查起点有没有遗漏或双计。

源总线保持至ack，不放在一串独立bit同步器里。第一层false例外不能延伸到整个同步链。Gray指针即使相邻只变一bit，也须位间skew/maxdelay、满空/回卷额外位和存储端口/epoch合同，不能从编码名称推出所有布线安全。

## RDC：数据在别人的复位沿改变

RDC是不同复位域之间的风险。A与B同一个clk不代表同一个reset：A的异步reset可以在任意时刻清Q，B仍活动，在B采样窗口附近看到变化；这是reset引起的数据跨窗口，不因“非CDC”便消失。复位还可能清掉req但未清ack，使接收端认为另一笔事务已经完成；同步bit电气安全也不足以恢复事务意义。

外部低有效reset异步assert允许无clk时拉到已知状态，本地域同步deassert需clk推进后释放；目的功能flop还要recovery/removal、最小脉宽和复位分布检查。复位同步链仅处理释放边界，不能保证所有交叉接口同拍恢复或状态一致。若一个域能独立复位，协议应有隔离/排空/取消、明确丢弃规则与重新加入握手。通过resetepoch或系统协调判别旧事务；不能让一个永远保留旧ack的域看到新req就误认为已经答复。

## 电源域：隔离不保存状态，保持不驱动输出

开关切断VSW后，普通flop/组合门的输出与内部状态未定义；跨到always-on域的信号应在失去有效电源之前被隔离到协议安全值。隔离单元和其控制通常由仍供电的域驱动，clamp0/1须对应实际接口的inactive值。不能在断电域内放一个普通AND再认为它会永远输出0。

retention用辅助仍在供电的存储保存指定状态；保存/恢复需要单元/控制时序，普通flop不会因为RTL变量还存在而保留物理电荷。保留内部值也不意味着中间buffer和输出仍能驱动，仍需隔离。levelshifter处理不同电压域的电气转换，隔离处理无效域的语义边界，两者功能不同；实际库可能有合并单元，仍须核对direction/rails/mode。

![[电子电路/80-实践/29-时序约束与物理预算/assets/power-sequence.svg]]

图明示VDD_AON、开关后的VSW、retention备份电源及隔离输出，不把三种功能画成没有供电脚的纯框图。这里clamp0被定义为valid=0，数据在valid0时被接收方忽略，wake_request由AON保存；若接收方在data0时产生动作，该clamp就不是安全值。

[Arm DEN0050D，§7.2.9印刷页103](https://documentation-service.arm.com/static/63f3499c9567172d4e2aadd6)讨论隔离/复位、idle值和retention输出边界。它是具体架构文档，不授权把本序列用于任意IP；真实poweraware模型、UPF/CPF、cell库、reset/clock控制和各接口仕様需共同核对。

## 一次关闭再恢复的明确合同

本模型有9个动作，事件索引k而非假设真实延迟：quiesce让上游停止新事务并确认在途已处理/取消；save备份被声明保留的状态；isolate使valid强制0；clock_off停止工作clk；power_off切VSW；power_on重接VSW并等待power_good；clock_on恢复有效clk；restore恢复状态/初始化，最后release解除隔离并允许事务。状态表用0..9共10行含初态；restore单独计一步。不能把等待power_good偷作一个CPU布尔数就称模拟供电稳定。

本教学系统在断电前不清被保持状态，恢复阶段功能reset保持assert直到restore完成并经本地域同步释放，release动作要求power_good、clk可用、reset_released、restored全部满足。若设计规定reset会清保持值，必须改为只reset非保持状态或在reset结束后restore，再重新定义顺序；不能同时承诺保留和清零同一flop。

CPU接口把power_good/reset_released作为外部已满足前提，验证动作顺序和拒绝早release；真实时间、电压达到阈值、PLL锁定、resetwindow和backpower都在模型外。持续有效的wake来源须AON，otherwise域断电后永远看不到唤醒请求。失败出口可保持隔离并报错误/重试，而不是power_good超时后强行继续。

反例序列isolate晚于power_off：从断电到clamp之间AON可能看见不定义valid；另一个反例只clockgating未断电却reset独立解除，电源稳定也不修RDC。powergating节省leakage，clockgating主要减少clock切换，不能互换。

## 四题及理由

1. 两域clk相同、reset不同，可排除RDC吗？**不能。** 源reset使Q异步改变并可能穿过目的窗口/事务状态，需边界与协议检查。
2. 一个retentionflop保存了data=42，可在断电期直接让普通buffer传到AON吗？**不能。** 保存不保证输出buffer供电，需隔离/合法输出单元及valid协议。
3. valid的inactive值为0，clamp1是否一定更安全，因为避免未知？**不。** 它可能制造假事务；合法电平仍可能错误语义。
4. reset释放时clk未运行，本域同步链能保证按时恢复吗？**不能。** 必须等有效clk与同步沿；有超时/保持隔离的失败出口，不能把数学状态表称真实波形测量。
