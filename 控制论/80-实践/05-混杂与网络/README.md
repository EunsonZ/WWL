---
type: lab
stage: 2
aliases:
  - 混杂与网络控制复算
sources:
  - https://liberzon.csl.illinois.edu/teaching/Liberzon-LectureNotes.pdf
  - https://www.ece.ucsb.edu/~hespanha/published/ncs_v15p.pdf
prerequisites:
  - '[[控制论/10-系统课程/13-混杂事件切换与驻留保证]]'
  - '[[控制论/10-系统课程/14-网络采样时延与允许更新序列]]'
---

# 混杂与网络：先核事件，再核允许序列

本实践首先承接 [[控制论/10-系统课程/13-混杂事件切换与驻留保证|混杂与切换课程]]。同一热模型的事件表回答温度怎样连续、功率怎样跳；另一个无量纲二维模型回答各mode稳定为何仍可轮流放大。规范源码 [hybrid_lab.py](hybrid_lab.py) 是真源，[[控制论/80-实践/05-混杂与网络/code-sync/hybrid_lab|代码阅读镜像]] 与之同步。

## 输入、运行与实际结果

[hybrid-input.json](hybrid-input.json) 保存全部有限案例：$C=10$ J/K、$h=1$ W/K、$U=2$ W、$\delta=0.5$ K、$(x_0,q_0)=(0,+1)$、热终点40s；切换模型取 $(c,\tau_d)=(4,1),(4,14),(1,1)$，归一化终点56，三例共用最大根方向的单位范数初值。温差和二维归一化状态没有混用单位。

在本目录执行，下述输出目录必须尚不存在；脚本拒绝覆盖，复核时换新目录：

```sh
python3 -I -B hybrid_lab.py --output-dir /private/tmp/wwl-hybrid-rerun
```

作者实际用候选内新目录 `assets/hybrid` 运行，退出0。源码只使用标准库，串行计算且不启动子进程或设备，数值库线程变量固定1（低于本任务4线程上限）；有限输入有时域/参数边界，计算阶段检查60s限额。该自查不是操作系统硬实时/资源隔离证书。实际Python3.14.7/macOS27.0.1、耗时约0.036s、进程峰值RSS23,838,720bytes记于 [hybrid-run-output.txt](hybrid-run-output.txt)，平台观察不推广为别的机器容量界。

| 检查 | 独立可核依据与本次结果 | 不承担的证明 |
| --- | --- | --- |
| 热事件定位 | 对数根与流公式二分根最大差 $4.44\times10^{-16}$ s；首次2.8768207245s，后续间隔5.1082562377s，共8事件 | 有噪声、执行延迟下仍保持同一guard。 |
| 温差带 | 采样导出值落在±0.5K，正文另给流/跳不变性归纳 | 用有限值代替全部连续时间证明。 |
| 各mode稳定而乘积不稳 | 两段谱半径2.4284931214；12周期相对缩放后最大根方向差 $8.88\times10^{-16}$ | 从12周期外推任意模型。 |
| 二次型证书 | `Fraction` 精确检查 $A_i^TP_i+P_iA_i=-I$；充分驻留界13.6743114904 | 声称该界是必要条件或临界最小驻留。 |
| 独立积分 | 两段RK4各10/20/40步与解析矩阵流最大差约 $1.57\times10^{-5},9.31\times10^{-7},5.67\times10^{-8}$ | 积分步长等同控制器采样周期。 |
| 共同函数例 | $c=1$ 有限轨迹核对 $\|z\|\le e^{-\tau/2}\|z_0\|$，一般证明在正文 | 有限检查穷尽所有切换序列。 |

## 原输出和图源

- [events.csv](assets/hybrid/events.csv) 明确跳前/跳后挡位，温度不变；[thermal.csv](assets/hybrid/thermal.csv) 保存各流段及端点的时间、温差、挡位与功率。跨事件相同时间可出现两行不同挡位，这是左右状态记录。
- [switching.csv](assets/hybrid/switching.csv) 保存三种序列的模式、状态与范数；[summary.json](assets/hybrid/summary.json) 给解析/数值核对量。
- [thermostat.svg](assets/hybrid/thermostat.svg) 与 [switching.svg](assets/hybrid/switching.svg) 由规范脚本同一组数据生成，SVG带title/desc，线型和标签共同识别。前者坐标是s/K，后者是无量纲时间与 $\log_{10}\|z\|$。

