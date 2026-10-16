# 承重原文与本卡模型

- [MIT6.776 Lecture12，2005](https://ocw.mit.edu/courses/6-776-high-speed-communication-circuits-spring-2005/2c7a97621d644036cfed2edbcfb833ad_lec12.pdf)，PDF第6–8页：共栅输入匹配与主要沟道噪声。作者读取原站文本，非作者另看相关页像素。本卡有限go/电容/三节点与实际数值自行定义；没抄来一个真实LNA的NF或器件参数。
- [MIT6.776 Lecture16，2005](https://ocw.mit.edu/courses/6-776-high-speed-communication-circuits-spring-2005/abdc7a7dbbadee52a8f2d77b38c920c4_lec16.pdf)，PDF第13–21页：SSB/DSB、方波LO谐波及转换增益；第27–30页为跨导/换流路线；第39页为被动开关桥。这些是选型与对象依据，本包四管/RB/LO条件和理想Ron噪声模型分别明示，不冒称同时实现整套Gilbert、镜像抑制或全部混频家族。
- [ngspice官方47 release source](https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47.tar.gz)，实际tar SHA894e649651f1838a14095e5a5439e7d3aa63e87ede14d283173fda4fcdef675f。作者与核查者实际读取本机该release的mos1noi.c、mos1temp.c、const.h；不是拿GitHub master当47。NLEV<3的channel热源比例(2/3)|gm|，NLEV≥3另有triode α项；oxide常量3.9·8.854214871e−12，kB1.38064852e−23。实际版本/二进制见[身份](spice/reader-evidence/actual-binary.txt)，具体噪声代码位置见[执行源说明](spice/reader-evidence/SOURCE-NOISE.md)。
- [ngspice文档入口](https://ngspice.sourceforge.io/docs.html)用于模型/分析语义的版本定位。MOS1的普通.noise是固定工作点的小信号统计；不能拿LO周期瞬态上的一个冻结工作点认证周期噪声。
- 库内[[电子电路/24-MOS与BJT/04-Q点偏导与实际小信号节点]]和[[电子电路/24-MOS与BJT/06-寄生短沟道与紧凑模型层级]]继续主讲偏导、端口电荷与模型层级；原amp_lab和08 active_match是真源，只读复用不抄镜像。

一般三节点/Routh、噪声注入外积与波变换、2/π/Ron/RB折叠模型均有独立解析核；有限SPICE由真实网表和原非均匀样点核对，不把有限运行当一般定理或真实工艺验证。输入噪声折叠求和要求WSS/频率正交且输出采用LO周期平均PSD；相关频带另加交叉项。实际周期MOS/预选器/驱动能量与完整RX仍有明示接口。
