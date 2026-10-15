---
domain: 电子电路
type: lab
stage: 5
content_status: usable
evidence_status: partial
aliases:
  - Chiplet封装接口预算实验
sources:
  - https://hc2023.hotchips.org/assets/program/tutorials/ucie/UCIe%20Protocol.pdf
  - https://www.cs.virginia.edu/~skadron/Papers/hotspot_mej.pdf
prerequisites:
  - "[[电子电路/62-Chiplet与异构封装/01-封装互连与异构集成#局部被动RLC由两个状态推出]]"
  - "[[电子电路/62-Chiplet与异构封装/02-热电机械协同#从热通量到两节点能量守恒]]"
  - "[[电子电路/62-Chiplet与异构封装/03-系统分割与接口权衡#带宽与延迟必须用相同层的字节]]"
---

# 封装耦合与接口：可检查的有限模型

实验沿同一A/B分区计算接口位数、帧填充、无排队串行时间、两端活动能量及分配给热节点的功率。RLC、秒级平均温升和自由CTE失配分别有明确对象与边界；没有把这些计算连成“封装全链已验证”。教学几何和材料/寄生均非真实制造保证。

在本目录执行 `python -B -m unittest discover -s . -v`。生成命令 `python -B generate.py --output /absolute/new/external/path`：output必填且须新目录，拒绝主库、候选及已有目录。可由调用者设置库外 `MPLCONFIGDIR`。models/generate纯导入只用标准库、不解释argv、不写图或加载NumPy/Matplotlib/CairoSVG；生成时才惰性加载，使用直接Figure和局部rc_context，没有pyplot或全局rcParams修改。

## 参数与返回合同

实数只接受Python int/float，拒bool/complex/object/容器/NaNInf及域外；整数计数严格int。返回complex仅限频域传递H，不丢弃虚部。下述域服务合理教学实验，不是任意精度/任意量级求解器。

|接口|输入单位和有限范围|返回及条件|
|---|---|---|
|interface|1–256数据lane，NRZ每lane .1–64 Gbit/s，编码效率.25–1，D1–4096B、L≥D且≤8192B，u.01–1，消息1–1048576B，固定0–1ms，e1fJ–1nJ/物理bit，idle0–10W|单方向raw/info bit/s、ceil帧数、wirebit、无排队/无重试/已激活串行与总增量s、平均W和消息J。D是协议信息，不默认应用payload；无lane条带对齐/暂停序列实现|
|rlc_transfer/rlc_step|R .1–200Ω，L1pH–10nH，C10fF–100pF；ζ限.1–.9；f0–1THz；t0–1μs且非零ω0t≥.001|高阻RX局部串联R/L到shuntC的Hcomplex和单位源v/i。零初值、常参数；初始更小归一时间域明确拒绝；不表示长走线或眼图合格|
|thermal|P1/P2 0–100W，每节点Ra .1–20K/W、R12 .1–100K/W、相同有效C .01–100J/K，t0–10000s，非零P/t至少1μW/1μs，Ta250–400K|稳态/时刻温升K、绝对K、两个时间常数s，初值均为0。仅对称独立环境支路和等有效热容；若共享散热器有独立状态须扩模型|
|thermo_mechanical|α1/α2 0–50ppm/K，ΔT±100K，距中性点.1–50mm，接头高度10μm–1mm|自由相对位移m和运动学γ，无应力/塑性/裂纹或寿命输出。均匀相同ΔT、小变形假设|
|leakage_equilibrium|每die基线0–100W，同a0–1W/K，Ra .1–20K/W|均匀稳态K与g−a的W/K阻尼，仅小范围线性化；g−a≥.01 W/K且温升≤200 K，超域（包括a≥g）在计算前拒绝，不迭代伪收敛|
|yield_cost|1–8个die，各.01–10cm²，D0–2/cm²，加工成本1–1000单位/cm²、分选每次0–100、组装0–1000、Ya .1–1|独立Poisson die良率、完美分选已知良die输入成本、每合格组装成本；无聚类/修复/检测逃逸/真实报价/NRE|

`data/parameters.json`保存原始教学输入；`data/results.json`保存同一接口.1224W及分到两个热节点的结果、CTE和三种成本流程。每die基线8/4W，链路总e已含两端，不再额外乘2；假设各端.0612W。图中的层高是独立示意坐标，不与成本假设die面积反推真实厚度。

## 独立核对与反例

13 tests实际测试：帧逐个计位而非重调用预算函数，65B消息填充/编码；RLC原v'=i/C、i'=(Vs−Ri−v)/L独立RK4（固定20000步）与峰导数/DC极限；两热节点原稳态KCL、均值/差模解析和零初/对称极限；CTE单位/符号；泄漏失稳a≥g拒绝；Poisson零缺陷概率与流程成本；invalid输入和纯导入。有限步RK4仅用于本例对照，不声称通用误差证书。

五个原创SVG和每个360/425px PNG分别承担结构/3D+剖面、闭合RLC/ps响应、两节点热/秒级温升、自由CTE/μm尺度和同分区多约束。V41是F02封装部分贡献，需要与F01Poisson/漂移扩散网格组合；本组不消费其待审内容。

## 原始来源与尚未验证

官方2023 Hot Chips UCIe Protocol的P2–3/P9/P11–13实际支持分层、Raw/CRC/retry责任和68B的协议信息口径；Electrical/Form-Factor的P1–4/P9–12/P19–21支持数据/时钟、封装和条件性时序预算。教程并非完整规范，也不是产品实测。UCIe规范公开入口与版本存在已查，规范正文未取得；生产需获取适用版本后审配置、电气、训练、协议及测试要求。本轮未填写表单、接受协议、上传或宣称UCIe符合性。

HotSpot原作者大学论文实际读必要模型/参数化/限制节支持热网络层次；本例对称2节点与解析拆模自行推导，不把作者FEM/实测结果转嫁给本实验。TI CTE文章说明焊点失配机制，本例自由小应变式自行推导，未认定寿命。

CPU/来源/作者渲染分别报告。PDK、真实PPA/SI/PI、native EDA、RTL/协议互通、EM/热机械求解器、制造/硬件、真实客户端和人的阅读验证均not_run，不能由CPU图像替代。