CSV使用标准 `csv.writer` 的CRLF；JSON和SVG为UTF-8/LF。复建日志的耗时/RSS可能变化，不能把环境观察要求为逐字一致。

## 改变条件后应交什么

正文的三个撤提示题含解析答案。复算时先说明目标与假设，再在个人副本改输入：把阈值改成1K应重新求事件；把挡位功率降到不足以过阈值时，源码主动拒绝原周期模型，读者应写“无有限根”的解析结论；不要只把assert删掉让程序寻找不存在的事件。改变切换驻留要同时重算周期乘积和充分证书，不把充分界之外全部标成失稳。

未连接热硬件、执行器、网络或保护设备；未认证Obsidian客户端显示或真人撤提示能力。设备接口应分别记录采样时间、实际功率变化时间、guard左右温度、同时事件优先级、饱和与漏检；这些记录才能支持现实时间和物理输出核对。返回 [[控制论/00-控制论-MOC|课程入口]]。

## 网络更新与时延接续

[[控制论/10-系统课程/14-网络采样时延与允许更新序列|第14课]] 分开两条保证：新鲜事务零延迟、保持旧命令、最多连续3次失败的任意允许序列；可靠周期采样、固定分数执行延迟的二维增广映射。规范源码 [network_lab.py](network_lab.py)、[[控制论/80-实践/05-混杂与网络/code-sync/network_lab|阅读镜像]]、有限输入 [network-input.json](network-input.json) 独立保存。脚本只从hybrid_lab.py复用SVG绘图函数；不运行混杂实验。

```sh
python3 -I -B network_lab.py --output-dir /private/tmp/wwl-network-rerun
```

同样要求全新输出目录。作者实际运行写入候选新目录 `assets/network`，exit0；Python3.14.7/macOS27.0.1、串行耗时约0.029s、RSS观察23,379,968bytes见 [network-run-output.txt](network-run-output.txt)。规范脚本固定数值线程变量1、有限模型输入与小循环边界，未运行网络收发或设备任务。

- 新鲜成功间隔取m=1至4；四次成功间隔的全部256条序列用精确分数逐基础时隙递推，核对成功节点乘积与统一收缩界。一般无限序列结论来自正文，不由256条测试推出。m=5是刻意超出允许界的解析失效例。
- [updates.csv](assets/network/updates.csv) 给重复4/5时隙与混合序列的成功索引、真实物理时间、持有样本、区间内温度、保持功率与时龄；保持积分与乘子最大差约3.33e-16K。图 [updates.svg](assets/network/updates.svg) 使用同一数据，横轴秒、纵轴K。
- [enumeration.csv](assets/network/enumeration.csv) 保存256个长度4的间隔序列、精确终值及共同上界。其基准初值为1K；图的三个时域案例初值是输入文件明确给定的0.5K，不混用。
- [delay.csv](assets/network/delay.csv) 给固定0/半拍/整拍延迟各20步；起点0.5K、启动旧命令−2W，可靠采样周期3.5667494394s。两段保持积分与二维矩阵最大差1.67e-16K；半拍独立RK4每段4/8/16步误差递减至3.86e-11K，缩步检查刻意采用旧命令1.25W以避免第一段旧/新相同而漏查时序。
- [delay.svg](assets/network/delay.svg) 的折线连接采样节点，不把它误读为区间内真实线性温度；三组根模为0与0.5、约0.739351、约1.095445。固定延迟的谱结论不证明任意时变延迟。
- [packets.csv](assets/network/packets.csv) 是独立五包排序夹具，输入秒值/温差是手工指定，未声称来自热轨迹。接受序号0、2、3，拒绝迟到1与重复3；接受时龄有值不代表真实设备时钟已同步。
- [summary.json](assets/network/summary.json) 保存系数精确分数、两种稳定边界、容差结果和有限范围。脚本/数据/图没有网络随机分布假设，CPU耗时不是网络延迟。

正文三个迁移题有可核答案。修改K时先重推成功间隔/幅度域；使用迟到测量则必须重新声明预测或历史状态，不能继续把到达时刻当采集时刻。若要在设备验收，应把采集、收包、算完、施加四个时戳及其时钟基准、单调序号、实际保持/限幅功率一起保存；当前未运行该接口。
